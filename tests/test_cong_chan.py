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
