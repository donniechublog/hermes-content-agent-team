#!/usr/bin/env python3
"""LOW-341 (21/09/2026) — anh NEN PHANG: mau chu tuong phan truoc, nen chu sau.

Ong Chu, hai slide quote MiniMax-H3 (hinh paper nen trang): *"ko nen lam the nay, hinh se bi
tach thanh 3 khoi. luon uu tien dat chu mau tuong phan voi mau nen truoc khi phai dung toi nen
chu. vi du truong hop nay chi can phong lon main image ra de hien thi full 90% width roi dat
quote mau den len nen trang la duoc"*; cung ngay: *"bia cung ap dung"*. Duong cu ra anh sac
55% / dai cover-blur xam 11% / overlay toi 29%, ma cong LOW-286 van cho qua (0.34 / 0.72).

Test pixel o day FAIL tren code cu: moi hang cua slide phai con la giay trang (trung vi),
code cu co dai xam (~199) va overlay toi (~40-80) ngay duoi hinh.

Chay:  venv/bin/python tests/test_low341_flat_background.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw  # noqa: E402

import carousel  # noqa: E402

QUOTE = ("Qua 517 bài kiểm tra, MiniMax-H3 chỉ đạt tỷ lệ thành công chung 41.97% khi suy "
         "luận về thế giới vật lý.")
TEXT = ("SoL-Pi đề xuất khung điều phối cho chu trình tự động nghiên cứu của coding agent. "
        "Hệ thống giữ hiệu quả token khi agent chạy chuỗi tác vụ dài.")


# ------------------------------------------------------------------ do gia
def _figure(w=2000, h=1300, bg=(255, 255, 255), ink=(40, 40, 40), margin=0.14, cut_line=True):
    """Hinh kieu paper: nen phang, noi dung (khung, thanh, chu) o giua, le rong hai ben.
    `cut_line`: mot dong chu than bai bi cat o MEP TREN — dung loi cat cua arxiv_figures
    (SoL-Pi Figure 1: "native Codex and Claude Code harnesses..." dinh o mep)."""
    im = Image.new("RGB", (w, h), bg)
    d = ImageDraw.Draw(im)
    x0, x1 = int(w * margin), int(w * (1 - margin))
    for i in range(3):
        bx = x0 + i * (x1 - x0) // 3
        bx1 = bx + (x1 - x0) // 3 - 10
        # Khung NET DUT (nhu khung "Auto-Research Loop"): khong hang nao cua hinh toi quá
        # nua be ngang — de phep do "moi hang con la nen trang" chi bat nen chu, khong bat hinh.
        for x in range(bx + 10, bx1, 24):
            d.rectangle([x, 180, min(x + 10, bx1), 183], fill=ink)
            d.rectangle([x, 617, min(x + 10, bx1), 620], fill=ink)
        d.rectangle([bx + 10, 180, bx + 13, 620], fill=ink)
        d.rectangle([bx1 - 3, 180, bx1, 620], fill=ink)
        d.rectangle([bx + 40, 260, bx + 200, 300], fill=(120, 190, 60))
        for k in range(6):
            d.text((bx + 40, 340 + k * 40), "Execution trace step", fill=ink)
    for k in range(4):
        d.rectangle([x0, 760 + k * 70, x0 + 200 + k * 180, 800 + k * 70], fill=(70, 80, 90))
    for k in range(5):
        d.text((x0, 1080 + k * 30), "Figure 1: Overview of the evaluation of the model " * 2, fill=ink)
    if cut_line:
        for x in range(x0, x1, 16):                       # chan net chu: ~1/5 be ngang dong
            d.rectangle([x, 0, x + 3, 8], fill=ink)
    return im


def _photo(w=2000, h=1300):
    """Anh chup gia: troi sang tren, dat toi duoi, vat the cham mep — vien KHONG phang."""
    im = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(im)
    for y in range(h):
        t = y / h
        d.line([(0, y), (w, y)], fill=(int(120 + 100 * (1 - t)), int(150 + 60 * (1 - t)), int(90 + 150 * (1 - t))))
    b = 7
    for x in range(0, w, 37):
        for y in range(0, h, 41):
            b = (b * 1103515245 + 12345) % 2147483648
            d.ellipse([x, y, x + 24, y + 24], fill=(b % 255, (b >> 8) % 255, (b >> 16) % 255))
    return im


def _save(im, tmp, name):
    p = Path(tmp) / name
    im.save(p)
    return str(p)


def _row_medians(path):
    import numpy as np
    a = np.asarray(Image.open(path).convert("L"), dtype=np.float32)
    return np.median(a, axis=1)


def _setup():
    carousel.set_brand("donniechublog")
    carousel.set_background("dark")


# ------------------------------------------------------------- nhan dien
def test_flat_background_detects_paper_figure():
    import logo_card
    assert logo_card.flat_background(_figure()) == (255, 255, 255)
    assert logo_card.flat_background(_figure(cut_line=False)) == (255, 255, 255)


def test_flat_background_detects_dark_screenshot():
    import logo_card
    bg = logo_card.flat_background(_figure(bg=(18, 18, 24), ink=(230, 230, 230)))
    assert bg == (18, 18, 24), bg


def test_flat_background_rejects_photo():
    import logo_card
    assert logo_card.flat_background(_photo()) is None
    # Troi phang o canh tren KHONG du: ca bon canh phai phang.
    sky = _photo()
    ImageDraw.Draw(sky).rectangle([0, 0, sky.width, 400], fill=(200, 220, 240))
    assert logo_card.flat_background(sky) is None


def test_content_box_drops_paper_margin():
    import logo_card
    fig = _figure(cut_line=False)
    x0, y0, x1, y1 = logo_card.content_box(fig, (255, 255, 255))
    assert abs(x0 - 280) <= 12 and abs(x1 - 1720) <= 12, (x0, x1)
    assert abs(y0 - 180) <= 12, y0


# ----------------------------------------------------- mot mat phang (pixel)
def _assert_one_plane(path, nhan, allow=0, start=0):
    """MOI hang cua slide: trung vi van la giay trang. Code cu: dai cover-blur (~199) va
    overlay toi (~40-80) ngay duoi hinh -> hang tram hang trung vi toi (do: 362-525).
    `allow`: slide quote co net ngang tren cua khung + chip ten kenh cung hang (~5px).
    `start`: chi xet tu hang nay — hinh cao keo xuong gan vung chu thi phan tren la hinh."""
    med = _row_medians(path)
    toi = [y for y, v in enumerate(med) if v < 245 and y >= start]
    assert len(toi) <= allow, (f"{nhan}: {len(toi)} hang khong con la nen trang "
                               f"(dau tien y={toi[0]}, trung vi {med[toi[0]]:.0f})")


def _assert_dark_text(path, y0, y1, nhan):
    """Chu tren nen trang phai TOI (khong phai chu trang tren giay trang)."""
    import numpy as np
    a = np.asarray(Image.open(path).convert("L"), dtype=np.float32)[y0:y1]
    assert np.percentile(a, 2) < 60, f"{nhan}: vung chu khong co net toi nao"


def test_quote_slide_is_one_plane():
    _setup()
    with tempfile.TemporaryDirectory() as t:
        out = str(Path(t) / "q.png")
        rep = {}
        carousel.build_body_quote(_save(_figure(), t, "f.png"), QUOTE, "via arXiv", "donniechublog",
                                  out, report=rep)
        _assert_one_plane(out, "slide quote", allow=8)
        _assert_dark_text(out, 950, 1250, "slide quote")
        assert rep.get("flat_bg") == [255, 255, 255], rep
        assert rep["bg_opacity"] == 0.0 and rep["flat_off_plane"] == 0.0, rep


def test_body_slide_is_one_plane():
    _setup()
    with tempfile.TemporaryDirectory() as t:
        out = str(Path(t) / "b.png")
        carousel.build_body(_save(_figure(), t, "f.png"), TEXT, "donniechublog", out, report={})
        _assert_one_plane(out, "slide than")
        _assert_dark_text(out, 1030, 1230, "slide than")


def test_cover_is_one_plane():
    """Ong Chu 21/09: "bia cung ap dung"."""
    _setup()
    with tempfile.TemporaryDirectory() as t:
        out = str(Path(t) / "c.png")
        carousel.build_cover(_save(_figure(), t, "f.png"), "Cắt 49% token và 1/3 chi phí API",
                             "SOL-PI", out, "donniechublog", category="RESEARCH", report={})
        _assert_one_plane(out, "bia")
        _assert_dark_text(out, 900, 1200, "bia")


def test_dark_flat_background_gets_light_text():
    _setup()
    with tempfile.TemporaryDirectory() as t:
        out = str(Path(t) / "q.png")
        rep = {}
        carousel.build_body_quote(_save(_figure(bg=(18, 18, 24), ink=(230, 230, 230)), t, "f.png"),
                                  QUOTE, "via arXiv", "donniechublog", out, report=rep)
        assert rep.get("flat_bg") == [18, 18, 24], rep
        import numpy as np
        a = np.asarray(Image.open(out).convert("L"), dtype=np.float32)
        assert np.median(a, axis=1).max() < 40                 # van la mot mat phang toi
        assert np.percentile(a[950:1250], 98) > 200            # chu sang


def test_content_fills_90_percent_width():
    """"phong lon main image ra de hien thi full 90% width": hinh thap -> noi dung rong 90%."""
    import numpy as np
    _setup()
    with tempfile.TemporaryDirectory() as t:
        out = str(Path(t) / "q.png")
        carousel.build_body_quote(_save(_figure(w=2400, h=900, cut_line=False), t, "f.png"), QUOTE, "",
                                  "donniechublog", out)
        a = np.asarray(Image.open(out).convert("L"))[:700]
        cols = np.nonzero((a < 200).sum(axis=0) >= 2)[0]
        rong = cols[-1] - cols[0] + 1
        assert abs(rong - round(carousel.W * 0.90)) <= 8, rong


def test_tall_flat_image_keeps_width_and_is_covered_under_text():
    """Ong Chu 21/09, bia SoL-Pi ghep 2 hinh: *"luon uu tien hien thi full chieu rong, phan noi
    dung anh bi chen vao text, chung ta phu len mot layer cung mau voi mau nen roi dat quote cua
    chung ta len"*. Hinh cao hon phan tren chu: KHONG thu lai — van 90% be ngang, vung chu la giay."""
    import numpy as np
    _setup()
    tall = Image.new("RGB", (1600, 2400), (255, 255, 255))
    tall.paste(_figure(w=1600, h=1300, cut_line=False), (0, 0))
    tall.paste(_figure(w=1600, h=1300, cut_line=False), (0, 1100))
    with tempfile.TemporaryDirectory() as t:
        out = str(Path(t) / "c.png")
        rep = {}
        carousel.build_cover(_save(tall, t, "tall.png"), "Cắt 49% token và 1/3 chi phí API",
                             "SOL-PI", out, "donniechublog", category="RESEARCH", report=rep)
        a = np.asarray(Image.open(out).convert("L"))
        cols = np.nonzero((a[:900] < 255 - 28).sum(axis=0) >= 1)[0]    # tieu chi cua content_box
        # Khong thu lai cho vua phan tren chu (thu thi chi con ~40% be ngang): van ~90%.
        rong = cols[-1] - cols[0] + 1
        assert carousel.W * 0.86 <= rong <= carousel.W * 0.90 + 8, rong
        assert (a[700:900] < 200).sum() > 1000, "hinh phai con keo xuong gan vung chu"
        _assert_one_plane(out, "bia hinh cao", start=980)      # dong hook dau ~y=1000
        _assert_dark_text(out, 950, 1200, "bia hinh cao")
        assert rep.get("flat_off_plane") == 0.0, rep


def test_photo_keeps_old_path():
    """Anh chup (vien khong phang): van di duong cu — anh phu kin + overlay LOW-286."""
    _setup()
    with tempfile.TemporaryDirectory() as t:
        out = str(Path(t) / "q.png")
        rep = {}
        carousel.build_body_quote(_save(_photo(), t, "p.png"), QUOTE, "via arXiv", "donniechublog",
                                  out, report=rep)
        assert "source_flat" not in rep and rep["bg_opacity"] > 0, rep


# ------------------------------------------------------------------ cong
def test_gate_flat():
    ok = {"source_flat": [255, 255, 255], "flat_bg": [255, 255, 255], "flat_off_plane": 0.0}
    assert carousel._gate_flat("slide 2", ok) == ""
    assert carousel._gate_flat("slide 2", {"bg_share": 0.3, "bg_opacity": 0.7}) == ""   # anh chup
    assert "3 khoi" in carousel._gate_flat("slide 2", dict(ok, flat_bg=None))
    assert "LOW-341" in carousel._gate_flat("slide 2", dict(ok, flat_off_plane=0.05))


def test_gate_image_accepts_flat_landscape():
    """Anh nen phang NGANG (1.54) khong bi cong ti le 4:5..1:1 chan — no duoc dan nguyen noi
    dung tren nen cua no. Anh chup ngang van bi chan nhu cu."""
    with tempfile.TemporaryDirectory() as t:
        f = _save(_figure(), t, "f.png")
        p = _save(_photo(), t, "p.png")
        loi, _ = carousel._gate_image([("slide 2", f, {})])
        assert not loi, loi
        loi, _ = carousel._gate_image([("slide 3", p, {})])
        assert any("4:5..1:1" in x for x in loi), loi


# --------------------------------------------------------- dre_submit
def test_dre_uses_original_for_flat_image():
    """Hinh paper ngang: dung anh GOC (khong ban cat 4:5), khong bao "anh NGANG phai ghep",
    va lam BIA duoc ke ca khi la chart."""
    from tam import so_tam
    from test_spec_dre import _anh, _m, _spec, _bia, _du_slide, _chay
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, f"A{i}", 1000, 1250) for i in range(1, 6)]
        for i, kind in ((0, "chart"), (1, "photo")):
            a = anh[i]
            _figure().save(a["original_path"])
            a.update(w=2000, h=1300, ratio=1.54, kind=kind, landscape=True)
        ra, loi, _canh, _dung = _chay(_spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"])), _m(wd, anh), wd)
        assert not [x for x in loi if "A1" in x or "A2" in x or "bìa" in x], loi
        assert ra["cover"]["image"] == anh[0]["original_path"]
        assert ra["slides"][0]["image"] == anh[1]["original_path"]


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
