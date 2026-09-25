#!/usr/bin/env python3
"""LOW-415 (25/09/2026): bộ ép của Kite đòi ảnh mà cổng "không dùng lại ảnh" chặn.

Hai bài dừng hẳn ngày 25/09, cùng một kiểu:
  - OpenEvidence (blog): `figure_right_use` ép A14 (chân dung Sam Altman, Commons),
    `check_not_reused` chặn vì A14 đã lên bài `chatgpt-now-knows-…-kite` 21/09.
  - Thẩm phán Mỹ chất vấn ByteDance (dcgr): ép A3 (toà nhà ByteDance), cổng chặn vì
    đã lên bài `byteplus-cua-bytedance-…-kite` 22/09.
Dùng thì dính trùng, bỏ thì thiếu mã ép — vai không còn đường nộp. Cặp cổng thứ ba
sau hai cặp của LOW-337: bộ ép và bìa phải hỏi CÙNG cổng `check_not_reused`.

Chạy:  venv/bin/python tests/test_low415_force_reused.py
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
from test_spec_dre import _co, _ve  # noqa: E402
from test_spec_kite import _chay, _cover, _figure, _m, _statement  # noqa: E402

OTHER_POST = "chatgpt-now-knows-what-you-do-on-oth-kite-donniechublog"


def _photo(wd, image_id, seed, w=1200, h=800):
    """Ảnh CHỤP, mỗi mã một hoa văn riêng (`seed`) để dHash không coi chúng là một."""
    path = wd / state_paths.ORIGINAL_DIR / f"{image_id}.png"
    path.parent.mkdir(parents=True, exist_ok=True)
    _ve(w, h, seed=seed).save(path)
    return {"id": image_id, "original_path": str(path), "w": w, "h": h, "ratio": round(w / h, 2),
            "kind": "photo", "relevant": True, "domain": "commons.wikimedia.org",
            "source": "commons", "notes": [], "faces": 0, "description": "ảnh chụp"}


def _transferred(wd, images):
    return _m(wd, images, kite_task_id="t_415")


def _used_by_other_post(image, draft_id=OTHER_POST, link="https://vi.du/bai-khac"):
    image_rules_kite.record_used(image["original_path"], draft_id, "kite", link)


def _set(wd):
    return [_photo(wd, "A1", 1), _photo(wd, "A2", 2), _photo(wd, "A3", 3), _photo(wd, "A4", 4)]


def test_force_drops_image_used_by_another_post():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        images = _set(wd)
        _used_by_other_post(images[2])                       # A3 da len bai khac
        m = _transferred(wd, images)
        assert kb._force_raw(m) == ["A1", "A2", "A4"], kb._force_raw(m)
        assert "A3" not in kb.figure_right_use(m), kb.figure_right_use(m)
        assert "TRUNG" in kb.reused_elsewhere(images[2], m)
        assert kb.reused_elsewhere(images[0], m) == ""


def test_hero_skips_image_used_by_another_post():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        images = _set(wd)
        _used_by_other_post(images[0])                       # A1 dang dung dau hang bia
        hero = kb.figure_hero(_transferred(wd, images))
        assert hero and hero["id"] != "A1", hero


def test_submit_following_the_force_list_passes_both_gates():
    """Bộ đặt đúng như brief đòi (bìa = hero, mỗi mã ép một slide `figure`) thì cổng
    trùng liên phiên lẫn cổng thiếu mã ép đều im — trên code cũ một trong hai kêu."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        images = _set(wd)
        _used_by_other_post(images[2])
        m = _transferred(wd, images)
        hero = kb.figure_hero(m)
        forced = kb.figure_right_use(m)
        slides = ([_cover(image=hero["id"], caption="Ảnh · via Commons")]
                  + [_figure(image_id) for image_id in forced]
                  + [_statement(title=f"Ý {i}") for i in range(len(forced) + 2, 7)])
        _r, errors, _w = _chay(slides, m, wd)
        assert not _co(errors, "TRUNG anh da dung"), errors
        assert not _co(errors, "còn thiếu"), errors


def test_same_draft_or_same_story_is_not_reuse():
    """Làm lại chính bài này, hoặc vai khác đã dùng ảnh cho CÙNG tin: không phải dùng
    lại — bộ ép giữ nguyên (cổng `check_not_reused` bỏ qua hai trường hợp đó)."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        images = _set(wd)
        m = _transferred(wd, images)
        _used_by_other_post(images[1], draft_id=m["draft_id"])
        _used_by_other_post(images[2], draft_id="tin-thu-dre", link=m["link"])
        assert kb._force_raw(m) == ["A1", "A2", "A3", "A4"], kb._force_raw(m)


def test_reuse_verdict_refreshes_when_the_log_grows():
    """Kết quả được nhớ theo dấu của sổ ảnh đã dùng: sổ thêm dòng thì phải hỏi lại."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        images = _set(wd)
        _used_by_other_post(images[3])                       # so phai ton tai tu dau
        m = _transferred(wd, images)
        assert kb.reused_elsewhere(images[0], m) == ""
        _used_by_other_post(images[0])
        assert "TRUNG" in kb.reused_elsewhere(images[0], m)


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
