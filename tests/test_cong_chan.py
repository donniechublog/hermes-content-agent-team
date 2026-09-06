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
