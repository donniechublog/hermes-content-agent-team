#!/usr/bin/env python3
"""LOW-442 (30/09/2026) — ảnh báo chí theo thực thể ghi CDN thay vì trang báo.

`press_entity_images._og` cố ý để `page_url` = chính ảnh (og:image nằm trên CDN
khác miền bài, cổng "host bên thứ ba" của download_filter sẽ coi là quảng cáo)
và giữ bài gốc ở `article_url`. Nhưng `download_and_filter` dựng mục ảnh chỉ từ
`page_url` — manifest/handoff/bảng đen ghi "via image.cnbcfm.com" thay vì cnbc.com.

Ứng viên đi từ CHÍNH `_og` (HTTP giả, không mạng) qua `download_and_filter` (tải
giả) để khoá cả hai đầu cùng lúc.

Chạy:  venv/bin/python tests/test_low442_press_article_page.py
"""
import io
import random
import sys
import tempfile
from pathlib import Path
from unittest import mock

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import press_entity_images                                    # noqa: E402
from prepare import download_filter                           # noqa: E402

ARTICLE = "https://www.cnbc.com/2026/09/29/tsmc-earnings.html"
IMAGE = "https://image.cnbcfm.com/api/v1/image/108000000-tsmc.jpg"


def _png(seed: int) -> bytes:
    w, h = 1000, 800
    buf = io.BytesIO()
    Image.frombytes("RGB", (w, h), random.Random(seed).randbytes(w * h * 3)).save(buf, "PNG")
    return buf.getvalue()


def _quiet(fn):
    old, sys.stderr = sys.stderr, io.StringIO()
    try:
        return fn()
    finally:
        sys.stderr = old


def _press_candidate() -> dict:
    html = f'<html><head><meta property="og:image" content="{IMAGE}"></head></html>'
    resp = mock.Mock(status_code=200, text=html, url=ARTICLE)
    with mock.patch("httpx.get", return_value=resp):
        c = press_entity_images._og({"url": ARTICLE, "title": "TSMC earnings", "domain": "cnbc.com"})
    assert c and c["image_url"] == IMAGE and c["article_url"] == ARTICLE, c
    return c


def _download(cands: list, remote: dict) -> list:
    with tempfile.TemporaryDirectory() as t, \
         mock.patch.object(download_filter, "_download_bytes", side_effect=lambda u: remote.get(u)):
        return _quiet(lambda: download_filter.download_and_filter(cands, Path(t)))


def test_press_image_keeps_article_page_and_domain():
    ra = _download([_press_candidate()], {IMAGE: _png(1)})
    assert len(ra) == 1, "og:image bao chi bi loai (cong ben thu ba?)"
    assert ra[0]["url"] == IMAGE
    assert ra[0]["page_url"] == ARTICLE, ra[0]["page_url"]
    assert ra[0]["domain"] == "cnbc.com", ra[0]["domain"]


def test_candidate_without_article_url_unchanged():
    """Nguồn thường (browser, tìm ảnh web): page_url/domain như cũ."""
    web = {"image_url": "https://cdn.example.org/x.jpg", "page_url": "https://cdn.example.org/x.jpg",
           "source": "web_bing", "alt": "", "score": 40}
    news = {"image_url": "https://news.example.com/img/a.jpg", "page_url": "https://news.example.com/story",
            "source": "browser", "alt": "", "score": 50}
    ra = _download([news, web], {web["image_url"]: _png(2), news["image_url"]: _png(3)})
    by_url = {a["url"]: a for a in ra}
    assert by_url[news["image_url"]]["page_url"] == "https://news.example.com/story"
    assert by_url[news["image_url"]]["domain"] == "news.example.com"
    assert by_url[web["image_url"]]["page_url"] == web["image_url"]
    assert by_url[web["image_url"]]["domain"] == "cdn.example.org"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
