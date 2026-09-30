#!/usr/bin/env python3
"""moat_publish_watch.sh tra id job tu jobs.json, khong go cung (B21).

Vi sao phai co test: script don output .md cu cua CHINH job nay. Id do do hermes
sinh luc tao job nen moi HERMES_HOME co the khac. Go cung `a4a246946091` thi home
co id khac se khong don duoc gi (ro), con thu muc trung id o home khac lai bi don
nham. Chay that bang bash voi HOME/HERMES_HOME gia.

Chay:  venv/bin/python tests/test_moat_publish_watch_job_lookup.py
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "hermes" / "scripts" / "moat_publish_watch.sh"
BASH = shutil.which("bash")


def _cu(p: Path):
    p.write_text("x", encoding="utf-8")
    t = time.time() - 10 * 86400
    os.utime(p, (t, t))


def test_clean_output_theo_id_tra_tu_jobs_json():
    if not BASH:
        print("  (bo qua: khong co bash)")
        return
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        h = home / ".hermes-x"
        (h / "cron").mkdir(parents=True)
        (h / "cron" / "jobs.json").write_text(json.dumps({"jobs": [
            {"id": "aaaa11112222", "name": "publish-due"},
            {"id": "bbbb33334444", "name": "moat-publish-watch"}]}, indent=2), encoding="utf-8")
        cua_toi = h / "cron" / "output" / "bbbb33334444"
        cua_khac = h / "cron" / "output" / "a4a246946091"     # id cu, cung dat cung, KHONG phai job nay
        for d2 in (cua_toi, cua_khac):
            d2.mkdir(parents=True)
            _cu(d2 / "old.md")
        ct = home / "content-team" / "venv" / "bin"
        ct.mkdir(parents=True)
        (ct / "python").symlink_to(sys.executable)
        (home / "content-team" / "moat_publish.py").write_text("", encoding="utf-8")
        r = subprocess.run([BASH, str(SCRIPT)], capture_output=True, text=True,
                           env={**os.environ, "HOME": str(home), "HERMES_HOME": str(h)})
        assert r.returncode == 0, f"{r.returncode}: {r.stdout}{r.stderr}"
        assert not (cua_toi / "old.md").exists(), "khong don output cua job tra tu jobs.json"
        assert (cua_khac / "old.md").exists(), "don nham thu muc cua id khac (id go cung)"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
