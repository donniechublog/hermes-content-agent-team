#!/usr/bin/env python3
"""migrate_model_board_keys.py (LOW-233): model-board stores -> English keys.

Guards: dry-run writes nothing; real run renames models_seen top keys + board keys
under rankings, model_audition per-model keys, required_nova ids/loai for renamed
boards, leaves other boards/models/values alone, backs up; conflict aborts; re-run no-op."""
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tests"))

SEEN = {"cap_nhat": "2026-09-13T22:01:55+00:00", "ids": ["a/b"], "aa_da_bao": {"GPT-6 Astra": "2026-09-03"},
        "xep_hang": {"text": {"claude-fable-5": 1}, "tri_tue": {"Claude Fable 5.1": 1},
                     "swe_da_ngon_ngu": {"Gemini 3 Flash": 1}}}
AUDITION = {"ds-v4-flash": {"dat": True, "ty_le_dau": 0.27, "tool": ["luu_caption"], "cache": True, "giay": 10.1,
                            "reason_tok": 356}}
REQUIRED = {"tri_tue|Claude Fable 5.1": {"ten": "Claude Fable 5.1", "loai": "tri_tue", "ghi_chu": "n", "link": "",
                                         "ngay": "2026-09-17"},
            "text|claude-fable-5": {"ten": "claude-fable-5", "loai": "text", "ghi_chu": "", "link": "", "ngay": "2026-09-17"}}


def _layout(tmp: Path, seen=SEEN) -> dict:
    st = tmp / "state"
    files = {"seen": st / "dcgr" / "models_seen.json", "aud": st / "model_audition.json",
             "req": st / "dcgr" / "required_nova.json", "other": st / "dcgr" / "required_finn.json"}
    for p in files.values():
        p.parent.mkdir(parents=True, exist_ok=True)
    files["seen"].write_text(json.dumps(seen, ensure_ascii=False), encoding="utf-8")
    files["aud"].write_text(json.dumps(AUDITION), encoding="utf-8")
    files["req"].write_text(json.dumps(REQUIRED, ensure_ascii=False), encoding="utf-8")
    files["other"].write_text(json.dumps({"x|y": {"ten": "y", "loai": "tri_tue"}}), encoding="utf-8")
    return files


def _run(tmp: Path, *extra):
    return subprocess.run([sys.executable, str(ROOT / "migrate_model_board_keys.py"), "--state", str(tmp / "state"), *extra],
                          capture_output=True, text=True, cwd=ROOT)


def test_dry_run_writes_nothing():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        before = {k: p.read_bytes() for k, p in f.items()}
        r = _run(tmp, "--dry-run")
        assert r.returncode == 0 and "DRY RUN" in r.stdout, (r.stdout, r.stderr)
        assert {k: p.read_bytes() for k, p in f.items()} == before and not list(tmp.glob("*.tar.gz"))


def test_real_run_renames_and_backs_up():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        before = {k: p.read_bytes() for k, p in f.items()}
        r = _run(tmp)
        assert r.returncode == 0, (r.stdout, r.stderr)
        seen = json.loads(f["seen"].read_text(encoding="utf-8"))
        assert seen == {"updated_at": SEEN["cap_nhat"], "ids": ["a/b"], "aa_reported": SEEN["aa_da_bao"],
                        "rankings": {"text": {"claude-fable-5": 1}, "intelligence": {"Claude Fable 5.1": 1},
                                     "swe_multilingual": {"Gemini 3 Flash": 1}}}, seen
        aud = json.loads(f["aud"].read_text())
        assert aud == {"ds-v4-flash": {"passed": True, "diacritic_ratio": 0.27, "tool": ["luu_caption"], "cache": True,
                                       "seconds": 10.1, "reason_tok": 356}}, aud
        req = json.loads(f["req"].read_text(encoding="utf-8"))
        assert set(req) == {"intelligence|Claude Fable 5.1", "text|claude-fable-5"}, req
        assert req["intelligence|Claude Fable 5.1"]["loai"] == "intelligence" and req["text|claude-fable-5"]["loai"] == "text"
        assert f["other"].read_bytes() == before["other"], "only required_nova holds model-board ids"
        (backup,) = tmp.glob("low233_model_keys_backup_*.tar.gz")
        with tarfile.open(backup) as tar:
            assert tar.extractfile("state/dcgr/models_seen.json").read() == before["seen"]


def test_conflict_aborts_and_rerun_is_noop():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp, dict(SEEN, rankings={}))
        before = {k: p.read_bytes() for k, p in f.items()}
        r = _run(tmp)
        assert r.returncode == 1 and "Conflict" in r.stderr, r.stderr
        assert {k: p.read_bytes() for k, p in f.items()} == before
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        assert _run(tmp).returncode == 0
        after = {k: p.read_bytes() for k, p in f.items()}
        r = _run(tmp)
        assert r.returncode == 0 and "nothing to do" in r.stdout, r.stdout
        assert {k: p.read_bytes() for k, p in f.items()} == after


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
