#!/usr/bin/env python3
"""migrate_state_files.py (LOW-231): state file/dir names -> English + leftovers archived.

Guards: dry-run touches nothing; a real run archives leftovers (tar) and removes them,
rewrites stored paths without touching other bytes, renames files/dirs, leaves history
text and kept files alone; a live engine pid aborts; a second run is a no-op."""
import json
import os
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import state_paths as sp  # noqa: E402

D = "some-story-dre-donniechublog"
ABS = "/home/u/content-team/state"


def _write(p: Path, text: str = "x") -> Path:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(text, encoding="utf-8")
    return p


def _layout(tmp: Path) -> dict:
    st, dr = tmp / "state", tmp / "drafts"
    b = st / "blog"
    wd = b / sp.PREPARE_DIR / D
    gin = b / sp.PREPARE_DIR / "gin_338"
    f = {
        "manifest": _write(wd / sp.MANIFEST_FILE, json.dumps(
            {"version": 3, "draft_id": D, "images": [], "source_path": f"{ABS}/blog/nguon_{D}.json"}, indent=2)),
        "stray_py": _write(wd / "chk.py"),
        "stray_old_spec": _write(wd / "spec.truoc_low215.json", "{}"),
        "source": _write(b / f"nguon_{D}.json", "{}"),
        "used": _write(b / "anh_da_dung.jsonl", ""),
        "redo": _write(b / "lam_lai_cho.json", "{}"),
        "required": _write(b / "bat_buoc_finn.json", "[]"),
        "report_mid": _write(b / "bao_cao_mid.nova.json", "{}"),
        "orphan": _write(b / "da_bao_chan.json", "{}"),
        "gin_tmp": _write(b / "338_nen_sach.png"),
        "scan_ds": _write(b / "quet" / "finn_1" / "ds.json", "[]"),
        "scan_brief": _write(b / "quet" / "finn_1" / "brief.md", f"Đường dẫn: {ABS}/blog/quet/finn_1/picks.json\n"),
        "journal_md": _write(b / "nhat_ky" / "2026-09-16.md", f"sự cố ở {ABS}/blog/quet/finn_1/ds.json\n"),
        "download": _write(b / "tai_ve" / "Dc1" / "1.jpg"),
        "gin_manifest": _write(gin / sp.MANIFEST_FILE, json.dumps(
            {"khoa": "k", "slides": [{"anh": f"{ABS}/blog/tai_ve/Dc1/1.jpg", "vung": f"{ABS}/blog/prepare/gin_338/vung_ocr.json",
                                      "nen_sach": f"{ABS}/blog/prepare/gin_338/nen_sach.png"}]})),
        "gin_ocr": _write(gin / "vung_ocr.json", "{}"),
        "gin_bg": _write(gin / "nen_sach.png"),
        "gin_result": _write(gin / "ket_qua_07.png"),
        "candidates": _write(b / "nova_candidates_2026-09-16.json", json.dumps(
            {"items": [{"source_file": f"{ABS}/blog/nguon_{D}.json", "title": "t"}]})),
        "root_legacy": _write(st / "finn_candidates_2026-08-20.json", "{}"),
        "root_journal": _write(st / "nhat_ky" / "ghi_chu.jsonl", "{}\n"),
        "root_topics": _write(st / "topics.blog.json", "{}"),
        "root_bak": _write(st / "topics.blog.json.bak-truoc-low14-20260910", "{}"),
        "router_conn": _write(st / "9router" / "ket_noi_2026-09-05.jsonl", ""),
        "router_journal": _write(st / "9router" / "nhat_ky" / "9router_2026-09-16.md"),
        "golden": _write(st / "golden" / "v0" / "samples.jsonl", ""),
        "draft_json": _write(dr / f"{D}.json", json.dumps({"source_path": f"{ABS}/blog/nguon_{D}.json"})),
    }
    return f


def _run(tmp: Path, *extra):
    return subprocess.run([sys.executable, str(ROOT / "migrate_state_files.py"), "--state", str(tmp / "state"),
                           "--drafts", str(tmp / "drafts"), *extra], capture_output=True, text=True, cwd=ROOT)


def _tree(tmp: Path) -> dict:
    return {str(p.relative_to(tmp)): (p.read_bytes() if p.is_file() else None)
            for p in sorted(tmp.rglob("*")) if "low231_" not in p.name}


def test_dry_run_touches_nothing():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        _layout(tmp)
        before = _tree(tmp)
        r = _run(tmp, "--dry-run")
        assert r.returncode == 0 and "DRY RUN" in r.stdout, (r.stdout, r.stderr)
        assert _tree(tmp) == before and not list(tmp.glob("low231_*"))


def test_real_run_archives_rewrites_and_renames():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        before = {k: p.read_bytes() for k, p in f.items()}
        r = _run(tmp)
        assert r.returncode == 0, (r.stdout, r.stderr)
        st, b = tmp / "state", tmp / "state" / "blog"
        wd = b / sp.PREPARE_DIR / D
        gin = b / sp.PREPARE_DIR / "gin_338"
        for k in ("stray_py", "stray_old_spec", "orphan", "gin_tmp", "root_legacy", "root_journal", "root_bak"):
            assert not f[k].exists(), k
        (arch,) = tmp.glob("low231_leftovers_*.tar.gz")
        with tarfile.open(arch) as tar:
            names = set(tar.getnames())
        assert "state/finn_candidates_2026-08-20.json" in names and f"state/blog/prepare/{D}/chk.py" in names, names
        assert "state/nhat_ky/ghi_chu.jsonl" in names and "state/blog/da_bao_chan.json" in names, names
        new_src = f"{ABS}/blog/{sp.ARTICLE_SOURCE_PREFIX}{D}.json"
        m_text = (wd / sp.MANIFEST_FILE).read_text(encoding="utf-8")
        assert m_text == before["manifest"].decode().replace(f"/blog/nguon_{D}.json", f"/blog/article_source_{D}.json"), m_text
        assert json.loads((tmp / "drafts" / f"{D}.json").read_text())["source_path"] == new_src
        assert json.loads((b / "nova_candidates_2026-09-16.json").read_text())["items"][0]["source_file"] == new_src
        for rel in (f"article_source_{D}.json", "used_images.jsonl", "redo_waiting.json", "required_finn.json",
                    "report_message_id.nova.json", "scan/finn_1/list.json", "scan/finn_1/brief.md",
                    "journal/2026-09-16.md", "downloads/Dc1/1.jpg"):
            assert (b / rel).exists(), rel
        assert (b / "scan" / "finn_1" / "brief.md").read_text(encoding="utf-8") == \
            f"Đường dẫn: {ABS}/blog/scan/finn_1/picks.json\n"
        assert (b / "journal" / "2026-09-16.md").read_bytes() == before["journal_md"], "history text must not change"
        for rel in ("regions_ocr.json", "clean_background.png", "result_07.png"):
            assert (gin / rel).exists(), rel
        g = json.loads((gin / sp.MANIFEST_FILE).read_text())["slides"][0]
        assert g == {"anh": f"{ABS}/blog/downloads/Dc1/1.jpg", "vung": f"{ABS}/blog/prepare/gin_338/regions_ocr.json",
                     "nen_sach": f"{ABS}/blog/prepare/gin_338/clean_background.png"}, g
        assert (st / "9router" / "connections_2026-09-05.jsonl").exists()
        assert (st / "9router" / "journal" / "9router_2026-09-16.md").exists()
        assert f["root_topics"].read_bytes() == before["root_topics"] and f["golden"].exists()
        (rw,) = tmp.glob("low231_rewrites_backup_*.tar.gz")
        with tarfile.open(rw) as tar:
            assert tar.extractfile(f"state/blog/prepare/{D}/{sp.MANIFEST_FILE}").read() == before["manifest"]
        assert list(st.glob("migrate_state_files_*.journal.jsonl"))


def test_second_run_is_noop():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        _layout(tmp)
        assert _run(tmp).returncode == 0
        after = _tree(tmp)
        r = _run(tmp)
        assert r.returncode == 0 and "nothing to do" in r.stdout, r.stdout
        assert _tree(tmp) == after


def test_live_engine_aborts():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        _layout(tmp)
        _write(tmp / "state" / "blog" / sp.PREPARE_DIR / D / sp.RUNNING_PID_FILE, str(os.getpid()))
        before = _tree(tmp)
        r = _run(tmp)
        assert r.returncode == 1 and "still running" in r.stderr, r.stderr
        assert _tree(tmp) == before


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
