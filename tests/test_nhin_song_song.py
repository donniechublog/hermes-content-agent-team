#!/usr/bin/env python3
"""Vision chạy 4 luồng (B2) phải chịu được 429 và một ảnh hỏng (audit lượt 2, B-r2-2/3).

- B-r2-2: 4 luồng bắn cùng lúc vào router, 429/5xx thì trước đây chỉ log
  'HTTPError' và trả lien_quan=None → ảnh rơi vào "CHƯA AI NHÌN", bị loại khỏi
  dung_duoc. Không retry/backoff nào; song song hoá làm 429 dễ xảy ra HƠN.
- B-r2-3: phan_loai không có try — một PNG cụt làm list(ex.map) ném tại
  _nhin_anh → cả lô mất kể cả ảnh đã nhìn xong, engine chết không xong.json.

Chạy:  venv/bin/python tests/test_nhin_song_song.py
"""
import io
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from PIL import Image                                         # noqa: E402
import prepare.vision as vision                                  # noqa: E202,E402


class _Resp:
    def __init__(self, s):
        self.s = s.encode()

    def read(self):
        return self.s


def test_429_duoc_thu_lai_roi_thanh_cong():
    dem = {"goi": 0}
    ngu = []

    def _open(req, timeout=0):
        dem["goi"] += 1
        if dem["goi"] < 3:
            raise urllib.error.HTTPError("u", 429, "Too Many", {}, io.BytesIO(b""))
        return _Resp("ok")
    cu = urllib.request.urlopen
    urllib.request.urlopen = _open
    try:
        r = vision._call_router(object(), _ngu=ngu.append)
    finally:
        urllib.request.urlopen = cu
    assert r.read() == b"ok" and dem["goi"] == 3, dem
    assert ngu == [1, 2], f"backoff tang dan 1s, 2s: {ngu}"


def test_401_khong_thu_lai():
    def _open(req, timeout=0):
        raise urllib.error.HTTPError("u", 401, "Unauthorized", {}, io.BytesIO(b""))
    cu = urllib.request.urlopen
    urllib.request.urlopen = _open
    try:
        try:
            vision._call_router(object(), _ngu=lambda s: None)
        except urllib.error.HTTPError as e:
            assert e.code == 401
            return
    finally:
        urllib.request.urlopen = cu
    raise AssertionError("401 phai nem ngay, khong thu lai")


def test_het_luot_thu_thi_nem_429():
    goi = []

    def _open(req, timeout=0):
        goi.append(1)
        raise urllib.error.HTTPError("u", 429, "Too Many", {}, io.BytesIO(b""))
    cu = urllib.request.urlopen
    urllib.request.urlopen = _open
    try:
        try:
            vision._call_router(object(), _ngu=lambda s: None)
        except urllib.error.HTTPError as e:
            assert e.code == 429 and len(goi) == len(vision._CHO_THU_LAI) + 1, len(goi)
            return
    finally:
        urllib.request.urlopen = cu
    raise AssertionError("het luot phai nem")


def test_mot_anh_hong_khong_giet_ca_lo():
    with tempfile.TemporaryDirectory() as t:
        wd = Path(t)
        anh = []
        for i in range(4):
            p = wd / f"A{i}.png"
            if i == 2:
                p.write_bytes(b"khong phai png")
            else:
                Image.new("RGB", (900, 700), (100 + i, 120, 140)).save(p)
            anh.append({"ma": f"A{i}", "goc": str(p)})
        # tieu_de rong -> khong goi vision; dem_mat co the None tren may khong cv2
        ra, dung_duoc, chua_nhin = vision._seen_image(anh, {}, "", wd)
        assert len(ra) == 4, "ca lo phai con du 4 ban ghi"
        assert ra[2]["lien_quan"] is None and any("không phân loại" in g for g in ra[2]["ghi_chu"]), ra[2]
        assert all("w" in a and a["w"] > 0 for a in (ra[0], ra[1], ra[3])), "anh tot phai duoc phan loai binh thuong"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
