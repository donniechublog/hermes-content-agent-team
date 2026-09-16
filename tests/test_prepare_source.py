#!/usr/bin/env python3
"""`prepare.source.load_source` ghi lại `.meta.json` sau khi giải mã link Google
News — PHẢI trộn vào bản trên đĩa, không ghi đè cả `meta` trong bộ nhớ (F2,
khảo sát ngoài phạm vi của audit).

`.meta.json` là tệp BA TIẾN TRÌNH cùng ghi không khoá chung (approve_service,
engine nền, và `blackboard` của hermes ghi riêng `root_task` — xem docstring
`env_load.write_json`). `approve_pick.py` đã né việc này bằng `schema.merge_meta`
(merge, không ghi đè) đúng cho trường hợp NÓ tự nêu ra trong docstring: "write_meta
chạy hai lần cho một bài — lúc chọn tin, RỒI LÚC GIẢI XONG LINK GOOGLE NEWS". Vế
sau chính là lệnh gọi trong `prepare/source.py`, nhưng cho tới trước bản sửa này
nó ghi đè `meta` (bản trong bộ nhớ, có thể đã CŨ đi so với lúc gọi hàm — pipeline
Kite/Dre/Ethan chạy lâu) thay vì trộn — mất đúng thứ `merge_meta` sinh ra để giữ.

Chạy:  venv/bin/python tests/test_prepare_source.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import article_sources                                              # noqa: E402
import prepare.source as source                                # noqa: E402

GNEWS_URL = "https://news.google.com/rss/articles/CBMi_gia_lap"
THAT_URL = "https://baothat.vi.du/bai-goc"


def _with_drafts_temp(ham):
    """Chay `ham(drafts, state)` voi source.DRAFTS tro vao thu muc tam, phuc hoi
    sau do du co loi hay khong."""
    with tempfile.TemporaryDirectory() as t:
        drafts = Path(t) / "drafts"
        state = Path(t) / "state"
        drafts.mkdir(parents=True)
        state.mkdir(parents=True)
        cu = source.DRAFTS
        source.DRAFTS = drafts
        try:
            return ham(drafts, state)
        finally:
            source.DRAFTS = cu


def _fake_repeat_resolve_code(ket_qua):
    """Doi article_sources.resolve_code_gnews de khong goi mang/Chromium that. `load_source`
    goi qua `import article_sources` moi lan, nen doi thuoc tinh tren MODULE la du —
    khong can vi sys.modules thu cong."""
    cu = article_sources.resolve_code_gnews
    article_sources.resolve_code_gnews = lambda url, phien=None, **k: ket_qua
    return cu


def test_resolve_gnews_full_no_overwrite_root_task_form_has_on_disk():
    """root_task duoc blackboard ghi vao .meta.json SAU khi meta da nap vao bo nho
    (mo phong dua bang cach: dia co root_task, ban trong bo nho thi khong) —
    load_source() giai gnews KHONG duoc xoa mat no khi ghi lai."""
    def _chay(drafts, state):
        draft_id = "d1"
        p_meta = drafts / f"{draft_id}.meta.json"
        # Dia: da co root_task (blackboard ghi rieng, sau luc meta duoc nap)
        p_meta.write_text(json.dumps({"source_url": GNEWS_URL, "title": "t",
                                      "category": "AI", "root_task": "t_42"}),
                          encoding="utf-8")
        # Bo nho: BAN CU, chua co root_task (dung dung bo nho da nap TRUOC khi
        # blackboard ghi — day la khe ho that)
        meta = {"source_url": GNEWS_URL, "title": "t", "category": "AI"}
        cu = _fake_repeat_resolve_code(THAT_URL)
        try:
            source.load_source(draft_id, meta, state)
        finally:
            article_sources.resolve_code_gnews = cu
        tren_dia = json.loads(p_meta.read_text(encoding="utf-8"))
        return meta, tren_dia
    meta, tren_dia = _with_drafts_temp(_chay)
    assert meta["source_url"] == THAT_URL, "ban trong bo nho phai duoc cap nhat"
    assert tren_dia.get("root_task") == "t_42", \
        f"root_task blackboard ghi bi mat sau khi load_source ghi lai: {tren_dia}"
    assert tren_dia.get("source_url") == THAT_URL, tren_dia


def test_no_right_gnews_then_no_use_dark_meta_json():
    """Duong dan thuong (khong phai news.google.com) khong duoc cham vao
    .meta.json — chi giai gnews moi ghi lai."""
    def _chay(drafts, state):
        draft_id = "d2"
        meta = {"source_url": "https://vi.du/bai-thuong", "title": "t"}
        source.load_source(draft_id, meta, state)
        return (drafts / f"{draft_id}.meta.json").exists()
    da_ghi = _with_drafts_temp(_chay)
    assert not da_ghi, ".meta.json khong duoc tao ra khi khong co gnews de giai"


def test_resolve_out_use_link_old_then_no_write_again():
    """resolve_code_gnews tra ve CHINH url dau vao (khong giai duoc gi moi) — guard
    `!= that` phai chan, khong ghi lai file vo ich."""
    def _chay(drafts, state):
        draft_id = "d3"
        meta = {"source_url": GNEWS_URL, "title": "t"}
        cu = _fake_repeat_resolve_code(GNEWS_URL)
        try:
            source.load_source(draft_id, meta, state)
        finally:
            article_sources.resolve_code_gnews = cu
        return (drafts / f"{draft_id}.meta.json").exists()
    da_ghi = _with_drafts_temp(_chay)
    assert not da_ghi


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
