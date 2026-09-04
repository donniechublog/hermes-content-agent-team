#!/usr/bin/env python3
"""Dich vu Telegram cho content-team: duyet bai (nut bam) + chon tin (reply so).

Chi MOT tien trinh duoc long-poll mot bot token voi mot offset -- Telegram
getUpdates xac nhan (va xoa khoi hang doi) MOI update tinh toi offset, khong
chi loai dang loc qua allowed_updates. Chay hai poller doc lap se lam rot
update cua nhau. Vi vay dich vu nay xu ly ca hai luong trong cung mot vong lap:

  A) callback_query -- nut Duyet/Bo tren ban nhap draft (nhu truoc)
  B) message -- Ong Chu reply so thu tu trong topic scout -> tao cap task
     vai anh + vai viet cho dung tin da chon trong manifest cua Finn
  C) lenh slash -- /bai <url> <vai> dat bai TAY tu mot URL bat ky, khong qua
     vong quet cua Finn. Tuong minh: dung cu phap moi lam, sai la bao ngan
     roi dung — KHONG roi ve hoi thoai nhu tin thuong, khong doan y.
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
import chat_router                                          # noqa: E402
import moat_publish                                         # noqa: E402
import tele_util                                            # noqa: E402
import ghi_log                                              # noqa: E402
log, rut = ghi_log.log, ghi_log.rut

ROOT = Path.home() / "content-team"
import env_load                                              # noqa: E402
DRAFTS = ROOT / "drafts"
STATE_DIR = env_load.state_dir()          # state/<brand>/ theo container (fallback state/)
OFFSET = STATE_DIR / "offset.txt"
TELEGRAM_INCOMING = STATE_DIR / "telegram_incoming"   # anh tai ve tu tin nhan reply
API = "https://api.telegram.org/bot{token}/{method}"
HERMES_PY = Path.home() / "hermes-agent" / "venv" / "bin" / "python"
# HERMES_HOME theo container: moi brand mot home rieng (~/.hermes-<brand>).
# Systemd/cron dat san; roi ve ~/.hermes o che do don cu.
HERMES_HOME = os.environ.get("HERMES_HOME", str(Path.home() / ".hermes"))
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


# ---------- A) duyet ban nhap (khong doi so voi truoc) ----------

def keyboard(draft_id):
    return {"inline_keyboard": [[
        {"text": "✅ Duyệt & đăng", "callback_data": "ok:" + draft_id},
        {"text": "❌ Bỏ", "callback_data": "no:" + draft_id},
    ]]}


def _send_media_group(token, chat, media, thread_id=None):
    """Gui album anh xem truoc. Album KHONG the gan nut bam -- gioi han Bot API.

    `media` la duong dan CUC BO (draft_write ghi duong dan tuyet doi tren may
    nay) nen phai upload bang attach:// nhu publish() lam. Truoc day gui thang
    chuoi duong dan cho Telegram — Telegram khong doc duoc may minh, album KHONG
    BAO GIO hien, va gia tri tra ve bi vut nen loi im lang: Ong Chu duyet mu moi
    bai nhieu anh tu ngay dau."""
    items, files = [], {}
    for i, m in enumerate(media):
        m = str(m)
        if m.startswith("http://") or m.startswith("https://"):
            items.append({"type": "photo", "media": m})
        else:
            if not Path(m).exists():
                continue
            key = f"file{i}"
            items.append({"type": "photo", "media": f"attach://{key}"})
            files[key] = open(m, "rb")
    if not items:
        return {"ok": False, "description": "khong co anh nao ton tai"}
    data = {"chat_id": chat, "media": json.dumps(items)}
    if thread_id:
        data["message_thread_id"] = str(int(thread_id))
    try:
        with httpx.Client(timeout=120) as c:
            r = c.post(API.format(token=token, method="sendMediaGroup"),
                       data=data, files=files or None)
    finally:
        for fh in files.values():
            fh.close()
    return r.json()


def draft_push(token, group, draft_id, thread_id=None):
    d = json.loads((DRAFTS / (draft_id + ".json")).read_text(encoding="utf-8"))
    caption = "<b>BẢN NHÁP</b>\n\n" + d["caption"]
    payload = {"chat_id": group, "caption": caption, "parse_mode": "HTML",
               "reply_markup": keyboard(draft_id)}
    if thread_id:
        payload["message_thread_id"] = int(thread_id)

    images = d.get("images")
    if images:
        # Album truoc (khong nut), roi tin nhan chu rieng kem nut duyet --
        # nut bam luon nam tren tin nhan NAY, khong phai anh.
        ra = _send_media_group(token, group, images, thread_id)
        if not ra.get("ok"):
            # KHONG nuot loi: Ong Chu phai biet minh dang duyet thieu anh.
            caption += ("\n\n\u26a0\ufe0f Album xem truoc gui loi: "
                        + html_escape(str(ra.get("description"))))
        text_payload = {"chat_id": group, "text": caption, "parse_mode": "HTML",
                        "reply_markup": keyboard(draft_id)}
        if thread_id:
            text_payload["message_thread_id"] = int(thread_id)
        return call(token, "sendMessage", **text_payload)

    img = d.get("image")
    if img and Path(img).exists():
        with httpx.Client(timeout=120) as c, open(img, "rb") as fh:
            r = c.post(API.format(token=token, method="sendPhoto"),
                       data={k: (json.dumps(v) if k == "reply_markup" else v)
                             for k, v in payload.items()},
                       files={"photo": (Path(img).name, fh, "image/png")})
        return r.json()
    payload["text"] = payload.pop("caption")
    return call(token, "sendMessage", **payload)


CAPTION_LIMIT = 1024      # gioi han caption cua sendPhoto / sendMediaGroup


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


def publish(token, channel, draft_id):
    """Dang draft len channel.

    Caption dai (teaser thuong 3000+ ky tu) VUOT gioi han 1024 cua caption anh.
    Truong hop do: gui anh truoc khong caption, roi gui chu rieng — thay vi de
    Telegram tu choi ca bai.
    """
    d = json.loads((DRAFTS / (draft_id + ".json")).read_text(encoding="utf-8"))
    caption = d["caption"]
    long_caption = len(caption) > CAPTION_LIMIT

    images = d.get("images")
    if images:
        # Anh co the la URL (teaser lay tu bai goc) HOAC tep cuc bo (the do vai dung anh
        # dung + anh that tai ve). Tep cuc bo phai dinh kem multipart qua
        # attach://, khong the truyen duong dan — Telegram khong doc duoc o may ta.
        items, files = [], {}
        for i, m in enumerate(images[:10]):          # Telegram cho toi da 10
            e = {"type": "photo"}
            if str(m).startswith("http"):
                e["media"] = str(m)
            else:
                pth = Path(m)
                if not pth.exists():
                    continue
                khoa = f"anh{i}"
                e["media"] = f"attach://{khoa}"
                files[khoa] = (pth.name, pth.read_bytes(), "image/png")
            if not items and not long_caption:
                e["caption"] = caption
                e["parse_mode"] = "HTML"
            items.append(e)
        with httpx.Client(timeout=180) as c:
            r = c.post(API.format(token=token, method="sendMediaGroup"),
                       data={"chat_id": channel, "media": json.dumps(items)},
                       files=files or None)
        res = r.json()
        if long_caption and res.get("ok"):
            return _gui_chu(token, channel, caption)
        return res

    img = d.get("image")
    if img and Path(img).exists():
        with httpx.Client(timeout=120) as c, open(img, "rb") as fh:
            data = {"chat_id": channel, "parse_mode": "HTML"}
            if not long_caption:
                data["caption"] = caption
            r = c.post(API.format(token=token, method="sendPhoto"),
                       data=data,
                       files={"photo": (Path(img).name, fh, "image/png")})
        res = r.json()
        if long_caption and res.get("ok"):
            return _gui_chu(token, channel, caption)
        return res
    return _gui_chu(token, channel, caption)


def mark_draft(draft_id, status):
    p = DRAFTS / (draft_id + ".json")
    d = json.loads(p.read_text(encoding="utf-8"))
    d["status"] = status
    d["decided_at"] = int(time.time())
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def handle_img_approval(token, action, draft_id, cq):
    """Cong duyet ANH truoc khi viet. designer (Ethan)/Dre/Dre day anh len topic kem
    ba nut:
      imgok    (Duyet)   -> sinh task viet caption (writer_body cat san o
                            `<draft_id>.writer.json`).
      imgredo  (Lam lai) -> tao lai task ANH (body cat o `<draft_id>.img.json`,
                            them ghi chu chon anh khac) -> designer dung lai.
      imgno    (Bo han)  -> giet tin: khong viet, khong lam lai."""
    msg = cq["message"]
    chat_id, msg_id = msg["chat"]["id"], msg["message_id"]
    wp = DRAFTS / (draft_id + ".writer.json")

    if action == "imgno":
        try:
            w = json.loads(wp.read_text(encoding="utf-8")) if wp.exists() else {}
        except Exception:                                       # noqa: BLE001
            w = {}
        if w.get("created") is True:
            # Da bam Duyet truoc do (writer dang chay) — khong bo han nua de tranh
            # trang thai mau thuan (task viet da ton tai ma sidecar lai 'rejected').
            note = "⚠️ Bài đã duyệt, đang viết — không bỏ hẳn được nữa"
            call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                 text="Đã duyệt trước đó, không bỏ", show_alert=True)
        else:
            note = "🗑 Đã bỏ hẳn tin — không viết, không làm lại"
            call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                 text="Đã bỏ hẳn")
            if wp.exists():
                try:
                    w["created"] = "rejected"
                    wp.write_text(json.dumps(w, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
                except Exception as e:                          # noqa: BLE001
                    # Khong ghi duoc sidecar nghia la lenh bo KHONG dinh: bam
                    # Duyet sau do van sinh task viet cho tin da giet. Phai noi.
                    note = ("⚠️ Bỏ hẳn nhưng KHÔNG ghi được trạng thái ("
                            + type(e).__name__ + ") — bấm Bỏ hẳn lại lần nữa")
    elif action == "imgredo":
        ip = DRAFTS / (draft_id + ".img.json")
        if not ip.exists():
            note = "⚠️ Không thấy thông tin task ảnh để làm lại"
            call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                 text="Thiếu thông tin ảnh", show_alert=True)
        else:
            call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                 text="Đang giao dựng lại…")
            im = json.loads(ip.read_text(encoding="utf-8"))
            n = int(im.get("remakes", 0)) + 1
            body = im["body"] + (
                f"\n\n== LAM LAI (lan {n}) ==\n"
                "Anh truoc CHUA DAT, Ong Chu bam lam lai. Chon ANH KHAC — goc khac, "
                "nguon khac, cach the hien khac; DUNG lap lai anh cu. Van day len kem "
                f"nut duyet nhu cu (--duyet {draft_id}).")
            tieu = ("Carousel (lam lai): " if im.get("carousel")
                    else "Anh (lam lai): ") + im.get("title", draft_id)
            rid, err = kanban_create(tieu, im["vai_anh"], body)
            if err:
                note = "⚠️ Làm lại lỗi: " + str(err)
            else:
                im["remakes"], im["last_task"] = n, rid
                ip.write_text(json.dumps(im, ensure_ascii=False, indent=2),
                              encoding="utf-8")
                ten = TEN_VAI_ANH.get(im["vai_anh"], "Ethan")
                note = f"🔄 Đã giao làm lại (lần {n}) — {ten} sẽ dựng ảnh khác (task {rid})"
    else:                                                       # imgok
        if not wp.exists():
            note = "⚠️ Không thấy thông tin bài (writer sidecar) cho draft này"
            call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                 text="Thiếu thông tin bài", show_alert=True)
        else:
            w = json.loads(wp.read_text(encoding="utf-8"))
            if w.get("created") is True:
                note = "✅ Đã duyệt rồi — bài đang được viết"
                call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                     text="Đã duyệt trước đó")
            elif w.get("created") == "rejected":
                note = "🗑 Tin này đã bỏ hẳn trước đó — không viết"
                call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                     text="Đã bỏ hẳn", show_alert=True)
            else:
                call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                     text="Đang giao cho người viết…")
                wid, err = kanban_create("Bai: " + w.get("title", draft_id),
                                         w["vai_viet"], w["body"])
                if err:
                    note = "⚠️ Duyệt ok nhưng tạo task viết lỗi: " + str(err)
                else:
                    w["created"], w["writer_task"] = True, wid
                    wp.write_text(json.dumps(w, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
                    ten = TEN_VAI_VIET.get(w["vai_viet"], "Miles")
                    note = f"✅ Đã duyệt ảnh — {ten} bắt đầu viết caption (task {wid})"

    log("nut", f"ket qua imgok/imgno/imgredo draft={draft_id}: {note}")
    base = msg.get("caption") or msg.get("text") or ""
    method = "editMessageCaption" if msg.get("caption") else "editMessageText"
    key = "caption" if msg.get("caption") else "text"
    r = call(token, method, chat_id=chat_id, message_id=msg_id,
             **{key: base + "\n\n<b>" + html_escape(note) + "</b>"},
             parse_mode="HTML", reply_markup={"inline_keyboard": []})
    if not r.get("ok"):
        call(token, "editMessageReplyMarkup", chat_id=chat_id, message_id=msg_id,
             reply_markup={"inline_keyboard": []})


def handle_callback(token, channel, cq):
    data = cq.get("data", "")
    action, _, draft_id = data.partition(":")
    msg = cq["message"]

    # Duyet ANH (truoc khi viet) — xu ly SOM vi luc nay ban nhap cuoi
    # (<draft>.json) chua ton tai, nhanh duoi se bao "khong tim thay ban nhap".
    if action in ("imgok", "imgno", "imgredo"):
        handle_img_approval(token, action, draft_id, cq)
        return

    p = DRAFTS / (draft_id + ".json")
    if not p.exists():
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Không tìm thấy bản nháp", show_alert=True)
        return

    # CHOT TRANG THAI TRUOC KHI LAM GI KHAC. publish() co the mat toi 180s,
    # trong thoi gian do nut van quay vong va Ong Chu se bam lai — hai callback
    # xep hang, va truoc day ca hai deu dang. Doc status som + tra loi callback
    # NGAY de nut thoi quay, roi moi lam viec nang.
    try:
        st = json.loads(p.read_text(encoding="utf-8")).get("status")
    except Exception:                                        # noqa: BLE001
        st = None
    if st in ("published", "rejected"):
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Bài này đã xử lý rồi (" + st + ")", show_alert=True)
        return

    if st == "publishing":
        # Dang co thread dang bai nay (publish chay NEN, xem _dang_nen). Truoc
        # day publish chay dong bo nen callback thu hai tu xep hang sau; nay
        # phai chan tuong minh de hai thread khong cung dang mot bai.
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Đang đăng — chờ chút", show_alert=True)
        return

    if action == "ok":
        # Danh dau DANG XU LY roi tra callback NGAY; viec nang (upload toi 180s
        # + moat) chay o thread NEN de vong poll khong nghen — nut cua bai khac
        # va chat van bam duoc, cung ly do voi handle_chat/handle_command.
        mark_draft(draft_id, "publishing")
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Đang đăng…")
        threading.Thread(target=_dang_nen, daemon=True,
                         args=(token, channel, draft_id, msg)).start()
        return
    elif action == "no":
        mark_draft(draft_id, "rejected")
        note = "❌ ĐÃ BỎ — không đăng"
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Đã bỏ bài")
    else:
        return

    _sua_tin_go_nut(token, msg, note)


def _dang_nen(token, channel, draft_id, msg):
    """Phan nang cua nut Duyet, chay trong thread rieng. Moi duong loi deu phai
    ra trang thai ro rang: publish_failed cho bam Duyet lai duoc — khong bao
    gio ket vinh vien o 'publishing' (truoc day exception giua chung se ket)."""
    try:
        res = publish(token, channel, draft_id)
        ok = res.get("ok")
        mark_draft(draft_id, "published" if ok else "publish_failed")
        note = ("✅ ĐÃ ĐĂNG lên channel" if ok
                else "⚠️ Đăng lỗi: " + str(res.get("description")))
        # Bai da len channel thi day tiep sang moat cho extension dang len social.
        # Chi day khi Telegram da nhan -- khong dang duoc o day thi bai chua duyet xong.
        # Loi ben moat chi them mot dong vao the, KHONG lam hong luong duyet.
        if ok:
            pushed, why = moat_publish.intake(draft_id)
            note += ("\n\U0001f4e4 moat: " + why) if pushed else ("\n\u26a0\ufe0f moat: " + why)
    except Exception as e:                                   # noqa: BLE001
        try:
            mark_draft(draft_id, "publish_failed")
        except Exception:                                    # noqa: BLE001
            pass
        note = "⚠️ Đăng lỗi: " + type(e).__name__ + ": " + str(e)
    _sua_tin_go_nut(token, msg, note)


def _sua_tin_go_nut(token, msg, note):
    log("nut", f"ket qua msg={msg.get('message_id')}: {note}")
    """Ghi ket qua vao tin nhan draft va go ban phim (dung chung cho nhanh Bo
    tren poll thread va nhanh Duyet chay nen)."""
    chat_id, msg_id = msg["chat"]["id"], msg["message_id"]
    base = msg.get("caption") or msg.get("text") or ""
    body = base.replace("BẢN NHÁP", "BẢN NHÁP (đã xử lý)", 1)
    method = "editMessageCaption" if msg.get("caption") else "editMessageText"
    key = "caption" if msg.get("caption") else "text"
    # `note` co the chua text tho tu moat (trang HTML 502 cua nginx...). Khong
    # escape thi editMessageText bi tu choi -> inline_keyboard khong duoc go ->
    # nut van con, moi bam tiep. Escape TOAN BO note vi minh chi chen <b> quanh no.
    r = call(token, method, chat_id=chat_id, message_id=msg_id,
             **{key: body + "\n\n<b>" + html_escape(note) + "</b>"},
             parse_mode="HTML", reply_markup={"inline_keyboard": []})
    if not r.get("ok"):
        # Khong sua duoc tin nhan (vi du body cu co ky tu la) thi it nhat go nut.
        call(token, "editMessageReplyMarkup", chat_id=chat_id, message_id=msg_id,
             reply_markup={"inline_keyboard": []})


# ---------- B) Ong Chu reply so thu tu -> tao cap task ----------

def slugify(title, fallback):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return (s[:40].strip("-") or fallback)


# Topic nao chon tin tu manifest nao. Finn, Nova va Vera deu la vai DI TIM TIN,
# nen ca ba phai chon duoc bang cach tra loi so — truoc day chi Finn lam duoc,
# bao cao cua Nova va Vera la van xuoi khong so nen Ong Chu khong biet rep gi.
MANIFEST_THEO_TOPIC = {
    "scout": "finn_candidates_*.json",
    "nova": "nova_candidates_*.json",
    "market": "vera_candidates_*.json",
}


def latest_manifest(vai="scout"):
    """Manifest MOI NHAT theo mtime, khong phai theo ten.

    Truoc day sap theo ten tep. Nhung ten khong phan anh thu tu ghi: dem 23/08
    ban `_t2327` ghi luc 23:27 sap TRUOC ban `2026-08-24` ghi luc 23:25 (cron
    dat ten theo ngay VN, quet lai dat hau to gio). Ong Chu tra loi so theo bao
    cao moi -> mo nham manifest cu -> tao bai SAI TIN. Thu tu ghi la thu duy
    nhat dung voi cau hoi "bao cao gan nhat Ong Chu vua doc la cai nao".
    """
    files = list(STATE_DIR.glob(MANIFEST_THEO_TOPIC.get(vai, "finn_candidates_*.json")))
    return max(files, key=lambda f: f.stat().st_mtime) if files else None


# Vai dung anh -> thuong hieu. Ong Chu chon bang cach tra loi "1 - Ethan".
# Khong ghi ten ai thi mac dinh Ethan (donniechublog).
# Chi con HAI vai dung anh, va ca hai lam CUNG MOT kieu anh: kieu tran, khong
# khung, khong vach. Khac nhau dung mot thu la THUONG HIEU. Iris da bo: khi ca
# doi chuyen sang mot kieu anh duy nhat thi vai cua Iris trung khit voi Ethan,
# giu lai chi de hai ban SOUL gan nhu giong het troi ra khoi nhau.
# Container = 1 brand co dinh (BRAND). Slug dat theo CHUC NANG, dung chung ten o
# moi brand: "designer" (the bia, card.py) va "carousel" (nhieu slide,
# carousel.py). Ten nhan vat cu (chad/ethan/heller/dre) giu lam alias de Ong Chu
# go quen tay van dung. Brand KHONG con nam trong map — lay tu BRAND (env).
VAI_ANH = {
    "designer": "designer", "img": "designer", "anh": "designer",
    "ethan": "designer",                               # alias ten persona
    "carousel": "carousel", "cr": "carousel",
    "dre": "carousel",                                 # alias ten persona
    "carousel-edu": "carousel-edu", "edu": "carousel-edu",
    "kite": "carousel-edu",            # alias ten persona (go "sli" / "kite")
}
# Ba loai vai anh, moi loai mot cong cu: card.py (the bia, designer), carousel.py
# (anh that nhieu slide, carousel), render_edu.py (art vector goc magazine,
# carousel-edu/Kite). Them vai moi thi khai vao day + dung set duoi.
VAI_CAROUSEL = {"carousel"}        # slug dung carousel.py (anh that nhieu slide)
VAI_EDU = {"carousel-edu"}         # slug dung render_edu.py (art vector goc, Kite)
MAC_DINH_ANH = "designer"
# Ong Chu go TEN NAO CUNG DUOC — nguoi dung anh hay nguoi viet.
#
# Mot lua chon sinh ra mot CAP di lien nhau: nguoi dung anh lam cha, nguoi viet
# lam con cho cha xong. Ca cap do bi khoa vao dung mot thuong hieu. Nen ten nao
# trong cap cung da du de xac dinh ca cap, va bat Ong Chu phai nho ai la nguoi
# dung anh con ai la nguoi viet la bat nho mot thu khong can nho.
#
#     1 - Ethan   ==  1 - Miles   ->  anh donniechublog + bai cua Miles
#     1 - Ethan  ==  1 - Miles   ->  anh dcgr.tech     + bai cua Miles
TEN_SANG_CAP = dict(VAI_ANH)
TEN_SANG_CAP.update({           # ten nguoi viet cung nhan -> ve default anh
    "writer": "designer", "cap": "designer",
    "miles": "designer",
})
# Ten hien ra bao cao (slug -> ten persona thong nhat, chung ca hai brand).
TEN_VAI_ANH = {"designer": "Ethan", "carousel": "Dre", "carousel-edu": "Kite"}
# Mot container mot nguoi viet duy nhat. Bang VAI_VIET theo brand da bo — no
# rong tu khi chuyen sang container-per-brand, moi lookup deu ve hang so nay.
MAC_DINH_VIET = "writer"
TEN_VAI_VIET = {"writer": "Miles"}


def doc_lenh_chon(text: str):
    """Phan tich lenh chon tin. Tra ve [(so, vai_anh, thuong_hieu)] hoac None.

    Quy tac: ten vai ap cho MOI SO dung truoc no, tinh tu ten vai gan nhat.
    So nao khong co ten vai nao phia sau thi ve mac dinh (Ethan).

        1                    -> Ethan
        1, 2, 3              -> ca ba Ethan
        1, 2, 3 - Ethan      -> ca ba Ethan
        1 - Ethan, 2 - Ethan  -> 1 Ethan, 2 Ethan
        1, 2 - Ethan, 3      -> 1 va 2 Ethan, 3 Ethan

    Ten nguoi VIET cung nhan, va cho ra dung cap do: "1 - Miles" giong het
    "1 - Ethan", "1 - Miles" giong het "1 - Ethan".

    Tra None neu co phan khong hieu duoc, de tin nhan roi ve luong hoi thoai
    thay vi bao loi — Ong Chu con dung chinh topic do de tro chuyen.
    """
    if not text or not text.strip():
        return None

    # Tach thanh cac manh: moi manh la mot SO hoac mot TEN VAI
    manh = []
    for c in re.split(r"[,\n;]+", text.strip()):
        c = c.strip()
        if not c:
            continue
        for phan in c.split():
            phan = phan.strip("-\u2013\u2012:")
            if not phan:
                continue
            if phan.isdigit():
                manh.append(("so", int(phan)))
            elif re.fullmatch(r"[A-Za-zÀ-ỹ]+", phan):
                if phan.lower() not in TEN_SANG_CAP:
                    return None          # ten la -> khong phai lenh chon
                manh.append(("vai", phan.lower()))
            else:
                return None
    if not any(k == "so" for k, _ in manh):
        return None

    ra, cho, thay = [], [], set()
    def _xa(ten):
        for n in cho:
            if n in thay:
                continue
            thay.add(n)
            ra.append((n, TEN_SANG_CAP[ten], BRAND))
        cho.clear()

    for kind, v in manh:
        if kind == "so":
            cho.append(v)
        else:
            _xa(v)                        # ten vai ap cho moi so dang cho
    _xa(MAC_DINH_ANH)                     # so con lai ve mac dinh
    return ra or None


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


# Khuon body task (van ban dai) tach sang task_bodies.py — xem ghi chu o do.
from task_bodies import ILLU_BODY, CAROUSEL_BODY, EDU_BODY, WRITER_BODY  # noqa: E402


# Slug cu (ten nhan vat) -> slug profile hien tai. Sidecar .img.json/.writer.json
# cu con ghi "dre"/"miles"; task tao tu do se khong ai nhan (khong co profile
# ten vay) va nam 'ready' mai — su co 01/09/2026: hai bai dcgr ket 2 ngay.
SLUG_CU = {"miles": "writer", "dre": "carousel", "ethan": "designer",
           "chad": "designer", "heller": "carousel", "kite": "carousel-edu",
           "finn": "scout", "vera": "market", "jean": "teaser", "ada": "analyst"}


def chuan_assignee(assignee):
    """Tra ve slug profile thuc co trong home container, hoac (None, loi)."""
    slug = SLUG_CU.get(str(assignee).lower(), assignee)
    co = Path(HERMES_HOME) / "profiles" / slug
    if not co.is_dir():
        return None, (f"không có profile '{slug}' trong {Path(HERMES_HOME).name} "
                      f"— task sẽ không ai nhận, không tạo")
    return slug, None


def kanban_create(title, assignee, body, parent=None):
    assignee, loi = chuan_assignee(assignee)
    if loi:
        log("kanban", f"tu choi tao '{title[:60]}': {loi}")
        return None, loi
    env = dict(os.environ, HERMES_HOME=HERMES_HOME)
    args = [str(HERMES_PY), "-m", "hermes_cli.main", "kanban", "create", title,
            "--assignee", assignee, "--max-runtime", "25m", "--json",
            "--body", body]
    if parent:
        args += ["--parent", parent]
    r = subprocess.run(args, cwd=str(Path.home() / "hermes-agent"),
                        env=env, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        log("kanban", f"tao '{title[:60]}' cho {assignee} LOI: {(r.stderr or r.stdout)[-200:]}")
        return None, (r.stderr[-300:] or r.stdout[-300:])
    try:
        tid = json.loads(r.stdout)["id"]
        log("kanban", f"tao task {tid} cho {assignee}: {title[:60]}")
        return tid, None
    except Exception:                                        # noqa: BLE001
        return None, r.stdout[-300:]


# ---- Bao khi mot viec bi chan --------------------------------------------
# Vai dung anh co mot nguyen tac cung: khong tim duoc anh THAT thi bao lai, tuyet
# doi khong tu ve minh hoa. Luc do no goi kanban_block, va vi day la block do
# worker chu dong nen hermes giu nguyen cho toi khi co nguoi go — dung nhu thiet
# ke. Task viet la con cua task anh nen nam yen o `todo`, cung dung.
#
# Cho sai la KHONG AI DUOC BAO. Bao cao nam trong kanban, con Ong Chu ngoi o
# Telegram: chon hai tin thay len mot bai, khong biet tin kia di dau. Doan nay
# keo bao cao do ra Telegram.
KANBAN_DB = Path(HERMES_HOME) / "kanban.db"    # kanban cua home container hien tai
DA_BAO_CHAN = STATE_DIR / "da_bao_chan.json"
VAI_CUA_DOI = {"designer": "Designer", "carousel": "Carousel", "writer": "Writer"}


def _da_bao() -> set:
    try:
        return set(json.loads(DA_BAO_CHAN.read_text(encoding="utf-8")))
    except Exception:                                        # noqa: BLE001
        return set()


def _ghi_da_bao(ids: set):
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    # Giu 300 id gan nhat la du: chi can nho de khoi bao trung, khong phai
    # de luu lich su.
    DA_BAO_CHAN.write_text(json.dumps(sorted(ids)[-300:]), encoding="utf-8")


def viec_bi_chan() -> list:
    """[(task_id, ten_vai, tieu_de, ly_do)] cho cac viec dang bi chan."""
    if not KANBAN_DB.exists():
        return []
    try:
        con = sqlite3.connect(f"file:{KANBAN_DB}?mode=ro", uri=True)
    except Exception:                                        # noqa: BLE001
        return []
    ra = []
    try:
        for tid, ai, tieu_de in con.execute(
                "select id, assignee, title from tasks where status='blocked'"):
            if ai not in VAI_CUA_DOI:
                continue
            ly_do = ""
            for (tt,) in con.execute(
                    "select coalesce(summary, error, '') from task_runs "
                    "where task_id=? order by id desc limit 1", (tid,)):
                ly_do = tt or ""
            ra.append((tid, ai, VAI_CUA_DOI[ai], tieu_de, ly_do))
    except Exception:                                        # noqa: BLE001
        return []
    finally:
        con.close()
    return ra


DA_BAO_TIEN_DO = STATE_DIR / "da_bao_tien_do.json"   # {task_id: trang thai da bao}
_TEN_HIEN = {"designer": "Ethan", "carousel": "Dre", "carousel-edu": "Kite",
             "writer": "Miles", "scout": "Finn", "nova": "Nova", "market": "Vera",
             "teaser": "Jean", "analyst": "Ada", "gin": "Gin", "itachi": "Itachi",
             "bob": "Bob"}


def bao_tien_do_kanban(token, group):
    """Bao TIEN DO hang doi kanban ve Telegram: task bat dau -> mot dong vao
    topic cua vai kem so viec con xep hang; task xong/hong -> mot dong nua.

    Vi sao: tu 03/09/2026 moi container chay MOT task mot luc. Sang 04/09 Ong
    Chu chon 7 bai luc 05:33, Dre lam bai 1, sau bai kia + Nova xep hang ca
    tieng — va khong ai noi gi, trong nhu he thong dung. Hang doi la thiet ke,
    im lang thi khong. Chay moi vong poll (~50s), chi bao khi trang thai doi."""
    if not KANBAN_DB.exists():
        return
    try:
        da = json.loads(DA_BAO_TIEN_DO.read_text(encoding="utf-8")) if DA_BAO_TIEN_DO.exists() else {}
    except Exception:                                        # noqa: BLE001
        da = {}
    try:
        con = sqlite3.connect(f"file:{KANBAN_DB}?mode=ro", uri=True)
        rows = con.execute(
            "SELECT id, assignee, status, title, created_at FROM tasks "
            "WHERE created_at > ? ORDER BY created_at", (time.time() - 86400,)).fetchall()
        con.close()
    except Exception as e:                                   # noqa: BLE001
        log("tiendo", f"khong doc duoc kanban: {e}")
        return
    cho = [r for r in rows if r[2] == "ready"]
    tp = env_load.topics_path()
    try:
        topics = json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else {}
    except Exception:                                        # noqa: BLE001
        topics = {}
    doi = False
    for tid, ai, st, title, _c in rows:
        if st in ("ready", "todo", "triage") or da.get(tid) == st:
            continue
        ten = _TEN_HIEN.get(ai, ai)
        if st == "running":
            sau = len(cho)
            text = (f"▶️ <b>{ten}</b> bắt đầu: <i>{html_escape(title[:80])}</i>"
                    + (f"\n(còn {sau} việc xếp hàng sau việc này)" if sau else ""))
        elif st == "done":
            text = f"✅ <b>{ten}</b> xong: <i>{html_escape(title[:80])}</i>"
        elif st in ("blocked", "failed"):
            text = f"⛔ <b>{ten}</b> dừng ({st}): <i>{html_escape(title[:80])}</i>"
        else:
            da[tid] = st
            doi = True
            continue
        thread = topics.get(ai)
        r = call(token, "sendMessage", chat_id=group,
                 **({"message_thread_id": thread} if thread else {}),
                 text=text, parse_mode="HTML")
        log("tiendo", f"{tid} {ai} -> {st} (thread={thread}) gui={'ok' if r.get('ok') else r.get('description')}")
        da[tid] = st
        doi = True
    if doi:
        # Chi giu task 24h gan nhat cho tep khong phinh.
        song = {r[0] for r in rows}
        da = {k: v for k, v in da.items() if k in song}
        try:
            DA_BAO_TIEN_DO.write_text(json.dumps(da), encoding="utf-8")
        except OSError as e:
            log("tiendo", f"khong ghi duoc {DA_BAO_TIEN_DO.name}: {e}")


def bao_viec_bi_chan(token, group):
    """Bao ve topic duyet moi viec vua bi chan. Im lang khi khong co gi moi.

    GOP thanh MOT tin nhan. Moi viec mot tin thi lan dau bat len se ban ra ca
    chuc tin lien tiep, va thu nay dang le phai de doc chu khong phai de chiu
    dung.
    """
    da = _da_bao()
    moi = [x for x in viec_bi_chan() if x[0] not in da]
    if not moi:
        return

    tp = env_load.topics_path()
    try:
        topics = json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else {}
    except Exception:                                        # noqa: BLE001
        topics = {}

    # Mot container mot nguoi viet — moi viec bi chan deu bao ve topic writer.
    # (Bang nhom theo brand da bo cung VAI_VIET: luon chi co mot nhom.)
    nhom = {MAC_DINH_VIET: [(tid, ten, tieu_de, ly_do)
                            for tid, ai, ten, tieu_de, ly_do in moi]}

    da_gui = set()
    for vai_viet, viecs in nhom.items():
        thread = topics.get(vai_viet)
        dau = ("⛔ <b>1 việc dừng lại</b>" if len(viecs) == 1
               else f"⛔ <b>{len(viecs)} việc dừng lại</b>")
        khoi = [dau, ""]
        for _tid, ten, tieu_de, ly_do in viecs:
            khoi.append(f"<b>{html_escape(ten)}</b> — "
                        f"<i>{html_escape(tieu_de[:100])}</i>")
            khoi.append(html_escape(ly_do.strip()[:400]) or "(khong ghi ly do)")
            khoi.append("")
        khoi.append("Bài đi kèm đang chờ, sẽ không chạy tới khi việc ảnh được gỡ.")
        try:
            for phan in tele_util.chia_tin("\n".join(khoi)):
                call(token, "sendMessage", chat_id=group, message_thread_id=thread,
                     text=phan, parse_mode="HTML")
        except Exception as e:                               # noqa: BLE001
            print(f"[bao-chan] khong gui duoc ({vai_viet}): {e}", flush=True)
            continue                  # brand nay chua ghi nhan -> lan sau bao lai
        da_gui |= {t[0] for t in viecs}
    _ghi_da_bao(da | da_gui)


def write_meta(draft_id, item, out_png, brand="donniechublog"):
    """Ghi san metadata cho draft — writer khoi phai go lai bang tay.

    Nhung gia tri nay Finn da quyet tu luc quet; bat LLM go lai chi tao co hoi
    go sai. draft_write.py se doc file nay khi ghep draft cuoi cung.

    `brand` di theo duong nay chu khong qua tham so dong lenh: vai viet goi
    draft_write.py khong kem co nao, nen sidecar la cho DUY NHAT mang duoc
    thuong hieu tu luc Ong Chu chon tin toi luc bam Duyet. Thieu no thi bai
    dcgr.tech day nham sang org social cua donniechublog.
    """
    meta = {
        "source_url": item["link"],
        "category": chuan_nhan(item.get("category")),
        "via": item.get("via", ""),
        "image": out_png,
        "title": item["title"],
        "score": item.get("score"),
        "score_reason": item.get("score_reason", ""),
        "brand": brand,
    }
    DRAFTS.mkdir(parents=True, exist_ok=True)
    (DRAFTS / (draft_id + ".meta.json")).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


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


def _draft_id(item, brand, vai_anh):
    """Khoa draft DUY NHAT theo (tin, brand, role lam anh).

    Mot tin hot co the giao cho NHIEU role lam anh (dang nhieu noi, nhieu cach
    dien dat) -> moi lan giao phai co draft_id rieng, neu khong hai san pham
    song song dung chung file png/meta/sidecar va nut Duyet -> de len nhau.

    GIOI HAN DO DAI: draft_id di vao callback_data cua nut Duyet/Lam lai/Bo
    ("imgredo:" + draft_id). Telegram chan callback_data > 64 byte va lang le
    tu choi ca ban phim -> anh dang len KHONG co nut. Giu draft_id <= 55 ky tu
    (ASCII) de "imgredo:" + draft_id <= 63 byte. Dat `vai` truoc trong khoa de
    role luon con nguyen; phan tieu de bi cat bot khi thieu cho."""
    khoa = slugify(f"{vai_anh}-{brand}", "x")[:20]           # vai truoc -> luon con
    base = slugify(item["title"], "item-" + str(item["index"]))[: 55 - 1 - len(khoa)]
    base = base.strip("-") or ("item-" + str(item["index"]))
    return f"{base}-{khoa}"


def create_pair(item, vai_anh="designer", brand="donniechublog"):
    draft_id = _draft_id(item, brand, vai_anh)
    out_png = str(DRAFTS / (draft_id + ".png"))
    out_json = str(DRAFTS / (draft_id + ".json"))
    write_meta(draft_id, item, out_png, brand)

    # BUOC RESEARCH — thuoc khau cua Finn, chay ngay khi Ong Chu chon tin.
    # Tim nguon la viec research, khong phai viec cua nguoi dung anh hay nguoi
    # viet chu. Lam mot lan o day thay vi de hai ben tu tim: khoi
    # tra cuu hai lan, va quan trong hon la ca hai cung doc MOT bo nguon nen bai
    # viet giai thich dung nhung gi doc gia nhin thay tren tam anh.
    nguon_path = STATE_DIR / f"nguon_{draft_id}.json"
    try:
        subprocess.run(
            [str(ROOT / "venv/bin/python"), str(ROOT / "nguon_bai.py"),
             "--tieu-de", item["title"], "--link", item["link"],
             "--out", str(nguon_path)],
            capture_output=True, text=True, timeout=180, cwd=str(ROOT))
    except Exception as e:                                   # noqa: BLE001
        print(f"[research] khong tim duoc nguon: {type(e).__name__}: {e}")

    # carousel (Dre) dung carousel nhieu slide, cac vai anh khac dung the bia.
    # Cung bo bien nhu nhau nen chon khuon roi format chung; .format bo qua
    # key thua.
    la_carousel = vai_anh in VAI_CAROUSEL
    la_edu = vai_anh in VAI_EDU
    khuon = EDU_BODY if la_edu else (CAROUSEL_BODY if la_carousel else ILLU_BODY)
    illu_body = khuon.format(
        source_note=item.get("source_note", ""), link=item["link"],
        via=item.get("via", ""), title=item["title"],
        summary=item.get("summary_vi", ""),
        image_url=item.get("image_url") or "khong co",
        out_png=out_png, out_png_goc=out_png[:-4],
        category=chuan_nhan(item.get("category")), draft_id=draft_id,
        brand=brand, vai=vai_anh,
        goc=str(ROOT), hermes_py=str(HERMES_PY),
        co_brand=("" if brand == "donniechublog" else f" --brand {brand}"))
    tieu_de_task = ("Carousel deck: " if la_edu
                    else ("Carousel: " if la_carousel else "Anh: ")) + item["title"]
    illu_id, err = kanban_create(tieu_de_task, vai_anh, illu_body)
    if err:
        return None, "Loi tao task anh: " + err

    # Cat lai body task anh de LAM LAI duoc: Ong Chu bam "Lam lai" tren anh chua
    # dat thi tao lai dung task nay (them ghi chu doi anh khac). Thieu file nay
    # thi nut Lam lai bao khong co thong tin.
    (DRAFTS / (draft_id + ".img.json")).write_text(
        json.dumps({"vai_anh": vai_anh, "carousel": la_carousel or la_edu,
                    "title": item["title"], "body": illu_body, "remakes": 0},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    # KHONG tao task viet ngay nua. Tinh san writer_body + vai_viet roi cat vao
    # sidecar `<draft_id>.writer.json`; task viet CHI sinh khi Ong Chu bam
    # "Duyet anh" (imgok) tren tam anh ma designer (Ethan)/Dre/Dre vua day len
    # topic. Anh chua dat thi khong co writer nao ca — dung y Ong Chu: khong
    # nhat thiet phai co writer sau khi tao hinh, o thi moi viet caption.
    writer_body = WRITER_BODY.format(
        title=item["title"], link=item["link"],
        source_note=item.get("source_note", ""), via=item.get("via", ""),
        score=item.get("score", "?"),
        score_reason=item.get("score_reason", ""),
        summary=item.get("summary_vi", ""), out_png=out_png,
        out_json=out_json, category=chuan_nhan(item.get("category")),
        draft_id=draft_id, goc=str(ROOT), hermes_py=str(HERMES_PY))
    vai_viet = MAC_DINH_VIET
    (DRAFTS / (draft_id + ".writer.json")).write_text(
        json.dumps({"vai_viet": vai_viet, "title": item["title"],
                    "body": writer_body, "created": False},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    item["picked"] = True
    item["vai_anh"], item["brand"], item["vai_viet"] = vai_anh, brand, vai_viet
    item["task_anh"], item["task_viet"] = illu_id, None
    # Ghi lai TUNG lan giao (mot tin co the giao nhieu role) — dung de chan
    # trung y het (cung role + cung brand) o vong chon, xem handle_pick.
    item.setdefault("da_giao", []).append(
        {"vai_anh": vai_anh, "brand": brand, "draft_id": draft_id, "task_anh": illu_id})
    return illu_id, None


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
            _chat_co_khoa(token, group, thread_id, text, profile, session, who, kw_thread)
        finally:
            with _KHOA_DANG_CHAY:
                _DANG_CHAY.pop(who, None)
            _CHO_CHAT.release()
    finally:
        hang.release()


def _chat_co_khoa(token, group, thread_id, text, profile, session, who, kw_thread):
    call(token, "sendMessage", chat_id=group, **kw_thread,
         text=f"⏳ Đang chuyển cho <b>{who}</b>…", parse_mode="HTML")

    # Goi agent o thread con de thread nay con ranh bao TIEN DO: qua 2 phut
    # chua xong thi nhan mot dong, de Ong Chu biet la dang chay chu khong phai
    # chet. Truoc day 10 phut im lang roi moi bao het gio.
    ket_qua = {}
    def _goi():
        ket_qua["r"] = chat_router.ask(profile, session, boi_canh_vai(profile) + text)
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


# ---------- lenh slash (dat bai tuong minh) ----------
# Nguyen tac: mot dau "/" nghia la Ong Chu dang RA LENH, khong tro chuyen.
# Dung cu phap moi chay; sai cu phap / sai ten vai / URL hong thi bao ngan
# va dung han — khong roi ve hoi thoai, khong tu suy dien "chac y la...".

DAT_BAI_SO = STATE_DIR / "dat_bai.json"     # so dedup: url chuan hoa -> lan dat
# handle_command chay o thread rieng: hai /bai cung luc se cung doc-sua-ghi
# dat_bai.json -> mat ban ghi dedup, tao cap task trung. Mot khoa la du.
_KHOA_DAT_BAI = threading.Lock()
ONG_CHU_IDS = STATE_DIR / "ong_chu.json"    # [user_id...] duoc phep ra lenh

# Chan host noi bo: bot chay ngay tren server (tunnel, dashboard, cron) nen
# mot URL tro nguoc vao trong la fetch thang vao ruot he thong. Chi so khop
# ten host, khong resolve DNS — du cho mo hinh rui ro nay (chi Ong Chu ra
# lenh duoc), khong phai tuong lua.
_HOST_CAM = re.compile(
    r"^(localhost$|127\.|10\.|192\.168\.|169\.254\.|0\.)"
    r"|^172\.(1[6-9]|2\d|3[01])\."
    r"|\.(local|internal|netbird\.mated)$", re.I)


def _nap_json(path, mac_dinh):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return mac_dinh


def _chuan_hoa_url(url):
    """Bo fragment + tham so tracking de dedup: cung mot bai dan hai lan tu
    hai nguon (newsletter, mang xa hoi) thuong chi khac nhau dung utm_*."""
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
    p = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(p.query)
         if not k.lower().startswith(("utm_", "fbclid", "gclid", "ref"))]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(),
                       p.path.rstrip("/"), urlencode(q), ""))


def _url_hop_le(url):
    """None neu dung duoc, chuoi ly do neu khong."""
    from urllib.parse import urlsplit
    try:
        p = urlsplit(url)
    except ValueError:
        return "URL không đọc được."
    if p.scheme not in ("http", "https") or not p.hostname:
        return "URL phải là http/https đầy đủ."
    if _HOST_CAM.search(p.hostname):
        return "Host này là địa chỉ nội bộ — không nhận."
    return None


def _doc_trang(url):
    """Lay title + anh og:image de dien khuon task. Chi can THE, khong can
    sach: vai duoc giao van tu doc bai goc va chay research (nguon_bai.py)
    nhu moi bai Finn quet. Tra (title|None, image_url, ghi_chu) — title None
    nghia la khong ket noi duoc (URL chet), con trang tra loi loi HTTP
    (paywall 403...) van tien hanh duoc, chi kem ghi chu."""
    try:
        with httpx.Client(timeout=20, follow_redirects=True, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) content-team"}) as c:
            r = c.get(url)
    except Exception as e:                                   # noqa: BLE001
        return None, "", f"không tải được trang ({type(e).__name__})"
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text[:500_000], "html.parser")
    og = soup.find("meta", property="og:title")
    title = (og and og.get("content") or "").strip()
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()
    ogi = soup.find("meta", property="og:image")
    image_url = (ogi and ogi.get("content") or "").strip()
    ghi_chu = ""
    if r.status_code >= 400:
        ghi_chu = (f"trang trả HTTP {r.status_code} (paywall/chặn bot?) — "
                   "vai được giao cần tự kiểm tra đọc được không")
    if not title:
        from urllib.parse import urlsplit
        p = urlsplit(url)
        title = p.netloc + p.path
    return title, image_url, ghi_chu


LENH_HELP = (
    "<b>Lệnh:</b>\n"
    "<code>/bai &lt;url&gt; &lt;vai&gt;</code> — đặt bài tay từ URL: tạo cặp task "
    "ảnh + viết, không qua vòng quét của Finn.\n"
    "  vai nhận: <code>designer</code> (thẻ bìa) hoặc <code>carousel</code> "
    "(nhiều slide); brand cố định theo container.\n"
    "<code>/vai</code> — bảng vai trong container này.\n"
    "<code>/help</code> — tin này.\n"
    "Sai cú pháp thì không làm gì — lệnh phải tường minh.")


def _lenh_bai(tra_loi, args):
    if len(args) != 2 or not args[0].lower().startswith(("http://", "https://")):
        tra_loi("Cú pháp: <code>/bai &lt;url&gt; &lt;vai&gt;</code> — đúng hai "
                "phần, URL trước vai sau. Không tạo gì.")
        return
    url, ten = args[0], args[1].lower()
    if ten not in TEN_SANG_CAP:
        tra_loi("Không có vai <b>" + html_escape(ten) + "</b>. Vai nhận: "
                + ", ".join(sorted(TEN_SANG_CAP)) + ". Không tạo gì.")
        return
    loi = _url_hop_le(url)
    if loi:
        tra_loi("❌ " + loi + " Không tạo gì.")
        return
    url_chuan = _chuan_hoa_url(url)
    so = _nap_json(DAT_BAI_SO, {})
    if url_chuan in so:
        cu = so[url_chuan]
        tra_loi("URL này đã đặt " + cu.get("ngay", "?") + " — draft <code>"
                + html_escape(cu.get("draft_id", "?")) + "</code>, giao "
                + cu.get("vai", "?") + ". Không tạo lại.")
        return

    vai_anh, brand = TEN_SANG_CAP[ten], BRAND
    title, image_url, ghi_chu = _doc_trang(url)
    if title is None:
        tra_loi("❌ " + ghi_chu + " — không tạo task. Kiểm tra URL rồi /bai lại.")
        return

    import hashlib
    item = {
        # index vao fallback cua slugify — bam theo URL de hai bai tieng Viet
        # (slug rong) khong de len nhau
        "index": "b" + hashlib.sha1(url_chuan.encode()).hexdigest()[:8],
        "title": title, "link": url,
        "summary_vi": "",
        "source_note": "Ong Chu dat tay qua lenh /bai — tu doc bai goc va tu tom tat.",
        "via": "", "image_url": image_url or "khong co",
        "category": None, "score": "?",
        "score_reason": "dat tay, khong qua cham diem",
        "nguon": "adhoc",
    }
    tid, err = create_pair(item, vai_anh=vai_anh, brand=brand)
    if err:
        tra_loi("❌ " + html_escape(err))
        return

    draft_id = _draft_id(item, brand, vai_anh)
    so[url_chuan] = {"ngay": time.strftime("%Y-%m-%d %H:%M"),
                     "draft_id": draft_id, "vai": vai_anh, "brand": brand,
                     "tasks": [tid], "title": title}
    tmp = DAT_BAI_SO.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(so, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, DAT_BAI_SO)

    ten_hien = TEN_VAI_ANH.get(vai_anh, "Ethan")
    ten_viet = TEN_VAI_VIET.get(MAC_DINH_VIET, "Miles")
    dong = ("✅ <b>" + html_escape(title) + "</b>\n"
            + f"{ten_hien} dựng ảnh ({brand}) — task {tid}. "
            + f"{ten_viet} viết caption SAU khi Ông Chủ bấm Duyệt ảnh.")
    if ghi_chu:
        dong += "\n⚠️ " + ghi_chu
    tra_loi(dong)


def handle_command(token, group, msg, thread_id, text):
    def tra_loi(t):
        call(token, "sendMessage", chat_id=group,
             **({"message_thread_id": thread_id} if thread_id else {}),
             text=t, parse_mode="HTML", disable_web_page_preview=True)

    # Allowlist: co file state/ong_chu.json (danh sach user_id) thi chi nhung
    # id do duoc ra lenh; chua co file thi giu hanh vi cu (ca group — group
    # hien chi co Ong Chu). Tin bao loi kem id de them vao file cho de.
    uid = msg.get("from", {}).get("id")
    cho_phep = _nap_json(ONG_CHU_IDS, [])
    if cho_phep and uid not in cho_phep:
        tra_loi("Lệnh slash chỉ nhận từ Ông Chủ. (id của bạn: <code>"
                + str(uid) + "</code>)")
        return

    phan = text.split()
    lenh = phan[0].split("@")[0].lower()    # "/bai@TenBot" -> "/bai"

    if lenh == "/help":
        tra_loi(LENH_HELP)
    elif lenh == "/vai":
        dong = [f"<b>Vai ảnh</b> (brand cố định của container: {BRAND}):"]
        for ten, va in sorted(VAI_ANH.items()):
            kieu = ("carousel deck" if va in VAI_EDU
                    else "carousel" if va in VAI_CAROUSEL else "thẻ bìa")
            dong.append(f"  <code>{ten}</code> → {va} ({kieu})")
        dong.append("<b>Vai viết</b>: <code>writer</code> — một người viết cho container này.")
        tra_loi("\n".join(dong))
    elif lenh == "/bai":
        with _KHOA_DAT_BAI:
            _lenh_bai(tra_loi, phan[1:])
    else:
        tra_loi("Không có lệnh " + html_escape(lenh) + " — /help để xem. "
                "Sai lệnh thì không làm gì.")


def _tai_anh_dinh_kem(token, msg):
    """Tai anh dinh kem (photo hoac document anh) cua tin nhan ve dia, tra ve
    duong dan cuc bo hoac None neu tin khong co anh.

    Day la khe ho THAT khien 'reply vao anh de sua' khong bao gio hoat dong
    dung: truoc gio chi CHU (text/caption) toi duoc agent qua chat_router,
    file anh thi khong — agent phai tu doan bang cach doc /tmp, drafts/,
    nhat ky gui Telegram. Ham nay dua duong dan THAT vao thang prompt, agent
    khong con phai doan."""
    file_id, ext = None, ".jpg"
    photos = msg.get("photo")
    if photos:
        file_id = photos[-1]["file_id"]          # phan tu cuoi = do phan giai cao nhat
    elif msg.get("document") and str(msg["document"].get("mime_type", "")).startswith("image/"):
        file_id = msg["document"]["file_id"]
        ten = msg["document"].get("file_name", "")
        if "." in ten:
            ext = "." + ten.rsplit(".", 1)[-1]
    if not file_id:
        return None
    try:
        r = call(token, "getFile", file_id=file_id)
        if not r.get("ok"):
            return None
        file_path = r["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{token}/{file_path}"
        with httpx.Client(timeout=30) as c:
            data = c.get(url).content
    except Exception:                              # noqa: BLE001
        return None
    TELEGRAM_INCOMING.mkdir(parents=True, exist_ok=True)
    out = TELEGRAM_INCOMING / f"{msg['message_id']}{ext}"
    out.write_bytes(data)
    return str(out)


def handle_message(token, group, msg):
    mid = msg.get("message_id")
    if msg.get("from", {}).get("is_bot"):
        return                      # tin cua chinh bot, khong log cho khoi nhieu
    if msg.get("chat", {}).get("id") != int(group):
        log("vao", f"bo qua msg={mid}: chat {msg.get('chat', {}).get('id')} "
                   f"khong phai group {group}")
        return
    # Anh/album kem caption: Telegram de chu o field "caption", KHONG phai
    # "text" (text chi co o tin nhan thuan chu). Thieu fallback nay lam moi
    # reply-kem-anh (vd sua lai anh theo yeu cau) bi handle_message am tham
    # bo qua — khong loi, khong tin nhan, chi im re. handle_callback da biet
    # phan biet hai field nay (xem dong ~268), ham nay truoc day thi khong.
    text = (msg.get("text") or msg.get("caption") or "").strip()

    # Anh dinh kem (photo hoac document anh): tai ve, dua duong dan THAT vao
    # dau text — agent doc duoc ngay, khong phai doan qua nhat ky/thu muc.
    # Tin chi co anh, khong chu (chu qua bam Reply roi gui thang anh, khong
    # go gi them) van phai di tiep, khong duoc bo som nhu truoc.
    anh_path = _tai_anh_dinh_kem(token, msg)
    if anh_path:
        text = f"[Ảnh đính kèm đã tải về: {anh_path}]\n" + (text or "(không có chú thích kèm theo)")

    thread_id = msg.get("message_thread_id")
    log("vao", f"msg={mid} thread={thread_id} vai={vai_cua_topic(thread_id)} "
               f"from={msg.get('from', {}).get('id')} text={rut(text)}")
    if not text:
        # Sticker, voice, video, file khong phai anh... — khong hieu duoc thi
        # noi ro, khong im lang (im lang = "khong phan hoi" trong mat Ong Chu).
        loai = next((k for k in ("sticker", "voice", "video", "audio", "document",
                                 "animation", "video_note", "poll", "location")
                     if k in msg), "khong ro")
        log("vao", f"msg={mid} khong co chu/anh (loai={loai}) -> bao khong ho tro")
        call(token, "sendMessage", chat_id=group,
             **({"message_thread_id": thread_id} if thread_id else {}),
             text=f"Tin dạng {loai} chưa hỗ trợ — chỉ nhận chữ và ảnh (photo hoặc file ảnh).")
        return

    # Dau "/" = LENH, o bat ky topic nao — xu ly rieng, khong bao gio roi ve
    # hoi thoai (mot lenh go sai ma dem hoi LLM la vua on ao vua nguy hiem).
    # Chay nen: /bai co buoc fetch trang + research (nguon_bai, toi 180s),
    # khong duoc nghen vong poll — cung ly do voi handle_chat ben duoi.
    if text.startswith("/"):
        log("route", f"msg={mid} lenh slash")
        _chay_nen("lenh", handle_command, token, group, thread_id,
                  token, group, msg, thread_id, text)
        return

    # So trong topic cua MOT VAI DI TIM TIN = lenh chon tin. Moi thu khac la
    # hoi thoai. Finn, Nova, Vera deu duoc — cung mot cach tra loi.
    vai = vai_cua_topic(thread_id)
    lenh = doc_lenh_chon(text) if vai in MANIFEST_THEO_TOPIC else None
    is_pick = lenh is not None
    if not is_pick:
        # Thi diem 04/09 (dcgr truoc): chat thuong di qua GATEWAY hermes bang bot
        # rieng (profile_routes theo topic). Bot approve chi con giu nut duyet,
        # chon so, lenh "/" va tien do kanban — KHONG tra loi chat nua, khong thi
        # hai bot cung dap mot cau. Bat bang CT_CHAT_QUA_GATEWAY=1 trong unit.
        if os.environ.get("CT_CHAT_QUA_GATEWAY", "") == "1":
            log("route", f"msg={mid} chat -> nhuong gateway (CT_CHAT_QUA_GATEWAY=1)")
            return
        # Chay nen: mot lan goi agent co the toi 10 phut, khong duoc de nghen
        # vong lap poll (nut Duyet/Bo phai bam duoc bat cu luc nao).
        _chay_nen("chat", handle_chat, token, group, thread_id,
                  token, group, msg, thread_id, text)
        return

    log("route", f"msg={mid} chon so vai={vai} lenh={lenh}")
    _chay_nen("chon", _xu_ly_chon, token, group, thread_id,
              token, group, thread_id, vai, lenh)


def _xu_ly_chon(token, group, thread_id, vai, lenh):
    """Tao cap task tu lenh chon so. Chay nen qua _chay_nen."""
    manifest_path = latest_manifest(vai)
    if not manifest_path:
        mau = MANIFEST_THEO_TOPIC.get(vai, "?")
        log("chon", f"khong co manifest {mau} trong {STATE_DIR}")
        call(token, "sendMessage", chat_id=group, message_thread_id=thread_id,
             text=f"Chưa có danh sách tin nào để chọn trong topic này.\n"
                  f"(tìm {mau} trong {STATE_DIR.name}/ — vai {vai} chưa gửi báo cáo "
                  f"nào cho container {ghi_log.brand()}, hoặc báo cáo ghi sai thư mục)")
        return
    log("chon", f"manifest={manifest_path.name}")
    # SAP THEO VAI, giu thu tu vai xuat hien lan dau: "1, 3 - Ethan, 2 - Dre"
    # -> [1 Ethan, 3 Ethan, 2 Dre]. Dispatcher chay FIFO theo created_at voi
    # kanban.max_in_progress=1, nen tao task theo thu tu nay = Ethan lam het
    # bai cua minh roi Dre moi bat dau (yeu cau Ong Chu 03/09/2026: khong giao
    # cho tat ca cung lam).
    thu_tu_vai = list(dict.fromkeys(v for _n, v, _b in lenh))
    lenh = sorted(lenh, key=lambda x: thu_tu_vai.index(x[1]))

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = {it["index"]: it for it in data.get("items", [])}
    lines = []
    changed = False
    for n, vai_anh, brand in lenh:
        it = items.get(n)
        if not it:
            lines.append("#" + str(n) + ": không tìm thấy")
            continue
        # Cho phep giao MOT tin cho NHIEU role lam anh (tin hot dang nhieu noi,
        # nhieu cach dien dat). Chi chan lap Y HET: cung role + cung brand da
        # giao roi -> khoi tao trung task va de file len nhau.
        if any(g.get("vai_anh") == vai_anh and g.get("brand") == brand
               for g in it.get("da_giao", [])):
            ten_da = TEN_VAI_ANH.get(vai_anh, vai_anh)
            lines.append(f"#{n}: đã giao {ten_da} ({brand}) trước đó — bỏ qua")
            continue
        tid, err = create_pair(it, vai_anh=vai_anh, brand=brand)
        if err:
            lines.append("#" + str(n) + ": lỗi — " + err)
            continue
        changed = True          # create_pair da danh dau vao `it`
        ten_hien = TEN_VAI_ANH.get(vai_anh, "Ethan")
        ten_viet = TEN_VAI_VIET.get(MAC_DINH_VIET, "Miles")
        lines.append(f"#{n}: {ten_hien} dựng ảnh ({brand}) — task {tid}"
                     f"; {ten_viet} viết caption sau khi Ông Chủ duyệt ảnh")

    if changed:
        manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
    log("chon", "ket qua: " + " | ".join(lines))
    _gui_chu(token, group, "<b>Kết quả chọn:</b>\n" + "\n".join(lines),
             thread=thread_id)


# ---------- vong lap chinh ----------

def _ghi_offset(offset: int):
    """Ghi offset NGUYEN TU. Chet giua luc ghi khong duoc de lai file cut:
    int() doc file cut se nem ValueError ngay khoi dong -> systemd restart ->
    crash-loop im lang, va kenh bao dong duy nhat (Telegram) thi can offset."""
    OFFSET.parent.mkdir(parents=True, exist_ok=True)
    tmp = OFFSET.with_suffix(".txt.tmp")
    tmp.write_text(str(offset))
    os.replace(tmp, OFFSET)


def _doc_offset() -> int:
    """File hong (cut nua chung, rac) thi ve 0 va bao — con hon chet han.
    offset=0 lam Telegram tra lai cac update con giu (toi da 24h), nhung
    handle_callback da co chot trang thai nen bai da xu ly khong dang lai."""
    if not OFFSET.exists():
        return 0
    try:
        return int(OFFSET.read_text().strip())
    except (ValueError, OSError) as e:
        print(f"[approve_service] offset.txt hong ({e}), ve 0", flush=True)
        return 0


def loop():
    token, channel, group = load_secrets()
    offset = _doc_offset()
    tp = env_load.topics_path()
    log("start", f"brand={ghi_log.brand()} group={group} state={STATE_DIR} "
                 f"topics={tp.name}({'co' if tp.exists() else 'THIEU'}) "
                 f"hermes_home={HERMES_HOME} offset={offset}")
    loi_lien_tiep = 0
    while True:
        try:
            r = call(token, "getUpdates", offset=offset, timeout=50,
                     allowed_updates=["callback_query", "message"])
            if not r.get("ok"):
                # 409 (hai poller cung token) / 429: long-poll khong giu duoc,
                # request tra ve NGAY -> khong sleep la nen API vo han.
                log("loi", "getUpdates tu choi: " + str(r.get("description")))
                time.sleep(5)
                continue
            for u in r.get("result", []):
                # Ghi offset TRUOC khi xu ly tung update. Truoc day ghi sau ca
                # lo: mot update no giua chung -> offset khong ghi -> restart
                # xu ly lai tu dau lo, DANG LAI bai da dang. Ghi truoc nghia la
                # update no se bi mat thay vi chay hai lan — voi dich vu duyet
                # bai, mat mot lenh (Ong Chu bam lai duoc) re hon dang trung
                # (doc gia thay hai bai giong het nhau tren channel).
                offset = u["update_id"] + 1
                _ghi_offset(offset)
                # Boc TUNG update: mot update hong khong duoc keo ca lo con
                # lai xuong except ngoai (bi bo qua im lang), va nut bam hong
                # thi Ong Chu phai thay nut ngung quay kem ly do.
                try:
                    if "callback_query" in u:
                        cq = u["callback_query"]
                        log("vao", f"callback data={cq.get('data')} "
                                   f"from={cq.get('from', {}).get('id')}")
                        handle_callback(token, channel, cq)
                    elif "message" in u:
                        handle_message(token, group, u["message"])
                except Exception as e:                      # noqa: BLE001
                    import traceback
                    log("loi", f"update {u.get('update_id')} hong: "
                               f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
                    if "callback_query" in u:
                        call(token, "answerCallbackQuery",
                             callback_query_id=u["callback_query"]["id"],
                             text=f"Lỗi: {type(e).__name__}: {str(e)[:150]}",
                             show_alert=True)
            # getUpdates cho toi 50 giay moi luot, nen goi moi vong la du thua
            # cho viec nay: no chi doc mot cau SQL va thuong khong gui gi.
            bao_viec_bi_chan(token, group)
            bao_tien_do_kanban(token, group)
            loi_lien_tiep = 0
        except Exception as e:                              # noqa: BLE001
            loi_lien_tiep += 1
            log("loi", "vong poll: " + type(e).__name__ + ": " + str(e))
            time.sleep(min(60, 5 * loi_lien_tiep))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "push":
        tok, _ch, grp = load_secrets()
        draft_id = sys.argv[2]
        # Dinh tuyen topic theo loai noi dung: teaser ve topic Jean, tin tuc
        # ve topic Miles. Tham so thu 3 (neu co) van ghi de duoc.
        thread = None
        tp = env_load.topics_path()
        if tp.exists():
            topics = json.loads(tp.read_text(encoding="utf-8"))
            dpath = DRAFTS / (draft_id + ".json")
            category = ""
            if dpath.exists():
                try:
                    category = json.loads(
                        dpath.read_text(encoding="utf-8")).get("category", "")
                except Exception:                            # noqa: BLE001
                    pass
            key = "teaser" if category.upper() == "TEASER" else "writer"
            if key == "writer":
                # Tin thuong tach theo THUONG HIEU: dcgr -> topic Miles,
                # donniechublog -> Miles. Truoc day MOI draft deu ve topic Miles
                # nen trong nhu Miles om ca dcgr; that ra Miles viet caption dcgr,
                # chi la ban nhap bi day nham topic. Brand nam trong sidecar meta.
                brand = ""
                mpath = DRAFTS / (draft_id + ".meta.json")
                if mpath.exists():
                    try:
                        brand = json.loads(
                            mpath.read_text(encoding="utf-8")).get("brand", "")
                    except Exception:                            # noqa: BLE001
                        pass
                key = MAC_DINH_VIET
            thread = topics.get(key)
        if len(sys.argv) > 3:
            thread = int(sys.argv[3])
        res = draft_push(tok, grp, draft_id, thread_id=thread)
        print("day ban nhap -> topic " + str(thread) + " | " +
              ("OK" if res.get("ok") else str(res.get("description"))))
    else:
        loop()
