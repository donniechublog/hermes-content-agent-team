#!/usr/bin/env python3
"""Bảng chủ đề của `anh_khai_niem` BẮT NHẦM nghĩa (LOW-23, Ông Chủ 12/09/2026).

`tests/test_khai_niem.py` chỉ kiểm ca THUẬN — "nhắc Nhật thì ra cờ Nhật". Tệp này
kiểm ca NGHỊCH: từ nào không được kéo tin sang rổ sai. Sinh ra từ một bộ thật —
bìa "AI giải toán giỏi, nền toán học thì lệch chuẩn" ra tấm dây mạng phòng máy,
vì `\\bhack` trần khớp "reward hacking" (mô hình lách thước đo), không phải tin tặc.

Chạy:  venv/bin/python tests/test_khai_niem_bat_nham.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import anh_khai_niem as k  # noqa: E402

TIN_TOAN = "AI is getting good at math. Mathematicians worry about what that means"


def _tk(tieu_de, tom=""):
    return [x["tu_khoa"] for x in k.tu_khoa_heuristic(tieu_de, tom)]


def test_reward_hacking_khong_thanh_tin_an_ninh_mang():
    """Đúng ca đã hỏng 12/09/2026: tin toán học + 'reward hacking'."""
    for tom in ("Models are reward hacking the benchmark, researchers say",
                "Researchers warn about benchmark gaming and reward hacking",
                "The team ran a hackathon on the Erdos problems"):
        assert "server room cables" not in _tk(TIN_TOAN, tom), tom


def test_tin_an_ninh_mang_that_van_ra_dung_ro():
    """Sửa chiều bắt nhầm mà giết luôn ca đúng thì còn tệ hơn."""
    for tieu_de in ("Hackers breached the model registry, company says",
                    "Ransomware group hits cloud provider",
                    "A phishing campaign targeted AI startups",
                    "State-backed hacking group hit the supply chain"):
        assert "server room cables" in _tk(tieu_de), tieu_de


def test_tin_toan_hoc_thuan_khong_ra_tu_khoa_nao():
    """Không có từ khoá còn hơn có từ khoá sai: rỗng thì vòng khái niệm thoát
    ngay và nấc chụp trang nguồn (LOW-22) lo phần ảnh."""
    assert _tk(TIN_TOAN, "The Erdos problems are a lighthouse for deeper understanding") == []


def test_cau_hoi_vision_hoi_ca_TU_KHOA_CO_HOP_BAI():
    """Cổng `lien_quan` cho ảnh khái niệm chỉ hỏi "có đúng là <từ khoá>" nên một
    từ khoá sai được chính cổng hợp thức hoá. Phải hỏi thêm chiều hợp bài."""
    c = k.cau_hoi_vision(TIN_TOAN, "server room cables")
    assert "hop chu de bai" in c, c
    assert "lac chu de bai" in c, c


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
