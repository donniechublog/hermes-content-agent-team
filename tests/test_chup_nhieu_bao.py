#!/usr/bin/env python3
"""CHỤP MÀN HÌNH NHIỀU BÁO CÙNG TIN, đệm nền cùng màu trang gốc — mỗi tấm là MỘT slide.

Ông Chủ 13/09/2026, đưa 6 ảnh chụp 6 báo khác nhau cùng một tin TSMC: *"ai nói
với bạn là chỉ được chụp từ một trang nguồn duy nhất... 1 article hot thì có
hàng vạn tờ báo khắp thế giới đưa tin, bạn chỉ cap 6 trong số đó về rồi đặt
quote và text lên mà cũng phải nghĩ sao?"* và *"phủ một lớp nền cùng màu với
nền của trang gốc, sau đó đặt text và quote của chúng ta lên"*.

Trước đó `_round_capture_source` chụp tối đa 3 trang và `break` ngay sau tấm ĐẦU
TIÊN — cả vòng chỉ bao giờ ra 1 ảnh, nên carousel 6 slide vẫn phải đi tìm ảnh
rời trên web (đường dài, dễ lạc đề). Tấm chụp khối lead lại thường NGANG, để
nguyên thì dính luật "ngang phải ghép đôi", thành tấm lẻ vô dụng.

Chạy:  venv/bin/python tests/test_chup_nhieu_bao.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import capture_page                                             # noqa: E402


def test_doc_mau_nen_moi_dinh_dang():
    assert capture_page._out_rgb("rgb(20, 20, 24)") == (20, 20, 24)
    assert capture_page._out_rgb("rgba(255, 255, 255, 0.9)") == (255, 255, 255)
    assert capture_page._out_rgb("#1a1a1a") == (26, 26, 26)
    assert capture_page._out_rgb("#fff") == (255, 255, 255)
    assert capture_page._out_rgb("") == (255, 255, 255), "khong doc duoc -> trang, khong nem"
    assert capture_page._out_rgb("chuoi la") == (255, 255, 255)


def _tam(tmp: Path, w, h, mau=(200, 30, 30)):
    from PIL import Image
    p = tmp / f"in_{w}x{h}.png"
    Image.new("RGB", (w, h), mau).save(p)
    return p


def test_anh_ngang_dem_nen_thanh_khung_4_5_dung_mot_minh():
    """Tấm chụp ngang 1200x500 -> 4:5, phần thừa tô đúng màu nền trang."""
    from PIL import Image
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        vao = _tam(tmp, 1200, 500)
        ra = tmp / "ra.png"
        w, h = capture_page.count_background(vao, ra, "rgb(18, 18, 20)")
        assert abs(w / h - 0.8) < 0.01, f"phai la 4:5, duoc {w}x{h}"
        im = Image.open(ra).convert("RGB")
        assert im.getpixel((5, 5)) == (18, 18, 20), "goc tren phai la MAU NEN cua trang"
        assert im.getpixel((w // 2, h - 5)) == (18, 18, 20), "day cung la mau nen"


def test_anh_qua_cao_duoc_thu_nho_vua_khung_khong_bi_cat():
    from PIL import Image
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        vao = _tam(tmp, 900, 3000)
        ra = tmp / "ra.png"
        w, h = capture_page.count_background(vao, ra, "#ffffff")
        assert abs(w / h - 0.8) < 0.01
        im = Image.open(ra).convert("RGB")
        # anh goc mau do phai con nguyen ven ben trong, khong bi cat mat
        assert im.getpixel((w // 2, h // 2)) == (200, 30, 30)


def test_vong_chup_giu_moi_tam_khong_dung_o_tam_dau():
    src = (ROOT / "prepare" / "fallback_rounds.py").read_text(encoding="utf-8")
    vong = src[src.index("def _round_capture_source"):src.index("def _round_concept")]
    assert "MAX_PAGE_CAPTURE" in vong
    assert "\n        break\n" not in vong, "khong duoc break sau tam dau — carousel can nhieu slide"
    assert "count_background" in vong, "phai dem nen cung mau trang truoc khi classify"
    assert "other_outlets_bing" in vong, "kho URL mong thi phai tu hoi them bao cung tin"


def test_dem_nen_chup_nguon_la_den_khong_lay_mau_trang_nguon():
    """Ong Chu 13/09/2026: dem bang mau trang cua trang nguon tao khoang trang
    lac long voi anh chinh (nhieu anh nguon nen toi/den), buoc carousel.py phu
    them lop mo (_layer_if_can) len tren de chu doc duoc - chinh la "vet nhat".
    Dem DEN co dinh: khop voi nen toi cua carousel va voi nen anh, khong con
    khoang trang, khong can lop phu."""
    src = (ROOT / "prepare" / "fallback_rounds.py").read_text(encoding="utf-8")
    vong = src[src.index("def _round_capture_source"):src.index("def _round_concept")]
    assert 'count_background(tam, moi, "#000000")' in vong, (
        "phai dem nen DEN co dinh, khong sample mau nen (thuong la trang) "
        "cua trang nguon")


def test_tran_chup_du_cho_mot_carousel():
    from prepare import fallback_rounds
    import carousel
    assert fallback_rounds.MAX_PAGE_CAPTURE >= carousel.MIN_SLIDE, \
        f"tran chup {fallback_rounds.MAX_PAGE_CAPTURE} < {carousel.MIN_SLIDE} slide toi thieu"


def test_chup_nguon_chay_TRUOC_tim_kiem_web():
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
