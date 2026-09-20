#!/usr/bin/env python3
"""LOW-312 — phat lai mot trang THAT cho Playwright (Chromium that, mang gia).

`wikipedia_gartner.har.zip` ghi bang `tests/replay.py record-har ... --no-js` tu
https://en.m.wikipedia.org/wiki/Gartner (CC BY-SA 4.0) ngay 20/09/2026. Moi
request duoc tra tu tep do; request khong co trong tep bi huy — test khong bao
gio ra mang, nen chay duoc trong CI va cho cung mot ket qua moi lan.

Day la cai mo khoa cho nhom module 0% can Chromium (`capture_page` 47%,
`prepare/browser` 21%, `capture_chart` 0%): truoc gio chung chi duoc kiem bang
cach chay that tren trang that.

Chay:  venv/bin/python tests/test_replay_browser.py
"""
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import capture_page                    # noqa: E402
import replay                          # noqa: E402

HAR = replay.GOLDEN / "replay" / "wikipedia_gartner.har.zip"
URL = "https://en.wikipedia.org/wiki/Gartner"      # ban ghi di qua chuyen huong m. -> en.


def test_capture_renders_recorded_page_offline():
    out = Path(tempfile.mkdtemp(prefix="replay_browser_")) / "page.png"
    with replay.replay_session(HAR) as session:
        assert capture_page.capture(URL, out, phien=session) is True
    w, h = Image.open(out).size
    assert w >= 600 and h >= 300, (w, h)
    # trang co noi dung that, khong phai trang trang "khong tai duoc"
    colors = Image.open(out).convert("RGB").resize((64, 64)).getcolors(64 * 64)
    assert len(colors) > 20, f"anh chup gan nhu mot mau ({len(colors)}) — HAR khong phat lai duoc?"


def test_page_text_comes_from_the_recording():
    with replay.replay_session(HAR) as session:
        with session.trang() as page:
            page.goto(URL, wait_until="domcontentloaded", timeout=20000)
            assert "Gartner" in page.title()
            assert page.query_selector("h1") is not None


def test_mobile_lead_block_is_cut_from_the_recorded_page():
    """Ong Chu 06/09 + 12/09/2026: chup trang nguon o khung mobile, cat khoi lead
    lam bia. Truoc gio chi kiem duoc bang cach chay that."""
    out = Path(tempfile.mkdtemp(prefix="replay_browser_")) / "lead.png"
    with replay.replay_session(HAR) as session:
        lead = capture_page.capture_lead_mobile(URL, out, phien=session)
    assert lead and lead["source"] == "capture_source" and lead["capture_source"] is True
    assert lead["page_title"] == "Gartner - Wikipedia", lead
    assert lead["capture_kind"] in ("headline", "hero"), lead
    assert out.exists() and Image.open(out).size[0] >= 300


def test_unrecorded_url_never_reaches_the_network():
    with replay.replay_session(HAR) as session:
        with session.trang() as page:
            try:
                page.goto("https://example.com/", timeout=10000)
            except Exception as e:                           # noqa: BLE001
                assert "ERR_" in str(e) or "abort" in str(e).lower(), e
            else:
                raise AssertionError("request ngoai HAR ma van di duoc — replay khong cach ly mang")


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
