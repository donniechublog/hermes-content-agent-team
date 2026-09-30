#!/usr/bin/env python3
"""LOW-440: cong "LAM LAI" cua Kite chi ap khi Ong Chu THAT SU bam Lam lai.

previous_submission.json duoc ghi o MOI lan gui (submit_common.send_album), nen "co
da_dung" chi co nghia la da nop mot lan. Dre/Ethan da co moc `remakes`
(submit_common.check_redo_reused, sua 06/09/2026); kite_submit._check_redo thi khong —
kanban retry / worker chet giua chung (LOW-134) la Kite bi bat "hook bia giong lan
truoc", phai doi hook roi gui bo thu hai kem nut Duyet thu hai.

Chay:  venv/bin/python tests/test_low440_kite_redo_remakes_gate.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import kite_submit                                              # noqa: E402
import submit_common as nc                                      # noqa: E402

SPEC = {"theme": "dark", "hero": "H1", "slides": [{"kind": "cover", "title": "Hook cũ"}]}
PREV = {"theme": "dark", "hero": "H1", "hook": "Hook cũ", "remakes": 0}


def _with_redo(so_lan, fn):
    cu = nc.count_of_redo
    nc.count_of_redo = lambda _id: so_lan
    try:
        return fn()
    finally:
        nc.count_of_redo = cu


def test_chay_lai_khong_bam_lam_lai_thi_khong_bat():
    """Ong Chu chua bam lan nao (remakes trong img.json = 0, da_dung ghi luc 0):
    y het lan truoc van qua — day la nhanh kanban retry / LOW-134."""
    def run():
        loi = []
        kite_submit._check_redo(SPEC, PREV, "Hook cũ", loi, draft_id="d1")
        assert loi == [], loi
        loi = []
        kite_submit._check_redo(SPEC, PREV, "Hook cũ", loi, theme_locked=True, draft_id="d1")
        assert loi == [], loi
    _with_redo(0, run)


def test_ong_chu_bam_lam_lai_thi_van_bat_nhu_cu():
    """remakes 0 -> 1: giu nguyen theme/hero + hook thi PHAI bat ca hai."""
    def run():
        loi = []
        kite_submit._check_redo(SPEC, PREV, "Hook cũ", loi, draft_id="d1")
        assert len(loi) == 2 and any("hook" in x for x in loi) and any("theme" in x for x in loi), loi
        # doi ca hai thi qua
        loi = []
        kite_submit._check_redo({**SPEC, "hero": "H2"}, PREV, "Hook mới", loi, draft_id="d1")
        assert loi == [], loi
    _with_redo(1, run)


def test_da_dung_cu_khong_co_remakes_thi_giu_hanh_vi_cu():
    """previous_submission.json ghi truoc khi co moc remakes: khong biet Ong Chu da bam
    chua -> van bat (cung cach check_redo_reused xu ly, `remakes` mac dinh -1)."""
    def run():
        loi = []
        kite_submit._check_redo(SPEC, {k: v for k, v in PREV.items() if k != "remakes"},
                                "Hook cũ", loi, draft_id="d1")
        assert len(loi) == 2, loi
    _with_redo(0, run)


def test_khong_truyen_draft_id_thi_khong_doi_moc():
    """Goi kieu cu (test_low340) van bat: moc chi bat khi biet draft_id."""
    def run():
        loi = []
        kite_submit._check_redo(SPEC, PREV, "Hook cũ", loi)
        assert len(loi) == 2, loi
    _with_redo(0, run)


def test_main_truyen_draft_id_vao_cong():
    src = (ROOT / "kite_submit.py").read_text(encoding="utf-8")
    goi = [d for d in src.split("\n") if "_check_redo(spec, da_dung" in d]
    assert goi and "draft_id=a.draft_id" in src.split("_check_redo(spec, da_dung", 1)[1][:200], goi


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
