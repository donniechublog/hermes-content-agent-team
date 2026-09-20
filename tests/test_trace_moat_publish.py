#!/usr/bin/env python3
"""LOW-311 — luoi doi chieu vet cho moat_publish: day bai sang moat (`intake`),
hang doi day lai (`bottom_again`), hoi trang thai (`poll`), bao ve Telegram
(`report_card`, `_notify`).

Moi kich ban khang dinh ba thu: vet goi ra ngoai (HTTP toi moat + Bot API, thu
tu + tham so), tep state sau cung (draft, hang doi, spool), va dong bao cho Ong
Chu. Canh HTTP la `httpx.MockTransport` ghi moi request vao `h.trace`:
    ("http", "POST /publish-intake", body=..., key=...)   -- moat
    ("tg",   "sendMessage", token=..., **payload)          -- Bot API
nen `h.tg.sent()/texts()` cua harness dung duoc nguyen.

Kich ban co chu "PIN" trong docstring ghi lai HANH VI HIEN TAI ma toi nghi la
loi san xuat (xem bao cao LOW-311) — sua loi thi sua luon test do.

Chay:  python tests/test_trace_moat_publish.py
"""
import base64
import io
import json
import os
import sys
import types
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import env_load                        # noqa: E402
import moat_publish as mp              # noqa: E402
import publish                         # noqa: E402
from trace_harness import Harness, run_tests  # noqa: E402

MOAT = "http://moat.test"
WRITER = 88                            # topic writer trong topics.json gia
BLOG, DCGR = "donniechublog", "dcgr"


class FakeServer:
    """Moat + Bot API gia. `script(route, r1, r2...)` xep hang cau tra loi cho
    route ("POST /publish-intake", "GET /publish-intake/<ref>", "tg sendMessage");
    het hang thi ve mac dinh. Cau tra loi: httpx.Response | Exception | callable
    (request, body) -> Response."""

    def __init__(self, h):
        self.h = h
        self._queue = {}
        self._mid = 5000

    def script(self, route, *responses):
        self._queue.setdefault(route, []).extend(responses)
        return self

    def _answer(self, route, request, body, default):
        q = self._queue.get(route)
        r = q.pop(0) if q else default
        if isinstance(r, BaseException):
            raise r
        return r(request, body) if callable(r) else r

    def __call__(self, request):
        body = json.loads(request.content.decode("utf-8")) if request.content else None
        if request.url.host == "api.telegram.org":
            _, bot, method = request.url.path.split("/")
            self.h.trace.add("tg", method, token=bot[3:], **(body or {}))
            self._mid += 1
            return self._answer("tg " + method, request, body, httpx.Response(
                200, json={"ok": True, "result": {"message_id": self._mid}}))
        assert str(request.url).startswith(MOAT), request.url
        path = request.url.path
        self.h.trace.add("http", request.method + " " + path, body=body,
                         key=request.headers.get("X-API-Key"))
        if request.method == "POST":
            default = httpx.Response(200, json={
                "workflowId": "wf-" + body["externalId"],
                "externalId": body["externalId"],
                "tasks": [{"id": "t-" + p} for p in body["platforms"]]})
        else:
            default = httpx.Response(200, json={"tasks": []})
        return self._answer(request.method + " " + path, request, body, default)


def _harness(**env):
    h = Harness(mp, publish)
    h.__enter__()
    h.server = FakeServer(h)
    transport = httpx.MockTransport(h.server)

    def client(*a, **kw):
        kw["transport"] = transport
        return httpx.Client(*a, **kw)

    fake = types.SimpleNamespace(**{k: getattr(httpx, k) for k in dir(httpx)
                                    if not k.startswith("_")})
    fake.Client = client
    h.patch(mp, "httpx", fake)
    h.patch(publish, "httpx", fake)
    # Khong doc tep secret that (~/.hermes/.env): moi cau hinh di qua patch_env.
    h.patch(env_load, "load", lambda *a: None)
    cfg = dict(MOAT_BASE_URL=MOAT + "/", MOAT_PUBLISH_KEY="key-blog",
               MOAT_PUBLISH_KEY_DCGR="key-dcgr", TELEGRAM_BOT_TOKEN="TOK",
               TELEGRAM_GROUP_ID="-1001", TELEGRAM_CHANNEL_ID="-1002",
               BRAND=None, CT_BRAND=None)
    cfg.update(env)
    h.patch_env(os.environ, **cfg)
    h.topics({"writer": WRITER})
    h.fake_time(mp)

    def _print(*a, **kw):
        h.trace.add("print", " ".join(str(x) for x in a))
    h.patch(mp, "print", _print)
    h.patch(publish, "print", _print)
    return h


def _image(h, name="card.png", data=b"\x89PNG-fake-bytes"):
    p = h.tmp / name
    p.write_bytes(data)
    return str(p)


def _draft(h, draft_id, **fields):
    d = {"brand": BLOG, "category": "NEWS", "status": "published",
         "caption": "<b>OpenAI</b> ra model moi.", "source_url": "https://x.test/a"}
    d.update(fields)
    if "images" not in d and "image" not in d:
        d["images"] = [_image(h, draft_id + ".png")]
    return h.write_draft(draft_id, **d)


def _http(h):
    return h.trace.names("http")


def _queue(h):
    return h.snapshot(h.state).get("moat_republish_queue.json", {})


def _pushed(h, draft_id, *, brand=BLOG, reported=None, age=0, **moat):
    """Mot draft DA day sang moat tu `age` giay truoc."""
    m = {"workflow_id": "wf-" + draft_id, "external_id": draft_id, "brand": brand,
         "platforms": list(mp.PLATFORMS), "pushed_at": int(h.clock.now - age),
         "reported": reported or {}}
    m.update(moat)
    return _draft(h, draft_id, brand=brand, tg_card_message_id=700, moat=m)


def _tasks(**status):
    """_tasks(facebook="published") -> 200 {"tasks": [...]} cua GET."""
    out = []
    for platform, st in status.items():
        t = {"id": "t-" + platform, "platform": platform, "status": st}
        if st == "published":
            t["result_url"] = "https://" + platform + ".test/p/1"
        if st == "failed":
            t["last_error"] = "Post button <div> never enabled"
        out.append(t)
    return httpx.Response(200, json={"tasks": out})


# =========================================================================
# intake — duong vui + idempotent
# =========================================================================
def test_intake_twice_posts_once_and_marks_draft_with_workflow_id():
    """Bam Duyet hai lan (double click / approve + cron day lai): moat chi duoc
    nhan MOT request. Dau hieu "da day" la draft['moat']['workflow_id']."""
    h = _harness()
    try:
        _draft(h, "d1")
        assert mp.intake("d1") == (True, "da xep 2 task publish")
        assert mp.intake("d1") == (True, "da day truoc do")

        assert _http(h) == ["POST /publish-intake"], _http(h)
        (_, req), = h.trace.of("http")
        assert req["key"] == "key-blog"
        body = req["body"]
        assert body["externalId"] == "d1"
        assert body["caption"] == "OpenAI ra model moi."          # the HTML da boc
        assert body["title"] == body["caption"][:80]
        assert body["sourceUrl"] == "https://x.test/a"
        assert body["platforms"] == ["facebook_post", "instagram_carousel"]
        assert "scheduledAt" not in body
        assert body["images"] == [{"base64": base64.b64encode(b"\x89PNG-fake-bytes").decode(),
                                   "mime": "image/png"}]

        moat = h.read_draft("d1")["moat"]
        assert moat == {"workflow_id": "wf-d1", "brand": BLOG, "external_id": "d1",
                        "platforms": mp.PLATFORMS, "pushed_at": int(h.clock.now),
                        "reported": {}}, moat
        assert _queue(h) == {}, "muc write-ahead phai duoc xoa khi day xong"
        assert h.tg.methods() == [], "intake khong tu bao Telegram"
    finally:
        h.__exit__()


def test_intake_scheduled_post_carries_scheduled_at():
    h = _harness()
    try:
        _draft(h, "d2")
        ok, _ = mp.intake("d2", scheduled_at="2026-09-21T02:00:00Z")
        assert ok
        assert h.trace.of("http")[0][1]["body"]["scheduledAt"] == "2026-09-21T02:00:00Z"
    finally:
        h.__exit__()


def test_intake_dcgr_draft_uses_dcgr_key_never_the_default_one():
    """Khoa quyet dinh org ben moat: bai dcgr di bang khoa blog = dang nham trang."""
    h = _harness()
    try:
        _draft(h, "d3", brand=DCGR)
        assert mp.intake("d3")[0] is True
        assert h.trace.of("http")[0][1]["key"] == "key-dcgr"
        assert h.read_draft("d3")["moat"]["brand"] == DCGR
    finally:
        h.__exit__()


def test_intake_missing_brand_key_refuses_instead_of_falling_back():
    """Khoa dcgr chua dien (con la cho trong '<dan khoa vao day>') -> KHONG goi
    moat, KHONG roi ve khoa blog, khong de lai gi trong hang doi."""
    h = _harness(MOAT_PUBLISH_KEY_DCGR="<dan khoa vao day>")
    try:
        _draft(h, "d4", brand=DCGR)
        ok, note = mp.intake("d4")
        assert ok is False
        assert "MOAT_PUBLISH_KEY_DCGR" in note and "dcgr" in note, note
        assert _http(h) == [] and _queue(h) == {}
        assert "moat" not in h.read_draft("d4")
    finally:
        h.__exit__()


# =========================================================================
# intake — cong chan truoc khi goi moat
# =========================================================================
def test_intake_teaser_stays_on_telegram_only():
    h = _harness()
    try:
        _draft(h, "d5", category="teaser")
        ok, note = mp.intake("d5")
        assert ok is False and "teaser" in note
        assert _http(h) == [] and _queue(h) == {}
    finally:
        h.__exit__()


def test_intake_caption_ceiling_measures_text_after_stripping_html():
    """Tran 2200 do tren chuoi THAT SU dang: 2200 ky tu boc trong <b></b> van
    qua; 2201 ky tu thi bi chan truoc khi ton bang thong."""
    h = _harness()
    try:
        _draft(h, "fit", caption="<b>" + "a" * 2200 + "</b>")
        _draft(h, "over", caption="a" * 2201)
        assert mp.intake("fit")[0] is True
        ok, note = mp.intake("over")
        assert ok is False and "2201" in note and "thua 1" in note, note
        assert _http(h) == ["POST /publish-intake"]
        assert "moat" not in h.read_draft("over") and _queue(h) == {}
    finally:
        h.__exit__()


def test_intake_without_any_readable_image_never_calls_moat():
    h = _harness()
    try:
        _draft(h, "d6", images=[str(h.tmp / "gone.png"), "", None])
        assert mp.intake("d6") == (False, "khong tim thay anh de day")
        assert _http(h) == [] and _queue(h) == {}
    finally:
        h.__exit__()


def test_intake_mixes_urls_and_local_files_and_caps_at_ten_images():
    """`images` cua hermes la DUONG DAN CUC BO; loc theo "http" tung lam bai
    nhieu anh ra rong. Va moat tu choi ca bai khi nhan 11 anh."""
    h = _harness()
    try:
        local = [_image(h, f"c{i}.jpg", b"jpg%d" % i) for i in range(6)]
        urls = [f"https://cdn.test/{i}.png" for i in range(6)]
        _draft(h, "d7", images=[urls[0], local[0]] + urls[1:] + local[1:])
        assert mp.intake("d7")[0] is True
        imgs = h.trace.of("http")[0][1]["body"]["images"]
        assert len(imgs) == 10
        assert imgs[0] == {"url": urls[0]}
        assert imgs[1] == {"base64": base64.b64encode(b"jpg0").decode(), "mime": "image/jpeg"}
        assert [i["url"] for i in imgs[2:7]] == urls[1:]
    finally:
        h.__exit__()


def test_intake_single_image_field_is_used_when_images_is_empty():
    h = _harness()
    try:
        _draft(h, "d8", images=[], image="https://cdn.test/one.png")
        assert mp.intake("d8")[0] is True
        assert h.trace.of("http")[0][1]["body"]["images"] == [{"url": "https://cdn.test/one.png"}]
    finally:
        h.__exit__()


def test_intake_steps_quality_down_until_total_fits_under_ceiling():
    """Cloudflare 524: carousel PNG nang khong di het trong 100 giay. The vuot
    nguong phai thanh WebP, va tong con vuot tran thi ha chat luong tung bac."""
    from PIL import Image
    h = _harness()
    try:
        im = Image.frombytes("RGB", (256, 256), os.urandom(256 * 256 * 3))
        buf = io.BytesIO()
        im.save(buf, "PNG")
        raw = buf.getvalue()
        h.patch(mp, "THRESHOLD_BACKGROUND", 1000)
        q90 = len(mp._background(raw, "image/png", "x", 90)[0])
        q80 = len(mp._background(raw, "image/png", "x", 80)[0])
        assert q80 < q90 < len(raw)
        h.patch(mp, "CEILING_TOTAL", (q90 + q80) // 2)      # q90 vuot, q80 lot
        _draft(h, "d9", images=[_image(h, "big.png", raw)])
        assert mp.intake("d9")[0] is True
        img, = h.trace.of("http")[0][1]["body"]["images"]
        assert img["mime"] == "image/webp"
        assert len(base64.b64decode(img["base64"])) == q80
        assert [n for n in h.trace.names("print") if "ha them mot bac" in n] != []
    finally:
        h.__exit__()


def test_compression_failure_sends_the_original_bytes():
    """Moi loi nen deu nuot: day duoc bai van hon la nen dep."""
    h = _harness()
    try:
        h.patch(mp, "THRESHOLD_BACKGROUND", 4)
        _draft(h, "d10", images=[_image(h, "broken.png", b"not-an-image-at-all")])
        assert mp.intake("d10")[0] is True
        img, = h.trace.of("http")[0][1]["body"]["images"]
        assert img == {"base64": base64.b64encode(b"not-an-image-at-all").decode(),
                       "mime": "image/png"}
        assert any("khong nen duoc broken.png" in n for n in h.trace.names("print"))
    finally:
        h.__exit__()


# =========================================================================
# intake — moat loi giua chung
# =========================================================================
def test_intake_5xx_returns_false_and_queues_a_retry():
    h = _harness()
    try:
        _draft(h, "e1")
        h.server.script("POST /publish-intake", httpx.Response(503, text="upstream down"))
        ok, note = mp.intake("e1", scheduled_at="2026-09-21T02:00:00Z")
        assert ok is False and note == "moat tra HTTP 503: upstream down", note
        assert "moat" not in h.read_draft("e1"), "chua co workflow thi khong duoc danh dau da day"
        assert _queue(h) == {"e1": {"attempts": 1, "brand": BLOG,
                                    "scheduled_at": "2026-09-21T02:00:00Z",
                                    "last_attempt_at": int(h.clock.now),
                                    "error": "moat tra HTTP 503: upstream down"}}, _queue(h)
    finally:
        h.__exit__()


def test_intake_network_timeout_never_raises_and_queues_a_retry():
    h = _harness()
    try:
        _draft(h, "e2")
        h.server.script("POST /publish-intake", httpx.WriteTimeout("body too slow"))
        ok, note = mp.intake("e2")
        assert ok is False
        assert note == "khong goi duoc moat: WriteTimeout: body too slow", note
        q = _queue(h)["e2"]
        assert q["attempts"] == 1 and q["error"] == note
        assert "moat" not in h.read_draft("e2")
    finally:
        h.__exit__()


def test_intake_4xx_is_the_articles_own_fault_and_is_not_queued():
    """400/401/422 day lai bao nhieu lan cung the: muc write-ahead phai bi go,
    khong thi cron day lai mai."""
    h = _harness()
    try:
        _draft(h, "e3")
        h.server.script("POST /publish-intake", httpx.Response(422, text="bad platforms"))
        ok, note = mp.intake("e3")
        assert ok is False and note.startswith("moat tra HTTP 422")
        assert _queue(h) == {}, _queue(h)
    finally:
        h.__exit__()


def test_intake_429_is_transient_and_is_queued():
    h = _harness()
    try:
        _draft(h, "e4")
        h.server.script("POST /publish-intake", httpx.Response(429, text="slow down"))
        assert mp.intake("e4")[0] is False
        assert _queue(h)["e4"]["attempts"] == 1
    finally:
        h.__exit__()


def test_intake_malformed_json_on_200_PIN_raises_but_write_ahead_survives():
    """PIN (nghi la loi): moat/Cloudflare tra 200 kem than khong phai JSON ->
    `r.json()` o ngoai try nen intake NEM, trai cam ket "khong bao gio nem".
    Trang thai van nhat quan: draft chua danh dau, muc write-ahead (attempts=0)
    con trong hang doi de cron day lai."""
    h = _harness()
    try:
        _draft(h, "e5")
        h.server.script("POST /publish-intake", httpx.Response(200, text="<html>cf</html>"))
        try:
            mp.intake("e5")
        except ValueError:
            pass
        else:
            raise AssertionError("hanh vi da doi: intake khong con nem — cap nhat test + bao cao")
        assert "moat" not in h.read_draft("e5")
        q = _queue(h)["e5"]
        assert q["attempts"] == 0 and q["error"] == "dang day, chua co ket qua", q
    finally:
        h.__exit__()


def test_intake_unreadable_draft_never_reaches_moat():
    h = _harness()
    try:
        (h.drafts / "bad.json").write_text("{cut", encoding="utf-8")
        ok, note = mp.intake("bad")
        assert ok is False and note.startswith("khong doc duoc draft")
        assert _http(h) == [] and _queue(h) == {}
    finally:
        h.__exit__()


def test_repost_one_platform_PIN_is_swallowed_by_the_already_pushed_guard():
    """PIN (nghi la loi): nut "Dang lai Facebook" (approve_post._bottom_again_moat)
    goi intake(platforms=[...], external_id=<moi>) tren bai DA co workflow_id —
    cong "da day truoc do" tra ve truoc, KHONG co request nao toi moat, va nhanh
    `moat_history` khong bao gio chay."""
    h = _harness()
    try:
        _pushed(h, "r1", reported={"t-facebook": "failed", "t-instagram": "published"})
        out = mp.intake("r1", platforms=["facebook_post"], external_id="r1-lai2")
        assert out == (True, "da day truoc do"), out
        assert _http(h) == []
        assert "moat_history" not in h.read_draft("r1")
    finally:
        h.__exit__()


def test_repost_after_workflow_id_cleared_keeps_old_workflow_in_history():
    """Nhanh moat_history chi toi duoc khi `moat` con nhung mat workflow_id."""
    h = _harness()
    try:
        _pushed(h, "r2", workflow_id=None)
        ok, note = mp.intake("r2", platforms=["facebook_post"], external_id="r2-lai2")
        assert (ok, note) == (True, "da xep 1 task publish")
        body = h.trace.of("http")[0][1]["body"]
        assert body["externalId"] == "r2-lai2" and body["platforms"] == ["facebook_post"]
        d = h.read_draft("r2")
        assert d["moat"]["workflow_id"] == "wf-r2-lai2"
        assert d["moat"]["external_id"] == "r2-lai2"
        assert [m["external_id"] for m in d["moat_history"]] == ["r2"]
    finally:
        h.__exit__()


# =========================================================================
# bottom_again — hang doi day lai
# =========================================================================
def _queued(h, draft_id, attempts=1, **extra):
    q = _queue(h)
    q[draft_id] = {"attempts": attempts, "brand": BLOG, "scheduled_at": None,
                   "last_attempt_at": int(h.clock.now), "error": "moat tra HTTP 503: x",
                   **extra}
    (h.state / "moat_republish_queue.json").write_text(json.dumps(q), encoding="utf-8")


def test_bottom_again_waits_out_the_backoff_then_retries_and_reports():
    h = _harness()
    try:
        _draft(h, "q1")
        _queued(h, "q1", attempts=1, scheduled_at="2026-09-21T02:00:00Z")
        h.clock.advance(4 * 60)
        assert mp.bottom_again() == [] and _http(h) == [], "chua du 5 phut"
        h.clock.advance(61)
        lines = mp.bottom_again()
        assert lines == ["✅ moat: day lai lan 1 thanh cong q1 — da xep 2 task publish"], lines
        assert h.trace.of("http")[0][1]["body"]["scheduledAt"] == "2026-09-21T02:00:00Z"
        assert _queue(h) == {} and h.read_draft("q1")["moat"]["workflow_id"] == "wf-q1"
        assert mp.bottom_again() == [] and len(_http(h)) == 1
    finally:
        h.__exit__()


def test_bottom_again_failing_again_stays_silent_and_backs_off_longer():
    """Moat sap 6 tieng: khong bao moi lan thu, chi tang so lan + lui lich."""
    h = _harness()
    try:
        _draft(h, "q2")
        _queued(h, "q2", attempts=1)
        h.server.script("POST /publish-intake", httpx.Response(502, text="bad gw"),
                        httpx.Response(502, text="bad gw"))
        h.clock.advance(5 * 60)
        assert mp.bottom_again() == []
        assert _queue(h)["q2"]["attempts"] == 2
        assert _queue(h)["q2"]["error"] == "moat tra HTTP 502: bad gw"
        h.clock.advance(14 * 60)                       # lan 2 phai cho 15 phut
        assert mp.bottom_again() == [] and len(_http(h)) == 1
        h.clock.advance(60)
        assert mp.bottom_again() == [] and len(_http(h)) == 2
        assert _queue(h)["q2"]["attempts"] == 3
        assert h.tg.methods() == []
    finally:
        h.__exit__()


def test_bottom_again_drops_article_whose_error_turned_permanent():
    h = _harness()
    try:
        _draft(h, "q3")
        _queued(h, "q3")
        h.server.script("POST /publish-intake", httpx.Response(401, text="bad key"))
        h.clock.advance(5 * 60)
        lines = mp.bottom_again()
        assert len(lines) == 1 and lines[0].startswith("⚠️ moat: thoi day lai q3"), lines
        assert "HTTP 401" in lines[0]
        assert _queue(h) == {}
    finally:
        h.__exit__()


def test_bottom_again_picks_up_write_ahead_entry_left_by_a_kill():
    """kill -9 giua luc upload: chi con muc attempts=0. Cron phai nhat len."""
    h = _harness()
    try:
        _draft(h, "q4")
        _queued(h, "q4", attempts=0, error="dang day, chua co ket qua")
        h.clock.advance(5 * 60)
        lines = mp.bottom_again()
        assert lines and "q4" in lines[0] and _http(h) == ["POST /publish-intake"]
    finally:
        h.__exit__()


def test_bottom_again_gives_up_with_a_reply_on_the_card_and_a_retry_button():
    h = _harness()
    try:
        _draft(h, "q5", tg_card_message_id=700)
        _queued(h, "q5", attempts=len(mp.SCHEDULE_BACK) + 1, error="moat tra HTTP 524: <cf>")
        lines = mp.bottom_again()
        assert lines == [], "da reply vao the thi khong bao them vao topic"
        assert _http(h) == [] and _queue(h) == {}
        sent, = h.tg.sent("sendMessage")
        assert sent["token"] == "TOK" and sent["chat_id"] == "-1001"
        assert sent["message_thread_id"] == WRITER and sent["reply_to_message_id"] == 700
        assert "Bỏ cuộc sau 7 lần" in sent["text"] and "&lt;cf&gt;" in sent["text"]
        assert sent["reply_markup"] == {"inline_keyboard": [[
            {"text": "🔁 Đẩy lại moat", "callback_data": "mlai:q5"}]]}
    finally:
        h.__exit__()


def test_bottom_again_give_up_falls_back_to_topic_line_when_card_unreachable():
    h = _harness(TELEGRAM_GROUP_ID=None)
    try:
        _draft(h, "q6")
        _queued(h, "q6", attempts=8)
        lines = mp.bottom_again()
        assert len(lines) == 1 and "bo cuoc sau 7 lan day lai q6" in lines[0], lines
        assert h.tg.methods() == [] and _queue(h) == {}
        assert any("thieu TELEGRAM_GROUP_ID" in n for n in h.trace.names("print"))
    finally:
        h.__exit__()


def test_bottom_again_leaves_other_brands_articles_alone():
    """Hai container dung chung hang doi? Khong — nhung cung drafts/. Bai blog
    ma container dcgr day la len nham org."""
    h = _harness(BRAND=DCGR)
    try:
        _draft(h, "q7")
        _queued(h, "q7", attempts=8)
        h.clock.advance(86400)
        assert mp.bottom_again() == []
        assert _http(h) == [] and h.tg.methods() == [] and "q7" in _queue(h)
    finally:
        h.__exit__()


# =========================================================================
# poll — trang thai doi giua cac lan hoi
# =========================================================================
def test_poll_reports_each_transition_once_queued_then_published_and_failed():
    h = _harness()
    try:
        _pushed(h, "p1")
        h.server.script("GET /publish-intake/wf-p1",
                        _tasks(facebook="queued", instagram="claimed"),
                        _tasks(facebook="published", instagram="failed"))
        assert mp.poll() == [], "trang thai chua ket thuc thi im"
        assert h.read_draft("p1")["moat"]["reported"] == {
            "t-facebook": "queued", "t-instagram": "claimed"}

        lines = mp.poll()
        assert lines == ["✅ p1 đã lên Facebook\nhttps://facebook.test/p/1"], lines
        # Instagram loi: REPLY vao the kem nut dang lai rieng nen tang, khong vao topic.
        sent, = h.tg.sent("sendMessage")
        assert sent["reply_to_message_id"] == 700 and sent["message_thread_id"] == WRITER
        assert sent["parse_mode"] == "HTML"
        assert "Đăng <b>Instagram</b> lỗi" in sent["text"]
        assert "Post button &lt;div&gt; never enabled" in sent["text"]
        assert sent["reply_markup"]["inline_keyboard"] == [[
            {"text": "🔁 Đăng lại Instagram", "callback_data": "mlaii:p1"}]]
        assert h.read_draft("p1")["moat"]["reported"] == {
            "t-facebook": "published", "t-instagram": "failed"}

        # Moi task da ket thuc: lan sau khong hoi, khong bao.
        assert mp.poll() == []
        assert _http(h) == ["GET /publish-intake/wf-p1"] * 2, _http(h)
        assert [d["key"] for _, d in h.trace.of("http")] == ["key-blog"] * 2
        assert len(h.tg.sent()) == 1
    finally:
        h.__exit__()


def test_poll_failed_platform_falls_back_to_topic_line_when_card_reply_impossible():
    h = _harness(TELEGRAM_GROUP_ID=None)
    try:
        _pushed(h, "p2")
        h.server.script("GET /publish-intake/wf-p2", _tasks(facebook="failed"))
        lines = mp.poll()
        assert lines == ["❌ p2 đăng Facebook lỗi: Post button <div> never enabled"], lines
        assert h.tg.methods() == []
    finally:
        h.__exit__()


def test_report_card_retries_without_reply_when_the_card_was_deleted():
    h = _harness()
    try:
        _draft(h, "p3", tg_card_message_id=700)
        h.server.script("tg sendMessage", httpx.Response(400, json={
            "ok": False, "description": "Bad Request: message to be replied not found"}))
        assert mp.report_card("p3", "hello") is True
        first, second = h.tg.sent("sendMessage")
        assert first["reply_to_message_id"] == 700
        assert "reply_to_message_id" not in second and second["text"] == "hello"
        assert second["message_thread_id"] == WRITER and "reply_markup" not in second
    finally:
        h.__exit__()


def test_report_card_returns_false_when_telegram_refuses_everything():
    h = _harness()
    try:
        _draft(h, "p4")                                   # khong co tg_card_message_id
        h.server.script("tg sendMessage", httpx.ConnectError("no route"))
        assert mp.report_card("p4", "hello") is False
        assert len(h.tg.sent()) == 1
        assert any("khong bao duoc Telegram: ConnectError" in n
                   for n in h.trace.names("print"))
    finally:
        h.__exit__()


def test_poll_unknown_status_is_recorded_silently_and_cancelled_is_announced():
    h = _harness()
    try:
        _pushed(h, "p5")
        h.server.script("GET /publish-intake/wf-p5",
                        _tasks(facebook="needs_human_review", instagram="cancelled"))
        lines = mp.poll()
        assert lines == ["⏹ p5 Instagram: cancelled"], lines
        assert h.read_draft("p5")["moat"]["reported"]["t-facebook"] == "needs_human_review"
        assert h.tg.methods() == []
        # Trang thai la chua ket thuc -> van hoi tiep, nhung khong bao lai.
        h.server.script("GET /publish-intake/wf-p5",
                        _tasks(facebook="needs_human_review", instagram="cancelled"))
        assert mp.poll() == [] and len(_http(h)) == 2
    finally:
        h.__exit__()


def test_poll_task_without_id_is_ignored():
    h = _harness()
    try:
        _pushed(h, "p6")
        before = h.read_draft("p6")
        h.server.script("GET /publish-intake/wf-p6", httpx.Response(200, json={
            "tasks": [{"platform": "facebook", "status": "published"}]}))
        assert mp.poll() == []
        assert h.read_draft("p6") == before
    finally:
        h.__exit__()


def test_poll_moat_outage_is_reported_once_per_error_kind_and_recovery_once():
    """Cron moi phut: moat sap 6 tieng ma bao moi lan la 360 tin rac. Bai khac
    trong cung dot van phai duoc hoi."""
    h = _harness()
    try:
        _pushed(h, "a-down")
        _pushed(h, "b-fine")
        h.server.script("GET /publish-intake/wf-a-down",
                        httpx.Response(500, text="boom"), httpx.Response(500, text="boom"),
                        httpx.ReadTimeout("slow"), _tasks(facebook="published"))
        h.server.script("GET /publish-intake/wf-b-fine", _tasks(instagram="published"))

        lines = mp.poll()
        assert lines == ["⚠️ a-down: khong hoi duoc moat (RuntimeError), se im cho toi khi tinh hinh doi",
                         "✅ b-fine đã lên Instagram\nhttps://instagram.test/p/1"], lines
        assert h.read_draft("a-down")["moat"]["reported_error"] == "RuntimeError"

        assert mp.poll() == [], "cung mot loai loi thi im"
        lines = mp.poll()
        assert len(lines) == 1 and "(ReadTimeout)" in lines[0], lines

        lines = mp.poll()
        assert lines == ["✅ a-down: moat hoi lai duoc roi",
                         "✅ a-down đã lên Facebook\nhttps://facebook.test/p/1"], lines
        assert "reported_error" not in h.read_draft("a-down")["moat"]
    finally:
        h.__exit__()


def test_poll_null_tasks_PIN_aborts_the_whole_batch():
    """PIN (nghi la loi): moat tra {"tasks": null} cho MOT bai -> TypeError thoat
    khoi poll(), cac bai xep sau khong duoc hoi, cron chet khong bao gi. Vong lap
    trong poll() khong co try/except quanh tung bai."""
    h = _harness()
    try:
        _pushed(h, "a-null")
        _pushed(h, "b-after")
        h.server.script("GET /publish-intake/wf-a-null",
                        httpx.Response(200, json={"tasks": None}))
        try:
            mp.poll()
        except TypeError:
            pass
        else:
            raise AssertionError("hanh vi da doi: poll khong con nem — cap nhat test + bao cao")
        assert _http(h) == ["GET /publish-intake/wf-a-null"], _http(h)
    finally:
        h.__exit__()


def test_poll_stops_tracking_after_seven_days_and_says_how_many_are_missing():
    """Extension tat: task dung o "scheduled" mai mai = mot request moi phut,
    vinh vien. reported RONG van phai dem la "con thieu het"."""
    h = _harness()
    try:
        _pushed(h, "old-none", age=8 * 86400)
        _pushed(h, "old-half", age=8 * 86400, reported={"t-facebook": "published"})
        _pushed(h, "young", age=6 * 86400)
        lines = mp.poll()
        assert lines == ["⏳ old-half: còn 1 task chưa đăng sau 7 ngày, ngừng theo dõi, xem lại extension",
                         "⏳ old-none: còn 2 task chưa đăng sau 7 ngày, ngừng theo dõi, xem lại extension"], lines
        assert _http(h) == ["GET /publish-intake/wf-young"]
        assert h.read_draft("old-none")["moat"]["tracking_stopped"] is True
        assert "tracking_stopped" not in h.read_draft("young")["moat"]
        assert mp.poll() == [] and len(_http(h)) == 2       # chi con "young"
    finally:
        h.__exit__()


def test_poll_only_touches_its_own_brand_and_asks_with_that_brands_key():
    h = _harness(BRAND=DCGR)
    try:
        _pushed(h, "mine", brand=DCGR)
        _pushed(h, "theirs", brand=BLOG)
        _draft(h, "never-pushed")
        (h.drafts / "mine.meta.json").write_text("{}", encoding="utf-8")
        (h.drafts / "cut.json").write_text("{cut", encoding="utf-8")
        h.server.script("GET /publish-intake/wf-mine", _tasks(facebook="published"))
        lines = mp.poll()
        assert lines == ["✅ mine đã lên Facebook\nhttps://facebook.test/p/1"]
        (_, req), = h.trace.of("http")
        assert req["key"] == "key-dcgr"
        assert h.read_draft("theirs")["moat"]["reported"] == {}
    finally:
        h.__exit__()


def test_poll_container_brand_derives_from_ct_brand_short_name():
    h = _harness(CT_BRAND="blog")
    try:
        _pushed(h, "mine", brand=BLOG)
        _pushed(h, "theirs", brand=DCGR)
        mp.poll()
        assert _http(h) == ["GET /publish-intake/wf-mine"]
    finally:
        h.__exit__()


def test_poll_is_silent_when_the_brand_key_was_removed_after_pushing():
    h = _harness(MOAT_PUBLISH_KEY_DCGR=None)
    try:
        _pushed(h, "orphan", brand=DCGR)
        assert mp.poll() == [] and _http(h) == []
    finally:
        h.__exit__()


def test_poll_without_base_url_does_nothing():
    h = _harness(MOAT_BASE_URL=None)
    try:
        _pushed(h, "x")
        assert mp.poll() == [] and h.trace.events == []
    finally:
        h.__exit__()


# =========================================================================
# _notify — bao vao topic writer, gui hut thi de danh
# =========================================================================
def _spool(h):
    return h.snapshot(h.state).get("moat_unsent_notices.json")


def test_notify_sends_one_message_to_the_writer_topic():
    h = _harness()
    try:
        mp._notify(["✅ a đã lên Facebook", "⏹ b Instagram: cancelled"])
        sent, = h.tg.sent("sendMessage")
        assert sent["chat_id"] == "-1001" and sent["message_thread_id"] == WRITER
        assert sent["text"] == "✅ a đã lên Facebook\n\n⏹ b Instagram: cancelled"
        assert _spool(h) is None
    finally:
        h.__exit__()


def test_notify_with_nothing_new_is_silent():
    h = _harness()
    try:
        mp._notify([])
        assert h.trace.events == []
    finally:
        h.__exit__()


def test_notify_spools_refused_lines_and_resends_them_with_the_next_batch():
    """`reported` da ghi vao draft TRUOC khi bao: dong nao gui hut ma khong de
    danh la mat vinh vien. Telegram 429 khong duoc giet cron (TelegramReject la
    Exception thuong, khong phai SystemExit)."""
    h = _harness()
    try:
        h.server.script("tg sendMessage", httpx.Response(429, json={
            "ok": False, "description": "Too Many Requests: retry after 30"}))
        mp._notify(["line-1"])
        assert _spool(h) == ["line-1"]
        assert any("de danh 1 dong" in n for n in h.trace.names("print"))

        mp._notify(["line-1", "line-2"])                  # line-1 khong duoc lap
        assert h.tg.texts()[-1] == "line-1\n\nline-2"
        assert _spool(h) is None, "gui duoc roi thi xoa spool"

        mp._notify([])
        assert len(h.tg.sent()) == 2
    finally:
        h.__exit__()


def test_notify_flushes_spool_even_when_this_run_has_no_news():
    h = _harness()
    try:
        (h.state / "moat_unsent_notices.json").write_text('["old"]', encoding="utf-8")
        mp._notify([])
        assert h.tg.texts() == ["old"] and _spool(h) is None
    finally:
        h.__exit__()


def test_notify_corrupt_spool_does_not_block_new_lines():
    h = _harness()
    try:
        (h.state / "moat_unsent_notices.json").write_text("{cut", encoding="utf-8")
        mp._notify(["fresh"])
        assert h.tg.texts() == ["fresh"] and _spool(h) is None
    finally:
        h.__exit__()


def test_notify_without_group_id_sends_nothing():
    h = _harness(TELEGRAM_GROUP_ID=None)
    try:
        mp._notify(["x"])
        assert h.tg.methods() == []
    finally:
        h.__exit__()


def test_notify_missing_bot_token_PIN_kills_the_process_and_loses_the_lines():
    """PIN (nghi la loi): publish.load_secrets() goi sys.exit khi thieu token;
    SystemExit xuyen qua `except Exception` cua _notify (va cua _tele — nhanh
    `if not token` la ma chet), nen cron chet TRUOC khi kip ghi spool."""
    h = _harness(TELEGRAM_BOT_TOKEN=None)
    try:
        try:
            mp._notify(["lost"])
        except SystemExit as e:
            assert "TELEGRAM_BOT_TOKEN" in str(e.code)
        else:
            raise AssertionError("hanh vi da doi: _notify khong con thoat — cap nhat test + bao cao")
        assert _spool(h) is None
    finally:
        h.__exit__()


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
