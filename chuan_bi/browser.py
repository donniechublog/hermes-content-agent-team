#!/usr/bin/env python3
"""PHA BROWSER: mo trang bang Playwright, boc anh trong trang, giai chuyen huong Google News.

Tach tu image_prepare.py 09/09/2026 (audit A1, di chuyen thuan — than ham giu y nguyen).
"""
import re
import sys
import time
from pathlib import Path


import image_rules
import env_load
from browser_session import session_or_new

from chuan_bi.chung import GNEWS, _mien


def _js_browser() -> dict:
    """Cac doan JS chay trong trang. Dung ham (khong phai hang module) vi chung
    ghep nguong/regex cua luat_anh tai thoi diem goi — doi luat_anh la doi JS."""
    JS_TITLE = """() => ((document.querySelector('meta[property="og:title"]')||{}).content
                    || document.title || '')"""
    JS_TEXT = """() => ((document.querySelector('article') || document.querySelector('main')
                    || document.body).innerText || '').slice(0, 20000)"""
    # Chi lay anh TRONG bai (article/main). Truoc day vot ca document.images ->
    # banner quang cao (Phemex), widget "for you", onboarding, placeholder logo
    # deu vao kho (bo Broadcom/Gimlet dcgr 05/09/2026). Loai theo ba lop: to
    # tien la ad/aside/nav/related/promo; src/class/id/alt mang tu quang cao;
    # va phan tu cao hon 75% trang (chup ca trang chu).
    JS_LOAI = """
        const XAU_DOM = """ + image_rules.js_junk_dom_pattern() + """;
        const XAU_URL = """ + image_rules.js_junk_url_pattern() + """;
        const trongBai = (el) => { const a = document.querySelector('article') || document.querySelector('main');
            return !a || a.contains(el); };
        const xau = (el) => { for (let e = el; e; e = e.parentElement) {
            const t = (e.tagName||'').toLowerCase();
            if (['aside','nav','footer','header','iframe'].includes(t)) return true;
            const k = ((e.className && e.className.baseVal) ? e.className.baseVal : (e.className||'')) + ' ' + (e.id||'');
            if (XAU_DOM.test(k.replace(/[-_]/g,' '))) return true; } return false; };
        const caoQua = (r) => r.height > Math.max(900, 0.75 * document.documentElement.scrollHeight);
    """
    JS_IMG = JS_LOAI + """() => Array.from(document.images)
        .filter(i => i.naturalWidth >= """ + str(image_rules.TAI_W_MIN) + """ && i.naturalHeight >= """ + str(image_rules.TAI_H_MIN) + """)
        .filter(i => trongBai(i) && !xau(i) && !XAU_URL.test((i.currentSrc||i.src||'').replace(/[-_]/g,' '))
                     && !XAU_URL.test((i.alt||'').replace(/[-_]/g,' ')))
        .map(i => ({src: i.currentSrc || i.src, alt: i.alt || '',
                    w: i.naturalWidth, h: i.naturalHeight})).slice(0, 12)"""
    JS_FIG = JS_LOAI + """() => { const ra = []; let k = 0;
        for (const s of ['table', 'canvas', 'svg', 'figure']) {
          for (const el of document.querySelectorAll(s)) {
            if (!trongBai(el) || xau(el)) continue;
            // <figure> la khung CHUNG cho ca chart LAN anh bien tap (photo +
            // figcaption) — LOW-45 (12/09/2026): TechCrunch boc dung anh hero
            // cua bai trong <figure>, code cu chup nguyen khoi coi la "chart",
            // dinh ca dai credit, roi vong chup nguon (LOW-22) lai tu tim ra
            // DUNG anh hero do lan nua — cung mot anh len ca bia lan slide
            // than. Chi coi <figure> la ung vien chart khi no THAT SU boc mot
            // bang/do thi (co canvas/svg/table ben trong); <figure><img> thuan
            // (anh bao + caption) thi bo qua o day — da co JS_IMG quet <img>
            // rieng, va vong chup nguon se tu tim hero neu con thieu.
            if (s === 'figure' && !el.querySelector('canvas, svg, table')) continue;
            const r = el.getBoundingClientRect();
            const w = Math.max(el.scrollWidth || 0, r.width), h = Math.max(el.scrollHeight || 0, r.height);
            if (w < 600 || h < 300 || w > 4000 || h > 6000 || caoQua(r)) continue;
            el.setAttribute('data-dre', 'f' + k);
            ra.push({sel: '[data-dre="f' + k + '"]', w, h, tag: s}); k++;
            if (ra.length >= 4) return ra;
          } }
        return ra; }"""
    JS_GNEWS = """() => Array.from(document.querySelectorAll('a[href*="/read/"], a[href*="/articles/"]'))
                     .map(a => a.href).slice(0, 10)"""
    return {"TITLE": JS_TITLE, "TEXT": JS_TEXT, "IMG": JS_IMG, "FIG": JS_FIG, "GNEWS": JS_GNEWS}


def _lay_anh_trang(page, url, so, wd, ra, JS, chup_fig=True, tran=None):
    """Anh <img> lon + figure/table/canvas/svg cua MOT trang, ghi vao ra['cands']."""
    # Tran moi trang: goc <= 4 anh, bao khac <= 3. Truoc day vet toi 12 anh
    # mot trang -> mot URL lap ca kho (Ong Chu 05/09/2026). Trang CONG BO chinh
    # chu (LOW-21) duoc tran cua bai goc: chart benchmark o do la anh dat nhat.
    for im in (page.evaluate(JS["IMG"]) or [])[: tran or (4 if so == 0 else 3)]:
        ra["cands"].append({"anh": im["src"], "alt": im["alt"], "og": False, "tu": "browser",
                            "trang": url, "rong": im["w"], "cao": im["h"], "diem": 45})
    if not chup_fig:
        return
    for f in page.evaluate(JS["FIG"]) or []:
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
        image_rules.stamp_file(out, "chup_chart")
        # alt de TRONG: chu "figure"/"screenshot" tu gan tung khop QUY cua
        # anh_bai -> hint_chart -> nhan CHART cho ca quang cao (05/09/2026).
        ra["cands"].append({"anh": str(out), "tep": str(out), "alt": "", "alt_chup": f"{f['tag']} chup tu trang",
                            "og": False, "tu": "chup", "the": f["tag"], "trang": url,
                            "rong": int(f["w"] * 2), "cao": int(f["h"] * 2), "diem": 50})


def _mo_trang(page, url, cho_yen=12000):
    page.goto(url, wait_until="domcontentloaded", timeout=30000)
    try:
        page.wait_for_load_state("networkidle", timeout=cho_yen)
    except Exception:                                    # noqa: BLE001
        pass
    page.wait_for_timeout(700)


def _tim_bao_gnews(page, ra, mien_goc, het_gio, JS):
    """Bo nguon mong: tim bao khac tren Google News theo tieu de tieng Anh, di
    theo chuyen huong tung link /read/, giu toi da 3 bao lien quan."""
    import urllib.parse as up
    # 2) tim bao khac (bo nguon mong)
    if True:
        try:
            q = re.sub(r"^\[[^\]]{1,20}\]\s*", "", ra["tieu_de_en"])[:120]
            _mo_trang(page, "https://news.google.com/search?q=" + up.quote(q)
               + "&hl=en-US&gl=US&ceid=US:en", cho_yen=6000)
            links, thay = [], set()
            for h in page.evaluate(JS["GNEWS"]) or []:
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
                    td = (page.title() or "")[:160]
                    # Google News tra ca bai KHONG lien quan (cung tu "AI"):
                    # bai benh than, letsdatascience (Gimlet 05/09). Phai
                    # chung >= 2 tu dac trung voi tieu de goc, nhu Bing da loc.
                    import anh_bai as _ab
                    if len(_ab._tu_dac_trung(ra["tieu_de_en"]) & _ab._tu_dac_trung(td)) < 2:
                        print(f"[browser] bo bao khong lien quan: {td[:60]!r}", file=sys.stderr)
                        continue
                    ra["trang_them"].append({"url": u, "loai": "báo",
                                             "tieu_de": td,
                                             "toa_soan": "https://" + _mien(u)})
                except Exception:                # noqa: BLE001
                    continue
        except Exception as e:                   # noqa: BLE001
            print(f"[browser] gnews search: {type(e).__name__}: {e!r}", file=sys.stderr)


def browser_pass(trang: list, wd: Path, tim_them: bool, gio_han=110, phien=None) -> dict:
    """MOT phien chromium lam het phan "mo browser that" ma SOUL tung bat vai lam tay:

      - trang goc: og:title (tieu de tieng Anh), CHU bai (innerText cua
        article/main — trang JS nhu ifm.ai fetch tinh doc ra rong), <img> lon
        (naturalWidth) ma fetch tinh bo sot, va chup figure/table/canvas/svg lon
        full be ngang (bang benchmark, chart);
      - bo nguon mong (chi co link goc): tim bao khac tren trang tim kiem Google
        News, giai ma tung link /read/ bang cach di theo chuyen huong;
      - 1-2 trang bao khac: lay <img> lon + figure.

    `phien` (PhienBrowser, tuy chon): dung chung tien trinh Chromium voi cac
    buoc khac cua cung mot bai thay vi tu mo rieng — audit B4. Khong truyen thi
    tu mo va tu dong, y nhu truoc.

    Khong co playwright / trang hong thi tra ve phan da lay duoc, khong loi."""
    # Thieu playwright thi `except` cuoi ham bat va IN RA ly do. Truoc day co
    # mot buoc kiem rieng o day, tra ve rong IM LANG — dung lop "hong cam lang"
    # ma quy uoc C1 di go.
    ra = {"tieu_de_en": "", "chu": "", "cands": [], "trang_them": []}
    JS = _js_browser()
    t0 = time.time()
    goc = next((t.get("url") for t in trang if t.get("loai") == "gốc" and t.get("url")), None) \
        or (trang[0].get("url") if trang else "")
    mien_goc = _mien(goc)

    def het_gio():
        return time.time() - t0 > gio_han

    try:
        with session_or_new(phien) as ph:
            with ph.trang(viewport={"width": 1600, "height": 1200}, device_scale_factor=2,
                          user_agent=env_load.UA_BROWSER) as page:
                # 1) trang goc
                if goc and goc.startswith("http") and GNEWS not in goc:
                    try:
                        _mo_trang(page, goc)
                        ra["tieu_de_en"] = re.sub(r"\s+[|\-–—]\s+[^|\-–—]{2,40}$", "",
                                                  (page.evaluate(JS["TITLE"]) or "").strip())
                        ra["chu"] = page.evaluate(JS["TEXT"]) or ""
                        _lay_anh_trang(page, goc, 0, wd, ra, JS)
                    except Exception as e:                   # noqa: BLE001
                        print(f"[browser] goc {goc[:60]}: {type(e).__name__}: {e!r}", file=sys.stderr)
                # 2) tim bao khac (bo nguon mong)
                if tim_them and ra["tieu_de_en"] and not het_gio():
                    _tim_bao_gnews(page, ra, mien_goc, het_gio, JS)
                # 3) bao khac (co san trong nguon + vua tim): lay anh, toi da 2 trang
                khac = [t for t in trang if t.get("url") and t.get("url") != goc and GNEWS not in t["url"]]
                khac += ra["trang_them"]
                # Trang cong bo chinh chu di TRUOC (LOW-21): chi mo 2 trang khac,
                # khong duoc de no rot khoi cua so vi bao Bing them vao truoc.
                khac.sort(key=lambda t: t.get("loai") != "công bố")
                for i, t in enumerate(khac[:2], start=1):
                    if het_gio():
                        break
                    try:
                        _mo_trang(page, t["url"], cho_yen=8000)
                        _lay_anh_trang(page, t["url"], i, wd, ra, JS,
                                       tran=4 if t.get("loai") == "công bố" else None)
                    except Exception as e:                   # noqa: BLE001
                        print(f"[browser] {t['url'][:60]}: {type(e).__name__}: {e!r}", file=sys.stderr)
    except Exception as e:                                   # noqa: BLE001
        print(f"[browser] bo qua: {type(e).__name__}: {e}", file=sys.stderr)
    return ra
