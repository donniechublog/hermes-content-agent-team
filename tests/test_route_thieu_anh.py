#!/usr/bin/env python3
"""Engine chỉ MÔ TẢ thiếu ảnh, tầng ghép nối mới QUYẾT ĐỊNH (issue A1).

Truoc 09/09/2026 `anh_chuan_bi._route_thieu_anh` gui Telegram va tao task Kite
ngay trong engine, nen engine phai `from duyet_giao_viec import chuan_assignee`
va `from duyet_bai import tao_task_kite`: lop CHUAN BI goi NGUOC len lop dieu
phoi. Nay engine ghi `xong.json["thieu_anh"] = {"so": .., "toi_thieu": ..}` va
nhan mot moc `sau_chuan_bi`; `route_thieu_anh.py` la noi duy nhat biet ca hai phia.

Test giu HAI thu:
  1. Hanh vi dinh tuyen khong doi (bon nhanh cua ham cu).
  2. Moc chay TRONG khoa va TRUOC khi ghi `xong.json` — day la thu chan cuoc
     dua: neu `xong.json` hien ra truoc khi dinh tuyen xong thi dre_chuan_bi /
     kite_chuan_bi co the doc trung khe do va dung brief noi "du anh" trong khi
     tin dang cho chuyen Kite.

Chay:  venv/bin/python tests/test_route_thieu_anh.py
"""
import contextlib
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import anh_chuan_bi as cb                                     # noqa: E402
import route_thieu_anh as rt                                  # noqa: E402


# --------------------------------------------------------------- engine mô tả
def test_mo_ta_thieu_anh_du_thi_None():
    assert cb._mo_ta_thieu_anh({"so_dung_duoc": 5, "toi_thieu": 5}) is None
    assert cb._mo_ta_thieu_anh({"so_dung_duoc": 9, "toi_thieu": 5}) is None


def test_mo_ta_thieu_anh_thieu_thi_ta_ro_so():
    assert cb._mo_ta_thieu_anh({"so_dung_duoc": 2, "toi_thieu": 5}) == {"so": 2, "toi_thieu": 5}


def _chay_gia(tmp, m_engine, sau_chuan_bi=None):
    """Chay cb.chay() voi engine gia (khong browser/mang), tra (m, wd)."""
    wd = Path(tmp) / "wd"
    wd.mkdir(parents=True, exist_ok=True)
    cu = (cb.chuan_bi, cb._cho_luot, cb.nap_meta, cb.workdir)
    cb.chuan_bi = lambda *a, **k: dict(m_engine)
    cb._cho_luot = lambda: contextlib.nullcontext()      # that su dung fcntl (POSIX)
    cb.nap_meta = lambda d: {}
    cb.workdir = lambda state, d: wd
    try:
        m, wd2, _ = cb.chay("d1", sau_chuan_bi=sau_chuan_bi)
        return m, wd2
    finally:
        cb.chuan_bi, cb._cho_luot, cb.nap_meta, cb.workdir = cu


def test_chay_ghi_co_thieu_anh_vao_xong_json():
    with tempfile.TemporaryDirectory() as tmp:
        m, wd = _chay_gia(tmp, {"so_dung_duoc": 2, "toi_thieu": 5, "anh": []})
        assert m["thieu_anh"] == {"so": 2, "toi_thieu": 5}, m
        tren_dia = json.loads((wd / "xong.json").read_text(encoding="utf-8"))
        assert tren_dia["thieu_anh"] == {"so": 2, "toi_thieu": 5}, tren_dia


def test_chay_du_anh_thi_khong_co_co():
    with tempfile.TemporaryDirectory() as tmp:
        m, _ = _chay_gia(tmp, {"so_dung_duoc": 6, "toi_thieu": 5, "anh": []})
        assert "thieu_anh" not in m, m


def test_chay_khong_co_moc_van_chay_duoc():
    """Engine phai dung mot minh duoc (chay tay, test) — moc la tuy chon."""
    with tempfile.TemporaryDirectory() as tmp:
        m, wd = _chay_gia(tmp, {"so_dung_duoc": 0, "toi_thieu": 5, "anh": []})
        assert (wd / "xong.json").exists()
        assert m["thieu_anh"]["so"] == 0


def test_moc_chay_TRUOC_khi_xong_json_hien_ra():
    """Thu chan cuoc dua: luc moc duoc goi, `xong.json` CHUA duoc ghi; va thu
    moc ghi vao `m` phai nam trong tep cuoi cung."""
    with tempfile.TemporaryDirectory() as tmp:
        thay = {}

        def moc(draft_id, m):
            thay["xong_ton_tai_luc_goi"] = (Path(tmp) / "wd" / "xong.json").exists()
            m["chuyen_kite"] = "t_9"

        m, wd = _chay_gia(tmp, {"so_dung_duoc": 0, "toi_thieu": 5, "anh": []}, moc)
        assert thay["xong_ton_tai_luc_goi"] is False, \
            "xong.json da hien ra TRUOC khi dinh tuyen xong — dung khe dua can chan"
        tren_dia = json.loads((wd / "xong.json").read_text(encoding="utf-8"))
        assert tren_dia.get("chuyen_kite") == "t_9", \
            f"quyet dinh cua moc khong duoc ghi xuong dia: {tren_dia}"


def test_moc_no_thi_van_ghi_xong_json():
    """Moc hong khong duoc lam mat xong.json — bai hoc audit 05/09."""
    with tempfile.TemporaryDirectory() as tmp:
        def moc(draft_id, m):
            raise RuntimeError("router vo")
        m, wd = _chay_gia(tmp, {"so_dung_duoc": 1, "toi_thieu": 5, "anh": []}, moc)
        assert (wd / "xong.json").exists(), "moc no lam mat xong.json"


# ------------------------------------------------------- tầng ghép nối quyết định
def _router(tmp, m, im, kite_co=True, tao_kite=("t_7", None)):
    """Goi rt.sau_chuan_bi voi sidecar gia. Tra (m, cac tin da gui)."""
    import duyet_giao_viec as dgv
    import duyet_bai as db
    drafts = Path(tmp) / "drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    (drafts / "d1.img.json").write_text(json.dumps(im), encoding="utf-8")
    tin = []
    cu = (rt.DRAFTS, rt._tg_gui, dgv.chuan_assignee, db.tao_task_kite)
    rt.DRAFTS = drafts
    rt._tg_gui = lambda vai, text, kb=None: tin.append((vai, text, kb))
    dgv.chuan_assignee = lambda v: (v, not kite_co)
    db.tao_task_kite = lambda *a, **k: tao_kite
    try:
        rt.sau_chuan_bi("d1", m)
        return m, tin
    finally:
        rt.DRAFTS, rt._tg_gui, dgv.chuan_assignee, db.tao_task_kite = cu


def test_du_anh_thi_router_im():
    with tempfile.TemporaryDirectory() as tmp:
        m, tin = _router(tmp, {"title": "x"}, {"vai_anh": "carousel"})
        assert tin == [] and "hoi_kite" not in m, (m, tin)


def test_khong_co_sidecar_thi_im():
    with tempfile.TemporaryDirectory() as tmp:
        drafts = Path(tmp) / "drafts"
        drafts.mkdir(parents=True)
        cu = rt.DRAFTS
        rt.DRAFTS = drafts
        try:
            m = {"thieu_anh": {"so": 0, "toi_thieu": 5}, "title": "x"}
            rt.sau_chuan_bi("d1", m)
            assert "chuyen_kite" not in m and "hoi_kite" not in m, m
        finally:
            rt.DRAFTS = cu


def test_da_la_kite_thi_khong_tu_chuyen_nua():
    with tempfile.TemporaryDirectory() as tmp:
        m, tin = _router(tmp, {"thieu_anh": {"so": 0, "toi_thieu": 5}, "title": "x"},
                         {"vai_anh": "carousel-edu"})
        assert tin == [] and "chuyen_kite" not in m, (m, tin)


def test_khong_anh_nao_thi_tu_chuyen_kite():
    with tempfile.TemporaryDirectory() as tmp:
        m, tin = _router(tmp, {"thieu_anh": {"so": 0, "toi_thieu": 5}, "title": "Tin A"},
                         {"vai_anh": "carousel"})
        assert m.get("chuyen_kite") == "t_7", m
        assert tin and "Kite" in tin[0][1], tin


def test_thieu_nhung_con_anh_thi_hoi_ong_chu_hai_nut():
    with tempfile.TemporaryDirectory() as tmp:
        m, tin = _router(tmp, {"thieu_anh": {"so": 3, "toi_thieu": 5}, "title": "Tin B"},
                         {"vai_anh": "carousel"})
        assert m.get("hoi_kite") is True, m
        nut = [b["callback_data"] for b in tin[0][2]["inline_keyboard"][0]]
        assert "imgkite:d1" in nut and "imgtiep:d1" in nut, nut


def test_brand_khong_co_kite_thi_khong_hua_chuyen():
    """dcgr 05/09/2026: khong duoc hien nut Kite khi brand chua co Kite."""
    with tempfile.TemporaryDirectory() as tmp:
        m, tin = _router(tmp, {"thieu_anh": {"so": 3, "toi_thieu": 5}, "title": "Tin C"},
                         {"vai_anh": "carousel"}, kite_co=False)
        assert m.get("hoi_kite") is True, m
        nut = [b["callback_data"] for b in tin[0][2]["inline_keyboard"][0]]
        assert "imgkite:d1" not in nut, f"hua chuyen Kite khi brand chua co: {nut}"
        assert "imgno:d1" in nut, nut


def test_brand_khong_co_kite_va_0_anh_thi_bao_bo_tin():
    with tempfile.TemporaryDirectory() as tmp:
        m, tin = _router(tmp, {"thieu_anh": {"so": 0, "toi_thieu": 5}, "title": "Tin D"},
                         {"vai_anh": "carousel"}, kite_co=False)
        assert m.get("khong_kite") is True, m
        assert "chuyen_kite" not in m, m


def test_tao_task_kite_loi_thi_bao_ra_khong_dat_co():
    with tempfile.TemporaryDirectory() as tmp:
        m, tin = _router(tmp, {"thieu_anh": {"so": 0, "toi_thieu": 5}, "title": "Tin E"},
                         {"vai_anh": "carousel"}, tao_kite=(None, "kanban 500"))
        assert "chuyen_kite" not in m, "dat co chuyen_kite du tao task hong"
        assert tin and "lỗi" in tin[0][1], tin


if __name__ == "__main__":
    ham = [v for k, v in list(globals().items()) if k.startswith("test_")]
    loi = 0
    for h in ham:
        try:
            h()
            print(f"OK   {h.__name__}")
        except AssertionError as e:
            loi += 1
            print(f"FAIL {h.__name__}: {e}")
    print(f"\n{len(ham) - loi}/{len(ham)} test qua")
    sys.exit(1 if loi else 0)
