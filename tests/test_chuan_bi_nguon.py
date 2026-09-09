#!/usr/bin/env python3
"""`chuan_bi.nguon.nap_nguon` ghi lại `.meta.json` sau khi giải mã link Google
News — PHẢI trộn vào bản trên đĩa, không ghi đè cả `meta` trong bộ nhớ (F2,
khảo sát ngoài phạm vi của audit).

`.meta.json` là tệp BA TIẾN TRÌNH cùng ghi không khoá chung (approve_service,
engine nền, và `bang_den` của hermes ghi riêng `root_task` — xem docstring
`env_load.ghi_json`). `duyet_chon_tin.py` đã né việc này bằng `schema.hop_nhat_meta`
(merge, không ghi đè) đúng cho trường hợp NÓ tự nêu ra trong docstring: "write_meta
chạy hai lần cho một bài — lúc chọn tin, RỒI LÚC GIẢI XONG LINK GOOGLE NEWS". Vế
sau chính là lệnh gọi trong `chuan_bi/nguon.py`, nhưng cho tới trước bản sửa này
nó ghi đè `meta` (bản trong bộ nhớ, có thể đã CŨ đi so với lúc gọi hàm — pipeline
Kite/Dre/Ethan chạy lâu) thay vì trộn — mất đúng thứ `hop_nhat_meta` sinh ra để giữ.

Chạy:  venv/bin/python tests/test_chuan_bi_nguon.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import nguon_bai                                              # noqa: E402
import chuan_bi.nguon as nguon                                # noqa: E402

GNEWS_URL = "https://news.google.com/rss/articles/CBMi_gia_lap"
THAT_URL = "https://baothat.vi.du/bai-goc"


def _voi_drafts_tam(ham):
    """Chay `ham(drafts, state)` voi nguon.DRAFTS tro vao thu muc tam, phuc hoi
    sau do du co loi hay khong."""
    with tempfile.TemporaryDirectory() as t:
        drafts = Path(t) / "drafts"
        state = Path(t) / "state"
        drafts.mkdir(parents=True)
        state.mkdir(parents=True)
        cu = nguon.DRAFTS
        nguon.DRAFTS = drafts
        try:
            return ham(drafts, state)
        finally:
            nguon.DRAFTS = cu


def _gia_lap_giai_ma(ket_qua):
    """Doi nguon_bai.giai_ma_gnews de khong goi mang/Chromium that. `nap_nguon`
    goi qua `import nguon_bai` moi lan, nen doi thuoc tinh tren MODULE la du —
    khong can vi sys.modules thu cong."""
    cu = nguon_bai.giai_ma_gnews
    nguon_bai.giai_ma_gnews = lambda url, phien=None, **k: ket_qua
    return cu


def test_giai_gnews_tron_khong_ghi_de_root_task_dang_co_tren_dia():
    """root_task duoc bang_den ghi vao .meta.json SAU khi meta da nap vao bo nho
    (mo phong dua bang cach: dia co root_task, ban trong bo nho thi khong) —
    nap_nguon() giai gnews KHONG duoc xoa mat no khi ghi lai."""
    def _chay(drafts, state):
        draft_id = "d1"
        p_meta = drafts / f"{draft_id}.meta.json"
        # Dia: da co root_task (bang_den ghi rieng, sau luc meta duoc nap)
        p_meta.write_text(json.dumps({"source_url": GNEWS_URL, "title": "t",
                                      "category": "AI", "root_task": "t_42"}),
                          encoding="utf-8")
        # Bo nho: BAN CU, chua co root_task (dung dung bo nho da nap TRUOC khi
        # bang_den ghi — day la khe ho that)
        meta = {"source_url": GNEWS_URL, "title": "t", "category": "AI"}
        cu = _gia_lap_giai_ma(THAT_URL)
        try:
            nguon.nap_nguon(draft_id, meta, state)
        finally:
            nguon_bai.giai_ma_gnews = cu
        tren_dia = json.loads(p_meta.read_text(encoding="utf-8"))
        return meta, tren_dia
    meta, tren_dia = _voi_drafts_tam(_chay)
    assert meta["source_url"] == THAT_URL, "ban trong bo nho phai duoc cap nhat"
    assert tren_dia.get("root_task") == "t_42", \
        f"root_task bang_den ghi bi mat sau khi nap_nguon ghi lai: {tren_dia}"
    assert tren_dia.get("source_url") == THAT_URL, tren_dia


def test_khong_phai_gnews_thi_khong_dung_toi_meta_json():
    """Duong dan thuong (khong phai news.google.com) khong duoc cham vao
    .meta.json — chi giai gnews moi ghi lai."""
    def _chay(drafts, state):
        draft_id = "d2"
        meta = {"source_url": "https://vi.du/bai-thuong", "title": "t"}
        nguon.nap_nguon(draft_id, meta, state)
        return (drafts / f"{draft_id}.meta.json").exists()
    da_ghi = _voi_drafts_tam(_chay)
    assert not da_ghi, ".meta.json khong duoc tao ra khi khong co gnews de giai"


def test_giai_ra_dung_link_cu_thi_khong_ghi_lai():
    """giai_ma_gnews tra ve CHINH url dau vao (khong giai duoc gi moi) — guard
    `!= that` phai chan, khong ghi lai file vo ich."""
    def _chay(drafts, state):
        draft_id = "d3"
        meta = {"source_url": GNEWS_URL, "title": "t"}
        cu = _gia_lap_giai_ma(GNEWS_URL)
        try:
            nguon.nap_nguon(draft_id, meta, state)
        finally:
            nguon_bai.giai_ma_gnews = cu
        return (drafts / f"{draft_id}.meta.json").exists()
    da_ghi = _voi_drafts_tam(_chay)
    assert not da_ghi


if __name__ == "__main__":
    ham = [v for k, v in list(globals().items()) if k.startswith("test_")]
    loi = 0
    for h in ham:
        try:
            h()
            print(f"OK   {h.__name__}")
        except AssertionError as e:
            loi += 1
            print(f"FAIL {h.__name__}: {e}")
    print(f"\n{len(ham) - loi}/{len(ham)} test qua")
    sys.exit(1 if loi else 0)
