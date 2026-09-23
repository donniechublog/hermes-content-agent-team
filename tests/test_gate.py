#!/usr/bin/env python3
"""Kiem cac CONG CHAN thêm ngày 06/09/2026 — trọng tâm là CHẶN OAN.

Một cổng chặn sai làm vai không nộp được bài, tệ hơn nhiều so với việc thiếu
cổng: vai sửa kiểu gì cũng sai và Ông Chủ chỉ thấy im lặng. Ngày 06/09
`check_quote_translated` đã chặn 5/6 hook hợp lệ vì chỉ đo dấu tiếng Việt, nên mọi
cổng ở đây phải có ví dụ ĐÚNG-PHẢI-QUA đi kèm ví dụ SAI-PHẢI-CHẶN.

Chạy:  venv/bin/python tests/test_gate.py

Ba lệnh subprocess trong tệp này gọi `sys.executable`, KHÔNG gõ cứng
`venv/bin/python`: đường cứng chỉ đúng trên Linux/macOS và làm test đỏ trên
Windows (`venv/Scripts/python.exe`) dù mã chính hoàn toàn ổn — xem lý do đầy đủ
trong docstring của `material.extract()`.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import submit_common as nc      # noqa: E402
import required as bb       # noqa: E402
import caption_check as cc  # noqa: E402
import state_paths                                            # noqa: E402


# `so_tam` da chuyen sang tests/tam.py 07/09/2026: tep test thu hai can dung
# no, va bai hoc cua chinh no la mot ban sua mot cho ma quen cho kia.
from tam import so_tam as _so_tam  # noqa: E402


# ---------------------------------------------------------------- quote dịch
QUOTE_PHAI_QUA = [
    # nhãn toàn tên riêng + số: không có dấu nào, nhưng hoàn toàn hợp lệ
    "Claude Opus 4.5 vs GPT-5.2: 82,5 vs 79,1 MMLU",
    "GPT-5 Codex Max: 2,75 USD / 1M token",
    "DeepSeek V4: 671B params, MIT license",
    "Qwen3-Max: 1 trieu token context",
    # tiếng Việt chuẩn
    "Mô hình mở đầu tiên vượt GPT-5 trên SWE-bench",
    # tiếng Việt gõ mất dấu: card.find_face_mark lo việc này, không phải cổng này
    "GPT-5 Codex Max ra mat, benchmark SWE-bench tang 12 diem so voi ban truoc",
]
QUOTE_PHAI_CHAN = [
    "AI agents are now writing most of the code at this company, says the CEO",
    "We are seeing a step change in how these models handle long context windows",
    "This is the first open model that beats GPT-5 on SWE-bench, and it runs locally",
]


def test_quote_translate_no_block_wrongly():
    for t in QUOTE_PHAI_QUA:
        assert nc.check_quote_translated(t, "hook") == [], f"chặn oan: {t}"


def test_quote_translate_still_catch_language_image():
    for t in QUOTE_PHAI_CHAN:
        assert nc.check_quote_translated(t, "hook"), f"lọt tiếng Anh: {t}"


def test_quote_translate_skip_string_short():
    assert nc.check_quote_translated("It is what it is", "hook") == []   # < 25 ký tự


def test_guide_source_compact_catch_phrase_excess():
    for t in ('Đọc bài "TSMC hits record" - btimesonline.com',
              "Xem bài chi tiết trên techcrunch.com",
              "Nguồn: reuters.com"):
        assert nc.check_guide_source_compact(t, "attrib"), f"lọt cụm thừa/tên miền: {t}"


def test_guide_source_compact_catch_name_domain_enough_no_has_phrase_read_article():
    assert nc.check_guide_source_compact("via businesstimes.com", "attrib")


def test_guide_source_compact_no_block_wrongly():
    for t in ("via BusinessTimes", "CEO TSMC", "Phát biểu của C.C. Wei, CEO TSMC",
              "TSMC vừa báo doanh thu tháng 8 đạt 514,8 tỷ Đài tệ.",
              "So với tháng 7, tăng 10,1%.", ""):
        assert nc.check_guide_source_compact(t, "attrib") == [], f"chặn oan: {t}"


# --------------------------------------------------------------- nhân vật
def test_subject_three_layer():
    anh = {"A1": {"faces": True, "description": "chan dung CEO"},
           "A2": {"faces": False},
           "A3": {"faces": True, "description": "anh quan chuc G20"}}
    # có mặt, không khai tên
    assert nc.check_subject_named(anh, ["A1"], "", "hock tan noi", "")
    # khai tên có trong bài
    assert nc.check_subject_named(anh, ["A1"], "Hock Tan, Broadcom", "ceo hock tan cua broadcom", "") == []
    # khai tên KHÔNG có trong bài (bịa)
    assert nc.check_subject_named(anh, ["A1"], "Hock Tan", "bai noi ve nvidia va jensen huang", "")
    # vision mô tả G20
    assert any("không phải nhân vật" in x for x in nc.check_subject_named(anh, ["A3"], "Jensen Huang", "jensen huang", ""))
    # ảnh không mặt / mã None không làm vỡ
    assert nc.check_subject_named(anh, ["A2", None], "", "abc", "") == []


# ------------------------------------------------------------------- số lạ
def test_count_is_change_single_vi_no_got_report():
    tl = "- Model dat 82,5 diem MMLU, gia 3 USD moi trieu token.\n- Huy dong 500 trieu USD."
    assert cc.count_is("Model dat 82,5 diem", tl) == []
    assert cc.count_is("chi 5 cai", tl) == []                    # 1 chữ số: bỏ qua
    assert cc.count_is("dat 99,9 diem va 1234 ty", tl) == ["99,9", "1234"]


# ------------------------------------------------------------ bắt buộc khớp
def test_match_still_label_out_item_real():
    that = [
        ("GPT-5.2", "OpenAI ra mat GPT-5.2 voi cua so 2 trieu token"),
        ("o4-mini", "OpenAI phat hanh o4-mini gia re"),
        ("Qwen3-Max", "Alibaba cong bo Qwen3-Max"),
        ("Gemini 3 Pro", "Google ra Gemini 3 Pro"),
        ("Claude Opus 4.5", "Anthropic ra mat Claude Opus 4.5"),
        ("Grok 5", "xAI ra mat Grok 5"),
        ("R2", "DeepSeek ra R2"),
    ]
    for ten, tieu_de in that:
        assert bb.match({"name": ten}, {"title": tieu_de, "summary_vi": ""}), f"trượt: {ten}"


def test_match_no_remaining_match_random_with_fragment_short():
    # "v3"/"ai" là mảnh 2 ký tự: trước 06/09 khớp gần như mọi tiêu đề
    assert bb.match({"name": "v3 ai"}, {"title": "bai nao cung co v3 va ai", "summary_vi": ""}) is False


def test_match_priority_link_and_keyword():
    assert bb.match({"link": "https://x.com/a/"}, {"link": "http://www.x.com/a"})
    assert bb.match({"keywords": ["nvidia", "hugging"]}, {"title": "Nvidia mua Hugging Face", "summary_vi": ""})
    assert not bb.match({"keywords": ["nvidia", "hugging"]}, {"title": "Nvidia ra chip moi", "summary_vi": ""})


# ------------------------------------------------------------------ teaser
def test_teaser_block_url_emoji_list_count():
    import teaser_assemble as ta
    day = ("Con so chi phi o muc 2,75 USD moi task, thap hon ba lan doi thu tren thi truong va van "
           "giu chat luong dau ra theo bo do luong cong khai cua ben thu ba doc lap. ") * 3
    ok = [day, day, day]
    # lay_emoji gia: khong duoc dung vao so xoay vong that (state/emoji_deck.json)
    gia = lambda n: ["•"] * n                                # noqa: E731
    assert ta.assemble("T", ok, [], lay_emoji=gia)["word_count"] > 0   # đoạn sạch thì qua
    for xau, ten in [("Chi tiet o https://example.com/x " + day, "URL"),
                     ("1. Muc dau tien noi ve chi phi " + day, "đánh số"),
                     ("🚀 Mo hinh moi chay nhanh hon " + day, "emoji")]:
        try:
            ta.assemble("T", [xau] + ok, [], lay_emoji=gia)
        except ValueError:
            pass
        else:
            raise AssertionError(f"không chặn {ten}")


def test_teaser_no_catch_wrong_ky_from_vietnamese():
    # ế ộ ữ … — “ ” đều dưới U+2500, không được coi là emoji
    for c in "ếộữ…—“”•":
        assert ord(c) < 0x2500, f"{c!r} U+{ord(c):04X} sẽ bị coi là emoji"


# ------------------------------------------------------- tin xếp hạng không bảng
def test_story_ranking_no_has_board_then_no_block():
    """Bẫy 06/09: tiêu đề trông như tin xếp hạng nhưng không nêu tên model →
    engine không chụp được bảng → không có mã "XH". Nếu cổng vẫn đòi "XH" thì
    vai sửa kiểu gì cũng sai và không bao giờ nộp được."""
    import image_prepare as cb
    import ranking as xh
    # tiêu đề kiểu này: là tin xếp hạng nhưng không tách được model
    for t in ["Bảng xếp hạng AI tháng 9: ai đang dẫn đầu",
              "LMArena leaderboard cập nhật tuần này"]:
        assert xh.is_ranking_story(t, ""), t
        assert not xh.extract_model(t), f"{t}: nếu tách được model thì bẫy không xảy ra"
    # brief KHÔNG được đòi mã XH khi không có
    dong = cb.ranking_brief_line({"is_ranking_story": True, "ranking": None}, "bìa", "dre_submit")
    assert "BẮT BUỘC" not in dong and "chặn ảnh khác" not in dong, dong
    assert "không chặn" in dong, dong
    # có bảng thì vẫn đòi như cũ
    dong2 = cb.ranking_brief_line(
        {"is_ranking_story": True, "ranking": {"site": "LMArena", "board": "text",
                                            "model": "GPT-5.2", "rank": 1, "kind": "table"}},
        "", "ethan_submit")
    assert "BẮT BUỘC" in dong2, dong2


def test_gate_ranking_only_block_when_capture_ok_board():
    """dre_submit/ethan_submit chỉ được chặn khi engine CHỤP được bảng thật
    (`ranking.is_capture(kind)`). Không có ảnh XH, hoặc chỉ có thẻ dự phòng engine
    tự dựng, đều không được ép — xem test_fallback_card_no_ok_force_make_image_main."""
    import re as _re
    mau = r'ranking\.is_capture\(\(m\.get\("ranking"\) or \{\}\)\.get\("kind"\)\)'
    # Tu 07/09/2026 dieu kien nam o MOT cho (submit_common.needs_ranking_image); hai vai
    # phai goi no chu khong tu viet lai — tu viet lai la cach no da lech.
    assert _re.search(mau, (ROOT / "submit_common.py").read_text(encoding="utf-8")), \
        "submit_common.needs_ranking_image phải hỏi ranking.is_capture(kieu)"
    for tep in ("dre_submit.py", "ethan_submit.py"):
        src = (ROOT / tep).read_text(encoding="utf-8")
        assert "nc.needs_ranking_image(" in src, f"{tep}: phải dùng cổng chung"
        assert not _re.search(mau, src), f"{tep}: còn bản chép tay của điều kiện"


# ------------------------------------------------ tin xếp hạng: nhận diện & thẻ bịa
TIEU_DE_THUONG = [
    "Reflection gọi vốn 2 tỷ USD, vòng seed do Nvidia dẫn đầu",
    "OpenAI vượt mốc 1 tỷ người dùng hàng tuần",
    "Doanh thu Anthropic vượt 10 tỷ USD năm 2026",
    "Nvidia công bố GPU mới, giá vượt 40.000 USD",
    "Cuộc đua chip AI: TSMC dẫn đầu về công suất 2nm",
    "Amazon ra chip Nova mới cho trung tâm dữ liệu",
]
TIEU_DE_XEP_HANG = [
    "GPT-5.2 leo lên #1 trên bảng xếp hạng LMArena",
    "Gemini 3 Pro đứng đầu bảng xếp hạng Text Arena",
    "Claude Opus 4.5 vượt GPT-5 trên leaderboard SWE-bench",
    "Qwen3-Max lọt top 3 Intelligence Index",
]


def test_story_regular_no_got_stamp_ranking():
    """Trước 06/09 mọi chữ 'vượt/dẫn đầu/số 1' đều kích hoạt, kéo engine đi lục
    12 bảng xếp hạng cho một tin gọi vốn rồi dựng thẻ số liệu bịa."""
    import ranking as xh
    for t in TIEU_DE_THUONG:
        assert not xh.is_ranking_story(t, ""), f"vẫn bắt nhầm: {t}"


def test_story_ranking_real_still_ok_label():
    import ranking as xh
    for t in TIEU_DE_XEP_HANG:
        assert xh.is_ranking_story(t, ""), f"mất nhận diện: {t}"


def test_model_family_duplicate_from_regular_right_go_with_count():
    """'seed', 'nova', 'solar'... chỉ là tên model khi có số phiên bản."""
    import ranking as xh
    assert xh.extract_model("vòng seed do Nvidia dẫn đầu") == []
    assert xh.extract_model("Amazon ra chip Nova mới") == []
    assert xh.extract_model("IBM mở nguồn Granite 4"), "Granite 4 phải nhận ra"
    assert xh.extract_model("GPT-5.2 leo lên #1"), "GPT-5.2 phải nhận ra"


def test_fallback_card_no_ok_force_make_image_main():
    """kind='card' là thẻ engine tự dựng, chưa đọc bảng thật — không được loại bỏ
    ảnh thật. Chỉ kieu chụp thật (`ranking.KIND_CAPTURE`) mới bật cổng bắt buộc."""
    import ethan_submit
    anh = [{"id": "A1", "original_path": "/tmp/x.png", "ready_path": None, "kind": "photo", "ratio": 1.0,
            "faces": 0, "landscape": False, "short_side": 1200, "w": 1200, "h": 1200,
            "bottom_left_brightness": 50, "uses": ["nền hero"], "notes": [], "domain": "x.com",
            "source": "x", "relevant": True}]
    spec = {"image": "A1", "card_style": "quote", "hook": "Mô hình mới đạt điểm cao nhất bảng",
            "tagline": "MODEL", "attrib": "via X"}
    for kieu, phai_chan in (("table", True), ("list", True), ("card", False), ("chup", False)):
        m = {"images": anh, "is_ranking_story": True, "article_text": "", "material": {}, "draft_id": "d1",
             "image_role": "ethan",
             "ranking": {"kind": kieu, "site": "arena.ai", "board": "Text Arena",
                          "model": "seed", "rank": 5}}
        _, loi, _ = ethan_submit.resolve_spec(spec, m, Path("/tmp"))
        co = any("XẾP HẠNG" in x for x in loi)
        assert co == phai_chan, f"kieu={kieu}: {'phải chặn' if phai_chan else 'không được chặn'}"


# ------------------------------------------------- sổ ảnh đã dùng: khoá theo TIN
def test_count_image_lock_by_story_no_by_draft():
    """Cùng một tin giao cho Dre rồi Ethan ra hai draft_id khác nhau nhưng dùng
    chung bộ ảnh — vai sau không được bị chặn sạch."""
    import image_rules_ethan as la
    from PIL import Image, ImageDraw
    with tempfile.TemporaryDirectory() as tmp, _so_tam(tmp) as d:
        p = d / "a.png"
        im = Image.new("RGB", (800, 600), (255, 255, 255))
        dr = ImageDraw.Draw(im)
        for i, h in enumerate([380, 300, 240, 180, 120]):
            dr.rectangle([60 + i * 140, 500 - h, 160 + i * 140, 500], fill=(40, 90, 200))
        im.save(p)
        LINK = "https://openai.com/tin-abc"
        la.record_used(p, "tin-abc-carousel-blog", "dre", LINK)
        # cùng tin, vai khác -> KHÔNG chặn
        assert la.check_not_reused("A1", p, "tin-abc-designer-blog", LINK)[0] == []
        # tin khác dùng lại đúng tấm đó -> CHẶN
        assert la.check_not_reused("A1", p, "tin-xyz-carousel-blog", "https://x.com/khac")[0]


def test_lock_story_standard_ify_url():
    import image_provenance as la
    assert la.story_key("https://www.OpenAI.com/tin/") == la.story_key("http://openai.com/tin")
    assert la.story_key("https://x.com/a?utm=1#z") == "x.com/a"


# ------------------------------------------- ảnh xếp hạng: dấu, cắt, tỉ lệ
def _image_xh(d: Path, ten="XH.png", w=1242, h=2688):
    """Ảnh giả lập bảng xếp hạng đã đóng dấu như ranking.py làm."""
    from PIL import Image, ImageDraw
    from PIL.PngImagePlugin import PngInfo
    im = Image.new("RGB", (w, h), (255, 255, 255))
    dr = ImageDraw.Draw(im)
    for i in range(12):                      # 12 hàng bảng
        y = 120 + i * (h - 240) // 12
        dr.rectangle([60, y, w - 60, y + 60], fill=(240, 240, 245))
    dr.rectangle([60, h - 700, w - 60, h - 640], outline=(245, 197, 24), width=8)  # khoanh model
    meta = PngInfo()
    meta.add_text("provenance", "ranking_capture")
    meta.add_text("model", "GPT-5.2")
    p = d / ten
    im.save(p, "PNG", pnginfo=meta)
    return p


def test_save_crop_keep_mark_image_original():
    """_save_crop từng dựng PngInfo trắng → bản cắt mất dấu ranking_capture →
    is_ranking_image False → mất miễn trừ → carousel chặn đúng cái bìa bắt buộc."""
    import image_prepare as cb
    import image_rules_ethan as la
    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        goc = _image_xh(d)
        with Image.open(goc) as im:
            assert la.is_ranking_image(im), "ảnh gốc phải mang dấu"
            cb._save_crop(im, d / "cat.png", "4:5", cy=0.35)
        with Image.open(d / "cat.png") as ra:
            assert la.is_ranking_image(ra), "bản cắt MẤT dấu ranking_capture"
            assert la.read_crop_trace(ra) == (1242, 2688), "bản cắt phải vẫn có dấu crop_trace"
            assert ra.text.get("model") == "GPT-5.2" and "crop_ti_le" not in ra.text, ra.text


def test_check_ratio_domain_except_image_ranking():
    """Bảng desktop ra ~1.28, bảng mobile ra ~0.46 — cả hai đều ngoài dải
    4:5..1:1. Không miễn trừ thì Dre kẹt: cổng bắt dùng XH, carousel chặn XH."""
    import image_rules_ethan as la
    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        for w, h in ((1600, 1250), (1242, 2688)):
            p = _image_xh(d, f"xh_{w}x{h}.png", w, h)
            with Image.open(p) as im:
                assert la.check_aspect_ratio("bìa", p, w, h, img=im)[0] == [], f"chặn oan {w}x{h}"
        # ảnh thường ngoài dải VẪN phải bị chặn
        from PIL import Image as I
        q = d / "thuong.png"
        I.new("RGB", (1600, 1250), (200, 200, 200)).save(q)
        with I.open(q) as im:
            assert la.check_aspect_ratio("bìa", q, 1600, 1250, img=im)[0], "ảnh thường phải bị chặn"


def test_image_ranking_no_got_crop():
    """Hàng model đã khoanh có thể nằm dưới 55% dải chụp; cắt 4:5 cy=0.35 sẽ
    xoá mất nó. Ảnh xếp hạng phải giữ nguyên vẹn (a["ready_path"] = a["original_path"])."""
    # `classify` sang prepare/vision.py khi tach goi 09/09/2026 (audit A1).
    src = (ROOT / "prepare" / "vision.py").read_text(encoding="utf-8")
    khoi = src[src.index("    san = wd / state_paths.READY_DIR"):]
    khoi = khoi[:khoi.index("a[\"uses\"] = [\"body_chart_full_width")]
    assert 'if a.get("ranking"):' in khoi, "classify thiếu nhánh giữ nguyên ảnh xếp hạng"
    truoc_elif = khoi[:khoi.index("elif r <")]
    assert 'a["ready_path"] = a["original_path"]' in truoc_elif, "nhánh xếp hạng phải đặt san = goc, không cắt"


# ------------------------------------------------- Kite: ảnh chưa ai nhìn
def test_kite_no_force_use_image_not_yet_seen():
    """Vision tắt → mọi ảnh relevant=None. Ép lúc đó là đẩy quảng cáo/widget
    lên slide."""
    import kite_submit
    def hinh(lien_quan):
        return {"A1": {"id": "A1", "original_path": "/tmp/a.png", "w": 1200, "h": 800,
                       "ratio": 1.5, "kind": "chart", "relevant": lien_quan,
                       "domain": "x.com", "source": "x", "notes": []}}
    slides = [{"kind": "cover", "eyebrow": "X", "title": "T", "standfirst": "S"}] * 6
    for lq, phai_ep in ((True, True), (None, False)):
        m = {"images": list(hinh(lq).values()), "brand": "donniechublog", "title": "T",
             "draft_id": "d1", "article_text": "", "material": {}, "link": ""}
        _, loi, _ = kite_submit.resolve_spec({"slides": slides}, m, Path("/tmp"))
        co = any("BẮT BUỘC dùng ít nhất một" in x for x in loi)
        assert co == phai_ep, f"lien_quan={lq}: {'phải ép' if phai_ep else 'KHÔNG được ép'}"


# -------------------------------------- tách model / hạng từ tiêu đề xếp hạng
def test_extract_model_keep_count_version_raw():
    """Lookahead cũ chặn mọi chữ thường sau số → "GPT-6 tops the leaderboard"
    ra ['GPT'], engine khoanh hàng đầu tiên chứa "gpt" (có thể là GPT-5.2 mini
    hạng 23) rồi cổng ép dùng đúng tấm đó làm hero."""
    import ranking as xh
    for t, mong in [("GPT-6 tops the leaderboard", "GPT-6"),
                    ("Gemini 4 leo lên #1 bảng xếp hạng", "Gemini 4"),
                    ("Llama 5 vượt Qwen trên LiveBench", "Llama 5"),
                    ("Grok 5 takes first place", "Grok 5"),
                    ("GPT-5.2 tops the leaderboard", "GPT-5.2")]:
        ra = xh.extract_model(t)
        assert ra and ra[0] == mong, f"{t!r} → {ra[:2]}, mong {mong}"


def test_extract_model_no_hide_count_single_vi():
    """Số đi với đơn vị (điểm, USD, tỷ) không phải số phiên bản."""
    import ranking as xh
    assert xh.extract_model("GPT-6 Astra đạt 55 điểm trên bảng xếp hạng")[0] == "GPT-6 Astra"
    assert xh.extract_model("Claude Opus 4.5 giá 3 USD mỗi triệu token")[0] == "Claude Opus 4.5"


def test_extract_rank_pick_use_no_take_match_mark():
    """"Top 10" đầu tiêu đề là kích cỡ danh sách, không phải thứ hạng."""
    import ranking as xh
    for t, mong in [("Top 10 mô hình AI 2026: GPT-6 Astra dẫn đầu", 1),
                    ("Kimi K3 lọt top 5 SWE-bench, hạng 4", 4),
                    ("GPT-6 leo lên #1 bảng xếp hạng LMArena", 1),
                    ("Gemini 3 Pro hạng 3 trên Text Arena", 3),
                    ("Qwen3-Max lọt top 5 Intelligence Index", 5)]:
        md = xh.extract_model(t)
        assert xh.extract_rank(t, md[0] if md else "") == mong, t


def _image_capture(ra, hat, co=(1200, 900)):
    """Anh giong ANH CHUP that: bo cuc RIENG theo `hat` (khoi mau tho, khong
    phai mot gradient chung) cong nhieu pixel-to-pixel. Doi `co` khong lam doi
    noi dung — dung de dung ca "dung lai anh o co khac".

    Phai dung the: dHash doc bo xuong bo cuc, nen neu moi anh thu deu chung mot
    gradient thi chung cho cung mot hash va bai test tu no thanh vo nghia.
    """
    from PIL import Image
    trang_thai = hat * 7919 + 12345

    def ke():
        nonlocal trang_thai
        trang_thai = (1103515245 * trang_thai + 12345) % (1 << 31)
        return trang_thai

    tho = Image.new("RGB", (12, 9))
    tho.putdata([(ke() % 256, ke() % 256, ke() % 256) for _ in range(12 * 9)])
    im = tho.resize((300, 225), Image.Resampling.BILINEAR)
    px = im.load()
    for y in range(225):
        for x in range(300):
            n = ke() % 40 - 20
            r, g, b = px[x, y]
            px[x, y] = (max(0, min(255, r + n)), max(0, min(255, g + n)),
                        max(0, min(255, b + n)))
    im.resize(co, Image.Resampling.LANCZOS).save(ra)
    return ra


def test_image_ranking_domain_gate_use_again():
    """Hai bài về hai model cùng trong top một bảng chụp đúng dải hàng đó, chỉ
    khác khung khoanh → dHash coi là trùng. Cổng dùng-lại chặn ảnh XH, còn cổng
    "tin xếp hạng phải dùng XH" chặn mọi ảnh khác: hai lỗi loại trừ nhau."""
    import image_rules_ethan as la
    from PIL import Image, ImageDraw
    from PIL.PngImagePlugin import PngInfo
    with tempfile.TemporaryDirectory() as tmp, _so_tam(tmp) as d:

        def bang(ten, khoanh_y, dau=True):
            im = Image.new("RGB", (1200, 900), (255, 255, 255))
            dr = ImageDraw.Draw(im)
            for i in range(10):
                dr.rectangle([50, 60 + i * 80, 1150, 120 + i * 80], fill=(240, 240, 245))
            dr.rectangle([50, khoanh_y, 1150, khoanh_y + 60], outline=(245, 197, 24), width=6)
            m = PngInfo()
            if dau:
                m.add_text("provenance", "ranking_capture")
            p = d / ten
            im.save(p, "PNG", pnginfo=m)
            return p

        b1, b2 = bang("xh1.png", 140), bang("xh2.png", 620)
        # "Anh thuong" phai la anh CHUP that (co nhieu tu nhien), khong phai mot
        # tam bang nua: bang/chart la do hoa, va do hoa nay di theo nguong chat
        # rieng (xem test_two_chart_different_no_got_regard_is_duplicate).
        a1 = _image_capture(d / "a1.png", 0)
        a2 = _image_capture(d / "a2.png", 0, co=(1000, 750))   # cung anh, khac co
        la.record_used(b1, "bai1-designer-blog", "ethan", "https://a.com/1")
        la.record_used(a1, "bai1-designer-blog", "ethan", "https://a.com/1")
        # ảnh xếp hạng: bài sau dùng lại được
        assert la.check_not_reused("XH", b2, "bai2-designer-blog", "https://a.com/2")[0] == []
        # ảnh chụp dùng lại (đổi cỡ, khác byte): vẫn phải chặn
        assert la.check_not_reused("A1", a2, "bai2-designer-blog", "https://a.com/2")[0]


# ------------------------------------------------- watermark cua Bob (@handle)
def test_handle_bob_always_has_gate_and_label_all_two_kind_lock():
    """CT_BRAND la khoa CONTAINER ('blog'), card.BRAND khoa theo TEN brand
    ('donniechublog'). Truoc 06/09/2026 `handle_channel` tra thang gia tri tra cuu
    nen tren container blog no roi ve chinh chuoi 'blog': MOI anh Bob dong khung
    in watermark "blog" thay vi "@donniechublog"."""
    import bob_submit
    assert bob_submit.handle_channel("blog") == "@donniechublog"
    assert bob_submit.handle_channel("dcgr").startswith("@")
    # dua san ten brand (kieu khoa con lai) van phai ra dung
    assert bob_submit.handle_channel("donniechublog") == "@donniechublog"
    # da co "@" thi khong duoc nhan doi
    assert bob_submit.handle_channel("@donniechublog") == "@donniechublog"
    # brand la khong biet: van phai co "@", khong duoc tra chuoi tran
    assert bob_submit.handle_channel("khong_co_that").startswith("@")


# ------------------------------------------- tran 8 tin khong cat muc BAT BUOC
def test_ceiling_story_no_crop_item_required():
    """Muc BAT BUOC ton tu hom truoc duoc gan score_partial=0 nen diem toi da chi
    con 50 — LUON xep chot va truoc 06/09/2026 LUON bi tran 8 tin cat. Cat xong
    thi `required.check` lai them BAN TRONG (score=0, summary_vi rong, ghi chu
    "vai bo sot"): bao cao do oan cho vai la bo sot dung tin no vua cham ky, con
    vai viet bai thi mat sach tom tat."""
    import json
    import os
    import subprocess
    BRAND = "thu_tran_bb"
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        # State cua tien trinh con di vao TEMP, khong vao state/ that cua repo.
        # Truoc audit lượt 2 (E-r2-1): tien trinh con ton trong CT_STATE_DIR
        # nhung phan don o `finally` gõ cung ROOT/"state"/BRAND — dat bien la
        # FileNotFoundError, 17 test sau khong chay; khong dat bien thi test
        # tao/xoa state/thu_tran_bb/ TRONG repo. `kho` phai tinh tu CUNG bien.
        moi_truong = {**os.environ, "CT_BRAND": BRAND, "CT_STATE_DIR": str(t / "state")}
        kho = t / "state" / BRAND
        BB = "https://anthropic.com/claude-opus-46"
        # ghi danh sach bat buoc bang chinh tien trinh con (cung state dir)
        subprocess.run([sys.executable, "-c",
                        "import sys; sys.path.insert(0, %r); import required; "
                        "required.extra('finn', 'k1', 'Claude Opus 4.6', 'release', '', %r)"
                        % (str(ROOT), BB)],
                       env=moi_truong, check=True, capture_output=True)
        try:
            cands = {"candidates": [
                {"link": BB, "title": "Claude Opus 4.6 dat 82% SWE-bench Verified",
                 "source": "HN", "points": 10, "comments": 2, "via": "hn",
                 "score_partial": 0, "score_recency": 0, "score_spread": 0, "image_url": None}
            ] + [{"link": f"https://ex.com/{i}", "title": f"Tin thuong {i}", "source": "HN",
                  "points": 100 + i, "comments": 5, "via": "hn", "score_partial": 40,
                  "score_recency": 10, "score_spread": 5, "image_url": None}
                 for i in range(1, 10)]}
            (t / "c.json").write_text(json.dumps(cands), encoding="utf-8")
            picks = [{"k": 1, "category": "MODEL", "score_technical": 28,
                      "score_relevance": 19, "score_reason": "model lon",
                      "summary_vi": "Claude Opus 4.6 dat 82% SWE-bench Verified"}] + \
                    [{"k": i + 1, "category": "TOOL", "score_technical": 20,
                      "score_relevance": 15, "summary_vi": f"tin {i}"} for i in range(1, 10)]
            (t / "p.json").write_text(json.dumps(picks), encoding="utf-8")

            r = subprocess.run(
                [sys.executable, str(ROOT / "manifest_build.py"),
                 "--candidates", str(t / "c.json"), "--picks", str(t / "p.json"),
                 "--out", str(t / "m.json"), "--khong-xoa-bat-buoc"],
                env=moi_truong, capture_output=True, text=True, cwd=str(ROOT))
            assert r.returncode == 0, f"manifest_build hong: {r.stderr[-300:]}"

            items = json.loads((t / "m.json").read_text(encoding="utf-8"))["items"]
            muc = [i for i in items if "opus" in i["link"].lower()]
            assert muc, "muc BAT BUOC bi tran cat khoi manifest"
            assert muc[0]["score"] == 47, f"muc BAT BUOC bi thay ban trong: {muc[0]['score']}"
            assert muc[0]["summary_vi"], "muc BAT BUOC mat tom tat cua vai"
            # tran VAN con hieu luc voi tin thuong: 9 nop -> 8 giu
            thuong = [i for i in items if "opus" not in i["link"].lower()]
            assert len(thuong) == 8, f"tran 8 tin thuong khong con chay: {len(thuong)}"
        finally:
            for tep in kho.glob("*"):
                tep.unlink()
            kho.rmdir()

# ------------------------------------------------------------ the quote (card)
def _image_still(w, h, ra, dai_toi=None, sang=False):
    """Anh thu co VAN DAY (khong bi `_block_chart` bat nham la bieu do) va mot dai
    toi tuy chon. Kich thuoc tranh khit 4:5 vi cong `_block_standard_image` doi dau vet
    crop_ratio.py voi anh dung khit ti le."""
    from PIL import Image, ImageDraw
    goc = (250, 250, 250) if sang else (240, 240, 240)
    im = Image.new("RGB", (w, h), goc)
    d = ImageDraw.Draw(im)
    for x in range(0, w, 9 if sang else 7):
        v = (x * 29) % (40 if sang else 190)
        d.rectangle([x, 0, x + 5, h],
                    fill=(250 - v, 248 - v, 245 - v // 2) if sang
                    else (60 + v, 200 - v // 2, 120 + (v * 3) % 130))
    if not sang:
        for y in range(0, h, 11):
            v = (y * 53) % 160
            d.rectangle([0, y, w, y + 3], fill=(210 - v, 100 + v, 60 + v // 2))
    if dai_toi:
        d.rectangle([0, int(h * dai_toi[0]), w, int(h * dai_toi[1])], fill=(16, 18, 22))
    im.save(ra)
    return ra


def _use_card(src, ra, tmp):
    import card
    card.set_brand("donniechublog")
    card.build(str(src), "Mô hình mở đầu tiên vượt GPT-5 trên SWE-bench Verified",
               str(ra), handle="@donniechublog", ratio="4:5",
               attrib="Đọc bài đầy đủ tại donniechublog - Hacker News")
    return ra


def test_image_landscape_no_leak_path_seam_landscape():
    """Anh THAP hon khung (moi anh ngang) dan thang len lop nen se lo mot duong
    ke ngang tai `nat_h`: tren la anh sac, duoi la ban cover-blur cua MOT VUNG
    KHAC. Do that trước 06/09/2026: anh 3:2 tut 128 do sang trong MOT hang, 4:3
    tut 41 — dung cai "the doc ra HAI VUNG" Ong Chu bat nhieu lan. Cong 
    `_chan_anh_thap` khong do duoc viec nay (no chi chan tu ti le > 1.6)."""
    from PIL import Image, ImageStat
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        for w, h in ((1500, 1000), (1200, 900), (1600, 1000)):     # 3:2, 4:3, 16:10
            src = _image_still(w, h, t / f"g{w}.png", dai_toi=(0.62, 1.0))
            ra = _use_card(src, t / f"the{w}.png", t)
            im = Image.open(ra).convert("L")
            W_, H_ = im.size
            nat_h = round(h * W_ / w)
            # LOW-364: khung quote nam trong o vuong giua nen co the phu toi nat_h — net khung
            # khong phai duong ranh. Chi do phan cua so NAM TREN khung chu cua chinh the.
            import card
            top_text, _ = card.quote_text_top("Mô hình mở đầu tiên vượt GPT-5 trên SWE-bench Verified",
                                              "Đọc bài đầy đủ tại donniechublog - Hacker News",
                                              "@donniechublog", "4:5")
            hang = [ImageStat.Stat(im.crop((0, y, W_, y + 1))).mean[0]
                    for y in range(max(0, nat_h - 14), min(H_, nat_h + 15, top_text - 2))]
            if len(hang) < 2:
                continue
            buoc = max(abs(hang[i] - hang[i - 1]) for i in range(1, len(hang)))
            assert buoc < 8, (f"anh {w}x{h}: van lo duong ranh tai nat_h={nat_h}, "
                              f"buoc nhay {buoc:.1f} do sang trong mot hang")


def test_line_source_read_ok_on_bottom_card_bright():
    """Dong nguon ("Doc bai ... - <nguon>") duoc ve DUOI `frame_bottom`, tuc
    ngoai cai hop dung de chon mau chu cho quote. Anh co khoi chu toi nhung day
    the sang thi truoc 06/09/2026 no lay mau TRANG cua quote dat len nen sang:
    do that CR 1.04 — mat hoan toan, va mat luon dan nguon."""
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        # anh 1200x1560 (khong khit 4:5): sang toan bo, chi toi o giua — khoi
        # quote nam tren nen toi, day the van sang.
        src = _image_still(1200, 1560, t / "sang.png", dai_toi=(0.58, 0.90), sang=True)
        ra = _use_card(src, t / "the.png", t)
        im = Image.open(ra).convert("L")
        W_, H_ = im.size
        dai = im.crop((150, H_ - 105, W_ - 150, H_ - 25))     # dai chua dong nguon
        px = sorted(dai.getdata())
        chenh = px[len(px) // 2] - px[len(px) // 100]         # trung vi - 1%
        assert chenh > 120, (f"dong nguon khong noi tren nen: chenh sang chi {chenh} "
                             "(nen ~230, chu phai tach han ra)")

# ------------------------------------- required: manh ngan CO SO la thu phan biet
def test_match_keep_count_understand_version():
    """`ten` cua muc BAT BUOC hay co so hieu phien ban ngan: "R1", "K2", "o4",
    "4 Fast". Loc `len >= 3` vut sach chung, nen "DeepSeek R1" rut con
    ["deepseek"]: Nova dua tin "DeepSeek V4 ra mat" la match() tra True, check()
    tuong da dua nen khong tu them, roi delete() xoa han muc. Tin R1 mat VINH VIEN
    vi scan_models ghi `aa_reported` vao moc nen khong gieo lai.

    Chieu nguoc lai cung phai dung: manh ngan khong duoc so tran tren van ban da
    bo ky hieu, vi "4" don doc dinh vao moi con so ("tang 40% toc do")."""
    khong_khop = [
        ("DeepSeek R1", "DeepSeek V4 ra mat, re hon 10 lan"),
        ("o4-mini", "OpenAI ra mat o3-mini gia re"),
        ("Kimi K2", "Moonshot ra mat Kimi K3"),
        ("Grok 4 Fast", "xAI ra mat Grok 5 Fast, tang 40% toc do"),
        ("Gemini 3 Flash", "Google ra mat Gemini 2.5 Flash ban cap nhat"),
    ]
    phai_khop = [
        ("DeepSeek R1", "DeepSeek R1 ban cap nhat manh hon"),
        ("o4-mini", "OpenAI ra mat o4-mini gia re"),
        ("Kimi K2", "Moonshot ra mat Kimi K2 ban moi"),
        ("Grok 4 Fast", "xAI ra mat Grok 4 Fast"),
        ("Claude Opus 4.6", "Claude Opus 4.6 dat 82% SWE-bench Verified"),
    ]
    for ten, td in khong_khop:
        assert not bb.match({"name": ten}, {"title": td}), \
            f"muc {ten!r} bi coi la 'da dua' boi tin khac: {td!r} — se bi xoa oan"
    for ten, td in phai_khop:
        assert bb.match({"name": ten}, {"title": td}), \
            f"muc {ten!r} KHONG nhan ra chinh no trong {td!r} — se bi them trung"


# ------------------------------------------ nhan_vat: chuc danh va dau tieng Viet
_BAI = ("sam altman, ceo of openai, said the model is ready today. "
        "jensen huang of nvidia spoke at the event. "
        "pham nhat vuong opened the new plant in hai phong.")


def test_subject_has_function_list_or_mark_still_over():
    """Phep so cu (`ho = nv.split(",")[0]`, roi `ho not in chu_bai`) tach hau to
    CHI bang dau phay va so CHUOI CON chu khong so TU. Hai huong hong: chan oan
    ten kem chuc danh trong ngoac / sau gach, chan oan ten Viet CO DAU khi bai
    goc viet khong dau; va lot bua khi bai tinh co chua dung ky tu do o cho
    khac. Vai doc "Bo anh nay" roi bo dung tam anh dung."""
    for nv in ("Sam Altman (CEO OpenAI)", "Jensen Huang – Nvidia",
               "Sam Altman - CEO OpenAI", "Phạm Nhật Vượng", "Sam Altman"):
        assert nc._name_in_article(nv, _BAI), f"chan oan ten dung: {nv!r}"


def test_subject_still_catch_name_cover():
    """Cong nay sinh ra sau su co bia ten 05/09 (anh quan chuc G20, khai "Hock
    Tan"), noi long khong duoc lam mat no."""
    for nv in ("Hock Tan", "Tim Cook (CEO Apple)", "Nguyen Van Bia"):
        assert not nc._name_in_article(nv, _BAI), f"lot ten khong co trong bai: {nv!r}"


def test_description_logo_rank_within_article_no_got_block():
    """Cong chi no khi anh CO MAT NGUOI va vai DA khai ten — tuc nham dung vao
    anh chan dung/su kien, loai anh the hero can nhat. Tu tran "logo" trong bo
    tu khoa chan luon "CEO tren san khau, phia sau la logo OpenAI" — anh chuan
    nhat cua loai do, va la thu chinh prompt vision day rang LA lien quan."""
    anh_ok = {"A1": {"faces": 1, "description":"Sam Altman phát biểu trên sân khấu, "
                                        "phía sau là logo OpenAI"}}
    assert not nc.check_subject_named(anh_ok, ["A1"], "Sam Altman", _BAI, ""), \
        "chan oan anh su kien co logo hang trong bai"
    # nhung logo cua TO BAO thi van phai chan
    anh_bao = {"A1": {"faces": 1, "description":"Ảnh có watermark của hãng tin, "
                                         "không rõ người"}}
    assert nc.check_subject_named(anh_bao, ["A1"], "Sam Altman", _BAI, "")


# ------------------------------------------------------- scan_submit: dong [bo qua]
def test_scan_submit_in_all_sync_over():
    """[bo qua] = mat tron mot tin, loai nang nhat, ma truoc 06/09/2026 bo loc
    khong nhat no. Vera go nham k=9: tin "OpenAI IPO dinh gia 900 ty USD" bien
    mat sach, khong mot dong canh bao, rc=0, vai bao "da gui bao cao"."""
    import scan_submit
    ra = scan_submit.filter_warning(
        "[bo qua] muc 2: k=9 ngoai danh sach 1..5\n"
        "[canh bao] category khong hop le\n"
        "dong thuong khong lien quan\n"
        "[LOI] khong doc duoc tep\n")
    assert any("[bo qua]" in d for d in ra), "dong [bo qua] van bi nuot"
    assert any("[LOI]" in d for d in ra)
    assert not any("dong thuong" in d for d in ra)


# --------------------------------- manifest_build: khong ghi de bang manifest rong
def test_manifest_empty_no_overwrite():
    """Cong `if not items` truoc 06/09/2026 nam LOT TRONG khoi `if problems`, ma
    ca hai duong vao deu cho problems RONG: picks la `[]`, hoac dict sai khoa
    (script chi nhan "picks"/"items"). Khi ay script ghi manifest 0 muc, gui bao
    cao chi co tieu de + dong moi tra loi so ma khong co so nao, rc=0. Nang hon:
    scan_submit co dinh ten tep theo NGAY nen lan chay lai de thang len ban tot, va
    approve_pick chon manifest theo mtime — khong co duong lui."""
    import json
    import os
    import subprocess
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        moi_truong = {**os.environ, "CT_BRAND": "thu_rong_mb", "CT_STATE_DIR": str(t / "state")}
        kho = t / "state" / "thu_rong_mb"          # xem ghi chu o test_tran_tin (E-r2-1)
        (t / "c.json").write_text(json.dumps({"candidates": [
            {"link": "https://a.com/1", "title": "T", "source": "HN", "points": 9,
             "comments": 1, "via": "hn", "score_partial": 40, "score_recency": 5,
             "score_spread": 2, "image_url": None}]}), encoding="utf-8")
        try:
            for ten, noi_dung in (("rong", "[]"),
                                  ("sai khoa", '{"tin": [{"k": 1}]}')):
                (t / "p.json").write_text(noi_dung, encoding="utf-8")
                ra = t / "m.json"
                if ra.exists():
                    ra.unlink()
                r = subprocess.run(
                    [sys.executable, str(ROOT / "manifest_build.py"),
                     "--candidates", str(t / "c.json"), "--picks", str(t / "p.json"),
                     "--out", str(ra)],
                    env=moi_truong, capture_output=True, text=True, cwd=str(ROOT))
                assert r.returncode != 0, f"picks {ten}: van tra rc=0"
                assert not ra.exists(), f"picks {ten}: van ghi manifest rong de len ban tot"
        finally:
            if kho.exists():
                for tep in kho.glob("*"):
                    tep.unlink()
                kho.rmdir()

# --------------------------------------------- the quote tren nen nua sang nua toi
def _cr(a, b):
    """Ti so tuong phan WCAG giua hai mau (da tuyen tinh hoa gamma)."""
    def lin(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
    def L(m):
        return 0.2126 * lin(m[0]) + 0.7152 * lin(m[1]) + 0.0722 * lin(m[2])
    x, y = L(a), L(b)
    hi, lo = max(x, y), min(x, y)
    return (hi + 0.05) / (lo + 0.05)


def _image_two_tone(w, h, ra, ranh):
    """Nua TREN toi, nua DUOI sang, ranh o `ranh` (ti le chieu cao). Van day de
    khong bi `_block_chart` bat nham la bieu do."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), (250, 250, 250))
    d = ImageDraw.Draw(im)
    yr = int(h * ranh)
    for x in range(0, w, 7):
        v, u = (x * 37) % 150, (x * 29) % 40
        d.rectangle([x, 0, x + 4, yr], fill=(18 + v // 5, 20 + v // 4, 26 + v // 3))
        d.rectangle([x, yr, x + 4, h], fill=(250 - u, 248 - u, 245 - u // 2))
    for y in range(0, h, 13):
        v = (y * 53) % 90
        d.rectangle([0, y, w, y + 2],
                    fill=(14 + v // 3, 18 + v // 2, 30 + v // 2) if y < yr
                    else (252 - v // 4, 246 - v // 5, 240 - v // 6))
    im.save(ra)
    return ra


def _min_cr(mau):
    """Nguong tuong phan cua mot khuc chu: chu thuong cua dong (FG/BG) 4.0 nhu
    truoc; khuc TEN HANG to mau (LOW-344) theo WCAG AA chu lon — card.BRAND_MIN_CONTRAST_LARGE."""
    import card
    return 4.0 if tuple(mau[:3]) in (tuple(card.FG), tuple(card.BG)) else card.BRAND_MIN_CONTRAST_LARGE


def _line_left(dong):
    """y -> x trai nhat cua dong. Tu LOW-344 mot dong quote ve theo TUNG KHUC (ten
    hang to rieng), khong con mot lan `d.text` cho ca dong; dai nen van do tu mep
    trai dong, nhu truoc."""
    trai: dict = {}
    for (x, y), _tx, _mau in dong:
        trai[y] = min(x, trai.get(y, x))
    return trai


def test_new_line_quote_read_ok_when_background_two_tone():
    """Ranh sang/toi NGANG cat qua khoi chu la ca rat thuong (anh chup co hero
    toi tren, bang trang duoi; anh ghep doc hai tam khac tone). Truoc 06/09/2026
    mau chu do MOT mean cho CA KHOI: trung binh 136 -> chon chu TRANG
    trong khi nua duoi khoi la nen 243-250, may dong cuoi la trang tren trang.
    Loi DOI XUNG o chieu kia: trung binh 142 -> chu toi, nua tren thanh
    den-tren-den. Do tung dai dong thi moi dong deu phai doc duoc."""
    from PIL import Image, ImageDraw
    import card
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        card.set_brand("donniechublog")
        ve_goc = ImageDraw.ImageDraw.text
        da_ve = []

        def ve_ghi(self, xy, text, *a, **kw):
            da_ve.append((xy, text, kw.get("fill")))
            return ve_goc(self, xy, text, *a, **kw)

        quote = "Mô hình mở đầu tiên vượt GPT-5 trên SWE-bench Verified"
        # 0.756: ranh roi GIUA khoi chu. 0.60: ca khoi tren nen sang.
        for ranh in (0.756, 0.60, 0.95):
            da_ve.clear()
            src = _image_two_tone(1200, 1560, t / f"g{int(ranh*1000)}.png", ranh)
            ra = t / f"the{int(ranh*1000)}.png"
            ImageDraw.ImageDraw.text = ve_ghi
            try:
                card.build(str(src), quote, str(ra), handle="@donniechublog",
                           ratio="4:5", attrib="Đọc bài đầy đủ tại donniechublog")
            finally:
                ImageDraw.ImageDraw.text = ve_goc
            im = Image.open(ra).convert("RGB")
            dong = [(xy, tx, f) for xy, tx, f in da_ve if tx and tx in quote and f]
            x_dong = _line_left(dong)
            assert len(dong) >= 3, f"khong ghi nhan du dong quote ({len(dong)})"
            for (x, y), tx, mau in dong:
                # nen = trung vi cua dai chua dong (chu chi chiem thieu so pixel)
                dai = im.crop((int(x_dong[y]), int(y) + 20, im.width - int(x_dong[y]), int(y) + 95))
                px = sorted(dai.convert("L").getdata())
                nen = px[len(px) // 2]
                assert _cr(mau, (nen,) * 3) >= _min_cr(mau), (
                    f"ranh {ranh}: dong {tx[:28]!r} mau {mau} tren nen L={nen} "
                    f"chi CR {_cr(mau, (nen,) * 3):.2f}")


def _image_network_bright_read(w, h, ra, x0_ti=0.42, x1_ti=0.72):
    """Nen TOI, mot mang SANG DOC (ao trang, cua so, den san khau) chiem mot
    phan be ngang — mang nay cat qua MOI dai dong, khong phai ranh ngang."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), (22, 24, 30))
    d = ImageDraw.Draw(im)
    for x in range(0, w, 7):
        v = (x * 37) % 90
        d.rectangle([x, 0, x + 4, h], fill=(16 + v // 6, 20 + v // 5, 28 + v // 4))
    for y in range(0, h, 13):
        v = (y * 53) % 70
        d.rectangle([0, y, w, y + 2], fill=(14 + v // 4, 18 + v // 3, 26 + v // 3))
    bx0, bx1 = int(w * x0_ti), int(w * x1_ti)
    for y in range(0, h, 11):
        u = (y * 31) % 30
        d.rectangle([bx0, y, bx1, y + 9], fill=(250 - u, 249 - u, 246 - u // 2))
    im.save(ra)
    return ra


def test_new_line_quote_read_ok_when_has_network_bright_read():
    """Nua con lai cua bai toan tren: mang sang/toi nam GON TRONG mot dai dong.

    Do tung dai (test tren) chi xu duoc ranh NGANG. Mang sang DOC thi trung binh
    ca dai van thien dung phe — mean 95 chon chu trang — nhung stddev 84 va nen
    cuc bo tai mang sang la 217: CR 1.19, mat chu dung chuong do. `_can_board_line`
    sinh ra cho ca nay, nhung toi 07/09/2026 moi chi noi vao kieu `tran`; kieu
    `quote` con dung `_bright_region` truc tiep.

    Cham bang CUA SO TRUOT doc dai, KHONG phai median ca dai: median cua chinh ca
    nay van cho CR 5.57 nen gate cu bao xanh trong khi chu da chim."""
    from PIL import Image, ImageDraw
    import card
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        card.set_brand("donniechublog")
        ve_goc = ImageDraw.ImageDraw.text
        da_ve = []

        def ve_ghi(self, xy, text, *a, **kw):
            da_ve.append((xy, text, kw.get("fill")))
            return ve_goc(self, xy, text, *a, **kw)

        quote = "Mô hình mở đầu tiên vượt GPT-5 trên SWE-bench Verified"
        for x0_ti, x1_ti in ((0.42, 0.72), (0.0, 0.35), (0.6, 1.0)):
            da_ve.clear()
            src = _image_network_bright_read(1200, 1560, t / f"g{int(x0_ti*100)}.png",
                                     x0_ti, x1_ti)
            ra = t / f"the{int(x0_ti*100)}.png"
            ImageDraw.ImageDraw.text = ve_ghi
            try:
                card.build(str(src), quote, str(ra), handle="@donniechublog",
                           ratio="4:5", attrib="Đọc bài đầy đủ tại donniechublog")
            finally:
                ImageDraw.ImageDraw.text = ve_goc
            im = Image.open(ra).convert("RGB")
            dong = [(xy, tx, f) for xy, tx, f in da_ve if tx and tx in quote and f]
            x_dong = _line_left(dong)
            assert len(dong) >= 3, f"khong ghi nhan du dong quote ({len(dong)})"
            for (x, y), tx, mau in dong:
                dai = im.crop((int(x_dong[y]), int(y) + 20, im.width - int(x_dong[y]), int(y) + 95))
                for wx in range(0, dai.width - 90, 30):
                    o = dai.crop((wx, 0, wx + 90, dai.height)).convert("L")
                    px = sorted(o.getdata())
                    nen = px[len(px) // 2]
                    assert _cr(mau, (nen,) * 3) >= _min_cr(mau), (
                        f"mang sang {x0_ti}..{x1_ti}: dong {tx[:28]!r} mau {mau} "
                        f"tren nen cuc bo L={nen} (x={int(x)+wx}) chi CR "
                        f"{_cr(mau, (nen,) * 3):.2f}")


def test_net_frame_and_mark_bracket_no_sink_on_background_bright():
    """Net khung + hai dau " 210px la vat nhan dien cua kieu pull-quote. Truoc
    06/09/2026 net khung la CYAN CUNG, khong nhanh nao doi: tren anh nen sang,
    CYAN cua dcgr (trang thuan) cho CR 1.04 — bien mat sach; cua donniechublog
    cho 1.88, nhat han. Dau ngoac con te hon: `_enough_bright` keo mau hang SANG THEM,
    dung luat danh cho nen toi, tuc sai chieu."""
    import card
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        for brand in ("donniechublog", "dcgr"):
            card.set_brand(brand)
            goc = card._quote_frame
            ghi = {}

            # `bat` doc `ghi`/`goc` cua lan lap hien tai (B023). Vo hai: no duoc
            # gan vao `card._quote_frame` va go ra trong `finally` cung lan lap,
            # nen khong bao gio chay voi `ghi`/`goc` cua brand khac.
            def bat(d, x0, y0, x1, y1, line_color, mark_color, lw=5):
                ghi["net"], ghi["mark"] = line_color, mark_color  # noqa: B023
                return goc(d, x0, y0, x1, y1, line_color, mark_color, lw)  # noqa: B023

            card._quote_frame = bat
            try:
                # ranh 0.60: ca khoi chu nam tren nen SANG
                src = _image_two_tone(1200, 1560, t / f"s_{brand}.png", 0.60)
                card.build(str(src), "Mô hình mở đầu tiên vượt GPT-5 trên SWE-bench",
                           str(t / f"the_{brand}.png"), handle="@donniechublog",
                           ratio="4:5", attrib="Đọc bài đầy đủ tại donniechublog")
            finally:
                card._quote_frame = goc
            for ten in ("net", "mark"):
                cr = _cr(ghi[ten], (250, 250, 250))
                assert cr >= 3.0, (f"{brand}: {ten} khung {ghi[ten]} tren nen sang "
                                   f"chi CR {cr:.2f} — chim")
        card.set_brand("donniechublog")

# ------------------------------------------- so "anh da dung": nguong theo loai
def _chart(ra, gia_tri, mau=(40, 90, 200)):
    """Bieu do cot nen trang — do hoa vector, khong co nhieu tu nhien."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (1200, 800), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rectangle([80, 60, 1120, 700], outline=(210, 210, 210), width=3)
    rong = 1000 // (len(gia_tri) * 2)
    for i, v in enumerate(gia_tri):
        x = 100 + i * rong * 2
        d.rectangle([x, 700 - int(620 * v), x + rong, 700], fill=mau)
    im.save(ra)
    return ra


def test_two_chart_different_no_got_regard_is_duplicate():
    """dHash 8x8 doc BO XUONG BO CUC. Anh chup that co nhieu tu nhien nen hai
    tam khac nhau cach hang chuc bit, nhung do hoa vector thi khong: hai bieu do
    cot HOAN TOAN khac so lieu, mien cung dang di xuong, chi cach 4-5 bit. Voi
    nguong chung 6, chart THAT cua bai — bang chung manh nhat — bi bao "TRUNG
    anh da dung", vai lang le doi sang anh minh hoa yeu hon."""
    import image_rules_ethan as la
    with tempfile.TemporaryDirectory() as tmp, _so_tam(tmp) as d:
        c1 = _chart(d / "c1.png", [0.90, 0.82, 0.75, 0.60, 0.50])
        c2 = _chart(d / "c2.png", [0.88, 0.80, 0.70, 0.62, 0.45], mau=(200, 80, 40))
        la.record_used(c1, "baiA", "ethan", "https://a.com/1")
        loi, _ = la.check_not_reused("A1", c2, "baiB", "https://a.com/2")
        assert not loi, f"hai chart khac so lieu bi coi la trung: {loi}"
        # nhung DUNG LAI y het tam do thi van phai chan
        import shutil
        c1b = d / "c1b.png"
        shutil.copyfile(c1, c1b)
        assert la.check_not_reused("A1", c1b, "baiB", "https://a.com/2")[0], \
            "dung lai y het mot chart ma khong chan"


def test_drop_article_then_go_image_block_count():
    """So duoc ghi o buoc GUI album, tuc TRUOC khi Ong Chu bam nut. Bam "Bo han
    tin" hay "Lam lai" thi anh KHONG bao gio len kenh, nhung truoc 06/09/2026
    chung van nam trong so va chan moi bai khac suot 14 ngay — ma thong bao chan
    chi noi ten bai va cham, KHONG noi bai do da bi bo."""
    import image_rules_ethan as la
    import image_provenance
    with tempfile.TemporaryDirectory() as tmp, _so_tam(tmp) as d:
        a1 = _image_capture(d / "x1.png", 5)
        a2 = _image_capture(d / "x2.png", 5, co=(1000, 750))     # cung anh, khac co
        la.record_used(a1, "bai-bi-bo", "ethan", "https://a.com/1")
        la.record_used(_image_capture(d / "y1.png", 9), "bai-khac", "ethan",
                       "https://a.com/9")
        assert la.check_not_reused("A1", a2, "bai-sau", "https://a.com/2")[0], \
            "chua go thi phai con chan (neu khong, test nay vo nghia)"
        assert image_provenance.remove_used_for_draft("bai-bi-bo") == 1
        assert not la.check_not_reused("A1", a2, "bai-sau", "https://a.com/2")[0], \
            "da bo bai ma anh van bi khoa"
        # khong duoc go nham dong cua bai khac
        assert image_provenance.remove_used_for_draft("bai-khong-co") == 0
        assert len((d / "s.jsonl").read_text(encoding="utf-8").strip().splitlines()) == 1

# ------------------------------------------------ bars: so kieu Viet, va cong text
def test_value_bars_read_use_touch_rank_thousand():
    """Kite viet "1.200" (mot nghin hai tram) — dung kieu Viet, dung cai docstring
    noi la chap nhan. Truoc 06/09/2026 `_value` chi doi ',' thanh '.', nen
    float("1.200") = 1.2: cot "1.200 tac vu" ve rong 0.1% con cot "900" ve rong
    100%, bieu do noi NGUOC han so lieu ma chu tren cot van ghi dung."""
    import render_edu as re_
    assert re_._value("1.200") == 1200.0
    assert re_._value("12.345") == 12345.0
    assert re_._value("1.200,50") == 1200.5      # cham nghin + phay thap phan
    assert re_._value("2,75") == 2.75            # phay thap phan kieu Viet
    assert re_._value("2.75") == 2.75            # cham thap phan kieu Anh
    assert re_._value(900) == 900.0
    vals = [re_._value("1.200"), re_._value(900)]
    ti_le = [round(v / max(vals) * 100, 1) for v in vals]
    assert ti_le == [100.0, 75.0], f"ti le cot sai: {ti_le}"


def test_gate_bars_catch_text_offset_value():
    """`text` la thu NGUOI DOC nhin thay tren cot, `value` la thu quyet dinh
    CHIEU DAI cot. Lech nhau thi bieu do noi mot dang, chu noi mot dang — va
    truoc day khong cong nao doi chieu hai cai."""
    import render_edu as re_
    def bars(v, t):
        return [{"kind": "cover", "eyebrow": "e", "title": "t"}] + [
            {"kind": "bars", "eyebrow": "e", "title": "t", "caption": "via HN",
             "bars": [{"label": "Truoc", "value": v, "text": t},
                      {"label": "Sau", "value": 900, "text": "900 tác vụ"}]}]
    loi = [d for d in re_.gate_slides(bars(1.2, "1.200 tác vụ"), False) if "cot 1" in d]
    assert loi, "khong bat duoc text 1.200 di voi value 1.2"
    assert not [d for d in re_.gate_slides(bars("1.200", "1.200 tác vụ"), False)
                if "cot 1" in d], "bao nham khi text va value khop"


# ------------------------------------------- get_source: giu dinh dang goc twimg
def test_twimg_keep_format_image_original():
    """`name=orig` chi duoc phuc vu o DUNG dinh dang anh duoc luu. Ep
    `format=jpg` cho post co anh PNG (anh chup man hinh meme — noi dung chinh
    cua kenh) thi CDN tra 404 chu khong tra ban JPEG. 404 bi vong ung vien nuot,
    tep bi xoa, roi page_fallback lay og:image = THE render 1200x630 — Bob dong
    khung cai the do, exit 0, khong canh bao. Dung cai loi ma fa36904 sinh ham
    nay de sua."""
    import importlib.util
    duong = ROOT / "hermes/skills/url-mascot-frame/scripts/get_source.py"
    spec = importlib.util.spec_from_file_location("get_source_thu", duong)
    gs = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gs)
    trang = ('<img src="https://pbs.twimg.com/media/GxAbc123DEF.png:large">'
             '<img src="https://pbs.twimg.com/media/GwPlain777AA.jpg">')

    class _R:
        def read(self):
            return trang.encode()
        def __enter__(self):
            return self
        def __exit__(self, *a):
            return False

    goc = gs.urllib.request.urlopen
    gs.urllib.request.urlopen = lambda *a, **k: _R()
    try:
        ra = gs.twimg_from_page("https://x.com/x/status/1")
    finally:
        gs.urllib.request.urlopen = goc
    png = [u for u in ra if "GxAbc123DEF" in u]
    assert png and "format=png" in png[0], f"anh PNG khong duoc thu bang PNG truoc: {png}"
    jpg = [u for u in ra if "GwPlain777AA" in u]
    assert jpg and "format=jpg" in jpg[0], f"anh JPG khong duoc thu bang JPG truoc: {jpg}"


# ------------------------------------------------------ Bob: mood tu luot nhin
def test_bob_use_result_seen_for_pick_mood():
    """main() goi description_image, IN mo ta, roi dong khung bang `a.emoji` va gui —
    tat ca trong mot lan chay. Truoc 06/09/2026 bien `mo_ta` khong bao gio cham
    toi mood, ma Bob chi thay stdout SAU KHI tien trinh thoat (luc anh da len
    kenh) va SOUL cam chay lenh thu hai. Ket qua: mood DONG CUNG o mac dinh,
    tinh nang khop tam trang chet lang le, van ton mot luot vision moi lan."""
    import bob_submit
    import image_prepare as cb
    da_dong = {}

    def khung_gia(src, ra, emoji, handle):
        da_dong["emoji"] = emoji
        Path(ra).write_bytes(b"x")

    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        (t / "goc.png").write_bytes(b"anh gia")
        goc_lay, goc_khung, goc_mo_ta = bob_submit.take_image, bob_submit.line_frame, cb.description_image
        bob_submit.take_image = lambda nguon, ra: (Path(ra).write_bytes(b"x"), "thu")[1]
        bob_submit.line_frame = khung_gia
        try:
            # (1) vision doc ra mood -> phai dung mood do
            cb.description_image = lambda *a, **k: ("mot con robot dang go phim", None, "MOOD: 🤖")
            bob_submit.main_thu = None
            sys.argv = ["bob_submit.py", str(t / "goc.png"), "--khong-gui",
                        "--out", str(t / "ra1.png")]
            bob_submit.main()
            assert da_dong["emoji"] == "🤖", f"khong dung mood vision chon: {da_dong}"

            # (2) Ong Chu truyen --emoji -> luon thang
            sys.argv = ["bob_submit.py", str(t / "goc.png"), "--khong-gui",
                        "--emoji", "😂", "--out", str(t / "ra2.png")]
            bob_submit.main()
            assert da_dong["emoji"] == "😂", f"--emoji bi ghi de: {da_dong}"

            # (3) vision hong / khong doc ra mood -> mac dinh an toan
            cb.description_image = lambda *a, **k: ("", None, "")
            sys.argv = ["bob_submit.py", str(t / "goc.png"), "--khong-gui",
                        "--out", str(t / "ra3.png")]
            bob_submit.main()
            assert da_dong["emoji"] == bob_submit.EMOJI_DEFAULT, \
                f"khong roi ve mac dinh an toan: {da_dong}"
        finally:
            bob_submit.take_image, bob_submit.line_frame, cb.description_image = goc_lay, goc_khung, goc_mo_ta

# ------------------------------------------- vong [LOI]: dem trong CODE, khong phai chu
def test_round_error_has_buffer_and_reset_when_error_change():
    """"Toi da 2 lan sua [LOI]" truoc 06/09/2026 chi la CHU trong task body —
    khong dong code nao dem. Ghep voi cong phi tat dinh (vision doi ket qua
    giua hai lan chay), vai co the lap toi khi het ngan sach tool call ma khong
    ai thay gi ngoai mot task treo."""
    with tempfile.TemporaryDirectory() as td:
        wd = Path(td)
        bo_loi = ["thieu anh A2", "slide 3 tran chu"]
        assert nc.count_round_error(wd, bo_loi, "lenh") == 1
        assert nc.count_round_error(wd, bo_loi, "lenh") == 1
        assert nc.count_round_error(wd, bo_loi, "lenh") == 2, "lan thu 3 phai bao DUNG"
        # bo loi DOI = vai da sua duoc mot thu -> cho di tiep
        assert nc.count_round_error(wd, ["loi khac han"], "lenh") == 1


# ------------------------------------------------ Itachi: vung quen, tran hop, mau
def test_itachi_color_wrong_form_no_make_crash_copy_about():
    """`tuple(color)` voi color tu spec nem TypeError GIUA buoi ve — mat ca
    slide, vai chi thay traceback."""
    import itachi_submit as it
    assert it._color([12, 34, 56]) == (12, 34, 56)
    for xau in ("xanh", [1, 2], [300, 0, 0], None, {}, [1, 2, "x"]):
        assert it._color(xau) == (20, 20, 20), f"khong do duoc dang xau: {xau!r}"


def test_itachi_catch_text_ceiling_box():
    """`_about_block` co lai co chu toi HAS_MIN roi VE BAT KE: vong while thoat vi
    `size > HAS_MIN` chu khong phai vi chu da vua. Cau dich dai gap doi cau goc
    thi tran de len anh ben duoi, khong cong nao bao."""
    from PIL import Image, ImageDraw
    import itachi_submit as it
    d = ImageDraw.Draw(Image.new("RGB", (1200, 1200)))
    dai = ("Một câu dịch dài gấp nhiều lần câu gốc, kể lể đủ thứ chi tiết mà hộp "
           "gốc không bao giờ chứa nổi dù chữ đã nhỏ hết cỡ.")
    assert it._ceiling_box(d, dai, 400, 40, "regular") > 0, "khong bat duoc chu tran"
    assert it._ceiling_box(d, "Ngắn", 400, 60, "regular") == 0, "bao nham chu vua hop"


# ------------------------------------------------------ Cape: dan y co duoc nhac
def test_teaser_mention_item_guide_y_got_drop():
    """SOUL bat Cape "nhac du muc dan y" nhung khong cong nao doi chieu —
    teaser dai dung so tu ma bo han mot nua bai van qua sach. So theo TU
    NGUYEN VEN: tieng Viet phan lon la am tiet 2-4 ky tu nen so chuoi con thi
    "tre" trung vao "truoc", cong se im lang."""
    import teaser_assemble as ta
    dan_y = [{"level": "h2", "text": "Chi phí mỗi task"},
             {"level": "h2", "text": "Độ trễ khi tải cao"},
             {"level": "h3", "text": "mục h3 không xét"}]
    doan = ["Con số chi phí gây bất ngờ: 2,75 USD mỗi task, rẻ hơn bản trước.",
            "Đổi lại là chất lượng giữ nguyên trên bộ đo nội bộ."]
    assert ta._item_no_ok_mention(dan_y, doan) == ["Độ trễ khi tải cao"]
    du = doan + ["Độ trễ khi tải cao vẫn nằm trong ngưỡng chịu được."]
    assert ta._item_no_ok_mention(dan_y, du) == []
    assert ta._item_no_ok_mention(None, doan) == []

# ------------------------------------------------- duong bao loi cua miles_submit
def test_miles_submit_report_error_see_vi_no():
    """Caption truot cong phai ra dong "Sua roi chay lai" + ma thoat 1.

    Bay 06/09/2026 (commit 519adb2): `count_round_error` duoc goi qua `nc` o dong 79
    trong khi `import submit_common as nc` nam o dong 109 CUNG ham, nen Python coi
    `nc` la bien cuc bo va nem UnboundLocalError. Duong di thuong gap nhat cua
    Miles ket thuc bang traceback: vai khong thay tran vong, khong thay lenh
    chay lai. Ca 82 test cu van xanh vi khong test nao cham duong nay.
    """
    import io
    import contextlib as _ctx
    import miles_submit as mn
    with tempfile.TemporaryDirectory() as tmp:
        wd = Path(tmp) / "wd"
        wd.mkdir()
        # caption vuot tran 2200 ky tu -> chac chan co [LOI]
        (wd / "caption.txt").write_text("Câu này dài. " * 200, encoding="utf-8")
        cu_meta, cu_wd, cu_argv = mn.cb.load_meta, mn.cb.workdir, sys.argv
        mn.cb.load_meta = lambda _id: {"brand": "donniechublog"}
        mn.cb.workdir = lambda _state, _id: wd
        sys.argv = ["miles_submit.py", "tin-thu-writer-blog"]
        try:
            buf = io.StringIO()
            with _ctx.redirect_stdout(buf):
                ma = mn.main()
        finally:
            mn.cb.load_meta, mn.cb.workdir, sys.argv = cu_meta, cu_wd, cu_argv
        ra = buf.getvalue()
        assert ma == 1, f"ma thoat {ma}, mong doi 1 (con sua duoc)"
        assert "[LOI]" in ra, ra[-400:]
        assert "Sua roi chay lai" in ra, "vai khong duoc bao cach chay lai:\n" + ra[-400:]
        assert (wd / state_paths.SUBMIT_COUNT_FILE).exists(), "khong ghi bo dem vong loi"


def test_count_used_ok_return_again_after_each_test_on():
    """Chot cai bay monkeypatch: sau moi test o tren, `_used_images_log()` phai tro
    ve duong THAT chu khong phai mot TemporaryDirectory da bi xoa — neu khong,
    `check_not_reused` tra rong vo dieu kien va moi cong "khong dung lai anh" trong
    cac test sau deu chet im."""
    import image_provenance as la
    p = la._used_images_log()
    assert p.name == "used_images.jsonl", p
    assert p.parent.exists(), f"so tro vao thu muc khong ton tai: {p}"


# --------------------------------------------------- trang thai (buoc 4)
def test_redo_only_apply_when_boss_really_press():
    """`previous_submission.json` duoc ghi o MOI lan gui va approve_post khong bao gio xoa, nen
    "co da_dung" khong dong nghia "Ong Chu bam Lam lai". Ban cu bat vai doi bia
    o moi lan chay lai, vai doi that, roi gui BO THU HAI kem nut Duyet thu hai.
    Moc dung la `remakes` trong img.json."""
    import submit_common as nc2
    cu = nc2.count_of_redo
    try:
        # Ong Chu chua bam lan nao; da_dung ghi luc remakes=0 -> chay lai KHONG bi bat
        nc2.count_of_redo = lambda _id: 0
        da_dung = {"cover_image": "A1", "hook": "Hook cu", "remakes": 0}
        assert nc2.check_redo_reused(da_dung, "bìa", "A1", "Hook cu",
                                khoa_anh="cover_image", draft_id="x") == []
        # Ong Chu bam Lam lai (remakes 0 -> 1): giu nguyen bia+hook thi PHAI bat
        nc2.count_of_redo = lambda _id: 1
        loi = nc2.check_redo_reused(da_dung, "bìa", "A1", "Hook cu",
                               khoa_anh="cover_image", draft_id="x")
        assert len(loi) == 2, loi
        # doi ca hai thi qua
        assert nc2.check_redo_reused(da_dung, "bìa", "A7", "Hook moi",
                                khoa_anh="cover_image", draft_id="x") == []
    finally:
        nc2.count_of_redo = cu


def test_only_ranking_choice_one_image_ranking():
    """`only_ranking_choice` chỉ trả về mã ảnh khi bài LÀ tin xếp hạng CHỤP được
    bảng và CHỈ CÓ ĐÚNG MỘT ảnh xếp hạng — None nếu không phải tin xếp hạng,
    chưa chụp được bảng, không có, hoặc có từ hai ảnh xếp hạng trở lên (còn
    đường khác để đổi, không cần miễn cổng làm lại)."""
    import submit_common as nc2
    m_mot = {"is_ranking_story": True, "ranking": {"kind": "table"},
              "images": [{"id": "XH", "ranking": True}, {"id": "A2", "ranking": False}]}
    assert nc2.only_ranking_choice(m_mot) == "XH"

    m_hai = {"is_ranking_story": True, "ranking": {"kind": "table"},
              "images": [{"id": "XH", "ranking": True}, {"id": "XH2", "ranking": True}]}
    assert nc2.only_ranking_choice(m_hai) is None

    m_khong_chup = {"is_ranking_story": True, "ranking": {"kind": "card"},
                     "images": [{"id": "XH", "ranking": True}]}
    assert nc2.only_ranking_choice(m_khong_chup) is None

    m_khong_xep_hang = {"is_ranking_story": False, "images": [{"id": "XH", "ranking": True}]}
    assert nc2.only_ranking_choice(m_khong_xep_hang) is None


def test_redo_no_end_when_only_has_one_image_ranking():
    """LOW-146: needs_ranking_image bắt bìa PHẢI là ảnh xếp hạng; check_redo_reused
    cấm bìa trùng lần trước. Khi bộ ảnh chỉ có ĐÚNG MỘT ảnh xếp hạng và nó đã là
    bìa lần trước, hai cổng khoá nhau — bộ ảnh không còn đường nộp hợp lệ dù sửa
    gì khác. `anh_bat_buoc=True` (tính từ only_ranking_choice) phải mở khoá phần
    so ảnh, nhưng vẫn giữ cổng hook — vai vẫn phải đổi cách diễn đạt."""
    import submit_common as nc2
    cu = nc2.count_of_redo
    try:
        nc2.count_of_redo = lambda _id: 1                # Ong Chu THAT SU bam lam lai
        da_dung = {"cover_image": "XH", "hook": "Hook cu", "remakes": 0}
        # khong bat_buoc: giu nguyen bia XH bi bat nhu binh thuong
        loi_cu = nc2.check_redo_reused(da_dung, "bìa", "XH", "Hook moi",
                                  khoa_anh="cover_image", draft_id="x")
        assert len(loi_cu) == 1 and "vẫn là" in loi_cu[0], loi_cu
        # bat_buoc=True (chi co 1 anh xep hang, khong the doi): bo qua phan so anh,
        # nhung hook giong het van bi bat
        assert nc2.check_redo_reused(da_dung, "bìa", "XH", "Hook moi",
                                khoa_anh="cover_image", draft_id="x", anh_bat_buoc=True) == []
        loi_hook = nc2.check_redo_reused(da_dung, "bìa", "XH", "Hook cu",
                                    khoa_anh="cover_image", draft_id="x", anh_bat_buoc=True)
        assert len(loi_hook) == 1 and "hook" in loi_hook[0].lower(), loi_hook
    finally:
        nc2.count_of_redo = cu


def test_album_already_len_count_by_file_and_time():
    """Ban cu hoi `if draft_id in dong` tren 400 dong cuoi MOI tep .jsonl, khong
    nhin moc thoi gian: album tu hom qua lam nhanh cuu hieu nham la "vua len",
    ghi so voi bo anh CHUA gui roi in "ĐỪNG chạy lại" — album moi khong bao gio
    len va anh bi khoa 14 ngay."""
    import json as _j
    import time as _t
    import submit_common as nc2
    import env_load as el
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        cu = el.state_dir
        el.state_dir = lambda: d
        try:
            sent = d / "telegram_sent"
            sent.mkdir()
            gio = int(_t.time())
            with (sent / "dre.jsonl").open("w", encoding="utf-8") as fh:
                fh.write(_j.dumps({"ts": gio - 86400, "files": ["/x/bai.png"]}) + "\n")
                fh.write(_j.dumps({"ts": gio - 60, "files": ["/x/moi.png"]}) + "\n")
            # bo vua gui 1 phut truoc -> True
            assert nc2._recently_posted("dre", ["/x/moi.png"]) is True
            # CUNG bo do nhung tu hom qua -> False (day la bug cu)
            assert nc2._recently_posted("dre", ["/x/bai.png"]) is False
            # vai khac khong duoc lay nham
            assert nc2._recently_posted("ethan", ["/x/moi.png"]) is False
            # tien to khong duoc coi la trung ("gpt-5" ⊂ "gpt-5-codex")
            assert nc2._recently_posted("dre", ["/x/moi_2.png"]) is False
        finally:
            el.state_dir = cu


def test_publish_no_form_album_attempt_two():
    """Caption dai: album len truoc, tin chu gui sau. Tin chu hong -> bai thanh
    publish_failed -> Ong Chu bam ✅ lai -> ban cu dang album LAN HAI."""
    import json as _j
    import approve_post as db
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        cu_drafts, cu_gui = db.DRAFTS, db._send_text
        db.DRAFTS = d
        goi = []
        db._send_text = lambda *a, **k: goi.append("chu") or {"ok": True}
        try:
            (d / "b.json").write_text(_j.dumps({
                "caption": "x" * (db.CAPTION_LIMIT + 10),
                "images": ["/khong-ton-tai.png"],
                "channel_album_mid": 4242}), encoding="utf-8")
            res = db.publish("tok", "-100", "b")
            assert res.get("ok"), res
            assert goi == ["chu"], f"phai gui MOI tin chu, khong gui lai album: {goi}"
        finally:
            db.DRAFTS, db._send_text = cu_drafts, cu_gui


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
