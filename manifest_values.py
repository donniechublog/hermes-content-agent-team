#!/usr/bin/env python3
"""Enumerated VALUES stored in the manifest and their Vietnamese display text (LOW-230).

Data holds English codes only (table: docs/tu_dien_ten/manifest_values_v3.json).
Text shown to roles or Ông Chủ stays Vietnamese and is produced from the maps below,
so code compares codes instead of searching substrings of a sentence.
"""

# image `uses`: slot code -> sentence printed in briefs (byte-identical to the
# strings stored before LOW-230, except the spec key `landscape_crop` — was
# `cat_ngang` before LOW-248).
USE_LABELS = {
    "cover": "bìa",
    "cover_headline_block": "bìa (khối tít của bài gốc — không còn ảnh nào khác)",
    "cover_article_hero": "bìa (ảnh hero của chính bài gốc)",
    "cover_ranking": "HERO / BÌA (bảng xếp hạng, model đã khoanh — ảnh chính bắt buộc của tin xếp hạng)",
    "body": "thân",
    "body_chart": "thân (chart)",
    "body_chart_full_width": "thân (chart, dán full bề ngang nguyên vẹn)",
    "stack_vertical": "ghép dọc với một ảnh ngang cùng tone",
    "landscape_crop_if_no_text": "landscape_crop: true NẾU là ảnh người/sản phẩm KHÔNG có chữ",
    "landscape_crop_confirmed": "landscape_crop: true (ảnh người/sản phẩm không chữ, vision đã xác nhận)",
    "figure": "figure",
}

COVER_USES = frozenset(u for u in USE_LABELS if u.startswith("cover"))
BODY_USES = frozenset(u for u in USE_LABELS if u.startswith("body"))


def use_label(code: str) -> str:
    """Vietnamese sentence for a slot code; unknown codes print as-is."""
    return USE_LABELS.get(code, code)


def use_labels(codes) -> list:
    return [use_label(c) for c in (codes or [])]


# Codes whose Vietnamese label starts with "bìa" — the old `str(d).startswith("bìa")`
# test (role.has_label_cover, prepare.vision). `cover_ranking` is NOT in it: its label
# starts "HERO / BÌA", which that test never matched.
COVER_PREFIX_USES = frozenset({"cover", "cover_headline_block", "cover_article_hero"})


# image `subject_kind` (LOW-273): what vision says the main character is.
SUBJECT_KIND_LABELS = {
    "person": "người", "product": "sản phẩm", "building": "toà nhà", "logo": "logo",
    "screen": "màn hình", "chart": "biểu đồ", "other": "chủ thể",
}


def subject_kind_label(code) -> str:
    """Vietnamese word for a subject kind; unknown/None prints 'chủ thể'."""
    return SUBJECT_KIND_LABELS.get(code or "", "chủ thể")


# Other enumerated values: code -> the Vietnamese value printed before LOW-230.
# Briefs, logs, Telegram and handoff text print through these so the text stays
# byte-identical; data and comparisons use the codes. Codes not listed print as-is.
SOURCE_LABELS = {                       # image.source
    "press_entity": "bao_thuc_the",
    "other_outlet": "báo khác",         # merged "báo khác" + "bao khac": prints the accented one
    "concept": "khai_niem",
    "article": "gốc",                   # merged "gốc" + "goc": prints the accented one
    "brand": "thuong_hieu",
    "browser_capture": "chup",
    "capture_source": "chup_nguon",
    "entity": "thuc_the",
    "ranking": "xep_hang",
    "arxiv_figure": "arxiv_hinh",
    "arxiv_cover": "arxiv_bia",
    "role_supplied": "vai",
}
# LOW-285: nguon tim anh web (find_image_web) truoc 19/09/2026 ghi CAU TRUY VAN vao
# `alt` — alt cua cac nguon nay KHONG phai chu thich that, khong duoc lay ten nguoi tu do
# (manifest cu van con, nen nhan theo nguon chu khong theo ngay).
SOURCES_ALT_IS_QUERY = frozenset({"web_bing", "web_yandex"})
# LOW-219: vong Commons/Wikipedia ghi TEN TEP vao `alt` ("Commons: Le Mistral.jpg").
# Ten tep van la bang chung ve NGUOI trong anh (quy uoc dat ten cua Commons, LOW-269)
# nhung KHONG phai bang chung "anh nay noi ve hang X": do 20/09/2026 tren 2.721 anh bi
# cham khong lien quan, khop ten hang trong ten tep keo vao tau chien "Le Mistral",
# tranh "Consulting the Oracle", cong nha tho "Portal Jacobiturmstr".
ALT_FILENAME_PREFIX = ("Commons:", "Wikipedia:")
KIND_LABELS = {"photo": "anh"}          # image.kind
RANKING_KIND_LABELS = {                 # ranking.kind
    "table": "bang",
    "table-stitched": "bang-ghep",
    "list": "danh-sach",
    "list-stitched": "danh-sach-ghep",
    "card": "the",
}
TONE_LABELS = {"light": "sáng", "dark": "tối"}   # brand_match.background_tone
STORY_OBJECT_LABELS = {                 # image_order_by_story_type[] (story_type.py)
    "concept": "khai_niem",
    "headquarters": "tru_so",
    "stock": "co_phieu",
    "stock_exchange": "san_giao_dich",
    "announcement_chart": "chart_cong_bo",
    "ranking": "xep_hang",
    "company_country_flag": "co_nuoc_hang",
    "two_company_pair": "ghep_hai_hang",
    "infrastructure_concept": "khai_niem_ha_tang",
}


def source_label(code) -> str:
    return SOURCE_LABELS.get(code, code)


def kind_label(code) -> str:
    return KIND_LABELS.get(code, code)


def ranking_kind_label(code) -> str:
    return RANKING_KIND_LABELS.get(code, code)


def tone_label(code) -> str:
    return TONE_LABELS.get(code, code)


def story_object_label(code) -> str:
    return STORY_OBJECT_LABELS.get(code, code)
