#!/usr/bin/env python3
"""LOW-23 (12/09/2026): canh bao "khong phan hoi" phai do LAN CHAY HIEN TAI va
noi dung trang thai; task bi hermes giet (timed_out) phai duoc bao.

Ca that t_24b214a6: hai run 25.1 phut deu timed_out, heartbeat moi 60s suot,
Telegram noi "khong phan hoi hon 20 phut" roi im lang khi bi giet. Dung harness
cua test_bao_treo (kanban/telegram gia), them stub cho ba ham moi cua
hermes_adapter. Fail tren code cu (khong co moc_lan_chay/cau_chay_lau), pass
tren code moi.

Chay:  venv/bin/python tests/test_bao_treo_lan_chay.py
"""
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT)); sys.path.insert(0, str(ROOT / "tests"))
import duyet_giao_viec as dg                                  # noqa: E402
from test_bao_treo import _chay_bao_tien_do_gia               # noqa: E402


def _voi_stub(moc, nhip, lan_cuoi, pid_song, rows, tmp):
    ha = dg.hermes_adapter
    cu = (ha.moc_lan_chay, ha.nhip_tho, ha.lan_chay_cuoi_nhieu, ha.pid_song)
    ha.moc_lan_chay = lambda db=None: moc
    ha.nhip_tho = lambda tids, db=None: nhip
    ha.lan_chay_cuoi_nhieu = lambda tids: lan_cuoi
    ha.pid_song = lambda pid: pid_song
    gui = []
    try:
        _chay_bao_tien_do_gia(tmp, rows, gui)
    finally:
        ha.moc_lan_chay, ha.nhip_tho, ha.lan_chay_cuoi_nhieu, ha.pid_song = cu
    return gui


def _row(now, bat_dau_luc, st="running"):
    return [{"id": "t_1", "vai": "miles", "trang_thai": st, "tieu_de": "Bai test",
             "tao_luc": now - 5000, "bat_dau_luc": bat_dau_luc,
             "xong_luc": None, "ket_qua": None, "loi": None}]


def test_retry_moi_30s_khong_bi_bao_du_started_at_40_phut():
    now = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        gui = _voi_stub({"t_1": (now - 30, 188)}, {"t_1": (now - 10, 4242)}, {}, True,
                        _row(now, now - 40 * 60), tmp)
    assert not any("phút" in t and "⚠️" in t for t in gui), gui
    assert any(t.startswith("▶️") for t in gui), gui


def test_dang_lam_co_nhip_tho_thi_noi_dang_lam_khong_noi_khong_phan_hoi():
    now = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        gui = _voi_stub({"t_1": (now - 22 * 60, 188)}, {"t_1": (now - 40, 4242)}, {}, True,
                        _row(now, now - 22 * 60), tmp)
    treo = [t for t in gui if "⏳" in t]
    assert treo and "vẫn đang làm" in treo[0], gui
    assert not any("không phản hồi" in t for t in gui), gui


def test_im_lang_that_thi_noi_khong_phan_hoi_kem_moc_nhip_cuoi():
    now = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        gui = _voi_stub({"t_1": (now - 22 * 60, 188)}, {"t_1": (now - 9 * 60, 4242)}, {}, True,
                        _row(now, now - 22 * 60), tmp)
    t = [x for x in gui if "không phản hồi" in x]
    assert t and "nhịp thở cuối" in t[0] and "9 phút" in t[0], gui


def test_worker_chet_thi_noi_da_chet():
    now = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        gui = _voi_stub({"t_1": (now - 22 * 60, 188)}, {"t_1": (now - 60, 4242)}, {}, False,
                        _row(now, now - 22 * 60), tmp)
    assert any("đã chết" in t and "4242" in t for t in gui), gui


def test_timed_out_duoc_bao_mot_lan_moi_run():
    now = time.time()
    lc = {"t_1": {"trang_thai": "timed_out", "id_lan_chay": 184, "tom_tat": "", "loi": "x",
                  "metadata": {"elapsed_seconds": 1502, "limit_seconds": 1500}}}
    with tempfile.TemporaryDirectory() as tmp:
        gui = _voi_stub({}, {}, lc, None, _row(now, now - 1600, st="ready"), tmp)
        t = [x for x in gui if "⏱" in x]
        assert t and "25 phút" in t[0] and "trần 25 phút" in t[0], gui
        da = json.loads((Path(tmp) / "da_bao_tien_do.json").read_text(encoding="utf-8"))
        assert da.get("t_1:timed_out:184") is True, da
        # vong sau, cung run -> KHONG bao lai
        gui2 = _voi_stub({}, {}, lc, None, _row(now, now - 1600, st="ready"), tmp)
        assert not any("⏱" in x for x in gui2), gui2
        # run moi timed_out (188) -> bao lai
        lc["t_1"]["id_lan_chay"] = 188
        gui3 = _voi_stub({}, {}, lc, None, _row(now, now - 1600, st="ready"), tmp)
        assert any("⏱" in x for x in gui3), gui3


if __name__ == "__main__":
    ok = 0
    ten = [k for k in list(globals()) if k.startswith("test_")]
    for k in ten:
        try:
            globals()[k]()
            ok += 1
        except AssertionError as e:
            print(f"    FAIL {k}: {e}")
    print(f"{Path(__file__).name:<34} {ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
