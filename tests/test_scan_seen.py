#!/usr/bin/env python3
"""LOW-375 — luoi cho `scan_seen.SeenStore`, kho nho da-thay dung chung.

Moi test duoi day khoa MOT trong sau luat o docstring cua `scan_seen`, va moi
luat la mot su co da xay ra that:

  - cat theo bang chu cai (`sorted(khoa)[-2000:]` cua scan_business ban cu):
    tin bat dau a-m bi day ra khoi bo nho va bao lai mai.
  - ghi de ca tep: xoa mat `note` cua business_seen (26/08), va se xoa mat
    `ids`/`rankings`/`aa_reported` cua models_seen neu Nova dung lop nay ma
    lop khong giu truong la.
  - danh dau ca phan bi `--top` cat: van an toan thanh may xoa tin.
  - tep hong im lang tra {}: lan ghi ngay sau do xoa sach kho that.

Chay:  venv/bin/python tests/test_scan_seen.py
"""
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import scan_seen                                             # noqa: E402
import tam  # noqa: E402


def _store(noi_dung=None, **kw):
    tmp = Path(tam.temp_dir(prefix="scan_seen_"))
    p = tmp / "seen.json"
    if noi_dung is not None:
        p.write_text(noi_dung if isinstance(noi_dung, str) else json.dumps(noi_dung),
                     encoding="utf-8")
    return scan_seen.SeenStore(p, **kw)


# =========================================================================
# Luat 1 — cat theo THOI GIAN, khong theo bang chu cai cung khong theo so
# =========================================================================
def test_prune_by_time_not_by_alphabet():
    """Vet seo: ban cu cat `sorted(khoa)[-2000:]` nen 'aaa' bi quen truoc 'zzz'
    du 'aaa' moi hon. Khoa MOI phai o lai bat ke chu cai dau."""
    kho = _store(keep_days=10)
    now = time.time()
    cu = now - 30 * 86400
    kho.mark(["zzz-tin-cu"], now=cu)
    kho.mark(["aaa-tin-moi"], now=now)
    con = kho.read()
    assert "aaa-tin-moi" in con, "khoa MOI bi cat — dang cat theo bang chu cai"
    assert "zzz-tin-cu" not in con, "khoa qua 10 ngay phai bi cat"


def test_item_inside_window_never_expires():
    """Luat 6: kho phai nho lau hon cua so quet. Muc 6 ngay tuoi trong cua so
    7 ngay cua Nova phai con nguyen."""
    kho = _store(keep_days=30)
    now = time.time()
    kho.mark(["tin-6-ngay"], now=now - 6 * 86400)
    assert "tin-6-ngay" in kho.read()


def test_keep_days_raised_to_twice_the_scan_window():
    """Khai keep_days ngan hon 2x cua so la tu ban chan: lop tu nang len."""
    kho = _store(keep_days=3, window_days=7)
    assert kho.keep_days == 14


# =========================================================================
# Luat 2 — doc tep cu, CHI thay truong cua minh
# =========================================================================
def test_other_fields_survive_a_write():
    """Vet seo 26/08: ghi de ca tep xoa mat `note` cua business_seen. Voi Nova
    con nang hon — `ids`/`rankings`/`aa_reported` nam CUNG tep."""
    kho = _store({"note": "ghi chu su co 26/08", "ids": ["a", "b"],
                  "rankings": {"text": {"M": 1}}, "aa_reported": {"X": "2026-09-01"}})
    kho.mark(["tin-moi"])
    d = json.loads(kho.path.read_text(encoding="utf-8"))
    assert d["note"] == "ghi chu su co 26/08"
    assert d["ids"] == ["a", "b"]
    assert d["rankings"] == {"text": {"M": 1}}
    assert d["aa_reported"] == {"X": "2026-09-01"}
    assert "tin-moi" in d["seen_at"]


def test_a_second_role_field_in_the_same_file_is_untouched():
    """Nova gan `seen_at` canh cac truong khac; hai kho khac `field` trong CUNG
    mot tep khong duoc dam nhau."""
    p = Path(tam.temp_dir(prefix="scan_seen_")) / "models_seen.json"
    hf = scan_seen.SeenStore(p, field="hf_seen")
    story = scan_seen.SeenStore(p, field="story_seen")
    hf.mark(["org/model-a"])
    story.mark(["https://example.com/x"])
    assert "org/model-a" in hf.read()
    assert "https://example.com/x" in story.read()
    assert "org/model-a" not in story.read()


# =========================================================================
# Luat 3 — danh dau LUC BAO, khong phai luc QUET
# =========================================================================
def test_only_marked_keys_are_filtered_out():
    """`mark` chi nhan thu DA DUA vao bao cao. Muc bi --top cat khong duoc
    truyen vao, va vi the hom sau van len duoc."""
    kho = _store()
    quet = [{"link": "a"}, {"link": "b"}, {"link": "c"}]
    da_bao = quet[:2]                      # 2 muc lot --top, 'c' bi cat
    kho.mark([it["link"] for it in da_bao])
    con, bo = kho.unseen(quet, key=lambda it: it["link"])
    assert [it["link"] for it in con] == ["c"], "muc bi cat phai con co hoi hom sau"
    assert bo == 2


def test_unseen_reads_the_store_once_and_counts_drops():
    kho = _store()
    kho.mark(["x", "y"])
    con, bo = kho.unseen([{"k": "x"}, {"k": "z"}], key=lambda it: it["k"])
    assert [it["k"] for it in con] == ["z"]
    assert bo == 1


# =========================================================================
# Luat 4 — tep hong: doi ten `.hong`, kho rong, noi to; KHONG im lang
# =========================================================================
def test_corrupt_file_is_renamed_and_does_not_wipe_silently():
    kho = _store("{ khong phai json")
    assert kho.read() == {}
    assert not kho.path.exists(), "tep hong phai duoc doi ten di"
    assert kho.path.with_suffix(".json.hong").exists()


def test_missing_file_is_simply_empty():
    kho = _store()
    assert kho.read() == {}
    assert kho.unseen([{"k": "a"}], key=lambda it: it["k"]) == ([{"k": "a"}], 0)


# =========================================================================
# Doc duoc dinh dang CU (list khoa tran) — Vera/Qinn tung ghi kieu do
# =========================================================================
def test_legacy_list_format_is_still_read_as_seen():
    kho = _store({"seen_at": ["tin-cu-1", "tin-cu-2"]})
    con = kho.read()
    assert set(con) == {"tin-cu-1", "tin-cu-2"}
    giu, bo = kho.unseen([{"k": "tin-cu-1"}, {"k": "tin-moi"}], key=lambda it: it["k"])
    assert [it["k"] for it in giu] == ["tin-moi"]
    assert bo == 1


def test_legacy_list_is_migrated_to_dict_on_next_write():
    kho = _store({"seen_at": ["tin-cu-1"]})
    kho.mark(["tin-moi"])
    d = json.loads(kho.path.read_text(encoding="utf-8"))
    assert isinstance(d["seen_at"], dict)
    assert set(d["seen_at"]) == {"tin-cu-1", "tin-moi"}


# =========================================================================
# Luat 5 — ghi nguyen tu, khong de lai tep tam
# =========================================================================
def test_write_leaves_no_temp_file_behind():
    kho = _store()
    kho.mark(["a"])
    thua = [p.name for p in kho.path.parent.iterdir() if ".tmp" in p.name]
    assert not thua, f"con tep tam: {thua}"


def test_empty_keys_are_ignored():
    """Muc thieu link/id khong duoc tao mot khoa rong nuot moi thu ve sau."""
    kho = _store()
    kho.mark(["", None, "that"])
    assert set(kho.read()) == {"that"}
    con, _ = kho.unseen([{"k": ""}], key=lambda it: it["k"])
    assert len(con) == 1, "khoa rong khong duoc tinh la da thay"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
