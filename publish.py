#!/usr/bin/env python3
"""Dang bai len Telegram: text hoac anh kem chu thich.

Doc TELEGRAM_BOT_TOKEN / TELEGRAM_CHANNEL_ID tu ~/content-team/.secrets.env.
Dung cho vai publisher trong pipeline noi dung.
"""
import argparse
import os
import sys
from pathlib import Path

import httpx

SECRETS = Path.home() / "content-team" / ".secrets.env"
API = "https://api.telegram.org/bot{token}/{method}"
CAPTION_LIMIT = 1024          # gioi han caption cua Telegram
TEXT_LIMIT = 4096


def load_secrets():
    if SECRETS.exists():
        for line in SECRETS.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip())
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_CHANNEL_ID")
    if not tok:
        sys.exit("Thieu TELEGRAM_BOT_TOKEN")
    return tok, chat


def _check(r: httpx.Response):
    data = r.json()
    if not data.get("ok"):
        sys.exit(f"Telegram tu choi: {data.get('description')}")
    return data["result"]


def send_text(token, chat, text, parse_mode="HTML", thread=None):
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


def main():
    p = argparse.ArgumentParser(description="Dang bai len Telegram channel")
    p.add_argument("--photo", type=Path, help="Duong dan anh")
    p.add_argument("--caption", default="", help="Chu thich anh (toi da 1024)")
    p.add_argument("--text", help="Dang tin chi co chu")
    p.add_argument("--to", help="Ghi de chat_id dich")
    p.add_argument("--thread", help="message_thread_id (topic) trong group")
    p.add_argument("--file", type=Path, help="Doc noi dung tu file")
    a = p.parse_args()

    token, chat = load_secrets()
    chat = a.to or chat
    if not chat:
        sys.exit("Thieu TELEGRAM_CHANNEL_ID (hoac dung --to)")

    body = a.file.read_text(encoding="utf-8") if a.file else None

    if a.photo:
        res = send_photo(token, chat, a.photo, body or a.caption, thread=a.thread)
    else:
        text = body or a.text
        if not text:
            sys.exit("Can --text, --file hoac --photo")
        res = send_text(token, chat, text, thread=a.thread)
    print(f"da dang | message_id={res.get('message_id')} chat={chat}")


if __name__ == "__main__":
    main()
