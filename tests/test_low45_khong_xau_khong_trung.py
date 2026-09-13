#!/usr/bin/env python3
"""LOW-45 (12/09/2026) — carousel dcgr "Moonshot nhắm 2 tỷ USD": Kite dùng CÙNG
MỘT ảnh (Bloomberg/Getty chụp App Store của Kimi K3) cho cả bìa lẫn thân, và
ảnh đó tự nó dưới chuẩn (chụp nghiêng, out-of-focus). Ông Chủ: *"xử lý đi. ko
ảnh xấu, ko ảnh trùng, bài có 8 slide thì tối thiểu phải có 3 hình thật."*

Đo trên máy chủ 12/09: hai vòng quét trang ĐỘC LẬP cùng chụp lại đúng ảnh hero
của bài TechCrunch — `_lay_anh_trang` (chuan_bi/browser.py, coi mọi `<figure>`
là ứng viên chart) và `_vong_chup_nguon` (LOW-22, tự tìm hero khung mobile) —
ra hai crop khác hash (dHash cách nhau 22 bit, KHÔNG bắt được bằng gần-giống)
nên `image_rules.check_duplicate` (md5 tuyệt đối) cũng không bắt được. Ba nhóm test,
mỗi nhóm FAIL trên code cũ:

  1. `_lay_anh_trang` không còn chụp `<figure>` thuần ảnh biên tập (chặn tại
     NGUỒN thay vì cố dò trùng SAU khi đã có hai crop khác nhau — dHash đo
     thật không đủ nhạy cho ca này).
  2. Câu hỏi con mắt MẶC ĐỊNH (đường "ảnh riêng của tin") có điều kiện rõ nét/
     không chụp góc nghiêng, đồng bộ với `anh_thuong_hieu`/`anh_khai_niem`.
  3. `kite_nop.giai_spec` chặn khi bộ nhiều slide dùng quá ít ảnh thật khác
     nhau (8 slide → tối thiểu 3), NHƯNG chỉ khi vòng tìm đủ nguồn.

Chạy:  venv/bin/python tests/test_low45_khong_xau_khong_trung.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import chuan_bi.browser as browser                             # noqa: E402
import chuan_bi.nhin as nhin                                   # noqa: E402
from tam import so_tam                                         # noqa: E402
from test_spec_kite import _cover, _statement, _hinh, _m, _chay  # noqa: E402


# --------------------------------------------------- 1. figure ảnh biên tập
def test_js_fig_bo_qua_figure_thuan_anh_khong_co_chart_ben_trong():
    """`<figure><img><figcaption>...</figcaption></figure>` (ảnh báo + credit,
    đúng khuôn TechCrunch bọc ảnh hero của Moonshot/Kimi) không còn được
    `_lay_anh_trang` coi là ứng viên chart — chỉ `<figure>` bọc canvas/svg/table
    (chart thật) mới còn được chụp."""
    js = browser._js_browser()["FIG"]
    assert "el.querySelector('canvas, svg, table')" in js, js
    i_figure_loop = js.index("for (const s of ['table', 'canvas', 'svg', 'figure'])")
    i_guard = js.index("el.querySelector('canvas, svg, table')")
    i_push = js.index("ra.push")
    assert i_figure_loop < i_guard < i_push, "cổng phải nằm TRONG vòng lặp, TRƯỚC khi push ứng viên"


# --------------------------------------------------- 2. câu hỏi mặc định rõ nét
def test_cau_hoi_mac_dinh_doi_ro_net_khong_goc_nghieng():
    """Trước 12/09/2026, nhánh mặc định (không `khai_niem`/`thuong_hieu`) —
    đường mà CẢ ảnh hero thật lẫn ảnh chụp lại trang đều đi qua — không hỏi gì
    về độ nét/góc chụp, chỉ hỏi "có liên quan bài không". Ảnh báo chụp nghiêng
    một màn hình (đúng ca Kimi K3) lọt qua dễ dàng vì rõ ràng đúng chủ đề.

    13/09/2026: cụm "chụp lại màn hình" gộp thành `image_rules.IMAGE_PHRASES_SCREENSHOT`
    dùng chung (xem `test_cum_chup_lai_man_hinh_dung_chung_moi_cau_hoi` bên dưới)."""
    import inspect
    src = inspect.getsource(nhin.mo_ta_anh)
    # Cụm phải nằm trong nhánh MẶC ĐỊNH (trước dòng gán `hoi` của khai_niem),
    # không phải chỉ tồn tại đâu đó trong tệp.
    i_hoi_mac_dinh = src.index('hoi = (f"Bai bao: \\"{tieu_de}\\".')
    i_khai_niem = src.index("elif khai_niem:")
    doan_mac_dinh = src[i_hoi_mac_dinh:i_khai_niem]
    assert "RO NET" in doan_mac_dinh, doan_mac_dinh
    assert "IMAGE_PHRASES_SCREENSHOT" in doan_mac_dinh, doan_mac_dinh


def test_cum_chup_lai_man_hinh_dung_chung_moi_cau_hoi():
    """LOW-45 (13/09/2026) — đúng ảnh Getty chụp nghiêng App Store của Kimi K3
    (đã chặn ở JS_FIG + _vong_chup_nguon) lọt qua LẦN THỨ BA qua một đường khác
    hẳn: nhánh "anh bối cảnh" của `anh_thuong_hieu.cau_hoi_vision` (dùng khi
    Commons/Wikidata rỗng, `_bao_thuong_hieu_rong` tìm ảnh qua báo) chưa từng
    có cụm này. Một hằng số dùng chung (`image_rules.IMAGE_PHRASES_SCREENSHOT`),
    mọi câu hỏi con mắt đều chèn — đóng cả lớp thay vì vá từng đường một."""
    import image_rules
    assert hasattr(image_rules, "IMAGE_PHRASES_SCREENSHOT")
    assert "man hinh" in image_rules.IMAGE_PHRASES_SCREENSHOT.lower()

    import anh_thuong_hieu as th
    for loai, th_dict in (("nguoi", {"hang": "X", "loai": "nguoi", "nguoi": "A", "vai": "CEO"}),
                         ("logo", {"hang": "X", "loai": "logo"}),
                         ("anh", {"hang": "X", "loai": "anh"})):
        c = th.cau_hoi_vision("tin gi do", th_dict)
        assert image_rules.IMAGE_PHRASES_SCREENSHOT in c, (loai, c)

    import anh_khai_niem as kn
    c = kn.cau_hoi_vision("tin gi do", "tu khoa x")
    assert image_rules.IMAGE_PHRASES_SCREENSHOT in c, c


# --------------------------------------------------- 3. tối thiểu ảnh thật/slide
def _bo_nhieu_anh(wd, so_anh: int, so_dung: int, so_slide: int = 8):
    """`so_anh` ảnh thật (lien_quan=True) trong `m["anh"]`, nhưng chỉ `so_dung`
    mã đầu tiên được đặt vào slide (mã còn lại coi như "tìm ra rồi mà không
    dùng" — đúng hiện trạng Moonshot: A1..A6 tìm ra, chỉ 1 ảnh (lặp lại) lên
    hình). Trả (slides, m)."""
    anh = [_hinh(wd, ma=f"H{i}", w=1200 + i, h=800) for i in range(1, so_anh + 1)]
    sl = [_cover(image="H1", caption="x · via AA")]
    sl += [_statement(title=f"Ý {i}", image=(f"H{i}" if i <= so_dung else None),
                      caption=("x · via AA" if i <= so_dung else None))
           for i in range(2, so_slide + 1)]
    # `_statement` không nhận None cho caption/image gọn gàng — dọn lại các
    # slide không có ảnh (bỏ hẳn khoá thay vì giữ None, giống decorator thật).
    for s in sl:
        if s.get("image") is None:
            s.pop("image", None); s.pop("caption", None)
    return sl, _m(wd, anh)


def test_8_slide_1_anh_lap_lai_thi_chan_khi_du_nguon():
    """Đúng ca Moonshot/Kimi K3: 8 slide, engine tìm ra 6 ảnh thật (đủ nguồn),
    nhưng chỉ 1 mã (H1) lên slide, lặp lại — phải CHẶN CỨNG."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_hinh(wd, ma=f"H{i}", w=1200, h=800) for i in range(1, 7)]      # 6 ảnh thật
        sl = [_cover(image="H1", caption="x · via AA")]
        sl += [_statement(title=f"Ý {i}") for i in range(2, 5)]
        sl.append(_statement(title="Kimi K3 lên kệ", image="H1", caption="x · via AA"))  # LẶP LẠI H1
        sl += [_statement(title=f"Ý {i}") for i in range(6, 9)]
        _r, loi, _canh = _chay(sl, _m(wd, anh), wd)
        assert any("tối thiểu" in d and "3" in d and "H1" in d for d in loi), loi


def test_8_slide_du_3_anh_khac_nhau_thi_qua():
    """Cùng 8 slide, cùng nguồn dồi dào, nhưng lần này 3 mã KHÁC NHAU lên slide
    — không còn gì để chặn ở cổng này."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl, m = _bo_nhieu_anh(wd, so_anh=6, so_dung=3, so_slide=8)
        _r, loi, _canh = _chay(sl, m, wd)
        assert not any("tối thiểu" in d and "hình thật" in d for d in loi), loi


def test_6_slide_thieu_nguon_thi_chi_canh_bao_khong_chan():
    """6 slide cần tối thiểu 2 ảnh (ceil(6/3)), nhưng vòng tìm CHỈ ra được 1 —
    không đủ nguồn để đòi, nên chỉ cảnh báo, không chặn cứng (Kite không thể
    dùng ảnh không tồn tại)."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl, m = _bo_nhieu_anh(wd, so_anh=1, so_dung=1, so_slide=6)
        _r, loi, canh = _chay(sl, m, wd)
        assert not any("tối thiểu" in d and "hình thật" in d for d in loi), loi
        assert any("tối thiểu" in c and "không đủ nguồn" in c for c in canh), canh


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
