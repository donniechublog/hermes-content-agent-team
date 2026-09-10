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
import render_edu as re_                                      # noqa: E402

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


# --------------------------------------------------------- mau_noi_bat / theme_gan_mau
# Ong Chu 09/09/2026, xem bo GPT-Image-2.5 (anh bang xep hang mau xanh la +
# vang, theme lai chon "rose" hong-tim): "hình thì tông green, yellow mà slide
# thì toàn pink purple ko được liên quan lắm". Do that tren dung anh: mau noi
# bat (76,217,111) xanh la — khop THEME "moss" (a=#7BE495, cung mau) hue_dist
# 0.000, xa nhat voi "rose" (hue_dist 0.447). Theme phai chon theo mau ANH
# THAT (khong doi duoc), khong theo chu de noi dung.
def _anh_mot_mau(rgb, w=600, h=800):
    from PIL import Image
    d = tempfile.mkdtemp()
    p = Path(d) / "mau.png"
    Image.new("RGB", (w, h), rgb).save(p, "PNG")
    return p


def test_mau_noi_bat_doc_dung_mau_chu_dao():
    import render_edu as re_
    p = _anh_mot_mau((76, 217, 111))          # xanh la — trung mau bang Arena that
    rgb = re_.mau_noi_bat(p)
    assert rgb is not None
    assert re_.theme_gan_mau(rgb) == "moss", f"mau {rgb} phai khop 'moss', duoc khac"


def test_mau_noi_bat_bo_qua_anh_xam_trang_den():
    """Anh khong co mau ro ret (den trang, xam) -> None, khong ep theme nao."""
    import render_edu as re_
    for rgb in [(255, 255, 255), (10, 10, 10), (140, 140, 140)]:
        p = _anh_mot_mau(rgb)
        assert re_.mau_noi_bat(p) is None, f"{rgb} phai la None (khong co mau ro)"
    assert re_.theme_gan_mau(None) is None


def test_theme_gan_mau_ca_5_theme_dung_huong():
    """Moi theme phai la lua chon GAN NHAT cho dung mot mau dai dien cua no —
    tranh dot bien lat nguoc bang tra cuu ma khong test nao bat duoc."""
    import render_edu as re_
    ca = {"orbit": (47, 212, 225), "ember": (255, 180, 84), "moss": (123, 228, 149),
          "ink": (143, 179, 255), "rose": (255, 126, 182)}
    for ten, rgb in ca.items():
        assert re_.theme_gan_mau(rgb) == ten, f"{rgb} phai khop chinh theme {ten}"


def test_chon_theme_tu_dong_uu_tien_khop_mau_khi_chua_ghi_theme():
    """Spec KHONG ghi theme, bia dung anh mau xanh la ro ret -> tu chon 'moss',
    khong xoay vong nhu truoc (truoc day chon theo lich su gan day, mu mau)."""
    import render_edu as re_
    p = _anh_mot_mau((76, 217, 111))
    theme, hero = re_.chon_theme_tu_dong({"folio": "test"}, bia_anh=True, anh_mau=str(p))
    assert theme == "moss", theme
    assert hero is None                       # bia_anh=True luon bo hero


def test_chon_theme_tu_dong_canh_bao_khi_theme_da_ghi_lech_mau():
    """Spec DA ghi theme (vd Kite chon 'rose' theo chu de) nhung anh bia mau
    xanh la ro ret -> CANH BAO ra stderr, KHONG tu doi (Kite/nguoi van co the
    co ly do khac), nhung phai thay duoc de sua."""
    import io
    import contextlib
    import render_edu as re_
    p = _anh_mot_mau((76, 217, 111))
    buf = io.StringIO()
    with contextlib.redirect_stderr(buf):
        theme, _hero = re_.chon_theme_tu_dong(
            {"folio": "test", "theme": "rose"}, bia_anh=True, anh_mau=str(p))
    assert theme == "rose", "theme da ghi trong spec khong bi tu doi"
    assert "LECH MAU" in buf.getvalue(), f"khong canh bao lech mau: {buf.getvalue()!r}"


def _anh_mau(t, ten, ve):
    """Anh 100x100, `ve(x, y) -> (r, g, b)`."""
    from PIL import Image
    im = Image.new("RGB", (100, 100))
    px = im.load()
    for y in range(100):
        for x in range(100):
            px[x, y] = ve(x, y)
    p = t / f"{ten}.png"
    im.save(p)
    return str(p)


def test_mau_bao_hoa_thuan_khong_bi_loai():
    """R-r2-1: `v > 0.97` tung loai MOI mau bao hoa thuan — do (255,0,0), vang, va
    chinh accent #FFB454 cua theme ember — nen anh chart mau tuoi tra None."""
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        assert re_.mau_noi_bat(_anh_mau(t, "do", lambda x, y: (255, 0, 0))) is not None
        assert re_.mau_noi_bat(_anh_mau(t, "ember", lambda x, y: (255, 180, 84))) is not None
        assert re_.mau_noi_bat(_anh_mau(t, "trang", lambda x, y: (250, 250, 250))) is None, "trang van phai bi loai"


def test_hue_do_hai_ben_diem_0_gop_thanh_mot():
    """R-r2-2: hue 0.01 va 0.99 la CUNG mau do; round(h*24) cho 0 va 24 — khong
    gop thi anh 60% do / 40% xanh chon theme XANH."""
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        p = _anh_mau(t, "do60", lambda x, y: (230, 30, 40) if x < 30 else ((230, 30, 20) if x < 60 else (40, 60, 230)))
        rgb = re_.mau_noi_bat(p)
        assert rgb is not None and rgb[0] > rgb[2], f"mau noi bat phai la DO, ra {rgb}"


def test_canh_bao_lech_mau_chi_khi_qua_nguong():
    """R-r2-3: NGUONG_HUE_LECH_MAU tung khai bao ma khong dung."""
    gan = re_.theme_gan_mau((0, 200, 180))
    assert re_.lech_hue((0, 200, 180), gan) <= re_.NGUONG_HUE_LECH_MAU
    xa = max(re_.THEMES, key=lambda ten: re_.lech_hue((0, 200, 180), ten))
    assert re_.lech_hue((0, 200, 180), xa) > re_.NGUONG_HUE_LECH_MAU, "phai co theme lech qua nguong de test co nghia"


def test_logo_hang_tren_nen_sang_van_ra_dung_mau():
    """LOW-11: bia la LOGO HANG — mot mark mau nam tren nen trang. Nen trang da
    bi bo loc `s < 0.35` gat het, nhung do ap dao lai dem chia cho TONG pixel,
    nen logo nao duoi 5% dien tich cung ket luan "anh khong co mau ro net" va
    tra None. Theme roi ve vong xoay mu mau: tin DeepSeek (xanh duong #4D6CF7)
    ra slide theme 'moss' xanh la. Mau nao 100% pixel co mau deu la no thi phai
    tin, du dien tich nho."""
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        ds = (77, 108, 247)                   # card.MAU_HANG["DEEPSEEK"] = #4D6CF7
        p = _anh_mau(t, "logo_ds",            # logo ~4% dien tich, con lai trang
                     lambda x, y: ds if y >= 96 else (255, 255, 255))
        rgb = re_.mau_noi_bat(p)
        assert rgb is not None, "logo mau ro tren nen trang khong phai 'anh khong co mau'"
        assert re_.theme_gan_mau(rgb) == "ink", (
            f"xanh DeepSeek phai khop theme 'ink', mau noi bat doc duoc {rgb} "
            f"-> {re_.theme_gan_mau(rgb)}")


def test_dam_nhieu_ti_hon_khong_tu_quyet_theme():
    """Mat kia cua LOW-11: da chia cho so pixel DA LOC thi mot anh gan nhu
    den-trang chi dinh vai pixel mau cung ra 100% ap dao. `TI_LE_ANH_CO_MAU`
    la cai chan cho do — anh phai co mau THAT moi duoc quyet theme."""
    with tempfile.TemporaryDirectory() as t:
        t = Path(t)
        p = _anh_mau(t, "nhieu",              # 0,25% dien tich la mau
                     lambda x, y: (255, 0, 0) if (x < 5 and y < 5) else (250, 250, 250))
        assert re_.mau_noi_bat(p) is None, "dam nhieu 0,25% khong duoc quyet theme ca bo"


def test_theme_bam_mau_hang_khi_anh_khong_co_mau():
    """LOW-11, Ong Chu chot 10/09/2026: palette cua slide phai di cung mau
    brand. Bia ve vector (khong co anh mau) thi theme bam MAU NHAN DIEN CUA
    HANG chu khong xoay vong mu mau — tin DeepSeek (xanh duong #4D6CF7) ra
    'ink', khong duoc ra 'moss' xanh la nua."""
    theme, _hero = re_.chon_theme_tu_dong({"folio": "DEEPSEEK V4"}, bia_anh=False)
    assert theme == "ink", f"tin DeepSeek phai ra theme 'ink', ra {theme}"


def test_mau_anh_that_van_thang_mau_hang():
    """Thu tu uu tien phai giu nguyen: anh that mau CO SAN (luat 09/09/2026)
    van thang mau hang. Tin DeepSeek (xanh duong) ma bia la anh xanh la ro ret
    thi theme chay theo ANH, ra 'moss'."""
    p = _anh_mot_mau((76, 217, 111))
    theme, _hero = re_.chon_theme_tu_dong(
        {"folio": "DEEPSEEK V4"}, bia_anh=True, anh_mau=str(p))
    assert theme == "moss", f"mau anh that phai thang mau hang, ra {theme}"


def test_mau_hang_trong_spec_chiu_duoc_spec_khong_co_slides():
    """`kite_chuan_bi.py` goi `chon_theme_tu_dong({"folio": title})` — spec
    KHONG co khoa "slides". Duong that dang chay, khong duoc nem."""
    assert re_.mau_hang_trong_spec({"folio": "DEEPSEEK V4"}) == (77, 108, 247)
    assert re_.mau_hang_trong_spec({}) is None
    assert re_.mau_hang_trong_spec({"folio": "MOT CHU DE KHONG NHAC HANG NAO"}) is None


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
