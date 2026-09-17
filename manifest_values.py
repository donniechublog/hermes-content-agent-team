#!/usr/bin/env python3
"""Enumerated VALUES stored in the manifest and their Vietnamese display text (LOW-230).

Data holds English codes only (table: docs/tu_dien_ten/manifest_values_v3.json).
Text shown to roles or Ông Chủ stays Vietnamese and is produced from the maps below,
so code compares codes instead of searching substrings of a sentence.
"""

# image `uses`: slot code -> sentence printed in briefs (byte-identical to the
# strings stored before LOW-230).
USE_LABELS = {
    "cover": "bìa",
    "cover_headline_block": "bìa (khối tít của bài gốc — không còn ảnh nào khác)",
    "cover_article_hero": "bìa (ảnh hero của chính bài gốc)",
    "cover_ranking": "HERO / BÌA (bảng xếp hạng, model đã khoanh — ảnh chính bắt buộc của tin xếp hạng)",
    "body": "thân",
    "body_chart": "thân (chart)",
    "body_chart_full_width": "thân (chart, dán full bề ngang nguyên vẹn)",
    "stack_vertical": "ghép dọc với một ảnh ngang cùng tone",
    "landscape_crop_if_no_text": "cat_ngang: true NẾU là ảnh người/sản phẩm KHÔNG có chữ",
    "landscape_crop_confirmed": "cat_ngang: true (ảnh người/sản phẩm không chữ, vision đã xác nhận)",
    "figure": "figure",
}

COVER_USES = frozenset(u for u in USE_LABELS if u.startswith("cover"))
BODY_USES = frozenset(u for u in USE_LABELS if u.startswith("body"))


def use_label(code: str) -> str:
    """Vietnamese sentence for a slot code; unknown codes print as-is."""
    return USE_LABELS.get(code, code)


def use_labels(codes) -> list:
    return [use_label(c) for c in (codes or [])]
