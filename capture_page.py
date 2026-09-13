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


def capture(url: str, ra, phien=None) -> bool:
    """Chup `url` ra `ra`. True neu ra tep khac rong.

    `phien` (PhienBrowser, tuy chon): dung chung tien trinh Chromium voi cac
    buoc khac; khong truyen thi tu mo va tu dong."""
    ra = Path(ra)
    ra.parent.mkdir(parents=True, exist_ok=True)
    try:
        with session_or_new(phien) as ph:
            with ph.trang(viewport=FRAME, device_scale_factor=DPR, user_agent=UA) as page:
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
                  w: W, co_tit: !!hr, co_anh: true};
  // KHONG CO ANH HERO (bai kieu tieu luan: toan hoc, chinh sach) -> "capture man
  // hinh" dung nghia luat 06/09 (Ong Chu nhac lai 12/09: "tin ko co ten rieng
  // thi capture man hinh"): khoi TIT o khung dien thoai, tu mep tren tit xuong.
  if (!hr) return null;
  return {top: hr.top, bottom: hr.bottom, left: 0, right: W, w: W, co_tit: true, co_anh: false};
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


# Ong Chu 13/09/2026, xem 4 slide render thu: *"khoang trong phia tren van qua
# lon va trong trai, nen chung ta se crop hinh ve chu nhat 9:16 nhung van giu
# duoc chu the ro rang, ko bi mat di phan quan trong"*. Anh chup khoi lead da
# len (16:9, 3:2...) dan het be ngang roi dem nen phia tren/duoi de vua 4:5 —
# doi voi anh NGANG, phan dem chiem toi 30-40% chieu cao, trong trai. Cat BOT
# HAI BEN truoc (can giua — anh hero bao chi thuong dat chu the o giua khung),
# CHUA toi ti le dich (0.8, gan day 4:5 chu KHONG toi 9:16=0.5625 thang: cat
# sat vay de mat chu the o hai ria khi khong biet no nam o dau) va GIOI HAN
# CAT TOI DA (35% be ngang) de khong lo cat mat chu the trai/phai. Anh da du
# hep (chan dung, cot bao...) thi khong cat gi ca — nhanh nay chi xu ly anh NGANG.
CROP_RATIO_TRANSLATE = 0.8      # muc tieu sau khi cat (gan 4:5, an toan hon 9:16 thang)
CROP_MAX = 0.35         # tran ti le be ngang duoc phep cat (giu chu the)


THRESHOLD_OTHER_BACKGROUND = 28     # do lech (0..255/kenh) de tinh mot cot la "co chu the"


def _variable_text_card_x(im):
    """Bien THAT (trai, phai) cua chu the theo truc ngang, tinh bang 0..1. None
    neu khong doan duoc (anh khong co nen don sac o bon goc — chup nguoi/canh
    that choan het khung, cu de nguyen khong cat gi them cho an toan).

    Khac ban dau dung TRONG TAM co trong so (da lam dut chu "t" cua logo TSMC,
    su co 13/09/2026): trong tam khong dam bao khung cat CHUA TRON chu the khi
    chu the qua rong — phai do dung BIEN NGOAI CUNG con "khac nen ro" o hai
    dau, roi khong bao gio cat vao trong bien do."""
    from PIL import Image as _Im
    nho = im.convert("RGB").resize((160, max(1, round(160 * im.size[1] / im.size[0]))), _Im.BOX)
    w, h = nho.size
    goc = [nho.getpixel((0, 0)), nho.getpixel((w - 1, 0)),
           nho.getpixel((0, h - 1)), nho.getpixel((w - 1, h - 1))]
    if max(abs(a[k] - b[k]) for a in goc for b in goc for k in range(3)) > 60:
        return None                  # bon goc da khac nhau -> khong phai nen don sac
    nen = tuple(sum(c[k] for c in goc) / 4 for k in range(3))
    px = nho.load()
    co_chu_the = []
    for x in range(w):
        khac = False
        for y in range(h):
            if any(abs(px[x, y][k] - nen[k]) > THRESHOLD_OTHER_BACKGROUND for k in range(3)):
                khac = True
                break
        co_chu_the.append(khac)
    if not any(co_chu_the):
        return None
    trai = next(x for x, v in enumerate(co_chu_the) if v)
    phai = len(co_chu_the) - 1 - next(x for x, v in enumerate(reversed(co_chu_the)) if v)
    return (trai / (w - 1), phai / (w - 1))


def count_background(anh_vao, ra, mau_nen: str, ti_le: float = 0.8, cao_tren: float = 0.15,
           lap_day: float = 0.78):
    """Dat anh chup vao khung `ti_le` (4:5) — CAT BOT HAI BEN neu anh qua ngang
    (quanh tam THI GIAC cua chu the — xem `_tam_chu_the_x` — toi da `CAT_TOI_DA`
    be ngang) roi PHONG LEN cho day khung (contain-fit, co the phong to hon anh
    goc), phan con lai (neu con) to MAU NEN cua chinh trang do. Ra mot tam dung
    mot minh lam slide duoc, khong ghep cap.

    Su co 13/09/2026 (hai lop): (1) cat can giua hinh hoc cat dut chu "t" cua
    logo TSMC vi chu the dat lech trai — sua bang tam thi giac o tren; (2) anh
    sau khi cat nho hon 1080px NHUNG khong duoc phong lai, nam co lai giua
    khung voi vien trang bon phia — nhin nhu hinh vuong chu khong phai 4:5 day
    khung. `cao_tren`: phan dem CON LAI (sau ca cat lan phong) chia cho phia
    tren theo ti le nay. Tra (w, h) cua tam da dem."""
    from PIL import Image as _Im
    im = _Im.open(anh_vao).convert("RGB")
    w, h = im.size
    if w / h > CROP_RATIO_TRANSLATE:
        w_dich = max(int(round(h * CROP_RATIO_TRANSLATE)), int(round(w * (1 - CROP_MAX))))
        bien = _variable_text_card_x(im)
        if bien is not None:
            # KHONG BAO GIO cat vao trong bien chu the that (do bang do-lech-mau-
            # nen, xem _bien_chu_the_x) — chu the rong hon `w_dich` thi NOI RONG
            # cua so cat ra du chua tron no, chap nhan giam bot muc dem thay vi
            # lam dut chu (su co 13/09/2026: logo "tsmc" trai het chieu ngang,
            # cat theo trong tam van dut chu "t").
            trai_px, phai_px = round(bien[0] * (w - 1)), round(bien[1] * (w - 1))
            w_dich = max(w_dich, phai_px - trai_px + 1)
            giua = (trai_px + phai_px) / 2
        else:
            giua = w / 2               # khong doan duoc nen -> can giua, an toan
        if w_dich < w:
            x0 = min(max(0, round(giua - w_dich / 2)), w - w_dich)
            im = im.crop((x0, 0, x0 + w_dich, h))
            w, h = im.size
    W = 1080
    H = int(round(W / ti_le))
    # CONTAIN-FIT vao (W, H*lap_day) — PHONG TO hoac thu nho, khong chi thu nho
    # nhu ban cu (do la nguyen nhan anh da cat gon van nho giua khung thay vi
    # day no ra). KHONG lap day 100% chieu cao (Ong Chu 13/09/2026, sau khi cat
    # gan day khung: chu tieu de de thang len anh, cong bao ve tuong phan cua
    # carousel.py (_lop_neu_can) phai phu mot dai xam day de chu den doc duoc —
    # chinh la "vet nhat" — vi khong con mieng nen PHANG nao ngay tren cho chu
    # se nam de cong do tu bo qua. Chua het khung: `lap_day` (0.78) danh lai
    # mot dai phang o duoi (via `cao_tren` thap, phan lon roi ve duoi) lam nen
    # sach cho tieu de, dai o tren chi con nho.
    PAD_MIN = 40
    H_dich = H * lap_day
    t = min((W - PAD_MIN) / w, (H_dich - PAD_MIN) / h)
    im = im.resize((max(1, round(w * t)), max(1, round(h * t))), _Im.LANCZOS)
    w, h = im.size
    nen = _Im.new("RGB", (W, H), _out_rgb(mau_nen))
    y = int(round((H - h) * cao_tren))
    nen.paste(im, ((W - w) // 2, max(0, min(y, H - h))))
    ra = Path(ra)
    ra.parent.mkdir(parents=True, exist_ok=True)
    nen.save(ra, "PNG")
    return nen.size


def capture_lead_mobile(url: str, ra, phien=None) -> dict | None:
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
        with session_or_new(phien) as ph:
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
                    if r and r["co_anh"]:
                        break
                    page.wait_for_timeout(WAIT_LAZY)
                if not r:
                    print(f"[chup_lead] {url[:70]}: khong thay tit lan anh lead", file=sys.stderr)
                    return None
                # Clip DUNG khung anh hero, khong lay tit/byline. full_page: clip
                # theo toa do TAI LIEU; da cuon ve 0 nen toa do khung nhin trung
                # toa do tai lieu, anh nam duoi mot man van chup du.
                if r["co_anh"]:
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
                page.screenshot(path=str(ra), full_page=True, clip=clip)
    except Exception as e:                                   # noqa: BLE001
        print(f"[chup_lead] {url[:70]}: {type(e).__name__}: {e!r}", file=sys.stderr)
        return None
    if not (ra.exists() and ra.stat().st_size > 0):
        return None
    # `tit_trang` de nguoi goi doi chieu "co cung tin khong" (LOW-33) — trang
    # trong `trang` co the la bao khac khop NHAM, khong duoc mac dinh la bai goc.
    return {"anh": url, "trang": url, "tu": "chup_nguon", "chup_nguon": True, "tit_trang": tit_trang,
            "kieu": "hero" if r["co_anh"] else "tit", "mau_nen": mau_nen,
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
        if not capture_lead_mobile(a.url, a.out):
            return 1
    elif not capture(a.url, a.out):
        return 1
    print(a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
