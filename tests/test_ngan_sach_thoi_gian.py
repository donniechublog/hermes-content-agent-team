#!/usr/bin/env python3
"""LOW-25 (12/09/2026): ngan sach thoi gian theo vai + tran cho `_cho_luot`, va
bat bien "hen gio trong < hen gio ngoai" (INV-4).

Do may chu 14 ngay: dre/kite p95 ~23 phut, sat tran 25m dung chung; ethan <= 8.
Fail tren code cu (khong co max_runtime_cua / WAIT_SLOT_SECONDS), pass tren code moi.

Chay:  venv/bin/python tests/test_ngan_sach_thoi_gian.py
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

TRAN_BASH_GIAY = 300          # bash tool cua hermes cat o ~300s (t_24b214a6: exit 124)


def _phut(s: str) -> int:
    return int(s[:-1]) * (60 if s.endswith("h") else 1)


def test_vai_anh_40m_vai_khac_25m():
    assert role.max_runtime_for("ethan") == "40m"
    assert role.max_runtime_for("dre") == "40m"
    assert role.max_runtime_for("kite") == "40m"
    assert role.max_runtime_for("miles") == "25m"
    assert role.max_runtime_for("designer") == "40m"      # slug cu cung ra dung vai
    assert role.max_runtime_for("khong-ton-tai") == "25m"


def test_kanban_create_truyen_max_runtime_theo_vai():
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


def test_bat_bien_hen_gio_trong_nho_hon_hen_gio_ngoai():
    assert cb.WAIT_LOCK_SECONDS < TRAN_BASH_GIAY
    assert cb.WAIT_SLOT_SECONDS < TRAN_BASH_GIAY
    # canh bao "chay lau" phai den TRUOC khi hermes giet, voi MOI vai
    for slug in role.ROLE:
        assert dg.THRESHOLD_STALLED_MINUTES < _phut(role.max_runtime_for(slug)), slug


def test_cho_luot_het_gio_thi_thoat_co_cau_bao_dinh_ky():
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
    fh = open(thu_muc / "chuan_bi.0.lock", "w")
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
