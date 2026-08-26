#!/usr/bin/env python3
"""Day bai da duyet sang moat de extension dang len Facebook/Instagram/TikTok.

Duyet bai van o day: Ong Chu bam nut trong topic, approve_service dang len
Telegram channel nhu cu. Phan them: bai do duoc bo vao hang doi publish cua
moat, roi extension trinh duyet claim va dang len social.

Hai chieu deu do BEN NAY chu dong:
  intake(draft_id)  -- day bai sang moat (goi ngay khi bam Duyet)
  poll()            -- hoi moat xem cac task da dang chua (cron goi dinh ky)

Moat khong goi nguoc ve day: host nay khong mo cong nao ra ngoai, va mot
vong poll 10 phut du nhanh cho viec "bao xem da len Facebook chua".

Khoa: MOT khoa cho MOI thuong hieu, trong .secrets.env, gui qua header
X-API-Key. MOAT_PUBLISH_KEY cho donniechublog, MOAT_PUBLISH_KEY_DCGR cho
dcgr.tech. Mot khoa ung voi dung mot org ben moat -- khong bao gio truyen
org_id tu day, chinh cai khoa da chon org roi. Nen chon dung khoa la toan bo
viec dinh tuyen thuong hieu o buoc nay.

Trang thai duoc ghi nguoc vao chinh file draft (khoa "moat"), nen mot bai da
day roi khong bao gio day lai, va mot ket qua da bao roi khong bao lai.
"""
import base64
import json
import os
import sys
import time
from pathlib import Path

import httpx

ROOT = Path.home() / "content-team"
DRAFTS = ROOT / "drafts"
STATE_DIR = ROOT / "state"
SECRETS = ROOT / ".secrets.env"

# Chi cac bucket ANH -- day chuyen nay ra the anh, khong ra video.
PLATFORMS = ["facebook_post", "instagram_carousel", "tiktok_slide"]

TIMEOUT = 60
TRAN_NEN_TANG = 2200        # gioi han caption cua Instagram va TikTok
MIME_BY_SUFFIX = {".png": "image/png", ".jpg": "image/jpeg",
                  ".jpeg": "image/jpeg", ".webp": "image/webp"}

MAX_ANH = 10                # tran so anh mot bai cua moat

# Task o cac trang thai nay coi nhu xong, khong hoi lai nua.
TERMINAL = {"published", "failed", "cancelled"}

# Ngung theo doi sau ngan nay ngay. Task khong ai dang (extension tat) se dung o
# "scheduled" vinh vien; khong co tran nay thi moi bai nhu the la them mot request
# MOI PHUT, mai mai. Bao mot dong roi buong.
MAX_TRACK_DAYS = 7

PLATFORM_LABEL = {"facebook": "Facebook", "instagram": "Instagram", "tiktok": "TikTok"}


def load_secrets():
    if SECRETS.exists():
        for line in SECRETS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())


# Thuong hieu -> ten bien moi truong chua khoa. Khoa quyet dinh org ben moat,
# nen bang nay CHINH LA anh xa thuong hieu -> org social. Them mot thuong hieu
# la them mot dong o day, khong sua cho nao khac.
KHOA_THEO_BRAND = {
    "donniechublog": "MOAT_PUBLISH_KEY",
    "dcgr": "MOAT_PUBLISH_KEY_DCGR",
}
MAC_DINH_BRAND = "donniechublog"
KHOA_MAC_DINH = "MOAT_PUBLISH_KEY"


def ten_khoa(brand=None):
    """Ten bien moi truong chua khoa cua thuong hieu nay."""
    return KHOA_THEO_BRAND.get(brand or MAC_DINH_BRAND, KHOA_MAC_DINH)


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
    key = os.environ.get(ten_khoa(brand)) or ""
    if not base or not key:
        return None, None
    return base, key


def draft_path(draft_id):
    return DRAFTS / (draft_id + ".json")


def read_draft(draft_id):
    return json.loads(draft_path(draft_id).read_text(encoding="utf-8"))


def write_draft(draft_id, data):
    draft_path(draft_id).write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


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

    out = []
    for s in srcs:
        if not isinstance(s, str) or not s:
            continue
        if s.startswith("http"):
            out.append({"url": s})
            continue
        f = Path(s)
        if not f.exists():
            continue
        mime = MIME_BY_SUFFIX.get(f.suffix.lower(), "image/png")
        out.append({"base64": base64.b64encode(f.read_bytes()).decode("ascii"),
                    "mime": mime})
    # Moat nhan toi da 10 anh mot bai; gui 11 la ca bai bi tu choi.
    return out[:MAX_ANH]


def intake(draft_id, scheduled_at=None):
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
    brand = d.get("brand") or MAC_DINH_BRAND
    base, key = config(brand)
    if not base:
        return False, ("chua cau hinh MOAT_BASE_URL/" + ten_khoa(brand)
                       + " cho thuong hieu " + brand)

    if isinstance(d.get("moat"), dict) and d["moat"].get("workflow_id"):
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
    cap = d.get("caption") or ""
    if len(cap) > TRAN_NEN_TANG:
        return False, (f"caption {len(cap)} ky tu, vuot tran {TRAN_NEN_TANG} cua "
                       f"Instagram/TikTok (thua {len(cap) - TRAN_NEN_TANG}). "
                       "Rut ngan roi day lai.")

    images = images_payload(d)
    if not images:
        return False, "khong tim thay anh de day"

    body = {
        "externalId": draft_id,
        "title": (d.get("caption") or "")[:80],
        "caption": d.get("caption") or "",
        "sourceUrl": d.get("source_url") or "",
        "images": images,
        "platforms": PLATFORMS,
    }
    if scheduled_at:
        body["scheduledAt"] = scheduled_at

    try:
        with httpx.Client(timeout=TIMEOUT) as c:
            r = c.post(base + "/publish-intake", json=body,
                       headers={"X-API-Key": key})
    except Exception as e:                                   # noqa: BLE001
        return False, "khong goi duoc moat: " + type(e).__name__ + ": " + str(e)

    if r.status_code not in (200, 201):
        return False, "moat tra HTTP " + str(r.status_code) + ": " + r.text[:200]

    out = r.json()
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
    n = len(out.get("tasks", []))
    return True, "da xep " + str(n) + " task publish"


def _fetch_status(base, key, ref):
    """`ref` nen la workflow_id: ben moat do la khoa chinh, con external_id phai
    quet bang workflows. Chay moi phut thi khac biet do tich lai."""
    with httpx.Client(timeout=TIMEOUT) as c:
        r = c.get(base + "/publish-intake/" + ref, headers={"X-API-Key": key})
    if r.status_code != 200:
        raise RuntimeError("HTTP " + str(r.status_code) + ": " + r.text[:200])
    return r.json().get("tasks", [])


def poll():
    """Hoi moat trang thai cac bai da day, tra ve list dong thong bao moi.

    Chi bao MOT lan cho moi task: trang thai da bao duoc ghi vao draft, nen
    cron chay 10 phut mot lan khong bien thanh may spam.
    """
    if not base_url():
        return []

    lines = []
    for path in sorted(DRAFTS.glob("*.json")):
        if path.name.endswith(".meta.json"):
            continue
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            continue
        moat = d.get("moat")
        if not isinstance(moat, dict) or not moat.get("external_id"):
            continue
        if moat.get("tracking_stopped"):
            continue
        reported = moat.get("reported") or {}
        if reported and all(v in TERMINAL for v in reported.values()) \
                and len(reported) >= len(moat.get("platforms") or PLATFORMS):
            continue

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
            path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            if pending:
                lines.append("⏳ " + path.stem + ": còn " + str(len(pending))
                             + " task chưa đăng sau " + str(MAX_TRACK_DAYS)
                             + " ngày, ngừng theo dõi, xem lại extension")
            continue

        # Hoi dung cai org da day bai nay len. Bai day tu truoc khi tach org
        # khong co khoa "brand" — roi ve mac dinh, tuc dung khoa cu.
        base, key = config(moat.get("brand") or d.get("brand"))
        if not base:
            # Khoa cua thuong hieu nay bi go khoi .secrets.env SAU khi da day.
            # Khong hoi duoc thi im: cron chay moi phut, canh bao o day la
            # 1440 dong rac mot ngay.
            continue

        try:
            tasks = _fetch_status(base, key, moat.get("workflow_id") or moat["external_id"])
        except Exception as e:                               # noqa: BLE001
            # Chi bao MOT lan cho moi loai loi. Cron chay moi phut: moat sap
            # 6 tieng ma bao moi lan la 360 tin rac vao topic Quinn. Nho loai
            # loi da bao trong draft; loi doi (DNS -> timeout) thi bao lai,
            # het loi thi xoa co de lan sap sau con bao.
            loi_moi = type(e).__name__
            if moat.get("loi_da_bao") != loi_moi:
                moat["loi_da_bao"] = loi_moi
                d["moat"] = moat
                path.write_text(json.dumps(d, ensure_ascii=False, indent=2),
                                encoding="utf-8")
                lines.append("⚠️ " + path.stem + ": khong hoi duoc moat ("
                             + loi_moi + "), se im cho toi khi tinh hinh doi")
            continue
        if moat.pop("loi_da_bao", None):
            d["moat"] = moat
            path.write_text(json.dumps(d, ensure_ascii=False, indent=2),
                            encoding="utf-8")
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
            else:
                line = "⏹ " + path.stem + " " + label + ": " + status
            lines.append(line)

        if changed:
            moat["reported"] = reported
            d["moat"] = moat
            path.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")

    return lines


SPOOL = STATE_DIR / "moat_chua_bao.json"


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
        tp = STATE_DIR / "topics.json"
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
            sys.exit("chua cau hinh MOAT_BASE_URL/" + ten_khoa(brand))
        print(json.dumps(_fetch_status(base, key, sys.argv[2]), ensure_ascii=False, indent=2))
        sys.exit(0)
    out = poll()
    _notify(out)
    # Khong co gi moi thi IM HAN (stdout rong). Cron chay moi phut, ma hermes ghi
    # moi ban stdout thanh mot file, in "khong co thay doi" la 1440 file rac/ngay.
    if out:
        print("\n".join(out))
