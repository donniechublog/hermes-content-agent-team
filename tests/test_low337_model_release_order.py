#!/usr/bin/env python3
"""LOW-337 (Ông Chủ 23/09/2026): tin RA MẮT model là dòng tin riêng.

*"Model release là dòng tin khác với tin thời sự có model là chủ thể, nên thứ tự ưu
tiên là: @arena → chart/score công bố (AA, tbench…) → logo → founder"*.

Bài "GPT-6 Sol and Luna" (23/09) ra deck dùng logo OpenAI + chân dung Sam Altman,
trong khi trang công bố có 8 biểu đồ benchmark. Hai gốc, mỗi phần có ví dụ SAI-PHẢI-
CHẶN đi kèm ĐÚNG-PHẢI-QUA:

  1. Bảng thứ tự: `MODEL` đặt logo đầu (LOW-337 21/09, cho tin thời sự có model là chủ
     thể — Qwen-Image-2.1 ra ảnh toà nhà Alibaba). Tin RA MẮT phải đi bảng riêng.
  2. Bóc hình: `prepare/browser.py` chỉ nhận `<figure>` khi bên trong có canvas/svg/
     table. Trang công bố GPT-6 vẽ biểu đồ BẰNG DIV (đo thật 23/09 ở khung 1600px:
     8 figure 1376x497–800, không có svg lúc chưa cuộn tới), nên cả 8 bị bỏ; trần 4
     ảnh lại bị 2 bảng nhỏ + một canvas nền 1585x920 chiếm chỗ.

Chạy:  venv/bin/python tests/test_low337_model_release_order.py
"""
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import story_type as st  # noqa: E402

RA_MAT = ("OpenAI introduces GPT-6 Sol and Luna",
          "Alibaba ra mắt Qwen-Image-2.1",
          "xAI tung Grok 4.7: quy mô 2,1 nghìn tỷ tham số",
          "Google launches Gemini 4 Flash",
          "Mistral unveils Magistral 2",
          "DeepSeek phát hành V4.1 Flash")
THOI_SU = ("Pentagon says overreliance on AI contributed to missile strike",
           "Google confirms Gemini models are deprecated",
           "Nhân viên OpenAI rời đi sau tranh cãi về GPT-6",
           "Claude Opus 5 bị phát hiện đọc sai ảnh y tế")


# ---------------------------------------------------------------- 1. bảng thứ tự
def test_release_titles_are_detected():
    for t in RA_MAT:
        assert st.is_model_release("MODEL", t), t


def test_news_about_a_model_is_not_a_release():
    for t in THOI_SU:
        assert not st.is_model_release("MODEL", t), t


def test_release_needs_a_model_story_type():
    """Tin kinh doanh có chữ "ra mắt" (gói cước, cửa hàng) KHÔNG đổi bảng."""
    assert not st.is_model_release("BUSINESS", "OpenAI ra mắt gói doanh nghiệp")
    assert st.order_image("BUSINESS", "OpenAI ra mắt gói doanh nghiệp")[0] == "logo"


def test_release_order_is_chart_first():
    ra = st.order_image("MODEL", RA_MAT[0])
    assert ra[:4] == ("ranking", "announcement_chart", "logo", "founder"), ra


def test_news_order_keeps_logo_first():
    """LOW-337 (21/09) vẫn đứng cho tin thời sự: logo CỦA MODEL trước toà nhà hãng mẹ."""
    assert st.order_image("MODEL", THOI_SU[0])[0] == "logo"


def test_benchmark_table_unchanged():
    assert st.order_image("BENCHMARK", "Grok 4.7 vào top 6 Terminal-Bench")[:2] == \
        ("ranking", "announcement_chart")


def test_score_flips_chart_above_logo_only_for_release():
    logo_rm = st.score_by_type("MODEL", "logo", RA_MAT[0])
    chart_rm = st.score_by_type("MODEL", "announcement_chart", RA_MAT[0])
    assert chart_rm > logo_rm, (chart_rm, logo_rm)
    logo_ts = st.score_by_type("MODEL", "logo", THOI_SU[0])
    chart_ts = st.score_by_type("MODEL", "announcement_chart", THOI_SU[0])
    assert logo_ts > chart_ts, (logo_ts, chart_ts)


def test_ranking_story_type_still_true_both_ways():
    """Cả hai dòng tin đều là tin xếp hạng (ranking nằm trong 2 vị trí đầu) — cổng
    `_capture_ranking` không được hẹp lại vì bản vá này."""
    assert st.is_ranking_story_type("MODEL", RA_MAT[0])
    assert st.is_ranking_story_type("MODEL", THOI_SU[0])


def test_brief_line_says_release():
    dong = st.line_brief({"category": "MODEL", "title": RA_MAT[0]})[0]
    assert "RA MẮT" in dong, dong
    assert dong.index("bảng") > 0
    dong2 = st.line_brief({"category": "MODEL", "title": THOI_SU[0]})[0]
    assert "RA MẮT" not in dong2, dong2


def test_order_without_title_keeps_old_table():
    """Nơi gọi chưa truyền tiêu đề thì hành vi y như trước bản vá."""
    assert st.order_image("MODEL") == st.BOARD_IMAGE_BY_TYPE["MODEL"]


# ---------------------------------------------------------------- 2. bóc hình
def _js_fig() -> str:
    import prepare.browser as br
    return br._js_browser()["FIG"]


def test_figure_no_longer_needs_svg_inside():
    js = _js_fig()
    assert "el.querySelector('img')" in js, js[-900:]
    assert "canvas, svg, table, figcaption" in js, js[-900:]


def test_figure_is_scanned_before_table_and_canvas():
    js = _js_fig()
    i = js.index("['figure', 'table', 'canvas', 'svg']")
    assert i > 0, js[-900:]


def test_width_threshold_fits_a_narrow_article_column():
    js = _js_fig()
    assert "wMin = 480" in js and "'table') ? 120 : 300" in js, js[-900:]


def test_nested_elements_are_not_captured_twice():
    js = _js_fig()
    assert "daLay.some" in js, js[-900:]


# ---------------------------------------------------------------- 3. bảng cho tin ra mắt
def test_release_story_gets_every_board():
    """Ông Chủ 23/09/2026: *"với model release thì bảng nào chả dùng? chỉ tin tức liên
    quan tới model thì ko ưu tiên dùng bảng thôi"*. LOW-389 thu hẹp registry ảnh về
    arena — đó là luật cho tin THƯỜNG, và câu "AA chỉ để tăng tính confirm" là luật của
    vai RESEARCH, không phải của designer."""
    import ranking
    ds = ranking.suggest_sources(RA_MAT[0], ra_mat=True)
    du = [n["id"] for n in ds if ranking.source_proves_story(n)]
    assert du and all(x.startswith("release:") for x in du), du
    assert "release:intelligence" in du, du


def test_normal_model_news_still_arena_only():
    """LOW-389 giữ nguyên cho tin thời sự: không bảng nào đủ tư cách nếu bài không nhắc."""
    import ranking
    ds = ranking.suggest_sources(THOI_SU[1])
    assert [n["id"] for n in ds if ranking.source_proves_story(n)] == []
    assert all(not n.get("release_board") for n in ds)


def test_release_boards_read_the_registry_not_a_second_copy():
    """Link bảng chỉ được khai MỘT nơi (`model_boards`) — hai bản là kiểu lỗi mà chính
    model_boards.py sinh ra để chặn."""
    import model_boards
    import ranking
    link = {b.khoa: b.link for b in model_boards.BOARD}
    for n in ranking.release_boards():
        assert n["url"] == link[n["id"].split(":", 1)[1]], n


def test_arena_still_first_for_release():
    import ranking
    ds = ranking.suggest_sources(RA_MAT[0], ra_mat=True)
    assert ds[0]["id"].startswith("arena-"), ds[0]["id"]
    assert [n["id"] for n in ds][-3:] == ["release:intelligence", "release:tbench", "release:swebench"]


def test_capture_round_does_not_stop_at_arena_for_release():
    """Bài GPT-6 có ảnh @arena nên vòng chụp dừng ngay ở đó — không bảng nào khác được
    thử. Nay tin RA MẮT phải đi tiếp; tin thường vẫn dừng."""
    import inspect

    from prepare import fallback_rounds
    src = inspect.getsource(fallback_rounds._capture_ranking)
    assert "if not ra_mat:" in src and "return arena, True" in src, src[-1200:]
    assert "ra_mat=ra_mat" in src, src[-1200:]


def test_board_row_must_carry_the_variant_name():
    """Đo thật 23/09: bài "GPT-6 Sol and Luna", bảng Terminal-Bench không có hàng Sol
    nên engine tụt xuống tên lỏng "GPT-6" và khoanh **GPT-6 Astra** — một model KHÁC.
    Cổng LOW-338 chỉ xét SỐ phiên bản nên không bắt được."""
    import ranking
    ms = ["GPT-6 Sol", "GPT-6"]
    sol = {"model": "GPT-6 Sol (max)", "row": "GPT-6 Sol (max) | 872k | OpenAI | 48 | $1.06"}
    astra = {"model": "GPT-6 Astra (max)", "row": "1 | GPT-6 Astra (max) | Codex | 58.2%"}
    assert ranking.row_carries_version(ms, sol)
    assert not ranking.row_carries_version(ms, astra)


def test_variant_gate_does_not_touch_names_without_a_word():
    """"Grok 4.7" không có từ biến thể — cổng mới không được đòi gì thêm (giữ LOW-338)."""
    import ranking
    assert ranking.row_carries_version(["Grok 4.7"], {"model": "Grok 4.7 (high)",
                                                       "row": "Grok 4.7 (high) | 46"})
    assert not ranking.row_carries_version(["Qwen Image 2.1"], {"model": "qwen-image-edit",
                                                                 "row": "qwen-image-edit | 1200"})


def test_effort_words_are_not_treated_as_variants():
    """Bảng tự thêm mức nghĩ (max/high/medium) vào MỌI hàng — không phân biệt model."""
    import ranking
    assert ranking.row_carries_version(["GPT-6 Sol max"], {"model": "GPT-6 Sol (high)",
                                                            "row": "GPT-6 Sol (high) | 44"})


# ---------------------------------------------------------------- 4. nguồn benchmark
HTML_DDG = """
<a class="result__a" href="https://kingy.ai/blog/gpt-6-sol-luna-specs-benchmarks-pricing/">Specs &amp; benchmarks</a>
<a class="result__a" href="//duckduckgo.com/l/?uddg=https%3A%2F%2Fartificialanalysis.ai%2Fmodels%2Fgpt-6-sol&rut=x">AA</a>
<a class="result__a" href="https://duckduckgo.com/y.js?ad_domain=grammarly.com">quang cao</a>
<a class="result__a" href="https://www.msn.com/en-us/news/gpt-6">msn</a>
<a class="result__a" href="https://kingy.ai/blog/khac/">cung mien</a>
"""


class _Resp:
    status_code = 200
    text = HTML_DDG


def test_web_search_reaches_beyond_the_news_index():
    """Ông Chủ 23/09/2026: *"nguồn nào chả được miễn là ra benchmark chuẩn"*. Đo thật từ
    máy chủ: truy vấn benchmark ra kingy.ai, metricnexus, finout, artificialanalysis —
    không trang nào nằm trong chỉ mục TIN mà `other_outlets_bing` đang tra."""
    import article_sources as a
    with mock.patch.object(a.httpx, "post", return_value=_Resp()):
        ra = a.web_search("GPT-6 Sol benchmark", so=6)
    mien = [x["outlet_url"] for x in ra]
    assert mien == ["https://kingy.ai", "https://artificialanalysis.ai"], ra
    assert all("y.js" not in x["url"] for x in ra), ra          # bo quang cao cua DDG
    assert all("msn.com" not in x["url"] for x in ra), ra       # DROP_DOMAIN giu nguyen


def test_web_search_survives_a_throttle():
    """DDG trả 202 khi hỏi dồn — vòng BỔ SUNG không được làm chết engine ảnh."""
    import article_sources as a

    class _R202:
        status_code = 202
        text = ""

    with mock.patch.object(a.httpx, "post", return_value=_R202()):
        assert a.web_search("q") == []


def _nguon(title_en):
    return {"title_en": title_en,
            "pages": [{"url": "https://openai.com/index/introducing-gpt-6-sol-and-luna/", "kind": "goc"}]}


def test_benchmark_round_only_for_release():
    from prepare import fallback_rounds as fr
    goi = []
    with mock.patch("article_sources.web_search", side_effect=lambda q, **k: goi.append(q) or []):
        n = _nguon("Pentagon says overreliance on GPT-6 contributed to a strike")
        fr._benchmark_pages(n, Path("/khong/ghi.json"), list(n["pages"]),
                            "Lầu Năm Góc nói phụ thuộc AI", "MODEL")
    assert goi == [], goi


def test_benchmark_round_adds_pages_and_caps():
    from prepare import fallback_rounds as fr
    trang = [{"url": f"https://kingy{i}.ai/x", "kind": "other_outlet", "title": "t",
              "outlet_url": f"https://kingy{i}.ai"} for i in range(6)]
    with mock.patch("article_sources.web_search", return_value=trang),             mock.patch("article_sources.WEB_SEARCH_SLEEP", 0),             mock.patch("prepare.fallback_rounds._write_json"):
        n = _nguon("Introducing GPT-6 Sol and Luna")
        ra = fr._benchmark_pages(n, Path("/khong/ghi.json"), list(n["pages"]),
                                 "OpenAI ra mắt GPT-6 Sol và Luna", "MODEL")
    them = [t for t in ra if "kingy" in t["url"]]
    assert len(them) == fr.MAX_BENCHMARK_PAGE, [t["url"] for t in ra]
    assert ra[0]["url"].startswith("https://openai.com"), ra[0]      # trang goc van dung dau


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
