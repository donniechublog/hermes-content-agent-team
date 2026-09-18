#!/usr/bin/env python3
"""approve_dispatch.py — BANG VAI (slug <-> ten <-> mac dinh anh/viet), tao task
kanban qua hermes CLI, doc kanban.db (trang thai/run/bang chung "xong ma khong
giao"), bang den swarm, bao tien do vao topic. Tach tu approve_service.py 06/09/2026
(di chuyen thuan, xem approve_base.py).
"""
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

from html import escape as html_escape


sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402
import blackboard                                              # noqa: E402
import write_log                                              # noqa: E402
import hermes_adapter                                        # noqa: E402
import role                                                   # noqa: E402
import state_paths                                           # noqa: E402

from approve_base import (  # noqa: E402
    HERMES_HOME, HERMES_PY, ROOT, STATE_DIR, _write_json, call, log,
)


def _report_receive_job(token, group, vai, tu_vai, title, tid, ly_do=""):
    """Bao NGAY vao topic cua vai nhan viec, ca khi Ong Chu giao task moi (tu_vai=None)
    lan khi viec duoc CHUYEN tu vai khac (Ong Chu 05/09/2026: "it nhat cung thong bao
    de biet da nhan job"; mo rong 08/09/2026 sang CA task moi giao, khong chi hang
    chuyen — truoc do task moi tao trong approve_pick.py im lang cho toi khi dispatcher
    chay, cung cai treo da bi bat o 05/09). Khong doi dispatcher: dong ▶️ cua
    bao_tien_do chi den khi task thuc su chay (poll 50s + dispatcher 60s + hang doi),
    truoc do topic cua vai moi im lang nhu chua biet gi."""
    try:
        tp = env_load.topics_path()
        topics = json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else {}
    except Exception:                                        # noqa: BLE001
        topics = {}
    thread = topics.get(vai)
    if not thread:
        return
    truoc = hermes_adapter.count_form_run(tru_tid=tid)
    if truoc is None:              # khong doc duoc kanban != khong con viec nao
        log("route", f"khong doc duoc hang doi kanban khi bao {vai} nhan {tid}")
        truoc = 0
    ten = _TEN_HIEN.get(vai, vai)
    nguon = f" chuyển từ <b>{_TEN_HIEN.get(tu_vai, tu_vai)}</b>" if tu_vai else ""
    text = (f"📥 <b>{ten}</b> đã nhận task{nguon}: <i>{html_escape(title[:80])}</i>\n"
            + (f"Lý do: {html_escape(ly_do[:160])}\n" if ly_do else "")
            + (f"Đang xếp hàng sau {truoc} việc, tới lượt sẽ bắt đầu" if truoc
               else "Bắt đầu ngay khi dispatcher nhận (≤ 1 phút)") + f" · task {tid}")
    call(token, "sendMessage", chat_id=group, message_thread_id=thread,
         text=text, parse_mode="HTML")
    log("route", f"bao {vai} nhan viec tu {tu_vai or 'Ong Chu'}: {tid} (truoc={truoc})")

# BANG VAI da gom vao `role.py` (audit A4/F1) — them mot vai = them MOT dong o
# do, khong phai sua sau cho nhu truoc. Cac ten duoi day giu nguyen la MAT TIEN
# cho ho approve_* (approve_command/approve_pick/approve_post) va test dang goi qua
# `approve_dispatch.X`; ly do ton tai cua tung bang nam trong role.py.
ROLE_IMAGE = role.ROLE_IMAGE
ROLE_CAROUSEL = role.ROLE_CAROUSEL
ROLE_EDU = role.ROLE_EDU
NAME_BRIGHT_CAP = role.NAME_BRIGHT_CAP
NAME_ROLE_IMAGE = role.NAME_ROLE_IMAGE
NAME_ROLE_WRITE = role.NAME_ROLE_WRITE
SLUG_OLD = role.SLUG_OLD
DEFAULT_IMAGE = role.DEFAULT_IMAGE
DEFAULT_WRITE = role.DEFAULT_WRITE

def role_of_topic(thread_id):
    """Topic id -> ten vai, doc tu state/topics.json."""
    tp = env_load.topics_path()
    if thread_id is None or not tp.exists():
        return None
    try:
        m = json.loads(tp.read_text(encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        return None
    for ten, tid in m.items():
        if str(tid) == str(thread_id):
            return ten
    return None

# SLUG_OLD (slug cu -> slug profile; su co 01/09/2026 hai bai dcgr ket 2 ngay vi
# sidecar ghi "dre"/"miles") nay la VIEW cua role.py — dong 69 o tren. Truoc audit
# lượt 2 (ADF-r2-1) mot bang chep tay o day ghi de no 21 dong sau khi gan, nen
# them slug_cu vao role.py KHONG toi duoc day (chua lo chi vi hai bang dang trung).

def standard_assignee(assignee):
    """Tra ve slug profile thuc co trong home container, hoac (None, loi)."""
    slug = role.canonical_slug(assignee)
    co = Path(HERMES_HOME) / "profiles" / slug
    if not co.is_dir():
        return None, (f"không có profile '{slug}' trong {Path(HERMES_HOME).name} "
                      f"— task sẽ không ai nhận, không tạo")
    return slug, None

def kanban_create(title, assignee, body, parent=None):
    """Tao task cho MOT VAI: kiem ten vai roi giao cho hermes_adapter.

    Hinh dang lenh `hermes kanban create` (co, workspace, doc JSON) nam trong
    hermes_adapter (audit C2) — o day chi con phan cua content-team: vai nay co
    that khong, va ghi mot dong log doc duoc."""
    assignee, loi = standard_assignee(assignee)
    if loi:
        log("kanban", f"tu choi tao '{title[:60]}': {loi}")
        return None, loi
    tid, loi = hermes_adapter.create_task(title, assignee, body, parent=parent,
                                       max_runtime=role.max_runtime_for(assignee))
    if loi:
        log("kanban", f"tao '{title[:60]}' cho {assignee} LOI: {loi[:200]}")
        return None, loi
    log("kanban", f"tao task {tid} cho {assignee}: {title[:60]}")
    return tid, None

# Kanban cua home container hien tai. Viec bi chan/that bai duoc bao qua
# report_progress_kanban (kem ly do); ham bao_viec_bi_chan rieng truoc day trung
# viec voi no va bo sot Kite, da bo 05/09/2026.
ALREADY_REPORT_PROGRESS = STATE_DIR / state_paths.REPORTED_PROGRESS_FILE   # {task_id: trang thai da bao}
STORY_RESULT = STATE_DIR / state_paths.TASK_RESULT_MESSAGES_FILE    # {task_id: {chat,thread,mid}}
ALREADY_REPORT_STALLED = STATE_DIR / state_paths.REPORTED_STALLED_FILE         # {task_id: epoch lan bao "treo" cuoi}
THRESHOLD_STALLED_MINUTES = 20          # lan chay hien tai lau hon nay -> bao (xem long_run_message)
AGAIN_REPORT_STALLED_MINUTES = 30         # con chay thi nhac lai sau moi khoang nay
BEAT_SILENT_MINUTES = 5               # khong co heartbeat lau hon nay -> goi la "im lang"


def long_run_message(ten: str, title: str, tid: str, phut: float, nhip_cuoi, pid, now) -> str:
    """Cau bao khi mot lan chay keo dai qua THRESHOLD_STALLED_MINUTES — noi DUNG cai do duoc.

    Ba trang thai khac han nhau ma cau cu "khong phan hoi hon N phut" gop lam mot
    (LOW-23): (a) worker da CHET, (b) im lang that (khong heartbeat qua BEAT_SILENT_MINUTES),
    (c) van dang lam, chi la lau. Khong doc duoc nhip/pid thi noi la khong biet."""
    bai = f"<i>{html_escape(title[:80])}</i> (task {tid})"
    song = hermes_adapter.pid_alive(pid)
    if song is False:
        return (f"⛔ <b>{ten}</b>: worker (pid {pid}) đã chết sau {int(phut)} phút chạy: {bai}\n"
                "hermes sẽ thu hồi và xếp lại hàng.")
    if nhip_cuoi:
        im = (now - nhip_cuoi) / 60
        if im >= BEAT_SILENT_MINUTES:
            return (f"⚠️ <b>{ten}</b> không phản hồi {int(im)} phút (nhịp thở cuối "
                    f"{time.strftime('%H:%M', time.localtime(nhip_cuoi))}), đã chạy "
                    f"{int(phut)} phút: {bai}")
        return (f"⏳ <b>{ten}</b> vẫn đang làm, đã {int(phut)} phút (nhịp thở "
                f"{int(im)} phút trước): {bai}\nQuá max_runtime thì hermes sẽ tự dừng.")
    return (f"⚠️ <b>{ten}</b> không phản hồi hơn {int(phut)} phút (không có nhịp thở "
            f"ghi lại): {bai}")


def killed_message(ten: str, title: str, tid: str, troi, tran, st: str) -> str:
    """Cau bao khi hermes giet worker vi qua max_runtime (run outcome=timed_out)."""
    bai = f"<i>{html_escape(title[:80])}</i> (task {tid})"
    phut = f"{int(troi) // 60} phút" if troi else "quá giờ"
    tran_ = f" (trần {int(tran) // 60} phút)" if tran else ""
    sau = "đang chạy lại" if st == "running" else "đã xếp lại hàng, sẽ chạy lại"
    return f"⏱ <b>{ten}</b> bị hermes dừng sau {phut}{tran_}, {sau}: {bai}"

_TEN_HIEN = role.DISPLAY_NAME            # xem role.py

# Gio VN (UTC+7, khong DST) — cung quy uoc voi journal.VN, dung rieng o day de
# khoi keo them journal.py (BAN DANG KY nay muon nhe, xem docstring dau tep).
VN = timezone(timedelta(hours=7))

# Vai can dem "task #NN hom nay" khi bao xong viec (LOW-250, Ong Chu 17/09/2026):
# CHI writer + designer (nguoi lam ra san pham dem duoc moi ngay) — researcher/
# analyst (Finn/Vera/Qinn/Ada...) chua can, de sau.
DAILY_ORDINAL_ROLES = set(NAME_ROLE_WRITE) | set(NAME_ROLE_IMAGE)


def _daily_task_ordinal(rows, ai, tid, completed_at):
    """So thu tu task `done` thu N trong NGAY (gio VN) cua vai `ai`, tinh ca
    task `tid` dang xet — None neu khong co completed_at de biet ngay nao.

    `rows` la danh sach 24h gan nhat da doc san trong report_progress_kanban
    (hermes_adapter.job(tu_ts=...)) — 24h luon phu het "hom nay" nen khong can
    doc kanban lan nua. Xep hang theo completed_at (rieng id lam tie-break khi
    trung giay) roi tim vi tri cua `tid` trong danh sach cung ngay/cung vai."""
    if not completed_at:
        return None
    ngay = datetime.fromtimestamp(completed_at, VN).strftime("%Y-%m-%d")
    cung_ngay = sorted(
        (r for r in rows if r["assignee"] == ai and r["status"] == "done"
         and r.get("completed_at")
         and datetime.fromtimestamp(r["completed_at"], VN).strftime("%Y-%m-%d") == ngay),
        key=lambda r: (r["completed_at"], r["id"]))
    for i, r in enumerate(cung_ngay, start=1):
        if r["id"] == tid:
            return i
    return len(cung_ngay) + 1        # tid chua nam trong rows (khong nen xay ra)

# Moi bai mot the goc (blackboard.py), Dre/Miles/Ada la con cua no. Ly do va so do
# o dau blackboard.py. O day chi co ba mieng noi vao luong san:
#   create_pair  -> tao the goc, task Dre parent=goc
#   imgok        -> task Miles parent=[Dre, goc]  (cong "Ong Chu duyet anh" giu nguyen)
#   tien do      -> ban giao cua Miles da nam tren bang den qua kanban_complete.
# Task "Ada soat" tung nam o day (sang 05/09) da bo chieu 05/09: mot task LLM moi
# bai cho viec caption_check gio lam bang code (so trong caption phai co trong tu lieu).
# Chi bat cho brand trong CT_BLACKBOARD_BRANDS (mac dinh: dcgr). Blog dang la nhom doi chung
# cua tuan do bot-mode (05–12/09) va Ong Chu chi yeu cau dcgr — code chung nhung
# hanh vi blog phai y nguyen. Bat blog: Environment=CT_BLACKBOARD_BRANDS=dcgr,blog trong unit.
BLACKBOARD_BRANDS = {b.strip() for b in os.environ.get("CT_BLACKBOARD_BRANDS", "dcgr").split(",") if b.strip()}

BLACKBOARD_ASSIGNEE = "ban_bien_tap"     # trung voi blackboard.ROOT_ASSIGNEE

BLACKBOARD_MENTION = """

== BANG DEN (kanban) ==
The goc cua bai: {root}. Ban giao cua vai truoc nam o muc "Parent task results"
trong context task nay; can them thi goi tool kanban_show(task_id="{root}").
Script nop (*_nop.py) TU ghi len bang den — ban khong phai ghi. Phan cua ban khi
xong: goi tool kanban_complete voi summary = dong "Ket qua task" va metadata =
JSON o dong "[metadata]" ma script in ra. Khong tu bia so lieu vao metadata."""

def _blackboard_root(draft_id, title, goal=""):
    """Tao the goc qua blackboard.py (python cua hermes, kanban.db cua container).
    Tra ve id hoac None — KHONG bao gio chan viec tao task Dre. None cung la
    cach TAT ca lop bang den (khong parent, khong Ada) cho brand khong bat."""
    if write_log.brand() not in BLACKBOARD_BRANDS:
        return None
    try:
        r = subprocess.run(
            [str(HERMES_PY), str(ROOT / "blackboard.py"), "root", draft_id,
             "--title", title, "--goal", goal or title, "--author", "approve_service"],
            cwd=str(ROOT), env=dict(os.environ, HERMES_HOME=HERMES_HOME),
            capture_output=True, text=True, timeout=120)
        rid = ((r.stdout or "").strip().splitlines() or [""])[-1].strip()
        if r.returncode != 0 or not rid.startswith("t_"):
            log("bangden", f"{draft_id}: khong tao duoc the goc: "
                           f"{(r.stderr or r.stdout)[-200:]}")
            return None
        log("bangden", f"{draft_id}: the goc {rid}")
        return rid
    except Exception as e:                                   # noqa: BLE001
        log("bangden", f"{draft_id}: loi tao the goc: {type(e).__name__}: {e}")
        return None

def _blackboard_write(draft_id, key, value):
    """Ghi mot muc len bang den qua blackboard.write_background (python cua hermes, tien
    trinh con). Best-effort, khong nem."""
    ok, loi = blackboard.write_background(draft_id, key, value, "approve_service", hermes_home=HERMES_HOME)
    if not ok:
        log("bangden", f"{draft_id}: ghi '{key}' loi: {loi}")

def _status_task(tid):
    """Trang thai hien tai cua mot task; '' neu task khong co; None neu KHONG DOC
    DUOC kanban (C1 — hai thu nay khac nhau, nguoi goi phai phan biet).

    Truoc audit lượt 2 (C-r2-3) ham nay ep None ve '' — kanban hong luc bam
    Duyet thi task Miles duoc tao khong co cha (mat ban giao cua Dre) ma note
    van bao "✅", va nut Duyet bam lai tra cau co dinh "dang duoc viet" — dung
    loi c81e6e6 sua. Doc qua hermes_adapter — noi duy nhat biet schema (C2)."""
    return hermes_adapter.status(tid)

def _summary_run(tid):
    """(summary, metadata_dict) cua lan chay cuoi cua task — cai vai vua ban giao."""
    run = hermes_adapter.last_run(tid)
    if not run:                                  # None (khong doc duoc) hoac {} (chua chay)
        return "", {}
    # Y het `coalesce(summary, error, '')` cu: chi roi sang `error` khi summary
    # la NULL, KHONG roi khi summary la chuoi rong.
    tom = run.get("summary")
    if tom is None:
        tom = run.get("error")
    return (tom or ""), run.get("metadata") or {}

def reason_task(tid):
    """Ban cong khai cua _summary_run: chi can cau ly do, khong can metadata —
    dung khi tra loi lai nut bam (approve_post.py) ve mot task da blocked/failed."""
    tom_tat, _md = _summary_run(tid)
    return tom_tat

def link_result(tid):
    """Link Telegram toi dong tien do (start/done/blocked...) da gui cho task
    nay, hoac None neu chua co (chua bao lan nao, hoac gui trong DM khong lam
    duoc deep-link). Ghi boi report_progress_kanban() moi khi gui mot dong."""
    if not tid:
        return None
    try:
        tin = json.loads(STORY_RESULT.read_text(encoding="utf-8")) if STORY_RESULT.exists() else {}
    except Exception:                                        # noqa: BLE001
        return None
    d = tin.get(tid)
    if not d or not d.get("mid"):
        return None
    chat = str(d.get("chat") or "")
    if not chat.startswith("-100"):        # chi supergroup moi co dang deep-link nay
        return None
    noi_bo = chat[4:]
    thread = d.get("thread")
    if thread:
        return f"https://t.me/c/{noi_bo}/{thread}/{d['mid']}"
    return f"https://t.me/c/{noi_bo}/{d['mid']}"

def _done_code_no_hand(tid, ai, created_at):
    """Vai anh dong task `done` ma KHONG gui album/the nao len topic — tra ve ly do
    de bao ⛔ thay vi ✅; None neu co san pham that.

    Su co 05/09/2026 07:27 (bai Nvidia/Thinking Machines): brief chi co 1 anh lac
    de, Dre bo cuoc nhung goi kanban_complete voi metadata tu che
    {"kind": "carousel_abort"} thay vi kanban_block -> kanban ghi done, topic bao
    "✅ Dre xong", Ong Chu: "bao xong ma co thay lam gi dau". Kanban tin loi vai;
    o day tin BANG CHUNG: nhat ky gui Telegram cua vai (telegram_sent/<vai>.jsonl)
    phai co mot dong SAU luc task duoc tao."""
    if ai not in NAME_ROLE_IMAGE:
        return None
    tom_tat, md = _summary_run(tid)
    if "abort" in str(md.get("kind", "")).lower():
        return tom_tat or "vai tự báo bỏ cuộc (abort) nhưng đóng task là xong"
    p = STATE_DIR / "telegram_sent" / f"{ai}.jsonl"
    try:
        for dong in reversed(p.read_text(encoding="utf-8").splitlines()[-80:]):
            try:
                d = json.loads(dong)
            except Exception:                                # noqa: BLE001
                continue
            if int(d.get("ts", 0)) >= int(created_at or 0) - 5:
                return None
    except OSError:
        pass
    return tom_tat or "(không có album nào được gửi lên topic sau khi task bắt đầu)"

def report_progress_kanban(token, group):
    """Bao TIEN DO hang doi kanban ve Telegram: task bat dau -> mot dong vao
    topic cua vai kem so viec con xep hang; task xong/hong -> mot dong nua;
    task chay QUA LAU ma khong doi trang thai (worker treo/chet) -> canh bao
    rieng, nhac lai moi AGAIN_REPORT_STALLED_MINUTES toi khi het treo.

    Vi sao: tu 03/09/2026 moi container chay MOT task mot luc. Sang 04/09 Ong
    Chu chon 7 bai luc 05:33, Dre lam bai 1, sau bai kia + Nova xep hang ca
    tieng — va khong ai noi gi, trong nhu he thong dung. Hang doi la thiet ke,
    im lang thi khong. Chay moi vong poll (~50s), chi bao khi trang thai doi."""
    if not hermes_adapter.has_kanban():
        return
    try:
        da = json.loads(ALREADY_REPORT_PROGRESS.read_text(encoding="utf-8")) if ALREADY_REPORT_PROGRESS.exists() else {}
    except Exception:                                        # noqa: BLE001
        da = {}
    try:
        tin = json.loads(STORY_RESULT.read_text(encoding="utf-8")) if STORY_RESULT.exists() else {}
    except Exception:                                        # noqa: BLE001
        tin = {}
    try:
        treo = json.loads(ALREADY_REPORT_STALLED.read_text(encoding="utf-8")) if ALREADY_REPORT_STALLED.exists() else {}
    except Exception:                                        # noqa: BLE001
        treo = {}
    rows = hermes_adapter.job(tu_ts=time.time() - 86400)
    if rows is None:                 # co tep ma doc khong duoc -> phai keu
        log("tiendo", "khong doc duoc kanban")
        return
    cho = [r for r in rows if r["status"] == "ready"]
    tp = env_load.topics_path()
    try:
        topics = json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else {}
    except Exception:                                        # noqa: BLE001
        topics = {}
    now = time.time()
    doi = doi_treo = False
    # LOW-23 (12/09/2026): "chay bao lau" do tu LAN CHAY DANG MO, khong tu
    # tasks.started_at (moc lan DAU, hermes khong bao gio reset — task bi giet o
    # 25m roi chay lai bi bao "khong phan hoi 40 phut" ngay giay dau). "Con song
    # khong" doc tu last_heartbeat_at/worker_pid — t_24b214a6 tho deu moi 60s
    # suot 50 phut ma Telegram van noi "khong phan hoi". None = khong doc duoc
    # -> coi nhu khong biet, roi ve cach cu, khong phai "da chet".
    moc = hermes_adapter.run_start() or {}
    nhip = hermes_adapter.heartbeat([r["id"] for r in rows]) or {}
    lan_cuoi = None                          # doc luoi: chi khi co task ready/running
    for v in rows:
        tid, ai, st = v["id"], v["assignee"], v["status"]
        title, _c = v["title"], v["created_at"]
        bat_dau = (moc.get(tid) or (None,))[0] or v.get("started_at")
        if st == "running" and ai != BLACKBOARD_ASSIGNEE and bat_dau:
            phut = (now - bat_dau) / 60
            if phut >= THRESHOLD_STALLED_MINUTES and now - treo.get(tid, 0) >= AGAIN_REPORT_STALLED_MINUTES * 60:
                ten_treo = _TEN_HIEN.get(ai, ai)
                thread_treo = topics.get(ai)
                nhip_cuoi, pid = nhip.get(tid) or (None, None)
                text = long_run_message(ten_treo, title, tid, phut, nhip_cuoi, pid, now)
                call(token, "sendMessage", chat_id=group,
                     **({"message_thread_id": thread_treo} if thread_treo else {}),
                     text=text, parse_mode="HTML")
                treo[tid] = now
                doi_treo = True
                log("tiendo", f"{tid} {ai} chay {int(phut)} phut, da bao: {text[:60]}")
        elif tid in treo:
            del treo[tid]                    # roi running (hoac chuyen vai) -> het treo
            doi_treo = True
        # BI HERMES DUNG VI QUA max_runtime: task ve `ready` roi chay lai; vong
        # nay truoc 12/09/2026 bo qua `ready` nen hai lan giet cua t_24b214a6
        # hoan toan im lang tren Telegram. Bao MOT lan cho MOI run timed_out.
        if st in ("ready", "running") and ai != BLACKBOARD_ASSIGNEE:
            if lan_cuoi is None:
                lan_cuoi = hermes_adapter.last_run_many([r["id"] for r in rows]) or {}
            lc = lan_cuoi.get(tid) or {}
            khoa_tt = f"{tid}:timed_out:{lc.get('run_id')}"
            if lc.get("status") == "timed_out" and not da.get(khoa_tt):
                md = lc.get("metadata") or {}
                ten_tt = _TEN_HIEN.get(ai, ai)
                thread_tt = topics.get(ai)
                text = killed_message(ten_tt, title, tid, md.get("elapsed_seconds"),
                                   md.get("limit_seconds"), st)
                call(token, "sendMessage", chat_id=group,
                     **({"message_thread_id": thread_tt} if thread_tt else {}),
                     text=text, parse_mode="HTML")
                da[khoa_tt] = True
                doi = True
                log("tiendo", f"{tid} {ai} timed_out run {lc.get('run_id')}, da bao")
        if st in ("ready", "todo", "triage") or da.get(tid) == st:
            continue
        if ai == BLACKBOARD_ASSIGNEE:          # the goc/bang den: khong phai viec cua ai
            da[tid] = st
            doi = True
            continue
        ten = _TEN_HIEN.get(ai, ai)
        if st == "running":
            sau = len(cho)
            text = (f"▶️ <b>{ten}</b> bắt đầu: <i>{html_escape(title[:80])}</i>"
                    + (f"\n(còn {sau} việc xếp hàng sau việc này)" if sau else ""))
        elif st == "done":
            gia = _done_code_no_hand(tid, ai, _c)
            if gia:
                text = (f"⛔ <b>{ten}</b> báo xong nhưng <b>không có sản phẩm</b>: "
                        f"<i>{html_escape(title[:80])}</i>\n{html_escape(gia.strip()[:500])}\n"
                        "(Task đóng sai cách — vai phải dùng kanban_block khi thiếu ảnh.)")
                log("bangden", f"{tid} {ai} done-gia: {gia[:120]}")
            else:
                so_tt = (_daily_task_ordinal(rows, ai, tid, v.get("completed_at"))
                         if ai in DAILY_ORDINAL_ROLES else None)
                nhan = f" task #{so_tt:02d}" if so_tt else ""
                text = f"✅ <b>{ten}</b> xong{nhan}: <i>{html_escape(title[:80])}</i>"
        elif st in ("blocked", "failed"):
            # Kem LY DO (summary/error cua lan chay cuoi) — day la cai Ong Chu can
            # de go: vai anh block vi thieu anh that thi bao ro anh nao bi loai.
            ly_do, _ = _summary_run(tid)
            text = (f"⛔ <b>{ten}</b> dừng ({st}): <i>{html_escape(title[:80])}</i>"
                    + (f"\n{html_escape(ly_do.strip()[:400])}" if ly_do.strip() else "")
                    + ("\nBài đi kèm đang chờ, sẽ không chạy tới khi việc ảnh được gỡ."
                       if ai in NAME_ROLE_IMAGE else ""))
        else:
            da[tid] = st
            doi = True
            continue
        thread = topics.get(ai)
        r = call(token, "sendMessage", chat_id=group,
                 **({"message_thread_id": thread} if thread else {}),
                 text=text, parse_mode="HTML")
        log("tiendo", f"{tid} {ai} -> {st} (thread={thread}) gui={'ok' if r.get('ok') else r.get('description')}")
        mid = (r.get("result") or {}).get("message_id")
        if mid:                              # nho lai de dung nut bam sau nay tra ve dung link
            tin[tid] = {"chat": group, "thread": thread, "mid": mid}
        da[tid] = st
        doi = True
    # Chi giu task 24h gan nhat cho ba tep khong phinh (da bao dung `r["id"]`:
    # tung la `r[0]` — rows la dict, luon nem KeyError, chan MOI lan ghi ke tu
    # do; sua kem trong doi nay vi STORY_RESULT/ALREADY_REPORT_STALLED moi cung se hong theo).
    song = {r["id"] for r in rows}
    if doi:
        # khoa "tid:timed_out:<run>" cung song theo task cua no
        da = {k: v for k, v in da.items() if k.split(":")[0] in song}
        tin = {k: v for k, v in tin.items() if k in song}
        try:
            _write_json(ALREADY_REPORT_PROGRESS, da, indent=None)
            _write_json(STORY_RESULT, tin, indent=None)
        except OSError as e:
            log("tiendo", f"khong ghi duoc {ALREADY_REPORT_PROGRESS.name}/{STORY_RESULT.name}: {e}")
    if doi_treo:
        treo = {k: v for k, v in treo.items() if k in song}
        try:
            _write_json(ALREADY_REPORT_STALLED, treo, indent=None)
        except OSError as e:
            log("tiendo", f"khong ghi duoc {ALREADY_REPORT_STALLED.name}: {e}")

# Nhan category dung TIENG ANH. Ong Chu chot: bo tieng Viet o nhan de khoi phat
# sinh loi dau. Nhan la tu ngan, doc gia ky thuat quen ca hai thu tieng, ma
# tieng Anh thi khong co dau nen khong bao gio go sai.
#
# Bang tra nhan ca ban tieng Viet cu (co dau lan mat dau) de manifest cu van
# chuan hoa dung, khong phai viet lai.
LABEL_STANDARD = {
    "arxiv": "ARXIV",
    "mo hinh": "MODEL", "model": "MODEL",
    "thu nghiem": "LAB", "lab": "LAB",
    "ha tang": "INFRA", "infra": "INFRA", "infrastructure": "INFRA",
    "cong cu": "TOOL", "tool": "TOOL",
    "ky thuat": "ENGINEERING", "engineering": "ENGINEERING",
    "kinh doanh": "BUSINESS", "business": "BUSINESS",
    "ma nguon mo": "OPEN SOURCE", "open source": "OPEN SOURCE",
    "open weights": "OPEN WEIGHTS",
    "benchmark": "BENCHMARK",
    "m&a": "M&A",
    "ban cap nhat": "UPDATE", "update": "UPDATE",
    "nghien cuu": "RESEARCH", "research": "RESEARCH",
    "bao mat": "SECURITY", "security": "SECURITY",
    "teaser": "TEASER",
}

def standard_label(nhan: str, mac_dinh="TOOL") -> str:
    """Tra ve nhan tieng Anh viet hoa. Khong nhan ra thi giu nguyen viet hoa."""
    if not nhan:
        return mac_dinh
    import unicodedata
    kh = unicodedata.normalize("NFD", str(nhan).strip().lower())
    kh = "".join(c for c in kh if unicodedata.category(c) != "Mn").replace("đ", "d")
    return LABEL_STANDARD.get(kh, str(nhan).strip().upper())
