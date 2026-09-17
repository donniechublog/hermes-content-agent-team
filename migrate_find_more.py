#!/usr/bin/env python3
"""find_more.json -> English keys (LOW-237). One-shot, engines/find_more_images stopped.

  state/<brand>/prepare/<draft_id>/find_more.json   {"luot": n, "da_thu": [...]}
                                                  -> {"run_count": n, "tried_queries": [...]}
  (also state/prepare/<draft_id>/ for the single-brand layout)

Table: docs/tu_dien_ten/image_search_keys_v2.json ("find_more_json"), copied into KEY_PAIRS. Only
the two keys change, values are kept as-is. A file with any other shape (not a dict, unknown key,
wrong value type, old and new name side by side) is reported and NOTHING is written; a draft whose
engine pid is alive is refused the same way. Originals go into one tar.gz, every written file into a journal
(jsonl) next to it; re-running is a no-op.

    venv/bin/python migrate_find_more.py --dry-run
    venv/bin/python migrate_find_more.py
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

# (old, new) from the approved table docs/tu_dien_ten/image_search_keys_v2.json "find_more_json";
# tests/test_migrate_find_more.py checks they stay equal.
KEY_MAP = {"luot": "run_count", "da_thu": "tried_queries"}
KEY_PAIRS = tuple(KEY_MAP.items())


class BadShape(ValueError):
    pass


def table() -> dict:
    return dict(KEY_PAIRS)


def find_files(state: Path) -> list:
    pattern = f"{sp.PREPARE_DIR}/*/{sp.FIND_MORE_FILE}"
    return sorted(set(state.glob(f"*/{pattern}")) | set(state.glob(pattern)))


def migrate(d, t: dict) -> dict:
    """Old or new shape -> new shape. Raises BadShape for anything else."""
    if not isinstance(d, dict):
        raise BadShape(f"not an object: {type(d).__name__}")
    known = set(t) | set(t.values())
    unknown = sorted(set(d) - known)
    if unknown:
        raise BadShape(f"unknown keys {unknown}")
    out = {}
    for k, v in d.items():
        new = t.get(k, k)
        if new != k and new in d:
            raise BadShape(f"both {k!r} and {new!r}")
        out[new] = v
    run_count, tried = out.get("run_count", 0), out.get("tried_queries", [])
    if not isinstance(run_count, int) or isinstance(run_count, bool):
        raise BadShape(f"run_count is {type(run_count).__name__}, expected int")
    if not isinstance(tried, list):
        raise BadShape(f"tried_queries is {type(tried).__name__}, expected list")
    return out


def _pid_alive(p: Path) -> bool:
    try:
        os.kill(int(p.read_text().strip()), 0)
        return True
    except (OSError, ValueError):
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="find_more.json -> English keys (LOW-237)")
    ap.add_argument("--state", default=str(env_load.ROOT / "state"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    state, t = Path(a.state), table()

    plans, errors = [], []
    for p in find_files(state):
        rel = p.relative_to(state.parent)
        if _pid_alive(p.parent / sp.RUNNING_PID_FILE):
            errors.append(f"{rel}: engine/find_more_images still running")
            continue
        try:
            old = json.loads(p.read_text(encoding="utf-8"))
            new = migrate(old, t)
        except (ValueError, OSError) as e:
            errors.append(f"{rel}: {type(e).__name__}: {e}")
            continue
        status = "migrate" if new != old else "unchanged"
        print(f"{status:9} {rel}")
        if new != old:
            plans.append((p, old, new))
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
    backup = state.parent / f"low237_find_more_backup_{stamp}.tar.gz"
    with tarfile.open(backup, "w:gz") as tar:
        for p, _, _ in plans:
            tar.add(p, arcname=str(p.relative_to(state.parent)))
    journal = state.parent / f"low237_find_more_{stamp}.journal.jsonl"
    with journal.open("w", encoding="utf-8") as fh:
        for p, old, new in plans:
            env_load.write_json(p, new)
            fh.write(json.dumps({"file": str(p), "from_keys": sorted(old), "to_keys": sorted(new)},
                                ensure_ascii=False) + "\n")
    print(f"written {len(plans)} file(s); originals in {backup}; journal {journal}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
