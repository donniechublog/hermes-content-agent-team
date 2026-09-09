#!/usr/bin/env python3
"""Cong chan caption cua Miles (`caption_check.kiem`).

Day la cong CUOI CUNG truoc khi mot bai vao hang duyet, va la thu Ong Chu doc
tren kenh. 103 dong, 14 cong, thuan (chuoi vao, bo ba ra) — ma truoc 07/09/2026
chi co helper `so_la` duoc test, con `kiem` thi khong. Moi cong o day la mot
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
    return cc.kiem(caption, tu_lieu)


def _co(ds, *manh):
    return any(all(x in d for x in manh) for d in ds)


# ---------------------------------------------------------------- duong hop le
def test_caption_chuan_khong_loi():
    loi, canh, tin = _kiem()
    assert loi == [], loi
    assert tin["so_cau"] == 4 and tin["so_trong_caption"] >= 2, tin
    # Duoi 700 ky tu chi la NHAC, khong chan.
    assert not any("MAT DAU" in c for c in canh)


def test_caption_rong_la_loi_duy_nhat():
    assert cc.kiem("   \n ", TU_LIEU) == (["Caption rỗng."], [], {})


# ---------------------------------------------------------------- dau tieng Viet
def test_mat_dau_la_loi_nang():
    """802 ky tu khong mot dau nao sau khi doi provider — khong ai thay cho toi
    khi doc ky. Loi nang hon thieu so vi bai khong dang duoc."""
    khong_dau = "Nvidia mo kho mo hinh Nemotron cho moi nha phat trien.\nBan lon nhat co 340 ty tham so.\nDieu nay thu hep khoang cach."
    loi, _c, tin = _kiem(khong_dau)
    assert _co(loi, "MAT DAU"), loi
    assert tin["ty_le_dau"] < cc.NGUONG_DAU


def test_nguong_dau_thap_hon_audition_co_y():
    """0.12 thap hon 0.15 cua model_audition: caption nhieu ten rieng tieng Anh
    keo ty le xuong. Hai nguong khac nhau la chu dich."""
    assert cc.NGUONG_DAU == 0.12


def test_ty_le_dau_khong_tinh_the_html():
    """<b>...</b> la chu Latin khong dau, khong duoc keo ty le xuong."""
    co_the = CHUAN.replace("Nvidia", "<b>Nvidia</b>").replace("Nemotron", "<code>Nemotron</code>")
    assert _kiem(co_the)[0] == []


# ---------------------------------------------------------------- do dai
def test_qua_1024_la_loi_vi_telegram_tach_anh_khoi_chu():
    dai = CHUAN + "\n" + ("Thêm một câu nữa để kéo dài caption ra. " * 18)
    assert 1024 < len(dai) <= 2200, len(dai)
    loi, _c, _t = _kiem(dai)
    assert _co(loi, "vượt giới hạn 1024"), loi


def test_qua_2200_bao_tran_nen_tang_chu_khong_phai_1024():
    dai = CHUAN + "\n" + ("Thêm một câu nữa để kéo dài caption ra. " * 50)
    assert len(dai) > 2200
    loi, _c, _t = _kiem(dai)
    assert _co(loi, "2200") and not _co(loi, "vượt giới hạn 1024"), loi


def test_duoi_700_chi_nhac_con_cho():
    loi, canh, _t = _kiem()
    assert loi == []
    assert _co(canh, "chưa dùng"), canh


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
    for cum in cc.SAO_RONG:
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
    for the in sorted(cc.THE_CHO_PHEP):
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
    assert tin["cau_so_trong_nguon"] == 2, tin


def test_caption_mot_so_thi_chi_nhac_them():
    mot_so = CHUAN.replace("340 tỷ tham số, theo hãng công bố đạt 86,2 điểm trên MMLU",
                           "340 tỷ tham số, theo hãng công bố")
    loi, canh, _t = _kiem(mot_so)
    assert loi == [], loi
    assert _co(canh, "mới dùng 1"), canh


def test_khong_co_tu_lieu_va_khong_so_thi_chi_nhac():
    khong_so = "Nvidia mở kho mô hình.\nBản lớn nhất rất mạnh, theo hãng.\nĐiều này thu hẹp khoảng cách.\nDùng được ngay."
    loi, canh, _t = cc.kiem(khong_so, "")
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
    assert tin["so_cau"] == 2
    assert _co(canh, "cấu trúc SOUL"), canh


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
