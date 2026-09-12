#!/usr/bin/env python3
"""LOW-26 (12/09/2026): khoa `dang_chay.pid` cua engine chuan bi anh.

t_24b214a6: ethan_chuan_bi.py chet SIGSEGV (exit 139) ba lan, khoa nam lai; lan
chay dau doi tron 300s (= tran bash tool cua vai) roi bi cat `exit 124`. Test:
  - khoa mo coi (pid chet) -> don NGAY, khong ngu mot giay nao, co dong log;
  - pid con song -> doi toi `cho` roi thoat bang SystemExit, KHONG ghi de khoa;
  - `cho` mac dinh phai nho han han 300.
Fail tren code cu (khong co _doi_khoa; cho=300), pass tren code moi.

Chay:  venv/bin/python tests/test_khoa_chuan_bi.py
"""
import io
import os
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import anh_chuan_bi as cb                                    # noqa: E402


def test_cho_mac_dinh_nho_han_tran_bash_cua_vai():
    assert cb.CHO_KHOA_GIAY <= 60, cb.CHO_KHOA_GIAY
    assert cb.chay.__defaults__[2] == cb.CHO_KHOA_GIAY        # (lam_moi, khong_browser, cho, ...)


def test_khoa_mo_coi_don_ngay_khong_doi():
    with tempfile.TemporaryDirectory() as tmp:
        khoa = Path(tmp) / "dang_chay.pid"
        khoa.write_text("999999999")                          # pid khong ton tai
        ngu = []
        err = io.StringIO()
        with redirect_stderr(err):
            cb._doi_khoa(khoa, 60, "draft-x", ngu=lambda s: ngu.append(s))
        assert not khoa.exists(), "khoa mo coi phai bi don"
        assert ngu == [], f"khong duoc ngu: {ngu}"
        assert "mo coi" in err.getvalue(), err.getvalue()


def test_pid_song_thi_doi_roi_thoat_khong_ghi_de():
    with tempfile.TemporaryDirectory() as tmp:
        khoa = Path(tmp) / "dang_chay.pid"
        khoa.write_text(str(os.getpid()))                    # chinh minh: chac chan song
        ngu = []
        # `ngu` gia: moi lan goi dich dong ho ao bang cach ghi lai; het `cho` nho
        cb.time_goc = cb.time
        t = [0.0]

        class _T:
            @staticmethod
            def time():
                return t[0]

            @staticmethod
            def sleep(s):
                ngu.append(s)
                t[0] += s
        cb.time = _T
        try:
            with redirect_stderr(io.StringIO()):
                try:
                    cb._doi_khoa(khoa, 7, "draft-x", ngu=_T.sleep)
                    raise AssertionError("phai thoat bang SystemExit")
                except SystemExit as e:
                    assert "van dang chuan bi" in str(e), str(e)
        finally:
            cb.time = cb.time_goc
        assert khoa.exists() and khoa.read_text() == str(os.getpid()), "khong duoc ghi de/xoa khoa cua pid song"
        assert ngu, "phai co doi"


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
