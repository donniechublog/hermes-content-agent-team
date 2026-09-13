#!/usr/bin/env python3
"""image_rules.py — BO TIEU CHI ANH DUNG CHUNG cho moi vai lam anh.

Ong Chu chot 04/09/2026: lam MOT bo tieu chi chung thay vi moi vai mot bo.

DUONG CAT — mot cau:
    "Anh nay co DUOC DUNG khong"      -> CHUNG, nam o day.
    "Dat no LEN KHUNG the nao"        -> RIENG tung vai, o lai renderer.

Vi sao phai chung (so lieu thuc do 04/09/2026 trong repo nay):

    Cong chan          card.py(Ethan)  carousel.py(Dre)  deck.py(Itachi)
    mat nguoi              khong            co               khong
    dau vet crop           khong            co               khong
    anh trung              khong            co               khong
    chart nguyen ven       khong            co               khong

Moi luat doi bang may ngay bat loi deu chi nam trong DUNG MOT tep, va nam o do
khong phai vi thiet ke ma vi do la cho Ong Chu bat loi. Khong co ly do nao de
"khong dung mat nguoi la" dung voi Dre ma khong dung voi Ethan hay Itachi.

Gia cua viec chia le da tra roi: trong cung mot ngay, hai phien lam hai lan
cung mot viec "nhan dien chart", va mot ban ra ket qua sai (bo sot chinh cai
chart gay ra su co K2 Horizon).

CACH DUNG: moi ham `kiem_*` tra ve (loi, canh_bao) — hai danh sach chuoi. Vai
tu chon cong nao hop voi khung cua minh roi gop lai. Khong ham nao ve gi, khong
ham nao biet den canvas — de vai nao cung goi duoc.
"""
import re
import sys
import threading
from pathlib import Path

from PIL import Image, ImageOps, ImageStat

# ---- Cum dung CHUNG cho MOI cau hoi con mat (LOW-45, 13/09/2026) -----------
#
# Ong Chu: "bộ logo của Moonshot hay hình ảnh nhà sáng lập khó kiếm lắm hay sao
# mà phải dùng cờ China?" — do that: mot anh bao Getty chup nghieng man hinh
# App Store cua Kimi K3 (nen mo/bokeh, chu net) lot qua BA duong khac nhau
# (`_lay_anh_trang`'s JS_FIG, `_vong_chup_nguon`, VA `anh_thuong_hieu.
# cau_hoi_vision` nhanh "anh bo canh") truoc khi bi chan dung ca ba — vi moi
# nhanh tu viet lai dieu kien "khong mo/nhoe" theo cach rieng, khong dong bo.
# MOT cum duy nhat, moi cau hoi con mat chen vao ve "khong =" cua no.
IMAGE_PHRASES_SCREENSHOT = (
    "HOAC la anh chup LAI mot man hinh dien thoai/may tinh bang MAY ANH KHAC "
    "(thay duoc vien man hinh, phan chieu anh sang, hoac nen phia sau man hinh "
    "bi mo/out-of-focus trong khi chu/hinh tren man hinh net) thay vi anh xuat "
    "truc tiep tu web/thiet ke — loai nay du doc duoc chu/logo tren man hinh "
    "van tinh la khong, vi la anh chup thu cap chu khong phai anh goc"
)

# ---- Nguong (do thuc tren kho anh cua doi, xem chu thich tung cong) --------
TI_LE_45, TI_LE_11 = 0.8, 1.0
TOLERANCE_RATIO = 0.03            # dai hop le 4:5..1:1, nong 3%
LANDSCAPE_CLEAR = 1.4                   # anh goc >= 1.4 la NGANG ro (16:9, 3:2)
SHORT_SIDE_MIN = 1000             # duoi nguong nay phong len 1080 se mem
BRIGHT_BOTTOM_MAX = 150               # do sang trung binh 25% duoi anh (chi con dung
                                 # lam ghi chu tham khao trong chuan_bi/nhin.py,
                                 # khong con la cong chan — kiem_day_sang da bo)
CHART_FLAT = 0.85
CHART_COUNT_COLOR = 220
EMPTY_COLOR = 4                     # <= 4 mau rieng biet (sau luong hoa 5 bit) = anh rong
EMPTY_FLAT = 0.995               # ... va gan nhu 100% cap pixel ke nhau bang nhau

MARK_PNG = ("crop_ti_le", "nguon_dung")   # cac khoa metadata bao "do doi dung ra"


# ---- Dau vet xuat xu ------------------------------------------------------
def stamp_provenance(xuat_xu, **them):
    """Tra ve PngInfo mang dau `nguon_dung=<xuat_xu>` (+ cac khoa phu neu co).

    Ten tham so la `xuat_xu` chu khong phai `nguon`: `nguon` la mot trong nhung
    khoa phu hay dung nhat (nguon=ARENA.AI), de trung ten thi vo TypeError.

    Moi cong cu trong doi sinh ra anh PHAI dong dau: crop_ti_le.py, arxiv_bia.py,
    ghep doc cua carousel.py, chup_chart.py. Cong `kiem_xuat_xu` dua vao dau nay
    de phan biet "anh do doi dung ra" voi "anh cat tay bang cong cu ngoai".
    """
    from PIL.PngImagePlugin import PngInfo
    m = PngInfo()
    m.add_text("nguon_dung", str(xuat_xu))
    for k, v in them.items():
        if v is not None:
            m.add_text(str(k), str(v))
    return m


def stamp_file(duong_dan, xuat_xu, **them):
    """Mo lai mot tep PNG DA LUU va ghi dau `nguon_dung` (+ khoa phu) vao do.

    Cho cac cong cu khong luu bang PIL (playwright screenshot, cv2.imwrite,
    tai thang tu URL). Khong phai PNG thi bo qua, tra ve False — dong dau la
    viec phu, khong duoc lam hong buoc chinh.
    """
    q = Path(duong_dan)
    try:
        im = Image.open(q)
        if (im.format or "").upper() != "PNG":
            return False
        im.load()
        im.save(q, "PNG", pnginfo=stamp_provenance(xuat_xu, **them))
        return True
    except Exception:
        return False


def _text(img):
    return (getattr(img, "text", None) or img.info or {})


def read_crop_trace(img):
    """Dau vet crop_ti_le.py -> (w_goc, h_goc), hoac None."""
    m = _text(img).get("crop_ti_le")
    if not m:
        return None
    try:
        goc = [k for k in m.split(";") if k.startswith("goc=")][0][4:]
        w, h = goc.lower().split("x")
        return int(w), int(h)
    except Exception:
        return None


def allows_landscape_crop(img):
    """crop_ti_le.py co duoc phep cat BE NGANG tam nay khong (co --cat-ngang)?

    Day la mot UY QUYEN da ghi lai luc cat, tuong duong `crop_ok` khai trong
    spec — chi khac la no duoc dong dau ngay tai cho cat nen khong khai lai
    duoc. `kiem_crop_ngang` nhan ca hai."""
    return _text(img).get("crop_ti_le", "").find("cat_ngang=1") >= 0


def is_ranking_image(img):
    """Anh do xep_hang.py dung: bang xep hang chup tu nguon (co khoanh model) hoac
    the du phong. Voi tin xep hang thi DAY LA CHU THE cua tin (Ong Chu 06/09/2026),
    nen no duoc mien hai cong von cam chart len bia/hero."""
    return _text(img).get("nguon_dung") in ("chup_xep_hang", "the_xep_hang")


def is_stacked_composite(img):
    """Anh nay co phai ban GHEP DOC do doi dung ra khong."""
    return _text(img).get("nguon_dung") == "ghep_doc"


# ---- Do luong anh ---------------------------------------------------------
def measure_chart_signal(img, w=480):
    """(phang, so_mau). Thuan PIL — venv tren server khong chac co numpy.

      phang  — ti le cap pixel KE NHAU theo hang gan nhu bang nhau (lech <= 2).
               Do hoa vector (chart, bang, UI) toan mang phang voi vai buoc nhay
               dung; anh chup that thi moi pixel lech nhau mot chut.
      so_mau — so mau RIENG BIET sau khi luong hoa 5 bit/kenh. Day la phep do
               tach bach nhat: chart/screenshot dung mot bang mau tay nen ra vai
               chuc mau, anh chup that ra hang nghin.

    Thu nho bang NEAREST chu KHONG phai LANCZOS: LANCZOS lam nhoe vung phang cua
    screenshot thanh gradient, tuc la xoa dung cai dau hieu can do.

    Do tren 16 the that trong drafts/ (anh that + scrim phang, tinh huong KHO
    nhat): phang 0.31..0.95, so_mau 350..4552 — khong tam nao bi goi nham la
    chart. Chart/screenshot do duoc: phang 0.89..0.99, so_mau 42..65. Nguong dat
    giua khoang trong do va phai dung CA HAI.
    """
    h = max(1, round(img.height * w / img.width))
    v = img.convert("RGB").resize((w, h), Image.NEAREST)
    px = v.convert("L").tobytes()
    bang = tong = 0
    for y in range(h):
        r = px[y * w:(y + 1) * w]
        for i in range(w - 1):
            tong += 1
            if abs(r[i] - r[i + 1]) <= 2:
                bang += 1
    phang = bang / max(1, tong)
    mau = ImageOps.posterize(v, 5).getcolors(w * h) or []
    return phang, len(mau)


def is_chart(img):
    """`img` co phai chart / bang / screenshot / slide khong -> (bool, mo_ta).

    UOC LUONG, khong phai su that. Do thuc 04/09/2026 cho thay no BO SOT chart
    co duong mau khu rang cua: training-losses.png cua K2 Horizon ra 1176 mau
    nen bi cham la "khong phai chart", trong khi do dung la chart gay ra su co.
    Vi vay `kiem_chart` chi dung ket qua nay theo MOT CHIEU — xem chu thich o do.
    """
    phang, so_mau = measure_chart_signal(img)
    return (phang >= CHART_FLAT and so_mau <= CHART_COUNT_COLOR), \
           f"phang {phang:.0%}, chi {so_mau} mau"


# ---- ANH RAC: MOT bo tu vung cho ca ba cho -----------------------------------
#
# Truoc 06/09/2026 co BA bo tu vung "anh rac" chong lan nhau ma khac han nhau:
# `anh_bai.RAC` (favicon/avatar/1x1/gravatar/author...), `anh_chuan_bi.URL_RAC`
# (quang cao/newsletter/wordmark...), va chuoi JS `XAU` chay trong browser. Anh
# bi mot bo bat con hai bo kia cho qua, tuy no di duong nao vao — ma ba duong
# deu do vao cung mot ho anh. Gio mot bo, ba noi dung chung.
#
# Tach lam hai vi chung tra loi hai cau hoi khac nhau:
#   TU_RAC_URL  — "URL hay alt nay noi day la do trang tri" (dung o moi noi)
#   TU_RAC_DOM  — them, chi co nghia khi soi VI TRI trong DOM (class/to tien):
#                 mot tu nhu "header" trong URL khong noi len gi.
JUNK_WORDS_URL = [
    # do trang tri cua trang
    "logo", "wordmark", "favicon", "avatar", "gravatar", "author", "sprite",
    "placeholder", "default-image", "onboarding",
    # anh do 1 pixel / anh chen cho
    r"1x1", r"tracking[-_]?pixel", r"pixel\.(gif|png)", "spacer",
    # the chia se mac dinh cua trang (khong phai anh cua bai)
    "social[-_]?card", "og[-_]?default", "default[-_]?og", "share[-_]?image",
    "card[-_]?default", "banner[-_]?site", "banner",
    # quang cao
    "/ads?/", "advert", "adsystem", "doubleclick", "outbrain", "taboola",
    "sponsor", "promo", "newsletter", "subscribe",
]
JUNK_WORDS_DOM = [
    "widget", "related", "recommend", "sidebar", "aside", "nav", "footer",
    "header", "share", "social", "comment", "popup", "modal", "overlay",
    "cookie", "paywall", "icon", "ads", "gpt", "dfp",
]

# Khop tren URL/alt: khong doi ranh gioi tu, vi ten tep hay dinh lien
# ("site-logo.png", "hero_placeholder.jpg").
JUNK = re.compile("(" + "|".join(JUNK_WORDS_URL) + ")", re.I)


def _js_regex_literal(tu: list) -> str:
    """Dung `new RegExp("...", "i")` chu KHONG phai regex literal `/.../i`.

    Tu vung co `/ads?/` — dau `/` trong do dong som mot regex literal cua JS va
    ca doan script chet voi "Invalid regular expression flags". json.dumps lo
    phan thoat ky tu cho dung chuan JS.
    """
    import json as _j
    return 'new RegExp(' + _j.dumps("(^|[^a-z])(" + "|".join(tu) + ")([^a-z]|$)") + ', "i")'


def js_junk_url_pattern() -> str:
    """Regex JS cho SRC va ALT — chi tu vung URL."""
    return _js_regex_literal(JUNK_WORDS_URL)


def js_junk_dom_pattern() -> str:
    """Regex JS cho CLASS/ID va to tien — tu vung URL cong tu vung DOM.

    Tach khoi `js_rac_url` (06/09/2026) vi ban cu ap CUNG mot bo cho ca hai, ma
    bo do chua "gpt" (Google Publisher Tag) va "icon" — nen moi anh co "gpt"
    trong URL bi bo, tuc DUNG cac anh ve GPT-4/GPT-5, va "silicon" dinh "icon".
    Trong class cua mot the div thi "gpt" van la quang cao; trong ten tep anh
    thi khong.
    """
    return _js_regex_literal(JUNK_WORDS_URL + JUNK_WORDS_DOM)


# ---- NGUONG CHON/TAI ANH -----------------------------------------------------
# Ba con so cho ba buoc KHAC NHAU, de canh nhau cho khoi tuong chung mau thuan:
SHORT_SIDE_DOWNLOAD = 500        # buoc TAI (anh_chuan_bi): duoi muc nay khong buon tai
AREA_DOWNLOAD = 120_000    # buoc XEP HANG ung vien (anh_bai): ~350x350
TAI_W_MIN, TAI_H_MIN = 600, 350   # buoc DOC DOM: bo anh nho ngay trong trang
# CANH_NGAN_MIN (o duoi) la nguong CANH BAO luc NOP, khong phai luc tai: anh 700px
# van co the la tam duy nhat co that, chan cung se mat tin.


def dhash(im) -> int:
    """Difference hash 8x8: hai anh cung noi dung (khac co, khac nen, JPEG lai)
    cho hash gan nhau. Dung de bat "dung lai anh" ma khong can trung byte."""
    g = im.convert("L").resize((9, 8), Image.LANCZOS)
    px = list(g.getdata())
    return sum(((px[r * 9 + c] > px[r * 9 + c + 1]) << (r * 8 + c))
               for r in range(8) for c in range(8))


def is_near_duplicate(h1: int, h2: int, nguong: int = 6) -> bool:
    return bin(h1 ^ h2).count("1") <= nguong


# Nguong dHash CHAT cho anh DO HOA (chart, bang, screenshot UI).
#
# dHash 8x8 doc BO XUONG BO CUC: sang/toi cua 64 cap pixel ke nhau. Anh chup
# that co nhieu tu nhien nen hai tam khac nhau cach nhau hang chuc bit — do
# cheo 16 slide that trong drafts/: 0/120 cap va cham. Do hoa vector thi khong
# co nhieu do: hai bieu do cot HOAN TOAN khac so lieu, mien la cung dang di
# xuong, chi cach nhau 5 bit; hai bang xep hang khac noi dung cach 4 bit. Voi
# nguong chung 6 thi chart THAT cua bai (bang chung manh nhat) bi bao "TRUNG
# anh da dung", vai lang le doi sang anh minh hoa yeu hon — dau ra xau di ma
# khong ai thay (06/09/2026).
#
# Bien rat mong chu khong an toan: cung do, colA vs colE = 7 — hon nguong dung
# mot bit. Nen voi anh do hoa chi coi la trung khi gan nhu y het.
THRESHOLD_GRAPHIC = 2


def _file_md5(duong_dan) -> str:
    """md5 cua TEP — bat chinh xac ca truong hop tai lai cung mot tap tin."""
    import hashlib
    try:
        return hashlib.md5(Path(duong_dan).read_bytes()).hexdigest()
    except OSError:
        return ""


def dhash_threshold_for(im, nguong=6) -> int:
    """Nguong dHash hop voi LOAI anh: do hoa thi phai chat hon nhieu (xem
    NGUONG_DO_HOA). Dung chung o buoc NOP (kiem_da_dung) va buoc TAI
    (anh_chuan_bi khu trung ung vien)."""
    try:
        return THRESHOLD_GRAPHIC if is_chart(im)[0] else nguong
    except Exception:                                        # noqa: BLE001
        return nguong


DATE_SMALL_IMAGE = 14      # cua so nho anh da dung, xem kiem_da_dung


def _used_images_log():
    """state/<brand>/anh_da_dung.jsonl — moi dong mot anh da GUI DI (khong phai
    ung vien). Ghi o buoc gui album, doc o buoc nop."""
    import env_load
    return env_load.state_dir() / "anh_da_dung.jsonl"


def story_key(link: str) -> str:
    """Khoa on dinh cua MOT TIN (khong phai mot draft).

    Cung mot tin giao cho Dre roi giao cho Ethan ra HAI draft_id khac nhau
    (duyet_chon_tin._draft_id ghep them vai-brand) nhung van la MOT tin va dung
    CHUNG bo anh engine tai ve. So "anh da dung" khoa theo draft thi vai nop sau
    bi chan sach anh cua vai truoc — do 06/09/2026: Ethan mat toan bo 5-6 ma Dre
    da dung, khong nop duoc the nao."""
    import re as _re
    u = _re.sub(r"^https?://(www\.)?", "", (link or "").strip().lower()).rstrip("/")
    return _re.sub(r"[?#].*$", "", u)


def record_used(duong_dan, draft_id: str, vai: str, link: str = "") -> None:
    import json, time
    q = Path(duong_dan)
    try:
        with Image.open(q) as im:
            h = dhash(im)
    except Exception:                                        # noqa: BLE001
        return
    dong = {"dhash": h, "draft_id": draft_id, "vai": vai, "tin": story_key(link),
            "ten": q.name, "md5": _file_md5(q), "luc": int(time.time())}
    with open(_used_images_log(), "a", encoding="utf-8") as f:
        f.write(json.dumps(dong, ensure_ascii=False) + "\n")


def remove_used_for_draft(draft_id: str) -> int:
    """Go moi dong cua mot draft khoi so "anh da dung". Tra so dong da go.

    So duoc ghi o buoc GUI album, tuc TRUOC khi Ong Chu bam nut. Bam "Bo han
    tin" hay "Lam lai" thi bai chet / album bi thay, anh KHONG bao gio len
    kenh — nhung truoc 06/09/2026 chung van nam trong so va chan moi bai khac
    suot 14 ngay. Voi cac tin cung chu de (cung anh wire Reuters/AP, cung anh
    tru so hang) thi bai sau bi day sang anh kem hon, hoac tac han neu tam bi
    khoa la anh that duy nhat — ma thong bao chan chi noi ten bai va cham, KHONG
    noi bai do da bi bo.
    """
    import json
    so = _used_images_log()
    if not so.exists():
        return 0
    dong = so.read_text(encoding="utf-8").splitlines()
    giu = []
    for d in dong:
        try:
            giu.append(d) if json.loads(d).get("draft_id") != draft_id else None
        except Exception:                                    # noqa: BLE001
            giu.append(d)                                    # dong hong: giu nguyen
    if len(giu) == len(dong):
        return 0
    tmp = so.with_suffix(".jsonl.tmp")
    tmp.write_text(("\n".join(giu) + "\n") if giu else "", encoding="utf-8")
    tmp.replace(so)
    return len(dong) - len(giu)


def check_not_reused(nhan, duong_dan, draft_id: str, link: str = ""):
    """KHONG DUNG LAI ANH DA DUNG (Ong Chu chot 06/09/2026): bang ti so giai golf
    Ricoh len hai the cua hai tin khac nhau trong cung mot ngay.

    So theo dHash (gan giong <= 6 bit) chu khong theo ten/byte, vi cung mot tam
    tai lai tu bao khac se khac byte. Bo qua chinh draft nay (lam lai mot bai thi
    duoc giu anh). Cua so NGAY_NHO_ANH — "trong phien" hieu la vai tuan gan day:
    nguoi doc kenh nho anh lau hon mot ngay.
    """
    import json, time
    so = _used_images_log()
    if not so.exists():
        return [], []
    try:
        with Image.open(duong_dan) as im:
            h = dhash(im)
    except Exception:                                        # noqa: BLE001
        return [], []
    # MIEN TRU ANH XEP HANG. Voi tin xep hang, BANG chinh la chu the: hai bai ve
    # hai model cung nam trong top mot bang se chup dung dai hang do, chi khac
    # khung khoanh vang — dHash coi la trung. Luc do cong nay chan anh XH, con
    # cong "TIN XEP HANG phai dung anh XH" o dre_nop/ethan_nop lai chan moi anh
    # KHAC: hai loi loai tru nhau, vai sua kieu gi cung sai roi tac (do
    # 06/09/2026). Lap lai bang xep hang la DUNG, khong phai loi.
    try:
        with Image.open(duong_dan) as _im:
            if is_ranking_image(_im):
                return [], []
    except Exception:                                        # noqa: BLE001
        pass
    moc = time.time() - DATE_SMALL_IMAGE * 86400
    tin = story_key(link)
    # Nguong theo LOAI anh (xem NGUONG_DO_HOA). md5 van chan tuyet doi: cung
    # mot tap tin thi trung that, khong can doan theo hinh.
    try:
        with Image.open(duong_dan) as _im:
            nguong = dhash_threshold_for(_im)
    except Exception:                                        # noqa: BLE001
        nguong = 6
    ma = _file_md5(duong_dan)
    for line in so.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
        except Exception:                                    # noqa: BLE001
            continue
        if d.get("draft_id") == draft_id or d.get("luc", 0) < moc:
            continue
        # Cung MOT TIN nhung vai khac (Dre roi Ethan) thi KHONG chan: hai vai
        # dung chung bo anh cua bai do, chan la vai sau khong con anh nao.
        if tin and d.get("tin") and d["tin"] == tin:
            continue
        if (ma and d.get("md5") == ma) or is_near_duplicate(int(d.get("dhash", 0)), h, nguong):
            khi = time.strftime("%d/%m %H:%M", time.localtime(d.get("luc", 0)))
            return [f"{nhan}: TRUNG anh da dung o bai '{d.get('draft_id')}' ({d.get('vai')}, {khi}) — "
                    "moi tin mot anh, nguoi doc kenh nhan ra anh lap lai ngay. Tim anh khac."], []
    return [], []


def tone_mismatch(ims, nguong_sang=60, nguong_mau=70):
    """Hai anh ghep chung khung ma TONE lech nhau nhieu thi doc ra nhu HAI VUNG
    rieng biet (Ong Chu chot 03/09/2026, siet thanh cong chan 04/09)."""
    ds = []
    for im in ims:
        nho = im.resize((64, 64))
        ds.append((ImageStat.Stat(nho.convert("L")).mean[0],
                   ImageStat.Stat(nho).mean))
    ra = []
    for i in range(len(ds) - 1):
        (l1, c1), (l2, c2) = ds[i], ds[i + 1]
        d_sang = abs(l1 - l2)
        d_mau = sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5
        if d_sang > nguong_sang or d_mau > nguong_mau:
            ra.append(f"anh {i+1} va {i+2} lech tone (sang {l1:.0f} vs {l2:.0f}, "
                      f"mau lech {d_mau:.0f}) — hai vung nhin tach roi; uu tien "
                      "hai anh CUNG tone (cung nen sang/toi, cung gam mau)")
    return ra


_YUNET = None
_YUNET_DA_THU = False
_YUNET_LOCK = threading.Lock()
FACE_EDGE_MAX = 1600            # canh dai nhat dua vao YuNet; lon hon thi thu nho (LOW-27)


def _load_yunet():
    """Nap lazy model YuNet, dung mot lan cho ca doi tien trinh.

    Khoa bang _YUNET_LOCK (audit_content_team B2): `phan_loai` gio duoc
    anh_chuan_bi._nhin_anh goi tu nhieu luong cung luc qua ThreadPoolExecutor.
    Khong khoa thi luong A dat _YUNET_DA_THU=True TRUOC khi gan xong _YUNET —
    `import cv2` va doc file .onnx o giua co the nha GIL — nen luong B doc co
    thay True nhung _YUNET con None, tra ve None nham nhu may thieu cv2/model
    du thuc ra co day du. Hau qua im lang: dem_mat() bao 0 mat, cong mat nguoi
    (LUAT_ANH §6) tu tat theo may rui thu tu luong thay vi theo may that su co
    cv2 hay khong.
    """
    global _YUNET, _YUNET_DA_THU
    if _YUNET_DA_THU:
        return _YUNET
    with _YUNET_LOCK:
        if _YUNET_DA_THU:             # luong khac vua nap xong trong luc cho khoa
            return _YUNET
        try:
            import os as _os
            _os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
            import cv2
            m = Path(__file__).resolve().parent / "assets" / \
                "face_detection_yunet_2023mar.onnx"
            if m.exists():            # thieu model -> bo qua cong, khong crash build
                _YUNET = cv2.FaceDetectorYN_create(str(m), "", (320, 320),
                                                   score_threshold=0.7)
        except Exception:
            _YUNET = None
        _YUNET_DA_THU = True          # dat SAU CUNG, sau khi _YUNET da co gia tri chot
    return _YUNET


def count_faces(path):
    """So mat nguoi trong anh. None neu khong chay duoc (thieu cv2/model).

    setInputSize + detect PHAI nam trong _YUNET_LOCK (audit lượt 2, B-r2-1):
    khoa o _yunet() chi bao ve luc NAP model, con mot FaceDetectorYN dung chung
    thi khong thread-safe khi DUNG — luong A vua setInputSize((w1,h1)) thi luong
    B setInputSize((w2,h2)) roi A detect() voi kich thuoc sai -> cv2 nem -> None.
    Do duoc voi 24 anh khac co, 4 luong: tuan tu 0/24 None, song song 22-23/24;
    nhin.py lam `or 0` nen 80-95% anh bi coi la KHONG co mat — cong mat nguoi
    (LUAT_ANH §6) tat cam. detect() nhanh (vai ms), khong can song song.
    """
    det = _load_yunet()
    if det is None:
        return None
    try:
        import cv2
        im = cv2.imread(str(path))
        if im is None:
            return None
        h, w = im.shape[:2]
        # THU NHO truoc khi do (LOW-27, 12/09/2026): YuNet SIGSEGV (exit 139, khong
        # ngoai le Python nao bat duoc) voi anh 9440x5310 — do tung anh trong tien
        # trinh rieng tren may chu: 7/8 anh cua draft t_24b214a6 ok, A2.png 50MP
        # chet -11 ngay ca khi chay MOT MINH. Tu do ca engine chet, khoa mo coi,
        # vai chay lai 16 lan. Model dung o 320px nen thu ve MAT_CANH_MAX khong
        # mat mat nao dang ke; INTER_AREA de thu nho khong ra rang cua.
        if max(h, w) > FACE_EDGE_MAX:
            ty = FACE_EDGE_MAX / max(h, w)
            im = cv2.resize(im, (max(1, int(w * ty)), max(1, int(h * ty))),
                            interpolation=cv2.INTER_AREA)
            h, w = im.shape[:2]
        with _YUNET_LOCK:
            det.setInputSize((w, h))
            _n, res = det.detect(im)
        return 0 if res is None else len(res)
    except Exception as e:                                   # noqa: BLE001
        print(f"[mat] {Path(path).name}: {type(e).__name__}: {e!r}", file=sys.stderr)
        return None


# ---- Cong chan: moi ham tra ve (loi, canh_bao) ----------------------------
def is_blank_image(img):
    """Anh co RONG khong (trang tron / mot mau phang) -> (bool, mo_ta).

    Bo Broadcom dcgr 04/09/2026: buoc chup tra ve anh trang tron (2 mau, phang
    100%), khong cong nao bat, ra mot slide trong tron chi co chu. Tro treu:
    anh trang la thu "giong chart" NHAT theo do_chart, nen cong chart cho qua.

    Do tren 76 anh trong kho: anh rong = 2 mau; anh that it mau nhat = 40 mau
    (screenshot UI toi hai tone). Cach nhau 20 lan nen nguong 4 la an toan —
    khac han cac phep do "slide trong" da thu va bo (chung chong lan voi chart
    sach). Day la RONG thuc su, khong phai "thua".
    """
    ph, mau = measure_chart_signal(img)
    return (mau <= EMPTY_COLOR and ph >= EMPTY_FLAT), f"{mau} mau, phang {ph:.0%}"


def check_blank_image(nhan, img):
    """Anh rong (trang tron / mot mau) -> CHAN. Goi TRUOC kiem_chart, neu khong
    thong bao se la "chart thieu co" thay vi "anh khong co gi"."""
    rong, mo_ta = is_blank_image(img)
    if rong:
        return [f"{nhan}: anh RONG ({mo_ta}) — khong co noi dung nao de hien. "
                "Thuong la buoc chup tra ve trang trang (trang chua render, "
                "selector bat nham phan tu rong, hoac tai ve tep hong). Mo anh "
                "ra XEM truoc khi ghi vao spec; chup lai bang chup_chart.py "
                "hoac chon anh khac."], []
    return [], []


def check_chart_integrity(nhan, img, khai_chart, la_bia=False):
    """Chart phai NGUYEN VEN va FULL BE NGANG (Ong Chu chot 04/09/2026).

    CONG NAY MOT CHIEU, co chu y:

      - THIEU co ma may nhan ra la chart  -> CHAN. Sai thi vai khai them co,
        gia rat re.
      - CO co ma may khong nhan ra chart  -> CANH BAO, khong chan. Vi `la_chart`
        bo sot that: bo K2 Horizon lam DUNG (chart goc + "chart": true) tung bi
        chan sach voi ly do "anh khong phai chart (1176 mau)", va thong bao con
        bao vai "bo co di va cat ve 1:1/4:5" — tuc chi thang vao dung cai sai da
        gay ra su co. Chan o chieu nay la giet viec dung.

    Anh GHEP DOC duoc mien han: no da nguyen ven va full be ngang san.
    """
    loi, canh_bao = [], []
    if is_stacked_composite(img) or is_ranking_image(img):
        return loi, canh_bao
    la_ct, mo_ta = is_chart(img)
    if la_ct and not khai_chart:
        if la_bia:
            loi.append(f"{nhan}: BIA la chart/screenshot ({mo_ta}). Bia co hook de "
                       "len anh nen chart nam duoi chu, doc khong ra. Ghep DOC hai "
                       'anh ngang cung tone ("images": [a, b]), hoac de chart o '
                       'SLIDE THAN voi "chart": true va tim anh khac lam bia.')
        else:
            loi.append(f"{nhan}: anh nay LA CHART/SCREENSHOT ({mo_ta}) ma slide "
                       'khong khai "chart": true. Them co do vao slide — anh se '
                       "duoc dan FULL BE NGANG NGUYEN VEN (khong crop, khong ep "
                       "ti le). Do la duong duy nhat giu tron tieu de, truc va "
                       "nhan cua chart.")
    elif khai_chart and not la_ct and not la_bia:
        canh_bao.append(f"{nhan}: khai \"chart\": true nhung may khong nhan ra la "
                        f"chart ({mo_ta}) — phep do nay bo sot chart co duong mau "
                        "khu rang cua, nen neu dung la chart thi CU DE CO. Chi xem "
                        "lai neu day thuc su la anh chup thuong.")
    return loi, canh_bao


def check_chart_standalone(nhan, img, da_ghep=False):
    """Chart di MOT MINH vao mot khung dat CHU DE LEN anh phu kin -> CHAN.

    Khac `kiem_chart` (do la chuyen khai co "chart": true cho slide than). Cong
    nay danh cho khung kieu hero/bia: anh phu kin va mot man toi an ~40% day de
    chu doc duoc. Chart nam mot minh o do la mat nua duoi cua chinh no — truc x,
    chu thich, dong nguon. Chart phai NGUYEN VEN va TRAI FULL BE NGANG.

    Anh GHEP DOC duoc mien: chart nam nua tren con nguyen, anh thu hai o duoi
    chiu man toi. Do la duong ra, khong phai vi pham.
    """
    if da_ghep or is_stacked_composite(img) or is_ranking_image(img):
        return [], []
    la_ct, mo_ta = is_chart(img)
    if not la_ct:
        return [], []
    return ([f"{nhan}: CHART DI MOT MINH vao khung co chu de len anh ({mo_ta}). "
             "Nua duoi cua chart chim han duoi man toi: mat truc x, chu thich, "
             "dong nguon. Ba duong ra: (1) tim them mot anh ngang CUNG TONE roi "
             "ghep DOC (card.py --image2 / carousel \"images\": [a, b]) — chart "
             "nam nua tren con nguyen; (2) de chart cho slide than voi "
             "\"chart\": true, o do no duoc dan full be ngang nguyen ven; "
             "(3) doi anh khac lam hero (nguoi, thiet bi, hien truong) va van "
             "dan chart o slide than."], [])


def check_aspect_ratio(nhan, p, w, h, lo=TI_LE_45, hi=TI_LE_11, dung_sai=TOLERANCE_RATIO, img=None):
    """Anh phai nam trong dai 4:5..1:1 (anh ghep doc roi vao giua dai nay).

    MIEN TRU anh xep hang, y nhu kiem_chart/kiem_chart_mot_minh da mien: voi tin
    xep hang thi bang la CHU THE cua tin, duoc dan full be ngang nguyen ven ke ca
    o bia. Truoc 06/09/2026 cong nay khong mien, nen Dre ket hai dau: cong cua
    dre_nop BAT BUOC bia la anh XH, con carousel lai chan chinh anh do vi ti le
    (bang desktop hay ra 1.1-1.5, bang chup khung mobile ra 0.3-0.5; ca hai deu
    ngoai dai 4:5..1:1). Tro treu la chi THE DU PHONG (1200x1500 = 0.8) lot qua."""
    r = w / h
    if lo - dung_sai <= r <= hi + dung_sai:
        return [], []
    if img is not None and is_ranking_image(img):
        return [], []
    if r >= LANDSCAPE_CLEAR:
        # Anh NGANG: crop_ti_le tu choi cat be ngang (can --cat-ngang), va cat
        # be ngang cung la sai huong — mat truc/nhan/cot cuoi. Dan thang sang
        # hai duong dung, dung goi y crop truoc.
        return [f"{nhan}: ti le {w}x{h} ({r:.2f}) khong nam trong 4:5..1:1. Anh "
                f"NGANG thi KHONG cat be ngang: (a) tim them mot anh ngang cung "
                f'tone roi ghep doc, ghi "images": [a, b]; hoac (b) chart/bang '
                f'benchmark thi ghi "chart": true de hien full be ngang nguyen ven '
                f"(slide than). Chi khi la anh chup nguoi/san pham KHONG co chu moi "
                f"duoc cat be ngang: crop_ti_le.py --anh {p} --ra <ra.png> "
                f"--ti-le 4:5 --cat-ngang"], []
    return [f"{nhan}: ti le {w}x{h} ({r:.2f}) khong nam trong 4:5..1:1 — cat "
            f"truoc: venv/bin/python crop_ti_le.py --anh {p} --ra <ra.png> "
            f"[--ti-le 4:5] [--cx/--cy]"], []


def check_crop_landscape(nhan, img, w, h, crop_ok=None):
    """Anh goc NGANG ma di qua crop_ti_le.py -> CHAN (Ong Chu bat loi 03/09/2026).

    Chart / bang / slide bi crop ve 4:5 la mat tieu de, mat truc, doc ra vo nghia.
    Chi anh chup nguoi/san pham KHONG co chu moi duoc crop, va co hai cach uy
    quyen: khai "crop_ok" trong spec, HOAC cat bang `crop_ti_le.py --cat-ngang`
    (co do dong dau vao PNG, xem `doc_cat_ngang`).
    """
    goc = read_crop_trace(img)
    if goc and goc[0] / goc[1] >= LANDSCAPE_CLEAR and not crop_ok and not allows_landscape_crop(img):
        return [f"{nhan}: anh goc NGANG {goc[0]}x{goc[1]} da bi crop ve {w}x{h} — "
                "bang/chart/slide/banner co tieu de PHAI NGUYEN VEN, khong crop. "
                'Tim them mot anh ngang cung tone, ghi "images": [a, b] de ghep '
                "doc. Chi anh chup nguoi/san pham KHONG co chu moi duoc crop: "
                'ghi "crop_ok": "<ly do>" vao slide.'], []
    return [], []


def check_resolution(nhan, w, h):
    """Canh ngan < 1000px thi phong len 1080 se mem. Canh bao, khong chan —
    anh doc quyen nho van hon anh sai."""
    if min(w, h) < SHORT_SIDE_MIN:
        return [], [f"{nhan}: canh ngan {min(w, h)}px < {SHORT_SIDE_MIN} — phong len "
                    "1080 se hoi mem, co ban to hon thi thay"]
    return [], []


def check_unnamed_face(nhan, path, nhan_vat=None):
    """Khong dung anh mot nguoi VO DANH (Ong Chu bat loi 03/09/2026).

    Code chi bao co mat hay khong; vai tu chiu trach nhiem nguoi do co phai
    nhan vat trong bai khong. Co mat la CHAN, tru khi khai "nhan_vat".
    """
    n = count_faces(path)
    if n is None:
        return [], [f"{nhan}: khong kiem duoc mat nguoi (thieu cv2/model hoac anh "
                    "loi khi doc) -- can soat tay truoc khi dung anh nay"]
    if not n:
        return [], []
    nv = str(nhan_vat or "").strip()
    if nv:
        return [], [f"{nhan}: {n} mat nguoi, khai la '{nv}' — OK neu dung la nguoi "
                    "do; sai ten la bia dat."]
    return [f"{nhan}: phat hien {n} mat nguoi ma KHONG khai nhan vat. Anh nguoi vo "
            "danh / khong lien quan tin la loi (doc ra la stock). Doi sang anh san "
            "pham/screenshot/chart; con neu dung la nhan vat trong bai (CEO phat "
            "bieu, tac gia paper) thi khai ten — carousel/deck: \"nhan_vat\": "
            "\"<ten>\" trong slide; card.py (hero): --nhan-vat \"<ten>\"."], []


def check_duplicate(nhan, path, da_thay):
    """Moi slide mot hinh DUY NHAT. Bat theo NOI DUNG tep (hash), khong theo ten.

    Han che da biet: hai CROP khac nhau cua cung mot tam thi hash khac — cai do
    van phai nho mat nguoi soi.
    """
    import hashlib
    h = hashlib.md5(Path(path).read_bytes()).hexdigest()
    if h in da_thay:
        return [f"{nhan}: trung anh voi {da_thay[h]} — moi slide phai mot hinh "
                "DUY NHAT, tim anh khac"], []
    da_thay[h] = nhan
    return [], []
