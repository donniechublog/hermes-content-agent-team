#!/usr/bin/env python3
"""LOW-292 (20/09/2026) — slide Kite KHONG ghi dong nguon anh.

Ong Chu xem album blog "Gemini pha vong kiem soat, vao ba cong ty that" (task
Kite `t_22d038a3`) va khoanh do dung dong `— <mo ta anh> · via <trang>` o ca bia
(slide 01) lan slide than (05, 06): *"noi dung khong duoc phep xuat hien"*.

Hai mat cua luat, va ca hai deu phai khoa:
  1. Bia va `figure` khong ve dong do nua — du spec CU (hoac vai) van con ghi
     `caption`, hinh xuat ra phai sach. Ban da render roi khong sua lai duoc.
  2. `caption` cua kind `bars` la chuyen KHAC: do la nguon CON SO trong bai
     ("So trong bai · via <ai>"), Ong Chu bat buoc tu truoc. Bo luon cai do la
     sua mot loi bang cach pha mot luat cu — dung kieu ma CLAUDE.md muc 6 cam.

Chay:  venv/bin/python tests/test_low292_no_image_credit.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image  # noqa: E402

import render_edu  # noqa: E402

_TMP = tempfile.TemporaryDirectory()
# Anh du to de qua cong FIG_EMPTY_MIN — cong kich thuoc khong phai viec cua test nay.
ANH = Path(_TMP.name) / "figure.png"
Image.new("RGB", (1200, 800), (90, 110, 140)).save(ANH)

# Nguyen van ba dong bi khoanh do trong album Gemini.
CREDIT_GEMINI = ["Logo Gemini · via The Verge",
                 "Anh chup san khau su kien Google · via OfficeChai",
                 "Trang ứng dụng Google Gemini · via Storyboard18"]


def _theme():
    return dict(render_edu.THEMES["ink"], hero="grid")


def _cover(**them):
    sl = {"kind": "cover", "eyebrow": "GEMINI · DEEP DIVE",
          "title": "Gemini phá vòng kiểm soát", "accent": "phá vòng",
          "standfirst": "Ba công ty thật đã cho agent chạm vào hệ thống nội bộ.",
          "byline": ["donniechublog", "Phân tích", "5 phút đọc"],
          "image": str(ANH)}
    sl.update(them)
    return sl


def _figure(**them):
    sl = {"kind": "figure", "eyebrow": "SỐ LIỆU", "title": "Điểm dựng lại trên SWE-bench",
          "standfirst": "Chữ minh hoạ.", "image": str(ANH)}
    sl.update(them)
    return sl


def _bars(**them):
    sl = {"kind": "bars", "eyebrow": "SỐ LIỆU", "title": "Chi phí mỗi task giảm ba lần",
          "bars": [{"label": "Trước", "value": 2.75, "text": "2,75 USD"},
                   {"label": "Sau", "value": 0.9, "text": "0,90 USD", "highlight": True}],
          "standfirst": "Chữ phụ của biểu đồ.",
          "caption": "Số trong bài · via Google DeepMind"}
    sl.update(them)
    return sl


def _html_cover(sl):
    return render_edu._cover_image(sl, _theme())


def test_cover_does_not_draw_image_credit():
    for cap in CREDIT_GEMINI:
        html = _html_cover(_cover(caption=cap))
        assert "fig-cap" not in html, cap
        assert "via" not in html, cap


def test_figure_does_not_draw_image_credit():
    for cap in CREDIT_GEMINI:
        html = render_edu.s_figure(_figure(caption=cap), _theme())
        assert "fig-cap" not in html, cap
        assert "via" not in html, cap


def test_old_spec_with_caption_still_renders_the_rest():
    """Spec cu (con `caption`) khong duoc no, chi la bo qua dong do."""
    html = _html_cover(_cover(caption=CREDIT_GEMINI[0]))
    # `accent` cat tieu de thanh nhieu the nen so tung manh, khong so ca cau.
    assert "Gemini" in html and "kiểm soát" in html
    assert "Ba công ty thật" in html


def test_bars_still_shows_number_source():
    """Nguon CON SO khong phai nguon anh — van phai hien."""
    html = render_edu.s_bars(_bars(), _theme())
    assert "fig-cap" in html and "Số trong bài · via Google DeepMind" in html


def test_figure_no_longer_requires_caption_but_bars_does():
    figure = _figure()
    assert "caption" not in render_edu.REQUIRED_KIND["figure"]["fields"]
    assert "caption" in render_edu.REQUIRED_KIND["bars"]["fields"]
    assert render_edu.check_field([_cover(), figure, _bars()]) == []
    thieu = render_edu.check_field([_cover(), figure, _bars(caption="")])
    assert any("caption" in d for d in thieu), thieu


def test_image_gate_no_longer_asks_for_caption():
    """Cong noi dung cua render_edu (kich thuoc anh, kind figure) van chay,
    nhung khong con dong "slide co anh phai co 'caption'"."""
    loi = render_edu._gate_content([_cover(), _figure(), _bars()], True)
    assert not any("caption" in d for d in loi), loi


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
