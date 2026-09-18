#!/usr/bin/env python3
"""LOW-250 (17/09/2026): tin "xong" gửi vào topic Telegram của writer/designer
phải kèm số thứ tự task trong ngày ("xong task #05") để biết mỗi vai hoàn thành
bao nhiêu task/ngày. Ông Chủ chốt phạm vi: CHỈ writer (Miles, Jika) + designer
dùng ảnh (Dre, Kite, Ethan) — researcher/analyst (Finn, Vera, Qinn, Ada...)
chưa cần, để sau.

Test theo đúng kiểu tests/test_report_stalled.py: monkeypatch trực tiếp thuộc
tính module, tự lưu/phục hồi trong finally, không đụng kanban.db/Telegram thật.

Chay:  venv/bin/python tests/test_daily_task_ordinal.py
"""
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import approve_dispatch as dg                                  # noqa: E402


# --------------------------------------------------------- _daily_task_ordinal
def test_daily_ordinal_count_only_same_role_same_day():
    now = time.time()
    rows = [
        {"id": "t_1", "assignee": "miles", "status": "done", "completed_at": now - 3000},
        {"id": "t_2", "assignee": "miles", "status": "done", "completed_at": now - 2000},
        {"id": "t_3", "assignee": "jika", "status": "done", "completed_at": now - 1000},
    ]
    assert dg._daily_task_ordinal(rows, "miles", "t_1", now - 3000) == 1
    assert dg._daily_task_ordinal(rows, "miles", "t_2", now - 2000) == 2
    # jika la vai khac -> mach dem rieng, khong cong don voi miles
    assert dg._daily_task_ordinal(rows, "jika", "t_3", now - 1000) == 1


def test_daily_ordinal_not_count_yesterday():
    now = time.time()
    hom_qua = now - 26 * 3600           # chac chan sang hom truoc theo gio VN
    rows = [
        {"id": "t_0", "assignee": "miles", "status": "done", "completed_at": hom_qua},
        {"id": "t_1", "assignee": "miles", "status": "done", "completed_at": now},
    ]
    assert dg._daily_task_ordinal(rows, "miles", "t_1", now) == 1, \
        "task hom qua khong duoc tinh vao so dem hom nay"


def test_daily_ordinal_not_count_other_status():
    now = time.time()
    rows = [
        {"id": "t_1", "assignee": "miles", "status": "running", "completed_at": None},
        {"id": "t_2", "assignee": "miles", "status": "done", "completed_at": now},
    ]
    assert dg._daily_task_ordinal(rows, "miles", "t_2", now) == 1


def test_daily_ordinal_none_when_no_completed_at():
    assert dg._daily_task_ordinal([], "miles", "t_1", None) is None


# --------------------------------------------------- pham vi vai (DAILY_ORDINAL_ROLES)
def test_daily_ordinal_roles_is_writer_and_image_only():
    assert dg.DAILY_ORDINAL_ROLES == {"miles", "jika", "ethan", "dre", "kite"}, \
        dg.DAILY_ORDINAL_ROLES
    for khong_thuoc in ("finn", "nova", "vera", "qinn", "ada", "cape", "gin", "itachi", "bob"):
        assert khong_thuoc not in dg.DAILY_ORDINAL_ROLES, khong_thuoc


# --------------------------------------------------------- tich hop qua report_progress_kanban
def _run_report_progress_fake(tmp, rows, gui_ghi_lai, topics=None):
    state = Path(tmp)
    cu = (dg.ALREADY_REPORT_PROGRESS, dg.STORY_RESULT, dg.ALREADY_REPORT_STALLED,
          dg.hermes_adapter.has_kanban, dg.hermes_adapter.job, dg.call, dg.env_load.topics_path)
    dg.ALREADY_REPORT_PROGRESS = state / "reported_progress.json"
    dg.STORY_RESULT = state / "task_result_messages.json"
    dg.ALREADY_REPORT_STALLED = state / "reported_stalled.json"
    dg.hermes_adapter.has_kanban = lambda: True
    dg.hermes_adapter.job = lambda tu_ts=None: list(rows)
    tp = state / "topics.json"
    tp.write_text(json.dumps(topics or {"miles": 52, "dre": 60, "finn": 70}), encoding="utf-8")
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


def test_writer_done_message_has_ordinal():
    with tempfile.TemporaryDirectory() as tmp:
        now = time.time()
        rows = [{"id": "t_1", "assignee": "miles", "status": "done",
                  "title": "Bai test", "created_at": now - 300,
                  "started_at": now - 300, "completed_at": now,
                  "result": None, "error": None}]
        gui = []
        _run_report_progress_fake(tmp, rows, gui)
    assert any("xong task #01" in t for t in gui), gui


def test_designer_done_message_has_ordinal_zero_padded():
    """5 task carousel da xong hom nay cua Dre — task dang xet la task thu 5.
    `_done_code_no_hand` doc telegram_sent/<vai>.jsonl tren dia that (khong qua
    tham so cua report_progress_kanban) nen fake rieng no ve None, dung nhu
    "co album that" — gate do khong phai thu dang test o day."""
    cu = dg._done_code_no_hand
    dg._done_code_no_hand = lambda tid, ai, created_at: None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            now = time.time()
            rows = [{"id": f"t_{i}", "assignee": "dre", "status": "done",
                      "title": f"Bai {i}", "created_at": now - (6 - i) * 100,
                      "started_at": now - (6 - i) * 100, "completed_at": now - (6 - i) * 100,
                      "result": None, "error": None} for i in range(1, 6)]
            gui = []
            _run_report_progress_fake(tmp, rows, gui)
    finally:
        dg._done_code_no_hand = cu
    assert any("xong task #05" in t for t in gui), gui


def test_researcher_done_message_has_no_ordinal():
    """Finn (researcher) chua nam trong pham vi LOW-250 — tin 'xong' giu nguyen,
    khong duoc them '#NN'."""
    with tempfile.TemporaryDirectory() as tmp:
        now = time.time()
        rows = [{"id": "t_1", "assignee": "finn", "status": "done",
                  "title": "Bai test", "created_at": now - 300,
                  "started_at": now - 300, "completed_at": now,
                  "result": None, "error": None}]
        gui = []
        _run_report_progress_fake(tmp, rows, gui)
    assert any(t.startswith("✅") and "xong:" in t and "xong task #" not in t for t in gui), gui


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
