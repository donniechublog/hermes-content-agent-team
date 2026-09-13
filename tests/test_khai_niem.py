#!/usr/bin/env python3
"""Ảnh khái niệm (anh_khai_niem.py) — kỹ năng "nhắc Nhật thì tìm cờ Nhật, tin
compute thì tìm datacenter" mà Dre từng tự làm, nay engine làm thay (07/09/2026).

Ba hàm thuần, không mạng:
  - tu_khoa_heuristic  tiêu đề -> từ khoá; hỏng = tin không ảnh lại đi thẳng Kite.
  - loc_commons        lọc trang API Commons; hỏng = cờ vẽ CGI / logo lọt vào bìa.
  - nhan_khai_niem     siết nhãn; hỏng = ảnh cờ chui vào slide thân như ảnh của tin.

Chạy:  venv/bin/python tests/test_khai_niem.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import anh_khai_niem as k  # noqa: E402


def _tk(tieu_de, tom=""):
    return [x["tu_khoa"] for x in k.tu_khoa_heuristic(tieu_de, tom)]


def test_nuoc_va_chu_de_cung_ra():
    tk = _tk("Japan to invest $10B in AI compute, new data centers by 2027")
    assert tk[0] == "flag of Japan", tk
    assert "data center server racks" in tk, tk


def test_tinh_tu_nuoc_cung_ve_mot_co():
    assert _tk("Japanese startup raises funds")[0] == "flag of Japan"
    assert _tk("Tokyo firm builds GPU cluster")[0] == "flag of Japan"


def test_viet_tat_phan_biet_hoa_thuong():
    assert _tk("US chipmakers face export limits")[0] == "flag of United States"
    assert not any("United States" in t for t in _tk("Let us build chips"))


def test_chi_mot_nuoc_dung_dau_toi_da_ba_tu_khoa():
    tk = _tk("China and Japan race on nuclear-powered data centers and chips")
    assert sum(t.startswith("flag of") for t in tk) == 1, tk
    assert len(tk) <= k.TOI_DA_TU_KHOA


def test_tin_khong_khai_niem_thi_rong():
    assert _tk("OpenAI launches GPT-6") == []
    assert _tk("") == []


def test_tom_tat_cung_duoc_doc():
    assert "humanoid robot" in _tk("Figure ships", "the humanoid robot maker started deliveries")


def test_doc_tra_loi_llm_bo_rac_va_gioi_han():
    ra = k.doc_tra_loi_llm("KEYWORD: Tokyo skyline at night | capital\nblah\nKEYWORD: server racks\n"
                           "KEYWORD: server racks | trùng\nKEYWORD: a b c d e f g | quá dài\nKEYWORD: x | y")
    assert [x["tu_khoa"] for x in ra] == ["tokyo skyline at night", "server racks", "x"]
    assert ra[1]["ly_do"] == "gợi ý của model"
    assert k.doc_tra_loi_llm("") == [] and k.doc_tra_loi_llm(None) == []


def _pg(ten, w=1600, h=1200, mime="image/jpeg"):
    return {"title": "File:" + ten, "imageinfo": [{"width": w, "height": h, "mime": mime,
                                                  "thumburl": "https://u/" + ten.replace(" ", "_")}]}


def test_loc_commons_can_hai_tu_dac_trung_va_bo_do_hoa():
    pages = {str(i): p for i, p in enumerate([
        _pg("Japan Flag at Kennedy Space Center.jpg"),
        _pg("CGI Japan Flag.png", mime="image/png"),          # dựng máy
        _pg("Japan flag - variant.png", mime="image/png"),     # cờ vẽ
        _pg("Flag of Japan.svg", mime="image/svg+xml"),        # vector
        _pg("Japan Tokyo tower.jpg"),                          # thiếu "flag"
        _pg("Japanese flag small.jpg", w=500, h=300),          # bé
        _pg("Flag map of Japan.png", mime="image/png"),        # bản đồ phẳng
    ])}
    ra = k.loc_commons(pages, "flag of Japan")
    assert [c["alt"] for c in ra] == ["Commons: Japan Flag at Kennedy Space Center.jpg"], ra
    assert ra[0]["tu"] == "khai_niem" and ra[0]["khai_niem"]["tu_khoa"] == "flag of Japan"


def test_loc_commons_jpeg_truoc_png_roi_moi_den_kich_thuoc():
    pages = {"1": _pg("Big data center racks.png", 4000, 3000, "image/png"),
             "2": _pg("Small data center racks.jpg", 1000, 800),
             "3": _pg("Huge data center racks.jpg", 3000, 2000)}
    ra = k.loc_commons(pages, "data center server racks")
    assert [c["alt"] for c in ra] == ["Commons: Huge data center racks.jpg",
                                      "Commons: Small data center racks.jpg",
                                      "Commons: Big data center racks.png"]


def test_ten_loai_khong_bat_chuoi_con():
    """09/09/2026: "icon" trần nằm trong "sil-icon" nên MỌI ảnh silicon wafer bị
    bỏ — mà đó là từ khoá khái niệm của toàn bộ tin bán dẫn. "graph" nằm trong
    "photograph", "chart" nằm trong "Charterhouse"."""
    pages = {"1": _pg("12-inch silicon wafer.jpg"), "2": _pg("Silicon wafer closeup.jpg")}
    assert len(k.loc_commons(pages, "silicon wafer")) == 2
    assert not k.TEN_LOAI.search("aerial photograph of the campus")
    assert not k.TEN_LOAI.search("charterhouse square")
    # vẫn phải bắt đúng thứ nó sinh ra để bắt
    for x in ("app icon.png", "bar graph of sales.png", "chart of revenue.png", "company logo.png"):
        assert k.TEN_LOAI.search(x), x


def test_philippines_co_trong_bang_nuoc():
    """Bảng SEA có đủ 5 nước còn lại; thiếu Philippines nên tin "Philippines rót
    34 tỷ USD" không ra từ khoá nào (09/09/2026)."""
    assert _tk("Philippines plans $34B to catch up in the AI race")[0] == "flag of Philippines"


def test_loc_commons_rong_khi_khong_co_gi():
    assert k.loc_commons({}, "x") == [] and k.loc_commons(None, "x") == []


def _anh(**o):
    a = {"khai_niem": {"tu_khoa": "flag of Japan", "ly_do": "tin nhắc tới Japan"}, "loai": "anh",
         "mat": 0, "ngang": False, "lien_quan": True, "dung": ["bìa", "thân"],
         "ghi_chu": ["ảnh CHUNG của hãng từ Wikimedia Commons (trụ sở/sản phẩm), không phải ảnh của tin"]}
    a.update(o)
    return a


def test_nhan_khai_niem_chi_bia_khong_than():
    a = k.nhan_khai_niem(_anh())
    assert a["dung"] == ["bìa"]
    assert a["ghi_chu"][0].startswith("🧭 ẢNH KHÁI NIỆM") and "flag of Japan" in a["ghi_chu"][0]
    assert not any("ảnh CHUNG của hãng" in g for g in a["ghi_chu"])


def test_nhan_khai_niem_ngang_chi_ghep():
    a = k.nhan_khai_niem(_anh(ngang=True, dung=["ghép dọc với một ảnh ngang cùng tone", "cat_ngang: true"]))
    assert a["dung"] == ["ghép dọc với một ảnh ngang cùng tone"]


def test_nhan_khai_niem_chart_hoac_mat_thi_bo():
    assert k.nhan_khai_niem(_anh(loai="chart"))["dung"] == []
    a = k.nhan_khai_niem(_anh(mat=2))
    assert a["dung"] == [] and a["ghi_chu"][0].startswith("❌")


def test_nhan_khai_niem_giu_nguyen_khi_vision_da_loai():
    a = k.nhan_khai_niem(_anh(lien_quan=False, dung=[], ghi_chu=["❌ KHÔNG LIÊN QUAN BÀI (vision) → KHÔNG DÙNG"]))
    assert a["dung"] == [] and a["ghi_chu"][0].startswith("❌ KHÔNG LIÊN QUAN")


def test_loc_commons_bo_co_chien_va_bieu_tinh():
    pages = {"1": _pg("Rising Sun Flag of Japan JS Aishima.jpg"), "2": _pg("Japan flag protest Tokyo.jpg"),
             "3": _pg("Waving Japanese flag.jpg")}
    assert [c["alt"] for c in k.loc_commons(pages, "flag of Japan")] == ["Commons: Waving Japanese flag.jpg"]


def test_manifest_dem_chum_khai_niem_la_mot():
    """5 lá cờ không phải 5 slide: so_dung_duoc = ảnh riêng + tối đa 1 khái niệm."""
    import anh_chuan_bi as cb
    from pathlib import Path
    def _a(ma, kn=False):
        return {"ma": ma, "dung": ["bìa"], "lien_quan": True, "mien": "x", "tu": "x", "ti_le": 0.8,
                "goc_trai_sang": 50, "canh_ngan": 1000, "ngang": False, "loai": "anh",
                **({"khai_niem": {"tu_khoa": "flag of Japan"}} if kn else {})}
    anh = [_a("A1"), _a("A2", True), _a("A3", True), _a("A4", True)]
    m = cb.build_manifest("t", {"brand": "dcgr"}, "t", "http://x", {}, Path("/nonexist"), {}, Path("/tmp"),
                         anh, None, False, {}, {}, False, 5)
    assert m["so_dung_duoc"] == 2, m["so_dung_duoc"]
    assert m["goi_y_bia"][0] == "A1", m["goi_y_bia"]


def test_cau_hoi_vision_noi_ro_khong_phai_anh_cua_tin():
    c = k.cau_hoi_vision("Japan to invest", "flag of Japan")
    assert "KHONG phai anh cua tin" in c and "flag of Japan" in c and "LIEN_QUAN" in c


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
