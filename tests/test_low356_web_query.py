#!/usr/bin/env python3
"""LOW-356: vong tim rong khong hoi Yandex bang ten rieng CHUA CO tren web.

Do tren may chu 22/09/2026: ten phuong phap paper vua dat ("IntBMoE", "RRSI") hoi
Yandex ra 16/16 anh rac (bieu tinh BLM; hoa chat, dua xe) — Yandex khong bao gio tra
rong. Bao chi cung vong tra 0 bai cho ca hai ten; hoi bang CA tieu de thi ra so do
MoE / bai ve agent harness. Commons KHONG phai tin hieu: 'RRSI' ra "Tree Rrsi".

Chay:  venv/bin/python tests/test_low356_web_query.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from prepare import fallback_rounds as fr                        # noqa: E402

TITLE = ("IntBMoE: Integrating Block-Level Conditioning into Expert Composition "
         "for Full-Participation Mixture-of-Experts")


def test_unknown_name_uses_full_title():
    assert fr.web_query("IntBMoE", TITLE, press_count=0) == TITLE


def test_known_name_keeps_name():
    # TSMC: bao chi co bai -> van hoi Yandex bang ten nhu cu (TIM NHU NGUOI, 12/09).
    assert fr.web_query("TSMC", "TSMC posts record profit", press_count=11) == "TSMC"


def test_no_name_uses_title():
    assert fr.web_query("", TITLE, press_count=0) == TITLE


def test_round_asks_press_before_yandex():
    src = (ROOT / "prepare" / "fallback_rounds.py").read_text(encoding="utf-8")
    body = src[src.index("def _round_widen_search"):]
    body = body[:body.index("\ndef ")]
    i_press = body.index("press_entity_images.press_entity_images(")
    i_query = body.index("web_query(")
    i_yandex = body.index("find_image_web.find_image_web(q_web")
    assert i_press < i_query < i_yandex, \
        "phai biet bao chi ra bao nhieu bai truoc khi chon truy van Yandex"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
