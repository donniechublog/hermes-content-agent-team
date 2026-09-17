#!/usr/bin/env python3
"""LOW-45 tiếp (13/09/2026) — Ông Chủ: *"bạn đâu cần tìm đúng tin về việc raise,
chỉ cần search tin tức theo từ khóa kimi / moonshot / kimi k3... là cũng đầy
article có ảnh dùng được mà, đã là ảnh khái niệm thì cần gì phải cầu kỳ?"*

Đo thật 13/09/2026: Moonshot AI có QID Wikidata (`Q130270266`) nhưng RỖNG (0 ảnh
công ty/logo/founder) — `vendor_images`/`image_wikidata` đều ra 0, và trước bản vá này
`_round_brand` bỏ cuộc luôn, rơi thẳng xuống ảnh khái niệm chung chung (cờ
Trung Quốc). Hai việc:

  1. `article_sources.report_about_keyword`: tìm báo THẬT theo TỪ KHOÁ (tên hãng), KHÔNG đòi
     "cùng một sự kiện" như `other_outlets_bing` — chỉ cần bài NÓI VỀ từ khoá đó.
  2. `_round_brand` gọi hàm này khi Commons/Wikidata của một hãng RỖNG, quét
     ảnh từ các báo tìm được (`browser_pass`, đã sửa LOW-45 phần 1 nên không vớ
     nhầm `<figure>` là chart) thay vì bỏ cuộc.

Chạy:  venv/bin/python tests/test_report_about_keyword.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import article_sources                                              # noqa: E402
from prepare import fallback_rounds                                  # noqa: E402
import state_paths                                            # noqa: E402
sys.path.insert(0, str(ROOT / "tests"))
from test_spec_dre import _ve                                 # noqa: E402


class _RSS:
    def __init__(self, items, ngay="Fri, 12 Sep 2026 00:00:00 GMT"):
        rows = "".join(f"<item><link>{u}</link><title>{t}</title>"
                       f"<pubDate>{ngay}</pubDate></item>"
                       for u, t in items)
        self.content = f"<rss><channel>{rows}</channel></rss>".encode()

    def raise_for_status(self):
        pass


def test_report_about_keyword_no_change_same_event():
    """Khác `other_outlets_bing` (đòi khớp MỘT sự kiện gốc qua `same_story(a, b)` — hai
    tham số): thân hàm không gọi `same_story(`, chỉ dùng `story_tokens(` (tách từ,
    một tham số) để so với chính từ khoá."""
    import re
    src = (ROOT / "article_sources.py").read_text(encoding="utf-8")
    than = src[src.index("def report_about_keyword("):src.index("\ndef find(")]
    assert not re.search(r"(?<!tu_)\bcung_tin\(", than), \
        "report_about_keyword không được đòi 'cùng một sự kiện' (same_story)"
    assert "story_tokens(tu_khoa)" in than


def test_report_about_keyword_filter_by_keyword_no_by_event_original():
    """Bài THIẾU từ khoá bị loại; bài CÓ đủ từ khoá (dù nói chuyện khác hẳn sự
    kiện gì) vẫn được nhận — đúng tinh thần "chỉ cần liên quan tới hãng"."""
    items = [
        ("https://a.example/1", "Moonshot AI opens new office in Singapore"),
        ("https://b.example/2", "Kimi Räikkönen wins another F1 podium"),  # khong co "moonshot"
        ("https://c.example/3", "Moonshot AI hires new head of safety team"),
    ]

    def _tai_gia(url, timeout=20):
        return _RSS(items)

    def _head_gia(url, headers=None, timeout=None, follow_redirects=None):
        import types
        return types.SimpleNamespace(status_code=200, url=url)

    with mock.patch.object(article_sources, "_download", side_effect=_tai_gia), \
         mock.patch("httpx.head", side_effect=_head_gia), \
         mock.patch("scan_common.url_hide_whole", return_value=True):
        ra = article_sources.report_about_keyword("Moonshot AI", so=6)

    mien = {r["outlet_url"] for r in ra}
    assert mien == {"https://a.example", "https://c.example"}, ra


def test_report_about_keyword_type_report_vietnamese():
    """Đo thật 13/09/2026 (test thử Kite trên tin Anthropic/Moonshot): query
    "Anthropic" — dù chỉ là tên hãng tiếng Anh, không có dấu — vẫn khiến Bing
    News trả về CẢ báo tiếng Việt (cafebiz.vn, thanhnien.vn...) vì đủ từ khoá
    khớp tiêu đề. `has_vietnamese(tu_khoa)` ở đầu hàm chỉ chặn được TỪ KHOÁ đầu
    vào — không chặn được đây. IMAGE_RULES §1.2d: "tìm kiếm bằng tiếng Anh hoặc
    tiếng Trung, tuyệt đối ko được dùng ngôn ngữ khác" — phải lọc trên chính
    TIÊU ĐỀ bài trả về."""
    items = [
        ("https://en.example/1", "Anthropic accuses Moonshot of routing requests to Claude"),
        ("https://vn.example/2", "Anthropic tố Moonshot định tuyến yêu cầu qua Claude"),
    ]

    def _tai_gia(url, timeout=20):
        return _RSS(items)

    def _head_gia(url, headers=None, timeout=None, follow_redirects=None):
        import types
        return types.SimpleNamespace(status_code=200, url=url)

    with mock.patch.object(article_sources, "_download", side_effect=_tai_gia), \
         mock.patch("httpx.head", side_effect=_head_gia), \
         mock.patch("scan_common.url_hide_whole", return_value=True):
        ra = article_sources.report_about_keyword("Anthropic", so=6)

    assert {r["outlet_url"] for r in ra} == {"https://en.example"}, ra


def test_report_about_keyword_no_limit_time():
    """IMAGE_RULES §1.2d (13/09/2026): "được tìm không giới hạn thời gian, sự
    kiện". Một bài rất CŨ (2019) về đúng từ khoá vẫn phải được nhận — mặc định
    `ngay=None` nghĩa là KHÔNG lọc theo ngày (khác `other_outlets_bing`, vẫn lọc
    ngày vì nó tìm 'báo khác CÙNG một sự kiện' — sự kiện thì có mốc thời gian
    thật, khác hẳn 'ảnh minh hoạ về hãng' thì không)."""
    items = [("https://cu.example/1", "Moonshot AI office photos from 2019")]

    def _tai_gia(url, timeout=20):
        return _RSS(items, ngay="Tue, 01 Jan 2019 00:00:00 GMT")

    def _head_gia(url, headers=None, timeout=None, follow_redirects=None):
        import types
        return types.SimpleNamespace(status_code=200, url=url)

    with mock.patch.object(article_sources, "_download", side_effect=_tai_gia), \
         mock.patch("httpx.head", side_effect=_head_gia), \
         mock.patch("scan_common.url_hide_whole", return_value=True):
        ra = article_sources.report_about_keyword("Moonshot AI", so=6)

    assert {r["outlet_url"] for r in ra} == {"https://cu.example"}, ra


def test_rank_empty_then_find_report_by_keyword_scan_image():
    """`_round_brand`: Commons/Wikidata rỗng cho một hãng -> gọi
    `report_about_keyword` rồi `browser_pass`, ứng viên tìm được gắn `brand_match`
    và cuối cùng có mặt trong `dung_duoc` (fail trên code cũ: hãng rỗng thì
    dừng, 0 ảnh, dù có báo thật ngoài kia)."""
    with tempfile.TemporaryDirectory() as d:
        wd = Path(d)
        (wd / state_paths.ORIGINAL_DIR).mkdir()
        ung_vien = {"image_url": "https://x/photo.jpg", "alt": "", "og": False, "source": "browser",
                   "page_url": "https://baomoi.example/moonshot", "w": 1600, "h": 1000, "score": 45}

        def tai_va_loc_gia(cands, wd2):
            ra = []
            for i, c in enumerate(cands, 1):
                tam = wd2 / f"A{i}.png"
                tam.parent.mkdir(parents=True, exist_ok=True)
                _ve(c["w"], c["h"]).save(tam)     # anh CO VAN, khong bi doc nham la chart phang
                c2 = dict(c); c2["original_path"] = str(tam); c2["file_path"] = str(tam)
                ra.append(c2)
            return ra

        import os
        import env_load
        import image_rules_ethan
        # LOW-127: test nay kiem luong TIM ANH QUA BAO, khong kiem vision. May chu co
        # secret.*.env that -> env_load.load() nap lai OPENAI_API_KEY -> vision THAT cham
        # anh nhieu tu ve la khong lien quan -> anh khong vao dung_duoc (do tren may chu).
        # Tat vision dung nhu tren CI: bo key va chan nap tep secret.
        env_khong_key = {k: v for k, v in os.environ.items() if k != "OPENAI_API_KEY"}
        with mock.patch.dict("os.environ", env_khong_key, clear=True), \
             mock.patch.object(env_load, "load", lambda *a, **k: None), \
             mock.patch("image_brand.vendors_in_story",
                        return_value=[{"company": "Moonshot AI", "key": "moonshot"}]), \
             mock.patch("image_brand.vendor_images", return_value=[]), \
             mock.patch.object(article_sources, "report_about_keyword",
                              return_value=[{"url": "https://baomoi.example/moonshot",
                                            "kind": "other_outlet", "title": "Moonshot AI raises",
                                            "outlet_url": "https://baomoi.example"}]), \
             mock.patch.object(fallback_rounds, "browser_pass",
                              return_value={"cands": [ung_vien], "title_en": "", "article_text": "",
                                           "extra_pages": []}), \
             mock.patch.object(fallback_rounds, "download_and_filter", side_effect=tai_va_loc_gia), \
             mock.patch.object(image_rules_ethan, "count_faces", return_value=0), \
             mock.patch.object(image_rules_ethan, "is_chart", return_value=(False, "ảnh chụp thật")), \
             mock.patch.object(image_rules_ethan, "measure_chart_signal", return_value=(0.1, 500)), \
             mock.patch.object(fallback_rounds, "_ranking_context_edge", return_value=None):  # trung mang that
            anh, dung_duoc, _ = fallback_rounds._round_brand([], "Moonshot AI raises funding", "", wd)

    assert len(anh) == 1, anh
    a = anh[0]
    assert a.get("brand_match", {}).get("company") == "Moonshot AI", a
    assert a in dung_duoc, "ảnh tìm qua báo phải qua được đến dùng_được (đủ quan/không mặt vô danh v.v.)"


def test_find_report_run_parallel_including_when_commons_has_image():
    """IMAGE_RULES §1.2d (13/09/2026, Ông Chủ chốt nguyên tắc nguồn): tìm báo theo
    từ khoá KHÔNG còn là phương án cuối khi Commons rỗng — chạy SONG SONG với
    Commons cho MỌI hãng, kể cả khi Commons ĐÃ có ảnh. Fail trên code cũ (nhánh
    `if not cands_h`): `report_about_keyword` không được gọi vì Commons đã có 1 ảnh."""
    with tempfile.TemporaryDirectory() as d:
        wd = Path(d); (wd / state_paths.ORIGINAL_DIR).mkdir()
        anh_commons = {"image_url": "https://commons.example/hq.jpg", "alt": "", "og": False,
                      "source": "brand", "w": 1600, "h": 1000, "score": 28,
                      "brand_match": {"company": "Moonshot AI", "key": "moonshot", "kind": "photo",
                                     "keyword": "tru so"}}
        goi = {"tim_bao": False}

        def bao_ve_tu_khoa_gia(hang, so=6):
            goi["tim_bao"] = True
            return []

        with mock.patch("image_brand.vendors_in_story",
                        return_value=[{"company": "Moonshot AI", "key": "moonshot"}]), \
             mock.patch("image_brand.vendor_images", return_value=[anh_commons]), \
             mock.patch.object(article_sources, "report_about_keyword", side_effect=bao_ve_tu_khoa_gia), \
             mock.patch.object(fallback_rounds, "_ranking_context_edge", return_value=None):
            fallback_rounds._round_brand([], "Moonshot AI raises funding", "", wd)

    assert goi["tim_bao"], "tìm báo theo từ khoá phải chạy dù Commons đã có ảnh (không còn là phương án cuối)"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
