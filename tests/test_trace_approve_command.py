#!/usr/bin/env python3
"""LOW-311 — luoi doi chieu vet cho approve_command: lenh slash /bai /vai /hd.

Nguyen tac cua module: dau "/" la Ong Chu RA LENH — dung cu phap moi chay, sai
thi bao ngan va KHONG tao gi. Moi kich ban khang dinh: vet goi ra ngoai
(create_pair co duoc goi khong, voi item nao), so dedup `article_request_counts`
sau cung, va dong tra loi Ong Chu nhan duoc.

Chay:  python tests/test_trace_approve_command.py
"""
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import approve_base as base            # noqa: E402
import approve_command as cmd          # noqa: E402
import social_post                     # noqa: E402
import state_paths                     # noqa: E402
from trace_harness import Harness, message, run_tests  # noqa: E402

TOPIC = 55
URL = "https://example.com/news/ai-chip"


def _harness(page=("AI chip mới", "https://img/x.png", ""), pair=("t_abc", None)):
    h = Harness(cmd, base)
    h.__enter__()
    h.capture_logs()
    h.patch_env(os.environ, CT_CHAT_VIA_GATEWAY=None)
    h.patch(cmd, "create_pair", h.spy("create_pair", returns=pair))
    h.patch(cmd, "_read_page", h.spy("_read_page", returns=page))
    h.patch(social_post, "is_social", lambda url: False)
    return h


def _send(h, text, **kw):
    cmd.handle_command(h.token, h.group, message(1, text, thread=TOPIC, **kw), TOPIC, text)


def _counts(h):
    return h.snapshot(h.state).get(state_paths.ARTICLE_REQUEST_COUNTS_FILE)


def _pairs(h):
    return [d for n, d in h.trace.of("fn") if n == "create_pair"]


# =========================================================================
# /bai — cu phap va cong chan
# =========================================================================
def test_bai_wrong_syntax_creates_nothing():
    h = _harness()
    try:
        for bad in ("/bai", "/bai dre " + URL, "/bai " + URL, "/bai " + URL + " dre thêm"):
            _send(h, bad)
        assert _pairs(h) == [] and _counts(h) is None
        assert len(h.tg.texts()) == 4 and all("Cú pháp" in t and "Không tạo gì" in t
                                              for t in h.tg.texts())
        assert all(d["message_thread_id"] == TOPIC for d in h.tg.sent())
    finally:
        h.__exit__()


def test_bai_unknown_role_lists_valid_roles():
    h = _harness()
    try:
        _send(h, "/bai " + URL + " <b>hacker</b>")
        assert _pairs(h) == []
        (t,) = h.tg.texts()
        assert "Không có vai" in t and "&lt;b&gt;hacker&lt;/b&gt;" in t and "dre" in t
    finally:
        h.__exit__()


def test_bai_refuses_internal_hosts_before_any_fetch():
    """Bot chay ngay tren server: URL tro nguoc vao trong la fetch thang vao
    ruot he thong. `127.1` va `[::1]` lot `_HOST_CAM` nhung khong lot cong chung."""
    h = _harness()
    try:
        for u in ("http://localhost:9120/x", "http://10.0.0.5/", "http://127.1/",
                  "http://[::1]/", "https://donniechu-01.netbird.mated/", "ftp://a.b/c"):
            _send(h, f"/bai {u} dre")
        assert h.trace.names("fn") == [], "khong duoc doc trang, khong duoc tao task"
        assert len(h.tg.texts()) == 6 and all(t.startswith(("❌", "Cú pháp")) for t in h.tg.texts())
    finally:
        h.__exit__()


# =========================================================================
# /bai — duong chinh + dedup (tin bi day nhieu lan)
# =========================================================================
def test_bai_happy_path_creates_pair_records_dedup_and_answers():
    h = _harness(page=("AI chip mới", "https://img/x.png", "trang trả HTTP 403"))
    try:
        _send(h, "/bai " + URL + "?utm_source=x dre")
        (p,) = _pairs(h)
        item = p["args"][0]
        assert p["kwargs"] == {"vai_anh": "dre", "brand": cmd.BRAND}
        assert item["title"] == "AI chip mới" and item["link"] == URL + "?utm_source=x"
        assert item["image_url"] == "https://img/x.png" and item["index"].startswith("b")
        counts = _counts(h)
        assert list(counts) == [URL], "khoa dedup la URL DA CHUAN HOA (bo utm)"
        rec = counts[URL]
        assert rec["tasks"] == ["t_abc"] and rec["image_role"] == "dre"
        assert rec["draft_id"].startswith("ai-chip-m") and "-dre-" in rec["draft_id"], rec
        (t,) = h.tg.texts()
        assert t.startswith("✅ <b>AI chip mới</b>") and "task t_abc" in t and "⚠️ trang trả HTTP 403" in t
    finally:
        h.__exit__()


def test_bai_same_article_twice_is_not_created_again():
    """Cung mot bai dan hai lan tu hai nguon chi khac utm_* / fragment / dau "/"."""
    h = _harness()
    try:
        _send(h, "/bai " + URL + " dre")
        _send(h, "/bai " + URL + "/?utm_campaign=nl&fbclid=1#top ethan")
        assert len(_pairs(h)) == 1
        assert "đã đặt" in h.tg.texts()[1] and "Không tạo lại" in h.tg.texts()[1]
        assert len(_counts(h)) == 1
    finally:
        h.__exit__()


def test_bai_dead_url_creates_nothing():
    h = _harness(page=(None, "", "không tải được trang (ConnectError)"))
    try:
        _send(h, "/bai " + URL + " dre")
        assert _pairs(h) == [] and _counts(h) is None
        assert "không tạo task" in h.tg.texts()[0] and "ConnectError" in h.tg.texts()[0]
    finally:
        h.__exit__()


def test_bai_create_pair_error_is_reported_and_not_recorded():
    """Ghi so dedup khi task CHUA tao = lan /bai sau bi tu choi "da dat" oan."""
    h = _harness(pair=(None, "kanban tu choi <x>"))
    try:
        _send(h, "/bai " + URL + " dre")
        assert _counts(h) is None
        assert h.tg.texts() == ["❌ kanban tu choi &lt;x&gt;"]
    finally:
        h.__exit__()


# =========================================================================
# /bai — post mang xa hoi (su co 08/09/2026, task t_905914b6)
# =========================================================================
def test_bai_social_post_uses_full_text_and_dedups_by_permalink():
    h = _harness()
    try:
        h.patch(social_post, "is_social", lambda url: True)
        h.patch(social_post, "read", h.spy("social_read", returns={
            "title": "Bài của Tùng", "text": "toàn văn post", "link": "https://fb.com/p/1",
            "media": [{"type": "video", "url": "v"}, {"type": "image", "url": "https://i/1.jpg"}]}))
        _send(h, "/bai https://fb.com/share/abc dre")
        (p,) = _pairs(h)
        item = p["args"][0]
        assert item["summary_vi"] == "toàn văn post" and item["link"] == "https://fb.com/p/1"
        assert item["image_url"] == "https://i/1.jpg" and "TOAN VAN" in item["source_note"]
        assert "_read_page" not in h.trace.names("fn")
        assert h.tg.texts()[0].startswith("⏳ Đang đọc post")
        # link chia se KHAC nhung cung permalink -> khong tao lai
        _send(h, "/bai https://fb.com/share/zzz dre")
        assert len(_pairs(h)) == 1 and "Post này đã đặt" in h.tg.texts()[-1]
    finally:
        h.__exit__()


def test_bai_social_crawl_failure_falls_back_to_page_tags():
    h = _harness()
    try:
        h.patch(social_post, "is_social", lambda url: True)
        h.patch(social_post, "read", h.spy("social_read", returns=None))
        _send(h, "/bai https://x.com/a/status/1 dre")
        assert h.trace.names("fn") == ["social_read", "_read_page", "create_pair"]
        assert _pairs(h)[0]["args"][0]["summary_vi"] == ""
    finally:
        h.__exit__()


def test_read_social_notes_post_without_image():
    h = _harness()
    try:
        h.patch(social_post, "read", lambda url, in_log=None: {
            "title": "t", "text": "x", "link": "l", "media": []})
        assert cmd._read_social("u") == ("t", "x", "", "l",
                                         "post khong co anh — vai tu lo phan hinh")
        h.patch(social_post, "read", lambda url, in_log=None: {"title": "t", "text": "",
                                                               "link": "l", "media": []})
        assert cmd._read_social("u") is None
    finally:
        h.__exit__()


# =========================================================================
# _read_page — doc the og: cua trang
# =========================================================================
def _fake_http(h, status=200, html="", raises=None):
    class _Client:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url):
            h.trace.add("http", "GET", url=url)
            if raises:
                raise raises
            return types.SimpleNamespace(status_code=status, text=html)
    h.patch(cmd, "httpx", types.SimpleNamespace(Client=_Client))


def test_read_page_prefers_og_tags_then_title_then_url():
    h = Harness(cmd, base)
    h.__enter__()
    try:
        _fake_http(h, html='<meta property="og:title" content=" OG tít "><title>T</title>'
                           '<meta property="og:image" content="https://i/og.png">')
        assert cmd._read_page(URL) == ("OG tít", "https://i/og.png", "")
        _fake_http(h, html="<title> Chỉ có title </title>")
        assert cmd._read_page(URL) == ("Chỉ có title", "", "")
        _fake_http(h, status=403, html="<html></html>")
        title, img, note = cmd._read_page(URL)
        assert title == "example.com/news/ai-chip" and "HTTP 403" in note
        _fake_http(h, raises=TimeoutError("x"))
        assert cmd._read_page(URL) == (None, "", "không tải được trang (TimeoutError)")
    finally:
        h.__exit__()


# =========================================================================
# handle_command — ai duoc ra lenh, lenh nao la cua ai
# =========================================================================
def test_stranger_cannot_run_slash_commands():
    h = _harness()
    try:
        (h.state / state_paths.BOSS_IDS_FILE).write_text("[42]", encoding="utf-8")
        _send(h, "/bai " + URL + " dre", user=7)
        assert _pairs(h) == []
        assert "chỉ nhận từ Ông Chủ" in h.tg.texts()[0] and "7" in h.tg.texts()[0]
    finally:
        h.__exit__()


def test_two_bots_one_group_approve_stays_silent_on_gateway_commands():
    """05/09/2026: approve va gateway chung group. Lenh cua Hermes (/help tran,
    /kanban, /new, /help@bot-gateway) -> approve IM, khong "Khong co lenh"."""
    h = _harness()
    try:
        h.patch_env(os.environ, CT_CHAT_VIA_GATEWAY="1")
        for t in ("/help", "/help@hermesdcgr_bot", "/kanban list", "/new@hermesdcgr_bot"):
            _send(h, t)
        assert h.tg.methods() == []
        _send(h, "/hd")
        _send(h, "/help@hermespm_bot")
        assert len(h.tg.texts()) == 2 and all("<b>Lệnh:</b>" in t for t in h.tg.texts())
    finally:
        h.__exit__()


def test_single_bot_brand_answers_unknown_command_and_help():
    h = _harness()
    try:
        _send(h, "/kanban")
        _send(h, "/help")
        assert "Không có lệnh /kanban" in h.tg.texts()[0]
        assert "<b>Lệnh:</b>" in h.tg.texts()[1]
    finally:
        h.__exit__()


def test_vai_lists_every_image_role_including_kite():
    """Truoc 08/09/2026 /hd ke thieu kite/edu — Ong Chu tuong khong giao duoc."""
    h = _harness()
    try:
        _send(h, "/vai@AnyBot")
        (t,) = h.tg.texts()
        for ten in cmd.ROLE_IMAGE:
            assert f"<code>{ten}</code>" in t, ten
        assert "Vai viết" in t
        assert "kite" in cmd.COMMAND_HELP
    finally:
        h.__exit__()


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
