#!/usr/bin/env python3
"""Bảng LOẠI TIN → vật được phép làm ảnh (`loai_tin.py`), Ông Chủ chốt 12/09/2026:
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
import loai_tin as lt  # noqa: E402
import anh_khai_niem as k  # noqa: E402


def test_chuan_loai_nhan_ca_viet_lan_lech():
    assert lt.chuan_loai("m&a") == "M&A"
    assert lt.chuan_loai("Thâu tóm") == "M&A"
    assert lt.chuan_loai("MO HINH") == "MODEL"
    assert lt.chuan_loai("HẠ TẦNG") == "INFRA"
    assert lt.chuan_loai("gi do la") == ""


def test_bang_theo_dung_loi_ong_chu():
    """Nguyên văn: brand→logo/trụ sở/founder/cổ phiếu/cờ; thương vụ→hai brand;
    model→benchmark; hạ tầng→datacenter/nhà máy."""
    assert lt.thu_tu_anh("M&A")[0] == "ghep_hai_hang"
    assert lt.muon("M&A", "co_phieu")
    assert lt.thu_tu_anh("MODEL")[0] == "xep_hang"
    assert lt.thu_tu_anh("INFRA")[0] == "khai_niem_ha_tang"
    assert lt.muon("LAB", "co_nuoc_hang") and lt.muon("LAB", "founder")
    assert lt.thu_tu_anh("BUSINESS")[0] == "co_phieu"
    assert lt.thu_tu_anh("") == lt.MAC_DINH


def test_diem_theo_loai_doi_thu_tu_ung_vien():
    """Cùng bộ ứng viên: M&A đẩy logo (18+6=24) lên ngang chân dung (24+2=26)?
    Không — founder đứng sau logo trong bảng M&A nên logo phải THẮNG."""
    logo = 18 + lt.diem_theo_loai("M&A", "logo")
    nguoi = 24 + lt.diem_theo_loai("M&A", "nguoi")
    tru_so = 28 + lt.diem_theo_loai("M&A", "anh")
    assert tru_so > logo, (tru_so, logo)          # tru so van la anh chup that
    assert logo == 24 and nguoi == 26 - 0, (logo, nguoi)
    # LAB: tru so/founder tren logo
    assert lt.diem_theo_loai("LAB", "anh") > lt.diem_theo_loai("LAB", "logo")
    assert lt.diem_theo_loai("SECURITY", "anh") == 0   # SECURITY khong muon tru so


def test_nuoc_va_ma_co_phieu():
    assert lt.nuoc_cua("samsung") == "South Korea"
    assert lt.nuoc_cua("deepseek") == "China"
    assert lt.nuoc_cua("khong co") == ""
    assert lt.ma_co_phieu("nvidia") == "NVDA:NASDAQ"
    assert lt.ma_co_phieu("anthropic") == "", "hãng tư nhân không được đoán mã"
    # Ten nuoc phai la ten chuan trong anh_khai_niem.NUOC de "flag of" khop
    for nuoc in set(lt.NUOC_CUA_HANG.values()):
        assert nuoc in k.NUOC.values(), f"{nuoc!r} khong co trong anh_khai_niem.NUOC"


def test_tu_khoa_khai_niem_them_dung_truoc():
    ra = k.tu_khoa_khai_niem("Samsung opens new chip plant", "", dung_llm=False,
                             them=["flag of South Korea"])
    assert ra[0]["tu_khoa"] == "flag of South Korea", ra
    assert ra[0]["ly_do"] == "theo loại tin"
    assert any(x["tu_khoa"] == "silicon wafer" for x in ra), ra   # heuristic van chay


def test_category_ep_chup_bang_xep_hang():
    """MODEL/BENCHMARK ép `tin_xep_hang=True` dù tiêu đề không có '#1'/'top'."""
    from chuan_bi import vong_bu
    goi = {}
    with mock.patch.object(vong_bu.xep_hang, "la_tin_xep_hang", return_value=False), \
         mock.patch.object(vong_bu.xep_hang, "tach_model", return_value=[]):
        _, tin = vong_bu._chup_xep_hang("DeepSeek releases V4.1 Flash", {"tieu_de_en": ""},
                                        {}, "https://x", {"category": "MODEL"}, {}, Path("/tmp"),
                                        khong_browser=False)
        goi["model"] = tin
        _, tin2 = vong_bu._chup_xep_hang("DeepSeek releases V4.1 Flash", {"tieu_de_en": ""},
                                         {}, "https://x", {"category": "SECURITY"}, {}, Path("/tmp"),
                                         khong_browser=False)
        goi["security"] = tin2
    assert goi["model"] is True and goi["security"] is False, goi


def test_ghep_hai_hang_chi_khi_ma():
    from chuan_bi import manifest
    anh = [{"ma": "A1", "dung": ["bìa"], "lien_quan": True,
            "thuong_hieu": {"khoa": "nvidia", "loai": "logo"}},
           {"ma": "A2", "dung": ["bìa"], "lien_quan": True,
            "thuong_hieu": {"khoa": "hugging face", "loai": "logo"}},
           {"ma": "A3", "dung": ["thân"], "lien_quan": True,
            "thuong_hieu": {"khoa": "nvidia", "loai": "nguoi"}}]
    assert manifest.ghep_hai_hang(anh, "M&A") == [["A1", "A2"]]
    assert manifest.ghep_hai_hang(anh, "MODEL") == []
    assert manifest.ghep_hai_hang(anh[:1], "M&A") == []


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
