#!/usr/bin/env python3
"""LOW-444 (30/09/2026) — the 4:5 / 3:4: anh cao GAN bang the + dinh phang -> dai DEN giua dai
mau keo dai va anh.

`card._layer_image` (LOW-364) ha anh co dinh phang xuong `safe_zone.top` (142 o 4:5, 192 o 3:4),
dai tren la chinh mau dinh keo dai. Anh thap hon the nhung nat_h + shift > H thi code cat GIUA:
top = (nat_h - H) // 2 — AM khi nat_h <= H, PIL dem DEN phan ngoai anh. Audit do that: the
`full_bleed` 1200x1500 tu anh 1200x1440 co 40 hang trang tren dinh -> 30 hang den thuan o
y=142..171 — mot vach ngang cat the lam hai (IMAGE_RULES §7).

Do TREN PIXEL: dung the that (`card.build`) tu anh co dinh trang phang, than xam (khong hang
nao den), roi dem hang TOAN DEN tu `shift` xuong. Code cu FAIL o 4:5 va 3:4; 1:1 mien (shift am).

Chay:  venv/bin/python tests/test_low444_card_negative_crop.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import card  # noqa: E402
import safe_zone  # noqa: E402

QUOTE = "Chúng tôi giữ nguyên giá để mọi đội ngũ đều dùng được mô hình mạnh nhất."
TITLE = "Grok 4.7 tăng vọt 17,7 điểm phần trăm trên Terminal-Bench"
FLAT_TOP = 40          # hang trang phang tren dinh anh (nhu le trang cua trang web)
BLACK_MAX = 8          # hang co moi pixel <= muc nay = hang den thuan (dem cua PIL)


def _flat_top_image(h, w=1200):
    """Anh w x h: FLAT_TOP hang trang phang tren dinh, than xam co van — khong hang nao den."""
    im = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(im)
    for y in range(FLAT_TOP, h, 20):
        d.rectangle([0, y, w, y + 19], fill=(90 + (y // 20) % 5 * 20, 110, 130))
    return im


def black_rows(img, y0, y1):
    """Cong do: cac hang trong [y0, y1) ma MOI pixel deu den thuan."""
    a = np.asarray(img.convert("L"))
    return [y for y in range(max(0, y0), min(a.shape[0], y1)) if a[y].max() <= BLACK_MAX]


def _layer(ratio, nat_h, top_anchor=False):
    H = card.RATIOS[ratio]
    canvas = Image.new("RGBA", (card.W, H), (10, 10, 10, 255))
    card._layer_image(canvas, _flat_top_image(nat_h), H, top_anchor=top_anchor)
    return canvas, H


def test_shift_values():
    """Mien 1:1 dung vi shift am; 4:5/3:4 la hai ti le dinh loi."""
    assert safe_zone.top(1200, 1200) == -8
    assert safe_zone.top(1200, 1500) == 142
    assert safe_zone.top(1200, 1600) == 192


def test_layer_no_black_band_4_5_and_3_4():
    """Moi nat_h trong (H - shift, H]: tu shift xuong khong hang nao den; anh bat dau DUNG tai
    shift (hang dinh trang cua anh nam ngay duoi dai mau keo dai)."""
    for ratio in ("4:5", "3:4"):
        H = card.RATIOS[ratio]
        shift = safe_zone.top(card.W, H)
        for nat_h in (H - shift + 2, H - shift + 60, H - 60, H - 1, H):
            cv, _ = _layer(ratio, nat_h)
            den = black_rows(cv, 0, H)
            assert not den, (f"{ratio} anh 1200x{nat_h}: {len(den)} hang den thuan "
                             f"y={den[0]}..{den[-1]} (shift={shift})")
            a = np.asarray(cv.convert("L"))
            assert a[:shift + FLAT_TOP].min() > 245, \
                f"{ratio} anh 1200x{nat_h}: dai tren + dinh anh khong con la mot mat trang lien"


def test_layer_cuts_bottom_not_top():
    """Anh thap hon the bi day xuong thi mat phan DAY (khong mat dinh)."""
    H = card.RATIOS["4:5"]
    shift = safe_zone.top(card.W, H)
    src = _flat_top_image(1440)
    cv = Image.new("RGBA", (card.W, H), (10, 10, 10, 255))
    card._layer_image(cv, src, H)
    got = np.asarray(cv.convert("RGB"))[shift:H]
    want = np.asarray(src.convert("RGB"))[0:H - shift]
    assert np.abs(got.astype(int) - want.astype(int)).max() <= 2, "anh khong dat tu dinh tai shift"


def test_square_and_taller_unchanged():
    """1:1 (shift am) va anh CAO hon the (cat giua, khong ha) khong doi hanh vi."""
    cv, H = _layer("1:1", 1150)
    assert not black_rows(cv, 0, H)
    for ratio in ("4:5", "3:4"):
        H = card.RATIOS[ratio]
        src = _flat_top_image(H + 300)
        cv = Image.new("RGBA", (card.W, H), (10, 10, 10, 255))
        card._layer_image(cv, src, H)
        got = np.asarray(cv.convert("RGB")).astype(int)
        want = np.asarray(src.convert("RGB"))[150:150 + H].astype(int)
        assert np.abs(got - want).max() <= 2, f"{ratio}: anh cao hon the khong con cat giua"


def test_source_capture_top_anchor_unchanged():
    for ratio in ("4:5", "3:4"):
        H = card.RATIOS[ratio]
        cv, _ = _layer(ratio, H - 30, top_anchor=True)
        assert not black_rows(cv, 0, H), ratio


def test_real_cards_no_black_band():
    """The THAT (quote + full_bleed) o 4:5 va 3:4 tu anh 1200x1440 / 1200x1500 dinh phang."""
    with tempfile.TemporaryDirectory() as t:
        for ratio, nat_h in (("4:5", 1440), ("3:4", 1500)):
            src = Path(t) / f"src_{nat_h}.png"
            _flat_top_image(nat_h).save(src)
            H = card.RATIOS[ratio]
            shift = safe_zone.top(card.W, H)
            for kieu in ("quote", "full_bleed"):
                out = str(Path(t) / f"{kieu}_{ratio.replace(':', 'x')}.png")
                card.build(str(src), QUOTE if kieu == "quote" else TITLE, out, ratio=ratio,
                           brand="dcgr", kieu=kieu, kicker="BENCHMARK", attrib="Elon Musk",
                           bo_qua_anh=True)
                img = Image.open(out)
                assert img.size == (card.W, H), img.size
                den = black_rows(img, shift, shift + FLAT_TOP + 40)
                assert not den, (f"the {kieu} {ratio}: {len(den)} hang den thuan "
                                 f"y={den[0]}..{den[-1]} giua dai mau keo dai va anh")


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
