#!/usr/bin/env python3
"""LOW-426 (30/09/2026): bộ ép/bìa của Kite phải hỏi CÙNG cổng ảnh với cổng nộp.

Ca kẹt: Kite t_d35f8cf7 (dcgr, bài chuyển từ Dre). `_force_raw` ép A5 (ảnh có viền màu đặc hai
bên, trái 14,4% / phải 5,8%) và bộ chọn bìa lấy A4 (2 mặt người, ảnh stock vô danh). Cổng nộp
chặn cả hai (`check_side_bars`, `check_unnamed_face`). Bỏ mã thì cổng ép chặn, giữ mã thì cổng nộp
chặn — Kite dừng chờ người. Cặp thứ tư/năm sau LOW-278/288 (ảnh trống), LOW-337 (trùng ảnh),
LOW-415 (ảnh đã dùng).

Chạy:  venv/bin/python tests/test_low426_force_shared_gate.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import image_rules_kite  # noqa: E402
import kite_prepare as kb  # noqa: E402
import state_paths  # noqa: E402
from tam import so_tam  # noqa: E402
from test_spec_dre import _ve  # noqa: E402
from test_spec_kite import _m  # noqa: E402


def _photo(wd, image_id, seed, w=1200, h=800, bars=None):
    """Ảnh chụp; `bars=(trái, phải)` là tỉ lệ mảng màu đặc dán hai bên."""
    path = wd / state_paths.ORIGINAL_DIR / f"{image_id}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    im = _ve(w, h, seed=seed).convert("RGB")
    if bars:
        im.paste((236, 236, 236), (0, 0, int(w * bars[0]), h))
        im.paste((236, 236, 236), (w - int(w * bars[1]), 0, w, h))
    im.save(path)
    return {"id": image_id, "original_path": str(path), "w": w, "h": h, "ratio": round(w / h, 2),
            "kind": "photo", "relevant": True, "domain": "commons.wikimedia.org",
            "source": "commons", "notes": [], "faces": 0, "description": "ảnh chụp"}


def _with_faces(paths_to_faces):
    """Giả `count_faces`: {đường dẫn: số mặt}, còn lại 0 mặt (không cần cv2/model)."""
    saved = image_rules_kite.count_faces
    image_rules_kite.count_faces = lambda p: paths_to_faces.get(str(p), 0)
    return saved


def test_side_bar_image_is_not_forced_and_never_hero():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        a5 = _photo(wd, "A5", 5, bars=(0.144, 0.058))
        good = [_photo(wd, "A1", 1), _photo(wd, "A2", 2), _photo(wd, "A3", 3)]
        m = _m(wd, good + [a5], kite_task_id="t_426")
        assert "viền" in image_rules_kite.gate_errors("A5", a5["original_path"])[0][0].lower() \
            or "VIEN" in image_rules_kite.gate_errors("A5", a5["original_path"])[0][0]
        assert "A5" not in kb._force_raw(m) and "A5" not in kb.figure_right_use(m)
        hero = kb.figure_hero(m)
        assert hero and hero["id"] != "A5", hero
        assert kb.gate_blocked(a5) and kb.gate_blocked(good[0]) == ""


def test_unnamed_face_image_is_not_forced_or_hero_but_named_portrait_is():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        a4 = _photo(wd, "A4", 4)                              # stock 2 mặt, vô danh
        chan_dung = _photo(wd, "A6", 6)                       # chân dung hãng: đã biết tên
        chan_dung["brand_match"] = {"kind": "person", "person": "Sam Altman", "company": "OpenAI"}
        good = [_photo(wd, "A1", 1), _photo(wd, "A2", 2)]
        saved = _with_faces({a4["original_path"]: 2, chan_dung["original_path"]: 1})
        try:
            m = _m(wd, good + [a4, chan_dung], kite_task_id="t_426")
            ep = kb._force_raw(m)
            assert "A4" not in ep and "A4" not in kb.figure_right_use(m), ep
            assert "A6" in ep, f"chân dung có tên khai được `subject` — không được loại: {ep}"
            hero = kb.figure_hero(m)
            assert hero and hero["id"] != "A4", hero
        finally:
            image_rules_kite.count_faces = saved


def test_every_forced_image_passes_the_submit_gate():
    """Tính chất chốt: mọi mã ép/hero KHÔNG bị `gate_errors` (cổng nộp) chặn — bất kể luật nào
    được thêm vào `gate_errors` sau này, vì bộ ép hỏi đúng hàm đó."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        imgs = [_photo(wd, "A1", 1), _photo(wd, "A2", 2, bars=(0.15, 0.06)),
                _photo(wd, "A3", 3), _photo(wd, "A4", 4), _photo(wd, "A5", 5)]
        saved = _with_faces({imgs[3]["original_path"]: 2})
        try:
            m = _m(wd, imgs, kite_task_id="t_426")
            hero = kb.figure_hero(m)
            ids = kb._force_raw(m) + ([hero["id"]] if hero else [])
            assert ids, "bộ này còn ảnh hợp lệ"
            by = {a["id"]: a for a in imgs}
            for ma in ids:
                loi, _ = image_rules_kite.gate_errors(ma, by[ma]["original_path"])
                assert loi == [], (ma, loi)
        finally:
            image_rules_kite.count_faces = saved


def test_all_images_blocked_leaves_no_forced_code_so_kite_is_not_stuck():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        imgs = [_photo(wd, "A1", 1, bars=(0.15, 0.06)), _photo(wd, "A2", 2, bars=(0.2, 0.2))]
        m = _m(wd, imgs, kite_task_id="t_426")
        assert kb._force_raw(m) == [] and kb.figure_right_use(m) == []


def test_submit_uses_the_same_function():
    src = (ROOT / "kite_submit.py").read_text(encoding="utf-8")
    assert "image_rules_kite.gate_errors(nhan, img_path" in src
    for cu in ("check_side_bars(nhan, _im)", "check_unnamed_face(nhan, img_path"):
        assert cu not in src, f"cổng nộp còn gọi thẳng {cu} — sẽ lệch khỏi bộ ép"


if __name__ == "__main__":
    ok = fail = 0
    for k, f in sorted(globals().items()):
        if k.startswith("test_") and callable(f):
            try:
                f()
                print("OK  ", k)
                ok += 1
            except Exception as e:                                   # noqa: BLE001
                print(f"FAIL {k}: {type(e).__name__}: {e}")
                fail += 1
    print(f"\n{ok}/{ok + fail} test qua")
    sys.exit(1 if fail else 0)
