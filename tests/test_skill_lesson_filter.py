#!/usr/bin/env python3
"""Layer 2 of the skill-lesson gate (LOW-119).

The case it must catch is real: on 2026-09-09 blog/kite staged a "known renderer
bug (avoid in spec)" section telling roles to dodge `render_edu.anh_lam_nen`,
a bug fixed nine hours later and a function renamed by LOW-50. That lesson sat
in HEAD for five days. A clean lesson must still pass untouched.

Run:  venv/bin/python tests/test_skill_lesson_filter.py
"""
import json
import sqlite3
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import skill_lesson_filter as slf                                     # noqa: E402

ANCHOR = "## Nhìn lại trước khi nộp (đọc spec)"
SKILL = f"""---
name: carousel-edu
---

# carousel-edu

Kite diễn đạt lại paper bằng art vector gốc trong bộ khung tạp chí, renderer vẽ
hết phần khung; vai chia slide, chọn hình diễn đạt và viết chữ cho từng slide.

{ANCHOR}

1. Bìa có hook giật và art không?
"""

BUG_LESSON = """## Bug renderer đã biết (tránh ở spec)

`render_edu.anh_lam_nen` không có `return` ở cuối khi ảnh chụp dạng "mo"
cần lớp mo (`can_lop=True`, lỗi `TypeError: cannot unpack non-iterable NoneType`
trong `s_cover`/`s_figure` khi dùng ảnh chụp rối nhiều chi tiết). Công đoạn để
**bìa vector hero** (không set `image`) và đưa ảnh thật bắt buộc vào `figure`.

"""

CLEAN_LESSON = """## Hình thật trùng bộ trước

Trước khi viết spec, đối chiếu từng mã hình thật với dòng báo TRUNG mà
`image_rules.check_not_reused` in ra ở lần nộp trước; mã đã bị báo thì đổi sang
hình khác trong brief rồi mới dựng slide.

"""


def _repo(tmp: Path) -> Path:
    repo = tmp / "repo"
    (repo / "hermes/skills/carousel-edu").mkdir(parents=True)
    (repo / "docs/tu_dien_ten").mkdir(parents=True)
    (repo / "render_edu.py").write_text("def image_make_background(sl, th, name):\n    return 1, 2\n")
    (repo / "image_rules.py").write_text("def check_not_reused(label, path, draft_id, link=''):\n    return [], []\n")
    (repo / "docs/tu_dien_ten/overrides.json").write_text(
        json.dumps({"render_edu.anh_lam_nen": "image_make_background"}))
    (repo / "docs/tu_dien_ten/cum.json").write_text(json.dumps({"luat_anh": "image_rules"}))
    (repo / "hermes/skills/carousel-edu/SKILL.md").write_text(SKILL, encoding="utf-8")
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "add", "-A"], check=True)
    subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@t", "-c", "user.name=t",
                    "commit", "-q", "-m", "init"], check=True)
    return repo


def _record(section: str, *, created_at: float, old: str = ANCHOR, record_id: str = "eb4b1c1f") -> dict:
    return {"id": record_id, "subsystem": "skills", "action": "patch", "origin": "foreground",
            "summary": "patch 'carousel-edu' SKILL.md", "created_at": created_at,
            "payload": {"action": "patch", "name": "carousel-edu", "old_string": old,
                        "new_string": section + old, "replace_all": False}}


def _judge(tmp: Path, record: dict) -> dict:
    return slf.judge(record, brand="blog", profile="kite", index=slf.RepoIndex(_repo(tmp)))


def _rules(verdict: dict) -> set:
    return {f["rule"] for f in verdict["flags"]}


def test_stale_workaround_lesson_is_flagged():
    with tempfile.TemporaryDirectory() as t:
        verdict = _judge(Path(t), _record(BUG_LESSON, created_at=1_700_000_000))
    assert verdict["verdict"] == "flagged"
    assert {"stale_symbol", "workaround"} <= _rules(verdict), verdict["flags"]
    stale = next(f["detail"] for f in verdict["flags"] if f["rule"] == "stale_symbol")
    assert "render_edu.anh_lam_nen" in stale and "image_make_background" in stale, stale


def test_clean_lesson_is_accepted():
    with tempfile.TemporaryDirectory() as t:
        verdict = _judge(Path(t), _record(CLEAN_LESSON, created_at=time.time() + 3600))
    assert verdict["verdict"] == "accepted", verdict["flags"]
    assert verdict["removed"] == [] and any("check_not_reused" in line for line in verdict["added"])


def test_patch_that_does_not_apply_is_flagged():
    with tempfile.TemporaryDirectory() as t:
        verdict = _judge(Path(t), _record(CLEAN_LESSON, created_at=time.time() + 3600,
                                          old="## Mục không tồn tại"))
    assert "does_not_apply" in _rules(verdict), verdict["flags"]


def test_duplicate_lesson_is_flagged():
    copy = ("Kite diễn đạt lại paper bằng art vector gốc trong bộ khung tạp chí, renderer vẽ\n"
            "hết phần khung; vai chia slide, chọn hình diễn đạt và viết chữ cho từng slide.\n\n")
    with tempfile.TemporaryDirectory() as t:
        verdict = _judge(Path(t), _record("## Nhắc lại\n\n" + copy, created_at=time.time() + 3600))
    assert "duplicate" in _rules(verdict), verdict["flags"]


def test_rewriting_existing_guidance_is_flagged():
    old = "1. Bìa có hook giật và art không?"
    record = _record("", created_at=time.time() + 3600, old=old)
    record["payload"]["new_string"] = "1. Bìa không cần hook."
    with tempfile.TemporaryDirectory() as t:
        verdict = _judge(Path(t), record)
    assert "rewrites_guidance" in _rules(verdict), verdict["flags"]


def test_oversized_lesson_is_flagged():
    section = "## Dài\n\n" + "".join(f"Dòng hướng dẫn số {i} cho vai.\n" for i in range(40)) + "\n"
    with tempfile.TemporaryDirectory() as t:
        verdict = _judge(Path(t), _record(section, created_at=time.time() + 3600))
    assert "too_large" in _rules(verdict), verdict["flags"]


def _home_with_pending(tmp: Path, record: dict) -> Path:
    home = tmp / "hermes-blog"
    pending = home / "profiles" / "kite" / "pending" / "skills"
    pending.mkdir(parents=True)
    (pending / f"{record['id']}.json").write_text(json.dumps(record, ensure_ascii=False), encoding="utf-8")
    con = sqlite3.connect(home / "kanban.db")
    con.execute("CREATE TABLE task_runs (task_id TEXT, profile TEXT, started_at REAL, ended_at REAL)")
    con.execute("INSERT INTO task_runs VALUES ('t_kite1', 'kite', ?, ?)",
                (record["created_at"] - 60, record["created_at"] + 60))
    con.commit()
    con.close()
    return home


def test_run_notifies_each_flagged_lesson_once_with_task():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = _repo(tmp)
        home = _home_with_pending(tmp, _record(BUG_LESSON, created_at=1_700_000_000))
        sent = []
        send = lambda text, role: sent.append((text, role)) or True             # noqa: E731
        first = slf.run(homes={"blog": home}, repo=repo, state=tmp / "state", send=send)
        second = slf.run(homes={"blog": home}, repo=repo, state=tmp / "state", send=send)
        verdict = json.loads(next((tmp / "state" / "verdicts").glob("*.json")).read_text(encoding="utf-8"))
    assert first["flagged"] == 1 and second["new"] == 0, (first, second)
    assert len(sent) == 1, f"one message per flagged lesson, got {len(sent)}"
    text, role = sent[0]
    assert role == "ada" and "t_kite1" in text and "Lỗi thời" in text, text
    assert verdict["task"] == "t_kite1" and verdict["notified"] is True


def test_failed_send_is_retried_next_run():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = _repo(tmp)
        home = _home_with_pending(tmp, _record(BUG_LESSON, created_at=1_700_000_000))
        attempts = []
        failing = lambda text, role: attempts.append(role) and False            # noqa: E731
        working = lambda text, role: attempts.append(role) or True              # noqa: E731
        first = slf.run(homes={"blog": home}, repo=repo, state=tmp / "state", send=failing)
        second = slf.run(homes={"blog": home}, repo=repo, state=tmp / "state", send=working)
    assert first["notified_ok"] is False and second["notified"] == 1, (first, second)
    assert len(attempts) == 2


def test_lesson_staged_just_after_run_end_maps_to_task():
    """Real case 2026-09-09: run t_14df7eee ended 00:45:25, the skill patch was
    staged 00:45:30 — the agent keeps calling tools after the task is marked done."""
    with tempfile.TemporaryDirectory() as t:
        db = Path(t) / "kanban.db"
        con = sqlite3.connect(db)
        con.execute("CREATE TABLE task_runs (task_id TEXT, profile TEXT, started_at REAL, ended_at REAL)")
        con.execute("INSERT INTO task_runs VALUES ('t_14df7eee', 'kite', 1788914503, 1788914725)")
        con.execute("INSERT INTO task_runs VALUES ('t_other', 'miles', 1788914700, 1788914800)")
        con.commit()
        con.close()
        assert slf.find_task(db, "kite", 1788914730.1) == "t_14df7eee"
        assert slf.find_task(db, "kite", 1788914725 + slf.TASK_END_GRACE_SECONDS + 10) is None


def test_accepted_lesson_sends_nothing():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        repo = _repo(tmp)
        home = _home_with_pending(tmp, _record(CLEAN_LESSON, created_at=time.time() + 3600))
        sent = []
        report = slf.run(homes={"blog": home}, repo=repo, state=tmp / "state",
                         send=lambda text, role: sent.append(text) or True)
    assert report["accepted"] == 1 and sent == [], (report, sent)


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
