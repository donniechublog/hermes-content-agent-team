#!/usr/bin/env python3
"""Phan co hoc cua hai script ghi manifest — `manifest_chung` va cac ham da
tach khoi `manifest_build.main` / `manifest_ghi.main`.

Vi sao dang o day: manifest la thu Ong Chu doc roi TRA LOI BANG SO. Sai o day
khong ra loi, no ra mot danh sach nhin binh thuong nhung so "2" tro toi bai
khac — va cac su co that trong repo deu dung kieu do: link "blank" cua Vera
(24/08, ba cap task chet), 4/8 muc mat vi chep URL sai mot ky tu (05/09),
manifest bi ghi de lam doi nghia so thu tu (06/09).

Chay:  venv/bin/python tests/test_manifest.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import manifest_chung as mc  # noqa: E402

from tam import bat_buoc_tam  # noqa: E402


# ------------------------------------------------------------ chon theo k
def test_chon_theo_k_dung_so_thu_tu_1_den_n():
    ds = [{"a": 1}, {"a": 2}, {"a": 3}]
    assert mc.chon_theo_k(1, ds, "x")[0] == {"a": 1}
    assert mc.chon_theo_k(3, ds, "x")[0] == {"a": 3}
    assert mc.chon_theo_k("2", ds, "x")[0] == {"a": 2}, "chuoi so cung phai nhan"


def test_chon_theo_k_ngoai_dai_thi_bao_ro_dai_hop_le():
    """Bao "k sai" ma khong noi dai nao thi vai doan tiep."""
    ds = [{"a": 1}, {"a": 2}]
    for k in (0, 3, -1, 99, None, "hai", ""):
        muc, loi = mc.chon_theo_k(k, ds, "muc 4")
        assert muc is None, (k, muc)
        assert "muc 4" in loi and "1..2" in loi, loi


def test_chon_theo_k_khong_bao_gio_lay_phan_tu_cuoi_bang_so_am():
    """`ds[-1]` la bai CUOI danh sach — im lang tra ve nham tin."""
    ds = [{"a": 1}, {"a": 2}, {"a": 3}]
    assert mc.chon_theo_k(-1, ds, "x")[0] is None


# ------------------------------------------------------------ don tom tat
def test_don_tom_tat_doi_em_dash_thanh_dau_phay():
    """Em-dash tren headline lot tiep xuong caption bai dang."""
    for dau in ("—", "–"):
        tom, canh = mc.don_tom_tat(f"Nvidia mở kho {dau} ai cũng tải được", "muc 1")
        assert tom == "Nvidia mở kho, ai cũng tải được", tom
        assert any("em-dash" in c for c in canh), canh


def test_don_tom_tat_khong_dung_toi_dau_gach_noi_binh_thuong():
    tom, canh = mc.don_tom_tat("GPT-5 Codex Max ra mắt", "muc 1")
    assert tom == "GPT-5 Codex Max ra mắt"
    assert canh == []


def test_don_tom_tat_canh_bao_dai_dung_nguong_15_tu():
    assert mc.don_tom_tat(" ".join(["từ"] * 15), "muc 1")[1] == []
    canh = mc.don_tom_tat(" ".join(["từ"] * 16), "muc 1")[1]
    assert len(canh) == 1 and "16 tu" in canh[0], canh


def test_don_tom_tat_canh_bao_luon_chi_ro_muc_nao():
    """Tren mot bao cao 8 tin, dong canh bao khong co nhan thi khong chi duoc ai."""
    for c in mc.don_tom_tat("Một câu — dài " + " ".join(["từ"] * 20), "bai: Nvidia")[1]:
        assert "bai: Nvidia" in c, c


def test_don_tom_tat_khong_no_voi_None():
    assert mc.don_tom_tat(None, "x") == ("", [])


def test_don_tom_tat_khong_cat_bot_chu():
    """CANH BAO chu khong cat: tin dai van co gia tri, cat la mat noi dung."""
    dai = " ".join(["từ"] * 40)
    assert mc.don_tom_tat(dai, "x")[0] == dai


# ------------------------------------------------------------ danh so / duong ra
def test_danh_so_theo_dung_thu_tu_hien_tai():
    items = [{"t": "a"}, {"t": "b"}, {"t": "c"}]
    assert [x["index"] for x in mc.danh_so(items)] == [1, 2, 3]


def test_duong_ra_moi_giu_thu_muc_va_duoi_tep():
    p = mc.duong_ra_moi(Path("/x/y/nova_candidates_2026-09-07.json"))
    assert p.parent == Path("/x/y")
    assert p.name.startswith("nova_candidates_2026-09-07_t") and p.suffix == ".json"
    assert p != Path("/x/y/nova_candidates_2026-09-07.json")


# ------------------------------------------------------------ manifest_build
def _c(link, title, partial=10, **k):
    d = {"link": link, "title": title, "source": "HN", "points": 100,
         "comments": 20, "via": "hn", "image_url": None, "score_partial": partial,
         "score_recency": 5, "score_spread": 3}
    d.update(k)
    return d


def _p(**k):
    d = {"category": "MODEL", "score_technical": 20, "score_relevance": 15,
         "score_reason": "r", "summary_vi": "Một mệnh đề ngắn"}
    d.update(k)
    return d


def test_gom_muc_cong_diem_tong_tu_ba_thanh_phan():
    import manifest_build as mb
    cands = [_c("https://a.vn/1", "Tin một", partial=12)]
    items, loi = mb.gom_muc([_p(k=1, score_technical=20, score_relevance=15)], cands)
    assert loi == [], loi
    assert items[0]["score"] == 12 + 20 + 15


def test_gom_muc_chan_vai_nop_trung_mot_tin():
    """Hay gap khi vai vua ghi `k` vua ghi `link`."""
    import manifest_build as mb
    cands = [_c("https://a.vn/1", "Tin một"), _c("https://b.vn/2", "Tin hai")]
    items, loi = mb.gom_muc([_p(k=1), _p(link="https://a.vn/1"), _p(k=2)], cands)
    assert len(items) == 2, [x["title"] for x in items]
    assert any("trung" in x for x in loi), loi


def test_gom_muc_van_nhan_link_cho_tuong_thich():
    import manifest_build as mb
    cands = [_c("https://a.vn/1?utm_source=x", "Tin một")]
    items, _loi = mb.gom_muc([_p(link="https://a.vn/1")], cands)
    assert len(items) == 1, "chuan hoa link khong khop"


def test_gom_muc_cat_diem_ngoai_dai_va_ghi_ro_da_sua():
    """Truoc 06/09/2026 diem ngoai dai chi ghi mot dong stderr roi VAN vao
    manifest, ma quet_nop nuot stderr khi rc=0 nen khong ai thay."""
    import manifest_build as mb
    cands = [_c("https://a.vn/1", "Tin một")]
    items, loi = mb.gom_muc([_p(k=1, score_technical=99, score_relevance=-5)], cands)
    assert items[0]["score_technical"] == 30 and items[0]["score_relevance"] == 0
    assert "script sua" in items[0]["score_reason"], items[0]["score_reason"]
    assert len(loi) == 2, loi


def test_gom_muc_diem_khong_phai_so_thanh_0_chu_khong_no():
    import manifest_build as mb
    cands = [_c("https://a.vn/1", "Tin một")]
    items, loi = mb.gom_muc([_p(k=1, score_technical="24 diem", score_relevance=None)], cands)
    assert items[0]["score_technical"] == 0 and items[0]["score_relevance"] == 0
    assert len(loi) == 2, loi


def test_gom_muc_category_la_thi_ve_TOOL_va_noi_ro():
    import manifest_build as mb
    cands = [_c("https://a.vn/1", "Tin một")]
    items, loi = mb.gom_muc([_p(k=1, category="VUI VE")], cands)
    assert items[0]["category"] == "TOOL"
    assert any("category khong hop le" in x for x in loi), loi


def test_gom_muc_nhan_ca_nhan_tieng_viet_lan_tieng_anh():
    """Bang cu chi co ban tieng Viet nen moi lan Finn nop deu bi bao sai."""
    import manifest_build as mb
    cands = [_c("https://a.vn/1", "Tin một"), _c("https://b.vn/2", "Tin hai")]
    items, loi = mb.gom_muc([_p(k=1, category="ENGINEERING"), _p(k=2, category="MÔ HÌNH")], cands)
    assert [x["category"] for x in items] == ["ENGINEERING", "MÔ HÌNH"], items
    assert loi == [], loi


def test_gom_muc_don_em_dash_cua_summary():
    import manifest_build as mb
    cands = [_c("https://a.vn/1", "Tin một")]
    items, loi = mb.gom_muc([_p(k=1, summary_vi="Mở kho — ai cũng tải")], cands)
    assert items[0]["summary_vi"] == "Mở kho, ai cũng tải"
    assert any("em-dash" in x for x in loi), loi


def test_cat_tran_giu_8_tin_diem_cao_nhat():
    import manifest_build as mb
    items = [{"link": f"https://a.vn/{i}", "title": f"T{i}", "score": i} for i in range(1, 13)]
    loi = []
    ra = mb.cat_tran(items, set(), loi)
    assert len(ra) == mb.TOI_DA_PICK
    assert [x["score"] for x in ra] == [12, 11, 10, 9, 8, 7, 6, 5]
    assert any("tran la 8" in x for x in loi), loi


def test_cat_tran_khong_tinh_muc_BAT_BUOC_vao_tran():
    """Muc BAT BUOC mang tu hom truoc co score_partial=0 nen LUON xep chot va
    LUON bi cat; cat xong thi buoc sau lai them BAN TRONG, bao cao do oan cho
    vai la bo sot dung tin no vua cham ky (06/09/2026)."""
    import bat_buoc
    import manifest_build as mb
    items = [{"link": f"https://a.vn/{i}", "title": f"T{i}", "score": i} for i in range(1, 13)]
    bb = {bat_buoc.chuan_link("https://a.vn/1")}
    ra = mb.cat_tran(items, bb, [])
    assert len(ra) == mb.TOI_DA_PICK + 1
    assert ra[0]["link"] == "https://a.vn/1", "muc BAT BUOC phai con"


# ------------------------------------------------------------ manifest_ghi
def test_muc_tu_nop_chan_link_khong_phai_URL():
    """Ngay 24/08 ca nam tin cua Vera deu la "blank": manifest nhin binh thuong,
    Ong Chu chon tin, roi vai dung anh moi phat hien khong co gi de tai."""
    import manifest_ghi as mg
    for xau in ("blank", "khong co", "a.vn/1", "ftp://a.vn/1", "  "):
        assert mg._muc_tu_nop({"title": "Tin một", "link": xau}, 1, [], "nova", "nova") is None, xau


def test_muc_tu_nop_thieu_title_thi_bo():
    import manifest_ghi as mg
    assert mg._muc_tu_nop({"link": "https://a.vn/1"}, 1, [], "nova", "nova") is None


def test_muc_tu_nop_suy_via_tu_ten_mien():
    """via = NGUON TIN, khong phai kenh phat hien."""
    import manifest_ghi as mg
    muc = mg._muc_tu_nop({"title": "Tin một", "link": "https://www.reuters.com/x"},
                         1, [], "nova", "nova")
    assert muc["via"], "khong suy duoc via"
    muc2 = mg._muc_tu_nop({"title": "Tin", "link": "https://a.vn/1", "via": "tay-viet"},
                          1, [], "nova", "nova")
    assert muc2["via"] == "tay-viet", "via vai ghi tay phai duoc giu"


def test_muc_tu_nop_lay_link_va_so_bao_tu_nguon_khi_vai_ghi_k():
    import manifest_ghi as mg
    nguon = [{"link": "https://x.vn/1", "tieu_de": "Nvidia rót vốn",
              "so_bao": 3, "cac_bao": ["VnExpress", "Tuổi Trẻ", "Thanh Niên"]}]
    muc = mg._muc_tu_nop({"k": 1, "summary_vi": "Rót vốn lớn"}, 1, nguon, "vera", "vera")
    assert muc["link"] == "https://x.vn/1"
    assert muc["title"] == "Nvidia rót vốn"
    assert "3 báo" in muc["source_note"] and "VnExpress" in muc["source_note"]


def test_muc_tu_nop_k_ngoai_dai_thi_bo_chu_khong_lay_bai_khac():
    import manifest_ghi as mg
    nguon = [{"link": "https://x.vn/1", "tieu_de": "Tin một"}]
    assert mg._muc_tu_nop({"k": 9, "summary_vi": "x"}, 1, nguon, "vera", "vera") is None


def test_muc_tu_nop_don_em_dash_giong_nhanh_Finn():
    """Lech da co that: cong bo em-dash chi co o nhanh Finn toi 07/09/2026."""
    import manifest_ghi as mg
    muc = mg._muc_tu_nop({"title": "Tin", "link": "https://a.vn/1",
                          "summary_vi": "Mở kho — ai cũng tải"}, 1, [], "nova", "nova")
    assert muc["summary_vi"] == "Mở kho, ai cũng tải"


def test_muc_tu_nop_lay_link_goi_y_cua_muc_bat_buoc_khi_vai_khong_ghi_link():
    """Nova chi can ghi dung ten model, khong phai di tim URL (05/09/2026)."""
    import manifest_ghi as mg
    with tempfile.TemporaryDirectory() as t:
        with bat_buoc_tam(t, nova={"k1": {"ten": "Qwen3-Max",
                                          "link": "https://qwen.ai/max"}}):
            muc = mg._muc_tu_nop({"title": "Qwen3-Max", "summary_vi": "Model mới"},
                                 1, [], "nova", "nova")
    assert muc is not None and muc["link"] == "https://qwen.ai/max", muc


def test_muc_tu_nop_category_mac_dinh_theo_vai():
    import manifest_ghi as mg
    n = mg._muc_tu_nop({"title": "T", "link": "https://a.vn/1"}, 1, [], "nova", "nova")
    v = mg._muc_tu_nop({"title": "T", "link": "https://a.vn/1"}, 1, [], "vera", "vera")
    assert n["category"] == "MODEL" and v["category"] == "BUSINESS"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
