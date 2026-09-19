#!/usr/bin/env python3
"""LOW-277 (19/09/2026): vong doan RSS theo ten mien trong article_sources.find()
tung ton ~80s cho mot tin.

Do tren may chu (26 tin that): 3 tin mat ~80s du bai khop da co tu giay 3-6 —
mot mien treo ca 5 duong x 15s, va `with ThreadPoolExecutor` doi no xong. Bai khop
qua RSS den muon nhat o giay 13,9. Sua: tran FEED_BUDGET_SECONDS cho ca vong, mien
timeout/khong ket noi duoc thi bo cac duong con lai, van giu thu tu Google News.

Chay:  venv/bin/python tests/test_rss_guess_budget.py
"""
import sys
import threading
import time
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import article_sources                                               # noqa: E402

TITLE = "Anthropic details practical metrics to help monitor the speed of AI development"
LINK = "https://siliconangle.com/2026/09/17/anthropic-details"


def _gnews_rss(outlets):
    rows = "".join(f"<item><title>t{i}</title><link>https://news.google.com/rss/articles/X{i}</link>"
                   f'<source url="{u}">S</source></item>' for i, u in enumerate(outlets))
    return SimpleNamespace(status_code=200, content=f"<rss><channel>{rows}</channel></rss>".encode())


def _feed(outlet):
    item = f"<item><title>{TITLE}</title><link>{outlet}/story</link></item>"
    return SimpleNamespace(status_code=200, content=f"<rss><channel>{item}</channel></rss>".encode())


def _run_find(outlets, feed_behaviour, budget):
    """find() voi Google News tra `outlets`; `feed_behaviour(outlet, url)` quyet
    tung lan tai feed. Tat Bing + bu Google News de chi con vong RSS."""
    def fake_download(url, timeout=20):
        if "news.google.com/rss/search" in url:
            return _gnews_rss(outlets)
        outlet = next(o for o in outlets if url.startswith(o))
        return feed_behaviour(outlet, url)
    with mock.patch.object(article_sources, "_download", side_effect=fake_download), \
            mock.patch.object(article_sources, "title_find", return_value=TITLE), \
            mock.patch.object(article_sources, "_query_bing", return_value=[]), \
            mock.patch.object(article_sources, "other_outlets_bing", return_value=[]), \
            mock.patch.object(article_sources, "other_outlets_gnews", return_value=[]), \
            mock.patch.object(article_sources, "FEED_BUDGET_SECONDS", budget):
        start = time.time()
        kq = article_sources.find("Anthropic công bố", LINK, so=4)
        return kq, time.time() - start


def test_feed_phase_stops_at_budget_and_keeps_early_match():
    """Mien treo khong duoc giu ca find(): het tran la di tiep voi bai da khop."""
    def behaviour(outlet, url):
        if outlet == "https://slow.example":
            time.sleep(2)
            return SimpleNamespace(status_code=404, content=b"")
        return _feed(outlet)
    kq, took = _run_find(["https://slow.example", "https://fast.example"], behaviour, budget=0.5)
    assert took < 1.5, f"find() doi mien treo: {took:.1f}s"
    assert [p["url"] for p in kq["pages"]] == [LINK, "https://fast.example/story"], kq["pages"]


def test_timeout_domain_skips_remaining_paths():
    calls = {}
    lock = threading.Lock()

    def behaviour(outlet, url):
        with lock:
            calls[outlet] = calls.get(outlet, 0) + 1
        if outlet == "https://dead.example":
            raise httpx.ConnectTimeout("khong ket noi duoc")
        if outlet == "https://readslow.example":
            raise httpx.ReadTimeout("doc qua lau")
        return SimpleNamespace(status_code=404, content=b"")
    _run_find(["https://dead.example", "https://readslow.example", "https://missing.example"],
              behaviour, budget=5)
    assert calls["https://dead.example"] == 1, calls
    assert calls["https://readslow.example"] == 1, calls
    assert calls["https://missing.example"] == 5, calls     # 404 thi van thu du 5 duong


def test_results_follow_google_news_order_not_finish_order():
    def behaviour(outlet, url):
        if outlet == "https://first.example":
            time.sleep(0.3)                                  # xong SAU nhung dung TRUOC trong Google News
        return _feed(outlet)
    kq, _ = _run_find(["https://first.example", "https://second.example"], behaviour, budget=5)
    urls = [p["url"] for p in kq["pages"]]
    assert urls == [LINK, "https://first.example/story", "https://second.example/story"], urls


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
