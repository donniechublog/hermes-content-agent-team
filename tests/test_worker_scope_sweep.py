#!/usr/bin/env python3
"""`worker_scope_sweep` — stop scope worker kanban mo coi (LOW-126).

Diem phai giu: chi stop khi CHAC task da roi run cua scope du lau. Worker dang
chay, run vua dong, khong doc duoc DB, khong thay task -> KHONG stop — giet
nham worker dang chay la mat bai, con de sot mot scope chi ton ~11 MB.

Chay:  venv/bin/python tests/test_worker_scope_sweep.py
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import worker_scope_sweep as ws                               # noqa: E402

NOW = 1_000_000


def _db(tmp, ten, tasks=(), runs=()):
    """kanban.db gia: tasks(id, status, current_run_id), task_runs(id, task_id, ended_at)."""
    p = Path(tmp) / f"{ten}.db"
    con = sqlite3.connect(p)
    con.execute("CREATE TABLE tasks (id TEXT PRIMARY KEY, status TEXT, current_run_id INTEGER)")
    con.execute("CREATE TABLE task_runs (id INTEGER PRIMARY KEY, task_id TEXT, ended_at INTEGER)")
    con.executemany("INSERT INTO tasks VALUES (?,?,?)", tasks)
    con.executemany("INSERT INTO task_runs VALUES (?,?,?)", runs)
    con.commit()
    con.close()
    return (ten, p)


class _Ra:
    def __init__(self, rc=0, out="", err=""):
        self.returncode, self.stdout, self.stderr = rc, out, err


def _systemctl(units, stop_rc=0):
    """subprocess.run gia: list-units tra `units`, ghi lai moi lenh stop."""
    da_stop = []

    def run(args, **k):
        if "list-units" in args:
            return _Ra(0, "".join(f"{u} loaded active running hermes -p x\n" for u in units))
        if "stop" in args:
            da_stop.append(args[-1])
            return _Ra(stop_rc, "", "that bai" if stop_rc else "")
        raise AssertionError(args)
    return run, da_stop


U = "hermes-worker-kanban-t_7fb5375f-run-204.scope"


def test_task_done_run_dong_lau_thi_stop():
    with tempfile.TemporaryDirectory() as t:
        homes = [_db(t, "blog"), _db(t, "dcgr", [("t_7fb5375f", "done", None)], [(204, "t_7fb5375f", NOW - 3600)])]
        run, da = _systemctl([U])
        assert ws.main([], run=run, homes=homes, now=NOW) == 0
        assert da == [U], da


def test_dang_chay_thi_giu():
    with tempfile.TemporaryDirectory() as t:
        homes = [_db(t, "dcgr", [("t_7fb5375f", "running", 204)], [(204, "t_7fb5375f", None)])]
        run, da = _systemctl([U])
        ws.main([], run=run, homes=homes, now=NOW)
        assert da == [], da


def test_run_vua_dong_trong_grace_thi_giu():
    with tempfile.TemporaryDirectory() as t:
        homes = [_db(t, "dcgr", [("t_7fb5375f", "done", None)], [(204, "t_7fb5375f", NOW - 30)])]
        run, da = _systemctl([U])
        ws.main([], run=run, homes=homes, now=NOW)
        assert da == [], "worker vua complete con dang thoat, khong giet ngang"


def test_run_cu_da_bi_thay_boi_run_moi_thi_stop_scope_cu():
    """Task reclaim roi chay lai: run 204 dong, run 205 dang chay -> scope 204 mo coi."""
    with tempfile.TemporaryDirectory() as t:
        homes = [_db(t, "dcgr", [("t_7fb5375f", "running", 205)],
                     [(204, "t_7fb5375f", NOW - 3600), (205, "t_7fb5375f", None)])]
        u205 = U.replace("204", "205")
        run, da = _systemctl([U, u205])
        ws.main([], run=run, homes=homes, now=NOW)
        assert da == [U], da


def test_khong_thay_task_hoac_run_chua_dong_thi_giu():
    with tempfile.TemporaryDirectory() as t:
        homes = [_db(t, "blog"), _db(t, "dcgr", [("t_7fb5375f", "blocked", None)])]
        run, da = _systemctl([U, "hermes-worker-kanban-t_abc-run-1.scope"])
        ws.main([], run=run, homes=homes, now=NOW)
        assert da == [], "run 204 khong co ended_at / t_abc khong co o dau -> khong biet thi khong giet"


def test_khong_doc_duoc_db_thi_giu():
    with tempfile.TemporaryDirectory() as t:
        homes = [("dcgr", Path(t) / "khong-co.db")]
        run, da = _systemctl([U])
        ws.main([], run=run, homes=homes, now=NOW)
        assert da == []


def test_dry_run_khong_stop():
    with tempfile.TemporaryDirectory() as t:
        homes = [_db(t, "dcgr", [("t_7fb5375f", "done", None)], [(204, "t_7fb5375f", NOW - 3600)])]
        run, da = _systemctl([U])
        assert ws.main(["--dry-run"], run=run, homes=homes, now=NOW) == 0
        assert da == []


def test_stop_that_bai_thi_ma_thoat_1():
    with tempfile.TemporaryDirectory() as t:
        homes = [_db(t, "dcgr", [("t_7fb5375f", "done", None)], [(204, "t_7fb5375f", NOW - 3600)])]
        run, _da = _systemctl([U], stop_rc=5)
        assert ws.main([], run=run, homes=homes, now=NOW) == 1


def test_bo_qua_unit_khong_dung_mau():
    run, _da = _systemctl(["hermes-worker-cron-x.scope", U])
    assert ws.list_scopes(run) == [(U, "t_7fb5375f", 204)]


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
