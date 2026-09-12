#!/usr/bin/env python3
"""render_edu.py khong con XAC cua co che lop mo (veil) — va carousel.py CON NGUYEN.

Commit aac796a ("anh chup vao dong thay vi lop mo che chu") bo het co che
veil/gradient-mask trong render_edu.py nhung de lai xac cua no:

  - ba hang so khong ai doc: NGUONG_ROI_CAN_LOP, TOI_TOI_DA_MO, VEIL_SPAN
  - ba luat CSS khong con ai gan class: .fig-molop, .fig-molop img, .fig-man
  - mot `page.evaluate("window.__datMan && window.__datMan()")` VINH VIEN no-op
    vi khong con cho nao sinh ra `window.__datMan` nua
  - mot slot `js` giua tuple tra ve cua `anh_lam_nen` luon la chuoi rong, hai
    noi goi (`_cover_anh`, `s_figure`) van noi `+ js` vao HTML

Vi sao phai la TEST chu khong chi xoa mot lan: xac nay doc ra nhu dang chay —
hang so co chu thich dai giai thich tai sao 0.93, CSS co ten class that — nen
lan sau ai do sua "lop mo" cho slide edu se sua o day va tuong la xong, trong
khi khong mot dong nao trong so do di vao HTML.

NUA THU HAI, quan trong khong kem: carousel.py co BAN SAO RIENG cua
NGUONG_ROI_CAN_LOP (dong 119) va VEIL_SPAN (dong 121), va VAN DUNG THAT o
carousel.py:324 va :329 — co che lop mo con SONG ben do. Test chot ca hai
chieu: don dep ben render_edu.py thi xanh, keo luon carousel.py theo thi DO.

Chay:  venv/bin/python tests/test_render_edu_xac_lop_mo.py
"""
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import render_edu as re_                                      # noqa: E402

TH = dict(bg="#171A21", panel="#212530", line="#333846",
          a="#2FD4E1", b="#8E86F0", stand="#BFC5CF")

# Ten hang so chi phuc vu co che veil: khong con ai doc sau aac796a.
HANG_SO_VEIL = ("NGUONG_ROI_CAN_LOP", "TOI_TOI_DA_MO", "VEIL_SPAN")


def _anh_chup_roi(w=600, h=760):
    """PNG gia lam ANH CHUP THAT: vien tren deu mot mau (-> phan loai 'mo',
    khong 'phang'), 40% duoi la nhieu do lech cao — dung nhanh tung can lop mo.
    Nho hon fixture cua test_render_edu.py vi o day chi can DUNG NHANH, khong
    can do lai nguong."""
    from PIL import Image
    random.seed(0)
    im = Image.new("RGB", (w, h), (40, 60, 90))
    px = im.load()
    for y in range(int(h * 0.6), h):
        for x in range(0, w, 3):
            c = random.randint(0, 255)
            px[x, y] = (c, c, c)
    d = tempfile.mkdtemp()
    p = Path(d) / "roi.png"
    im.save(p, "PNG")
    return p


def test_khong_con_hang_so_chi_danh_cho_lop_mo():
    """Xoa han khoi module, khong phai de lai = None hay 0: con ten thi lan sau
    con nguoi tuong co cho de chinh."""
    con = [t for t in HANG_SO_VEIL if hasattr(re_, t)]
    assert not con, (
        f"render_edu con hang so cua co che lop mo da bo: {con} — "
        f"khong mot cho nao trong render_edu.py doc chung")


def test_css_khong_con_luat_cua_lop_mo():
    """`.fig-molop` / `.fig-man` khong con duoc gan cho element nao: giu lai thi
    bang stylesheet noi co mot co che ma render khong con sinh ra."""
    css = re_.BASE_CSS_TPL
    for luat in (".fig-molop", ".fig-man"):
        assert luat not in css, f"BASE_CSS_TPL con luat chet: {luat}"
    # `.fig-anh` / `.fig-anh-wrap` la co che MOI (anh vao dong) — phai con.
    assert ".fig-anh-wrap" in css, "xoa nham lop anh-trong-dong dang dung"


def test_khong_con_goi_window_datMan():
    """`page.evaluate("window.__datMan && window.__datMan()")` la no-op vinh
    vien: khong con cho nao sinh ra ham do. Doc THAN TEP vi day la mot cau lenh
    trong `_chup_cac_slide`, khong phai thuoc tinh import duoc."""
    src = (ROOT / "render_edu.py").read_text(encoding="utf-8")
    assert "__datMan" not in src, \
        "render_edu.py con goi window.__datMan — khong con ai dinh nghia ham nay"


def test_anh_lam_nen_tra_ve_hai_gia_tri():
    """Hop dong moi: (nen, anh). Slot `js` o giua luon la "" tu aac796a nen hai
    noi goi chi `+ js` mot chuoi rong — bo slot thi co che script dat lop mo
    thanh KHONG THE quay lai, manh hon mot assert `js == ""`."""
    p = _anh_chup_roi()
    ra = re_.anh_lam_nen({"image": str(p)}, TH, "figure")
    assert isinstance(ra, tuple) and len(ra) == 2, (
        f"phai la (nen, anh), duoc "
        f"{f'tuple {len(ra)}' if isinstance(ra, tuple) else type(ra).__name__}")
    nen, anh = ra
    # KHONG in `nen`/`anh` vao thong bao fail: chung chua data URI base64 ca
    # tam anh, mot dong FAIL nhu vay nuot chung log cua chay.sh.
    assert isinstance(nen, str) and isinstance(anh, str), "ca hai phai la str"
    assert "fig-anh-wrap" in anh, "di sai nhanh: nhanh 'mo' phai dat anh vao dong"


def test_carousel_VAN_con_co_che_lop_mo():
    """Cong chan chieu nguoc: co che lop mo con SONG trong carousel.py (ban sao
    rieng cua hai hang so, dung that o :324 va :329). Mot lan don dep sau nay
    grep theo ten hang so rat de keo luon carousel.py theo — test do ngay."""
    import carousel                                           # noqa: PLC0415
    for t in ("NGUONG_ROI_CAN_LOP", "VEIL_SPAN"):
        assert hasattr(carousel, t), (
            f"carousel.{t} bi xoa — co che lop mo ben carousel VAN DUNG THAT, "
            f"chi render_edu bo no")
    src = (ROOT / "carousel.py").read_text(encoding="utf-8")
    # Khong chi "co ten": phai con duoc DOC, khong thi lai thanh xac moi.
    assert "roi - NGUONG_ROI_CAN_LOP" in src, \
        "carousel khong con doc NGUONG_ROI_CAN_LOP — lop mo ben carousel hong"
    assert "top_y + VEIL_SPAN" in src, \
        "carousel khong con doc VEIL_SPAN — lop mo ben carousel hong"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
