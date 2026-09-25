#!/usr/bin/env python3
"""LOW-414 — the logo hang (kind chart) khong phai chart trong cong nop cua Dre.

The logo hang (`image_brand.card_logo`, `role.is_brand_logo_card`) mang kind chart vi
phang. `role.can_be_hero` va `ethan_submit` da coi no la anh hero dung MOT MINH tu
LOW-337, rieng `dre_submit._resolve_single` thi dung no o nhanh chart: lam bia bi chan
"là CHART/screenshot" (28 lan 13–24/09 tren may chu), lam slide than thi dung nhu chart
thay vi slide logo LOW-295. Ban va nong tren may chu tu 24/09 07:05 sua dung dong do;
Ong Chu 25/09: "logo hang tren nen tron ko thanh van de".

Chay:  venv/bin/python tests/test_low414_dre_brand_logo_card.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image                                          # noqa: E402

from tam import so_tam                                          # noqa: E402
from test_spec_dre import _anh, _bia, _chay, _co, _du_slide, _m, _spec  # noqa: E402
import state_paths                                             # noqa: E402

BRAND_CARD = {"logo_card": True, "brand_match": {"kind": "logo", "company": "Nvidia"}}


def _images(wd, first):
    """A1 theo `first` (kind chart + khoa them), A2..A5 la anh chup doc hop le."""
    return ([_anh(wd, "A1", 1000, 1250, loai="chart", **first)]
            + [_anh(wd, f"A{i}", 1000, 1250) for i in range(2, 6)])


def test_brand_logo_card_is_a_valid_cover_and_becomes_a_logo_slide():
    """Fail tren ma cu: "bìa: A1 là CHART/screenshot, hook đè lên là mất nửa dưới"."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        spec, m = _spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"])), _m(wd, _images(wd, BRAND_CARD))
        ra, loi, _warn, _used = _chay(spec, m, wd)
        assert loi == [], loi
        assert ra["cover"]["image"].endswith("A1" + state_paths.LOGO_SUFFIX), ra["cover"]
        assert ra["cover"].get("logo_bg"), "bia phai la slide logo LOW-295 (co mau nen logo)"


def test_brand_logo_card_in_a_body_slide_is_a_logo_slide_not_a_chart():
    """Fail tren ma cu: slide than danh dau `chart` (anh nguyen be ngang + nen chu dac)."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        spec, m = _spec(_bia("A2"), _du_slide(["A1", "A3", "A4", "A5"])), _m(wd, _images(wd, BRAND_CARD))
        ra, loi, _warn, _used = _chay(spec, m, wd)
        assert loi == [], loi
        first = ra["slides"][0]
        assert "chart" not in first and first.get("logo_bg"), first


def test_plain_chart_still_cannot_be_the_cover():
    """Mien tru chi cho the logo hang: chart thuong van khong lam bia (luat cu giu nguyen).
    Nen CHUYEN MAU nhu test_spec_dre: chart nen phang da co duong rieng (LOW-341)."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        images = _images(wd, {})
        Image.linear_gradient("L").resize((1000, 1250)).convert("RGB").save(images[0]["original_path"])
        spec, m = _spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"])), _m(wd, images)
        _ra, loi, _warn, _used = _chay(spec, m, wd)
        assert _co(loi, "bìa: A1 là CHART/screenshot"), loi


def test_logo_card_without_a_brand_logo_match_is_still_a_chart():
    """`logo_card` ma `brand_match` khong phai logo (vd anh chup bien hieu) khong duoc
    mien — do 23/09: phan lon co `logo_card` la anh chup logo nho, dung loai cong chan."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sign = {"logo_card": True, "brand_match": {"kind": "photo", "company": "Nvidia"}}
        spec, m = _spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"])), _m(wd, _images(wd, sign))
        _ra, loi, _warn, _used = _chay(spec, m, wd)
        assert _co(loi, "bìa: A1 là CHART/screenshot"), loi


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
