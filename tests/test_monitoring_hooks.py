#!/usr/bin/env python3
"""Ba lop "bao loi" cua D17 (audit 30/09/2026) — khoa bang vat that, khong bang tai lieu.

  1. hermes-approve@.service co `OnFailure=` tro toi mot unit CO THAT, va co gioi han khoi
     dong (khong co no thi `Restart=always` khong bao gio sang `failed`, OnFailure chet);
  2. notify-fail.sh cu phap dung, luon exit 0 va dong dau mang tien to `<3>` (muc err);
  3. `write_log.run_cli` ghi ERROR cho `sys.exit(<chuoi>)` NHUNG giu nguyen chuoi + ma
     thoat, va khong ghi gi cho ket qua binh thuong / ma so;
  4. journal_web: docstring khong noi 0.0.0.0 la mac dinh khi code la 127.0.0.1.

Chay:  venv/bin/python tests/test_monitoring_hooks.py
"""
import logging
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
SYSTEMD = ROOT / "hermes" / "systemd"


def test_approve_unit_has_onfailure_and_start_limit():
    vb = (SYSTEMD / "hermes-approve@.service").read_text(encoding="utf-8")
    dong = [d.strip() for d in vb.splitlines() if d.strip() and not d.strip().startswith("#")]
    assert "OnFailure=notify-fail@%n.service" in dong
    assert any(d.startswith("StartLimitIntervalSec=") for d in dong), \
        "thieu StartLimitIntervalSec: Restart=always khong bao gio thanh `failed`"
    assert any(d.startswith("StartLimitBurst=") for d in dong)
    unit = SYSTEMD / "notify-fail@.service"
    assert unit.exists(), "OnFailure tro toi unit khong co trong repo"
    assert "notify-fail.sh" in unit.read_text(encoding="utf-8")
    assert (SYSTEMD / "notify-fail.sh").exists()


def test_notify_fail_script_syntax_and_exit_0():
    sh = SYSTEMD / "notify-fail.sh"
    assert subprocess.run(["/bin/sh", "-n", str(sh)]).returncode == 0
    with tempfile.TemporaryDirectory() as home:      # HOME rong: khong co python -> khong gui Telegram
        r = subprocess.run(["/bin/sh", str(sh), "hermes-approve@blog.service"],
                           capture_output=True, text=True, env={"HOME": home, "PATH": os.environ["PATH"]})
    assert r.returncode == 0, r.stderr
    dau = r.stdout.splitlines()[0]
    assert dau.startswith("<3>notify-fail:") and "hermes-approve@blog.service" in dau, dau
    r = subprocess.run(["/bin/sh", str(sh)], capture_output=True, text=True)   # thieu doi so
    assert r.returncode == 0


def _run_cli(main, monkey_argv="foo_submit.py"):
    """Chay write_log.run_cli voi handler bo nho, tra ve (ket qua/SystemExit, ban ghi)."""
    import write_log

    class Cap(logging.Handler):
        def __init__(self):
            super().__init__()
            self.records = []

        def emit(self, record):
            self.records.append(record)

    cap = Cap()
    lg = write_log._block_create()
    lg.addHandler(cap)
    cu = sys.argv
    sys.argv = [monkey_argv]
    try:
        try:
            res = write_log.run_cli(main)
        except SystemExit as e:
            res = e
    finally:
        sys.argv = cu
        lg.removeHandler(cap)
    return res, cap.records


def test_run_cli_log_error_but_keep_message_and_exit_code():
    def loi():
        sys.exit("[LOI] khong thay tep: x.png")
    res, ban_ghi = _run_cli(loi)
    assert isinstance(res, SystemExit) and res.code == "[LOI] khong thay tep: x.png", res
    assert [r.levelno for r in ban_ghi] == [logging.ERROR]
    assert "foo_submit.py" in ban_ghi[0].getMessage() and "khong thay tep: x.png" in ban_ghi[0].getMessage()


def test_run_cli_no_log_for_ok_result_and_numeric_exit():
    assert _run_cli(lambda: 0) == (0, [])
    res, ban_ghi = _run_cli(lambda: sys.exit(2))
    assert isinstance(res, SystemExit) and res.code == 2 and ban_ghi == []
    res, ban_ghi = _run_cli(lambda: sys.exit(None))
    assert isinstance(res, SystemExit) and res.code is None and ban_ghi == []


def test_all_submit_scripts_use_run_cli():
    thieu = [p.name for p in sorted(ROOT.glob("*_submit.py"))
             if "write_log.run_cli(main)" not in p.read_text(encoding="utf-8")]
    assert not thieu, f"script vai chua boc write_log.run_cli: {thieu}"


def test_journal_web_docstring_match_code_host():
    import journal_web
    assert journal_web.HOST == "127.0.0.1" or "JOURNAL_WEB_HOST" in os.environ
    doc = journal_web.__doc__
    assert "mặc định 127.0.0.1" in doc and "mặc định 0.0.0.0" not in doc


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
