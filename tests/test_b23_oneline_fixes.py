#!/usr/bin/env python3
"""B23 (audit LOW-430, 30/09/2026): ba loi mot dong.

(a) `article_sources.web_search`: `re.match(...).group` khong kiem None (mypy union-attr).
(b) `dre_submit`: cong Lam lai so bia "stack" ("A3+A5") voi `cover_image` da ghi, ma ghi
    lai chi luu `cover.get("image")` = None cho bia stack -> giu nguyen cap anh cu van qua.
(c) tai ve khong tran dung luong: `arxiv_cover.download_pdf`, logo Commons cua image_brand.

Chay:  venv/bin/python tests/test_b23_oneline_fixes.py
"""
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import arxiv_cover                                           # noqa: E402
import article_sources                                       # noqa: E402
import dre_submit                                            # noqa: E402
import image_brand                                           # noqa: E402
import submit_common as nc                                   # noqa: E402


# ---- (a) -------------------------------------------------------------------------
def test_web_search_url_without_host_is_skipped_not_crash():
    html = ('<a class="result__a" href="http://">Khong host</a>'
            '<a class="result__a" href="https://example.org/a">Co host</a>')
    resp = mock.Mock(status_code=200, text=html)
    with mock.patch.object(article_sources.httpx, "post", return_value=resp), \
         mock.patch.object(article_sources.scan_common, "url_hide_whole", return_value=True):
        ra = article_sources.web_search("x")
    assert [r["outlet_url"] for r in ra] == ["https://example.org"], ra


# ---- (b) -------------------------------------------------------------------------
def test_cover_key_stack_and_single():
    assert dre_submit._cover_key({"image": "A2"}) == "A2"
    assert dre_submit._cover_key({"stack": ["A3", "A5"]}) == "A3+A5"
    assert dre_submit._cover_key({}) == ""


def test_redo_gate_catches_same_stack_cover():
    cu = nc.count_of_redo
    try:
        nc.count_of_redo = lambda _id: 1                     # Ong Chu vua bam Lam lai
        cover = {"stack": ["A3", "A5"], "hook": "Hook cu"}
        da_dung = {"cover_image": dre_submit._cover_key(cover), "hook": "Hook cu", "remakes": 0}
        loi = nc.check_redo_reused(da_dung, "bìa", dre_submit._cover_key(cover), "Hook moi",
                                   khoa_anh="cover_image", draft_id="x")
        assert len(loi) == 1 and "A3+A5" in loi[0], loi     # bia stack giu nguyen -> bi bat
        assert nc.check_redo_reused(da_dung, "bìa", "A3+A7", "Hook moi",
                                    khoa_anh="cover_image", draft_id="x") == []
    finally:
        nc.count_of_redo = cu


# ---- (c) -------------------------------------------------------------------------
class _Stream:
    """Gia `httpx.stream(...)`: tra dung so byte yeu cau, dem so chunk da doc."""
    def __init__(self, total, ctype="application/pdf", status=200, head=b"%PDF-"):
        self.total, self.status_code, self.headers, self.head = total, status, {"content-type": ctype}, head
        self.served = 0

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def iter_bytes(self, n):
        first = True
        while self.served < self.total:
            k = min(n, self.total - self.served)
            chunk = (self.head + b"0" * k)[:k] if first else b"0" * k
            first = False
            self.served += k
            yield chunk


def test_download_pdf_normal_file_unchanged():
    with mock.patch.object(arxiv_cover.httpx, "stream", return_value=_Stream(200_000)):
        data = arxiv_cover.download_pdf("https://arxiv.org/pdf/2501.00001")
    assert data is not None and len(data) == 200_000 and data[:5] == b"%PDF-"


def test_download_pdf_stops_over_cap():
    s = _Stream(arxiv_cover.PDF_MAX_BYTES * 3)
    with mock.patch.object(arxiv_cover.httpx, "stream", return_value=s):
        assert arxiv_cover.download_pdf("https://arxiv.org/pdf/2501.00001") is None
    assert s.served <= arxiv_cover.PDF_MAX_BYTES + 65536, "phai dung doc ngay khi vuot tran"


def test_download_pdf_still_rejects_non_pdf_and_bad_status():
    with mock.patch.object(arxiv_cover.httpx, "stream", return_value=_Stream(1000, "text/html", head=b"<html")):
        assert arxiv_cover.download_pdf("https://x.org/a") is None
    with mock.patch.object(arxiv_cover.httpx, "stream", return_value=_Stream(1000, status=404)):
        assert arxiv_cover.download_pdf("https://x.org/a") is None


def test_brand_logo_download_capped():
    import httpx
    from prepare.download_filter import DOWNLOAD_MAX_BYTE
    with mock.patch.object(httpx, "stream", return_value=_Stream(50_000, "image/png")):
        assert len(image_brand._download_capped("https://upload.wikimedia.org/a.png", 5)) == 50_000
    s = _Stream(DOWNLOAD_MAX_BYTE * 2, "image/png")
    with mock.patch.object(httpx, "stream", return_value=s):
        try:
            image_brand._download_capped("https://upload.wikimedia.org/a.png", 5)
        except ValueError as e:
            assert "MB" in str(e)
        else:
            raise AssertionError("tep vuot tran phai bi bo")
    assert s.served <= DOWNLOAD_MAX_BYTE + 65536


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
