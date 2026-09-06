#!/usr/bin/env python3
"""Tim NGUON cho mot tin — buoc research, thuoc khau cua Finn.

Vi sao dat o day: viec di tim nguon la RESEARCH, do la nghe cua Finn. Truoc day
Vai dung anh tu tim nguon de lay anh, vai viet lai tu tim de lay chu — hai lan tra
cuu cho cung mot tin, va co the ra hai bo bai khac nhau, khien bai viet noi mot
dang con tam anh cho thay mot dang khac.

Nay Finn lam mot lan ngay sau khi Ong Chu chon tin, ghi ra
state/nguon_<draft_id>.json, roi ca vai dung anh lan vai viet cung doc tep do.

Cach tim: Google News KHONG cho URL bai (link cua no la duong chuyen huong chay
bang JS, chuoi CBMi khong phai base64 cua URL, con DuckDuckGo tra 202 chan bot).
Nhung Google News CO cho ten mien toa soan o <source url>. Nen di duong vong:
ten mien -> RSS cua chinh toa soan -> khop tieu de -> ra link bai that.

Dung:
    venv/bin/python nguon_bai.py --tieu-de "..." --link "..." --out state/nguon_x.json
"""
import argparse
import concurrent.futures as cf
import json
import re
import sys
import urllib.parse as up
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import quet_chung                                            # noqa: E402

UA = quet_chung.UA                     # mot ban duy nhat, xem quet_chung
HDR = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
GNEWS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
SO_NGUON = 4

TU_RONG = quet_chung.TU_RONG           # mot ban duy nhat, xem quet_chung
_tu = quet_chung.tu_dac_trung


def _tai(url: str, timeout=20):
    return httpx.get(url, headers=HDR, timeout=timeout, follow_redirects=True)


GNEWS_BAI = "news.google.com/rss/articles"


def giai_ma_gnews(url: str, timeout: int = 30) -> str | None:
    """Link Google News (news.google.com/rss/articles/CBMi...) -> URL bai THAT.

    Tin cua Vera (scan_business doc RSS Google News) luon mang link dang nay.
    Fetch tinh chi ra mot trang chuyen huong chay bang JS, nen anh_bai/tu_lieu
    doc ra RONG — Dre/Miles phai tu web_search lai tin (do that 04/09/2026:
    web_search 11 lan, curl 38 lan trong 4 task carousel dcgr). Giai ma MOT LAN
    o day, ngay luc Ong Chu chon tin, roi moi vai sau dung link that.

    Thu nhe truoc (trang chuyen huong doi khi co san href), khong duoc thi mo
    bang chromium (playwright) va doi URL doi. Khong giai duoc thi tra None —
    nguoi goi giu link cu."""
    if GNEWS_BAI not in (url or ""):
        return url
    try:
        import html as _html
        r = _tai(url, 20)
        m = (re.search(r'data-n-au="([^"]+)"', r.text)
             or re.search(r'<a[^>]+href="(https?://(?!news\.google)[^"]+)"', r.text))
        if m:
            return _html.unescape(m.group(1))
    except Exception:                                        # noqa: BLE001
        pass
    try:
        import time as _t
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage"])
            try:
                page = b.new_page(user_agent=UA.replace("compatible; ", ""))
                page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                t0 = _t.time()
                while "news.google.com" in page.url and _t.time() - t0 < timeout:
                    page.wait_for_timeout(500)
                that = page.url
            finally:
                b.close()
        if that and "news.google.com" not in that:
            return that
    except Exception as e:                                   # noqa: BLE001
        print(f"[nguon_bai] khong giai duoc link Google News: {type(e).__name__}",
              file=sys.stderr)
    return None


BING_RSS = "https://www.bing.com/news/search?q={q}&format=rss"
BO_MIEN = ("msn.com", "seekingalpha.com", "news.google.com", "bing.com", "yahoo.com")


TU_RONG_TRUY_VAN = {"the", "a", "an", "of", "in", "on", "to", "for", "and", "or",
                    "with", "is", "its", "as", "at", "by", "from", "how", "nearly", "targets",
                    "introducing", "launches", "unveils", "announces", "says", "new", "news"}


# ---- LUAT: KHONG BAO GIO tim kiem bang tieng Viet ----------------------------
# Ong Chu 05/09/2026. Su co: manifest cua Vera luu tieu de DA DICH sang tieng Viet
# ("Nvidia dam phan rot $2,5 ty vao Thinking Machines Lab cua Mira Murati"); ca
# Google News RSS lan Bing News la kho tieng Anh -> 0 ket qua -> chi con 1 trang
# goc (paywall) -> engine anh vot duoc 1 anh lac de -> Dre bo cuoc. Cung luc, cau
# tieng Anh tra 40 bai. Tieu de tim kiem phai la tieng Anh: lay og:title cua bai
# goc; khong lay duoc thi chi giu ten rieng/so (khong dau) trong tieu de Viet.
_DAU_VIET = re.compile(r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợ"
                       r"ùúủũụưừứửữựỳýỷỹỵđÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊ"
                       r"ÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]")
_TU_VIET_KHONG_DAU = {"cua", "va", "voi", "cho", "trong", "tren", "duoi", "khi", "la",
                      "co", "khong", "se", "da", "dang", "moi", "lon", "nho", "ty", "trieu",
                      "ngan", "nghin", "usd", "vnd", "dong"}


def co_tieng_viet(t: str) -> bool:
    return bool(_DAU_VIET.search(t or ""))


def _tieu_de_trang(url: str) -> str:
    """og:title / <title> cua bai goc — tieu de tieng Anh THAT cua toa soan."""
    try:
        r = httpx.get(url, headers=HDR, timeout=20, follow_redirects=True)
        html = r.text[:200_000]
        m = (re.search(r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)', html, re.I)
             or re.search(r'content=["\']([^"\']+)["\'][^>]*property=["\']og:title', html, re.I)
             or re.search(r"<title[^>]*>([^<]{5,200})</title>", html, re.I))
        if not m:
            return ""
        import html as _h
        t = _h.unescape(m.group(1)).strip()
        t = re.sub(r"\s+[|\-–—]\s+[^|\-–—]{2,40}$", "", t)      # bo " | Ten bao"
        return "" if co_tieng_viet(t) or len(t) < 8 else t
    except Exception:                                        # noqa: BLE001
        return ""


def _ten_rieng_khong_dau(tieu_de_viet: str) -> str:
    """Duong lui: chi giu ten rieng / so KHONG DAU trong tieu de Viet
    ("Nvidia Thinking Machines Lab Mira Murati 2,5"). Van la truy van tieng Anh."""
    t = re.sub(r"[\$;:,\"\'()\[\]|—–-]", " ", tieu_de_viet or "")
    ra = []
    for w in t.split():
        if co_tieng_viet(w) or w.lower() in _TU_VIET_KHONG_DAU or len(w) < 2:
            continue
        if w[:1].isupper() or any(c.isdigit() for c in w) or w.isupper():
            ra.append(w)
    return " ".join(ra[:8])


def tieu_de_tim(tieu_de: str, link: str) -> str:
    """Tieu de DUNG DE TIM KIEM (tieng Anh). Rong = khong duoc tim gi ca."""
    if tieu_de and not co_tieng_viet(tieu_de):
        return tieu_de
    en = _tieu_de_trang(link) if link else ""
    if en:
        print(f"[nguon_bai] tieu de tim = og:title bai goc: {en[:90]}", file=sys.stderr)
        return en
    en = _ten_rieng_khong_dau(tieu_de)
    if len(en.split()) >= 2:
        # Bac 3: hoi Google News bang ten rieng, lay HEADLINE tieng Anh cua bai
        # dau (chung >= 2 tu voi ten rieng) — cau day du keo ve nhieu bao hon
        # hin ten rieng roi rac (Nvidia 05/09: ten rieng -> 3 trang, headline -> 40).
        try:
            its = ET.fromstring(_tai(GNEWS.format(q=up.quote(en)), 20).content).findall(".//item")
            goc = _tu(en)
            for it in its[:5]:
                hd = re.sub(r"\s+-\s+[^-]{2,60}$", "", it.findtext("title") or "").strip()
                if hd and not co_tieng_viet(hd) and len(goc & _tu(hd)) >= 2:
                    print(f"[nguon_bai] tieu de tim = headline Google News: {hd[:90]}", file=sys.stderr)
                    return hd
        except Exception as e:                               # noqa: BLE001
            print(f"[nguon_bai] google news (headline) hong: {type(e).__name__}", file=sys.stderr)
        print(f"[nguon_bai] tieu de tim = ten rieng khong dau: {en}", file=sys.stderr)
        return en
    print("[nguon_bai] KHONG co tieu de tieng Anh -> khong tim bao khac (luat: khong tim bang tieng Viet)",
          file=sys.stderr)
    return ""


def _truy_van_bing(tieu_de: str) -> list:
    if co_tieng_viet(tieu_de):
        print("[nguon_bai] TU CHOI truy van Bing bang tieng Viet", file=sys.stderr)
        return []
    """Bing News chi tra ket qua cho truy van NGAN va nhay chu (do 04/09/2026:
    tieu de day du -> 1 bai; "Broadcom AI revenue FY27" -> 11; "Broadcom
    Targets 115B Revenue FY27" -> 0). Sinh NHIEU dang truy van roi lay hop ket
    qua: tu dac trung 5/4/3 tu (giu "AI"/"model"), ten rieng + so 4/3 tu, ten
    rieng dau + AI."""
    t = re.sub(r"^\[[^\]]{1,20}\]\s*", "", tieu_de or "")
    t = re.sub(r"[\$;:,\"\'()\[\]|]", " ", t)
    tu = [w for w in t.split() if w.lower() not in TU_RONG_TRUY_VAN and len(w) > 1]
    rieng = [w for w in tu if w[:1].isupper() or any(c.isdigit() for c in w)]
    ra = []
    for ds in (tu[:5], tu[:4], tu[:3], rieng[:4], rieng[:3],
               ([rieng[0], "AI"] if rieng and "AI" in tu else [])):
        q = " ".join(ds)
        if q and q not in ra:
            ra.append(q)
    return ra


def bao_khac_bing(tieu_de: str, so: int = 4, bo_mien: tuple = (), ngay: int = 10) -> list:
    if co_tieng_viet(tieu_de):
        print("[nguon_bai] TU CHOI bao_khac_bing bang tieng Viet", file=sys.stderr)
        return []
    """Bao khac dua cung tin qua Bing News RSS. Khac Google News, link cua Bing
    la chuyen huong HTTP thuong (apiclick.aspx) -> di theo redirect la ra URL
    bai that, khong can browser. ~1s/link.

    Loc: bai trong `ngay` ngay gan day, tieu de phai chung >= 2 tu dac trung voi
    tieu de goc (truy van ngan de keo ve ca tin cu/khong lien quan). Bo trang
    tong hop (msn, yahoo), trang chan bot (seekingalpha) va `bo_mien`.
    Tra ve [{url, loai: "báo", tieu_de, toa_soan}]."""
    import email.utils as eu
    import time as _t
    goc = _tu(tieu_de)
    moc = _t.time() - ngay * 86400
    its, co_link = [], set()
    for q in _truy_van_bing(tieu_de):
        try:
            r = _tai(BING_RSS.format(q=up.quote(q)), 20)
            for it in ET.fromstring(r.content).findall(".//item"):
                k = it.findtext("link") or ""
                if k and k not in co_link:
                    co_link.add(k)
                    its.append(it)
        except Exception as e:                               # noqa: BLE001
            print(f"[nguon_bai] bing rss hong: {type(e).__name__}", file=sys.stderr)
        if len(its) >= so * 3:
            break
    ra, thay = [], set()
    for it in its[: so * 6]:
        link = it.findtext("link") or ""
        td = it.findtext("title") or ""
        if not link or len(goc & _tu(td)) < 2:
            continue
        try:
            ts = eu.parsedate_to_datetime(it.findtext("pubDate") or "").timestamp()
            if ts < moc:
                continue
        except Exception:                                    # noqa: BLE001
            pass
        try:
            rr = httpx.head(link, headers=HDR, timeout=12, follow_redirects=True)
            u = str(rr.url)
            if rr.status_code != 200:
                continue
        except Exception:                                    # noqa: BLE001
            continue
        m = re.match(r"https?://([^/]+)", u)
        mien = (m.group(1) if m else "").replace("www.", "")
        if not mien or mien in thay or any(b in mien for b in BO_MIEN + tuple(bo_mien)):
            continue
        thay.add(mien)
        ra.append({"url": u, "loai": "báo", "tieu_de": td[:160], "toa_soan": "https://" + mien})
        if len(ra) >= so:
            break
    return ra


def tim(tieu_de: str, link: str, so=SO_NGUON) -> dict:
    link_gnews = None
    if GNEWS_BAI in link:
        that = giai_ma_gnews(link)
        if that:
            link_gnews, link = link, that
            print(f"[nguon_bai] link Google News -> {link[:90]}", file=sys.stderr)
    ra = [{"url": link, "loai": "gốc", "tieu_de": tieu_de}]
    # Tim kiem CHI bang tieng Anh (xem luat o tren). `ten` rong -> khong hoi feed nao.
    ten = tieu_de_tim(tieu_de, link)
    its = []
    if ten:
        try:
            its = ET.fromstring(_tai(GNEWS.format(q=up.quote(ten)), 25).content
                                ).findall(".//item")
        except Exception as e:                               # noqa: BLE001
            print(f"[nguon_bai] google news hong: {type(e).__name__}", file=sys.stderr)

    mien = []
    for it in its[: so * 3]:
        src = it.find("source")
        u = (src.get("url") if src is not None else "") or ""
        if u:
            u = u.rstrip("/")
            if u not in [m for m, _ in mien]:
                mien.append((u, it.findtext("title") or ""))

    goc = _tu(ten or tieu_de)

    def _trong_feed(cap):
        m, _ = cap
        for duong in ("/feed/", "/rss", "/feed", "/rss.xml", "/index.xml"):
            try:
                rr = _tai(m + duong, 15)
                if rr.status_code != 200 or b"<item" not in rr.content[:400_000]:
                    continue
                for i in ET.fromstring(rr.content).findall(".//item"):
                    t = i.findtext("title") or ""
                    chung = goc & _tu(t)
                    if chung and len(chung) / max(len(goc), 1) >= 0.5:
                        return {"url": i.findtext("link") or "", "loai": "báo",
                                "tieu_de": t, "toa_soan": m}
                return None
            except Exception:                                # noqa: BLE001
                continue
        return None

    thay = {link}
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for kq in ex.map(_trong_feed, mien[: so * 3]):
            if kq and kq["url"] and kq["url"] not in thay:
                thay.add(kq["url"])
                ra.append(kq)
            if len(ra) > so:
                break
    # Goi Bing khi chua du `so`+1 nguon (truoc: < 3). Vong feed thuong chi ra 2-3
    # trang vi nhieu toa soan khong co RSS; Bing voi headline tieng Anh bu phan con lai.
    if len(ra) <= so:
        m = re.match(r"https?://([^/]+)", link)
        mien_goc = ((m.group(1) if m else "").replace("www.", ""),)
        for t in (bao_khac_bing(ten, so=so, bo_mien=mien_goc) if ten else []):
            if t["url"] not in thay:
                thay.add(t["url"])
                ra.append(t)
            if len(ra) > so:
                break
    kq = {"tieu_de": tieu_de, "tieu_de_en": ten, "link_goc": link, "trang": ra}
    if link_gnews:
        kq["link_gnews"] = link_gnews
    return kq


def main():
    ap = argparse.ArgumentParser(description="Tim nguon cho mot tin (viec cua Finn)")
    ap.add_argument("--tieu-de", required=True)
    ap.add_argument("--link", required=True)
    ap.add_argument("--so", type=int, default=SO_NGUON)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    kq = tim(a.tieu_de, a.link, a.so)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(kq, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    print(a.out)
    for t in kq["trang"]:
        print(f"  [{t['loai']}] {t['url'][:88]}", file=sys.stderr)
    return 0 if len(kq["trang"]) > 1 else 1


if __name__ == "__main__":
    sys.exit(main())
