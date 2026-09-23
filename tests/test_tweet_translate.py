#!/usr/bin/env python3
"""tweet_translate.py — phần THUẦN: bóc id, dựng URL thẻ nhúng, đổi bản dịch
thành HTML, đọc bản dịch, chọn màu nhấn, ghép prompt.

Không mở trình duyệt, không gọi router. Phần cần mạng (`render`, `translate`)
nằm ngoài phạm vi — chúng đã được dựng hình thật trên dc-group trước khi merge
(luật LOW-286), còn ở đây giữ những luật mà một lần sửa vô ý là hỏng âm thầm:

  1. URL thẻ nhúng LUÔN mang `conversation=none` + `hideThread=true`. Thiếu nó,
     thẻ dựng cả chuỗi hội thoại và node chữ ĐẦU TIÊN lại là tweet CHA — bản
     dịch bị gắn nhầm bài. Đo thật 23/09/2026 trên arena/2102497079834882494.
  2. Bản dịch GIỮ dòng trống giữa các đoạn. `vietnamese.drop_mark_forbid` nén
     mọi khoảng trắng về một dấu cách (nó viết cho tiêu đề một dòng), nên gọi
     thẳng trên cả bản dịch là tweet bốn đoạn ra một khối chữ liền.
  3. `--vi` nhận `\\n` viết liền hai ký tự; đọc từ TỆP thì không đổi. Vai Bob
     chạy theo allowlist từng chuỗi lệnh nên không ghi được tệp tạm.
  4. Màu nhấn TẤT ĐỊNH theo id (dựng lại cùng tweet không đổi màu), và bảng nền
     sáng KHÔNG có vàng — #ffd400 trên nền trắng gần như không đọc được.
  5. Nhãn "Hiển thị thêm" bị bóc khỏi nguyên văn, và khi tweet bị cắt thì prompt
     phải dặn model bỏ mẩu câu dở dang — nếu không, tweet cụt ở "The" cho ra một
     dòng "Cái" lơ lửng trong ảnh.

Chạy:  venv/bin/python tests/test_tweet_translate.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import tweet_translate as tt                                 # noqa: E402

LINK = "https://x.com/arena/status/2102497076831818113"


def _read_vi(text=None, file_path=None, bo_qua_dau=False):
    return tt.read_vi(text, file_path, bo_qua_dau, "test")


def _thoat(fn, *a, **kw):
    """Chạy `fn`, trả về thông điệp SystemExit; None nếu nó KHÔNG thoát."""
    try:
        fn(*a, **kw)
    except SystemExit as e:
        return str(e)
    return None


# ---- bóc id ----------------------------------------------------------------

def test_tweet_id_doc_moi_dang_link():
    assert tt.tweet_id(LINK) == "2102497076831818113"
    assert tt.tweet_id("https://twitter.com/jack/status/20") == "20"
    assert tt.tweet_id("https://x.com/a/statuses/12345") == "12345"
    assert tt.tweet_id(LINK + "?s=46&t=abc") == "2102497076831818113"
    assert tt.tweet_id("  20  ") == "20", "id trần, có khoảng trắng thừa"


def test_tweet_id_tu_choi_thu_khong_phai_tweet():
    # Trang hồ sơ không có bài nào để dịch — phải nói ra, đừng đoán id.
    for xau in ("https://x.com/arena", "https://example.com/a/status/1", "", None):
        assert _thoat(tt.tweet_id, xau), f"lẽ ra phải từ chối: {xau!r}"


# ---- URL thẻ nhúng ---------------------------------------------------------

def test_embed_url_luon_tat_hoi_thoai():
    """Luật 1 — thiếu hai tham số này là dịch nhầm bài, không phải xấu hình."""
    u = tt.embed_url("20", "dark", "vi")
    assert "conversation=none" in u, u
    assert "hideThread=true" in u, u
    assert "id=20" in u and "theme=dark" in u and "lang=vi" in u, u


def test_embed_url_theo_theme_va_lang():
    u = tt.embed_url("20", "light", "en")
    assert "theme=light" in u and "lang=en" in u, u


# ---- bản dịch -> HTML ------------------------------------------------------

def test_to_html_doi_hl_thanh_span_dung_mau():
    ra = tt.to_html("Qwen <hl>miễn phí</hl> tuần này", "#ff7a00")
    assert 'color:#ff7a00' in ra and "font-weight:700" in ra, ra
    assert ra.count("<span") == 1 and ra.count("</span>") == 1, ra
    assert "miễn phí" in ra


def test_to_html_escape_chu_nguoi_viet():
    """Bản dịch là CHỮ, không phải HTML: một dấu `<` lọt qua là vỡ bố cục thẻ."""
    ra = tt.to_html('a < b & c <script>x</script>', "#f4212e")
    assert "<script>" not in ra, ra
    assert "&lt;" in ra and "&amp;" in ra, ra


def test_to_html_giu_dong_trong_giua_doan():
    ra = tt.to_html("đoạn một\n\nđoạn hai", "#f4212e")
    assert ra.count("<br>") == 2, ra


def test_strip_marks_bo_het_hl():
    assert tt.strip_marks("a <hl>b</hl> c") == "a b c"
    assert tt.strip_marks(None) == ""


# ---- đọc bản dịch ----------------------------------------------------------

def test_read_vi_giu_dong_trong():
    """Luật 2 — `drop_mark_forbid` nén cả `\\n`, phải áp theo từng dòng."""
    ra = _read_vi("đoạn một.\n\nđoạn hai.\n\nđoạn ba.")
    assert ra.count("\n\n") == 2, repr(ra)


def test_read_vi_doi_backslash_n_cua_dong_lenh():
    """Luật 3 — `--vi` gõ trên một dòng."""
    ra = _read_vi("dòng một\\n\\ndòng hai")
    assert ra == "dòng một\n\ndòng hai", repr(ra)


def test_read_vi_doc_tu_tep_thi_khong_doi_backslash_n():
    """Tệp đã có xuống dòng thật; `\\n` trong tệp là ý người viết."""
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "vi.txt"
        p.write_text("giữ nguyên \\n này\n", encoding="utf-8")
        ra = _read_vi(file_path=str(p))
    assert ra == "giữ nguyên \\n này", repr(ra)


def test_read_vi_chan_chu_mat_dau():
    loi = _thoat(_read_vi, "mo hinh mien phi cho nguoi dung")
    assert loi and "mất dấu" in loi, loi


def test_read_vi_bo_qua_dau_thi_cho_qua():
    assert _read_vi("mo hinh mien phi", bo_qua_dau=True)


def test_read_vi_bo_em_dash():
    """Em-dash bị cấm trong mọi văn bản đăng; thẻ ảnh đi đường khác nên chặn ở đây."""
    assert "—" not in _read_vi("một — hai")


def test_read_vi_tu_choi_ban_dich_rong():
    for xau in ("", "   ", "\n\n"):
        assert _thoat(_read_vi, xau), f"lẽ ra phải từ chối: {xau!r}"


def test_read_vi_giu_nguyen_hl():
    assert "<hl>" in _read_vi("Qwen <hl>miễn phí</hl> một tuần")


# ---- màu nhấn --------------------------------------------------------------

def test_pick_hl_tat_dinh_theo_id():
    """Luật 4 — dựng lại cùng một tweet không được đổi màu giữa chừng."""
    a = tt.pick_hl("2102497076831818113", "dark")
    b = tt.pick_hl("2102497076831818113", "dark")
    assert a == b, (a, b)
    assert a[1].startswith("#") and len(a[1]) == 7, a


def test_pick_hl_khong_ra_cung_mot_mau_cho_moi_bai():
    mau = {tt.pick_hl(str(1000 + i), "dark")[1] for i in range(40)}
    assert len(mau) >= 5, mau


def test_pick_hl_ep_bang_ten_hoac_hex():
    assert tt.pick_hl("20", "dark", "purple")[1] == tt.HL_DARK["purple"]
    assert tt.pick_hl("20", "dark", "#AABBCC") == ("tự chọn", "#aabbcc")


def test_pick_hl_tu_choi_gia_tri_sai():
    loi = _thoat(tt.pick_hl, "20", "dark", "#zzzzzz")
    assert loi and "red" in loi, "báo lỗi phải kèm danh sách màu hợp lệ"
    assert _thoat(tt.pick_hl, "20", "dark", "xanh lá")


def test_pick_hl_nen_sang_khong_dung_vang():
    """#ffd400 trên nền trắng gần như không đọc được."""
    assert "yellow" not in tt.HL_LIGHT
    assert all(tt.HL_LIGHT[k] != tt.HL_DARK.get(k) for k in tt.HL_LIGHT), \
        "bảng nền sáng phải là tông đậm riêng, không chép y bảng nền tối"
    assert tt.pick_hl("20", "light")[1] in tt.HL_LIGHT.values()


# ---- tweet bị cắt ----------------------------------------------------------

def test_cut_show_more_boc_nhan_va_bao_bi_cat():
    """Luật 5 — nhãn của X không phải nội dung tweet."""
    for nhan in ("Hiển thị thêm", "Show more", "Xem thêm"):
        chu, bi_cat = tt.cut_show_more(f"nội dung dài... The {nhan}")
        assert bi_cat is True, nhan
        assert nhan not in chu, chu
        assert chu.endswith("The"), chu


def test_cut_show_more_tweet_binh_thuong_thi_khong_bao():
    chu, bi_cat = tt.cut_show_more("một tweet trọn vẹn.")
    assert bi_cat is False and chu == "một tweet trọn vẹn."


def test_prompt_dan_bo_mau_cau_do_dang_khi_bi_cat():
    """Không dặn thì tweet cụt ở 'The' ra một dòng 'Cái' lơ lửng trong ảnh."""
    co = tt.translate_prompt("abc", cut=True)
    khong = tt.translate_prompt("abc", cut=False)
    assert tt.PROMPT_CUT in co and tt.PROMPT_CUT not in khong
    assert co.endswith("abc") and khong.endswith("abc")


def test_prompt_luon_co_bon_luat_xuong_dong_va_hl():
    p = tt.translate_prompt("abc")
    for luat in ("Dịch HẾT", "<hl>", "số đoạn", "@handle"):
        assert luat in p, luat


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
