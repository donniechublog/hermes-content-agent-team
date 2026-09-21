#!/usr/bin/env python3
"""Chụp màn hình một trang ở DPR cao — thay `screenshot.js` (audit A6).

Dung khi URL KHONG phai mot tam anh tai ve duoc (tweet toan chu, bai bao, trang
chung chung). Anh chup 1x nhin mem; day chup o deviceScaleFactor 3 nen net that,
khong can upscaler nao. Uu tien khoi NOI DUNG chinh (tweet/article/main) thay vi
chup ca khung trang.

Bo ban Node vi Python cua du an da co Playwright — xem docstring image_frame.py.
Moi hang so duoi day chep tu screenshot.js, khong chinh lai.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from browser_session import (MOBILE_DPR, MOBILE_UA,             # noqa: E402
                           MOBILE_VIEWPORT, got_block, session_or_new)

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
FRAME = {"width": 820, "height": 1100}
DPR = 3                       # Retina — 3x pixel, net that
WAIT_LANG = 1200               # ms de anh/font toi muon kip on
WAIT_LAZY = 900                # ms sau cu cuon danh thuc anh lazy-load
LEAD_TRY = 8                  # so lan do lai khi chua thay anh hero (5 truot 1/2 lan tren theverge)
TIME_LIMIT = 45000               # ms cho goto

# Khoi noi dung chinh, thu theo thu tu. Nho hon nguong nay thi coi nhu bat nham
# mot hop rong/banner -> chup ca trang.
PICK = ("[data-testid=\"tweet\"]", "article", "main", ".entry-content")
MIN = 200


def capture(url: str, out_path, phien=None) -> bool:
    """Chup `url` ra `out_path`. True neu ra tep khac rong.

    `phien` (PhienBrowser, tuy chon): dung chung tien trinh Chromium voi cac
    buoc khac; khong truyen thi tu mo va tu dong."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        with session_or_new(phien) as ph:
            with ph.page(viewport=FRAME, device_scale_factor=DPR, user_agent=UA) as page:
                try:
                    page.goto(url, wait_until="networkidle", timeout=TIME_LIMIT)
                except Exception as e:                       # noqa: BLE001
                    # Ban Node cung nuot loi goto (`.catch(() => {})`): trang co
                    # the khong bao gio "networkidle" (quang cao, websocket) ma
                    # phan nhin duoc thi da xong.
                    print(f"[chup_trang] goto chua yen ({type(e).__name__}), chup phan da co",
                          file=sys.stderr)
                page.wait_for_timeout(WAIT_LANG)

                khoi = None
                for sel in PICK:
                    el = page.query_selector(sel)
                    if not el:
                        continue
                    hop = el.bounding_box()
                    if hop and hop["width"] > MIN and hop["height"] > MIN:
                        khoi = el
                        break
                if khoi is not None:
                    khoi.screenshot(path=str(out_path))
                else:
                    page.screenshot(path=str(out_path), full_page=True)
    except Exception as e:                                   # noqa: BLE001
        print(f"[chup_trang] {url[:70]}: {type(e).__name__}: {e!r}", file=sys.stderr)
        return False
    return out_path.exists() and out_path.stat().st_size > 0


# ---- KHOI LEAD o khung mobile ----------------------------------------------
# Ong Chu 06/09/2026, nhac lai 12/09: "vao trang nao chup thi cung hay duyet
# theo kich thuoc mobile, vi hinh luon dang o ratio 4:5" — va 12/09 chot cach
# dung lam bia: "cat lay khoi lead roi lam bia". Khoi lead = anh chinh + tit cua
# chinh bai do, tuc mot vat THAT cua tin, khac han anh khai niem Commons.
#
# Khong cat toi 4:5 o day: `prepare/vision.classify` da cat san 4:5/1:1 cho moi
# anh (`_save_crop`), cat hai lan la cat vao tit. O day chi chan hai dau: thap hon
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
  // Chi lay bo dam anh (img/picture) BEN TRONG figure, KHONG lay ca <figure>:
  // <figure><img>...</img><figcaption>Photo: Ann Wang/Reuters</figcaption></figure>
  // la khuon HTML pho bien — lay r cua ca figure keo theo chu chu thich nguon
  // anh, chong len chinh dong tieu de/quote ta ve sau (do that 13/09/2026, tin
  // TSMC: "gorodenkoff / Getty Images", "(Photo: Ann Wang/Reuters/file photo)"
  // deu la NOI DUNG cua trang, khong phai chu cua ta, van con trong tam chup).
  const chiAnh = (el) => {
    const t = (el.tagName || '').toLowerCase();
    if (t === 'img') return el;
    const img = el.querySelector('img, picture img, picture source');
    return img || el;
  };
  for (const goc_el of document.querySelectorAll('figure, picture, img')) {
    const el = chiAnh(goc_el);
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
  if (ir) return {top: ir.top, bottom: ir.bottom, left: ir.left, right: ir.right,
                  w: W, has_headline: !!hr, has_hero_image: true};
  // KHONG CO ANH HERO (bai kieu tieu luan: toan hoc, chinh sach) -> "capture man
  // hinh" dung nghia luat 06/09 (Ong Chu nhac lai 12/09: "tin ko co ten rieng
  // thi capture man hinh"): khoi TIT o khung dien thoai, tu mep tren tit xuong.
  if (!hr) return null;
  return {top: hr.top, bottom: hr.bottom, left: 0, right: W, w: W, has_headline: true, has_hero_image: false};
}"""


# Mau NEN THAT cua trang: leo tu body len documentElement, bo qua trong suot.
# Dung de dem quanh anh chup cho vua khung slide (Ong Chu 13/09/2026: "phu mot
# lop nen cung mau voi nen cua trang goc, sau do dat text va quote cua chung ta
# len") — khong crop mat gi, khong phai ghep doi, moi tam chup thanh MOT slide.
_JS_MAU_NEN = r"""() => {
  const trong = (c) => !c || c === 'transparent' || /rgba\(\s*0\s*,\s*0\s*,\s*0\s*,\s*0\s*\)/.test(c);
  for (const el of [document.body, document.documentElement]) {
    if (!el) continue;
    const c = getComputedStyle(el).backgroundColor;
    if (!trong(c)) return c;
  }
  return '#ffffff';
}"""


def _out_rgb(mau: str) -> tuple:
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


# LOW-336 (Ong Chu 21/09/2026): *"nguyen tac anh nay la chung cho moi role designer,
# ko bao gio de vien 2 ben, cung ko cat sat vao noi dung"*. Truoc do ham
# `count_background` (13/09) CAT BOT HAI BEN (dut chu o mep: "Functional" con
# "al") roi DEM DEN tam chup thanh 4:5 — mang den la pixel that, di theo tam anh
# vao the Ethan/slide Dre thanh vien hai ben va mang dac duoi day (IMAGE_RULES
# §7 "khong co mau nen dac o dau het"). Nay tam chup GIU TI LE TU NHIEN, chi bo
# phan TRONG o mep; lap khung la viec cua renderer (nen = chinh anh lam mo).


def frame_source_capture(src, out_path):
    """Lam sach mep tam chup trang nguon va dong dau `source_capture`.

    Khong cat vao noi dung, khong dem mau: day cat ngang dong chu thi lui ve hang
    trong, le dac hai ben thi got di (`image_rules_common.clean_capture_edges`).
    Tra (w, h) cua tam da luu."""
    from PIL import Image as _Im

    import image_provenance
    import image_rules_common
    im = image_rules_common.clean_capture_edges(_Im.open(src).convert("RGB"))
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    im.save(out_path, "PNG", pnginfo=image_provenance.stamp_provenance("source_capture"))
    return im.size


def capture_lead_mobile(url: str, out_path, phien=None) -> dict | None:
    """Chup KHOI LEAD cua `url` o khung mobile. -> dict mo ta, hoac None.

    None = trang chan bot, khong do duoc khoi lead (khong tit, khong anh lead),
    hoac chup hong; nguoi goi coi nhu nguon nay khong dung duoc va di tiep —
    KHONG dung anh rac.

    Ba buoc truoc khi do, moi buoc sinh ra tu mot tam anh hong do that
    12/09/2026: (1) `got_block` — arstechnica tra tuong "confirm you are human" ma
    van co <h1>, chup ra thi tam do len bia; (2) cuon xuong roi ve dau — anh hero
    lazy-load cua techcrunch chua bao gio tai, khoi lead chi con tit va mot o
    trong; (3) `_JS_AN_LOP_NOI` — banner dieu khoan cua theverge che kin nua duoi
    khoi lead."""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tit_trang = ""
    try:
        with session_or_new(phien) as ph:
            with ph.page(viewport=MOBILE_VIEWPORT, device_scale_factor=MOBILE_DPR,
                          is_mobile=True, has_touch=True, user_agent=MOBILE_UA) as page:
                resp = None
                try:
                    # `domcontentloaded`, KHONG `networkidle` — giong
                    # `ranking._try_source`. Do that tren may chu 12/09/2026:
                    # theverge KHONG BAO GIO yen (quang cao + websocket chay
                    # lien tuc) nen goto an tron 45s roi nem TimeoutError, toi
                    # luc do trang moi tai duoc mot phan va h1/anh hero chua
                    # hydrate -> "khong thay tit lan anh lead" 3/3 lan, trong
                    # khi may dev cung URL do lai qua. Doi DOM xong la du: nhip
                    # cuon danh thuc lazy + vong do lap ben duoi moi la thu
                    # quyet dinh khi nao anh san sang.
                    resp = page.goto(url, wait_until="domcontentloaded", timeout=TIME_LIMIT)
                except Exception as e:                       # noqa: BLE001
                    print(f"[chup_lead] goto chua yen ({type(e).__name__}), do phan da co",
                          file=sys.stderr)
                # Cuon xuong roi ve dau: anh hero cua nhieu bao la lazy-load, khong
                # cuon thi no chua bao gio duoc tai — khoi lead chup ra chi co tit
                # va mot o trong (do that tren techcrunch 12/09/2026).
                page.evaluate("window.scrollTo(0, window.innerHeight * 1.5)")
                page.wait_for_timeout(WAIT_LAZY)
                page.evaluate("window.scrollTo(0, 0)")
                page.wait_for_timeout(WAIT_LANG)
                # Tuong chan bot van co <h1> va van chup ra anh — ra mot tam
                # "Let's confirm you are human" lam bia (do that tren
                # arstechnica 12/09/2026). Nhan ra thi BO nguon, khong tim cach
                # vuot.
                tit_trang = (page.title() or "")[:200]
                mau_nen = page.evaluate(_JS_MAU_NEN) or "#ffffff"
                ly = got_block(tit_trang, resp.status if resp else None,
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
                for _ in range(LEAD_TRY):
                    r = page.evaluate(_JS_LEAD) or r
                    if r and r["has_hero_image"]:
                        break
                    page.wait_for_timeout(WAIT_LAZY)
                if not r:
                    print(f"[chup_lead] {url[:70]}: khong thay tit lan anh lead", file=sys.stderr)
                    return None
                # Clip DUNG khung anh hero, khong lay tit/byline. full_page: clip
                # theo toa do TAI LIEU; da cuon ve 0 nen toa do khung nhin trung
                # toa do tai lieu, anh nam duoi mot man van chup du.
                if r["has_hero_image"]:
                    if r["bottom"] - max(0, r["top"]) < 60:
                        print(f"[chup_lead] {url[:70]}: anh hero do ra cao {r['bottom']-max(0,r['top']):.0f}px, bo", file=sys.stderr)
                        return None
                    clip = {"x": max(0, r["left"]), "y": max(0, r["top"]),
                            "width": r["right"] - max(0, r["left"]),
                            "height": r["bottom"] - max(0, r["top"])}
                else:
                    # Khong co anh hero: khoi TIT, vuong theo be ngang may (tit + doan
                    # dau), dung nhu tam Wikipedia 1242x1242 do sang 12/09.
                    print(f"[chup_lead] {url[:70]}: khong co anh hero, chup khoi tit", file=sys.stderr)
                    clip = {"x": 0, "y": max(0, r["top"]), "width": r["w"], "height": r["w"]}
                page.screenshot(path=str(out_path), full_page=True, clip=clip)
    except Exception as e:                                   # noqa: BLE001
        print(f"[chup_lead] {url[:70]}: {type(e).__name__}: {e!r}", file=sys.stderr)
        return None
    if not (out_path.exists() and out_path.stat().st_size > 0):
        return None
    # `page_title` de nguoi goi doi chieu "co cung tin khong" (LOW-33) — trang
    # trong `page_url` co the la bao khac khop NHAM, khong duoc mac dinh la bai goc.
    return {"image_url": url, "page_url": url, "source": "capture_source", "capture_source": True, "page_title": tit_trang,
            "capture_kind": "hero" if r["has_hero_image"] else "headline", "background_color": mau_nen,
            "alt": "ảnh chính + tít của chính bài gốc, chụp ở khung điện thoại",
            "score_reason": "khối lead của trang nguồn"
                     + (", có tít" if r["has_headline"] else "")
                     + (", có ảnh chính" if r["has_hero_image"] else "")}


def main() -> int:
    ap = argparse.ArgumentParser(description="Chup mot trang o DPR cao (thay screenshot.js)")
    ap.add_argument("url")
    ap.add_argument("out")
    ap.add_argument("--lead-mobile", action="store_true",
                    help="chup KHOI LEAD (anh chinh + tit) o khung dien thoai")
    a = ap.parse_args()
    if a.lead_mobile:
        if not capture_lead_mobile(a.url, a.out):
            return 1
    elif not capture(a.url, a.out):
        return 1
    print(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
