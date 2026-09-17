#!/usr/bin/env python3
"""Nấc cuối không bao giờ rỗng (`entity_images.py`, LOW-35). Ông Chủ 12/09/2026:
*"ko có lý gì mà ko tìm được ảnh minh hoạ đâu, đây là 2026, mọi thứ bạn cần đều
có sẵn"*. Test offline: mock mạng, khoá (1) tách thực thể, (2) lọc Wikipedia
pageimages theo cỡ, (3) Commons theo CỤM (không lọt hai người khác ghép tên),
(4) nấc chỉ chạy khi các nấc trên còn thiếu.

Chạy:  venv/bin/python tests/test_entity_images.py
"""
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import entity_images as tt  # noqa: E402


def test_extract_entity_phrase_write_ify_and_model():
    r = tt.entity_within_title("Claude is only available to people over 18, Anthropic says",
                                  models=["Claude Opus 5"])
    assert r[0] == "Claude Opus 5", r
    assert "Anthropic" in r, r
    # Tu don khong phai ten hang thi bo — "Claude" mot minh ra tranh Claude
    # Lorrain tren Commons (do that 12/09/2026); "Flash" la tu dien thuong.
    assert "Claude" not in r, r
    assert "Flash" not in tt.entity_within_title("DeepSeek V4.1 Flash tops LiveBench")


def test_pageimages_drop_image_small_and_no_has():
    nho = {"query": {"pages": {"1": {"title": "Paul Erdős", "original": {"source": "u", "width": 324, "height": 430}}}}}
    to = {"query": {"pages": {"1": {"title": "Anthropic", "original": {"source": "https://x/a.jpg", "width": 2865, "height": 2952}}}}}
    trong = {"query": {"pages": {"1": {"title": "DeepSeek"}}}}
    class R:
        def __init__(self, j): self._j = j
        def raise_for_status(self): pass
        def json(self): return self._j
    with mock.patch("httpx.get", side_effect=[R(nho), R(to), R(trong)]):
        assert tt.pageimages("Erdős problems") is None
        c = tt.pageimages("Anthropic")
        assert c and c["score"] == 27 and c["entity"]["article_name"] == "Anthropic"
        assert tt.pageimages("DeepSeek") is None


def test_commons_by_phrase_no_pass_two_person_stack_name():
    def _p(w, h, ten):
        return {"title": f"File:{ten}", "imageinfo": [{"width": w, "height": h, "mime": "image/jpeg",
                                                       "thumburl": f"https://x/{ten}"}]}
    pages = {"1": _p(4000, 2667, "Dario Amodei at TechCrunch Disrupt 2023 01.jpg"),
             "2": _p(4000, 2667, "Dario Rossi meets Luca Amodei in Rome.jpg"),
             "3": _p(1800, 2880, "Dario Amodei in 2023.jpg")}
    import image_brand as th
    with mock.patch.object(th, "_ask_commons", return_value=pages):
        ra = tt.commons_by_phrase("Dario Amodei", so=5)
    ten = [c["alt"] for c in ra]
    assert len(ra) == 2 and all("Rossi" not in t for t in ten), ten
    assert ra[0]["w"] >= ra[0]["h"], "anh ngang phai dung truoc"


def test_tier_only_run_when_remaining_missing():
    src = (ROOT / "image_prepare.py").read_text(encoding="utf-8")
    i_cn, i_tt, i_kn = (src.index("_round_capture_source(anh"), src.index("_round_entity(anh"),
                        src.index("_round_concept(anh"))
    # 1c02bba: thuc the TRUOC khai niem — khai niem (tu khoa LLM) la nac CUOI CUNG
    # vi do tren may chu no la nac duy nhat sinh duong tinh gia.
    assert i_cn < i_tt < i_kn, "thu tu phai: chup nguon -> thuc the -> khai niem"
    assert "has_enough_material(vai_anh, dung_duoc, flagship):\n            anh, dung_duoc, chua_nhin = _round_entity" in src

def test_round_entity_ask_sentence_concept_no_ask_image_of_matter():
    """Đo trên máy chủ 12/09/2026: ảnh Wikipedia của Anthropic bị vision từ chối vì
    nấc hỏi câu mặc định "có phải ảnh của sự việc". Nấc phải gắn `concept`
    trước `classify` để đi câu "có đúng là <thực thể>, hợp bìa"."""
    src = (ROOT / "prepare" / "fallback_rounds.py").read_text(encoding="utf-8")
    i = src.index("def _round_entity")
    than = src[i:i + 3000]
    assert 'a["concept"] = {"keyword": a["entity"]["name"]' in than
    assert than.index('a["concept"] = ') < than.index("classify(a, wd, tieu_de_nhin)")


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
