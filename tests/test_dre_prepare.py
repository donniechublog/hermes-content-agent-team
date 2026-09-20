#!/usr/bin/env python3
"""dre_prepare.py — brief carousel cho Dre (LOW-307, module 0% độ phủ).

Brief là TOÀN BỘ những gì vai nhìn thấy: thiếu một dòng ở đây thì vai không biết
mà làm, và không ai thấy lỗi — bộ slide vẫn ra, chỉ là sai. Ba nhóm đáng giữ:

  1. **Các lối THOÁT SỚM**: 0 ảnh thật, brand chưa có Kite, tin đã chuyển Kite.
     Sai ở đây là Dre dựng hình giả hoặc dựng trùng việc của Kite.
  2. **Bảng ảnh**: ảnh ❌ phải hiện rõ là KHÔNG DÙNG; ảnh có mặt người phải kèm
     tên để vai khai `subject` (LOW-178); nhãn đo bằng máy phải nói rõ khi vision
     chưa chạy.
  3. **Đếm ảnh dùng được** theo ĐÚNG công thức của người ghi
     (`schema.count_image_use_ok`) — đếm tay ra số khác vì chùm ảnh khái niệm
     phải đếm là MỘT.

Chay:  venv/bin/python tests/test_dre_prepare.py
"""
import contextlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import dre_prepare as db                                     # noqa: E402
import image_prepare as cb                                   # noqa: E402


def _anh(ma, **k):
    a = {"id": ma, "w": 1200, "h": 1500, "ratio": 0.8, "kind": "photo", "landscape": False,
         "faces": 0, "relevant": True, "description": f"anh {ma}", "alt": "", "uses": ["body"],
         "domain": "bao.test", "source": "article", "notes": []}
    a.update(k)
    return a


def _m(anh=None, **k):
    m = {"images": anh if anh is not None else [_anh("A1"), _anh("A2")],
         "draft_id": "tin-thu", "title": "Tin thử", "link": "https://vi.du/bai",
         "brand": "donniechublog", "workdir": "/tmp/wd", "min_images": 5,
         "flagship": False, "material": {}, "summary": "", "domains": None,
         "cover_suggestions": [], "stackable_pairs": None, "category": ""}
    m.update(k)
    return m


# ---------- các lối thoát sớm ----------

def test_no_real_image_then_tells_role_to_stop_not_to_draw():
    """0 ảnh: brief vẫn in tiếp (engine định tuyến riêng), nhưng dòng ĐẦU của bảng
    ảnh phải là lệnh DỪNG — không được để vai tự nghĩ ra hình."""
    b = db.write_brief(_m(anh=[]), None)
    assert "KHÔNG CÓ ảnh thật" in b and "Không dựng hình giả" in b, b
    assert "THIẾU ẢNH" not in b, "0 ảnh thì đừng bảo vai đi tìm thêm, đã có dòng dừng"


def test_kite_unavailable_then_stop_and_say_brand_has_no_kite():
    b = db.write_brief(_m(anh=[], kite_unavailable=True), None)
    assert "brand chưa có Kite" in b and "KHÔNG dựng hình giả" in b, b
    assert "## Viết spec vào" not in b


def test_already_moved_to_kite_then_stop_without_spec():
    b = db.write_brief(_m(kite_task_id="t-99"), None)
    assert "ĐÃ CHUYỂN KITE (task t-99)" in b and "KHÔNG viết spec" in b, b
    assert "## Viết spec vào" not in b


def test_normal_case_reaches_spec_and_one_command():
    b = db.write_brief(_m(), None)
    assert "## Viết spec vào: /tmp/wd/spec.json" in b, b
    assert "venv/bin/python dre_submit.py tin-thu" in b, b


# ---------- thiếu ảnh ----------

def test_not_enough_images_then_tells_role_to_search_itself():
    """Không được nhồi ảnh không liên quan cho đủ — phải đi tìm, tối đa 3 lượt."""
    b = db.write_brief(_m(anh=[_anh("A1")], min_images=5), None)
    assert "THIẾU ẢNH: chỉ 1 slide dựng được, cần ≥ 5" in b, b
    assert "find_more_images.py tin-thu" in b and "tối đa 3 lượt" in b, b


def test_usable_count_from_writer_beats_counting_by_hand():
    """Chùm ảnh khái niệm đếm là MỘT: `usable_count` của người ghi là số đúng."""
    anh = [_anh(f"A{i}") for i in range(1, 6)]
    b = db.write_brief(_m(anh=anh, usable_count=2, min_images=5), None)
    assert "chỉ 2 slide dựng được" in b, b


def test_enough_images_then_no_warning():
    anh = [_anh(f"A{i}") for i in range(1, 6)]
    assert "THIẾU ẢNH" not in db.write_brief(_m(anh=anh, min_images=5), None)


# ---------- bảng ảnh ----------

def test_irrelevant_image_is_marked_do_not_use_and_has_no_label_line():
    b = db.write_brief(_m(anh=[_anh("A1", relevant=False, description="con mèo")]), None)
    assert "A1: ❌ KHÔNG LIÊN QUAN — con mèo → KHÔNG DÙNG" in b, b
    assert "1200x1500" not in b, "ảnh ❌ vẫn in dòng nhãn như ảnh dùng được"


def test_face_without_name_says_only_if_article_names_this_person():
    b = db.write_brief(_m(anh=[_anh("A1", faces=1, description="một người đàn ông")]), None)
    assert "mặt người KHÔNG rõ ai" in b, b


def test_face_with_name_asks_role_to_fill_subject():
    """LOW-178: tên người do chính tấm ảnh mang theo — khai đúng tên đó là qua cổng."""
    b = db.write_brief(_m(anh=[_anh("A1", faces=1,
                                    description="Jensen Huang cầm chip trên sân khấu")]), None)
    assert 'khai "subject" đúng tên NGƯỜI' in b, b
    assert "Jensen Huang" in b, b


def test_notes_and_alt_reach_the_brief():
    b = db.write_brief(_m(anh=[_anh("A1", description="", alt="nvidia gpu photo",
                                    source="web", domain="", notes=["⚠️ RỐI"])]), None)
    assert "alt: nvidia gpu photo" in b and "⚠️ RỐI" in b, b


def test_not_yet_seen_says_labels_may_be_wrong():
    """Vision chưa chạy: nhãn chỉ là đo số — vai phải mở contact_sheet trước khi tin."""
    b = db.write_brief(_m(not_yet_seen=["A1", "A2"]), None)
    assert "CHƯA AI NHÌN A1, A2" in b and "contact_sheet.png" in b, b


def test_single_domain_is_pointed_out_only_when_set_is_big():
    anh = [_anh(f"A{i}") for i in range(1, 6)]
    b = db.write_brief(_m(anh=anh, domains=["bao.test"]), None)
    assert "chỉ MỘT nguồn" in b, b
    b2 = db.write_brief(_m(anh=[_anh("A1")], domains=["bao.test"], min_images=1), None)
    assert "chỉ MỘT nguồn" not in b2, b2


def test_cover_suggestions_and_stack_pairs_are_shown():
    b = db.write_brief(_m(cover_suggestions=["A2"], stackable_pairs=[["A1", "A2"]]), None)
    assert "Gợi ý bìa" in b and "A1+A2" in b, b
    assert '"image": "A2"' in b, "gợi ý bìa đầu tiên phải vào khung spec"


# ---------- làm lại & loại tin ----------

def test_redo_block_says_what_must_change():
    da_dung = {"submitted_at": "2026-09-19 10:00", "cover_image": "A1",
               "image_ids": ["A1", "A2"], "hook": "Hook cũ"}
    b = db.write_brief(_m(), da_dung)
    assert "LÀM LẠI" in b and "Hook cũ" in b, b
    assert "BÌA và HOOK phải khác" in b, b


def test_story_type_line_is_included():
    b = db.write_brief(_m(category="M&A", two_company_pairs=[["A1", "A2"]]), None)
    assert "THƯƠNG VỤ" in b and "A1+A2" in b, b


def test_flagship_and_ranking_lines():
    b = db.write_brief(_m(flagship=True, is_ranking_story=True, ranking=None), None)
    assert "FLAGSHIP" in b, b
    assert "xếp hạng" in b.lower() or "THẺ DỰ PHÒNG" in b, b


# ---------- dòng lệnh ----------

@contextlib.contextmanager
def _engine(m, wd):
    """Thay engine chuẩn bị (mạng + Chromium) bằng kết quả định sẵn."""
    cu_run, cu_doc = cb.run, cb._read_json
    cb.run = lambda *a, **k: (m, wd, {})
    cb._read_json = lambda p: None
    try:
        yield
    finally:
        cb.run, cb._read_json = cu_run, cu_doc


def test_main_writes_brief_md_into_workdir():
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        wd = Path(t)
        cu = sys.argv
        sys.argv = ["dre_prepare.py", "tin-thu", "--im"]
        try:
            with _engine(_m(workdir=str(wd)), wd):
                assert db.main() == 0
        finally:
            sys.argv = cu
        b = (wd / "brief.md").read_text(encoding="utf-8")
    assert "# DRE — ĐÃ CHUẨN BỊ XONG: Tin thử" in b, b[:200]


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
