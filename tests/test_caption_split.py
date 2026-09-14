#!/usr/bin/env python3
"""_split_caption_html (approve_post.py) — LOW-157.

Caption vuot 1024 ky tu khong con bi caption_check chan nop (xem
tests/test_caption.py); publish() tu tach thanh phan 1 (<=1024, gan lam
caption that cua anh) + phan 2 (tin nhan rieng). Diem nong nhat la the HTML
(b/i/code/strong/em/a) con mo dung tai diem cat — cat tho se vo parse_mode=HTML
(Telegram tu choi 400).

Chay:  venv/bin/python tests/test_caption_split.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import approve_post as db  # noqa: E402

_TAG = re.compile(r"<(/?)([a-zA-Z][\w-]*)")


def _tag_stack_at_end(s: str) -> list:
    """Danh sach the con mo o CUOI chuoi (khong quan tam thu tu long trong bai
    that vi CARD_ALLOW khong lam to nhau sau, nhung van dung stack cho dung)."""
    stack = []
    for m in _TAG.finditer(s):
        closing, name = m.group(1), m.group(2).lower()
        if closing:
            if stack and stack[-1] == name:
                stack.pop()
        else:
            stack.append(name)
    return stack


def test_ngan_hon_limit_tra_nguyen_khong_tach():
    cap = "Caption ngắn, không cần tách."
    p1, p2 = db._split_caption_html(cap, 1024)
    assert p1 == cap and p2 == ""


def test_dai_hon_limit_phan1_khong_vuot_gioi_han():
    cap = ("Câu một kết thúc. " * 100)  # ~1900 ky tu, khong the HTML
    assert len(cap) > 1024
    p1, p2 = db._split_caption_html(cap, 1024)
    assert len(p1) <= 1024, len(p1)
    assert p2 != ""


def test_cat_tai_ranh_gioi_cau_khong_cat_giua_tu():
    cap = ("Câu một kết thúc rõ ràng. " * 60)
    p1, p2 = db._split_caption_html(cap, 1024)
    # Phan 1 phai ket thuc bang dau cham cau (cat tai ranh gioi cau), khong
    # phai cat cung giua mot tu.
    assert p1.rstrip().endswith("."), repr(p1[-30:])


def test_ghep_lai_giu_nguyen_noi_dung_khong_the():
    cap = ("Đoạn văn dài có nhiều câu để kiểm tra việc tách không làm mất nội dung nào cả. " * 20)
    p1, p2 = db._split_caption_html(cap, 1024)
    # Ghep lai (bo khoang trang thua o diem noi) phai khop noi dung goc.
    assert (p1 + " " + p2).replace("  ", " ").strip() == cap.replace("  ", " ").strip() \
        or p1 + p2 == cap, (p1, p2)


def test_the_con_mo_tai_diem_cat_duoc_dong_va_mo_lai():
    """<b> mo truoc diem cat, dong o cuoi phan1 va mo lai dau phan2 — Telegram
    HTML parser can moi tin nhan tu can bang, khong duoc de the ho."""
    truoc = "X " * 200                       # day do dai qua 1024 truoc khi mo <b>
    cap = truoc + "<b>" + ("chữ đậm rất dài " * 60) + "</b>" + " hết."
    assert len(cap) > 1024
    p1, p2 = db._split_caption_html(cap, 1024)
    assert _tag_stack_at_end(p1) == [], f"phần 1 còn thẻ hở: {p1[-60:]!r}"
    # Phan 2 phai tu can bang tu dau (khong bi thieu the mo neu <b> con dang mo)
    assert _tag_stack_at_end(p1 + p2) == [], "ghép lại vẫn phải cân bằng the"


def test_the_dong_truoc_diem_cat_khong_bi_dong_them():
    """<b>ngắn</b> dong xong TRUOC diem cat thi phan 1 khong duoc them </b> thua."""
    cap = "<b>Mở đầu ngắn.</b> " + ("Câu tiếp theo dài. " * 70)
    assert len(cap) > 1024
    p1, _p2 = db._split_caption_html(cap, 1024)
    assert p1.count("<b>") == 1 and p1.count("</b>") == 1


def test_the_a_giu_nguyen_href_khi_mo_lai():
    truoc = "X " * 200
    cap = truoc + '<a href="https://vd.example/duong-dan">chữ liên kết dài ' + ("lặp lại " * 150) + "</a> hết."
    assert len(cap) > 1024, len(cap)
    p1, p2 = db._split_caption_html(cap, 1024)
    assert _tag_stack_at_end(p1) == []
    if "<a" in p2:
        assert 'href="https://vd.example/duong-dan"' in p2, p2[:80]


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
