#!/usr/bin/env python3
"""Dang bai len Telegram: text hoac anh kem chu thich.

Doc TELEGRAM_BOT_TOKEN / TELEGRAM_CHANNEL_ID tu ~/content-team/.secrets.env.
Dung cho vai publisher trong pipeline noi dung.
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx

import env_load
import tele_util
API = "https://api.telegram.org/bot{token}/{method}"
CAPTION_LIMIT = 1024          # gioi han caption cua Telegram


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
    # 3. bo em-dash. Ong Chu khong dung dau nay trong van ban dang len kenh.
    #    " — " giua cau thanh dau phay; dinh lien chu thanh gach ngang thuong.
    text = re.sub(r"\s+[\u2014\u2013]\s+", ", ", text)
    text = re.sub(r"(?<=\w)[\u2014\u2013](?=\w)", "-", text)
    text = text.replace("\u2014", ",").replace("\u2013", "-")
    text = re.sub(r",\s*,", ",", text)
    # 4. gop dong trong thua
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


class TelegramTuChoi(RuntimeError):
    """Telegram tra ok:false. La Exception THUONG, khong phai SystemExit.

    Truoc day _check goi sys.exit() — SystemExit ke thua BaseException nen
    xuyen qua moi `except Exception` cua NGUOI GOI THU VIEN: moat_publish
    da ghi `reported` xong, goi _notify, Telegram 429 -> sys.exit giet ca
    tien trinh cron -> khong bao gio bao lai. CLI van thoat gon: main() bat
    loi nay va exit(1).
    """


def _check(r: httpx.Response):
    data = r.json()
    if not data.get("ok"):
        raise TelegramTuChoi(f"Telegram tu choi: {data.get('description')}")
    return data["result"]


def send_text(token, chat, text, parse_mode="HTML", thread=None):
    """Gui text; neu dai qua gioi han Telegram thi chia thanh nhieu tin gui
    lien tiep thay vi cat bot phan cuoi. Tra ve result cua tin cuoi."""
    ket_qua = None
    for phan in tele_util.chia_tin(don_dep(text)):
        with httpx.Client(timeout=60) as c:
            payload = {"chat_id": chat, "text": phan, "parse_mode": parse_mode,
                       "disable_web_page_preview": True}
            if thread:
                payload["message_thread_id"] = int(thread)
            r = c.post(API.format(token=token, method="sendMessage"), json=payload)
        ket_qua = _check(r)
    return ket_qua


def send_photo(token, chat, photo: Path, caption="", parse_mode="HTML", thread=None):
    caption = don_dep(caption)
    if len(caption) > CAPTION_LIMIT:
        # Exception thuong, KHONG sys.exit: day la ham thu vien — xem TelegramTuChoi.
        raise TelegramTuChoi(
            f"Caption {len(caption)} ky tu, vuot gioi han {CAPTION_LIMIT} "
            f"cua Telegram. Rut ngan hoac tach thanh tin rieng.")
    with httpx.Client(timeout=120) as c, photo.open("rb") as fh:
        r = c.post(API.format(token=token, method="sendPhoto"),
                   data={"chat_id": chat, "caption": caption,
                         "parse_mode": parse_mode,
                         **({"message_thread_id": str(int(thread))} if thread else {})},
                   files={"photo": (photo.name, fh, "image/png")})
    return _check(r)


def send_document(token, chat, doc: Path, caption="", parse_mode="HTML", thread=None):
    """Gui anh dang FILE (sendDocument). Khac sendPhoto: Telegram GIU NGUYEN file
    goc — khong ha ve 1280px, khong nen lai JPEG. Dung khi can giu do net (vd
    frame HD cua Bob). Anh van hien thumbnail; bam vao xem/tai full-res."""
    caption = don_dep(caption)
    if len(caption) > CAPTION_LIMIT:
        # Exception thuong, KHONG sys.exit: day la ham thu vien — xem TelegramTuChoi.
        raise TelegramTuChoi(
            f"Caption {len(caption)} ky tu, vuot gioi han {CAPTION_LIMIT} "
            f"cua Telegram. Rut ngan hoac tach thanh tin rieng.")
    with httpx.Client(timeout=120) as c, doc.open("rb") as fh:
        r = c.post(API.format(token=token, method="sendDocument"),
                   data={"chat_id": chat, "caption": caption,
                         "parse_mode": parse_mode,
                         **({"message_thread_id": str(int(thread))} if thread else {})},
                   files={"document": (doc.name, fh, "image/png")})
    return _check(r)


def send_media_group(token, chat, media, caption="", parse_mode="HTML",
                     thread=None):
    """Gui album nhieu anh. `media` la danh sach URL (http...) hoac Path cuc bo.

    Chu thich chi gan vao anh DAU TIEN — dung quy tac cua Telegram cho album.
    """
    caption = don_dep(caption)
    if len(caption) > CAPTION_LIMIT:
        # Exception thuong, KHONG sys.exit: day la ham thu vien — xem TelegramTuChoi.
        raise TelegramTuChoi(
            f"Caption {len(caption)} ky tu, vuot gioi han {CAPTION_LIMIT} "
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
    data = {"chat_id": chat, "media": json.dumps(items)}
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


def gui_topic(text: str, vai: str) -> bool:
    """Gui `text` (HTML) vao topic cua `vai` trong group cua brand. Thieu token/
    group thi in ra man hinh; loi Telegram thi in canh bao — KHONG nem, vi day la
    ham cua script cron (usage_audit, model_watch, theo_doi_9router).
    Truoc 05/09/2026 sau tep tu viet lai doan nay moi tep mot kieu."""
    env_load.nap()
    tok = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat = os.environ.get("TELEGRAM_GROUP_ID") or os.environ.get("TELEGRAM_CHANNEL_ID")
    if not (tok and chat):
        print("[canh bao] thieu TELEGRAM_BOT_TOKEN/GROUP_ID — in ra man hinh thay vi gui")
        print(text)
        return False
    try:
        send_text(tok, chat, text, thread=env_load.topics().get(vai))
        return True
    except Exception as e:                                   # noqa: BLE001
        print(f"[canh bao] khong gui duoc Telegram: {type(e).__name__}: {e}")
        return False


def main():
    try:
        return _main()
    except TelegramTuChoi as e:
        sys.exit(str(e))


def _main():
    p = argparse.ArgumentParser(description="Dang bai len Telegram channel")
    p.add_argument("--photo", type=Path, help="Duong dan anh (sendPhoto — Telegram nen)")
    p.add_argument("--document", type=Path,
                   help="Gui anh dang FILE (sendDocument) — giu nguyen do net, "
                        "Telegram khong ha 1280 khong nen. Dung cho frame HD.")
    p.add_argument("--caption", default="", help="Chu thich anh (toi da 1024)")
    p.add_argument("--text", help="Dang tin chi co chu")
    p.add_argument("--to", help="Ghi de chat_id dich")
    p.add_argument("--to-env", dest="to_env",
                   help="Lay chat_id tu bien moi truong nay (vd TELEGRAM_GROUP_ID). "
                        "Cho phep goi bang MOT lenh tuyet doi, khong can $(...) — "
                        "hop de dua vao command_allowlist.")
    p.add_argument("--thread", help="message_thread_id (topic) trong group")
    p.add_argument("--thread-name", dest="thread_name",
                   help="Ten topic trong state/topics.json (vd bob) — tu giai ra "
                        "thread id, khoi phai --thread $(...).")
    p.add_argument("--file", type=Path, help="Doc noi dung tu file")
    p.add_argument("--album", nargs="+",
                   help="Gui nhieu anh (URL hoac duong dan cuc bo) thanh 1 album")
    p.add_argument("--luu-mid", dest="luu_mid", type=Path,
                   help="Ghi {message_id, ts} cua tin vua gui vao tep JSON nay — "
                        "de noi goi (vd bao cao danh so) sau do doi chieu REPLY "
                        "dung vao tin nao, khong phai tin bat ky trong topic.")
    a = p.parse_args()

    token, chat = load_secrets()
    chat = a.to or (os.environ.get(a.to_env) if a.to_env else None) or chat
    if not chat:
        sys.exit("Thieu chat_id: dung --to, --to-env VAR, hoac TELEGRAM_CHANNEL_ID")

    # Giai thread tu ten topic (paths tuyet doi theo vi tri file, khong theo cwd).
    thread = a.thread
    if a.thread_name:
        topics_path = env_load.topics_path()
        try:
            topics = json.loads(topics_path.read_text(encoding="utf-8"))
        except Exception as e:
            sys.exit(f"Khong doc duoc {topics_path}: {e}")
        if a.thread_name not in topics:
            sys.exit(f"Topic {a.thread_name!r} khong co trong {topics_path}")
        thread = topics[a.thread_name]

    body = a.file.read_text(encoding="utf-8") if a.file else None

    if a.album:
        res = send_media_group(token, chat, a.album, body or a.caption, thread=thread)
    elif a.document:
        res = send_document(token, chat, a.document, body or a.caption, thread=thread)
    elif a.photo:
        res = send_photo(token, chat, a.photo, body or a.caption, thread=thread)
    else:
        text = body or a.text
        if not text:
            sys.exit("Can --text, --file hoac --photo")
        res = send_text(token, chat, text, thread=thread)
    print(f"da dang | message_id={res.get('message_id')} chat={chat}")
    if a.luu_mid:
        # Best-effort: khong luu duoc mid khong duoc lam hong viec da dang xong.
        try:
            a.luu_mid.parent.mkdir(parents=True, exist_ok=True)
            a.luu_mid.write_text(
                json.dumps({"message_id": res.get("message_id"), "ts": time.time()},
                          ensure_ascii=False), encoding="utf-8")
        except OSError as e:
            print(f"[canh bao] khong ghi duoc --luu-mid {a.luu_mid}: {e}")


if __name__ == "__main__":
    main()
