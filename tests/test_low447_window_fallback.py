"""LOW-447: `digest_slide.choose_window` (Hiro) khi MOI khung cat deu bi bac vi mat de len chu.

Audit 30/09/2026: anh doc 1000x1250 (da sat 4:5), mat y 0,45..0,75. Khong khung nao giu duoc day
mat tren dong chu dau - FACE_TEXT_GAP; code cu roi xuong "khung giua" = (0, 0, 1000, 1250), chinh
khung day mat 1012px nam giua khung quote, va khong bao gi. Khung phong 1.4 dich xuong chi hut ~14px.

Giu:
  1. Du phong chon khung mat TRAN IT NHAT (px tren canvas), khong phai khung giua.
  2. Ghi `face_text_overlap_px` vao report va build_all in dong [CANH BAO] (khong chan).
  3. Ca binh thuong (co khung dat, hoac khong co mat) khong ghi gi vao report.
  4. Mat qua nho de nhan ra (< subject_fit.FACE_MIN_HEIGHT, nguoi dung xa) khong ep phong/dich:
     dung that 30/09 (quay le tan AMD, mat 2% anh) ban dau phong 1.4 lam tieu de mat chu.

Chay:  python tests/test_low447_window_fallback.py
"""
import contextlib
import io
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from PIL import Image, ImageDraw                               # noqa: E402

import digest_slide as ds                                      # noqa: E402
import tam                                                     # noqa: E402

TEXT = ("OpenAI ra mắt GPT-5.5 cho mọi người dùng", "Giá giảm một nửa so với bản trước, có ngay hôm nay.")
LOW_FACE = [0.35, 0.45, 0.65, 0.75]                             # mat thap tren anh doc (so audit)


def _g():
    return ds.geometry(ds.fit_text(ImageDraw.Draw(Image.new("RGB", (ds.W, ds.H))), *TEXT))


def _face_bottom_on_canvas(face, size, box):
    x0, y0, ww, wh = box
    return (face[3] * size[1] - y0) / wh * ds.H


def test_all_windows_rejected_picks_least_overlap_not_middle():
    im = Image.new("RGB", (1000, 1250), (40, 40, 40))
    g = _g()
    box = ds.choose_window(im, [LOW_FACE], g)
    middle = ds._windows(1000, 1250, 1.0)[len(ds._windows(1000, 1250, 1.0)) // 2]
    assert tuple(round(v) for v in box) != tuple(round(v) for v in middle), box
    limit = g["first_line_top"] - ds.FACE_TEXT_GAP
    old = _face_bottom_on_canvas(LOW_FACE, im.size, middle) - limit
    new = _face_bottom_on_canvas(LOW_FACE, im.size, box) - limit
    assert old > 100 and 0 < new < 30, (old, new, box)
    # mat van con nguyen trong khung (khong doi de-chu lay cat-mat)
    x0, y0, ww, wh = box
    assert x0 <= LOW_FACE[0] * 1000 and LOW_FACE[2] * 1000 <= x0 + ww and y0 <= LOW_FACE[1] * 1250, box
    rep = {}
    assert tuple(ds.choose_window(im, [LOW_FACE], g, rep)) == tuple(box)
    assert rep.get("face_text_overlap_px") == round(new), (rep, new)


def test_normal_cases_write_nothing_to_report():
    g = _g()
    im = Image.new("RGB", (800, 1000), (90, 90, 90))
    for faces in ([], [[0.4, 0.05, 0.6, 0.2]], [[0.3, 0.2, 0.5, 0.4]]):
        rep = {}
        box = ds.choose_window(im, faces, g, rep)
        assert rep == {}, (faces, rep)
        for f in faces:
            assert _face_bottom_on_canvas(f, im.size, box) <= g["first_line_top"] - ds.FACE_TEXT_GAP, (f, box)
    ds.choose_window(im, [LOW_FACE], g)                        # report=None van chay (build goi thang)


def test_tiny_background_faces_do_not_force_the_crop():
    im = Image.new("RGB", (864, 1080), (40, 40, 40))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 900, 864, 1080), fill=(230, 220, 200))   # quay sang duoi day, nguoi dung xa
    g = _g()
    tiny = [[0.30, 0.827, 0.324, 0.851], [0.408, 0.839, 0.428, 0.859]]   # so do that 260930_4C
    rep = {}
    assert tuple(ds.choose_window(im, tiny, g, rep)) == tuple(ds.choose_window(im, [], g)), rep
    assert rep == {}, rep


def _photo(path):
    rnd = random.Random(7)
    im = Image.new("RGB", (1000, 1250), (70, 90, 120))
    d = ImageDraw.Draw(im)
    for _ in range(400):
        x, y = rnd.randint(0, 1000), rnd.randint(0, 1250)
        d.ellipse((x, y, x + 60, y + 60), fill=tuple(rnd.randint(0, 255) for _ in range(3)))
    im.save(path)
    return str(path)


def test_build_all_prints_warning_but_does_not_block():
    tmp = tam.temp_dir(prefix="low447_")
    p = _photo(tmp / "low_face.png")
    cu = ds._face_boxes
    ds._face_boxes = lambda path: [LOW_FACE]
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            paths, errors = ds.build_all([{"image": p, "title": TEXT[0], "summary": TEXT[1]}], tmp / "q.png", "dcgr")
    finally:
        ds._face_boxes = cu
    assert errors == [] and len(paths) == 1 and paths[0].exists(), errors
    assert "[CANH BAO] slide 1" in err.getvalue() and "px" in err.getvalue(), err.getvalue()


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
