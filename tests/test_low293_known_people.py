#!/usr/bin/env python3
"""LOW-293 (20/09/2026) — ảnh ghép chân dung nhiều CEO không còn bị loại là "mặt người
không rõ ai", nếu tin xác nhận được tên.

Tin "Đơn kiện cáo buộc Anthropic, OpenAI, SpaceXAI và Google thông đồng làm chậm AI":
A1 (independent.co.uk) và A33 (AP) là ảnh ghép đúng các CEO bị nêu, mô tả vision ghi rõ
"Sam Altman (OpenAI), Elon Musk…", nhưng cổng chỉ đọc printed_name/alt/tên tệp nên loại cả hai.

Tên trong mô tả chỉ được tính khi: giống tên người, VÀ khớp người của hãng (Wikidata)
hoặc nằm liền nhau trong chữ bài, VÀ không chứa chữ nào là tên hãng của tin, VÀ Wikidata
nói đó là một con người. Đo 20/09 trên 4.240 ảnh máy chủ: thiếu bước cuối thì "Claude
Cowork", "Maxton Hall", "Bloomberg Tech", "Model Context Protocol" lọt vào.

Chạy:  venv/bin/python tests/test_low293_known_people.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import role  # noqa: E402
import schema  # noqa: E402
from prepare.manifest import label_people  # noqa: E402

BAI = ("Đơn kiện cáo buộc Anthropic, OpenAI, SpaceXAI và Google thông đồng làm chậm AI. "
       "Sam Altman và Elon Musk bị nêu tên. Dario Amodei nói về vụ việc. "
       "Claude Cowork là sản phẩm, Maxton Hall là phim.")
NGUOI = {"Sam Altman", "Elon Musk", "Dario Amodei", "Satya Nadella"}


def _person(ten):
    return ten in NGUOI


def _anh(ma, faces, mo_ta, **k):
    a = {"id": ma, "faces": faces, "description": mo_ta, "notes": [], "uses": ["body"],
         "relevant": True, "kind": "photo", "cluttered": False, "alt": "", "w": 1600, "h": 1200,
         "ratio": 1.33, "landscape": False}
    a.update(k)
    return a


def _bo():
    return [
        _anh("A1", 4, "Ảnh ghép 4 chân dung CEO các công ty AI: Sam Altman (OpenAI), Elon Musk.",
             notes=["CÓ 4 MẶT NGƯỜI mà KHÔNG RÕ AI (ảnh không in tên, alt/caption không nêu tên) → KHÔNG DÙNG."]),
        _anh("A3", 1, "Ảnh chân dung một người đàn ông đeo kính gọng đen, mặc áo thun nâu.",
             notes=["CÓ 1 MẶT NGƯỜI mà KHÔNG RÕ AI → KHÔNG DÙNG."]),
        _anh("A15", 1, "Ảnh chân dung Dario Amodei (CEO Anthropic).",
             brand_match={"company": "Anthropic", "person": "Dario Amodei"}),
        _anh("A22", 1, "Ảnh minh họa app Claude Cowork bên trái và cửa sổ trình duyệt."),
        _anh("A6", 2, "Poster phim \"Maxton Hall\" mùa cuối của Prime Original."),
        _anh("A9", 1, "Lãnh đạo Hyundai Steel trả lời phỏng vấn.",
             brand_match={"company": "Hyundai Steel"}),
    ]


def test_collage_of_named_ceos_is_unlocked():
    bo = _bo()
    label_people(bo, BAI, is_person=_person)
    a1 = bo[0]
    assert a1["people"] == ["Sam Altman", "Elon Musk"], a1["people"]
    assert role.face_no_clear_ai(a1) is False
    assert not any("KHÔNG RÕ AI" in g for g in a1["notes"]), a1["notes"]
    assert any("tin xác nhận tên" in g for g in a1["notes"]), a1["notes"]


def test_unnamed_person_still_blocked():
    bo = _bo()
    label_people(bo, BAI, is_person=_person)
    assert bo[1]["people"] == [] and role.face_no_clear_ai(bo[1]) is True


def test_product_and_film_names_not_people():
    bo = _bo()
    label_people(bo, BAI, is_person=_person)
    assert bo[3]["people"] == [] and role.face_no_clear_ai(bo[3]) is True, bo[3]["people"]
    assert bo[4]["people"] == [] and role.face_no_clear_ai(bo[4]) is True, bo[4]["people"]


def test_company_name_in_description_not_a_person():
    bo = _bo()
    label_people(bo, BAI, is_person=lambda t: True)     # ke ca Wikidata noi "co"
    assert bo[5]["people"] == [] and role.face_no_clear_ai(bo[5]) is True, bo[5]["people"]


def test_name_not_in_story_not_accepted():
    bo = [_anh("A9", 1, "Ảnh chân dung Tim Cook tại sự kiện.")]
    label_people(bo, BAI, is_person=lambda t: True)     # Tim Cook la nguoi that, nhung bai khong nhac
    assert bo[0]["people"] == [] and role.face_no_clear_ai(bo[0]) is True


def test_wikidata_unreachable_blocks_as_before():
    bo = _bo()
    label_people(bo, BAI, is_person=lambda t: None)     # khong hoi duoc mang
    assert bo[0]["people"] == [] and role.face_no_clear_ai(bo[0]) is True


def test_counter_sees_the_unlocked_image():
    bo = _bo()
    truoc = schema.count_image_use_ok(bo, "dre")
    label_people(bo, BAI, is_person=_person)
    assert schema.count_image_use_ok(bo, "dre") > truoc


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
