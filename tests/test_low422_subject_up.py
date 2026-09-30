"""LOW-422: chu the len nua tren khung, day anh keo dai bang mau mep (Ong Chu 30/09/2026:
*"day logo cao len cho phan duoi nhieu khong gian de text ko bi chen vao chu the"*).

Chay:  python tests/test_low422_subject_up.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from PIL import Image, ImageDraw                               # noqa: E402

import digest_slide as ds                                      # noqa: E402
import subject_focus                                           # noqa: E402


def _blob_img(w, h, box):
    im = Image.new("RGB", (w, h), (10, 10, 10))
    ImageDraw.Draw(im).rectangle(box, fill=(240, 240, 240))
    return im


def test_edge_box_finds_the_bright_subject():
    im = _blob_img(600, 900, (150, 500, 450, 800))
    subject_focus._faces = lambda i: []
    box = subject_focus.find(im)
    assert box and 0.2 < box[0] < 0.3 and 0.7 < box[2] < 0.8 and 0.5 < box[1] < 0.62 and 0.85 < box[3] < 0.95, box


def test_crop_center_puts_subject_in_upper_half_for_tall_image():
    """Anh doc: chu the o duoi (y 0.55..0.9) -> cat 4:5 day chu the len het muc anh cho phep."""
    import crop_ratio
    subject_focus._faces = lambda i: []
    im = _blob_img(600, 1200, (150, 660, 450, 1080))
    cx, cy = subject_focus.crop_center(im, 0.8)
    ra = crop_ratio.crop(im, 0.8, cx, cy, cat_ngang=True)
    sub_center_y = (0.5 * (660 + 1080) - (im.height - ra.height) * 0)  # toa do anh goc
    y0 = round(cy * im.height - ra.height / 2)
    y0 = max(0, min(im.height - ra.height, y0))
    rel = (sub_center_y - y0) / ra.height
    assert rel < 0.6, (rel, cx, cy)                                   # cat giua: 0.86; day cua anh chan o 0.56
    assert (cx, cy) != (0.5, 0.5)


def test_crop_center_flat_image_falls_back_to_center():
    subject_focus._faces = lambda i: []
    assert subject_focus.crop_center(Image.new("RGB", (400, 600), (50, 50, 50)), 0.8) == (0.5, 0.5)


def test_extend_bottom_only_when_bottom_is_simple():
    dark = _blob_img(400, 500, (100, 100, 300, 250))                   # day toi phang
    out, k = ds.extend_bottom(dark)
    assert k > 1.2 and out.height == round(500 * (1 + ds.EXT_MAX)), (k, out.size)
    # mep noi: hang cuoi anh goc va hang dau phan keo dai cung mau (khong lo vet)
    assert max(abs(a - b) for a, b in zip(out.getpixel((10, 499)), out.getpixel((10, 501)))) <= 3
    noisy = Image.effect_noise((400, 500), 90).convert("RGB")           # day nhieu chi tiet
    out2, k2 = ds.extend_bottom(noisy)
    assert k2 == 1.0 and out2.size == (400, 500)


def test_choose_window_uses_extension_to_lift_subject():
    """Logo sang o ~62%..80% chieu cao tren nen toi: khung chon phai day logo len (y0 > 0 trong anh
    da keo dai) de vung chu ra nen toi."""
    im = _blob_img(800, 1000, (150, 600, 650, 820))
    ext, k = ds.extend_bottom(im)
    assert k > 1.0
    g = ds.geometry(ds._lay(*("OpenAI ra mắt GPT-5.5", "Giá giảm một nửa.")) if hasattr(ds, "_lay") else
                    ds.fit_text(ImageDraw.Draw(Image.new("RGB", (ds.W, ds.H))), "OpenAI ra mắt GPT-5.5", "Giá giảm một nửa."))
    x0, y0, ww, wh = ds.choose_window(ext, [], g)
    assert y0 > 0.05 * ext.height, (x0, y0, ww, wh, ext.size)


if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "tests"))
    from tam import chay_tat_ca
    chay_tat_ca(globals())
