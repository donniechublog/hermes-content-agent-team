#!/usr/bin/env python3
"""B24 (audit LOW-430, 30/09/2026): ba ca bien khi dung hinh, chung minh bang anh tong hop.

(a) `logo_card.build_card`: hop vision suy bien (rong/cao 0, dao nguoc) -> ZeroDivisionError /
    ValueError. Nay roi ve lay ca tam nhu khi khong co hop.
(b) `card._densest_center`: anh cuc mong (3000x1) -> ValueError o crop. Nay tra tam giua.
(c) `carousel._layer_if_can`: vung chu RONG (slide `"text": " "`) do `_measure_region_text`
    tra 255 = "qua sang" -> overlay dam nhat phu len slide KHONG chu. Nay khong overlay.
    CHI chan ca bien: slide co chu van di dung duong cu (test_low286_text_overlay.py).

Chay:  venv/bin/python tests/test_b24_render_edge_cases.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageChops, ImageDraw  # noqa: E402

import card                                                  # noqa: E402
import carousel                                              # noqa: E402
import logo_card                                             # noqa: E402


def _logo_file(d):
    p = Path(d) / "logo.png"
    im = Image.new("RGB", (1000, 800), (250, 250, 250))
    ImageDraw.Draw(im).rectangle([300, 300, 700, 500], fill=(20, 20, 20))
    im.save(p)
    return p


def test_logo_card_degenerate_box_falls_back_to_whole_image():
    with tempfile.TemporaryDirectory() as d:
        p = _logo_file(d)
        whole, bg = logo_card.build_card(p, None, 1080, 1350)
        for box in ((0.5, 0.5, 0.5, 0.5), (0.4, 0.4, 0.4, 0.6), (0.4, 0.4, 0.6, 0.4),
                    (0.6, 0.4, 0.4, 0.6), (0.7, 0.7, 0.2, 0.2)):
            khung, bg2 = logo_card.build_card(p, box, 1080, 1350)
            assert khung.size == (1080, 1350) and bg2 == bg, box
            assert ImageChops.difference(khung, whole).getbbox() is None, box   # = khong hop


def test_logo_card_normal_box_unchanged():
    with tempfile.TemporaryDirectory() as d:
        p = _logo_file(d)
        khung, _ = logo_card.build_card(p, (0.3, 0.375, 0.7, 0.625), 1080, 1350)
        whole, _ = logo_card.build_card(p, None, 1080, 1350)
        assert ImageChops.difference(khung, whole).getbbox() is not None   # hop that van cat sat


def test_densest_center_hairline_images():
    for size in ((3000, 1), (3000, 3), (200, 2)):
        assert card._densest_center(Image.new("RGB", size, (9, 9, 9)), 0.5, 0.5) == (0.5, 0.5), size


def test_densest_center_normal_image_still_measures():
    im = Image.new("RGB", (1200, 800), (30, 30, 30))
    ImageDraw.Draw(im).rectangle([800, 100, 1000, 300], fill=(250, 250, 250))
    cx, cy = card._densest_center(im, 0.5, 0.5)
    assert cx > 0.55 and cy < 0.5, (cx, cy)         # nghieng ve o sang, khong phai tam giua mac dinh


def _busy():
    im = Image.new("RGBA", (carousel.W, carousel.H), (150, 150, 150, 255))
    d = ImageDraw.Draw(im)
    for x in range(0, carousel.W, 14):
        d.rectangle([x, 0, x + 6, carousel.H], fill=(240, 240, 240, 255))
    return im


def test_empty_text_region_gets_no_overlay():
    for theme in ("dark", "light"):
        carousel.set_background(theme)
        for cluttered in (False, True):
            for top, bottom in ((carousel.TEXT_BASE, carousel.TEXT_BASE), (900, 900), (900, 800)):
                cv = _busy()
                goc = cv.copy()
                r = carousel._layer_if_can(cv, cv.convert("RGB"), top, bottom, image_cluttered=cluttered,
                                           overlay_only=True)
                assert r is None and ImageChops.difference(cv, goc).getbbox() is None, (theme, cluttered, top)


def test_build_body_blank_text_slide_has_no_overlay():
    """Duong that: `"text": " "` lot `_standard_text` (chuoi khong rong) -> khong chu -> khong overlay."""
    carousel.set_background("dark")
    with tempfile.TemporaryDirectory() as d:
        src = Path(d) / "s.png"
        _busy().convert("RGB").save(src)
        rep = {}
        carousel.build_body(src, " ", "@x", Path(d) / "o.png", report=rep)
        assert rep["bg_opacity"] == 0.0 and rep["bg_share"] == 0.0, rep
        rep2 = {}
        carousel.build_body(src, "Mot doan van that su co chu.", "@x", Path(d) / "o2.png", report=rep2)
        assert rep2["bg_opacity"] > 0.3, rep2          # slide co chu van co overlay


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
