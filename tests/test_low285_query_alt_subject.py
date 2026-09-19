#!/usr/bin/env python3
"""LOW-285 (19/09/2026) — album dcgr "Lovable mua Sutro":

  1. Ảnh tìm web (Bing/Yandex) mang CÂU TRUY VẤN trong `alt` ("Tomas Halgas Sutro
     founder") → tên người trong truy vấn thành "alt nêu tên" cho MỌI mặt người trong
     kết quả; chữ "logo" trong truy vấn làm download_filter bỏ cả loạt như ảnh rác.
  2. Dre khai `"subject": "Lovable Sutro"` (tên hãng) cho ảnh 2 người vẫn qua cổng,
     vì cổng so từng chữ rời trong bài.

Chạy:  venv/bin/python tests/test_low285_query_alt_subject.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import find_image_web  # noqa: E402
import image_rules_dre as dre  # noqa: E402
import role  # noqa: E402
import submit_common as nc  # noqa: E402

BAI = ("Lovable mua lai Sutro, cong ty dung sau ngon ngu lap trinh SLang. CEO Anton Osika "
       "noi ... Tomas Halgas, nguoi sang lap Sutro, cung ba ky su gia nhap Lovable.")


def _anh():
    return {
        "A13": {"faces": 1, "source": "brand", "alt": "Commons: Anton Osika — CEO Lovable",
                "brand_match": {"company": "Lovable", "person": "Anton Osika"}},
        "A43": {"faces": 2, "source": "web_yandex", "alt": "Tomas Halgas Sutro founder",
                "description": "Hai nguoi dan ong ngoi tren ghe sofa trong van phong."},
        "A99": {"faces": 1, "source": "brand", "alt": "Commons: Michael Dell",
                "brand_match": {"company": "Dell", "person": "Michael Dell"}},
    }


# ------------------------------------------------ 1. alt = cau truy van
def test_web_search_result_has_no_query_alt():
    ra = find_image_web.filter(["https://x.com/a/photo.jpg"], 5, "web_yandex", "Anton Osika Lovable logo")
    assert ra and ra[0]["alt"] == "" and ra[0]["keyword"] == "Anton Osika Lovable logo", ra


def test_old_manifest_query_alt_not_name_evidence():
    a43 = _anh()["A43"]
    assert role.person_names_of(a43) == [], role.person_names_of(a43)
    assert role.face_no_clear_ai(a43) is True
    assert "Tomas Halgas" not in dre.subject_names(a43)


def test_real_alt_still_counts():
    a = {"faces": 1, "source": "press_entity", "alt": "Jensen Huang speaking at GTC 2026"}
    assert role.person_names_of(a) == ["Jensen Huang"]
    assert role.face_no_clear_ai(a) is False


# ------------------------------------------------ 2. subject phai la ten nguoi
def test_company_names_as_subject_blocked():
    loi = nc.check_subject_named(_anh(), ["A43"], "Lovable Sutro", BAI, "slide 3: ")
    assert loi and "TÊN NGƯỜI" in loi[0], loi


def test_single_word_subject_blocked():
    loi = nc.check_subject_named(_anh(), ["A43"], "Sutro", BAI, "slide 3: ")
    assert loi and "TÊN NGƯỜI" in loi[0], loi


def test_scattered_words_not_a_name():
    # "Anton" va "Halgas" deu co trong bai nhung khong lien nhau -> khong phai ten trong bai
    loi = nc.check_subject_named(_anh(), ["A43"], "Anton Halgas", BAI, "slide 3: ")
    assert loi, loi


def test_real_person_in_article_passes():
    assert nc.check_subject_named(_anh(), ["A43"], "Tomas Halgas", BAI, "slide 3: ") == []
    assert nc.check_subject_named(_anh(), ["A13"], "Anton Osika", BAI, "slide 2: ") == []


def test_founder_sharing_brand_name_passes():
    # ten nguoi trung ten hang (Michael Dell / Dell) nhung la brand_match.person cua chinh anh
    assert nc.check_subject_named(_anh(), ["A99"], "Michael Dell",
                                  "Michael Dell noi ve Dell", "slide 4: ") == []


def test_name_with_descriptor_still_passes():
    anh = {"A1": {"faces": 1, "alt": ""}}
    assert nc.check_subject_named(anh, ["A1"], "Hock Tan, Broadcom", "ceo hock tan cua broadcom", "") == []


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
