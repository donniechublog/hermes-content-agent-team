#!/usr/bin/env python3
"""LOW-363: ảnh phải khớp PHIÊN BẢN model của tin — không bao giờ xét tuổi ảnh.

Draft thật `google-xac-nhan-cac-mo-hinh-gemini-da-dre-donniechublog` (22/09/2026): tin
"Google confirms Gemini models hacked three companies in May 2026" ra slide bảng benchmark
Gemini 1.0/1.5 (A40–A43) vì Dre tự tìm "Gemini 1.5 Pro benchmark".
"""
import sys
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import model_version as mv                  # noqa: E402

TITLE = "Google confirms Gemini models hacked three companies in May 2026"
GEMINI_TIMELINE = [("1.0", date(2023, 12, 13)), ("1.5", date(2024, 2, 15)), ("2.5", date(2025, 3, 25)),
                   ("3", date(2025, 11, 18)), ("3.5", date(2026, 5, 19)), ("3.8", date(2026, 9, 2))]


def _tl(fam):
    return GEMINI_TIMELINE if fam == "gemini" else []


def test_versions_in_text():
    v = mv.versions_in_text
    assert v("Gemini 1.5 Pro benchmark") == {"gemini": {"1.5"}}
    assert v("Claude Opus 4.7 high") == {"claude": {"4.7"}} and v("Claude 3.5 Sonnet") == {"claude": {"3.5"}}
    assert v("GPT-5.5 Pro") == {"gpt": {"5.5"}} and v("gpt-4o mini") == {"gpt": {"4"}}
    assert v("Qwen3.8 Max") == {"qwen": {"3.8"}} and v("DeepSeek-V4.1-Flash") == {"deepseek": {"4.1"}}
    assert v("Google Gemini interface") == {} and v("Gemini 2026 roadmap") == {}   # nam khong phai phien ban


def test_story_date_from_title_or_fallback():
    assert mv.story_date(TITLE) == date(2026, 5, 31)
    assert mv.story_date("Google xác nhận Gemini xâm nhập hồi tháng 5/2026") == date(2026, 5, 31)
    assert mv.story_date("Gemini ra mắt", fallback_ts=1790049454).year == 2026


def test_parse_version_table_formats():
    wt = """{| class="wikitable sortable"
! Version
! Release date
|-
| 1.5 Pro
| {{date|2024-02-15}}
|-
|3 Pro
|{{date|2025-11-18}}
|}
{| class="wikitable plainrowheaders"
|-
! scope="row" | 1.5
| {{dts|2024-5}}
|-
|[[GPT-4]]
|{{dts|2023-3-14}}
|}"""
    rows = mv.parse_version_table(wt)
    assert ("1.5", date(2024, 2, 15)) in rows and ("3", date(2025, 11, 18)) in rows, rows
    assert ("1.5", date(2024, 5, 1)) in rows and ("4", date(2023, 3, 14)) in rows, rows


def test_reference_newest_before_story_date_not_later():
    ref = mv.reference_versions(TITLE, "", mv.story_date(TITLE), timeline=_tl)
    assert ref == {"gemini": {"versions": ["3.5"], "source": "wikipedia", "date": "2026-05-19"}}, ref
    # 3.8 (ra 9/2026) SAU ngay cua tin -> khong phai tham chieu


def test_reference_from_article_when_version_named():
    ref = mv.reference_versions("Gemini 3.1 Pro leads the board", "", date(2026, 9, 1), timeline=_tl)
    assert ref["gemini"]["versions"] == ["3.1"] and ref["gemini"]["source"] == "article"


def test_image_gate_blocks_draft_a40_a43_keeps_current_and_plain():
    ref = mv.reference_versions(TITLE, "", mv.story_date(TITLE), timeline=_tl)
    imgs = [
        {"id": "A40", "uses": ["body"], "relevant": True, "description": "Bảng so sánh kết quả các phiên bản mô hình Gemini",
         "printed_version": "Gemini 1.0 Pro, Gemini 1.0 Ultra, Gemini 1.5 Pro"},
        {"id": "A41", "uses": ["body"], "relevant": True, "description": "Bảng benchmark các phiên bản Google Gemini",
         "url": "https://dataconomy.com/wp-content/uploads/2024/08/Gemini-1.5-Pro-2.jpg"},
        {"id": "A42", "uses": ["body"], "relevant": True,
         "description": "Bảng so sánh kết quả kiểm chuẩn năng lực các phiên bản mô hình Gemini 1.5."},
        {"id": "A43", "uses": ["body"], "relevant": True, "description": "Bảng so sánh điểm chuẩn Google Gemini",
         "printed_version": "Gemini 1.5 Pro, Gemini 1.0 Ultra"},
        {"id": "A13", "uses": ["cover"], "relevant": True, "description": "Logo ngôi sao và chữ Gemini trên nền sáng"},
        {"id": "A39", "uses": ["body"], "relevant": True, "description": "Biểu trưng mô hình AI Gemini 3.1 Pro trên nền đen"},
        {"id": "A17", "uses": ["body"], "relevant": True, "description": "Chân dung Sergey Brin", "url": "https://x/2014/brin.jpg"},
        # slug URL mat dau cham: "gemini-35-p" = Gemini 3.5 Pro (dung phien ban) -> KHONG chan
        {"id": "A37", "uses": ["body"], "relevant": True, "description": "Điện thoại hiển thị chữ Google Gemini",
         "url": "https://etimg.etb2bimg.com/thumb/msid-132549333/internet/google-delays-launch-of-gemini-35-p"},
        # anh ro ri "Gemini 4 Pro" (9/2026) khong phai phien ban cua tin 5/2026 -> chan
        {"id": "A24", "uses": ["body"], "relevant": True, "description": "Giao diện Gemini 4 Pro trên màn hình",
         "url": "https://nokiapoweruser.com/wp-content/uploads/2026/09/gemini-4-pro.jpeg"},
    ]
    assert mv.apply_image_gate(imgs, ref) == 5
    by = {a["id"]: a for a in imgs}
    for k in ("A40", "A41", "A42", "A43"):
        assert by[k]["relevant"] is False and by[k]["uses"] == [] and "gemini 1" in by[k]["version_mismatch"], by[k]
    assert by["A24"]["relevant"] is False and by["A24"]["version_mismatch"] == "gemini 4", by["A24"]
    for k in ("A13", "A39", "A17", "A37"):     # logo tron, cung the he (3.1 ~ 3.5), anh cu, slug mo ho
        assert by[k]["relevant"] is True and "version_mismatch" not in by[k], by[k]


def test_find_more_refuses_other_version_query():
    import find_more_images as fm
    ref = {"gemini": {"versions": ["3.5"], "source": "wikipedia", "date": "2026-05-19"}}
    loi = fm.version_query_errors(["Gemini 1.5 Pro benchmark", "Google Gemini interface", "Gemini 3 Pro launch"], ref)
    assert len(loi) == 1 and "Gemini 1.5 Pro benchmark" in loi[0] and "gemini 3.5" in loi[0], loi


def test_brief_names_reference_version():
    import brief_common
    m = {"title": "t", "link": "l", "model_versions": {"gemini": {"versions": ["3.5"], "source": "wikipedia",
                                                                "date": "2026-05-19"}}}
    L = brief_common.mark(m, "DRE", "x")
    assert any("Phiên bản model của tin: gemini 3.5 (Wikipedia, ra 2026-05-19)" in x for x in L), L


def test_vision_parses_printed_version():
    from prepare import vision
    assert vision.parse_printed_version("MO_TA: bang\nPHIEN_BAN: Gemini 1.5 Pro, Gemini 1.0 Ultra") \
        == "Gemini 1.5 Pro, Gemini 1.0 Ultra"
    assert vision.parse_printed_version("PHIÊN_BẢN: không") is None


def test_version_gate_in_manifest_uses_timeline():
    from prepare import manifest
    saved = mv.release_timeline
    mv.release_timeline = _tl
    try:
        imgs = [{"id": "A42", "uses": ["body"], "relevant": True, "description": "Bảng Gemini 1.5 Pro"}]
        ref = manifest.version_gate(imgs, TITLE)
        assert ref["gemini"]["versions"] == ["3.5"] and imgs[0]["relevant"] is False
        # find_more: dung lai tham chieu da ghi, khong tinh lai
        imgs2 = [{"id": "A50", "uses": ["body"], "relevant": True, "description": "Gemini 1.0 Ultra chart"}]
        assert manifest.version_gate(imgs2, "x", ref=ref) == ref and imgs2[0]["relevant"] is False
    finally:
        mv.release_timeline = saved


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
