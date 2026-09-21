#!/usr/bin/env python3
"""LOW-340 — palette slide Kite di theo HANG CHU THE cua tin.

Ong Chu 21/09/2026: tin DeepSeek (xanh duong · xam · trang) ra ca bo xanh la
("moss"). Do tren may chu, bon cho hong cung luc:
  (a) theme vai tu ghi trong spec thang mau hang, chi in canh bao; nguong hue
      0.28 coi moss (lech 0.262) la "cung tong" nen canh bao cung khong co;
  (b) ten hang dinh gach noi/gach cheo ("DeepSeek-V4.1-Flash",
      "deepseek-ai/...") khong nhan ra;
  (c) chi doc spec vai viet — bat nham "Hugging Face" (noi dang model);
  (d) khong co palette DeepSeek de chon ('ink' la navy x vang).
Ong Chu chot: palette hang -> mau anh bia -> hang gan hue -> xoay vong; hang
tong den trang (OpenAI, xAI, Apple...) khong can palette.

Chay:  venv/bin/python tests/test_low340_brand_palettes.py
"""
import contextlib
import io
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import render_edu  # noqa: E402
import text_bg  # noqa: E402

MIN_CONTRAST = 4.5          # WCAG AA chu thuong


def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _solid_image(rgb):
    from PIL import Image
    p = Path(tempfile.mkdtemp()) / "cover.png"
    Image.new("RGB", (600, 800), rgb).save(p, "PNG")
    return str(p)


# ------------------------------------------------------------- palette
def test_every_theme_readable_on_its_own_background():
    """Mau nhan `a` la chu eyebrow/accent/so buoc (va nen cua chip chu toi), `b`
    la so the + cot bar, `stand` la standfirst — ca ba phai doc duoc tren ca
    `bg` lan `panel`. Mau goc cua hang thuong dam (DeepSeek #4D6BFE chi 3.6:1)
    nen palette phai nang sang, khong duoc lay nguyen."""
    hong = []
    for ten, th in render_edu.THEMES.items():
        for k in ("a", "b", "stand"):
            for nen in ("bg", "panel"):
                cr = text_bg.ratio_wall_part(_rgb(th[k]), _rgb(th[nen]))
                if cr < MIN_CONTRAST:
                    hong.append(f"{ten}.{k} tren {nen}: {cr:.2f}")
    assert not hong, hong


def test_brand_themes_map_to_existing_palettes():
    assert set(render_edu.MOOD_THEMES) <= set(render_edu.THEMES)
    for key, ten in render_edu.BRAND_THEME.items():
        assert ten in render_edu.THEMES and ten not in render_edu.MOOD_THEMES, (key, ten)
    # Hang den trang khong co palette (Ong Chu 21/09/2026).
    for key in render_edu.MONO_BRANDS:
        assert key not in render_edu.BRAND_THEME, key


def test_deepseek_palette_is_blue_grey_white():
    """Dung nhan dien: nhan chinh xanh duong, nhan phu xam (bao hoa thap)."""
    import colorsys
    th = render_edu.THEMES["deepseek"]
    h, s, _v = colorsys.rgb_to_hsv(*(c / 255 for c in _rgb(th["a"])))
    assert 0.58 < h < 0.70 and s > 0.4, (h, s)
    _h, s_b, _v = colorsys.rgb_to_hsv(*(c / 255 for c in _rgb(th["b"])))
    assert s_b < 0.15, s_b


# ------------------------------------------------------------- do hang
def test_hyphenated_model_names_are_recognised():
    """(b): bon chuoi do tren may chu 21/09 — ba chuoi dau truoc day ra None."""
    for text in ("DeepSeek-V4.1-Flash nén KV Cache kỷ lục",
                 "deepseek-ai/DeepSeek-V4.1-Flash",
                 "deepseek-ai/DeepSeek-V4.1-Flash: thả trọng số HuggingFace 10/09",
                 "DEEPSEEK V4.1-FLASH"):
        assert render_edu.subject_brand([text]) == ("DEEPSEEK",), text
    assert render_edu.subject_brand(["Qwen-Image-2.1 lên top"]) == ("QWEN",)
    # so phien ban dinh lien ten (tin that 21/09: "ukisai/Swift-Qwen3.8-27b")
    assert render_edu.subject_brand(["ukisai/Swift-Qwen3.8-27b thả trọng số"]) == ("QWEN",)
    assert render_edu.subject_brand(["Llama4 Scout"]) == ("LLAMA",)
    assert render_edu.subject_brand(["GPT-5.1 vượt mặt"]) == ("OPENAI",)
    assert render_edu.subject_brand(["Một chủ đề không nhắc hãng nào"]) is None


def test_platform_counts_only_when_no_other_brand():
    """(c): "Hugging Face" la noi dang model, khong phai chu the."""
    assert render_edu.subject_brand(
        ["V4.1-FLASH", "HUGGING FACE · DEEP DIVE", "Model nhỏ nhất của DeepSeek"]) == ("DEEPSEEK",)
    assert render_edu.brand_theme_of(
        {"folio": "HUGGING FACE", "slides": [{"title": "Hugging Face ra mắt kho mới"}]})[0] == "huggingface"


def test_subject_is_read_before_role_written_spec():
    """(c): spec that cua bo blog 14/09 — folio khong ten hang, eyebrow "HUGGING
    FACE". Doc tieu de tin goc (`subject`) truoc thi ra DeepSeek."""
    spec = {"subject": "deepseek-ai/DeepSeek-V4.1-Flash: thả trọng số HuggingFace 10/09",
            "folio": "V4.1-FLASH", "theme": "moss",
            "slides": [{"kind": "cover", "eyebrow": "HUGGING FACE · DEEP DIVE",
                        "title": "Model nhỏ nhất, chạy thay cả bản Pro"}]}
    assert render_edu.brand_theme_of(spec) == ("deepseek", ("DEEPSEEK",))


# ------------------------------------------------------------- chon theme
def test_spec_theme_cannot_override_brand_palette():
    """(a): dung bo trong anh chup cua Ong Chu (blog 21/09, folio "DEEPSEEK
    V4.1-FLASH", vai ghi theme "moss", bia la hinh paper mau xanh)."""
    img = _solid_image((76, 111, 217))
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        theme, hero = render_edu.pick_theme_auto(
            {"folio": "DEEPSEEK V4.1-FLASH", "theme": "moss", "hero": "orbit",
             "slides": [{"kind": "cover", "eyebrow": "RESEARCH · DEEP DIVE",
                         "title": "DeepSeek-V4.1-Flash nén KV Cache kỷ lục"}]},
            bia_anh=True, anh_mau=img)
    assert theme == "deepseek", theme
    assert hero is None
    assert "deepseek" in err.getvalue() and "moss" in err.getvalue(), err.getvalue()


def test_mono_brands_skip_the_brand_color_tier():
    """Hang den trang: khong palette, va KHONG do hue cua mau xam — xAI
    (225,225,225) tung ra 'rose' hong, OpenAI ra 'orbit'."""
    for text in ("XAI GROK 5 RA MẮT", "Grok-5 ra mắt", "OPENAI SORA", "GPT-5 vượt mặt",
                 "APPLE INTELLIGENCE", "KIMI K3", "MIDJOURNEY V8"):
        spec = {"folio": text}
        assert render_edu.color_rank_within_spec(spec) is None, text
        assert render_edu.brand_theme_of(spec)[0] is None, text
        theme, _h = render_edu.pick_theme_auto(spec, bia_anh=False)
        assert theme in render_edu.MOOD_THEMES, (text, theme)


def test_brand_without_palette_uses_nearest_mood_theme():
    """Hang co mau nhung chua co palette (Microsoft xanh da troi) -> theme tam
    trang gan hue nhat, khong bao gio rot vao palette cua hang khac."""
    theme, _h = render_edu.pick_theme_auto({"folio": "MICROSOFT BUILD"}, bia_anh=False)
    assert theme == "orbit", theme
    for rgb in [(77, 108, 247), (0, 129, 251), (118, 185, 0), (255, 210, 30)]:
        assert render_edu.theme_near_color(rgb) in render_edu.MOOD_THEMES, rgb


def test_green_theme_on_blue_cover_now_warns():
    """(a) nguong: moss lech xanh DeepSeek 0.262 — duoi nguong cu 0.28, khong
    mot dong canh bao. Tin KHONG gan hang de chi thu nguong."""
    img = _solid_image((77, 108, 247))
    err = io.StringIO()
    with contextlib.redirect_stderr(err):
        theme, _h = render_edu.pick_theme_auto({"folio": "test", "theme": "moss"},
                                               bia_anh=True, anh_mau=img)
    assert theme == "moss"
    assert "LECH MAU" in err.getvalue(), err.getvalue()


# ------------------------------------------------------------- kite_submit
def test_kite_submit_locks_theme_to_subject_brand():
    from tam import so_tam
    from test_spec_kite import _chay, _du_bia
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl, m = _du_bia(wd, title="deepseek-ai/DeepSeek-V4.1-Flash: thả trọng số HuggingFace")
        ra, loi, canh = _chay(sl, m, wd, theme="moss")
        assert loi == [], loi
        assert ra["theme"] == "deepseek", ra.get("theme")
        assert ra["subject"] == m["title"]
        assert any("moss" in c and "deepseek" in c for c in canh), canh


def test_kite_submit_rejects_other_brands_palette():
    from tam import so_tam
    from test_spec_kite import _chay, _co, _du_bia
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        sl, m = _du_bia(wd)                  # tin Nemotron, khong nhac hang co palette
        _r, loi, _c = _chay(sl, m, wd, theme="anthropic")
        assert _co(loi, "anthropic", "palette riêng"), loi


def test_redo_not_blocked_when_theme_is_locked():
    """Bia anh that -> hero luon None; theme khoa -> "doi theme hoac hero" la
    chan cung moi lan lam lai. Chi con doi hook."""
    import kite_submit
    spec = {"theme": "deepseek", "slides": [{"kind": "cover", "image": "B1"}]}
    prev = {"theme": "deepseek", "hero": None, "hook": "Hook cũ"}
    loi = []
    kite_submit._check_redo(spec, prev, "Hook mới", loi, theme_locked=True)
    assert loi == [], loi
    kite_submit._check_redo(spec, prev, "Hook cũ", loi, theme_locked=True)
    assert len(loi) == 1 and "hook" in loi[0], loi


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
