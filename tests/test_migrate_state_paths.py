#!/usr/bin/env python3
"""migrate_state_paths.py (LOW-228): move state to the English layout.

Guards what the deploy relies on: dry-run touches nothing; a real run renames the
whole tree (nested round dirs, prefixed image files, locks, handoffs), rewrites
paths stored inside files without changing any other byte, backs the rewritten
originals up, leaves history alone; a second run is a no-op; a live engine pid or
a pre-existing prepare/ dir aborts before anything moves."""
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

DRAFT = "some-story-dre-donniechublog"


def _layout(tmp: Path) -> dict:
    st, dr = tmp / "state", tmp / "drafts"
    wd = st / "blog" / "chuan_bi" / DRAFT
    abs_wd = f"/home/u/content-team/state/blog/chuan_bi/{DRAFT}"
    files = {
        "manifest": wd / "xong.json",
        "manifest_bak": wd / "xong.json.v1.bak",
        "log": wd / "chuan_bi.log",
        "brief": wd / "brief.md",
        "material": wd / "tu_lieu.md",
        "sheet": wd / "bang_anh.png",
        "orig": wd / "goc" / "A1.png",
        "ready": wd / "san" / "A1.ngang.png",
        "rank": wd / "thuong_hieu" / "xh" / "xep_hang_arena-text.png",
        "board": wd / "thuong_hieu" / "bang" / "goc" / "A2.png",
        "extra": wd / "them_2" / "goc" / "A9.png",
        "capture": wd / "goc" / "chup_3_a.png",
        "spec": wd / "carousel.spec.json",
        "prev": wd / "da_dung.json",
        "gin": st / "blog" / "chuan_bi" / "gin_03" / "vung.json",
        "lock": st / "chuan_bi.0.lock",
        "handoff": dr / f"{DRAFT}.ban_giao.md",
        "img": dr / f"{DRAFT}.img.json",
        "history": st / "blog" / "nhat_ky" / "2026-09-13.md",
        "golden": st / "golden" / "v0" / "samples.jsonl",
    }
    for p in files.values():
        p.parent.mkdir(parents=True, exist_ok=True)
    manifest_text = json.dumps({"version": 2, "draft_id": DRAFT, "workdir": abs_wd,
                                "images": [{"id": "A1", "original_path": f"{abs_wd}/goc/A1.png",
                                            "ready_path": f"{abs_wd}/san/A1.ngang.png", "source": "khai_niem"}],
                                "ranking": {"file_path": f"{abs_wd}/thuong_hieu/xh/xep_hang_arena-text.png"}},
                               ensure_ascii=False, indent=2)
    files["manifest"].write_text(manifest_text, encoding="utf-8")
    files["manifest_bak"].write_text(manifest_text, encoding="utf-8")
    files["log"].write_text(f"[anh] ghi {abs_wd}/xong.json\n", encoding="utf-8")
    files["brief"].write_text(f"Nhìn tất cả ảnh trong MỘT tấm: {abs_wd}/bang_anh.png. Mở bang_anh.png khi cần.\n",
                              encoding="utf-8")
    files["material"].write_text("tư liệu", encoding="utf-8")
    for k in ("sheet", "orig", "ready", "rank", "board", "extra", "capture"):
        files[k].write_bytes(b"\x89PNG")
    files["spec"].write_text(json.dumps({"slides": [{"image": f"{abs_wd}/san/A1.ngang.png"}]}, indent=1), encoding="utf-8")
    files["prev"].write_text(json.dumps({"bia": "A1"}), encoding="utf-8")
    files["gin"].write_text("{}", encoding="utf-8")
    files["lock"].write_text("", encoding="utf-8")
    files["handoff"].write_text(f"Ảnh: {abs_wd}/san/A1.ngang.png\n", encoding="utf-8")
    files["img"].write_text(json.dumps({"image_role": "dre", "body": f"mở {abs_wd}/bang_anh.png rồi đọc tu_lieu.md"},
                                       ensure_ascii=False), encoding="utf-8")
    files["history"].write_text(f"sự cố ở {abs_wd}/xong.json\n", encoding="utf-8")
    files["golden"].write_text(json.dumps({"id": "x", "image": {"original_path": f"{abs_wd}/goc/A1.png"}}) + "\n",
                               encoding="utf-8")
    return files


def _run(tmp: Path, *extra) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(ROOT / "migrate_state_paths.py"), "--state", str(tmp / "state"),
                           "--drafts", str(tmp / "drafts"), *extra], capture_output=True, text=True, cwd=ROOT)


def _tree(tmp: Path) -> dict:
    return {str(p.relative_to(tmp)): (p.read_bytes() if p.is_file() else None) for p in sorted(tmp.rglob("*"))}


def test_dry_run_touches_nothing():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        _layout(tmp)
        before = _tree(tmp)
        r = _run(tmp, "--dry-run")
        assert r.returncode == 0, r.stderr
        assert "DRY RUN" in r.stdout and _tree(tmp) == before


def test_real_run_moves_tree_and_rewrites_stored_paths():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        files = _layout(tmp)
        before = {k: p.read_bytes() for k, p in files.items()}
        r = _run(tmp)
        assert r.returncode == 0, (r.stdout, r.stderr)
        st, dr = tmp / "state", tmp / "drafts"
        wd = st / "blog" / "prepare" / DRAFT
        new_abs = f"/home/u/content-team/state/blog/prepare/{DRAFT}"
        assert not (st / "blog" / "chuan_bi").exists()
        for rel in ("manifest.json", "manifest.json.v1.bak", "prepare.log", "brief.md", "material.md",
                    "contact_sheet.png", "original/A1.png", "ready/A1.landscape.png",
                    "brand_match/ranking/ranking_arena-text.png", "brand_match/board/original/A2.png",
                    "extra_2/original/A9.png", "original/capture_3_a.png", "carousel.spec.json",
                    "previous_submission.json"):
            assert (wd / rel).exists(), rel
        assert (st / "blog" / "prepare" / "gin_03" / "vung.json").exists()
        assert (st / "prepare.0.lock").exists() and not (st / "chuan_bi.0.lock").exists()
        m_text = (wd / "manifest.json").read_text(encoding="utf-8")
        assert m_text == before["manifest"].decode().replace(
            f"chuan_bi/{DRAFT}/goc/A1.png", f"prepare/{DRAFT}/original/A1.png").replace(
            f"chuan_bi/{DRAFT}/san/A1.ngang.png", f"prepare/{DRAFT}/ready/A1.landscape.png").replace(
            f"chuan_bi/{DRAFT}/thuong_hieu/xh/xep_hang_arena-text.png",
            f"prepare/{DRAFT}/brand_match/ranking/ranking_arena-text.png").replace(
            f"chuan_bi/{DRAFT}\"", f"prepare/{DRAFT}\""), m_text
        m = json.loads(m_text)
        assert m["images"][0]["source"] == "khai_niem" and m["workdir"] == new_abs
        assert json.loads((wd / "carousel.spec.json").read_text())["slides"][0]["image"] == f"{new_abs}/ready/A1.landscape.png"
        assert (wd / "brief.md").read_text(encoding="utf-8") == \
            f"Nhìn tất cả ảnh trong MỘT tấm: {new_abs}/contact_sheet.png. Mở contact_sheet.png khi cần.\n"
        assert (wd / "manifest.json.v1.bak").read_bytes() == before["manifest_bak"]
        assert (wd / "prepare.log").read_bytes() == before["log"]
        assert files["history"].read_bytes() == before["history"]
        assert (dr / f"{DRAFT}.handoff.md").read_text(encoding="utf-8") == f"Ảnh: {new_abs}/ready/A1.landscape.png\n"
        assert json.loads((dr / f"{DRAFT}.img.json").read_text(encoding="utf-8"))["body"] == \
            f"mở {new_abs}/contact_sheet.png rồi đọc material.md"
        g = json.loads(files["golden"].read_text().splitlines()[0])
        assert g["image"]["original_path"] == f"{new_abs}/original/A1.png"
        backups = list(tmp.glob("low228_state_backup_*.tar.gz"))
        assert len(backups) == 1
        with tarfile.open(backups[0]) as tar:
            names = tar.getnames()
        assert f"state/blog/chuan_bi/{DRAFT}/xong.json" in names and f"drafts/{DRAFT}.img.json" in names
        journal = list((st).glob("migrate_state_paths_*.journal.jsonl"))
        assert journal and any('"to"' in l for l in journal[0].read_text().splitlines())


def test_second_run_is_noop():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        _layout(tmp)
        assert _run(tmp).returncode == 0
        after = _tree(tmp)
        r = _run(tmp)
        assert r.returncode == 0 and "nothing to do" in r.stdout, r.stdout
        assert _tree(tmp) == after


def test_live_engine_or_existing_prepare_aborts_before_moving():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        _layout(tmp)
        (tmp / "state" / "blog" / "chuan_bi" / DRAFT / "dang_chay.pid").write_text(str(os.getpid()))
        before = _tree(tmp)
        r = _run(tmp)
        assert r.returncode == 1 and "still running" in r.stderr, r.stderr
        assert _tree(tmp) == before
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        _layout(tmp)
        (tmp / "state" / "blog" / "prepare").mkdir()
        before = _tree(tmp)
        r = _run(tmp)
        assert r.returncode == 1 and "already exists" in r.stderr, r.stderr
        assert _tree(tmp) == before


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
