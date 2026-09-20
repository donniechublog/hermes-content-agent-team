#!/usr/bin/env python3
"""LOW-219 (20/09/2026) — chân dung người mà TIN nhắc tới không còn bị vision chấm
"không liên quan".

Con mắt không nhận diện mặt người: một tấm chân dung lãnh đạo của chính hãng trong tin
hiện ra với nó là "một người đàn ông đeo kính" → LIEN_QUAN: khong. Đo trên máy chủ
20/09/2026: 2.721/4.309 ảnh bị chấm không liên quan, trong đó 291 chân dung; riêng tin
"Đơn kiện cáo buộc Anthropic, OpenAI, SpaceXAI và Google" mất 10 tấm Musk/Amodei/
Hassabis/Pichai thật. Luật mới cứu 91 tấm thành ảnh DÙNG ĐƯỢC trên 225 manifest.

Các bẫy đã đo được và bị chặn ở đây: chú thích nêu người KHÁC ("Ed Davey takes aim at
… Elon Musk"), tên tệp Commons trùng chữ ("Le Mistral.jpg" là tàu chiến), tên hãng trong
chú thích mà không có người ("The Lambda variant" là bệnh nhân COVID), vision nói thẳng
"không phải Jeff Dean", và Wikidata không xác nhận là người ("Bloomberg Tech").

Chạy:  venv/bin/python tests/test_low219_named_subject.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from prepare.vision import relevant_by_named_subject  # noqa: E402

TIN = "Đơn kiện cáo buộc Anthropic, OpenAI, SpaceXAI và Google thông đồng làm chậm AI"
THAN = ("Đơn kiện nêu tên Elon Musk của xAI, Dario Amodei của Anthropic và Demis Hassabis "
        "của Google DeepMind. Sam Altman cũng bị nhắc tới.")
NGUOI = {"Elon Musk", "Dario Amodei", "Demis Hassabis", "Sam Altman", "Ed Davey", "Jeff Dean"}


def _person(ten):
    return ten in NGUOI


def _anh(faces=1, **k):
    a = {"id": "A1", "faces": faces, "relevant": False, "description": "", "alt": "",
         "url": "", "source": "press_entity", "notes": []}
    a.update(k)
    return a


def _cuu(a):
    return relevant_by_named_subject(a, TIN, story=THAN, is_person=_person)


def test_portrait_named_in_description_is_rescued():
    a = _anh(description="Ảnh chân dung Elon Musk mặc vest đen, hai tay đan vào nhau.")
    assert _cuu(a) == "named_person_in_story"


def test_caption_naming_person_of_the_story_is_rescued():
    a = _anh(description="Ảnh chân dung một người đàn ông đeo kính gọng xanh.",
             alt="Google DeepMind enters a new era as co-founder Demis Hassabis shifts AI role")
    assert _cuu(a) == "named_person_in_story"


def test_caption_with_person_and_brand_is_rescued():
    """Không đọc ra tên người trong bài, nhưng chú thích thật nêu cả người lẫn hãng."""
    a = _anh(description="Ảnh một người đàn ông đeo kính đang phát biểu, nền xanh đậm.",
             alt="Inside Anthropic's safety bet, with policy lead Jack Clark")
    assert _cuu(a) == "brand_person_in_caption"


def test_brand_match_person_is_rescued():
    a = _anh(description="Ảnh hai người đàn ông mặc vest đứng cạnh nhau.",
             brand_match={"company": "Google", "person": "Sundar Pichai"})
    assert _cuu(a) == "brand_person_photo"


def test_caption_about_someone_else_not_rescued():
    """Bẫy thật: ảnh là Ed Davey, chú thích chỉ NHẮC tới Elon Musk."""
    a = _anh(description="Ảnh một người đàn ông mặc áo sơ mi phát biểu trên sân khấu.",
             alt="Ed Davey takes aim at Reform and Elon Musk as Lib Dem conference begins")
    assert _cuu(a) == ""


def test_brand_in_caption_without_person_not_rescued():
    a = _anh(description="Ảnh cụ bà nằm giường bệnh, đeo mặt nạ oxy.",
             alt="The Anthropic variant: is it more infectious? A virologist explains")
    assert _cuu(a) == ""


def test_commons_filename_is_not_brand_evidence():
    """"Commons: Le Mistral.jpg" là tàu chiến — tên tệp không phải chú thích."""
    a = _anh(description="Ảnh tàu chiến neo tại cảng, phía trước có người.",
             alt="Commons: Le Anthropic Sam Altman.jpg", source="commons")
    assert _cuu(a) == "" or _cuu(a) == "named_person_in_story"  # tên người trong tệp vẫn đọc được
    b = _anh(description="Ảnh tàu chiến neo tại cảng, phía trước có người đi lại.",
             alt="Commons: Le Anthropic warship.jpg", source="commons")
    assert _cuu(b) == ""


def test_description_saying_not_that_person_not_rescued():
    a = _anh(description="Ảnh chân dung người đàn ông đeo kính xanh, không phải Jeff Dean.")
    assert _cuu(a) == ""


def test_wikidata_not_a_person_not_rescued():
    a = _anh(description="Người đàn ông đứng cạnh logo Bloomberg Tech.",
             alt="Bloomberg Tech summit day two")
    assert relevant_by_named_subject(a, TIN, story=THAN, is_person=lambda t: False) == ""


def test_image_without_face_not_rescued():
    """Ảnh không có mặt người đi đường khác (toà nhà Uber trong tin về hãng AI)."""
    a = _anh(faces=0, description="Ảnh chụp toà nhà văn phòng kính Uber tại góc phố.",
             alt="REPORT: OpenAI Zeroing In On Uber's Office Space")
    assert _cuu(a) == ""


def test_search_query_alt_is_not_a_caption():
    a = _anh(description="Ảnh một người đàn ông đang phát biểu.",
             alt="Anthropic CEO portrait", source="web_yandex")
    assert _cuu(a) == ""


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
