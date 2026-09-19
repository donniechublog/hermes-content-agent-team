#!/usr/bin/env python3
"""LOW-265 (19/09/2026) — carousel dcgr "Nvidia rót 2 tỷ USD vào một quỹ" (Brookfield):
Ông Chủ, sau khi xem carousel, chỉ ra hai lỗi lặp ảnh chưa cổng nào bắt:

  1. Hai TẤM ẢNH KHÁC NHAU nhưng cùng là chân dung/cận cảnh Jensen Huang (một tấm
     cầm 2 laptop, một tấm nói với mic) — "ko dùng 2 ảnh cùng là chân dung founder
     trong 1 slide". `check_unnamed_face` chỉ đòi khai `subject`, không đối chiếu
     hai lần khai CÙNG một người là hai tấm khác nhau.
  2. CÙNG MỘT tấm ảnh gốc (Jensen cầm 2 laptop) bị dùng lại ở 3 slide khác nhau,
     chỉ khác crop/kích thước nên md5 khác nhau — `check_duplicate` cũ chỉ so
     md5 tuyệt đối nên lọt hết cả 3.

Đã THỬ vá (1) bằng dHash gần-giống trong `check_duplicate`, nhưng ĐO THẬT trên
ảnh chụp (không phải đồ hoạ) cho thấy dHash không giải quyết được: crop nhẹ
(~10% mép) đã cách nhau 7-17 bit, còn hai ảnh THẬT SỰ khác nhau chỉ cách 36 bit
— không có ngưỡng nào vừa bắt được crop vừa không báo oan hai ảnh khác nhau
(khớp đúng kết quả đo thật của LOW-45 trước đó: crop khác của cùng một tấm
cách 22 bit). Bỏ hướng đó, giữ nguyên `check_duplicate` (md5 tuyệt đối).

Fix thật: `check_repeated_subject_portrait` — bắt hai tấm KHÁC NHAU nhưng cùng
khai một `subject` VÀ đều chỉ có 1 mặt (tức đều là chân dung). Dựa vào dữ liệu
ĐÃ KHAI (subject, bắt buộc khai khi có mặt người — `check_unnamed_face`) thay
vì đoán qua pixel, nên bắt được CẢ hai ca: ảnh khác nhau cùng chủ thể (mục 1)
VÀ cùng một tấm gốc bị crop lại nhiều lần (mục 4) — cả hai đều tự động khai
cùng một `subject` ở mọi slide dùng đến, nên chỉ cần một cổng.

Chạy:  venv/bin/python tests/test_low265_repeated_founder_portrait.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image                                        # noqa: E402

import image_rules_dre as dre                                 # noqa: E402


# ------------------------------------------------------- 1. check_duplicate/dHash
def _anh_ngau_nhien(p, w=1200, h=1500, seed=1):
    """Ảnh nhiễu ngẫu nhiên (đủ chi tiết để không bị coi là 'rỗng'/'chart')."""
    Image.effect_noise((w, h), 40 + seed).convert("RGB").save(p)


def test_check_duplicate_bat_md5_trung_tuyet_doi():
    with tempfile.TemporaryDirectory() as t:
        wd = Path(t)
        p1, p2 = wd / "a.png", wd / "b.png"
        _anh_ngau_nhien(p1, seed=1)
        p2.write_bytes(p1.read_bytes())                       # copy y het
        da_thay = {}
        loi1, _ = dre.check_duplicate("slide 2", str(p1), da_thay)
        loi2, _ = dre.check_duplicate("slide 5", str(p2), da_thay)
        assert loi1 == [], loi1
        assert loi2 and "trung anh" in loi2[0] and "slide 2" in loi2[0], loi2


def test_check_duplicate_van_thuan_md5_khong_dung_dhash():
    """LOW-265: dHash gần-giống đã THỬ và BỎ (đo thật thấy không tách được crop
    nhẹ với ảnh khác nhau thật sự — xem docstring `check_duplicate`) — hàm chỉ
    còn so md5 tuyệt đối, không gọi `dhash()`/`is_near_duplicate()` trong thân."""
    import inspect
    src = inspect.getsource(dre.check_duplicate)
    than = src.split('"""', 2)[-1]                            # bo docstring, chi xet THAN ham
    assert "dhash(" not in than and "is_near_duplicate(" not in than, than
    assert "hashlib.md5" in than, than


def test_check_duplicate_khong_bao_oan_hai_anh_that_khac_nhau():
    with tempfile.TemporaryDirectory() as t:
        wd = Path(t)
        p1, p2 = wd / "a.png", wd / "b.png"
        _anh_ngau_nhien(p1, seed=1)
        _anh_ngau_nhien(p2, seed=97)
        da_thay = {}
        loi1, _ = dre.check_duplicate("slide 2", str(p1), da_thay)
        loi2, _ = dre.check_duplicate("slide 3", str(p2), da_thay)
        assert loi1 == [] and loi2 == [], (loi1, loi2)


# ---------------------------------------------- 2. check_repeated_subject_portrait
def test_chan_dung_khac_nhau_cung_mot_nguoi_bi_chan_low265():
    with tempfile.TemporaryDirectory() as t:
        wd = Path(t)
        p1, p2 = wd / "a.png", wd / "b.png"
        _anh_ngau_nhien(p1, seed=1)
        _anh_ngau_nhien(p2, seed=2)
        cu = dre.count_faces
        dre.count_faces = lambda p: 1                         # hai tam deu "mot mat"
        try:
            da_subject = {}
            loi1, _ = dre.check_repeated_subject_portrait(
                "slide 2", str(p1), {"subject": "Jensen Huang"}, da_subject)
            loi2, _ = dre.check_repeated_subject_portrait(
                "slide 7", str(p2), {"subject": "Jensen Huang"}, da_subject)
            assert loi1 == [], loi1
            assert loi2 and "Jensen Huang" in loi2[0] and "slide 2" in loi2[0], loi2
        finally:
            dre.count_faces = cu


def test_chan_dung_ten_khac_nhau_khong_chan():
    with tempfile.TemporaryDirectory() as t:
        wd = Path(t)
        p1, p2 = wd / "a.png", wd / "b.png"
        _anh_ngau_nhien(p1, seed=1)
        _anh_ngau_nhien(p2, seed=2)
        cu = dre.count_faces
        dre.count_faces = lambda p: 1
        try:
            da_subject = {}
            loi1, _ = dre.check_repeated_subject_portrait(
                "slide 2", str(p1), {"subject": "Jensen Huang"}, da_subject)
            loi2, _ = dre.check_repeated_subject_portrait(
                "slide 6", str(p2), {"subject": "Lisa Su"}, da_subject)
            assert loi1 == [] and loi2 == [], (loi1, loi2)
        finally:
            dre.count_faces = cu


def test_chan_dung_anh_nhom_khong_chan():
    """Cùng subject nhưng tấm thứ hai là ảnh NHIỀU mặt (hiện trường/nhóm) —
    không còn là 'chân dung', không chặn."""
    with tempfile.TemporaryDirectory() as t:
        wd = Path(t)
        p1, p2 = wd / "a.png", wd / "b.png"
        _anh_ngau_nhien(p1, seed=1)
        _anh_ngau_nhien(p2, seed=2)
        cu = dre.count_faces
        so = {str(p1): 1, str(p2): 4}
        dre.count_faces = lambda p: so[str(p)]
        try:
            da_subject = {}
            loi1, _ = dre.check_repeated_subject_portrait(
                "slide 2", str(p1), {"subject": "Jensen Huang"}, da_subject)
            loi2, _ = dre.check_repeated_subject_portrait(
                "slide 4", str(p2), {"subject": "Jensen Huang"}, da_subject)
            assert loi1 == [] and loi2 == [], (loi1, loi2)
        finally:
            dre.count_faces = cu


def test_khong_khai_subject_thi_khong_chan():
    with tempfile.TemporaryDirectory() as t:
        wd = Path(t)
        p1 = wd / "a.png"
        _anh_ngau_nhien(p1, seed=1)
        cu = dre.count_faces
        dre.count_faces = lambda p: 1
        try:
            da_subject = {}
            loi, _ = dre.check_repeated_subject_portrait("slide 2", str(p1), {}, da_subject)
            assert loi == [], loi
            assert da_subject == {}
        finally:
            dre.count_faces = cu


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
