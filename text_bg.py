#!/usr/bin/env python3
"""text_bg.py — DO va TINH cho quyet dinh mau chu/lop phu khi chu de len anh,
dung CHUNG cho moi vai lam anh (card.py/Ethan, carousel.py/Dre, render_edu.py/
Ethan+Dre+Kite).

Tach ra 08/09/2026: sau khi ca 3 file tu cai lai CUNG MOT phep do (sang trung
binh + do lech mau xam cua dung vung pixel WYSIWYG nam duoi chu), card.py rieng
con giu mot nguong tuong phan HARDCODE (116) chi tinh dung cho MOT thuong hieu
(donniechublog, FG=(230,237,243)/BG=(14,17,23)) roi dung lai y het cho dcgr —
dcgr co FG/BG khac han (trang tuyet doi / den gan tuyet doi) nen nguong dung
phai khac (~119, khong phai 116).

Dong voi tinh than image_rules.py: CONG THUC/PHEP DO dung dung cho moi anh thi
nam MOT cho; con NGUONG/BIEN DO cu the (bao nhieu do lech la CLUTTERED, phu toi da
bao nhieu, co them bien do an toan hay khong) la lua chon RIENG cua tung vai
(khac canvas, khac muc chiu rui ro voi anh that) nen o lai file cua vai do.

Ham o day khong biet canvas, khong biet frame, khong biet vai nao goi — chi
nhan anh/mau va tinh.
"""
from PIL import ImageStat


def measure_bright_offset(vung):
    """Do sang trung binh + do lech mau (stddev) cua MOT vung anh (PIL Image,
    da crop dung vung pixel se nam duoi chu — canvas that sau khi dan anh, hoac
    ban ImageOps.fit mo phong dung cover-crop se ve). -> (sang 0..255, lech
    0..255). Vung phai la anh THAT SU se hien, khong doan qua toa do nguon —
    day la ky luat WYSIWYG dung chung cho ca 3 renderer."""
    st = ImageStat.Stat(vung.convert("L"))
    return st.mean[0], st.stddev[0]


def color_average(vung):
    """Mau RGB trung binh cua MOT vung anh (PIL Image) — dung khi can biet
    dung MAU (khong chi do sang xam) de tinh ti le tuong phan voi mot mau cu
    the da co san (vd mau chu OCR do duoc tu anh goc, xem `ratio_wall_part`).
    -> (r, g, b) 0..255."""
    st = ImageStat.Stat(vung.convert("RGB"))
    return tuple(round(c) for c in st.mean[:3])


def _luminance(rgb):
    """Do sang tuong doi WCAG (tuyen tinh hoa gamma), 0..1."""
    def kenh(c):
        c = c / 255
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    r, g, b = rgb
    return 0.2126 * kenh(r) + 0.7152 * kenh(g) + 0.0722 * kenh(b)


def _ratio_wall_part(l1, l2):
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def threshold_wall_part(mau_sang, mau_toi):
    """Diem sang nen (0..255, xam) noi ti le tuong phan cua `mau_sang` (vd chu
    trang) BANG ti le tuong phan cua `mau_toi` (vd chu toi) — duoi diem nay chu
    toi doc ro hon, tren diem nay chu sang doc ro hon. Tinh theo cong thuc WCAG
    (contrast ratio) bang do nhi phan, khong go tay: doi thuong hieu (FG/BG
    khac) la nguong tu doi theo dung cap mau do, khong con mot con so co dinh
    dung chung cho moi bang mau."""
    l_sang, l_toi = _luminance(mau_sang), _luminance(mau_toi)
    lo, hi = 0.0, 255.0
    for _ in range(40):
        mid = (lo + hi) / 2
        l_nen = _luminance((mid, mid, mid))
        if _ratio_wall_part(l_sang, l_nen) > _ratio_wall_part(l_toi, l_nen):
            lo = mid
        else:
            hi = mid
    return (lo + hi) / 2


def ratio_wall_part(mau1, mau2):
    """Ti le tuong phan WCAG giua HAI MAU RGB THAT (0..255 moi kenh) — khac
    `threshold_wall_part` (tim DIEM SANG NEN noi hai lua chon mau hoa nhau): ham
    nay dung khi da co san ca hai mau cu the (vd mau chu do tu anh goc qua OCR
    + mau nen do duoc sau khi da xoa/ve lai) va can biet chung co du tuong
    phan voi nhau khong. 1.0 = khong the phan biet, 21.0 = den tren trang."""
    return _ratio_wall_part(_luminance(mau1), _luminance(mau2))
