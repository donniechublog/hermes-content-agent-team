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

# Loi nhac che do HOI THOAI, ghep truoc moi tin nhan chat cho MOI vai.
# Vi sao o day (ma) chu khong chi trong SOUL: SOUL moi vai mot ban, de lech;
# day la luat chung cua kenh Telegram nen dat mot cho. Su co 02/09/2026: Vera
# nhan "Hom nay ko lam viec ?" roi tu chay lai scan_business, doc cron, mo
# kanban.db... 74 tin nhan, 10 phut, bi giet vi het gio — Ong Chu khong nhan
# duoc gi ngoai dong bao het gio.
CHAT_HINT = (
    "[Ghi chú hệ thống — tin nhắn hội thoại từ Telegram, không phải task]\n"
    "Trả lời NGẮN (tối đa vài câu), bằng tiếng Việt, đúng câu hỏi. Không tự "
    "chạy lại quét/scan, không tạo task, không sửa tệp — trừ khi câu hỏi yêu "
    "cầu rõ ràng làm việc đó. Việc cần chạy lâu thì nói ngắn cách làm và hỏi "
    "lại trước. Nếu cần tra cứu thì tối đa 2-3 lệnh đọc nhanh, rồi trả lời.\n\n"
)


def route(thread_id, topics: dict) -> tuple:
    """Tra ve (profile, ten_phien) cho topic nay."""
    by_id = {v: k for k, v in topics.items()}
    key = by_id.get(thread_id)
    profile = TOPIC_PROFILE.get(key)
    session = f"tele-{key or 'general'}"
    return profile, session


def ask(profile, session, text, timeout=TIMEOUT_SEC, hint=True) -> tuple:
    """Goi hermes CLI, tra ve (noi_dung, loi). LUON tra ve — khong nem.

    - Chay trong process group rieng (start_new_session) de khi het gio giet
      duoc CA con lan chau (shell cua terminal tool, chromium...). Truoc day chi
      giet tien trinh CLI, chau mo coi van chay tiep, ngon tai nguyen.
    - Het gio ma stdout da co gi thi TRA VE phan do kem ghi chu, thay vi vut.
    - Ghi log bat dau/ket thuc voi thoi luong + ma thoat, de doi chieu khi
      Ong Chu bao "khong tra loi".
    """
    import time
    import signal
    try:
        import ghi_log
        log = ghi_log.log
    except Exception:                                        # noqa: BLE001
        log = lambda a, b: print(f"[{a}] {b}", flush=True)   # noqa: E731

    args = [str(HERMES_PY), "-m", "hermes_cli.main"]
    if profile:
        args += ["-p", profile]
    prompt = (CHAT_HINT + text) if hint else text
    args += ["--continue", session, "-z", prompt]
    env = dict(os.environ, HERMES_HOME=HERMES_HOME)
    t0 = time.time()
    log("chat", f"goi agent profile={profile or '-'} session={session} "
                f"home={HERMES_HOME} timeout={timeout}s")
    try:
        proc = subprocess.Popen(args, cwd=str(HERMES_DIR), env=env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                text=True, start_new_session=True)
    except Exception as e:                                   # noqa: BLE001
        log("chat", f"KHONG chay duoc hermes CLI: {type(e).__name__}: {e}")
        return None, f"Không chạy được agent: {type(e).__name__}: {e}"

    try:
        out, err = proc.communicate(timeout=timeout)
        het_gio = False
    except subprocess.TimeoutExpired:
        het_gio = True
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            out, err = proc.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            out, err = proc.communicate()
    dt = time.time() - t0
    out = (out or "").strip()
    err = (err or "").strip()
    log("chat", f"agent xong profile={profile or '-'} rc={proc.returncode} "
                f"het_gio={het_gio} {dt:.0f}s out={len(out)}c err={len(err)}c")
    if het_gio:
        phut = f"{timeout // 60}" if timeout >= 60 else f"{timeout / 60:.1f}"
        if out:
            return (out + f"\n\n⚠️ (agent chạy quá {phut} phút, đã dừng — trên là "
                          "phần đã trả lời được)"), None
        return None, (f"Agent chạy quá {phut} phút chưa xong, đã dừng. "
                      "Hỏi ngắn hơn hoặc giao thành task kanban.")
    if proc.returncode != 0 and not out:
        return None, (err[-400:] or f"Agent trả về lỗi rỗng (mã {proc.returncode}).")
    return out or "(agent không trả về nội dung)", None


def clean(text: str) -> str:
    """Bo ma mau ANSI. KHONG cat noi dung nua — tin dai duoc `chia_tin` tach
    thanh nhieu tin (xem handle_chat), nen reply khong con bi mat phan cuoi."""
    return tele_util.bo_ansi(text)
