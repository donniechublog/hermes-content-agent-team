#!/usr/bin/env python3
"""Engine chỉ MÔ TẢ thiếu ảnh, tầng ghép nối mới QUYẾT ĐỊNH (issue A1).

Truoc 09/09/2026 `image_prepare._route_thieu_anh` gui Telegram va tao task Kite
ngay trong engine, nen engine phai `from approve_dispatch import standard_assignee`
va `from approve_post import create_task_kite`: lop CHUAN BI goi NGUOC len lop dieu
phoi. Nay engine ghi `xong.json["thieu_anh"] = {"so": .., "toi_thieu": ..}` va
nhan mot moc `after_prepare`; `route_missing_images.py` la noi duy nhat biet ca hai phia.

Test giu HAI thu:
  1. Hanh vi dinh tuyen khong doi (bon nhanh cua ham cu).
  2. Moc chay TRONG khoa va TRUOC khi ghi `xong.json` — day la thu chan cuoc
     dua: neu `xong.json` hien ra truoc khi dinh tuyen xong thi dre_prepare /
     kite_prepare co the doc trung khe do va dung brief noi "du anh" trong khi
     tin dang cho chuyen Kite.

Chay:  venv/bin/python tests/test_route_thieu_anh.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_prepare as cb                                     # noqa: E402
import route_missing_images as rt                                  # noqa: E402


# --------------------------------------------------------------- engine mô tả
def test_mo_ta_thieu_anh_du_thi_None():
    assert cb._description_missing_image({"so_dung_duoc": 5, "toi_thieu": 5}) is None
    assert cb._description_missing_image({"so_dung_duoc": 9, "toi_thieu": 5}) is None


def test_mo_ta_thieu_anh_thieu_thi_ta_ro_so():
    assert cb._description_missing_image({"so_dung_duoc": 2, "toi_thieu": 5}) == {"so": 2, "toi_thieu": 5}


def _chay_gia(tmp, m_engine, sau_chuan_bi=None):
    """Chay cb.run() voi engine gia (khong browser/mang), tra (m, wd)."""
    wd = Path(tmp) / "wd"
    wd.mkdir(parents=True, exist_ok=True)
    # Dung `_wait_for_slot` THAT: tu khi C3 them fallback khi thieu fcntl, no chay
    # duoc ca tren Windows (khong khoa, co canh bao) nen test khong con phai
    # thay bang no-op de lach nua.
    cu = (cb.prepare_article, cb.load_meta, cb.workdir)
    cb.prepare_article = lambda *a, **k: dict(m_engine)
    cb.load_meta = lambda d: {}
    cb.workdir = lambda state, d: wd
    try:
        m, wd2, _ = cb.run("d1", sau_chuan_bi=sau_chuan_bi)
        return m, wd2
    finally:
        cb.prepare_article, cb.load_meta, cb.workdir = cu


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
def _router(tmp, m, im, kite_co=True, tao_kite=("t_7", None), gui_ok=True):
    """Goi rt.after_prepare voi sidecar gia. Tra (m, cac tin da gui).

    `gui_ok=False` gia lap Telegram tu choi (400) — _time_send tra False."""
    import approve_dispatch as dgv
    import approve_post as db
    drafts = Path(tmp) / "drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    (drafts / "d1.img.json").write_text(json.dumps(im), encoding="utf-8")
    tin = []
    cu = (rt.DRAFTS, rt._time_send, dgv.standard_assignee, db.create_task_kite)
    rt.DRAFTS = drafts

    def _gui(vai, text, kb=None):
        tin.append((vai, text, kb))
        return gui_ok
    rt._time_send = _gui
    dgv.standard_assignee = lambda v: (v, not kite_co)
    db.create_task_kite = lambda *a, **k: tao_kite
    try:
        rt.after_prepare("d1", m)
        return m, tin
    finally:
        rt.DRAFTS, rt._time_send, dgv.standard_assignee, db.create_task_kite = cu


def test_telegram_tu_choi_thi_KHONG_danh_dau_da_hoi():
    """C-r2-1: truoc day _time_send vut ket qua post, m["hoi_kite"]=True van ghi vao
    xong.json — bai 'dang cho Ong Chu chon' ma Ong Chu chua bao gio nhan nut."""
    with tempfile.TemporaryDirectory() as tmp:
        m, tin = _router(tmp, {"thieu_anh": {"so": 3, "toi_thieu": 5}, "title": "T"},
                         {"vai_anh": "dre"}, gui_ok=False)
        assert len(tin) == 1, "van phai THU gui"
        assert "hoi_kite" not in m, m
        assert "route_loi" in m and "hoi_kite" in m["route_loi"], m


def test_sidecar_cu_ghi_slug_cu_van_toi_dung_topic():
    """C-r2-1 (N-r2-5): im.json cu ghi mot chu KHAC slug hien tai — phai doi ve
    slug that truoc khi tra topic, khong thi task nam 'ready' mai (su co
    01/09/2026). Sau LOW-14 chu do la slug ROLE cu ("carousel"), con "heller"
    la ten persona doi truoc nua; ca hai deu phai ra "dre"."""
    for chu in ("carousel", "heller"):
        with tempfile.TemporaryDirectory() as tmp:
            m, tin = _router(tmp, {"thieu_anh": {"so": 3, "toi_thieu": 5}, "title": "T"},
                             {"vai_anh": chu})
            assert tin and tin[0][0] == "dre", (chu, tin)
            assert m.get("hoi_kite") is True, (chu, m)


def test_tg_gui_that_doc_ok_cua_telegram():
    """_time_send phai nhin vao {"ok": false} cua Telegram, khong chi vao HTTP."""
    import httpx
    import os

    class _R:
        status_code = 400
        def json(self):
            return {"ok": False, "description": "Bad Request: message thread not found"}
    cu_post, cu_topics = httpx.post, rt.env_load.topics
    cu_env = {k: os.environ.get(k) for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_GROUP_ID")}
    os.environ["TELEGRAM_BOT_TOKEN"], os.environ["TELEGRAM_GROUP_ID"] = "t", "g"
    httpx.post = lambda *a, **k: _R()
    rt.env_load.topics = lambda: {"dre": 7}
    try:
        assert rt._time_send("dre", "x") is False
    finally:
        httpx.post, rt.env_load.topics = cu_post, cu_topics
        for k, v in cu_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def test_du_anh_thi_router_im():
    with tempfile.TemporaryDirectory() as tmp:
        m, tin = _router(tmp, {"title": "x"}, {"vai_anh": "dre"})
        assert tin == [] and "hoi_kite" not in m, (m, tin)


def test_khong_co_sidecar_thi_im():
    with tempfile.TemporaryDirectory() as tmp:
        drafts = Path(tmp) / "drafts"
        drafts.mkdir(parents=True)
        cu = rt.DRAFTS
        rt.DRAFTS = drafts
        try:
            m = {"thieu_anh": {"so": 0, "toi_thieu": 5}, "title": "x"}
            rt.after_prepare("d1", m)
            assert "chuyen_kite" not in m and "hoi_kite" not in m, m
        finally:
            rt.DRAFTS = cu


def test_da_la_kite_thi_khong_tu_chuyen_nua():
    with tempfile.TemporaryDirectory() as tmp:
        m, tin = _router(tmp, {"thieu_anh": {"so": 0, "toi_thieu": 5}, "title": "x"},
                         {"vai_anh": "kite"})
        assert tin == [] and "chuyen_kite" not in m, (m, tin)


def test_khong_anh_nao_thi_tu_chuyen_kite():
    with tempfile.TemporaryDirectory() as tmp:
        m, tin = _router(tmp, {"thieu_anh": {"so": 0, "toi_thieu": 5}, "title": "Tin A"},
                         {"vai_anh": "dre"})
        assert m.get("chuyen_kite") == "t_7", m
        assert tin and "Kite" in tin[0][1], tin


def test_thieu_nhung_con_anh_thi_hoi_ong_chu_hai_nut():
    with tempfile.TemporaryDirectory() as tmp:
        m, tin = _router(tmp, {"thieu_anh": {"so": 3, "toi_thieu": 5}, "title": "Tin B"},
                         {"vai_anh": "dre"})
        assert m.get("hoi_kite") is True, m
        nut = [b["callback_data"] for b in tin[0][2]["inline_keyboard"][0]]
        assert "imgkite:d1" in nut and "imgtiep:d1" in nut, nut


def test_brand_khong_co_kite_thi_khong_hua_chuyen():
    """dcgr 05/09/2026: khong duoc hien nut Kite khi brand chua co Kite."""
    with tempfile.TemporaryDirectory() as tmp:
        m, tin = _router(tmp, {"thieu_anh": {"so": 3, "toi_thieu": 5}, "title": "Tin C"},
                         {"vai_anh": "dre"}, kite_co=False)
        assert m.get("hoi_kite") is True, m
        nut = [b["callback_data"] for b in tin[0][2]["inline_keyboard"][0]]
        assert "imgkite:d1" not in nut, f"hua chuyen Kite khi brand chua co: {nut}"
        assert "imgno:d1" in nut, nut


def test_brand_khong_co_kite_va_0_anh_thi_bao_bo_tin():
    with tempfile.TemporaryDirectory() as tmp:
        m, tin = _router(tmp, {"thieu_anh": {"so": 0, "toi_thieu": 5}, "title": "Tin D"},
                         {"vai_anh": "dre"}, kite_co=False)
        assert m.get("khong_kite") is True, m
        assert "chuyen_kite" not in m, m


def test_tao_task_kite_loi_thi_bao_ra_khong_dat_co():
    with tempfile.TemporaryDirectory() as tmp:
        m, tin = _router(tmp, {"thieu_anh": {"so": 0, "toi_thieu": 5}, "title": "Tin E"},
                         {"vai_anh": "dre"}, tao_kite=(None, "kanban 500"))
        assert "chuyen_kite" not in m, "dat co chuyen_kite du tao task hong"
        assert tin and "lỗi" in tin[0][1], tin


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
