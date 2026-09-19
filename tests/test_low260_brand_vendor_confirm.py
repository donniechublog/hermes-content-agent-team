#!/usr/bin/env python3
"""LOW-260: tiêu đề Title Case ("Microsoft Advertising Sets New Rules for AI
Generated Ads") khiến "Rules" — chữ thường bị viết hoa vì kiểu tiêu đề, không
phải tên hãng — lọt qua `image_brand.vendors_in_story` (nhánh all_proper_nouns
ngoài watchlist, LOW-176) thành một "hãng", tốn suất tải+vision vào ảnh Commons
"Rules headquarters" vô nghĩa. Đo thật: state/dcgr/prepare/
microsoft-advertising-ra-quy-tac-moi-cho-dre-dcgr/manifest.json (A1, A3).

`vendors_in_story` phải giữ THUẦN (không mạng — xem tests/test_brand.py), nên
việc xác nhận "cụm này có thật là công ty không" nằm ở `confirm_unlisted_vendor`
(gọi Wikidata, cùng cổng `qid_rank` dùng cho tier trụ sở/founder/logo) và được
`prepare/fallback_rounds._round_brand` gọi ngay trước khi tải ảnh.

Chạy:  venv/bin/python tests/test_low260_brand_vendor_confirm.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_brand as th                                     # noqa: E402
from prepare import fallback_rounds                            # noqa: E402


TIEU_DE_THAT = "Microsoft Advertising Sets New Rules for AI Generated Ads"


def test_real_title_still_leaks_rules_as_cluster():
    """Chốt hành vi HIỆN TẠI của `vendors_in_story` (không đổi, vẫn thuần):
    "Rules" vẫn lọt ra như một cụm — bug nằm ở chỗ KHÔNG XÁC NHẬN nó, không
    phải ở việc `all_proper_nouns` nhìn thấy nó."""
    hangs = th.vendors_in_story(TIEU_DE_THAT)
    khoa = {h["key"] for h in hangs}
    assert "microsoft" in khoa, khoa
    assert "rules" in khoa, "test giả định trước lỗi tồn tại — vá all_proper_nouns thì sửa test này"


def test_confirm_unlisted_vendor_true_when_wikidata_confirms():
    with mock.patch("image_brand.qid_rank", return_value=("Q123", {"P159": []})):
        assert th.confirm_unlisted_vendor("salesforce", "Salesforce") is True


def test_confirm_unlisted_vendor_false_when_no_match_or_network_down():
    with mock.patch("image_brand.qid_rank", return_value=(None, {})):
        assert th.confirm_unlisted_vendor("rules", "Rules") is False


def test_sentence_ask_vision_stock_branch_no_ask_headquarters_question():
    """LOW-260: trước đây kind="stock" rơi vào câu chung "co so/san pham",
    một biểu đồ giá không bao giờ trả lời "có" được -> luôn bị vision loại."""
    c = th.sentence_ask_vision("Microsoft co phieu tang", {"company": "Microsoft", "kind": "stock",
                                                     "ticker": "MSFT:NASDAQ"})
    assert "BIEU DO GIA" in c and "MSFT:NASDAQ" in c and "LIEN_QUAN" in c
    assert "BOI CANH" not in c and "co so/san pham" not in c


def test_round_brand_drops_titlecase_noise_keeps_real_watchlist_company():
    """Tích hợp: `_round_brand` với tiêu đề THẬT gây lỗi — "Rules" (ngoài
    DISPLAY_NAME) phải bị lọc trước khi tới `vendor_images`; "Microsoft" (có
    trong DISPLAY_NAME) không cần xác nhận Wikidata, luôn được xử lý."""
    goi_vendor_images = []

    def vendor_images_gia(hang, so=4, wd=None):
        goi_vendor_images.append(hang["key"])
        return []

    with tempfile.TemporaryDirectory() as d, \
         mock.patch("image_brand.qid_rank", return_value=(None, {})), \
         mock.patch("image_brand.vendor_images", side_effect=vendor_images_gia), \
         mock.patch.object(fallback_rounds, "_report_brand_empty", return_value=[]), \
         mock.patch.object(fallback_rounds, "download_and_filter", return_value=[]):
        fallback_rounds._round_brand([], TIEU_DE_THAT, "", Path(d))

    assert "microsoft" in goi_vendor_images, goi_vendor_images
    assert "rules" not in goi_vendor_images, (
        f"'Rules' (chữ Title Case bị hiểu nhầm là hãng) vẫn tiêu ngân sách tải/vision: {goi_vendor_images}")


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
