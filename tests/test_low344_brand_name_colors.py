#!/usr/bin/env python3
"""LOW-344 — to mau TEN HANG / TEN MODEL thong nhat cho ca Ethan, Dre, Kite.

Truoc day chi Ethan to ten hang, va `card._extract_label` chi tach theo dau cach
nen ten model viet lien truot het ("DEEPSEEK-V4.1-FLASH", "QWEN3.8-27B",
"GPT-5.6", "OPENAI/GPT-OSS-120B" — do 21/09/2026). Dre chi lay mau hang cho
dau ngoac quote; Kite chi to cum `accent` do vai tu chon.

Ong Chu chot 21/09/2026: (1) to tron cum ten model; (2) tien to to chuc to
khac mau; (3) mau theo palette hang, cho ca ba vai; (4) Kite: tieu de co ten
hang thi bo `accent`; (5) hang den trang van to, bang mau tuong phan noi bat.

Chay:  venv/bin/python tests/test_low344_brand_name_colors.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image, ImageDraw  # noqa: E402

import brand_names  # noqa: E402
import card  # noqa: E402
import render_edu  # noqa: E402
import text_bg  # noqa: E402


def _named(text):
    """[(khuc, vai, khoa[0])] cua cac khuc duoc to."""
    return [(t, r, k[0]) for w in brand_names.line_segments(text) for t, r, k in w if r]


# ------------------------------------------------------------- nhan dien
def test_whole_model_name_is_one_colored_chunk():
    """(1) + 7 chuoi do tren may chu 21/09 — truoc day khong chuoi nao duoc to."""
    ca = {
        "DEEPSEEK-V4.1-FLASH THẢ TRỌNG SỐ": [("DEEPSEEK-V4.1-FLASH", "name", "DEEPSEEK")],
        "QWEN-IMAGE-2.1 LÊN TOP": [("QWEN-IMAGE-2.1", "name", "QWEN")],
        "GPT-5.6 LUNA ĐÁNH BẠI GPT-6": [("GPT-5.6", "name", "OPENAI"), ("GPT-6", "name", "OPENAI")],
        "CLAUDE-OPUS-5 RA MẮT": [("CLAUDE-OPUS-5", "name", "CLAUDE")],
        "LLAMA4 SCOUT": [("LLAMA4", "name", "LLAMA")],
        "QWEN3.8-27B": [("QWEN3.8-27B", "name", "QWEN")],
        "DeepSeek-V4.1-Flash nén KV Cache kỷ lục": [("DeepSeek-V4.1-Flash", "name", "DEEPSEEK")],
    }
    for text, mong in ca.items():
        assert _named(text) == mong, (text, _named(text))


def test_org_prefix_is_its_own_chunk():
    """(2): tien to to chuc truoc "/" la mot khuc rieng, vai "org"."""
    assert _named("OPENAI/GPT-OSS-120B") == [("OPENAI/", "org", "OPENAI"), ("GPT-OSS-120B", "name", "OPENAI")]
    assert _named("deepseek-ai/DeepSeek-V4.1-Flash:") == [
        ("deepseek-ai/", "org", "DEEPSEEK"), ("DeepSeek-V4.1-Flash", "name", "DEEPSEEK")]
    # tien to la mot to chuc la (ukisai) van to theo hang cua ten model
    assert _named("ukisai/Swift-Qwen3.8-27b") == [("ukisai/", "org", "QWEN"), ("Swift-Qwen3.8-27b", "name", "QWEN")]


def test_chunks_rebuild_the_exact_line_and_leave_punctuation_plain():
    for text in ["“DeepSeek-V4.1-Flash”, nhanh hơn", "OPENAI/GPT-OSS-120B:", "Không nhắc hãng nào"]:
        words = brand_names.line_segments(text)
        assert " ".join("".join(t for t, _r, _k in w) for w in words) == text
    w = brand_names.line_segments("“DeepSeek”,")[0]
    assert w == [("“", None, None), ("DeepSeek", "name", ("DEEPSEEK",)), ("”,", None, None)], w


def test_no_false_positive_on_plain_compounds_and_codes():
    for text in ["AI-FIRST", "ĐA-PHƯƠNG-THỨC", "H100 B200", "V4.1-FLASH", "Một chủ đề bình thường"]:
        assert _named(text) == [], (text, _named(text))


# ------------------------------------------------------------- mau
def test_palette_brand_uses_palette_a_and_distinct_org_color():
    """(3) + (2): hang co palette -> ten model = `a`, tien to khac mau ro rang."""
    for key, theme in [(("DEEPSEEK",), "deepseek"), (("CLAUDE",), "anthropic"), (("QWEN",), "qwen"),
                       (("GEMINI",), "gemini"), (("MISTRAL",), "mistral")]:
        ten, org = brand_names.colors_for(key, None)
        assert ten == brand_names.hex_rgb(render_edu.THEMES[theme]["a"]), key
        assert org != ten and sum(abs(a - b) for a, b in zip(org, ten, strict=True)) >= 60, (key, ten, org)


def test_mono_brand_uses_fallback_never_its_old_color():
    """(5): OpenAI khong con xanh la ChatGPT; lay mau noi bat do noi goi dua."""
    ten, org = brand_names.colors_for(("OPENAI",), (0, 204, 224))
    assert ten == (0, 204, 224) and org != ten
    assert brand_names.colors_for(("XAI",), None) == (None, None)


def test_mono_fallback_stands_out_from_title_text_for_both_channels():
    """(5): dcgr co CYAN = trang = mau chu — mau du phong phai khac chu."""
    for ten in ("donniechublog", "dcgr"):
        card.set_brand(ten)
        assert text_bg.ratio_wall_part(card.BRAND_NAME_FALLBACK, card.FG) >= 1.5, (ten, card.BRAND_NAME_FALLBACK)
        assert text_bg.ratio_wall_part(card.BRAND_NAME_FALLBACK, card.BG) >= 4.5, ten


# ------------------------------------------------------------- Ethan / Dre (PIL)
def _font():
    return card.ImageFont.truetype(card.F_BOLD, 56)


def _ink_bbox(im, bg=(0, 0, 0)):
    """Hop bao pixel khac nen."""
    px = im.load()
    xs = [x for x in range(im.width) for y in range(0, im.height, 2) if px[x, y] != bg]
    return (min(xs), max(xs)) if xs else (None, None)


def _count_near(im, rgb, tol=40):
    raw = im.convert("RGB").tobytes()          # getdata() da deprecated o Pillow 12
    r0, g0, b0 = rgb[:3]
    return sum(1 for r, g, b in zip(raw[0::3], raw[1::3], raw[2::3], strict=True)
               if abs(r - r0) + abs(g - g0) + abs(b - b0) <= tol)


def test_ethan_line_is_colored_and_width_matches_drawing():
    """Ve that tren PIL: ten model mang mau palette, va be ngang `_empty_line`
    khop be ngang ve (sai lech -> dong can giua bi lech)."""
    card.set_brand("donniechublog")
    f = _font()
    dong = "DEEPSEEK-AI/DEEPSEEK-V4.1-FLASH THẢ TRỌNG SỐ"
    im = Image.new("RGB", (2400, 120), (0, 0, 0))
    d = ImageDraw.Draw(im)
    x0 = 40
    card._about_line(d, x0, 20, dong, f, (255, 255, 255), che_do="cyan")
    ten, org = (card.brand_fill(("DEEPSEEK",), r) for r in ("name", "org"))
    assert _count_near(im, ten) > 400, "ten model phai mang mau palette DeepSeek"
    assert _count_near(im, org) > 200, "tien to phai co mau rieng"
    _left, right = _ink_bbox(im)
    assert abs((x0 + card._empty_line(d, dong, f)) - right) <= 6, (right, card._empty_line(d, dong, f))


def test_ethan_long_card_stays_single_color():
    """che_do None (the tin kieu dai) — khong to gi, nhu truoc."""
    card.set_brand("donniechublog")
    im = Image.new("RGB", (1600, 120), (0, 0, 0))
    card._about_line(ImageDraw.Draw(im), 20, 20, "DEEPSEEK-V4.1-FLASH", _font(), (255, 255, 255))
    assert _count_near(im, card.brand_fill(("DEEPSEEK",), "name"), tol=20) == 0


def test_dre_cover_hook_colors_brand_names():
    """Dre truoc day khong to ten hang tren hook bia."""
    import carousel
    card.set_brand("donniechublog")
    carousel.set_background("dark")
    with tempfile.TemporaryDirectory() as t:
        src = Path(t) / "bg.png"
        Image.new("RGB", (carousel.W, carousel.H), (30, 34, 40)).save(src)
        out = Path(t) / "cover.png"
        carousel.build_cover(str(src), "Qwen3.8-27B vượt mặt GPT-5.6", "QWEN", str(out),
                             handle="donniechublog", category="MODEL RELEASE")
        im = Image.open(out).convert("RGB")
    assert _count_near(im, card.brand_fill(("QWEN",), "name")) > 400, "hook phai to Qwen theo palette"
    assert _count_near(im, card.brand_fill(("OPENAI",), "name")) > 200, "GPT (den trang) van phai noi bat"


def test_quote_mark_color_follows_compound_names():
    assert card._color_rank_within("DEEPSEEK-V4.1-FLASH nói") == brand_names.hex_rgb(render_edu.THEMES["deepseek"]["a"])
    assert card._color_rank_within("OpenAI nói") is None          # den trang -> mau mac dinh cua khung


# ------------------------------------------------------------- Kite (HTML)
def test_kite_title_with_brand_drops_accent():
    """(4): co ten hang -> to ten hang, bo `accent`; khong ten hang -> accent nhu cu."""
    th = render_edu.THEMES["deepseek"]
    h = render_edu.accent_html("DeepSeek-V4.1-Flash nén KV Cache kỷ lục", "nén KV Cache", th)
    assert 'class="brand"' in h and "accent" not in h, h
    assert "--bc:#7189FE" in h, h
    h2 = render_edu.accent_html("Bài toán chạm trần bộ nhớ", "chạm trần", th)
    assert '<span class="accent">chạm trần</span>' in h2, h2


def test_kite_mono_brand_uses_theme_accent_and_light_region_css():
    th = render_edu.THEMES["ink"]
    h = render_edu.accent_html("GPT-5.6 Luna đánh bại GPT-6", None, th)
    assert h.count('class="brand"') == 2 and f"--bc:{th['a'].upper()}" in h, h
    css = render_edu._css_text_dark_region("#figtxt", th)
    assert ".brand{color:var(--bcd);}" in css
    assert ".brand{color:var(--bc);}" in render_edu.base_css(dict(th, hero=None))


def test_kite_subject_brand_still_works():
    """LOW-340 dung chung bo nhan dien moi."""
    assert render_edu.subject_brand(["ukisai/Swift-Qwen3.8-27b thả trọng số"]) == ("QWEN",)
    assert render_edu.subject_brand(["V4.1-FLASH", "HUGGING FACE · DEEP DIVE",
                                     "Model nhỏ nhất của DeepSeek"]) == ("DEEPSEEK",)


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
