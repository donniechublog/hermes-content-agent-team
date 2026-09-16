#!/usr/bin/env python3
"""`prepare.vision.classify` phai HOI vision cat_ngang_ok cho anh ngang cao,
khong lai de "NEU" mo ho cho writer doan (su co 12/09/2026, t_a8ffd2f6 lan hai).

Dre chay that voi bo anh da co du 8 tam ("du 6 slide" theo cong thuc cu), nhung
4/5 anh ngang cao (>=700) la bien hieu/logo/chart CO CHU — chi 1 tam la nguoi/
san pham that dung mot minh duoc qua cat_ngang. Cong thuc cu chi nhin chieu cao,
khong biet noi dung, nen dem thua 2 slide. Xem them tests/test_schema.py
(cong thuc dem) va tests/test_vision_lien_quan.py (parse cau LIEN_QUAN).

Chay:  venv/bin/python tests/test_cat_ngang_vision.py
"""
import io
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from prepare import vision                                     # noqa: E402


def _bat_stderr(ham):
    cu, sys.stderr = sys.stderr, io.StringIO()
    try:
        return ham(), sys.stderr.getvalue()
    finally:
        sys.stderr = cu


def _anh(tmp: Path, w=1600, h=1000) -> dict:
    """Anh chup GIA co van (khong phang 1 mau) -- anh mot mau bi `image_rules.is_chart`
    nhan la chart 100%, khien nhanh CHART chay thay vi nhanh anh chup thuong."""
    import random
    from PIL import Image
    rnd = random.Random(42)
    p = tmp / "a.png"
    img = Image.new("RGB", (w, h))
    img.putdata([(rnd.randint(0, 255), rnd.randint(0, 255), rnd.randint(0, 255))
                 for _ in range(w * h)])
    img.save(p)
    return {"ma": "A1", "goc": str(p), "url": "https://x/a.png", "tu": "chup"}


class _Res:
    def __init__(self, content: bytes):
        self._c = content

    def read(self):
        return self._c


def _goi_thu(txt: str):
    import json
    body = json.dumps({"choices": [{"message": {"content": txt}}]}).encode()
    return mock.patch.object(vision, "_call_router", return_value=_Res(body))


def test_ngang_cao_khong_phai_chart_thi_hoi_cat_ngang_va_luu_ket_qua():
    with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        a = _anh(Path(tmp), 1600, 1000)      # ngang ro, cao 1000 >=700
        with _goi_thu("MO_TA: nguoi cam san pham.\nLIEN_QUAN: co\nCAT_NGANG: co"):
            classify(a := a, wd=Path(tmp), tieu_de="T")
        assert a["cat_ngang_ok"] is True
        assert any("vision đã xác nhận" in d for d in a["dung"]), a["dung"]
        assert not any("NẾU" in d for d in a["dung"]), "khong con cau NEU mo ho khi da xac nhan duoc"


def test_ngang_cao_co_chu_thi_khong_offer_cat_ngang():
    with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        a = _anh(Path(tmp), 1600, 1000)
        with _goi_thu("MO_TA: bien hieu logo cong ty tren tuong.\nLIEN_QUAN: co\nCAT_NGANG: khong"):
            classify(a, wd=Path(tmp), tieu_de="T")
        assert a["cat_ngang_ok"] is False
        assert not any("cat_ngang" in d and "NẾU" not in d and "false" not in d.lower()
                       for d in a["dung"] if "true (" in d)
        assert any("không được crop" in g for g in a["ghi_chu"]), a["ghi_chu"]


def test_ngang_qua_thap_khong_hoi_cat_ngang_gi_ca():
    with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
        a = _anh(Path(tmp), 1600, 600)       # ngang, cao < 700
        with _goi_thu("MO_TA: x.\nLIEN_QUAN: co"):
            classify(a, wd=Path(tmp), tieu_de="T")
        assert a["cat_ngang_ok"] is None
        assert "quá thấp để cắt dọc, chỉ ghép" in a["ghi_chu"]


def test_vision_noi_bieu_do_ma_pixel_bo_lo_thi_sua_lai_thanh_chart():
    """A11 that (12/09): pixel do 'la_chart' False nhung mo_ta ro rang la
    bieu do -- phai tin mo_ta, khong con hoi CAT_NGANG mot cach vo nghia."""
    with tempfile.TemporaryDirectory() as tmp, mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}), \
         mock.patch("image_rules_ethan.is_chart", return_value=(False, "khong phai chart (pixel)")):
        a = _anh(Path(tmp), 1600, 1000)
        with _goi_thu("MO_TA: Biểu đồ tròn thể hiện tỷ trọng doanh thu.\nLIEN_QUAN: co\nCAT_NGANG: khong"):
            classify(a, wd=Path(tmp), tieu_de="T")
        assert a["loai"] == "chart", "mo_ta noi bieu do thi phai sua lai la chart du pixel bo lo"
        assert a["cat_ngang_ok"] is None
        assert any("chart" in d for d in a["dung"])


def test_hong_vision_giu_cau_dieu_kien_cu_khong_chan_writer():
    with tempfile.TemporaryDirectory() as tmp:
        a = _anh(Path(tmp), 1600, 1000)
        with mock.patch.dict("os.environ", {}, clear=False):
            import os
            cu = os.environ.pop("OPENAI_API_KEY", None)
            try:
                with mock.patch.object(vision.env_load, "load", lambda *a, **k: None):
                    classify(a, wd=Path(tmp), tieu_de="T")
            finally:
                if cu is not None:
                    os.environ["OPENAI_API_KEY"] = cu
        assert a["cat_ngang_ok"] is None
        assert any("NẾU" in d for d in a["dung"]), "vision hong thi giu cau dieu kien cu, khong tu quyet dinh thay writer"


from prepare.vision import classify  # noqa: E402  (import sau de mock image_rules o test rieng khong dinh)


if __name__ == "__main__":
    import role
    role.set_active_role("ethan")            # xem tam.chay_tat_ca (LOW-182)
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
