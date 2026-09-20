#!/usr/bin/env python3
"""LOW-309 — lưới ĐỐI CHIẾU VẾT cho `journal.use_page` trước khi tách.

`use_page` (độ phức tạp 48) dựng nguyên trang nhật ký ngày. Nó thuần: mọi thứ
chạm CSDL nằm ở các hàm `part_*`, nên thay chúng bằng dữ liệu định sẵn là hàm
trở thành một phép biến đổi dữ liệu → chuỗi, so được **từng ký tự**.

  1. KỊCH BẢN = một bộ `part_*` trả dữ liệu cố định (+ `ERROR_READ`).
  2. VẾT = TOÀN BỘ chuỗi Markdown trả về.
  3. Vết của bản TRƯỚC khi tách ở `tests/golden/journal_pages.json`. Bản sau khi
     tách phải cho ra đúng chuỗi đó — 0 lệch.

Đồng hồ bị khoá (`datetime` giả) vì dòng "Dựng lúc …" có giờ thật.

Cố ý đổi trang thì ghi lại vết và giải thích phần lệch trong PR:
    venv/bin/python tests/test_journal_page_trace.py --write-golden

Chay:  venv/bin/python tests/test_journal_page_trace.py
"""
import contextlib
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import journal as nk                                          # noqa: E402

GOLDEN = Path(__file__).resolve().parent / "golden" / "journal_pages.json"
NGAY = "2026-09-19"


class _DongHo:
    """`datetime` giả: chỉ khoá `now`, mọi thứ khác đi thẳng về bản thật."""

    @staticmethod
    def now(tz=None):
        return datetime(2026, 9, 19, 23, 45, tzinfo=tz)

    def __getattr__(self, ten):
        return getattr(datetime, ten)


def _ghi_chu(**k):
    d = {"kind": "bug", "time": "09:12", "content": "Dre dựng nhầm bìa vector"}
    d.update(k)
    return d


def _task(**k):
    d = {"id": "t1", "time": "05:10", "role": "dre", "title": "Carousel: Nvidia mở kho",
         "status": "done", "seconds": 132, "summary": "đã giao 6 ảnh", "error": None}
    d.update(k)
    return d


def _cron(**k):
    d = {"name": "daily-scan", "time": "05:00", "status": "completed",
         "seconds": 41, "error": None}
    d.update(k)
    return d


# Mỗi kịch bản: dict các `part_*` + `notes` + `ERROR_READ`.
SCENARIOS = {
    "ngay_trong": {},
    "chi_ghi_chu": {"notes": [_ghi_chu(), _ghi_chu(kind="fix", time="10:00", content="Đã vá")]},
    "chi_git": {"git": [{"hash": "abc1234", "time": "08:00", "subject": "fix(dre): cong so slide"}]},
    "finn_day_du": {"finn": {"candidate_count": 26, "picked_count": 2,
                             "top": [{"score": 88, "title": "Nvidia mở kho", "source_note": "HN"},
                                     {"score": 71, "title": "Anthropic ra bản mới", "source_note": "Lobste.rs"}],
                             "picked_titles": ["Nvidia mở kho", "Anthropic ra bản mới"]}},
    "finn_khong_chon_gi": {"finn": {"candidate_count": 9, "picked_count": 0,
                                    "top": [{"score": 40, "title": "Tin nhạt", "source_note": "X"}],
                                    "picked_titles": []}},
    "kanban_du_trang_thai": {"kanban": [
        _task(), _task(id="t2", status="failed", seconds=None, summary="", error="hết giờ\nchi tiết"),
        _task(id="t3", status="running", seconds=0, summary="", error=None)]},
    "draft": {"draft": [{"id": "d1", "time": "11:00", "caption_length": 812,
                         "has_image": True, "status": "published"},
                        {"id": "d2", "time": "12:00", "caption_length": 0,
                         "has_image": False, "status": "pending"}]},
    "cron_thua_luot_thi_gom": {"cron": [_cron(seconds=i) for i in range(12)]},
    "cron_it_luot_thi_ke_tung_cai": {"cron": [
        _cron(), _cron(name="moat-publish-watch", time="05:05", status="failed",
                       seconds=None, error="timeout"),
        _cron(name="audit-cron", time="00:00", status="running", seconds=None)]},
    "cron_gom_ma_co_loi": {"cron": [_cron(seconds=i) for i in range(11)]
                           + [_cron(status="failed", seconds=None, error="hỏng")] * 2},
    "model_hong": {"model": {"broken_models": ["deepseek-v4-flash"], "model_count": 9,
                             "reasons": {"deepseek-v4-flash": "402 hết tiền"}}},
    "model_khoe": {"model": {"broken_models": [], "model_count": 9, "reasons": {}}},
    "doc_hong_mot_mang": {"kanban": [_task()], "error_read": ["part_kanban: sqlite3.Error"]},
    "day_du_moi_muc": {
        "notes": [_ghi_chu()],
        "git": [{"hash": "abc1234", "time": "08:00", "subject": "fix(dre): cong so slide"}],
        "finn": {"candidate_count": 26, "picked_count": 1,
                 "top": [{"score": 88, "title": "Nvidia mở kho", "source_note": "HN"}],
                 "picked_titles": ["Nvidia mở kho"]},
        "kanban": [_task()],
        "draft": [{"id": "d1", "time": "11:00", "caption_length": 812,
                   "has_image": True, "status": "published"}],
        "cron": [_cron()],
        "model": {"broken_models": [], "model_count": 9, "reasons": {}},
    },
}


@contextlib.contextmanager
def _gia(kb):
    """Thay mọi cạnh CSDL + đồng hồ; trả lại hết khi ra khỏi khối."""
    cu = {ten: getattr(nk, ten) for ten in
          ("read_notes", "part_git", "part_finn", "part_kanban", "part_draft",
           "part_cron", "part_model", "datetime")}
    nk.read_notes = lambda ngay: list(kb.get("notes", []))
    nk.part_git = lambda ngay: list(kb.get("git", []))
    nk.part_finn = lambda ngay: kb.get("finn")
    nk.part_kanban = lambda ngay: list(kb.get("kanban", []))
    nk.part_draft = lambda ngay: list(kb.get("draft", []))
    nk.part_cron = lambda ngay: list(kb.get("cron", []))
    nk.part_model = lambda ngay: kb.get("model")
    nk.datetime = _DongHo()
    try:
        yield
    finally:
        for ten, v in cu.items():
            setattr(nk, ten, v)
        nk.ERROR_READ.clear()


def _chay(ten):
    kb = SCENARIOS[ten]
    with _gia(kb):
        # `use_page` xoá ERROR_READ ở dòng đầu, nên nạp vào qua một `part_*` giả.
        loi_doc = list(kb.get("error_read", []))
        if loi_doc:
            that = nk.part_kanban
            nk.part_kanban = lambda ngay: (nk.ERROR_READ.extend(loi_doc) or that(ngay))
        return nk.use_page(NGAY)


def _make_test(ten):
    def _test():
        muon = json.loads(GOLDEN.read_text(encoding="utf-8"))[ten]
        duoc = _chay(ten)
        if duoc != muon:
            import difflib
            khac = "\n".join(list(difflib.unified_diff(
                muon.splitlines(), duoc.splitlines(), "muốn", "được", lineterm=""))[:40])
            raise AssertionError(f"{ten} lệch:\n{khac}")
    _test.__name__ = "test_" + ten
    return _test


for _ten in SCENARIOS:
    globals()["test_" + _ten] = _make_test(_ten)


def test_golden_has_no_stale_or_missing_scenarios():
    assert sorted(json.loads(GOLDEN.read_text(encoding="utf-8"))) == sorted(SCENARIOS)


def test_scenarios_touch_every_section():
    """Vết vàng mà rỗng thì 0-lệch không chứng minh gì: mọi mục phải có mặt."""
    tat_ca = "\n".join(json.loads(GOLDEN.read_text(encoding="utf-8")).values())
    for muc in ("## Vấn đề, bug và cách sửa", "## Thay đổi mã nguồn", "## Finn quét tin",
                "## Task kanban", "## Bài viết", "## Cron", "**Lượt lỗi**", "## Model",
                "## ⚠️ Không đọc được một phần dữ liệu",
                "*Không có hoạt động nào được ghi lại trong ngày.*"):
        assert muc in tat_ca, muc


if __name__ == "__main__":
    if "--write-golden" in sys.argv:
        GOLDEN.parent.mkdir(parents=True, exist_ok=True)
        GOLDEN.write_text(json.dumps({t: _chay(t) for t in SCENARIOS},
                                     ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        print(f"da ghi {GOLDEN}")
        raise SystemExit(0)
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
