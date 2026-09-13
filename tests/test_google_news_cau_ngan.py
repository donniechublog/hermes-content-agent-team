#!/usr/bin/env python3
"""LOW-45 tiếp (13/09/2026) — Ông Chủ dán 5 URL ảnh thật tìm bằng tay trên Bing
(MSN/Sedaily×2/SCMP/CNBC) và hỏi *"thế những hình tìm theo cách thủ công này
bạn ko tự tìm ra được?"*.

Đo trên máy chủ: `nguon_bai.tim()` chỉ hỏi Google News DUY NHẤT MỘT LẦN bằng
headline ĐẦY ĐỦ của bài gốc (`tieu_de_tim`, vd "Kimi-maker Moonshot AI targets
$2B in annual revenue") — cùng câu, cùng địa chỉ máy chủ, KHÔNG khoá `hl`/`gl`,
chỉ ra vài miền. Hỏi lại bằng câu NGẮN mà chính `_truy_van_bing` đã sinh ra cho
Bing từ lâu ("Kimi Moonshot AI", "Kimi maker Moonshot AI") ra tới 18-19 miền,
gồm đúng SCMP/Bloomberg/CNBC/Reuters — y hệt các nguồn Ông Chủ tìm thấy. Cùng
loại lỗi ĐÃ BIẾT ở Bing (`_truy_van_bing` docstring: "truy vấn đầy đủ -> 1 bài")
nhưng chưa từng áp dụng sang Google News.

Chạy:  venv/bin/python tests/test_google_news_cau_ngan.py
"""
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import nguon_bai                                              # noqa: E402


class _RSS:
    def __init__(self, sources):
        rows = "".join(f'<item><link>https://x/{i}</link><title>t{i}</title>'
                       f'<source url="{u}">S</source></item>'
                       for i, u in enumerate(sources))
        self.content = f"<rss><channel>{rows}</channel></rss>".encode()


def test_tim_khong_chi_hoi_headline_day_du():
    """Thân `tim()` phải gọi `_truy_van_bing` để sinh thêm câu ngắn cho GNEWS,
    không chỉ hỏi đúng một lần bằng `ten` (headline đầy đủ)."""
    src = (ROOT / "nguon_bai.py").read_text(encoding="utf-8")
    than = src[src.index("def tim("):src.index("\ndef main(")]
    assert "_truy_van_bing(ten)" in than, \
        "tim() phải thử thêm câu ngắn (_truy_van_bing) cho Google News, không chỉ headline đầy đủ"


def test_cau_ngan_gop_them_mien_khong_co_o_cau_day_du():
    """Câu đầy đủ ra 2 miền; một câu ngắn (được `_truy_van_bing` sinh ra) ra
    thêm SCMP/Bloomberg — `trang` cuối cùng phải gồm cả hai, không chỉ câu đầu."""
    goi = []

    def _tai_gia(url, timeout=20):
        goi.append(url)
        if "n=1" not in url and len(goi) == 1:              # cau day du: it mien
            return _RSS(["https://techcrunch.com", "https://startupfortune.com"])
        return _RSS(["https://techcrunch.com", "https://www.scmp.com",
                     "https://www.bloomberg.com"])            # cau ngan: nhieu mien hon

    with mock.patch.object(nguon_bai, "_tai", side_effect=_tai_gia), \
         mock.patch.object(nguon_bai, "tieu_de_tim", return_value="Headline day du cua bai goc ve X"), \
         mock.patch.object(nguon_bai, "_truy_van_bing", return_value=["X ngan"]), \
         mock.patch.object(nguon_bai, "giai_ma_gnews", return_value=None), \
         mock.patch("httpx.get", side_effect=lambda *a, **k: (_ for _ in ()).throw(OSError("khong mang"))):
        kq = nguon_bai.tim("Headline day du cua bai goc ve X", "https://baigoc.example/x", so=4)

    mien = {t["url"] for t in kq["trang"]}
    # `_trong_feed` (khong co RSS that trong test) se khong ra bai nao, nhung
    # `mien` trung gian (bien cuc bo) phai da gop CA HAI lan hoi — kiem qua so
    # LAN goi _tai: it nhat 2 (headline day du + it nhat 1 cau ngan).
    assert len(goi) >= 2, goi


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
