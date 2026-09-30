#!/usr/bin/env python3
"""Test cho `schedule_board.py` (LOW-428) — bang lich dang cua Ada.

Giu bon thu:
  1. `collect` chi lay bai CUA brand nay, co gio dang hom nay (gio VN) hoac con
     cho o ngay sau; bo draft chua duyet va tep phu (.writer/.meta).
  2. `render` ghi dung trang thai, nguoi viet (tu sidecar), gio VN, link the.
  3. `refresh` gui MOT tin roi chi SUA tin do; noi dung khong doi thi khong goi
     Telegram; ngay moi thi gui tin moi; tin bi xoa thi gui lai.
  4. Chua co bai nao va chua co tin -> im lang (khong gui bang rong).

Cach ly: DRAFTS la bien module (monkeypatch), state qua CT_STATE_DIR, topic qua
env_load.topics_path (monkeypatch). Khong goi mang: `call` la ham gia.

Chay:  python tests/test_schedule_board.py
"""
import json
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import env_load               # noqa: E402
import schedule_board as sb   # noqa: E402

BRAND = "donniechublog"
GROUP = "-1001234567"
# 30/09/2026 10:00 gio VN
NOW = int(datetime(2026, 9, 30, 10, 0, tzinfo=sb.VN).timestamp())
HOUR = 3600


class _Sandbox:
    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.drafts = base / "drafts"
        self.drafts.mkdir()
        topics = base / "topics.json"
        topics.write_text(json.dumps({"ada": 14, "miles": 9}), encoding="utf-8")
        self._old = (sb.DRAFTS, env_load.topics_path, os.environ.get("CT_STATE_DIR"))
        sb.DRAFTS = self.drafts
        env_load.topics_path = lambda brand=None: topics
        os.environ["CT_STATE_DIR"] = str(base / "state")
        return self

    def __exit__(self, *exc):
        sb.DRAFTS, env_load.topics_path, old_state = self._old
        if old_state is None:
            os.environ.pop("CT_STATE_DIR", None)
        else:
            os.environ["CT_STATE_DIR"] = old_state
        self._tmp.cleanup()
        return False

    def draft(self, draft_id, status, at, brand=BRAND, writer=None, title=None, card=None):
        d = {"caption": "x", "brand": brand, "status": status, "publish_at": at}
        if card:
            d["tg_card_message_id"] = card
        (self.drafts / (draft_id + ".json")).write_text(json.dumps(d), encoding="utf-8")
        if writer:
            (self.drafts / (draft_id + ".writer.json")).write_text(
                json.dumps({"writer_role": writer, "title": title or draft_id}), encoding="utf-8")


class FakeTelegram:
    def __init__(self):
        self.calls = []
        self.next_mid = 100
        self.edit_reply = None

    def __call__(self, token, method, **kw):
        self.calls.append((method, kw))
        if method == "sendMessage":
            self.next_mid += 1
            return {"ok": True, "result": {"message_id": self.next_mid}}
        if method == "editMessageText":
            return self.edit_reply or {"ok": True, "result": {}}
        return {"ok": False, "description": "unexpected"}


def test_collect_filters():
    with _Sandbox() as s:
        s.draft("a-today-published", "published", NOW - 2 * HOUR, writer="jika")
        s.draft("b-today-scheduled", "scheduled", NOW + HOUR, writer="miles")
        s.draft("c-tomorrow-scheduled", "scheduled", NOW + 24 * HOUR)
        s.draft("d-yesterday-published", "published", NOW - 24 * HOUR)
        s.draft("e-pending", "pending", NOW)
        s.draft("f-other-brand", "scheduled", NOW + HOUR, brand="dcgr.tech")
        s.draft("g-cancelled", "cancelled", NOW - HOUR)
        ids = [r["draft_id"] for r in sb.collect(now=NOW, brand=BRAND)]
        assert ids == ["a-today-published", "g-cancelled", "b-today-scheduled",
                       "c-tomorrow-scheduled"], ids


def test_render_rows():
    with _Sandbox() as s:
        s.draft("a", "published", NOW - HOUR, writer="jika", title="GPT 6.1 Sol <x>", card=5347)
        s.draft("b", "scheduled", NOW + HOUR, writer="miles", title="Dots")
        body = sb.render(sb.collect(now=NOW, brand=BRAND), NOW, BRAND, GROUP)
        assert "Lịch đăng donniechublog — 30/09" in body, body
        assert "✅ 1 đã đăng · 🕒 1 chờ" in body, body
        assert "✅ 09:00 · Jika · <a href=\"https://t.me/c/1234567/5347\">GPT 6.1 Sol &lt;x&gt;</a>" in body, body
        assert "🕒 11:00 · Miles · Dots" in body, body
        assert "Cập nhật" not in body          # gio cap nhat nam ngoai dau van tay


def test_refresh_send_then_edit_then_unchanged():
    with _Sandbox() as s:
        tg = FakeTelegram()
        s.draft("a", "scheduled", NOW + HOUR, writer="miles")
        assert sb.refresh(tg, "tok", GROUP, now=NOW, brand=BRAND) == "sent"
        method, kw = tg.calls[-1]
        assert method == "sendMessage" and kw["message_thread_id"] == 14, tg.calls
        # khong doi gi -> khong goi Telegram
        n = len(tg.calls)
        assert sb.refresh(tg, "tok", GROUP, now=NOW + 60, brand=BRAND) == "unchanged"
        assert len(tg.calls) == n
        # bai da dang -> sua DUNG tin cu
        s.draft("a", "published", NOW + HOUR, writer="miles")
        assert sb.refresh(tg, "tok", GROUP, now=NOW + HOUR + 60, brand=BRAND) == "edited"
        method, kw = tg.calls[-1]
        assert method == "editMessageText" and kw["message_id"] == 101, tg.calls
        assert "✅" in kw["text"]


def test_refresh_empty_is_silent():
    with _Sandbox():
        tg = FakeTelegram()
        assert sb.refresh(tg, "tok", GROUP, now=NOW, brand=BRAND) == "empty"
        assert tg.calls == []


def test_refresh_new_day_new_message():
    with _Sandbox() as s:
        tg = FakeTelegram()
        s.draft("a", "scheduled", NOW + HOUR)
        sb.refresh(tg, "tok", GROUP, now=NOW, brand=BRAND)
        s.draft("b", "scheduled", NOW + 24 * HOUR)
        assert sb.refresh(tg, "tok", GROUP, now=NOW + 24 * HOUR - 60, brand=BRAND) == "sent"
        assert [m for m, _ in tg.calls] == ["sendMessage", "sendMessage"], tg.calls


def test_refresh_deleted_message_resends():
    with _Sandbox() as s:
        tg = FakeTelegram()
        s.draft("a", "scheduled", NOW + HOUR)
        sb.refresh(tg, "tok", GROUP, now=NOW, brand=BRAND)
        s.draft("a", "cancelled", NOW + HOUR)
        tg.edit_reply = {"ok": False, "description": "Bad Request: message to edit not found"}
        assert sb.refresh(tg, "tok", GROUP, now=NOW + 60, brand=BRAND) == "sent"
        assert [m for m, _ in tg.calls] == ["sendMessage", "editMessageText", "sendMessage"]


def test_refresh_other_edit_error_keeps_state():
    with _Sandbox() as s:
        tg = FakeTelegram()
        s.draft("a", "scheduled", NOW + HOUR)
        sb.refresh(tg, "tok", GROUP, now=NOW, brand=BRAND)
        s.draft("a", "published", NOW + HOUR)
        tg.edit_reply = {"ok": False, "description": "Too Many Requests"}
        assert sb.refresh(tg, "tok", GROUP, now=NOW + 60, brand=BRAND).startswith("error")
        # lan sau Telegram on lai -> van sua tin cu, khong gui tin thu hai
        tg.edit_reply = None
        assert sb.refresh(tg, "tok", GROUP, now=NOW + 120, brand=BRAND) == "edited"
        assert [m for m, _ in tg.calls].count("sendMessage") == 1


if __name__ == "__main__":
    fails = 0
    for name, fn in sorted(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print("PASS", name)
            except Exception as e:                           # noqa: BLE001
                fails += 1
                print("FAIL", name, type(e).__name__, e)
    sys.exit(1 if fails else 0)
