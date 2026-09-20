#!/usr/bin/env python3
"""LOW-312 — luoi cho phan TRANG THAI + HANG RAO CHONG SAP cua `scan_models.py`.

Vi sao chon dung phan nay: `scan_models` chay hang ngay cho Nova (do 20/09/2026:
`nova_20260920` co bao cao that, `brief_nova` goi script nay moi luot quet), nhung
do phu chi 16%. Phan CON LAI cua tep — 14 ham `fetch_*` — doc trang cua ben thu ba;
repo nay CONG KHAI nen khong dua noi dung do vao. Con doan duoi day thi khong can
mot byte nao cua ai: no la bo nho giua hai lan quet va cac hang rao giu cho mot
nguon hong khong keo do ca luot.

Moi kich ban dung theo mot su co DA GHI trong chinh comment cua code:
  - `_try`: parse loi (khong phai loi mang) nem thang ra main, giet ca 22 bang,
    roi `brief_nova` van dung bao cao rong -> Nova ket luan "hom nay khong co gi".
  - `write_timestamp`: mot bang tam tra rong ghi de moc cu -> lan sau khong con
    moc de so, "leo hang" im lang bien mat.
  - `read_state`: tep moc hong lam MOI lan chay sau do chet, va theo cron thi
    khong ai duoc bao.
  - `count_rank`: lan dau (chua co moc) khong duoc bao ca bang la "moi".

Chay:  venv/bin/python tests/test_scan_models_state.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import scan_models as sm               # noqa: E402


class _State:
    """Tro `scan_models.STATE` vao tep tam; tra lai khi xong."""

    def __init__(self, noi_dung=None):
        self.noi_dung = noi_dung

    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="scan_models_"))
        self.old, sm.STATE = sm.STATE, self.tmp / "models_seen.json"
        if self.noi_dung is not None:
            sm.STATE.write_text(self.noi_dung if isinstance(self.noi_dung, str)
                                else json.dumps(self.noi_dung), encoding="utf-8")
        self.old_hong, sm._HONG_KHAC[:] = list(sm._HONG_KHAC), []
        return self

    def __exit__(self, *exc):
        sm.STATE = self.old
        sm._HONG_KHAC[:] = self.old_hong
        return False

    def read(self):
        return json.loads(sm.STATE.read_text(encoding="utf-8"))


# =========================================================================
# _try — mot nguon hong khong duoc keo do ca luot quet
# =========================================================================
def test_parse_error_in_one_source_does_not_kill_the_scan():
    """Cac try rieng cua tung fetcher chi boc LOI GOI MANG. `float("-")` cua
    livebench, `r["codingIndex"]` thieu khoa... nam NGOAI try do."""
    with _State():
        assert sm._try("livebench", lambda: float("-"), khi_hong=([], {})) == ([], {})
        assert sm._try("aa", lambda: {"x": 1}["codingIndex"], khi_hong={}) == {}
        assert sm._try("opencompass", lambda: 1 < None, khi_hong=([], {})) == ([], {})
        assert sm._HONG_KHAC == ["livebench", "aa", "opencompass"]


def test_working_source_passes_its_value_through_untouched():
    with _State():
        sentinel = {"text": [{"name": "M", "rank": 1}]}
        assert sm._try("arena", lambda: sentinel, khi_hong={}) is sentinel
        assert sm._HONG_KHAC == []


def test_broken_source_is_named_so_the_report_can_say_which():
    """`broken_boards` chi bat duoc fetcher tra RONG, khong bat duoc fetcher NEM —
    nen ten phai vao `_HONG_KHAC`, khong thi nguon do bien mat khoi bao cao."""
    with _State():
        sm._try("tbench", lambda: (_ for _ in ()).throw(KeyError("accuracy")), khi_hong=([], {}))
        assert sm._HONG_KHAC == ["tbench"]


# =========================================================================
# read_state — moc hong khong duoc lam ket day chuyen
# =========================================================================
def test_corrupt_state_is_renamed_and_the_scan_continues_with_an_empty_mark():
    with _State("{ cat ngang"):
        assert sm.read_state() == {}
        assert sm.STATE.with_suffix(".json.hong").exists(), "phai giu lai ban hong de soi"
        assert not sm.STATE.exists()


def test_missing_state_is_simply_empty():
    with _State():
        assert sm.read_state() == {} and sm.already_see() == set()
        assert sm.rank_old() == {} and sm.aa_already_report() == {}


def test_state_fields_are_read_back_as_written():
    with _State({"ids": ["a", "b"], "rankings": {"text": {"M": 3}},
                 "aa_reported": {"M": "2026-09-01"}}):
        assert sm.already_see() == {"a", "b"}
        assert sm.rank_old() == {"text": {"M": 3}}
        assert sm.aa_already_report() == {"M": "2026-09-01"}


# =========================================================================
# write_timestamp — bang tam rong khong duoc xoa moc cu
# =========================================================================
def test_empty_board_keeps_the_previous_mark_instead_of_wiping_it():
    """Su co 06/09/2026: bang tam hong (fetch tra []) ghi de bo nho xep hang
    bang rong -> lan sau khong con moc de so, "leo hang" im lang bien mat."""
    with _State({"ids": [], "rankings": {"text": {"M": 1}, "code": {"N": 2}}}) as st:
        sm.write_timestamp({"x"}, {"text": {}, "code": {"N": 1}})
        r = st.read()["rankings"]
        assert r["text"] == {"M": 1}, "bang rong DA XOA moc cu"
        assert r["code"] == {"N": 1}, "bang co du lieu phai duoc cap nhat"


def test_new_board_is_added_and_ids_are_sorted():
    with _State({"ids": ["b"], "rankings": {}}) as st:
        sm.write_timestamp({"b", "a"}, {"moi": {"M": 1}})
        d = st.read()
        assert d["ids"] == ["a", "b"]
        assert d["rankings"] == {"moi": {"M": 1}}
        assert d["updated_at"].endswith("+00:00")


def test_reported_models_default_to_what_was_already_there():
    """Moi model AA bao dung mot lan — quen mang `aa_reported` sang la bao lai."""
    with _State({"ids": [], "rankings": {}, "aa_reported": {"M": "2026-09-01"}}) as st:
        sm.write_timestamp(set(), {})
        assert st.read()["aa_reported"] == {"M": "2026-09-01"}
        sm.write_timestamp(set(), {}, da_bao={"M": "2026-09-01", "N": "2026-09-20"})
        assert st.read()["aa_reported"] == {"M": "2026-09-01", "N": "2026-09-20"}


def test_state_write_leaves_no_temp_file_behind():
    with _State({"ids": [], "rankings": {}}):
        sm.write_timestamp({"a"}, {"text": {"M": 1}})
        assert sorted(p.name for p in sm.STATE.parent.iterdir()) == ["models_seen.json"]


# =========================================================================
# count_rank — bat model VUA LEO HANG
# =========================================================================
def test_first_ever_scan_does_not_announce_the_whole_board_as_new():
    """Chua co moc cu cho bang do -> im. Khong thi lan quet dau tien bao ca bang."""
    arena = {"text": [{"name": "A", "rank": 1}, {"name": "B", "rank": 2}]}
    assert sm.count_rank(arena, {}) == []
    assert sm.count_rank(arena, {"text": {}}) == []


def test_model_entering_an_existing_board_is_news():
    arena = {"text": [{"name": "A", "rank": 1}, {"name": "MOI", "rank": 3}]}
    ra = sm.count_rank(arena, {"text": {"A": 1}})
    assert [(r["name"], r["previous_rank"], r["climb"]) for r in ra] == [("MOI", None, None)]
    assert ra[0]["note"] == "MOI vao bang, thang hang #3" and ra[0]["board"] == "text"


def test_only_climbs_are_reported_never_drops_or_standing_still():
    arena = {"text": [{"name": "LEN", "rank": 2}, {"name": "XUONG", "rank": 9},
                      {"name": "YEN", "rank": 5}]}
    cu = {"text": {"LEN": 7, "XUONG": 3, "YEN": 5}}
    ra = sm.count_rank(arena, cu)
    assert [r["name"] for r in ra] == ["LEN"]
    assert (ra[0]["previous_rank"], ra[0]["climb"]) == (7, 5)
    assert ra[0]["note"] == "leo 5 bac: #7 -> #2"


def test_new_entries_currently_lead_over_climbers_PIN():
    """GHIM hanh vi hien tai, KHONG sua trong ticket nay.

    Comment trong code noi "leo nhieu bac nhat len dau; model moi vao bang xep
    theo hang". Thuc te nguoc lai: khoa sap la `(-(climb or 99), rank)`, ma model
    moi co `climb is None` -> `99` -> `-99`, nho hon `-18` cua model leo 18 bac —
    nen MODEL MOI LUON DUNG TRUOC moi model leo duoi 99 bac.

    Docstring cua chinh ham lai ung ho thu tu nay ("vao thang top 3 la tin"), nen
    chua ro day la loi hay comment cu. Nguong lat dung o 99 bac, mot artifact cua
    so canh `or 99` chu khong phai con so ai chon. Ghim de sau nay ai sua thi
    phai sua co y thuc, ca code lan comment."""
    arena = {"a": [{"name": "LEO_IT", "rank": 4}, {"name": "LEO_NHIEU", "rank": 2}],
             "b": [{"name": "MOI_SAU", "rank": 8}, {"name": "MOI_TRUOC", "rank": 3}]}
    cu = {"a": {"LEO_IT": 5, "LEO_NHIEU": 20}, "b": {"CU": 1}}
    assert [r["name"] for r in sm.count_rank(arena, cu)] == [
        "MOI_TRUOC", "MOI_SAU", "LEO_NHIEU", "LEO_IT"]

    # nguong lat o 99 bac: phai leo hon 99 bac moi vuot duoc mot model moi
    xa = {"a": [{"name": "LEO_RAT_XA", "rank": 1}], "b": [{"name": "MOI", "rank": 2}]}
    assert [r["name"] for r in sm.count_rank(xa, {"a": {"LEO_RAT_XA": 101}, "b": {"CU": 1}})] == [
        "LEO_RAT_XA", "MOI"]


def test_each_board_is_compared_against_its_own_history():
    """Cung ten model o hai bang khac nhau khong duoc lan sang nhau."""
    arena = {"text": [{"name": "M", "rank": 5}], "code": [{"name": "M", "rank": 5}]}
    ra = sm.count_rank(arena, {"text": {"M": 9}, "code": {"M": 2}})
    assert [(r["board"], r["climb"]) for r in ra] == [("text", 4)]


# =========================================================================
# region_of — phan vung nha lam model (uu tien Ong Chu chot)
# =========================================================================
def test_region_split_drives_the_us_versus_china_priority():
    vung = {org: sm.region_of(org) for org in
            ("openai", "anthropic", "google", "deepseek", "alibaba", "moonshot", "khong-ai-biet")}
    assert vung["openai"] == vung["anthropic"] == vung["google"]
    assert vung["deepseek"] == vung["alibaba"] == vung["moonshot"]
    assert vung["openai"] != vung["deepseek"], "My va Trung phai tach nhau"
    assert sm.region_of("") == sm.region_of("khong-ai-biet")


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
