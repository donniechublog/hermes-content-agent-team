#!/usr/bin/env python3
"""LOW-317 (20/09/2026) — "hom nay khong co gi" khong duoc gui khi VAN CON tin dat nguong.

Su co: 05:01 gio VN, topic Finn cua blog nhan *"Finn: hom nay khong co tin nao
dat nguong (da quet 35 tin). Khong co gi de chon."* Roi chinh Finn tu chan va
khai: chay `scan_submit.py --vai finn --khong-co` khi CHUA viet picks.json,
chua cham diem. Do lai `state/blog/scan/finn_20260920/candidates.json`: 35 ung
vien, trong do **3 tin da 50 diem co hoc** (phan bo that: 50x3, 49, 41, 34x2,
32x2, 22x25). Blog mat tron mot ngay tin.

Vi sao may kiem duoc ma khong can phan doan: diem co hoc (`score_partial`) la
SAN TREN cua diem tong — vai chi cong them technical (0-30) va relevance
(0-20), khong bao gio tru. Da >= SCORE_PASS diem co hoc thi chac chan dat nguong.

Chay:  venv/bin/python tests/test_low317_nothing_found_gate.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import scan_common  # noqa: E402
import scan_prepare  # noqa: E402
import scan_submit  # noqa: E402

# Phan bo diem co hoc THAT cua lan quet 20/09/2026 (35 ung vien).
FINN_20260920 = [50, 50, 50, 49, 41, 34, 34, 32, 32] + [22] * 26


def _candidates(diem: list) -> list:
    return [{"title": f"Tin {i}", "link": f"https://a.vn/{i}", "score_partial": d}
            for i, d in enumerate(diem, 1)]


def test_real_scan_20260920_would_have_been_blocked():
    chan = scan_submit.nothing_found_block(_candidates(FINN_20260920))
    assert chan, "lan quet that phai bi chan"
    assert "3 tin" in chan[0], chan[0]
    assert str(scan_common.SCORE_PASS) in chan[0]
    # Ba tin cao nhat phai duoc goi ten de vai biet cham lai tin nao.
    assert sum(1 for d in chan if d.strip().startswith("50d")) == 3, chan


def test_all_below_threshold_still_allowed():
    """That su khong co tin nao dat nguong thi van gui duoc nhu cu."""
    assert scan_submit.nothing_found_block(_candidates([49, 41, 34, 22])) == []
    assert scan_submit.nothing_found_block([]) == []


def test_threshold_is_inclusive():
    assert scan_submit.nothing_found_block(_candidates([scan_common.SCORE_PASS])) != []
    assert scan_submit.nothing_found_block(_candidates([scan_common.SCORE_PASS - 1])) == []


def test_missing_or_broken_score_does_not_block():
    """Ung vien thieu `score_partial` (hoac None) khong duoc tinh la dat nguong —
    chan oan thi vai khong bao gio ket thuc duoc task."""
    assert scan_submit.nothing_found_block([{"title": "T", "link": "https://a.vn/1"}]) == []
    assert scan_submit.nothing_found_block([{"title": "T", "score_partial": None}]) == []


def test_long_list_names_three_then_counts_the_rest():
    chan = scan_submit.nothing_found_block(_candidates([50] * 7))
    assert any("va 4 tin nua" in d for d in chan), chan


def test_brief_and_gate_read_the_same_threshold():
    """Brief day vai nguong nao thi cong phai chan dung nguong do — hai ban lech
    nhau la cong chan sai ma khong ai thay."""
    assert "import scan_common" in (ROOT / "scan_prepare.py").read_text(encoding="utf-8")
    src = (ROOT / "scan_prepare.py").read_text(encoding="utf-8")
    assert "scan_common.SCORE_PASS" in src, "brief phai lay hang chung"
    assert "≥ 50" not in src, "khong duoc go cung nguong trong brief"
    assert scan_prepare.scan_common.SCORE_PASS == scan_common.SCORE_PASS


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
