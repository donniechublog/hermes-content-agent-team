#!/usr/bin/env python3
"""LOW-337 (23/09/2026): hai cổng ảnh đá nhau làm Kite dừng hẳn.

Bài "Pentagon says overreliance on AI contributed to missile strike" (task
t_c6d378c6, 14:06 23/09): `figure_right_use` ép đủ 5 mã [A2, A16, A17, A18, A21]
vào slide thân, còn `submit_common.check_same_photo` (LOW-284) chặn vì A2 và A21
là CÙNG MỘT bức ảnh (ibtimes.co.uk, images.inkl.com — dHash lệch 0 bit) và A16,
A17 là hai bản cắt của cùng ảnh huy hiệu Lầu Năm Góc (ORB 279 điểm, tương quan
0.92). Bỏ mã thì thiếu ảnh ép, giữ mã thì dính trùng: không có đường nộp.

Hai gốc, mỗi phần có ví dụ SAI-PHẢI-CHẶN đi kèm ĐÚNG-PHẢI-QUA:
  1. `download_and_filter` chỉ khử trùng TRONG một vòng: bản inkl.com bị bỏ ở vòng
     1 rồi vòng [bao thuc the] tải lại thành A21. Nay có `da_giu`.
  2. bộ ép của Kite phải đọc CÙNG luật LOW-284 mà cổng nộp đang chặn.

Chạy:  venv/bin/python tests/test_low337_duplicate_force.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import kite_prepare as kb  # noqa: E402
import submit_common  # noqa: E402
from prepare import decision_log, download_filter  # noqa: E402
from tam import so_tam  # noqa: E402
from test_spec_dre import _co, _ve  # noqa: E402
from test_spec_kite import _chay, _cover, _hinh, _m, _statement  # noqa: E402


def _anh_chup(wd, ma, w=1200, h=800, **k):
    """Ảnh CHỤP (kind=photo) — cổng trùng ảnh chỉ xét loại này."""
    return _hinh(wd, ma=ma, w=w, h=h, kind="photo", **k)


# ------------------------------------------------- 1. khử trùng xuyên vòng
def _cand(wd, ten, w, h):
    p = Path(wd) / ten
    _ve(w, h).save(p)
    return {"image_url": str(p), "file_path": str(p), "alt": "", "page_url": "https://vi.du/b",
            "source": "other_outlet", "score": 10}


def _chay_tai(tmp, cands, da_giu=()):
    wd = Path(tmp) / "vong"
    wd.mkdir(parents=True, exist_ok=True)
    return download_filter.download_and_filter(cands, wd, da_giu=da_giu), wd


def test_candidate_duplicate_of_earlier_round_dropped():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        cu = Path(t) / "cu.png"
        _ve(1200, 800).save(cu)                              # vong 1 da giu tam nay
        anh, wd = _chay_tai(t, [_cand(t, "moi.png", 1200, 800)],
                            da_giu=[{"id": "A2", "original_path": str(cu)}])
        assert anh == [], [a["id"] for a in anh]
        ghi = [d for d in decision_log.collect(wd) if d.get("stage") == "near_duplicate"]
        assert ghi and ghi[0]["rule"] == "dhash_kept_earlier", ghi


def test_different_image_still_downloaded():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        cu = Path(t) / "cu.png"
        _ve(1200, 800, seed=1).save(cu)
        anh, _wd = _chay_tai(t, [_cand(t, "khac.png", 1100, 900)],
                             da_giu=[{"id": "A2", "original_path": str(cu)}])
        assert len(anh) == 1, anh


def test_kept_hashes_survives_a_missing_file():
    """Ảnh cũ mất tệp/hỏng thì bỏ qua tấm đó, KHÔNG làm chết cả vòng tải."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        ra = download_filter.kept_hashes([{"id": "A1", "original_path": str(Path(t) / "khong_co.png")},
                                          {"id": "A2"}])
        assert ra == [], ra


# ------------------------------------------------- 2. bộ ép không tự mâu thuẫn
def _m_chuyen(wd, anh):
    return _m(wd, anh, kite_task_id="t_9")


def test_force_drops_the_same_photo_keeps_the_bigger():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        a2 = _anh_chup(wd, "A2", 1200, 800)
        a18 = _anh_chup(wd, "A18", 1200, 630)
        a21 = _anh_chup(wd, "A21", 1000, 667)                # cung anh voi A2, ban nho hon
        cap = {(a2["original_path"], a21["original_path"]), (a21["original_path"], a2["original_path"])}
        with mock.patch("same_photo.is_same_photo", side_effect=lambda x, y: (x, y) in cap):
            ep = kb._force_raw(_m_chuyen(wd, [a2, a18, a21]))    # CHUA tru tam len bia
        assert ep == ["A2", "A18"], ep


def test_force_keeps_both_when_they_are_different_photos():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh_chup(wd, "A2"), _anh_chup(wd, "A18", 1200, 630)]
        with mock.patch("same_photo.is_same_photo", return_value=False):
            ep = kb._force_raw(_m_chuyen(wd, anh))
        assert ep == ["A2", "A18"], ep


def test_force_never_asks_for_a_pair_the_submit_gate_blocks():
    """Cổng ép và cổng nộp phải đọc cùng một luật: mỗi mã bị ép lên một slide
    riêng thì `check_same_photo` không được kêu tiếng nào."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        a2 = _anh_chup(wd, "A2", 1200, 800)
        a16 = _anh_chup(wd, "A16", 2000, 1601)
        a17 = _anh_chup(wd, "A17", 1200, 630)                # ban cat cua A16
        a18 = _anh_chup(wd, "A18", 1200, 630)
        a21 = _anh_chup(wd, "A21", 1200, 800)                # cung anh voi A2
        anh = [a2, a16, a17, a18, a21]
        cung = {("A2", "A21"), ("A21", "A2"), ("A16", "A17"), ("A17", "A16")}
        ten = {a["original_path"]: a["id"] for a in anh}

        def _gia(x, y):
            return (ten[x], ten[y]) in cung

        with mock.patch("same_photo.is_same_photo", side_effect=_gia):
            m = _m_chuyen(wd, anh)
            assert kb._force_raw(m) == ["A2", "A16", "A18"], kb._force_raw(m)
            ep = kb.figure_right_use(m)                     # tru them tam da len bia
            assert set(ep) <= {"A2", "A16", "A18"} and len(ep) >= 2, (ep, kb.figure_hero(m))
            loi = submit_common.check_same_photo({a["id"]: a for a in anh},
                                                 [(f"slide {i + 2}", [ma]) for i, ma in enumerate(ep)])
        assert loi == [], loi

        # ...con bo ep CU (chua khu trung) thi cong nop CHAN — bang chung cong nay that
        with mock.patch("same_photo.is_same_photo", side_effect=_gia):
            loi_cu = submit_common.check_same_photo(
                {a["id"]: a for a in anh},
                [(f"slide {i + 2}", [a["id"]]) for i, a in enumerate(anh)])
        assert len(loi_cu) == 2, loi_cu


def test_force_without_cv2_keeps_everything():
    """Thiếu cv2 thì `is_same_photo` trả False — bộ ép y như trước, không tự co lại."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh_chup(wd, "A2"), _anh_chup(wd, "A21")]
        with mock.patch("same_photo.compare", return_value=None):
            ep = kb._force_raw(_m_chuyen(wd, anh))
        assert ep == ["A2", "A21"], ep


# ------------------------------------------------- 3. thẻ logo: hai cổng một luật
def test_logo_card_passes_the_kite_empty_gate():
    """Bài "GPT-6 Sol and Luna" (23/09): A13 là thẻ logo OpenAI (`logo_card`, 80% nền
    trơn). `role.blocked_empty` miễn nó từ LOW-295 nên bộ ép đòi dùng, còn cổng nộp
    đọc thẳng `check_empty_image` nên chặn — Kite hết đường. Nay cổng nộp hỏi qua
    `role.blocked_empty`, tức CÙNG một luật."""
    import role
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        the = _hinh(wd, ma="A13", w=1200, h=1500, empty_share=0.8, logo_card=True,
                    subject_kind="logo", uses=["cover"], subject_box=[0.2, 0.2, 0.8, 0.6])
        assert role.blocked_empty(the, "kite") is False
        sl = [_cover(image="A13", caption="Logo OpenAI · via Commons")] +              [_statement(title=f"Ý {i}") for i in range(2, 7)]
        _r, loi, _c = _chay(sl, _m_chuyen(wd, [the]), wd)
        assert not _co(loi, "gần như TRỐNG"), loi


def test_really_empty_image_still_blocked():
    """Ảnh trống KHÔNG phải thẻ logo thì cổng vẫn chặn y như trước (LOW-273)."""
    import role
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        a = _hinh(wd, ma="A9", w=1200, h=1500, empty_share=0.9, subject_kind="logo",
                  uses=["cover"], subject_box=[0.4, 0.45, 0.6, 0.55])
        assert role.blocked_empty(a, "kite") is True
        sl = [_cover(image="A9", caption="Ảnh · via x.com")] +              [_statement(title=f"Ý {i}") for i in range(2, 7)]
        _r, loi, _c = _chay(sl, _m_chuyen(wd, [a]), wd)
        assert _co(loi, "gần như TRỐNG"), loi


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
