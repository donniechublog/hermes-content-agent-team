#!/usr/bin/env python3
"""LOW-381 (23/09/2026) — ten model dang SLUG phai khop duoc hang tren bang.

Bai that: tieu de "claude-opus-5-5-max-effort va xhigh-effort vao top LiveBench".
`extract_model` tra dung MOT ung vien `claude-opus-5-5-max`; bang AA in
"Claude Opus 5.5 (max with fallback)" nen khong hang nao khop -> tin ra THE CHU.
Do tren may chu cung ngay: cung bai do, voi ten "Claude Opus 5.5" thi chup duoc
bang 2828x1846 khoanh dung hang.

Chay:  python tests/test_ranking_slug_model.py
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import model_name  # noqa: E402
import ranking  # noqa: E402

# Hang THAT doc tu bang AA tren may chu 23/09/2026 (`[xep_hang] aa-models: khop`).
ROW_AA = "Claude Opus 5.5 (max with fallback) | 1M | Anthropic | 58 | $5.98 | -- | -- | -- | Model Providers"
TITLE = "claude-opus-5-5-max-effort và xhigh-effort vào top LiveBench"


def _norm(s: str) -> str:
    """Ban Python cua `norm` trong `ranking._JS_NORM` — dung de doi chieu bang so
    ma khong can chromium. Doi mot ben thi test nay do."""
    return re.sub(r"[\s\-_–—.]+", "", (s or "").lower())


def _matches(row: str, model: str) -> bool:
    """Ban Python cua `matchesModel`: khop chuoi, nhung ky tu ngay sau cho khop
    khong duoc la CHU SO (chan "Gemini 3" an vao "Gemini 3.8")."""
    hay, nm = _norm(row), _norm(model)
    for m in re.finditer(re.escape(nm), hay):
        if not hay[m.end():m.end() + 1].isdigit():
            return True
    return False


def test_slug_becomes_display_name():
    assert model_name.display_name("claude-opus-5-5-max-effort") == "Claude Opus 5.5"
    assert model_name.display_name("claude-opus-5-5-max") == "Claude Opus 5.5"
    assert model_name.display_name("gpt-6-astra-max") == "GPT 6 Astra"
    assert model_name.display_name("qwen3.8-max-0902") == "qwen3.8", "duoi ngay cua arena"
    assert model_name.display_name("claude-opus-4-6-search") == "Claude Opus 4.6 Search", \
        "`search` la nang luc, khong phai muc no luc — giu lai"


def test_display_name_does_not_touch_ordinary_names():
    """Ten da o dang hien thi: chi bo ngoac va hau to, KHONG doi chu hoa/thuong."""
    assert model_name.display_name("GPT-6 Astra (high)") == "GPT-6 Astra"
    assert model_name.display_name("Claude Opus 5.5 (max with fallback)") == "Claude Opus 5.5"
    assert model_name.display_name("Muse Spark 1.3") == "Muse Spark 1.3"
    # Gach noi trong mot ten CO CHU HOA la mot phan cua ten, khong phai dau tach
    # cua slug — be ra la bia ra mot ten khac.
    assert model_name.display_name("MiMo-V2.6-Pro") == "MiMo-V2.6-Pro"
    assert model_name.display_name("Kimi-K3") == "Kimi-K3"
    assert model_name.display_name("Qwen-Image-2.1") == "Qwen-Image-2.1"
    assert model_name.display_name("") == ""


def test_extract_model_expands_a_slug_title():
    """DO trong ticket: truoc LOW-381 danh sach nay dung MOT phan tu."""
    names = ranking.extract_model(TITLE)
    assert names[0] == "claude-opus-5-5-max", "ban dai nhat van duoc thu truoc"
    assert "Claude Opus 5.5" in names, "thieu ten hien thi -> khong bang nao khop"
    assert len(names) > 1


def test_variant_matches_the_real_row_but_a_shorter_one_does_not():
    names = ranking.extract_model(TITLE)
    assert not _matches(ROW_AA, names[0]), "chinh cho tin 23/09 chet: dau '(' chen giua"
    assert any(_matches(ROW_AA, m) for m in names), "phai co it nhat mot bien the khop hang that"
    # Luat cu (LOW-177) khong duoc no: "Claude Opus 5" khong duoc an vao "5.5".
    assert not _matches(ROW_AA, "Claude Opus 5")
    assert "Claude" not in names, "ten hang tran khoanh trung moi hang co chu Claude"


def test_fallback_card_names_the_board_from_the_title():
    """The du phong 23/09 ghi ARTIFICIALANALYSIS vi LINK bai tro toi do, trong khi
    tieu de (va hook) noi LiveBench."""
    ds = ranking.suggest_sources(TITLE, link="https://artificialanalysis.ai/leaderboards/models")
    card_name, source = ranking._card_fields(ranking.extract_model(TITLE), ds)
    assert source["id"] == "livebench", f"the van ghi bang {source['id']}"
    assert card_name == "Claude Opus 5.5", "the in nguyen slug"


def test_fallback_card_keeps_a_source_when_the_title_names_none():
    ds = ranking.suggest_sources("Kimi-K3 leo lên #1", link="")
    card_name, source = ranking._card_fields(["Kimi-K3"], ds)
    assert source and source.get("site") and source.get("board"), "khong duoc rong khi tieu de khong goi ten bang"
    assert card_name == "Kimi-K3"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
