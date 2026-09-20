#!/usr/bin/env python3
"""LOW-311 — luoi doi chieu vet cho publish.py: CLI `main()` (bao cao dai chia
manh, --luu-mid, dinh tuyen chat/topic, ma thoat) va cac ham thu vien gui anh /
album / topic.

Moi kich ban khang dinh ba thu: vet goi Bot API (thu tu + tham so tung request),
tep state sau cung (tep --luu-mid), va thu nguoi goi nhan lai (stdout, ma thoat).
Canh HTTP la `httpx.MockTransport` ghi moi request vao `h.trace` duoi kind "tg"
nen `h.tg.sent()/texts()` cua harness dung duoc nguyen. Request multipart
(sendPhoto/sendDocument/sendMediaGroup) duoc tach thanh truong + ten tep.

Chay:  python tests/test_trace_publish.py
"""
import json
import os
import re
import sys
import types
from pathlib import Path
from urllib.parse import parse_qsl

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import env_load                        # noqa: E402
import publish                         # noqa: E402
import tele_util                       # noqa: E402
from trace_harness import Harness, run_tests  # noqa: E402

BOB, VERA = 55, 77


def _multipart(request):
    """{ten truong: gia tri} + "_files": {ten truong: ten tep} cua mot request
    multipart/form-data."""
    boundary = request.headers["content-type"].split("boundary=")[1].encode()
    fields, files = {}, {}
    for part in request.content.split(b"--" + boundary):
        head, _, value = part.partition(b"\r\n\r\n")
        m = re.search(rb'name="([^"]+)"(?:; filename="([^"]+)")?', head)
        if not m:
            continue
        name = m.group(1).decode()
        if m.group(2):
            files[name] = m.group(2).decode()
        else:
            fields[name] = value.rstrip(b"\r\n").decode("utf-8")
    fields["_files"] = files
    return fields


class FakeBotApi:
    """`script(r1, r2...)`: cau tra loi lan luot cho cac request ke tiep (dict
    JSON | Exception); het hang thi tra ok voi message_id tang dan tu 9001."""

    def __init__(self, h):
        self.h, self._queue, self._mid = h, [], 9000

    def script(self, *responses):
        self._queue.extend(responses)
        return self

    def __call__(self, request):
        assert request.url.host == "api.telegram.org", request.url
        _, bot, method = request.url.path.split("/")
        ctype = request.headers.get("content-type", "")
        if ctype.startswith("multipart/"):
            kw = _multipart(request)
        elif ctype.startswith("application/x-www-form-urlencoded"):   # album toan URL
            kw = dict(parse_qsl(request.content.decode("utf-8")))
        else:
            kw = json.loads(request.content.decode("utf-8"))
        self.h.trace.add("tg", method, token=bot[3:], **kw)
        self._mid += 1
        r = self._queue.pop(0) if self._queue else {
            "ok": True, "result": {"message_id": self._mid}}
        if isinstance(r, BaseException):
            raise r
        return httpx.Response(200 if r.get("ok") else 400, json=r)


def _harness(**env):
    h = Harness(publish)
    h.__enter__()
    h.api = FakeBotApi(h)
    transport = httpx.MockTransport(h.api)

    def client(*a, **kw):
        kw["transport"] = transport
        return httpx.Client(*a, **kw)

    fake = types.SimpleNamespace(**{k: getattr(httpx, k) for k in dir(httpx)
                                    if not k.startswith("_")})
    fake.Client = client
    h.patch(publish, "httpx", fake)
    # Khong doc tep secret that (~/.hermes/.env): moi cau hinh di qua patch_env.
    h.patch(env_load, "load", lambda *a: None)
    cfg = dict(TELEGRAM_BOT_TOKEN="TOK", TELEGRAM_CHANNEL_ID="-1002",
               TELEGRAM_GROUP_ID="-1001", CT_BRAND=None)
    cfg.update(env)
    h.patch_env(os.environ, **cfg)
    h.topics({"bob": BOB, "vera": VERA})

    def _print(*a, **kw):
        h.trace.add("print", " ".join(str(x) for x in a))
    h.patch(publish, "print", _print)
    return h


def _cli(h, *argv):
    """Chay publish.main() voi argv gia. Tra ma thoat nhu shell thay: 0 khi
    main() tra ve binh thuong; SystemExit(chuoi) la ma 1 + chuoi ra stderr."""
    h.patch(sys, "argv", ["publish.py", *[str(a) for a in argv]])
    try:
        publish.main()
    except SystemExit as e:
        if e.code is None or e.code == 0:
            return 0, ""
        return (e.code, "") if isinstance(e.code, int) else (1, str(e.code))
    return 0, ""


def _prints(h):
    return h.trace.names("print")


def _long_report(n_items=120):
    """Bao cao danh so kieu Vera: moi muc mot doan, tong > 2 x 4096 ky tu."""
    items = [f"{i}. <b>Tin so {i}</b> " + ("noi dung " * 12).strip() for i in range(1, n_items + 1)]
    text = "\n\n".join(items)
    assert len(text) > 2 * tele_util.LIMIT
    return text


# =========================================================================
# Bao cao dai -> nhieu manh, --luu-mid giu mid cua MOI manh (su co 12/09/2026)
# =========================================================================
def test_long_report_is_split_and_luu_mid_keeps_every_chunk_id():
    """12/09/2026: Ong Chu reply vao manh DAU (noi co muc so 1); --luu-mid chi
    giu mid manh cuoi nen lenh chon bi im lang bo qua."""
    h = _harness()
    try:
        text = _long_report()
        src = h.tmp / "report.html"
        src.write_text(text, encoding="utf-8")
        mid_file = h.state / "sub" / "report_mid.json"       # thu muc chua co
        code, _ = _cli(h, "--file", src, "--to-env", "TELEGRAM_GROUP_ID",
                       "--thread-name", "vera", "--luu-mid", mid_file)
        assert code == 0

        sent = h.tg.sent()
        assert h.tg.methods() == ["sendMessage"] * len(sent) and len(sent) >= 3, h.tg.methods()
        for s in sent:
            assert s["token"] == "TOK" and s["chat_id"] == "-1001"
            assert s["message_thread_id"] == VERA, "MOI manh phai vao dung topic"
            assert s["parse_mode"] == "HTML" and s["disable_web_page_preview"] is True
            assert 0 < len(s["text"]) <= tele_util.LIMIT
        assert sent[0]["text"].startswith("1. <b>Tin so 1</b>")
        assert sent[-1]["text"].rstrip().endswith(text[-20:])
        joined = "".join(re.sub(r"\s+", "", s["text"]) for s in sent)
        assert joined == re.sub(r"\s+", "", text), "chia manh khong duoc mat chu"

        mids = list(range(9001, 9001 + len(sent)))
        saved = json.loads(mid_file.read_text(encoding="utf-8"))
        assert saved["message_ids"] == mids, saved
        assert saved["message_id"] == mids[-1]
        assert isinstance(saved["ts"], float)
        assert _prints(h) == [f"da dang | message_id={mids[-1]} chat=-1001"]
    finally:
        h.__exit__()


def test_luu_mid_overwrites_the_whole_file_so_stale_keys_disappear():
    """Moi lan gui la mot bao cao moi: khoa cu (vd `manifest` scan_submit ghim)
    phai bien mat cung ban cu, khong merge."""
    h = _harness()
    try:
        mid_file = h.state / "mid.json"
        mid_file.write_text(json.dumps({"message_id": 1, "message_ids": [1],
                                        "manifest": "old.json"}), encoding="utf-8")
        assert _cli(h, "--text", "short report", "--luu-mid", mid_file)[0] == 0
        saved = json.loads(mid_file.read_text(encoding="utf-8"))
        assert sorted(saved) == ["message_id", "message_ids", "ts"], saved
        assert saved["message_ids"] == [9001] and saved["message_id"] == 9001
    finally:
        h.__exit__()


def test_telegram_refusing_a_middle_chunk_stops_sending_and_exits_non_zero():
    """LOW-160: nguoi goi (scan_submit, cron) chi biet qua MA THOAT. Manh 2 bi
    tu choi -> khong gui manh 3, khong in "da dang", khong ghi de tep mid cu
    (bao cao cu van la bao cao dang reply duoc)."""
    h = _harness()
    try:
        src = h.tmp / "report.html"
        src.write_text(_long_report(), encoding="utf-8")
        mid_file = h.state / "mid.json"
        mid_file.write_text('{"message_id": 1, "message_ids": [1]}', encoding="utf-8")
        h.api.script({"ok": True, "result": {"message_id": 9001}},
                     {"ok": False, "description": "Bad Request: can't parse entities"})
        code, err = _cli(h, "--file", src, "--luu-mid", mid_file)
        assert code == 1, code
        assert err == "Telegram tu choi: Bad Request: can't parse entities", err
        assert h.tg.methods() == ["sendMessage", "sendMessage"], h.tg.methods()
        assert _prints(h) == []
        assert json.loads(mid_file.read_text(encoding="utf-8")) == {
            "message_id": 1, "message_ids": [1]}
    finally:
        h.__exit__()


def test_successful_send_exits_zero_and_defaults_to_the_channel():
    h = _harness()
    try:
        assert _cli(h, "--text", "hello") == (0, "")
        sent, = h.tg.sent("sendMessage")
        assert sent["chat_id"] == "-1002" and "message_thread_id" not in sent
        assert _prints(h) == ["da dang | message_id=9001 chat=-1002"]
    finally:
        h.__exit__()


def test_unwritable_luu_mid_warns_but_the_send_still_counts():
    """Best-effort: khong luu duoc mid khong duoc bien mot tin DA dang thanh
    that bai (nguoi goi se gui lai -> Ong Chu nhan hai bao cao)."""
    h = _harness()
    try:
        blocker = h.tmp / "blocker"
        blocker.write_text("i am a file", encoding="utf-8")
        code, _ = _cli(h, "--text", "hello", "--luu-mid", blocker / "mid.json")
        assert code == 0
        assert h.tg.methods() == ["sendMessage"]
        assert _prints(h)[0].startswith("da dang | message_id=9001")
        assert "khong ghi duoc --luu-mid" in _prints(h)[1]
    finally:
        h.__exit__()


# =========================================================================
# Dinh tuyen chat + topic
# =========================================================================
def test_to_overrides_to_env_and_thread_is_sent_as_int():
    h = _harness()
    try:
        assert _cli(h, "--text", "x", "--to", "-555", "--to-env", "TELEGRAM_GROUP_ID",
                    "--thread", "62")[0] == 0
        sent, = h.tg.sent()
        assert sent["chat_id"] == "-555" and sent["message_thread_id"] == 62
    finally:
        h.__exit__()


def test_unknown_topic_name_exits_before_anything_is_sent():
    """Sai ten topic ma van gui thi bao cao roi vao General — sai cho, va
    --luu-mid ghim mid cua mot tin khong ai reply."""
    h = _harness()
    try:
        code, err = _cli(h, "--text", "x", "--thread-name", "ghost")
        assert code == 1 and "'ghost'" in err and "topics.json" in err, err
        assert h.tg.methods() == []
    finally:
        h.__exit__()


def test_unreadable_topics_file_exits_before_anything_is_sent():
    h = _harness()
    try:
        env_load.topics_path().write_text("{cut", encoding="utf-8")
        code, err = _cli(h, "--text", "x", "--thread-name", "vera")
        assert code == 1 and err.startswith("Khong doc duoc"), err
        assert h.tg.methods() == []
    finally:
        h.__exit__()


def test_missing_chat_id_exits_non_zero_without_sending():
    h = _harness(TELEGRAM_CHANNEL_ID=None, TELEGRAM_GROUP_ID=None)
    try:
        code, err = _cli(h, "--text", "x", "--to-env", "TELEGRAM_GROUP_ID")
        assert code == 1 and err.startswith("Thieu chat_id"), err
        assert h.tg.methods() == []
    finally:
        h.__exit__()


def test_missing_bot_token_exits_non_zero_without_sending():
    h = _harness(TELEGRAM_BOT_TOKEN=None)
    try:
        code, err = _cli(h, "--text", "x")
        assert (code, err) == (1, "Thieu TELEGRAM_BOT_TOKEN")
        assert h.tg.methods() == []
    finally:
        h.__exit__()


def test_nothing_to_send_exits_non_zero():
    h = _harness()
    try:
        code, err = _cli(h)
        assert code == 1 and "--text" in err
        assert h.tg.methods() == []
    finally:
        h.__exit__()


# =========================================================================
# Lam sach chu truoc khi gui (Telegram TU CHOI ca tin khi gap the khoi)
# =========================================================================
def test_agent_html_and_literal_newlines_are_cleaned_in_the_outgoing_payload():
    h = _harness()
    try:
        raw = ("<p>Dong <b>mot</b> — het</p><ul><li>muc a</li><li>muc b</li></ul>"
               "<font color=red>x</font><br>cuoi")
        assert _cli(h, "--text", raw)[0] == 0
        text = h.tg.texts()[0]
        assert text == "Dong <b>mot</b>, het\n\n• muc a\n• muc b\n\nx\ncuoi", repr(text)

        assert _cli(h, "--text", "a\\nb\\r\\nc")[0] == 0
        assert h.tg.texts()[1] == "a\nb\nc"
    finally:
        h.__exit__()


# =========================================================================
# Anh / file / album
# =========================================================================
def _png(h, name="a.png"):
    p = h.tmp / name
    p.write_bytes(b"\x89PNG" + name.encode())
    return p


def test_photo_caption_comes_from_file_and_goes_to_the_topic():
    h = _harness()
    try:
        cap = h.tmp / "cap.txt"
        cap.write_text("<b>Tieu de</b><br>than bai", encoding="utf-8")
        mid_file = h.state / "mid.json"
        code, _ = _cli(h, "--photo", _png(h), "--file", cap, "--caption", "ignored",
                       "--to-env", "TELEGRAM_GROUP_ID", "--thread-name", "bob",
                       "--luu-mid", mid_file)
        assert code == 0
        sent, = h.tg.sent("sendPhoto")
        assert sent["chat_id"] == "-1001" and sent["message_thread_id"] == str(BOB)
        assert sent["caption"] == "<b>Tieu de</b>\nthan bai" and sent["parse_mode"] == "HTML"
        assert sent["_files"] == {"photo": "a.png"}
        saved = json.loads(mid_file.read_text(encoding="utf-8"))
        assert saved["message_ids"] == [9001] and saved["message_id"] == 9001
    finally:
        h.__exit__()


def test_caption_over_1024_is_refused_locally_with_non_zero_exit_for_every_media_kind():
    """Telegram se tu choi ca tin; chan som de khoi upload anh roi moi biet.
    La TelegramReject (Exception thuong) — CLI doi thanh ma thoat 1."""
    h = _harness()
    try:
        long_cap = "a" * (publish.CAPTION_LIMIT + 1)
        for flag in ("--photo", "--document"):
            code, err = _cli(h, flag, _png(h), "--caption", long_cap)
            assert code == 1 and "Caption 1025 ky tu" in err, (flag, err)
        code, err = _cli(h, "--album", _png(h), _png(h, "b.png"), "--caption", long_cap)
        assert code == 1 and "Caption 1025 ky tu" in err
        assert h.tg.methods() == [] and _prints(h) == []
        # Dung tran thi di.
        assert _cli(h, "--photo", _png(h), "--caption", "a" * publish.CAPTION_LIMIT)[0] == 0
        assert h.tg.methods() == ["sendPhoto"]
    finally:
        h.__exit__()


def test_document_keeps_the_original_file_and_routes_like_a_photo():
    h = _harness()
    try:
        assert _cli(h, "--document", _png(h, "frame_hd.png"), "--caption", "HD",
                    "--thread", "62")[0] == 0
        sent, = h.tg.sent("sendDocument")
        assert sent["_files"] == {"document": "frame_hd.png"}
        assert sent["caption"] == "HD" and sent["message_thread_id"] == "62"
        assert sent["chat_id"] == "-1002"
    finally:
        h.__exit__()


def test_album_mixes_urls_and_local_files_caption_only_on_first_item():
    h = _harness()
    try:
        a, b = _png(h, "a.png"), _png(h, "b.png")
        code, _ = _cli(h, "--album", a, "https://cdn.test/x.jpg", b,
                       "--caption", "<b>album</b>", "--thread", "62")
        assert code == 0
        sent, = h.tg.sent("sendMediaGroup")
        assert sent["chat_id"] == "-1002" and sent["message_thread_id"] == "62"
        assert json.loads(sent["media"]) == [
            {"type": "photo", "caption": "<b>album</b>", "parse_mode": "HTML",
             "media": "attach://file0"},
            {"type": "photo", "media": "https://cdn.test/x.jpg"},
            {"type": "photo", "media": "attach://file2"}]
        assert sent["_files"] == {"file0": "a.png", "file2": "b.png"}
    finally:
        h.__exit__()


def test_album_closes_local_files_even_when_the_upload_dies():
    h = _harness()
    try:
        opened = []
        real_open = open

        def spy_open(*a, **kw):
            fh = real_open(*a, **kw)
            opened.append(fh)
            return fh
        h.patch(publish, "open", spy_open)
        h.api.script(httpx.ConnectError("network down"))
        try:
            publish.send_media_group("TOK", "-1002", [_png(h, "a.png"), _png(h, "b.png")])
        except httpx.ConnectError:
            pass
        else:
            raise AssertionError("loi mang phai noi len cho nguoi goi")
        assert len(opened) == 2 and all(fh.closed for fh in opened)
    finally:
        h.__exit__()


def test_album_refused_by_telegram_raises_plain_exception_not_system_exit():
    """moat_publish._notify / approve_post bat `except Exception`: SystemExit
    tung xuyen qua va giet ca tien trinh cron."""
    h = _harness()
    try:
        h.api.script({"ok": False, "description": "Bad Request: WEBPAGE_MEDIA_EMPTY"})
        try:
            publish.send_media_group("TOK", "-1002", ["https://cdn.test/x.jpg"], "cap")
        except publish.TelegramReject as e:
            assert isinstance(e, Exception) and "WEBPAGE_MEDIA_EMPTY" in str(e)
            sent, = h.tg.sent("sendMediaGroup")
            assert json.loads(sent["media"])[0]["media"] == "https://cdn.test/x.jpg"
        else:
            raise AssertionError("phai nem TelegramReject")
    finally:
        h.__exit__()


# =========================================================================
# send_topic / send_topic_with_keyboard — ham cua script cron, KHONG nem
# =========================================================================
def test_send_topic_routes_to_the_roles_thread_in_the_group():
    h = _harness()
    try:
        assert publish.send_topic("<b>bao cao</b>", "vera") is True
        sent, = h.tg.sent()
        assert sent["chat_id"] == "-1001" and sent["message_thread_id"] == VERA
        assert sent["text"] == "<b>bao cao</b>"
        # Vai khong co topic: van gui, vao General (khong co message_thread_id).
        assert publish.send_topic("x", "nobody") is True
        assert "message_thread_id" not in h.tg.sent()[1]
    finally:
        h.__exit__()


def test_send_topic_falls_back_to_channel_when_group_is_not_configured():
    h = _harness(TELEGRAM_GROUP_ID=None)
    try:
        assert publish.send_topic("x", "vera") is True
        assert h.tg.sent()[0]["chat_id"] == "-1002"
    finally:
        h.__exit__()


def test_send_topic_without_token_prints_the_text_instead_of_losing_it():
    h = _harness(TELEGRAM_BOT_TOKEN=None)
    try:
        assert publish.send_topic("bao cao quan trong", "vera") is False
        assert h.tg.methods() == []
        assert _prints(h)[-1] == "bao cao quan trong" and "thieu TELEGRAM_BOT_TOKEN" in _prints(h)[0]
    finally:
        h.__exit__()


def test_send_topic_swallows_refusal_and_network_errors():
    h = _harness()
    try:
        h.api.script({"ok": False, "description": "Too Many Requests"},
                     httpx.ConnectError("down"))
        assert publish.send_topic("x", "vera") is False
        assert publish.send_topic("x", "vera") is False
        warns = _prints(h)
        assert "TelegramReject" in warns[0] and "Too Many Requests" in warns[0]
        assert "ConnectError" in warns[1]
    finally:
        h.__exit__()


def test_send_topic_with_keyboard_returns_the_message_so_it_can_be_edited():
    h = _harness()
    try:
        kb = {"inline_keyboard": [[{"text": "Duyet", "callback_data": "ok:1"}]]}
        res = publish.send_topic_with_keyboard("chon <br>di", "bob", kb)
        assert res == {"message_id": 9001}
        sent, = h.tg.sent()
        assert sent["reply_markup"] == kb and sent["message_thread_id"] == BOB
        assert sent["chat_id"] == "-1001" and sent["text"] == "chon \ndi"
        assert sent["disable_web_page_preview"] is True
    finally:
        h.__exit__()


def test_send_topic_with_keyboard_returns_none_on_refusal_or_missing_config():
    h = _harness()
    try:
        h.api.script({"ok": False, "description": "BUTTON_DATA_INVALID"})
        assert publish.send_topic_with_keyboard("x", "bob", {"inline_keyboard": []}) is None
        assert "BUTTON_DATA_INVALID" in _prints(h)[0]
        h.patch_env(os.environ, TELEGRAM_BOT_TOKEN=None)
        assert publish.send_topic_with_keyboard("y", "bob", {"inline_keyboard": []}) is None
        assert len(h.tg.sent()) == 1 and _prints(h)[-1] == "y"
    finally:
        h.__exit__()


def test_send_text_returns_the_last_chunk_result():
    h = _harness()
    try:
        res = publish.send_text("TOK", "-1001", _long_report(), thread=VERA)
        assert res == {"message_id": 9000 + len(h.tg.sent())} and len(h.tg.sent()) >= 3
    finally:
        h.__exit__()


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
