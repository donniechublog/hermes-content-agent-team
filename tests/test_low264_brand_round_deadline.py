#!/usr/bin/env python3
"""LOW-264 (bổ sung, 20/09/2026, Ông Chủ: "thêm giới hạn cho thời gian tìm ảnh").

Vòng ảnh thương hiệu không có hạn giờ nào: một hãng = 9 request tuần tự, mỗi
request timeout 20 s, tối đa 3 hãng — Wikimedia treo thì một draft giữ một slot
chuẩn bị tới ~540 s (suy từ code). Hạn MỀM `image_brand.BRAND_ROUND_SECONDS`: sau
hạn không bắt đầu bước mạng mới, giữ ứng viên đã có; `_round_brand` đặt/gỡ hạn và
in tổng giây (log trước đây không có mốc giờ).

Chạy:  venv/bin/python tests/test_low264_brand_round_deadline.py
"""
import io
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_brand as th                                     # noqa: E402
from prepare import fallback_rounds                            # noqa: E402


def _stderr(fn):
    old, sys.stderr = sys.stderr, io.StringIO()
    try:
        result = fn()
        return result, sys.stderr.getvalue()
    finally:
        sys.stderr = old


def test_no_deadline_means_no_limit_and_full_timeout():
    th.clear_deadline()
    assert th.time_left() is None and not th.deadline_passed() and not th.deadline_passed(30)
    assert th.cap_timeout(20) == 20


def test_deadline_caps_request_timeout_and_reports_passed():
    th.start_deadline(5)
    try:
        assert 0 < th.time_left() <= 5
        assert th.cap_timeout(20) <= 5.0
        assert th.deadline_passed(30)            # con < 30 s: buoc can browser khong bat dau
        assert not th.deadline_passed()          # nhung chua het han
    finally:
        th.clear_deadline()
    th.start_deadline(0)
    try:
        assert th.deadline_passed()
        assert th.cap_timeout(20) == 1.0         # toi thieu 1 s, khong bao gio 0
    finally:
        th.clear_deadline()


def test_ask_api_after_deadline_makes_no_request_and_logs_once():
    th.start_deadline(0)
    try:
        with mock.patch("httpx.get", side_effect=AssertionError("het gio ma van goi mang")):
            (a, b), err = _stderr(lambda: (th._ask_api("https://www.wikidata.org/w/api.php", action="x"),
                                           th._ask_api("https://www.wikidata.org/w/api.php", action="y")))
        assert a is None and b is None
        assert err.count("HET GIO") == 1, err     # mot dong DUY NHAT, khong spam
    finally:
        th.clear_deadline()


def test_vendor_images_after_deadline_skips_commons_and_wikidata():
    th.start_deadline(0)
    try:
        with mock.patch("scan_common.ask_commons", side_effect=AssertionError("goi Commons sau han")), \
             mock.patch.object(th, "image_wikidata", side_effect=AssertionError("goi Wikidata sau han")):
            ra, err = _stderr(lambda: th.vendor_images({"key": "microsoft", "company": "Microsoft"}))
        assert ra == [] and "HET GIO" in err, (ra, err)
    finally:
        th.clear_deadline()


def test_vendor_images_keeps_candidates_found_before_deadline():
    page = {"1": {"title": "File:Microsoft Headquarters A.jpg",
                  "imageinfo": [{"width": 4000, "height": 3000, "mime": "image/jpeg", "thumburl": "https://u/a.jpg"}]}}

    def commons(cau, **kw):
        th.start_deadline(0)                      # het gio ngay sau cau hoi dau tien
        return page

    th.clear_deadline()
    try:
        with mock.patch("scan_common.ask_commons", side_effect=commons), \
             mock.patch.object(th, "image_wikidata", side_effect=AssertionError("goi Wikidata sau han")):
            ra, _ = _stderr(lambda: th.vendor_images({"key": "microsoft", "company": "Microsoft"}))
        assert len(ra) == 1 and ra[0]["alt"].endswith("Microsoft Headquarters A.jpg"), ra
    finally:
        th.clear_deadline()


def test_round_brand_stops_starting_new_vendors_after_deadline_and_clears_it():
    vendors = [{"key": k, "company": k.title()} for k in ("openai", "anthropic", "google deepmind")]
    calls = {"vendor_images": [], "report": [], "ranking": []}

    def vendor_images(hang, wd=None):
        calls["vendor_images"].append(hang["key"])
        time.sleep(0.15)                          # vuot han mem (0.05 s)
        return []

    with tempfile.TemporaryDirectory() as d, \
         mock.patch.object(th, "BRAND_ROUND_SECONDS", 0.05), \
         mock.patch("image_brand.vendors_in_story", return_value=vendors), \
         mock.patch("image_brand.vendor_images", side_effect=vendor_images), \
         mock.patch.object(fallback_rounds, "_report_brand_empty",
                           side_effect=lambda *a, **k: calls["report"].append(1) or []), \
         mock.patch.object(fallback_rounds, "_ranking_context_edge",
                           side_effect=lambda *a, **k: calls["ranking"].append(1)), \
         mock.patch.object(fallback_rounds, "download_and_filter", return_value=[]):
        _, err = _stderr(lambda: fallback_rounds._round_brand([], "OpenAI, Anthropic and Google", "", Path(d)))
    assert calls["vendor_images"] == ["openai"], calls        # hang 2, 3 khong bat dau
    assert not calls["report"] and not calls["ranking"], calls   # buoc can browser bi bo
    assert "HET GIO" in err and "vong tim anh hang mat" in err, err
    assert th.time_left() is None, "han gio phai duoc go sau vong"


def test_round_brand_clears_deadline_even_when_it_raises():
    with mock.patch("image_brand.vendors_in_story", side_effect=RuntimeError("boom")):
        try:
            fallback_rounds._round_brand([], "x", "", Path("/tmp"))
        except RuntimeError:
            pass
        else:
            raise AssertionError("phai nem lai loi")
    assert th.time_left() is None


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
