#!/usr/bin/env python3
"""Thong bao ro khi mot buoc khong thuc hien duoc (09/09/2026): 3 mieng moi trong
approve_dispatch.py — link_result/reason_task (nut bam cu tra loi dung trang thai
thuc) va canh bao "khong phan hoi" khi mot vai treo giua running trong
report_progress_kanban. Test o day chi phan LOGIC THUAN (khong Telegram/kanban.db
that), theo dung kieu tests/test_route_missing_images.py: monkeypatch truc tiep
thuoc tinh module, tu luu/phuc hoi trong finally.

Chay:  venv/bin/python tests/test_report_stalled.py
"""
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import approve_dispatch as dg                                  # noqa: E402


# --------------------------------------------------------------- link_result
def test_link_result_not_yet_has_then_none():
    with tempfile.TemporaryDirectory() as tmp:
        cu = dg.STORY_RESULT
        dg.STORY_RESULT = Path(tmp) / "tin.json"
        try:
            assert dg.link_result("t_khong_ton_tai") is None
            assert dg.link_result(None) is None
        finally:
            dg.STORY_RESULT = cu


def test_link_result_use_format_has_thread():
    with tempfile.TemporaryDirectory() as tmp:
        cu = dg.STORY_RESULT
        dg.STORY_RESULT = Path(tmp) / "tin.json"
        dg.STORY_RESULT.write_text(json.dumps(
            {"t_1": {"chat": -1001234567890, "thread": 52, "mid": 999}}), encoding="utf-8")
        try:
            assert dg.link_result("t_1") == "https://t.me/c/1234567890/52/999"
        finally:
            dg.STORY_RESULT = cu


def test_link_result_no_has_thread_then_drop_guess_measure():
    with tempfile.TemporaryDirectory() as tmp:
        cu = dg.STORY_RESULT
        dg.STORY_RESULT = Path(tmp) / "tin.json"
        dg.STORY_RESULT.write_text(json.dumps(
            {"t_1": {"chat": -1001234567890, "thread": None, "mid": 999}}), encoding="utf-8")
        try:
            assert dg.link_result("t_1") == "https://t.me/c/1234567890/999"
        finally:
            dg.STORY_RESULT = cu


def test_link_result_dm_no_right_supergroup_then_none():
    """Chat thuong (DM, id duong, khong -100...) khong lam duoc deep-link kieu nay."""
    with tempfile.TemporaryDirectory() as tmp:
        cu = dg.STORY_RESULT
        dg.STORY_RESULT = Path(tmp) / "tin.json"
        dg.STORY_RESULT.write_text(json.dumps(
            {"t_1": {"chat": 8112291996, "thread": None, "mid": 5}}), encoding="utf-8")
        try:
            assert dg.link_result("t_1") is None
        finally:
            dg.STORY_RESULT = cu


# --------------------------------------------------------------------- reason_task
def test_reason_task_take_from_last_run():
    cu = dg.hermes_adapter.last_run
    dg.hermes_adapter.last_run = lambda tid: {"tom_tat": None, "loi": "thieu anh that", "metadata": {}}
    try:
        assert dg.reason_task("t_1") == "thieu anh that"
    finally:
        dg.hermes_adapter.last_run = cu


def test_reason_task_not_yet_run_attempt_which_then_string_empty():
    cu = dg.hermes_adapter.last_run
    dg.hermes_adapter.last_run = lambda tid: {}
    try:
        assert dg.reason_task("t_1") == ""
    finally:
        dg.hermes_adapter.last_run = cu


# --------------------------------------------------- canh bao "khong phan hoi"
def _run_report_progress_fake(tmp, rows, gui_ghi_lai):
    """Chay report_progress_kanban() voi kanban/telegram gia, tra list text da 'send'."""
    state = Path(tmp)
    cu = (dg.ALREADY_REPORT_PROGRESS, dg.STORY_RESULT, dg.ALREADY_REPORT_STALLED,
          dg.hermes_adapter.has_kanban, dg.hermes_adapter.job, dg.call, dg.env_load.topics_path)
    dg.ALREADY_REPORT_PROGRESS = state / "reported_progress.json"
    dg.STORY_RESULT = state / "task_result_messages.json"
    dg.ALREADY_REPORT_STALLED = state / "reported_stalled.json"
    dg.hermes_adapter.has_kanban = lambda: True
    dg.hermes_adapter.job = lambda tu_ts=None: list(rows)
    tp = state / "topics.json"
    tp.write_text(json.dumps({"miles": 52}), encoding="utf-8")
    dg.env_load.topics_path = lambda: tp

    def _call_gia(token, method, **kw):
        gui_ghi_lai.append(kw.get("text", ""))
        return {"ok": True, "result": {"message_id": len(gui_ghi_lai)}}
    dg.call = _call_gia
    try:
        dg.report_progress_kanban("TOKEN", -100999)
    finally:
        (dg.ALREADY_REPORT_PROGRESS, dg.STORY_RESULT, dg.ALREADY_REPORT_STALLED,
         dg.hermes_adapter.has_kanban, dg.hermes_adapter.job, dg.call, dg.env_load.topics_path) = cu


def test_stalled_report_when_running_over_long_time():
    with tempfile.TemporaryDirectory() as tmp:
        now = time.time()
        rows = [{"id": "t_1", "vai": "miles", "trang_thai": "running",
                  "tieu_de": "Bai test", "tao_luc": now - 3000,
                  "bat_dau_luc": now - dg.THRESHOLD_STALLED_MINUTES * 60 - 60,
                  "xong_luc": None, "ket_qua": None, "loi": None}]
        gui = []
        _run_report_progress_fake(tmp, rows, gui)
        assert any("không phản hồi" in t for t in gui), gui
        # Da ghi lai reported_stalled de vong sau khong bao lap ngay.
        treo = json.loads((Path(tmp) / "reported_stalled.json").read_text(encoding="utf-8"))
        assert "t_1" in treo


def test_stalled_not_yet_over_threshold_then_silent():
    with tempfile.TemporaryDirectory() as tmp:
        now = time.time()
        rows = [{"id": "t_1", "vai": "miles", "trang_thai": "running",
                  "tieu_de": "Bai test", "tao_luc": now - 60,
                  "bat_dau_luc": now - 60,       # moi chay 1 phut, chua treo
                  "xong_luc": None, "ket_qua": None, "loi": None}]
        gui = []
        _run_report_progress_fake(tmp, rows, gui)
        assert not any("không phản hồi" in t for t in gui), gui


def test_stalled_no_report_repeat_within_of_count_again_report():
    with tempfile.TemporaryDirectory() as tmp:
        now = time.time()
        state = Path(tmp)
        # Da bao "treo" 5 phut truoc — con trong cua so AGAIN_REPORT_STALLED_MINUTES (30p).
        (state / "reported_stalled.json").write_text(
            json.dumps({"t_1": now - 5 * 60}), encoding="utf-8")
        rows = [{"id": "t_1", "vai": "miles", "trang_thai": "running",
                  "tieu_de": "Bai test", "tao_luc": now - 3000,
                  "bat_dau_luc": now - dg.THRESHOLD_STALLED_MINUTES * 60 - 60,
                  "xong_luc": None, "ket_qua": None, "loi": None}]
        gui = []
        _run_report_progress_fake(tmp, rows, gui)
        assert not any("không phản hồi" in t for t in gui), gui


def test_stalled_ok_delete_when_task_all_done_running():
    with tempfile.TemporaryDirectory() as tmp:
        now = time.time()
        state = Path(tmp)
        (state / "reported_stalled.json").write_text(
            json.dumps({"t_1": now - 40 * 60}), encoding="utf-8")
        rows = [{"id": "t_1", "vai": "miles", "trang_thai": "done",
                  "tieu_de": "Bai test", "tao_luc": now - 3000,
                  "bat_dau_luc": now - 3000, "xong_luc": now,
                  "ket_qua": None, "loi": None}]
        gui = []
        _run_report_progress_fake(tmp, rows, gui)
        treo = json.loads((state / "reported_stalled.json").read_text(encoding="utf-8"))
        assert "t_1" not in treo


if __name__ == "__main__":
    # Truoc E-r2-2: vong `fn(); print("OK")` khong try/except, khong tong ket —
    # dung o test dau hong, va run.sh in "OK" khi qua vi khong thay dong N/M.
    from tam import chay_tat_ca
    chay_tat_ca(globals())
