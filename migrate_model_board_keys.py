#!/usr/bin/env python3
"""Model-board stores -> English keys (LOW-233). One-shot, model-watch cron + gateways stopped.

  state/<brand>/models_seen.json   top keys (cap_nhat, xep_hang, aa_da_bao) + board keys under rankings
  state/model_audition.json        per-model keys (dat, giay, ty_le_dau)  [also any brand-level copy]
  state/<brand>/required_nova.json dedup ids "<board>|<name>" and item "loai" for renamed board keys

Table: docs/tu_dien_ten/model_board_keys_v2.json. Only keys (and the board key where it is
stored as an id or `loai`) change. Originals go into one tar.gz; re-running is a no-op;
a dict holding both an old key and its new name aborts before anything is written.

    venv/bin/python migrate_model_board_keys.py --dry-run
    venv/bin/python migrate_model_board_keys.py
"""
import argparse
import json
import sys
import tarfile
import time
from pathlib import Path

import env_load

TABLE_FILE = Path(__file__).resolve().parent / "docs" / "tu_dien_ten" / "model_board_keys_v2.json"


class Conflict(ValueError):
    pass


def table() -> dict:
    return json.loads(TABLE_FILE.read_text(encoding="utf-8"))


def _rename(d: dict, mapping: dict, where: str) -> dict:
    out = {}
    for k, v in d.items():
        new = mapping.get(k, k)
        if new in out or (new != k and new in d):
            raise Conflict(f"{where}: both {k!r} and {new!r}")
        out[new] = v
    return out


def migrate_models_seen(d: dict, t: dict) -> dict:
    d = _rename(d, t["models_seen.json"], "models_seen")
    if isinstance(d.get("rankings"), dict):
        d["rankings"] = _rename(d["rankings"], t["board_keys"], "models_seen.rankings")
    return d


def migrate_audition(d: dict, t: dict) -> dict:
    return {m: (_rename(v, t["model_audition.json"], f"model_audition.{m}") if isinstance(v, dict) else v)
            for m, v in d.items()}


def migrate_required(d: dict, t: dict) -> dict:
    boards = t["board_keys"]
    out = {}
    for k, item in d.items():
        board, sep, rest = k.partition("|")
        nk = f"{boards[board]}|{rest}" if sep and board in boards else k
        if nk in out or (nk != k and nk in d):
            raise Conflict(f"required: both {k!r} and {nk!r}")
        if isinstance(item, dict) and item.get("loai") in boards:
            item = dict(item, loai=boards[item["loai"]])
        out[nk] = item
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Model-board stores -> English keys (LOW-233)")
    ap.add_argument("--state", default=str(env_load.ROOT / "state"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    state, t = Path(a.state), table()

    jobs = [(p, migrate_models_seen) for p in sorted(state.glob("*/models_seen.json"))]
    jobs += [(p, migrate_audition) for p in sorted(state.glob("model_audition.json")) + sorted(state.glob("*/model_audition.json"))]
    jobs += [(p, migrate_required) for p in sorted(state.glob("*/required_nova.json"))]

    plans, errors = [], []
    for p, fn in jobs:
        try:
            old = json.loads(p.read_text(encoding="utf-8"))
            new = fn(old, t)
        except (ValueError, Conflict) as e:
            errors.append(f"{p}: {type(e).__name__}: {e}")
            continue
        state_ = "migrate" if new != old else "unchanged"
        print(f"{state_:9} {p.relative_to(state.parent)}")
        if new != old:
            plans.append((p, new))
    for e in errors:
        print(f"[LOI] {e}", file=sys.stderr)
    if errors:
        return 1
    if not plans:
        print("nothing to do (already migrated)")
        return 0
    if a.dry_run:
        print("DRY RUN — nothing written")
        return 0
    backup = state.parent / f"low233_model_keys_backup_{time.strftime('%Y%m%d-%H%M%S')}.tar.gz"
    with tarfile.open(backup, "w:gz") as tar:
        for p, _ in plans:
            tar.add(p, arcname=str(p.relative_to(state.parent)))
    for p, new in plans:
        env_load.write_json(p, new)
    print(f"written; originals in {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
