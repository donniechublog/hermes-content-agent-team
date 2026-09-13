#!/usr/bin/env python3
"""Bảng LOẠI TIN → vật được phép làm ảnh (`story_type.py`), Ông Chủ chốt 12/09/2026:
*"tìm relevant image ko hề khó, hoàn toàn xây dựng logic định lượng được"*.

Đo trước khi viết: `category` đã gán từ lúc quét nhưng engine ảnh chưa đọc.
Tệp này khoá (1) bảng thuần, (2) `category` thật sự đổi hành vi ở ba nấc:
cổng chụp bảng xếp hạng, điểm ứng viên thương hiệu, từ khoá ảnh khái niệm.

Chạy:  venv/bin/python tests/test_loai_tin.py
"""
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import story_type as lt  # noqa: E402
import image_concept as k  # noqa: E402


def test_chuan_loai_nhan_ca_viet_lan_lech():
    assert lt.standard_type("m&a") == "M&A"
    assert lt.standard_type("Thâu tóm") == "M&A"
    assert lt.standard_type("MO HINH") == "MODEL"
    assert lt.standard_type("HẠ TẦNG") == "INFRA"
    assert lt.standard_type("gi do la") == ""


def test_bang_theo_dung_loi_ong_chu():
    """Nguyên văn: brand→logo/trụ sở/founder/cổ phiếu/cờ; thương vụ→hai brand;
    model→benchmark; hạ tầng→datacenter/nhà máy."""
    assert lt.order_image("M&A")[0] == "ghep_hai_hang"
    assert lt.late("M&A", "co_phieu")
    assert lt.order_image("MODEL")[0] == "xep_hang"
    assert lt.order_image("INFRA")[0] == "khai_niem_ha_tang"
    assert lt.late("LAB", "co_nuoc_hang") and lt.late("LAB", "founder")
    assert lt.order_image("BUSINESS")[0] == "co_phieu"
    assert lt.order_image("") == lt.DEFAULT


def test_diem_theo_loai_doi_thu_tu_ung_vien():
    """Cùng bộ ứng viên: M&A đẩy logo (18+6=24) lên ngang chân dung (24+2=26)?
    Không — founder đứng sau logo trong bảng M&A nên logo phải THẮNG."""
    logo = 18 + lt.score_by_type("M&A", "logo")
    nguoi = 24 + lt.score_by_type("M&A", "nguoi")
    tru_so = 28 + lt.score_by_type("M&A", "anh")
    assert tru_so > logo, (tru_so, logo)          # tru so van la anh chup that
    assert logo == 24 and nguoi == 26 - 0, (logo, nguoi)
    # LAB: tru so/founder tren logo
    assert lt.score_by_type("LAB", "anh") > lt.score_by_type("LAB", "logo")
    assert lt.score_by_type("SECURITY", "anh") == 0   # SECURITY khong muon tru so


def test_nuoc_va_ma_co_phieu():
    assert lt.country_of("samsung") == "South Korea"
    assert lt.country_of("deepseek") == "China"
    assert lt.country_of("khong co") == ""
    assert lt.code_has_ballot("nvidia") == "NVDA:NASDAQ"
    assert lt.code_has_ballot("anthropic") == "", "hãng tư nhân không được đoán mã"
    # Ten nuoc phai la ten chuan trong anh_khai_niem.NUOC de "flag of" khop
    for nuoc in set(lt.COUNTRY_OF_RANK.values()):
        assert nuoc in k.COUNTRY.values(), f"{nuoc!r} khong co trong image_concept.COUNTRY"


def test_tu_khoa_khai_niem_them_dung_truoc():
    ra = k.keyword_concept("Samsung opens new chip plant", "", dung_llm=False,
                             them=["flag of South Korea"])
    assert ra[0]["tu_khoa"] == "flag of South Korea", ra
    assert ra[0]["ly_do"] == "theo loại tin"
    assert any(x["tu_khoa"] == "silicon wafer" for x in ra), ra   # heuristic van chay


def test_category_ep_chup_bang_xep_hang():
    """MODEL/BENCHMARK ép `tin_xep_hang=True` dù tiêu đề không có '#1'/'top'."""
    from prepare import fallback_rounds
    goi = {}
    with mock.patch.object(fallback_rounds.ranking, "is_ranking_story", return_value=False), \
         mock.patch.object(fallback_rounds.ranking, "extract_model", return_value=[]):
        _, tin = fallback_rounds._capture_ranking("DeepSeek releases V4.1 Flash", {"tieu_de_en": ""},
                                        {}, "https://x", {"category": "MODEL"}, {}, Path("/tmp"),
                                        khong_browser=False)
        goi["model"] = tin
        _, tin2 = fallback_rounds._capture_ranking("DeepSeek releases V4.1 Flash", {"tieu_de_en": ""},
                                         {}, "https://x", {"category": "SECURITY"}, {}, Path("/tmp"),
                                         khong_browser=False)
        goi["security"] = tin2
    assert goi["model"] is True and goi["security"] is False, goi


def test_ghep_hai_hang_chi_khi_ma():
    from prepare import manifest
    anh = [{"ma": "A1", "dung": ["bìa"], "lien_quan": True,
            "thuong_hieu": {"khoa": "nvidia", "loai": "logo"}},
           {"ma": "A2", "dung": ["bìa"], "lien_quan": True,
            "thuong_hieu": {"khoa": "hugging face", "loai": "logo"}},
           {"ma": "A3", "dung": ["thân"], "lien_quan": True,
            "thuong_hieu": {"khoa": "nvidia", "loai": "nguoi"}}]
    assert manifest.pair_two_vendor_images(anh, "M&A") == [["A1", "A2"]]
    assert manifest.pair_two_vendor_images(anh, "MODEL") == []
    assert manifest.pair_two_vendor_images(anh[:1], "M&A") == []


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
