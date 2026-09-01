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
BRAND = os.environ.get("BRAND", "donniechublog")   # content-brand co dinh cua container ('dcgr'|'donniechublog')


def load_secrets():
    env_load.nap()
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not tok:
        sys.exit("Thieu TELEGRAM_BOT_TOKEN")
    return (tok,
            os.environ.get("TELEGRAM_CHANNEL_ID"),
            os.environ.get("TELEGRAM_GROUP_ID"))


def call(token, method, **kw):
    with httpx.Client(timeout=90) as c:
        r = c.post(API.format(token=token, method=method), json=kw)
    return r.json()


def scout_thread_id():
    p = env_load.topics_path()
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding="utf-8")).get("scout")


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
TEXT_LIMIT = 4096         # gioi han cua sendMessage


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
    """Cong duyet ANH truoc khi viet. Chad/Ethan/Heller/Dre day anh len topic kem
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
                except Exception:                               # noqa: BLE001
                    pass
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
                ten = TEN_VAI_ANH.get(im["vai_anh"], "Chad")
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
                    ten = TEN_VAI_VIET.get(w["vai_viet"], "Quinn")
                    note = f"✅ Đã duyệt ảnh — {ten} bắt đầu viết caption (task {wid})"

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
    chat_id, msg_id = msg["chat"]["id"], msg["message_id"]

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

    if action == "ok":
        # Danh dau DANG XU LY truoc khi dang: callback thu hai toi trong luc
        # publish() dang chay se bi chan o nhanh tren.
        mark_draft(draft_id, "publishing")
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Đang đăng…")
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
    elif action == "no":
        mark_draft(draft_id, "rejected")
        note = "❌ ĐÃ BỎ — không đăng"
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Đã bỏ bài")
    else:
        return

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
# Khong ghi ten ai thi mac dinh Chad (donniechublog).
# Chi con HAI vai dung anh, va ca hai lam CUNG MOT kieu anh: kieu tran, khong
# khung, khong vach. Khac nhau dung mot thu la THUONG HIEU. Iris da bo: khi ca
# doi chuyen sang mot kieu anh duy nhat thi vai cua Iris trung khit voi Chad,
# giu lai chi de hai ban SOUL gan nhu giong het troi ra khoi nhau.
# Container = 1 brand co dinh (BRAND). Slug dat theo CHUC NANG, dung chung ten o
# moi brand: "designer" (the bia, card.py) va "carousel" (nhieu slide,
# carousel.py). Ten nhan vat cu (chad/ethan/heller/dre) giu lam alias de Ong Chu
# go quen tay van dung. Brand KHONG con nam trong map — lay tu BRAND (env).
VAI_ANH = {
    "designer": "designer", "img": "designer", "anh": "designer",
    "chad": "designer", "ethan": "designer",          # alias nhan vat cu
    "carousel": "carousel", "cr": "carousel",
    "heller": "carousel", "dre": "carousel",           # alias
}
# Vai dung carousel.py (nhieu slide) thay vi card.py (mot the bia). Them vai
# carousel moi thi chi can them vao day — cho o duoi doc bang nay, khong ghim
# cung ten "heller".
VAI_CAROUSEL = {"carousel"}        # slug dung carousel.py thay card.py
MAC_DINH_ANH = "designer"
# Ong Chu go TEN NAO CUNG DUOC — nguoi dung anh hay nguoi viet.
#
# Mot lua chon sinh ra mot CAP di lien nhau: nguoi dung anh lam cha, nguoi viet
# lam con cho cha xong. Ca cap do bi khoa vao dung mot thuong hieu. Nen ten nao
# trong cap cung da du de xac dinh ca cap, va bat Ong Chu phai nho ai la nguoi
# dung anh con ai la nguoi viet la bat nho mot thu khong can nho.
#
#     1 - Chad   ==  1 - Quinn   ->  anh donniechublog + bai cua Quinn
#     1 - Ethan  ==  1 - Miles   ->  anh dcgr.tech     + bai cua Miles
TEN_SANG_CAP = dict(VAI_ANH)
TEN_SANG_CAP.update({           # ten nguoi viet cung nhan -> ve default anh
    "writer": "designer", "cap": "designer",
    "quinn": "designer", "miles": "designer",
})
# Ten hien ra bao cao (slug -> nhan). Slug generic nen chung cho moi brand.
TEN_VAI_ANH = {"designer": "Designer", "carousel": "Carousel"}
# Mot container mot nguoi viet duy nhat = "writer" (brand lay tu BRAND, khong
# con chon nguoi viet theo brand nua). VAI_VIET rong -> .get luon ve MAC_DINH_VIET.
VAI_VIET = {}
MAC_DINH_VIET = "writer"
TEN_VAI_VIET = {"writer": "Writer"}
# Vai anh the bia dung kieu tran. Giu bang tra de sau them kieu khac con cho.
KIEU_ANH = {"designer": "tran"}


def doc_lenh_chon(text: str):
    """Phan tich lenh chon tin. Tra ve [(so, vai_anh, thuong_hieu)] hoac None.

    Quy tac: ten vai ap cho MOI SO dung truoc no, tinh tu ten vai gan nhat.
    So nao khong co ten vai nao phia sau thi ve mac dinh (Chad).

        1                    -> Chad
        1, 2, 3              -> ca ba Chad
        1, 2, 3 - Ethan      -> ca ba Ethan
        1 - Chad, 2 - Ethan  -> 1 Chad, 2 Ethan
        1, 2 - Ethan, 3      -> 1 va 2 Ethan, 3 Chad

    Ten nguoi VIET cung nhan, va cho ra dung cap do: "1 - Quinn" giong het
    "1 - Chad", "1 - Miles" giong het "1 - Ethan".

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


ILLU_BODY = """Nguon: {source_note}
Link: {link}
Nguon anh (via): {via}
Chu de: {title}
Tom tat: {summary}
image_url (og:image so bo, co the la the thuong hieu): {image_url}

NHIEM VU: dung the anh cho bai nay tu ANH THAT cua nguon.
Thuong hieu: {brand}

NGUYEN TAC TREN HET: KHONG BAO GIO tu ve minh hoa.
Ve ra la bia dat — the anh phai phan anh dung cai co that trong nguon. Khong tim
duoc anh thi BAO LAI, khong duoc lap cho trong bang hinh tu nghi ra.

BUOC 1 — tim anh that cua tin nay (BAT BUOC chay lenh nay):
cd /home/donniechu/content-team && venv/bin/python anh_bai.py \\
  --tieu-de "{title}" --link "{link}" --json \\
  --tu-nguon /home/donniechu/content-team/state/nguon_{draft_id}.json

Finn DA tim nguon san va ghi vao tep tren — day la ket qua research cua cau ay.
Ban dung lai bo nguon do, khong tu di tim. Quinn cung doc chinh tep nay de viet,
nho vay bai viet va tam anh cung noi ve mot thu.

Script lay anh tu chinh link goc VA tu cac bao khac dua cung tin, loc bo
logo/favicon/the thuong hieu, do kich thuoc that roi xep hang. Anh co bang so
hay bieu do duoc cong diem — do la thu doc gia muon nhin.

BUOC 2 — chon anh:
- Lay anh diem cao nhat lam anh chinh. Tai ve: /tmp/src_{draft_id}.png
- Neu con anh khac tu 40 diem tro len va NOI DUNG KHAC NHAU (bang benchmark,
  bieu do gia, so do kien truc...), tai them: /tmp/src_{draft_id}_2.png,
  _3.png... Toi da 4 anh. Nhieu anh la TOT, khong sao ca.
- Bo anh trung noi dung, bo anh chi la anh bia chung chung neu da co anh co so lieu.

BUOC 3 — neu KHONG tim duoc anh nao:

Truoc khi dung lai, xem link co phai arxiv khong (arxiv.org/abs/... hoac /pdf/...).
Neu phai, "anh that" cua bai la CHINH TRANG DAU PAPER — ten cong trinh va nhom
tac gia in tren nen trang that. Do khong phai hinh bia dat, nen chup no khong
vi pham nguyen tac. Chay:

venv/bin/python arxiv_bia.py \
  --link "{link}" --out /tmp/src_{draft_id}.png

Chay xong (thoat 0) thi coi nhu DA CO anh chinh, di tiep buoc 4 binh thuong.
Khong co anh phu.

Neu KHONG phai arxiv, hoac arxiv_bia.py thoat khac 0 (khong tai duoc PDF):
Dung lai. Bao dung mot cau: "Khong tim duoc anh that cho tin nay" kem link da thu.
KHONG tao the, KHONG ve SVG, KHONG chay card.py. Ong Chu se quyet dinh bo tin
hay tu dua anh vao.

BUOC 4 — dung the anh (chi khi buoc 2 co anh). MAC DINH LA KIEU QUOTE (the HOOK).

--kieu quote la mot CAU LON trong khung dau " sao cho DAP VAO MAT trong 3 GIAY
dau, khien nguoi ta phai doc tiep. Cau nay KHONG nhat thiet la loi ai noi trong
bai — dung may moc. No co the la:
 - chinh TIEU DE / mot goc giat cua tin (manh nhat khi co CON SO soc), HOAC
 - mot cau noi CO THAT cua nguoi trong bai (neu bai co cau du dat).
Chon cai nao gay an tuong hon. Doc {source_note} / {summary} / bai goc ({link}).

--tagline la CHIP CATEGORY goc tren-trai (nhan ngan TIENG ANH): MODEL RELEASE /
FUNDING / ROBOTICS / CYBERSECURITY / APPS / OPEN SOURCE / RESEARCH / M&A / IN
BRIEF... Chon nhan dung chu de tin. (KHONG con mac dinh "daily AI update".)

--attrib la dong nguon o duoi khung:
 - Cau la LOI CO THAT cua mot nguoi  -> "Phat bieu cua <ten>, <chuc/hang>".
 - Cau la tieu de/hook (khong phai loi ai) -> ghi NGUON: "via <bao>" hoac
   "<Chu de>, via <bao>". TUYET DOI KHONG gan cau minh tu viet thanh loi mot
   nguoi cu the — bia loi la sai. Hook thi ghi nguon, dung ghi "phat bieu".

cd /home/donniechu/content-team && /home/donniechu/hermes-agent/venv/bin/python card.py \\
  --kieu quote --ratio 4:5 \\
  --tagline "<CATEGORY ngan TIENG ANH>" \\
  --image /tmp/src_{draft_id}.png \\
  --title "<CAU HOOK co dau, dap vao mat trong 3s>" \\
  --attrib "<'via <bao>' hoac 'Phat bieu cua <ten>' neu la loi that>"{co_brand} \\
  --out {out_png}

Kieu tran (--kieu tran, kicker + tieu de mono, layout bang-tin co dien) van dung
duoc khi ban muon doi khong khi thay vi the hook — nhung MAC DINH la quote/hook.

Cac anh phu KHONG dung the — giu nguyen ban goc, chi doi ten thanh
{out_png_goc}_2.png, _3.png... de buoc dang sau gui thanh album.

BUOC 5 — GUI ANH LEN TOPIC CUA MINH NGAY (KHONG cho nguoi viet):
Dung xong the anh la viec cua ban da XONG — day anh ra topic cua chinh minh
ngay, KHONG cho Quinn/Miles viet xong roi moi co anh trong bai. Ong Chu ngoi o
Telegram, chi thay ket qua khi anh len topic; de anh nam trong drafts/ ma khong
gui thi voi Ong Chu y het nhu ban im lang.
cd /home/donniechu/content-team && venv/bin/python gui_telegram.py \\
  --vai {vai} --anh {out_png} --duyet {draft_id} --mo-ta "<mot cau anh nay la gi>"
Co anh phu ({out_png_goc}_2.png, _3.png...) thi lap them --anh cho tung tam de
gui thanh album. Gui xong moi ghi ket qua task.

`--duyet {draft_id}` gan BA nut duoi anh: "Duyet" (nguoi viet Quinn/Miles moi
viet caption), "Lam lai" (tao lai dung task nay, ban se dung ANH KHAC), "Bo han"
(giet tin). Vay nen viec cua ban chi la ra ANH cho that dat — dung cho, cung
dung tu di goi nguoi viet. Neu bi giao "lam lai", doc ghi chu cuoi task va chon
anh khac han lan truoc.

LUU Y — doc skill `hero-image` (muc "Kieu quote" la mac dinh, phan hero tran la
du phong). Day chi la phan hay sai nhat:

Chung ca hai kieu:
- Anh va chu la MOT mat phang lien. KHONG khung, KHONG vach, KHONG phu de.
- Chu TIENG VIET CO DAU. Nua duoi/vung dat chu phai TRONG; anh chup man hinh
  day chu thi doi anh khac.
- Ten hang trong chu duoc TO MAU tu dong, ban khong phai lam gi. Gap hang chua
  duoc to thi bao lai de them vao danh sach.

Kieu quote / hook (mac dinh):
- --title la CAU HOOK — dap vao mat trong 3 giay. Co the la tieu de/goc giat
  HOAC loi that cua nguoi trong bai. Cau NGAN de doc lon (cham 7 dong la cat).
- --tagline = CHIP CATEGORY (MODEL RELEASE / FUNDING / ROBOTICS / IN BRIEF...).
- --attrib: loi that -> "Phat bieu cua <ten>"; hook -> "via <bao>". Khong gan
  cau tu viet thanh loi mot nguoi cu the.
- Dau " trong khung tu doi mau theo hang duoc nhac, tu dong.

Kieu tran (layout bang-tin co dien, khi muon doi khong khi):
- KHONG --subtitle, KHONG --via, KHONG nhan category. Tren anh chi co bon thu:
  anh, kicker, tieu de, ten kenh.
- TIEU DE LA MOT CAU HOAN CHINH bao quat ca tin, khong gioi han so dong/ky tu;
  tin co so thi dua so vao chinh cau do.
- Kicker TIENG ANH, toi da hai tu: BREAKING / MODEL RELEASE / AGENT / FUNDING /
  BENCHMARK / OPEN SOURCE / M&A / RESEARCH / INFRA / POLICY.

- Nguon anh ({via}) KHONG con in tren anh nua. Bao lai nguon do trong ket qua
  task de nguoi viet caption dua vao bai — day la viec SONG SONG, KHONG phai
  dieu kien de gui anh. Ban da gui anh o buoc 5 roi moi ghi nguon cho ho.
- Ket qua bat buoc: file {out_png} phai ton tai VA da gui len topic (buoc 5)
  sau khi chay (tru truong hop buoc 3 — khong co anh that)."""


# Body cho Heller — dung carousel nhieu slide thay vi mot the bia. Khac ILLU_BODY
# o cho: khong chay card.py, ma viet copy tung slide roi chay carousel.py. Van
# dung anh_bai.py de tim anh that, van cong chan "khong tu ve minh hoa".
CAROUSEL_BODY = """Nguon: {source_note}
Link: {link}
Nguon anh (via): {via}
Chu de: {title}
Tom tat: {summary}

NHIEM VU: dung mot CAROUSEL nhieu slide ke tin nay, kieu bang tin — anh full be
ngang o tren TAN dan vao nen den, khoi chu trang o duoi, watermark nghieng o day.
Anh va chu la MOT mat phang lien: KHONG vien, KHONG vach, KHONG khung chia hai vung.

DOC SKILL `carousel` TRUOC khi lam — no co day du khung ke chuyen, cach viet copy
tung slide, luat chon anh, va cong chan. Duoi day chi la phan hay sai nhat.

NGUYEN TAC TREN HET: KHONG BAO GIO tu ve minh hoa. Moi slide phai co mot ANH THAT
lay tu nguon. Khong du anh that thi chia lai slide hoac gop y; cung lam thi bao
lai — tuyet doi khong dung hinh gia.

BUOC 1 — hieu tin du sau de chia slide. Finn DA research san, doc bo nguon nay:
  /home/donniechu/content-team/state/nguon_{draft_id}.json

BUOC 2 — tim anh that (BAT BUOC chay lenh nay):
cd /home/donniechu/content-team && venv/bin/python anh_bai.py \\
  --tieu-de "{title}" --link "{link}" --json \\
  --tu-nguon /home/donniechu/content-team/state/nguon_{draft_id}.json
Tai cac anh diem cao ve /tmp: /tmp/src_{draft_id}.png, /tmp/src_{draft_id}_2.png...
Bai arxiv khong co anh minh hoa thi chup bia paper:
  venv/bin/python arxiv_bia.py --link "{link}" --out /tmp/src_{draft_id}.png

BUOC 3 — chia tin thanh 4-8 slide va viet copy (theo khung ke chuyen trong skill):
  - BIA: mot cau HOOK giat khien nguoi ta dung luot (thuong la nghich ly hoac con
    so), kem mot NHAN NGAN. Cover can goc duoi-trai thoang de hook doc ro.
  - Cac slide sau: moi slide MOT y moi day nguoi doc sang slide sau (cai gi vua
    xay ra, con so gay soc, y nghia that, doi thu, cai can theo doi).
  - Slide cuoi de lai mot moc hoac cau hoi, khong chot cut.
  - Chu TIENG VIET CO DAU, cau ngan, moi doan 2-4 dong, tach doan bang dong trong.
  - CA CAU QUOTE (trich dan) cung phai DICH sang tieng Viet co dau — bai goc
    tieng Anh thi DICH cau trich, giu ten rieng/thuat ngu/so lieu; DUNG chep
    nguyen van tieng Anh vao quote.

BUOC 4 — ghi spec JSON roi dung (cac anh o BUOC 2 chia cho tung slide theo y):
cat > /tmp/carousel_{draft_id}.json <<'JSON'
{{
  "handle": "{brand}",
  "cover":  {{"image": "/tmp/src_{draft_id}.png", "hook": "<cau giat co dau>", "label": "<NHAN NGAN>"}},
  "slides": [
    {{"image": "/tmp/src_{draft_id}_2.png", "text": "doan mot.\\n\\ndoan hai."}},
    {{"image": "/tmp/src_{draft_id}_3.png", "text": "..."}}
  ]
}}
JSON
cd /home/donniechu/content-team && venv/bin/python carousel.py \\
  --spec /tmp/carousel_{draft_id}.json --out {out_png} --brand {brand}

Ra {out_png} (bia) + {out_png_goc}_2.png, _3.png... — draft_write.py tu gom thanh
album khi Quinn ghep draft, ban KHONG phai lam gi them o khau dang.

CONG CHAN: tieng Viet khong dau bi chan (chi tiếng Anh moi them --bo-qua-dau);
toi da 10 slide ke ca bia; thieu image/text mot slide thi dung.

BUOC 5 — GUI CAROUSEL LEN TOPIC CUA MINH NGAY (KHONG cho nguoi viet):
Dung xong bo slide la viec cua ban da XONG — day ca album ra topic cua chinh
minh ngay, KHONG cho Quinn/Miles viet xong roi moi co anh trong bai. Ong Chu
ngoi o Telegram, chi thay ket qua khi anh len topic.
cd /home/donniechu/content-team && venv/bin/python gui_telegram.py \\
  --vai {vai} --anh {out_png} --anh {out_png_goc}_2.png --anh {out_png_goc}_3.png \\
  --duyet {draft_id} --mo-ta "<mot cau carousel nay ve gi>"
Lap --anh cho DU so slide that su dung ra (bo bot cac dong _N.png khong ton tai,
them vao neu nhieu hon 3). Gui xong moi ghi ket qua task.

`--duyet {draft_id}` gan BA nut duoi album: "Duyet" (nguoi viet Quinn/Miles moi
viet caption), "Lam lai" (tao lai dung task nay, ban dung BO SLIDE khac), "Bo
han" (giet tin). Viec cua ban chi la ra BO SLIDE cho that dat — dung cho writer,
cung dung tu di goi nguoi viet. Neu bi giao "lam lai", doc ghi chu cuoi task va
lam khac lan truoc.

BAN GIAO: watermark tren slide KHONG phai ghi nguon. Bao lai nguon tin va nguon
tung anh ({via}) trong ket qua task de Quinn dua vao chu thich bai dang — viec
SONG SONG, KHONG phai dieu kien de gui anh.
Ket qua bat buoc: {out_png} phai ton tai VA da gui len topic (buoc 5)."""


WRITER_BODY = """Bai goc: {title}
Link: {link}
Nguon: {source_note}
Via: {via}
Diem Finn cham: {score}/100 -- ly do: {score_reason}
(Dung ly do diem nay de viet phan Y NGHIA — vi sao chuyen nay quan trong; noi thang
bang thong tin cu the, dung tu y suy dien, va KHONG dung cum "dang chu y / dang quan tam")

Du kien (Finn da tom tat — CHI la diem khoi dau, KHONG du de viet):
{summary}

BUOC 1 — DOC TU LIEU THAT (bat buoc, lam truoc khi viet mot chu nao):
cd /home/donniechu/content-team && venv/bin/python tu_lieu.py \\
  --tieu-de "{title}" --link "{link}" --out /tmp/tulieu_{draft_id}.md \\
  --tu-nguon /home/donniechu/content-team/state/nguon_{draft_id}.json

Script boc chu tu bai goc VA tu cac bao khac dua cung tin, roi tach rieng muc
"Cau co so lieu". Tom tat cua Finn khong co con so nao — viet chay theo no thi
bai ra cung khong co so nao. Da gap that: tin co bang 11 dong benchmark, caption
viet ra 0 con so.

BUOC 2 — VIET. Day la bai SOCIAL, khong phai trang tai lieu:
nhanh, khach quan, ngan gon, xuc tich.

Nguoi doc luot qua trong vai giay. Ho can biet: chuyen gi, con so nao dang nho,
va co dang quan tam khong. Ho KHONG can bang thong so day du — cai do da co
tren the anh va o link.

KHONG dung em-dash (dau — hoac –) o bat cu dau. Dung dau phay, dau hai cham,
hoac tach thanh cau rieng. Script se tu choi caption co dau nay.

TIEU CHUAN BIEN TAP:
- Moi CAU xuong dong rieng: het mot cau thi xuong dong roi moi viet cau tiep
  theo. Moi DOAN cach nhau MOT dong trong.
- KHONG de link song trong caption (script tu choi, ke ca ten mien tran nhu
  z.ai). Buoc phai nhac ten mien thi viet dau cham thanh " . " (vd z . ai) de
  no khong thanh link.
- KHONG dung cum sao rong "dang chu y", "dang quan tam" va bien the ("ly do
  dang chu y", "dang chu y vi", "dang quan tam vi"...). Script tu choi. Noi
  thang y nghia bang thong tin cu the.

Bon y BAT BUOC co, moi y mot cau la du:
- Chuyen gi vua xay ra, kem SO quan trong nhat
- So sanh: hon hay kem cai gi, cach biet bao nhieu. Neu nguon co noi cho THUA
  thi phai noi — bo di la thien lech, khong con khach quan
- Han che hoac dieu kien kem theo, neu nguon co noi
- Y NGHIA: vi sao chuyen nay quan trong (dung ly do Finn cham diem) — noi thang,
  KHONG dung cum "dang chu y / dang quan tam vi..."

Do dai: tan dung TOI DA 1024 ky tu, do la gioi han chu thich anh cua Telegram.
Vua trong muc do thi anh va chu di chung MOT tin nhan, doc gia thay ca hai cung
luc. Vuot qua la Telegram tach lam hai, anh mot noi chu mot noi.

Nham 800-1000 ky tu. Ngan gon nam o CACH VIET chu khong o viec cat bot y: moi
cau phai mang mot thong tin moi, khong cau nao lap lai cau truoc.

YEU CAU KY THUAT:
- Toi da 900 ky tu, HTML Telegram (chi <b> <i> <code>), dung cau truc SOUL.
- Ghi caption ra file tam /tmp/caption_{draft_id}.txt (CHI caption, khong kem gi khac).
- Tu kiem truoc khi ghep draft:
    cd /home/donniechu/content-team && venv/bin/python caption_check.py \\
      --caption-file /tmp/caption_{draft_id}.txt --tu-lieu /tmp/tulieu_{draft_id}.md
- Ghep draft bang lenh sau — script tu dien source_url / category / via / duong dan anh,
  BAN KHONG CAN go lai nhung gia tri do:
    cd /home/donniechu/content-team && venv/bin/python draft_write.py {draft_id} --caption-file /tmp/caption_{draft_id}.txt --tu-lieu /tmp/tulieu_{draft_id}.md
- Day vao hang duyet:
    cd /home/donniechu/content-team && venv/bin/python approve_service.py push {draft_id}
- KHONG tu dang len channel."""


def kanban_create(title, assignee, body, parent=None):
    env = dict(os.environ, HERMES_HOME=HERMES_HOME)
    args = [str(HERMES_PY), "-m", "hermes_cli.main", "kanban", "create", title,
            "--assignee", assignee, "--max-runtime", "25m", "--json",
            "--body", body]
    if parent:
        args += ["--parent", parent]
    r = subprocess.run(args, cwd=str(Path.home() / "hermes-agent"),
                        env=env, capture_output=True, text=True, timeout=60)
    if r.returncode != 0:
        return None, (r.stderr[-300:] or r.stdout[-300:])
    try:
        return json.loads(r.stdout)["id"], None
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

    # Tach theo THUONG HIEU: viec anh dcgr bao ve topic Miles, donniechublog ve
    # Quinn — dung nguoi viet cua brand do, khong dua het ve Quinn.
    nhom = {}
    for tid, ai, ten, tieu_de, ly_do in moi:
        brand = BRAND
        vai_viet = VAI_VIET.get(brand, MAC_DINH_VIET)
        nhom.setdefault(vai_viet, []).append((tid, ten, tieu_de, ly_do))

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

    # Heller va Dre dung carousel nhieu slide, cac vai anh khac dung the bia.
    # Cung bo bien nhu nhau nen chon khuon roi format chung; .format bo qua
    # key thua.
    la_carousel = vai_anh in VAI_CAROUSEL
    khuon = CAROUSEL_BODY if la_carousel else ILLU_BODY
    illu_body = khuon.format(
        source_note=item.get("source_note", ""), link=item["link"],
        via=item.get("via", ""), title=item["title"],
        summary=item.get("summary_vi", ""),
        image_url=item.get("image_url") or "khong co",
        out_png=out_png, out_png_goc=out_png[:-4],
        category=chuan_nhan(item.get("category")), draft_id=draft_id,
        brand=brand, vai=vai_anh,
        co_brand=("" if brand == "donniechublog" else f" --brand {brand}"))
    tieu_de_task = ("Carousel: " if la_carousel else "Anh: ") + item["title"]
    illu_id, err = kanban_create(tieu_de_task, vai_anh, illu_body)
    if err:
        return None, "Loi tao task anh: " + err

    # Cat lai body task anh de LAM LAI duoc: Ong Chu bam "Lam lai" tren anh chua
    # dat thi tao lai dung task nay (them ghi chu doi anh khac). Thieu file nay
    # thi nut Lam lai bao khong co thong tin.
    (DRAFTS / (draft_id + ".img.json")).write_text(
        json.dumps({"vai_anh": vai_anh, "carousel": la_carousel,
                    "title": item["title"], "body": illu_body, "remakes": 0},
                   ensure_ascii=False, indent=2), encoding="utf-8")

    # KHONG tao task viet ngay nua. Tinh san writer_body + vai_viet roi cat vao
    # sidecar `<draft_id>.writer.json`; task viet CHI sinh khi Ong Chu bam
    # "Duyet anh" (imgok) tren tam anh ma Chad/Ethan/Heller/Dre vua day len
    # topic. Anh chua dat thi khong co writer nao ca — dung y Ong Chu: khong
    # nhat thiet phai co writer sau khi tao hinh, o thi moi viet caption.
    writer_body = WRITER_BODY.format(
        title=item["title"], link=item["link"],
        source_note=item.get("source_note", ""), via=item.get("via", ""),
        score=item.get("score", "?"),
        score_reason=item.get("score_reason", ""),
        summary=item.get("summary_vi", ""), out_png=out_png,
        out_json=out_json, category=chuan_nhan(item.get("category")),
        draft_id=draft_id)
    vai_viet = VAI_VIET.get(brand, MAC_DINH_VIET)
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
    return (illu_id, None), None


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
    call(token, "sendMessage", chat_id=group,
         **({"message_thread_id": thread_id} if thread_id else {}),
         text=f"⏳ Đang chuyển cho <b>{who}</b>…", parse_mode="HTML")

    out, err = chat_router.ask(profile, session, text)
    reply = ("⚠️ " + err) if err else chat_router.clean(out)
    # Reply dai vuot 4096 se bi Telegram tu choi/cat -> chia thanh nhieu tin
    # gui lien tiep (dung thu tu), thay vi cat bot phan cuoi.
    for phan in chat_router.chia_tin(reply):
        call(token, "sendMessage", chat_id=group,
             **({"message_thread_id": thread_id} if thread_id else {}),
             text=phan, disable_web_page_preview=True)


# ---------- lenh slash (dat bai tuong minh) ----------
# Nguyen tac: mot dau "/" nghia la Ong Chu dang RA LENH, khong tro chuyen.
# Dung cu phap moi chay; sai cu phap / sai ten vai / URL hong thi bao ngan
# va dung han — khong roi ve hoi thoai, khong tu suy dien "chac y la...".

DAT_BAI_SO = STATE_DIR / "dat_bai.json"     # so dedup: url chuan hoa -> lan dat
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
    ids, err = create_pair(item, vai_anh=vai_anh, brand=brand)
    if err:
        tra_loi("❌ " + html_escape(err))
        return

    draft_id = _draft_id(item, brand, vai_anh)
    so[url_chuan] = {"ngay": time.strftime("%Y-%m-%d %H:%M"),
                     "draft_id": draft_id, "vai": vai_anh, "brand": brand,
                     "tasks": [x for x in ids if x], "title": title}
    tmp = DAT_BAI_SO.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(so, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, DAT_BAI_SO)

    ten_hien = TEN_VAI_ANH.get(vai_anh, "Chad")
    ten_viet = TEN_VAI_VIET.get(VAI_VIET.get(brand, MAC_DINH_VIET), "Quinn")
    dong = ("✅ <b>" + html_escape(title) + "</b>\n"
            + f"{ten_hien} dựng ảnh ({brand}) — task {ids[0]}. "
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
            kieu = "carousel" if va in VAI_CAROUSEL else "thẻ bìa"
            dong.append(f"  <code>{ten}</code> → {va} ({kieu})")
        dong.append("<b>Vai viết</b>: <code>writer</code> — một người viết cho container này.")
        tra_loi("\n".join(dong))
    elif lenh == "/bai":
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


def handle_message(token, group, scout_thread, msg):
    if msg.get("from", {}).get("is_bot"):
        return
    if msg.get("chat", {}).get("id") != int(group):
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

    if not text:
        return
    thread_id = msg.get("message_thread_id")

    # Dau "/" = LENH, o bat ky topic nao — xu ly rieng, khong bao gio roi ve
    # hoi thoai (mot lenh go sai ma dem hoi LLM la vua on ao vua nguy hiem).
    # Chay nen: /bai co buoc fetch trang + research (nguon_bai, toi 180s),
    # khong duoc nghen vong poll — cung ly do voi handle_chat ben duoi.
    if text.startswith("/"):
        threading.Thread(target=handle_command, daemon=True,
                         args=(token, group, msg, thread_id, text)).start()
        return

    # So trong topic cua MOT VAI DI TIM TIN = lenh chon tin. Moi thu khac la
    # hoi thoai. Finn, Nova, Vera deu duoc — cung mot cach tra loi.
    vai = vai_cua_topic(thread_id)
    lenh = doc_lenh_chon(text) if vai in MANIFEST_THEO_TOPIC else None
    is_pick = lenh is not None
    if not is_pick:
        # Chay nen: mot lan goi agent co the toi 10 phut, khong duoc de nghen
        # vong lap poll (nut Duyet/Bo phai bam duoc bat cu luc nao).
        threading.Thread(target=handle_chat, daemon=True,
                         args=(token, group, msg, thread_id, text)).start()
        return

    manifest_path = latest_manifest(vai)
    if not manifest_path:
        call(token, "sendMessage", chat_id=group, message_thread_id=thread_id,
             text="Chưa có danh sách tin nào để chọn trong topic này.")
        return

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
        ids, err = create_pair(it, vai_anh=vai_anh, brand=brand)
        if err:
            lines.append("#" + str(n) + ": lỗi — " + err)
            continue
        changed = True          # create_pair da danh dau vao `it`
        ten_hien = TEN_VAI_ANH.get(vai_anh, "Chad")
        ten_viet = TEN_VAI_VIET.get(VAI_VIET.get(brand, MAC_DINH_VIET), "Quinn")
        lines.append(f"#{n}: {ten_hien} dựng ảnh ({brand}) — task {ids[0]}"
                     f"; {ten_viet} viết caption sau khi Ông Chủ duyệt ảnh")

    if changed:
        manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
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
    scout_thread = scout_thread_id()
    offset = _doc_offset()
    print("[approve_service] chay, offset=" + str(offset) +
          ", scout_thread=" + str(scout_thread), flush=True)
    loi_lien_tiep = 0
    while True:
        try:
            r = call(token, "getUpdates", offset=offset, timeout=50,
                     allowed_updates=["callback_query", "message"])
            if not r.get("ok"):
                # 409 (hai poller cung token) / 429: long-poll khong giu duoc,
                # request tra ve NGAY -> khong sleep la nen API vo han.
                print("[approve_service] getUpdates tu choi: "
                      + str(r.get("description")), flush=True)
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
                if "callback_query" in u:
                    handle_callback(token, channel, u["callback_query"])
                elif "message" in u:
                    handle_message(token, group, scout_thread, u["message"])
            # getUpdates cho toi 50 giay moi luot, nen goi moi vong la du thua
            # cho viec nay: no chi doc mot cau SQL va thuong khong gui gi.
            bao_viec_bi_chan(token, group)
            loi_lien_tiep = 0
        except Exception as e:                              # noqa: BLE001
            loi_lien_tiep += 1
            print("[approve_service] loi: " + type(e).__name__ + ": " + str(e),
                  flush=True)
            time.sleep(min(60, 5 * loi_lien_tiep))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "push":
        tok, _ch, grp = load_secrets()
        draft_id = sys.argv[2]
        # Dinh tuyen topic theo loai noi dung: teaser ve topic Jean, tin tuc
        # ve topic Quinn. Tham so thu 3 (neu co) van ghi de duoc.
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
                # donniechublog -> Quinn. Truoc day MOI draft deu ve topic Quinn
                # nen trong nhu Quinn om ca dcgr; that ra Miles viet caption dcgr,
                # chi la ban nhap bi day nham topic. Brand nam trong sidecar meta.
                brand = ""
                mpath = DRAFTS / (draft_id + ".meta.json")
                if mpath.exists():
                    try:
                        brand = json.loads(
                            mpath.read_text(encoding="utf-8")).get("brand", "")
                    except Exception:                            # noqa: BLE001
                        pass
                key = VAI_VIET.get(brand, MAC_DINH_VIET)
            thread = topics.get(key)
        if len(sys.argv) > 3:
            thread = int(sys.argv[3])
        res = draft_push(tok, grp, draft_id, thread_id=thread)
        print("day ban nhap -> topic " + str(thread) + " | " +
              ("OK" if res.get("ok") else str(res.get("description"))))
    else:
        loop()
