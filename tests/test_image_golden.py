#!/usr/bin/env python3
"""Bộ nhãn chuẩn ảnh + phép đo loại oan/lọt rác (LOW-224, 17/09/2026).

Giữ ba điều:
  1. "Engine giữ ảnh" trong phép đo là ĐÚNG công thức `schema.count_image_use_ok`
     (relevant, uses, mặt người không tên) — không đoán lại lần thứ hai.
  2. Chọn mẫu tất định theo seed, giữ trọn draft chỉ định, không vượt trần mỗi draft.
  3. Ảnh được CHỤP RIÊNG kèm md5: chạy lại draft ghi đè original/ không làm lệch nhãn.

Chạy:  venv/bin/python tests/test_image_golden.py
"""
import json
import sys
import tempfile
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_eval                                             # noqa: E402
import image_golden_sample                                    # noqa: E402
import state_paths                                            # noqa: E402


def _image(**k):
    a = {"id": "A1", "source": "commons", "uses": ["thân"], "relevant": True, "notes": []}
    a.update(k)
    return a


def _make_state(root: Path, drafts: dict) -> Path:
    """drafts = {draft_id: [image dict, ...]} -> state/dcgr/prepare/<draft>/manifest.json + original/*.png"""
    for draft_id, images in drafts.items():
        wd = root / "dcgr" / state_paths.PREPARE_DIR / draft_id
        (wd / state_paths.ORIGINAL_DIR).mkdir(parents=True)
        anh = []
        for i, a in enumerate(images, 1):
            goc = wd / state_paths.ORIGINAL_DIR / f"A{i}.png"
            Image.new("RGB", (1200, 800), (i * 20 % 255, 80, 120)).save(goc)
            anh.append(dict(a, id=f"A{i}", original_path=str(goc)))
        (wd / state_paths.MANIFEST_FILE).write_text(json.dumps({
            "version": 2, "draft_id": draft_id, "title": draft_id, "title_en": draft_id.upper(),
            "material": {"lead_paragraph": "lead " * 400}, "images": anh}), encoding="utf-8")
    return root


# --------------------------------------------- 1. quyết định engine = công thức schema
def test_system_kept_matches_schema_formula():
    import schema
    imgs = [_image(), _image(relevant=False), _image(uses=[]),
            _image(faces=1, alt=""), _image(faces=1, alt="Jack Clark, co-founder of Anthropic")]
    kept = [image_eval.system_kept(a) for a in imgs]
    assert kept == [True, False, False, False, True], kept
    for a in imgs:
        assert image_eval.system_kept(a) == (schema.count_image_use_ok([a], "ethan") == 1)


def test_drop_reason_separates_capture_quality_from_vision():
    assert image_eval.drop_reason(_image(relevant=False, capture_source=True)) == "capture_quality"
    assert image_eval.drop_reason(_image(relevant=False)) == "vision_not_relevant"
    assert image_eval.drop_reason(_image(faces=2, alt="")) == "unnamed_face"
    assert image_eval.drop_reason(_image()) == "kept"


def test_evaluate_counts_wrong_drop_and_junk_pass():
    samples = [{"id": "a", "image": _image(relevant=False)},          # tốt mà bỏ -> loại oan
               {"id": "b", "image": _image()},                         # rác mà giữ -> lọt rác
               {"id": "c", "image": _image()},                         # tốt, giữ
               {"id": "d", "image": _image(relevant=False)},          # rác, bỏ
               {"id": "e", "image": _image()}]                         # chưa nhãn
    labels = [{"id": "a", "usable": "yes"}, {"id": "b", "usable": "no", "defect": "wrong_meaning"},
              {"id": "c", "usable": "yes"}, {"id": "d", "usable": "no"}, {"id": "zz", "usable": "yes"}]
    r = image_eval.evaluate(samples, labels)
    assert r["total"]["yes_dropped"] == 1 and r["total"]["no_kept"] == 1
    assert [x[0] for x in r["wrongly_dropped"]] == ["a"]
    assert [x[0] for x in r["junk_kept"]] == ["b"]
    assert r["unlabeled"] == 1
    report = image_eval.format_report(r)
    assert "LOẠI OAN: 1/2 = 50%" in report and "LỌT RÁC: 1/2 = 50%" in report


# --------------------------------------------- 2. chọn mẫu
def test_sample_is_deterministic_keeps_must_drafts_and_caps_per_draft():
    with tempfile.TemporaryDirectory() as tmp:
        state = _make_state(Path(tmp), {
            "must-draft": [_image(), _image(relevant=False)],
            "big-draft": [_image(relevant=False, source="web_yandex") for _ in range(9)],
            "other-draft": [_image(source="báo khác"), _image(source="bao khac", relevant=False)],
        })
        cands = image_golden_sample.load_candidates(state)
        assert len(cands) == 13
        one = image_golden_sample.stratified_sample(cands, 8, ["must-draft"], seed=3, per_draft_cap=4)
        two = image_golden_sample.stratified_sample(cands, 8, ["must-draft"], seed=3, per_draft_cap=4)
        assert [c["id"] for c in one] == [c["id"] for c in two], "cùng seed phải ra cùng mẫu"
        ids = [c["id"] for c in one]
        assert "dcgr/must-draft/A1" in ids and "dcgr/must-draft/A2" in ids
        assert sum(1 for i in ids if "/big-draft/" in i) <= 4
        assert len(ids) == len(set(ids))


def test_sample_never_exceeds_available():
    with tempfile.TemporaryDirectory() as tmp:
        state = _make_state(Path(tmp), {"d1": [_image(), _image(relevant=False)]})
        cands = image_golden_sample.load_candidates(state)
        assert len(image_golden_sample.stratified_sample(cands, 300)) == 2


def test_load_candidates_reads_v1_manifest_with_new_keys():
    """LOW-227: manifest.json bản 1 (khoá Việt) chưa migrate vẫn ra mẫu khoá English."""
    with tempfile.TemporaryDirectory() as tmp:
        wd = Path(tmp) / "dcgr" / state_paths.PREPARE_DIR / "d1"
        (wd / state_paths.ORIGINAL_DIR).mkdir(parents=True)
        goc = wd / state_paths.ORIGINAL_DIR / "A1.png"
        Image.new("RGB", (1200, 800), (10, 80, 120)).save(goc)
        (wd / state_paths.MANIFEST_FILE).write_text(json.dumps({
            "phien_ban": 1, "draft_id": "d1", "title": "d1", "tieu_de_en": "D1",
            "tu_lieu": {"doan_dau": "lead"},
            "anh": [{"ma": "A1", "goc": str(goc), "tu": "commons", "dung": ["thân"],
                     "lien_quan": True, "ghi_chu": [], "khai_niem": {"tu_khoa": "flag"}}]}),
            encoding="utf-8")
        cands = image_golden_sample.load_candidates(Path(tmp))
        assert [c["id"] for c in cands] == ["dcgr/d1/A1"], cands
        assert cands[0]["image"] == {"id": "A1", "source": "commons", "uses": ["thân"], "relevant": True,
                                     "notes": [], "concept": {"keyword": "flag"}}, cands[0]["image"]
        assert cands[0]["story"]["title_en"] == "D1" and cands[0]["story"]["lead"] == "lead"


# --------------------------------------------- 3. chụp riêng ảnh
def test_snapshot_copies_image_so_rerun_cannot_shift_labels():
    with tempfile.TemporaryDirectory() as tmp:
        state = _make_state(Path(tmp), {"d1": [_image()]})
        cands = image_golden_sample.load_candidates(state)
        path = image_golden_sample.write_snapshot(cands, Path(tmp) / "golden" / "v0")
        row = json.loads(path.read_text(encoding="utf-8").splitlines()[0])
        thumb = path.parent / row["thumb"]
        assert thumb.is_file() and max(Image.open(thumb).size) <= image_golden_sample.THUMB_MAX
        # Chạy lại draft ghi đè original/A1.png: ảnh chụp riêng và md5 không đổi theo.
        before = thumb.read_bytes()
        Image.new("RGB", (900, 900), (0, 0, 0)).save(cands[0]["goc"])
        assert thumb.read_bytes() == before
        assert row["md5"] and row["story"]["title_en"] == "D1"
        assert len(row["story"]["lead"]) <= image_golden_sample.LEAD_CHARS


def test_main_refuses_to_overwrite_existing_version():
    with tempfile.TemporaryDirectory() as tmp:
        state = _make_state(Path(tmp), {"d1": [_image()]})
        assert image_golden_sample.main(["--version", "v0", "--state", str(state)]) == 0
        assert image_golden_sample.main(["--version", "v0", "--state", str(state)]) == 1


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
