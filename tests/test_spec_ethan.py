#!/usr/bin/env python3
"""Cong chan spec the hero cua Ethan (`ethan_submit.resolve_spec`).

Cung ho voi cong Dre (`test_spec_dre`): cung manifest anh, cung ba cong dung
chung o submit_common (mat nguoi, quote dich, so tren anh), cung cong XH va cong
"khong lien quan" — nhung viet lai rieng, va da tung lech: truoc 06/09/2026
Ethan khong doc co `relevant` nen chon bang ti so giai golf cho tin GPT-6.

Rieng cua Ethan: mot anh (hoac ghep hai anh ngang qua "anh2"), kieu quote/tran,
va nguong ngang RATIO_HERO_MAX cua card.py.

Chay:  venv/bin/python tests/test_spec_ethan.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tam import so_tam  # noqa: E402
from test_spec_dre import _anh, _co  # noqa: E402
from test_spec_dre import _m as _m_dre  # noqa: E402


def _m(wd, anh, **k):
    """Manifest cua Ethan: `stackable_pairs` la LIST (engine ghi list rong khi khong
    co cap) — `eb.stackable_pairs_hero` lap thang qua no, None la TypeError."""
    k.setdefault("stackable_pairs", [])
    k.setdefault("image_role", "ethan")
    return _m_dre(wd, anh, **k)


def _spec(ma="A1", **k):
    d = {"anh": ma, "kieu": "quote", "hook": "Nvidia mở kho mô hình Nemotron",
         "tagline": "MODEL RELEASE", "attrib": "via Reuters"}
    d.update(k)
    return d


def _chay(spec, m, wd):
    import ethan_submit
    return ethan_submit.resolve_spec(spec, m, Path(wd))


def _bo(t, them=()):
    wd = Path(t)
    anh = [_anh(wd, "A1", 1000, 1250), _anh(wd, "A2", 1000, 1250)] + list(them)
    return anh, wd


# ---------------------------------------------------------------- hop le
def test_spec_du_thi_tra_ve_anh_da_giai():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        kq, loi, _c = _chay(_spec(), _m(wd, anh), wd)
        assert loi == [], loi
        assert kq["kieu"] == "quote" and kq["anh"]["id"] == "A1" and kq["anh2"] is None


def test_kieu_tran_can_title_khong_can_hook():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        kq, loi, _c = _chay({"anh": "A1", "kieu": "tran",
                             "title": "Nvidia mở kho mô hình Nemotron cho mọi người"},
                            _m(wd, anh), wd)
        assert loi == [], loi
        assert kq["kieu"] == "tran"
        _kq, loi2, _c = _chay({"anh": "A1", "kieu": "tran"}, _m(wd, anh), wd)
        assert _co(loi2, "tran", "title"), loi2


def test_kieu_la_thi_bao():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        _kq, loi, _c = _chay(_spec(kieu="banner"), _m(wd, anh), wd)
        assert _co(loi, "kieu", "quote", "tran"), loi


def test_quote_thieu_hook_tagline_attrib_bao_du_ba():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        _kq, loi, _c = _chay(_spec(hook=" ", tagline="", attrib=None), _m(wd, anh), wd)
        assert _co(loi, "hook") and _co(loi, "tagline") and _co(loi, "attrib"), loi


# ---------------------------------------------------------------- ma anh
def test_anh_khong_ton_tai_thi_dung_ngay_va_liet_ke_ma_co():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        kq, loi, _c = _chay(_spec("A9"), _m(wd, anh), wd)
        assert kq is None and _co(loi, "A9", "A1"), loi


def test_anh2_sai_hoac_trung_thi_bo_anh2_nhung_van_bao():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        _kq, loi, _c = _chay(_spec(anh2="A9"), _m(wd, anh), wd)
        assert _co(loi, "anh2", "A9"), loi
        _kq, loi2, _c = _chay(_spec(anh2="A1"), _m(wd, anh), wd)
        assert _co(loi2, "anh2", "trùng"), loi2


def test_anh_khong_lien_quan_bi_chan_va_chi_duong_ra():
    """Loi 06/09/2026: Ethan khong doc co relevant nen chon bang ti so giai golf
    cho tin GPT-6 — bat chu 'leaderboard', khong nhin noi dung."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        anh[0]["relevant"] = False
        anh[0]["description"] = "bảng tỉ số giải golf Ricoh"
        _kq, loi, _c = _chay(_spec(), _m(wd, anh), wd)
        assert _co(loi, "A1", "KHÔNG LIÊN QUAN", "giải golf"), loi


# ---------------------------------------------------------------- chart / ngang
def test_chart_di_mot_minh_thi_doi_anh2():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t, [_anh(wd := Path(t), "C1", 1600, 900, loai="chart")])
        _kq, loi, _c = _chay(_spec("C1"), _m(wd, anh), wd)
        assert _co(loi, "C1", "CHART", "anh2"), loi


def test_anh_ngang_qua_nguong_khong_con_bi_ep_doi_anh2():
    """13/09/2026: bỏ điều kiện "ảnh quá ngang phải ghép" (tương đương
    `image_rules.kiem_anh_thap`, đã bỏ khỏi hệ thống, mọi vai) — ảnh ngang dù vượt
    ngưỡng cũ vẫn được đứng một mình, không còn bị ép thêm "anh2"."""
    import ethan_prepare as eb
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250), _anh(wd, "N1", 1920, 1080)]
        assert 1920 / 1080 > eb.RATIO_HERO_MAX
        _kq, loi, _c = _chay(_spec("N1"), _m(wd, anh), wd)
        assert loi == [], loi


def test_anh_ngang_duoi_nguong_thi_di_mot_minh_duoc():
    import ethan_prepare as eb
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250), _anh(wd, "N1", 1500, 1000)]
        assert 1.5 <= eb.RATIO_HERO_MAX
        _kq, loi, _c = _chay(_spec("N1"), _m(wd, anh), wd)
        assert loi == [], loi


def test_ghep_hai_anh_ngang_hop_le():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "N1", 1920, 1080), _anh(wd, "N2", 1600, 900)]
        kq, loi, _c = _chay(_spec("N1", anh2="N2"), _m(wd, anh), wd)
        assert loi == [], loi
        assert kq["anh2"]["id"] == "N2"


def test_ghep_qua_ngang_khong_con_bi_chan():
    """Ông Chủ 13/09/2026: bỏ `kiem_anh_thap` khỏi hệ thống, mọi vai — ghép hai
    ảnh cực ngang (4:1 mỗi ảnh, ghép ra 2.0, trước đây > ngưỡng 1.6 nên bị
    chặn) giờ không còn báo lỗi nào về việc này."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "N1", 4000, 1000), _anh(wd, "N2", 4000, 1000)]
        _kq, loi, _c = _chay(_spec("N1", anh2="N2"), _m(wd, anh), wd)
        assert not _co(loi, "quá ngang"), loi


def test_ghep_doc_chi_cho_hai_anh_ngang():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "N1", 1920, 1080), _anh(wd, "A2", 1000, 1250)]
        _kq, loi, _c = _chay(_spec("N1", anh2="A2"), _m(wd, anh), wd)
        assert _co(loi, "hai ảnh NGANG", "A2"), loi


# ---------------------------------------------------------------- xep hang
def test_tin_xep_hang_da_chup_bang_ma_anh_khong_phai_XH_thi_chan():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        xh = _anh(wd, "XH", 1200, 900, loai="chart", ranking={"site": "LMArena"})
        anh = [_anh(wd, "A1", 1000, 1250), xh]
        m = _m(wd, anh, is_ranking_story=True,
               ranking={"kind": "bang", "site": "LMArena", "board": "text", "model": "GPT"})
        _kq, loi, _c = _chay(_spec("A1"), m, wd)
        assert _co(loi, "XẾP HẠNG", "XH"), loi
        kq, loi2, _c = _chay(_spec("XH"), m, wd)
        assert loi2 == [], loi2
        assert kq["anh"]["id"] == "XH"


def test_khong_chup_duoc_bang_thi_khong_ep():
    """Cung hoi quy 06/09 nhu Dre: ep dung ma XH khi ma do khong ton tai la vai
    sua kieu gi cung sai."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        for xh in (None, {"kind": "the", "site": "s", "board": "b", "model": "x"}):
            _kq, loi, _c = _chay(_spec("A1"), _m(wd, anh, is_ranking_story=True, ranking=xh), wd)
            assert not _co(loi, "XẾP HẠNG"), (xh, loi)


# ---------------------------------------------------------------- cong dung chung
def test_mat_nguoi_khong_khai_ten_thi_chan():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        anh[0]["faces"] = 1
        _kq, loi, _c = _chay(_spec(), _m(wd, anh), wd)
        assert loi, "mat nguoi ma khong nhan_vat phai bi chan"
        assert not _chay(_spec(nhan_vat="Jensen Huang"),
                         _m(wd, anh, article_text="CEO Jensen Huang phát biểu tại GTC"), wd)[1]


def test_hook_con_nguyen_tieng_anh_thi_chan():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        _kq, loi, _c = _chay(_spec(hook="We are opening the model zoo to every developer"),
                             _m(wd, anh), wd)
        assert loi, "hook tieng Anh phai bi chan"


def test_anh_da_dung_o_tin_khac_thi_chan():
    import image_rules_ethan as image_rules
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        image_rules.record_used(anh[0]["original_path"], "tin-khac", "ethan", "https://vi.du/khac")
        _kq, loi, _c = _chay(_spec(), _m(wd, anh), wd)
        assert _co(loi, "TRUNG anh da dung", "tin-khac"), loi


def test_so_tren_the_khong_co_trong_tu_lieu_thi_canh_bao():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        _kq, loi, canh = _chay(_spec(hook="Nvidia đạt 97,3 điểm MMLU"),
                               _m(wd, anh, article_text="Nvidia mở kho, đạt 86,2 điểm MMLU"), wd)
        assert loi == [], loi
        assert any("97,3" in c for c in canh), canh


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
