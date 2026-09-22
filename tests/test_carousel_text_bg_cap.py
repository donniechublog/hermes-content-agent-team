#!/usr/bin/env python3
"""Nen chu cua anh CLUTTERED trong carousel: CHI overlay, co tran dien tich — than VA bia.

Lich su mot luat, ba lan sua:
- LOW-47  (13/09/2026): anh roi buoc phai dung thi dat NEN DAC duoi chu ("lop nen cua
  text phai lam cho nghiem chinh").
- LOW-215 (17/09/2026): nen den tron phu 50% khung -> chan tran 30% o slide than.
- LOW-286 (19/09/2026): bo han nen dac o slide than, chi con mot overlay gradient.
- LOW-330 (20/09/2026, Ong Chu xem bia dcgr "Anthropic tu dat thuoc do": *"dung de cho
  nen dac, trong rat thieu chuyen nghiep"*): BIA — duong cuoi cung con nen dac — cung ve
  overlay. Tu day khong mot duong nao trong carousel sinh ra mang mau dac.

Chay:  venv/bin/python tests/test_carousel_text_bg_cap.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

import carousel  # noqa: E402

TEXT_TOP = 1033


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


def _is_background(canvas, y):
    return all(canvas.getpixel((x, y))[:3] == tuple(carousel.BG)
               for x in (0, 301, 777, canvas.width - 1))


def _layer(cv, **kw):
    return carousel._layer_if_can(cv, cv.convert("RGB"), TEXT_TOP, carousel.H, **kw)


# ---------------------------------------------------------------- slide than
def test_body_dark_background_capped_at_30_percent():
    carousel.set_background("dark")
    cv = _stacked_like_claude_slide()
    _layer(cv, image_cluttered=True, overlay_only=True)
    cap = carousel.H - int(carousel.H * 0.30)
    dark_rows = [y for y in range(carousel.H) if _near_bg(cv, y)]
    assert dark_rows, "phai co nen toi duoi chu"
    assert min(dark_rows) >= cap - 2, (min(dark_rows), cap)
    for y in (1040, 1200, carousel.H - 1):
        assert _near_bg(cv, y), (y, cv.getpixel((0, y)))


def test_body_image_above_overlay_untouched():
    """LOW-286 thay cho y LOW-215 "chu in san tren tran van tan ra bang lam mo": dai mo
    manh phia tren chu cat ngang mat nguoi, bi bac. Phan anh tren overlay giu NGUYEN."""
    carousel.set_background("dark")
    cv = _stacked_like_claude_slide()
    goc = cv.copy()
    _layer(cv, image_cluttered=True, overlay_only=True)
    for y in (100, 650, 800, TEXT_TOP - carousel.OVERLAY_LEAD - 20):
        assert cv.getpixel((301, y)) == goc.getpixel((301, y)), y


def test_body_dark_background_not_flat_background_color():
    """Luat 04/09: nen khong bao gio la mang mau tron — phan toi van mang mau anh."""
    carousel.set_background("dark")
    cv = Image.new("RGBA", (carousel.W, carousel.H), (200, 60, 30, 255))
    _layer(cv, image_cluttered=True, overlay_only=True)
    assert cv.getpixel((500, carousel.H - 5))[:3] != tuple(carousel.BG), cv.getpixel((500, carousel.H - 5))


def _bright_detailed():
    """Anh SANG va nhieu chi tiet (bang so lieu trang) — dung hinh dang lam overlay LOW-286
    thoai hoa thanh mang trang: do that slide 6 dcgr 20/09, do lech 99,7 -> 3,5."""
    W, H = carousel.W, carousel.H
    im = Image.new("RGBA", (W, H), (246, 246, 244, 255))
    d = ImageDraw.Draw(im)
    for y in range(0, H, 26):
        d.rectangle([40, y, W - 40, y + 11], fill=(40, 40, 44, 255))
    return im


def _row_spread(canvas, y):
    px = [canvas.getpixel((x, y))[:3] for x in range(0, canvas.width, 7)]
    tb = sum(sum(p) / 3 for p in px) / len(px)
    return (sum((sum(p) / 3 - tb) ** 2 for p in px) / len(px)) ** 0.5


def test_overlay_backs_off_until_the_image_is_still_there():
    """LOW-330: muc toi co dinh (80% + mo) tren anh sang nhieu chi tiet cho ra MOT MANG
    TRANG — cong bat dung nhung Dre dung han. `_overlay_text` phai tu lui toi khi do tren
    pixel that noi anh con hien qua."""
    carousel.set_background("dark")
    cv = _bright_detailed()
    truoc = cv.copy()
    carousel._layer_if_can(cv, cv.convert("RGB"), TEXT_TOP, carousel.H,
                           image_cluttered=True, overlay_only=True)
    bao = carousel._text_bg_report(truoc, cv)
    assert bao["bg_opacity"] <= carousel.TEXT_BG_SAFE_OPACITY, bao
    assert not carousel._gate_text_background("slide 2", bao), bao
    # Con chi tiet that duoi chu, khong phai mang mau tron.
    for y in (TEXT_TOP + 60, carousel.H - 40):
        assert _row_spread(cv, y) >= 4, (y, _row_spread(cv, y), _row_spread(truoc, y))


def test_overlay_does_not_back_off_when_it_does_not_need_to():
    """Anh binh thuong giu NGUYEN ban LOW-286 — vong lui khong duoc lam nhat ca loat."""
    carousel.set_background("dark")
    cv = _stacked_like_claude_slide()
    truoc = cv.copy()
    carousel._layer_if_can(cv, cv.convert("RGB"), TEXT_TOP, carousel.H,
                           image_cluttered=True, overlay_only=True)
    bao = carousel._text_bg_report(truoc, cv)
    assert bao["bg_opacity"] <= carousel.TEXT_BG_SAFE_OPACITY, bao
    # Buoc dau cua OVERLAY_BACKOFF la 1.0: mat na dung nguyen muc OVERLAY_CLUTTERED.
    assert carousel.OVERLAY_BACKOFF[0] == 1.0
    assert carousel.TEXT_BG_SAFE_OPACITY < carousel.TEXT_BG_MAX_OPACITY


# ---------------------------------------------------------------- bia (LOW-330)
def test_cover_cluttered_is_overlay_not_solid_background():
    """Duong BIA (khong `overlay_only`) truoc day goi `_background_solid_below_text`:
    tu khoang lang xuong day la MAU NEN DAC. Nay la overlay — anh lo qua moi hang."""
    carousel.set_background("dark")
    cv = _stacked_like_claude_slide()
    goc = cv.copy()
    _layer(cv, image_cluttered=True)
    for y in (TEXT_TOP + 10, 1200, carousel.H - 1):
        assert not _is_background(cv, y), (y, cv.getpixel((301, y)))
    for y in (100, 650, TEXT_TOP - carousel.OVERLAY_LEAD - 20):
        assert cv.getpixel((301, y)) == goc.getpixel((301, y)), y


def test_cover_and_body_take_the_same_road_when_cluttered():
    """Bia va slide than cung mot ket qua pixel: khong con hai duong code cho anh roi."""
    carousel.set_background("dark")
    bia, than = _stacked_like_claude_slide(), _stacked_like_claude_slide()
    _layer(bia, image_cluttered=True)
    _layer(than, image_cluttered=True, overlay_only=True)
    assert bia.tobytes() == than.tobytes()


def test_built_cover_passes_the_pixel_gate():
    """Bia dung THAT (ca anh roi lan anh sach) phai qua cong do nen chu tren pixel."""
    carousel.set_background("dark")
    with tempfile.TemporaryDirectory() as t:
        src = Path(t) / "a.png"
        _stacked_like_claude_slide().convert("RGB").save(src)
        for cluttered in (False, True):
            bao = {}
            carousel.build_cover(str(src), "Anthropic tự đặt thước đo tốc độ AI, trước khi bị bắt đo",
                                 "ANTHROPIC", str(Path(t) / "c.png"), "dcgr.tech",
                                 category="POLICY", cluttered=cluttered, report=bao)
            assert bao, cluttered
            assert bao["bg_opacity"] <= carousel.TEXT_BG_MAX_OPACITY, (cluttered, bao)
            loi = carousel._gate_text_background("bia", bao, max_share=carousel.TEXT_BG_MAX_SHARE_COVER)
            assert not loi, (cluttered, loi, bao)


# ---------------------------------------------------------------- cong anh ghep
def test_gate_blocks_stack_last_image_hidden():
    """A25+A29 cu: anh duoi 607..1215, nen dong vao tu 541 -> ro 0/608."""
    loi = carousel._gate_stack_last_hidden("slide 2", {"_stack_last": (607, 608)}, 541)
    assert "0/608" in loi, loi


def test_gate_stack_hint_matches_cause():
    """22/09/2026 (Dre dcgr t_b7a7ebb1): khong anh nao roi ma loi van bao "dat anh
    ROI len TREN" — Dre dao thu tu 27 lan toi het 90 vong. Loi phai noi dung nguyen
    nhan (day anh qua sang) va cach sua chua duoc."""
    geo = {"_stack_last": (607, 608), "quote": "q"}
    loi = carousel._gate_stack_last_hidden("slide 4", geo, 700)
    assert "RỐI lên TRÊN" not in loi, loi
    assert "KHÔNG chữa được" in loi and "MỘT ảnh" in loi and "bottom_brightness" in loi, loi
    assert "câu quote" in loi, loi
    roi = carousel._gate_stack_last_hidden("slide 4", {**geo, "cluttered": True}, 700)
    assert "RỐI lên TRÊN" in roi, roi


def test_gate_allows_stack_last_image_mostly_visible():
    assert carousel._gate_stack_last_hidden("slide 2", {"_stack_last": (607, 608)}, 900) == ""
    assert carousel._gate_stack_last_hidden("slide 2", {"_stack_last": (607, 608)}, None) == ""
    assert carousel._gate_stack_last_hidden("slide 2", {}, 541) == ""


def test_stack_records_last_image_geometry(tmp=None):
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
