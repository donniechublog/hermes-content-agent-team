#!/usr/bin/env python3
"""Bảng vai dẫn xuất phải khớp CHÍNH XÁC bảng viết tay cũ (issue A4/F1).

Tri thuc ve vai tung nam rai sau cho trong duyet_giao_viec cong ba map "slug ->
ten" chep tay o noi khac. `vai.py` gom lai mot cho va sinh lai cac bang do.

Tep nay giu hai thu:
  1. HOP DONG KHONG DOI: cac bang duoi day duoc chep NGUYEN VAN tu ban viet tay
     truoc khi gom (git 3a18f79:duyet_giao_viec.py). Bang dan xuat lech mot khoa
     la mot duong hong THAT — `SLUG_CU` sai thi task khong ai nhan va nam
     'ready' mai (su co 01/09/2026), `TEN_SANG_CAP` thieu mot chu thi ca lenh
     chon bi tu choi roi gui nham topic (su co 06/09/2026 voi "kites").
  2. Them mot vai chi ton MOT dong: kiem bang chinh bang dang ky, khong phai
     bang cach doc code.

Chay:  venv/bin/python tests/test_vai.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import vai                                                    # noqa: E402

# ---- chep NGUYEN VAN tu ban viet tay truoc khi gom (3a18f79) ----------------
VAI_ANH_CU = {
    "designer": "designer", "img": "designer", "anh": "designer",
    "ethan": "designer",
    "carousel": "carousel", "cr": "carousel",
    "dre": "carousel",
    "carousel-edu": "carousel-edu", "edu": "carousel-edu",
    "kite": "carousel-edu",
    "kites": "carousel-edu",
}
TEN_SANG_CAP_CU = dict(VAI_ANH_CU)
TEN_SANG_CAP_CU.update({"writer": "designer", "cap": "designer", "miles": "designer"})
VAI_CAROUSEL_CU = {"carousel"}
VAI_EDU_CU = {"carousel-edu"}
TEN_VAI_ANH_CU = {"designer": "Ethan", "carousel": "Dre", "carousel-edu": "Kite"}
TEN_VAI_VIET_CU = {"writer": "Miles"}
SLUG_CU_CU = {"miles": "writer", "dre": "carousel", "ethan": "designer",
              "chad": "designer", "heller": "carousel", "kite": "carousel-edu",
              "finn": "scout", "vera": "market", "jean": "teaser", "ada": "analyst"}
TEN_HIEN_CU = {"designer": "Ethan", "carousel": "Dre", "carousel-edu": "Kite",
               "writer": "Miles", "scout": "Finn", "nova": "Nova", "market": "Vera",
               "teaser": "Cape", "analyst": "Ada", "gin": "Gin", "itachi": "Itachi",
               "bob": "Bob"}


def _khop(ten, moi, cu):
    thieu = {k: v for k, v in cu.items() if k not in moi}
    thua = {k: v for k, v in moi.items() if k not in cu}
    lech = {k: (cu[k], moi[k]) for k in cu if k in moi and cu[k] != moi[k]}
    assert not (thieu or thua or lech), \
        f"{ten} lech ban viet tay:\n  thieu={thieu}\n  thua={thua}\n  lech={lech}"


def test_VAI_ANH_khop_ban_cu():
    _khop("VAI_ANH", vai.VAI_ANH, VAI_ANH_CU)


def test_TEN_SANG_CAP_khop_ban_cu():
    """Thieu mot chu o day la ca lenh chon bi tu choi (su co "kites" 06/09)."""
    _khop("TEN_SANG_CAP", vai.TEN_SANG_CAP, TEN_SANG_CAP_CU)


def test_SLUG_CU_khop_ban_cu():
    """Sai o day la task khong ai nhan, nam 'ready' mai (su co 01/09)."""
    _khop("SLUG_CU", vai.SLUG_CU, SLUG_CU_CU)


def test_TEN_VAI_ANH_va_VIET_khop_ban_cu():
    _khop("TEN_VAI_ANH", vai.TEN_VAI_ANH, TEN_VAI_ANH_CU)
    _khop("TEN_VAI_VIET", vai.TEN_VAI_VIET, TEN_VAI_VIET_CU)


def test_TEN_HIEN_khop_ban_cu():
    _khop("TEN_HIEN", vai.TEN_HIEN, TEN_HIEN_CU)


def test_VAI_CAROUSEL_va_EDU_khop_ban_cu():
    assert vai.VAI_CAROUSEL == VAI_CAROUSEL_CU, vai.VAI_CAROUSEL
    assert vai.VAI_EDU == VAI_EDU_CU, vai.VAI_EDU


def test_mac_dinh_khong_doi():
    assert vai.MAC_DINH_ANH == "designer" and vai.MAC_DINH_VIET == "writer"


# ---- tinh chat cua ban dang ky ---------------------------------------------
def test_slug_that_nhan_ten_cu_va_giu_nguyen_chu_la():
    assert vai.slug_that("dre") == "carousel"
    assert vai.slug_that("Jean") == "teaser", "phai khong phan biet hoa thuong"
    assert vai.slug_that("carousel") == "carousel", "slug hien tai giu nguyen"
    assert vai.slug_that("khong-co-that") == "khong-co-that", \
        "chu la phai tra NGUYEN VAN de chuan_assignee con bao loi tu te"


def test_ten_hien_roi_ve_slug_khi_chua_khai():
    assert vai.ten_hien("carousel") == "Dre"
    assert vai.ten_hien("chua-khai") == "chua-khai"


def test_moi_vai_anh_deu_co_renderer():
    thieu = [v.slug for v in vai.VAI.values() if v.nhan_anh and not v.renderer]
    assert not thieu, f"vai dung anh ma khong khai renderer: {thieu}"


def test_khong_alias_nao_dam_len_slug_cua_vai_khac():
    """Mot chu vua la slug cua vai A vua la alias cua vai B thi lookup thanh
    may rui theo thu tu chen — chan tu trong ban dang ky."""
    xau = []
    for v in vai.VAI.values():
        for chu in v.go + v.slug_cu:
            if chu in vai.VAI and chu != v.slug:
                xau.append(f"{chu!r} la slug cua {chu} nhung lam alias cho {v.slug}")
    assert not xau, xau


def test_them_vai_chi_ton_mot_dong():
    """F1: them mot dong vao VAI la moi bang dan xuat co ngay, khong phai sua
    tam cho. Kiem bang chinh ban dang ky chu khong doc code."""
    them = vai.Vai("thu_nghiem", "Thu", go=("tn",), renderer="card", nhan_anh=True)
    v2 = dict(vai.VAI, thu_nghiem=them)
    ten_hien = {v.slug: v.ten for v in v2.values()}
    anh = {}
    for v in v2.values():
        if v.nhan_anh:
            anh[v.slug] = v.slug
            for g in v.go:
                anh[g] = v.slug
    assert ten_hien["thu_nghiem"] == "Thu"
    assert anh["tn"] == "thu_nghiem" and anh["thu_nghiem"] == "thu_nghiem"
    assert {v.slug for v in v2.values() if v.renderer == "card"} == {"designer", "thu_nghiem"}


# ---- tai lieu khong duoc lech ban dang ky (audit C6) ------------------------
def _bang_vai_trong_readme():
    """(ten, slug) tu bang 'Doi hinh' trong README: `| Ten | \\`slug\\` | ... |`."""
    import re
    doc = (ROOT / "README.md").read_text(encoding="utf-8")
    return {m.group(2): m.group(1).strip()
            for m in re.finditer(r"^\|\s*([A-ZĐ][\wÀ-ỹ]*)\s*\|\s*`([a-z-]+)`\s*\|", doc, re.M)}


def test_README_goi_dung_ten_vai_nhu_ban_dang_ky():
    """Su co C6: tai lieu con goi Kite/Cape bang ten persona cu (Jean, Heller...)
    trong khi ma da doi. Ten trong bang README phai khop vai.TEN_HIEN."""
    lech = {slug: (ten, vai.TEN_HIEN.get(slug))
            for slug, ten in _bang_vai_trong_readme().items()
            if vai.TEN_HIEN.get(slug) != ten}
    assert not lech, f"README goi ten khac ban dang ky (slug: README vs vai.py): {lech}"


def test_moi_vai_trong_ban_dang_ky_deu_co_trong_README():
    """Them mot dong vao vai.py ma quen ghi vao bang README thi doi khong biet
    vai do ton tai — F1 hua 'them vai = mot dong registry', cai gia la phai
    dong bo tai lieu ngay canh."""
    thieu = sorted(set(vai.VAI) - set(_bang_vai_trong_readme()))
    assert not thieu, f"co trong vai.py ma khong co trong bang README: {thieu}"


def test_khong_vai_la_nao_trong_README():
    thua = sorted(set(_bang_vai_trong_readme()) - set(vai.VAI))
    assert not thua, f"README ke vai khong co trong vai.py: {thua}"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
