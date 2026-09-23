#!/usr/bin/env python3
"""LOW-383 (23/09/2026) — cung model quet duoc o ca arena.ai lan AA thi giu ban arena.

Ong Chu: *"giu no lam nguon bo sung cho Nova quet, neu quet duoc o ca AA thi tin
quet tu Arena.ai duoc uu tien"*.

Bay o day KHONG phai luat uu tien, ma la phep so ten: arena tra slug
(`claude-opus-5-max`), AA tra ten hien thi (`Claude Opus 5.5`). Do that tren may
chu 23/09: khop tho thay 1/20 ten trung, qua `model_name.display_name` la 16/20 —
luat uu tien ma khop tho thi im lang bo sot 15/16 ca.

Chay:  python tests/test_scan_source_priority.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import model_boards  # noqa: E402
import scan_models  # noqa: E402


def _climb(board, name, previous_rank=3, rank=1):
    return {"board": board, "name": name, "rank": rank, "previous_rank": previous_rank,
            "climb": None if previous_rank is None else previous_rank - rank,
            "note": "MOI vao bang" if previous_rank is None else "leo"}


def _release(name, released="2026-09-22"):
    return {"original_name": name, "released": released, "maker": "Anthropic",
            "coding": 58, "coding_rank": 1}


def test_board_keys_come_from_the_registry():
    """Them bang moi khong phai nho sua mot danh sach thu hai (bai hoc 07/09)."""
    assert "webdev" in model_boards.ARENA_KEYS and "text" in model_boards.ARENA_KEYS
    assert "intelligence" in model_boards.AA_KEYS and "coding" in model_boards.AA_KEYS
    assert "tts" in model_boards.AA_KEYS, "bang media cung la cua artificialanalysis"
    assert not (model_boards.ARENA_KEYS & model_boards.AA_KEYS)
    assert "livebench" not in model_boards.ARENA_KEYS | model_boards.AA_KEYS, \
        "benchmark rieng khong thuoc ben nao — luat uu tien khong duoc dung toi"


def test_same_model_named_two_ways_counts_as_one():
    """Chinh ca that: arena goi `claude-opus-5-5-max`, AA goi `Claude Opus 5.5`."""
    climbs = [_climb("webdev", "claude-opus-5-5-max"), _climb("intelligence", "Claude Opus 5.5")]
    _, kept, _ = scan_models.prefer_arena([], climbs)
    assert [c["board"] for c in kept] == ["webdev"], "ban AA phai nhuong cho arena"
    # Gach noi trong ten CO chu hoa (`GLM-5.3`) khong duoc lam lech phep so.
    both_sides = [_climb("webdev", "glm-5.3"), _climb("coding", "GLM-5.3")]
    _, kept2, _ = scan_models.prefer_arena([], both_sides)
    assert [c["board"] for c in kept2] == ["webdev"]


def test_a_shorter_version_is_not_the_same_model():
    """Luat LOW-177 o phep so ten: Opus 5 khong duoc nuot Opus 5.5."""
    climbs = [_climb("webdev", "claude-opus-5-max"), _climb("intelligence", "Claude Opus 5.5")]
    _, kept, _ = scan_models.prefer_arena([], climbs)
    assert {c["board"] for c in kept} == {"webdev", "intelligence"}


def test_a_model_only_on_aa_still_reports():
    """AA la nguon BO SUNG, khong phai nguon bi cam noi. Do 23/09: 4/20 ten chi co o AA."""
    climbs = [_climb("webdev", "gpt-6-astra-max"), _climb("intelligence", "Step 5 Preview")]
    _, kept, _ = scan_models.prefer_arena([], climbs)
    assert {c["board"] for c in kept} == {"webdev", "intelligence"}


def test_independent_benchmarks_are_untouched():
    climbs = [_climb("webdev", "kimi-k3"), _climb("livebench", "Kimi-K3"),
              _climb("tbench", "Kimi-K3")]
    _, kept, _ = scan_models.prefer_arena([], climbs)
    assert {c["board"] for c in kept} == {"webdev", "livebench", "tbench"}, \
        "LiveBench/Terminal-Bench do thu khac, khong phai ban sao cua arena"


def test_release_yields_only_to_a_first_sighting_on_arena():
    """"Leo 3 bac" ben arena la tin KHAC, khong thay duoc tin "model moi xuat hien"."""
    first_seen = [_climb("webdev", "claude-opus-5-5-max", previous_rank=None)]
    climbed = [_climb("webdev", "claude-opus-5-5-max", previous_rank=3)]
    kept, _, dropped = scan_models.prefer_arena([_release("Claude Opus 5.5")], first_seen)
    assert kept == [] and [r["original_name"] for r in dropped] == ["Claude Opus 5.5"]
    kept2, _, dropped2 = scan_models.prefer_arena([_release("Claude Opus 5.5")], climbed)
    assert [r["original_name"] for r in kept2] == ["Claude Opus 5.5"] and dropped2 == []


def test_it_says_what_it_dropped():
    """Im lang thi "vi sao Nova khong bao model nay" lai phai doan (INV-3)."""
    logged = []
    scan_models.prefer_arena([], [_climb("webdev", "glm-5.3"), _climb("coding", "GLM-5.3")],
                             in_log=logged.append)
    assert logged and "coding|GLM-5.3" in logged[0]


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
