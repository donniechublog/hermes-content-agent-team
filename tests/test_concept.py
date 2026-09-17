#!/usr/bin/env python3
"""Ảnh khái niệm (image_concept.py) — kỹ năng "nhắc Nhật thì tìm cờ Nhật, tin
compute thì tìm datacenter" mà Dre từng tự làm, nay engine làm thay (07/09/2026).

Ba hàm thuần, không mạng:
  - keyword_heuristic  tiêu đề -> từ khoá; hỏng = tin không ảnh lại đi thẳng Kite.
  - filter_commons        lọc trang API Commons; hỏng = cờ vẽ CGI / logo lọt vào bìa.
  - label_concept     siết nhãn; hỏng = ảnh cờ chui vào slide thân như ảnh của tin.

Chạy:  venv/bin/python tests/test_concept.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_concept as k  # noqa: E402


def _tk(tieu_de, tom=""):
    return [x["tu_khoa"] for x in k.keyword_heuristic(tieu_de, tom)]


def test_country_and_topic_same_out():
    tk = _tk("Japan to invest $10B in AI compute, new data centers by 2027")
    assert tk[0] == "flag of Japan", tk
    assert "data center server racks" in tk, tk


def test_static_from_country_same_about_one_has():
    assert _tk("Japanese startup raises funds")[0] == "flag of Japan"
    assert _tk("Tokyo firm builds GPU cluster")[0] == "flag of Japan"


def test_write_all_distinguish_ify_regular():
    assert _tk("US chipmakers face export limits")[0] == "flag of United States"
    assert not any("United States" in t for t in _tk("Let us build chips"))


def test_only_one_country_use_mark_max_three_keyword():
    tk = _tk("China and Japan race on nuclear-powered data centers and chips")
    assert sum(t.startswith("flag of") for t in tk) == 1, tk
    assert len(tk) <= k.MAX_KEYWORD


def test_story_no_concept_then_empty():
    assert _tk("OpenAI launches GPT-6") == []
    assert _tk("") == []


def test_summary_same_ok_read():
    assert "humanoid robot" in _tk("Figure ships", "the humanoid robot maker started deliveries")


def test_read_return_error_llm_drop_junk_and_limit():
    ra = k.read_return_error_llm("KEYWORD: Tokyo skyline at night | capital\nblah\nKEYWORD: server racks\n"
                           "KEYWORD: server racks | trùng\nKEYWORD: a b c d e f g | quá dài\nKEYWORD: x | y")
    assert [x["tu_khoa"] for x in ra] == ["tokyo skyline at night", "server racks", "x"]
    assert ra[1]["ly_do"] == "gợi ý của model"
    assert k.read_return_error_llm("") == [] and k.read_return_error_llm(None) == []


# ------------------------------------------------------------- LOW-191: nhai lai vi du
def test_drop_keyword_mimic_raw_still_example_within_prompt():
    """Do that 16/09/2026: tin "TypeSafe ra System One: 193,6 lần nhanh hơn,
    444,6 lần rẻ hơn frontier model" (toc do/gia model) ra dung nguyen ba vi
    du cu trong prompt cua keyword_llm — khong lien quan toan/luat/truong hoc
    gi ca. "laboratory bench" tim tren Commons ra dung nghia den: mot cai voi
    nuoc gan ban thi nghiem, khong phai an du "benchmark"."""
    ra = k.read_return_error_llm(
        "KEYWORD: chalkboard equations | math visual\n"
        "KEYWORD: courthouse building | law visual\n"
        "KEYWORD: laboratory bench | testing visual")
    assert ra == [], ra


def test_no_block_wrong_phrase_valid_not_yet_same_from():
    """Chi chan NGUYEN VAN, khong chan substring — cum khac vi du van qua."""
    ra = k.read_return_error_llm(
        "KEYWORD: harvard laboratory renovation | that cum khac\n"
        "KEYWORD: blackboard mathematical formulas | dung tu khac chalkboard\n"
        "KEYWORD: server racks | khong nam trong danh sach vi du")
    assert [x["tu_khoa"] for x in ra] == [
        "harvard laboratory renovation", "blackboard mathematical formulas", "server racks"]


def test_all_lie_example_copy_old_all_got_block():
    for vd in ("flag flying", "a building", "a laboratory bench", "a product", "a chalkboard",
               "chalkboard equations", "courthouse", "classroom"):
        assert k.read_return_error_llm(f"KEYWORD: {vd} | ly do") == [], vd


def _pg(ten, w=1600, h=1200, mime="image/jpeg"):
    return {"title": "File:" + ten, "imageinfo": [{"width": w, "height": h, "mime": mime,
                                                  "thumburl": "https://u/" + ten.replace(" ", "_")}]}


def test_filter_commons_can_two_from_distinctive_and_drop_graphic():
    pages = {str(i): p for i, p in enumerate([
        _pg("Japan Flag at Kennedy Space Center.jpg"),
        _pg("CGI Japan Flag.png", mime="image/png"),          # dựng máy
        _pg("Japan flag - variant.png", mime="image/png"),     # cờ vẽ
        _pg("Flag of Japan.svg", mime="image/svg+xml"),        # vector
        _pg("Japan Tokyo tower.jpg"),                          # thiếu "flag"
        _pg("Japanese flag small.jpg", w=500, h=300),          # bé
        _pg("Flag map of Japan.png", mime="image/png"),        # bản đồ phẳng
    ])}
    ra = k.filter_commons(pages, "flag of Japan")
    assert [c["alt"] for c in ra] == ["Commons: Japan Flag at Kennedy Space Center.jpg"], ra
    assert ra[0]["source"] == "concept" and ra[0]["concept"]["keyword"] == "flag of Japan"


def test_filter_commons_jpeg_before_png_fall_new_black_size():
    pages = {"1": _pg("Big data center racks.png", 4000, 3000, "image/png"),
             "2": _pg("Small data center racks.jpg", 1000, 800),
             "3": _pg("Huge data center racks.jpg", 3000, 2000)}
    ra = k.filter_commons(pages, "data center server racks")
    assert [c["alt"] for c in ra] == ["Commons: Huge data center racks.jpg",
                                      "Commons: Small data center racks.jpg",
                                      "Commons: Big data center racks.png"]


def test_name_type_no_catch_string_remaining():
    """09/09/2026: "icon" trần nằm trong "sil-icon" nên MỌI ảnh silicon wafer bị
    bỏ — mà đó là từ khoá khái niệm của toàn bộ tin bán dẫn. "graph" nằm trong
    "photograph", "chart" nằm trong "Charterhouse"."""
    pages = {"1": _pg("12-inch silicon wafer.jpg"), "2": _pg("Silicon wafer closeup.jpg")}
    assert len(k.filter_commons(pages, "silicon wafer")) == 2
    assert not k.NAME_TYPE.search("aerial photograph of the campus")
    assert not k.NAME_TYPE.search("charterhouse square")
    # vẫn phải bắt đúng thứ nó sinh ra để bắt
    for x in ("app icon.png", "bar graph of sales.png", "chart of revenue.png", "company logo.png"):
        assert k.NAME_TYPE.search(x), x


def test_philippines_has_within_board_country():
    """Bảng SEA có đủ 5 nước còn lại; thiếu Philippines nên tin "Philippines rót
    34 tỷ USD" không ra từ khoá nào (09/09/2026)."""
    assert _tk("Philippines plans $34B to catch up in the AI race")[0] == "flag of Philippines"


def test_filter_commons_empty_when_no_has_what():
    assert k.filter_commons({}, "x") == [] and k.filter_commons(None, "x") == []


def _image(**o):
    a = {"concept": {"keyword": "flag of Japan", "reason": "tin nhắc tới Japan"}, "kind": "photo",
         "faces": 0, "landscape": False, "relevant": True, "uses": ["cover", "body"],
         "notes": ["ảnh CHUNG của hãng từ Wikimedia Commons (trụ sở/sản phẩm), không phải ảnh của tin"]}
    a.update(o)
    return a


def test_label_concept_only_cover_no_than():
    a = k.label_concept(_image())
    assert a["uses"] == ["cover"]
    assert a["notes"][0].startswith("🧭 ẢNH KHÁI NIỆM") and "flag of Japan" in a["notes"][0]
    assert not any("ảnh CHUNG của hãng" in g for g in a["notes"])


def test_label_concept_landscape_only_stack():
    a = k.label_concept(_image(landscape=True, uses=["stack_vertical", "landscape_crop_if_no_text"]))
    assert a["uses"] == ["stack_vertical"]


def test_label_concept_chart_or_face_then_drop():
    assert k.label_concept(_image(kind="chart"))["uses"] == []
    a = k.label_concept(_image(faces=2))
    assert a["uses"] == [] and a["notes"][0].startswith("❌")


def test_label_concept_keep_raw_when_vision_already_type():
    a = k.label_concept(_image(relevant=False, uses=[], notes=["❌ KHÔNG LIÊN QUAN BÀI (vision) → KHÔNG DÙNG"]))
    assert a["uses"] == [] and a["notes"][0].startswith("❌ KHÔNG LIÊN QUAN")


def test_filter_commons_drop_has_war_and_protest():
    pages = {"1": _pg("Rising Sun Flag of Japan JS Aishima.jpg"), "2": _pg("Japan flag protest Tokyo.jpg"),
             "3": _pg("Waving Japanese flag.jpg")}
    assert [c["alt"] for c in k.filter_commons(pages, "flag of Japan")] == ["Commons: Waving Japanese flag.jpg"]


def test_manifest_count_cluster_concept_is_one():
    """5 lá cờ không phải 5 slide: so_dung_duoc = ảnh riêng + tối đa 1 khái niệm."""
    import image_prepare as cb
    from pathlib import Path
    def _a(ma, kn=False):
        return {"id": ma, "uses": ["cover"], "relevant": True, "domain": "x", "source": "x", "ratio": 0.8,
                "bottom_left_brightness": 50, "short_side": 1000, "landscape": False, "kind": "photo",
                **({"concept": {"keyword": "flag of Japan"}} if kn else {})}
    anh = [_a("A1"), _a("A2", True), _a("A3", True), _a("A4", True)]
    m = cb.build_manifest("t", {"brand": "dcgr"}, "t", "http://x", {}, Path("/nonexist"), {}, Path("/tmp"),
                         anh, None, False, {}, {}, False, 5, vai_anh="ethan")
    assert m["usable_count"] == 2, m["usable_count"]
    assert m["cover_suggestions"][0] == "A1", m["cover_suggestions"]


def test_sentence_ask_vision_say_clear_no_right_image_of_story():
    c = k.sentence_ask_vision("Japan to invest", "flag of Japan")
    assert "KHONG phai anh cua tin" in c and "flag of Japan" in c and "LIEN_QUAN" in c


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
