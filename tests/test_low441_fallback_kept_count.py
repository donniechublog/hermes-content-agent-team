#!/usr/bin/env python3
"""LOW-441 (30/09/2026) — trần vòng bổ sung đếm `len(anh)` gồm cả ảnh ĐÃ LOẠI.

LOW-267 chỉ vá vòng thương hiệu (`_round_brand` đếm `_count_kept`). Ba vòng còn
lại — tìm rộng (`MAX_IMAGE + 4`), thực thể và khái niệm (`MAX_IMAGE + 6`) — vẫn
so `len(anh)`: tải về 20 ảnh, vision loại 15, thì 20 >= 14 và vòng dừng ngay
("+0 anh") dù bộ chỉ còn 5 ảnh dùng được.

Mã tệp `A<i>` vẫn phải đánh tiếp từ `len(anh)` (kể cả ảnh loại) — ảnh loại vẫn
nằm trong manifest với tệp của nó, đánh số theo số ảnh giữ là đè tệp cũ.

Không mạng: mọi nguồn ứng viên, tải/lọc và con mắt đều giả.

Chạy:  venv/bin/python tests/test_low441_fallback_kept_count.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import state_paths                                            # noqa: E402
from prepare import fallback_rounds                           # noqa: E402


def _stocked(d: Path, kept: int, dropped: int) -> list:
    """Bộ ảnh sẵn có: `kept` ảnh giữ + `dropped` ảnh đã loại, mỗi ảnh một tệp
    A<i>.png có nội dung riêng để kiểm không bị đè."""
    od = d / state_paths.ORIGINAL_DIR
    od.mkdir(parents=True, exist_ok=True)
    anh = []
    for i in range(1, kept + dropped + 1):
        p = od / f"A{i}.png"
        p.write_bytes(f"cu-{i}".encode())
        giu = i <= kept
        anh.append({"id": f"A{i}", "url": f"https://x/{i}.jpg", "original_path": str(p),
                    "uses": ["body"] if giu else [], "relevant": True if giu else False})
    return anh


def _fake_download(cands, wd, da_giu=()):
    wd.mkdir(parents=True, exist_ok=True)
    ra = []
    for i, c in enumerate(cands):
        p = wd / f"tai_{i}.png"
        p.write_bytes(f"moi-{c['image_url']}".encode())
        ra.append(dict(c, url=c["image_url"], original_path=str(p)))
    return ra


def _fake_classify(a, wd, tieu_de):
    a["uses"] = ["body"]
    a["relevant"] = True
    return a


def _cands(prefix: str, n: int, **them) -> list:
    return [dict({"image_url": f"https://{prefix}/{i}.jpg", "alt": "", "source": prefix,
                  "w": 1600, "h": 1000, "page_url": f"https://{prefix}/p", "score": 10}, **them)
            for i in range(n)]


def _assert_no_overwrite(d: Path, anh: list, n_cu: int):
    ids = [a["id"] for a in anh]
    assert len(ids) == len(set(ids)), f"trung ma anh: {ids}"
    od = d / state_paths.ORIGINAL_DIR
    for i in range(1, n_cu + 1):
        assert (od / f"A{i}.png").read_bytes() == f"cu-{i}".encode(), f"A{i}.png bi de"
    for a in anh[n_cu:]:
        assert Path(a["original_path"]).read_bytes().startswith(b"moi-"), a


# ------------------------------------------------------------- vong thuc the
def _run_entity(d: Path, anh: list):
    cands = _cands("wiki", 3, entity={"name": "Acme"})
    with mock.patch("entity_images.entity_images", return_value=cands), \
         mock.patch("entity_images.label_entity", side_effect=lambda a: a), \
         mock.patch("ranking.extract_model", return_value=[]), \
         mock.patch.object(fallback_rounds, "download_and_filter", side_effect=_fake_download), \
         mock.patch.object(fallback_rounds, "classify", side_effect=_fake_classify):
        return fallback_rounds._round_entity(anh, "Acme ships a thing", d)


def test_round_entity_dropped_images_do_not_fill_cap():
    """20 ảnh, 15 đã loại: vòng thực thể vẫn thêm được 3 ảnh (trước: +0)."""
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        anh = _stocked(d, kept=5, dropped=15)
        assert len(anh) >= fallback_rounds.MAX_IMAGE + 6
        ra, dung_duoc, _ = _run_entity(d, anh)
        assert len(ra) == 23, f"vong thuc the +{len(ra) - 20} anh (anh da loai van chiem tran)"
        assert [a["id"] for a in ra[20:]] == ["A21", "A22", "A23"]
        assert len(dung_duoc) == 8, len(dung_duoc)
        _assert_no_overwrite(d, ra, 20)


def test_round_entity_cap_still_applies_when_kept_full():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        anh = _stocked(d, kept=fallback_rounds.MAX_IMAGE + 6, dropped=2)
        ra, _, _ = _run_entity(d, anh)
        assert len(ra) == fallback_rounds.MAX_IMAGE + 8, len(ra)


# ------------------------------------------------------------- vong khai niem
def _run_concept(d: Path, anh: list):
    with mock.patch("story_type.late", return_value=False), \
         mock.patch("image_concept.keyword_concept",
                    return_value=[{"keyword": "datacenter", "reason": "x"}]), \
         mock.patch("image_concept.image_concept", return_value=_cands("concept", 2)), \
         mock.patch.object(fallback_rounds, "download_and_filter", side_effect=_fake_download), \
         mock.patch.object(fallback_rounds, "classify", side_effect=_fake_classify):
        return fallback_rounds._round_concept(anh, "Acme builds datacenter", "", d)


def test_round_concept_dropped_images_do_not_fill_cap():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        anh = _stocked(d, kept=5, dropped=15)
        ra, _, _ = _run_concept(d, anh)
        assert len(ra) == 22, f"vong khai niem +{len(ra) - 20} anh"
        assert [a["id"] for a in ra[20:]] == ["A21", "A22"]
        _assert_no_overwrite(d, ra, 20)


def test_round_concept_cap_still_applies_when_kept_full():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        anh = _stocked(d, kept=fallback_rounds.MAX_IMAGE + 6, dropped=0)
        ra, _, _ = _run_concept(d, anh)
        assert len(ra) == fallback_rounds.MAX_IMAGE + 6, len(ra)


# ------------------------------------------------------------- vong tim rong
def _run_widen(d: Path, anh: list, n_cands: int = 3):
    with mock.patch("article_sources.other_outlets_bing", return_value=[]), \
         mock.patch("press_entity_images.press_entity_images", return_value=[]), \
         mock.patch("find_image_web.find_image_web", return_value=_cands("yandex", n_cands)), \
         mock.patch.object(fallback_rounds, "_model_over_parent", return_value="Acme"), \
         mock.patch.object(fallback_rounds, "commons_images", return_value=[]), \
         mock.patch.object(fallback_rounds, "download_and_filter", side_effect=_fake_download), \
         mock.patch.object(fallback_rounds, "classify", side_effect=_fake_classify):
        dung = [a for a in anh if a["uses"]]
        return fallback_rounds._round_widen_search(anh, [], "Acme ships a thing", 5, dung, d)


def test_round_widen_search_dropped_images_do_not_fill_cap():
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        anh = _stocked(d, kept=5, dropped=15)
        assert len(anh) >= fallback_rounds.MAX_IMAGE + 4
        ra, dung_duoc, _ = _run_widen(d, anh)
        assert len(ra) == 23, f"vong tim rong +{len(ra) - 20} anh"
        assert [a["id"] for a in ra[20:]] == ["A21", "A22", "A23"]
        assert len(dung_duoc) == 8, len(dung_duoc)
        _assert_no_overwrite(d, ra, 20)


def test_round_widen_search_cap_counts_kept():
    """Trần vẫn còn: 10 ảnh giữ + 15 loại, 5 ứng viên -> chỉ thêm tới 12 ảnh giữ."""
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        anh = _stocked(d, kept=10, dropped=15)
        ra, _, _ = _run_widen(d, anh, n_cands=5)
        assert sum(1 for a in ra if a["uses"]) == fallback_rounds.MAX_IMAGE + 4
        _assert_no_overwrite(d, ra, 25)


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
