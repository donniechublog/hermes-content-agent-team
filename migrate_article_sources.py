#!/usr/bin/env python3
"""article_source_<id>.json -> English keys + English page kinds (LOW-238). One-shot,
approve/engines stopped.

  state/<brand>/article_source_<draft_id>.json   (also state/ for the single-brand layout)
  {"tieu_de", "tieu_de_en", "link_goc", "link_gnews"?, "trang": [{"url", "loai", "tieu_de", "toa_soan"}]}
  -> {"title", "title_en", "source_url", "gnews_url"?, "pages": [{"url", "kind", "title", "outlet_url"}]}
  pages[].kind: gốc/báo/công bố/bảng/giá -> article/other_outlet/announcement/table/price

Table: docs/tu_dien_ten/article_source_keys_v2.json, copied into KEY_MAP / PAGE_KEY_MAP /
KIND_MAP (tests/test_migrate_article_sources.py checks they stay equal). Keys outside the
table (hand-written extras such as tom_tat, y_chinh, pages[].anh) are kept as they are and
listed in the journal. A file with any other shape (top level not a dict, pages not a
list, a page not a dict, an unknown kind value, old and new name side by side) is reported
and NOTHING is written; a draft whose prepare engine pid is alive is refused the same way.
Originals go into one tar.gz, every written file into a journal (jsonl) next to it;
re-running is a no-op.

    venv/bin/python migrate_article_sources.py --dry-run
    venv/bin/python migrate_article_sources.py
"""
import argparse
import json
import os
import sys
import tarfile
import time
from collections import Counter
from pathlib import Path

import env_load
import state_paths as sp

# (old, new) from the approved table docs/tu_dien_ten/article_source_keys_v2.json.
KEY_MAP = {"tieu_de": "title", "tieu_de_en": "title_en", "link_goc": "source_url",
           "link_gnews": "gnews_url", "trang": "pages"}
PAGE_KEY_MAP = {"loai": "kind", "tieu_de": "title", "toa_soan": "outlet_url"}
KIND_MAP = {"gốc": "article", "báo": "other_outlet", "công bố": "announcement",
            "bảng": "table", "giá": "price"}
PAGE_FIXED_KEYS = ("url",)          # already English, not in the table


class BadShape(ValueError):
    pass


def tables() -> tuple:
    return dict(KEY_MAP), dict(PAGE_KEY_MAP), dict(KIND_MAP)


def find_files(state: Path) -> list:
    pattern = f"{sp.ARTICLE_SOURCE_PREFIX}*.json"
    return sorted(set(state.glob(f"*/{pattern}")) | set(state.glob(pattern)))


def draft_id_of(p: Path) -> str:
    return p.name[len(sp.ARTICLE_SOURCE_PREFIX):-len(".json")]


def _rename(d: dict, key_map: dict, where: str) -> tuple:
    """Rename known old keys; returns (new dict, unknown keys kept as-is)."""
    known = set(key_map) | set(key_map.values())
    out, unknown = {}, []
    for k, v in d.items():
        new = key_map.get(k, k)
        if new != k and new in d:
            raise BadShape(f"{where}: both {k!r} and {new!r}")
        if k not in known:
            unknown.append(k)
        out[new] = v
    return out, unknown


def migrate(d, t: tuple = None) -> tuple:
    """Old, mixed or new shape -> (new shape, kept unknown keys, kind values seen).
    Raises BadShape for anything the table does not cover."""
    key_map, page_key_map, kind_map = t or tables()
    if not isinstance(d, dict):
        raise BadShape(f"not an object: {type(d).__name__}")
    out, unknown = _rename(d, key_map, "top level")
    kinds = Counter()
    if "pages" in out:
        pages = out["pages"]
        if not isinstance(pages, list):
            raise BadShape(f"pages is {type(pages).__name__}, expected list")
        new_pages = []
        page_known = set(page_key_map) | set(page_key_map.values()) | set(PAGE_FIXED_KEYS)
        for i, pg in enumerate(pages):
            where = f"pages[{i}]"
            if not isinstance(pg, dict):
                raise BadShape(f"{where} is {type(pg).__name__}, expected object")
            new_pg, _ = _rename(pg, page_key_map, where)
            unknown += [f"{where}.{k}" for k in pg if k not in page_known]
            if "kind" in new_pg:
                kind = new_pg["kind"]
                if not isinstance(kind, str) or (kind not in kind_map and kind not in kind_map.values()):
                    raise BadShape(f"{where}: unknown kind {kind!r}")
                new_pg["kind"] = kind_map.get(kind, kind)
                kinds[kind] += 1
            new_pages.append(new_pg)
        out["pages"] = new_pages
    return out, unknown, dict(kinds)


def _pid_alive(p: Path) -> bool:
    try:
        os.kill(int(p.read_text().strip()), 0)
        return True
    except (OSError, ValueError):
        return False


def main() -> int:
    ap = argparse.ArgumentParser(description="article_source_<id>.json -> English keys (LOW-238)")
    ap.add_argument("--state", default=str(env_load.ROOT / "state"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    state, t = Path(a.state), tables()

    plans, errors = [], []
    for p in find_files(state):
        rel = p.relative_to(state.parent)
        pid = p.parent / sp.PREPARE_DIR / draft_id_of(p) / sp.RUNNING_PID_FILE
        if _pid_alive(pid):
            errors.append(f"{rel}: prepare engine still running ({pid.relative_to(state.parent)})")
            continue
        try:
            old = json.loads(p.read_text(encoding="utf-8"))
            new, unknown, kinds = migrate(old, t)
        except (ValueError, OSError) as e:
            errors.append(f"{rel}: {type(e).__name__}: {e}")
            continue
        status = "migrate" if new != old else "unchanged"
        print(f"{status:9} {rel}" + (f"  (kept unknown keys: {', '.join(unknown)})" if unknown else ""))
        if new != old:
            plans.append((p, old, new, unknown, kinds))
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
    backup = state.parent / f"low238_article_sources_backup_{stamp}.tar.gz"
    with tarfile.open(backup, "w:gz") as tar:
        for p, *_ in plans:
            tar.add(p, arcname=str(p.relative_to(state.parent)))
    journal = state.parent / f"low238_article_sources_{stamp}.journal.jsonl"
    with journal.open("w", encoding="utf-8") as fh:
        for p, old, new, unknown, kinds in plans:
            env_load.write_json(p, new)
            fh.write(json.dumps({"file": str(p), "from_keys": sorted(old), "to_keys": sorted(new),
                                 "page_kinds": kinds, "kept_unknown_keys": unknown},
                                ensure_ascii=False) + "\n")
    print(f"written {len(plans)} file(s); originals in {backup}; journal {journal}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
