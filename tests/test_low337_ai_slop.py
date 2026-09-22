#!/usr/bin/env python3
"""LOW-337 (22/09/2026): ảnh AI slop không được lên slide.

Ông Chủ, carousel Kite "Grok 4.7" slide 04/07: *"sao mọc đâu ra cái hình AI slop
vô duyên vậy?"*. Tấm "xAI 4.7 vs DeepSeek R1" là ảnh đầu bài của wccftech, do
model sinh ảnh tạo (1376x768, cỡ 16:9 của Gemini 3 Pro Image). Nó qua hết cổng:
bảng cỡ `HAS_AI_GENERATE` chỉ có cỡ đời cũ, còn câu vision chỉ hỏi "đúng chủ đề
không". Kite dựng cả slide quanh nó, tít lấy chữ "R1" vẽ trên ảnh — tư liệu chỉ
có DeepSeek V4.1 Flash.

Mỗi phần có ví dụ SAI-PHẢI-CHẶN đi kèm ĐÚNG-PHẢI-QUA:
  1. cỡ ảnh Gemini mới nằm trong `HAS_AI_GENERATE`, cỡ ảnh chụp thường thì không;
  2. vision hỏi dòng `AI slop: yes | no` và đọc ra được;
  3. `classify`: ảnh AI slop mất hết `uses`, kể cả khi LOW-219 (chủ thể có tên) muốn
     hồi sinh; ảnh thật / đồ hoạ @arena / thẻ logo thì giữ.

Chạy:  venv/bin/python tests/test_low337_ai_slop.py
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw  # noqa: E402

import article_images  # noqa: E402
import image_rules_ethan  # noqa: E402
import prepare.vision as vision  # noqa: E402


class _Resp:
    def __init__(self, txt: str):
        self._b = json.dumps({"choices": [{"message": {"content": txt}}]}).encode()

    def read(self):
        return self._b


def _image_temp(tmp, w=1000, h=1250):
    im = Image.new("RGB", (w, h), (30, 30, 40))
    d = ImageDraw.Draw(im)
    for x in range(0, w, 37):
        for y in range(0, h, 41):
            d.rectangle([x, y, x + 12, y + 14], fill=(90 + x % 120, 60, 80 + y % 150))
    p = Path(tmp) / "a.png"
    im.save(p)
    return p


# ---------------------------------------------------------------- 1. co anh
def test_gemini_new_sizes_are_ai_sizes():
    for co in [(1376, 768), (768, 1376), (1264, 848), (1584, 672), (2752, 1536)]:
        assert co in article_images.HAS_AI_GENERATE, co


def test_common_photo_sizes_not_flagged():
    for co in [(1200, 800), (1600, 900), (1920, 1080), (1440, 926), (1200, 675)]:
        assert co not in article_images.HAS_AI_GENERATE, co


# ---------------------------------------------------------------- 2. vision
def _ask_vision(tra_loi, **k):
    gui = {}

    def _goi(req, _ngu=None):
        gui["hoi"] = json.loads(req.data)["messages"][0]["content"][0]["text"]
        return _Resp(tra_loi)

    kq = {}
    with tempfile.TemporaryDirectory() as t, \
            mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}), \
            mock.patch.object(vision, "_call_router", side_effect=_goi):
        ra = vision.description_image(str(_image_temp(t)), "xAI tung Grok 4.7", ket_qua=kq, **k)
    return ra, kq, gui.get("hoi", "")


def test_vision_asks_ai_slop_line_in_english():
    _ra, kq, hoi = _ask_vision("MO_TA: đồ hoạ xAI 4.7 vs DeepSeek R1.\nLIEN_QUAN: co\nAI slop: yes")
    assert "AI slop: yes | no" in hoi and "DUNG 8 dong" in hoi, hoi
    assert kq["ai_slop"] is True, kq


def test_vision_ai_slop_no_and_missing():
    _ra, kq, _h = _ask_vision("MO_TA: biểu đồ CursorBench của x.ai.\nLIEN_QUAN: co\nAI slop: no")
    assert kq["ai_slop"] is False, kq
    _ra, kq, _h = _ask_vision("MO_TA: ảnh.\nLIEN_QUAN: co")
    assert kq["ai_slop"] is None, kq                      # khong doc ra thi khong doan


def test_parse_ai_slop_variants():
    assert vision.parse_ai_slop("AI_SLOP: Yes") is True
    assert vision.parse_ai_slop("ai slop : no") is False
    assert vision.parse_ai_slop("MO_TA: slop") is None


# ---------------------------------------------------------------- 3. classify
def _classify(a_them: dict, ai_slop, relevant=True):
    def _gia(path, tieu_de, hang="", **k):
        k["ket_qua"]["ai_slop"] = ai_slop
        return ("Đồ họa so sánh mô hình xAI 4.7 và DeepSeek R1.", relevant)

    with tempfile.TemporaryDirectory() as t:
        a = {"id": "A2", "original_path": str(_image_temp(t)), **a_them}
        with mock.patch.object(vision, "description_image", side_effect=_gia), \
                mock.patch.object(image_rules_ethan, "count_faces", return_value=0):
            vision.classify(a, Path(t), "xAI tung Grok 4.7")
    return a


def test_classify_ai_slop_dropped():
    a = _classify({"source": "other_outlet"}, ai_slop=True)
    assert a["uses"] == [] and a["relevant"] is False, a
    assert "AI SLOP" in a["notes"][0], a["notes"]


def test_classify_ai_slop_not_revived_by_named_subject():
    with mock.patch.object(vision, "relevant_by_named_subject", return_value="named_subject"):
        a = _classify({"source": "other_outlet"}, ai_slop=True, relevant=False)
    assert a["uses"] == [] and a["relevant"] is False, a


def test_classify_real_image_kept():
    a = _classify({"source": "other_outlet"}, ai_slop=False)
    assert a["uses"] and a["relevant"] is True, a
    a = _classify({"source": "other_outlet"}, ai_slop=None)   # vision khong tra dong -> fail-open
    assert a["uses"] and a["relevant"] is True, a


def test_classify_official_sources_exempt():
    for them in ({"source": "ranking", "ranking": {"kind": "chart"}}, {"source": "brand"},
                 {"source": "other_outlet", "graphic_allowed": True}):
        a = _classify(them, ai_slop=True)
        assert a["relevant"] is True and a["uses"], (them, a)


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
