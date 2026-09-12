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
from phien_browser import (MOBILE_DPR, MOBILE_UA,             # noqa: E402
                           MOBILE_VIEWPORT, bi_chan, phien_hoac_moi)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
KHUNG = {"width": 820, "height": 1100}
DPR = 3                       # Retina — 3x pixel, net that
CHO_LANG = 1200               # ms de anh/font toi muon kip on
CHO_LAZY = 900                # ms sau cu cuon danh thuc anh lazy-load
LEAD_THU = 8                  # so lan do lai khi chua thay anh hero (5 truot 1/2 lan tren theverge)
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


# ---- KHOI LEAD o khung mobile ----------------------------------------------
# Ong Chu 06/09/2026, nhac lai 12/09: "vao trang nao chup thi cung hay duyet
# theo kich thuoc mobile, vi hinh luon dang o ratio 4:5" — va 12/09 chot cach
# dung lam bia: "cat lay khoi lead roi lam bia". Khoi lead = anh chinh + tit cua
# chinh bai do, tuc mot vat THAT cua tin, khac han anh khai niem Commons.
#
# Khong cat toi 4:5 o day: `chuan_bi/nhin.phan_loai` da cat san 4:5/1:1 cho moi
# anh (`_luu_crop`), cat hai lan la cat vao tit. O day chi chan hai dau: thap hon
# vuong thi khong con la "khoi", cao hon 2:1 thi phan duoi chac chan la than bai.
# Chup DUNG khung anh hero cua bai, khong kem tit/byline (Ong Chu 12/09/2026
# chot lai sau ban "khoi lead": "dung anh hero trong main article lam thumbnail
# cho hero slide, vi anh do la chu nhat ngang, nen no hien thi vua van voi nua
# tren cua hero slide"). Tit cua bao khong lay: render_edu tu viet tit.

# LOP NOI che khoi lead: banner dong y cookie, header dinh, popup ban tin. Chi
# AN di khi chup (visibility:hidden) — KHONG bam "Dong y", khong bam nut dong:
# doc mot trang thi khong duoc thay nguoi dung chap nhan dieu khoan cua ho.
_JS_AN_LOP_NOI = """() => {
  const W = window.innerWidth, H = window.innerHeight;
  const chon = (ss) => { for (const s of ss) { const e = document.querySelector(s);
      if (e) { const r = e.getBoundingClientRect();
               if (r.width > 200 && r.height > 200) return e; } } return null; };
  const goc = chon(['[data-testid="tweet"]', 'article', 'main', '.entry-content']);
  let n = 0;
  for (const el of document.body.querySelectorAll('*')) {
    const cs = getComputedStyle(el);
    // CHI `fixed`. `sticky` tung nam trong danh sach nay va da an nham chinh anh
    // hero cua techcrunch (no nam trong mot khoi sticky ngoai <main>): banner
    // dong y / popup gan nhu luon la `fixed`, con `sticky` la noi dung trong dong.
    if (cs.position !== 'fixed') continue;
    const r = el.getBoundingClientRect();
    if (r.width * r.height < W * H * 0.02) continue;      // nho qua: khong che duoc gi
    if (goc && (el.contains(goc) || goc.contains(el))) continue;   // chinh khung bai
    el.style.setProperty('visibility', 'hidden', 'important');
    n++;
  }
  return n;
}"""

# Do TRONG trang: tra ve (top, bottom) cua khoi lead theo toa do khung nhin.
_JS_LEAD = """() => {
  const W = window.innerWidth, H = window.innerHeight;
  const chon = (ss) => { for (const s of ss) { const e = document.querySelector(s);
      if (e) { const r = e.getBoundingClientRect();
               if (r.width > 200 && r.height > 200) return e; } } return null; };
  const hop = chon(['[data-testid="tweet"]', 'article', 'main', '.entry-content']);
  const goc = hop || document.body;
  const h1 = goc.querySelector('h1') || document.querySelector('h1');
  const hr = h1 ? h1.getBoundingClientRect() : null;
  let ir = null;
  // Tim trong CA TRANG, khong chi trong `goc`: techcrunch dat anh hero NGOAI
  // <main>, loc theo `goc` thi khoi lead mat anh (do that 12/09/2026). Cai giu
  // cho khoi khop nham logo/quang cao la hai dieu kien duoi: du to, va dinh tit.
  for (const el of document.querySelectorAll('figure, picture, img')) {
    const r = el.getBoundingClientRect();
    if (r.width < W * 0.6 || r.height < 120) continue;       // qua nho: khong phai anh lead
    if (r.bottom <= 0 || r.top > H * 3) continue;            // o ngoai man (slot an, lazy chua dat cho)
    // Anh lead phai DINH voi tit — ngay tren no, hoac ngay duoi no. Khong rang
    // buoc chuyen do thi mot trang khong co anh dau bai (Wikipedia: anh nam
    // trong infobox giua bai) se keo khoi lead thanh mot buc tuong chu.
    if (!hr) { if (r.top < H * 1.5) { ir = r; break; } }
    else if (r.bottom <= hr.top + 40 || (r.top >= hr.top && r.top <= hr.bottom + H * 0.6)) {
      ir = r; break;
    }
  }
  // CHI ANH HERO, khong lay tit (Ong Chu 12/09/2026: "dung anh hero trong main
  // article lam thumbnail cho hero slide, vi anh do la chu nhat ngang, nen no
  // hien thi vua van voi nua tren"). Tit cua bao la thu render_edu tu viet.
  if (!ir) return null;
  return {top: ir.top, bottom: ir.bottom, left: ir.left, right: ir.right,
          w: W, co_tit: !!hr, co_anh: true};
}"""


# Mau NEN THAT cua trang: leo tu body len documentElement, bo qua trong suot.
# Dung de dem quanh anh chup cho vua khung slide (Ong Chu 13/09/2026: "phu mot
# lop nen cung mau voi nen cua trang goc, sau do dat text va quote cua chung ta
# len") — khong crop mat gi, khong phai ghep doi, moi tam chup thanh MOT slide.
_JS_MAU_NEN = """() => {
  const trong = (c) => !c || c === 'transparent' || /rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\s*\)/.test(c);
  for (const el of [document.body, document.documentElement]) {
    if (!el) continue;
    const c = getComputedStyle(el).backgroundColor;
    if (!trong(c)) return c;
  }
  return '#ffffff';
}"""


def _ra_rgb(mau: str) -> tuple:
    """'rgb(20, 20, 24)' | 'rgba(...)' | '#fff' -> (r, g, b). Khong doc duoc -> trang."""
    import re as _re
    m = _re.findall(r"[\d.]+", mau or "")
    if len(m) >= 3 and ("rgb" in (mau or "")):
        return tuple(min(255, max(0, int(float(x)))) for x in m[:3])
    h = (mau or "").strip().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    if len(h) == 6:
        try:
            return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
        except ValueError:
            pass
    return (255, 255, 255)


def dem_nen(anh_vao, ra, mau_nen: str, ti_le: float = 0.8, cao_tren: float = 0.42):
    """Dat anh chup vao giua khung `ti_le` (4:5), phan con lai to MAU NEN cua
    chinh trang do — ra mot tam dung mot minh lam slide duoc, khong crop mat
    gi, khong phai ghep cap.

    `cao_tren`: tam anh nam o dau theo chieu doc (0.42 = hoi len tren giua, chua
    cho chu o nua duoi nhu bo cuc carousel). Tra (w, h) cua tam da dem."""
    from PIL import Image as _Im
    im = _Im.open(anh_vao).convert("RGB")
    w, h = im.size
    W = max(w, 1080)
    H = int(round(W / ti_le))
    if h > H - 40:                      # anh cao hon khung: thu nho vua chieu cao
        ty = (H - 40) / h
        im = im.resize((max(1, int(w * ty)), max(1, int(h * ty))), _Im.LANCZOS)
        w, h = im.size
    if w > W - 40:
        tx = (W - 40) / w
        im = im.resize((max(1, int(w * tx)), max(1, int(h * tx))), _Im.LANCZOS)
        w, h = im.size
    nen = _Im.new("RGB", (W, H), _ra_rgb(mau_nen))
    y = int(round((H - h) * cao_tren))
    nen.paste(im, ((W - w) // 2, max(0, min(y, H - h))))
    ra = Path(ra)
    ra.parent.mkdir(parents=True, exist_ok=True)
    nen.save(ra, "PNG")
    return nen.size


def chup_lead_mobile(url: str, ra, phien=None) -> dict | None:
    """Chup KHOI LEAD cua `url` o khung mobile. -> dict mo ta, hoac None.

    None = trang chan bot, khong do duoc khoi lead (khong tit, khong anh lead),
    hoac chup hong; nguoi goi coi nhu nguon nay khong dung duoc va di tiep —
    KHONG dung anh rac.

    Ba buoc truoc khi do, moi buoc sinh ra tu mot tam anh hong do that
    12/09/2026: (1) `bi_chan` — arstechnica tra tuong "confirm you are human" ma
    van co <h1>, chup ra thi tam do len bia; (2) cuon xuong roi ve dau — anh hero
    lazy-load cua techcrunch chua bao gio tai, khoi lead chi con tit va mot o
    trong; (3) `_JS_AN_LOP_NOI` — banner dieu khoan cua theverge che kin nua duoi
    khoi lead."""
    ra = Path(ra)
    ra.parent.mkdir(parents=True, exist_ok=True)
    tit_trang = ""
    try:
        with phien_hoac_moi(phien) as ph:
            with ph.trang(viewport=MOBILE_VIEWPORT, device_scale_factor=MOBILE_DPR,
                          is_mobile=True, has_touch=True, user_agent=MOBILE_UA) as page:
                resp = None
                try:
                    # `domcontentloaded`, KHONG `networkidle` — giong
                    # `xep_hang._thu_nguon`. Do that tren may chu 12/09/2026:
                    # theverge KHONG BAO GIO yen (quang cao + websocket chay
                    # lien tuc) nen goto an tron 45s roi nem TimeoutError, toi
                    # luc do trang moi tai duoc mot phan va h1/anh hero chua
                    # hydrate -> "khong thay tit lan anh lead" 3/3 lan, trong
                    # khi may dev cung URL do lai qua. Doi DOM xong la du: nhip
                    # cuon danh thuc lazy + vong do lap ben duoi moi la thu
                    # quyet dinh khi nao anh san sang.
                    resp = page.goto(url, wait_until="domcontentloaded", timeout=GIO_HAN)
                except Exception as e:                       # noqa: BLE001
                    print(f"[chup_lead] goto chua yen ({type(e).__name__}), do phan da co",
                          file=sys.stderr)
                # Cuon xuong roi ve dau: anh hero cua nhieu bao la lazy-load, khong
                # cuon thi no chua bao gio duoc tai — khoi lead chup ra chi co tit
                # va mot o trong (do that tren techcrunch 12/09/2026).
                page.evaluate("window.scrollTo(0, window.innerHeight * 1.5)")
                page.wait_for_timeout(CHO_LAZY)
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(CHO_LANG)
                # Tuong chan bot van co <h1> va van chup ra anh — ra mot tam
                # "Let's confirm you are human" lam bia (do that tren
                # arstechnica 12/09/2026). Nhan ra thi BO nguon, khong tim cach
                # vuot.
                tit_trang = (page.title() or "")[:200]
                mau_nen = page.evaluate(_JS_MAU_NEN) or "#ffffff"
                ly = bi_chan(tit_trang, resp.status if resp else None,
                             page.evaluate("document.body ? document.body.innerText : ''") or "")
                if ly:
                    print(f"[chup_lead] {url[:70]}: trang chặn bot ({ly}), bỏ nguồn này",
                          file=sys.stderr)
                    return None
                n_an = page.evaluate(_JS_AN_LOP_NOI)
                if n_an:
                    print(f"[chup_lead] ẩn {n_an} lớp nổi (banner/header dính) khi chụp",
                          file=sys.stderr)
                # Do LAP: anh hero co the chua xong layout o nhip do dau (do
                # that: cung mot URL theverge ra 1581px co anh o luot nay va
                # 1242px khong anh o luot sau). Doi den khi THAY anh, hoac het
                # luot thi lay ban do cuoi — tit khong bao gio den muon.
                r = None
                for _ in range(LEAD_THU):
                    r = page.evaluate(_JS_LEAD) or r
                    if r and r["co_anh"]:
                        break
                    page.wait_for_timeout(CHO_LAZY)
                if not r:
                    print(f"[chup_lead] {url[:70]}: khong thay tit lan anh lead", file=sys.stderr)
                    return None
                # Clip DUNG khung anh hero, khong lay tit/byline. full_page: clip
                # theo toa do TAI LIEU; da cuon ve 0 nen toa do khung nhin trung
                # toa do tai lieu, anh nam duoi mot man van chup du.
                if r["bottom"] - max(0, r["top"]) < 60:
                    print(f"[chup_lead] {url[:70]}: anh hero do ra cao {r['bottom']-max(0,r['top']):.0f}px, bo", file=sys.stderr)
                    return None
                page.screenshot(path=str(ra), full_page=True,
                                clip={"x": max(0, r["left"]), "y": max(0, r["top"]),
                                      "width": r["right"] - max(0, r["left"]),
                                      "height": r["bottom"] - max(0, r["top"])})
    except Exception as e:                                   # noqa: BLE001
        print(f"[chup_lead] {url[:70]}: {type(e).__name__}: {e!r}", file=sys.stderr)
        return None
    if not (ra.exists() and ra.stat().st_size > 0):
        return None
    # `tit_trang` de nguoi goi doi chieu "co cung tin khong" (LOW-33) — trang
    # trong `trang` co the la bao khac khop NHAM, khong duoc mac dinh la bai goc.
    return {"anh": url, "trang": url, "tu": "chup_nguon", "chup_nguon": True, "tit_trang": tit_trang,
            "mau_nen": mau_nen,
            "alt": "ảnh chính + tít của chính bài gốc, chụp ở khung điện thoại",
            "ly_do": "khối lead của trang nguồn"
                     + (", có tít" if r["co_tit"] else "")
                     + (", có ảnh chính" if r["co_anh"] else "")}


def main() -> int:
    ap = argparse.ArgumentParser(description="Chup mot trang o DPR cao (thay screenshot.js)")
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--lead-mobile", action="store_true",
                    help="chup KHOI LEAD (anh chinh + tit) o khung dien thoai")
    a = ap.parse_args()
    if a.lead_mobile:
        if not chup_lead_mobile(a.url, a.out):
            return 1
    elif not chup(a.url, a.out):
        return 1
    print(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
