#!/usr/bin/env python3
"""Vong TIM RONG phai chay ca khi kho "du" anh ma khong tam nao len bia/hero
duoc (LOW-12 — lan thu ba cua cung mot hinh dang loi, sau LOW-10).

Ong Chu: *"Ethan khong tu di tim anh lien quan tren mang ma chi tim anh co trong
article goc"*. Va khi hoi lai: *"Dre tim duoc anh ma Ethan ko tim duoc? dau can
phai tu di may mo. dung code co san cung tim duoc ma?"* — dung: engine la MOT,
`_vong_tim_rong` (Bing -> bao khac cung tin -> browser boc anh + Commons) da co
san du may moc. Hong nam o DIEU KIEN mo cong:

    if len(dung_duoc) < muc_tieu_tim and not khong_browser:
        anh, dung_duoc, chua_nhin = _vong_tim_rong(...)

`dung_duoc` dem bang tien te cua CAROUSEL: anh dung duoc o bat ky dau, ke ca
"chi ghep doc". Tin co 5 anh ngang 16:9 — hinh dang thuong gap nhat cua anh bao
— dem ra du 5 nen cong dong lai; nhung `card.py` chan anh ngang >1.6 lan chart
di mot minh, tuc Ethan con 0 anh hero, ma brief thi cam vai tu tai them ("chi
dung MA ANH"). Ket qua: bo anh cua Ethan chi con anh bai goc + mot tam khai
niem chung chung, du bao khac cung tin dang co anh that.

Ban sua dung dung `_co_bia` ma `_vong_khai_niem` ngay duoi da dung.

Chay:  venv/bin/python tests/test_vong_tim_rong_khi_het_anh_bia.py
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
    """Anh doc 4:5, day toi, khong mat — `phan_loai` cho no nhan "bìa"."""
    a = {"ma": ma, "goc": f"/khong-co/{ma}.png", "url": f"http://vi.du/{ma}.png",
         "ti_le": 0.8, "w": 960, "h": 1200, "loai": "anh", "ngang": False,
         "dung": ["bìa", "thân"], "lien_quan": True, "mat": 0, "goc_trai_sang": 60,
         "canh_ngan": 960, "mien": "vi_du.com", "tu": "bai", "ghi_chu": []}
    a.update(doi)
    return a


def _anh_ngang(ma: str) -> dict:
    """Anh 16:9 (1.78 >= luat_anh.NGANG_RO): Dre dung lam mot slide ghep doc,
    Ethan KHONG dung mot minh duoc (card.py chan >1.6). Khong co "bìa"."""
    return _anh(ma, ti_le=1.78, w=1920, h=1080, ngang=True, canh_ngan=1080,
                dung=["ghép dọc với một ảnh ngang cùng tone"])


def _anh_chart(ma: str) -> dict:
    return _anh(ma, ti_le=1.5, w=1500, h=1000, loai="chart", ngang=True, canh_ngan=1000,
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


def test_du_anh_nhung_het_bia_van_di_tim_bao_khac():
    """Dung canh sinh ra su co: bai goc cho DU 5 anh, nhung toan anh ngang 16:9 /
    chart — khong tam nao lam bia/hero. Truoc sua: `tim_rong` khong chay."""
    for ten, bo in (("5 ngang 16:9", [_anh_ngang(f"A{i + 1}") for i in range(5)]),
                    ("3 ngang + 2 chart", [_anh_ngang("A1"), _anh_ngang("A2"), _anh_ngang("A3"),
                                           _anh_chart("A4"), _anh_chart("A5")])):
        for vai_anh in ("designer", "carousel"):
            goi = _vong_bu_da_chay(bo, vai_anh=vai_anh)
            assert "tim_rong" in goi, (
                f"{ten} / {vai_anh}: kho du anh ma het bia van KHONG di tim bao khac "
                f"— dung su co LOW-12 (da chay: {goi or 'khong vong nao'})")


def test_du_anh_VA_co_bia_thi_khong_ton_mot_vong_browser():
    """Vong nay mo browser + hoi Bing: bai da co anh lam hero duoc thi khong duoc
    chay. Khong co ve nay thi ban sua thanh "luc nao cung tim", cham va ton."""
    goi = _vong_bu_da_chay([_anh(f"A{i + 1}") for i in range(5)])
    assert "tim_rong" not in goi, \
        f"bai da du anh VA co bia van di tim rong — ton mot phien browser + Bing: {goi}"


def test_thieu_anh_that_su_thi_van_chay_nhu_cu():
    assert "tim_rong" in _vong_bu_da_chay([_anh_ngang("A1"), _anh_ngang("A2")])
    assert "tim_rong" in _vong_bu_da_chay([_anh("A1"), _anh("A2")])


def test_khong_browser_van_khong_chay():
    """`--khong-browser` (chay tay/test) khong duoc mo phien browser nao."""
    goi = _vong_bu_da_chay([_anh_ngang(f"A{i + 1}") for i in range(5)], khong_browser=True)
    assert "tim_rong" not in goi, f"--khong-browser ma van mo browser di tim rong: {goi}"


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


def test_dieu_kien_phai_van_hoi_co_bia():
    """Cong chong troi: ba test tren dung stub, nen ai do doi dieu kien ve dem
    thuan ("< muc_tieu_tim", "< toi_thieu", mot ten moi) van co the vo tinh xanh
    neu con so tinh co thuan. Day bat thang HINH DANG cua ma: dieu kien mo cong
    `_vong_tim_rong` phai con hoi `_co_bia`."""
    goc = ast.parse(textwrap.dedent(inspect.getsource(cb.chuan_bi)))
    ifs = _if_boc_loi_goi(goc, "_vong_tim_rong")
    assert ifs, "khong tim thay loi goi _vong_tim_rong nam trong mot `if` cua chuan_bi()"
    for nut in ifs:
        ten_trong_test = {getattr(n.func, "id", "") for n in ast.walk(nut.test)
                          if isinstance(n, ast.Call)}
        assert "_co_bia" in ten_trong_test, (
            "dieu kien mo vong tim rong khong con hoi `_co_bia` — do la LOW-12: "
            "bai du 5 anh ngang/chart se khong bao gio duoc di tim anh that o bao khac")


def test_tim_rong_phai_di_TRUOC_khai_niem():
    """Anh that cua bao khac cung tin dat hon anh khai niem chung chung (co,
    rack, datacenter). Doi thu tu la bai nao cung dinh anh minh hoa truoc."""
    src = textwrap.dedent(inspect.getsource(cb.chuan_bi))
    goc = ast.parse(src)
    dong = {}
    for n in ast.walk(goc):
        if isinstance(n, ast.Call) and getattr(n.func, "id", "") in ("_vong_tim_rong", "_vong_khai_niem"):
            dong.setdefault(n.func.id, n.lineno)
    assert dong["_vong_tim_rong"] < dong["_vong_khai_niem"], \
        "vong khai niem chay TRUOC vong tim rong — anh minh hoa se de len cho cua anh that"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
