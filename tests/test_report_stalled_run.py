#!/usr/bin/env python3
"""LOW-23 (12/09/2026): canh bao "khong phan hoi" phai do LAN CHAY HIEN TAI va
noi dung trang thai; task bi hermes giet (timed_out) phai duoc bao.

Ca that t_24b214a6: hai run 25.1 phut deu timed_out, heartbeat moi 60s suot,
Telegram noi "khong phan hoi hon 20 phut" roi im lang khi bi giet. Dung harness
cua test_report_stalled (kanban/telegram gia), them stub cho ba ham moi cua
hermes_adapter. Fail tren code cu (khong co run_start/long_run_message), pass
tren code moi.

Chay:  venv/bin/python tests/test_report_stalled_run.py
"""
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
import approve_dispatch as dg                                  # noqa: E402
from test_report_stalled import _run_report_progress_fake               # noqa: E402


def _with_stub(moc, nhip, lan_cuoi, pid_song, rows, tmp):
    ha = dg.hermes_adapter
    cu = (ha.run_start, ha.heartbeat, ha.last_run_many, ha.pid_alive)
    ha.run_start = lambda db=None: moc
    ha.heartbeat = lambda tids, db=None: nhip
    ha.last_run_many = lambda tids: lan_cuoi
    ha.pid_alive = lambda pid: pid_song
    gui = []
    try:
        _run_report_progress_fake(tmp, rows, gui)
    finally:
        ha.run_start, ha.heartbeat, ha.last_run_many, ha.pid_alive = cu
    return gui


def _row(now, bat_dau_luc, st="running"):
    return [{"id": "t_1", "vai": "miles", "trang_thai": st, "tieu_de": "Bai test",
             "tao_luc": now - 5000, "bat_dau_luc": bat_dau_luc,
             "xong_luc": None, "ket_qua": None, "loi": None}]


def test_retry_new_30s_no_got_report_enough_started_at_40_minutes():
    now = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        gui = _with_stub({"t_1": (now - 30, 188)}, {"t_1": (now - 10, 4242)}, {}, True,
                        _row(now, now - 40 * 60), tmp)
    assert not any("phút" in t and "⚠️" in t for t in gui), gui
    assert any(t.startswith("▶️") for t in gui), gui


def test_form_make_has_heartbeat_then_say_form_make_no_say_no_part_ask():
    now = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        gui = _with_stub({"t_1": (now - 22 * 60, 188)}, {"t_1": (now - 40, 4242)}, {}, True,
                        _row(now, now - 22 * 60), tmp)
    treo = [t for t in gui if "⏳" in t]
    assert treo and "vẫn đang làm" in treo[0], gui
    assert not any("không phản hồi" in t for t in gui), gui


def test_silent_real_then_say_no_part_ask_with_timestamp_last_beat():
    now = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        gui = _with_stub({"t_1": (now - 22 * 60, 188)}, {"t_1": (now - 9 * 60, 4242)}, {}, True,
                        _row(now, now - 22 * 60), tmp)
    t = [x for x in gui if "không phản hồi" in x]
    assert t and "nhịp thở cuối" in t[0] and "9 phút" in t[0], gui


def test_worker_crash_then_say_already_crash():
    now = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        gui = _with_stub({"t_1": (now - 22 * 60, 188)}, {"t_1": (now - 60, 4242)}, {}, False,
                        _row(now, now - 22 * 60), tmp)
    assert any("đã chết" in t and "4242" in t for t in gui), gui


def test_timed_out_ok_report_one_attempt_new_run():
    now = time.time()
    lc = {"t_1": {"trang_thai": "timed_out", "id_lan_chay": 184, "tom_tat": "", "loi": "x",
                  "metadata": {"elapsed_seconds": 1502, "limit_seconds": 1500}}}
    with tempfile.TemporaryDirectory() as tmp:
        gui = _with_stub({}, {}, lc, None, _row(now, now - 1600, st="ready"), tmp)
        t = [x for x in gui if "⏱" in x]
        assert t and "25 phút" in t[0] and "trần 25 phút" in t[0], gui
        da = json.loads((Path(tmp) / "reported_progress.json").read_text(encoding="utf-8"))
        assert da.get("t_1:timed_out:184") is True, da
        # vong sau, cung run -> KHONG bao lai
        gui2 = _with_stub({}, {}, lc, None, _row(now, now - 1600, st="ready"), tmp)
        assert not any("⏱" in x for x in gui2), gui2
        # run moi timed_out (188) -> bao lai
        lc["t_1"]["id_lan_chay"] = 188
        gui3 = _with_stub({}, {}, lc, None, _row(now, now - 1600, st="ready"), tmp)
        assert any("⏱" in x for x in gui3), gui3


if __name__ == "__main__":
    ok = 0
    ten = [k for k in list(globals()) if k.startswith("test_")]
    for k in ten:
        try:
            globals()[k]()
            ok += 1
        except AssertionError as e:
            print(f"    FAIL {k}: {e}")
    print(f"{Path(__file__).name:<34} {ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
