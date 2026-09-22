#!/usr/bin/env python3
"""LOW-337 bổ sung (22/09/2026) — tin MODEL RELEASE lấy ảnh X @arena ĐẦU TIÊN, ở mọi designer,
và mọi post X làm nguồn bài đều lấy được ảnh gốc qua code crawl tweet có sẵn (get_source.py).

Ông Chủ, lần nhắc thứ n (tweet Grok 4.7 x.com/arena/status/2102080801462689999): *"miễn là tin
về model release, cứ lấy từ arena.ai đầu tiên, ko có thì mới qua nguồn khác. trong repo của chúng
ta có sẵn code để crawl hình từ tweet, check kỹ lại đi và sử dụng nó mỗi khi các designer tìm ảnh"*.

Ba chỗ hở đã đo được trên code cũ, mỗi test dưới FAIL trên code trước bản vá:
  1. `arena_x` chỉ được hỏi bên trong `find_and_capture_many`, tức chỉ tin "xếp hạng" + có
     browser; "xAI ra mắt Grok 4.7" có `is_ranking_story` False nên không bao giờ tới.
  2. Nguồn tweet @arena: crawler X chết từ 13/09, crawl-queue chỉ trả MỘT tweet đầu/ghim
     -> tweet Grok 4.7 thứ 3 trên trang không bao giờ được thấy, và không ai được báo.
  3. Thẻ logo của Ethan được miễn cổng "phải dùng XH" — kể cả khi XH là ảnh @arena.

Chay:  python tests/test_low337_arena_release_first.py
"""
import json
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import arena_x  # noqa: E402

GROK_ID = "2102080801462689999"
GROK_TEXT = ("Grok 4.7 by @SpaceXAI just dropped. Looking at how past Grok versions have trended on "
             "Agent Arena's net improvement score, where do you think 4.7 lands? Poll below.")


def _b64(tid):
    import base64
    return base64.b64encode(f"Tweet:{tid}".encode()).decode()


# Dung theo cau truc trang x.com/arena khong dang nhap do ngay 22/09/2026 (rut gon).
PROFILE_HTML = (
    '<div data-href="/arena/status/2102142912943489220" data-timeline-entry=""></div>'
    '<div data-href="/XiaomiMiMo/status/2102138559952290106" data-timeline-entry=""></div>'
    '<div data-href="/arena/status/2102074819743453410" data-timeline-entry=""></div>'
    f'<div data-href="/arena/status/{GROK_ID}" data-timeline-entry=""></div>'
    '<script>'
    f'"client:{_b64("2102142912943489220")}:details":$R[1]={{__typename:"TBirdData",'
    'full_text:"MiMo-V2.6-Pro just landed @XiaomiMiMo back in the top 10 on Code Arena"},'
    f'"client:{_b64("2102138559952290106")}:details":$R[2]={{full_text:"Grok 4.7 is great &amp; fast"}},'
    f'"client:{_b64("2102074819743453410")}:details":$R[3]={{display_text_range:$R[4]=[0,278],'
    'full_text:"Grok 4.7 by @SpaceXAI and @elonmusk is now in the Agent Arena!\\n\\nYour votes"},'
    f'"client:{_b64(GROK_ID)}:details":$R[5]={{full_text:"{GROK_TEXT}"}}'
    '</script>')


class _Resp:
    def __init__(self, body):
        self.body = body.encode()

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_x_page_posts_reads_every_tweet_with_author():
    gs = arena_x._get_source()
    with mock.patch.object(gs.urllib.request, "urlopen", lambda req, timeout=60: _Resp(PROFILE_HTML)):
        posts = gs.x_page_posts("https://x.com/arena")
    by_id = {p["id"]: p for p in posts}
    assert len(posts) == 4, posts
    assert by_id[GROK_ID]["handle"] == "arena" and by_id[GROK_ID]["text"] == GROK_TEXT
    assert by_id["2102138559952290106"]["handle"] == "XiaomiMiMo"
    assert by_id["2102138559952290106"]["text"] == "Grok 4.7 is great & fast", "entity HTML phai giai"
    assert "\n\nYour votes" in by_id["2102074819743453410"]["text"], "\\n trong chuoi JS phai thanh xuong dong"


def test_created_from_tweet_id():
    assert arena_x.created_from_id(GROK_ID) == "2026-09-21T17:01:32.000Z"


def test_page_tweets_only_arena_tweets_match():
    gs = arena_x._get_source()
    with mock.patch.object(gs.urllib.request, "urlopen", lambda req, timeout=60: _Resp(PROFILE_HTML)):
        tweets = arena_x.page_tweets(arena_x.PROFILE_URL)
    from datetime import datetime, timezone
    now = datetime(2026, 9, 22, tzinfo=timezone.utc)
    hits = [t["url"] for t in tweets if arena_x.usable(t, ["Grok 4.7"], now)]
    assert hits == ["https://x.com/arena/status/2102074819743453410", f"https://x.com/arena/status/{GROK_ID}"], \
        "tweet cua @XiaomiMiMo hien tren trang @arena KHONG duoc tinh"


def test_profile_page_is_asked_before_dead_sources_and_newest_first():
    calls = []
    older = arena_x._record("https://x.com/arena/status/2102074819743453410", "arena",
                            "2026-09-21T16:37:00.000Z", "Grok 4.7 is now in the Agent Arena!")
    newer = arena_x._record(f"https://x.com/arena/status/{GROK_ID}", "arena",
                            "2026-09-21T17:01:32.000Z", GROK_TEXT)
    srcs = [("trang", lambda: calls.append("trang") or [older, newer]),
            ("crawler", lambda: calls.append("crawler") or []),
            ("social", lambda: calls.append("social") or [])]
    with mock.patch.object(arena_x, "tweet_sources", lambda extra_urls=(): srcs), \
         mock.patch.object(arena_x, "usable", lambda tw, models, now=None: "grok 4.7"):
        got = arena_x.matching_tweets(["Grok 4.7"], in_log=lambda *_: None)
    assert [tid for tid, _ in got] == [GROK_ID, "2102074819743453410"], "MOI NHAT truoc"
    assert calls == ["trang"], "da co tweet khop thi khong doc nguon cham/chet nua"


def test_default_sources_start_with_links_then_profile_page():
    names = [n for n, _ in arena_x.tweet_sources(["see https://x.com/arena/status/2102080801462689999 now"])]
    assert names[0] == f"link https://x.com/arena/status/{GROK_ID}"
    assert names[1] == "trang x.com/arena"


def test_loud_warning_when_no_source_readable():
    logs = []
    with mock.patch.object(arena_x, "tweet_sources", lambda extra_urls=(): [("a", list), ("b", list)]):
        assert arena_x.matching_tweets(["Grok 4.7"], in_log=logs.append) == []
    assert logs and "KHÔNG ĐỌC ĐƯỢC" in logs[0], logs


def test_status_urls_from_story_material():
    got = arena_x.status_urls(["https://twitter.com/lmarena_ai/status/2093015572212846673",
                               f"xem https://x.com/arena/status/{GROK_ID}?s=20 va lai https://x.com/arena/status/{GROK_ID}",
                               "https://x.com/someone/status/2093015572212846999", None])
    assert got == ["https://x.com/lmarena_ai/status/2093015572212846673", f"https://x.com/arena/status/{GROK_ID}"]


def test_download_uses_get_source_photo_only():
    gs = arena_x._get_source()
    seen = {}
    with mock.patch.object(gs, "save_x_photo", lambda url, out: seen.setdefault("u", url) and False):
        assert arena_x.download_image(f"https://x.com/arena/status/{GROK_ID}", Path("x.png")) is False
    assert seen["u"].endswith(GROK_ID)


HIT = [{"file_path": "a.png", "kind": arena_x.KIND, "source": "arena-x", "site": arena_x.SITE,
        "board": "Grok 4.7 by @SpaceXAI just dropped", "rank": None, "model": "grok 4.7",
        "url": f"https://x.com/arena/status/{GROK_ID}", "row": "b", "logo": None, "mentioned": True}]


def test_release_story_asks_arena_first_without_browser():
    """"xAI ra mắt Grok 4.7" KHONG phai tin xep hang theo regex, category rong, khong browser:
    van phai hoi @arena, va co anh thi bai thanh tin co XH."""
    from prepare import fallback_rounds
    asked = {}

    def fake_arena(models, out_dir, in_log, extra_urls=()):
        asked["models"], asked["urls"] = models, list(extra_urls)
        return HIT

    with mock.patch.object(fallback_rounds.ranking, "arena_first", fake_arena), \
         mock.patch.object(fallback_rounds.ranking, "find_and_capture_many",
                           side_effect=AssertionError("khong duoc chup trang bang khi da co anh @arena")):
        xhs, tin = fallback_rounds._capture_ranking(
            "xAI ra mắt Grok 4.7", {"title_en": ""}, {"summary": ""}, "https://x.com/arena/status/" + GROK_ID,
            {"category": ""}, {"article_text": ""}, Path("/tmp"), khong_browser=True)
    assert asked["models"] == ["Grok 4.7"], asked
    assert f"https://x.com/arena/status/{GROK_ID}" in asked["urls"], "link goc cua bai phai duoc dua vao"
    assert xhs == HIT and tin is True


def test_xiaomi_mimo_is_a_model_family():
    """Tin MiMo that tren may chu 22/09/2026 tach ra [] nen khong hoi @arena."""
    import ranking
    ms = ranking.extract_model("XiaomiMiMo/MiMo-V2.6-Pro-RL thả trọng số trên HuggingFace")
    assert ms and ms[0] == "MiMo-V2.6-Pro", ms
    assert arena_x.tweet_matches("MiMo-V2.6-Pro just landed @XiaomiMiMo back in the top 10 on Code Arena", ms)


def test_release_story_without_arena_keeps_old_path():
    from prepare import fallback_rounds
    with mock.patch.object(fallback_rounds.ranking, "arena_first", lambda *a, **k: []), \
         mock.patch.object(fallback_rounds.ranking, "find_and_capture_many",
                           side_effect=AssertionError("tin khong xep hang, khong chup")):
        xhs, tin = fallback_rounds._capture_ranking(
            "xAI ra mắt Grok 4.7", {"title_en": ""}, {"summary": ""}, "https://x",
            {"category": ""}, {"article_text": ""}, Path("/tmp"), khong_browser=False)
    assert xhs == [] and tin is False


def test_ranking_story_does_not_ask_x_twice():
    from prepare import fallback_rounds
    got = {}

    def fake_many(*a, **k):
        got.update(k)
        return []

    with mock.patch.object(fallback_rounds.ranking, "arena_first", lambda *a, **k: []), \
         mock.patch.object(fallback_rounds.ranking, "find_and_capture_many", fake_many):
        fallback_rounds._capture_ranking("Grok 4.7 lands #1 on LMArena", {"title_en": ""}, {"summary": ""},
                                         "https://x", {"category": "MODEL"}, {"article_text": ""},
                                         Path("/tmp"), khong_browser=False)
    assert got.get("arena_checked") is True


def test_xh_item_from_arena_is_not_described_as_circled_board():
    from prepare import fallback_rounds
    it = fallback_rounds._image_item_ranking(0, HIT[0])
    assert it["id"] == "XH" and "@arena" in it["alt"] and "khoanh" not in it["alt"]


def _logo_card():
    return {"id": "A1", "kind": "chart", "logo_card": True,
            "brand_match": {"kind": "logo", "model_logo": True}}


def test_ethan_arena_beats_logo_card_other_boards_do_not():
    import ethan_submit
    m = {"is_ranking_story": True, "ranking": {"kind": arena_x.KIND}}
    assert ethan_submit._must_use_ranking(m, _logo_card()), "anh @arena dung TRUOC the logo"
    m2 = {"is_ranking_story": True, "ranking": {"kind": "table"}}
    assert not ethan_submit._must_use_ranking(m2, _logo_card()), "bang chup trang khac: logo van truoc (LOW-337)"


def test_kite_cover_takes_arena_first():
    import kite_prepare
    m = {"draft_id": "x", "images": [
        {"id": "A1", "w": 1600, "h": 900, "kind": "photo", "relevant": True},
        {"id": "XH", "w": 4088, "h": 4088, "kind": "chart", "relevant": None,
         "ranking": {"kind": arena_x.KIND}}]}
    with mock.patch.object(kite_prepare, "_force_raw", lambda m: []):
        assert kite_prepare.figure_hero(m)["id"] == "XH"


def test_social_post_x_falls_back_to_get_source_photo():
    """crawl-queue tra media[] RONG cho post anh tren X — truoc ban va candidate_social ra 0 anh."""
    import tempfile
    import social_post
    gs = arena_x._get_source()
    out = {"tweet": {"text": GROK_TEXT, "author": {"handle": "arena"},
                     "url": f"https://x.com/arena/status/{GROK_ID}", "media": []}}
    run = mock.Mock(returncode=0, stdout=json.dumps(out), stderr="")

    def fake_photo(url, path):
        Path(path).write_bytes(b"\x89PNG\r\n\x1a\n")
        return True

    with tempfile.TemporaryDirectory() as d, \
         mock.patch.object(social_post.subprocess, "run", lambda *a, **k: run), \
         mock.patch.object(gs, "save_x_photo", fake_photo):
        r = social_post.read(f"https://x.com/arena/status/{GROK_ID}", tai_ve=Path(d))
        assert [m["file_path"] for m in r["media"]] == [str(Path(d) / "x_01.jpg")], r["media"]


def test_x_photos_only_for_x_hosts():
    import social_post
    gs = arena_x._get_source()
    with mock.patch.object(gs, "save_x_photo", side_effect=AssertionError("khong goi cho instagram")):
        assert social_post.x_photos("https://www.instagram.com/p/abc/", Path("/tmp")) == []


def test_get_source_finds_social_crawl_sibling():
    gs = arena_x._get_source()
    assert gs.SOCIAL_FETCH.exists(), gs.SOCIAL_FETCH
    assert gs.SOCIAL_FETCH == ROOT / "hermes/skills/social-crawl/scripts/social_fetch.py", \
        "duong ~/.claude/skills khong ton tai tren may chu — phai la skill anh em trong cung thu muc skills/"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
