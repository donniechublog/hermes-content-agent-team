#!/usr/bin/env python3
"""Tách tên riêng từ tiêu đề bằng BẰNG CHỨNG trong thân bài (LOW-222, 17/09/2026).

Sự cố: tiêu đề title-case viết hoa mọi từ nên "Banks" (tin Blackstone/Alphabet),
"OpenAI Considers", "Financing" thành hãng. Commons ra ca sĩ Banks, Yandex/báo
thực thể/vision đều hỏi sai tên. Trước đây chặn bằng danh sách từ tay, không bao
giờ đủ. Nay hỏi chính thân bài: tên riêng thật viết hoa giữa câu, từ thường viết
thường. Thân bài trong test là văn tự soạn, mô phỏng các kiểu đã gặp trên máy chủ.

Chạy:  venv/bin/python tests/test_title_entity_evidence.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from prepare import source                                    # noqa: E402

FILLER = (" The company did not comment further on the terms of the arrangement, and people"
          " familiar with the matter said the details could still change before signing.") * 3


# ------------------------------------------------ ca gốc của ticket
def test_banks_is_a_common_word_blackstone_alphabet_are_names():
    title = "Banks arrange $22B chip loan connected to Blackstone and Alphabet in record AI infrastructure deal"
    body = ("A group of banks is arranging a $22 billion loan to buy chips, in a deal connected to"
            " Blackstone and Alphabet. The banks expect to syndicate the debt next month, while"
            " Blackstone declined to comment and a spokesperson for Alphabet pointed to earlier"
            " statements about infrastructure spending." + FILLER)
    names = source.all_proper_nouns(title, body=body)
    assert names == ["Blackstone", "Alphabet"], names


def test_title_case_verbs_are_cut_from_the_name():
    title = "OpenAI Considers New Financing at a $1.5 Trillion Valuation"
    body = ("OpenAI is considering new financing that would value the company at about $1.5 trillion,"
            " according to people briefed on the talks. The financing would come on top of earlier"
            " rounds, and the valuation discussed is not final." + FILLER)
    assert source.all_proper_nouns(title, body=body) == ["OpenAI"]


def test_name_only_at_sentence_start_still_counts():
    title = "Gimlet Labs nabs $300M for its disaggregated inference platform"
    body = ("Gimlet Labs raised $300 million in new funding. The startup sells a platform that splits"
            " inference across chips from several vendors. Frontier labs and cloud providers are its"
            " first customers." + FILLER)
    assert source.all_proper_nouns(title, body=body) == ["Gimlet Labs"]


def test_headline_lines_in_page_chrome_are_not_evidence():
    title = "Google Invests €13 Billion in Finland AI Infrastructure"
    body = ("Related\nGoogle Invests Heavily In Nordic Data Centres Today\n"
            "Google said it will invest 13 billion euros in Finland to build AI infrastructure over"
            " the next five years. The investment includes three new data centres near Helsinki,"
            " and Finland welcomed the plan." + FILLER)
    names = source.all_proper_nouns(title, body=body)
    assert names[0] == "Google", names
    assert not any("Invests" in n for n in names), names
    assert any(n.startswith("Finland") for n in names), names


def test_urls_and_hyphenated_ids_are_not_lowercase_evidence():
    title = "GPT-6 Astra: OpenAI’s Answer to Claude Opus and Fable"
    body = ("See claude.ai and the model card at docs/claude-opus-5 for details. Benchmarks put"
            " OpenAI's new model against Anthropic's Claude Opus and its Fable line, and the"
            " answer from reviewers was mixed." + FILLER)
    names = source.all_proper_nouns(title, body=body)
    assert "Claude Opus" in names and "Answer" not in names, names


# ------------------------------------------------ không có thân bài đáng tin: giữ cách tách cũ
def test_bot_wall_body_falls_back_to_title_clusters():
    title = "AI Startup Cognition Raises $2 Billion at a $48 Billion Value"
    wall = ("We've detected unusual activity from your computer network. To continue, please click"
            " the box below to let us know you're not a robot. Please make sure your browser"
            " supports JavaScript and cookies. ") * 4
    assert source.all_proper_nouns(title, body=wall) == source._title_clusters(title)


def test_no_body_is_exactly_the_title_clusters():
    title = "Qualcomm unveils Snapdragon 8 Elite chips with Amazon"
    assert source.all_proper_nouns(title, body="") == source._title_clusters(title)
    assert source.all_proper_nouns(title) == source._title_clusters(title)


def test_process_story_text_is_the_default_body():
    title = "Banks arrange $22B chip loan connected to Blackstone and Alphabet in record AI infrastructure deal"
    body = ("A group of banks is arranging a loan tied to Blackstone and Alphabet. The banks will"
            " share the risk, while Blackstone and Alphabet did not comment." + FILLER)
    try:
        source.set_story_text(body)
        assert source.all_proper_nouns(title) == ["Blackstone", "Alphabet"]
        assert source._leading_proper_noun(title) == "Blackstone"
    finally:
        source.set_story_text("")
    assert source.all_proper_nouns(title)[0] == "Banks", "hết thân bài thì về cách tách cũ"


# ------------------------------------------------ ranh giới cụm trong tiêu đề
def test_possessive_and_comma_are_name_boundaries():
    assert source._title_clusters("Hugging Face approached Nvidia’s Huang weeks ahead of acquisition") == \
        ["Hugging Face", "Nvidia", "Huang"]
    assert source._title_clusters("Cohere, Aleph Alpha combine to target enterprise AI market") == \
        ["Cohere", "Aleph Alpha"]


def test_old_cases_still_hold():
    assert source._leading_proper_noun("Gimlet Labs raises 40M | TechCrunch") == "Gimlet Labs"
    assert "Snapdragon Elite" in source.all_proper_nouns("Qualcomm launches Snapdragon 8 Elite for phones")
    assert source.all_proper_nouns("Anthropic ra tích hợp Salesforce trong Claude") == \
        ["Anthropic", "Salesforce", "Claude"]


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
