#!/usr/bin/env python3
"""Thong bao ro khi mot buoc khong thuc hien duoc (09/09/2026): 3 mieng moi trong
duyet_giao_viec.py — link_ket_qua/ly_do_task (nut bam cu tra loi dung trang thai
thuc) va canh bao "khong phan hoi" khi mot vai treo giua running trong
bao_tien_do_kanban. Test o day chi phan LOGIC THUAN (khong Telegram/kanban.db
that), theo dung kieu tests/test_route_thieu_anh.py: monkeypatch truc tiep
thuoc tinh module, tu luu/phuc hoi trong finally.

Chay:  venv/bin/python tests/test_bao_treo.py
"""
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import duyet_giao_viec as dg                                  # noqa: E402


# --------------------------------------------------------------- link_ket_qua
def test_link_ket_qua_chua_co_thi_none():
    with tempfile.TemporaryDirectory() as tmp:
        cu = dg.TIN_KET_QUA
        dg.TIN_KET_QUA = Path(tmp) / "tin.json"
        try:
            assert dg.link_ket_qua("t_khong_ton_tai") is None
            assert dg.link_ket_qua(None) is None
        finally:
            dg.TIN_KET_QUA = cu


def test_link_ket_qua_dung_dinh_dang_co_thread():
    with tempfile.TemporaryDirectory() as tmp:
        cu = dg.TIN_KET_QUA
        dg.TIN_KET_QUA = Path(tmp) / "tin.json"
        dg.TIN_KET_QUA.write_text(json.dumps(
            {"t_1": {"chat": -1001234567890, "thread": 52, "mid": 999}}), encoding="utf-8")
        try:
            assert dg.link_ket_qua("t_1") == "https://t.me/c/1234567890/52/999"
        finally:
            dg.TIN_KET_QUA = cu


def test_link_ket_qua_khong_co_thread_thi_bo_doan_do():
    with tempfile.TemporaryDirectory() as tmp:
        cu = dg.TIN_KET_QUA
        dg.TIN_KET_QUA = Path(tmp) / "tin.json"
        dg.TIN_KET_QUA.write_text(json.dumps(
            {"t_1": {"chat": -1001234567890, "thread": None, "mid": 999}}), encoding="utf-8")
        try:
            assert dg.link_ket_qua("t_1") == "https://t.me/c/1234567890/999"
        finally:
            dg.TIN_KET_QUA = cu


def test_link_ket_qua_dm_khong_phai_supergroup_thi_none():
    """Chat thuong (DM, id duong, khong -100...) khong lam duoc deep-link kieu nay."""
    with tempfile.TemporaryDirectory() as tmp:
        cu = dg.TIN_KET_QUA
        dg.TIN_KET_QUA = Path(tmp) / "tin.json"
        dg.TIN_KET_QUA.write_text(json.dumps(
            {"t_1": {"chat": 8112291996, "thread": None, "mid": 5}}), encoding="utf-8")
        try:
            assert dg.link_ket_qua("t_1") is None
        finally:
            dg.TIN_KET_QUA = cu


# --------------------------------------------------------------------- ly_do_task
def test_ly_do_task_lay_tu_lan_chay_cuoi():
    cu = dg.hermes_adapter.lan_chay_cuoi
    dg.hermes_adapter.lan_chay_cuoi = lambda tid: {"tom_tat": None, "loi": "thieu anh that", "metadata": {}}
    try:
        assert dg.ly_do_task("t_1") == "thieu anh that"
    finally:
        dg.hermes_adapter.lan_chay_cuoi = cu


def test_ly_do_task_chua_chay_lan_nao_thi_chuoi_rong():
    cu = dg.hermes_adapter.lan_chay_cuoi
    dg.hermes_adapter.lan_chay_cuoi = lambda tid: {}
    try:
        assert dg.ly_do_task("t_1") == ""
    finally:
        dg.hermes_adapter.lan_chay_cuoi = cu


# --------------------------------------------------- canh bao "khong phan hoi"
def _chay_bao_tien_do_gia(tmp, rows, gui_ghi_lai):
    """Chay bao_tien_do_kanban() voi kanban/telegram gia, tra list text da 'gui'."""
    state = Path(tmp)
    cu = (dg.DA_BAO_TIEN_DO, dg.TIN_KET_QUA, dg.DA_BAO_TREO,
          dg.hermes_adapter.co_kanban, dg.hermes_adapter.viec, dg.call, dg.env_load.topics_path)
    dg.DA_BAO_TIEN_DO = state / "da_bao_tien_do.json"
    dg.TIN_KET_QUA = state / "tin_ket_qua.json"
    dg.DA_BAO_TREO = state / "da_bao_treo.json"
    dg.hermes_adapter.co_kanban = lambda: True
    dg.hermes_adapter.viec = lambda tu_ts=None: list(rows)
    tp = state / "topics.json"
    tp.write_text(json.dumps({"writer": 52}), encoding="utf-8")
    dg.env_load.topics_path = lambda: tp

    def _call_gia(token, method, **kw):
        gui_ghi_lai.append(kw.get("text", ""))
        return {"ok": True, "result": {"message_id": len(gui_ghi_lai)}}
    dg.call = _call_gia
    try:
        dg.bao_tien_do_kanban("TOKEN", -100999)
    finally:
        (dg.DA_BAO_TIEN_DO, dg.TIN_KET_QUA, dg.DA_BAO_TREO,
         dg.hermes_adapter.co_kanban, dg.hermes_adapter.viec, dg.call, dg.env_load.topics_path) = cu


def test_treo_bao_khi_running_qua_lau():
    with tempfile.TemporaryDirectory() as tmp:
        now = time.time()
        rows = [{"id": "t_1", "vai": "writer", "trang_thai": "running",
                  "tieu_de": "Bai test", "tao_luc": now - 3000,
                  "bat_dau_luc": now - dg.NGUONG_TREO_PHUT * 60 - 60,
                  "xong_luc": None, "ket_qua": None, "loi": None}]
        gui = []
        _chay_bao_tien_do_gia(tmp, rows, gui)
        assert any("không phản hồi" in t for t in gui), gui
        # Da ghi lai da_bao_treo de vong sau khong bao lap ngay.
        treo = json.loads((Path(tmp) / "da_bao_treo.json").read_text(encoding="utf-8"))
        assert "t_1" in treo


def test_treo_chua_qua_nguong_thi_im():
    with tempfile.TemporaryDirectory() as tmp:
        now = time.time()
        rows = [{"id": "t_1", "vai": "writer", "trang_thai": "running",
                  "tieu_de": "Bai test", "tao_luc": now - 60,
                  "bat_dau_luc": now - 60,       # moi chay 1 phut, chua treo
                  "xong_luc": None, "ket_qua": None, "loi": None}]
        gui = []
        _chay_bao_tien_do_gia(tmp, rows, gui)
        assert not any("không phản hồi" in t for t in gui), gui


def test_treo_khong_bao_lap_trong_cua_so_lai_bao():
    with tempfile.TemporaryDirectory() as tmp:
        now = time.time()
        state = Path(tmp)
        # Da bao "treo" 5 phut truoc — con trong cua so LAI_BAO_TREO_PHUT (30p).
        (state / "da_bao_treo.json").write_text(
            json.dumps({"t_1": now - 5 * 60}), encoding="utf-8")
        rows = [{"id": "t_1", "vai": "writer", "trang_thai": "running",
                  "tieu_de": "Bai test", "tao_luc": now - 3000,
                  "bat_dau_luc": now - dg.NGUONG_TREO_PHUT * 60 - 60,
                  "xong_luc": None, "ket_qua": None, "loi": None}]
        gui = []
        _chay_bao_tien_do_gia(tmp, rows, gui)
        assert not any("không phản hồi" in t for t in gui), gui


def test_treo_duoc_xoa_khi_task_het_running():
    with tempfile.TemporaryDirectory() as tmp:
        now = time.time()
        state = Path(tmp)
        (state / "da_bao_treo.json").write_text(
            json.dumps({"t_1": now - 40 * 60}), encoding="utf-8")
        rows = [{"id": "t_1", "vai": "writer", "trang_thai": "done",
                  "tieu_de": "Bai test", "tao_luc": now - 3000,
                  "bat_dau_luc": now - 3000, "xong_luc": now,
                  "ket_qua": None, "loi": None}]
        gui = []
        _chay_bao_tien_do_gia(tmp, rows, gui)
        treo = json.loads((state / "da_bao_treo.json").read_text(encoding="utf-8"))
        assert "t_1" not in treo


if __name__ == "__main__":
    # Truoc E-r2-2: vong `fn(); print("OK")` khong try/except, khong tong ket —
    # dung o test dau hong, va chay.sh in "OK" khi qua vi khong thay dong N/M.
    from tam import chay_tat_ca
    chay_tat_ca(globals())
