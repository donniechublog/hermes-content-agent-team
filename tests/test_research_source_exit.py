#!/usr/bin/env python3
"""LOW-275 (19/09/2026): 5/9 tin Dre dcgr bao "không tìm được nguồn ... article_sources
exit 1: inance.biggo.com/..." — khong phai loi.

Do that tren may chu:
* `article_sources.main()` tra 1 khi CHI CO BAI GOC — trung ma Python tu tra khi co
  exception. approve coi la loi, in 300 ky tu CUOI stderr (cat ngang giua chu,
  "inance.biggo.com") va BO buoc doi link Google News -> link that: 4 draft giao
  Dre va ghi meta voi link chuyen huong news.google.com.
* Tieu de tim cua bai biggo la slug UUID "1050d70e f675 45be 8384 79934321d06f".
* Tin Anthropic: Google News tra san CNBC/Tekedia cung tin, nhung `find()` chi
  doan RSS theo ten mien, Bing rong -> chi con bai goc.

Chay:  venv/bin/python tests/test_research_source_exit.py
"""
import email.utils as eu
import json
import sys
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import approve_pick                                                  # noqa: E402
import article_sources                                               # noqa: E402

GNEWS_LINK = "https://news.google.com/rss/articles/CBMiQUFVX3lxTE9PT3NieVEt?oc=5"
REAL_LINK = "https://finance.biggo.com/news/1050d70e-f675-45be-8384-79934321d06f"
TRACEBACK = """Traceback (most recent call last):
  File "/home/x/content-team/article_sources.py", line 29, in <module>
    import httpx
ModuleNotFoundError: No module named 'httpx'
"""


class _Rss:
    def __init__(self, rows):
        body = "".join(
            f"<item><title>{t}</title><link>{lk}</link><pubDate>{d}</pubDate>"
            f'<source url="{src}">S</source></item>' for t, lk, d, src in rows)
        self.content = f"<rss><channel>{body}</channel></rss>".encode()


def _recent(days=0):
    return eu.formatdate(time.time() - days * 86400)


def test_exit_code_constants_match_and_differ_from_python_errors():
    assert approve_pick.EXIT_ONLY_ORIGINAL == article_sources.EXIT_ONLY_ORIGINAL
    assert article_sources.EXIT_ONLY_ORIGINAL not in (0, 1, 2)   # 1 = exception, 2 = argparse


def test_main_only_original_still_writes_file_with_own_code():
    one_page = {"title": "t", "title_en": "", "source_url": REAL_LINK,
                "pages": [{"url": REAL_LINK, "kind": "article", "title": "t"}]}
    with tempfile.TemporaryDirectory() as d, \
            mock.patch.object(article_sources, "find", return_value=one_page), \
            mock.patch.object(sys, "argv", ["x", "--tieu-de", "t", "--link", REAL_LINK,
                                            "--out", f"{d}/a.json"]):
        code = article_sources.main()
        assert code == article_sources.EXIT_ONLY_ORIGINAL, code
        assert json.loads(Path(d, "a.json").read_text())["source_url"] == REAL_LINK


def test_last_error_line_is_the_exception_not_a_cut_tail():
    assert approve_pick._last_error_line(TRACEBACK) == "ModuleNotFoundError: No module named 'httpx'"
    info = "[nguon_bai] link Google News -> https://finance.biggo.com/news/1050d70e\n  [gốc] https://x\n"
    assert approve_pick._last_error_line(info) == "[gốc] https://x"
    assert approve_pick._last_error_line("") == "(khong co stderr)"


def _run_research(returncode, stderr="", source=None):
    """Chay _research_source voi subprocess gia: ghi `source` ra tep nguon nhu
    article_sources that roi tra `returncode`."""
    item = {"title": "Trung tâm dữ liệu AI", "link": GNEWS_LINK, "index": 14}
    with tempfile.TemporaryDirectory() as d:
        def fake_run(cmd, **_kw):
            if source is not None:
                out = Path(cmd[cmd.index("--out") + 1])
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(json.dumps(source), encoding="utf-8")
            return SimpleNamespace(returncode=returncode, stderr=stderr, stdout="")
        with mock.patch.object(approve_pick, "STATE_DIR", Path(d)), \
                mock.patch.object(approve_pick.subprocess, "run", side_effect=fake_run), \
                mock.patch.object(approve_pick, "write_meta") as write_meta:
            result = approve_pick._research_source(item, "draft-x", f"{d}/x.png", "dcgr")
    return result, item, write_meta


def test_only_original_warns_but_still_swaps_google_news_link():
    source = {"title": "t", "title_en": "AI Data Centers Spark Storage Boom",
              "source_url": REAL_LINK, "gnews_url": GNEWS_LINK,
              "pages": [{"url": REAL_LINK, "kind": "article"}]}
    (error, warning), item, write_meta = _run_research(approve_pick.EXIT_ONLY_ORIGINAL, source=source)
    assert error is None, error
    assert warning and "chỉ có bài gốc" in warning and "AI Data Centers Spark" in warning, warning
    assert item["link"] == REAL_LINK and item["gnews_url"] == GNEWS_LINK, item
    assert write_meta.called, "meta phai ghi lai link that"


def test_crash_reports_real_exception():
    (error, warning), item, _ = _run_research(1, stderr=TRACEBACK)
    assert warning is None
    assert "ModuleNotFoundError: No module named 'httpx'" in error and "exit 1" in error, error
    assert item["link"] == GNEWS_LINK


def test_success_has_no_message():
    source = {"title": "t", "title_en": "x", "source_url": REAL_LINK, "gnews_url": GNEWS_LINK,
              "pages": [{"url": REAL_LINK}, {"url": "https://cnbc.com/a"}]}
    (error, warning), item, _ = _run_research(0, source=source)
    assert (error, warning) == (None, None)
    assert item["link"] == REAL_LINK


def test_title_slug_skips_uuid_but_keeps_model_names():
    assert article_sources._title_slug(REAL_LINK) == ""
    got = article_sources._title_slug("https://x.com/news/nvidia-b200-sales-surge-in-china")
    assert got == "nvidia b200 sales surge in china", got


def test_title_gnews_id_takes_only_the_same_article_id():
    rows = [("Some other story - Other", "https://news.google.com/rss/articles/CBMiOTHER?oc=5",
             _recent(), "https://other.com"),
            ("AI Data Centers Spark Storage Boom - BigGo Finance", GNEWS_LINK, _recent(),
             "https://finance.biggo.com")]
    queries = []

    def fake_download(url, timeout=20):
        queries.append(url)
        return _Rss(rows)
    with mock.patch.object(article_sources, "_download", side_effect=fake_download):
        got = article_sources._title_gnews_id(GNEWS_LINK, REAL_LINK)
    assert got == "AI Data Centers Spark Storage Boom", got
    assert "1050d70e-f675-45be-8384-79934321d06f" in queries[0], queries

    with mock.patch.object(article_sources, "_download", return_value=_Rss(rows[:1])):
        assert article_sources._title_gnews_id(GNEWS_LINK, REAL_LINK) == ""
    assert article_sources._title_gnews_id("", REAL_LINK) == ""       # khong phai tin Google News


def test_title_page_asks_google_news_id_before_slug():
    blocked = mock.Mock(status_code=403, text="")
    with mock.patch.object(article_sources.httpx, "get", return_value=blocked), \
            mock.patch.object(article_sources, "_title_rss", return_value=""), \
            mock.patch.object(article_sources, "_title_gnews_id", return_value="Real headline here") as gid:
        assert article_sources._title_page(REAL_LINK, GNEWS_LINK) == "Real headline here"
    gid.assert_called_once_with(GNEWS_LINK, REAL_LINK)


def _gnews_items():
    title = "Anthropic details practical metrics to help monitor the speed of AI development"
    rows = [
        (title + " - SiliconANGLE", "g/orig", _recent(), "https://siliconangle.com"),
        ("Anthropic Proposes Three New AI Development Metrics - Tekedia", "g/tek", _recent(1),
         "https://www.tekedia.com"),
        ("Anthropic shares 3 metrics to help AI companies monitor pace of development - cnbc.com",
         "g/cnbc", _recent(), "https://www.cnbc.com"),
        ("Anthropic metrics development old story - Old", "g/old", _recent(40), "https://old.com"),
        ("For AI agents, it's the best of times - SiliconANGLE", "g/other", _recent(),
         "https://unrelated.com"),
        ("Anthropic công bố chỉ số phát triển metrics development", "g/vi", _recent(),
         "https://vnexpress.net"),
        ("Anthropic metrics development roundup - MSN", "g/msn", _recent(), "https://www.msn.com"),
    ]
    import xml.etree.ElementTree as ET
    return title, ET.fromstring(_Rss(rows).content).findall(".//item")


def test_other_outlets_gnews_filters_ranks_and_resolves():
    title, items = _gnews_items()
    real = {"g/tek": "https://www.tekedia.com/anthropic-metrics",
            "g/cnbc": "https://www.cnbc.com/2026/09/17/anthropic-metrics.html"}
    resolved = []

    def fake_resolve(link, timeout=30, phien=None):
        resolved.append(link)
        return real.get(link)
    with mock.patch.object(article_sources, "resolve_code_gnews", side_effect=fake_resolve):
        pages = article_sources.other_outlets_gnews(title, items, count=3,
                                                    skip_domains=("siliconangle.com",))
    assert [p["url"] for p in pages] == [real["g/cnbc"], real["g/tek"]], pages   # chung nhieu tu xep truoc
    assert all(p["kind"] == "other_outlet" for p in pages)
    assert set(resolved) == {"g/cnbc", "g/tek"}, resolved   # cu, lac de, tieng Viet, msn, bai goc: khong mo


def test_find_falls_back_to_google_news_when_rss_and_bing_are_empty():
    title, items = _gnews_items()
    rss = _Rss([(i.findtext("title"), i.findtext("link"), i.findtext("pubDate"),
                 i.find("source").get("url")) for i in items])
    with mock.patch.object(article_sources, "title_find", return_value=title), \
            mock.patch.object(article_sources, "_download", return_value=rss), \
            mock.patch.object(article_sources, "_query_bing", return_value=[]), \
            mock.patch.object(article_sources, "other_outlets_bing", return_value=[]), \
            mock.patch.object(article_sources, "resolve_code_gnews",
                              side_effect=lambda link, **_k: f"https://real.example/{link[2:]}"):
        kq = article_sources.find("Anthropic công bố bộ chỉ số",
                                  "https://siliconangle.com/2026/09/17/anthropic-details", so=4)
    kinds = [p["kind"] for p in kq["pages"]]
    assert kinds[0] == "article" and kinds.count("other_outlet") >= 2, kq["pages"]


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
