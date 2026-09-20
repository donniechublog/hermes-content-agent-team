#!/usr/bin/env python3
"""LOW-264 (bổ sung, 20/09/2026): hai lỗi nguồn ảnh brand lộ ra khi đo "live vs thư viện".

(a) Bing News RSS không có tham số ngôn ngữ thì định vị theo IP (máy chủ + Mac đều
    ở Việt Nam) và trả tiêu đề TIẾNG VIỆT cho từ khoá ngắn — đo thật 8 hãng x 85
    mục: 0/85 tiêu đề tiếng Anh; thêm `setlang=en`: 87/87. `has_vietnamese` phía
    sau lọc hết nên `report_about_keyword("Anthropic")` rỗng 0/12, "OpenAI" 0/7.
(b) `material_wikidata` bỏ người không có nhãn `en`: CEO mới của Apple (Q106028933,
    John Ternus, P169 preferred) chỉ có nhãn `mul` nên bị bỏ, chỉ ra Wozniak.

Chạy:  venv/bin/python tests/test_low264_brand_source_bugs.py
"""
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import article_sources                                         # noqa: E402
import image_brand as th                                     # noqa: E402


def test_bing_news_rss_forces_english_language():
    assert "setlang=en" in article_sources.BING_RSS, article_sources.BING_RSS
    asked = []

    def download(url, *a, **k):
        asked.append(url)
        raise OSError("khong can mang")

    with mock.patch.object(article_sources, "_download", side_effect=download):
        assert article_sources.report_about_keyword("Anthropic", so=4) == []
    assert asked and all("setlang=en" in u for u in asked), asked


def _person(ent_id, labels, p18="Some Person.jpg"):
    return {ent_id: {"labels": {k: {"language": k, "value": v} for k, v in labels.items()},
                     "claims": {"P18": [{"mainsnak": {"datavalue": {"value": p18}}}]}}}


def test_material_wikidata_person_label_falls_back_to_mul_not_dropped():
    company_claims = {"P169": [{"rank": "preferred", "mainsnak": {"datavalue": {"value": {"id": "Q10"}}}}],
                      "P112": [{"rank": "normal", "mainsnak": {"datavalue": {"value": {"id": "Q20"}}}},
                               {"rank": "normal", "mainsnak": {"datavalue": {"value": {"id": "Q30"}}}}]}
    asked = {}

    def ask_api(url, **kw):
        asked.update(kw)
        ents = {}
        ents.update(_person("Q10", {"mul": "John Ternus"}, "John Ternus.jpg"))           # chi co mul
        ents.update(_person("Q20", {"en": "Steve Wozniak", "mul": "Woz"}, "Woz.jpg"))     # en thang mul
        ents.update(_person("Q30", {"ja": "ジョン"}, "Nolabel.jpg"))                       # khong en/mul -> bo
        return {"entities": ents}

    with mock.patch.object(th, "qid_rank", return_value=("Q312", company_claims)), \
         mock.patch.object(th, "_ask_api", side_effect=ask_api):
        tl = th.material_wikidata("Apple")
    assert asked.get("languages") == "en|mul", asked
    names = [p["name"] for p in tl["people"]]
    assert names[0] == "John Ternus" and tl["people"][0]["person_role"] == "CEO", tl["people"]
    assert "Steve Wozniak" in names and "Woz" not in names, names
    assert all(p["name"] != "ジョン" for p in tl["people"]), tl["people"]


def test_ranking_image_gets_its_own_vision_question():
    """(c) `kind="ranking"` rơi vào câu chung "trụ sở/campus/sản phẩm" — một bảng chụp
    màn hình không bao giờ trả lời "có" được. Đo thật trên router vision: 5/5 ảnh
    arena.ai thật bị loại với câu cũ, 5/5 qua với câu mới; ảnh campus hỏi kiểu
    ranking vẫn bị loại."""
    q = th.sentence_ask_vision("Samsung rót vốn vào đối thủ chip AI của Nvidia",
                               {"company": "Nvidia", "kind": "ranking", "site": "ARENA.AI",
                                "board": "Text Arena"})
    assert "BANG XEP HANG" in q and "LIEN_QUAN" in q and "Nvidia" in q, q
    assert "ARENA.AI" in q and "Text Arena" in q, q
    assert "BOI CANH" not in q and "co so/san pham" not in q, q
    # khong co site/board (ung vien thieu truong) van ra cau hoi hop le
    q2 = th.sentence_ask_vision("x", {"company": "OpenAI", "kind": "ranking"})
    assert "BANG XEP HANG" in q2 and "tu ," not in q2 and "bang ," not in q2, q2
    # cac loai khac khong doi
    assert "BOI CANH" in th.sentence_ask_vision("x", {"company": "Nvidia", "kind": "photo"})


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
