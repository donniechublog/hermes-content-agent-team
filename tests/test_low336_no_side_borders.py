#!/usr/bin/env python3
"""LOW-336 (21/09/2026) — luat khung CHUNG moi vai designer: khong vien hai ben,
khong cat sat vao noi dung.

Ong Chu, the Ethan task #02 (anh chup trang HuggingFace la mot dai hep giua hai
mang den, day sat khung tit): *"Ethan lam anh van bi vien hai ben va cat qua sat
vao text"*, roi *"nguyen tac anh nay la chung cho moi role designer, ko bao gio de
vien 2 ben, cung ko cat sat vao noi dung"*.

Goc: `capture_page.count_background` cat bot hai canh (dut chu o mep) roi DEM DEN
tam chup trang nguon thanh 4:5 — mang den la pixel that, di vao the Ethan va slide
Dre. Do tren 10 ban dem that o may chu: ca 10 co mang dac 1.7–12.5% moi ben.

Chay:  venv/bin/python tests/test_low336_no_side_borders.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

import capture_page  # noqa: E402
import image_provenance  # noqa: E402
import image_rules_common  # noqa: E402
import image_rules_dre  # noqa: E402
import image_rules_ethan  # noqa: E402

TEXT = (20, 20, 20)
PAGE = (250, 250, 250)


def _page(w, h, blocks, margin=0):
    """Trang gia: nen trang, cac KHOI dong chu (thanh ngang den mong, cach deu)
    tai [(y0, y1), ...]; `margin` = le trong hai ben (ti le be ngang)."""
    im = Image.new("RGB", (w, h), PAGE)
    d = ImageDraw.Draw(im)
    x0, x1 = int(w * margin) + 8, w - int(w * margin) - 8
    for y0, y1 in blocks:
        for y in range(y0, y1, 30):
            for x in range(x0, x1, 23):                     # "chu": cac net rieng le
                d.rectangle([x, y, x + 15, y + 16], fill=TEXT)
    return im


def _noise_photo(w, h):
    import random
    rnd = random.Random(7)
    im = Image.new("RGB", (w, h))
    im.putdata([(rnd.randrange(40, 220), rnd.randrange(40, 220), rnd.randrange(40, 220))
                for _ in range(w * h)])
    return im


def _old_padded(photo):
    """Dung dang ban `count_background` cu: anh giua, mang DEN hai ben va duoi."""
    c = Image.new("RGB", (1080, 1350), (0, 0, 0))
    p = photo.resize((800, 800))
    c.paste(p, (140, 60))
    return c


# ---- Phep do vien -----------------------------------------------------------------

def test_side_bars_measured_on_old_padding_not_on_real_photo():
    pad = _old_padded(_noise_photo(300, 300))
    co, mo_ta = image_rules_common.has_side_bars(pad)
    assert co, mo_ta
    assert not image_rules_common.has_side_bars(_noise_photo(540, 675))[0]
    # Anh mot mau la anh RONG (cong rieng), khong bao nham la vien.
    assert not image_rules_common.has_side_bars(Image.new("RGB", (500, 600), (0, 0, 0)))[0]


def test_gate_side_bars_blocks_every_role_but_exempts_logo_card():
    pad = _old_padded(_noise_photo(300, 300))
    for mod in (image_rules_dre, image_rules_ethan):
        loi, _ = mod.check_side_bars("A1", pad)
        assert loi and "VIEN" in loi[0], mod.__name__
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "logo.png"
        pad.save(p, pnginfo=image_provenance.stamp_provenance("logo_card"))
        assert image_rules_dre.check_side_bars("L", Image.open(p)) == ([], [])


# ---- Nguon: tam chup giu ti le tu nhien, chi bo phan TRONG ----------------------

def test_capture_keeps_full_width_and_trims_only_empty_margins():
    """Le trang 10% moi ben la VIEN cua chinh trang nguon -> got; cot co chu
    (ke ca net ngoai cung) khong duoc mat."""
    src = _page(1000, 700, [(40, 300), (380, 640)], margin=0.10)
    with tempfile.TemporaryDirectory() as t:
        vao, ra = Path(t) / "in.png", Path(t) / "out.png"
        src.save(vao)
        w, h = capture_page.frame_source_capture(vao, ra)
        out = Image.open(ra)
        assert image_provenance.is_source_capture(out)
        assert not image_rules_common.has_side_bars(out)[0], image_rules_common.has_side_bars(out)[1]
        assert h == 700, "day sach thi khong duoc cat"
        # Noi dung rong 1000 - 2*108 = 784px: khong mat cot nao, le da got gan het.
        assert 784 <= w <= 1000 * 0.86, w


def test_capture_bottom_cut_through_a_line_steps_back_to_quiet_row():
    """Clip dung giua mot dong chu (day bi cat ngang) -> lui ve khe trong."""
    src = _page(1000, 700, [(40, 300), (380, 700)])        # khoi duoi tran het day
    im = image_rules_common.trim_busy_bottom(src)
    assert im.height < 700
    e = image_rules_common.row_energy(im)
    assert max(e[-3:]) <= image_rules_common.QUIET_ROW_ENERGY, "day moi phai la hang trong"


def test_quiet_cut_prefers_gap_between_blocks_over_gap_between_lines():
    """Tit hai dong ngay tren moc: cat giua hai dong cua tit la sai (con mot dong
    lung lung) — phai cat o khoang trong GIUA HAI KHOI, truoc ca cum tit."""
    im = _page(1000, 1000, [(40, 500), (620, 680)])       # khoi than, roi tit 2 dong
    y = image_rules_common.quiet_cut_row(im, 400, 670)
    assert 510 <= y <= 620, y


# ---- Renderer: full be ngang, lop sac dung TREN vung chu --------------------------

def _capture_file(tmp, im):
    p = Path(tmp) / "cap.png"
    im.save(p, pnginfo=image_provenance.stamp_provenance("source_capture"))
    return p


def _col_energy_band(img, y0, y1):
    e = image_rules_common.row_energy(img.crop((0, y0, img.width, y1)))
    return max(e) if e else 0


def test_card_capture_fills_card_no_bars_text_is_overlay():
    """Style the Ethan Ong Chu chot 21/09: anh LAP KIN the, khung quote la lop overlay
    DE LEN anh (khong tach chu khoi hinh) — chi bo vien hai ben. Anh chup cao hon the
    thi giu DINH trang (tit nam o tren)."""
    import card
    src = _page(1000, 2000, [(20, 330), (400, 2000)])
    d = ImageDraw.Draw(src)
    d.rectangle([0, 0, 999, 12], fill=(220, 20, 20))         # dau do o DINH trang
    with tempfile.TemporaryDirectory() as t:
        p = _capture_file(t, src)
        out = Path(t) / "card.png"
        card.build(str(p), "Tiêu đề thử nghiệm cho thẻ trần", str(out), ratio="4:5",
                   kieu="full_bleed", kicker="MODEL RELEASE", brand="dcgr", bo_qua_anh=True)
        im = Image.open(out).convert("RGB")
        assert not image_rules_common.has_side_bars(im)[0], image_rules_common.has_side_bars(im)[1]
        r, g, _ = im.getpixel((600, 4))
        assert r > 180 and g < 80, "anh chup cao phai giu DINH trang, khong cat giua"
        # Anh sac chay toi SAT vung chu (vung chu chi lam mo cuc bo tu frame_top - 110,
        # `_open_region_text`) — khong dung som o mot moc tren chu nhu ban dung-tren-chu.
        H = im.height
        split = H - int(H * card.CEILING_TEXTBOX)
        assert _col_energy_band(im, split - 190, split - 130) > 20, "anh bi tach khoi vung chu"


def test_carousel_cover_capture_not_cover_cropped_and_no_bars():
    import carousel
    src = _page(1400, 700, [(40, 320), (400, 660)])        # anh chup NGANG
    d = ImageDraw.Draw(src)
    d.rectangle([4, 100, 30, 600], fill=(220, 20, 20))       # dau do sat MEP TRAI trang
    with tempfile.TemporaryDirectory() as t:
        p = _capture_file(t, src)
        out = Path(t) / "cover.png"
        carousel.build_cover(str(p), "Hook thu nghiem", "LABEL", str(out), handle="@x")
        im = Image.open(out).convert("RGB")
        assert not image_rules_common.has_side_bars(im)[0], image_rules_common.has_side_bars(im)[1]
        # Cover-crop cu cat hai canh -> mat dau do; full be ngang thi dau do o cot
        # 0..25 (anh ngang dat giua vung tren: y0 = (0.6H - 540) / 2 = 135, dau do 212..597).
        do = [im.getpixel((x, 400)) for x in range(0, 30)]
        assert any(r > 180 and g < 80 for r, g, _ in do), "bia cat mat mep trai cua anh chup"


def test_carousel_body_capture_no_bars():
    import carousel
    src = _page(1000, 1000, [(20, 330), (400, 1000)])
    with tempfile.TemporaryDirectory() as t:
        p = _capture_file(t, src)
        out = Path(t) / "body.png"
        carousel.build_body(str(p), "Chu slide than.", "@x", str(out))
        im = Image.open(out).convert("RGB")
        # Anh nen phang (LOW-341) dat 90% be ngang tren CHINH mau nen cua no: le hai ben la
        # mau nen cua trang (lien voi anh), khong phai mang mau la (vien den cu).
        for x in (5, im.width - 6):
            c = im.getpixel((x, im.height // 3))
            assert all(abs(c[k] - PAGE[k]) <= 6 for k in range(3)), f"le x={x} khong phai mau nen anh: {c}"


# ---- Tu khoa to mau rieng tren tit the tran (Ong Chu 21/09: "mark key quan trong") ----

def test_key_role_for_highlight_and_model_codes():
    """Vai "key" (brand_names.line_segments, chi the Ethan): cum `highlight` Ethan khai va ma
    model chu lan so khong kem ten hang. Hang/ho model van thang truoc (LOW-344)."""
    import brand_names

    def vai(text, **k):
        return [(t, r) for w in brand_names.line_segments(text, **k) for t, r, _k in w if r]
    kq = vai("CACTUS COMPUTE RA MẮT NEEDLE3 TỐI ƯU", keys=brand_names.key_words(["Cactus Compute"]),
             codes=True)
    assert kq == [("CACTUS", "key"), ("COMPUTE", "key"), ("NEEDLE3", "key")], kq
    assert ("DEEPSEEK-V4.1-FLASH", "name") in vai("DEEPSEEK-V4.1-FLASH RA MẮT", codes=True)
    assert vai("H100 B200 CHẠY TỐT") == [], "mac dinh (Kite/Dre) khong to ma chip"


def test_ethan_highlight_must_be_in_title():
    import ethan_submit
    loi = []
    ethan_submit._check_text({"title": "Cactus Compute ra mắt Needle3", "highlight": ["Cactus Compute"]},
                             "full_bleed", loi)
    assert loi == [], loi
    ethan_submit._check_text({"title": "Cactus Compute ra mắt Needle3", "highlight": ["Needle 4"]},
                             "full_bleed", loi)
    assert loi and "không có trong title" in loi[0], loi


def test_card_title_key_drawn_in_accent_color():
    """Tu khoa phai ra MAU KHAC tren pixel that cua the, khong chi danh dau trong code."""
    import card
    src = _noise_photo(300, 375)
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "a.png"
        src.save(p)
        outs = {}
        for hl in ((), ("Cactus Compute",)):
            o = Path(t) / f"c{len(hl)}.png"
            card.build(str(p), "Cactus Compute ra mắt mô hình mới", str(o), ratio="4:5",
                       kieu="full_bleed", kicker="MODEL RELEASE", brand="dcgr", bo_qua_anh=True,
                       highlight=hl)
            outs[len(hl)] = Image.open(o).convert("RGB")
        H = outs[0].height
        vung = (0, int(H * 0.6), outs[0].width, H)
        a, b = outs[0].crop(vung).getcolors(1 << 24), outs[1].crop(vung).getcolors(1 << 24)
        # Mau du phong cua dcgr la ho phach (am, bao hoa); `_enough_bright/_dark` chi
        # keo do sang, giu sac do — dem diem "am bao hoa" thay vi so dung mot mau.
        assert card.BRAND["dcgr"]["fallback_company_color"] == (255, 176, 32)

        def gan(cs):
            return sum(n for n, c in cs if c[0] > c[2] + 90 and c[1] > c[2] + 40)
        assert gan(b) > gan(a) + 500, (gan(a), gan(b))


def test_card_text_box_background_is_flat_over_blotchy_image():
    """Ong Chu bac 5 the tran: *"nen cua text bi loang lo la ko duoc phep"*. Anh la cac
    MANG lon sang/toi xen ke (nhu nut toi HuggingFace, la co): trong khung chu phai
    PHANG — do tren le trong cua khung (giua net khung va chu), khong dinh chu."""
    import card
    from PIL import ImageStat
    im = Image.new("RGB", (1200, 1500), (240, 240, 240))
    d = ImageDraw.Draw(im)
    for i, y in enumerate(range(0, 1500, 150)):
        d.rectangle([0, y, 1200, y + 90], fill=(30, 30, 30) if i % 2 else (220, 40, 40))
    d.rectangle([0, 0, 500, 1500], fill=(20, 60, 200))
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "a.png"
        im.save(p)
        o = Path(t) / "c.png"
        card.build(str(p), "Tiêu đề ba dòng để thử nền khung chữ có phẳng hay không nhé", str(o),
                   ratio="4:5", kieu="full_bleed", kicker="MODEL RELEASE", brand="dcgr", bo_qua_anh=True)
        c = Image.open(o).convert("L")
        H, Wc = c.height, c.width
        # Le trong TRAI nam tren mang xanh, le PHAI tren dai xam/do/den: hai mang anh rat
        # khac nhau. Nen khung phang thi hai le gan nhu cung do sang.
        # Khung tu ~0.70H (CEILING_TEXTBOX 30%, LOW-343) — tranh goc bo tron o dinh khung.
        y0, y1 = int(H * 0.76), int(H * 0.90)
        a, b = card.CEILING_FRAME_X + 10, card.CEILING_TEXT_X - 12
        trai = ImageStat.Stat(c.crop((a, y0, b, y1)))
        phai = ImageStat.Stat(c.crop((Wc - b, y0, Wc - a, y1)))
        lech = abs(trai.mean[0] - phai.mean[0])
        assert lech < 30, f"nen trong khung chu loang lo: le trai {trai.mean[0]:.0f} vs phai {phai.mean[0]:.0f}"
        assert phai.stddev[0] < 12, f"nen trong khung chu loang lo: stddev {phai.stddev[0]:.1f}"


def test_plain_photo_fills_card_no_blur_band():
    """Ong Chu 21/09: *"dong nhoe nhoet phia duoi van la diem tru tham my lon"* (la co, toa
    nha, Xiaomi). Anh chup THUONG thap hon the -> phu kin the quanh chu the, khong con dai
    nen mo; chu the rong hon khung cat -> quay ve full be ngang (khong cat vao chu the)."""
    import card
    card.set_brand("donniechublog")
    photo = _noise_photo(600, 400)                        # 3:2 -> nat_h 800/1500
    c1 = Image.new("RGBA", (card.W, 1500))
    card._layer_image(c1, photo, 1500, cover_focus=(0.4, 0.5, 0.3))
    c0 = Image.new("RGBA", (card.W, 1500))
    card._layer_image(c0, photo, 1500)
    band = (0, 1150, card.W, 1450)
    assert _col_energy_band(c1.convert("RGB"), *band[1::2]) > 20, "anh thuong van con dai nen mo"
    assert _col_energy_band(c0.convert("RGB"), *band[1::2]) < 20
    # Chu the rong 90% anh > khung cat (2/3 * 0.8 = 53%) -> khong cat, giu full be ngang.
    assert card._cover_window(photo, card.W, 1500, (0.5, 0.5, 0.9)) is None


def test_cover_only_for_plain_photos():
    import ethan_submit
    photo = {"kind": "photo", "source": "brand", "original_path": "x"}
    assert ethan_submit.cover_focus(photo, False) == (0.5, 0.5, 0.0)
    got = ethan_submit.cover_focus({**photo, "subject_box": [0.2, 0.1, 0.6, 0.9]}, False)
    assert all(abs(a - b) < 1e-9 for a, b in zip(got, (0.4, 0.5, 0.4))), got
    for khong in ({**photo, "source": "capture_source"}, {**photo, "kind": "chart"},
                  {**photo, "ranking": {"kind": "table"}}, {**photo, "subject_kind": "screen"}):
        assert ethan_submit.cover_focus(khong, False) is None, khong
    assert ethan_submit.cover_focus(photo, True) is None, "anh ghep doc giu full be ngang"
    # Toa nha khoanh ca khung (rong 100%) van phu kin duoc: cat canh toa nha khong mat gi.
    toa = ethan_submit.cover_focus({**photo, "subject_kind": "building", "subject_box": [0, 0, 1, 1]}, False)
    assert toa is not None and toa[2] == 0.0, toa


def test_flat_bottom_extends_own_background_no_blur():
    """Ong Chu 21/09: *"mot buc anh tot la ko can phai dung nhung bien phap phuc tap nhu
    blur"* (vi du logo Qwen tren nen tron). Anh thap hon the ma DAY la nen phang -> phan
    thieu la CHINH mau nen do, khong phai ban mo cua anh."""
    import card
    card.set_brand("dcgr")
    src = _page(1200, 700, [(60, 400)])                  # trang trang, day phang
    c = Image.new("RGBA", (card.W, 1500))
    card._layer_image(c, src, 1500)
    duoi = c.convert("RGB").crop((0, 900, card.W, 1500))
    assert duoi.getcolors(4) == [(card.W * 600, PAGE)], "phan thieu khong phai mau nen cua chinh anh"


def test_cover_without_subject_keeps_logo_corner():
    """Khong biet chu the -> khung cat giu vung NHIEU CHI TIET (the Xiaomi 21/09: cat giua
    lam mat chu logo o goc trai)."""
    import card
    im = Image.new("RGB", (1200, 800), (200, 90, 30))
    ImageDraw.Draw(im).rectangle([30, 60, 330, 200], fill=(255, 255, 255))
    for x in range(40, 320, 18):                             # "chu logo" o goc trai
        ImageDraw.Draw(im).rectangle([x, 90, x + 8, 170], fill=(10, 10, 10))
    x0, _, x1, _ = card._cover_window(im, card.W, 1500, (0.5, 0.5, 0.0))
    assert x0 <= 30 and x1 >= 330, (x0, x1)


# ---- Uu tien chon anh: vung khung chu sach, khong mat chi tiet mep ---------------------

def test_text_zone_clean_page_vs_busy_photo():
    """Ong Chu 21/09: *"mot buc anh tot la ko can phai dung nhung bien phap phuc tap nhu
    blur ma text quote van hien thi ro rang"*. Trang nen tron (chu o nua tren) -> vung khung
    chu sach; anh nhieu chi tiet kin khung -> roi."""
    import card
    import ethan_prepare
    card.set_brand("dcgr")
    with tempfile.TemporaryDirectory() as t:
        sach, roi = Path(t) / "sach.png", Path(t) / "roi.png"
        _page(1200, 700, [(40, 400)]).save(sach)
        _noise_photo(400, 500).save(roi)
        z1 = card.text_zone_report(str(sach))
        z2 = card.text_zone_report(str(roi), cover_focus=(0.5, 0.5, 0.0))
    assert z1["busy"] <= ethan_prepare.ZONE_CLEAN, z1
    assert z2["busy"] > ethan_prepare.ZONE_BUSY, z2
    assert ethan_prepare.zone_rank(z1) < ethan_prepare.zone_rank(z2)
    assert any("SẠCH" in g for g in ethan_prepare.zone_notes(z1))
    assert any("RỐI" in g for g in ethan_prepare.zone_notes(z2))


def test_text_zone_lost_edge_detail_when_cover_cuts_logo():
    """Logo chu o SAT hai mep anh vuong: phu kin 4:5 buoc phai cat mot ben -> `lost` cao
    va brief canh bao (the Xiaomi 21/09)."""
    import card
    import ethan_prepare
    im = Image.new("RGB", (1200, 1200), (200, 90, 30))
    d = ImageDraw.Draw(im)
    for x0 in (10, 1000):
        for x in range(x0, x0 + 180, 16):
            d.rectangle([x, 80, x + 8, 300], fill=(255, 255, 255))
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "logo.png"
        im.save(p)
        z = card.text_zone_report(str(p), cover_focus=(0.5, 0.5, 0.0))
    assert z["lost"] > ethan_prepare.EDGE_LOST_MAX, z
    assert any("CẮT MẤT" in g for g in ethan_prepare.zone_notes(z))


if __name__ == "__main__":
    ok = 0
    ten = [n for n in dir() if n.startswith("test_")]
    for n in ten:
        try:
            globals()[n]()
            ok += 1
        except AssertionError as e:
            print(f"FAIL {n}: {e}")
    print(f"{ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
