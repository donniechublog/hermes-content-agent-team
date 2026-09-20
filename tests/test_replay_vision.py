#!/usr/bin/env python3
"""LOW-312 — phat lai cau tra loi vision THAT qua code THAT.

Ban ghi: 11 cap (cau hoi, cau tra loi) cua tin "Gartner du bao chi tieu AI tang
49,5%" (dcgr, 20/09/2026), thu tu `vision_raw` trong manifest production bang
`tests/replay.py harvest-vision`. Anh la THE CHO dung kich thuoc (khong giu anh
ben thu ba trong repo) — xem docstring tests/replay.py.

Hai luoi:
  1. `description_image`: cau tra loi that -> DUNG cac truong ma production da
     ghi vao manifest (relevant, subject_box, subject_kind, empty_share...). Sua
     regex parse ma lam lech mot truong la do o day, khong doi toi luc chay that.
  2. `classify` (do phuc tap 69, ham dau tien LOW-312 muon tach): chup KET QUA
     cho 11 anh x {chup_nguon co/khong} vao `classify_snapshot.json`. Tach ham
     = chay lai, 0 lech moi duoc commit. Co y doi hanh vi thi:
         venv/bin/python tests/test_replay_vision.py --write-snapshot
     va giai thich phan lech trong PR.

Chay:  venv/bin/python tests/test_replay_vision.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "prepare"))
sys.path.insert(0, str(ROOT / "tests"))

import replay                          # noqa: E402
import role                            # noqa: E402
import vision                          # noqa: E402

RECORDINGS = replay.GOLDEN / "replay" / "vision_gartner_spending.json"
SNAPSHOT = replay.GOLDEN / "replay" / "classify_snapshot.json"
GOLD = json.loads(RECORDINGS.read_text(encoding="utf-8"))
TITLE = "Gartner Forecasts Worldwide AI Spending to Grow 49.5% in 2026"
PARSED_FIELDS = ("cluttered", "has_keywords", "subject_box", "subject_kind", "empty_share",
                 "printed_name")


class _Replayed:
    """with _Replayed() as (rp, tmp): vision noi voi ban ghi, khong ra mang."""

    def __enter__(self):
        self.rp = replay.VisionReplay.load(RECORDINGS)
        self.undo = self.rp.install(vision, os.environ)
        self.tmp = Path(tempfile.mkdtemp(prefix="replay_vision_"))
        return self.rp, self.tmp

    def __exit__(self, *exc):
        self.undo()
        return False


def _stand_in(tmp, rec):
    return replay.stand_in_image(tmp / f"{rec['id']}.png", rec["number"], rec["w"], rec["h"])


def test_real_answers_parse_to_the_fields_production_wrote():
    with _Replayed() as (rp, tmp):
        for rec in GOLD["recordings"]:
            found = {}
            description, relevant = vision.description_image(_stand_in(tmp, rec), TITLE,
                                                             ket_qua=found)
            want = rec["expected"]
            assert relevant is want["relevant"], (rec["id"], relevant)
            assert description == want["description"], rec["id"]
            for k in PARSED_FIELDS:
                assert found.get(k) == want[k], (rec["id"], k, found.get(k), want[k])
            assert found["vision_raw"]["answer"] == rec["answer"]
        assert rp.misses == [] and len(rp.calls) == len(GOLD["recordings"])


def test_recordings_cover_both_verdicts_and_every_subject_kind_seen():
    """Bo ban ghi phai con du da dang, khong thi luoi chi con bat duoc mot nhanh."""
    verdicts = {r["expected"]["relevant"] for r in GOLD["recordings"]}
    kinds = {r["expected"]["subject_kind"] for r in GOLD["recordings"]}
    assert verdicts == {True, False}
    assert {"logo", "person", "chart", "building"} <= kinds, kinds


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
        tmp = Path(tempfile.mkdtemp(prefix="replay_vision_"))
        found = {}
        _, relevant = vision.description_image(_stand_in(tmp, rec), TITLE, ket_qua=found)
        assert relevant is False and found["override"] == "unparsed_twice_forced_false"
        assert len(rp.calls) == 2, "hoi lai DUNG mot lan"
    finally:
        undo()


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
