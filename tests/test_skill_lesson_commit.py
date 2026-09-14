#!/usr/bin/env python3
"""Layer 3 of the skill-lesson gate (LOW-120).

Layer 2 (skill_lesson_filter.py) marks a staged skill write "accepted" when
every rule passes. This module turns an accepted verdict into a real PR: a
fresh worktree off `github/main` (never the production checkout), one commit
with a traceable metadata comment, a pushed branch, and auto-merge once CI is
green — then discards the original pending record. A lesson that no longer
applies (main moved since it was judged) is rejected with a reason, not
silently dropped.

Run:  venv/bin/python tests/test_skill_lesson_commit.py
"""
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import skill_lesson_commit as slc                                     # noqa: E402
from test_skill_lesson_filter import ANCHOR, SKILL                    # noqa: E402


def _repo(tmp: Path) -> Path:
    """A working repo whose 'github' remote is a local bare repo, so push/fetch
    against `github/main` work without any network — the exact pattern layer 3
    uses on the server (worktree off github/main, never the production checkout)."""
    bare = tmp / "github.git"
    subprocess.run(["git", "init", "-q", "--bare", str(bare)], check=True)
    work = tmp / "repo"
    (work / "hermes/skills/carousel-edu").mkdir(parents=True)
    (work / "hermes/skills/carousel-edu/SKILL.md").write_text(SKILL, encoding="utf-8")
    subprocess.run(["git", "init", "-q", "-b", "main", str(work)], check=True)
    subprocess.run(["git", "-C", str(work), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(work), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "-m", "init"], check=True)
    subprocess.run(["git", "-C", str(work), "remote", "add", "github", str(bare)], check=True)
    subprocess.run(["git", "-C", str(work), "push", "-q", "github", "main"], check=True)
    return work


LESSON = "## Hình thật trùng bộ trước\n\nMã đã báo TRUNG thì đổi sang hình khác trong brief.\n\n"


def _stage(tmp: Path, *, verdict_status="accepted", old=ANCHOR, session_id="s1", boss_decision=None) -> tuple:
    """Write a pending record + its layer-2 verdict, as skill_lesson_filter would."""
    pending = tmp / "pending.json"
    pending.write_text(json.dumps({
        "id": "eb4b1c1f", "action": "patch", "created_at": time.time(),
        "payload": {"action": "patch", "name": "carousel-edu", "old_string": old,
                    "new_string": LESSON + old, "replace_all": False, "session_id": session_id},
    }, ensure_ascii=False), encoding="utf-8")
    verdicts = tmp / "state" / "verdicts"
    verdicts.mkdir(parents=True, exist_ok=True)
    verdict_path = verdicts / "blog__kite__eb4b1c1f.json"
    record = {
        "id": "eb4b1c1f", "brand": "blog", "profile": "kite", "skill": "carousel-edu",
        "action": "patch", "file_path": "SKILL.md", "created_at": time.time(),
        "task": "t_kite1", "verdict": verdict_status, "flags": [],
        "added": [l for l in LESSON.splitlines() if l.strip()], "removed": [],
        "pending_path": str(pending),
    }
    if boss_decision:
        record["boss_decision"] = boss_decision
    verdict_path.write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    return pending, verdict_path


def _fakes():
    calls = {"open_pr": [], "auto_merge": [], "pr_state": [], "discard": []}
    return calls, dict(
        open_pr=lambda repo, branch, title, body: calls["open_pr"].append((branch, title, body)) or "https://pr/1",
        enable_auto_merge=lambda url: calls["auto_merge"].append(url),
        pr_state=lambda url: calls["pr_state"].append(url) or {"state": "OPEN", "mergedAt": None},
        discard=lambda verdict: calls["discard"].append(verdict["id"]),
    )


def test_accepted_lesson_becomes_a_pushed_pr_with_metadata():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = _repo(tmp)
        _stage(tmp)
        calls, fakes = _fakes()
        report = slc.run(repo=repo, state=tmp / "state", **fakes)
        verdict = json.loads(next((tmp / "state" / "verdicts").glob("*.json")).read_text(encoding="utf-8"))
        branch = calls["open_pr"][0][0]
        subprocess.run(["git", "-C", str(repo), "fetch", "-q", "github", branch], check=True)
        log = subprocess.run(["git", "-C", str(repo), "log", "-1", "--format=%s%n%b", f"github/{branch}"],
                             capture_output=True, text=True, check=True).stdout
        content = subprocess.run(["git", "-C", str(repo), "show",
                                  f"github/{branch}:hermes/skills/carousel-edu/SKILL.md"],
                                 capture_output=True, text=True, check=True).stdout
        worktrees = subprocess.run(["git", "-C", str(repo), "worktree", "list"],
                                   capture_output=True, text=True, check=True).stdout
    assert report["opened"] == 1 and calls["auto_merge"] == ["https://pr/1"]
    branch_, title, body = calls["open_pr"][0]
    assert branch_ == "skill-lesson/blog-kite-eb4b1c1f" and "kite" in title and "t_kite1" in body
    assert verdict["commit_status"] == "pr_open" and verdict["pr_url"] == "https://pr/1"
    assert "kite" in log and "Claude Sonnet 5" in log
    assert "role=kite" in content and "session=s1" in content and "task=t_kite1" in content
    assert worktrees.count("\n") == 1, "local worktree must be removed, only the main checkout left"


def test_flagged_verdict_is_never_touched():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = _repo(tmp)
        _stage(tmp, verdict_status="flagged")
        calls, fakes = _fakes()
        report = slc.run(repo=repo, state=tmp / "state", **fakes)
    assert report["opened"] == 0 and calls["open_pr"] == [] and calls["discard"] == []


def test_stale_lesson_is_rejected_with_reason_and_discard_is_called():
    """main moved since layer 2 judged it — old_string no longer matches."""
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = _repo(tmp)
        _stage(tmp, old="## Mục không còn tồn tại")
        calls, fakes = _fakes()
        report = slc.run(repo=repo, state=tmp / "state", **fakes)
        verdict_path = next((tmp / "state" / "verdicts").glob("*.json"))
        verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    assert report["rejected"] == 1 and calls["open_pr"] == []
    assert verdict["commit_status"] == "rejected" and "old_string" in verdict["reject_reason"]
    assert calls["discard"] == ["eb4b1c1f"]


def test_default_discard_removes_the_pending_file():
    with tempfile.TemporaryDirectory() as t:
        pending, _ = _stage(Path(t))
        slc.discard_pending({"pending_path": str(pending)})
        assert not pending.exists()
        slc.discard_pending({"pending_path": str(pending)})  # missing file is not an error


def test_open_pr_still_pending_makes_no_new_commit_or_pr():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = _repo(tmp)
        _, verdict_path = _stage(tmp)
        calls, fakes = _fakes()
        slc.run(repo=repo, state=tmp / "state", **fakes)
        first_open_pr_calls = len(calls["open_pr"])
        report = slc.run(repo=repo, state=tmp / "state", **fakes)
    assert report["checked"] == 1 and report["opened"] == 0
    assert len(calls["open_pr"]) == first_open_pr_calls, "must not re-apply/re-push an already-open PR"


def test_merged_pr_marks_verdict_and_discards_pending():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = _repo(tmp)
        pending, verdict_path = _stage(tmp)
        calls, fakes = _fakes()
        slc.run(repo=repo, state=tmp / "state", **fakes)
        fakes["pr_state"] = lambda url: {"state": "MERGED", "mergedAt": "2026-09-15T00:00:00Z"}
        report = slc.run(repo=repo, state=tmp / "state", **fakes)
        verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
    assert report["merged"] == 1 and verdict["commit_status"] == "merged"
    assert calls["discard"] == ["eb4b1c1f"]


def test_closed_without_merge_is_recorded_and_pending_kept():
    """CI never went green and the boss closed it — record the outcome, but leave
    the pending record for a human to decide, don't silently make it vanish."""
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = _repo(tmp)
        pending, verdict_path = _stage(tmp)
        calls, fakes = _fakes()
        slc.run(repo=repo, state=tmp / "state", **fakes)
        fakes["pr_state"] = lambda url: {"state": "CLOSED", "mergedAt": None}
        report = slc.run(repo=repo, state=tmp / "state", **fakes)
        verdict = json.loads(verdict_path.read_text(encoding="utf-8"))
        assert pending.exists(), "boss might still resolve the PR by hand, so keep the lesson queued"
    assert report["closed_without_merge"] == 1
    assert verdict["commit_status"] == "closed_without_merge"
    assert calls["discard"] == []


def test_boss_approved_lesson_goes_through_the_same_pr_path_as_accepted():
    """LOW-154: a flagged lesson the boss pressed ✅ on is treated exactly like
    a clean, machine-accepted one — same worktree/commit/PR/auto-merge path."""
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = _repo(tmp)
        _stage(tmp, verdict_status="flagged", boss_decision="approved")
        calls, fakes = _fakes()
        report = slc.run(repo=repo, state=tmp / "state", **fakes)
        verdict = json.loads(next((tmp / "state" / "verdicts").glob("*.json")).read_text(encoding="utf-8"))
    assert report["opened"] == 1 and len(calls["open_pr"]) == 1
    assert verdict["commit_status"] == "pr_open"


def test_boss_rejected_lesson_is_marked_rejected_and_pending_discarded():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = _repo(tmp)
        _stage(tmp, verdict_status="flagged", boss_decision="rejected")
        calls, fakes = _fakes()
        report = slc.run(repo=repo, state=tmp / "state", **fakes)
        verdict = json.loads(next((tmp / "state" / "verdicts").glob("*.json")).read_text(encoding="utf-8"))
    assert report["rejected"] == 1 and calls["open_pr"] == []
    assert verdict["commit_status"] == "rejected" and "Ông Chủ" in verdict["reject_reason"]
    assert calls["discard"] == ["eb4b1c1f"]


def test_flagged_verdict_awaiting_a_decision_is_still_never_touched():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = _repo(tmp)
        _stage(tmp, verdict_status="flagged")  # no boss_decision at all
        calls, fakes = _fakes()
        report = slc.run(repo=repo, state=tmp / "state", **fakes)
    assert report["opened"] == 0 and report["rejected"] == 0 and calls["open_pr"] == []


def test_merged_and_rejected_are_never_reprocessed():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = _repo(tmp)
        _stage(tmp)
        calls, fakes = _fakes()
        slc.run(repo=repo, state=tmp / "state", **fakes)
        fakes["pr_state"] = lambda url: {"state": "MERGED", "mergedAt": "x"}
        slc.run(repo=repo, state=tmp / "state", **fakes)
        report = slc.run(repo=repo, state=tmp / "state", **fakes)
    assert report == {"at": report["at"], "kind": "commit", "opened": 0, "merged": 0,
                      "rejected": 0, "checked": 0, "closed_without_merge": 0}


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
