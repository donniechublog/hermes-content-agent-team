#!/usr/bin/env python3
"""logo_card.py — dung SLIDE LOGO: logo phong to 90% be ngang tren chinh mau nen cua no.

Ong Chu 20/09/2026, sau khi xem hai ban dung thu bang logo Google/OpenAI/Anthropic that:
*"Chi can phong to logo cho hien thi het 90% chieu rong. Phan con du lai, dat text mau
tuong phan len la duoc, dung co them nen text, rat la phen."*

Vi sao can (LOW-295): luat anh trong (LOW-273) chan logo tren nen tron o moi designer, ma
tin nhieu hang thi logo la anh tu nhien nhat — tin "Don kien cao buoc Anthropic, OpenAI,
SpaceXAI va Google" co 6 anh bi chan kieu nay. Cat vao khung 4:5 KHONG cuu duoc: logo chu
la dai ngang dep (Google 1200x1500, hop chu cao 0.23 khung) nen cat xong van trong 80%;
do tren may chu chi 3/32 anh cat ra lap duoc khung.

Ham THUAN (PIL), khong biet vai nao goi: nhan hop logo da do (vision `subject_box`) va tra
ve mot tam anh dung san o dung co khung cua renderer.
"""
from PIL import Image

LOGO_WIDTH_SHARE = 0.90          # logo chiem 90% be ngang khung (Ong Chu chot)
LOGO_MAX_HEIGHT_SHARE = 0.42     # ... nhung khong cao qua muc nay, con cho cho chu
LOGO_CENTER_Y = 0.34             # tam logo o 34% chieu cao: nam gon phan tren, khong dinh chu
BOX_MARGIN = 0.04                # le quanh hop logo khi cat sat (theo canh hop)
CORNER = 6                       # o vuong lay mau nen o bon goc anh goc


def background_color(im: Image.Image) -> tuple:
    """Mau NEN cua anh logo: mau hay gap nhat o bon goc (logo thuong nam giua)."""
    im = im.convert("RGB")
    w, h = im.size
    diem = []
    for x0, y0 in ((0, 0), (w - CORNER, 0), (0, h - CORNER), (w - CORNER, h - CORNER)):
        o = im.crop((x0, y0, x0 + CORNER, y0 + CORNER))
        diem.extend(list(o.getdata()))
    dem = {}
    for p in diem:
        k = tuple(v // 8 for v in p)                  # gom mau gan giong
        dem.setdefault(k, []).append(p)
    lon = max(dem.values(), key=len)
    n = len(lon)
    return tuple(sum(p[i] for p in lon) // n for i in range(3))


def is_light(bg) -> bool:
    return (0.299 * bg[0] + 0.587 * bg[1] + 0.114 * bg[2]) >= 140


def text_color(bg) -> tuple:
    """Mau chu TUONG PHAN voi nen (khong them nen chu — Ong Chu 20/09)."""
    return (17, 17, 20) if is_light(bg) else (255, 255, 255)


def crop_logo(im: Image.Image, box) -> Image.Image:
    """Cat sat quanh hop logo (toa do 0..1 cua vision), chua le BOX_MARGIN."""
    w, h = im.size
    x0, y0, x1, y1 = box
    mx, my = (x1 - x0) * w * BOX_MARGIN, (y1 - y0) * h * BOX_MARGIN
    return im.crop((max(0, int(x0 * w - mx)), max(0, int(y0 * h - my)),
                    min(w, int(x1 * w + mx)), min(h, int(y1 * h + my))))


def build_card(path, box, w: int, h: int) -> tuple:
    """-> (anh khung w x h co logo 90% be ngang tren nen cua chinh no, mau nen).

    `box`: hop logo 0..1 (vision `subject_box`); thieu thi lay ca tam."""
    im = Image.open(path).convert("RGB")
    bg = background_color(im)
    lg = crop_logo(im, box) if box else im
    # Ti le tinh theo CHINH HOP LOGO, khong tinh le cat: Ong Chu doi logo hien het 90% be
    # ngang. Tinh theo anh da cat thi logo chi con ~80% (do 20/09).
    rong_logo = (box[2] - box[0]) * im.width if box else lg.width
    ty = min(w * LOGO_WIDTH_SHARE / max(1, rong_logo), w / lg.width,
             h * LOGO_MAX_HEIGHT_SHARE / lg.height)
    lg = lg.resize((max(1, round(lg.width * ty)), max(1, round(lg.height * ty))), Image.Resampling.LANCZOS)
    khung = Image.new("RGB", (w, h), bg)
    khung.paste(lg, ((w - lg.width) // 2, max(0, round(h * LOGO_CENTER_Y) - lg.height // 2)))
    return khung, bg


def is_logo_image(a: dict) -> bool:
    """Tam anh nay co phai LOGO tren nen tron (loai bi LOW-273 chan) khong."""
    return bool(a.get("subject_kind") == "logo" and a.get("subject_box")
                and a.get("empty_share") is not None)
