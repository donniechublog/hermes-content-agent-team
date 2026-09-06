#!/usr/bin/env python3
"""Dựng thẻ ảnh hero cho kênh AI (vai designer / Ethan). Hai kiểu:

  - `quote` (mặc định): pull-quote 4:5 — ảnh phủ kín, câu trích dẫn lớn trong
    khung hai góc ngoặc, dòng nguồn canh giữa, chip tên kênh và tagline.
  - `tran`: ảnh full bề ngang, tiêu đề MỘT câu đè lên qua màn tối liền mạch,
    kicker ngắn phía trên, tên kênh canh giữa ở đáy. Không khung, không nhãn.

Bề ngang cố định 1200px; ảnh không bao giờ bị cắt bề ngang (luật LUAT_ANH.md).
Kiểu `dai` cũ (ảnh trên, textbox riêng dưới, nhãn category, hàng icon social,
mascot) đã bỏ 05/09/2026: từ khi cả đội chuyển sang một kiểu ảnh duy nhất,
không vai nào gọi tới nó nữa.
"""
import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat

import luat_anh

ASSETS = Path(__file__).resolve().parent / "assets"
FONTS = ASSETS / "fonts"

# Brand guideline: JetBrains Mono cho heading/UI, Inter cho body text
F_BOLD = str(FONTS / "JetBrainsMono-ExtraBold.ttf")   # tieu de
F_UI = str(FONTS / "JetBrainsMono-Bold.ttf")          # nhan category, UI
F_MONO = str(FONTS / "JetBrainsMono-Regular.ttf")     # chip neobrutalism khong dam
F_REG = str(FONTS / "Inter.ttf")                      # via, ten kenh, UI phu
# Phu de dung serif: no la cau dan chuyen, khong phai nhan UI. Chan chu tao
# nhip doc cham hon tieu de mono, hai tang chu tach bach han thay vi chi khac
# co. Dung ban Text chu KHONG dung ban Display: Display tuong phan net cao,
# net manh mong qua nen o co chu nho doc met mat.
F_SUB = str(FONTS / "NotoSerif.ttf")                  # phu de
# Hero image dung font KHONG CHAN, khong don cach. JetBrains Mono la font don
# cach: moi chu cai chiem dung mot o, nen mot cau dai an rat nhieu be ngang va
# nhin ra "code" chu khong ra "bao". Oswald la sans condensed, hep ngang nen
# chua duoc cau dai o co chu to, dung dang chu cua cac mau tham khao.
F_HERO = str(FONTS / "Oswald.ttf")                    # tieu de hero image
HERO_WEIGHT = 700                                     # truc Weight cua Oswald: 200-700
# Kieu quote (pull-quote). Chu trich dan la Be Vietnam Pro Bold: sans nhan van,
# du dau tieng Viet, doc ra "cau noi" chu khong ra "tieu de" nhu Oswald hep.
# Dau ngoac kep dung NotoSerifDisplay: serif tuong phan cao, cho ra hai dau "
# to va chac lam vat dong khung — dung dang pull-quote bao chi.
F_QUOTE = str(FONTS / "BeVietnamPro-Bold.ttf")        # cau trich dan
F_QUOTE_REG = str(FONTS / "BeVietnamPro-Regular.ttf") # dong nguon (attribution)
F_MARK = str(FONTS / "Oswald.ttf")                    # dau ngoac kep — glyph co duong net, hoi vuong

W = 1200                          # bề ngang cố định
# Tran chieu cao textbox khi ti le bi khoa. Anh la noi dung chinh, textbox chi
# la phan chu thich; cho nao thua thi tra cho anh chu khong don vao textbox.
TRAN_TEXTBOX = 0.40
PAD = 44

# ---- Thuong hieu ----------------------------------------------------------
# Bo cuc, font va moi rang buoc bo cuc GIU NGUYEN giua cac thuong hieu — day la
# cung mot he thong the, chi khac lop son va danh tinh. Doi mau ma doi luon bo
# cuc thi thanh hai san pham khac nhau, mat cai loi cua viec dung chung code.
THUONG_HIEU = {
    "donniechublog": {
        "handle": "donniechublog",
        # Ten hang trong tieu de lay CYAN cua bo nhan dien. Bang mau nay da co
        # mot mau nhan manh roi, muon them mau rieng cua tung hang nua thi doi
        # "cyan" thanh "hang" o day, khong phai sua cho nao khac.
        "to_ten_hang": "cyan",
        # Ten kenh ro va dung mau CYAN nhan dien.
        "ro_handle": 1.0,
        "mau": {
            "BG": (14, 17, 23), "BG_CARD": (22, 27, 34),
            "FG": (230, 237, 243), "MUTED": (139, 147, 158),
            "ACCENT": (88, 166, 255), "ACCENT_DIM": (31, 111, 235),
            "CYAN": (0, 204, 224), "LINE": (48, 54, 61),
        },
    },
    # dcgr.tech: chi trang va den.
    "dcgr": {
        "handle": "dcgr.tech",
        # Bang mau chi co trang va den, nen to ten hang bang mau nhan cua bo
        # nhan dien la vo nghia: mau nhan o day CHINH LA mau chu. Mau thu ba
        # cua no khong phai mot mau co dinh them vao bang, ma la mau cua chinh
        # chu the dang duoc nhac toi — nhac Spotify thi ra xanh la Spotify.
        # Nho vay bang mau van don sac o moi cho khac, va cham mau duy nhat tren
        # the luon mang y nghia.
        "to_ten_hang": "hang",
        "mau_du_phong": (255, 176, 32),   # hang chua biet mau: ho phach
        # Chan the la thong tin PHU: nho va mo hon de lui ve sau.
        "co_chan": 0.85,        # co chu o chan the: 85% co goc
        "mo_chan": 0.55,        # do sang chu chan, 1.0 la bang FG
        # Ten kenh la nhan dien, khong phai chu thich: no phai doc ro.
        "ro_handle": 0.95,
        "mau": {
            "BG": (10, 10, 10), "BG_CARD": (26, 26, 26),
            "FG": (255, 255, 255), "MUTED": (150, 150, 150),
            "ACCENT": (255, 255, 255), "ACCENT_DIM": (110, 110, 110),
            "CYAN": (255, 255, 255), "LINE": (72, 72, 72),
        },
    },
}

# Gia tri mac dinh; build() ghi de theo --brand
BG = BG_CARD = FG = MUTED = ACCENT = ACCENT_DIM = CYAN = LINE = None


def dat_thuong_hieu(ten: str):
    """Nap bang mau cua mot thuong hieu."""
    global BG, BG_CARD, FG, MUTED, ACCENT, ACCENT_DIM, CYAN, LINE
    b = THUONG_HIEU.get(ten)
    if b is None:
        raise SystemExit(f"Khong biet thuong hieu {ten!r}. "
                         f"Co: {', '.join(sorted(THUONG_HIEU))}")
    m = b["mau"]
    BG, BG_CARD = m["BG"], m["BG_CARD"]
    FG, MUTED = m["FG"], m["MUTED"]
    ACCENT, ACCENT_DIM = m["ACCENT"], m["ACCENT_DIM"]
    CYAN, LINE = m["CYAN"], m["LINE"]
    return b

TITLE_SIZE_HI, TITLE_SIZE_LO = 56, 38
TITLE_GROW_MAX = 104              # trần khi tiêu đề nở vào chỗ trống
TITLE_GROW_LINES = 2   # the tin: tuyet doi khong de tieu de 3 dong
# Hero image di huong nguoc lai. O the tin, tieu de la nhan de va phu de moi mang
# noi dung, nen tieu de dai la hong nhip. O hero image KHONG CO phu de: tieu de
# la toan bo noi dung, mot cau tron ven bao quat ca tin. No duoc phep chay bao
# nhieu dong tuy y mien con cho. Tran 6 dong chi de chan truong hop dan ca doan
# van vao, khong phai de giu nhip.
TRAN_TITLE_LINES = 6
# Oswald hep ngang hon JetBrains Mono nhieu nen tran no cua tieu de phai cao hon,
# khong thi cau ngan bi chan o co chu nho hon muc dang le duoc.
TRAN_TITLE_MAX = 150
KICKER_SIZE = 30
KICKER_TRACK = 7        # gian chu cai cua kicker; chu nho ma gian rong moi ra nhan
# Khoang ho giua kicker va tieu de. Do RIENG thay vi dung g1 cua khoi nhan dien,
# vi kicker phai nam SAT tieu de moi doc ra la mot cum; xa qua thi no troi thanh
# mot dong chu le loi giua khoang trong.
KICKER_GAP = 14
# Ca cum kicker (ke trai + chu + ke phai) chiem dung nua be ngang the.
KICKER_CUM = 0.50
KICKER_HO = 20          # ho giua chu va hai duong ke
# Gian dong: chu display co to thi khoang ho mac dinh nhin ra roi rac. Bo sat
# lai cho khoi chu doc thanh MOT mang, dung nhu cac mau tham khao.
LEAD, TRAN_LEAD = 6, 2
SUB_SIZE = 31
VIA_SIZE = 29
BRAND_SIZE = 27   # ten kenh nho hon dong via mot chut

# Tỉ lệ đầu ra khoá cứng: tên → chiều cao thẻ (bề ngang luôn 1200)
RATIOS = {"1:1": 1200, "4:5": 1500, "3:4": 1600}

# ---- Kieu quote (pull-quote) ---------------------------------------------
QUOTE_SIZE_HI, QUOTE_SIZE_LO = 66, 40   # co chu trich dan, tu day xuong
QUOTE_LEAD = 16                         # gian dong quote — thoang hon tieu de
QUOTE_MAX_LINES = 7                     # dai hon la cau qua dai cho mot the
QUOTE_PAD = 64                          # le trong hon hero: quote can khoang tho
MARK_SIZE = 210                         # dau ngoac kep (Oswald: ink that ~28% co font)
QUOTE_BLUR = 28                         # ban kinh mo vung chu de len (Gaussian)
QUOTE_BLUR_DEM = 110                    # khoang dem TREN diem chu bat dau, de mo tan dan khong dot ngot


def _f(path, size, weight=None):
    """Nap font, dat do day neu font co truc bien thien.

    Truoc day ham nay dat cung [size, weight] vi chi phuc vu Inter, font co dung
    hai truc (opsz, wght) theo dung thu tu do. Oswald chi co MOT truc (Weight),
    nen truyen hai gia tri la nem loi, bi except nuot, va font ra do day mac
    dinh 400 — chu tieu de mong dinh ma khong bao gi. Nay doc thang danh sach
    truc cua font roi dien tung truc mot.
    """
    f = ImageFont.truetype(path, size)
    if weight is None:
        return f
    try:
        truc = f.get_variation_axes()
    except Exception:              # noqa: BLE001 — font tinh, khong co truc
        return f
    gia_tri = []
    for t in truc:
        ten = t.get("name")
        ten = ten.decode("utf-8", "ignore") if isinstance(ten, bytes) else str(ten)
        ten = ten.lower()
        if "weight" in ten or "wght" in ten:
            gia_tri.append(float(weight))
        elif "optical" in ten or "opsz" in ten:
            gia_tri.append(float(size))
        else:
            gia_tri.append(float(t.get("default", 0)))
    try:
        f.set_variation_by_axes(gia_tri)
    except Exception:              # noqa: BLE001
        pass
    return f


# ---- To ten thuong hieu trong tieu de -------------------------------------
# Cac mau tham khao deu to mot mau khac cho ten hang xuat hien trong tieu de.
# Do la thu tao nhip manh nhat: mat bat duoc "ai lam" truoc khi doc het cau.
#
# Nhan dien TU DONG theo danh sach thay vi bat nguoi viet danh dau tay: danh dau
# tay nghia la them mot cu phap vao chuoi tieu de, ma chuoi do con di qua kiem
# tra dau, qua wrap, qua ca draft_write. Mot danh sach tra cuu khong dung toi
# cho nao trong so do.
BRAND_TU = {
    "META", "OPENAI", "ANTHROPIC", "GOOGLE", "DEEPMIND", "MICROSOFT", "APPLE",
    "AMAZON", "NVIDIA", "DEEPSEEK", "QWEN", "ALIBABA", "MISTRAL", "XAI",
    "GROK", "CLAUDE", "CHATGPT", "GEMINI", "LLAMA", "PERPLEXITY", "TESLA",
    "SAMSUNG", "INTEL", "AMD", "BAIDU", "BYTEDANCE", "TIKTOK", "MOONSHOT",
    "KIMI", "ZHIPU", "MINIMAX", "MIDJOURNEY", "RUNWAY", "COHERE", "IBM",
    "ORACLE", "QUALCOMM", "TSMC", "SOFTBANK", "TENCENT", "HUAWEI", "SPACEX",
    "GITHUB", "REDDIT", "LINKEDIN", "INSTAGRAM", "FACEBOOK", "YOUTUBE",
    "DISCORD", "SALESFORCE", "ADOBE", "SONY", "XIAOMI", "FIGMA", "CANVA",
    "STRIPE", "UBER", "NETFLIX", "SPOTIFY", "ARM", "BROADCOM", "MICRON",
    "SIEMENS", "FOXCONN", "VINGROUP", "VNG", "FPT", "VIETTEL", "VERTIV",
}
# Cum nhieu tu. Xet truoc tu don, vi "AI" mot minh KHONG duoc to — no la tu
# thuong gap nhat trong moi tieu de, to len thi ca cau nhap nhay.
BRAND_CUM = (
    ("HUGGING", "FACE"), ("BOSTON", "DYNAMICS"), ("STABILITY", "AI"),
    ("SCALE", "AI"), ("MISTRAL", "AI"), ("BLACK", "FOREST", "LABS"),
    ("STABLE", "DIFFUSION"), ("META", "AI"), ("AMAZON", "WEB", "SERVICES"),
)
_RIA = " .,:;!?\u201c\u201d\"'()[]"


# Mau nhan dien cua tung hang. Bang mau dcgr chi co trang va den, nen ten hang
# to len khong khac gi chu thuong. Day la MAU THU BA cua no: khong phai mot mau
# co dinh them vao bang, ma la mau cua chinh chu the dang duoc nhac toi. Nhac
# Spotify thi ra xanh la Spotify, nhac Nvidia thi ra xanh la Nvidia.
MAU_HANG = {
    "SPOTIFY": (30, 215, 96), "NVIDIA": (118, 185, 0),
    "META": (0, 129, 251), "FACEBOOK": (24, 119, 242),
    "OPENAI": (16, 163, 127), "CHATGPT": (16, 163, 127),
    "ANTHROPIC": (217, 119, 87), "CLAUDE": (217, 119, 87),
    "GOOGLE": (66, 133, 244), "GEMINI": (66, 133, 244),
    "DEEPMIND": (66, 133, 244), "MICROSOFT": (0, 164, 239),
    "APPLE": (210, 210, 215), "AMAZON": (255, 153, 0),
    "NETFLIX": (229, 9, 20), "YOUTUBE": (255, 0, 0),
    "TIKTOK": (255, 44, 85), "BYTEDANCE": (255, 44, 85),
    "INSTAGRAM": (225, 48, 108), "LINKEDIN": (10, 102, 194),
    "REDDIT": (255, 69, 0), "DISCORD": (88, 101, 242),
    "GITHUB": (240, 246, 252), "FIGMA": (162, 89, 255),
    "CANVA": (0, 196, 204), "STRIPE": (99, 91, 255),
    "ADOBE": (255, 0, 0), "SALESFORCE": (0, 161, 224),
    "TESLA": (227, 26, 26), "SPACEX": (210, 210, 215),
    "INTEL": (0, 113, 197), "AMD": (237, 28, 36),
    "QUALCOMM": (49, 54, 181), "BROADCOM": (204, 0, 0),
    "IBM": (15, 98, 254), "ORACLE": (234, 0, 17),
    "SAMSUNG": (20, 64, 160), "SONY": (220, 220, 220),
    "HUAWEI": (207, 0, 24), "XIAOMI": (255, 103, 0),
    "TENCENT": (0, 164, 255), "BAIDU": (43, 80, 255),
    "ALIBABA": (255, 102, 0), "TSMC": (0, 89, 159),
    "SOFTBANK": (167, 167, 167), "ARM": (0, 145, 189),
    "DEEPSEEK": (77, 108, 247), "QWEN": (98, 84, 243),
    "MISTRAL": (255, 143, 0), "PERPLEXITY": (32, 178, 170),
    "COHERE": (216, 102, 255), "MIDJOURNEY": (210, 210, 215),
    "XAI": (225, 225, 225), "GROK": (225, 225, 225),
    "KIMI": (110, 130, 255), "MOONSHOT": (110, 130, 255),
    "LLAMA": (0, 129, 251), "VIETTEL": (238, 0, 0),
    "FPT": (0, 110, 181), "VNG": (0, 148, 218),
    "VINGROUP": (176, 141, 87), "VERTIV": (100, 165, 57),
}
MAU_CUM = {
    ("HUGGING", "FACE"): (255, 208, 0),
    ("BOSTON", "DYNAMICS"): (0, 160, 220),
    ("STABILITY", "AI"): (135, 100, 255),
    ("SCALE", "AI"): (100, 160, 255),
    ("MISTRAL", "AI"): (255, 143, 0),
    ("META", "AI"): (0, 129, 251),
    ("STABLE", "DIFFUSION"): (135, 100, 255),
    ("BLACK", "FOREST", "LABS"): (200, 200, 210),
    ("AMAZON", "WEB", "SERVICES"): (255, 153, 0),
}


def _do_sang(mau) -> float:
    r, g, b = (c / 255 for c in mau[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _du_sang(mau, toi_thieu=0.42):
    """Keo mau ve phia trang cho toi khi doc duoc tren nen toi.

    Mau nhan dien cua nhieu hang la mau dam — xanh navy Samsung, xanh TSMC — va
    dat nguyen xi len nen den thi khong doc noi. Keo sang KHONG lam mat nhan
    dien: van ra dung sac do, chi la sang hon.
    """
    mau = tuple(mau[:3])
    for _ in range(24):
        if _do_sang(mau) >= toi_thieu:
            break
        mau = tuple(min(255, round(c + (255 - c) * 0.12)) for c in mau)
    return mau


def _mau_cua_hang(tu_sach: tuple):
    """Mau cua mot ten hang (da tach dau, viet hoa). None neu chua biet."""
    if len(tu_sach) > 1 and tuple(tu_sach) in MAU_CUM:
        return MAU_CUM[tuple(tu_sach)]
    if len(tu_sach) == 1 and tu_sach[0] in MAU_HANG:
        return MAU_HANG[tu_sach[0]]
    for cum, mau in MAU_CUM.items():
        if tu_sach and tu_sach[0] in cum:
            return mau
    return None


def _tach_nhan(dong: str):
    """Tach mot dong thanh [(tu, khoa_hang)]. Giu nguyen tu goc de ve.

    `khoa_hang` la tuple cac tu da lam sach cua ten hang khop duoc, hoac None.
    Tra ve tuple chu khong phai True/False de ben ve con tra duoc MAU cua hang
    do — ca cum "HUGGING FACE" phai ra cung mot mau, ke ca khi hai tu bi tach
    ra hai lan ve.

    So khop KHONG PHAN BIET HOA/THUONG: tieu de the tin (noi ham nay ra doi)
    luon viet hoa toan bo nen truoc day so thang khong sao — nhung van xuoi
    thuong (vd chu than carousel.py) viet ten hang kieu "Nvidia" binh thuong,
    so thang voi BRAND_TU ("NVIDIA") thi trat, lai vo tinh trung mot tu VIET
    TAT tinh co da hoa san (vd "AMD") thay vi dung hang dang noi toi. Chi
    UPPER() luc SO KHOP; `khoa` van tra ve dang chuan hoa (hoa) vi MAU_HANG/
    BRAND_TU luu key hoa — khong lien quan gi toi `tu` goc dung de ve.
    """
    tu = dong.split(" ")
    sach = [t.strip(_RIA).upper() for t in tu]
    khoa = [None] * len(tu)
    i = 0
    while i < len(tu):
        for cum in BRAND_CUM:
            n = len(cum)
            if tuple(sach[i:i + n]) == cum:
                for k in range(i, i + n):
                    khoa[k] = cum
                i += n
                break
        else:
            if sach[i] in BRAND_TU:
                khoa[i] = (sach[i],)
            i += 1
    return list(zip(tu, khoa))


def _mau_hang_trong(text: str):
    """Mau cua ten hang DAU TIEN nhan ra trong `text`, hoac None. Dung de to
    dau ngoac quote theo mau hang duoc nhac toi trong chu de."""
    for _tu, khoa in _tach_nhan(text or ""):
        if khoa:
            mau = _mau_cua_hang(khoa)
            if mau:
                return mau
    return None


def _rong_dong(d, dong, font):
    """Be ngang mot dong khi ve tung tu mot.

    Phai do dung cach se ve, khong duoc do ca chuoi mot lan: ve tung tu thi be
    ngang la tong cua tung manh, lech vai pixel so voi do ca chuoi, va cho lech
    do du de mot dong can giua nhin ra la lech.
    """
    if not dong:
        return 0
    khoang = d.textlength(" ", font=font)
    return sum(d.textlength(t, font=font) for t in dong.split(" ")) \
        + khoang * (len(dong.split(" ")) - 1)


def _ve_dong(d, x, y, dong, font, mau, che_do=None, mau_du_phong=None):
    """Ve mot dong, to rieng ten thuong hieu.

    che_do:
      None    — khong to gi, ca dong mot mau (the tin kieu dai)
      "cyan"  — ten hang lay CYAN cua bo nhan dien (donniechublog)
      "hang"  — ten hang lay MAU RIENG CUA HANG do (dcgr). Hang chua biet mau
                thi dung `mau_du_phong`.
    """
    khoang = d.textlength(" ", font=font)
    for tu, khoa in _tach_nhan(dong):
        f_mau = mau
        if khoa and che_do == "cyan":
            f_mau = CYAN
        elif khoa and che_do == "hang":
            f_mau = _du_sang(_mau_cua_hang(khoa) or mau_du_phong or CYAN)
        d.text((x, y), tu, font=font, fill=f_mau)
        x += d.textlength(tu, font=font) + khoang


def _rong_tracked(d, text, font, track):
    return (sum(d.textlength(c, font=font) for c in text)
            + track * max(0, len(text) - 1))


def _ve_tracked(d, x, y, text, font, fill, track):
    """Ve chu co gian chu cai. PIL khong co tracking nen phai ve tung ky tu."""
    for c in text:
        d.text((x, y), c, font=font, fill=fill)
        x += d.textlength(c, font=font) + track


def _wrap(d, text, font, max_w):
    lines, cur = [], ""
    for w in text.split():
        t = (cur + " " + w).strip()
        if d.textlength(t, font=font) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def _fit_text(d, text, max_w, max_lines, hi, lo, bold=False, path=None,
              weight=None):
    path = path or (F_BOLD if bold else F_SUB)
    for size in range(hi, lo - 1, -2):
        f = _f(path, size, weight)
        lines = _wrap(d, text, f, max_w)
        if len(lines) <= max_lines:
            return f, lines
    f = _f(path, lo, weight)
    lines = _wrap(d, text, f, max_w)[:max_lines]
    if lines:
        lines[-1] = lines[-1].rstrip(" .,") + "…"
    return f, lines


def _grow_title(d, text, max_w, max_h, max_lines=TITLE_GROW_LINES, lead=LEAD,
                path=None, weight=None, hi=None, do_that=False):
    """Chọn cỡ chữ lớn nhất mà tiêu đề vẫn vừa cả bề ngang lẫn chiều cao trống.

    Chỉ dùng khi tỉ lệ thẻ bị khoá — lúc đó textbox có chiều cao cố định nên
    biết chính xác còn bao nhiêu chỗ cho tiêu đề.
    """
    best = None
    path = path or F_BOLD
    for size in range(hi or TITLE_GROW_MAX, TITLE_SIZE_LO - 1, -2):
        f = _f(path, size, weight)
        lines = _wrap(d, text, f, max_w)
        if len(lines) > max_lines:
            continue
        cao = ((_buoc_dong(f, lines, lead)[0] * len(lines)) if do_that
               else _line_h(f, lead) * len(lines))
        if cao <= max_h:
            best = (f, lines)
            break
    if best is None:                       # chỗ quá hẹp — về cỡ nhỏ nhất
        f = _f(path, TITLE_SIZE_LO, weight)
        lines = _wrap(d, text, f, max_w)[:max_lines]
        if lines:
            lines[-1] = lines[-1].rstrip(" .,") + "…"
        best = (f, lines)
    return best


def _buoc_dong(font, lines, lead):
    """Buoc nhay giua hai dong va do nho cua dong dau, do bang CHINH cac dong se ve.

    `_line_h` do bang bbox cua "Ây" — mot chuoi mau co dau mu tren va duoi chu y.
    Cach do do du cho chu thuong, nhung KHONG du cho tieu de tieng Viet viet hoa:
    dau sac tren "Ắ" cao hon dau mu, dau nang duoi "Ạ" thap hon duoi chu y. Do
    that: chuoi mau cao 121px trong khi mot dong that trai tu 0 den 134. Voi gian
    dong bo sat cua hero image, chenh lech do du de hai dong lien nhau chong len
    nhau 11px.

    Tra ve (buoc, tren): `tren` la khoang cach tu goc ve xuong dinh chu cao nhat,
    dung de dat dong dau vao dung cho thay vi tha noi theo viec dong do co dau hay
    khong.
    """
    if not lines:
        return 0, 0
    hop = [font.getbbox(l) for l in lines]
    tren = min(h[1] for h in hop)
    duoi = max(h[3] for h in hop)
    return (duoi - tren) + lead, tren


def _line_h(font, spacing=8):
    b = font.getbbox("Ây")
    return (b[3] - b[1]) + spacing


def ghep_doc(paths, gap=0, nen=(0, 0, 0)):
    """GHEP DOC nhieu anh NGANG thanh mot anh (Ong Chu chot 03/09/2026): mot anh
    qua chu nhat ngang (slide, banner, bang) dua vao khung 4:5 se hoac bi crop
    mat tieu de, hoac de trong nua khung. Thay vi crop, tim THEM mot anh ngang
    nua va xep hai anh doc trong cung khung: moi anh full be ngang, nguyen ti
    le. Tra ve PIL.Image RGB; mot path thi tra ve anh do nguyen ven.

    `gap=0` (Ong Chu chot 04/09/2026): truoc day chen 12px nen den giua hai anh.
    Vach den do la mot DUONG KE ngang giua khung — dung cai mat bat ngay va doc
    ra HAI VUNG rieng biet, dung thu ma luat carousel/hero cam. Hai anh ap sat
    nhau, cong `lech_tone` lo phan tone, moi ra mot mat phang lien. Chi truyen
    `gap` khac 0 khi co ly do rat cu the."""
    ims = [Image.open(q).convert("RGB") for q in paths]
    if len(ims) == 1:
        return ims[0]
    # DUNG han, khong chi canh bao (Ong Chu 04/09/2026). Tieu chi o
    # `luat_anh.kiem_lech_tone` — cung mot cho voi carousel: day la cau hoi
    # "hai anh nay co ghep duoc khong", tuc la do dung chung.
    loi, _ = luat_anh.kiem_lech_tone("ghep anh", ims)
    if loi:
        raise SystemExit("GHEP ANH LECH TONE — " + "\n  ".join(loi))
    w = max(im.width for im in ims)
    ims = [im.resize((w, round(im.height * w / im.width)), Image.LANCZOS) for im in ims]
    h = sum(im.height for im in ims) + gap * (len(ims) - 1)
    out = Image.new("RGB", (w, h), nen)
    y = 0
    for im in ims:
        out.paste(im, (0, y))
        y += im.height + gap
    return out


def _chan_anh_thap(src, ratio):
    """Anh qua ngang di MOT MINH vao kieu quote thi DUNG.

    Tieu chi va nguong nam o `luat_anh.kiem_anh_thap` — do la cau hoi "anh nay
    co dung duoc khong", tuc la do dung chung cho moi vai lam anh. O day chi con
    phan RIENG cua card.py: kieu nao khoa kho (quote khoa theo RATIOS, con
    `dai`/`tran` thi khong nen khong goi cong nay), va cach bao loi (dung han
    thay vi gop danh sach nhu carousel).
    """
    if isinstance(src, (list, tuple)) and len([q for q in src if q]) >= 2:
        return                                   # ghep doc: chinh la duong ra
    H = RATIOS.get(ratio) or RATIOS["4:5"]
    q = src[0] if isinstance(src, (list, tuple)) else src
    with Image.open(q) as im:
        w_anh, h_anh = im.size
    loi, _ = luat_anh.kiem_anh_thap(str(q), w_anh, h_anh, W, H)
    if loi:
        raise SystemExit("ANH QUA NGANG CHO KIEU QUOTE — " + "\n  ".join(loi) +
                         "\n  (Khong co anh thu hai va van muon dung thi --bo-qua-anh)")


def _chan_chuan_anh(src, nhan_vat=""):
    """Bo cong CHUAN ANH dung chung — Ethan chiu dung tieu chuan nhu Dre.

    Ong Chu chot 04/09/2026: "anh do ai lam ma cha phai dat tieu chuan". Truoc
    do bang trong docstring cua `luat_anh` ghi thang ra chenh lech: mat nguoi,
    dau vet crop, anh trung, do phan giai — carousel.py CO, card.py KHONG. Bon
    cong do khong co gi rieng cua carousel ca, chung chi tinh co duoc viet o do
    vi do la cho Ong Chu bat loi truoc.

    Gom het loi roi bao MOT LAN (nhu carousel) thay vi dung o cai dau tien: sua
    mot vong con hon chay lai bon lan.
    """
    duong = [q for q in (src if isinstance(src, (list, tuple)) else [src]) if q]
    loi, canh_bao, da_thay = [], [], {}
    for q in duong:
        nhan = str(q)
        with Image.open(q) as im:
            w, h = im.size
            rgb = im.convert("RGB")
            for l, c in (luat_anh.kiem_anh_rong(nhan, rgb),
                         luat_anh.kiem_xuat_xu(nhan, im, w, h),
                         luat_anh.kiem_do_phan_giai(nhan, w, h),
                         luat_anh.kiem_day_sang(nhan, rgb),
                         luat_anh.kiem_mat_nguoi(nhan, q, nhan_vat),
                         luat_anh.kiem_trung(nhan, q, da_thay)):
                loi += l
                canh_bao += c
    for c in canh_bao:
        print(f"[CANH BAO] {c}", file=sys.stderr)
    if loi:
        raise SystemExit("ANH KHONG DAT CHUAN —\n  " + "\n  ".join(loi))


def _chan_chart(src):
    """Chart di MOT MINH vao kieu `quote`/`tran` thi DUNG.

    Tieu chi o `luat_anh.kiem_chart_mot_minh` — cau hoi "anh nay co dung duoc
    khong", dung chung cho moi khung dat CHU DE LEN anh phu kin. O day chi con
    phan rieng cua card.py: kieu nao la khung do (quote/tran, xem `build`), va
    bao loi bang cach dung han."""
    da_ghep = isinstance(src, (list, tuple)) and len([q for q in src if q]) >= 2
    q = src[0] if isinstance(src, (list, tuple)) else src
    with Image.open(q) as im:
        loi, _ = luat_anh.kiem_chart_mot_minh(str(q), im.convert("RGB"), da_ghep)
    if loi:
        raise SystemExit("CHART DI MOT MINH VAO HERO — " + "\n  ".join(loi) +
                         "\n  (Chac chan muon chart mot minh thi --bo-qua-anh)")


def _chan_crop(src):
    """DUNG neu anh dua vao la mot anh NGANG da bi cat bot BE NGANG.

    Tieu chi o `luat_anh.kiem_crop_ngang` — cung mot cong ma carousel dung.
    O day chi con phan rieng cua card.py: doc nhieu duong dan (--image/--image2)
    va bao loi bang cach dung han."""
    for q in (src if isinstance(src, (list, tuple)) else [src]):
        if not q:
            continue
        with Image.open(q) as im:
            w, h = im.size
            loi, _ = luat_anh.kiem_crop_ngang(str(q), im, w, h)
        if loi:
            raise SystemExit(
                "ANH BI CAT BE NGANG — " + "\n  ".join(loi) +
                "\n  Full chieu rong di truoc, chieu cao xet sau: dua thang ANH "
                "GOC vao --image,\n  anh qua ngang thi ghep doc bang --image2.")


def _mo_anh(src):
    """src: mot duong dan, hoac danh sach duong dan (ghep doc)."""
    if isinstance(src, (list, tuple)):
        return ghep_doc(src)
    return Image.open(src).convert("RGB")


def _fit_cover(img, box_w, box_h):
    src_r, box_r = img.width / img.height, box_w / box_h
    if src_r > box_r:
        nh = box_h
        nw = round(img.width * nh / img.height)
    else:
        nw = box_w
        nh = round(img.height * nw / img.width)
    img = img.resize((nw, nh), Image.LANCZOS)
    left, top = (nw - box_w) // 2, (nh - box_h) // 2
    return img.crop((left, top, left + box_w, top + box_h))


def _khoang(nen: float) -> tuple:
    """Bon khoang cach doc cua khoi nhan dien, co gian theo he so nen.

    Truoc day bon con so nay hard-code (24, 10, 34, PAD). Hau qua: khoi chu
    chiem mot chieu cao co dinh, va khi anh can them cho thi ANH phai thu lai —
    tuc la hy sinh noi dung de giu khoang trong trang tri. Nguoc ca uu tien.

    Nay chu nhuong cho anh: nen tu 1.0 xuong 0.55, chu van doc duoc vi chi bop
    KHOANG TRONG chu khong bop co chu.
    """
    return (max(10, int(24 * nen)),      # sau nhan category
            max(4, int(10 * nen)),       # giua tieu de va phu de
            max(14, int(34 * nen)),      # truoc dong via
            max(22, int(PAD * nen)))     # le duoi


def _tran_anh(canvas, src_img, split, nat_h=None):
    """Anh phu KIN the, chu dat de len tren qua mot man toi chuyen dan.

    Kieu dai (mac dinh) cat the thanh hai o: anh o tren, textbox mau dac o duoi.
    Ranh gioi thang bang do lam anh nhin nhu bi cat cut. Kieu tran bo ranh gioi:
    anh chay het chieu cao, chu nam de len phan duoi, va cai giu cho chu doc
    duoc la mot man toi day dan chu khong phai mot mang mau dac.

    Danh doi: phu kin the thi phai CAT anh theo be ngang hoac chieu cao. Chi
    dung kieu nay cho hero image, con the tin thi van dung kieu dai de anh
    nguon hien tron ven.
    """
    H = canvas.height
    nat_h = nat_h or round(W * src_img.height / src_img.width)

    # ANH LUON HIEN FULL BE NGANG. Do la uu tien so mot, va no quyet dinh phan
    # con lai: chieu cao tu nhien cua anh o be ngang W la `nat_h`, khong thuong
    # luong. Chi co hai truong hop.
    if nat_h >= H:
        # ANH DU CAO (hoac cao hon the): phu kin, cat bot theo chieu doc, chu
        # nam de len phan duoi. Day la truong hop "anh qua dai, lop text chen
        # len" — khong mat be ngang nao, chi mat mot phan chieu cao.
        canvas.paste(_fit_cover(src_img, W, H), (0, 0))
        ket = split
    else:
        # ANH THAP HON THE: dat sat tren, giu nguyen ti le, phan duoi la nen cua
        # bo nhan dien. Day la truong hop "anh qua ngan, lop nen text cao len".
        # KHONG phong to cho vua chieu cao: phong len la cat mat be ngang hoac
        # vo net, ca hai deu te hon mot mang nen phang.
        canvas.paste(src_img.resize((W, nat_h), Image.LANCZOS), (0, 0))
        ket = min(nat_h, split)

    # Man toi. Diem uon dat tren `ket` mot doan de khong co duong gay lo ra.
    #
    # Voi anh thap, man PHAI dat mo hoan toan dung o day anh. Truoc day no chi
    # toi alpha 145 o moc chu roi dam dan xuong het the — dung cho anh phu kin,
    # nhung voi anh thap thi day anh con hien 43% roi cham thang vao nen, lo ra
    # mot duong ngang. Ca kieu tran sinh ra de xoa dung cai duong do.
    day_kin = nat_h < H
    # Dai chuyen tiep. Voi anh phu kin the thi 18% chieu cao the la vua. Voi anh
    # THAP thi con so do an qua sau vao mot tam anh von da ngan: anh cao 675px ma
    # dai chuyen 270px la mat 40% tam anh vao bong toi. Co lai theo chinh chieu
    # cao anh.
    dai = int(H * 0.18) if not day_kin else min(int(H * 0.18), int(nat_h * 0.30))
    uon = max(0, ket - dai)
    man = Image.new("L", (1, H))
    for y in range(H):
        if y <= uon:
            a = int(90 * (y / max(1, uon)) ** 2)
        elif day_kin:
            t = (y - uon) / max(1, ket - uon)
            a = 90 + (255 - 90) * min(1.0, t) ** 0.9
        else:
            t = (y - uon) / max(1, H - uon)
            a = 90 + (238 - 90) * t ** 0.85
        man.putpixel((0, y), min(255, int(a)))
    lop = Image.new("RGBA", (W, H), (*BG, 255))
    lop.putalpha(man.resize((W, H)))
    canvas.alpha_composite(lop)
    return (0, 0, W, H)


def _mo_vung_chu(canvas, frame_top, dem=QUOTE_BLUR_DEM):
    """Lam MO CUC BO dung vung chu de len (Ong Chu chot 06/09/2026: chu co vien
    "trong nhu karaoke" — bo vien, thay bang lam mo phan anh o duoi chu).

    Chi mo tu `frame_top - dem` tro xuong DAY THE: phan anh phia tren van net
    100%. Mo tan dan theo duong cong power (tu 0 tai `frame_top - dem` toi full
    tai `frame_top`) — tranh dung lai chinh cai loi da bat nhieu lan (mep net/mo
    dot ngot doc ra hai vung), lan nay la ranh gioi SAC/MO thay vi SANG/TOI. Tu
    `frame_top` toi day the giu MO DEU — do la vung chua quote, chip, dong
    nguon (chip co nen dac rieng nen mo duoi no khong sao).

    Vi sao mo la du, khong can vien: mo xoa het chi tiet roi (chu/ke bang trong
    anh nguon), lam dong deu do sang trong khoi — luc do MOT mau chu duy nhat
    (do o `_mau_doi_nen` ke tiep) doc duoc tren toan khoi, khong con truong hop
    vua sang vua toi trong cung mot cau nhu khi chi dua vao mot phep do bat ky.

    Sua canvas tai cho, khong tra ban moi."""
    W_, H_ = canvas.size
    top = max(0, int(frame_top - dem))
    if H_ <= top:
        return canvas
    vung = canvas.crop((0, top, W_, H_)).convert("RGB")
    mo = vung.filter(ImageFilter.GaussianBlur(QUOTE_BLUR))
    mat_na = Image.new("L", vung.size, 255)
    doan_tan = max(1, int(frame_top - top))
    for y in range(vung.height):
        y_that = top + y
        a = 255 if y_that >= frame_top else int(255 * ((y_that - top) / doan_tan) ** 0.82)
        mat_na.paste(a, (0, y, vung.width, y + 1))
    ghep = Image.composite(mo, vung, mat_na)
    canvas.paste(ghep.convert(canvas.mode), (0, top))
    return canvas


def _mau_doi_nen(canvas, box):
    """Mau chu TUONG PHAN voi vung anh ben duoi `box` (x0,y0,x1,y1), DO SAU KHI
    da lam mo (`_mo_vung_chu`) — do sang trung binh, MOT phep do duy nhat.

    Vung toi -> chu sang (FG); vung sang -> chu toi (BG, mau nen thuong hieu,
    khong phai den tuyet doi)."""
    x0, y0, x1, y1 = (max(0, int(box[0])), max(0, int(box[1])),
                      min(canvas.width, int(box[2])), min(canvas.height, int(box[3])))
    if x1 <= x0 or y1 <= y0:
        return FG
    vung = canvas.convert("RGB").crop((x0, y0, x1, y1))
    sang = ImageStat.Stat(vung.convert("L")).mean[0]
    return FG if sang < 140 else BG


def _quote_mark(d, cx, cy, font, color, closing=False):
    """Ve mot dau ngoac kep (glyph FONT) can giua THAT su tai (cx, cy).

    Khong dung font.getbbox de can: voi Oswald no phong chieu cao (bao 113px
    trong khi ink that ~39px), lam dau lech len tren line. Render thu ra mask,
    lay ink bbox THAT roi can theo do. Tra ve be rong ink that (de clean line)."""
    g = "”" if closing else "“"
    bb = font.getbbox(g)
    probe = Image.new("L", (bb[2] + 8, bb[3] + 8), 0)
    ImageDraw.Draw(probe).text((4, 4), g, font=font, fill=255)
    ink = probe.getbbox() or (4, 4, 5, 5)
    off_x = (ink[0] + ink[2]) / 2 - 4          # tam ink that, lech tu goc ve (4,4)
    off_y = (ink[1] + ink[3]) / 2 - 4
    d.text((cx - off_x, cy - off_y), g, font=font, fill=color)
    return ink[2] - ink[0]


def _quote_frame(d, x0, y0, x1, y1, line_color, mark_color, lw=5):
    """Khung quote kieu TiaSang: HAI goc ngoac doi nhau (TL + BR), goc bo tron,
    moi goc giu 1/3 net NGANG + 1/2 net DOC. Dau " (glyph FONT) nam GIUA net
    ngang, net ngang CLEAN quanh dau.

    MAU: net (line + arc) dung `line_color` CO DINH (xanh Apple); dau " dung
    `mark_color` (doi theo hang duoc nhac)."""
    r = 30
    aw = (x1 - x0) // 3          # net ngang giu 1/3
    av = (y1 - y0) // 2          # net doc giu 1/2
    br_lift = 22                 # goc BR nhac len mot chut
    pad = 14                     # khoang clean line quanh dau
    mfont = _f(F_MARK, MARK_SIZE, 700)      # font dau ngoac (Oswald, weight day)

    # --- goc tren-trai: dau MO nam GIUA net ngang tren (y0) ---
    d.arc([x0, y0, x0 + 2 * r, y0 + 2 * r], 180, 270, fill=line_color, width=lw)
    d.line([(x0, y0 + r), (x0, y0 + av)], fill=line_color, width=lw)  # net doc
    cx = x0 + r + 30 + pad                    # day dau RA XA goc them mot khoang = pad
    tot = _quote_mark(d, cx, y0, mfont, mark_color, closing=False)
    ml, mr = cx - tot / 2 - pad, cx + tot / 2 + pad
    if ml > x0 + r:
        d.line([(x0 + r, y0), (ml, y0)], fill=line_color, width=lw)  # line vao (trai)
    if mr < x0 + aw:
        d.line([(mr, y0), (x0 + aw, y0)], fill=line_color, width=lw)  # line ra (phai)

    # --- goc duoi-phai: dau DONG nam GIUA net ngang duoi (yb), nhac len br_lift ---
    yb = y1 - br_lift
    d.arc([x1 - 2 * r, yb - 2 * r, x1, yb], 0, 90, fill=line_color, width=lw)
    d.line([(x1, yb - av), (x1, yb - r)], fill=line_color, width=lw)  # net doc
    cx2 = x1 - r - 30 - pad                   # day dau RA XA goc them mot khoang = pad
    tot2 = _quote_mark(d, cx2, yb, mfont, mark_color, closing=True)
    ml2, mr2 = cx2 - tot2 / 2 - pad, cx2 + tot2 / 2 + pad
    if ml2 > x1 - aw:
        d.line([(x1 - aw, yb), (ml2, yb)], fill=line_color, width=lw)  # line vao (trai)
    if mr2 < x1 - r:
        d.line([(mr2, yb), (x1 - r, yb)], fill=line_color, width=lw)   # line ra (phai)


def _render_quote(src, quote, attrib, out, handle, ratio, tagline=""):
    """The pull-quote: mot cau trich dan lon tren anh phu kin, KHONG LOP NEN.

    Khac hero image (mot tieu de bao quat tin) va carousel (nhieu slide): day la
    MOT cau noi dat trong ngoac kep, co dong nguon o duoi — dung dang the trich
    dan cua bao.

    Ong Chu chot 06/09/2026, sau nhieu lan bat loi cung mot goc (nen phu chu
    cao hon chinh cau chu, doc ra hai vung rieng biet): BO HAN man toi. Quote
    dat THANG len anh goc, mau chu tu doi theo do sang vung anh ben duoi
    (`_mau_doi_nen`) — sang thi chu toi, toi thi chu sang — cong mot vien
    tuong phan quanh chu (`_ve_chu_vien`) de doc duoc ca khi vung do vua sang
    vua toi (bang xep hang: nen trang, chu den). Khong con hinh hoc frame_top/
    nat_h/gradient nao de tinh sai nua.
    """
    H = RATIOS.get(ratio) or RATIOS["4:5"]     # quote luon khoa khung; free -> 4:5
    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    src_img = _mo_anh(src)
    # ANH LUON HIEN FULL BE NGANG, KHONG CAT HAI CANH (Ong Chu bat loi 03/09/2026:
    # cover-crop lam mat tieu de cua slide/bang nguon, anh doc ra vo nghia).
    # Nen: ban cover LAM MO phu kin khung (KHONG lam toi — Ong Chu 06/09/2026:
    # "lam mo chu dung boi them mau", ap dung ca cho lop nen nay chu khong chi
    # vung chu; truoc day co giam sang .enhance(0.5), gio bo, giu nguyen do sang
    # goc, chi mo). Lop sac: anh nguyen ti le, full W, dat sat tren (chu quote
    # nam duoi). Anh cao hon khung thi chi cat theo chieu doc, giu tron be
    # ngang. Dong nhip voi carousel._body_image.
    nen = _fit_cover(src_img, W, H).filter(ImageFilter.GaussianBlur(40))
    canvas.paste(nen, (0, 0))
    nat_h = round(src_img.height * W / src_img.width)
    sac = src_img.resize((W, nat_h), Image.LANCZOS)
    if nat_h > H:
        top = (nat_h - H) // 2
        sac = sac.crop((0, top, W, top + H))
    canvas.paste(sac, (0, 0))

    d = ImageDraw.Draw(canvas)
    # Khung o le FRAME_X; chu THUT VAO them (TEXT_X > FRAME_X) de hai canh chieu
    # rong cua khung thoang khoi chu.
    FRAME_X = 42
    TEXT_X = FRAME_X + 54
    avail_w = W - 2 * TEXT_X

    # Cau trich dan — giu nguyen HOA/thuong (khong .upper() nhu tieu de).
    f_q, q_lines = _fit_text(d, quote, avail_w, max_lines=QUOTE_MAX_LINES,
                             hi=QUOTE_SIZE_HI, lo=QUOTE_SIZE_LO, path=F_QUOTE)
    buoc, tren = _buoc_dong(f_q, q_lines, QUOTE_LEAD)
    quote_h = buoc * len(q_lines)

    f_at = _f(F_QUOTE_REG, 26)
    at_lines = _wrap(d, attrib, f_at, avail_w) if attrib else []
    at_lh = _line_h(f_at, 8)
    at_h = at_lh * len(at_lines)

    # Tagline ngan cua kenh — chip nho o goc duoi-trai khung (xem ben duoi).
    tag = (tagline or "").strip()

    # KHUNG CHU NHAT BO GOC bao quanh quote; dau " gan goc TL/BR (xem _quote_frame).
    # BO CUC (Ong Chu chot 03/09/2026): hai CHIP can theo muc net khung (tam chip
    # ngang voi net ngang), khung giu design goc:
    #   - chip ten kenh (cyan) o goc TREN-PHAI khung, muc net ngang tren
    #   - chip tagline (trang) o goc DUOI-TRAI khung, muc net ngang duoi
    #   - dong nguon canh giua sat day.
    # Chip KHONG o goc tren the: o do no de len tieu de cua anh nguon.
    BOX_PAD_Y = 66       # khung cao hon khoi chu tren/duoi — chua khoang tho + dau "
    BR_LIFT = 22         # net ngang duoi nam tren frame_bottom chung nay (xem _quote_frame)
    CHIP_OFF = 7         # bong cung cua chip
    CHIP_INSET = 26      # chip thut vao tu canh doc cua khung
    GAP_BOT = 60         # day chip duoi <-> dong nguon
    BOT_MARGIN = 30      # dong nguon <-> day the

    f_hchip = _f(F_MONO, 22)          # JetBrains Mono Regular — ten kenh KHONG dam
    f_tchip = _f(F_UI, 20)            # JetBrains Mono Bold
    ten = handle if handle.startswith("@") else "@" + handle
    htb = d.textbbox((0, 0), ten, font=f_hchip)
    chip_h = (htb[3] - htb[1]) + 2 * 13

    src_top = H - BOT_MARGIN - at_h
    yb = src_top - GAP_BOT - CHIP_OFF - chip_h // 2      # net ngang duoi = tam chip duoi
    frame_bottom = yb + BR_LIFT
    last_line_bottom = frame_bottom - BOX_PAD_Y
    first_line_top = last_line_bottom - quote_h
    frame_top = first_line_top - BOX_PAD_Y

    # KHONG CON LOP NEN CA THE (Ong Chu chot 06/09/2026, sua tiep sau khi vien
    # chu bi che "phen nhu karaoke"): quote dat THANG len anh goc, CHI lam MO
    # CUC BO dung vung chu de len (`_mo_vung_chu`) — phan anh phia tren van
    # net nguyen. Mo lam dong deu do sang trong khoi nen MOT mau chu duy nhat
    # (`_mau_doi_nen`, do SAU khi da mo) la du, khong can vien.
    _mo_vung_chu(canvas, frame_top)
    mau_chu = _mau_doi_nen(canvas, (TEXT_X, frame_top, W - TEXT_X, frame_bottom))

    # Cac dong quote, canh trai (thut vao TEXT_X).
    qy = first_line_top
    for ln in q_lines:
        d.text((TEXT_X, qy - tren), ln, font=f_q, fill=mau_chu)
        qy += buoc

    # MAU: net khung dung CYAN cua bo nhan dien (nhu ten kenh, dong tong voi the
    # cua Bob); DAU " doi theo hang duoc nhac trong chu de (quote hoac dong
    # nguon). Khong nhan ra hang nao thi dau cung CYAN.
    mau_hang = _mau_hang_trong(quote) or _mau_hang_trong(attrib)
    mark_col = _du_sang(mau_hang) if mau_hang else CYAN
    _quote_frame(d, FRAME_X, frame_top, W - FRAME_X, frame_bottom,
                 CYAN, mark_col)

    # Dong nguon (attribution), CANH GIUA, sat day — cung mau, vung nay da
    # duoc _mo_vung_chu lam mo tu truoc.
    ay = src_top
    for ln in at_lines:
        lw_ln = d.textlength(ln, font=f_at)
        d.text(((W - lw_ln) / 2, ay), ln, font=f_at, fill=mau_chu)
        ay += at_lh

    # CHIP theo phong cach NEOBRUTALISM: khoi dac, vien den day, bong cung lech
    # (KHONG mo), chu MONO. Cuoi len net khung (xem bo cuc o tren).
    def _chip_neo(txt, font, top, align, bg, fg, off=7, bord=4, pad_x=22, pad_y=13, x=None):
        tb = d.textbbox((0, 0), txt, font=font)
        bw, bh = (tb[2] - tb[0]) + 2 * pad_x, (tb[3] - tb[1]) + 2 * pad_y
        x0 = x if x is not None else (QUOTE_PAD if align == "l" else (W - QUOTE_PAD - bw))
        y0 = top
        x1, y1 = x0 + bw, y0 + bh
        d.rectangle([x0 + off, y0 + off, x1 + off, y1 + off], fill=(0, 0, 0))   # bong cung lech
        d.rectangle([x0, y0, x1, y1], fill=bg, outline=(0, 0, 0), width=bord)   # khoi dac + vien den
        d.text((x0 + pad_x - tb[0], y0 + pad_y - tb[1]), txt, font=font, fill=fg)
        return bh, x1

    fx0, fx1 = FRAME_X, W - FRAME_X
    # Chip ten kenh: goc TREN-PHAI, tam chip ngang muc net ngang tren. Khung giu
    # nguyen design goc (net 1/3), KHONG keo dai net toi chip.
    tb_h = d.textbbox((0, 0), ten, font=f_hchip)
    hw = (tb_h[2] - tb_h[0]) + 2 * 22
    hx0 = fx1 - CHIP_INSET - hw
    _chip_neo(ten, f_hchip, frame_top - chip_h // 2, "l", CYAN, (0, 0, 0), x=hx0)
    if tag:
        # Chip tagline: goc DUOI-TRAI, tam chip ngang muc net ngang duoi (yb).
        tx0 = fx0 + CHIP_INSET
        _chip_neo(tag, f_tchip, yb - chip_h // 2, "l", (255, 255, 255), (0, 0, 0), x=tx0)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, "PNG", optimize=True)
    print("the: {}x{} ({:.2f}:1) | kieu: quote | {} dong quote".format(
        W, H, W / H, len(q_lines)))
    return out


    # Moi goc deu de len anh -> khong dan mascot


def _pha(mau, do_sang: float, nen=None):
    """Tron mau ve phia nen de lam mo. do_sang=1.0 giu nguyen, 0 la bang nen."""
    nen = nen if nen is not None else BG
    t = max(0.0, min(1.0, do_sang))
    return tuple(int(n + (c - n) * t) for c, n in zip(mau, nen))


# Em-dash bi cam trong moi van ban dang. caption_check chan o bai viet, publish
# doi not truoc khi gui, nhung THE ANH di duong khac nen truot qua. Chan tai day.
DAU_CAM = {"\u2014": ",", "\u2013": "-", "\u2012": "-", "\u2015": "-"}


def bo_dau_cam(t: str) -> str:
    if not t:
        return t
    for a, b in DAU_CAM.items():
        t = t.replace(a, b)
    import re as _re
    return _re.sub(r"\s+,", ",", _re.sub(r"\s{2,}", " ", t)).strip()


# Tieng Viet KHONG DAU tren the la loi nang: the la thu nguoi doc nhin thay dau
# tien, va chu khong dau lam ca kenh trong nhu lam au. Da lot mot lan — nhan
# "CONG CU" in ra tren the that.
#
# Cach nhan biet: tim TU TIENG VIET quen thuoc bi go mat dau. Khong the chi dua
# vao "co dau hay khong", vi tieu de hop le van co the toan tieng Anh
# ("OzBrain", "Audio-to-MIDI"). Nhung neu xuat hien nguyen mot tu tieng Viet
# thieu dau thi chac chan la go sai.
# Am tiet tieng Viet thuong gap, viet KHONG DAU. Danh sach rong vi mot tieu de
# tieng Viet bi go mat dau se dinh nhieu tu cung luc, con tieng Anh thi hau nhu
# khong dinh tu nao.
AM_MAT_DAU = {
    # tu chuc nang, xuat hien trong hau het cau tieng Viet
    "va", "cua", "cho", "voi", "khong", "duoc", "nhung", "nguoi", "hon", "tren",
    "duoi", "trong", "ngoai", "moi", "cung", "chung", "cac", "nhieu", "khi",
    "neu", "nen", "phai", "the", "nay", "do", "day", "ra", "vao", "len", "xuong",
    "sau", "truoc", "theo", "bang", "them", "boi", "tu", "den", "roi", "van",
    "chi", "deu", "cang", "rat", "qua", "hay", "hoac", "ma", "la", "co", "khac",
    "o", "an", "vi", "sao", "gi", "ai", "dau", "bao", "moi",
    # dong tu thuong gap
    "lam", "chay", "viet", "doc", "xem", "thay", "biet", "hieu", "dung", "tao",
    "chuyen", "nhan", "gui", "mo", "dong", "tang", "giam", "vuot", "dat", "giu",
    "bo", "them", "sua", "kiem", "tra", "chon", "tim", "ghi", "luu", "tai",
    "phat", "hanh", "cap", "nhat", "ho", "tro", "dua", "lay", "noi", "hoi",
    # danh tu ky thuat va thuong gap
    "cong", "cu", "hinh", "thu", "nghiem", "ha", "tang", "nguon", "kinh",
    "doanh", "nghe", "lieu", "nghien", "tri", "tue", "hoc", "may", "mang",
    "diem", "so", "ty", "trieu", "nghin", "tram", "gia", "phi", "quoc", "te",
    "chinh", "thuc", "ban", "phien", "dau", "cuoi", "giua", "giong", "tuong",
    "bai", "tin", "anh", "chu", "am", "thanh", "khai", "han", "lan", "viec",
    "gioi", "muc", "loai", "dang", "kien", "truc", "he", "thong", "phan",
    "tich", "ket", "qua", "hieu", "suat", "toc", "kha", "nang", "tinh", "nang",
    # tinh tu, so dem
    "manh", "nhanh", "cham", "tot", "xau", "re", "dat", "mien", "moi", "cu",
    "lon", "nho", "cao", "thap", "dai", "ngan", "day", "mong", "sau", "rong",
    "mot", "hai", "ba", "bon", "muoi", "thang", "ngay", "gio", "phut", "nam",
}

# Cum tu chac chan la tieng Viet mat dau — dinh mot cum la du ket luan
CUM_MAT_DAU = {
    "cong cu", "mo hinh", "thu nghiem", "ha tang", "ma nguon mo", "ban cap nhat",
    "kinh doanh", "cong nghe", "du lieu", "nghien cuu", "phat hanh", "cap nhat",
    "tri tue", "may hoc", "mien phi", "quoc te", "chinh thuc",
}


def tim_mat_dau(text: str) -> list:
    """Tra ve dau hieu tieng Viet bi go mat dau trong `text`.

    Hai muc: dinh mot CUM quen thuoc la du, hoac dinh tu HAI am tiet tro len.
    Nguong hai la de tieng Anh khong bi bao nham — tu nhu "the", "do", "so",
    "ra" cung xuat hien trong tieng Anh, nhung hiem khi hai cai cung luc trong
    mot tieu de ngan.
    """
    if not text:
        return []
    import re as _re

    # Nhieu am tiet tieng Viet VON khong co dau: "cho", "chung", "cong", "ban".
    # Neu van ban da co dau o dau do thi coi nhu go dung, va nhung tu tren la
    # chinh ta binh thuong chu khong phai loi. Da bao nham "Bo nao dung chung
    # cho moi agent" vi hai tu "cho" va "chung" — trong khi ca cau co dau du.
    # Nen chi soi khi CA VAN BAN khong co lay mot dau nao.
    if _re.search(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợ"
                  r"ùúủũụưừứửữựỳýỷỹỵđ]", text, _re.I):
        return []

    tu = _re.findall(r"[A-Za-zÀ-ỹ]+", text)
    low = [t.lower() for t in tu]

    cum = []
    for i in range(len(low) - 1):
        if f"{low[i]} {low[i+1]}" in CUM_MAT_DAU:
            cum.append(f"{tu[i]} {tu[i+1]}")
    if cum:
        return sorted(set(cum))

    don = sorted({tu[i] for i, t in enumerate(low) if t in AM_MAT_DAU})
    return don if len(don) >= 2 else []


def build(src, title, out, handle=None, ratio="free", tagline="daily AI update",
          brand="donniechublog", bo_qua_dau=False, kieu="quote", kicker="",
          attrib="", bo_qua_anh=False, nhan_vat=""):
    """Dung the `quote` (mac dinh) hoac `tran`. `src`: mot duong dan, hoac danh
    sach hai duong dan (ghep doc). `title` la cau trich dan (quote) hoac cau
    tieu de (tran)."""
    # Nap bang mau TRUOC moi thu khac: cac ham ve doc BG/FG/ACCENT o pham vi
    # module, chua nap thi chung con la None.
    b = dat_thuong_hieu(brand)
    handle = handle or b["handle"]
    title, attrib = bo_dau_cam(title), bo_dau_cam(attrib)

    # Chan tieng Viet khong dau TRUOC khi ve, o moi cho chu hien len the.
    loi = {}
    for ten, gt in (("tieu de", title), ("nguon", attrib)):
        m = tim_mat_dau(gt or "")
        if m:
            loi[ten] = m
    if loi and not bo_qua_dau:
        chi_tiet = "; ".join(f"{k}: {', '.join(v)}" for k, v in loi.items())
        raise SystemExit(
            f"Tieng Viet KHONG DAU tren the — {chi_tiet}\n"
            "  Go lai co dau day du roi chay lai. The la thu nguoi doc nhin thay\n"
            "  dau tien, chu khong dau lam ca kenh trong nhu lam au.\n"
            "  (Neu that su la tieng Anh, chay lai voi --bo-qua-dau)")
    if kieu not in ("quote", "tran"):
        raise SystemExit(f"--kieu phai la quote hoac tran, nhan {kieu!r}")
    _chan_crop(src)          # anh ngang bi cat bot be ngang: dung o moi kieu
    if not bo_qua_anh:
        _chan_chuan_anh(src, nhan_vat)   # chuan anh chung: xuat xu, do net, mat nguoi, trung
        _chan_chart(src)     # chart di mot minh vao hero: ep sang --image2/carousel
    if kieu == "quote" and not bo_qua_anh:
        _chan_anh_thap(src, ratio)   # anh qua ngang: nua the se bo trong
    # Kieu quote co duong ve rieng (anh phu kin + cau trich dan + dong nguon).
    if kieu == "quote":
        return _render_quote(src, title, attrib, out, handle, ratio, tagline)

    # ---- kieu tran: hero image, tieu de la MOT cau tron ven de len anh -------
    src_img = _mo_anh(src)
    # Chieu cao tu nhien cua anh khi hien full be ngang: con so quyet dinh moi
    # thu con lai — anh la lop nen, khong co tran.
    nat_h = round(W * src_img.height / src_img.width)
    img_h, how = nat_h, "tran"

    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    co_chan = b.get("co_chan") or 1.0
    mo_chan = b.get("mo_chan") or 1.0
    f_via = _f(F_REG, max(12, round(VIA_SIZE * co_chan)), weight=500)
    avail_w = W - PAD * 2
    lead = TRAN_LEAD
    # Hero image dung Oswald (khong chan, condensed): mot cau dai van vua be
    # ngang o co chu to, dung dang chu cua cac mau tham khao.
    f_title, title_lines = _fit_text(probe, title.upper(), avail_w,
                                      max_lines=TRAN_TITLE_LINES,
                                      hi=TITLE_SIZE_HI, lo=TITLE_SIZE_LO, bold=True,
                                      path=F_HERO, weight=HERO_WEIGHT)

    # Kicker: nhan ngan phia tren tieu de.
    kicker = (kicker or "").strip().upper()
    f_kick = _f(F_REG, KICKER_SIZE, weight=700)
    # Do CHIEU CAO CHU THAT chu khong dung _line_h. _line_h do bang bbox cua
    # "Ây" — co ca dau mu lan duoi chu y — vi no phuc vu chu tieng Viet co dau.
    # Kicker toan chu Latin viet hoa, khong dau, nen cach do do chua them gan 20px
    # troi o duoi, va cong voi khoang ho nua thi kicker troi han khoi tieu de.
    _kb = f_kick.getbbox(kicker) if kicker else (0, 0, 0, 0)
    kick_h = (_kb[3] - _kb[1]) if kicker else 0
    via_h = f_via.getbbox("Ây")[3] - f_via.getbbox("Ây")[1]

    def _cao_tieu_de(f=None, dong=None):
        """Chieu cao khoi tieu de, do bang CHINH cac dong se ve."""
        f, dong = f or f_title, dong if dong is not None else title_lines
        return _buoc_dong(f, dong, lead)[0] * len(dong)

    def _cao_dau(nen=1.0):
        # Phan dau textbox la khoang ho, cong them kicker neu co (kicker cong
        # mot khoang ho nua truoc tieu de). Kieu tran khong ve nhan category.
        return _khoang(nen)[0] + (kick_h + KICKER_GAP if kicker else 0)

    def _box_min(nen=1.0, f_t=None, d_t=None):
        """Chieu cao toi thieu textbox de chua het chu, o mot he so nen."""
        _g1, _g2, g3, g4 = _khoang(nen)
        return _cao_dau(nen) + _cao_tieu_de(f_t, d_t) + g3 + max(via_h, 34) + g4

    nen = 1.0
    box_min = _box_min()
    if ratio in RATIOS:
        # Khoa ti le dau ra. Kieu tran KHONG thuong luong chieu cao: anh phu
        # kin the va textbox la mot lop DE LEN anh, khong ai lan cho ai.
        H = RATIOS[ratio]
        if nat_h >= H:
            # Anh du cao: chu de len anh, vung chu lay phan da dinh.
            box_h = max(box_min, int(H * TRAN_TEXTBOX))
        else:
            # Anh thap: nen cua vung chu cao len bu dung phan anh thieu. Chu
            # can nhieu hon the thi vung chu an nguoc len day anh, va man toi
            # lo phan chuyen tiep.
            box_h = max(box_min, H - nat_h)
        if H - box_h != img_h:
            img_h, how = H - box_h, "letterbox"
        # Cho trong con lai danh cho tieu de no, chan o TRAN_TITLE_LINES dong.
        _g1, _g2, _g3, _g4 = _khoang(nen)
        frame_h = _cao_dau(nen) + _g3 + max(via_h, 34) + _g4
        f_title, title_lines = _grow_title(probe, title.upper(), avail_w,
                                           box_h - frame_h,
                                           max_lines=TRAN_TITLE_LINES,
                                           lead=lead, path=F_HERO,
                                           weight=HERO_WEIGHT, do_that=True,
                                           hi=TRAN_TITLE_MAX)
    else:
        box_h = box_min
        H = img_h + box_h

    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    _tran_anh(canvas, src_img, img_h, nat_h)
    d = ImageDraw.Draw(canvas)
    # Kieu tran KHONG ve khung, khong mot net nao: anh, man toi, chu. Het.
    g1, _g2, g3, g4 = _khoang(nen)

    # Kieu tran khong co ranh gioi anh/chu, nen nhan (kicker) tut han xuong
    # thanh hang dau tien cua khoi chu. Khi khoa ti le, CAN GIUA DOC ca cum
    # (kicker + tieu de) TRUOC khi ve — kicker va tieu de phai troi cung nhau.
    y = img_h + g1
    if ratio != "free":
        _cao_cum = (kick_h + KICKER_GAP if kicker else 0) + _cao_tieu_de()
        _thua = (H - g4 - via_h - g3) - y - _cao_cum
        if _thua > 0:
            y += _thua // 2
    if kicker:
        mau_kick = _pha(CYAN, 1.0)
        rong_chu = _rong_tracked(d, kicker, f_kick, KICKER_TRACK)
        # Tru _kb[1] de DINH chu roi dung vao y, khong phai goc ascender.
        _ve_tracked(d, (W - rong_chu) / 2, y - _kb[1], kicker, f_kick,
                    mau_kick, KICKER_TRACK)
        # Hai duong ke hai ben. Ca cum rong dung KICKER_CUM cua the, nen ke
        # NGAN LAI khi chu dai ra — cum giu nguyen be ngang, chu khong phai
        # ke giu nguyen do dai. Chu qua dai thi khong con cho, bo ke di.
        rong_ke = (W * KICKER_CUM - rong_chu) / 2 - KICKER_HO
        if rong_ke >= 24:
            giua = y + kick_h / 2
            trai = (W - rong_chu) / 2 - KICKER_HO
            d.line([(trai - rong_ke, giua), (trai, giua)],
                   fill=mau_kick, width=2)
            d.line([(W - trai, giua), (W - trai + rong_ke, giua)],
                   fill=mau_kick, width=2)
        y += kick_h + KICKER_GAP

    # Tieu de can giua: chu noi tren anh, truc doi xung cua tam anh la moc duy
    # nhat. Ve TUNG TU (de to ten thuong hieu) nen do be ngang dung cach do.
    def _x_chu(ln, font):
        return (W - _rong_dong(d, ln, font)) / 2

    che_do_to = b.get("to_ten_hang")
    mau_du_phong = b.get("mau_du_phong")
    # Dat dong dau bang DINH CHU chu khong bang goc ve: nho vay khoang ho toi
    # kicker khong doi theo viec dong do co dau hay khong.
    buoc, tren = _buoc_dong(f_title, title_lines, lead)
    for ln in title_lines:
        _ve_dong(d, _x_chu(ln, f_title), y - tren, ln, f_title, FG,
                 che_do_to, mau_du_phong)
        y += buoc

    # Chan the chi con TEN KENH, can giua. Nguon van phai ghi, nhung ghi o chu
    # thich bai dang; mot hero image dung mot minh thi cai phai nho la TEN KENH.
    bottom_y = H - g4 - via_h
    f_handle = _f(F_REG, max(12, round(BRAND_SIZE * co_chan)), weight=500)
    mau_handle = _pha(CYAN, b.get("ro_handle", mo_chan))
    ten = handle if handle.startswith("@") else "@" + handle
    bb = f_handle.getbbox("Ay")
    d.text(((W - d.textlength(ten, font=f_handle)) / 2,
            bottom_y + via_h / 2 - (bb[3] - bb[1]) / 2 - bb[1]),
           ten, font=f_handle, fill=mau_handle)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, "PNG", optimize=True)
    print("the: {}x{} ({:.2f}:1) | anh: {}px ({}) | textbox: {}px".format(
        W, H, W / H, img_h, how, box_h))
    return out


def main():
    p = argparse.ArgumentParser(description="Dựng thẻ ảnh hero cho kênh AI")
    p.add_argument("--image", required=True)
    p.add_argument("--image2", default=None,
                   help="Anh NGANG thu hai, ghep DOC duoi --image trong cung khung "
                        "(dung khi anh chinh qua chu nhat ngang, thay vi crop mat tieu de)")
    p.add_argument("--title", required=True,
                   help="Cau trich dan (--kieu quote) hoac cau tieu de tron ven (--kieu tran)")
    p.add_argument("--handle", default=None,
                   help="Ghi de ten kenh; mac dinh lay theo --brand")
    p.add_argument("--nhan-vat", default="",
                   help="Ten nguoi trong anh, BAT BUOC neu anh co mat nguoi. Phai la "
                        "nhan vat duoc nhac trong bai (CEO phat bieu, tac gia paper); "
                        "anh nguoi vo danh doc ra la anh stock.")
    p.add_argument("--bo-qua-anh", action="store_true",
                   help="Bo qua cong chan chart di mot minh vao hero (chi dung khi "
                        "da nhin tan mat va chac chan muon chart dung mot minh)")
    p.add_argument("--bo-qua-dau", action="store_true",
                   help="Bo qua kiem tra tieng Viet khong dau (chi dung khi chu "
                        "that su la tieng Anh)")
    p.add_argument("--brand", default="donniechublog",
                   choices=sorted(THUONG_HIEU),
                   help="Bo nhan dien: donniechublog (xanh dem) hoac dcgr (trang den)")
    p.add_argument("--tagline", default="daily AI update",
                   help="Chip tagline o goc duoi-trai khung quote (chip category)")
    p.add_argument("--kicker", default="",
                   help="Nhan ngan phia tren tieu de, CHI co o --kieu tran. "
                        "Vi du: BREAKING, MODEL RELEASE, AGENT, FUNDING")
    p.add_argument("--kieu", default="quote", choices=["quote", "tran"],
                   help="quote: the trich dan — cau noi lon trong ngoac kep, co dong "
                        "nguon o duoi (--title la cau, --attrib la nguon). "
                        "tran: anh phu kin the, tieu de de len qua man toi.")
    p.add_argument("--attrib", default="",
                   help="Dong nguon cho --kieu quote, vi du: "
                        "\"Doc bai 'Ten bai' - Tac gia\"")
    p.add_argument("--ratio", default="free",
                   choices=["free"] + list(RATIOS),
                   help="free: chiều cao trôi theo ảnh. 1:1/4:5/3:4: khoá tỉ lệ")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    build([a.image, a.image2] if a.image2 else a.image, a.title, a.out,
          handle=a.handle, ratio=a.ratio, tagline=a.tagline, brand=a.brand,
          bo_qua_dau=a.bo_qua_dau, kieu=a.kieu, kicker=a.kicker, attrib=a.attrib,
          bo_qua_anh=a.bo_qua_anh, nhan_vat=a.nhan_vat)


if __name__ == "__main__":
    main()
