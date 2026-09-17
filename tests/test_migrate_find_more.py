#!/usr/bin/env python3
"""migrate_find_more.py (LOW-237): find_more.json -> English keys.

Guards: dry-run writes nothing; real run renames luot/da_thu in every brand + the single-brand
layout, keeps values, backs up originals and writes a journal; the result reads back through
find_more_images.read_count_turn; an unknown shape or old+new side by side refuses the whole run
(nothing written); re-run is a no-op."""
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import state_paths as sp                                      # noqa: E402

OLD = {"luot": 2, "da_thu": ["TSMC fab Arizona", "https://x.example/a"]}
NEW = {"run_count": 2, "tried_queries": ["TSMC fab Arizona", "https://x.example/a"]}


def _find_more(state: Path, *parts) -> Path:
    return state.joinpath(*parts, sp.PREPARE_DIR, "d1", sp.FIND_MORE_FILE)


def _layout(tmp: Path, extra=None) -> dict:
    st = tmp / "state"
    files = {"dcgr": _find_more(st, "dcgr"), "blog": _find_more(st, "blog"), "single": _find_more(st),
             "done": st / "blog" / sp.PREPARE_DIR / "d2" / sp.FIND_MORE_FILE,
             "other": st / "blog" / sp.PREPARE_DIR / "d1" / sp.MANIFEST_FILE}
    data = {"dcgr": OLD, "blog": {"luot": 1, "da_thu": []}, "single": OLD, "done": NEW,
            "other": {"luot": 9}}
    data.update(extra or {})
    for k, p in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data[k], ensure_ascii=False), encoding="utf-8")
    return files


def _run(tmp: Path, *extra):
    return subprocess.run([sys.executable, str(ROOT / "migrate_find_more.py"), "--state", str(tmp / "state"), *extra],
                          capture_output=True, text=True, cwd=ROOT)


def _bytes(files: dict) -> dict:
    return {k: p.read_bytes() for k, p in files.items()}


def test_key_pairs_equal_approved_table():
    import migrate_find_more
    t = json.loads((ROOT / "docs" / "tu_dien_ten" / "image_search_keys_v2.json").read_text(encoding="utf-8"))
    assert migrate_find_more.table() == {k: v for k, v in t["find_more_json"].items() if not k.startswith("_")}


def test_dry_run_writes_nothing():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        before = _bytes(f)
        r = _run(tmp, "--dry-run")
        assert r.returncode == 0 and "DRY RUN" in r.stdout and "3 file(s)" in r.stdout, (r.stdout, r.stderr)
        assert _bytes(f) == before and not list(tmp.glob("*.tar.gz")) and not list(tmp.glob("*.jsonl"))


def test_real_run_renames_backs_up_and_journals():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        before = _bytes(f)
        r = _run(tmp)
        assert r.returncode == 0, (r.stdout, r.stderr)
        assert json.loads(f["dcgr"].read_text(encoding="utf-8")) == NEW
        assert json.loads(f["single"].read_text(encoding="utf-8")) == NEW
        assert json.loads(f["blog"].read_text(encoding="utf-8")) == {"run_count": 1, "tried_queries": []}
        assert f["done"].read_bytes() == before["done"], "already-new file must not be rewritten"
        assert f["other"].read_bytes() == before["other"], "only find_more.json is touched"
        (backup,) = tmp.glob("low237_find_more_backup_*.tar.gz")
        with tarfile.open(backup) as tar:
            assert sorted(tar.getnames()) == sorted(str(f[k].relative_to(tmp)) for k in ("dcgr", "blog", "single"))
            assert tar.extractfile(str(f["dcgr"].relative_to(tmp))).read() == before["dcgr"]
        (journal,) = tmp.glob("low237_find_more_*.journal.jsonl")
        rows = [json.loads(x) for x in journal.read_text(encoding="utf-8").splitlines()]
        assert {r_["file"] for r_ in rows} == {str(f[k]) for k in ("dcgr", "blog", "single")}, rows
        assert all(r_["from_keys"] == ["da_thu", "luot"] and r_["to_keys"] == ["run_count", "tried_queries"]
                   for r_ in rows), rows
        import find_more_images
        assert find_more_images.read_count_turn(f["dcgr"].parent) == NEW


def test_bad_shape_or_conflict_refuses_everything():
    for bad, word in (({"luot": 1, "run_count": 1}, "both"), ({"luot": 1, "ghi_chu": "x"}, "unknown keys"),
                      (["luot"], "not an object"), ({"luot": "2"}, "expected int")):
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            f = _layout(tmp, {"blog": bad})
            before = _bytes(f)
            r = _run(tmp)
            assert r.returncode == 1 and word in r.stderr and "nothing written" in r.stderr, (bad, r.stderr)
            assert _bytes(f) == before and not list(tmp.glob("*.tar.gz")), bad


def test_rerun_is_noop():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        assert _run(tmp).returncode == 0
        after = _bytes(f)
        r = _run(tmp)
        assert r.returncode == 0 and "nothing to do" in r.stdout, r.stdout
        assert _bytes(f) == after and len(list(tmp.glob("*.tar.gz"))) == 1


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
