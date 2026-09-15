#!/usr/bin/env python3
"""Cong chan spec carousel kien thuc cua Kite (`kite_submit.resolve_spec`).

Khac Dre/Ethan: Kite ve vector, anh that la tuy chon. Cong nay kiem TRUOC khi
render_edu mo Chromium — bao som thi vai sua mot vong thay vi cho ~20s roi
nhan KeyError. 134 dong, va chi co MOT test truoc 07/09/2026 (khong ep dung
anh chua nhin).

Chay:  venv/bin/python tests/test_spec_kite.py
"""
import contextlib
import pathlib
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


def _du_bia(wd, **mk):
    """Bộ HỢP LỆ tối thiểu SAU 10/09/2026: bìa BẮT BUỘC có ảnh thật (§1.2f, Ông
    Chủ: "không chấp nhận việc dùng vector ở hero slide"), nên `_du()` toàn chữ
    không còn là bộ hợp lệ. Trả (slides, m)."""
    sl = _du()
    sl[0] = _cover(image="B1", caption="Bảng trong bài · via AA")
    return sl, _m(wd, [_hinh(wd, ma="B1")], **mk)


@contextlib.contextmanager
def _khong_soi_mat():
    """YuNet (dem mat) can tep model va ton thoi gian; cong mat nguoi cua Kite
    chi CANH BAO nen tat no trong test, TRA LAI sau."""
    import image_rules
    cu = image_rules.check_unnamed_face
    image_rules.check_unnamed_face = lambda nhan, path, nhan_vat=None: ([], [])
    try:
        yield
    finally:
        image_rules.check_unnamed_face = cu


def _chay(slides, m, wd, **spec):
    import kite_submit
    with _khong_soi_mat():
        return kite_submit.resolve_spec({"slides": slides, **spec}, m, Path(wd))


# ---------------------------------------------------------------- hop le
def test_bo_sau_slide_bia_co_anh_khong_loi():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl, m = _du_bia(wd)
        ra, loi, _c = _chay(sl, m, wd)
        assert loi == [], loi
        assert len(ra["slides"]) == 6
        assert ra["brand"] == "donniechublog" and ra["section"] == "RESEARCH"


def test_bo_toan_chu_bi_chan_vi_bia_ve_hero_vector():
    """Ông Chủ 10/09/2026: "không chấp nhận việc dùng vector ở hero slide, thời
    đại này không có ảnh gì mà không thể tìm được". Bộ toàn chữ TỪNG là bộ hợp
    lệ (test cũ `..._toan_chu_khong_loi`); nay bìa không ảnh là chặn, kể cả khi
    engine giao 0 hình — im lặng vẽ vector là giấu một thất bại của vòng tìm
    ảnh dưới một bộ slide trông như thật."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        _r, loi, _c = _chay(_du(), _m(wd), wd)
        assert _co(loi, "bìa", "vòng tìm ảnh về trắng", "KHÔNG được vẽ"), loi
        # Nuoc di dau tien la TIM LAI, khong phai bao hong (Ong Chu 10/09/2026:
        # "ko co ly gi ma ko tim duoc anh de bao hong").
        assert _co(loi, "đã tự tìm lại"), loi
        assert _co(loi, "--lam-moi"), loi
        assert _co(loi, "kanban_block"), loi


def test_brand_dcgr_ra_handle_hien_thi():
    """Masthead in CHU brand: dcgr -> dcgr.tech, khong phai slug (05/09/2026)."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl, m = _du_bia(wd, brand="dcgr")
        ra, loi, _c = _chay(sl, m, wd)
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
        sl, m = _du_bia(wd)
        _r, loi, _c = _chay(sl, m, wd, theme="neon-xyz", hero="rong")
        assert _co(loi, "theme", "neon-xyz") and _co(loi, "hero", "rong"), loi
        th = sorted(render_edu.THEMES)[0]
        ra, loi2, _c = _chay(sl, m, wd, theme=th)
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
        sl, m = _du_bia(wd)
        sl[2] = _statement(title="T" * 80)
        _r, loi, canh = _chay(sl, m, wd)
        assert loi == [], loi
        assert _co(canh, "slide 3", "title", "80"), canh


def test_ma_anh_khong_bi_bao_la_so_bia():
    """Ong Chu 15/09/2026: `kite_submit.py` bao canh bao "số trên slide KHÔNG
    thấy trong tư liệu: 13" cho mot tin ma "13" chi la HAU TO cua ma anh noi
    bo ("A13") trong truong `image`, khong he xuat hien tren slide that. Truoc
    day `chu` quet ca sl.values() nen an ca ma anh vao — gio chi quet cac
    truong CHU HIEN THI (eyebrow/title/standfirst/callout/caption)."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl = _du()
        sl[0] = _cover(image="A13", caption="Bảng trong bài · via AA")
        m = _m(wd, [_hinh(wd, ma="A13")])
        _r, _loi, canh = _chay(sl, m, wd)
        assert not _co(canh, "KHÔNG thấy trong tư liệu"), canh


def test_so_bia_that_van_bi_canh_bao():
    """Doi chung voi test tren: thu hep truong quet KHONG duoc lam mat luon
    cong that — so bia gia (khong trong tu lieu) tren `title` van phai bi bat."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl = _du()
        sl[0] = _cover(title="Doanh thu tăng 999%", image="B1",
                       caption="Bảng trong bài · via AA")
        m = _m(wd, [_hinh(wd, ma="B1")])
        _r, _loi, canh = _chay(sl, m, wd)
        assert _co(canh, "KHÔNG thấy trong tư liệu", "999"), canh


def test_bars_can_2_den_6_cot_va_value_phai_la_so():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        bars = {"kind": "bars", "eyebrow": "SO", "title": "So sánh", "standfirst": "x",
                "caption": "via AA", "bars": [{"label": "A", "value": "1.200"}]}
        sl, m = _du_bia(wd)
        sl[4] = bars
        _r, loi, _c = _chay(sl, m, wd)
        assert _co(loi, "slide 5", "2..6"), loi
        bars["bars"] = [{"label": "A", "value": "1.200"}, {"label": "B", "value": "nhiều"}]
        _r, loi2, _c = _chay(sl, m, wd)
        assert _co(loi2, "slide 5", "cột 2", "số thật"), loi2
        bars["bars"] = [{"label": "A", "value": "1.200"}, {"label": "B", "value": "900"}]
        assert _chay(sl, m, wd)[1] == []


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
    import image_prepare as cb
    import kite_prepare as kb
    import json as _j
    with tempfile.TemporaryDirectory() as t:
        cu, cb.DRAFTS = cb.DRAFTS, Path(t)
        try:
            assert kb.transfer_from_role({"draft_id": "d1"}) == ""
            assert kb.transfer_from_role({"draft_id": "d1", "chuyen_kite": "t_9"}) == "vai ảnh"
            (Path(t) / "d1.img.json").write_text(_j.dumps({"chuyen_tu": "dre"}), encoding="utf-8")
            assert kb.transfer_from_role({"draft_id": "d1"}) == "Dre"
            (Path(t) / "d1.img.json").write_text(_j.dumps({"chuyen_tu": "ethan"}), encoding="utf-8")
            assert kb.transfer_from_role({"draft_id": "d1"}) == "Ethan"
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
    """Đặt MỘT tấm lên bìa rồi vẽ vector cả thân, trong khi engine tìm được HAI
    tấm — đúng cái lỗi khiến tin phải chuyển sang Kite (Ông Chủ 09/09/2026).

    Đo bằng hai tấm chứ không phải một: từ 10/09/2026 tin chỉ có ĐÚNG MỘT tấm
    thì tấm đó lên bìa là đúng, không còn là lỗi (xem
    `test_chuyen_kite_chi_mot_tam_thi_BIA_thang`)."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_hinh(wd, ma="H1"), _hinh(wd, ma="H2", w=1100, h=900)]
        sl = _du()
        sl[0] = _cover(image="H1", caption="Bảng trong bài · via nguoi-dua")
        _r, loi, _c = _chay(sl, _m(wd, anh, chuyen_kite="t_9"), wd)
        assert _co(loi, "chỉ nằm ở BÌA"), loi
        sl[1] = _figure("H2", title="Bảng hai")      # thêm ở thân -> qua
        _r, loi2, _c = _chay(sl, _m(wd, anh, chuyen_kite="t_9"), wd)
        assert loi2 == [], loi2


def test_chuyen_kite_bo_trang_thi_bao_du_loi_mot_vong():
    """Bộ không dùng tấm nào: phải nói CẢ "thiếu mã nào" ngay vòng này, và
    KHÔNG nói "chỉ nằm ở bìa" (sai, vì có nằm ở đâu đâu)."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_hinh(wd, ma="H1"), _hinh(wd, ma="H2", w=1100, h=900)]
        _r, loi, _c = _chay(_du(), _m(wd, anh, chuyen_kite="t_9"), wd)
        assert _co(loi, "BẮT BUỘC dùng ít nhất một"), loi
        # H1 la hero -> cong bia goi ten no; H2 la phan con lai -> cong than.
        assert _co(loi, "bìa", "H1"), loi
        assert _co(loi, "H2", "phải vào bộ"), loi
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


# ---- BIA phai dung anh that (Ong Chu 10/09/2026) --------------------------
def test_bia_ve_vector_trong_khi_co_hinh_that_thi_chan():
    """Ông Chủ 10/09/2026: "kite vẫn dùng vector làm hero, chưa sử dụng ảnh".
    Cổng "ít nhất một" cũ cho phép nhét hết ảnh vào `figure` thân rồi vẽ sơ đồ
    lên bìa."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl = _du(); sl[1] = _figure("H1")
        _r, loi, _c = _chay(sl, _m(wd, [_hinh(wd)]), wd)
        assert _co(loi, "bìa", "hero vector", "H1"), loi


def test_bia_co_anh_that_thi_qua():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl = _du()
        sl[0] = _cover(image="H1", caption="Bảng trong bài · via AA")
        _r, loi, _c = _chay(sl, _m(wd, [_hinh(wd)]), wd)
        assert loi == [], loi


def test_hinh_chua_nhin_khong_bi_ep_len_bia():
    """Vision tắt thì mọi ảnh `lien_quan=None` — ép lúc đó là đẩy banner lên
    bìa, cùng bài học với `figure_right_use`. Nhưng từ 10/09/2026 cũng KHÔNG được
    lặng lẽ vẽ vector: đây là hỏng khâu vận hành, phải nói ra thứ cần bật."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        _r, loi, _c = _chay(_du(), _m(wd, [_hinh(wd, lien_quan=None)]), wd)
        assert _co(loi, "vision CHƯA NHÌN", "H1"), loi
        # KHONG duoc chi dinh dat H1 len bia — chua ai nhin no
        assert not _co(loi, 'đặt `"image": "H1"'), loi


def test_hinh_paper_van_len_bia_du_vision_tat():
    """Hình paper bóc thẳng từ PDF nên không thể là quảng cáo — IMAGE_RULES §1.4
    "Figure 1 là hero" không phụ thuộc vision."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        h = _hinh(wd, lien_quan=None, paper_hinh="Figure 1")
        _r, loi, _c = _chay(_du(), _m(wd, [h]), wd)
        assert _co(loi, "hero vector", "H1"), loi


def test_chuyen_kite_chi_mot_tam_thi_BIA_thang():
    """Hai cổng không được đá nhau: tin chuyển sang Kite đòi hình thật nằm ở
    slide THÂN (09/09), mà cùng một ảnh không lên được hai slide (`check_duplicate`).

    ĐẢO NGƯỢC 10/09/2026 — Ông Chủ: "không chấp nhận việc dùng vector ở hero
    slide". Bản trước cho THÂN thắng và bìa vẽ vector. Nay BÌA thắng: đòi của
    §1.2e sinh ra từ ca NHIỀU tấm mà Kite chỉ dùng một; còn đúng một tấm thì nó
    VẪN được dùng, chỉ là dùng ở bìa. `figure_right_use` trừ tấm ấy ra nên thân
    không đòi nữa."""
    import kite_prepare as kb
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        m = _m(wd, [_hinh(wd)], chuyen_kite="t_9")
        assert kb.figure_hero(m)["ma"] == "H1"
        assert kb.figure_right_use(m) == [], kb.figure_right_use(m)
        sl = _du()
        sl[0] = _cover(image="H1", caption="Bảng trong bài · via AA")
        assert _chay(sl, m, wd)[1] == [], _chay(sl, m, wd)[1]
        # ...va de no o THAN roi ve vector bia thi CHAN (khong con duong vector)
        sl2 = _du(); sl2[1] = _figure("H1")
        assert _co(_chay(sl2, m, wd)[1], "bìa", "hero vector", "H1")


def test_hero_khong_bao_gio_None_khi_con_mot_anh_da_nhin():
    """Bất biến của §1.2f sau 10/09/2026: còn một tấm ĐÃ NHÌN là còn bìa ảnh.
    `figure_hero` chỉ trả None khi engine giao 0 hình dùng được — mọi đường khác
    dẫn tới hero vector đều đã bị bịt."""
    import kite_prepare as kb
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        r1 = _hinh(wd, ma="R1")
        kn = _khai_niem(wd, ma="K1", w=1100, h=900)
        for ten, anh, mk in [
            ("1 rieng", [r1], {}),
            ("1 rieng, CHUYEN sang", [r1], {"chuyen_kite": "t_9"}),
            ("1 khai niem", [kn], {}),
            ("1 khai niem, CHUYEN sang", [kn], {"chuyen_kite": "t_9"}),
            ("rieng + khai niem, CHUYEN sang", [r1, kn], {"chuyen_kite": "t_9"}),
        ]:
            assert kb.figure_hero(_m(wd, anh, **mk)) is not None, ten
        # chi con MOT duong ra None: engine giao 0 hinh
        assert kb.figure_hero(_m(wd)) is None
        assert kb.figure_hero(_m(wd, [_hinh(wd, ma="X1", lien_quan=None)])) is None


def test_hero_uu_tien_paper_roi_anh_rieng_roi_anh_bu():
    """IMAGE_RULES §1.2c/§1.2d: gợi ý bìa xếp SAU mọi ảnh riêng của tin."""
    import kite_prepare as kb
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        kn = _hinh(wd, ma="K1", khai_niem={"tu_khoa": "Japan flag"})
        th = _hinh(wd, ma="T1", thuong_hieu={"loai": "anh", "hang": "Nvidia"})
        rieng = _hinh(wd, ma="R1")
        paper = _hinh(wd, ma="P1", paper_hinh="Figure 1")
        assert kb.figure_hero(_m(wd, [kn]))["ma"] == "K1"
        assert kb.figure_hero(_m(wd, [kn, th]))["ma"] == "T1"
        assert kb.figure_hero(_m(wd, [kn, th, rieng]))["ma"] == "R1"
        assert kb.figure_hero(_m(wd, [kn, th, rieng, paper]))["ma"] == "P1"
        assert kb.figure_hero(_m(wd)) is None


# ---- KITE PHAI TU TIM LAI ANH, khong thua ke that bai cua vai cu ----------
def test_kite_tu_tim_lai_khi_thua_ke_bo_anh_khong_co_bia():
    """Ông Chủ 10/09/2026: *"Dre tìm được ảnh đúng, nên kỹ năng tìm ảnh đó dùng
    được. ko có lý gì mà ko tìm được ảnh để báo hỏng"*.

    `image_prepare.run` trả thẳng `xong.json` cũ khi tệp đã có, và task body
    giao cho Kite chạy `kite_prepare.py <id>` KHÔNG kèm `--lam-moi` — nên Kite
    đọc lại đúng kết quả đã thất bại của vai cũ, vòng tìm ảnh không bao giờ
    chạy lần nữa. Hai vai dừng ở hai ngưỡng khác nhau: vai cũ cần ~5 ảnh, Kite
    chỉ cần MỘT tấm lên bìa."""
    import kite_prepare as kb
    import image_prepare as cb
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        goi = []
        sau = _m(wd, [_hinh(wd, ma="K9")])          # vong tim lai ra duoc mot tam

        def gia_chay(draft_id, lam_moi, khong_browser, cho, sau_chuan_bi=None):
            goi.append(lam_moi)
            return sau, wd, {}

        cu, cb.run = cb.run, gia_chay
        try:
            # 1) thua ke bo TRANG -> phai chay lai, va chay voi lam_moi=True
            m2, _w = kb.ensure_has_cover("d1", _m(wd), wd, False, 30)
            assert goi == [True], goi
            assert kb.figure_hero(m2)["ma"] == "K9"
            # 2) da co tam len bia -> KHONG dung toi engine lan nua
            goi.clear()
            kb.ensure_has_cover("d1", _m(wd, [_hinh(wd, ma="R1")]), wd, False, 30)
            assert goi == [], goi
            # 3) chinh vai da goi --lam-moi -> khong de quy them mot vong nua
            goi.clear()
            kb.ensure_has_cover("d1", _m(wd), wd, False, 30, da_lam_moi=True)
            assert goi == [], goi
        finally:
            cb.run = cu


def test_task_body_khong_con_bao_kite_ve_vector_hoan_toan():
    """Câu "ve vector hoan toan" trong task body là CHÍNH HỆ THỐNG bảo vai làm
    đúng thứ §1.2f cấm: vai đọc body TRƯỚC khi chạy `kite_prepare.py`, nên nó
    vào vòng với định kiến "bộ này không có ảnh" dù brief tìm lại được."""
    import approve_post
    src = pathlib.Path(approve_post.__file__).read_text(encoding="utf-8")
    than = src[src.index("def create_task_kite"):][:3500]
    assert "ve vector hoan toan" not in than, "task body van bao Kite ve vector"
    assert "CHAY LAI vong tim" in than, than[-600:]



# ---- ANH KHAI NIEM chi duoc dung o bia (IMAGE_RULES §1.2c) -------------------
def _khai_niem(wd, ma="K1", tu_khoa="Japan flag", **k):
    """Anh khai niem cua `image_concept.py`: co nuoc / day rack datacenter lay
    tu Wikimedia Commons khi tin khong co anh rieng. La ANH CHUP THAT nen no di
    qua moi cong ky thuat — chi cho dung cua no la bi gioi han."""
    return _hinh(wd, ma=ma, loai="anh",
                 khai_niem={"tu_khoa": tu_khoa, "ly_do": "tin nhac Nhat"}, **k)


def test_anh_khai_niem_o_slide_than_thi_canh_bao_khong_chan():
    """§1.2c nới lỏng LOW-58 (15/09/2026, Ông Chủ: "ảnh nào cũng dùng được hết,
    không phải câu nệ"): ảnh khái niệm đặt vào `figure` thân KHÔNG còn bị chặn,
    chỉ còn cảnh báo để người duyệt biết đây là ảnh minh hoạ chủ đề, không phải
    ảnh của tin."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        rieng = _hinh(wd, ma="R1")
        kn = _khai_niem(wd, ma="K1", w=1100, h=900)
        sl = _du()
        sl[0] = _cover(image="R1", caption="Bảng trong bài · via AA")
        sl[1] = _figure("K1", title="Cờ Nhật")
        _r, loi, _c = _chay(sl, _m(wd, [rieng, kn]), wd)
        assert loi == [], loi
        assert _co(_c, "K1", "KHÁI NIỆM"), _c


def test_anh_khai_niem_len_bia_thi_qua():
    """Chặn ở thân, KHÔNG chặn ở bìa — bìa/hero đúng là chỗ của nó."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl = _du()
        sl[0] = _cover(image="K1", caption="Cờ Nhật · via Wikimedia Commons")
        _r, loi, _c = _chay(sl, _m(wd, [_khai_niem(wd)]), wd)
        assert loi == [], loi


def test_anh_khai_niem_khong_bi_ep_xuong_than_khi_chuyen_kite():
    """Hai cổng không được đá nhau: §1.2e ép "đủ mã + phải có hình ở BODY",
    §1.2c cấm ảnh khái niệm ở thân. Tin CHUYỂN sang Kite mà chỉ có đúng một ảnh
    khái niệm thì trước 10/09/2026 đường nộp DUY NHẤT là đặt nó xuống `figure`
    thân — cổng ép đúng cái luật cấm. Nó phải rơi khỏi `figure_right_use`, và bìa
    là đường nộp còn lại."""
    import kite_prepare as kb
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        m = _m(wd, [_khai_niem(wd)], chuyen_kite="t_9")
        assert kb.figure_right_use(m) == [], kb.figure_right_use(m)
        assert kb.figure_hero(m)["ma"] == "K1"
        sl = _du()
        sl[0] = _cover(image="K1", caption="Cờ Nhật · via Wikimedia Commons")
        _r, loi, _c = _chay(sl, m, wd)
        assert loi == [], loi


def test_hero_lui_sang_anh_khai_niem_khi_tam_dau_bi_than_giu():
    """Tin chuyển sang Kite có một ảnh riêng + một ảnh khái niệm: ảnh riêng bị
    §1.2e giữ ở thân, nên bìa lùi sang ảnh khái niệm thay vì vẽ vector — đúng
    §1.2f ("bìa phải là ảnh thật khi CÓ ảnh thật dùng được")."""
    import kite_prepare as kb
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        rieng = _hinh(wd, ma="R1")
        kn = _khai_niem(wd, ma="K1", w=1100, h=900)
        m = _m(wd, [rieng, kn], chuyen_kite="t_9")
        assert kb.figure_right_use(m) == ["R1"], kb.figure_right_use(m)
        assert kb.figure_hero(m)["ma"] == "K1"
        sl = _du()
        sl[0] = _cover(image="K1", caption="Cờ Nhật · via Wikimedia Commons")
        sl[1] = _figure("R1")
        _r, loi, _c = _chay(sl, m, wd)
        assert loi == [], loi


def test_brief_noi_ro_anh_khai_niem_chi_dung_o_bia():
    """Brief liệt kê ảnh khái niệm chung danh sách "dùng được cho `figure` / bìa
    `image`" — không nói gì thì vai đặt nó xuống `figure` rồi ăn cổng chặn."""
    import kite_prepare as kb
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        rieng = _hinh(wd, ma="R1")
        kn = _khai_niem(wd, ma="K1", w=1100, h=900)
        brief = kb.write_brief(_m(wd, [rieng, kn], workdir=str(wd)), None)
        dong = [d for d in brief.splitlines() if d.startswith("- K1:")]
        assert dong and "KHÁI NIỆM" in dong[0] and "bìa" in dong[0], dong


def test_khung_spec_khong_in_ma_cua_bia_lai_o_figure():
    """Cùng một mã ở cả cover lẫn `figure` là `image_rules.check_duplicate` chặn — khung
    mẫu không được đẩy vai vào cổng."""
    import kite_prepare as kb
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_hinh(wd, ma="H1"), _hinh(wd, ma="H2", w=1100, h=900)]
        m = _m(wd, anh, chuyen_kite="t_9", workdir=str(wd))
        brief = kb.write_brief(m, None)
        spec = brief[brief.index("{\n"):]
        assert spec.count('"image": "H1"') == 1, spec[:400]


def test_hinh_chua_nhin_thi_chi_goi_y():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        _r, loi, canh = _chay(_du(), _m(wd, [_hinh(wd, lien_quan=None)]), wd)
        assert not _co(loi, "BẮT BUỘC"), loi
        assert _co(canh, "chưa nhìn", "H1"), canh


def test_hinh_qua_nho_chua_nhin_khong_bi_bao_gia():
    """kite_submit tinh "chua nhin" tu `hinh` (= kb.figure_real(m), da loc >= 800px),
    KHONG doc thang m["chua_nhin"] cap manifest (tinh tren TOAN BO anh, xem
    prepare/manifest.py) — anh <800px khong bao gio la candidate cua Kite nen
    "chua nhin" cua no la nhieu, khong phai tin. Neu sau nay co ai "gon" lai
    thanh doc thang khoa manifest thi test nay do ngay: NHO se bi bao gia."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        nho = _hinh(wd, ma="NHO", w=400, h=300, lien_quan=None)
        # Gia lap dung khoa "chua_nhin" cap manifest nhu prepare/manifest.py
        # se ghi (tinh tren TOAN BO anh, khong loc kich thuoc) — neu kite_submit
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
        h1, h2 = _hinh(wd), _hinh(wd, ma="H2", w=1100, h=900)
        sl = _du()
        sl[0] = _cover(image="H1", caption="Bảng benchmark · via AA")
        sl[1] = _statement(image="H2", caption="Bảng thứ hai · via AA")
        ra, loi, _c = _chay(sl, _m(wd, [h1, h2]), wd)
        assert loi == [], loi
        assert ra["slides"][0]["image"] == h1["goc"]
        assert ra["slides"][1]["image"] == h2["goc"]


def test_hinh_da_dung_o_tin_khac_thi_chan():
    """Dre va Ethan co cong nay tu dau; Kite thi khong — bang benchmark Dre dung
    hom qua van len bo cua Kite hom nay (06/09/2026)."""
    import image_rules
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        h = _hinh(wd)
        image_rules.record_used(h["goc"], "tin-khac", "dre", "https://vi.du/khac")
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
        sl, m = _du_bia(wd)
        sl[1] = _statement(standfirst="Đạt 97,3 điểm.")
        _r, loi, canh = _chay(sl, m, wd)
        assert loi == [], loi
        assert any("97,3" in c for c in canh), canh


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
