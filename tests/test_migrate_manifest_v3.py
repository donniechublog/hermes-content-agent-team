#!/usr/bin/env python3
"""migrate_manifest_v3.py (LOW-230): manifest values -> English codes, v2 -> v3.

Guards: dry-run writes nothing; a real run maps every field in the approved table
(both "báo khác" spellings merge), keeps unknown values with a warning, aborts on an
unmapped `uses` sentence before writing anything, backs originals up; re-run is a no-op."""
import json
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import state_paths as sp  # noqa: E402

V2_IMAGE = {"id": "A1", "source": "báo khác", "kind": "anh", "capture_kind": "tit",
            "uses": ["bìa (ảnh hero của chính bài gốc)", "ghép dọc với một ảnh ngang cùng tone"],
            "brand_match": {"company": "Nvidia", "kind": "co_phieu", "background_tone": "sáng"},
            "ranking": {"kind": "danh-sach", "rank": 3}}


def _manifest(**extra):
    m = {"version": 2, "draft_id": "d1", "images": [dict(V2_IMAGE),
                                                   {"id": "A2", "source": "bao khac", "kind": "chart",
                                                    "uses": ["thân (chart, dán full bề ngang nguyên vẹn)"]}],
         "ranking": {"kind": "bang-ghep"}, "image_order_by_story_type": ["tru_so", "logo", "chart_cong_bo"],
         "dropped": [{"stage": "download", "source": "khai_niem"}]}
    m.update(extra)
    return m


def _layout(tmp: Path, manifest=None) -> dict:
    st = tmp / "state"
    files = {"m": st / "blog" / sp.PREPARE_DIR / "d1" / sp.MANIFEST_FILE,
             "itachi": st / "blog" / sp.PREPARE_DIR / "itachi_1" / sp.MANIFEST_FILE,
             "golden": st / "golden" / "v0" / "samples.jsonl"}
    for p in files.values():
        p.parent.mkdir(parents=True, exist_ok=True)
    files["m"].write_text(json.dumps(manifest or _manifest(), ensure_ascii=False, indent=2), encoding="utf-8")
    files["itachi"].write_text(json.dumps({"khoa": "k", "slides": []}), encoding="utf-8")
    files["golden"].write_text(json.dumps({"id": "blog/d1/A1", "image": V2_IMAGE}, ensure_ascii=False) + "\n",
                               encoding="utf-8")
    return files


def _run(tmp: Path, *extra):
    return subprocess.run([sys.executable, str(ROOT / "migrate_manifest_v3.py"), "--state", str(tmp / "state"), *extra],
                          capture_output=True, text=True, cwd=ROOT)


def test_dry_run_writes_nothing():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        files = _layout(tmp)
        before = {k: p.read_bytes() for k, p in files.items()}
        r = _run(tmp, "--dry-run")
        assert r.returncode == 0 and "DRY RUN" in r.stdout, (r.stdout, r.stderr)
        assert {k: p.read_bytes() for k, p in files.items()} == before
        assert not list(tmp.glob("*.tar.gz"))


def test_real_run_maps_every_field_and_keeps_backup():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        files = _layout(tmp, _manifest(images=[dict(V2_IMAGE, source="nguon_la")]))
        before = {k: p.read_bytes() for k, p in files.items()}
        r = _run(tmp)
        assert r.returncode == 0, (r.stdout, r.stderr)
        assert "gia tri ngoai bang, giu nguyen: image.source = 'nguon_la'" in r.stdout, r.stdout
        m = json.loads(files["m"].read_text(encoding="utf-8"))
        assert m["version"] == 3
        a = m["images"][0]
        assert a["source"] == "nguon_la" and a["kind"] == "photo" and a["capture_kind"] == "headline", a
        assert a["uses"] == ["cover_article_hero", "stack_vertical"], a
        assert a["brand_match"] == {"company": "Nvidia", "kind": "stock", "background_tone": "light"}, a
        assert a["ranking"] == {"kind": "list", "rank": 3}, a
        assert m["ranking"] == {"kind": "table-stitched"}
        assert m["image_order_by_story_type"] == ["headquarters", "logo", "announcement_chart"]
        assert m["dropped"] == [{"stage": "download", "source": "concept"}]
        g = json.loads(files["golden"].read_text(encoding="utf-8"))
        assert g["image"]["source"] == "other_outlet" and g["image"]["uses"][0] == "cover_article_hero", g
        assert files["itachi"].read_bytes() == before["itachi"]
        (backup,) = tmp.glob("low230_values_backup_*.tar.gz")
        with tarfile.open(backup) as tar:
            assert tar.extractfile(f"state/blog/{sp.PREPARE_DIR}/d1/{sp.MANIFEST_FILE}").read() == before["m"]


def test_both_spellings_merge():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        files = _layout(tmp)
        assert _run(tmp).returncode == 0
        m = json.loads(files["m"].read_text(encoding="utf-8"))
        assert [a["source"] for a in m["images"]] == ["other_outlet", "other_outlet"], m["images"]
        assert m["images"][1]["uses"] == ["body_chart_full_width"]


def test_unknown_uses_aborts_before_writing():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        files = _layout(tmp, _manifest(images=[dict(V2_IMAGE, uses=["bìa (câu mới chưa có mã)"])]))
        before = {k: p.read_bytes() for k, p in files.items()}
        r = _run(tmp)
        assert r.returncode == 1 and "UnknownUse" in r.stderr, (r.stdout, r.stderr)
        assert {k: p.read_bytes() for k, p in files.items()} == before
        assert not list(tmp.glob("*.tar.gz"))


def test_second_run_is_noop():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        files = _layout(tmp)
        assert _run(tmp).returncode == 0
        after = {k: p.read_bytes() for k, p in files.items()}
        r = _run(tmp)
        assert r.returncode == 0 and "nothing to do" in r.stdout, r.stdout
        assert {k: p.read_bytes() for k, p in files.items()} == after


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
