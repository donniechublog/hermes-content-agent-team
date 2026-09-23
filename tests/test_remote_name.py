#!/usr/bin/env python3
"""Khong tai lieu/script nao duoc goi remote la `origin` (CLAUDE.md muc 2).

Chuan ten remote chot 21/09/2026: chi co `github` (an toan) va `deploy`
(= production, push vao la deploy ngay). **Khong clone nao co remote ten
`origin`** — go nham `git push origin main` theo thoi quen se bao loi thay vi
deploy, va do la co y.

Vi sao can mot cong chu khong chi mot dong trong CLAUDE.md: 23/09/2026 van con
hai cho goi ten `origin` trong loi van (`skill_lesson_commit.py` va
`hermes/scripts/skill_lesson_commit.sh` — ca hai deu bao "never pushes
origin"), trong khi chinh ma nguon cua chung da goi dung `github`. Loi van lech
ma khong ai thay thi nguoi doc sau se tin loi van.

CHI bat cac dang LENH GIT that. KHONG dung toi:
  - truong du lieu ten `origin` (`{"origin": null}` trong hermes/cron/jobs.*.json,
    `record.get("origin")`, `tests/golden/judge_verdicts.json`) — trung ten, khac viec
  - tu tieng Anh `original` / `origin` trong cau van thuong

HAI TEP DUOC MIEN VINH VIEN vi chung la HO SO LICH SU, khong phai huong dan:
`origin` co that vao thoi diem chung duoc viet, sua lai la bop meo ghi chep.

Chay:  venv/bin/python tests/test_remote_name.py
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

ROOT = Path(__file__).resolve().parent.parent

# Hai tep DAY luat, khong phai vi pham no:
#   - CLAUDE.md CO Y nhac `origin` de canh bao ("khong clone nao co remote ten
#     origin", "clone con origin thi rename").
#   - chinh tep nay: no phai chua vi du vi pham lam mau thu, neu khong thi khong
#     co cach nao chung minh regex con bat duoc.
RULE_FILE = {"CLAUDE.md", "tests/test_remote_name.py"}

# Ho so lich su — xem docstring.
HISTORY = {
    "hermes/gateway/dcgr/config.yaml",      # ghi chu su co 07/09: `reset --hard origin/main`
    "nhat_ky/2026-09-12-the-3-bang-van-ban-di-kem.md",   # nhat ky: "Deploy: push origin"
}

# `git <lenh> ... origin`, `origin/<nhanh>`, `remote add origin`.
GIT_ORIGIN = re.compile(
    r"\borigin/[A-Za-z0-9._\-]+"
    r"|\b(?:push|pull|fetch|clone|remote|reset|merge|rebase|checkout|ls-remote)\b"
    r"[^\n`'\"]{0,40}\borigin\b"
    r"|\bpushes?\s+`?origin`?",
    re.I)

EXT = {".py", ".sh", ".md", ".yaml", ".yml", ".toml", ".cfg"}


# Duyet thang thu muc, KHONG goi `git ls-files`: tren o D: cua may dev, moi lenh
# git deu chet vi "dubious ownership" (worktree nam tren he tep khong ghi chu so
# huu), va mot cong chi chay duoc o mot so may thi khong phai cong.
SKIP_DIR = {".git", "venv", "node_modules", "__pycache__", "state", "drafts",
            "assets", ".claude", "backups"}


def _files() -> list:
    ra = []
    for p in ROOT.rglob("*"):
        if p.suffix not in EXT or not p.is_file():
            continue
        if any(phan in SKIP_DIR for phan in p.relative_to(ROOT).parts[:-1]):
            continue
        ra.append(p.relative_to(ROOT).as_posix())
    return ra


def test_no_file_calls_a_remote_origin():
    xau = []
    for rel in _files():
        if rel in RULE_FILE or rel in HISTORY:
            continue
        try:
            noi_dung = (ROOT / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for i, dong in enumerate(noi_dung.splitlines(), 1):
            if GIT_ORIGIN.search(dong):
                xau.append(f"{rel}:{i}: {dong.strip()[:100]}")
    assert not xau, (
        "goi remote la `origin` — chuan la `github` (an toan) hoac `deploy` "
        "(production); xem CLAUDE.md muc 2:\n  " + "\n  ".join(xau))


def test_the_gate_would_actually_catch_a_regression():
    """Cong nao cung phai tu chung minh no bat duoc — mot regex go sai thi im
    lang xanh mai. Day la cac dong THAT da bi sua o 23/09/2026."""
    phai_bat = [
        "# pushes origin (deploy stays a deliberate manual step).",
        "green. It never pushes `origin` (that stays a deliberate, manual deploy step)",
        "git push origin main",
        "  # d4ded02) da bi `reset --hard origin/main` 07/09 xoa mat, ma tien trinh van",
    ]
    for dong in phai_bat:
        assert GIT_ORIGIN.search(dong), f"cong KHONG bat duoc: {dong!r}"


def test_the_gate_leaves_data_fields_and_plain_words_alone():
    """Bat nham thi nguoi sau se tat cong, nen phai chung minh no khong bat rac."""
    khong_duoc_bat = [
        '      "origin": null,',                                  # hermes/cron/jobs.*.json
        '        "origin": record.get("origin"), "summary": …',   # skill_lesson_filter
        '  "origin": "dre",',                                     # tests/golden/judge_verdicts.json
        "human) can find its origin later without digging through git blame.",
        "Always fetch the CDN original — a platform-compressed variant",
        "can fall back to a screenshot. This keeps the \"always fetch the original\" rule",
    ]
    for dong in khong_duoc_bat:
        assert not GIT_ORIGIN.search(dong), f"cong bat NHAM: {dong!r}"


def test_the_two_history_files_are_exempt_on_purpose_and_still_exist():
    """Mien tru phai tro toi tep CO THAT — tep bi doi ten/xoa thi mien tru tro
    thanh mot lo hong im lang."""
    for rel in HISTORY | RULE_FILE:
        assert (ROOT / rel).exists(), f"mien tru tro toi tep khong con: {rel}"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
