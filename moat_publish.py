#!/usr/bin/env python3
"""Day bai da duyet sang moat de extension dang len Facebook/Instagram/TikTok.

Duyet bai van o day: Ong Chu bam nut trong topic, approve_service dang len
Telegram channel nhu cu. Phan them: bai do duoc bo vao hang doi publish cua
moat, roi extension trinh duyet claim va dang len social.

Hai chieu deu do BEN NAY chu dong:
  intake(draft_id)  -- day bai sang moat (goi ngay khi bam Duyet)
  poll()            -- hoi moat xem cac task da dang chua (cron goi dinh ky)

Moat khong goi nguoc ve day: host nay khong mo cong nao ra ngoai, va mot
vong poll 5 phut du nhanh cho viec "bao xem da len Facebook chua".

Khoa: MOT khoa cho MOI thuong hieu, trong secret.<brand>.env, gui qua header
X-API-Key. MOAT_PUBLISH_KEY cho donniechublog, MOAT_PUBLISH_KEY_DCGR cho
dcgr.tech. Mot khoa ung voi dung mot org ben moat -- khong bao gio truyen
org_id tu day, chinh cai khoa da chon org roi. Nen chon dung khoa la toan bo
viec dinh tuyen thuong hieu o buoc nay.

Trang thai duoc ghi nguoc vao chinh file draft (khoa "moat"), nen mot bai da
day roi khong bao gio day lai, va mot ket qua da bao roi khong bao lai.
"""
import base64
import io
import html
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx

import env_load
import state_paths

ROOT = env_load.ROOT
DRAFTS = ROOT / "drafts"
STATE_DIR = env_load.state_dir()          # state/<brand>/ theo container (fallback state/)

# Chi cac bucket ANH -- day chuyen nay ra the anh, khong ra video.
#
# KHONG co tiktok_slide: extension chi biet mot luong TikTok la upload VIDEO
# (content-tiktok.js), nen the anh nhet vao form video se treo o "Post button
# never enabled" roi het gio. Server van giao task vi cong kiem media-kind mien
# tru tiktok/instagram (gia dinh mot content script lo ca hai kieu -- dung voi
# Instagram, sai voi TikTok). Bo o day de khoi de ra task chet moi lan duyet bai.
# Mo lai khi extension co luong dang anh cho TikTok.
PLATFORMS = ["facebook_post", "instagram_carousel"]

TIMEOUT = 60

# Rieng luc DAY bai thi khong dung TIMEOUT chung duoc. Uplink cua may nay do
# duoc ~50 KB/s (7 MB het 136 giay, moat tra 400 chu khong tu choi -- ca body
# da qua). Mot bai carousel 5 anh la ~7 MB base64, day du 10 anh la ~14 MB, tuc
# rieng buoc GHI body mat 2-5 phut. httpx.Client(timeout=60) ap mot con so cho
# ca connect/read/write, nen moi bai nhieu anh chet o WriteTimeout va bai da len
# Telegram roi thi khong bao gio sang duoc social.
# Tach ra: connect/read van ngan de loi mang lo som, chi rieng write nuoi that dai.
TIMEOUT_BOTTOM = httpx.Timeout(connect=15.0, read=180.0, write=600.0, pool=15.0)
CEILING_BACKGROUND_LAYER = 2200        # gioi han caption cua Instagram va TikTok
MIME_BY_SUFFIX = {".png": "image/png", ".jpg": "image/jpeg",
                  ".jpeg": "image/jpeg", ".webp": "image/webp"}

MAX_IMAGE = 10                # tran so anh mot bai cua moat

# Nen anh truoc khi day. Uplink cua may nay ~50 KB/s, ma Cloudflare dung truoc
# moat cat request sau 100 giay (loi 524) -- KHONG phai timeout cua httpx, nen
# noi TIMEOUT_BOTTOM bao nhieu cung vo ich: body chua di het thi ket noi da dut.
# Mot carousel 5 the PNG la ~7 MB (base64 ~9.7 MB, ~180 giay) => luon 524.
# Cung bo the do sang WebP q90 con ~1.1 MB (~29 giay), qua duoi tran.
# Chi nen the nao VUOT nguong; the nho de nguyen. Tat bang MOAT_COMPRESS_IMAGES=0.
BACKGROUND_IMAGE = (os.environ.get("MOAT_COMPRESS_IMAGES") or "1") != "0"
THRESHOLD_BACKGROUND = int(os.environ.get("MOAT_COMPRESS_MIN_BYTES") or 400_000)   # bytes
QUALITY_BACKGROUND = int(os.environ.get("MOAT_COMPRESS_QUALITY") or 90)

# Tran CUNG cho tong anh mot bai. Nen tung the rieng le khong bao dam gi ca: 10
# the anh chup (nhieu chi tiet, WebP kem hieu qua hon anh do hoa) van co the ra
# 5 MB va lai 524. Uplink do duoc dao dong 37-49 KB/s, nen lay 1,5 MB: base64
# ~2 MB, tuc ~55 giay o luc mang xau nhat -- con nua thoi gian du phong.
# Vuot tran thi ha chat luong dan; kem nhat van con q60, thua bo bai.
CEILING_TOTAL = int(os.environ.get("MOAT_MAX_TOTAL_BYTES") or 1_500_000)
TIER_QUALITY = [QUALITY_BACKGROUND, 80, 70, 60]

# Task o cac trang thai nay coi nhu xong, khong hoi lai nua.
TERMINAL = {"published", "failed", "cancelled"}

# Ngung theo doi sau ngan nay ngay. Task khong ai dang (extension tat) se dung o
# "scheduled" vinh vien; khong co tran nay thi moi bai nhu the la them mot request
# MOI PHUT, mai mai. Bao mot dong roi buong.
MAX_TRACK_DAYS = 7

PLATFORM_LABEL = {"facebook": "Facebook", "instagram": "Instagram", "tiktok": "TikTok"}


def load_secrets():
    """Nap cau hinh qua env_load: secret.common.env -> secret.<brand>.env ->
    .secrets.env.

    Truoc day ham nay tu doc MOT MINH .secrets.env. Hau qua: tien trinh chay
    doc lap (cron goi poll()) khong bao gio thay tep rieng cua brand, chi
    approve_service -- vi no goi env_load.nap() luc import -- moi thay. Hai
    duong vao cung mot module ma ra hai ket qua khac nhau, va brand dcgr thi
    khong duong nao thay khoa ca. Mot cua nap duy nhat de het lech.
    """
    env_load.load()


def _wait_within(v):
    """Gia tri kieu '<dan khoa vao day>' trong secret.<brand>.env la CHO TRONG
    chua dien, khong phai khoa. Coi la chua cau hinh, thay vi cam dau goi moat
    de an 401 moi phut."""
    return v.startswith("<")


# Thuong hieu -> ten bien moi truong chua khoa. Khoa quyet dinh org ben moat,
# nen bang nay CHINH LA anh xa thuong hieu -> org social. Them mot thuong hieu
# la them mot dong o day, khong sua cho nao khac.
LOCK_BY_BRAND = {
    "donniechublog": "MOAT_PUBLISH_KEY",
    "dcgr": "MOAT_PUBLISH_KEY_DCGR",
}
DEFAULT_BRAND = "donniechublog"
LOCK_DEFAULT = "MOAT_PUBLISH_KEY"


def name_lock(brand=None):
    """Ten bien moi truong chua khoa cua thuong hieu nay."""
    return LOCK_BY_BRAND.get(brand or DEFAULT_BRAND, LOCK_DEFAULT)


# CUNG quy uoc voi approve_service: CT_BRAND ('blog'|'dcgr') la khoa container,
# BRAND (ten content-brand day du) suy tu no va van cho env de len.
_TEN_BRAND = env_load.BRAND_LONG        # mot bang, o env_load (ADF-r2-10)


def brand_container():
    """Brand ma container nay phu trach. Rong = che do don cu (khong loc)."""
    load_secrets()
    ten = os.environ.get("BRAND", "").strip()
    if ten:
        return ten
    return _TEN_BRAND.get(os.environ.get("CT_BRAND", "").strip(), "")


def base_url():
    load_secrets()
    return (os.environ.get("MOAT_BASE_URL") or "").rstrip("/")


def config(brand=None):
    """(base_url, api_key) cua MOT thuong hieu, (None, None) khi chua cau hinh.

    Chua cau hinh KHONG phai loi: dich vu duyet bai van chay binh thuong
    chi khong day sang moat. Day la duong lui khi moat sap.

    Thieu khoa cua thuong hieu nay thi tra (None, None) chu KHONG roi ve khoa
    mac dinh. Roi ve la day bai dcgr.tech vao org cua donniechublog — dung
    cai sai ma ca duong dan brand nay sinh ra de chan. Tha khong day con hon
    day nham: bai van len Telegram, va the duyet ghi ro thieu khoa nao.
    """
    base = base_url()
    key = os.environ.get(name_lock(brand)) or ""
    if _wait_within(key):
        key = ""
    if not base or not key:
        return None, None
    return base, key


def draft_path(draft_id):
    return DRAFTS / (draft_id + ".json")


def read_draft(draft_id):
    return json.loads(draft_path(draft_id).read_text(encoding="utf-8"))


def _write_json(path, data):
    """Ghi atomic (tmp + os.replace): draft la so cai cua he thong, write_text
    truc tiep ma chet giua chung se de lai JSON cut."""
    # ADF-r2-11: mot ban o env_load.ghi_json (tmp co pid+thread, mkdir, don tmp
    # khi hong) — ban cu o day dung ten tmp co dinh nen hai tien trinh cung ghi
    # mot draft la lan vao nhau.
    env_load.write_json(path, data)


def write_draft(draft_id, data):
    _write_json(draft_path(draft_id), data)


# Caption duoc viet CHO TELEGRAM (parse_mode=HTML): <b>, <i>, <code>. Facebook,
# Instagram va TikTok khong hieu HTML — chung in nguyen chu "<b>" ra bai dang.
# Do tren drafts hien co: 42/61 bai co the, chi gom b/i/code, khong co <a> va
# khong co entity — nen boc the va giu nguyen chu ben trong la du, khong mat gi.
_THE_HTML = re.compile(r"</?[a-zA-Z][a-zA-Z0-9-]*[^>]*>")


def pure_text(text):
    """Caption dang len social: bo the HTML, giu chu ben trong."""
    return html.unescape(_THE_HTML.sub("", text or "")).strip()


def _background(raw, mime, ten="", chat_luong=None):
    """(bytes, mime) sau khi nen. Tra lai nguyen ban neu khong nen duoc/khong loi.

    WebP giu duoc chu tren the carousel o q90 ma nho hon PNG ~6 lan. Giu kenh
    alpha khi anh co, vi convert("RGB") se bien nen trong suot thanh den.
    Moi loi o day deu nuot: day duoc bai van hon la nen dep.
    """
    q = QUALITY_BACKGROUND if chat_luong is None else chat_luong
    if not BACKGROUND_IMAGE or len(raw) <= THRESHOLD_BACKGROUND:
        return raw, mime
    try:
        from PIL import Image                                 # noqa: PLC0415
        im = Image.open(io.BytesIO(raw))
        buf = io.BytesIO()
        if im.mode in ("RGBA", "LA", "P"):
            im.convert("RGBA").save(buf, "WEBP", quality=q, method=6)
        else:
            im.convert("RGB").save(buf, "WEBP", quality=q, method=6)
        out = buf.getvalue()
    except Exception as e:                                   # noqa: BLE001
        print("khong nen duoc " + ten + ": " + str(e))
        return raw, mime
    # PNG nho/da toi uu co the con nho hon ban WebP -- giu cai nao nhe hon.
    if len(out) >= len(raw):
        return raw, mime
    return out, "image/webp"


def images_payload(d):
    """Anh gui sang moat: URL de nguyen, file cuc bo thi gui bytes.

    Host nay khong serve HTTP ra ngoai nen file cuc bo BUOC phai di kem
    request; moat luu vao kho media cua no roi tra ve duong dan noi bo.

    `images` cua hermes chua DUONG DAN CUC BO (card.py ghi .png vao drafts/),
    khong phai URL. Loc ca danh sach theo "http" tung lam moi bai NHIEU anh tra
    ve rong -> "khong tim thay anh de day", trong khi bai mot anh (`image`) lai
    di duoc. Nen duyet tung phan tu: http de nguyen, con lai doc bytes.
    """
    srcs = d.get("images") or []
    if not srcs and d.get("image"):
        srcs = [d["image"]]

    # Doc het bytes truoc: phai biet TONG moi chon duoc muc nen, ma nen tung
    # the roi cong lai thi da muon.
    tho = []
    for s in srcs:
        if not isinstance(s, str) or not s:
            continue
        if s.startswith("http"):
            tho.append(("url", s, "", ""))
            continue
        f = Path(s)
        if not f.exists():
            continue
        mime = MIME_BY_SUFFIX.get(f.suffix.lower(), "image/png")
        tho.append(("bytes", f.read_bytes(), mime, f.name))

    da_nen = None
    for q in TIER_QUALITY:
        thu = [(k, (_background(v, mi, ten, q) if k == "bytes" else (v, mi)))
               for k, v, mi, ten in tho]
        tong = sum(len(v[0]) for k, v in thu if k == "bytes")
        da_nen = thu
        if tong <= CEILING_TOTAL or not BACKGROUND_IMAGE:
            break
        print("anh con " + str(tong // 1024) + " KB o q" + str(q)
              + ", ha them mot bac")

    out = []
    for kind, v in (da_nen or []):
        if kind == "url":
            out.append({"url": v[0]})
        else:
            raw, mime = v
            out.append({"base64": base64.b64encode(raw).decode("ascii"),
                        "mime": mime})
    # Moat nhan toi da 10 anh mot bai; gui 11 la ca bai bi tu choi.
    return out[:MAX_IMAGE]


def _body_intake(draft_id, d, cap, images, scheduled_at=None,
                 platforms=None, external_id=None):
    """Payload /publish-intake cua moat — mot cho de doi chieu voi schema cua no.

    `platforms` de dang LAI mot nen tang da that bai ma khong dang lai nhung
    nen tang da len: intake tao task cho MOI nen tang trong danh sach, nen giu
    nguyen ca bo la Facebook len hai lan.
    `external_id` phai KHAC lan truoc thi moat moi tao workflow moi -- no
    idempotent theo khoa nay, gui lai id cu chi tra ve workflow cu.
    """
    body = {
        "externalId": external_id or draft_id,
        "title": cap[:80],
        "caption": cap,
        "sourceUrl": d.get("source_url") or "",
        "images": images,
        "platforms": platforms or PLATFORMS,
    }
    if scheduled_at:
        body["scheduledAt"] = scheduled_at
    return body


def intake(draft_id, scheduled_at=None, platforms=None, external_id=None):
    """Day mot draft da duyet sang hang doi publish cua moat.

    Tra (ok, note). Khong bao gio nem ngoai le: bai da len Telegram channel
    roi, mot loi o day khong duoc lam hong luong duyet.
    """
    try:
        d = read_draft(draft_id)
    except Exception as e:                                   # noqa: BLE001
        return False, "khong doc duoc draft: " + str(e)

    # Doc draft TRUOC khi lay cau hinh: chua biet thuong hieu thi chua biet
    # phai dung khoa nao, ma khoa moi la thu quyet dinh bai len org nao.
    # Draft ghi truoc khi co truong "brand" roi ve mac dinh — dung nhu cu.
    brand = d.get("brand") or DEFAULT_BRAND
    base, key = config(brand)
    if not base:
        return False, ("chua cau hinh MOAT_BASE_URL/" + name_lock(brand)
                       + " cho thuong hieu " + brand)

    # Idempotent CHI cho cu day mac dinh. Nut "Day lai <nen tang>" truyen
    # external_id moi (va mot platform) de co mot workflow khac — chan o day
    # thi nut do khong bao gio tao duoc task, bam bao nhieu lan cung chi thay
    # "da day truoc do" (gap 19/09/2026 khi dang lai Facebook bi mat anh).
    if (external_id is None and platforms is None
            and isinstance(d.get("moat"), dict) and d["moat"].get("workflow_id")):
        return True, "da day truoc do"

    # Tran chung cho moi nen tang. Ong Chu chot lay gioi han Instagram lam moc
    # va chap nhan danh doi: mot ban dang duoc khap noi, thay vi phai fine-tune
    # rieng cho tung nen tang. Chan o day la lop cuoi — truoc luc di qua moat
    # thi bai phai o trang thai dang duoc ngay.
    # Teaser CHI dang len Telegram — no moi doc sang bai goc tren donniechu.com,
    # ma Instagram va TikTok khong cho link an duoc nen dua sang do cung vo ich.
    # Bo qua han thay vi chan, de khong bao loi gia moi lan duyet mot teaser.
    if (d.get("category") or "").upper() == "TEASER":
        return False, "teaser chi dang Telegram, khong day sang moat"

    # Tran chi ap cho TIN HANG NGAY. Ong Chu chot lay gioi han Instagram lam moc
    # va chap nhan danh doi: mot ban dang duoc khap noi, thay vi fine-tune rieng
    # tung nen tang. Chan o day la lop cuoi — toi day bai phai dang duoc ngay.
    # Boc the TRUOC khi do: tran nay phai do dung chuoi that su dang len,
    # khong phai chuoi con lan the HTML.
    cap = pure_text(d.get("caption"))
    if len(cap) > CEILING_BACKGROUND_LAYER:
        return False, (f"caption {len(cap)} ky tu, vuot tran {CEILING_BACKGROUND_LAYER} cua "
                       f"Instagram/TikTok (thua {len(cap) - CEILING_BACKGROUND_LAYER}). "
                       "Rut ngan roi day lai.")

    images = images_payload(d)
    if not images:
        return False, "khong tim thay anh de day"

    body = _body_intake(draft_id, d, cap, images, scheduled_at,
                        platforms, external_id)

    # Danh dau "dang day" TRUOC khi goi: mot cu kill -9 giua luc upload (may tat,
    # systemd restart, OOM) khong chay duoc nhanh loi nao ben duoi, va bai se mat
    # dau y nhu thoi chua co hang doi. Ghi truoc thi cron sau do nhat len.
    _list_mark_form_bottom(draft_id, brand, scheduled_at)

    try:
        with httpx.Client(timeout=TIMEOUT_BOTTOM) as c:
            r = c.post(base + "/publish-intake", json=body,
                       headers={"X-API-Key": key})
    except Exception as e:                                   # noqa: BLE001
        loi = "khong goi duoc moat: " + type(e).__name__ + ": " + str(e)
        refill(draft_id, brand, scheduled_at, loi)
        return False, loi

    if r.status_code not in (200, 201):
        loi = "moat tra HTTP " + str(r.status_code) + ": " + r.text[:200]
        if not refill(draft_id, brand, scheduled_at, loi):
            _drop_block_queue(draft_id)      # loi khong tu khoi, dung giu lai
        return False, loi

    out = r.json()
    # Day lai bang external_id moi sinh ra mot workflow khac; ghi de thang thi
    # mat dau workflow cu (con task dang theo doi). Cat vao lich su truoc.
    cu = d.get("moat")
    if isinstance(cu, dict) and cu.get("workflow_id") != out.get("workflowId"):
        d.setdefault("moat_history", []).append(cu)
    d["moat"] = {
        "workflow_id": out.get("workflowId"),
        # Ghi lai org da day len. poll() phai hoi dung cai org do, khong
        # duoc suy lai tu draft: doi brand sau khi day la mat dau vet.
        "brand": brand,
        "external_id": out.get("externalId", draft_id),
        "platforms": PLATFORMS,
        "pushed_at": int(time.time()),
        "reported": {},
    }
    write_draft(draft_id, d)
    _drop_block_queue(draft_id)
    n = len(out.get("tasks", []))
    return True, "da xep " + str(n) + " task publish"


# Hang doi day lai. Bai da len Telegram channel roi ma intake truot (mang dut,
# Cloudflare 524, moat 5xx) thi TRUOC DAY nam im vinh vien: intake() nuot loi
# theo thiet ke -- de khong lam hong luong duyet -- va khong ai goi lai. Ghi vao
# day, cron moat-publish-watch (5 phut/lan) day lai theo lich lui dan.
# An toan vi intake cua moat idempotent theo external_id: goi lai bai da vao roi
# thi no tra ve workflow cu kem "duplicate": true, khong de ra task trung.
QUEUE = STATE_DIR / state_paths.MOAT_REPUBLISH_QUEUE_FILE

# Phut cho truoc lan thu thu 1, 2, 3... Het bang la bo cuoc va bao mot dong.
SCHEDULE_BACK = [5, 15, 45, 120, 360, 720, 1440]


def _read_queue():
    try:
        d = json.loads(QUEUE.read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:                                        # noqa: BLE001
        return {}


def _write_queue(d):
    try:
        QUEUE.parent.mkdir(parents=True, exist_ok=True)
        QUEUE.write_text(json.dumps(d, ensure_ascii=False, indent=2),
                            encoding="utf-8")
    except Exception as e:                                   # noqa: BLE001
        print("khong ghi duoc hang doi day lai: " + str(e))


def _form_try_again(loi):
    """Loi nay day lai co cua khong?

    Mang dut / 5xx / 408 / 429 / 524 la nhat thoi -> thu lai. Con caption dai,
    thieu anh, chua cau hinh khoa, 4xx khac la loi cua chinh bai: day lai bao
    nhieu lan cung the, chi ton bang thong va rac log.
    """
    if loi.startswith("khong goi duoc moat"):
        return True
    m = re.match(r"moat tra HTTP (\d+)", loi)
    if not m:
        return False
    ma = int(m.group(1))
    return ma in (408, 425, 429) or ma >= 500


def _list_mark_form_bottom(draft_id, brand, scheduled_at):
    """Ghi mot muc "dang day" truoc khi POST. KHONG tang so lan: day la dau vet
    de song sot qua mot cu kill, khong phai mot lan that bai."""
    d = _read_queue()
    muc = d.get(draft_id) or {"attempts": 0}
    muc["brand"] = brand
    muc["scheduled_at"] = scheduled_at
    muc["last_attempt_at"] = int(time.time())
    muc["error"] = muc.get("error") or "dang day, chua co ket qua"
    d[draft_id] = muc
    _write_queue(d)


def refill(draft_id, brand, scheduled_at, loi):
    """Ghi mot bai truot vao hang doi (hoac tang so lan da thu)."""
    if not _form_try_again(loi):
        return False
    d = _read_queue()
    muc = d.get(draft_id) or {"attempts": 0, "brand": brand,
                              "scheduled_at": scheduled_at}
    muc["attempts"] = int(muc.get("attempts", 0)) + 1
    muc["brand"] = brand
    muc["scheduled_at"] = scheduled_at
    muc["last_attempt_at"] = int(time.time())
    muc["error"] = loi[:200]
    d[draft_id] = muc
    _write_queue(d)
    return True


def _drop_block_queue(draft_id):
    """Doc-sua-ghi ngay lap tuc: intake() cung ghi vao file nay giua chung,
    nen giu mot ban `d` trong bo nho roi ghi de o cuoi la mat cap nhat cua no."""
    d = _read_queue()
    if d.pop(draft_id, None) is not None:
        _write_queue(d)


def bottom_again():
    """Day lai cac bai dang cho trong hang doi, tra ve list dong thong bao.

    Chi dung bai cua brand container nay -- hai container dung chung drafts/, ma
    khoa moat moi la thu quyet dinh bai len org nao.
    """
    d = _read_queue()
    if not d:
        return []
    cua_toi = brand_container()
    bay_gio = int(time.time())
    lines = []

    for draft_id in list(d.keys()):
        muc = d.get(draft_id) or {}
        brand = muc.get("brand") or DEFAULT_BRAND
        if cua_toi and brand != cua_toi:
            continue
        lan = max(int(muc.get("attempts", 1)), 1)   # muc write-ahead co attempts=0
        if lan > len(SCHEDULE_BACK):
            _drop_block_queue(draft_id)
            txt = ("🛑 Bỏ cuộc sau " + str(lan - 1) + " lần đẩy lại sang moat — "
                   + _exit(str(muc.get("error", ""))[:150]))
            if not report_card(draft_id, txt,
                           [{"text": "🔁 Đẩy lại moat", "callback_data": "mlai:" + draft_id}]):
                lines.append("🛑 moat: bo cuoc sau " + str(lan - 1) + " lan day lai "
                             + draft_id + " — " + str(muc.get("error", ""))[:120])
            continue
        if bay_gio - int(muc.get("last_attempt_at", 0)) < SCHEDULE_BACK[lan - 1] * 60:
            continue

        # intake() tu tang so lan (loi con thu lai duoc) hoac tu xoa (thanh cong).
        ok, note = intake(draft_id, muc.get("scheduled_at"))
        if ok:
            lines.append("✅ moat: day lai lan " + str(lan) + " thanh cong "
                         + draft_id + " — " + note)
        elif not _form_try_again(note):
            _drop_block_queue(draft_id)
            lines.append("⚠️ moat: thoi day lai " + draft_id
                         + " vi loi khong tu khoi: " + note[:150])
    return lines


def _fetch_status(base, key, ref):
    """`ref` nen la workflow_id: ben moat do la khoa chinh, con external_id phai
    quet bang workflows. Chay moi phut thi khac biet do tich lai."""
    with httpx.Client(timeout=TIMEOUT) as c:
        r = c.get(base + "/publish-intake/" + ref, headers={"X-API-Key": key})
    if r.status_code != 200:
        raise RuntimeError("HTTP " + str(r.status_code) + ": " + r.text[:200])
    return r.json().get("tasks", [])


def _poll_one_article(path, d, cua_toi, lines):
    """Mot draft: bo qua neu khong phai bai da day / khac brand / da xong / het
    han theo doi; hoi moat mot lan, bao MOI trang thai moi mot lan, ghi nguoc
    vao draft. `lines` la danh sach dong thong bao, ghi them vao."""
    moat = d.get("moat")
    if not isinstance(moat, dict) or not moat.get("external_id"):
        return
    if moat.get("tracking_stopped"):
        return
    # Bai day tu truoc khi tach brand khong co khoa "brand" -> mac dinh.
    if cua_toi and (moat.get("brand") or d.get("brand") or DEFAULT_BRAND) != cua_toi:
        return
    reported = moat.get("reported") or {}
    if reported and all(v in TERMINAL for v in reported.values()) \
            and len(reported) >= len(moat.get("platforms") or PLATFORMS):
        return

    pushed_at = moat.get("pushed_at") or 0
    if pushed_at and time.time() - pushed_at > MAX_TRACK_DAYS * 86400:
        # Dem viec CON THIEU theo danh sach platform da dang ky, khong theo
        # reported: extension chua tung chay thi reported RONG — ca hai
        # cach dem deu phai ra "con thieu het", truoc day lai ra "xong".
        cac_san = moat.get("platforms") or PLATFORMS
        xong = sum(1 for st in reported.values() if st in TERMINAL)
        pending = list(range(max(0, len(cac_san) - xong)))
        moat["tracking_stopped"] = True
        d["moat"] = moat
        _write_json(path, d)
        if pending:
            lines.append("⏳ " + path.stem + ": còn " + str(len(pending))
                         + " task chưa đăng sau " + str(MAX_TRACK_DAYS)
                         + " ngày, ngừng theo dõi, xem lại extension")
        return

    # Hoi dung cai org da day bai nay len. Bai day tu truoc khi tach org
    # khong co khoa "brand" — roi ve mac dinh, tuc dung khoa cu.
    base, key = config(moat.get("brand") or d.get("brand"))
    if not base:
        # Khoa cua thuong hieu nay bi go khoi .secrets.env SAU khi da day.
        # Khong hoi duoc thi im: cron chay moi phut, canh bao o day la
        # 1440 dong rac mot ngay.
        return

    try:
        tasks = _fetch_status(base, key, moat.get("workflow_id") or moat["external_id"])
    except Exception as e:                               # noqa: BLE001
        # Chi bao MOT lan cho moi loai loi. Cron chay moi phut: moat sap
        # 6 tieng ma bao moi lan la 360 tin rac vao topic Miles. Nho loai
        # loi da bao trong draft; loi doi (DNS -> timeout) thi bao lai,
        # het loi thi xoa co de lan sap sau con bao.
        loi_moi = type(e).__name__
        if moat.get("reported_error") != loi_moi:
            moat["reported_error"] = loi_moi
            d["moat"] = moat
            _write_json(path, d)
            lines.append("⚠️ " + path.stem + ": khong hoi duoc moat ("
                         + loi_moi + "), se im cho toi khi tinh hinh doi")
        return
    if moat.pop("reported_error", None):
        d["moat"] = moat
        _write_json(path, d)
        lines.append("✅ " + path.stem + ": moat hoi lai duoc roi")

    changed = False
    for t in tasks:
        tid, status = t.get("id"), t.get("status")
        if not tid or status == reported.get(tid):
            continue
        reported[tid] = status
        changed = True
        if status not in TERMINAL:
            continue
        label = PLATFORM_LABEL.get(t.get("platform"), t.get("platform"))
        if status == "published":
            line = "✅ " + path.stem + " đã lên " + label
            if t.get("result_url"):
                line += "\n" + t["result_url"]
        elif status == "failed":
            line = ("❌ " + path.stem + " đăng " + label + " lỗi: "
                    + (t.get("last_error") or "không rõ lý do"))
            # Bao TRA LOI vao the, kem nut dang lai rieng nen tang nay. Gui
            # duoc thi thoi khong nem vao topic nua -- cung mot loi bao hai
            # cho la nhieu, ma reply moi la cai chi dung bai.
            ma = CODE_BUTTON_FORM_AGAIN.get(t.get("platform"))
            nut = ([{"text": "🔁 Đăng lại " + label,
                     "callback_data": ma + path.stem}] if ma else None)
            if report_card(path.stem, "❌ Đăng <b>" + label + "</b> lỗi: "
                       + _exit(t.get("last_error") or "không rõ lý do"), nut):
                continue
        else:
            line = "⏹ " + path.stem + " " + label + ": " + status
        lines.append(line)

    if changed:
        moat["reported"] = reported
        d["moat"] = moat
        _write_json(path, d)


def poll():
    """Hoi moat trang thai cac bai da day, tra ve list dong thong bao moi.

    Chi bao MOT lan cho moi task: trang thai da bao duoc ghi vao draft, nen
    cron chay 5 phut mot lan khong bien thanh may spam.
    """
    if not base_url():
        return []

    # drafts/ dung CHUNG cho moi container, ma poll() lai ghi co trang thai
    # ("reported_error", "reported", "tracking_stopped") nguoc vao chinh file draft.
    # Container nao cung soi ca thu muc thi hai tien trinh thay nhau dat va xoa
    # cung mot co: co che "chi bao MOT lan" thanh bao mai mai, va bao sai — moi
    # container giai ra mot khoa khac nhau cho cung mot brand, nen ben thay
    # workflow ben khong. Moi container chi soi bai cua brand minh.
    cua_toi = brand_container()

    lines = []
    for path in sorted(DRAFTS.glob("*.json")):
        if path.name.endswith(".meta.json"):
            continue
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            continue
        _poll_one_article(path, d, cua_toi, lines)

    return lines


# Ma nut "dang lai" cho tung nen tang. Callback data cua Telegram toi da 64
# byte, ma _DRAFT_ID_HOP_LE cho draft_id dai toi 55 ky tu -> tien to phai ngan;
# 6 + 55 = 61, vua du. Dung draft_id thang thay vi mot so tra bang de nut con
# bam duoc sau khi dich vu restart (khong con so tra nao de tra).
CODE_BUTTON_FORM_AGAIN = {"facebook": "mlaif:", "instagram": "mlaii:", "tiktok": "mlait:"}


def _exit(s):
    """Escape cho parse_mode=HTML. last_error cua extension co the chua dau <>
    (ten the DOM), khong thoat thi Telegram tu choi ca tin nhan."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _tele(method, **kw):
    """Goi Bot API. Khong bao gio nem: bao loi that bai khong duoc lam hong
    vong poll dang chay."""
    try:
        sys.path.insert(0, str(ROOT))
        import publish                                        # noqa: PLC0415
        token, _channel = publish.load_secrets()
        if not token:
            return {"ok": False, "description": "khong co token"}
        with httpx.Client(timeout=30) as c:
            r = c.post("https://api.telegram.org/bot" + token + "/" + method,
                       json=kw)
        return r.json()
    except Exception as e:                                   # noqa: BLE001
        return {"ok": False, "description": type(e).__name__ + ": " + str(e)}


def report_card(draft_id, text, nut=None):
    """Bao TRA LOI thang vao the cua bai tren Telegram, kem nut neu co.

    Truoc day moi thu bao ket qua deu roi vao topic writer nhu mot dong troi
    noi: bai nao dang loi thi phai tu doi chieu tieu de. Reply vao dung the moi
    thay ngay bai nao, va cho nut "dang lai" mot cho de dat.

    Tra True neu gui duoc; nguoi goi lay do quyet dinh co can bao kieu cu nua
    khong. The bi xoa (reply_to chet) thi gui roi, van hon la mat tin.
    """
    try:
        d = read_draft(draft_id)
    except Exception:                                        # noqa: BLE001
        d = {}
    # Nap secret nhu config() lam: chay tu CLI thi TELEGRAM_GROUP_ID chua co
    # trong moi truong (systemd moi dat san cho dich vu), va thieu no thi ham
    # nay im lang khong gui gi -- dung kieu loi ma co che nay sinh ra de chua.
    env_load.load()
    group = os.environ.get("TELEGRAM_GROUP_ID")
    if not group:
        print("khong bao duoc the: thieu TELEGRAM_GROUP_ID")
    if not group:
        return False
    kw = {"chat_id": group, "text": text, "parse_mode": "HTML"}
    try:
        tp = env_load.topics_path()
        if tp.exists():
            thread = json.loads(tp.read_text(encoding="utf-8")).get("writer")
            if thread:
                kw["message_thread_id"] = thread
    except Exception:                                        # noqa: BLE001
        pass
    if nut:
        kw["reply_markup"] = {"inline_keyboard": [nut]}
    mid = d.get("tg_card_message_id")
    if mid:
        r = _tele("sendMessage", reply_to_message_id=mid, **kw)
        if r.get("ok"):
            return True
        # The da bi xoa/qua cu -> Telegram tu choi ca tin. Gui khong reply.
        print("khong reply duoc the " + str(mid) + ": " + str(r.get("description")))
    r = _tele("sendMessage", **kw)
    if not r.get("ok"):
        print("khong bao duoc Telegram: " + str(r.get("description")))
    return bool(r.get("ok"))


SPOOL = STATE_DIR / state_paths.MOAT_UNSENT_NOTICES_FILE


def _notify(lines):
    """Bao ket qua vao topic writer. Im lang khi khong co gi moi.

    `reported` da ghi vao draft TRUOC khi den day, nen dong nao khong gui duoc
    la mat vinh vien — lan poll sau thay trang thai "da bao roi" va im. Vi the
    gui hut thi de danh vao SPOOL, lan chay sau gop vao gui lai. Cron moi phut
    nen do tre toi da chi mot phut sau khi Telegram hoi phuc.

    Khong tu in ra man hinh -- ban ghi cron do __main__ in mot lan duy nhat
    neu khong moi lan chay se ra hai ban giong het nhau.
    """
    cho = []
    if SPOOL.exists():
        try:
            cho = json.loads(SPOOL.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            cho = []
    lines = cho + [l for l in lines if l not in cho]
    if not lines:
        return
    try:
        sys.path.insert(0, str(ROOT))
        import publish                                       # noqa: PLC0415
        token, _channel = publish.load_secrets()
        group = os.environ.get("TELEGRAM_GROUP_ID")
        if not group:
            return
        thread = None
        tp = env_load.topics_path()
        if tp.exists():
            thread = json.loads(tp.read_text(encoding="utf-8")).get("writer")
        publish.send_text(token, group, "\n\n".join(lines), thread=thread)
        SPOOL.unlink(missing_ok=True)
    except Exception as e:                                   # noqa: BLE001
        print("khong bao duoc Telegram, de danh " + str(len(lines))
              + " dong bao lai lan sau: " + str(e))
        SPOOL.write_text(json.dumps(lines[-40:], ensure_ascii=False, indent=2),
                         encoding="utf-8")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "push":
        ok, note = intake(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
        print(("OK: " if ok else "LOI: ") + note)
        sys.exit(0 if ok else 1)
    if len(sys.argv) > 1 and sys.argv[1] == "status":
        brand = sys.argv[3] if len(sys.argv) > 3 else None
        base, key = config(brand)
        if not base:
            sys.exit("chua cau hinh MOAT_BASE_URL/" + name_lock(brand))
        print(json.dumps(_fetch_status(base, key, sys.argv[2]), ensure_ascii=False, indent=2))
        sys.exit(0)
    out = bottom_again() + poll()
    _notify(out)
    # Khong co gi moi thi IM HAN (stdout rong). Cron chay moi phut, ma hermes ghi
    # moi ban stdout thanh mot file, in "khong co thay doi" la 1440 file rac/ngay.
    if out:
        print("\n".join(out))
