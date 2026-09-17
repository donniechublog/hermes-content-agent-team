#!/usr/bin/env python3
"""Ảnh thương hiệu (image_brand.py) — "tin về Big Brand mà kho ảnh mỏng thì
đi tìm trụ sở/campus của chính hãng đó", việc Dre không tự làm được từ khi vai
mất công cụ tìm ảnh (Ông Chủ 09/09/2026).

Bốn hàm thuần, không mạng:
  - vendors_in_story    tiêu đề -> hãng; hỏng = tin hai hãng chỉ hỏi được một.
  - truy_van          hãng -> câu hỏi Commons; hỏng = hỏi tên trần, ra ảnh hội thảo mờ.
  - filter_commons       lọc trang API; hỏng = rừng Amazon / quả táo lọt vào bộ.
  - label_brand  siết nhãn; hỏng = mặt người vô danh lên bìa (IMAGE_RULES §6).

Chạy:  venv/bin/python tests/test_brand.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_brand as th  # noqa: E402


def _h(tieu_de, tom=""):
    return [x["company"] for x in th.vendors_in_story(tieu_de, tom)]


def test_two_rank_within_one_story_all_out():
    """Tin sáng 09/09 làm lộ lỗi: `_leading_proper_noun` chỉ ra "Qualcomm", Amazon
    không bao giờ được hỏi tới."""
    assert _h("Qualcomm signs AI chip deal with Amazon, option to buy $4B in shares") \
        == ["Qualcomm", "Amazon"]


def test_by_order_export_show():
    assert _h("Amazon and Qualcomm sign chip deal") == ["Amazon", "Qualcomm"]


def test_name_model_rule_about_rank_text():
    assert _h("Claude Opus 5 tops the coding leaderboard") == ["Anthropic"]
    assert _h("Xiaomi ra mắt Pad 9 Pro Max, chip Xring O3") == ["Xiaomi"]
    assert _h("Gemini 3 ships to enterprise") == ["Google"]


def test_max_three_rank_and_no_duplicate():
    ra = _h("OpenAI, Google, Meta, Nvidia and Amazon all raise AI spending")
    assert ra == ["OpenAI", "Google", "Meta Platforms"], ra
    assert _h("OpenAI ships GPT-6; OpenAI says ChatGPT grew") == ["OpenAI"]


def test_name_ceiling_watchlist_no_keep():
    """WATCHLIST giữ "google deepmind"/"meta ai" (dạng liên quan AI); tin thì
    viết "Google", "Meta". Bù bằng NAME_EXTRA, không sửa WATCHLIST."""
    assert _h("Google cuts cloud prices") == ["Google"]
    assert _h("Meta buys a data center site") == ["Meta Platforms"]
    assert _h("Snapdragon 8 Elite ships") == ["Qualcomm"]


def test_border_from_no_catch_wrong():
    """"arm" không được khớp "harm", "intel" không khớp "intelligence" —
    cùng loại lỗi mà scan_business đã chặn cho watchlist."""
    assert _h("New rules to prevent harm from artificial intelligence") == []
    assert _h("Arm licenses new core to phone makers") == ["Arm Holdings"]


def test_summary_same_ok_read_and_story_no_rank_then_empty():
    assert _h("Philippines plans $34B to catch up in the AI race") == []
    assert _h("Philippines plans $34B", "the plan leans on Nvidia hardware") == ["Nvidia"]
    assert _h("") == []


def test_query_ask_straight_except_count_no_ask_name_ceiling():
    cau = [c for _, c in th.query("qualcomm")]
    assert cau == ["Qualcomm headquarters", "Qualcomm building", "Qualcomm campus"], cau
    assert "Qualcomm" not in cau                # tên trần là cách cũ, ra ảnh lạc đề


def test_query_use_all_name_secondary_and_has_ceiling():
    ten = [t for t, _ in th.query("meta")]
    assert ten == ["Meta Platforms"] * 3 + ["Facebook"], ten
    assert len(th.query("meta")) <= th.MAX_QUERY


def _pg(ten, w=1600, h=1200, mime="image/jpeg"):
    return {"title": "File:" + ten, "imageinfo": [{"width": w, "height": h, "mime": mime,
                                                  "thumburl": "https://u/" + ten.replace(" ", "_")}]}


def test_filter_change_name_rank_within_name_file():
    """Commons trả cả ảnh chỉ khớp hậu tố: "MHealth Attendees at FCC's
    Headquarters" là ảnh THẬT trả về cho câu "Qualcomm headquarters" (09/09)."""
    pages = {str(i): p for i, p in enumerate([
        _pg("Qualcomm Headquarters La Jolla.jpg", 4036, 3456),
        _pg("MHealth Attendees at FCC's Headquarters.jpg"),      # không có "qualcomm"
        _pg("Qualcomm logo sign.jpg"),                           # đồ hoạ
        _pg("Qualcomm building small.jpg", 500, 400),            # bé
    ])}
    assert [c["alt"] for c in th.filter_commons(pages, "Qualcomm")] \
        == ["Commons: Qualcomm Headquarters La Jolla.jpg"]


def test_filter_drop_many_forest_amazon_and_over_create():
    pages = {"1": _pg("Amazon Spheres Seattle.jpg"), "2": _pg("Amazon rainforest canopy.jpg"),
             "3": _pg("Amazon river at dusk.jpg")}
    assert [c["alt"] for c in th.filter_commons(pages, "Amazon")] == ["Commons: Amazon Spheres Seattle.jpg"]
    tao = {"1": _pg("Apple Park aerial view.jpg"), "2": _pg("Apple tree in blossom.jpg")}
    assert [c["alt"] for c in th.filter_commons(tao, "Apple")] == ["Commons: Apple Park aerial view.jpg"]


def test_filter_drop_image_rally_gate_guess():
    """Đo thật 09/09/2026: câu "Amazon building" trả về hai tấm "International
    Day of Solidarity With Alabama Amazon Workers" — đúng chữ Amazon, sai hẳn
    loại ảnh cho tin ký hợp đồng chip. Tên tệp không có chữ "protest" nên
    NAME_TYPE không bắt được."""
    pages = {"1": _pg("International Day of Solidarity With Alabama Amazon Workers 01.jpg"),
             "2": _pg("Amazon workers strike in Coventry.jpg"),
             "3": _pg("Amazon Spheres Seattle.jpg")}
    assert [c["alt"] for c in th.filter_commons(pages, "Amazon")] == ["Commons: Amazon Spheres Seattle.jpg"]


def test_filter_no_catch_wrong_straight_three_and_union_square():
    """"march" trùng tháng Ba, "union" trần trùng Union Square — không đưa vào."""
    pages = {"1": _pg("Apple Store Union Square San Francisco.jpg"),
             "2": _pg("Apple Park March 2024.jpg")}
    assert len(th.filter_commons(pages, "Apple")) == 2


def test_filter_no_change_from_common_within_name_gate_billion():
    """"Mistral AI headquarters" mà bắt tên tệp chứa "ai" thì không tệp nào qua."""
    pages = {"1": _pg("Mistral office Paris.jpg")}
    assert len(th.filter_commons(pages, "Mistral AI")) == 1


def test_filter_border_from_chat_than_string_remaining():
    pages = {"1": _pg("Armstrong Building Ohio.jpg"), "2": _pg("Arm Cambridge office.jpg")}
    assert [c["alt"] for c in th.filter_commons(pages, "Arm Holdings")] == ["Commons: Arm Cambridge office.jpg"]


def test_filter_jpeg_before_png_fall_new_black_size():
    pages = {"1": _pg("Samsung Town big.png", 4000, 3000, "image/png"),
             "2": _pg("Samsung Town small.jpg", 1000, 800),
             "3": _pg("Samsung Town huge.jpg", 3000, 2000)}
    assert [c["alt"] for c in th.filter_commons(pages, "Samsung")] == [
        "Commons: Samsung Town huge.jpg", "Commons: Samsung Town small.jpg",
        "Commons: Samsung Town big.png"]


def test_filter_empty_when_no_has_what():
    assert th.filter_commons({}, "Qualcomm") == [] and th.filter_commons(None, "Qualcomm") == []


def _image(**o):
    a = {"brand_match": {"company": "Qualcomm", "key": "qualcomm", "kind": "photo",
                         "keyword": "Qualcomm headquarters"},
         "kind": "photo", "faces": 0, "landscape": False, "relevant": True, "uses": ["cover", "body"],
         "notes": ["ảnh CHUNG của hãng từ Wikimedia Commons (trụ sở/sản phẩm), không phải ảnh của tin"]}
    a.update(o)
    return a


def test_label_keep_all_cover_attempt_than():
    """Khác ảnh khái niệm: ảnh của CHÍNH hãng trong tin được vào slide thân."""
    a = th.label_brand(_image())
    assert a["uses"] == ["cover", "body"]
    assert a["notes"][0].startswith("🏢 ẢNH THƯƠNG HIỆU (Qualcomm)")
    assert not any("ảnh CHUNG của hãng" in g for g in a["notes"])


def test_label_drop_face_anonymous():
    a = th.label_brand(_image(faces=2))
    assert a["uses"] == [] and a["notes"][0].startswith("❌") and "§6" in a["notes"][0]


def test_label_drop_chart():
    a = th.label_brand(_image(kind="chart"))
    assert a["uses"] == [] and a["notes"][0].startswith("❌")


def test_label_keep_raw_when_vision_already_type():
    a = th.label_brand(_image(relevant=False, uses=[],
                                 notes=["❌ KHÔNG LIÊN QUAN BÀI (vision) → KHÔNG DÙNG"]))
    assert a["uses"] == [] and a["notes"][0].startswith("❌ KHÔNG LIÊN QUAN")


def test_manifest_count_enough_and_arrange_cover_after_image_own():
    """Ảnh thương hiệu ĐẾM ĐỦ (khác chùm khái niệm chỉ đếm là một) nhưng vẫn
    đứng sau ảnh riêng của tin, trước ảnh khái niệm, ở gợi ý bìa."""
    import image_prepare as cb

    def _a(ma, kn=False, thh=False):
        return {"id": ma, "uses": ["cover"], "relevant": True, "domain": "x", "source": "x", "ratio": 0.8,
                "bottom_left_brightness": 50, "short_side": 1000, "landscape": False, "kind": "photo",
                **({"concept": {"keyword": "silicon wafer"}} if kn else {}),
                **({"brand_match": {"company": "Qualcomm"}} if thh else {})}

    anh = [_a("A1", kn=True), _a("A2", thh=True), _a("A3"), _a("A4", thh=True)]
    m = cb.build_manifest("t", {"brand": "dcgr"}, "t", "http://x", {}, Path("/nonexist"), {},
                         Path("/tmp"), anh, None, False, {}, {}, False, 5, vai_anh="ethan")
    assert m["usable_count"] == 4, m["usable_count"]          # 3 riêng/thương hiệu + 1 khái niệm
    assert m["cover_suggestions"] == ["A3", "A2", "A4"], m["cover_suggestions"]


# ---- hồ sơ Wikidata: logo, founder/CEO, bảng xếp hạng ----------------------
def _claim_person(qid, het=False, bac="normal"):
    c = {"mainsnak": {"datavalue": {"value": {"id": qid, "entity-type": "item"}}}, "rank": bac}
    if het:
        c["qualifiers"] = {"P582": [{}]}          # end time = đã thôi chức
    return c


def test_qid_claim_drop_person_already_time_function():
    """Wikidata giữ cả người tiền nhiệm trong P169: hỏi CEO OpenAI trả về cả Sam
    Altman lẫn Mira Murati (CEO tạm quyền), phân biệt bằng qualifier P582. Không
    lọc thì brief ghi sai tên CEO mà vai không có đường nào kiểm (09/09/2026)."""
    cl = {"P169": [_claim_person("Q1"), _claim_person("Q2", het=True),
                   _claim_person("Q3", bac="deprecated")]}
    assert th._qid_claim(cl, "P169") == ["Q1"]
    assert th._qid_claim({}, "P169") == [] and th._qid_claim(None, "P169") == []


def test_file_claim_only_take_name_file():
    cl = {"P154": [{"mainsnak": {"datavalue": {"value": "X logo.svg"}}},
                   {"mainsnak": {"datavalue": {"value": {"id": "Q9"}}}}]}   # sai kiểu
    assert th._file_claim(cl, "P154") == ["X logo.svg"]


def test_rank_has_model_only_rank_make_model():
    """Chỉ hãng có model trên bảng mới đáng mở browser đi chụp bảng."""
    assert th.rank_has_model("deepseek") and th.rank_has_model("openai")
    assert not th.rank_has_model("qualcomm") and not th.rank_has_model("tsmc")


def test_sentence_ask_vision_no_ask_has_right_image_of_story():
    """Câu chung hỏi "có phải ảnh của tin không" — chân dung founder và thẻ logo
    chắc chắn không phải, nên bị đánh rớt đúng lúc ta cần chúng nhất."""
    c = th.sentence_ask_vision("Kiện Anthropic", {"company": "Anthropic", "kind": "person",
                                             "person": "Dario Amodei", "person_role": "CEO"})
    assert "Dario Amodei" in c and "CHAN DUNG" in c and "LIEN_QUAN" in c
    c = th.sentence_ask_vision("DeepSeek gọi vốn", {"company": "DeepSeek", "kind": "logo"})
    assert "THE LOGO" in c and "DeepSeek" in c
    c = th.sentence_ask_vision("Qualcomm ký", {"company": "Qualcomm", "kind": "photo"})
    assert "BOI CANH" in c and "mit tinh" in c


def test_label_block_use_change_declare_use_name():
    a = th.label_brand(_image(brand_match={"company": "Anthropic", "kind": "person",
                                              "person": "Dario Amodei", "person_role": "CEO"}, faces=1))
    assert a["uses"] == ["cover", "body"]
    assert "Dario Amodei" in a["notes"][0] and "nhan_vat" in a["notes"][0]


def test_label_block_use_no_block_by_face():
    """`count_faces` trả None (-> 0) khi thiếu cv2, mà IMAGE_RULES §6 cho phép cổng mặt
    tự tắt. Lấy mat==0 làm "không phải chân dung" là bỏ câm lặng mọi chân dung."""
    a = th.label_brand(_image(brand_match={"company": "Anthropic", "kind": "person",
                                              "person": "Dario Amodei", "person_role": "CEO"}, faces=0))
    assert a["uses"] == ["cover", "body"], a["uses"]


def test_label_card_logo_go_notes_chart_color_pure():
    """Thẻ logo là nền trơn + chữ nên `classify` đọc ra "chart" và dán kèm
    "KHÔNG làm bìa" — ngược hẳn công dụng của nó (09/09/2026)."""
    a = th.label_brand(_image(brand_match={"company": "DeepSeek", "kind": "logo", "background_tone": "dark"},
                                 kind="chart", uses=["body_chart_full_width"],
                                 notes=["chart cao, đã cắt bớt phần dưới về 4:5", "KHÔNG làm bìa"]))
    assert a["uses"] == ["cover"]
    assert not any("KHÔNG làm bìa" in g or "chart" in g.lower() for g in a["notes"]), a["notes"]


def test_label_card_logo_only_cover_and_say_clear_background():
    a = th.label_brand(_image(brand_match={"company": "DeepSeek", "kind": "logo", "background_tone": "dark"}))
    assert a["uses"] == ["cover"]
    assert a["notes"][0].startswith("🔖 THẺ LOGO DeepSeek") and '"nen": "toi"' in a["notes"][0]
    b = th.label_brand(_image(brand_match={"company": "Anthropic", "kind": "logo", "background_tone": "light"}))
    assert '"nen": "sang"' in b["notes"][0]


def test_label_board_ranking_say_clear_no_right_board_of_story():
    a = th.label_brand(_image(brand_match={"company": "DeepSeek", "kind": "ranking",
                                              "site": "ARENA", "board": "Text"},
                                 kind="chart", uses=["body_chart"]))
    assert a["uses"] == ["body_chart"]                  # chart CỦA BẢNG thì giữ
    assert "KHÔNG phải bảng của tin này" in a["notes"][0] and "ARENA" in a["notes"][0]


def test_ua_wikimedia_only_send_wait_use_host_wikimedia():
    """UA riêng chỉ đi tới host Wikimedia thật, không đi tới host nhái."""
    import image_prepare as cb
    import env_load
    for u in ("https://upload.wikimedia.org/a.jpg", "https://en.wikipedia.org/a.jpg"):
        assert cb._hdr(u)["User-Agent"] == env_load.UA_WIKI, u
    for u in ("https://evil-wikimedia.org/a.jpg", "https://wikimedia.org.evil.com/a.jpg",
              "https://theverge.com/a.jpg", ""):
        assert cb._hdr(u)["User-Agent"] == cb.UA, u


def test_ua_wikimedia_has_path_contact():
    """Wikimedia trả 403 cho UA kiểu trình duyệt; phải có ngoặc chứa đường liên
    hệ. Đây là lỗi làm CHẾT CÂM LẶNG cả đường Commons trước 09/09/2026."""
    import env_load
    assert "(" in env_load.UA_WIKI and "http" in env_load.UA_WIKI
    assert not env_load.UA_WIKI.startswith("Mozilla")
    import image_concept
    assert image_concept.UA == env_load.UA_WIKI


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
