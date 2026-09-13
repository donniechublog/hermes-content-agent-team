#!/usr/bin/env python3
"""Vùng chụp khối lead chỉ lấy tấm <img>, không lấy cả <figure> — bỏ sót
<figcaption> (chú thích nguồn ảnh: "Photo: ..., Getty Images") đè lên chữ
tiêu đề/quote khi render (phát hiện 13/09/2026 khi Ông Chủ yêu cầu render
thật lên các slide chụp báo cùng tin).

`<figure><img>...</img><figcaption>Ảnh: X/Reuters</figcaption></figure>` là
khuôn HTML phổ biến — `figure.getBoundingClientRect()` bao trọn cả figcaption,
kéo dài vùng chụp xuống đúng chỗ ta sẽ vẽ headline/quote đè lên.

Chạy:  venv/bin/python tests/test_chup_loai_chu_thich.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import capture_page                                              # noqa: E402


def test_js_lead_chi_do_img_ben_trong_figure_khong_do_ca_figure():
    js = capture_page._JS_LEAD
    assert "chiAnh" in js, "phải có bước thu hẹp về ảnh bên trong, không dùng thẳng bbox của figure/picture"
    # `el` (bbox dùng để đo) phải đến từ `chiAnh(goc_el)`, không phải chính `goc_el`.
    m = re.search(r"const el = chiAnh\(goc_el\);\s*\n\s*const r = el\.getBoundingClientRect\(\)", js)
    assert m, "phải đo bbox của chiAnh(goc_el), không phải goc_el (tức cả <figure>)"


def test_chi_anh_uu_tien_img_con_khi_goc_la_figure():
    js = capture_page._JS_LEAD
    # Hàm chiAnh: figure/picture -> tìm img con; img -> giữ nguyên.
    assert "el.querySelector('img, picture img, picture source')" in js
    assert "if (t === 'img') return el;" in js


if __name__ == "__main__":
    ok = 0
    ten = [n for n in dir() if n.startswith("test_")]
    for n in ten:
        try:
            globals()[n]()
            ok += 1
        except AssertionError as e:
            print(f"FAIL {n}: {e}")
    print(f"{ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
