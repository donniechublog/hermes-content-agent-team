#!/usr/bin/env python3
"""LOW-337 (21/09/2026) — tin ve MODEL: logo > benchmark chart > founder > office.

Ong Chu, the Qwen-Image-2.1 (dcgr): Ethan chon anh toa nha Alibaba trong khi engine da co san
the logo + Jack Ma. Nguyen nhan: the logo bi coi la chart ("CHI ghep doc") nen khong the la hero,
nen "Goi y nen hero" chi con anh toa nha. Chay:  python tests/test_low337_model_image_priority.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import role  # noqa: E402
import story_type  # noqa: E402

LOGO = {"id": "A4", "kind": "chart", "ratio": 0.8, "short_side": 1200, "logo_card": True, "uses": ["bìa"], "relevant": True,
        "brand_match": {"kind": "logo", "company": "Alibaba"}}
OFFICE = {"id": "A11", "kind": "photo", "ratio": 1.33, "uses": ["bìa"], "relevant": True,
          "brand_match": {"kind": "photo", "company": "Alibaba"}}
PLAIN_CHART = {"id": "A9", "kind": "chart", "ratio": 1.2, "uses": ["thân"], "relevant": True}


def test_model_order_logo_then_chart_then_founder_then_office():
    o = story_type.order_image("MODEL")
    assert o[:1] == ("logo",), o
    assert o.index("logo") < o.index("ranking") < o.index("founder") < o.index("headquarters"), o
    assert o.index("announcement_chart") < o.index("founder"), o


def test_scores_follow_the_order():
    s = lambda k: story_type.score_by_type("MODEL", k)      # noqa: E731
    assert s("logo") > s("founder") > s("photo") > 0, (s("logo"), s("founder"), s("photo"))


def test_model_still_ranking_story_business_still_not():
    assert story_type.is_ranking_story_type("MODEL") and story_type.is_ranking_story_type("BENCHMARK")
    assert not story_type.is_ranking_story_type("BUSINESS")
    assert not story_type.is_ranking_story_type("M&A")


def test_logo_card_is_hero_for_ethan_plain_chart_is_not():
    assert role.is_brand_logo_card(LOGO) and not role.is_brand_logo_card(OFFICE)
    assert role.can_be_hero("ethan", LOGO)
    assert not role.can_be_hero("ethan", PLAIN_CHART)


def test_brief_hero_suggestion_puts_logo_before_office():
    import ethan_prepare
    d, _ = ethan_prepare.label_ethan({**LOGO, "ratio": 0.8, "faces": 0})
    assert d[0].startswith("THẺ LOGO"), d



def _m(category, images, **k):
    return {"category": category, "images": images, "brand": "dcgr", "title": "Qwen-Image-2.1",
            "is_ranking_story": category in ("MODEL", "BENCHMARK"), "image_role": "ethan", **k}


XH = {"id": "XH", "kind": "chart", "ratio": 0.8, "uses": ["bìa"], "relevant": True,
      "ranking": {"kind": "card", "model": "Qwen-Image-2.1"}}


def test_ethan_model_story_only_logo_or_benchmark():
    import image_rules_ethan as r
    assert r.model_story_only("MODEL") and r.model_story_only("benchmark")
    assert not r.model_story_only("BUSINESS") and not r.model_story_only("")
    assert r.model_story_image_ok(LOGO) and r.model_story_image_ok(XH)
    assert not r.model_story_image_ok(OFFICE)


def _loi(category, pick, images):
    import ethan_submit
    anh = {a["id"]: a for a in images}
    return ethan_submit._check_model_story(anh, pick, None, _m(category, images))


def test_ethan_submit_blocks_office_on_model_story_allows_logo():
    imgs = [dict(LOGO), dict(OFFICE), dict(XH)]
    assert _loi("MODEL", "A11", imgs), "anh toa nha phai bi chan o tin MODEL"
    assert not _loi("MODEL", "A4", imgs)
    assert not _loi("MODEL", "XH", imgs)
    assert not _loi("BUSINESS", "A11", imgs), "tin khong phai model: khong ap luat nay"


def test_logo_not_forced_to_xh_when_board_captured():
    import ethan_submit
    import ranking
    m = _m("MODEL", [dict(LOGO), dict(XH), dict(OFFICE)], ranking={"kind": sorted(ranking.KIND_CAPTURE)[0]})
    assert not ethan_submit._must_use_ranking(m, LOGO)
    assert ethan_submit._must_use_ranking(m, OFFICE)


def test_resolve_spec_calls_model_gate():
    src = (ROOT / "ethan_submit.py").read_text(encoding="utf-8")
    assert "loi += _check_model_story(anh, ma, ma2, m)" in src and "if _must_use_ranking(m, a):" in src


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
