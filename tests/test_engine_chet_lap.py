#!/usr/bin/env python3
"""LOW-28 (12/09/2026): engine chet bat thuong lap tren MOT draft thi DUNG va bao.

t_24b214a6: SIGSEGV 3 lan, vai tu `rm -f dang_chay.pid` roi goi lai 16 lan trong
50 phut — khong co gi noi "thoi". Gio `_doi_khoa` bao ve khoa mo coi, `dem_chet`
dem, `chay()` dung o TOI_DA_CHET va goi `_bao_chet_lap`. Fail tren code cu
(chua co dem_chet / _doi_khoa tra None), pass tren code moi.

Chay:  venv/bin/python tests/test_engine_chet_lap.py
"""
import ast
import io
import sys
import tempfile
from contextlib import redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import anh_chuan_bi as cb                                    # noqa: E402


def test_doi_khoa_bao_mo_coi():
    with tempfile.TemporaryDirectory() as tmp:
        khoa = Path(tmp) / "dang_chay.pid"
        with redirect_stderr(io.StringIO()):
            assert cb._doi_khoa(khoa, 5, "d") is False          # khong co khoa
            khoa.write_text("999999999")
            assert cb._doi_khoa(khoa, 5, "d") is True           # mo coi
        assert not khoa.exists()


def test_dem_chet_tang_theo_mo_coi_va_ve_0_khi_lam_moi():
    with tempfile.TemporaryDirectory() as tmp:
        wd = Path(tmp)
        assert cb.dem_chet(wd, False) == 0
        assert cb.dem_chet(wd, True) == 1
        assert cb.dem_chet(wd, True) == 2
        assert cb.dem_chet(wd, False) == 2                       # khong mo coi: giu nguyen
        assert cb.dem_chet(wd, False, lam_moi=True) == 0
        assert cb.dem_chet(wd, False) == 0


def test_toi_da_chet_la_hai():
    assert cb.TOI_DA_CHET == 2


def test_chay_dung_o_toi_da_va_bao():
    """Cong o muc ma nguon: `chay()` phai goi dem_chet, so voi TOI_DA_CHET, goi
    _bao_chet_lap va sys.exit — khong test duoc bang chay that (can meta draft +
    browser), nen doc AST cua chay() nhu cong _vong_thuong_hieu (10/09/2026)."""
    src = (ROOT / "anh_chuan_bi.py").read_text(encoding="utf-8")
    ham = next(n for n in ast.walk(ast.parse(src))
               if isinstance(n, ast.FunctionDef) and n.name == "chay")
    goi = {n.func.id for n in ast.walk(ham)
           if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    ten = {n.id for n in ast.walk(ham) if isinstance(n, ast.Name)}
    assert {"dem_chet", "_bao_chet_lap", "_doi_khoa"} <= goi, goi
    assert "TOI_DA_CHET" in ten
    assert any(isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
               and n.func.attr == "exit" for n in ast.walk(ham)), "chay() phai sys.exit khi chet lap"


def test_bao_chet_lap_gui_dung_topic_va_khong_nem():
    """Stub publish.gui_topic: test KHONG duoc gui Telegram that (tren may chu co token)."""
    import publish
    gui = []
    cu = publish.gui_topic
    publish.gui_topic = lambda text, vai: gui.append((vai, text)) or True
    try:
        with redirect_stderr(io.StringIO()):
            cb._bao_chet_lap("draft-khong-ton-tai", 2)
    finally:
        publish.gui_topic = cu
    assert len(gui) == 1 and gui[0][0] == cb.vai.MAC_DINH_ANH, gui
    assert "2 lần" in gui[0][1] and "draft-khong-ton-tai" in gui[0][1], gui
    # gui_topic nem thi _bao_chet_lap van khong nem
    publish.gui_topic = lambda text, vai: (_ for _ in ()).throw(RuntimeError("x"))
    try:
        with redirect_stderr(io.StringIO()):
            cb._bao_chet_lap("d", 3)
    finally:
        publish.gui_topic = cu


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
