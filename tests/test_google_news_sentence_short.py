#!/usr/bin/env python3
"""LOW-45 tiếp (13/09/2026) — Ông Chủ dán 5 URL ảnh thật tìm bằng tay trên Bing
(MSN/Sedaily×2/SCMP/CNBC) và hỏi *"thế những hình tìm theo cách thủ công này
bạn ko tự tìm ra được?"*.

Đo trên máy chủ: `article_sources.find()` chỉ hỏi Google News DUY NHẤT MỘT LẦN bằng
headline ĐẦY ĐỦ của bài gốc (`title_find`, vd "Kimi-maker Moonshot AI targets
$2B in annual revenue") — cùng câu, cùng địa chỉ máy chủ, KHÔNG khoá `hl`/`gl`,
chỉ ra vài miền. Hỏi lại bằng câu NGẮN mà chính `_query_bing` đã sinh ra cho
Bing từ lâu ("Kimi Moonshot AI", "Kimi maker Moonshot AI") ra tới 18-19 miền,
gồm đúng SCMP/Bloomberg/CNBC/Reuters — y hệt các nguồn Ông Chủ tìm thấy. Cùng
loại lỗi ĐÃ BIẾT ở Bing (`_query_bing` docstring: "truy vấn đầy đủ -> 1 bài")
nhưng chưa từng áp dụng sang Google News.

Chạy:  venv/bin/python tests/test_google_news_sentence_short.py
"""
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import article_sources                                              # noqa: E402


class _RSS:
    def __init__(self, sources):
        rows = "".join(f'<item><link>https://x/{i}</link><title>t{i}</title>'
                       f'<source url="{u}">S</source></item>'
                       for i, u in enumerate(sources))
        self.content = f"<rss><channel>{rows}</channel></rss>".encode()


def test_find_no_only_ask_headline_bottom_enough():
    """Đường `find()` đi qua phải gọi `_query_bing` để sinh thêm câu ngắn cho
    GNEWS, không chỉ hỏi đúng một lần bằng `ten` (headline đầy đủ).

    Đọc theo CHUỖI GỌI chứ không cắt thân `find` từ tệp (LOW-309): vòng hỏi
    Google News đã tách ra `_gnews_item`, và bản cũ cắt chuỗi từ `def find(` tới
    `def main(` nên nó đỏ dù đường chạy không đổi — một phép đo sai chỗ."""
    import inspect
    assert "_gnews_item(" in inspect.getsource(article_sources.find), "find() không còn gọi vòng GNEWS"
    assert "_query_bing(ten)" in inspect.getsource(article_sources._gnews_item), \
        "vòng GNEWS phải thử thêm câu ngắn (_query_bing), không chỉ headline đầy đủ"


def test_sentence_short_merge_extra_domain_no_has_cell_sentence_bottom_enough():
    """Câu đầy đủ ra 2 miền; một câu ngắn (được `_query_bing` sinh ra) ra
    thêm SCMP/Bloomberg — `trang` cuối cùng phải gồm cả hai, không chỉ câu đầu."""
    goi = []

    def _tai_gia(url, timeout=20):
        goi.append(url)
        if "n=1" not in url and len(goi) == 1:              # cau day du: it mien
            return _RSS(["https://techcrunch.com", "https://startupfortune.com"])
        return _RSS(["https://techcrunch.com", "https://www.scmp.com",
                     "https://www.bloomberg.com"])            # cau ngan: nhieu mien hon

    with mock.patch.object(article_sources, "_download", side_effect=_tai_gia), \
         mock.patch.object(article_sources, "title_find", return_value="Headline day du cua bai goc ve X"), \
         mock.patch.object(article_sources, "_query_bing", return_value=["X ngan"]), \
         mock.patch.object(article_sources, "resolve_code_gnews", return_value=None), \
         mock.patch("httpx.get", side_effect=lambda *a, **k: (_ for _ in ()).throw(OSError("khong mang"))):
        article_sources.find("Headline day du cua bai goc ve X", "https://baigoc.example/x", so=4)

    # `_trong_feed` (khong co RSS that trong test, httpx.get bi chan) se khong
    # ra bai nao ca — nen chi kiem duoc so LAN goi _tai: it nhat 2 (headline
    # day du + it nhat 1 cau ngan), khong kiem duoc noi dung `trang` cuoi cung.
    assert len(goi) >= 2, goi


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
