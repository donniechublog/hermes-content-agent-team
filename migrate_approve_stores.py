#!/usr/bin/env python3
"""Telegram approve-bot stores -> English keys (LOW-241). One-shot.

STOP FIRST: hermes-approve@blog/@dcgr (they write drafts, sidecars, redo_waiting.json and
article_request_counts.json) and every role that calls send_telegram.py (it appends to
telegram_sent/<role>.jsonl) must not run while this runs — a write landing mid-run cannot
be detected from here and would be overwritten or left half old. Deploy the code of
LOW-241 and run this in the same stop window; rename the env vars in the systemd
drop-ins (override.conf) in that window too, the code reads only the new names.

  drafts/<id>.json                            channel_anh_mid, channel_chu_mid, ghi_chu_cuu
  drafts/<id>.writer.json                     vai_viet, dre_task_truoc_kite
  state/<brand>/redo_waiting.json             entry hoi_mid
  state/<brand>/article_request_counts.json   entry ngay, vai
  state/<brand>/telegram_sent/<role>.jsonl    line mo_ta (rewritten line by line, order kept)
  state/<brand>/ong_chu.json                  renamed to boss_ids.json
(each also in the single-brand layout state/…)

Not migrated: kanban blackboard entries (append-only history in kanban.db, new entries use
the new keys), the sync_hermes snapshot marker (rewritten on the next capture), env vars
(systemd drop-ins, warned about when still set here).

Table: docs/tu_dien_ten/approve_keys_v2.json, copied into the maps below
(tests/test_migrate_approve_stores.py checks they stay equal). Only the table's keys are
renamed; other keys stay where they are (unknown keys of the sidecar/entries are listed in
the journal). A draft or telegram_sent line that does not mention an old key is left
byte-identical; other files of drafts/ (.meta.json, .img.json, *.bak…) are not read. Any
other shape (wrong container or value type, old and new name side by side, a file or line
mentioning an old key that does not parse, a boss_ids.json already next to ong_chu.json)
is reported and NOTHING is written. Originals go into one tar.gz, every change into a
journal (jsonl) next to it; re-running is a no-op.

    venv/bin/python migrate_approve_stores.py --dry-run
    venv/bin/python migrate_approve_stores.py [--state state] [--drafts drafts]
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

# ---- maps, (old -> new) from the approved table docs/tu_dien_ten/approve_keys_v2.json
DRAFT_KEY_MAP = {"channel_anh_mid": "channel_photo_mid", "channel_chu_mid": "channel_text_mid",
                 "ghi_chu_cuu": "rescue_note"}
WRITER_SIDECAR_KEY_MAP = {"vai_viet": "writer_role", "dre_task_truoc_kite": "dre_task_before_kite"}
REDO_WAITING_ENTRY_KEY_MAP = {"hoi_mid": "question_mid"}
BLACKBOARD_ENTRY_KEY_MAP = {"lam_lai": "redo", "chuyen_kite": "kite_transfer"}
BLACKBOARD_REDO_KEY_MAP = {"lan": "attempt", "ly_do": "reason", "task_truoc": "previous_task"}
BLACKBOARD_KITE_TRANSFER_KEY_MAP = {"tu_vai": "transferred_from", "ly_do": "transfer_reason",
                                    "anh_that_dung_duoc": "usable_image_ids"}
ARTICLE_REQUEST_COUNT_ENTRY_KEY_MAP = {"ngay": "requested_at", "vai": "image_role"}
TELEGRAM_SENT_LINE_KEY_MAP = {"mo_ta": "description"}
FILE_RENAMES = {"ong_chu.json": "boss_ids.json"}
SNAPSHOT_MARKER_RENAMES = {"LOI_DOC": "READ_ERROR"}
ENV_RENAMES = {"CT_BANG_DEN": "CT_BLACKBOARD_BRANDS", "CT_CHAT_QUA_GATEWAY": "CT_CHAT_VIA_GATEWAY",
               "CT_CHAT_SONG_SONG": "CT_CHAT_PARALLEL"}

# Allowed value types of the renamed keys (new name -> types).
_MID = (int, bool)
VALUE_TYPES = {
    "channel_photo_mid": _MID, "channel_text_mid": _MID, "rescue_note": (str,),
    "writer_role": (str,), "dre_task_before_kite": (str, type(None)),
    "question_mid": (int,),
    "requested_at": (str,), "image_role": (str,),
    "description": (str,),
}

# English keys the writers already use (not in the table) — anything else is reported as kept.
FIXED_KEYS = {
    "writer_sidecar": {"title", "body", "created", "root_task", "dre_task", "writer_task"},
    "redo_waiting_entry": {"draft_id", "thread_id", "ts", "title"},
    "article_request_count_entry": {"draft_id", "brand", "tasks", "title"},
    "telegram_sent_line": {"ts", "message_id", "message_ids", "files", "md5", "button_draft",
                           "button_message_id"},
}

OLD_BOSS_IDS, NEW_BOSS_IDS = next(iter(FILE_RENAMES.items()))
TELEGRAM_SENT_DIR = "telegram_sent"


class BadShape(ValueError):
    pass


def _rename(d, key_map: dict, fixed, where: str, unknown: set) -> dict:
    """Rename the table's keys in place of order; `fixed` None = do not report unknown keys."""
    if not isinstance(d, dict):
        raise BadShape(f"{where or 'top'} is {type(d).__name__}, expected object")
    known = set(key_map) | set(key_map.values()) | (fixed or set())
    out = {}
    for k, v in d.items():
        new = key_map.get(k, k)
        if new != k and new in d:
            raise BadShape(f"{where}: both {k!r} and {new!r}")
        if new in key_map.values() and not isinstance(v, VALUE_TYPES[new]):
            raise BadShape(f"{where}.{k} is {type(v).__name__}, expected "
                           + " or ".join(t.__name__ for t in VALUE_TYPES[new]))
        if fixed is not None and k not in known:
            unknown.add(f"{where}.{k}" if where else k)
        out[new] = v
    return out


# ---------------------------------------------------------------- per store
def migrate_draft(d, unknown: set) -> dict:
    return _rename(d, DRAFT_KEY_MAP, None, "", unknown)


def migrate_writer_sidecar(d, unknown: set) -> dict:
    return _rename(d, WRITER_SIDECAR_KEY_MAP, FIXED_KEYS["writer_sidecar"], "", unknown)


def _migrate_entries(d, key_map: dict, fixed: set, unknown: set) -> dict:
    if not isinstance(d, dict):
        raise BadShape(f"top is {type(d).__name__}, expected object")
    return {k: _rename(e, key_map, fixed, f"[{k}]", unknown) for k, e in d.items()}


def migrate_redo_waiting(d, unknown: set) -> dict:
    return _migrate_entries(d, REDO_WAITING_ENTRY_KEY_MAP, FIXED_KEYS["redo_waiting_entry"], unknown)


def migrate_article_request_counts(d, unknown: set) -> dict:
    return _migrate_entries(d, ARTICLE_REQUEST_COUNT_ENTRY_KEY_MAP,
                            FIXED_KEYS["article_request_count_entry"], unknown)


def migrate_telegram_sent(text: str, unknown: set) -> tuple:
    """(new text, lines changed). Lines without an old key stay byte-identical.

    Split on "\\n" only, the way send_telegram writes: str.splitlines would also cut at
    U+2028 and friends, which json.dumps(ensure_ascii=False) leaves inside a string."""
    olds = tuple(f'"{k}"' for k in TELEGRAM_SENT_LINE_KEY_MAP)
    out, changed = [], 0
    for i, line in enumerate(text.split("\n")):
        if not any(o in line for o in olds):
            out.append(line)
            continue
        try:
            d = json.loads(line)
        except ValueError as e:
            raise BadShape(f"line {i + 1} mentions an old key but does not parse: {e}") from e
        new = _rename(d, TELEGRAM_SENT_LINE_KEY_MAP, FIXED_KEYS["telegram_sent_line"], f"line {i + 1}", unknown)
        if list(new) == list(d):
            out.append(line)
            continue
        out.append(json.dumps(new, ensure_ascii=False))
        changed += 1
    return "\n".join(out), changed


# ---------------------------------------------------------------- discovery
def _both_layouts(state: Path, pattern: str) -> list:
    return sorted(set(state.glob(f"*/{pattern}")) | set(state.glob(pattern)))


def draft_files(drafts: Path) -> list:
    """drafts/<id>.json only: a draft id has no dot (approve_post._DRAFT_ID_HOP_LE)."""
    return [p for p in sorted(drafts.glob("*.json")) if "." not in p.name[:-len(".json")]]


def writer_sidecar_files(drafts: Path) -> list:
    return [p for p in sorted(drafts.glob("*.writer.json")) if "." not in p.name[:-len(".writer.json")]]


def _indent(text: str):
    """Keep the writer's layout: approve_post writes redo_waiting.json on one line."""
    return 2 if "\n" in text.strip() else None


def _arcname(p: Path, bases: list) -> str:
    for b in bases:
        try:
            return str(p.relative_to(b))
        except ValueError:
            continue
    return p.name


def main() -> int:
    ap = argparse.ArgumentParser(description="approve-bot stores -> English keys (LOW-241)")
    ap.add_argument("--state", default=str(env_load.ROOT / "state"))
    ap.add_argument("--drafts", default=str(env_load.ROOT / "drafts"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    state, drafts = Path(a.state), Path(a.drafts)
    bases = [state.parent, drafts.parent]

    plans, renames, errors = [], [], []      # plans: (path, kind, new JSON, new jsonl text, journal row)

    def _show(rel, status, unknown, extra=""):
        notes = [extra] if extra else []
        if unknown:
            notes.append("kept unknown keys: " + ", ".join(sorted(unknown)))
        print(f"{status:9} {rel}" + (f"  ({'; '.join(notes)})" if notes else ""))

    def _json_store(kind, p, fn, prefilter=None):
        rel = _arcname(p, bases)
        try:
            text = p.read_text(encoding="utf-8")
        except OSError as e:
            errors.append(f"{rel}: {type(e).__name__}: {e}")
            return
        if prefilter and not any(f'"{k}"' in text for k in prefilter):
            return
        unknown = set()
        try:
            old = json.loads(text)
            new = fn(old, unknown)
        except ValueError as e:
            errors.append(f"{rel}: {type(e).__name__}: {e}")
            return
        changed = new != old or (isinstance(new, dict) and list(new) != list(old))
        if prefilter and not changed:
            return
        _show(rel, "migrate" if changed else "unchanged", unknown)
        if changed:
            plans.append((p, kind, new, None, {"from_keys": _keys(old), "to_keys": _keys(new),
                                               "kept_unknown_keys": sorted(unknown), "indent": _indent(text)}))

    if drafts.is_dir():
        for p in draft_files(drafts):
            _json_store("draft", p, migrate_draft, prefilter=DRAFT_KEY_MAP)
        for p in writer_sidecar_files(drafts):
            _json_store("writer_sidecar", p, migrate_writer_sidecar)
    for p in _both_layouts(state, sp.REDO_WAITING_FILE):
        _json_store("redo_waiting", p, migrate_redo_waiting)
    for p in _both_layouts(state, sp.ARTICLE_REQUEST_COUNTS_FILE):
        _json_store("article_request_counts", p, migrate_article_request_counts)

    for p in _both_layouts(state, f"{TELEGRAM_SENT_DIR}/*.jsonl"):
        rel = _arcname(p, bases)
        unknown = set()
        try:
            text = p.read_text(encoding="utf-8")
            new_text, n = migrate_telegram_sent(text, unknown)
        except (ValueError, OSError) as e:
            errors.append(f"{rel}: {type(e).__name__}: {e}")
            continue
        if n:
            _show(rel, "migrate", unknown, f"{n} line(s)")
            plans.append((p, "telegram_sent", None, new_text, {"lines": n, "kept_unknown_keys": sorted(unknown)}))
        else:
            _show(rel, "unchanged", unknown)

    for p in _both_layouts(state, OLD_BOSS_IDS):
        target = p.with_name(NEW_BOSS_IDS)
        rel = _arcname(p, bases)
        if target.exists():
            errors.append(f"{rel}: {NEW_BOSS_IDS} already exists next to it")
            continue
        print(f"{'rename':9} {rel} -> {NEW_BOSS_IDS}")
        renames.append((p, target))

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
    backup = state.parent / f"low241_approve_stores_backup_{stamp}.tar.gz"
    with tarfile.open(backup, "w:gz") as tar:
        for p, *_ in plans:
            tar.add(p, arcname=_arcname(p, bases))
        for p, _ in renames:
            tar.add(p, arcname=_arcname(p, bases))
    journal = state.parent / f"low241_approve_stores_{stamp}.journal.jsonl"
    with journal.open("w", encoding="utf-8") as fh:
        for p, kind, new, new_text, info in plans:
            if kind == "telegram_sent":
                tmp = p.with_name(f"{p.name}.tmp.{os.getpid()}")
                tmp.write_text(new_text, encoding="utf-8")
                os.replace(tmp, p)
            else:
                env_load.write_json(p, new, indent=info["indent"])
            fh.write(json.dumps({"file": str(p), "kind": kind, **info}, ensure_ascii=False) + "\n")
        for p, target in renames:
            os.replace(p, target)
            fh.write(json.dumps({"file": str(p), "kind": "rename", "renamed_to": str(target)},
                                ensure_ascii=False) + "\n")
    print(f"written {len(plans)} file(s), renamed {len(renames)}; originals in {backup}; journal {journal}")
    return 0


def _keys(d):
    return list(d) if isinstance(d, dict) else None


if __name__ == "__main__":
    sys.exit(main())
