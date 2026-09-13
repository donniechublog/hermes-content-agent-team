#!/usr/bin/env python3
"""Mot phien Chromium dung chung cho ca mot bai (audit_content_team B4).

Vi sao: engine mo toi BON tien trinh Chromium cho MOT bai — browser_pass (boc
anh trong trang), nguon_bai.giai_ma_gnews (theo chuyen huong Google News), va
xep_hang co the chup HAI lan (bang cua tin xep hang, roi bang lam boi canh cho
tin thuong). Moi lan launch ton 1-2s va vai tram MB, trong khi ca bon deu chay
noi tiep trong cung mot tien trinh engine.

Phien nay giu browser theo BO THAM SO: hai noi xin cung mot bo args thi dung
chung mot tien trinh, khac bo args thi moi tien trinh rieng. Vi sao khong gop
het lam mot: xep_hang launch kem `--force-color-profile=srgb` de mau anh chup
tat dinh, hai cho kia thi khong — gop bua la lang le doi cach xu ly mau cua anh
chup trong trang. Muon gop hoan toan thi phai co y quyet dinh srgb cho tat ca,
va nhin lai anh that truoc khi chot.

Cach ly loi: moi buoc lay mot `new_context()` rieng roi dong ngay, nen mot trang
lam hong context khong keo theo cac buoc sau; chi TIEN TRINH browser la dung chung.

NUA SAU CUA B4 (thay 20 cho `wait_for_timeout` co dinh) — DA SOI, KET LUAN LA
KHONG DOI DUOC TU XA. Ghi lai day de lan sau khoi soi lai, va de khong ai bien
mot cho `settle` thanh cho doi selector roi lam anh chup vo:

  1. SETTLE sau cuon/resize/animation, TRUOC khi do hoac chup (13 cho):
     browser.py:82,100 · chup_chart.py:141,155,161 · render_edu.py:1414 ·
     xep_hang.py:522,538,567,615,809,812,857. Khong co dieu kien DOM nao de
     doi — cai dang doi la layout/font/animation da yen chua, ma chuyen do chi
     nhin trang THAT moi biet. Audit cung noi "chi giu wait_for_timeout o noi
     co animation chart".
  2. NHIP POLL trong mot vong da doi theo dieu kien (3 cho): browser.py:126 ·
     nguon_bai.py (vong doi Google News nha URL) · xep_hang.py:468. O day
     `wait_for_timeout` la khoang cach giua hai lan kiem — dung nhu vay roi.
  3. Cho Cloudflare/interstitial kip hien de doc `page.title()` (2 cho):
     xep_hang.py:994,1015. Doi mot dieu kien o day la doi chinh cai minh dang
     dinh phat hien.
  4. `xep_hang._doi_bang:457` nhin thi tuong thay duoc bang `wait_for_selector`
     theo dung selector o dong 461 — nhung 1200ms do la settle TRUOC khi bat
     dau do, bo di la doi thoi diem kiem DOM lan dau. Docstring ngay tren no
     ghi "Cho co dinh 6s la danh bac": cho nay ho da bi timing can mot lan roi.

Muon lam not: phai mo duoc cac trang xep hang that va doi chieu anh chup truoc/
sau, khong phai doc ma.

Dung:
    with PhienBrowser() as phien:
        with phien.trang(viewport={"width": 1600, "height": 1200}) as page:
            page.goto(...)

Ham nao nhan `phien` tuy chon thi dung `phien_hoac_moi`:
    with phien_hoac_moi(phien) as ph:      # phien=None -> tu mo, tu dong
        with ph.trang() as page:
            ...
"""
import contextlib
import re
import sys
import threading

ARGS_DEFAULT = ("--no-sandbox", "--disable-dev-shm-usage")

# KHUNG MOBILE — mot ban duy nhat cho ca doi (Ong Chu 06/09/2026, nhac lai
# 12/09/2026): "vao trang nao chup thi cung hay duyet theo kich thuoc mobile, vi
# hinh luon dang o ratio 4:5". 414px * DPR 3 = 1242px, gan khop kho the 1200px
# nen chu gan nhu khong bi co; desktop 2400 * DPR 2 = 4800px phai co bon lan.
# O day chu khong o xep_hang.py: tu 12/09 ca `chup_trang` (chup trang nguon lam
# anh bia) lan `xep_hang` (chup bang) cung dung, chep doi thi mot ngay nao do
# hai cho lech nhau ma khong ai thay.
MOBILE_VIEWPORT = {"width": 414, "height": 896}
MOBILE_DPR = 3
MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
             "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")

# TUONG CHAN BOT: khong phai noi dung trang, va KHONG duoc co vuot qua — chi
# nhan ra roi bo nguon do. Truoc 12/09/2026 phep thu nay nam inline trong
# `xep_hang._thu_nguon`; `chup_trang` chup lead khong co no nen mot trang chan
# bot ra tam anh "Let's confirm you are human" chay thang len bia (do that tren
# arstechnica 12/09).
CODE_BLOCK = (403, 429, 503)
_DAU_CHAN = re.compile(r"just a moment|security verification|attention required|access denied|"
                       r"confirm you are human|verify you are human|are you a robot|"
                       r"checking your browser|enable javascript and cookies", re.I)


def got_block(tieu_de: str = "", ma=None, chu: str = "") -> str:
    """Trang nay co phai tuong chan bot khong -> ly do, hoac "" neu khong.

    Thuan, test duoc. `chu` la chu nhin thay duoc cua trang: mot so tuong chan
    giu nguyen <title> cua bai (arstechnica) nen chi doc tieu de la bo sot —
    nhung chi xet khi trang NGAN, vi mot bai that viet ve chan bot cung chua
    dung cac cum nay."""
    if ma in CODE_BLOCK:
        return f"HTTP {ma}"
    for nguon, nhan in ((tieu_de, "tiêu đề"), (chu[:600] if len(chu) < 1200 else "", "nội dung")):
        m = _DAU_CHAN.search(nguon or "")
        if m:
            return f"{nhan}: {m.group(0)!r}"
    return ""


class BrowserSession:
    """Giu cac tien trinh Chromium dung chung, mo LUOI theo bo tham so."""

    def __init__(self):
        self._pw = None
        self._browser = {}            # tuple(args) -> Browser
        self._khoa = threading.Lock()  # check-then-launch khong khoa la 2 Chromium, giu 1 (B-r2-4)

    def __enter__(self):
        return self

    def __exit__(self, *_e):
        self.dong()
        return False

    def browser(self, args=ARGS_DEFAULT):
        """Browser cho bo `args` nay, mo neu chua co.

        Mo LUOI: bai khong dung browser (vd --khong-browser) thi khong ton mot
        tien trinh Chromium nao."""
        khoa = tuple(args)
        with self._khoa:
            b = self._browser.get(khoa)
            # Browser chet giua bai (Chromium crash/OOM, bi kill) ma van nam
            # trong cache thi MOI buoc sau cua cung bai deu TargetClosedError —
            # anh_chuan_bi dung MOT phien cho ca 5 buoc, nen truoc B4 mot crash
            # chi mat mot buoc, sau B4 mat ca gnews/xep_hang/vong_bu (audit
            # lượt 2, N-r2-1). Mo lai thay vi tra xac.
            if b is not None and not b.is_connected():
                print(f"[phien] browser {khoa} da chet, mo lai", file=sys.stderr)
                with contextlib.suppress(Exception):
                    b.close()
                b = None
            if b is None:
                if self._pw is None:
                    from playwright.sync_api import sync_playwright
                    self._pw = sync_playwright().start()
                b = self._browser[khoa] = self._pw.chromium.launch(args=list(khoa))
        return b

    @contextlib.contextmanager
    def trang(self, args=ARGS_DEFAULT, **ctx):
        """Mot context+page rieng, dong ngay sau khi dung (cach ly loi)."""
        c = self.browser(args).new_context(**ctx)
        try:
            yield c.new_page()
        finally:
            with contextlib.suppress(Exception):
                c.close()

    def dong(self):
        """Dong moi thu. Nuot loi: dong browser hong khong duoc lam hong ca bai,
        va tien trinh con dang chet cung khong con gi de cuu."""
        for b in self._browser.values():
            try:
                b.close()
            except Exception as e:                           # noqa: BLE001
                print(f"[phien] dong browser loi: {type(e).__name__}: {e!r}", file=sys.stderr)
        self._browser.clear()
        if self._pw is not None:
            try:
                self._pw.stop()
            except Exception as e:                           # noqa: BLE001
                print(f"[phien] dung playwright loi: {type(e).__name__}: {e!r}", file=sys.stderr)
            self._pw = None


@contextlib.contextmanager
def session_or_new(phien):
    """Dung `phien` dang co, hoac mo mot phien RIENG va dong khi xong.

    Nho vay moi ham van chay doc lap duoc nhu truoc (chay tay, test, tien trinh
    rieng) ma khong phai bat nguoi goi dung phien chung."""
    if phien is not None:
        yield phien
        return
    with BrowserSession() as moi:
        yield moi
