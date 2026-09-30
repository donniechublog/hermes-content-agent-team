#!/usr/bin/env python3
"""LOW-424 — tin "📥 <Vai> đã nhận task" co so thu tu "#NN".

Ong Chu 30/09/2026: 10 tin Dre lien tiep khong dem nhanh duoc. Moi vai dem RIENG,
reset moi ngay VN, cung task id goi lai giu nguyen so, task chuyen vai lay so cua
vai NHAN; dong "Chờ engine đếm ảnh…" lap o moi tin da bo.

Chay:  venv/bin/python tests/test_low424_receive_number.py
"""
import json
import sys
import tempfile
import threading
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import approve_dispatch as dispatch                            # noqa: E402
import hermes_adapter                                          # noqa: E402
import receive_number                                             # noqa: E402

D1 = datetime(2026, 9, 30, 9, 0, tzinfo=receive_number.VN)
D2 = datetime(2026, 10, 1, 0, 5, tzinfo=receive_number.VN)


def test_consecutive_tasks_of_one_role_count_up():
    with tempfile.TemporaryDirectory() as tmp:
        got = [receive_number.next_number(Path(tmp), "dre", f"t_{i}", D1) for i in range(1, 4)]
    assert got == [1, 2, 3], got


def test_same_task_id_keeps_its_number():
    with tempfile.TemporaryDirectory() as tmp:
        a = receive_number.next_number(Path(tmp), "dre", "t_a", D1)
        b = receive_number.next_number(Path(tmp), "dre", "t_b", D1)
        again = receive_number.next_number(Path(tmp), "dre", "t_a", D1)
        after = receive_number.next_number(Path(tmp), "dre", "t_c", D1)
    assert (a, b, again, after) == (1, 2, 1, 3), (a, b, again, after)


def test_roles_count_independently():
    with tempfile.TemporaryDirectory() as tmp:
        assert receive_number.next_number(Path(tmp), "dre", "t_1", D1) == 1
        assert receive_number.next_number(Path(tmp), "kite", "t_2", D1) == 1
        assert receive_number.next_number(Path(tmp), "dre", "t_3", D1) == 2


def test_new_vn_day_restarts_at_one():
    with tempfile.TemporaryDirectory() as tmp:
        receive_number.next_number(Path(tmp), "dre", "t_1", D1)
        receive_number.next_number(Path(tmp), "dre", "t_2", D1)
        assert receive_number.next_number(Path(tmp), "dre", "t_3", D2) == 1
        # 23:30 UTC ngay 30 da la 06:30 ngay 01/10 gio VN -> cung ngay voi D2
        late_utc = datetime(2026, 9, 30, 23, 30, tzinfo=receive_number.timezone.utc)
        assert receive_number.next_number(Path(tmp), "dre", "t_4", late_utc) == 2


def test_corrupt_state_file_starts_over_instead_of_raising():
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "receive_number.json").write_text("{cut", encoding="utf-8")
        assert receive_number.next_number(Path(tmp), "dre", "t_1", D1) == 1


def test_concurrent_callers_never_get_the_same_number():
    with tempfile.TemporaryDirectory() as tmp:
        out = []

        def work(i):
            out.append(receive_number.next_number(Path(tmp), "dre", f"t_{i}", D1))

        ts = [threading.Thread(target=work, args=(i,)) for i in range(20)]
        for t in ts:
            t.start()
        for t in ts:
            t.join()
    assert sorted(out) == list(range(1, 21)), sorted(out)


def test_label_pads_to_two_digits_and_grows_after_99():
    assert [receive_number.label(n) for n in (1, 9, 10, 99, 100)] == ["#01", "#09", "#10", "#99", "#100"]


def _notice(tmp, vai, tu_vai, tid, status="ready", title="Tin A"):
    sent = []
    topics = Path(tmp) / "topics.json"
    topics.write_text(json.dumps({"dre": 11, "kite": 12, "miles": 13}), encoding="utf-8")
    saved = (dispatch.env_load.topics_path, hermes_adapter.status,
             hermes_adapter.count_form_run, dispatch.call, dispatch.log, dispatch.STATE_DIR)
    dispatch.env_load.topics_path = lambda: topics
    hermes_adapter.status = lambda t: status
    hermes_adapter.count_form_run = lambda tru_tid=None: 0
    dispatch.call = lambda token, method, **kw: sent.append(kw) or {"ok": True}
    dispatch.log = lambda *a, **k: None
    dispatch.STATE_DIR = Path(tmp)
    try:
        dispatch._report_receive_job("TOK", "-100", vai, tu_vai, title, tid)
    finally:
        (dispatch.env_load.topics_path, hermes_adapter.status,
         hermes_adapter.count_form_run, dispatch.call, dispatch.log, dispatch.STATE_DIR) = saved
    assert len(sent) == 1, sent
    return sent[0]["text"]


def test_notice_carries_the_number_right_after_da_nhan_task():
    with tempfile.TemporaryDirectory() as tmp:
        t1 = _notice(tmp, "dre", None, "t_1", title="Hard Vision")
        t2 = _notice(tmp, "dre", None, "t_2", title="GPT 6.1 Sol")
    assert "đã nhận task #01: <i>Hard Vision</i>" in t1, t1
    assert "đã nhận task #02: <i>GPT 6.1 Sol</i>" in t2, t2


def test_engine_wait_notice_drops_the_repeated_wait_line():
    with tempfile.TemporaryDirectory() as tmp:
        text = _notice(tmp, "dre", None, "t_1", status="blocked")
    assert "Chờ engine" not in text and "≤ 1 phút" not in text, text
    assert text.endswith("\ntask t_1"), text


def test_resent_notice_keeps_its_number():
    with tempfile.TemporaryDirectory() as tmp:
        _notice(tmp, "dre", None, "t_1")
        _notice(tmp, "dre", None, "t_2")
        again = _notice(tmp, "dre", None, "t_1")
    assert "đã nhận task #01" in again, again


def test_transferred_task_takes_the_receiving_roles_number():
    with tempfile.TemporaryDirectory() as tmp:
        _notice(tmp, "dre", None, "t_1")
        _notice(tmp, "dre", None, "t_2")
        moved = _notice(tmp, "kite", "dre", "t_3")
    assert "đã nhận task #01 chuyển từ <b>" in moved, moved


def test_counter_failure_still_sends_the_notice_without_a_number():
    with tempfile.TemporaryDirectory() as tmp:
        saved = receive_number.next_number

        def boom(*a, **k):
            raise OSError("disk full")
        receive_number.next_number = boom
        try:
            text = _notice(tmp, "dre", None, "t_1")
        finally:
            receive_number.next_number = saved
    assert "đã nhận task: <i>Tin A</i>" in text and "#" not in text, text


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
