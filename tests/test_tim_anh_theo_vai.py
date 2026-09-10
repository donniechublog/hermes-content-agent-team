#!/usr/bin/env python3
"""ENGINE CON PHAI DI TIM ANH NUA KHONG — hoi theo VAI, khong do bang so cua
carousel (LOW-12, 10/09/2026).

Ong Chu: *"Ethan khong tu di tim anh lien quan tren mang ma chi tim anh co trong
article goc"*. Hoi lai lan mot: *"Dre tim duoc anh ma Ethan ko tim duoc? dau can
phai tu di may mo. dung code co san cung tim duoc ma?"* — dung, `_vong_tim_rong`
(Bing -> bao khac cung tin -> browser boc anh + Commons) da co san du may moc,
hong nam o DIEU KIEN mo cong. Lan hai, chot cai sai that su: *"cach lam anh cua
Ethan dau phai la carousel? nhung gi thuoc ve carousel ma lien quan toi Ethan la
nhung thu ko dung"* va *"tieu chi ve anh thi la chung cua moi designer, nhung
carousel la nhieu anh con Ethan lam single image, nen 'so luong' ko the la thu
ap vao duoc"*.

Ban cu do bang MOT con so cho ca ba vai:

    muc_tieu_tim = max(toi_thieu, carousel.FLAGSHIP_MIN if flagship else carousel.MIN_SLIDE)
    if len(dung_duoc) < muc_tieu_tim ...

Tin co 5 anh ngang 16:9 (hinh dang thuong gap nhat cua anh bao) dem ra "du 5"
nen engine ngung tim; nhung card.py chan anh ngang >1.6 lan chart di mot minh,
tuc Ethan con 0 duong dung, ma brief cam vai tu tai them ("chi dung MA ANH").

Nay `vai.du_nguyen_lieu` tra loi: MOI vai deu phai co mot tam lam anh chinh,
rieng SO LUONG thi chi vai xep nhieu anh moi bi dem. Tieu chi CHAT LUONG van
dung chung o luat_anh + phan_loai, khong dong toi.

Chay:  venv/bin/python tests/test_tim_anh_theo_vai.py
"""
import ast
import inspect
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import anh_chuan_bi as cb                                       # noqa: E402


# ------------------------------------------------------------------ do dac that
class _Phien:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _anh(ma: str, **doi) -> dict:
    """Anh doc 4:5, day toi, khong mat — `phan_loai` dan nhan "bìa" cho no, va
    card.py cung dung lam nen hero duoc."""
    a = {"ma": ma, "goc": f"/khong-co/{ma}.png", "url": f"http://vi.du/{ma}.png",
         "ti_le": 0.8, "w": 960, "h": 1200, "loai": "anh", "ngang": False,
         "dung": ["bìa", "thân"], "lien_quan": True, "mat": 0, "goc_trai_sang": 60,
         "canh_ngan": 960, "mien": "vi_du.com", "tu": "bai", "alt": "", "ghi_chu": []}
    a.update(doi)
    return a


def _anh_ngang(ma: str) -> dict:
    """16:9 (1.78): Dre ghep doc thanh mot slide, Ethan khong dung duoc (>1.6)."""
    return _anh(ma, ti_le=1.78, w=1920, h=1080, ngang=True, canh_ngan=1080,
                dung=["ghép dọc với một ảnh ngang cùng tone"])


def _anh_ngang_vua(ma: str) -> dict:
    """1.5: qua NGANG_RO (1.4) nen KHONG co nhan "bìa" cua carousel, nhung card.py
    cho toi 1.6 — day dung la cho luat cua carousel bat Ethan di tim vo ich."""
    return _anh(ma, ti_le=1.5, w=1500, h=1000, ngang=True, canh_ngan=1000,
                dung=["ghép dọc với một ảnh ngang cùng tone"])


def _anh_chart(ma: str) -> dict:
    return _anh(ma, ti_le=1.2, w=1200, h=1000, loai="chart", canh_ngan=1000,
                goc_trai_sang=200, dung=["thân (chart, dán full bề ngang nguyên vẹn)"])


PHA_NANG = ("PhienBrowser", "nap_nguon", "_tom_tat_tu_img_json", "_bo_sung_nguon",
            "_lay_tu_browser", "_chup_xep_hang", "_gom_va_tai_anh", "_nhin_anh",
            "_vong_tim_rong", "_vong_thuong_hieu", "_vong_khai_niem", "_tu_lieu_bai",
            "dung_manifest", "bang_anh")


def _vong_bu_da_chay(anh_bai: list, vai_anh="designer", khong_browser=False,
                     tieu_de="OpenAI ships new image model for developers") -> list:
    """Chay THAT `chuan_bi()` voi moi pha nang thay bang stub, tra ve ten cac vong
    bu da duoc goi. Khong mang, khong browser, khong vision."""
    goi = []
    cu = {k: getattr(cb, k) for k in PHA_NANG}

    def _vong(ten):
        def f(a, *args, **kw):
            goi.append(ten)
            return a, [x for x in a if x["dung"]], []
        return f

    cb.PhienBrowser = lambda *a, **k: _Phien()
    cb.nap_nguon = lambda d, m, s, phien=None: ({"trang": [], "tieu_de_en": tieu_de},
                                                Path(s) / "n.json", "http://vi.du/a")
    cb._tom_tat_tu_img_json = lambda d: {"vai_anh": vai_anh, "summary": ""}
    cb._bo_sung_nguon = lambda *a, **k: []
    cb._lay_tu_browser = lambda trang, *a, **k: (
        {"tieu_de_en": "", "chu": "", "cands": [], "trang_them": []}, trang)
    cb._chup_xep_hang = lambda *a, **k: ([], False)
    cb._gom_va_tai_anh = lambda *a, **k: anh_bai
    cb._nhin_anh = lambda a, nguon, t, wd: (a, [x for x in a if x["dung"]], [])
    cb._vong_tim_rong = _vong("tim_rong")
    cb._vong_thuong_hieu = _vong("thuong_hieu")
    cb._vong_khai_niem = _vong("khai_niem")
    cb._tu_lieu_bai = lambda *a, **k: {"cau_co_so": [], "doan_dau": "", "so_nguon": 1}
    cb.dung_manifest = lambda *a, **k: {"anh": anh_bai}
    cb.bang_anh = lambda *a, **k: None
    try:
        with tempfile.TemporaryDirectory() as tmp:
            cb.chuan_bi("d1", {"brand": "donniechublog", "title": tieu_de},
                        Path(tmp), Path(tmp), khong_browser=khong_browser)
    finally:
        for k, v in cu.items():
            setattr(cb, k, v)
    return goi


# ------------------------------------------------------- vai MOT ANH (Ethan)
def test_bai_du_anh_ma_khong_tam_nao_len_hero_thi_van_di_tim():
    """Dung canh sinh ra su co: bai goc cho DU 5 anh nhung toan 16:9 / chart."""
    for ten, bo in (("5 ngang 16:9", [_anh_ngang(f"A{i + 1}") for i in range(5)]),
                    ("3 ngang + 2 chart", [_anh_ngang("A1"), _anh_ngang("A2"), _anh_ngang("A3"),
                                           _anh_chart("A4"), _anh_chart("A5")]),
                    ("9 ngang — nhieu khong cuu duoc", [_anh_ngang(f"A{i + 1}") for i in range(9)])):
        goi = _vong_bu_da_chay(bo)
        assert "tim_rong" in goi, \
            f"{ten}: Ethan het duong lam hero ma engine khong di tim (da chay: {goi or 'khong vong nao'})"


def test_mat_nguoi_khong_ro_ai_khong_tinh_la_hero():
    """`nop_chung.kiem_nhan_vat` chan anh co mat ma khong khai `nhan_vat`, va vai
    khong duoc bia ten cho qua cong — tam do khong phai mot duong dung duoc."""
    assert "tim_rong" in _vong_bu_da_chay([_anh(f"A{i + 1}", mat=1) for i in range(5)])
    assert "tim_rong" not in _vong_bu_da_chay(
        [_anh("A1", mat=1, alt="Jensen Huang speaks at GTC")]), \
        "alt da neu ten thi Ethan khai duoc nhan_vat — khong can di tim nua"


def test_MOT_tam_hero_la_du_cho_the_don():
    """So luong khong phai tieu chi cua vai lam san pham mot anh (Ong Chu
    10/09/2026). Mot tam dung duoc la du, khong doi cho du 5."""
    assert "tim_rong" not in _vong_bu_da_chay([_anh("A1")]), \
        "Ethan da co nen hero ma engine van tra tien mot phien browser di tim"


def test_luat_ti_le_phai_la_cua_card_khong_phai_cua_carousel():
    """Anh 1.5: carousel khong goi la "bìa" (qua NGANG_RO 1.4) nhung card.py cho
    toi 1.6. Do bang nhan cua carousel la Ethan di tim mot cach vo ich."""
    assert "tim_rong" not in _vong_bu_da_chay([_anh_ngang_vua("A1")]), \
        "do anh cua Ethan bang nguong 1.4 cua carousel thay vi 1.6 cua card.py"


def test_khong_browser_van_khong_mo_phien_nao():
    goi = _vong_bu_da_chay([_anh_ngang(f"A{i + 1}") for i in range(5)], khong_browser=True)
    assert "tim_rong" not in goi, f"--khong-browser ma van mo browser di tim rong: {goi}"


# --------------------------------------------------- vai NHIEU ANH (Dre, Kite)
def test_vai_nhieu_anh_giu_nguyen_cach_dem_cu():
    """Ban sua khong duoc dong toi Dre/Kite: o do moi slide an mot tam that, nen
    SO LUONG van la mot tieu chi that."""
    for vai_anh in ("carousel", "carousel-edu"):
        assert "tim_rong" not in _vong_bu_da_chay([_anh(f"A{i + 1}") for i in range(5)],
                                                  vai_anh=vai_anh), \
            f"{vai_anh}: du 5 tam va co bia ma van di tim"
        assert "tim_rong" in _vong_bu_da_chay([_anh("A1"), _anh("A2")], vai_anh=vai_anh), \
            f"{vai_anh}: moi 2 tam ma khong di tim — thieu 3 slide"
        assert "tim_rong" in _vong_bu_da_chay([_anh_ngang(f"A{i + 1}") for i in range(5)],
                                              vai_anh=vai_anh), \
            f"{vai_anh}: du 5 tam nhung khong tam nao lam bia duoc"


def test_anh_khai_niem_van_la_duong_cuoi():
    """Anh khai niem (co, rack, datacenter) chung chung, phai doi den luc that su
    het duong — va phai di SAU vong tim anh that o bao khac."""
    goi = _vong_bu_da_chay([_anh_ngang(f"A{i + 1}") for i in range(5)])
    assert goi.index("tim_rong") < goi.index("khai_niem")
    assert "khai_niem" not in _vong_bu_da_chay([_anh("A1")]), \
        "bai da co nen hero that ma van day them anh minh hoa chung chung"


# ------------------------------------------- cong o muc ma nguon (chong troi)
def _if_boc_loi_goi(goc: ast.AST, ten: str) -> list:
    """Cac node `ast.If` ma than no goi thang `ten(...)`."""
    ra = []

    def di(node, boc):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == ten and boc is not None:
            ra.append(boc)
        if isinstance(node, ast.If):
            di(node.test, boc)
            for c in node.body + node.orelse:
                di(c, node)
            return
        for c in ast.iter_child_nodes(node):
            di(c, boc)

    di(goc, None)
    return ra


def _ten_ham_trong(nut: ast.AST) -> set:
    ra = set()
    for n in ast.walk(nut):
        if isinstance(n, ast.Call):
            f = n.func
            ra.add(getattr(f, "id", "") or getattr(f, "attr", ""))
    return ra


def test_hai_vong_bu_phai_hoi_ban_dang_ky_vai():
    """Cong chong troi: cac test tren dung stub, nen ai do do lai bang mot phep
    dem khac van co the vo tinh xanh khi con so tinh co thuan. Day bat thang
    HINH DANG cua ma."""
    goc = ast.parse(textwrap.dedent(inspect.getsource(cb.chuan_bi)))
    for ten_vong in ("_vong_tim_rong", "_vong_khai_niem"):
        ifs = _if_boc_loi_goi(goc, ten_vong)
        assert ifs, f"khong tim thay loi goi {ten_vong} trong mot `if` cua chuan_bi()"
        for nut in ifs:
            assert "du_nguyen_lieu" in _ten_ham_trong(nut.test), (
                f"dieu kien mo {ten_vong} khong con hoi `vai.du_nguyen_lieu` — do la "
                "LOW-12: no se lai do bo anh cua Ethan bang so slide cua carousel")


def test_khong_con_so_nao_cua_carousel_trong_duong_di_tim():
    """`chuan_bi()` chay chung cho ca ba vai, nen mot hang so cua carousel nam
    trong do la ap luat cua Dre len Ethan (Ong Chu 10/09/2026)."""
    src = textwrap.dedent(inspect.getsource(cb.chuan_bi))
    for cam in ("MIN_SLIDE", "FLAGSHIP_MIN"):
        for dong in src.splitlines():
            d = dong.strip()
            assert d.startswith("#") or cam not in d, \
                f"con so cua carousel quay lai trong chuan_bi(): {d}"
    for dong in src.splitlines():
        d = dong.strip()
        assert d.startswith("#") or "len(dung_duoc)" not in d, \
            f"dang dem tam anh trong chuan_bi() thay vi hoi vai: {d}"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
