#!/usr/bin/env python3
"""LOW-273 (phan 2): chu the chinh nam TREN vung chu o Ethan (the quote) va Kite (anh chup).

Ong Chu 19/09/2026: "ko chap nhan nhung hinh nhu the nay o moi designer. ko phai la tim
hinh co ty le 4:5, ma la tim hinh co main character dat vua trong 4:5". Dre co cong tu
LOW-273 phan 1 (dre_submit._place_subject); tep nay chot Ethan va Kite.

Do that 19/09 truoc khi viet cong:
  - Ethan quote: anh ngang (Altman) nam nua tren the -> mat tron tren khung, QUA; anh
    doc A15 voi quote dai -> mat ket thuc 55%, khung tu 56% -> QUA (nhin anh dung ra
    xac nhan); noi hop mat 0.4 lan xuong duoi thi bao oan 66%.
  - Kite: dinh khoi chu do bang Chromium 53..62% khung tren 4 bo that; 4 slide anh nguoi
    da dang deu co mat tron tren chu -> QUA. Bang/bieu do KHONG xet (bang DeepSeek trong
    anh chuan chay xuong duoi chu).

Chay:  venv/bin/python tests/test_subject_gate_ethan_kite.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from PIL import Image  # noqa: E402

import card  # noqa: E402
import ethan_submit  # noqa: E402
import kite_submit  # noqa: E402
import render_edu  # noqa: E402
import subject_fit  # noqa: E402

LONG_Q = ("Năm 2025, suy luận chiếm 9% khối lượng trung tâm dữ liệu toàn cầu, huấn luyện "
          "14%. Đến 2030 là 37% và 13%.")


# ------------------------------------------------------------ hinh hoc chung
def test_head_box_only_small_margin_under_chin():
    hb = subject_fit.head_box([[0.4, 0.2, 0.6, 0.5]])
    assert abs(hb[3] - 0.53) < 1e-6, hb          # 0.1 x chieu cao mat, khong phai 0.4
    assert abs(hb[1] - 0.05) < 1e-6, hb


def test_face_boxes_with_none_detector_is_none():
    assert subject_fit.face_boxes_with(None, None, "x.png", 1600) is None


# ------------------------------------------------------------ Ethan
def test_quote_text_top_moves_up_with_longer_quote():
    top_long, H = card.quote_text_top(LONG_Q, "Báo cáo JLL, qua CNBC", None, "4:5", "dcgr")
    top_short, _ = card.quote_text_top("Ngắn gọn thôi.", "Báo cáo JLL, qua CNBC", None, "4:5", "dcgr")
    assert H == card.RATIOS["4:5"]
    assert top_long < top_short < H, (top_long, top_short)


def _ethan_img(w, h, **k):
    a = {"id": "A1", "original_path": "/x/A1.png", "w": w, "h": h, "kind": "photo", "faces": 1,
         "subject_box": [0.2, 0.05, 0.8, 0.95], "subject_kind": "person"}
    a.update(k)
    return a


def _ethan(a, spec=None, kieu="quote", ma2=None, faces=None):
    spec = spec or {"hook": LONG_Q, "attrib": "Báo cáo JLL, qua CNBC"}
    with mock.patch("image_rules_ethan.face_boxes", return_value=faces):
        return ethan_submit._check_subject_above_quote(spec, kieu, a, "A1", ma2, {"brand": "dcgr"})


def test_ethan_face_under_quote_frame_blocked():
    # anh doc 960x1280 -> cao 1600 tren the 1500, mat xuong toi ~73% the
    loi = _ethan(_ethan_img(960, 1280), faces=[[0.4, 0.45, 0.6, 0.72]])
    assert loi and "khuôn mặt" in loi[0] and "full_bleed" in loi[0], loi


def test_ethan_face_in_upper_half_passes():
    assert _ethan(_ethan_img(960, 1280), faces=[[0.5, 0.2, 0.8, 0.52]]) == []


def test_ethan_short_quote_gives_more_room():
    # LOW-338: quote <= 20% khung nen khung chu thap hon — mat phai xuong thap hon moi cham.
    a, f = _ethan_img(960, 1280), [[0.4, 0.4, 0.6, 0.68]]
    assert _ethan(a, faces=f)                                                 # quote dai: chan
    assert _ethan(a, spec={"hook": "Ngắn gọn thôi.", "attrib": "X"}, faces=f) == []


def test_ethan_full_bleed_chart_stack_or_unmeasured_not_checked():
    low = [[0.4, 0.6, 0.6, 0.9]]
    assert _ethan(_ethan_img(960, 1280), kieu="full_bleed", faces=low) == []
    assert _ethan(_ethan_img(960, 1280, kind="chart"), faces=low) == []
    assert _ethan(_ethan_img(960, 1280), ma2="A2", faces=low) == []
    assert _ethan(_ethan_img(960, 1280, faces=0, subject_box=None), faces=None) == []


def test_ethan_uses_vision_box_when_no_face():
    a = _ethan_img(960, 1280, faces=0, subject_box=[0.2, 0.5, 0.8, 0.9], subject_kind="product")
    loi = _ethan(a, faces=None)
    assert loi and "sản phẩm" in loi[0], loi


def test_ethan_resolve_spec_calls_gate():
    src = (ROOT / "ethan_submit.py").read_text(encoding="utf-8")
    assert "_check_subject_above_quote(spec, kieu, a, ma, ma2, m)" in src


# ------------------------------------------------------------ Kite
def _kite(tmp, kind="photo", faces_n=1, box=None, **k):
    p = Path(tmp) / "A5.png"
    Image.new("RGB", (1500, 1000), (90, 80, 70)).save(p)             # anh ngang -> cao 720
    a = {"id": "A5", "original_path": str(p), "w": 1500, "h": 1000, "kind": kind,
         "faces": faces_n, "subject_box": box, "subject_kind": "person"}
    a.update(k)
    spec_r = {"slides": [{"kind": "cover", "image": str(p)}]}
    return spec_r, {"images": [a]}


def _gate(spec_r, m, top, faces):
    with mock.patch("image_rules_kite.face_boxes", return_value=faces), \
            mock.patch.object(render_edu, "read_background", return_value=("mo", "#000000", False)):
        return kite_submit.check_subject_above_text(spec_r, m, {1: top})


def test_kite_face_under_text_block_blocked():
    with tempfile.TemporaryDirectory() as t:
        spec_r, m = _kite(t)
        # anh cao 720 tu y=150; mat 0.7..0.95 -> day ~150+0.975*720=852 > khoi chu 740
        loi = _gate(spec_r, m, 740, [[0.4, 0.7, 0.6, 0.95]])
        assert loi and "slide 1 (A5)" in loi[0] and "khuôn mặt" in loi[0], loi


def test_kite_face_above_text_block_passes():
    with tempfile.TemporaryDirectory() as t:
        spec_r, m = _kite(t)
        assert _gate(spec_r, m, 740, [[0.4, 0.1, 0.6, 0.6]]) == []


def test_kite_charts_ranking_padded_unmeasured_skipped():
    low = [[0.4, 0.7, 0.6, 0.95]]
    for k in ({"kind": "chart"}, {"ranking": {"board": "x"}}, {"unpadded_path": "/x/u.png"}):
        with tempfile.TemporaryDirectory() as t:
            spec_r, m = _kite(t, **k)
            assert _gate(spec_r, m, 740, low) == [], k
    with tempfile.TemporaryDirectory() as t:
        spec_r, m = _kite(t, faces_n=0, box=None)
        assert _gate(spec_r, m, 740, None) == []
        spec_r, m = _kite(t)
        with mock.patch("image_rules_kite.face_boxes", return_value=low):
            assert kite_submit.check_subject_above_text(spec_r, m, {}) == []      # khong do duoc


def test_kite_vision_box_for_product():
    with tempfile.TemporaryDirectory() as t:
        spec_r, m = _kite(t, faces_n=0, box=[0.2, 0.6, 0.8, 0.98], subject_kind="product")
        loi = _gate(spec_r, m, 740, None)
        assert loi and "sản phẩm" in loi[0], loi


def test_kite_measure_text_tops_real_layout():
    """Do bang Chromium that (CI co cai). Khong co Playwright/Chromium thi bo qua."""
    import importlib.util
    if importlib.util.find_spec("playwright") is None:
        return
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "A1.png"
        Image.new("RGB", (1500, 1000), (90, 80, 70)).save(p)
        spec_r = {"brand": "dcgr.tech", "section": "AI", "folio": "THU", "slides": [
            {"kind": "cover", "eyebrow": "AI", "title": "Tiêu đề bìa", "standfirst": "Một câu dẫn.",
             "image": str(p), "caption": "Ảnh thử · via x"},
            {"kind": "statement", "eyebrow": "A", "title": "B", "cards": []}]}
        try:
            tops = kite_submit.measure_text_tops(spec_r, "dcgr")
        except Exception as e:                                           # noqa: BLE001
            if "Executable doesn't exist" in str(e):
                return
            raise
    assert set(tops) == {1}, tops
    assert 0.4 * render_edu.H < tops[1] < 0.8 * render_edu.H, tops


def test_kite_main_calls_gate_before_render():
    """Cổng chủ thể phải chạy TRƯỚC khi mở Chromium dựng slide.

    Đọc thân `main` chứ không đọc cả tệp (LOW-309): bản cũ so vị trí hai chuỗi
    trong TOÀN tệp, nên tách `_render` ra một hàm đặt phía trên `main` là test
    đỏ dù thứ tự lúc CHẠY không đổi — một phép đo sai chỗ. `_render` cũng phải
    là chỗ DUY NHẤT gọi render_edu.py, không thì thứ tự trong `main` vô nghĩa."""
    import inspect
    than = inspect.getsource(kite_submit.main)
    i_gate = than.index("check_subject_above_text(spec_r, m, tops)")
    i_render = than.index("_render(")
    assert i_gate < i_render, than

    src = (ROOT / "kite_submit.py").read_text(encoding="utf-8")
    assert src.count('str(ROOT / "render_edu.py")') == 1, "có hơn một chỗ gọi render_edu.py"
    assert 'str(ROOT / "render_edu.py")' in inspect.getsource(kite_submit._render)


if __name__ == "__main__":
    ok = 0
    ten = [n for n in dir() if n.startswith("test_")]
    for n in ten:
        try:
            globals()[n]()
            ok += 1
        except AssertionError as e:
            print(f"FAIL {n}: {e}")
    print(f"{ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
