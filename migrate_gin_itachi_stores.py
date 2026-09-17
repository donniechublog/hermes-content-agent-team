#!/usr/bin/env python3
"""Gin/Itachi workdir stores -> English keys (LOW-247, part of LOW-243). One-shot.

STOP FIRST: the Gin and Itachi gateways / kanban workers must not run while this runs — a
prepare rewriting regions_ocr.json or a role rewriting spec.json mid-run cannot be detected
from here. Deploy the code of LOW-247 and run this in the same stop window.

  state/<brand>/prepare/gin_<id>/regions_ocr.json     cache: itachi_prepare re-uses it, gin_submit reads it
  state/<brand>/prepare/gin_<id>/regions.json         itachi_prepare re-reads it while clean_background.png exists
  state/<brand>/prepare/gin_<id>/spec.json            Gin spec (gin_submit also still accepts the old names)
  state/<brand>/prepare/itachi_<set>/manifest.json    itachi_submit re-reads it on a re-submit without prepare
  state/<brand>/prepare/itachi_<set>/spec.json        Itachi spec (itachi_submit also still accepts the old names)
(each also in the single-brand layout state/prepare/…)

deck.spec.json is NOT migrated: itachi_submit regenerates it on every submit and deck.py
still accepts the old names.

Table: docs/tu_dien_ten/gin_itachi_keys_v2.json, copied into the maps below
(tests/test_gin_itachi_keys.py checks they stay equal). Keys outside the table are kept and
listed in the journal. Any other shape (not an object/list where one is expected, old and new
name side by side, an unknown `nen` value) is reported and NOTHING is written. A spec.json that
does not parse as JSON is kept verbatim and counted (the submit scripts report it to the role).
Originals go into one tar.gz, every change into a journal (jsonl) next to it; re-running is a
no-op.

    venv/bin/python migrate_gin_itachi_stores.py --dry-run
    venv/bin/python migrate_gin_itachi_stores.py [--state state]
"""
import argparse
import json
import os
import sys
import tarfile
import time
from pathlib import Path

import env_load
import state_paths as sp

# ---- maps, (old -> new) from the approved table docs/tu_dien_ten/gin_itachi_keys_v2.json
REGIONS_OCR_KEY_MAP = {"anh": "image_path", "vung": "regions"}
REGION_KEY_MAP = {"stt": "number", "nen": "background_kind", "std_nen": "background_std",
                  "nen_rgb": "background_rgb", "cao_net": "ink_height", "muc": "ink_ratio", "can": "align"}
BACKGROUND_KIND_VALUE_MAP = {"phang": "flat", "anh": "photo"}
REGIONS_JSON_ITEM_KEY_MAP = {"stt": "number"}
GIN_SPEC_KEY_MAP = {"gop": "merges", "vung": "region_texts", "ghi_chu": "note", "ep_phang": "force_flat",
                    "giu": "mask_keep", "xoa_them": "mask_extra"}
GIN_REGION_OVERRIDE_KEY_MAP = {"can": "align"}
ITACHI_MANIFEST_KEY_MAP = {"khoa": "set_id"}
ITACHI_MANIFEST_SLIDE_KEY_MAP = {"anh": "image_path", "nen_sach": "clean_background_path", "vung": "regions",
                                 "so_vung_ocr": "ocr_region_count"}
ITACHI_SPEC_SLIDE_KEY_MAP = {"nguon": "slide_id", "cach": "mode", "vung": "region_texts", "gop": "merges",
                             "bg_anh": "use_clean_background"}
ITACHI_MODE_VALUE_MAP = {"tai_cho": "in_place"}      # compared after .lower(), like itachi_submit
DECK_SLIDE_KEY_MAP = {"bg_anh": "bg_image", "nhan": "labels", "ghi_chu": "annotation"}
DECK_ANNOTATION_KEY_MAP = {"nghieng": "tilt"}
DECK_SUB_COL_VALUE_MAP = {"den": "black"}

# English keys the writers already use (not in the table) — anything else is reported as kept.
FIXED_KEYS = {
    "regions_ocr": {"id", "w", "h"},
    "region": {"box", "x", "y", "w", "h", "text", "conf", "color_rgb", "adv", "font"},
    "regions_json_item": {"x", "y", "w", "h", "color_rgb", "ocr_text", "conf"},
    "gin_spec": set(),
    "itachi_manifest": {"slides"},
    "itachi_manifest_slide": {"id", "w", "h"},
    "itachi_spec": {"slides"},
    "itachi_spec_slide": {"layout", "badge", "heading", "heading_col_rgb", "subs", "serif", "sans", "rows",
                          "footer", "title1", "title2", "sub", "items", "footer1", "footer2", "tiers",
                          "title_col_rgb", "bg", "fg", "bg_image"},
}


class BadShape(ValueError):
    pass


def _type_name(v) -> str:
    return type(v).__name__


def _rename(d, key_map: dict, fixed: set, where: str, unknown: set) -> dict:
    """Rename keys keeping their order; refuse old+new side by side."""
    if not isinstance(d, dict):
        raise BadShape(f"{where or 'top level'} is {_type_name(d)}, expected object")
    known = set(key_map) | set(key_map.values()) | fixed
    out = {}
    for k, v in d.items():
        new = key_map.get(k, k)
        if new != k and new in d:
            raise BadShape(f"{where}both {k!r} and {new!r}")
        if k not in known:
            unknown.add(f"{where}{k}")
        out[new] = v
    return out


def _list(v, where: str) -> list:
    if not isinstance(v, list):
        raise BadShape(f"{where} is {_type_name(v)}, expected list")
    return v


# ---------------------------------------------------------------- per store
def migrate_region(r, where: str, unknown: set) -> dict:
    out = _rename(r, REGION_KEY_MAP, FIXED_KEYS["region"], where, unknown)
    kind = out.get("background_kind")
    if "background_kind" in out:
        if kind in BACKGROUND_KIND_VALUE_MAP:
            out["background_kind"] = BACKGROUND_KIND_VALUE_MAP[kind]
        elif kind not in BACKGROUND_KIND_VALUE_MAP.values():
            raise BadShape(f"{where}background_kind is {kind!r}, expected one of "
                           + ", ".join(sorted(BACKGROUND_KIND_VALUE_MAP) + sorted(BACKGROUND_KIND_VALUE_MAP.values())))
    return out


def migrate_regions_ocr(d, unknown: set) -> dict:
    out = _rename(d, REGIONS_OCR_KEY_MAP, FIXED_KEYS["regions_ocr"], "", unknown)
    if "regions" in out:
        out["regions"] = [migrate_region(r, f"regions[{i}].", unknown)
                          for i, r in enumerate(_list(out["regions"], "regions"))]
    return out


def migrate_regions_json(d, unknown: set) -> list:
    return [_rename(r, REGIONS_JSON_ITEM_KEY_MAP, FIXED_KEYS["regions_json_item"], f"[{i}].", unknown)
            for i, r in enumerate(_list(d, "top level"))]


def migrate_gin_spec(d, unknown: set) -> dict:
    out = _rename(d, GIN_SPEC_KEY_MAP, FIXED_KEYS["gin_spec"], "", unknown)
    texts = out.get("region_texts")
    if isinstance(texts, dict):                  # a wrong type is the role's [LOI] to fix, keep it
        out["region_texts"] = {k: _rename(v, GIN_REGION_OVERRIDE_KEY_MAP, {"text", "font", "color_rgb"},
                                          f"region_texts.{k}.", unknown) if isinstance(v, dict) else v
                               for k, v in texts.items()}
    return out


def migrate_itachi_manifest(d, unknown: set) -> dict:
    out = _rename(d, ITACHI_MANIFEST_KEY_MAP, FIXED_KEYS["itachi_manifest"], "", unknown)
    if "slides" in out:
        slides = []
        for i, s in enumerate(_list(out["slides"], "slides")):
            w = f"slides[{i}]."
            s = _rename(s, ITACHI_MANIFEST_SLIDE_KEY_MAP, FIXED_KEYS["itachi_manifest_slide"], w, unknown)
            if "regions" in s:
                s["regions"] = [_rename(r, REGIONS_JSON_ITEM_KEY_MAP, FIXED_KEYS["regions_json_item"],
                                        f"{w}regions[{j}].", unknown)
                                for j, r in enumerate(_list(s["regions"], f"{w}regions"))]
            slides.append(s)
        out["slides"] = slides
    return out


def migrate_itachi_spec(d, unknown: set) -> dict:
    out = _rename(d, {}, FIXED_KEYS["itachi_spec"], "", unknown)
    if "slides" in out:
        slides = []
        for i, s in enumerate(_list(out["slides"], "slides")):
            w = f"slides[{i}]."
            # Itachi's own keys first: `bg_anh` here is the flag (use_clean_background), not deck's path.
            known = FIXED_KEYS["itachi_spec_slide"] | set(DECK_SLIDE_KEY_MAP) | set(DECK_SLIDE_KEY_MAP.values())
            s = _rename(s, ITACHI_SPEC_SLIDE_KEY_MAP, known, w, unknown)
            s = _rename(s, DECK_SLIDE_KEY_MAP, known | set(ITACHI_SPEC_SLIDE_KEY_MAP.values()), w, set())
            mode = s.get("mode")
            if isinstance(mode, str) and mode.lower() in ITACHI_MODE_VALUE_MAP:
                s["mode"] = ITACHI_MODE_VALUE_MAP[mode.lower()]
            if isinstance(s.get("annotation"), dict):
                s["annotation"] = _rename(s["annotation"], DECK_ANNOTATION_KEY_MAP, {"text", "max_w", "x"},
                                          f"{w}annotation.", unknown)
            if isinstance(s.get("subs"), list):
                s["subs"] = [{**sub, "col": DECK_SUB_COL_VALUE_MAP[sub["col"]]}
                             if isinstance(sub, dict) and isinstance(sub.get("col"), str)
                             and sub["col"] in DECK_SUB_COL_VALUE_MAP else sub
                             for sub in s["subs"]]
            slides.append(s)
        out["slides"] = slides
    return out


MIGRATE = {"regions_ocr": migrate_regions_ocr, "regions_json": migrate_regions_json, "gin_spec": migrate_gin_spec,
           "itachi_manifest": migrate_itachi_manifest, "itachi_spec": migrate_itachi_spec}
SPEC_KINDS = {"gin_spec", "itachi_spec"}
SPEC_FILE = "spec.json"


# ---------------------------------------------------------------- discovery
def _both_layouts(state: Path, pattern: str) -> list:
    return sorted(set(state.glob(f"*/{pattern}")) | set(state.glob(pattern)))


def find_files(state: Path) -> list:
    """[(kind, path)] in a stable order."""
    out = []
    for kind, pattern in (("regions_ocr", f"gin_*/{sp.GIN_REGIONS_OCR_FILE}"),
                          ("regions_json", f"gin_*/{sp.GIN_REGIONS_FILE}"),
                          ("gin_spec", f"gin_*/{SPEC_FILE}"),
                          ("itachi_manifest", f"itachi_*/{sp.MANIFEST_FILE}"),
                          ("itachi_spec", f"itachi_*/{SPEC_FILE}")):
        out += [(kind, p) for p in _both_layouts(state, f"{sp.PREPARE_DIR}/{pattern}")]
    return out


def _arcname(p: Path, base: Path) -> str:
    try:
        return str(p.relative_to(base))
    except ValueError:
        return p.name


def _write_text_atomic(p: Path, text: str) -> None:
    tmp = p.with_name(f"{p.name}.tmp.{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, p)


def main() -> int:
    ap = argparse.ArgumentParser(description="Gin/Itachi workdir stores -> English keys (LOW-247)")
    ap.add_argument("--state", default=str(env_load.ROOT / "state"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    state = Path(a.state)
    base = state.parent

    plans, errors, unparseable = [], [], 0
    for kind, p in find_files(state):
        rel = _arcname(p, base)
        unknown: set = set()
        try:
            text = p.read_text(encoding="utf-8")
            try:
                old = json.loads(text)
            except ValueError:
                if kind not in SPEC_KINDS:
                    raise
                unparseable += 1
                print(f"{'kept':9} {rel}  (not valid JSON, left as is)")
                continue
            new = MIGRATE[kind](old, unknown)
        except (ValueError, OSError) as e:
            errors.append(f"{rel}: {type(e).__name__}: {e}")
            continue
        status = "migrate" if json.dumps(new) != json.dumps(old) else "unchanged"     # key order counts
        if status == "migrate":
            plans.append((p, kind, json.dumps(new, ensure_ascii=False, indent=1), unknown))
        print(f"{status:9} {rel}" + (f"  (kept unknown keys: {', '.join(sorted(unknown))})" if unknown else ""))

    for e in errors:
        print(f"[LOI] {e}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} file(s) refused — nothing written", file=sys.stderr)
        return 1
    if not plans:
        print("nothing to do (already migrated)" + (f"; {unparseable} unparseable spec(s) kept" if unparseable else ""))
        return 0
    if a.dry_run:
        print(f"DRY RUN — {len(plans)} file(s) would be migrated, nothing written")
        return 0
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = base / f"low247_gin_itachi_stores_backup_{stamp}.tar.gz"
    with tarfile.open(backup, "w:gz") as tar:
        for p, *_ in plans:
            tar.add(p, arcname=_arcname(p, base))
    journal = base / f"low247_gin_itachi_stores_{stamp}.journal.jsonl"
    with journal.open("w", encoding="utf-8") as fh:
        for p, kind, new_text, unknown in plans:
            _write_text_atomic(p, new_text)
            fh.write(json.dumps({"file": str(p), "kind": kind, "kept_unknown_keys": sorted(unknown)},
                                ensure_ascii=False) + "\n")
    print(f"written {len(plans)} file(s); originals in {backup}; journal {journal}"
          + (f"; {unparseable} unparseable spec(s) kept" if unparseable else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
