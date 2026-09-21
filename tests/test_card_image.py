#!/usr/bin/env python3
"""The anh (`card.py`) — lop anh dung chung va bo cuc kieu `tran`.

Audit 06/09/2026 bat mot loi ma khong cong nao chan: kieu `tran`, khi anh thap
hon the, lay MAU NEN DAC cua bo nhan dien lam nen cho phan thieu. Do dung la
"hai vung rieng biet" ma IMAGE_RULES muc 7 cam, va chinh spec cua kieu tran cung
da ghi la phai dung nen mo — ma khong ai doi chieu spec voi ma. Ong Chu chot
07/09/2026: bo nen dac, chu dat thang len anh voi mau tuong phan, bao quanh
bang mot khung chu nhat net.

Cac test o day soi CHINH TAM ANH ra chu khong soi ma nguon: mot mang mau dac
la mot dai pixel giong het nhau, dem duoc.

Chay:  venv/bin/python tests/test_card_image.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw, ImageFilter  # noqa: E402


def _image_real(w, h, sang=False):
    """Mot tam anh co van — anh phang bi cong `check_blank_image` chan dung.

    `sang=True`: anh NEN TRANG co van, dung dang mot bang benchmark hay mot
    trang web chup lai — ca IMAGE_RULES lan cac su co da ghi deu noi day la loai
    anh hay gap nhat, va la loai lam mat chu trang."""
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h
        if sang:
            d.line([(0, y), (w, y)], fill=(int(232 + 18 * t), int(234 + 16 * t),
                                           int(238 + 14 * t)))
        else:
            d.line([(0, y), (w, y)], fill=(int(28 + 40 * t), int(34 + 32 * t),
                                           int(46 + 26 * t)))
    b, dai = 0, (150, 226) if sang else (30, 230)
    for x in range(0, w, 37):
        for y in range(0, h, 41):
            b = (b * 1103515245 + 12345) % 2147483648
            r = 12 + b % 70
            d.ellipse([x, y, x + r, y + r],
                      fill=tuple(dai[0] + (b >> k) % (dai[1] - dai[0])
                                 for k in (7, 11, 15)))
    return im.filter(ImageFilter.GaussianBlur(1.2))


def _line_flat(im, tu, den) -> int:
    """So HANG chi co DUNG MOT mau trong khoang [tu, den).

    Mot mang nen dac cho ra hang phang; anh lam mo thi khong hang nao phang."""
    px = im.convert("RGB")
    n = 0
    for y in range(tu, den):
        # getcolors tra ve None khi qua `maxcolors` mau — tuc hang do khong phang.
        mau = px.crop((0, y, px.width, y + 1)).getcolors(maxcolors=4)
        if mau and len(mau) == 1:
            n += 1
    return n


# --------------------------------------------------- lop anh dung chung
def test_image_low_no_for_again_network_background_solid():
    """Loi goc: anh 16:9 tren khung 4:5 -> nat_h 675/1500, hon MOT NUA the la
    mau nen dac. Nay phan thieu la chinh tam anh lam mo — khong hang nao phang."""
    import card
    card.set_brand("donniechublog")
    canvas = Image.new("RGBA", (card.W, 1500), (*card.BG, 255))
    card._layer_image(canvas, _image_real(1920, 1080), 1500)
    phang = _line_flat(canvas, 700, 1500)
    assert phang == 0, f"{phang} hang mau dac o nua duoi the"


def test_image_low_no_for_again_path_seam_landscape():
    """Mep duoi cua lop sac phai TAN vao lop nen mo (smoothstep), khong duoc la
    mot buoc nhay. Do that truoc khi sua: tut 159 do sang trong MOT hang."""
    import card
    card.set_brand("donniechublog")
    canvas = Image.new("RGBA", (card.W, 1500), (*card.BG, 255))
    nat_h = card._layer_image(canvas, _image_real(1800, 1200), 1500)
    xam = canvas.convert("L")
    def _sang(y):
        return sum(xam.getpixel((x, y)) for x in range(0, card.W, 8)) / (card.W // 8)
    nhay = max(abs(_sang(y + 1) - _sang(y)) for y in range(nat_h - 8, nat_h + 8))
    assert nhay < 12, f"buoc nhay {nhay:.1f} do sang tai mep anh (y={nat_h})"


def test_always_keep_full_be_landscape_no_crop_two_edge():
    """Uu tien so mot cua ca hai kieu the (Ong Chu bat loi 03/09/2026:
    cover-crop lam mat tieu de cua slide/bang nguon). Dat mot vach mau o SAT
    hai canh anh nguon roi doi chung phai con tren the.

    Thu ca hai nhanh: anh CAO hon the (cat doc) va anh NGANG hon the (lop sac
    thap hon the) — nhanh nao lo dung `_fit_cover` cho lop sac la mat vach."""
    import card
    card.set_brand("donniechublog")
    for w, h in ((1200, 2000), (1920, 1080)):
        src = _image_real(w, h)
        d = ImageDraw.Draw(src)
        d.rectangle([0, 0, 14, h], fill=(255, 0, 0))
        d.rectangle([w - 15, 0, w, h], fill=(0, 255, 0))
        canvas = Image.new("RGBA", (card.W, 1500), (*card.BG, 255))
        nat_h = card._layer_image(canvas, src, 1500)
        assert nat_h == round(card.W * h / w), nat_h
        giua = min(nat_h, 1500) // 2
        rgb = canvas.convert("RGB")
        trai, phai = rgb.getpixel((3, giua)), rgb.getpixel((card.W - 4, giua))
        assert trai[0] > 150 and trai[1] < 90, f"mat vach TRAI ({w}x{h}): {trai}"
        assert phai[1] > 150 and phai[0] < 90, f"mat vach PHAI ({w}x{h}): {phai}"


# --------------------------------------------------- khung do sang
def test_within_card_force_frame_measure_lie_within_image():
    """`canvas.crop` ra ngoai bien tra ve vung DEN (PIL dem den vao), tuc mot
    dai chu sat day the se do ra 'nen toi' va chon chu TRANG du day the sang."""
    import card
    canvas = Image.new("RGBA", (100, 80), (255, 255, 255, 255))
    assert card._within_card(canvas, (-20, -5, 500, 900)) == (0, 0, 100, 80)
    x0, y0, x1, y1 = card._within_card(canvas, (50, 79, 50, 79))
    assert x1 > x0 and y1 > y0, "khung do rong -> ImageStat nem loi"


def test_measure_bright_close_bottom_card_no_got_border_black_drag_down():
    import card
    card.set_brand("donniechublog")
    canvas = Image.new("RGBA", (card.W, 400), (250, 250, 250, 255))
    sang = card._bright_region(canvas, card._within_card(canvas, (0, 380, card.W, 460)))
    assert sang > 200, f"day the sang ma do ra {sang:.0f}"


# --------------------------------------------------- mau ten hang tren nen sang
def test_name_rank_on_background_bright_drag_about_side_dark():
    """CYAN cua dcgr (gan trang) tren nen trang cho CR 1.04 — mat chu. Da sua
    cho net khung quote 06/09/2026; kieu tran dat chu thang len anh nen dai chu
    co the sang, phai sua cung mot kieu."""
    import card
    card.set_brand("donniechublog")
    im = Image.new("RGB", (600, 90), (250, 250, 250))
    d = ImageDraw.Draw(im)
    f = card._f(card.F_HERO, 60, weight=card.HERO_WEIGHT)
    card._about_line(d, 10, 5, "NVIDIA", f, card.BG, "cyan", None, nen_sang=True)
    tren_sang = min(sum(im.getpixel((x, y))) for x in range(600) for y in range(90))
    im2 = Image.new("RGB", (600, 90), (250, 250, 250))
    card._about_line(ImageDraw.Draw(im2), 10, 5, "NVIDIA", f, card.BG, "cyan", None)
    tren_toi = min(sum(im2.getpixel((x, y))) for x in range(600) for y in range(90))
    assert tren_sang < tren_toi, (
        f"nen_sang khong keo mau ten hang ve phia toi ({tren_sang} vs {tren_toi})")


# --------------------------------------------------- the tran dung du
def _use_card(tmp, ten_anh, title, **k):
    import card
    src = Path(tmp) / "source.png"
    _image_real(*ten_anh, sang=k.pop("sang", False)).save(src)
    out = Path(tmp) / "the.png"
    card.build(str(src), title, str(out), kieu="full_bleed", ratio="4:5",
               bo_qua_anh=True, **k)
    return Image.open(out).convert("RGB")


def test_card_ceiling_image_above_frame_clean_color_below():
    """LOW-343 (Ong Chu 21/09/2026: *"lam no sach tron di, de lai nhung lom dom nay rat thieu
    chuyen nghiep"*) DAO luat cu "day the phai la anh": phia TREN vung chu van la anh (khong hang
    nao phang), tu khoang lang tren khung xuong day la MOT mau tron — khong con vet mo lom dom."""
    import card
    with tempfile.TemporaryDirectory() as t:
        im = _use_card(t, (1920, 1080), "Nvidia mở kho mô hình Nemotron")
        tren = 1500 - int(1500 * card.CEILING_TEXTBOX) - card.CLEAN_QUIET_SEARCH - 10
        assert _line_flat(im, 300, tren) == 0, "phia tren vung chu phai con la anh"
        assert _line_flat(im, 1480, 1500) == 20, "day the (duoi khung) phai la mau tron"


def test_card_ceiling_has_frame_text_most_net():
    """Ong Chu chot 07/09/2026: co khung (LOW-342: vung chu 30% the, khung tu ~70%). Net doc cua khung la mot cot pixel
    gan nhu khong doi mau — anh (ke ca da lam mo) thi khong bao gio nhu vay."""
    import card
    with tempfile.TemporaryDirectory() as t:
        im = _use_card(t, (1920, 1080), "Nvidia mở kho mô hình Nemotron")
        x = card.CEILING_FRAME_X + card.CEILING_FRAME_LW // 2
        cot = [im.getpixel((x, y)) for y in range(int(1500 * 0.72), int(1500 * 0.88))]
        lech = max(max(abs(p[i] - cot[0][i]) for i in range(3)) for p in cot)
        assert lech < 24, f"khong thay net doc cua khung o x={x} (lech {lech})"
        # ...va ngay ben trong khung thi KHONG phai net (khong phai ca vung mot mau)
        trong = [im.getpixel((x + 60, y)) for y in range(int(1500 * 0.72), int(1500 * 0.88))]
        assert max(max(abs(p[i] - trong[0][i]) for i in range(3))
                   for p in trong) > 24, "ben trong khung cung phang: van la mang dac"


def test_card_ceiling_bright_bottom_then_text_change_bright_color_dark():
    """Bo man toi roi thi chu phai tu doi mau. Anh day SANG ma chu van trang la
    mat chu — cai gia cua viec bo man toi neu khong do do sang."""
    import card
    card.set_brand("donniechublog")
    with tempfile.TemporaryDirectory() as t:
        im = _use_card(t, (1800, 1200), "Nvidia mở kho mô hình Nemotron", sang=True)
        xam = im.convert("L")
        dai = [(x, y) for y in range(1000, 1330) for x in range(120, 1080)]
        toi = sum(1 for xy in dai if xam.getpixel(xy) < 60)
        rat_sang = sum(1 for xy in dai if xam.getpixel(xy) > 200)
        assert toi > 12000, f"chi {toi} pixel chu TOI tren nen sang — chu chua doi mau"
        assert toi > rat_sang / 4, f"toi {toi} vs rat sang {rat_sang}"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
