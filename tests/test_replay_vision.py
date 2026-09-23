#!/usr/bin/env python3
"""LOW-312 — phat lai cau tra loi vision THAT qua code THAT.

Ban ghi: 22 cap (cau hoi, cau tra loi) cua tin "Google confirms Gemini models hacked
three companies in May 2026" (blog, 22/09/2026), thu tu `vision_raw` bang
`tests/replay.py harvest-vision`. LOW-363 (dong PHIEN_BAN) va LOW-337 (dong AI slop)
doi cau hoi vision nen ban ghi Gartner cu (LOW-312, dcgr 20/09) het khop; thu dap lai
tren may chu bang code da gop (/tmp, khong dung production), `call` dung lai tu cau hoi
va tu kiem bang cach sinh lai cau hoi (khop tuyet doi); bo ban ghi bi vong sau lat
`relevant`. Dong PHIEN_BAN khoa qua A20/A22/A23 (Gemini 3.1/3.8/3.5). Anh la THE CHO
dung kich thuoc (khong giu anh ben thu ba trong repo) — xem docstring tests/replay.py.

Hai luoi:
  1. `description_image`: cau tra loi that -> DUNG cac truong ma production da
     ghi vao manifest (relevant, subject_box, subject_kind, empty_share...). Sua
     regex parse ma lam lech mot truong la do o day, khong doi toi luc chay that.
  2. `classify` (do phuc tap 69, ham dau tien LOW-312 muon tach): chup KET QUA
     cho moi anh x {chup_nguon co/khong} vao `classify_snapshot.json`. Tach ham
     = chay lai, 0 lech moi duoc commit. Co y doi hanh vi thi:
         venv/bin/python tests/test_replay_vision.py --write-snapshot
     va giai thich phan lech trong PR.

Chay:  venv/bin/python tests/test_replay_vision.py
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "prepare"))
sys.path.insert(0, str(ROOT / "tests"))

import replay                          # noqa: E402
import role                            # noqa: E402
import vision                          # noqa: E402
import tam  # noqa: E402

RECORDINGS = replay.GOLDEN / "replay" / "vision_gemini_hack.json"
SNAPSHOT = replay.GOLDEN / "replay" / "classify_snapshot.json"
GOLD = json.loads(RECORDINGS.read_text(encoding="utf-8"))
TITLE = GOLD["title"]
PARSED_FIELDS = ("cluttered", "has_keywords", "subject_box", "subject_kind", "empty_share",
                 "printed_name", "printed_version", "ai_slop")


class _Replayed:
    """with _Replayed() as (rp, tmp): vision noi voi ban ghi, khong ra mang."""

    def __enter__(self):
        self.rp = replay.VisionReplay.load(RECORDINGS)
        self.undo = self.rp.install(vision, os.environ)
        self.tmp = Path(tam.temp_dir(prefix="replay_vision_"))
        return self.rp, self.tmp

    def __exit__(self, *exc):
        self.undo()
        return False


def _stand_in(tmp, rec):
    return replay.stand_in_image(tmp / f"{rec['id']}.png", rec["number"], rec["w"], rec["h"])


def _ask(tmp, rec, **kw):
    """Goi `description_image` DUNG bo tham so production da dung cho ban ghi nay
    (`rec["call"]`). Goi sai bo do thi cau hoi sinh ra khac cau hoi da ghi, va
    test tut xuong chi con kiem phan boc cau tra loi — xem `drifted`."""
    return vision.description_image(_stand_in(tmp, rec), TITLE, **{**rec["call"], **kw})


def test_real_answers_parse_to_the_fields_production_wrote():
    with _Replayed() as (rp, tmp):
        for rec in GOLD["recordings"]:
            found = {}
            description, relevant = _ask(tmp, rec, ket_qua=found)[:2]
            want = rec["expected"]
            assert relevant is want["relevant"], (rec["id"], relevant)
            assert description == want["description"], rec["id"]
            for k in PARSED_FIELDS:
                assert found.get(k) == want[k], (rec["id"], k, found.get(k), want[k])
            assert found["vision_raw"]["answer"] == rec["answer"]
        assert rp.misses == [] and len(rp.calls) == len(GOLD["recordings"])
        assert rp.drifted == [], (
            "CAU HOI hom nay khac cau hoi trong ban ghi — ban ghi da cu. Doc "
            "`drifted[0]['question']` so voi ban ghi, roi thu lai bang "
            "`tests/replay.py harvest-vision` tu mot manifest production moi.")


def test_recordings_cover_both_verdicts_and_every_subject_kind_seen():
    """Bo ban ghi phai con du da dang, khong thi luoi chi con bat duoc mot nhanh."""
    verdicts = {r["expected"]["relevant"] for r in GOLD["recordings"]}
    kinds = {r["expected"]["subject_kind"] for r in GOLD["recordings"]}
    assert verdicts == {True, False}
    # LOW-363: bo ban ghi Gemini khong con "building" (tin model co y khong lay tru so hang
    # me, LOW-354) va "chart" (bang benchmark deu bi cong phien ban lat relevant nen khong
    # so duoc o tang description_image); screen/product thay vao.
    assert {"logo", "person", "screen", "product"} <= kinds, kinds
    assert any(r["expected"].get("printed_version") for r in GOLD["recordings"])   # khoa dong PHIEN_BAN


def test_missing_recording_is_loud_not_a_silent_unseen_image():
    """`description_image` nuot moi Exception thanh None ("CHUA AI NHIN") — nen
    thieu ban ghi phai lo ra o `misses`, khong thi test xanh nho nhanh fail-open."""
    with _Replayed() as (rp, tmp):
        stranger = replay.stand_in_image(tmp / "stranger.png", 999, 640, 480)
        _, relevant = vision.description_image(stranger, TITLE)
        assert relevant is None
        assert [m["number"] for m in rp.misses] == [999]


def test_unparsable_answer_is_asked_again_once_then_forced_false():
    """12/09/2026: router TRA LOI duoc nhung khong doc ra LIEN_QUAN -> truoc day
    thanh None va DUOC COI LA DUYET (anh Tesla, logo Anthropic lot bia)."""
    rec = dict(GOLD["recordings"][0], answer="Toi khong chac day la gi.")
    rp = replay.VisionReplay([rec])
    undo = rp.install(vision, os.environ)
    try:
        tmp = Path(tam.temp_dir(prefix="replay_vision_"))
        found = {}
        _, relevant = _ask(tmp, rec, ket_qua=found)[:2]
        assert relevant is False and found["override"] == "unparsed_twice_forced_false"
        assert len(rp.calls) == 2, "hoi lai DUNG mot lan"
    finally:
        undo()


def test_drift_detector_actually_fires_when_the_prompt_changes():
    """Khang dinh `drifted == []` chi co nghia neu bo phat hien troi THAT SU keu.
    Doi cau hoi trong ban ghi = gia bo "ai do vua sua prompt vision": phai van
    phat lai duoc (khop theo ANH), nhung phai bao troi."""
    rec = dict(GOLD["recordings"][0])
    rec["question"] = rec["question"].replace("Tra loi DUNG", "Tra loi (moi) DUNG")
    rp = replay.VisionReplay([rec])
    undo = rp.install(vision, os.environ)
    try:
        tmp = Path(tam.temp_dir(prefix="replay_vision_"))
        description, _ = _ask(tmp, rec)[:2]
        assert description == rec["expected"]["description"], "van phai phat lai duoc"
        assert rp.misses == []
        assert [d["number"] for d in rp.drifted] == [rec["number"]], "KHONG bao troi"
    finally:
        undo()


def test_harvest_reads_only_images_the_engine_actually_asked_about():
    """`harvest_vision` la thu LAM RA ban ghi — no sai thi moi fixture sau deu sai.
    Manifest that co ca anh CHUA hoi vision, va vai phien ban ghi `vision_raw`
    duoi dang repr(dict) chu khong phai JSON."""
    raw = {"model": "m", "question": "hoi?", "answer": "MO_TA: x\nLIEN_QUAN: co"}
    manifest = {"brand": "dcgr", "draft_id": "d1", "created_at": "2026-09-20", "title": "T",
                "images": [
                    {"id": "A1", "w": 10, "h": 20, "source": "other_outlet",
                     "vision_raw": raw, "relevant": True, "description": "x",
                     "cluttered": False, "has_keywords": False, "subject_box": None,
                     "subject_kind": "logo", "empty_share": 0.1, "printed_name": None},
                    {"id": "A2", "w": 1, "h": 1},                      # chua hoi vision
                    {"id": "A3", "w": 3, "h": 4, "vision_raw": repr(raw)},   # repr(dict)
                    {"id": "A4", "w": 5, "h": 6, "vision_raw": "khong phai dict"},
                ]}
    p = Path(tam.temp_dir()) / "manifest.json"
    p.write_text(json.dumps(manifest), encoding="utf-8")

    out = replay.harvest_vision(p)
    assert [r["id"] for r in out["recordings"]] == ["A1", "A3"], out["recordings"]
    assert out["source"] == "dcgr/d1 (2026-09-20)" and out["title"] == "T"
    a1 = out["recordings"][0]
    assert (a1["number"], a1["w"], a1["h"]) == (1, 10, 20), "so thu tu tinh tren CA danh sach"
    assert a1["expected"]["subject_kind"] == "logo" and a1["question"] == "hoi?"
    assert out["recordings"][1]["number"] == 3, "A3 phai giu so thu tu 3, khong phai 2"

    chon = replay.harvest_vision(p, {"A3"})
    assert [r["id"] for r in chon["recordings"]] == ["A3"]


def _classify_all():
    role.set_active_role("dre")                  # tin that la bai cua Dre (LOW-182)
    out = {}
    with _Replayed() as (rp, tmp):
        for rec in GOLD["recordings"]:
            for from_source in (False, True):
                path = _stand_in(tmp, rec)
                image = {"id": rec["id"], "original_path": str(path), "source": rec["source"],
                         "url": f"https://example.test/{rec['id']}.png"}
                got = vision.classify(image, tmp, TITLE, chup_nguon=from_source)
                got = json.loads(json.dumps(got, ensure_ascii=False, default=str))
                for k in ("original_path", "ready_path"):           # duong dan tmp doi moi lan
                    if got.get(k):
                        got[k] = Path(got[k]).name
                got.pop("vision_raw", None)
                out[f"{rec['id']}{'+source' if from_source else ''}"] = got
        assert rp.misses == [], rp.misses
    return out


def test_classify_matches_snapshot():
    want = json.loads(SNAPSHOT.read_text(encoding="utf-8"))
    got = _classify_all()
    assert sorted(got) == sorted(want)
    for key in want:
        diff = {f: (want[key].get(f), got[key].get(f))
                for f in set(want[key]) | set(got[key]) if want[key].get(f) != got[key].get(f)}
        assert not diff, f"{key} lech snapshot: {diff}"


if __name__ == "__main__":
    if "--write-snapshot" in sys.argv:
        SNAPSHOT.write_text(json.dumps(_classify_all(), ensure_ascii=False, indent=1,
                                       sort_keys=True) + "\n", encoding="utf-8")
        print(f"da ghi {SNAPSHOT}")
        sys.exit(0)
    from tam import chay_tat_ca
    chay_tat_ca(globals())
