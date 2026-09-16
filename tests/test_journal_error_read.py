#!/usr/bin/env python3
"""Nhật ký không được IM LẶNG khi đọc kanban.db hỏng (hồi quy review Fable, C2).

Lich su: 06/09/2026 doi them `_bear_error_db` vi mot lan `hermes update` doi ten
cot lam nhat_ky chet im — cron chay `>/dev/null 2>&1`, khong trang, khong dong
log. Decorator do bat sqlite3.Error va day vao LOI_DOC, in o CUOI TRANG.

09/09/2026 C2 chuyen part_kanban sang hermes_adapter. Adapter NUOT sqlite3.Error
va tra None, nen decorator khong con bat duoc gi — ban dau tien cua doan nay tra
[] im lang: trang nhat ky hien "hom nay khong co task" trong khi thuc ra la doc
DB loi. Dung su co 06/09 lam lai. Test nay giu cho no khong quay lai.

Chay:  venv/bin/python tests/test_journal_error_read.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import hermes_adapter as ha                                   # noqa: E402
import journal as nk                                          # noqa: E402

_TS = 1_757_400_000                       # mot moc epoch bat ky trong 09/2026
_NGAY = nk._hours_vn(_TS).strftime("%Y-%m-%d")


def _run(viec, runs=None):
    """Goi part_kanban voi adapter gia; tra (ket_qua, LOI_DOC sau khi goi)."""
    cu = (ha.job, ha.last_run_many)
    ha.job = lambda *a, **k: viec
    ha.last_run_many = lambda tids: runs
    nk.ERROR_READ.clear()
    try:
        return nk.part_kanban(_NGAY), list(nk.ERROR_READ)
    finally:
        ha.job, ha.last_run_many = cu
        nk.ERROR_READ.clear()


def test_kanban_no_read_ok_then_error_read_right_has_line():
    """None tu adapter = doc DB hong. Phai len LOI_DOC de in cuoi trang."""
    ra, loi = _run(None)
    assert ra == [], ra
    assert any("part_kanban" in d for d in loi), \
        f"doc kanban hong ma LOI_DOC rong -> trang nhat ky im lang, dung su co 06/09: {loi}"


def test_kanban_empty_real_then_no_report_error():
    """[] tu adapter = doc duoc, hom nay khong co task. Khac han None (quy uoc C1)."""
    ra, loi = _run([])
    assert ra == [] and loi == [], f"khong co task ma lai bao loi: {loi}"


def test_task_runs_no_read_ok_then_still_out_task_and_has_line_report():
    """viec doc duoc nhung task_runs hong: van liet ke task (tom tat trong), va
    LOI_DOC phai noi ro la phan tom tat/loi bi thieu — khong duoc im."""
    v = [{"id": "t1", "vai": "ethan", "trang_thai": "done", "tieu_de": "Bai X",
          "tao_luc": _TS, "bat_dau_luc": None, "xong_luc": None,
          "ket_qua": "kq", "loi": None}]
    ra, loi = _run(v, runs=None)
    assert [x["id"] for x in ra] == ["t1"], ra
    assert ra[0]["tom_tat"] == "kq", "khong co run thi phai roi ve result cua task"
    assert any("task_runs" in d for d in loi), f"task_runs hong ma khong bao: {loi}"


def test_read_ok_all_done_then_error_read_empty_and_take_use_summary():
    v = [{"id": "t1", "vai": "ethan", "trang_thai": "done", "tieu_de": "Bai X",
          "tao_luc": _TS, "bat_dau_luc": None, "xong_luc": None,
          "ket_qua": "kq", "loi": None}]
    ra, loi = _run(v, runs={"t1": {"tom_tat": "da giao 6 anh", "loi": None}})
    assert loi == [], loi
    assert ra[0]["tom_tat"] == "da giao 6 anh", ra


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
