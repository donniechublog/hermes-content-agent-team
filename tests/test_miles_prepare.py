#!/usr/bin/env python3
"""miles_prepare.py + jika_prepare/jika_submit — brief cho vai viết (LOW-307).

`write_brief` là chỗ duy nhất nói cho writer biết phải viết gì. Ba thứ hay sai và
không ai thấy:

  * **giọng theo BRAND, không theo tên vai** — dcgr hỏi "rồi sao nữa", blog hỏi
    "làm thế nào". Lẫn hai cái là bài đúng sự thật mà sai người đọc;
  * **bàn giao của vai ảnh** phải có mặt, không thì caption lặp lại hook trên ảnh;
  * **lệnh nộp phải mang tên persona của BÀI** (`jika_submit` cho bài của Jika).
    Sai ở đây thì vai chạy nhầm script, `author` trên bảng đen ghi nhầm người.

Và một hợp đồng của cặp `jika_*`: chúng là MỘT DÒNG trỏ vào Miles, không phải
bản sao. Test khoá đúng điều đó — bản sao thì sửa một bên, bên kia lệch.

Chay:  venv/bin/python tests/test_miles_prepare.py
"""
import contextlib
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import caption_check                                         # noqa: E402
import image_prepare as cb                                   # noqa: E402
import miles_prepare as mb                                   # noqa: E402
import state_paths                                           # noqa: E402
import submit_common as nc                                   # noqa: E402


def _m(**k):
    m = {"draft_id": "tin-thu", "title": "Tin thử", "link": "https://vi.du/bai",
         "material": {}, "summary": ""}
    m.update(k)
    return m


def _meta(**k):
    d = {"category": "Model", "via": "@ai"}
    d.update(k)
    return d


# ---------- giọng theo brand ----------

def test_voice_follows_brand_not_role_name():
    with tempfile.TemporaryDirectory() as t:
        blog = mb.write_brief(_m(), _meta(brand="donniechublog"), Path(t), "jika")
        dcgr = mb.write_brief(_m(), _meta(brand="dcgr"), Path(t), "miles")
    assert "làm thế nào" in blog and "rồi sao nữa" not in blog, blog[:400]
    assert "rồi sao nữa" in dcgr and "làm thế nào" not in dcgr, dcgr[:400]


def test_unknown_brand_falls_back_to_blog_voice():
    with tempfile.TemporaryDirectory() as t:
        b = mb.write_brief(_m(), _meta(brand="brand-la"), Path(t), "miles")
    assert "làm thế nào" in b, b[:400]


# ---------- điểm chấm, tư liệu, bàn giao ----------

def test_score_reason_is_quoted_for_the_meaning_sentence():
    """Trước đây bóc bằng regex trên văn bản task: đổi một chữ trong mẫu là chết câm."""
    with tempfile.TemporaryDirectory() as t:
        b = mb.write_brief(_m(), _meta(score=88, score_reason="mở trọng số"), Path(t), "miles")
    assert "Điểm chấm: 88/100" in b and "mở trọng số" in b, b[:600]


def test_no_score_reason_then_no_score_line():
    with tempfile.TemporaryDirectory() as t:
        b = mb.write_brief(_m(), _meta(score=88), Path(t), "miles")
    assert "Điểm chấm" not in b, b[:600]


def test_material_missing_says_so_instead_of_staying_quiet():
    """Bài học 06/09: brief thiếu dòng này thì vai không biết mình đang viết chay."""
    with tempfile.TemporaryDirectory() as t:
        b = mb.write_brief(_m(), _meta(), Path(t), "miles")
    assert "KHÔNG bịa số" in b, b


def test_number_sentences_reach_the_brief():
    tl = {"number_sentences": ["Mô hình đạt 71.2% trên SWE-bench."]}
    with tempfile.TemporaryDirectory() as t:
        b = mb.write_brief(_m(material=tl), _meta(), Path(t), "miles")
    assert "71.2%" in b, b


def test_handoff_from_image_role_is_included():
    """Không có bàn giao thì caption lặp lại hook đã in trên ảnh."""
    with tempfile.TemporaryDirectory() as t:
        wd = Path(t)
        state_paths.handoff_file(wd, "tin-thu").write_text("Bìa dùng ảnh A1, hook: X",
                                                           encoding="utf-8")
        b = mb.write_brief(_m(), _meta(), wd, "miles")
    assert "Ảnh đã duyệt" in b and "hook: X" in b, b
    assert "không lặp lại hook" in b, b


def test_title_en_is_shown_when_present():
    with tempfile.TemporaryDirectory() as t:
        b = mb.write_brief(_m(title_en="Original headline"), _meta(), Path(t), "miles")
    assert "Tiêu đề bài gốc: Original headline" in b, b


# ---------- luật caption in sẵn ----------

def test_caption_rules_come_from_caption_check_not_hardcoded():
    """Luật in trong brief phải lấy từ chính cổng chặn — hai bản là hai luật."""
    with tempfile.TemporaryDirectory() as t:
        b = mb.write_brief(_m(), _meta(), Path(t), "miles")
    assert str(caption_check.CEILING_BACKGROUND_LAYER) in b, b
    for cum in caption_check.STAR_EMPTY[:3]:
        assert cum in b, cum


def test_submit_command_uses_the_article_persona():
    with tempfile.TemporaryDirectory() as t:
        b = mb.write_brief(_m(), _meta(), Path(t), "jika")
        assert "jika_submit.py tin-thu" in b and "miles_submit.py" not in b, b
        b2 = mb.write_brief(_m(), _meta(), Path(t), "miles")
        assert "miles_submit.py tin-thu" in b2, b2


def test_brief_tells_role_not_to_resubmit_after_done():
    """LOW-296: nộp lại là đổi thẻ trong topic của Ông Chủ."""
    with tempfile.TemporaryDirectory() as t:
        b = mb.write_brief(_m(), _meta(), Path(t), "miles")
    assert "KHÔNG chạy lại lệnh nộp" in b, b
    assert "[nhac]" in b and "KHÔNG phải lỗi" in b, b


# ---------- dòng lệnh ----------

@contextlib.contextmanager
def _engine(m, wd, meta, persona):
    cu_run, cu_ten, cu_cho = cb.run, nc.writer_persona_name, nc.writer_for_article
    cb.run = lambda *a, **k: (m, wd, meta)
    nc.writer_for_article = lambda draft_id, brand: persona
    nc.writer_persona_name = lambda vai: persona
    try:
        yield
    finally:
        cb.run, nc.writer_persona_name, nc.writer_for_article = cu_run, cu_ten, cu_cho


def test_main_writes_brief_named_after_persona():
    with tempfile.TemporaryDirectory() as t:
        wd = Path(t)
        cu = sys.argv
        sys.argv = ["miles_prepare.py", "tin-thu", "--im"]
        try:
            with _engine(_m(), wd, _meta(brand="dcgr"), "jika"):
                assert mb.main() == 0
        finally:
            sys.argv = cu
        assert (wd / "brief_jika.md").exists(), sorted(p.name for p in wd.iterdir())
        b = (wd / "brief_jika.md").read_text(encoding="utf-8")
    assert b.startswith("# JIKA — TƯ LIỆU ĐÃ SẴN: Tin thử"), b[:120]


# ---------- cặp jika_* là một dòng, không phải bản sao ----------

def test_jika_scripts_are_one_line_into_miles_engine():
    """Sửa engine một bên mà bên kia là bản chép thì hai vai lệch luật lúc nào không hay."""
    import jika_prepare
    import jika_submit
    import miles_submit
    assert jika_prepare.main is mb.main, "jika_prepare đã tách khỏi miles_prepare"
    assert jika_submit.main is miles_submit.main, "jika_submit đã tách khỏi miles_submit"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
