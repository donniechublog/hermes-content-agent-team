#!/usr/bin/env python3
"""`_vong_thuong_hieu` phải TẢI ứng viên theo thứ tự điểm — đúng hợp đồng mà
chính `tai_va_loc` tự ghi trong docstring: "Tai ung vien theo thu tu diem".

`anh_thuong_hieu._ung_vien` gán điểm khác nhau theo LOẠI ảnh: nơi/sản phẩm 28 >
người (chân dung) 24 > logo 18 — đúng ý "ảnh minh hoạ được nhiều hơn thắng ảnh
chỉ là headshot". `_vong_tim_rong` (vong_bu.py:198) đã sort đúng; `_vong_thuong_hieu`
thì quên, nên tin NHIỀU HÃNG ("Qualcomm ... with Amazon", docstring của chính
hàm) nối thẳng candidate của hãng A trước hãng B theo thứ tự gọi `anh_hang`,
không theo độ "minh hoạ được" — một chân dung của hãng xử lý trước có thể chặn
mất một ảnh trụ sở/sản phẩm của hãng xử lý sau.

Việc sort không cứu được ca "chỉ có đúng một ảnh" (Anthropic/Dario — xem ticket
đường lùi bìa Kite), nhưng đúng hợp đồng cho ca có nhiều lựa chọn thật.

Chạy:  venv/bin/python tests/test_vong_thuong_hieu_sap_xep.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from chuan_bi import vong_bu  # noqa: E402


def test_cands_duoc_sap_theo_diem_giam_dan_truoc_khi_tai():
    """Tin hai hãng: hãng A xử lý trước chỉ có chân dung (24), hãng B xử lý sau
    có ảnh trụ sở (28). Danh sách đưa vào `tai_va_loc` phải đặt ảnh trụ sở của
    hãng B lên TRƯỚC chân dung của hãng A — ngược thứ tự xử lý."""
    ung_vien_A = {"anh": "https://x/a-portrait.jpg", "alt": "chân dung", "og": False,
                 "tu": "thuong_hieu", "rong": 1800, "cao": 2880, "trang": "https://x/a",
                 "diem": 24, "thuong_hieu": {"hang": "HangA", "khoa": "hanga",
                                             "loai": "nguoi", "tu_khoa": "CEO HangA"}}
    ung_vien_B = {"anh": "https://x/b-hq.jpg", "alt": "trụ sở", "og": False,
                 "tu": "thuong_hieu", "rong": 2000, "cao": 1200, "trang": "https://x/b",
                 "diem": 28, "thuong_hieu": {"hang": "HangB", "khoa": "hangb",
                                             "loai": "anh", "tu_khoa": "HangB headquarters"}}

    def anh_hang_gia(hang, so=4, wd=None):
        return [ung_vien_A] if hang["khoa"] == "hanga" else [ung_vien_B]

    goi = {}

    def tai_va_loc_gia(cands, wd):
        goi["thu_tu_diem"] = [c["diem"] for c in cands]
        return []

    with tempfile.TemporaryDirectory() as d, \
         mock.patch("anh_thuong_hieu.hang_trong_tin",
                   return_value=[{"hang": "HangA", "khoa": "hanga"},
                                 {"hang": "HangB", "khoa": "hangb"}]), \
         mock.patch("anh_thuong_hieu.anh_hang", side_effect=anh_hang_gia), \
         mock.patch.object(vong_bu, "tai_va_loc", side_effect=tai_va_loc_gia):
        vong_bu._vong_thuong_hieu([], "Qualcomm partners with HangB on chips", "", Path(d))

    assert "thu_tu_diem" in goi, "khong goi toi tai_va_loc — test khong do dung nhanh"
    assert goi["thu_tu_diem"] == sorted(goi["thu_tu_diem"], reverse=True), (
        f"cands khong duoc sap theo diem giam dan: {goi['thu_tu_diem']} — "
        f"vi pham hop dong cua tai_va_loc ('tai ung vien theo thu tu diem')")
    assert goi["thu_tu_diem"][0] == 28, "anh tru so (diem cao hon) phai dung TRUOC chan dung"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
