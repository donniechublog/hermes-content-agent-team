#!/usr/bin/env python3
"""LOW-298 (20/09/2026): `social_fetch.py` dùng `re` mà không `import re`.

Commit 07/09 gỡ `import re` lúc tệp chưa dùng tới; commit 08/09 thêm 6 chỗ `re.*`
mà không import lại. Đo 20/09 trên bản đang chạy:
  * `normalize_url` văng NameError với MỌI link Facebook (dòng `re.match(r"^/share/")`
    chạy trước cả khi biết link có phải `/share/` không) — X và Instagram thì qua.
  * `--download` văng NameError ở bước đặt tên thư mục (`re.sub`) với MỌI post có
    media, cả ba nền tảng, TRƯỚC khi in JSON. `social_post.read(..., tai_ve=...)` của
    engine ảnh đi đúng đường này nên "ảnh của chính post" âm thầm không bao giờ ra.
CI không thấy vì bước pyflakes chỉ liệt kê một thư mục skill, không phủ `hermes/`.

Các test dưới gọi THẬT hai đường đó, không giả `re`, không ra mạng.

Chạy:  venv/bin/python tests/test_social_fetch.py
"""
import contextlib
import importlib.util
import io
import json
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "hermes" / "skills" / "social-crawl" / "scripts" / "social_fetch.py"

_spec = importlib.util.spec_from_file_location("social_fetch", SCRIPT)
social_fetch = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(social_fetch)

NUMERIC = "https://www.facebook.com/somepage/posts/1234567890"


def test_facebook_numeric_permalink_passes_through():
    with mock.patch.object(social_fetch, "_fetch_html") as fetch:
        assert social_fetch.normalize_url(NUMERIC, "facebook") == NUMERIC
    fetch.assert_not_called()                      # khong phai /share/ thi khong tai trang


def test_facebook_slug_permalink_becomes_numeric():
    slug = "https://www.facebook.com/somepage/posts/co-nhung-ngay-2026-1234567890/"
    assert social_fetch.normalize_url(slug, "facebook") == NUMERIC
    # nhieu cum so: lay cum CUOI (id bai), khong lay cum dau
    two = "https://www.facebook.com/somepage/posts/ky-niem-20260908-1234567890"
    assert social_fetch.normalize_url(two, "facebook") == NUMERIC


def test_facebook_share_link_reads_canonical_then_og_url():
    share = "https://www.facebook.com/share/p/AbCdEf123/"
    canonical = '<link rel="canonical" data-x="1" href="https://www.facebook.com/somepage/posts/ten-bai-1234567890/">'
    og_url = '<meta property="og:url" data-x="1" content="https://www.facebook.com/somepage/posts/1234567890">'
    for html in (canonical, og_url):
        with mock.patch.object(social_fetch, "_fetch_html", return_value=html) as fetch:
            assert social_fetch.normalize_url(share, "facebook") == NUMERIC, html
        fetch.assert_called_once_with(share)
    # trang share khong co the nao doc duoc -> tra nguyen link, de endpoint noi loi cuoi
    with mock.patch.object(social_fetch, "_fetch_html", return_value="<html></html>"):
        assert social_fetch.normalize_url(share, "facebook") == share


def test_other_platforms_are_returned_untouched():
    with mock.patch.object(social_fetch, "_fetch_html") as fetch:
        for url, platform in (("https://x.com/a/status/1", "x"),
                              ("https://www.instagram.com/p/ABC/", "instagram")):
            assert social_fetch.normalize_url(url, platform) == url
    fetch.assert_not_called()


def _run_main(url, data, download):
    """Chay main() voi crawl + download_media gia; tra (dest da chon, JSON in ra stdout)."""
    out = io.StringIO()
    with mock.patch.object(social_fetch, "crawl", return_value=data), \
            mock.patch.object(social_fetch, "download_media") as download_media, \
            mock.patch.object(sys, "argv", ["social_fetch.py", url, "--download", download]), \
            contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        social_fetch.main()
    dest = download_media.call_args.args[1] if download_media.called else None
    return dest, json.loads(out.getvalue())


def test_download_names_folder_from_author_on_all_three_platforms():
    media = [{"url": "https://cdn.example/1.jpg", "type": "photo"}]
    cases = [
        # X: author nam trong tweet, handle co ky tu cam trong ten thu muc
        ("https://x.com/open/status/111",
         {"tweet": {"id": "111", "media": media, "author": {"handle": "open/design"}}},
         Path("downloads/open-design-111")),
        # Instagram: author la object
        ("https://www.instagram.com/p/ABC/",
         {"author": {"handle": "nasa"}, "shortcode": "ABC", "media": media},
         Path("downloads/nasa-ABC")),
        # Facebook: author la CHUOI ten (khong phai object), co dau va khoang trang
        (NUMERIC,
         {"author": "Nguyễn Văn A", "postId": "1234567890", "media": media},
         Path("downloads/Nguyễn-Văn-A-1234567890")),
    ]
    for url, data, expected in cases:
        dest, printed = _run_main(url, data, "-")
        assert dest == expected, (url, dest)
        assert printed == data, "JSON phai duoc in ra SAU khi tai, khong chet giua chung"


def test_download_to_explicit_folder_and_no_media():
    media = [{"url": "https://cdn.example/1.jpg", "type": "photo"}]
    dest, _ = _run_main("https://www.instagram.com/p/ABC/",
                        {"author": {"handle": "nasa"}, "shortcode": "ABC", "media": media},
                        "/tmp/low298-out")
    assert dest == Path("/tmp/low298-out"), dest
    dest, printed = _run_main("https://x.com/a/status/1", {"tweet": {"id": "1", "media": []}}, "-")
    assert dest is None and printed == {"tweet": {"id": "1", "media": []}}


def test_ci_lints_the_whole_hermes_tree():
    """Buoc pyflakes cua CI phai phu CA thu muc `hermes`, khong liet ke tung skill —
    chinh danh sach liet ke la cho de lot loi nay suot 12 ngay."""
    ci = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    line = next(ln for ln in ci.splitlines() if "-m pyflakes" in ln and ln.strip().startswith("run:"))
    assert "hermes" in line.split(), f"pyflakes khong phu ca thu muc hermes: {line.strip()}"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
