#!/usr/bin/env python3
"""receive_number.py — so thu tu "#NN" cua tin "📥 <Vai> đã nhận task" (LOW-424).

Ong Chu 30/09/2026: nhieu task ve cung luc (10 tin Dre lien tiep) thi khong dem
nhanh duoc da nhan bao nhieu viec. Moi vai dem RIENG, reset moi ngay (gio VN);
cung mot task id goi lai (retry) giu NGUYEN so cu.

State: state/<brand>/receive_number.json
    {"date": "2026-09-30", "roles": {"dre": {"last": 3, "tasks": {"t_1": 1, ...}}}}
Ghi nguyen tu (env_load.write_json) duoi flock, nen hai tien trinh approve cung
goi khong cap trung so. Loi doc/ghi KHONG duoc chan tin bao: nguoi goi bat loi va
gui tin khong co so.
"""
import fcntl
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import env_load
import state_paths

VN = timezone(timedelta(hours=7))   # gio VN, khong DST (cung quy uoc approve_dispatch.VN)


def next_number(state: Path, role: str, task_id: str, now: datetime = None) -> int:
    """So thu tu (bat dau tu 1) cua `task_id` trong ngay VN hien tai cua vai `role`."""
    state = Path(state)
    state.mkdir(parents=True, exist_ok=True)
    date = (now or datetime.now(VN)).astimezone(VN).strftime("%Y-%m-%d")
    path = state / state_paths.RECEIVE_NUMBER_FILE
    with open(state / state_paths.RECEIVE_NUMBER_LOCK, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        if not isinstance(data, dict) or data.get("date") != date:
            data = {"date": date, "roles": {}}        # sang ngay moi: dem lai tu #01
        entry = data.setdefault("roles", {}).setdefault(role, {"last": 0, "tasks": {}})
        number = entry["tasks"].get(task_id)
        if number is None:
            number = entry["last"] + 1
            entry["last"] = number
            entry["tasks"][task_id] = number
            env_load.write_json(path, data)
        return number


def label(number: int) -> str:
    """`#01`…`#99`, tu 100 tro di in du (`#100`)."""
    return f"#{number:02d}"
