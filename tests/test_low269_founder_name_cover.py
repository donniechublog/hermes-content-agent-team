#!/usr/bin/env python3
"""LOW-269 (19/09/2026) — ba lỗ còn lại sau LOW-267 (draft dcgr "Nhà nghiên cứu dùng
Claude tấn công OpenAI"):

  1. Ảnh Dario Amodei có tên trong TÊN TỆP URL (alt rỗng) bị coi là "mặt người
     không rõ ai"; alt "...San Francisco staff..." lại bị coi là có tên người.
  2. Tin hai hãng dùng chân dung founder một bên mà thiếu bên kia dù manifest có.
  3. Bìa là khối tít chụp từ trang nguồn (toàn chữ) trong khi còn cặp ảnh sạch
     ghép dọc được (logo cả hai chủ thể).

Chạy:  venv/bin/python tests/test_low269_founder_name_cover.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import dre_submit                                             # noqa: E402
import image_rules_dre as dre                                 # noqa: E402
import role                                                   # noqa: E402


# ------------------------------------------------ 1. ten nguoi tu ten tep + dia danh
def test_ten_tep_url_ra_ten_nguoi():
    u = "https://trithucvn2.net/wp-content/uploads/2026/09/Dario_Amodei_at_TechCrunch_Disrupt_2023_01_Resized.jpg"
    assert role.person_names_in_url(u) == ["Dario Amodei"], role.person_names_in_url(u)


def test_ten_tep_khac_dinh_dang():
    assert role.person_names_in_url("https://x/a/Sam-Altman%20speaking.png?w=1200") == ["Sam Altman"]
    assert role.person_names_in_url("https://x/a/hero-image.fill.size_1200x675.png") == []
    assert role.person_names_in_url("") == []


def test_dia_danh_khong_phai_ten_nguoi():
    alt = "Anthropic tells San Francisco staff to work from home"
    assert role.person_names_in_alt(alt) == [], role.person_names_in_alt(alt)
    assert role.person_names_in_alt("Getty Images / Wall Street") == []
    assert role.person_names_in_alt("Jensen Huang at Nvidia HQ") == ["Jensen Huang"]


def test_face_no_clear_ai_doc_ten_tep():
    a = {"faces": 1, "alt": "", "url": "https://x/Dario_Amodei_at_Event.jpg"}
    assert role.face_no_clear_ai(a) is False, "ten tep co ten nguoi phai qua cong"
    b = {"faces": 1, "alt": "Anthropic tells San Francisco staff", "url": "https://x/6a8c5ba7.jpg"}
    assert role.face_no_clear_ai(b) is True, "San Francisco khong phai ten nguoi"
    c = {"faces": 1, "alt": "", "url": "https://x/6a8c5ba7.jpg"}
    assert role.face_no_clear_ai(c) is True


def test_subject_names_dre_gom_ten_tep():
    a = {"alt": "", "description": "", "url": "https://x/Dario_Amodei_at_Event.jpg"}
    assert "Dario Amodei" in dre.subject_names(a), dre.subject_names(a)


# ------------------------------------------------ 2. can bang founder giua cac hang
def _anh():
    return {
        "A29": {"brand_match": {}, "uses": ["stack_vertical"], "relevant": True},
        "A5": {"brand_match": {"kind": "person", "person": "Sam Altman", "key": "openai"},
               "uses": ["body"], "relevant": True},
        "A6": {"brand_match": {"kind": "person", "person": "Dario Amodei", "key": "anthropic"},
               "uses": ["body"], "relevant": True},
    }


def test_chi_founder_mot_hang_bi_chan():
    loi = dre.check_founder_balance(_anh(), [{"image": "A5", "subject": "Sam Altman"}])
    assert loi and "anthropic" in loi[0] and "A6" in loi[0], loi


def test_founder_bao_chi_khai_subject_cung_tinh_la_co_mat():
    """A29 khong co nhan hang nhung khai "Sam Altman" -> hang openai da co dai dien."""
    loi = dre.check_founder_balance(_anh(), [{"stack": ["A29", "A29"], "subject": "Sam Altman"}])
    assert loi and "anthropic" in loi[0], loi


def test_du_hai_hang_khong_chan():
    muc = [{"stack": ["A5", "A6"], "subject": "Sam Altman, Dario Amodei"}]
    assert dre.check_founder_balance(_anh(), muc) == []
    muc2 = [{"image": "A5", "subject": "Sam Altman"}, {"image": "A6", "subject": "Dario Amodei"}]
    assert dre.check_founder_balance(_anh(), muc2) == []


def test_khong_dung_founder_nao_khong_chan():
    assert dre.check_founder_balance(_anh(), [{"image": "A29"}]) == []


def test_het_nguon_founder_hang_kia_khong_chan():
    """Manifest chi co founder mot hang -> khong co gi de chan (khong doi vai bia ten)."""
    anh = _anh()
    del anh["A6"]
    assert dre.check_founder_balance(anh, [{"image": "A5", "subject": "Sam Altman"}]) == []
    anh2 = _anh()
    anh2["A6"]["relevant"] = False
    assert dre.check_founder_balance(anh2, [{"image": "A5", "subject": "Sam Altman"}]) == []


# ------------------------------------------------ 3. bia khoi tit
def _anh_bia():
    clean = {"relevant": True, "cluttered": False, "faces": 0, "kind": "photo",
            "uses": ["stack_vertical"], "source": "other_outlet"}
    return {
        "A8": {"relevant": True, "cluttered": True, "faces": 0, "kind": "photo",
               "uses": ["cover_headline_block", "body"], "source": "capture_source"},
        "A2": dict(clean), "A4": dict(clean),
        "A3": dict(clean, faces=1),
        "A9": dict(clean, cluttered=True),
    }


def test_bia_khoi_tit_con_cap_sach_bi_chan():
    loi = dre_submit._headline_cover_with_better(_anh_bia(), "A8", [["A2", "A4"]])
    assert loi and "A2" in loi and "A4" in loi and "KHỐI TÍT" in loi, loi


def test_bia_khoi_tit_het_cap_sach_thi_cho_qua():
    anh = _anh_bia()
    # cap duy nhat: mot co mat nguoi, mot roi -> khong sach
    assert dre_submit._headline_cover_with_better(anh, "A8", [["A3", "A9"]]) is None
    assert dre_submit._headline_cover_with_better(anh, "A8", []) is None


def test_bia_khong_phai_khoi_tit_khong_dung_den():
    assert dre_submit._headline_cover_with_better(_anh_bia(), "A2", [["A2", "A4"]]) is None


def test_cap_sach_bo_qua_anh_chup_khoi_tit_va_chart():
    anh = _anh_bia()
    anh["A4"]["kind"] = "chart"
    assert dre_submit._clean_cover_stack_pair(anh, [["A2", "A4"], ["A2", "A8"]]) is None


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
