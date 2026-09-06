#!/usr/bin/env python3
"""Kiem cac CONG CHAN thêm ngày 06/09/2026 — trọng tâm là CHẶN OAN.

Một cổng chặn sai làm vai không nộp được bài, tệ hơn nhiều so với việc thiếu
cổng: vai sửa kiểu gì cũng sai và Ông Chủ chỉ thấy im lặng. Ngày 06/09
`kiem_quote_dich` đã chặn 5/6 hook hợp lệ vì chỉ đo dấu tiếng Việt, nên mọi
cổng ở đây phải có ví dụ ĐÚNG-PHẢI-QUA đi kèm ví dụ SAI-PHẢI-CHẶN.

Chạy:  venv/bin/python tests/test_cong_chan.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import nop_chung as nc      # noqa: E402
import bat_buoc as bb       # noqa: E402
import caption_check as cc  # noqa: E402


# ---------------------------------------------------------------- quote dịch
QUOTE_PHAI_QUA = [
    # nhãn toàn tên riêng + số: không có dấu nào, nhưng hoàn toàn hợp lệ
    "Claude Opus 4.5 vs GPT-5.2: 82,5 vs 79,1 MMLU",
    "GPT-5 Codex Max: 2,75 USD / 1M token",
    "DeepSeek V4: 671B params, MIT license",
    "Qwen3-Max: 1 trieu token context",
    # tiếng Việt chuẩn
    "Mô hình mở đầu tiên vượt GPT-5 trên SWE-bench",
    # tiếng Việt gõ mất dấu: card.tim_mat_dau lo việc này, không phải cổng này
    "GPT-5 Codex Max ra mat, benchmark SWE-bench tang 12 diem so voi ban truoc",
]
QUOTE_PHAI_CHAN = [
    "AI agents are now writing most of the code at this company, says the CEO",
    "We are seeing a step change in how these models handle long context windows",
    "This is the first open model that beats GPT-5 on SWE-bench, and it runs locally",
]


def test_quote_dich_khong_chan_oan():
    for t in QUOTE_PHAI_QUA:
        assert nc.kiem_quote_dich(t, "hook") == [], f"chặn oan: {t}"


def test_quote_dich_van_bat_tieng_anh():
    for t in QUOTE_PHAI_CHAN:
        assert nc.kiem_quote_dich(t, "hook"), f"lọt tiếng Anh: {t}"


def test_quote_dich_bo_qua_chuoi_ngan():
    assert nc.kiem_quote_dich("It is what it is", "hook") == []   # < 25 ký tự


# --------------------------------------------------------------- nhân vật
def test_nhan_vat_ba_lop():
    anh = {"A1": {"mat": True, "mo_ta": "chan dung CEO"},
           "A2": {"mat": False},
           "A3": {"mat": True, "mo_ta": "anh quan chuc G20"}}
    # có mặt, không khai tên
    assert nc.kiem_nhan_vat(anh, ["A1"], "", "hock tan noi", "")
    # khai tên có trong bài
    assert nc.kiem_nhan_vat(anh, ["A1"], "Hock Tan, Broadcom", "ceo hock tan cua broadcom", "") == []
    # khai tên KHÔNG có trong bài (bịa)
    assert nc.kiem_nhan_vat(anh, ["A1"], "Hock Tan", "bai noi ve nvidia va jensen huang", "")
    # vision mô tả G20
    assert any("không phải nhân vật" in x for x in nc.kiem_nhan_vat(anh, ["A3"], "Jensen Huang", "jensen huang", ""))
    # ảnh không mặt / mã None không làm vỡ
    assert nc.kiem_nhan_vat(anh, ["A2", None], "", "abc", "") == []


# ------------------------------------------------------------------- số lạ
def test_so_la_doi_don_vi_khong_bi_bao():
    tl = "- Model dat 82,5 diem MMLU, gia 3 USD moi trieu token.\n- Huy dong 500 trieu USD."
    assert cc.so_la("Model dat 82,5 diem", tl) == []
    assert cc.so_la("chi 5 cai", tl) == []                    # 1 chữ số: bỏ qua
    assert cc.so_la("dat 99,9 diem va 1234 ty", tl) == ["99,9", "1234"]


# ------------------------------------------------------------ bắt buộc khớp
def test_khop_van_nhan_ra_muc_that():
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
        assert bb.khop({"ten": ten}, {"title": tieu_de, "summary_vi": ""}), f"trượt: {ten}"


def test_khop_khong_con_khop_bua_voi_manh_ngan():
    # "v3"/"ai" là mảnh 2 ký tự: trước 06/09 khớp gần như mọi tiêu đề
    assert bb.khop({"ten": "v3 ai"}, {"title": "bai nao cung co v3 va ai", "summary_vi": ""}) is False


def test_khop_uu_tien_link_va_tu_khoa():
    assert bb.khop({"link": "https://x.com/a/"}, {"link": "http://www.x.com/a"})
    assert bb.khop({"tu_khoa": ["nvidia", "hugging"]}, {"title": "Nvidia mua Hugging Face", "summary_vi": ""})
    assert not bb.khop({"tu_khoa": ["nvidia", "hugging"]}, {"title": "Nvidia ra chip moi", "summary_vi": ""})


# ------------------------------------------------------------------ teaser
def test_teaser_chan_url_emoji_danh_so():
    import teaser_assemble as ta
    day = ("Con so chi phi o muc 2,75 USD moi task, thap hon ba lan doi thu tren thi truong va van "
           "giu chat luong dau ra theo bo do luong cong khai cua ben thu ba doc lap. ") * 3
    ok = [day, day, day]
    assert ta.assemble("T", ok, [])["word_count"] > 0        # đoạn sạch thì qua
    for xau, ten in [("Chi tiet o https://example.com/x " + day, "URL"),
                     ("1. Muc dau tien noi ve chi phi " + day, "đánh số"),
                     ("🚀 Mo hinh moi chay nhanh hon " + day, "emoji")]:
        try:
            ta.assemble("T", [xau] + ok, [])
        except ValueError:
            pass
        else:
            raise AssertionError(f"không chặn {ten}")


def test_teaser_khong_bat_nham_ky_tu_tieng_viet():
    # ế ộ ữ … — “ ” đều dưới U+2500, không được coi là emoji
    for c in "ếộữ…—“”•":
        assert ord(c) < 0x2500, f"{c!r} U+{ord(c):04X} sẽ bị coi là emoji"


# ------------------------------------------------------- tin xếp hạng không bảng
def test_tin_xep_hang_khong_co_bang_thi_khong_chan():
    """Bẫy 06/09: tiêu đề trông như tin xếp hạng nhưng không nêu tên model →
    engine không chụp được bảng → không có mã "XH". Nếu cổng vẫn đòi "XH" thì
    vai sửa kiểu gì cũng sai và không bao giờ nộp được."""
    import anh_chuan_bi as cb
    import xep_hang as xh
    # tiêu đề kiểu này: là tin xếp hạng nhưng không tách được model
    for t in ["Bảng xếp hạng AI tháng 9: ai đang dẫn đầu",
              "LMArena leaderboard cập nhật tuần này"]:
        assert xh.la_tin_xep_hang(t, ""), t
        assert not xh.tach_model(t), f"{t}: nếu tách được model thì bẫy không xảy ra"
    # brief KHÔNG được đòi mã XH khi không có
    dong = cb.dong_brief_xep_hang({"tin_xep_hang": True, "xep_hang": None}, "bìa", "dre_nop")
    assert "BẮT BUỘC" not in dong and "chặn ảnh khác" not in dong, dong
    assert "không chặn" in dong, dong
    # có bảng thì vẫn đòi như cũ
    dong2 = cb.dong_brief_xep_hang(
        {"tin_xep_hang": True, "xep_hang": {"site": "LMArena", "bang": "text",
                                            "model": "GPT-5.2", "hang": 1, "kieu": "chup"}},
        "", "ethan_nop")
    assert "BẮT BUỘC" in dong2, dong2


def test_cong_xep_hang_chi_chan_khi_CHUP_duoc_bang():
    """dre_nop/ethan_nop chỉ được chặn khi engine CHỤP được bảng thật
    (kieu == "chup"). Không có ảnh XH, hoặc chỉ có thẻ dự phòng engine tự dựng,
    đều không được ép — xem test_the_du_phong_khong_duoc_ep_lam_anh_chinh."""
    import re as _re
    mau = r'\(m\.get\("xep_hang"\) or \{\}\)\.get\("kieu"\) == "chup"'
    for tep in ("dre_nop.py", "ethan_nop.py"):
        src = (ROOT / tep).read_text(encoding="utf-8")
        assert _re.search(mau, src), f"{tep}: cổng xếp hạng phải đòi kieu == 'chup'"


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


def test_tin_thuong_khong_bi_dong_dau_xep_hang():
    """Trước 06/09 mọi chữ 'vượt/dẫn đầu/số 1' đều kích hoạt, kéo engine đi lục
    12 bảng xếp hạng cho một tin gọi vốn rồi dựng thẻ số liệu bịa."""
    import xep_hang as xh
    for t in TIEU_DE_THUONG:
        assert not xh.la_tin_xep_hang(t, ""), f"vẫn bắt nhầm: {t}"


def test_tin_xep_hang_that_van_duoc_nhan():
    import xep_hang as xh
    for t in TIEU_DE_XEP_HANG:
        assert xh.la_tin_xep_hang(t, ""), f"mất nhận diện: {t}"


def test_ho_model_trung_tu_thuong_phai_di_kem_so():
    """'seed', 'nova', 'solar'... chỉ là tên model khi có số phiên bản."""
    import xep_hang as xh
    assert xh.tach_model("vòng seed do Nvidia dẫn đầu") == []
    assert xh.tach_model("Amazon ra chip Nova mới") == []
    assert xh.tach_model("IBM mở nguồn Granite 4"), "Granite 4 phải nhận ra"
    assert xh.tach_model("GPT-5.2 leo lên #1"), "GPT-5.2 phải nhận ra"


def test_the_du_phong_khong_duoc_ep_lam_anh_chinh():
    """kieu='the' là thẻ engine tự dựng, chưa đọc bảng thật — không được loại bỏ
    ảnh thật. Chỉ kieu='chup' mới bật cổng bắt buộc."""
    import ethan_nop
    anh = [{"ma": "A1", "goc": "/tmp/x.png", "san": None, "loai": "anh", "ti_le": 1.0,
            "mat": 0, "ngang": False, "canh_ngan": 1200, "w": 1200, "h": 1200,
            "goc_trai_sang": 50, "dung": ["nền hero"], "ghi_chu": [], "mien": "x.com",
            "tu": "x", "lien_quan": True}]
    spec = {"anh": "A1", "kieu": "quote", "hook": "Mô hình mới đạt điểm cao nhất bảng",
            "tagline": "MODEL", "attrib": "via X"}
    for kieu, phai_chan in (("chup", True), ("the", False)):
        m = {"anh": anh, "tin_xep_hang": True, "chu_bai": "", "tu_lieu": {}, "draft_id": "d1",
             "xep_hang": {"kieu": kieu, "site": "arena.ai", "bang": "Text Arena",
                          "model": "seed", "hang": 5}}
        _, loi, _ = ethan_nop.giai_spec(spec, m, Path("/tmp"))
        co = any("XẾP HẠNG" in x for x in loi)
        assert co == phai_chan, f"kieu={kieu}: {'phải chặn' if phai_chan else 'không được chặn'}"


# ------------------------------------------------- sổ ảnh đã dùng: khoá theo TIN
def test_so_anh_khoa_theo_tin_khong_theo_draft():
    """Cùng một tin giao cho Dre rồi Ethan ra hai draft_id khác nhau nhưng dùng
    chung bộ ảnh — vai sau không được bị chặn sạch."""
    import luat_anh as la
    from PIL import Image, ImageDraw
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        la._so_da_dung = lambda: d / "s.jsonl"
        p = d / "a.png"
        im = Image.new("RGB", (800, 600), (255, 255, 255))
        dr = ImageDraw.Draw(im)
        for i, h in enumerate([380, 300, 240, 180, 120]):
            dr.rectangle([60 + i * 140, 500 - h, 160 + i * 140, 500], fill=(40, 90, 200))
        im.save(p)
        LINK = "https://openai.com/tin-abc"
        la.ghi_da_dung(p, "tin-abc-carousel-blog", "carousel", LINK)
        # cùng tin, vai khác -> KHÔNG chặn
        assert la.kiem_da_dung("A1", p, "tin-abc-designer-blog", LINK)[0] == []
        # tin khác dùng lại đúng tấm đó -> CHẶN
        assert la.kiem_da_dung("A1", p, "tin-xyz-carousel-blog", "https://x.com/khac")[0]


def test_khoa_tin_chuan_hoa_url():
    import luat_anh as la
    assert la.khoa_tin("https://www.OpenAI.com/tin/") == la.khoa_tin("http://openai.com/tin")
    assert la.khoa_tin("https://x.com/a?utm=1#z") == "x.com/a"


# ------------------------------------------- ảnh xếp hạng: dấu, cắt, tỉ lệ
def _anh_xh(d: Path, ten="XH.png", w=1242, h=2688):
    """Ảnh giả lập bảng xếp hạng đã đóng dấu như xep_hang.py làm."""
    from PIL import Image, ImageDraw
    from PIL.PngImagePlugin import PngInfo
    im = Image.new("RGB", (w, h), (255, 255, 255))
    dr = ImageDraw.Draw(im)
    for i in range(12):                      # 12 hàng bảng
        y = 120 + i * (h - 240) // 12
        dr.rectangle([60, y, w - 60, y + 60], fill=(240, 240, 245))
    dr.rectangle([60, h - 700, w - 60, h - 640], outline=(245, 197, 24), width=8)  # khoanh model
    meta = PngInfo()
    meta.add_text("nguon_dung", "chup_xep_hang")
    meta.add_text("model", "GPT-5.2")
    p = d / ten
    im.save(p, "PNG", pnginfo=meta)
    return p


def test_luu_crop_giu_dau_anh_goc():
    """_luu_crop từng dựng PngInfo trắng → bản cắt mất dấu chup_xep_hang →
    la_xep_hang False → mất miễn trừ → carousel chặn đúng cái bìa bắt buộc."""
    import anh_chuan_bi as cb
    import luat_anh as la
    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        goc = _anh_xh(d)
        with Image.open(goc) as im:
            assert la.la_xep_hang(im), "ảnh gốc phải mang dấu"
            cb._luu_crop(im, d / "cat.png", "4:5", cy=0.35)
        with Image.open(d / "cat.png") as ra:
            assert la.la_xep_hang(ra), "bản cắt MẤT dấu chup_xep_hang"
            assert la.doc_dau_crop(ra), "bản cắt phải vẫn có dấu crop_ti_le"


def test_kiem_ti_le_mien_tru_anh_xep_hang():
    """Bảng desktop ra ~1.28, bảng mobile ra ~0.46 — cả hai đều ngoài dải
    4:5..1:1. Không miễn trừ thì Dre kẹt: cổng bắt dùng XH, carousel chặn XH."""
    import luat_anh as la
    from PIL import Image
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        for w, h in ((1600, 1250), (1242, 2688)):
            p = _anh_xh(d, f"xh_{w}x{h}.png", w, h)
            with Image.open(p) as im:
                assert la.kiem_ti_le("bìa", p, w, h, img=im)[0] == [], f"chặn oan {w}x{h}"
        # ảnh thường ngoài dải VẪN phải bị chặn
        from PIL import Image as I
        q = d / "thuong.png"
        I.new("RGB", (1600, 1250), (200, 200, 200)).save(q)
        with I.open(q) as im:
            assert la.kiem_ti_le("bìa", q, 1600, 1250, img=im)[0], "ảnh thường phải bị chặn"


def test_anh_xep_hang_khong_bi_cat():
    """Hàng model đã khoanh có thể nằm dưới 55% dải chụp; cắt 4:5 cy=0.35 sẽ
    xoá mất nó. Ảnh xếp hạng phải giữ nguyên vẹn (a["san"] = a["goc"])."""
    src = (ROOT / "anh_chuan_bi.py").read_text(encoding="utf-8")
    khoi = src[src.index("    san = wd / \"san\""):]
    khoi = khoi[:khoi.index("a[\"dung\"] = [\"thân")]
    assert 'if a.get("xep_hang"):' in khoi, "phan_loai thiếu nhánh giữ nguyên ảnh xếp hạng"
    truoc_elif = khoi[:khoi.index("elif r <")]
    assert 'a["san"] = a["goc"]' in truoc_elif, "nhánh xếp hạng phải đặt san = goc, không cắt"


# ------------------------------------------------- Kite: ảnh chưa ai nhìn
def test_kite_khong_ep_dung_anh_chua_nhin():
    """Vision tắt → mọi ảnh lien_quan=None. Ép lúc đó là đẩy quảng cáo/widget
    lên slide."""
    import kite_nop
    def hinh(lien_quan):
        return {"A1": {"ma": "A1", "goc": "/tmp/a.png", "w": 1200, "h": 800,
                       "ti_le": 1.5, "loai": "chart", "lien_quan": lien_quan,
                       "mien": "x.com", "tu": "x", "ghi_chu": []}}
    slides = [{"kind": "cover", "eyebrow": "X", "title": "T", "standfirst": "S"}] * 6
    for lq, phai_ep in ((True, True), (None, False)):
        m = {"anh": list(hinh(lq).values()), "brand": "donniechublog", "title": "T",
             "draft_id": "d1", "chu_bai": "", "tu_lieu": {}, "link": ""}
        _, loi, _ = kite_nop.giai_spec({"slides": slides}, m, Path("/tmp"))
        co = any("BẮT BUỘC dùng ít nhất một" in x for x in loi)
        assert co == phai_ep, f"lien_quan={lq}: {'phải ép' if phai_ep else 'KHÔNG được ép'}"


# -------------------------------------- tách model / hạng từ tiêu đề xếp hạng
def test_tach_model_giu_so_phien_ban_nguyen():
    """Lookahead cũ chặn mọi chữ thường sau số → "GPT-6 tops the leaderboard"
    ra ['GPT'], engine khoanh hàng đầu tiên chứa "gpt" (có thể là GPT-5.2 mini
    hạng 23) rồi cổng ép dùng đúng tấm đó làm hero."""
    import xep_hang as xh
    for t, mong in [("GPT-6 tops the leaderboard", "GPT-6"),
                    ("Gemini 4 leo lên #1 bảng xếp hạng", "Gemini 4"),
                    ("Llama 5 vượt Qwen trên LiveBench", "Llama 5"),
                    ("Grok 5 takes first place", "Grok 5"),
                    ("GPT-5.2 tops the leaderboard", "GPT-5.2")]:
        ra = xh.tach_model(t)
        assert ra and ra[0] == mong, f"{t!r} → {ra[:2]}, mong {mong}"


def test_tach_model_khong_an_so_don_vi():
    """Số đi với đơn vị (điểm, USD, tỷ) không phải số phiên bản."""
    import xep_hang as xh
    assert xh.tach_model("GPT-6 Astra đạt 55 điểm trên bảng xếp hạng")[0] == "GPT-6 Astra"
    assert xh.tach_model("Claude Opus 4.5 giá 3 USD mỗi triệu token")[0] == "Claude Opus 4.5"


def test_tach_hang_chon_dung_khong_lay_match_dau():
    """"Top 10" đầu tiêu đề là kích cỡ danh sách, không phải thứ hạng."""
    import xep_hang as xh
    for t, mong in [("Top 10 mô hình AI 2026: GPT-6 Astra dẫn đầu", 1),
                    ("Kimi K3 lọt top 5 SWE-bench, hạng 4", 4),
                    ("GPT-6 leo lên #1 bảng xếp hạng LMArena", 1),
                    ("Gemini 3 Pro hạng 3 trên Text Arena", 3),
                    ("Qwen3-Max lọt top 5 Intelligence Index", 5)]:
        md = xh.tach_model(t)
        assert xh.tach_hang(t, md[0] if md else "") == mong, t


def test_anh_xep_hang_mien_cong_dung_lai():
    """Hai bài về hai model cùng trong top một bảng chụp đúng dải hàng đó, chỉ
    khác khung khoanh → dHash coi là trùng. Cổng dùng-lại chặn ảnh XH, còn cổng
    "tin xếp hạng phải dùng XH" chặn mọi ảnh khác: hai lỗi loại trừ nhau."""
    import luat_anh as la
    from PIL import Image, ImageDraw
    from PIL.PngImagePlugin import PngInfo
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        la._so_da_dung = lambda: d / "s.jsonl"

        def bang(ten, khoanh_y, dau=True):
            im = Image.new("RGB", (1200, 900), (255, 255, 255))
            dr = ImageDraw.Draw(im)
            for i in range(10):
                dr.rectangle([50, 60 + i * 80, 1150, 120 + i * 80], fill=(240, 240, 245))
            dr.rectangle([50, khoanh_y, 1150, khoanh_y + 60], outline=(245, 197, 24), width=6)
            m = PngInfo()
            if dau:
                m.add_text("nguon_dung", "chup_xep_hang")
            p = d / ten
            im.save(p, "PNG", pnginfo=m)
            return p

        b1, b2 = bang("xh1.png", 140), bang("xh2.png", 620)
        t1, t2 = bang("t1.png", 140, dau=False), bang("t2.png", 620, dau=False)
        la.ghi_da_dung(b1, "bai1-designer-blog", "designer", "https://a.com/1")
        la.ghi_da_dung(t1, "bai1-designer-blog", "designer", "https://a.com/1")
        # ảnh xếp hạng: bài sau dùng lại được
        assert la.kiem_da_dung("XH", b2, "bai2-designer-blog", "https://a.com/2")[0] == []
        # ảnh thường gần giống: vẫn phải chặn
        assert la.kiem_da_dung("A1", t2, "bai2-designer-blog", "https://a.com/2")[0]


# ------------------------------------------------- watermark cua Bob (@handle)
def test_handle_bob_luon_co_cong_va_nhan_ca_hai_kieu_khoa():
    """CT_BRAND la khoa CONTAINER ('blog'), card.THUONG_HIEU khoa theo TEN brand
    ('donniechublog'). Truoc 06/09/2026 `handle_kenh` tra thang gia tri tra cuu
    nen tren container blog no roi ve chinh chuoi 'blog': MOI anh Bob dong khung
    in watermark "blog" thay vi "@donniechublog"."""
    import bob_nop
    assert bob_nop.handle_kenh("blog") == "@donniechublog"
    assert bob_nop.handle_kenh("dcgr").startswith("@")
    # dua san ten brand (kieu khoa con lai) van phai ra dung
    assert bob_nop.handle_kenh("donniechublog") == "@donniechublog"
    # da co "@" thi khong duoc nhan doi
    assert bob_nop.handle_kenh("@donniechublog") == "@donniechublog"
    # brand la khong biet: van phai co "@", khong duoc tra chuoi tran
    assert bob_nop.handle_kenh("khong_co_that").startswith("@")


# ------------------------------------------- tran 8 tin khong cat muc BAT BUOC
def test_tran_tin_khong_cat_muc_bat_buoc():
    """Muc BAT BUOC ton tu hom truoc duoc gan score_partial=0 nen diem toi da chi
    con 50 — LUON xep chot va truoc 06/09/2026 LUON bi tran 8 tin cat. Cat xong
    thi `bat_buoc.kiem` lai them BAN TRONG (score=0, summary_vi rong, ghi chu
    "vai bo sot"): bao cao do oan cho vai la bo sot dung tin no vua cham ky, con
    vai viet bai thi mat sach tom tat."""
    import json
    import os
    import subprocess
    BRAND = "thu_tran_bb"
    moi_truong = {**os.environ, "CT_BRAND": BRAND}
    kho = ROOT / "state" / BRAND
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        BB = "https://anthropic.com/claude-opus-46"
        # ghi danh sach bat buoc bang chinh tien trinh con (cung state dir)
        subprocess.run([str(ROOT / "venv/bin/python"), "-c",
                        "import sys; sys.path.insert(0, %r); import bat_buoc; "
                        "bat_buoc.them('scout', 'k1', 'Claude Opus 4.6', 'ra_mat', '', %r)"
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
                [str(ROOT / "venv/bin/python"), str(ROOT / "manifest_build.py"),
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
def _anh_van(w, h, ra, dai_toi=None, sang=False):
    """Anh thu co VAN DAY (khong bi `_chan_chart` bat nham la bieu do) va mot dai
    toi tuy chon. Kich thuoc tranh khit 4:5 vi cong `_chan_chuan_anh` doi dau vet
    crop_ti_le.py voi anh dung khit ti le."""
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


def _dung_the(src, ra, tmp):
    import card
    card.dat_thuong_hieu("donniechublog")
    card.build(str(src), "Mô hình mở đầu tiên vượt GPT-5 trên SWE-bench Verified",
               str(ra), handle="@donniechublog", ratio="4:5",
               attrib="Đọc bài đầy đủ tại donniechublog - Hacker News")
    return ra


def test_anh_ngang_khong_lo_duong_ranh_ngang():
    """Anh THAP hon khung (moi anh ngang) dan thang len lop nen se lo mot duong
    ke ngang tai `nat_h`: tren la anh sac, duoi la ban cover-blur cua MOT VUNG
    KHAC. Do that trước 06/09/2026: anh 3:2 tut 128 do sang trong MOT hang, 4:3
    tut 41 — dung cai "the doc ra HAI VUNG" Ong Chu bat nhieu lan. Cong 
    `_chan_anh_thap` khong do duoc viec nay (no chi chan tu ti le > 1.6)."""
    from PIL import Image, ImageStat
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        for w, h in ((1500, 1000), (1200, 900), (1600, 1000)):     # 3:2, 4:3, 16:10
            src = _anh_van(w, h, t / f"g{w}.png", dai_toi=(0.62, 1.0))
            ra = _dung_the(src, t / f"the{w}.png", t)
            im = Image.open(ra).convert("L")
            W_, H_ = im.size
            nat_h = round(h * W_ / w)
            hang = [ImageStat.Stat(im.crop((0, y, W_, y + 1))).mean[0]
                    for y in range(max(0, nat_h - 14), min(H_, nat_h + 15))]
            buoc = max(abs(hang[i] - hang[i - 1]) for i in range(1, len(hang)))
            assert buoc < 8, (f"anh {w}x{h}: van lo duong ranh tai nat_h={nat_h}, "
                              f"buoc nhay {buoc:.1f} do sang trong mot hang")


def test_dong_nguon_doc_duoc_tren_day_the_sang():
    """Dong nguon ("Doc bai ... - <nguon>") duoc ve DUOI `frame_bottom`, tuc
    ngoai cai hop dung de chon mau chu cho quote. Anh co khoi chu toi nhung day
    the sang thi truoc 06/09/2026 no lay mau TRANG cua quote dat len nen sang:
    do that CR 1.04 — mat hoan toan, va mat luon dan nguon."""
    from PIL import Image
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        # anh 1200x1560 (khong khit 4:5): sang toan bo, chi toi o giua — khoi
        # quote nam tren nen toi, day the van sang.
        src = _anh_van(1200, 1560, t / "sang.png", dai_toi=(0.58, 0.90), sang=True)
        ra = _dung_the(src, t / "the.png", t)
        im = Image.open(ra).convert("L")
        W_, H_ = im.size
        dai = im.crop((150, H_ - 105, W_ - 150, H_ - 25))     # dai chua dong nguon
        px = sorted(dai.getdata())
        chenh = px[len(px) // 2] - px[len(px) // 100]         # trung vi - 1%
        assert chenh > 120, (f"dong nguon khong noi tren nen: chenh sang chi {chenh} "
                             "(nen ~230, chu phai tach han ra)")

# ------------------------------------- bat_buoc: manh ngan CO SO la thu phan biet
def test_khop_giu_so_hieu_phien_ban():
    """`ten` cua muc BAT BUOC hay co so hieu phien ban ngan: "R1", "K2", "o4",
    "4 Fast". Loc `len >= 3` vut sach chung, nen "DeepSeek R1" rut con
    ["deepseek"]: Nova dua tin "DeepSeek V4 ra mat" la khop() tra True, kiem()
    tuong da dua nen khong tu them, roi xoa() xoa han muc. Tin R1 mat VINH VIEN
    vi scan_models ghi `aa_da_bao` vao moc nen khong gieo lai.

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
        assert not bb.khop({"ten": ten}, {"title": td}), \
            f"muc {ten!r} bi coi la 'da dua' boi tin khac: {td!r} — se bi xoa oan"
    for ten, td in phai_khop:
        assert bb.khop({"ten": ten}, {"title": td}), \
            f"muc {ten!r} KHONG nhan ra chinh no trong {td!r} — se bi them trung"


# ------------------------------------------ nhan_vat: chuc danh va dau tieng Viet
_BAI = ("sam altman, ceo of openai, said the model is ready today. "
        "jensen huang of nvidia spoke at the event. "
        "pham nhat vuong opened the new plant in hai phong.")


def test_nhan_vat_co_chuc_danh_hoac_dau_van_qua():
    """Phep so cu (`ho = nv.split(",")[0]`, roi `ho not in chu_bai`) tach hau to
    CHI bang dau phay va so CHUOI CON chu khong so TU. Hai huong hong: chan oan
    ten kem chuc danh trong ngoac / sau gach, chan oan ten Viet CO DAU khi bai
    goc viet khong dau; va lot bua khi bai tinh co chua dung ky tu do o cho
    khac. Vai doc "Bo anh nay" roi bo dung tam anh dung."""
    for nv in ("Sam Altman (CEO OpenAI)", "Jensen Huang – Nvidia",
               "Sam Altman - CEO OpenAI", "Phạm Nhật Vượng", "Sam Altman"):
        assert nc._ten_co_trong_bai(nv, _BAI), f"chan oan ten dung: {nv!r}"


def test_nhan_vat_van_bat_ten_bia():
    """Cong nay sinh ra sau su co bia ten 05/09 (anh quan chuc G20, khai "Hock
    Tan"), noi long khong duoc lam mat no."""
    for nv in ("Hock Tan", "Tim Cook (CEO Apple)", "Nguyen Van Bia"):
        assert not nc._ten_co_trong_bai(nv, _BAI), f"lot ten khong co trong bai: {nv!r}"


def test_mo_ta_logo_hang_trong_bai_khong_bi_chan():
    """Cong chi no khi anh CO MAT NGUOI va vai DA khai ten — tuc nham dung vao
    anh chan dung/su kien, loai anh the hero can nhat. Tu tran "logo" trong bo
    tu khoa chan luon "CEO tren san khau, phia sau la logo OpenAI" — anh chuan
    nhat cua loai do, va la thu chinh prompt vision day rang LA lien quan."""
    anh_ok = {"A1": {"mat": 1, "mo_ta": "Sam Altman phát biểu trên sân khấu, "
                                        "phía sau là logo OpenAI"}}
    assert not nc.kiem_nhan_vat(anh_ok, ["A1"], "Sam Altman", _BAI, ""), \
        "chan oan anh su kien co logo hang trong bai"
    # nhung logo cua TO BAO thi van phai chan
    anh_bao = {"A1": {"mat": 1, "mo_ta": "Ảnh có watermark của hãng tin, "
                                         "không rõ người"}}
    assert nc.kiem_nhan_vat(anh_bao, ["A1"], "Sam Altman", _BAI, "")


# ------------------------------------------------------- quet_nop: dong [bo qua]
def test_quet_nop_in_ca_dong_bo_qua():
    """[bo qua] = mat tron mot tin, loai nang nhat, ma truoc 06/09/2026 bo loc
    khong nhat no. Vera go nham k=9: tin "OpenAI IPO dinh gia 900 ty USD" bien
    mat sach, khong mot dong canh bao, rc=0, vai bao "da gui bao cao"."""
    import quet_nop
    ra = quet_nop.loc_canh_bao(
        "[bo qua] muc 2: k=9 ngoai danh sach 1..5\n"
        "[canh bao] category khong hop le\n"
        "dong thuong khong lien quan\n"
        "[LOI] khong doc duoc tep\n")
    assert any("[bo qua]" in d for d in ra), "dong [bo qua] van bi nuot"
    assert any("[LOI]" in d for d in ra)
    assert not any("dong thuong" in d for d in ra)


# --------------------------------- manifest_build: khong ghi de bang manifest rong
def test_manifest_rong_khong_ghi_de():
    """Cong `if not items` truoc 06/09/2026 nam LOT TRONG khoi `if problems`, ma
    ca hai duong vao deu cho problems RONG: picks la `[]`, hoac dict sai khoa
    (script chi nhan "picks"/"items"). Khi ay script ghi manifest 0 muc, gui bao
    cao chi co tieu de + dong moi tra loi so ma khong co so nao, rc=0. Nang hon:
    quet_nop co dinh ten tep theo NGAY nen lan chay lai de thang len ban tot, va
    duyet_chon_tin chon manifest theo mtime — khong co duong lui."""
    import json
    import os
    import subprocess
    moi_truong = {**os.environ, "CT_BRAND": "thu_rong_mb"}
    kho = ROOT / "state" / "thu_rong_mb"
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
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
                    [str(ROOT / "venv/bin/python"), str(ROOT / "manifest_build.py"),
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


def _anh_hai_tone(w, h, ra, ranh):
    """Nua TREN toi, nua DUOI sang, ranh o `ranh` (ti le chieu cao). Van day de
    khong bi `_chan_chart` bat nham la bieu do."""
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


def test_moi_dong_quote_doc_duoc_khi_nen_hai_tone():
    """Ranh sang/toi NGANG cat qua khoi chu la ca rat thuong (anh chup co hero
    toi tren, bang trang duoi; anh ghep doc hai tam khac tone). Truoc 06/09/2026
    `_mau_doi_nen` lay MOT mean cho ca khoi: trung binh 136 -> chon chu TRANG
    trong khi nua duoi khoi la nen 243-250, may dong cuoi la trang tren trang.
    Loi DOI XUNG o chieu kia: trung binh 142 -> chu toi, nua tren thanh
    den-tren-den. Do tung dai dong thi moi dong deu phai doc duoc."""
    from PIL import Image, ImageDraw
    import card
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        card.dat_thuong_hieu("donniechublog")
        ve_goc = ImageDraw.ImageDraw.text
        da_ve = []

        def ve_ghi(self, xy, text, *a, **kw):
            da_ve.append((xy, text, kw.get("fill")))
            return ve_goc(self, xy, text, *a, **kw)

        quote = "Mô hình mở đầu tiên vượt GPT-5 trên SWE-bench Verified"
        # 0.756: ranh roi GIUA khoi chu. 0.60: ca khoi tren nen sang.
        for ranh in (0.756, 0.60, 0.95):
            da_ve.clear()
            src = _anh_hai_tone(1200, 1560, t / f"g{int(ranh*1000)}.png", ranh)
            ra = t / f"the{int(ranh*1000)}.png"
            ImageDraw.ImageDraw.text = ve_ghi
            try:
                card.build(str(src), quote, str(ra), handle="@donniechublog",
                           ratio="4:5", attrib="Đọc bài đầy đủ tại donniechublog")
            finally:
                ImageDraw.ImageDraw.text = ve_goc
            im = Image.open(ra).convert("RGB")
            dong = [(xy, tx, f) for xy, tx, f in da_ve if tx and tx in quote and f]
            assert len(dong) >= 3, f"khong ghi nhan du dong quote ({len(dong)})"
            for (x, y), tx, mau in dong:
                # nen = trung vi cua dai chua dong (chu chi chiem thieu so pixel)
                dai = im.crop((int(x), int(y) + 20, im.width - int(x), int(y) + 95))
                px = sorted(dai.convert("L").getdata())
                nen = px[len(px) // 2]
                assert _cr(mau, (nen,) * 3) >= 4.0, (
                    f"ranh {ranh}: dong {tx[:28]!r} mau {mau} tren nen L={nen} "
                    f"chi CR {_cr(mau, (nen,) * 3):.2f}")


def test_net_khung_va_dau_ngoac_khong_chim_tren_nen_sang():
    """Net khung + hai dau " 210px la vat nhan dien cua kieu pull-quote. Truoc
    06/09/2026 net khung la CYAN CUNG, khong nhanh nao doi: tren anh nen sang,
    CYAN cua dcgr (trang thuan) cho CR 1.04 — bien mat sach; cua donniechublog
    cho 1.88, nhat han. Dau ngoac con te hon: `_du_sang` keo mau hang SANG THEM,
    dung luat danh cho nen toi, tuc sai chieu."""
    import card
    with tempfile.TemporaryDirectory() as td:
        t = Path(td)
        for brand in ("donniechublog", "dcgr"):
            card.dat_thuong_hieu(brand)
            goc = card._quote_frame
            ghi = {}

            def bat(d, x0, y0, x1, y1, line_color, mark_color, lw=5):
                ghi["net"], ghi["mark"] = line_color, mark_color
                return goc(d, x0, y0, x1, y1, line_color, mark_color, lw)

            card._quote_frame = bat
            try:
                # ranh 0.60: ca khoi chu nam tren nen SANG
                src = _anh_hai_tone(1200, 1560, t / f"s_{brand}.png", 0.60)
                card.build(str(src), "Mô hình mở đầu tiên vượt GPT-5 trên SWE-bench",
                           str(t / f"the_{brand}.png"), handle="@donniechublog",
                           ratio="4:5", attrib="Đọc bài đầy đủ tại donniechublog")
            finally:
                card._quote_frame = goc
            for ten in ("net", "mark"):
                cr = _cr(ghi[ten], (250, 250, 250))
                assert cr >= 3.0, (f"{brand}: {ten} khung {ghi[ten]} tren nen sang "
                                   f"chi CR {cr:.2f} — chim")
        card.dat_thuong_hieu("donniechublog")

if __name__ == "__main__":
    ham = [v for k, v in list(globals().items()) if k.startswith("test_")]
    loi = 0
    for h in ham:
        try:
            h()
            print(f"OK   {h.__name__}")
        except AssertionError as e:
            loi += 1
            print(f"FAIL {h.__name__}: {e}")
    print(f"\n{len(ham) - loi}/{len(ham)} test qua")
    sys.exit(1 if loi else 0)
