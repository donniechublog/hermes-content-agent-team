#!/usr/bin/env python3
"""Mot cho duy nhat nap bien moi truong tu cac tep .env cua du an.

Vi sao gom lai: truoc day sau tep tu viet lai doan nay, va chung KHONG giong
nhau — `publish.py` va `approve_service.py` chi doc `.secrets.env`, bon tep con
lai doc ca `~/.hermes/.env`. Ai sua mot cho thi nam cho kia lech.

Nguy hiem hon: `~/.hermes/.env` co dong `TELEGRAM_BOT_TOKEN=` DE RONG CO Y —
de tat Telegram cua gateway. Cac ban cu chi khong dinh bay nho doc `.secrets.env`
TRUOC roi mai doc `.env`, cong voi `setdefault`. Chi can ai do doi thu tu hai
dong do la token that bi gia tri rong che mat, va canh bao chet CAM — dung loai
loi im lang ma du an nay da dinh nhieu lan.

Nen bo nap nay BO QUA GIA TRI RONG. Nho vay ket qua khong con phu thuoc thu tu:
mot bien duoc dat rong o tep nay khong bao gio de len gia tri that o tep kia.
"""
import os
from pathlib import Path

# Thu tu uu tien: tep dung truoc thang. Gia tri rong luon bi bo qua.
TEP_ENV = (
    Path.home() / "content-team" / ".secrets.env",
    Path.home() / ".hermes" / ".env",
)


def nap(*them: Path) -> None:
    """Nap TEP_ENV (va cac tep truyen them) vao os.environ.

    Khong ghi de bien da co san trong moi truong, va khong bao gio dat mot
    bien thanh chuoi rong.
    """
    for p in tuple(TEP_ENV) + tuple(them):
        if not p or not p.exists():
            continue
        for dong in p.read_text(encoding="utf-8").splitlines():
            dong = dong.strip()
            if not dong or dong.startswith("#") or "=" not in dong:
                continue
            k, v = dong.split("=", 1)
            k, v = k.strip(), v.strip()
            if not k or not v:            # gia tri rong: bo qua, xem muc dich o docstring
                continue
            os.environ.setdefault(k, v)


def bat_buoc(ten: str) -> str:
    """Nap roi lay mot bien bat buoc; thieu thi dung han voi loi ro rang."""
    nap()
    gt = os.environ.get(ten)
    if not gt:
        raise SystemExit(f"Thieu {ten} — kiem tra {' hoac '.join(str(p) for p in TEP_ENV)}")
    return gt
