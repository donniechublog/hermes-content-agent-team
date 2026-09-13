#!/usr/bin/env python3
"""LOW-46: người đếm slide (`schema.so_anh_dung_duoc`) không được lạc quan hơn cổng chặn.

Tin TSMC lần ba (t_2d546375, 13/09/2026): engine đếm "đủ 6", ngừng tìm; Dre dựng
thật thì cổng chặn loại cặp ghép A5+A10 (ra tỉ lệ 0.75, ngoài dải 4:5..1:1) và
tấm A3 có mặt người không rõ ai — còn 4 slide, Dre block. Hai chỗ đếm sai:

  1. `len(chi_ghep) // 2` coi BẤT KỲ hai tấm chỉ-ghép nào cũng là một cặp;
  2. tấm mặt người không rõ ai vẫn được đếm dù `kiem_nhan_vat` chặn nó.

Nay người đếm, gợi ý cặp (`manifest.cap_ghep`) và cổng chặn (`dre_nop`) hỏi
CÙNG một luật ghép (`luat_anh.ghep_vua_khung`); người đếm và `anh_chinh_duoc`
hỏi CÙNG một luật mặt người (`vai.mat_khong_ro_ai`).

Chạy:  venv/bin/python tests/test_dem_ghep_mat_nguoi.py
"""
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import luat_anh                                               # noqa: E402
import schema                                                 # noqa: E402
import vai                                                    # noqa: E402


def _doc(ma, **k):
    a = {"ma": ma, "dung": ["thân"], "lien_quan": True, "ngang": False, "h": 1350,
         "ti_le": 0.8, "loai": "anh", "mat": 0, "alt": ""}
    a.update(k)
    return a


def _thap(ma, ti_le, **k):
    """Anh ngang qua thap de cat doc — chi dung duoc qua "ghep"."""
    return _doc(ma, ngang=True, h=600, ti_le=ti_le, dung=["ghép dọc với một ảnh ngang"], **k)


# ---------------------------------------------------------------- luat ghep
def test_ghep_vua_khung_dung_dai_4_5_toi_1_1():
    assert not luat_anh.ghep_vua_khung(1.5, 1.5), "3:2 + 3:2 = 0.75, ngoai dai"
    assert luat_anh.ghep_vua_khung(1.78, 1.78), "16:9 + 16:9 = 0.89"
    assert luat_anh.ghep_vua_khung(2.0, 2.0), "2:1 + 2:1 = 1.0"
    assert not luat_anh.ghep_vua_khung(3.0, 3.0), "3:1 + 3:1 = 1.5, qua ngang"
    assert not luat_anh.ghep_vua_khung(None, 2.0) and not luat_anh.ghep_vua_khung(0, 2.0)


def test_mot_luat_ghep_cho_ca_ba_noi():
    """Gộp, không chép: ba nơi trước đây mỗi nơi tự tính công thức tỉ lệ."""
    from chuan_bi import manifest
    import dre_nop
    assert "luat_anh.ghep_vua_khung(" in inspect.getsource(manifest.cap_ghep)
    assert "luat_anh.ghep_vua_khung(" in inspect.getsource(dre_nop._giai_ghep)
    assert "luat_anh.ghep_vua_khung(" in inspect.getsource(schema._so_cap_ghep_that)
    for ham in (manifest.cap_ghep, dre_nop._giai_ghep):
        assert "1 / (1 /" not in inspect.getsource(ham) and "1 / sum(" not in inspect.getsource(ham)


def test_mot_luat_mat_nguoi_cho_nguoi_dem_va_anh_chinh():
    assert "vai.mat_khong_ro_ai(" in inspect.getsource(schema.so_anh_dung_duoc)
    assert "mat_khong_ro_ai(a)" in inspect.getsource(vai.anh_chinh_duoc)


# ---------------------------------------------------------------- dem cap that
def test_cap_ghep_lech_khung_khong_duoc_dem():
    bo = [_doc("A6"), _doc("A7"), _doc("A8"), _doc("A9"), _thap("A5", 1.5), _thap("A10", 1.5)]
    assert schema.so_anh_dung_duoc(bo) == 4, "A5+A10 ra 0.75 — cong ghep chan, khong phai mot slide"


def test_hai_banner_16_9_ghep_duoc_dem_mot_slide():
    assert schema.so_anh_dung_duoc([_thap("A1", 1.78), _thap("A2", 1.78)]) == 1


def test_dem_cap_toi_uu_khong_tham_lam():
    """C-A-B-D: chỉ A-C, A-B, B-D ghép vừa khung. Nhặt A-B trước ra 1 cặp; đúng là 2."""
    A, B, C, D = 1 / 0.5, 1 / 0.7, 1 / 0.61, 1 / 0.3
    assert luat_anh.ghep_vua_khung(A, C) and luat_anh.ghep_vua_khung(A, B)
    assert luat_anh.ghep_vua_khung(B, D)
    assert not (luat_anh.ghep_vua_khung(C, B) or luat_anh.ghep_vua_khung(A, D)
                or luat_anh.ghep_vua_khung(C, D))
    bo = [_thap("A", A), _thap("B", B), _thap("C", C), _thap("D", D)]
    assert schema.so_anh_dung_duoc(bo) == 2


# ---------------------------------------------------------------- mat nguoi
def test_mat_nguoi_khong_ro_ai_khong_duoc_dem():
    assert schema.so_anh_dung_duoc([_doc("A3", mat=1)]) == 0
    assert schema.so_anh_dung_duoc([_doc("A3", mat=1, alt="Jensen Huang on stage")]) == 1
    assert schema.so_anh_dung_duoc([_doc("A3", mat=2, thuong_hieu={"nguoi": "C.C. Wei"})]) == 1


def test_mat_nguoi_trong_cap_ghep_cung_khong_dem():
    bo = [_thap("A1", 1.78, mat=1), _thap("A2", 1.78)]
    assert schema.so_anh_dung_duoc(bo) == 0, "cong ghep cung kiem mat (bo.kiem_mat)"


def test_tai_hien_t_2d546375():
    """Đúng bộ Dre thấy khi block: 4 ảnh dùng được A6..A9, A5+A10 lệch khung, A3 mặt lạ."""
    bo = [_doc("A3", mat=1), _thap("A5", 1.5), _doc("A6"), _doc("A7"), _doc("A8"), _doc("A9"),
          _thap("A10", 1.5)]
    assert schema.so_anh_dung_duoc(bo) == 4
    assert not vai.du_nguyen_lieu("dre", bo), "4 slide < 6: engine phai tim tiep, khong ngung"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
