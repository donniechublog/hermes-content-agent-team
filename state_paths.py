#!/usr/bin/env python3
"""Every file/dir name under `state/<brand>/prepare/<draft_id>/` — ONE place (LOW-228).

Before LOW-228 these were Vietnamese literals scattered over ~40 modules
(`wd / "goc"`, `"xong.json"`, `f"chuan_bi.{i}.lock"`…). Code builds paths only
through the names below; the old → new table lives in
docs/tu_dien_ten/state_paths_v2.json (on-disk data migrated once at LOW-228 deploy;
the one-shot script was removed in LOW-229). Imports nothing heavy so any module can use it.
"""
from pathlib import Path

PREPARE_DIR = "prepare"                 # state/<brand>/prepare/<draft_id>/
LOCK_FILE = "prepare.{}.lock"           # state/prepare.<i>.lock (flock slots)

MANIFEST_FILE = "manifest.json"
PREPARE_LOG = "prepare.log"
MATERIAL_FILE = "material.md"
CONTACT_SHEET_FILE = "contact_sheet.png"
RUNNING_PID_FILE = "running.pid"
CRASH_COUNT_FILE = "crash_count.json"
FIND_MORE_FILE = "find_more.json"
PREVIOUS_SUBMISSION_FILE = "previous_submission.json"
SUBMIT_COUNT_FILE = "submit_count.json"
HANDOFF_SUFFIX = ".handoff.md"          # drafts/<draft_id>.handoff.md (or in the workdir with --khong-gui)

ORIGINAL_DIR = "original"               # downloaded originals (image key `original_path`)
READY_DIR = "ready"                     # processed images (image key `ready_path`)
EXTRA_DIR = "extra"                     # fallback round; find_more_images uses extra_<n>
CONCEPT_DIR = "concept"
BRAND_MATCH_DIR = "brand_match"
ENTITY_DIR = "entity"
CAPTURE_SOURCE_DIR = "capture_source"
RANKING_DIR = "ranking"
BOARD_DIR = "board"

RANKING_IMAGE_PREFIX = "ranking_"       # ranking_<board>.png
CAPTURE_IMAGE_PREFIX = "capture_"       # capture_<n>_<k>.png
LANDSCAPE_SUFFIX = ".landscape.png"     # <id>.landscape.png


LEGACY_PREPARE_DIR = "chuan_bi"


class NotMigrated(RuntimeError):
    pass


def prepare_root(state: Path) -> Path:
    """Refuses a state dir still holding the pre-LOW-228 layout: silently creating an
    empty `prepare/` next to 192 old drafts would make every draft look unprepared."""
    if (Path(state) / LEGACY_PREPARE_DIR).is_dir():
        raise NotMigrated(f"{Path(state) / LEGACY_PREPARE_DIR} van con — chua migrate LOW-228: "
                          "migration mot lan da go o LOW-229, lay lai tu git (e6663b3)")
    return Path(state) / PREPARE_DIR


def workdir(state: Path, draft_id: str) -> Path:
    return prepare_root(state) / draft_id


def extra_dir(wd: Path, n: int) -> Path:
    return Path(wd) / f"{EXTRA_DIR}_{n}"


def handoff_file(folder: Path, draft_id: str) -> Path:
    return Path(folder) / f"{draft_id}{HANDOFF_SUFFIX}"
