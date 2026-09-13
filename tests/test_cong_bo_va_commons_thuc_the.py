#!/usr/bin/env python3
"""LOW-34 + LOW-35 (12/09/2026): trang cong bo chinh chu phai duoc hoi, va Commons
phai khop THUC THE (cum ten lien nhau), khong khop chu roi.

LOW-34: <title> HF "deepseek-ai/DeepSeek-V4.1-Flash · Hugging Face" -> tach_model
ra ['deepseek'] (tien to repo) -> _khoa_model rong -> trang_cong_bo tra None IM
LANG -> deepseek.com/en/news/deepseek-v4-1-flash/ (4 chart) khong bao gio duoc hoi.
LOW-35: "Hugging Face" (tu hau to site) thanh hang trong tin + tu khoa Commons ->
"Octopus' Hugging Face.jpg", "West Lighthouse, Rathlin hugging the cliff face".
Fail tren code cu, pass tren code moi.

Chay:  venv/bin/python tests/test_cong_bo_va_commons_thuc_the.py
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
from chuan_bi import source as cbn, fallback_rounds                   # noqa: E402

EN = "deepseek-ai/DeepSeek-V4.1-Flash · Hugging Face"
VI = "DeepSeek-V4.1-Flash thả trọng số: trending 1657, 75.774 lượt tải"


def _pg(*ten):
    return {str(i): {"title": "File:" + t, "imageinfo": [{"width": 2000, "height": 1400,
                                                            "mime": "image/jpeg", "url": "u" + str(i)}]}
            for i, t in enumerate(ten)}


# ---------------------------------------------------------------- LOW-34
def test_tach_model_bo_tien_to_repo_hf():
    assert ranking.extract_model(EN)[0] == "DeepSeek-V4.1-Flash", ranking.extract_model(EN)
    assert th._lock_model(ranking.extract_model(EN))[0] == "deepseek-v4-1-flash"


def test_them_trang_cong_bo_hoi_voi_ten_dai_nhat_va_khong_co_hugging_face():
    goi = {}
    cu = th.announcement_page
    th.announcement_page = lambda hang, models: goi.update(hang=hang, models=models) or None
    try:
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "source.json"
            ng = {"tieu_de_en": EN, "trang": [{"url": "https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash"}]}
            p.write_text(json.dumps(ng), encoding="utf-8")
            with redirect_stderr(io.StringIO()):
                fallback_rounds._extra_announcement_page(ng, p, ng["trang"], VI, "")
    finally:
        th.announcement_page = cu
    assert goi.get("models") and goi["models"][0] == "DeepSeek-V4.1-Flash", goi
    assert goi["hang"]["khoa"] == "deepseek", goi


def test_trang_cong_bo_khong_im_khi_khong_co_khoa():
    err = io.StringIO()
    with redirect_stderr(err):
        assert th.announcement_page({"khoa": "deepseek", "hang": "DeepSeek"}, ["deepseek"]) is None
    assert "[cong bo]" in err.getvalue() and "khong ra khoa" in err.getvalue(), err.getvalue()


# ---------------------------------------------------------------- LOW-35
def test_commons_hugging_face_phai_la_cum_lien_nhau():
    pages = _pg("West Lighthouse, Rathlin hugging the cliff face 01.jpg",
                "Hugging Face headquarters Paris 2025.jpg",
                "Face hugging octopus.jpg")
    assert [c["alt"] for c in th.filter_commons(pages, "Hugging Face")] == \
        ["Commons: Hugging Face headquarters Paris 2025.jpg"]


def test_co_cum_ten_mot_tu_nhu_cu():
    assert th._has_phrase(["samsung"], "samsung town seoul.jpg")
    assert not th._has_phrase(["arm"], "harmony hall.jpg")
    assert th._has_phrase(["thinking", "machines"], "thinking machines lab office.jpg")
    assert not th._has_phrase(["thinking", "machines"], "machines for thinking.jpg")


def test_ten_rieng_dau_khong_lay_hau_to_site():
    assert cbn._leading_proper_noun(EN) == "", cbn._leading_proper_noun(EN)
    assert cbn._leading_proper_noun("Gimlet Labs raises 40M | TechCrunch") == "Gimlet Labs"


def test_hang_trong_tin_khong_co_hugging_face_sau_khi_bo_hau_to():
    import article_sources
    hangs = th.vendors_in_story(f"{VI} {article_sources.strip_site_suffix(EN)}")
    assert [h["khoa"] for h in hangs] == ["deepseek"], hangs


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
