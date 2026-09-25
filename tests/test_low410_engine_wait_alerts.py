#!/usr/bin/env python3
"""LOW-410 — hai buoc BINH THUONG cua luong chot vai LOW-382 khong duoc thanh tin ⛔.

Do 23–25/09/2026: 65/71 tin ⛔ tren topic vai anh la gia — moi lan `create_pair`
chan task cho engine dem anh ra "⛔ dừng (blocked)", moi task he thong dong khi bai
sang Kite ra "⛔ báo xong nhưng không có sản phẩm". Tep nay giu:

  1. tin "📥 đã nhận task" khong hua "≤ 1 phút" cho task dang cho engine;
  2. ben VIET (create_pair, route_missing_images) va ben DOC (bang tien do) dung
     CHUNG hai hang ENGINE_WAIT_REASON / ROUTED_TO_KITE_RESULT — lech chu la ⛔ gia
     quay lai ma khong test nao do;
  3. task he thong dong khong dem vao "task #NN" cua vai.

Phan bang tien do (im lang, bao khi chan qua nguong, chan that van bao) khoa bang
vet vang: tests/test_trace_report_progress.py, kich ban `low410_*`.

Chay:  venv/bin/python tests/test_low410_engine_wait_alerts.py
"""
import inspect
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import approve_dispatch as dispatch                            # noqa: E402
import hermes_adapter                                          # noqa: E402
import route_missing_images as rt                              # noqa: E402


def _receive_job_text(status):
    """Tin "📥 đã nhận task" cho mot task Dre moi tao dang o trang thai `status`."""
    sent = []
    with tempfile.TemporaryDirectory() as tmp:
        topics = Path(tmp) / "topics.json"
        topics.write_text(json.dumps({"dre": 11}), encoding="utf-8")
        saved = (dispatch.env_load.topics_path, hermes_adapter.status,
                 hermes_adapter.count_form_run, dispatch.call, dispatch.log)
        dispatch.env_load.topics_path = lambda: topics
        hermes_adapter.status = lambda tid: status
        hermes_adapter.count_form_run = lambda tru_tid=None: 0
        dispatch.call = lambda token, method, **kw: sent.append(kw) or {"ok": True}
        dispatch.log = lambda *a, **k: None
        try:
            dispatch._report_receive_job("TOK", "-100", "dre", None, "Tin A", "t_1")
        finally:
            (dispatch.env_load.topics_path, hermes_adapter.status,
             hermes_adapter.count_form_run, dispatch.call, dispatch.log) = saved
    assert len(sent) == 1, sent
    return sent[0]["text"]


def test_receive_job_while_waiting_for_engine_does_not_promise_one_minute():
    """Fail tren ma cu: task dang bi chan cho engine van nhan "Bắt đầu ngay khi
    dispatcher nhận (≤ 1 phút)" — bai OpenEvidence 25/09 nhan cau do luc 11:09,
    11:10 topic hien "dừng (blocked)"."""
    text = _receive_job_text("blocked")
    assert "≤ 1 phút" not in text, text
    assert "Chờ engine đếm ảnh" in text, text


def test_receive_job_for_ready_task_keeps_start_promise():
    text = _receive_job_text("ready")
    assert "Bắt đầu ngay khi dispatcher nhận (≤ 1 phút)" in text, text


def test_create_pair_blocks_with_the_shared_engine_wait_reason():
    """Ly do chan phai la hang chung: bang tien do nhan lan chan binh thuong nay
    bang chinh chu do. Viet tay lai o day thi hai ben lech ma khong ai hay."""
    import approve_pick
    src = inspect.getsource(approve_pick.create_pair)
    assert "ENGINE_WAIT_REASON" in src, "create_pair khong dung hang ENGINE_WAIT_REASON"
    assert '"cho engine dem anh' not in src, "ly do chan viet tay, se lech voi ben doc"


def test_kite_transfer_close_result_is_recognised_by_progress_board():
    """Fail tren ma cu: ROUTED_TO_KITE_RESULT/routed_to_kite chua co — bang tien do
    khong phan biet task he thong dong voi task vai "dong sai cach"."""
    got = []
    saved = (hermes_adapter.status, dispatch.kanban_complete, rt.DRAFTS)
    with tempfile.TemporaryDirectory() as tmp:
        rt.DRAFTS = Path(tmp)
        (Path(tmp) / "d1.img.json").write_text(json.dumps({"image_task": "t_1"}), encoding="utf-8")
        hermes_adapter.status = lambda tid: "blocked"
        dispatch.kanban_complete = lambda tid, result="": got.append((tid, result)) or (True, None)
        try:
            rt._close_image_task("d1", "t_1", "t_9")
        finally:
            hermes_adapter.status, dispatch.kanban_complete, rt.DRAFTS = saved
    assert got and got[0][0] == "t_1", got
    assert dispatch.routed_to_kite({"result": got[0][1]}), got


def test_daily_ordinal_skips_tasks_closed_on_kite_transfer():
    """Fail tren ma cu: task Dre he thong dong khi sang Kite duoc dem, bai Dre lam
    that dau tien trong ngay thanh "task #02"."""
    t0 = 1_790_000_000
    rows = [{"id": "t0", "assignee": "dre", "status": "done", "completed_at": t0 - 100,
             "result": dispatch.ROUTED_TO_KITE_RESULT + " (task t9) — thieu anh that."},
            {"id": "t1", "assignee": "dre", "status": "done", "completed_at": t0 - 10}]
    assert dispatch._daily_task_ordinal(rows, "dre", "t1", t0 - 10) == 1


def test_waiting_for_engine_only_matches_image_roles_blocked_by_the_engine():
    """Chi lan chan cua create_pair moi im lang: vai tu chan (thieu anh that),
    task cua vai viet, hay task da mo chan deu khong phai."""
    class _Run:
        def __init__(self, summary):
            self.summary = summary

        def last_run(self, tid):
            return {"summary": self.summary}

    reason = dispatch.ENGINE_WAIT_REASON + " (draft d1)"
    blocked_dre = {"id": "t1", "assignee": "dre", "status": "blocked"}
    assert dispatch._waiting_for_engine(_Run(reason), blocked_dre)
    assert not dispatch._waiting_for_engine(_Run(reason), dict(blocked_dre, status="ready"))
    assert not dispatch._waiting_for_engine(_Run(reason), dict(blocked_dre, assignee="miles"))
    assert not dispatch._waiting_for_engine(_Run("thiếu ảnh thật: A3 bị loại"), blocked_dre)
    assert not dispatch._waiting_for_engine(_Run(None), blocked_dre)


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
