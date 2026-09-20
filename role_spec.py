#!/usr/bin/env python3
"""spec.json that the DESIGNER roles write themselves (Dre / Ethan / Kite) — English keys and
values (LOW-248, table: docs/tu_dien_ten/designer_spec_keys_v2.json).

Briefs, SOUL, SKILL, IMAGE_RULES and `[LOI]` texts print only the names below; renderers
(carousel.py, card.py, render_edu.py) receive only these names.

LOW-248 transition: spec.json written before the deploy (server 17/09/2026: blog 68 + dcgr 73)
are re-read days later ("Làm lại", reruns) and are NOT migrated. Each role has ONE normaliser
below, called right after its spec is read: old keys and old values -> new; when an old key
and its new key are both present, the new one wins. Key order is kept.
"""

# ---- Dre (carousel): top level + cover/slides[] ------------------------------------------
TIERS = ("flagship", "regular")                 # `tier`
BACKGROUND_TONES = ("dark", "light")            # `background_tone` (= carousel.BACKGROUND keys)

# LOW-248 legacy aliases (old Vietnamese spec names -> new). Only role_spec reads them.
DRE_LEGACY_KEYS = {"tam_co": "tier", "nen": "background_tone"}
DRE_LEGACY_ITEM_KEYS = {"anh": "image", "ghep": "stack", "cat_ngang": "landscape_crop",
                        "tam": "crop_center", "nhan_vat": "subject"}
TIER_LEGACY_VALUES = {"thuong": "regular"}
BACKGROUND_TONE_LEGACY_VALUES = {"toi": "dark", "sang": "light"}

# ---- Ethan (hero card) ---------------------------------------------------------------------
CARD_STYLES = ("quote", "full_bleed")           # `card_style`; first = default
# Display word for a style in captions / task result lines — unchanged text for people.
CARD_STYLE_LABELS = {"quote": "quote", "full_bleed": "tran"}

ETHAN_LEGACY_KEYS = {"anh": "image", "anh2": "image2", "nhan_vat": "subject", "kieu": "card_style"}
CARD_STYLE_LEGACY_VALUES = {"tran": "full_bleed"}

# ---- Kite (carousel-edu): slides[] and slides[].bars[] ----------------------------------------
KITE_LEGACY_SLIDE_KEYS = {"nhan_vat": "subject"}
KITE_LEGACY_BAR_KEYS = {"nhan": "highlight"}


def _rename_keys(d, aliases: dict):
    """Copy of `d` with old keys renamed in place (same position); new key wins."""
    if not isinstance(d, dict):
        return d
    out = {}
    for k, v in d.items():
        new = aliases.get(k)
        if new is None:
            out[k] = v
        elif new not in d:
            out[new] = v
    return out


def legacy_value(v, legacy: dict):
    """Old enumerated value -> new code (case/space-insensitive, like the readers); other values as-is."""
    if isinstance(v, str) and v.strip().lower() in legacy:
        return legacy[v.strip().lower()]
    return v


def background_tone(v):
    """`background_tone` / carousel `--nen` value: old `toi`/`sang` -> `dark`/`light`."""
    return legacy_value(v, BACKGROUND_TONE_LEGACY_VALUES)


def card_style_value(v):
    """`card_style` / card.py `--kieu` value: old `tran` -> `full_bleed`."""
    return legacy_value(v, CARD_STYLE_LEGACY_VALUES)


def card_style_label(style: str) -> str:
    return CARD_STYLE_LABELS.get(style, style)


def dre_spec(spec):
    """Dre spec.json (any age) -> new names only."""
    if not isinstance(spec, dict):
        return spec
    out = _rename_keys(spec, DRE_LEGACY_KEYS)
    if "tier" in out:
        out["tier"] = legacy_value(out["tier"], TIER_LEGACY_VALUES)
    if "background_tone" in out:
        out["background_tone"] = background_tone(out["background_tone"])
    if isinstance(out.get("cover"), dict):
        out["cover"] = _rename_keys(out["cover"], DRE_LEGACY_ITEM_KEYS)
    if isinstance(out.get("slides"), list):
        out["slides"] = [_rename_keys(s, DRE_LEGACY_ITEM_KEYS) for s in out["slides"]]
    return out


def ethan_spec(spec):
    """Ethan spec.json (any age) -> new names only."""
    if not isinstance(spec, dict):
        return spec
    out = _rename_keys(spec, ETHAN_LEGACY_KEYS)
    if "card_style" in out:
        out["card_style"] = card_style_value(out["card_style"])
    return out


def kite_spec(spec):
    """Kite spec.json (any age) -> new names only."""
    if not isinstance(spec, dict):
        return spec
    out = dict(spec)
    if isinstance(out.get("slides"), list):
        slides = []
        for sl in out["slides"]:
            sl = _rename_keys(sl, KITE_LEGACY_SLIDE_KEYS)
            if isinstance(sl, dict) and isinstance(sl.get("bars"), list):
                sl["bars"] = [_rename_keys(b, KITE_LEGACY_BAR_KEYS) for b in sl["bars"]]
            slides.append(sl)
        out["slides"] = slides
    return out
