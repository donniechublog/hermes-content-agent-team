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
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont

ASSETS = Path(__file__).resolve().parent / "assets"
FONTS = ASSETS / "fonts"
ICONS = ASSETS / "icons"
MASCOT_PATH = ASSETS / "mascot.png"

# Brand guideline: JetBrains Mono cho heading/UI, Inter cho body text
F_BOLD = str(FONTS / "JetBrainsMono-ExtraBold.ttf")   # tieu de
F_UI = str(FONTS / "JetBrainsMono-Bold.ttf")          # nhan category, UI
F_REG = str(FONTS / "Inter.ttf")                      # body: subtitle, via

W = 1200                          # bề ngang cố định
IMG_MIN_H = 600                   # ảnh không mỏng hơn 2:1
IMG_MAX_H = 1200                  # ảnh không cao hơn 1:1
PAD = 44

BG = (14, 17, 23)             # #0e1117 background
BG_CARD = (22, 27, 34)        # #161b22 background card
FG = (230, 237, 243)          # #e6edf3 text primary
MUTED = (139, 147, 158)       # #8b939e text muted
ACCENT = (88, 166, 255)       # #58a6ff accent / CTA
ACCENT_DIM = (31, 111, 235)   # #1f6feb accent dim — dung cho mat khoi
CYAN = (0, 204, 224)          # #00cce0 accent highlight (mau logo)
LINE = (48, 54, 61)           # duong vien phu, cung ho voi bg card

SOCIALS = ["telegram", "linkedin", "x-twitter", "tiktok", "youtube"]

MASCOT_MAX_H_RATIO = 0.10
MASCOT_MARGIN = 44

TITLE_SIZE_HI, TITLE_SIZE_LO = 56, 38
TITLE_GROW_MAX = 104              # trần khi tiêu đề nở vào chỗ trống
TITLE_GROW_LINES = 2   # tuyet doi khong de tieu de 3 dong
SUB_SIZE = 26
CHIP_SIZE = 26
VIA_SIZE = 19
BRAND_SIZE = 18   # ten kenh nho hon dong via mot chut

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
    path = F_BOLD if bold else F_REG
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
    inset = 40
    fitted = _fit_contain(src_img, W - inset * 2, img_h - inset * 2)
    x, y = (W - fitted.width) // 2, (img_h - fitted.height) // 2
    canvas.paste(fitted, (x, y))
    ImageDraw.Draw(canvas).rectangle(
        [x - 1, y - 1, x + fitted.width, y + fitted.height],
        outline=(*LINE, 255), width=2)
    return (x, y, fitted.width, fitted.height)


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

    # Tam giac gap, cung mau than the:
    #   "down" — bam goc tren-phai, thon dan xuong (the trai, nam de len anh)
    #   "up"   — bam goc TREN-trai, dinh nhon huong len (the phai)
    # Ca hai deu nam o nua tren cua the, tuc phan de len anh.
    if fold == "down":
        d.polygon([(x + bw, y), (x + bw + fold_w, y), (x + bw, y + fold_w)],
                  fill=CYAN)
    elif fold == "up":
        tri = [(x, y), (x, y + fold_w), (x - fold_w, y + fold_w)]
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
    if not MASCOT_PATH.exists():
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


def _social_row(canvas, d, right_x, cy, handle, font, icon_size=26, gap=10):
    """Hang icon + ten kenh, can sat le phai. Cung tong mau voi cum via."""
    handle_text = handle if handle.startswith("@") else "@" + handle
    b = font.getbbox("Ay")
    tw = d.textlength(handle_text, font=font)
    x = right_x - tw
    d.text((x, cy - (b[3] - b[1]) / 2 - b[1]), handle_text, font=font,
           fill=ACCENT)
    x -= gap + 4
    for name in reversed(SOCIALS):
        icon = _load_icon(name, icon_size, FG)
        x -= icon_size
        if icon is not None:
            canvas.alpha_composite(icon, (int(x), int(cy - icon_size / 2)))
        x -= gap





def _tech_frame(d, H, split, side_col=LINE, box_col=LINE):
    m, brk = 18, 46
    # Hai goc tren: mau nhan. Hai goc duoi: mau trang, cung do day.
    for (x, y, dx, dy, col) in ((m, m, 1, 1, CYAN),
                                (W - m, m, -1, 1, CYAN),
                                (m, H - m, 1, -1, FG),
                                (W - m, H - m, -1, -1, FG)):
        d.line([(x, y), (x + dx * brk, y)], fill=col, width=3)
        d.line([(x, y), (x, y + dy * brk)], fill=col, width=3)
    # Hai net doc chay lien mach doc hai ben vung anh
    for x in (m, W - m):
        d.line([(x, m + brk + 12), (x, split - 12)], fill=side_col, width=2)
    # Hai net doc trong textbox — mau nghich voi net o vung anh, tao nhip
    for x in (m, W - m):
        d.line([(x, split + 12), (x, H - m - brk - 12)], fill=box_col, width=2)
    d.line([(0, split), (int(W * 0.34), split)], fill=LINE, width=2)
    d.line([(int(W * 0.42), split), (W, split)], fill=LINE, width=2)
    d.line([(int(W * 0.34), split), (int(W * 0.40), split)],
           fill=ACCENT, width=3)


def build(src, title, subtitle, via, out, category="AI",
          category_right="", handle="donniechublog", ratio="free",
          tagline="daily AI update"):
    src_img = Image.open(src).convert("RGB")
    img_h, how = _plan_image(src_img)

    # Đo trước phần chữ để biết textbox cần cao bao nhiêu
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    f_chip = _f(F_UI, CHIP_SIZE)
    f_via = _f(F_REG, VIA_SIZE, weight=500)
    avail_w = W - PAD * 2

    f_title, title_lines = _fit_text(probe, title.upper(), avail_w,
                                      max_lines=2, hi=TITLE_SIZE_HI,
                                      lo=TITLE_SIZE_LO, bold=True)
    f_sub, sub_lines = _fit_text(probe, subtitle, avail_w, max_lines=3,
                                  hi=SUB_SIZE, lo=18)
    _, chip_h = _chip_size(probe, category.upper(), f_chip)
    via_h = f_via.getbbox("Ây")[3] - f_via.getbbox("Ây")[1]

    # Chiều cao tối thiểu textbox cần để chứa hết chữ
    box_min = (chip_h // 2 + 24
               + _line_h(f_title, 6) * len(title_lines) + 10
               + _line_h(f_sub, 6) * len(sub_lines)
               + 34 + max(via_h, 34) + PAD)

    if ratio in RATIOS:
        # Khoá tỉ lệ đầu ra: textbox phình ra bù phần ảnh thiếu.
        # Ảnh càng ngang (16:9) thì textbox càng cao — đúng ý đồ bố cục.
        H = RATIOS[ratio]
        if H - img_h < box_min:
            # Ảnh quá cao, phải thu lại để chừa đủ chỗ cho chữ
            img_h, how = H - box_min, "letterbox"
        box_h = H - img_h
        # Chỗ trống chia theo thứ tự ưu tiên: khung cố định -> subtitle
        # (tối đa 3 dòng) -> phần còn lại dành cho tiêu đề nở, chặn ở 2 dòng.
        frame_h = (chip_h // 2 + 24 + 10 + 34 + max(via_h, 34) + PAD)
        sub_h = _line_h(f_sub, 6) * len(sub_lines)
        f_title, title_lines = _grow_title(probe, title.upper(), avail_w,
                                           box_h - frame_h - sub_h)
    else:
        box_h = box_min
        H = img_h + box_h

    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    o_anh = _render_image_area(canvas, src_img, img_h, how)
    _paste_mascot(canvas, img_h, o_anh)
    d = ImageDraw.Draw(canvas)
    # Mot he mau co dinh, khong phu thuoc anh sang hay toi:
    #   vung anh   -> cyan, dong bo voi hai ngoac goc TREN va nhan category
    #   vung chu   -> trang, dong bo voi hai ngoac goc DUOI
    _tech_frame(d, H, img_h, CYAN, FG)

    # Nhan category vat qua ranh gioi anh/textbox — khau hai vung lam mot,
    # dong thoi tra lai chieu cao textbox cho tieu de.
    chip_y = img_h - chip_h // 2
    _chip(d, PAD, chip_y, category.upper(), f_chip, solid=True,
          fold="down")
    if category_right:
        _chip(d, 0, chip_y, category_right.upper(), f_chip,
              right_align=W - PAD, fold="up")
    y = img_h + chip_h // 2 + 24

    for ln in title_lines:
        d.text((PAD, y), ln, font=f_title, fill=FG)
        y += _line_h(f_title, 6)
    y += 10

    for ln in sub_lines:
        d.text((PAD, y), ln, font=f_sub, fill=MUTED)
        y += _line_h(f_sub, 6)

    bottom_y = H - PAD - via_h
    via_text = via if via.startswith("via:") else "via: " + via
    d.text((PAD, bottom_y), via_text, font=f_via, fill=ACCENT)
    _social_row(canvas, d, W - PAD, bottom_y + via_h / 2, handle,
                _f(F_REG, BRAND_SIZE, weight=500))

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
    p.add_argument("--handle", default="donniechublog")
    p.add_argument("--tagline", default="daily AI update",
                   help="Mo ta ngan duoi ten kenh trong khoi thuong hieu")
    p.add_argument("--ratio", default="free",
                   choices=["free"] + list(RATIOS),
                   help="free: chiều cao trôi theo ảnh. 1:1/4:5/3:4: khoá tỉ lệ, "
                        "textbox phình ra bù phần ảnh thiếu")
    p.add_argument("--out", required=True)
    a = p.parse_args()
    build(a.image, a.title, a.subtitle, a.via, a.out,
          a.category, a.category_right, a.handle, a.ratio, a.tagline)


if __name__ == "__main__":
    main()
