#!/usr/bin/env python3
"""Gui anh (mot hoac nhieu — sendPhoto/sendMediaGroup) vao dung topic Telegram
cua mot vai, va ghi lai nhat ky (message_id, file, mo ta) de sau nay tra loi
mot yeu cau sua con biet dang noi anh nao.

Dung cho MOI vai dung anh (slug: designer, carousel, gin, itachi...) de
tu day anh minh vua dung ra topic cua chinh minh — khong phai cho writer viet
xong roi moi co anh trong bai. Gin/Itachi con duoc goi tu `--gui <vai>` trong
tao_nen_ai.py, no goi thang ham post() o day.

Khong dung chung tien trinh voi approve_service.py (dich vu duyet bai) — day
la mot lenh CHAY MOT LAN, khong long-poll, khong dung chung offset Telegram
voi dich vu kia. An toan goi bao nhieu lan cung duoc.

Dung:
    venv/bin/python gui_telegram.py --vai itachi \\
      --anh a.png --anh b.png --mo-ta "Doraemon bat tay Conan, lang La"
    venv/bin/python gui_telegram.py --vai itachi --list      # gan day da gui gi
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load

ROOT = Path.home() / "content-team"
STATE = env_load.state_dir() / "telegram_sent"
TOPICS = env_load.topics_path()
API = "https://api.telegram.org/bot{token}/{method}"


def _topic(vai: str) -> int:
    m = json.loads(TOPICS.read_text(encoding="utf-8"))
    if vai not in m:
        raise SystemExit(f"Vai '{vai}' chua co topic trong {TOPICS}")
    return m[vai]


def _ghi_nhat_ky(vai: str, message_id, files, mo_ta: str) -> None:
    STATE.mkdir(parents=True, exist_ok=True)
    dong = {"ts": int(time.time()), "message_id": message_id,
            "files": [str(f) for f in files], "mo_ta": mo_ta}
    with (STATE / f"{vai}.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dong, ensure_ascii=False) + "\n")


def _kb_duyet(draft_id: str) -> dict:
    """Ba nut cho tam anh (approve_service xu ly callback):
      imgok   Duyet   -> sinh task viet caption.
      imgredo Lam lai -> tao lai task anh, designer dung anh khac.
      imgno   Bo han   -> giet tin, khong viet khong lam lai."""
    return {"inline_keyboard": [
        [{"text": "✅ Duyệt ảnh → viết caption", "callback_data": "imgok:" + draft_id}],
        [{"text": "🔄 Làm lại", "callback_data": "imgredo:" + draft_id},
         {"text": "🗑 Bỏ hẳn", "callback_data": "imgno:" + draft_id}],
    ]}


def post(vai: str, files, mo_ta: str = "", reply_to=None, duyet=None) -> dict:
    """Gui 1 hoac nhieu anh (>1 tu dong thanh album) vao topic cua `vai`.

    `reply_to` (message_id, tuy chon): gui thanh REPLY vao dung tin nhan yeu
    cau — dung khi tra ket qua cho mot yeu cau sua cu the, de Ong Chu thay
    ngay ket qua nam duoi dung cau hoi cua minh thay vi mot tin roi o cuoi
    topic. Bo trong thi gui binh thuong (khong reply ai).

    Tra ve response Telegram (list ket qua neu la album, dict neu mot anh).
    Luon ghi nhat ky sau khi gui thanh cong, de `--list` doc lai duoc.
    """
    env_load.nap()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    group = os.environ.get("TELEGRAM_GROUP_ID")
    if not token or not group:
        raise SystemExit("Thieu TELEGRAM_BOT_TOKEN/TELEGRAM_GROUP_ID trong .secrets.env")
    thread_id = _topic(vai)

    files = [Path(f) for f in files]
    thieu = [f for f in files if not f.exists()]
    if thieu:
        raise SystemExit(f"Khong thay file: {', '.join(str(f) for f in thieu)}")
    if len(files) > 10:
        raise SystemExit("Toi da 10 anh mot album (gioi han Telegram).")

    if len(files) == 1:
        with httpx.Client(timeout=120) as c, open(files[0], "rb") as fh:
            data = {"chat_id": group, "message_thread_id": str(int(thread_id))}
            if mo_ta:
                data["caption"] = mo_ta[:1024]
            if reply_to:
                data["reply_to_message_id"] = str(int(reply_to))
            r = c.post(API.format(token=token, method="sendPhoto"), data=data,
                       files={"photo": (files[0].name, fh, "image/png")})
        res = r.json()
    else:
        items, filemap = [], {}
        for i, f in enumerate(files):
            key = f"file{i}"
            e = {"type": "photo", "media": f"attach://{key}"}
            if i == 0 and mo_ta:
                e["caption"] = mo_ta[:1024]
            items.append(e)
            filemap[key] = open(f, "rb")
        data = {"chat_id": group, "message_thread_id": str(int(thread_id)),
                "media": json.dumps(items)}
        if reply_to:
            data["reply_to_message_id"] = str(int(reply_to))
        try:
            with httpx.Client(timeout=180) as c:
                r = c.post(API.format(token=token, method="sendMediaGroup"),
                           data=data, files=filemap)
        finally:
            for fh in filemap.values():
                fh.close()
        res = r.json()

    if not res.get("ok"):
        raise SystemExit(f"Gui Telegram loi: {res.get('description')}")

    result = res["result"]
    last = result[-1] if isinstance(result, list) else result
    _ghi_nhat_ky(vai, last.get("message_id"), files, mo_ta)

    # Album KHONG gan duoc nut (gioi han Bot API), nen nut Duyet luon nam tren
    # mot tin nhan chu RIENG ngay duoi anh — dung cho ca anh don lan album.
    if duyet:
        with httpx.Client(timeout=60) as c:
            c.post(API.format(token=token, method="sendMessage"), data={
                "chat_id": group, "message_thread_id": str(int(thread_id)),
                "text": ("Ảnh đã xong. Duyệt để người viết làm caption, "
                         "hoặc bỏ nếu ảnh chưa đạt."),
                "reply_markup": json.dumps(_kb_duyet(duyet)),
            })
    return res


def gan_day(vai: str, n: int = 5) -> list:
    p = STATE / f"{vai}.jsonl"
    if not p.exists():
        return []
    dong = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    return dong[-n:]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vai", required=True,
                    help="slug vai — khop key trong topics.<brand>.json")
    ap.add_argument("--anh", action="append", default=[], help="Duong dan PNG, lap lai cho nhieu anh (album)")
    ap.add_argument("--mo-ta", default="", help="Caption ngan mo ta anh — giup tra loi SAU biet dang noi anh nao")
    ap.add_argument("--reply-to", type=int, default=None,
                    help="message_id can reply — ket qua sua theo yeu cau thi reply DUNG tin da yeu cau, "
                         "khong gui roi o cuoi topic")
    ap.add_argument("--duyet", default=None, metavar="DRAFT_ID",
                    help="Gan nut Duyet/Bo cho tam anh (draft_id). Bam Duyet thi "
                         "approve_service moi sinh task viet caption; khong co co "
                         "nay thi chi day anh, khong hoi duyet (dung cho chat le).")
    ap.add_argument("--list", action="store_true", help="In cac lan gui gan day (mac dinh 5) thay vi gui moi")
    a = ap.parse_args()

    if a.list:
        for d in gan_day(a.vai):
            print(json.dumps(d, ensure_ascii=False))
        return

    if not a.anh:
        ap.error("--anh la bat buoc (tru khi dung --list)")
    res = post(a.vai, a.anh, a.mo_ta, reply_to=a.reply_to, duyet=a.duyet)
    result = res["result"]
    mid = result[-1]["message_id"] if isinstance(result, list) else result["message_id"]
    print(f"da gui {len(a.anh)} anh vao topic '{a.vai}', message_id={mid}")


if __name__ == "__main__":
    main()
