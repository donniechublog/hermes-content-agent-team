#!/usr/bin/env python3
"""Dựng thẻ ảnh cho kênh AI — chiều cao co giãn theo tỉ lệ ảnh gốc.

Nguyên tắc bố cục:
  - Bề ngang cố định 1200px. Ảnh gốc giữ NGUYÊN tỉ lệ, trải hết bề ngang.
    Không cắt, không lẹm mất nội dung nào.
  - Textbox bên dưới co giãn: ảnh càng ngang (16:9) thì textbox càng cao,
    vừa cân bố cục vừa có chỗ cho tiêu đề lớn.
  - Ảnh quá ngang (>2:1) hoặc quá dọc (>1:1) thì mới thu vừa khung giới hạn,
    nền lấp bằng chính ảnh đó làm mờ — vẫn không mất nội dung.
  - Mascot góc trên-phải, ≤10% chiều cao vùng ảnh.
  - Font Be Vietnam Pro. Icon là logo SVG chính chủ, tô âm bản.
"""
import argparse
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ASSETS = Path(__file__).resolve().parent / "assets"
FONTS = ASSETS / "fonts"
ICONS = ASSETS / "icons"

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
IMG_MIN_H = 600                   # ảnh không mỏng hơn 2:1
IMG_MAX_H = 1200                  # ảnh không cao hơn 1:1
SUB_GROW_MAX = 50                 # cỡ tối đa phụ đề được nở tới khi còn chỗ
# Ảnh luôn được giữ ít nhất chừng này phần chiều cao thẻ — chữ phải nhường,
# không được lấn. Bảng số bị thu nhỏ là mất dữ liệu; phụ đề ngắn đi một dòng
# thì không mất gì.
TY_LE_ANH_TOI_THIEU = 0.72
# Kieu tran chi duoc phong anh toi muc nay de phu kin the. Qua nguong thi
# nen mo + anh sac dat len, vi vo net la mat noi dung.
NGUONG_PHONG = 1.35
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
        "mascot": "mascot.png",
        "nhan_trai": True,
        "socials": ["telegram", "linkedin", "x-twitter", "tiktok", "youtube"],
        # Ten hang trong tieu de lay CYAN cua bo nhan dien. Bang mau nay da co
        # mot mau nhan manh roi, muon them mau rieng cua tung hang nua thi doi
        # "cyan" thanh "hang" o day, khong phai sua cho nao khac.
        "to_ten_hang": "cyan",
        # Phu de keo ve gan FG thay vi mau MUTED xam: xam qua thi cau dan
        # chuyen bi chim, doc luot qua la mat. Giong muc dcgr dang dung.
        "ro_phu_de": 1.0,
        # Ten kenh ro va dung mau CYAN nhan dien; hang icon mo han xuong.
        "ro_handle": 1.0,
        "mo_icon": 0.34,
        "mau": {
            "BG": (14, 17, 23), "BG_CARD": (22, 27, 34),
            "FG": (230, 237, 243), "MUTED": (139, 147, 158),
            "ACCENT": (88, 166, 255), "ACCENT_DIM": (31, 111, 235),
            "CYAN": (0, 204, 224), "LINE": (48, 54, 61),
        },
    },
    # dcgr.tech: chi trang va den. Khong mascot mau — mot hinh nhieu mau giua
    # bang mau don sac se pha vo chinh cai lam nen nhan dien cua no.
    "dcgr": {
        "handle": "dcgr.tech",
        "mascot": None,
        # Bang mau chi co trang va den, nen to ten hang bang mau nhan cua bo
        # nhan dien la vo nghia: mau nhan o day CHINH LA mau chu. Mau thu ba
        # cua no khong phai mot mau co dinh them vao bang, ma la mau cua chinh
        # chu the dang duoc nhac toi — nhac Spotify thi ra xanh la Spotify.
        # Nho vay bang mau van don sac o moi cho khac, va cham mau duy nhat tren
        # the luon mang y nghia.
        "to_ten_hang": "hang",
        "mau_du_phong": (255, 176, 32),   # hang chua biet mau: ho phach
        # Chi giu nhan phai. Nhan trai nen dac mau nhan, ma o bang don sac no
        # thanh mot khoi trang lon hut het mat khoi noi dung.
        "nhan_trai": False,
        "socials": ["telegram", "linkedin", "x-twitter", "tiktok", "youtube"],
        # Cum via va hang social la thong tin PHU: lam mo va thu nho de chung lui
        # ve sau, nhuong mat cho tieu de va phu de.
        "co_chan": 0.85,        # co chu + icon o chan the: 85% co goc
        "mo_chan": 0.55,        # do sang chu chan, 1.0 la bang FG
        "ro_phu_de": 1.0,      # phu de sang gan bang FG thay vi mau MUTED xam
        # Ten kenh la nhan dien, khong phai chu thich: no phai doc ro. Chi cum
        # "via:" va hang icon moi lui ve sau theo mo_chan.
        "ro_handle": 0.95,
        "mo_icon": 0.34,
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
SOCIALS = []
MASCOT_PATH = None


def dat_thuong_hieu(ten: str):
    """Nap bang mau, mascot va danh sach social cua mot thuong hieu."""
    global BG, BG_CARD, FG, MUTED, ACCENT, ACCENT_DIM, CYAN, LINE
    global SOCIALS, MASCOT_PATH
    b = THUONG_HIEU.get(ten)
    if b is None:
        raise SystemExit(f"Khong biet thuong hieu {ten!r}. "
                         f"Co: {', '.join(sorted(THUONG_HIEU))}")
    m = b["mau"]
    BG, BG_CARD = m["BG"], m["BG_CARD"]
    FG, MUTED = m["FG"], m["MUTED"]
    ACCENT, ACCENT_DIM = m["ACCENT"], m["ACCENT_DIM"]
    CYAN, LINE = m["CYAN"], m["LINE"]
    SOCIALS = list(b["socials"])
    MASCOT_PATH = (ASSETS / b["mascot"]) if b.get("mascot") else None
    return b

MASCOT_MAX_H_RATIO = 0.10
MASCOT_MARGIN = 44

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
CHIP_SIZE = 26
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
# Man toi cua quote bat dau tan tu day len; tren nguong nay hoan toan trong de
# nhan vat tho nguyen, khong lo mot duong mep nao (cung bai voi _tran_anh).
QUOTE_FADE_TOP = 0.38


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


def _grow_sub(d, text, max_w, max_h, max_lines=2):
    """Chon co chu lon nhat cho phu de ma van vua cho trong con lai.

    Khi anh khong an het chieu cao, textbox thua ra kha nhieu — de phu de o co
    nho nhat mot dong thi phi cho va nhin trong rong. No ra toi 2 dong.
    """
    best = None
    for size in range(SUB_GROW_MAX, 20, -1):
        f = _f(F_SUB, size)
        lines = _wrap(d, text, f, max_w)
        if len(lines) > max_lines:
            continue
        if _line_h(f, 6) * len(lines) <= max_h:
            best = (f, lines)
            break
    return best or (_f(F_SUB, SUB_SIZE), _wrap(d, text, _f(F_SUB, SUB_SIZE), max_w)[:max_lines])


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


def _fit_contain(img, box_w, box_h):
    scale = min(box_w / img.width, box_h / img.height)
    nw, nh = max(1, round(img.width * scale)), max(1, round(img.height * scale))
    return img.resize((nw, nh), Image.LANCZOS)


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


def _plan_image(src_img):
    """Tính chiều cao vùng ảnh và cách đặt — không bao giờ cắt nội dung."""
    natural_h = round(W * src_img.height / src_img.width)
    if IMG_MIN_H <= natural_h <= IMG_MAX_H:
        return natural_h, "exact"          # trường hợp phổ biến: 16:9, 4:3, 1:1
    if natural_h < IMG_MIN_H:
        return IMG_MIN_H, "letterbox"      # ảnh siêu ngang (panorama)
    return IMG_MAX_H, "letterbox"          # ảnh dọc


def _render_image_area(canvas, src_img, img_h, how):
    """Ve vung anh. Tra ve o chu nhat (x, y, rong, cao) ma ANH THAT chiem cho.

    Can o nay de dat mascot: uu tien tren het la HIEN DAY DU anh nguon. Anh
    bang so hay bieu do ma bi che mot goc la mat du lieu, khong chap nhan duoc.
    """
    if how == "exact":
        canvas.paste(src_img.resize((W, img_h), Image.LANCZOS), (0, 0))
        return (0, 0, W, img_h)          # anh phu kin, khong con cho trong
    blur = _fit_cover(src_img, W, img_h).filter(ImageFilter.GaussianBlur(48))
    blur = ImageEnhance.Brightness(blur).enhance(0.38)
    canvas.paste(blur, (0, 0))
    # KHONG thut le. Truoc day inset=40 moi ben, cong voi viec anh da phai ha
    # chieu cao de chua cho chu, lam bang benchmark 1200x979 chi con hien o
    # 1030x840 — thu hep vo co gan 15% be ngang. Uu tien la HIEN DAY DU va TO
    # NHAT co the; vien mo hai ben chi la phan thua, khong phai bo cuc.
    fitted = _fit_contain(src_img, W, img_h)
    x, y = (W - fitted.width) // 2, (img_h - fitted.height) // 2
    canvas.paste(fitted, (x, y))
    # Chi ve vien khi anh KHONG cham mep — cham mep roi thi vien la thua
    if fitted.width < W - 2 or fitted.height < img_h - 2:
        ImageDraw.Draw(canvas).rectangle(
            [x - 1, y - 1, x + fitted.width, y + fitted.height],
            outline=(*LINE, 255), width=2)
    return (x, y, fitted.width, fitted.height)


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


def _man_quote(canvas):
    """Man toi cho kieu quote: gradient tu day len, to bang mau nen brand (BG),
    KHONG den tuyen. Tan ve 0 tren dinh khoi chu (`QUOTE_FADE_TOP`) theo duong
    cong power nen khong lo duong mep — nhan vat o nua tren tho nguyen. Chua
    max ~236 chu khong 255, de day anh con thoang thay chu khong thanh mang det."""
    H = canvas.height
    top = int(H * QUOTE_FADE_TOP)
    man = Image.new("L", (1, H), 0)
    for y in range(H):
        if y <= top:
            a = 0
        else:
            t = (y - top) / max(1, H - top)
            a = int(236 * (t ** 0.82))
        man.putpixel((0, y), min(255, a))
    lop = Image.new("RGBA", (W, H), (*BG, 255))
    lop.putalpha(man.resize((W, H)))
    canvas.alpha_composite(lop)


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
    """The pull-quote: mot cau trich dan lon tren anh phu kin.

    Khac hero image (mot tieu de bao quat tin) va carousel (nhieu slide): day la
    MOT cau noi dat trong ngoac kep, co dong nguon o duoi — dung dang the trich
    dan cua bao. Anh phu kin + man toi lien mach lo cung mot bai voi kieu tran;
    chu nam o ~35% day, nhan vat tho nguyen o tren.
    """
    H = RATIOS.get(ratio) or RATIOS["4:5"]     # quote luon khoa khung; free -> 4:5
    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    src_img = Image.open(src).convert("RGB")
    # ANH LUON HIEN FULL BE NGANG, KHONG CAT HAI CANH (Ong Chu bat loi 03/09/2026:
    # cover-crop lam mat tieu de cua slide/bang nguon, anh doc ra vo nghia).
    # Nen: ban cover LAM MO + toi phu kin khung; lop sac: anh nguyen ti le,
    # full W, dat sat tren (chu quote nam duoi). Anh cao hon khung thi chi cat
    # theo chieu doc, giu tron be ngang. Dong nhip voi carousel._body_image.
    nen = _fit_cover(src_img, W, H).filter(ImageFilter.GaussianBlur(40))
    nen = ImageEnhance.Brightness(nen).enhance(0.5)
    canvas.paste(nen, (0, 0))
    nat_h = round(src_img.height * W / src_img.width)
    sac = src_img.resize((W, nat_h), Image.LANCZOS)
    if nat_h > H:
        top = (nat_h - H) // 2
        sac = sac.crop((0, top, W, top + H))
    canvas.paste(sac, (0, 0))
    _man_quote(canvas)                                # man toi lien mach

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

    # Tagline ngan cua kenh — dong NHO o DAY the. KHONG phai ten kenh (ten kenh
    # la brand text, da o goc TREN); day chi la mot dong tagline mo ta ngan.
    f_tag = _f(F_QUOTE_REG, 23)
    tag = (tagline or "").strip()
    tag_lh = _line_h(f_tag, 8)
    tag_h = tag_lh if tag else 0

    f_mark = _f(F_MARK, MARK_SIZE)
    ob = f_mark.getbbox("“")          # dau mo "
    cb = f_mark.getbbox("”")          # dau dong "
    open_h, close_h = ob[3] - ob[1], cb[3] - cb[1]

    # KHUNG CHU NHAT BO GOC bao quanh quote; dau " gan goc TL/BR (xem _quote_frame).
    # BO CUC (Ong Chu chot 03/09/2026): hai CHIP CUOI LEN NET KHUNG — net di qua
    # tam chip theo chieu doc, nhu nhan dan tren hop:
    #   - chip ten kenh (cyan) o goc TREN-PHAI khung, tren net ngang tren
    #   - chip tagline (trang) o goc DUOI-TRAI khung, tren net ngang duoi
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

    # Cac dong quote, canh trai (thut vao TEXT_X).
    qy = first_line_top
    for ln in q_lines:
        d.text((TEXT_X, qy - tren), ln, font=f_q, fill=FG)
        qy += buoc

    # MAU: net khung dung CYAN cua bo nhan dien (nhu ten kenh, dong tong voi the
    # cua Bob); DAU " doi theo hang duoc nhac trong chu de (quote hoac dong
    # nguon). Khong nhan ra hang nao thi dau cung CYAN.
    mau_hang = _mau_hang_trong(quote) or _mau_hang_trong(attrib)
    mark_col = _du_sang(mau_hang) if mau_hang else CYAN
    _quote_frame(d, FRAME_X, frame_top, W - FRAME_X, frame_bottom,
                 CYAN, mark_col)

    # Dong nguon (attribution), CANH GIUA, sat day.
    ay = src_top
    for ln in at_lines:
        lw_ln = d.textlength(ln, font=f_at)
        d.text(((W - lw_ln) / 2, ay), ln, font=f_at, fill=_pha(FG, 0.72))
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
    aw = (fx1 - fx0) // 3                     # 1/3 net ngang cua _quote_frame
    # Chip ten kenh: goc TREN-PHAI, tam chip nam tren net ngang tren. Keo net
    # ngang tren tu cuoi doan co san (fx0+aw) sang toi chip de net "xuyen" chip.
    tb_h = d.textbbox((0, 0), ten, font=f_hchip)
    hw = (tb_h[2] - tb_h[0]) + 2 * 22
    hx0 = fx1 - CHIP_INSET - hw
    d.line([(fx0 + aw, frame_top), (hx0 + hw // 2, frame_top)], fill=CYAN, width=5)
    _chip_neo(ten, f_hchip, frame_top - chip_h // 2, "l", CYAN, (0, 0, 0), x=hx0)
    if tag:
        # Chip tagline: goc DUOI-TRAI, tam chip tren net ngang duoi (yb). Keo net
        # ngang duoi tu chip sang toi dau doan co san (fx1-aw).
        tb_t = d.textbbox((0, 0), tag, font=f_tchip)
        tw_ = (tb_t[2] - tb_t[0]) + 2 * 22
        tx0 = fx0 + CHIP_INSET
        d.line([(tx0 + tw_ // 2, yb), (fx1 - aw, yb)], fill=CYAN, width=5)
        _chip_neo(tag, f_tchip, yb - chip_h // 2, "l", (255, 255, 255), (0, 0, 0), x=tx0)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, "PNG", optimize=True)
    print("the: {}x{} ({:.2f}:1) | kieu: quote | {} dong quote".format(
        W, H, W / H, len(q_lines)))
    return out


def _chip_size(d, text, font, pad_x=18, pad_y=12):
    b = font.getbbox("Ây")
    return (d.textlength(text, font=font) + pad_x * 2,
            (b[3] - b[1]) + pad_y * 2)


def _chip(d, x, y, text, font, pad_x=18, pad_y=12, right_align=None,
          solid=False, fold=None):
    """Nhan category, co tam giac gap o canh tao cam giac hinh khoi.

    Tam giac dung mau toi hon (ACCENT_DIM) nhu mot mat bi khuat sang — thu
    phap ruy-bang quen thuoc, khien the noi len khoi mat phang cua anh.
    """
    bw, bh = _chip_size(d, text, font, pad_x, pad_y)
    if right_align is not None:
        x = right_align - bw
    b = font.getbbox("Ây")
    # Cao dung bang nua tren cua the — the vat qua mep textbox nen nua tren
    # chinh la phan de len anh; lay dung so nay thi tam giac cham sat mep,
    # khong con khe ho.
    fold_w = bh // 2

    if solid:
        d.rectangle([x, y, x + bw, y + bh], fill=CYAN)
        d.text((x + pad_x, y + pad_y - b[1]), text, font=font, fill=BG)
    else:
        d.rectangle([x, y, x + bw, y + bh], fill=BG_CARD, outline=CYAN,
                    width=2)
        d.text((x + pad_x, y + pad_y - b[1]), text, font=font, fill=FG)

    # Tam giac gap, cung mau than the. CA HAI deu bam canh PHAI cua the — truoc
    # day the phai gap sang trai nen hai the doi dinh vao nhau, nhin nhu bi hut
    # vao giua. Cung huong thi nhip deu va mat di theo mot chieu.
    if fold == "down":
        # HAI tam giac doi xung tren duoi, khoet mot chu V o dau phai — dung
        # hinh duoi ruy bang. Mot tam giac don chi giong goc bi gap, hai cai
        # moi doc ra la dai bang.
        d.polygon([(x + bw, y), (x + bw + fold_w, y), (x + bw, y + fold_w)],
                  fill=CYAN)
        d.polygon([(x + bw, y + bh), (x + bw + fold_w, y + bh),
                   (x + bw, y + bh - fold_w)], fill=CYAN)
    elif fold == "up":
        tri = [(x + bw, y), (x + bw, y + fold_w), (x + bw + fold_w, y + fold_w)]
        d.polygon(tri, fill=BG_CARD)
        d.line(tri + [tri[0]], fill=CYAN, width=2)
    return bw, bh


def _de_len(a, b, ho=8) -> bool:
    """Hai o chu nhat co cham nhau khong (cong mot khoang ho cho de tho)."""
    ax, ay, aw, ah = a
    bx, by, bw, bh = b
    return not (ax + aw + ho <= bx or bx + bw + ho <= ax
                or ay + ah + ho <= by or by + bh + ho <= ay)


def _paste_mascot(canvas, img_h, o_anh):
    """Dat mascot vao goc KHONG che anh. Khong con goc nao trong thi BO HAN.

    Truoc day mascot luon dan cung mot cho o goc tren-phai, nen voi anh phu kin
    khung no che mat mot phan noi dung — da gap that: che cot Opus-4.8 cua mot
    bang benchmark. Nhan dien thuong hieu da co goc cyan, nhan category, tieu de
    va dai mang xa hoi; thieu mascot mot the khong mat nhan dien, con che mat so
    lieu thi hong ca tam anh.
    """
    if MASCOT_PATH is None or not MASCOT_PATH.exists():
        return
    mascot = Image.open(MASCOT_PATH).convert("RGBA")
    th = int(img_h * MASCOT_MAX_H_RATIO)
    tw = int(th * mascot.width / mascot.height)
    m = MASCOT_MARGIN
    # Thu bon goc cua vung anh, uu tien tren-phai nhu cu
    goc = [(W - tw - m, m), (m, m),
           (W - tw - m, img_h - th - m), (m, img_h - th - m)]
    for x, y in goc:
        if y < 0 or x < 0:
            continue
        if not _de_len((x, y, tw, th), o_anh):
            canvas.alpha_composite(mascot.resize((tw, th), Image.LANCZOS), (x, y))
            return
    # Moi goc deu de len anh -> khong dan mascot


_ICON_CACHE = {}          # (name, size, color) -> Image; icon tinh, doi duoc


def _load_icon(name, size, color):
    """Doc SVG icon qua rsvg-convert, co CACHE — 5 icon social duoc goi lai moi
    lan render, khong co ly do gi chay lai subprocess moi lan. Thieu binary thi
    canh bao MOT lan ro rang thay vi de icon lang le bien mat."""
    khoa = (name, size, color)
    if khoa in _ICON_CACHE:
        return _ICON_CACHE[khoa]
    src = ICONS / (name + ".svg")
    if not src.exists():
        _ICON_CACHE[khoa] = None
        return None
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        out = tmp.name
    try:
        subprocess.run(["rsvg-convert", str(src), "-w", str(size),
                        "-h", str(size), "-o", out],
                       check=True, capture_output=True, timeout=20)
        icon = Image.open(out).convert("RGBA")
    except Exception as e:                                   # noqa: BLE001
        if not _ICON_CACHE.get("_da_bao"):
            _ICON_CACHE["_da_bao"] = True
            print(f"[canh bao] khong render duoc icon SVG ({type(e).__name__}) "
                  f"— thieu rsvg-convert? Icon social se KHONG hien.",
                  file=sys.stderr)
        _ICON_CACHE[khoa] = None
        return None
    finally:
        Path(out).unlink(missing_ok=True)
    tinted = Image.new("RGBA", icon.size, (*color, 0))
    tinted.putalpha(icon.split()[-1])
    _ICON_CACHE[khoa] = tinted
    return tinted


def _pha(mau, do_sang: float, nen=None):
    """Tron mau ve phia nen de lam mo. do_sang=1.0 giu nguyen, 0 la bang nen."""
    nen = nen if nen is not None else BG
    t = max(0.0, min(1.0, do_sang))
    return tuple(int(n + (c - n) * t) for c, n in zip(mau, nen))


def _social_row(canvas, d, right_x, cy, handle, font, icon_size=39, gap=15,
                mau_chu=None, mau_icon=None):
    """Hang icon + ten kenh, can sat le phai. Cung tong mau voi cum via."""
    mau_chu = mau_chu if mau_chu is not None else ACCENT
    mau_icon = mau_icon if mau_icon is not None else FG
    handle_text = handle if handle.startswith("@") else "@" + handle
    b = font.getbbox("Ay")
    tw = d.textlength(handle_text, font=font)
    x = right_x - tw
    d.text((x, cy - (b[3] - b[1]) / 2 - b[1]), handle_text, font=font,
           fill=mau_chu)
    x -= gap + 4
    for name in reversed(SOCIALS):
        icon = _load_icon(name, icon_size, mau_icon)
        x -= icon_size
        if icon is not None:
            canvas.alpha_composite(icon, (int(x), int(cy - icon_size / 2)))
        x -= gap





def _tech_frame(d, H, split, box_col, vach=True):
    m, brk = 18, 46
    # Hai goc tren: mau nhan. Hai goc duoi: mau trang, cung do day.
    for (x, y, dx, dy, col) in ((m, m, 1, 1, CYAN),
                                (W - m, m, -1, 1, CYAN),
                                (m, H - m, 1, -1, FG),
                                (W - m, H - m, -1, -1, FG)):
        d.line([(x, y), (x + dx * brk, y)], fill=col, width=3)
        d.line([(x, y), (x, y + dy * brk)], fill=col, width=3)
    # Vung anh KHONG ve net doc hai ben nua: anh nay chay sat mep nen net chi
    # cat vao noi dung, khong con vai tro khung.
    # Hai net doc trong textbox — mau nghich voi net o vung anh, tao nhip
    for x in (m, W - m):
        d.line([(x, split + 12), (x, H - m - brk - 12)], fill=box_col, width=2)
    # Kieu tran khong ve vach: vach la thu bien anh va chu thanh hai o rieng,
    # dung noi ma chinh no la cai can bo.
    if not vach:
        return
    d.line([(0, split), (int(W * 0.34), split)], fill=LINE, width=2)
    d.line([(int(W * 0.42), split), (W, split)], fill=LINE, width=2)
    d.line([(int(W * 0.34), split), (int(W * 0.40), split)],
           fill=ACCENT, width=3)


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


def build(src, title, subtitle, via, out, category="AI",
          category_right="", handle=None, ratio="free",
          tagline="daily AI update", brand="donniechublog",
          bo_qua_dau=False, kieu="dai", kicker="", attrib=""):
    # Nap bang mau TRUOC moi thu khac: cac ham ve doc BG/FG/ACCENT o pham vi
    # module, chua nap thi chung con la None.
    b = dat_thuong_hieu(brand)
    handle = handle or b["handle"]
    title, subtitle = bo_dau_cam(title), bo_dau_cam(subtitle)
    attrib = bo_dau_cam(attrib)

    # Chan tieng Viet khong dau TRUOC khi ve, o moi cho chu hien len the.
    loi = {}
    for ten, gt in (("tieu de", title), ("phu de", subtitle),
                    ("category", category), ("category-right", category_right),
                    ("via", via), ("nguon", attrib)):
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
    # Kieu quote co duong ve rieng (anh phu kin + cau trich dan + dong nguon),
    # khong di qua logic dai/tran ben duoi. Dat NGAY sau cong tieng Viet co dau.
    if kieu == "quote":
        return _render_quote(src, title, attrib, out, handle, ratio, tagline)
    if kieu != "tran" and not (subtitle or "").strip():
        raise SystemExit(
            "Thieu --subtitle. The tin kieu dai can phu de: tieu de chi la nhan\n"
            "  de, phu de moi mang noi dung. (Hero image --kieu tran thi khong\n"
            "  can, vi o do tieu de la mot cau tron ven.)")
    src_img = Image.open(src).convert("RGB")
    img_h, how = _plan_image(src_img)
    # Chieu cao tu nhien cua anh khi hien full be ngang. Kieu tran khong dung
    # `_plan_image`: ham do chan chieu cao trong khoang IMG_MIN_H..IMG_MAX_H de
    # thu vua vung anh cua the tin, con o day anh la lop nen nen khong co tran.
    nat_h = round(W * src_img.height / src_img.width)
    if kieu == "tran":
        img_h, how = nat_h, "tran"

    # Đo trước phần chữ để biết textbox cần cao bao nhiêu
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    f_chip = _f(F_UI, CHIP_SIZE)
    co_chan = b.get("co_chan") or 1.0
    mo_chan = b.get("mo_chan") or 1.0
    # Hang icon social la thu it dang chu y nhat tren the: ai cung biet
    # no la gi, no khong mang thong tin. De no mo hon ca cum via.
    mo_icon = b.get("mo_icon") or round(mo_chan * 0.62, 2)
    f_via = _f(F_REG, max(12, round(VIA_SIZE * co_chan)), weight=500)
    avail_w = W - PAD * 2

    tran = kieu == "tran"
    lead = TRAN_LEAD if tran else LEAD
    so_dong_tieu_de = TRAN_TITLE_LINES if tran else 2
    # Hero image dung Oswald (khong chan, condensed); the tin giu JetBrains Mono
    # vi font don cach la mot phan nhan dien cua no.
    font_tieu_de = F_HERO if tran else F_BOLD
    do_day = HERO_WEIGHT if tran else None

    f_title, title_lines = _fit_text(probe, title.upper(), avail_w,
                                      max_lines=so_dong_tieu_de,
                                      hi=TITLE_SIZE_HI,
                                      lo=TITLE_SIZE_LO, bold=True,
                                      path=font_tieu_de, weight=do_day)

    # Kicker: nhan ngan phia tren tieu de. Chi co o kieu tran.
    kicker = (kicker or "").strip().upper() if tran else ""
    f_kick = _f(F_REG, KICKER_SIZE, weight=700)
    # Do CHIEU CAO CHU THAT chu khong dung _line_h. _line_h do bang bbox cua
    # "Ây" — co ca dau mu lan duoi chu y — vi no phuc vu chu tieng Viet co dau.
    # Kicker toan chu Latin viet hoa, khong dau, nen cach do do chua them gan 20px
    # troi o duoi, va cong voi khoang ho nua thi kicker troi han khoi tieu de.
    _kb = f_kick.getbbox(kicker) if kicker else (0, 0, 0, 0)
    kick_h = (_kb[3] - _kb[1]) if kicker else 0
    # Hero image khong co phu de. Van nap font de cac nhanh phia sau con doi
    # tuong de goi, nhung danh sach dong rong nen moi phep tinh chieu cao va moi
    # vong ve deu tu dong bo qua no.
    if tran:
        f_sub, sub_lines = _f(F_SUB, SUB_SIZE), []
    else:
        f_sub, sub_lines = _fit_text(probe, subtitle, avail_w, max_lines=3,
                                      hi=SUB_SIZE, lo=22)
    _, chip_h = _chip_size(probe, category.upper(), f_chip)
    via_h = f_via.getbbox("Ây")[3] - f_via.getbbox("Ây")[1]

    # Chieu cao phan DAU textbox, phan nam tren tieu de. Hai kieu an khac nhau:
    #   dai  — nhan VAT qua ranh gioi, chi nua duoi cua no roi vao textbox
    #   tran — nhan nam han trong khoi chu, an tron chieu cao cong hai khoang ho
    # Quen cho vao day thi phu de bi day tut xuong de len hang chan. Da gap that.
    def _cao_tieu_de(f=None, dong=None):
        """Chieu cao khoi tieu de. Kieu tran do that, kieu dai giu cach cu."""
        f, dong = f or f_title, dong if dong is not None else title_lines
        if tran:
            return _buoc_dong(f, dong, lead)[0] * len(dong)
        return _line_h(f, lead) * len(dong)

    def _cao_dau(nen=1.0):
        g1 = _khoang(nen)[0]
        # Kieu tran khong ve nhan category; phan dau la khoang ho, cong them
        # kicker neu co (kicker cong mot khoang ho nua truoc tieu de).
        if kieu == "tran":
            return g1 + (kick_h + KICKER_GAP if kicker else 0)
        return chip_h // 2 + g1

    # Chiều cao tối thiểu textbox cần để chứa hết chữ, ở một hệ số nén cho trước
    def _box_min(nen=1.0, f_t=None, d_t=None, f_s=None, d_s=None):
        g1, g2, g3, g4 = _khoang(nen)
        _dong_sub = d_s if d_s is not None else sub_lines
        # Khong co phu de thi khong cong ca chieu cao LAN khoang ho g2 truoc no.
        cao_sub = (g2 + _line_h(f_s or f_sub, LEAD) * len(_dong_sub)
                   if _dong_sub else 0)
        return (_cao_dau(nen)
                + _cao_tieu_de(f_t, d_t)
                + cao_sub + g3 + max(via_h, 34) + g4)

    nen = 1.0
    # Nhan category VAT qua ranh gioi anh/textbox — khau hai vung lam mot. No co
    # de len mep duoi cua anh, nhung Ong Chu da chot: che phan chu thich thi
    # chap nhan duoc, khong can khat khe. Chi mascot moi phai tranh, vi no nam
    # o giua vung anh chu khong o mep.
    box_min = _box_min()

    if ratio in RATIOS:
        # Khoá tỉ lệ đầu ra: textbox phình ra bù phần ảnh thiếu.
        # Ảnh càng ngang (16:9) thì textbox càng cao — đúng ý đồ bố cục.
        H = RATIOS[ratio]

        # Kieu tran KHONG thuong luong chieu cao. Ca doan duoi day sinh ra cho
        # kieu dai, noi anh va chu cat nhau mot chieu cao huu han nen phai co ai
        # do nhuong. O kieu tran anh phu kin the va textbox la mot lop DE LEN
        # anh, khong phai mot o cat ra tu the: khong ai lan cho ai, khong co gi
        # de nhuong. Chay nham vao day thi `min(H - img_h, ...)` ben duoi kep
        # vung chu xuong bang phan anh con thua, va tieu de bi ep nho lai.
        if not tran:
            #   1. NÉN khoảng trắng của khối nhận diện (chữ vẫn nguyên cỡ)
            #   2. RÚT phụ đề bớt dòng
            #   3. NỚI tỉ lệ thẻ cho cao hơn
            #   4. cuối cùng mới thu ảnh — và chỉ khi bị ép giữ tỉ lệ
            while H - img_h < box_min and nen > 0.55:
                nen = round(nen - 0.05, 2)
                box_min = _box_min(nen)
            # Rut phu de bot dong, nhung KHONG duoc rut den muc bi cat cut. Da gap:
            # ep xuong 1 dong thi phu de dai khong vua o co nho nhat nen bi thay
            # bang dau ba cham. Cat mat chu la mat noi dung, con nhuong them mot
            # chut chieu cao thi khong mat gi. Nen dung o 2 dong khi 1 dong se cat.
            while H - img_h < box_min and len(sub_lines) > 1:
                thu_f, thu_lines = _fit_text(probe, subtitle, avail_w,
                                             max_lines=len(sub_lines) - 1,
                                             hi=SUB_SIZE, lo=19)
                if "…" in "".join(thu_lines) and len(sub_lines) <= 2:
                    break                       # rut nua la cat mat chu, dung lai
                f_sub, sub_lines = thu_f, thu_lines
                box_min = _box_min(nen)

            if H - img_h < box_min:
                # Khoa ti le ma van muon chua du chu thi phai THU ANH — khong chap
                # nhan duoc, vi thu anh la mat noi dung. Thay vi vay, NOI TI LE ra
                # cao hon cho toi khi anh vua tron ven. Chi khi moi ti le deu khong
                # du moi danh thu, va bao ro ra man hinh.
                for ten_ti_le, cao in sorted(RATIOS.items(), key=lambda x: x[1]):
                    if cao <= H:
                        continue
                    if cao - img_h >= box_min:
                        ratio, H = ten_ti_le, cao
                        break
                else:
                    H = img_h + box_min              # tha the dai hon la thu anh
        # ANH LA CHINH, TEXTBOX LA PHU. Truoc day toan bo cho thua bi don het
        # vao textbox: khoa 4:5 thi chu chiem 58% chieu cao con anh 42%, nguoc
        # vai tro. Nay textbox chi lay phan chu that su can, tran o TRAN_TEXTBOX;
        # phan con lai tra cho vung anh, anh nam giua tren nen mo cung tong mau.
        if tran:
            # Anh hien full be ngang, nen chieu cao tu nhien cua no la con so
            # quyet dinh moi thu con lai.
            if nat_h >= H:
                # Anh du cao: chu de len anh, vung chu lay phan da dinh.
                box_h = max(box_min, int(H * TRAN_TEXTBOX))
            else:
                # Anh thap: nen cua vung chu cao len bu dung phan anh thieu.
                # Chu can nhieu hon the thi vung chu an nguoc len day anh, va
                # man toi lo phan chuyen tiep.
                box_h = max(box_min, H - nat_h)
        else:
            box_h = min(H - img_h, max(box_min, int(H * TRAN_TEXTBOX)))
        if H - box_h != img_h:
            img_h, how = H - box_h, "letterbox"
        # Chỗ trống chia theo thứ tự ưu tiên: khung cố định -> subtitle
        # (tối đa 3 dòng) -> phần còn lại dành cho tiêu đề nở, chặn ở 2 dòng.
        _g1, _g2, _g3, _g4 = _khoang(nen)
        frame_h = (_cao_dau(nen) + (_g2 if sub_lines else 0)
                   + _g3 + max(via_h, 34) + _g4)
        # Chia cho trong: tieu de truoc, phan con lai cho phu de. Neu textbox van
        # thua thi phu de no theo — thay vi de mot dong chu nho lo lung giua
        # khoang trong. O kieu tran khong co phu de nen tieu de an tron cho.
        sub_h = _line_h(f_sub, LEAD) * len(sub_lines)
        f_title, title_lines = _grow_title(probe, title.upper(), avail_w,
                                           box_h - frame_h - sub_h,
                                           max_lines=so_dong_tieu_de,
                                           lead=lead, path=font_tieu_de,
                                           weight=do_day, do_that=tran,
                                           hi=TRAN_TITLE_MAX if tran else None)
        con_lai = box_h - frame_h - _cao_tieu_de()
        if sub_lines and con_lai > sub_h + 12:
            f_sub, sub_lines = _grow_sub(probe, subtitle, avail_w, con_lai)
    else:
        box_h = box_min
        H = img_h + box_h

    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    if kieu == "tran":
        o_anh = _tran_anh(canvas, src_img, img_h, nat_h)
    else:
        o_anh = _render_image_area(canvas, src_img, img_h, how)
        _paste_mascot(canvas, img_h, o_anh)
    d = ImageDraw.Draw(canvas)
    # Mot he mau co dinh, khong phu thuoc anh sang hay toi:
    #   vung anh   -> cyan, dong bo voi hai ngoac goc TREN va nhan category
    #   vung chu   -> trang, dong bo voi hai ngoac goc DUOI
    # Kieu tran KHONG ve khung, khong mot net nao. Truoc day no van ve hai
    # ngoac goc va hai net doc trong vung chu, chi bo moi cai vach ngang. Nhung
    # ngoac goc chinh la mot cai vien, va net doc trong vung chu lai to ra dung
    # cai ranh gioi ma kieu tran sinh ra de xoa. Hero image lien mot mat phang:
    # anh, man toi, chu. Het.
    if kieu != "tran":
        _tech_frame(d, H, img_h, FG, vach=True)

    g1, g2, g3, g4 = _khoang(nen)

    # Cho dat nhan category khac han giua hai kieu.
    #
    # Kieu dai co ranh gioi that giua anh va textbox, va nhan duoc dat VAT qua
    # ranh gioi do de khau hai vung lam mot, dong thoi tra lai chieu cao textbox
    # cho tieu de.
    #
    # Kieu tran khong co ranh gioi nao. De nhan o cao do thi chinh nhan tro
    # thanh vat danh dau cai duong ma kieu tran sinh ra de xoa: nhin vao van
    # thay the bi chia hai, chi la duong ke doi thanh hai cai nhan. Nen o kieu
    # tran nhan tut han xuong, thanh hang dau tien cua khoi chu.
    # Kieu tran KHONG ve nhan category. Nhan ruy-bang la mot khoi dac bam mep,
    # sinh ra de khau hai vung cua the tin lam mot. Hero image khong co hai vung
    # de khau, va mot khoi mau dac bam mep lai keo mat ve phia le dung luc ca
    # khoi chu dang can giua. Bo di thi con lai dung bon thu: anh, tieu de,
    # phu de, ten kenh.
    if kieu == "tran":
        y = img_h + g1
        # CAN GIUA DOC truoc khi ve BAT KY thu gi. Truoc day khoi can giua nam
        # sau doan ve kicker: kicker dung yen o y cu con tieu de bi day xuong
        # `_cho_trong // 2`, ho ra toi 137px voi tieu de mot dong — pha dung
        # ban sua "kicker sat tieu de". Ca cum (kicker + tieu de + phu de) phai
        # troi xuong CUNG NHAU, nen phai dich y truoc.
        if ratio != "free":
            _cao_cum = ((kick_h + KICKER_GAP if kicker else 0)
                        + _cao_tieu_de()
                        + (g2 + _line_h(f_sub, LEAD) * len(sub_lines)
                           if sub_lines else 0))
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
    else:
        chip_y = img_h - chip_h // 2
        y = img_h + chip_h // 2 + g1
        if b.get("nhan_trai", True):
            _chip(d, PAD, chip_y, category.upper(), f_chip, solid=True,
                  fold="down")
        if category_right:
            _chip(d, 0, chip_y, category_right.upper(), f_chip,
                  right_align=W - PAD, fold="up")

    # Khi ti le bi khoa, tieu de va phu de da no het co cho phep ma textbox van
    # con thua thi day khoi chu xuong giua thay vi de no dinh sat mep tren va bo
    # lai mot mang trong o duoi. (Kieu tran da can o tren, TRUOC khi ve kicker —
    # can lai o day la kicker dung yen con tieu de troi.)
    if ratio != "free" and kieu != "tran":
        _cao_chu = (_cao_tieu_de()
                    + (g2 + _line_h(f_sub, LEAD) * len(sub_lines)
                       if sub_lines else 0))
        _cho_trong = (H - g4 - via_h - g3) - y - _cao_chu
        if _cho_trong > 0:
            y += _cho_trong // 2

    # Kieu tran can giua tieu de va phu de; kieu dai can trai.
    #
    # Can trai hop voi the tin vi o do chu nam trong mot textbox rieng, co mep
    # trai lam moc, va con nhan trai vat qua ranh gioi ngay phia tren cung mot
    # duong doc. Hero image khong con textbox, khong con moc nao: chu noi tren
    # anh, nen truc doi xung cua tam anh la moc duy nhat con lai.
    def _x_chu(ln, font):
        # O kieu tran tieu de duoc ve TUNG TU (de to ten thuong hieu), nen phai
        # do be ngang dung cach do — do ca chuoi mot lan se lech vai pixel.
        return (W - _rong_dong(d, ln, font)) / 2 if kieu == "tran" else PAD

    che_do_to = b.get("to_ten_hang") if tran else None
    mau_du_phong = b.get("mau_du_phong")
    # Dat dong dau bang DINH CHU chu khong bang goc ve: nho vay khoang ho toi
    # kicker khong doi theo viec dong do co dau hay khong.
    buoc, tren = (_buoc_dong(f_title, title_lines, lead) if tran
                  else (_line_h(f_title, lead), 0))
    for ln in title_lines:
        _ve_dong(d, _x_chu(ln, f_title), y - tren, ln, f_title, FG,
                 che_do_to, mau_du_phong)
        y += buoc
    if sub_lines:
        y += g2

    # Phu de mac dinh dung MUTED cho lui ve sau. Thuong hieu nao muon ro hon thi
    # keo mau ve phia FG theo `ro_phu_de` — chu van nhat hon tieu de nhung doc
    # duoc thoai mai.
    mau_sub = MUTED if b.get("ro_phu_de") is None else _pha(FG, b["ro_phu_de"])
    for ln in sub_lines:
        d.text((_x_chu(ln, f_sub), y), ln, font=f_sub, fill=mau_sub)
        y += _line_h(f_sub, LEAD)

    bottom_y = H - g4 - via_h
    f_handle = _f(F_REG, max(12, round(BRAND_SIZE * co_chan)), weight=500)
    mau_handle = _pha(CYAN, b.get("ro_handle", mo_chan))

    if kieu == "tran":
        # Chan the rut con DUNG ten kenh, can giua. Cum `via` va day icon deu
        # bam hai mep, ma o kieu tran hai mep khong con gi khac de bam vao: bo
        # khung roi, bo nhan roi, tieu de va phu de da ve giua. De lai chung thi
        # ca tam anh chi con hai vet dinh o hai goc duoi, keo mat ra khoi truc.
        #
        # Nguon van phai ghi, nhung ghi o cho khac: chu thich bai dang. Mot hero
        # image dung mot minh thi cai phai nho la TEN KENH.
        ten = handle if handle.startswith("@") else "@" + handle
        bb = f_handle.getbbox("Ay")
        d.text(((W - d.textlength(ten, font=f_handle)) / 2,
                bottom_y + via_h / 2 - (bb[3] - bb[1]) / 2 - bb[1]),
               ten, font=f_handle, fill=mau_handle)
    else:
        via_text = via if via.startswith("via:") else "via: " + via
        # Cum via lay CYAN cua bo nhan dien, giong ten kenh. Truoc day no dung
        # ACCENT (xanh duong) nen lech tong voi cyan o ngay ben canh.
        d.text((PAD, bottom_y), via_text, font=f_via, fill=_pha(CYAN, mo_chan))
        _social_row(canvas, d, W - PAD, bottom_y + via_h / 2, handle, f_handle,
                    icon_size=max(16, round(39 * co_chan)),
                    gap=max(8, round(15 * co_chan)),
                    mau_chu=mau_handle, mau_icon=_pha(FG, mo_icon))

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, "PNG", optimize=True)
    print("the: {}x{} ({:.2f}:1) | anh: {}px ({}) | textbox: {}px".format(
        W, H, W / H, img_h, how, box_h))
    return out


def main():
    p = argparse.ArgumentParser(description="Dựng thẻ ảnh cho kênh AI")
    p.add_argument("--image", required=True)
    p.add_argument("--title", required=True)
    # Bat buoc o kieu dai, bo qua o kieu tran (hero image khong co phu de).
    p.add_argument("--subtitle", default="")
    # Van nhan o ca hai kieu, nhung kieu tran khong ve ra: nguon duoc ghi o chu
    # thich bai dang thay vi tren the.
    p.add_argument("--via", default="")
    p.add_argument("--category", default="AI")
    p.add_argument("--category-right", default="")
    p.add_argument("--handle", default=None,
                   help="Ghi de ten kenh; mac dinh lay theo --brand")
    p.add_argument("--bo-qua-dau", action="store_true",
                   help="Bo qua kiem tra tieng Viet khong dau (chi dung khi chu "
                        "that su la tieng Anh)")
    p.add_argument("--brand", default="donniechublog",
                   choices=sorted(THUONG_HIEU),
                   help="Bo nhan dien: donniechublog (xanh dem) hoac dcgr (trang den)")
    p.add_argument("--tagline", default="daily AI update",
                   help="Mo ta ngan duoi ten kenh trong khoi thuong hieu")
    p.add_argument("--kicker", default="",
                   help="Nhan ngan phia tren tieu de, CHI co o --kieu tran. "
                        "Vi du: BREAKING, MODEL RELEASE, AGENT, FUNDING")
    p.add_argument("--kieu", default="dai", choices=["dai", "tran", "quote"],
                   help="dai: anh o tren, textbox rieng o duoi (mac dinh). "
                        "tran: anh phu kin the, chu de len qua man toi. "
                        "quote: the trich dan — cau noi lon trong ngoac kep, "
                        "co dong nguon o duoi (--title la cau, --attrib la nguon)")
    p.add_argument("--attrib", default="",
                   help="Dong nguon cho --kieu quote, vi du: "
                        "\"Doc bai 'Ten bai' - Tac gia\"")
    p.add_argument("--ratio", default="free",
                   choices=["free"] + list(RATIOS),
                   help="free: chiều cao trôi theo ảnh. 1:1/4:5/3:4: khoá tỉ lệ, "
                        "textbox phình ra bù phần ảnh thiếu")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    build(a.image, a.title, a.subtitle, a.via, a.out,
          a.category, a.category_right, a.handle, a.ratio, a.tagline,
          brand=a.brand,
          bo_qua_dau=a.bo_qua_dau, kieu=a.kieu, kicker=a.kicker, attrib=a.attrib)


if __name__ == "__main__":
    main()
