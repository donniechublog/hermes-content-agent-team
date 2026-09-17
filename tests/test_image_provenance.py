#!/usr/bin/env python3
"""image_provenance.py (LOW-237): PNG metadata in English, readers accept BOTH names.

PNGs already on the server (~9 GB, md5 recorded) keep their Vietnamese metadata forever
(`nguon_dung=chup_xep_hang`, `crop_ti_le=goc=WxH;ti_le=..;cat_ngang=1`, `hinh`, `trang_pdf`).
So: every reader gives the SAME answer on an old PNG and on its new-named twin; writers use
only the new names; `_save_crop` translates old keys while copying and never carries an old
crop trace next to the new one; the legacy tables equal the approved table.

Chạy:  venv/bin/python tests/test_image_provenance.py
"""
import ast
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

from PIL import Image                                         # noqa: E402
from PIL.PngImagePlugin import PngInfo                        # noqa: E402

import image_provenance as ip                                 # noqa: E402

TABLE = json.loads((ROOT / "docs" / "tu_dien_ten" / "image_search_keys_v2.json").read_text(encoding="utf-8"))

# (old metadata, new metadata) — same meaning, spelled before/after LOW-237
PAIRS = [
    ({"nguon_dung": "chup_xep_hang", "model": "GPT-5.2"}, {"provenance": "ranking_capture", "model": "GPT-5.2"}),
    ({"nguon_dung": "the_xep_hang", "rank": "3"}, {"provenance": "ranking_card", "rank": "3"}),
    ({"nguon_dung": "ghep_doc"}, {"provenance": "vertical_stack"}),
    ({"nguon_dung": "arxiv_hinh", "hinh": "figure 1", "trang_pdf": "2"},
     {"provenance": "arxiv_figure", "figure": "figure 1", "pdf_page": "2"}),
    ({"crop_ti_le": "goc=2400x1200;ti_le=4:5;cx=0.5;cy=0.4;cat_ngang=1"},
     {"crop_trace": "original=2400x1200;ratio=4:5;cx=0.5;cy=0.4;landscape_crop=1"}),
    ({"crop_ti_le": "goc=1600x900;ti_le=1:1;cx=0.5;cy=0.5;cat_ngang=0", "nguon_dung": "chup_chart"},
     {"crop_trace": "original=1600x900;ratio=1:1;cx=0.5;cy=0.5;landscape_crop=0", "provenance": "chart_capture"}),
    # crop trace written before the landscape flag existed
    ({"crop_ti_le": "goc=1000x800;ti_le=4:5;cx=0.5;cy=0.5"}, {"crop_trace": "original=1000x800;ratio=4:5;cx=0.5;cy=0.5"}),
    ({"nguon_dung": "dre_chuan_bi"}, {"provenance": "engine_download"}),
    ({}, {}),
]


def _png(path: Path, text: dict, size=(64, 48)) -> Path:
    meta = PngInfo()
    for k, v in text.items():
        meta.add_text(k, v)
    Image.new("RGB", size, (10, 20, 30)).save(path, "PNG", pnginfo=meta)
    return path


def _answers(img) -> tuple:
    import image_rules_dre
    t = ip.read_text(img)
    return (ip.read_crop_trace(img), ip.allows_landscape_crop(img), ip.is_ranking_image(img),
            ip.is_stacked_composite(img), ip.provenance(img), t.get(ip.FIGURE_KEY), t.get(ip.PDF_PAGE_KEY),
            image_rules_dre.read_crop_trace(img))


def test_readers_same_answer_on_old_and_new_metadata():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        for i, (old, new) in enumerate(PAIRS):
            with Image.open(_png(d / f"old{i}.png", old)) as a, Image.open(_png(d / f"new{i}.png", new)) as b:
                assert _answers(a) == _answers(b), (old, new, _answers(a), _answers(b))
                assert ip.read_text(a) == ip.read_text(b) == dict(b.text), (ip.read_text(a), b.text)


def test_readers_meaning_not_just_equal():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        for text in PAIRS[0]:
            with Image.open(_png(d / "x.png", text)) as im:
                assert ip.is_ranking_image(im) and not ip.is_stacked_composite(im)
        for text in PAIRS[2]:
            with Image.open(_png(d / "x.png", text)) as im:
                assert ip.is_stacked_composite(im) and not ip.is_ranking_image(im)
        for text in PAIRS[4]:
            with Image.open(_png(d / "x.png", text)) as im:
                assert ip.read_crop_trace(im) == (2400, 1200) and ip.allows_landscape_crop(im)
        for text in PAIRS[5] + PAIRS[6]:
            with Image.open(_png(d / "x.png", text)) as im:
                assert ip.read_crop_trace(im) and not ip.allows_landscape_crop(im)
        with Image.open(_png(d / "x.png", {"crop_trace": "garbage"})) as im:
            assert ip.read_crop_trace(im) is None and not ip.allows_landscape_crop(im)


def test_crop_trace_round_trip():
    s = ip.crop_trace_text(2400, 1200, "4:5", 0.5, 0.35, True)
    assert s == "original=2400x1200;ratio=4:5;cx=0.5;cy=0.35;landscape_crop=1", s
    assert ip.parse_crop_trace(s) == {"original": "2400x1200", "ratio": "4:5", "cx": "0.5", "cy": "0.35",
                                      "landscape_crop": "1"}
    old = "goc=2400x1200;ti_le=4:5;cx=0.5;cy=0.35;cat_ngang=1"
    assert ip.parse_crop_trace(old) == ip.parse_crop_trace(s)
    assert ip.crop_trace_text(10, 20, "1:1", 0.5, 0.5, False).endswith("landscape_crop=0")


def test_save_crop_translates_old_keys_and_keeps_one_crop_trace():
    import image_prepare as cb
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        src = _png(d / "src.png", {"nguon_dung": "chup_xep_hang", "model": "GPT-5.2",
                                   "crop_ti_le": "goc=9x9;ti_le=1:1;cx=0.5;cy=0.5;cat_ngang=0"}, size=(1600, 800))
        with Image.open(src) as im:
            cb._save_crop(im, d / "cut.png", "4:5", cy=0.4, cat_ngang=True)
        with Image.open(d / "cut.png") as ra:
            assert dict(ra.text) == {"provenance": "ranking_capture", "model": "GPT-5.2",
                                     "crop_trace": "original=1600x800;ratio=4:5;cx=0.5;cy=0.4;landscape_crop=1"}, ra.text
            assert ip.read_crop_trace(ra) == (1600, 800) and ip.allows_landscape_crop(ra) and ip.is_ranking_image(ra)
        # a second crop of the NEW image replaces its crop trace, never stacks a second one
        with Image.open(d / "cut.png") as im:
            cb._save_crop(im, d / "cut2.png", "1:1")
        with Image.open(d / "cut2.png") as ra:
            assert ra.text["crop_trace"].startswith("original=") and list(ra.text).count("crop_trace") == 1
            assert "crop_ti_le" not in ra.text and "nguon_dung" not in ra.text, ra.text


def test_stamp_writes_new_names_only():
    with tempfile.TemporaryDirectory() as t:
        p = _png(Path(t) / "s.png", {})
        assert ip.stamp_file(p, "arxiv_figure", **{ip.FIGURE_KEY: "figure 2", ip.PDF_PAGE_KEY: 3})
        with Image.open(p) as im:
            assert dict(im.text) == {"provenance": "arxiv_figure", "figure": "figure 2", "pdf_page": "3"}, im.text


def test_legacy_tables_equal_approved_table():
    keys = {k: v for k, v in TABLE["png_metadata_keys"].items() if not k.startswith("_")}
    assert ip.LEGACY_KEYS == keys, (ip.LEGACY_KEYS, keys)
    tokens = {k.rstrip("="): v.rstrip("=") for k, v in TABLE["png_crop_trace_tokens"].items()}
    assert ip.LEGACY_CROP_TOKENS == tokens, (ip.LEGACY_CROP_TOKENS, tokens)
    assert ip.LEGACY_PROVENANCE_VALUES == TABLE["png_provenance_values"]
    assert set(ip.MARK_PNG) == {"crop_trace", "provenance", "crop_ti_le", "nguon_dung"}, ip.MARK_PNG


def _old_literals_in_writer_calls(src: str) -> list:
    """Chuoi cu (khoa/gia tri metadata truoc LOW-237) o doi so cua stamp_provenance/stamp_file/add_text."""
    old = set(ip.LEGACY_KEYS) | set(ip.LEGACY_PROVENANCE_VALUES)
    bad = []
    for n in ast.walk(ast.parse(src)):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        name = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
        args = {"stamp_provenance": n.args[:1], "stamp_file": n.args[1:2], "add_text": n.args[:2]}.get(name, [])
        args = list(args) + ([kw.value for kw in n.keywords] if name in ("stamp_provenance", "stamp_file") else [])
        kw_names = [kw.arg for kw in n.keywords if kw.arg] if name in ("stamp_provenance", "stamp_file") else []
        for a in args:
            if isinstance(a, ast.Constant) and a.value in old:
                bad.append((n.lineno, a.value))
        bad += [(n.lineno, k) for k in kw_names if k in old]
    return bad


def test_production_writers_use_new_names():
    assert _old_literals_in_writer_calls('m.add_text("nguon_dung", "ghep_doc")\n'
                                         'image_provenance.stamp_file(out, "chup_chart")\n'
                                         'stamp_provenance("arxiv_hinh", hinh="figure 1", trang_pdf=2)\n')
    assert not _old_literals_in_writer_calls('print("[arxiv_hinh] khong co")\nstamp_file(out, "chart_capture")\n')
    bad = []
    for p in sorted(ROOT.glob("*.py")) + sorted((ROOT / "prepare").glob("*.py")):
        if p.name == "image_provenance.py":
            continue
        bad += [(p.name, ln, v) for ln, v in _old_literals_in_writer_calls(p.read_text(encoding="utf-8"))]
    assert not bad, f"writer still stamps pre-LOW-237 metadata names: {bad}"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
