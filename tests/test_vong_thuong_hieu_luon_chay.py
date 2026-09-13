#!/usr/bin/env python3
"""Vong anh thuong hieu phai chay cho MOI tin co Big Brand, khong doi thieu anh
(su co 10/09/2026 — lan thu hai cua cung mot loi).

Ong Chu, kem hai link task: *"Dre van ko chiu di tim cac hinh lien quan nhu logo,
brand, founder, tru so... cua chu de duoc nhac toi"*. Ban 09/09 da dung du may
moc (image_brand.py: Commons + Wikidata P18/P154/P112, cau hoi vision rieng
cho tung loai tu lieu), nhung noi vao day chuyen nhu mot VONG BU:

    if len(dung_duoc) < muc_tieu_tim or not _co_bia(dung_duoc):
        anh, dung_duoc, chua_nhin = _round_brand(...)

nen tin nao bai goc du anh (Dre 5, flagship 8) la khong bao gio hoi toi
Commons/Wikidata. Vai khong "khong chiu di tim": brief cam vai tu tai them ("chi
dung MA ANH, khong tai/crop/mo gi them"), nen bo anh giao cho vai trang tron mac
du may moc da san.

Bon test giu bon mat cua duong hong do: vong that su chay khi du anh, vong khai
niem KHONG bi keo theo, cong o muc ma nguon chong viet lai kieu cu, va nhan chan
dung founder di duoc toi ca hai brief.

Chay:  venv/bin/python tests/test_vong_thuong_hieu_luon_chay.py
"""
import ast
import inspect
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_prepare as cb                                       # noqa: E402
import image_brand as th                                    # noqa: E402


# ------------------------------------------------------------------ do dac that
class _Phien:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _anh(ma: str) -> dict:
    return {"ma": ma, "goc": f"/khong-co/{ma}.png", "url": f"http://vi.du/{ma}.png",
            "ti_le": 1.0, "w": 1200, "h": 1200, "loai": "anh", "ngang": False,
            "dung": ["bìa", "slide"], "lien_quan": True, "mat": 0, "goc_trai_sang": 60,
            "canh_ngan": 1200, "mien": "vi_du.com", "tu": "bai", "ghi_chu": []}


PHA_NANG = ("BrowserSession", "load_source", "_summary_from_img_json", "_supplement_source", "_extra_announcement_page",
            "_take_from_browser", "_capture_ranking", "_gather_and_download_image", "_seen_image",
            "_round_widen_search", "_round_brand", "_round_concept", "_article_material",
            "build_manifest", "contact_sheet")


def _vong_bu_da_chay(so_anh_cua_tin: int,
                     tieu_de="Samsung opens new chip plant in Texas") -> list:
    """Chay THAT `prepare_article()` voi moi pha nang thay bang stub, tra ve ten cac vong
    bu da duoc goi. Khong mang, khong browser, khong vision."""
    goi = []
    anh = [_anh(f"A{i + 1}") for i in range(so_anh_cua_tin)]
    cu = {k: getattr(cb, k) for k in PHA_NANG}

    def _vong(ten):
        def f(a, *args, **kw):
            goi.append(ten)
            return a, [x for x in a if x["dung"]], []
        return f

    cb.BrowserSession = lambda *a, **k: _Phien()
    cb.load_source = lambda d, m, s, phien=None: ({"trang": [], "tieu_de_en": tieu_de},
                                                Path(s) / "n.json", "http://vi.du/a")
    cb._summary_from_img_json = lambda d: {"vai_anh": "dre", "summary": ""}
    cb._supplement_source = lambda *a, **k: []
    cb._extra_announcement_page = lambda n, p, trang, *a, **k: trang
    cb._take_from_browser = lambda trang, *a, **k: (
        {"tieu_de_en": "", "chu": "", "cands": [], "trang_them": []}, trang)
    cb._capture_ranking = lambda *a, **k: ([], False)
    cb._gather_and_download_image = lambda *a, **k: anh
    cb._seen_image = lambda a, nguon, tieu_de_, wd: (a, [x for x in a if x["dung"]], [])
    cb._round_widen_search = _vong("tim_rong")
    cb._round_brand = _vong("thuong_hieu")
    cb._round_concept = _vong("khai_niem")
    cb._article_material = lambda *a, **k: {"sentence_has_count": [], "doan_dau": "", "so_nguon": 1}
    cb.build_manifest = lambda *a, **k: {"anh": anh}
    cb.contact_sheet = lambda *a, **k: None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            cb.prepare_article("d1", {"brand": "donniechublog", "title": tieu_de},
                        Path(tmp), Path(tmp), khong_browser=True)
    finally:
        for k, v in cu.items():
            setattr(cb, k, v)
    return goi


def test_du_anh_van_di_tim_logo_founder_tru_so():
    """Dung canh sinh ra su co: bai goc DU anh (>= 5 cua Dre), Big Brand trong
    tieu de. Truoc sua: khong mot vong nao chay, bo anh khong co lay mot tam logo
    / chan dung founder / tru so nao."""
    for so in (5, 9):
        assert "thuong_hieu" in _vong_bu_da_chay(so), \
            f"bai {so} anh: KHONG di tim anh cua chinh hang — dung su co 10/09/2026"


def test_thieu_anh_thi_van_chay_nhu_cu():
    assert "thuong_hieu" in _vong_bu_da_chay(2)


def test_anh_khai_niem_KHONG_bi_keo_theo():
    """Anh khai niem (co nuoc, dai rack) la anh chung chung, khong phai anh cua
    chu de duoc nhac toi — no van phai doi toi luc thieu anh. Chua sua qua tay."""
    assert "khai_niem" not in _vong_bu_da_chay(9), \
        "anh khai niem chay ca khi du anh — bo se day rac vao moi bai"
    assert "khai_niem" in _vong_bu_da_chay(2)


# ------------------------------------------------- cong o muc ma nguon (chong troi)
def _goi_nam_trong_if(goc: ast.AST, ten: str) -> list:
    """[True/False, ...] cho tung loi goi `ten`: True neu no nam trong mot `if`."""
    ra = []

    def di(node, trong_if):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == ten:
            ra.append(trong_if)
        if isinstance(node, ast.If):
            di(node.test, trong_if)
            for c in node.body + node.orelse:
                di(c, True)
            return
        for c in ast.iter_child_nodes(node):
            di(c, trong_if)

    di(goc, False)
    return ra


def test_loi_goi_khong_duoc_treo_lai_sau_mot_if():
    """Cong o muc MA NGUON vi ba test tren dung stub: ai do treo lai dieu kien
    "chi khi thieu anh" bang mot bien khac (`toi_thieu`, `muc_tieu_tim`, hay mot
    ten moi) thi stub van chay qua neu con so tinh co thuan. Day bat thang cai
    HINH DANG cua ma: loi goi phai nam o than ham, khong nam trong `if` nao."""
    goc = ast.parse(textwrap.dedent(inspect.getsource(cb.prepare_article)))
    trong_if = _goi_nam_trong_if(goc, "_round_brand")
    assert trong_if, "khong tim thay loi goi _round_brand trong prepare_article()"
    assert not any(trong_if), (
        "vong anh thuong hieu bi treo lai sau mot `if` — do la su co 10/09/2026: "
        "tin du anh se khong bao gio duoc di tim logo/founder/tru so")
    assert any(_goi_nam_trong_if(goc, "_round_concept")), \
        "vong anh khai niem phai VAN nam trong `if` (chi chay khi thieu anh)"


# ------------------------------------------- nhan chan dung founder toi ca hai brief
_TH_NGUOI = {"hang": "Nvidia", "khoa": "nvidia", "loai": "nguoi",
             "nguoi": "Jensen Huang", "vai": "nhà sáng lập"}


def test_nhan_chan_dung_noi_ten_va_doi_khai_nhan_vat():
    n = th.label_by_type(_TH_NGUOI)
    assert "Jensen Huang" in n and "nhan_vat" in n and n.startswith("👤")


def test_brief_cua_ethan_khong_con_goi_chan_dung_la_tru_so():
    """Ban cu cua `nhan_ethan` dan mot cau "tru so/campus/bien hieu" chung cho
    MOI loai tu lieu, va khong noi TEN nguoi. Ethan vi vay khong co duong nao
    khai `nhan_vat` dung, ma `submit_common.check_subject_named` thi chan anh co mat nguoi
    khong khai ten -> Ethan buoc phai bo anh founder."""
    import ethan_chuan_bi
    a = {"ma": "A6", "ti_le": 0.8, "w": 960, "h": 1200, "loai": "anh", "mat": 1,
         "goc_trai_sang": 60, "canh_ngan": 960, "ghi_chu": [], "thuong_hieu": _TH_NGUOI}
    _dung, ghi = ethan_chuan_bi.nhan_ethan(a)
    chu = " ".join(ghi)
    assert "Jensen Huang" in chu, f"brief cua Ethan khong noi ten nguoi trong anh: {chu}"
    assert "trụ sở/campus/biển hiệu" not in chu, \
        f"van goi mot tam chan dung la anh tru so/campus: {chu}"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
