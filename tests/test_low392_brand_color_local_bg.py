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
import carousel  # noqa: E402
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
                    ghi[i]["hop"] = (xx + bb[0], y + bb[1], xx + bb[2], y + bb[3])
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


# ---------------------------------------------------- bia carousel cua Dre (duong DANG CHAY)
HOOK = "GPT-5 và Claude Opus 5.5 cùng hạ giá API trong một tuần"
COVER_MIN_CR = 2.5           # tren nen sang L~156, mau SANG NHAT cung chi dat ~2.72 (tran vat ly)


def _render_cover(tmp, seam):
    """Bia Dre tren anh hai tong -> (duong dan, [(hop net chu, mau)])."""
    ghi = []
    goc = card.draw_brand_line

    def spy(d, x, y, dong, font, mau, colored=True, nen_sang=False, fallback=None,
            bg_level=None, words=None, bg_for=None):
        import brand_names
        xx, khoang = x, d.textlength(" ", font=font)
        for word in (words if words is not None else brand_names.line_segments(dong)):
            for text, role, key in word:
                rong = d.textlength(text, font=font)
                if colored and role:
                    bb = font.getbbox(text)
                    muc = bg_level
                    if bg_for is not None:
                        muc = bg_for(xx + bb[0], y + bb[1], xx + bb[2], y + bb[3])
                    ghi.append({"chu": text, "muc": muc,
                                "hop": (xx + bb[0], y + bb[1], xx + bb[2], y + bb[3]),
                                "mau": card.brand_fill(key, role, nen_sang, fallback, muc)})
                xx += rong
            xx += khoang
        try:
            return goc(d, x, y, dong, font, mau, colored, nen_sang, fallback, bg_level, words, bg_for)
        except TypeError:            # ma cu chua co `bg_for` — van do duoc hanh vi that cua no
            return goc(d, x, y, dong, font, mau, colored, nen_sang, fallback, bg_level, words)

    carousel.set_brand("dcgr")
    carousel.set_background("dark")
    src = _image_two_tone(carousel.W, carousel.H, Path(tmp) / f"nen{seam}.png", seam)
    ra = Path(tmp) / f"bia{seam}.png"
    card.draw_brand_line = spy
    try:
        carousel.build_cover(str(src), HOOK, "OPUS 5.5", str(ra), category="MODEL RELEASE")
    finally:
        card.draw_brand_line = goc
    return ra, ghi


def test_dre_cover_brand_name_keeps_contrast_on_bright_band():
    """Bia Dre: hook nam tren dai SANG cua anh chup. Truoc LOW-392 hook khong do nen gi ca
    (`bg_level` None) nen mau hang giu nguyen palette — do that: "Claude" cam tren nen 151
    chi con CR 1.07-1.28, gan nhu mat chu ben canh dong chu trang cung dong."""
    with tempfile.TemporaryDirectory() as t:
        for seam in (0.55, 0.62):
            ra, ghi = _render_cover(t, seam)
            assert ghi, f"ranh {seam}: khong ghi nhan cum ten hang nao"
            for g in ghi:
                assert g["muc"] is not None, f"{g['chu']}: hook khong do nen, mau to mu"
                that = _background_under(ra, g["hop"], g["mau"])
                cr = text_bg.ratio_wall_part(tuple(g["mau"]), (round(that),) * 3)
                assert cr >= COVER_MIN_CR, (
                    f"ranh {seam} {g['chu']}: CR {cr:.2f} < {COVER_MIN_CR} tren nen {that:.0f}")


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
