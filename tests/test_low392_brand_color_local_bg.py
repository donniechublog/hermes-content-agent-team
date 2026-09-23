#!/usr/bin/env python3
"""LOW-392 (23/09/2026) — mau ten hang phai fit theo nen NGAY DUOI cum chu do.

Bao cao ban dau ("cum ten model vat qua ranh sang/toi chi con CR 2.6") hoa ra la LOI CUA
PHEP DO, khong phai cua hinh: phep do cu lay TRUNG VI mot dai rong bang ca dong, nen tron
ca hai tong LAN net chu vao voi nhau. Do lai bang cach loai cac diem thuoc net chu thi tren
`main` a5c09ab cho CR thap nhat 3.33 — tren nguong `BRAND_MIN_CONTRAST_LARGE` = 3.0.

Nhung cai LECH thi co that va do duoc: `card._render_quote` dua cho `brand_fill` do sang
TRUNG BINH CA DAI DONG (x tu TEXT_X toi W-TEXT_X, 1008px), trong khi cum `GPT-5` chi nam o
x=96..323. Ranh sang/toi cat qua dai dong (lech chuan 23-59) thi hai con so lech nhau: code
dung 99 trong khi nen that duoi cum la 111. Mau duoc ep dat 3.0 so voi mot con so KHONG
phai nen ma no se nam len.

Test nay khoa dung cho do: muc nen code dung phai khop nen THAT duoi cum chu. Fail tren
`main` (lech 12), pass tren ban moi (lech <= 3).

Chay:  venv/bin/python tests/test_low392_brand_color_local_bg.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

import card  # noqa: E402
import text_bg  # noqa: E402
from test_gate import _image_two_tone  # noqa: E402

QUOTE = "Mô hình mở đầu tiên vượt GPT-5 trên SWE-bench Verified"
ATTRIB = "Đọc bài đầy đủ tại donniechublog"
SEAM = 0.76                  # ranh sang/toi cat NGANG dai dong chua cum ten model
INK_NEAR = 60                # lech mau duoi muc nay = diem thuoc net chu, khong phai nen
LEVEL_TOLERANCE = 8          # muc code dung duoc lech nen that bay nhieu


def _render(tmp):
    """Dung the quote tren anh hai tong -> (duong dan, [(hop net chu, mau, muc code dung)])."""
    ghi = []
    goc_fill, goc_draw = card.brand_fill, card.draw_brand_line

    def fill_spy(key, role, nen_sang=False, fallback=None, bg_level=None):
        mau = goc_fill(key, role, nen_sang, fallback, bg_level)
        ghi.append({"muc": bg_level, "mau": mau})
        return mau

    def draw_spy(d, x, y, dong, font, mau, colored=True, nen_sang=False, fallback=None,
                 bg_level=None, words=None, **kw):
        truoc = len(ghi)
        card.brand_fill = fill_spy
        try:
            goc_draw(d, x, y, dong, font, mau, colored, nen_sang, fallback, bg_level, words, **kw)
        finally:
            card.brand_fill = goc_fill
        # Hop net chu cua tung khuc, theo dung thu tu `brand_fill` da duoc goi.
        import brand_names
        xx, khoang, i = x, d.textlength(" ", font=font), truoc
        for word in (words if words is not None else brand_names.line_segments(dong)):
            for text, role, _key in word:
                rong = d.textlength(text, font=font)
                if colored and role and i < len(ghi):
                    bb = font.getbbox(text)
                    ghi[i]["hop"] = (x + 0 if False else xx + bb[0], y + bb[1], xx + bb[2], y + bb[3])
                    ghi[i]["chu"] = text
                    i += 1
                xx += rong
            xx += khoang

    card.set_brand("donniechublog")
    src = _image_two_tone(1200, 1560, Path(tmp) / "nen.png", SEAM)
    ra = Path(tmp) / "the.png"
    card.draw_brand_line = draw_spy
    try:
        card.build(str(src), QUOTE, str(ra), handle="@donniechublog", ratio="4:5", attrib=ATTRIB)
    finally:
        card.draw_brand_line = goc_draw
    return ra, [g for g in ghi if g.get("hop")]


def _background_under(path, hop, mau):
    """Nen THAT trong hop net chu: bo cac diem thuoc net chu roi lay trung vi."""
    rgb = np.asarray(Image.open(path).convert("RGB"), dtype=np.float32)
    x0, y0, x1, y1 = (int(v) for v in hop)
    o = rgb[y0:y1, x0:x1]
    net = np.abs(o - np.array(mau, dtype=np.float32)).max(axis=2) < INK_NEAR
    nen = o[~net]
    assert len(nen), "hop toan net chu, khong do duoc nen"
    return float(np.median(nen.mean(axis=1)))


def test_brand_color_fits_the_background_it_actually_sits_on():
    """Muc nen code dua cho `brand_fill` phai la nen duoi CUM CHU, khong phai ca dai dong."""
    with tempfile.TemporaryDirectory() as t:
        ra, ghi = _render(t)
        assert ghi, "khong ghi nhan duoc khuc ten hang nao"
        for g in ghi:
            that = _background_under(ra, g["hop"], g["mau"])
            assert g["muc"] is not None, f"{g['chu']}: khong do nen gi, mau to mu"
            assert abs(g["muc"] - that) <= LEVEL_TOLERANCE, (
                f"{g['chu']}: code fit theo nen {g['muc']:.0f} nhung nen that duoi cum la "
                f"{that:.0f} (lech {abs(g['muc'] - that):.0f})")


def test_brand_color_keeps_contrast_on_the_seam():
    """Va do thanh qua: tuong phan THAT (bo net chu ra) dat nguong cho chu to."""
    with tempfile.TemporaryDirectory() as t:
        ra, ghi = _render(t)
        for g in ghi:
            that = _background_under(ra, g["hop"], g["mau"])
            cr = text_bg.ratio_wall_part(tuple(g["mau"]), (round(that),) * 3)
            assert cr >= card.BRAND_MIN_CONTRAST_LARGE, (
                f"{g['chu']}: CR {cr:.2f} < {card.BRAND_MIN_CONTRAST_LARGE} tren nen {that:.0f}")


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:           # noqa: BLE001
                failed += 1
                print(f"FAIL {name}: {e}")
    sys.exit(1 if failed else 0)
