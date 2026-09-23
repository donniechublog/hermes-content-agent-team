#!/usr/bin/env python3
"""state_paths.py (LOW-228): tên English cho mọi tệp/thư mục dưới state/<brand>/prepare/<draft_id>/.

Giữ ba điều:
  1. `prepare_root` TỪ CHỐI state còn thư mục `chuan_bi/` cũ (NotMigrated) — lặng lẽ
     tạo `prepare/` rỗng cạnh 192 draft cũ thì mọi draft trông như chưa chuẩn bị.
  2. Mọi hằng trong state_paths khớp đúng tên MỚI trong bảng đã duyệt
     docs/tu_dien_ten/state_paths_v2.json — code và bảng migrate không được lệch.
  3. Quét tĩnh (ast) mã production: không còn tên CŨ nằm ở chỗ dựng đường dẫn
     (toán hạng `/`, `open(...)`, `Path(...)`, `.glob(...)`…), và không còn chuỗi
     mang dạng tên tệp cũ (`chuan_bi.<n>.lock`, `xep_hang_<b>.png`, `chup_<n>_<k>.png`,
     `<id>.ngang.png`, `<id>.ban_giao.md`, `them_<n>`). Cùng từ tiếng Việt đó ở chỗ
     KHÔNG phải đường dẫn vẫn hợp lệ: `a.get("source") == "khai_niem"` là giá trị
     nguồn ảnh, không phải thư mục.

LOW-231 mở rộng (2) và (3) cho tệp/thư mục CẤP STATE (`state/<brand>/…`, quét, Gin,
nhật ký, 9router) theo bảng docs/tu_dien_ten/state_files_v2.json: hằng phải khớp
bảng, mỗi dòng bảng phải có hằng, và tên cũ (`nguon_<id>.json`, `anh_da_dung.jsonl`,
`quet/`, `tai_ve/`, `vung_ocr.json`…) không được nằm ở chỗ dựng đường dẫn. Thư mục
`nhat_ky/` Ở GỐC REPO (nhật ký sự cố) không phải state — không tệp .py nào trong
phạm vi quét dựng đường dẫn tới nó, nên không cần ngoại lệ.

Ngoài phạm vi quét: shim LOW-50 (`*chuan_bi*.py`, gói `chuan_bi/`), chính bảng đổi
tên (`state_path_migration.py`, `migrate_state_paths.py`, `migrate_state_files.py`),
`docs/`, `tests/`.

Chạy:  venv/bin/python tests/test_state_paths.py
"""
import ast
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import state_paths                                            # noqa: E402

TABLE = json.loads((ROOT / "docs" / "tu_dien_ten" / "state_paths_v2.json").read_text(encoding="utf-8"))
TABLE_231 = json.loads((ROOT / "docs" / "tu_dien_ten" / "state_files_v2.json").read_text(encoding="utf-8"))
TABLE_237 = json.loads((ROOT / "docs" / "tu_dien_ten" / "image_search_keys_v2.json").read_text(encoding="utf-8"))["workdir_files"]
TABLE_240 = json.loads((ROOT / "docs" / "tu_dien_ten" / "scan_keys_v2.json").read_text(encoding="utf-8"))
TABLE_242 = json.loads((ROOT / "docs" / "tu_dien_ten" / "submit_keys_v2.json").read_text(encoding="utf-8"))
# LOW-242: chi dong tep workdir (khoa khong co chu thich "(… tmp)" — tep tam cua bob_submit nam trong mkdtemp)
FILES_242 = {cu: moi for cu, moi in TABLE_242["files"].items() if " " not in cu}
TABLE_241 = json.loads((ROOT / "docs" / "tu_dien_ten" / "approve_keys_v2.json").read_text(encoding="utf-8"))
FILES_246 = {cu: moi for cu, moi in json.loads((ROOT / "docs" / "tu_dien_ten" / "ada_keys_v2.json")
                                               .read_text(encoding="utf-8"))["files"].items() if not cu.startswith("_")}
SECTIONS_231 = ("brand_files", "brand_dirs", "scan_files", "journal_files", "router_9", "gin_files")


# ------------------------------------------------------------ 1. prepare_root
def test_prepare_root_refuses_unmigrated_state():
    with tempfile.TemporaryDirectory() as t:
        state = Path(t)
        (state / "chuan_bi" / "some-draft").mkdir(parents=True)
        try:
            state_paths.prepare_root(state)
        except state_paths.NotMigrated as e:
            assert "chuan_bi" in str(e), e
        else:
            raise AssertionError("state con chuan_bi/ ma prepare_root khong nem NotMigrated")
        try:
            state_paths.workdir(state, "some-draft")
        except state_paths.NotMigrated:
            pass
        else:
            raise AssertionError("workdir phai di qua prepare_root va cung tu choi")
        assert not (state / "prepare").exists(), "khong duoc tao prepare/ khi tu choi"


def test_prepare_root_returns_prepare_when_migrated():
    with tempfile.TemporaryDirectory() as t:
        state = Path(t)
        assert state_paths.prepare_root(state) == state / "prepare"
        (state / "prepare").mkdir()
        assert state_paths.prepare_root(state) == state / "prepare"
        assert state_paths.workdir(state, "d1") == state / "prepare" / "d1"
        # tep (khong phai thu muc) ten chuan_bi khong phai layout cu
        (state / "chuan_bi").write_text("x")
        assert state_paths.prepare_root(state) == state / "prepare"


def test_not_migrated_is_runtime_error():
    assert issubclass(state_paths.NotMigrated, RuntimeError)


def test_helpers_build_new_names():
    wd = Path("/s/prepare/d1")
    assert state_paths.extra_dir(wd, 2) == wd / "extra_2"
    assert state_paths.handoff_file(Path("/drafts"), "d1") == Path("/drafts/d1.handoff.md")


# ------------------------------------------------------- 2. hang khop bang duyet
def test_constants_match_approved_table():
    t = TABLE
    df, dirs, pats = t["draft_files"], t["dirs"], t["file_patterns"]
    pairs = {
        "PREPARE_DIR": t["root"]["chuan_bi"],
        "LOCK_FILE": t["lock"]["chuan_bi.{n}.lock"].replace("{n}", "{}"),
        "MANIFEST_FILE": df["xong.json"],
        "PREPARE_LOG": df["chuan_bi.log"],
        "MATERIAL_FILE": df["tu_lieu.md"],
        "CONTACT_SHEET_FILE": df["bang_anh.png"],
        "RUNNING_PID_FILE": df["dang_chay.pid"],
        "CRASH_COUNT_FILE": df["so_lan_chet.json"],
        "FIND_MORE_FILE": df["tim_them.json"],
        "PREVIOUS_SUBMISSION_FILE": df["da_dung.json"],
        "SUBMIT_COUNT_FILE": df["nop_lan.json"],
        "ORIGINAL_DIR": dirs["goc"],
        "READY_DIR": dirs["san"],
        "EXTRA_DIR": dirs["them"],
        "CONCEPT_DIR": dirs["khai_niem"],
        "BRAND_MATCH_DIR": dirs["thuong_hieu"],
        "ENTITY_DIR": dirs["thuc_the"],
        "CAPTURE_SOURCE_DIR": dirs["chup_nguon"],
        "RANKING_DIR": dirs["xh"],
        "BOARD_DIR": dirs["bang"],
        "RANKING_IMAGE_PREFIX": pats["xep_hang_{board}.png"].split("{")[0],
        "CAPTURE_IMAGE_PREFIX": pats["chup_{n}_{k}.png"].split("{")[0],
        "LANDSCAPE_SUFFIX": pats["{id}.ngang.png"].split("}", 1)[1],
        # LOW-273: ten MOI, khong co ten Viet cu -> bang ghi trung chinh no
        "SUBJECT_SUFFIX": pats["{id}.subject.png"].split("}", 1)[1],
        "LOGO_SUFFIX": pats["{id}.logo.png"].split("}", 1)[1],
        "HANDOFF_SUFFIX": pats["{draft_id}.ban_giao.md"].split("}", 1)[1],
        "LEGACY_PREPARE_DIR": "chuan_bi",
    }
    sai = {k: (getattr(state_paths, k, None), v) for k, v in pairs.items() if getattr(state_paths, k, None) != v}
    assert not sai, f"hang lech bang duyet (hang, bang): {sai}"
    # them_{n} -> extra_{n} di qua extra_dir
    assert dirs["them_{n}"] == "extra_{n}" and state_paths.extra_dir(Path("w"), 3).name == "extra_3"
    # moi hang chuoi IN HOA deu da duoc doi chieu — hang moi phai vao bang truoc
    # (hang LOW-231 doi chieu voi state_files_v2.json o test ben duoi, cung do chat)
    hang = {k for k, v in vars(state_paths).items() if k.isupper() and isinstance(v, str)}
    thieu = sorted(hang - set(pairs) - {ten for _, ten in _rows_231().values()}
                   - {ten for _, ten in _rows_237().values()}
                   - {ten for _, ten in _rows_240().values()} - {ten for _, ten in _rows_375().values()} - set(_rows_239())
                   - set(_rows_publish_schedule())
                   - set(_rows_scan_overflow())
                   - set(_rows_dispatch_shadow())
                   - set(_rows_auto_handoff())
                   - set(_rows_model_versions())
                   - set(_rows_repick())
                   - {ten for _, ten in _rows_242().values()}
                   - {ten for _, ten in _rows_241().values()}
                   - {ten for _, ten in _rows_246().values()})
    assert not thieu, f"hang chua doi chieu voi state_paths_v2.json / state_files_v2.json: {thieu}"


def test_every_draft_file_and_dir_in_table_has_a_constant():
    """Moi dong cua bang (tru ban sao luu v1.bak cua LOW-227) co mot hang tuong ung."""
    gia_tri = {v for k, v in vars(state_paths).items() if k.isupper() and isinstance(v, str)}
    moi = [v for k, v in TABLE["draft_files"].items() if not k.endswith(".bak")]
    moi += [v for k, v in TABLE["dirs"].items() if "{" not in k]
    thieu = sorted(set(moi) - gia_tri)
    assert not thieu, f"ten moi trong bang ma state_paths khong co hang: {thieu}"


def _rows_231() -> dict:
    """{(muc, ten CU trong bang): (ten MOI dung lai tu hang, ten hang)} — cho giu cho
    `{id}`/`{role}`/`{date}`/`{n}` giu nguyen chu nhu bang de so bang ==."""
    sp = state_paths
    return {
        ("brand_files", "nguon_{id}.json"): (f"{sp.ARTICLE_SOURCE_PREFIX}{{id}}.json", "ARTICLE_SOURCE_PREFIX"),
        ("brand_files", "anh_da_dung.jsonl"): (sp.USED_IMAGES_FILE, "USED_IMAGES_FILE"),
        ("brand_files", "edu_theme_da_dung.jsonl"): (sp.USED_EDU_THEMES_FILE, "USED_EDU_THEMES_FILE"),
        ("brand_files", "dat_bai.json"): (sp.ARTICLE_REQUEST_COUNTS_FILE, "ARTICLE_REQUEST_COUNTS_FILE"),
        ("brand_files", "da_bao_tien_do.json"): (sp.REPORTED_PROGRESS_FILE, "REPORTED_PROGRESS_FILE"),
        ("brand_files", "da_bao_treo.json"): (sp.REPORTED_STALLED_FILE, "REPORTED_STALLED_FILE"),
        ("brand_files", "tin_ket_qua_task.json"): (sp.TASK_RESULT_MESSAGES_FILE, "TASK_RESULT_MESSAGES_FILE"),
        ("brand_files", "lam_lai_cho.json"): (sp.REDO_WAITING_FILE, "REDO_WAITING_FILE"),
        ("brand_files", "moat_day_lai.json"): (sp.MOAT_REPUBLISH_QUEUE_FILE, "MOAT_REPUBLISH_QUEUE_FILE"),
        ("brand_files", "bao_cao_mid.{role}.json"): (sp.REPORT_MESSAGE_ID_FILE.format("{role}"), "REPORT_MESSAGE_ID_FILE"),
        ("brand_files", "bat_buoc_{role}.json"): (sp.REQUIRED_FILE.format("{role}"), "REQUIRED_FILE"),
        ("brand_dirs", "quet"): (sp.SCAN_DIR, "SCAN_DIR"),
        ("brand_dirs", "tai_ve"): (sp.DOWNLOADS_DIR, "DOWNLOADS_DIR"),
        ("brand_dirs", "nhat_ky"): (sp.JOURNAL_DIR, "JOURNAL_DIR"),
        ("scan_files", "baocao.txt"): (sp.SCAN_REPORT_FILE, "SCAN_REPORT_FILE"),
        ("scan_files", "ds.json"): (sp.SCAN_LIST_FILE, "SCAN_LIST_FILE"),
        ("scan_files", "quet.json"): (sp.SCAN_RESULT_FILE, "SCAN_RESULT_FILE"),
        ("scan_files", "khong_co.txt"): (sp.SCAN_NONE_FOUND_FILE, "SCAN_NONE_FOUND_FILE"),
        ("scan_files", "thu_manifest.json"): (sp.SCAN_TRIAL_MANIFEST_FILE, "SCAN_TRIAL_MANIFEST_FILE"),
        ("journal_files", "ghi_chu.jsonl"): (sp.JOURNAL_NOTES_FILE, "JOURNAL_NOTES_FILE"),
        ("router_9", "ket_noi_{date}.jsonl"): (f"{sp.ROUTER_CONNECTIONS_PREFIX}{{date}}.jsonl", "ROUTER_CONNECTIONS_PREFIX"),
        ("router_9", "nhat_ky"): (sp.JOURNAL_DIR, "JOURNAL_DIR"),
        ("gin_files", "vung.json"): (sp.GIN_REGIONS_FILE, "GIN_REGIONS_FILE"),
        ("gin_files", "vung_ocr.json"): (sp.GIN_REGIONS_OCR_FILE, "GIN_REGIONS_OCR_FILE"),
        ("gin_files", "vung_preview.png"): (sp.GIN_REGIONS_PREVIEW_FILE, "GIN_REGIONS_PREVIEW_FILE"),
        ("gin_files", "nen_sach.png"): (sp.GIN_CLEAN_BACKGROUND_FILE, "GIN_CLEAN_BACKGROUND_FILE"),
        ("gin_files", "ket_qua_{n}.png"): (f"{sp.GIN_RESULT_PREFIX}{{n}}.png", "GIN_RESULT_PREFIX"),
        ("gin_files", "{id}_nen_sach.png"): (f"{{id}}_{sp.GIN_CLEAN_BACKGROUND_FILE}", "GIN_CLEAN_BACKGROUND_FILE"),
    }


def test_low231_constants_match_approved_table():
    rows = _rows_231()
    sai = {f"{muc}/{cu}": (moi, TABLE_231[muc].get(cu)) for (muc, cu), (moi, _) in rows.items()
           if TABLE_231[muc].get(cu) != moi}
    assert not sai, f"hang LOW-231 lech state_files_v2.json (dung tu hang, bang): {sai}"
    # moi dong cua bang deu co hang doi chieu — dong moi trong bang ma quen hang thi hong
    bang = {(muc, cu) for muc in SECTIONS_231 for cu in TABLE_231[muc]}
    thieu = sorted(bang - set(rows))
    assert not thieu, f"dong state_files_v2.json chua co hang trong state_paths: {thieu}"
    thua = sorted(set(rows) - bang)
    assert not thua, f"doi chieu dong khong co trong bang: {thua}"
    ten_hang = {ten for _, ten in rows.values()}
    khong_co = sorted(t for t in ten_hang if not isinstance(getattr(state_paths, t, None), str))
    assert not khong_co, f"hang khong ton tai trong state_paths: {khong_co}"


def _rows_237() -> dict:
    """LOW-237: tep trong workdir image_brand (brand_match/<key>/). {ten CU: (ten MOI, ten hang)}."""
    sp = state_paths
    return {
        "logo_goc.png": (sp.LOGO_ORIGINAL_FILE, "LOGO_ORIGINAL_FILE"),
        "the_logo.png": (sp.LOGO_CARD_FILE, "LOGO_CARD_FILE"),
        "co_phieu_<key>.png": (f"{sp.STOCK_IMAGE_PREFIX}<key>.png", "STOCK_IMAGE_PREFIX"),
    }


def test_low237_constants_match_approved_table():
    rows = _rows_237()
    sai = {cu: (moi, TABLE_237.get(cu)) for cu, (moi, _) in rows.items() if TABLE_237.get(cu) != moi}
    assert not sai, f"hang LOW-237 lech image_search_keys_v2.json (dung tu hang, bang): {sai}"
    assert set(rows) == set(TABLE_237), (sorted(rows), sorted(TABLE_237))


def _rows_240() -> dict:
    """LOW-240: seen-store cua scan (ten khong doi, nay la hang) + spool moat (doi ten).
    {ten CU: (ten MOI, ten hang)}."""
    sp = state_paths
    return {
        "business_seen.json": (sp.BUSINESS_SEEN_FILE, "BUSINESS_SEEN_FILE"),
        "x_seen.json": (sp.X_SEEN_FILE, "X_SEEN_FILE"),
        "moat_chua_bao.json": (sp.MOAT_UNSENT_NOTICES_FILE, "MOAT_UNSENT_NOTICES_FILE"),
    }


def test_low240_constants_match_approved_table():
    rows = _rows_240()
    assert set(TABLE_240["files"]) <= set(rows), (sorted(TABLE_240["files"]), sorted(rows))
    for cu, (moi, ten) in rows.items():
        if cu in TABLE_240["files"]:
            assert TABLE_240["files"][cu] == moi, (cu, moi, TABLE_240["files"][cu])
        else:          # ten giu nguyen, bang chi dat hang cho no
            assert cu == moi, (cu, moi)
            muc = "business_seen" if ten == "BUSINESS_SEEN_FILE" else "x_seen"
            assert f"state_paths.{ten}" in TABLE_240[muc]["_where"] and cu in TABLE_240[muc]["_where"], muc


def _rows_375() -> dict:
    """LOW-375: hai seen-store nua, CUNG hinh dang voi business_seen/x_seen.
    Ca hai ten deu giu nguyen chu dang co tren dia (`models_seen.json` truoc
    day go thang trong scan_models.py; `finn_seen.json` la kho moi, dat ten
    theo dung khuon). {ten CU: (ten MOI, ten hang)}."""
    sp = state_paths
    return {
        "models_seen.json": (sp.MODELS_SEEN_FILE, "MODELS_SEEN_FILE"),
        "finn_seen.json": (sp.FINN_SEEN_FILE, "FINN_SEEN_FILE"),
    }


def test_low375_constants_match_approved_table():
    muc_bang = {"MODELS_SEEN_FILE": "models_seen", "FINN_SEEN_FILE": "finn_seen"}
    for cu, (moi, ten) in _rows_375().items():
        assert cu == moi, (cu, moi)          # ten giu nguyen, bang chi dat cho
        muc = muc_bang[ten]
        assert muc in TABLE_240, f"{muc} chua co trong scan_keys_v2.json"
        noi = TABLE_240[muc]["_where"]
        assert f"state_paths.{ten}" in noi and cu in noi, (muc, noi)


def test_low375_seen_store_fields_match_the_table():
    """Ba truong cua Nova nam CUNG tep voi ids/rankings/aa_reported — bang phai
    ghi ro ten chung, neu khong lan sau co nguoi ghi de ca tep lan nua."""
    import scan_models
    bang = TABLE_240["models_seen"]
    assert bang["khoa_hf"] == scan_models.HF_SEEN_FIELD
    assert bang["khoa_tin_hang"] == scan_models.STORY_SEEN_FIELD
    assert bang["khoa_github"] == scan_models.GITHUB_SEEN_FIELD
    import scan_seen
    assert TABLE_240["finn_seen"]["khoa"] == scan_seen.SEEN_FIELD


def _rows_242() -> dict:
    """LOW-242: tep thu cua miles_submit --khong-push trong workdir. {ten CU: (ten MOI, ten hang)}."""
    return {"draft_thu.txt": (state_paths.DRAFT_TRIAL_FILE, "DRAFT_TRIAL_FILE")}


def test_low242_constants_match_approved_table():
    rows = _rows_242()
    assert set(rows) == set(FILES_242), (sorted(rows), sorted(FILES_242))
    for cu, (moi, _ten) in rows.items():
        assert FILES_242[cu] == moi, (cu, moi, FILES_242[cu])


def _rows_241() -> dict:
    """LOW-241: allowlist cua bot duyet. {ten CU: (ten MOI, ten hang)}."""
    return {"ong_chu.json": (state_paths.BOSS_IDS_FILE, "BOSS_IDS_FILE")}


def test_low241_constants_match_approved_table():
    rows = _rows_241()
    assert set(rows) == set(TABLE_241["files"]), (sorted(rows), sorted(TABLE_241["files"]))
    sai = {cu: (moi, TABLE_241["files"][cu]) for cu, (moi, _) in rows.items() if TABLE_241["files"][cu] != moi}
    assert not sai, f"hang LOW-241 lech approve_keys_v2.json (dung tu hang, bang): {sai}"
    import approve_base
    assert approve_base.BOSS_IDS.name == state_paths.BOSS_IDS_FILE


def _rows_246() -> dict:
    """LOW-246: tep cua Ada (workdir ada_<date>/ + journal/). {ten CU: (ten MOI dung lai tu hang, ten hang)}."""
    sp = state_paths
    return {
        "manifest.json": (sp.ADA_METRICS_FILE, "ADA_METRICS_FILE"),
        "bao_cao.txt": (sp.ADA_REPORT_FILE, "ADA_REPORT_FILE"),
        "phan_tich_{date}.md": (f"{sp.ANALYSIS_REPORT_PREFIX}{{date}}.md", "ANALYSIS_REPORT_PREFIX"),
    }


def test_low246_constants_match_approved_table():
    rows = _rows_246()
    assert set(rows) == set(FILES_246), (sorted(rows), sorted(FILES_246))
    sai = {cu: (moi, FILES_246[cu]) for cu, (moi, _) in rows.items() if FILES_246[cu] != moi}
    assert not sai, f"hang LOW-246 lech ada_keys_v2.json (dung tu hang, bang): {sai}"


def _rows_239() -> dict:
    """LOW-239: hang cho tep da English san (ten giu nguyen, chi thoi viet chuoi rai rac)."""
    return {"CRON_AUDIT_FILE": ("cron_audit.json", "state/cron_audit.json")}


def _rows_publish_schedule() -> dict:
    """Hang cua hang doi xep lich dang bai (18/09/2026) — sinh ra da English
    san, khong co ten cu de doi chieu, nen chi kiem ten + phai co mat trong
    `_kept` cua bang."""
    return {"PUBLISH_SCHEDULE_FILE": ("publish_schedule.json",
                                      "state/<brand>/publish_schedule.json"),
            "PUBLISH_SLOT_LOCK": ("publish_slot.lock",
                                  "state/<brand>/publish_slot.lock"),
            "PUBLISH_DUE_LOCK": ("publish_due.lock",
                                 "state/<brand>/publish_due.lock")}


def _rows_scan_overflow() -> dict:
    """LOW-283 (19/09/2026): tep cua phan tin du Vera chuyen sang blog — sinh ra
    da English san, cung kieu `_rows_publish_schedule`."""
    return {"SCAN_OVERFLOW_REPORT_FILE": ("overflow_report.txt",
                                          "state/<brand>/scan/<run>/overflow_report.txt"),
            "SCAN_TRIAL_OVERFLOW_MANIFEST_FILE": ("trial_overflow_manifest.json",
                                                  "state/<brand>/scan/<run>/trial_overflow_manifest.json")}


def test_scan_overflow_constants_are_declared():
    for hang, (ten, kept) in _rows_scan_overflow().items():
        assert getattr(state_paths, hang) == ten, (hang, getattr(state_paths, hang))
        assert kept in TABLE_231["_kept"], f"{kept} khong co trong _kept cua state_files_v2.json"


def _rows_dispatch_shadow() -> dict:
    """LOW-349 (21/09/2026): log goi y chay bong tu chon tin — sinh ra da English
    san, cung kieu `_rows_publish_schedule`."""
    return {"DISPATCH_SHADOW_FILE": ("dispatch_shadow.jsonl", "state/<brand>/dispatch_shadow.jsonl")}


def _rows_auto_handoff() -> dict:
    """LOW-382 (23/09/2026): co cua cong tu duyet ban nhap (auto_handoff.py) — sinh
    ra da English san, cung kieu `_rows_publish_schedule`."""
    return {"AUTO_HANDOFF_FILE": ("auto_handoff.json", "state/<brand>/auto_handoff.json")}


def _rows_model_versions() -> dict:
    """LOW-363 (22/09/2026): cache lich su phien ban model tu Wikipedia — sinh ra da
    English san, cung kieu `_rows_publish_schedule`."""
    return {"MODEL_VERSIONS_FILE": ("model_versions.json", "state/<brand>/model_versions.json")}


def _rows_repick() -> dict:
    """LOW-362 (22/09/2026): lich su bao cao researcher (reply bao cao cu) + cau hoi lam lai
    tin da giao — sinh ra da English san, cung kieu `_rows_publish_schedule`."""
    return {"REPORT_HISTORY_FILE": ("report_history.{}.jsonl", "state/<brand>/report_history.<role>.jsonl"),
            "REPICK_PENDING_FILE": ("repick_pending.json", "state/<brand>/repick_pending.json")}


def test_repick_constants_are_declared():
    for const, (name, kept) in _rows_repick().items():
        assert getattr(state_paths, const) == name, (const, getattr(state_paths, const))
        assert kept in TABLE_231["_kept"], f"{kept} khong co trong _kept cua state_files_v2.json"


def test_model_versions_constants_are_declared():
    for const, (name, kept) in _rows_model_versions().items():
        assert getattr(state_paths, const) == name, (const, getattr(state_paths, const))
        assert kept in TABLE_231["_kept"], f"{kept} khong co trong _kept cua state_files_v2.json"


def test_dispatch_shadow_constants_are_declared():
    for const, (name, kept) in _rows_dispatch_shadow().items():
        assert getattr(state_paths, const) == name, (const, getattr(state_paths, const))
        assert kept in TABLE_231["_kept"], f"{kept} khong co trong _kept cua state_files_v2.json"


def test_publish_schedule_constants_are_declared():
    for hang, (ten, kept) in _rows_publish_schedule().items():
        assert getattr(state_paths, hang) == ten, (hang, getattr(state_paths, hang))
        assert kept in TABLE_231["_kept"], f"{kept} khong co trong _kept cua state_files_v2.json"


def test_low239_constants_keep_existing_names():
    for hang, (ten, kept) in _rows_239().items():
        assert getattr(state_paths, hang) == ten, (hang, getattr(state_paths, hang))
        assert kept in TABLE_231["_kept"], f"{kept} khong con trong _kept cua state_files_v2.json"


def test_article_source_file_uses_table_name():
    moi = TABLE_231["brand_files"]["nguon_{id}.json"].replace("{id}", "d1")
    assert state_paths.article_source_file(Path("/s/blog"), "d1") == Path("/s/blog") / moi


# ------------------------------------------------------------ 3. quet production
OLD_NAMES = {"chuan_bi", "xong.json", "goc", "san", "bang_anh.png", "tu_lieu.md", "dang_chay.pid",
             "so_lan_chet.json", "tim_them.json", "da_dung.json", "nop_lan.json", "xh"}
# Phan con lai cua bang (thu muc vong tim anh, chuan_bi.log) cung la ten cu o cho duong dan.
OLD_NAMES |= set(TABLE["root"]) | {k for k in TABLE["draft_files"]} | {k for k in TABLE["dirs"] if "{" not in k}

# Dang ten tep cu — sai o BAT KY chuoi nao (khong tinh docstring). \0 = cho {bieu thuc} cua f-string.
OLD_FILE_SHAPES = [
    re.compile(r"^chuan_bi\."),                     # chuan_bi.{i}.lock, chuan_bi.log
    re.compile(r"^xep_hang_.*\.png$"),              # xep_hang_<board>.png
    re.compile(r"^chup_.*\.png$"),                  # chup_<n>_<k>.png
    re.compile(r"\.ngang\.png"),                    # <id>.ngang.png
    re.compile(r"\.ban_giao\.md"),                  # <draft_id>.ban_giao.md
    re.compile(r"^them_(\d+|\x00)$"),               # them_<n>
]

# LOW-231: ten CU cap state. Ten phang (khong co cho giu {…}) sai o cho duong dan, ca
# thu muc (quet/tai_ve/nhat_ky cua state — `nhat_ky/` goc repo khong .py nao dung).
_PLAIN_231 = {cu for muc in SECTIONS_231 for cu in TABLE_231[muc] if "{" not in cu}
OLD_NAMES |= _PLAIN_231
# LOW-237: tep workdir image_brand
OLD_NAMES |= {cu for cu in TABLE_237 if "<" not in cu}
# LOW-240: spool moat
OLD_NAMES |= set(TABLE_240["files"])
# LOW-242: tep thu cua miles_submit
OLD_NAMES |= set(FILES_242)
# LOW-241: allowlist bot duyet
OLD_NAMES |= set(TABLE_241["files"])
# LOW-246: bao cao Ada (manifest.json van la ten hop le cua engine, khong cam)
OLD_NAMES |= {"bao_cao.txt"}
OLD_FILE_SHAPES += [
    re.compile(r"(^|/)(logo_goc|the_logo)\.png$"),        # logo_goc.png, the_logo.png
    re.compile(r"(^|/)co_phieu_.*\.png$"),                  # co_phieu_<key>.png
]
OLD_FILE_SHAPES += [
    re.compile(r"(^|/)(" + "|".join(re.escape(cu) for cu in sorted(_PLAIN_231) if "." in cu) + r")$"),
    re.compile(r"(^|/)nguon_.*\.json$"),            # nguon_<id>.json, nguon_*.json
    re.compile(r"(^|/)bao_cao_mid\."),              # bao_cao_mid.<role>.json
    re.compile(r"(^|/)bat_buoc_.*\.json$"),         # bat_buoc_<role>.json
    re.compile(r"(^|/)ket_noi_.*\.jsonl$"),         # 9router/ket_noi_<date>.jsonl
    re.compile(r"(^|/)ket_qua_.*\.png$"),           # Gin ket_qua_<n>.png
    re.compile(r"_nen_sach\.png$"),                 # <id>_nen_sach.png
    re.compile(r"_da_dung\.jsonl$"),                # glob("*_da_dung.jsonl")
    re.compile(r"(^|/)phan_tich_.*\.md$"),          # Ada journal/phan_tich_<date>.md (LOW-246)
    re.compile(r"(^|/)bao_cao\.txt$"),              # Ada workdir bao_cao.txt (LOW-246)
]

PATH_FUNCS = {"open", "Path", "PurePath", "PosixPath", "glob", "rglob", "joinpath", "join", "with_name"}
EXCLUDE_NAMES = {"state_path_migration.py", "migrate_state_paths.py", "migrate_state_files.py"}


def _production_files():
    files = sorted(ROOT.glob("*.py")) + sorted((ROOT / "prepare").glob("*.py"))
    return [p for p in files if "chuan_bi" not in p.name and p.name not in EXCLUDE_NAMES]


def _template(node):
    """Chuoi cua Constant/JoinedStr, bieu thuc trong f-string thay bang \\0; None neu khong phai chuoi."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "\x00" for v in node.values)
    return None


def _path_operands(node):
    """Cac nut chuoi DUNG o vi tri doan duong dan (di qua IfExp/BoolOp, khong di vao Call/Subscript)."""
    if isinstance(node, ast.IfExp):
        yield from _path_operands(node.body)
        yield from _path_operands(node.orelse)
    elif isinstance(node, ast.BoolOp):
        for v in node.values:
            yield from _path_operands(v)
    elif _template(node) is not None:
        yield node


def _skip_nodes(tree):
    """id cua docstring va cua phan hang BEN TRONG f-string (f-string duoc xet nguyen khoi)."""
    ra = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body:
            first = n.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                ra.add(id(first.value))
        if isinstance(n, ast.JoinedStr):
            ra |= {id(v) for v in n.values}
    return ra


def _old_segment(tpl: str):
    for seg in tpl.split("/"):
        if seg in OLD_NAMES:
            return seg
    return None


def scan_source(src: str, name: str = "<src>") -> list:
    """[(ten tep, dong, mo ta)] cho moi cho production con dung ten cu."""
    tree = ast.parse(src)
    skip = _skip_nodes(tree)
    bad = []
    # (a) ten cu o vi tri doan duong dan
    for n in ast.walk(tree):
        cands = []
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
            cands = [n.left, n.right]
        elif isinstance(n, ast.Call):
            f = n.func
            fname = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if fname in PATH_FUNCS:
                cands = list(n.args)
        for c in cands:
            for op in _path_operands(c):
                seg = _old_segment(_template(op))
                if seg is not None:
                    bad.append((name, op.lineno, f"ten cu {seg!r} o cho dung duong dan"))
    # (b) chuoi mang dang ten tep cu, o bat ky dau (tru docstring)
    for n in ast.walk(tree):
        tpl = _template(n)
        if tpl is None or id(n) in skip:
            continue
        for rx in OLD_FILE_SHAPES:
            if rx.search(tpl):
                bad.append((name, n.lineno, f"chuoi dang ten tep cu {tpl.replace(chr(0), '{…}')!r}"))
                break
    return bad


def test_scanner_catches_old_path_names_and_allows_non_path_use():
    must_catch = [
        'wd / "goc" / f"{ma}.png"',
        'p = STATE_DIR / "chuan_bi" / draft_id / "xong.json"',
        'open(wd / "dang_chay.pid", "w")',
        'Path("state", "chuan_bi")',
        'wd.glob("goc/*.png")',
        'wd.glob("*/xong.json")',
        'd = wd / ("san" if ok else "goc")',
        'x = wd / f"chuan_bi/{d}/tu_lieu.md"',
        'lock = f"chuan_bi.{i}.lock"',
        'out = d / f"xep_hang_{slug}.png"',
        'ten = f"chup_{n}_{k}.png"',
        'p = src.with_name(f"{ma}.ngang.png")',
        'h = DRAFTS / f"{draft_id}.ban_giao.md"',
        'r = wd / f"them_{n}"',
        'r = wd / "them"',
        'r = wd / "thuong_hieu" / "xh"',
        'os.path.join(root, "bang_anh.png")',
    ]
    for src in must_catch:
        assert scan_source(src), f"quet bo sot: {src}"
    must_allow = [
        'ok = a.get("source") == "khai_niem"',
        'a["source"] = "chup_nguon"',
        'meta.add_text("nguon_dung", "chup_xep_hang")',
        'k = m.get("goc") or m.get("san")',
        'wd / m.get("goc")',
        'text = "ghép dọc với một ảnh ngang cùng tone"',
        'def f():\n    """ghi <id>.ngang.png va xong.json"""\n',
        'r = {"kind": "bang"}',
        'wd / state_paths.ORIGINAL_DIR / f"{ma}.png"',
        'wd / f"{ma}{state_paths.LANDSCAPE_SUFFIX}"',
    ]
    for src in must_allow:
        assert not scan_source(src), f"quet bat oan: {src} -> {scan_source(src)}"


def test_scanner_catches_low231_state_names():
    must_catch = [
        'p = STATE_DIR / f"nguon_{draft_id}.json"',
        'p = state / "nguon_x.json"',
        'for f in state.glob("nguon_*.json"): pass',
        'p = env_load.state_dir() / "anh_da_dung.jsonl"',
        'p = env_load.state_dir() / "edu_theme_da_dung.jsonl"',
        'for f in d.glob("*_da_dung.jsonl"): pass',
        'Q = STATE_DIR / "dat_bai.json"',
        'Q = STATE_DIR / "da_bao_tien_do.json"',
        'Q = STATE_DIR / "da_bao_treo.json"',
        'Q = STATE_DIR / "tin_ket_qua_task.json"',
        'Q = STATE_DIR / "lam_lai_cho.json"',
        'Q = STATE_DIR / "moat_day_lai.json"',
        'm = STATE_DIR / f"bao_cao_mid.{vai}.json"',
        'b = env_load.state_dir() / f"bat_buoc_{vai}.json"',
        'wd = env_load.state_dir() / "quet" / ten',
        'dest = env_load.state_dir() / "tai_ve" / ma',
        'j = env_load.state_dir() / "nhat_ky"',
        'j = DIRECTORY / "nhat_ky" / "ghi_chu.jsonl"',
        'q = wd / "quet.json"',
        'b = wd / "baocao.txt"',
        'tep = "picks.json" if finn else "ds.json"',
        'x = f"{wd}/ds.json"',
        'open(wd / "khong_co.txt", "w")',
        'o = wd / "thu_manifest.json"',
        'p = DIRECTORY / f"ket_noi_{ngay}.jsonl"',
        'd = json.loads((wd / "vung_ocr.json").read_text())',
        'v = wd / "vung.json"',
        'about_preview(img, vung, wd / "vung_preview.png")',
        'n = wd / "nen_sach.png"',
        'o = wd / f"ket_qua_{id_}.png"',
        'o = state / f"{id_}_nen_sach.png"',
        'goc = Path(wd) / "logo_goc.png"',                       # LOW-237
        'the = card_logo(goc, Path(wd) / "the_logo.png")',
        'ra = _P(wd) / f"co_phieu_{khoa}.png"',
        'SPOOL = STATE_DIR / "moat_chua_bao.json"',            # LOW-240
        '(wd / "draft_thu.txt").write_text(cap)',                # LOW-242
        'BOSS_IDS = STATE_DIR / "ong_chu.json"',                # LOW-241
    ]
    for src in must_catch:
        assert scan_source(src), f"quet bo sot (LOW-231): {src}"
    must_allow = [
        'k = d.get("nguon_dung")',
        'nguon_path = state_paths.article_source_file(STATE_DIR, draft_id)',
        'x = {"nhat_ky_9router": nk, "ghi_chu": "", "loi_ket_noi": []}',
        'print(f"[nhat_ky] loi doc DB — {loi}")',
        'return {"nen_sach": str(wd / state_paths.GIN_CLEAN_BACKGROUND_FILE)}',
        'r = required.file("vera").name',
        'wd = env_load.state_dir() / state_paths.SCAN_DIR / ten',
        'q = wd / state_paths.SCAN_RESULT_FILE',
        'o = wd / f"{state_paths.GIN_RESULT_PREFIX}{id_}.png"',
        'ra = wd / f"{state_paths.STOCK_IMAGE_PREFIX}{khoa}.png"',
        'print(f"[co_phieu] {ma}: khong thay bieu do")',
        'def f():\n    """doc state/<brand>/anh_da_dung.jsonl va quet/ds.json"""\n',
    ]
    for src in must_allow:
        assert not scan_source(src), f"quet bat oan (LOW-231): {src} -> {scan_source(src)}"


def test_production_has_no_old_state_path_names():
    bad = []
    for p in _production_files():
        try:
            bad += scan_source(p.read_text(encoding="utf-8"), str(p.relative_to(ROOT)))
        except SyntaxError as e:
            bad.append((str(p.relative_to(ROOT)), e.lineno, f"SyntaxError {e.msg}"))
    assert not bad, (f"{len(bad)} cho production con ten duong dan cu (LOW-228):\n  "
                     + "\n  ".join(f"{f}:{d} {m}" for f, d, m in bad))


# Ten tep cap draft CO DUOI — trong chu gui vai/Ong Chu ("mở bang_anh.png", "Thiếu xong.json")
# ten cu cung sai: tep do khong con ton tai. Chan bien \w/. de "anh_da_dung.jsonl" (LOW-231) khong dinh.
OLD_FILE_TOKEN = re.compile(r"(?<![\w.])(" + "|".join(
    re.escape(k) for k in sorted(TABLE["draft_files"], key=len, reverse=True)) + r")(?![\w])")


def scan_text(src: str, name: str = "<src>") -> list:
    """[(ten tep, dong, ten cu)] cho chuoi (khong tinh docstring) nhac ten tep cap draft cu."""
    tree = ast.parse(src)
    skip = _skip_nodes(tree)
    bad = []
    for n in ast.walk(tree):
        if id(n) in skip:
            continue
        tpl = _template(n)
        if tpl is None:
            continue
        m = OLD_FILE_TOKEN.search(tpl)
        if m:
            bad.append((name, n.lineno, m.group(1)))
    return bad


def test_text_scanner_catches_old_file_names_in_messages():
    assert scan_text('L.append(f"Nhìn tất cả ảnh: {m[\'workdir\']}/bang_anh.png")')
    assert scan_text('note = "⚠️ Không đọc được bản chuẩn bị (xong.json)"')
    assert scan_text('x = "mở tu_lieu.md rồi đọc"')
    assert not scan_text('p = state_dir() / "anh_da_dung.jsonl"'), "LOW-231 ngoai pham vi"
    assert not scan_text('for f in d.glob("*_da_dung.jsonl"): pass')
    assert not scan_text('def f():\n    """doc xong.json"""\n')
    assert not scan_text('x = "mở contact_sheet.png rồi đọc material.md"')


def test_production_text_names_no_old_draft_files():
    bad = []
    for p in _production_files():
        try:
            bad += scan_text(p.read_text(encoding="utf-8"), str(p.relative_to(ROOT)))
        except SyntaxError:
            continue                                    # da bao o test_production_has_no_old_state_path_names
    assert not bad, (f"{len(bad)} chuoi production con nhac ten tep cu (LOW-228):\n  "
                     + "\n  ".join(f"{f}:{d} {m}" for f, d, m in bad))


def test_scan_covers_real_files():
    names = {p.name for p in _production_files()}
    assert {"image_prepare.py", "approve_post.py", "submit_common.py", "fallback_rounds.py"} <= names, names
    assert not any("chuan_bi" in n for n in names) and not names & EXCLUDE_NAMES


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
