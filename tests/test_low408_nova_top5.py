#!/usr/bin/env python3
"""LOW-408 (25/09/2026) — Nova chi bao top 5: toan cau + My + Trung Quoc.

Do tren dc-group: bao cao Nova 24/09 co 34 muc, trong do 10 muc la model hang
#6-#9 ("leo 1 bac #9 -> #8") va 10 repo HuggingFace. Ong Chu chot: ngoai top 5
khong liet ke; ra mat hang thap khong bao; HF chi top trending; Mistral vao
top 5 toan cau thi nhan.

Chay:  venv/bin/python tests/test_low408_nova_top5.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import scan_models as sm  # noqa: E402


def _r(name, rank, region):
    return {"name": name, "rank": rank, "region": region}


# #1-#6 My, #7 Mistral, #8-#13 Trung Quoc.
BOARD = ([_r(f"us{i}", i, "my") for i in range(1, 7)] + [_r("mistral", 7, "khac")]
         + [_r(f"cn{i}", i, "tq") for i in range(8, 14)])


def test_report_rows_top5_global_us_china():
    names = [r["name"] for r in sm.report_rows(BOARD)]
    assert names == ["us1", "us2", "us3", "us4", "us5",
                     "cn8", "cn9", "cn10", "cn11", "cn12"], names


def test_other_country_only_in_global_top5():
    top = [_r("us1", 1, "my"), _r("us2", 2, "my"), _r("us3", 3, "my"),
           _r("mistral", 4, "khac"), _r("us5", 5, "my"), _r("xai", 6, "khac")]
    names = [r["name"] for r in sm.report_rows(top)]
    assert "mistral" in names and "xai" not in names, names


def test_board_without_region_is_global_top5():
    rows = [_r(f"m{i}", i, "khac") for i in range(1, 11)]
    assert [r["name"] for r in sm.report_rows(rows)] == [f"m{i}" for i in range(1, 6)]


def test_climb_outside_top5_is_not_news():
    """Nhu main(): count_rank chi thay phan report_rows cua bang."""
    now = [_r("a", 1, "khac"), _r("b", 2, "khac"), _r("c", 3, "khac"),
           _r("up4", 4, "khac"), _r("d", 5, "khac"), _r("up6", 6, "khac")]
    cu = {"text": {"a": 1, "b": 2, "c": 3, "d": 5, "up4": 8, "up6": 8}}
    leo = sm.count_rank({"text": sm.report_rows(now)}, cu)
    names = [x["name"] for x in leo]
    assert names == ["up4"], leo
    assert leo[0]["note"] == "leo 4 bac: #8 -> #4", leo


def test_china_top5_climb_is_news_even_below_global_top5():
    cu = {"text": {r["name"]: r["rank"] + 3 for r in BOARD}}
    leo = sm.count_rank({"text": sm.report_rows(BOARD)}, cu)
    names = {x["name"] for x in leo}
    assert "cn8" in names and "us6" not in names and "mistral" not in names, names


def test_release_low_rank_dropped():
    keys = sm.reported_keys({"coding": [_r("GPT-6 Astra", 1, "khac")]})
    assert not sm.keep_release({"original_name": "Tiny Model", "coding_rank": 30}, keys)
    assert sm.keep_release({"original_name": "Some Model", "coding_rank": 3}, keys)
    assert sm.keep_release({"original_name": "GPT-6 Astra", "coding_rank": None}, keys)


def test_arena_tweet_rank_outside_top5_dropped():
    assert not sm.tweet_in_top("Real-world results are in for GPT-6 Luna (Max). It just landed #24 in the Code Arena")
    assert not sm.tweet_in_top("MiMo-V2.6-Pro just landed back in the top 10 on Code Arena: WebDev")
    assert sm.tweet_in_top("Claude Opus 5.5 (Max) landed #1 in the Code Arena: WebDev")
    assert sm.tweet_in_top("Grok 4.7 by @SpaceXAI is now in the Agent Arena!")


def test_hf_and_board_ceilings_are_top5():
    assert sm.REPORT_TOP == 5
    assert sm.CEILING_HF == sm.REPORT_TOP and sm.CEILING_BOARD == sm.REPORT_TOP


def test_board_print_shows_china_counterweight():
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sm._in_board("VAN BAN", BOARD)
    out = buf.getvalue()
    assert "cn8" in out and "us5" in out, out
    assert "us6" not in out and "mistral" not in out, out


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
