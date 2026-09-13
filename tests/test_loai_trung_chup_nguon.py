#!/usr/bin/env python3
"""Anh chup TRANG NGUON phai LOAI TRUNG bang dHash (giong duong tai anh binh
thuong), khong duoc them thang vao carousel.

Ong Chu 13/09/2026, xem carousel that: *"có đến 3 ảnh giống hệt nhau về nội
dung, góc máy, bố cục. việc này ko được phép"*. Nhieu bao dung CHUNG mot anh
photo-wire (AP/Reuters/Getty) cho cung mot tin bao; `_vong_chup_nguon` chup
tung trang RIENG LE, khong di qua `chuan_bi.tai_loc.tai_va_loc` (noi CO san
co che so dHash) nen chua bao gio duoc so trung.

Chay:  venv/bin/python tests/test_loai_trung_chup_nguon.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from chuan_bi import vong_bu                                   # noqa: E402


def _anh(tmp: Path, ten: str, seed: int) -> Path:
    """Anh co CAU TRUC ro (o vuong lech theo `seed`), khong phai mau phang —
    dHash doc chenh lech SANG/TOI giua cac pixel ke nhau nen hai anh mau phang
    khac nhau (vd xanh vs do) van co the ra hash GIONG HET nhau (ca hai deu
    "khong co chenh lech o dau"). Seed khac nhau -> vi tri o vuong khac han ->
    hash khac han; cung seed -> cung anh, mo phong dung CHUNG mot photo-wire."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (400, 300), (245, 245, 245))
    d = ImageDraw.Draw(im)
    x0 = 20 + (seed * 37) % 300
    y0 = 20 + (seed * 53) % 200
    d.rectangle([x0, y0, x0 + 60, y0 + 60], fill=(20, 20, 20))
    d.ellipse([300 - (seed * 11) % 250, 10, 340 - (seed * 11) % 250, 50], fill=(200, 30, 30))
    p = tmp / ten
    im.save(p)
    return p


def _gia_chup_lead(anh_map):
    """Gia `chup_trang.chup_lead_mobile`: 'chup' bang cach COPY tep anh co san
    (mo phong hai trang dung CHUNG mot photo-wire khi anh_map anh xa nhieu URL
    ve CUNG mot tep nguon)."""
    def gia(url, ra, phien=None):
        src = anh_map.get(url)
        if src is None:
            return None
        from PIL import Image
        Path(ra).parent.mkdir(parents=True, exist_ok=True)
        Image.open(src).convert("RGB").save(ra)
        return {"anh": url, "trang": url, "tu": "chup_nguon", "chup_nguon": True,
                "tit_trang": "", "mau_nen": "#ffffff", "alt": "", "ly_do": ""}
    return gia


def test_hai_bao_dung_chung_photo_wire_chi_giu_mot_tam():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        wire = _anh(tmp, "wire.png", seed=1)       # anh AP/Reuters dung chung
        rieng = _anh(tmp, "rieng.png", seed=2)      # anh khac han cua bao thu ba
        anh_map = {
            "https://a.com/bai": wire,
            "https://b.com/bai-khac-dua-cung-tin": wire,   # CUNG anh, khac bao
            "https://c.com/bai-thu-ba": rieng,
        }
        with mock.patch("chup_trang.chup_lead_mobile", _gia_chup_lead(anh_map)), \
             mock.patch("nguon_bai.cung_tin", return_value=True):
            anh, dung_duoc, _ = vong_bu._vong_chup_nguon(
                [], "https://a.com/bai",
                [{"url": "https://b.com/bai-khac-dua-cung-tin"}, {"url": "https://c.com/bai-thu-ba"}],
                tmp / "wd")
        mien = sorted(a["mien"] for a in anh)
        assert len(anh) == 2, f"phai con 2 anh (1 wire + 1 rieng), duoc {mien}"
        assert "a.com" in mien or "b.com" in mien
        assert "c.com" in mien


def test_khong_trung_voi_anh_da_co_tu_vong_khac():
    """Anh chup TRUNG voi mot tam DA CO SAN trong `anh` (tu vong tim rong/goc)
    tu truoc do — cung phai bi loai, khong chi so giua cac tam chup voi nhau."""
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        wire = _anh(tmp, "wire.png", seed=1)
        da_co = tmp / "wd" / "goc"
        da_co.mkdir(parents=True)
        from PIL import Image
        Image.open(wire).convert("RGB").save(da_co / "A1.png")
        anh_ban_dau = [{"ma": "A1", "goc": str(da_co / "A1.png"), "dung": ["thân"], "lien_quan": True}]
        anh_map = {"https://a.com/bai": wire}
        with mock.patch("chup_trang.chup_lead_mobile", _gia_chup_lead(anh_map)):
            anh, dung_duoc, _ = vong_bu._vong_chup_nguon(anh_ban_dau, "https://a.com/bai", [], tmp / "wd")
        assert len(anh) == 1, "anh chup trung voi A1 da co tu truoc phai bi loai"


def test_hai_anh_that_su_khac_nhau_deu_duoc_giu():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        a1 = _anh(tmp, "a1.png", seed=1)
        a2 = _anh(tmp, "a2.png", seed=2)
        anh_map = {"https://a.com/bai": a1, "https://b.com/khac": a2}
        with mock.patch("chup_trang.chup_lead_mobile", _gia_chup_lead(anh_map)), \
             mock.patch("nguon_bai.cung_tin", return_value=True):
            anh, dung_duoc, _ = vong_bu._vong_chup_nguon(
                [], "https://a.com/bai", [{"url": "https://b.com/khac"}], tmp / "wd")
        assert len(anh) == 2


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
