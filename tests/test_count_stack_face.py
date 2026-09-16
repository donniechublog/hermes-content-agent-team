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

Chạy:  venv/bin/python tests/test_count_stack_face.py
"""
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_rules_ethan as image_rules                       # noqa: E402
import schema                                                 # noqa: E402
import role                                                    # noqa: E402


def _read(ma, **k):
    a = {"ma": ma, "dung": ["thân"], "lien_quan": True, "ngang": False, "h": 1350,
         "ti_le": 0.8, "loai": "anh", "mat": 0, "alt": ""}
    a.update(k)
    return a


def _low(ma, ti_le, **k):
    """Anh ngang qua thap de cat doc — chi dung duoc qua "ghep"."""
    return _read(ma, ngang=True, h=600, ti_le=ti_le, dung=["ghép dọc với một ảnh ngang"], **k)


# ---------------------------------------------------------------- luat ghep
def test_stack_fit_frame_use_long_4_5_dark_1_1():
    assert not image_rules.stack_fit_frame(1.5, 1.5), "3:2 + 3:2 = 0.75, ngoai dai"
    assert image_rules.stack_fit_frame(1.78, 1.78), "16:9 + 16:9 = 0.89"
    assert image_rules.stack_fit_frame(2.0, 2.0), "2:1 + 2:1 = 1.0"
    assert not image_rules.stack_fit_frame(3.0, 3.0), "3:1 + 3:1 = 1.5, qua ngang"
    assert not image_rules.stack_fit_frame(None, 2.0) and not image_rules.stack_fit_frame(0, 2.0)


def test_rules_stack_own_dre_label_cap_3_2_low178():
    """LOW-178 (16/09/2026): Dre có sàn ghép riêng `STACK_FLOOR` — hai ảnh 3:2
    (= 0.75, tỉ lệ phổ biến nhất của ảnh báo/Wikimedia) và 4:3+4:3 (= 0.67) đều
    ghép được; `carousel._body_image` cắt giữa dọc phần cao hơn khung. Trần 1:1
    giữ nguyên. Ethan KHÔNG đổi (bài test trên vẫn dùng `image_rules_ethan`)."""
    import image_rules_dre as dre
    assert dre.stack_fit_frame(1.5, 1.5), "3:2 + 3:2 = 0.75: Dre ghép được"
    assert dre.stack_fit_frame(1.5, 1.33), "3:2 + 4:3 = 0.71"
    assert dre.stack_fit_frame(1.33, 1.33), "4:3 + 4:3 = 0.67"
    assert not dre.stack_fit_frame(1.0, 1.0), "1:1 + 1:1 = 0.5: mat qua nhieu"
    assert not dre.stack_fit_frame(3.0, 3.0), "3:1 + 3:1 = 1.5: tran 1:1 giu nguyen"
    assert not dre.stack_fit_frame(None, 1.5) and not dre.stack_fit_frame(0, 1.5)
    assert not image_rules.stack_fit_frame(1.5, 1.5), "Ethan khong doi theo"
    # Canh bao (khong chan) chi khi cao hon 4:5; vua khung thi im.
    assert dre.stack_crop_note(1.78, 1.78) == ""
    assert "3%" in dre.stack_crop_note(1.5, 1.5) and "mép" in dre.stack_crop_note(1.5, 1.5)


def test_one_rules_stack_wait_all_three_say():
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


def test_one_rules_face_wait_person_count_and_image_main():
    assert "role.face_no_clear_ai(" in inspect.getsource(schema.count_image_use_ok)
    assert "face_no_clear_ai(a)" in inspect.getsource(role.can_be_hero)


# ---------------------------------------------------------------- dem cap that
def test_cap_3_2_stack_ok_count_one_slide_low178():
    """Trước LOW-178 cặp 3:2+3:2 (0.75) bị cổng ghép loại nên người đếm cũng
    không đếm (4). Nay Dre nhận cặp đó — người đếm và cổng chặn vẫn hỏi CÙNG
    `image_rules_dre.stack_fit_frame`, nên cùng ra 5."""
    bo = [_read("A6"), _read("A7"), _read("A8"), _read("A9"), _low("A5", 1.5), _low("A10", 1.5)]
    assert schema.count_image_use_ok(bo, "dre") == 5, "A5+A10 ra 0.75 — Dre ghep duoc, mot slide"


def test_cap_over_height_still_no_ok_count():
    bo = [_read("A6"), _low("A5", 1.0), _low("A10", 1.0)]
    assert schema.count_image_use_ok(bo, "dre") == 1, "1:1 + 1:1 = 0.5 — duoi san STACK_FLOOR"


def test_two_banner_16_9_stack_ok_count_one_slide():
    assert schema.count_image_use_ok([_low("A1", 1.78), _low("A2", 1.78)], "dre") == 1


def test_count_cap_dark_prefer_no_greedy():
    """C-A-B-D: chỉ A-C, A-B, B-D ghép vừa khung. Nhặt A-B trước ra 1 cặp; đúng là 2."""
    A, B, C, D = 1 / 0.5, 1 / 0.7, 1 / 0.61, 1 / 0.3
    assert image_rules.stack_fit_frame(A, C) and image_rules.stack_fit_frame(A, B)
    assert image_rules.stack_fit_frame(B, D)
    assert not (image_rules.stack_fit_frame(C, B) or image_rules.stack_fit_frame(A, D)
                or image_rules.stack_fit_frame(C, D))
    bo = [_low("A", A), _low("B", B), _low("C", C), _low("D", D)]
    assert schema.count_image_use_ok(bo, "dre") == 2


# ---------------------------------------------------------------- mat nguoi
def test_face_no_clear_ai_no_ok_count():
    assert schema.count_image_use_ok([_read("A3", mat=1)], "dre") == 0
    assert schema.count_image_use_ok([_read("A3", mat=1, alt="Jensen Huang on stage")], "dre") == 1
    assert schema.count_image_use_ok([_read("A3", mat=2, thuong_hieu={"nguoi": "C.C. Wei"})], "dre") == 1


def test_face_within_stackable_pairs_same_no_count():
    bo = [_low("A1", 1.78, mat=1), _low("A2", 1.78)]
    assert schema.count_image_use_ok(bo, "dre") == 0, "cong ghep cung kiem mat (bo.kiem_mat)"


def test_download_show_t_2d546375():
    """Đúng bộ Dre thấy khi block: 4 ảnh dùng được A6..A9, A5+A10 (3:2+3:2), A3 mặt lạ.
    Trước LOW-178 đếm 4 (cặp 0.75 bị loại); nay cặp đó là một slide -> 5, vẫn < 6."""
    bo = [_read("A3", mat=1), _low("A5", 1.5), _read("A6"), _read("A7"), _read("A8"), _read("A9"),
          _low("A10", 1.5)]
    assert schema.count_image_use_ok(bo, "dre") == 5
    assert not role.has_enough_material("dre", bo), "5 slide < 6: engine phai tim tiep, khong ngung"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
