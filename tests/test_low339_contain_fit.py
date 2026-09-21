#!/usr/bin/env python3
"""LOW-339: logo / hình vẽ nền sáng cao hơn vùng trên khung chữ phải CO CẢ TẤM cho vừa.

Slide 04/06 "Pirate Face" (Kite, blog, 21/09/2026): `A77.png` 806x980, nét đen chạm mép,
mép trên chỉ 83% trắng nên `read_background` xếp là ảnh chụp ('mo'); ~40% hình nằm sau
khung chữ. Nhánh 'phang' cũng chỉ CẮT mép dưới (`set_image(..., True)` -> 700/1313) chứ
không co ảnh. Không hạ ngưỡng phẳng chung: trên 247 ảnh Kite thật có 25 ảnh 'mo' nằm
0,60–0,85 (ảnh chụp màu, bảng xếp hạng).

Chạy:  venv/bin/python tests/test_low339_contain_fit.py
"""
import subprocess
import sys
import tempfile
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import render_edu as re_                                      # noqa: E402

TH = dict(bg="#171A21", panel="#212530", line="#333846",
          a="#2FD4E1", b="#8E86F0", stand="#BFC5CF")
# Số đo thật của A77 trong manifest blog/pirate-face-… (vision).
PIRATE_MANIFEST = {"subject_kind": "logo", "subject_box": [0.01, 0.01, 0.99, 0.99],
                   "empty_share": 0.35, "w": 806, "h": 980, "kind": "chart"}


def _line_art(w=806, h=980, color=(200, 20, 20), border_touch=True):
    """Hình vẽ nét đậm nền trắng, nét chạm mép trên (như A77: mép trên < 85% trắng)."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.ellipse((int(w * 0.05), 0 if border_touch else 20, int(w * 0.95), int(h * 0.98)),
              outline=color, width=int(w * 0.06))
    d.rectangle((int(w * 0.35), int(h * 0.45), int(w * 0.65), int(h * 0.75)), fill=color)
    tmp = Path(tempfile.mkdtemp()) / "art.png"
    im.save(tmp)
    return tmp


def _photo(w=806, h=980):
    """Ảnh 'thật': mép lốm đốm nhiều màu, không thể hoà vào một màu nền."""
    import random
    from PIL import Image
    random.seed(3)
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            px[x, y] = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))
    tmp = Path(tempfile.mkdtemp()) / "photo.png"
    im.save(tmp)
    return tmp


def test_pirate_is_below_text_zone_but_4x5_logo_card_is_not():
    assert re_.subject_below_text_zone(PIRATE_MANIFEST)
    # thẻ logo 4:5 (1080x1350) logo nằm trên cao: đáy chủ thể 0.35 x 1350 = 472 < 700
    card = {"subject_kind": "logo", "subject_box": [0.1, 0.1, 0.9, 0.35],
            "empty_share": 0.5, "w": 1080, "h": 1350}
    assert not re_.subject_below_text_zone(card)
    assert not re_.subject_below_text_zone({**PIRATE_MANIFEST, "subject_kind": "person"})
    assert not re_.subject_below_text_zone({**PIRATE_MANIFEST, "subject_box": None})


def test_edge_ground_share_accepts_line_art_and_rejects_photo():
    share, ground = re_.edge_ground_share(_line_art())
    assert share >= re_.CONTAIN_GROUND_MIN and ground == (255, 255, 255), (share, ground)
    share2, _ = re_.edge_ground_share(_photo())
    assert share2 < re_.CONTAIN_GROUND_MIN, share2


def test_contain_background_shape_and_text_colour():
    p = _line_art()
    nen, anh = re_.image_make_background({"image": str(p), "image_fit": "contain"}, TH, "figure")
    assert anh == ""
    room = int(re_.H * re_.FIG_BOTTOM_FLAT) - re_.FIG_FIXED
    assert f"height:{room}px" in nen and "object-fit:contain" in nen, nen[:300]
    for cu in ("fig-molop", "fig-man", "__datMan", "blur("):
        assert cu not in nen, f"chế độ co ảnh không được có {cu}"
    assert 'background:#FFFFFF' in nen
    assert "#figtxt .title{color:rgba(0,0,0" in nen, "nền sáng phải đảo chữ sang tối"


def test_falls_back_to_old_path_when_edges_are_not_one_colour():
    nen, _ = re_.image_make_background({"image": str(_photo()), "image_fit": "contain"}, TH, "figure")
    assert "object-fit:contain" not in nen
    assert 'class="fig-sac' in nen


def test_falls_back_when_image_already_fits():
    p = _line_art(w=1200, h=600)              # ngang: cao hiện 540 <= 700
    nen, _ = re_.image_make_background({"image": str(p), "image_fit": "contain"}, TH, "figure")
    assert "object-fit:contain" not in nen


def test_no_image_fit_key_means_no_change():
    p = _line_art()
    nen, _ = re_.image_make_background({"image": str(p)}, TH, "figure")
    assert "object-fit:contain" not in nen


def _render_slide(image, image_fit):
    """Dựng slide figure thật bằng Chromium; trả ảnh PNG slide 4 (khung 1080x1350 x scale)."""
    slides = [{"kind": "cover", "eyebrow": "A", "title": "Bia test", "standfirst": "s",
               "byline": ["b"]},
              {"kind": "statement", "eyebrow": "B", "title": "Hai", "standfirst": "s",
               "cards": [{"num": "01", "text": "x"}]},
              {"kind": "steps", "eyebrow": "C", "title": "Ba",
               "steps": [{"title": "t", "desc": "d"}]},
              {"kind": "figure", "eyebrow": "BIỂU TƯỢNG", "title": "Ý tưởng bảo tồn vĩnh cửu cho trọng số mở",
               "standfirst": "Hình ảnh cướp biển đại diện cho triết lý chia sẻ ngang hàng tự do.",
               "image": str(image), **({"image_fit": "contain"} if image_fit else {})},
              {"kind": "loop", "eyebrow": "D", "title": "Năm", "standfirst": "s",
               "chips": ["a", "b"], "callout": "c"},
              {"kind": "cta", "eyebrow": "E", "title": "Sáu", "checks": ["a", "b"]}]
    d = Path(tempfile.mkdtemp())
    spec = {"brand": "donniechublog", "section": "TEST", "folio": "TEST", "theme": "ink",
            "hero": "orbit", "slides": slides}
    (d / "spec.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "render_edu.py"), "--spec", str(d / "spec.json"),
                        "--out", str(d / "s.png"), "--brand", "donniechublog", "--theme", "ink",
                        "--bo-qua-dau", "--scale", "1"], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-400:]
    return d / "s_4.png"


def _red_rows(png):
    """(hàng đỏ đầu, hàng đỏ cuối) của nét hình (đỏ thuần, tách khỏi chữ đen/xanh)."""
    from PIL import Image
    im = Image.open(png).convert("RGB")
    w, h = im.size
    rows = [y for y in range(h)
            if any(im.getpixel((x, y))[0] > 150 and im.getpixel((x, y))[1] < 80 and im.getpixel((x, y))[2] < 80
                   for x in range(0, w, 4))]
    return (min(rows), max(rows), h) if rows else (None, None, h)


def test_real_render_whole_figure_stays_above_text_zone():
    """Cổng đo trên pixel thật: nét hình (đỏ) phải kết thúc trên mép trên vùng chữ, và
    ảnh cũ (không co) thì KHÔNG — đó là lỗi gốc."""
    art = _line_art()
    top, bottom, h = _red_rows(_render_slide(art, image_fit=True))
    limit = (re_.FIG_FIXED + int(re_.H * re_.FIG_BOTTOM_FLAT) - re_.FIG_FIXED) / re_.H
    assert top is not None and bottom / h <= limit + 0.01, (top, bottom, h, limit)
    assert top / h >= re_.FIG_FIXED / re_.H - 0.01, "hình không được tràn lên masthead"
    _, old_bottom, old_h = _red_rows(_render_slide(art, image_fit=False))
    assert old_bottom / old_h > limit + 0.05, (
        "ảnh không co lẽ ra phải tràn xuống dưới vùng trên chữ (lỗi gốc LOW-339)", old_bottom / old_h)


def _padded_canvas():
    """Khung 4:5 (1080x1350) nền đen đệm sẵn quanh một tấm 1000x560 nhiều màu ở giữa,
    như infographic MediaTek / ảnh toà nhà TSMC thật (edge 1.0, nền đen phẳng)."""
    import random
    from PIL import Image
    random.seed(5)
    im = Image.new("RGB", (1080, 1350), (0, 0, 0))
    px = im.load()
    for y in range(400, 960):
        for x in range(40, 1040):
            px[x, y] = (random.randint(80, 255), random.randint(80, 255), random.randint(80, 255))
    tmp = Path(tempfile.mkdtemp()) / "padded.png"
    im.save(tmp)
    return tmp


def test_flat_padding_is_trimmed_before_fitting():
    """Co cả khung 4:5 làm hình thật chỉ còn ~50% bề ngang (chữ infographic không đọc được).
    Phải bỏ viền nền phẳng rồi mới co: tấm 1000x560 -> gần full bề ngang khung."""
    import re
    p = _padded_canvas()
    ground = re_.contain_ground(p, 1080, 1350)
    assert ground == (0, 0, 0), ground
    box = re_.content_box(p, ground)      # đo trên bản thu nhỏ nên lệch vài pixel
    assert all(abs(a - b) <= 8 for a, b in zip(box, (40, 400, 1040, 960))), box
    nen, _ = re_.image_make_background({"image": str(p), "image_fit": "contain"}, TH, "figure")
    width = int(re.search(r"width:(\d+)px;height:(\d+)px", nen).group(1))
    assert width >= 0.9 * re_.W, f"hình thật chỉ chiếm {width}/{re_.W}px sau khi co"
    # đã trong bằng nền phẳng thì không cắt gì
    assert re_.content_box(_line_art(), (255, 255, 255)) is not None
    from PIL import Image
    blank = Path(tempfile.mkdtemp()) / "blank.png"
    Image.new("RGB", (300, 300), (255, 255, 255)).save(blank)
    assert re_.content_box(blank, (255, 255, 255)) is None


def _boxed_picture(pic_w=700, pic_h=1000):
    """Khung 4:5 nền đen quanh MỘT TẤM ẢNH có khung riêng (như ảnh toà nhà TSMC, banner cookie)."""
    import random
    from PIL import Image
    random.seed(9)
    im = Image.new("RGB", (1080, 1350), (0, 0, 0))
    px = im.load()
    x0, y0 = (1080 - pic_w) // 2, 100
    for y in range(y0, y0 + pic_h):
        for x in range(x0, x0 + pic_w):
            px[x, y] = (random.randint(60, 255), random.randint(60, 255), random.randint(60, 255))
    tmp = Path(tempfile.mkdtemp()) / "boxed.png"
    im.save(tmp)
    return tmp


def test_boxed_picture_not_full_width_is_rejected_but_logo_that_blends_is_not():
    """Ông Chủ 21/09/2026 xem 6 ảnh thật: banner cookie (52% bề ngang) và toà nhà TSMC (63%) lộ
    thành cái hộp trên nền đen -> "ko hiển thị được full width thì ko sử dụng". Logo nền sáng
    hoà vào nền (cướp biển, GA Today) thì được giữ."""
    import kite_submit as ks
    boxed = _boxed_picture()
    fit = re_.contain_fit(boxed, 1080, 1350)
    assert fit and not fit["blends"] and fit["width_share"] < re_.CONTAIN_FULL_WIDTH_MIN, fit
    m = {"images": [{"id": "A9", "original_path": str(boxed), "w": 1080, "h": 1350}]}
    slide = {"kind": "figure", "image": str(boxed), "image_fit": "contain"}
    loi = ks.check_subject_above_text({"slides": [slide]}, m, {1: 916.0})
    assert len(loi) == 1 and "full bề ngang" in loi[0], loi
    art = _line_art()
    fit2 = re_.contain_fit(art, 806, 980)
    assert fit2["blends"] and fit2["width_share"] < re_.CONTAIN_FULL_WIDTH_MIN, fit2
    m2 = {"images": [{"id": "A77", "original_path": str(art), "w": 806, "h": 980}]}
    assert ks.check_subject_above_text({"slides": [{**slide, "image": str(art)}]}, m2, {1: 916.0}) == []
    # tấm ảnh rộng gần full khung (infographic MediaTek) thì đạt
    wide = _boxed_picture(pic_w=1040, pic_h=650)
    assert re_.contain_fit(wide, 1080, 1350)["width_share"] >= re_.CONTAIN_FULL_WIDTH_MIN


def test_forced_boxed_picture_goes_full_width_with_text_layer_over_overflow():
    """Ông Chủ 21/09/2026: "buộc phải sử dụng thì phóng lớn ra full width, phần thừa chạm text
    thì để layer của text phủ lên". Cổng nộp cho qua khi slide ghi image_force; renderer bỏ
    viền nền đệm rồi đi đường ảnh chụp (full bề ngang + dải phủ dưới chữ), KHÔNG co thành hộp."""
    import kite_submit as ks
    boxed = _boxed_picture()
    nen, _ = re_.image_make_background({"image": str(boxed), "image_fit": "contain"}, TH, "figure")
    assert "object-fit:contain" not in nen, "hình có khung riêng không được co thành hộp"
    assert f"width:{re_.W}px" in nen or 'class="fig-sac' in nen
    for cu in ("__datMan", "fig-molop"):
        assert cu in nen, f"thiếu lớp chữ phủ lên phần thừa: {cu}"
    # viền nền đệm đã bị cắt: ảnh nhúng là tấm 700x1000, không phải khung 1080x1350
    import base64
    import io
    from PIL import Image
    m = __import__("re").search(r'src="data:image/png;base64,([^"]+)"', nen)
    assert Image.open(io.BytesIO(base64.b64decode(m.group(1)))).size[0] <= 720
    slide = {"kind": "figure", "image": str(boxed), "image_fit": "contain", "image_force": True}
    meta = {"images": [{"id": "A9", "original_path": str(boxed), "w": 1080, "h": 1350}]}
    assert ks.check_subject_above_text({"slides": [slide]}, meta, {1: 500.0}) == []


def _framed_picture(bar=30, side=2, sky=False):
    """Khung đen 1080x1350 quanh một tấm gradient xanh tối 1000x700 có VẠCH THỪA ở mép, như ảnh
    Gemini thật: thanh trắng dày ở đỉnh + vạch trắng mảnh hai bên (Ông Chủ 21/09/2026: "những
    đoạn chi tiết thừa vô duyên này phải loại bỏ triệt để"). `sky=True`: thay bằng vùng SÁNG
    dày ~12% chiều cao ở đỉnh (bầu trời thật, phải giữ)."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (1080, 1350), (0, 0, 0))
    d = ImageDraw.Draw(im)
    x0, y0, x1, y1 = 40, 300, 1040, 1000
    for y in range(y0, y1):
        t = (y - y0) / (y1 - y0)
        d.line((x0, y, x1, y), fill=(int(10 + 20 * t), int(15 + 60 * t), int(40 + 120 * t)))
    if sky:
        for y in range(y0, y0 + 84):
            d.line((x0, y, x1, y), fill=(200 - (y % 7), 210, 235))
    else:
        d.rectangle((x0, y0, x1, y0 + bar), fill=(245, 245, 245))
        d.rectangle((x0, y0, x0 + side - 1, y1), fill=(230, 230, 230))
        d.rectangle((x1 - side, y0, x1, y1), fill=(230, 230, 230))
    tmp = Path(tempfile.mkdtemp()) / "framed.png"
    im.save(tmp)
    return tmp


def test_stray_edge_bars_are_cut_but_real_content_is_kept():
    p = _framed_picture()
    ground = re_.contain_ground(p, 1080, 1350)
    x0, y0, x1, y1 = re_.content_box(p, ground)
    assert y0 >= 300 + 30 - 2, f"thanh trắng ở đỉnh còn sót: y0={y0}"
    assert x0 >= 40 + 2 - 1 and x1 <= 1040 - 2 + 1, f"vạch mảnh hai bên còn sót: {x0},{x1}"
    assert y1 >= 990 and x1 - x0 >= 990, "không được cắt vào tấm ảnh thật"
    # vùng sáng DÀY (bầu trời thật, > 6% chiều cao) không phải vạch thừa
    ps = _framed_picture(sky=True)
    box = re_.content_box(ps, re_.contain_ground(ps, 1080, 1350))
    assert box[1] <= 300 + 2, f"bầu trời thật bị cắt: {box}"
    # nét vẽ chạm mép (chóp râu logo) không bị coi là vạch thừa: đường nền trắng giữ nguyên
    assert re_.content_box(_line_art(), (255, 255, 255)) is not None       # chỉ bỏ lề trắng
    x0, y0, x1, y1 = re_.content_box(_line_art(), (255, 255, 255))
    assert y1 >= int(980 * 0.97) and (x1 - x0) >= int(806 * 0.88), (x0, y0, x1, y1)


def test_submit_guard_blocks_text_that_climbs_into_the_contained_image():
    """Đo thật trên 7 ảnh Kite: đáy ảnh co cố định ở y=850, khối chữ ngắn/thật bắt đầu 1030/916,
    chữ dài (2 cards + standfirst dài) bắt đầu 613 -> đè 237px vào hình. Cổng nộp phải chặn."""
    import kite_submit as ks
    art = _line_art()
    slide = {"kind": "figure", "image": str(art), "image_fit": "contain"}
    m = {"images": [{"id": "A1", "original_path": str(art), "w": 806, "h": 980}]}
    assert ks.check_subject_above_text({"slides": [slide]}, m, {1: 916.0}) == []
    loi = ks.check_subject_above_text({"slides": [slide]}, m, {1: 613.0})
    assert len(loi) == 1 and "Rút gọn chữ" in loi[0], loi
    # ảnh không co (không có image_fit) thì cổng này không xét, luật cũ giữ nguyên
    assert ks.check_subject_above_text({"slides": [{**slide, "image_fit": None}]}, m, {1: 613.0}) == []


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
