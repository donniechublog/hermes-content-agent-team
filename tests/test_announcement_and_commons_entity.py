#!/usr/bin/env python3
"""LOW-34 + LOW-35 (12/09/2026): trang cong bo chinh chu phai duoc hoi, va Commons
phai khop THUC THE (cum ten lien nhau), khong khop chu roi.

LOW-34: <title> HF "deepseek-ai/DeepSeek-V4.1-Flash · Hugging Face" -> extract_model
ra ['deepseek'] (tien to repo) -> _lock_model rong -> announcement_page tra None IM
LANG -> deepseek.com/en/news/deepseek-v4-1-flash/ (4 chart) khong bao gio duoc hoi.
LOW-35: "Hugging Face" (tu hau to site) thanh hang trong tin + tu khoa Commons ->
"Octopus' Hugging Face.jpg", "West Lighthouse, Rathlin hugging the cliff face".
Fail tren code cu, pass tren code moi.

Chay:  venv/bin/python tests/test_announcement_and_commons_entity.py
"""
import io
import json
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import ranking                                              # noqa: E402
import image_brand as th                                 # noqa: E402
from prepare import source as cbn, fallback_rounds                   # noqa: E402

EN = "deepseek-ai/DeepSeek-V4.1-Flash · Hugging Face"
VI = "DeepSeek-V4.1-Flash thả trọng số: trending 1657, 75.774 lượt tải"


def _pg(*ten):
    return {str(i): {"title": "File:" + t, "imageinfo": [{"width": 2000, "height": 1400,
                                                            "mime": "image/jpeg", "url": "u" + str(i)}]}
            for i, t in enumerate(ten)}


# ---------------------------------------------------------------- LOW-34
def test_extract_model_drop_prefix_repo_hf():
    assert ranking.extract_model(EN)[0] == "DeepSeek-V4.1-Flash", ranking.extract_model(EN)
    assert th._lock_model(ranking.extract_model(EN))[0] == "deepseek-v4-1-flash"


def test_extra_announcement_page_ask_with_name_long_most_and_no_has_hugging_face():
    goi = {}
    cu = th.announcement_page
    th.announcement_page = lambda hang, models: goi.update(hang=hang, models=models) or None
    try:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "source.json"
            ng = {"title_en": EN, "pages": [{"url": "https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash"}]}
            p.write_text(json.dumps(ng), encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                fallback_rounds._extra_announcement_page(ng, p, ng["pages"], VI, "")
    finally:
        th.announcement_page = cu
    assert goi.get("models") and goi["models"][0] == "DeepSeek-V4.1-Flash", goi
    assert goi["hang"]["key"] == "deepseek", goi


def test_announcement_page_no_silent_when_no_has_lock():
    err = io.StringIO()
    with redirect_stderr(err):
        assert th.announcement_page({"key": "deepseek", "company": "DeepSeek"}, ["deepseek"]) is None
    assert "[cong bo]" in err.getvalue() and "khong ra khoa" in err.getvalue(), err.getvalue()


# ---------------------------------------------------------------- LOW-35
def test_commons_hugging_face_right_is_phrase_connect_other():
    pages = _pg("West Lighthouse, Rathlin hugging the cliff face 01.jpg",
                "Hugging Face headquarters Paris 2025.jpg",
                "Face hugging octopus.jpg")
    assert [c["alt"] for c in th.filter_commons(pages, "Hugging Face")] == \
        ["Commons: Hugging Face headquarters Paris 2025.jpg"]


def test_has_phrase_name_one_from_like_old():
    assert th._has_phrase(["samsung"], "samsung town seoul.jpg")
    assert not th._has_phrase(["arm"], "harmony hall.jpg")
    assert th._has_phrase(["thinking", "machines"], "thinking machines lab office.jpg")
    assert not th._has_phrase(["thinking", "machines"], "machines for thinking.jpg")


def test_leading_proper_noun_no_take_suffix_site():
    assert cbn._leading_proper_noun(EN) == "", cbn._leading_proper_noun(EN)
    assert cbn._leading_proper_noun("Gimlet Labs raises 40M | TechCrunch") == "Gimlet Labs"


def test_vendors_in_story_no_has_hugging_face_after_when_drop_suffix():
    import article_sources
    hangs = th.vendors_in_story(f"{VI} {article_sources.strip_site_suffix(EN)}")
    assert [h["key"] for h in hangs] == ["deepseek"], hangs


if __name__ == "__main__":
    ok = 0
    ten = [k for k in list(globals()) if k.startswith("test_")]
    for k in ten:
        try:
            globals()[k]()
            ok += 1
        except AssertionError as e:
            print(f"    FAIL {k}: {e}")
    print(f"{Path(__file__).name:<34} {ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
