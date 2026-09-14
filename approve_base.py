#!/usr/bin/env python3
"""approve_base.py — NEN dung chung cua dich vu duyet: hang so duong dan/brand, goi
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
import sys
import threading
import time
from pathlib import Path


import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402
import tele_util                                            # noqa: E402
import write_log                                              # noqa: E402


log, rut = write_log.log, write_log.shorten

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

env_load.load()                            # nap secret.<brand>.env de co BRAND luc import

# MOT num brand duy nhat: CT_BRAND ('dcgr'|'blog') la khoa container cua env_load.
# BRAND (ten content-brand day du) SUY tu CT_BRAND — truoc day la hai bien doc lap
# voi hai bo gia tri, dat lech mot trong hai la content di nham brand. Van cho
# BRAND trong env de len (tuong thich nguoc), nhung cau hinh chuan chi can CT_BRAND.
_TEN_BRAND = env_load.BRAND_LONG        # mot bang, o env_load (ADF-r2-10)

BRAND = (os.environ.get("BRAND")
         or _TEN_BRAND.get(os.environ.get("CT_BRAND", ""), "donniechublog"))

def load_secrets():
    env_load.load()
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

def _write_json(path, data, indent=2):
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
    # ADF-r2-11: pid+thread va don tmp khi hong nay nam trong env_load.ghi_json
    # (mot ban cho 4 cho tung tu viet). Giu ten ham cho ho duyet_*.
    env_load.write_json(path, data, indent=indent)

_KHOA_DRAFT = {}                       # draft_id -> Lock: hai nut cua CUNG mot bai chay lan luot

_KHOA_KHOA_DRAFT = threading.Lock()

def _lock_of(draft_id):
    with _KHOA_KHOA_DRAFT:
        return _KHOA_DRAFT.setdefault(draft_id or "", threading.Lock())

def _run_background(ten, fn, token, group, thread_id, *args):
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
                      f"Chi tiết trong log approve của container {write_log.brand()}.")
    threading.Thread(target=_boc, daemon=True, name=f"{ten}-{thread_id}").start()

def _send_text(token, chat, text, thread=None):
    """Gui `text` (co the dai) thanh MOT hoac NHIEU tin neu vuot gioi han
    sendMessage, thay vi de Telegram tu choi ca tin. Tra ve response cua tin
    cuoi; dung va tra ve ngay neu mot tin bi tu choi."""
    res = None
    for phan in tele_util.split_message(text):
        kw = {"chat_id": chat, "text": phan, "parse_mode": "HTML",
              "disable_web_page_preview": True}
        if thread:
            kw["message_thread_id"] = int(thread)
        res = call(token, "sendMessage", **kw)
        if isinstance(res, dict) and not res.get("ok"):
            return res
    return res

def _reply_real(msg: dict):
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

def _extract_line(body: str, nhan: str) -> str:
    m_ = re.search(r"^" + re.escape(nhan) + r"\s*:\s*(.+)$", body or "", re.M)
    return (m_.group(1).strip() if m_ else "")

BOSS_IDS = STATE_DIR / "ong_chu.json"    # [user_id...] duoc phep ra lenh

def _load_json(path, mac_dinh):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return mac_dinh


def is_boss(msg) -> bool:
    """Tin nhan / nut bam nay co den tu nguoi duoc phep ra lenh khong.

    Nhan ca `message` lan `callback_query` — ca hai deu co truong `from`.

    KHONG co state/ong_chu.json = cho qua het (hanh vi cu: group rieng, chi co
    Ong Chu). Co tep thi MOI cua deu phai kiem — truoc 06/09/2026 chi hai cho
    kiem (lenh slash o approve_command, ly do lam lai o approve_post) trong khi ba cua
    con lai thi khong:

      - nut Duyet/Bo/Lam lai  -> bam ✅ la bai len channel VA day sang moat
      - lenh chon so          -> tao cap task, tot LLM that
      - chat                  -> agent chay voi bo cong cu day du

    Ba cua do la ba cua nang nhat. Co co che ma che duoc 2/5 con nguy hiem hon
    khong co: no tao cam giac da khoa cua.
    """
    cho_phep = _load_json(BOSS_IDS, [])
    if not cho_phep:
        return True
    return ((msg or {}).get("from") or {}).get("id") in cho_phep
