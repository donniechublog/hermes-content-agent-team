#!/usr/bin/env python3
"""Boc hinh that trong paper (arxiv_hinh.py) — cac ham THUAN, khong PDF khong mang.

Vi sao co tep nay: `vung_hinh` la mot chuoi luat hinh hoc, moi luat sinh ra tu
MOT paper that lam hong ban truoc do (ACE, BERT, DeepSeek-R1, Attention). Hong
o day thi khong ai thay: engine van chay, van ra anh, chi la anh cat sai — nua
dong chay dau trang, cut mat ten bieu do, hoac nguyen mot trang chu hai cot.
Moi test duoi day la mot ca that, ghi ro paper nao.

Truc toa do cua MuPDF: y TANG khi di XUONG. Hinh nam TREN chu thich nghia la y
nho hon.

Chay:  venv/bin/python tests/test_arxiv_hinh.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TRANG = (0.0, 0.0, 612.0, 792.0)          # letter, nhu ACE / Attention


def _k(x0, y0, x1, y1, text=""):
    return (x0, y0, x1, y1, text)


DOAN = "x" * 200                          # khoi chu chac chan la than bai


# ------------------------------------------------------------- la_chu_thich
def test_nhan_dung_cac_kieu_chu_thich():
    import arxiv_hinh as ah
    assert ah.la_chu_thich("Figure 1: Overall Performance Results.")[:2] == ("figure", 1)
    assert ah.la_chu_thich("Fig. 2. Scaled attention")[:2] == ("figure", 2)
    assert ah.la_chu_thich("Table 3: GLUE results")[:2] == ("table", 3)
    # DeepSeek-R1 dung gach dung thay hai cham
    assert ah.la_chu_thich("Figure 1 | (a) AIME accuracy of DeepSeek-R1-Zero")[:2] == ("figure", 1)


def test_khong_nham_cau_than_bai_nhac_toi_hinh():
    """DeepSeek-R1 co hai doan mo dau bang tham chieu hinh. Nhan nham chung la
    chu thich thi engine cat mot vung chu giua bai roi dan len slide."""
    import arxiv_hinh as ah
    for t in ["Figure 1(a) depicts the performance trajectory of DeepSeek-R1-Zero",
              "Table 3 summarizes the performance of DeepSeek-R1 across stages",
              "As shown in Figure 1, we represent the input question",
              "Figure 1"]:
        assert ah.la_chu_thich(t) is None, f"nhan nham: {t!r}"


# --------------------------------------------------------- chu_thich_du_dong
def test_gom_du_cac_dong_chu_thich_khi_pdf_cat_tung_dong():
    """DeepSeek-R1: MuPDF tra MOI DONG mot khoi. Khong gom thi anh cut mat cac
    dong sau cua chu thich."""
    import arxiv_hinh as ah
    cap = _k(71, 263, 524, 275, "Figure 1 | (a) AIME accuracy of DeepSeek-R1-Zero during training.")
    khoi = [cap,
            _k(71, 276, 524, 288, "problem as input and a number as output, illustrated in Table 32."),
            _k(71, 289, 524, 301, "described in Supplementary D.1. The baseline is the average score.")]
    assert ah.chu_thich_du_dong(cap, khoi)[3] == 301


def test_khong_nuot_doan_than_bai_ngay_duoi_chu_thich():
    """BERT: chu thich 5 dong nam TRON mot khoi (cao 60pt). Neu do khe theo
    chieu cao CA KHOI thi doan than bai cach 30pt bi gom vao, roi chuoi tiep
    xuong het trang — anh ra la ca trang chu hai cot."""
    import arxiv_hinh as ah
    cap = _k(72, 90, 540, 150, "Figure 1: Overall pre-training\nand fine-tuning\nprocedures\nfor\nBERT.")
    khoi = [cap, _k(72, 180, 300, 400, DOAN)]
    assert ah.chu_thich_du_dong(cap, khoi)[3] == 150


# ----------------------------------------------------------------- vung_hinh
def test_cat_dung_hinh_va_chu_thich():
    import arxiv_hinh as ah
    cap = _k(108, 652, 504, 673, "Figure 1: Overall Performance Results.")
    khoi = [_k(144, 268, 468, 475, DOAN),          # tom tat
            _k(122, 618, 153, 640, "Base LLM"),    # nhan cot trong bieu do
            cap]
    ve = [(117.9, 526.9, 494.1, 641.9)]            # khung bieu do
    hop = ah.vung_hinh(cap, khoi, ve, TRANG)
    assert hop is not None
    assert abs(hop[1] - (526.9 - ah.DEM)) < 0.01, hop      # met tren = dinh khung ve
    assert abs(hop[3] - (673 + ah.DEM)) < 0.01, hop        # met duoi = day chu thich
    assert hop[0] <= 108 and hop[2] >= 504


def test_net_ve_tran_ra_ngoai_trang_khong_keo_vung_cat_theo():
    """ACE: cot bieu do duoc ve bang duong keo dai roi cat bang clip — hop cua
    net ve cao toi y=964 tren trang 792. Cat theo hop do thi anh nuot ca doan
    van duoi chu thich va tran khoi trang."""
    import arxiv_hinh as ah
    cap = _k(108, 652, 504, 673, "Figure 1: Overall Performance Results.")
    khoi = [_k(144, 268, 468, 475, DOAN), cap]
    ve = [(117.9, 526.9, 494.1, 641.9), (145.4, 609.5, 158.4, 964.9)]
    hop = ah.vung_hinh(cap, khoi, ve, TRANG)
    assert hop[3] <= 673 + ah.DEM + 0.01, hop
    assert hop[3] <= TRANG[3]


def test_bo_chay_dau_trang_va_duong_ke_cua_no():
    """ACE hinh 4: hinh nam ngay dau trang. Duong ke mo cua chay dau (y=39.15)
    lot vao dai thi anh bat dau tu do va cong them nua dong chu
    "Published as a conference paper at ICLR 2026"."""
    import arxiv_hinh as ah
    cap = _k(108, 400, 504, 430, "Figure 4: The ACE Framework.")
    khoi = [_k(108, 28, 293, 38, "Published as a conference paper at ICLR 2026"), cap]
    ve = [(108, 39.15, 504, 39.15), (120, 120, 500, 380)]
    hop = ah.vung_hinh(cap, khoi, ve, TRANG)
    assert hop[1] > 41, f"cat cham vao chay dau trang: {hop}"


def test_dong_chu_rong_BEN_TRONG_hinh_khong_cat_cut_hinh():
    """BERT hinh 1: trong hinh co nhung hang o token trai rong bang cot, trong
    het nhu mot dong than bai. Chot moc ngay o dong do thi anh chi con mot vet
    duoi cung cua hinh (do that: ti le 5.4:1, bi loai)."""
    import arxiv_hinh as ah
    cap = _k(72, 300, 540, 360, "Figure 1: Overall pre-training and fine-tuning procedures for BERT.")
    khoi = [_k(72, 40, 540, 90, DOAN),                        # than bai that
            _k(90, 200, 520, 214, "E[CLS] E1 ... EN E[SEP] E1' ... EM'"),   # chu trong hinh
            cap]
    ve = [(80, 100, 530, 290)]
    hop = ah.vung_hinh(cap, khoi, ve, TRANG)
    assert hop[1] < 105, f"vung cat bi cat cut o dong chu trong hinh: {hop}"


def test_ten_bieu_do_ke_sat_khung_van_duoc_lay():
    """DeepSeek-R1: ten bieu do ("DeepSeek-R1-Zero AIME accuracy during
    training") nam ngay TREN khung ve, khong cham vao khung — khong keo hop ra
    thi anh cat cut dau ten."""
    import arxiv_hinh as ah
    cap = _k(71, 263, 524, 275, "Figure 1 | (a) AIME accuracy during training.")
    khoi = [_k(99, 83, 270, 90, "DeepSeek-R1-Zero AIME accuracy during training"), cap]
    ve = [(77.9, 91.6, 291.0, 247.3)]
    hop = ah.vung_hinh(cap, khoi, ve, TRANG)
    assert hop[1] <= 83, f"cut mat ten bieu do: {hop}"


def test_khong_co_do_hoa_thi_khong_boc():
    """Chu thich ma tren no khong co net ve nao — khong doan mo, tra None."""
    import arxiv_hinh as ah
    cap = _k(108, 652, 504, 673, "Figure 1: Overall Performance Results.")
    assert ah.vung_hinh(cap, [_k(144, 268, 468, 475, DOAN), cap], [], TRANG) is None


def test_bo_qua_do_hoa_cot_khac_trong_bo_cuc_hai_cot():
    import arxiv_hinh as ah
    cap = _k(60, 400, 290, 420, "Figure 2: BERT input representation.")
    khoi = [_k(60, 100, 290, 300, DOAN), cap]
    ve = [(70, 320, 280, 390), (320, 100, 540, 390)]       # cot phai: hinh khac
    hop = ah.vung_hinh(cap, khoi, ve, TRANG)
    assert hop[2] < 300, f"nuot ca cot ben kia: {hop}"


# --------------------------------------------------------------- pdf_cua_link
def test_nhan_link_paper():
    import arxiv_hinh as ah
    for u in ["https://arxiv.org/abs/2510.04618", "https://arxiv.org/pdf/2510.04618v3",
              "https://arxiv.org/html/2510.04618v3"]:
        assert ah.pdf_cua_link(u) == "https://arxiv.org/pdf/2510.04618", u
    assert ah.pdf_cua_link("https://openreview.net/x.pdf") == "https://openreview.net/x.pdf"
    for u in ["https://openai.com/index/gpt-5", "", "https://arxiv.org/list/cs.AI/recent"]:
        assert ah.pdf_cua_link(u) is None, u


if __name__ == "__main__":
    ham = [v for k, v in list(globals().items()) if k.startswith("test_")]
    loi = 0
    for h in ham:
        try:
            h()
            print(f"OK   {h.__name__}")
        except AssertionError as e:
            loi += 1
            print(f"FAIL {h.__name__}: {e}")
    print(f"\n{len(ham) - loi}/{len(ham)} test qua")
    sys.exit(1 if loi else 0)
