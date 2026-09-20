#!/usr/bin/env python3
"""Layer 2 of the skill-lesson gate (LOW-119): judge every staged skill write.

Since LOW-118 the roles' `skill_manage` writes are staged under
`<brand home>/profiles/<role>/pending/skills/<id>.json` instead of editing
`hermes/skills/` in the server checkout. This script reads those records from
both brand homes, applies machine-checkable rules, and writes one verdict per
record under `state/skill_lessons/verdicts/`:

  accepted  every rule passed -> layer 3 (LOW-120) may commit it
  flagged   at least one rule hit -> the boss reviews it on Telegram (topic ada)

It never applies, edits or discards a pending record; that is layer 3's job.
Runs in both containers: the lock and the verdict files keep it to one
Telegram message per record.

Usage:
    venv/bin/python skill_lesson_filter.py            # judge new records, notify flagged
    venv/bin/python skill_lesson_filter.py --no-send  # print the message instead
"""
import argparse
import difflib
import fcntl
import html
import json
import re
import sqlite3
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import env_load
import publish

REPO = env_load.ROOT
STATE = REPO / "state" / "skill_lessons"
RENAME_DICTS = ("docs/tu_dien_ten/overrides.json", "docs/tu_dien_ten/cum.json")

# Measured 2026-09-14: largest SKILL.md is 201 lines / 7 sections; the two real
# lessons roles wrote on 09-10 were 21 and 25 lines.
MAX_ADDED_LINES = 30
MAX_SKILL_LINES = 220
MAX_SKILL_SECTIONS = 10
DUPLICATE_RATIO = 0.85
TELEGRAM_BUDGET = 3800
# The agent keeps calling tools after the task is marked done: on 2026-09-09 a
# lesson was staged 5 s after its run ended (session closed 9 s after).
TASK_END_GRACE_SECONDS = 120

RENAME_COMMIT = re.compile(r"LOW-50|LOW-56|rename|đổi tên English|doi ten English", re.I)
BUG_WORDS = re.compile(r"\b(bug|lỗi|crash|traceback|exception|typeerror|keyerror|valueerror)\b"
                       r"|thiếu `?return|không có `return`", re.I)
AVOID_WORDS = re.compile(r"\b(né|tránh|workaround|bypass)\b|đi vòng", re.I)
BRAND_WORDS = re.compile(r"donniechublog|dcgr", re.I)
# IMAGE_RULES = ten moi cua LUAT_ANH (LOW-142); bai hoc cu van ghi ten cu nen khop ca hai.
# IMAGE_RULES khop PHAN BIET hoa thuong `(?-i:...)`: ten module `image_rules.check_*`
# xuat hien trong bai hoc sach, khong phai nhac tai lieu nguon su that.
SOURCE_OF_TRUTH = re.compile(r"(?-i:IMAGE_RULES)|LUAT_ANH|§|LUẬT CỨNG", re.I)
BACKTICK = re.compile(r"`([^`\n]+)`")
DOTTED = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+$")
PY_FILE = re.compile(r"^[\w/.-]+\.py$")
IDENTIFIER = re.compile(r"^[A-Za-z_]\w*$")
DATA_SUFFIXES = {"json", "md", "yaml", "yml", "sh", "txt", "png", "jpg", "html", "log", "db"}

RULE_LABELS = {
    "stale_symbol": "Lỗi thời",
    "code_changed_since": "Code đã đổi sau khi ghi",
    "workaround": "Né lỗi (cần mở ticket Linear cho chính lỗi — máy chủ chưa có LINEAR_API_KEY)",
    "duplicate": "Trùng nội dung đã có",
    "rewrites_guidance": "Viết đè hướng dẫn cũ",
    "source_of_truth": "Đụng nguồn sự thật",
    "brand_specific": "Gắn brand",
    "too_large": "Quá dài",
    "does_not_apply": "Không áp được lên SKILL hiện tại",
    "unknown_skill": "Skill ngoài repo",
    "manual_action": "Thao tác cần người",
}


class RepoIndex:
    """Tracked files, rename dictionary and git lookups of one checkout."""

    def __init__(self, repo: Path):
        self.repo = Path(repo)
        listing = subprocess.run(["git", "-C", str(self.repo), "ls-files"],
                                 capture_output=True, text=True, check=True).stdout
        self.files = set(listing.splitlines())
        self.by_name = {}
        for path in self.files:
            self.by_name.setdefault(Path(path).name, []).append(path)
        self.renames = {}
        for rel in reversed(RENAME_DICTS):
            try:
                self.renames.update(json.loads((self.repo / rel).read_text(encoding="utf-8")))
            except (OSError, ValueError):
                pass
        self._identifier_cache = {}

    def _read(self, path: str) -> str:
        try:
            return (self.repo / path).read_text(encoding="utf-8")
        except OSError:
            return ""

    def _defines(self, path: str, name: str) -> bool:
        pattern = (rf"^\s*(?:async\s+def|def|class)\s+{re.escape(name)}\b"
                   rf"|^{re.escape(name)}\s*[:=]|^\s*from\s+\S+\s+import\s+.*\b{re.escape(name)}\b")
        return re.search(pattern, self._read(path), re.M) is not None

    def has_identifier(self, name: str) -> bool:
        if name not in self._identifier_cache:
            found = subprocess.run(
                ["git", "-C", str(self.repo), "grep", "-q", "-w", "-F", "-e", name,
                 "--", "*.py", "*.sh", "hermes/*.md"], capture_output=True)
            self._identifier_cache[name] = found.returncode == 0
        return self._identifier_cache[name]

    def _suggest(self, symbol: str, module: str, attr: str):
        new_attr = self.renames.get(symbol) or self.renames.get(attr)
        new_module = self.renames.get(module, module)
        if not new_attr and new_module == module:
            return None
        return f"{new_module}.{new_attr or attr}"

    def check_symbol(self, symbol: str):
        """(exists: True/False/None when unverifiable, file it lives in, suggested new name)."""
        if symbol.endswith(".py"):
            if symbol in self.files or Path(symbol).name in self.by_name:
                return True, self.by_name.get(Path(symbol).name, [symbol])[0], None
            new_stem = self.renames.get(Path(symbol).stem)
            return False, None, f"{new_stem}.py" if new_stem else None
        if "." in symbol:
            parts = symbol.split(".")
            if parts[-1] in DATA_SUFFIXES:
                return None, None, None
            for cut in range(len(parts) - 1, 0, -1):
                module, attr = "/".join(parts[:cut]), parts[cut]
                dotted_module = ".".join(parts[:cut])
                if f"{module}.py" in self.files:
                    ok = self._defines(f"{module}.py", attr)
                    return ok, f"{module}.py", None if ok else self._suggest(symbol, dotted_module, attr)
                if f"{module}/__init__.py" in self.files:
                    if f"{module}/{attr}.py" in self.files:
                        return True, f"{module}/{attr}.py", None
                    package = [p for p in self.files if p.startswith(module + "/") and p.endswith(".py")]
                    ok = any(self._defines(p, attr) for p in package)
                    return ok, f"{module}/__init__.py", None if ok else self._suggest(symbol, dotted_module, attr)
            if parts[0] in self.renames:
                return False, None, self._suggest(symbol, parts[0], parts[1])
            return None, None, None
        ok = self.has_identifier(symbol)
        return ok, None, None if ok else self.renames.get(symbol)

    def commits_since(self, path: str, since: float) -> list:
        iso = datetime.fromtimestamp(since, timezone.utc).isoformat()
        log = subprocess.run(["git", "-C", str(self.repo), "log", "--no-merges", f"--since={iso}",
                              "--format=%h %s", "--", path], capture_output=True, text=True).stdout
        return [line for line in log.splitlines() if line and not RENAME_COMMIT.search(line)]


def extract_symbols(text: str) -> list:
    symbols = []
    for raw in BACKTICK.findall(text):
        token = raw.strip().split("(")[0].strip()
        if not token or " " in token:
            continue
        if PY_FILE.match(token) or DOTTED.match(token) or (IDENTIFIER.match(token) and "_" in token):
            symbols.append(token)
    return list(dict.fromkeys(symbols))


def _line_diff(old: str, new: str) -> tuple:
    added, removed = [], []
    for line in difflib.ndiff(old.splitlines(), new.splitlines()):
        if line.startswith("+ "):
            added.append(line[2:])
        elif line.startswith("- "):
            removed.append(line[2:])
    return added, removed


def _paragraphs(text: str) -> list:
    return [p.strip() for p in re.split(r"\n\s*\n", text) if len(p.strip()) >= 40]


def _apply_record(payload: dict, action: str, skill: str, target: str, current, flag) -> tuple:
    """Áp bản ghi lên SKILL hiện tại -> (kết quả, dòng thêm, dòng bớt).

    `current is None` nghĩa là repo không có skill đó. Hai nhánh KHÔNG áp được
    (thao tác lạ / skill lạ) trả lại `current` NGUYÊN VẸN chứ không phải None:
    cổng trần độ dài ở dưới đọc `result`, nên đổi chỗ này thành None sẽ lặng lẽ
    tắt cổng đó cho một `patch` vào tệp khác SKILL.md.

    Tách khỏi `judge` ở LOW-309: đây là phần "dựng lại tệp", ba luật sinh ra ở
    đây (`manual_action`, `unknown_skill`, `does_not_apply`) là hệ quả của việc
    áp, không phải luật nội dung.
    """
    if action not in ("patch", "edit") or target != "SKILL.md":
        flag("manual_action", f"thao tác `{action}` trên `{target}` — chỉ patch/edit SKILL.md mới tự nhận được")
        return current, (payload.get("content") or payload.get("file_content")
                         or payload.get("new_string") or "").splitlines(), []
    if current is None:
        flag("unknown_skill", f"skill `{skill}` không có trong hermes/skills của repo")
        return current, (payload.get("content") or payload.get("new_string") or "").splitlines(), []
    if action == "patch":
        old, new = payload.get("old_string") or "", payload.get("new_string") or ""
        count = current.count(old) if old else 0
        if count == 0 or (count > 1 and not payload.get("replace_all")):
            flag("does_not_apply", f"`old_string` xuất hiện {count} lần trong SKILL hiện tại")
            result = current
        else:
            result = current.replace(old, new) if payload.get("replace_all") else current.replace(old, new, 1)
        added, removed = _line_diff(old, new)
        return result, added, removed
    result = payload.get("content") or ""
    added, removed = _line_diff(current, result)
    return result, added, removed


def _check_symbol(added_text: str, created_at: float, index: RepoIndex, flag) -> None:
    """Tên hàm/tệp bài học nhắc tới: còn không, và code đó có đổi sau khi ghi bài không.

    Mỗi đường dẫn chỉ báo MỘT lần (`changed_paths`) — một bài nhắc `dre_submit.py`
    năm lần thì vẫn là một chuyện, không phải năm cờ.
    """
    changed_paths = set()
    for symbol in extract_symbols(added_text):
        exists, path, suggestion = index.check_symbol(symbol)
        if exists is False:
            hint = f" (tên mới có thể là `{suggestion}`)" if suggestion else ""
            flag("stale_symbol", f"`{symbol}` không còn trong code{hint}")
        elif exists and path and path not in changed_paths and created_at:
            commits = index.commits_since(path, created_at)
            if commits:
                changed_paths.add(path)
                flag("code_changed_since", f"`{path}` có {len(commits)} commit sau khi ghi bài: {commits[0]}")


def _check_content(added_text: str, current, removed: list, flag) -> None:
    """Luật về NỘI DUNG bài học. Thứ tự gọi ở đây là thứ tự cờ Ông Chủ đọc."""
    if BUG_WORDS.search(added_text) and AVOID_WORDS.search(added_text):
        flag("workaround", "bài dặn vai né một lỗi thay vì sửa lỗi đó")

    if current:
        existing = _paragraphs(current)
        for paragraph in _paragraphs(added_text):
            best = max((difflib.SequenceMatcher(None, paragraph, other).ratio() for other in existing), default=0)
            if best >= DUPLICATE_RATIO:
                flag("duplicate", f"đoạn mới giống {best:.0%} một đoạn đã có: {paragraph[:80]}")
                break

    removed_guidance = [line for line in removed if line.strip()]
    if removed_guidance:
        flag("rewrites_guidance", f"xoá/sửa {len(removed_guidance)} dòng đang có, vd: {removed_guidance[0][:80]}")
    if SOURCE_OF_TRUTH.search(added_text):
        flag("source_of_truth", "bài nhắc IMAGE_RULES (LUAT_ANH) / § / LUẬT CỨNG — người đối chiếu nguồn sự thật")

    brand_hit = BRAND_WORDS.search(added_text)
    if brand_hit:
        flag("brand_specific", f"bài nhắc `{brand_hit.group(0)}` nhưng skill dùng chung hai brand")


def _check_size(added: list, result, action: str, flag) -> None:
    """Trần độ dài: của phần THÊM, và của SKILL sau khi áp."""
    added_lines = [line for line in added if line.strip()]
    if len(added_lines) > MAX_ADDED_LINES:
        flag("too_large", f"thêm {len(added_lines)} dòng (trần {MAX_ADDED_LINES})")
    if result is not None and action in ("patch", "edit"):
        lines, sections = len(result.splitlines()), len(re.findall(r"^## ", result, re.M))
        if lines > MAX_SKILL_LINES:
            flag("too_large", f"SKILL thành {lines} dòng (trần {MAX_SKILL_LINES})")
        if sections > MAX_SKILL_SECTIONS:
            flag("too_large", f"SKILL thành {sections} mục (trần {MAX_SKILL_SECTIONS})")


def judge(record: dict, *, brand: str, profile: str, index: RepoIndex) -> dict:
    """Apply every rule to one pending record and return its verdict."""
    payload = record.get("payload") or {}
    action = payload.get("action") or record.get("action") or ""
    skill = payload.get("name") or ""
    target = payload.get("file_path") or "SKILL.md"
    created_at = float(record.get("created_at") or 0)
    flags: list = []

    def flag(rule, detail):
        flags.append({"rule": rule, "detail": detail})

    skill_path = index.repo / "hermes" / "skills" / skill / "SKILL.md"
    current = skill_path.read_text(encoding="utf-8") if skill and skill_path.is_file() else None
    result, added, removed = _apply_record(payload, action, skill, target, current, flag)
    added_text = "\n".join(added)

    _check_symbol(added_text, created_at, index, flag)
    _check_content(added_text, current, removed, flag)
    _check_size(added, result, action, flag)

    return {
        "id": record.get("id"), "brand": brand, "profile": profile, "skill": skill,
        "action": action, "file_path": target, "created_at": created_at,
        "origin": record.get("origin"), "summary": record.get("summary"),
        "verdict": "flagged" if flags else "accepted", "flags": flags,
        "added": added, "removed": removed,
    }


def collect_pending(homes: dict) -> list:
    found = []
    for brand, home in homes.items():
        for path in sorted(Path(home).glob("profiles/*/pending/skills/*.json")):
            try:
                record = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as e:
                print(f"[warning] unreadable pending record {path}: {e}", file=sys.stderr)
                continue
            found.append((brand, path.parents[2].name, path, record))
    return found


def find_task(kanban_db: Path, profile: str, created_at: float):
    """Task whose run by `profile` covered the moment the lesson was staged."""
    if not Path(kanban_db).exists() or not created_at:
        return None
    try:
        con = sqlite3.connect(f"file:{kanban_db}?mode=ro", uri=True)
        try:
            row = con.execute(
                "SELECT task_id FROM task_runs WHERE profile = ? AND started_at <= ? "
                "AND (ended_at IS NULL OR ended_at >= ?) ORDER BY started_at DESC LIMIT 1",
                (profile, created_at, created_at - TASK_END_GRACE_SECONDS)).fetchone()
        finally:
            con.close()
    except sqlite3.Error as e:
        print(f"[warning] cannot read {kanban_db}: {e}", file=sys.stderr)
        return None
    return row[0] if row else None


def keyboard_for(key: str) -> dict:
    """Two buttons routed to skill_lesson_approve.handle_button (LOW-154) via
    approve_post.handle_callback, same callback machinery as imgok/imgno."""
    return {"inline_keyboard": [[
        {"text": "✅ Nhận", "callback_data": f"skillok:{key}"},
        {"text": "❌ Từ chối", "callback_data": f"skillno:{key}"},
    ]]}


def format_message(verdict: dict) -> str:
    """One Telegram message for ONE flagged lesson — every lesson gets its own
    message (not batched) so its Duyệt/Từ chối buttons unambiguously belong to
    it (LOW-154)."""
    esc = html.escape
    lines = [f"🧪 <b>Bài học skill cần duyệt</b> — {esc(verdict['profile'])} · {esc(verdict['brand'])} "
             f"· task <code>{esc(verdict.get('task') or '?')}</code> · skill <code>{esc(verdict['skill'])}</code>"]
    lines += [f"• <b>{esc(RULE_LABELS.get(f['rule'], f['rule']))}</b>: {esc(f['detail'])}"
             for f in verdict["flags"]]
    diff = ["+ " + line for line in verdict["added"][:8]] + ["- " + line for line in verdict["removed"][:4]]
    if diff:
        text = "\n".join(diff)
        budget = TELEGRAM_BUDGET - sum(len(line) for line in lines)
        if len(text) > budget:
            text = text[:budget] + "\n… (cắt bớt, xem state/skill_lessons/verdicts/)"
        lines.append("<pre>" + esc(text) + "</pre>")
    return "\n".join(lines)


def run(homes=None, repo=REPO, state=STATE, send=None, now=None, notify=True) -> dict:
    """Judge records without a verdict yet, then notify every flagged, unnotified verdict."""
    homes = env_load.hermes_homes() if homes is None else homes
    now = time.time() if now is None else now
    verdict_dir = Path(state) / "verdicts"
    verdict_dir.mkdir(parents=True, exist_ok=True)
    index = RepoIndex(repo)
    pending = collect_pending(homes)
    new = []
    for brand, profile, path, record in pending:
        out = verdict_dir / f"{brand}__{profile}__{record.get('id') or path.stem}.json"
        if out.exists():
            continue
        verdict = judge(record, brand=brand, profile=profile, index=index)
        verdict.update(task=find_task(Path(homes[brand]) / "kanban.db", profile, verdict["created_at"]),
                       pending_path=str(path), judged_at=now, notified=False)
        env_load.write_json(out, verdict)
        new.append(verdict)

    waiting = []
    for out in sorted(verdict_dir.glob("*.json")):
        verdict = json.loads(out.read_text(encoding="utf-8"))
        if verdict["verdict"] == "flagged" and not verdict.get("notified"):
            waiting.append((out, verdict))

    sender = send or publish.send_topic_with_keyboard
    sent = 0
    notified_ok = True
    for out, verdict in waiting:
        if not notify:
            print(format_message(verdict))
            continue
        result = sender(format_message(verdict), "ada", keyboard_for(out.stem))
        if not result:
            notified_ok = False
            continue
        verdict["notified"] = True
        if isinstance(result, dict):
            verdict["telegram_chat_id"] = (result.get("chat") or {}).get("id")
            verdict["telegram_message_id"] = result.get("message_id")
        env_load.write_json(out, verdict)
        sent += 1

    rules = Counter(f["rule"] for v in new for f in v["flags"])
    report = {"at": datetime.fromtimestamp(now, timezone.utc).isoformat(), "pending": len(pending),
              "new": len(new), "accepted": sum(v["verdict"] == "accepted" for v in new),
              "flagged": sum(v["verdict"] == "flagged" for v in new), "by_rule": dict(rules),
              "notified": sent, "notified_ok": notified_ok}
    with open(Path(state) / "reports.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(report, ensure_ascii=False) + "\n")
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Layer 2 of the skill-lesson gate: judge staged skill writes")
    ap.add_argument("--no-send", action="store_true", help="print the Telegram message instead of sending")
    args = ap.parse_args()
    STATE.mkdir(parents=True, exist_ok=True)
    with open(STATE / ".lock", "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("skill lessons: another run holds the lock, skipping")
            return 0
        report = run(notify=not args.no_send)
    print(f"skill lessons: pending {report['pending']}, new {report['new']}, accepted {report['accepted']}, "
          f"flagged {report['flagged']} {report['by_rule'] or ''}, notified {report['notified']}")
    return 0 if report["notified_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
