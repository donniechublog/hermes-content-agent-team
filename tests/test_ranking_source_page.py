#!/usr/bin/env python3
"""LOW-385 (23/09/2026) — khong khoanh duoc hang thi chup lay bang cua CHINH trang nguon.

Ong Chu: *"sao chung ta ko chup luon trang nay ma lai dung text nhi?"* — bai
23/09 co `link goc` la chinh trang bang cua artificialanalysis, engine da mo
trang do o buoc [browser], roi van in THE CHU.

Do 23/09 tren may chu: 23 bai roi ve the chu, 4 bai co link goc la trang bang
(artificialanalysis x3, arena.ai x1) — trong do 3 bang (text-to-speech,
speech-to-text, code/webdev) KHONG co muc rieng trong registry `SOURCE`, nen
vong di nguon khong bao gio cham toi chung.

Chay:  python tests/test_ranking_source_page.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import manifest_values  # noqa: E402
import ranking  # noqa: E402

# Bon `link goc` THAT, lay tu brief.md cua cac bai da roi ve the chu tren may chu.
BOARD_PAGES = [
    "https://artificialanalysis.ai/leaderboards/models",
    "https://artificialanalysis.ai/text-to-speech",
    "https://artificialanalysis.ai/speech-to-text",
    "https://arena.ai/leaderboard/code/webdev",
]
ARTICLE_PAGES = [
    "https://techcrunch.com/2026/09/11/kimi-maker-moonshot-ai-targets-2-billion-in-annual-revenue/",
    "https://www.reuters.com/world/chinas-deepseek-taps-citic-securities-domestic-ipo-sources-say-2026-09-09/",
    "https://arstechnica.com/ai/2026/09/researchers-used-claude-to-hack-openai/",
    "https://huggingface.co/Comfy-Org/Qwen-Image-2.1",
    "",
]


def test_only_a_board_page_opens_the_new_rung():
    for url in BOARD_PAGES:
        assert ranking.source_page_is_board(url), url
    for url in ARTICLE_PAGES:
        assert not ranking.source_page_is_board(url), f"{url} khong phai trang bang"


def test_three_of_those_boards_have_no_entry_in_the_registry():
    """Ly do nac nay ton tai: vong di nguon khong bao gio toi duoc cac bang do."""
    urls = {n["url"] for n in ranking.SOURCE}
    ngoai = [u for u in BOARD_PAGES if u not in urls]
    assert len(ngoai) == 3, ngoai


def test_it_only_grabs_a_real_table_or_chart():
    """Khong lui ve chup ca trang: chup dai mot trang bai roi goi la anh xep hang
    dung la loi LOW-179 cam."""
    assert ranking.BOARD_PICK == ["table", "figure", "svg", "canvas"]
    import capture_chart
    assert "img" in capture_chart.PICK_DEFAULT and "img" not in ranking.BOARD_PICK


def test_the_new_kind_is_a_real_capture_but_says_it_did_not_highlight():
    assert ranking.is_capture("board-page"), "van la anh THAT cua mot bang"
    assert not ranking.is_capture("card")
    assert manifest_values.ranking_kind_label("board-page") == "bang-trang-nguon"
    import prepare.fallback_rounds as fr
    muc = fr._image_item_ranking(0, {"kind": "board-page", "file_path": "/tmp/x.png",
                                     "url": BOARD_PAGES[0], "site": "ARTIFICIALANALYSIS.AI",
                                     "board": "LLM Leaderboard", "model": "Claude Opus 5.5",
                                     "rank": None})
    assert "CHƯA khoanh hàng" in muc["alt"], muc["alt"]
    assert "đã khoanh hàng" not in muc["alt"], "khong duoc khang dinh da khoanh"
    assert muc["chart_hint"] is True


def test_the_card_still_says_it_is_a_card():
    import prepare.fallback_rounds as fr
    muc = fr._image_item_ranking(0, {"kind": "card", "file_path": "/tmp/x.png",
                                     "url": BOARD_PAGES[0], "site": "LIVEBENCH.AI",
                                     "board": "LiveBench", "model": "Claude Opus 5.5", "rank": None})
    assert "THẺ DỰ PHÒNG" in muc["alt"] and muc["chart_hint"] is False


def test_the_rung_is_skipped_when_the_source_is_not_a_board():
    """Ham dieu phoi khong duoc mo browser cho mot link bai thuong."""
    goi = []
    saved = ranking.capture_source_board
    ranking.capture_source_board = lambda *a, **k: goi.append(a) or None
    try:
        assert ranking._board_page_result(None, ["X"], ARTICLE_PAGES[0], Path("."), lambda *_: None) is None
        assert goi == [], "da goi chup du link khong phai trang bang"
    finally:
        ranking.capture_source_board = saved


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
