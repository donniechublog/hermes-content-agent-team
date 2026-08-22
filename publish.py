#!/usr/bin/env python3
"""Dang bai len Telegram: text hoac anh kem chu thich.

Doc TELEGRAM_BOT_TOKEN / TELEGRAM_CHANNEL_ID tu ~/content-team/.secrets.env.
Dung cho vai publisher trong pipeline noi dung.
"""
import argparse
import os
import re
import sys
from pathlib import Path

import httpx

import env_load
API = "https://api.telegram.org/bot{token}/{method}"
CAPTION_LIMIT = 1024          # gioi han caption cua Telegram
TEXT_LIMIT = 4096


def load_secrets():
    env_load.nap()
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHANNEL_ID")
    if not tok:
        sys.exit("Thieu TELEGRAM_BOT_TOKEN")
    return tok, chat


# Telegram chi hieu mot tap the RAT HEP. Cac the khoi (<br>, <p>, <li>...) bi
# TU CHOI HAN — tra ve "Bad Request: Unsupported start tag", chu khong phai lo di.
# Da kiem chung. Nen phai tu doi chung thanh xuong dong that truoc khi gui.
THE_HOP_LE = {"b", "strong", "i", "em", "u", "ins", "s", "strike", "del",
              "a", "code", "pre", "blockquote", "span", "tg-spoiler"}

# The khoi -> xuong dong
_KHOI = [
    (re.compile(r"<br\s*/?>", re.I), "\n"),
    (re.compile(r"</(p|div|h[1-6]|tr)>", re.I), "\n\n"),
    (re.compile(r"<li[^>]*>", re.I), "• "),
    (re.compile(r"</li>", re.I), "\n"),
    (re.compile(r"</?(ul|ol|table|tbody|thead)[^>]*>", re.I), "\n"),
    (re.compile(r"<(p|div|h[1-6]|tr)[^>]*>", re.I), ""),
]


def don_dep(text: str) -> str:
    """Lam sach chu truoc khi gui Telegram — sua dung ba loi thuong gap.

    1. Agent viet chuoi mot dong voi \\n VAN BAN (dau gach nguoc + n) vi phai
       nhet vao mot tham so shell. Telegram in ra nguyen chu \\n, hoac te hon
       la ca bai dinh lien nhau. Doi thanh xuong dong that.
    2. Agent viet HTML day du co <br>, <p>, <li>. Telegram TU CHOI ca tin nhan.
       Doi the khoi thanh xuong dong, bo cac the con lai khong nam trong danh
       sach hop le.
    3. Thua qua ba dong trong lien tiep thi gop lai — khong ai muon doc khoang
       trong dai.
    """
    if not text:
        return text
    # 1. \n van ban -> xuong dong that (chi khi KHONG co xuong dong that nao)
    if "\\n" in text and "\n" not in text:
        text = text.replace("\\r\\n", "\n").replace("\\n", "\n")
    # 2. the khoi -> xuong dong
    for pat, thay in _KHOI:
        text = pat.sub(thay, text)
    # bo the khong hop le, giu the hop le nguyen ven
    def _bo(m):
        ten = (m.group(1) or "").lower()
        return m.group(0) if ten in THE_HOP_LE else ""
    text = re.sub(r"</?([a-zA-Z][a-zA-Z0-9-]*)[^>]*>", _bo, text)
    # 3. gop dong trong thua
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _check(r: httpx.Response):
    data = r.json()
    if not data.get("ok"):
        sys.exit(f"Telegram tu choi: {data.get('description')}")
    return data["result"]


def send_text(token, chat, text, parse_mode="HTML", thread=None):
    text = don_dep(text)
    if len(text) > TEXT_LIMIT:
        text = text[: TEXT_LIMIT - 1] + "…"
    with httpx.Client(timeout=60) as c:
        payload = {"chat_id": chat, "text": text, "parse_mode": parse_mode,
                   "disable_web_page_preview": True}
        if thread:
            payload["message_thread_id"] = int(thread)
        r = c.post(API.format(token=token, method="sendMessage"), json=payload)
    return _check(r)


def send_photo(token, chat, photo: Path, caption="", parse_mode="HTML", thread=None):
    caption = don_dep(caption)
    if len(caption) > CAPTION_LIMIT:
        sys.exit(f"Caption {len(caption)} ky tu, vuot gioi han {CAPTION_LIMIT} "
                 f"cua Telegram. Rut ngan hoac tach thanh tin rieng.")
    with httpx.Client(timeout=120) as c, photo.open("rb") as fh:
        r = c.post(API.format(token=token, method="sendPhoto"),
                   data={"chat_id": chat, "caption": caption,
                         "parse_mode": parse_mode,
                         **({"message_thread_id": str(int(thread))} if thread else {})},
                   files={"photo": (photo.name, fh, "image/png")})
    return _check(r)


def send_media_group(token, chat, media, caption="", parse_mode="HTML",
                     thread=None):
    """Gui album nhieu anh. `media` la danh sach URL (http...) hoac Path cuc bo.

    Chu thich chi gan vao anh DAU TIEN — dung quy tac cua Telegram cho album.
    """
    caption = don_dep(caption)
    if len(caption) > CAPTION_LIMIT:
        sys.exit(f"Caption {len(caption)} ky tu, vuot gioi han {CAPTION_LIMIT} "
                 f"cua Telegram. Rut ngan hoac tach thanh tin rieng.")
    items, files = [], {}
    for i, m in enumerate(media):
        m = str(m)
        entry = {"type": "photo"}
        if i == 0 and caption:
            entry["caption"] = caption
            entry["parse_mode"] = parse_mode
        if m.startswith("http://") or m.startswith("https://"):
            entry["media"] = m
        else:
            key = f"file{i}"
            entry["media"] = f"attach://{key}"
            files[key] = open(m, "rb")
        items.append(entry)
    data = {"chat_id": chat, "media": __import__("json").dumps(items)}
    if thread:
        data["message_thread_id"] = str(int(thread))
    try:
        with httpx.Client(timeout=120) as c:
            r = c.post(API.format(token=token, method="sendMediaGroup"),
                      data=data, files=files or None)
    finally:
        for fh in files.values():
            fh.close()
    return _check(r)


def main():
    p = argparse.ArgumentParser(description="Dang bai len Telegram channel")
    p.add_argument("--photo", type=Path, help="Duong dan anh")
    p.add_argument("--caption", default="", help="Chu thich anh (toi da 1024)")
    p.add_argument("--text", help="Dang tin chi co chu")
    p.add_argument("--to", help="Ghi de chat_id dich")
    p.add_argument("--thread", help="message_thread_id (topic) trong group")
    p.add_argument("--file", type=Path, help="Doc noi dung tu file")
    p.add_argument("--album", nargs="+",
                   help="Gui nhieu anh (URL hoac duong dan cuc bo) thanh 1 album")
    a = p.parse_args()

    token, chat = load_secrets()
    chat = a.to or chat
    if not chat:
        sys.exit("Thieu TELEGRAM_CHANNEL_ID (hoac dung --to)")

    body = a.file.read_text(encoding="utf-8") if a.file else None

    if a.album:
        res = send_media_group(token, chat, a.album, body or a.caption,
                               thread=a.thread)
    elif a.photo:
        res = send_photo(token, chat, a.photo, body or a.caption, thread=a.thread)
    else:
        text = body or a.text
        if not text:
            sys.exit("Can --text, --file hoac --photo")
        res = send_text(token, chat, text, thread=a.thread)
    print(f"da dang | message_id={res.get('message_id')} chat={chat}")


if __name__ == "__main__":
    main()
