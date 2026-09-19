#!/usr/bin/env python3
"""Bảng LOẠI TIN → vật được phép làm ảnh (`story_type.py`), Ông Chủ chốt 12/09/2026:
*"tìm relevant image ko hề khó, hoàn toàn xây dựng logic định lượng được"*.

Đo trước khi viết: `category` đã gán từ lúc quét nhưng engine ảnh chưa đọc.
Tệp này khoá (1) bảng thuần, (2) `category` thật sự đổi hành vi ở ba nấc:
cổng chụp bảng xếp hạng, điểm ứng viên thương hiệu, từ khoá ảnh khái niệm.

Chạy:  venv/bin/python tests/test_story_type.py
"""
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import story_type as lt  # noqa: E402
import image_concept as k  # noqa: E402


def test_standard_type_label_all_write_attempt_offset():
    assert lt.standard_type("m&a") == "M&A"
    assert lt.standard_type("Thâu tóm") == "M&A"
    assert lt.standard_type("MO HINH") == "MODEL"
    assert lt.standard_type("HẠ TẦNG") == "INFRA"
    assert lt.standard_type("gi do la") == ""


def test_board_by_use_error_boss():
    """LOW-264 (19/09/2026): logo > CEO/founder > trụ sở > bảng xếp hạng > cổ
    phiếu cho MỌI loại tin về một hãng cụ thể (BUSINESS/M&A/LAB) — tính năng
    riêng (ghép 2 hãng của M&A, cờ nước của LAB) vẫn giữ, không tính vào 5 mục
    này; model→benchmark, hạ tầng→datacenter/nhà máy không đổi."""
    assert lt.order_image("M&A")[0] == "two_company_pair"
    assert lt.order_image("M&A")[1] == "logo"
    assert lt.late("M&A", "stock")
    assert lt.order_image("MODEL")[0] == "ranking"
    assert lt.order_image("INFRA")[0] == "infrastructure_concept"
    assert lt.order_image("LAB")[0] == "logo" and lt.order_image("LAB")[-1] == "company_country_flag"
    assert lt.late("LAB", "company_country_flag") and lt.late("LAB", "founder")
    assert lt.order_image("BUSINESS") == ("logo", "founder", "headquarters", "ranking", "stock")
    assert lt.order_image("") == lt.DEFAULT
    assert lt.DEFAULT[0] == "logo"


def test_score_by_type_change_order_candidate():
    """LOW-264: biên độ điểm cộng theo thứ tự (100/80/60/40/20/0) phải áp đảo
    chênh lệch điểm GỐC theo loại ảnh (photo 28 / person 24 / logo 18) — trước
    đây biên độ chỉ +8 nên dù bảng nói "logo đứng đầu", logo (18+8=26) vẫn
    thua trụ sở (28+4=32); giờ logo phải THẬT SỰ thắng cả trụ sở lẫn chân
    dung ở BUSINESS/M&A/LAB."""
    for loai in ("BUSINESS", "M&A", "LAB"):
        logo = 18 + lt.score_by_type(loai, "logo")
        nguoi = 24 + lt.score_by_type(loai, "person")
        tru_so = 28 + lt.score_by_type(loai, "photo")
        co_phieu = 30 + lt.score_by_type(loai, "stock")
        assert logo > nguoi > tru_so > co_phieu, (loai, logo, nguoi, tru_so, co_phieu)
    assert lt.score_by_type("SECURITY", "photo") == 0   # SECURITY khong muon tru so
    # MODEL khong doi: logo van truoc founder, bien do moi cang lam ro dieu do
    assert lt.score_by_type("MODEL", "logo") > lt.score_by_type("MODEL", "person")


def test_line_brief_prints_old_object_names():
    """LOW-230: bảng lưu mã English, dòng brief vẫn in đúng tên cũ (byte y hệt).
    LOW-264 (19/09/2026): BUSINESS/M&A/LAB đổi sang logo>founder>trụ sở>xếp
    hạng>cổ phiếu."""
    assert lt.line_brief({"category": "M&A"}) == [
        "Loại tin M&A → ảnh hợp lệ theo thứ tự: ghep_hai_hang > logo > founder > tru_so > xep_hang > co_phieu"
        " (bảng story_type.py, Ông Chủ 12/09/2026)."]
    assert lt.line_brief({"category": "INFRA"})[0].split(": ", 1)[1].startswith(
        "khai_niem_ha_tang > tru_so > co_nuoc_hang > logo (")
    assert lt.line_brief({"category": "MODEL"})[0].split(": ", 1)[1].startswith(
        "xep_hang > chart_cong_bo > logo > founder > khai_niem (")
    assert lt.line_brief({"category": "BUSINESS"})[0].split(": ", 1)[1].startswith(
        "logo > founder > tru_so > xep_hang > co_phieu (")
    assert lt.line_brief({"category": "LAB"})[0].split(": ", 1)[1].startswith(
        "logo > founder > tru_so > xep_hang > co_phieu > co_nuoc_hang (")


def test_country_and_code_has_ballot():
    assert lt.country_of("samsung") == "South Korea"
    assert lt.country_of("deepseek") == "China"
    assert lt.country_of("khong co") == ""
    assert lt.code_has_ballot("nvidia") == "NVDA:NASDAQ"
    assert lt.code_has_ballot("anthropic") == "", "hãng tư nhân không được đoán mã"
    # Ten nuoc phai la ten chuan trong image_concept.COUNTRY de "flag of" khop
    for nuoc in set(lt.COUNTRY_OF_RANK.values()):
        assert nuoc in k.COUNTRY.values(), f"{nuoc!r} khong co trong image_concept.COUNTRY"


def test_keyword_concept_extra_use_before():
    ra = k.keyword_concept("Samsung opens new chip plant", "", dung_llm=False,
                             them=["flag of South Korea"])
    assert ra[0]["keyword"] == "flag of South Korea", ra
    assert ra[0]["reason"] == "theo loại tin"
    assert any(x["keyword"] == "silicon wafer" for x in ra), ra   # heuristic van chay


def test_category_force_capture_board_ranking():
    """MODEL/BENCHMARK ép `is_ranking_story=True` dù tiêu đề không có '#1'/'top'."""
    from prepare import fallback_rounds
    goi = {}
    with mock.patch.object(fallback_rounds.ranking, "is_ranking_story", return_value=False), \
         mock.patch.object(fallback_rounds.ranking, "extract_model", return_value=[]):
        _, tin = fallback_rounds._capture_ranking("DeepSeek releases V4.1 Flash", {"title_en": ""},
                                        {}, "https://x", {"category": "MODEL"}, {}, Path("/tmp"),
                                        khong_browser=False)
        goi["model"] = tin
        _, tin2 = fallback_rounds._capture_ranking("DeepSeek releases V4.1 Flash", {"title_en": ""},
                                         {}, "https://x", {"category": "SECURITY"}, {}, Path("/tmp"),
                                         khong_browser=False)
        goi["security"] = tin2
        # LOW-266: BUSINESS/M&A/LAB co `ranking` (anh boi canh cua hang, cuoi bang
        # tu LOW-264) nhung KHONG phai tin xep hang — truoc day bi ep thanh tin xep
        # hang, brief in dong 🏁 sai va submit_common ap cong xep hang.
        for loai in ("BUSINESS", "M&A", "LAB"):
            _, tin3 = fallback_rounds._capture_ranking(
                "Microsoft Advertising Sets New Rules for AI Generated Ads", {"title_en": ""},
                {}, "https://x", {"category": loai}, {}, Path("/tmp"), khong_browser=False)
            goi[loai] = tin3
    assert goi["model"] is True and goi["security"] is False, goi
    assert goi["BUSINESS"] is False and goi["M&A"] is False and goi["LAB"] is False, goi


def test_is_ranking_story_type_only_when_ranking_leads():
    assert lt.is_ranking_story_type("MODEL") and lt.is_ranking_story_type("BENCHMARK")
    for loai in ("BUSINESS", "M&A", "LAB", "SECURITY", ""):
        assert lt.late(loai, "ranking") == (loai in ("BUSINESS", "M&A", "LAB", "")), loai
        assert not lt.is_ranking_story_type(loai), loai


def test_stack_two_rank_only_when_code():
    from prepare import manifest
    anh = [{"id": "A1", "uses": ["cover"], "relevant": True,
            "brand_match": {"key": "nvidia", "kind": "logo"}},
           {"id": "A2", "uses": ["cover"], "relevant": True,
            "brand_match": {"key": "hugging face", "kind": "logo"}},
           {"id": "A3", "uses": ["body"], "relevant": True,
            "brand_match": {"key": "nvidia", "kind": "person"}}]
    assert manifest.pair_two_vendor_images(anh, "M&A") == [["A1", "A2"]]
    assert manifest.pair_two_vendor_images(anh, "MODEL") == []
    assert manifest.pair_two_vendor_images(anh[:1], "M&A") == []


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
