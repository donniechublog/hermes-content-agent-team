#!/usr/bin/env python3
"""Layer 3 of the skill-lesson gate (LOW-120): commit accepted lessons via PR.

Layer 2 (skill_lesson_filter.py) judges each staged skill write and marks it
"accepted" when every rule passes. This script takes those accepted verdicts
and turns them into real repo history: a fresh worktree off `github/main`
(never the server's production checkout), one commit per lesson with a
traceable metadata comment, a pushed branch, a PR, and auto-merge once CI is
green. It never pushes `deploy` (that stays a deliberate, manual deploy step)
and never touches a lesson the boss still needs to review (verdict "flagged").

Once a lesson is merged — or found impossible to re-apply because `main`
moved since it was judged — its original pending record
(`<home>/profiles/<role>/pending/skills/<id>.json`) is discarded, since layer 2
no longer needs to re-judge it and layer 1 is done staging it. A rejection is
recorded with its reason in the verdict file, never silently dropped.

Usage:
    venv/bin/python skill_lesson_commit.py
"""
import argparse
import fcntl
import json
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import env_load
import skill_lesson_filter as slf

REPO = slf.REPO
STATE = slf.STATE
BRANCH_PREFIX = "skill-lesson"


class ApplyError(Exception):
    """A lesson can no longer be applied cleanly (main moved, or the action needs a human)."""


def branch_name(verdict: dict) -> str:
    return f"{BRANCH_PREFIX}/{verdict['brand']}-{verdict['profile']}-{verdict['id']}"


def metadata_comment(verdict: dict, payload: dict) -> str:
    """One traceable line embedded right where the lesson lands, so layer 2 (or a
    human) can find its origin later without digging through git blame."""
    when = (datetime.fromtimestamp(verdict["created_at"], timezone.utc).strftime("%Y-%m-%d")
            if verdict.get("created_at") else "unknown")
    symbols = slf.extract_symbols("\n".join(verdict.get("added") or []))
    symbol = symbols[0] if symbols else verdict.get("skill", "")
    session = payload.get("session_id") or "unknown"
    return (f"<!-- skill-lesson: {when} | role={verdict['profile']} | brand={verdict['brand']} "
            f"| task={verdict.get('task') or 'unknown'} | session={session} | symbol={symbol} -->")


def build_worktree(repo: Path, work_dir: Path, branch: str, *, remote: str = "github", base: str = "main") -> None:
    subprocess.run(["git", "-C", str(repo), "fetch", "-q", remote, base], check=True)
    subprocess.run(["git", "-C", str(repo), "worktree", "add", "-q", "-b", branch,
                    str(work_dir), f"{remote}/{base}"], check=True)


def remove_worktree(repo: Path, work_dir: Path, branch: str) -> None:
    subprocess.run(["git", "-C", str(repo), "worktree", "remove", "--force", str(work_dir)], check=False)
    subprocess.run(["git", "-C", str(repo), "branch", "-D", branch], check=False)
    shutil.rmtree(work_dir, ignore_errors=True)


def apply_lesson(work_dir: Path, verdict: dict, payload: dict) -> str:
    """Apply the pending payload, with a metadata comment appended, to the SKILL.md
    inside `work_dir`. Returns the skill name. Raises ApplyError when the exact
    text layer 2 judged no longer matches — main moved since then — or the
    action needs a human (create/delete/write_file)."""
    skill = payload.get("name") or verdict["skill"]
    skill_path = work_dir / "hermes" / "skills" / skill / "SKILL.md"
    action = payload.get("action") or verdict["action"]
    if not skill_path.is_file():
        raise ApplyError(f"skill `{skill}` không còn trong hermes/skills của repo")
    current = skill_path.read_text(encoding="utf-8")
    meta = metadata_comment(verdict, payload)
    if action == "patch":
        old, new = payload.get("old_string") or "", payload.get("new_string") or ""
        count = current.count(old) if old else 0
        if not old or count == 0 or (count > 1 and not payload.get("replace_all")):
            raise ApplyError(f"`old_string` xuất hiện {count} lần trong SKILL hiện tại — main đã đổi từ lúc chấm")
        new_with_meta = new + "\n" + meta + "\n"
        result = (current.replace(old, new_with_meta) if payload.get("replace_all")
                  else current.replace(old, new_with_meta, 1))
    elif action == "edit":
        result = (payload.get("content") or "") + "\n" + meta + "\n"
    else:
        raise ApplyError(f"thao tác `{action}` cần người áp tay, không tự commit được")
    skill_path.write_text(result, encoding="utf-8")
    return skill


def commit_lesson(work_dir: Path, verdict: dict, skill: str) -> None:
    subprocess.run(["git", "-C", str(work_dir), "add", f"hermes/skills/{skill}/SKILL.md"], check=True)
    message = (f"docs(skills): bài học {verdict['profile']} ({verdict['brand']}) — {skill}\n\n"
               f"Task: {verdict.get('task') or 'không rõ'}\n"
               "Tự nhận qua cổng bài học lớp 2 (LOW-119) — mọi luật đều qua.\n\n"
               "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>")
    subprocess.run(["git", "-C", str(work_dir), "-c", "user.email=skill-lessons@content-team",
                    "-c", "user.name=skill-lesson-gate", "commit", "-q", "-m", message], check=True)


def format_pr_body(verdict: dict) -> str:
    lines = [
        "Bài học skill được máy lọc (LOW-119) chấm sạch, tự merge qua cổng lớp 3 (LOW-120).", "",
        f"- Vai: {verdict['profile']}", f"- Brand: {verdict['brand']}",
        f"- Task: {verdict.get('task') or 'không rõ'}", f"- Skill: {verdict['skill']}", "",
        "🤖 Generated with [Claude Code](https://claude.com/claude-code)",
    ]
    return "\n".join(lines)


def default_open_pr(repo: Path, branch: str, title: str, body: str) -> str:
    out = subprocess.run(["gh", "pr", "create", "--base", "main", "--head", branch,
                          "--title", title, "--body", body], cwd=repo, capture_output=True,
                         text=True, check=True)
    return out.stdout.strip().splitlines()[-1]


def default_enable_auto_merge(pr_url: str) -> None:
    subprocess.run(["gh", "pr", "merge", pr_url, "--merge", "--auto"], check=True)


def default_pr_state(pr_url: str) -> dict:
    out = subprocess.run(["gh", "pr", "view", pr_url, "--json", "state,mergedAt"],
                         capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def discard_pending(verdict: dict) -> None:
    """The lesson is resolved (merged or rejected) — layer 1's queue entry has done
    its job. Best-effort: a missing file is not an error (already cleared)."""
    try:
        Path(verdict["pending_path"]).unlink()
    except (KeyError, OSError):
        pass


def run(*, repo=REPO, state=STATE, open_pr=default_open_pr, enable_auto_merge=default_enable_auto_merge,
        pr_state=default_pr_state, discard=discard_pending, now=None) -> dict:
    verdict_dir = Path(state) / "verdicts"
    opened = merged = rejected = checked = closed = 0
    for out in sorted(verdict_dir.glob("*.json")):
        verdict = json.loads(out.read_text(encoding="utf-8"))
        boss_decision = verdict.get("boss_decision")
        # A clean lesson (layer 2) or a flagged one the boss approved on
        # Telegram (LOW-154) both go through the same apply→PR→auto-merge path
        # below. A flagged lesson with no decision yet is left alone — still
        # waiting on the boss, not this script's call.
        if verdict.get("verdict") != "accepted" and boss_decision != "approved":
            if verdict.get("verdict") == "flagged" and boss_decision == "rejected" \
                    and verdict.get("commit_status") not in ("merged", "rejected", "closed_without_merge"):
                verdict["commit_status"] = "rejected"
                verdict["reject_reason"] = "Ông Chủ từ chối trên Telegram"
                env_load.write_json(out, verdict)
                discard(verdict)
                rejected += 1
            continue
        status = verdict.get("commit_status")
        if status in ("merged", "rejected", "closed_without_merge"):
            continue
        if status == "pr_open":
            checked += 1
            info = pr_state(verdict["pr_url"])
            if info.get("mergedAt"):
                verdict["commit_status"] = "merged"
                env_load.write_json(out, verdict)
                discard(verdict)
                merged += 1
            elif info.get("state") == "CLOSED":
                verdict["commit_status"] = "closed_without_merge"
                env_load.write_json(out, verdict)
                closed += 1
            continue

        pending_path = Path(verdict["pending_path"])
        try:
            payload = (json.loads(pending_path.read_text(encoding="utf-8")).get("payload") or {})
        except (OSError, ValueError) as e:
            verdict["commit_status"], verdict["reject_reason"] = "rejected", f"không đọc được pending: {e}"
            env_load.write_json(out, verdict)
            rejected += 1
            continue

        branch = branch_name(verdict)
        # mkdtemp-ok: `finally` ngay duoi goi remove_worktree(), trong do co
        # shutil.rmtree(work_dir) — thu muc nay khong the song qua vong lap.
        work_dir = Path(tempfile.mkdtemp(prefix="skill-lesson-"))
        try:
            build_worktree(repo, work_dir, branch)
            skill = apply_lesson(work_dir, verdict, payload)
            commit_lesson(work_dir, verdict, skill)
            subprocess.run(["git", "-C", str(work_dir), "push", "-q", "github", branch], check=True)
            pr_url = open_pr(repo, branch, f"docs(skills): bài học {verdict['profile']} — {skill}",
                             format_pr_body(verdict))
            enable_auto_merge(pr_url)
            verdict.update(commit_status="pr_open", pr_url=pr_url, branch=branch)
            env_load.write_json(out, verdict)
            opened += 1
        except ApplyError as e:
            verdict["commit_status"], verdict["reject_reason"] = "rejected", str(e)
            env_load.write_json(out, verdict)
            discard(verdict)
            rejected += 1
        finally:
            remove_worktree(repo, work_dir, branch)

    report = {"at": datetime.fromtimestamp(now, timezone.utc).isoformat() if now else
              datetime.now(timezone.utc).isoformat(), "kind": "commit", "opened": opened,
              "merged": merged, "rejected": rejected, "checked": checked, "closed_without_merge": closed}
    with open(Path(state) / "reports.jsonl", "a", encoding="utf-8") as fh:
        fh.write(json.dumps(report, ensure_ascii=False) + "\n")
    return report


def main() -> int:
    argparse.ArgumentParser(description="Layer 3 of the skill-lesson gate: commit accepted lessons via PR").parse_args()
    STATE.mkdir(parents=True, exist_ok=True)
    with open(STATE / ".lock", "w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("skill lesson commit: another run holds the lock, skipping")
            return 0
        report = run()
    print(f"skill lesson commit: opened {report['opened']}, merged {report['merged']}, "
          f"rejected {report['rejected']}, checked {report['checked']}, "
          f"closed_without_merge {report['closed_without_merge']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
