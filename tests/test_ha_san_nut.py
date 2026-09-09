#!/usr/bin/env python3
"""Nut "ha san" (imgtiep) khi HET DUONG that su (duyet_bai.py) — sinh sau su co
08/09/2026: Ong Chu bam "Dre lam voi 4 anh", engine tra loi "chi 4 anh ma can
toi thieu 5 slide — bam tiep cung khong dung duoc. Chuyen Kite ve vector, hoac
bo tin" RỒI GỠ LUÔN BÀN PHÍM — không còn nút nào bấm được hai đường vừa nêu,
phải tự gõ lệnh. `_chot_nut` trước đó gỡ bàn phím vô điều kiện bất kể nút nào
vừa bấm ra kết quả gì.

Sua: `_nut_ha_san` het duong thi tra ve mot ban phim moi (Gui Kite + Bo han,
hoac chi Bo han neu brand khong co Kite) thay vi None; `_chot_nut` gan lai dung
ban phim do thay vi go trang.

Chay:  venv/bin/python tests/test_ha_san_nut.py
"""
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import duyet_bai as db              # noqa: E402
import duyet_giao_viec as dgv       # noqa: E402


class _CQ(dict):
    """cq gia: chi can ['id'] cho answerCallbackQuery."""
    def __init__(self):
        super().__init__(id="cbq1")


def _xong_json(tmp: Path, so_dung_duoc: int, toi_thieu: int, toi_thieu_co_ban=5) -> Path:
    d = tmp / "state" / "chuan_bi" / "d1"
    d.mkdir(parents=True, exist_ok=True)
    p = d / "xong.json"
    p.write_text(json.dumps({"so_dung_duoc": so_dung_duoc, "toi_thieu": toi_thieu,
                             "toi_thieu_co_ban": toi_thieu_co_ban}), encoding="utf-8")
    return p


def _goi_ha_san(tmp: Path, so_dung_duoc: int, toi_thieu: int, co_kite: bool):
    """Chay _nut_ha_san voi moi truong gia, tra (note, keyboard)."""
    xong = _xong_json(tmp, so_dung_duoc, toi_thieu)
    profiles = tmp / "home" / "profiles"
    profiles.mkdir(parents=True, exist_ok=True)
    if co_kite:
        (profiles / "carousel-edu").mkdir(exist_ok=True)   # slug THAT (SLUG_CU anh xa "kite"-> day)
    cu_state, cu_home, cu_call = db.STATE_DIR, dgv.HERMES_HOME, db.call
    db.STATE_DIR, dgv.HERMES_HOME = tmp / "state", str(tmp / "home")
    db.call = lambda *a, **k: {"ok": True}
    try:
        return db._nut_ha_san("tok", "d1", _CQ())
    finally:
        db.STATE_DIR, dgv.HERMES_HOME, db.call = cu_state, cu_home, cu_call


# --------------------------------------------------------------- het duong
def test_het_duong_co_kite_giu_lai_nut_gui_kite_va_bo_han():
    """so=4 < san=5 (carousel.MIN_SLIDE), brand CO Kite -> ban phim phai con
    du hai nut: Gui Kite (imgkite) va Bo han (imgno). Truoc sua: keyboard=None
    -> _chot_nut go trang, ca hai duong noi trong `note` deu khong bam duoc."""
    with tempfile.TemporaryDirectory() as tmp:
        note, kb = _goi_ha_san(Path(tmp), so_dung_duoc=4, toi_thieu=8, co_kite=True)
        assert kb is not None, "khong con ban phim nao — dung loai bug 08/09/2026"
        hang = kb["inline_keyboard"][0]
        data = [b["callback_data"] for b in hang]
        assert "imgkite:d1" in data, f"thieu nut Gui Kite: {hang}"
        assert "imgno:d1" in data, f"thieu nut Bo han: {hang}"
        assert "4" in note and "5" in note


def test_het_duong_khong_co_kite_chi_con_bo_han():
    """Brand chua co Kite (dcgr): KHONG duoc hua nut Gui Kite se chi ra loi
    "khong co profile" — chi con Bo han, dung nguyen tac "khong hua suong" da
    ap dung o nhanh khong_kite cua _route_thieu_anh (anh_chuan_bi.py)."""
    with tempfile.TemporaryDirectory() as tmp:
        note, kb = _goi_ha_san(Path(tmp), so_dung_duoc=4, toi_thieu=8, co_kite=False)
        assert kb is not None
        hang = kb["inline_keyboard"][0]
        data = [b["callback_data"] for b in hang]
        assert "imgkite:d1" not in data, f"hua nut Kite nhung brand khong co Kite: {hang}"
        assert data == ["imgno:d1"], f"phai chi con dung mot nut Bo han: {hang}"


# ----------------------------------------------------- cac nhanh khac giu nguyen
def test_ha_san_thanh_cong_khong_dinh_ban_phim():
    """so=6 >= san=5, cu=8 > san -> ha san thanh cong, KHONG can ban phim moi
    (task da co the tiep tuc qua dre_nop.py, khong can bam gi them nua)."""
    with tempfile.TemporaryDirectory() as tmp:
        note, kb = _goi_ha_san(Path(tmp), so_dung_duoc=6, toi_thieu=8, co_kite=True)
        assert kb is None
        assert "Đã hạ sàn 8 → 5" in note


def test_da_o_san_toi_thieu_khong_dinh_ban_phim():
    """cu <= san (tin thuong, toi_thieu da la 5): khong co gi de ha them,
    keyboard van None nhu truoc gio."""
    with tempfile.TemporaryDirectory() as tmp:
        note, kb = _goi_ha_san(Path(tmp), so_dung_duoc=5, toi_thieu=5, co_kite=True)
        assert kb is None
        assert "Sàn đã ở mức tối thiểu" in note


# --------------------------------------------------------------- _chot_nut
def test_chot_nut_gan_dung_ban_phim_duoc_truyen():
    """_chot_nut phai dung keyboard duoc truyen vao, khong go trang nhu mac dinh."""
    goi = []
    cu_call = db.call
    db.call = lambda *a, **k: goi.append(k.get("reply_markup")) or {"ok": True}
    try:
        msg = {"chat": {"id": 1}, "message_id": 2, "text": "goc"}
        kb_moi = {"inline_keyboard": [[{"text": "x", "callback_data": "imgno:d1"}]]}
        db._chot_nut("tok", msg, "d1", "note", kb_moi)
        assert goi and goi[0] == kb_moi, f"khong dung keyboard truyen vao: {goi}"
    finally:
        db.call = cu_call


def test_chot_nut_mac_dinh_van_go_trang():
    """Khong truyen keyboard (cac nut khac: imgok/imgno/imgkite) -> hanh vi CU
    khong doi, ban phim van bi go trang."""
    goi = []
    cu_call = db.call
    db.call = lambda *a, **k: goi.append(k.get("reply_markup")) or {"ok": True}
    try:
        msg = {"chat": {"id": 1}, "message_id": 2, "text": "goc"}
        db._chot_nut("tok", msg, "d1", "note")
        assert goi and goi[0] == {"inline_keyboard": []}, f"phai go trang nhu cu: {goi}"
    finally:
        db.call = cu_call


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
