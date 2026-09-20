#!/usr/bin/env python3
"""LOW-311 — luoi doi chieu vet cho approve_chat: chat theo topic.

Ba thu module nay hua, va da tung vo that:
  - cong toolset: tin GO TROI chay voi bo cong cu chi doc (02/09/2026 Vera nhan
    "Hom nay ko lam viec ?" roi tu chay scan 10 phut); reply / anh / URL / vai
    chay-bang-chat thi day du.
  - hang doi hai tang: cung vai thi tin truoc tra loi truoc, khac vai thi song
    song toi CT_CHAT_PARALLEL — va Ong Chu LUON duoc bao dang cho gi.
  - khong im lang: agent loi, thread chet, Telegram tu choi tin dai... deu phai
    ra mot dong trong topic.

Chay:  python tests/test_trace_approve_chat.py
"""
import sys
import threading
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import approve_base as base            # noqa: E402
import approve_chat as chat            # noqa: E402
import approve_dispatch as dispatch    # noqa: E402
import chat_router                     # noqa: E402
import hermes_adapter                  # noqa: E402
from trace_harness import Harness, message, run_tests  # noqa: E402

VERA, GIN, GHOST = 77, 66, 99


def _harness(answer=("xin chào", None)):
    h = Harness(chat, base, dispatch)
    h.__enter__()
    h.topics({"vera": VERA, "gin": GIN})
    h.capture_logs()
    h.patch(chat_router, "profile_missing", lambda profile, home=None: False)
    h.patch(chat_router, "ask", h.spy("ask", returns=answer))
    h.patch(hermes_adapter, "has_kanban", lambda: False)
    # hang doi la bien cap module song qua cac test -> moi test mot bo moi
    h.patch(chat, "_HANG_PHIEN", {})
    h.patch(chat, "_DANG_CHAY", {})
    return h


def _chat(h, msg, thread=VERA):
    text = msg.get("text") or msg.get("caption") or ""
    chat.handle_chat(h.token, h.group, msg, thread, text)


def _asks(h):
    return [d for n, d in h.trace.of("fn") if n == "ask"]


# =========================================================================
# duong chinh + cong toolset
# =========================================================================
def test_bare_chat_runs_read_only_and_answer_lands_in_same_topic():
    h = _harness()
    try:
        _chat(h, message(1, "Hôm nay ko làm việc ?", thread=VERA))
        (a,) = _asks(h)
        assert a["args"] == ("vera", "tele-vera", "Hôm nay ko làm việc ?")
        assert a["kwargs"] == {"toolsets": chat_router.DROP_ONLY_READ}
        assert [k for k in h.trace.kinds() if not k.startswith("log:")] == [
            "tg:sendMessage", "fn:ask", "tg:sendMessage"]
        assert "Đang chuyển cho <b>vera</b>" in h.tg.texts()[0]
        assert h.tg.texts()[1] == "xin chào"
        assert all(d["message_thread_id"] == VERA for d in h.tg.sent())
    finally:
        h.__exit__()


def test_toolset_gate_full_tools_only_for_reply_image_url_or_chat_driven_role():
    h = _harness()
    try:
        cases = [
            (message(2, "làm lại đi", thread=VERA, reply_to=500), VERA, None),
            (message(3, "xem https://x.com/a/status/1", thread=VERA), VERA, None),
            (message(4, thread=VERA, caption="ảnh", photo=[{"file_id": "p"}]), VERA, None),
            (message(5, thread=VERA, caption="tệp",
                     document={"mime_type": "image/png"}), VERA, None),
            (message(6, thread=VERA, caption="pdf",
                     document={"mime_type": "application/pdf"}), VERA,
             chat_router.DROP_ONLY_READ),
            (message(7, "dịch ảnh vừa rồi", thread=GIN), GIN, None),
        ]
        for msg, thread, _ in cases:
            _chat(h, msg, thread)
        got = [a["kwargs"]["toolsets"] for a in _asks(h)]
        assert got == [c[2] for c in cases], got
    finally:
        h.__exit__()


def test_topic_without_profile_in_this_brand_explains_instead_of_calling_agent():
    """LOW-283: topic Vera ben blog chi de chon tin du — `-p vera` o blog chi ra loi."""
    h = _harness()
    try:
        h.patch(chat_router, "profile_missing", lambda profile, home=None: True)
        _chat(h, message(8, "chào", thread=VERA))
        assert _asks(h) == []
        (t,) = h.tg.texts()
        assert "không chạy ở brand này" in t and "Reply số" in t
    finally:
        h.__exit__()


def test_unknown_topic_falls_back_to_default_assistant_session():
    h = _harness()
    try:
        _chat(h, message(9, "ai đó?", thread=GHOST), GHOST)
        assert _asks(h)[0]["args"][:2] == (None, "tele-general")
        assert "trợ lý" in h.tg.texts()[0]
    finally:
        h.__exit__()


# =========================================================================
# khong im lang
# =========================================================================
def test_agent_error_is_shown_with_warning_sign():
    h = _harness(answer=(None, "HTTP 429 quota"))
    try:
        _chat(h, message(10, "x", thread=VERA))
        assert h.tg.texts()[-1] == "⚠️ HTTP 429 quota"
    finally:
        h.__exit__()


def test_agent_thread_crash_still_answers():
    h = _harness()
    try:
        def _boom(*a, **kw):
            raise RuntimeError("agent no")
        h.patch(chat_router, "ask", _boom)
        h.patch(threading, "excepthook", lambda args: None)      # khong in traceback ra test
        _chat(h, message(11, "x", thread=VERA))
        assert "Không nhận được kết quả từ agent" in h.tg.texts()[-1]
        assert chat._DANG_CHAY == {}, "vai phai roi bang dang-chay ke ca khi hong"
    finally:
        h.__exit__()


def test_long_answer_is_split_in_order_and_refused_chunk_gets_short_fallback():
    h = _harness(answer=("A" * 4000 + "\n" + "B" * 4000, None))
    try:
        h.tg.script("sendMessage",
                    {"ok": True, "result": {"message_id": 1}},          # "Dang chuyen"
                    {"ok": True, "result": {"message_id": 2}},          # manh A
                    {"ok": False, "description": "can't parse entities"})  # manh B bi tu choi
        _chat(h, message(12, "kể dài", thread=VERA))
        texts = h.tg.texts()
        assert len(texts) == 4, [t[:30] for t in texts]
        assert set(texts[1]) <= {"A", "\n"} and texts[2].lstrip("\n").startswith("B")
        assert texts[3].startswith("⚠️ Không gửi được trả lời gốc (can't parse entities)")
        assert len(texts[3]) < 1700
    finally:
        h.__exit__()


class _SlowThread:
    """Thread gia: `is_alive` tra True `beats` lan (moi `join` day dong ho 130s)
    roi moi chay target — gia mot agent chay lau ma test khong phai doi."""

    def __init__(self, clock, beats, target, daemon=None):
        self.clock, self.beats, self.target = clock, beats, target

    def start(self):
        pass

    def is_alive(self):
        if self.beats:
            self.beats -= 1
            return True
        if self.target:
            self.target()
            self.target = None
        return False

    def join(self, timeout=None):
        self.clock.advance(130)


def test_progress_note_after_two_and_six_minutes_then_answer():
    """Truoc day 10 phut im lang roi moi bao het gio."""
    h = _harness()
    try:
        h.fake_time(chat)
        fake_threading = types.SimpleNamespace(**{k: getattr(threading, k) for k in dir(threading)
                                                  if not k.startswith("__")})
        fake_threading.Thread = lambda target, daemon=None: _SlowThread(h.clock, 3, target)
        h.patch(chat, "threading", fake_threading)
        _chat(h, message(13, "việc dài", thread=VERA))
        texts = h.tg.texts()
        assert len(texts) == 4, texts
        assert "vẫn đang xử lý (2 phút)" in texts[1] and "tự dừng ở 10 phút" in texts[1]
        assert "vẫn đang xử lý (6 phút)" in texts[2]
        assert texts[3] == "xin chào"
    finally:
        h.__exit__()


# =========================================================================
# hang doi hai tang
# =========================================================================
def _wait(cond, timeout=3.0):
    t0 = time.time()
    while not cond() and time.time() - t0 < timeout:
        time.sleep(0.01)
    return cond()


def test_same_role_second_message_is_told_to_wait_and_runs_in_order():
    h = _harness()
    try:
        ticket, ahead = chat._rank_of("tele-vera").lay_so()      # tin 1 dang duoc tra loi
        assert (ticket, ahead) == (0, 0)
        t = threading.Thread(target=_chat, args=(h, message(14, "tin hai", thread=VERA)),
                             daemon=True)
        t.start()
        assert _wait(lambda: len(h.tg.texts()) == 1)
        assert "đang trả lời 1 tin trước" in h.tg.texts()[0]
        time.sleep(0.05)
        assert _asks(h) == [], "tin hai KHONG duoc chay khi tin mot chua xong"
        chat._rank_of("tele-vera").release()
        t.join(5)
        assert not t.is_alive() and len(_asks(h)) == 1
        assert h.tg.texts()[-1] == "xin chào"
    finally:
        h.__exit__()


def test_other_roles_wait_for_a_slot_and_are_told_who_is_running():
    h = _harness()
    try:
        h.patch(chat, "_CHO_CHAT", threading.BoundedSemaphore(1))
        h.patch(chat, "_SO_SONG_SONG", 1)
        chat._CHO_CHAT.acquire()
        chat._DANG_CHAY["gin"] = time.time()
        t = threading.Thread(target=_chat, args=(h, message(15, "chào", thread=VERA)),
                             daemon=True)
        t.start()
        assert _wait(lambda: len(h.tg.texts()) == 1)
        assert "chờ chỗ — đang có <b>gin</b> chạy" in h.tg.texts()[0]
        assert "tối đa 1 vai" in h.tg.texts()[0]
        assert _asks(h) == []
        chat._CHO_CHAT.release()
        t.join(5)
        assert not t.is_alive() and len(_asks(h)) == 1
        # cho da tra lai: vai sau vao thang
        assert chat._CHO_CHAT.acquire(blocking=False)
    finally:
        h.__exit__()


def test_queue_is_released_even_when_sending_fails_hard():
    """Mot ngoai le giua chung khong duoc giu ve so / cho chung mai mai — neu
    giu, MOI tin sau cua vai do treo vinh vien."""
    h = _harness()
    try:
        h.tg.script("sendMessage", RuntimeError("tele no"))
        try:
            _chat(h, message(16, "x", thread=VERA))
        except RuntimeError:
            pass
        else:
            raise AssertionError("ngoai le phai noi len cho _run_background bao")
        assert chat._DANG_CHAY == {}
        _chat(h, message(17, "y", thread=VERA))                  # khong treo
        assert h.tg.texts()[-1] == "xin chào"
        assert not any("tin trước" in t for t in h.tg.texts())
    finally:
        h.__exit__()


# =========================================================================
# boi canh task gan nhat (su co 03/09/2026 15:14 — Ethan "session trong")
# =========================================================================
def test_recent_kanban_tasks_are_prepended_to_the_prompt():
    h = _harness()
    try:
        h.patch(hermes_adapter, "has_kanban", lambda: True)
        h.patch(hermes_adapter, "job", h.spy("job", returns=[
            {"id": "t_1", "title": "Dựng 6 ảnh bài chip", "status": "done",
             "completed_at": 1_790_000_000},
            {"id": "t_2", "title": "Bài khác", "status": "running", "completed_at": None}]))
        h.patch(hermes_adapter, "last_run_many", h.spy("last_run_many", returns={
            "t_1": {"summary": "đã đẩy 3 ảnh\nlên topic"}}))
        _chat(h, message(18, "chưa đủ 6 ảnh", thread=VERA))
        job_call = [d for n, d in h.trace.of("fn") if n == "job"][0]
        assert job_call["kwargs"] == {"vai": "vera", "so": 3, "moi_truoc": True}
        prompt = _asks(h)[0]["args"][2]
        assert prompt.startswith("[Việc gần nhất của bạn trên kanban")
        assert "- t_1 [done] Dựng 6 ảnh bài chip" in prompt
        assert "tóm tắt: đã đẩy 3 ảnh lên topic" in prompt
        assert "- t_2 [running] Bài khác (xong -)" in prompt
        assert prompt.endswith("\n\nchưa đủ 6 ảnh")
    finally:
        h.__exit__()


def test_unreadable_kanban_degrades_to_plain_prompt_with_a_log_line():
    h = _harness()
    try:
        h.patch(hermes_adapter, "has_kanban", lambda: True)
        h.patch(hermes_adapter, "job", lambda **kw: None)
        assert chat.context_edge_role("vera") == ""
        assert any("khong doc duoc kanban" in t for t in h.logs("chat"))
        h.patch(hermes_adapter, "job", lambda **kw: [])
        assert chat.context_edge_role("vera") == ""
        assert chat.context_edge_role(None) == ""
    finally:
        h.__exit__()


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
