#!/usr/bin/env python3
"""LOW-295 (20/09/2026) — logo hãng dựng thành SLIDE LOGO thay vì bị cổng ảnh trống chặn.

Ông Chủ, sau khi xem hai bản dựng thử bằng logo Google/OpenAI/Anthropic thật:
*"Chỉ cần phóng to logo cho hiển thị hết 90% chiều rộng. Phần còn dư lại, đặt text màu
tương phản lên là được, đừng có thêm nền text, rất là phèn."*

Chạy:  venv/bin/python tests/test_low295_logo_card.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw  # noqa: E402

import carousel  # noqa: E402
import logo_card  # noqa: E402
import role  # noqa: E402

BOX = [0.1, 0.42, 0.9, 0.58]          # logo chu: dai ngang det, nam giua


def _logo_anh(nen=(245, 245, 245), muc=(20, 20, 24), w=1200, h=1500):
    im = Image.new("RGB", (w, h), nen)
    d = ImageDraw.Draw(im)
    d.rectangle([int(BOX[0] * w), int(BOX[1] * h), int(BOX[2] * w), int(BOX[3] * h)], fill=muc)
    return im


def test_card_logo_takes_90_percent_width():
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "logo.png"
        _logo_anh().save(p)
        khung, bg = logo_card.build_card(p, BOX, carousel.W, carousel.H)
        assert khung.size == (carousel.W, carousel.H)
        assert bg == (245, 245, 245), bg
        # do be ngang thuc cua phan logo tren khung
        g = khung.convert("L")
        hang = [x for x in range(carousel.W) if g.getpixel((x, int(carousel.H * 0.34))) < 100]
        rong = (max(hang) - min(hang) + 1) / carousel.W
        assert 0.88 <= rong <= 0.93, rong


def test_text_color_contrasts_with_background():
    assert logo_card.text_color((245, 245, 245))[0] < 40
    assert logo_card.text_color((10, 10, 12))[0] > 200


def test_logo_card_not_counted_as_empty():
    a = {"empty_share": 0.85, "subject_kind": "logo", "subject_box": BOX, "logo_card": True}
    assert role.blocked_empty(a, "dre") is False
    assert role.blocked_empty(dict(a, logo_card=False), "dre") is True


def test_slide_has_no_text_background_layer():
    """Slide logo KHONG duoc phu overlay: pixel nen quanh chu giu nguyen mau nen."""
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "logo.png"
        _logo_anh().save(p)
        khung, bg = logo_card.build_card(p, BOX, carousel.W, carousel.H)
        card = Path(t) / "card.png"
        khung.save(card)
        out = Path(t) / "slide.png"
        carousel.set_background("dark")
        bao = {}
        touched = carousel.build_body(str(card), "Một đoạn chữ ngắn cho slide logo.",
                                      "dcgr.tech", str(out), report=bao, logo_bg=list(bg))
        assert touched is None, touched
        assert bao.get("bg_opacity", 0) == 0 and bao.get("bg_share", 0) == 0, bao
        sl = Image.open(out).convert("RGB")
        # ngay tren dong chu dau (vung nen) van la mau nen goc
        assert sl.getpixel((carousel.W - 30, carousel.TEXT_BASE - 40)) == bg, \
            sl.getpixel((carousel.W - 30, carousel.TEXT_BASE - 40))


def test_dark_logo_background_gets_white_text():
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "logo.png"
        _logo_anh(nen=(8, 8, 10), muc=(250, 250, 250)).save(p)
        khung, bg = logo_card.build_card(p, BOX, carousel.W, carousel.H)
        assert logo_card.text_color(bg) == (255, 255, 255), bg


def test_is_logo_image():
    assert logo_card.is_logo_image({"subject_kind": "logo", "subject_box": BOX, "empty_share": 0.85})
    assert not logo_card.is_logo_image({"subject_kind": "person", "subject_box": BOX, "empty_share": 0.85})
    assert not logo_card.is_logo_image({"subject_kind": "logo", "empty_share": 0.85})


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
