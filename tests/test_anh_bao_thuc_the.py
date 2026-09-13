#!/usr/bin/env python3
"""Ảnh báo chí theo thực thể (og:image) — phần lọc thuần, không mạng.

Ông Chủ 12/09/2026 ném 7 link ảnh TSMC tìm bằng tay; tất cả là og:image của
bài báo VỀ TSMC, không phải bài cùng tin. Xem docstring press_entity_images.py.

Chạy:  venv/bin/python tests/test_anh_bao_thuc_the.py
"""
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import press_entity_images as bt                                 # noqa: E402


def test_link_bing_rss_giai_ra_url_that():
    l = "http://www.bing.com/news/apiclick.aspx?ref=FexRss&aid=&url=https%3a%2f%2f247wallst.com%2finvesting%2f2026%2f09%2f11%2ftsmc-x%2f&c=1&mkt=en-ww"
    assert bt.link_real(l) == "https://247wallst.com/investing/2026/09/11/tsmc-x/"
    assert bt.link_real("https://a.com/b") == "https://a.com/b"
    assert bt.link_real("") == ""


def test_loc_bai_bo_trung_bo_tong_hop_toi_da_moi_mien():
    items = [
        ("https://www.msn.com/en-us/x", "msn tong hop"),                       # BO_MIEN
        ("https://seekingalpha.com/news/1", "chan bot"),                       # BO_MIEN
        ("https://247wallst.com/a", "a"), ("https://247wallst.com/a", "a lap"),
        ("https://247wallst.com/b", "b"), ("https://247wallst.com/c", "c"),    # mien thu 3 -> bo
        ("https://www.engadget.com/x", "e"),
        ("ftp://x", "khong http"),
    ]
    ra = bt.filter_article(items)
    assert [b["url"] for b in ra] == ["https://247wallst.com/a", "https://247wallst.com/b", "https://www.engadget.com/x"]
    assert ra[0]["mien"] == "247wallst.com"
    assert bt.filter_article(items, bo_mien=("engadget.com",))[-1]["mien"] == "247wallst.com"


def test_og_tu_html_hai_thu_tu_thuoc_tinh_va_twitter():
    assert bt.og_from_html('<meta property="og:image" content="https://c/x.jpg">', "https://a/b") == "https://c/x.jpg"
    assert bt.og_from_html('<meta content="https://c/y.jpg" property="og:image"/>', "https://a/b") == "https://c/y.jpg"
    assert bt.og_from_html('<meta name="twitter:image" content="/img/z.jpg">', "https://a/b/c") == "https://a/img/z.jpg"
    assert bt.og_from_html("<html></html>", "https://a") is None


def test_ung_vien_dat_trang_bang_chinh_anh_de_qua_loc_ben_thu_ba():
    """og:image gần như luôn trên CDN khác miền bài; tai_loc coi khác miền là
    quảng cáo. Ứng viên phải mang trang=ảnh và giữ bài gốc ở `bai`."""
    src = inspect.getsource(bt._og)
    assert '"trang": im' in src and '"bai": u' in src


def test_tim_anh_them_goi_nguon_nay():
    src = (ROOT / "find_more_images.py").read_text(encoding="utf-8")
    assert "press_entity_images.press_entity_images(" in src


if __name__ == "__main__":
    ok = 0
    ten = [n for n in dir() if n.startswith("test_")]
    for n in ten:
        try:
            globals()[n]()
            ok += 1
        except AssertionError as e:
            print(f"FAIL {n}: {e}")
    print(f"{ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
