#!/usr/bin/env python3
"""LOW-169: article_sources.title_find() từng khớp nhầm headline Google News
khi og:title/RSS đều hỏng (trang chặn bot) và tiêu đề Việt chỉ rút ra được 2 từ
khoá chung (tên nước + số trần) — "Malaysia 385" khớp bừa với một bài xe hơi
"iCaur 03" có cả "Malaysia" và "385" (385 Nm lực xoắn) hoàn toàn ngẫu nhiên.

_title_slug() thêm một nấc trước khi rơi về nhánh yếu đó: rút tiêu đề tiếng
Anh trực tiếp từ slug URL của chính bài gốc (đa số CMS tin tức đặt slug =
headline nối bằng gạch ngang), vừa tiếng Anh vừa đặc trưng hơn nhiều, không
đánh đổi bằng cách bỏ tìm kiếm (Ông Chủ 15/09/2026: luôn tìm bằng tiếng Anh,
không bao giờ thiếu nguồn).

Chạy: venv/bin/python tests/test_article_source_title.py
"""
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import article_sources as src  # noqa: E402

REAL_HEADLINE_URL = (
    "https://www.businesstoday.com.my/2026/09/14/malaysia-records-rm385-7-"
    "billion-in-data-centre-investments-sim-calls-for-broader-economic-impact/"
)


def test_title_slug_extracts_real_headline_from_url():
    got = src._title_slug(REAL_HEADLINE_URL)
    assert got.startswith("malaysia records rm385"), got
    assert "data centre investments" in got, got


def test_title_slug_rejects_short_or_numeric_last_segment():
    # ID số trần cuối đường dẫn, không phải slug — thử lùi về đoạn trước cũng
    # không đủ 4 từ chữ nên phải trả rỗng, KHÔNG được đoán liều.
    assert src._title_slug("https://example.com/news/2026/09/14/482913") == ""
    assert src._title_slug("https://example.com/") == ""


def test_title_page_falls_back_to_slug_when_og_title_and_rss_fail():
    """Mô phỏng đúng ca thật: trang trả 403 (chặn bot) nên không có og:title,
    RSS toà soạn cũng không khớp — _title_page() phải rơi tiếp về slug URL
    thay vì trả rỗng (rỗng = mất nguồn, đúng thứ Ông Chủ không muốn)."""
    fake_403 = mock.Mock(status_code=403, text="Just a moment...")
    with mock.patch.object(src.httpx, "get", return_value=fake_403), \
         mock.patch.object(src, "_title_rss", return_value=""):
        got = src._title_page(REAL_HEADLINE_URL)
    assert got.startswith("malaysia records rm385"), got


def test_title_page_prefers_rss_over_slug():
    """RSS (tiêu đề thật từ toà soạn) vẫn phải thắng slug (chỉ là suy ra) khi
    cả hai đều có."""
    fake_403 = mock.Mock(status_code=403, text="Just a moment...")
    with mock.patch.object(src.httpx, "get", return_value=fake_403), \
         mock.patch.object(src, "_title_rss", return_value="Real RSS headline text"):
        got = src._title_page(REAL_HEADLINE_URL)
    assert got == "Real RSS headline text", got


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bắt cả Exception, luôn in N/M (E-r2-2)
    chay_tat_ca(globals())
