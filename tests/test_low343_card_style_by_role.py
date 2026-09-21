#!/usr/bin/env python3
"""LOW-343 (21/09/2026) — kieu the khoa theo VAI: quote = Dre, khung chu nhat (full_bleed) = Ethan.

Ong Chu, duyet hai the Qwen-Image-2.1: *"phong cach o tren la cua Dre, phong cach duoi la cua
Ethan. do la ly do vi sao chung ta can tach mot so phan trong engine cua tung Designer"*.
Cong chong troi: kieu gan voi vai trong `role.py`, va moi cho vai doc (brief, task body, SOUL,
skill) khong con goi y quote cho Ethan.

Chay:  python tests/test_low343_card_style_by_role.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import role  # noqa: E402
import role_spec  # noqa: E402


def _read(rel):
    return (ROOT / rel).read_text(encoding="utf-8")


def test_style_lives_on_the_role():
    assert role.card_styles_for("ethan") == ("full_bleed",)
    assert role.card_styles_for("designer") == ("full_bleed",)          # slug cu cua Ethan
    for v in role.ROLE.values():
        if v.renderer == "card":
            assert v.card_styles and set(v.card_styles) <= set(role_spec.CARD_STYLES), v.slug
        else:
            assert not v.card_styles, v.slug                                # Dre/Kite khong dung card.py


def test_ethan_brief_template_is_full_bleed():
    src = _read("ethan_prepare.py")
    assert '"card_style": "full_bleed"' in src
    assert '"card_style": "quote"' not in src and "kiểu mặc định: quote" not in src


def test_ethan_prompts_do_not_offer_quote():
    body = _read("task_bodies.py")
    ethan = body[body.index("NHIEM VU: dung MOT the anh"):body.index("ethan_submit.py {draft_id}")]
    assert "quote/HOOK" not in ethan and "hook, tagline, attrib" not in ethan
    soul = _read("hermes/profiles/shared/ethan.SOUL.md")
    assert "Mặc định thẻ HOOK" not in soul and "phong cách" in soul and "Dre" in soul
    skill = _read("hermes/skills/hero-image/SKILL.md")
    assert "mặc định kiểu quote" not in skill and "## Kiểu quote" not in skill
    assert "phong cách của Dre" in skill


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
