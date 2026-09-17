#!/usr/bin/env python3
"""Quet tin DAU TU / KINH TE / DOANH NGHIEP / THUONG HIEU quanh AI — tat dinh.

Viec cua Vera (profile market). Khac hai vai kia:
  - Finn quet HN/Reddit/arXiv: tin ky thuat, can co nguoi ban luan.
  - Nova doc so dang ky model: model nao vua ra, manh yeu the nao.
  - Vera doc bao kinh doanh: tien di dau, ai mua ai, chinh sach nao vua doi,
    nghe nao sap mat viec.

Xuong song la Google News RSS: mien phi, khong khoa, va quan trong nhat la
TRUY VAN TU DO — muon theo doi chu de moi thi them mot dong vao QUERY, khong
phai di tim nguon moi. Da do song: 'Anthropic IPO' ra 92 bai, 'AI acquisition'
ra 100 bai trong do co dung tin Stripe mua OpenRouter.

Bo sung vai feed bao cong nghe de khong phu thuoc mot nha.

Chong trung: Google News tra ve cung mot su kien tu nhieu bao. Gom theo tieu de
da chuan hoa (bo ten toa soan phia sau dau gach, bo dau cau, ha chu thuong) roi
giu ban som nhat, nen mot su kien chi hien mot lan du muoi bao dua tin.
"""
import argparse
import json
import re
import sys
import os
import time
import unicodedata
import urllib.parse as up
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path


import scan_common                                            # noqa: E402
import env_load
import required

STATE = env_load.state_dir() / "business_seen.json"
UA = scan_common.UA                     # mot ban duy nhat, xem scan_common
GNEWS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

# Moi dong la mot goc theo doi. Them chu de moi = them mot dong.
QUERY = [
    ("gọi vốn / IPO", "AI startup IPO OR funding round OR valuation when:7d"),
    ("thâu tóm", "AI company acquisition OR acquires OR merger when:7d"),
    ("hạ tầng & vốn lớn", "AI datacenter investment billion when:7d"),
    ("chính sách & nhãn AI", "AI generated content label OR watermark OR disclosure policy when:14d"),
    ("lao động & việc làm", "AI job losses OR layoffs OR humanoid robot workers when:14d"),
    ("thương hiệu & sản phẩm", "brand launches AI product OR partnership when:7d"),
    ("kiện tụng & bản quyền", "AI copyright lawsuit OR settlement when:14d"),
    # Ba nhom them sau khi doi chieu voi mot ban tin ben ngoai va thay bo sot:
    # Databricks goi von $5 ty va Snowflake/TrueFoundry deu la ha tang du lieu
    # doanh nghiep, khong nhom nao trong sau nhom tren phu toi.
    ("hạ tầng dữ liệu doanh nghiệp",
     "data platform OR data warehouse AI funding OR valuation when:7d"),
    ("MLOps & công cụ triển khai",
     "MLOps OR inference platform OR model serving startup when:7d"),
    ("chip & bán dẫn cho AI",
     "AI chip deal OR semiconductor financing OR foundry capacity when:7d"),
    # Them 26/08: nhom tren chi bat DEAL/tai chinh chip, khong bat RA MAT san
    # pham. Xiaomi ra mat AI Cube (mini PC chay chip Xring) phu day tren Reuters
    # va Bloomberg ma khong dong nao cham toi: "brand launches AI product" qua
    # chung nen Google News chon no xuong duoi 50 tin khac. Dong nay nham thang
    # vao ra mat chip / phan cung AI.
    ("ra mắt chip & phần cứng AI",
     "AI chip OR processor OR NPU OR mini PC unveils OR launches OR announces when:7d"),
]

# Feed bao de khong phu thuoc mot minh Google News. Day la nguon TAT DINH: no tra
# dung nhung gi toa soan dang, khong qua xep hang cua Google News. Google News xep
# hang bat dinh nen tin cu the (Xiaomi ra Cube, Rillet thanh unicorn) luc co luc
# khong; feed beat cua bao thi luon co.
#
# (ten, url, can_loc_ai): feed chuyen ve AI thi can_loc_ai=False (moi tin deu AI).
# Feed beat chung (venture, startups) can_loc_ai=True: chi giu tin co dinh toi AI,
# de khong dua ca tin VC khong lien quan vao.
RSS_REPORT = [
    ("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/", False),
    ("The Verge", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml", False),
    # Beat goi von / startup: bat tin nhu Rillet ($100M, unicorn), Hugging Face bi
    # mua lai, ma truy van gop cua Google News hay chon xuong duoi.
    ("TechCrunch", "https://techcrunch.com/category/venture/feed/", True),
    ("TechCrunch", "https://techcrunch.com/category/startups/feed/", True),
    # Feed CHUYEN AI cua cac toa soan lon: moi tin deu AI nen khong loc. Day la
    # xuong song tat dinh — phu dung nhung beat Google News hay chon sot: goi von
    # (SiliconAngle, VentureBeat), enterprise & ha tang (The Register), nghien cuu
    # & phan cung (Ars Technica).
    ("SiliconAngle", "https://siliconangle.com/category/ai/feed/", False),
    ("VentureBeat", "https://venturebeat.com/category/ai/feed/", False),
    ("The Register", "https://www.theregister.com/software/ai_ml/headlines.atom", False),
    ("Ars Technica", "https://arstechnica.com/ai/feed/", False),
]

# Toa soan uy tin — dung de xep do tin cay, khong dung de loai bo
REPORT_LARGE = ("reuters", "bloomberg", "financial times", "wall street journal", "wsj",
           "the information", "cnbc", "axios", "forbes", "fortune", "nytimes",
           "new york times", "the economist", "techcrunch", "the verge", "ft.com")

# WATCHLIST — cac ten trong nganh AI ma tin ve chung PHAI theo sat, bat ke may
# bao dua hay diem co hoc bao nhieu. Day la nguyen tac chu khong phai goi y: tin
# ve mot ten trong day KHONG BAO GIO bi cat truoc khi Vera nhin (xem chon_cho_vera).
#
# Vi sao can rieng danh sach nay: diem co hoc xep hang theo "nhieu bao dua". Google
# News RSS chi tra vai bien the tit cho mot su kien, moi bien the mot bao, nen tin
# lon nhung chi hien vai dong (Xiaomi ra mat AI Cube, Apple ra chip M6) bi cham
# thap va cat mat. Ma day la nhung thu tac dong ca nganh. MiMo cua Xiaomi tung la
# model tieu thu token nhieu nhat the gioi truoc khi v4-flash ra; bo tin Xiaomi la
# bo dung loai tin quan trong nhat.
#
# Gom ca TEN HANG lan TEN MODEL/CHIP, vi tin thuong goi ten san pham chu khong goi
# ten hang (vd "MiMo", "M6", "Xring", "Gemini" thay vi "Xiaomi", "Apple", "Google").
WATCHLIST = (
    # phong thi nghiem & hang lam model
    "openai", "chatgpt", "gpt", "anthropic", "claude", "google deepmind",
    "deepmind", "gemini", "meta ai", "llama", "mistral", "mixtral", "cohere",
    "perplexity", "xai", "grok", "stability ai", "stable diffusion", "midjourney",
    "runway", "hugging face", "black forest", "flux",
    # hang Trung Quoc & model
    "deepseek", "qwen", "alibaba", "tongyi", "bytedance", "doubao", "tencent",
    "hunyuan", "baidu", "ernie", "moonshot", "kimi", "zhipu", "glm", "minimax",
    "xiaomi", "mimo", "xring", "01.ai", "yi ",
    # hang phan cung & nen tang lon
    "nvidia", "apple", "microsoft", "amazon", "aws", "samsung", "huawei",
    "qualcomm", "intel", "amd", "tsmc", "arm", "broadcom", "sony", "tesla",
    "databricks", "snowflake", "oracle", "softbank", "lenovo",
)


# Nhieu ten cung mot hang: gom ve mot moi de "cuu" khong dem Xiaomi/MiMo/Xring
# thanh ba hang khac nhau, va de OpenAI/ChatGPT/GPT khong chiem ba suat.
RANK_OF_NAME = {
    "chatgpt": "openai", "gpt": "openai",
    "claude": "anthropic",
    "gemini": "google deepmind", "deepmind": "google deepmind",
    "google deepmind": "google deepmind",
    "meta ai": "meta", "llama": "meta",
    "mixtral": "mistral",
    "stable diffusion": "stability ai",
    "tongyi": "alibaba", "qwen": "alibaba",
    "doubao": "bytedance", "hunyuan": "tencent", "ernie": "baidu",
    "kimi": "moonshot", "glm": "zhipu",
    "mimo": "xiaomi", "xring": "xiaomi",
    "aws": "amazon",
    "flux": "black forest", "yi ": "01.ai",
}


# Hang LOI: co tin la bat buoc, ke ca chi mot bao. Hang watchlist khac chi bat
# buoc khi tu 2 bao tro len (Lenovo ra man hinh moi khong phai tin nganh AI).
RANK_ERROR = {"openai", "anthropic", "google", "deepmind", "meta", "nvidia", "microsoft",
            "apple", "deepseek", "qwen", "alibaba", "xai", "amazon", "hugging face",
            "mistral", "moonshot", "kimi", "bytedance", "xiaomi", "samsung"}


def name_watchlist(tieu_de: str) -> str | None:
    """Ten HANG trong watchlist ma tin nay noi toi, hoac None.

    So theo BIEN GIOI TU de "arm" khong khop "harm", "yi" khong khop "yield".
    Ten model/chip (MiMo, Gemini...) duoc quy ve hang chu (Xiaomi, Google) qua
    RANK_OF_NAME, de khau "cuu" dam bao du HANG chu khong trung mot hang nhieu lan.
    """
    td = " " + tieu_de.lower() + " "
    for ten in WATCHLIST:
        khop = (ten in td) if " " in ten else (
            f" {ten} " in td or f" {ten}'" in td
            or f" {ten}," in td or f" {ten}." in td or f" {ten}:" in td)
        if khop:
            return RANK_OF_NAME.get(ten, ten)
    return None


def within_watchlist(tieu_de: str) -> bool:
    return name_watchlist(tieu_de) is not None



_get = scan_common.get                  # mot ban duy nhat, xem scan_common


_ts = scan_common.timestamp_time          # mot ban (ADF-r2-15): 45e206c them ham chung ma chua ai goi


def standard_ify(tieu_de: str) -> str:
    """Rut tieu de ve dang so sanh duoc, de gom cac bao dua cung mot tin.

    Google News gan ' - Ten Toa Soan' vao cuoi. Cat phan do truoc, roi bo dau
    cau va ha chu thuong."""
    t = re.sub(r"\s+-\s+[^-]{2,40}$", "", tieu_de).strip()
    t = unicodedata.normalize("NFKD", t)
    t = re.sub(r"[^\w\s]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def outlet(tieu_de: str) -> str:
    m = re.search(r"\s+-\s+([^-]{2,40})$", tieu_de)
    return m.group(1).strip() if m else ""


def scan_gnews(gio_toi_da: int) -> list:
    nguong = time.time() - gio_toi_da * 3600
    ra = []
    for nhan, q in QUERY:
        try:
            root = ET.fromstring(_get(GNEWS.format(q=up.quote(q))).content)
        except Exception as e:                               # noqa: BLE001
            print(f"[gnews {nhan}] hong: {type(e).__name__}", file=sys.stderr)
            continue
        for it in root.findall(".//item"):
            td = (it.findtext("title") or "").strip()
            ts = _ts(it.findtext("pubDate") or "")
            if not td or (ts and ts < nguong):
                continue
            ra.append({"goc": nhan, "tieu_de": td, "toa_soan": outlet(td),
                       "link": it.findtext("link") or "", "ts": ts,
                       "ngay": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
                       if ts else "?"})
    return ra


def scan_report(gio_toi_da: int) -> list:
    nguong = time.time() - gio_toi_da * 3600
    ra = []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for ten, url, can_loc_ai in RSS_REPORT:
        try:
            root = ET.fromstring(_get(url).content)
        except Exception as e:                               # noqa: BLE001
            print(f"[rss {ten}] hong: {type(e).__name__}", file=sys.stderr)
            continue
        for it in (root.findall(".//item") or root.findall(".//a:entry", ns)):
            td = (it.findtext("title") or (it.find("a:title", ns).text
                  if it.find("a:title", ns) is not None else "") or "").strip()
            ngay_txt = (it.findtext("pubDate") or it.findtext("published")
                        or (it.find("a:published", ns).text
                            if it.find("a:published", ns) is not None else "") or "")
            ts = _ts(ngay_txt)
            if not td or (ts and ts < nguong):
                continue
            # Feed beat chung: chi giu tin dinh toi AI (co "ai"/"artificial
            # intelligence" hoac ten trong watchlist). Rillet la "AI accounting
            # startup" nen dat; Fiat Ventures khong AI thi bo.
            if can_loc_ai:
                tl = td.lower()
                if not ("artificial intelligence" in tl
                        or " ai " in f" {tl} " or " ai," in tl or "ai-" in tl
                        or within_watchlist(td)):
                    continue
            link = it.findtext("link") or ""
            if not link and it.find("a:link", ns) is not None:
                link = it.find("a:link", ns).get("href") or ""
            ra.append({"goc": "báo công nghệ", "tieu_de": td, "toa_soan": ten,
                       "link": link, "ts": ts,
                       "ngay": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
                       if ts else "?"})
    return ra


# Tu qua pho bien, khong giup phan biet su kien
FROM_EMPTY = {"the", "a", "an", "of", "in", "on", "to", "for", "and", "or", "with",
           "as", "at", "by", "from", "its", "it", "is", "are", "be", "new", "ai",
           "says", "said", "after", "over", "into", "amid", "this", "that"}


def _keyword(tieu_de: str) -> set:
    return {w for w in standard_ify(tieu_de).split() if w not in FROM_EMPTY and len(w) > 2}


CURRENCY_OF_MARK = {"$": "usd", "us$": "usd", "usd": "usd", "€": "eur", "eur": "eur",
                    "£": "gbp", "gbp": "gbp", "¥": "jpy"}
AMOUNT_UNIT = {"m": 1, "mn": 1, "mln": 1, "million": 1, "b": 1000, "bn": 1000, "billion": 1000,
               "tn": 1_000_000, "trillion": 1_000_000}
AMOUNT_PATTERN = re.compile(
    r"(us\$|\$|€|£|¥|usd|eur|gbp)\s?(\d+(?:[.,]\d+)?)\s?(trillion|million|billion|mln|mn|bn|tn|m|b)\b",
    re.IGNORECASE)
# Tu chung cua moi tin goi von/mua ban: hai vu KHAC nhau cung "raises $100M in
# Series A funding round" van chia se may tu nay, nen khong duoc tinh la trung.
DEAL_WORDS = {"raises", "raise", "raised", "funding", "round", "series", "valuation",
              "investment", "invests", "invest", "deal", "startup", "led", "leads",
              "lead", "backed", "backs", "secures", "million", "billion", "trillion", "mln",
              "company", "firm", "more", "than", "around", "about", "reportedly"}
SAME_AMOUNT_TOLERANCE = 0.03
# EUR/GBP -> USD lech toi ~25%: Crypto Briefing "over €200M" va CNBC "$230 million"
# la cung vong Euclyd (LOW-184).
CROSS_CURRENCY_TOLERANCE = 0.25
MIN_SHARED_DEAL_KEYWORDS = 2
# LOW-213: OpenAI "$1.5 Trillion Valuation" (GV Wire) vs "over $1.5 trillion
# valuation" (Straits Times) chi chung `openai`. So tien co nay gan nhu la dinh
# danh cua vu; con $1B thi nhieu vu (Nvidia dau tu $1B vao Nokia lan Anthropic),
# va ca $100B cung trung (Nvidia-OpenAI $100B, Stargate $100B) nen nguong la $1T.
MEGA_AMOUNT_MILLIONS = 1_000_000
# LOW-213: tin khong co so tien (Anthropic Queensland, SK Hynix-Intel) khong dung
# duoc luat cung-so-tien. Do tren 7 lo that 11-17/09.
NO_AMOUNT_MIN_SHARED = 4
NO_AMOUNT_MIN_RATIO = 0.5
WATCHLIST_WORDS = {w for name in (*WATCHLIST, *RANK_OF_NAME, *RANK_ERROR) for w in name.split()}


def _amounts(tieu_de: str) -> list:
    out = []
    for m in AMOUNT_PATTERN.finditer(tieu_de):
        value = float(m.group(2).replace(",", ".")) * AMOUNT_UNIT[m.group(3).lower()]
        out.append((CURRENCY_OF_MARK[m.group(1).lower()], value))
    return out


def _deal_keywords(tieu_de: str) -> set:
    return {w for w in _keyword(tieu_de)
            if w not in DEAL_WORDS and not re.fullmatch(r"\d+(?:m|mn|bn|tn|b)?", w)}


def _lead_keyword(tieu_de: str) -> str | None:
    return next((w for w in standard_ify(tieu_de).split()
                 if w not in FROM_EMPTY and len(w) > 2), None)


def _same_amount(a: list, b: list, cross_currency=True) -> bool:
    for cur_a, va in a:
        for cur_b, vb in b:
            if cur_a == cur_b:
                tol = SAME_AMOUNT_TOLERANCE
            elif cross_currency:
                tol = CROSS_CURRENCY_TOLERANCE
            else:
                continue
            if abs(va - vb) / max(va, vb) <= tol:
                return True
    return False


FOLLOW_UP_BEFORE_AMOUNT = re.compile(r"\b(after|following|amid|despite|since)\b", re.IGNORECASE)
FOLLOW_UP_WINDOW = 60


def _is_follow_up(tieu_de: str) -> bool:
    # LOW-197: "Finland's Opposition Calls for Data Center Controls After Google's
    # €13 Billion AI Investment" — so tien nam sau "after" la BOI CANH cua mot tin
    # moi, khong phai chu de; khong duoc gop vao tin cong bo €13B.
    for m in AMOUNT_PATTERN.finditer(tieu_de):
        if FOLLOW_UP_BEFORE_AMOUNT.search(tieu_de[max(0, m.start() - FOLLOW_UP_WINDOW):m.start()]):
            return True
    return False


def _capitalized(tieu_de: str, word: str) -> bool:
    return any(tok[0].isupper() and standard_ify(tok) == word
               for tok in re.findall(r"\w+", tieu_de))


def gather_duplicate(tin: list, nguong=0.6) -> list:
    """Mot su kien nhieu bao dua -> giu ban som nhat, dem so bao de biet do nong.

    So khop nguyen van KHONG du: cac bao dien dat khac nhau ve cung mot viec.
    Da gap that — Reuters viet "Nvidia invests in data center developer Cloverleaf
    Infrastructure", TechCrunch viet "Nvidia partners with data center developer
    Cloverleaf", so nguyen van thi thanh hai tin. Nen gom theo DO TRUNG TU KHOA:
    hai tieu de dung chung >= 60% tu dac trung (bo tu rong) thi coi la mot.

    Tin tien (goi von, mua ban) thi dien dat lech qua xa cho nguong 60%: vong
    Euclyd 16/09 ra 5 dong rieng — "Samsung backs Nvidia AI chip rival in $230
    million funding round" vs "Samsung Co-Led $231 Million Funding Round for
    Nvidia AI Chip Rival" chi 7/12=0.58 (LOW-184). Nen them luat thu hai: CUNG
    SO TIEN (xem _same_amount) va chung >= 2 tu dac trung khong phai tu goi von.

    Gom theo cap roi hop nhom (union-find), khong so voi ban dai dien: "Euclyd
    pulled in $231 million with Samsung's backing" chi noi voi nhom qua ban
    "...EUCLYD Amid Memory Shortage", khong qua ban som nhat.
    """
    items = []
    for t in sorted(tin, key=lambda x: x["ts"] or 0):      # som nhat truoc
        tu = _keyword(t["tieu_de"])
        if tu:
            items.append((t, tu, _deal_keywords(t["tieu_de"]), _amounts(t["tieu_de"])))

    items_with_word = {}
    for idx, (_, tu, _, _) in enumerate(items):
        for w in tu:
            items_with_word.setdefault(w, []).append(idx)

    def is_deal_name(w, i, j):
        # LOW-193: Cornelis/Profound chi chung DUNG MOT ten. Tin mot tu don khi:
        # - moi tieu de trong lo co tu do deu noi cung so tien: ten hang le chi
        #   xuat hien quanh vu cua no, con tu thuong ("factory" robots) va hang
        #   lon ("nvidia" dau tu $1B vao Nokia lan Anthropic) thi khong;
        # - viet hoa o CA HAI tieu de va cung tien te: 13/09 "Nvidia Considers
        #   $10 Billion" da nho "considers" + €13bn ma dinh vao tin Finland.
        if len(w) < 4 or w in WATCHLIST_WORDS:
            return False
        if not all(_capitalized(items[k][0]["tieu_de"], w) for k in (i, j)):
            return False
        return all(items[k][3] and _same_amount(items[k][3], items[i][3], cross_currency=False)
                   for k in items_with_word[w])

    def same_subject_without_amount(i, j):
        # LOW-213: chung >= 4 tu dac trung (bo tu goi von/so) va phu >= 1/2 tieu
        # de ngan hon, co >= 2 tu ngoai watchlist, va tu DAU cua mot ben co o ben
        # kia. Tu dau chan hai may Intel Wildcat Lake khac hang (HP OmniDesk vs
        # Acemagic Kron) ma van giu "TSMC posts record August revenue"...
        deal_i, deal_j = items[i][2], items[j][2]
        shared = deal_i & deal_j
        if len(shared) < NO_AMOUNT_MIN_SHARED:
            return False
        if len(shared) / min(len(deal_i), len(deal_j)) < NO_AMOUNT_MIN_RATIO:
            return False
        if len(shared - WATCHLIST_WORDS) < 2:
            return False
        lead_i, lead_j = lead[i], lead[j]
        return lead_i in items[j][1] or lead_j in items[i][1]

    follow_up = [_is_follow_up(t["tieu_de"]) for t, _, _, _ in items]
    lead = [_lead_keyword(t["tieu_de"]) for t, _, _, _ in items]
    parent = list(range(len(items)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i, (_, tu_i, deal_i, amt_i) in enumerate(items):
        for j in range(i):
            _, tu_j, deal_j, amt_j = items[j]
            chung = tu_i & tu_j
            # Mau so la MAX chu khong phai MIN. Voi min, tit ngan la tap con
            # cua tit dai thi LUON gop: "Nvidia stock jumps" nuot "Nvidia stock
            # slides after Beijing bans chip purchases" (2/min(3,7)=0.67) — hai
            # tin nguoc nhau thanh mot. Voi max, ca hai tit phai chia se phan
            # lon tu: ca Cloverleaf kinh dien (invests vs partners) van gop
            # dung (5/7=0.71), con jumps-vs-slides thi khong (2/7=0.29).
            same = chung and len(chung) / max(len(tu_i), len(tu_j)) >= nguong
            guarded = follow_up[i] or follow_up[j]
            if not same and amt_i and amt_j and not guarded:
                shared = deal_i & deal_j
                mega = any(v >= MEGA_AMOUNT_MILLIONS for _, v in amt_i + amt_j)
                same = _same_amount(amt_i, amt_j, cross_currency=not mega) and (
                    len(shared) >= MIN_SHARED_DEAL_KEYWORDS
                    or any(is_deal_name(w, i, j) for w in shared)
                    or (mega and bool(shared)))
            if not same and not guarded:
                same = same_subject_without_amount(i, j)
            if same:
                ri, rj = root(i), root(j)
                parent[max(ri, rj)] = min(ri, rj)   # goc = ban som nhat

    nhom = {}
    for i, (t, _, _, _) in enumerate(items):
        r = root(i)
        vao = nhom.get(r)
        if vao is None:
            vao = dict(t)
            vao["so_bao"] = 1
            vao["cac_bao"] = [t["toa_soan"]] if t["toa_soan"] else []
            # Co watchlist tinh tren tung bien the, va nhom giu co neu BAT KY
            # bien the nao khop. Truoc day tinh sau dedup tren tit dai dien
            # (ban som nhat): ban tin dau khong nhac ten hang lam dai dien la
            # ca nhom mat co bao ve — dung kich ban Xiaomi Cube.
            vao["hang_watch"] = name_watchlist(t["tieu_de"])
            vao["seen_keys"] = [standard_ify(t["tieu_de"])]
            nhom[r] = vao
        else:
            vao["seen_keys"].append(standard_ify(t["tieu_de"]))
            vao["so_bao"] += 1
            if t["toa_soan"] and t["toa_soan"] not in vao["cac_bao"]:
                vao["cac_bao"].append(t["toa_soan"])
            if not vao.get("hang_watch"):
                vao["hang_watch"] = name_watchlist(t["tieu_de"])
    return list(nhom.values())


def already_see() -> dict:
    """Doc bo nho da-thay: {khoa: unix_ts lan cuoi thay}.

    Dinh dang cu la list khoa tran — doc duoc ca hai, chuyen dan sang dict.
    """
    if not STATE.exists():
        return {}
    d = json.loads(STATE.read_text(encoding="utf-8")).get("khoa", [])
    if isinstance(d, list):                # dinh dang cu
        now = time.time()
        return {k: now for k in d}
    return d


def write_timestamp(khoa: dict):
    """Ghi bo nho da-thay, cat theo THOI GIAN, giu cac truong khac cua tep.

    Hai loi cu cua ham nay, ca hai da gay chuyen that:
    - `sorted(khoa)[-2000:]` cat theo BANG CHU CAI: tin bat dau a–m bi day ra
      khoi bo nho va bao lai mai, tin bat dau z khong bao gio duoc quen. Gio
      moi khoa keo theo timestamp va cat theo do.
    - Ghi de ca tep chi voi hai truong -> xoa mat `ghi_chu` (ghi chu su co
      26/08 tung bay theo cach nay). Gio doc tep cu, chi thay truong cua minh.
    """
    STATE.parent.mkdir(parents=True, exist_ok=True)
    goc = {}
    if STATE.exists():
        try:
            goc = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            goc = {}
    giu = dict(sorted(khoa.items(), key=lambda kv: kv[1])[-2000:])
    goc["cap_nhat"] = datetime.now(timezone.utc).isoformat()
    goc["khoa"] = giu
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(goc, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    os.replace(tmp, STATE)


def main():
    ap = argparse.ArgumentParser(description="Quet tin kinh doanh/dau tu quanh AI")
    ap.add_argument("--gio", type=int, default=72, help="Chi lay tin trong N gio (mac dinh 72)")
    # Khong con cham diem cat top: Vera nhin HET tin trong cua so va tu xet. Day
    # chi la VAN AN TOAN chong ngay bat thuong dot bien tin, khong phai bo loc do
    # quan trong. Dat cao, va cat theo MOI NHAT chu khong theo diem, nen tin bi
    # cat (neu co) luon la tin cu nhat trong cua so.
    # 80 thay vi 120 (chot 01/09 sau audit chi phi): prompt cua Vera an theo so
    # tin, ma tin thu 81+ la tin CU NHAT cua so va gan nhu khong bao gio duoc
    # chon. Tin watchlist van LUON qua bat ke cap.
    ap.add_argument("--top", type=int, default=80,
                    help="Van an toan: toi da bao nhieu tin dua cho Vera (mac dinh 80)")
    ap.add_argument("--lan-dau", action="store_true", help="Chi ghi moc, khong bao")
    ap.add_argument("--out", help="Ghi JSON ra tep")
    ap.add_argument("--state", help="Duong dan file seen khac (de TEST khong dung "
                    "business_seen.json that). Mac dinh dung file that.")
    a = ap.parse_args()

    # Cho phep tro seen sang file khac khi test. Su co 26/08: chay --lan-dau khi
    # test lam ghi de business_seen that, danh dau nham tin chua bao la da thay.
    global STATE
    if a.state:
        STATE = Path(a.state)

    tin = gather_duplicate(scan_gnews(a.gio) + scan_report(a.gio))
    cu = already_see()
    now = time.time()

    if a.lan_dau:
        write_timestamp({**cu, **{k: now for t in tin for k in t["seen_keys"]}})
        print(f"Da ghi moc {len(tin)} tin. Lan sau chi bao cai moi.")
        return

    # LOW-213: nhom da thay neu BAT KY bien the nao da thay. Chi so dai dien thi
    # hom sau dai dien doi sang ban khac (Euclyd, Glass Imaging 17/09) va tin cu
    # lot lai vao danh sach.
    moi = [t for t in tin if not any(k in cu for k in t["seen_keys"])]
    for t in moi:
        # hang_watch da duoc gather_duplicate tinh tren TUNG bien the truoc khi gop.
        t["watchlist"] = bool(t.get("hang_watch"))

    # KHONG cham diem, KHONG cat theo do quan trong. Cach cham cu xep theo "nhieu
    # bao dua", nen tin lon ma Google News chi tra vai dong (Xiaomi ra AI Cube,
    # Apple ra M6) bi cat truoc khi Vera nhin. Vera moi la bo loc that: dua het
    # tin trong cua so cho no tu xet.
    #
    # Xep MOI NHAT truoc — thu tu Vera doc.
    moi.sort(key=lambda t: -(t["ts"] or 0))

    # Van an toan chi chan tin THUONG. Tin watchlist (top brand) LUON qua, bat ke
    # cap: cai cap sinh ra de chong ngay dot bien tin lam vo prompt cua Vera, chu
    # khong phai de bo tin quan trong. Ngay Xiaomi ra Cube ma cap cat mat no thi
    # lai dung loi cu.
    wl = [t for t in moi if t["watchlist"]]
    thuong = [t for t in moi if not t["watchlist"]]
    chon = wl + thuong[:max(0, a.top - len(wl))]
    chon.sort(key=lambda t: -(t["ts"] or 0))

    # Gon tung item truoc khi ghi tep cho Vera — prompt cua no an theo kich
    # thuoc tep nay (audit 01/09). `so_bao` du de danh gia do nong; danh sach
    # ten bao cap 3 (du cho source_note); `hang_watch` trung y voi `watchlist`
    # thi bo. `chon` goc van dung nguyen cho write_timestamp ben duoi.
    xuat = []
    for t in chon:
        t2 = {k: v for k, v in t.items() if k not in ("hang_watch", "seen_keys")}
        t2["cac_bao"] = t.get("cac_bao", [])[:3]
        xuat.append(t2)
    # BAT BUOC (luat Ong Chu 04/09/2026): tin watchlist (top brand nganh AI)
    # la PHAI co trong manifest cua Vera, tich luy sang hom sau neu sot.
    # MOT muc moi HANG moi NGAY (khong phai moi bai bao): Nvidia mua Hugging
    # Face co 3 bao thi Vera chon 1 bai la du. Chi hang LOI, hoac tin >= 2 bao.
    # Khop bang ten hang trong tieu de/tom tat cua Vera (tu_khoa), khong theo link.
    if not a.lan_dau:
        nhom = {}
        for t in chon:
            hang = (t.get("hang_watch") or "").lower()
            if not (t["watchlist"] and hang):
                continue
            if hang not in RANK_ERROR and (t.get("so_bao") or 0) < 2:
                continue
            k = f"hang|{hang}|{t['ngay']}"
            # KHONG dung ten `cu`: do la bo nho da-thay (da_thay()) dung o cuoi
            # main cho write_timestamp. Ghi de no o day lam write_timestamp nhan None -> crash
            # sau khi da ghi --out, tuc Vera co tep ma moc khong duoc cap nhat
            # (tin bao lai hom sau). Bat 04/09/2026 khi chay thu scan_prepare.
            cu_nhom = nhom.get(k)
            if not cu_nhom or (t.get("so_bao") or 0) > (cu_nhom.get("so_bao") or 0):
                nhom[k] = t
        muc = [(k, f"{t['hang_watch']}: {t['tieu_de']}", "watchlist",
                f"{t['so_bao']} bao; {t['ngay']}", t.get("link", ""), [t["hang_watch"]])
               for k, t in nhom.items()]
        so_moi = required.extra_many("vera", muc)
        print(f"  bat buoc: {len(muc)} tin watchlist, {so_moi} moi; tong dang cho "
              f"{len(required.read('vera'))} (bat_buoc_vera.json)", file=sys.stderr)

    ket = {"quet_luc": datetime.now(timezone.utc).isoformat(),
           "tong_quet": len(tin),
           "tin_watchlist": sum(1 for t in chon if t["watchlist"]),
           "tin_moi": xuat}
    if a.out:
        Path(a.out).write_text(json.dumps(ket, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        print(a.out)
    else:
        wl = sum(1 for t in chon if t["watchlist"])
        print(f"=== {len(chon)}/{len(tin)} tin (sau gom trung, bo da bao) "
              f"| {wl} tin watchlist ===\n")
        for t in chon:
            dau = "[W]" if t["watchlist"] else "   "
            print(f"  {dau} {t['ngay']}  ({t['goc']})  {t['so_bao']} báo")
            print(f"        {t['tieu_de'][:100]}")
    # CHI danh dau tin DA DUA cho Vera (chon), khong phai tat ca tin quet duoc.
    # Truoc day danh dau het: ngay dot bien, phan bi van --top cat van vao seen
    # -> lan sau bi loc "da thay" -> khong bao gio toi Vera nua. Van an toan
    # thanh may xoa tin. Tin bi cat hom nay, mai van con moi thi van len duoc.
    write_timestamp({**cu, **{k: now for t in chon for k in t["seen_keys"]}})


if __name__ == "__main__":
    main()
