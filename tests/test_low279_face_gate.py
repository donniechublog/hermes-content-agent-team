#!/usr/bin/env python3
"""LOW-279 (19/09/2026) — cổng "mặt người không rõ ai" loại oan ba ảnh thật của Lovable
(dcgr, tin "Lovable mua Sutro"), Dre báo thiếu ảnh dù hãng có dư ảnh:

  A26  tay cầm điện thoại chạy app Lovable — "mặt" là avatar tí hon trong giao diện
       (cao 3.2% ảnh, đo YuNet trên máy chủ);
  A38  Anton Osika với lower-third in sẵn "Anton Osika / Lovable CEO" — cổng chỉ đọc
       alt/tên tệp nên coi là "không rõ ai";
  A39  ảnh tập thể 209 người của đội Lovable — luật khai tên cho chân dung áp vào đám đông.

Mỗi phần có ca ĐÚNG-PHẢI-QUA đi kèm ca SAI-VẪN-CHẶN (người lạ trong ảnh stock, họp
4 người lạ, diễn giả nổi bật giữa khán giả).

Chạy:  venv/bin/python tests/test_low279_face_gate.py
"""
import importlib.util
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image  # noqa: E402

import image_rules_dre as dre  # noqa: E402
import image_rules_ethan  # noqa: E402
import image_rules_kite  # noqa: E402
import prepare.vision as vision  # noqa: E402
import role  # noqa: E402
import subject_fit  # noqa: E402


def _box(h, y0=0.1, x0=0.4):
    """Hop mat 0..1 cao `h` (rong bang cao)."""
    return [x0, y0, x0 + h, y0 + h]


# ------------------------------------------------ 1. mat nao doi khai ten
def test_avatar_in_app_ui_not_counted():
    assert subject_fit.faces_needing_name([_box(0.032)]) == 0          # A26


def test_stranger_in_stock_photo_still_counted():
    # A1 "nu nhan vien di trong hanh lang trung tam du lieu": mat cao 7.2% anh
    assert subject_fit.faces_needing_name([_box(0.072)]) == 1
    assert subject_fit.faces_needing_name([_box(0.33)]) == 1            # chan dung


def test_crowd_without_focus_not_counted():
    tap_the = [_box(0.02 + 0.028 * (i % 10) / 10, y0=0.01 * (i % 50)) for i in range(209)]
    assert max(b[3] - b[1] for b in tap_the) < subject_fit.CROWD_FACE_HEIGHT_MAX
    assert subject_fit.faces_needing_name(tap_the) == 0                 # A39


def test_small_meeting_of_strangers_still_counted():
    # hop 4 nguoi la (mat 14% anh): khong phai dam dong, van phai khai ten
    assert subject_fit.faces_needing_name([_box(0.14, x0=0.2 * i) for i in range(4)]) == 4


def test_standout_speaker_in_crowd_still_counted():
    # 18 mat, dien gia tren san khau cao 11% anh: co tieu diem -> khong mien
    mat = [_box(0.03, y0=0.5 + 0.02 * i) for i in range(16)] + [_box(0.11), _box(0.11, x0=0.1)]
    assert subject_fit.faces_needing_name(mat) == 2


def test_none_means_gate_did_not_run():
    assert subject_fit.faces_needing_name(None) is None
    assert subject_fit.faces_needing_name([]) == 0


class _Det:
    """Detector YuNet gia: tra cac hop mat pixel [x, y, w, h] cho truoc."""

    def __init__(self, rows):
        self.rows = rows
        self.wh = None

    def setInputSize(self, wh):
        self.wh = tuple(wh)

    def detect(self, im):
        return 0, (self.rows or None)


def _count_with(mod, rows, w=1426, h=800):
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "a.png"
        Image.new("RGB", (w, h), (90, 90, 90)).save(p)
        cu = mod._load_yunet
        mod._load_yunet = lambda: _Det(rows)
        try:
            return mod.count_faces(p)
        finally:
            mod._load_yunet = cu


def test_count_faces_three_roles_same_rule():
    if importlib.util.find_spec("cv2") is None:
        print("   (bo qua: may nay khong co cv2)")
        return
    avatar = [[1000, 60, 25, 25]]                   # 25px / 800px = 3.1% -> A26
    chan_dung = [[500, 100, 260, 280]]              # 35% -> A38
    for mod in (dre, image_rules_ethan, image_rules_kite):
        assert _count_with(mod, avatar) == 0, mod.__name__
        assert _count_with(mod, chan_dung) == 1, mod.__name__
        assert _count_with(mod, []) == 0, mod.__name__


def test_unnamed_face_gate_lets_avatar_through():
    if importlib.util.find_spec("cv2") is None:
        return
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "a26.png"
        Image.new("RGB", (1426, 800), (90, 90, 90)).save(p)
        cu = dre._load_yunet
        dre._load_yunet = lambda: _Det([[1000, 60, 25, 25]])
        try:
            loi, _canh = dre.check_unnamed_face("slide 3", p, None)
        finally:
            dre._load_yunet = cu
    assert loi == [], loi


# ------------------------------------------------ 2. ten IN tren anh
def test_parse_printed_name():
    assert vision.parse_printed_name("MO_TA: x\nTEN_IN: Anton Osika") == "Anton Osika"
    assert vision.parse_printed_name("TÊN_IN: \"Anton Osika\"") == "Anton Osika"
    assert vision.parse_printed_name("TEN_IN: khong") is None
    assert vision.parse_printed_name("TEN_IN: không") is None
    assert vision.parse_printed_name("MO_TA: x\nLIEN_QUAN: co") is None


def test_printed_name_makes_face_named():
    a38 = {"faces": 1, "alt": "", "url": "https://assets.bwbx.io/images/users/x/-1x-1.webp",
           "printed_name": "Anton Osika"}
    assert role.person_names_of(a38) == ["Anton Osika"]
    assert role.face_no_clear_ai(a38) is False
    assert dre.subject_names(a38) == ["Anton Osika"]


def test_no_printed_name_still_unknown():
    a1 = {"faces": 1, "alt": "", "url": "https://www.unite.ai/wp-content/uploads/x.jpg",
          "printed_name": None,
          "description": "Ảnh minh họa nữ nhân viên đi trong hành lang trung tâm dữ liệu."}
    assert role.face_no_clear_ai(a1) is True


def test_printed_nonperson_text_not_a_name():
    # chu in tren anh khong phai ten nguoi (bien hieu, dia danh) -> khong bao lanh
    a = {"faces": 1, "alt": "", "url": "", "printed_name": "San Francisco"}
    assert role.face_no_clear_ai(a) is True


class _Resp:
    def __init__(self, txt: str):
        self._b = json.dumps({"choices": [{"message": {"content": txt}}]}).encode()

    def read(self):
        return self._b


def test_vision_asks_printed_name_and_returns_it():
    gui = {}

    def _goi(req, _ngu=None):
        gui["hoi"] = json.loads(req.data)["messages"][0]["content"][0]["text"]
        return _Resp("MO_TA: Anton Osika phát biểu.\nLIEN_QUAN: co\nTEN_IN: Anton Osika")

    kq = {}
    with tempfile.TemporaryDirectory() as t, \
            mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}), \
            mock.patch.object(vision, "_call_router", side_effect=_goi):
        p = Path(t) / "a.png"
        Image.new("RGB", (1920, 1080), (40, 40, 40)).save(p)
        ra = vision.description_image(str(p), "Lovable Acquires Sutro", ket_qua=kq)
    assert ra == ("Anton Osika phát biểu.", True)
    assert "TEN_IN:" in gui["hoi"] and "DUNG 7 dong" in gui["hoi"], gui["hoi"]
    assert kq["printed_name"] == "Anton Osika", kq


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
