#!/usr/bin/env python3
"""Nấc cuối không bao giờ rỗng (`anh_thuc_the.py`, LOW-35). Ông Chủ 12/09/2026:
*"ko có lý gì mà ko tìm được ảnh minh hoạ đâu, đây là 2026, mọi thứ bạn cần đều
có sẵn"*. Test offline: mock mạng, khoá (1) tách thực thể, (2) lọc Wikipedia
pageimages theo cỡ, (3) Commons theo CỤM (không lọt hai người khác ghép tên),
(4) nấc chỉ chạy khi các nấc trên còn thiếu.

Chạy:  venv/bin/python tests/test_anh_thuc_the.py
"""
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import anh_thuc_the as tt  # noqa: E402


def test_tach_thuc_the_cum_viet_hoa_va_model():
    r = tt.thuc_the_trong_tieu_de("Claude is only available to people over 18, Anthropic says",
                                  models=["Claude Opus 5"])
    assert r[0] == "Claude Opus 5", r
    assert "Anthropic" in r, r
    # Tu don khong phai ten hang thi bo — "Claude" mot minh ra tranh Claude
    # Lorrain tren Commons (do that 12/09/2026); "Flash" la tu dien thuong.
    assert "Claude" not in r, r
    assert "Flash" not in tt.thuc_the_trong_tieu_de("DeepSeek V4.1 Flash tops LiveBench")


def test_pageimages_bo_anh_nho_va_khong_co():
    nho = {"query": {"pages": {"1": {"title": "Paul Erdős", "original": {"source": "u", "width": 324, "height": 430}}}}}
    to = {"query": {"pages": {"1": {"title": "Anthropic", "original": {"source": "https://x/a.jpg", "width": 2865, "height": 2952}}}}}
    trong = {"query": {"pages": {"1": {"title": "DeepSeek"}}}}
    class R:
        def __init__(self, j): self._j = j
        def raise_for_status(self): pass
        def json(self): return self._j
    with mock.patch("httpx.get", side_effect=[R(nho), R(to), R(trong)]):
        assert tt.pageimages("Erdős problems") is None
        c = tt.pageimages("Anthropic")
        assert c and c["diem"] == 27 and c["thuc_the"]["bai"] == "Anthropic"
        assert tt.pageimages("DeepSeek") is None


def test_commons_theo_cum_khong_lot_hai_nguoi_ghep_ten():
    def _p(w, h, ten):
        return {"title": f"File:{ten}", "imageinfo": [{"width": w, "height": h, "mime": "image/jpeg",
                                                       "thumburl": f"https://x/{ten}"}]}
    pages = {"1": _p(4000, 2667, "Dario Amodei at TechCrunch Disrupt 2023 01.jpg"),
             "2": _p(4000, 2667, "Dario Rossi meets Luca Amodei in Rome.jpg"),
             "3": _p(1800, 2880, "Dario Amodei in 2023.jpg")}
    import anh_thuong_hieu as th
    with mock.patch.object(th, "_hoi_commons", return_value=pages):
        ra = tt.commons_theo_cum("Dario Amodei", so=5)
    ten = [c["alt"] for c in ra]
    assert len(ra) == 2 and all("Rossi" not in t for t in ten), ten
    assert ra[0]["rong"] >= ra[0]["cao"], "anh ngang phai dung truoc"


def test_nac_chi_chay_khi_con_thieu():
    src = (ROOT / "anh_chuan_bi.py").read_text(encoding="utf-8")
    i_kn, i_tt = src.index("_vong_khai_niem(anh"), src.index("_vong_thuc_the(anh")
    assert i_kn < i_tt, "nac thuc the phai SAU nac khai niem"
    assert "du_nguyen_lieu(vai_anh, dung_duoc, flagship):\n            anh, dung_duoc, chua_nhin = _vong_thuc_the" in src

def test_vong_thuc_the_hoi_cau_khai_niem_khong_hoi_anh_cua_su_viec():
    """Đo trên máy chủ 12/09/2026: ảnh Wikipedia của Anthropic bị vision từ chối vì
    nấc hỏi câu mặc định "có phải ảnh của sự việc". Nấc phải gắn `khai_niem`
    trước `phan_loai` để đi câu "có đúng là <thực thể>, hợp bìa"."""
    src = (ROOT / "chuan_bi" / "vong_bu.py").read_text(encoding="utf-8")
    i = src.index("def _vong_thuc_the")
    than = src[i:i + 3000]
    assert 'a["khai_niem"] = {"tu_khoa": a["thuc_the"]["ten"]' in than
    assert than.index('a["khai_niem"] = ') < than.index("phan_loai(a, wd, tieu_de_nhin)")


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
