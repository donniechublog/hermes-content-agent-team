#!/usr/bin/env python3
"""duyet_giao_viec.py — BANG VAI (slug <-> ten <-> mac dinh anh/viet), tao task
kanban qua hermes CLI, doc kanban.db (trang thai/run/bang chung "xong ma khong
giao"), bang den swarm, bao tien do vao topic. Tach tu approve_service.py 06/09/2026
(di chuyen thuan, xem duyet_co_so.py).
"""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from html import escape as html_escape


sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402
import bang_den                                              # noqa: E402
import ghi_log                                              # noqa: E402
import hermes_adapter                                        # noqa: E402
import vai                                                   # noqa: E402

from duyet_co_so import (  # noqa: E402
    HERMES_HOME, HERMES_PY, ROOT, STATE_DIR, _ghi_json, call, log,
)


def _bao_nhan_viec(token, group, vai, tu_vai, title, tid, ly_do=""):
    """Bao NGAY vao topic cua vai nhan viec, ca khi Ong Chu giao task moi (tu_vai=None)
    lan khi viec duoc CHUYEN tu vai khac (Ong Chu 05/09/2026: "it nhat cung thong bao
    de biet da nhan job"; mo rong 08/09/2026 sang CA task moi giao, khong chi hang
    chuyen — truoc do task moi tao trong duyet_chon_tin.py im lang cho toi khi dispatcher
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
    truoc = hermes_adapter.dem_dang_chay(tru_tid=tid)
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

# BANG VAI da gom vao `vai.py` (audit A4/F1) — them mot vai = them MOT dong o
# do, khong phai sua sau cho nhu truoc. Cac ten duoi day giu nguyen la MAT TIEN
# cho ho duyet_* (duyet_lenh/duyet_chon_tin/duyet_bai) va test dang goi qua
# `duyet_giao_viec.X`; ly do ton tai cua tung bang nam trong vai.py.
VAI_ANH = vai.VAI_ANH
VAI_CAROUSEL = vai.VAI_CAROUSEL
VAI_EDU = vai.VAI_EDU
TEN_SANG_CAP = vai.TEN_SANG_CAP
TEN_VAI_ANH = vai.TEN_VAI_ANH
TEN_VAI_VIET = vai.TEN_VAI_VIET
SLUG_CU = vai.SLUG_CU
MAC_DINH_ANH = vai.MAC_DINH_ANH
MAC_DINH_VIET = vai.MAC_DINH_VIET

def vai_cua_topic(thread_id):
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

# SLUG_CU (slug cu -> slug profile; su co 01/09/2026 hai bai dcgr ket 2 ngay vi
# sidecar ghi "dre"/"miles") nay la VIEW cua vai.py — dong 69 o tren. Truoc audit
# lượt 2 (ADF-r2-1) mot bang chep tay o day ghi de no 21 dong sau khi gan, nen
# them slug_cu vao vai.py KHONG toi duoc day (chua lo chi vi hai bang dang trung).

def chuan_assignee(assignee):
    """Tra ve slug profile thuc co trong home container, hoac (None, loi)."""
    slug = vai.slug_that(assignee)
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
    assignee, loi = chuan_assignee(assignee)
    if loi:
        log("kanban", f"tu choi tao '{title[:60]}': {loi}")
        return None, loi
    tid, loi = hermes_adapter.tao_task(title, assignee, body, parent=parent)
    if loi:
        log("kanban", f"tao '{title[:60]}' cho {assignee} LOI: {loi[:200]}")
        return None, loi
    log("kanban", f"tao task {tid} cho {assignee}: {title[:60]}")
    return tid, None

# Kanban cua home container hien tai. Viec bi chan/that bai duoc bao qua
# bao_tien_do_kanban (kem ly do); ham bao_viec_bi_chan rieng truoc day trung
# viec voi no va bo sot Kite, da bo 05/09/2026.
DA_BAO_TIEN_DO = STATE_DIR / "da_bao_tien_do.json"   # {task_id: trang thai da bao}
TIN_KET_QUA = STATE_DIR / "tin_ket_qua_task.json"    # {task_id: {chat,thread,mid}}
DA_BAO_TREO = STATE_DIR / "da_bao_treo.json"         # {task_id: epoch lan bao "treo" cuoi}
NGUONG_TREO_PHUT = 20          # running lau hon nay ma khong doi trang thai -> nghi treo
LAI_BAO_TREO_PHUT = 30         # con treo thi nhac lai sau moi khoang nay

_TEN_HIEN = vai.TEN_HIEN            # xem vai.py

# Moi bai mot the goc (bang_den.py), Dre/Miles/Ada la con cua no. Ly do va so do
# o dau bang_den.py. O day chi co ba mieng noi vao luong san:
#   create_pair  -> tao the goc, task Dre parent=goc
#   imgok        -> task Miles parent=[Dre, goc]  (cong "Ong Chu duyet anh" giu nguyen)
#   tien do      -> ban giao cua Miles da nam tren bang den qua kanban_complete.
# Task "Ada soat" tung nam o day (sang 05/09) da bo chieu 05/09: mot task LLM moi
# bai cho viec caption_check gio lam bang code (so trong caption phai co trong tu lieu).
# Chi bat cho brand trong CT_BANG_DEN (mac dinh: dcgr). Blog dang la nhom doi chung
# cua tuan do bot-mode (05–12/09) va Ong Chu chi yeu cau dcgr — code chung nhung
# hanh vi blog phai y nguyen. Bat blog: Environment=CT_BANG_DEN=dcgr,blog trong unit.
BANG_DEN_BRANDS = {b.strip() for b in os.environ.get("CT_BANG_DEN", "dcgr").split(",") if b.strip()}

BANG_DEN_ASSIGNEE = "ban_bien_tap"     # trung voi bang_den.ROOT_ASSIGNEE

BANG_DEN_NHAC = """

== BANG DEN (kanban) ==
The goc cua bai: {root}. Ban giao cua vai truoc nam o muc "Parent task results"
trong context task nay; can them thi goi tool kanban_show(task_id="{root}").
Script nop (*_nop.py) TU ghi len bang den — ban khong phai ghi. Phan cua ban khi
xong: goi tool kanban_complete voi summary = dong "Ket qua task" va metadata =
JSON o dong "[metadata]" ma script in ra. Khong tu bia so lieu vao metadata."""

def _bang_den_root(draft_id, title, goal=""):
    """Tao the goc qua bang_den.py (python cua hermes, kanban.db cua container).
    Tra ve id hoac None — KHONG bao gio chan viec tao task Dre. None cung la
    cach TAT ca lop bang den (khong parent, khong Ada) cho brand khong bat."""
    if ghi_log.brand() not in BANG_DEN_BRANDS:
        return None
    try:
        r = subprocess.run(
            [str(HERMES_PY), str(ROOT / "bang_den.py"), "root", draft_id,
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

def _bang_den_ghi(draft_id, key, value):
    """Ghi mot muc len bang den qua bang_den.ghi_nen (python cua hermes, tien
    trinh con). Best-effort, khong nem."""
    ok, loi = bang_den.ghi_nen(draft_id, key, value, "approve_service", hermes_home=HERMES_HOME)
    if not ok:
        log("bangden", f"{draft_id}: ghi '{key}' loi: {loi}")

def _trang_thai_task(tid):
    """Trang thai hien tai cua mot task; '' neu task khong co; None neu KHONG DOC
    DUOC kanban (C1 — hai thu nay khac nhau, nguoi goi phai phan biet).

    Truoc audit lượt 2 (C-r2-3) ham nay ep None ve '' — kanban hong luc bam
    Duyet thi task Miles duoc tao khong co cha (mat ban giao cua Dre) ma note
    van bao "✅", va nut Duyet bam lai tra cau co dinh "dang duoc viet" — dung
    loi c81e6e6 sua. Doc qua hermes_adapter — noi duy nhat biet schema (C2)."""
    return hermes_adapter.trang_thai(tid)

def _tom_tat_run(tid):
    """(summary, metadata_dict) cua lan chay cuoi cua task — cai vai vua ban giao."""
    run = hermes_adapter.lan_chay_cuoi(tid)
    if not run:                                  # None (khong doc duoc) hoac {} (chua chay)
        return "", {}
    # Y het `coalesce(summary, error, '')` cu: chi roi sang `error` khi summary
    # la NULL, KHONG roi khi summary la chuoi rong.
    tom = run.get("tom_tat")
    if tom is None:
        tom = run.get("loi")
    return (tom or ""), run.get("metadata") or {}

def ly_do_task(tid):
    """Ban cong khai cua _tom_tat_run: chi can cau ly do, khong can metadata —
    dung khi tra loi lai nut bam (duyet_bai.py) ve mot task da blocked/failed."""
    tom_tat, _md = _tom_tat_run(tid)
    return tom_tat

def link_ket_qua(tid):
    """Link Telegram toi dong tien do (start/done/blocked...) da gui cho task
    nay, hoac None neu chua co (chua bao lan nao, hoac gui trong DM khong lam
    duoc deep-link). Ghi boi bao_tien_do_kanban() moi khi gui mot dong."""
    if not tid:
        return None
    try:
        tin = json.loads(TIN_KET_QUA.read_text(encoding="utf-8")) if TIN_KET_QUA.exists() else {}
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

def _xong_ma_khong_giao(tid, ai, created_at):
    """Vai anh dong task `done` ma KHONG gui album/the nao len topic — tra ve ly do
    de bao ⛔ thay vi ✅; None neu co san pham that.

    Su co 05/09/2026 07:27 (bai Nvidia/Thinking Machines): brief chi co 1 anh lac
    de, Dre bo cuoc nhung goi kanban_complete voi metadata tu che
    {"kind": "carousel_abort"} thay vi kanban_block -> kanban ghi done, topic bao
    "✅ Dre xong", Ong Chu: "bao xong ma co thay lam gi dau". Kanban tin loi vai;
    o day tin BANG CHUNG: nhat ky gui Telegram cua vai (telegram_sent/<vai>.jsonl)
    phai co mot dong SAU luc task duoc tao."""
    if ai not in TEN_VAI_ANH:
        return None
    tom_tat, md = _tom_tat_run(tid)
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

def bao_tien_do_kanban(token, group):
    """Bao TIEN DO hang doi kanban ve Telegram: task bat dau -> mot dong vao
    topic cua vai kem so viec con xep hang; task xong/hong -> mot dong nua;
    task chay QUA LAU ma khong doi trang thai (worker treo/chet) -> canh bao
    rieng, nhac lai moi LAI_BAO_TREO_PHUT toi khi het treo.

    Vi sao: tu 03/09/2026 moi container chay MOT task mot luc. Sang 04/09 Ong
    Chu chon 7 bai luc 05:33, Dre lam bai 1, sau bai kia + Nova xep hang ca
    tieng — va khong ai noi gi, trong nhu he thong dung. Hang doi la thiet ke,
    im lang thi khong. Chay moi vong poll (~50s), chi bao khi trang thai doi."""
    if not hermes_adapter.co_kanban():
        return
    try:
        da = json.loads(DA_BAO_TIEN_DO.read_text(encoding="utf-8")) if DA_BAO_TIEN_DO.exists() else {}
    except Exception:                                        # noqa: BLE001
        da = {}
    try:
        tin = json.loads(TIN_KET_QUA.read_text(encoding="utf-8")) if TIN_KET_QUA.exists() else {}
    except Exception:                                        # noqa: BLE001
        tin = {}
    try:
        treo = json.loads(DA_BAO_TREO.read_text(encoding="utf-8")) if DA_BAO_TREO.exists() else {}
    except Exception:                                        # noqa: BLE001
        treo = {}
    rows = hermes_adapter.viec(tu_ts=time.time() - 86400)
    if rows is None:                 # co tep ma doc khong duoc -> phai keu
        log("tiendo", "khong doc duoc kanban")
        return
    cho = [r for r in rows if r["trang_thai"] == "ready"]
    tp = env_load.topics_path()
    try:
        topics = json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else {}
    except Exception:                                        # noqa: BLE001
        topics = {}
    now = time.time()
    doi = doi_treo = False
    for v in rows:
        tid, ai, st = v["id"], v["vai"], v["trang_thai"]
        title, _c = v["tieu_de"], v["tao_luc"]
        if st == "running" and ai != BANG_DEN_ASSIGNEE and v.get("bat_dau_luc"):
            phut = (now - v["bat_dau_luc"]) / 60
            if phut >= NGUONG_TREO_PHUT and now - treo.get(tid, 0) >= LAI_BAO_TREO_PHUT * 60:
                ten_treo = _TEN_HIEN.get(ai, ai)
                thread_treo = topics.get(ai)
                call(token, "sendMessage", chat_id=group,
                     **({"message_thread_id": thread_treo} if thread_treo else {}),
                     text=(f"⚠️ <b>{ten_treo}</b> không phản hồi hơn {int(phut)} phút: "
                           f"<i>{html_escape(title[:80])}</i> (task {tid})"),
                     parse_mode="HTML")
                treo[tid] = now
                doi_treo = True
                log("tiendo", f"{tid} {ai} treo {int(phut)} phut, da bao")
        elif tid in treo:
            del treo[tid]                    # roi running (hoac chuyen vai) -> het treo
            doi_treo = True
        if st in ("ready", "todo", "triage") or da.get(tid) == st:
            continue
        if ai == BANG_DEN_ASSIGNEE:          # the goc/bang den: khong phai viec cua ai
            da[tid] = st
            doi = True
            continue
        ten = _TEN_HIEN.get(ai, ai)
        if st == "running":
            sau = len(cho)
            text = (f"▶️ <b>{ten}</b> bắt đầu: <i>{html_escape(title[:80])}</i>"
                    + (f"\n(còn {sau} việc xếp hàng sau việc này)" if sau else ""))
        elif st == "done":
            gia = _xong_ma_khong_giao(tid, ai, _c)
            if gia:
                text = (f"⛔ <b>{ten}</b> báo xong nhưng <b>không có sản phẩm</b>: "
                        f"<i>{html_escape(title[:80])}</i>\n{html_escape(gia.strip()[:500])}\n"
                        "(Task đóng sai cách — vai phải dùng kanban_block khi thiếu ảnh.)")
                log("bangden", f"{tid} {ai} done-gia: {gia[:120]}")
            else:
                text = f"✅ <b>{ten}</b> xong: <i>{html_escape(title[:80])}</i>"
        elif st in ("blocked", "failed"):
            # Kem LY DO (summary/error cua lan chay cuoi) — day la cai Ong Chu can
            # de go: vai anh block vi thieu anh that thi bao ro anh nao bi loai.
            ly_do, _ = _tom_tat_run(tid)
            text = (f"⛔ <b>{ten}</b> dừng ({st}): <i>{html_escape(title[:80])}</i>"
                    + (f"\n{html_escape(ly_do.strip()[:400])}" if ly_do.strip() else "")
                    + ("\nBài đi kèm đang chờ, sẽ không chạy tới khi việc ảnh được gỡ."
                       if ai in TEN_VAI_ANH else ""))
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
    # do; sua kem trong doi nay vi TIN_KET_QUA/DA_BAO_TREO moi cung se hong theo).
    song = {r["id"] for r in rows}
    if doi:
        da = {k: v for k, v in da.items() if k in song}
        tin = {k: v for k, v in tin.items() if k in song}
        try:
            _ghi_json(DA_BAO_TIEN_DO, da, indent=None)
            _ghi_json(TIN_KET_QUA, tin, indent=None)
        except OSError as e:
            log("tiendo", f"khong ghi duoc {DA_BAO_TIEN_DO.name}/{TIN_KET_QUA.name}: {e}")
    if doi_treo:
        treo = {k: v for k, v in treo.items() if k in song}
        try:
            _ghi_json(DA_BAO_TREO, treo, indent=None)
        except OSError as e:
            log("tiendo", f"khong ghi duoc {DA_BAO_TREO.name}: {e}")

# Nhan category dung TIENG ANH. Ong Chu chot: bo tieng Viet o nhan de khoi phat
# sinh loi dau. Nhan la tu ngan, doc gia ky thuat quen ca hai thu tieng, ma
# tieng Anh thi khong co dau nen khong bao gio go sai.
#
# Bang tra nhan ca ban tieng Viet cu (co dau lan mat dau) de manifest cu van
# chuan hoa dung, khong phai viet lai.
NHAN_CHUAN = {
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

def chuan_nhan(nhan: str, mac_dinh="TOOL") -> str:
    """Tra ve nhan tieng Anh viet hoa. Khong nhan ra thi giu nguyen viet hoa."""
    if not nhan:
        return mac_dinh
    import unicodedata
    kh = unicodedata.normalize("NFD", str(nhan).strip().lower())
    kh = "".join(c for c in kh if unicodedata.category(c) != "Mn").replace("đ", "d")
    return NHAN_CHUAN.get(kh, str(nhan).strip().upper())
