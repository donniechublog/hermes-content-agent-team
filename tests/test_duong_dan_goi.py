#!/usr/bin/env python3
"""Hằng số đường dẫn trong gói `chuan_bi/` phải trỏ về GỐC DỰ ÁN.

Su co 09/09/2026 (commit 7b72620): khi tach goi A1, dong
`ROOT = Path(__file__).resolve().parent` duoc chep NGUYEN VAN tu
image_prepare.py o goc sang chuan_bi/common.py. Tep moi nam sau mot cap thu muc
nen mot `.parent` chi ra `chuan_bi/`, khien `DRAFTS = ROOT / "drafts"` thanh
`chuan_bi/drafts` (rong). Moi lenh doc `drafts/<id>.meta.json` bao "Khong thay
... task nay khong do approve_service tao?" du tep TON TAI — bat duoc khi
kite_submit.py chay lai mot draft that.

Vi sao khong luoi nao bat duoc: pyflakes thay ROOT co dinh nghia va co dung nen
im; `import chuan_bi.chung` chay binh thuong; con suite thi monkeypatch DRAFTS
va workdir nen khong bao gio cham duong dan THAT. Tep nay chinh la cho trong do.

Chay:  venv/bin/python tests/test_duong_dan_goi.py
"""
import sys
from pathlib import Path

GOC = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GOC))
import env_load                                               # noqa: E402
import image_prepare as cb                                     # noqa: E402
import chuan_bi.common as common                                # noqa: E402


def test_ROOT_cua_goi_la_goc_du_an():
    """Khong phai chuan_bi/. Day la dung dong da vo hom 09/09."""
    assert common.ROOT == GOC, \
        f"chuan_bi.common.ROOT tro sai: {common.ROOT} (phai la {GOC})"


def test_ROOT_khop_env_load():
    """env_load.ROOT la ban goc su that; hai cho lech nhau la mot cho sai."""
    assert common.ROOT == Path(env_load.ROOT).resolve(), \
        f"{common.ROOT} != env_load.ROOT {env_load.ROOT}"


def test_DRAFTS_nam_ngay_duoi_goc_va_co_anh_em_that():
    """`drafts/` phai la thu muc drafts THAT o goc — canh cac tep nguon, khong
    phai mot duong dan long trong goi."""
    assert common.DRAFTS == GOC / "drafts", common.DRAFTS
    assert (common.DRAFTS.parent / "image_prepare.py").exists(), \
        f"cha cua DRAFTS khong phai goc du an: {common.DRAFTS.parent}"


def test_mat_tien_anh_chuan_bi_tro_cung_cho():
    """Vai/test goi qua `cb.DRAFTS`; no chi la tai xuat cua common.DRAFTS nen hai
    ben lech nhau la co mot ban sao thu hai dang song."""
    assert cb.ROOT == common.ROOT and cb.DRAFTS == common.DRAFTS, (cb.DRAFTS, common.DRAFTS)


def test_moi_hang_so_duong_dan_trong_goi_deu_duoi_goc():
    """Quet moi Path cap module cua goi: khong cai nao duoc ro ra ngoai goc du
    an, va khong cai nao duoc nam trong chuan_bi/ (dau hieu thieu .parent)."""
    import importlib
    goi = GOC / "chuan_bi"
    xau = []
    for p in sorted(goi.glob("*.py")):
        m = importlib.import_module(f"chuan_bi.{p.stem}")
        for ten in dir(m):
            if ten.startswith("__"):
                continue
            gt = getattr(m, ten)
            if not isinstance(gt, Path):
                continue
            gt = gt.resolve()
            if GOC not in gt.parents and gt != GOC:
                xau.append(f"{p.name}.{ten} = {gt} (ngoai goc)")
            elif goi == gt or goi in gt.parents:
                xau.append(f"{p.name}.{ten} = {gt} (nam TRONG chuan_bi/ — thieu .parent?)")
    assert not xau, "hang so duong dan sai cho:\n  " + "\n  ".join(xau)


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
