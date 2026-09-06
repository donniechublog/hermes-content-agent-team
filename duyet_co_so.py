#!/usr/bin/env python3
"""duyet_co_so.py — NEN dung chung cua dich vu duyet: hang so duong dan/brand, goi
Telegram (`call`), ghi JSON nguyen tu, khoa theo draft, chay nen co boc loi, doc
reply. Khong phu thuoc module duyet_* nao khac — moi module khac import tu day.

Tach tu approve_service.py ngay 06/09/2026: tep do phinh 441 -> 2372 dong trong 17
ngay, gom 9 trach nhiem (audit 05/09 goi la god-file). Tach la DI CHUYEN THUAN:
than ham giu nguyen tung ky tu, chi doi cho o. approve_service.py con lai vong
poll + dieu phoi tin nhan, va van re-export moi ten cu.
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


log, rut = ghi_log.log, ghi_log.rut

ROOT = env_load.ROOT

DRAFTS = ROOT / "drafts"

STATE_DIR = env_load.state_dir()          # state/<brand>/ theo container (fallback state/)

OFFSET = STATE_DIR / "offset.txt"

TELEGRAM_INCOMING = STATE_DIR / "telegram_incoming"   # anh tai ve tu tin nhan reply

API = "https://api.telegram.org/bot{token}/{method}"

HERMES_PY = env_load.HERMES_PY

# HERMES_HOME theo container: moi brand mot home rieng (~/.hermes-<brand>).
# Systemd/cron dat san; roi ve ~/.hermes o che do don cu.
HERMES_HOME = str(env_load.hermes_home())

env_load.nap()                            # nap secret.<brand>.env de co BRAND luc import

# MOT num brand duy nhat: CT_BRAND ('dcgr'|'blog') la khoa container cua env_load.
# BRAND (ten content-brand day du) SUY tu CT_BRAND — truoc day la hai bien doc lap
# voi hai bo gia tri, dat lech mot trong hai la content di nham brand. Van cho
# BRAND trong env de len (tuong thich nguoc), nhung cau hinh chuan chi can CT_BRAND.
_TEN_BRAND = {"blog": "donniechublog", "dcgr": "dcgr"}

BRAND = (os.environ.get("BRAND")
         or _TEN_BRAND.get(os.environ.get("CT_BRAND", ""), "donniechublog"))

def load_secrets():
    env_load.nap()
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not tok:
        sys.exit("Thieu TELEGRAM_BOT_TOKEN")
    return (tok,
            os.environ.get("TELEGRAM_CHANNEL_ID"),
            os.environ.get("TELEGRAM_GROUP_ID"))

def call(token, method, **kw):
    """Goi Bot API. LUON tra ve dict; loi mang -> {"ok": False, "description"}.

    Truoc day nem exception: trong thread nen thi thread chet im, trong vong
    poll thi ca lo update con lai bi bo. Gio moi loi deu thanh mot dong log +
    mot ket qua doc duoc, nguoi goi tu quyet."""
    try:
        with httpx.Client(timeout=90) as c:
            r = c.post(API.format(token=token, method=method), json=kw)
        res = r.json()
    except Exception as e:                                   # noqa: BLE001
        res = {"ok": False, "description": f"{type(e).__name__}: {e}"}
    if not res.get("ok") and method != "getUpdates":
        log("tele", f"{method} tu choi: {res.get('description')} | "
                    f"thread={kw.get('message_thread_id')} text={rut(kw.get('text'), 60)}")
    return res

def _ghi_json(path, data, indent=2):
    """Ghi mot tep state JSON NGUYEN TU: tmp cung thu muc + os.replace.

    Vi sao 06/09/2026: ca tep nay ghi state bang write_text thang, trong khi
    offset.txt/dat_bai.json (va moat_publish, bat_buoc, emoji_deck...) da di qua
    tmp tu lau. write_text CAT NGAN tep cu truoc khi ghi noi dung moi: dich vu
    bi restart hay het cho dia dung giua hai buoc do se de lai mot sidecar cut,
    va moi nguoi doc sau do (nut Duyet, vai anh, moat) nem ValueError — bai ket
    vinh vien ma khong ai biet.

    Ten tmp mang pid + thread id vi nhieu thread nen cung ghi mot tep state
    (nut chay nen, vong poll): dung chung mot ten tmp thi hai ban ghi lai lan
    vao nhau roi ban lai lan do moi la cai duoc replace."""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_name(f"{p.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    try:
        tmp.write_text(json.dumps(data, ensure_ascii=False, indent=indent),
                       encoding="utf-8")
        os.replace(tmp, p)
    except BaseException:
        tmp.unlink(missing_ok=True)              # khong de lai rac .tmp
        raise

_KHOA_DRAFT = {}                       # draft_id -> Lock: hai nut cua CUNG mot bai chay lan luot

_KHOA_KHOA_DRAFT = threading.Lock()

def _khoa_cua(draft_id):
    with _KHOA_KHOA_DRAFT:
        return _KHOA_DRAFT.setdefault(draft_id or "", threading.Lock())

def _chay_nen(ten, fn, token, group, thread_id, *args):
    """Chay `fn` o thread nen, BOC de khong bao gio chet im.

    Moi nhanh xu ly (chat, lenh, chon so) deu qua day: loi gi cung ghi log day
    du traceback VA gui mot dong ⚠️ ve dung topic. Nguyen tac: Ong Chu nhan
    tin, thi luon co tin tra ve — ke ca tin bao hong."""
    import traceback

    def _boc():
        t0 = time.time()
        try:
            fn(*args)
            log(ten, f"xong sau {time.time() - t0:.0f}s thread={thread_id}")
        except Exception as e:                               # noqa: BLE001
            log("loi", f"{ten} hong: {type(e).__name__}: {e}\n"
                       + traceback.format_exc())
            call(token, "sendMessage", chat_id=group,
                 **({"message_thread_id": thread_id} if thread_id else {}),
                 text=f"⚠️ Lỗi khi xử lý ({ten}): {type(e).__name__}: {str(e)[:300]}\n"
                      f"Chi tiết trong log approve của container {ghi_log.brand()}.")
    threading.Thread(target=_boc, daemon=True, name=f"{ten}-{thread_id}").start()

def _gui_chu(token, chat, text, thread=None):
    """Gui `text` (co the dai) thanh MOT hoac NHIEU tin neu vuot gioi han
    sendMessage, thay vi de Telegram tu choi ca tin. Tra ve response cua tin
    cuoi; dung va tra ve ngay neu mot tin bi tu choi."""
    res = None
    for phan in tele_util.chia_tin(text):
        kw = {"chat_id": chat, "text": phan, "parse_mode": "HTML",
              "disable_web_page_preview": True}
        if thread:
            kw["message_thread_id"] = int(thread)
        res = call(token, "sendMessage", **kw)
        if isinstance(res, dict) and not res.get("ok"):
            return res
    return res

def _reply_that(msg: dict):
    """Tin ma Ong Chu THUC SU bam Reply vao, hoac None neu chi go troi.

    Trong sieu nhom co topic (is_forum), Telegram GAN SAN reply_to_message cho
    MOI tin trong topic — tro toi tin dich vu tao topic, va tin do do CHINH BOT
    tao ra. Nen ca hai cach kiem cu deu luon dung, khong phan biet duoc gi:
    "co reply_to_message khong" va "reply toi mot tin cua bot khong".

    Bang chung 06/09/2026 (msg=657, go troi mot chu "5" trong topic Nova):
        reply_to_message = {"message_id": 16, "message_thread_id": 16,
                            "from": {"is_bot": true, "username": "hermesdcmodebot"},
                            "forum_topic_created": {...}}

    Tin goc topic nhan ra bang forum_topic_created, va message_id cua no CHINH
    LA message_thread_id. Loc dung no ra thi phan con lai moi la reply that."""
    rt = msg.get("reply_to_message")
    if not rt:
        return None
    if rt.get("forum_topic_created") is not None:
        return None
    if rt.get("message_id") == msg.get("message_thread_id"):
        return None
    return rt

def _boc_dong(body: str, nhan: str) -> str:
    m_ = re.search(r"^" + re.escape(nhan) + r"\s*:\s*(.+)$", body or "", re.M)
    return (m_.group(1).strip() if m_ else "")

ONG_CHU_IDS = STATE_DIR / "ong_chu.json"    # [user_id...] duoc phep ra lenh

def _nap_json(path, mac_dinh):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return mac_dinh
