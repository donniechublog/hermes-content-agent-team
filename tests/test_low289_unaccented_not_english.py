#!/usr/bin/env python3
"""LOW-289 (20/09/2026) — tiếng Việt GÕ MẤT DẤU không được báo là "còn nguyên tiếng Anh".

Dre làm lại tin Lovable (task t_740dcfd8) viết spec không dấu. `carousel._gate_text` báo
đúng ("tieng Viet mat dau"), nhưng `submit_common.check_quote_translated` cũng báo
"trông như còn nguyên tiếng Anh" vì "the" trong "the nao" và "that" trong "that su" bị
đếm là từ chức năng tiếng Anh. Dre đi theo thông báo sai, viết lại quote hai lần rồi
block. Docstring của hàm đã hứa "tiếng Việt gõ mất dấu không phải việc của hàm này".

Kèm một lỗi của chính bộ đo: `vietnamese.find_face_mark` đếm "The" và "the" là HAI dấu
hiệu (khác hoa/thường), nên câu tiếng Anh có hai chữ "the" bị chấm là tiếng Việt mất dấu.

Chạy:  venv/bin/python tests/test_low289_unaccented_not_english.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import carousel  # noqa: E402
import submit_common as nc  # noqa: E402
import vietnamese  # noqa: E402

VI_KHONG_DAU = "Toi lam cong viec nay de nguoi xay dung hieu ro cong nghe that su van hanh the nao."
VI_CO_DAU = "Tôi làm công việc này để người xây dựng hiểu rõ công nghệ thật sự vận hành thế nào."
EN = "The model is now available to everyone in the developer preview and the team says it is faster."


def test_unaccented_vietnamese_not_called_english():
    assert nc.check_quote_translated(VI_KHONG_DAU, "slide 4") == []


def test_unaccented_vietnamese_still_flagged_as_missing_marks():
    """Van phai bao — nhung bang DUNG ten loi, o cong mat dau."""
    loi = carousel._gate_text([("slide 4", VI_KHONG_DAU)], False)
    assert loi and "mat dau" in loi[0], loi
    assert vietnamese.find_face_mark(VI_KHONG_DAU)


def test_real_english_still_blocked():
    loi = nc.check_quote_translated(EN, "slide 4")
    assert loi and "tiếng Anh" in loi[0], loi


def test_accented_vietnamese_clean():
    assert nc.check_quote_translated(VI_CO_DAU, "slide 4") == []
    assert carousel._gate_text([("slide 4", VI_CO_DAU)], False) == []


def test_english_the_twice_not_missing_marks():
    """"The … the" (hoa + thuong) la MOT tu, khong phai hai dau hieu tieng Viet."""
    assert vietnamese.find_face_mark(EN) == []
    assert vietnamese.find_face_mark("The price is the same for the whole team") == []
    # hai tu Viet mat dau KHAC nhau thi van bat
    assert vietnamese.find_face_mark("Hom nay nguoi dung duoc mien phi")


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
