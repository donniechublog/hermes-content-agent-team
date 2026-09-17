#!/usr/bin/env python3
"""migrate_article_sources.py (LOW-238): article_source_<id>.json -> English keys + kinds.

Guards: the script's maps equal the approved table; dry-run writes nothing; real run renames
keys and page kinds in every brand + the single-brand layout, keeps hand-written extra keys
(noted in the journal), backs up originals; the result reads back through the readers
(article_images.other_outlets' filter, prepare.source.load_source); an unknown shape (not a
dict, pages not a list, page not a dict, unknown kind, old and new side by side) or a live
prepare engine refuses the whole run (nothing written); re-run is a no-op."""
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
import state_paths as sp                                      # noqa: E402

OLD = {"tieu_de": "Nvidia rót vốn", "tieu_de_en": "Nvidia invests", "link_goc": "https://a.example/1",
       "link_gnews": "https://news.google.com/rss/articles/CBMi",
       "trang": [{"url": "https://a.example/1", "loai": "gốc", "tieu_de": "Nvidia rót vốn"},
                 {"url": "https://b.example/2", "loai": "báo", "tieu_de": "Nvidia invests",
                  "toa_soan": "https://b.example"},
                 {"url": "https://nvidia.com/news/x", "loai": "công bố", "tieu_de": "",
                  "toa_soan": "https://nvidia.com"}]}
NEW = {"title": "Nvidia rót vốn", "title_en": "Nvidia invests", "source_url": "https://a.example/1",
       "gnews_url": "https://news.google.com/rss/articles/CBMi",
       "pages": [{"url": "https://a.example/1", "kind": "article", "title": "Nvidia rót vốn"},
                 {"url": "https://b.example/2", "kind": "other_outlet", "title": "Nvidia invests",
                  "outlet_url": "https://b.example"},
                 {"url": "https://nvidia.com/news/x", "kind": "announcement", "title": "",
                  "outlet_url": "https://nvidia.com"}]}
# hand-written blog file: extra keys nobody reads, kinds bảng/giá
HAND = {"tieu_de": "t", "link_goc": "https://c.example/", "tom_tat": "s", "y_chinh": ["a"],
        "trang": [{"url": "https://c.example/", "loai": "bảng", "anh": ["x.png"]},
                  {"url": "https://c.example/p", "loai": "giá"}]}
HAND_NEW = {"title": "t", "source_url": "https://c.example/", "tom_tat": "s", "y_chinh": ["a"],
            "pages": [{"url": "https://c.example/", "kind": "table", "anh": ["x.png"]},
                      {"url": "https://c.example/p", "kind": "price"}]}


def _layout(tmp: Path, extra=None) -> dict:
    st = tmp / "state"
    files = {"dcgr": sp.article_source_file(st / "dcgr", "d1"), "blog": sp.article_source_file(st / "blog", "d1"),
             "single": sp.article_source_file(st, "d1"), "done": sp.article_source_file(st / "blog", "d2"),
             "other": st / "blog" / sp.USED_IMAGES_FILE}
    data = {"dcgr": OLD, "blog": HAND, "single": OLD, "done": NEW, "other": {"trang": []}}
    data.update(extra or {})
    for k, p in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(json.dumps(data[k], ensure_ascii=False, indent=2), encoding="utf-8")
    return files


def _run(tmp: Path, *extra):
    return subprocess.run([sys.executable, str(ROOT / "migrate_article_sources.py"), "--state", str(tmp / "state"),
                           *extra], capture_output=True, text=True, cwd=ROOT)


def _bytes(files: dict) -> dict:
    return {k: p.read_bytes() for k, p in files.items()}


def test_maps_equal_approved_table():
    import migrate_article_sources as m
    t = json.loads((ROOT / "docs" / "tu_dien_ten" / "article_source_keys_v2.json").read_text(encoding="utf-8"))

    def _clean(d):
        return {k: v for k, v in d.items() if not k.startswith("_")}
    assert m.KEY_MAP == _clean(t["article_source"])
    assert m.PAGE_KEY_MAP == _clean(t["article_source.pages[]"])
    assert m.KIND_MAP == _clean(t["article_source.pages[].kind"])


def test_code_writes_only_table_kinds_and_labels_cover_them():
    """Mọi `kind` code ghi ra là mã trong bảng, và nhãn hiển thị tiếng Việt khớp giá trị cũ."""
    import article_sources
    import migrate_article_sources as m
    assert {v: k for k, v in m.KIND_MAP.items()} == article_sources.PAGE_KIND_LABELS


def test_dry_run_writes_nothing():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        before = _bytes(f)
        r = _run(tmp, "--dry-run")
        assert r.returncode == 0 and "DRY RUN" in r.stdout and "3 file(s)" in r.stdout, (r.stdout, r.stderr)
        assert "kept unknown keys: tom_tat, y_chinh, pages[0].anh" in r.stdout, r.stdout
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
        assert json.loads(f["blog"].read_text(encoding="utf-8")) == HAND_NEW
        assert f["done"].read_bytes() == before["done"], "already-new file must not be rewritten"
        assert f["other"].read_bytes() == before["other"], "only article_source_*.json is touched"
        (backup,) = tmp.glob("low238_article_sources_backup_*.tar.gz")
        with tarfile.open(backup) as tar:
            assert sorted(tar.getnames()) == sorted(str(f[k].relative_to(tmp)) for k in ("dcgr", "blog", "single"))
            assert tar.extractfile(str(f["dcgr"].relative_to(tmp))).read() == before["dcgr"]
        (journal,) = tmp.glob("low238_article_sources_*.journal.jsonl")
        rows = {r_["file"]: r_ for r_ in (json.loads(x) for x in journal.read_text(encoding="utf-8").splitlines())}
        assert set(rows) == {str(f[k]) for k in ("dcgr", "blog", "single")}, rows
        assert rows[str(f["dcgr"])]["to_keys"] == ["gnews_url", "pages", "source_url", "title", "title_en"]
        assert rows[str(f["dcgr"])]["page_kinds"] == {"gốc": 1, "báo": 1, "công bố": 1}
        assert rows[str(f["dcgr"])]["kept_unknown_keys"] == []
        assert rows[str(f["blog"])]["kept_unknown_keys"] == ["tom_tat", "y_chinh", "pages[0].anh"]

        # readers see the migrated file the same way they saw the old one
        import article_sources
        from unittest import mock
        import article_images
        with mock.patch.object(article_sources, "find",
                               return_value=json.loads(f["dcgr"].read_text(encoding="utf-8"))):
            assert article_images.other_outlets("x", "https://a.example/1") == [
                ("https://b.example/2", "Nvidia invests"), ("https://nvidia.com/news/x", "")]
        from prepare import source
        nguon, _, link = source.load_source("d1", {"source_url": "https://a.example/1"}, tmp / "state" / "dcgr")
        assert link == "https://a.example/1" and nguon["pages"][2]["kind"] == "announcement"


def test_bad_shape_or_conflict_refuses_everything():
    cases = (({"tieu_de": "t", "title": "t"}, "both"),
             ({"trang": [{"url": "u", "loai": "gốc", "kind": "article"}]}, "both"),
             (["trang"], "not an object"),
             ({"trang": {"url": "u"}}, "expected list"),
             ({"pages": ["https://u"]}, "expected object"),
             ({"trang": [{"url": "u", "loai": "tweet"}]}, "unknown kind"),
             ({"trang": [{"url": "u", "loai": None}]}, "unknown kind"))
    for bad, word in cases:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            f = _layout(tmp, {"blog": bad})
            before = _bytes(f)
            r = _run(tmp)
            assert r.returncode == 1 and word in r.stderr and "nothing written" in r.stderr, (bad, r.stderr)
            assert _bytes(f) == before and not list(tmp.glob("*.tar.gz")), bad


def test_live_engine_refuses_everything():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        pid = tmp / "state" / "dcgr" / sp.PREPARE_DIR / "d1" / sp.RUNNING_PID_FILE
        pid.parent.mkdir(parents=True)
        pid.write_text(str(os.getpid()))
        before = _bytes(f)
        r = _run(tmp)
        assert r.returncode == 1 and "still running" in r.stderr, r.stderr
        assert _bytes(f) == before and not list(tmp.glob("*.tar.gz"))


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
