#!/usr/bin/env python3
"""Migrate on-disk data to manifest keys v2 (English) — LOW-227, run once on the server at deploy.

Three stores share the image/manifest keys:
  1. state/<brand>/prepare/<draft>/manifest.json   (engine manifest; v0/v1 -> v2)
  2. drafts/<draft>.img.json                    (image sidecar)
  3. state/golden/v0/samples.jsonl              (LOW-224 golden set; image_eval reads it)

A manifest is rewritten as exactly what `schema.read_manifest` returns for it, so a
v0 file gets the same derived keys (`usable_count`, `ranking_count`) that reading it
today would compute — the migrated file and an on-the-fly read cannot disagree.

Each changed file keeps its original bytes next to it as `<name>.v1.bak` (never
overwritten). Files that are already v2, or not an engine manifest (Itachi/Ada
also write files named manifest.json), are left untouched. Re-running is a no-op.

    venv/bin/python migrate_manifest_v2.py --dry-run
    venv/bin/python migrate_manifest_v2.py
"""
import argparse
import json
import shutil
import sys
from pathlib import Path

import env_load
import manifest_migration as mm
import schema
import state_paths

BACKUP_SUFFIX = ".v1.bak"


def _backup(p: Path) -> None:
    b = p.with_name(p.name + BACKUP_SUFFIX)
    if not b.exists():
        shutil.copy2(p, b)


def plan_manifest(p: Path):
    """(new_dict | None, reason) — None means leave the file alone."""
    raw = json.loads(p.read_text(encoding="utf-8"))
    if not mm.is_manifest(raw):
        return None, "not an engine manifest"
    if int(raw.get("version") or 0) >= schema.VERSION_MANIFEST and "phien_ban" not in raw:
        return None, "already v2"
    new = schema.read_manifest(raw)
    if new is None:
        raise mm.KeyConflict(f"read_manifest refused {p}")
    return new, f"v{int(raw.get('phien_ban') or 0)} -> v{new['version']}"


def plan_sidecar(p: Path):
    raw = json.loads(p.read_text(encoding="utf-8"))
    new = mm.migrate_sidecar_image(raw)
    return (None, "unchanged") if new == raw else (new, "renamed")


def plan_golden(p: Path):
    lines = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    new = [mm.migrate_golden_sample(s) for s in lines]
    return (None, "unchanged") if new == lines else (new, f"{len(new)} samples renamed")


def main() -> int:
    ap = argparse.ArgumentParser(description="Migrate manifest/sidecar/golden JSON keys to v2 (LOW-227)")
    ap.add_argument("--state", default=str(env_load.ROOT / "state"), help="state root (holds <brand>/prepare)")
    ap.add_argument("--drafts", default=str(env_load.ROOT / "drafts"))
    ap.add_argument("--dry-run", action="store_true", help="report only, write nothing")
    a = ap.parse_args()
    state, drafts = Path(a.state), Path(a.drafts)

    counts, errors = {}, []

    def handle(kind, p, planner, dump):
        try:
            new, why = planner(p)
        except Exception as e:                                   # noqa: BLE001
            errors.append(f"{p}: {type(e).__name__}: {e}")
            return
        counts[(kind, why if new is None else "migrate")] = counts.get((kind, why if new is None else "migrate"), 0) + 1
        if new is None or a.dry_run:
            return
        _backup(p)
        dump(p, new)

    def dump_json(p, d):
        env_load.write_json(p, d)

    def dump_jsonl(p, rows):
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
        tmp.replace(p)

    for p in sorted(state.glob(f"*/{state_paths.PREPARE_DIR}/*/{state_paths.MANIFEST_FILE}")):
        handle("manifest", p, plan_manifest, dump_json)
    for p in sorted(drafts.glob("*.img.json")):
        handle("img.json", p, plan_sidecar, dump_json)
    golden = state / "golden" / "v0" / "samples.jsonl"
    if golden.exists():
        handle("golden", golden, plan_golden, dump_jsonl)

    for (kind, what), n in sorted(counts.items()):
        print(f"{kind:9} {what:24} {n}")
    for e in errors:
        print(f"[LOI] {e}", file=sys.stderr)
    print("DRY RUN — nothing written" if a.dry_run else "written (originals kept as *.v1.bak)")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
