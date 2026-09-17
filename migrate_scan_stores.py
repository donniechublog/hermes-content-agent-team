#!/usr/bin/env python3
"""News-scan stores + moat stores -> English keys and values (LOW-240). One-shot.

STOP FIRST: the gateways (scan crons of Finn/Nova/Vera/Qinn), hermes-approve and the
moat-publish-watch cron must not run while this runs — a scan writing scan.json or an
approve pick writing `assignments` back into a candidates file mid-run cannot be
detected from here and would be overwritten or left half old. Deploy the code of
LOW-240 and run this in the same stop window.

  state/<brand>/scan/<run>/scan.json            scan_business (Vera) / scan_x (Qinn)
  state/<brand>/scan/finn_<date>/candidates.json scan_sources + scan_prepare supplement
  state/<brand>/<role>_candidates_<date>*.json   manifest_common + approve_pick
  state/<brand>/scan/<run>/trial_manifest.json   same shape (scan_submit --thu)
  state/<brand>/business_seen.json, x_seen.json  seen-stores
  state/<brand>/required_<role>.json             required entries (+ kind/id `ra_mat` -> `release`)
  state/<brand>/moat_republish_queue.json        queue entries
  state/<brand>/moat_chua_bao.json               renamed to moat_unsent_notices.json
  drafts/<id>.json                               `moat_lich_su`, `moat.loi_da_bao` (also inside history)
(each also in the single-brand layout state/…)

Table: docs/tu_dien_ten/scan_keys_v2.json, copied into the maps below
(tests/test_migrate_scan_stores.py checks they stay equal). `toa_soan` means the outlet
in a Vera story and the tweet author in a Qinn story: a scan.json is told apart by its
own keys (window/skipped/x_source = Qinn, watchlist count/feed group/outlets = Vera)
and must agree with its run directory name when that names vera/qinn. Keys outside the
table (summary_vi, score_*, freshness, hand-written extras…) are kept and listed in the
journal. Any other shape (wrong container type, old and new name side by side, a scan
file that is neither or both formats, a required id colliding after rename, a spool
whose new name already exists, a draft mentioning the old keys that does not parse) is
reported and NOTHING is written. Originals go into one tar.gz, every change into a
journal (jsonl) next to it; re-running is a no-op.

    venv/bin/python migrate_scan_stores.py --dry-run
    venv/bin/python migrate_scan_stores.py [--state state] [--drafts drafts]
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

# ---- maps, (old -> new) from the approved table docs/tu_dien_ten/scan_keys_v2.json
SCAN_RESULT_KEY_MAP = {"quet_luc": "scanned_at", "tong_quet": "scanned_total",
                       "tin_watchlist": "watchlist_count", "tin_moi": "new_stories",
                       "cua_so_gio": "window_hours", "bo_qua": "skipped",
                       "tre_gio": "crawl_lag_hours", "canh_bao": "warnings"}
SKIPPED_KEY_MAP = {"ngan": "too_short", "da_thay": "already_seen", "rong": "missing_id_or_url"}
VERA_STORY_KEY_MAP = {"goc": "feed_group", "tieu_de": "title", "toa_soan": "outlet", "ngay": "date",
                      "so_bao": "outlet_count", "cac_bao": "outlets"}
VERA_IN_MEMORY_KEY_MAP = {"hang_watch": "watchlist_company"}
QINN_STORY_KEY_MAP = {"tieu_de": "title", "ngay": "date", "toa_soan": "author", "so_bao": "outlet_count",
                      "nguon_x": "x_source", "loai": "tweet_type", "so_lieu": "metrics",
                      "so_anh": "media_count", "diem": "mechanical_score"}
FINN_CANDIDATE_KEY_MAP = {"nguoi_dang": "posted_by", "bat_buoc": "required"}
FINN_SOURCE_VALUE_MAP = {"bat_buoc": "required"}
ROLE_CANDIDATES_KEY_MAP = {"quet_luc": "scanned_at", "vai": "scan_role"}
ROLE_ITEM_KEY_MAP = {"tu_them": "auto_added", "vai_anh": "image_role", "vai_viet": "writer_role",
                     "task_anh": "image_task", "task_viet": "writer_task", "nguon_loi": "source_error",
                     "da_giao": "assignments", "link_gnews": "gnews_url"}
ASSIGNMENT_KEY_MAP = {"vai_anh": "image_role", "task_anh": "image_task"}
BUSINESS_SEEN_KEY_MAP = {"cap_nhat": "updated_at", "khoa": "seen_at", "ghi_chu": "note"}
X_SEEN_KEY_MAP = {"khoa": "seen_at", "ghi_luc": "updated_at"}
REQUIRED_ENTRY_KEY_MAP = {"ten": "name", "loai": "kind", "ghi_chu": "note", "ngay": "added_date",
                          "tu_khoa": "keywords"}
REQUIRED_KIND_VALUE_MAP = {"ra_mat": "release"}
MOAT_QUEUE_ENTRY_KEY_MAP = {"lan": "attempts", "loi": "error", "luc": "last_attempt_at"}
DRAFT_MOAT_KEY_MAP = {"moat_lich_su": "moat_history", "moat.loi_da_bao": "moat.reported_error"}
FILE_RENAMES = {"moat_chua_bao.json": "moat_unsent_notices.json"}
ENV_RENAMES = {"MOAT_NEN_ANH": "MOAT_COMPRESS_IMAGES", "MOAT_NGUONG_NEN": "MOAT_COMPRESS_MIN_BYTES",
               "MOAT_CHAT_LUONG_NEN": "MOAT_COMPRESS_QUALITY", "MOAT_TRAN_TONG": "MOAT_MAX_TOTAL_BYTES"}

# English keys the writers already use (not in the table) — anything else is reported as kept.
FIXED_KEYS = {
    "scan_result": {"freshness"},
    "skipped": {"reply"},
    "vera_story": {"link", "ts", "watchlist", "seen_keys"},
    "qinn_story": {"id", "link", "text"},
    "finn_top": {"scanned_at", "note", "candidates"},
    "finn_candidate": {"source", "title", "link", "discussion", "points", "comments", "via", "age_hours",
                       "score_recency", "score_spread", "score_partial", "source_median_points",
                       "image_url", "spread_note", "summary", "description"},
    "role_top": {"items"},
    "role_item": {"index", "title", "link", "via", "source_note", "summary_vi", "score", "score_reason",
                  "category", "image_url", "picked", "score_technical", "score_relevance",
                  "score_recency", "score_spread", "brand"},
    "assignment": {"brand", "draft_id"},
    "business_seen": set(),
    "x_seen": set(),
    "required_entry": {"link"},
    "moat_queue_entry": {"brand", "scheduled_at"},
}

OLD_SPOOL, NEW_SPOOL = next(iter(FILE_RENAMES.items()))
DRAFT_HISTORY_OLD, DRAFT_HISTORY_NEW = "moat_lich_su", DRAFT_MOAT_KEY_MAP["moat_lich_su"]
DRAFT_ERROR_OLD = next(k for k in DRAFT_MOAT_KEY_MAP if k.startswith("moat."))[len("moat."):]
DRAFT_ERROR_NEW = DRAFT_MOAT_KEY_MAP["moat." + DRAFT_ERROR_OLD][len("moat."):]


class BadShape(ValueError):
    pass


class Report:
    """Unknown keys kept and enumerated values rewritten, collected per file."""

    def __init__(self):
        self.unknown, self.values = set(), {}

    def value(self, what: str, old: str) -> None:
        k = f"{what}:{old}"
        self.values[k] = self.values.get(k, 0) + 1


def _rename(d, key_map: dict, fixed: set, where: str, rep: Report) -> dict:
    if not isinstance(d, dict):
        raise BadShape(f"{where} is {type(d).__name__}, expected object")
    known = set(key_map) | set(key_map.values()) | fixed
    out = {}
    for k, v in d.items():
        new = key_map.get(k, k)
        if new != k and new in d:
            raise BadShape(f"{where}: both {k!r} and {new!r}")
        if k not in known:
            rep.unknown.add(f"{where}.{k}" if where else k)
        out[new] = v
    return out


def _list(v, where: str) -> list:
    if not isinstance(v, list):
        raise BadShape(f"{where} is {type(v).__name__}, expected list")
    return v


# ---------------------------------------------------------------- per store
def migrate_scan_result(d, run_role: str, rep: Report) -> dict:
    if not isinstance(d, dict):
        raise BadShape(f"not an object: {type(d).__name__}")
    stories = d.get("tin_moi", d.get("new_stories", []))
    _list(stories, "new_stories")
    for i, s in enumerate(stories):
        if not isinstance(s, dict):
            raise BadShape(f"new_stories[{i}] is {type(s).__name__}, expected object")
    top = set(d)
    item_keys = {k for s in stories for k in s}
    qinn = bool(top & {"cua_so_gio", "window_hours", "bo_qua", "skipped", "tre_gio", "crawl_lag_hours"}
                or item_keys & {"nguon_x", "x_source", "author"})
    vera = bool(top & {"tin_watchlist", "watchlist_count"}
                or item_keys & {"goc", "feed_group", "cac_bao", "outlets", "outlet"})
    if qinn and vera:
        raise BadShape("both Qinn (X) and Vera (business) scan keys — cannot tell outlet from author")
    if not qinn and not vera and "toa_soan" in item_keys:
        raise BadShape("neither Qinn nor Vera scan keys — cannot tell whether toa_soan is outlet or author")
    fmt = "qinn" if qinn else "vera" if vera else ""
    if fmt and run_role in ("qinn", "vera") and fmt != run_role:
        raise BadShape(f"content looks like {fmt} but the run directory is {run_role}")
    out = _rename(d, SCAN_RESULT_KEY_MAP, FIXED_KEYS["scan_result"], "", rep)
    if "skipped" in out:
        out["skipped"] = _rename(out["skipped"], SKIPPED_KEY_MAP, FIXED_KEYS["skipped"], "skipped", rep)
    if "new_stories" in out:
        if fmt == "qinn":
            story_map, fixed = QINN_STORY_KEY_MAP, FIXED_KEYS["qinn_story"]
        else:
            story_map, fixed = {**VERA_STORY_KEY_MAP, **VERA_IN_MEMORY_KEY_MAP}, FIXED_KEYS["vera_story"]
        out["new_stories"] = [_rename(s, story_map, fixed, "new_stories[]", rep) for s in out["new_stories"]]
    return out


def migrate_finn_candidates(d, rep: Report) -> dict:
    out = _rename(d, {}, FIXED_KEYS["finn_top"], "", rep)
    if "candidates" in out:
        new = []
        for c in _list(out["candidates"], "candidates"):
            c2 = _rename(c, FINN_CANDIDATE_KEY_MAP, FIXED_KEYS["finn_candidate"], "candidates[]", rep)
            src = c2.get("source")
            if isinstance(src, str) and src in FINN_SOURCE_VALUE_MAP:
                c2["source"] = FINN_SOURCE_VALUE_MAP[src]
                rep.value("source", src)
            new.append(c2)
        out["candidates"] = new
    return out


def _migrate_role_item(it, rep: Report) -> dict:
    it2 = _rename(it, ROLE_ITEM_KEY_MAP, FIXED_KEYS["role_item"], "items[]", rep)
    if "assignments" in it2:
        it2["assignments"] = [_rename(g, ASSIGNMENT_KEY_MAP, FIXED_KEYS["assignment"], "items[].assignments[]", rep)
                              for g in _list(it2["assignments"], "items[].assignments")]
    return it2


def migrate_role_candidates(d, rep: Report):
    if isinstance(d, list):                       # legacy: bare item list
        return [_migrate_role_item(it, rep) for it in d]
    out = _rename(d, ROLE_CANDIDATES_KEY_MAP, FIXED_KEYS["role_top"], "", rep)
    if "items" in out:
        out["items"] = [_migrate_role_item(it, rep) for it in _list(out["items"], "items")]
    return out


def migrate_seen(d, key_map: dict, fixed: set, rep: Report) -> dict:
    out = _rename(d, key_map, fixed, "", rep)
    if "seen_at" in out and not isinstance(out["seen_at"], (dict, list)):
        raise BadShape(f"seen_at is {type(out['seen_at']).__name__}, expected object or list")
    return out


def migrate_required(d, rep: Report) -> dict:
    if not isinstance(d, dict):
        raise BadShape(f"not an object: {type(d).__name__}")
    out = {}
    for rid, entry in d.items():
        e2 = _rename(entry, REQUIRED_ENTRY_KEY_MAP, FIXED_KEYS["required_entry"], f"[{rid}]", rep)
        kind = e2.get("kind")
        if isinstance(kind, str) and kind in REQUIRED_KIND_VALUE_MAP:
            e2["kind"] = REQUIRED_KIND_VALUE_MAP[kind]
            rep.value("kind", kind)
        new_id = rid
        prefix, sep, rest = rid.partition("|")
        if sep and prefix in REQUIRED_KIND_VALUE_MAP:
            new_id = f"{REQUIRED_KIND_VALUE_MAP[prefix]}|{rest}"
            rep.value("id_prefix", prefix)
        if new_id in out or (new_id != rid and new_id in d):
            raise BadShape(f"required id {rid!r} -> {new_id!r} collides with an existing entry")
        out[new_id] = e2
    return out


def migrate_moat_queue(d, rep: Report) -> dict:
    if not isinstance(d, dict):
        raise BadShape(f"not an object: {type(d).__name__}")
    return {draft_id: _rename(e, MOAT_QUEUE_ENTRY_KEY_MAP, FIXED_KEYS["moat_queue_entry"], f"[{draft_id}]", rep)
            for draft_id, e in d.items()}


def _moat_error(m, where: str) -> dict:
    if not isinstance(m, dict):
        return m
    if DRAFT_ERROR_OLD in m and DRAFT_ERROR_NEW in m:
        raise BadShape(f"{where}: both {DRAFT_ERROR_OLD!r} and {DRAFT_ERROR_NEW!r}")
    return {(DRAFT_ERROR_NEW if k == DRAFT_ERROR_OLD else k): v for k, v in m.items()}


def migrate_draft(d) -> dict:
    """Only the moat keys; everything else in a draft is left exactly as it is."""
    if not isinstance(d, dict):
        raise BadShape(f"not an object: {type(d).__name__}")
    if DRAFT_HISTORY_OLD in d and DRAFT_HISTORY_NEW in d:
        raise BadShape(f"both {DRAFT_HISTORY_OLD!r} and {DRAFT_HISTORY_NEW!r}")
    out = {}
    for k, v in d.items():
        if k in (DRAFT_HISTORY_OLD, DRAFT_HISTORY_NEW):
            out[DRAFT_HISTORY_NEW] = [_moat_error(m, f"{DRAFT_HISTORY_NEW}[{i}]")
                                      for i, m in enumerate(_list(v, DRAFT_HISTORY_NEW))]
        elif k == "moat":
            out[k] = _moat_error(v, "moat")
        else:
            out[k] = v
    return out


# ---------------------------------------------------------------- discovery
def _both_layouts(state: Path, pattern: str) -> list:
    return sorted(set(state.glob(f"*/{pattern}")) | set(state.glob(pattern)))


def find_files(state: Path) -> list:
    """[(kind, path)] in a stable order."""
    out = []
    for p in _both_layouts(state, f"{sp.SCAN_DIR}/*/{sp.SCAN_RESULT_FILE}"):
        out.append(("scan_result", p))
    for p in _both_layouts(state, f"{sp.SCAN_DIR}/*/candidates.json"):
        out.append(("finn_candidates", p))
    for p in _both_layouts(state, f"{sp.SCAN_DIR}/*/{sp.SCAN_TRIAL_MANIFEST_FILE}"):
        out.append(("role_candidates", p))
    for p in _both_layouts(state, "*_candidates_*.json"):
        out.append(("role_candidates", p))
    for p in _both_layouts(state, sp.BUSINESS_SEEN_FILE):
        out.append(("business_seen", p))
    for p in _both_layouts(state, sp.X_SEEN_FILE):
        out.append(("x_seen", p))
    for p in _both_layouts(state, sp.REQUIRED_FILE.format("*")):
        out.append(("required", p))
    for p in _both_layouts(state, sp.MOAT_REPUBLISH_QUEUE_FILE):
        out.append(("moat_queue", p))
    return out


def run_role_of(p: Path) -> str:
    return p.parent.name.split("_")[0]


def migrate_file(kind: str, p: Path, d, rep: Report):
    if kind == "scan_result":
        return migrate_scan_result(d, run_role_of(p), rep)
    if kind == "finn_candidates":
        return migrate_finn_candidates(d, rep)
    if kind == "role_candidates":
        return migrate_role_candidates(d, rep)
    if kind == "business_seen":
        return migrate_seen(d, BUSINESS_SEEN_KEY_MAP, FIXED_KEYS["business_seen"], rep)
    if kind == "x_seen":
        return migrate_seen(d, X_SEEN_KEY_MAP, FIXED_KEYS["x_seen"], rep)
    if kind == "required":
        return migrate_required(d, rep)
    if kind == "moat_queue":
        return migrate_moat_queue(d, rep)
    raise AssertionError(kind)


def _arcname(p: Path, bases: list) -> str:
    for b in bases:
        try:
            return str(p.relative_to(b))
        except ValueError:
            continue
    return p.name


def main() -> int:
    ap = argparse.ArgumentParser(description="scan/moat stores -> English keys (LOW-240)")
    ap.add_argument("--state", default=str(env_load.ROOT / "state"))
    ap.add_argument("--drafts", default=str(env_load.ROOT / "drafts"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    state, drafts = Path(a.state), Path(a.drafts)
    bases = [state.parent, drafts.parent]

    plans, renames, errors = [], [], []

    def _show(rel, status, rep):
        extra = []
        if rep.values:
            extra.append("values: " + ", ".join(f"{k} x{n}" for k, n in sorted(rep.values.items())))
        if rep.unknown:
            extra.append("kept unknown keys: " + ", ".join(sorted(rep.unknown)))
        print(f"{status:9} {rel}" + (f"  ({'; '.join(extra)})" if extra else ""))

    for kind, p in find_files(state):
        rel = _arcname(p, bases)
        rep = Report()
        try:
            old = json.loads(p.read_text(encoding="utf-8"))
            new = migrate_file(kind, p, old, rep)
        except (ValueError, OSError) as e:
            errors.append(f"{rel}: {type(e).__name__}: {e}")
            continue
        _show(rel, "migrate" if new != old else "unchanged", rep)
        if new != old:
            plans.append((p, kind, old, new, rep))

    for p in _both_layouts(state, OLD_SPOOL):
        target = p.with_name(NEW_SPOOL)
        rel = _arcname(p, bases)
        if target.exists():
            errors.append(f"{rel}: {NEW_SPOOL} already exists next to it")
            continue
        print(f"{'rename':9} {rel} -> {NEW_SPOOL}")
        renames.append((p, target))

    if drafts.is_dir():
        for p in sorted(drafts.glob("*.json")):
            rel = _arcname(p, bases)
            try:
                text = p.read_text(encoding="utf-8")
            except OSError as e:
                errors.append(f"{rel}: {type(e).__name__}: {e}")
                continue
            if DRAFT_HISTORY_OLD not in text and DRAFT_ERROR_OLD not in text:
                continue
            try:
                old = json.loads(text)
                new = migrate_draft(old)
            except ValueError as e:
                errors.append(f"{rel}: {type(e).__name__}: {e}")
                continue
            if new != old:
                _show(rel, "migrate", Report())
                plans.append((p, "draft", old, new, Report()))

    for e in errors:
        print(f"[LOI] {e}", file=sys.stderr)
    set_env = [k for k in ENV_RENAMES if k in os.environ]
    if set_env:
        print("[CANH BAO] old env names still set (rename them where they are defined): "
              + ", ".join(f"{k} -> {ENV_RENAMES[k]}" for k in set_env), file=sys.stderr)
    if errors:
        print(f"{len(errors)} file(s) refused — nothing written", file=sys.stderr)
        return 1
    if not plans and not renames:
        print("nothing to do (already migrated)")
        return 0
    if a.dry_run:
        print(f"DRY RUN — {len(plans)} file(s) would be migrated, {len(renames)} renamed, nothing written")
        return 0
    stamp = time.strftime("%Y%m%d-%H%M%S")
    backup = state.parent / f"low240_scan_stores_backup_{stamp}.tar.gz"
    with tarfile.open(backup, "w:gz") as tar:
        for p, *_ in plans:
            tar.add(p, arcname=_arcname(p, bases))
        for p, _ in renames:
            tar.add(p, arcname=_arcname(p, bases))
    journal = state.parent / f"low240_scan_stores_{stamp}.journal.jsonl"
    with journal.open("w", encoding="utf-8") as fh:
        for p, kind, old, new, rep in plans:
            env_load.write_json(p, new)
            row = {"file": str(p), "kind": kind,
                   "from_keys": sorted(old) if isinstance(old, dict) else None,
                   "to_keys": sorted(new) if isinstance(new, dict) else None,
                   "values": rep.values, "kept_unknown_keys": sorted(rep.unknown)}
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        for p, target in renames:
            os.replace(p, target)
            fh.write(json.dumps({"file": str(p), "kind": "rename", "renamed_to": str(target)},
                                ensure_ascii=False) + "\n")
    print(f"written {len(plans)} file(s), renamed {len(renames)}; originals in {backup}; journal {journal}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
