#!/usr/bin/env python3
"""LOW-312 — luoi DOI CHIEU VET cho `approve_dispatch.report_progress_kanban`.

Ham nay (do phuc tap 64 truoc khi tach) doc kanban cua tien trinh khac, gui
Telegram va ghi ba tep state — sai chi lo khi chay that. Cach kiem o day:

  1. KICH BAN = mot chuoi "nhip" (tick) cua vong poll: moi nhip la anh chup kanban
     (rows, run dang mo, nhip tho, lan chay cuoi) + dong ho.
  2. VET = moi tin gui di (tham so day du), moi dong log, va BA tep state sau
     TUNG nhip.
  3. Vet cua ban TRUOC khi tach da ghi vao `tests/golden/report_progress_trace.json`.
     Ban sau khi tach phai cho ra DUNG vet do — 0 lech moi commit.

Co y doi hanh vi thi ghi lai vet va giai thich phan lech trong PR:
    venv/bin/python tests/test_trace_report_progress.py --write-golden

Chay:  venv/bin/python tests/test_trace_report_progress.py
"""
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import approve_base as base            # noqa: E402
import approve_dispatch as dispatch    # noqa: E402
import hermes_adapter                  # noqa: E402
from trace_harness import Harness, run_tests  # noqa: E402

GOLDEN = Path(__file__).resolve().parent / "golden" / "report_progress_trace.json"
T0 = 1_790_000_000                      # 2026-09-21 23:33:20 UTC
TOPICS = {"dre": 11, "miles": 22, "ethan": 33}


def _task(tid, who, status, title="Bài <chip> & AI", created=T0 - 3000, started=None, done=None):
    return {"id": tid, "assignee": who, "status": status, "title": title,
            "created_at": created, "started_at": started, "completed_at": done}


def _tick(rows, at=0, **kw):
    """Mot nhip poll. kw: run_start, heartbeat, last_runs, last_run, dead_pids,
    has_kanban, send (cau tra loi sendMessage), sent_log (dong telegram_sent/<vai>),
    corrupt (ten tep state bi lam hong truoc nhip), write_error."""
    return dict(rows=rows, at=at, **kw)


SCENARIOS = {
    "no_kanban_is_silent": [_tick([], has_kanban=False)],
    "unreadable_kanban_logs_and_stops": [_tick(None)],
    "start_with_queue_then_same_state_is_not_repeated": [
        _tick([_task("t1", "dre", "running", started=T0 - 60), _task("t2", "dre", "ready"),
               _task("t3", "miles", "ready"), _task("t4", "miles", "todo")]),
        _tick([_task("t1", "dre", "running", started=T0 - 60), _task("t2", "dre", "ready"),
               _task("t3", "miles", "ready"), _task("t4", "miles", "todo")], at=50),
    ],
    "done_with_product_gets_daily_ordinal": [
        _tick([_task("t0", "dre", "done", done=T0 - 7200), _task("t1", "dre", "done", done=T0 - 10),
               _task("w1", "miles", "done", done=T0 - 5)],
              sent_log={"dre": [{"ts": T0 - 100}, "khong phai json"]}),
    ],
    "done_without_product_is_flagged_not_celebrated": [
        _tick([_task("t1", "dre", "done", done=T0 - 10)],
              last_run={"t1": {"summary": "brief chỉ có 1 ảnh <lạc đề>", "metadata": {}}},
              sent_log={"dre": [{"ts": T0 - 9000}]}),
        _tick([_task("t5", "kite", "done", done=T0 - 10)], at=60,
              last_run={"t5": {"summary": None, "error": "bo cuoc",
                               "metadata": {"kind": "carousel_abort"}}},
              sent_log={"kite": [{"ts": T0 + 30}]}),
        _tick([_task("t6", "ethan", "done", done=T0 - 10)], at=120),
    ],
    "blocked_and_failed_carry_the_reason": [
        _tick([_task("t1", "dre", "blocked"), _task("w1", "miles", "failed"),
               _task("w2", "jika", "blocked")],
              last_run={"t1": {"summary": "thiếu ảnh thật: A3 <bị loại>", "metadata": {}},
                        "w1": {"summary": None, "error": "HTTP 402", "metadata": {}},
                        "w2": {"summary": "   ", "metadata": {}}}),
    ],
    "stalled_run_warns_then_reminds_then_clears": [
        _tick([_task("t1", "dre", "running", started=T0 - 60)]),
        _tick([_task("t1", "dre", "running", started=T0 - 60)], at=25 * 60,
              run_start={"t1": (T0, "r1")}, heartbeat={"t1": (T0 + 24 * 60 + 30, 4242)}),
        _tick([_task("t1", "dre", "running", started=T0 - 60)], at=35 * 60,
              run_start={"t1": (T0, "r1")}, heartbeat={"t1": (T0 + 25 * 60, 4242)}),
        _tick([_task("t1", "dre", "running", started=T0 - 60)], at=56 * 60,
              run_start={"t1": (T0, "r1")}, heartbeat={"t1": (T0 + 40 * 60, 4242)}),
        _tick([_task("t1", "dre", "running", started=T0 - 60)], at=90 * 60,
              run_start={"t1": (T0, "r1")}, heartbeat={"t1": (T0 + 40 * 60, 4242)},
              dead_pids=[4242]),
        _tick([_task("t1", "dre", "done", done=T0 + 91 * 60)], at=91 * 60,
              sent_log={"dre": [{"ts": T0 + 90 * 60}]}),
    ],
    "stalled_without_heartbeat_data_falls_back_to_started_at": [
        _tick([_task("t1", "miles", "running", started=T0 - 40 * 60)]),
    ],
    "low23_restarted_run_is_timed_from_the_open_run_not_first_start": [
        _tick([_task("t1", "dre", "running", started=T0 - 3 * 3600)],
              run_start={"t1": (T0 - 120, "r2")}),
    ],
    "killed_by_max_runtime_is_reported_once_per_run": [
        _tick([_task("t1", "dre", "ready")],
              last_runs={"t1": {"status": "timed_out", "run_id": "r1",
                                "metadata": {"elapsed_seconds": 1500, "limit_seconds": 1500}}}),
        _tick([_task("t1", "dre", "running", started=T0 + 40)], at=50,
              last_runs={"t1": {"status": "timed_out", "run_id": "r1", "metadata": {}}}),
        _tick([_task("t1", "dre", "running", started=T0 + 40)], at=1600,
              last_runs={"t1": {"status": "timed_out", "run_id": "r2", "metadata": None}}),
    ],
    "killed_then_restarted_in_one_tick_reports_kill_before_start": [
        _tick([_task("t1", "dre", "running", started=T0 - 30)],
              last_runs={"t1": {"status": "timed_out", "run_id": "r1",
                                "metadata": {"elapsed_seconds": 900}}}),
    ],
    "blackboard_root_and_unknown_status_are_marked_silently": [
        _tick([_task("root", "ban_bien_tap", "running", started=T0 - 9999),
               _task("root2", "ban_bien_tap", "done"), _task("t9", "dre", "archived")]),
    ],
    "telegram_refusal_is_logged_and_state_still_advances": [
        _tick([_task("t1", "dre", "running", started=T0 - 5)],
              send=[{"ok": False, "description": "Bad Request: message thread not found"}]),
        _tick([_task("t1", "dre", "running", started=T0 - 5)], at=50),
    ],
    "role_without_topic_posts_to_group_root": [
        _tick([_task("t1", "ada", "running", started=T0 - 5)]),
    ],
    "corrupt_state_files_are_treated_as_empty": [
        _tick([_task("t1", "dre", "running", started=T0 - 5)], corrupt=True),
    ],
    "finished_tasks_older_than_the_window_are_pruned_on_next_write": [
        _tick([_task("old", "dre", "running", started=T0 - 5)]),
        _tick([_task("new", "miles", "running", started=T0 + 5)], at=60),
    ],
    "state_write_failure_is_logged_not_raised": [
        _tick([_task("t1", "dre", "running", started=T0 - 40 * 60)], write_error=True),
    ],
}


def _run_scenario(ticks):
    """Chay chuoi nhip, tra ve vet: [{tg, logs, state}] cho tung nhip."""
    old_tz = os.environ.get("TZ")
    os.environ["TZ"] = "UTC"                     # long_run_message in gio dia phuong
    time.tzset()
    out = []
    with Harness(dispatch, base) as h:
        h.capture_logs()
        h.topics(TOPICS)
        h.fake_time(dispatch)
        real_write = dispatch._write_json
        for tick in ticks:
            h.clock.now = float(T0 + tick["at"])
            rows = tick["rows"]
            h.patch(hermes_adapter, "has_kanban", lambda t=tick: t.get("has_kanban", True))
            h.patch(hermes_adapter, "job", lambda tu_ts=None, r=rows, **kw: r)
            h.patch(hermes_adapter, "run_start", lambda t=tick: t.get("run_start"))
            h.patch(hermes_adapter, "heartbeat", lambda ids, t=tick: t.get("heartbeat"))
            h.patch(hermes_adapter, "last_run_many", lambda ids, t=tick: t.get("last_runs"))
            h.patch(hermes_adapter, "last_run", lambda tid, t=tick: (t.get("last_run") or {}).get(tid))
            h.patch(hermes_adapter, "pid_alive",
                    lambda pid, t=tick: None if pid is None else pid not in t.get("dead_pids", []))
            for who, lines in (tick.get("sent_log") or {}).items():
                p = h.state / "telegram_sent" / f"{who}.jsonl"
                p.parent.mkdir(exist_ok=True)
                p.write_text("\n".join(x if isinstance(x, str) else json.dumps(x) for x in lines),
                             encoding="utf-8")
            if tick.get("corrupt"):
                for f in (dispatch.ALREADY_REPORT_PROGRESS, dispatch.STORY_RESULT,
                          dispatch.ALREADY_REPORT_STALLED):
                    f.write_text("{cut", encoding="utf-8")
            if tick.get("send"):
                h.tg.script("sendMessage", *tick["send"])

            def _boom(*a, **kw):
                raise OSError("het cho dia")
            h.patch(dispatch, "_write_json", _boom if tick.get("write_error") else real_write)
            n_tg, n_log = len(h.trace.of("tg")), len(h.trace.of("log"))
            dispatch.report_progress_kanban(h.token, h.group)
            state = {k: v for k, v in h.snapshot(h.state).items() if not k.startswith("telegram_sent")}
            out.append({
                "tg": [[name, {k: v for k, v in d.items() if k != "token"}]
                       for name, d in h.trace.of("tg")[n_tg:]],
                "logs": [[name, d["text"]] for name, d in h.trace.of("log")[n_log:]],
                "state": state,
            })
    if old_tz is None:
        os.environ.pop("TZ", None)
    else:
        os.environ["TZ"] = old_tz
    time.tzset()
    return json.loads(json.dumps(out, ensure_ascii=False))


def _make_test(name):
    def _test():
        want = json.loads(GOLDEN.read_text(encoding="utf-8"))[name]
        got = _run_scenario(SCENARIOS[name])
        assert len(got) == len(want), (len(got), len(want))
        for i, (g, w) in enumerate(zip(got, want)):
            for part in ("tg", "logs", "state"):
                assert g[part] == w[part], (f"{name} nhip {i} lech o `{part}`:\n  muon: "
                                            f"{json.dumps(w[part], ensure_ascii=False)}\n  ra:   "
                                            f"{json.dumps(g[part], ensure_ascii=False)}")
    _test.__name__ = "test_" + name
    return _test


for _name in SCENARIOS:
    globals()["test_" + _name] = _make_test(_name)


def test_golden_has_no_stale_or_missing_scenarios():
    assert sorted(json.loads(GOLDEN.read_text(encoding="utf-8"))) == sorted(SCENARIOS)


def test_scenarios_actually_exercise_every_kind_of_message():
    """Vet vang ma rong thi 0-lech khong chung minh gi: moi loai tin phai co mat."""
    texts = " ".join(d["text"] for ticks in json.loads(GOLDEN.read_text(encoding="utf-8")).values()
                     for t in ticks for _, d in t["tg"])
    for mark in ("▶️", "✅", "task #02", "không có sản phẩm", "dừng (blocked)", "dừng (failed)",
                 "vẫn đang làm", "không phản hồi", "đã chết", "bị hermes dừng", "còn 2 việc"):
        assert mark in texts, mark


if __name__ == "__main__":
    if "--write-golden" in sys.argv:
        GOLDEN.write_text(json.dumps({n: _run_scenario(t) for n, t in SCENARIOS.items()},
                                     ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"da ghi {GOLDEN}")
        sys.exit(0)
    sys.exit(run_tests(globals()))
