#!/usr/bin/env python3
"""Tim NGUON cho mot tin — buoc research, thuoc khau cua Finn.

Vi sao dat o day: viec di tim nguon la RESEARCH, do la nghe cua Finn. Truoc day
Vai dung anh tu tim nguon de lay anh, vai viet lai tu tim de lay chu — hai lan tra
cuu cho cung mot tin, va co the ra hai bo bai khac nhau, khien bai viet noi mot
dang con tam anh cho thay mot dang khac.

Nay Finn lam mot lan ngay sau khi Ong Chu chon tin, ghi ra
state/<brand>/article_source_<draft_id>.json, roi ca vai dung anh lan vai viet cung doc tep do.

Cach tim: Google News KHONG cho URL bai (link cua no la duong chuyen huong chay
bang JS, chuoi CBMi khong phai base64 cua URL, con DuckDuckGo tra 202 chan bot).
Nhung Google News CO cho ten mien toa soan o <source url>. Nen di duong vong:
ten mien -> RSS cua chinh toa soan -> khop tieu de -> ra link bai that. Chua du
bao thi hoi Bing, roi moi mo Chromium giai ma link Google News cua cac bai cung
tin (LOW-275: nhieu toa soan khong co RSS doan duoc, Bing lai tra rong).

Dung:
    venv/bin/python article_sources.py --tieu-de "..." --link "..." --out state/<brand>/article_source_x.json

Ma thoat: 0 = co bao khac; EXIT_ONLY_ORIGINAL (3) = tep van ghi du nhung chi co
bai goc; khac = loi that (1 la ma Python tu tra khi co exception).
"""
import argparse
import concurrent.futures as cf
import json
import os
import re
import sys
import threading
import time
import urllib.parse as up
import urllib.request
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_common                                            # noqa: E402
import env_load                                              # noqa: E402
import safe_xml                                              # noqa: E402

UA = scan_common.UA                     # mot ban duy nhat, xem scan_common
HDR = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
GNEWS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
COUNT_SOURCE = 4
# LOW-275 (19/09/2026): truoc day "chi tim duoc bai goc" tra ma 1 — trung ma Python
# tu tra khi co exception, nen approve coi 5/9 tin la "loi" va BO LUON buoc doi
# link Google News sang link that. Ma rieng de nguoi goi tach hai truong hop.
EXIT_ONLY_ORIGINAL = 3
# LOW-277 (19/09/2026): vong doan RSS theo ten mien trong `find()` tung ton ~80s cho
# mot tin — mot mien treo ca 5 duong x 15s, va `with ThreadPoolExecutor` doi no du
# ket qua da co tu giay 3-6. Do 26 tin that: bai khop qua RSS den muon nhat o giay
# 13,9 tinh tu dau `find()`. Tran ca vong + timeout moi lan tai:
FEED_BUDGET_SECONDS = 15
FEED_TIMEOUT_SECONDS = 10

# ---- tep article_source_<id>.json (LOW-238; bang docs/tu_dien_ten/article_source_keys_v2.json)
#   {"title", "title_en", "source_url", "gnews_url"?, "pages": [{"url", "kind", "title"?, "outlet_url"?}]}
# `kind` luu MA English; chu hien thi tieng Viet (log) in qua PAGE_KIND_LABELS — dung
# chu da in truoc LOW-238. "table"/"price" chi co trong tep viet tay, code khong sinh.
PAGE_KIND_LABELS = {
    "article": "gốc",
    "other_outlet": "báo",
    "announcement": "công bố",
    "table": "bảng",
    "price": "giá",
}


def page_kind_label(code: str) -> str:
    """Chu tieng Viet cua mot `pages[].kind`; ma la in nguyen."""
    return PAGE_KIND_LABELS.get(code, code)

FROM_EMPTY = scan_common.FROM_EMPTY           # mot ban duy nhat, xem scan_common
_tu = scan_common.from_distinctive

# ---- "CUNG TIN" (LOW-33, 12/09/2026) ------------------------------------------
# The Ethan "DeepSeek-V4.1-Flash tha trong so" ra anh con vit-robot: `title_en`
# la <title> thô cua trang HuggingFace "deepseek-ai/DeepSeek-V4.1-Flash · Hugging
# Face" — hau to " · Hugging Face" khong bi boc (regex chi biet | - – —), hai chu
# "Hugging"+"Face" tu no da du nguong "chung >= 2 tu", nen Bing tra bai
# "Hugging Face robot duck is already a hit" va no thanh "bao khac cung tin".
# Ba lop sua: boc hau to voi ca `·`/`»`; ten nen tang (HuggingFace, GitHub,
# arXiv...) KHONG duoc tinh la tu dac trung; va moi cho quyet "cung tin" di qua
# MOT ham `same_story` — ke ca vong chup trang nguon, truoc day mien kiem.
_HAU_TO_SITE = re.compile(r"\s+[|\-–—·»]\s+[^|\-–—·»]{2,40}$|\s+::\s+[^:]{2,40}$")
_TU_NEN = {"hugging", "face", "huggingface", "github", "arxiv", "reddit", "medium",
           "substack", "youtube", "twitter", "linkedin", "wikipedia", "hacker", "news"}


def strip_site_suffix(t: str) -> str:
    """"Tieu de · Ten site" / "Tieu de | Ten bao" -> "Tieu de"."""
    return _HAU_TO_SITE.sub("", (t or "").strip())


def story_tokens(t: str) -> set:
    """Tu dac trung DUNG DE SO "cung tin": bo hau to site va bo ten nen tang."""
    return _tu(strip_site_suffix(t)) - _TU_NEN


# ---- "CUNG TIN" = CUNG SU KIEN (LOW-276, 19/09/2026) ---------------------------
# Chung >= 2 tu dac trung khong du: do 180 cap tieu de that (421 cap "bao khac"
# tung duoc nhan), luat cu nhan nham 34/38 cap KHAC tin — cung chu the, khac su
# kien ("Claude Fable 5.1 giai mat ma" vs "Claude Fable 5.1 len dau bang xep
# hang"; tin luu tru dien biggo vs bai Crusoe goi von vi chung "data centers").
# Moi luat chi dem/cham do hiem cua tu deu that bai (tot nhat van nhan nham
# 27/38), vi cap sai va cap dung chung tu hiem nhu nhau. Nen: code loai/nhan
# ca CHAC, chi ca lung chung (chung 2-3 tu) hoi LLM — MOT lan cho ca danh sach.
# Bo mau 180 cap: tests/golden/same_story_golden.json.
SAME_STORY_SURE = 4                          # chung >= 4 tu: chac cung tin, khong hoi
SAME_STORY_MODEL = env_load.SAME_STORY_MODEL  # cung model Vera gom tin (scan_business)
SAME_STORY_TIMEOUT = 40


def _same_event_prompt(title: str, candidates: list) -> str:
    lines = "\n".join(f"{i}. {c[:200]}" for i, c in enumerate(candidates, 1))
    return ("You check which candidate headlines cover the SAME news as an original headline.\n\n"
            f"Original: {title[:200]}\n\nCandidates:\n{lines}\n\n"
            "A candidate MATCHES if it is about the same news as the original: the same announcement, "
            "launch, release, deal, funding round, incident, report or finding — even if it covers it "
            "from another angle (analysis, reaction, benchmark or explainer of that same release, "
            "slightly different figures). The original may be a terse label such as a model name.\n"
            "A candidate does NOT match if it is about a different event that merely involves the "
            "same company, product, person or topic (another launch, another deal, an older story, "
            "an unrelated feature). Headlines may be in any language.\n"
            "Reply with ONLY a JSON array of the matching candidate numbers, e.g. [1, 3] or [].")


def _ask_same_event(title: str, candidates: list) -> set | None:
    """Chi so (tu 0) cac ung vien CUNG SU KIEN theo LLM; None khi LLM hong (goi
    router loi, thieu khoa, tra loi khong doc duoc) — nguoi goi tu quyet lui."""
    print(f"[nguon_bai] same_story: hoi llm {len(candidates)} ca lung chung", file=sys.stderr)
    env_load.load()
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("[nguon_bai] same_story: thieu OPENAI_API_KEY -> chi dung luat tu", file=sys.stderr)
        return None
    body = {"model": SAME_STORY_MODEL, "thinking": {"type": "disabled"}, "max_tokens": 300,
            "stream": False, "temperature": 0,
            "messages": [{"role": "user", "content": _same_event_prompt(title, candidates)}]}
    try:
        req = urllib.request.Request(env_load.ROUTER_URL, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json",
                                              "Authorization": "Bearer " + key})
        raw = urllib.request.urlopen(req, timeout=SAME_STORY_TIMEOUT).read().decode().strip()
        if raw.startswith("data:"):
            raw = raw.split("data: [DONE]")[0].strip()[5:].strip()
        text = json.loads(raw)["choices"][0]["message"]["content"]
    except Exception as e:                                   # noqa: BLE001
        ma = getattr(e, "code", "") or ""
        print(f"[nguon_bai] same_story: TAT: llm loi {type(e).__name__}"
              f"{f' {ma}' if ma else ''} tren model {SAME_STORY_MODEL!r} "
              "-> chi dung luat tu", file=sys.stderr)
        return None
    found = re.search(r"\[[\d,\s]*\]", text or "")
    if not found:
        print(f"[nguon_bai] same_story: llm tra loi khong doc duoc {text[:80]!r} -> chi dung luat tu",
              file=sys.stderr)
        return None
    return {int(n) - 1 for n in re.findall(r"\d+", found.group(0)) if 1 <= int(n) <= len(candidates)}


def same_story_many(title: str, candidates: list) -> list:
    """[bool] cho tung ung vien: co bao CUNG SU KIEN voi `title` khong.

    Chung < 2 tu dac trung -> khong; >= SAME_STORY_SURE -> co; con lai (lung
    chung) gom lai hoi LLM mot lan. LLM hong thi lung chung tinh la co — dung
    luat cu, khong de mat nguon vi mot lan goi hong."""
    story = story_tokens(title)
    shared = [len(story & story_tokens(c)) for c in candidates]
    verdict = [n >= SAME_STORY_SURE for n in shared]
    borderline = [i for i, n in enumerate(shared) if 2 <= n < SAME_STORY_SURE]
    if borderline:
        picked = _ask_same_event(title, [candidates[i] for i in borderline])
        for k, i in enumerate(borderline):
            verdict[i] = True if picked is None else k in picked
        if picked is not None:
            print(f"[nguon_bai] same_story: llm nhan {len(picked)}/{len(borderline)} ca lung chung "
                  f"cho {title[:60]!r}", file=sys.stderr)
    return verdict


def same_story(tieu_de_goc: str, tieu_de_khac: str) -> bool:
    """Hai tieu de co noi ve CUNG mot su kien khong — xem `same_story_many`."""
    return same_story_many(tieu_de_goc, [tieu_de_khac])[0]


def _download(url: str, timeout=20):
    return httpx.get(url, headers=HDR, timeout=timeout, follow_redirects=True)


GNEWS_ARTICLE = "news.google.com/rss/articles"


def resolve_code_gnews(url: str, timeout: int = 30, phien=None) -> str | None:
    """Link Google News (news.google.com/rss/articles/CBMi...) -> URL bai THAT.

    Tin cua Vera (scan_business doc RSS Google News) luon mang link dang nay.
    Fetch tinh chi ra mot trang chuyen huong chay bang JS, nen article_images/material
    doc ra RONG — Dre/Miles phai tu web_search lai tin (do that 04/09/2026:
    web_search 11 lan, curl 38 lan trong 4 task carousel dcgr). Giai ma MOT LAN
    o day, ngay luc Ong Chu chon tin, roi moi vai sau dung link that.

    Thu nhe truoc (trang chuyen huong doi khi co san href), khong duoc thi mo
    bang chromium (playwright) va doi URL doi. Khong giai duoc thi tra None —
    nguoi goi giu link cu."""
    if GNEWS_ARTICLE not in (url or ""):
        return url
    try:
        import html as _html
        r = _download(url, 20)
        m = (re.search(r'data-n-au="([^"]+)"', r.text)
             or re.search(r'<a[^>]+href="(https?://(?!news\.google)[^"]+)"', r.text))
        if m:
            return _html.unescape(m.group(1))
    except Exception:                                        # noqa: BLE001
        pass
    try:
        import time as _t
        from browser_session import session_or_new
        # `phien`: dung chung tien trinh Chromium voi cac buoc khac cua cung mot
        # bai (audit B4). Khong truyen thi tu mo, tu dong — y nhu truoc.
        with session_or_new(phien) as ph:
            with ph.page(user_agent=UA.replace("compatible; ", "")) as page:
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


# `setlang=en` (LOW-264 bo sung, do that 20/09/2026 tu may chu IP Viet Nam): khong co
# tham so ngon ngu thi Bing dinh vi theo IP va tra tieu de TIENG VIET cho tu khoa
# ngan (8 hang x 85 muc: 0/85 tieu de tieng Anh; them setlang=en: 87/87). Moi
# `has_vietnamese` phia duoi lai loc het -> `report_about_keyword("Anthropic")` rong
# 0/12, "OpenAI" 0/7 mot cach im lang. `setmkt=en-US` tra it muc hon (2 muc cho
# Anthropic/OpenAI/Samsung) nen khong dung.
BING_RSS = "https://www.bing.com/news/search?q={q}&format=rss&setlang=en"
DROP_DOMAIN = ("msn.com", "seekingalpha.com", "news.google.com", "bing.com", "yahoo.com")


FROM_EMPTY_QUERY = {"the", "a", "an", "of", "in", "on", "to", "for", "and", "or",
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


def has_vietnamese(t: str) -> bool:
    return bool(_DAU_VIET.search(t or ""))


# Trang chan bot (Cloudflare/Akamai) tra 403 kem trang "Just a moment...", hoac
# title chi con la ten mien tran. Nhan dien de KHONG dem lam tieu de that (bai
# Economist 08/09/2026: httpx lan Playwright/Chromium that deu bi chan giong nhau).
_CHAN_BOT = re.compile(r"just a moment|attention required|checking your browser|"
                       r"access denied|are you (a )?human|enable javascript and cookies",
                       re.I)

RSS_GUESS = ("/rss.xml", "/feed", "/feed.xml", "/feed/", "/rss", "/index.xml")


def _title_rss(url: str) -> str:
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
    ung_vien = [goc + d for d in RSS_GUESS]
    if doan_dau:
        ung_vien = [f"{goc}/{doan_dau}/rss.xml", f"{goc}/{doan_dau}/feed"] + ung_vien
    dich = url.split("?")[0].rstrip("/")
    for feed in ung_vien[:6]:
        try:
            r = _download(feed, 12)
            if r.status_code != 200 or b"<item" not in r.content[:400_000]:
                continue
            for it in safe_xml.fromstring(r.content).findall(".//item"):
                lk = (it.findtext("link") or "").split("?")[0].rstrip("/")
                if lk != dich:
                    continue
                t = (it.findtext("title") or "").strip()
                if t and not has_vietnamese(t):
                    print(f"[nguon_bai] tieu de tim = RSS toa soan ({feed}): {t[:90]}",
                          file=sys.stderr)
                    return t
        except Exception:                                    # noqa: BLE001
            continue
    return ""


def _gnews_article_id(url: str) -> str:
    """Ma bai trong link Google News (doan cuoi duong dan, bo `?oc=5`)."""
    return up.urlsplit(url or "").path.rstrip("/").rsplit("/", 1)[-1]


def _title_gnews_id(gnews_url: str, url: str) -> str:
    """Headline tieng Anh cua CHINH bai nay theo Google News, khop DUNG ma bai.

    LOW-275 (19/09/2026): bai finance.biggo.com tra 403 cho ca httpx lan Chromium,
    khong RSS, slug la UUID — khong con cho nao cho tieu de tieng Anh, nen roi ve
    ten rieng roi rac cua tieu de Viet (dang khop nham LOW-169). Nhung tin cua
    Vera DEN TU Google News: hoi Google News bang doan duong dan cua URL that
    (UUID, slug) ra lai dung bai do, va ma bai (CBMi...) trung y het link Vera
    dua -> tieu de chac chan cua dung bai, khong phai doan. Do that 4/4 tin
    link Google News ngay 19/09 (biggo, ET Enterprise AI, The Information, AIM)."""
    if GNEWS_ARTICLE not in (gnews_url or ""):
        return ""
    article_id = _gnews_article_id(gnews_url)
    segments = [s for s in up.urlsplit(url or "").path.split("/") if len(s) >= 6]
    for query in list(reversed(segments))[:3]:
        try:
            items = safe_xml.fromstring(_download(GNEWS.format(q=up.quote(query)), 20).content
                                        ).findall(".//item")
        except Exception as e:                               # noqa: BLE001
            print(f"[nguon_bai] google news (ma bai) hong: {type(e).__name__}", file=sys.stderr)
            continue
        for item in items:
            if _gnews_article_id(item.findtext("link") or "") != article_id:
                continue
            title = strip_site_suffix(item.findtext("title") or "")
            if title and not has_vietnamese(title):
                print(f"[nguon_bai] tieu de tim = Google News khop ma bai: {title[:90]}",
                      file=sys.stderr)
                return title
    return ""


def _title_page(url: str, gnews_url: str = "") -> str:
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
    chan giong nhau). Tin den tu Google News (`gnews_url`) thi hoi Google News
    khop ma bai truoc khi suy tu slug (LOW-275)."""
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
                t = strip_site_suffix(t)                    # bo " | Ten bao", " · Hugging Face"
                if t and len(t.split()) < 4:
                    print(f"[nguon_bai] bo tieu de qua ngan (co the la ten site, chua hydrate): {t!r}",
                          file=sys.stderr)
                elif t and len(t) >= 8 and not has_vietnamese(t) and not _CHAN_BOT.search(t):
                    print(f"[nguon_bai] tieu de tim = og:title bai goc: {t[:90]}", file=sys.stderr)
                    return t
    except Exception:                                        # noqa: BLE001
        pass
    return _title_rss(url) or _title_gnews_id(gnews_url, url) or _title_slug(url)


_HEX_ID = re.compile(r"[0-9a-f]*[0-9][0-9a-f]*", re.I)


def _title_slug(url: str) -> str:
    """Suy tieu de tieng Anh THAT tu duong dan URL khi ca og:title va RSS deu
    khong lay duoc (trang chan bot, khong co feed cong khai). Da so CMS tin
    tuc (WordPress...) dat slug = chinh headline noi bang gach ngang; tach
    gach ngang ra la ca cau tieng Anh day du va dac trung, KHONG can Google
    News doi chieu — DUNG va AN TOAN HON nhieu so voi ten rieng roi rac cua
    `_name_own_no_mark` (Malaysia 14/09/2026: og:title bi Cloudflare chan,
    RSS khong khop, roi ve "Malaysia 385" tu tieu de Viet khop nham bai xe
    dien iCaur 03 vi ca hai co du 2 tu "malaysia" + "385"; slug URL cua chinh
    bai goc lai ra dung ca cau "malaysia records rm385 7 billion in data
    centre investments...", vua tieng Anh vua dac trung, khong lam mat nguon
    tim kiem nhu tra ve rong).

    Manh hex co chu so (UUID/hash: `1050d70e`, `f675`, `45be`) KHONG tinh la tu
    (LOW-275: slug UUID cua finance.biggo.com tung thanh "tieu de" tim kiem
    `1050d70e f675 45be 8384 79934321d06f` vi 4/5 manh co chu cai a-f)."""
    try:
        path = up.urlsplit(url).path
    except Exception:                                        # noqa: BLE001
        return ""
    for doan in reversed([d for d in path.split("/") if d]):
        doan = re.sub(r"\.(html?|php|aspx?)$", "", doan, flags=re.I)
        tu = [w for w in doan.split("-") if w]
        if sum(1 for w in tu if re.search(r"[a-zA-Z]", w) and not _HEX_ID.fullmatch(w)) < 4:
            continue                                          # doan qua ngan/toan so/UUID, khong phai slug
        t = " ".join(tu)
        if not has_vietnamese(t):
            print(f"[nguon_bai] tieu de tim = slug URL bai goc: {t[:90]}", file=sys.stderr)
            return t
    return ""


def _name_own_no_mark(tieu_de_viet: str) -> str:
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
        if not w or has_vietnamese(w) or w.lower() in _TU_VIET_KHONG_DAU or len(w) < 2:
            continue
        if w[:1].isupper() or any(c.isdigit() for c in w) or w.isupper():
            ra.append(w)
    return " ".join(ra[:8])


def title_find(tieu_de: str, link: str, gnews_url: str = "") -> str:
    """Tieu de DUNG DE TIM KIEM (tieng Anh). Rong = khong duoc tim gi ca.

    Uu tien HEADLINE THAT cua toa soan (og:title hoac RSS) hon tieu de dau vao,
    ke ca khi tieu de dau vao da la tieng Anh: no co the la DEK/subtitle hay
    tieu de HN paraphrase, cau chu khac voi cach bao khac dua lai tin nen tim
    ra 0 ket qua. Vi du that (Economist 08/09/2026): dek "Initial effects of AI
    technology on employment look positive" -> Google News 0 bai; headline that
    "The jobs apocalypse is postponed. An AI jobs boom is here" -> ra New Yorker."""
    # Moi nhanh cua _title_page tu in nguon cua no (og:title/RSS/ma bai/slug) —
    # truoc day dong nay in "og:title/RSS" ca khi tieu de la slug UUID (LOW-275).
    en = _title_page(link, gnews_url) if link else ""
    if en:
        return en
    if tieu_de and not has_vietnamese(tieu_de):
        return tieu_de
    en = _name_own_no_mark(tieu_de)
    if len(en.split()) >= 2:
        # Bac 3: hoi Google News bang ten rieng, lay HEADLINE tieng Anh cua bai
        # dau (chung >= 2 tu voi ten rieng) — cau day du keo ve nhieu bao hon
        # hin ten rieng roi rac (Nvidia 05/09: ten rieng -> 3 trang, headline -> 40).
        try:
            its = safe_xml.fromstring(_download(GNEWS.format(q=up.quote(en)), 20).content).findall(".//item")
            goc = _tu(en)
            for it in its[:5]:
                hd = re.sub(r"\s+-\s+[^-]{2,60}$", "", it.findtext("title") or "").strip()
                if hd and not has_vietnamese(hd) and len(goc & _tu(hd)) >= 2:
                    print(f"[nguon_bai] tieu de tim = headline Google News: {hd[:90]}", file=sys.stderr)
                    return hd
        except Exception as e:                               # noqa: BLE001
            print(f"[nguon_bai] google news (headline) hong: {type(e).__name__}", file=sys.stderr)
        print(f"[nguon_bai] tieu de tim = ten rieng khong dau: {en}", file=sys.stderr)
        return en
    print("[nguon_bai] KHONG co tieu de tieng Anh -> khong tim bao khac (luat: khong tim bang tieng Viet)",
          file=sys.stderr)
    return ""


def _query_bing(tieu_de: str) -> list:
    if has_vietnamese(tieu_de):
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
        tu = [w for w in tt.split() if w.lower() not in FROM_EMPTY_QUERY and len(w) > 1]
        rieng = [w for w in tu if w[:1].isupper() or any(c.isdigit() for c in w)]
        for ds in (tu[:5], tu[:4], tu[:3], rieng[:4], rieng[:3],
                   ([rieng[0], "AI"] if rieng and "AI" in tu else [])):
            q = " ".join(ds)
            if q and q not in ra:
                ra.append(q)
    return ra


def other_outlets_bing(tieu_de: str, so: int = 4, bo_mien: tuple = (), ngay: int = 10) -> list:
    if has_vietnamese(tieu_de):
        print("[nguon_bai] TU CHOI other_outlets_bing bang tieng Viet", file=sys.stderr)
        return []
    """Bao khac dua cung tin qua Bing News RSS. Khac Google News, link cua Bing
    la chuyen huong HTTP thuong (apiclick.aspx) -> di theo redirect la ra URL
    bai that, khong can browser. ~1s/link.

    Loc: bai trong `ngay` ngay gan day, tieu de phai chung >= 2 tu dac trung voi
    tieu de goc (truy van ngan de keo ve ca tin cu/khong lien quan). Bo trang
    tong hop (msn, yahoo), trang chan bot (seekingalpha) va `bo_mien`.
    Tra ve [{url, kind: "other_outlet", title, outlet_url}] (muc `pages[]`, LOW-238)."""
    import email.utils as eu
    import time as _t
    tieu_de = strip_site_suffix(tieu_de)      # LOW-33: " · Hugging Face" khong vao truy van
    moc = _t.time() - ngay * 86400
    its, co_link = [], set()
    for q in _query_bing(tieu_de):
        try:
            r = _download(BING_RSS.format(q=up.quote(q)), 20)
            for it in safe_xml.fromstring(r.content).findall(".//item"):
                k = it.findtext("link") or ""
                if k and k not in co_link:
                    co_link.add(k)
                    its.append(it)
        except Exception as e:                               # noqa: BLE001
            print(f"[nguon_bai] bing rss hong: {type(e).__name__}", file=sys.stderr)
        if len(its) >= so * 3:
            break
    recent = []
    for it in its[: so * 6]:
        link = it.findtext("link") or ""
        if not link:
            continue
        try:
            ts = eu.parsedate_to_datetime(it.findtext("pubDate") or "").timestamp()
            if ts < moc:
                continue
        except Exception:                                    # noqa: BLE001
            pass
        recent.append((link, it.findtext("title") or ""))
    # Loc cung su kien MOT lan cho ca danh sach (LOW-276) — ca lung chung hoi LLM mot lan.
    verdicts = same_story_many(tieu_de, [td for _link, td in recent])
    ra, thay = [], set()
    for (link, td), ok in zip(recent, verdicts):
        if not ok:
            continue
        try:
            if not scan_common.url_hide_whole(link):
                continue
            rr = httpx.head(link, headers=HDR, timeout=12, follow_redirects=True)
            u = str(rr.url)
            # `u` la dia chi SAU chuyen huong va duoc dung lam nguon that cho
            # bai — mot ket qua tim kiem 302 ve 127.0.0.1 khong duoc di tiep.
            if rr.status_code != 200 or not scan_common.url_hide_whole(u):
                continue
        except Exception:                                    # noqa: BLE001
            continue
        m = re.match(r"https?://([^/]+)", u)
        mien = (m.group(1) if m else "").replace("www.", "")
        if not mien or mien in thay or any(b in mien for b in DROP_DOMAIN + tuple(bo_mien)):
            continue
        thay.add(mien)
        ra.append({"url": u, "kind": "other_outlet", "title": td[:160], "outlet_url": "https://" + mien})
        if len(ra) >= so:
            break
    return ra


def report_about_keyword(tu_khoa: str, so: int = 6, bo_mien: tuple = (), ngay: int | None = None) -> list:
    """Bao THẬT về một TỪ KHOÁ (tên hãng/sản phẩm) qua Bing News RSS — KHÁC
    `other_outlets_bing`: không đòi "cùng một sự kiện" với một tiêu đề gốc, VÀ
    KHÔNG GIỚI HẠN THỜI GIAN (Ông Chủ 13/09/2026, chốt nguyên tắc nguồn ở
    IMAGE_RULES.md §1.2d: *"được tìm không giới hạn thời gian, sự kiện. miễn là
    trong article có nhắc tới tên brand... ngoài nguyên tắc này, không có bất
    kỳ một cấm đoán nào về nguồn ảnh"*). Trước đó (LOW-45, 13/09 sáng) còn giới
    hạn 20 ngày và chỉ coi là phương án khi Commons/Wikidata RỖNG — hai giới
    hạn đó đã bỏ theo đúng luật mới; `ngay` giữ lại làm tham số CHO PHÉP hẹp
    lại nếu một lần gọi cụ thể cần, mặc định là KHÔNG giới hạn.

    Lọc nhẹ hơn `other_outlets_bing`: chỉ đòi tiêu đề bài chứa lại chính TỪ KHOÁ
    (không đòi khớp với MỘT sự kiện cụ thể nào) — vì mục đích là ảnh MINH HOẠ
    hãng/sản phẩm (như ảnh khái niệm), không phải bằng chứng của một tin riêng.
    Cùng hạ tầng với `other_outlets_bing`: giải chuyển hướng HTTP, chặn SSRF
    (`scan_common.url_hide_whole`), bỏ trang tổng hợp/`bo_mien`. Ngôn ngữ: chỉ Anh
    hoặc Trung (IMAGE_RULES §1.2d) — `has_vietnamese` chặn CẢ từ khoá đầu vào LẪN
    tiêu đề từng bài Bing trả về (test thật 13/09/2026: query "Anthropic" vẫn
    lẫn cafebiz.vn/thanhnien.vn nếu chỉ chặn từ khoá); tiếng Trung không bị
    chặn ở đây (không có dấu tiếng Việt để nhận nhầm)."""
    if has_vietnamese(tu_khoa):
        print("[nguon_bai] TU CHOI report_about_keyword bang tieng Viet", file=sys.stderr)
        return []
    import email.utils as eu
    import time as _t
    can = story_tokens(tu_khoa)
    if not can:
        return []
    moc = (_t.time() - ngay * 86400) if ngay is not None else 0
    its, co_link = [], set()
    for q in _query_bing(tu_khoa) or [tu_khoa]:
        try:
            r = _download(BING_RSS.format(q=up.quote(q)), 20)
            for it in safe_xml.fromstring(r.content).findall(".//item"):
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
        # doi CUNG MOT su kien nhu `other_outlets_bing` (`same_story`/`goc & ...`).
        if not link or not can <= story_tokens(td):
            continue
        # `has_vietnamese(tu_khoa)` o dau ham chi chan TU KHOA dau vao (ten
        # hang luon la tieng Anh) — KHONG chan duoc bao TIENG VIET Bing tra ve
        # (vd "Anthropic" van khop tieu de mot bai cafebiz.vn/thanhnien.vn).
        # Do that 13/09/2026: query "Anthropic" tra ca cafebiz.vn, vietnam.vn,
        # trithucvn2.net, thanhnien.vn lan vao ket qua. IMAGE_RULES §1.2d doi
        # "chi Anh hoac Trung" cho ca NGUON, khong chi cau hoi — phai loc lai
        # o day, tren chinh tieu de bai tra ve.
        if has_vietnamese(td):
            continue
        try:
            ts = eu.parsedate_to_datetime(it.findtext("pubDate") or "").timestamp()
            if ts < moc:
                continue
        except Exception:                                    # noqa: BLE001
            pass
        try:
            if not scan_common.url_hide_whole(link):
                continue
            rr = httpx.head(link, headers=HDR, timeout=12, follow_redirects=True)
            u = str(rr.url)
            if rr.status_code != 200 or not scan_common.url_hide_whole(u):
                continue
        except Exception:                                    # noqa: BLE001
            continue
        m = re.match(r"https?://([^/]+)", u)
        mien = (m.group(1) if m else "").replace("www.", "")
        if not mien or mien in thay or any(b in mien for b in DROP_DOMAIN + tuple(bo_mien)):
            continue
        thay.add(mien)
        ra.append({"url": u, "kind": "other_outlet", "title": td[:160], "outlet_url": "https://" + mien})
        if len(ra) >= so:
            break
    return ra


def _domain(url: str) -> str:
    return re.sub(r"^https?://(www\.)?", "", url or "").split("/")[0].lower()


# Bu bao qua Google News chi khi con it hon chung nay bao khac: moi link phai mo
# Chromium giai ma (~4s), khong dang ton khi RSS/Bing da ra du.
MIN_OTHER_OUTLETS = 2


def other_outlets_gnews(title_en: str, items: list, count: int = 3, skip_domains: tuple = (),
                        days: int = 10, budget_seconds: int = 30) -> list:
    """Bao khac cung tin lay tu CHINH cac muc Google News `find()` da tai ve.

    LOW-275 (19/09/2026): tin "Anthropic details practical metrics..." Google
    News tra san CNBC, Tekedia, blockchain.news cung dua — nhung `find()` chi
    lay TEN MIEN roi doan RSS (/feed, /rss...), CNBC/Tekedia khong co feed doan
    duoc, Bing lai tra rong -> chi con bai goc. Link Google News la chuyen huong
    JS (xem `resolve_code_gnews`), nen mo Chromium giai ma — dat, nen chi lam
    cho vai bai cung tin nhat, trong `budget_seconds` giay.

    Loc giong `other_outlets_bing`: `same_story`, dang trong `days` ngay, moi
    mien mot bai, bo `DROP_DOMAIN` + `skip_domains`, chan SSRF tren URL sau giai
    ma. Xep bai chung nhieu tu nhat len truoc. Do that 19/09: giai ma ~4-5s/link,
    link chan bot treo toi het timeout — nen 10s/link va tran `budget_seconds`
    de ca buoc research khong cham 180s cua approve (buoc doan RSS truoc do da
    co the ton ~80s)."""
    import email.utils as eu
    import time as _t
    story = story_tokens(title_en)
    cutoff = _t.time() - days * 86400
    skip = DROP_DOMAIN + tuple(skip_domains)
    pool = []
    for item in items:
        title = strip_site_suffix(item.findtext("title") or "")
        if len(story & story_tokens(title)) < 2 or has_vietnamese(title):
            continue                                          # chac khong cung tin: khoi dua LLM
        try:
            if eu.parsedate_to_datetime(item.findtext("pubDate") or "").timestamp() < cutoff:
                continue
        except Exception:                                    # noqa: BLE001
            continue                                          # khong ngay -> khong biet cung dot tin
        source = item.find("source")
        outlet = ((source.get("url") if source is not None else "") or "").rstrip("/")
        domain = _domain(outlet)
        if not domain or any(s in domain for s in skip):
            continue
        pool.append((item.findtext("link") or "", title, outlet, domain))
    # Loc cung su kien truoc, bo trung mien sau: mot bai khac tin cua mien X dung
    # truoc khong duoc chan bai cung tin cua chinh mien X (LOW-276).
    candidates, seen_domains = [], set()
    for (gnews_link, title, outlet, domain), ok in zip(
            pool, same_story_many(title_en, [p[1] for p in pool])):
        if not ok or domain in seen_domains:
            continue
        seen_domains.add(domain)
        candidates.append((len(story & story_tokens(title)), gnews_link, title, outlet))
    candidates.sort(key=lambda c: -c[0])
    pages = []
    if not candidates:
        return pages
    from browser_session import session_or_new
    deadline = _t.time() + budget_seconds
    with session_or_new(None) as session:
        for _common, gnews_link, title, outlet in candidates[: count + 2]:
            if _t.time() > deadline:
                print(f"[nguon_bai] google news: het {budget_seconds}s giai ma, dung o {len(pages)} bao",
                      file=sys.stderr)
                break
            real = resolve_code_gnews(gnews_link, timeout=10, phien=session)
            if (not real or not scan_common.url_hide_whole(real)
                    or any(s in _domain(real) for s in skip)):
                continue
            pages.append({"url": real, "kind": "other_outlet", "title": title[:160],
                          "outlet_url": outlet})
            if len(pages) >= count:
                break
    return pages


def _gnews_item(ten: str, so: int) -> list:
    """Cac <item> Google News cho mot tieu de tieng Anh, KHONG trung link.

    THU CA CAU NGAN, khong chi headline day du (Ong Chu 13/09/2026: do that
    Moonshot/Kimi K3 — headline day du cua chinh TechCrunch chi keo ve mot vai
    mien; cau ngan "Kimi Moonshot AI"/"Kimi maker Moonshot AI" (`_query_bing`
    sinh ra, von chi dung cho Bing) keo ve them SCMP/Bloomberg/CNBC/Reuters ma
    headline day du BO SOT — cung mot dang loi da biet o Bing, chua bao gio ap
    sang Google News. Dung theo THU TU cua ham (dai -> ngan trong tung bo), dung
    som khi da du mien de khong hoi qua nhieu.

    Tach khoi `find` o LOW-309.
    """
    its, co_link_gn = [], set()
    if not ten:
        return its
    for q in [ten] + _query_bing(ten):
        try:
            for it in safe_xml.fromstring(_download(GNEWS.format(q=up.quote(q)), 25).content
                                          ).findall(".//item"):
                k = it.findtext("link") or ""
                if k and k not in co_link_gn:
                    co_link_gn.add(k)
                    its.append(it)
        except Exception as e:                               # noqa: BLE001
            print(f"[nguon_bai] google news hong ({q!r}): {type(e).__name__}", file=sys.stderr)
        if len({it.find('source').get('url') for it in its
                if it.find('source') is not None}) >= so * 3:
            break
    return its


def _outlet_of_item(its: list, so: int) -> list:
    """[(mien toa soan, tieu de)] theo THU TU Google News tra ve, khong trung mien."""
    mien = []
    for it in its[: so * 6]:
        src = it.find("source")
        u = (src.get("url") if src is not None else "") or ""
        if u:
            u = u.rstrip("/")
            if u not in [m for m, _ in mien]:
                mien.append((u, it.findtext("title") or ""))
    return mien


def _scan_feed(mien: list, goc: set, so: int) -> list:
    """Doan RSS cua tung toa soan, song song, co TRAN THOI GIAN (LOW-277).

    Tra ve ket qua theo DUNG thu tu Google News (khong theo luc luong xong), de
    nguon dau tien van la toa soan Google News xep dau. Tach khoi `find` o LOW-309.
    """
    stop_feeds = threading.Event()

    def _trong_feed(cap):
        m, _ = cap
        for duong in ("/feed/", "/rss", "/feed", "/rss.xml", "/index.xml"):
            if stop_feeds.is_set():                          # het FEED_BUDGET_SECONDS (LOW-277)
                return None
            try:
                rr = _download(m + duong, FEED_TIMEOUT_SECONDS)
                if rr.status_code != 200 or b"<item" not in rr.content[:400_000]:
                    continue
                for i in safe_xml.fromstring(rr.content).findall(".//item"):
                    t = i.findtext("title") or ""
                    chung = goc & _tu(t)
                    if chung and len(chung) / max(len(goc), 1) >= 0.5:
                        return {"url": i.findtext("link") or "", "kind": "other_outlet",
                                "title": t, "outlet_url": m}
                return None
            except (httpx.TimeoutException, httpx.ConnectError):
                return None                                  # mien treo/khong toi duoc: bo 4 duong con lai
            except Exception:                                # noqa: BLE001
                continue
        return None

    # Khong `with`: khoi `with` doi MOI luong xong ke ca khi da het tran (LOW-277).
    # Luong dang tai do se tu dung sau lan tai hien tai nho `stop_feeds`.
    feed_start = time.time()
    pool = cf.ThreadPoolExecutor(max_workers=env_load.quantity(6))
    futures = [pool.submit(_trong_feed, cap) for cap in mien[: so * 3]]
    done, not_done = cf.wait(futures, timeout=FEED_BUDGET_SECONDS)
    stop_feeds.set()
    pool.shutdown(wait=False, cancel_futures=True)
    if not_done:
        print(f"[nguon_bai] doan RSS: het {FEED_BUDGET_SECONDS}s, bo {len(not_done)}/{len(futures)} "
              f"mien chua xong", file=sys.stderr)
    elif futures:
        print(f"[nguon_bai] doan RSS: {len(futures)} mien xong trong {time.time() - feed_start:.1f}s",
              file=sys.stderr)
    return [fut.result() if fut in done and fut.exception() is None else None
            for fut in futures]


def find(tieu_de: str, link: str, so=COUNT_SOURCE) -> dict:
    link_gnews = None
    if GNEWS_ARTICLE in link:
        that = resolve_code_gnews(link)
        if that:
            link_gnews, link = link, that
            print(f"[nguon_bai] link Google News -> {link[:90]}", file=sys.stderr)
    ra = [{"url": link, "kind": "article", "title": tieu_de}]
    # Tim kiem CHI bang tieng Anh (xem luat o tren). `ten` rong -> khong hoi feed nao.
    ten = title_find(tieu_de, link, link_gnews or "")
    its = _gnews_item(ten, so)
    mien = _outlet_of_item(its, so)

    thay = {link}
    for kq in _scan_feed(mien, _tu(ten or tieu_de), so):
        if kq and kq["url"] and kq["url"] not in thay:
            thay.add(kq["url"])
            ra.append(kq)
        if len(ra) > so:
            break
    # Goi Bing khi chua du `so`+1 nguon (truoc: < 3). Vong feed thuong chi ra 2-3
    # trang vi nhieu toa soan khong co RSS; Bing voi headline tieng Anh bu phan con lai.
    m = re.match(r"https?://([^/]+)", link)
    mien_goc = ((m.group(1) if m else "").replace("www.", ""),)
    if len(ra) <= so:
        for t in (other_outlets_bing(ten, so=so, bo_mien=mien_goc) if ten else []):
            if t["url"] not in thay:
                thay.add(t["url"])
                ra.append(t)
            if len(ra) > so:
                break
    # Van con it bao -> giai ma chinh cac bai cung tin Google News da tra (LOW-275).
    if ten and len(ra) - 1 < MIN_OTHER_OUTLETS:
        found_domains = tuple(_domain(t["url"]) for t in ra)
        for t in other_outlets_gnews(ten, its, count=so + 1 - len(ra),
                                     skip_domains=mien_goc + found_domains):
            if t["url"] not in thay:
                thay.add(t["url"])
                ra.append(t)
    kq = {"title": tieu_de, "title_en": ten, "source_url": link, "pages": ra}
    if link_gnews:
        kq["gnews_url"] = link_gnews
    return kq


def main():
    ap = argparse.ArgumentParser(description="Tim nguon cho mot tin (viec cua Finn)")
    ap.add_argument("--tieu-de", required=True)
    ap.add_argument("--link", required=True)
    ap.add_argument("--so", type=int, default=COUNT_SOURCE)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    kq = find(a.tieu_de, a.link, a.so)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(kq, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    print(a.out)
    for t in kq["pages"]:
        print(f"  [{page_kind_label(t['kind'])}] {t['url'][:88]}", file=sys.stderr)
    return 0 if len(kq["pages"]) > 1 else EXIT_ONLY_ORIGINAL


if __name__ == "__main__":
    sys.exit(main())
