#!/usr/bin/env python3
"""LOW-445 + LOW-446: ham mo anh cua designer phai xoay theo EXIF va khong bien vung
trong suot thanh DEN.

LOW-445 (audit 30/09/2026): `Image.open(p).convert("RGB")` khong ap EXIF orientation.
JPEG 300x200 dieu 6 -> PIL (300, 200) nhung cv2.imread (5.0) ra w=200,h=300: anh luu PNG
NAM NGANG, hop mat (cv2) va khung cat (PIL) lech truc.

LOW-446: RGBA/P trong suot -> convert("RGB") ra nen DEN: carousel._open goc (0,0,0),
logo_card.flat_background tra den -> slide "nen phang" DEN, logo toi bien mat.

Chay:  venv/bin/python tests/test_low445_446_exif_alpha_open.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from PIL import Image, ImageDraw                               # noqa: E402

import card                                                   # noqa: E402
import carousel                                               # noqa: E402
import image_frame                                            # noqa: E402
import image_rules_common                                     # noqa: E402
import logo_card                                              # noqa: E402
import subject_fit                                            # noqa: E402
from prepare import download_filter                           # noqa: E402
from tam import so_tam                                        # noqa: E402
from test_spec_dre import _ve                                 # noqa: E402

ORIENTATION = 0x0112


def _rotated_jpeg(path, w=300, h=200, fmt="JPEG"):
    """Anh THO w x h (khoi do o nua TRAI) gan EXIF orientation 6 — nhu anh dien thoai
    chup doc: hien thi dung phai xoay 90 do theo chieu kim dong ho thanh h x w."""
    im = _ve(w, h)
    ImageDraw.Draw(im).rectangle((0, 0, w // 4, h - 1), fill=(220, 20, 20))
    ex = Image.Exif()
    ex[ORIENTATION] = 6
    im.save(path, fmt, exif=ex.tobytes(), **({"quality": 95} if fmt == "JPEG" else {}))
    return path


def _logo_rgba(w=900, h=600, fill=(15, 15, 20)):
    """Logo tren nen TRONG SUOT (alpha 0, RGB ngam = 0,0,0 nhu phan lon PNG logo)."""
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse((w // 5, h // 4, w // 2, 3 * h // 4), fill=fill + (255,))
    d.rectangle((w // 2 + 20, h // 3, 4 * w // 5, 2 * h // 3), fill=fill + (255,))
    for k in range(40):                                      # vien mem (alpha trung gian)
        d.line((w // 5 + k * 5, h // 4 - 8, w // 5 + k * 5 + 3, h // 4 - 8), fill=fill + (6 * k,))
    return im


def _textured_logo():
    """Logo co hoa van (du mau de khong bi cong anh RONG chan) tren nen trong suot."""
    im = _logo_rgba()
    im.paste(_ve(200, 120).convert("RGBA"), (im.width // 2 + 20, im.height // 3 + 10))
    return im


# ------------------------------------------------------------------ LOW-445: EXIF
def test_open_helpers_apply_exif_orientation():
    with tempfile.TemporaryDirectory() as t:
        p = _rotated_jpeg(Path(t) / "doc.jpg")
        for ten, ham in (("carousel._open", carousel._open), ("card._open_image", card._open_image),
                         ("card.stack_read", lambda q: card.stack_read([q]))):
            im = ham(str(p))
            assert im.size == (200, 300), (ten, im.size)
            # orientation 6: canh TRAI cua anh tho thanh canh TREN
            assert im.getpixel((100, 10))[0] > 180 and im.getpixel((100, 290))[0] < 150, \
                (ten, im.getpixel((100, 10)), im.getpixel((100, 290)))


def test_cv2_face_axes_match_pil_open():
    """Hop mat (cv2.imread trong face_boxes_with) phai cung he truc voi anh PIL renderer
    dung de cat — ca JPEG, PNG va WebP co tag orientation."""
    class Det:
        def setInputSize(self, wh):
            self.wh = wh

        def detect(self, im):
            return 1, None
    import threading
    with tempfile.TemporaryDirectory() as t:
        for fmt, ext in (("JPEG", "jpg"), ("PNG", "png"), ("WEBP", "webp")):
            p = _rotated_jpeg(Path(t) / f"doc.{ext}", fmt=fmt)
            det = Det()
            assert subject_fit.face_boxes_with(det, threading.Lock(), p, 1600) == []
            assert det.wh == carousel._open(p).size == card._open_image(str(p)).size, \
                (fmt, det.wh, carousel._open(p).size)


def test_download_filter_saves_upright_png():
    """Goc cua loi: anh tai ve luu PNG (khong con tag) — phai xoay TRUOC khi luu."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        p = _rotated_jpeg(Path(t) / "doc.jpg", w=900, h=600)
        wd = Path(t) / "vong"
        wd.mkdir()
        anh = download_filter.download_and_filter(
            [{"image_url": str(p), "file_path": str(p), "alt": "", "page_url": "https://vi.du/b",
              "source": "other_outlet", "score": 10}], wd)
        assert len(anh) == 1, anh
        with Image.open(anh[0]["original_path"]) as im:
            assert im.size == (600, 900), im.size
            assert im.getexif().get(ORIENTATION) in (None, 1)


# ------------------------------------------------------------------ LOW-446: alpha
def test_transparent_area_not_black():
    """Audit: RGBA 300x300 alpha 0 + o do -> carousel._open goc (0,0,0)."""
    im = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    ImageDraw.Draw(im).rectangle((100, 100, 200, 200), fill=(200, 0, 0, 255))
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "trong.png"
        im.save(p)
        for ten, ham in (("carousel._open", carousel._open), ("card._open_image", card._open_image)):
            ra = ham(str(p))
            assert ra.mode == "RGB" and ra.getpixel((0, 0)) == (255, 255, 255), (ten, ra.getpixel((0, 0)))
            assert ra.getpixel((150, 150)) == (200, 0, 0), (ten, ra.getpixel((150, 150)))


def test_dark_logo_on_transparent_stays_visible():
    lg = _logo_rgba()
    assert logo_card.flat_background(lg) == (255, 255, 255), logo_card.flat_background(lg)
    assert logo_card.background_color(lg) == (255, 255, 255)
    assert logo_card.content_box(lg, (255, 255, 255))[2] < lg.width      # tim duoc hop logo
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "logo.png"
        lg.save(p)
        khung, bg = logo_card.build_card(p, None, 1080, 1350)
        assert bg == (255, 255, 255), bg
        import numpy as np
        toi = int((np.asarray(khung.resize((108, 135))).max(axis=2) < 60).sum())
        assert toi > 100, toi                                  # logo toi van hien tren nen trang
        # Luong carousel: _open roi flat_background — nen phang TRANG, chu toi
        nen = logo_card.flat_background(carousel._open(p))
        assert nen == (255, 255, 255) and logo_card.text_color(nen) == (17, 17, 20), nen


def test_light_logo_keeps_dark_background():
    """Logo TRANG (danh cho trang nen toi): convert("RGB") cu ra nen den va logo van hien —
    giu nguyen, khong dan len nen trang lam logo bien mat."""
    lg = _logo_rgba(fill=(250, 250, 250))
    ra = image_rules_common.to_rgb(lg)
    assert ra.getpixel((0, 0)) == (0, 0, 0), ra.getpixel((0, 0))
    assert ra.getpixel((lg.width * 7 // 20, lg.height // 2)) == (250, 250, 250)


def test_multicolor_logo_gets_light_background():
    """Logo nhieu mau (vang + xanh den, kieu Hugging Face): nen SANG nhu the logo image_brand."""
    lg = _logo_rgba(fill=(255, 210, 30))
    ImageDraw.Draw(lg).rectangle((600, 250, 700, 350), fill=(20, 30, 70, 255))
    assert image_rules_common.contrast_background(lg) == (255, 255, 255)


def test_opaque_images_byte_identical():
    """Anh khong co diem trong suot nao: dung byte nhu convert("RGB") cu."""
    rgb = _ve(400, 300)
    rgba = rgb.convert("RGBA")
    for im in (rgb, rgba, rgb.convert("P")):
        assert image_rules_common.to_rgb(im).tobytes() == im.convert("RGB").tobytes(), im.mode


def test_download_filter_transparent_logo_not_black():
    lg = _textured_logo()
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        p = Path(t) / "logo.png"
        lg.save(p)
        wd = Path(t) / "vong"
        wd.mkdir()
        anh = download_filter.download_and_filter(
            [{"image_url": str(p), "file_path": str(p), "alt": "", "page_url": "https://vi.du/b",
              "source": "other_outlet", "score": 10, "graphic_allowed": True}], wd)
        assert len(anh) == 1, anh
        with Image.open(anh[0]["original_path"]) as im:
            assert im.convert("RGB").getpixel((0, 0)) == (255, 255, 255), im.convert("RGB").getpixel((0, 0))


def _about_rgb_old(im, bg):
    """Than `image_frame._about_rgb` truoc LOW-446 (chep nguyen de so byte)."""
    if im.mode.startswith("I"):
        im = im.point(lambda v: v / 256).convert("L")
    elif im.mode == "P" and "transparency" in im.info:
        im = im.convert("RGBA")
    if im.mode in ("RGBA", "LA"):
        nen = Image.new("RGB", im.size, bg)
        nen.paste(im.convert("RGBA"), mask=im.getchannel("A"))
        return nen
    return im.convert("RGB")


def test_image_frame_about_rgb_unchanged():
    """image_frame dung chung than moi voi nen BG cua no — dung byte nhu truoc."""
    bg = image_frame._color(image_frame.BG)
    lg = _logo_rgba()
    p_tr = lg.convert("P")
    p_tr.info["transparency"] = 0
    i16 = Image.new("I;16", (50, 40), 40000)
    for im in (lg, lg.convert("LA"), p_tr, i16, _ve(200, 150)):
        assert image_frame._about_rgb(im).tobytes() == _about_rgb_old(im, bg).tobytes(), im.mode


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
