#!/usr/bin/env python3
"""LOW-26 (12/09/2026): khoa `dang_chay.pid` cua engine chuan bi anh.

t_24b214a6: ethan_prepare.py chet SIGSEGV (exit 139) ba lan, khoa nam lai; lan
chay dau doi tron 300s (= tran bash tool cua vai) roi bi cat `exit 124`. Test:
  - khoa mo coi (pid chet) -> don NGAY, khong ngu mot giay nao, co dong log;
  - pid con song -> doi toi `cho` roi thoat bang SystemExit, KHONG ghi de khoa;
  - `cho` mac dinh phai nho han han 300.
Fail tren code cu (khong co _handle_lock; cho=300), pass tren code moi.

Chay:  venv/bin/python tests/test_lock_prepare.py
"""
import io
import os
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_prepare as cb                                    # noqa: E402


def test_wait_default_small_limit_ceiling_bash_of_role():
    assert cb.WAIT_LOCK_SECONDS <= 60, cb.WAIT_LOCK_SECONDS
    assert cb.run.__defaults__[2] == cb.WAIT_LOCK_SECONDS        # (lam_moi, khong_browser, cho, ...)


def test_lock_orphan_single_date_no_change():
    with tempfile.TemporaryDirectory() as tmp:
        khoa = Path(tmp) / "dang_chay.pid"
        khoa.write_text("999999999")                          # pid khong ton tai
        ngu = []
        err = io.StringIO()
        with redirect_stderr(err):
            cb._handle_lock(khoa, 60, "draft-x", ngu=lambda s: ngu.append(s))
        assert not khoa.exists(), "khoa mo coi phai bi don"
        assert ngu == [], f"khong duoc ngu: {ngu}"
        assert "mo coi" in err.getvalue(), err.getvalue()


def test_pid_alive_then_change_fall_exit_no_overwrite():
    with tempfile.TemporaryDirectory() as tmp:
        khoa = Path(tmp) / "dang_chay.pid"
        khoa.write_text(str(os.getpid()))                    # chinh minh: chac chan song
        ngu = []
        # `ngu` gia: moi lan goi dich dong ho ao bang cach ghi lai; het `cho` nho
        cb.time_goc = cb.time
        t = [0.0]

        class _T:
            @staticmethod
            def time():
                return t[0]

            @staticmethod
            def sleep(s):
                ngu.append(s)
                t[0] += s
        cb.time = _T
        try:
            with redirect_stderr(io.StringIO()):
                try:
                    cb._handle_lock(khoa, 7, "draft-x", ngu=_T.sleep)
                    raise AssertionError("phai thoat bang SystemExit")
                except SystemExit as e:
                    assert "van dang chuan bi" in str(e), str(e)
        finally:
            cb.time = cb.time_goc
        assert khoa.exists() and khoa.read_text() == str(os.getpid()), "khong duoc ghi de/xoa khoa cua pid song"
        assert ngu, "phai co doi"


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
