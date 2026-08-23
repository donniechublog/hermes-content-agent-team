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
F_REG = str(FONTS / "Inter.ttf")                      # via, ten kenh, UI phu
# Phu de dung serif: no la cau dan chuyen, khong phai nhan UI. Chan chu tao
# nhip doc cham hon tieu de mono, hai tang chu tach bach han thay vi chi khac
# co. Dung ban Text chu KHONG dung ban Display: Display tuong phan net cao,
# net manh mong qua nen o co chu nho doc met mat.
F_SUB = str(FONTS / "NotoSerif.ttf")                  # phu de

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
TITLE_GROW_LINES = 2   # tuyet doi khong de tieu de 3 dong
SUB_SIZE = 31
CHIP_SIZE = 26
VIA_SIZE = 29
BRAND_SIZE = 27   # ten kenh nho hon dong via mot chut

# Tỉ lệ đầu ra khoá cứng: tên → chiều cao thẻ (bề ngang luôn 1200)
RATIOS = {"1:1": 1200, "4:5": 1500, "3:4": 1600}


def _f(path, size, weight=None):
    f = ImageFont.truetype(path, size)
    if weight is not None:
        try:                       # Inter la font bien thien (opsz, wght)
            f.set_variation_by_axes([float(size), float(weight)])
        except Exception:          # noqa: BLE001 — font tinh thi bo qua
            pass
    return f


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


def _fit_text(d, text, max_w, max_lines, hi, lo, bold=False):
    path = F_BOLD if bold else F_SUB
    for size in range(hi, lo - 1, -2):
        f = _f(path, size)
        lines = _wrap(d, text, f, max_w)
        if len(lines) <= max_lines:
            return f, lines
    f = _f(path, lo)
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


def _grow_title(d, text, max_w, max_h, max_lines=TITLE_GROW_LINES):
    """Chọn cỡ chữ lớn nhất mà tiêu đề vẫn vừa cả bề ngang lẫn chiều cao trống.

    Chỉ dùng khi tỉ lệ thẻ bị khoá — lúc đó textbox có chiều cao cố định nên
    biết chính xác còn bao nhiêu chỗ cho tiêu đề.
    """
    best = None
    for size in range(TITLE_GROW_MAX, TITLE_SIZE_LO - 1, -2):
        f = _f(F_BOLD, size)
        lines = _wrap(d, text, f, max_w)
        if len(lines) > max_lines:
            continue
        if _line_h(f, 6) * len(lines) <= max_h:
            best = (f, lines)
            break
    if best is None:                       # chỗ quá hẹp — về cỡ nhỏ nhất
        f = _f(F_BOLD, TITLE_SIZE_LO)
        lines = _wrap(d, text, f, max_w)[:max_lines]
        if lines:
            lines[-1] = lines[-1].rstrip(" .,") + "…"
        best = (f, lines)
    return best


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


def _tran_anh(canvas, src_img, split):
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
    # Phu kin the phai phong anh len. Phong qua nguong thi vo net va cat mat
    # noi dung — da thay ro voi anh nguon 1200x630 keo len kho 4:5, phai phong
    # 2.4 lan, chu trong anh bay mat mot nua. Qua nguong thi doi cach: nen la
    # ban cover lam mo, con ban SAC dat tron ven len tren. Van la mot mat phang
    # lien, khong co vach, nhung khong danh doi do net.
    can = max(W / src_img.width, H / src_img.height)
    if can <= NGUONG_PHONG:
        canvas.paste(_fit_cover(src_img, W, H), (0, 0))
    else:
        canvas.paste(_fit_cover(src_img, W, H).filter(
            ImageFilter.GaussianBlur(56)), (0, 0))
        sac = _fit_contain(src_img, W, split)
        canvas.paste(sac, ((W - sac.width) // 2, (split - sac.height) // 2))
    # Man bat dau mo han tu tren dinh (anh van doc duoc), dam dan xuong, va
    # dam han o vung chu. Diem uon dat tren `split` mot doan de khong co mot
    # duong gay lo ra dung cho chu bat dau.
    uon = max(0, split - int(H * 0.18))
    man = Image.new("L", (1, H))
    for y in range(H):
        if y <= uon:
            a = int(90 * (y / max(1, uon)) ** 2)
        else:
            t = (y - uon) / max(1, H - uon)
            a = int(90 + (238 - 90) * t ** 0.85)
        man.putpixel((0, y), min(255, a))
    lop = Image.new("RGBA", (W, H), (*BG, 255))
    lop.putalpha(man.resize((W, H)))
    canvas.alpha_composite(lop)
    return (0, 0, W, H)


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


def _load_icon(name, size, color):
    src = ICONS / (name + ".svg")
    if not src.exists():
        return None
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
        out = tmp.name
    try:
        subprocess.run(["rsvg-convert", str(src), "-w", str(size),
                        "-h", str(size), "-o", out],
                       check=True, capture_output=True, timeout=20)
        icon = Image.open(out).convert("RGBA")
    except Exception:                                        # noqa: BLE001
        return None
    finally:
        Path(out).unlink(missing_ok=True)
    tinted = Image.new("RGBA", icon.size, (*color, 0))
    tinted.putalpha(icon.split()[-1])
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





def _tech_frame(d, H, split, side_col=LINE, box_col=LINE, vach=True):
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
          tagline="daily AI update", khoa_ti_le=False, brand="donniechublog",
          bo_qua_dau=False, kieu="dai"):
    # Nap bang mau TRUOC moi thu khac: cac ham ve doc BG/FG/ACCENT o pham vi
    # module, chua nap thi chung con la None.
    b = dat_thuong_hieu(brand)
    handle = handle or b["handle"]
    title, subtitle = bo_dau_cam(title), bo_dau_cam(subtitle)

    # Chan tieng Viet khong dau TRUOC khi ve, o moi cho chu hien len the.
    loi = {}
    for ten, gt in (("tieu de", title), ("phu de", subtitle),
                    ("category", category), ("category-right", category_right),
                    ("via", via)):
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
    src_img = Image.open(src).convert("RGB")
    img_h, how = _plan_image(src_img)

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

    f_title, title_lines = _fit_text(probe, title.upper(), avail_w,
                                      max_lines=2, hi=TITLE_SIZE_HI,
                                      lo=TITLE_SIZE_LO, bold=True)
    f_sub, sub_lines = _fit_text(probe, subtitle, avail_w, max_lines=3,
                                  hi=SUB_SIZE, lo=22)
    _, chip_h = _chip_size(probe, category.upper(), f_chip)
    via_h = f_via.getbbox("Ây")[3] - f_via.getbbox("Ây")[1]

    # Chiều cao tối thiểu textbox cần để chứa hết chữ, ở một hệ số nén cho trước
    def _box_min(nen=1.0, f_t=None, d_t=None, f_s=None, d_s=None):
        g1, g2, g3, g4 = _khoang(nen)
        return (chip_h // 2 + g1
                + _line_h(f_t or f_title, 6) * len(d_t or title_lines) + g2
                + _line_h(f_s or f_sub, 6) * len(d_s or sub_lines)
                + g3 + max(via_h, 34) + g4)

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

        # ẢNH ĐƯỢC ƯU TIÊN. Thứ tự nhường chỗ, từ ít thiệt hại đến nhiều:
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
                if not khoa_ti_le:
                    H = img_h + box_min          # tha the dai hon la thu anh
                else:
                    img_h, how = H - box_min, "letterbox"
                    print(f"[canh bao] khoa ti le {ratio} nen phai thu anh xuong "
                          f"{img_h}px — bo --ratio de hien day du.", file=sys.stderr)
        # ANH LA CHINH, TEXTBOX LA PHU. Truoc day toan bo cho thua bi don het
        # vao textbox: khoa 4:5 thi chu chiem 58% chieu cao con anh 42%, nguoc
        # vai tro. Nay textbox chi lay phan chu that su can, tran o TRAN_TEXTBOX;
        # phan con lai tra cho vung anh, anh nam giua tren nen mo cung tong mau.
        box_h = min(H - img_h, max(box_min, int(H * TRAN_TEXTBOX)))
        if H - box_h != img_h:
            img_h, how = H - box_h, "letterbox"
        # Chỗ trống chia theo thứ tự ưu tiên: khung cố định -> subtitle
        # (tối đa 3 dòng) -> phần còn lại dành cho tiêu đề nở, chặn ở 2 dòng.
        _g1, _g2, _g3, _g4 = _khoang(nen)
        frame_h = (chip_h // 2 + _g1 + _g2 + _g3 + max(via_h, 34) + _g4)
        # Chia cho trong: tieu de truoc (no toi 2 dong), phan con lai cho phu de.
        # Neu textbox van thua thi phu de no theo — thay vi de mot dong chu nho
        # lo lung giua khoang trong.
        sub_h = _line_h(f_sub, 6) * len(sub_lines)
        f_title, title_lines = _grow_title(probe, title.upper(), avail_w,
                                           box_h - frame_h - sub_h)
        con_lai = box_h - frame_h - _line_h(f_title, 6) * len(title_lines)
        if con_lai > _line_h(f_sub, 6) * len(sub_lines) + 12:
            f_sub, sub_lines = _grow_sub(probe, subtitle, avail_w, con_lai)
    else:
        box_h = box_min
        H = img_h + box_h

    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    if kieu == "tran":
        o_anh = _tran_anh(canvas, src_img, img_h)
    else:
        o_anh = _render_image_area(canvas, src_img, img_h, how)
        _paste_mascot(canvas, img_h, o_anh)
    d = ImageDraw.Draw(canvas)
    # Mot he mau co dinh, khong phu thuoc anh sang hay toi:
    #   vung anh   -> cyan, dong bo voi hai ngoac goc TREN va nhan category
    #   vung chu   -> trang, dong bo voi hai ngoac goc DUOI
    _tech_frame(d, H, img_h, CYAN, FG, vach=(kieu != "tran"))

    # Nhan category vat qua ranh gioi anh/textbox — khau hai vung lam mot,
    # dong thoi tra lai chieu cao textbox cho tieu de.
    chip_y = img_h - chip_h // 2
    if b.get("nhan_trai", True):
        _chip(d, PAD, chip_y, category.upper(), f_chip, solid=True,
              fold="down")
    if category_right:
        _chip(d, 0, chip_y, category_right.upper(), f_chip,
              right_align=W - PAD, fold="up")
    g1, g2, g3, g4 = _khoang(nen)
    y = img_h + chip_h // 2 + g1

    # Khi ti le bi khoa, tieu de va phu de da no het co cho phep ma textbox van
    # con thua thi day khoi chu xuong giua thay vi de no dinh sat mep tren va bo
    # lai mot mang trong o duoi.
    if ratio != "free":
        _cao_chu = (_line_h(f_title, 6) * len(title_lines) + g2
                    + _line_h(f_sub, 6) * len(sub_lines))
        _cho_trong = (H - g4 - via_h - g3) - y - _cao_chu
        if _cho_trong > 0:
            y += _cho_trong // 2

    for ln in title_lines:
        d.text((PAD, y), ln, font=f_title, fill=FG)
        y += _line_h(f_title, 6)
    y += g2

    # Phu de mac dinh dung MUTED cho lui ve sau. Thuong hieu nao muon ro hon thi
    # keo mau ve phia FG theo `ro_phu_de` — chu van nhat hon tieu de nhung doc
    # duoc thoai mai.
    mau_sub = MUTED if b.get("ro_phu_de") is None else _pha(FG, b["ro_phu_de"])
    for ln in sub_lines:
        d.text((PAD, y), ln, font=f_sub, fill=mau_sub)
        y += _line_h(f_sub, 6)

    bottom_y = H - g4 - via_h
    via_text = via if via.startswith("via:") else "via: " + via
    # Cum via lay CYAN cua bo nhan dien, giong ten kenh. Truoc day no dung ACCENT
    # (xanh duong) nen lech tong voi cyan o ngay ben canh.
    d.text((PAD, bottom_y), via_text, font=f_via, fill=_pha(CYAN, mo_chan))
    _social_row(canvas, d, W - PAD, bottom_y + via_h / 2, handle,
                _f(F_REG, max(12, round(BRAND_SIZE * co_chan)), weight=500),
                icon_size=max(16, round(39 * co_chan)),
                gap=max(8, round(15 * co_chan)),
                mau_chu=_pha(CYAN, b.get("ro_handle", mo_chan)),
                mau_icon=_pha(FG, mo_icon))

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
    p.add_argument("--subtitle", required=True)
    p.add_argument("--via", required=True)
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
    p.add_argument("--kieu", default="dai", choices=["dai", "tran"],
                   help="dai: anh o tren, textbox rieng o duoi (mac dinh). "
                        "tran: anh phu kin the, chu de len qua man toi")
    p.add_argument("--ratio", default="free",
                   choices=["free"] + list(RATIOS),
                   help="free: chiều cao trôi theo ảnh. 1:1/4:5/3:4: khoá tỉ lệ, "
                        "textbox phình ra bù phần ảnh thiếu")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    build(a.image, a.title, a.subtitle, a.via, a.out,
          a.category, a.category_right, a.handle, a.ratio, a.tagline,
          khoa_ti_le=getattr(a, "khoa_ti_le", False), brand=a.brand,
          bo_qua_dau=a.bo_qua_dau, kieu=a.kieu)


if __name__ == "__main__":
    main()
