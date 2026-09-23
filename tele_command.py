#!/usr/bin/env python3
"""Dang ky LENH SLASH cua bot duyet bai voi Telegram (menu "/" trong khung chat).

Vi sao can: `approve_command.py` hieu `/bai /vai /auto /hd`, nhung Telegram khong
tu biet — go "/" trong nhom chi hien nhung lenh DA DANG KY. Truoc tep nay, bon
lenh do la tri thuc truyen mieng: khong go dung chu thi khong ai nhac.

CAN THAN — `setMyCommands` THAY CA DANH SACH, khong phai them vao:
  Bot cua moi brand (@hermesdcmodebot / @hermesmodebot) dang mang ~62 lenh cua
  nen tang Hermes (`/new`, `/kanban`, `/model`...). Goi thang `setMyCommands` voi
  bon lenh cua minh la XOA SACH 62 cai kia khoi menu. Nen tep nay LUON doc danh
  sach dang co (`getMyCommands`), ghep lenh cua minh vao, roi moi gui len.

Va vi the no phai chay lai duoc nhieu lan: Hermes co the dang ky lai danh sach
cua no khi gateway khoi dong, de len phan cua ta. Chay lai la xong, khong can
don dep gi (idempotent: lenh trung `command` thi cap nhat mo ta, khong nhan doi).

Dung:
    venv/bin/python tele_command.py            # dang ky cho brand cua container
    venv/bin/python tele_command.py --xem      # chi xem, khong ghi
"""
import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402

import httpx                                                  # noqa: E402

# Mo ta hien trong menu "/" cua Telegram. Toi da 256 ky tu moi dong (gioi han cua
# Bot API) — cau chu o day la CHU THICH DUY NHAT Ong Chu doc luc dang go lenh,
# nen no phai tra loi duoc "lenh nay lam gi, va no an toi dau".
COMMANDS = [
    ("bai", "Đặt bài tay từ URL: /bai <url> <vai> — vai nhận: ethan (thẻ bìa), dre "
            "(carousel ảnh thật), kite (carousel vector). Tạo cặp task ảnh + viết, "
            "không qua vòng quét."),
    ("auto", "Bật/tắt TỰ DUYỆT bản nháp — chỉ cho brand của NHÓM NÀY, nhóm brand kia "
             "phải gõ riêng. /auto on|off, gõ trần để xem trạng thái. Bật thì thẻ nháp "
             "im lặng 20 phút là tự xếp lịch đăng (bấm ⛔ Giữ lại để chặn); 25% số bài "
             "vẫn phải bấm tay; tự tắt sau 24h."),
    ("vai", "Bảng vai trong container này: ai dựng ảnh kiểu gì, ai viết caption."),
    ("hd", "Danh sách lệnh của bot duyệt bài (kèm cú pháp)."),
]
API = "https://api.telegram.org/bot{}/{}"


def _token() -> str:
    env_load.load()
    t = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not t:
        sys.exit("Thieu TELEGRAM_BOT_TOKEN trong secret.<brand>.env")
    return t


def read_current(token: str) -> list:
    r = httpx.get(API.format(token, "getMyCommands"), timeout=30).json()
    if not r.get("ok"):
        sys.exit(f"getMyCommands hong: {r}")
    return r.get("result") or []


def merge(current: list, moi=COMMANDS) -> list:
    """Ghep lenh cua ta vao danh sach dang co. Lenh trung ten thi CAP NHAT mo ta
    (de sua cau chu ma khong sinh ban trung), con lai giu nguyen thu tu cu."""
    theo_ten = {c.get("command"): dict(c) for c in current}
    ra = [dict(c) for c in current]
    for ten, mo_ta in moi:
        if ten in theo_ten:
            for c in ra:
                if c.get("command") == ten:
                    c["description"] = mo_ta
        else:
            ra.append({"command": ten, "description": mo_ta})
    return ra


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--xem", action="store_true", help="chi in danh sach sau khi ghep, khong gui")
    a = p.parse_args()
    token = _token()
    dang_co = read_current(token)
    sau = merge(dang_co)
    cua_ta = {ten for ten, _ in COMMANDS}
    print(f"dang co {len(dang_co)} lenh; sau khi ghep: {len(sau)} "
          f"(cua bot duyet: {', '.join('/' + t for t in cua_ta)})")
    for c in sau:
        if c["command"] in cua_ta:
            print(f"  /{c['command']}: {c['description'][:70]}…")
    if a.xem:
        return
    r = httpx.post(API.format(token, "setMyCommands"), json={"commands": sau}, timeout=30).json()
    if not r.get("ok"):
        sys.exit(f"setMyCommands hong: {r}")
    print(f"da dang ky {len(sau)} lenh cho brand {os.environ.get('CT_BRAND', '?')}")


if __name__ == "__main__":
    main()
