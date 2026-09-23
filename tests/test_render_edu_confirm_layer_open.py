#!/usr/bin/env python3
"""Bìa/figure có ẢNH CHỤP trong render_edu.py — đúng ba ý Ông Chủ chốt 12/09/2026.

Lịch sử ngắn, vì tệp này đã đổi nghĩa một lần: aac796a đưa ảnh vào dòng (contain)
và blur cả ảnh làm nền; 955f33b dọn xác lớp mờ và khoá bằng test rằng lớp mờ
KHÔNG được quay lại. Cùng ngày, Ông Chủ xem bìa thật và nói nguyên văn:

  1. "dùng ảnh hero trong main article làm thumbnail cho hero slide, vì ảnh đó
     là chữ nhật ngang, nên nó hiển thị vừa vặn với nửa trên của hero slide";
  2. "blur toàn bộ tấm ảnh để làm nền cho hero slide CHƯA-BAO-GIỜ là việc được
     yêu cầu với Kite cả, chỉ cần chọn color palette tương đồng với chủ đề";
  3. blur chỉ dành cho ảnh DỌC kéo xuống quá nhiều (bảng xếp hạng): mờ phần
     dưới để title/subtitle hiện lên — không phải blur cả ảnh chính làm nền.

Nên test này khoá CẢ HAI chiều: không còn nền blur (`.fig-nen`) và không còn
ảnh-trong-dòng (`.fig-anh`); nhưng lớp mờ phần-dưới-chữ (`__datMan`, `.fig-molop`,
`DARK_MAX_OPEN`, `VEIL_SPAN`) PHẢI có và phải được đọc thật.

Chạy:  venv/bin/python tests/test_render_edu_confirm_layer_open.py
"""
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import render_edu as re_                                      # noqa: E402
import tam  # noqa: E402

TH = dict(bg="#171A21", panel="#212530", line="#333846",
          a="#2FD4E1", b="#8E86F0", stand="#BFC5CF")


def _image_capture(w=600, h=760):
    """PNG giả làm ẢNH CHỤP THẬT: viền không phẳng -> phân loại 'mo'."""
    from PIL import Image
    random.seed(0)
    im = Image.new("RGB", (w, h), (40, 60, 90))
    px = im.load()
    # Vien tren/hai ben deu mot mau, 40% duoi la nhieu: doc_nen ra "mo" (anh
    # chup), khong phai "phang" (chart) — cung fixture voi test_render_edu.
    for y in range(int(h * 0.6), h):
        for x in range(0, w, 3):
            c = random.randint(0, 255)
            px[x, y] = (c, c, c)
    d = tam.temp_dir()
    p = Path(d) / "chup.png"
    im.save(p, "PNG")
    return p


def test_branch_open_no_remaining_background_blur_and_no_remaining_image_within_line():
    """Ý 2: nền là màu theme, không phải bản blur của chính tấm ảnh.
    Ý 1: ảnh là `.fig-sac` full bề ngang, không phải `.fig-anh` contain."""
    nen, anh = re_.image_make_background({"image": str(_image_capture())}, TH, "bia")
    assert "fig-nen" not in nen, "còn nền blur cả ảnh — Ông Chủ: chưa bao giờ yêu cầu"
    assert "fig-anh" not in nen and "fig-anh" not in anh, "còn ảnh-trong-dòng (contain)"
    assert 'class="fig-sac' in nen, "ảnh chụp phải là lớp sắc full bề ngang"
    assert f'background:{TH["bg"]}' in nen, "nền phải là màu palette của theme"


def test_layer_open_part_below_text_remaining_alive_and_ok_read_real():
    """Ý 3: lớp mờ chỉ cho phần ảnh chờm xuống chữ. Hằng số phải tồn tại VÀ được
    đọc trong HTML sinh ra, script đặt lớp phải được sinh và được gọi."""
    for t in ("DARK_MAX_OPEN", "VEIL_SPAN"):
        assert hasattr(re_, t), f"thiếu {t}"
    nen, _ = re_.image_make_background({"image": str(_image_capture())}, TH, "bia")
    assert "window.__datMan=function" in nen, "không sinh script đặt lớp mờ"
    assert f"{re_.DARK_MAX_OPEN:.3f}" in nen and f"top+{re_.VEIL_SPAN}" in nen, \
        "hằng số lớp mờ có tên nhưng không được đọc"
    assert 'id="figmo"' in nen and 'id="figman"' in nen
    src = (ROOT / "render_edu.py").read_text(encoding="utf-8")
    assert 'page.evaluate("window.__datMan && window.__datMan()")' in src, \
        "_capture_each_slide không gọi __datMan sau khi font xong — lớp mờ đặt sai dòng chữ"
    css = re_.BASE_CSS_TPL
    for luat in (".fig-molop", ".fig-man"):
        assert luat in css, f"BASE_CSS_TPL thiếu {luat}"
    for luat in (".fig-anh-wrap", ".fig-nen{"):
        assert luat not in css, f"BASE_CSS_TPL còn luật chết: {luat}"


def test_layer_open_only_catch_when_image_overlap_over_text():
    """Script phải có đường tắt: mép dưới ảnh nằm trên dòng chữ đầu -> ẩn cả
    lớp mờ lẫn màn tint. Ảnh ngang (ý 1) đi đúng nhánh này."""
    nen, _ = re_.image_make_background({"image": str(_image_capture(1500, 1000))}, TH, "bia")
    assert 'if(Y0+CAO<=top){v.style.display="none";m.style.display="none";return;}' in nen


def test_carousel_still_remaining_mechanism_layer_open():
    """Chiều ngược, giữ từ 955f33b: cơ chế lớp mờ của carousel.py là bản riêng,
    dọn bên render_edu không được kéo theo."""
    import carousel                                           # noqa: PLC0415
    for t in ("THRESHOLD_VARIANCE_NEEDS_LAYER", "VEIL_SPAN"):
        assert hasattr(carousel, t), f"carousel.{t} bị xoá"
    src = (ROOT / "carousel.py").read_text(encoding="utf-8")
    assert "variance - THRESHOLD_VARIANCE_NEEDS_LAYER" in src
    assert "top_y + VEIL_SPAN" in src


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
