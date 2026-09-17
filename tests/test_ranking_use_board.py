#!/usr/bin/env python3
"""LOW-22 (12/09/2026): tin xep hang lay anh BANG KHAC voi bang tieu de noi.

Ca that: the Ethan "claude-opus-4-7-high leo lên #3 bảng văn bản Arena, chốt
1501.8 điểm Elo" di kem anh khoanh hang #26 — la bang WebDev/Code Arena, khong
phai Text Arena. Hai lo:
  1. TOPIC khong co muc nao cho bang text, nen mot chu "code" trong than bai
     goc day arena-code (+200) len tren arena-text.
  2. `mentioned` so theo TEN MIEN; bay bang arena chung mot mien nen tin co link
     arena.ai lam ca 7 bang deu "duoc nhac" -> canh bao "BANG KHAC" khong no.
Fail tren code cu (da doi chung), pass tren code moi.

Chay:  venv/bin/python tests/test_ranking_use_board.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import ranking as xh                                        # noqa: E402

TD = "claude-opus-4-7-high leo lên #3 bảng văn bản Arena, chốt 1501.8 điểm Elo"
LINK = "https://arena.ai/leaderboard/text"
CHU = "Anthropic nói model mới mạnh hơn ở code và toán."   # 1 chu 'code' trong bai goc


def test_story_board_text_no_got_board_code_snatch_vi_than_article_has_text_code():
    ds = xh.suggest_sources(TD, LINK, "Arena", CHU)
    assert ds[0]["id"] == "arena-text", [n["id"] for n in ds[:3]]


def test_ok_mention_by_board_no_only_by_domain():
    ds = {n["id"]: n for n in xh.suggest_sources(TD, LINK, "Arena", CHU)}
    assert ds["arena-text"]["mentioned"] is True
    # Cung mien arena.ai nhung tieu de/link khong noi toi bang code
    assert ds["arena-code"]["mentioned"] is False
    assert ds["arena-vision"]["mentioned"] is False


def test_warning_board_other_no_when_capture_ok_board_code_wait_story_text():
    """Manifest nhu engine ghi khi (van) chup duoc arena-code: cau brief phai co ⚠️."""
    from prepare.manifest import describe_ranking_image
    ds = {n["id"]: n for n in xh.suggest_sources(TD, LINK, "Arena", CHU)}
    m = {"ranking": {"site": "ARENA.AI", "board": "WebDev / Code Arena", "kind": "table",
                     "model": "claude-opus-4-7-high", "rank": 26,
                     "mentioned": ds["arena-code"]["mentioned"]}}
    assert "BẢNG KHÁC" in describe_ranking_image(m), describe_ranking_image(m)


def test_story_really_about_code_still_out_arena_code():
    ds = xh.suggest_sources("Kimi-K3 leo lên #1 Frontend Code Arena", "", "", "")
    assert ds[0]["id"] == "arena-code", [n["id"] for n in ds[:3]]
    # "Arena" tran khong khop mien `arena\.ai|lmarena` (hanh vi cu, giu nguyen):
    # khong link thi khong nguon nao "duoc nhac", chi thu tu la doi.
    assert all(n["mentioned"] is False for n in ds), [n["id"] for n in ds if n["mentioned"]]


def test_link_code_make_board_code_ok_mention():
    ds = {n["id"]: n for n in xh.suggest_sources("Qwen 3.8 vào top WebDev", "https://arena.ai/leaderboard/code", "", "")}
    assert ds["arena-code"]["mentioned"] is True
    assert ds["arena-text"]["mentioned"] is False


if __name__ == "__main__":
    ok = 0
    ten = [k for k in list(globals()) if k.startswith("test_")]
    for k in ten:
        try:
            globals()[k]()
            ok += 1
        except AssertionError as e:
            print(f"    FAIL {k}: {e}")
    print(f"{Path(__file__).name:<34} {ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
