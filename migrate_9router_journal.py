#!/usr/bin/env python3
"""state/9router/journal/9router_<date>.json -> English keys (LOW-239). One-shot; run while
the `daily-log` cron (monitor_9router) and Ada are not writing/reading the journal.

Table: docs/tu_dien_ten/journal_keys_v2.json, section `router_journal*`, copied into the maps
below (tests/test_migrate_9router_journal.py checks they stay equal). Only fixed keys are
renamed; dynamic-key maps keep their data keys (model @ connection, API key label, hour,
"a → b", "model: status", brand/role, brand) and only their inner fixed keys change:

  top level                     ngay/tong/theo_model/... -> date/totals/by_model/...
  totals, by_model.*, by_api_key.*, by_hour.*   loi -> error_count
  top_prompt[]                  luc -> time
  low_cache_models[]            vai -> config_roles (values such as "engine anh:vision" kept)
  connection_errors[]           ten/trang_thai/ma/loi/luc/trong_ngay/bat -> name/.../active
  legacy_connection             co_watcher -> has_watcher (`ip` must be empty, see below)
  role_costs                    theo_vai/theo_brand/phu_pct/ghi_chu/loi_doc -> by_role/...
  role_costs.by_role.*          phien -> sessions
  role_costs.by_brand.*         bai/usd_bai -> published_count/usd_per_published

The `.md` next to each file is NOT touched (the new write_md renders the same bytes).

Refuses the WHOLE run (nothing written) when any file has a shape the table does not cover:
not a JSON object, a key at a mapped level that is neither old, new nor a known English key,
old and new name side by side, a wrong type at a mapped level, or a non-empty
legacy_connection.ip (watcher data from before 05/09/2026 — its inner keys ket_noi/dau/cuoi/
ngoai are not in the table). Originals go into one tar.gz, every written file into a journal
(jsonl) next to it; re-running is a no-op.

    venv/bin/python migrate_9router_journal.py --dry-run
    venv/bin/python migrate_9router_journal.py
"""
import argparse
import json
import sys
import tarfile
import time
from pathlib import Path

import env_load
import state_paths as sp

# (old, new) from the approved table docs/tu_dien_ten/journal_keys_v2.json.
TOP_KEY_MAP = {"ngay": "date", "cua_so_utc": "utc_window", "tong": "totals", "theo_model": "by_model",
               "theo_khoa": "by_api_key", "theo_gio": "by_hour", "model_la": "unknown_models",
               "cache_kem": "low_cache_models", "lat_model": "model_switches",
               "lat_vi_du": "model_switch_examples", "rong": "empty_responses",
               "rong_vi_du": "empty_response_examples", "loi": "errors_by_model_status",
               "loi_doc": "read_error", "loi_ket_noi": "connection_errors", "vai": "role_costs",
               "ket_noi": "legacy_connection"}
BUCKET_KEY_MAP = {"loi": "error_count"}
TOP_PROMPT_KEY_MAP = {"luc": "time"}
LOW_CACHE_KEY_MAP = {"vai": "config_roles"}
CONNECTION_ERROR_KEY_MAP = {"ten": "name", "trang_thai": "test_status", "ma": "error_code",
                            "loi": "last_error", "luc": "last_error_at", "trong_ngay": "error_in_window",
                            "bat": "active"}
LEGACY_CONNECTION_KEY_MAP = {"co_watcher": "has_watcher"}
ROLE_COSTS_KEY_MAP = {"theo_vai": "by_role", "theo_brand": "by_brand", "phu_pct": "coverage_pct",
                      "ghi_chu": "note", "loi_doc": "unreadable_profiles"}
BY_ROLE_KEY_MAP = {"phien": "sessions"}
BY_BRAND_KEY_MAP = {"bai": "published_count", "usd_bai": "usd_per_published"}

# Keys already English at each mapped level (not in the table, written by monitor_9router).
TOP_FIXED = ("fallback", "top_prompt")
BUCKET_FIXED = ("req", "prompt", "cache", "out", "usd", "cache_pct")
TOP_PROMPT_FIXED = ("prompt", "model", "cache", "usd")
UNKNOWN_MODEL_FIXED = ("model", "req", "prompt", "usd", "cache_pct")
LOW_CACHE_FIXED = ("model", "prompt", "cache_pct")
CONNECTION_ERROR_FIXED = ("backoff",)
LEGACY_CONNECTION_FIXED = ("ip",)
BY_ROLE_FIXED = ("brand", "api", "in", "out", "cache", "reasoning", "usd", "model", "task_done", "usd_task")
BY_BRAND_FIXED = ("usd",)


class BadShape(ValueError):
    pass


def tables() -> dict:
    return {"router_journal": dict(TOP_KEY_MAP), "router_journal.usage_bucket": dict(BUCKET_KEY_MAP),
            "router_journal.top_prompt[]": dict(TOP_PROMPT_KEY_MAP),
            "router_journal.low_cache_models[]": dict(LOW_CACHE_KEY_MAP),
            "router_journal.connection_errors[]": dict(CONNECTION_ERROR_KEY_MAP),
            "router_journal.legacy_connection": dict(LEGACY_CONNECTION_KEY_MAP),
            "router_journal.role_costs": dict(ROLE_COSTS_KEY_MAP),
            "router_journal.role_costs.by_role.*": dict(BY_ROLE_KEY_MAP),
            "router_journal.role_costs.by_brand.*": dict(BY_BRAND_KEY_MAP)}


def find_files(state: Path) -> list:
    return sorted((Path(state) / "9router" / sp.JOURNAL_DIR).glob("9router_*.json"))


def _expect(v, kind, where: str):
    if not isinstance(v, kind):
        want = kind.__name__ if isinstance(kind, type) else "/".join(k.__name__ for k in kind)
        raise BadShape(f"{where} is {type(v).__name__}, expected {want}")
    return v


def _rename(d, key_map: dict, fixed: tuple, where: str) -> dict:
    """Rename one fixed-key level; any key outside old/new/fixed refuses."""
    _expect(d, dict, where)
    known = set(key_map) | set(key_map.values()) | set(fixed)
    out = {}
    for k, v in d.items():
        if k not in known:
            raise BadShape(f"{where}: unknown key {k!r}")
        new = key_map.get(k, k)
        if new != k and new in d:
            raise BadShape(f"{where}: both {k!r} and {new!r}")
        out[new] = v
    return out


def _each_value(d, where: str, fn) -> dict:
    """Dynamic-key map: keep data keys, migrate every value."""
    _expect(d, dict, where)
    return {k: fn(v, f"{where}[{k!r}]") for k, v in d.items()}


def _each_item(items, where: str, fn) -> list:
    _expect(items, list, where)
    return [fn(x, f"{where}[{i}]") for i, x in enumerate(items)]


def _bucket(v, where):
    return _rename(v, BUCKET_KEY_MAP, BUCKET_FIXED, where)


def migrate(d) -> dict:
    """Old, mixed or new shape -> new shape. Raises BadShape for anything the table does not cover."""
    if not isinstance(d, dict):
        raise BadShape(f"not an object: {type(d).__name__}")
    out = _rename(d, TOP_KEY_MAP, TOP_FIXED, "top level")
    for k, kind in (("date", str), ("read_error", str), ("utc_window", list), ("model_switch_examples", list),
                    ("empty_response_examples", list), ("model_switches", dict),
                    ("errors_by_model_status", dict), ("empty_responses", dict)):
        if k in out:
            _expect(out[k], kind, k)
    if "fallback" in out:
        _expect(out["fallback"], int, "fallback")
    if "totals" in out:
        out["totals"] = _bucket(out["totals"], "totals")
    for k in ("by_model", "by_api_key", "by_hour"):
        if k in out:
            out[k] = _each_value(out[k], k, _bucket)
    if "top_prompt" in out:
        out["top_prompt"] = _each_item(out["top_prompt"], "top_prompt",
                                       lambda x, w: _rename(x, TOP_PROMPT_KEY_MAP, TOP_PROMPT_FIXED, w))
    if "unknown_models" in out:
        out["unknown_models"] = _each_item(out["unknown_models"], "unknown_models",
                                           lambda x, w: _rename(x, {}, UNKNOWN_MODEL_FIXED, w))
    if "low_cache_models" in out:
        out["low_cache_models"] = _each_item(out["low_cache_models"], "low_cache_models",
                                             lambda x, w: _rename(x, LOW_CACHE_KEY_MAP, LOW_CACHE_FIXED, w))
    if "connection_errors" in out:
        out["connection_errors"] = _each_item(
            out["connection_errors"], "connection_errors",
            lambda x, w: _rename(x, CONNECTION_ERROR_KEY_MAP, CONNECTION_ERROR_FIXED, w))
    if "legacy_connection" in out:
        lc = _rename(out["legacy_connection"], LEGACY_CONNECTION_KEY_MAP, LEGACY_CONNECTION_FIXED,
                     "legacy_connection")
        if lc.get("ip"):
            raise BadShape("legacy_connection.ip is not empty: per-IP keys (ket_noi/dau/cuoi/ngoai) "
                           "are not in journal_keys_v2.json")
        out["legacy_connection"] = lc
    if "role_costs" in out:
        rc = _rename(out["role_costs"], ROLE_COSTS_KEY_MAP, (), "role_costs")
        if "by_role" in rc:
            rc["by_role"] = _each_value(rc["by_role"], "role_costs.by_role",
                                        lambda x, w: _rename(x, BY_ROLE_KEY_MAP, BY_ROLE_FIXED, w))
            for k, a in rc["by_role"].items():
                if "model" in a:
                    _expect(a["model"], dict, f"role_costs.by_role[{k!r}].model")
        if "by_brand" in rc:
            rc["by_brand"] = _each_value(rc["by_brand"], "role_costs.by_brand",
                                         lambda x, w: _rename(x, BY_BRAND_KEY_MAP, BY_BRAND_FIXED, w))
        if "unreadable_profiles" in rc:
            _expect(rc["unreadable_profiles"], list, "role_costs.unreadable_profiles")
        if "note" in rc:
            _expect(rc["note"], str, "role_costs.note")
        out["role_costs"] = rc
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="9router_<date>.json -> English keys (LOW-239)")
    ap.add_argument("--state", default=str(env_load.ROOT / "state"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    state = Path(a.state)

    plans, errors = [], []
    for p in find_files(state):
        rel = p.relative_to(state.parent)
        try:
            old = json.loads(p.read_text(encoding="utf-8"))
            new = migrate(old)
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
    backup = state.parent / f"low239_9router_journal_backup_{stamp}.tar.gz"
    with tarfile.open(backup, "w:gz") as tar:
        for p, *_ in plans:
            tar.add(p, arcname=str(p.relative_to(state.parent)))
    journal = state.parent / f"low239_9router_journal_{stamp}.journal.jsonl"
    with journal.open("w", encoding="utf-8") as fh:
        for p, old, new in plans:
            # indent=1 + ensure_ascii=False: same layout monitor_9router.use() writes
            env_load.write_json(p, new, indent=1)
            fh.write(json.dumps({"file": str(p), "from_keys": sorted(old), "to_keys": sorted(new)},
                                ensure_ascii=False) + "\n")
    print(f"written {len(plans)} file(s); originals in {backup}; journal {journal}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
