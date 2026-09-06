#!/usr/bin/env python3
"""duyet_chat.py — CHAT theo topic (brand blog; dcgr da sang gateway): moi vai mot
hang FIFO, semaphore chung CT_CHAT_SONG_SONG, boi canh task gan nhat cho vai, goi
chat_router. Tach tu approve_service.py 06/09/2026 (di chuyen thuan).
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

from html import escape as html_escape

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402
import bang_den                                              # noqa: E402
import chat_router                                          # noqa: E402
import moat_publish                                         # noqa: E402
import tele_util                                            # noqa: E402
import ghi_log                                              # noqa: E402

from duyet_co_so import (  # noqa: E402
    STATE_DIR, _reply_that, call, log, rut,
)
from duyet_giao_viec import (  # noqa: E402
    KANBAN_DB, vai_cua_topic,
)


# HANG DOI CHAT — hai tang, thay cho mot khoa chung ca container (03/09):
#
# 1) Moi PHIEN (tele-<vai>) mot hang FIFO: cung mot vai khong bao gio chay hai
#    luot cung luc (hai tien trinh `chat -c` cung ghi mot phien = hong mach), va
#    tin gui truoc tra loi truoc — threading.Lock khong dam bao thu tu danh thuc,
#    nen dung ve so.
# 2) Mot semaphore chung gioi han SO VAI chay cung luc (CT_CHAT_SONG_SONG, mac
#    dinh 4) — van thu 9router/DeepSeek khoi bi dap don (400 "response_format
#    unavailable", 429) neu co gi do bung no, nhung KHONG duoc la cai lam reply
#    doi nhau. Nguyen tac Ong Chu (04/09): task lam lan luot duoc, reply thi
#    phai song song va nhanh — reply do la viec treo theo het. Mot nguoi go
#    thi thuc te khong hoi qua 3-4 vai cung luc nen 4 gan nhu khong bao gio
#    cham; 429 le te da co chat_router thu lai theo "reset after Ns". Su co
#    04/09 07:19 voi khoa chung: Itachi doi Gin 108s chi de tra loi "xac nhan".
#    Dat CT_CHAT_SONG_SONG=1 la ve dung hanh vi cu.
# Task kanban van tuan tu (max_in_progress: 1) — muc nay chi noi ve chat.
_SO_SONG_SONG = max(1, int(os.environ.get("CT_CHAT_SONG_SONG", "4") or 4))

_CHO_CHAT = threading.BoundedSemaphore(_SO_SONG_SONG)

_DANG_CHAY = {}                                # who -> t0, cac vai dang goi agent

_KHOA_DANG_CHAY = threading.Lock()

class _HangFIFO:
    """Ve so xep hang: acquire() lay so, doi toi luot; release() goi so tiep.
    `vi_tri()` tra ve so nguoi dang dung truoc — de bao Ong Chu con may tin."""

    def __init__(self):
        self._cv = threading.Condition()
        self._phat = 0
        self._phuc_vu = 0

    def lay_so(self) -> tuple:
        """(so cua minh, so nguoi dang dung truoc). Tach khoi doi() de ben goi
        kip bao Ong Chu "con N tin truoc" TRONG LUC cho, khong phai sau."""
        with self._cv:
            so = self._phat
            self._phat += 1
            return so, so - self._phuc_vu

    def doi(self, so):
        with self._cv:
            while so != self._phuc_vu:
                self._cv.wait()

    def release(self):
        with self._cv:
            self._phuc_vu += 1
            self._cv.notify_all()

_HANG_PHIEN = {}                               # session -> _HangFIFO

_KHOA_HANG_PHIEN = threading.Lock()

def _hang_cua(session) -> "_HangFIFO":
    with _KHOA_HANG_PHIEN:
        h = _HANG_PHIEN.get(session)
        if h is None:
            h = _HANG_PHIEN[session] = _HangFIFO()
        return h

def _ai_dang_chay(tru=None) -> str:
    with _KHOA_DANG_CHAY:
        ten = [w for w in _DANG_CHAY if w != tru]
    return ", ".join(sorted(ten)) or "vai khác"

def boi_canh_vai(profile) -> str:
    """Vai chat KHONG nhin thay viec minh vua lam qua kanban: phien chat
    (tele-<vai>) va phien task la hai phien rieng. Su co 03/09/2026 15:14: Ong
    Chu hoi Ethan "chua du 6 anh", Ethan tra loi "session trong, khong co draft
    nao" trong khi 15 phut truoc vua day 3 anh len. Doan nay doc kanban.db lay
    3 task gan nhat cua vai (tieu de, trang thai, tom tat) + ban nhap lien quan,
    ghep vao dau tin de vai tra loi dung viec cua minh."""
    if not profile or not KANBAN_DB.exists():
        return ""
    try:
        con = sqlite3.connect(f"file:{KANBAN_DB}?mode=ro", uri=True)
        rows = con.execute(
            "SELECT t.id, t.title, t.status, t.completed_at, "
            "(SELECT summary FROM task_runs r WHERE r.task_id=t.id "
            " ORDER BY r.rowid DESC LIMIT 1) "
            "FROM tasks t WHERE t.assignee=? "
            "ORDER BY t.created_at DESC LIMIT 3", (profile,)).fetchall()
        con.close()
    except Exception as e:                                   # noqa: BLE001
        log("chat", f"boi canh {profile}: khong doc duoc kanban ({e})")
        return ""
    if not rows:
        return ""
    dong = ["[Việc gần nhất của bạn trên kanban — để trả lời đúng việc mình đã làm]"]
    for tid, title, st, done, tom in rows:
        luc = time.strftime("%d/%m %H:%M", time.localtime(done)) if done else "-"
        dong.append(f"- {tid} [{st}] {title[:90]} (xong {luc})")
        if tom:
            dong.append("    tóm tắt: " + str(tom)[:400].replace("\n", " "))
    dong.append("Bản nháp nằm ở drafts/<draft_id>.png|.json; log gửi Telegram ở "
                f"{STATE_DIR / 'telegram_sent'}/<vai>.jsonl.")
    return "\n".join(dong) + "\n\n"

# Vai CHAY BANG CHAT: ca luong viec cua ho la Ong Chu tha mot tam anh hoac mot
# URL vao topic, khong reply gi ca, agent tu nhan va lam (gin/itachi sua anh,
# bob dung frame). Khong co nut, khong co lenh slash. Neu ap luat "khong reply
# = chi doc" cho ho thi ba vai nay chet han — nen mien tru, va ghi ro o day de
# lan sau khong ai tuong day la sot.
VAI_CHAT_LAM_VIEC = {"gin", "itachi", "bob", "analyst"}
# analyst (Ada) them 06/09/2026 chieu, sau khi audit bat duoc: Ada dung la Jean
# thu hai. SOUL cua Ada la chay ada_chuan_bi.py roi ada_nop.py BANG BASH, ma
# Ada khong co task kanban nao o blog (dem that: 0), khong nut, khong cron rieng,
# va cau hoi cua Ong Chu ("do 7 ngay qua di") KHONG co URL lan anh — nen ca hai
# cua ngo con lai (_reply_that, _tin_dua_viec) deu khong cuu duoc. Bo `safe`
# khong co terminal = Ada chet han, y het Jean.

# Tin DUA VIEC: co anh dinh kem, hoac co URL trong chu. Khong phai tan gau.
_CO_URL = re.compile(r"https?://\S", re.I)


def _tin_dua_viec(msg, text) -> bool:
    """Tin nay co DUA VIEC vao khong (anh hoac URL), hay chi la tan gau.

    Vi sao can, ngoai luat vai (06/09/2026 chieu, sau khi audit bat duoc ba hoi
    quy THAT do ban dau chi khoa theo vai):
      - Jean (teaser) CHET HAN: teaser.SOUL.md:8 "Ong Chu dan mot URL bai vao
        chat... Do la yeu cau viet teaser", roi chay jean_chuan_bi.py /
        jean_nop.py bang bash. Bo `safe` khong co terminal.
      - Skill social-crawl viet RIENG cho duong chat cua Finn/Nova/Vera
        (social-crawl/SKILL.md:6 "dan mot link x.com/instagram.com vao hoi
        thoai") — tinh nang moi them o b2bc852, bi giet ngay.
    Diem chung cua MOI thu bi hong: tin mang theo URL hoac anh. Do cung dung la
    ranh gioi "dua viec" vs "tan gau" — su co Vera 02/09 ("Hom nay ko lam viec
    ?") khong co URL lan anh, nen luat nay van chan dung no."""
    if msg.get("photo"):
        return True
    if str((msg.get("document") or {}).get("mime_type", "")).startswith("image/"):
        return True
    return bool(_CO_URL.search(text or ""))


def _bo_cong_cu_chat(vai, msg, text="") -> str:
    """Toolset cho mot tin chat: None = day du, BO_CHI_DOC = chi doc.

    Luat Ong Chu 06/09/2026: chi BAM NUT hoac REPLY moi tinh la dang lam viec;
    moi tin go troi deu la chat ngoai task. Truoc day luat nay chi la mot loi
    NHAC trong prompt (chat_router.chat_hint) — va loi nhac da tung that bai
    that: 02/09/2026 Vera nhan "Hom nay ko lam viec ?" roi tu chay
    scan_business, doc cron, mo kanban.db, 74 tin, chay 10 phut roi bi giet vi
    het gio. Nay thanh cong that: tin go troi chay voi bo cong cu chi doc, agent
    khong con terminal/write_file/execute_code de ma tu y lam."""
    if vai in VAI_CHAT_LAM_VIEC:
        return None
    if _reply_that(msg):
        return None
    if _tin_dua_viec(msg, text):
        return None                   # dua anh/URL = giao viec, du khong reply
    return chat_router.BO_CHI_DOC

def handle_chat(token, group, msg, thread_id, text):
    """Chuyen tin nhan toi dung agent theo topic, giu mach hoi thoai.

    Gateway cua hermes da tat Telegram (khong the cung long-poll mot token voi
    tien trinh nay), nen day la duong duy nhat de nhan voi LLM qua Telegram.
    Bu lai: dinh tuyen duoc theo topic, moi topic mot phien rieng.
    """
    topics = {}
    tp = env_load.topics_path()
    if tp.exists():
        topics = json.loads(tp.read_text(encoding="utf-8"))
    profile, session = chat_router.route(thread_id, topics)

    who = profile or "trợ lý"
    kw_thread = {"message_thread_id": thread_id} if thread_id else {}
    log("route", f"chat -> profile={profile or '(mac dinh)'} session={session} "
                 f"thread={thread_id} text={rut(text)}")
    # Tang 1: hang FIFO cua rieng phien nay — cung vai thi tin truoc tra loi truoc.
    hang = _hang_cua(session)
    so, truoc = hang.lay_so()
    da_bao = False
    if truoc:
        log("route", f"thread={thread_id} {who} con {truoc} tin truoc trong topic")
        call(token, "sendMessage", chat_id=group, **kw_thread,
             text=f"⏳ <b>{who}</b> đang trả lời {truoc} tin trước trong topic này, "
                  "xong sẽ tới tin này…", parse_mode="HTML")
        da_bao = True
    hang.doi(so)
    try:
        # Tang 2: cho chung — toi da _SO_SONG_SONG vai goi agent cung luc.
        if not _CHO_CHAT.acquire(blocking=False):
            cho_ai = _ai_dang_chay(tru=who)
            log("route", f"thread={thread_id} {who} cho cho, dang chay: {cho_ai}")
            if not da_bao:
                call(token, "sendMessage", chat_id=group, **kw_thread,
                     text=f"⏳ <b>{who}</b> chờ chỗ — đang có <b>{cho_ai}</b> chạy "
                          f"(tối đa {_SO_SONG_SONG} vai cùng lúc), tới lượt sẽ trả lời…",
                     parse_mode="HTML")
            _CHO_CHAT.acquire()
        with _KHOA_DANG_CHAY:
            _DANG_CHAY[who] = time.time()
        try:
            _chat_co_khoa(token, group, thread_id, text, profile, session, who, kw_thread,
                          _bo_cong_cu_chat(vai_cua_topic(thread_id), msg, text))
        finally:
            with _KHOA_DANG_CHAY:
                _DANG_CHAY.pop(who, None)
            _CHO_CHAT.release()
    finally:
        hang.release()

def _chat_co_khoa(token, group, thread_id, text, profile, session, who, kw_thread,
                  toolsets=None):
    call(token, "sendMessage", chat_id=group, **kw_thread,
         text=f"⏳ Đang chuyển cho <b>{who}</b>…", parse_mode="HTML")
    log("chat", f"thread={thread_id} {who} bo cong cu="
                f"{toolsets or 'day du'} (chi doc = tin go troi, khong reply)")

    # Goi agent o thread con de thread nay con ranh bao TIEN DO: qua 2 phut
    # chua xong thi nhan mot dong, de Ong Chu biet la dang chay chu khong phai
    # chet. Truoc day 10 phut im lang roi moi bao het gio.
    ket_qua = {}
    def _goi():
        ket_qua["r"] = chat_router.ask(profile, session, boi_canh_vai(profile) + text,
                                       toolsets=toolsets)
    th = threading.Thread(target=_goi, daemon=True)
    th.start()
    moc_bao = [120, 360]
    t0 = time.time()
    while th.is_alive():
        th.join(5)
        if moc_bao and time.time() - t0 >= moc_bao[0]:
            phut = moc_bao.pop(0) // 60
            call(token, "sendMessage", chat_id=group, **kw_thread,
                 text=f"⏳ {who} vẫn đang xử lý ({phut} phút)… "
                      f"tự dừng ở {chat_router.TIMEOUT_SEC // 60} phút.")
    out, err = ket_qua.get("r") or (None, "Không nhận được kết quả từ agent (thread hỏng).")
    reply = ("⚠️ " + err) if err else chat_router.clean(out)
    log("chat", f"tra loi thread={thread_id} loi={bool(err)} {len(reply)}c: {rut(reply)}")
    # Reply dai vuot 4096 se bi Telegram tu choi/cat -> chia thanh nhieu tin
    # gui lien tiep (dung thu tu), thay vi cat bot phan cuoi.
    for phan in tele_util.chia_tin(reply):
        r = call(token, "sendMessage", chat_id=group, **kw_thread,
                 text=phan, disable_web_page_preview=True)
        if not r.get("ok"):
            # Thu lai KHONG parse/ky tu la — thuong loi la do noi dung; mat
            # dinh dang con hon mat cau tra loi.
            call(token, "sendMessage", chat_id=group, **kw_thread,
                 text="⚠️ Không gửi được trả lời gốc (" + str(r.get("description"))
                      + "). Bản rút gọn:\n" + phan[:1500])
