#!/usr/bin/env python3
"""LOW-360 (22/09/2026) — Nova bo sot arena.ai va X @arena.

Do tren dc-group 22/09: danh sach Nova chi co HuggingFace + artificialanalysis.
Hai nguyen nhan:

  1. `_arena_board` bo dong co `rank: 0` — hang TAM arena gan cho model vua len
     bang. MiMo-V2.6-Pro (1628 Elo, 790 vote, CI #8-#18, ~#10 WebDev) mat han.
  2. Nova khong doc tweet @arena. Grok 4.7 "now in the Agent Arena" + poll 21/09
     luc chua bang nao co ten no — chi X moi co.

Chay:  venv/bin/python tests/test_low360_nova_arena_sources.py
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import arena_x  # noqa: E402
import scan_models as sm  # noqa: E402


def _row(name, rank, rating, **extra):
    return {"rank": rank, "modelDisplayName": name, "rating": rating, "votes": 1000,
            "modelOrganization": extra.pop("org", "OpenAI"), **extra}


# Trich payload webdev that 22/09 (rut gon): 9 model co hang, mimo-v2.6-pro rank 0.
WEBDEV = [_row(f"m{i}", i, 1800 - i * 15) for i in range(1, 10)] + [
    _row("mimo-v2.6-pro", 0, 1628.15, rankUpper=8, rankLower=18, org="Xiaomi"),
    _row("m10", 10, 1600),
]


class _Resp:
    def __init__(self, text):
        self.text = text


def _html(rows):
    """Trang arena gia: payload RSC trong self.__next_f.push([1, "..."])."""
    raw = json.dumps({"entries": rows})
    return f'<script>self.__next_f.push([1,{json.dumps(raw)}])</script>'


def _board(rows):
    cu = sm._get
    sm._get = lambda url, timeout=0: _Resp(_html(rows))
    try:
        return sm._arena_board("code/webdev")
    finally:
        sm._get = cu


def test_rank_zero_model_kept_with_provisional_rank_by_elo():
    rows = _board(WEBDEV)
    mimo = [r for r in rows if r["name"] == "mimo-v2.6-pro"]
    assert mimo, [r["name"] for r in rows]
    assert mimo[0]["rank"] == 10 and mimo[0]["provisional"] is True, mimo
    assert mimo[0]["rank_ci"] == [8, 18], mimo


def test_ranked_rows_unchanged_and_sorted():
    rows = _board(WEBDEV)
    assert [r["name"] for r in rows[:9]] == [f"m{i}" for i in range(1, 10)]
    assert [r["rank"] for r in rows] == sorted(r["rank"] for r in rows)
    assert not any(r.get("provisional") for r in rows if r["name"] != "mimo-v2.6-pro")


def test_real_rank_beats_provisional_duplicate():
    """Cung model hai provider: ban co hang that thang ban hang tam."""
    rows = _board([_row("x-1", 3, 1500), _row("x-1", 0, 1700, rankUpper=1, rankLower=4)])
    assert rows == [r for r in rows if r["name"] == "x-1"] and len(rows) == 1
    assert rows[0]["rank"] == 3 and not rows[0].get("provisional")


def test_provisional_entry_becomes_climb_news():
    rows = _board(WEBDEV)
    cu = {"webdev": {f"m{i}": i for i in range(1, 11)}}
    # Cat top 10 DUNG nhu main(): mimo #10 tam dong hang m10, dung SAU no.
    leo = sm.count_rank({"webdev": sm.top_rows(rows, 10)}, cu)
    mimo = [x for x in leo if x["name"] == "mimo-v2.6-pro"]
    assert mimo and "MOI vao bang" in mimo[0]["note"], leo
    assert "hang TAM" in mimo[0]["note"] and "#8-#18" in mimo[0]["note"], mimo


# Nguyen van dong dau cac tweet @arena doc tu x.com/arena 22/09.
TWEETS = {
    "MiMo-V2.6-Pro just landed @XiaomiMiMo back in the top 10 on Code Arena: WebDev": "MiMo-V2.6-Pro",
    "Grok 4.7 by @SpaceXAI and @elonmusk is now in the Agent Arena!": "Grok 4.7",
    "Grok 4.7 by @SpaceXAI just dropped. Looking at how past Grok versions have trended": "Grok 4.7",
    "Gemini Omni 1.1 Flash has landed #1 in the Text-to-Video Arena": "Gemini Omni 1.1 Flash",
    "Introducing Agent Mode: Agentic AI is now measured in the Arena.": "",
    "What can user praise and complaints tell us about coding agents themselves?": "",
    "https://t.co/S3ErIXcnoe": "",
}


def test_model_name_from_arena_tweet():
    for text, ten in TWEETS.items():
        assert sm.arena_tweet_model(text) == ten, (text, sm.arena_tweet_model(text))


NOW = datetime(2026, 9, 22, 3, 0, tzinfo=timezone.utc)
PAGE = [
    {"url": "https://x.com/arena/status/2062565126600114484", "handle": "arena",
     "created": "2026-06-04T16:00:00.000Z", "text": "Introducing Agent Mode: ..."},        # ghim cu
    {"url": "https://x.com/XiaomiMiMo/status/2102138559952290106", "handle": "xiaomimimo",
     "created": "2026-09-21T20:51:00.000Z", "text": "Introducing Xiaomi MiMo-V2.6 — Pro & Flash."},
    {"url": "https://x.com/arena/status/2102142912943489220", "handle": "arena",
     "created": "2026-09-21T21:08:00.000Z",
     "text": "MiMo-V2.6-Pro just landed @XiaomiMiMo back in the top 10 on Code Arena: WebDev\n\nIt scores 1628"},
    {"url": "https://x.com/arena/status/2102074819743453410", "handle": "arena",
     "created": "2026-09-21T16:37:00.000Z", "text": "Grok 4.7 by @SpaceXAI and @elonmusk is now in the Agent Arena!"},
]


def _fetch(page, ngay=7):
    cu = arena_x.page_tweets
    arena_x.page_tweets = lambda url: page
    try:
        return sm.fetch_arena_tweets(ngay, now=NOW)
    finally:
        arena_x.page_tweets = cu


def test_fetch_keeps_only_recent_arena_tweets():
    ra = _fetch(PAGE)
    assert [t["url"].rsplit("/", 1)[1] for t in ra] == ["2102142912943489220", "2102074819743453410"], ra
    assert [t["model"] for t in ra] == ["MiMo-V2.6-Pro", "Grok 4.7"]


def test_empty_profile_page_is_a_broken_source_not_silence():
    try:
        _fetch([])
    except RuntimeError:
        return
    raise AssertionError("trang x.com/arena rong phai NEM de vao muc NGUON HONG")


def test_arena_tweet_is_required_item_with_tweet_link():
    bat = []
    cu = sm.required.extra_many
    sm.required.extra_many = lambda vai, muc: bat.extend(muc)
    try:
        sm.write_required([], [], [], _fetch(PAGE))
    finally:
        sm.required.extra_many = cu
    x = {m[0]: m for m in bat if m[2] == "arena_x"}
    assert set(x) == {"arena_x|mimo-v2.6-pro", "arena_x|grok 4.7"}, bat
    assert x["arena_x|grok 4.7"][4] == "https://x.com/arena/status/2102074819743453410"


def test_arena_tweets_section_printed_in_report():
    import contextlib
    import io
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        sm._in_report({"arena_tweets": _fetch(PAGE)})
    out = buf.getvalue()
    assert "=== X @arena (2)" in out and "https://x.com/arena/status/2102142912943489220" in out, out


def test_arena_x_label_registered():
    assert sm.LABEL_BOARD.get("arena_x") == "X @arena"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
