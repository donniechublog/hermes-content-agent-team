#!/usr/bin/env python3
"""Layer 3b of the skill-lesson gate (LOW-154): the boss's Duyệt/Từ chối
buttons on a flagged lesson. `approve_post.handle_callback` already checked
`is_boss(cq)` before this module ever runs, so these tests start from "the
boss pressed a button" — they cover the button's own logic: idempotent
decisions, a message that no longer exists, and a callback payload a
Telegram client could forge.

Run:  venv/bin/python tests/test_skill_lesson_approve.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import skill_lesson_approve as sla                                    # noqa: E402

KEY = "blog__kite__eb4b1c1f"


def _verdict(tmp: Path, **extra) -> Path:
    verdicts = tmp / "verdicts"
    verdicts.mkdir(parents=True, exist_ok=True)
    path = verdicts / f"{KEY}.json"
    path.write_text(json.dumps({"id": "eb4b1c1f", "brand": "blog", "profile": "kite",
                                "skill": "carousel-edu", "verdict": "flagged", **extra},
                               ensure_ascii=False), encoding="utf-8")
    return path


def _cq(*, with_message=True):
    cq = {"id": "cbq1", "data": f"skillok:{KEY}"}
    if with_message:
        cq["message"] = {
            "chat": {"id": -100}, "message_id": 55, "text": "🧪 Bài học skill cần duyệt",
            "reply_markup": {"inline_keyboard": [[
                {"text": "✅ Nhận", "callback_data": f"skillok:{KEY}"},
                {"text": "❌ Từ chối", "callback_data": f"skillno:{KEY}"},
            ]]},
        }
    return cq


def test_approve_records_decision_and_edits_message():
    with tempfile.TemporaryDirectory() as t:
        state = Path(t)
        path = _verdict(state)
        calls = []
        sla.handle_button("tok", "skillok", KEY, _cq(), call=lambda tok, method, **kw: calls.append((method, kw)),
                          state=state)
        verdict = json.loads(path.read_text(encoding="utf-8"))
    assert verdict["boss_decision"] == "approved" and "boss_decision_at" in verdict
    methods = [m for m, _ in calls]
    assert methods == ["answerCallbackQuery", "editMessageText"]
    edit_kw = calls[1][1]
    assert edit_kw["chat_id"] == -100 and edit_kw["message_id"] == 55
    assert "Đã NHẬN" in edit_kw["text"]
    assert edit_kw["reply_markup"]["inline_keyboard"] == [], "the resolved lesson's row must be removed"


def test_reject_records_decision():
    with tempfile.TemporaryDirectory() as t:
        state = Path(t)
        path = _verdict(state)
        calls = []
        cq = _cq()
        cq["data"] = f"skillno:{KEY}"
        sla.handle_button("tok", "skillno", KEY, cq, call=lambda tok, method, **kw: calls.append((method, kw)),
                          state=state)
        verdict = json.loads(path.read_text(encoding="utf-8"))
    assert verdict["boss_decision"] == "rejected"
    assert "Đã TỪ CHỐI" in calls[1][1]["text"]


def test_pressing_an_already_decided_button_does_not_change_the_decision():
    with tempfile.TemporaryDirectory() as t:
        state = Path(t)
        path = _verdict(state, boss_decision="approved", boss_decision_at=123)
        calls = []
        sla.handle_button("tok", "skillno", KEY, _cq(), call=lambda tok, method, **kw: calls.append((method, kw)),
                          state=state)
        verdict = json.loads(path.read_text(encoding="utf-8"))
    assert verdict["boss_decision"] == "approved" and verdict["boss_decision_at"] == 123, \
        "a repeat click must never flip an already-recorded decision"
    toast = calls[0][1]["text"]
    assert "đã được xử lý" in toast or "approved" in toast


def test_unknown_key_answers_alert_without_crashing():
    with tempfile.TemporaryDirectory() as t:
        calls = []
        sla.handle_button("tok", "skillok", "blog__kite__no-such-id", _cq(),
                          call=lambda tok, method, **kw: calls.append((method, kw)), state=Path(t))
    assert calls == [("answerCallbackQuery", {"callback_query_id": "cbq1",
                                              "text": "Không tìm thấy bài học này (đã xử lý ở lượt khác?)",
                                              "show_alert": True})]


def test_forged_key_is_rejected_without_touching_the_filesystem():
    """callback_data comes straight from a Telegram client — must not let
    '../..' or an absolute path escape state/skill_lessons/verdicts/."""
    with tempfile.TemporaryDirectory() as t:
        state = Path(t)
        _verdict(state)
        calls = []
        for bad_key in ("../../../etc/passwd", "/etc/passwd", "blog__kite__eb4b1c1f/../secret"):
            sla.handle_button("tok", "skillok", bad_key, _cq(),
                              call=lambda tok, method, **kw: calls.append((method, kw)), state=state)
    assert all(c[0] == "answerCallbackQuery" and c[1]["show_alert"] for c in calls)
    assert len(calls) == 3


def test_flagged_only_verdict_is_never_touched_by_something_else():
    """Only 'flagged' verdicts are decidable — an accepted one reaching this
    module (a stale button on an old message, say) must be refused."""
    with tempfile.TemporaryDirectory() as t:
        state = Path(t)
        path = _verdict(state, **{"verdict": "accepted"})
        calls = []
        sla.handle_button("tok", "skillok", KEY, _cq(), call=lambda tok, method, **kw: calls.append((method, kw)),
                          state=state)
        verdict = json.loads(path.read_text(encoding="utf-8"))
    assert "boss_decision" not in verdict
    assert calls[0][1]["text"] == "Bài này không ở trạng thái chờ duyệt."


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
