#!/usr/bin/env python3
"""cape_prepare.py + cape_submit.py — teaser mời đọc bài (LOW-307, cả hai 0% độ phủ).

Cape là vai duy nhất nhận đầu vào TRỰC TIẾP từ Ông Chủ (một URL dán vào chat),
nên nó là chỗ dễ nhất để một URL lạ đi vào dây chuyền. Và teaser đi thẳng lên
topic: sai thì Ông Chủ đọc ra, không có cổng nào phía sau.

Ba nhóm test này giữ:
  1. `workdir`/`slug` — cùng một URL phải ra cùng một thư mục, khác URL thì khác
     thư mục (trộn là teaser của bài này dán vào bài kia);
  2. brief phải in ĐỦ luật của `teaser_assemble` (độ dài, giọng cấm) — lấy từ
     chính module đó chứ không gõ lại;
  3. cổng của `cape_submit`: thiếu chuẩn bị, spec hỏng, tiếng Việt mất dấu, và
     `--khong-gui` thì KHÔNG được đụng tới Telegram.

Chay:  venv/bin/python tests/test_cape.py
"""
import contextlib
import io
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import cape_prepare as jb                                    # noqa: E402
import cape_submit as ns                                     # noqa: E402

URL = "https://www.donniechu.com/posts/bai-thu"

BAI = {"title": "Bài thử", "description": "Mô tả bài", "url": URL,
       "outline": [{"level": "h2", "text": "Mục một"}, {"level": "h3", "text": "Mục con"}],
       "paragraphs": ["Đoạn một của bài.", "Đoạn hai của bài."],
       "images": ["https://cdn.test/1.jpg", "https://cdn.test/2.jpg"]}

FAKE_EXTRACT = '''
import json, sys
from pathlib import Path
d = Path(__file__).parent
ma = int((d / "ma.txt").read_text(encoding="utf-8"))
if ma:
    print("khong boc duoc", file=sys.stderr)
    sys.exit(ma)
out = sys.argv[sys.argv.index("--out") + 1]
Path(out).write_text((d / "bai.json").read_text(encoding="utf-8"), encoding="utf-8")
print(out)
'''


@contextlib.contextmanager
def _sandbox(ma=0, bai=None):
    """state riêng + article_extract.py giả (trỏ ROOT của cape_prepare vào tạm)."""
    cu_root, cu_state = jb.ROOT, os.environ.get("CT_STATE_DIR")
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        (d / "article_extract.py").write_text(FAKE_EXTRACT, encoding="utf-8")
        (d / "bai.json").write_text(json.dumps(bai if bai is not None else BAI,
                                               ensure_ascii=False), encoding="utf-8")
        (d / "ma.txt").write_text(str(ma), encoding="utf-8")
        os.environ["CT_STATE_DIR"] = str(d / "state")
        jb.ROOT = d
        try:
            yield d
        finally:
            jb.ROOT = cu_root
            if cu_state is None:
                os.environ.pop("CT_STATE_DIR", None)
            else:
                os.environ["CT_STATE_DIR"] = cu_state


# ---------- slug & thư mục làm việc ----------

def test_slug_is_stable_and_separates_different_urls():
    assert jb.slug(URL) == jb.slug(URL + "/") == jb.slug(" " + URL + " ")
    assert jb.slug(URL) != jb.slug("https://www.donniechu.com/posts/bai-khac")


def test_slug_never_empty_and_is_bounded():
    assert jb.slug("https://") == "bai"
    assert len(jb.slug("https://x.test/" + "a" * 500)) <= 60


def test_workdir_is_created_once_per_url():
    with _sandbox():
        a, b = jb.workdir(URL), jb.workdir(URL)
        assert a == b and a.is_dir(), (a, b)
        assert a != jb.workdir("https://www.donniechu.com/posts/khac")


# ---------- bóc bài ----------

def test_extract_caches_and_lam_moi_refetches():
    with _sandbox() as d:
        wd = jb.workdir(URL)
        assert jb.extract(URL, wd, False)["title"] == "Bài thử"
        # đổi bảng: bản cache phải thắng, `--lam-moi` mới đọc bản mới
        (d / "bai.json").write_text(json.dumps({**BAI, "title": "Bản mới"},
                                               ensure_ascii=False), encoding="utf-8")
        assert jb.extract(URL, wd, False)["title"] == "Bài thử"
        assert jb.extract(URL, wd, True)["title"] == "Bản mới"


def test_extract_failure_exits_with_reason():
    with _sandbox(ma=4):
        wd = jb.workdir(URL)
        try:
            jb.extract(URL, wd, False)
        except SystemExit as e:
            assert "[LOI] không bóc được bài" in str(e.code), e.code
            return
        raise AssertionError("bóc hỏng mà vẫn đi tiếp")


# ---------- brief ----------

def test_brief_carries_outline_paragraphs_and_the_real_rules():
    import teaser_assemble as ta
    with _sandbox():
        wd = jb.workdir(URL)
        b = jb.write_brief(URL, BAI, wd)
    assert "Mục một" in b and "Đoạn một của bài." in b, b
    assert "Ảnh trong bài: 2" in b and "Mô tả: Mô tả bài" in b, b
    assert f"{ta.LONG_THIN_LATE[0]}–{ta.LONG_THIN_LATE[1]} từ" in b, b
    assert ta.PHRASE_WALL_TECHNIQUE[0] in b, b
    assert "cape_submit.py" in b and "KHÔNG chạy article_extract" in b, b


def test_brief_cuts_very_long_article_and_says_so():
    dai = {**BAI, "paragraphs": ["x" * (jb.TEXT_MAX + 10), "đoạn sau bị cắt"]}
    with _sandbox():
        b = jb.write_brief(URL, dai, jb.workdir(URL))
    assert "(cắt bớt)" in b and "đoạn sau bị cắt" not in b, b


def test_prepare_main_writes_brief_and_url():
    with _sandbox():
        cu = sys.argv
        sys.argv = ["cape_prepare.py", URL, "--im"]
        try:
            assert jb.main() == 0
        finally:
            sys.argv = cu
        wd = jb.workdir(URL)
        assert (wd / "brief.md").exists(), sorted(x.name for x in wd.iterdir())
        assert (wd / "url.txt").read_text(encoding="utf-8") == URL


# ---------- nộp ----------

@contextlib.contextmanager
def _no_send():
    """Chặn mọi đường ra Telegram; trả về danh sách lệnh đã định gọi."""
    goi = []

    class _KetQua:
        returncode = 0
        stdout = stderr = ""

    cu = ns.subprocess.run
    ns.subprocess.run = lambda cmd, **k: (goi.append(cmd) or _KetQua())
    try:
        yield goi
    finally:
        ns.subprocess.run = cu


# ~560 từ: trên sàn cứng 200 và trong dải mong muốn 500–800 của teaser_assemble,
# đủ dày để qua cổng "phủ hết các mục trong outline".
_CAU = ("Chi phí huấn luyện rơi xuống mức một nhóm ba người cũng gánh nổi, nên mục một "
        "của câu chuyện không còn là tiền nữa mà là ai dám thử trước. Mô hình mở chạy "
        "thẳng trên máy để bàn, khỏi thuê cụm máy chủ theo giờ, và mục con nằm ở chỗ "
        "đó: thời gian chờ ngắn lại thì số lần thử nhiều lên. ")


def _doan_du(so_tu=560):
    doan, dem = [], 0
    while dem < so_tu:
        doan.append((_CAU * 3).strip())
        dem += len((_CAU * 3).split())
    return doan


def _spec(wd, **k):
    d = {"title": "Bài thử đọc đi",
         "paragraphs": ["Đoạn mở đầu nói thẳng vào chuyện.", "Đoạn hai tiếp tục."]}
    d.update(k)
    (wd / "spec.json").write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")


def _nop(*args):
    cu = sys.argv
    sys.argv = ["cape_submit.py", URL, *args]
    try:
        return ns.main()
    except SystemExit as e:
        return e.code
    finally:
        sys.argv = cu


def test_submit_without_prepare_says_run_prepare_first():
    with _sandbox():
        jb.workdir(URL)
        ma = _nop()
    assert isinstance(ma, str) and "cape_prepare.py" in ma, ma


def test_submit_without_spec_says_write_spec():
    with _sandbox():
        wd = jb.workdir(URL)
        jb.extract(URL, wd, False)
        ma = _nop()
    assert isinstance(ma, str) and "Chưa có spec" in ma, ma


def test_submit_broken_spec_json_is_named_not_swallowed():
    with _sandbox():
        wd = jb.workdir(URL)
        jb.extract(URL, wd, False)
        (wd / "spec.json").write_text("{khong phai json", encoding="utf-8")
        ma = _nop()
    assert isinstance(ma, str) and "spec.json không phải JSON" in ma, ma


def test_submit_missing_title_is_an_error_line_not_a_crash():
    with _sandbox():
        wd = jb.workdir(URL)
        jb.extract(URL, wd, False)
        _spec(wd, title="   ")
        assert _nop() == 1


def test_submit_vietnamese_without_marks_is_refused():
    """Teaser đi thẳng lên topic — mất dấu ở đây là Ông Chủ đọc thấy.

    Đoạn văn phải ĐỦ DÀI, không thì cổng độ dài chặn trước và test xanh giả:
    đột biến `find_face_mark -> None` vẫn lọt (đã đo, LOW-307)."""
    with _sandbox():
        wd = jb.workdir(URL)
        jb.extract(URL, wd, False)
        _spec(wd, paragraphs=_doan_du() + ["Doan nay khong co dau tieng Viet nao ca."])
        cu = sys.stdout
        sys.stdout = io.StringIO()
        try:
            ma = _nop()
            ra = sys.stdout.getvalue()
        finally:
            sys.stdout = cu
    assert ma == 1, ma
    assert "tiếng Việt mất dấu" in ra, ra


def test_submit_khong_gui_writes_teaser_but_touches_no_network():
    with _sandbox():
        wd = jb.workdir(URL)
        jb.extract(URL, wd, False)
        _spec(wd, paragraphs=_doan_du())
        with _no_send() as goi:
            ma = _nop("--khong-gui")
        assert ma == 0, ma
        assert goi == [], goi
        assert (wd / "teaser.txt").read_text(encoding="utf-8").strip(), "teaser rỗng"


def test_submit_sends_to_the_cape_topic():
    with _sandbox():
        wd = jb.workdir(URL)
        jb.extract(URL, wd, False)
        _spec(wd, paragraphs=_doan_du())
        with _no_send() as goi:
            ma = _nop()
        assert ma == 0, ma
        assert len(goi) == 1 and "--thread-name" in goi[0], goi
        assert goi[0][goi[0].index("--thread-name") + 1] == "cape", goi[0]


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
