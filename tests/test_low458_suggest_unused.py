#!/usr/bin/env python3
"""LOW-458: loi "Dung anh khac" cua dre_submit phai chi TAM THAY THE co san trong bai.

Do 7 ngay toi 03/10/2026: 299/381 lan Dre goi find_more_images (78%) la luc bai DA du
anh. Ngay truoc lan goi thua hay nhat la loi "A# gan nhu TRONG" va "<chu the> cua A#
khong dat vua khung 4:5 phia TREN vung chu" — chi noi "Dung anh khac", khong noi tam nao,
nen Dre di tim anh moi (~2 phut moi lan) thay vi doi sang tam co san.

Chay:  venv/bin/python tests/test_low458_suggest_unused.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tam import so_tam  # noqa: E402
import test_spec_dre as ts  # noqa: E402
import test_stack_last_resort as sl  # noqa: E402

HINT = "KHÔNG cần find_more_images"


def _line(loi, *parts):
    return next((x for x in loi if all(p in x for p in parts)), None)


def test_empty_image_error_names_unused_image_that_passes():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = sl._bo(Path(t))
        m["images"][4]["empty_share"] = 0.9                   # A5 (slide 4) trong
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        line = _line(loi, "slide 4", "A5", "TRỐNG")
        assert line and "A6" in line and HINT in line, loi


def test_no_suggestion_when_every_fitting_image_is_already_used():
    """Khong co tam thay the thi KHONG duoc noi "khong can tim" — luc do tim them la dung."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = sl._bo(Path(t))
        m["images"][4]["empty_share"] = 0.9
        spec["slides"].append(ts._slide("A6"))                # A6 da dung o slide 5
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        line = _line(loi, "slide 4", "A5", "TRỐNG")
        assert line and HINT not in line, loi


def test_quote_slide_only_suggests_images_that_fit_above_the_quote_zone():
    """Vung chu slide quote (45%) lon hon slide than (30%): tam chi vua slide than khong
    duoc goi y cho slide quote."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = sl._bo(Path(t))
        # A6 vua ca quote; A8 chi vua slide than (chu the xuong toi 65% anh doc)
        m["images"].append(ts._anh(Path(t), "A8", 1000, 1250, uses=["body"], cluttered=False,
                                   subject_box=[0.3, 0.3, 0.7, 0.65], subject_kind="product",
                                   empty_share=0.2))
        m["images"][3]["empty_share"] = 0.9                   # A4 la slide 3 (quote) va trong
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        line = _line(loi, "slide 3", "A4", "TRỐNG")
        assert line and "A6" in line and "A8" not in line, loi


def test_suggestions_follow_the_real_gates_not_a_stricter_rule():
    """Phat lai 494 loi that: tieu chi "anh chup sach, khong mat nguoi" chi thay tam thay
    the o 10% loi, trong khi 89% loi co tam qua dung cac cong cua dre_submit. Goi y phai
    theo cong that: chua do hop chu the van qua `_place_subject`; mat nguoi KHONG ro ai thi
    bi `check_subject_named` chan -> khong goi y; anh roi xep sau anh sach."""
    import submit_common as nc
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        _spec, m, _wd = sl._bo(wd)
        extra = [ts._anh(wd, "A9", 1000, 1250, uses=["body"]),                       # chua do hop
                 ts._anh(wd, "A10", 1000, 1250, uses=["body"], faces=1),              # mat la
                 ts._anh(wd, "A11", 1000, 1250, uses=["body"], cluttered=True,
                         subject_box=[0.3, 0.1, 0.7, 0.5], empty_share=0.2)]
        m["images"] += extra
        anh = {a["id"]: a for a in m["images"]}
        used = {x: "s" for x in ("A1", "A2", "A3", "A4", "A5")}
        got = nc.unused_fitting_images(anh, used, m, 0.3)
        assert "A9" in got and "A10" not in got, got
        assert got.index("A11") > got.index("A6"), got


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
