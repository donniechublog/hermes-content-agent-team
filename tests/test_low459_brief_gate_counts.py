#!/usr/bin/env python3
"""LOW-459: brief Dre phai noi con so CONG NOP that se nhan, khong chi so "dung duoc" tho.

Do 7 ngay toi 03/10/2026 tren 85 manifest Dre: trung vi `usable_count` 15, nhung chi 3
anh don qua cong vung chu slide than, 2 qua cong quote. Dre tin "Slide dung duoc 15 / 6 —
DU", nop, bi chan, roi di tim them (LOW-458: 78% lan find_more la luc "du").

Chay:  venv/bin/python tests/test_low459_brief_gate_counts.py
"""
import inspect
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tam import so_tam  # noqa: E402
import test_spec_dre as ts  # noqa: E402
import test_stack_last_resort as sl  # noqa: E402
import submit_common as nc  # noqa: E402


def test_summary_counts_each_slide_kind_with_its_own_text_zone():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        _spec, m, _wd = sl._bo(wd)
        # A6 vua ca quote; A8 chi vua slide than (chu the xuong toi 65% anh doc)
        m["images"].append(ts._anh(wd, "A8", 1000, 1250, uses=["body"], cluttered=False,
                                   subject_box=[0.3, 0.3, 0.7, 0.65], subject_kind="product",
                                   empty_share=0.2))
        for a in m["images"][:5]:
            a["empty_share"] = 0.9                         # A1..A5 trong: khong qua cong nao
        line = nc.gate_ready_summary(m)
        assert "thân 2 (A6, A8)" in line, line
        assert "quote 1 (A6)" in line, line
        assert "TRƯỚC khi đi tìm thêm" in line, line


def test_role_without_per_slide_text_zones_gets_no_line():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        _spec, m, _wd = sl._bo(Path(t))
        m["image_role"] = "ethan"                          # mot anh, khong co vung chu quote/bia
        assert nc.gate_ready_summary(m) == ""


def test_brief_and_find_more_print_the_gate_line():
    import dre_prepare
    import find_more_images
    assert "gate_ready_summary(" in inspect.getsource(dre_prepare.write_brief)
    assert "gate_ready_summary(" in inspect.getsource(find_more_images.in_result)


if __name__ == "__main__":
    ok = 0
    ten = [n for n in dir() if n.startswith("test_")]
    for n in ten:
        try:
            globals()[n]()
            ok += 1
        except AssertionError as e:
            print(f"FAIL {n}: {e}")
        except AttributeError as e:
            print(f"FAIL {n}: {e}")
    print(f"{ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
