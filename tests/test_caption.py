#!/usr/bin/env python3
"""Cong chan caption cua Miles (`caption_check.check`).

Day la cong CUOI CUNG truoc khi mot bai vao hang duyet, va la thu Ong Chu doc
tren kenh. 103 dong, 14 cong, thuan (chuoi vao, bo ba ra) — ma truoc 07/09/2026
chi co helper `count_is` duoc test, con `kiem` thi khong. Moi cong o day la mot
loi da len kenh that: caption 802 ky tu khong mot dau nao (doi provider), tin
DeepSeek co bang 11 dong so ma caption 0 con so, cung mot cum 6 tu lap hai lan
trong 500 ky tu, link song lot vi khong co scheme.

Chay:  venv/bin/python tests/test_caption.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import caption_check as cc  # noqa: E402

# Caption HOP LE: co dau, moi cau mot dong, co so va ghi ro tu cong bo, khong
# thoi phong, khong link, khong the la, khong em-dash. Moi test doi DUNG MOT thu.
CHUAN = """Nvidia mở kho mô hình Nemotron cho mọi nhà phát triển, tải về không cần đăng ký.
Bản lớn nhất có 340 tỷ tham số, theo hãng công bố đạt 86,2 điểm trên MMLU.
Điều này thu hẹp khoảng cách với các mô hình đóng chỉ còn vài điểm.
Với người làm sản phẩm, đây là lần đầu một mô hình cỡ này dùng được miễn phí ở Việt Nam."""

TU_LIEU = """# Tư liệu
- Nemotron có 340 tỷ tham số.
- Điểm MMLU 86,2 theo hãng công bố.
- Mô hình tải về miễn phí, giấy phép mở.
"""


def _kiem(caption=CHUAN, tu_lieu=TU_LIEU):
    return cc.check(caption, tu_lieu)


def _co(ds, *manh):
    return any(all(x in d for x in manh) for d in ds)


# ---------------------------------------------------------------- duong hop le
def test_caption_chuan_khong_loi():
    loi, canh, tin = _kiem()
    assert loi == [], loi
    assert tin["sentence_count"] == 4 and tin["number_count"] >= 2, tin
    # Do dai khong phai tieu chi (LOW-296): khong chan, khong nhac.
    assert not any("MAT DAU" in c for c in canh)


def test_caption_rong_la_loi_duy_nhat():
    assert cc.check("   \n ", TU_LIEU) == (["Caption rỗng."], [], {})


# ---------------------------------------------------------------- dau tieng Viet
def test_mat_dau_la_loi_nang():
    """802 ky tu khong mot dau nao sau khi doi provider — khong ai thay cho toi
    khi doc ky. Loi nang hon thieu so vi bai khong dang duoc."""
    khong_dau = "Nvidia mo kho mo hinh Nemotron cho moi nha phat trien.\nBan lon nhat co 340 ty tham so.\nDieu nay thu hep khoang cach."
    loi, _c, tin = _kiem(khong_dau)
    assert _co(loi, "MAT DAU"), loi
    assert tin["diacritic_ratio"] < cc.THRESHOLD_MARK


def test_nguong_dau_thap_hon_audition_co_y():
    """0.12 thap hon 0.15 cua model_audition: caption nhieu ten rieng tieng Anh
    keo ty le xuong. Hai nguong khac nhau la chu dich."""
    assert cc.THRESHOLD_MARK == 0.12


def test_ty_le_dau_khong_tinh_the_html():
    """<b>...</b> la chu Latin khong dau, khong duoc keo ty le xuong."""
    co_the = CHUAN.replace("Nvidia", "<b>Nvidia</b>").replace("Nemotron", "<code>Nemotron</code>")
    assert _kiem(co_the)[0] == []


# ---------------------------------------------------------------- do dai
# Cau don le KHAC NHAU tung cau (khong lap cum 6 tu) de khong tu dinh vao loi
# LAP Y khi noi voi CHUAN de keo dai — moi cau mot chu de rieng.
_CAU_KHAC_NHAU = [
    "Một trung tâm dữ liệu mới ở Malaysia vừa ký hợp đồng thuê chip trong ba năm tới.",
    "Giá pin lithium giảm 12% theo báo cáo quý này từ một hãng phân tích độc lập.",
    "Startup robot hút bụi tại Hàn Quốc huy động thêm vòng vốn Series B tuần trước.",
    "Một đại học ở Nhật công bố chip quang học tiêu thụ điện thấp hơn hẳn bản cũ.",
    "Hãng viễn thông châu Âu bắt đầu thử nghiệm mạng vệ tinh cho vùng núi hẻo lánh.",
    "Nhóm nghiên cứu Canada công bố phương pháp làm mát chip bằng chất lỏng vi kênh.",
    "Một sàn thương mại điện tử Đông Nam Á mở kho hàng tự động đầu tiên trong khu vực.",
    "Chính phủ Đức công bố gói hỗ trợ cho ngành bán dẫn nội địa trong năm tới.",
    "Một công ty xe điện Trung Quốc giới thiệu pin thể rắn cho dòng xe phổ thông.",
    "Nhà sản xuất máy chủ tại Đài Loan tăng công suất nhà máy thêm một phần ba.",
    "Một tạp chí khoa học công bố nghiên cứu về vật liệu bán dẫn thế hệ mới.",
    "Hãng hàng không thử nghiệm nhiên liệu sinh học cho các chuyến bay nội địa ngắn.",
    "Một quỹ đầu tư mạo hiểm tại Singapore rót vốn vào chuỗi cung ứng linh kiện quang học.",
    "Nhóm kỹ sư Ấn Độ phát triển cảm biến giá rẻ cho nông nghiệp chính xác.",
    "Một thành phố tại Bắc Âu thử nghiệm lưới điện thông minh quy mô toàn khu dân cư.",
    "Hãng bảo hiểm tại Anh bắt đầu dùng mô hình dự báo rủi ro thiên tai theo vùng.",
    "Một trường đại học Úc mở phòng thí nghiệm chung với ngành công nghiệp bán dẫn.",
    "Nhóm phát triển game độc lập tại Brazil ra mắt bản demo chạy trên phần cứng yếu.",
    "Một hãng dược tại Thụy Sĩ công bố kết quả thử nghiệm giai đoạn hai cho thuốc mới.",
    "Nhà máy thép tại Việt Nam lắp đặt hệ thống giám sát khí thải theo thời gian thực.",
    "Một liên minh ngân hàng châu Á thống nhất chuẩn thanh toán xuyên biên giới mới.",
    "Nhóm nghiên cứu tại Phần Lan công bố pin mặt trời trong suốt gắn trên kính cửa sổ.",
    "Một hãng logistics tại Mỹ mở rộng đội xe tải tự hành cho tuyến đường cao tốc.",
    "Nhà xuất bản tại Pháp thử nghiệm mô hình dịch thuật cho sách văn học cổ điển.",
]


def test_khong_con_gioi_han_1024():
    """Ong Chu 20/09 (LOW-296): khong co gioi han chu thich anh 1024 nua, vuot thi
    publish() tu tach thanh phan 1 + tin nhan rieng. Caption dai khong loi, khong
    canh bao do dai."""
    dai = CHUAN + "\n" + "\n".join(_CAU_KHAC_NHAU[:12])
    assert 1024 < len(dai) <= 2200, len(dai)
    loi, canh, _t = _kiem(dai)
    assert loi == [], loi
    assert not _co(canh, "1024"), canh
    assert not _co(canh, "giới hạn"), canh
    assert not hasattr(cc, "LIMIT"), "khong con hang so LIMIT 1024 trong caption_check"


def test_qua_2200_van_la_loi_tran_nen_tang():
    """2200 la gioi han Instagram/TikTok phia moat, khong lien quan viec Telegram
    tach caption — van chan nop."""
    dai = CHUAN + "\n" + "\n".join(_CAU_KHAC_NHAU)
    assert len(dai) > 2200, len(dai)
    loi, canh, _t = _kiem(dai)
    assert _co(loi, "2200"), loi
    assert not _co(canh, "1024"), canh


def test_ngan_khong_bi_nhac_do_dai():
    """Ong Chu 20/09: ngan hay dai khong quan trong, quan trong la thong tin day du.
    Caption ngan (van du so lieu) khong loi va khong canh bao do dai."""
    ngan = "Nvidia mở kho Nemotron, bản lớn nhất 340 tỷ tham số, theo hãng công bố đạt 86,2 điểm trên MMLU."
    assert len(ngan) < 700
    loi, canh, _t = _kiem(ngan)
    assert loi == [], loi
    assert not _co(canh, "ký tự"), canh
    assert not hasattr(cc, "BACKGROUND_SET")


# ---------------------------------------------------------------- ky tu / link
def test_em_dash_ca_hai_loai_deu_chan():
    for dau in ("—", "–"):
        loi, _c, _t = _kiem(CHUAN.replace(",", f" {dau}", 1))
        assert _co(loi, "em-dash"), (dau, loi)


def test_link_song_bi_chan_ke_ca_domain_tran():
    """Truoc day chi bat http/www; ten mien tran (z.ai) lot vi khong co scheme."""
    for link in ("https://z.ai/x", "www.z.ai", "z.ai", "openai.com", "docs.nvidia.com"):
        loi, _c, _t = _kiem(CHUAN + f"\nXem thêm tại {link} nhé.")
        assert _co(loi, "link sống"), (link, loi)


def test_link_da_defang_thi_cho_qua():
    """Tieu chuan bien tap: link trong noi dung viet dau cham thanh ' . '."""
    loi, _c, _t = _kiem(CHUAN + "\nXem thêm tại z . ai nhé.")
    assert not _co(loi, "link sống"), loi


def test_so_thap_phan_va_phien_ban_khong_bi_coi_la_link():
    loi, _c, _t = _kiem(CHUAN.replace("86,2", "86.2") + "\nGPT-4.5 và Llama 3.1 cũng vậy.")
    assert not _co(loi, "link sống"), loi


# ---------------------------------------------------------------- van phong
def test_cum_sao_rong_bi_cam():
    for cum in cc.STAR_EMPTY:
        loi, _c, _t = _kiem(CHUAN + f"\nĐây là điều {cum}.")
        assert _co(loi, "sáo rỗng", cum), (cum, loi)


def test_tu_thoi_phong_bi_chan():
    loi, _c, _t = _kiem(CHUAN.replace("thu hẹp khoảng cách", "tạo cuộc cách mạng"))
    assert _co(loi, "thổi phồng", "cuộc cách mạng"), loi


def test_lap_cum_sau_tu_la_loi():
    """Cung mot cum >= 6 tu hai lan trong 500 ky tu la phi pham nghiem trong."""
    lap = CHUAN + "\nNvidia mở kho mô hình Nemotron cho mọi nhà phát triển một lần nữa."
    loi, _c, _t = _kiem(lap)
    assert _co(loi, "Lặp ý"), loi


def test_nhieu_cau_mot_dong_chi_nhac():
    gop = CHUAN.replace("đăng ký.\nBản", "đăng ký. Bản")
    loi, canh, _t = _kiem(gop)
    assert loi == [], loi
    assert _co(canh, "xuống dòng riêng"), canh


def test_the_html_la_bi_chan_the_cho_phep_thi_khong():
    loi, _c, _t = _kiem(CHUAN.replace("Nvidia", "<div>Nvidia</div>"))
    assert _co(loi, "Thẻ HTML", "div"), loi
    for the in sorted(cc.CARD_ALLOW):
        loi, _c, _t = _kiem(CHUAN.replace("Nvidia", f"<{the}>Nvidia</{the}>"))
        assert not _co(loi, "Thẻ HTML"), (the, loi)


# ---------------------------------------------------------------- so lieu
def test_nguon_co_so_ma_caption_khong_co_la_loi():
    """Tin DeepSeek vision co bang 11 dong so, caption 0 con so — Miles chi doc
    3 cau tom tat cua Finn chu khong doc nguon."""
    khong_so = """Nvidia mở kho mô hình Nemotron cho mọi nhà phát triển.
Bản lớn nhất rất mạnh, theo hãng công bố ngang các mô hình đóng.
Điều này thu hẹp khoảng cách đáng kể với nhóm dẫn đầu.
Người làm sản phẩm dùng được ngay mà không cần đăng ký."""
    loi, _c, tin = _kiem(khong_so)
    assert _co(loi, "KHÔNG có con số"), loi
    assert tin["source_number_sentence_count"] == 2, tin


def test_caption_mot_so_thi_chi_nhac_them():
    mot_so = CHUAN.replace("340 tỷ tham số, theo hãng công bố đạt 86,2 điểm trên MMLU",
                           "340 tỷ tham số, theo hãng công bố")
    loi, canh, _t = _kiem(mot_so)
    assert loi == [], loi
    assert _co(canh, "mới dùng 1"), canh


def test_khong_co_tu_lieu_va_khong_so_thi_chi_nhac():
    khong_so = "Nvidia mở kho mô hình.\nBản lớn nhất rất mạnh, theo hãng.\nĐiều này thu hẹp khoảng cách.\nDùng được ngay."
    loi, canh, _t = cc.check(khong_so, "")
    assert loi == [] and _co(canh, "không có con số"), (loi, canh)


def test_so_khong_co_trong_tu_lieu_thi_nhac_la_bia():
    """Diem soat so lieu ma truoc phai nho Ada (LLM) doc lai. Chi NHAC vi doi don
    vi (2,5 ti / 2.5B) la thuong — chan cung se chan oan."""
    loi, canh, _t = _kiem(CHUAN.replace("86,2", "91,7"))
    assert loi == [], loi
    assert _co(canh, "KHÔNG thấy trong tư liệu", "91,7"), canh


def test_so_lieu_khong_ghi_tu_cong_bo_thi_nhac():
    loi, canh, _t = _kiem(CHUAN.replace("theo hãng công bố ", ""))
    assert loi == [], loi
    assert _co(canh, "tự công bố"), canh


def test_duoi_ba_cau_thi_nhac_cau_truc():
    ngan = "Nvidia mở kho mô hình Nemotron với 340 tỷ tham số, theo hãng công bố.\nAi cũng tải được."
    loi, canh, tin = _kiem(ngan)
    assert tin["sentence_count"] == 2
    assert _co(canh, "cấu trúc SOUL"), canh


# ---------------------------------------------------------------- dan nguon/anh (LOW-173)
def test_dong_dan_nguon_bi_chan():
    loi, _c, _t = _kiem(CHUAN + "\nNguồn: TechCrunch.")
    assert _co(loi, "dẫn nguồn", "Nguồn:"), loi


def test_dong_dan_anh_bi_chan():
    loi, _c, _t = _kiem(CHUAN + "\nẢnh: techcrunch chấm com.")
    assert _co(loi, "dẫn nguồn", "Ảnh:"), loi


def test_ma_nguon_mo_khong_bi_chan():
    """Loai tru giong _DAN_NGUON_SAI cua render_edu: khong bat 'mã nguồn mở'."""
    loi, _c, _t = _kiem(CHUAN.replace("mô hình", "mô hình mã nguồn mở", 1))
    assert not _co(loi, "dẫn nguồn"), loi


# ---------------------------------------------------------------- nguon tin giua cau (LOW-259)
def test_nguon_tin_van_phong_bao_chi_khong_bi_chan():
    """'Bốn nguồn tin nói...' la van phong bao chi binh thuong (four sources
    say), khac han dong dan nguon 'Nguồn tin: X'. Bug that: task t_6a8bca46
    (Miles) bi chan 3 lan cung mot loi roi ket vinh vien o blocked."""
    loi, _c, _t = _kiem(CHUAN + "\nBốn nguồn tin nói quân đội Mỹ lập kế hoạch chặn tàu.")
    assert not _co(loi, "dẫn nguồn"), loi


def test_dong_dan_nguon_tin_van_bi_chan():
    """Dong dan nguon that co dau hai cham/gach ngang van phai bi chan."""
    loi, _c, _t = _kiem(CHUAN + "\nNguồn tin: Reuters.")
    assert _co(loi, "dẫn nguồn", "Nguồn tin:"), loi


# ---------------------------------------------------------------- giong Jika (LOW-274)
def test_jika_bat_hoi_that_va_ban_trong_cau_that():
    """Cau that Ong Chu bao bo (19/09): 'Bần đạo hỏi thật: nếu là bạn, bạn rót ...'."""
    loi = cc.check_jika_voice("🏆 Mở bài.\n💬 Bần đạo hỏi thật: nếu là bạn, bạn rót không?")
    assert _co(loi, "bạn", "quý đạo hữu"), loi
    assert _co(loi, "hỏi thật"), loi


def test_jika_ban_dao_khong_bi_chan():
    """Ong Chu 19/09: khi buoc phai tu xung thi dung 'bần đạo'; cong khong chan
    ('tôi', 'mình' cung khong chan). Chi cau hoi mao dau moi bi bat."""
    ok = "🏆 Bần đạo chưa từng thấy hãng nào công bố số như thế.\nGiữa bài.\n💬 Quý đạo hữu nghĩ sao về chuyện này?"
    assert cc.check_jika_voice(ok) == []
    assert cc.check_jika_voice(ok.replace("Bần đạo", "Tôi").replace("chưa từng", "chưa từng")) == []


def test_jika_bat_moi_kieu_mao_dau_cau_hoi():
    for lead in ("Xin hỏi", "Cho hỏi", "Thử hỏi", "Hỏi nhỏ", "hỏi nhé"):
        assert _co(cc.check_jika_voice(f"{lead}: quý đạo hữu rót không?"), "mào đầu"), lead


def test_jika_quy_dao_huu_dat():
    ok = "🏆 Model mới ra lò.\nSố liệu do hãng công bố.\n💬 Quý đạo hữu còn tin điểm MMLU tới mức nào, hay giờ chỉ tin bài test của chính mình?"
    assert cc.check_jika_voice(ok) == []


def test_jika_khong_bat_oan_ban_be_ban_gai():
    """'bạn bè', 'bạn gái', 'bạn học' la danh tu trong tin, khong phai goi nguoi doc."""
    loi = cc.check_jika_voice("🏆 Bạn bè ông Musk và bạn gái cũ, bạn học cùng lớp đều có mặt.\n💬 Quý đạo hữu nghĩ đó là tình cờ?")
    assert not _co(loi, "bạn", "quý đạo hữu"), loi
    assert loi == [], loi


def test_jika_bai_mau_trong_soul_dat_cong():
    """Bai mau trong SOUL Jika phai qua chinh cong nop: khong bat oan, khong lech luat."""
    import re
    for org in ("blog", "dcgr"):
        t = (ROOT / "hermes" / "profiles" / org / "jika.SOUL.md").read_text(encoding="utf-8")
        mau = re.search(r"### Bài mẫu đúng giọng.*?```\n(.*?)```", t, re.S).group(1).strip()
        assert cc.check_jika_voice(mau) == [], (org, cc.check_jika_voice(mau))
        loi, _c, _t = cc.check(mau)
        assert loi == [], (org, loi)
        co_emoji = [d for d in mau.splitlines() if cc._EMOJI_HEAD.match(d)]
        assert len(co_emoji) == 2, f"{org}: chỉ câu mở và câu kết có emoji, đang có {len(co_emoji)}"


def test_jika_emoji_chi_o_cau_mo_va_ket():
    """Ong Chu 19/09: emoji chi o cau mo dau va cau ket, khong con o dau moi cau."""
    dung = "🏆 Mở bài.\nCâu giữa.\nCâu giữa nữa.\n💬 Quý đạo hữu nghĩ sao về chuyện này?"
    assert cc.check_jika_voice(dung) == []
    moi_cau = "🏆 Mở bài.\n📦 Câu giữa.\n💬 Quý đạo hữu nghĩ sao về chuyện này?"
    assert _co(cc.check_jika_voice(moi_cau), "câu giữa bài"), cc.check_jika_voice(moi_cau)


def test_jika_thieu_emoji_mo_hoac_ket_la_loi():
    loi = cc.check_jika_voice("Mở bài không emoji.\nCâu giữa.\nKết không emoji.")
    assert _co(loi, "Câu mở đầu"), loi
    assert _co(loi, "Câu kết"), loi


def test_jika_emoji_mo_va_ket_trung_nhau_la_loi():
    loi = cc.check_jika_voice("💬 Mở bài.\nCâu giữa.\n💬 Quý đạo hữu nghĩ sao?")
    assert _co(loi, "trùng nhau"), loi


def test_jika_emoji_co_the_html_va_variation_selector():
    """<b> boc dau dong va emoji co U+FE0F (🕳️) van duoc nhan la emoji."""
    loi = cc.check_jika_voice("<b>🕳️ Mở bài.</b>\nGiữa.\n💬 Quý đạo hữu nghĩ sao?")
    assert loi == [], loi


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
