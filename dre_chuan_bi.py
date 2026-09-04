#!/usr/bin/env python3
"""dre_chuan_bi.py — CHUAN BI cho Dre (carousel): tat dinh, chay MOT lan.

Vi sao co tep nay (do that 04/09/2026, 11 task carousel o ca hai brand): moi
task Dre ton 51-60 tool call va 130k-260k token input moi, trong do phan lon la
viec CO HOC — `curl` tai tung anh (27-38 lan/7 task), `ls`/`head`/`grep`/`echo`
gan 70 luot, `write_file` roi `read_file` lai chinh spec, `vision_analyze` mo
tung anh, `crop_ti_le` lap 14 lan. Task GPT-6 Astra bi block sau 47 tool call
vi cai nhau voi cong chan thay vi doc luat.

Nguyen tac Ong Chu: CODE TOI DA, LLM TOI THIEU. Vai chi con hai viec code khong
lam duoc: CHIA TIN THANH SLIDE va VIET COPY. Moi thu con lai nam o day:

  1. Nguon: doc bo nguon Finn da research (`state/<brand>/nguon_<id>.json`),
     giai ma link Google News neu link goc la duong chuyen huong (tin cua Vera
     luon nhu vay — truoc day anh_bai/tu_lieu doc ra rong, Dre phai tu
     web_search 11 lan).
  2. Anh: chay anh_bai (tinh) + mo trang bang browser that (dong — screenshot
     UI, bang benchmark, figure) — dung cai ma SOUL bat vai "mo browser" bang
     tay. Tai ve, loai trung (md5), loai anh be.
  3. Do va phan loai tung anh bang `luat_anh`: chart hay anh chup, ti le, mat
     nguoi, day sang, do phan giai. Cat san ve 1:1/4:5 qua crop_ti_le (co dau
     vet), tinh san cap anh ngang ghep duoc (cung tone). Anh ngang co chu thi
     KHONG cat — de nguyen cho "chart": true.
  4. Tu lieu: goi tu_lieu.gom -> cau co so lieu, doan dau bai goc.
  5. In MOT ban chuan bi (brief) + khung spec: vai doc mot lan, viet mot tep
     JSON, chay dre_nop.py. Bang anh thu nho `bang_anh.png` gom moi anh vao
     MOT tam — muon nhin thi mo mot lan, khong mo tung anh.

Idempotent: ket qua ghi o `state/<brand>/dre/<id>/xong.json`; chay lai chi in
brief. `--lam-moi` de lam lai tu dau. approve_service khoi chay tep nay o NEN
ngay khi Ong Chu chon tin, nen toi luc Dre nhan task thi moi thu da san.

Dung:
    venv/bin/python dre_chuan_bi.py <draft_id>            # in brief (chay neu chua co)
    venv/bin/python dre_chuan_bi.py <draft_id> --im       # chay nen, khong in
    venv/bin/python dre_chuan_bi.py <draft_id> --lam-moi  # bo cache, lam lai
"""
import argparse
import hashlib
import io
import json
import os
import re
import sys
import time
from pathlib import Path

import httpx
from PIL import Image, ImageDraw, ImageStat

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

DRAFTS = ROOT / "drafts"
TEN_CT = {"dcgr": "dcgr", "donniechublog": "blog"}      # brand -> CT_BRAND

# Nguong (cung goc voi luat_anh; o day chi la phan CHON anh de tai)
CANH_NGAN_BO = 500          # duoi nguong nay khong tai (phong len 1080 la vo)
TOI_DA_ANH = 8              # anh giu lai sau khi loc — du cho 10 slide ke ca ghep
TOI_DA_TAI = 14             # ung vien thu tai (co cai hong/trung)
TAI_TOI_DA_BYTE = 14_000_000
GNEWS = "news.google.com/rss/articles"
UA = "Mozilla/5.0 (compatible; donniechu-dre/1.0)"
HDR = {"User-Agent": UA, "Accept": "image/*,*/*;q=0.8"}


# ---- tien ich -------------------------------------------------------------
def _brand_cua(meta: dict) -> str:
    return meta.get("brand") or "donniechublog"


def _mien(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url or "")
    return (m.group(1) if m else "").replace("www.", "")


def _doc_json(p: Path, mac_dinh=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        return mac_dinh


def _ghi_json(p: Path, d) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")


def _tom_tat_tu_img_json(draft_id: str) -> dict:
    """Tom tat + source_note nam trong body task (img.json). Doc lai tu do thay
    vi bat vai chep — mot nguon, khong lech."""
    d = _doc_json(DRAFTS / f"{draft_id}.img.json", {}) or {}
    body = d.get("body", "")
    ra = {}
    for khoa, nhan in (("summary", "Tom tat"), ("source_note", "Nguon")):
        m = re.search(rf"^{nhan}: (.*)$", body, re.M)
        ra[khoa] = (m.group(1).strip() if m else "")
    ra["remakes"] = int(d.get("remakes", 0) or 0)
    return ra


# ---- 1. nguon ---------------------------------------------------------------
def nap_nguon(draft_id: str, meta: dict, state: Path) -> tuple:
    """Tra ve (nguon_dict, nguon_path, link_that). Giai ma link Google News neu
    can va ghi nguoc vao nguon json + meta de moi vai sau cung dung link that."""
    import nguon_bai
    p = state / f"nguon_{draft_id}.json"
    link = meta.get("source_url", "")
    nguon = _doc_json(p) or {"tieu_de": meta.get("title", ""), "link_goc": link,
                             "trang": [{"url": link, "loai": "gốc",
                                        "tieu_de": meta.get("title", "")}]}
    link_goc = nguon.get("link_goc") or link
    if GNEWS in link_goc:
        that = nguon_bai.giai_ma_gnews(link_goc)
        if that:
            print(f"[nguon] giai ma Google News -> {that[:90]}", file=sys.stderr)
            nguon["link_gnews"] = link_goc
            nguon["link_goc"] = that
            for t in nguon.get("trang", []):
                if t.get("url") == link_goc:
                    t["url"] = that
            _ghi_json(p, nguon)
            link_goc = that
            if meta.get("source_url") != that:
                meta["source_url"] = that
                _ghi_json(DRAFTS / f"{draft_id}.meta.json", meta)
    # Tieu de TIENG ANH cua bai that: tin cua Vera/Nova mang tieu de tieng Viet,
    # tim Google News/RSS bang tieu de do ra rong. Lay <title>/og:title cua trang
    # goc mot lan, ghi vao nguon json de anh_bai/tu_lieu tim bao khac bang no.
    return nguon, p, link_goc


def _tieu_de_trang(url: str) -> str:
    try:
        r = httpx.get(url, headers={"User-Agent": UA}, timeout=20, follow_redirects=True)
        html = r.text[:200_000]
        m = (re.search(r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)', html, re.I)
             or re.search(r'content=["\']([^"\']+)["\'][^>]*property=["\']og:title', html, re.I)
             or re.search(r"<title[^>]*>([^<]{5,200})</title>", html, re.I))
        if not m:
            return ""
        import html as _h
        t = _h.unescape(m.group(1)).strip()
        return re.sub(r"\s+[|\-–—]\s+[^|\-–—]{2,40}$", "", t)   # bo " | Ten bao"
    except Exception:                                        # noqa: BLE001
        return ""


# ---- 2. anh -----------------------------------------------------------------
def _tai_bytes(url: str) -> bytes | None:
    try:
        with httpx.stream("GET", url, headers=HDR, timeout=40,
                          follow_redirects=True) as r:
            if r.status_code != 200:
                return None
            buf = b""
            for chunk in r.iter_bytes(65536):
                buf += chunk
                if len(buf) > TAI_TOI_DA_BYTE:
                    return None
            return buf
    except Exception:                                        # noqa: BLE001
        return None


def ung_vien_tinh(title: str, link: str, nguon_path: Path, title_en: str = "") -> list:
    """anh_bai.tim tren bo nguon cua Finn; it qua thi tim rong them (bao khac,
    bang tieu de tieng Anh cua bai that)."""
    import anh_bai
    ds = anh_bai.tim(title, link, sau_rong=True, tu_nguon=str(nguon_path))
    if len(ds) < 4:
        them = anh_bai.tim(title_en or title, link, sau_rong=True, tu_nguon=None)
        co = {c["anh"] for c in ds}
        ds += [c for c in them if c["anh"] not in co]
    return ds


def browser_pass(trang: list, wd: Path, tim_them: bool, gio_han=110) -> dict:
    """MOT phien chromium lam het phan "mo browser that" ma SOUL tung bat vai lam tay:

      - trang goc: og:title (tieu de tieng Anh), CHU bai (innerText cua
        article/main — trang JS nhu ifm.ai fetch tinh doc ra rong), <img> lon
        (naturalWidth) ma fetch tinh bo sot, va chup figure/table/canvas/svg lon
        full be ngang (bang benchmark, chart);
      - bo nguon mong (chi co link goc): tim bao khac tren trang tim kiem Google
        News, giai ma tung link /read/ bang cach di theo chuyen huong;
      - 1-2 trang bao khac: lay <img> lon + figure.

    Khong co playwright / trang hong thi tra ve phan da lay duoc, khong loi."""
    ra = {"tieu_de_en": "", "chu": "", "cands": [], "trang_them": []}
    try:
        from playwright.sync_api import sync_playwright
    except Exception:                                        # noqa: BLE001
        return ra
    import urllib.parse as up
    import luat_anh
    JS_TITLE = """() => ((document.querySelector('meta[property="og:title"]')||{}).content
                    || document.title || '')"""
    JS_TEXT = """() => ((document.querySelector('article') || document.querySelector('main')
                    || document.body).innerText || '').slice(0, 20000)"""
    JS_IMG = """() => Array.from(document.images)
        .filter(i => i.naturalWidth >= 600 && i.naturalHeight >= 350)
        .map(i => ({src: i.currentSrc || i.src, alt: i.alt || '',
                    w: i.naturalWidth, h: i.naturalHeight})).slice(0, 12)"""
    JS_FIG = """() => { const ra = []; let k = 0;
        for (const s of ['table', 'canvas', 'svg', 'figure']) {
          for (const el of document.querySelectorAll(s)) {
            const r = el.getBoundingClientRect();
            const w = Math.max(el.scrollWidth || 0, r.width), h = Math.max(el.scrollHeight || 0, r.height);
            if (w < 600 || h < 300 || w > 4000 || h > 6000) continue;
            el.setAttribute('data-dre', 'f' + k);
            ra.push({sel: '[data-dre="f' + k + '"]', w, h, tag: s}); k++;
            if (ra.length >= 4) return ra;
          } }
        return ra; }"""
    JS_GNEWS = """() => Array.from(document.querySelectorAll('a[href*="/read/"], a[href*="/articles/"]'))
                     .map(a => a.href).slice(0, 10)"""
    t0 = time.time()
    goc = next((t.get("url") for t in trang if t.get("loai") == "gốc" and t.get("url")), None) \
        or (trang[0].get("url") if trang else "")
    mien_goc = _mien(goc)

    def het_gio():
        return time.time() - t0 > gio_han

    def lay_anh(page, url, so, chup_fig=True):
        for im in page.evaluate(JS_IMG) or []:
            ra["cands"].append({"anh": im["src"], "alt": im["alt"], "og": False, "tu": "browser",
                                "trang": url, "rong": im["w"], "cao": im["h"], "diem": 45})
        if not chup_fig:
            return
        for f in page.evaluate(JS_FIG) or []:
            out = wd / "goc" / f"chup_{so}_{f['sel'][-3:-2]}.png"
            out.parent.mkdir(parents=True, exist_ok=True)
            el = page.query_selector(f["sel"])
            if not el:
                continue
            try:
                el.scroll_into_view_if_needed()
                page.wait_for_timeout(300)
                el.screenshot(path=str(out))
            except Exception:                                # noqa: BLE001
                continue
            luat_anh.dong_dau_tep(out, "chup_chart")
            ra["cands"].append({"anh": str(out), "tep": str(out), "alt": f"{f['tag']} chup tu trang",
                                "og": False, "tu": "chup", "the": f["tag"], "trang": url,
                                "rong": int(f["w"] * 2), "cao": int(f["h"] * 2), "diem": 50})

    def mo(page, url, cho_yen=12000):
        page.goto(url, wait_until="domcontentloaded", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=cho_yen)
        except Exception:                                    # noqa: BLE001
            pass
        page.wait_for_timeout(700)

    try:
        with sync_playwright() as p:
            b = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            try:
                ctx = b.new_context(viewport={"width": 1600, "height": 1200}, device_scale_factor=2,
                                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                                               "AppleWebKit/537.36 (KHTML, like Gecko) "
                                               "Chrome/124.0 Safari/537.36")
                page = ctx.new_page()
                # 1) trang goc
                if goc and goc.startswith("http") and GNEWS not in goc:
                    try:
                        mo(page, goc)
                        ra["tieu_de_en"] = re.sub(r"\s+[|\-–—]\s+[^|\-–—]{2,40}$", "",
                                                  (page.evaluate(JS_TITLE) or "").strip())
                        ra["chu"] = page.evaluate(JS_TEXT) or ""
                        lay_anh(page, goc, 0)
                    except Exception as e:                   # noqa: BLE001
                        print(f"[browser] goc {goc[:60]}: {type(e).__name__}", file=sys.stderr)
                # 2) tim bao khac (bo nguon mong)
                if tim_them and ra["tieu_de_en"] and not het_gio():
                    try:
                        q = re.sub(r"^\[[^\]]{1,20}\]\s*", "", ra["tieu_de_en"])[:120]
                        mo(page, "https://news.google.com/search?q=" + up.quote(q)
                           + "&hl=en-US&gl=US&ceid=US:en", cho_yen=6000)
                        links, thay = [], set()
                        for h in page.evaluate(JS_GNEWS) or []:
                            k = h.split("?")[0]
                            if k not in thay:
                                thay.add(k)
                                links.append(h)
                        for h in links[:5]:
                            if het_gio() or len(ra["trang_them"]) >= 3:
                                break
                            try:
                                page.goto(h, wait_until="domcontentloaded", timeout=25000)
                                t1 = time.time()
                                while "news.google.com" in page.url and time.time() - t1 < 12:
                                    page.wait_for_timeout(500)
                                u = page.url
                                if "news.google.com" in u or _mien(u) == mien_goc \
                                        or any(_mien(u) == _mien(x["url"]) for x in ra["trang_them"]):
                                    continue
                                ra["trang_them"].append({"url": u, "loai": "báo",
                                                         "tieu_de": (page.title() or "")[:160],
                                                         "toa_soan": "https://" + _mien(u)})
                            except Exception:                # noqa: BLE001
                                continue
                    except Exception as e:                   # noqa: BLE001
                        print(f"[browser] gnews search: {type(e).__name__}", file=sys.stderr)
                # 3) bao khac (co san trong nguon + vua tim): lay anh, toi da 2 trang
                khac = [t for t in trang if t.get("url") and t.get("url") != goc and GNEWS not in t["url"]]
                khac += ra["trang_them"]
                for i, t in enumerate(khac[:2], start=1):
                    if het_gio():
                        break
                    try:
                        mo(page, t["url"], cho_yen=8000)
                        lay_anh(page, t["url"], i)
                    except Exception as e:                   # noqa: BLE001
                        print(f"[browser] {t['url'][:60]}: {type(e).__name__}", file=sys.stderr)
            finally:
                b.close()
    except Exception as e:                                   # noqa: BLE001
        print(f"[browser] bo qua: {type(e).__name__}: {e}", file=sys.stderr)
    return ra


def _dhash(im: Image.Image) -> int:
    g = im.convert("L").resize((9, 8), Image.LANCZOS)
    px = list(g.getdata())
    return sum(((px[r * 9 + c] > px[r * 9 + c + 1]) << (r * 8 + c))
               for r in range(8) for c in range(8))


def _gan_giong(h1: int, h2: int, nguong=6) -> bool:
    return bin(h1 ^ h2).count("1") <= nguong


def anh_commons(tu_khoa: str, so: int = 4) -> list:
    """Anh that tren Wikimedia Commons (tru so, san pham, su kien) cho tin mong
    anh — LUAT_ANH muc 1.2 ke Commons la nguon hop le. Chi goi khi bai + bao khac
    khong du 5 anh. Loai SVG/logo (mime + _do_hoa o buoc tai)."""
    try:
        r = httpx.get("https://commons.wikimedia.org/w/api.php", params={
            "action": "query", "generator": "search", "gsrsearch": f"{tu_khoa} filetype:bitmap",
            "gsrnamespace": 6, "gsrlimit": 14, "prop": "imageinfo",
            "iiprop": "url|size|mime", "iiurlwidth": 1800, "format": "json"},
            headers={"User-Agent": UA}, timeout=20)
        pages = r.json().get("query", {}).get("pages", {})
    except Exception as e:                                   # noqa: BLE001
        print(f"[commons] hong: {type(e).__name__}", file=sys.stderr)
        return []
    ra = []
    for pg in pages.values():
        ii = (pg.get("imageinfo") or [{}])[0]
        w, h = ii.get("width", 0), ii.get("height", 0)
        if min(w, h) < 600 or ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        ten = (pg.get("title") or "").replace("File:", "")
        if tu_khoa.lower() not in ten.lower():       # tim mo cua Commons hay lac de
            continue
        ra.append({"anh": ii.get("thumburl") or ii.get("url"), "alt": "Commons: " + ten, "og": False,
                   "tu": "commons", "trang": "https://commons.wikimedia.org/wiki/File:" + ten.replace(" ", "_"),
                   "rong": w, "cao": h, "diem": 30})
    ra.sort(key=lambda c: -(c["rong"] * c["cao"]))
    return ra[:so]


def _ten_rieng_dau(tieu_de: str) -> str:
    """Ten rieng dau tieu de (hang/san pham) lam tu khoa Commons. Bo the "[News]"
    dau tieu de truoc — khong thi "News" thanh tu khoa, ra anh bao 1873."""
    import nguon_bai
    t = re.sub(r"^\[[^\]]{1,20}\]\s*", "", tieu_de or "")
    for w in re.sub(r"[\$;:,\"\'()\[\]|]", " ", t).split():
        w = w.replace("’s", "").replace("'s", "")
        if w[:1].isupper() and w.isalpha() and len(w) >= 4 and w.lower() not in nguon_bai.TU_RONG_TRUY_VAN:
            return w
    return ""


def tai_va_loc(cands: list, wd: Path, tin_model: bool) -> list:
    """Tai ung vien theo thu tu diem, loai trung (md5) va anh be, luu PNG co dau
    xuat xu. Tra ve danh sach anh da tai [{ma, goc, ...}]."""
    import anh_bai
    import luat_anh
    goc_dir = wd / "goc"
    goc_dir.mkdir(parents=True, exist_ok=True)
    da_tai = []                       # [(dhash, im, c, data_len)] — de khu trung gan giong
    for c in cands[:TOI_DA_TAI + 6]:
        if len(da_tai) >= TOI_DA_ANH + 4:
            break
        try:
            if c.get("tep"):
                data = Path(c["tep"]).read_bytes()
            else:
                data = _tai_bytes(c["anh"])
            if not data:
                continue
            im = Image.open(io.BytesIO(data))
            im.load()
            im = im.convert("RGB")
            w, hh = im.size
            if min(w, hh) < CANH_NGAN_BO:
                continue
            if (w, hh) in anh_bai.CO_AI_SINH:
                continue
            ly_do_do_hoa = anh_bai._do_hoa(im)
            la_ct, _ = luat_anh.la_chart(im)
            if ly_do_do_hoa and not la_ct and not _chart_theo_hinh(im):
                continue                                  # logo/wordmark
            h = _dhash(im)
            # Trung gan giong (cung anh o co khac, anh <img> vs figure chup): giu ban LON hon.
            trung = next((k for k, (h2, im2, _, _) in enumerate(da_tai) if _gan_giong(h, h2)), None)
            if trung is not None:
                if w * hh > da_tai[trung][1].width * da_tai[trung][1].height:
                    da_tai[trung] = (h, im, c, len(data))
                continue
            da_tai.append((h, im, c, len(data)))
        except Exception as e:                               # noqa: BLE001
            print(f"[tai] {str(c.get('anh'))[:60]}: {type(e).__name__}", file=sys.stderr)
    ra = []
    for n, (h, im, c, _) in enumerate(da_tai[:TOI_DA_ANH], start=1):
        ma = f"A{n}"
        out = goc_dir / f"{ma}.png"
        im.save(out, "PNG", pnginfo=luat_anh.dong_dau(
            "chup_chart" if c.get("tu") == "chup" else "dre_chuan_bi"))
        hint = bool(anh_bai.QUY.search(c.get("anh", "") or "") or anh_bai.QUY.search(c.get("alt", "") or "")
                    or anh_bai.QUY_MODEL.search(c.get("alt", "") or "")
                    or c.get("the") in ("table", "canvas", "svg"))
        ra.append({"ma": ma, "goc": str(out), "url": c.get("anh", ""),
                   "alt": (c.get("alt") or "")[:120], "tu": c.get("tu", ""),
                   "trang": c.get("trang", ""), "mien": _mien(c.get("trang") or c.get("anh")),
                   "diem": c.get("diem", 0), "ly_do": c.get("ly_do", ""), "hint_chart": hint})
    return ra


def _chart_theo_hinh(im: Image.Image) -> bool:
    """Bo sung cho luat_anh.la_chart (bo sot chart co duong mau khu rang cua, xem
    chu thich ben do). Do 04/09/2026 tren 11 anh that: chart/bang/infographic co
    NEN GAN TRANG 0.64-0.82 va MAT DO CANH 0.09-0.14; anh chup 0.00-0.06 /
    0.04-0.05; anh chup co vien trang 0.36 / 0.05. Can CA HAI: nen trang nhieu
    (mot tam san pham tren nen trang co canh thua) VA canh day (chu, truc, cot)."""
    from PIL import ImageFilter
    w, h = im.size
    v = im.resize((480, max(1, round(h * 480 / w))))
    L = v.convert("L")
    n = v.width * v.height
    trang = sum(L.histogram()[236:]) / n
    canh = sum(L.filter(ImageFilter.FIND_EDGES).histogram()[60:]) / n
    return trang >= 0.45 and canh >= 0.08


# ---- 3. do, phan loai, cat san --------------------------------------------
def _luu_crop(img: Image.Image, out: Path, ti_le_ten: str, cx=0.5, cy=0.5,
              cat_ngang=False) -> Image.Image:
    """Cat qua crop_ti_le.cat va DONG DAU y het CLI crop_ti_le.py — cong
    `kiem_xuat_xu`/`kiem_crop_ngang` doc dau nay."""
    import crop_ti_le
    from PIL.PngImagePlugin import PngInfo
    ra = crop_ti_le.cat(img, crop_ti_le.TI_LE[ti_le_ten], cx, cy, cat_ngang=cat_ngang)
    meta = PngInfo()
    meta.add_text("crop_ti_le", f"goc={img.size[0]}x{img.size[1]};ti_le={ti_le_ten};"
                                f"cx={cx};cy={cy};cat_ngang={int(cat_ngang)}")
    out.parent.mkdir(parents=True, exist_ok=True)
    ra.save(out, "PNG", pnginfo=meta)
    return ra


def phan_loai(a: dict, wd: Path) -> dict:
    """Do mot anh bang luat_anh, quyet dinh no DUNG DUOC O DAU, cat san neu can."""
    import luat_anh
    img = Image.open(a["goc"]).convert("RGB")
    w, h = img.size
    r = w / h
    la_ct, mo_ta = luat_anh.la_chart(img)
    if not la_ct and (a.get("hint_chart") or _chart_theo_hinh(img)):
        la_ct, mo_ta = True, mo_ta + "; nen trang + canh day / alt-tag chart"
    mat = luat_anh.dem_mat(a["goc"]) or 0
    day = ImageStat.Stat(img.convert("L").crop((0, int(h * .75), w, h))).mean[0]
    goc_trai = ImageStat.Stat(img.convert("L").crop((0, int(h * .55), int(w * .6), h))).mean[0]
    a.update({"w": w, "h": h, "ti_le": round(r, 2), "loai": "chart" if la_ct else "anh",
              "do_chart": mo_ta, "mat": mat, "day_sang": round(day),
              "goc_trai_sang": round(goc_trai), "canh_ngan": min(w, h),
              "ngang": r >= luat_anh.NGANG_RO, "san": None, "dung": [], "ghi_chu": []})
    san = wd / "san" / f"{a['ma']}.png"
    if la_ct:
        if r < luat_anh.TI_LE_45 - luat_anh.DUNG_SAI_TI_LE:
            _luu_crop(img, san, "4:5", cy=0.35)           # chart cao: cat bot day
            a["san"] = str(san)
            a["ghi_chu"].append("chart cao, đã cắt bớt phần dưới về 4:5")
        else:
            a["san"] = a["goc"]                           # chart giu NGUYEN
        a["dung"] = ["thân (chart, dán full bề ngang nguyên vẹn)"]
        if a["ngang"]:
            a["dung"].append("ghép dọc với một ảnh ngang cùng tone")
        a["ghi_chu"].append("KHÔNG làm bìa")
    else:
        if a["ngang"]:
            a["dung"] = ["ghép dọc với một ảnh ngang cùng tone"]
            if h >= 700:
                a["dung"].append("cat_ngang: true NẾU là ảnh người/sản phẩm KHÔNG có chữ")
            else:
                # Banner thap (vd 1900x524): cat doc 4:5 chi con ~420px roi phong
                # len 1080 — mem nhoe (do thu 04/09). Chi con duong ghep.
                a["ghi_chu"].append("quá thấp để cắt dọc, chỉ ghép")
        else:
            ten = "1:1" if r > 0.9 else "4:5"
            _luu_crop(img, san, ten, cy=0.4 if r < 0.7 else 0.5)
            a["san"] = str(san)
            a["dung"] = ["thân"]
            if not mat and goc_trai < 150:
                a["dung"].insert(0, "bìa")
    if a.get("commons"):
        a["ghi_chu"].append("ảnh CHUNG của hãng từ Wikimedia Commons (trụ sở/sản phẩm), không phải ảnh của tin — hợp bìa/slide bối cảnh")
    if mat:
        a["ghi_chu"].append(f"CÓ {mat} MẶT NGƯỜI → chỉ dùng khi khai \"nhan_vat\": \"<tên người trong bài>\"")
    if a["canh_ngan"] < luat_anh.CANH_NGAN_MIN:
        a["ghi_chu"].append(f"cạnh ngắn {a['canh_ngan']}px, phóng lên hơi mềm")
    if day > luat_anh.DAY_SANG_MAX and not la_ct:
        a["ghi_chu"].append("đáy sáng, chữ trắng hơi nhạt")
    return a


def cap_ghep(anh: list) -> list:
    """Cac cap anh NGANG ghep doc duoc: cung tone (luat_anh.lech_tone) va ti le
    sau ghep nam trong dai carousel chap nhan."""
    import luat_anh
    ngang = [a for a in anh if a["ti_le"] >= 1.3]
    ims = {a["ma"]: Image.open(a["goc"]).convert("RGB") for a in ngang}
    ra = []
    for i in range(len(ngang)):
        for j in range(i + 1, len(ngang)):
            x, y = ngang[i], ngang[j]
            rc = 1 / (1 / x["ti_le"] + 1 / y["ti_le"])
            if not (luat_anh.TI_LE_45 - luat_anh.DUNG_SAI_TI_LE <= rc
                    <= luat_anh.TI_LE_11 + luat_anh.DUNG_SAI_TI_LE):
                continue
            if luat_anh.lech_tone([ims[x["ma"]], ims[y["ma"]]]):
                continue
            ra.append([x["ma"], y["ma"]])
    return ra


def bang_anh(anh: list, out: Path) -> None:
    """Mot tam thu nho gom moi anh, nhan MA + kich thuoc + loai: vai muon nhin
    thi mo MOT tam nay, khong mo tung anh."""
    if not anh:
        return
    from PIL import ImageFont
    try:
        f = ImageFont.truetype(str(ROOT / "assets/fonts/Inter.ttf"), 22)
    except Exception:                                        # noqa: BLE001
        f = ImageFont.load_default()
    W, cot = 360, 3
    hang = (len(anh) + cot - 1) // cot
    canvas = Image.new("RGB", (W * cot, 300 * hang), (18, 18, 18))
    d = ImageDraw.Draw(canvas)
    for k, a in enumerate(anh):
        im = Image.open(a["goc"]).convert("RGB")
        im.thumbnail((W - 16, 240))
        x, y = (k % cot) * W + 8, (k // cot) * 300 + 8
        canvas.paste(im, (x, y))
        nhan = f"{a['ma']}  {a['w']}x{a['h']}  {a['loai'].upper()}" + \
               ("  MẶT" if a["mat"] else "") + ("  NGANG" if a["ngang"] else "")
        d.text((x, y + 250), nhan, font=f, fill=(0, 204, 224))
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "PNG")


# ---- 4. tu lieu ------------------------------------------------------------
def gom_tu_lieu(title: str, link: str, nguon_path: Path, wd: Path) -> dict:
    import tu_lieu
    p = wd / "tu_lieu.md"
    try:
        tl = tu_lieu.gom(title, link, tu_nguon=str(nguon_path))
        p.write_text(tu_lieu.dung_trang(tl), encoding="utf-8")
        doan = []
        for n in tl.get("nguon", []):
            if n.get("nhan") == "bài gốc":
                doan = n.get("doan", [])
                break
        if not doan and tl.get("nguon"):
            doan = tl["nguon"][0].get("doan", [])
        return {"cau_co_so": tl.get("cau_co_so", [])[:25],
                "doan_dau": " ".join(doan)[:1500],
                "so_nguon": len(tl.get("nguon", []))}
    except Exception as e:                                   # noqa: BLE001
        print(f"[tu_lieu] hong: {type(e).__name__}: {e}", file=sys.stderr)
        return {"cau_co_so": [], "doan_dau": "", "so_nguon": 0}


# ---- 5. brief ---------------------------------------------------------------
def viet_brief(m: dict, da_dung: dict | None) -> str:
    import carousel
    L = []
    L.append(f"# DRE — ĐÃ CHUẨN BỊ XONG: {m['title']}")
    L.append(f"Brand: {m['brand']} | draft: {m['draft_id']} | "
             f"slide tối thiểu: {m['toi_thieu']}"
             + (" (FLAGSHIP: tin model của hãng frontier)" if m["flagship"] else "")
             + " | tối đa 10 | quote ≥ 2")
    L.append(f"Link gốc: {m['link']}" + (f" | via: {m['via']}" if m.get("via") else ""))
    if m.get("tieu_de_en"):
        L.append(f"Tiêu đề bài gốc: {m['tieu_de_en']}")
    if da_dung:
        L.append("")
        L.append(f"⚠️ LÀM LẠI — lần trước đã gửi lúc {da_dung.get('luc', '?')}: bìa {da_dung.get('bia')}, "
                 f"ảnh dùng {', '.join(da_dung.get('anh', []))}, hook: “{da_dung.get('hook', '')}”. "
                 "Lần này BÌA và HOOK phải khác, đổi ít nhất nửa số ảnh, đổi cách chia slide.")
    L.append("")
    L.append("## Tư liệu")
    if m.get("summary"):
        L.append(f"Tóm tắt (Finn): {m['summary']}")
    if m.get("source_note"):
        L.append(f"Nguồn (Finn): {m['source_note']}")
    tl = m.get("tu_lieu", {})
    if tl.get("cau_co_so"):
        L.append("Câu có số liệu (bóc từ bài, dùng làm text/quote):")
        for i, c in enumerate(tl["cau_co_so"], 1):
            L.append(f"  {i}. {c}")
    if tl.get("doan_dau"):
        L.append(f"Đoạn đầu bài gốc: {tl['doan_dau']}")
    if not tl.get("cau_co_so") and not tl.get("doan_dau"):
        L.append("(Không bóc được chữ từ nguồn — viết từ tóm tắt, KHÔNG bịa số.)")
    L.append("")
    L.append("## Ảnh đã tải & xử lý xong — chỉ dùng MÃ ẢNH, không tải/crop/mở gì thêm")
    if not m["anh"]:
        L.append("KHÔNG CÓ ảnh thật nào dùng được. Không dựng hình giả. Kết thúc task bằng "
                 "một câu: \"Không tìm được ảnh thật cho tin này\" kèm link đã thử.")
    for a in m["anh"]:
        dong = (f"- {a['ma']}: {a['w']}x{a['h']} ({a['ti_le']}) {a['loai'].upper()}"
                f"{' NGANG' if a['ngang'] else ''} | dùng: {'; '.join(a['dung'])}"
                f" | nguồn: {a['mien'] or a['tu']}")
        if a.get("alt"):
            dong += f" | alt: {a['alt'][:70]}"
        if a["ghi_chu"]:
            dong += " | " + "; ".join(a["ghi_chu"])
        L.append(dong)
    if m.get("goi_y_bia"):
        L.append(f"Gợi ý bìa (không chart, không mặt, góc dưới-trái tối): {', '.join(m['goi_y_bia'])}")
    if m.get("cap_ghep"):
        L.append("Cặp ảnh ngang ghép dọc được (cùng tone): " +
                 ", ".join("+".join(c) for c in m["cap_ghep"]))
    L.append(f"Nhìn tất cả ảnh trong MỘT tấm: {m['workdir']}/bang_anh.png (mở tối đa một lần, khi thật cần).")
    L.append("")
    L.append(f"## Viết spec vào: {m['workdir']}/spec.json")
    khung = {
        "tam_co": "flagship" if m["flagship"] else "thuong",
        "cover": {"anh": (m.get("goi_y_bia") or ["A?"])[0], "hook": "<một câu giật, ≤ 90 ký tự, có dấu>",
                  "category": "<" + " | ".join(carousel.CATEGORY_GOI_Y) + " | EARNINGS | M&A>",
                  "label": "<TÊN MODEL / HÃNG, VIẾT HOA>"},
        "slides": [
            {"anh": "A?", "text": "<đoạn 1.\\n\\nđoạn 2 — tổng ≤ 240 ký tự>"},
            {"anh": "A?", "quote": "<câu đắt nhất, DỊCH tiếng Việt, ≤ 150 ký tự>", "attrib": "<Ai nói / Đọc bài “…” - nguồn>"},
            {"ghep": ["A?", "A?"], "text": "<hai ảnh ngang cùng tone xếp dọc>"},
            {"anh": "A?", "nhan_vat": "<tên người trong bài>", "quote": "…", "attrib": "…"},
            {"anh": "A?", "cat_ngang": True, "text": "<chỉ cho ảnh NGANG là người/sản phẩm không chữ>"},
        ],
    }
    L.append(json.dumps(khung, ensure_ascii=False, indent=1))
    L.append("Luật điền: mỗi slide MỘT ảnh, MỘT ý; `text` HOẶC `quote`+`attrib`; mỗi mã ảnh dùng đúng "
             "một lần; chart chỉ ở slide thân (script tự dán full bề ngang); ảnh NGANG phải `ghep` "
             "hoặc `cat_ngang`; ảnh có mặt phải có `nhan_vat`. Tiếng Việt có dấu, không em-dash, "
             "câu quote phải DỊCH. Bỏ các slide mẫu không dùng — khung trên chỉ minh hoạ cú pháp.")
    L.append("Khung kể: bìa HOOK (nghịch lý/con số) → chuyện gì vừa xảy ra → con số gây sốc → "
             "ý nghĩa thật → đối thủ/diễn biến → cái cần theo dõi (không chốt cụt).")
    L.append("")
    L.append("## Rồi chạy đúng MỘT lệnh:")
    L.append(f"cd {ROOT} && venv/bin/python dre_nop.py {m['draft_id']}")
    L.append("Script tự cắt/ghép ảnh theo spec, chạy cổng chặn, dựng slide, gửi album lên topic kèm nút "
             "duyệt, ghi bàn giao cho Miles. Báo [LOI] thì sửa đúng chỗ đó trong spec.json rồi chạy "
             "lại đúng lệnh này. KHÔNG curl, KHÔNG ls, KHÔNG mở từng ảnh, KHÔNG chạy carousel.py hay "
             "gui_telegram.py tay.")
    return "\n".join(L)


# ---- main -------------------------------------------------------------------
def chuan_bi(draft_id: str, meta: dict, state: Path, wd: Path, khong_browser=False) -> dict:
    import carousel
    title = meta.get("title", draft_id)
    nguon, nguon_path, link = nap_nguon(draft_id, meta, state)
    trang = nguon.get("trang", [])
    tom = _tom_tat_tu_img_json(draft_id)
    import anh_bai
    tin_model = bool(anh_bai.LA_TIN_MODEL.search(title + " " + nguon.get("tieu_de_en", "")))

    # Tieu de TIENG ANH cua bai that (tin Vera/Nova mang tieu de tieng Viet):
    # mot fetch httpx; khong ra thi browser lay og:title sau.
    if not nguon.get("tieu_de_en"):
        nguon["tieu_de_en"] = _tieu_de_trang(link)
        _ghi_json(nguon_path, nguon)
    # Bo nguon mong -> Bing News RSS bang tieu de tieng Anh (link chuyen huong HTTP
    # thuong, khong can browser). Lam TRUOC khi mo browser de browser ghe luon
    # cac trang bao nay lay anh. Ghi vao nguon json de tu_lieu (Miles) cung dung.
    if len(trang) < 3 and nguon.get("tieu_de_en"):
        import nguon_bai
        co = {t.get("url") for t in trang}
        mien_co = {_mien(t.get("url", "")) for t in trang}
        them = nguon_bai.bao_khac_bing(nguon["tieu_de_en"], so=4, bo_mien=tuple(mien_co))
        for t in them:
            if t["url"] not in co:
                nguon["trang"].append(t)
                co.add(t["url"])
        if them:
            _ghi_json(nguon_path, nguon)
            trang = nguon["trang"]
        print(f"[nguon] bing: +{len(them)} bao -> {len(trang)} trang", file=sys.stderr)
    bp = {"tieu_de_en": "", "chu": "", "cands": [], "trang_them": []}
    if not khong_browser:
        print("[browser] mo trang goc (tieu de, chu, anh, figure) + bao khac...", file=sys.stderr)
        bp = browser_pass(trang, wd, tim_them=len(trang) < 2)
        doi = False
        if bp["tieu_de_en"] and not nguon.get("tieu_de_en"):
            nguon["tieu_de_en"] = bp["tieu_de_en"]
            doi = True
        co = {t.get("url") for t in trang}
        for t in bp["trang_them"]:
            if t["url"] not in co:
                nguon["trang"].append(t)
                co.add(t["url"])
                doi = True
        if doi:
            _ghi_json(nguon_path, nguon)
            trang = nguon["trang"]
        print(f"[browser] tieu de: {(nguon.get('tieu_de_en') or '')[:70]!r}; +{len(bp['trang_them'])} bao; "
              f"{len(bp['cands'])} anh/figure; {len(bp['chu'])} ky tu chu", file=sys.stderr)
    print(f"[anh] tim tinh qua {len(trang)} nguon...", file=sys.stderr)
    cands = ung_vien_tinh(title, link, nguon_path, nguon.get("tieu_de_en", ""))
    co = {c["anh"] for c in cands}
    for c in bp["cands"]:
        if c["anh"] not in co:
            cands.append(c)
    # arxiv khong anh: bia paper
    if not cands:
        import arxiv_bia
        pdf = arxiv_bia.la_arxiv(link)
        if pdf:
            out = wd / "goc" / "arxiv.png"
            data = arxiv_bia.tai_pdf(pdf)
            bia = arxiv_bia.chup_bia(data) if data else None
            if bia is not None:
                out.parent.mkdir(parents=True, exist_ok=True)
                import luat_anh
                bia.save(out, "PNG", pnginfo=luat_anh.dong_dau("arxiv_bia"))
                cands.append({"anh": str(out), "tep": str(out), "alt": "trang bia paper",
                              "tu": "arxiv_bia", "trang": link, "diem": 60})
    cands.sort(key=lambda c: -c.get("diem", 0))
    anh = tai_va_loc(cands, wd, tin_model)
    print(f"[anh] tai duoc {len(anh)} anh dung duoc", file=sys.stderr)
    if len(anh) < 5:
        # Tin mong anh: them anh that tu Wikimedia Commons theo ten rieng dau
        # tieu de (tru so, san pham, su kien). Chi bu phan thieu.
        tk = _ten_rieng_dau(nguon.get("tieu_de_en") or title)
        if tk:
            them = anh_commons(tk, so=6)
            print(f"[commons] '{tk}': {len(them)} anh", file=sys.stderr)
            if them:
                da = {a["url"] for a in anh}
                bo_sung = tai_va_loc([c for c in them if c["anh"] not in da], wd / "commons", tin_model)
                for i, a in enumerate(bo_sung, start=len(anh) + 1):
                    if len(anh) >= TOI_DA_ANH:
                        break
                    a["ma"] = f"A{i}"
                    moi = wd / "goc" / f"{a['ma']}.png"
                    Path(a["goc"]).replace(moi)
                    a["goc"] = str(moi)
                    a["commons"] = True
                    anh.append(a)
    anh = [phan_loai(a, wd) for a in anh]

    goi_y_bia = [a["ma"] for a in sorted(
        (a for a in anh if "bìa" in a["dung"]),
        key=lambda a: (a["goc_trai_sang"], -a["canh_ngan"]))][:3]
    print("[tu_lieu] boc chu tu nguon...", file=sys.stderr)
    tl = gom_tu_lieu(title, link, nguon_path, wd)
    if len(tl.get("cau_co_so", [])) < 3 and bp.get("chu"):
        # Fetch tinh doc ra rong (trang JS) -> dung chu lay tu browser.
        import tu_lieu as _tl
        doan = [d.strip() for d in bp["chu"].split("\n") if len(d.strip()) > 40]
        tl = {"cau_co_so": _tl.cau_co_so(doan)[:25], "doan_dau": " ".join(doan)[:1500],
              "so_nguon": max(tl.get("so_nguon", 0), 1), "tu": "browser"}
        (wd / "tu_lieu.md").write_text("# Tư liệu (chữ lấy từ browser)\n\n" + "\n\n".join(doan[:60]),
                                       encoding="utf-8")
    flagship = bool(carousel._FLAGSHIP_RE.search(title + " " + tom.get("summary", "")))
    m = {"draft_id": draft_id, "brand": _brand_cua(meta), "title": title, "link": link,
         "via": meta.get("via", ""), "category": meta.get("category", ""),
         "summary": tom.get("summary", ""), "source_note": tom.get("source_note", ""),
         "workdir": str(wd), "tao_luc": int(time.time()),
         "flagship": flagship, "toi_thieu": carousel.FLAGSHIP_MIN if flagship else 5,
         "anh": anh, "cap_ghep": cap_ghep(anh), "goi_y_bia": goi_y_bia, "tu_lieu": tl,
         "nguon_path": str(nguon_path), "tieu_de_en": nguon.get("tieu_de_en", "")}
    bang_anh(anh, wd / "bang_anh.png")
    return m


def main() -> int:
    ap = argparse.ArgumentParser(description="Chuan bi carousel cho Dre (tat dinh)")
    ap.add_argument("draft_id")
    ap.add_argument("--lam-moi", action="store_true", help="Bo cache, lam lai tu dau")
    ap.add_argument("--im", action="store_true", help="Chay nen: khong in brief")
    ap.add_argument("--khong-browser", action="store_true", help="Bo buoc mo browser that")
    ap.add_argument("--cho", type=int, default=300,
                    help="Neu mot tien trinh khac dang chuan bi: doi toi da bao nhieu giay")
    a = ap.parse_args()

    meta = _doc_json(DRAFTS / f"{a.draft_id}.meta.json")
    if not meta:
        sys.exit(f"Khong thay drafts/{a.draft_id}.meta.json — task nay khong do approve_service tao?")
    os.environ.setdefault("CT_BRAND", TEN_CT.get(_brand_cua(meta), "blog"))
    import env_load
    state = env_load.state_dir()
    wd = state / "dre" / a.draft_id
    wd.mkdir(parents=True, exist_ok=True)
    xong, khoa = wd / "xong.json", wd / "dang_chay.pid"

    # Idempotent + khoa: approve_service da khoi chay nen luc chon tin; vai goi
    # lai thi chi doi/in, khong lam hai lan.
    if not a.lam_moi and khoa.exists():
        try:
            pid = int(khoa.read_text().strip() or 0)
            os.kill(pid, 0)
            print(f"[cho] tien trinh {pid} dang chuan bi, doi toi da {a.cho}s...", file=sys.stderr)
            t0 = time.time()
            while khoa.exists() and time.time() - t0 < a.cho:
                time.sleep(3)
        except (ValueError, ProcessLookupError, PermissionError):
            khoa.unlink(missing_ok=True)
    if xong.exists() and not a.lam_moi:
        m = _doc_json(xong)
    else:
        khoa.write_text(str(os.getpid()))
        try:
            m = chuan_bi(a.draft_id, meta, state, wd, khong_browser=a.khong_browser)
            _ghi_json(xong, m)
        finally:
            khoa.unlink(missing_ok=True)
    da_dung = _doc_json(wd / "da_dung.json")
    brief = viet_brief(m, da_dung)
    (wd / "brief.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    else:
        print(f"[xong] {len(m['anh'])} anh, brief o {wd / 'brief.md'}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
