#!/usr/bin/env python3
"""CHỤP MÀN HÌNH NHIỀU BÁO CÙNG TIN, mỗi tấm là MỘT slide (LOW-336: giữ tỉ lệ tự nhiên, không đệm).

Ông Chủ 13/09/2026, đưa 6 ảnh chụp 6 báo khác nhau cùng một tin TSMC: *"ai nói
với bạn là chỉ được chụp từ một trang nguồn duy nhất... 1 article hot thì có
hàng vạn tờ báo khắp thế giới đưa tin, bạn chỉ cap 6 trong số đó về rồi đặt
quote và text lên mà cũng phải nghĩ sao?"* và *"phủ một lớp nền cùng màu với
nền của trang gốc, sau đó đặt text và quote của chúng ta lên"*.

Trước đó `_round_capture_source` chụp tối đa 3 trang và `break` ngay sau tấm ĐẦU
TIÊN — cả vòng chỉ bao giờ ra 1 ảnh, nên carousel 6 slide vẫn phải đi tìm ảnh
rời trên web (đường dài, dễ lạc đề). Tấm chụp khối lead lại thường NGANG, để
nguyên thì dính luật "ngang phải ghép đôi", thành tấm lẻ vô dụng.

Chạy:  venv/bin/python tests/test_capture_many_report.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import capture_page                                             # noqa: E402


def test_read_color_background_new_format():
    assert capture_page._out_rgb("rgb(20, 20, 24)") == (20, 20, 24)
    assert capture_page._out_rgb("rgba(255, 255, 255, 0.9)") == (255, 255, 255)
    assert capture_page._out_rgb("#1a1a1a") == (26, 26, 26)
    assert capture_page._out_rgb("#fff") == (255, 255, 255)
    assert capture_page._out_rgb("") == (255, 255, 255), "khong doc duoc -> trang, khong nem"
    assert capture_page._out_rgb("chuoi la") == (255, 255, 255)


def _temp(tmp: Path, w, h, mau=(200, 30, 30)):
    from PIL import Image
    p = tmp / f"in_{w}x{h}.png"
    Image.new("RGB", (w, h), mau).save(p)
    return p


def test_image_landscape_keep_natural_ratio_no_padding():
    """LOW-336: tam chup NGANG giu ti le tu nhien — khong dem mau thanh 4:5 nua
    (vien dem la pixel that, di vao the/slide thanh vien hai ben)."""
    from PIL import Image
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        vao = _temp(tmp, 1200, 500)
        ra = tmp / "ra.png"
        w, h = capture_page.frame_source_capture(vao, ra)
        assert (w, h) == (1200, 500), f"khong duoc dem/cat, duoc {w}x{h}"
        import image_provenance
        assert image_provenance.is_source_capture(Image.open(ra))


def test_round_capture_keep_new_temp_no_use_cell_temp_mark():
    src = (ROOT / "prepare" / "fallback_rounds.py").read_text(encoding="utf-8")
    vong = src[src.index("def _round_capture_source"):src.index("def _round_concept")]
    assert "MAX_PAGE_CAPTURE" in vong
    assert "\n        break\n" not in vong, "khong duoc break sau tam dau — carousel can nhieu slide"
    assert "frame_source_capture(tam, moi)" in vong, "phai lam sach mep + dong dau truoc khi classify"
    assert "capture_page.count_background(" not in vong, "LOW-336: khong dem vien nua"
    assert "other_outlets_bing" in vong, "kho URL mong thi phai tu hoi them bao cung tin"


def test_ceiling_capture_enough_wait_one_carousel():
    from prepare import fallback_rounds
    import carousel
    assert fallback_rounds.MAX_PAGE_CAPTURE >= carousel.MIN_SLIDE, \
        f"tran chup {fallback_rounds.MAX_PAGE_CAPTURE} < {carousel.MIN_SLIDE} slide toi thieu"


def test_capture_source_run_before_find_check_web():
    """Đường ngắn (chụp báo cùng tin) phải thử trước đường dài (Yandex/og:image)."""
    src = (ROOT / "image_prepare.py").read_text(encoding="utf-8")
    than = src[src.index("def prepare_article("):src.index("def workdir(")]
    assert than.index("_round_capture_source(") < than.index("_round_widen_search("), \
        "chup trang nguon phai dung TRUOC vong tim rong"


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
