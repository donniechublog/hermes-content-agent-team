#!/usr/bin/env python3
"""LOW-215: nen chu cua anh ROI o slide than carousel khong duoc thanh mot khoi
den lon.

Ong Chu 17/09/2026, hai slide Claude Cowork: "phan nen chu qua lon va tho kech,
ko theo tieu chi". Do that: khoang lang gan nhat phia tren chu nam o MEP NOI
hai anh ghep (y=678) -> nen den tron phu 50% khung, anh duoi (A29) ro 0/608px.

Chay:  venv/bin/python tests/test_carousel_solid_bg_cap.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

import card  # noqa: E402
import carousel  # noqa: E402


def _stacked_like_claude_slide():
    """Anh tren 0..606 (chi tiet anh chup), mep noi phang 607..690 (khoang
    lang), anh duoi co chu in san 700..980 — dung hinh dang A25+A29."""
    W, H = carousel.W, carousel.H
    im = Image.new("RGBA", (W, H), (70, 70, 70, 255))
    d = ImageDraw.Draw(im)
    for x in range(0, W, 40):
        d.rectangle([x, 0, x + 19, 606], fill=(110, 110, 110, 255))
    for x in range(0, W, 8):
        d.rectangle([x, 700, x + 3, 980], fill=(250, 250, 250, 255))
    return im


def _near_bg(canvas, y, tol=30):
    bg = carousel.BG
    return all(abs(canvas.getpixel((x, y))[c] - bg[c]) <= tol
               for x in (0, 301, 777, canvas.width - 1) for c in range(3))


def _row_energy(canvas, y):
    g = canvas.convert("L")
    return sum(abs(g.getpixel((x + 1, y)) - g.getpixel((x, y))) for x in range(0, canvas.width - 1)) / canvas.width


def test_body_dark_background_capped_at_30_percent():
    carousel.set_background("toi")
    cv = _stacked_like_claude_slide()
    carousel._layer_if_can(cv, cv.convert("RGB"), 1033, carousel.H, image_cluttered=True,
                           max_share=carousel.SOLID_BG_MAX_SHARE)
    cap = carousel.H - int(carousel.H * carousel.SOLID_BG_MAX_SHARE)
    dark_rows = [y for y in range(carousel.H) if _near_bg(cv, y)]
    assert dark_rows, "phai co nen toi duoi chu"
    assert min(dark_rows) >= cap - 2, (min(dark_rows), cap)
    assert (carousel.H - min(dark_rows)) / carousel.H <= carousel.SOLID_BG_MAX_SHARE + 0.01
    for y in (1040, 1200, carousel.H - 1):
        assert _near_bg(cv, y), (y, cv.getpixel((0, y)))


def test_body_printed_text_above_cap_still_dissolved():
    """Chu in san nam tren tran toi (700..940) van phai tan ra (y LOW-47) —
    bang lam mo, khong phai bang khoi den."""
    carousel.set_background("toi")
    cv = _stacked_like_claude_slide()
    truoc = _row_energy(cv, 800)
    carousel._layer_if_can(cv, cv.convert("RGB"), 1033, carousel.H, image_cluttered=True,
                           max_share=carousel.SOLID_BG_MAX_SHARE)
    assert _row_energy(cv, 800) < truoc * 0.1, (truoc, _row_energy(cv, 800))
    assert not _near_bg(cv, 800, tol=12), "vung tren tran khong duoc thanh den tron"


def test_body_dark_background_not_flat_black():
    """Luat 04/09: nen khong bao gio la den tron — phan toi van mang mau anh."""
    carousel.set_background("toi")
    W, H = carousel.W, carousel.H
    cv = Image.new("RGBA", (W, H), (200, 60, 30, 255))
    carousel._layer_if_can(cv, cv.convert("RGB"), 1033, H, image_cluttered=True,
                           max_share=carousel.SOLID_BG_MAX_SHARE)
    assert cv.getpixel((500, H - 5))[:3] != tuple(carousel.BG), cv.getpixel((500, H - 5))


def test_cover_path_keeps_old_behaviour():
    """Bia (khong truyen max_share) giu nguyen: nen dac mau BG tu khoang lang."""
    carousel.set_background("toi")
    cv = _stacked_like_claude_slide()
    carousel._layer_if_can(cv, cv.convert("RGB"), 1033, carousel.H, image_cluttered=True)
    dac, _top = card._timestamp_background_solid(_stacked_like_claude_slide(), 1033 - carousel.CLUTTERED_BG_ODD,
                                                 carousel.CLUTTERED_BG_SPREAD)
    assert dac < 945
    assert all(cv.getpixel((x, dac + 5))[:3] == tuple(carousel.BG) for x in (0, 500, 1079))


def test_gate_blocks_stack_last_image_hidden():
    """A25+A29 cu: anh duoi 607..1215, nen dong vao tu 541 -> ro 0/608."""
    loi = carousel._gate_stack_last_hidden("slide 2", {"_stack_last": (607, 608)}, 541)
    assert "0/608" in loi, loi


def test_gate_allows_stack_last_image_mostly_visible():
    assert carousel._gate_stack_last_hidden("slide 2", {"_stack_last": (607, 608)}, 900) == ""
    assert carousel._gate_stack_last_hidden("slide 2", {"_stack_last": (607, 608)}, None) == ""
    assert carousel._gate_stack_last_hidden("slide 2", {}, 541) == ""


def test_stack_records_last_image_geometry(tmp=None):
    import tempfile
    with tempfile.TemporaryDirectory() as d:
        a, b = Path(d) / "a.png", Path(d) / "b.png"
        Image.new("RGB", (1782, 1002), (200, 200, 200)).save(a)
        Image.new("RGB", (1920, 1080), (30, 30, 30)).save(b)
        muc = {"images": [str(a), str(b)]}
        carousel._stack_if_can(muc, "slide 2", str(Path(d) / "s"))
        y0, h = muc["_stack_last"]
        assert abs(y0 - 607) <= 2 and abs(h - 608) <= 2, muc["_stack_last"]


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
