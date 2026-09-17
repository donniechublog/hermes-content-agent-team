#!/usr/bin/env python3
"""Migrate manifest VALUES to English codes, version 2 -> 3 (LOW-230). One-shot, services stopped.

Rewrites, per the approved table docs/tu_dien_ten/manifest_values_v3.json:
  state/<brand>/prepare/<draft>/manifest.json   images[].source/kind/capture_kind/uses,
      images[].brand_match.kind/background_tone, images[].ranking.kind, ranking.kind,
      image_order_by_story_type[], dropped[].source; version -> 3
  state/golden/v0/samples.jsonl                 the embedded image dict, same fields

Only VALUES change. A value that is neither in the table nor listed as already English
is reported and left as is — except an unknown `uses` sentence, which aborts: readers now
compare slot codes, so an unmapped sentence would silently stop counting as a slot.
Originals go into one tar.gz before anything is written; re-running is a no-op.

    venv/bin/python migrate_manifest_v3.py --dry-run
    venv/bin/python migrate_manifest_v3.py
"""
import argparse
import collections
import json
import sys
import tarfile
import time
from pathlib import Path

import env_load
import state_paths as sp

TABLE_FILE = Path(__file__).resolve().parent / "docs" / "tu_dien_ten" / "manifest_values_v3.json"


class UnknownUse(ValueError):
    pass


def table() -> dict:
    return json.loads(TABLE_FILE.read_text(encoding="utf-8"))


def is_engine_manifest(m) -> bool:
    return isinstance(m, dict) and "images" in m and "draft_id" in m


class Migrator:
    def __init__(self, t: dict):
        self.t = t
        self.unknown = collections.Counter()

    def _value(self, field: str, v):
        if not isinstance(v, str):
            return v
        new = self.t[field].get(v)
        if new is not None:
            return new
        known = set(self.t[field].values()) | set(self.t["_unchanged_english"].get(field, []))
        if v not in known:
            self.unknown[(field, v)] += 1
        return v

    def image(self, a: dict) -> dict:
        a = dict(a)
        for key, field in (("source", "image.source"), ("kind", "image.kind"), ("capture_kind", "image.capture_kind")):
            if key in a:
                a[key] = self._value(field, a[key])
        if isinstance(a.get("uses"), list):
            uses = []
            for u in a["uses"]:
                code = self.t["image.uses[]"].get(u)
                if code is None and u not in self.t["image.uses[]"].values():
                    raise UnknownUse(f"uses sentence not in table: {u!r}")
                uses.append(code or u)
            a["uses"] = uses
        if isinstance(a.get("brand_match"), dict):
            bm = dict(a["brand_match"])
            for key, field in (("kind", "brand_match.kind"), ("background_tone", "brand_match.background_tone")):
                if key in bm:
                    bm[key] = self._value(field, bm[key])
            a["brand_match"] = bm
        if isinstance(a.get("ranking"), dict):
            a["ranking"] = self.ranking(a["ranking"])
        return a

    def ranking(self, r: dict) -> dict:
        r = dict(r)
        if "kind" in r:
            r["kind"] = self._value("ranking.kind", r["kind"])
        return r

    def manifest(self, m: dict) -> dict:
        m = dict(m)
        m["images"] = [self.image(a) if isinstance(a, dict) else a for a in m.get("images") or []]
        if isinstance(m.get("ranking"), dict):
            m["ranking"] = self.ranking(m["ranking"])
        if isinstance(m.get("image_order_by_story_type"), list):
            m["image_order_by_story_type"] = [self._value("image_order_by_story_type[]", x)
                                              for x in m["image_order_by_story_type"]]
        if isinstance(m.get("dropped"), list):
            m["dropped"] = [dict(d, source=self._value("image.source", d["source"]))
                            if isinstance(d, dict) and "source" in d else d for d in m["dropped"]]
        m["version"] = 3
        return m

    def golden_line(self, s: dict) -> dict:
        s = dict(s)
        if isinstance(s.get("image"), dict):
            s["image"] = self.image(s["image"])
        return s


def main() -> int:
    ap = argparse.ArgumentParser(description="Manifest values -> English codes, v2 -> v3 (LOW-230)")
    ap.add_argument("--state", default=str(env_load.ROOT / "state"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    state = Path(a.state)
    mig = Migrator(table())

    plans, errors, counts = [], [], collections.Counter()
    for p in sorted(state.glob(f"*/{sp.PREPARE_DIR}/*/{sp.MANIFEST_FILE}")):
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
            if not is_engine_manifest(m):
                counts["manifest skipped (not engine)"] += 1
                continue
            if int(m.get("version") or 0) >= 3:
                counts["manifest already v3"] += 1
                continue
            if int(m.get("version") or 0) != 2:
                errors.append(f"{p}: version {m.get('version')!r}, expected 2")
                continue
            plans.append((p, "json", mig.manifest(m)))
            counts["manifest migrate"] += 1
        except (ValueError, UnknownUse) as e:
            errors.append(f"{p}: {type(e).__name__}: {e}")
    golden = state / "golden" / "v0" / "samples.jsonl"
    if golden.exists():
        try:
            rows = [json.loads(x) for x in golden.read_text(encoding="utf-8").splitlines() if x.strip()]
            new = [mig.golden_line(r) for r in rows]
            if new != rows:
                plans.append((golden, "jsonl", new))
                counts["golden migrate"] += 1
            else:
                counts["golden unchanged"] += 1
        except (ValueError, UnknownUse) as e:
            errors.append(f"{golden}: {type(e).__name__}: {e}")

    for k, n in sorted(counts.items()):
        print(f"{k:32} {n}")
    for (field, v), n in sorted(mig.unknown.items()):
        print(f"[CANH BAO] gia tri ngoai bang, giu nguyen: {field} = {v!r} x{n}")
    for e in errors:
        print(f"[LOI] {e}", file=sys.stderr)
    if errors:
        return 1
    if not plans:
        print("nothing to do (already v3)")
        return 0
    if a.dry_run:
        print("DRY RUN — nothing written")
        return 0

    backup = state.parent / f"low230_values_backup_{time.strftime('%Y%m%d-%H%M%S')}.tar.gz"
    with tarfile.open(backup, "w:gz") as tar:
        for p, _, _ in plans:
            tar.add(p, arcname=str(p.relative_to(state.parent)))
    for p, kind, data in plans:
        if kind == "json":
            env_load.write_json(p, data)
        else:
            tmp = p.with_name(p.name + ".tmp")
            tmp.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in data), encoding="utf-8")
            tmp.replace(p)
    print(f"written; originals in {backup}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
