#!/usr/bin/env python3
"""Cong chan moi 13/09/2026 (Anthropic/Nvidia IPO): Ong Chu bam Lam lai va CHI
RO slide 6 hai lan lien tiep, nhung ca hai ban moi cua Dre deu ra dung anh cu
(chi doi ma). Hai nguyen nhan that:

  1. `_tach_ly_do_lam_lai` chi bat "slide N: ly do" NEO O DAU CAU va BAT BUOC
     dau hai cham — hai cau that Ong Chu go ("Làm lại slide 3, 6: ..." co chu
     dan truoc, "Slide 6 vẫn là hình cũ, ..." khong co hai cham) deu lot qua,
     slide ve None.
  2. Ke ca slide duoc nhan dung, khong co gi CHAN CUNG viec chon lai dung anh —
     dong "DUNG lap lai anh cu" trong task chi la chu, khong ai bat buoc theo.

Tep nay kiem phan (1) o duyet_bai._tach_ly_do_lam_lai va phan ghi-doc dHash cua
duyet_bai._ghi_cam_anh_lam_lai; cong chan o dre_nop/nop_chung da co test rieng
trong test_spec_dre.py.

Chay:  venv/bin/python tests/test_lam_lai_cam_anh.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw  # noqa: E402

import duyet_bai as db  # noqa: E402
import luat_anh  # noqa: E402


def _ve(w, h, tone, seed=7):
    im = Image.new("RGB", (w, h), tone)
    d = ImageDraw.Draw(im)
    b = seed
    for x in range(0, w, 29):
        for y in range(0, h, 31):
            b = (b * 1103515245 + 12345) % 2147483648
            d.rectangle([x, y, x + (8 + b % 30), y + (8 + (b // 7) % 30)],
                        fill=tuple(min(255, c + b % 200) for c in tone))
    return im


def test_slide_co_chu_dan_truoc_van_nhan_dung_so():
    so, ly_do = db._tach_ly_do_lam_lai(
        "Làm lại slide 3, 6: có rất nhiều hình chất lượng hơn, đừng dùng hình chỉ thuần text")
    assert so == "3, 6", so
    assert "chất lượng hơn" in ly_do


def test_slide_khong_co_hai_cham_van_nhan_dung_so():
    so, ly_do = db._tach_ly_do_lam_lai(
        "Slide 6 vẫn là hình cũ, tìm hình khác. Đã nói ko dùng hình chỉ có text")
    assert so == "6", so
    assert "vẫn là hình cũ" in ly_do        # khong mat noi dung khi khong tach duoc


def test_kieu_cu_bare_so_van_chay_binh_thuong():
    assert db._tach_ly_do_lam_lai("4: chart bi cat") == ("4", "chart bi cat")
    assert db._tach_ly_do_lam_lai("2,5: hai anh nay xau") == ("2, 5", "hai anh nay xau")


def test_tat_ca_va_rong_khong_doi():
    assert db._tach_ly_do_lam_lai("tất cả: xấu quá")[0] == "CA BO"
    assert db._tach_ly_do_lam_lai("") == (None, "")
    assert db._tach_ly_do_lam_lai("làm lại đi") == (None, "làm lại đi")


def test_ghi_cam_anh_lam_lai_chup_dung_anh_dang_o_slide_bi_neu():
    """spec.json co bia=A1 (slide 1) va slides[0]=A2 (slide 2); che slide 2 thi
    img.json phai co dHash cua A2, KHONG phai A1."""
    with tempfile.TemporaryDirectory() as t:
        wd = Path(t) / "chuan_bi" / "tin-thu"
        (wd / "goc").mkdir(parents=True)
        _ve(800, 1000, (10, 20, 30), seed=1).save(wd / "goc" / "A1.png")
        _ve(800, 1000, (200, 90, 40), seed=2).save(wd / "goc" / "A2.png")
        (wd / "spec.json").write_text(json.dumps({
            "cover": {"anh": "A1"}, "slides": [{"anh": "A2", "text": "..."}]}),
            encoding="utf-8")
        cu_state, cu_drafts = db.STATE_DIR, db.DRAFTS
        db.STATE_DIR, db.DRAFTS = Path(t), Path(t)
        try:
            db._ghi_cam_anh_lam_lai("tin-thu", [2])
            im = json.loads((Path(t) / "tin-thu.img.json").read_text(encoding="utf-8"))
            h_a1 = format(luat_anh.dhash(Image.open(wd / "goc" / "A1.png").convert("RGB")), "x")
            h_a2 = format(luat_anh.dhash(Image.open(wd / "goc" / "A2.png").convert("RGB")), "x")
            assert im["cam_anh_slide"]["2"] == [h_a2]
            assert h_a1 not in im["cam_anh_slide"]["2"]
            assert "1" not in im["cam_anh_slide"]           # khong che nham slide khac
        finally:
            db.STATE_DIR, db.DRAFTS = cu_state, cu_drafts


def test_ghi_cam_anh_lam_lai_ghep_ca_hai_ma():
    """Slide bi neu la mot cap "ghep" — phai che CA HAI ma, khong chi ma dau."""
    with tempfile.TemporaryDirectory() as t:
        wd = Path(t) / "chuan_bi" / "tin-thu"
        (wd / "goc").mkdir(parents=True)
        _ve(1200, 700, (10, 20, 30), seed=6).save(wd / "goc" / "A6.png")
        _ve(1200, 700, (200, 90, 40), seed=12).save(wd / "goc" / "A12.png")
        (wd / "spec.json").write_text(json.dumps({
            "cover": {"anh": "A1"},
            "slides": [{"anh": "A2", "text": "x"}, {"anh": "A3", "text": "y"},
                       {"anh": "A4", "text": "z"}, {"ghep": ["A6", "A12"], "text": "w"}]}),
            encoding="utf-8")
        cu_state, cu_drafts = db.STATE_DIR, db.DRAFTS
        db.STATE_DIR, db.DRAFTS = Path(t), Path(t)
        try:
            db._ghi_cam_anh_lam_lai("tin-thu", [5])          # slides[3] (ghep) = slide 2+3=5
            im = json.loads((Path(t) / "tin-thu.img.json").read_text(encoding="utf-8"))
            assert len(im["cam_anh_slide"]["5"]) == 2, im["cam_anh_slide"]
        finally:
            db.STATE_DIR, db.DRAFTS = cu_state, cu_drafts


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
