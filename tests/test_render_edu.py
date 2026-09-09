#!/usr/bin/env python3
"""render_edu.py — anh_lam_nen(): mat cau lenh `return` cuoi ham (09/09/2026).

Commit e883880 ("doi mau chu theo nen truoc, chi phu lop mo/toi khi pixel that
su roi") viet lai `anh_lam_nen` nhung lam ROI cau `return nen, js` cuoi cung —
nhanh "anh chup ma vung duoi chu THAT SU roi" (can_lop=True) build xong `js`
roi RA KHOI HAM khong return, Python tra ve None ngam. Moi noi goi ham nay
(`_cover_anh`, `s_figure`) deu doi unpack `(nen, js)`; gap None thi
`TypeError: cannot unpack non-iterable NoneType object` — sap tat ca cong
chan roi den thang Chromium trong `render()`.

Khong ai bat duoc vi ca hai nhanh con lai ("phang" va "mo" nhung khong roi)
deu co return rieng ngay tai cho, chi nhanh "mo VA roi" (anh chup that co chi
tiet — dung loai anh Kite hay dung nhat: bang xep hang, chart chup man hinh)
la di qua het than ham roi moi return — va truoc 09/09/2026 chua bo nao chay
qua dung nhanh do trong test.

Chay:  venv/bin/python tests/test_render_edu.py
"""
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

TH = dict(bg="#171A21", panel="#212530", line="#333846",
          a="#2FD4E1", b="#8E86F0", stand="#BFC5CF")


def _anh_chup_roi(w=1200, h=1500):
    """Mot PNG gia lam ANH CHUP THAT (bien mau vien khong deu -> 'mo', khong
    'phang') VA co vung duoi 'roi' (do lech mau cao) -> can_lop=True."""
    from PIL import Image
    random.seed(0)
    im = Image.new("RGB", (w, h), (40, 60, 90))
    px = im.load()
    # Vien tren/trai deu mot mau (anh chup nen troi), rieng 40% duoi la nhieu
    # ngau nhien do lech cao — mo phong bang so/chart chi tiet o day.
    for y in range(int(h * 0.6), h):
        for x in range(0, w, 3):
            c = random.randint(0, 255)
            px[x, y] = (c, c, c)
    d = tempfile.mkdtemp()
    p = Path(d) / "roi.png"
    im.save(p, "PNG")
    return p


def test_anh_lam_nen_tra_ve_tuple_khong_phai_none():
    """Nhanh 'mo VA roi' phai return (nen, js), khong duoc roi qua het than
    ham ma khong return (bug that: None, TypeError o moi noi goi)."""
    import render_edu as re_
    p = _anh_chup_roi()
    sl = {"image": str(p)}
    ra = re_.anh_lam_nen(sl, TH, "figure")
    assert ra is not None, "anh_lam_nen tra None — mat return cuoi ham"
    assert isinstance(ra, tuple) and len(ra) == 2, f"phai la (nen, js), duoc {ra!r}"
    nen, js = ra
    assert isinstance(nen, str) and "<div" in nen
    assert isinstance(js, str) and "__datMan" in js, \
        "js rong — chung to khong di qua đúng nhanh can_lop=True can kiem"


def test_s_figure_khong_nem_khi_dung_anh_roi():
    """Goi qua dung builder that (`s_figure`) — cong chan o muc thap hon co
    the che mat loi neu chi test noi bo ham con."""
    import render_edu as re_
    p = _anh_chup_roi()
    sl = {"image": str(p), "eyebrow": "SO LIEU", "title": "Tieu de test",
         "kind": "figure"}
    html = re_.s_figure(sl, TH)
    assert isinstance(html, str) and len(html) > 100


def _anh_bang_xep_hang(w=1188, h=1524):
    """Mo phong DUNG dac diem lam sai lop mo (09/09/2026): nen TRANG chiem gan
    het vung duoi, chi vai dong chu/so MONG xen vao — do that tren anh XH cua
    bo GPT-Image-2.5: roi_duoi=29.2, vua qua NGUONG_ROI_CAN_LOP=26 mot chut,
    dan toi max_toi=0.036 (gan nhu khong toi) truoc khi sua. Anh chup THAT (noise
    day dac ca vung, xem `_anh_chup_roi`) khong tai hien duoc ca nay — do ro
    "roi VUA DU de kich hoat, nhung con qua yeu de che het chu" phai la mot anh
    RIENG, gan sat nguong."""
    from PIL import Image
    random.seed(1)
    im = Image.new("RGB", (w, h), (255, 255, 255))
    px = im.load()
    # Thanh header mau dam, het be ngang, ngay canh TREN — de mau median cua
    # canh tren LECH han ba canh con lai (van trang), phan loai "mo" thay vi
    # "phang" (doc_nen doi ca 4 canh gan cung mot mau). Khong dung o duoi 45%
    # de khong lam sai roi_duoi cua vung dang test.
    for y in range(0, 24):
        for x in range(w):
            px[x, y] = (30, 60, 120)
    # 6 "hang" mong (~3% chieu cao/hang) co chu den — giong 6 dong so trong
    # bang xep hang, phan con lai cua vung duoi la trang tuyet doi.
    for hang in range(6):
        y0 = int(h * 0.55) + hang * int(h * 0.06)
        for y in range(y0, min(h, y0 + max(2, int(h * 0.012)))):
            for x in range(0, w, 2):
                if random.random() < 0.4:
                    px[x, y] = (20, 20, 20)
    d = tempfile.mkdtemp()
    p = Path(d) / "bang.png"
    im.save(p, "PNG")
    return p


def test_anh_gan_nguong_van_duoc_toi_toi_da():
    """Chinh loi Ong Chu bat 09/09/2026: 'chữ blue ở dưới nền vẫn còn màu đen
    mờ... blur thì blur 1 màu luôn đi chứ'. Anh chi VUA QUA nguong roi (nhu
    bang xep hang: nen trang, chu mong) truoc day chi duoc toi ~3.6% — so con
    doc ro muot duoi tieu de. Gio phai toi GAN BANG TOI_TOI_DA_MO, khong con ti
    le theo do roi nua."""
    import re as _re
    import render_edu as re_
    p = _anh_bang_xep_hang()
    sl = {"image": str(p)}
    nen, js = re_.anh_lam_nen(sl, TH, "bia")
    m = _re.search(r"MAX=([\d.]+)", js)
    assert m, f"khong thay MAX= trong js: {js[:200]!r}"
    max_toi = float(m.group(1))
    assert max_toi >= re_.TOI_TOI_DA_MO - 0.01, (
        f"anh gan nguong (roi vua qua {re_.NGUONG_ROI_CAN_LOP}) chi duoc toi "
        f"{max_toi}, con doc duoc chu — dung phai gan {re_.TOI_TOI_DA_MO}")


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
