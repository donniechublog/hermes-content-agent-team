#!/usr/bin/env python3
"""Dinh tuyen tin nhan Telegram toi dung profile hermes, giu mach hoi thoai.

Vi sao khong dung gateway cua hermes: gateway va approve_service khong the
cung long-poll mot bot token (Telegram tu choi). Tach ra hai bot thi ton them
token va them mot gateway ~584 MB. Cach nay chi can MOT bot, MOT tien trinh
dang chay san (approve_service), va cho phep dinh tuyen theo TOPIC — nhan
trong topic cua Jean thi Jean tra loi, trong topic cua Finn thi Finn tra loi.

Moi topic giu mot phien rieng qua `--continue <ten phien>`, nen hoi thoai co
mach chu khong phai moi tin la mot lan chay roi rac.
"""
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import tele_util                                             # noqa: E402
from tele_util import chia_tin                               # noqa: E402  (re-export cho approve_service)

HERMES_DIR = Path.home() / "hermes-agent"
HERMES_PY = HERMES_DIR / "venv" / "bin" / "python"
# Container: home theo brand (moi brand mot ~/.hermes-<brand>). Systemd dat san;
# roi ve ~/.hermes o che do don cu.
HERMES_HOME = os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))

# topic -> profile. Slug generic, trung ten profile trong home cua container.
# Nhan ngoai cac topic nay (vd General) di vao profile mac dinh. Phai co du cho
# MOI topic trong state/topics.<brand>.json; thieu mot cai thi chat trong topic
# do roi ve profile mac dinh.
TOPIC_PROFILE = {
    "scout": "scout",
    "designer": "designer",
    "carousel": "carousel",
    "carousel-edu": "carousel-edu",
    "writer": "writer",
    "analyst": "analyst",
    "teaser": "teaser",
    "nova": "nova",
    "market": "market",
    "gin": "gin",
    "itachi": "itachi",
    "bob": "bob",
}

REPLY_LIMIT = 4000          # chua toi 4096 cua Telegram, chua cho phan hau to
TIMEOUT_SEC = 600           # agent chay lau; 10 phut la du cho hau het viec


def route(thread_id, topics: dict) -> tuple:
    """Tra ve (profile, ten_phien) cho topic nay."""
    by_id = {v: k for k, v in topics.items()}
    key = by_id.get(thread_id)
    profile = TOPIC_PROFILE.get(key)
    session = f"tele-{key or 'general'}"
    return profile, session


def ask(profile, session, text) -> tuple:
    """Goi hermes CLI, tra ve (noi_dung, loi)."""
    args = [str(HERMES_PY), "-m", "hermes_cli.main"]
    if profile:
        args += ["-p", profile]
    args += ["--continue", session, "-z", text]
    env = dict(os.environ, HERMES_HOME=HERMES_HOME)
    try:
        r = subprocess.run(args, cwd=str(HERMES_DIR), env=env,
                           capture_output=True, text=True, timeout=TIMEOUT_SEC)
    except subprocess.TimeoutExpired:
        return None, f"Agent chay qua {TIMEOUT_SEC // 60} phut chua xong."
    out = (r.stdout or "").strip()
    if r.returncode != 0 and not out:
        return None, (r.stderr or "").strip()[-400:] or "Agent tra ve loi rong."
    return out or "(agent khong tra ve noi dung)", None


def clean(text: str) -> str:
    """Bo ma mau ANSI. KHONG cat noi dung nua — tin dai duoc `chia_tin` tach
    thanh nhieu tin (xem handle_chat), nen reply khong con bi mat phan cuoi."""
    return tele_util.bo_ansi(text)
