#!/usr/bin/env python3
"""Dựng thẻ ảnh hero cho kênh AI (vai designer / Ethan). Hai kiểu:

  - `quote` (mặc định): pull-quote 4:5 — ảnh phủ kín, câu trích dẫn lớn trong
    khung hai góc ngoặc, dòng nguồn canh giữa, chip tên kênh và tagline.
  - `full_bleed` (tràn; giá trị cũ `tran`, LOW-248): ảnh full bề ngang, tiêu
    đề MỘT câu đè lên qua khung chữ nhật nét, kicker ngắn phía trên, tên kênh
    canh giữa ở đáy.

Bề ngang cố định 1200px; ảnh không bao giờ bị cắt bề ngang (luật IMAGE_RULES.md).
Kiểu `dai` cũ (ảnh trên, textbox riêng dưới, nhãn category, hàng icon social,
mascot) đã bỏ 05/09/2026: từ khi cả đội chuyển sang một kiểu ảnh duy nhất,
không vai nào gọi tới nó nữa.

Chữ đè lên ảnh (cả hai kiểu): KHÔNG mặc định phủ lớp nào — chỉ làm mờ cục bộ
đúng vùng dưới chữ (`_open_region_text`) rồi đổi màu chữ theo độ sáng đo được
(`_color_change_background_hide_whole`). Độ sáng đo qua `_can_board_line` chứ không lấy trung
bình thuần: một dải chữ có mảng sáng cục bộ (áo trắng, cửa sổ, đèn sân khấu)
thì trung bình cả dải vẫn nói "nền tối" trong khi chữ chìm đúng chỗ mảng sáng
đó. Ngưỡng sáng/tối tính theo đúng cặp màu FG/BG của từng thương hiệu
(`text_bg.threshold_wall_part`), không còn một con số cố định dùng chung cho
mọi bảng màu.
"""
import argparse
import functools
import re
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont, ImageStat

import image_rules_ethan
import role_spec
import text_bg

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
CEILING_TEXTBOX = 0.30
TEXT_MAX_SHARE = 0.20                     # LOW-342: khoi chu (khong tinh le/chip) <= 20% chieu cao the
PAD = 44

# ---- Thuong hieu ----------------------------------------------------------
# Bo cuc, font va moi rang buoc bo cuc GIU NGUYEN giua cac thuong hieu — day la
# cung mot he thong the, chi khac lop son va danh tinh. Doi mau ma doi luon bo
# cuc thi thanh hai san pham khac nhau, mat cai loi cua viec dung chung code.
BRAND = {
    "donniechublog": {
        "handle": "donniechublog",
        # Ten hang trong tieu de lay CYAN cua bo nhan dien. Bang mau nay da co
        # mot mau nhan manh roi, muon them mau rieng cua tung hang nua thi doi
        # "cyan" thanh "company" o day, khong phai sua cho nao khac.
        "company_name_color": "cyan",
        # Ten kenh ro va dung mau CYAN nhan dien.
        "handle_clarity": 1.0,
        "palette": {
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
        "company_name_color": "company",
        "fallback_company_color": (255, 176, 32),   # hang chua biet mau: ho phach
        # Chan the la thong tin PHU: nho va mo hon de lui ve sau.
        "footer_size_scale": 0.85,        # co chu o chan the: 85% co goc
        "footer_brightness": 0.55,        # do sang chu chan, 1.0 la bang FG
        # Ten kenh la nhan dien, khong phai chu thich: no phai doc ro.
        "handle_clarity": 0.95,
        "palette": {
            "BG": (10, 10, 10), "BG_CARD": (26, 26, 26),
            "FG": (255, 255, 255), "MUTED": (150, 150, 150),
            "ACCENT": (255, 255, 255), "ACCENT_DIM": (110, 110, 110),
            "CYAN": (255, 255, 255), "LINE": (72, 72, 72),
        },
    },
}

# Gia tri mac dinh; build() ghi de theo --brand
BG = BG_CARD = FG = MUTED = ACCENT = ACCENT_DIM = CYAN = LINE = None
THRESHOLD_BACKGROUND_BRIGHT = None    # diem sang nen (0..255) FG/BG hoa nhau — dat qua set_brand


def set_brand(ten: str):
    """Nap bang mau cua mot thuong hieu."""
    global BG, BG_CARD, FG, MUTED, ACCENT, ACCENT_DIM, CYAN, LINE, THRESHOLD_BACKGROUND_BRIGHT
    b = BRAND.get(ten)
    if b is None:
        raise SystemExit(f"Khong biet thuong hieu {ten!r}. "
                         f"Co: {', '.join(sorted(BRAND))}")
    m: dict = b["palette"]          # LOW-308: dict long trong BRAND, khai de mypy doc duoc
    BG, BG_CARD = m["BG"], m["BG_CARD"]
    FG, MUTED = m["FG"], m["MUTED"]
    ACCENT, ACCENT_DIM = m["ACCENT"], m["ACCENT_DIM"]
    CYAN, LINE = m["CYAN"], m["LINE"]
    # Diem hoa nhau cua WCAG contrast ratio giua chu FG va chu BG tren nen xam —
    # tinh theo dung cap mau CUA THUONG HIEU NAY (text_bg.threshold_wall_part), vi
    # mot con so co dinh (116, tinh rieng cho FG/BG cua donniechublog) se sai
    # nguong voi dcgr (FG/BG gan nhu trang tuyet doi / den tuyet doi).
    THRESHOLD_BACKGROUND_BRIGHT = text_bg.threshold_wall_part(FG, BG)
    return b

TITLE_SIZE_HI, TITLE_SIZE_LO = 56, 38
TITLE_GROW_MAX = 104              # trần khi tiêu đề nở vào chỗ trống
TITLE_GROW_LINES = 2   # the tin: tuyet doi khong de tieu de 3 dong
# Hero image di huong nguoc lai. O the tin, tieu de la nhan de va phu de moi mang
# noi dung, nen tieu de dai la hong nhip. O hero image KHONG CO phu de: tieu de
# la toan bo noi dung, mot cau tron ven bao quat ca tin. No duoc phep chay bao
# nhieu dong tuy y mien con cho. Tran 6 dong chi de chan truong hop dan ca doan
# van vao, khong phai de giu nhip.
CEILING_TITLE_LINES = 6
# Oswald hep ngang hon JetBrains Mono nhieu nen tran no cua tieu de phai cao hon,
# khong thi cau ngan bi chan o co chu nho hon muc dang le duoc.
CEILING_TITLE_MAX = 150
KICKER_SIZE = 30
KICKER_TRACK = 7        # gian chu cai cua kicker; chu nho ma gian rong moi ra nhan
# Khoang ho giua kicker va tieu de. Do RIENG thay vi dung g1 cua khoi nhan dien,
# vi kicker phai nam SAT tieu de moi doc ra la mot cum; xa qua thi no troi thanh
# mot dong chu le loi giua khoang trong.
KICKER_GAP = 14
# Ca cum kicker (ke trai + chu + ke phai) chiem dung nua be ngang the.
KICKER_PHRASE = 0.50
KICKER_FAMILY = 20          # ho giua chu va hai duong ke
# Gian dong: chu display co to thi khoang ho mac dinh nhin ra roi rac. Bo sat
# lai cho khoi chu doc thanh MOT mang, dung nhu cac mau tham khao.
LEAD, TRAN_LEAD = 6, 2
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
QUOTE_BLUR = 30                         # ban kinh mo vung chu de len (Gaussian) — LOW-165: tang gap
                                # doi tu 28, van khong xoa het mot mang lech tong hang tram px
                                # (xem docstring _open_region_text) nhung giam manh do "sot" —
                                # truong hop nang giai bang cach mo rong dinh nghia CLUTTERED
                                # (prepare/vision.py) de di duong nen dac thay vi blur.
QUOTE_BLUR_COUNT = 80                     # khoang dem TREN diem chu bat dau, de mo tan dan khong dot ngot

# ---- Kieu tran: khung chu nhat quanh khoi chu ------------------------------
# Ong Chu chot 07/09/2026: bo nen dac, dat chu thang len anh voi mau tuong phan,
# va bao quanh bang mot khung chu nhat NET — "nhu cach Dre lam quote". Khac
# quote o chi mot cho: khong ngoac kep, vi day la tieu de chu khong phai cau
# trich dan. Nen bon net day du thay vi hai goc ngoac doi nhau.
CEILING_FRAME_X = 40                       # le ngoai cua khung
CEILING_TEXT_X = CEILING_FRAME_X + 44         # chu thut vao trong khung
CEILING_FRAME_PAD = 34                     # ho doc giua net khung va khoi chu
CEILING_FRAME_R = 26                       # bo goc
CEILING_FRAME_LW = 4                       # do day net


@functools.lru_cache(maxsize=256)
def _f(path, size, weight=None):
    """Nap font, dat do day neu font co truc bien thien.

    CACHE (audit A5): `_fit_text`/`_fit_block` do chu bang cach thu tung co
    `range(hi, lo-1, -2)` — moi buoc mot `ImageFont.truetype` doc lai tep TTF tu
    dia, va moi the goi chung vai chuc lan. Ham thuan theo (path, size, weight)
    nen cache duoc; da kiem khong cho nao doi font sau khi nhan (`set_variation_by_axes`
    chi chay TRONG day, truoc khi tra ve).

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
BRAND_FROM = {
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
BRAND_PHRASE = (
    ("HUGGING", "FACE"), ("BOSTON", "DYNAMICS"), ("STABILITY", "AI"),
    ("SCALE", "AI"), ("MISTRAL", "AI"), ("BLACK", "FOREST", "LABS"),
    ("STABLE", "DIFFUSION"), ("META", "AI"), ("AMAZON", "WEB", "SERVICES"),
)
_RIA = " .,:;!?\u201c\u201d\"'()[]"


# Mau nhan dien cua tung hang. Bang mau dcgr chi co trang va den, nen ten hang
# to len khong khac gi chu thuong. Day la MAU THU BA cua no: khong phai mot mau
# co dinh them vao bang, ma la mau cua chinh chu the dang duoc nhac toi. Nhac
# Spotify thi ra xanh la Spotify, nhac Nvidia thi ra xanh la Nvidia.
COLOR_RANK = {
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
COLOR_PHRASE = {
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


# ---- To TEN MODEL day du (LOW-343, Ong Chu 21/09/2026: *"ko thay doi mau keyword quan trong?"*) ----
# Bo to cu chi to TEN HANG dung mot tu trong BRAND_FROM: the "Gemini Omni Flash #2" chi to
# "GEMINI", the "Fable 5 ha gia 25%" khong to gi, the Qwen chi to "ALIBABA". Gio to NGUYEN CUM
# ten model kem phien ban bang mau cua ho model. Ho model -> mau (mau hang chu quan khi model
# khong co mau rieng). Khong dung ranking.extract_model: no bo sot "Fable 5" (thieu chu Claude),
# "Grok Voice Transcribe 2.0" (chi ra "Grok").
MODEL_FAMILY_COLOR = {
    "QWEN": COLOR_RANK["QWEN"], "WAN": COLOR_RANK["QWEN"],
    "GEMINI": COLOR_RANK["GEMINI"], "GEMMA": COLOR_RANK["GEMINI"], "VEO": COLOR_RANK["GEMINI"],
    "CLAUDE": COLOR_RANK["CLAUDE"], "FABLE": COLOR_RANK["CLAUDE"], "OPUS": COLOR_RANK["CLAUDE"],
    "SONNET": COLOR_RANK["CLAUDE"], "HAIKU": COLOR_RANK["CLAUDE"],
    "GPT": COLOR_RANK["CHATGPT"], "CHATGPT": COLOR_RANK["CHATGPT"], "SORA": COLOR_RANK["CHATGPT"],
    "GROK": COLOR_RANK["GROK"], "LLAMA": COLOR_RANK["LLAMA"], "MUSE": COLOR_RANK["META"],
    "DEEPSEEK": COLOR_RANK["DEEPSEEK"], "MISTRAL": COLOR_RANK["MISTRAL"],
    "MAGISTRAL": COLOR_RANK["MISTRAL"], "DEVSTRAL": COLOR_RANK["MISTRAL"],
    "CODESTRAL": COLOR_RANK["MISTRAL"], "KIMI": COLOR_RANK["KIMI"],
    "NEMOTRON": COLOR_RANK["NVIDIA"], "PHI": COLOR_RANK["MICROSOFT"],
    "SEEDANCE": COLOR_RANK["BYTEDANCE"], "SEEDREAM": COLOR_RANK["BYTEDANCE"],
    "DOUBAO": COLOR_RANK["BYTEDANCE"], "GLM": None, "MINIMAX": None, "HAILUO": None,
    "HUNYUAN": COLOR_RANK["TENCENT"], "ERNIE": COLOR_RANK["BAIDU"],
}
_MODEL_TAIL = re.compile(r"^[A-Z0-9][A-Za-z0-9.\-+]*$")


def _model_family(tu: str):
    """Ho model ma tu `tu` (da bo dau cau, viet hoa) bat dau bang, hoac None. Sau ten ho phai
    het tu hoac la ky tu KHONG phai chu cai: "QWEN-IMAGE-2.1", "QWEN3", "GPT-6" khop;
    "WANT", "PHILIPPINES" khong khop."""
    for ho in MODEL_FAMILY_COLOR:
        if tu.startswith(ho) and (len(tu) == len(ho) or not tu[len(ho)].isalpha()):
            return ho
    return None


def model_marks(title: str) -> list:
    """Mau to cho TUNG TU cua `title.split()` — mau ho model voi cac tu thuoc cum ten model,
    None voi tu khac (va voi ho chua co mau rieng: `False` = la ten model, dung mau du phong).
    Cum = tu thuoc mot ho model + cac tu NOI TIEP viet hoa/co so (ten, phien ban, bien the);
    dung o chu thuong tieng Viet, "#2", "25%", dau cau."""
    tus = (title or "").split()
    ra = [None] * len(tus)
    i = 0
    while i < len(tus):
        sach = tus[i].strip(_RIA)
        ho = _model_family(sach.upper()) if sach else None
        if not ho:
            i += 1
            continue
        mau = MODEL_FAMILY_COLOR[ho] or False
        ra[i] = mau
        j = i + 1
        het = tus[i] != tus[i].rstrip(_RIA)                  # "Flash," — dau cau dong cum
        while not het and j < len(tus):
            s = tus[j].rstrip(_RIA)
            if not s or not _MODEL_TAIL.match(s):
                break
            ra[j] = mau
            het = tus[j] != s
            j += 1
        i = j
    return ra


def _measure_bright(mau) -> float:
    r, g, b = (c / 255 for c in mau[:3])
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _enough_bright(mau, toi_thieu=0.42):
    """Keo mau ve phia trang cho toi khi doc duoc tren nen toi.

    Mau nhan dien cua nhieu hang la mau dam — xanh navy Samsung, xanh TSMC — va
    dat nguyen xi len nen den thi khong doc noi. Keo sang KHONG lam mat nhan
    dien: van ra dung sac do, chi la sang hon.
    """
    mau = tuple(mau[:3])
    for _ in range(24):
        if _measure_bright(mau) >= toi_thieu:
            break
        mau = tuple(min(255, round(c + (255 - c) * 0.12)) for c in mau)
    return mau


def _enough_dark(mau, toi_da=0.42):
    """Keo mau ve phia den cho toi khi doc duoc tren nen SANG — anh cua _enough_bright.

    Can thiet vi nguyen bo nhan dien duoc dinh nghia cho NEN TOI: CYAN cua dcgr
    la trang thuan, dat len anh nen trang thi CR 1.04, bien mat hoan toan.
    """
    mau = tuple(mau[:3])
    for _ in range(24):
        if _measure_bright(mau) <= toi_da:
            break
        mau = tuple(max(0, round(c * 0.88)) for c in mau)
    return mau


def _color_of_rank(tu_sach: tuple):
    """Mau cua mot ten hang (da tach dau, viet hoa). None neu chua biet."""
    if len(tu_sach) > 1 and tuple(tu_sach) in COLOR_PHRASE:
        return COLOR_PHRASE[tuple(tu_sach)]
    if len(tu_sach) == 1 and tu_sach[0] in COLOR_RANK:
        return COLOR_RANK[tu_sach[0]]
    for cum, mau in COLOR_PHRASE.items():
        if tu_sach and tu_sach[0] in cum:
            return mau
    return None


def _extract_label(dong: str):
    """Tach mot dong thanh [(tu, khoa_hang)]. Giu nguyen tu goc de ve.

    `khoa_hang` la tuple cac tu da lam sach cua ten hang khop duoc, hoac None.
    Tra ve tuple chu khong phai True/False de ben ve con tra duoc MAU cua hang
    do — ca cum "HUGGING FACE" phai ra cung mot mau, ke ca khi hai tu bi tach
    ra hai lan ve.

    So khop KHONG PHAN BIET HOA/THUONG: tieu de the tin (noi ham nay ra doi)
    luon viet hoa toan bo nen truoc day so thang khong sao — nhung van xuoi
    thuong (vd chu than carousel.py) viet ten hang kieu "Nvidia" binh thuong,
    so thang voi BRAND_FROM ("NVIDIA") thi trat, lai vo tinh trung mot tu VIET
    TAT tinh co da hoa san (vd "AMD") thay vi dung hang dang noi toi. Chi
    UPPER() luc SO KHOP; `khoa` van tra ve dang chuan hoa (hoa) vi COLOR_RANK/
    BRAND_FROM luu key hoa — khong lien quan gi toi `tu` goc dung de ve.
    """
    tu = dong.split(" ")
    cleaned = [t.strip(_RIA).upper() for t in tu]
    khoa = [None] * len(tu)
    i = 0
    while i < len(tu):
        for cum in BRAND_PHRASE:
            n = len(cum)
            if tuple(cleaned[i:i + n]) == cum:
                for k in range(i, i + n):
                    khoa[k] = cum
                i += n
                break
        else:
            if cleaned[i] in BRAND_FROM:
                khoa[i] = (cleaned[i],)
            i += 1
    return list(zip(tu, khoa))


def _color_rank_within(text: str):
    """Mau cua ten hang DAU TIEN nhan ra trong `text`, hoac None. Dung de to
    dau ngoac quote theo mau hang duoc nhac toi trong chu de."""
    for _tu, khoa in _extract_label(text or ""):
        if khoa:
            mau = _color_of_rank(khoa)
            if mau:
                return mau
    return None


def _empty_line(d, dong, font):
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


def _about_line(d, x, y, dong, font, mau, che_do=None, mau_du_phong=None,
             nen_sang=False, marks=None):
    """Ve mot dong, to rieng ten thuong hieu.

    che_do:
      None    — khong to gi, ca dong mot mau (the tin kieu dai)
      "cyan"  — ten hang lay CYAN cua bo nhan dien (donniechublog)
      "company" — ten hang lay MAU RIENG CUA HANG do (dcgr). Hang chua biet mau
                thi dung `mau_du_phong` (BRAND `fallback_company_color`).

    `nen_sang`: dong nay nam tren mot dai anh SANG. Khi do mau ten hang phai
    keo ve phia TOI (`_enough_dark`), khong phai sang them — dung cai loi da sua cho
    net khung quote 06/09/2026 (CYAN cua dcgr tren nen trang cho CR 1.04, tuc
    mat chu). Chi kieu `full_bleed` truyen co nay: no dat chu thang len anh khong man
    toi nen dai chu co the sang; kieu the tin luon co nen toi.
    """
    khoang = d.textlength(" ", font=font)
    marks = list(marks or [])
    for k, (tu, khoa) in enumerate(_extract_label(dong)):
        f_mau = mau
        mk = marks[k] if k < len(marks) else None
        if mk is not None and che_do:                         # LOW-343: nguyen cum ten model
            goc = CYAN if che_do == "cyan" else (mk or mau_du_phong or CYAN)
            f_mau = _enough_dark(goc) if nen_sang else _enough_bright(goc)
        elif khoa and che_do == "cyan":
            f_mau = _enough_dark(CYAN) if nen_sang else CYAN
        elif khoa and che_do == "company":
            goc = _color_of_rank(khoa) or mau_du_phong or CYAN
            f_mau = _enough_dark(goc) if nen_sang else _enough_bright(goc)
        d.text((x, y), tu, font=font, fill=f_mau)
        x += d.textlength(tu, font=font) + khoang


def _empty_tracked(d, text, font, track):
    return (sum(d.textlength(c, font=font) for c in text)
            + track * max(0, len(text) - 1))


def _about_tracked(d, x, y, text, font, fill, track):
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
                path=None, weight=None, hi=None):
    """Chọn cỡ chữ lớn nhất mà tiêu đề vẫn vừa cả bề ngang lẫn chiều cao trống.

    Chỉ dùng khi tỉ lệ thẻ bị khoá — lúc đó textbox có chiều cao cố định nên
    biết chính xác còn bao nhiêu chỗ cho tiêu đề.

    Đo chiều cao bằng CHÍNH các dòng sẽ vẽ (`_step_line`), không phải một
    chuỗi mẫu cố định: chuỗi mẫu không có các tổ hợp dấu đôi (mũ/móc + dấu
    thanh, vd "ẫ" "ệ" "ữ") nên đánh giá thấp một dòng tiếng Việt thật, khiến
    hai dòng liền nhau chồng lên nhau khi giãn dòng bó sát.
    """
    best = None
    path = path or F_BOLD
    for size in range(hi or TITLE_GROW_MAX, TITLE_SIZE_LO - 1, -2):
        f = _f(path, size, weight)
        lines = _wrap(d, text, f, max_w)
        if len(lines) > max_lines:
            continue
        cao = _step_line(f, lines, lead)[0] * len(lines)
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


def _step_line(font, lines, lead):
    """Buoc nhay giua hai dong va do nho cua dong dau, do bang CHINH cac dong se ve.

    Mot chuoi mau co dinh (vd "Ây") khong bao gom cac to hop dau DOI (mu/moc +
    dau thanh, vd "ấ" "ẫ" "ữ") nen danh gia THAP dong tieng Viet that: dau sac
    tren "Ắ" cao hon dau mu, dau nang duoi "Ạ" thap hon duoi chu y. Do that:
    chuoi mau cao 121px trong khi mot dong that trai tu 0 den 134. Voi gian
    dong bo sat cua hero image, chenh lech do du de hai dong lien nhau chong
    len nhau 11px — nen luon do tren CHINH cac dong se ve, khong doan qua mot
    chuoi tham chieu.

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


def stack_read(paths, gap=0, nen=(0, 0, 0)):
    """GHEP DOC nhieu anh NGANG thanh mot anh (Ong Chu chot 03/09/2026): mot anh
    qua chu nhat ngang (slide, banner, bang) dua vao khung 4:5 se hoac bi crop
    mat tieu de, hoac de trong nua khung. Thay vi crop, tim THEM mot anh ngang
    nua va xep hai anh doc trong cung khung: moi anh full be ngang, nguyen ti
    le. Tra ve PIL.Image RGB; mot path thi tra ve anh do nguyen ven.

    `gap=0` (Ong Chu chot 04/09/2026): truoc day chen 12px nen den giua hai anh.
    Vach den do la mot DUONG KE ngang giua khung — dung cai mat bat ngay va doc
    ra HAI VUNG rieng biet, dung thu ma luat carousel/hero cam. Hai anh ap sat
    nhau, cong `tone_mismatch` lo phan tone, moi ra mot mat phang lien. Chi truyen
    `gap` khac 0 khi co ly do rat cu the."""
    ims = [Image.open(q).convert("RGB") for q in paths]
    if len(ims) == 1:
        return ims[0]
    # Cong lech tone (`kiem_lech_tone`) da bo (Ong Chu 13/09/2026: bo
    # cam doan ve nguon/chat luong nay khoi he thong, moi vai).
    w = max(im.width for im in ims)
    ims = [im.resize((w, round(im.height * w / im.width)), Image.Resampling.LANCZOS) for im in ims]
    h = sum(im.height for im in ims) + gap * (len(ims) - 1)
    out = Image.new("RGB", (w, h), nen)
    y = 0
    for im in ims:
        out.paste(im, (0, y))
        y += im.height + gap
    return out


def _block_standard_image(src, nhan_vat=""):
    """Bo cong CHUAN ANH dung chung — Ethan chiu dung tieu chuan nhu Dre.

    Ong Chu chot 04/09/2026: "anh do ai lam ma cha phai dat tieu chuan". Truoc
    do bang trong docstring cua `image_rules_ethan` ghi thang ra chenh lech: mat nguoi,
    anh trung, do phan giai — carousel.py CO, card.py KHONG. Cac cong do khong
    co gi rieng cua carousel ca, chung chi tinh co duoc viet o do vi do la cho
    Ong Chu bat loi truoc. (13/09/2026: bo `kiem_xuat_xu`/`kiem_day_sang` khoi
    danh sach — hai cong nay da bo khoi he thong, moi vai.)

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
            for l, c in (image_rules_ethan.check_blank_image(nhan, rgb),
                         image_rules_ethan.check_resolution(nhan, w, h),
                         image_rules_ethan.check_unnamed_face(nhan, q, nhan_vat),
                         image_rules_ethan.check_duplicate(nhan, q, da_thay)):
                loi += l
                canh_bao += c
    for c in canh_bao:
        print(f"[CANH BAO] {c}", file=sys.stderr)
    if loi:
        raise SystemExit("ANH KHONG DAT CHUAN —\n  " + "\n  ".join(loi))


def _block_chart(src):
    """Chart di MOT MINH vao kieu `quote`/`full_bleed` thi DUNG.

    Tieu chi o `image_rules_ethan.check_chart_standalone` — cau hoi "anh nay co dung duoc
    khong", dung chung cho moi khung dat CHU DE LEN anh phu kin. O day chi con
    phan rieng cua card.py: kieu nao la khung do (quote/full_bleed, xem `build`), va
    bao loi bang cach dung han."""
    da_ghep = isinstance(src, (list, tuple)) and len([q for q in src if q]) >= 2
    q = src[0] if isinstance(src, (list, tuple)) else src
    with Image.open(q) as im:
        loi, _ = image_rules_ethan.check_chart_standalone(str(q), im.convert("RGB"), da_ghep)
    if loi:
        raise SystemExit("CHART DI MOT MINH VAO HERO — " + "\n  ".join(loi) +
                         "\n  (Chac chan muon chart mot minh thi --bo-qua-anh)")


def _block_crop(src):
    """DUNG neu anh dua vao la mot anh NGANG da bi cat bot BE NGANG.

    Tieu chi o `image_rules_ethan.check_crop_landscape` — cung mot cong ma carousel dung.
    O day chi con phan rieng cua card.py: doc nhieu duong dan (--image/--image2)
    va bao loi bang cach dung han."""
    for q in (src if isinstance(src, (list, tuple)) else [src]):
        if not q:
            continue
        with Image.open(q) as im:
            w, h = im.size
            loi, _ = image_rules_ethan.check_crop_landscape(str(q), im, w, h)
        if loi:
            raise SystemExit(
                "ANH BI CAT BE NGANG — " + "\n  ".join(loi) +
                "\n  Full chieu rong di truoc, chieu cao xet sau: dua thang ANH "
                "GOC vao --image,\n  anh qua ngang thi ghep doc bang --image2.")


def _open_image(src):
    """src: mot duong dan, hoac danh sach duong dan (ghep doc)."""
    if isinstance(src, (list, tuple)):
        return stack_read(src)
    return Image.open(src).convert("RGB")


def _fit_cover(img, box_w, box_h):
    src_r, box_r = img.width / img.height, box_w / box_h
    if src_r > box_r:
        nh = box_h
        nw = round(img.width * nh / img.height)
    else:
        nw = box_w
        nh = round(img.height * nw / img.width)
    img = img.resize((nw, nh), Image.Resampling.LANCZOS)
    left, top = (nw - box_w) // 2, (nh - box_h) // 2
    return img.crop((left, top, left + box_w, top + box_h))


def _range(nen: float) -> tuple:
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


def _layer_image(canvas, src_img, H) -> int:
    """Lop ANH cua the — dung chung cho CA HAI kieu (`quote` va `full_bleed`).

    ANH LUON HIEN FULL BE NGANG, KHONG CAT HAI CANH (Ong Chu bat loi 03/09/2026:
    cover-crop lam mat tieu de cua slide/bang nguon, anh doc ra vo nghia). Nen:
    ban cover LAM MO phu kin khung — KHONG lam toi (Ong Chu 06/09/2026: "lam mo
    chu dung boi them mau", ap dung ca cho lop nen nay). Lop sac: anh nguyen ti
    le, full W, dat sat tren. Anh cao hon khung thi chi cat theo chieu doc.

    Tu 07/09/2026 kieu `full_bleed` cung di duong nay. Truoc do no co duong rieng
    (`_tran_anh`): anh thap hon the thi phan duoi la mot mang MAU NEN DAC cua bo
    nhan dien — dung cai "vung thu hai" ma IMAGE_RULES muc 7 cam, va chinh spec cua
    kieu full_bleed cung da ghi la phai dung nen mo. Hai duong ve cho cung mot viec la
    cach mot ban sua duoc mot nua.

    Tra ve `nat_h` — chieu cao tu nhien cua anh o be ngang W.
    """
    canvas.paste(_fit_cover(src_img, W, H).filter(ImageFilter.GaussianBlur(40)), (0, 0))
    nat_h = round(src_img.height * W / src_img.width)
    sac = src_img.resize((W, nat_h), Image.Resampling.LANCZOS)
    if nat_h > H:
        top = (nat_h - H) // 2
        canvas.paste(sac.crop((0, top, W, top + H)), (0, 0))
        return nat_h

    # ANH THAP HON KHUNG (moi anh ngang: 3:2 ra nat_h=800, 4:3 ra 900 tren
    # khung 1500) — day la cho sinh ra DUONG RANH ma Ong Chu bat nhieu lan.
    # Dan thang `sac` len nen thi tai dung hang nat_h co mot buoc nhay: tren la
    # anh SAC, duoi la ban cover-blur cua MOT VUNG KHAC cua chinh tam anh. Do
    # that (anh 3:2): y=799 L=240.0 -> y=800 L=80.7, tut 159 do sang trong MOT
    # hang, do net cung roi tu 8.0 xuong 0.6.
    #
    # Truoc dot lam lai 06/09/2026 co `_man_quote` dat man DAC dung tai nat_h de
    # xoa mep (9f129cf viet ro la de sua ca nay); 9b7244d go man do ma khong
    # thay gi, 0c7415b bo not .enhance(0.5) cua lop nen. Con `_open_region_text` thi
    # bat dau tan `frame_top - 110`, thuong NAM DUOI mep, va ngay khi no phu
    # trung thi mat na o do moi dat mot phan nen mep van lo (anh 4:3 quote 3
    # dong: mat na ~28%, delta van +20).
    #
    # Cach xoa mep dung tinh than "lam mo chu dung boi them mau": khong dat lai
    # man toi, ma cho lop SAC TAN dan vao lop nen mo qua mot dai ngan ket thuc
    # dung tai nat_h. Dung smoothstep (dao ham bang 0 o CA HAI dau) nen khong
    # sinh mep moi o dau dai — mot dai chuyen muot thay cho mot duong ke.
    dai = max(1, min(int(nat_h * 0.16), 180))
    mat_na = Image.new("L", (W, nat_h), 255)
    for y in range(dai):
        t = (y + 1) / dai
        muot = t * t * (3 - 2 * t)                  # smoothstep
        mat_na.paste(int(255 * (1 - muot)),
                     (0, nat_h - dai + y, W, nat_h - dai + y + 1))
    canvas.paste(sac, (0, 0), mat_na)
    return nat_h


# LOW-330 (Ong Chu 20/09/2026): anh roi cung CHI duoc mot lop phu, khong bao gio la
# mang mau dac. 205/255 = 80% — bang OVERLAY_CLUTTERED cua carousel, va duoi tran
# carousel.TEXT_BG_MAX_OPACITY (88%) de the va slide than cung mot luat.
TEXT_OVERLAY_CLUTTERED = 205


def _text_bg_overlay(canvas, frame_top):
    """Nen chu cho ANH ROI buoc phai dung. `_open_region_text` chi lam mo — tren anh co
    chu in san, chu cu van lo mo mo sau chu moi, doc ra lem nhem (LOW-47). O day: van mo
    cuc bo nhu anh sach, sau do phu them mot lop tinh mau nen theo gradient, tran
    TEXT_OVERLAY_CLUTTERED — dam hon anh sach nhung anh van hien qua.

    LOW-330 (Ong Chu 20/09/2026: *"dung de cho nen dac, trong rat thieu chuyen nghiep"*):
    ban truoc (`_text_bg_strict`, LOW-47) phu NEN DAC mau BG tu khoang lang gan nhat xuong
    day the — chinh cai ma LOW-286 da bac o slide than carousel. Nay the di cung mot duong
    voi carousel: chi overlay, khong bao gio la mang mau dac."""
    _open_region_text(canvas, frame_top)
    W_, H_ = canvas.size
    top = max(0, int(frame_top - QUOTE_BLUR_COUNT))
    doan = max(1, int(frame_top) - top)
    mat_na = Image.new("L", (W_, H_), 0)
    for y in range(top, H_):
        t = min(1.0, (y - top + 1) / doan)
        mat_na.paste(int(TEXT_OVERLAY_CLUTTERED * t * t * (3 - 2 * t)), (0, y, W_, y + 1))
    canvas.paste(Image.new(canvas.mode, (W_, H_), tuple(BG) + ((255,) if canvas.mode == "RGBA" else ())),
                 (0, 0), mat_na)


def _open_region_text(canvas, frame_top):
    """Lam MO CUC BO vung anh nam duoi chu, sua canvas tai cho (Ong Chu 06/09/2026:
    chu co vien "phen nhu karaoke" — bo vien, thay bang lam mo).

    Tu `frame_top - dem` toi day the; rieng doan `dem` la fade dan de mep sac/mo
    khong doc ra hai vung — dung cai loi da bat nhieu lan voi man toi. Mo xoa het
    chi tiet nen do sang trong khoi deu lai, nho vay MOT mau chu duy nhat (chon
    SAU khi mo) doc duoc tren ca khoi, khong can vien.

    Chi deu duoc chi tiet co ~QUOTE_BLUR px: chenh sang trai vai tram px (mang
    ao trang cat doc khoi chu) thi mo bao nhieu cung khong san phang, do la
    viec cua `_can_board_line`."""
    W_, H_ = canvas.size
    top = max(0, int(frame_top - QUOTE_BLUR_COUNT))
    vung = canvas.crop((0, top, W_, H_))
    mo = vung.filter(ImageFilter.GaussianBlur(QUOTE_BLUR))
    # Mat na: full mo tu frame_top tro xuong, rieng doan `dem` phia tren la fade.
    mat_na = Image.new("L", vung.size, 255)
    doan_tan = max(1, int(frame_top - top))
    for y in range(doan_tan):
        mat_na.paste(int(255 * (y / doan_tan) ** 0.82), (0, y, vung.width, y + 1))
    canvas.paste(Image.composite(mo, vung, mat_na), (0, top))


# Nguong quyet dinh chu SANG hay chu TOI tren mot vung nen: diem sang xam noi
# CR(chu trang) = CR(chu toi) — dat qua set_brand (text_bg.threshold_wall_part)
# theo dung cap mau CUA THUONG HIEU DANG NAP, khong con la mot con so co dinh
# (116, tinh rieng cho FG/BG cua donniechublog) dung nham sang ca dcgr. Truoc
# 06/09/2026 con so nay la 140, go tay: sai phe tren ca dai nen 116..140 (dai
# hay gap nhat o anh chup nua sang nua toi).


def _within_card(canvas, box):
    """Ep mot khung do sang nam gon trong the, va luon co dien tich.

    `_bright_region` goi `canvas.crop` roi `ImageStat` — crop ra ngoai bien tra ve
    vung DEN (PIL dem den vao), tuc mot dai chu sat day the se do ra "nen toi"
    va chon chu trang, du day the that su sang."""
    x0, y0, x1, y1 = (int(v) for v in box)
    W_, H_ = canvas.size
    x0, x1 = max(0, min(x0, W_ - 1)), max(1, min(x1, W_))
    y0, y1 = max(0, min(y0, H_ - 1)), max(1, min(y1, H_))
    if x1 <= x0:
        x1 = x0 + 1
    if y1 <= y0:
        y1 = y0 + 1
    return (x0, y0, x1, y1)


def _bright_region(canvas, box) -> float:
    """Do sang trung binh cua mot vung canvas (0..255)."""
    return ImageStat.Stat(canvas.crop(tuple(int(v) for v in box)).convert("L")).mean[0]


# Mot dai chu rong (gan het be ngang the) rat de vua co mang toi vua co mang
# sang cuc bo (vd hero portrait: co ao trang canh vung toi) — TRUNG BINH ca
# dai van thien dung mot phe, nhung diem sang/toi cuc bo do van lo ra thanh
# mot "vet sang" duoi chu, du _open_region_text da mo. Do o day THEO ANH THAT (anh
# Trump 08/09/2026: dai "HON 40 PHAN TRAM" mean=54.6 — chon dung chu trang —
# nhung std=49.7: mot mang co ao trang lam ho mot khoang du sang de chu trang
# mat tuong phan tai dung cho do).
THRESHOLD_FALL_LINE = 42     # do lech (stddev xam) trong MOT dai vuot muc nay moi can tinh them
TRANSLATE_FALL_LINE = 24       # tinh vua du de KEO do lech ve muc nay (an toan de mot mau doc duoc)
DARK_MAX_LINE = 195    # tran alpha lop tinh (0..255) cho truong hop cuc doan


def _can_board_line(canvas, box):
    """Do sang MOT dai (box); neu do lech (stddev) qua cao — co diem sang/toi
    cuc bo giua dai — tinh THEM mot lop mong CHI TRONG box nay (khong lan ra
    ca the) keo ve phia phe da chiem da so, roi tra ve do sang MOI (sau khi
    tinh) de chon mau chu cho dung. Do lech thap (dai deu mau) thi khong lam
    gi, giu nguyen tinh than 'khong phu lop nao neu khong can'.

    Tinh mot mau PHANG vao vung giam do lech THEO TI LE (1-alpha) — muon do
    lech con lai <= TRANSLATE_FALL_LINE thi alpha >= 1 - TRANSLATE_FALL_LINE/std do duoc."""
    box = _within_card(canvas, box)
    x0, y0, x1, y1 = box
    st = ImageStat.Stat(canvas.crop(box).convert("L"))
    if st.stddev[0] <= THRESHOLD_FALL_LINE:
        return st.mean[0]
    mau_ve = BG if st.mean[0] < THRESHOLD_BACKGROUND_BRIGHT else FG
    do = min(DARK_MAX_LINE,
             round(255 * max(0.0, 1 - TRANSLATE_FALL_LINE / st.stddev[0])))
    lop = Image.new("RGBA", (x1 - x0, y1 - y0), (*mau_ve[:3], int(do)))
    canvas.alpha_composite(lop, (x0, y0))
    return _bright_region(canvas, box)


def _color_change_background_hide_whole(canvas, box):
    """Mau chu TUONG PHAN voi vung anh ben duoi `box` (x0,y0,x1,y1), DO SAU KHI
    da lam mo (`_open_region_text`). Vung toi -> chu sang (FG); vung sang -> chu toi
    (BG, mau nen thuong hieu, khong phai den tuyet doi).

    Do sang lay qua `_can_board_line` chu khong phai mean thuan: mean bao "nen
    toi" van sai khi trong box co mot mang sang cuc bo — chu ra trang roi chim
    dung tai mang do. `_can_board_line` bat ca ay bang stddev va tinh them mot
    lop mong CHI TRONG box truoc khi chon mau."""
    return FG if _can_board_line(canvas, box) < THRESHOLD_BACKGROUND_BRIGHT else BG


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


def _quote_geometry(d, quote, attrib, handle, H):
    """Hinh hoc cua the `quote` o khung cao H: co chu, cac dong, vi tri khung/chip/dong
    nguon. MOT noi tinh cho CA hai nguoi dung: `_render_quote` (ve) va `quote_text_top`
    (ethan_submit kiem chu the co nam tren khung chu khong, LOW-273) — hai ban tinh
    rieng la lech nhau ngay khi mot ben doi le."""
    from types import SimpleNamespace
    # Khung o le FRAME_X; chu THUT VAO them (TEXT_X > FRAME_X) de hai canh chieu
    # rong cua khung thoang khoi chu.
    FRAME_X = 42
    TEXT_X = FRAME_X + 54
    avail_w = W - 2 * TEXT_X

    # Cau trich dan — giu nguyen HOA/thuong (khong .upper() nhu tieu de).
    # LOW-342: khoi quote chi chiem <= 20% chieu cao the — co chu ha dan toi khi vua.
    for size_hi in range(QUOTE_SIZE_HI, QUOTE_SIZE_LO - 1, -2):
        f_q, q_lines = _fit_text(d, quote, avail_w, max_lines=QUOTE_MAX_LINES,
                                 hi=size_hi, lo=size_hi, path=F_QUOTE)
        buoc, tren = _step_line(f_q, q_lines, QUOTE_LEAD)
        if buoc * len(q_lines) <= H * TEXT_MAX_SHARE and not q_lines[-1].endswith("…"):
            break
    quote_h = buoc * len(q_lines)

    f_at = _f(F_QUOTE_REG, 26)
    at_lines = _wrap(d, attrib, f_at, avail_w) if attrib else []
    at_lh = _step_line(f_at, at_lines, 8)[0]
    at_h = at_lh * len(at_lines)

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

    return SimpleNamespace(FRAME_X=FRAME_X, TEXT_X=TEXT_X, CHIP_INSET=CHIP_INSET,
                           f_q=f_q, q_lines=q_lines, buoc=buoc, tren=tren,
                           f_at=f_at, at_lines=at_lines, at_lh=at_lh, at_h=at_h,
                           f_hchip=f_hchip, f_tchip=f_tchip, ten=ten, chip_h=chip_h,
                           src_top=src_top, yb=yb, frame_bottom=frame_bottom,
                           first_line_top=first_line_top, frame_top=frame_top)


def quote_text_top(quote, attrib, handle, ratio="4:5", brand="donniechublog") -> tuple:
    """(y dau tien ma the `quote` ve chu/khung/chip DE LEN anh, chieu cao the) — de
    kiem chu the cua anh co nam TREN vung chu khong (LOW-273). Tinh bang CHINH
    `_quote_geometry` ma `_render_quote` dung de ve."""
    b = set_brand(brand)
    handle = handle or b["handle"]
    H = RATIOS.get(ratio) or RATIOS["4:5"]
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    g = _quote_geometry(d, drop_mark_forbid(quote), drop_mark_forbid(attrib or ""), handle, H)
    return min(g.frame_top, g.frame_top - g.chip_h // 2), H


def _render_quote(src, quote, attrib, out, handle, ratio, tagline="", cluttered=False):
    """The pull-quote: mot cau trich dan lon tren anh phu kin, KHONG LOP NEN.

    Khac hero image (mot tieu de bao quat tin) va carousel (nhieu slide): day la
    MOT cau noi dat trong ngoac kep, co dong nguon o duoi — dung dang the trich
    dan cua bao.

    Ong Chu chot 06/09/2026, sau nhieu lan bat loi cung mot goc (nen phu chu
    cao hon chinh cau chu, doc ra hai vung rieng biet): BO HAN man toi. Quote
    dat THANG len anh goc; vung anh duoi chu duoc lam mo cuc bo (`_open_region_text`)
    roi mau chu chon theo do sang do duoc (`_color_change_background_hide_whole`).
    """
    H = RATIOS.get(ratio) or RATIOS["4:5"]     # quote luon khoa khung; free -> 4:5
    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    src_img = _open_image(src)
    # ANH LUON HIEN FULL BE NGANG, KHONG CAT HAI CANH (Ong Chu bat loi 03/09/2026:
    # cover-crop lam mat tieu de cua slide/bang nguon, anh doc ra vo nghia).
    # Nen: ban cover LAM MO phu kin khung (KHONG lam toi — Ong Chu 06/09/2026:
    # "lam mo chu dung boi them mau", ap dung ca cho lop nen nay chu khong chi
    # vung chu; truoc day co giam sang .enhance(0.5), gio bo, giu nguyen do sang
    # goc, chi mo). Lop sac: anh nguyen ti le, full W, dat sat tren (chu quote
    # nam duoi). Anh cao hon khung thi chi cat theo chieu doc, giu tron be
    # ngang. Dong nhip voi carousel._body_image.
    _layer_image(canvas, src_img, H)

    d = ImageDraw.Draw(canvas)
    g = _quote_geometry(d, quote, attrib, handle, H)
    FRAME_X, TEXT_X, CHIP_INSET = g.FRAME_X, g.TEXT_X, g.CHIP_INSET
    f_q, q_lines, buoc, tren = g.f_q, g.q_lines, g.buoc, g.tren
    f_at, at_lines, at_lh, at_h = g.f_at, g.at_lines, g.at_lh, g.at_h
    f_hchip, f_tchip, ten, chip_h = g.f_hchip, g.f_tchip, g.ten, g.chip_h
    src_top, yb, frame_bottom = g.src_top, g.yb, g.frame_bottom
    first_line_top, frame_top = g.first_line_top, g.frame_top

    # Tagline ngan cua kenh — chip nho o goc duoi-trai khung (xem ben duoi).
    tag = (tagline or "").strip()

    (_text_bg_overlay if cluttered else _open_region_text)(canvas, frame_top)
    # DO THEO TUNG DAI DONG, khong phai mot trung binh cho ca khoi.
    #
    # Ranh sang/toi NGANG cat qua khoi chu la ca rat thuong: anh chup co hero
    # toi phia tren roi bang trang phia duoi, anh ghep doc hai tam khac tone,
    # anh phong canh troi sang dat toi. Mot phep mean cho ca khoi thi trung
    # binh 136 -> chon chu TRANG, nhung nua duoi khoi la nen 243-250: may dong
    # quote cuoi la trang tren trang. Loi DOI XUNG: trung binh 142 -> chon chu
    # toi, nua tren toi cua khoi thanh den-tren-den (do that CR 1.15).
    #
    # Ly do ghi trong c2e991f ("mo xoa het chi tiet nen do sang trong khoi deu
    # lai, mot mau la du") khong dung: Gaussian ban kinh 28 chi xoa chi tiet co
    # ~28px, khong he san phang chenh sang co vai tram px.
    #
    # Dung `_can_board_line` chu khong `_bright_region` truc tiep: do tung dai moi xu
    # duoc ranh sang/toi NGANG, con mang sang/toi DOC nam gon trong MOT dai (ao
    # trang, cua so, den san khau) thi trung binh ca dai van thien dung phe ma
    # chu van chim tai dung cho do. Do that (nen toi co mang sang doc): dai
    # mean=95 -> chon chu trang, nhung stddev=84 va nen cuc bo tai mang sang la
    # 217 — CR 1.19, mat chu. Nhanh `full_bleed` da di duong nay tu 07/09/2026 (xem
    # dai_dong cua no); day la back-port sang kieu quote.
    dai_dong = [(TEXT_X, first_line_top + i * buoc,
                 W - TEXT_X, first_line_top + (i + 1) * buoc)
                for i in range(len(q_lines))]
    sang_dong = [_can_board_line(canvas, b) for b in dai_dong] or [0.0]
    mau_dong = [FG if sg < THRESHOLD_BACKGROUND_BRIGHT else BG for sg in sang_dong]
    # Phe cua CA KHOI — dung cho net khung va dau ngoac, hai thu trai het khoi.
    nen_sang = sum(1 for sg in sang_dong if sg >= THRESHOLD_BACKGROUND_BRIGHT) * 2 >= len(sang_dong)
    mau_chu = BG if nen_sang else FG
    # DONG NGUON do RIENG. No duoc ve tai `src_top`, tuc NAM DUOI `frame_bottom`
    # — ngoai han cai hop vua do. Anh co khoi chu toi nhung day the sang thi
    # `mau_chu` ra TRANG (dung cho quote), roi dong nguon cung trang dat len day
    # sang: do that la CR 1.08, coi nhu mat chu. Ma dong nguon chinh la cho ghi
    # "Doc bai ... - <nguon>" — mat no la mat dan nguon (06/09/2026).
    mau_nguon = (_color_change_background_hide_whole(canvas, (0, src_top, W, src_top + at_h))
                 if at_lines else mau_chu)

    # Cac dong quote, canh trai (thut vao TEXT_X).
    qy = first_line_top
    for ln, mau_ln in zip(q_lines, mau_dong):
        d.text((TEXT_X, qy - tren), ln, font=f_q, fill=mau_ln)
        qy += buoc

    # MAU: net khung dung CYAN cua bo nhan dien (nhu ten kenh, dong tong voi the
    # cua Bob); DAU " doi theo hang duoc nhac trong chu de (quote hoac dong
    # nguon). Khong nhan ra hang nao thi dau cung CYAN.
    # Ca hai deu phai theo quyet dinh sang/toi cua nen. Truoc 06/09/2026 net
    # khung la CYAN CUNG, khong co nhanh nao doi: tren anh nen sang, CYAN cua
    # dcgr (trang thuan) cho CR 1.04 — bon doan line + hai arc bien mat sach;
    # CYAN cua donniechublog cho 1.88, nhat han. Con dau ngoac thi _enough_bright keo
    # mau hang SANG THEM (nguong 0.42 von danh cho nen toi), tuc sai chieu.
    # Hai dau " co 210px va khung la vat nhan dien cua kieu pull-quote.
    mau_net = _enough_dark(CYAN) if nen_sang else CYAN
    mau_hang = _color_rank_within(quote) or _color_rank_within(attrib)
    if mau_hang:
        mark_col = _enough_dark(mau_hang) if nen_sang else _enough_bright(mau_hang)
    else:
        mark_col = mau_net
    _quote_frame(d, FRAME_X, frame_top, W - FRAME_X, frame_bottom,
                 mau_net, mark_col)

    # Dong nguon (attribution), CANH GIUA, sat day. Vung nay da duoc
    # _open_region_text lam mo tu truoc, va mau lay theo phep do cua CHINH no.
    ay = src_top
    for ln in at_lines:
        lw_ln = d.textlength(ln, font=f_at)
        d.text(((W - lw_ln) / 2, ay), ln, font=f_at, fill=mau_nguon)
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


def _phase(mau, do_sang: float, nen=None):
    """Tron mau ve phia nen de lam mo. do_sang=1.0 giu nguyen, 0 la bang nen."""
    nen = nen if nen is not None else BG
    t = max(0.0, min(1.0, do_sang))
    return tuple(int(n + (c - n) * t) for c, n in zip(mau, nen))


# Cac phep kiem chu tieng Viet da chuyen sang `vietnamese.py` (audit 06/09/2026
# dot 2): chung la cong chan CHU, khong lien quan toi ve anh, va viec chung
# song o day bat manifest_write/ada_submit/cape_submit/itachi_submit/render_edu phai keo ca
# PIL vao chi de hoi "chuoi nay co mat dau khong". Re-export de moi loi goi cu
# (`card.find_face_mark`, `card.drop_mark_forbid`, `card.MARK_FORBID`...) giu nguyen.
from vietnamese import (  # noqa: E402
    NEGATIVE_FACE_MARK, PHRASE_FACE_MARK, MARK_FORBID, drop_mark_forbid, find_face_mark,
)
# pyflakes khong hieu `noqa` (chi flake8/ruff hieu) nen ba ten re-export tren bao
# "imported but unused" o moi lan lint — cham vao de cong pyflakes (CI) sach.
_RE_EXPORT = (NEGATIVE_FACE_MARK, PHRASE_FACE_MARK, MARK_FORBID)

def build(src, title, out, handle=None, ratio="free", tagline="daily AI update",
          brand="donniechublog", bo_qua_dau=False, kieu="quote", kicker="",
          attrib="", bo_qua_anh=False, nhan_vat="", cluttered=False, logo_card=False):
    """Dung the `quote` (mac dinh) hoac `full_bleed`. `src`: mot duong dan, hoac danh
    sach hai duong dan (ghep doc). `title` la cau trich dan (quote) hoac cau
    tieu de (full_bleed). `kieu` nhan ca gia tri cu `tran` (LOW-248, role_spec)."""
    # Nap bang mau TRUOC moi thu khac: cac ham ve doc BG/FG/ACCENT o pham vi
    # module, chua nap thi chung con la None.
    b = set_brand(brand)
    handle = handle or b["handle"]
    title, attrib = drop_mark_forbid(title), drop_mark_forbid(attrib)

    # Chan tieng Viet khong dau TRUOC khi ve, o moi cho chu hien len the.
    loi = {}
    for ten, gt in (("tieu de", title), ("nguon", attrib)):
        m = find_face_mark(gt or "")
        if m:
            loi[ten] = m
    if loi and not bo_qua_dau:
        chi_tiet = "; ".join(f"{k}: {', '.join(v)}" for k, v in loi.items())
        raise SystemExit(
            f"Tieng Viet KHONG DAU tren the — {chi_tiet}\n"
            "  Go lai co dau day du roi chay lai. The la thu nguoi doc nhin thay\n"
            "  dau tien, chu khong dau lam ca kenh trong nhu lam au.\n"
            "  (Neu that su la tieng Anh, chay lai voi --bo-qua-dau)")
    kieu = role_spec.card_style_value(kieu)
    if kieu not in role_spec.CARD_STYLES:
        raise SystemExit(f"--kieu phai la quote hoac full_bleed, nhan {kieu!r}")
    _block_crop(src)          # anh ngang bi cat bot be ngang: dung o moi kieu
    if not bo_qua_anh:
        _block_standard_image(src, nhan_vat)   # chuan anh chung: do net, mat nguoi, trung
        if not logo_card:     # LOW-337: the logo 4:5 (image_brand.card_logo) la hero, khong phai chart
            _block_chart(src)     # chart di mot minh vao hero: ep sang --image2/carousel
    # Moi kieu the mot ham ve rieng; `build` chi con la cong chan + re nhanh.
    if kieu == "quote":
        return _render_quote(src, title, attrib, out, handle, ratio, tagline, cluttered=cluttered)
    return _render_ceiling(src, title, out, handle, ratio, kicker, b, cluttered=cluttered)


def _render_ceiling(src, title, out, handle, ratio, kicker, b, cluttered=False):
    """The hero TRAN: anh phu kin the, tieu de MOT cau tron ven de len anh
    trong mot khung chu nhat net.

    Tach khoi `build` 07/09/2026 cho doi xung voi `_render_quote`: `build`
    chi con la cong chan (tieng Viet co dau, luat anh) cong mot cho re nhanh,
    con moi kieu the mot ham ve. Truoc do `build` la 221 dong trong do 187
    dong chi thuoc ve kieu full_bleed — doc mot kieu phai luot qua ca kieu kia.

    `b`: bang thuong hieu da nap (`set_brand`), can cho co chan, che do
    to ten hang va do ro cua ten kenh.
    """
    src_img = _open_image(src)
    # Chieu cao tu nhien cua anh khi hien full be ngang: con so quyet dinh moi
    # thu con lai — anh la lop nen, khong co tran.
    nat_h = round(W * src_img.height / src_img.width)

    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    co_chan = b.get("footer_size_scale") or 1.0
    mo_chan = b.get("footer_brightness") or 1.0
    f_via = _f(F_REG, max(12, round(VIA_SIZE * co_chan)), weight=500)
    # Chu thut vao trong khung (CEILING_TEXT_X > CEILING_FRAME_X), khong an ra sat le
    # the nhu truoc: co khung roi thi chu cham net la khoi chu doc ra chat.
    avail_w = W - 2 * CEILING_TEXT_X
    lead = TRAN_LEAD
    # Hero image dung Oswald (khong chan, condensed): mot cau dai van vua be
    # ngang o co chu to, dung dang chu cua cac mau tham khao.
    f_title, title_lines = _fit_text(probe, title.upper(), avail_w,
                                      max_lines=CEILING_TITLE_LINES,
                                      hi=TITLE_SIZE_HI, lo=TITLE_SIZE_LO, bold=True,
                                      path=F_HERO, weight=HERO_WEIGHT)

    # Kicker: nhan ngan phia tren tieu de.
    kicker = (kicker or "").strip().upper()
    f_kick = _f(F_REG, KICKER_SIZE, weight=700)
    # Do CHIEU CAO CHU THAT bang bbox cua chinh chuoi kicker, khong doan qua
    # mot chuoi tham chieu co dau tieng Viet (vd "Ây", co ca dau mu lan duoi
    # chu y): kicker toan chu Latin viet hoa, khong dau, nen mot chuoi tham
    # chieu co dau se thua them gan 20px troi o duoi, cong voi khoang ho nua
    # thi kicker troi han khoi tieu de.
    _kb = f_kick.getbbox(kicker) if kicker else (0, 0, 0, 0)
    kick_h = (_kb[3] - _kb[1]) if kicker else 0
    via_h = f_via.getbbox("Ây")[3] - f_via.getbbox("Ây")[1]

    def _cao_tieu_de(f=None, dong=None):
        """Chieu cao khoi tieu de, do bang CHINH cac dong se ve."""
        f, dong = f or f_title, dong if dong is not None else title_lines
        return _step_line(f, dong, lead)[0] * len(dong)

    def _cao_dau(nen=1.0):
        # Phan dau textbox la khoang ho, cong them kicker neu co (kicker cong
        # mot khoang ho nua truoc tieu de). Kieu tran khong ve nhan category.
        return _range(nen)[0] + (kick_h + KICKER_GAP if kicker else 0)

    def _box_min(nen=1.0, f_t=None, d_t=None):
        """Chieu cao toi thieu textbox de chua het chu, o mot he so nen."""
        _g1, _g2, g3, g4 = _range(nen)
        return _cao_dau(nen) + _cao_tieu_de(f_t, d_t) + g3 + max(via_h, 34) + g4

    nen = 1.0
    box_min = _box_min()
    if ratio in RATIOS:
        # Khoa ti le dau ra. Kieu tran KHONG thuong luong chieu cao: anh phu
        # kin the va vung chu la mot lop DE LEN anh, khong ai lan cho ai.
        H = RATIOS[ratio]
        # Vung chu luon lay dung phan da dinh, KE CA khi anh thap hon the.
        # Truoc 07/09/2026 nhanh "anh thap" keo box_h len `H - nat_h` de phan
        # thieu cua anh thanh nen cua vung chu — tuc dung mot mang MAU DAC lam
        # nen, va anh cang thap thi mang do cang cao. Nay `_layer_image` lap day
        # bang chinh tam anh lam mo, nen chieu cao vung chu khong con phu
        # thuoc vao anh cao bao nhieu.
        box_h = max(box_min, int(H * CEILING_TEXTBOX))
        # Cho trong con lai danh cho tieu de no, chan o CEILING_TITLE_LINES dong.
        _g1, _g2, _g3, _g4 = _range(nen)
        frame_h = _cao_dau(nen) + _g3 + max(via_h, 34) + _g4
        f_title, title_lines = _grow_title(probe, title.upper(), avail_w,
                                           min(box_h - frame_h, round(H * TEXT_MAX_SHARE)),
                                           max_lines=CEILING_TITLE_LINES,
                                           lead=lead, path=F_HERO,
                                           weight=HERO_WEIGHT,
                                           hi=CEILING_TITLE_MAX)
    else:
        box_h = box_min
        H = nat_h + box_h
    # Moc tren cua vung chu. Khong con la "day anh" nhu ten `img_h` cu goi y:
    # anh phu kin the o moi truong hop, day chi la cho khoi chu bat dau.
    split = H - box_h

    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    # Lop anh dung chung voi kieu quote: nen mo phu kin + anh sac full be ngang,
    # mep duoi tan dan. KHONG con nhanh "anh thap -> nen mau dac" (xem _layer_image).
    _layer_image(canvas, src_img, H)
    d = ImageDraw.Draw(canvas)
    g1, _g2, g3, g4 = _range(nen)

    # Kieu tran khong co ranh gioi anh/chu, nen nhan (kicker) tut han xuong
    # thanh hang dau tien cua khoi chu. Khi khoa ti le, CAN GIUA DOC ca cum
    # (kicker + tieu de) TRUOC khi ve — kicker va tieu de phai troi cung nhau.
    y = split + g1
    cao_cum = (kick_h + KICKER_GAP if kicker else 0) + _cao_tieu_de()
    if ratio != "free":
        _thua = (H - g4 - via_h - g3) - y - cao_cum
        if _thua > 0:
            y += _thua // 2
    cum_top, cum_bot = y, y + cao_cum

    # ---- KHUNG + MAU CHU (Ong Chu chot 07/09/2026) --------------------------
    # Truoc do kieu full_bleed doc duoc nho MOT MAN TOI dai phu ca vung chu, va chu
    # luon la FG. Man toi do chinh la thu bien vung chu thanh mot mang thu hai,
    # va o anh thap thi phan duoi con la MAU NEN DAC — dung cai IMAGE_RULES muc 7
    # cam. Nay di dung duong cua kieu quote: khong man toi, chi LAM MO CUC BO
    # dai chu, roi mau chu do theo chinh vung da mo.
    bottom_y = H - g4 - via_h
    frame_top = max(CEILING_FRAME_PAD, cum_top - CEILING_FRAME_PAD)
    frame_bot = min(bottom_y - 16, cum_bot + CEILING_FRAME_PAD)
    (_text_bg_overlay if cluttered else _open_region_text)(canvas, frame_top)

    # DO THEO TUNG DAI DONG, khong phai mot trung binh cho ca khoi: ranh
    # sang/toi ngang cat qua khoi chu la ca rat thuong (anh chup hero toi tren
    # nen trang duoi, anh ghep doc hai tone). Mot phep trung binh thi nua khoi
    # thanh trang-tren-trang hoac den-tren-den. `_can_board_line` (khong phai
    # `_bright_region` truc tiep) vi mot dai RONG van co the co diem sang/toi cuc
    # bo du trung binh ca dai dung phe — xem ghi chu tai dinh nghia ham.
    buoc, tren = _step_line(f_title, title_lines, lead)
    dau_tieu_de = cum_top + (kick_h + KICKER_GAP if kicker else 0)
    dai_dong = [(CEILING_TEXT_X, dau_tieu_de + i * buoc,
                 W - CEILING_TEXT_X, dau_tieu_de + (i + 1) * buoc)
                for i in range(len(title_lines))]
    sang_dong = [_can_board_line(canvas, b) for b in dai_dong] or [0.0]
    mau_dong = [FG if sg < THRESHOLD_BACKGROUND_BRIGHT else BG for sg in sang_dong]
    # Phe cua CA KHOI — dung cho net khung, kicker, va mau ten hang trong tieu de.
    nen_sang = sum(1 for sg in sang_dong if sg >= THRESHOLD_BACKGROUND_BRIGHT) * 2 >= len(sang_dong)
    mau_net = _enough_dark(CYAN) if nen_sang else CYAN

    # Khung chu nhat bo goc, bon net day du. Ve TRUOC chu de chu nam tren net
    # neu co cham nhau.
    d.rounded_rectangle([CEILING_FRAME_X, frame_top, W - CEILING_FRAME_X, frame_bot],
                        radius=CEILING_FRAME_R, outline=mau_net, width=CEILING_FRAME_LW)

    if kicker:
        # Kicker do RIENG dai cua chinh no: no nam tren cung khoi chu, tuc o
        # phan anh sang/toi khac voi may dong tieu de duoi.
        mau_kick = _color_change_background_hide_whole(
            canvas, (CEILING_TEXT_X, cum_top, W - CEILING_TEXT_X, cum_top + max(kick_h, 8)))
        mau_kick = _enough_dark(CYAN) if mau_kick == BG else CYAN
        rong_chu = _empty_tracked(d, kicker, f_kick, KICKER_TRACK)
        # Tru _kb[1] de DINH chu roi dung vao y, khong phai goc ascender.
        _about_tracked(d, (W - rong_chu) / 2, y - _kb[1], kicker, f_kick,
                    mau_kick, KICKER_TRACK)
        # Hai duong ke hai ben. Ca cum rong dung KICKER_PHRASE cua the, nen ke
        # NGAN LAI khi chu dai ra — cum giu nguyen be ngang, chu khong phai
        # ke giu nguyen do dai. Chu qua dai thi khong con cho, bo ke di.
        rong_ke = (W * KICKER_PHRASE - rong_chu) / 2 - KICKER_FAMILY
        if rong_ke >= 24:
            giua = y + kick_h / 2
            trai = (W - rong_chu) / 2 - KICKER_FAMILY
            d.line([(trai - rong_ke, giua), (trai, giua)],
                   fill=mau_kick, width=2)
            d.line([(W - trai, giua), (W - trai + rong_ke, giua)],
                   fill=mau_kick, width=2)
        y += kick_h + KICKER_GAP

    # Tieu de can giua: chu noi tren anh, truc doi xung cua tam anh la moc duy
    # nhat. Ve TUNG TU (de to ten thuong hieu) nen do be ngang dung cach do.
    def _x_chu(ln, font):
        return (W - _empty_line(d, ln, font)) / 2

    che_do_to = b.get("company_name_color")
    mau_du_phong = b.get("fallback_company_color")
    # Dat dong dau bang DINH CHU chu khong bang goc ve: nho vay khoang ho toi
    # kicker khong doi theo viec dong do co dau hay khong.
    # strict=False co y: `sang_dong` co hau to `or [0.0]` nen o ca tieu de rong
    # (khong xay ra qua CLI, nhung `build` la thu vien) hai danh sach lech mot.
    # Dong tieu de la cac lat LIEN TIEP cua `title.split()` (_wrap), nen mau tung tu cua ten
    # model tinh mot lan tren ca cau roi cat theo dong — cum ten model vat qua hai dong van to.
    marks, dau = model_marks(title), 0
    for ln, mau_ln in zip(title_lines, mau_dong, strict=False):
        n = len(ln.split(" "))
        _about_line(d, _x_chu(ln, f_title), y - tren, ln, f_title, mau_ln,
                 che_do_to, mau_du_phong, nen_sang=(mau_ln == BG), marks=marks[dau:dau + n])
        dau += n
        y += buoc

    # Chan the chi con TEN KENH, can giua. Nguon van phai ghi, nhung ghi o chu
    # thich bai dang; mot hero image dung mot minh thi cai phai nho la TEN KENH.
    # Do RIENG dai cua chinh no: no nam NGOAI khung, va anh co khoi chu toi
    # nhung day the sang la ca rat thuong (loi dong nguon quote 06/09/2026).
    f_handle = _f(F_REG, max(12, round(BRAND_SIZE * co_chan)), weight=500)
    mau_handle = _color_change_background_hide_whole(canvas, (0, bottom_y, W, bottom_y + via_h))
    mau_handle = (_enough_dark(CYAN) if mau_handle == BG
                  else _phase(CYAN, b.get("handle_clarity", mo_chan)))
    ten = handle if handle.startswith("@") else "@" + handle
    bb = f_handle.getbbox("Ay")
    d.text(((W - d.textlength(ten, font=f_handle)) / 2,
            bottom_y + via_h / 2 - (bb[3] - bb[1]) / 2 - bb[1]),
           ten, font=f_handle, fill=mau_handle)

    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.convert("RGB").save(out, "PNG", optimize=True)
    print("the: {}x{} ({:.2f}:1) | anh: {}px tu nhien | vung chu: {}px | khung {}..{}".format(
        W, H, W / H, nat_h, box_h, int(frame_top), int(frame_bot)))
    return out


def main():
    p = argparse.ArgumentParser(description="Dựng thẻ ảnh hero cho kênh AI")
    p.add_argument("--image", required=True)
    p.add_argument("--image2", default=None,
                   help="Anh NGANG thu hai, ghep DOC duoi --image trong cung khung "
                        "(dung khi anh chinh qua chu nhat ngang, thay vi crop mat tieu de)")
    p.add_argument("--title", required=True,
                   help="Cau trich dan (--kieu quote) hoac cau tieu de tron ven (--kieu full_bleed)")
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
                   choices=sorted(BRAND),
                   help="Bo nhan dien: donniechublog (xanh dem) hoac dcgr (trang den)")
    p.add_argument("--tagline", default="daily AI update",
                   help="Chip tagline o goc duoi-trai khung quote (chip category)")
    p.add_argument("--kicker", default="",
                   help="Nhan ngan phia tren tieu de, CHI co o --kieu full_bleed. "
                        "Vi du: BREAKING, MODEL RELEASE, AGENT, FUNDING")
    p.add_argument("--kieu", default="quote",
                   choices=list(role_spec.CARD_STYLES) + list(role_spec.CARD_STYLE_LEGACY_VALUES),
                   help="quote: the trich dan — cau noi lon trong ngoac kep, co dong "
                        "nguon o duoi (--title la cau, --attrib la nguon). "
                        "full_bleed (cu: tran): anh phu kin the, tieu de de len qua man toi.")
    p.add_argument("--attrib", default="",
                   help="Dong nguon cho --kieu quote, vi du: "
                        "\"Doc bai 'Ten bai' - Tac gia\"")
    p.add_argument("--ratio", default="free",
                   choices=["free"] + list(RATIOS),
                   help="free: chiều cao trôi theo ảnh. 1:1/4:5/3:4: khoá tỉ lệ")
    p.add_argument("--out", required=True)
    p.add_argument("--logo-card", action="store_true",
                   help="Anh la THE LOGO 4:5 cua hang (LOW-337): dung mot minh lam hero, khong bi chan nhu chart")
    p.add_argument("--cluttered", action="store_true",
                   help="Anh roi (cluttered) buoc phai dung: nen chu dac thay lam mo (LOW-47)")
    a = p.parse_args()
    build([a.image, a.image2] if a.image2 else a.image, a.title, a.out,
          handle=a.handle, ratio=a.ratio, tagline=a.tagline, brand=a.brand,
          bo_qua_dau=a.bo_qua_dau, kieu=a.kieu, kicker=a.kicker, attrib=a.attrib,
          bo_qua_anh=a.bo_qua_anh, nhan_vat=a.nhan_vat, cluttered=a.cluttered,
          logo_card=a.logo_card)


if __name__ == "__main__":
    main()
