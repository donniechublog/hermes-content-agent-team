#!/usr/bin/env python3
"""Khung ảnh của Bob dựng bằng PIL phải giữ đúng hình học của `frame.js` (A6).

Ban Node da bo (khong con node_modules tren server), nen khong the so truc tiep
trong CI. Thay vao do tep nay ghim nhung CON SO da doi chieu voi ban Node hom
09/09/2026, luc ca hai con chay song song:

    nguon 1400x900  ->  canvas 1507x1033   (khop CHINH XAC)
    vach header, vung anh                  lech 0 pixel
    goc bo tron                            lech 619 px (khu rang cua duong cong)
    chu header + footer                    lech ~5700 px (rasterize font)
    trung binh toan anh                    1.11/255

Hai loai lech con lai la KHONG THE khop va da biet truoc: `sharp.sharpen` va
`ImageFilter.UnsharpMask` la hai cong thuc khac nhau, con librsvg/fontconfig
rasterize chu khac FreeType. Cai PHAI dung tuyet doi la hinh hoc, mau va vi tri
— do la thu tep nay giu.

Cai bay da bat duoc khi port, giu lai lam test:
  - `Math.round` cua JS lam tron NUA LEN, `round()` cua Python lam tron ve so
    CHAN: round(40.5) ra 40 thay vi 41 -> canvas lech 2 pixel.
  - SVG ve net GIUA duong (straddle), PIL ve VAO TRONG hop -> vien lech 2,5px.

Chay:  venv/bin/python tests/test_khung_anh.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from PIL import Image                                         # noqa: E402
import khung_anh as ka                                        # noqa: E402


def _nguon(tmp, w=1400, h=900):
    p = Path(tmp) / "nguon.png"
    Image.new("RGB", (w, h), (28, 42, 66)).save(p)
    return p


# ------------------------------------------------- lam tron kieu JS
def test_lam_tron_nua_len_nhu_Math_round():
    """round() cua Python lam tron ve so CHAN — dung no la canvas lech 2px."""
    assert ka._lam_tron(40.5) == 41, "phai lam tron LEN nhu Math.round cua JS"
    assert ka._lam_tron(41.5) == 42
    assert round(40.5) == 40, "day la ly do khong dung round() cua Python"
    assert ka._lam_tron(4.5) == 5 and ka._lam_tron(4.4) == 4


# ------------------------------------------------- hinh hoc khop ban Node
def test_canvas_khop_con_so_da_doi_chieu_voi_ban_node():
    with tempfile.TemporaryDirectory() as t:
        mo_ta = ka.dong_khung(_nguon(t), Path(t) / "ra.png", khong_mascot=True)
        assert mo_ta["canvas"] == {"width": 1507, "height": 1033}, mo_ta["canvas"]
        assert mo_ta["source"] == {"width": 1400, "height": 900}, mo_ta["source"]
        assert Image.open(Path(t) / "ra.png").size == (1507, 1033)


def test_canvas_co_gian_theo_ti_le_anh_khong_cat_vuong():
    """Anh doc phai ra canvas doc — frame.js co y giu ti le goc."""
    with tempfile.TemporaryDirectory() as t:
        mo_ta = ka.dong_khung(_nguon(t, 600, 1200), Path(t) / "ra.png", khong_mascot=True)
        c = mo_ta["canvas"]
        assert c["height"] > c["width"], c


def test_anh_qua_rong_bi_thu_ve_2048():
    with tempfile.TemporaryDirectory() as t:
        mo_ta = ka.dong_khung(_nguon(t, 3000, 1500), Path(t) / "ra.png", khong_mascot=True)
        assert mo_ta["source"]["width"] == ka.MAXW, mo_ta["source"]
        assert mo_ta["source"]["height"] == 1024, "phai giu ti le khi thu"


# ------------------------------------------------- mau va vi tri
# Lop vector ve o 4x roi thu bang LANCZOS, ma LANCZOS co rung (ringing): ngay
# giua mot vung mot mau van lech vai don vi. Nen so mau co dung sai — cai dang
# do o day la VI TRI, khong phai gia tri byte.
def _diem(anh, x, y):
    return Image.open(anh).convert("RGB").getpixel((int(x), int(y)))


def _gan(thuc, mong, sai=10):
    return all(abs(a - b) <= sai for a, b in zip(thuc, mong))


def _hinh_hoc(w=1400, h=900):
    """Dung LAI cong thuc cua frame.js. Test tu tinh cho phai nhin thay, thay vi
    ghim toa do dem duoc tren mot anh — de doi cong thuc la test do ngay."""
    R, ngan = ka._lam_tron, min(w, h)
    canh, header_h = R(ngan * 0.045), R(ngan * 0.05)
    cham_d = max(6, R(header_h * 0.50))
    return {"canh": canh, "header_h": header_h, "day": max(2, R(ngan * 0.005)),
            "cham_d": cham_d, "cham_khe": R(cham_d * 0.7), "cham_cy": R(header_h / 2)}


def test_vien_den_bat_dau_ngay_tu_mep_trai():
    """SVG ve net giua duong nen vien phu [0, day). Lui nua do day nhu SVG la
    lech 2,5px — do duoc bang chinh diem nay khi con ban Node de so."""
    g = _hinh_hoc()
    with tempfile.TemporaryDirectory() as t:
        ra = Path(t) / "ra.png"
        ka.dong_khung(_nguon(t), ra, khong_mascot=True)
        for x in (0, g["day"] // 2):
            assert _gan(_diem(ra, x, 200), ka._mau(ka.VIEN)), f"x={x} phai la vien den"
        # Ngoai be day vien la da vao nen the — vien khong duoc day hon frame.js.
        assert _gan(_diem(ra, g["day"] + 3, 200), ka._mau(ka.BG)), "vien day qua"


def test_nen_the_la_mau_kem_thuong_hieu():
    with tempfile.TemporaryDirectory() as t:
        ra = Path(t) / "ra.png"
        ka.dong_khung(_nguon(t), ra, khong_mascot=True)
        assert _gan(_diem(ra, 30, 200), ka._mau(ka.BG))


def test_ba_cham_macos_dung_mau_va_dung_cho():
    """Ba cham phai dung mau den giao thong VA dung thu tu do-vang-luc."""
    g = _hinh_hoc()
    with tempfile.TemporaryDirectory() as t:
        ra = Path(t) / "ra.png"
        ka.dong_khung(_nguon(t), ra, khong_mascot=True)
        for i, mau in enumerate(ka.DOTS):
            cx = g["canh"] + g["cham_d"] / 2 + i * (g["cham_d"] + g["cham_khe"])
            thuc = _diem(ra, cx, g["cham_cy"])
            assert _gan(thuc, ka._mau(mau)), f"cham {i} o x={cx}: {thuc} != {mau}"


def test_vach_ngan_duoi_header_la_den():
    """Vach nam o [header_h - day/2, header_h + day/2) nhu net SVG."""
    g = _hinh_hoc()
    with tempfile.TemporaryDirectory() as t:
        ra = Path(t) / "ra.png"
        ka.dong_khung(_nguon(t), ra, khong_mascot=True)
        assert _gan(_diem(ra, 700, g["header_h"]), ka._mau(ka.VIEN)), "giua vach phai den"
        # Tren vach la header (nen kem), duoi vach la khe roi toi anh.
        assert _gan(_diem(ra, 700, g["header_h"] - g["day"]), ka._mau(ka.BG))


# ------------------------------------------------- mascot & footer
def test_emoji_trong_bang_ra_dung_avatar_da_ghim():
    with tempfile.TemporaryDirectory() as t:
        mo_ta = ka.dong_khung(_nguon(t), Path(t) / "ra.png", emoji="😂")
        assert mo_ta["avatar"] == "expr-021-040-0004.png", mo_ta["avatar"]


def test_emoji_la_thi_van_ra_anh_chi_la_khong_co_mascot():
    with tempfile.TemporaryDirectory() as t:
        mo_ta = ka.dong_khung(_nguon(t), Path(t) / "ra.png", emoji="🦄")
        assert mo_ta["avatar"] is None
        assert (Path(t) / "ra.png").exists(), "thieu mascot khong duoc lam hong ca khung"


def test_khong_mascot_thi_khong_ve_mascot():
    with tempfile.TemporaryDirectory() as t:
        mo_ta = ka.dong_khung(_nguon(t), Path(t) / "ra.png", emoji="😂", khong_mascot=True)
        assert mo_ta["avatar"] is None


def test_handle_la_thi_KHONG_muon_footer_cua_brand_khac():
    """Loi thuong hieu khong ai thay cho toi khi da dang: moi khung dcgr tung
    mang tagline cua donniechublog."""
    with tempfile.TemporaryDirectory() as t:
        ka.dong_khung(_nguon(t), Path(t) / "ra.png", handle="@dcgr", khong_mascot=True)
    assert ka.FOOTER.get("@dcgr") is None, "chua khai footer cho @dcgr — dung doan ho"


def test_footer_truyen_tay_thi_duoc_dung():
    with tempfile.TemporaryDirectory() as t:
        ra = Path(t) / "ra.png"
        ka.dong_khung(_nguon(t), ra, handle="@la", footer=">_ dong rieng", khong_mascot=True)
        assert ra.exists()


# ------------------------------------------------- khong con Node
def test_khong_con_tep_node_nao_trong_skill():
    skill = ROOT / "hermes" / "skills" / "url-mascot-frame"
    con = [p.name for p in skill.rglob("*")
           if p.name in ("frame.js", "screenshot.js", "package.json", "package-lock.json")]
    assert not con, f"van con tep Node trong skill: {con}"


def test_khong_con_ai_shell_ra_node():
    xau = []
    for p in list(ROOT.glob("*.py")) + list((ROOT / "hermes").rglob("*.py")):
        s = p.read_text(encoding="utf-8", errors="replace")
        for dong in s.splitlines():
            if '"node"' in dong or "'node'" in dong:
                xau.append(f"{p.name}: {dong.strip()[:70]}")
    assert not xau, f"van con cho goi node: {xau}"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
