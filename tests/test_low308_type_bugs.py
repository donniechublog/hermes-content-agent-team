#!/usr/bin/env python3
"""Hai chỗ `None` ĐI TỚI NƠI thật, mypy chỉ ra (LOW-308).

Cả hai đều là loại hỏng đúng lúc đang khó: đường LÙI của một hàm, hoặc một tệp
ảnh biến mất. Chúng không bao giờ xuất hiện trong luồng chạy tốt, nên không test
nào cũ chạm tới — và khi xảy ra thì thông báo lỗi chẳng nói gì về nguyên nhân.

  1. `article_extract.extract` — `soup.title.string` là **None** khi `<title>`
     rỗng. Đây là đường lùi khi trang không có `og:title`, tức đúng lúc trang đã
     khó bóc; `.strip()` trên None giết cả lần bóc, và `material.py` chỉ thấy
     tiến trình con thoát khác 0 — không biết vì sao.
  2. `gin_submit.single` — `cv2.imread` trả **None** khi tệp không còn/không đọc
     được (link tạm hết hạn, tải hỏng). Trước đây None đi tiếp vào `use_mask`
     rồi nổ ra một lỗi numpy ở giữa chừng.

Chay:  venv/bin/python tests/test_low308_type_bugs.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import article_extract as ae                                 # noqa: E402
import state_paths                                           # noqa: E402


def _boc(html):
    cu = ae.fetch
    ae.fetch = lambda url: html
    try:
        return ae.extract("https://bao.test/bai")
    finally:
        ae.fetch = cu


def test_empty_title_tag_does_not_kill_extraction():
    """`<title></title>` + không og:title: trước đây AttributeError trên None."""
    d = _boc("<html><head><title></title></head><body><article>"
             "<p>Một đoạn văn đủ dài để tính.</p></article></body></html>")
    assert d["title"] == "", d["title"]
    assert d["paragraphs"] == ["Một đoạn văn đủ dài để tính."], d


def test_title_with_markup_stays_literal_text():
    """`<title>` là RCDATA theo chuẩn HTML: thẻ bên trong KHÔNG thành thẻ, nó là
    chữ. Bản vá không được đổi điều đó — chỉ đổi cái trước đây NỔ."""
    d = _boc("<html><head><title>Hãng <b>mở</b> kho</title></head>"
             "<body><article><p>Một đoạn văn đủ dài.</p></article></body></html>")
    assert d["title"] == "Hãng <b>mở</b> kho", d["title"]


def test_plain_title_unchanged():
    """Đường thường không được đổi: chữ vẫn y nguyên, vẫn cắt khoảng trắng."""
    d = _boc("<html><head><title>  Tiêu đề thường  </title></head>"
             "<body><article><p>Một đoạn văn đủ dài.</p></article></body></html>")
    assert d["title"] == "Tiêu đề thường", d["title"]


def test_og_title_still_wins_over_title_tag():
    d = _boc('<html><head><title>Thẻ title</title>'
             '<meta property="og:title" content="Tiêu đề OG"></head>'
             "<body><article><p>Một đoạn văn đủ dài.</p></article></body></html>")
    assert d["title"] == "Tiêu đề OG", d["title"]


def test_missing_image_file_says_which_file_not_a_numpy_error():
    """gin_submit: ảnh gốc biến mất -> một câu đọc được, kèm lệnh chạy lại."""
    import gin_submit
    with tempfile.TemporaryDirectory() as t:
        wd = Path(t)
        mat = wd / "khong-co-that.png"
        (wd / state_paths.GIN_REGIONS_OCR_FILE).write_text(
            json.dumps({"image_path": str(mat),
                        "regions": [{"number": 1, "x": 0, "y": 0, "w": 5, "h": 5,
                                     "box": [[0, 0], [5, 0], [5, 5], [0, 5]],
                                     "text": "X", "conf": 0.9}]}),
            encoding="utf-8")
        try:
            gin_submit.single("777", wd, {})
        except SystemExit as e:
            assert "khong doc duoc anh goc" in str(e.code), e.code
            assert mat.name in str(e.code), e.code
            assert "gin_prepare.py" in str(e.code), e.code
            return
    raise AssertionError("ảnh không đọc được mà vẫn đi tiếp")


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
