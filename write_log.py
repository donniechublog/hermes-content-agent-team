#!/usr/bin/env python3
"""Log dung chung cho approve_service / chat_router: ra stdout (journal) VA ra
tep `state/<brand>/approve.log` (xoay vong, 5 MB x 3).

Vi sao can: truoc 03/09/2026 approve_service chi in khi loi o vong poll. Tin
nhan vao, quyet dinh dinh tuyen (chon so / chat / lenh), ket qua goi agent,
tin gui di — khong dong nao. Khi Ong Chu bao "vai khong tra loi" thi khong co
gi de doi chieu, phai mo state.db cua tung profile ma doan. Moi tin nhan vao
gio de lai it nhat mot dong o day, va moi dong co ma tin (update/message id)
de noi cac buoc lai voi nhau.

MUC LOG (LOW-305, 20/09/2026). Truoc do MOI dong — ke ca `log("loi", ...)` — ra o
muc INFO, nen khong loc duoc "chi loi": `grep` tren approve.log phai doan theo
nhan chu, con `journalctl -p err` tra ve rong. Gio dong log co ten muc, va nhan
nao la loi thi khai o MOT cho (`ERROR_LABELS`) thay vi sua rai rac tung cho goi.
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402

# Nhan nao TU NO da la loi. Mot cho duy nhat: 7 cho goi `log("loi", ...)` khong
# phai sua, va them mot nhan loi moi thi them o day chu khong doi tung cho goi.
# Nhan dung chung cho ca dong tot lan dong hong (`tele`, `kanban`, `start`) khong
# vao day duoc — cho goi phai tu khai muc bang `warn()` / `error()`.
ERROR_LABELS = frozenset({"loi"})

# systemd doc tien to `<N>` (muc syslog) o dau dong stdout khi `SyslogLevelPrefix=yes`.
# Da DO tren may chu 20/09/2026: systemd 255, `hermes-approve@` co
# StandardOutput=journal va SyslogLevelPrefix=yes. Khong co tien to thi moi dong vao
# journal deu la muc info, tuc `journalctl -p err` van rong du dong do la loi.
# Chi bat khi systemd that su dang doc dau ra: no dat JOURNAL_STREAM cho tien trinh
# con. Chay tay hoac trong test khong co bien do nen khong thay `<3>` trong terminal.
_SYSLOG_BY_LEVEL = {logging.CRITICAL: 2, logging.ERROR: 3, logging.WARNING: 4,
                    logging.INFO: 6, logging.DEBUG: 7}


class JournalLevelPrefix(logging.Formatter):
    """Nhu Formatter thuong, them tien to muc syslog cho journald doc ra muc."""

    def format(self, record):
        return f"<{_SYSLOG_BY_LEVEL.get(record.levelno, 6)}>" + super().format(record)


_LOG = None
_KHOA = __import__("threading").Lock()


def _block_create():
    if _LOG is not None:
        return _LOG
    with _KHOA:                      # nhieu thread cung khoi tao -> handler lap 3 lan
        if _LOG is not None:
            return _LOG
        return _block_create_real()


def _block_create_real():
    global _LOG
    lg = logging.getLogger("approve")
    lg.setLevel(logging.INFO)
    lg.propagate = False
    # `-7s`: INFO/ERROR/WARNING lech nhau do dai, cot khong thang thi doc kem.
    mau = "%(asctime)s %(levelname)-7s %(message)s"
    fmt = logging.Formatter(mau, "%m-%d %H:%M:%S")
    ra = logging.StreamHandler(sys.stdout)
    # Tien to `<N>` CHI ra stdout (journald doc), khong ghi vao tep log.
    ra.setFormatter(JournalLevelPrefix(mau, "%m-%d %H:%M:%S")
                    if os.environ.get("JOURNAL_STREAM") else fmt)
    lg.addHandler(ra)
    # Chi ghi ra TEP khi co CT_BRAND, tuc dang chay that trong mot container
    # (systemd/cron dat san bien nay). Test va script chay tay khong co no, va
    # truoc 09/09/2026 chung ghi thang vao `state/approve.log` that: mot lan
    # chay tests/ de lai vai chuc dong lan trong nhat ky cua dich vu that, doc
    # log su co xong phai loc bo tay. Mat tep log o che do don la chap nhan
    # duoc — stdout van con nguyen (journald cua systemd bat cai do).
    if os.environ.get("CT_BRAND", "").strip():
        try:
            tep = env_load.state_dir() / "approve.log"
            fh = RotatingFileHandler(tep, maxBytes=5_000_000, backupCount=3,
                                     encoding="utf-8")
            fh.setFormatter(fmt)
            lg.addHandler(fh)
        except OSError as e:                 # khong ghi tep duoc thi van con stdout
            lg.warning("[log] khong mo duoc tep log: %s", e)
    _LOG = lg
    return lg


def log(nhan: str, noi_dung: str, level: int | None = None) -> None:
    """Mot dong log: `[nhan] noi_dung`. Nhan la buoc (vao/route/chat/gui/loi...).

    `level` bo trong thi lay theo nhan (`ERROR_LABELS`), khong co trong bang thi
    INFO — nen moi cho goi cu giu nguyen hanh vi, tru `log("loi", ...)` nay len ERROR.
    """
    lv = (logging.ERROR if nhan in ERROR_LABELS else logging.INFO) if level is None else level
    _block_create().log(lv, "[%s] %s", nhan, noi_dung.replace("\n", " ⏎ "))


def warn(nhan: str, noi_dung: str) -> None:
    """Chuyen nhe: dich vu van chay nhung co thu dang tat/thieu, can ai do nhin."""
    log(nhan, noi_dung, logging.WARNING)


def error(nhan: str, noi_dung: str) -> None:
    """Dung khi nhan KHONG phai `loi` ma dong nay van la loi."""
    log(nhan, noi_dung, logging.ERROR)


def shorten(text, n: int = 90) -> str:
    """Rut gon chuoi de log, khong log ca bai."""
    t = (text or "").replace("\n", " ")
    return t if len(t) <= n else t[: n - 1] + "…"


def brand() -> str:
    return os.environ.get("CT_BRAND", "") or "don"
