#!/usr/bin/env python3
"""LOW-355 (22/09/2026) — ảnh GỐC từ chính tweet, không dùng ảnh báo chụp lại tweet.

Ông Chủ, bài Dre Grok 4.7: *"thay vì dùng hình cap từ tweet, sao bạn ko vào chính cái tweet được
retweet có hình gốc chất lượng cao mà phải đi lòng vòng vậy ?"*. Slide dùng A3 — ảnh Futu tự chụp
tweet Elon Musk (611x734, giao diện dịch tiếng Trung) — trong khi decrypt.co, cùng nằm trong nguồn
của draft, nhúng link x.com/elonmusk/status/2102071804495872374 mà get_source tải được biểu đồ
gốc 3062x1960. Engine dùng chung cho Dre/Ethan/Kite, nên luật này áp cho cả ba.

Mỗi test dưới FAIL trên code trước bản vá (không có `candidate_embedded_tweets`,
`drop_tweet_screenshots`, nhãn nguồn `embedded_tweet`).

Chay:  python tests/test_low355_tweet_original_image.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from prepare import source  # noqa: E402

ELON_QUOTE = "2102071804495872374"      # Elon trich @SpaceXAI, kem bieu do CursorBench 4.0
SPACEXAI = "2102069815225586149"        # bang gia/benchmark
ELON_OLD = "2099458047408013751"        # ~7 ngay truoc — con trong han
NOW = source.tweet_time(ELON_QUOTE) + 3600
_real = source.embedded_tweet_urls
OLD_30_DAYS = str(((int((NOW - 30 * 86400) * 1000) - source._TWITTER_EPOCH_MS) << 22))

# Rut gon tu HTML decrypt.co/378824 do ngay 22/09/2026 (embed twitter-tweet).
DECRYPT_HTML = (
    '<blockquote class="twitter-tweet"><p>Grok 4.7 is here</p>&mdash; SpaceXAI '
    f'<a href="https://twitter.com/SpaceXAI/status/{SPACEXAI}?ref_src=twsrc%5Etfw">Sep 21</a></blockquote>'
    f'<blockquote class="twitter-tweet"><a href="https://x.com/elonmusk/status/{ELON_QUOTE}">x</a></blockquote>'
    f'<a href="https://x.com/elonmusk/status/{ELON_OLD}">older</a>'
    f'<a href="https://twitter.com/decryptmedia/status/{OLD_30_DAYS}">archive</a>'
    '<a href="https://twitter.com/intent/tweet?text=share">share</a>'
)

FUTU_DESC = ("Ảnh chụp màn hình bài đăng mạng xã hội X của Elon Musk và SpaceXAI giới thiệu "
             "Grok 4.7 kèm biểu đồ CursorBench 4.0.")


def test_tweet_time_reads_snowflake():
    from datetime import datetime, timezone
    d = datetime.fromtimestamp(source.tweet_time(ELON_QUOTE), timezone.utc)
    assert (d.year, d.month, d.day) in ((2026, 9, 21), (2026, 9, 22)), d


def test_embedded_tweet_urls_newest_first_old_dropped():
    got = source.embedded_tweet_urls([DECRYPT_HTML], NOW)
    assert got == [f"https://x.com/elonmusk/status/{ELON_QUOTE}",
                   f"https://x.com/SpaceXAI/status/{SPACEXAI}",
                   f"https://x.com/elonmusk/status/{ELON_OLD}"], got


def test_embedded_tweet_urls_skips_source_post_and_dupes():
    got = source.embedded_tweet_urls([DECRYPT_HTML, DECRYPT_HTML], NOW,
                                     skip_urls=(f"https://x.com/elonmusk/status/{ELON_QUOTE}",))
    assert f"https://x.com/elonmusk/status/{ELON_QUOTE}" not in got, got
    assert len(got) == len(set(got)) == 2, got


def test_candidate_embedded_tweets_uses_get_source_path():
    """Anh lay qua `social_post.x_photos` (get_source, ban name=orig) — khong dung duong moi."""
    import article_images
    import social_post

    class R:
        status_code = 200
        text = DECRYPT_HTML
    hoi = []

    def fake_photos(url, out_dir, log):
        hoi.append(url)
        if "SpaceXAI" in url or ELON_QUOTE in url:
            return [{"type": "image", "url": url, "file_path": str(Path(out_dir) / "x_01.jpg")}]
        return []
    with tempfile.TemporaryDirectory() as d, \
         mock.patch.object(article_images, "_download", lambda u, t=15: R()), \
         mock.patch.object(social_post, "x_photos", fake_photos), \
         mock.patch.object(source, "embedded_tweet_urls",
                           lambda h, now, skip_urls=(): _real(h, NOW, skip_urls)):
        cands = source.candidate_embedded_tweets([{"url": "https://decrypt.co/378824/xai-launches-grok-4-7"}],
                                                 "https://siliconangle.com/x", Path(d))
    assert len(hoi) == 3, hoi
    assert [c["page_url"] for c in cands] == [f"https://x.com/elonmusk/status/{ELON_QUOTE}",
                                              f"https://x.com/SpaceXAI/status/{SPACEXAI}"], cands
    for c in cands:
        assert c["source"] == "embedded_tweet" and c["file_path"] == c["image_url"], c
        assert c["score"] > 45, "phai dung truoc anh bao (browser 45, og:image ~100 chi khi cuc net)"
    assert f"x_{ELON_QUOTE}" in cands[0]["file_path"], "moi tweet mot thu muc — x_photos luon ghi x_01.jpg"



def test_candidate_embedded_tweets_skips_social_pages_and_survives_errors():
    import article_images

    def boom(u, t=15):
        raise RuntimeError("mang hong")
    with tempfile.TemporaryDirectory() as d, mock.patch.object(article_images, "_download", boom):
        assert source.candidate_embedded_tweets([{"url": "https://decrypt.co/a"}], "https://x.com/a/status/1",
                                                Path(d)) == []


def test_gather_puts_embedded_tweets_into_candidates():
    """`_gather_and_download_image` (engine chung Dre/Ethan/Kite) phai hoi tweet nhung."""
    from prepare import fallback_rounds
    import arxiv_figures
    tweet = {"image_url": "/tmp/x_1/x_01.jpg", "file_path": "/tmp/x_1/x_01.jpg", "source": "embedded_tweet",
             "score": 90, "page_url": "https://x.com/elonmusk/status/1", "alt": ""}
    bao = {"image_url": "https://postimg.futunn.com/a.jpeg", "source": "browser", "score": 45}
    seen = {}

    def fake_download(cands, wd):
        seen["cands"] = cands
        return [{"id": "A1"}, {"id": "A2"}, {"id": "A3"}, {"id": "A4"}, {"id": "A5"}]
    with mock.patch.object(fallback_rounds, "candidate_embedded_tweets", lambda sp, link, wd, story="": [tweet]), \
         mock.patch.object(fallback_rounds, "candidate_social", lambda link, wd: []), \
         mock.patch.object(fallback_rounds, "candidate_static", lambda *a, **k: [bao]), \
         mock.patch.object(arxiv_figures, "candidate", lambda link, out: []), \
         mock.patch.object(fallback_rounds, "download_and_filter", fake_download):
        fallback_rounds._gather_and_download_image("t", "https://siliconangle.com/x", Path("/tmp/nope"),
                                                   {"title_en": ""}, [{"url": "https://decrypt.co/a"}],
                                                   {"cands": []}, Path("/tmp/nope"), [])
    assert seen["cands"][0] is tweet, [c["source"] for c in seen["cands"]]


# Bieu do CursorBench 4.0 THAT tai tu x.com/elonmusk/status/2102071804495872374 (thu nho 1000x640).
CHART = ROOT / "tests" / "golden" / "low355_cursorbench_chart.png"


def test_white_background_tweet_chart_survives_download_gate():
    """Chay that 22/09: bieu do goc 3062x1960 tu tweet bi `graphic_logo` loai (nen trang 69%)."""
    import article_images
    import role
    from PIL import Image
    from prepare import download_filter
    role.set_active_role("dre")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x_01.png"
        p.write_bytes(CHART.read_bytes())
        assert article_images._graphic(Image.open(p)), "anh mau phai dinh cong do hoa nhu anh that"
        with mock.patch.object(source, "embedded_tweet_urls", lambda h, now, skip_urls=(): [f"https://x.com/elonmusk/status/{ELON_QUOTE}"]), \
             mock.patch.object(article_images, "_download", lambda u, t=15: None), \
             mock.patch("social_post.x_photos", lambda u, out, log: [{"type": "image", "url": u, "file_path": str(p)}]):
            cands = source.candidate_embedded_tweets([{"url": "https://decrypt.co/a"}], "https://s.com/a", Path(d))
        kept = download_filter.download_and_filter(cands, Path(d) / "wd")
    assert [a["source"] for a in kept] == ["embedded_tweet"], kept


def _img(i, source, desc, relevant=True):
    return {"id": i, "source": source, "description": desc, "relevant": relevant,
            "uses": ["body"], "notes": [], "page_url": "https://news.futunn.com/p"}


def test_screenshot_dropped_when_original_exists():
    from prepare import vision
    anh = [_img("A1", "embedded_tweet", "Biểu đồ CursorBench 4.0 so sánh Grok 4.7"),
           _img("A3", "browser", FUTU_DESC)]
    assert vision.drop_tweet_screenshots(anh) == ["A3"]
    assert anh[1]["relevant"] is False and anh[1]["uses"] == []
    assert anh[1]["decisions"][-1]["rule"] == "tweet_screenshot_has_original"
    assert anh[0]["uses"] == ["body"], "anh goc khong bi dong vao"


def test_screenshot_kept_but_flagged_without_original():
    from prepare import vision
    anh = [_img("A3", "browser", FUTU_DESC)]
    assert vision.drop_tweet_screenshots(anh) == []
    assert anh[0]["uses"] == ["body"] and anh[0]["decisions"][-1]["outcome"] == "flag"


def test_regex_only_x_posts():
    """Mo ta that tren production 22/09: blog/bai dang thuong KHONG bi coi la tweet."""
    from prepare import vision
    r = vision.TWEET_SCREENSHOT_RE
    for yes in (FUTU_DESC,
                "Ảnh chụp màn hình bài đăng trên X của Andrew Clark về các API sắp lỗi thời trong React.",
                "Ảnh chụp màn hình một bài đăng X (Twitter) của tài khoản Artificial Analysis.",
                "Ảnh chụp màn hình tweet của Sam Altman.",
                # cung anh A3, lan chay that thu hai tren may chu (22/09): khong co chu "man hinh"
                "Ảnh chụp bài đăng X của Elon Musk trích dẫn SpaceXAI kèm biểu đồ đánh giá Grok 4.7.",
                "Ảnh chụp tweet của SpaceXAI."):
        assert r.search(yes), yes
    for no in ('Ảnh chụp màn hình bài đăng blog tiêu đề đỏ "What a time to be alive" về RubyGems.org.',
               "Ảnh chụp màn hình giao diện 1920 x 1080 của ứng dụng Grok.",
               "Ảnh chụp màn hình trang SpaceX-X1 launch.",
               "Biểu đồ so sánh Grok 4.7 trên nền tảng X.",
               "Ảnh chụp chân dung Elon Musk mặc áo thun xám trước phông nền X.",
               "Ảnh chụp bài đăng của CEO xAI trên blog SpaceX."):
        assert not r.search(no), no


def test_seen_image_runs_the_gate():
    from prepare import vision
    anh = [_img("A1", "embedded_tweet", "Biểu đồ"), _img("A3", "browser", FUTU_DESC)]
    with mock.patch.object(vision, "_classify_hide_whole", lambda a, wd, t: a):
        _, dung_duoc, _ = vision._seen_image(anh, {"title_en": "Grok 4.7"}, "Grok 4.7", Path("/tmp"))
    assert [a["id"] for a in dung_duoc] == ["A1"], dung_duoc


def test_source_label():
    import manifest_values
    assert manifest_values.source_label("embedded_tweet") == "tweet trong bài"


# ---- Ong Chu 22/09/2026: "chart goc tu tweet chinh chu duoc tinh la bang hop le" ----------
GROK_TITLE = "SpaceX phát hành Grok 4.7 SpaceX launches Grok 4.7 with long-horizon processing"


def test_official_handle_vendor_or_benchmark():
    ok = source.is_official_handle
    assert ok("SpaceXAI", GROK_TITLE) and ok("artificialanlys", GROK_TITLE)
    assert not ok("elonmusk", GROK_TITLE) and not ok("ericbalchunas", GROK_TITLE)
    assert ok("XiaomiMiMo", "XiaomiMiMo MiMo-V2.6-Pro-RL thả trọng số")
    assert ok("AIatMeta", "Meta ra mắt Llama 5")
    assert not ok("themetaverse", "Meta ra mắt Llama 5"), "ten ngan chi khop dau/cuoi handle"


def test_official_flag_reaches_manifest_and_provenance():
    """Co `official_tweet` di qua download_and_filter -> manifest + dau PNG `official_tweet`
    (is_ranking_image True -> mien cong chart y nhu anh xep hang, o MOI vai)."""
    import article_images
    import image_provenance
    import role
    from PIL import Image
    from prepare import download_filter
    role.set_active_role("ethan")
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "x_01.png"
        p.write_bytes(CHART.read_bytes())
        for handle, official in (("SpaceXAI", True), ("elonmusk", False)):
            url = f"https://x.com/{handle}/status/{ELON_QUOTE}"
            with mock.patch.object(source, "embedded_tweet_urls", lambda h, now, skip_urls=(): [url]),                  mock.patch.object(article_images, "_download", lambda u, t=15: None),                  mock.patch("social_post.x_photos", lambda u, out, log: [{"type": "image", "url": u, "file_path": str(p)}]):
                cands = source.candidate_embedded_tweets([{"url": "https://decrypt.co/a"}], "https://s.com/a",
                                                         Path(d), story=GROK_TITLE)
            kept = download_filter.download_and_filter(cands, Path(d) / f"wd_{handle}")
            assert kept[0]["official_tweet"] is official and kept[0]["tweet_handle"] == handle, kept
            assert image_provenance.is_ranking_image(Image.open(kept[0]["original_path"])) is official


def _official_chart(**k):
    return dict({"id": "A4", "source": "embedded_tweet", "official_tweet": True, "tweet_handle": "artificialanlys",
                 "subject_kind": "chart", "relevant": True, "kind": "chart", "cluttered": True,
                 "has_keywords": False, "empty_share": 0.7, "ratio": 1.1, "original_path": "/x"}, **k)


def test_ethan_model_story_accepts_official_chart_only():
    import image_rules_ethan
    assert image_rules_ethan.model_story_image_ok(_official_chart())
    assert not image_rules_ethan.model_story_image_ok(_official_chart(official_tweet=False))
    assert not image_rules_ethan.model_story_image_ok(_official_chart(relevant=False))
    assert not image_rules_ethan.model_story_image_ok(_official_chart(subject_kind="person"))


def test_official_chart_exempt_from_clutter_and_empty_gates():
    import submit_common
    assert submit_common.check_empty_image(_official_chart(), "image", 0.5) == []
    assert submit_common.check_empty_image(_official_chart(official_tweet=False), "image", 0.5),         "anh tweet nguoi ngoai van chiu cong anh trong"
    anh = {"A4": _official_chart()}
    assert submit_common.check_image_fall(anh, {"A4": "image"}, {"image_role": "ethan"}) == []


def test_needs_ranking_image_keeps_arena_first():
    import arena_x
    import submit_common
    tbench = {"is_ranking_story": True, "ranking": {"kind": "table"}}
    arena = {"is_ranking_story": True, "ranking": {"kind": arena_x.KIND}}
    assert not submit_common.needs_ranking_image(tbench, _official_chart()), "bang chinh chu ngang bang engine chup"
    assert submit_common.needs_ranking_image(arena, _official_chart()), "@arena van dung dau"
    assert submit_common.needs_ranking_image(tbench, _official_chart(official_tweet=False))


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
