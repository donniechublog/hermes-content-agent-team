#!/usr/bin/env python3
"""LOW-25 (12/09/2026): ngan sach thoi gian theo vai + tran cho `_wait_for_slot`, va
bat bien "hen gio trong < hen gio ngoai" (INV-4).

Do may chu 14 ngay: dre/kite p95 ~23 phut, sat tran 25m dung chung; ethan <= 8.
Fail tren code cu (khong co max_runtime_for / WAIT_SLOT_SECONDS), pass tren code moi.

Chay:  venv/bin/python tests/test_budget_time.py
"""
import io
import sys
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_prepare as cb                                    # noqa: E402
import approve_dispatch as dg                                 # noqa: E402
import role                                                   # noqa: E402
import state_paths                                            # noqa: E402

TRAN_BASH_GIAY = 300          # bash tool cua hermes cat o ~300s (t_24b214a6: exit 124)


def _minutes(s: str) -> int:
    return int(s[:-1]) * (60 if s.endswith("h") else 1)


def test_role_image_40m_role_other_25m():
    assert role.max_runtime_for("ethan") == "40m"
    assert role.max_runtime_for("dre") == "40m"
    assert role.max_runtime_for("kite") == "40m"
    assert role.max_runtime_for("miles") == "25m"
    assert role.max_runtime_for("designer") == "40m"      # slug cu cung ra dung vai
    assert role.max_runtime_for("khong-ton-tai") == "25m"


def test_kanban_create_transmit_max_runtime_by_role():
    goi = {}
    cu = (dg.hermes_adapter.create_task, dg.standard_assignee)
    dg.hermes_adapter.create_task = lambda *a, **k: (goi.update(k) or ("t_x", None))
    dg.standard_assignee = lambda a: (a, None)               # khong can profile that
    try:
        tid, loi = dg.kanban_create("Anh: tin X", "ethan", "than")
    finally:
        dg.hermes_adapter.create_task, dg.standard_assignee = cu
    assert tid == "t_x" and loi is None, (tid, loi)
    assert goi.get("max_runtime") == "40m", goi


def test_catch_variable_timer_hours_within_small_than_timer_hours_outside():
    assert cb.WAIT_LOCK_SECONDS < TRAN_BASH_GIAY
    assert cb.WAIT_SLOT_SECONDS < TRAN_BASH_GIAY
    # canh bao "chay lau" phai den TRUOC khi hermes giet, voi MOI vai
    for slug in role.ROLE:
        assert dg.THRESHOLD_STALLED_MINUTES < _minutes(role.max_runtime_for(slug)), slug


def test_engine_slots_match_worker_count():
    """LOW-290 (Ong Chu chot 20/09/2026): tran engine = so worker kanban toi da toan may.

    May chu 20/09: `kanban.max_in_progress: 3` moi brand x 2 brand = 6. Truoc do tran la
    2 (dat 05/09 khi moi brand chay 1 task) — tu 14/09 cau hinh thanh 3/brand thi 7 ngay
    sau do 95/126 draft phai xep hang va 56 draft chet o WAIT_SLOT_SECONDS. Ha con so nay
    lai = hang dai hon so cho, vai lai quay vong va chay het ngan sach luot.

    Do RAM 20/09 tren may 8GB: 6 phien Chromium kieu engine lam RAM kha dung tut ~1.9GB,
    con ~2.7GB + swap 3.3GB. Doi tran thi do lai, dung doan."""
    import os
    if os.environ.get("CT_PREPARE_PARALLEL"):
        return                                            # may nay dat tay, khong xet mac dinh
    assert cb.COUNT_ENGINE_PARALLEL == 6, cb.COUNT_ENGINE_PARALLEL


def test_wait_slot_all_done_hours_then_exit_has_sentence_report_fixed_ky():
    if cb.fcntl is None:
        return                                            # Windows: khong khoa
    import fcntl
    thu_muc = cb.ROOT / "state"
    thu_muc.mkdir(parents=True, exist_ok=True)
    cu = (cb.COUNT_ENGINE_PARALLEL, cb.WAIT_SLOT_SECONDS, cb._ngu, cb.time)
    t = [0.0]
    ngu = []

    class _T:
        @staticmethod
        def time():
            return t[0]

        @staticmethod
        def sleep(s):
            ngu.append(s); t[0] += s
    # giu chinh khoa so 0 trong test -> engine khong bao gio co cho
    fh = open(thu_muc / state_paths.LOCK_FILE.format(0), "w")
    fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    err = io.StringIO()
    try:
        cb.COUNT_ENGINE_PARALLEL, cb.WAIT_SLOT_SECONDS, cb._ngu, cb.time = 1, 70, _T.sleep, _T
        with redirect_stderr(err):
            try:
                with cb._wait_for_slot():
                    raise AssertionError("khong duoc vao khi het cho")
            except SystemExit as e:
                assert "chay lai sau" in str(e), str(e)
    finally:
        cb.COUNT_ENGINE_PARALLEL, cb.WAIT_SLOT_SECONDS, cb._ngu, cb.time = cu
        fcntl.flock(fh, fcntl.LOCK_UN); fh.close()
    bao = [l for l in err.getvalue().splitlines() if "doi toi luot" in l]
    assert len(bao) >= 3, err.getvalue()                  # 0s, 30s, 60s
    assert ngu, "phai co ngu gia"


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
