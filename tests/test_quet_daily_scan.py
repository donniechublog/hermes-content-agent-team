#!/usr/bin/env python3
"""Script cron quet tin sang phai giao task cho PROFILE CO THAT (LOW-20).

Vi sao phai co test: sang 11/09/2026 Vera (dcgr) va Finn (blog) im ca sang.
Cutover LOW-14 doi `--vai` trong BODY nhung quen `--assignee`, task giao cho
`market`/`scout` — hai profile khong con ton tai. Kanban `create` nhan assignee
bat ky, dispatcher xep task do vao "nonspawnable" va CO Y khong bao "stuck",
cron van `ok`. Ba lop deu im, nen lop chan phai nam o day: vo mong chi duoc
truyen slug hien tai, va than script phai tu choi slug la va profile khong co.

Chay:  venv/bin/python tests/test_quet_daily_scan.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import vai  # noqa: E402

SCRIPTS = ROOT / "hermes" / "scripts"
THAN = SCRIPTS / "quet_daily_scan.sh"
VO = ["finn_daily_scan.sh", "nova_daily_scan.sh", "vera_daily_scan.sh"]
BASH = shutil.which("bash")


def test_vo_mong_truyen_slug_hien_tai():
    """Moi vo mong `exec quet_daily_scan.sh <x>`: x la slug trong vai.VAI, khong phai slug cu."""
    for ten in VO:
        s = (SCRIPTS / ten).read_text(encoding="utf-8")
        m = re.search(r'quet_daily_scan\.sh"?\s+(\S+)', s)
        assert m, f"{ten}: khong thay dong exec quet_daily_scan.sh"
        x = m.group(1)
        assert x not in vai.SLUG_CU, f"{ten}: truyen slug CU '{x}' (-> {vai.SLUG_CU[x]})"
        assert x in vai.VAI, f"{ten}: '{x}' khong co trong vai.VAI"
        assert ten.startswith(x + "_"), f"{ten}: ten tep va slug lech ({x})"


def test_than_dung_slug_lam_assignee():
    """--assignee phai la chinh $VAI (slug profile), khong qua bien trung gian nao."""
    s = THAN.read_text(encoding="utf-8")
    assert re.search(r'--assignee\s+"\$VAI"', s), "quet_daily_scan.sh: --assignee khong phai \"$VAI\""
    for cu in vai.SLUG_CU:
        assert not re.search(rf"^\s*{re.escape(cu)}\)", s, re.M), \
            f"quet_daily_scan.sh: con nhanh case cho slug cu '{cu}'"


def _chay(arg, home):
    return subprocess.run([BASH, str(THAN), arg], capture_output=True, text=True,
                          env={**os.environ, "HERMES_HOME": str(home), "HOME": str(home)})


def test_tu_choi_slug_cu_va_profile_thieu():
    """Chay that bang bash: slug cu -> thoat 2; slug moi ma home khong co profile -> thoat 1."""
    if not BASH:
        print("  (bo qua: khong co bash)")
        return
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        (home / "profiles" / "vera").mkdir(parents=True)
        r = _chay("market", home)
        assert r.returncode == 2, f"slug cu 'market' phai bi tu choi (ma 2), duoc {r.returncode}: {r.stderr}"
        r = _chay("finn", home)
        assert r.returncode == 1 and "khong co profile" in r.stderr, \
            f"thieu profile finn phai thoat 1 + bao ro, duoc {r.returncode}: {r.stderr}"
        # vera co profile: phai qua cong, roi moi hong o cho goi hermes (khong co
        # trong home gia) — chung to cong khong chan nham profile co that.
        r = _chay("vera", home)
        assert "khong co profile" not in r.stderr, f"vera co profile ma van bi chan: {r.stderr}"


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
