#!/usr/bin/env python3
"""Dich vu Telegram cho content-team: duyet bai (nut bam) + chon tin (reply so).

Chi MOT tien trinh duoc long-poll mot bot token voi mot offset -- Telegram
getUpdates xac nhan (va xoa khoi hang doi) MOI update tinh toi offset, khong
chi loai dang loc qua allowed_updates. Chay hai poller doc lap se lam rot
update cua nhau. Vi vay dich vu nay xu ly ca hai luong trong cung mot vong lap:

  A) callback_query -- nut Duyet/Bo tren ban nhap draft (nhu truoc)
  B) message -- Ong Chu reply so thu tu trong topic scout -> tao cap task
     illustrator+writer cho dung tin da chon trong manifest cua Finn
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path.home() / "content-team"
DRAFTS = ROOT / "drafts"
STATE_DIR = ROOT / "state"
OFFSET = STATE_DIR / "offset.txt"
API = "https://api.telegram.org/bot{token}/{method}"
HERMES_PY = Path.home() / "hermes-agent" / "venv" / "bin" / "python"
HERMES_HOME = str(Path.home() / ".hermes")


def load_secrets():
    p = ROOT / ".secrets.env"
    if p.exists():
        for line in p.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
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
    p = STATE_DIR / "topics.json"
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
    """Gui album URL anh (Telegram tu tai, khong can file cuc bo). Album
    KHONG the gan nut bam -- day la gioi han cua Telegram Bot API."""
    items = [{"type": "photo", "media": m} for m in media]
    data = {"chat_id": chat, "media": json.dumps(items)}
    if thread_id:
        data["message_thread_id"] = str(int(thread_id))
    with httpx.Client(timeout=120) as c:
        r = c.post(API.format(token=token, method="sendMediaGroup"), data=data)
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
        _send_media_group(token, group, images, thread_id)
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
        items = [{"type": "photo", "media": m} for m in images]
        if not long_caption:
            items[0]["caption"] = caption
            items[0]["parse_mode"] = "HTML"
        with httpx.Client(timeout=120) as c:
            r = c.post(API.format(token=token, method="sendMediaGroup"),
                      data={"chat_id": channel, "media": json.dumps(items)})
        res = r.json()
        if long_caption and res.get("ok"):
            return call(token, "sendMessage", chat_id=channel, text=caption,
                        parse_mode="HTML", disable_web_page_preview=True)
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
            return call(token, "sendMessage", chat_id=channel, text=caption,
                        parse_mode="HTML", disable_web_page_preview=True)
        return res
    return call(token, "sendMessage", chat_id=channel, text=caption,
                parse_mode="HTML", disable_web_page_preview=True)


def mark_draft(draft_id, status):
    p = DRAFTS / (draft_id + ".json")
    d = json.loads(p.read_text(encoding="utf-8"))
    d["status"] = status
    d["decided_at"] = int(time.time())
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def handle_callback(token, channel, cq):
    data = cq.get("data", "")
    action, _, draft_id = data.partition(":")
    msg = cq["message"]
    chat_id, msg_id = msg["chat"]["id"], msg["message_id"]

    if not (DRAFTS / (draft_id + ".json")).exists():
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Không tìm thấy bản nháp", show_alert=True)
        return

    if action == "ok":
        res = publish(token, channel, draft_id)
        ok = res.get("ok")
        mark_draft(draft_id, "published" if ok else "publish_failed")
        note = ("✅ ĐÃ ĐĂNG lên channel" if ok
                else "⚠️ Đăng lỗi: " + str(res.get("description")))
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Đã đăng" if ok else "Lỗi khi đăng")
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
    call(token, method, chat_id=chat_id, message_id=msg_id,
         **{key: body + "\n\n<b>" + note + "</b>"}, parse_mode="HTML",
         reply_markup={"inline_keyboard": []})


# ---------- B) Ong Chu reply so thu tu -> tao cap task ----------

def slugify(title, fallback):
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return (s[:40].strip("-") or fallback)


def latest_manifest():
    files = sorted(STATE_DIR.glob("finn_candidates_*.json"))
    return files[-1] if files else None


ILLU_BODY = """Nguon: {source_note}
Link: {link}
Nguon anh (via): {via}
Chu de: {title}
Tom tat: {summary}
image_url: {image_url}

NHIEM VU: dung the anh cho bai nay.

BUOC 1 — co anh nguon:
- Neu image_url o tren khac "khong co": tai anh ve /tmp/src_{draft_id}.png
- Neu anh co chu thich tieng Anh, doc va dich sang tieng Viet de dung cho subtitle

BUOC 2 — khong co anh nguon thi tu ve SVG:
- Viet file SVG 1200x1200 (vuong), nen xanh dem gradient #0e1117 -> #161b22,
  net trang tri mau #00cce0, minh hoa truu tuong dung chu de
- TUYET DOI KHONG dat chu nao trong SVG (khong the <text>)
- Render: rsvg-convert /tmp/illu_{draft_id}.svg -o /tmp/src_{draft_id}.png

BUOC 3 — dung the (BAT BUOC chay lenh nay):
cd /home/donniechu/content-team && /home/donniechu/hermes-agent/venv/bin/python card.py \
  --image /tmp/src_{draft_id}.png \
  --title "<tieu de ngan, TOI DA 60 KY TU>" \
  --subtitle "<mot cau tom tat y chinh, toi da 140 ky tu>" \
  --via "{via}" \
  --category "{category}" \
  --category-right "<nhan phu ngan, vd: MA NGUON MO / BENCHMARK / M&A>" \
  --ratio 1:1 \
  --out {out_png}

LUU Y QUAN TRONG:
- Tieu de dung font don cach (JetBrains Mono) nen chiem nhieu be ngang.
  Qua 60 ky tu se bi thu nho hoac cat bot. Viet NGAN va DAT.
- Tieu de va subtitle deu bang TIENG VIET CO DAU.
- Ket qua bat buoc: file {out_png} phai ton tai sau khi chay."""

WRITER_BODY = """Bai goc: {title}
Link: {link}
Nguon: {source_note}
Via: {via}
Diem Finn cham: {score}/100 -- ly do: {score_reason}
(Dung ly do diem nay de viet phan "vi sao dang chu y" trong bai, dung tu y suy dien them)

Du kien (Finn da tom tat):
{summary}

YEU CAU:
- Viet caption tieng Viet toi da 900 ky tu, dinh dang HTML Telegram (chi <b> <i> <code>), dung cau truc SOUL.
- Ghi caption ra file tam, vi du /tmp/caption_{draft_id}.txt (CHI caption, khong kem gi khac).
- Ghep draft bang lenh sau — script tu dien source_url / category / via / duong dan anh,
  BAN KHONG CAN go lai nhung gia tri do:
    cd /home/donniechu/content-team && venv/bin/python draft_write.py {draft_id} --caption-file /tmp/caption_{draft_id}.txt
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


def write_meta(draft_id, item, out_png):
    """Ghi san metadata cho draft — writer khoi phai go lai bang tay.

    Nhung gia tri nay Finn da quyet tu luc quet; bat LLM go lai chi tao co hoi
    go sai. draft_write.py se doc file nay khi ghep draft cuoi cung.
    """
    meta = {
        "source_url": item["link"],
        "category": item.get("category", "CONG CU"),
        "via": item.get("via", ""),
        "image": out_png,
        "title": item["title"],
        "score": item.get("score"),
        "score_reason": item.get("score_reason", ""),
    }
    DRAFTS.mkdir(parents=True, exist_ok=True)
    (DRAFTS / (draft_id + ".meta.json")).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def create_pair(item):
    draft_id = slugify(item["title"], "item-" + str(item["index"]))
    out_png = str(DRAFTS / (draft_id + ".png"))
    out_json = str(DRAFTS / (draft_id + ".json"))
    write_meta(draft_id, item, out_png)

    illu_body = ILLU_BODY.format(
        source_note=item.get("source_note", ""), link=item["link"],
        via=item.get("via", ""), title=item["title"],
        summary=item.get("summary_vi", ""),
        image_url=item.get("image_url") or "khong co",
        out_png=out_png, category=item.get("category", "CONG CU"),
        draft_id=draft_id)
    illu_id, err = kanban_create("Anh: " + item["title"], "illustrator", illu_body)
    if err:
        return None, "Loi tao task anh: " + err

    writer_body = WRITER_BODY.format(
        title=item["title"], link=item["link"],
        source_note=item.get("source_note", ""), via=item.get("via", ""),
        score=item.get("score", "?"),
        score_reason=item.get("score_reason", ""),
        summary=item.get("summary_vi", ""), out_png=out_png,
        out_json=out_json, category=item.get("category", "CONG CU"),
        draft_id=draft_id)
    writer_id, err = kanban_create("Bai: " + item["title"], "writer",
                                    writer_body, parent=illu_id)
    if err:
        return None, "Loi tao task viet: " + err
    return (illu_id, writer_id), None


def handle_message(token, group, scout_thread, msg):
    if msg.get("from", {}).get("is_bot"):
        return
    if msg.get("chat", {}).get("id") != int(group):
        return
    if scout_thread is None or msg.get("message_thread_id") != int(scout_thread):
        return
    text = (msg.get("text") or "").strip()
    if not text or not re.fullmatch(r"[\d,\s]+", text):
        return  # khong phai lenh chon so -- im lang

    nums = sorted(set(int(n) for n in re.findall(r"\d+", text)))
    manifest_path = latest_manifest()
    if not manifest_path:
        call(token, "sendMessage", chat_id=group, message_thread_id=scout_thread,
             text="Chưa có danh sách tin nào hôm nay để chọn.")
        return

    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    items = {it["index"]: it for it in data.get("items", [])}
    lines = []
    changed = False
    for n in nums:
        it = items.get(n)
        if not it:
            lines.append("#" + str(n) + ": không tìm thấy")
            continue
        if it.get("picked"):
            lines.append("#" + str(n) + ": đã chọn trước đó")
            continue
        ids, err = create_pair(it)
        if err:
            lines.append("#" + str(n) + ": lỗi — " + err)
            continue
        it["picked"] = True
        changed = True
        lines.append("#" + str(n) + ": đã tạo task ảnh " + ids[0] + " + viết " + ids[1])

    if changed:
        manifest_path.write_text(json.dumps(data, ensure_ascii=False, indent=2),
                                  encoding="utf-8")
    call(token, "sendMessage", chat_id=group, message_thread_id=scout_thread,
         text="<b>Kết quả chọn:</b>\n" + "\n".join(lines), parse_mode="HTML")


# ---------- vong lap chinh ----------

def loop():
    token, channel, group = load_secrets()
    scout_thread = scout_thread_id()
    offset = int(OFFSET.read_text()) if OFFSET.exists() else 0
    print("[approve_service] chay, offset=" + str(offset) +
          ", scout_thread=" + str(scout_thread), flush=True)
    while True:
        try:
            r = call(token, "getUpdates", offset=offset, timeout=50,
                     allowed_updates=["callback_query", "message"])
            for u in r.get("result", []):
                offset = u["update_id"] + 1
                if "callback_query" in u:
                    handle_callback(token, channel, u["callback_query"])
                elif "message" in u:
                    handle_message(token, group, scout_thread, u["message"])
            OFFSET.parent.mkdir(parents=True, exist_ok=True)
            OFFSET.write_text(str(offset))
        except Exception as e:                              # noqa: BLE001
            print("[approve_service] loi: " + type(e).__name__ + ": " + str(e),
                  flush=True)
            time.sleep(5)


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "push":
        tok, _ch, grp = load_secrets()
        draft_id = sys.argv[2]
        # Dinh tuyen topic theo loai noi dung: teaser ve topic Jean, tin tuc
        # ve topic Quinn. Tham so thu 3 (neu co) van ghi de duoc.
        thread = None
        tp = STATE_DIR / "topics.json"
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
            thread = topics.get(key)
        if len(sys.argv) > 3:
            thread = int(sys.argv[3])
        res = draft_push(tok, grp, draft_id, thread_id=thread)
        print("day ban nhap -> topic " + str(thread) + " | " +
              ("OK" if res.get("ok") else str(res.get("description"))))
    else:
        loop()
