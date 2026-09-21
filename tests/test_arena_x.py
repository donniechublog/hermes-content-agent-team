#!/usr/bin/env python3
"""LOW-337 (21/09/2026) — anh xep hang lay tu X cua arena.ai TRUOC, bang ben khac sau.

Chay:  python tests/test_arena_x.py
"""
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import arena_x  # noqa: E402
import ranking  # noqa: E402

NOW = datetime(2026, 9, 21, tzinfo=timezone.utc)


def _tw(text, created="2026-09-15T10:00:00.000Z", handle="arena", url="https://x.com/arena/status/2093015572212846673"):
    return arena_x._record(url, handle, created, text)


def test_exact_model_with_version_only():
    m = ["Qwen-Image-2.1"]
    assert arena_x.tweet_matches("Qwen-Image-2.1 by @Alibaba_Qwen lands #2 in Image Edit Arena", m)
    assert arena_x.tweet_matches("qwen image 2.1 is live", m)
    assert not arena_x.tweet_matches("Qwen-Image-2.0 by @Alibaba_Qwen is in the Image Arena", m)
    assert not arena_x.tweet_matches("Qwen-Image is live in the Arena", m), "ten ngan mat so phien ban"
    assert not arena_x.tweet_matches("Qwen-Image-2.15 preview", m)


def test_only_the_headline_counts():
    t = ("Big news: Gemini Omni 1.1 Flash has landed #1 in the Text-to-Video Arena!\n\n"
         "For Image-to-Video the release is a strong +25pt improvement from Gemini Omni Flash")
    assert arena_x.tweet_matches(t, ["Gemini Omni 1.1 Flash"])
    assert not arena_x.tweet_matches(t, ["Gemini Omni Flash", "Gemini Omni"]), "ban cu chi duoc nhac de so sanh"


def test_short_names_only_when_they_keep_the_version():
    assert arena_x.model_keys(["Gemini Omni Flash", "Gemini Omni"]) == ["gemini omni flash"]
    assert not arena_x.tweet_matches("Gemini Omni 2 Flash lands #1", ["Gemini Omni", "Gemini"])
    assert arena_x.model_keys(["GPT-6 Astra (max)", "GPT-6 Astra", "GPT-6"])[-1] == "gpt 6"


def test_usable_filters_handle_age_url():
    m = ["Qwen-Image-2.1"]
    assert arena_x.usable(_tw("Qwen-Image-2.1 #1"), m, NOW)
    assert not arena_x.usable(_tw("Qwen-Image-2.1 #1", handle="designarena"), m, NOW)
    assert not arena_x.usable(_tw("Qwen-Image-2.1 #1", created="2026-06-01T00:00:00.000Z"), m, NOW)
    assert not arena_x.usable(_tw("Qwen-Image-2.1 #1", url=""), m, NOW)


def test_status_ids_from_search_html():
    html = ('<a href="https://x.com/arena/status/2093015572212846673">x</a>'
            '<a href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fx.com%2Farena%2Fstatus%2F2029284431278862660">y</a>'
            '<a href="https://x.com/someoneelse/status/2029284431278862999">z</a>')
    assert [m.group(2) for m in arena_x._STATUS.finditer(html)] == ["2093015572212846673", "2029284431278862660"]


def test_arena_x_is_a_real_capture_and_goes_first():
    assert ranking.is_capture(arena_x.KIND)
    saved = arena_x.find_arena_images
    hit = [{"file_path": "a.png", "kind": arena_x.KIND, "source": "arena-x", "site": arena_x.SITE,
            "board": "b", "rank": None, "model": "qwen image 2.1", "url": "u", "row": "b", "logo": None,
            "mentioned": True}]
    arena_x.find_arena_images = lambda models, out_dir, in_log=print: hit
    try:
        assert ranking.find_and_capture_many(["Qwen-Image-2.1"], [], Path("."), in_log=lambda *_: None) == hit
        assert ranking.find_and_capture(["Qwen-Image-2.1"], [], Path("."), in_log=lambda *_: None) == hit[0]
    finally:
        arena_x.find_arena_images = saved



def test_uses_team_skills_not_ad_hoc_search():
    """Ong Chu 21/09/2026: "skill crawl X trong repo cua chung ta co roi, tan dung thoi"."""
    src = (ROOT / "arena_x.py").read_text(encoding="utf-8")
    assert arena_x.SOCIAL_FETCH.exists() and arena_x.GET_SOURCE.exists()
    assert "duckduckgo" not in src.lower() and "syndication" not in src.lower()


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
