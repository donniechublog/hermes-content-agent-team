#!/usr/bin/env python3
"""LOW-284 (19/09/2026) — cùng một bức ảnh tải từ hai nguồn lên hai slide.

Album dcgr "Lovable mua Sutro": điện thoại chạy app Lovable ở slide 5 (A59, 9to5mac)
và slide 6 (A26, computerworld); trang chủ Lovable ở slide 2 (A76) và slide 6 (A42).
`check_duplicate` so md5 nên hai tệp từ hai URL lọt.

Chạy:  venv/bin/python tests/test_low284_same_photo.py
"""
import importlib.util
import random
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw  # noqa: E402

import same_photo  # noqa: E402
import submit_common as nc  # noqa: E402

CV2 = importlib.util.find_spec("cv2") is not None


def _photo(seed, w=1400, h=900):
    """Anh 'chup' nhieu chi tiet (hinh khoi, net) — du diem ORB nhu anh that."""
    rnd = random.Random(seed)
    im = Image.new("RGB", (w, h), (rnd.randrange(40, 90),) * 3)
    d = ImageDraw.Draw(im)
    for _ in range(260):
        x, y = rnd.randrange(w), rnd.randrange(h)
        r = rnd.randrange(6, 60)
        col = tuple(rnd.randrange(256) for _ in range(3))
        if rnd.random() < 0.5:
            d.rectangle([x, y, x + r, y + r // 2], fill=col)
        else:
            d.ellipse([x, y, x + r, y + r], outline=col, width=3)
    return im


def _save(im, t, name, **kw):
    p = Path(t) / name
    im.save(p, **kw)
    return str(p)


def test_recropped_recompressed_copy_is_same_photo():
    if not CV2:
        return
    with tempfile.TemporaryDirectory() as t:
        goc = _photo(1)
        a = _save(goc, t, "a26.png")
        # nguon khac: cat 8% mep, thu nho, nen JPEG
        c = goc.crop((110, 70, 1290, 830)).resize((1024, 660))
        b = _save(c, t, "a59.jpg", quality=70)
        n, corr = same_photo.compare(a, b)
        assert n >= same_photo.SAME_PHOTO_INLIERS and corr >= same_photo.SAME_PHOTO_CORR, (n, corr)
        assert same_photo.is_same_photo(a, b)


def test_different_photo_not_same():
    if not CV2:
        return
    with tempfile.TemporaryDirectory() as t:
        a = _save(_photo(1), t, "a.png")
        b = _save(_photo(2), t, "b.png")
        assert not same_photo.is_same_photo(a, b), same_photo.compare(a, b)


def test_shared_logo_on_different_background_not_same():
    """Hai do hoa khac nhau CHUNG mot logo (Apple M3 Ultra / M5 Ultra) — khop nhieu diem o
    logo nhung phan con lai khac -> KHONG phai cung anh."""
    if not CV2:
        return
    with tempfile.TemporaryDirectory() as t:
        logo = _photo(9, 420, 420)
        a_im = Image.new("RGB", (1400, 900), (10, 10, 10))
        a_im.paste(logo, (490, 240))
        b_im = _photo(10)
        b_im.paste(logo, (200, 300))
        a = _save(a_im, t, "m3.png")
        b = _save(b_im, t, "m5.png")
        assert not same_photo.is_same_photo(a, b), same_photo.compare(a, b)


def test_gate_flags_two_slides_same_photo_and_skips_charts():
    if not CV2:
        return
    with tempfile.TemporaryDirectory() as t:
        goc = _photo(3)
        p1 = _save(goc, t, "a26.png")
        p2 = _save(goc.crop((80, 50, 1320, 850)), t, "a59.png")
        p3 = _save(_photo(4), t, "a42.png")
        anh = {"A26": {"original_path": p1, "kind": "photo", "domain": "computerworld.com"},
               "A59": {"original_path": p2, "kind": "photo", "domain": "9to5mac.com"},
               "A42": {"original_path": p3, "kind": "photo", "domain": "webrazzi.com"},
               "C1": {"original_path": p1, "kind": "chart"},
               "C2": {"original_path": p2, "kind": "chart"}}
        loi = nc.check_same_photo(anh, [("slide 5", ["A59", "A42"]), ("slide 6", ["A26"])])
        assert len(loi) == 1 and "A26" in loi[0] and "A59" in loi[0] and "CÙNG MỘT" in loi[0], loi
        # chart cung khuon khong xet
        assert nc.check_same_photo(anh, [("slide 2", ["C1"]), ("slide 3", ["C2"])]) == []
        # moi slide mot anh rieng -> sach
        assert nc.check_same_photo(anh, [("slide 2", ["A26"]), ("slide 3", ["A42"])]) == []


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
