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


# LOW-341 (Ong Chu 21/09/2026, xem slide quote MiniMax-H3: hinh paper nen trang -> anh sac /
# dai mo xam / overlay toi): *"hinh se bi tach thanh 3 khoi. luon uu tien dat chu mau tuong
# phan voi mau nen truoc khi phai dung toi nen chu"*. Logo khong phai loai duy nhat co nen
# phang: hinh trong paper, anh chup trang nen trang, bang so lieu cung vay. Anh nao VIEN la
# mot mau phang thi dung nhu slide logo: khung lay chinh mau nen do, noi dung phong 90% be
# ngang, chu tuong phan — khong dai mo, khong lop phu.
FLAT_RIM_SHARE = 0.01            # be day vien do, theo canh ngan cua ban do
FLAT_RIM_MIN = 3                 # ... nhung khong mong hon chung nay px
FLAT_TOLERANCE = 12              # lech toi da moi kenh so voi mau nen van tinh la nen
# Do 21/09 (11 hinh paper MiniMax-H3 + SoL-Pi, ke ca cap ghep doc lam bia, vs 26 anh chup nen
# khong phang), vien 1%, dung sai 12: hinh paper dat >= 0.927 ca vien, canh yeu nhat >= 0.757
# (hinh cat dinh dong chu than bai o mep); anh chup cao nhat 0.694 ca vien, canh yeu nhat
# <= 0.304. Vien 2% an vao chu cua hinh cat sat le (cap ghep bia SoL-Pi ra 0.906). Dung sai 20
# de lot nen mot mau co cham lom dom (anh gia `_ve` cua test_spec_dre: 0.908) — giay paper la
# mau thuan nen siet xuong 12 hinh gan nhu khong doi. Hai nguong nam giua hai nhom.
FLAT_MIN_SHARE = 0.90            # phan diem VIEN trung mau nen de anh la nen phang
FLAT_SIDE_MIN_SHARE = 0.70       # ... va MOI canh rieng cung phai dat muc nay
CONTENT_TOLERANCE = 28           # diem lech hon muc nay so voi nen la noi dung
CONTENT_MIN_PIXELS = 2           # hang/cot co it nhat chung nay diem noi dung moi tinh
FLAT_PROBE = 640                 # do tren ban thu nho (canh dai) — nhanh, va lam mo nhieu JPEG


def _probe(im: Image.Image) -> Image.Image:
    im = im.convert("RGB")
    if max(im.size) > FLAT_PROBE:
        im = im.copy()
        im.thumbnail((FLAT_PROBE, FLAT_PROBE), Image.Resampling.BOX)
    return im


def flat_background(im: Image.Image):
    """Mau NEN (r, g, b) neu VIEN anh la mot mau phang, None neu khong (LOW-341).

    Do ca bon canh chu khong chi bon goc nhu `background_color`: anh chup co goc trung mau
    (troi, tuong) van khong phai nen phang. Mau nen = nhom mau hay gap nhat tren vien. Chu
    lac o mep (so hieu arXiv doc canh trai, dong chu bi cat o mep tren) chiem it diem vien
    nen van qua duoc, con anh chup (gradient, chu the cham mep) thi khong."""
    import numpy as np
    a = np.asarray(_probe(im), dtype=np.int16)
    h, w = a.shape[:2]
    t = max(FLAT_RIM_MIN, round(min(w, h) * FLAT_RIM_SHARE))
    if min(w, h) <= 2 * t:
        return None
    sides = [a[:t].reshape(-1, 3), a[-t:].reshape(-1, 3),
             a[:, :t].reshape(-1, 3), a[:, -t:].reshape(-1, 3)]
    rim = np.concatenate(sides)
    q = rim // 8                                          # gom mau gan giong, nhu background_color
    keys = q[:, 0] * 1024 + q[:, 1] * 32 + q[:, 2]
    values, counts = np.unique(keys, return_counts=True)
    bg = np.median(rim[keys == values[counts.argmax()]], axis=0)

    def share(px):
        return float((np.abs(px - bg).max(axis=1) <= FLAT_TOLERANCE).mean())
    if share(rim) < FLAT_MIN_SHARE or min(share(s) for s in sides) < FLAT_SIDE_MIN_SHARE:
        return None
    return tuple(int(round(v)) for v in bg)


def content_box(im: Image.Image, bg) -> tuple:
    """Hop (x0, y0, x1, y1) theo pixel cua anh GOC bao phan KHAC mau nen `bg`.

    Hinh paper thuong co le trang rong (Figure 1 MiniMax-H3: noi dung chi 73% be ngang) —
    phong theo ca tam thi le trang an mat cho cua noi dung."""
    import numpy as np
    im = im.convert("RGB")
    p = _probe(im)
    a = np.asarray(p, dtype=np.int16)
    diff = np.abs(a - np.array(bg[:3])).max(axis=2) > CONTENT_TOLERANCE
    rows = np.nonzero(diff.sum(axis=1) >= CONTENT_MIN_PIXELS)[0]
    cols = np.nonzero(diff.sum(axis=0) >= CONTENT_MIN_PIXELS)[0]
    if not len(rows) or not len(cols):
        return (0, 0, im.width, im.height)
    sx, sy = im.width / p.width, im.height / p.height
    # Noi ra MOT diem cua ban do moi phia: ban thu nho lam mat nua diem o mep noi dung.
    return (max(0, int((cols[0] - 1) * sx)), max(0, int((rows[0] - 1) * sy)),
            min(im.width, int(np.ceil((cols[-1] + 2) * sx))),
            min(im.height, int(np.ceil((rows[-1] + 2) * sy))))
