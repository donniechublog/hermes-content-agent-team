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


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
