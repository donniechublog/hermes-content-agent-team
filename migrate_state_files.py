#!/usr/bin/env python3
"""State file/dir names -> English (LOW-231). One-shot, services stopped.

Order: (1) leftovers (pre-brand-split files at state/ root, orphan/debug files, *.bak-truoc-*)
go into one tar.gz and are removed from state; (2) paths stored inside data files are
rewritten by text substitution (manifest `source_path`, drafts/*.json, candidates, Gin
manifests, scan briefs); (3) files/dirs are renamed. History text (journal *.md, logs,
telegram_sent) is not rewritten. Table: docs/tu_dien_ten/state_files_v2.json.

A second tar.gz holds the original bytes of every rewritten file; renames go to a journal.
Refuses to run while an engine pid is alive. Re-running is a no-op.

    venv/bin/python migrate_state_files.py --dry-run
    venv/bin/python migrate_state_files.py
"""
import argparse
import json
import os
import re
import shutil
import sys
import tarfile
import time
from pathlib import Path

import env_load
import state_paths as sp

BRANDS_SKIP = {"golden", "skill_lessons", "9router", "nhat_ky", "telegram_sent", "telegram_incoming", "journal"}

ROOT_LEFTOVER_GLOBS = ["nguon_*.json", "finn_candidates_*", "nova_candidates_*", "vera_candidates_*", "bob_job*.txt",
                       "da_bao_chan.json", "business_seen.json", "donniechu_posted.json", "offset.txt",
                       "model_health.json", "approve.log", "emoji_deck.json", "emoji_deck.lock",
                       "edu_theme_da_dung.jsonl", "nhat_ky", "telegram_sent", "telegram_incoming"]
BRAND_LEFTOVER_GLOBS = ["da_bao_chan.json", "*_mask_debug.png", "*_nen_sach.png", "_kite_probe.py"]
DRAFT_LEFTOVER_GLOBS = ["*.py", "*.truoc_low*.json", "chuan_bi.low*.log", "bao_cao.txt", "draft_thu.txt",
                        "tu_lieu_bo_sung.txt", "thieu_anh.md", "chu_de"]

BRAND_FILES = {"anh_da_dung.jsonl": sp.USED_IMAGES_FILE, "edu_theme_da_dung.jsonl": sp.USED_EDU_THEMES_FILE,
               "dat_bai.json": sp.ARTICLE_REQUEST_COUNTS_FILE, "da_bao_tien_do.json": sp.REPORTED_PROGRESS_FILE,
               "da_bao_treo.json": sp.REPORTED_STALLED_FILE, "tin_ket_qua_task.json": sp.TASK_RESULT_MESSAGES_FILE,
               "lam_lai_cho.json": sp.REDO_WAITING_FILE, "moat_day_lai.json": sp.MOAT_REPUBLISH_QUEUE_FILE,
               "quet": sp.SCAN_DIR, "tai_ve": sp.DOWNLOADS_DIR, "nhat_ky": sp.JOURNAL_DIR}
BRAND_PATTERNS = [(re.compile(r"^nguon_(.+)\.json$"), sp.ARTICLE_SOURCE_PREFIX + r"\1.json"),
                  (re.compile(r"^bao_cao_mid\.(.+)\.json$"), sp.REPORT_MESSAGE_ID_FILE.format(r"\1")),
                  (re.compile(r"^bat_buoc_(.+)\.json$"), sp.REQUIRED_FILE.format(r"\1"))]
SCAN_FILES = {"baocao.txt": sp.SCAN_REPORT_FILE, "ds.json": sp.SCAN_LIST_FILE, "quet.json": sp.SCAN_RESULT_FILE,
              "khong_co.txt": sp.SCAN_NONE_FOUND_FILE, "thu_manifest.json": sp.SCAN_TRIAL_MANIFEST_FILE}
JOURNAL_FILES = {"ghi_chu.jsonl": sp.JOURNAL_NOTES_FILE}
GIN_FILES = {"vung.json": sp.GIN_REGIONS_FILE, "vung_ocr.json": sp.GIN_REGIONS_OCR_FILE,
             "vung_preview.png": sp.GIN_REGIONS_PREVIEW_FILE, "nen_sach.png": sp.GIN_CLEAN_BACKGROUND_FILE}
GIN_PATTERNS = [(re.compile(r"^ket_qua_(.+)\.png$"), sp.GIN_RESULT_PREFIX + r"\1.png")]


def _rename_name(name: str, exact: dict, patterns=()) -> str:
    if name in exact:
        return exact[name]
    for rx, rep in patterns:
        if rx.match(name):
            return rx.sub(rep, name)
    return name


# ---- text rewrite of stored paths (only the path segments this ticket renames)
_TEXT_RULES = [
    (re.compile(r"(state/(?:[a-z0-9_-]+/)?)nguon_([^/\s\"'`]+?)\.json"), r"\1" + sp.ARTICLE_SOURCE_PREFIX + r"\2.json"),
    (re.compile(r"(state/[a-z0-9_-]+/)quet/"), r"\1" + sp.SCAN_DIR + "/"),
    (re.compile(r"(state/[a-z0-9_-]+/)tai_ve/"), r"\1" + sp.DOWNLOADS_DIR + "/"),
    (re.compile(r"(/prepare/[^/\s\"'`]+/)vung_ocr\.json"), r"\1" + sp.GIN_REGIONS_OCR_FILE),
    (re.compile(r"(/prepare/[^/\s\"'`]+/)vung_preview\.png"), r"\1" + sp.GIN_REGIONS_PREVIEW_FILE),
    (re.compile(r"(/prepare/[^/\s\"'`]+/)vung\.json"), r"\1" + sp.GIN_REGIONS_FILE),
    (re.compile(r"(/prepare/[^/\s\"'`]+/)nen_sach\.png"), r"\1" + sp.GIN_CLEAN_BACKGROUND_FILE),
    (re.compile(r"(/prepare/[^/\s\"'`]+/)ket_qua_([^/\s\"'`]+?)\.png"), r"\1" + sp.GIN_RESULT_PREFIX + r"\2.png"),
]


def rewrite_text(s: str) -> str:
    for rx, rep in _TEXT_RULES:
        s = rx.sub(rep, s)
    return s


def _pid_alive(p: Path) -> bool:
    try:
        os.kill(int(p.read_text().strip()), 0)
        return True
    except (OSError, ValueError):
        return False


def _brands(state: Path) -> list:
    return sorted(p for p in state.iterdir() if p.is_dir() and p.name not in BRANDS_SKIP
                  and ((p / sp.PREPARE_DIR).is_dir() or any(p.glob("nguon_*.json")) or (p / "quet").is_dir()))


def plan(state: Path, drafts: Path) -> dict:
    leftovers, rewrites, renames, errors = [], [], [], []
    for pid in state.glob(f"*/{sp.PREPARE_DIR}/*/{sp.RUNNING_PID_FILE}"):
        if _pid_alive(pid):
            errors.append(f"{pid}: engine still running")

    def take(base: Path, globs: list):
        for g in globs:
            leftovers.extend(p for p in sorted(base.glob(g)) if p not in leftovers)

    take(state, ROOT_LEFTOVER_GLOBS)
    brands = _brands(state)
    for b in brands:
        take(b, BRAND_LEFTOVER_GLOBS)
        for d in sorted((b / sp.PREPARE_DIR).glob("*/")) if (b / sp.PREPARE_DIR).is_dir() else []:
            take(d, DRAFT_LEFTOVER_GLOBS)
    for p in sorted(state.rglob("*.bak-truoc-*")):
        if p not in leftovers and not any(parent in leftovers for parent in p.parents):
            leftovers.append(p)
    gone = set(leftovers)

    def alive(p: Path) -> bool:
        return p not in gone and not any(parent in gone for parent in p.parents)

    # content rewrites
    candidates = []
    for b in brands:
        candidates += list((b / sp.PREPARE_DIR).glob(f"*/{sp.MANIFEST_FILE}")) if (b / sp.PREPARE_DIR).is_dir() else []
        candidates += list((b / sp.PREPARE_DIR).glob("*/vung_ocr.json")) if (b / sp.PREPARE_DIR).is_dir() else []
        candidates += list(b.glob("*_candidates_*.json"))
        candidates += list(b.glob("quet/*/brief.md"))
    candidates += list(drafts.glob("*.json")) if drafts.is_dir() else []
    for p in sorted(set(candidates)):
        if alive(p):
            rewrites.append(p)

    # renames (deepest first inside each renamed tree)
    for b in brands:
        prep = b / sp.PREPARE_DIR
        if prep.is_dir():
            for d in sorted(prep.iterdir()):
                if d.is_dir():
                    for f in sorted(d.iterdir()):
                        new = _rename_name(f.name, GIN_FILES, GIN_PATTERNS)
                        if new != f.name and alive(f):
                            renames.append((f, d / new))
        quet = b / "quet"
        if quet.is_dir():
            for run in sorted(quet.iterdir()):
                if run.is_dir():
                    for f in sorted(run.iterdir()):
                        new = _rename_name(f.name, SCAN_FILES)
                        if new != f.name:
                            renames.append((f, run / new))
        nk = b / "nhat_ky"
        if nk.is_dir():
            for f in sorted(nk.iterdir()):
                new = _rename_name(f.name, JOURNAL_FILES)
                if new != f.name:
                    renames.append((f, nk / new))
        for f in sorted(b.iterdir()):
            new = _rename_name(f.name, BRAND_FILES, BRAND_PATTERNS)
            if new != f.name and alive(f):
                renames.append((f, b / new))
    router = state / "9router"
    if router.is_dir():
        for f in sorted(router.iterdir()):
            if f.name.startswith("ket_noi_"):
                renames.append((f, router / (sp.ROUTER_CONNECTIONS_PREFIX + f.name[len("ket_noi_"):])))
        if (router / "nhat_ky").is_dir():
            renames.append((router / "nhat_ky", router / sp.JOURNAL_DIR))
    for src, dst in renames:
        if dst.exists():
            errors.append(f"{src} -> {dst.name}: target exists")
    return {"leftovers": leftovers, "rewrites": rewrites, "renames": renames, "errors": errors}


def main() -> int:
    ap = argparse.ArgumentParser(description="State file/dir names -> English (LOW-231)")
    ap.add_argument("--state", default=str(env_load.ROOT / "state"))
    ap.add_argument("--drafts", default=str(env_load.ROOT / "drafts"))
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    state, drafts = Path(a.state), Path(a.drafts)
    pl = plan(state, drafts)

    content = []
    for p in pl["rewrites"]:
        old = p.read_text(encoding="utf-8")
        new = rewrite_text(old)
        if new != old:
            if p.suffix == ".json":
                try:
                    json.loads(new)
                except ValueError as e:
                    pl["errors"].append(f"{p}: rewrite breaks JSON: {e}")
                    continue
            content.append((p, new))
    print(f"leftovers to archive: {len(pl['leftovers'])} | content rewrites: {len(content)} | renames: {len(pl['renames'])}")
    for p in pl["leftovers"][:8]:
        print(f"  archive {p.relative_to(state.parent)}")
    for s, d in pl["renames"][:6]:
        print(f"  rename {s.relative_to(state.parent)} -> {d.name}")
    for e in pl["errors"]:
        print(f"[LOI] {e}", file=sys.stderr)
    if pl["errors"]:
        return 1
    if not (pl["leftovers"] or content or pl["renames"]):
        print("nothing to do (already migrated)")
        return 0
    if a.dry_run:
        print("DRY RUN — nothing written")
        return 0

    stamp = time.strftime("%Y%m%d-%H%M%S")
    if pl["leftovers"]:
        arch = state.parent / f"low231_leftovers_{stamp}.tar.gz"
        with tarfile.open(arch, "w:gz") as tar:
            for p in pl["leftovers"]:
                tar.add(p, arcname=str(p.relative_to(state.parent)))
        for p in pl["leftovers"]:
            shutil.rmtree(p) if p.is_dir() and not p.is_symlink() else p.unlink()
        print(f"leftovers archived: {arch}")
    if content:
        backup = state.parent / f"low231_rewrites_backup_{stamp}.tar.gz"
        with tarfile.open(backup, "w:gz") as tar:
            for p, _ in content:
                tar.add(p, arcname=str(p.relative_to(state.parent)))
        for p, new in content:
            tmp = p.with_name(p.name + f".tmp{os.getpid()}")
            tmp.write_text(new, encoding="utf-8")
            os.replace(tmp, p)
        print(f"rewritten originals: {backup}")
    if pl["renames"]:
        journal = state / f"migrate_state_files_{stamp}.journal.jsonl"
        with journal.open("w", encoding="utf-8") as fh:
            for src, dst in pl["renames"]:
                os.rename(src, dst)
                fh.write(json.dumps({"from": str(src), "to": str(dst)}, ensure_ascii=False) + "\n")
        print(f"rename journal: {journal}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
