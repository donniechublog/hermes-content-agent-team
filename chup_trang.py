#!/usr/bin/env python3
"""Chụp màn hình một trang ở DPR cao — thay `screenshot.js` (audit A6).

Dung khi URL KHONG phai mot tam anh tai ve duoc (tweet toan chu, bai bao, trang
chung chung). Anh chup 1x nhin mem; day chup o deviceScaleFactor 3 nen net that,
khong can upscaler nao. Uu tien khoi NOI DUNG chinh (tweet/article/main) thay vi
chup ca khung trang.

Bo ban Node vi Python cua du an da co Playwright — xem docstring khung_anh.py.
Moi hang so duoi day chep tu screenshot.js, khong chinh lai.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from phien_browser import phien_hoac_moi                      # noqa: E402

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
KHUNG = {"width": 820, "height": 1100}
DPR = 3                       # Retina — 3x pixel, net that
CHO_LANG = 1200               # ms de anh/font toi muon kip on
GIO_HAN = 45000               # ms cho goto

# Khoi noi dung chinh, thu theo thu tu. Nho hon nguong nay thi coi nhu bat nham
# mot hop rong/banner -> chup ca trang.
CHON = ("[data-testid=\"tweet\"]", "article", "main", ".entry-content")
TOI_THIEU = 200


def chup(url: str, ra, phien=None) -> bool:
    """Chup `url` ra `ra`. True neu ra tep khac rong.

    `phien` (PhienBrowser, tuy chon): dung chung tien trinh Chromium voi cac
    buoc khac; khong truyen thi tu mo va tu dong."""
    ra = Path(ra)
    ra.parent.mkdir(parents=True, exist_ok=True)
    try:
        with phien_hoac_moi(phien) as ph:
            with ph.trang(viewport=KHUNG, device_scale_factor=DPR, user_agent=UA) as page:
                try:
                    page.goto(url, wait_until="networkidle", timeout=GIO_HAN)
                except Exception as e:                       # noqa: BLE001
                    # Ban Node cung nuot loi goto (`.catch(() => {})`): trang co
                    # the khong bao gio "networkidle" (quang cao, websocket) ma
                    # phan nhin duoc thi da xong.
                    print(f"[chup_trang] goto chua yen ({type(e).__name__}), chup phan da co",
                          file=sys.stderr)
                page.wait_for_timeout(CHO_LANG)

                khoi = None
                for sel in CHON:
                    el = page.query_selector(sel)
                    if not el:
                        continue
                    hop = el.bounding_box()
                    if hop and hop["width"] > TOI_THIEU and hop["height"] > TOI_THIEU:
                        khoi = el
                        break
                if khoi is not None:
                    khoi.screenshot(path=str(ra))
                else:
                    page.screenshot(path=str(ra), full_page=True)
    except Exception as e:                                   # noqa: BLE001
        print(f"[chup_trang] {url[:70]}: {type(e).__name__}: {e!r}", file=sys.stderr)
        return False
    return ra.exists() and ra.stat().st_size > 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Chup mot trang o DPR cao (thay screenshot.js)")
    ap.add_argument("url")
    ap.add_argument("out")
    a = ap.parse_args()
    if not chup(a.url, a.out):
        return 1
    print(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
