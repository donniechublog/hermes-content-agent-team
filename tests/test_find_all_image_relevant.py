#!/usr/bin/env python3
"""LOW-21 (11/09/2026) — Dre bi chan tin DeepSeek-V4.1-Flash (LiveBench #6) vi
"thieu anh" trong khi trang cong bo cua DeepSeek co 4 chart benchmark.

Ong Chu: *"khi lam carousel tu mot topic goc, phai tim tat ca anh lien quan chu
khong phai chi tim anh trong nguon topic, dac biet la nhung thong tin lien quan
toi benchmark cua model"*. Lan thu ba cua cung hinh dang loi (LOW-10, LOW-12).

Ba loi do duoc, moi loi mot nhom test FAIL TREN CODE CU:
  1. `article_sources._name_own_no_mark` xoa gach noi truoc khi tach tu -> ten model
     `deepseek-v4.1-flash-max` vo, mat chu `deepseek`, truy van Bing ra 0 bao.
  2. `manifest`/`submit_common` doi `kieu == "chup"` — gia tri xep_hang chua bao gio
     phat ra; moi test cu stub "chup" nen xanh gia. Cong o muc MA NGUON: tap
     `kind` xep_hang phat ra phai duoc nguoi doc coi la "chup that".
  3. Khong co duong nao toi trang cong bo chinh chu cua model
     (`image_brand.announcement_page` + `fallback_rounds._extra_announcement_page` +
     `browser_pass` uu tien trang do voi tran 4 anh).

Chay:  venv/bin/python tests/test_find_all_image_relevant.py
"""
import ast
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import article_sources                                              # noqa: E402
import ranking                                               # noqa: E402
import submit_common                                              # noqa: E402
import image_brand as th                                  # noqa: E402
import prepare.manifest as manifest                          # noqa: E402
import prepare.fallback_rounds as fallback_rounds                            # noqa: E402
import prepare.browser as browser                            # noqa: E402

TIEU_DE = "deepseek-v4.1-flash-max vào bảng LiveBench ở #6, 81.4 điểm, kém đầu bảng 2.4"


# ------------------------------------------------ 1. truy van giu ten model
def test_name_own_no_mark_keep_token_dash_say():
    en = article_sources._name_own_no_mark(TIEU_DE)
    assert "deepseek-v4.1-flash-max" in en.split(), en
    assert "deepseek" in en.lower(), f"mat ten hang: {en!r}"


def test_title_find_no_face_name_rank_when_og_title_empty():
    """Dung canh that: og:title cua livebench.ai la 'LiveBench' (bi bo vi < 4 tu),
    Google News hong -> roi ve ten rieng. Ket qua PHAI con 'deepseek'."""
    cu = article_sources._title_page, article_sources._download
    article_sources._title_page = lambda url, gnews_url="": ""

    def _hong(*a, **k):
        raise OSError("khong mang trong test")
    article_sources._download = _hong
    try:
        en = article_sources.title_find(TIEU_DE, "https://livebench.ai/")
    finally:
        article_sources._title_page, article_sources._download = cu
    assert "deepseek" in en.lower(), f"truy van khong co ten hang/model: {en!r}"


def test_query_bing_try_copy_drop_dash_before():
    """Do 11/09: 'deepseek-v4.1-flash-max ...' -> 1 bai, 'deepseek v4.1 flash max' -> 6."""
    qs = article_sources._query_bing("deepseek-v4.1-flash-max LiveBench #6 81.4")
    assert qs and "-" not in qs[0], qs
    assert qs[0].lower().startswith("deepseek v4.1 flash"), qs
    assert any("-" in q for q in qs), "van phai giu ban co gach de khong mat ket qua cu"


# ------------------------------------------------ 2. kieu "chup that" thong nhat
def _kind_ranking_emit_out() -> set:
    """Moi gia tri chuoi gan cho khoa "kind" trong dict literal cua ranking.py."""
    cay = ast.parse((ROOT / "ranking.py").read_text(encoding="utf-8"))
    ra = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                if isinstance(k, ast.Constant) and k.value == "kind" \
                        and isinstance(v, ast.Constant) and isinstance(v.value, str):
                    ra.add(v.value)
    return ra


def test_new_kind_ranking_emit_out_all_ok_reader_understand():
    phat = _kind_ranking_emit_out()
    assert phat, "khong doc duoc kieu nao tu ranking.py — test hong"
    assert "card" in phat, "the du phong phai con"
    la = {k for k in phat if k != "card"}
    assert la and la <= ranking.KIND_CAPTURE, f"xep_hang phat {la} ma KIND_CAPTURE chi biet {set(ranking.KIND_CAPTURE)}"
    assert "chup" not in phat and "chup" not in ranking.KIND_CAPTURE, \
        "'chup' la gia tri ma stub test tung bia ra, khong duoc quay lai"
    for k in la:
        assert ranking.is_capture(k), k
    assert not ranking.is_capture("card") and not ranking.is_capture(None)


def test_brief_and_gate_submit_regard_board_capture_real_is_required():
    m = {"is_ranking_story": True,
         "ranking": {"site": "LIVEBENCH.AI", "board": "LiveBench", "model": "deepseek-v4.1-flash-max",
                     "rank": 6, "kind": "table", "mentioned": True}}
    dong = manifest.ranking_brief_line(m, "bìa ", "dre_submit")
    assert "BẮT BUỘC" in dong and "THẺ DỰ PHÒNG" not in dong, dong
    assert submit_common.needs_ranking_image(m, {"id": "A1"}), "bang chup that ma cong khong ep"
    assert not submit_common.needs_ranking_image(m, {"id": "XH", "ranking": m["ranking"]})
    m["ranking"]["kind"] = "card"
    assert "THẺ DỰ PHÒNG" in manifest.ranking_brief_line(m, "bìa ", "dre_submit")
    assert not submit_common.needs_ranking_image(m, {"id": "A1"})


def test_reader_kind_no_count_string_manual():
    """Cong o muc ma nguon: hai noi doc phai hoi ranking.is_capture, khong so chuoi."""
    for tep in ("prepare/manifest.py", "submit_common.py"):
        src = (ROOT / tep).read_text(encoding="utf-8")
        assert 'get("kieu") == "chup"' not in src and 'get("kieu") != "chup"' not in src, tep
        assert 'get("kind") == "chup"' not in src and 'get("kind") != "chup"' not in src, tep
        assert "ranking.is_capture(" in src, f"{tep}: phai dung ranking.is_capture"


# ------------------------------------------------ 3. trang cong bo chinh chu
HTML_NEWS = """<html><head>
<link rel="preload" as="image" href="/images/blog/deepseek-v4-1-flash/cover.webp">
</head><body>
<a href="/en/news/">News</a>
<a href="/en/news/deepseek-v3-2/">V3.2</a>
<a href="/en/news/deepseek-v4-1-flash/">Introducing DeepSeek-V4.1-Flash</a>
<a href="https://huggingface.co/deepseek-ai/DeepSeek-V4.1-Flash">HF</a>
</body></html>"""
RSS = """<rss><channel><item><title>GPT-6 Astra</title>
<link>https://vi.du/index/gpt-6-astra-next-generation-work</link></item></channel></rss>"""


def _with_stub(website, tai):
    cu = th.vendor_website, th._download_html
    th.vendor_website = website
    th._download_html = tai
    return cu


def _restore(cu):
    th.vendor_website, th._download_html = cu


def test_lock_model_drop_suffix_effort_and_keep_min_two_fragment():
    assert th._lock_model(["deepseek-v4.1-flash-max"]) == ["deepseek-v4-1-flash", "deepseek-v4-1", "deepseek-v4"]
    assert th._lock_model(ranking.extract_model("GPT-6 Astra (max) 55 điểm"))[0] == "gpt-6-astra"
    assert th._lock_model([]) == []


def test_announcement_page_match_article_no_match_image_cover():
    goi = []

    def _tai(url, timeout=15, feed=False):
        goi.append(url)
        return HTML_NEWS if url.endswith("/news/") and not feed else ""
    cu = _with_stub(lambda hang: "https://vi.du", _tai)
    try:
        kq = th.announcement_page({"key": "deepseek", "company": "DeepSeek"},
                              ranking.extract_model(TIEU_DE))
    finally:
        _restore(cu)
    assert kq and kq["url"] == "https://vi.du/en/news/deepseek-v4-1-flash/", kq
    assert kq["kind"] == "announcement" and kq["outlet_url"] == "https://vi.du"
    assert len(goi) == 1, f"khop o /news/ ma van fetch tiep: {goi}"


def test_announcement_page_fall_about_rss_when_html_got_block():
    def _tai(url, timeout=15, feed=False):
        return RSS if feed and url.endswith("/news/rss.xml") else ""
    cu = _with_stub(lambda hang: "https://vi.du", _tai)
    try:
        kq = th.announcement_page({"key": "openai", "company": "OpenAI"},
                              ranking.extract_model("GPT-6 Astra dẫn đầu bảng"))
    finally:
        _restore(cu)
    assert kq and kq["url"] == "https://vi.du/index/gpt-6-astra-next-generation-work", kq


def test_announcement_page_no_ask_what_when_no_has_model_or_website():
    goi = []
    cu = _with_stub(lambda hang: goi.append(("web", hang)) or "", lambda *a, **k: goi.append("tai") or "")
    try:
        assert th.announcement_page({"key": "samsung", "company": "Samsung"}, []) is None
        assert goi == [], f"khong co model ma van hoi: {goi}"
        assert th.announcement_page({"key": "x", "company": "X"}, ["GPT-6"]) is None
        assert "tai" not in goi, "khong co website ma van fetch"
    finally:
        _restore(cu)


def test_extra_announcement_page_write_into_source_json_one_attempt():
    cu = th.announcement_page, th.vendors_in_story
    th.announcement_page = lambda h, models: {"url": "https://vi.du/news/deepseek-v4-1-flash/",
                                          "kind": "announcement", "title": "", "outlet_url": "https://vi.du"}
    th.vendors_in_story = lambda td, tt="": [{"key": "deepseek", "company": "DeepSeek"}]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "article_source_d1.json"
            nguon = {"title_en": "", "pages": [{"url": "https://livebench.ai/", "kind": "article"}]}
            trang = fallback_rounds._extra_announcement_page(nguon, p, nguon["pages"], TIEU_DE, "")
            assert [t["kind"] for t in trang] == ["article", "announcement"], trang
            tren_dia = json.loads(p.read_text(encoding="utf-8"))
            assert tren_dia["pages"][-1]["kind"] == "announcement", "phai ghi nguon json cho Miles cung dung"
            trang2 = fallback_rounds._extra_announcement_page(nguon, p, trang, TIEU_DE, "")
            assert len(trang2) == 2, "goi lan hai khong duoc them trung"
            # Tin khong nhac model nao: khong dong toi nguon
            nguon3 = {"title_en": "", "pages": [{"url": "https://vi.du/a", "kind": "article"}]}
            assert fallback_rounds._extra_announcement_page(nguon3, p, nguon3["pages"],
                                               "Samsung opens new chip plant", "") == nguon3["pages"]
    finally:
        th.announcement_page, th.vendors_in_story = cu


class _PageGia:
    def __init__(self, so_anh):
        self.so_anh = so_anh

    def evaluate(self, js):
        return [{"src": f"http://vi.du/{i}.png", "alt": "", "w": 1600, "h": 900}
                for i in range(self.so_anh)]


def test_browser_ceiling_image_announcement_page_board_article_original():
    """Bao khac <= 3 anh, nhung trang cong bo chinh chu duoc 4 nhu bai goc —
    4 chart benchmark cua DeepSeek ma cat con 3 la mat mot tam."""
    JS = {"IMG": ""}
    with tempfile.TemporaryDirectory() as tmp:
        ra = {"cands": []}
        browser._take_image_page(_PageGia(6), "http://vi.du", 1, Path(tmp), ra, JS, chup_fig=False)
        assert len(ra["cands"]) == 3
        ra = {"cands": []}
        browser._take_image_page(_PageGia(6), "http://vi.du", 1, Path(tmp), ra, JS, chup_fig=False, tran=4)
        assert len(ra["cands"]) == 4
    src = (ROOT / "prepare" / "browser.py").read_text(encoding="utf-8")
    assert 'tran=4 if t.get("kind") == "announcement"' in src, "browser_pass phai cap tran 4 cho trang cong bo"
    assert 'khac.sort(key=lambda t: t.get("kind") != "announcement")' in src, "trang cong bo phai duoc mo truoc"


def test_engine_say_announcement_page_before_browser():
    """Cong o muc ma nguon: prepare_article() goi _extra_announcement_page giua _supplement_source
    va _take_from_browser — de browser ghe trang do lay chart."""
    src = (ROOT / "image_prepare.py").read_text(encoding="utf-8")
    a, b, c = src.index("_supplement_source(nguon"), src.index("_extra_announcement_page(nguon"), src.index("_take_from_browser(trang")
    assert a < b < c, "thu tu phai la bo_sung_nguon -> them_trang_cong_bo -> lay_tu_browser"


if __name__ == "__main__":
    tests = [(k, v) for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    qua = 0
    for ten, f in tests:
        try:
            f()
            qua += 1
            print(f"  ok  {ten}")
        except Exception as e:                               # noqa: BLE001
            print(f"FAIL  {ten}: {type(e).__name__}: {e}")
    print(f"{qua}/{len(tests)} test qua")
    sys.exit(0 if qua == len(tests) else 1)
