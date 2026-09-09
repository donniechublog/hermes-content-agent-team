#!/usr/bin/env python3
"""`hermes_adapter` — nơi duy nhất biết ruột kanban.db (issue C2).

Vi sao test ky: kanban.db la bang cua TIEN TRINH KHAC (hermes-agent), hermes co
quyen doi schema bat cu luc nao. Truoc day tri thuc ve no nam rai o 5 tep, doi
schema la phai sua 5 cho va quen mot cho thi cho do hong CAM. Tep test nay giu
hai thu: (1) doc dung du lieu, (2) khong doc duoc thi tra None chu KHONG tra
rong — vi "khong doc duoc kanban" va "kanban khong co viec nao" la hai ket luan
khac han nhau (quy uoc C1).

Chay:  venv/bin/python tests/test_hermes_adapter.py
"""
import json
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import hermes_adapter as ha                                   # noqa: E402

# Chi cac cot adapter thuc su doc — du de bat loi doi ten cot.
_TAO_TASKS = """CREATE TABLE tasks (
    id TEXT PRIMARY KEY, assignee TEXT, status TEXT, title TEXT,
    created_at INTEGER, started_at INTEGER, completed_at INTEGER,
    result TEXT, last_failure_error TEXT)"""
_TAO_RUNS = """CREATE TABLE task_runs (
    id INTEGER PRIMARY KEY, task_id TEXT, status TEXT, summary TEXT,
    error TEXT, metadata TEXT)"""


def _db(tmp, tasks=(), runs=()):
    """Dung mot kanban.db gia va tro adapter vao no."""
    p = Path(tmp) / "kanban.db"
    con = sqlite3.connect(p)
    con.execute(_TAO_TASKS)
    con.execute(_TAO_RUNS)
    con.executemany("INSERT INTO tasks VALUES (?,?,?,?,?,?,?,?,?)", tasks)
    con.executemany("INSERT INTO task_runs VALUES (?,?,?,?,?,?)", runs)
    con.commit()
    con.close()
    ha.kanban_db = lambda: p
    return p


def _go():
    ha.kanban_db = _KANBAN_DB_THAT


_KANBAN_DB_THAT = ha.kanban_db


# ------------------------------------------------------------------ doc duoc
def test_viec_loc_theo_vai_va_gioi_han():
    with tempfile.TemporaryDirectory() as tmp:
        _db(tmp, tasks=[
            ("t1", "designer", "done", "bai 1", 100, 101, 102, "xong", None),
            ("t2", "writer", "ready", "bai 2", 200, None, None, None, None),
            ("t3", "designer", "running", "bai 3", 300, 301, None, None, None),
        ])
        try:
            ra = ha.viec(vai="designer")
            assert [v["id"] for v in ra] == ["t1", "t3"], ra
            assert ra[0]["tieu_de"] == "bai 1" and ra[0]["trang_thai"] == "done", ra[0]
            moi = ha.viec(vai="designer", so=1, moi_truoc=True)
            assert [v["id"] for v in moi] == ["t3"], moi
        finally:
            _go()


def test_viec_loc_theo_moc_thoi_gian():
    with tempfile.TemporaryDirectory() as tmp:
        _db(tmp, tasks=[
            ("t1", "a", "done", "cu", 100, None, None, None, None),
            ("t2", "a", "done", "moi", 500, None, None, None, None),
        ])
        try:
            assert [v["id"] for v in ha.viec(tu_ts=200)] == ["t2"]
        finally:
            _go()


def test_trang_thai_va_dem_dang_chay():
    with tempfile.TemporaryDirectory() as tmp:
        _db(tmp, tasks=[
            ("t1", "a", "ready", "x", 100, None, None, None, None),
            ("t2", "a", "running", "y", 200, None, None, None, None),
            ("t3", "a", "done", "z", 300, None, None, None, None),
        ])
        try:
            assert ha.trang_thai("t2") == "running"
            assert ha.trang_thai("khong-co") == "", "task khong co phai la '' "
            assert ha.dem_dang_chay() == 2, "chi ready+running moi tinh"
            assert ha.dem_dang_chay(tru_tid="t1") == 1, "phai tru chinh no ra"
        finally:
            _go()


def test_lan_chay_cuoi_lay_ban_moi_nhat_va_doc_metadata():
    with tempfile.TemporaryDirectory() as tmp:
        _db(tmp,
            tasks=[("t1", "a", "done", "x", 100, None, None, None, None)],
            runs=[(1, "t1", "failed", "lan dau", "vo", None),
                  (2, "t1", "done", "lan hai", None, json.dumps({"kind": "ok"}))])
        try:
            r = ha.lan_chay_cuoi("t1")
            assert r["tom_tat"] == "lan hai", r
            assert r["metadata"] == {"kind": "ok"}, r
        finally:
            _go()


def test_metadata_hong_thi_thanh_dict_rong_khong_nem():
    """hermes da tung ghi metadata la NULL lan chuoi khong phai JSON."""
    with tempfile.TemporaryDirectory() as tmp:
        _db(tmp,
            tasks=[("t1", "a", "done", "x", 100, None, None, None, None)],
            runs=[(1, "t1", "done", "s", None, "khong-phai-json")])
        try:
            assert ha.lan_chay_cuoi("t1")["metadata"] == {}
        finally:
            _go()


def test_lan_chay_cuoi_task_chua_chay_la_dict_rong():
    with tempfile.TemporaryDirectory() as tmp:
        _db(tmp, tasks=[("t1", "a", "ready", "x", 100, None, None, None, None)])
        try:
            assert ha.lan_chay_cuoi("t1") == {}, "chua chay != khong doc duoc"
        finally:
            _go()


def test_lan_chay_cuoi_nhieu_lay_dung_ban_cuoi_cua_tung_task():
    with tempfile.TemporaryDirectory() as tmp:
        _db(tmp,
            tasks=[("t1", "a", "done", "x", 1, None, None, None, None),
                   ("t2", "a", "done", "y", 2, None, None, None, None)],
            runs=[(1, "t1", "failed", "t1 cu", None, None),
                  (2, "t2", "done", "t2 chi mot lan", None, None),
                  (3, "t1", "done", "t1 moi", None, None)])
        try:
            ra = ha.lan_chay_cuoi_nhieu(["t1", "t2"])
            assert ra["t1"]["tom_tat"] == "t1 moi", ra
            assert ra["t2"]["tom_tat"] == "t2 chi mot lan", ra
        finally:
            _go()


# ------------------------------------------ khong doc duoc -> None (quy uoc C1)
def test_thieu_kanban_db_thi_tra_None_khong_phai_rong():
    """Diem cot loi cua C2/C1: "khong doc duoc kanban" phai KHAC "kanban rong".
    Truoc day cac cau SQL rai rac deu nuot loi va tra [] / 0, nen mot ngay
    kanban.db bien mat se doc y het mot ngay khong ai lam gi."""
    with tempfile.TemporaryDirectory() as tmp:
        ha.kanban_db = lambda: Path(tmp) / "khong-ton-tai.db"
        try:
            assert ha.viec() is None
            assert ha.mot_viec("t1") is None
            assert ha.trang_thai("t1") is None
            assert ha.dem_dang_chay() is None
            assert ha.lan_chay_cuoi("t1") is None
            assert ha.lan_chay_cuoi_nhieu(["t1"]) is None
        finally:
            _go()


def test_sai_schema_cung_tra_None():
    """hermes doi ten bang/cot -> phai lo ra, khong duoc im lang thanh rong."""
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "kanban.db"
        con = sqlite3.connect(p)
        con.execute("CREATE TABLE tasks (id TEXT, ten_moi TEXT)")   # thieu cot
        con.commit()
        con.close()
        ha.kanban_db = lambda: p
        try:
            assert ha.viec() is None, "doi schema ma van tra rong la hong cam"
        finally:
            _go()


# ------------------------------------------------------ tao_task (CLI hermes)
class _Ra:
    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def _tao_task(ket_qua, **kw):
    """Goi ha.tao_task voi subprocess gia. Tra (ket_qua_ham, args_da_chay)."""
    import subprocess
    da_chay = {}

    def _run(args, **k):
        da_chay["args"] = args
        da_chay["kw"] = k
        if isinstance(ket_qua, Exception):
            raise ket_qua
        return ket_qua
    cu = subprocess.run
    subprocess.run = _run
    try:
        return ha.tao_task("Anh: Tin X", "carousel", "than task", **kw), da_chay
    finally:
        subprocess.run = cu


def test_tao_task_doc_id_tu_json():
    (tid, loi), da = _tao_task(_Ra(0, '{"id": "t_42"}'))
    assert (tid, loi) == ("t_42", None), (tid, loi)
    a = da["args"]
    assert "kanban" in a and "create" in a and "--json" in a, a
    assert a[a.index("--assignee") + 1] == "carousel", a
    assert a[a.index("--workspace") + 1].startswith("dir:"), \
        "phai dung workspace CO DINH — scratch lam vo cache prompt (do 05/09)"


def test_tao_task_nhieu_cha_thi_lap_lai_co_parent():
    """Miles co HAI cha: task Dre + the goc bang den."""
    _kq, da = _tao_task(_Ra(0, '{"id": "t_1"}'), parent=["t_dre", "t_goc"])
    a = da["args"]
    assert [a[i + 1] for i, x in enumerate(a) if x == "--parent"] == ["t_dre", "t_goc"], a


def test_tao_task_mot_cha_dang_chuoi_cung_duoc():
    _kq, da = _tao_task(_Ra(0, '{"id": "t_1"}'), parent="t_goc")
    a = da["args"]
    assert [a[i + 1] for i, x in enumerate(a) if x == "--parent"] == ["t_goc"], a


def test_tao_task_rc_khac_0_thi_tra_loi_khong_nem():
    (tid, loi), _da = _tao_task(_Ra(2, "", "kanban tu choi"))
    assert tid is None and "kanban tu choi" in loi, (tid, loi)


def test_tao_task_json_hong_thi_tra_loi_khong_nem():
    (tid, loi), _da = _tao_task(_Ra(0, "khong phai json"))
    assert tid is None and "khong phai json" in loi, (tid, loi)


def test_tao_task_subprocess_nem_thi_van_tra_loi():
    """Thieu python cua hermes / het tien trinh: khong duoc nem len vong poll."""
    import subprocess
    (tid, loi), _da = _tao_task(subprocess.TimeoutExpired("x", 120))
    assert tid is None and "TimeoutExpired" in loi, (tid, loi)


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
