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
import json
import os
from pathlib import Path

_BASE = Path(__file__).resolve().parent
# Goc du an = thu muc chua tep nay. Truoc day 16 tep tu tinh `Path.home() /
# "content-team"` — dung tren server, sai o moi may khac (audit 05/09/2026).
ROOT = _BASE
HERMES_DIR = Path.home() / "hermes-agent"
HERMES_PY = HERMES_DIR / "venv" / "bin" / "python"
ROUTER_URL = "http://127.0.0.1:20128/v1/chat/completions"   # 9router cuc bo, chung hai brand
VISION_MODEL = "ds/deepseek-v4-flash-vision-exp"            # con mat cua engine anh (anh_chuan_bi)


def hermes_home() -> Path:
    """HERMES_HOME cua container hien tai (~/.hermes-<brand>, systemd/cron dat san);
    khong co bien thi roi ve ~/.hermes (che do don cu)."""
    return Path(os.environ.get("HERMES_HOME") or (Path.home() / ".hermes"))


def topics() -> dict:
    """Anh xa ten vai -> thread_id cua brand; rong neu tep thieu hoac hong."""
    try:
        return json.loads(topics_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


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


def album_phu(draft_id: str, thu_muc: Path = None) -> list:
    """Danh sach anh phu <draft_id>_2.png, _3.png... _10.png... sap dung so,
    khong theo thu tu chuoi.

    Truoc day 3 noi (draft_write, dre_nop, kite_nop) tu glob rieng bang mau
    `_[0-9].png` — chi khop MOT chu so nen bo sot slide thu 10 tro len. Bug
    that: Ong Chu duyet du 10 slide tren Telegram nhung album dang kenh chi
    con 9, vi draft_write doc thieu slide cuoi (audit 06/09/2026). Gom mot cho
    de sua mot lan, dung o ca ba noi."""
    d = thu_muc or (ROOT / "drafts")
    ung_vien = set(d.glob(f"{draft_id}_[0-9].png")) | set(d.glob(f"{draft_id}_[0-9][0-9].png"))

    def so(p: Path) -> int:
        try:
            return int(p.stem.rsplit("_", 1)[-1])
        except ValueError:
            return 0

    return sorted(ung_vien, key=so)


def bat_buoc(ten: str) -> str:
    """Nap roi lay mot bien bat buoc; thieu thi dung han voi loi ro rang."""
    nap()
    gt = os.environ.get(ten)
    if not gt:
        raise SystemExit(
            f"Thieu {ten} — kiem tra secret.common.env / secret.<brand>.env "
            f"(hoac .secrets.env che do don)")
    return gt

def ghi_json(p, d, indent: int = 2) -> None:
    """Ghi mot tep JSON state NGUYEN TU: tmp cung thu muc + os.replace.

    Dat o day vi gan nhu moi script deu da import env_load. `write_text` CAT
    NGAN tep cu truoc khi ghi noi dung moi — chet dung giua hai buoc do (restart
    dich vu, het cho dia) de lai mot sidecar cut, va moi nguoi doc sau do nem
    ValueError: bai ket vinh vien ma khong ai biet.

    Quan trong nhat voi cac tep NHIEU TIEN TRINH cung ghi: `drafts/<id>.meta.json`
    duoc ghi tu approve_service, tu engine chay nen, VA tu tien trinh hermes cua
    bang den — ba tien trinh khac nhau, khong khoa chung.

    Ten tmp mang pid de hai tien trinh khong ghi lan vao cung mot tep tam.
    """
    import json as _j
    import os as _os
    p = Path(p)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(p.name + f".tmp.{_os.getpid()}")
    tmp.write_text(_j.dumps(d, ensure_ascii=False, indent=indent, default=str),
                   encoding="utf-8")
    _os.replace(tmp, p)
