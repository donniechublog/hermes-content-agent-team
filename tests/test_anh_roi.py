#!/usr/bin/env python3
"""LOW-47: ảnh RỐI không được ưu tiên, buộc dùng thì nền chữ phải đặc.

Ông Chủ 13/09/2026: *"không ưu tiên sử dụng tất cả những ảnh nhìn rối, trong
trường hợp buộc phải dùng, thì lớp nền của text phải làm cho nghiêm chỉnh, đừng
nham nhở"*. Bộ Anthropic/Nvidia IPO có ba ảnh rối lọt qua cổng LIEN_QUAN: splash
"Claude" còn "loading chart...", đồ hoạ "Nvidia Weighs $10B..." in chìm sau câu
quote, tiêu đề báo Nga RBC.

Bốn phần, mỗi phần có ví dụ ĐÚNG-PHẢI-QUA đi kèm SAI-PHẢI-CHẶN:
  1. vision hỏi thêm dòng ROI, trả qua `ket_qua` mà không đổi số phần tử tuple;
  2. `phan_loai`: ảnh rối không làm bìa, có ghi chú đầu dòng;
  3. `nop_chung.kiem_anh_roi`: chỉ chặn khi CÒN ảnh sạch thật sự thay được;
  4. nền chữ đặc ở carousel và thẻ Ethan.

Chạy:  venv/bin/python tests/test_anh_roi.py
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw  # noqa: E402

import chuan_bi.nhin as nhin  # noqa: E402
from tam import so_tam  # noqa: E402


class _Resp:
    def __init__(self, txt: str):
        self._b = json.dumps({"choices": [{"message": {"content": txt}}]}).encode()

    def read(self):
        return self._b


def _anh_tam(tmp, ten="a.png", w=1000, h=1250, tone=(30, 30, 40), seed=3):
    im = Image.new("RGB", (w, h), tone)
    d = ImageDraw.Draw(im)
    b = seed
    for x in range(0, w, 37):
        for y in range(0, h, 41):
            b = (b * 1103515245 + 12345) % 2147483648
            d.rectangle([x, y, x + 10 + b % 25, y + 10 + (b // 9) % 25],
                        fill=tuple(min(255, c + b % 180) for c in tone))
    p = Path(tmp) / ten
    im.save(p)
    return p


def _hoi_vision(tra_loi, **k):
    """Goi mo_ta_anh voi router gia; tra (ket qua, ket_qua dict, cau hoi da gui)."""
    gui = {}

    def _goi(req, _ngu=None):
        gui["hoi"] = json.loads(req.data)["messages"][0]["content"][0]["text"]
        return _Resp(tra_loi)

    kq = {}
    with tempfile.TemporaryDirectory() as t, \
            mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}), \
            mock.patch.object(nhin, "_goi_router", side_effect=_goi):
        p = _anh_tam(t)
        ra = nhin.mo_ta_anh(str(p), "Nvidia rót 10 tỷ USD vào IPO Anthropic", ket_qua=kq, **k)
    return ra, kq, gui.get("hoi", "")


# ---------------------------------------------------------------- 1. vision
def test_vision_hoi_them_dong_roi_va_doc_ra():
    ra, kq, hoi = _hoi_vision("MO_TA: đồ hoạ tin tức nhiều chữ.\nLIEN_QUAN: co\nROI: co")
    assert "DUNG 3 dong" in hoi and "ROI:" in hoi, hoi
    assert ra == ("đồ hoạ tin tức nhiều chữ.", True)       # tuple van 2 phan tu
    assert kq["roi"] is True


def test_vision_anh_sach_la_false():
    _ra, kq, _hoi = _hoi_vision("MO_TA: biển hiệu trụ sở Nvidia.\nLIEN_QUAN: có\nRỐI: không")
    assert kq["roi"] is False


def test_vision_khong_tra_dong_roi_thi_none_khong_doan():
    _ra, kq, _hoi = _hoi_vision("MO_TA: ảnh.\nLIEN_QUAN: co")
    assert kq["roi"] is None


def test_vision_hoi_them_cua_bob_van_ba_phan_tu():
    ra, kq, hoi = _hoi_vision("MO_TA: ảnh.\nLIEN_QUAN: co\nROI: khong\nMOOD: vui",
                              hoi_them="tâm trạng ảnh", nhan_them="MOOD")
    assert "DUNG 4 dong" in hoi, hoi
    assert ra == ("ảnh.", True, "vui")
    assert kq["roi"] is False


# ---------------------------------------------------------------- 2. phan_loai
def test_phan_loai_anh_roi_khong_lam_bia_va_ghi_chu_dau_dong():
    def _gia(path, tieu_de, hang="", **k):
        k["ket_qua"]["roi"] = True
        return ("đồ hoạ nhiều chữ", True)

    with tempfile.TemporaryDirectory() as t:
        p = _anh_tam(t, tone=(20, 20, 25))                  # toi, doc: binh thuong duoc goi y bia
        a = {"ma": "A1", "goc": str(p)}
        with mock.patch.object(nhin, "mo_ta_anh", side_effect=_gia), \
                mock.patch.object(nhin.luat_anh, "dem_mat", return_value=0):
            nhin.phan_loai(a, Path(t), "Tin gì đó")
    assert a["roi"] is True
    assert not any(str(d).startswith("bìa") for d in a["dung"]), a["dung"]
    assert a["dung"], "anh roi van dung duoc lam than khi het anh sach"
    assert a["ghi_chu"][0].startswith("⚠️ ẢNH RỐI"), a["ghi_chu"]


# ---------------------------------------------------------------- 3. kiem_anh_roi
def _muc(tmp, ma, seed, **k):
    a = {"ma": ma, "goc": str(_anh_tam(tmp, f"{ma}.png", seed=seed)), "dung": ["thân"],
         "lien_quan": True, "roi": False, "loai": "anh", "mat": 0, "ngang": False, "h": 1250}
    a.update(k)
    return a


def test_con_anh_sach_chua_dung_thi_chan_anh_roi():
    import nop_chung as nc
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh = {"A1": _muc(t, "A1", 1, roi=True), "A2": _muc(t, "A2", 2)}
        loi = nc.kiem_anh_roi(anh, {"A1": "slide 5"}, {"draft_id": "tin", "link": "https://x/y"})
    assert loi and "slide 5" in loi[0] and "A2" in loi[0], loi


def test_het_anh_sach_thi_duoc_dung_anh_roi():
    import nop_chung as nc
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh = {"A1": _muc(t, "A1", 1, roi=True), "A2": _muc(t, "A2", 2)}
        loi = nc.kiem_anh_roi(anh, {"A1": "slide 5", "A2": "slide 6"},
                              {"draft_id": "tin", "link": "https://x/y"})
    assert loi == [], loi


def test_khong_tinh_la_sach_neu_khong_the_dung_mot_minh():
    """Chặn oan là vai kẹt vòng: ứng viên phải thật sự thay được, không cần khai thêm."""
    import nop_chung as nc
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh = {"A1": _muc(t, "A1", 1, roi=True),
               "A2": _muc(t, "A2", 2, roi=None),                       # chua ai noi la sach
               "A3": _muc(t, "A3", 3, mat=1),                          # mat nguoi
               "A4": _muc(t, "A4", 4, loai="chart"),
               "A5": _muc(t, "A5", 5, ngang=True, h=600, cat_ngang_ok=True),   # qua thap
               "A6": _muc(t, "A6", 6, ngang=True, h=900, cat_ngang_ok=False),  # co chu
               "A7": _muc(t, "A7", 7, lien_quan=False),
               "A8": _muc(t, "A8", 8, dung=[])}
        loi = nc.kiem_anh_roi(anh, {"A1": "slide 2"}, {"draft_id": "tin", "link": "https://x/y"})
    assert loi == [], loi


def test_anh_sach_da_len_bai_khac_khong_tinh():
    import luat_anh
    import nop_chung as nc
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh = {"A1": _muc(t, "A1", 1, roi=True), "A2": _muc(t, "A2", 2)}
        luat_anh.ghi_da_dung(anh["A2"]["goc"], "tin-khac", "dre", "https://x/khac")
        loi = nc.kiem_anh_roi(anh, {"A1": "slide 2"}, {"draft_id": "tin", "link": "https://x/y"})
    assert loi == [], loi


def test_dre_nop_gan_roi_cho_slide_va_chan_khi_con_anh_sach():
    import test_spec_dre as ts
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = ts._du(t)
        m["anh"][1]["roi"] = True                              # A2 o slide 2
        ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert loi == [], loi                                  # khong co anh sach nao thay
        assert ra["slides"][0].get("roi") is True
        assert not ra["slides"][1].get("roi")
        m["anh"].append(ts._anh(wd, "A6", 1000, 1250, dung=["thân"], roi=False))
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert ts._co(loi, "slide 2", "RỐI", "A6"), loi


# ---------------------------------------------------------------- 4. nen chu dac
def _canvas_vung(W, H, vung, nen=(40, 40, 40)):
    """Canvas co cac DAI ngang `vung` = [(y0, y1, kieu)]:
    "chu" = soc manh day dac (nhu chu in san), "anh" = soc thua tuong phan
    vua (nhu chi tiet anh chup); ngoai cac dai la mau phang (khoang lang)."""
    im = Image.new("RGBA", (W, H), (*nen, 255))
    d = ImageDraw.Draw(im)
    for y0, y1, kieu in vung:
        if kieu == "chu":
            # net 4px cach 4px, trang tren toi: sau khi thu nho 4 lan van con
            # xen ke sang/toi tung diem — nhu chu in san that (A9: 25-47)
            for x in range(0, W, 8):
                d.rectangle([x, y0, x + 3, y1], fill=(250, 250, 250, 255))
        else:
            for x in range(0, W, 40):
                d.rectangle([x, y0, x + 19, y1], fill=(110, 110, 110, 255))
    return im


def _la_nen(canvas, y, bg):
    return all(canvas.getpixel((x, y))[:3] == tuple(bg) for x in (0, 301, 777, canvas.width - 1))


def test_nguong_phan_biet_chu_in_san_voi_anh_chup():
    """Hai loại dải giả phải rơi đúng hai phía ngưỡng NEN_ROI_CHU, không thì
    các test dưới đo sai thứ."""
    import card
    e = card._nang_luong_hang(_canvas_vung(1080, 400, [(0, 199, "chu"), (200, 399, "anh")]))
    assert min(e[20:180]) >= card.NEN_ROI_CHU, min(e[20:180])
    assert card.NEN_ROI_LANG <= max(e[220:380]) < card.NEN_ROI_CHU, max(e[220:380])


def test_moc_nen_dac_leo_len_khoang_lang_tren_chu_in_san():
    """Đo thật A9 carousel: chữ in sẵn 690–989, khe lặng 630–689, phía trên là
    ảnh chụp. Nền đặc phủ trọn chữ in sẵn, dải chuyển nằm trong khe lặng."""
    import card
    cv = _canvas_vung(1080, 1350, [(0, 600, "anh"), (700, 980, "chu")])
    dac, top = card._moc_nen_dac(cv, 990)
    assert 690 <= dac <= 700, dac
    assert 600 <= top < dac, (top, dac)


def test_moc_nen_dac_khe_hep_ngay_duoi_chu_in_san_khong_duoc_dung():
    """Đo thật thẻ Ethan A9: chữ in sẵn 780–1109, khe 1110–1136 ngay trên chữ
    của ta. Dừng ở khe đó là tiêu đề in sẵn lộ nguyên — phải leo qua."""
    import card
    cv = _canvas_vung(1200, 1500, [(0, 650, "anh"), (780, 1100, "chu")])
    dac, top = card._moc_nen_dac(cv, 1136)
    assert 770 <= dac <= 780, dac


def test_moc_nen_dac_cham_tran_thi_ve_khoang_lang_khong_cat_chu_in_san():
    """Đo thật A9 slide quote: khe lặng 627–650 ngay trên khung quote, phía trên
    lại có chữ in sẵn "$10B INVESTMENT" vắt qua trần 40% (540). Dừng ở trần là
    dải chuyển cắt nửa chữ — phải quay về khe lặng cao nhất đã gặp."""
    import card
    cv = _canvas_vung(1080, 1350, [(0, 480, "anh"), (500, 560, "chu"), (690, 980, "chu")])
    dac, top = card._moc_nen_dac(cv, 650)
    assert dac == 650, dac
    assert 561 <= top < dac, (top, dac)                  # dai chuyen khong cham dai chu 500-560


def test_moc_nen_dac_chu_ta_nam_duoi_khoang_lang_rong_thi_giu_nguyen_vi_tri():
    import card
    cv = _canvas_vung(1080, 1350, [(0, 500, "anh")])
    dac, top = card._moc_nen_dac(cv, 990)
    assert dac == 990 and 990 - card.NEN_ROI_TAN <= top < 990, (dac, top)


def test_moc_nen_dac_khong_co_khoang_lang_thi_dung_o_tran_40_phan_tram():
    import card
    cv = _canvas_vung(1080, 1350, [(0, 1349, "chu")])
    dac, top = card._moc_nen_dac(cv, 990)
    assert dac == int(1350 * card.NEN_ROI_TRAN), dac
    assert top == dac - card.NEN_ROI_TAN_CUNG, top


def test_carousel_anh_roi_phu_tron_chu_in_san_giu_anh_phia_tren():
    import carousel
    carousel.dat_nen("toi")
    cv = _canvas_vung(carousel.W, carousel.H, [(0, 600, "anh"), (700, 980, "chu")])
    truoc = cv.copy()
    carousel._lop_neu_can(cv, cv.convert("RGB"), 1030, carousel.H, anh_roi=True)
    for y in (705, 800, 975, 1100, carousel.H - 1):
        assert _la_nen(cv, y, carousel.BG), (y, cv.getpixel((0, y)))
    assert cv.getpixel((3, 300)) == truoc.getpixel((3, 300)), "anh phia tren khong duoc dong"
    L = [cv.convert("L").getpixel((30, y)) for y in range(601, 700)]      # cot nen cua dai "anh"
    assert max(abs(L[i + 1] - L[i]) for i in range(len(L) - 1)) < 20, "khong co buoc nhay = khong co vach"


def test_carousel_anh_sach_giu_nguyen_lop_mo_cu():
    import carousel
    carousel.dat_nen("toi")
    canvas = Image.new("RGBA", (carousel.W, carousel.H), (10, 10, 10, 255))
    truoc = canvas.copy()
    carousel._lop_neu_can(canvas, canvas.convert("RGB"), 1000, carousel.H)
    assert canvas.tobytes() == truoc.tobytes(), "nen toi deu du tuong phan -> khong phu gi"


def test_card_nen_chu_nghiem_phu_tron_chu_in_san():
    import card
    card.dat_thuong_hieu("dcgr")
    cv = _canvas_vung(1200, 1500, [(0, 650, "anh"), (780, 1100, "chu")])
    truoc = cv.copy()
    card._nen_chu_nghiem(cv, 1160)
    for y in (790, 1000, 1499):
        assert _la_nen(cv, y, card.BG), (y, cv.getpixel((0, y)))
    assert cv.getpixel((3, 300)) == truoc.getpixel((3, 300))


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
