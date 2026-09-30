#!/usr/bin/env python3
"""LOW-439: mot anh hong KHONG duoc lam contact_sheet nem.

vision._classify_hide_whole (B-r2-3) giu anh hong lai thanh anh "chua nhin" khong co
kind/landscape/ratio de ca lo khong chet. Nhung contact_sheet mo lai tep va doc
a['kind'], a['landscape'] bang khoa cung -> KeyError (hoac PIL nem khi tep la rac),
ma contact_sheet chay TRUOC khi run() ghi manifest.json: engine chet KHONG manifest,
vo hieu chinh co che vua cuu.

Chay:  venv/bin/python tests/test_low439_contact_sheet_broken_image.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from PIL import Image                                           # noqa: E402
from prepare import manifest, vision                            # noqa: E402

W, COT, HANG_PX = 360, 3, 300


def _good(tmp: Path, ten: str) -> dict:
    p = tmp / f"{ten}.png"
    Image.new("RGB", (400, 300), (200, 30, 30)).save(p)
    return {"id": ten, "original_path": str(p)}


def _cut(tmp: Path, ten: str) -> dict:
    """PNG cut nua chung: PIL mo duoc header nhung khong doc het."""
    p = tmp / f"{ten}.png"
    Image.new("RGB", (400, 300), (30, 30, 200)).save(p)
    p.write_bytes(p.read_bytes()[:120])
    return {"id": ten, "original_path": str(p)}


def _rac(tmp: Path, ten: str) -> dict:
    p = tmp / f"{ten}.png"
    p.write_bytes(b"khong phai anh")
    return {"id": ten, "original_path": str(p)}


def _seen(tmp: Path, anh: list) -> list:
    wd = tmp / "wd"
    wd.mkdir(exist_ok=True)
    # tieu_de rong: classify khong hoi vision, chi do hinh hoc -> test khong can mang
    return [vision._classify_hide_whole(a, wd, "") for a in anh]


def test_anh_cut_khong_lam_sheet_chet():
    with tempfile.TemporaryDirectory() as s:
        tmp = Path(s)
        anh = _seen(tmp, [_good(tmp, "A1"), _cut(tmp, "A2")])
        assert "kind" not in anh[1] and anh[1]["uses"] == [], anh[1]     # dung la anh "chua nhin"
        out = tmp / "sheet.png"
        manifest.contact_sheet(anh, out)                                 # truoc LOW-439: KeyError 'kind'
        sheet = Image.open(out)
        assert sheet.size == (W * COT, HANG_PX), sheet.size
        # o A1 (goc tren trai) van la thumbnail do — cac anh lanh khong bi anh hong keo theo
        assert sheet.getpixel((8 + 40, 8 + 40)) == (200, 30, 30), sheet.getpixel((48, 48))


def test_tep_rac_khong_lam_sheet_chet():
    with tempfile.TemporaryDirectory() as s:
        tmp = Path(s)
        anh = _seen(tmp, [_rac(tmp, "A1"), _good(tmp, "A2")])
        out = tmp / "sheet.png"
        manifest.contact_sheet(anh, out)                                 # truoc LOW-439: PIL nem
        assert out.exists()


def test_anh_lanh_van_ghi_nhan_day_du():
    """Duong binh thuong khong doi: du khoa thi nhan van co loai/MAT/NGANG."""
    with tempfile.TemporaryDirectory() as s:
        tmp = Path(s)
        a = _seen(tmp, [_good(tmp, "A1")])[0]
        # mot mau phang thi classify goi la "chart" — o day chi can DU KHOA nhu duong that
        assert a["kind"] in ("photo", "chart") and a["w"] == 400 and "landscape" in a, a
        out = tmp / "sheet.png"
        manifest.contact_sheet([a], out)
        assert Image.open(out).size == (W * COT, HANG_PX)


def test_sheet_chay_trong_ca_lo_moi_anh_deu_hong():
    with tempfile.TemporaryDirectory() as s:
        tmp = Path(s)
        anh = _seen(tmp, [_cut(tmp, "A1"), _rac(tmp, "A2"), _cut(tmp, "A3"), _rac(tmp, "A4")])
        out = tmp / "sheet.png"
        manifest.contact_sheet(anh, out)
        assert Image.open(out).size == (W * COT, HANG_PX * 2)


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
