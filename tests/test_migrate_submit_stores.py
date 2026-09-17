#!/usr/bin/env python3
"""migrate_submit_stores.py (LOW-242): writer/designer submit stores -> English keys.

Guards: the script's maps equal the approved table and the code writes/reads exactly the
table's new names (previous_submission via send_album, submit_count, used_images lines,
handoff metadata, caption_check info, card.BRAND, render_edu internals, draft_trial.txt);
dry-run writes nothing; a real run renames keys in every store of both brands and the
single-brand layout (Dre list `anh` vs Ethan string `anh` told apart by type), keeps
unknown keys (journal), keeps unparseable/blank/already-new jsonl lines byte for byte,
backs up originals; the result reads back through the readers (check_redo_reused,
block_redo, count_round_error, check_not_reused); an unknown shape refuses the whole run
(nothing written); re-run is a no-op."""
import contextlib
import hashlib
import io
import json
import subprocess
import sys
import tarfile
import tempfile
import time
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import state_paths as sp                                      # noqa: E402

TABLE = json.loads((ROOT / "docs" / "tu_dien_ten" / "submit_keys_v2.json").read_text(encoding="utf-8"))

DRE_PREV = {"bia": "A3", "hook": "Nvidia mua lại", "anh": ["A3", "A1", "A5"], "luc": "11:58 14/09", "lan": 2,
            "remakes": 1, "message_id": 2791}
DRE_PREV_NEW = {"cover_image": "A3", "hook": "Nvidia mua lại", "image_ids": ["A3", "A1", "A5"],
                "submitted_at": "11:58 14/09", "submission_count": 2, "remakes": 1, "message_id": 2791}
ETHAN_PREV = {"anh": "A2", "hook": "Hook", "anh2": None, "luc": "09:00 15/09", "lan": 1, "remakes": 0,
              "message_id": None, "ghi_tay": "x"}
ETHAN_PREV_NEW = {"image": "A2", "hook": "Hook", "image2": None, "submitted_at": "09:00 15/09",
                  "submission_count": 1, "remakes": 0, "message_id": None, "ghi_tay": "x"}
KITE_PREV = {"theme": "ocean", "hero": "chip", "hook": "H", "hinh": ["A1"], "luc": "10:00 16/09", "lan": 3,
             "remakes": 2, "message_id": 12}
KITE_PREV_NEW = {"theme": "ocean", "hero": "chip", "hook": "H", "image_ids": ["A1"], "submitted_at": "10:00 16/09",
                 "submission_count": 3, "remakes": 2, "message_id": 12}
LOI = ["bìa: thiếu ảnh"]
SIG = hashlib.md5("\n".join(sorted(LOI)).encode()).hexdigest()     # same signature count_round_error computes
NOW = int(time.time())
COUNT = {"ky": SIG, "lan": 2, "luc": NOW, "loi_cuoi": LOI}
COUNT_NEW = {"error_signature": SIG, "repeat_count": 2, "updated_at": NOW, "last_errors": LOI}
USED_OLD = {"dhash": "123", "draft_id": "d1-carousel-dcgr", "vai": "dre", "tin": "openai.com/x", "ten": "A1.png",
            "md5": "ab", "luc": 1758000000}
USED_NEW = {"dhash": "123", "draft_id": "d1-carousel-dcgr", "role": "dre", "story_key": "openai.com/x",
            "file_name": "A1.png", "md5": "ab", "used_at": 1758000000}


def _used_text(*rows, broken=False) -> str:
    lines = [json.dumps(r, ensure_ascii=False) for r in rows]
    if broken:
        lines.insert(1, '{"dhash": "9", "draft_')              # half-written append
    return "\n".join(lines) + "\n"


def _layout(tmp: Path, extra=None) -> dict:
    st = tmp / "state"
    files = {
        "dre_prev": st / "dcgr" / sp.PREPARE_DIR / "d1-carousel-dcgr" / sp.PREVIOUS_SUBMISSION_FILE,
        "ethan_prev": st / "blog" / sp.PREPARE_DIR / "d2-designer-blog" / sp.PREVIOUS_SUBMISSION_FILE,
        "kite_prev": st / sp.PREPARE_DIR / "d3-edu" / sp.PREVIOUS_SUBMISSION_FILE,
        "count": st / "dcgr" / sp.PREPARE_DIR / "d1-carousel-dcgr" / sp.SUBMIT_COUNT_FILE,
        "count_done": st / "blog" / sp.PREPARE_DIR / "d2-designer-blog" / sp.SUBMIT_COUNT_FILE,
        "used_dcgr": st / "dcgr" / sp.USED_IMAGES_FILE,
        "used_single": st / sp.USED_IMAGES_FILE,
        "used_done": st / "blog" / sp.USED_IMAGES_FILE,
        "other": st / "dcgr" / sp.PREPARE_DIR / "d1-carousel-dcgr" / "spec.json",
    }
    data = {"dre_prev": DRE_PREV, "ethan_prev": ETHAN_PREV, "kite_prev": KITE_PREV, "count": COUNT,
            "count_done": COUNT_NEW, "other": {"anh": "A1", "luc": 1},
            "used_dcgr": _used_text(USED_OLD, {**USED_OLD, "draft_id": "d9", "ghi_chu": "tay"}, broken=True),
            "used_single": "\n" + _used_text(USED_NEW, USED_OLD),
            "used_done": _used_text(USED_NEW)}
    data.update(extra or {})
    for k, p in files.items():
        p.parent.mkdir(parents=True, exist_ok=True)
        v = data[k]
        p.write_text(v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, indent=2), encoding="utf-8")
    return files


def _run(tmp: Path, *extra):
    return subprocess.run([sys.executable, str(ROOT / "migrate_submit_stores.py"), "--state", str(tmp / "state"),
                           *extra], capture_output=True, text=True, cwd=ROOT)


def _bytes(files: dict) -> dict:
    return {k: p.read_bytes() for k, p in files.items() if p.exists()}


def _load(p: Path):
    return json.loads(p.read_text(encoding="utf-8"))


def _clean(d: dict) -> dict:
    return {k: v for k, v in d.items() if not k.startswith("_")}


# ------------------------------------------------------------------ table <-> code
def test_maps_equal_approved_table():
    import migrate_submit_stores as m
    prev = _clean(TABLE["previous_submission"])
    plain = {k: v for k, v in prev.items() if " " not in k}
    by_role = {k.split(" ")[0]: v for k, v in prev.items() if " " in k and not k.startswith("anh ")}
    assert m.PREVIOUS_SUBMISSION_KEY_MAP == {**plain, **by_role}, (m.PREVIOUS_SUBMISSION_KEY_MAP, plain, by_role)
    assert m.OLD_IMAGE_KEY == "anh"
    assert m.PREVIOUS_SUBMISSION_IMAGE_BY_TYPE == {"list": prev["anh (Dre, list)"], "str": prev["anh (Ethan, chuỗi)"]}
    assert m.SUBMIT_COUNT_KEY_MAP == _clean(TABLE["submit_count"])
    assert m.USED_IMAGES_LINE_KEY_MAP == _clean(TABLE["used_images_line"])
    assert set(m.PREVIOUS_SUBMISSION_TYPES) == set(m.PREVIOUS_SUBMISSION_KEY_MAP.values()) \
        | set(m.PREVIOUS_SUBMISSION_IMAGE_BY_TYPE.values())
    assert set(m.SUBMIT_COUNT_TYPES) == set(m.SUBMIT_COUNT_KEY_MAP.values())
    assert set(m.USED_IMAGES_LINE_TYPES) == set(m.USED_IMAGES_LINE_KEY_MAP.values())


def test_used_images_writers_follow_table_and_schema():
    import migrate_submit_stores as m
    import schema
    from PIL import Image
    from tam import so_tam
    want = set(m.USED_IMAGES_LINE_KEY_MAP.values()) | m.FIXED_KEYS["used_images_line"]
    assert set(schema._kind(schema.LineImageUsed)) == want, schema._kind(schema.LineImageUsed)
    import image_rules_dre
    import image_rules_ethan
    import image_rules_kite
    for mod in (image_rules_dre, image_rules_ethan, image_rules_kite):
        with tempfile.TemporaryDirectory() as t, so_tam(t) as d:
            p = d / "a.png"
            Image.new("RGB", (64, 64), (200, 30, 30)).save(p)
            mod.record_used(p, "d1", "dre", "https://openai.com/x")
            (row,) = [json.loads(x) for x in (d / "s.jsonl").read_text(encoding="utf-8").splitlines()]
            assert set(row) == want, (mod.__name__, row)


def test_submit_count_and_previous_submission_writers_follow_table():
    import migrate_submit_stores as m
    import submit_common as nc
    with tempfile.TemporaryDirectory() as t:
        wd = Path(t)
        with contextlib.redirect_stdout(io.StringIO()):
            assert nc.count_round_error(wd, ["x"], "cmd") == 1
            assert nc.count_round_error(wd, ["x"], "cmd") == 1
        d = _load(wd / sp.SUBMIT_COUNT_FILE)
        assert set(d) == set(m.SUBMIT_COUNT_KEY_MAP.values()) and d["repeat_count"] == 2, d

    fake = types.SimpleNamespace(post=lambda *a, **k: {"result": {"message_id": 77}}, SendError=RuntimeError)
    old_mod = sys.modules.get("send_telegram")
    sys.modules["send_telegram"] = fake
    try:
        with tempfile.TemporaryDirectory() as t:
            wd = Path(t)
            with contextlib.redirect_stdout(io.StringIO()):
                mid = nc.send_album("dre", [], "x", "low242-khong-co-draft", wd, {"submission_count": 4},
                                    {"cover_image": "A1", "hook": "h", "image_ids": ["A1"]})
            d = _load(wd / sp.PREVIOUS_SUBMISSION_FILE)
            assert mid == 77 and d["submission_count"] == 5 and d["message_id"] == 77, d
            names = set(m.PREVIOUS_SUBMISSION_KEY_MAP.values()) | set(m.PREVIOUS_SUBMISSION_IMAGE_BY_TYPE.values())
            assert set(d) <= names | m.FIXED_KEYS["previous_submission"], d
    finally:
        if old_mod is None:
            sys.modules.pop("send_telegram", None)
        else:
            sys.modules["send_telegram"] = old_mod
    src = (ROOT / "submit_common.py").read_text(encoding="utf-8")
    assert 'for k in ("image_ids", "image", "image2", "cover_image"):' in src


def test_other_sections_follow_table():
    """Sections without on-disk data: handoff metadata, caption info, card.BRAND,
    render_edu internals, compute_derived, file names — code uses the new names."""
    import caption_check
    import card
    import render_edu
    from prepare import manifest
    info = _clean(TABLE["caption_check_info"])
    cap = "Nvidia công bố doanh thu 30 tỉ USD.\n\nCon số tăng 12% so với năm trước.\n\nHãng tự công bố."
    _l, _c, tin = caption_check.check(cap, "- Doanh thu 30 tỉ USD\n- Tăng 12%\n")
    assert set(tin) == set(info.values()), tin

    brand = _clean(TABLE["card_brand"])
    for name, b in card.BRAND.items():
        assert not set(b) & set(brand), (name, set(b) & set(brand))
        assert set(b) - {"handle"} <= set(brand.values()), (name, set(b))
    assert card.BRAND["dcgr"]["company_name_color"] == TABLE["card_brand.company_name_color_value"]["hang"]

    ren = TABLE["render_edu_internal"]
    for kind, q in render_edu.REQUIRED_KIND.items():
        assert set(q) <= {ren["truong"], ren["long"]} and ren["truong"] in q, (kind, q)
    assert '"served"' in (ROOT / "render_edu.py").read_text(encoding="utf-8")

    dx = manifest.compute_derived([], "ethan")
    assert TABLE["manifest_compute_derived"]["dung_duoc"] in dx and "dung_duoc" not in dx, dx

    assert sp.DRAFT_TRIAL_FILE == TABLE["files"]["draft_thu.txt"]
    bob = (ROOT / "bob_submit.py").read_text(encoding="utf-8")
    assert f'"{TABLE["files"]["goc.png (bob_submit tmp)"]}"' in bob and f'"{TABLE["files"]["khung.png (bob_submit tmp)"]}"' in bob

    handoff = _clean(TABLE["handoff_metadata"])
    entry = TABLE["handoff_blackboard_entry_keys"]
    for script in ("dre_submit.py", "kite_submit.py", "miles_submit.py"):
        src = (ROOT / script).read_text(encoding="utf-8")
        for old in handoff:
            assert f'"{old}":' not in src, (script, old)
        assert f'write_blackboard(a.draft_id, "{next(iter(entry))}"' not in src, script
    for script, keys in {"dre_submit.py": ("image_sources", "file_path", "handoff_path"),
                         "kite_submit.py": ("image_ids", "file_path", "handoff_path", "role"),
                         "miles_submit.py": ("char_count", "sentence_count", "number_count")}.items():
        src = (ROOT / script).read_text(encoding="utf-8")
        for k in keys:
            assert f'"{k}":' in src, (script, k)
    for script in ("dre_submit.py", "kite_submit.py"):
        assert f'write_blackboard(a.draft_id, "{entry["anh"]}"' in (ROOT / script).read_text(encoding="utf-8")


# ------------------------------------------------------------------ migration
def test_dry_run_writes_nothing():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        before = _bytes(f)
        r = _run(tmp, "--dry-run")
        assert r.returncode == 0 and "DRY RUN" in r.stdout and "6 file(s)" in r.stdout, (r.stdout, r.stderr)
        assert "unchanged state/blog/used_images.jsonl" in r.stdout, r.stdout
        assert "kept 1 unparseable line(s)" in r.stdout, r.stdout
        assert _bytes(f) == before and not list(tmp.glob("*.tar.gz")) and not list(tmp.glob("*.jsonl"))


def test_real_run_renames_backs_up_and_journals():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        before = _bytes(f)
        r = _run(tmp)
        assert r.returncode == 0, (r.stdout, r.stderr)
        assert _load(f["dre_prev"]) == DRE_PREV_NEW and list(_load(f["dre_prev"])) == list(DRE_PREV_NEW)
        assert _load(f["ethan_prev"]) == ETHAN_PREV_NEW
        assert _load(f["kite_prev"]) == KITE_PREV_NEW
        assert _load(f["count"]) == COUNT_NEW
        assert f["count"].read_text(encoding="utf-8") == json.dumps(COUNT_NEW, ensure_ascii=False)
        for k in ("count_done", "used_done", "other"):
            assert f[k].read_bytes() == before[k], f"{k} must not be rewritten"

        lines = f["used_dcgr"].read_text(encoding="utf-8").split("\n")
        assert len(lines) == 4 and lines[-1] == "", lines
        assert json.loads(lines[0]) == USED_NEW and list(json.loads(lines[0])) == list(USED_NEW)
        assert lines[1] == '{"dhash": "9", "draft_', "unparseable line kept verbatim"
        assert json.loads(lines[2]) == {**USED_NEW, "draft_id": "d9", "ghi_chu": "tay"}
        single = f["used_single"].read_text(encoding="utf-8").split("\n")
        assert single[0] == "" and single[1] == json.dumps(USED_NEW, ensure_ascii=False) \
            and json.loads(single[2]) == USED_NEW and single[3] == "", single

        (backup,) = tmp.glob("low242_submit_stores_backup_*.tar.gz")
        with tarfile.open(backup) as tar:
            names = set(tar.getnames())
            assert len(names) == 6, names
            assert tar.extractfile(str(f["used_dcgr"].relative_to(tmp))).read() == before["used_dcgr"]
        (journal,) = tmp.glob("low242_submit_stores_*.journal.jsonl")
        rows = {r_["file"]: r_ for r_ in (json.loads(x) for x in journal.read_text(encoding="utf-8").splitlines())}
        assert len(rows) == 6, rows
        assert rows[str(f["used_dcgr"])]["lines_changed"] == 2
        assert rows[str(f["used_dcgr"])]["unparseable_lines_kept"] == 1
        assert rows[str(f["used_dcgr"])]["kept_unknown_keys"] == ["line 3: ghi_chu"]
        assert rows[str(f["ethan_prev"])]["kept_unknown_keys"] == ["ghi_tay"]

        # readers see the migrated stores the way they saw the old ones
        import brief_common
        import submit_common as nc
        cu = nc.count_of_redo
        try:
            nc.count_of_redo = lambda _id: 2                   # Ong Chu bam Lam lai sau lan nop truoc
            loi = nc.check_redo_reused(_load(f["dre_prev"]), "bìa", "A3", "Nvidia mua lại",
                                       khoa_anh="cover_image", draft_id="x")
            assert len(loi) == 2, loi
            loi = nc.check_redo_reused(_load(f["ethan_prev"]), "ảnh", "A2", "Hook moi", draft_id="x")
            assert len(loi) == 1 and "A2" in loi[0], loi
        finally:
            nc.count_of_redo = cu
        assert "(11:58 14/09)" in brief_common.block_redo(_load(f["dre_prev"]), "x")[1]
        # the 3rd identical failure within 6 hours stops the role: only true if the
        # migrated signature/repeat_count/updated_at were read back
        with contextlib.redirect_stdout(io.StringIO()) as out:
            assert nc.count_round_error(f["count"].parent, LOI, "cmd") == 2, out.getvalue()
        assert _load(f["count"])["repeat_count"] == 3


def test_used_images_reader_blocks_on_migrated_line():
    import image_provenance
    import image_rules_ethan as la
    from PIL import Image, ImageDraw
    import migrate_submit_stores as m
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        p = tmp / "a.png"
        im = Image.new("RGB", (800, 600), (255, 255, 255))
        dr = ImageDraw.Draw(im)
        for i, h in enumerate([380, 300, 240, 180, 120]):
            dr.rectangle([60 + i * 140, 500 - h, 160 + i * 140, 500], fill=(40, 90, 200))
        im.save(p)
        log = tmp / "state" / "blog" / sp.USED_IMAGES_FILE
        log.parent.mkdir(parents=True)
        cu = image_provenance._used_images_log
        image_provenance._used_images_log = lambda: log
        try:
            la.record_used(p, "tin-abc-carousel-blog", "dre", "https://openai.com/tin-abc")
            back = {v: k for k, v in m.USED_IMAGES_LINE_KEY_MAP.items()}
            row = json.loads(log.read_text(encoding="utf-8"))
            log.write_text(json.dumps({back.get(k, k): v for k, v in row.items()}) + "\n", encoding="utf-8")
            assert "vai" in log.read_text(encoding="utf-8")
            assert _run(tmp).returncode == 0
            assert json.loads(log.read_text(encoding="utf-8")) == row
            assert la.check_not_reused("A1", p, "tin-abc-designer-blog", "https://openai.com/tin-abc")[0] == []
            (msg,) = la.check_not_reused("A1", p, "tin-xyz-carousel-blog", "https://x.com/khac")[0]
            assert "tin-abc-carousel-blog" in msg and "(dre," in msg, msg
        finally:
            image_provenance._used_images_log = cu


def test_bad_shape_or_conflict_refuses_everything():
    cases = (("dre_prev", {**DRE_PREV, "anh": {"A1": 1}}, "expected list (Dre) or str (Ethan)"),
             ("dre_prev", {**DRE_PREV, "anh": None}, "expected list (Dre) or str (Ethan)"),
             ("dre_prev", {**DRE_PREV, "submission_count": 2}, "both"),
             ("dre_prev", {**DRE_PREV, "hinh": ["A9"]}, "both become 'image_ids'"),
             ("kite_prev", {**KITE_PREV, "hinh": "A1"}, "image_ids is str"),
             ("ethan_prev", {**ETHAN_PREV, "lan": "1"}, "submission_count is str"),
             ("ethan_prev", ["anh", "A1"], "expected object"),
             ("count", {**COUNT, "luc": "hom qua"}, "updated_at is str"),
             ("count", {**COUNT, "lan": True}, "repeat_count is bool"),
             ("count", {**COUNT, "repeat_count": 1}, "both"),
             ("used_dcgr", _used_text(USED_OLD, [1, 2]), "line 2 is list"),
             ("used_dcgr", _used_text({**USED_OLD, "role": "dre"}), "both"),
             ("used_dcgr", _used_text({**USED_OLD, "luc": "x"}), "used_at is str"))
    for key, bad, word in cases:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            f = _layout(tmp, {key: bad})
            before = _bytes(f)
            r = _run(tmp)
            assert r.returncode == 1 and word in r.stderr and "nothing written" in r.stderr, (key, bad, r.stderr)
            assert _bytes(f) == before and not list(tmp.glob("*.tar.gz")), (key, bad)


def test_rerun_is_noop():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        f = _layout(tmp)
        assert _run(tmp).returncode == 0
        after = _bytes(f)
        r = _run(tmp)
        assert r.returncode == 0 and "nothing to do" in r.stdout, r.stdout
        assert _bytes(f) == after
        assert len(list(tmp.glob("*.tar.gz"))) == 1


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
