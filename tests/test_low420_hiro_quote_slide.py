"""LOW-420: slide Hiro theo khuon QUOTE cua Dre — tieu de trong khung, tom tat ngoai khung.

Ong Chu 26/09/2026: *"Output cua Hiro nen la dang Quote cua Dre, nhung thay vi dan mot cau trong
noi dung thi phan text la tieu de tom tat. Sau do o ngoai the quote se la summary ngan gon."*

Giu (do tren toa do + pixel that, khong chi doc code):
  1. Thu tu tu tren xuong: khung quote (chua tieu de) -> dau dong ngoac -> tom tat. Tom tat
     nam NGOAI khung, khong de len dau ngoac.
  2. Khung + tom tat nam trong vung an toan 1:1 (LOW-364) voi MOI do dai chu hop le.
  3. Tieu de + tom tat <= 20% khung (LOW-286); nen chu qua cong overlay.
  4. Net khung quote that su duoc ve (mau net cua Dre) o canh trai khung.

Chay:  python tests/test_low420_hiro_quote_slide.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
from PIL import Image, ImageDraw                               # noqa: E402

import carousel                                                # noqa: E402
import digest_slide as ds                                      # noqa: E402
import safe_zone                                               # noqa: E402
import tam                                                     # noqa: E402

SHORT = ("OpenAI ra mắt GPT-5.5", "Giá giảm một nửa.")
LONG = ("Microsoft khánh thành vùng đám mây thứ tư tại Telangana, Ấn Độ, đón sóng AI",
        "Microsoft mở rộng cụm trung tâm dữ liệu đám mây tại thị trường chiến lược Ấn Độ.")


def _lay(title, summary):
    return ds.fit_text(ImageDraw.Draw(Image.new("RGB", (ds.W, ds.H))), title, summary)


def _photo(path):
    import random
    rnd = random.Random(5)
    im = Image.new("RGB", (1080, 1350), (70, 90, 120))
    d = ImageDraw.Draw(im)
    for _ in range(500):
        x, y = rnd.randint(0, 1080), rnd.randint(0, 1350)
        d.ellipse((x, y, x + 60, y + 60), fill=tuple(rnd.randint(0, 255) for _ in range(3)))
    im.save(path)
    return str(path)


def test_order_frame_then_summary_outside():
    for title, summary in (SHORT, LONG):
        g = ds.geometry(_lay(title, summary))
        assert g["frame_top"] < g["first_line_top"] < g["frame_bottom"], g
        assert g["frame_bottom"] + carousel.Q_FRAME_DROP < g["summary_top"], "tom tat de len dau dong ngoac"
        assert g["summary_top"] < g["summary_bottom"]


def test_frame_and_summary_inside_safe_zone_for_all_valid_lengths():
    top, bottom = safe_zone.top(ds.W, ds.H), safe_zone.bottom(ds.W, ds.H)
    for title, summary in (SHORT, LONG):
        g = ds.geometry(_lay(title, summary))
        assert g["frame_top"] - carousel.Q_MARK_CLEAR >= top, (title, g)
        assert g["summary_bottom"] <= bottom, (title, g)


def test_text_budget_twenty_percent():
    for title, summary in (SHORT, LONG):
        lay = _lay(title, summary)
        assert lay.total <= ds.TEXT_MAX_H == round(ds.H * 0.20)
        assert len(lay.title_lines) <= ds.TITLE_MAX_LINES
        assert lay.summary_font.size < lay.title_font.size


def test_rendered_slide_has_quote_frame_and_passes_overlay_gate():
    tmp = Path(tam.temp_dir(prefix="low420_"))
    img = _photo(tmp / "p.png")
    slides = [{"image": img, "title": LONG[0], "summary": LONG[1]},
              {"image": img, "title": SHORT[0], "summary": SHORT[1]}]
    paths, errors = ds.build_all(slides, tmp / "q.png", "dcgr")
    assert errors == [], errors
    sizes = ds.deck_sizes(slides)
    g = ds.geometry(ds.fit_text(ImageDraw.Draw(Image.new("RGB", (ds.W, ds.H))),
                                LONG[0], LONG[1], ds.TEXT_MAX_H, *sizes))
    net = carousel._net()
    with Image.open(paths[0]) as im:
        px = im.convert("RGB")
        # net doc TRAI cua khung (goc tren-trai: r=30, net doc tu y0+r xuong 1/2 khung)
        y = g["frame_top"] + 30 + 20
        found = [px.getpixel((ds.FRAME_X + dx, y)) for dx in range(-3, 4)]
        assert any(max(abs(a - b) for a, b in zip(c, net)) <= 40 for c in found), (found, net)


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
