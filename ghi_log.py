#!/usr/bin/env python3
"""Log dung chung cho approve_service / chat_router: ra stdout (journal) VA ra
tep `state/<brand>/approve.log` (xoay vong, 5 MB x 3).

Vi sao can: truoc 03/09/2026 approve_service chi in khi loi o vong poll. Tin
nhan vao, quyet dinh dinh tuyen (chon so / chat / lenh), ket qua goi agent,
tin gui di — khong dong nao. Khi Ong Chu bao "vai khong tra loi" thi khong co
gi de doi chieu, phai mo state.db cua tung profile ma doan. Moi tin nhan vao
gio de lai it nhat mot dong o day, va moi dong co ma tin (update/message id)
de noi cac buoc lai voi nhau.
"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402

_LOG = None
_KHOA = __import__("threading").Lock()


def _khoi_tao():
    if _LOG is not None:
        return _LOG
    with _KHOA:                      # nhieu thread cung khoi tao -> handler lap 3 lan
        if _LOG is not None:
            return _LOG
        return _khoi_tao_that()


def _khoi_tao_that():
    global _LOG
    lg = logging.getLogger("approve")
    lg.setLevel(logging.INFO)
    lg.propagate = False
    fmt = logging.Formatter("%(asctime)s %(message)s", "%m-%d %H:%M:%S")
    ra = logging.StreamHandler(sys.stdout)
    ra.setFormatter(fmt)
    lg.addHandler(ra)
    try:
        tep = env_load.state_dir() / "approve.log"
        fh = RotatingFileHandler(tep, maxBytes=5_000_000, backupCount=3,
                                 encoding="utf-8")
        fh.setFormatter(fmt)
        lg.addHandler(fh)
    except OSError as e:                     # khong ghi tep duoc thi van con stdout
        lg.warning("[log] khong mo duoc tep log: %s", e)
    _LOG = lg
    return lg


def log(nhan: str, noi_dung: str) -> None:
    """Mot dong log: `[nhan] noi_dung`. Nhan la buoc (vao/route/chat/gui/loi...)."""
    _khoi_tao().info("[%s] %s", nhan, noi_dung.replace("\n", " ⏎ "))


def rut(text, n: int = 90) -> str:
    """Rut gon chuoi de log, khong log ca bai."""
    t = (text or "").replace("\n", " ")
    return t if len(t) <= n else t[: n - 1] + "…"


def brand() -> str:
    return os.environ.get("CT_BRAND", "") or "don"
