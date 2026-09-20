#!/usr/bin/env python3
"""material.py — gom tư liệu thật cho vai viết (LOW-307, module 0% độ phủ).

Vì sao đáng giữ: trước khi có tệp này, Miles chỉ nhận 3 câu tóm tắt của Finn nên
caption viết ra **không có con số nào**. Tư liệu sai hoặc rỗng không làm hỏng
task — nó ra một caption nghe được mà không có gì thật bên trong, loại lỗi chỉ
Ông Chủ mới bắt được.

Test bằng dữ liệu tổng hợp, KHÔNG mạng: thay `article_extract.py` bằng một script
nhỏ trong thư mục tạm rồi trỏ `material.ROOT` vào đó — nên đường tiến trình con
(mã thoát, `--out`, đọc JSON, dọn tệp tạm) chạy THẬT, chỉ nội dung là giả.

Chay:  venv/bin/python tests/test_material.py
"""
import contextlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import material                                              # noqa: E402

# Script đóng thế `article_extract.py`: đọc bảng JSON cạnh nó, tra theo URL.
FAKE_EXTRACT = '''
import json, sys
from pathlib import Path
url = sys.argv[1]
out = sys.argv[sys.argv.index("--out") + 1]
bang = json.loads((Path(__file__).parent / "bang.json").read_text(encoding="utf-8"))
if url not in bang:
    print("khong boc duoc " + url, file=sys.stderr)
    sys.exit(3)
Path(out).write_text(json.dumps(bang[url], ensure_ascii=False), encoding="utf-8")
print(out)
'''


@contextlib.contextmanager
def _fake_extract(bang):
    """Trỏ `material.ROOT` vào thư mục tạm có article_extract.py giả."""
    cu = material.ROOT
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        (d / "article_extract.py").write_text(FAKE_EXTRACT, encoding="utf-8")
        (d / "bang.json").write_text(json.dumps(bang, ensure_ascii=False), encoding="utf-8")
        material.ROOT = d
        try:
            yield d
        finally:
            material.ROOT = cu


@contextlib.contextmanager
def _other_outlets(ds):
    """Thay `article_images.other_outlets` (đường ra mạng) bằng danh sách định sẵn."""
    import article_images
    cu = article_images.other_outlets
    article_images.other_outlets = lambda tieu_de, link, so=2: ds
    try:
        yield
    finally:
        article_images.other_outlets = cu


# ---------- câu có số liệu ----------

def test_sentence_has_count_keeps_only_sentences_with_numbers():
    doan = ["Mô hình mới ra mắt hôm nay và được nhiều người chú ý rất nhiều nhé.",
            "Điểm SWE-bench đạt 71.2% so với 62.0% của bản trước đó, cách biệt rõ."]
    ra = material.sentence_has_count(doan)
    assert len(ra) == 1 and "71.2%" in ra[0], ra


def test_sentence_has_count_drops_too_short_and_too_long():
    """Dưới 25 ký tự là mẩu vụn, trên 320 là cả đoạn dính liền — cả hai vô dụng."""
    assert material.sentence_has_count(["Giá 25 USD."]) == []
    dai = "Con số 71.2% quan trọng. " + "x" * 400
    assert material.sentence_has_count([dai]) == []


def test_sentence_has_count_drops_duplicates_across_sources():
    """Hai báo chép của nhau: câu y hệt chỉ được vào một lần."""
    c = "Mô hình đạt 71.2% trên SWE-bench, hơn bản cũ 9 điểm phần trăm."
    assert len(material.sentence_has_count([c, c])) == 1


def test_sentence_has_count_keeps_order_of_appearance():
    doan = ["Doanh thu quý này là 1.2 tỷ USD, tăng so với cùng kỳ năm ngoái.",
            "Chi phí huấn luyện khoảng 500 triệu USD theo hãng tự công bố."]
    ra = material.sentence_has_count(doan)
    assert len(ra) == 2 and ra[0].startswith("Doanh thu"), ra


# ---------- bóc bài qua tiến trình con ----------

def test_extract_reads_json_and_cleans_temp_file():
    with _fake_extract({"https://a.test/1": {"paragraphs": ["Một đoạn."], "title": "A"}}):
        d = material.extract("https://a.test/1")
    assert d["title"] == "A" and d["paragraphs"] == ["Một đoạn."], d


def test_extract_nonzero_exit_then_empty_and_says_why(capsys=None):
    """Bug thật trên dcgr: article_extract chết vì thiếu bs4, tư liệu ra {} IM LẶNG."""
    import io
    cu = sys.stderr
    sys.stderr = io.StringIO()
    try:
        with _fake_extract({}):
            d = material.extract("https://a.test/khong-co")
        ra = sys.stderr.getvalue()
    finally:
        sys.stderr = cu
    assert d == {}, d
    assert "article_extract loi rc=3" in ra and "khong boc duoc" in ra, ra


# ---------- gom tư liệu ----------

def _bang(so_bao_khac=1):
    bang = {"https://goc.test/bai": {"title": "Bài gốc",
                                     "paragraphs": ["Mô hình đạt 71.2% trên SWE-bench, hơn bản cũ 9 điểm."]}}
    for i in range(so_bao_khac):
        bang[f"https://bao{i}.test/x"] = {
            "title": f"Báo {i}",
            "paragraphs": [f"Hãng cho biết chi phí huấn luyện khoảng {i + 1}00 triệu USD."]}
    return bang


def test_gather_uses_saved_sources_instead_of_searching_again():
    """Bài viết phải giải thích đúng cái độc giả thấy trên ảnh — dùng LẠI nguồn của ảnh."""
    with _fake_extract(_bang()) as d:
        ns = d / "nguon.json"
        ns.write_text(json.dumps({"pages": [{"url": "https://goc.test/bai"},
                                            {"url": "https://bao0.test/x"}]}), encoding="utf-8")
        goi = []
        with _other_outlets([("https://khong-duoc-goi.test/z", "")]):
            import article_images
            that = article_images.other_outlets
            article_images.other_outlets = lambda *a, **k: goi.append(1) or that(*a, **k)
            tl = material.gather("Tin", "https://goc.test/bai", 2, str(ns))
    assert goi == [], "đã có nguồn sẵn mà vẫn đi tìm lại"
    assert [n["url"] for n in tl["sources"]] == ["https://goc.test/bai", "https://bao0.test/x"], tl


def test_gather_skips_the_original_link_inside_saved_sources():
    """Link gốc đã bóc rồi: không được bóc lại thành 'báo đưa tin'."""
    with _fake_extract(_bang(2)) as d:
        ns = d / "nguon.json"
        ns.write_text(json.dumps({"pages": [{"url": "https://goc.test/bai"},
                                            {"url": "https://bao0.test/x"},
                                            {"url": "https://bao1.test/x"}]}), encoding="utf-8")
        tl = material.gather("Tin", "https://goc.test/bai", 2, str(ns))
    assert [n["label"] for n in tl["sources"]] == ["bài gốc", "báo đưa tin", "báo đưa tin"], tl


def test_gather_falls_back_to_search_when_no_saved_sources():
    with _fake_extract(_bang()):
        with _other_outlets([("https://bao0.test/x", "Báo 0")]):
            tl = material.gather("Tin", "https://goc.test/bai", 2, None)
    assert [n["url"] for n in tl["sources"]] == ["https://goc.test/bai", "https://bao0.test/x"], tl


def test_gather_survives_search_blowing_up():
    """Mất báo khác không được làm mất luôn bài gốc."""
    import article_images
    cu = article_images.other_outlets

    def no(*a, **k):
        raise RuntimeError("mang hong")
    article_images.other_outlets = no
    try:
        with _fake_extract(_bang()):
            tl = material.gather("Tin", "https://goc.test/bai", 2, None)
    finally:
        article_images.other_outlets = cu
    assert [n["url"] for n in tl["sources"]] == ["https://goc.test/bai"], tl


def test_gather_collects_number_sentences_from_every_source():
    with _fake_extract(_bang()):
        with _other_outlets([("https://bao0.test/x", "Báo 0")]):
            tl = material.gather("Tin", "https://goc.test/bai", 2, None)
    chu = " ".join(tl["number_sentences"])
    assert "71.2%" in chu and "100 triệu USD" in chu, tl["number_sentences"]


def test_gather_source_without_paragraphs_is_dropped():
    with _fake_extract({"https://goc.test/bai": {"title": "Rỗng", "paragraphs": []}}):
        with _other_outlets([]):
            tl = material.gather("Tin", "https://goc.test/bai", 2, None)
    assert tl["sources"] == [] and tl["number_sentences"] == [], tl


# ---------- dựng trang tư liệu ----------

def test_use_page_puts_numbers_first_and_marks_when_none():
    tl = {"title": "T", "link": "L", "sources": [], "number_sentences": []}
    trang = material.use_page(tl)
    assert "*Không tìm thấy câu nào mang số liệu.*" in trang
    assert "KHÔNG bịa" not in trang            # dòng đó của brief, không của đây
    assert "không được đoán" in trang, trang


def test_use_page_cuts_long_source_and_says_so():
    dai = "x" * (material.TEXT_MAX + 50)
    tl = {"title": "T", "link": "L", "number_sentences": [],
          "sources": [{"label": "bài gốc", "url": "u", "title": "A",
                       "paragraphs": [dai, "đoạn sau bị cắt"]}]}
    trang = material.use_page(tl)
    assert "*(cắt bớt)*" in trang and "đoạn sau bị cắt" not in trang


def test_use_page_caps_number_sentences_at_25():
    tl = {"title": "T", "link": "L", "sources": [],
          "number_sentences": [f"cau so {i}" for i in range(40)]}
    trang = material.use_page(tl)
    assert trang.count("\n- cau so ") == 25, trang.count("\n- cau so ")


# ---------- dòng lệnh ----------

def test_main_writes_file_and_prints_path():
    with _fake_extract(_bang()) as d:
        out = d / "tu_lieu.md"
        cu = sys.argv
        sys.argv = ["material.py", "--tieu-de", "Tin", "--link", "https://goc.test/bai",
                    "--out", str(out), "--so-bai-khac", "0"]
        try:
            with _other_outlets([]):
                material.main()
        finally:
            sys.argv = cu
        chu = out.read_text(encoding="utf-8")
    assert chu.startswith("# Tư liệu: Tin") and "71.2%" in chu, chu[:200]


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
