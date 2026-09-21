#!/usr/bin/env python3
"""dispatch_shadow.py (LOW-349): chạy bóng tự chọn tin.

Giữ các luật làm số đo độ trùng là số thật:
  1. Gợi ý của một tin không phụ thuộc quyết định của chính tin đó, và chỉ học
     từ lượt quét TRƯỚC nó (cùng lượt quét cũng không tính).
  2. Quét lại trong ngày (`_tHHMMSS`) là CÙNG một tin; ngày không chọn tin nào
     không tính là "không chọn"; tin mới hơn DECISION_HOURS là "chờ".
  3. Gợi ý đóng băng trong log, chạy lại không chấm lại; kết quả đọc sống từ
     manifest (Ông Chủ chọn muộn vẫn được tính).
  4. Ngưỡng "đủ điều kiện tự chọn": ≥ 10 mẫu, ≥ 90%, trong 20 lần gần nhất.
  5. Báo cáo chỉ liệt kê lỗi tốn công (gợi ý chọn tin đã bị bỏ).

Chạy:  venv/bin/python tests/test_dispatch_shadow.py
"""
import json
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import dispatch_shadow as ds                                  # noqa: E402
import state_paths                                            # noqa: E402

T0 = datetime(2026, 9, 1, 22, 0, tzinfo=timezone.utc)         # 05:00 VN, giờ quét của Finn
NOW = T0 + timedelta(days=40)


def _item(slug, category="MODEL", score=95, picked=False, index=1):
    return {"index": index, "title": f"Tin {slug}", "link": f"https://x.test/{slug}",
            "category": category, "score": score, "picked": picked}


def _scan(day, items, scan_role="finn", hour=0):
    return {"manifest": f"{scan_role}_candidates_d{day}h{hour}.json", "scan_role": scan_role,
            "scanned_at": T0 + timedelta(days=day, hours=hour), "items": items}


def _history(days=12):
    """Mỗi ngày: một tin MODEL 95 được chọn, một tin TOOL 60 bị bỏ."""
    return [_scan(d, [_item(f"m{d}", "MODEL", 95, picked=True),
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
    k = _by_key(stories)
    m = ds.suggest(k[ds.story_key(_item("new-m"))], table)
    assert (m["suggested_pick"], m["pick_basis"], m["pick_samples"]) == (True, "category_tier", 12), m
    t = ds.suggest(k[ds.story_key(_item("new-t"))], table)
    assert (t["suggested_pick"], t["pick_basis"], t["pick_rate"]) == (False, "category_tier", 0.0), t


def test_pick_falls_back_to_tier_then_to_none():
    stories = ds.gather_stories(_history())
    table = ds.learn(stories, T0 + timedelta(days=20), ds.reviewed_days(stories), NOW)
    sec = ds.suggest({"category": "SECURITY", "score": 91}, table)
    assert (sec["suggested_pick"], sec["pick_basis"]) == (True, "tier"), sec
    mid = ds.suggest({"category": "MODEL", "score": 85}, table)
    assert (mid["suggested_pick"], mid["pick_basis"], mid["pick_samples"]) == (None, "", 0), mid
    unscored = ds.suggest({"category": "BUSINESS", "score": None}, table)       # tin Vera/Nova
    assert unscored["suggested_pick"] is None, unscored


def test_only_earlier_scans_are_learned():
    stories = ds.gather_stories(_history())
    reviewed = ds.reviewed_days(stories)
    early = ds.suggest({"category": "MODEL", "score": 95},
                       ds.learn(stories, T0 + timedelta(days=3), reviewed, NOW))
    assert early["suggested_pick"] is None and early["pick_samples"] == 3, early
    # tin nằm TRONG lượt quét ngày 10: chỉ học ngày 0..9, không học chính lượt của nó
    same = ds.suggest({"category": "MODEL", "score": 95},
                      ds.learn(stories, T0 + timedelta(days=10), reviewed, NOW))
    assert same["suggested_pick"] is True and same["pick_samples"] == 10, same


def test_own_decision_does_not_change_suggestion():
    rows = []
    for picked in (False, True):
        stories = ds.gather_stories(_history() + [_scan(20, [_item("x", "MODEL", 92, picked=picked)])])
        new = ds.score_new(stories, {}, ds.reviewed_days(stories), NOW)
        rows.append([r for r in new if r["key"] == ds.story_key(_item("x"))])
    assert rows[0] == rows[1] and rows[0], rows


# ------------------------------------------------------------ 2. dữ liệu thô
def test_rescans_count_as_one_story():
    scans = [_scan(0, [_item("a"), _item("b", index=2)]),
             _scan(0, [_item("a", picked=True), _item("b", index=2)], hour=2)]
    stories = ds.gather_stories(scans)
    assert len(stories) == 2, stories
    a = _by_key(stories)[ds.story_key(_item("a"))]
    assert a["picked"], a
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


def test_legacy_scan_role_is_canonical():
    with tempfile.TemporaryDirectory() as t:
        state = Path(t)
        _write(state, dict(_scan(0, [_item("a")]), scan_role="scout"))
        _write(state, dict(_scan(1, [_item("b")], scan_role="market")))
        assert [s["scan_role"] for s in ds.load_scans(state)] == ["finn", "vera"]


# ------------------------------------------------------------ 3. log đóng băng
def test_run_freezes_suggestions_and_reads_live_outcome():
    with tempfile.TemporaryDirectory() as t:
        state = Path(t)
        for s in _history():
            _write(state, s)
        target = _scan(20, [_item("late", "MODEL", 92)])
        _write(state, target)
        n, before = ds.run(state, NOW, 60)
        assert n == 25, n
        path = state / state_paths.DISPATCH_SHADOW_FILE
        log = path.read_text(encoding="utf-8").splitlines()
        row = ds.load_log(path)[ds.story_key(_item("late"))]
        assert row["suggested_pick"] is True, row
        assert row["version"] == ds.VERSION and row["manifest"] == target["manifest"], row
        # Ông Chủ chọn muộn: log giữ nguyên, báo cáo thấy kết quả mới
        target["items"][0]["picked"] = True
        _write(state, target)
        n2, after = ds.run(state, NOW, 60)
        assert n2 == 0, n2
        assert path.read_text(encoding="utf-8").splitlines() == log
        assert after["total"]["picked"] == before["total"]["picked"] + 1, (before["total"], after["total"])
        assert after["total"]["hit"] == before["total"]["hit"] + 1, (before["total"], after["total"])


# ------------------------------------------------------------ 4. đủ điều kiện
def _row(picked=True, suggested=True):
    return {"outcome": "picked" if picked else "not_picked", "suggested_pick": suggested}


def test_readiness_needs_ten_samples_at_ninety_percent():
    assert not ds._readiness([_row()] * 9)["ready"]
    assert ds._readiness([_row()] * 10)["ready"]
    assert ds._readiness([_row()] * 10 + [_row(picked=False)])["ready"]            # 10/11 >= 90%
    assert not ds._readiness([_row()] * 10 + [_row(picked=False)] * 2)["ready"]    # 10/12 < 90%
    # gợi ý "bỏ" không tính vào mẫu
    assert not ds._readiness([_row()] * 9 + [_row(suggested=False)] * 5)["ready"]
    # chỉ READY_WINDOW lần gần nhất: 5 lần sai cũ bị đẩy khỏi cửa sổ
    assert ds._readiness([_row(picked=False)] * 5 + [_row()] * 20)["ready"]


def test_status_text():
    assert ds._status(ds._readiness([_row(suggested=False)] * 12)) == "chưa đủ mẫu (0/10)"
    assert ds._status(ds._readiness([_row()] * 10)) == "✅ đủ điều kiện tự chọn"
    assert ds._status(ds._readiness([_row()] * 8 + [_row(picked=False)] * 2)) == "chưa khớp (8/10)"


# ------------------------------------------------------------ 5. báo cáo
def test_report_lists_only_costly_misses_and_escapes_titles():
    at = NOW - timedelta(days=2)
    logged = {
        # gợi ý chọn mà Ông Chủ bỏ -> hiện
        "k1": {"key": "k1", "title": "A <b>bold</b> & co", "category": "TOOL", "score": 81,
               "scan_role": "finn", "suggested_pick": True},
        # gợi ý bỏ mà Ông Chủ chọn -> rẻ, KHÔNG hiện
        "k2": {"key": "k2", "title": "Bỏ sót", "category": "ARXIV", "score": 60,
               "scan_role": "finn", "suggested_pick": False},
        # tin Vera không điểm, chưa có gợi ý
        "k3": {"key": "k3", "title": "Tin Vera", "category": "BUSINESS", "score": None,
               "scan_role": "vera", "suggested_pick": None}}
    stories = {"k1": {"key": "k1", "picked": False, "scan_role": "finn", "scanned_at": at},
               "k2": {"key": "k2", "picked": True, "scan_role": "finn", "scanned_at": at},
               "k3": {"key": "k3", "picked": True, "scan_role": "vera", "scanned_at": at}}
    reviewed = {("finn", ds._local_date(at))}
    text = ds.render(ds.evaluate(logged, stories, reviewed, NOW, 30), "donniechublog", 30)
    assert "A &lt;b&gt;bold&lt;/b&gt; &amp; co (TOOL, 81 điểm, Finn)" in text, text
    assert "Bỏ sót" not in text, text
    assert "3 headline đã quyết, bạn chọn 2" in text, text
    assert "Gợi ý chọn đúng 0/1 (0%)" in text, text
    assert "• Finn: 1/2 · 0/1 (0%) · 0/1 (0%)" in text, text
    assert "• Vera: 1/1 · — · —" in text, text
    empty = ds.render(ds.evaluate({}, {}, set(), NOW, 30), "dcgr", 30)
    assert "Chưa có headline nào đã quyết" in empty, empty


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
