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
import env_load                                              # noqa: E402

UA = quet_chung.UA                     # mot ban duy nhat, xem quet_chung
HDR = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
GNEWS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
SO_NGUON = 4

TU_RONG = quet_chung.TU_RONG           # mot ban duy nhat, xem quet_chung
_tu = quet_chung.tu_dac_trung

# ---- "CUNG TIN" (LOW-33, 12/09/2026) ------------------------------------------
# The Ethan "DeepSeek-V4.1-Flash tha trong so" ra anh con vit-robot: `tieu_de_en`
# la <title> thô cua trang HuggingFace "deepseek-ai/DeepSeek-V4.1-Flash · Hugging
# Face" — hau to " · Hugging Face" khong bi boc (regex chi biet | - – —), hai chu
# "Hugging"+"Face" tu no da du nguong "chung >= 2 tu", nen Bing tra bai
# "Hugging Face robot duck is already a hit" va no thanh "bao khac cung tin".
# Ba lop sua: boc hau to voi ca `·`/`»`; ten nen tang (HuggingFace, GitHub,
# arXiv...) KHONG duoc tinh la tu dac trung; va moi cho quyet "cung tin" di qua
# MOT ham `cung_tin` — ke ca vong chup trang nguon, truoc day mien kiem.
_HAU_TO_SITE = re.compile(r"\s+[|\-–—·»]\s+[^|\-–—·»]{2,40}$|\s+::\s+[^:]{2,40}$")
_TU_NEN = {"hugging", "face", "huggingface", "github", "arxiv", "reddit", "medium",
           "substack", "youtube", "twitter", "linkedin", "wikipedia", "hacker", "news"}


def bo_hau_to_site(t: str) -> str:
    """"Tieu de · Ten site" / "Tieu de | Ten bao" -> "Tieu de"."""
    return _HAU_TO_SITE.sub("", (t or "").strip())


def tu_cung_tin(t: str) -> set:
    """Tu dac trung DUNG DE SO "cung tin": bo hau to site va bo ten nen tang."""
    return _tu(bo_hau_to_site(t)) - _TU_NEN


def cung_tin(tieu_de_goc: str, tieu_de_khac: str, toi_thieu: int = 2) -> bool:
    """Hai tieu de co noi ve CUNG mot tin khong: chung >= `toi_thieu` tu dac trung
    sau khi bo hau to site va ten nen tang."""
    return len(tu_cung_tin(tieu_de_goc) & tu_cung_tin(tieu_de_khac)) >= toi_thieu


def _tai(url: str, timeout=20):
    return httpx.get(url, headers=HDR, timeout=timeout, follow_redirects=True)


GNEWS_BAI = "news.google.com/rss/articles"


def giai_ma_gnews(url: str, timeout: int = 30, phien=None) -> str | None:
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
        from phien_browser import phien_hoac_moi
        # `phien`: dung chung tien trinh Chromium voi cac buoc khac cua cung mot
        # bai (audit B4). Khong truyen thi tu mo, tu dong — y nhu truoc.
        with phien_hoac_moi(phien) as ph:
            with ph.trang(user_agent=UA.replace("compatible; ", "")) as page:
                page.goto(url, wait_until="domcontentloaded", timeout=timeout * 1000)
                t0 = _t.time()
                while "news.google.com" in page.url and _t.time() - t0 < timeout:
                    page.wait_for_timeout(500)
                that = page.url
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


# Trang chan bot (Cloudflare/Akamai) tra 403 kem trang "Just a moment...", hoac
# title chi con la ten mien tran. Nhan dien de KHONG dem lam tieu de that (bai
# Economist 08/09/2026: httpx lan Playwright/Chromium that deu bi chan giong nhau).
_CHAN_BOT = re.compile(r"just a moment|attention required|checking your browser|"
                       r"access denied|are you (a )?human|enable javascript and cookies",
                       re.I)

RSS_DOAN = ("/rss.xml", "/feed", "/feed.xml", "/feed/", "/rss", "/index.xml")


def _tieu_de_rss(url: str) -> str:
    """Do RSS cong khai cua toa soan de lay tieu de THAT khi trang bai bi chan bot.

    Vi du that: economist.com chan ca httpx lan Chromium that (403 "Just a
    moment..."), nhung economist.com/finance-and-economics/rss.xml van 200 va
    liet ke dung bai voi tieu de goc. Doan feed toan trang truoc, roi feed theo
    chuyen muc (doan dau URL) — khop link (bo query/slash cuoi) de lay tieu de."""
    try:
        u = up.urlsplit(url)
    except Exception:                                        # noqa: BLE001
        return ""
    if not u.scheme or not u.netloc:
        return ""
    goc = f"{u.scheme}://{u.netloc}"
    doan_dau = u.path.strip("/").split("/")[0] if u.path.strip("/") else ""
    ung_vien = [goc + d for d in RSS_DOAN]
    if doan_dau:
        ung_vien = [f"{goc}/{doan_dau}/rss.xml", f"{goc}/{doan_dau}/feed"] + ung_vien
    dich = url.split("?")[0].rstrip("/")
    for feed in ung_vien[:6]:
        try:
            r = _tai(feed, 12)
            if r.status_code != 200 or b"<item" not in r.content[:400_000]:
                continue
            for it in ET.fromstring(r.content).findall(".//item"):
                lk = (it.findtext("link") or "").split("?")[0].rstrip("/")
                if lk != dich:
                    continue
                t = (it.findtext("title") or "").strip()
                if t and not co_tieng_viet(t):
                    print(f"[nguon_bai] tieu de tim = RSS toa soan ({feed}): {t[:90]}",
                          file=sys.stderr)
                    return t
        except Exception:                                    # noqa: BLE001
            continue
    return ""


def _tieu_de_trang(url: str) -> str:
    """og:title / <title> cua bai goc — tieu de tieng Anh THAT cua toa soan.

    Trang SPA chua hydrate (vd techinasia.com fetch tinh) tra <title> = TEN
    THUONG HIEU site ("Tech in Asia"), khong phai headline — qua check cu
    "khong tieng Viet" nen bi nhan la tieu de that, roi tro thanh truy van +
    thuoc do "cung tin" chi con 2 tu chung, khop voi ca bai khong lien quan
    (Gimlet 06/09: khop nham bai PR "Tech Week Singapore 2026" vi ca hai co
    "tech" + "asia"). Headline that hau nhu luon >=4 tu; ten thuong hieu/site
    thi 1-3 tu — loai o day, roi thu RSS thay vi bo cuoc luon.

    Trang bi chan bot (403/challenge) -> cung thu RSS cong khai truoc khi bo
    cuoc (Economist 08/09/2026: httpx lan Playwright/Chromium that deu bi
    chan giong nhau)."""
    try:
        r = httpx.get(url, headers=HDR, timeout=20, follow_redirects=True)
        if r.status_code == 200:
            html = r.text[:200_000]
            m = (re.search(r'property=["\']og:title["\'][^>]*content=["\']([^"\']+)', html, re.I)
                 or re.search(r'content=["\']([^"\']+)["\'][^>]*property=["\']og:title', html, re.I)
                 or re.search(r"<title[^>]*>([^<]{5,200})</title>", html, re.I))
            if m:
                import html as _h
                t = _h.unescape(m.group(1)).strip()
                t = bo_hau_to_site(t)                    # bo " | Ten bao", " · Hugging Face"
                if t and len(t.split()) < 4:
                    print(f"[nguon_bai] bo tieu de qua ngan (co the la ten site, chua hydrate): {t!r}",
                          file=sys.stderr)
                elif t and len(t) >= 8 and not co_tieng_viet(t) and not _CHAN_BOT.search(t):
                    return t
    except Exception:                                        # noqa: BLE001
        pass
    return _tieu_de_rss(url)


def _ten_rieng_khong_dau(tieu_de_viet: str) -> str:
    """Duong lui: chi giu ten rieng / so KHONG DAU trong tieu de Viet
    ("Nvidia Thinking Machines Lab Mira Murati 2,5"). Van la truy van tieng Anh.

    GIU gach noi TRONG token (LOW-21, 11/09/2026): ten model kieu
    `deepseek-v4.1-flash-max` la MOT ten rieng. Ban cu xoa `-` truoc khi tach
    tu, nen no vo thanh `deepseek` (thuong, khong so -> bo) + `v4.1` + `flash`
    + `max`, truy van con `v4.1 LiveBench #6 81.4 2.4` -> Bing 0 bao, va Dre bi
    chan "thieu anh" cho tin ma bao nao cung dua. Gach dai/ngang (— –) van la
    dau cau, van xoa."""
    t = re.sub(r"[\$;:,\"\'()\[\]|—–]", " ", tieu_de_viet or "")
    ra = []
    for w in t.split():
        w = w.strip("-")
        if not w or co_tieng_viet(w) or w.lower() in _TU_VIET_KHONG_DAU or len(w) < 2:
            continue
        if w[:1].isupper() or any(c.isdigit() for c in w) or w.isupper():
            ra.append(w)
    return " ".join(ra[:8])


def tieu_de_tim(tieu_de: str, link: str) -> str:
    """Tieu de DUNG DE TIM KIEM (tieng Anh). Rong = khong duoc tim gi ca.

    Uu tien HEADLINE THAT cua toa soan (og:title hoac RSS) hon tieu de dau vao,
    ke ca khi tieu de dau vao da la tieng Anh: no co the la DEK/subtitle hay
    tieu de HN paraphrase, cau chu khac voi cach bao khac dua lai tin nen tim
    ra 0 ket qua. Vi du that (Economist 08/09/2026): dek "Initial effects of AI
    technology on employment look positive" -> Google News 0 bai; headline that
    "The jobs apocalypse is postponed. An AI jobs boom is here" -> ra New Yorker."""
    en = _tieu_de_trang(link) if link else ""
    if en:
        print(f"[nguon_bai] tieu de tim = og:title/RSS bai goc: {en[:90]}", file=sys.stderr)
        return en
    if tieu_de and not co_tieng_viet(tieu_de):
        return tieu_de
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
    rieng dau + AI.

    Ten model co gach noi (`deepseek-v4.1-flash-max`) thu THEM ban bo gach
    TRUOC (LOW-21, do 11/09/2026: `deepseek-v4.1-flash-max LiveBench #6` -> 1
    bai, `deepseek v4.1 flash max` -> 6 bai — Bing coi gach noi la mot token
    khac voi cach bao viet "DeepSeek V4.1 Flash")."""
    t = re.sub(r"^\[[^\]]{1,20}\]\s*", "", tieu_de or "")
    t = re.sub(r"[\$;:,\"\'()\[\]|]", " ", t)
    ra = []
    for tt in ([t.replace("-", " "), t] if "-" in t else [t]):
        tu = [w for w in tt.split() if w.lower() not in TU_RONG_TRUY_VAN and len(w) > 1]
        rieng = [w for w in tu if w[:1].isupper() or any(c.isdigit() for c in w)]
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
    tieu_de = bo_hau_to_site(tieu_de)      # LOW-33: " · Hugging Face" khong vao truy van
    goc = tu_cung_tin(tieu_de)
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
        if not link or len(goc & tu_cung_tin(td)) < 2:
            continue
        try:
            ts = eu.parsedate_to_datetime(it.findtext("pubDate") or "").timestamp()
            if ts < moc:
                continue
        except Exception:                                    # noqa: BLE001
            pass
        try:
            if not quet_chung.url_an_toan(link):
                continue
            rr = httpx.head(link, headers=HDR, timeout=12, follow_redirects=True)
            u = str(rr.url)
            # `u` la dia chi SAU chuyen huong va duoc dung lam nguon that cho
            # bai — mot ket qua tim kiem 302 ve 127.0.0.1 khong duoc di tiep.
            if rr.status_code != 200 or not quet_chung.url_an_toan(u):
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


def bao_ve_tu_khoa(tu_khoa: str, so: int = 6, bo_mien: tuple = (), ngay: int | None = None) -> list:
    """Bao THẬT về một TỪ KHOÁ (tên hãng/sản phẩm) qua Bing News RSS — KHÁC
    `bao_khac_bing`: không đòi "cùng một sự kiện" với một tiêu đề gốc, VÀ
    KHÔNG GIỚI HẠN THỜI GIAN (Ông Chủ 13/09/2026, chốt nguyên tắc nguồn ở
    LUAT_ANH.md §1.2d: *"được tìm không giới hạn thời gian, sự kiện. miễn là
    trong article có nhắc tới tên brand... ngoài nguyên tắc này, không có bất
    kỳ một cấm đoán nào về nguồn ảnh"*). Trước đó (LOW-45, 13/09 sáng) còn giới
    hạn 20 ngày và chỉ coi là phương án khi Commons/Wikidata RỖNG — hai giới
    hạn đó đã bỏ theo đúng luật mới; `ngay` giữ lại làm tham số CHO PHÉP hẹp
    lại nếu một lần gọi cụ thể cần, mặc định là KHÔNG giới hạn.

    Lọc nhẹ hơn `bao_khac_bing`: chỉ đòi tiêu đề bài chứa lại chính TỪ KHOÁ
    (không đòi khớp với MỘT sự kiện cụ thể nào) — vì mục đích là ảnh MINH HOẠ
    hãng/sản phẩm (như ảnh khái niệm), không phải bằng chứng của một tin riêng.
    Cùng hạ tầng với `bao_khac_bing`: giải chuyển hướng HTTP, chặn SSRF
    (`quet_chung.url_an_toan`), bỏ trang tổng hợp/`bo_mien`. Ngôn ngữ: chỉ Anh
    hoặc Trung (LUAT_ANH §1.2d) — `co_tieng_viet` chặn CẢ từ khoá đầu vào LẪN
    tiêu đề từng bài Bing trả về (test thật 13/09/2026: query "Anthropic" vẫn
    lẫn cafebiz.vn/thanhnien.vn nếu chỉ chặn từ khoá); tiếng Trung không bị
    chặn ở đây (không có dấu tiếng Việt để nhận nhầm)."""
    if co_tieng_viet(tu_khoa):
        print("[nguon_bai] TU CHOI bao_ve_tu_khoa bang tieng Viet", file=sys.stderr)
        return []
    import email.utils as eu
    import time as _t
    can = tu_cung_tin(tu_khoa)
    if not can:
        return []
    moc = (_t.time() - ngay * 86400) if ngay is not None else 0
    its, co_link = [], set()
    for q in _truy_van_bing(tu_khoa) or [tu_khoa]:
        try:
            r = _tai(BING_RSS.format(q=up.quote(q)), 20)
            for it in ET.fromstring(r.content).findall(".//item"):
                k = it.findtext("link") or ""
                if k and k not in co_link:
                    co_link.add(k)
                    its.append(it)
        except Exception as e:                               # noqa: BLE001
            print(f"[nguon_bai] bing tu khoa hong: {type(e).__name__}", file=sys.stderr)
        if len(its) >= so * 3:
            break
    ra, thay = [], set()
    for it in its[: so * 6]:
        link = it.findtext("link") or ""
        td = it.findtext("title") or ""
        # Chi doi bai NOI VE tu khoa (het cac tu cua chinh no co mat), khong
        # doi CUNG MOT su kien nhu `bao_khac_bing` (`cung_tin`/`goc & ...`).
        if not link or not can <= tu_cung_tin(td):
            continue
        # `co_tieng_viet(tu_khoa)` o dau ham chi chan TU KHOA dau vao (ten
        # hang luon la tieng Anh) — KHONG chan duoc bao TIENG VIET Bing tra ve
        # (vd "Anthropic" van khop tieu de mot bai cafebiz.vn/thanhnien.vn).
        # Do that 13/09/2026: query "Anthropic" tra ca cafebiz.vn, vietnam.vn,
        # trithucvn2.net, thanhnien.vn lan vao ket qua. LUAT_ANH §1.2d doi
        # "chi Anh hoac Trung" cho ca NGUON, khong chi cau hoi — phai loc lai
        # o day, tren chinh tieu de bai tra ve.
        if co_tieng_viet(td):
            continue
        try:
            ts = eu.parsedate_to_datetime(it.findtext("pubDate") or "").timestamp()
            if ts < moc:
                continue
        except Exception:                                    # noqa: BLE001
            pass
        try:
            if not quet_chung.url_an_toan(link):
                continue
            rr = httpx.head(link, headers=HDR, timeout=12, follow_redirects=True)
            u = str(rr.url)
            if rr.status_code != 200 or not quet_chung.url_an_toan(u):
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
    its, co_link_gn = [], set()
    if ten:
        # THU CA CAU NGAN, khong chi headline day du (Ong Chu 13/09/2026: do
        # that Moonshot/Kimi K3 — headline day du cua chinh TechCrunch chi keo
        # ve mot vai mien; cau ngan "Kimi Moonshot AI"/"Kimi maker Moonshot AI"
        # (_truy_van_bing sinh ra, von chi dung cho Bing) keo ve them SCMP/
        # Bloomberg/CNBC/Reuters ma headline day du BO SOT — cung mot dang loi
        # da biet o Bing (_truy_van_bing doc noi "truy van day du -> 1 bai"),
        # chua bao gio ap sang Google News. Dung theo THU TU cua ham (dai ->
        # ngan trong tung bo), dung som khi da du mien de khong hoi qua nhieu.
        for q in [ten] + _truy_van_bing(ten):
            try:
                for it in ET.fromstring(_tai(GNEWS.format(q=up.quote(q)), 25).content
                                        ).findall(".//item"):
                    k = it.findtext("link") or ""
                    if k and k not in co_link_gn:
                        co_link_gn.add(k)
                        its.append(it)
            except Exception as e:                           # noqa: BLE001
                print(f"[nguon_bai] google news hong ({q!r}): {type(e).__name__}", file=sys.stderr)
            if len({it.find('source').get('url') for it in its
                    if it.find('source') is not None}) >= so * 3:
                break

    mien = []
    for it in its[: so * 6]:
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
    with cf.ThreadPoolExecutor(max_workers=env_load.so_luong(6)) as ex:
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
