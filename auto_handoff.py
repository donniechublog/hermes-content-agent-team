#!/usr/bin/env python3
"""CONG TAC TU CHUYEN VIEC giua hai chang (LOW-382/LOW-373).

Mot cong = mot cho ma hom nay Ong Chu phai bam de viec di tiep. Bat cong tac
thi CODE bam thay, khong phai vai LLM tu quyet: cong tac la mot co tren dia,
doc boi `approve_service`, chu khong phai mot cau noi voi agent. Vi sao: vai
khong cam cong tac (moi viec giao task deu do approve_service lam), va trang
thai nam trong bo nho agent thi reset theo phien — bat hom nay, mai im lang tat.

Cong dau tien: `draft_to_publish` — the ban nhap len topic, im lang qua
`HOLD_WINDOW_MIN` phut thi TU XEP LICH DANG. Do tren approve.log 18-22/09/2026:
98/100 lan bam o cong nay la "duyet", 2 lan bo — tuc cai Ong Chu lam o day gan
nhu luon la "ok, di tiep". Doi thanh IM LANG LA DONG Y thi tai cua nguoi ti le
voi SO BAI CO VAN DE (2%), khong phai tong so bai.

Ba rao, deu do chinh cho nay (khong rao nao nam trong tay vai):
  - `AUTO_HOURS`  — chi tu xep lich trong khung gio Ong Chu con thuc de phu
                    quyet. Im lang luc 3h sang khong phai la dong y, do la ngu.
  - `SAMPLE_PERCENT` — mot phan so bai VAN phai bam tay, chon tat dinh theo
                    draft_id. Khong co mau thi auto chay mu: sau vai thang
                    khong ai biet chat luong tut tu bao gio.
  - `pause_today` — mot lan "Giu lai" la phan con lai cua ngay ve bam tay. Mot
                    bai sai thuong khong di mot minh.

Co tu het han (`expires_at`, mac dinh `DEFAULT_HOURS`): bat nham khong tro
thanh trang thai vinh vien.
"""
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402
import state_paths                                           # noqa: E402

VN = timezone(timedelta(hours=7))          # cung quy uoc voi approve_post/journal

# Cong dang co. Them cong moi = them mot dong o day + mot cho goi `is_on`.
GATE_DRAFT_TO_PUBLISH = "draft_to_publish"
GATES = (GATE_DRAFT_TO_PUBLISH,)

# Bao lau sau khi the len topic thi coi la "khong ai phan doi". 20 phut: du de
# Ong Chu doc mot bai tren dien thoai, ma khong giu bai lai ca buoi.
HOLD_WINDOW_MIN = int(os.environ.get("CT_HOLD_WINDOW_MIN", "20") or 20)
# Khung gio (gio VN) duoc tu xep lich. Ngoai khung thi bai NAM CHO, tick sang
# hom sau don — dung y "tin khong tha trong ngay thi de sang hom sau".
AUTO_HOURS = (7, 23)
# Bao nhieu phan tram bai VAN phai bam tay. 25% ~ 3 bai/ngay o ngan sach 12
# bai/org/ngay. Chon theo bam draft_id (khong phai random()): tick chay lai
# nhieu lan phai ra cung mot cau tra loi, khong thi mot bai "may rui" duoc auto
# o lan tick thu hai.
SAMPLE_PERCENT = int(os.environ.get("CT_SAMPLE_PERCENT", "25") or 25)
DEFAULT_HOURS = 24                         # co tu tat sau ngan nay


def _path() -> Path:
    return env_load.state_dir() / state_paths.AUTO_HANDOFF_FILE


def _read() -> dict:
    try:
        return json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def _write(d: dict) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def _today() -> str:
    return datetime.now(VN).strftime("%Y-%m-%d")


def set_gate(gate: str, on: bool, by=None, hours: int = DEFAULT_HOURS) -> dict:
    """Bat/tat mot cong. Tra ve ban ghi moi cua cong do."""
    d = _read()
    now = time.time()
    d[gate] = {"on": bool(on), "by": by, "at": now,
               "expires_at": (now + hours * 3600) if on else None}
    _write(d)
    return d[gate]


def pause_today(gate: str) -> None:
    """Ong Chu vua "Giu lai" mot bai -> phan con lai cua NGAY ve bam tay.

    Khong tat han co: sang mai cong lai chay, khong ai phai nho bat lai."""
    d = _read()
    rec = d.setdefault(gate, {"on": False})
    rec["paused_date"] = _today()
    _write(d)


def is_on(gate: str) -> tuple:
    """(dang bat khong, ly do neu khong). Het han thi TAT LUON tren dia."""
    rec = _read().get(gate) or {}
    if not rec.get("on"):
        return False, "chưa bật"
    het = rec.get("expires_at")
    if het and time.time() >= het:
        set_gate(gate, False)
        return False, "đã hết hạn — bật lại nếu vẫn muốn"
    if rec.get("paused_date") == _today():
        return False, "đã bấm Giữ lại hôm nay — phần còn lại của ngày bấm tay"
    return True, ""


def status_line(gate: str) -> str:
    """Mot dong cho Ong Chu doc trong Telegram."""
    on, ly_do = is_on(gate)
    rec = _read().get(gate) or {}
    if not on:
        return f"⛔ <b>{gate}</b>: tắt ({ly_do})"
    het = rec.get("expires_at")
    gio = datetime.fromtimestamp(int(het), VN).strftime("%H:%M %d/%m") if het else "không hạn"
    return (f"✅ <b>{gate}</b>: bật, hết hạn {gio} — im lặng {HOLD_WINDOW_MIN} phút là "
            f"tự xếp lịch đăng, {SAMPLE_PERCENT}% số bài vẫn phải bấm tay")


def in_auto_hours(now=None) -> bool:
    gio = datetime.fromtimestamp(now or time.time(), VN).hour
    return AUTO_HOURS[0] <= gio < AUTO_HOURS[1]


def must_review(draft_id: str) -> bool:
    """Bai nay co nam trong phan LAY MAU (bat buoc bam tay) khong.

    Tat dinh theo draft_id: cung mot bai thi moi lan hoi deu ra cung cau tra
    loi, nen tick chay lai khong bien mot bai mau thanh bai auto."""
    if SAMPLE_PERCENT <= 0:
        return False
    h = int(hashlib.sha1(draft_id.encode("utf-8")).hexdigest()[:8], 16)
    return (h % 100) < SAMPLE_PERCENT
