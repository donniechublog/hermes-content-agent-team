#!/usr/bin/env python3
"""LOW-433: hai tin KHAC nhau khong duoc ra cung draft_id.

Truoc day `_draft_id` chi giu 37 ky tu dau tieu de (khoa `dre-donniechublog` dai 17),
nen "Anthropic's Claude Opus 5.5 now available in Amazon Bedrock" va "... in Google
Vertex AI" cung ra `anthropic-s-claude-opus-5-5-now-avail-dre-donniechublog` — tin sau
ghi de .img.json/.writer.json/.png cua tin truoc, bang den noi nham the goc.
"""
import json
import re
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import approve_pick as pick                 # noqa: E402
import tam  # noqa: E402

DRAFT_ID_OK = re.compile(r"^[a-z0-9][a-z0-9-]{0,54}$")     # = approve_post._DRAFT_ID_HOP_LE

BEDROCK = {"index": 1, "title": "Anthropic's Claude Opus 5.5 now available in Amazon Bedrock",
           "link": "https://aws.amazon.com/about-aws/whats-new/2026/09/claude-opus-5-5-bedrock/"}
VERTEX = {"index": 2, "title": "Anthropic's Claude Opus 5.5 now available in Google Vertex AI",
          "link": "https://cloud.google.com/blog/products/ai-machine-learning/claude-opus-5-5-vertex"}


def _callback_prefixes():
    """Moi tien to callback_data ghep TRUC TIEP voi draft_id trong ma nguon."""
    ra = set()
    for p in ROOT.glob("*.py"):
        src = p.read_text(encoding="utf-8")
        ra |= set(re.findall(r'"callback_data":\s*"([a-z]+:)"\s*\+\s*draft_id', src))
        if p.name == "moat_publish.py":           # "mlaif:" + path.stem (stem = draft_id)
            m = re.search(r"CODE_BUTTON_FORM_AGAIN\s*=\s*(\{[^}]*\})", src)
            ra |= set(json.loads(m.group(1)).values())
    return ra


def test_same_title_prefix_different_link_gives_different_id():
    for brand in ("donniechublog", "dcgr"):
        for vai in ("dre", "ethan", "kite", "gin"):
            a, b = pick._draft_id(BEDROCK, brand, vai), pick._draft_id(VERTEX, brand, vai)
            assert a != b, (a, b)
            for d in (a, b):
                assert len(d.encode()) <= 55 and DRAFT_ID_OK.match(d), d
                assert d.startswith("anthropic-s-claude-opus"), d          # van doc duoc la tin nao
                assert d.endswith(f"-{vai}-{brand}"), d                          # khoa vai con nguyen


def test_same_link_gives_same_id():
    lai = dict(BEDROCK, link=BEDROCK["link"] + "?utm_source=x")          # bao cao khac, them utm
    assert pick._draft_id(BEDROCK, "donniechublog", "dre") == pick._draft_id(lai, "donniechublog", "dre")


def test_id_stable_after_research_swaps_google_news_link():
    """`_research_source` doi item["link"] Google News -> link that va cat link cu vao
    `gnews_url`; approve_command goi lai `_draft_id` SAU create_pair, nut lam lai goi
    tren item da ghi manifest — ca hai phai ra dung id da tao."""
    goc = dict(BEDROCK, link="https://news.google.com/rss/articles/CBMiXYZ")
    truoc = pick._draft_id(goc, "dcgr", "dre")
    sau = dict(goc, gnews_url=goc["link"], link=BEDROCK["link"])
    assert pick._draft_id(sau, "dcgr", "dre") == truoc


def test_longest_callback_data_fits_telegram():
    tien_to = _callback_prefixes()
    assert {"imgredo:", "imgok:", "ok:", "pcancel:", "mlaif:"} <= tien_to, tien_to
    dai = {"index": 9, "title": "x" * 200, "link": "https://example.com/a"}
    for vai in ("ethan", "dre", "kite", "gin", "itachi"):
        for brand in ("donniechublog", "dcgr"):
            d = pick._draft_id(dai, brand, vai)
            for t in tien_to:
                assert len((t + d).encode()) <= 64, (t, d)


def test_legacy_formula_unchanged():
    """Draft dang song mang id cong thuc cu — `legacy=True` phai ra DUNG id cu."""
    assert pick._draft_id(BEDROCK, "donniechublog", "dre", legacy=True) == \
        "anthropic-s-claude-opus-5-5-now-avail-dre-donniechublog"


def _repick_env(items, img_files):
    tmp = Path(tam.temp_dir(prefix="low433_"))
    (tmp / "drafts").mkdir()
    for name, body in img_files.items():
        (tmp / "drafts" / (name + ".img.json")).write_text(json.dumps(body), encoding="utf-8")
    m = tmp / "finn_candidates_a.json"
    m.write_text(json.dumps({"items": items}), encoding="utf-8")
    return tmp, m


def _run_repick(tmp, m, index):
    redo, created = [], []
    saved = {k: getattr(pick, k) for k in ("STATE_DIR", "DRAFTS", "create_pair")}
    pick.STATE_DIR, pick.DRAFTS = tmp, tmp / "drafts"
    pick.create_pair = lambda it, **kw: (created.append(it["index"]), ("t_new", None))[1]
    old_post = sys.modules.get("approve_post")
    sys.modules["approve_post"] = types.SimpleNamespace(
        _hand_redo=lambda d: (redo.append(d), ("ok", "t_r"))[1])
    try:
        pick._repick({"manifest": str(m), "index": index, "brand": "blog", "scan_role": "finn"}, "dre")
    finally:
        for k, v in saved.items():
            setattr(pick, k, v)
        if old_post is None:
            sys.modules.pop("approve_post", None)
        else:
            sys.modules["approve_post"] = old_post
    return redo, created


def test_repick_finds_draft_created_before_low433():
    cu = pick._draft_id(BEDROCK, "blog", "dre", legacy=True)
    tmp, m = _repick_env([BEDROCK], {cu: {"link": BEDROCK["link"]}})
    redo, created = _run_repick(tmp, m, 1)
    assert redo == [cu] and created == [], (redo, created)


def test_repick_ignores_legacy_draft_of_other_story():
    """Id cu da bi tin Bedrock chiem: nut lam lai cua tin Vertex KHONG duoc lam lai
    draft cua Bedrock — tao cap moi."""
    cu = pick._draft_id(VERTEX, "blog", "dre", legacy=True)
    assert cu == pick._draft_id(BEDROCK, "blog", "dre", legacy=True)
    tmp, m = _repick_env([VERTEX], {cu: {"link": BEDROCK["link"]}})
    redo, created = _run_repick(tmp, m, 2)
    assert redo == [] and created == [2], (redo, created)


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
