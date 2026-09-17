#!/usr/bin/env python3
"""Old → new state path names (LOW-228), as pure functions.

Applies docs/tu_dien_ten/state_paths_v2.json to (a) single path segments, (b) any
string that embeds a path under `…/chuan_bi/<draft_id>/…`, and (c) instruction text
(briefs, handoffs, task bodies) that also names files bare ("mở bang_anh.png").
Used by migrate_state_paths.py on disk data and by the equivalence check.
"""
import json
import re
from functools import lru_cache
from pathlib import Path

TABLE_FILE = Path(__file__).resolve().parent / "docs" / "tu_dien_ten" / "state_paths_v2.json"


@lru_cache(maxsize=1)
def table() -> dict:
    return json.loads(TABLE_FILE.read_text(encoding="utf-8"))


_PATTERNS = [
    (re.compile(r"^xep_hang_(.+)\.png$"), r"ranking_\1.png"),
    (re.compile(r"^chup_(\d+)_(\w+)\.png$"), r"capture_\1_\2.png"),
    (re.compile(r"^(.+)\.ngang\.png$"), r"\1.landscape.png"),
    (re.compile(r"^(.+)\.ban_giao\.md$"), r"\1.handoff.md"),
    (re.compile(r"^them_(\d+)$"), r"extra_\1"),
]


def new_name(name: str, top_level: bool) -> str:
    """New name for ONE path segment. `top_level` = direct child of the draft dir,
    where the draft-level file names (xong.json, bang_anh.png…) apply."""
    t = table()
    if top_level and name in t["draft_files"]:
        return t["draft_files"][name]
    if name in t["dirs"]:
        return t["dirs"][name]
    for rx, rep in _PATTERNS:
        if rx.match(name):
            return rx.sub(rep, name)
    return name


def new_relative(parts: list) -> list:
    """Segments below the draft dir → new segments."""
    return [new_name(p, i == 0) for i, p in enumerate(parts)]


_PATH_RX = re.compile(r"(?<![A-Za-z0-9_])chuan_bi/(?P<draft>[^/\s\"'`<>()]+)(?P<rest>(?:/[^/\s\"'`<>()]+)*)")
_LOCK_RX = re.compile(r"(?<![A-Za-z0-9_])chuan_bi\.(\d+)\.lock\b")
_TRAIL = ".,:;"


def _sub_path(m: re.Match) -> str:
    rest = m.group("rest")
    tail = ""
    while rest and rest[-1] in _TRAIL:
        tail = rest[-1] + tail
        rest = rest[:-1]
    parts = [p for p in rest.split("/") if p]
    new_rest = "".join("/" + p for p in new_relative(parts))
    return f"{table()['root']['chuan_bi']}/{m.group('draft')}{new_rest}{tail}"


def rewrite_paths(s: str) -> str:
    """Rewrite every embedded `chuan_bi/<draft>/<rest>` path (absolute or relative)."""
    if "chuan_bi" not in s:
        return s
    s = _PATH_RX.sub(_sub_path, s)
    return _LOCK_RX.sub(r"prepare.\1.lock", s)


_BARE = None


def rewrite_text(s: str) -> str:
    """Paths + bare draft-level file names mentioned in instruction text."""
    global _BARE
    s = rewrite_paths(s)
    if _BARE is None:
        names = dict(table()["draft_files"])
        names.pop("xong.json.v1.bak", None)
        _BARE = [(re.compile(r"(?<![A-Za-z0-9_/.])" + re.escape(k) + r"(?![A-Za-z0-9_])"), v) for k, v in names.items()]
        _BARE.append((re.compile(r"\.ban_giao\.md\b"), ".handoff.md"))
    for rx, v in _BARE:
        s = rx.sub(v, s)
    return s


def rewrite_json(obj, fn=rewrite_paths):
    """Apply `fn` to every string value (not keys) of a JSON-like object."""
    if isinstance(obj, str):
        return fn(obj)
    if isinstance(obj, list):
        return [rewrite_json(x, fn) for x in obj]
    if isinstance(obj, dict):
        return {k: rewrite_json(v, fn) for k, v in obj.items()}
    return obj
