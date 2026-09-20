#!/usr/bin/env python3
"""article_extract.py — bóc thân bài ra JSON (LOW-307, module 0% độ phủ).

Đây là cái miệng ăn của cả dây chuyền chữ: `material.py` (tư liệu cho writer) và
`cape_prepare.py` (teaser) đều bóc bằng tệp này. Hai loại lỗi đã có thật ở đây:

  * **đoạn bị nhân đôi** khi thiếu `lxml` — `html.parser` lồng đoạn sau vào đoạn
    trước trên `<p>` không đóng (rất phổ biến trên báo thật), và đoạn nhân đôi đó
    đi thẳng vào câu-có-số-liệu của brief;
  * **SSRF**: URL tới đây KHÔNG phải luôn tin được (Ông Chủ dán link vào chat,
    các vai quét link về từ web) mà bot chạy ngay cạnh 9router/dashboard/tunnel.

Test bằng HTML tổng hợp, không mạng: thay `fetch` bằng chuỗi có sẵn. Riêng cổng
host thì gọi THẬT (`scan_common.check_url`) vì đó mới là thứ cần giữ.

Chay:  venv/bin/python tests/test_article_extract.py
"""
import contextlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import article_extract as ae                                 # noqa: E402

HTML = """<html><head>
<title>Tiêu đề thẻ title</title>
<meta property="og:title" content="Tiêu đề OG">
<meta property="og:description" content="Mô tả OG">
<meta property="og:image" content="https://cdn.test/og.jpg">
<script type="application/ld+json">{"@type":"BlogPosting","datePublished":"2026-09-20"}</script>
</head><body>
<nav><p>Đoạn ngoài article, không được lấy</p></nav>
<article>
  <h2>Mục một</h2><h3>Mục con</h3>
  <p>Đoạn văn thứ nhất đủ dài để tính.</p>
  <p>ok</p>
  <p></p>
  <img src="/anh/that.jpg">
  <img src="https://cdn.test/avatar-nguoi.jpg">
  <img src="/_next/image?url=x">
  <img data-src="https://cdn.test/lazy.jpg">
</article></body></html>"""


@contextlib.contextmanager
def _fetch(html):
    cu = ae.fetch
    ae.fetch = lambda url: html
    try:
        yield
    finally:
        ae.fetch = cu


# ---------- bóc ----------

def test_extract_reads_meta_outline_paragraphs_images():
    with _fetch(HTML):
        d = ae.extract("https://bao.test/bai")
    assert d["title"] == "Tiêu đề OG", d["title"]
    assert d["description"] == "Mô tả OG"
    assert d["date_published"] == "2026-09-20"
    assert d["outline"] == [{"level": "h2", "text": "Mục một"},
                            {"level": "h3", "text": "Mục con"}], d["outline"]
    assert d["url"] == "https://bao.test/bai"


def test_extract_only_takes_paragraphs_inside_article():
    """`<nav>` và chân trang không phải bài — lọt vào là brief đầy rác."""
    with _fetch(HTML):
        d = ae.extract("https://bao.test/bai")
    assert "Đoạn ngoài article, không được lấy" not in d["paragraphs"], d["paragraphs"]
    assert "Đoạn văn thứ nhất đủ dài để tính." in d["paragraphs"]


def test_extract_drops_paragraphs_of_two_chars_or_less():
    with _fetch(HTML):
        d = ae.extract("https://bao.test/bai")
    assert "ok" not in d["paragraphs"] and "" not in d["paragraphs"], d["paragraphs"]


def test_extract_image_rules():
    """Ảnh: bỏ avatar/logo/favicon và `/_next/image`, đổi link tương đối sang tuyệt đối,
    og:image lên đầu, không trùng."""
    with _fetch(HTML):
        d = ae.extract("https://bao.test/bai")
    assert d["images"][0] == "https://cdn.test/og.jpg", d["images"]
    assert "https://bao.test/anh/that.jpg" in d["images"], d["images"]
    assert "https://cdn.test/lazy.jpg" in d["images"], d["images"]
    assert not any("avatar" in x or "_next/image" in x for x in d["images"]), d["images"]
    assert len(d["images"]) == len(set(d["images"])), d["images"]


def test_extract_word_count_counts_only_kept_paragraphs():
    with _fetch(HTML):
        d = ae.extract("https://bao.test/bai")
    assert d["word_count"] == sum(len(p.split()) for p in d["paragraphs"])


def test_extract_falls_back_to_title_tag_and_main_then_body():
    html = "<html><head><title>Chỉ có title</title></head><body><main>" \
           "<p>Một đoạn trong main.</p></main></body></html>"
    with _fetch(html):
        d = ae.extract("https://bao.test/x")
    assert d["title"] == "Chỉ có title" and d["paragraphs"] == ["Một đoạn trong main."], d


def test_extract_survives_broken_ld_json():
    """Một `<script type=ld+json>` hỏng không được làm chết cả lần bóc."""
    html = ('<html><head><title>T</title>'
            '<script type="application/ld+json">{khong phai json</script>'
            '<script type="application/ld+json">{"@graph":[{"@type":"BlogPosting",'
            '"datePublished":"2026-01-02"}]}</script></head>'
            '<body><article><p>Một đoạn văn đủ dài.</p></article></body></html>')
    with _fetch(html):
        d = ae.extract("https://bao.test/x")
    assert d["date_published"] == "2026-01-02", d["date_published"]


def test_extract_meta_by_name_not_only_property():
    html = ('<html><head><title>T</title><meta name="description" content="Mô tả name">'
            '</head><body><article><p>Một đoạn văn đủ dài.</p></article></body></html>')
    with _fetch(html):
        d = ae.extract("https://bao.test/x")
    assert d["description"] == "Mô tả name", d


# ---------- parser ----------

def test_parser_prefers_lxml_and_falls_back_loudly():
    """Thiếu lxml phải KÊU rồi dùng html.parser, không được chết câm (lớp lỗi C1)."""
    import builtins
    import importlib
    import io
    assert ae._parser() == "lxml", "máy này thiếu lxml — cài theo requirements.txt"

    cu_im, cu_bao = importlib.import_module, ae._DA_BAO_PARSER

    def no(ten, *a, **k):
        if ten == "lxml":
            raise ImportError("gia vo thieu lxml")
        return cu_im(ten, *a, **k)

    cu_err = sys.stderr
    sys.stderr = io.StringIO()
    importlib.import_module = no
    ae._DA_BAO_PARSER = False
    try:
        assert ae._parser() == "html.parser"
        ra = sys.stderr.getvalue()
        assert ae._parser() == "html.parser"          # lần hai: không kêu lại
        ra2 = sys.stderr.getvalue()
    finally:
        importlib.import_module = cu_im
        ae._DA_BAO_PARSER = cu_bao
        sys.stderr = cu_err
        del builtins
    assert "THIEU lxml" in ra and "nhan doi" in ra, ra
    assert ra2 == ra, "cảnh báo in lặp mỗi lần gọi"


# ---------- cổng SSRF ----------

def test_fetch_refuses_internal_host_before_any_request():
    """Cổng /bai chặn việc này từ lâu; đường này thì chưa, phát hiện 06/09/2026.
    Bản chép tay cũ chỉ so khớp CHUỖI nên `127.1` và `2130706433` đều lọt."""
    for xau in ("http://127.0.0.1:9130/x", "http://127.1/x", "http://2130706433/x",
                "http://localhost:20128/v1", "file:///etc/passwd", "http://[::1]/x"):
        try:
            ae.fetch(xau)
        except ValueError:
            continue
        except Exception as e:                               # noqa: BLE001
            raise AssertionError(f"{xau}: phải ValueError, ra {type(e).__name__}: {e}") from e
        raise AssertionError(f"{xau} lọt qua cổng host nội bộ")


# ---------- dòng lệnh ----------

def test_main_writes_file_and_prints_path():
    with tempfile.TemporaryDirectory() as t:
        out = Path(t) / "bai.json"
        cu = sys.argv
        sys.argv = ["article_extract.py", "https://bao.test/bai", "--out", str(out)]
        try:
            with _fetch(HTML):
                ae.main()
        finally:
            sys.argv = cu
        d = json.loads(out.read_text(encoding="utf-8"))
    assert d["title"] == "Tiêu đề OG", d


def test_main_prints_json_when_no_out():
    import io
    cu_out, cu_argv = sys.stdout, sys.argv
    sys.stdout = io.StringIO()
    sys.argv = ["article_extract.py", "https://bao.test/bai"]
    try:
        with _fetch(HTML):
            ae.main()
        ra = sys.stdout.getvalue()
    finally:
        sys.stdout, sys.argv = cu_out, cu_argv
    assert json.loads(ra)["title"] == "Tiêu đề OG", ra[:200]


def test_main_error_is_json_on_stdout_and_exit_1():
    """Người gọi là `material.extract` — nó đọc mã thoát, nên lỗi phải ra mã ≠ 0."""
    import io

    def no(url):
        raise RuntimeError("mang hong")
    cu_fetch, cu_out, cu_argv = ae.fetch, sys.stdout, sys.argv
    ae.fetch = no
    sys.stdout = io.StringIO()
    sys.argv = ["article_extract.py", "https://bao.test/bai"]
    ma = None
    try:
        ae.main()
    except SystemExit as e:
        ma = e.code
    finally:
        ra = sys.stdout.getvalue()
        ae.fetch, sys.stdout, sys.argv = cu_fetch, cu_out, cu_argv
    assert ma == 1, ma
    assert json.loads(ra)["error"] == "mang hong", ra


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
