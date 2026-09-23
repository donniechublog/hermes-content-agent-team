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

Chay:  venv/bin/python tests/test_image_frame.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from PIL import Image                                         # noqa: E402
import image_frame as ka                                        # noqa: E402


def _source(tmp, w=1400, h=900):
    p = Path(tmp) / "source.png"
    Image.new("RGB", (w, h), (28, 42, 66)).save(p)
    return p


# ------------------------------------------------- lam tron kieu JS
def test_make_full_half_len_like_math_round():
    """round() cua Python lam tron ve so CHAN — dung no la canvas lech 2px."""
    assert ka._make_full(40.5) == 41, "phai lam tron LEN nhu Math.round cua JS"
    assert ka._make_full(41.5) == 42
    assert round(40.5) == 40, "day la ly do khong dung round() cua Python"
    assert ka._make_full(4.5) == 5 and ka._make_full(4.4) == 4


# ------------------------------------------------- hinh hoc khop ban Node
def test_canvas_match_remaining_count_already_change_dimension_with_copy_node():
    with tempfile.TemporaryDirectory() as t:
        mo_ta = ka.line_frame(_source(t), Path(t) / "ra.png", khong_mascot=True)
        assert mo_ta["canvas"] == {"width": 1507, "height": 1033}, mo_ta["canvas"]
        assert mo_ta["source"] == {"width": 1400, "height": 900}, mo_ta["source"]
        assert Image.open(Path(t) / "ra.png").size == (1507, 1033)


def test_canvas_has_space_by_ratio_image_no_crop_square():
    """Anh doc phai ra canvas doc — frame.js co y giu ti le goc."""
    with tempfile.TemporaryDirectory() as t:
        mo_ta = ka.line_frame(_source(t, 600, 1200), Path(t) / "ra.png", khong_mascot=True)
        c = mo_ta["canvas"]
        assert c["height"] > c["width"], c


def test_image_over_empty_got_try_about_2048():
    with tempfile.TemporaryDirectory() as t:
        mo_ta = ka.line_frame(_source(t, 3000, 1500), Path(t) / "ra.png", khong_mascot=True)
        assert mo_ta["source"]["width"] == ka.MAXW, mo_ta["source"]
        assert mo_ta["source"]["height"] == 1024, "phai giu ti le khi thu"


# ------------------------------------------------- mau va vi tri
# Lop vector ve o 4x roi thu bang LANCZOS, ma LANCZOS co rung (ringing): ngay
# giua mot vung mot mau van lech vai don vi. Nen so mau co dung sai — cai dang
# do o day la VI TRI, khong phai gia tri byte.
def _score(anh, x, y):
    return Image.open(anh).convert("RGB").getpixel((int(x), int(y)))


def _near(thuc, mong, sai=10):
    return all(abs(a - b) <= sai for a, b in zip(thuc, mong))


def _figure_geometry(w=1400, h=900):
    """Dung LAI cong thuc cua frame.js. Test tu tinh cho phai nhin thay, thay vi
    ghim toa do dem duoc tren mot anh — de doi cong thuc la test do ngay."""
    R, ngan = ka._make_full, min(w, h)
    canh, header_h = R(ngan * 0.045), R(ngan * 0.05)
    cham_d = max(6, R(header_h * 0.50))
    return {"canh": canh, "header_h": header_h, "day": max(2, R(ngan * 0.005)),
            "cham_d": cham_d, "cham_khe": R(cham_d * 0.7), "cham_cy": R(header_h / 2)}


def test_border_black_start_date_from_edge_left():
    """SVG ve net giua duong nen vien phu [0, day). Lui nua do day nhu SVG la
    lech 2,5px — do duoc bang chinh diem nay khi con ban Node de so."""
    g = _figure_geometry()
    with tempfile.TemporaryDirectory() as t:
        ra = Path(t) / "ra.png"
        ka.line_frame(_source(t), ra, khong_mascot=True)
        for x in (0, g["day"] // 2):
            assert _near(_score(ra, x, 200), ka._color(ka.BORDER)), f"x={x} phai la vien den"
        # Ngoai be day vien la da vao nen the — vien khong duoc day hon frame.js.
        assert _near(_score(ra, g["day"] + 3, 200), ka._color(ka.BG)), "vien day qua"


def test_background_card_is_color_with_brand():
    with tempfile.TemporaryDirectory() as t:
        ra = Path(t) / "ra.png"
        ka.line_frame(_source(t), ra, khong_mascot=True)
        assert _near(_score(ra, 30, 200), ka._color(ka.BG))


def test_ellipsis_macos_use_color_and_use_wait():
    """Ba cham phai dung mau den giao thong VA dung thu tu do-vang-luc."""
    g = _figure_geometry()
    with tempfile.TemporaryDirectory() as t:
        ra = Path(t) / "ra.png"
        ka.line_frame(_source(t), ra, khong_mascot=True)
        for i, mau in enumerate(ka.DOTS):
            cx = g["canh"] + g["cham_d"] / 2 + i * (g["cham_d"] + g["cham_khe"])
            thuc = _score(ra, cx, g["cham_cy"])
            assert _near(thuc, ka._color(mau)), f"cham {i} o x={cx}: {thuc} != {mau}"


def test_divider_short_below_header_is_black():
    """Vach nam o [header_h - day/2, header_h + day/2) nhu net SVG."""
    g = _figure_geometry()
    with tempfile.TemporaryDirectory() as t:
        ra = Path(t) / "ra.png"
        ka.line_frame(_source(t), ra, khong_mascot=True)
        assert _near(_score(ra, 700, g["header_h"]), ka._color(ka.BORDER)), "giua vach phai den"
        # Tren vach la header (nen kem), duoi vach la khe roi toi anh.
        assert _near(_score(ra, 700, g["header_h"] - g["day"]), ka._color(ka.BG))


# ------------------------------------------------- mascot & footer
def test_emoji_within_board_out_use_avatar_already_pin():
    with tempfile.TemporaryDirectory() as t:
        mo_ta = ka.line_frame(_source(t), Path(t) / "ra.png", emoji="😂")
        assert mo_ta["avatar"] == "expr-021-040-0004.png", mo_ta["avatar"]


def test_emoji_is_then_still_out_image_only_is_no_has_mascot():
    with tempfile.TemporaryDirectory() as t:
        mo_ta = ka.line_frame(_source(t), Path(t) / "ra.png", emoji="🦄")
        assert mo_ta["avatar"] is None
        assert (Path(t) / "ra.png").exists(), "thieu mascot khong duoc lam hong ca khung"


def test_no_mascot_then_no_about_mascot():
    with tempfile.TemporaryDirectory() as t:
        mo_ta = ka.line_frame(_source(t), Path(t) / "ra.png", emoji="😂", khong_mascot=True)
        assert mo_ta["avatar"] is None


def test_handle_is_then_no_late_footer_of_brand_other():
    """Loi thuong hieu khong ai thay cho toi khi da dang: moi khung dcgr tung
    mang tagline cua donniechublog.

    Truoc 23/09/2026 test nay do handle "@dcgr" — KHONG phai handle that cua
    brand do ("@dcgr.tech", xem card.BRAND), nen no chi chung minh mot chuoi
    bat ky khong co trong bang. Gio dung dung y do: mot handle la thi khong lay
    tagline cua ai ca."""
    la = "@khong-co-trong-bang"
    with tempfile.TemporaryDirectory() as t:
        ka.line_frame(_source(t), Path(t) / "ra.png", handle=la, khong_mascot=True)
    assert ka.FOOTER.get(la) is None, "handle la thi dung doan ho"


def test_moi_brand_mot_dong_footer_rieng():
    """Hai brand phai co hai dong KHAC nhau — dan tagline brand kia len anh la
    loi thuong hieu khong ai thay cho toi khi da dang."""
    blog = ka.FOOTER.get("@donniechublog")
    dcgr = ka.FOOTER.get("@dcgr.tech")
    assert blog and dcgr, ka.FOOTER
    assert blog != dcgr, ka.FOOTER


def test_footer_transmit_manual_then_ok_use():
    with tempfile.TemporaryDirectory() as t:
        ra = Path(t) / "ra.png"
        ka.line_frame(_source(t), ra, handle="@la", footer=">_ dong rieng", khong_mascot=True)
        assert ra.exists()


# ------------------------------------------------- khong con Node
def test_no_remaining_file_node_which_within_skill():
    skill = ROOT / "hermes" / "skills" / "url-mascot-frame"
    con = [p.name for p in skill.rglob("*")
           if p.name in ("frame.js", "screenshot.js", "package.json", "package-lock.json")]
    assert not con, f"van con tep Node trong skill: {con}"


def test_no_remaining_ai_shell_out_node():
    """Doc bang ast (E-r2-4): chi bat lenh subprocess.*([... "node" ...]) hoac
    shutil.which("node") — quet chuoi tho tung bao hong oan voi mot comment."""
    import ast
    xau = []
    for p in list(ROOT.glob("*.py")) + list((ROOT / "hermes").rglob("*.py")):
        try:
            cay = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except SyntaxError:
            continue
        for n in ast.walk(cay):
            if not isinstance(n, ast.Call) or not isinstance(n.func, ast.Attribute):
                continue
            goc = n.func.value
            if not (isinstance(goc, ast.Name) and goc.id in ("subprocess", "shutil")):
                continue
            if any(isinstance(c, ast.Constant) and c.value == "node" for a in n.args for c in ast.walk(a)):
                xau.append(f"{p.name}:{n.lineno} {goc.id}.{n.func.attr}(... 'node')")
    assert not xau, f"van con cho goi node: {xau}"


# ------------------------------------------------- anh dau vao la (N-r2-3)
def test_png_transparent_out_background_with_no_right_black():
    """convert("RGB") vut alpha -> vung trong suot ra DEN; sharp cua ban Node
    composite giu alpha nen ra nen the. Logo/meme/sticker la dau vao thuong."""
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "trong.png"
        Image.new("RGBA", (1200, 800), (0, 0, 0, 0)).save(p)
        mo = ka.line_frame(p, Path(t) / "ra.png", khong_mascot=True)
        c = mo["canvas"]
        assert _near(_score(Path(t) / "ra.png", c["width"] // 2, c["height"] // 2), ka._color(ka.BG)), \
            "vung trong suot phai la nen the kem"


def test_png_16bit_no_out_page_static():
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "i16.png"
        im = Image.new("I;16", (1200, 800))
        im.putdata([int(x / 1200 * 65535) for y in range(800) for x in range(1200)])
        im.save(p)
        ka.line_frame(p, Path(t) / "ra.png", khong_mascot=True)
        g = _figure_geometry(1200, 800)
        # giua anh: gradient ~50% -> xam, KHONG phai (255,255,255)
        px = _score(Path(t) / "ra.png", g["canh"] + 600, g["header_h"] + 400)
        assert max(px) < 200, f"anh 16-bit ra trang tinh: {px}"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
