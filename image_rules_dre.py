#!/usr/bin/env python3
"""image_rules_dre.py — BO TIEU CHI ANH RIENG CUA DRE (`carousel`, `carousel.py`).

LOW-182 (16/09/2026): Ong Chu dao nguoc quyet dinh 04/09/2026 ("lam MOT bo tieu
chi chung thay vi moi vai mot bo") — tach `image_rules.py` dung chung thanh MOT
BAN RIENG cho moi vai lam anh (Ethan/Dre/Kite), bat dau tu dung noi dung ban
chung tai thoi diem tach (khong mat luat dang co). Tu day ba ban la BA TEP DOC
LAP: sua luat o day KHONG con tu dong ap sang `image_rules_ethan.py`/
`image_rules_kite.py` nua — muon dong bo thi phai tu tay sua ca ba.

Rui ro da noi ro va Ong Chu da xac nhan chap nhan (xem LOW-182): ba ban de troi
khac nhau theo thoi gian, va mot loi an toan (vd chong bia danh tinh, cam logo)
gio phai nho sua ca ba cho thay vi mot.

DUONG CAT cu van con dung — mot cau:
    "Anh nay co DUOC DUNG khong"      -> nam o day (rieng cua Dre).
    "Dat no LEN KHUNG the nao"        -> rieng vai, o lai renderer (`carousel.py`).

CACH DUNG: moi ham `kiem_*`/`check_*` tra ve (loi, canh_bao) — hai danh sach
chuoi. `carousel.py` tu chon cong nao hop voi khung cua minh roi gop lai. Khong
ham nao ve gi, khong ham nao biet den canvas.
"""
import re
import sys
import threading
from pathlib import Path

from PIL import Image, ImageOps, ImageStat

# IMAGE_PHRASES_SCREENSHOT (LOW-45, 13/09/2026) DA GO 16/09/2026 (LOW-201, dao
# LOW-45): tieu chi "trong giong chup lai man hinh" loai oan anh dung chu de
# (screenshot sach chup thang tu web). Xem prepare/vision.py cho ly do day du.

# ---- Nguong (do thuc tren kho anh cua doi, xem chu thich tung cong) --------
TI_LE_45, TI_LE_11 = 0.8, 1.0
TOLERANCE_RATIO = 0.03            # dai hop le 4:5..1:1, nong 3%
LANDSCAPE_CLEAR = 1.4                   # anh goc >= 1.4 la NGANG ro (16:9, 3:2)
# San rieng cua Dre cho anh GHEP DOC (LOW-178, 16/09/2026). Truoc do cap ghep
# phai roi dung dai 4:5..1:1 nhu anh don, nen hai anh 3:2 (= 0.75) bi loai — ma
# 3:2 la ti le pho bien nhat cua anh bao/Wikimedia: tin Samsung Taylor co bon
# anh sach deu 3:2, khong ghep duoc voi nhau, Dre block du anh dung chu de.
# `carousel._body_image` dan anh full be ngang va CAT GIUA DOC phan cao hon
# khung, nen cap cao hon 4:5 chi mat mot dai mong o mep tren anh 1 + mep duoi
# anh 2 (0.75 -> ~3% moi mep; 4:3+4:3 = 0.67 -> ~8%). Ong Chu 12/09/2026: lech
# ti le/bo cuc la LOI NHO — canh bao, khong chan. Duoi san nay (mat > ~10% moi
# mep) moi la mat noi dung that. Tran 1:1 giu nguyen: ghep RONG hon 1:1 thi nua
# duoi khung la nen, ra "hai vung" (muc 7).
STACK_FLOOR = 0.65


def ratio_after_stack(r1: float, r2: float) -> float:
    """Ti le rong/cao cua hai anh chong doc cung be ngang: 1 / (1/r1 + 1/r2)."""
    return 1 / (1 / r1 + 1 / r2)


def stack_fit_frame(r1, r2) -> bool:
    """Hai anh ti le rong/cao r1, r2 chong doc co dung duoc khong: ra
    STACK_FLOOR..1:1 (nong TOLERANCE_RATIO). MOT ban cho ca ba noi: goi y cap
    (`prepare.manifest.stackable_pairs`), cong chan (`dre_submit._resolve_stack`)
    va nguoi dem slide (`schema.count_image_use_ok`, LOW-46) — ba noi phai cung
    mot cau tra loi, khong thi nguoi dem noi "du" ma cong chan loai (LOW-46).
    Thieu ti le = khong ghep duoc."""
    r1, r2 = float(r1 or 0), float(r2 or 0)
    if r1 <= 0 or r2 <= 0:
        return False
    return STACK_FLOOR - TOLERANCE_RATIO <= ratio_after_stack(r1, r2) <= TI_LE_11 + TOLERANCE_RATIO


def stack_crop_note(r1, r2) -> str:
    """Canh bao (KHONG chan) cho cap ghep vua `stack_fit_frame` nhung cao hon
    khung 4:5: khung se cat mot dai o mep tren anh 1 va mep duoi anh 2. Rong
    neu cap roi dung dai 4:5..1:1. Tinh theo phan tram chieu cao, khong biet
    canvas."""
    rc = ratio_after_stack(float(r1), float(r2))
    if rc >= TI_LE_45 - TOLERANCE_RATIO:
        return ""
    mat = 1 - rc / TI_LE_45                     # phan chieu cao bi cat, ca hai mep
    return (f"ghép ra tỉ lệ {rc:.2f}, cao hơn khung 4:5: cắt ~{mat / 2:.0%} chiều cao ở "
            "mép trên ảnh 1 và mép dưới ảnh 2 — nếu ảnh 1 là chart/bảng có tiêu đề sát "
            "mép thì đảo thứ tự hai mã")


def _is_title_case_headline(t: str) -> bool:
    """alt la TIEU DE BAO viet hoa dau moi tu (>= 5 tu, > 60% viet hoa): regex ten
    rieng khong phan biet duoc ten nguoi voi cum "Here Following" trong do."""
    w = [x for x in re.split(r"\s+", t.strip()) if x]
    if len(w) < 5:
        return False
    return sum(1 for x in w if x[0].isupper()) / len(w) > 0.6


# Tu dung dau mot cum ten do vision/caption viet khong dau: "Anh Jensen Huang".
_NAME_PREFIX = ("anh", "ong", "ba", "ceo", "chu", "tich", "ts", "gs")


def subject_names(a: dict) -> list:
    """Ten nguoi ma CHINH tam anh mang theo, theo thu tu tin cay: nhan nguoi cua
    vong thuong hieu (`thuong_hieu.nguoi`, Wikidata founder/CEO), ten rieng trong
    `mo_ta` (vision NHIN mat va goi ten), roi ten rieng trong alt/caption.

    Do that 16/09/2026 (A18 tin Nvidia/Anthropic): alt la tieu de bao
    "Nvidia CEO Says AGI is Here Following GPT-6 Astra Launch" -> regex ten rieng
    tra "Here Following", brief in ra, Dre khai dung the va qua cong voi mot ten
    bia — trong khi mo_ta noi ro "CEO Jensen Huang". Nen: alt dang headline
    Title-Case bo qua, mo_ta duoc doc truoc. `role.person_names_in_alt` (nguoi
    dem chung) giu nguyen."""
    import role
    ra = []
    th = (a.get("thuong_hieu") or {}).get("nguoi")
    if th:
        ra.append(str(th))
    for txt in (a.get("mo_ta") or "", a.get("alt") or ""):
        if not txt or _is_title_case_headline(txt):
            continue
        for ten in role.person_names_in_alt(txt):
            w = ten.split()
            while len(w) > 2 and w[0].lower() in _NAME_PREFIX:
                w = w[1:]
            ten = " ".join(w)
            if ten not in ra:
                ra.append(ten)
    return ra


def subject_evidence(anh_ds) -> str:
    """Chuoi de doi chieu `nhan_vat` NGOAI chu bai (LOW-178, 16/09/2026): ten
    nguoi ma chinh nhung tam anh dang xet mang theo (`subject_names`).

    Truoc do ten khai phai co trong CHU BAI — bai ve Nvidia khong go "Jensen
    Huang" thi anh Jensen Huang (Wikimedia, caption ghi ro ten) bi coi la bia.
    Su co goc 05/09 (anh quan chuc G20 khai "Hock Tan") van bi chan: caption
    anh do khong co ten nay. Chi xet dung nhung tam dang khai, tam khac trong
    manifest khong bao lanh."""
    return " ".join(x for a in anh_ds for x in subject_names(a or {}))
SHORT_SIDE_MIN = 1000             # duoi nguong nay phong len 1080 se mem
BRIGHT_BOTTOM_MAX = 150               # do sang trung binh 25% duoi anh (chi con dung
                                 # lam ghi chu tham khao trong prepare/vision.py,
                                 # khong con la cong chan — kiem_day_sang da bo)
CHART_FLAT = 0.85
CHART_COUNT_COLOR = 220
EMPTY_COLOR = 4                     # <= 4 mau rieng biet (sau luong hoa 5 bit) = anh rong
EMPTY_FLAT = 0.995               # ... va gan nhu 100% cap pixel ke nhau bang nhau

# Dau vet xuat xu PNG: THUAN CO CHE, khong co nguong/phan doan nao — chuyen
# sang image_provenance.py dung chung cho moi cong cu TAO/SUA anh (ke ca
# Gin/Itachi, von di khong ap bo luat nay) khi tach `image_rules.py` (LOW-182).
from image_provenance import (       # noqa: E402
    read_crop_trace, allows_landscape_crop, is_ranking_image, is_stacked_composite,
)


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
    Vi vay `check_chart_integrity` chi dung ket qua nay theo MOT CHIEU — xem chu thich o do.
    """
    phang, so_mau = measure_chart_signal(img)
    return (phang >= CHART_FLAT and so_mau <= CHART_COUNT_COLOR), \
           f"phang {phang:.0%}, chi {so_mau} mau"


# ---- ANH RAC: MOT bo tu vung cho ca ba cho -----------------------------------
#
# Truoc 06/09/2026 co BA bo tu vung "anh rac" chong lan nhau ma khac han nhau:
# `article_images.JUNK` (favicon/avatar/1x1/gravatar/author...), `prepare.download_filter.URL_JUNK`
# (quang cao/newsletter/wordmark...), va chuoi JS `XAU` chay trong browser. Anh
# bi mot bo bat con hai bo kia cho qua, tuy no di duong nao vao — ma ba duong
# deu do vao cung mot ho anh. Gio mot bo, ba noi dung chung.
#
# Tach lam hai vi chung tra loi hai cau hoi khac nhau:
#   JUNK_WORDS_URL  — "URL hay alt nay noi day la do trang tri" (dung o moi noi)
#   JUNK_WORDS_DOM  — them, chi co nghia khi soi VI TRI trong DOM (class/to tien):
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

    Tach khoi `js_junk_url_pattern` (06/09/2026) vi ban cu ap CUNG mot bo cho ca hai, ma
    bo do chua "gpt" (Google Publisher Tag) va "icon" — nen moi anh co "gpt"
    trong URL bi bo, tuc DUNG cac anh ve GPT-4/GPT-5, va "silicon" dinh "icon".
    Trong class cua mot the div thi "gpt" van la quang cao; trong ten tep anh
    thi khong.
    """
    return _js_regex_literal(JUNK_WORDS_URL + JUNK_WORDS_DOM)


# ---- NGUONG CHON/TAI ANH -----------------------------------------------------
# Ba con so cho ba buoc KHAC NHAU, de canh nhau cho khoi tuong chung mau thuan:
SHORT_SIDE_DOWNLOAD = 500        # buoc TAI (image_prepare): duoi muc nay khong buon tai
AREA_DOWNLOAD = 120_000    # buoc XEP HANG ung vien (article_images): ~350x350
TAI_W_MIN, TAI_H_MIN = 600, 350   # buoc DOC DOM: bo anh nho ngay trong trang
# SHORT_SIDE_MIN (o duoi) la nguong CANH BAO luc NOP, khong phai luc tai: anh 700px
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
    THRESHOLD_GRAPHIC). Dung chung o buoc NOP (check_not_reused) va buoc TAI
    (image_prepare khu trung ung vien)."""
    try:
        return THRESHOLD_GRAPHIC if is_chart(im)[0] else nguong
    except Exception:                                        # noqa: BLE001
        return nguong


DATE_SMALL_IMAGE = 14      # cua so nho anh da dung, xem check_not_reused


# `_used_images_log`/`story_key`/`remove_used_for_draft` chuyen sang
# image_provenance.py (THUAN I/O, dung CHUNG ca ba vai theo thiet ke — LOW-182).
# Goi QUA TEN MODULE (khong `from ... import`) de test van patch duoc dung MOT
# cho (`image_provenance._used_images_log`) va ca ba vai deu thay ngay — patch
# rieng tung ban se lech nhau, dung cai LOW-182 dinh tranh.
import image_provenance


def record_used(duong_dan, draft_id: str, vai: str, link: str = "") -> None:
    import json, time
    q = Path(duong_dan)
    try:
        with Image.open(q) as im:
            h = dhash(im)
    except Exception:                                        # noqa: BLE001
        return
    dong = {"dhash": h, "draft_id": draft_id, "vai": vai, "tin": image_provenance.story_key(link),
            "ten": q.name, "md5": _file_md5(q), "luc": int(time.time())}
    with open(image_provenance._used_images_log(), "a", encoding="utf-8") as f:
        f.write(json.dumps(dong, ensure_ascii=False) + "\n")


def check_not_reused(nhan, duong_dan, draft_id: str, link: str = ""):
    """KHONG DUNG LAI ANH DA DUNG (Ong Chu chot 06/09/2026): bang ti so giai golf
    Ricoh len hai the cua hai tin khac nhau trong cung mot ngay.

    So theo dHash (gan giong <= 6 bit) chu khong theo ten/byte, vi cung mot tam
    tai lai tu bao khac se khac byte. Bo qua chinh draft nay (lam lai mot bai thi
    duoc giu anh). Cua so DATE_SMALL_IMAGE — "trong phien" hieu la vai tuan gan day:
    nguoi doc kenh nho anh lau hon mot ngay.
    """
    import json, time
    so = image_provenance._used_images_log()
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
    # cong "TIN XEP HANG phai dung anh XH" o dre_submit/ethan_submit lai chan moi anh
    # KHAC: hai loi loai tru nhau, vai sua kieu gi cung sai roi tac (do
    # 06/09/2026). Lap lai bang xep hang la DUNG, khong phai loi.
    try:
        with Image.open(duong_dan) as _im:
            if is_ranking_image(_im):
                return [], []
    except Exception:                                        # noqa: BLE001
        pass
    moc = time.time() - DATE_SMALL_IMAGE * 86400
    tin = image_provenance.story_key(link)
    # Nguong theo LOAI anh (xem THRESHOLD_GRAPHIC). md5 van chan tuyet doi: cung
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

    Khoa bang _YUNET_LOCK (audit_content_team B2): `classify` gio duoc
    prepare.vision._seen_image goi tu nhieu luong cung luc qua ThreadPoolExecutor.
    Khong khoa thi luong A dat _YUNET_DA_THU=True TRUOC khi gan xong _YUNET —
    `import cv2` va doc file .onnx o giua co the nha GIL — nen luong B doc co
    thay True nhung _YUNET con None, tra ve None nham nhu may thieu cv2/model
    du thuc ra co day du. Hau qua im lang: count_faces() bao 0 mat, cong mat nguoi
    (IMAGE_RULES §6) tu tat theo may rui thu tu luong thay vi theo may that su co
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
    vision.py lam `or 0` nen 80-95% anh bi coi la KHONG co mat — cong mat nguoi
    (IMAGE_RULES §6) tat cam. detect() nhanh (vai ms), khong can song song.
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
        # vai chay lai 16 lan. Model dung o 320px nen thu ve FACE_EDGE_MAX khong
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
    """Anh rong (trang tron / mot mau) -> CHAN. Goi TRUOC check_chart_integrity, neu khong
    thong bao se la "chart thieu co" thay vi "anh khong co gi"."""
    rong, mo_ta = is_blank_image(img)
    if rong:
        return [f"{nhan}: anh RONG ({mo_ta}) — khong co noi dung nao de hien. "
                "Thuong la buoc chup tra ve trang trang (trang chua render, "
                "selector bat nham phan tu rong, hoac tai ve tep hong). Mo anh "
                "ra XEM truoc khi ghi vao spec; chup lai bang capture_chart.py "
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

    Khac `check_chart_integrity` (do la chuyen khai co "chart": true cho slide than). Cong
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

    MIEN TRU anh xep hang, y nhu check_chart_integrity/check_chart_standalone da mien: voi tin
    xep hang thi bang la CHU THE cua tin, duoc dan full be ngang nguyen ven ke ca
    o bia. Truoc 06/09/2026 cong nay khong mien, nen Dre ket hai dau: cong cua
    dre_submit BAT BUOC bia la anh XH, con carousel lai chan chinh anh do vi ti le
    (bang desktop hay ra 1.1-1.5, bang chup khung mobile ra 0.3-0.5; ca hai deu
    ngoai dai 4:5..1:1). Tro treu la chi THE DU PHONG (1200x1500 = 0.8) lot qua."""
    r = w / h
    if lo - dung_sai <= r <= hi + dung_sai:
        return [], []
    if img is not None and is_ranking_image(img):
        return [], []
    if r >= LANDSCAPE_CLEAR:
        # Anh NGANG: crop_ratio tu choi cat be ngang (can --cat-ngang), va cat
        # be ngang cung la sai huong — mat truc/nhan/cot cuoi. Dan thang sang
        # hai duong dung, dung goi y crop truoc.
        return [f"{nhan}: ti le {w}x{h} ({r:.2f}) khong nam trong 4:5..1:1. Anh "
                f"NGANG thi KHONG cat be ngang: (a) tim them mot anh ngang cung "
                f'tone roi ghep doc, ghi "images": [a, b]; hoac (b) chart/bang '
                f'benchmark thi ghi "chart": true de hien full be ngang nguyen ven '
                f"(slide than). Chi khi la anh chup nguoi/san pham KHONG co chu moi "
                f"duoc cat be ngang: crop_ratio.py --anh {p} --ra <ra.png> --vai dre "
                f"--ti-le 4:5 --cat-ngang"], []
    return [f"{nhan}: ti le {w}x{h} ({r:.2f}) khong nam trong 4:5..1:1 — cat "
            f"truoc: venv/bin/python crop_ratio.py --anh {p} --ra <ra.png> --vai dre "
            f"[--ti-le 4:5] [--cx/--cy]"], []


def check_crop_landscape(nhan, img, w, h, crop_ok=None):
    """Anh goc NGANG ma di qua crop_ratio.py -> CHAN (Ong Chu bat loi 03/09/2026).

    Chart / bang / slide bi crop ve 4:5 la mat tieu de, mat truc, doc ra vo nghia.
    Chi anh chup nguoi/san pham KHONG co chu moi duoc crop, va co hai cach uy
    quyen: khai "crop_ok" trong spec, HOAC cat bang `crop_ratio.py --cat-ngang`
    (co do dong dau vao PNG, xem `allows_landscape_crop`).
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
