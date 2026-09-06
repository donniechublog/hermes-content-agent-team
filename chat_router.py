#!/usr/bin/env python3
"""Dinh tuyen tin nhan Telegram toi dung profile hermes, giu mach hoi thoai.

Vi sao khong dung gateway cua hermes: gateway va approve_service khong the
cung long-poll mot bot token (Telegram tu choi). Tach ra hai bot thi ton them
token va them mot gateway ~584 MB. Cach nay chi can MOT bot, MOT tien trinh
dang chay san (approve_service), va cho phep dinh tuyen theo TOPIC — nhan
trong topic cua Jean thi Jean tra loi, trong topic cua Finn thi Finn tra loi.

Moi topic giu mot phien rieng qua `chat -c <ten phien>`, nen hoi thoai co
mach chu khong phai moi tin la mot lan chay roi rac.
"""
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402
import tele_util                                             # noqa: E402

HERMES_DIR = env_load.HERMES_DIR
HERMES_PY = env_load.HERMES_PY
# Container: home theo brand (moi brand mot ~/.hermes-<brand>). Systemd dat san;
# roi ve ~/.hermes o che do don cu.
HERMES_HOME = str(env_load.hermes_home())

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
_TEN_BRAND = {"blog": ("donniechublog", "@donniechublog"),
              "dcgr": ("dcgr.tech", "@dcgr.tech")}


def chat_hint() -> str:
    """Loi nhac che do hoi thoai, kem BRAND cua container hien tai.

    Vi sao kem brand: nhieu vai dung chung SOUL cho ca hai container (Gin, Ada,
    Itachi, Bob, Jean). Khi hoi "ban lam cho kenh nao", Gin o dcgr tra loi
    donniechublog, Bob luon dung handle @donniechublog. Container chi co MOT
    brand, va ma la noi biet chac dieu do — nen noi thang cho agent moi lan."""
    key = os.environ.get("CT_BRAND", "")
    ten, handle = _TEN_BRAND.get(key, ("(chưa rõ brand)", ""))
    return (
        "[Ghi chú hệ thống — tin nhắn hội thoại từ Telegram, không phải task]\n"
        f"Bạn đang chạy trong container của brand **{ten}** (handle {handle}). "
        "Mọi việc, mọi câu tự giới thiệu đều là cho brand này, không phải brand kia.\n"
        "Trả lời NGẮN (tối đa vài câu), bằng tiếng Việt, đúng câu hỏi. Không tự "
        "chạy lại quét/scan, không tạo task, không sửa tệp — trừ khi câu hỏi yêu "
        "cầu rõ ràng làm việc đó. Việc cần chạy lâu thì nói ngắn cách làm và hỏi "
        "lại trước. Nếu cần tra cứu thì tối đa 2-3 lệnh đọc nhanh, rồi trả lời.\n\n"
    )


# Tuong thich: ma cu tham chieu CHAT_HINT (hang). Gia tri that lay luc goi.
CHAT_HINT = chat_hint()


def route(thread_id, topics: dict) -> tuple:
    """Tra ve (profile, ten_phien) cho topic nay."""
    by_id = {v: k for k, v in topics.items()}
    key = by_id.get(thread_id)
    profile = TOPIC_PROFILE.get(key)
    session = f"tele-{key or 'general'}"
    return profile, session


_LOI_HTTP = re.compile(r"^HTTP [45]\d\d\b")

# `chat -Q` van in vai dong canh bao ha tang truoc cau tra loi (vd
# "  ⚠ tirith security scanner enabled but not available"); `-z` truoc day
# khong co. Chi bo cac dong DAU va phai co khoang trang thut dau — cau tra loi
# that cua agent khong bao gio thut dau, nen khong an nham noi dung.
_DONG_RAC = re.compile(r"^\s+[⚠✓↻ℹ]")
# Ghi vao log de lan sau "vai khong nho gi" la doi chieu duoc ngay: dong nay
# noi ro resume trung phien nao, bao nhieu tin — thay vi phai mo state.db.
_PHIEN = re.compile(r"(↻ Resumed session[^\n]*|Session \S+ found but has no messages)")


def _bo_dong_rac(out: str) -> str:
    dong = out.split("\n")
    i = 0
    while i < len(dong) and (not dong[i].strip() or _DONG_RAC.match(dong[i])):
        i += 1
    return "\n".join(dong[i:]).strip()


# Bo cong cu CHI DOC cho chat ngoai task. Do that tren server 06/09/2026:
# khong gioi han = 38 cong cu (co terminal, execute_code, write_file, patch,
# delegate_task); `safe` = ba cong cu web_search / web_extract / vision_analyze.
# Tuc la vai van tra loi va tra cuu duoc, nhung KHONG chay duoc script, khong
# sua duoc tep, khong tao duoc task.
BO_CHI_DOC = "safe"


def ask(profile, session, text, timeout=TIMEOUT_SEC, hint=True, thu_lai=2,
        toolsets=None) -> tuple:
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
    prompt = (chat_hint() + text) if hint else text
    # KHONG dung `-z` (oneshot): hermes_cli/main.py xu ly `-z` TRUOC roi thoat
    # ngay (`_run_and_exit_oneshot` chi nhan prompt/model/provider/toolsets/
    # skills) — `--continue` khong bao gio toi `_resolve_continue_arg`, bi bo
    # qua IM LANG. Hau qua: MOI tin nhan mo mot phien MOI, khong vai nao nho gi.
    # Bang chung 04/09/2026: state.db cua itachi KHONG he co phien ten
    # `tele-itachi`, chi co chuoi phien tu dat ten theo dong dau cua prompt
    # ("[Ghi chu he thong... #2 #3 #4"); phien 00:20:54 co dung 2 tin. Nen luc
    # 07:19 Ong Chu tra loi "xac nhan" thi Itachi dap "Xac nhan gi? Chua thay
    # cau hoi cu the truoc do" du mot phut truoc chinh no vua hoi. Su co Ethan
    # 03/09 15:14 ("session trong, khong co draft nao") cung mot goc nay.
    # Duong dung la subcommand `chat`: -c giu mach theo ten, --create-if-missing
    # tao phien lan dau (thieu co nay thi hermes thoat 1), -Q chi in cau tra loi
    # cuoi, --no-restore-cwd de lan resume sau khong tu cd di cho khac.
    args += ["chat", "-c", session, "--create-if-missing",
             "--no-restore-cwd", "-Q", "-q", prompt]
    # Han che cong cu cho lan goi nay. Da kiem chung `--toolsets` CO tac dung
    # tren duong `chat` (khong phai chi -z/--tui nhu dong help noi): cli.py
    # nhan vao self.enabled_toolsets roi dung no dung dan cho
    # get_tool_definitions() — danh sach cong cu dua cho model bi cat that.
    if toolsets:
        args += ["--toolsets", toolsets]
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
    out = _bo_dong_rac(out or "")
    err = (err or "").strip()
    mp = _PHIEN.search(err)
    log("chat", f"agent xong profile={profile or '-'} rc={proc.returncode} "
                f"het_gio={het_gio} {dt:.0f}s out={len(out)}c err={len(err)}c "
                f"phien={mp.group(1) if mp else '(khong ro)'}")
    if het_gio:
        phut = f"{timeout // 60}" if timeout >= 60 else f"{timeout / 60:.1f}"
        if out:
            return (out + f"\n\n⚠️ (agent chạy quá {phut} phút, đã dừng — trên là "
                          "phần đã trả lời được)"), None
        return None, (f"Agent chạy quá {phut} phút chưa xong, đã dừng. "
                      "Hỏi ngắn hơn hoặc giao thành task kanban.")
    if proc.returncode != 0 and not out:
        return None, (err[-400:] or f"Agent trả về lỗi rỗng (mã {proc.returncode}).")
    # Upstream tu choi tam thoi (vd DeepSeek "response_format unavailable now",
    # 429, 502): hermes in nguyen dong "HTTP 4xx/5xx ..." lam cau tra loi. Thu
    # lai toi da HAI lan (tu 04/09, chat co the chay 2 vai song song nen 429 de
    # gap hon) sau vai giay truoc khi dua loi do cho Ong Chu.
    if _LOI_HTTP.match(out) and thu_lai > 0 and time.time() - t0 < timeout / 2:
        # 9router ghi "(reset after 17s)" = upstream dang cooldown; cho dung
        # so giay do + 2, toi da 60. Khong co so thi 8s.
        m = re.search(r"reset after (\d+)s", out)
        cho = min(60, int(m.group(1)) + 2) if m else 8
        log("chat", f"agent tra loi HTTP loi ({out[:60]!r}) -> thu lai sau {cho}s")
        time.sleep(cho)
        return ask(profile, session, text, timeout=timeout - dt - cho, hint=hint,
                   thu_lai=thu_lai - 1, toolsets=toolsets)
    return out or "(agent không trả về nội dung)", None


def clean(text: str) -> str:
    """Bo ma mau ANSI. KHONG cat noi dung nua — tin dai duoc `chia_tin` tach
    thanh nhieu tin (xem handle_chat), nen reply khong con bi mat phan cuoi."""
    return tele_util.bo_ansi(text)
