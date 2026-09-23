#!/usr/bin/env python3
"""LOW-364 (22/09/2026) — hinh 4:5 bi cat VUONG GIUA luc dang: noi dung chinh phai nam trong
o vuong giua.

Ong Chu, bai dcgr Grok 4.7 (the Ethan 1200x1500): *"lý do đã làm hình ratio 4:5 nhưng đăng
ig vẫn bị crop"* — Instagram/Threads cat 1:1, mat 150px tren (hang tieu de bang) va 150px
duoi (dong tua cuoi). Chot: *"đưa những thứ quan trọng nhất vào safezone, như vậy ko còn lệ
thuộc vào hình lúc publish nữa"*.

Do TREN PIXEL: dung the/slide tren mot anh nen biet truoc (dai mau ngang, hang nao cung nhu
hang nao), roi so tung hang cua hai dai bi cat voi chinh anh nen. Khac nen = co noi dung ve
vao dai bi cat. Code cu FAIL: khung chu Ethan toi y~1410, dong chu Dre toi 1230, chip bia
~1266, dong nguon quote ~1300.

Chay:  venv/bin/python tests/test_instagram_safe_zone.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402

import card  # noqa: E402
import carousel  # noqa: E402
import image_provenance  # noqa: E402
import safe_zone  # noqa: E402

TITLE = "Grok 4.7 tăng vọt 17,7 điểm phần trăm trên Terminal-Bench và giữ nguyên giá cước API"
TEXT = ("SpaceXAI vừa tung bản Grok 4.7 với cửa sổ ngữ cảnh nửa triệu token.\n\n"
        "Giá API giữ nguyên 2 USD cho mỗi triệu token đầu vào, đánh thẳng vào túi tiền "
        "của các xưởng code.")
QUOTE = "Chúng tôi giữ nguyên giá để mọi đội ngũ đều dùng được mô hình mạnh nhất."
TOL = 10       # lech muc xam cho phep (resize/nen mo cua chinh dai mau)


def _stripes(w, h):
    """Nen TOI doi mau theo chieu NGANG, moi hang nhu nhau — chu trang tu doc duoc, khong
    can lop phu (lop phu la nen, khong phai noi dung, nhung se lam nhieu phep do)."""
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for x in range(w):
        v = 30 + int(40 * x / w)
        d.line([(x, 0), (x, h)], fill=(v, v + 6, v + 12))
    return im


def _save(im, tmp, name, provenance=None):
    p = Path(tmp) / name
    im.save(p, pnginfo=image_provenance.stamp_provenance(provenance) if provenance else None)
    return str(p)


def _band_rows_changed(out, x0, x1):
    """Cac hang trong HAI dai bi cat 1:1 ma cot [x0, x1) lech khoi hang tham chieu (hang giua
    dai tren cung cua anh nen — anh nen hang nao cung nhu nhau)."""
    a = np.asarray(Image.open(out).convert("L"), dtype=np.float32)
    h, w = a.shape
    b = safe_zone.band(w, h)
    ref = a[b // 2, x0:x1]
    # LOW-365: o vuong that cat lech xuong duoi, nen vung an toan dich len SAFE_SHIFT_UP —
    # do theo safe_zone.top/bottom chu khong theo dai cat doi xung.
    bad = [y for y in list(range(safe_zone.top(w, h))) + list(range(safe_zone.bottom(w, h) + 1, h))
           if np.abs(a[y, x0:x1] - ref).max() > TOL]
    return bad, b


def _assert_bands_clean(out, label, x0, x1):
    bad, b = _band_rows_changed(out, x0, x1)
    assert not bad, (f"{label}: {len(bad)} hang trong dai bi cat 1:1 ({b}px moi dau) co noi dung "
                     f"— dau tien y={bad[0]}, cuoi y={bad[-1]}")


# ------------------------------------------------------------------ module chung
def test_band_is_square_center_crop():
    assert safe_zone.band(1200, 1500) == 150
    assert safe_zone.band(1080, 1350) == 135
    assert safe_zone.band(1080, 1080) == 0
    assert safe_zone.violations({"x": (200, 1300)}, 1200, 1500) == []
    assert safe_zone.violations({"x": (200, 1410)}, 1200, 1500)
    # LOW-365 (Ong Chu 23/09/2026, anh chup tu IG: tren con du vien, duoi sat chu): ca hai mep
    # cua vung an toan dich LEN SAFE_SHIFT_UP px.
    assert safe_zone.bottom(1200, 1500) == 1500 - 150 - safe_zone.SAFE_SHIFT_UP - safe_zone.SAFE_PAD
    assert safe_zone.top(1200, 1500) == 150 - safe_zone.SAFE_SHIFT_UP + safe_zone.SAFE_PAD
    assert safe_zone.violations({"x": (200, 1330)}, 1200, 1500)


# ------------------------------------------------------------------ Ethan
def test_ethan_frame_inside_safe_zone():
    """The Grok 4.7: khung chu toi y~1410, dong tua cuoi 1310-1380 -> mat khi cat 1:1.
    Ten kenh (@handle) duoc o lai dai duoi — chi xet hai ben, ngoai be ngang cua name kenh."""
    with tempfile.TemporaryDirectory() as t:
        out = str(Path(t) / "e.png")
        card.build(_save(_stripes(1200, 1500), t, "bg.png"), TITLE, out, ratio="4:5",
                   brand="dcgr", kieu="full_bleed", kicker="BENCHMARK", bo_qua_anh=True)
        assert Image.open(out).size == (1200, 1500)
        _assert_bands_clean(out, "the Ethan (trai)", 60, 400)
        _assert_bands_clean(out, "the Ethan (phai)", 800, 1140)


def test_ethan_source_capture_top_moves_into_safe_zone():
    """Anh chup trang (bang xep hang) co dinh trang: hang tieu de bang phai nam DUOI dai cat
    tren, dai tren la chinh mau nen cua trang keo dai."""
    cap = Image.new("RGB", (1200, 2400), (255, 255, 255))
    d = ImageDraw.Draw(cap)
    d.rectangle([0, 20, 1200, 60], fill=(20, 20, 20))            # hang tieu de bang
    for k in range(40):
        d.rectangle([40, 100 + k * 55, 1160, 120 + k * 55], fill=(120 + k, 120, 140))
    with tempfile.TemporaryDirectory() as t:
        out = str(Path(t) / "c.png")
        card.build(_save(cap, t, "cap.png", "source_capture"), TITLE, out, ratio="4:5",
                   brand="dcgr", kieu="full_bleed", kicker="BENCHMARK", bo_qua_anh=True)
        a = np.asarray(Image.open(out).convert("L"), dtype=np.float32)
        header_rows = [y for y in range(600) if a[y, 100:1100].mean() < 60]
        assert header_rows, "khong thay hang tieu de bang"
        assert header_rows[0] >= safe_zone.top(1200, 1500), \
            f"hang tieu de bang o y={header_rows[0]} — nam trong dai bi cat 1:1"
        assert a[:safe_zone.top(1200, 1500)].min() > 245, "dai tren khong phai mau nen trang"


def test_ethan_ranking_table_top_moves_into_safe_zone():
    """Anh bang xep hang (KHONG mang dau source_capture, thap hon the): the Grok 4.7 that van
    dat hang tieu de bang o y=0 sau ban dau — nhanh ha dinh chi nhin anh chup trang."""
    tab = Image.new("RGB", (1200, 1000), (255, 255, 255))
    d = ImageDraw.Draw(tab)
    d.rectangle([0, 20, 1200, 60], fill=(20, 20, 20))
    for k in range(15):
        d.rectangle([40, 100 + k * 55, 1160, 120 + k * 55], fill=(120 + k, 120, 140))
    with tempfile.TemporaryDirectory() as t:
        out = str(Path(t) / "r.png")
        card.build(_save(tab, t, "tab.png"), TITLE, out, ratio="4:5", brand="dcgr",
                   kieu="full_bleed", kicker="BENCHMARK", bo_qua_anh=True)
        a = np.asarray(Image.open(out).convert("L"), dtype=np.float32)
        header_rows = [y for y in range(600) if a[y, 100:1100].mean() < 60]
        assert header_rows and header_rows[0] >= safe_zone.top(1200, 1500), header_rows[:1]


def test_ethan_quote_card_inside_safe_zone():
    with tempfile.TemporaryDirectory() as t:
        out = str(Path(t) / "q.png")
        card.build(_save(_stripes(1200, 1500), t, "bg.png"), QUOTE, out, ratio="4:5",
                   brand="dcgr", kieu="quote", attrib="Elon Musk, SpaceXAI", bo_qua_anh=True)
        # Dong nguon (giua, hep) duoc roi vao dai cat — xet hai ben ngoai be ngang cua no.
        _assert_bands_clean(out, "the quote (trai)", 0, 380)
        _assert_bands_clean(out, "the quote (phai)", 820, 1200)


# ------------------------------------------------------------------ Dre
def _dre():
    carousel.set_brand("dcgr")
    carousel.set_background("dark")


def test_dre_body_inside_safe_zone():
    _dre()
    with tempfile.TemporaryDirectory() as t:
        out = str(Path(t) / "b.png")
        carousel.build_body(_save(_stripes(1080, 1350), t, "bg.png"), TEXT, None, out)
        _assert_bands_clean(out, "slide than", 0, 1080)


def test_dre_quote_inside_safe_zone():
    _dre()
    with tempfile.TemporaryDirectory() as t:
        out = str(Path(t) / "q.png")
        carousel.build_body_quote(_save(_stripes(1080, 1350), t, "bg.png"), QUOTE,
                                  "Elon Musk, SpaceXAI", None, out)
        # Ong Chu 22/09: dong nguon duoi khung "co the bo luon" -> ca be ngang dai cat phai sach.
        _assert_bands_clean(out, "slide quote", 0, 1080)


def test_dre_cover_inside_safe_zone():
    _dre()
    with tempfile.TemporaryDirectory() as t:
        out = str(Path(t) / "c.png")
        carousel.build_cover(_save(_stripes(1080, 1350), t, "bg.png"), TITLE, "GROK 4.7", out,
                             category="MODEL RELEASE")
        _assert_bands_clean(out, "bia", 0, 1080)


def test_dre_flat_table_top_inside_safe_zone():
    """Bang/hinh paper nen phang: dinh noi dung (hang tieu de) nam duoi dai cat tren."""
    _dre()
    fig = Image.new("RGB", (1600, 2000), (255, 255, 255))
    d = ImageDraw.Draw(fig)
    for k in range(30):
        d.rectangle([200, 100 + k * 60, 1400, 130 + k * 60], fill=(40, 40, 40))
    with tempfile.TemporaryDirectory() as t:
        out = str(Path(t) / "f.png")
        carousel.build_body(_save(fig, t, "fig.png"), TEXT, None, out)
        a = np.asarray(Image.open(out).convert("L"), dtype=np.float32)
        ink_rows = [y for y in range(a.shape[0]) if a[y].min() < 100]
        assert ink_rows[0] >= safe_zone.top(1080, 1350), f"dinh bang o y={ink_rows[0]}"


def _bright_stripes(w, h):
    """Nen SANG va roi (chu trang KHONG doc duoc) -> bat buoc co nen chu overlay."""
    im = Image.new("RGB", (w, h), (235, 225, 200))
    d = ImageDraw.Draw(im)
    for x in range(0, w, 14):
        d.rectangle([x, 0, x + 6, h], fill=(250, 250, 250))
    return im


def test_dre_overlay_hugs_text():
    """Ong Chu 22/09/2026: *"làm phần nền text hẹp lại sát vào phần quote / text hơn là ok"*.
    Duoi dong chu cuoi + OVERLAY_HOLD_AFTER + OVERLAY_TAIL, anh hien lai NGUYEN (code truoc do:
    overlay giu dam toi day khung)."""
    _dre()
    src = _bright_stripes(1080, 1350)
    ref = np.asarray(src.convert("L"), dtype=np.float32)
    with tempfile.TemporaryDirectory() as t:
        for name, build in (
                ("slide than", lambda p, o: carousel.build_body(p, TEXT, None, o)),
                ("slide quote", lambda p, o: carousel.build_body_quote(p, QUOTE, "", None, o))):
            out = str(Path(t) / "o.png")
            touched = build(_save(src, t, "bg.png"), out)
            assert touched is not None, f"{name}: anh sang ma khong co nen chu"
            a = np.asarray(Image.open(out).convert("L"), dtype=np.float32)
            below = carousel.TEXT_BASE + carousel.OVERLAY_HOLD_AFTER + carousel.OVERLAY_TAIL + 2
            x0, x1 = 0, 1080
            if name == "slide quote":
                # Vong 4: nen chu quote tan tu dong quote CUOI, khong keo toi net khung duoi —
                # do be ngang ben trai (net khung duoi va dau dong ngoac nam ben phai).
                below = safe_zone.bottom(1080, 1350) - 62 + carousel.OVERLAY_TAIL + 2
                x0, x1 = 100, 300
            diff = np.abs(a[below:, x0:x1] - ref[below:, x0:x1]).mean(axis=1)
            assert diff.max() < 3, f"{name}: nen chu con phu duoi y={below} (lech {diff.max():.0f})"


def test_ranking_image_uses_relaxed_flat_threshold():
    """Anh xep hang (arena X) la chart du spec khong khai "chart": nguong nen phang noi, de bia
    di duong 90% be ngang thay vi cover-crop mat hai canh (bia Xiaomi 22/09)."""
    import logo_card
    seen = []
    goc = logo_card.flat_background
    logo_card.flat_background = lambda im, relaxed=False: seen.append(relaxed) or (250, 250, 246)
    try:
        with tempfile.TemporaryDirectory() as t:
            p = _save(Image.new("RGB", (800, 800), (250, 250, 246)), t, "r.png", "ranking_capture")
            assert carousel._flat_plan({"image": p})[0] == (250, 250, 246)
    finally:
        logo_card.flat_background = goc
    assert seen == [True], seen


def test_gate_stops_layout_outside_safe_zone():
    try:
        safe_zone.gate("thu", {"text_frame": (1000, 1410)}, 1200, 1500)
    except SystemExit as e:
        assert "LOW-364" in str(e)
    else:
        raise AssertionError("cong khong dung")


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
