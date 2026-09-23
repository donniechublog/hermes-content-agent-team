#!/usr/bin/env python3
"""Trinh bay mach lac cua caption (LOW-379/LOW-380, Ong Chu 23/09/2026).

Ong Chu: *"quan trong nhat la trinh bay mach lac, bullet hay emoji thi cung chi
la phan them"*. Tep nay neo vao DUNG HAI BAI Ong Chu chi ra cung ngay, chep
nguyen van tu `state/<brand>/prepare/<draft>/caption.txt` tren may chu:

  KHEN  microchip-hoan-tat-thau-tom-cong-ty-c-dre-donniechublog (Miles 22/09)
  CHE   grok-4-7-kite-donniechublog (Jika 22/09)

VI SAO CHEP CA BAI THAT VAO DAY thay vi dung mau rut gon: lan chan doan dau tien
23/09 da chon nham thuoc do — "ty le dong trong / so dong" — va thuoc do do cham
bai KHEN 0,4, tuc la danh truot chinh bai Ong Chu khen. Chi co bai that moi lo ra
dieu do. Bai KHEN o day la cai chan cong khong duoc chan oan.

Chay:  venv/bin/python tests/test_caption_spacing.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import caption_check as cc  # noqa: E402

# --------------------------------------------------------------- hai bai moc
# Bai KHEN: doan 1-2 cau, cum bullet dinh nhau, khong mot emoji nao.
KHEN = """Cộng đồng hơn 10.000 lập trình viên cùng hơn 100 khách hàng phần cứng vừa đổi chủ sau một thỏa thuận M&A kín tiếng.
Tập đoàn bán dẫn Microchip Technology đã ký kết và hoàn tất thâu tóm Hailo, công ty khởi nghiệp từ Israel chuyên về chip tăng tốc <b>EDGE AI</b>, tức trí tuệ nhân tạo xử lý trực tiếp tại thiết bị biên.

Thỏa thuận này bổ sung trực tiếp năng lực xử lý suy luận mô hình AI vào các dải sản phẩm vi điều khiển, vi mạch logic khả trình FPGA và hệ thống trên một vi mạch SoC của Microchip.
Trước đó, tập đoàn này cũng từng mua lại hãng Neuronix AI Labs nhằm tối ưu hóa mạng nơ-ron trên chip FPGA.

Danh mục phần cứng tiếp quản từ thương vụ gồm ba dòng sản phẩm chính:
• Hailo-8 tập trung tăng tốc các tác vụ thị giác máy tính và ứng dụng điều khiển robot.
• Hailo-10 với phiên bản Hailo-10H ra mắt tháng 6/2025, cho phép chạy trực tiếp mô hình ngôn ngữ lớn LLM và mô hình thị giác VLM ngay trên thiết bị biên mà không cần máy chủ đám mây.
• Hailo-15 cung cấp năng lực xử lý hình ảnh và video thông minh đa luồng.

Mặt khác, tổng giá trị tài chính thực tế của thương vụ thâu tóm này vẫn chưa được hai bên tiết lộ.

Bước đi mua lại giúp Microchip củng cố danh mục bán dẫn chuyên dụng cho thị trường thiết bị rìa mạng ngày càng nóng.
Năng lực tự chạy suy luận AI tạo sinh cục bộ đang trở thành cấu hình chuẩn mực cho phần cứng nhúng thế hệ mới."""

# Bai CHE: hook + 8 cau dinh lien mot khoi + cau ket.
CHE = """🎯 Tăng vọt 40% tham số lên mức 2,1 nghìn tỷ, nhưng điểm thi thực chiến lại chỉ đứng lưng chừng bảng tổng sắp.

xAI vừa phát hành <b>Grok 4.7</b>, mở rộng mô hình nền so với mức 1,5 nghìn tỷ tham số của bản 4.6 trước đó nhưng giữ nguyên giá gọi API ở mức 2 USD trên triệu token nạp vào và 6 USD mỗi triệu token tạo ra.
Trên bảng đánh giá độc lập Artificial Analysis Intelligence Index v4.3.2 gồm 10 bài đo, mô hình chỉ đạt 46 điểm và nằm ở nhóm giữa.
Ở bài kiểm tra Terminal-Bench 4.0, bản 4.7 chỉ ghi được 26%, thua xa mức 60% của GPT-6 Astra và 55% của Claude Fable 5.1.
Xét về chi phí tác vụ, mô hình đắt hơn GPT-6 Astra lẫn Claude Sonnet 5, đồng thời xếp sau Fable 5.1 khi đối thủ này dẫn đầu ở mọi mốc giá so sánh.
Trên thước đo GDPval, hệ thống đạt 1695 điểm và ở một phép đo khác ghi 1657 điểm so với 1678 điểm của Fable 5.1.
Hãng tự công bố mô hình đứng đầu CursorBench 4.0 về hiệu năng trên giá thành nhờ kéo dài thời gian chạy reinforcement learning cho các tác vụ suy luận sâu.
Về phòng vệ an toàn, xAI dựng lớp kiểm soát mới giúp chặn rủi ro sinh học ở mức 62,4% trên LatchBio và chỉ lọt 3,3% prompt nguy hiểm trên HackerBench v0.3.
Bản phát hành chính thức kèm bộ benchmark năng lực chi tiết cho thấy bài toán đánh đổi quen thuộc: nhồi thêm hàng trăm tỷ tham số vào mô hình chưa chắc đã giúp qua mặt đối thủ ở các tác vụ môi trường dòng lệnh phức tạp.

💬 Quý đạo hữu thấy mức chi phí nạp vào tạo ra cho khối tham số này đã đủ hấp dẫn để đổi agent lập trình chưa?"""


def _co(ds, *manh):
    return any(all(x in d for x in manh) for d in ds)


# ------------------------------------------------------- do khoi van xuoi
def test_hai_bai_moc_do_ra_dung_con_so():
    """Hai bai gan bang nhau ve SO dong trong (4 va 2) — thu tach chung la do dai
    KHOI van xuoi. Test nay khoa lai chinh cai thuoc do do."""
    assert cc.longest_prose_block(KHEN) == 2, cc.longest_prose_block(KHEN)
    assert cc.longest_prose_block(CHE) == 8, cc.longest_prose_block(CHE)


def test_bai_khen_khong_bi_chan_oan():
    """Chan cong: bai Ong Chu goi la 'rat chuan muc' phai qua sach, khong mot loi.

    Day la test quan trong nhat cua tep. Thuoc do dau tien ('ty le dong trong')
    cham bai nay 0,4 va se da no ve — cong nao chan bai nay la cong sai."""
    loi, _canh, _tin = cc.check(KHEN)
    assert loi == [], loi


def test_bai_che_bi_chan():
    loi, _canh, _tin = cc.check(CHE)
    assert _co(loi, "dòng văn xuôi dính liền"), loi


def test_cum_bullet_dinh_nhau_khong_tinh_la_khoi():
    """Bullet dinh nhau la DUNG khuon (xem bai KHEN) — chen dong trong vao giua
    cac gach dau dong moi la sai. Sau bullet lien tiep van phai qua."""
    bullet = "Ba dòng sản phẩm chính:\n" + "\n".join(f"• Dòng số {i} làm việc của nó." for i in range(6))
    assert cc.longest_prose_block(bullet) == 1, cc.longest_prose_block(bullet)
    for dau in ("•", "-", "*", "1."):
        cum = "Danh sách:\n" + "\n".join(f"{dau} Mục {i} nói một chuyện." for i in range(6))
        assert cc.longest_prose_block(cum) <= 1, (dau, cc.longest_prose_block(cum))


def test_nguong_chan_tu_5_dong_tro_len():
    """SOUL day 1-3 cau mot doan, cong chi chan tu 5 dong dinh lien: day chat,
    chan long. Mot bai 4 dong hoi dai khong bi da ve (vai chi duoc sua 2 lan)."""
    cau = "Hãng công bố một con số mới trong quý này {}.\n"
    for n, cho_phep in ((3, True), (4, True), (5, False), (9, False)):
        t = "".join(cau.format(i) for i in range(n))
        assert (cc.longest_prose_block(t) <= cc.MAX_PROSE_BLOCK) is cho_phep, (n, t)


def test_dong_trong_cat_khoi():
    """Cung 8 cau, chia doan thi qua — chung minh cong do CACH TRINH BAY chu
    khong do do dai bai."""
    cau = [f"Hãng công bố con số thứ {i} trong quý này." for i in range(8)]
    dinh = "\n".join(cau)
    chia = "\n\n".join("\n".join(cau[i:i + 2]) for i in range(0, 8, 2))
    assert cc.longest_prose_block(dinh) == 8
    assert cc.longest_prose_block(chia) == 2


# ------------------------------------------- emoji dau danh sach (LOW-380)
_MO = "🎯 Một con số lớn mở đầu bài viết này cho người đọc dừng lại.\n"
_KET = "\n💬 Quý đạo hữu thấy con số đó đã đủ thuyết phục chưa?"


def test_bullet_mang_emoji_khong_bi_cong_jika_da_ve():
    """LOW-380: emoji dau gach dau dong la 'phan them' Ong Chu cho phep. Truoc
    23/09 cong nay chan that — Jika viet dung khuon liet ke cung bi da ve."""
    cap = (_MO + "\nBa điểm chính của thương vụ:\n"
           "• 📊 Điểm thi đạt 46 trên bảng đánh giá độc lập.\n"
           "• 💸 Giá gọi API giữ nguyên 2 USD mỗi triệu token.\n"
           "• 🧪 Lớp an toàn chặn 62,4% rủi ro sinh học.\n" + _KET)
    assert cc.check_jika_voice(cap) == [], cc.check_jika_voice(cap)


def test_emoji_lam_gach_dau_dong_cung_duoc_mien():
    """Khuon 'moi y lon mo bang MOT emoji' cua SOUL Miles: emoji CHINH LA gach
    dau dong, khong co dau • nao."""
    cap = (_MO + "\nBa điểm chính của thương vụ:\n"
           "📊 Điểm thi đạt 46 trên bảng đánh giá độc lập.\n"
           "💸 Giá gọi API giữ nguyên 2 USD mỗi triệu token.\n"
           "🧪 Lớp an toàn chặn 62,4% rủi ro sinh học.\n" + _KET)
    assert cc.check_jika_voice(cap) == [], cc.check_jika_voice(cap)


def test_emoji_le_loi_giua_van_xuoi_van_la_loi():
    """LOW-274 khong bi noi long: mot dong emoji don doc giua van xuoi khong phai
    danh sach, va do dung la thu Ong Chu bo 19/09."""
    cap = (_MO + "\nHãng công bố một con số mới trong quý này.\n"
           "📊 Điểm thi đạt 46 trên bảng đánh giá độc lập.\n"
           "Con số đó thấp hơn hẳn đối thủ cùng tầm giá.\n" + _KET)
    assert _co(cc.check_jika_voice(cap), "Emoji chỉ đặt ở câu mở đầu và câu kết"), cc.check_jika_voice(cap)


def test_emoji_dau_moi_cau_van_bi_chan():
    """Kieu truoc LOW-274 (emoji o dau MOI cau, khong phai danh sach) phai van
    hong: dong trong sau hook cat khoi, nen cum van xuoi ben duoi khong duoc
    coi la mot danh sach."""
    cap = (_MO + "\n🤖 Hãng công bố một con số mới trong quý này.\n"
           "📉 Con số đó thấp hơn hẳn đối thủ cùng tầm giá.\n"
           "🧾 Bản phát hành kèm bộ benchmark chi tiết.\n" + _KET)
    loi = cc.check_jika_voice(cap)
    assert _co(loi, "Emoji chỉ đặt ở câu mở đầu và câu kết"), loi


if __name__ == "__main__":
    n = 0
    for ten, ham in sorted(globals().items()):
        if ten.startswith("test_") and callable(ham):
            ham()
            n += 1
            print(f"  ok  {ten}")
    print(f"\n{n} test DAT.")
