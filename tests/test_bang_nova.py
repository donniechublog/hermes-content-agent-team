#!/usr/bin/env python3
"""Cong chan cho bo bang xep hang cua Nova.

Vi sao co tep nay: 06/09/2026 mo tu 12 len 20 bang. Ba loi ben duoi deu la loai
KHONG BAO GI CA — script van chay, bao cao van in, chi la Nova mat tin hoac mat
link, va phai vai ngay sau moi co nguoi de y:

  1. Them bang ma quen khai NHAN_BANG  -> muc "leo hang" in ra ma khoa tho
  2. Them bang ma quen khai LINK_BANG  -> muc BAT BUOC ra link RONG, vai nop
     tin khong co nguon
  3. In danh sach BAT BUOC hai lan     -> ton 5.600 ky tu o cuoi bao cao, dung
     cho de bi tran cat mat truoc tien

Chay: venv/bin/python tests/test_bang_nova.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import bat_buoc                                             # noqa: E402
import scan_models as s                                     # noqa: E402

KHOA_BANG = s.KHOA_BANG

qua = loi = 0


def kiem(ten, dieu_kien, ghi_chu=""):
    global qua, loi
    if dieu_kien:
        qua += 1
        print(f"OK   {ten}")
    else:
        loi += 1
        print(f"HONG {ten}  {ghi_chu}")


def test_moi_bang_co_nhan():
    thieu = [k for k in KHOA_BANG if k not in s.NHAN_BANG]
    kiem("test_moi_bang_co_nhan", not thieu,
         f"thieu NHAN_BANG cho: {thieu}")


def test_moi_bang_co_link():
    # `hf` khong nam trong KHOA_BANG (khong phai bang xep hang) nhung muc bat
    # buoc cua no tu mang link rieng — kiem rieng o duoi.
    thieu = [k for k in KHOA_BANG if not bat_buoc.LINK_BANG.get(k)]
    kiem("test_moi_bang_co_link", not thieu,
         f"thieu LINK_BANG cho: {thieu} -> muc bat buoc se ra link rong")


def test_link_bang_deu_la_url():
    xau = [k for k, v in bat_buoc.LINK_BANG.items() if not v.startswith("https://")]
    kiem("test_link_bang_deu_la_url", not xau, f"khong phai https: {xau}")


def test_muc_hf_co_link_rieng():
    l = bat_buoc.link_goi_y({"loai": "hf", "ten": "deepseek-ai/X",
                             "link": "https://huggingface.co/deepseek-ai/X"})
    kiem("test_muc_hf_co_link_rieng", l == "https://huggingface.co/deepseek-ai/X")


def test_so_bang_khop_ban_ke_khai():
    kiem("test_so_bang_khop_ban_ke_khai", s.SO_BANG == len(KHOA_BANG),
         f"SO_BANG={s.SO_BANG} nhung ke khai {len(KHOA_BANG)} bang")
    kiem("test_khong_trung_khoa_bang", len(set(KHOA_BANG)) == len(KHOA_BANG),
         "co khoa bang bi khai hai lan")


def test_main_kiem_lech_ban_ke_khai():
    """main() phai tu doi chieu bang_so voi KHOA_BANG — them bang ma quen khai
    thi state khong co moc, va 'leo hang' cua bang do im lang mai mai."""
    src = Path(s.__file__).read_text(encoding="utf-8")
    kiem("test_main_kiem_lech_ban_ke_khai",
         "set(bang_so) ^ set(KHOA_BANG)" in src)


def test_khong_in_bat_buoc_hai_lan():
    """quet_chuan_bi PHAI goi scan_models voi --khong-bat-buoc, vi chinh no da
    in danh sach do mot lan roi (qua _bat_buoc, nam NGOAI vung cat)."""
    src = (ROOT / "quet_chuan_bi.py").read_text(encoding="utf-8")
    i = src.find("def brief_nova")
    j = src.find("def brief_market", i)
    kiem("test_khong_in_bat_buoc_hai_lan", "--khong-bat-buoc" in src[i:j],
         "brief_nova goi scan_models ma khong co --khong-bat-buoc")


def test_bao_cao_bi_cat_thi_noi_ra():
    """Cat cam lang la loi cu: Nova doc het bao cao roi ket luan 'khong co gi',
    trong khi that ra phan duoi da bi xen mat."""
    import quet_chuan_bi as q
    dai = "x" * (q.TRAN_BAO_CAO + 5000)
    ra = q._cat(dai)
    kiem("test_bao_cao_bi_cat_thi_noi_ra",
         "BAO CAO BI CAT" in ra and len(ra) < len(dai),
         "cat ma khong bao -> vai tuong nham la da doc het")
    ngan = "y" * 100
    kiem("test_bao_cao_ngan_thi_khong_dong_gi", q._cat(ngan) == ngan)


def test_tran_in_an_co_can_tren():
    """Ba muc nay truoc 06/09 khong co `[:n]`, mot ngay xau nuot sach phan duoi."""
    kiem("test_tran_in_an_co_can_tren",
         all(isinstance(v, int) and 0 < v < 100
             for v in (s.TRAN_MOI, s.TRAN_BM, s.TRAN_GH, s.TRAN_HF, s.TRAN_BANG)))


def test_bang_hong_thi_noi_ra():
    """Bang hong truoc day chi... khong in ra. Nova doc bao cao khong thay
    Terminal-Bench dau thi ket luan 'khong co gi moi o do' — trong khi that ra
    la khong lay duoc. Hai ket luan khac han nhau."""
    import contextlib
    import io as _io
    b = _io.StringIO()
    with contextlib.redirect_stdout(b):
        s._in_bao_cao({"model_moi": [], "bang_hong": ["tbench", "hle"]}, 7)
    ra = b.getvalue()
    kiem("test_bang_hong_thi_noi_ra",
         "NGUON KHONG LAY DUOC" in ra and "Terminal-B" in ra and "HLE" in ra,
         "khong bao ten bang hong -> vai tuong la bang do khong co tin")
    b2 = _io.StringIO()
    with contextlib.redirect_stdout(b2):
        s._in_bao_cao({"model_moi": [], "bang_hong": []}, 7)
    kiem("test_khong_hong_thi_im", "NGUON KHONG LAY DUOC" not in b2.getvalue())


def test_diem_cao_hon_la_tot_hon():
    """so_hang() gia dinh hang 1 = tot nhat. Bang STT cua AA cho ti le LOI (WER,
    THAP hon la tot hon) nen fetch_aa_media phai doi thanh do chinh xac; quen
    doi thi bang xep nguoc ma khong co gi bao."""
    src = s.__file__ and Path(s.__file__).read_text(encoding="utf-8")
    i = src.find("if ma == \"stt\"")
    doan = src[i:i + 700]
    kiem("test_diem_cao_hon_la_tot_hon", "(1 - float(wer))" in doan,
         "STT phai doi WER -> do chinh xac truoc khi vao bang")


if __name__ == "__main__":
    for f in list(globals()):
        if f.startswith("test_"):
            globals()[f]()
    print(f"\n{qua}/{qua + loi} test qua")
    sys.exit(1 if loi else 0)
