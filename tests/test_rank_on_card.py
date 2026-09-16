#!/usr/bin/env python3
"""LOW-24 (12/09/2026): so hang vai viet len the phai TRUNG hang engine khoanh.

Ca that: hook "#3 bảng văn bản Arena" in len anh XH khoanh hang #26 (bang code).
Brief co ghi #26 nhung la chu dan, khong cong nao so. Test cong
`submit_common.check_rank_matches_image` (dung chung Ethan hook / Dre bia) va hai call site.
Fail tren code cu (khong co ham), pass tren code moi.

Chay:  venv/bin/python tests/test_rank_on_card.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import submit_common as nc                                       # noqa: E402


def _xh(hang=26, kieu="bang"):
    return {"ma": "XH", "xep_hang": {"site": "ARENA.AI", "bang": "WebDev / Code Arena",
                                     "model": "claude-opus-4-7-high", "hang": hang, "kieu": kieu}}


HOOK3 = "claude-opus-4-7-high leo lên #3 bảng văn bản Arena, chốt 1501.8 điểm Elo"


def test_hook_3_image_26_got_block_and_content_count():
    loi = nc.check_rank_matches_image(HOOK3, _xh(26))
    assert len(loi) == 1 and "#3" in loi[0] and "#26" in loi[0] and "Code Arena" in loi[0], loi


def test_hook_duplicate_rank_image_then_over():
    assert nc.check_rank_matches_image("claude-opus-4-7-high leo lên #26 bảng code Arena", _xh(26)) == []
    assert nc.check_rank_matches_image("Claude Opus 4.7 dẫn đầu Text Arena", _xh(1)) == []


def test_hook_no_say_rank_then_no_block():
    assert nc.check_rank_matches_image("Claude Opus 4.7 vào Text Arena với 1502 điểm", _xh(26)) == []


def test_fallback_card_no_change_dimension():
    assert nc.check_rank_matches_image(HOOK3, _xh(26, kieu="the")) == []


def test_image_regular_no_relevant():
    assert nc.check_rank_matches_image(HOOK3, {"ma": "A1"}) == []


def test_top10_is_size_has_list_clean_no_right_rank():
    assert nc.check_rank_matches_image("Top 10 model 2026: claude-opus-4-7-high dẫn đầu", _xh(1)) == []


def test_ethan_and_dre_all_call_gate():
    src_e = (ROOT / "ethan_submit.py").read_text(encoding="utf-8")
    src_d = (ROOT / "dre_submit.py").read_text(encoding="utf-8")
    assert "check_rank_matches_image(" in src_e, "ethan_submit chua goi cong LOW-24"
    assert "check_rank_matches_image(" in src_d, "dre_submit chua goi cong LOW-24"


if __name__ == "__main__":
    ok = 0
    ten = [k for k in list(globals()) if k.startswith("test_")]
    for k in ten:
        try:
            globals()[k]()
            ok += 1
        except AssertionError as e:
            print(f"    FAIL {k}: {e}")
    print(f"{Path(__file__).name:<34} {ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
