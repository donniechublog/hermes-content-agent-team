#!/usr/bin/env python3
"""Nhật ký không được IM LẶNG khi đọc kanban.db hỏng (hồi quy review Fable, C2).

Lich su: 06/09/2026 doi them `_chiu_loi_db` vi mot lan `hermes update` doi ten
cot lam nhat_ky chet im — cron chay `>/dev/null 2>&1`, khong trang, khong dong
log. Decorator do bat sqlite3.Error va day vao LOI_DOC, in o CUOI TRANG.

09/09/2026 C2 chuyen phan_kanban sang hermes_adapter. Adapter NUOT sqlite3.Error
va tra None, nen decorator khong con bat duoc gi — ban dau tien cua doan nay tra
[] im lang: trang nhat ky hien "hom nay khong co task" trong khi thuc ra la doc
DB loi. Dung su co 06/09 lam lai. Test nay giu cho no khong quay lai.

Chay:  venv/bin/python tests/test_nhat_ky_loi_doc.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import hermes_adapter as ha                                   # noqa: E402
import nhat_ky as nk                                          # noqa: E402

_TS = 1_757_400_000                       # mot moc epoch bat ky trong 09/2026
_NGAY = nk._gio_vn(_TS).strftime("%Y-%m-%d")


def _chay(viec, runs=None):
    """Goi phan_kanban voi adapter gia; tra (ket_qua, LOI_DOC sau khi goi)."""
    cu = (ha.viec, ha.lan_chay_cuoi_nhieu)
    ha.viec = lambda *a, **k: viec
    ha.lan_chay_cuoi_nhieu = lambda tids: runs
    nk.LOI_DOC.clear()
    try:
        return nk.phan_kanban(_NGAY), list(nk.LOI_DOC)
    finally:
        ha.viec, ha.lan_chay_cuoi_nhieu = cu
        nk.LOI_DOC.clear()


def test_kanban_khong_doc_duoc_thi_LOI_DOC_phai_co_dong():
    """None tu adapter = doc DB hong. Phai len LOI_DOC de in cuoi trang."""
    ra, loi = _chay(None)
    assert ra == [], ra
    assert any("phan_kanban" in d for d in loi), \
        f"doc kanban hong ma LOI_DOC rong -> trang nhat ky im lang, dung su co 06/09: {loi}"


def test_kanban_rong_that_thi_KHONG_bao_loi():
    """[] tu adapter = doc duoc, hom nay khong co task. Khac han None (quy uoc C1)."""
    ra, loi = _chay([])
    assert ra == [] and loi == [], f"khong co task ma lai bao loi: {loi}"


def test_task_runs_khong_doc_duoc_thi_van_ra_task_va_co_dong_bao():
    """viec doc duoc nhung task_runs hong: van liet ke task (tom tat trong), va
    LOI_DOC phai noi ro la phan tom tat/loi bi thieu — khong duoc im."""
    v = [{"id": "t1", "vai": "ethan", "trang_thai": "done", "tieu_de": "Bai X",
          "tao_luc": _TS, "bat_dau_luc": None, "xong_luc": None,
          "ket_qua": "kq", "loi": None}]
    ra, loi = _chay(v, runs=None)
    assert [x["id"] for x in ra] == ["t1"], ra
    assert ra[0]["tom_tat"] == "kq", "khong co run thi phai roi ve result cua task"
    assert any("task_runs" in d for d in loi), f"task_runs hong ma khong bao: {loi}"


def test_doc_duoc_het_thi_LOI_DOC_rong_va_lay_dung_tom_tat():
    v = [{"id": "t1", "vai": "ethan", "trang_thai": "done", "tieu_de": "Bai X",
          "tao_luc": _TS, "bat_dau_luc": None, "xong_luc": None,
          "ket_qua": "kq", "loi": None}]
    ra, loi = _chay(v, runs={"t1": {"tom_tat": "da giao 6 anh", "loi": None}})
    assert loi == [], loi
    assert ra[0]["tom_tat"] == "da giao 6 anh", ra


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
