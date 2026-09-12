#!/usr/bin/env python3
"""LOW-27 (12/09/2026): `luat_anh.dem_mat` phai THU NHO anh lon truoc khi dua vao YuNet.

Ca that: A2.png 9440x5310 cua draft t_24b214a6 lam YuNet SIGSEGV (exit -11) ke
ca khi chay mot minh — do tung anh trong tien trinh rieng tren may chu, 7/8 ok,
1 chet. Segfault khong bat duoc bang except, keo ca engine chet, khoa mo coi,
vai chay lai 16 lan trong 50 phut.

Test khong cho detector that an anh 50MP (se segfault chinh test runner tren
code cu): dung detector GIA ghi lai kich thuoc `setInputSize` nhan duoc. Fail
tren code cu (nhan 9440x5310), pass tren code moi (<= MAT_CANH_MAX).

Chay:  venv/bin/python tests/test_dem_mat_anh_lon.py
"""
import importlib.util
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import luat_anh                                              # noqa: E402


class _DetGia:
    def __init__(self):
        self.kich_thuoc = None

    def setInputSize(self, wh):
        self.kich_thuoc = tuple(wh)

    def detect(self, im):
        assert im.shape[1] == self.kich_thuoc[0] and im.shape[0] == self.kich_thuoc[1]
        return 0, None


def _voi_det_gia(path):
    det = _DetGia()
    cu = luat_anh._yunet
    luat_anh._yunet = lambda: det
    try:
        ra = luat_anh.dem_mat(path)
    finally:
        luat_anh._yunet = cu
    return ra, det.kich_thuoc


def test_anh_50mp_duoc_thu_ve_duoi_tran():
    if importlib.util.find_spec("cv2") is None:
        return                                            # may khong co cv2: dem_mat ve None
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "a2.png"
        Image.new("RGB", (9440, 5310), (30, 30, 30)).save(p, compress_level=1)
        ra, wh = _voi_det_gia(p)
    assert ra == 0, ra
    assert wh is not None and max(wh) <= luat_anh.MAT_CANH_MAX, wh
    # giu ti le: 9440/5310 = 1.778
    assert abs(wh[0] / wh[1] - 9440 / 5310) < 0.01, wh


def test_anh_nho_giu_nguyen_kich_thuoc():
    if importlib.util.find_spec("cv2") is None:
        return                                            # may khong co cv2: dem_mat ve None
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "a.png"
        Image.new("RGB", (1200, 675), (200, 200, 200)).save(p)
        _ra, wh = _voi_det_gia(p)
    assert wh == (1200, 675), wh


def test_tran_nho_hon_gioi_han_thuc_te_da_do():
    assert luat_anh.MAT_CANH_MAX < 9440


if __name__ == "__main__":
    ok = 0
    ten = [k for k in list(globals()) if k.startswith("test_")]
    for k in ten:
        try:
            globals()[k]()
            ok += 1
        except AssertionError as e:
            print(f"    FAIL {k}: {e}")
    print(f"{Path(__file__).name:<34} {ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
