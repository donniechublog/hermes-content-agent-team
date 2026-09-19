#!/usr/bin/env python3
"""LOW-273: Dre chi ghep doc khi HET anh vua khung 4:5 co chu the.

Ong Chu 19/09/2026: "uu tien tim hinh dat vua 4:5 ratio ma co chu the truoc, neu
ko thi chuyen qua ghep". Ghep doc tao duong noi ngang giua khung va, voi cau quote
dai, nen chu che gan het anh duoi (cong LOW-215).

Chay:  venv/bin/python tests/test_stack_last_resort.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from tam import so_tam  # noqa: E402
import test_spec_dre as ts  # noqa: E402


def _bo(wd, fit_uses=("body",), **fit):
    """Bia A1 + ghep A2/A3 (hai anh ngang) o slide 2; A4..A5 lam cac slide con lai;
    A6 la anh vua khung con roi (chua dung)."""
    anh = [ts._anh(wd, "A1", 1000, 1250, uses=["cover"]),
           ts._anh(wd, "A2", 1600, 1000, uses=["body"]),
           ts._anh(wd, "A3", 1600, 1000, uses=["body"]),
           ts._anh(wd, "A4", 1000, 1250, uses=["body"]),
           ts._anh(wd, "A5", 1000, 1250, uses=["body"]),
           ts._anh(wd, "A6", 1000, 1250, uses=list(fit_uses), cluttered=False, **fit)]
    for a in anh:
        a.setdefault("cluttered", False)
    slides = [{"stack": ["A2", "A3"], "text": "x", "quote": "Một câu", "attrib": "X"},
              ts._slide("A4", quote="Câu hai", attrib="Y"), ts._slide("A5"),
              ts._slide("A4x")]
    slides = slides[:3]
    return ts._spec(ts._bia("A1"), slides), ts._m(wd, anh, min_images=4), wd


def test_con_anh_vua_4_5_chua_dung_thi_chan_ghep():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t))
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert ts._co(loi, "slide 2", "ghép A2+A3", "A6", "VỪA khung 4:5"), loi


def test_het_anh_vua_khung_thi_cho_ghep():
    """A6 khong con (da dung o slide khac) -> ghep la duong con lai, khong chan."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t))
        spec["slides"].append(ts._slide("A6"))       # A6 nay da duoc dung
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert not ts._co(loi, "VỪA khung 4:5"), loi


def test_anh_ngang_du_cat_doc_duoc_khong_tinh_la_vua_khung():
    """Ong Chu 04/09: anh ngang thi ghep, khong cat — nen A6 ngang khong bat ghep."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t), landscape_crop_ok=True)
        m["images"][5].update({"w": 1600, "h": 1000, "ratio": 1.6, "landscape": True})
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert not ts._co(loi, "VỪA khung 4:5"), loi


def test_anh_roi_khong_tinh_la_vua_khung():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t))
        m["images"][5]["cluttered"] = True
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert not ts._co(loi, "VỪA khung 4:5"), loi


def test_anh_khong_lien_quan_khong_tinh_la_vua_khung():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t))
        m["images"][5]["relevant"] = False
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert not ts._co(loi, "VỪA khung 4:5"), loi


def test_anh_mat_nguoi_khong_tinh_de_khong_ket_vai():
    """Mat nguoi con phu thuoc ten co trong bai — khong ep vai vao ngo cut."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t))
        m["images"][5]["faces"] = 1
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert not ts._co(loi, "VỪA khung 4:5"), loi


def test_anh_ti_le_ngoai_dai_khong_tinh():
    """Anh 1000x1600 (0.62) khong vua khung 4:5..1:1."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t))
        m["images"][5].update({"w": 1000, "h": 1600, "ratio": 0.62})
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert not ts._co(loi, "VỪA khung 4:5"), loi


def test_khong_ghep_thi_khong_chan_gi():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t))
        spec["slides"][0] = ts._slide("A2", quote="Một câu", attrib="X")
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert not ts._co(loi, "VỪA khung 4:5"), loi


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
