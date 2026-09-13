#!/usr/bin/env python3
"""LOW-22 (12/09/2026): tin xep hang lay anh BANG KHAC voi bang tieu de noi.

Ca that: the Ethan "claude-opus-4-7-high leo lên #3 bảng văn bản Arena, chốt
1501.8 điểm Elo" di kem anh khoanh hang #26 — la bang WebDev/Code Arena, khong
phai Text Arena. Hai lo:
  1. CHU_DE khong co muc nao cho bang text, nen mot chu "code" trong than bai
     goc day arena-code (+200) len tren arena-text.
  2. `duoc_nhac` so theo TEN MIEN; bay bang arena chung mot mien nen tin co link
     arena.ai lam ca 7 bang deu "duoc nhac" -> canh bao "BANG KHAC" khong no.
Fail tren code cu (da doi chung), pass tren code moi.

Chay:  venv/bin/python tests/test_xep_hang_dung_bang.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import xep_hang as xh                                        # noqa: E402

TD = "claude-opus-4-7-high leo lên #3 bảng văn bản Arena, chốt 1501.8 điểm Elo"
LINK = "https://arena.ai/leaderboard/text"
CHU = "Anthropic nói model mới mạnh hơn ở code và toán."   # 1 chu 'code' trong bai goc


def test_tin_bang_text_khong_bi_bang_code_cuop_vi_than_bai_co_chu_code():
    ds = xh.goi_y_nguon(TD, LINK, "Arena", CHU)
    assert ds[0]["ma"] == "arena-text", [n["ma"] for n in ds[:3]]


def test_duoc_nhac_theo_bang_khong_chi_theo_mien():
    ds = {n["ma"]: n for n in xh.goi_y_nguon(TD, LINK, "Arena", CHU)}
    assert ds["arena-text"]["duoc_nhac"] is True
    # Cung mien arena.ai nhung tieu de/link khong noi toi bang code
    assert ds["arena-code"]["duoc_nhac"] is False
    assert ds["arena-vision"]["duoc_nhac"] is False


def test_canh_bao_bang_khac_no_khi_chup_duoc_bang_code_cho_tin_text():
    """Manifest nhu engine ghi khi (van) chup duoc arena-code: cau brief phai co ⚠️."""
    from chuan_bi.manifest import describe_ranking_image
    ds = {n["ma"]: n for n in xh.goi_y_nguon(TD, LINK, "Arena", CHU)}
    m = {"xep_hang": {"site": "ARENA.AI", "bang": "WebDev / Code Arena", "kieu": "bang",
                      "model": "claude-opus-4-7-high", "hang": 26,
                      "duoc_nhac": ds["arena-code"]["duoc_nhac"]}}
    assert "BẢNG KHÁC" in describe_ranking_image(m), describe_ranking_image(m)


def test_tin_that_su_ve_code_van_ra_arena_code():
    ds = xh.goi_y_nguon("Kimi-K3 leo lên #1 Frontend Code Arena", "", "", "")
    assert ds[0]["ma"] == "arena-code", [n["ma"] for n in ds[:3]]
    # "Arena" tran khong khop mien `arena\.ai|lmarena` (hanh vi cu, giu nguyen):
    # khong link thi khong nguon nao "duoc nhac", chi thu tu la doi.
    assert all(n["duoc_nhac"] is False for n in ds), [n["ma"] for n in ds if n["duoc_nhac"]]


def test_link_code_lam_bang_code_duoc_nhac():
    ds = {n["ma"]: n for n in xh.goi_y_nguon("Qwen 3.8 vào top WebDev", "https://arena.ai/leaderboard/code", "", "")}
    assert ds["arena-code"]["duoc_nhac"] is True
    assert ds["arena-text"]["duoc_nhac"] is False


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
