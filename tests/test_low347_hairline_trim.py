#!/usr/bin/env python3
"""LOW-347: cắt vạch hairline thừa ở mép cho MỌI ảnh Kite, không cắt nội dung thật.

Đo trên 133 ảnh Kite thật (21/09/2026): bộ đo dải mép tổng quát (`_artifact_depth`, tới 6% cạnh)
đánh dấu 23 ảnh nhưng phần lớn là NỘI DUNG (lề đệm 4:5, chú thích dưới biểu đồ, nhãn trục, viền
giao diện, mép ảnh người) nên không áp đại trà. Nhóm hairline (<= 0,6% cạnh, dòng ngoài cùng gần
một màu) có 5 ảnh: 3 vạch thừa thật (ukisai 2px, bellman 13px, ảnh chụp Gemini 1px), 2 nội dung
(thanh nhấn cam 7px của ảnh Elon = 1,1% cạnh; vệt tối 25px không đều màu của ảnh Infineon).

Chạy:  venv/bin/python tests/test_low347_hairline_trim.py
"""
import base64
import io
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import render_edu as re_                                      # noqa: E402
import tam  # noqa: E402

TH = dict(bg="#171A21", panel="#212530", line="#333846", a="#2FD4E1", b="#8E86F0", stand="#BFC5CF")


def _photo(w=1400, h=1000, bright=False, **edges):
    """Ảnh kiểu chụp (gradient + nhiễu; `bright`: nền giấy sáng như hình paper) rồi vẽ dải mép:
    top=(px,(r,g,b)), right=..., v.v. Vạch phải lệch >= 90 độ sáng so với lòng ảnh mới bị coi là thừa."""
    from PIL import Image, ImageDraw
    random.seed(7)
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            v = (205 if bright else 30) + int(40 * x / w) + random.randint(0, 12)
            px[x, y] = (v, v + 6, min(255, v + 25))
    d = ImageDraw.Draw(im)
    for side, (n, col) in edges.items():
        box = {"top": (0, 0, w, n - 1), "bottom": (0, h - n, w, h), "left": (0, 0, n - 1, h),
               "right": (w - n, 0, w, h)}[side]
        d.rectangle(box, fill=col)
    tmp = Path(tam.temp_dir()) / "photo.png"
    im.save(tmp)
    return tmp


def test_thin_uniform_strong_lines_are_cut():
    """Vạch 2px hồng nhạt ở đáy/phải và 1px sáng ở đỉnh trên ảnh tối; vạch đỏ 13px trên hình
    paper nền sáng: đúng kiểu ukisai / ảnh chụp Gemini / bellman."""
    p = _photo(right=(2, (255, 225, 225)), bottom=(2, (255, 225, 225)))
    assert re_.hairline_box(p) == (0, 0, 1400 - 2, 1000 - 2), re_.hairline_box(p)
    p2 = _photo(top=(1, (250, 210, 210)))
    assert re_.hairline_box(p2) == (0, 1, 1400, 1000)
    p3 = _photo(w=2504, h=2392, bright=True, right=(13, (200, 40, 40)))          # bellman: 13px trên 2504 = 0,5%
    assert re_.hairline_box(p3) == (0, 0, 2504 - 13, 2392)


def test_real_content_is_kept():
    # thanh nhấn cam 7px trên ảnh cao 630 (1,1% cạnh, như ảnh Elon): thiết kế, giữ
    p = _photo(w=1200, h=630, top=(7, (255, 235, 200)))
    assert re_.hairline_box(p) is None
    # chú thích/nhãn dày 2,5% cạnh: giữ
    assert re_.hairline_box(_photo(bottom=(25, (230, 230, 230)))) is None
    # vệt mép KHÔNG đều màu (như ảnh Infineon): giữ
    from PIL import Image
    noisy = _photo()
    im = Image.open(noisy)
    px = im.load()
    random.seed(2)
    for y in range(1000):
        for x in range(0, 3):
            v = random.choice((0, 255))
            px[x, y] = (v, v, v)
    im.save(noisy)
    assert re_.hairline_box(noisy) is None


def test_image_without_hairline_is_untouched():
    """Không có vạch thì không đổi một pixel: hộp None và nhúng nguyên byte ảnh gốc."""
    p = _photo()
    assert re_.hairline_box(p) is None
    nen, _ = re_.image_make_background({"image": str(p)}, TH, "figure")
    assert re_._image_data_uri(p) in nen


def test_render_embeds_the_cropped_image():
    p = _photo(bright=True, right=(8, (200, 40, 40)), bottom=(2, (200, 40, 40)))     # 8px = 0,57% của 1400
    nen, _ = re_.image_make_background({"image": str(p)}, TH, "figure")
    b64 = re.search(r'src="data:image/png;base64,([^"]+)"', nen).group(1)
    from PIL import Image
    assert Image.open(io.BytesIO(base64.b64decode(b64))).size == (1400 - 8, 1000 - 2)
    assert re_._image_data_uri(p) not in nen


def test_truncated_file_does_not_crash():
    p = Path(tam.temp_dir()) / "cut.png"
    good = _photo()
    p.write_bytes(good.read_bytes()[:400])
    assert re_.hairline_box(p) is None


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
