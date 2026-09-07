#!/usr/bin/env python3
"""Cong chan spec the hero cua Ethan (`ethan_nop.giai_spec`).

Cung ho voi cong Dre (`test_spec_dre`): cung manifest anh, cung ba cong dung
chung o nop_chung (mat nguoi, quote dich, so tren anh), cung cong XH va cong
"khong lien quan" — nhung viet lai rieng, va da tung lech: truoc 06/09/2026
Ethan khong doc co `lien_quan` nen chon bang ti so giai golf cho tin GPT-6.

Rieng cua Ethan: mot anh (hoac ghep hai anh ngang qua "anh2"), kieu quote/tran,
va nguong ngang TI_LE_HERO_MAX cua card.py.

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
    """Manifest cua Ethan: `cap_ghep` la LIST (engine ghi list rong khi khong
    co cap) — `eb.cap_ghep_hero` lap thang qua no, None la TypeError."""
    k.setdefault("cap_ghep", [])
    return _m_dre(wd, anh, **k)


def _spec(ma="A1", **k):
    d = {"anh": ma, "kieu": "quote", "hook": "Nvidia mở kho mô hình Nemotron",
         "tagline": "MODEL RELEASE", "attrib": "via Reuters"}
    d.update(k)
    return d


def _chay(spec, m, wd):
    import ethan_nop
    return ethan_nop.giai_spec(spec, m, Path(wd))


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
        assert kq["kieu"] == "quote" and kq["anh"]["ma"] == "A1" and kq["anh2"] is None


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
    """Loi 06/09/2026: Ethan khong doc co lien_quan nen chon bang ti so giai golf
    cho tin GPT-6 — bat chu 'leaderboard', khong nhin noi dung."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        anh[0]["lien_quan"] = False
        anh[0]["mo_ta"] = "bảng tỉ số giải golf Ricoh"
        _kq, loi, _c = _chay(_spec(), _m(wd, anh), wd)
        assert _co(loi, "A1", "KHÔNG LIÊN QUAN", "giải golf"), loi


# ---------------------------------------------------------------- chart / ngang
def test_chart_di_mot_minh_thi_doi_anh2():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t, [_anh(wd := Path(t), "C1", 1600, 900, loai="chart")])
        _kq, loi, _c = _chay(_spec("C1"), _m(wd, anh), wd)
        assert _co(loi, "C1", "CHART", "anh2"), loi


def test_anh_ngang_qua_nguong_thi_doi_anh2():
    import ethan_chuan_bi as eb
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250), _anh(wd, "N1", 1920, 1080)]
        assert 1920 / 1080 > eb.TI_LE_HERO_MAX
        _kq, loi, _c = _chay(_spec("N1"), _m(wd, anh), wd)
        assert _co(loi, "N1", "NGANG", "anh2"), loi


def test_anh_ngang_duoi_nguong_thi_di_mot_minh_duoc():
    import ethan_chuan_bi as eb
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250), _anh(wd, "N1", 1500, 1000)]
        assert 1.5 <= eb.TI_LE_HERO_MAX
        _kq, loi, _c = _chay(_spec("N1"), _m(wd, anh), wd)
        assert loi == [], loi


def test_ghep_hai_anh_ngang_hop_le():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "N1", 1920, 1080), _anh(wd, "N2", 1600, 900)]
        kq, loi, _c = _chay(_spec("N1", anh2="N2"), _m(wd, anh), wd)
        assert loi == [], loi
        assert kq["anh2"]["ma"] == "N2"


def test_ghep_van_qua_ngang_thi_bao():
    """Hai anh 16:9 ghep doc ra ~0.89 — duoc. Hai anh 3:1 ghep doc ra 1.5 —
    van qua nguong 1.6? Khong: 1/(1/3+1/3)=1.5. Dung 4:1 -> 2.0 > 1.6."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "N1", 4000, 1000), _anh(wd, "N2", 4000, 1000)]
        _kq, loi, _c = _chay(_spec("N1", anh2="N2"), _m(wd, anh), wd)
        assert _co(loi, "vẫn quá ngang"), loi


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
        xh = _anh(wd, "XH", 1200, 900, loai="chart", xep_hang={"site": "LMArena"})
        anh = [_anh(wd, "A1", 1000, 1250), xh]
        m = _m(wd, anh, tin_xep_hang=True,
               xep_hang={"kieu": "chup", "site": "LMArena", "bang": "text", "model": "GPT"})
        _kq, loi, _c = _chay(_spec("A1"), m, wd)
        assert _co(loi, "XẾP HẠNG", "XH"), loi
        kq, loi2, _c = _chay(_spec("XH"), m, wd)
        assert loi2 == [], loi2
        assert kq["anh"]["ma"] == "XH"


def test_khong_chup_duoc_bang_thi_khong_ep():
    """Cung hoi quy 06/09 nhu Dre: ep dung ma XH khi ma do khong ton tai la vai
    sua kieu gi cung sai."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        for xh in (None, {"kieu": "the", "site": "s", "bang": "b", "model": "x"}):
            _kq, loi, _c = _chay(_spec("A1"), _m(wd, anh, tin_xep_hang=True, xep_hang=xh), wd)
            assert not _co(loi, "XẾP HẠNG"), (xh, loi)


# ---------------------------------------------------------------- cong dung chung
def test_mat_nguoi_khong_khai_ten_thi_chan():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        anh[0]["mat"] = 1
        _kq, loi, _c = _chay(_spec(), _m(wd, anh), wd)
        assert loi, "mat nguoi ma khong nhan_vat phai bi chan"
        assert not _chay(_spec(nhan_vat="Jensen Huang"),
                         _m(wd, anh, chu_bai="CEO Jensen Huang phát biểu tại GTC"), wd)[1]


def test_hook_con_nguyen_tieng_anh_thi_chan():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        _kq, loi, _c = _chay(_spec(hook="We are opening the model zoo to every developer"),
                             _m(wd, anh), wd)
        assert loi, "hook tieng Anh phai bi chan"


def test_anh_da_dung_o_tin_khac_thi_chan():
    import luat_anh
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        luat_anh.ghi_da_dung(anh[0]["goc"], "tin-khac", "designer", "https://vi.du/khac")
        _kq, loi, _c = _chay(_spec(), _m(wd, anh), wd)
        assert _co(loi, "TRUNG anh da dung", "tin-khac"), loi


def test_so_tren_the_khong_co_trong_tu_lieu_thi_canh_bao():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        _kq, loi, canh = _chay(_spec(hook="Nvidia đạt 97,3 điểm MMLU"),
                               _m(wd, anh, chu_bai="Nvidia mở kho, đạt 86,2 điểm MMLU"), wd)
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
