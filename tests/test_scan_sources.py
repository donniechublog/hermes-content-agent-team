#!/usr/bin/env python3
"""`scan_sources.seen_keys()` — URL nào coi là "đã dùng", không được gợi ý lại.

Audit F2 (survey ngoài phạm vi) nêu: `(ROOT / "drafts").glob("*.json")` khớp cả
`<id>.meta.json` lẫn `<id>.json`, trong khi những chỗ khác (theo_doi_9router.py,
ada_prepare.py, approve_service.py) đều LỌC BỎ `.meta.json`/`.img.json`/
`.writer.json` khi quét `drafts/`. Nhìn thoáng qua giống một glob quên lọc.

ĐÃ ĐO và kết luận đây KHÔNG phải lỗi — hai loại quét có mục đích khác nhau:
  - Các chỗ kia quét để tìm DRAFT THẬT (đọc "caption"/"status" — thứ chỉ
    `<id>.json` mới có, `.meta.json` không có các khoá đó).
  - `seen_keys()` chỉ đọc MỘT trường (`source_url`), mà `.meta.json` CÓ trường
    đó (schema.Meta, bắt buộc) — nó được ghi ngay lúc Ông Chủ giao task, TRƯỚC
    khi vai viết xong caption. Bỏ nó ra khỏi glob nghĩa là một URL đang có vai
    viết dở (chỉ có .meta.json, chưa có .json) không còn bị coi là "đã dùng"
    nữa, và scan_sources có thể gợi ý lại CHÍNH URL đó cho một task thứ hai
    trong lúc task đầu chưa xong — hai vai cùng viết một bài.

Tệp này khoá lại hành vi ĐÚNG đó bằng số đo, để một lượt "dọn" glob sau này
không biến nó thành hồi quy.

Chạy:  venv/bin/python tests/test_scan_sources.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import scan_sources as ss                                     # noqa: E402


def _moi_truong(tmp):
    """Tra (drafts_dir, state_dir) da tao san, va mot ham don don DE PHUC HOI
    ss.ROOT/ss.STATE ve gia tri that."""
    drafts = Path(tmp) / "drafts"
    state = Path(tmp) / "state"
    drafts.mkdir(parents=True, exist_ok=True)
    state.mkdir(parents=True, exist_ok=True)
    return drafts, state


def _voi_moi_truong(tmp, ham):
    """Chay `ham()` voi ss.ROOT/ss.STATE tro vao tmp, roi phuc hoi du co loi hay
    khong (khong dung contextmanager de tep nay tu chay boi runner rieng)."""
    drafts, state = _moi_truong(tmp)
    cu = (ss.ROOT, ss.STATE)
    ss.ROOT, ss.STATE = Path(tmp), state
    try:
        return ham(drafts, state)
    finally:
        ss.ROOT, ss.STATE = cu


def test_task_dang_giao_chi_co_meta_json_van_tinh_la_da_dung():
    """.meta.json duoc ghi NGAY luc giao task (duyet_chon_tin.write_meta), TRUOC
    khi vai viet xong caption (.json). URL cua no PHAI bi coi la da dung — day
    la ly do that scan_sources khong loc .meta.json ra khoi glob."""
    def _chay(drafts, state):
        (drafts / "d1.meta.json").write_text(
            json.dumps({"source_url": "https://vi.du/bai-a", "title": "t",
                        "category": "AI"}), encoding="utf-8")
        return ss.seen_keys()
    with tempfile.TemporaryDirectory() as t:
        keys = _voi_moi_truong(t, _chay)
    assert ss._norm_url("https://vi.du/bai-a") in keys, keys


def test_draft_da_viet_xong_van_tinh_la_da_dung():
    """`.json` that (draft_write.py da ghi) van phai duoc dem — cong that su
    dang bao ve la .meta.json, khong phai lam mat truong hop .json thuong."""
    def _chay(drafts, state):
        (drafts / "d2.json").write_text(
            json.dumps({"caption": "x", "source_url": "https://vi.du/bai-b",
                        "category": "AI", "status": "pending"}), encoding="utf-8")
        return ss.seen_keys()
    with tempfile.TemporaryDirectory() as t:
        keys = _voi_moi_truong(t, _chay)
    assert ss._norm_url("https://vi.du/bai-b") in keys, keys


def test_ca_hai_tep_cung_mot_draft_khong_sinh_hai_khoa_khac_nhau():
    """d3.json va d3.meta.json cung mot source_url (truong hop binh thuong sau
    khi vai viet xong) -> set dedup tu nhien, khong phinh ra hai khoa."""
    def _chay(drafts, state):
        (drafts / "d3.meta.json").write_text(
            json.dumps({"source_url": "https://vi.du/bai-c", "title": "t",
                        "category": "AI"}), encoding="utf-8")
        (drafts / "d3.json").write_text(
            json.dumps({"caption": "x", "source_url": "https://vi.du/bai-c",
                        "category": "AI", "status": "pending"}), encoding="utf-8")
        return ss.seen_keys()
    with tempfile.TemporaryDirectory() as t:
        keys = _voi_moi_truong(t, _chay)
    assert sum(1 for k in keys if k == ss._norm_url("https://vi.du/bai-c")) <= 1


def test_meta_khong_co_source_url_khong_lam_chet_seen_keys():
    """Sidecar cu/hong thieu source_url (vd tao tay, thieu truong bat buoc) —
    .get() phai tra falsy va bi bo qua em, khong duoc nem KeyError."""
    def _chay(drafts, state):
        (drafts / "d4.meta.json").write_text(
            json.dumps({"title": "t", "category": "AI"}), encoding="utf-8")
        return ss.seen_keys()
    with tempfile.TemporaryDirectory() as t:
        keys = _voi_moi_truong(t, _chay)
    assert isinstance(keys, set)


def test_json_hong_khong_lam_chet_seen_keys():
    """Mot tep .json hong (ghi do dang, disk day...) khong duoc lam sap ca luot
    quet — cac tep con lai van phai duoc doc."""
    def _chay(drafts, state):
        (drafts / "d5.json").write_text("{khong phai json", encoding="utf-8")
        (drafts / "d6.meta.json").write_text(
            json.dumps({"source_url": "https://vi.du/bai-song-sot", "title": "t",
                        "category": "AI"}), encoding="utf-8")
        return ss.seen_keys()
    with tempfile.TemporaryDirectory() as t:
        keys = _voi_moi_truong(t, _chay)
    assert ss._norm_url("https://vi.du/bai-song-sot") in keys, keys


def test_candidate_cu_trong_state_cung_tinh_la_da_dung():
    """finn_candidates_*.json (ung vien tu vong quet truoc) cung la nguon —
    khong chi drafts/."""
    def _chay(drafts, state):
        (state / "finn_candidates_20260101.json").write_text(
            json.dumps({"items": [{"link": "https://vi.du/candidate-cu"}]}),
            encoding="utf-8")
        return ss.seen_keys()
    with tempfile.TemporaryDirectory() as t:
        keys = _voi_moi_truong(t, _chay)
    assert ss._norm_url("https://vi.du/candidate-cu") in keys, keys


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
