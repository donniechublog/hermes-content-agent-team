#!/usr/bin/env python3
"""LOW-286 (19/09/2026) — nền chữ slide thân/quote carousel chỉ là OVERLAY, chữ ~20% khung.

Ông Chủ, album dcgr "Lovable mua Sutro": *"text chỉ được chiếm khoảng 20% diện tích,
phần nền text đã nói từ rất lâu ko làm thô kệch như vậy, chỉ để như một lớp overlay
trên ảnh, giờ lại làm một đống dày cộm là sao"*. LOW-272 cho mọi ảnh có chi tiết dưới
chữ đi nền đặc LOW-215: mờ 44px từ "khoảng lặng" (cắt ngang mặt người) + phủ màu nền
91% → khối đen 33–47% khung. Slide quote còn neo nền ở đỉnh khung quote.

Chạy:  venv/bin/python tests/test_low286_text_overlay.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw  # noqa: E402

import carousel  # noqa: E402

TEXT_TOP = 1030
LOVABLE_QUOTE = ("Một khi ai cũng đưa được phần mềm lên chạy thật, độ tin cậy và niềm tin "
                 "phải khớp với trải nghiệm xây nó.")


def _busy(color=(150, 150, 150)):
    """Anh co chi tiet sac trai kin khung (nhu anh chup van phong / UI)."""
    W, H = carousel.W, carousel.H
    im = Image.new("RGBA", (W, H), (*color, 255))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 14):
        d.rectangle([x, 0, x + 6, H], fill=(240, 240, 240, 255))
    return im


def _row_energy(canvas, y):
    g = canvas.convert("L")
    return sum(abs(g.getpixel((x + 1, y)) - g.getpixel((x, y))) for x in range(0, canvas.width - 1)) / canvas.width


def _layer(cv, cluttered=False, top=TEXT_TOP):
    return carousel._layer_if_can(cv, cv.convert("RGB"), top, carousel.TEXT_BASE,
                                  image_cluttered=cluttered, max_share=carousel.SOLID_BG_MAX_SHARE)


def test_no_blur_band_above_text():
    """Khong con dai mo manh phia tren chu: anh tren overlay giu nguyen tung pixel."""
    carousel.set_background("dark")
    for cluttered in (False, True):
        cv = _busy()
        goc = cv.copy()
        top = _layer(cv, cluttered)
        assert top == TEXT_TOP - carousel.OVERLAY_LEAD, top
        for y in (300, 600, 800, top - 1):
            assert cv.getpixel((7, y)) == goc.getpixel((7, y)), (cluttered, y)


def test_overlay_not_solid_block():
    """Tai vung chu anh van hien qua overlay (khong phai mau nen dac)."""
    carousel.set_background("dark")
    for cluttered in (False, True):
        cv = Image.new("RGBA", (carousel.W, carousel.H), (220, 60, 30, 255))
        d = ImageDraw.Draw(cv)
        for x in range(0, carousel.W, 14):
            d.rectangle([x, 0, x + 6, carousel.H], fill=(240, 200, 40, 255))
        _layer(cv, cluttered)
        for y in (TEXT_TOP + 20, carousel.TEXT_BASE, carousel.H - 5):
            r, g, b = cv.getpixel((500, y))[:3]
            bg = carousel.BG
            assert r - bg[0] >= 25, (cluttered, y, (r, g, b))      # mau anh con lo qua


def test_dark_area_about_one_quarter_of_frame():
    """Phan bi toi >= 40% (tinh ca dai chuyen OVERLAY_LEAD) khong qua 30% khung: vung chu
    ~15-20% + chip ten kenh + dai chuyen. Ban LOW-272 bi bac: 33-47% gan nhu dac."""
    carousel.set_background("dark")
    cv = _busy()
    goc = cv.copy()
    _layer(cv, cluttered=True)
    toi = [y for y in range(carousel.H)
           if sum(cv.getpixel((500, y))[:3]) < 0.6 * sum(goc.getpixel((500, y))[:3])]
    assert toi and (carousel.H - min(toi)) / carousel.H <= 0.30, min(toi)


def test_text_still_legible_on_detail():
    """Van giu y LOW-272: chi tiet ngay duoi chu diu han di (chu khong nhoe)."""
    carousel.set_background("dark")
    cv = _busy()
    truoc = _row_energy(cv, TEXT_TOP + 40)
    _layer(cv)
    assert _row_energy(cv, TEXT_TOP + 40) < truoc * 0.25, (truoc, _row_energy(cv, TEXT_TOP + 40))


def test_smooth_image_untouched():
    """Anh tron du tuong phan: khong phu gi."""
    carousel.set_background("dark")
    cv = Image.new("RGBA", (carousel.W, carousel.H), (30, 35, 60, 255))
    assert _layer(cv) is None


def test_quote_text_at_most_20_percent():
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    _f, lines, buoc, _t, vua = carousel._fit_quote(probe, LOVABLE_QUOTE)
    assert vua and buoc * len(lines) <= carousel.Q_TEXT_MAX_H <= round(carousel.H * 0.2), (len(lines), buoc)


def test_quote_too_long_is_gated():
    dai = LOVABLE_QUOTE + " " + LOVABLE_QUOTE + " " + LOVABLE_QUOTE
    loi = carousel._gate_overflow([{"quote": dai, "attrib": "x"}])
    assert loi and "20%" in loi[0], loi
    assert not carousel._gate_overflow([{"quote": LOVABLE_QUOTE, "attrib": "x"}])


def test_quote_overlay_anchored_at_first_line(tmp=None):
    """Slide quote: phan anh tren dong chu dau - OVERLAY_LEAD giu nguyen (truoc day nen
    chu bat dau tu dinh khung quote, ~47% khung)."""
    import tempfile
    carousel.set_background("dark")
    with tempfile.TemporaryDirectory() as t:
        src = Path(t) / "a.png"
        _busy().convert("RGB").save(src)
        out = Path(t) / "q.png"
        top = carousel.build_body_quote(str(src), LOVABLE_QUOTE, "Lovable, thông báo thâu tóm",
                                        "dcgr.tech", str(out))
        assert top is not None and top >= carousel.H * 0.58, top


# ------------------------------------------------ cong do nen chu tren pixel that
def test_gate_passes_new_overlay_body_and_quote():
    import tempfile
    carousel.set_background("dark")
    with tempfile.TemporaryDirectory() as t:
        src = Path(t) / "a.png"
        _busy().convert("RGB").save(src)
        for cluttered in (False, True):
            bao = {}
            carousel.build_body(str(src), "Một đoạn chữ ngắn cho slide thân.", "dcgr.tech",
                                str(Path(t) / "b.png"), cluttered=cluttered, report=bao)
            assert bao and not carousel._gate_text_background("slide 2", bao), bao
            bao = {}
            carousel.build_body_quote(str(src), LOVABLE_QUOTE, "Lovable", "dcgr.tech",
                                      str(Path(t) / "q.png"), cluttered=cluttered, report=bao)
            assert bao and not carousel._gate_text_background("slide 3", bao), bao


def test_gate_blocks_old_solid_background():
    """Nen chu LOW-272/LOW-215 (mo 44px tu khoang lang + phu mau nen 91%) phai bi chan."""
    carousel.set_background("dark")
    cv = _busy()
    truoc = cv.copy()
    carousel._background_solid_below_text(cv, TEXT_TOP, carousel.SOLID_BG_MAX_SHARE)
    bao = carousel._text_bg_report(truoc, cv)
    loi = carousel._gate_text_background("slide 5", bao)
    assert loi and "overlay" in loi and bao["bg_opacity"] > carousel.TEXT_BG_MAX_OPACITY, bao


def test_gate_blocks_background_starting_too_high():
    """Nen chu keo tu gan nua khung (nhu slide quote cu neo o dinh khung) phai bi chan."""
    carousel.set_background("dark")
    cv = _busy()
    truoc = cv.copy()
    carousel._overlay_text(cv, 700, 0, 40)
    bao = carousel._text_bg_report(truoc, cv)
    assert bao["bg_share"] > carousel.TEXT_BG_MAX_SHARE, bao
    assert carousel._gate_text_background("slide 3", bao)


def test_gate_untouched_image_reports_zero():
    carousel.set_background("dark")
    cv = _busy()
    bao = carousel._text_bg_report(cv.copy(), cv)
    assert bao == {"bg_share": 0.0, "bg_opacity": 0.0}, bao
    assert not carousel._gate_text_background("slide 2", bao)


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
