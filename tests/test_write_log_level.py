#!/usr/bin/env python3
"""Muc log cua write_log (LOW-305).

Truoc 20/09/2026 `write_log.log()` luon goi `.info`, ke ca 7 cho goi
`log("loi", ...)`. Hau qua do duoc: dong loi nam lan giua hang nghin dong INFO
trong `state/<brand>/approve.log`, khong loc ra duoc bang muc; va o journal thi
`journalctl -p err` tra ve RONG du dich vu dang bao loi — vi khong dong nao mang
muc err ca.

Test nay khoa ba thu:
  1. nhan `loi` ra ERROR, nhan thuong ra INFO, va NOI DUNG dong khong doi;
  2. `warn()`/`error()` ra dung muc, `level=` de nguoi goi ep muc khi nhan khong
     noi len dieu gi (`tele`, `kanban` dung chung cho ca dong tot lan dong hong);
  3. dong ra stdout mang tien to muc syslog `<N>` khi — va CHI khi — systemd dang
     doc dau ra (`JOURNAL_STREAM`), con dong ghi vao TEP thi khong.

Chay:  venv/bin/python tests/test_write_log_level.py
"""
import logging
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import write_log                                             # noqa: E402


class _Capture(logging.Handler):
    """Handler bo nho: giu nguyen ban ghi de doc lai muc va noi dung."""

    def __init__(self):
        super().__init__()
        self.records = []

    def emit(self, record):
        self.records.append(record)


def _fresh_logger(**env):
    """Dung lai logger tu dau voi MOT handler bo nho; tra (handler, ham tra lai).

    Phai tu dung vi `_LOG` la singleton va `_block_create_real` them handler moi
    lan goi — khong don thi lan chay thu hai nhan doi moi dong.
    """
    cu_log = write_log._LOG
    cu_env = {k: os.environ.get(k) for k in env}
    for k, v in env.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    lg = logging.getLogger("approve")
    cu_handlers = list(lg.handlers)
    write_log._LOG = None
    lg.handlers.clear()
    lg_that = write_log._block_create()
    cap = _Capture()
    lg_that.addHandler(cap)

    def restore():
        lg.handlers.clear()
        lg.handlers.extend(cu_handlers)
        write_log._LOG = cu_log
        for k, v in cu_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v

    return cap, restore


def _one_record(goi, **env):
    """Chay `goi(write_log)` roi tra ban ghi duy nhat sinh ra."""
    cap, restore = _fresh_logger(**env)
    try:
        goi(write_log)
        assert len(cap.records) == 1, f"mong dung 1 dong, duoc {len(cap.records)}"
        return cap.records[0]
    finally:
        restore()


def test_label_error_then_level_error():
    """Cho hong truoc 20/09: `log("loi", ...)` ra INFO nen khong loc duoc."""
    r = _one_record(lambda w: w.log("loi", "getUpdates tu choi: 409"))
    assert r.levelno == logging.ERROR, \
        f"nhan `loi` phai la ERROR, dang la {logging.getLevelName(r.levelno)}"
    assert r.getMessage() == "[loi] getUpdates tu choi: 409", r.getMessage()


def test_label_normal_then_level_info_and_content_same():
    """Moi cho goi cu phai giu nguyen hanh vi — noi dung y het, van INFO."""
    r = _one_record(lambda w: w.log("route", "update 12 -> chon"))
    assert r.levelno == logging.INFO, logging.getLevelName(r.levelno)
    assert r.getMessage() == "[route] update 12 -> chon", r.getMessage()


def test_newline_then_still_one_line():
    """Xuong dong van bi doi thanh ⏎ — mot su kien mot dong, khong doi."""
    r = _one_record(lambda w: w.log("vao", "dong 1\ndong 2"))
    assert r.getMessage() == "[vao] dong 1 ⏎ dong 2", r.getMessage()


def test_warn_and_error_then_right_level():
    assert _one_record(lambda w: w.warn("start", "tirith TAT")).levelno == logging.WARNING
    assert _one_record(lambda w: w.error("tele", "sendMessage tu choi")).levelno == logging.ERROR


def test_level_given_then_override_label_map():
    """`level=` thang bang nhan: nhan `loi` van ep xuong WARNING duoc."""
    r = _one_record(lambda w: w.log("loi", "thu lai duoc", logging.WARNING))
    assert r.levelno == logging.WARNING, logging.getLevelName(r.levelno)


def test_unknown_label_then_info_not_crash():
    """Nhan la nao khong co trong bang thi INFO, khong no."""
    r = _one_record(lambda w: w.log("nhan_chua_tung_co", "x"))
    assert r.levelno == logging.INFO, logging.getLevelName(r.levelno)


def _stdout_format(**env):
    """Tra (formatter cua handler stdout, chuoi da dinh dang cua mot dong ERROR)."""
    cap, restore = _fresh_logger(**env)
    try:
        lg = logging.getLogger("approve")
        ra = [h for h in lg.handlers
              if isinstance(h, logging.StreamHandler) and h.stream is sys.stdout]
        assert len(ra) == 1, f"mong dung 1 handler stdout, co {len(ra)}"
        write_log.log("loi", "hong")
        return ra[0].formatter, ra[0].formatter.format(cap.records[0])
    finally:
        restore()


def test_format_then_has_level_name():
    """Dinh dang phai co ten muc — khong thi doc log van phai doan theo nhan chu."""
    _, dong = _stdout_format(JOURNAL_STREAM=None)
    assert "ERROR" in dong, dong
    assert "[loi] hong" in dong, dong


def test_no_journal_stream_then_no_syslog_prefix():
    """Chay tay/trong test: khong duoc thay `<3>` trong terminal."""
    fmt, dong = _stdout_format(JOURNAL_STREAM=None)
    assert not isinstance(fmt, write_log.JournalLevelPrefix), type(fmt)
    assert not dong.startswith("<"), dong


def test_journal_stream_then_syslog_prefix_error_is_3():
    """Duoi systemd: khong co tien to thi `journalctl -p err` rong (do 20/09/2026
    tren may chu — systemd 255, hermes-approve@ co SyslogLevelPrefix=yes)."""
    fmt, dong = _stdout_format(JOURNAL_STREAM="9:12345")
    assert isinstance(fmt, write_log.JournalLevelPrefix), type(fmt)
    assert dong.startswith("<3>"), dong
    assert "ERROR" in dong, dong


def test_journal_stream_then_info_is_6():
    cap, restore = _fresh_logger(JOURNAL_STREAM="9:12345")
    try:
        lg = logging.getLogger("approve")
        ra = [h for h in lg.handlers
              if isinstance(h, logging.StreamHandler) and h.stream is sys.stdout][0]
        write_log.log("route", "binh thuong")
        assert ra.formatter.format(cap.records[0]).startswith("<6>"), \
            ra.formatter.format(cap.records[0])
    finally:
        restore()


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
