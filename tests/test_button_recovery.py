#!/usr/bin/env python3
"""LOW-134 — album len topic ma MAT nut Duyet/Lam lai/Bo (su co 14/09/2026).

Chuoi that (phien Kite 20260914_115957_2c11ed): mang may chu toi Telegram chap
(`SSL: UNEXPECTED_EOF_WHILE_READING`) -> album len nhung sendMessage tin nut nem
httpx.ConnectError (khong phai SendError, nhanh cuu submit_common khong chay) ->
vai chay lai -> chong trung 30 phut return TRUOC buoc gui nut -> khong bao gio co nut.

Test hai phan:
  A. send_telegram.post: loi mang thanh SendError, thu lai loi chua-gui-di, so
     ghi du message_ids + button_message_id, chay lai thi CHI gui bu nut.
  B. approve_post.handle_reply_approval: Ong Chu reply vao anh bat ky trong album
     "gửi cho Jika" = bam ✅ nhung ep nguoi viet.

Chay:  venv/bin/python tests/test_button_recovery.py
"""
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import send_telegram as st                                        # noqa: E402
import approve_post as db                                         # noqa: E402


# ================================================================ A. send_telegram
class FakeTelegram:
    """Handler cho MockTransport: album 3 anh id 1569..1571, tin nut id 1600;
    `button_failures` lan dau sendMessage nem ConnectError."""

    def __init__(self, button_failures=0, album_error=None):
        self.calls = []
        self.button_failures = button_failures
        self.album_error = album_error

    def __call__(self, request):
        method = request.url.path.rsplit("/", 1)[-1]
        request.read()
        self.calls.append((method, request))
        if method == "sendMediaGroup":
            if self.album_error:
                raise self.album_error("gia lap", request=request)
            return httpx.Response(200, json={"ok": True, "result": [
                {"message_id": 1569 + i} for i in range(3)]})
        if method == "sendMessage":
            if self.button_failures:
                self.button_failures -= 1
                raise httpx.ConnectError("[SSL: UNEXPECTED_EOF_WHILE_READING]", request=request)
            return httpx.Response(200, json={"ok": True, "result": {"message_id": 1600}})
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    def count(self, method):
        return sum(1 for m, _ in self.calls if m == method)


def _files(tmp: Path) -> list:
    out = []
    for i in range(3):
        f = tmp / ("d-1.png" if i == 0 else f"d-1_{i + 1}.png")
        if not f.exists():
            f.write_bytes(b"png%d" % i)
        out.append(f)
    return out


def _post(tmp: Path, fake: FakeTelegram, **kw):
    real_client = httpx.Client
    saved = (st.STATE, st.RETRY_DELAYS, st.env_load.load, st._topic)

    def client(*a, **k):
        k.pop("transport", None)
        return real_client(*a, transport=httpx.MockTransport(fake), **k)

    os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_GROUP_ID"] = "tok", "-100"
    httpx.Client = client
    st.STATE, st.RETRY_DELAYS = tmp / "sent", (0, 0, 0)
    st.env_load.load = lambda *a, **k: None
    st._topic = lambda vai: 52
    try:
        return st.post("kite", _files(tmp), "Carousel", **kw)
    finally:
        httpx.Client = real_client
        st.STATE, st.RETRY_DELAYS, st.env_load.load, st._topic = saved


def _journal(tmp: Path) -> list:
    p = tmp / "sent" / "kite.jsonl"
    return [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines()] if p.exists() else []


def test_button_network_error_is_send_error_and_journal_marks_missing():
    with tempfile.TemporaryDirectory() as t:
        tmp, fake = Path(t), FakeTelegram(button_failures=99)
        try:
            _post(tmp, fake, duyet="d-1")
            raised = None
        except st.SendError as e:
            raised = e
        rec = _journal(tmp)[-1]
    assert raised is not None, "loi mang o tin nut phai thanh SendError, khong duoc lot httpx ra ngoai"
    assert fake.count("sendMessage") == 4, f"phai thu lai tin nut 3 lan nua, dang {fake.count('sendMessage')}"
    assert rec["message_ids"] == [1569, 1570, 1571] and rec["message_id"] == 1571, rec
    assert rec["button_draft"] == "d-1" and rec["button_message_id"] is None, rec


def test_rerun_resends_only_button():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        try:
            _post(tmp, FakeTelegram(button_failures=99), duyet="d-1")
        except st.SendError:
            pass
        fake = FakeTelegram()
        res = _post(tmp, fake, duyet="d-1")
        rec = _journal(tmp)[-1]
    assert fake.count("sendMediaGroup") == 0, "chay lai KHONG duoc gui trung album"
    assert fake.count("sendMessage") == 1, "chay lai phai gui BU dung mot tin nut"
    body = fake.calls[0][1].content
    assert b"reply_to_message_id=1571" in body and b"imgok%3Ad-1" in body, body
    assert res["duplicate"] and res["button_state"] == "resent" and res["button_message_id"] == 1600, res
    assert rec["button_message_id"] == 1600, rec


def test_transient_button_error_is_retried():
    with tempfile.TemporaryDirectory() as t:
        tmp, fake = Path(t), FakeTelegram(button_failures=1)
        res = _post(tmp, fake, duyet="d-1")
        rec = _journal(tmp)[-1]
    assert res["button_state"] == "sent" and fake.count("sendMessage") == 2, res
    assert rec["button_message_id"] == 1600, rec


def test_album_read_timeout_is_not_retried():
    """ReadTimeout = co the album DA len: thu lai la trung album."""
    with tempfile.TemporaryDirectory() as t:
        tmp, fake = Path(t), FakeTelegram(album_error=httpx.ReadTimeout)
        try:
            _post(tmp, fake, duyet="d-1")
            raised = False
        except st.SendError:
            raised = True
        journal = _journal(tmp)
    assert raised and fake.count("sendMediaGroup") == 1, fake.calls
    assert journal == [], "album chua chac len thi khong ghi so"


def test_old_journal_record_without_button_field_is_not_resent():
    """Dong so truoc LOW-134 khong biet nut co len khong: giu hanh vi cu, khong gui."""
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        files = _files(tmp)
        (tmp / "sent").mkdir()
        (tmp / "sent" / "kite.jsonl").write_text(json.dumps(
            {"ts": int(time.time()), "message_id": 1571, "files": [str(f) for f in files],
             "md5": st._md5(files), "mo_ta": ""}) + "\n", encoding="utf-8")
        fake = FakeTelegram()
        res = _post(tmp, fake, duyet="d-1")
    assert fake.calls == [] and res["button_state"] == "unknown", (fake.calls, res)


# ============================================================ B. reply "gửi cho"
DRAFT = "reverse-engineering-kite-donniechublog"


def _approve_env(tmp: Path, records, writer="miles", brand="donniechublog"):
    drafts = tmp / "drafts"
    drafts.mkdir()
    sent = tmp / "state" / "telegram_sent"
    sent.mkdir(parents=True)
    (drafts / f"{DRAFT}.writer.json").write_text(json.dumps(
        {"vai_viet": writer, "title": "Tin test", "created": False, "dre_task": "t_anh1",
         "body": f"venv/bin/python {writer}_prepare.py x\nvenv/bin/python {writer}_submit.py x"}),
        encoding="utf-8")
    (drafts / f"{DRAFT}.meta.json").write_text(json.dumps({"brand": brand}), encoding="utf-8")
    (sent / "kite.jsonl").write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
    return drafts, tmp / "state"


def _old_record():
    """Dung dang dong so cua album 1576 ngay 14/09: chi message_id tin cuoi."""
    return {"ts": 1, "message_id": 1576,
            "files": [f"/x/drafts/{DRAFT}.png"] + [f"/x/drafts/{DRAFT}_{i}.png" for i in range(2, 9)]}


class ApprovePatch:
    """Thay moi phu thuoc ngoai cua approve_post; ghi lai task tao va cac lan goi API."""

    def __init__(self, drafts, state_dir, queue_writer="miles"):
        self.tasks, self.calls = [], []
        self.values = {
            "DRAFTS": drafts, "STATE_DIR": state_dir,
            "kanban_create": lambda title, vai, body, parent=None: self.tasks.append((vai, body)) or ("t_writer1", None),
            "_report_receive_job": lambda *a, **k: None,
            "_status_task": lambda _tid: "done",
            "call": lambda *a, **k: self.calls.append((a, k)) or {"ok": True},
            "_run_background": lambda name, fn, token, group, thread, *args: fn(*args),
            "_writer_by_queue": lambda draft_id, w: queue_writer,
        }

    def __enter__(self):
        self.saved = {k: getattr(db, k) for k in self.values}
        for k, v in self.values.items():
            setattr(db, k, v)
        return self

    def __exit__(self, *exc):
        for k, v in self.saved.items():
            setattr(db, k, v)

    def sent_texts(self):
        return [k for a, k in self.calls if a[1] == "sendMessage"]


def _msg(reply_to=1570, mid=1700):
    m = {"message_id": mid, "message_thread_id": 52, "chat": {"id": -100}, "from": {"id": 1}}
    if reply_to:
        m["reply_to_message"] = {"message_id": reply_to, "message_thread_id": 52}
    return m


def test_parse_reply_approval():
    cases = {"gửi cho Jika": "Jika", "Gửi Miles.": "Miles", "gui cho miles": "miles",
             "duyệt, gửi cho jika": "jika", "duyệt": "", "Duyet!": "",
             "ảnh đẹp quá": None, "gửi cho mẹ xem đi": None, "": None}
    for text, want in cases.items():
        got = db.parse_reply_approval(text)
        assert got == want, f"{text!r}: muon {want!r}, duoc {got!r}"


def test_find_album_draft_old_record_any_photo():
    with tempfile.TemporaryDirectory() as t:
        drafts, state = _approve_env(Path(t), [_old_record()])
        with ApprovePatch(drafts, state):
            first, middle, before, after = (db.find_album_draft(i) for i in (1569, 1572, 1568, 1577))
    assert first and first[0] == DRAFT and middle and middle[0] == DRAFT, (first, middle)
    assert before is None and after is None, (before, after)


def test_find_album_draft_by_button_message():
    rec = {"ts": 1, "message_id": 2002, "message_ids": [2001, 2002], "button_draft": DRAFT,
           "button_message_id": 2003, "files": ["/x/a.png", "/x/b.png"]}
    with tempfile.TemporaryDirectory() as t:
        drafts, state = _approve_env(Path(t), [rec])
        with ApprovePatch(drafts, state):
            by_button, by_photo = db.find_album_draft(2003), db.find_album_draft(2001)
    assert by_button and by_button[0] == DRAFT and by_photo and by_photo[0] == DRAFT


def test_reply_send_to_named_writer_bypasses_queue():
    with tempfile.TemporaryDirectory() as t:
        drafts, state = _approve_env(Path(t), [_old_record()], writer="miles")
        with ApprovePatch(drafts, state, queue_writer="miles") as p:
            handled = db.handle_reply_approval("tok", "-100", _msg(), 52, "gửi cho Jika")
        w = json.loads((drafts / f"{DRAFT}.writer.json").read_text(encoding="utf-8"))
    assert handled
    assert [v for v, _ in p.tasks] == ["jika"], f"phai giao Jika dung ten Ong Chu go: {p.tasks}"
    assert "jika_prepare.py" in p.tasks[0][1], "body phai tro lenh sang Jika"
    assert w["created"] is True and w["vai_viet"] == "jika", w
    assert not [a for a, _ in p.calls if a[1] == "answerCallbackQuery"], "reply khong co callback de tra loi"
    replies = [k for k in p.sent_texts() if k.get("reply_to_message_id") == 1700]
    assert replies and "Jika" in replies[0]["text"], p.sent_texts()


def test_reply_approve_without_name_uses_queue():
    with tempfile.TemporaryDirectory() as t:
        drafts, state = _approve_env(Path(t), [_old_record()], writer="miles")
        with ApprovePatch(drafts, state, queue_writer="jika") as p:
            assert db.handle_reply_approval("tok", "-100", _msg(), 52, "duyệt")
    assert [v for v, _ in p.tasks] == ["jika"], p.tasks


def test_reply_non_writer_name_warns_without_task():
    with tempfile.TemporaryDirectory() as t:
        drafts, state = _approve_env(Path(t), [_old_record()])
        with ApprovePatch(drafts, state) as p:
            handled = db.handle_reply_approval("tok", "-100", _msg(), 52, "gửi cho Kite")
    assert handled and p.tasks == [], p.tasks
    assert "không phải người viết" in p.sent_texts()[0]["text"], p.sent_texts()


def test_reply_not_to_album_falls_through():
    with tempfile.TemporaryDirectory() as t:
        drafts, state = _approve_env(Path(t), [_old_record()])
        with ApprovePatch(drafts, state) as p:
            no_reply = db.handle_reply_approval("tok", "-100", _msg(reply_to=None), 52, "gửi cho Jika")
            other_msg = db.handle_reply_approval("tok", "-100", _msg(reply_to=999), 52, "gửi cho Jika")
            chat = db.handle_reply_approval("tok", "-100", _msg(), 52, "ảnh đẹp quá")
            topic_root = db.handle_reply_approval("tok", "-100", _msg(reply_to=52), 52, "gửi cho Jika")
    assert not (no_reply or other_msg or chat or topic_root), (no_reply, other_msg, chat, topic_root)
    assert p.tasks == [] and p.calls == []


def test_second_reply_after_approval_creates_no_new_task():
    with tempfile.TemporaryDirectory() as t:
        drafts, state = _approve_env(Path(t), [_old_record()])
        with ApprovePatch(drafts, state) as p:
            db.handle_reply_approval("tok", "-100", _msg(), 52, "gửi cho Jika")
            db.handle_reply_approval("tok", "-100", _msg(mid=1701), 52, "gửi cho Miles")
    assert len(p.tasks) == 1, f"reply lan hai khong duoc tao task moi: {p.tasks}"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
