#!/usr/bin/env python3
"""Gin/Itachi/deck keys -> English (LOW-247, part of LOW-243).

Guards: the legacy maps in gin_submit/itachi_submit/deck and the migration maps equal the approved
table docs/tu_dien_ten/gin_itachi_keys_v2.json; writers (gin_prepare regions, briefs, Itachi
manifest, deck.spec.json) emit only the new names; an OLD-key spec and the equivalent NEW-key spec
give the same draw blocks as the pre-LOW-247 code (golden below, captured from main 88f7164 on the
same fixture), the same Gin card pixels and caption, the same Itachi in-place/deck PNGs, the same
[LOI] lines and the same deck render; new name wins when both are present; the one-shot
migrate_gin_itachi_stores.py renames every store (both layouts), keeps unknown keys, refuses an
unknown shape (nothing written), keeps an unparseable spec, and a re-run is a no-op."""
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import state_paths as sp                                      # noqa: E402

TABLE = json.loads((ROOT / "docs" / "tu_dien_ten" / "gin_itachi_keys_v2.json").read_text(encoding="utf-8"))
FONTS = ROOT / "assets" / "fonts"


def _clean(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


# ------------------------------------------------------------------ fixture
def _region(number, x, y, w, h, text, kind, std, rgb, ink, ratio, adv, font, align) -> dict:
    return {"box": [[x, y], [x + w, y], [x + w, y + h], [x, y + h]], "x": x, "y": y, "w": w, "h": h,
            "text": text, "conf": 0.99, "color_rgb": [250, 250, 250], "background_kind": kind,
            "background_std": std, "background_rgb": rgb, "ink_height": ink, "ink_ratio": ratio, "adv": adv,
            "font": font, "align": align, "number": number}


# Measured by gin_prepare on _image() (boxes then widened by 6 px, like a real OCR box).
REGIONS = [
    _region(1, 51, 100, 245, 43, "PHOTO TEXT", "photo", 74.0, [126, 125, 127], 31, 0.493, 0.752, "bold", "left"),
    _region(2, 31, 260, 286, 39, "THE QUICK BROWN", "flat", 0.0, [8, 8, 8], 21, 0.333, 0.838, "bold", "left"),
    _region(3, 31, 300, 262, 39, "FOX JUMPS OVER", "flat", 0.0, [8, 8, 8], 21, 0.317, 0.816, "regular", "left"),
    _region(4, 31, 340, 227, 39, "THE LAZY DOG", "flat", 0.0, [8, 8, 8], 21, 0.287, 0.821, "regular", "left"),
    _region(5, 241, 410, 142, 43, "BADGE", "flat", 0.0, [8, 8, 8], 25, 0.534, 0.96, "bold", "center"),
]


def _image():
    import numpy as np
    from PIL import Image, ImageDraw, ImageFont
    rng = np.random.default_rng(7)
    a = np.zeros((480, 640, 3), np.uint8)
    a[:240] = rng.integers(0, 255, (240, 640, 3), dtype=np.uint8)
    a[240:] = (8, 8, 8)
    im = Image.fromarray(a)
    d = ImageDraw.Draw(im)
    reg = ImageFont.truetype(str(FONTS / "BeVietnamPro-Regular.ttf"), 28)
    bold = ImageFont.truetype(str(FONTS / "BeVietnamPro-Bold.ttf"), 34)
    for xy, text, f in (((40, 262), "THE QUICK BROWN", reg), ((40, 302), "FOX JUMPS OVER", reg),
                        ((40, 342), "THE LAZY DOG", reg), ((250, 410), "BADGE", bold), ((60, 100), "PHOTO TEXT", bold)):
        d.text(xy, text, font=f, fill=(250, 250, 250))
    return im


LONG = ("Một câu dịch dài gấp nhiều lần câu gốc, kể lể đủ thứ chi tiết mà hộp gốc không bao giờ chứa nổi "
        "dù chữ đã nhỏ hết cỡ, thật dài thật dài thật dài")
PARA = "Con cáo nâu nhanh nhẹn nhảy qua chó lười"
GIN_OLD = {
    "A": {"gop": [[2, 4, PARA]], "vung": {"5": {"text": "Nhãn", "can": "center"}, "1": None}, "ghi_chu": "Ghi chú cho Ông Chủ"},
    "B": {"vung": {"2": "Cáo nâu", "3": "nhảy qua", "4": None, "5": "Nhãn",
                   "1": {"text": "Chữ ảnh", "font": "bold", "color_rgb": [255, 0, 0], "can": "left"}}, "ep_phang": [1]},
    "C": {"vung": {"9": "x", "2": "Một"}},
    "D": {"vung": ["x"]},
    "E": {"gop": [[1, 3, "abc"], ["x"], [7, 8, "y"]], "vung": {"1": "Ảnh", "4": "", "5": 3}},
    "F": {},
    "G": {"gop": [[2, 4, LONG]], "vung": {"5": "NHAN", "1": None}},
}
GIN_NEW = {
    "A": {"merges": [[2, 4, PARA]], "region_texts": {"5": {"text": "Nhãn", "align": "center"}, "1": None}, "note": "Ghi chú cho Ông Chủ"},
    "B": {"region_texts": {"2": "Cáo nâu", "3": "nhảy qua", "4": None, "5": "Nhãn",
                           "1": {"text": "Chữ ảnh", "font": "bold", "color_rgb": [255, 0, 0], "align": "left"}},
          "force_flat": [1]},
    "C": {"region_texts": {"9": "x", "2": "Một"}},
    "D": {"region_texts": ["x"]},
    "E": {"merges": [[1, 3, "abc"], ["x"], [7, 8, "y"]], "region_texts": {"1": "Ảnh", "4": "", "5": 3}},
    "F": {},
    "G": {"merges": [[2, 4, LONG]], "region_texts": {"5": "NHAN", "1": None}},
}
W250 = [250, 250, 250]
# _box_translate of the pre-LOW-247 code on the old-key specs (number, x, y, w, h, source numbers, text,
# ocr_text, ink_height, font, line_pitch, color_rgb, align) and its [LOI] lines with the renamed tokens.
GOLDEN_BLOCKS = {
    "A": [["2-4", 31, 260, 286, 119, [2, 3, 4], PARA, "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG", 21, "regular", 40, W250, "left"],
          [5, 241, 410, 142, 43, [5], "Nhãn", "BADGE", 25, "bold", None, W250, "center"]],
    "B": [[2, 31, 260, 286, 39, [2], "Cáo nâu", "THE QUICK BROWN", 21, "bold", None, W250, "left"],
          [3, 31, 300, 262, 39, [3], "nhảy qua", "FOX JUMPS OVER", 21, "regular", None, W250, "left"],
          [5, 241, 410, 142, 43, [5], "Nhãn", "BADGE", 25, "bold", None, W250, "center"],
          [1, 51, 100, 245, 43, [1], "Chữ ảnh", "PHOTO TEXT", 31, "bold", None, [255, 0, 0], "left"]],
    "C": [[2, 31, 260, 286, 39, [2], "Một", "THE QUICK BROWN", 21, "bold", None, W250, "left"]],
    "D": [], "E": [], "F": [],
    "G": [["2-4", 31, 260, 286, 119, [2, 3, 4], LONG, "THE QUICK BROWN FOX JUMPS OVER THE LAZY DOG", 21, "regular", 40, W250, "left"],
          [5, 241, 410, 142, 43, [5], "NHAN", "BADGE", 25, "bold", None, W250, "center"]],
}
GOLDEN_ERRORS = {
    "C": ["`region_texts` có stt không tồn tại: 9 (ảnh này chỉ có 1, 2, 3, 4, 5).",
          "vùng nền phẳng 3, 4, 5 chưa khai trong `region_texts` — dịch thì ghi bản dịch, cố ý giữ chữ gốc thì ghi null."],
    "D": ['spec.json: "region_texts" phải là object {"<stt>": "<bản dịch>"} — xem brief.md.'],
    "E": ["merges 1..3 chứa vùng nền ảnh [1] — việc của Itachi. Thu hẹp dải gộp, hoặc thêm vào `force_flat` nếu đã xem preview.",
          'merges phải là [stt_đầu, stt_cuối, "bản dịch"]',
          "merges 7..8 không có vùng nào",
          "vùng nền phẳng 2, 3 chưa khai trong `region_texts` — dịch thì ghi bản dịch, cố ý giữ chữ gốc thì ghi null.",
          "vùng 1 'PHOTO TEXT' nằm trên NỀN ẢNH (std 74.0), xoá là hỏng ảnh — đó là việc của Itachi. Ghi null để giữ "
          'nguyên, hoặc thêm "force_flat": [1] nếu bạn đã xem preview và chắc nền phẳng.',
          "vùng 4: bản dịch rỗng — ghi null nếu cố ý giữ chữ gốc.",
          'vùng 5: phải là chuỗi bản dịch, null, hoặc object {"text": …, "font": …, "color_rgb": …, "align": …}.'],
    "F": ["spec.json chưa có `merges` lẫn `region_texts` — chưa khai bản dịch nào. Xem brief.md."],
}
GIN_CAPTION_A = ("Kết quả (trả lời Ông Chủ đúng một câu): Thẻ quote tiếng Việt (ảnh 777): thay 2 vùng chữ. "
                 "Còn 1 vùng nằm trên nền ảnh (stt 1) — việc của Itachi. Ghi chú cho Ông Chủ")

SUBS = [{"text": "dòng san hô", "col": "coral", "bold": True}]
TIERS = [[["DÒNG MỘT", "DÒNG HAI"], 110, 60], [["dòng nhỏ"], 60, 40]]
IT_OLD = {"slides": [
    {"nguon": "338", "cach": "tai_cho", "vung": {"1": "CHỮ ẢNH", "5": {"text": "NHÃN", "align": "center"}},
     "gop": [[2, 4, PARA]]},
    {"nguon": "339", "cach": "deck", "layout": "cover", "bg_anh": True, "tiers": TIERS,
     "ghi_chu": {"text": "ghi chú tay nè", "nghieng": -6, "x": 600}},
    {"nguon": "340", "cach": "DECK", "layout": "grid3", "badge": "BƯỚC 1", "serif": "Chữ nghiêng", "sans": "Chữ đậm",
     "sub": "phụ đề", "nhan": [{"text": "Nhãn một", "x": 300, "y": 900}, {"text": "Nhãn hai", "x": 700, "y": 900}],
     "footer": "chân trang"},
    {"nguon": "341", "cach": "deck", "layout": "statement", "heading": "Câu lớn", "bg": "cream",
     "subs": [{"text": "dòng đen", "col": "den"}] + SUBS},
]}
IT_NEW = {"slides": [
    {"slide_id": "338", "mode": "in_place", "region_texts": {"1": "CHỮ ẢNH", "5": {"text": "NHÃN", "align": "center"}},
     "merges": [[2, 4, PARA]]},
    {"slide_id": "339", "mode": "deck", "layout": "cover", "use_clean_background": True, "tiers": TIERS,
     "annotation": {"text": "ghi chú tay nè", "tilt": -6, "x": 600}},
    {"slide_id": "340", "mode": "DECK", "layout": "grid3", "badge": "BƯỚC 1", "serif": "Chữ nghiêng", "sans": "Chữ đậm",
     "sub": "phụ đề", "labels": [{"text": "Nhãn một", "x": 300, "y": 900}, {"text": "Nhãn hai", "x": 700, "y": 900}],
     "footer": "chân trang"},
    {"slide_id": "341", "mode": "deck", "layout": "statement", "heading": "Câu lớn", "bg": "cream",
     "subs": [{"text": "dòng đen", "col": "black"}] + SUBS},
]}
IT_BAD_OLD = {"slides": [{"nguon": "999"}, {"nguon": "338", "cach": "khac"},
                         {"nguon": "338", "vung": {"9": "x"}, "gop": [["x"], [8, 9, "y"]]},
                         {"nguon": "339", "cach": "deck", "layout": "nope"}]}
IT_BAD_NEW = {"slides": [{"slide_id": "999"}, {"slide_id": "338", "mode": "khac"},
                         {"slide_id": "338", "region_texts": {"9": "x"}, "merges": [["x"], [8, 9, "y"]]},
                         {"slide_id": "339", "mode": "deck", "layout": "nope"}]}
GOLDEN_IT_BAD = [
    "[LOI] mục 1: slide_id '999' không có trong bộ (có: 338, 339, 340, 341)",
    '[LOI] mục 2: mode phải là "in_place" hoặc "deck"',
    '[LOI] slide 338: merges phải là [stt_đầu, stt_cuối, "bản dịch"]',
    "[LOI] slide 338: merges 8..9 không có vùng nào",
    "[LOI] slide 338: vùng 9 không tồn tại (có: 1, 2, 3, 4, 5)",
    "[LOI] slide 338: vùng 1, 2, 3, 4, 5 chưa khai trong spec — dịch thì ghi bản dịch, cố ý bỏ trống thì ghi null "
    "(chữ gốc đã bị xoá, không khai là mất hẳn)",
    "[LOI] mục 4: layout 'nope' không hợp lệ",
]


def _compact(blocks: list) -> list:
    return [[b["number"], b["x"], b["y"], b["w"], b["h"], [v["number"] for v in b["source_regions"]], b["text"],
             b["ocr_text"], b["ink_height"], b["font"], b["line_pitch"], b["color_rgb"], b["align"]] for b in blocks]


def _pixels(p: Path) -> bytes:
    import numpy as np
    from PIL import Image
    return np.asarray(Image.open(p).convert("RGB")).tobytes()


def _env(state: Path) -> dict:
    env = {**os.environ, "CT_STATE_DIR": str(state)}
    env.pop("CT_BRAND", None)
    return env


def _gin_workdir(state: Path) -> Path:
    wd = sp.prepare_root(state) / "gin_777"
    wd.mkdir(parents=True, exist_ok=True)
    _image().save(wd / "src.png")
    (wd / sp.GIN_REGIONS_OCR_FILE).write_text(json.dumps(
        {"image_path": str(wd / "src.png"), "id": "777", "w": 640, "h": 480, "regions": REGIONS},
        ensure_ascii=False, indent=1), encoding="utf-8")
    return wd


def _itachi_workdir(state: Path, spec: dict) -> Path:
    import numpy as np
    from PIL import Image
    slides = []
    for sid, rgb in (("338", (8, 8, 8)), ("339", (120, 130, 140)), ("340", (8, 8, 8)), ("341", (120, 130, 140))):
        g = sp.prepare_root(state) / f"gin_{sid}"
        g.mkdir(parents=True, exist_ok=True)
        clean = g / sp.GIN_CLEAN_BACKGROUND_FILE
        Image.fromarray(np.full((480, 640, 3), rgb, np.uint8)).save(clean)
        regions = [{"number": r["number"], "x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"],
                    "color_rgb": r["color_rgb"], "ocr_text": r["text"], "conf": r["conf"]} for r in REGIONS]
        slides.append({"id": sid, "image_path": f"/in/{sid}.jpg", "w": 640, "h": 480,
                       "clean_background_path": str(clean), "regions": regions, "ocr_region_count": 5})
    wd = sp.prepare_root(state) / "itachi_338"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / sp.MANIFEST_FILE).write_text(json.dumps({"set_id": "338", "slides": slides}, ensure_ascii=False, indent=1),
                                       encoding="utf-8")
    (wd / "spec.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    return wd


def _run_submit(script: str, arg: str, state: Path):
    return subprocess.run([sys.executable, str(ROOT / script), arg, "--khong-gui"], capture_output=True, text=True,
                          cwd=str(ROOT), env=_env(state), timeout=300)


# ------------------------------------------------------------------ table <-> code
def test_maps_equal_approved_table():
    import deck
    import gin_submit
    import itachi_submit
    import migrate_gin_itachi_stores as m
    assert gin_submit.LEGACY_SPEC_KEYS == _clean(TABLE["gin_spec"]) == m.GIN_SPEC_KEY_MAP
    assert gin_submit.LEGACY_REGION_OVERRIDE_KEYS == _clean(TABLE["gin_spec.region_override"]) \
        == m.GIN_REGION_OVERRIDE_KEY_MAP
    assert itachi_submit.LEGACY_SLIDE_KEYS == _clean(TABLE["itachi_spec.slide"]) == m.ITACHI_SPEC_SLIDE_KEY_MAP
    assert itachi_submit.LEGACY_MODE_VALUES == TABLE["itachi_spec.slide.mode_values"] == m.ITACHI_MODE_VALUE_MAP
    assert deck.LEGACY_SLIDE_KEYS == _clean(TABLE["deck_spec.slide"]) == m.DECK_SLIDE_KEY_MAP
    assert deck.LEGACY_ANNOTATION_KEYS == TABLE["deck_spec.slide.annotation"] == m.DECK_ANNOTATION_KEY_MAP
    assert deck.LEGACY_SUB_COL_VALUES == TABLE["deck_spec.slide.subs.col_values"] == m.DECK_SUB_COL_VALUE_MAP
    assert m.REGIONS_OCR_KEY_MAP == _clean(TABLE["regions_ocr"])
    assert m.REGION_KEY_MAP == _clean(TABLE["regions_ocr.region"])
    assert m.BACKGROUND_KIND_VALUE_MAP == TABLE["regions_ocr.region.background_kind_values"]
    assert m.REGIONS_JSON_ITEM_KEY_MAP == _clean(TABLE["regions_json_item"])
    assert m.ITACHI_MANIFEST_KEY_MAP == _clean(TABLE["itachi_manifest"])
    assert m.ITACHI_MANIFEST_SLIDE_KEY_MAP == _clean(TABLE["itachi_manifest.slide"])
    assert m.FIXED_KEYS["region"] == set(TABLE["regions_ocr.region"]["_fixed"])
    assert m.FIXED_KEYS["regions_json_item"] == set(TABLE["regions_json_item"]["_fixed"])


# ------------------------------------------------------------------ writers emit new names only
def test_gin_prepare_regions_and_brief_new_names():
    import cv2
    import gin_prepare as gb
    import swap_image_text
    new_region = set(TABLE["regions_ocr.region"]["_fixed"]) | set(_clean(TABLE["regions_ocr.region"]).values())
    with tempfile.TemporaryDirectory() as t:
        src = Path(t) / "src.png"
        _image().save(src)
        # the unwidened boxes the fixture was measured on
        boxes = [([[r["x"] + 6, r["y"] + 6], [r["x"] + r["w"] - 6, r["y"] + 6], [r["x"] + r["w"] - 6, r["y"] + r["h"] - 6],
                   [r["x"] + 6, r["y"] + r["h"] - 6]], r["text"], r["conf"]) for r in REGIONS]
        orig = swap_image_text.find_region_text
        swap_image_text.find_region_text = lambda img, verbose=False: boxes
        try:
            img, regions = gb.ocr_region(src)
        finally:
            swap_image_text.find_region_text = orig
        for r in regions:
            assert set(r) == new_region, set(r) ^ new_region
            assert r["background_kind"] in ("flat", "photo"), r
        keep = ("number", "text", "background_kind", "background_std", "background_rgb", "ink_height", "ink_ratio",
                "adv", "font", "align")
        assert [{k: r[k] for k in keep} for r in regions] == [{k: r[k] for k in keep} for r in REGIONS], regions
        brief = gb.write_brief("777", src, cv2.imread(str(src)), REGIONS, Path(t))
    block = brief.split("spec.json\n", 1)[1]
    template = json.loads(block[:block.index("\n}") + 2])
    assert list(template) == ["merges", "region_texts", "note"], template
    for old in ("`gop`", "`vung`", "`ghi_chu`", '"can"'):
        assert old not in brief, old
    assert '"align": "left|center"' in brief and "`note` báo Ông Chủ" in brief


def test_itachi_brief_and_layout_help_new_names():
    import itachi_prepare as ip
    slides = [{"id": "338", "w": 640, "h": 480, "clean_background_path": "/cb.png",
               "regions": [{"number": 1, "x": 1, "y": 2, "w": 3, "h": 4, "color_rgb": W250, "ocr_text": "HI"}]}]
    brief = ip.write_brief(slides, "338", Path("/wd"))
    block = brief.split("giữ thứ tự\n", 1)[1]
    template = json.loads(block[:block.index("\n}") + 2])
    assert [list(s)[:3] for s in template["slides"]] == [["slide_id", "mode", "region_texts"],
                                                        ["slide_id", "mode", "layout"]]
    assert template["slides"][0]["mode"] == "in_place" and "merges" in template["slides"][0]
    assert template["slides"][1]["use_clean_background"] is True
    for old in ("tai_cho", "bg_anh", "`gop`", '"nhan"', '"ghi_chu"', '"nghieng"', '"nguon"', '"cach"'):
        assert old not in brief, old
    assert '"labels": [' in ip.LAYOUT_HELP["grid3"] and '"annotation": {' in ip.LAYOUT_HELP["cover"]
    assert '"tilt": -6' in ip.LAYOUT_HELP["cover"]


def test_prompts_name_new_tokens():
    texts = {p: (ROOT / p).read_text(encoding="utf-8") for p in (
        "hermes/profiles/shared/gin.SOUL.md", "hermes/profiles/shared/itachi.SOUL.md",
        "hermes/skills/inplace-translate/SKILL.md", "hermes/skills/ai-background/SKILL.md")}
    for p, s in texts.items():
        for old in ("`gop`", "tai_cho", "bg_anh", "ep_phang"):
            assert old not in s, (p, old)
    assert '"force_flat": [stt]' in texts["hermes/skills/inplace-translate/SKILL.md"]
    assert "`use_clean_background: true`" in texts["hermes/skills/inplace-translate/SKILL.md"]
    assert '`"bg_image"`' in texts["hermes/skills/ai-background/SKILL.md"]


# ------------------------------------------------------------------ Gin: old spec == new spec == before
def test_gin_old_and_new_spec_same_blocks_as_before():
    import gin_submit
    d = {"image_path": "/x.png", "id": "777", "w": 640, "h": 480, "regions": REGIONS}
    for k in GIN_OLD:
        old_blocks, old_errors = gin_submit._box_translate(d, GIN_OLD[k])
        new_blocks, new_errors = gin_submit._box_translate(d, GIN_NEW[k])
        assert old_blocks == new_blocks and old_errors == new_errors, k
        assert _compact(new_blocks) == GOLDEN_BLOCKS[k], (k, _compact(new_blocks))
        assert new_errors == GOLDEN_ERRORS.get(k, []), (k, new_errors)


def test_gin_legacy_spec_new_name_wins():
    import gin_submit
    both = {"gop": [[1, 2, "cũ"]], "merges": [[2, 4, "mới"]], "vung": {"1": {"text": "x", "can": "left", "align": "center"}},
            "giu": [3], "xoa_them": [[0, 0, 1, 1]]}
    got = gin_submit._legacy_spec(both)
    assert got == {"merges": [[2, 4, "mới"]], "region_texts": {"1": {"text": "x", "align": "center"}},
                   "mask_keep": [3], "mask_extra": [[0, 0, 1, 1]]}, got
    assert gin_submit._legacy_spec(GIN_NEW["B"]) == GIN_NEW["B"]
    assert gin_submit._legacy_spec(["x"]) == ["x"]


def test_gin_submit_old_and_new_spec_same_card_and_caption():
    with tempfile.TemporaryDirectory() as t:
        state = Path(t)
        wd = _gin_workdir(state)
        seen = {}
        for tag, specs in (("old", GIN_OLD), ("new", GIN_NEW)):
            for k in ("A", "B", "E"):
                (wd / "spec.json").write_text(json.dumps(specs[k], ensure_ascii=False), encoding="utf-8")
                (wd / sp.SUBMIT_COUNT_FILE).unlink(missing_ok=True)
                out = wd / f"{sp.GIN_RESULT_PREFIX}777.png"
                out.unlink(missing_ok=True)
                r = _run_submit("gin_submit.py", "777", state)
                seen[tag, k] = (r.returncode, r.stdout, _pixels(out) if out.exists() else None)
        for k in ("A", "B", "E"):
            assert seen["old", k] == seen["new", k], k
        assert seen["new", "A"][0] == 0 and seen["new", "A"][2] is not None, seen["new", "A"][:2]
        assert seen["new", "A"][1].strip().splitlines()[-1] == GIN_CAPTION_A
        assert seen["new", "B"][0] == 0 and seen["new", "A"][2] != seen["new", "B"][2]
        assert seen["new", "E"][0] == 1 and seen["new", "E"][2] is None
        assert [ln[len("[LOI] "):] for ln in seen["new", "E"][1].splitlines() if ln.startswith("[LOI]")] \
            == GOLDEN_ERRORS["E"]


# ------------------------------------------------------------------ Itachi + deck
def test_itachi_legacy_spec_normalises_deck_fields_and_mode():
    import itachi_submit
    got = itachi_submit._legacy_spec(IT_OLD)
    assert got == IT_NEW and [list(s) for s in got["slides"]] == [list(s) for s in IT_NEW["slides"]], got
    assert itachi_submit._legacy_spec(IT_NEW) == IT_NEW
    assert itachi_submit._legacy_spec({"slides": [{"cach": "TAI_CHO", "mode": "deck"}]}) == {"slides": [{"mode": "deck"}]}
    assert itachi_submit._legacy_spec({"slides": [{"cach": "TAI_CHO"}]}) == {"slides": [{"mode": "in_place"}]}
    assert itachi_submit._legacy_spec({"slides": "x"}) == {"slides": "x"}


def test_itachi_submit_old_and_new_spec_same_output():
    with tempfile.TemporaryDirectory() as t:
        state = Path(t)
        seen = {}
        for tag, good, bad in (("old", IT_OLD, IT_BAD_OLD), ("new", IT_NEW, IT_BAD_NEW)):
            wd = _itachi_workdir(state, good)
            for f in list(wd.glob(f"{sp.GIN_RESULT_PREFIX}*.png")) + list(wd.glob("deck*")):
                f.unlink()
            (wd / sp.SUBMIT_COUNT_FILE).unlink(missing_ok=True)
            r = _run_submit("itachi_submit.py", "338", state)
            pngs = {f.name: _pixels(f) for f in sorted(wd.glob(f"{sp.GIN_RESULT_PREFIX}*.png"))}
            deck_spec = (wd / "deck.spec.json").read_text(encoding="utf-8")
            (wd / "spec.json").write_text(json.dumps(bad, ensure_ascii=False), encoding="utf-8")
            (wd / sp.SUBMIT_COUNT_FILE).unlink(missing_ok=True)
            rb = _run_submit("itachi_submit.py", "338", state)
            seen[tag] = (r.returncode, r.stdout, pngs, deck_spec, rb.returncode, rb.stdout)
        assert seen["old"] == seen["new"]
        code, _out, pngs, deck_spec, bad_code, bad_out = seen["new"]
        assert code == 0 and len(pngs) == 4, (code, _out)
        slides = json.loads(deck_spec)["slides"]
        assert [list(s) for s in slides] == [["layout", "tiers", "annotation", "bg_image"],
                                            ["layout", "badge", "serif", "sans", "sub", "labels", "footer"],
                                            ["layout", "heading", "bg", "subs"]], slides
        assert slides[0]["annotation"] == {"text": "ghi chú tay nè", "tilt": -6, "x": 600}
        assert slides[2]["subs"][0]["col"] == "black"
        assert bad_code == 1
        assert [ln for ln in bad_out.splitlines() if ln.startswith("[LOI]")] == GOLDEN_IT_BAD, bad_out


def test_deck_legacy_slide_same_render():
    """Old deck names normalise to the new ones, and the renderers really read the new ones
    (dropping the renamed field changes the picture; `black` is INK, not the white fallback)."""
    import deck
    cover_old = {"layout": "cover", "bg_anh": None, "tiers": TIERS, "ghi_chu": {"text": "ghi chú tay", "nghieng": 8, "x": 500}}
    cover = {"layout": "cover", "bg_image": None, "tiers": TIERS, "annotation": {"text": "ghi chú tay", "tilt": 8, "x": 500}}
    grid_old = {"layout": "grid3", "serif": "Chữ", "sans": "Đậm", "nhan": [{"text": "Nhãn", "x": 300, "y": 900}]}
    grid = {"layout": "grid3", "serif": "Chữ", "sans": "Đậm", "labels": [{"text": "Nhãn", "x": 300, "y": 900}]}
    stmt_old = {"layout": "statement", "heading": "Câu", "subs": [{"text": "đen", "col": "den"}, {"text": "trắng"}]}
    stmt = {"layout": "statement", "heading": "Câu", "subs": [{"text": "đen", "col": "black"}, {"text": "trắng"}]}
    for old, new in ((cover_old, cover), (grid_old, grid), (stmt_old, stmt)):
        assert deck.legacy_slide(old) == new and deck.legacy_slide(new) == new, deck.legacy_slide(old)
        assert deck._gate([deck.legacy_slide(old)], False) == deck._gate([new], False)
    assert deck.legacy_slide({"nhan": [1], "labels": [2]}) == {"labels": [2]}
    assert deck.legacy_slide("x") == "x"

    def png(s):
        return deck.LAYOUTS[s["layout"]](s).tobytes()
    assert png(cover) != png({**cover, "annotation": {**cover["annotation"], "tilt": 0}})
    assert png(grid) != png({**grid, "labels": []})
    assert png(stmt) != png({**stmt, "subs": [{"text": "đen", "col": "white"}, {"text": "trắng"}]})
    no_marks = "Nhan hieu cua chung toi rat dep va khong co dau"
    assert deck._gate([{"layout": "grid3", "labels": [{"text": no_marks, "x": 1, "y": 1}]}], False), "gate must read labels"
    assert deck._gate([{"layout": "cover", "annotation": {"text": no_marks}}], False), "gate must read annotation"


# ------------------------------------------------------------------ migration
OLD_REGION = {"box": [[1, 2], [3, 2], [3, 4], [1, 4]], "x": 1, "y": 2, "w": 2, "h": 2, "text": "HI", "conf": 0.9,
              "color_rgb": W250, "nen": "phang", "std_nen": 0.0, "nen_rgb": [8, 8, 8], "cao_net": 12, "muc": 0.3,
              "adv": 0.8, "font": "bold", "can": "left", "stt": 1}
NEW_REGION = {"box": [[1, 2], [3, 2], [3, 4], [1, 4]], "x": 1, "y": 2, "w": 2, "h": 2, "text": "HI", "conf": 0.9,
              "color_rgb": W250, "background_kind": "flat", "background_std": 0.0, "background_rgb": [8, 8, 8],
              "ink_height": 12, "ink_ratio": 0.3, "adv": 0.8, "font": "bold", "align": "left", "number": 1}
OLD_OCR = {"anh": "/in/03.jpg", "id": "03", "w": 10, "h": 10,
           "vung": [OLD_REGION, {**OLD_REGION, "nen": "anh", "stt": 2, "hep": 1}]}
NEW_OCR = {"image_path": "/in/03.jpg", "id": "03", "w": 10, "h": 10,
           "regions": [NEW_REGION, {**NEW_REGION, "background_kind": "photo", "number": 2, "hep": 1}]}
OLD_REGIONS_JSON = [{"stt": 2, "x": 1, "y": 2, "w": 3, "h": 4, "color_rgb": W250, "ocr_text": "HI", "conf": 0.9}]
NEW_REGIONS_JSON = [{"number": 2, "x": 1, "y": 2, "w": 3, "h": 4, "color_rgb": W250, "ocr_text": "HI", "conf": 0.9}]
OLD_MANIFEST = {"khoa": "03", "slides": [{"id": "03", "anh": "/in/03.jpg", "w": 10, "h": 10, "nen_sach": "/cb.png",
                                         "vung": OLD_REGIONS_JSON, "so_vung_ocr": 2}]}
NEW_MANIFEST = {"set_id": "03", "slides": [{"id": "03", "image_path": "/in/03.jpg", "w": 10, "h": 10,
                                           "clean_background_path": "/cb.png", "regions": NEW_REGIONS_JSON,
                                           "ocr_region_count": 2}]}


def _write(p: Path, v) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, indent=1), encoding="utf-8")


def _migration_layout(tmp: Path, extra=None) -> dict:
    st = tmp / "state"
    blog, single = sp.prepare_root(st / "blog"), sp.prepare_root(st)
    files = {
        "ocr": blog / "gin_03" / sp.GIN_REGIONS_OCR_FILE, "regions": blog / "gin_03" / sp.GIN_REGIONS_FILE,
        "gin_spec": blog / "gin_03" / "spec.json", "manifest": blog / "itachi_03" / sp.MANIFEST_FILE,
        "it_spec": blog / "itachi_03" / "spec.json", "ocr_single": single / "gin_646" / sp.GIN_REGIONS_OCR_FILE,
        "ocr_done": blog / "gin_07" / sp.GIN_REGIONS_OCR_FILE, "gin_spec_broken": blog / "gin_07" / "spec.json",
        "deck_spec": blog / "itachi_03" / "deck.spec.json", "other": blog / "d1-carousel" / "spec.json",
    }
    data = {"ocr": OLD_OCR, "regions": OLD_REGIONS_JSON, "gin_spec": GIN_OLD["A"], "manifest": OLD_MANIFEST,
            "it_spec": IT_OLD, "ocr_single": OLD_OCR, "ocr_done": NEW_OCR, "gin_spec_broken": '{"gop": [',
            "deck_spec": {"slides": [{"layout": "cover", "ghi_chu": {"nghieng": 1}}]}, "other": {"vung": 1}}
    data.update(extra or {})
    for k, p in files.items():
        _write(p, data[k])
    return files


def _migrate(tmp: Path, *extra):
    return subprocess.run([sys.executable, str(ROOT / "migrate_gin_itachi_stores.py"), "--state", str(tmp / "state"),
                           *extra], capture_output=True, text=True, cwd=ROOT)


def _bytes(files: dict) -> dict:
    return {k: p.read_bytes() for k, p in files.items()}


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def test_migration_dry_run_writes_nothing():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _migration_layout(tmp)
        before = _bytes(f)
        r = _migrate(tmp, "--dry-run")
        assert r.returncode == 0, r.stderr
        assert "DRY RUN — 6 file(s)" in r.stdout, r.stdout
        assert _bytes(f) == before
        assert not list(tmp.glob("low247_*"))


def test_migration_renames_every_store_and_rerun_is_noop():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _migration_layout(tmp)
        before = _bytes(f)
        r = _migrate(tmp)
        assert r.returncode == 0, r.stdout + r.stderr
        assert _load(f["ocr"]) == NEW_OCR and _load(f["ocr_single"]) == NEW_OCR
        assert list(_load(f["ocr"])["regions"][0]) == list(NEW_REGION), "key order kept"
        assert _load(f["regions"]) == NEW_REGIONS_JSON
        assert _load(f["manifest"]) == NEW_MANIFEST
        assert _load(f["gin_spec"]) == GIN_NEW["A"]
        assert _load(f["it_spec"]) == IT_NEW
        for k in ("ocr_done", "gin_spec_broken", "deck_spec", "other"):
            assert f[k].read_bytes() == before[k], k
        assert "not valid JSON" in r.stdout
        backups = list(tmp.glob("low247_gin_itachi_stores_backup_*.tar.gz"))
        journals = list(tmp.glob("low247_gin_itachi_stores_*.journal.jsonl"))
        assert len(backups) == 1 and len(journals) == 1
        with tarfile.open(backups[0]) as tar:
            names = sorted(tar.getnames())
            assert len(names) == 6, names
            assert tar.extractfile("state/blog/prepare/itachi_03/manifest.json").read() == before["manifest"]
        rows = [json.loads(ln) for ln in journals[0].read_text(encoding="utf-8").splitlines()]
        assert {row["kind"] for row in rows} == {"regions_ocr", "regions_json", "gin_spec", "itachi_manifest",
                                                 "itachi_spec"}
        assert any("regions[1].hep" in row["kept_unknown_keys"] for row in rows), rows
        after = _bytes(f)
        r2 = _migrate(tmp)
        assert r2.returncode == 0 and "nothing to do" in r2.stdout, r2.stdout + r2.stderr
        assert _bytes(f) == after


def test_migrated_stores_read_back_through_submit_scripts():
    """Old stores + old specs, migrated, then submitted: same card/pixels as fresh new-name stores."""
    import gin_submit
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        state = tmp / "state"
        wd = _gin_workdir(state)
        fresh = gin_submit._box_translate(_load(wd / sp.GIN_REGIONS_OCR_FILE), GIN_NEW["B"])
        old_ocr = {"anh": str(wd / "src.png"), "id": "777", "w": 640, "h": 480,
                   "vung": [{{"background_kind": "nen", "background_std": "std_nen", "background_rgb": "nen_rgb",
                              "ink_height": "cao_net", "ink_ratio": "muc", "align": "can", "number": "stt"}.get(k, k):
                             ({"flat": "phang", "photo": "anh"}[v] if k == "background_kind" else v)
                             for k, v in r.items()} for r in REGIONS]}
        _write(wd / sp.GIN_REGIONS_OCR_FILE, old_ocr)
        _write(wd / "spec.json", GIN_OLD["B"])
        r = _migrate(tmp)
        assert r.returncode == 0, r.stdout + r.stderr
        d = _load(wd / sp.GIN_REGIONS_OCR_FILE)
        assert d["regions"] == REGIONS
        assert gin_submit._box_translate(d, _load(wd / "spec.json")) == fresh
        res = _run_submit("gin_submit.py", "777", state)
        assert res.returncode == 0, res.stdout + res.stderr


def test_migration_refuses_unknown_shape():
    for bad in ({"ocr": {**OLD_OCR, "regions": []}},
                {"ocr": {**OLD_OCR, "vung": [{**OLD_REGION, "nen": "xam"}]}},
                {"ocr": {**OLD_OCR, "vung": "x"}},
                {"regions": {"stt": 1}},
                {"gin_spec": {"gop": [], "merges": []}},
                {"gin_spec": ["x"]},
                {"manifest": {**OLD_MANIFEST, "slides": [{"vung": [], "regions": []}]}},
                {"it_spec": {"slides": [{"bg_anh": True, "use_clean_background": False}]}},
                {"it_spec": {"slides": ["x"]}},
                {"it_spec": {"slides": [{"ghi_chu": {"nghieng": 1, "tilt": 2}}]}}):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            f = _migration_layout(tmp, bad)
            before = _bytes(f)
            r = _migrate(tmp)
            assert r.returncode == 1, (bad, r.stdout, r.stderr)
            assert "nothing written" in r.stderr, r.stderr
            assert _bytes(f) == before, bad
            assert not list(tmp.glob("low247_*"))


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
