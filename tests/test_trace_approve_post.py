#!/usr/bin/env python3
"""LOW-311 — luoi doi chieu vet cho approve_post: nut tren the duyet (Duyet / Bo /
Dang ngay / day lai moat), cong duyet ANH (imgok / imgno / imgredo / imgkite),
vong hoi ly do lam lai, duyet bang reply (LOW-134) va `publish()` len channel.

Moi kich ban dung theo mot SU CO THAT va khang dinh ba thu: vet goi ra ngoai
(thu tu + tham so), tep state sau cung, tin gui cho Ong Chu. Canh I/O thay bang
tests/trace_harness.py — khong mang, khong thread, khong state that.

Chay:  python tests/test_trace_approve_post.py
"""
import json
import os
import sys
import tempfile
import threading
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from PIL import Image                  # noqa: E402

import approve_base as base            # noqa: E402
import approve_dispatch as dispatch    # noqa: E402
import approve_post as post            # noqa: E402
import blackboard                      # noqa: E402
import hermes_adapter                  # noqa: E402
import image_provenance                # noqa: E402
import moat_publish                    # noqa: E402
import publish_schedule                # noqa: E402
import state_paths                     # noqa: E402
from trace_harness import Harness, callback, message, run_tests  # noqa: E402

BOSS = 42
DRE, KITE, MILES, JIKA = 55, 66, 88, 89          # topic id gia
DRAFT = "openai-ipo-dcgr"
LONG_CAPTION = ("<b>OpenAI nop ho so IPO</b>\n\n"
                + "\n\n".join(f"Doan {i}: " + "chu " * 60 for i in range(1, 8)))


class FakeHttp:
    """Thay ten global `httpx` cua approve_post: `publish()` mo httpx.Client
    thang (anh dang kenh la ban goc, khong qua call_upload). Ghi vet
    ("http", method, data, files) va tra cau tra loi da xep hang."""

    def __init__(self, trace):
        self.trace = trace
        self._queue = {}

    def script(self, method, *responses):
        self._queue.setdefault(method, []).extend(responses)
        return self

    def Client(self, timeout=None):                          # noqa: N802
        return _FakeHttpClient(self)

    def sent(self, method=None):
        return [d for n, d in self.trace.of("http") if method is None or n == method]


class _FakeHttpClient:
    def __init__(self, owner):
        self.owner = owner

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def post(self, url, data=None, files=None):
        method = url.rsplit("/", 1)[-1]
        self.owner.trace.add("http", method, data=dict(data or {}),
                             files=sorted(files or {}))
        q = self.owner._queue.get(method)
        if q:
            r = q.pop(0)
            if isinstance(r, BaseException):
                raise r
        elif method == "sendMediaGroup":
            r = {"ok": True, "result": [{"message_id": 9001}, {"message_id": 9002}]}
        else:
            r = {"ok": True, "result": {"message_id": 9100}}
        return types.SimpleNamespace(json=lambda: r)


def _harness(run_background=True):
    h = Harness(post, base, dispatch, publish_schedule)
    h.__enter__()
    h.capture_logs()
    h.inline_background(run=run_background)
    h.topics({"dre": DRE, "kite": KITE, "miles": MILES, "jika": JIKA})
    # standard_assignee kiem profile co that trong home container
    home = h.tmp / "home"
    for slug in ("dre", "ethan", "kite", "miles", "jika"):
        (home / "profiles" / slug).mkdir(parents=True)
    h.patch(dispatch, "HERMES_HOME", str(home))
    # kanban: ghi vet lenh tao, trang thai doc tu bang `h.task_status`
    h.task_status = {}
    h.created = []

    def _create(title, assignee, body, parent=None, max_runtime=None):
        h.created.append({"title": title, "assignee": assignee, "body": body, "parent": parent})
        return f"t_new{len(h.created)}", None
    h.patch(hermes_adapter, "create_task", h.spy("create_task", side_effect=_create))
    h.patch(hermes_adapter, "status", lambda tid: h.task_status.get(tid, "done") if tid else "")
    h.patch(hermes_adapter, "count_form_run", lambda tru_tid=None: 0)
    h.patch(hermes_adapter, "writer_queue", lambda slugs: None)
    h.patch(hermes_adapter, "last_run", lambda tid: {"summary": "thieu anh that", "metadata": {}})
    h.patch(blackboard, "write_background", h.spy("blackboard", returns=(True, "")))
    h.patch(image_provenance, "remove_used_for_draft", h.spy("remove_used", returns=2))
    # lich dang: state theo tmp, khong doc secret that, khong cham moat
    h.patch(publish_schedule, "_state_file", lambda name: h.state / name)
    h.patch(publish_schedule, "_secrets", lambda: (h.token, h.channel))
    h.patch(publish_schedule, "_finish_card", h.spy("_finish_card"))
    h.patch(moat_publish, "intake", h.spy("intake", returns=(True, "wf_1")))
    h.patch(moat_publish, "report_card", h.spy("report_card"))
    # LOW-361: Lam lai chay lai khau tim anh (subprocess image_prepare) — vet thay vi chay that.
    h.patch(post, "_refresh_images_for_redo", h.spy("refresh_images", returns=""))
    h.http = FakeHttp(h.trace)
    h.patch(post, "httpx", h.http)

    class SyncThread:
        """threading.Thread chay DONG BO luc start() — khong de thread that song sot."""

        def __init__(self, target=None, args=(), kwargs=None, daemon=None, name=None):
            self.target, self.args, self.kwargs = target, args, kwargs or {}

        def start(self):
            h.trace.add("thread", getattr(self.target, "__name__", "?"))
            self.target(*self.args, **self.kwargs)
    h.patch(threading, "Thread", SyncThread)
    return h


def _boss_only(h):
    (h.state / state_paths.BOSS_IDS_FILE).write_text(json.dumps([BOSS]), encoding="utf-8")


def _answers(h):
    return [(d.get("text"), bool(d.get("show_alert"))) for d in h.tg.sent("answerCallbackQuery")]


def _png(path, size=(64, 80), color=(10, 120, 200)):
    Image.new("RGB", size, color).save(path, "PNG")
    return str(path)


def _sidecars(h, draft_id=DRAFT, *, image_role="dre", writer="miles", root=None,
              dre_task="t_dre1", brand=None, carousel=True):
    img = {"image_role": image_role, "title": "OpenAI nop ho so IPO", "carousel": carousel,
           "body": "Nguon: Reuters\nLink: https://a.b/c\nTom tat: OpenAI nop S-1\nBODY-ANH-GOC",
           "last_task": dre_task}
    (h.drafts / f"{draft_id}.img.json").write_text(json.dumps(img), encoding="utf-8")
    w = {"writer_role": writer, "title": "OpenAI nop ho so IPO", "created": False,
         "dre_task": dre_task,
         "body": f"venv/bin/python {writer}_prepare.py x\nvenv/bin/python {writer}_submit.py x"}
    if root:
        w["root_task"] = root
    (h.drafts / f"{draft_id}.writer.json").write_text(json.dumps(w), encoding="utf-8")
    if brand:
        (h.drafts / f"{draft_id}.meta.json").write_text(json.dumps({"brand": brand}), encoding="utf-8")


def _side(h, suffix, draft_id=DRAFT):
    return json.loads((h.drafts / f"{draft_id}.{suffix}.json").read_text(encoding="utf-8"))


def _redo_wait(h):
    p = h.state / state_paths.REDO_WAITING_FILE
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}


# =========================================================================
# handle_callback — cong vao cua moi nut
# =========================================================================
def test_stranger_pressing_approve_changes_nothing():
    """06/09/2026: truoc do nhanh nut khong doc cq["from"] — bat ky thanh vien
    group nao bam ✅ la bai len channel va sang moat."""
    h = _harness()
    try:
        _boss_only(h)
        h.write_draft(DRAFT, caption="x")
        post.handle_callback(h.token, h.channel, callback("ok:" + DRAFT, user=666))
        assert h.tg.methods() == ["answerCallbackQuery"], h.tg.methods()
        assert _answers(h) == [("Chỉ Ông Chủ bấm được nút này.", True)]
        assert h.read_draft(DRAFT)["status"] == "pending"
        assert not (h.state / state_paths.PUBLISH_SCHEDULE_FILE).exists()
        assert any("TU CHOI cq tu 666" in t for t in h.logs("nut"))
    finally:
        h.__exit__()


def test_stranger_cannot_hand_image_to_writer_either():
    h = _harness()
    try:
        _boss_only(h)
        _sidecars(h)
        post.handle_callback(h.token, h.channel, callback("imgok:" + DRAFT, user=666))
        assert h.created == [] and h.tg.methods() == ["answerCallbackQuery"]
        assert _side(h, "writer")["created"] is False
    finally:
        h.__exit__()


def test_forged_draft_id_cannot_reach_files_outside_drafts():
    """callback_data do client gui: "no:../state/x" tung doc/ghi `status` vao
    mot tep JSON bat ky cua dich vu."""
    h = _harness()
    try:
        victim = h.state / "victim.json"
        victim.write_text(json.dumps({"status": "pending", "keep": 1}), encoding="utf-8")
        post.handle_callback(h.token, h.channel, callback("no:../state/victim"))
        assert json.loads(victim.read_text(encoding="utf-8")) == {"status": "pending", "keep": 1}
        assert _answers(h) == [("Nút hỏng (mã bài không hợp lệ).", True)]
        assert h.tg.methods() == ["answerCallbackQuery"]
    finally:
        h.__exit__()


def test_button_of_vanished_draft_says_not_found():
    h = _harness()
    try:
        post.handle_callback(h.token, h.channel, callback("ok:da-xoa"))
        assert _answers(h) == [("Không tìm thấy bản nháp", True)]
        assert h.tg.methods() == ["answerCallbackQuery"]
    finally:
        h.__exit__()


def test_unknown_action_touches_nothing():
    """Ghim hanh vi HIEN TAI: action la tren draft con pending -> khong sua tin,
    khong doi trang thai (va cung khong tra loi callback)."""
    h = _harness()
    try:
        h.write_draft(DRAFT, caption="x")
        post.handle_callback(h.token, h.channel, callback("zzz:" + DRAFT))
        assert h.tg.methods() == [], h.tg.methods()
        assert h.read_draft(DRAFT) == {"id": DRAFT, "status": "pending", "caption": "x"}
    finally:
        h.__exit__()


def test_corrupt_draft_file_surfaces_error_on_the_button():
    """Tep draft hong: chot trang thai doc ra {} (khong chan), `mark_draft` nem —
    _process_button phai bao loi len nut roi nem tiep cho _run_background."""
    h = _harness()
    try:
        (h.drafts / f"{DRAFT}.json").write_text("{hong", encoding="utf-8")
        raised = None
        try:
            post._process_button(h.token, h.channel, callback("no:" + DRAFT))
        except ValueError as e:
            raised = e
        assert raised is not None, "loi phai di tiep len _run_background"
        assert h.tg.methods() == ["answerCallbackQuery"]
        text, alert = _answers(h)[0]
        assert text.startswith("Lỗi: JSONDecodeError") and alert
        assert (h.drafts / f"{DRAFT}.json").read_text(encoding="utf-8") == "{hong"
    finally:
        h.__exit__()


# =========================================================================
# E5 / LOW-296 — bam Duyet hai lan
# =========================================================================
def test_double_press_approve_takes_one_slot_only():
    """Bam ✅ hai lan: lan hai KHONG duoc chiem slot thu hai (bai ke tiep se bi
    day lui mot tieng) va khong duoc sua the lan nua."""
    h = _harness()
    try:
        h.fake_time(post, publish_schedule)
        h.write_draft(DRAFT, caption="x")
        cq = callback("ok:" + DRAFT, text="BẢN NHÁP\n\nx")
        post._process_button(h.token, h.channel, cq)
        slot = json.loads((h.state / state_paths.PUBLISH_SCHEDULE_FILE).read_text())["last_slot"]
        first = h.read_draft(DRAFT)
        assert first["status"] == publish_schedule.SCHEDULED and first["publish_at"] == slot
        assert h.tg.methods() == ["answerCallbackQuery", "editMessageText"]
        edit = h.tg.sent("editMessageText")[0]
        assert "ĐÃ DUYỆT — đăng lúc" in edit["text"] and "BẢN NHÁP (đã xử lý)" in edit["text"]
        assert [b["callback_data"] for b in edit["reply_markup"]["inline_keyboard"][0]] == [
            "pnow:" + DRAFT, "pcancel:" + DRAFT]

        h.clock.advance(5)
        post._process_button(h.token, h.channel, callback("ok:" + DRAFT, cq_id="cq2"))
        assert h.tg.methods() == ["answerCallbackQuery", "editMessageText", "answerCallbackQuery"]
        text, alert = _answers(h)[-1]
        assert text.startswith("Đã xếp lịch rồi — đăng lúc ") and alert
        assert json.loads((h.state / state_paths.PUBLISH_SCHEDULE_FILE).read_text())["last_slot"] == slot
        assert h.read_draft(DRAFT) == first
        assert h.http.sent() == [] and h.trace.names("fn") == []
    finally:
        h.__exit__()


def test_press_on_published_draft_never_publishes_again():
    h = _harness()
    try:
        h.write_draft(DRAFT, caption="x", status="published", channel_text_mid=9)
        for data in ("ok:", "pnow:", "no:", "pcancel:"):
            post._process_button(h.token, h.channel, callback(data + DRAFT))
        assert h.tg.methods() == ["answerCallbackQuery"] * 4
        assert set(_answers(h)) == {("Bài này đã xử lý rồi (published)", True)}
        assert h.read_draft(DRAFT)["status"] == "published"
        assert h.http.sent() == [] and h.trace.names("thread") == []
    finally:
        h.__exit__()


def test_publish_now_while_publishing_is_blocked():
    """publish() mat toi 180s, nut van quay -> Ong Chu bam lai. Callback thu hai
    KHONG duoc mo thread dang thu hai."""
    h = _harness()
    try:
        h.write_draft(DRAFT, caption="x", status="publishing")
        h.patch(publish_schedule, "publish_one", h.spy("publish_one", returns=(True, "x")))
        post._process_button(h.token, h.channel, callback("pnow:" + DRAFT))
        assert _answers(h) == [("Đang đăng — chờ chút", True)]
        assert h.trace.names("thread") == [] and h.trace.names("fn") == []
        assert h.read_draft(DRAFT)["status"] == "publishing"
    finally:
        h.__exit__()


def test_reject_button_falls_back_to_stripping_keyboard_when_edit_fails():
    h = _harness()
    try:
        h.write_draft(DRAFT, caption="x")
        h.tg.script("editMessageCaption", {"ok": False, "description": "can't parse entities"})
        post._process_button(h.token, h.channel, callback("no:" + DRAFT, caption="BẢN NHÁP\n\nx"))
        assert h.tg.methods() == ["answerCallbackQuery", "editMessageCaption",
                                  "editMessageReplyMarkup"]
        assert h.tg.sent("editMessageReplyMarkup")[0]["reply_markup"] == {"inline_keyboard": []}
        assert "ĐÃ BỎ — không đăng" in h.tg.sent("editMessageCaption")[0]["caption"]
        d = h.read_draft(DRAFT)
        assert d["status"] == "rejected" and d["decided_at"]
        # bo roi thi bam Duyet khong con tac dung
        post._process_button(h.token, h.channel, callback("ok:" + DRAFT))
        assert _answers(h)[-1] == ("Bài này đã xử lý rồi (rejected)", True)
        assert h.read_draft(DRAFT)["status"] == "rejected"
    finally:
        h.__exit__()


# =========================================================================
# publish() — loi giua chung (06/09 dot 2, 09/09, LOW-157)
# =========================================================================
def _album_draft(h, caption=LONG_CAPTION, **extra):
    a, b = _png(h.drafts / f"{DRAFT}.png"), _png(h.drafts / f"{DRAFT}_2.png")
    return h.write_draft(DRAFT, caption=caption, images=[a, b],
                         status=publish_schedule.SCHEDULED, publish_at=1, **extra)


def test_album_lands_then_text_fails_retry_sends_only_the_text():
    """Caption dai: album len channel, tin chu bi Telegram 400 -> publish_failed.
    Ong Chu bam lai: album KHONG duoc len lan hai (doc gia thay hai bai)."""
    h = _harness()
    try:
        _album_draft(h)
        h.tg.script("sendMessage", {"ok": False, "description": "Bad Request: can't parse entities"})
        cq = callback("pnow:" + DRAFT, text="BẢN NHÁP\n\nx")
        post._process_button(h.token, h.channel, cq)

        assert [n for n, _ in h.trace.of("http")] == ["sendMediaGroup"]
        group = h.http.sent("sendMediaGroup")[0]
        assert group["data"]["chat_id"] == h.channel and group["files"] == ["anh0", "anh1"]
        media = json.loads(group["data"]["media"])
        assert len(media[0]["caption"]) <= post.CAPTION_LIMIT and "caption" not in media[1]
        d = h.read_draft(DRAFT)
        assert d["channel_album_mid"] == 9001 and "channel_text_mid" not in d
        assert d["status"] == "publish_failed"
        assert post.already_len_channel(d)
        assert h.trace.names("fn") == [], "bai chua len du thi KHONG day sang moat"
        edit = h.tg.sent("editMessageText")[0]
        assert "Đăng lỗi: Bad Request: can&#x27;t parse entities" in edit["text"], edit["text"]
        assert edit["reply_markup"] == {"inline_keyboard": []}

        # --- bam lai: Duyet -> Dang ngay
        post._process_button(h.token, h.channel, callback("ok:" + DRAFT, cq_id="cq2"))
        post._process_button(h.token, h.channel, callback("pnow:" + DRAFT, cq_id="cq3"))
        assert [n for n, _ in h.trace.of("http")] == ["sendMediaGroup"], "album len LAN HAI"
        channel_texts = [d_ for d_ in h.tg.sent("sendMessage") if d_["chat_id"] == h.channel]
        assert len(channel_texts) >= 2                      # lan hong + lan gui lai
        d = h.read_draft(DRAFT)
        assert d["status"] == "published" and d["channel_text_mid"] and d["channel_album_mid"] == 9001
        assert h.trace.names("fn") == ["intake"]
        assert "ĐÃ ĐĂNG lên channel" in h.tg.sent("editMessageText")[-1]["text"]
    finally:
        h.__exit__()


def test_album_rejected_by_telegram_leaves_no_mark_and_no_text():
    h = _harness()
    try:
        _album_draft(h)
        h.http.script("sendMediaGroup", {"ok": False, "description": "PHOTO_INVALID_DIMENSIONS"})
        post._process_button(h.token, h.channel, callback("pnow:" + DRAFT, text="BẢN NHÁP"))
        d = h.read_draft(DRAFT)
        assert d["status"] == "publish_failed" and not post.already_len_channel(d), d
        assert [x for x in h.tg.sent("sendMessage") if x["chat_id"] == h.channel] == []
        assert "Đăng lỗi: PHOTO_INVALID_DIMENSIONS" in h.tg.sent("editMessageText")[0]["text"]
        assert h.trace.names("fn") == []
    finally:
        h.__exit__()


def test_short_caption_album_already_on_channel_sends_nothing():
    """Tien trinh chet giua publish() va mark_draft("published"): bai ket
    `publishing`, buoc cuu ha ve publish_failed, Ong Chu bam lai."""
    h = _harness()
    try:
        _album_draft(h, caption="ngan", channel_album_mid=9001)
        res = post.publish(h.token, h.channel, DRAFT)
        assert res == {"ok": True}
        assert h.http.sent() == [] and h.tg.methods() == []
    finally:
        h.__exit__()


def test_single_photo_upload_dies_midway_then_retry_skips_the_photo():
    """09/09/2026: truoc do chi album co dau — bai anh don len channel lan hai."""
    h = _harness()
    try:
        img = _png(h.drafts / f"{DRAFT}.png")
        h.write_draft(DRAFT, caption=LONG_CAPTION, image=img,
                      status=publish_schedule.SCHEDULED, publish_at=1)
        h.tg.script("sendMessage", RuntimeError("ssl eof"))
        ok, note = publish_schedule.publish_one(DRAFT)
        assert not ok and "RuntimeError" in note
        d = h.read_draft(DRAFT)
        assert d["channel_photo_mid"] == 9100 and d["status"] == "publish_failed"
        photo = h.http.sent("sendPhoto")[0]
        assert photo["data"]["chat_id"] == h.channel and len(photo["data"]["caption"]) <= 1024

        res = post.publish(h.token, h.channel, DRAFT)
        assert res["ok"] and len(h.http.sent("sendPhoto")) == 1, "anh don len LAN HAI"
        d = h.read_draft(DRAFT)
        assert d["channel_text_mid"] and d["channel_photo_mid"] == 9100
        # lan ba: ca hai phan da len -> khong gui gi
        before = len(h.trace.events)
        assert post.publish(h.token, h.channel, DRAFT) == {"ok": True}
        assert len(h.trace.events) == before
    finally:
        h.__exit__()


def test_text_only_post_is_sent_once_for_the_life_of_the_draft():
    h = _harness()
    try:
        h.write_draft(DRAFT, caption="chi co chu")
        assert post.publish(h.token, h.channel, DRAFT)["ok"]
        mid = h.read_draft(DRAFT)["channel_text_mid"]
        assert mid and h.tg.sent("sendMessage")[0]["chat_id"] == h.channel
        assert post.publish(h.token, h.channel, DRAFT) == {"ok": True}
        assert h.tg.methods() == ["sendMessage"]
        assert h.read_draft(DRAFT)["channel_text_mid"] == mid
    finally:
        h.__exit__()


def test_mark_write_failure_does_not_turn_a_published_post_into_an_error():
    h = _harness()
    try:
        h.write_draft(DRAFT, caption="chi co chu")

        def _disk_full(path, data, indent=2):
            raise OSError("No space left on device")
        h.patch(post, "_write_json", _disk_full)
        res = post.publish(h.token, h.channel, DRAFT)
        assert res["ok"] and h.tg.methods() == ["sendMessage"]
        assert "channel_text_mid" not in h.read_draft(DRAFT)
    finally:
        h.__exit__()


def test_publish_album_skips_missing_files_and_mixes_urls():
    h = _harness()
    try:
        a = _png(h.drafts / f"{DRAFT}.png")
        h.write_draft(DRAFT, caption="ngan", images=[str(h.drafts / "mat.png"),
                                                     "https://img.example/x.jpg", a])
        assert post.publish(h.token, h.channel, DRAFT)["ok"]
        sent = h.http.sent("sendMediaGroup")[0]
        media = json.loads(sent["data"]["media"])
        assert [m["media"] for m in media] == ["https://img.example/x.jpg", "attach://anh2"]
        assert media[0]["caption"] == "ngan" and "caption" not in media[1]
        assert sent["files"] == ["anh2"]
        assert h.tg.methods() == [], "caption ngan: khong co tin chu rieng"
    finally:
        h.__exit__()


# =========================================================================
# Day lai moat
# =========================================================================
def test_push_again_to_moat_runs_on_published_draft_and_clears_button():
    h = _harness()
    try:
        h.write_draft(DRAFT, caption="x", status="published")
        cq = callback("mlai:" + DRAFT, text="⚠️ Chưa đẩy được sang moat")
        post._process_button(h.token, h.channel, cq)
        assert h.trace.kinds() == ["tg:answerCallbackQuery", "thread:run", "fn:intake",
                                   "tg:editMessageText", "log:nut"], h.trace.kinds()
        assert _answers(h) == [("Đang đẩy lại…", False)]
        name, d = h.trace.of("fn")[0]
        assert d["args"] == (DRAFT,) and d["kwargs"] == {}
        edit = h.tg.sent("editMessageText")[0]
        assert edit["text"].endswith("<b>✅ Đã đẩy lại: wf_1</b>")
        assert edit["reply_markup"] == {"inline_keyboard": []}
        assert h.read_draft(DRAFT)["status"] == "published"
    finally:
        h.__exit__()


def test_single_platform_retry_uses_new_external_id_and_keeps_button_on_failure():
    """external_id PHAI khac lan truoc, khong thi moat tra workflow cu va khong
    task nao duoc tao. That bai thi giu nut de bam tiep."""
    h = _harness()
    try:
        h.write_draft(DRAFT, caption="x", status="published", moat_history=[{"a": 1}])
        h.patch(moat_publish, "intake", h.spy("intake", returns=(False, "502 <html>nginx</html>")))
        cq = callback("mlaif:" + DRAFT, text="the")
        kb = {"inline_keyboard": [[{"text": "🔁 Facebook", "callback_data": "mlaif:" + DRAFT}]]}
        cq["message"]["reply_markup"] = kb
        post._process_button(h.token, h.channel, cq)
        _, d = h.trace.of("fn")[0]
        assert d["kwargs"] == {"platforms": ["facebook_post"], "external_id": DRAFT + "-lai3"}
        edit = h.tg.sent("editMessageText")[0]
        assert "Đẩy lại vẫn lỗi: Facebook: 502 &lt;html&gt;nginx&lt;/html&gt;" in edit["text"]
        assert edit["reply_markup"] == kb
    finally:
        h.__exit__()


def test_moat_intake_crash_is_reported_not_swallowed():
    h = _harness()
    try:
        h.write_draft(DRAFT, caption="x", status="published")

        def _boom(*a, **kw):
            raise RuntimeError("moat down")
        h.patch(moat_publish, "intake", _boom)
        post._process_button(h.token, h.channel, callback("mlait:" + DRAFT, text="the"))
        assert "Đẩy lại vẫn lỗi: RuntimeError: moat down" in h.tg.sent("editMessageText")[0]["text"]
    finally:
        h.__exit__()


# =========================================================================
# imgok — Duyet anh -> task viet
# =========================================================================
def test_image_approve_creates_writer_task_under_done_parents_only():
    """Sau "Lam lai" task Dre cu co the blocked: noi vao la Miles nam todo mai.
    Chi noi voi cha DA done."""
    h = _harness()
    try:
        _sidecars(h, root="t_root")
        h.task_status.update({"t_root": "done", "t_dre1": "blocked"})
        state_paths.handoff_file(h.drafts, DRAFT).write_text("anh A1: reuters.com", encoding="utf-8")
        cq = callback("imgok:" + DRAFT, thread=DRE, caption="Album OpenAI")
        post._process_button(h.token, h.channel, cq)

        assert h.trace.kinds() == ["tg:answerCallbackQuery", "fn:create_task", "log:kanban",
                                   "tg:sendMessage", "log:route", "log:nut",
                                   "tg:editMessageCaption"], h.trace.kinds()
        assert _answers(h) == [("Đang giao cho người viết…", False)]
        task = h.created[0]
        assert task["assignee"] == "miles" and task["parent"] == ["t_root"]
        assert task["title"] == "Bai: OpenAI nop ho so IPO"
        assert "BAN GIAO TU VAI ANH" in task["body"] and "anh A1: reuters.com" in task["body"]
        assert "t_root" in task["body"].split("BAN GIAO")[1]           # nhac bang den
        w = _side(h, "writer")
        assert w["created"] is True and w["writer_task"] == "t_new1"
        topic = h.tg.sent("sendMessage")[0]
        assert topic["message_thread_id"] == MILES and "đã nhận task" in topic["text"]
        assert "chuyển từ <b>Dre</b>" in topic["text"] and "t_new1" in topic["text"]
        edit = h.tg.sent("editMessageCaption")[0]
        assert "Đã duyệt ảnh — đã gửi cho Miles viết caption (task t_new1)" in edit["caption"]
        assert edit["reply_markup"] == {"inline_keyboard": []}
    finally:
        h.__exit__()


def test_second_press_on_image_approve_reports_real_task_state_without_new_task():
    """LOW-296 / E5: bam lai nut cu KHONG tao task viet thu hai; tra loi dung
    trang thai THAT (Ong Chu tung tuong Miles treo, thuc ra da done 12h truoc)."""
    h = _harness()
    try:
        _sidecars(h)
        post._process_button(h.token, h.channel, callback("imgok:" + DRAFT, text="Album"))
        assert len(h.created) == 1
        seen = {}
        for status in ("running", "blocked", None, "", "done"):
            h.task_status["t_new1"] = status
            post._process_button(h.token, h.channel, callback("imgok:" + DRAFT, text="Album"))
            seen[status] = h.tg.sent("editMessageText")[-1]["text"]
            assert _answers(h)[-1] == ("Đã duyệt trước đó", False)
        assert len(h.created) == 1, "bam lai KHONG duoc tao task viet thu hai"
        assert "Miles đang viết (task t_new1)" in seen["running"]
        assert "Miles dừng (blocked): thieu anh that" in seen["blocked"]
        assert "Không đọc được kanban" in seen[None] and "t_new1" in seen[None]
        assert "Đã duyệt rồi — bài đang được viết" in seen[""]
        assert "Bài đã viết xong (task t_new1)" in seen["done"]
        assert len(h.tg.sent("sendMessage")) == 1, "chi bao topic nguoi viet MOT lan"
    finally:
        h.__exit__()


def test_done_task_answer_links_to_progress_message_when_known():
    h = _harness()
    try:
        _sidecars(h)
        w = _side(h, "writer")
        w.update(created=True, writer_task="t_w9")
        (h.drafts / f"{DRAFT}.writer.json").write_text(json.dumps(w), encoding="utf-8")
        (h.state / state_paths.TASK_RESULT_MESSAGES_FILE).write_text(json.dumps(
            {"t_w9": {"chat": "-1001234", "thread": MILES, "mid": 321}}), encoding="utf-8")
        post._process_button(h.token, h.channel, callback("imgok:" + DRAFT, text="Album"))
        assert f"xem tại https://t.me/c/1234/{MILES}/321" in h.tg.sent("editMessageText")[0]["text"]
        assert h.created == []
    finally:
        h.__exit__()


def test_unreadable_kanban_refuses_to_create_orphan_writer_task():
    """C-r2-3: kanban hong luc bam Duyet -> task Miles khong cha (mat ban giao
    cua Dre) ma note van "✅". Phai noi that va de bam lai."""
    h = _harness()
    try:
        _sidecars(h, root="t_root")
        h.task_status["t_root"] = None
        post._process_button(h.token, h.channel, callback("imgok:" + DRAFT, text="Album"))
        assert h.created == []
        assert _side(h, "writer")["created"] is False
        assert "không đọc được kanban để nối thẻ cha" in h.tg.sent("editMessageText")[0]["text"]
        assert h.tg.sent("sendMessage") == []
        # kanban song lai: bam lai thi tao duoc
        h.task_status["t_root"] = "done"
        post._process_button(h.token, h.channel, callback("imgok:" + DRAFT, text="Album"))
        assert len(h.created) == 1 and _side(h, "writer")["created"] is True
    finally:
        h.__exit__()


def test_writer_task_creation_error_keeps_draft_approvable():
    h = _harness()
    try:
        _sidecars(h, writer="jika")
        (h.tmp / "home" / "profiles" / "jika").rmdir()
        post._process_button(h.token, h.channel, callback("imgok:" + DRAFT, text="Album"))
        text = h.tg.sent("editMessageText")[0]["text"]
        assert "Duyệt ok nhưng tạo task viết lỗi" in text and "jika" in text
        assert h.created == [] and _side(h, "writer")["created"] is False
    finally:
        h.__exit__()


def test_image_approve_without_writer_sidecar_says_so():
    h = _harness()
    try:
        post._process_button(h.token, h.channel, callback("imgok:" + DRAFT, text="Album"))
        assert _answers(h) == [("Thiếu thông tin bài", True)]
        assert "Không thấy thông tin bài (writer sidecar)" in h.tg.sent("editMessageText")[0]["text"]
        assert h.created == []
    finally:
        h.__exit__()


def test_low123_shorter_queue_writer_gets_the_task_with_retargeted_commands():
    h = _harness()
    try:
        _sidecars(h, writer="miles", brand="dcgr")
        h.patch(hermes_adapter, "writer_queue",
                lambda slugs: {"miles": (3, 100.0), "jika": (0, 50.0)})
        post._process_button(h.token, h.channel, callback("imgok:" + DRAFT, text="Album"))
        task = h.created[0]
        assert task["assignee"] == "jika"
        assert "venv/bin/python jika_prepare.py" in task["body"]
        assert "venv/bin/python jika_submit.py" in task["body"] and "miles_" not in task["body"]
        w = _side(h, "writer")
        assert w["writer_role"] == "jika" and "jika_submit.py" in w["body"]
        assert h.tg.sent("sendMessage")[0]["message_thread_id"] == JIKA
        assert "gửi cho Jika" in h.tg.sent("editMessageText")[0]["text"]
        assert any("assigned jika instead of miles" in t for t in h.logs("nut"))
    finally:
        h.__exit__()


def test_unreadable_queue_keeps_tentative_writer():
    h = _harness()
    try:
        _sidecars(h, writer="jika", brand="dcgr")          # writer_queue tra None
        post._process_button(h.token, h.channel, callback("imgok:" + DRAFT, text="Album"))
        assert h.created[0]["assignee"] == "jika"
    finally:
        h.__exit__()


# =========================================================================
# imgno — Bo han tin
# =========================================================================
def test_drop_news_blocks_later_approval_and_frees_used_images():
    h = _harness()
    try:
        _sidecars(h)
        post._process_button(h.token, h.channel, callback("imgno:" + DRAFT, text="Album"))
        assert _side(h, "writer")["created"] == "rejected"
        assert [d["args"] for n, d in h.trace.of("fn") if n == "remove_used"] == [(DRAFT,)]
        assert "Đã bỏ hẳn tin" in h.tg.sent("editMessageText")[0]["text"]
        # bam Duyet tren tin cu: khong sinh task viet cho tin da giet
        post._process_button(h.token, h.channel, callback("imgok:" + DRAFT, text="Album"))
        assert h.created == []
        assert _answers(h)[-1] == ("Đã bỏ hẳn", True)
        assert "đã bỏ hẳn trước đó" in h.tg.sent("editMessageText")[-1]["text"]
    finally:
        h.__exit__()


def test_drop_after_approval_is_refused_to_avoid_contradicting_state():
    h = _harness()
    try:
        _sidecars(h)
        post._process_button(h.token, h.channel, callback("imgok:" + DRAFT, text="Album"))
        post._process_button(h.token, h.channel, callback("imgno:" + DRAFT, text="Album"))
        w = _side(h, "writer")
        assert w["created"] is True and w["writer_task"] == "t_new1"
        assert _answers(h)[-1] == ("Đã duyệt trước đó, không bỏ", True)
        assert "không bỏ hẳn được nữa" in h.tg.sent("editMessageText")[-1]["text"]
        assert "remove_used" not in h.trace.names("fn"), "anh cua bai dang viet phai con trong so"
    finally:
        h.__exit__()


def test_drop_that_cannot_be_persisted_tells_the_boss_to_press_again():
    h = _harness()
    try:
        _sidecars(h)

        def _readonly(path, data, indent=2):
            raise PermissionError("read-only")
        h.patch(post, "_write_json", _readonly)
        post._process_button(h.token, h.channel, callback("imgno:" + DRAFT, text="Album"))
        text = h.tg.sent("editMessageText")[0]["text"]
        assert "KHÔNG ghi được trạng thái (PermissionError)" in text
        assert _side(h, "writer")["created"] is False
    finally:
        h.__exit__()


# =========================================================================
# LOW-280 — Gui Kite
# =========================================================================
def _manifest(h, usable):
    wd = state_paths.workdir(h.state, DRAFT)
    wd.mkdir(parents=True)
    images = [{"id": f"A{i}", "uses": True, "relevant": True} for i in range(1, usable + 1)]
    images.append({"id": "A9", "uses": False})
    (wd / state_paths.MANIFEST_FILE).write_text(json.dumps(
        {"version": post.schema.VERSION_MANIFEST, "images": images, "usable_count": usable,
         "min_images": 8, "base_min_images": 5}), encoding="utf-8")


def test_send_to_kite_moves_the_draft_so_only_one_image_role_owns_it():
    h = _harness()
    try:
        _sidecars(h, root="t_root", dre_task="t_dre1")
        _manifest(h, 2)
        cq = callback("imgkite:" + DRAFT, thread=DRE, text="Album thieu anh")
        post._process_button(h.token, h.channel, cq)

        assert h.trace.kinds() == ["tg:answerCallbackQuery", "fn:create_task", "log:kanban",
                                   "fn:blackboard", "tg:sendMessage", "log:route", "log:nut",
                                   "tg:editMessageText"], h.trace.kinds()
        task = h.created[0]
        assert task["assignee"] == "kite" and task["parent"] == "t_root"
        assert task["title"] == "Carousel deck: OpenAI nop ho so IPO"
        assert "== CHUYEN TU Dre ==" in task["body"]
        assert "2 anh THAT dung duoc (ma: A1, A2" in task["body"]
        assert "https://a.b/c" in task["body"] and "OpenAI nop S-1" in task["body"]
        im = _side(h, "img")
        assert (im["image_role"], im["transferred_from"], im["kite_task_id"]) == ("kite", "dre", "t_new1")
        assert im["carousel"] is True and im["body"] == task["body"]
        w = _side(h, "writer")
        assert w["dre_task"] == "t_new1" and w["dre_task_before_kite"] == "t_dre1"
        _, bb = [x for x in h.trace.of("fn") if x[0] == "blackboard"][0]
        assert bb["args"][:2] == (DRAFT, "kite_transfer")
        assert bb["args"][2]["transferred_from"] == "dre" and bb["args"][2]["usable_image_ids"] == ["A1", "A2"]
        topic = h.tg.sent("sendMessage")[0]
        assert topic["message_thread_id"] == KITE and "chuyển từ <b>Dre</b>" in topic["text"]
        assert "Đã giao Kite vẽ vector (task t_new1) — Dre dừng bộ này" in h.tg.sent("editMessageText")[0]["text"]

        # bam lan hai (tin cu con nut): khong co task Kite thu hai
        post._process_button(h.token, h.channel, callback("imgkite:" + DRAFT, text="Album"))
        assert len(h.created) == 1
        assert _answers(h)[-1] == ("↪️ Đã chuyển Kite trước đó (task t_new1)", False)

        # "Lam lai" sau khi chuyen: viec ve Kite, KHONG ve Dre
        note, rid = post._hand_redo(DRAFT)
        assert h.created[-1]["assignee"] == "kite" and "Kite" in note and rid == "t_new2"
        assert _side(h, "writer")["dre_task"] == "t_new2"
    finally:
        h.__exit__()


def test_send_to_kite_with_no_usable_image_tells_kite_to_search_again():
    h = _harness()
    try:
        _sidecars(h, image_role="ethan", carousel=False)
        post._process_button(h.token, h.channel, callback("imgkite:" + DRAFT, text="Album"))
        body = h.created[0]["body"]
        assert "== CHUYEN TU Ethan ==" in body and "KHONG ve hero vector" in body
        assert h.created[0]["parent"] is None
        assert "blackboard" not in h.trace.names("fn"), "khong co the goc thi khong ghi bang den"
        assert "Ethan dừng bộ này" in h.tg.sent("editMessageText")[0]["text"]
    finally:
        h.__exit__()


def test_send_to_kite_failure_leaves_old_role_in_charge():
    h = _harness()
    try:
        _sidecars(h, root="t_root")
        (h.tmp / "home" / "profiles" / "kite").rmdir()
        before = _side(h, "img")
        post._process_button(h.token, h.channel, callback("imgkite:" + DRAFT, text="Album"))
        assert "Chuyển Kite lỗi" in h.tg.sent("editMessageText")[0]["text"]
        assert _side(h, "img") == before and _side(h, "writer")["dre_task"] == "t_dre1"
        assert h.tg.sent("sendMessage") == [] and h.created == []
    finally:
        h.__exit__()


def test_kite_button_without_image_sidecar():
    h = _harness()
    try:
        post._process_button(h.token, h.channel, callback("imgkite:" + DRAFT, text="Album"))
        assert _answers(h) == [("⚠️ Không thấy thông tin task ảnh", True)]
        assert h.created == []
    finally:
        h.__exit__()


def test_lower_floor_without_manifest_does_not_pretend():
    h = _harness()
    try:
        _sidecars(h)
        post._process_button(h.token, h.channel, callback("imgtiep:" + DRAFT, text="Album"))
        assert _answers(h) == [("Thiếu manifest.json", True)]
        assert "chưa hạ sàn được" in h.tg.sent("editMessageText")[0]["text"]
    finally:
        h.__exit__()


# =========================================================================
# Lam lai — hoi ly do, nuot cau tra loi, het han
# =========================================================================
def _press_redo(h, draft_id=DRAFT, question_mid=7000, thread=DRE, cq_id="cq1"):
    h.tg.script("sendMessage", {"ok": True, "result": {"message_id": question_mid}})
    post._process_button(h.token, h.channel,
                         callback("imgredo:" + draft_id, thread=thread, text="Album", cq_id=cq_id))


def test_redo_asks_for_reason_then_hands_task_with_the_boss_words():
    """04/09/2026: chi bam "lam lai" thi vai khong biet sua cho nao."""
    h = _harness()
    try:
        _boss_only(h)
        h.fake_time(post)
        _sidecars(h, root="t_root")
        _press_redo(h)
        assert h.created == [], "KHONG giao ngay"
        assert h.tg.methods() == ["answerCallbackQuery", "sendMessage", "editMessageText"]
        ask = h.tg.sent("sendMessage")[0]
        assert ask["reply_markup"] == {"force_reply": True, "selective": False}
        assert ask["message_thread_id"] == DRE and "số slide: lý do" in ask["text"]
        assert "Chờ lý do làm lại (lần 1)" in h.tg.sent("editMessageText")[0]["text"]
        rec = _redo_wait(h)[DRAFT]
        assert rec["thread_id"] == DRE and rec["question_mid"] == 7000 and rec["ts"] == h.clock.now
        assert [d["args"] for n, d in h.trace.of("fn") if n == "remove_used"] == [(DRAFT,)]

        reply = message(801, "Làm lại slide 3, 6: chart bị cắt", thread=DRE, user=BOSS, reply_to=7000)
        assert post._label_reason_redo(h.token, h.group, reply, DRE, reply["text"]) is True
        assert _redo_wait(h) == {}
        task = h.created[0]
        assert task["assignee"] == "dre" and task["parent"] == "t_root"
        assert task["title"] == "Carousel (lam lai): OpenAI nop ho so IPO"
        assert "BODY-ANH-GOC" in task["body"] and "== LAM LAI (lan 1) ==" in task["body"]
        assert "SLIDE:  3, 6" in task["body"] and "LY DO:  chart bị cắt" in task["body"]
        im = _side(h, "img")
        assert im["remakes"] == 1 and im["last_task"] == "t_new1"
        assert im["redo_reasons"] == [{"attempt": 1, "slide": "3, 6", "reason": "chart bị cắt"}]
        assert _side(h, "writer")["dre_task"] == "t_new1"
        _, bb = [x for x in h.trace.of("fn") if x[0] == "blackboard"][0]
        assert bb["args"][1] == "redo" and bb["args"][2]["previous_task"] == "t_dre1"
        told = h.tg.sent("sendMessage")[-1]
        assert told["reply_to_message_id"] == 801 and told["message_thread_id"] == DRE
        assert "Đã giao làm lại slide 3, 6 (lần 1) — Dre — lý do: chart bị cắt (task t_new1)" in told["text"]
    finally:
        h.__exit__()


def test_redo_reason_gate_ignores_strangers_and_loose_messages():
    """05/09/2026: moi chu go trong topic suot 10 phut deu bi nuot lam ly do."""
    h = _harness()
    try:
        _boss_only(h)
        _sidecars(h)
        _press_redo(h)
        waiting = _redo_wait(h)
        stranger = message(802, "4: xau", thread=DRE, user=666, reply_to=7000)
        loose = message(803, "Dre oi hom nay sao roi", thread=DRE, user=BOSS)
        other = message(804, "4: xau", thread=DRE, user=BOSS, reply_to=6999)
        other_topic = message(805, "4: xau", thread=MILES, user=BOSS, reply_to=7000)
        for m, tid in ((stranger, DRE), (loose, DRE), (other, DRE), (other_topic, MILES)):
            assert post._label_reason_redo(h.token, h.group, m, tid, m["text"]) is False, m
        assert _redo_wait(h) == waiting and h.created == []
        assert h.trace.names("bg") == []
    finally:
        h.__exit__()


def test_second_redo_in_same_topic_is_refused_and_keeps_its_buttons():
    """06/09/2026: bam Lam lai bai B khi topic dang cho ly do bai A tung ghi de
    IM LANG ban ghi cua A."""
    h = _harness()
    try:
        _sidecars(h)
        _sidecars(h, "bai-b")
        _press_redo(h)
        n = len(h.tg.methods())
        post._process_button(h.token, h.channel,
                             callback("imgredo:bai-b", thread=DRE, text="Album B", cq_id="cq2"))
        assert h.tg.methods()[n:] == ["answerCallbackQuery"], "KHONG sua tin, giu nguyen nut"
        text, alert = _answers(h)[-1]
        assert text.startswith("Đang chờ lý do bài: OpenAI nop ho so IPO") and alert
        assert list(_redo_wait(h)) == [DRAFT]
        # topic KHAC thi van nhan
        h.tg.script("sendMessage", {"ok": True, "result": {"message_id": 7001}})
        post._process_button(h.token, h.channel,
                             callback("imgredo:bai-b", thread=KITE, text="Album B", cq_id="cq3"))
        assert sorted(_redo_wait(h)) == sorted([DRAFT, "bai-b"])
    finally:
        h.__exit__()


def test_redo_cancel_and_bare_redo_words():
    h = _harness()
    try:
        _sidecars(h, carousel=False, image_role="ethan")
        _press_redo(h)
        assert "Trả lời <b>lý do</b> ảnh chưa đạt" in h.tg.sent("sendMessage")[0]["text"]
        m = message(810, "Hủy", thread=DRE, user=BOSS, reply_to=7000)
        assert post._label_reason_redo(h.token, h.group, m, DRE, m["text"]) is True
        assert h.created == [] and "remakes" not in _side(h, "img")
        assert "Đã huỷ làm lại — giữ nguyên ảnh hiện tại" in h.tg.sent("sendMessage")[-1]["text"]

        _press_redo(h, question_mid=7005, cq_id="cq2")
        m = message(811, "làm lại", thread=DRE, user=BOSS, reply_to=7005)
        assert post._label_reason_redo(h.token, h.group, m, DRE, m["text"]) is True
        assert h.created[0]["assignee"] == "ethan"
        assert h.created[0]["title"].startswith("Anh (lam lai): ")
        assert "khong neu ly do cu the" in h.created[0]["body"]
        assert "redo_reasons" not in _side(h, "img")
        assert "Ethan sẽ dựng ảnh khác (task t_new1)" in h.tg.sent("sendMessage")[-1]["text"]
    finally:
        h.__exit__()


def test_redo_whole_set_reason():
    h = _harness()
    try:
        _sidecars(h)
        wd = state_paths.workdir(h.state, DRAFT)
        wd.mkdir(parents=True)
        (wd / "spec.json").write_text(json.dumps(
            {"cover": {"image": "A1"}, "slides": [{"image": "A2"}, {"stack": ["A3", "A4"]}]}),
            encoding="utf-8")
        _press_redo(h)
        m = message(812, "tất cả: màu xấu quá", thread=DRE, user=BOSS, reply_to=7000)
        assert post._label_reason_redo(h.token, h.group, m, DRE, m["text"]) is True
        assert "SLIDE:  CA BO" in h.created[0]["body"]
        assert "Đã giao làm lại cả bộ (lần 1)" in h.tg.sent("sendMessage")[-1]["text"]
        assert _side(h, "img")["forbidden_slide_images"] == {}       # khong co anh goc de chup dHash
    finally:
        h.__exit__()


def test_redo_times_out_into_old_style_task_exactly_once():
    h = _harness()
    try:
        h.fake_time(post)
        _sidecars(h)
        _press_redo(h)
        n = len(h.trace.events)
        h.clock.advance(post.REDO_LIMIT - 1)
        post._redo_all_done_limit(h.token, h.group)
        assert len(h.trace.events) == n and list(_redo_wait(h)) == [DRAFT]

        h.clock.advance(2)
        post._redo_all_done_limit(h.token, h.group)
        assert _redo_wait(h) == {}
        name, bg = h.trace.of("bg")[-1]
        assert (name, bg["fn"], bg["thread_id"]) == ("lamlai-han", "_hand_all_done_limit", DRE)
        assert len(h.created) == 1 and "khong neu ly do cu the" in h.created[0]["body"]
        told = h.tg.sent("sendMessage")[-1]
        assert told["message_thread_id"] == DRE
        assert told["text"].startswith("⏱ Hết 10 phút chưa nêu lý do — 🔄 Đã giao làm lại (lần 1)")
        # vong poll ke tiep khong giao lan hai; tra loi muon khong con bi nuot
        post._redo_all_done_limit(h.token, h.group)
        assert len(h.created) == 1
        late = message(820, "4: muon", thread=DRE, user=BOSS, reply_to=7000)
        assert post._label_reason_redo(h.token, h.group, late, DRE, late["text"]) is False
    finally:
        h.__exit__()


def test_expired_wait_of_another_draft_does_not_block_a_new_redo():
    h = _harness()
    try:
        h.fake_time(post)
        _sidecars(h)
        _sidecars(h, "bai-b")
        _press_redo(h)
        h.clock.advance(post.REDO_LIMIT + 5)                   # vong poll chua kip don
        h.tg.script("sendMessage", {"ok": True, "result": {"message_id": 7002}})
        post._process_button(h.token, h.channel,
                             callback("imgredo:bai-b", thread=DRE, text="Album B", cq_id="cq2"))
        assert _redo_wait(h)["bai-b"]["question_mid"] == 7002
    finally:
        h.__exit__()


def test_legacy_wait_record_keyed_by_thread_survives_restart():
    """Ban ghi truoc 06/09 (khoa la thread_id, khong co question_mid): reply toi
    mot tin cua bot van duoc nhan khi topic chi cho DUY NHAT mot bai; `ts` rac
    tinh la qua han."""
    h = _harness()
    try:
        _sidecars(h)
        (h.state / state_paths.REDO_WAITING_FILE).write_text(json.dumps(
            {str(DRE): {"draft_id": DRAFT, "ts": "rac"}, "x": "khong phai dict", "y": {}}),
            encoding="utf-8")
        assert post._load_redo_wait() == {DRAFT: {"draft_id": DRAFT, "ts": "rac", "thread_id": DRE}}
        m = message(830, "4: chart bi cat", thread=DRE, user=BOSS, reply_to=555)
        assert post._label_reason_redo(h.token, h.group, m, DRE, m["text"]) is True
        assert "SLIDE:  4" in h.created[0]["body"] and _redo_wait(h) == {}

        (h.state / state_paths.REDO_WAITING_FILE).write_text(json.dumps(
            {str(DRE): {"draft_id": DRAFT, "ts": "rac"}}), encoding="utf-8")
        post._redo_all_done_limit(h.token, h.group)
        assert len(h.created) == 2 and _redo_wait(h) == {}
    finally:
        h.__exit__()


def test_redo_without_image_sidecar():
    h = _harness()
    try:
        post._process_button(h.token, h.channel, callback("imgredo:" + DRAFT, thread=DRE, text="A"))
        assert _answers(h) == [("Thiếu thông tin ảnh", True)]
        assert _redo_wait(h) == {} and "remove_used" not in h.trace.names("fn")
        assert post._hand_redo(DRAFT) == ("⚠️ Không thấy thông tin task ảnh để làm lại", None)
    finally:
        h.__exit__()


def test_redo_task_creation_error_is_told_and_counter_not_bumped():
    h = _harness()
    try:
        _sidecars(h)
        (h.tmp / "home" / "profiles" / "dre").rmdir()
        note, rid = post._hand_redo(DRAFT, "4", "xau")
        assert rid is None and note.startswith("⚠️ Làm lại lỗi: ")
        assert "remakes" not in _side(h, "img")
    finally:
        h.__exit__()


# =========================================================================
# LOW-361 — Lam lai phai chay lai khau tim anh, TRUOC khi giao task
# =========================================================================
def test_low361_redo_refreshes_images_before_creating_task():
    h = _harness()
    try:
        _sidecars(h)
        note, rid = post._hand_redo(DRAFT, "4", "bang benchmark cu")
        names = h.trace.names("fn")
        assert "refresh_images" in names and "create_task" in names, names
        assert names.index("refresh_images") < names.index("create_task"), names
        assert rid and "đã tìm lại ảnh bằng code mới" in note, note
        # het han 10 phut / khong ly do: cung di qua tim lai anh
        post._hand_redo(DRAFT)
        assert h.trace.names("fn").count("refresh_images") == 2
    finally:
        h.__exit__()


def test_low361_refresh_warning_still_hands_task_and_is_told():
    h = _harness()
    try:
        _sidecars(h)
        h.patch(post, "_refresh_images_for_redo", h.spy("refresh_images", returns="⚠️ Tìm lại ảnh lỗi (mã 1, xem prepare.log)"))
        note, rid = post._hand_redo(DRAFT)
        assert rid and "⚠️ Tìm lại ảnh lỗi" in note and "đã tìm lại ảnh" not in note, note
    finally:
        h.__exit__()


def test_low361_refresh_command_and_live_lock(tmp_path=None):
    import subprocess
    tmp = Path(tempfile.mkdtemp())
    saved = (post.STATE_DIR, subprocess.run)
    seen = {}

    def fake_run(cmd, **kw):
        seen["cmd"] = cmd
        return subprocess.CompletedProcess(cmd, 0)
    try:
        post.STATE_DIR = tmp
        subprocess.run = fake_run
        assert post._refresh_images_for_redo(DRAFT) == ""
        assert seen["cmd"][2:] == [DRAFT, "--lam-moi", "--im", "--skip-route"], seen["cmd"]
        # engine khac dang giu draft (pid song) -> khong chay, bao lai
        seen.clear()
        wd = post.state_paths.workdir(tmp, DRAFT)
        (wd / post.state_paths.RUNNING_PID_FILE).write_text(str(os.getpid()))
        msg = post._refresh_images_for_redo(DRAFT)
        assert "Engine khác đang chuẩn bị" in msg and "cmd" not in seen, msg
    finally:
        post.STATE_DIR, subprocess.run = saved


def test_low361_image_prepare_skip_route_flag():
    import image_prepare
    src = Path(image_prepare.__file__).read_text(encoding="utf-8")
    assert '"--skip-route"' in src
    assert "sau_chuan_bi=None if a.skip_route else route_missing_images.after_prepare" in src


# =========================================================================
# LOW-134 — tin nut khong len, duyet bang reply vao album
# =========================================================================
def test_low134_reply_approval_creates_task_and_strips_stale_button():
    h = _harness()
    try:
        _sidecars(h, brand="dcgr")
        sent = h.state / "telegram_sent"
        sent.mkdir()
        # so that: dong dung nam TRUOC, theo sau la dong rac / dong thieu truong
        (sent / "dre.jsonl").write_text(
            json.dumps({"message_id": 1576, "message_ids": [1570, 1576],
                        "files": [f"/x/drafts/{DRAFT}.png", f"/x/drafts/{DRAFT}_2.png"],
                        "button_message_id": 1580}) + "\n"
            + json.dumps({"message_id": "x"}) + "\nkhong phai json\n", encoding="utf-8")
        m = message(1700, "Duyệt, gửi cho Jika", thread=DRE, user=BOSS, reply_to=1570)
        assert post.handle_reply_approval(h.token, h.group, m, DRE, m["text"]) is True

        assert h.created[0]["assignee"] == "jika" and "jika_submit.py" in h.created[0]["body"]
        assert h.tg.sent("answerCallbackQuery") == [], "khong co callback de tra loi"
        methods = h.tg.methods()
        assert methods == ["sendMessage", "sendMessage", "editMessageReplyMarkup"], methods
        told = h.tg.sent("sendMessage")[1]
        assert told["reply_to_message_id"] == 1700 and told["message_thread_id"] == DRE
        assert "đã gửi cho Jika viết caption (task t_new1)" in told["text"]
        strip = h.tg.sent("editMessageReplyMarkup")[0]
        assert strip["message_id"] == 1580 and strip["reply_markup"] == {"inline_keyboard": []}

        # reply lan hai (hoac bam nut cu): khong co task thu hai, khong go nut lan nua
        m2 = message(1701, "duyệt", thread=DRE, user=BOSS, reply_to=1580)
        assert post.handle_reply_approval(h.token, h.group, m2, DRE, m2["text"]) is True
        assert len(h.created) == 1 and len(h.tg.sent("editMessageReplyMarkup")) == 1
        assert "Bài đã viết xong" in h.tg.sent("sendMessage")[-1]["text"]
    finally:
        h.__exit__()


def test_low134_reply_that_is_not_an_approval_falls_through_untouched():
    h = _harness()
    try:
        _sidecars(h)
        loose = message(1702, "gửi cho Miles", thread=DRE, user=BOSS)
        chat = message(1703, "anh nay dep", thread=DRE, user=BOSS, reply_to=1570)
        unknown = message(1704, "duyệt", thread=DRE, user=BOSS, reply_to=4242)
        for m in (loose, chat, unknown):
            assert post.handle_reply_approval(h.token, h.group, m, DRE, m["text"]) is False
        assert h.trace.events == []
    finally:
        h.__exit__()


# =========================================================================
# Day ban nhap vao hang duyet
# =========================================================================
def test_preview_multi_image_draft_sends_only_the_hero():
    """Ong Chu 22/09/2026: bo anh da duyet o buoc anh — the duyet caption chi kem
    ANH BIA (anh dau ton tai), khong gui lai ca album; draft van giu du anh de dang."""
    h = _harness()
    try:
        hero = _png(h.drafts / f"{DRAFT}.png")
        second = _png(h.drafts / f"{DRAFT}_2.png")
        h.write_draft(DRAFT, caption="cap", images=[str(h.drafts / "mat.png"), hero, second])
        seen = []

        def _upload(token, method, data, open_files, timeout=None):
            handles = open_files()
            seen.append((method, data, [v[0] for v in handles.values()]))
            for v in handles.values():
                v[1].close()
            return {"ok": True, "result": {"message_id": 11}}
        h.patch(post, "call_upload", _upload)
        res = post.draft_push(h.token, h.group, DRAFT, thread_id=MILES)
        assert res["ok"]
        (method, data, names), = seen
        assert method == "sendPhoto" and [Path(n).stem for n in names] == [DRAFT]
        assert data["message_thread_id"] == MILES
        assert "khi đăng sẽ lên đủ 3 ảnh" in data["caption"]
        assert json.loads(data["reply_markup"])["inline_keyboard"][0][0]["callback_data"] == "ok:" + DRAFT
        assert h.tg.sent("sendMessage") == []
    finally:
        h.__exit__()


def test_preview_multi_image_draft_with_no_file_says_so_on_the_card():
    """Khong con tep anh nao tren may: KHONG nuot loi, the chu van co nut duyet."""
    h = _harness()
    try:
        h.write_draft(DRAFT, caption="cap", images=[str(h.drafts / "mat.png"), "https://img.example/x.jpg"])
        h.patch(post, "call_upload", h.spy("call_upload", returns={"ok": True}))
        post.draft_push(h.token, h.group, DRAFT, thread_id=MILES)
        card = h.tg.sent("sendMessage")[0]
        assert "Không thấy tệp ảnh nào" in card["text"]
        assert card["reply_markup"]["inline_keyboard"][0][0]["callback_data"] == "ok:" + DRAFT
        assert h.trace.kinds() == ["tg:sendMessage"]
    finally:
        h.__exit__()


def test_preview_album_with_no_existing_file_never_calls_telegram_upload():
    h = _harness()
    try:
        h.patch(post, "call_upload", h.spy("call_upload", returns={"ok": True}))
        res = post._send_media_group(h.token, h.group, [str(h.drafts / "mat.png")])
        assert res == {"ok": False, "description": "khong co anh nao ton tai"}
        assert h.trace.events == []
    finally:
        h.__exit__()


def test_text_only_draft_card_carries_the_buttons():
    h = _harness()
    try:
        h.write_draft(DRAFT, caption="cap", image=str(h.drafts / "mat.png"))
        post.draft_push(h.token, h.group, DRAFT)
        card = h.tg.sent("sendMessage")[0]
        assert card["text"] == "<b>BẢN NHÁP</b>\n\ncap" and "message_thread_id" not in card
        assert [b["callback_data"] for b in card["reply_markup"]["inline_keyboard"][0]] == [
            "ok:" + DRAFT, "no:" + DRAFT]
    finally:
        h.__exit__()


def test_low296_old_card_removal_falls_back_to_one_by_one():
    h = _harness()
    try:
        h.tg.script("deleteMessages", {"ok": False, "description": "message can't be deleted"})
        h.tg.script("deleteMessage", {"ok": True}, {"ok": False})
        assert post.delete_messages(h.token, h.group, [11, None, "12"]) == 1
        assert h.tg.methods() == ["deleteMessages", "deleteMessage", "deleteMessage"]
        assert h.tg.sent("deleteMessages")[0]["message_ids"] == [11, 12]
        assert post.delete_messages(h.token, h.group, [None, 0]) == 0
        assert len(h.tg.methods()) == 3
    finally:
        h.__exit__()


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
