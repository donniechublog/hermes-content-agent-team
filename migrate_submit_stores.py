#!/usr/bin/env python3
"""Writer/designer submit stores -> English keys (LOW-242). One-shot.

STOP FIRST: the gateways / kanban workers of the image roles (Dre/Ethan/Kite) and the
writers (Miles/Jika), and hermes-approve, must not run while this runs — a submit
appending to used_images.jsonl or rewriting previous_submission.json / submit_count.json
mid-run cannot be detected from here and would be overwritten or left half old.
Deploy the code of LOW-242 and run this in the same stop window.

  state/<brand>/prepare/<draft>/previous_submission.json   submit_common.send_album
  state/<brand>/prepare/<draft>/submit_count.json          submit_common.count_round_error
  state/<brand>/used_images.jsonl                          image_rules_<role>.record_used
(each also in the single-brand layout state/…)

Table: docs/tu_dien_ten/submit_keys_v2.json, copied into the maps below
(tests/test_migrate_submit_stores.py checks they stay equal). `anh` in a previous
submission is a list of image ids for Dre (-> image_ids) and ONE id for Ethan
(-> image); the value's type decides, any other type is refused. `lan`/`luc` mean
different things per store (submission count vs repeat count, display time vs epoch),
hence one map per store. Keys outside the table (hook, theme, hand-written extras…)
are kept and listed in the journal. Any other shape (not an object, old and new name
side by side, two old names landing on one new name, a renamed value of the wrong
type, a used_images line that parses but is not an object) is reported and NOTHING is
written. A used_images line that does not parse as JSON is kept verbatim (readers skip
it too) and counted. Unchanged lines keep their exact bytes; line order is preserved.
Originals go into one tar.gz, every change into a journal (jsonl) next to it;
re-running is a no-op.

    venv/bin/python migrate_submit_stores.py --dry-run
    venv/bin/python migrate_submit_stores.py [--state state]
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

# ---- maps, (old -> new) from the approved table docs/tu_dien_ten/submit_keys_v2.json
PREVIOUS_SUBMISSION_KEY_MAP = {"bia": "cover_image", "anh2": "image2", "hinh": "image_ids",
                               "lan": "submission_count", "luc": "submitted_at"}
# `anh` by value type: Dre wrote a list of ids, Ethan a single id.
PREVIOUS_SUBMISSION_IMAGE_BY_TYPE = {"list": "image_ids", "str": "image"}
SUBMIT_COUNT_KEY_MAP = {"ky": "error_signature", "lan": "repeat_count", "luc": "updated_at",
                        "loi_cuoi": "last_errors"}
USED_IMAGES_LINE_KEY_MAP = {"vai": "role", "tin": "story_key", "ten": "file_name", "luc": "used_at"}

# Types a renamed value may have (the writers' own types; None where the writer can store it).
_NUM = (int, float)
PREVIOUS_SUBMISSION_TYPES = {"cover_image": (str, type(None)), "image2": (str, type(None)), "image_ids": (list,),
                             "image": (str,), "submission_count": (int,), "submitted_at": (str,)}
SUBMIT_COUNT_TYPES = {"error_signature": (str,), "repeat_count": (int,), "updated_at": _NUM,
                      "last_errors": (list,)}
USED_IMAGES_LINE_TYPES = {"role": (str,), "story_key": (str,), "file_name": (str,), "used_at": _NUM}

# English keys the writers already use (not in the table) — anything else is reported as kept.
FIXED_KEYS = {
    "previous_submission": {"hook", "theme", "hero", "remakes", "message_id"},
    "submit_count": set(),
    "used_images_line": {"dhash", "draft_id", "md5"},
}

OLD_IMAGE_KEY = "anh"


class BadShape(ValueError):
    pass


def _type_name(v) -> str:
    return type(v).__name__


def _check_type(where: str, key: str, v, types: dict) -> None:
    want = types.get(key)
    if want is None:
        return
    if isinstance(v, bool) or not isinstance(v, want):
        raise BadShape(f"{where}{key} is {_type_name(v)}, expected "
                       + " or ".join("null" if t is type(None) else t.__name__ for t in want))


def _rename(d, key_map: dict, types: dict, fixed: set, where: str, unknown: set) -> dict:
    """Rename keys in place of order. `key_map` values may be a callable(value) -> new name."""
    if not isinstance(d, dict):
        raise BadShape(f"{where or 'top level'} is {_type_name(d)}, expected object")
    new_names = {v for v in key_map.values() if isinstance(v, str)} | set(types)
    known = set(key_map) | new_names | fixed
    out = {}
    for k, v in d.items():
        target = key_map.get(k, k)
        new = target(v) if callable(target) else target
        if new != k and new in d:
            raise BadShape(f"{where}both {k!r} and {new!r}")
        if new in out:
            raise BadShape(f"{where}{k!r} and another old key both become {new!r}")
        if k not in known:
            unknown.add(f"{where}{k}")
        if new != k or k in types:
            _check_type(where, new, v, types)
        out[new] = v
    return out


def _previous_image_key(v) -> str:
    new = PREVIOUS_SUBMISSION_IMAGE_BY_TYPE.get(_type_name(v))
    if new is None:
        raise BadShape(f"{OLD_IMAGE_KEY!r} is {_type_name(v)}, expected list (Dre) or str (Ethan)")
    return new


# ---------------------------------------------------------------- per store
def migrate_previous_submission(d, unknown: set) -> dict:
    key_map = {**PREVIOUS_SUBMISSION_KEY_MAP, OLD_IMAGE_KEY: _previous_image_key}
    return _rename(d, key_map, PREVIOUS_SUBMISSION_TYPES, FIXED_KEYS["previous_submission"], "", unknown)


def migrate_submit_count(d, unknown: set) -> dict:
    return _rename(d, SUBMIT_COUNT_KEY_MAP, SUBMIT_COUNT_TYPES, FIXED_KEYS["submit_count"], "", unknown)


def migrate_used_images(text: str, unknown: set) -> tuple:
    """(new text, changed line count, unparseable line count). Line order, blank lines,
    the trailing newline and every unchanged line are kept byte for byte."""
    lines = text.split("\n")
    out, changed, broken = [], 0, 0
    for i, line in enumerate(lines, 1):
        if not line.strip():
            out.append(line)
            continue
        try:
            d = json.loads(line)
        except ValueError:
            broken += 1
            out.append(line)
            continue
        if not isinstance(d, dict):
            raise BadShape(f"line {i} is {_type_name(d)}, expected object")
        new = _rename(d, USED_IMAGES_LINE_KEY_MAP, USED_IMAGES_LINE_TYPES,
                      FIXED_KEYS["used_images_line"], f"line {i}: ", unknown)
        if list(new) == list(d):
            out.append(line)
        else:
            out.append(json.dumps(new, ensure_ascii=False))
            changed += 1
    return "\n".join(out), changed, broken


# ---------------------------------------------------------------- discovery
def _both_layouts(state: Path, pattern: str) -> list:
    return sorted(set(state.glob(f"*/{pattern}")) | set(state.glob(pattern)))


def find_files(state: Path) -> list:
    """[(kind, path)] in a stable order."""
    out = []
    for p in _both_layouts(state, f"{sp.PREPARE_DIR}/*/{sp.PREVIOUS_SUBMISSION_FILE}"):
        out.append(("previous_submission", p))
    for p in _both_layouts(state, f"{sp.PREPARE_DIR}/*/{sp.SUBMIT_COUNT_FILE}"):
        out.append(("submit_count", p))
    for p in _both_layouts(state, sp.USED_IMAGES_FILE):
        out.append(("used_images", p))
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
    ap = argparse.ArgumentParser(description="writer/designer submit stores -> English keys (LOW-242)")
    ap.add_argument("--state", default=str(env_load.ROOT / "state"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    state = Path(a.state)
    base = state.parent

    plans, errors = [], []
    for kind, p in find_files(state):
        rel = _arcname(p, base)
        unknown: set = set()
        extra = []
        try:
            text = p.read_text(encoding="utf-8")
            if kind == "used_images":
                new_text, changed, broken = migrate_used_images(text, unknown)
                if broken:
                    extra.append(f"kept {broken} unparseable line(s)")
                row = {"lines_changed": changed, "unparseable_lines_kept": broken}
                if new_text != text:
                    plans.append((p, kind, new_text, row, unknown))
                status = "migrate" if new_text != text else "unchanged"
                if changed:
                    extra.insert(0, f"{changed} line(s)")
            else:
                old = json.loads(text)
                if kind == "previous_submission":
                    new = migrate_previous_submission(old, unknown)
                    indent = 2                        # as submit_common.send_album writes it
                else:
                    new = migrate_submit_count(old, unknown)
                    indent = None                     # as submit_common.count_round_error writes it
                status = "migrate" if list(new) != list(old) else "unchanged"
                if status == "migrate":
                    new_text = json.dumps(new, ensure_ascii=False, indent=indent)
                    plans.append((p, kind, new_text, {"from_keys": list(old), "to_keys": list(new)}, unknown))
        except (ValueError, OSError) as e:
            errors.append(f"{rel}: {type(e).__name__}: {e}")
            continue
        if unknown:
            extra.append("kept unknown keys: " + ", ".join(sorted(unknown)))
        print(f"{status:9} {rel}" + (f"  ({'; '.join(extra)})" if extra else ""))

    for e in errors:
        print(f"[LOI] {e}", file=sys.stderr)
    if errors:
        print(f"{len(errors)} file(s) refused — nothing written", file=sys.stderr)
        return 1
    if not plans:
        print("nothing to do (already migrated)")
        return 0
    if a.dry_run:
        print(f"DRY RUN — {len(plans)} file(s) would be migrated, nothing written")
        return 0
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = base / f"low242_submit_stores_backup_{stamp}.tar.gz"
    with tarfile.open(backup, "w:gz") as tar:
        for p, *_ in plans:
            tar.add(p, arcname=_arcname(p, base))
    journal = base / f"low242_submit_stores_{stamp}.journal.jsonl"
    with journal.open("w", encoding="utf-8") as fh:
        for p, kind, new_text, row, unknown in plans:
            _write_text_atomic(p, new_text)
            fh.write(json.dumps({"file": str(p), "kind": kind, **row, "kept_unknown_keys": sorted(unknown)},
                                ensure_ascii=False) + "\n")
    print(f"written {len(plans)} file(s); originals in {backup}; journal {journal}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
