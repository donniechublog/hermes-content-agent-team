#!/usr/bin/env python3
"""Layer 3b of the skill-lesson gate (LOW-154): the boss's Duyệt/Từ chối
buttons on a flagged lesson (from skill_lesson_filter.py, LOW-119).

`approve_post.handle_callback` already checks `is_boss(cq)` before dispatching
any button, so `handle_button` here does not repeat that check. It only
records the decision on the verdict file; `skill_lesson_commit.py` (LOW-120)
is the one that actually applies/PRs an approved lesson or discards a rejected
one on its next cron run — this module never touches the pending record or
opens a PR itself.
"""
import json
import re
import time
from pathlib import Path

import env_load
from approve_base import call as default_call

STATE = env_load.ROOT / "state" / "skill_lessons"
SAFE_KEY = re.compile(r"^[a-z0-9]+__[a-z0-9]+__[a-z0-9]+$")

DECISION_NOTE = {"approved": "✅ Đã NHẬN — chờ tạo PR (skill_lesson_commit)",
                 "rejected": "❌ Đã TỪ CHỐI — bài học sẽ không vào repo"}


def verdict_path(key: str, state=STATE) -> Path | None:
    """The verdict file for `key` (a Telegram-supplied callback payload — never
    trust it as a bare filename), or None if `key` doesn't look like one of our
    own `<brand>__<profile>__<id>` names or the file doesn't exist."""
    if not SAFE_KEY.match(key):
        return None
    path = Path(state) / "verdicts" / f"{key}.json"
    return path if path.is_file() else None


def decide(path: Path, decision: str, *, now=None) -> tuple:
    """Record the boss's decision on a verdict, once. Returns (verdict, already)
    — `already` is True when a decision was already recorded (a repeat click on
    an old message), in which case nothing is changed."""
    verdict = json.loads(path.read_text(encoding="utf-8"))
    if verdict.get("boss_decision"):
        return verdict, True
    verdict["boss_decision"] = decision
    verdict["boss_decision_at"] = now if now is not None else time.time()
    env_load.write_json(path, verdict)
    return verdict, False


def _drop_row(inline_keyboard: list, key: str) -> list:
    """Remove the row whose buttons reference `key` — the other lessons batched
    into earlier design iterations, if any old message still has them, keep
    working buttons for whichever lesson wasn't just decided."""
    return [row for row in inline_keyboard
            if not any(key in (btn.get("callback_data") or "") for btn in row)]


def handle_button(token, action: str, key: str, cq, *, call=None, state=STATE) -> None:
    """action is 'skillok' or 'skillno'; key is the callback payload after ':'."""
    call = call or default_call
    path = verdict_path(key, state)
    if path is None:
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Không tìm thấy bài học này (đã xử lý ở lượt khác?)", show_alert=True)
        return
    verdict = json.loads(path.read_text(encoding="utf-8"))
    if verdict.get("verdict") != "flagged":
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Bài này không ở trạng thái chờ duyệt.", show_alert=True)
        return

    decision = "approved" if action == "skillok" else "rejected"
    verdict, already = decide(path, decision)
    msg = cq.get("message") or {}
    toast = ("Bài này đã được xử lý trước đó (" + verdict["boss_decision"] + ")"
             if already else ("Đã nhận, sẽ tạo PR ở lượt cron tới." if decision == "approved" else "Đã từ chối."))
    call(token, "answerCallbackQuery", callback_query_id=cq["id"], text=toast)

    chat_id, message_id = (msg.get("chat") or {}).get("id"), msg.get("message_id")
    if not (chat_id and message_id):
        return
    rows = ((msg.get("reply_markup") or {}).get("inline_keyboard") or [])
    new_text = (msg.get("text") or "") + ("" if already else "\n\n" + DECISION_NOTE[verdict["boss_decision"]])
    call(token, "editMessageText", chat_id=chat_id, message_id=message_id, text=new_text,
        parse_mode="HTML", reply_markup={"inline_keyboard": _drop_row(rows, key)})
