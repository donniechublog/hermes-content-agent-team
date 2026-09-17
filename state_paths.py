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
DRAFT_TRIAL_FILE = "draft_trial.txt"      # miles_submit --khong-push, LOW-242 (was draft_thu.txt); table submit_keys_v2.json
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

# image_brand workdir (brand_match/<key>/), LOW-237; table docs/tu_dien_ten/image_search_keys_v2.json
LOGO_ORIGINAL_FILE = "logo_original.png"   # logo downloaded from Commons (Wikidata P154)
LOGO_CARD_FILE = "logo_card.png"           # logo placed on the brand card
STOCK_IMAGE_PREFIX = "stock_"              # stock_<key>.png (Google Finance capture)


# ---- brand-level state (state/<brand>/…), LOW-231; table docs/tu_dien_ten/state_files_v2.json
ARTICLE_SOURCE_PREFIX = "article_source_"          # article_source_<draft_id>.json
USED_IMAGES_FILE = "used_images.jsonl"
USED_EDU_THEMES_FILE = "used_edu_themes.jsonl"
ARTICLE_REQUEST_COUNTS_FILE = "article_request_counts.json"
REPORTED_PROGRESS_FILE = "reported_progress.json"
REPORTED_STALLED_FILE = "reported_stalled.json"
TASK_RESULT_MESSAGES_FILE = "task_result_messages.json"
REDO_WAITING_FILE = "redo_waiting.json"
MOAT_REPUBLISH_QUEUE_FILE = "moat_republish_queue.json"
BUSINESS_SEEN_FILE = "business_seen.json"            # scan_business seen-store (Vera), LOW-240
X_SEEN_FILE = "x_seen.json"                          # scan_x seen-store (Qinn), LOW-240
MOAT_UNSENT_NOTICES_FILE = "moat_unsent_notices.json"  # moat_publish spool, LOW-240 (was moat_chua_bao.json)
BOSS_IDS_FILE = "boss_ids.json"                      # approve allowlist [user_id…], LOW-241 (was ong_chu.json)
REPORT_MESSAGE_ID_FILE = "report_message_id.{}.json"   # .format(role)
REQUIRED_FILE = "required_{}.json"                      # .format(role)
SCAN_DIR = "scan"                                       # state/<brand>/scan/<role>_<n>/
DOWNLOADS_DIR = "downloads"
JOURNAL_DIR = "journal"

# inside state/<brand>/scan/<run>/
SCAN_REPORT_FILE = "report.txt"
SCAN_LIST_FILE = "list.json"
SCAN_RESULT_FILE = "scan.json"
SCAN_NONE_FOUND_FILE = "none_found.txt"
SCAN_TRIAL_MANIFEST_FILE = "trial_manifest.json"

JOURNAL_NOTES_FILE = "notes.jsonl"                     # state/journal/notes.jsonl
ROUTER_CONNECTIONS_PREFIX = "connections_"             # state/9router/connections_<date>.jsonl
CRON_AUDIT_FILE = "cron_audit.json"                    # state/cron_audit.json (audit_cron, shared by brands), LOW-239

# Gin (image-text swap) artefacts in its prepare workdir
GIN_REGIONS_FILE = "regions.json"
GIN_REGIONS_OCR_FILE = "regions_ocr.json"
GIN_REGIONS_PREVIEW_FILE = "regions_preview.png"
GIN_CLEAN_BACKGROUND_FILE = "clean_background.png"
GIN_RESULT_PREFIX = "result_"                          # result_<n>.png


def article_source_file(state: Path, draft_id: str) -> Path:
    return Path(state) / f"{ARTICLE_SOURCE_PREFIX}{draft_id}.json"


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
