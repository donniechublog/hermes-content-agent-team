#!/usr/bin/env python3
"""LOW-322 (20/09/2026) — nguon RSS cua Nova: them Google/Google Research/NVIDIA.

Ong Chu chot them bon nguon; do song tung cai thi chi BA cai dung duoc:

  - `blog.google/technology/ai/rss/` 302 sang `/innovation-and-ai/technology/ai/
    rss/` — phai ghi duong CUOI CUNG, khong dua vao chuyen huong.
  - `research.google/blog/rss/` va `developer.nvidia.com/blog/feed/` tuoi.
  - Qwen: feed con song nhung bai moi nhat 23/09/2025, va `QwenLM/Qwen3`,
    `QwenLM/Qwen3-VL` tren GitHub co 0 ban phat hanh — KHONG them lai.

Chay:  venv/bin/python tests/test_low322_nova_sources.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import scan_models as sm  # noqa: E402

MOI = {
    "Google": "https://blog.google/innovation-and-ai/technology/ai/rss/",
    "Google Research": "https://research.google/blog/rss/",
    "NVIDIA": "https://developer.nvidia.com/blog/feed/",
}


def test_three_live_feeds_added_with_exact_url():
    co = dict(sm.RSS_RANK)
    for hang, url in MOI.items():
        assert co.get(hang) == url, (hang, co.get(hang))


def test_blog_google_uses_the_url_after_redirect():
    """Duong cu `blog.google/technology/ai/rss/` chi con la mot cu 302."""
    assert not any(u == "https://blog.google/technology/ai/rss/" for _h, u in sm.RSS_RANK)


def test_dead_qwen_feed_not_added_back():
    assert not any("qwenlm" in u.lower() for _h, u in sm.RSS_RANK), \
        "feed Qwen chet tu 9/2025 — xem ghi chu tren RSS_RANK"


def test_old_feeds_kept():
    co = dict(sm.RSS_RANK)
    assert co["OpenAI"] == "https://openai.com/news/rss.xml"
    assert co["Google DeepMind"] == "https://deepmind.google/blog/rss.xml"
    assert "Mistral" in co and "HuggingFace" in co


def test_no_duplicate_feed_url_or_company():
    urls = [u for _h, u in sm.RSS_RANK]
    hang = [h for h, _u in sm.RSS_RANK]
    assert len(urls) == len(set(urls)), urls
    assert len(hang) == len(set(hang)), hang


def test_every_feed_is_https():
    assert all(u.startswith("https://") for _h, u in sm.RSS_RANK)


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
