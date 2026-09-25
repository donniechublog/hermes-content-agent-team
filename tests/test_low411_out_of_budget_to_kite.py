#!/usr/bin/env python3
"""LOW-411 — Dre het ngan sach HAI lan thi bai khong duoc chet im lang.

Do dcgr 16–25/09/2026: 10 task Dre het 90/90 luot; hermes cho chay lai mot lan,
7 task xong, 3 task hong lan hai -> `gave_up` -> nam `blocked` mai, khong ai mo
(Microsoft 22/09, Alibaba 24/09, ByteDance 25/09). Tep nay giu:

  1. `gave_up` vi het luot / het gio -> tu chuyen Kite (duong "thieu anh thi pass
     Kite"), dong task cu bang ROUTED_TO_KITE_RESULT de bang tien do im lang (LOW-410),
     bao topic vai cu + bao Kite nhan viec;
  2. KHONG chuyen khi: lan het luot dau (hermes con chay lai), worker chet (ha tang),
     vai khong phai carousel, bai da sang Kite, brand chua co Kite; chuyen hong thi
     khong thu lai moi vong poll; loi khong bao gio len toi vong poll;
  3. hai nguyen nhan lam phien het luot: cau cong ghep "35% < 35%" va prompt
     xui Dre di doc ma nguon.

Chay:  venv/bin/python tests/test_low411_out_of_budget_to_kite.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import approve_dispatch as dispatch                            # noqa: E402
import approve_post as post                                    # noqa: E402
import hermes_adapter as ha                                    # noqa: E402
import route_missing_images as rt                              # noqa: E402

ITERATIONS = "Iteration budget exhausted (90/90) — task could not complete within the allowed iterations"
IMG = {"image_role": "dre", "image_task": "t_1", "blocked_for_engine": False, "title": "Tin ByteDance"}


def _task(tid="t_1", who="dre", status="blocked"):
    return {"id": tid, "assignee": who, "status": status, "title": "Carousel: Tin ByteDance"}


def _gave_up(error=ITERATIONS, status="gave_up"):
    return {"status": status, "error": error, "summary": None, "metadata": {}, "run_id": 822}


def _route(rows, runs, img=IMG, kite=("t_7", None), no_kite=False, keep_tried=False):
    """Goi rt.route_out_of_budget voi kanban/Telegram/Kite gia. Tra (ket qua, cac lan goi)."""
    calls = {"create": [], "complete": [], "sent": [], "received": [], "log": []}
    saved = (rt.DRAFTS, rt._time_send, rt._log, dispatch.standard_assignee, dispatch.kanban_complete,
             dispatch._report_receive_job, post.create_task_kite, ha.last_run_many, ha.status)
    with tempfile.TemporaryDirectory() as tmp:
        rt.DRAFTS = Path(tmp)
        if img is not None:
            (Path(tmp) / "d1.img.json").write_text(json.dumps(img), encoding="utf-8")
        rt._time_send = lambda vai, text, kb=None: calls["sent"].append((vai, text)) or True
        rt._log = lambda msg: calls["log"].append(msg)
        dispatch.standard_assignee = lambda v: (v, "khong co profile kite" if no_kite else None)
        dispatch.kanban_complete = lambda tid, result="": calls["complete"].append((tid, result)) or (True, None)
        dispatch._report_receive_job = lambda *a, **k: calls["received"].append((a, k))
        post.create_task_kite = lambda draft_id, im, ly_do="": calls["create"].append((draft_id, ly_do)) or kite
        ha.last_run_many = lambda ids: {k: v for k, v in runs.items() if k in ids}
        ha.status = lambda tid: "blocked"
        if not keep_tried:
            rt._ROUTE_TRIED.clear()
        try:
            out = rt.route_out_of_budget("TOK", "-100", rows=rows)
        finally:
            (rt.DRAFTS, rt._time_send, rt._log, dispatch.standard_assignee, dispatch.kanban_complete,
             dispatch._report_receive_job, post.create_task_kite, ha.last_run_many, ha.status) = saved
    return out, calls


def test_dre_gave_up_out_of_iterations_is_routed_to_kite():
    """Fail tren ma cu: khong co duong nao — task nam `blocked` mai (t_bc52ed47)."""
    out, calls = _route([_task()], {"t_1": _gave_up()})
    assert out == [("t_1", "t_7")], out
    assert calls["create"] and calls["create"][0][0] == "d1", calls["create"]
    assert "het ngan sach" in calls["create"][0][1], calls["create"]
    (tid, result), = calls["complete"]
    assert tid == "t_1" and dispatch.routed_to_kite({"result": result}), \
        f"task cu phai dong bang ROUTED_TO_KITE_RESULT de bang tien do im lang: {result!r}"
    (vai, text), = calls["sent"]
    assert vai == "dre" and "Kite" in text and "t_7" in text, calls["sent"]
    assert calls["received"] and calls["received"][0][0][2] == "kite", calls["received"]


def test_gave_up_over_max_runtime_is_routed_too():
    out, calls = _route([_task()], {"t_1": _gave_up(error="elapsed 2407s > limit 2400s")})
    assert out == [("t_1", "t_7")], (out, calls)


def test_first_exhaustion_is_left_to_the_retry():
    """Lan het luot DAU: hermes con chay lai mot lan (7/10 task xong o lan do)."""
    out, calls = _route([_task(status="ready")], {"t_1": _gave_up(status="timed_out")})
    assert out == [] and calls["create"] == [], calls
    out, calls = _route([_task()], {"t_1": _gave_up(status="timed_out")})
    assert out == [] and calls["create"] == [], calls


def test_worker_crash_is_not_routed():
    """`pid ... not alive` la ha tang (t_334cf778 20/09): chay lai la xong, khong doi vai."""
    out, calls = _route([_task()], {"t_1": _gave_up(error="pid 2023868 not alive")})
    assert out == [] and calls["create"] == [], calls


def test_only_the_carousel_role_is_routed():
    """Ethan: tin benchmark/model la cua Ethan tuyet doi — Kite khong duoc nhan."""
    out, calls = _route([_task(who="ethan")], {"t_1": _gave_up()})
    assert out == [] and calls["create"] == [], calls


def test_already_transferred_is_not_routed_again():
    out, calls = _route([_task()], {"t_1": _gave_up()}, img=dict(IMG, kite_task_id="t_5"))
    assert out == [] and calls["create"] == [], calls


def test_draft_without_image_task_is_left_alone():
    out, calls = _route([_task()], {"t_1": _gave_up()}, img={"image_role": "dre", "title": "cu"})
    assert out == [] and calls["create"] == [], calls


def test_brand_without_kite_is_left_for_the_progress_board():
    out, calls = _route([_task()], {"t_1": _gave_up()}, no_kite=True)
    assert out == [] and calls["create"] == [], calls


def test_failed_transfer_is_not_retried_every_poll():
    """Tao Kite hong: bao mot lan, khong thu lai moi 50 giay."""
    out, calls = _route([_task()], {"t_1": _gave_up()}, kite=(None, "kanban 500"))
    assert out == [] and len(calls["create"]) == 1 and calls["complete"] == [], calls
    assert any("lỗi" in text for _, text in calls["sent"]), calls["sent"]
    out, calls = _route([_task()], {"t_1": _gave_up()}, kite=(None, "kanban 500"), keep_tried=True)
    assert calls["create"] == [], "thu lai moi vong poll"


def test_errors_never_reach_the_poll_loop():
    """Exception len toi vong poll thi approve_service hieu nham la mat ket noi Telegram."""
    saved = (ha.job, rt._log)
    ha.job = lambda **kw: (_ for _ in ()).throw(RuntimeError("kanban.db khoa"))
    rt._log = lambda msg: None
    try:
        assert rt.route_out_of_budget("TOK", "-100") == []
    finally:
        ha.job, rt._log = saved


def test_approve_service_routes_before_the_progress_board():
    import inspect

    import approve_service
    src = inspect.getsource(approve_service.loop)
    assert "route_out_of_budget(token, group)" in src, "vong poll khong goi duong cuu bai"
    assert src.index("route_out_of_budget(") < src.index("report_progress_kanban("), \
        "cuu bai phai chay TRUOC bang tien do, khong thi task gave_up bi bao ⛔ truoc"


def test_stack_gate_never_prints_two_equal_percentages():
    """Fail tren ma cu: 268/772 = 34.7% in ra "(35% < 35%)" — 21 dong nhu vay trong
    cac phien Dre het luot, phien ByteDance di tim chinh cau nay trong ma nguon."""
    import carousel
    msg = carousel._gate_stack_last_hidden("slide 6", {"_stack_last": (500, 772)}, 500 + 268)
    assert "268/772px" in msg, msg
    assert "(35% < 35%)" not in msg and "(34% < 35%)" in msg, msg


def test_dre_prompts_do_not_send_dre_into_the_source_code():
    """Fail tren ma cu: SKILL carousel bao "kiem bang `image_rules.tone_mismatch`" va ghi
    `schema.HEIGHT_MIN_CROP_LANDSCAPE`; SOUL chi cam lenh shell, khong cam read_file/
    search_files — phien Dre het luot doc ma p50 29 luot (phien thuong 0)."""
    skill = (ROOT / "hermes" / "skills" / "carousel" / "SKILL.md").read_text(encoding="utf-8")
    for ref in ("image_rules.", "schema.", "submit_common.", "carousel.py"):
        assert ref not in skill, f"SKILL carousel con tro vao ma nguon: {ref}"
    soul = (ROOT / "hermes" / "profiles" / "shared" / "dre.SOUL.md").read_text(encoding="utf-8")
    assert "read_file" in soul and "search_files" in soul and "mã nguồn" in soul, \
        "SOUL Dre khong cam doc ma nguon bang read_file/search_files"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
