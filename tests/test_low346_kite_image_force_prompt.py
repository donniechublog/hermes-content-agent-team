#!/usr/bin/env python3
"""LOW-346: Kite (LLM) phải BIẾT khoá `image_force` và luật "đổi hình khác trước".

Cổng nộp (LOW-339) chặn hình có khung riêng không full bề ngang và bảo ghi
`"image_force": true`. Khoá spec do vai LLM viết thì đổi CÙNG prompt (CLAUDE.md mục 5):
nếu prompt không nhắc thì Kite chỉ biết qua thông báo lỗi, và có thể tự ghi `image_fit`
(khoá do `kite_submit` gắn).

Chạy:  venv/bin/python tests/test_low346_kite_image_force_prompt.py
"""
import sys
from pathlib import Path
import tam  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SKILL = ROOT / "hermes" / "skills" / "carousel-edu" / "SKILL.md"
SOUL = ROOT / "hermes" / "profiles" / "shared" / "kite.SOUL.md"


def _text(p):
    return p.read_text(encoding="utf-8")


def test_skill_and_soul_teach_image_force():
    for p in (SKILL, SOUL):
        assert '"image_force": true' in _text(p), f"{p.name} không nhắc image_force"


def test_skill_says_replace_the_image_first_then_force():
    t = _text(SKILL)
    assert "Đổi hình khác" in t and "buộc phải dùng" in t
    assert t.index("Đổi hình khác") < t.index('"image_force": true'), "phải nói đổi hình TRƯỚC khi ép dùng"


def test_prompts_tell_kite_not_to_write_image_fit():
    """`image_fit` do kite_submit gắn; prompt chỉ được nhắc để CẤM tự ghi."""
    for p in (SKILL, SOUL):
        t = _text(p)
        if "image_fit" in t:
            assert "đừng tự ghi" in t, f"{p.name} nhắc image_fit mà không dặn đừng tự ghi"
    assert "image_fit" in _text(SKILL)


def test_gate_message_and_key_match_the_prompt():
    """Khoá trong prompt = khoá cổng nộp đọc = khoá trong thông báo lỗi."""
    import kite_submit as ks
    import render_edu as re_
    from PIL import Image
    boxed = Path(tam.temp_dir()) / "boxed.png"
    import random
    random.seed(11)
    im = Image.new("RGB", (1080, 1350), (0, 0, 0))
    px = im.load()
    for y in range(100, 1100):                              # tấm ảnh có khung riêng, 700px, nhiều màu
        for x in range(190, 890):
            px[x, y] = (random.randint(60, 255), random.randint(60, 255), random.randint(60, 255))
    im.save(boxed)
    m = {"images": [{"id": "A9", "original_path": str(boxed), "w": 1080, "h": 1350}]}
    slide = {"kind": "figure", "image": str(boxed), "image_fit": "contain"}
    loi = ks.check_subject_above_text({"slides": [slide]}, m, {1: 916.0})
    assert len(loi) == 1 and '"image_force": true' in loi[0], loi
    assert ks.check_subject_above_text({"slides": [{**slide, "image_force": True}]}, m, {1: 916.0}) == []
    assert re_.CONTAIN_FULL_WIDTH_MIN == 0.90 and "90%" in _text(SKILL)


def test_role_spec_passes_image_force_through():
    """role_spec.kite_spec (đọc khoá cũ) không được nuốt khoá mới."""
    import role_spec
    out = role_spec.kite_spec({"slides": [{"kind": "figure", "image": "A1", "image_force": True}]})
    assert out["slides"][0].get("image_force") is True, out


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
