#!/usr/bin/env python3
"""Manifest key migration v0/v1 -> v2 (Vietnamese keys -> English, LOW-227).

The key table lives in `docs/tu_dien_ten/manifest_keys_v2.json` (approved by Ông Chủ
17/09/2026); this module only applies it, section by section, because the same
old key means different things at different levels (`ma` is `id` on an image but
`board_id` inside `brand_match`; `kieu` is `capture_kind` on an image but `kind`
inside `ranking`). Only KEYS change — values stay byte-identical.

Every function is pure and idempotent: already-English keys pass through, and a
dict holding both an old key and its new name raises instead of guessing.
"""
import json
from functools import lru_cache
from pathlib import Path

KEYS_FILE = Path(__file__).resolve().parent / "docs" / "tu_dien_ten" / "manifest_keys_v2.json"


class KeyConflict(ValueError):
    pass


@lru_cache(maxsize=1)
def key_table() -> dict:
    return json.loads(KEYS_FILE.read_text(encoding="utf-8"))


def _rename(d: dict, section: str) -> dict:
    table = key_table()[section]
    out = {}
    for k, v in d.items():
        new = table.get(k, k)
        if new in out or (new != k and new in d):
            raise KeyConflict(f"{section}: both {k!r} and {new!r} present")
        out[new] = v
    return out


def _nested(d: dict, key: str, section: str) -> None:
    if isinstance(d.get(key), dict):
        d[key] = _rename(d[key], section)


def migrate_ranking(r):
    return _rename(r, "ranking") if isinstance(r, dict) else r


def migrate_image(a):
    if not isinstance(a, dict):
        return a
    a = _rename(a, "image")
    _nested(a, "concept", "image.concept")
    _nested(a, "brand_match", "image.brand_match")
    _nested(a, "entity", "image.entity")
    if isinstance(a.get("ranking"), dict):
        a["ranking"] = migrate_ranking(a["ranking"])
    return a


def migrate_material(t):
    if not isinstance(t, dict):
        return t
    t = _rename(t, "manifest.material")
    if isinstance(t.get("sources"), list):
        t["sources"] = [_rename(s, "manifest.material.sources[]") if isinstance(s, dict) else s
                        for s in t["sources"]]
    return t


def is_manifest(m) -> bool:
    """Engine manifests only — `xong.json` is also the file name of Itachi's
    `{khoa, slides}` and Ada's daily report, which must be left alone."""
    return isinstance(m, dict) and ("anh" in m or "images" in m) and "draft_id" in m


def migrate_manifest(m: dict) -> dict:
    """Rename keys of an engine manifest to v2. Does NOT compute derived keys or
    set `version` — `schema.read_manifest` owns that, so a migrated file and an
    on-the-fly read go through the same code."""
    m = _rename(m, "manifest")
    if isinstance(m.get("images"), list):
        m["images"] = [migrate_image(a) for a in m["images"]]
    if "material" in m:
        m["material"] = migrate_material(m["material"])
    if isinstance(m.get("dropped"), list):
        m["dropped"] = [_rename(r, "manifest.dropped[]") if isinstance(r, dict) else r for r in m["dropped"]]
    _nested(m, "missing_images", "manifest.missing_images")
    if isinstance(m.get("ranking"), dict):
        m["ranking"] = migrate_ranking(m["ranking"])
    return m


def migrate_sidecar_image(d: dict) -> dict:
    d = _rename(d, "sidecar_image")
    if isinstance(d.get("redo_reasons"), list):
        d["redo_reasons"] = [_rename(x, "sidecar_image.redo_reasons[]") if isinstance(x, dict) else x
                             for x in d["redo_reasons"]]
    return d


def migrate_golden_sample(s: dict) -> dict:
    """One line of `state/golden/v0/samples.jsonl`: `{id, story, n, md5, thumb, image}`
    — only the embedded image dict carries manifest keys."""
    s = dict(s)
    if isinstance(s.get("image"), dict):
        s["image"] = migrate_image(s["image"])
    return s
