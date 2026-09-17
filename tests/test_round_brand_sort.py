#!/usr/bin/env python3
"""`_round_brand` phải TẢI ứng viên theo thứ tự điểm — đúng hợp đồng mà
chính `download_and_filter` tự ghi trong docstring: "Tai ung vien theo thu tu diem".

`image_brand._candidate` gán điểm khác nhau theo LOẠI ảnh: nơi/sản phẩm 28 >
người (chân dung) 24 > logo 18 — đúng ý "ảnh minh hoạ được nhiều hơn thắng ảnh
chỉ là headshot". `_round_widen_search` (fallback_rounds.py:198) đã sort đúng; `_round_brand`
thì quên, nên tin NHIỀU HÃNG ("Qualcomm ... with Amazon", docstring của chính
hàm) nối thẳng candidate của hãng A trước hãng B theo thứ tự gọi `vendor_images`,
không theo độ "minh hoạ được" — một chân dung của hãng xử lý trước có thể chặn
mất một ảnh trụ sở/sản phẩm của hãng xử lý sau.

Việc sort không cứu được ca "chỉ có đúng một ảnh" (Anthropic/Dario — xem ticket
đường lùi bìa Kite), nhưng đúng hợp đồng cho ca có nhiều lựa chọn thật.

Chạy:  venv/bin/python tests/test_round_brand_sort.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from prepare import fallback_rounds  # noqa: E402
import state_paths                                            # noqa: E402


def test_cands_ok_sort_by_score_decrease_guide_before_when_download():
    """Tin hai hãng: hãng A xử lý trước chỉ có chân dung (24), hãng B xử lý sau
    có ảnh trụ sở (28). Danh sách đưa vào `download_and_filter` phải đặt ảnh trụ sở của
    hãng B lên TRƯỚC chân dung của hãng A — ngược thứ tự xử lý."""
    ung_vien_A = {"image_url": "https://x/a-portrait.jpg", "alt": "chân dung", "og": False,
                 "source": "brand", "w": 1800, "h": 2880, "page_url": "https://x/a",
                 "score": 24, "brand_match": {"company": "HangA", "key": "hanga",
                                              "kind": "person", "keyword": "CEO HangA"}}
    ung_vien_B = {"image_url": "https://x/b-hq.jpg", "alt": "trụ sở", "og": False,
                 "source": "brand", "w": 2000, "h": 1200, "page_url": "https://x/b",
                 "score": 28, "brand_match": {"company": "HangB", "key": "hangb",
                                              "kind": "photo", "keyword": "HangB headquarters"}}

    def anh_hang_gia(hang, so=4, wd=None):
        return [ung_vien_A] if hang["key"] == "hanga" else [ung_vien_B]

    goi = {}

    def tai_va_loc_gia(cands, wd):
        goi["thu_tu_diem"] = [c["score"] for c in cands]
        return []

    with tempfile.TemporaryDirectory() as d, \
         mock.patch("image_brand.vendors_in_story",
                   return_value=[{"company": "HangA", "key": "hanga"},
                                 {"company": "HangB", "key": "hangb"}]), \
         mock.patch("image_brand.vendor_images", side_effect=anh_hang_gia), \
         mock.patch.object(fallback_rounds, "_report_brand_empty", return_value=[]), \
         mock.patch.object(fallback_rounds, "download_and_filter", side_effect=tai_va_loc_gia):
        fallback_rounds._round_brand([], "Qualcomm partners with HangB on chips", "", Path(d))

    assert "thu_tu_diem" in goi, "khong goi toi tai_va_loc — test khong do dung nhanh"
    assert goi["thu_tu_diem"] == sorted(goi["thu_tu_diem"], reverse=True), (
        f"cands khong duoc sap theo diem giam dan: {goi['thu_tu_diem']} — "
        f"vi pham hop dong cua tai_va_loc ('tai ung vien theo thu tu diem')")
    # Tu 12/09/2026 diem con duoc cong theo LOAI TIN (story_type.score_by_type) —
    # khong assert so tuyet doi, chi assert thu tu: tru so (goc 28) van TRUOC
    # chan dung (goc 24) voi category mac dinh.
    assert goi["thu_tu_diem"][0] > goi["thu_tu_diem"][1], \
        "anh tru so (diem cao hon) phai dung TRUOC chan dung"


def test_new_rank_has_it_most_one_image_before_when_rank_which_ok_extra():
    """Đo thật 13/09/2026 (tin Anthropic tố Moonshot): 3 hãng trong tin,
    Anthropic ra 2 chân dung (diem 24), Alibaba ra 2 ảnh trụ sở (diem 28),
    Moonshot chỉ ra ĐÚNG 1 ảnh thật (diem 20, loại "anh" thường) từ
    `_report_brand_empty`. `MAX_EXTRA_BRAND_` = 4 — nếu cứ lấy 4 tấm điểm cao
    nhất theo thứ tự phẳng, Anthropic (2) + Alibaba (2) chiếm hết 4 slot,
    Moonshot bị cắt TRƯỚC KHI vào brief dù có ảnh thật hợp lệ — đúng lỗi
    "bài nhắc cả Anthropic và Moonshot mà chỉ có ảnh Anthropic" Ông Chủ báo.
    Sau khi round-robin theo hãng khi cắt `MAX_EXTRA_BRAND_`, ảnh của Moonshot
    phải sống sót."""
    def _ung(hang, khoa, diem, i):
        return {"image_url": f"https://x/{khoa}-{i}.jpg", "alt": khoa, "og": False,
                "source": "brand", "w": 1800, "h": 1200, "page_url": f"https://x/{khoa}",
                "score": diem, "brand_match": {"company": hang, "key": khoa,
                                               "kind": "person" if diem >= 24 else "photo",
                                               "keyword": f"{hang}"}}

    cands_theo_hang = {
        "anthropic": [_ung("Anthropic", "anthropic", 24, 1), _ung("Anthropic", "anthropic", 24, 2)],
        "alibaba": [_ung("Alibaba", "alibaba", 28, 1), _ung("Alibaba", "alibaba", 28, 2)],
        "moonshot": [_ung("Moonshot AI", "moonshot", 20, 1)],
    }

    def anh_hang_gia(hang, so=4, wd=None):
        return []                                             # Commons rỗng cho cả 3 — ép sang report_about_keyword

    def bao_thuong_hieu_rong_gia(h, wd, phien=None):
        return cands_theo_hang.get(h["key"], [])

    def tai_va_loc_gia(cands, wd):
        wd.mkdir(parents=True, exist_ok=True)
        ra = []
        for i, c in enumerate(cands):
            c = dict(c)
            p = wd / f"tai_{i}.png"
            p.write_bytes(b"\x89PNG\r\n")
            c["original_path"] = str(p)
            ra.append(c)
        return ra                                               # giữ nguyên thứ tự đưa vào (mô phỏng tải xong)

    def phan_loai_gia(a, wd, tieu_de):
        a["uses"] = True
        a["relevant"] = True
        return a

    with tempfile.TemporaryDirectory() as d, \
         mock.patch("image_brand.vendors_in_story",
                   return_value=[{"company": "Anthropic", "key": "anthropic"},
                                 {"company": "Alibaba", "key": "alibaba"},
                                 {"company": "Moonshot AI", "key": "moonshot"}]), \
         mock.patch("image_brand.vendor_images", side_effect=anh_hang_gia), \
         mock.patch.object(fallback_rounds, "_report_brand_empty", side_effect=bao_thuong_hieu_rong_gia), \
         mock.patch.object(fallback_rounds, "download_and_filter", side_effect=tai_va_loc_gia), \
         mock.patch.object(fallback_rounds, "classify", side_effect=phan_loai_gia):
        (Path(d) / state_paths.ORIGINAL_DIR).mkdir()
        anh, dung_duoc, _ = fallback_rounds._round_brand(
            [], "Anthropic accuses Alibaba and Moonshot AI", "", Path(d))

    hang_da_len = {a["brand_match"]["key"] for a in anh if a.get("brand_match")}
    assert "moonshot" in hang_da_len, (
        f"ảnh Moonshot bị cắt trước khi vào brief dù có ứng viên thật — "
        f"chỉ còn hãng: {hang_da_len}")
    assert hang_da_len == {"anthropic", "alibaba", "moonshot"}, (
        f"phải có đủ cả 3 hãng trong tin, chỉ thấy: {hang_da_len}")


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
