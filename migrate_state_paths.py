#!/usr/bin/env python3
"""Move on-disk state to the English layout (LOW-228) — run once at deploy, services stopped.

  state/<brand>/chuan_bi/<draft>/{xong.json, goc/, san/, thuong_hieu/xh/…}
      -> state/<brand>/prepare/<draft>/{manifest.json, original/, ready/, brand_match/ranking/…}
  state/chuan_bi.<i>.lock -> state/prepare.<i>.lock
  drafts/<id>.ban_giao.md -> drafts/<id>.handoff.md

Names come from docs/tu_dien_ten/state_paths_v2.json via state_path_migration. Paths
stored INSIDE files are rewritten too (manifest `original_path`/`ready_path`/`workdir`,
render specs, task bodies, briefs, golden samples) by text substitution, so every other
byte of those files stays as it was. History (logs, nhat_ky/, telegram_sent/, *.bak)
is not rewritten.

Before rewriting any file content the originals go into one tar.gz next to the state
dir; renames are listed in a journal. Refuses to run while a draft has a live
running pid. Re-running after success is a no-op.

    venv/bin/python migrate_state_paths.py --dry-run
    venv/bin/python migrate_state_paths.py
"""
import argparse
import json
import os
import sys
import tarfile
import time
from pathlib import Path

import env_load
import state_path_migration as spm
import state_paths as sp

LEGACY = sp.LEGACY_PREPARE_DIR
TEXT_REWRITE_MD = ("brief",)                 # brief.md, brief_<writer>.md


def _pid_alive(p: Path) -> bool:
    try:
        pid = int(p.read_text().strip())
        os.kill(pid, 0)
        return True
    except (OSError, ValueError):
        return False


def plan(state: Path, drafts: Path) -> dict:
    """Everything the run would do, computed without touching the disk."""
    renames, rewrites, errors = [], [], []
    for brand_dir in sorted(p for p in state.iterdir() if p.is_dir()):
        old_root = brand_dir / LEGACY
        if not old_root.is_dir():
            continue
        new_root = brand_dir / sp.PREPARE_DIR
        if new_root.exists():
            errors.append(f"{new_root} already exists next to {old_root}")
            continue
        for draft in sorted(p for p in old_root.iterdir() if p.is_dir()):
            for pid_name in ("dang_chay.pid", sp.RUNNING_PID_FILE):
                if (draft / pid_name).exists() and _pid_alive(draft / pid_name):
                    errors.append(f"{draft / pid_name}: engine still running")
            for dirpath, dirnames, filenames in os.walk(draft, topdown=False):
                here = Path(dirpath)
                top = here == draft
                for name in filenames + dirnames:
                    new = spm.new_name(name, top)
                    if new != name:
                        src = here / name
                        if (here / new).exists():
                            errors.append(f"{src} -> {new}: target exists")
                        renames.append((src, here / new))
                for name in filenames:
                    if name.endswith(".bak") or name.endswith(".log"):
                        continue
                    kind = "json" if name.endswith((".json", ".jsonl")) else (
                        "text" if name.endswith(".md") and (name.startswith(TEXT_REWRITE_MD) or name.endswith(".ban_giao.md")) else None)
                    if kind:
                        rewrites.append((here / name, kind))
        renames.append((old_root, new_root))
    for lock in sorted(state.glob(f"{LEGACY}.*.lock")):
        renames.append((lock, state / sp.LOCK_FILE.format(lock.name.split(".")[1])))
    if drafts.is_dir():
        for p in sorted(drafts.glob("*.ban_giao.md")):
            renames.append((p, p.with_name(spm.new_name(p.name, False))))
            rewrites.append((p, "text"))
        for p in sorted(drafts.glob("*.json")):
            rewrites.append((p, "text" if p.name.endswith((".img.json", ".writer.json")) else "json"))
    golden = state / "golden" / "v0" / "samples.jsonl"
    if golden.exists():
        rewrites.append((golden, "json"))
    return {"renames": renames, "rewrites": rewrites, "errors": errors}


def _new_text(p: Path, kind: str):
    old = p.read_text(encoding="utf-8")
    new = spm.rewrite_text(old) if kind == "text" else spm.rewrite_paths(old)
    if new == old:
        return None
    if p.name.endswith(".json"):
        json.loads(new)
    elif p.name.endswith(".jsonl"):
        for line in new.splitlines():
            if line.strip():
                json.loads(line)
    return new


def main() -> int:
    ap = argparse.ArgumentParser(description="Move state to the English layout (LOW-228)")
    ap.add_argument("--state", default=str(env_load.ROOT / "state"))
    ap.add_argument("--drafts", default=str(env_load.ROOT / "drafts"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    state, drafts = Path(a.state), Path(a.drafts)

    pl = plan(state, drafts)
    content = []
    for p, kind in pl["rewrites"]:
        try:
            new = _new_text(p, kind)
        except ValueError as e:
            pl["errors"].append(f"{p}: rewrite breaks JSON: {e}")
            continue
        if new is not None:
            content.append((p, new))
    n_dirs = sum(1 for s, _ in pl["renames"] if s.is_dir())
    print(f"renames: {len(pl['renames'])} ({n_dirs} dirs) | content rewrites: {len(content)} files")
    for s, d in pl["renames"][:5]:
        print(f"  {s} -> {d.name}")
    for e in pl["errors"]:
        print(f"[LOI] {e}", file=sys.stderr)
    if pl["errors"]:
        return 1
    if not pl["renames"] and not content:
        print("nothing to do (already migrated)")
        return 0
    if a.dry_run:
        print("DRY RUN — nothing written")
        return 0

    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = state.parent / f"low228_state_backup_{stamp}.tar.gz"
    with tarfile.open(backup, "w:gz") as tar:
        for p, _ in content:
            tar.add(p, arcname=str(p.relative_to(state.parent)))
    for p, new in content:
        _write_text(p, new)
    journal = state / f"migrate_state_paths_{stamp}.journal.jsonl"
    with journal.open("w", encoding="utf-8") as fh:
        for s, d in pl["renames"]:
            os.rename(s, d)
            fh.write(json.dumps({"from": str(s), "to": str(d)}, ensure_ascii=False) + "\n")
    print(f"done: content backup {backup}, rename journal {journal}")
    return 0


def _write_text(p: Path, text: str) -> None:
    tmp = p.with_name(p.name + f".tmp{os.getpid()}")
    tmp.write_text(text, encoding="utf-8")
    os.replace(tmp, p)


if __name__ == "__main__":
    sys.exit(main())
