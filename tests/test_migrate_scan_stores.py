#!/usr/bin/env python3
"""migrate_scan_stores.py (LOW-240): news-scan + moat stores -> English keys/values.

Guards: the script's maps equal the approved table; dry-run writes nothing; a real run
renames keys + enumerated values in every store of both brands and the single-brand
layout (Vera outlet vs Qinn author told apart), renames the moat spool, touches only the
moat keys of drafts, keeps unknown keys (journal), backs up originals; the result reads
back through the readers (manifest_write, required, scan_business/scan_x seen-stores,
approve_pick's duplicate gate data); an unknown shape refuses the whole run (nothing
written); re-run is a no-op."""
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

TABLE = json.loads((ROOT / "docs" / "tu_dien_ten" / "scan_keys_v2.json").read_text(encoding="utf-8"))

VERA_SCAN = {"quet_luc": "2026-09-17T00:00:00+00:00", "tong_quet": 40, "tin_watchlist": 1,
             "tin_moi": [{"goc": "báo công nghệ", "tieu_de": "Nvidia invests - Reuters", "toa_soan": "Reuters",
                          "link": "https://g.example/1", "ts": 100, "ngay": "2026-09-17", "so_bao": 2,
                          "cac_bao": ["Reuters", "CNBC"], "watchlist": True}]}
VERA_SCAN_NEW = {"scanned_at": "2026-09-17T00:00:00+00:00", "scanned_total": 40, "watchlist_count": 1,
                 "new_stories": [{"feed_group": "báo công nghệ", "title": "Nvidia invests - Reuters",
                                  "outlet": "Reuters", "link": "https://g.example/1", "ts": 100,
                                  "date": "2026-09-17", "outlet_count": 2, "outlets": ["Reuters", "CNBC"],
                                  "watchlist": True}]}
QINN_SCAN = {"quet_luc": "t", "cua_so_gio": 12, "tong_quet": 3,
             "tin_moi": [{"id": "1", "tieu_de": "repo x", "link": "https://x.com/a/1", "ngay": "2026-09-17",
                          "toa_soan": "@karpathy", "so_bao": 1, "nguon_x": "list:ai", "loai": "tweet",
                          "so_lieu": {"views": 1, "likes": 2, "replies": 0, "retweets": 0}, "so_anh": 0,
                          "diem": 30, "text": "long text"}],
             "bo_qua": {"reply": 1, "ngan": 2, "da_thay": 3, "rong": 0},
             "freshness": {"latestCrawledAt": "t"}, "tre_gio": 0.5, "canh_bao": []}
QINN_SCAN_NEW = {"scanned_at": "t", "window_hours": 12, "scanned_total": 3,
                 "new_stories": [{"id": "1", "title": "repo x", "link": "https://x.com/a/1", "date": "2026-09-17",
                                  "author": "@karpathy", "outlet_count": 1, "x_source": "list:ai",
                                  "tweet_type": "tweet",
                                  "metrics": {"views": 1, "likes": 2, "replies": 0, "retweets": 0},
                                  "media_count": 0, "mechanical_score": 30, "text": "long text"}],
                 "skipped": {"reply": 1, "too_short": 2, "already_seen": 3, "missing_id_or_url": 0},
                 "freshness": {"latestCrawledAt": "t"}, "crawl_lag_hours": 0.5, "warnings": []}
FINN_CANDS = {"scanned_at": "t", "note": "n", "candidates": [
    {"source": "hackernews", "title": "A", "link": "https://a.example/", "nguoi_dang": "@pg", "points": 200},
    {"source": "bat_buoc", "title": "B", "link": "https://b.example/", "nguoi_dang": "", "points": 0,
     "bat_buoc": True, "summary_vi": "x"}]}
FINN_CANDS_NEW = {"scanned_at": "t", "note": "n", "candidates": [
    {"source": "hackernews", "title": "A", "link": "https://a.example/", "posted_by": "@pg", "points": 200},
    {"source": "required", "title": "B", "link": "https://b.example/", "posted_by": "", "points": 0,
     "required": True, "summary_vi": "x"}]}
ROLE_CANDS = {"quet_luc": "t", "vai": "vera", "items": [
    {"index": 1, "title": "T", "link": "https://real.example/1", "picked": True, "vai_anh": "dre",
     "brand": "dcgr", "vai_viet": "jika", "task_anh": "t_1", "task_viet": None, "nguon_loi": "boom",
     "link_gnews": "https://news.google.com/rss/articles/x",
     "da_giao": [{"vai_anh": "dre", "brand": "dcgr", "draft_id": "d1", "task_anh": "t_1"}]},
    {"index": 2, "title": "U", "link": "https://u.example/", "picked": False, "tu_them": True}]}
ROLE_CANDS_NEW = {"scanned_at": "t", "scan_role": "vera", "items": [
    {"index": 1, "title": "T", "link": "https://real.example/1", "picked": True, "image_role": "dre",
     "brand": "dcgr", "writer_role": "jika", "image_task": "t_1", "writer_task": None, "source_error": "boom",
     "gnews_url": "https://news.google.com/rss/articles/x",
     "assignments": [{"image_role": "dre", "brand": "dcgr", "draft_id": "d1", "image_task": "t_1"}]},
    {"index": 2, "title": "U", "link": "https://u.example/", "picked": False, "auto_added": True}]}
BUSINESS_SEEN = {"cap_nhat": "t", "khoa": {"nvidia invests": 100.0}, "ghi_chu": "su co 26/08"}
BUSINESS_SEEN_NEW = {"updated_at": "t", "seen_at": {"nvidia invests": 100.0}, "note": "su co 26/08"}
BUSINESS_SEEN_LIST = {"khoa": ["a", "b"]}                     # legacy list format
X_SEEN = {"khoa": {"1": 100.0}, "ghi_luc": "t"}
X_SEEN_NEW = {"seen_at": {"1": 100.0}, "updated_at": "t"}
REQUIRED = {"ra_mat|Claude Opus 5": {"ten": "Claude Opus 5", "loai": "ra_mat", "ghi_chu": "ra mat 2026-09-16",
                                     "link": "", "ngay": "2026-09-16"},
            "hang|nvidia|2026-09-17": {"ten": "nvidia: Nvidia invests", "loai": "watchlist", "ghi_chu": "2 bao",
                                       "link": "https://g.example/1", "ngay": "2026-09-17",
                                       "tu_khoa": ["nvidia"]}}
REQUIRED_NEW = {"release|Claude Opus 5": {"name": "Claude Opus 5", "kind": "release",
                                          "note": "ra mat 2026-09-16", "link": "", "added_date": "2026-09-16"},
                "hang|nvidia|2026-09-17": {"name": "nvidia: Nvidia invests", "kind": "watchlist", "note": "2 bao",
                                           "link": "https://g.example/1", "added_date": "2026-09-17",
                                           "keywords": ["nvidia"]}}
QUEUE = {"d1": {"lan": 2, "brand": "dcgr", "scheduled_at": None, "luc": 1700000000, "loi": "moat tra HTTP 524"}}
QUEUE_NEW = {"d1": {"attempts": 2, "brand": "dcgr", "scheduled_at": None, "last_attempt_at": 1700000000,
                    "error": "moat tra HTTP 524"}}
DRAFT = {"caption": "loi_da_bao trong chu thi khong doi", "moat": {"workflow_id": "w2", "loi_da_bao": "ConnectError"},
         "moat_lich_su": [{"workflow_id": "w1", "loi_da_bao": "ReadTimeout"}]}
DRAFT_NEW = {"caption": "loi_da_bao trong chu thi khong doi", "moat": {"workflow_id": "w2",
                                                                       "reported_error": "ConnectError"},
             "moat_history": [{"workflow_id": "w1", "reported_error": "ReadTimeout"}]}


def _layout(tmp: Path, extra=None) -> dict:
    st, dr = tmp / "state", tmp / "drafts"
    files = {
        "vera_scan": st / "dcgr" / sp.SCAN_DIR / "vera_20260917" / sp.SCAN_RESULT_FILE,
        "qinn_scan": st / "blog" / sp.SCAN_DIR / "qinn_20260917_p0" / sp.SCAN_RESULT_FILE,
        "finn_cands": st / "blog" / sp.SCAN_DIR / "finn_20260917" / "candidates.json",
        "role_cands": st / "dcgr" / "vera_candidates_2026-09-17.json",
        "single_cands": st / "finn_candidates_2026-09-17_t0501.json",
        "business_seen": st / "dcgr" / sp.BUSINESS_SEEN_FILE,
        "business_seen_list": st / sp.BUSINESS_SEEN_FILE,
        "x_seen": st / "blog" / sp.X_SEEN_FILE,
        "required": st / "blog" / sp.REQUIRED_FILE.format("nova"),
        "required_empty": st / "dcgr" / sp.REQUIRED_FILE.format("vera"),
        "queue": st / "dcgr" / sp.MOAT_REPUBLISH_QUEUE_FILE,
        "draft": dr / "d1.json",
        "draft_plain": dr / "d2.json",
        "done": st / "blog" / "nova_candidates_2026-09-16.json",
        "other": st / "blog" / sp.USED_IMAGES_FILE,
    }
    data = {"vera_scan": VERA_SCAN, "qinn_scan": QINN_SCAN, "finn_cands": FINN_CANDS, "role_cands": ROLE_CANDS,
            "single_cands": ROLE_CANDS, "business_seen": BUSINESS_SEEN, "business_seen_list": BUSINESS_SEEN_LIST,
            "x_seen": X_SEEN, "required": REQUIRED, "required_empty": {}, "queue": QUEUE, "draft": DRAFT,
            "draft_plain": {"caption": "x", "moat": {"workflow_id": "w"}}, "done": ROLE_CANDS_NEW,
            "other": {"khoa": 1}}
    data.update(extra or {})
    for k, p in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data[k], ensure_ascii=False, indent=2), encoding="utf-8")
    spool = st / "blog" / "moat_chua_bao.json"
    spool.write_text(json.dumps(["✅ d1 đã lên Facebook"], ensure_ascii=False), encoding="utf-8")
    files["spool"] = spool
    return files


def _run(tmp: Path, *extra):
    return subprocess.run([sys.executable, str(ROOT / "migrate_scan_stores.py"), "--state", str(tmp / "state"),
                           "--drafts", str(tmp / "drafts"), *extra], capture_output=True, text=True, cwd=ROOT)


def _bytes(files: dict) -> dict:
    return {k: p.read_bytes() for k, p in files.items() if p.exists()}


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def test_maps_equal_approved_table():
    import migrate_scan_stores as m

    def _clean(d):
        return {k: v for k, v in d.items() if not k.startswith("_")}
    pairs = {
        "scan_result": m.SCAN_RESULT_KEY_MAP,
        "scan_result.skipped": m.SKIPPED_KEY_MAP,
        "scan_result.new_stories[] (Vera, scan_business)": m.VERA_STORY_KEY_MAP,
        "scan_business_in_memory": m.VERA_IN_MEMORY_KEY_MAP,
        "scan_result.new_stories[] (Qinn, scan_x)": m.QINN_STORY_KEY_MAP,
        "finn_candidates": m.FINN_CANDIDATE_KEY_MAP,
        "finn_candidates.source_value": m.FINN_SOURCE_VALUE_MAP,
        "role_candidates": m.ROLE_CANDIDATES_KEY_MAP,
        "role_candidates.items[]": m.ROLE_ITEM_KEY_MAP,
        "role_candidates.items[].assignments[]": m.ASSIGNMENT_KEY_MAP,
        "business_seen": m.BUSINESS_SEEN_KEY_MAP,
        "x_seen": m.X_SEEN_KEY_MAP,
        "required_entry": m.REQUIRED_ENTRY_KEY_MAP,
        "required_entry.kind_value": m.REQUIRED_KIND_VALUE_MAP,
        "moat_republish_queue_entry": m.MOAT_QUEUE_ENTRY_KEY_MAP,
        "draft_moat": m.DRAFT_MOAT_KEY_MAP,
        "files": m.FILE_RENAMES,
        "env": m.ENV_RENAMES,
    }
    data_sections = {k for k in TABLE if not k.startswith("_")}
    assert set(pairs) == data_sections, (sorted(set(pairs) ^ data_sections))
    for section, mp in pairs.items():
        assert mp == _clean(TABLE[section]), section


def test_code_constants_follow_table():
    """Code and labels use the table's new names; display labels give back the old words."""
    import migrate_scan_stores as m
    import moat_publish
    import required
    import scan_x
    assert sp.MOAT_UNSENT_NOTICES_FILE == m.FILE_RENAMES["moat_chua_bao.json"]
    assert moat_publish.SPOOL.name == sp.MOAT_UNSENT_NOTICES_FILE
    assert {v: k for k, v in m.REQUIRED_KIND_VALUE_MAP.items()} == required.KIND_LABELS
    assert {v: k for k, v in m.FINN_SOURCE_VALUE_MAP.items()} == required.SOURCE_LABELS
    assert required.KIND_RELEASE in required.LINK_BOARD
    assert {v: k for k, v in m.SKIPPED_KEY_MAP.items()} == {k: v for k, v in scan_x.SKIPPED_LABELS.items()
                                                           if k != v}
    src = (ROOT / "moat_publish.py").read_text(encoding="utf-8")
    for old, new in m.ENV_RENAMES.items():
        assert old not in src and f'"{new}"' in src, (old, new)


def test_dry_run_writes_nothing():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        before = _bytes(f)
        r = _run(tmp, "--dry-run")
        assert r.returncode == 0 and "DRY RUN" in r.stdout and "11 file(s)" in r.stdout \
            and "1 renamed" in r.stdout, (r.stdout, r.stderr)
        assert "unchanged state/blog/nova_candidates_2026-09-16.json" in r.stdout, r.stdout
        assert _bytes(f) == before and not list(tmp.glob("*.tar.gz")) and not list(tmp.glob("*.jsonl"))


def test_real_run_renames_backs_up_and_journals():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        before = _bytes(f)
        r = _run(tmp)
        assert r.returncode == 0, (r.stdout, r.stderr)
        assert _load(f["vera_scan"]) == VERA_SCAN_NEW
        assert _load(f["qinn_scan"]) == QINN_SCAN_NEW
        assert _load(f["finn_cands"]) == FINN_CANDS_NEW
        assert _load(f["role_cands"]) == ROLE_CANDS_NEW and _load(f["single_cands"]) == ROLE_CANDS_NEW
        assert _load(f["business_seen"]) == BUSINESS_SEEN_NEW
        assert _load(f["business_seen_list"]) == {"seen_at": ["a", "b"]}
        assert _load(f["x_seen"]) == X_SEEN_NEW
        assert _load(f["required"]) == REQUIRED_NEW
        assert _load(f["queue"]) == QUEUE_NEW
        assert _load(f["draft"]) == DRAFT_NEW
        for k in ("done", "other", "draft_plain", "required_empty"):
            assert f[k].read_bytes() == before[k], f"{k} must not be rewritten"
        assert not f["spool"].exists()
        new_spool = f["spool"].with_name(sp.MOAT_UNSENT_NOTICES_FILE)
        assert new_spool.read_bytes() == before["spool"]

        (backup,) = tmp.glob("low240_scan_stores_backup_*.tar.gz")
        with tarfile.open(backup) as tar:
            names = set(tar.getnames())
            assert str(f["vera_scan"].relative_to(tmp)) in names and "drafts/d1.json" in names, names
            assert str(f["spool"].relative_to(tmp)) in names, names
            assert tar.extractfile(str(f["qinn_scan"].relative_to(tmp))).read() == before["qinn_scan"]
            assert len(names) == 12, names
        (journal,) = tmp.glob("low240_scan_stores_*.journal.jsonl")
        rows = {r_["file"]: r_ for r_ in (json.loads(x) for x in journal.read_text(encoding="utf-8").splitlines())}
        assert len(rows) == 12, rows
        assert rows[str(f["required"])]["values"] == {"kind:ra_mat": 1, "id_prefix:ra_mat": 1}
        assert rows[str(f["finn_cands"])]["values"] == {"source:bat_buoc": 1}
        assert rows[str(f["finn_cands"])]["kept_unknown_keys"] == ["candidates[].summary_vi"]
        assert rows[str(f["spool"])]["renamed_to"] == str(new_spool)

        # readers see the migrated stores the way they saw the old ones
        import manifest_write as mw
        assert mw._count_report(_load(f["vera_scan"])["new_stories"][0]) == "2 báo: Reuters, CNBC"
        assert mw._count_report(_load(f["qinn_scan"])["new_stories"][0]) == "@karpathy · list:ai"
        import required
        from unittest import mock
        with mock.patch.object(required, "file", lambda vai: f["required"]):
            (release,) = [v for v in required.read("nova").values() if v["kind"] == required.KIND_RELEASE]
            assert required.link_call_y(release) == "https://artificialanalysis.ai/leaderboards/models"
            assert required.check("nova", [{"title": "Nvidia invests", "summary_vi": ""}]) == [release]
        import scan_business
        import scan_x
        with mock.patch.object(scan_business, "STATE", f["business_seen"]):
            assert scan_business.already_see() == {"nvidia invests": 100.0}
        with mock.patch.object(scan_business, "STATE", f["business_seen_list"]):
            assert set(scan_business.already_see()) == {"a", "b"}
        with mock.patch.object(scan_x, "STATE", f["x_seen"]):
            assert scan_x.already_see() == {"1": 100.0}


def test_bad_shape_or_conflict_refuses_everything():
    cases = (("vera_scan", {"quet_luc": "t", "scanned_at": "t"}, "both"),
             ("vera_scan", {"tin_moi": {"a": 1}}, "expected list"),
             ("vera_scan", {"tin_moi": [{"tieu_de": "x", "toa_soan": "y"}]}, "cannot tell"),
             ("vera_scan", {"tin_watchlist": 1, "tin_moi": [{"toa_soan": "@a", "nguon_x": "home"}]}, "both Qinn"),
             ("vera_scan", QINN_SCAN, "run directory is vera"),
             ("qinn_scan", {**QINN_SCAN, "bo_qua": [1]}, "expected object"),
             ("finn_cands", {"candidates": [{"nguoi_dang": "a", "posted_by": "a"}]}, "both"),
             ("role_cands", {"items": [{"da_giao": {"vai_anh": "dre"}}]}, "expected list"),
             ("role_cands", "items", "expected object"),
             ("business_seen", {"khoa": 3}, "expected object or list"),
             ("required", {"ra_mat|X": {"ten": "X"}, "release|X": {"name": "X"}}, "collides"),
             ("queue", {"d1": ["lan", 1]}, "expected object"),
             ("draft", {"moat_lich_su": [], "moat_history": []}, "both"),
             ("draft", {"moat": {"loi_da_bao": "a", "reported_error": "b"}}, "both"))
    for key, bad, word in cases:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            f = _layout(tmp, {key: bad})
            before = _bytes(f)
            r = _run(tmp)
            assert r.returncode == 1 and word in r.stderr and "nothing written" in r.stderr, (key, bad, r.stderr)
            assert _bytes(f) == before and not list(tmp.glob("*.tar.gz")), (key, bad)


def test_unparseable_draft_mentioning_old_keys_or_spool_conflict_refuses():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        (tmp / "drafts" / "broken.json").write_text('{"moat_lich_su": [', encoding="utf-8")
        (tmp / "drafts" / "broken_other.json").write_text('{"caption": ', encoding="utf-8")   # not ours: ignored
        r = _run(tmp)
        assert r.returncode == 1 and "broken.json" in r.stderr and "broken_other" not in r.stderr, r.stderr
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        f["spool"].with_name(sp.MOAT_UNSENT_NOTICES_FILE).write_text("[]", encoding="utf-8")
        before = _bytes(f)
        r = _run(tmp)
        assert r.returncode == 1 and "already exists" in r.stderr, r.stderr
        assert _bytes(f) == before


def test_rerun_is_noop():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        assert _run(tmp).returncode == 0
        after = {k: p.read_bytes() for k, p in f.items() if p.exists()}
        r = _run(tmp)
        assert r.returncode == 0 and "nothing to do" in r.stdout, r.stdout
        assert {k: p.read_bytes() for k, p in f.items() if p.exists()} == after
        assert len(list(tmp.glob("*.tar.gz"))) == 1


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
