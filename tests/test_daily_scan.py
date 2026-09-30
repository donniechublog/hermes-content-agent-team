#!/usr/bin/env python3
"""Script cron quet tin sang phai giao task cho PROFILE CO THAT (LOW-20).

Vi sao phai co test: sang 11/09/2026 Vera (dcgr) va Finn (blog) im ca sang.
Cutover LOW-14 doi `--vai` trong BODY nhung quen `--assignee`, task giao cho
`market`/`scout` — hai profile khong con ton tai. Kanban `create` nhan assignee
bat ky, dispatcher xep task do vao "nonspawnable" va CO Y khong bao "stuck",
cron van `ok`. Ba lop deu im, nen lop chan phai nam o day: vo mong chi duoc
truyen slug hien tai, va than script phai tu choi slug la va profile khong co.

Chay:  venv/bin/python tests/test_daily_scan.py
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import role  # noqa: E402

SCRIPTS = ROOT / "hermes" / "scripts"
THAN = SCRIPTS / "daily_scan.sh"
VO = ["finn_daily_scan.sh", "nova_daily_scan.sh", "vera_daily_scan.sh"]
BASH = shutil.which("bash")


def test_without_thin_transmit_slug_current():
    """Moi vo mong `exec daily_scan.sh <x>`: x la slug trong role.ROLE, khong phai slug cu."""
    for ten in VO:
        s = (SCRIPTS / ten).read_text(encoding="utf-8")
        m = re.search(r'daily_scan\.sh"?\s+(\S+)', s)
        assert m, f"{ten}: khong thay dong exec daily_scan.sh"
        x = m.group(1)
        assert x not in role.SLUG_OLD, f"{ten}: truyen slug CU '{x}' (-> {role.SLUG_OLD[x]})"
        assert x in role.ROLE, f"{ten}: '{x}' khong co trong role.ROLE"
        assert ten.startswith(x + "_"), f"{ten}: ten tep va slug lech ({x})"


def test_than_use_slug_make_assignee():
    """--assignee phai la chinh $VAI (slug profile), khong qua bien trung gian nao."""
    s = THAN.read_text(encoding="utf-8")
    assert re.search(r'--assignee\s+"\$VAI"', s), "daily_scan.sh: --assignee khong phai \"$VAI\""
    for cu in role.SLUG_OLD:
        assert not re.search(rf"^\s*{re.escape(cu)}\)", s, re.M), \
            f"daily_scan.sh: con nhanh case cho slug cu '{cu}'"


def _run(arg, home):
    return subprocess.run([BASH, str(THAN), arg], capture_output=True, text=True,
                          env={**os.environ, "HERMES_HOME": str(home), "HOME": str(home)})


def test_reject_slug_old_and_profile_missing():
    """Chay that bang bash: slug cu -> thoat 2; slug moi ma home khong co profile -> thoat 1."""
    if not BASH:
        print("  (bo qua: khong co bash)")
        return
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        (home / "profiles" / "vera").mkdir(parents=True)
        r = _run("market", home)
        assert r.returncode == 2, f"slug cu 'market' phai bi tu choi (ma 2), duoc {r.returncode}: {r.stderr}"
        r = _run("finn", home)
        assert r.returncode == 1 and "khong co profile" in r.stderr, \
            f"thieu profile finn phai thoat 1 + bao ro, duoc {r.returncode}: {r.stderr}"
        # vera co profile: phai qua cong, roi moi hong o cho goi hermes (khong co
        # trong home gia) — chung to cong khong chan nham profile co that.
        r = _run("vera", home)
        assert "khong co profile" not in r.stderr, f"vera co profile ma van bi chan: {r.stderr}"


def _run_with_fake_kanban(home: Path, created_at: float, title: str,
                          stdout_tail: str = "", stderr_tail: str = "", raw: str | None = None):
    """Chay daily_scan.sh finn voi `python` gia: `-m hermes_cli...` in JSON task
    dung san, con lai chuyen sang python that (script dung no de doc JSON).
    `stdout_tail`/`stderr_tail`: rac in SAU JSON (warning cua hermes); `raw` thay
    han JSON bang chuoi tuy y (vd JSON hong)."""
    (home / "profiles" / "finn").mkdir(parents=True, exist_ok=True)
    bin_dir = home / "hermes-agent" / "venv" / "bin"
    bin_dir.mkdir(parents=True, exist_ok=True)
    (home / "task.json").write_text(raw if raw is not None else json.dumps(
        {"id": "t_old", "title": title, "status": "done", "created_at": created_at}, indent=2),
        encoding="utf-8")
    (home / "tail_out").write_text(stdout_tail, encoding="utf-8")
    (home / "tail_err").write_text(stderr_tail, encoding="utf-8")
    fake = bin_dir / "python"
    real = Path(sys.executable).as_posix()
    fake.write_text(
        "#!/bin/bash\n"
        f'if [ "$1" = "-m" ]; then cat "{(home / "task.json").as_posix()}"; '
        f'cat "{(home / "tail_out").as_posix()}"; cat "{(home / "tail_err").as_posix()}" >&2; exit 0; fi\n'
        f'exec "{real}" "$@"\n', encoding="utf-8")
    fake.chmod(0o755)
    return _run("finn", home)


def test_old_task_same_vn_day_is_rejected():
    """LOW-353: luot thu hai cung ngay VN trung khoa -> kanban tra task CU co DUNG
    tieu de hom nay. Cong cu so tieu de nen cho qua (exit 0, khong tao task, sang
    22/09/2026 Finn/Nova/Vera khong quet). Cong moi so created_at -> thoat 1."""
    if not BASH:
        print("  (bo qua: khong co bash)")
        return
    today = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")
    title = f"Quet tin sang {today}"
    with tempfile.TemporaryDirectory() as d:
        r = _run_with_fake_kanban(Path(d), time.time() - 17 * 3600, title)
        assert r.returncode == 1 and "task CU" in r.stdout, \
            f"task cu cung tieu de phai bi bat (ma 1), duoc {r.returncode}: {r.stdout}{r.stderr}"
    with tempfile.TemporaryDirectory() as d:
        r = _run_with_fake_kanban(Path(d), time.time() - 2, title)
        assert r.returncode == 0, f"task vua tao phai qua cong, duoc {r.returncode}: {r.stdout}{r.stderr}"


def test_warning_after_json_does_not_fake_old_task():
    """B19: hermes in warning SAU dong JSON (stderr, hoac ca stdout) -> khong duoc lam
    json.loads hong roi bao "task CU" gia + exit 1 du task vua tao that."""
    if not BASH:
        print("  (bo qua: khong co bash)")
        return
    today = datetime.now(timezone(timedelta(hours=7))).strftime("%Y-%m-%d")
    title = f"Quet tin sang {today}"
    warn = "\nWARNING: hermes deprecation {x}\n"
    for kieu, k in (("stderr", {"stderr_tail": warn}), ("stdout", {"stdout_tail": warn})):
        with tempfile.TemporaryDirectory() as d:
            r = _run_with_fake_kanban(Path(d), time.time() - 2, title, **k)
            assert r.returncode == 0, \
                f"warning o {kieu} sau JSON lam hong cong (ma {r.returncode}): {r.stdout}{r.stderr}"
    # task CU van phai bi bat du co warning di kem
    with tempfile.TemporaryDirectory() as d:
        r = _run_with_fake_kanban(Path(d), time.time() - 17 * 3600, title, stderr_tail=warn)
        assert r.returncode == 1 and "task CU" in r.stdout, f"{r.returncode}: {r.stdout}{r.stderr}"


def test_json_unreadable_is_reported_as_such_not_old_task():
    """B19: co "id" nhung JSON hong -> bao "khong doc duoc JSON" (khong gia vo task CU)."""
    if not BASH:
        print("  (bo qua: khong co bash)")
        return
    with tempfile.TemporaryDirectory() as d:
        r = _run_with_fake_kanban(Path(d), 0, "t", raw='{"id": "t_x", "created_at": ')
        assert r.returncode == 1 and "khong doc duoc JSON" in r.stdout and "task CU" not in r.stdout, \
            f"{r.returncode}: {r.stdout}{r.stderr}"


def test_qinn_turn_matches_scan_prepare():
    """Cong thuc LUOT trong daily_scan.sh phai cung moc gio voi scan_prepare.turn."""
    import scan_prepare
    s = THAN.read_text(encoding="utf-8")
    m = re.search(r"10#\$GIO - (\d+) \+ 24", s)
    assert m and int(m.group(1)) == scan_prepare.FRAME_START, \
        f"daily_scan.sh moc {m and m.group(1)} != scan_prepare.FRAME_START {scan_prepare.FRAME_START}"
    assert scan_prepare.turn(6) == 0 and scan_prepare.turn(18) == 1


if __name__ == "__main__":
    hong = 0
    for ten, f in list(globals().items()):
        if ten.startswith("test_") and callable(f):
            try:
                f()
                print(f"  OK   {ten}")
            except AssertionError as e:
                hong += 1
                print(f"  HONG {ten}: {e}")
    sys.exit(1 if hong else 0)
