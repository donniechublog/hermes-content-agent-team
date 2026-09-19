#!/usr/bin/env python3
"""LOW-272: slide than carousel khong duoc de chu de len chi tiet doc duoc cua anh.

Ong Chu 19/09/2026, hai slide Claude Cowork dcgr: "chu nhoe nhoet, khong biet
bao gio moi khac phuc". Do that: duoi chu con menu UI / chu in san (variance 52..63,
nguong 26) nhung anh KHONG duoc gan co `cluttered` nen di lop mo 14px + toi toi da
55%, lai bat dau ngay dong chu dau -> dong dau nam tren anh con sac. Tu nay, o
slide than (co max_share), do thay chi tiet duoi chu thi dung nen chu cua LOW-215.

Chay:  venv/bin/python tests/test_carousel_body_text_zone_detail.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

import carousel  # noqa: E402

TEXT_TOP = 1040


def _detailed_under_text():
    """Anh co chi tiet sac (soc sang/toi hep) tran xuong vung chu, nhu menu UI."""
    W, H = carousel.W, carousel.H
    im = Image.new("RGBA", (W, H), (70, 70, 70, 255))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 12):
        d.rectangle([x, 900, x + 5, H], fill=(245, 245, 245, 255))
    return im


def _smooth():
    W, H = carousel.W, carousel.H
    im = Image.new("RGBA", (W, H))
    px = im.load()
    for y in range(H):
        row = (20 + y // 30, 30, 80 + y // 20, 255)
        for x in range(W):
            px[x, y] = row
    return im


def _row_energy(canvas, y):
    g = canvas.convert("L")
    return sum(abs(g.getpixel((x + 1, y)) - g.getpixel((x, y))) for x in range(0, canvas.width - 1)) / canvas.width


def test_detail_under_first_text_line_is_cleared():
    """Dong chu dau (y ~ text_top + 10) phai nam tren nen da xoa het chi tiet."""
    carousel.set_background("dark")
    cv = _detailed_under_text()
    truoc = _row_energy(cv, TEXT_TOP + 10)
    assert truoc > 20, truoc
    carousel._layer_if_can(cv, cv.convert("RGB"), TEXT_TOP, carousel.TEXT_BASE,
                           max_share=carousel.SOLID_BG_MAX_SHARE)
    for y in (TEXT_TOP + 10, TEXT_TOP + 60, carousel.TEXT_BASE - 10):
        assert _row_energy(cv, y) < truoc * 0.1, (y, truoc, _row_energy(cv, y))


def test_body_still_within_solid_cap():
    """Nen chu van bi tran 30% khung (LOW-215): nua tren khung khong bi dong vao."""
    carousel.set_background("dark")
    cv = _detailed_under_text()
    touched = carousel._layer_if_can(cv, cv.convert("RGB"), TEXT_TOP, carousel.TEXT_BASE,
                                     max_share=carousel.SOLID_BG_MAX_SHARE)
    assert touched is not None
    assert touched >= carousel.H * 0.5, touched


def test_smooth_image_keeps_light_layer():
    """Anh tron khong co chi tiet de lo -> khong leo thang len nen chu."""
    carousel.set_background("dark")
    cv = _smooth()
    goc = cv.copy()
    touched = carousel._layer_if_can(cv, cv.convert("RGB"), TEXT_TOP, carousel.TEXT_BASE,
                                     max_share=carousel.SOLID_BG_MAX_SHARE)
    assert touched is None, touched
    # anh giu nguyen o vung ngay duoi chu (khong thanh mau BG dac)
    assert cv.getpixel((500, carousel.TEXT_BASE))[:3] != tuple(carousel.BG)
    assert abs(cv.getpixel((500, 200))[0] - goc.getpixel((500, 200))[0]) == 0


def test_cover_path_not_escalated():
    """Bia (khong truyen max_share) giu lop nhe nhu cu, khong leo thang."""
    carousel.set_background("dark")
    cv = _detailed_under_text()
    touched = carousel._layer_if_can(cv, cv.convert("RGB"), TEXT_TOP, carousel.H)
    assert touched is None, touched


if __name__ == "__main__":
    ok = 0
    ten = [n for n in dir() if n.startswith("test_")]
    for n in ten:
        try:
            globals()[n]()
            ok += 1
        except AssertionError as e:
            print(f"FAIL {n}: {e}")
    print(f"{ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
