#!/usr/bin/env python3
"""dispatch_shadow.py (LOW-349): chạy bóng tự giao việc.

Giữ các luật làm số đo độ trùng là số thật:
  1. Gợi ý của một tin không phụ thuộc quyết định của chính tin đó, và chỉ học
     từ lượt quét TRƯỚC nó (cùng lượt quét cũng không tính).
  2. Quét lại trong ngày (`_tHHMMSS`) là CÙNG một tin; ngày không chọn tin nào
     không tính là "không chọn"; tin mới hơn DECISION_HOURS là "chờ".
  3. Gợi ý đóng băng trong log, chạy lại không chấm lại; kết quả đọc sống từ
     manifest (Ông Chủ chọn muộn vẫn được tính).
  4. Designer: bảng khởi đầu -> lịch sử khi đủ mẫu; bỏ designer không có profile.
  5. Ngưỡng "đủ điều kiện tự giao": ≥ 10 mẫu, ≥ 90%, trong 20 lần gần nhất.

Chạy:  venv/bin/python tests/test_dispatch_shadow.py
"""
import collections
import json
import os
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import dispatch_shadow as ds                                  # noqa: E402
import role                                                   # noqa: E402
import state_paths                                            # noqa: E402

T0 = datetime(2026, 9, 1, 22, 0, tzinfo=timezone.utc)         # 05:00 VN, giờ quét của Finn
NOW = T0 + timedelta(days=40)
ALL = {"ethan", "dre", "kite"}


def _item(slug, category="MODEL", score=95, designer=None, index=1):
    it = {"index": index, "title": f"Tin {slug}", "link": f"https://x.test/{slug}",
          "category": category, "score": score}
    if designer:
        it["picked"] = True
        it["assignments"] = [{"image_role": designer, "brand": "blog"}]
    return it


def _scan(day, items, scan_role="finn", hour=0):
    return {"manifest": f"{scan_role}_candidates_d{day}h{hour}.json", "scan_role": scan_role,
            "scanned_at": T0 + timedelta(days=day, hours=hour), "items": items}


def _history(days=12):
    """Mỗi ngày: một tin MODEL 95 được giao Dre, một tin TOOL 60 bị bỏ."""
    return [_scan(d, [_item(f"m{d}", "MODEL", 95, designer="dre"),
                      _item(f"t{d}", "TOOL", 60, index=2)]) for d in range(days)]


def _by_key(stories):
    return {s["key"]: s for s in stories}


def _write(state, scan):
    (state / scan["manifest"]).write_text(json.dumps(
        {"scanned_at": scan["scanned_at"].isoformat(), "scan_role": scan["scan_role"],
         "items": scan["items"]}, ensure_ascii=False), encoding="utf-8")


# ------------------------------------------------------------ 1. không rò rỉ
def test_pick_follows_category_and_tier_rate():
    stories = ds.gather_stories(_history() + [_scan(20, [_item("new-m", "MODEL", 92),
                                                          _item("new-t", "TOOL", 65, index=2)])])
    table = ds.learn(stories, T0 + timedelta(days=20), ds.reviewed_days(stories), NOW)
    assert table["designers"]["MODEL"] == {"dre": 12}, table["designers"]
    k = _by_key(stories)
    m = ds.suggest(k[ds.story_key(_item("new-m"))], table, ALL)
    assert (m["suggested_pick"], m["pick_basis"], m["pick_samples"]) == (True, "category_tier", 12), m
    assert (m["suggested_designer"], m["designer_basis"]) == ("dre", "history"), m
    t = ds.suggest(k[ds.story_key(_item("new-t"))], table, ALL)
    assert (t["suggested_pick"], t["pick_basis"], t["pick_rate"]) == (False, "category_tier", 0.0), t


def test_pick_falls_back_to_tier_then_to_none():
    stories = ds.gather_stories(_history())
    table = ds.learn(stories, T0 + timedelta(days=20), ds.reviewed_days(stories), NOW)
    sec = ds.suggest({"category": "SECURITY", "score": 91}, table, ALL)
    assert (sec["suggested_pick"], sec["pick_basis"]) == (True, "tier"), sec
    mid = ds.suggest({"category": "MODEL", "score": 85}, table, ALL)
    assert (mid["suggested_pick"], mid["pick_basis"], mid["pick_samples"]) == (None, "", 0), mid


def test_only_earlier_scans_are_learned():
    stories = ds.gather_stories(_history())
    reviewed = ds.reviewed_days(stories)
    early = ds.suggest({"category": "MODEL", "score": 95},
                       ds.learn(stories, T0 + timedelta(days=3), reviewed, NOW), ALL)
    assert early["suggested_pick"] is None and early["pick_samples"] == 3, early
    # tin nằm TRONG lượt quét ngày 10: chỉ học ngày 0..9, không học chính lượt của nó
    same = ds.suggest({"category": "MODEL", "score": 95},
                      ds.learn(stories, T0 + timedelta(days=10), reviewed, NOW), ALL)
    assert same["suggested_pick"] is True and same["pick_samples"] == 10, same


def test_own_decision_does_not_change_suggestion():
    rows = []
    for designer in (None, "kite"):
        stories = ds.gather_stories(_history() + [_scan(20, [_item("x", "MODEL", 92, designer=designer)])])
        new = ds.score_new(stories, {}, ds.reviewed_days(stories), ALL, NOW)
        rows.append([r for r in new if r["key"] == ds.story_key(_item("x"))])
    assert rows[0] == rows[1] and rows[0], rows


# ------------------------------------------------------------ 2. dữ liệu thô
def test_rescans_count_as_one_story():
    scans = [_scan(0, [_item("a"), _item("b", index=2)]),
             _scan(0, [_item("a", designer="ethan"), _item("b", index=2)], hour=2)]
    stories = ds.gather_stories(scans)
    assert len(stories) == 2, stories
    a = _by_key(stories)[ds.story_key(_item("a"))]
    assert a["picked"] and a["designers"] == {"ethan"}, a
    assert a["manifest"] == scans[0]["manifest"] and a["scanned_at"] == scans[0]["scanned_at"], a


def test_day_without_any_pick_is_not_counted():
    stories = ds.gather_stories([_scan(d, [_item(f"n{d}")]) for d in range(6)])
    reviewed = ds.reviewed_days(stories)
    assert {ds.outcome(s, reviewed, NOW) for s in stories} == {"not_reviewed"}
    assert not ds.learn(stories, NOW, reviewed, NOW)["by_tier"]
    fresh = dict(stories[0], scanned_at=NOW - timedelta(hours=2))
    assert ds.outcome(fresh, reviewed, NOW) == "pending"
    reviewed_day = {(fresh["scan_role"], ds._local_date(stories[0]["scanned_at"]))}
    assert ds.outcome(stories[0], reviewed_day, NOW) == "not_picked"


# ------------------------------------------------------------ 3. log đóng băng
def test_run_freezes_suggestions_and_reads_live_outcome():
    with tempfile.TemporaryDirectory() as t:
        state = Path(t)
        for s in _history():
            _write(state, s)
        target = _scan(20, [_item("late", "MODEL", 92)])
        _write(state, target)
        n, before = ds.run(state, NOW, ALL, 60)
        assert n == 25, n
        path = state / state_paths.DISPATCH_SHADOW_FILE
        log = path.read_text(encoding="utf-8").splitlines()
        row = ds.load_log(path)[ds.story_key(_item("late"))]
        assert row["suggested_pick"] is True and row["suggested_designer"] == "dre", row
        assert row["version"] == ds.VERSION and row["manifest"] == target["manifest"], row
        # Ông Chủ chọn muộn: log giữ nguyên, báo cáo thấy kết quả mới
        target["items"][0].update(picked=True, assignments=[{"image_role": "carousel"}])
        _write(state, target)
        n2, after = ds.run(state, NOW, ALL, 60)
        assert n2 == 0, n2
        assert path.read_text(encoding="utf-8").splitlines() == log
        assert after["total"]["picked"] == before["total"]["picked"] + 1, (before["total"], after["total"])
        assert after["total"]["hit"] == before["total"]["hit"] + 1, (before["total"], after["total"])
        assert after["total"]["designer_ok"] == before["total"]["designer_ok"] + 1   # "carousel" = Dre


# ------------------------------------------------------------ 4. designer
def test_designer_prior_then_history_and_availability():
    empty = {"designers": {}}
    assert ds.suggest_designer("MODEL", 85, empty, ALL) == ("ethan", "prior")
    assert ds.suggest_designer("MODEL", 95, empty, ALL) == ("dre", "prior")
    assert ds.suggest_designer("ARXIV", 70, empty, ALL) == ("kite", "prior")
    assert ds.suggest_designer("", None, empty, ALL) == (role.DEFAULT_IMAGE, "prior")
    assert ds.suggest_designer("ARXIV", 70, empty, {"ethan", "dre"}) == ("ethan", "prior")
    two = {"designers": {"MODEL": collections.Counter({"kite": 2})}}
    assert ds.suggest_designer("MODEL", 85, two, ALL) == ("ethan", "prior")
    three = {"designers": {"MODEL": collections.Counter({"kite": 3, "ethan": 1})}}
    assert ds.suggest_designer("MODEL", 85, three, ALL) == ("kite", "history")
    assert ds.suggest_designer("MODEL", 85, three, {"ethan", "dre"}) == ("ethan", "prior")
    tie = {"designers": {"MODEL": collections.Counter({"kite": 2, "ethan": 2})}}
    assert ds.suggest_designer("MODEL", 85, tie, ALL) == ("ethan", "history")


def test_designer_learns_per_scan_role_first():
    """Cùng MODEL: tin Nova giao Ethan, tin Finn giao Dre — gợi ý phải tách theo vai quét."""
    scans = []
    for d in range(3):
        scans.append(_scan(d, [_item(f"f{d}", "MODEL", 70, designer="dre")]))
        scans.append(_scan(d, [_item(f"n{d}", "MODEL", 70, designer="ethan")], scan_role="nova", hour=1))
    stories = ds.gather_stories(scans)
    table = ds.learn(stories, NOW, ds.reviewed_days(stories), NOW)
    assert ds.suggest_designer("MODEL", 70, table, ALL, "finn") == ("dre", "history")
    assert ds.suggest_designer("MODEL", 70, table, ALL, "nova") == ("ethan", "history")
    # vai quét chưa đủ mẫu -> theo cả loại tin (3 dre, 3 ethan: hoà -> bảng khởi đầu)
    assert ds.suggest_designer("MODEL", 70, table, ALL, "qinn") == ("ethan", "history")


def test_legacy_scan_role_is_canonical():
    with tempfile.TemporaryDirectory() as t:
        state = Path(t)
        _write(state, dict(_scan(0, [_item("a")]), scan_role="scout"))
        _write(state, dict(_scan(1, [_item("b")], scan_role="market")))
        assert [s["scan_role"] for s in ds.load_scans(state)] == ["finn", "vera"]


def test_designers_available_reads_profiles():
    old = os.environ.get("HERMES_HOME")
    with tempfile.TemporaryDirectory() as t:
        os.environ["HERMES_HOME"] = t
        try:
            assert ds.designers_available() == set(role.NAME_ROLE_IMAGE)
            (Path(t) / "profiles" / "ethan").mkdir(parents=True)
            (Path(t) / "profiles" / "dre").mkdir()
            assert ds.designers_available() == {"ethan", "dre"}
        finally:
            if old is None:
                os.environ.pop("HERMES_HOME", None)
            else:
                os.environ["HERMES_HOME"] = old


# ------------------------------------------------------------ 5. đủ điều kiện
def _row(picked=True, suggested=True, designer="ethan", actual="ethan"):
    return {"outcome": "picked" if picked else "not_picked", "suggested_pick": suggested,
            "suggested_designer": designer, "actual_designers": [actual] if picked else []}


def test_readiness_needs_ten_samples_at_ninety_percent():
    assert not ds._readiness([_row()] * 9)["enough"]
    assert ds._readiness([_row()] * 10)["ready"]
    assert ds._readiness([_row()] * 10 + [_row(picked=False)])["ready"]            # 10/11 >= 90%
    wrong_pick = ds._readiness([_row()] * 10 + [_row(picked=False)] * 2)            # 10/12 < 90%
    assert wrong_pick["enough"] and not wrong_pick["ready"], wrong_pick
    wrong_designer = ds._readiness([_row()] * 8 + [_row(actual="dre")] * 2)
    assert wrong_designer["enough"] and not wrong_designer["ready"], wrong_designer
    # chỉ READY_WINDOW lần gần nhất: 5 lần sai cũ bị đẩy khỏi cửa sổ
    assert ds._readiness([_row(picked=False)] * 5 + [_row()] * 20)["ready"]


# ------------------------------------------------------------ báo cáo
def test_report_lists_only_costly_misses_and_escapes_titles():
    at = NOW - timedelta(days=2)
    logged = {
        # sai designer -> hiện
        "k1": {"key": "k1", "title": "A <b>bold</b> & co", "category": "MODEL", "score": 92,
               "suggested_pick": False, "suggested_designer": "ethan"},
        # gợi ý chọn mà Ông Chủ bỏ -> hiện
        "k2": {"key": "k2", "title": "Chọn nhầm", "category": "TOOL", "score": 81,
               "suggested_pick": True, "suggested_designer": "kite"},
        # gợi ý bỏ mà Ông Chủ chọn, designer đúng -> rẻ, KHÔNG hiện
        "k3": {"key": "k3", "title": "Bỏ sót", "category": "ARXIV", "score": 60,
               "suggested_pick": False, "suggested_designer": "kite"}}
    stories = {
        "k1": {"key": "k1", "picked": True, "designers": {"dre"}, "scan_role": "finn", "scanned_at": at},
        "k2": {"key": "k2", "picked": False, "designers": set(), "scan_role": "finn", "scanned_at": at},
        "k3": {"key": "k3", "picked": True, "designers": {"kite"}, "scan_role": "finn", "scanned_at": at}}
    reviewed = {("finn", ds._local_date(at))}
    text = ds.render(ds.evaluate(logged, stories, reviewed, NOW, 30), "donniechublog", 30)
    assert "A &lt;b&gt;bold&lt;/b&gt; &amp; co" in text, text
    assert "gợi ý Ethan, bạn giao Dre" in text, text
    assert "Chọn nhầm (TOOL, 81): gợi ý chọn → Kite, bạn bỏ" in text, text
    assert "Bỏ sót" not in text, text
    assert "3 tin đã quyết, bạn chọn 2" in text, text
    assert "Designer trùng 1/2 (50%)" in text, text
    assert "Gợi ý chọn đúng 0/1 (0%)" in text, text
    empty = ds.render(ds.evaluate({}, {}, set(), NOW, 30), "dcgr", 30)
    assert "Chưa có tin nào đã quyết" in empty, empty


def test_status_names_what_is_missing():
    assert ds._status(ds._readiness([_row(suggested=False)] * 12)) == "chưa đủ mẫu: gợi ý chọn 0/10"
    assert ds._status(ds._readiness([_row()] * 10)) == "✅ đủ điều kiện tự giao"
    off = ds._status(ds._readiness([_row()] * 8 + [_row(actual="dre")] * 2))
    assert off == "chưa khớp (chọn đúng 10/10, designer 8/10)", off


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
