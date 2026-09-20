#!/usr/bin/env python3
"""social_post.py — MỘT cửa duy nhất đọc post X/Instagram/Facebook (LOW-307).

Hai nơi cần cùng thứ này vì lý do khác nhau: `/bai` cần CHỮ để làm brief,
`image_prepare` cần HÌNH của chính post đó làm ảnh thật. Viết hai bản thì một
bản sửa, bản kia lệch — nhất là luật chuẩn hoá URL Facebook, thứ đã đắt giá mới
tìm ra.

Test dùng script giả thay `social_fetch.py` rồi trỏ `social_post.SCRIPT` vào đó,
nên đường tiến trình con chạy THẬT (mã thoát, stdout không phải JSON, timeout).
Cái duy nhất là giả: nội dung JSON.

Chay:  venv/bin/python tests/test_social_post.py
"""
import contextlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import social_post as sp                                     # noqa: E402

# Script đóng thế: in nguyên `ra.txt` cạnh nó rồi thoát với mã trong `ma.txt`.
FAKE = '''
import sys
from pathlib import Path
d = Path(__file__).parent
if "--download" in sys.argv:
    dich = Path(sys.argv[sys.argv.index("--download") + 1])
    dich.mkdir(parents=True, exist_ok=True)
    for ten in (d / "tai.txt").read_text(encoding="utf-8").split():
        ten, so = ten.rsplit(":", 1)
        (dich / ten).write_bytes(b"x" * int(so))
sys.stdout.write((d / "ra.txt").read_text(encoding="utf-8"))
sys.stderr.write((d / "err.txt").read_text(encoding="utf-8"))
sys.exit(int((d / "ma.txt").read_text(encoding="utf-8")))
'''


@contextlib.contextmanager
def _fake(ra="", ma=0, err="", tai=""):
    cu = sp.SCRIPT
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        (d / "social_fetch.py").write_text(FAKE, encoding="utf-8")
        (d / "ra.txt").write_text(ra, encoding="utf-8")
        (d / "ma.txt").write_text(str(ma), encoding="utf-8")
        (d / "err.txt").write_text(err, encoding="utf-8")
        (d / "tai.txt").write_text(tai, encoding="utf-8")
        sp.SCRIPT = d / "social_fetch.py"
        try:
            yield d
        finally:
            sp.SCRIPT = cu


# ---------- nhận diện URL ----------

def test_is_social_covers_every_host_of_the_table():
    for u in ("https://x.com/a/status/1", "https://www.twitter.com/a/status/1",
              "https://mobile.twitter.com/a", "https://instagram.com/p/abc/",
              "https://www.facebook.com/share/p/xyz/", "https://m.facebook.com/x",
              "https://fb.watch/abc/", "https://web.facebook.com/x"):
        assert sp.is_social(u), u


def test_is_social_rejects_other_sites_and_junk():
    for u in ("https://bao.test/bai", "https://xcom.test/a", "", None,
              "khong phai url", "https://notx.com/a"):
        assert not sp.is_social(u), u


# ---------- tiêu đề từ chữ ----------

def test_title_from_text_takes_first_sentence_of_first_nonempty_line():
    t = sp.title_from_text("\n\n  Dòng đầu là câu chốt. Câu hai không lấy.\nDòng hai.")
    assert t == "Dòng đầu là câu chốt.", t


def test_title_from_text_cuts_at_word_boundary_with_ellipsis():
    t = sp.title_from_text("mot hai ba bon nam sau bay tam chin muoi " * 4, gioi_han=30)
    assert len(t) <= 31 and t.endswith("…") and not t[:-1].endswith(" "), (len(t), t)


def test_title_from_text_empty_stays_empty():
    assert sp.title_from_text("") == "" and sp.title_from_text(None) == ""


def test_title_from_text_line_without_end_mark_is_used_whole():
    assert sp.title_from_text("Mot dong khong cham") == "Mot dong khong cham"


# ---------- đọc post ----------

def _json_post(**k):
    d = {"text": "Chúng tôi mở kho mô hình. Chi tiết bên dưới.",
         "author": {"name": "Jensen"}, "url": "https://x.com/a/status/1",
         "media": [{"type": "image", "url": "https://cdn.test/1.jpg", "index": 1}]}
    d.update(k)
    return d


def test_read_returns_tidy_shape():
    with _fake(ra=json.dumps(_json_post())):
        d = sp.read("https://x.com/a/status/1")
    assert d["title"] == "Chúng tôi mở kho mô hình." and d["author"] == "Jensen", d
    assert d["media"] == [{"type": "image", "url": "https://cdn.test/1.jpg",
                           "file_path": None}], d["media"]


def test_read_accepts_tweet_wrapper_and_string_author():
    with _fake(ra=json.dumps({"tweet": {"text": "Một câu.", "author": "handle",
                                        "media": [], "url": "https://x.com/z"}})):
        d = sp.read("https://x.com/a/status/1")
    assert d["author"] == "handle" and d["link"] == "https://x.com/z", d


def test_read_author_object_falls_back_to_handle():
    with _fake(ra=json.dumps(_json_post(author={"handle": "@ai"}))):
        assert sp.read("https://x.com/a")["author"] == "@ai"


def test_read_nonzero_exit_then_none_and_logs_stderr_tail():
    ghi = []
    with _fake(ra="", ma=2, err="khong toi duoc endpoint"):
        d = sp.read("https://x.com/a", in_log=ghi.append)
    assert d is None and any("rc=2" in x and "endpoint" in x for x in ghi), ghi


def test_read_non_json_stdout_then_none_and_says_so():
    ghi = []
    with _fake(ra="<html>Just a moment...</html>"):
        d = sp.read("https://x.com/a", in_log=ghi.append)
    assert d is None and any("khong phai JSON" in x for x in ghi), ghi


def test_read_empty_post_then_none():
    """Không chữ mà cũng không ảnh: gọi nó là lấy được thì brief rỗng đi tiếp."""
    ghi = []
    with _fake(ra=json.dumps({"text": "   ", "media": []})):
        d = sp.read("https://x.com/a", in_log=ghi.append)
    assert d is None and any("khong co chu lan anh" in x for x in ghi), ghi


def test_read_timeout_then_none_not_raise():
    ghi = []
    with _fake(ra=json.dumps(_json_post())):
        d = sp.read("https://x.com/a", cho=0, in_log=ghi.append)
    assert d is None and any("that bai" in x for x in ghi), ghi


def test_read_media_only_post_is_kept():
    with _fake(ra=json.dumps({"text": "", "media": [{"type": "video",
                                                     "url": "https://cdn.test/v.mp4"}]})):
        d = sp.read("https://x.com/a")
    assert d and d["title"] == "" and d["media"][0]["type"] == "video", d


def test_read_media_without_url_is_dropped():
    with _fake(ra=json.dumps(_json_post(media=[{"type": "image"},
                                               {"type": "image", "url": "https://cdn.test/2.jpg"}]))):
        d = sp.read("https://x.com/a")
    assert [m["url"] for m in d["media"]] == ["https://cdn.test/2.jpg"], d["media"]


# ---------- tải media ----------

def test_download_attaches_file_path_by_carousel_order():
    post = _json_post(media=[{"type": "image", "url": "https://cdn.test/1.jpg", "index": 1},
                             {"type": "video", "url": "https://cdn.test/2.mp4", "index": 2}])
    with tempfile.TemporaryDirectory() as t:
        with _fake(ra=json.dumps(post), tai="01.jpg:10 02.mp4:10"):
            d = sp.read("https://x.com/a", tai_ve=Path(t))
    assert [Path(m["file_path"]).name for m in d["media"]] == ["01.jpg", "02.mp4"], d["media"]


def test_zero_byte_file_counts_as_not_downloaded():
    """0 byte = CDN 302 hụt hoặc link hết hạn — coi là có ảnh thì slide ra tấm trắng."""
    with tempfile.TemporaryDirectory() as t:
        with _fake(ra=json.dumps(_json_post()), tai="01.jpg:0"):
            d = sp.read("https://x.com/a", tai_ve=Path(t))
    assert d["media"][0]["file_path"] is None, d["media"]


def test_index_missing_then_numbered_by_position():
    post = _json_post(media=[{"type": "image", "url": "https://cdn.test/1.jpg"},
                             {"type": "image", "url": "https://cdn.test/2.jpg"}])
    with tempfile.TemporaryDirectory() as t:
        with _fake(ra=json.dumps(post), tai="01.jpg:9 02.jpg:9"):
            d = sp.read("https://x.com/a", tai_ve=Path(t))
    assert [Path(m["file_path"]).name for m in d["media"]] == ["01.jpg", "02.jpg"], d["media"]


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
