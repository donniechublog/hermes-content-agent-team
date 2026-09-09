#!/usr/bin/env python3
"""Một phiên Chromium dùng chung cho cả một bài (issue B4).

Truoc 09/09/2026 mot bai co the mo toi BON tien trinh Chromium: nap_nguon (giai
link Google News), browser_pass, va xep_hang chup hai lan. Tep nay giu ba tinh
chat cua phien dung chung:

  1. Mo LUOI — bai khong dung browser thi khong ton tien trinh nao.
  2. Cung bo tham so thi DUNG CHUNG mot tien trinh; khac bo tham so thi rieng
     (xep_hang ep --force-color-profile=srgb, gop bua la doi cach xu ly mau).
  3. Nguoi MUON phien khong duoc dong no — chi nguoi mo moi dong. Ro ri tien
     trinh chromium dung la su co da ghi trong xep_hang.py.

Khong can playwright that: thay `sync_playwright` bang ban gia.

Chay:  venv/bin/python tests/test_phien_browser.py
"""
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import phien_browser as pb                                    # noqa: E402


class _BrowserGia:
    def __init__(self, args):
        self.args = list(args)
        self.da_dong = False
        self.context = []

    def new_context(self, **kw):
        c = _CtxGia(kw)
        self.context.append(c)
        return c

    def close(self):
        self.da_dong = True

    def is_connected(self):
        # Chromium that tra False sau khi tien trinh chet/bi kill (N-r2-1)
        return not self.da_dong and not getattr(self, "chet", False)


class _CtxGia:
    def __init__(self, kw):
        self.kw = kw
        self.da_dong = False

    def new_page(self):
        return f"page-cua-{id(self)}"

    def close(self):
        self.da_dong = True


class _PwGia:
    def __init__(self):
        self.da_dung = False
        self.chromium = types.SimpleNamespace(launch=self._launch)
        self.da_launch = []

    def _launch(self, args=None):
        b = _BrowserGia(args or [])
        self.da_launch.append(b)
        return b

    def stop(self):
        self.da_dung = True


def _gia():
    """Cai playwright gia vao sys.modules, tra ve doi tuong theo doi."""
    pw = _PwGia()
    mod = types.ModuleType("playwright")
    sub = types.ModuleType("playwright.sync_api")
    sub.sync_playwright = lambda: types.SimpleNamespace(start=lambda: pw)
    mod.sync_api = sub
    sys.modules["playwright"] = mod
    sys.modules["playwright.sync_api"] = sub
    return pw


def _go():
    sys.modules.pop("playwright", None)
    sys.modules.pop("playwright.sync_api", None)


def test_mo_luoi_khong_dung_thi_khong_launch():
    """Bai chay --khong-browser khong duoc ton mot tien trinh Chromium nao."""
    pw = _gia()
    try:
        with pb.PhienBrowser():
            pass
        assert pw.da_launch == [], "mo Chromium du khong ai xin"
    finally:
        _go()


def test_cung_tham_so_thi_dung_chung_mot_tien_trinh():
    pw = _gia()
    try:
        with pb.PhienBrowser() as ph:
            a = ph.browser()
            b = ph.browser()
            c = ph.browser(pb.ARGS_MAC_DINH)
        assert a is b is c, "cung bo args ma launch nhieu lan"
        assert len(pw.da_launch) == 1, pw.da_launch
    finally:
        _go()


def test_khac_tham_so_thi_tien_trinh_rieng():
    """xep_hang ep srgb — gop chung la lang le doi cach xu ly mau anh chup."""
    pw = _gia()
    try:
        srgb = tuple(pb.ARGS_MAC_DINH) + ("--force-color-profile=srgb",)
        with pb.PhienBrowser() as ph:
            a = ph.browser()
            b = ph.browser(srgb)
        assert a is not b, "hai bo args khac nhau ma dung chung mot tien trinh"
        assert len(pw.da_launch) == 2
        assert "--force-color-profile=srgb" in b.args and "--force-color-profile=srgb" not in a.args
    finally:
        _go()


def test_browser_chet_giua_bai_thi_mo_lai_khong_tra_xac():
    """N-r2-1: Chromium crash/OOM giua bai — B4 dung MOT phien cho ca 5 buoc,
    nen tra lai browser da chet la 4 buoc sau deu TargetClosedError. Phai mo lai."""
    pw = _gia()
    with pb.PhienBrowser() as ph:
        b1 = ph.browser()
        b1.chet = True                       # tien trinh chet, doi tuong van trong cache
        b2 = ph.browser()
        assert b2 is not b1, "tra lai browser da chet"
        assert len(pw.da_launch) == 2, pw.da_launch
        assert ph.browser() is b2, "browser song thi van dung chung"


def test_ra_khoi_khoi_thi_dong_het():
    pw = _gia()
    try:
        with pb.PhienBrowser() as ph:
            b = ph.browser()
        assert b.da_dong, "khong dong browser khi ra khoi khoi"
        assert pw.da_dung, "khong dung playwright khi ra khoi khoi"
    finally:
        _go()


def test_trang_dong_context_ngay_de_cach_ly_loi():
    pw = _gia()
    try:
        with pb.PhienBrowser() as ph:
            with ph.trang(viewport={"width": 100, "height": 100}) as page:
                assert page.startswith("page-cua-")
            ctx = pw.da_launch[0].context[0]
            assert ctx.da_dong, "context phai dong ngay sau khi dung"
            assert ctx.kw["viewport"] == {"width": 100, "height": 100}
    finally:
        _go()


def test_context_dong_ca_khi_than_nem():
    pw = _gia()
    try:
        with pb.PhienBrowser() as ph:
            try:
                with ph.trang():
                    raise RuntimeError("vo giua chung")
            except RuntimeError:
                pass
            assert pw.da_launch[0].context[0].da_dong, "than nem thi context bi bo lai"
    finally:
        _go()


# ------------------------------------------------------------ phien_hoac_moi
def test_khong_truyen_phien_thi_tu_mo_va_TU_DONG():
    _gia()
    try:
        with pb.phien_hoac_moi(None) as ph:
            b = ph.browser()
        assert b.da_dong, "phien tu mo ma khong tu dong -> ro ri tien trinh"
    finally:
        _go()


def test_muon_phien_thi_KHONG_duoc_dong_cua_nguoi_khac():
    """Tinh chat quan trong nhat: ham nhan `phien` tu ngoai chi MUON. Dong no la
    cac buoc sau cua cung bai mat browser giua chung."""
    pw = _gia()
    try:
        with pb.PhienBrowser() as chung:
            b = chung.browser()
            with pb.phien_hoac_moi(chung) as ph:
                assert ph is chung
            assert not b.da_dong, "nguoi muon da dong phien cua nguoi khac"
            assert not pw.da_dung
        assert b.da_dong, "nguoi mo phai dong khi ra khoi khoi cua minh"
    finally:
        _go()


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
