#!/usr/bin/env python3
"""LOW-21 (11/09/2026) — Dre bi chan tin DeepSeek-V4.1-Flash (LiveBench #6) vi
"thieu anh" trong khi trang cong bo cua DeepSeek co 4 chart benchmark.

Ong Chu: *"khi lam carousel tu mot topic goc, phai tim tat ca anh lien quan chu
khong phai chi tim anh trong nguon topic, dac biet la nhung thong tin lien quan
toi benchmark cua model"*. Lan thu ba cua cung hinh dang loi (LOW-10, LOW-12).

Ba loi do duoc, moi loi mot nhom test FAIL TREN CODE CU:
  1. `article_sources._name_own_no_mark` xoa gach noi truoc khi tach tu -> ten model
     `deepseek-v4.1-flash-max` vo, mat chu `deepseek`, truy van Bing ra 0 bao.
  2. `manifest`/`nop_chung` doi `kieu == "chup"` — gia tri xep_hang chua bao gio
     phat ra; moi test cu stub "chup" nen xanh gia. Cong o muc MA NGUON: tap
     `kieu` xep_hang phat ra phai duoc nguoi doc coi la "chup that".
  3. Khong co duong nao toi trang cong bo chinh chu cua model
     (`image_brand.announcement_page` + `fallback_rounds._extra_announcement_page` +
     `browser_pass` uu tien trang do voi tran 4 anh).

Chay:  venv/bin/python tests/test_tim_tat_ca_anh_lien_quan.py
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
import chuan_bi.manifest as manifest                          # noqa: E402
import chuan_bi.fallback_rounds as fallback_rounds                            # noqa: E402
import chuan_bi.browser as browser                            # noqa: E402

TIEU_DE = "deepseek-v4.1-flash-max vào bảng LiveBench ở #6, 81.4 điểm, kém đầu bảng 2.4"


# ------------------------------------------------ 1. truy van giu ten model
def test_ten_rieng_khong_dau_giu_token_gach_noi():
    en = article_sources._name_own_no_mark(TIEU_DE)
    assert "deepseek-v4.1-flash-max" in en.split(), en
    assert "deepseek" in en.lower(), f"mat ten hang: {en!r}"


def test_tieu_de_tim_khong_mat_ten_hang_khi_og_title_rong():
    """Dung canh that: og:title cua livebench.ai la 'LiveBench' (bi bo vi < 4 tu),
    Google News hong -> roi ve ten rieng. Ket qua PHAI con 'deepseek'."""
    cu = article_sources._title_page, article_sources._download
    article_sources._title_page = lambda url: ""

    def _hong(*a, **k):
        raise OSError("khong mang trong test")
    article_sources._download = _hong
    try:
        en = article_sources.title_find(TIEU_DE, "https://livebench.ai/")
    finally:
        article_sources._title_page, article_sources._download = cu
    assert "deepseek" in en.lower(), f"truy van khong co ten hang/model: {en!r}"


def test_truy_van_bing_thu_ban_bo_gach_truoc():
    """Do 11/09: 'deepseek-v4.1-flash-max ...' -> 1 bai, 'deepseek v4.1 flash max' -> 6."""
    qs = article_sources._query_bing("deepseek-v4.1-flash-max LiveBench #6 81.4")
    assert qs and "-" not in qs[0], qs
    assert qs[0].lower().startswith("deepseek v4.1 flash"), qs
    assert any("-" in q for q in qs), "van phai giu ban co gach de khong mat ket qua cu"


# ------------------------------------------------ 2. kieu "chup that" thong nhat
def _kieu_xep_hang_phat_ra() -> set:
    """Moi gia tri chuoi gan cho khoa "kieu" trong dict literal cua ranking.py."""
    cay = ast.parse((ROOT / "ranking.py").read_text(encoding="utf-8"))
    ra = set()
    for n in ast.walk(cay):
        if isinstance(n, ast.Dict):
            for k, v in zip(n.keys, n.values):
                if isinstance(k, ast.Constant) and k.value == "kieu" \
                        and isinstance(v, ast.Constant) and isinstance(v.value, str):
                    ra.add(v.value)
    return ra


def test_moi_kieu_xep_hang_phat_ra_deu_duoc_nguoi_doc_hieu():
    phat = _kieu_xep_hang_phat_ra()
    assert phat, "khong doc duoc kieu nao tu ranking.py — test hong"
    assert "the" in phat, "the du phong phai con"
    la = {k for k in phat if k != "the"}
    assert la and la <= ranking.KIND_CAPTURE, f"xep_hang phat {la} ma KIND_CAPTURE chi biet {set(ranking.KIND_CAPTURE)}"
    assert "chup" not in phat and "chup" not in ranking.KIND_CAPTURE, \
        "'chup' la gia tri ma stub test tung bia ra, khong duoc quay lai"
    for k in la:
        assert ranking.is_capture(k), k
    assert not ranking.is_capture("the") and not ranking.is_capture(None)


def test_brief_va_cong_nop_coi_bang_chup_that_la_bat_buoc():
    m = {"tin_xep_hang": True,
         "xep_hang": {"site": "LIVEBENCH.AI", "bang": "LiveBench", "model": "deepseek-v4.1-flash-max",
                      "hang": 6, "kieu": "bang", "duoc_nhac": True}}
    dong = manifest.ranking_brief_line(m, "bìa ", "dre_submit")
    assert "BẮT BUỘC" in dong and "THẺ DỰ PHÒNG" not in dong, dong
    assert submit_common.needs_ranking_image(m, {"ma": "A1"}), "bang chup that ma cong khong ep"
    assert not submit_common.needs_ranking_image(m, {"ma": "XH", "xep_hang": m["xep_hang"]})
    m["xep_hang"]["kieu"] = "the"
    assert "THẺ DỰ PHÒNG" in manifest.ranking_brief_line(m, "bìa ", "dre_submit")
    assert not submit_common.needs_ranking_image(m, {"ma": "A1"})


def test_nguoi_doc_kieu_khong_so_chuoi_tay():
    """Cong o muc ma nguon: hai noi doc phai hoi ranking.is_capture, khong so chuoi."""
    for tep in ("chuan_bi/manifest.py", "submit_common.py"):
        src = (ROOT / tep).read_text(encoding="utf-8")
        assert 'get("kieu") == "chup"' not in src and 'get("kieu") != "chup"' not in src, tep
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


def _voi_stub(website, tai):
    cu = th.vendor_website, th._download_html
    th.vendor_website = website
    th._download_html = tai
    return cu


def _phuc_hoi(cu):
    th.vendor_website, th._download_html = cu


def test_khoa_model_bo_hau_to_effort_va_giu_toi_thieu_hai_manh():
    assert th._lock_model(["deepseek-v4.1-flash-max"]) == ["deepseek-v4-1-flash", "deepseek-v4-1", "deepseek-v4"]
    assert th._lock_model(ranking.extract_model("GPT-6 Astra (max) 55 điểm"))[0] == "gpt-6-astra"
    assert th._lock_model([]) == []


def test_trang_cong_bo_khop_bai_khong_khop_anh_bia():
    goi = []

    def _tai(url, timeout=15, feed=False):
        goi.append(url)
        return HTML_NEWS if url.endswith("/news/") and not feed else ""
    cu = _voi_stub(lambda hang: "https://vi.du", _tai)
    try:
        kq = th.announcement_page({"khoa": "deepseek", "hang": "DeepSeek"},
                              ranking.extract_model(TIEU_DE))
    finally:
        _phuc_hoi(cu)
    assert kq and kq["url"] == "https://vi.du/en/news/deepseek-v4-1-flash/", kq
    assert kq["loai"] == "công bố" and kq["toa_soan"] == "https://vi.du"
    assert len(goi) == 1, f"khop o /news/ ma van fetch tiep: {goi}"


def test_trang_cong_bo_roi_ve_rss_khi_html_bi_chan():
    def _tai(url, timeout=15, feed=False):
        return RSS if feed and url.endswith("/news/rss.xml") else ""
    cu = _voi_stub(lambda hang: "https://vi.du", _tai)
    try:
        kq = th.announcement_page({"khoa": "openai", "hang": "OpenAI"},
                              ranking.extract_model("GPT-6 Astra dẫn đầu bảng"))
    finally:
        _phuc_hoi(cu)
    assert kq and kq["url"] == "https://vi.du/index/gpt-6-astra-next-generation-work", kq


def test_trang_cong_bo_khong_hoi_gi_khi_khong_co_model_hay_website():
    goi = []
    cu = _voi_stub(lambda hang: goi.append(("web", hang)) or "", lambda *a, **k: goi.append("tai") or "")
    try:
        assert th.announcement_page({"khoa": "samsung", "hang": "Samsung"}, []) is None
        assert goi == [], f"khong co model ma van hoi: {goi}"
        assert th.announcement_page({"khoa": "x", "hang": "X"}, ["GPT-6"]) is None
        assert "tai" not in goi, "khong co website ma van fetch"
    finally:
        _phuc_hoi(cu)


def test_them_trang_cong_bo_ghi_vao_nguon_json_mot_lan():
    cu = th.announcement_page, th.vendors_in_story
    th.announcement_page = lambda h, models: {"url": "https://vi.du/news/deepseek-v4-1-flash/",
                                          "loai": "công bố", "tieu_de": "", "toa_soan": "https://vi.du"}
    th.vendors_in_story = lambda td, tt="": [{"khoa": "deepseek", "hang": "DeepSeek"}]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "nguon_d1.json"
            nguon = {"tieu_de_en": "", "trang": [{"url": "https://livebench.ai/", "loai": "gốc"}]}
            trang = fallback_rounds._extra_announcement_page(nguon, p, nguon["trang"], TIEU_DE, "")
            assert [t["loai"] for t in trang] == ["gốc", "công bố"], trang
            tren_dia = json.loads(p.read_text(encoding="utf-8"))
            assert tren_dia["trang"][-1]["loai"] == "công bố", "phai ghi nguon json cho Miles cung dung"
            trang2 = fallback_rounds._extra_announcement_page(nguon, p, trang, TIEU_DE, "")
            assert len(trang2) == 2, "goi lan hai khong duoc them trung"
            # Tin khong nhac model nao: khong dong toi nguon
            nguon3 = {"tieu_de_en": "", "trang": [{"url": "https://vi.du/a", "loai": "gốc"}]}
            assert fallback_rounds._extra_announcement_page(nguon3, p, nguon3["trang"],
                                               "Samsung opens new chip plant", "") == nguon3["trang"]
    finally:
        th.announcement_page, th.vendors_in_story = cu


class _PageGia:
    def __init__(self, so_anh):
        self.so_anh = so_anh

    def evaluate(self, js):
        return [{"src": f"http://vi.du/{i}.png", "alt": "", "w": 1600, "h": 900}
                for i in range(self.so_anh)]


def test_browser_tran_anh_trang_cong_bo_bang_bai_goc():
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
    src = (ROOT / "chuan_bi" / "browser.py").read_text(encoding="utf-8")
    assert 'tran=4 if t.get("loai") == "công bố"' in src, "browser_pass phai cap tran 4 cho trang cong bo"
    assert 'khac.sort(key=lambda t: t.get("loai") != "công bố")' in src, "trang cong bo phai duoc mo truoc"


def test_engine_noi_trang_cong_bo_truoc_browser():
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
