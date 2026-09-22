#!/usr/bin/env python3
"""Phan KY THUAT THUAN dung chung cho ba module luat anh (LOW-310).

Luat "moi designer mot rule anh" (LOW-182) tach cong PHAN DOAN NOI DUNG theo vai
— sua Dre khong duoc lan sang Ethan/Kite. Chinh luat do noi phan **kiem ky thuat
thuan** thi giu CHUNG. Truoc 20/09/2026 ca hai loai deu chep 3 ban.

Ong Chu chot 20/09/2026: gop DUNG BON ham khong chua phan doan noi dung:

    load_yunet            nap mo hinh nhan mat (31 dong x 3)
    measure_chart_signal  do tin hieu bieu do bang pixel (31 x 3)
    is_blank_image        do anh trong bang pixel (14 x 3)
    record_used           ghi so anh da dung (12 x 3)

KHONG gop bat ky ham `check_*` nao. Tam ham cong (`check_not_reused`,
`check_chart_integrity`, `check_chart_standalone`, `check_unnamed_face`,
`check_crop_landscape`, `check_duplicate`, `check_blank_image`,
`check_resolution`) hien GIONG HET nhau ba ban — do khong phai ly do de gop:
chung de rieng la de MAI SAU sua cho mot vai khong lan sang vai kia. Nguong cung
vay: `EMPTY_COLOR`, `EMPTY_FLAT`, `FACE_EDGE_MAX`... van song trong tung module
vai va duoc TRUYEN VAO day, khong doc nguoc.

Ba module vai van xuat du ten cu (`_load_yunet`, `measure_chart_signal`,
`is_blank_image`, `record_used`, `_YUNET_LOCK`) nen moi cho goi ben ngoai khong
doi mot dong nao, va moi test dang va `image_rules_<vai>._load_yunet` van va
dung cho.
"""
import threading
from pathlib import Path

from PIL import Image, ImageOps

# Mot detector duy nhat cho ca tien trinh, thay vi ba ban giong het nhau. Truoc
# LOW-310 moi module vai nap rieng mot ban tu CUNG mot tep .onnx.
_YUNET = None
_YUNET_TRIED = False
YUNET_LOCK = threading.Lock()


def load_yunet():
    """Nap lazy model YuNet, dung mot lan cho ca doi tien trinh.

    Khoa bang YUNET_LOCK (audit_content_team B2): `classify` gio duoc
    prepare.vision._seen_image goi tu nhieu luong cung luc qua ThreadPoolExecutor.
    Khong khoa thi luong A dat co "da thu" = True TRUOC khi gan xong detector —
    `import cv2` va doc file .onnx o giua co the nha GIL — nen luong B doc co
    thay True nhung detector con None, tra ve None nham nhu may thieu cv2/model
    du thuc ra co day du. Hau qua im lang: count_faces() bao 0 mat, cong mat nguoi
    (IMAGE_RULES §6) tu tat theo may rui thu tu luong thay vi theo may that su co
    cv2 hay khong.
    """
    global _YUNET, _YUNET_TRIED
    if _YUNET_TRIED:
        return _YUNET
    with YUNET_LOCK:
        if _YUNET_TRIED:              # luong khac vua nap xong trong luc cho khoa
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
        _YUNET_TRIED = True           # dat SAU CUNG, sau khi detector da co gia tri chot
    return _YUNET


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
    v = img.convert("RGB").resize((w, h), Image.Resampling.NEAREST)
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


def is_blank_image(img, empty_color, empty_flat):
    """Anh co RONG khong (trang tron / mot mau phang) -> (bool, mo_ta).

    `empty_color` / `empty_flat` la NGUONG CUA VAI, truyen vao chu khong doc
    nguoc tu module vai (LOW-310): nguong la chinh sach, than do la ky thuat.

    Bo Broadcom dcgr 04/09/2026: buoc chup tra ve anh trang tron (2 mau, phang
    100%), khong cong nao bat, ra mot slide trong tron chi co chu. Tro treu:
    anh trang la thu "giong chart" NHAT theo do_chart, nen cong chart cho qua.

    Do tren 76 anh trong kho: anh rong = 2 mau; anh that it mau nhat = 40 mau
    (screenshot UI toi hai tone). Cach nhau 20 lan nen nguong 4 la an toan —
    khac han cac phep do "slide trong" da thu va bo (chung chong lan voi chart
    sach). Day la RONG thuc su, khong phai "thua".
    """
    ph, mau = measure_chart_signal(img)
    return (mau <= empty_color and ph >= empty_flat), f"{mau} mau, phang {ph:.0%}"


def record_used(duong_dan, draft_id: str, vai: str, link: str, dhash_of, md5_of) -> None:
    """Ghi mot dong vao so anh da dung.

    `dhash_of` / `md5_of` la ham CUA VAI (moi module vai co ban rieng, chua chac
    mai sau con giong nhau) — truyen vao thay vi import nguoc, de module chung
    khong bao gio phu thuoc vao module vai (LOW-310).

    So nam o MOT cho (`image_provenance._used_images_log`) va ca ba vai deu thay
    ngay — patch rieng tung ban se lech nhau, dung cai LOW-182 dinh tranh.
    """
    import json
    import time

    import image_provenance
    q = Path(duong_dan)
    try:
        with Image.open(q) as im:
            h = dhash_of(im)
    except Exception:                                        # noqa: BLE001
        return
    dong = {"dhash": h, "draft_id": draft_id, "role": vai,
            "story_key": image_provenance.story_key(link),
            "file_name": q.name, "md5": md5_of(q), "used_at": int(time.time())}
    with open(image_provenance._used_images_log(), "a", encoding="utf-8") as f:
        f.write(json.dumps(dong, ensure_ascii=False) + "\n")


# ---- LOW-336: luat khung CHUNG moi vai designer (Ong Chu 21/09/2026) --------
#
# *"nguyen tac anh nay la chung cho moi role designer, ko bao gio de vien 2 ben,
# cung ko cat sat vao noi dung"*. Hai phep do thuan pixel duoi day la than ky
# thuat cua luat do; nguong la hang so o day vi luat KHONG rieng vai nao.

SIDE_BAR_MIN = 0.015      # mang dac >= 1.5% be ngang moi tinh la vien (16px/1080)
SIDE_BAR_TOLERANCE = 3    # do lech 0..255/kenh van coi la CUNG mot mau dac
SIDE_BAR_HEIGHT = 0.98    # vien phai chay gan het chieu cao — anh that it khi vay


def measure_side_bars(img) -> tuple:
    """(trai, phai) — be ngang (0..1) cua MANG MAU DAC chay doc suot mep trai/phai.

    Vien dem (`capture_page.count_background` cu dem den 4:5, LOW-336) la pixel dac
    TUYET DOI: moi diem trong mang cung mot mau. Anh that (ke ca bau troi, tuong
    tron, ban cover da lam mo) luon co nhieu/gradient nen khong cot nao phang
    tuyet doi tren ~98% chieu cao. Do tren ban thu nho 360px bang BOX nen van
    giu duoc tinh phang do."""
    from PIL import ImageChops
    im = img.convert("RGB")
    w0, h0 = im.size
    nho = im.resize((360, max(1, round(360 * h0 / w0))), Image.Resampling.BOX)
    w, h = nho.size
    y0 = int(h * (1 - SIDE_BAR_HEIGHT) / 2)
    y1 = h - y0

    def _flat_col(x) -> bool:
        cot = nho.crop((x, y0, x + 1, y1))
        lo, hi = zip(*cot.getextrema())
        return all(b - a <= SIDE_BAR_TOLERANCE for a, b in zip(lo, hi))

    def _same(x, ref) -> bool:
        diff = ImageChops.difference(nho.crop((x, y0, x + 1, y1)), ref)
        return max(e[1] for e in diff.getextrema()) <= SIDE_BAR_TOLERANCE

    def _run(xs) -> int:
        n, ref = 0, None
        for x in xs:
            if not _flat_col(x):
                break
            if ref is None:
                ref = nho.crop((x, y0, x + 1, y1))
            elif not _same(x, ref):
                break
            n += 1
        return n

    trai = _run(range(w))
    if trai >= w:
        return 0.0, 0.0                 # ca anh mot mau: la anh RONG (cong rieng chan), khong phai vien
    return trai / w, _run(range(w - 1, -1, -1)) / w


def has_side_bars(img) -> tuple:
    """(co_vien, mo_ta). Vien NHO hon SIDE_BAR_MIN bo qua (khu rang/1-2px mep)."""
    trai, phai = measure_side_bars(img)
    co = max(trai, phai) >= SIDE_BAR_MIN
    return co, f"mang dac trai {trai:.1%}, phai {phai:.1%}"


SIDE_KEEP = 0.008         # got le trang: chua lai mot dai mong hon SIDE_BAR_MIN de noi dung khong cham mep


def trim_flat_sides(img):
    """Got MANG DAC hai ben (le trang cua chinh trang nguon, vien dem) — chi bo
    phan trong, khong bao gio cat vao cot co noi dung. Chua `SIDE_KEEP` moi ben."""
    trai, phai = measure_side_bars(img)
    w = img.width
    x0 = max(0, int((trai - SIDE_KEEP) * w))
    x1 = min(w, w - int((phai - SIDE_KEEP) * w))
    if x0 <= 0 and x1 >= w:
        return img
    return img.crop((x0, 0, x1, img.height))


QUIET_ROW_ENERGY = 6.0    # nang luong canh trung binh cua mot hang (0..255) duoi muc nay = hang TRONG
QUIET_BAND = 0.006        # hang trong phai lien mot dai >= 0.6% chieu cao, khong phai khe giua hai net chu


def cut_fade(h: int) -> int:
    """Be cao dai tan o mep cat (renderer dung CHUNG so nay): mep cat nam o hang
    trong nen chi can dai ngan de khong thanh mot duong ke."""
    return max(1, min(int(h * 0.05), 48))


def row_energy(img) -> list:
    """Nang luong canh trung binh cua tung hang (0..255), do tren anh xam."""
    from PIL import ImageFilter
    g = img.convert("L").filter(ImageFilter.FIND_EDGES)
    w, h = g.size
    # FIND_EDGES de lai vien 1px sang o CA BON mep anh: bo hai cot mep truoc khi lay
    # trung binh, va hang dau/cuoi lay theo hang ke ben — khong thi day anh nao cung
    # "ban" va `trim_busy_bottom` cat oan mot day sach.
    if w > 4:
        g = g.crop((1, 0, w - 1, h))
    e = list(g.resize((1, h), Image.Resampling.BOX).getdata())
    if h > 2:
        e[0], e[-1] = e[1], e[-2]
    return e


def quiet_cut_row(img, lo: int, hi: int) -> int:
    """Hang y trong [lo, hi] de CAT anh ma khong cat NGANG qua noi dung (LOW-336).

    Chon DAI TRONG DAI NHAT cham vao [lo, hi], cat o hang cuoi cua no (khong qua
    `hi`); bang nhau thi lay dai thap hon (giu nhieu anh hon). Dai trong dai nhat
    la ranh gioi GIUA HAI KHOI (anh | chu thich | tit | doan), cat o do thi khoi nao
    con thi con TRON. Do tren anh that 21/09: lay dai trong THAP NHAT thi rot vao
    khe giua hai dong — tit "Vals AI Backed by Andreessen" / chu thich Honor con
    mot dong; do rong khe cung khong phan biet duoc (chu thich Honor gian dong 3%,
    rong hon khe giua anh va chu thich 1.1%).
    Khong co dai nao trong thi lay hang it canh nhat — van tot hon cat mu o `hi`."""
    h = img.height
    lo, hi = max(1, min(lo, h)), max(1, min(hi, h))
    if lo >= hi:
        return hi
    e = row_energy(img)
    band = max(2, round(h * QUIET_BAND))
    tot = None                              # (do dai, hang cat)
    y = 0
    while y < h:
        if e[y] > QUIET_ROW_ENERGY:
            y += 1
            continue
        dau = y
        while y < h and e[y] <= QUIET_ROW_ENERGY:
            y += 1
        cat = min(y, hi)
        # Phan trong GIU LAI tren mep cat phai du chua dai tan — khong thi dai tan
        # lam mo chinh dong chu cuoi.
        if y - dau >= band and cat - dau >= max(band, cut_fade(cat)) and cat >= lo:
            ung = (y - dau, cat)
            if tot is None or ung > tot:
                tot = ung
    if tot is not None:
        return tot[1]
    return min(range(lo, hi + 1), key=lambda y: (e[min(y, h - 1)], -y))


def trim_busy_bottom(img, max_share: float = 0.15):
    """Day anh CAT NGANG qua mot dong chu (clip chup trang nguon dung ngay giua
    dong) thi lui ve hang trong gan nhat, mat toi da `max_share` chieu cao.
    Day da sach thi tra ve nguyen anh."""
    h = img.height
    band = max(2, round(h * QUIET_BAND))
    e = row_energy(img)
    if max(e[h - band:]) <= QUIET_ROW_ENERGY:
        return img
    y = quiet_cut_row(img, int(h * (1 - max_share)), h - band)
    if y >= h - band or max(e[max(0, y - band):y] or [255]) > QUIET_ROW_ENERGY:
        return img                      # khong tim duoc cho trong that: giu nguyen, khong cat mu
    return img.crop((0, 0, img.width, y))


def clean_capture_edges(img):
    """Anh chup trang nguon -> bo mep: day cat ngang dong chu lui ve hang trong, roi
    got le dac hai ben. Got DAY TRUOC: mot khoi noi dung chi nam o day ben phai
    (nhu notebookcheck) giu cot phai khong phang; bo day di thi le phai moi lo ra."""
    img = trim_busy_bottom(img)
    for _ in range(3):
        moi = trim_flat_sides(img)
        if moi.size == img.size:
            break
        img = moi
    return img


def is_official_tweet_chart(a: dict | None) -> bool:
    """LOW-355 (Ong Chu 22/09/2026): *"chart goc tu tweet chinh chu duoc tinh la bang hop le"*.
    Anh goc tai tu tweet cua chinh hang/ben do benchmark (`official_tweet`, prepare/source.py),
    vision thay la chart/bang, khong bi cham "khong lien quan". Duoc doi xu nhu anh xep hang:
    mien cong chart-di-mot-minh, anh-roi, anh-trong (bang benchmark von day chu, nen trang)."""
    a = a or {}
    return (a.get("source") == "embedded_tweet" and bool(a.get("official_tweet"))
            and a.get("subject_kind") in ("chart", "table") and a.get("relevant") is not False)
