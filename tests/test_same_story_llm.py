#!/usr/bin/env python3
"""LOW-276 (19/09/2026): "bao khac cung tin" = cung SU KIEN, khong chi chung 2 tu.

Do 180 cap tieu de that (tests/golden/same_story_golden.json): luat cu (chung >= 2
tu dac trung) nhan nham 34/38 cap khac tin — cung chu the, khac su kien (tin luu
tru dien biggo vs bai Crusoe goi von, chi vi chung "data centers"). Moi luat chi
dem/cham do hiem cua tu deu that bai (tot nhat 27/38). Sua: code loai (<2 tu) va
nhan (>=4 tu) ca chac, ca lung chung hoi LLM MOT lan cho ca danh sach; LLM hong
thi lui ve luat cu. Do that voi LLM: nhan nham 5-6/38, giu 127-128/142.

Chay:  venv/bin/python tests/test_same_story_llm.py
"""
import email.utils as eu
import io
import json
import os
import sys
import time
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import article_sources as a                                          # noqa: E402

ORIGINAL = "Anthropic details practical metrics to help monitor the speed of AI development"
SURE = "Anthropic shares 3 metrics to help AI companies monitor pace of development"       # chung 5 tu
BORDER_SAME = "Anthropic Proposes Three New AI Development Metrics Days After Amodei Calls"  # chung 3 tu
BORDER_OTHER = "Anthropic to Release Further Analyses on Economic Index Metrics"            # chung 2 tu
UNRELATED = "Exclusive: PeakMetrics tracks brand reputations across five top AI platforms"  # chung 0 tu


def test_triage_asks_llm_once_and_only_for_borderline():
    asked = []

    def fake_llm(title, candidates):
        asked.append(list(candidates))
        return {0}                                           # chi ung vien lung chung dau tien cung tin
    with mock.patch.object(a, "_ask_same_event", side_effect=fake_llm):
        got = a.same_story_many(ORIGINAL, [SURE, BORDER_SAME, BORDER_OTHER, UNRELATED])
    assert got == [True, True, False, False], got
    assert asked == [[BORDER_SAME, BORDER_OTHER]], asked      # mot lan, khong gui ca chac


def test_llm_down_keeps_old_word_rule():
    with mock.patch.object(a, "_ask_same_event", return_value=None):
        assert a.same_story_many(ORIGINAL, [BORDER_SAME, BORDER_OTHER, UNRELATED]) == [True, True, False]


def test_no_llm_call_without_borderline():
    with mock.patch.object(a, "_ask_same_event") as llm:
        assert a.same_story_many(ORIGINAL, [SURE, UNRELATED]) == [True, False]
        assert a.same_story_many(ORIGINAL, []) == []
    llm.assert_not_called()


def _router_reply(content):
    body = json.dumps({"choices": [{"message": {"content": content}}]}).encode()
    return SimpleNamespace(read=lambda: body)


def test_ask_same_event_reads_router_reply():
    cands = ["x", "y", "z"]
    with mock.patch.object(a.env_load, "load"), mock.patch.dict(os.environ, {"OPENAI_API_KEY": "k"}):
        with mock.patch.object(a.urllib.request, "urlopen", return_value=_router_reply("Answer: [2, 3, 9]")):
            assert a._ask_same_event("t", cands) == {1, 2}           # 9 ngoai danh sach: bo
        with mock.patch.object(a.urllib.request, "urlopen", return_value=_router_reply("[]")):
            assert a._ask_same_event("t", cands) == set()
        with mock.patch.object(a.urllib.request, "urlopen", return_value=_router_reply("I am not sure")):
            assert a._ask_same_event("t", cands) is None
        with mock.patch.object(a.urllib.request, "urlopen", side_effect=OSError("router down")):
            assert a._ask_same_event("t", cands) is None
    with mock.patch.object(a.env_load, "load"), mock.patch.dict(os.environ, {"OPENAI_API_KEY": ""}):
        assert a._ask_same_event("t", cands) is None


def _rss(rows):
    now = eu.formatdate(time.time())
    items = "".join(f"<item><title>{t}</title><link>{lk}</link><pubDate>{now}</pubDate>"
                    f'<source url="{src}">S</source></item>' for t, lk, src in rows)
    return SimpleNamespace(status_code=200, content=f"<rss><channel>{items}</channel></rss>".encode())


def test_bing_keeps_only_same_event_after_one_llm_call():
    rows = [(SURE, "https://www.cnbc.com/a", "https://www.cnbc.com"),
            (BORDER_OTHER, "https://blockchain.news/b", "https://blockchain.news"),
            (UNRELATED, "https://siliconangle.com/c", "https://siliconangle.com")]
    with mock.patch.object(a, "_download", return_value=_rss(rows)), \
            mock.patch.object(a, "_query_bing", return_value=["q"]), \
            mock.patch.object(a.httpx, "head", side_effect=lambda url, **k: SimpleNamespace(url=url, status_code=200)), \
            mock.patch.object(a, "_ask_same_event", return_value=set()) as llm, \
            mock.patch("sys.stderr", io.StringIO()):
        pages = a.other_outlets_bing(ORIGINAL, so=4)
    assert [p["url"] for p in pages] == ["https://www.cnbc.com/a"], pages
    llm.assert_called_once()


def test_gnews_dedupes_domain_after_same_event_filter():
    """Bai khac tin cua mien X dung truoc khong duoc chan bai cung tin cua chinh X."""
    import xml.etree.ElementTree as ET
    rows = [(BORDER_OTHER + " - Tekedia", "g/other", "https://www.tekedia.com"),
            (BORDER_SAME + " - Tekedia", "g/same", "https://www.tekedia.com")]
    items = ET.fromstring(_rss(rows).content).findall(".//item")
    with mock.patch.object(a, "_ask_same_event", return_value={1}), \
            mock.patch.object(a, "resolve_code_gnews", side_effect=lambda link, **k: f"https://www.tekedia.com/{link[2:]}"), \
            mock.patch("sys.stderr", io.StringIO()):
        pages = a.other_outlets_gnews(ORIGINAL, items, count=3)
    assert [p["url"] for p in pages] == ["https://www.tekedia.com/same"], pages


def test_golden_set_never_decided_wrong_by_code_alone():
    """Code chi tu quyet ca chac: khong ca KHAC tin nao trong bo mau duoc tu nhan
    (chung >= SAME_STORY_SURE), khong ca CUNG tin nao bi tu loai (chung < 2)."""
    gold = json.loads((ROOT / "tests/golden/same_story_golden.json").read_text(encoding="utf-8"))["pairs"]
    assert len(gold) >= 150 and {"title", "candidate", "same"} <= set(gold[0])
    for g in gold:
        shared = len(a.story_tokens(g["title"]) & a.story_tokens(g["candidate"]))
        if g["same"]:
            assert shared >= 2, g
        else:
            assert shared < a.SAME_STORY_SURE, g


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
