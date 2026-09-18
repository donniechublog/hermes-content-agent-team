#!/usr/bin/env python3
"""Nut "Duyet & dang" sau khi co hang doi xep lich (18/09/2026).

Nut khong con dang bai nua -- no goi `publish_schedule.schedule()` de chiem mot
slot roi tra the ve NGAY, kem hai nut moi: "Dang ngay" (pnow) va "Huy lich"
(pcancel). Viec dang that su do cron `publish-due` lam, hoac do chinh nut
"Dang ngay" goi `publish_schedule.publish_one()` -- CUNG MOT ham, khong co ban
sao.

Test o day giu dung mot thu: cai nut goi dung cai gi. Con hanh vi cua
`schedule`/`publish_one` (con tro slot, bat bien "Telegram loi thi khong day
moat") nam o tests/test_publish_schedule.py.

Chay:  venv/bin/python tests/test_approve_schedule_button.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import approve_post as db              # noqa: E402
import publish_schedule as ps          # noqa: E402


class _Bench:
    """drafts/ tam + moi cua ra ngoai cua handle_callback deu bi chan lai."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.drafts = Path(self._tmp.name) / "drafts"
        self.drafts.mkdir()
        self.calls = []            # (method, kwargs) da goi len Bot API
        self.published = []        # draft_id da that su dang
        self.scheduled = []        # draft_id da xep lich
        self._old = (db.DRAFTS, db.call, db.is_boss, db.publish,
                     db.publish_schedule, db.log)
        db.DRAFTS = self.drafts
        db.call = lambda token, method, **kw: (self.calls.append((method, kw))
                                               or {"ok": True})
        db.is_boss = lambda cq: True
        db.publish = self._publish_khong_duoc_goi
        db.log = lambda *a, **k: None
        db.publish_schedule = self._fake_schedule()
        return self

    def __exit__(self, *exc):
        (db.DRAFTS, db.call, db.is_boss, db.publish,
         db.publish_schedule, db.log) = self._old
        self._tmp.cleanup()
        return False

    def _publish_khong_duoc_goi(self, *a, **k):
        raise AssertionError("nut khong duoc dang bai truc tiep nua")

    def _fake_schedule(bench):
        class _Fake:
            SCHEDULED = ps.SCHEDULED
            CANCELLED = ps.CANCELLED

            @staticmethod
            def schedule(draft_id, now=None):
                bench.scheduled.append(draft_id)
                return 1_700_003_600

            @staticmethod
            def publish_one(draft_id):
                bench.published.append(draft_id)
                return True, "✅ ĐÃ ĐĂNG lên channel"

        return _Fake

    def write_draft(self, draft_id, **fields):
        d = {"caption": "bai thu", "brand": "donniechublog"}
        d.update(fields)
        (self.drafts / (draft_id + ".json")).write_text(
            json.dumps(d, ensure_ascii=False), encoding="utf-8")

    def read_draft(self, draft_id):
        return json.loads((self.drafts / (draft_id + ".json")).read_text(encoding="utf-8"))

    def press(self, action, draft_id="d1"):
        cq = {"id": "cbq1", "data": action + ":" + draft_id,
              "from": {"id": 1},
              "message": {"chat": {"id": 9}, "message_id": 7, "text": "BẢN NHÁP"}}
        db.handle_callback("tok", "chan", cq)

    def keyboard_last(self):
        """reply_markup cua lan sua tin nhan gan nhat."""
        for method, kw in reversed(self.calls):
            if "reply_markup" in kw:
                return kw["reply_markup"]
        return None

    def text_last(self):
        for method, kw in reversed(self.calls):
            if "text" in kw and method != "answerCallbackQuery":
                return kw["text"]
            if "caption" in kw:
                return kw["caption"]
        return ""


def test_approve_button_schedules_instead_of_publishing():
    """Bam Duyet: goi schedule(), KHONG dang, va the hien gio se dang."""
    with _Bench() as b:
        b.write_draft("d1")
        b.press("ok")
        assert b.scheduled == ["d1"], b.scheduled
        assert b.published == [], "nut Duyet khong duoc dang ngay nua"
        assert db._clock(1_700_003_600) in b.text_last(), (
            f"the phai ghi gio se dang (gio VN): {b.text_last()!r}")


def test_approve_button_leaves_publish_now_and_cancel_buttons():
    """Xep lich xong phai con duong ra tay: dang ngay, hoac huy."""
    with _Bench() as b:
        b.write_draft("d1")
        b.press("ok")
        kb = b.keyboard_last()
        data = [nut["callback_data"] for hang in kb["inline_keyboard"] for nut in hang]
        assert "pnow:d1" in data, data
        assert "pcancel:d1" in data, data


def test_approve_button_refuses_draft_already_scheduled():
    """Bam Duyet lan hai khong duoc chiem them mot slot nua."""
    with _Bench() as b:
        b.write_draft("d1", status=ps.SCHEDULED, publish_at=1_700_000_000)
        b.press("ok")
        assert b.scheduled == [], "da chiem slot thu hai cho cung mot bai"


def test_publish_now_button_calls_publish_one():
    with _Bench() as b:
        b.write_draft("d1", status=ps.SCHEDULED, publish_at=1_700_003_600)
        db._publish_now_work("tok", {"chat": {"id": 9}, "message_id": 7,
                                     "text": "BẢN NHÁP"}, "d1")
        assert b.published == ["d1"], b.published


def test_cancel_button_marks_cancelled_without_publishing():
    with _Bench() as b:
        b.write_draft("d1", status=ps.SCHEDULED, publish_at=1_700_003_600)
        b.press("pcancel")
        assert b.published == [], "huy lich ma van dang"
        assert b.read_draft("d1")["status"] == ps.CANCELLED


def test_cancelled_draft_cannot_be_approved_again():
    """Da huy la xong: bam Duyet lai khong duoc am tham xep lich lan nua."""
    with _Bench() as b:
        b.write_draft("d1", status=ps.CANCELLED)
        b.press("ok")
        assert b.scheduled == [], b.scheduled


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "tests"))
    from tam import chay_tat_ca          # noqa: E402
    chay_tat_ca(globals())
