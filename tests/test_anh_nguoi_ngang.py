#!/usr/bin/env python3
"""`image_wikidata` chỉ giữ ĐÚNG MỘT ảnh mỗi người (P18, thường là chân dung studio
dọc) mà chưa bao giờ hỏi Commons theo TÊN NGƯỜI để tìm ảnh sự kiện/họp báo NGANG.

Ông Chủ 12/09/2026: *"chỉ cần search claude hay anthropic thì cũng ra một rừng
ảnh rồi, kiếm cái ảnh rõ nét và ratio phù hợp khó thế sao?"* — đúng, đo thật
bằng chính `scan_common.ask_commons`: search "Dario Amodei" ra 9 ảnh họp báo/sự
kiện tỉ lệ 1,5 (ngang), điều mà `image_wikidata` trước đây không bao giờ chạm tới.

Test này KHÔNG gọi mạng thật (mock `_ask_commons`) để chạy được offline/CI; bằng
chứng mạng thật nằm trong ticket, không nằm trong test.

Chạy:  venv/bin/python tests/test_anh_nguoi_ngang.py
"""
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_brand as th  # noqa: E402


def _trang_commons(w, h, ten_tep, mime="image/jpeg"):
    return {"title": f"File:{ten_tep}",
            "imageinfo": [{"width": w, "height": h, "mime": mime,
                          "thumburl": f"https://x/{ten_tep}", "url": f"https://x/{ten_tep}"}]}


def test_anh_nguoi_ngang_loc_dung_ten_va_ti_le():
    """Trả ảnh NGANG, khớp đủ hai từ của tên, bỏ ảnh dọc và ảnh không khớp tên."""
    pages = {
        "1": _trang_commons(4000, 2667, "Dario Amodei at TechCrunch Disrupt 2023 01.jpg"),
        "2": _trang_commons(1800, 2880, "Dario Amodei in 2023.jpg"),          # doc -> bo
        "3": _trang_commons(3500, 2300, "Some Other Person at an event.jpg"),  # sai ten -> bo
        "4": _trang_commons(600, 400, "Dario Amodei tiny.jpg"),               # qua nho -> bo
    }
    with mock.patch.object(th, "_ask_commons", return_value=pages):
        ra = th.image_person_landscape("Dario Amodei", "CEO", "Anthropic", "anthropic")
    assert len(ra) == 1, [c["thuong_hieu"] for c in ra]
    c = ra[0]
    assert c["rong"] >= c["cao"], "phai la anh ngang/vuong, khong doc"
    assert c["diem"] == 26
    assert c["thuong_hieu"]["loai"] == "nguoi"
    assert c["thuong_hieu"]["nguoi"] == "Dario Amodei"


def test_hai_nguoi_khac_ghep_ten_khong_duoc_lot():
    """Tên phải nằm LIỀN NHAU, đúng thứ tự — không phải "mỗi từ có mặt đâu đó".

    Bản lỏng `all(_has_word(...))` cho "dario rossi meets luca amodei in rome" đi
    qua: ảnh HAI NGƯỜI KHÁC, mà caption lại khai `nhan_vat: "Dario Amodei"` —
    bịa mặt người, đúng thứ IMAGE_RULES §0/§6 sinh ra để chặn. Cùng lớp lỗi mà
    `filter_commons` bị siết ngày 12/09/2026 ("Hugging Face" khớp "Rathlin hugging
    the cliff face"), bản vá đó không lan sang đây."""
    pages = {
        "1": _trang_commons(4000, 2667, "Dario Rossi meets Luca Amodei in Rome.jpg"),
        "2": _trang_commons(4000, 2667, "Amodei family and Dario Gabbani at a wedding.jpg"),
    }
    with mock.patch.object(th, "_ask_commons", return_value=pages):
        ra = th.image_person_landscape("Dario Amodei", "CEO", "Anthropic", "anthropic")
    assert ra == [], [c["alt"] for c in ra]


def test_anh_wikidata_uu_tien_ngang_hon_chan_dung_doc_sau_khi_sap():
    """Ghép với sort của `_round_brand` (test riêng): trong chính danh sách
    `image_wikidata` trả về, ảnh ngang (26) phải đứng trước chân dung dọc (24)
    một khi đã sort theo điểm — đo bằng lệnh Ông Chủ có thể tự chạy lại."""
    tl = {"anh": [], "nguoi": [{"ten": "Dario Amodei", "tep": "Dario Amodei in 2023.jpg",
                                "vai": "CEO"}], "logo": []}
    pages_p18 = {"p": _trang_commons(1800, 2880, "Dario Amodei in 2023.jpg")}
    pages_ngang = {"e": _trang_commons(4000, 2667, "Dario Amodei at TechCrunch Disrupt 2023 01.jpg")}

    def hoi_commons_gia(cau):
        # commons_urls goi _ask_commons(...) mot lan cho danh sach ten tep P18;
        # image_person_landscape goi rieng mot lan voi cau la ten nguoi trong ngoac kep.
        return pages_ngang if cau.startswith('"Dario') else pages_p18

    with mock.patch.object(th, "material_wikidata", return_value=tl), \
         mock.patch.object(th, "_ask_commons", side_effect=hoi_commons_gia):
        ra = th.image_wikidata({"khoa": "anthropic", "hang": "Anthropic"})
    ra.sort(key=lambda c: -c.get("diem", 0))
    assert ra[0]["rong"] >= ra[0]["cao"], "sau khi sap, anh dau tien phai la anh ngang"
    assert ra[-1]["rong"] < ra[-1]["cao"], "chan dung doc phai roi xuong cuoi"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
