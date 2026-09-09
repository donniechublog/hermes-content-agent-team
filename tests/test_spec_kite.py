#!/usr/bin/env python3
"""Cong chan spec carousel kien thuc cua Kite (`kite_nop.giai_spec`).

Khac Dre/Ethan: Kite ve vector, anh that la tuy chon. Cong nay kiem TRUOC khi
render_edu mo Chromium — bao som thi vai sua mot vong thay vi cho ~20s roi
nhan KeyError. 134 dong, va chi co MOT test truoc 07/09/2026 (khong ep dung
anh chua nhin).

Chay:  venv/bin/python tests/test_spec_kite.py
"""
import contextlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tam import so_tam  # noqa: E402
from test_spec_dre import _co, _ve  # noqa: E402


def _cover(**k):
    d = {"kind": "cover", "eyebrow": "MODEL", "title": "Nemotron mở kho",
         "standfirst": "Nvidia mở mô hình cho mọi nhà phát triển."}
    d.update(k)
    return d


def _statement(**k):
    d = {"kind": "statement", "eyebrow": "SỐ", "title": "Ba con số",
         "standfirst": "Những gì đáng nhớ.",
         "cards": [{"num": "340B", "text": "tham số"}, {"num": "86,2", "text": "điểm MMLU"}]}
    d.update(k)
    return d


def _du():
    """Sau slide hop le toan chu (khong image): cover + 5 statement."""
    return [_cover()] + [_statement(title=f"Ý {i}") for i in range(2, 7)]


def _m(wd, anh=(), **k):
    d = {"anh": list(anh), "brand": "donniechublog", "title": "Nemotron mở kho",
         "draft_id": "tin-thu", "link": "https://vi.du/bai",
         "chu_bai": "Nemotron có 340 tỷ tham số, đạt 86,2 điểm MMLU.", "tu_lieu": {}}
    d.update(k)
    return d


def _hinh(wd, ma="H1", w=1200, h=800, lien_quan=True, **k):
    goc = wd / "goc" / f"{ma}.png"
    goc.parent.mkdir(parents=True, exist_ok=True)
    _ve(w, h).save(goc)
    a = {"ma": ma, "goc": str(goc), "w": w, "h": h, "ti_le": round(w / h, 2),
         "loai": "chart", "lien_quan": lien_quan, "mien": "x.com", "tu": "x",
         "ghi_chu": [], "mat": 0, "mo_ta": "bảng benchmark"}
    a.update(k)
    return a


@contextlib.contextmanager
def _khong_soi_mat():
    """YuNet (dem mat) can tep model va ton thoi gian; cong mat nguoi cua Kite
    chi CANH BAO nen tat no trong test, TRA LAI sau."""
    import luat_anh
    cu = luat_anh.kiem_mat_nguoi
    luat_anh.kiem_mat_nguoi = lambda nhan, path, nhan_vat=None: ([], [])
    try:
        yield
    finally:
        luat_anh.kiem_mat_nguoi = cu


def _chay(slides, m, wd, **spec):
    import kite_nop
    with _khong_soi_mat():
        return kite_nop.giai_spec({"slides": slides, **spec}, m, Path(wd))


# ---------------------------------------------------------------- hop le
def test_bo_sau_slide_toan_chu_khong_loi():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        ra, loi, _c = _chay(_du(), _m(wd), wd)
        assert loi == [], loi
        assert len(ra["slides"]) == 6
        assert ra["brand"] == "donniechublog" and ra["section"] == "RESEARCH"


def test_brand_dcgr_ra_handle_hien_thi():
    """Masthead in CHU brand: dcgr -> dcgr.tech, khong phai slug (05/09/2026)."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        ra, loi, _c = _chay(_du(), _m(wd, brand="dcgr"), wd)
        assert loi == [], loi
        assert ra["brand"] != "dcgr" and "dcgr" in ra["brand"], ra["brand"]


# ---------------------------------------------------------------- khung
def test_so_slide_ngoai_6_10_bao():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        _r, loi, _c = _chay(_du()[:4], _m(wd), wd)
        assert _co(loi, "4 slide", "6..10"), loi
        _r, loi, _c = _chay(_du() + [_statement()] * 5, _m(wd), wd)
        assert _co(loi, "11 slide"), loi


def test_slide_dau_phai_la_cover():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        _r, loi, _c = _chay([_statement()] + _du()[1:], _m(wd), wd)
        assert _co(loi, "slide 1", "cover"), loi


def test_kind_la_thi_liet_ke_kind_hop_le():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl = _du(); sl[2] = {"kind": "meme", "title": "x"}
        _r, loi, _c = _chay(sl, _m(wd), wd)
        assert _co(loi, "slide 3", "meme", "cover/statement"), loi


def test_thieu_truong_bat_buoc_theo_kind():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl = _du(); sl[1] = _statement(standfirst="", eyebrow=None)
        _r, loi, _c = _chay(sl, _m(wd), wd)
        assert _co(loi, "slide 2", "thiếu", "standfirst") and _co(loi, "eyebrow"), loi


def test_khoa_long_thieu_bat_truoc_khi_mo_chromium():
    """cards[].num thieu -> renderer KeyError SAU khi da mo Chromium."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl = _du(); sl[1] = _statement(cards=[{"text": "khong co num"}])
        _r, loi, _c = _chay(sl, _m(wd), wd)
        assert _co(loi, "slide 2", "num"), loi


def test_theme_va_hero_la_thi_bao_kem_lua_chon():
    import render_edu
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        _r, loi, _c = _chay(_du(), _m(wd), wd, theme="neon-xyz", hero="rong")
        assert _co(loi, "theme", "neon-xyz") and _co(loi, "hero", "rong"), loi
        th = sorted(render_edu.THEMES)[0]
        ra, loi2, _c = _chay(_du(), _m(wd), wd, theme=th)
        assert loi2 == [] and ra["theme"] == th


# ---------------------------------------------------------------- noi dung
def test_dan_nguon_phai_ghi_via():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl = _du(); sl[3] = _statement(standfirst="Theo nguồn: Nvidia.")
        _r, loi, _c = _chay(sl, _m(wd), wd)
        assert _co(loi, "slide 4", "via"), loi


def test_dan_nguon_bat_ca_dang_khong_co_theo():
    """"Nguồn: X" (khong co "Theo" dau) van la dan nguon sai dinh dang."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl = _du(); sl[3] = _statement(standfirst="Nguồn: Nvidia công bố hôm qua.")
        _r, loi, _c = _chay(sl, _m(wd), wd)
        assert _co(loi, "slide 4", "via"), loi


def test_standfirst_noi_ve_nguon_cung_khong_bi_bat_nham():
    """b403ca4 (08/09/2026) thu hep cong nay lai vi no da bat nham "Nguồn cung"/
    "Khan hiếm nguồn cung" (cum tu thuong, chuoi cung ung) trong hai job Kite
    doc lap cung ngay — nhung fix do KHONG co test bao ve, nen khi standfirst
    duoc dua tro lai vao cong nay (test tren) phai chan lai dung false positive
    do, khong chi chan lai lỗi that."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl = _du(); sl[3] = _statement(standfirst="Khan hiếm nguồn cung chip toàn cầu.")
        _r, loi, _c = _chay(sl, _m(wd), wd)
        assert not _co(loi, "via"), loi


def test_chu_dai_chi_canh_bao():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl = _du(); sl[2] = _statement(title="T" * 80)
        _r, loi, canh = _chay(sl, _m(wd), wd)
        assert loi == [], loi
        assert _co(canh, "slide 3", "title", "80"), canh


def test_bars_can_2_den_6_cot_va_value_phai_la_so():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        bars = {"kind": "bars", "eyebrow": "SO", "title": "So sánh", "standfirst": "x",
                "caption": "via AA", "bars": [{"label": "A", "value": "1.200"}]}
        sl = _du(); sl[4] = bars
        _r, loi, _c = _chay(sl, _m(wd), wd)
        assert _co(loi, "slide 5", "2..6"), loi
        bars["bars"] = [{"label": "A", "value": "1.200"}, {"label": "B", "value": "nhiều"}]
        _r, loi2, _c = _chay(sl, _m(wd), wd)
        assert _co(loi2, "slide 5", "cột 2", "số thật"), loi2
        bars["bars"] = [{"label": "A", "value": "1.200"}, {"label": "B", "value": "900"}]
        assert _chay(sl, _m(wd), wd)[1] == []


# ---------------------------------------------------------------- hinh that
def test_co_hinh_that_da_nhin_ma_khong_dung_thi_chan():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        _r, loi, _c = _chay(_du(), _m(wd, [_hinh(wd)]), wd)
        assert _co(loi, "BẮT BUỘC dùng ít nhất một", "H1"), loi


# ---- tin CHUYEN TU Dre/Ethan vi thieu anh (Ong Chu 09/09/2026) -------------
def _figure(ma, **k):
    d = {"kind": "figure", "eyebrow": "SỐ LIỆU", "title": "Bảng điểm",
         "standfirst": "Kết quả đo trên bộ chuẩn.", "image": ma,
         "caption": "Bảng trong bài · via nguoi-dua"}
    d.update(k)
    return d


def test_chuyen_tu_vai_doc_img_json():
    """Nút "Gửi Kite" của Ông Chủ chỉ ghi `chuyen_tu` vào img.json, xong.json
    không có — đọc nhầm chỗ là cổng dưới không bao giờ bật."""
    import anh_chuan_bi as cb
    import kite_chuan_bi as kb
    import json as _j
    with tempfile.TemporaryDirectory() as t:
        cu, cb.DRAFTS = cb.DRAFTS, Path(t)
        try:
            assert kb.chuyen_tu_vai({"draft_id": "d1"}) == ""
            assert kb.chuyen_tu_vai({"draft_id": "d1", "chuyen_kite": "t_9"}) == "vai ảnh"
            (Path(t) / "d1.img.json").write_text(_j.dumps({"chuyen_tu": "carousel"}), encoding="utf-8")
            assert kb.chuyen_tu_vai({"draft_id": "d1"}) == "Dre"
            (Path(t) / "d1.img.json").write_text(_j.dumps({"chuyen_tu": "designer"}), encoding="utf-8")
            assert kb.chuyen_tu_vai({"draft_id": "d1"}) == "Ethan"
        finally:
            cb.DRAFTS = cu


def test_chuyen_kite_doi_dung_DU_ma_hinh():
    """Ông Chủ 09/09/2026: tin pass sang Kite vì thiếu ảnh thì Kite vẫn phải
    dùng những hình đó. Cổng "ít nhất một" cũ cho phép bỏ tấm thứ hai."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_hinh(wd, ma="H1"), _hinh(wd, ma="H2", w=1100, h=900)]
        sl = _du(); sl[1] = _figure("H1")
        _r, loi, _c = _chay(sl, _m(wd, anh, chuyen_kite="t_9"), wd)
        assert _co(loi, "H2", "phải vào bộ"), loi
        sl[2] = _figure("H2", title="Bảng hai")
        _r, loi2, _c = _chay(sl, _m(wd, anh, chuyen_kite="t_9"), wd)
        assert not _co(loi2, "phải vào bộ"), loi2


def test_chuyen_kite_khong_cho_hinh_nam_moi_o_bia():
    """Một tấm đặt lên bìa rồi vẽ vector cả thân là đúng cái lỗi khiến tin phải
    chuyển sang Kite."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_hinh(wd, ma="H1")]
        sl = _du()
        sl[0] = _cover(image="H1", caption="Bảng trong bài · via nguoi-dua")
        _r, loi, _c = _chay(sl, _m(wd, anh, chuyen_kite="t_9"), wd)
        assert _co(loi, "chỉ nằm ở BÌA"), loi
        sl[1] = _figure("H1")            # thêm ở thân -> qua
        _r, loi2, _c = _chay(sl, _m(wd, anh, chuyen_kite="t_9"), wd)
        assert not _co(loi2, "chỉ nằm ở BÌA"), loi2


def test_chuyen_kite_bo_trang_thi_bao_du_loi_mot_vong():
    """Bộ không dùng tấm nào: phải nói CẢ "thiếu mã nào" ngay vòng này, và
    KHÔNG nói "chỉ nằm ở bìa" (sai, vì có nằm ở đâu đâu)."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_hinh(wd, ma="H1"), _hinh(wd, ma="H2", w=1100, h=900)]
        _r, loi, _c = _chay(_du(), _m(wd, anh, chuyen_kite="t_9"), wd)
        assert _co(loi, "BẮT BUỘC dùng ít nhất một"), loi
        assert _co(loi, "H1", "H2", "phải vào bộ"), loi
        assert not _co(loi, "chỉ nằm ở BÌA"), loi


def test_khong_chuyen_kite_thi_van_chi_doi_mot_tam():
    """Tin Kite bình thường (không phải hàng chuyển sang) giữ luật cũ."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_hinh(wd, ma="H1"), _hinh(wd, ma="H2", w=1100, h=900)]
        sl = _du(); sl[1] = _figure("H1")
        _r, loi, _c = _chay(sl, _m(wd, anh), wd)
        assert not _co(loi, "phải vào bộ"), loi
        assert not _co(loi, "chỉ nằm ở BÌA"), loi


def test_hinh_chua_nhin_thi_chi_goi_y():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        _r, loi, canh = _chay(_du(), _m(wd, [_hinh(wd, lien_quan=None)]), wd)
        assert not _co(loi, "BẮT BUỘC"), loi
        assert _co(canh, "chưa nhìn", "H1"), canh


def test_hinh_qua_nho_chua_nhin_khong_bi_bao_gia():
    """kite_nop tinh "chua nhin" tu `hinh` (= kb.hinh_that(m), da loc >= 800px),
    KHONG doc thang m["chua_nhin"] cap manifest (tinh tren TOAN BO anh, xem
    chuan_bi/manifest.py) — anh <800px khong bao gio la candidate cua Kite nen
    "chua nhin" cua no la nhieu, khong phai tin. Neu sau nay co ai "gon" lai
    thanh doc thang khoa manifest thi test nay do ngay: NHO se bi bao gia."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        nho = _hinh(wd, ma="NHO", w=400, h=300, lien_quan=None)
        # Gia lap dung khoa "chua_nhin" cap manifest nhu chuan_bi/manifest.py
        # se ghi (tinh tren TOAN BO anh, khong loc kich thuoc) — neu kite_nop
        # doc thang khoa nay thay vi tinh tu `hinh`, NHO se lot vao canh bao.
        _r, loi, canh = _chay(_du(), _m(wd, [nho], chua_nhin=["NHO"]), wd)
        assert not _co(canh, "chưa nhìn", "NHO"), canh


def test_image_phai_la_ma_hinh_that_va_co_caption():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl = _du(); sl[1] = _statement(image="H9")
        _r, loi, _c = _chay(sl, _m(wd, [_hinh(wd)]), wd)
        assert _co(loi, "slide 2", "H9", "không phải mã hình thật"), loi
        sl[1] = _statement(image="H1")
        _r, loi2, _c = _chay(sl, _m(wd, [_hinh(wd)]), wd)
        assert _co(loi2, "slide 2", "caption"), loi2


def test_image_hop_le_doi_thanh_duong_dan_tep():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        h = _hinh(wd)
        sl = _du(); sl[1] = _statement(image="H1", caption="Bảng benchmark · via AA")
        ra, loi, _c = _chay(sl, _m(wd, [h]), wd)
        assert loi == [], loi
        assert ra["slides"][1]["image"] == h["goc"]


def test_hinh_da_dung_o_tin_khac_thi_chan():
    """Dre va Ethan co cong nay tu dau; Kite thi khong — bang benchmark Dre dung
    hom qua van len bo cua Kite hom nay (06/09/2026)."""
    import luat_anh
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        h = _hinh(wd)
        luat_anh.ghi_da_dung(h["goc"], "tin-khac", "carousel", "https://vi.du/khac")
        sl = _du(); sl[1] = _statement(image="H1", caption="x · via AA")
        _r, loi, _c = _chay(sl, _m(wd, [h]), wd)
        assert _co(loi, "slide 2", "TRUNG anh da dung"), loi


def test_cung_mot_hinh_hai_slide_bi_chan():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        h = _hinh(wd)
        sl = _du()
        sl[1] = _statement(image="H1", caption="x · via AA")
        sl[2] = _statement(image="H1", caption="y · via AA")
        _r, loi, _c = _chay(sl, _m(wd, [h]), wd)
        assert _co(loi, "slide 3"), loi


def test_so_tren_slide_khong_co_trong_tu_lieu_thi_canh_bao():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl = _du(); sl[1] = _statement(standfirst="Đạt 97,3 điểm.")
        _r, loi, canh = _chay(sl, _m(wd), wd)
        assert loi == [], loi
        assert any("97,3" in c for c in canh), canh


if __name__ == "__main__":
    ham = [v for k, v in list(globals().items()) if k.startswith("test_")]
    loi = 0
    for h in ham:
        try:
            h()
            print(f"OK   {h.__name__}")
        except AssertionError as e:
            loi += 1
            print(f"FAIL {h.__name__}: {e}")
    print(f"\n{len(ham) - loi}/{len(ham)} test qua")
    sys.exit(1 if loi else 0)
