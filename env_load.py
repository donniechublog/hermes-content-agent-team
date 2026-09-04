#!/usr/bin/env python3
"""Mot cho duy nhat nap bien moi truong tu cac tep .env cua du an.

Vi sao gom lai: truoc day nhieu tep tu viet lai doan nay, va chung KHONG giong
nhau — ai sua mot cho thi nam cho kia lech.

Nguy hiem hon: `~/.hermes/.env` co dong `TELEGRAM_BOT_TOKEN=` DE RONG CO Y — de
tat Telegram cua gateway. Neu doc nham thu tu, token that bi gia tri rong che
mat va canh bao chet CAM. Nen nap nay BO QUA GIA TRI RONG: mot bien dat rong o
tep nay khong bao gio de len gia tri that o tep kia, va ket qua khong phu thuoc
thu tu.

KIEN TRUC CONTAINER (nhieu brand tren 1 ma nguon):
- Moi brand mot tep `secret.<key>.env` (key = bien moi truong `CT_BRAND`, vd
  'dcgr' | 'blog'), dung chung `secret.common.env`.
- Systemd/cron dat san `CT_BRAND` + `HERMES_HOME` cho tung container; cac gia tri
  do da nam trong os.environ nen `setdefault` o day khong de len chung.
- STATE per-brand: `state/<CT_BRAND>/` (offset, topics, dedup, manifest...) — xem
  `state_dir()`. Khong co `CT_BRAND` -> roi ve che do don cu (`.secrets.env`,
  `state/`), nen ma cu van chay binh thuong truoc khi cutover.
"""
import os
from pathlib import Path

_BASE = Path(__file__).resolve().parent


def _brand() -> str:
    """Khoa brand cua container hien tai ('dcgr' | 'blog'), rong neu che do don."""
    return os.environ.get("CT_BRAND", "").strip()


def _tep_env() -> tuple:
    """Danh sach tep .env theo thu tu uu tien (tep truoc thang qua setdefault)."""
    files = [_BASE / "secret.common.env"]
    key = _brand()
    if key:
        files.append(_BASE / f"secret.{key}.env")
    # Tuong thich nguoc: che do don truoc cutover van doc tep cu.
    files.append(_BASE / ".secrets.env")
    files.append(Path.home() / ".hermes" / ".env")
    return tuple(files)


def state_dir() -> Path:
    """Thu muc STATE RUNTIME cua brand (offset, dedup, manifest, drafts tam...).
    `state/<CT_BRAND>/` khi co CT_BRAND, nguoc lai `state/` (che do don cu).
    Bi gitignore (du lieu chay). Luon tao san thu muc."""
    d = _BASE / "state"
    key = _brand()
    if key:
        d = d / key
    d.mkdir(parents=True, exist_ok=True)
    return d


def topics_path() -> Path:
    """Duong dan tep anh xa topic cua brand. KHONG phai runtime — day la CAU HINH
    khong tai tao duoc (topic id trong group), NEN commit vao git: `state/
    topics.<CT_BRAND>.json` (da un-ignore). Che do don cu: `state/topics.json`."""
    base = _BASE / "state"
    key = _brand()
    return base / f"topics.{key}.json" if key else base / "topics.json"


def nap(*them: Path) -> None:
    """Nap cac tep .env vao os.environ.

    Khong ghi de bien da co san trong moi truong, va khong bao gio dat mot bien
    thanh chuoi rong.
    """
    for p in _tep_env() + tuple(them):
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
        raise SystemExit(
            f"Thieu {ten} — kiem tra secret.common.env / secret.<brand>.env "
            f"(hoac .secrets.env che do don)")
    return gt
