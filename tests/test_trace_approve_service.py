#!/usr/bin/env python3
"""LOW-311 — luoi doi chieu vet cho approve_service: dieu phoi tin nhan
(`handle_message`), vong poll (`loop`), cuu bai ket `publishing` luc khoi dong.

Moi kich ban dung theo mot SU CO THAT da co ticket va khang dinh ba thu: vet goi
ra ngoai (thu tu + tham so), tep state sau cung, tin gui cho Ong Chu. Canh I/O
thay bang tests/trace_harness.py — khong mang, khong thread, khong state that.

Chay:  python tests/test_trace_approve_service.py
"""
import json
import os
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import approve_base as base            # noqa: E402
import approve_dispatch as dispatch    # noqa: E402
import approve_pick as pick            # noqa: E402
import approve_post as post            # noqa: E402
import approve_service as svc          # noqa: E402
import state_paths                     # noqa: E402
from trace_harness import Harness, StopLoop, callback, message, run_tests  # noqa: E402

VERA = 77          # topic id cua Vera trong topics.json gia
MILES = 88


def _harness():
    h = Harness(svc, base, pick, dispatch, post)
    h.__enter__()
    h.topics({"vera": VERA, "miles": MILES})
    h.capture_logs()
    h.inline_background()
    h.patch_env(os.environ, CT_CHAT_VIA_GATEWAY=None)
    # Hai cong dung TRUOC "chon so" doc state rieng cua approve_post — o day chi
    # thu DIEU PHOI cua approve_service nen de chung tra "khong phai cua toi".
    h.patch(svc, "_label_reason_redo", h.spy("_label_reason_redo", returns=False))
    h.patch(svc, "handle_reply_approval", h.spy("handle_reply_approval", returns=False))
    return h


def _report_sent(h, vai, *mids):
    """scan_submit vua gui bao cao cua `vai` thanh cac manh co message_id `mids`."""
    p = h.state / state_paths.REPORT_MESSAGE_ID_FILE.format(vai)
    p.write_text(json.dumps({"message_ids": list(mids), "message_id": mids[-1]}),
                 encoding="utf-8")


def _bg(h):
    return [(n, d["fn"], d["args"]) for n, d in h.trace.of("bg")]


# =========================================================================
# handle_message — cong vao
# =========================================================================
def test_own_bot_message_leaves_no_trace():
    h = _harness()
    try:
        m = message(1, "1, 2", thread=VERA)
        m["from"]["is_bot"] = True
        svc.handle_message(h.token, h.group, m)
        assert h.trace.events == [], h.trace.kinds()
    finally:
        h.__exit__()


def test_message_from_other_chat_is_dropped_without_reply():
    h = _harness()
    try:
        svc.handle_message(h.token, h.group, message(2, "/bai x y", chat="-999"))
        assert h.tg.methods() == [] and _bg(h) == []
        assert any("khong phai group" in t for t in h.logs("vao"))
    finally:
        h.__exit__()


def test_stranger_is_refused_before_any_bytes_hit_disk():
    """06/09/2026: allowlist phai dung TRUOC buoc tai anh — nguoi la trong group
    tung ghi duoc tep vao may ma khong qua cong nao."""
    h = _harness()
    try:
        (h.state / state_paths.BOSS_IDS_FILE).write_text("[42]", encoding="utf-8")
        m = message(3, thread=VERA, user=666, caption="1, 2",
                    photo=[{"file_id": "small"}, {"file_id": "big"}])
        svc.handle_message(h.token, h.group, m)
        assert h.tg.methods() == ["sendMessage"], h.tg.methods()   # KHONG co getFile
        sent = h.tg.sent()[0]
        assert "Chỉ Ông Chủ" in sent["text"] and "666" in sent["text"]
        assert sent["message_thread_id"] == VERA
        assert _bg(h) == []
        assert not (h.state / "telegram_incoming").exists()
    finally:
        h.__exit__()


def test_unsupported_message_type_gets_an_answer_not_silence():
    h = _harness()
    try:
        svc.handle_message(h.token, h.group, message(4, thread=MILES, sticker={"x": 1}))
        assert h.tg.methods() == ["sendMessage"]
        assert "sticker" in h.tg.texts()[0] and "chưa hỗ trợ" in h.tg.texts()[0]
        assert _bg(h) == []
    finally:
        h.__exit__()


def test_slash_command_goes_to_command_thread_never_to_chat():
    h = _harness()
    try:
        m = message(5, "/bai https://a.b/c dre", thread=MILES)
        svc.handle_message(h.token, h.group, m)
        assert _bg(h) == [("lenh", "handle_command",
                           (h.token, h.group, m, MILES, "/bai https://a.b/c dre"))]
        assert h.tg.methods() == []
        # lenh slash dung TRUOC ca cong "ly do lam lai"
        assert h.trace.names("fn") == []
    finally:
        h.__exit__()


# =========================================================================
# LOW-25 / LOW-28 — reply vao bao cao cu thi IM LANG
# =========================================================================
def test_low25_reply_to_old_report_warns_instead_of_silence():
    """12/09/2026 07:24: Vera gui ba ban bao cao, Ong Chu reply "1, 7 - Dre" vao
    ban thu hai -> khong bai, khong loi, khong mot dong."""
    h = _harness()
    try:
        _report_sent(h, "vera", 300)                 # ban MOI NHAT la tin 300
        svc.handle_message(h.token, h.group,
                           message(10, "1, 7 - Dre", thread=VERA, reply_to=200))
        # khong tao bai; tin roi ve hoi thoai (blog) SAU khi da canh bao
        assert [n for n, _, _ in _bg(h)] == ["chat"], "reply ban cu KHONG duoc tao bai"
        assert h.trace.kinds()[-2:] == ["tg:sendMessage", "bg:chat"]
        assert h.tg.methods() == ["sendMessage"]
        t = h.tg.texts()[0]
        assert "Chưa tạo bài" in t and "báo cáo cũ" in t and "Vera" in t, t
        assert h.tg.sent()[0]["message_thread_id"] == VERA
    finally:
        h.__exit__()


def test_low25_bare_number_without_reply_says_so():
    """Trong topic, Telegram gan san reply_to = tin goc topic cho MOI tin: go
    troi "5" KHONG phai reply (quirk 06/09/2026)."""
    h = _harness()
    try:
        _report_sent(h, "vera", 300)
        svc.handle_message(h.token, h.group, message(11, "5", thread=VERA))
        assert [n for n, _, _ in _bg(h)] == ["chat"]
        assert "không bấm Reply" in h.tg.texts()[0]
    finally:
        h.__exit__()


def test_reply_to_latest_report_dispatches_pick_with_parsed_command():
    h = _harness()
    try:
        _report_sent(h, "vera", 300)
        svc.handle_message(h.token, h.group,
                           message(12, "1, 7 - Dre", thread=VERA, reply_to=300))
        brand = pick.BRAND
        assert _bg(h) == [("chon", "_process_pick",
                           (h.token, h.group, VERA, "vera",
                            [(1, "dre", brand), (7, "dre", brand)], None))], _bg(h)
        assert h.tg.methods() == []
    finally:
        h.__exit__()


def test_reply_to_first_chunk_of_split_report_is_accepted():
    """12/09/2026: bao cao 27 muc bi Telegram chia doi, muc 1 nam o manh DAU."""
    h = _harness()
    try:
        _report_sent(h, "vera", 300, 301)
        svc.handle_message(h.token, h.group, message(13, "1", thread=VERA, reply_to=300))
        assert [n for n, _, _ in _bg(h)] == ["chon"]
    finally:
        h.__exit__()


def test_number_in_a_writer_topic_is_chat_not_pick():
    h = _harness()
    try:
        m = message(14, "1, 2", thread=MILES, reply_to=300)
        svc.handle_message(h.token, h.group, m)
        assert _bg(h) == [("chat", "handle_chat", (h.token, h.group, m, MILES, "1, 2"))]
    finally:
        h.__exit__()


def test_redo_reason_swallows_message_before_pick_gate():
    """"4: chart bi cat" roi vao topic chon tin khong duoc hieu la chon bai 4."""
    h = _harness()
    try:
        _report_sent(h, "vera", 300)
        h.patch(svc, "_label_reason_redo", h.spy("_label_reason_redo", returns=True))
        svc.handle_message(h.token, h.group, message(15, "4", thread=VERA, reply_to=300))
        assert h.trace.names("fn") == ["_label_reason_redo"]
        assert _bg(h) == [] and h.tg.methods() == []
    finally:
        h.__exit__()


def test_low134_reply_approval_swallows_message_before_pick_gate():
    h = _harness()
    try:
        h.patch(svc, "handle_reply_approval", h.spy("handle_reply_approval", returns=True))
        svc.handle_message(h.token, h.group, message(16, "duyệt", thread=MILES, reply_to=9))
        assert h.trace.names("fn") == ["_label_reason_redo", "handle_reply_approval"]
        assert _bg(h) == []
    finally:
        h.__exit__()


def test_gateway_brand_stays_silent_on_chat_but_still_picks():
    h = _harness()
    try:
        h.patch_env(os.environ, CT_CHAT_VIA_GATEWAY="1")
        _report_sent(h, "vera", 300)
        svc.handle_message(h.token, h.group, message(17, "hôm nay thế nào", thread=VERA))
        assert _bg(h) == [] and h.tg.methods() == []
        svc.handle_message(h.token, h.group, message(18, "2", thread=VERA, reply_to=300))
        assert [n for n, _, _ in _bg(h)] == ["chon"]
    finally:
        h.__exit__()


# =========================================================================
# anh dinh kem
# =========================================================================
def _fake_file_download(h, data=b"\x89PNG"):
    got = []

    class _Client:
        def __init__(self, *a, **kw): pass
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def get(self, url):
            got.append(url)
            h.trace.add("http", "GET", url=url)
            return types.SimpleNamespace(content=data)
    h.patch(svc, "httpx", types.SimpleNamespace(Client=_Client))
    h.tg.script("getFile", {"ok": True, "result": {"file_path": "photos/f.jpg"}})
    return got


def test_photo_only_message_reaches_chat_with_real_path():
    """Caption nam o field `caption`, va tin CHI co anh van phai di tiep."""
    h = _harness()
    try:
        _fake_file_download(h)
        m = message(20, thread=MILES, photo=[{"file_id": "small"}, {"file_id": "big"}])
        svc.handle_message(h.token, h.group, m)
        assert h.tg.sent("getFile") == [{"token": h.token, "file_id": "big"}]
        out = h.state / "telegram_incoming" / "20.jpg"
        assert out.read_bytes() == b"\x89PNG"
        (name, fn, args), = _bg(h)
        assert (name, fn) == ("chat", "handle_chat")
        assert args[4] == f"[Ảnh đính kèm đã tải về: {out}]\n(không có chú thích kèm theo)"
    finally:
        h.__exit__()


def test_document_filename_cannot_escape_incoming_dir():
    h = _harness()
    try:
        _fake_file_download(h)
        m = message(21, thread=MILES, caption="sửa ảnh này",
                    document={"file_id": "d", "mime_type": "image/png",
                              "file_name": "x.png/../../../evil"})
        svc.handle_message(h.token, h.group, m)
        files = sorted(p.name for p in (h.state / "telegram_incoming").iterdir())
        assert files == ["21.jpg"], files
        m2 = message(22, thread=MILES, caption="c",
                     document={"file_id": "d", "mime_type": "image/webp", "file_name": "A.WEBP"})
        h.tg.script("getFile", {"ok": True, "result": {"file_path": "p"}})
        svc.handle_message(h.token, h.group, m2)
        assert (h.state / "telegram_incoming" / "22.webp").exists()
    finally:
        h.__exit__()


def test_failed_getfile_falls_back_to_text_only():
    h = _harness()
    try:
        h.tg.script("getFile", {"ok": False, "description": "file is too big"})
        m = message(23, thread=MILES, caption="xem giúp", photo=[{"file_id": "p"}])
        svc.handle_message(h.token, h.group, m)
        (_, _, args), = _bg(h)
        assert args[4] == "xem giúp"
    finally:
        h.__exit__()


# =========================================================================
# loop() — vong poll
# =========================================================================
def _loop_harness():
    h = _harness()
    h.fake_time(svc)
    h.patch(svc, "load_secrets", lambda: (h.token, h.channel, h.group))
    h.patch(svc, "HERMES_HOME", str(h.tmp / "hermes_home"))
    h.patch(svc, "_redo_all_done_limit", h.spy("_redo_all_done_limit"))
    h.patch(svc, "report_progress_kanban", h.spy("report_progress_kanban"))
    return h


def _run_loop(h):
    try:
        svc.loop()
    except StopLoop:
        return
    raise AssertionError("loop() thoat ma khong qua StopLoop")


def test_loop_writes_offset_before_handling_and_survives_bad_update():
    """Offset ghi TRUOC tung update (mat mot lenh re hon dang trung), va mot
    update hong khong duoc keo ca lo con lai xuong."""
    h = _loop_harness()
    try:
        seen = []

        def _handle(token, group, msg):
            seen.append((msg["message_id"], svc._read_offset()))
            if msg["message_id"] == 1:
                raise RuntimeError("update hong")
        h.patch(svc, "handle_message", _handle)
        cq = callback("ok:d1", thread=MILES)
        h.tg.script("getUpdates",
                    {"ok": True, "result": [
                        {"update_id": 10, "message": {"message_id": 1}},
                        {"update_id": 11, "message": {"message_id": 2}},
                        {"update_id": 12, "callback_query": cq}]},
                    StopLoop())
        _run_loop(h)
        assert seen == [(1, 11), (2, 12)], seen
        assert (h.state / "offset.txt").read_text() == "13"
        assert _bg(h) == [("nut", "_process_button", (h.token, h.channel, cq))]
        assert h.trace.of("bg")[0][1]["thread_id"] == MILES
        assert any("update 10 hong" in t for t in h.logs("loi"))
        # quet kanban + het han lam lai chay SAU khi xu ly lo, moi vong mot lan
        assert h.trace.names("fn")[-2:] == ["_redo_all_done_limit", "report_progress_kanban"]
        # vong hai xin dung offset moi
        assert h.tg.sent("getUpdates")[1]["offset"] == 13
    finally:
        h.__exit__()


def test_loop_409_alerts_once_sleeps_then_reports_reconnect():
    h = _loop_harness()
    try:
        bad = {"ok": False, "description": "Conflict: terminated by other getUpdates"}
        h.tg.script("getUpdates", bad, bad, {"ok": True, "result": []}, StopLoop())
        _run_loop(h)
        assert h.tg.methods() == ["getUpdates", "sendMessage", "getUpdates",
                                  "getUpdates", "sendMessage", "getUpdates"], h.tg.methods()
        mat, lai = h.tg.texts()
        assert "từ chối getUpdates" in mat and "Conflict" in mat
        assert "Đã kết nối lại" in lai and "0.2 phút" in lai, lai     # 2 x sleep(5)
        assert [d["seconds"] for _, d in h.trace.of("clock")] == [5, 5]
    finally:
        h.__exit__()


def test_loop_network_exception_backs_off_and_reports_recovery():
    h = _loop_harness()
    try:
        h.tg.script("getUpdates", ConnectionError("dns"), ConnectionError("dns"),
                    {"ok": True, "result": []}, StopLoop())
        _run_loop(h)
        assert [d["seconds"] for _, d in h.trace.of("clock")] == [5, 10]
        assert len(h.tg.texts()) == 1 and "Đã kết nối lại" in h.tg.texts()[0]
        assert sum("vong poll" in t for t in h.logs("loi")) == 2
    finally:
        h.__exit__()


def test_corrupt_offset_file_restarts_from_zero_instead_of_crash_loop():
    h = _loop_harness()
    try:
        (h.state / "offset.txt").write_text("12\x00garbage")
        h.tg.script("getUpdates", StopLoop())
        _run_loop(h)
        assert h.tg.sent("getUpdates")[0]["offset"] == 0
    finally:
        h.__exit__()


def test_startup_flags_tirith_enabled_without_binary():
    h = _loop_harness()
    try:
        home = Path(svc.HERMES_HOME)
        home.mkdir()
        (home / "config.yaml").write_text(
            "security:\n  tirith_enabled: true\n  tirith_path: no-such-binary-low311\n"
            "  tirith_fail_open: true\n", encoding="utf-8")
        svc._audit_tirith()
        (line,) = [t for t in h.logs("start") if "tirith" in t]
        assert "KHONG co binary 'no-such-binary-low311'" in line and "fail_open" in line
        # LOW-305: mot cong bao mat dang TAT phai la WARNING, khong duoc lan giua
        # hang nghin dong INFO — day la dong `journalctl -p warning` phai loc ra.
        (muc,) = [lv for t, lv in h.log_levels("start") if "tirith" in t]
        assert muc == "WARNING", muc
        (home / "config.yaml").write_text("tirith_enabled: false\n", encoding="utf-8")
        svc._audit_tirith()
        assert len([t for t in h.logs("start") if "tirith" in t]) == 1
    finally:
        h.__exit__()


# =========================================================================
# cuu bai ket `publishing` sau restart
# =========================================================================
def test_rescue_splits_already_on_channel_from_never_sent():
    """Bai DA co dau channel_*_mid ma ha ve publish_failed = moi Ong Chu dang
    trung. Bai chua co dau moi duoc mo khoa. Bai moi bam (<15 phut) de yen."""
    h = _loop_harness()
    try:
        now = int(h.clock.now)
        h.write_draft("on-channel", status="publishing", decided_at=now - 3600,
                      channel_album_mid=9)
        h.write_draft("never-sent", status="publishing", decided_at=now - 3600)
        h.write_draft("just-clicked", status="publishing", decided_at=now - 60)
        h.write_draft("other", status="pending")
        (h.drafts / "never-sent.meta.json").write_text('{"status": "publishing"}')
        (h.drafts / "broken.json").write_text("{cut")
        svc._rescue_article_end_publishing(h.token, h.group)
        st = {k: h.read_draft(k)["status"]
              for k in ("on-channel", "never-sent", "just-clicked", "other")}
        assert st == {"on-channel": "published", "never-sent": "publish_failed",
                      "just-clicked": "publishing", "other": "pending"}, st
        assert "rescue_note" in h.read_draft("never-sent")
        assert json.loads((h.drafts / "never-sent.meta.json").read_text()) == {
            "status": "publishing"}, "sidecar khong phai draft, khong duoc dung vao"
        (t,) = h.tg.texts()
        assert "đừng bấm Duyệt lại" in t and "on-channel" in t
        assert "bấm Duyệt lại nếu chưa lên" in t and "never-sent" in t
        assert "just-clicked" not in t
    finally:
        h.__exit__()


def test_rescue_says_nothing_when_nothing_is_stuck():
    h = _loop_harness()
    try:
        h.write_draft("fine", status="published")
        svc._rescue_article_end_publishing(h.token, h.group)
        assert h.tg.methods() == []
    finally:
        h.__exit__()


# =========================================================================
# CLI push (LOW-160 / LOW-296)
# =========================================================================
def test_low160_failed_push_exits_nonzero_and_saves_no_card_id():
    h = _loop_harness()
    try:
        h.write_draft("d1")
        h.patch(svc, "draft_push", h.spy("draft_push", returns={
            "ok": False, "description": "RemoteProtocolError"}))
        assert svc._push_replace(h.token, h.group, "d1", MILES) == 1
        assert "tg_card_message_id" not in h.read_draft("d1")
    finally:
        h.__exit__()


def test_low296_identical_resubmit_is_not_pushed_and_changed_one_replaces_card():
    h = _loop_harness()
    try:
        h.write_draft("d1", caption="ban 1")
        h.patch(svc, "draft_push", h.spy("draft_push", returns={
            "ok": True, "result": {"message_id": 700}, "extra_ids": [701]}))
        assert svc._push_replace(h.token, h.group, "d1", MILES) == 0
        d = h.read_draft("d1")
        assert (d["tg_card_message_id"], d["tg_extra_message_ids"]) == (700, [701])
        # nop lai Y HET: khong day, khong xoa
        assert svc._push_replace(h.token, h.group, "d1", MILES) == 0
        assert h.trace.names("fn") == ["draft_push"] and h.tg.methods() == []
        # caption doi: the moi len roi the cu (ca tin phu) moi bi xoa
        d["caption"] = "ban 2"
        (h.drafts / "d1.json").write_text(json.dumps(d), encoding="utf-8")
        assert svc._push_replace(h.token, h.group, "d1", MILES) == 0
        assert h.trace.names("fn") == ["draft_push", "draft_push"]
        assert h.tg.methods() and all(m.startswith("deleteMessage") for m in h.tg.methods())
        gone = [i for d in h.tg.sent() for i in (d.get("message_ids") or [d.get("message_id")])]
        assert sorted(gone) == [700, 701], gone
    finally:
        h.__exit__()


if __name__ == "__main__":
    sys.exit(run_tests(globals()))
