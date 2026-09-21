#!/usr/bin/env python3
"""LOW-352 (21/09/2026) — Nova/Vera tự chấm điểm 0–100, để chạy bóng (LOW-349)
đoán được headline nào được chọn ở dcgr.

Giữ:
  1. Nova/Vera: score = score_impact + score_relevance (mỗi phần 0–50), thành phần
     ghi vào manifest; sai dải / không phải số thì cắt và ghi "script sua" vào
     score_reason (cùng luật Finn); thiếu cả hai thì score null, KHÔNG bỏ tin.
  2. Qinn không đổi: không điểm, không thêm khoá.
  3. Báo cáo quét KHÔNG in điểm Nova/Vera (Ông Chủ thấy điểm sẽ chọn theo, chạy
     bóng đo sai); Finn in như cũ.
  4. Khung nộp trong brief Nova/Vera có đúng hai thành phần của manifest_write
     (cùng dải) + score_reason; brief Finn/Qinn không có.
  5. Finn vẫn dùng chung bộ kiểm điểm (manifest_common.score_part), thông báo không đổi.

Chạy:  venv/bin/python tests/test_low352_scan_scores.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import manifest_common as mc  # noqa: E402
import manifest_report  # noqa: E402
import manifest_write as mw  # noqa: E402
import scan_prepare as sp  # noqa: E402
import state_paths  # noqa: E402

from tam import bat_buoc_tam  # noqa: E402

SOURCE = [{"title": "Stripe buys OpenRouter", "link": "https://www.reuters.com/a",
           "outlet_count": 3, "outlets": ["Reuters", "Bloomberg", "FT"]}]


def _vera(**extra):
    it = {"k": 1, "title": "Stripe mua OpenRouter", "summary_vi": "Thâu tóm lớn"}
    it.update(extra)
    return it


# ------------------------------------------------------------ 1. điểm Nova/Vera
def test_vera_score_is_the_sum_of_two_parts():
    m = mw._item_from_submit(_vera(score_impact=42, score_relevance=38, score_reason="thâu tóm lớn"),
                             1, SOURCE, "vera", "vera")
    assert (m["score"], m["score_impact"], m["score_relevance"]) == (80, 42, 38), m
    assert m["score_reason"] == "thâu tóm lớn", m


def test_nova_and_the_old_market_slug_are_scored_too():
    n = mw._item_from_submit({"title": "Qwen4 lên top 3 WebDev", "link": "https://openrouter.ai/q",
                              "score_impact": 45, "score_relevance": 30}, 1, [], "nova", "nova")
    assert n["score"] == 75, n
    m = mw._item_from_submit(_vera(score_impact=10, score_relevance=5), 1, SOURCE, "market", "vera")
    assert m["score"] == 15, m


def test_out_of_range_and_non_number_are_clamped_and_noted():
    m = mw._item_from_submit(_vera(score_impact=80, score_relevance="cao", score_reason="lớn"),
                             1, SOURCE, "vera", "vera")
    assert (m["score_impact"], m["score_relevance"], m["score"]) == (50, 0, 50), m
    assert m["score_reason"].startswith("lớn | script sua:"), m["score_reason"]
    assert "score_impact phai 0-50" in m["score_reason"] and "score_relevance khong phai so" in m["score_reason"]


def test_missing_parts_give_null_score_but_keep_the_item():
    m = mw._item_from_submit(_vera(), 1, SOURCE, "vera", "vera")
    assert m is not None and m["score"] is None and "score_impact" not in m, m
    half = mw._item_from_submit(_vera(score_impact=30), 1, SOURCE, "vera", "vera")
    assert half["score"] == 30 and half["score_relevance"] == 0, half
    assert half["score_reason"].startswith("script sua: score_relevance khong phai so"), half


def test_qinn_is_untouched():
    q = mw._item_from_submit({"title": "Repo mới", "link": "https://github.com/a/b",
                              "score_impact": 40, "score_relevance": 40}, 1, [], "qinn", "qinn")
    assert q["score"] is None and "score_impact" not in q and "score_relevance" not in q, q


# ------------------------------------------------------------ 2. báo cáo
def test_report_hides_nova_vera_scores_but_keeps_finn():
    items = [{"index": 1, "title": "Tin", "via": "reuters.com", "source_note": "", "score": 80}]
    for vai in ("vera", "market", "nova", "qinn"):
        assert "[80đ]" not in manifest_report.use(items, vai, "2026-09-21"), vai
    assert "<b>1.</b> [80đ] Tin" in manifest_report.use(items, "finn", "2026-09-21")


# ------------------------------------------------------------ 3. brief
def _briefs() -> dict:
    """Dựng brief thật của bốn vai từ dữ liệu quét giả (tệp mới -> không chạy lại script quét)."""
    with tempfile.TemporaryDirectory() as t, bat_buoc_tam(t):
        out = {}
        for vai, name, data in (
                ("finn", "candidates.json", {"candidates": []}),
                ("vera", state_paths.SCAN_RESULT_FILE, {"new_stories": SOURCE, "scanned_total": 1}),
                ("qinn", state_paths.SCAN_RESULT_FILE, {"new_stories": []})):
            wd = Path(t) / vai
            wd.mkdir()
            (wd / name).write_text(json.dumps(data), encoding="utf-8")
            out[vai] = {"finn": sp.brief_scout, "vera": sp.brief_market, "qinn": sp.brief_qinn}[vai](wd, False, vai)
        wd = Path(t) / "nova"
        wd.mkdir()
        (wd / "scan_models.txt").write_text("BÁO CÁO\n[stderr]\n", encoding="utf-8")
        out["nova"] = sp.brief_nova(wd, False, "nova")
        return out


def test_brief_frames_ask_nova_and_vera_for_the_same_parts_manifest_write_reads():
    b = _briefs()
    for vai in ("nova", "vera"):
        for key, high in mw.SCORE_PARTS:
            assert f'"{key}": "<0-{high}' in b[vai], (vai, key)
        assert '"score_reason"' in b[vai] and sp.SCORE_NOTE in b[vai], vai
    for vai in ("finn", "qinn"):
        assert "score_impact" not in b[vai] and sp.SCORE_NOTE not in b[vai], vai


# ------------------------------------------------------------ 4. Finn
def test_finn_clamp_messages_unchanged():
    problems = []
    assert mc.score_part(99, "score_technical", 30, problems, "Bai") == (30, True)
    assert mc.score_part("24 diem", "score_relevance", 20, problems, "Bai") == (0, True)
    assert mc.score_part(12, "score_relevance", 20, problems, "Bai") == (12, False)
    assert problems == ["score_technical phai 0-30, nhan 99 -> cat ve dai (bai: Bai)",
                        "score_relevance khong phai so: '24 diem' -> 0 (bai: Bai)"], problems


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
