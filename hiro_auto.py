#!/usr/bin/env python3
"""CONG TAC Hiro tu dung ban tin khi researcher nop bao cao (LOW-406).

Ong Chu 25/09/2026: `/hiro on` bat, `/hiro off` tat; bat ma bao cao tren 10 tin thi *"cu
lay 10 tin dau tien"* (hiro_pick.first_items_command). Co nam tren dia THEO BRAND
(`state/<brand>/hiro_auto.json`), doc boi scan_submit ngay sau khi bao cao chinh da len
topic — code bam thay, khong phai mot cau noi voi vai (cung ly do voi `auto_handoff`).

KHAC `auto_handoff`: co KHONG tu het han. `/auto` la quyen tu duyet THAY nguoi nen phai tu
tat; con day chi la cong tac dung ban nhap — bo Hiro van qua nut Duyet cua Ong Chu nhu thuong.
"""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402
import state_paths                                           # noqa: E402

VN = timezone(timedelta(hours=7))


def _path() -> Path:
    return env_load.state_dir() / state_paths.HIRO_AUTO_FILE


def _read() -> dict:
    try:
        return json.loads(_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def is_on() -> bool:
    return bool(_read().get("on"))


def set_on(on: bool, by=None) -> None:
    p = _path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps({"on": bool(on), "by": by, "at": datetime.now(VN).isoformat(timespec="seconds")},
                            ensure_ascii=False), encoding="utf-8")


def status_line() -> str:
    """Mot dong tra loi `/hiro` — chi cho brand cua NHOM nay (co theo brand)."""
    import hiro_pick                                         # tre: hiro_pick keo approve_*
    d = _read()
    n = hiro_pick.MAX_SLIDES
    if d.get("on"):
        luc = str(d.get("at") or "")[:16].replace("T", " ")
        return (f"🤖 Hiro tự động: <b>BẬT</b>{f' (từ {luc})' if luc else ''} — mỗi báo cáo researcher "
                f"tự dựng bản tin vắn; trên {n} tin thì lấy {n} tin đầu. Bộ vẫn qua nút Duyệt. "
                "<code>/hiro off</code> để tắt.")
    return ("Hiro tự động: <b>TẮT</b> — reply <code>Hiro</code> (hoặc <code>Hiro /3,5</code>) vào báo cáo "
            "để dựng tay. <code>/hiro on</code> để bật.")
