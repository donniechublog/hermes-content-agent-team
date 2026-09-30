#!/usr/bin/env python3
"""LOW-444: the quote/ceiling khong duoc co DAI DEN giua dai mau keo dai va anh.

`card._layer_image`: anh thap hon the (nat_h <= H) co dinh phang thi ha xuong vung an
toan 142px (LOW-364) va keo dai mau dinh len tren. Nhung anh trong dai (H-142, H]
(ti le 0,80-0,88 tren the 4:5: le trang cua bang, header app, san pham tren nen trang)
thi ha het 142px la tran khung -> nhanh cat lay `top = (nat_h - H)//2` AM -> PIL dem
DEN. Do tren the ceiling that: 30 hang den y=142..171. Khong cong pixel nao bat.

Cong do o day: khong hang nao TOAN DEN tren lop anh, o moi nat_h trong dai do, ca hai
ti le 4:5 va 3:4, ca ham lop anh lan hai kieu the dung end-to-end.

Chay:  venv/bin/python tests/test_low444_card_black_band.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from PIL import Image                                           # noqa: E402
import card                                                     # noqa: E402
import safe_zone                                                # noqa: E402

NEN = (40, 40, 40)          # nen canvas KHAC den, de "hang toan den" chi co the la PIL dem


def _image_flat_top(w, h, dinh=40):
    """Anh 'chup san pham': nhieu chi tiet + dai trang phang tren dinh."""
    import random
    rng = random.Random(2)
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(0, w, 4):
            c = (rng.randrange(40, 220), rng.randrange(40, 220), rng.randrange(40, 220))
            for dx in range(4):
                if x + dx < w:
                    px[x + dx, y] = c if y >= dinh else (255, 255, 255)
    return im


def _black_rows(im):
    """Cac hang ma MOI pixel deu (0,0,0)."""
    g = im.convert("RGB")
    w, h = g.size
    ra = []
    for y in range(h):
        row = g.crop((0, y, w, y + 1)).getcolors(2)
        if row and len(row) == 1 and row[0][1] == (0, 0, 0):
            ra.append(y)
    return ra


def _layer(img, ratio):
    H = card.RATIOS[ratio]
    canvas = Image.new("RGB", (card.W, H), NEN)
    nat_h = card._layer_image(canvas, img, H)
    return canvas, H, nat_h


def test_khong_hang_den_trong_dai_nat_h_tran_khung():
    for ratio in ("4:5", "3:4"):
        H = card.RATIOS[ratio]
        top = safe_zone.top(card.W, H)
        for nat_h in (H - top + 1, H - top + 30, H - 100, H - 1, H):
            img = _image_flat_top(1200, nat_h)
            canvas, _, got = _layer(img, ratio)
            assert got == nat_h, (ratio, nat_h, got)
            den = _black_rows(canvas)
            assert not den, (ratio, nat_h, den[:3], len(den))
            # anh ha VUA DU: dinh anh (dai trang) ngay duoi dai mau keo dai, day anh cham day the
            shift = H - nat_h
            assert canvas.getpixel((600, shift)) == (255, 255, 255), (ratio, nat_h, canvas.getpixel((600, shift)))
            assert canvas.getpixel((600, H - 1)) != NEN, (ratio, nat_h)


def test_anh_du_thap_van_ha_het_142px_nhu_cu():
    """nat_h <= H - 142: hanh vi LOW-364 khong doi — ha het, dai tren la mau dinh keo dai."""
    for ratio in ("4:5", "3:4"):
        H = card.RATIOS[ratio]
        top = safe_zone.top(card.W, H)
        canvas, _, _ = _layer(_image_flat_top(1200, H - top - 200), ratio)
        assert canvas.getpixel((600, top - 1)) == (255, 255, 255), ratio      # dai keo dai = trang
        assert canvas.getpixel((600, top)) == (255, 255, 255), ratio          # dinh anh
        assert canvas.getpixel((600, top + 60)) != (255, 255, 255), ratio     # than anh
        assert not _black_rows(canvas), ratio


def test_anh_cao_hon_the_van_cat_giua_khong_ha():
    H = card.RATIOS["4:5"]
    canvas, _, nat_h = _layer(_image_flat_top(1200, H + 400), "4:5")
    assert nat_h == H + 400
    # cat giua: dinh trang (40px) da bi cat mat -> hang 0 khong con la trang
    assert canvas.getpixel((600, 0)) != (255, 255, 255)
    assert not _black_rows(canvas)


def test_anh_chup_trang_van_ha_het_va_giu_dinh():
    """top_anchor: giu tit trang, cat day — khong doi (LOW-336)."""
    H = card.RATIOS["4:5"]
    top = safe_zone.top(card.W, H)
    canvas = Image.new("RGB", (card.W, H), NEN)
    card._layer_image(canvas, _image_flat_top(1200, H - 60), H, top_anchor=True)
    assert canvas.getpixel((600, top)) == (255, 255, 255)
    assert not _black_rows(canvas)


def test_hai_kieu_the_that_khong_hang_den():
    b = card.set_brand("donniechublog")
    with tempfile.TemporaryDirectory() as s:
        tmp = Path(s)
        src = tmp / "src.png"
        _image_flat_top(1200, 1440).save(src)
        q = card._render_quote(str(src), "Một câu trích dẫn thử nghiệm đủ dài để xuống hai dòng.",
                               "via thử nghiệm", str(tmp / "quote.png"), b["handle"], "4:5")
        c = card._render_ceiling(str(src), "Tiêu đề thử nghiệm cho thẻ tràn", str(tmp / "ceiling.png"),
                                 b["handle"], "4:5", "KICKER", b)
        for out in (q, c):
            den = _black_rows(Image.open(out))
            assert not den, (out, den[:3], len(den))


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
