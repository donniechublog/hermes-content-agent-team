#!/usr/bin/env python3
"""LOW-46: người đếm slide (`schema.count_image_use_ok`) không được lạc quan hơn cổng chặn.

Tin TSMC lần ba (t_2d546375, 13/09/2026): engine đếm "đủ 6", ngừng tìm; Dre dựng
thật thì cổng chặn loại cặp ghép A5+A10 (ra tỉ lệ 0.75, ngoài dải 4:5..1:1) và
tấm A3 có mặt người không rõ ai — còn 4 slide, Dre block. Hai chỗ đếm sai:

  1. `len(chi_ghep) // 2` coi BẤT KỲ hai tấm chỉ-ghép nào cũng là một cặp;
  2. tấm mặt người không rõ ai vẫn được đếm dù `check_subject_named` chặn nó.

Nay người đếm, gợi ý cặp (`manifest.stackable_pairs`) và cổng chặn (`dre_submit`) hỏi
CÙNG một luật ghép (`image_rules.stack_fit_frame`); người đếm và `can_be_hero`
hỏi CÙNG một luật mặt người (`role.face_no_clear_ai`).

Chạy:  venv/bin/python tests/test_dem_ghep_mat_nguoi.py
"""
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_rules_ethan as image_rules                       # noqa: E402
import schema                                                 # noqa: E402
import role                                                    # noqa: E402


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
    assert not image_rules.stack_fit_frame(1.5, 1.5), "3:2 + 3:2 = 0.75, ngoai dai"
    assert image_rules.stack_fit_frame(1.78, 1.78), "16:9 + 16:9 = 0.89"
    assert image_rules.stack_fit_frame(2.0, 2.0), "2:1 + 2:1 = 1.0"
    assert not image_rules.stack_fit_frame(3.0, 3.0), "3:1 + 3:1 = 1.5, qua ngang"
    assert not image_rules.stack_fit_frame(None, 2.0) and not image_rules.stack_fit_frame(0, 2.0)


def test_mot_luat_ghep_cho_ca_ba_noi():
    """Gộp, không chép: ba nơi trước đây mỗi nơi tự tính công thức tỉ lệ.

    LOW-182 (16/09/2026): không còn một `image_rules.stack_fit_frame` dùng
    chung — mỗi nơi gọi ĐÚNG module luật của vai đang chạy (`manifest`/`schema`
    qua `role.active_rules()`/`role.rules_module()`, `dre_submit` tĩnh qua
    `image_rules_dre` vì nó luôn là Dre) — nhưng cả ba vẫn CÙNG GỌI
    `stack_fit_frame(`, không tự tính lại công thức tỉ lệ."""
    from prepare import manifest
    import dre_submit
    assert "stack_fit_frame(" in inspect.getsource(manifest.stackable_pairs)
    assert "image_rules_dre.stack_fit_frame(" in inspect.getsource(dre_submit._resolve_stack)
    assert "stack_fit_frame(" in inspect.getsource(schema._count_stackable_pairs_real)
    for ham in (manifest.stackable_pairs, dre_submit._resolve_stack):
        assert "1 / (1 /" not in inspect.getsource(ham) and "1 / sum(" not in inspect.getsource(ham)


def test_mot_luat_mat_nguoi_cho_nguoi_dem_va_anh_chinh():
    assert "role.face_no_clear_ai(" in inspect.getsource(schema.count_image_use_ok)
    assert "face_no_clear_ai(a)" in inspect.getsource(role.can_be_hero)


# ---------------------------------------------------------------- dem cap that
def test_cap_ghep_lech_khung_khong_duoc_dem():
    bo = [_doc("A6"), _doc("A7"), _doc("A8"), _doc("A9"), _thap("A5", 1.5), _thap("A10", 1.5)]
    assert schema.count_image_use_ok(bo, "dre") == 4, "A5+A10 ra 0.75 — cong ghep chan, khong phai mot slide"


def test_hai_banner_16_9_ghep_duoc_dem_mot_slide():
    assert schema.count_image_use_ok([_thap("A1", 1.78), _thap("A2", 1.78)], "dre") == 1


def test_dem_cap_toi_uu_khong_tham_lam():
    """C-A-B-D: chỉ A-C, A-B, B-D ghép vừa khung. Nhặt A-B trước ra 1 cặp; đúng là 2."""
    A, B, C, D = 1 / 0.5, 1 / 0.7, 1 / 0.61, 1 / 0.3
    assert image_rules.stack_fit_frame(A, C) and image_rules.stack_fit_frame(A, B)
    assert image_rules.stack_fit_frame(B, D)
    assert not (image_rules.stack_fit_frame(C, B) or image_rules.stack_fit_frame(A, D)
                or image_rules.stack_fit_frame(C, D))
    bo = [_thap("A", A), _thap("B", B), _thap("C", C), _thap("D", D)]
    assert schema.count_image_use_ok(bo, "dre") == 2


# ---------------------------------------------------------------- mat nguoi
def test_mat_nguoi_khong_ro_ai_khong_duoc_dem():
    assert schema.count_image_use_ok([_doc("A3", mat=1)], "dre") == 0
    assert schema.count_image_use_ok([_doc("A3", mat=1, alt="Jensen Huang on stage")], "dre") == 1
    assert schema.count_image_use_ok([_doc("A3", mat=2, thuong_hieu={"nguoi": "C.C. Wei"})], "dre") == 1


def test_mat_nguoi_trong_cap_ghep_cung_khong_dem():
    bo = [_thap("A1", 1.78, mat=1), _thap("A2", 1.78)]
    assert schema.count_image_use_ok(bo, "dre") == 0, "cong ghep cung kiem mat (bo.kiem_mat)"


def test_tai_hien_t_2d546375():
    """Đúng bộ Dre thấy khi block: 4 ảnh dùng được A6..A9, A5+A10 lệch khung, A3 mặt lạ."""
    bo = [_doc("A3", mat=1), _thap("A5", 1.5), _doc("A6"), _doc("A7"), _doc("A8"), _doc("A9"),
          _thap("A10", 1.5)]
    assert schema.count_image_use_ok(bo, "dre") == 4
    assert not role.has_enough_material("dre", bo), "4 slide < 6: engine phai tim tiep, khong ngung"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
