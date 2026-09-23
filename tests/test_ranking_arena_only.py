#!/usr/bin/env python3
"""LOW-389 (23/09/2026) — anh xep hang CHI lay tu arena.ai.

Ong Chu: *"vi anh ko dep nen chung ta moi chi dung source arena.ai, con AA chi
dung de tang tinh confirm"* — *"Chung ta quet arena.ai thoi, cac benchmark site
con lai la nguon su that"*.

Do 23/09 tren toan bo log con trong `state`: arena ra 40/45 tam anh, aa-models ra
0/45. OpenRouter bi bo tu LOW-185 (16/09) nhung luc do chi go o `scan_models` —
o `ranking.SOURCE` no van song va van de ra 3 tam anh tu bang LUOT DUNG.

Chay:  python tests/test_ranking_arena_only.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import model_boards  # noqa: E402
import ranking  # noqa: E402
import required  # noqa: E402

GONE = ["aa-models", "tbench", "swebench", "livebench", "aider", "openrouter",
        "livecodebench", "bfcl", "gaia", "hle", "vellum", "opencompass"]


def test_only_arena_boards_can_become_an_image():
    ids = [n["id"] for n in ranking.SOURCE]
    assert ids, "registry rong thi khong con duong anh nao"
    assert all(i.startswith("arena") for i in ids), ids
    for i in GONE:
        assert i not in ids, f"{i} van con tren duong anh"


def test_openrouter_is_gone_everywhere_not_just_half():
    """LOW-185 (16/09) bo OpenRouter, nhung chi go o `scan_models` — `ranking` van
    giu no them mot tuan va van ra 3 tam anh tu bang luot dung."""
    assert "openrouter" not in repr(ranking.SOURCE).lower()
    assert "openrouter" not in repr(ranking.TOPIC).lower()
    assert not ranking.source_page_is_board("https://openrouter.ai/rankings")
    # Chu thich/tai lieu VAN duoc nhac ten no — do la cho ghi VI SAO no bien mat.


def test_topic_never_points_at_a_source_that_does_not_exist():
    ids = {n["id"] for n in ranking.SOURCE}
    la = [m for _, mas in ranking.TOPIC for m in mas if m not in ids]
    assert not la, f"TOPIC tro toi nguon khong ton tai: {la}"


def test_a_story_about_another_board_no_longer_captures_it():
    """Cai gia da biet truoc: tin ve chinh mot bang khac gio ra THE CHU."""
    ds = ranking.suggest_sources("Grok 4.7 vao top 6 Terminal-Bench", "")
    assert [n["id"] for n in ds if ranking.source_proves_story(n)] == []


def test_a_story_on_an_arena_board_still_gets_its_image():
    ds = ranking.suggest_sources("Kimi-K3 leo len #1 WebDev Arena",
                                 "https://arena.ai/leaderboard/code/webdev")
    assert "arena-code" in [n["id"] for n in ds if ranking.source_proves_story(n)]


def test_the_source_page_rung_is_arena_only_now():
    """Nac LOW-385 doc registry, nen no phai hep lai cung luc — khong thi luat moi
    thung ngay o cho vua va."""
    assert ranking.source_page_is_board("https://arena.ai/leaderboard/code/webdev")
    for u in ("https://artificialanalysis.ai/leaderboards/models",
              "https://artificialanalysis.ai/text-to-speech",
              "https://www.tbench.ai/leaderboard",
              "https://openrouter.ai/rankings"):
        assert not ranking.source_page_is_board(u), u


def test_benchmark_sites_stay_as_sources_of_truth():
    """Chung ra khoi duong ANH, KHONG ra khoi nguon so lieu: Nova van doc diem va
    muc BAT BUOC van can link (`model_boards` + `required.LINK_BOARD`)."""
    khoa = {b.khoa for b in model_boards.BOARD}
    for k in ("tbench", "livebench", "swebench", "intelligence", "coding", "hle"):
        assert k in khoa, k
        assert required.LINK_BOARD.get(k, "").startswith("https://"), k


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
