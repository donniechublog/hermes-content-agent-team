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


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
