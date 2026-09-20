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
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


import scan_common                                            # noqa: E402
import env_load
import required
import safe_xml
import state_paths

STATE = env_load.state_dir() / state_paths.BUSINESS_SEEN_FILE
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
            root = safe_xml.fromstring(_get(GNEWS.format(q=up.quote(q))).content)
        except Exception as e:                               # noqa: BLE001
            print(f"[gnews {nhan}] hong: {type(e).__name__}", file=sys.stderr)
            continue
        for it in root.findall(".//item"):
            td = (it.findtext("title") or "").strip()
            ts = _ts(it.findtext("pubDate") or "")
            if not td or (ts and ts < nguong):
                continue
            ra.append({"feed_group": nhan, "title": td, "outlet": outlet(td),
                       "link": it.findtext("link") or "", "ts": ts,
                       "date": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
                       if ts else "?"})
    return ra


def scan_report(gio_toi_da: int) -> list:
    nguong = time.time() - gio_toi_da * 3600
    ra = []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for ten, url, can_loc_ai in RSS_REPORT:
        try:
            root = safe_xml.fromstring(_get(url).content)
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
            ra.append({"feed_group": "báo công nghệ", "title": td, "outlet": ten,
                       "link": link, "ts": ts,
                       "date": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
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
        tu = _keyword(t["title"])
        if tu:
            items.append((t, tu, _deal_keywords(t["title"]), _amounts(t["title"])))

    items_with_word = {}
    for idx, (_, tu, _, _) in enumerate(items):
        for w in tu:
            items_with_word.setdefault(w, []).append(idx)

    def is_deal_name(w, i, j):
        # LOW-193: Cornelis/Profound chi chung DUNG MOT ten. Tin mot tu don khi:
        # - moi tieu de trong lo co tu do deu noi cung so tien: ten hang le chi
        #   xuat hien quanh vu cua no, con tu thuong ("factory" robots) va hang
        #   lon ("nvidia" dau tu $1B vao Nokia lan Anthropic) thi khong;
        # - viet hoa o CA HAI tieu de: 13/09 "Nvidia Considers $10 Billion" da
        #   nho "considers" + €13bn ma dinh vao tin Finland.
        # LOW-214: tieu de khong co so tien ma DA cung nhom voi cap nay thi bo
        # qua (UA.NEWS "...Dutch AI startup Euclyd" chan IO+ "EUCLYD raises more
        # than €200M"); tieu de khong so tien NGOAI nhom van chan, do la cai giu
        # "factory" robots tach khoi Factory $5B. Cho lech tien te (€200M vs $231M).
        if len(w) < 4 or w in WATCHLIST_WORDS:
            return False
        if not all(_capitalized(items[k][0]["title"], w) for k in (i, j)):
            return False
        groups = {root(i), root(j)}
        for k in items_with_word[w]:
            if items[k][3]:
                if not _same_amount(items[k][3], items[i][3]):
                    return False
            elif root(k) not in groups:
                return False
        return True

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

    follow_up = [_is_follow_up(t["title"]) for t, _, _, _ in items]
    lead = [_lead_keyword(t["title"]) for t, _, _, _ in items]
    parent = list(range(len(items)))

    def root(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def pair_is_same(i, j):
        _, tu_i, deal_i, amt_i = items[i]
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
        return bool(same)

    # Lap toi khi khong gop them: luat mot-ten-chung xet nhom HIEN TAI, nen cap
    # bi tu choi o luot dau co the dat sau khi cap khac vua gop (LOW-214).
    changed = True
    while changed:
        changed = False
        for i, j in _unmerged_pairs(len(items), root):
            if pair_is_same(i, j):
                ri, rj = root(i), root(j)
                parent[max(ri, rj)] = min(ri, rj)   # goc = ban som nhat
                changed = True

    nhom = {}
    for i, (t, _, _, _) in enumerate(items):
        r = root(i)
        vao = nhom.get(r)
        if vao is None:
            vao = dict(t)
            vao["outlet_count"] = 1
            vao["outlets"] = [t["outlet"]] if t["outlet"] else []
            # Co watchlist tinh tren tung bien the, va nhom giu co neu BAT KY
            # bien the nao khop. Truoc day tinh sau dedup tren tit dai dien
            # (ban som nhat): ban tin dau khong nhac ten hang lam dai dien la
            # ca nhom mat co bao ve — dung kich ban Xiaomi Cube.
            vao["watchlist_company"] = name_watchlist(t["title"])
            vao["seen_keys"] = [standard_ify(t["title"])]
            nhom[r] = vao
        else:
            vao["seen_keys"].append(standard_ify(t["title"]))
            vao["outlet_count"] += 1
            if t["outlet"] and t["outlet"] not in vao["outlets"]:
                vao["outlets"].append(t["outlet"])
            if not vao.get("watchlist_company"):
                vao["watchlist_company"] = name_watchlist(t["title"])
    return list(nhom.values())


def _unmerged_pairs(n, root):
    for i in range(n):
        for j in range(i):
            if root(i) != root(j):
                yield i, j


# LOW-253: sau 5 lan va luat tu khoa (LOW-184..214) van con tin trung chi khac
# vai chu (NYT/Microsoft "theft" 4 dong, BrainChip, Cohere + Aleph Alpha 18/09)
# va tin cu quay lai khi cac ban cu ra khoi cua so quet (Glass Imaging). Luat
# "code truoc, LLM sau" (17/09): code gom phan tat dinh o tren, LLM gom phan con
# lai. Do 18/09 tren lo that: flash gop bua (Snapdragon voi Tesla AI5, Mistral voi
# Cohere); pro dung het 12 nhom, ~2 giay.
SAME_STORY_MODEL = env_load.SAME_STORY_MODEL
SAME_STORY_LOOKBACK_SECONDS = 3 * 86400
SAME_STORY_MAX_PRIOR = 200
SAME_STORY_TIMEOUT = 120
SAME_STORY_ASKS = 2
# Dong tu tin tuc chung: hai tin khac nhau van hay dung chung ("Manus nears $500M
# raise" vs "Emulate nears $700 million round", 18/09 ca hai lan hoi deu noi nham).
GENERIC_NEWS_WORDS = {"nears", "hits", "approaches", "launches", "launch", "announces",
                      "unveils", "reveals", "says", "plans", "expands", "weighs", "considers",
                      "talks", "gets", "wins", "adds", "makes", "boosts", "first", "latest",
                      "report", "reports", "stock", "shares", "market", "global"}
SAME_STORY_LINE = re.compile(r"\b([TP])(\d+)\b")
# Tieu de cu danh so tu 1000: do 18/09, khi hai danh sach cung bat dau tu 0 thi ca
# hai lan hoi deu ghep T123 voi P123, T124 voi P124... (lech so, khong lien quan).
PRIOR_ID_OFFSET = 1000


def same_story_prompt(today: list, prior: list) -> str:
    lines = ([f"T{i}: {t}" for i, t in enumerate(today)]
             + [f"P{i + PRIOR_ID_OFFSET}: {t}" for i, t in enumerate(prior)])
    return ("Below are news headlines. T = today's candidates, P = already reported in the last 3 days.\n"
            "Find headlines that report the SAME specific event (same company/people AND same action), "
            "even if worded differently or with different figures from different sources.\n"
            "Do NOT group headlines that merely share a company, a topic, or a trend.\n"
            "Every group must contain at least one T headline.\n"
            "Answer ONLY with lines like: SAME: T3, T11, P1040\n"
            "No other text. If nothing matches, answer NONE.\n\n" + "\n".join(lines))


def parse_same_story_groups(txt: str, today: list, prior: list) -> list:
    """Boc `SAME: T3, T11, P40` thanh [[("T", 3), ...]] — thuan, test duoc.

    Bo chi so ngoai pham vi, bo thanh vien khong chung TU KHOA nao voi thanh vien
    con lai (LLM lech so thu tu thi ghep bua), bo nhom khong con T hoac < 2 muc.
    """
    groups = []
    for line in txt.splitlines():
        members = []
        for kind, n in SAME_STORY_LINE.findall(line):
            n = int(n) - (PRIOR_ID_OFFSET if kind == "P" else 0)
            src = today if kind == "T" else prior
            if 0 <= n < len(src) and (kind, n) not in members:
                members.append((kind, n))
        words = {m: _keyword((today if m[0] == "T" else prior)[m[1]]) for m in members}
        members = [m for m in members
                   if any(words[m] & words[o] for o in members if o != m)]
        if len(members) >= 2 and any(k == "T" for k, _ in members):
            groups.append(members)
    return groups


def ask_same_story(today: list, prior: list) -> str | None:
    env_load.load()
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("[same_story] thieu OPENAI_API_KEY -> chi dung gom bang code", file=sys.stderr)
        return None
    body = {"model": SAME_STORY_MODEL, "thinking": {"type": "disabled"}, "max_tokens": 1500,
            "stream": False, "temperature": 0,
            "messages": [{"role": "user", "content": same_story_prompt(today, prior)}]}
    try:
        req = urllib.request.Request(env_load.ROUTER_URL, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json",
                                              "Authorization": "Bearer " + key})
        raw = urllib.request.urlopen(req, timeout=SAME_STORY_TIMEOUT).read().decode().strip()
        if raw.startswith("data:"):
            raw = raw.split("data: [DONE]")[0].strip()[5:].strip()
        return json.loads(raw)["choices"][0]["message"]["content"]
    except Exception as e:                                   # noqa: BLE001
        print(f"[same_story] llm loi {type(e).__name__} -> chi dung gom bang code", file=sys.stderr)
        return None


def consensus_groups(txts: list, today: list, prior: list) -> list:
    """Chi giu lien ket ma MOI cau tra loi deu co — thuan, test duoc.

    Do 18/09: cung lo, cung prompt, temperature 0 ma hai lan hoi ra nhom khac
    nhau; lan dau gop nham Sagtec (hop tac vs hop dong $10M) va Snap (Specs AI vs
    kinh $2,200), lan sau khong. Loi gop bua hiem khi lap lai hai lan.
    """
    def title(m):
        return today[m[1]] if m[0] == "T" else prior[m[1]]

    def cross_day_ok(a, b):
        # Lien ket T-P lam tin MOI bien mat vi "da bao" — loi dat nhat, nen phai
        # chung mot tu rieng (ten), khong tinh tu goi von, so, dong tu tin chung.
        if a[0] == b[0]:
            return True
        return bool((_deal_keywords(title(a)) & _deal_keywords(title(b))) - GENERIC_NEWS_WORDS)

    edge_sets = []
    for txt in txts:
        edges = set()
        for members in parse_same_story_groups(txt, today, prior):
            edges |= {frozenset((a, b)) for a in members for b in members
                      if a != b and cross_day_ok(a, b)}
        edge_sets.append(edges)
    if not edge_sets:
        return []
    agreed = set.intersection(*edge_sets)
    parent = {}

    def root(m):
        parent.setdefault(m, m)
        while parent[m] != m:
            m = parent[m]
        return m

    for edge in agreed:
        a, b = sorted(edge)
        parent[root(b)] = root(a)
    comps = {}
    for m in {m for e in agreed for m in e}:
        comps.setdefault(root(m), []).append(m)
    return sorted(sorted(c) for c in comps.values() if any(k == "T" for k, _ in c))


def merge_same_story(fresh: list, groups: list) -> tuple:
    """Ap ket qua LLM len cac nhom chua bao (`fresh`) — thuan, test duoc.

    Nhom dinh mot tieu de da bao (P) -> bo, tra ve de danh dau da thay. Cac nhom
    T cung mot su kien -> gop vao ban som nhat, cong so bao va khoa da thay.
    Tra ve (fresh_moi, nhom_da_bao).
    """
    absorbed, already_reported = set(), []
    out = {id(t): t for t in fresh}
    for members in groups:
        idx = sorted({n for k, n in members if k == "T"} - absorbed,
                     key=lambda n: fresh[n]["ts"] or 0)
        if not idx:
            continue
        if any(k == "P" for k, _ in members):
            for n in idx:
                already_reported.append(fresh[n])
                out.pop(id(fresh[n]), None)
            absorbed.update(idx)
            continue
        if len(idx) < 2:
            continue
        base = fresh[idx[0]]
        for n in idx[1:]:
            other = fresh[n]
            base["outlet_count"] += other["outlet_count"]
            base["outlets"] += [o for o in other["outlets"] if o not in base["outlets"]]
            base["seen_keys"] += other["seen_keys"]
            base["watchlist_company"] = base.get("watchlist_company") or other.get("watchlist_company")
            out.pop(id(other), None)
        absorbed.update(idx)
    return [t for t in fresh if id(t) in out], already_reported



def already_see() -> dict:
    """Doc bo nho da-thay: {seen_at: {khoa: unix_ts lan cuoi thay}}.

    Dinh dang cu la list khoa tran — doc duoc ca hai, chuyen dan sang dict.
    """
    if not STATE.exists():
        return {}
    d = json.loads(STATE.read_text(encoding="utf-8")).get("seen_at", [])
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
    - Ghi de ca tep chi voi hai truong -> xoa mat `note` (ghi chu su co
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
    goc["updated_at"] = datetime.now(timezone.utc).isoformat()
    goc["seen_at"] = giu
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
    # LOW-253: buoc 2, LLM gom nhom cung su kien ma luat code bo sot, va so voi
    # tieu de da bao 3 ngay qua. Khoa da thay la standard_ify(tieu de) — chu
    # thuong, bo dau cau — van du de LLM doc. LLM loi thi giu nguyen buoc 1.
    prior = [k for k, ts in sorted(cu.items(), key=lambda kv: -kv[1])
             if ts >= now - SAME_STORY_LOOKBACK_SECONDS][:SAME_STORY_MAX_PRIOR]
    reported = []
    if moi:
        today = [t["title"] for t in moi]
        txts = [ask_same_story(today, prior) for _ in range(SAME_STORY_ASKS)]
        if all(x is not None for x in txts):
            truoc = len(moi)
            moi, reported = merge_same_story(moi, consensus_groups(txts, today, prior))
            print(f"  same_story: {truoc} -> {len(moi)} nhom moi, {len(reported)} nhom da bao "
                  f"({SAME_STORY_MODEL})", file=sys.stderr)
    for t in moi:
        # watchlist_company da duoc gather_duplicate tinh tren TUNG bien the truoc khi gop.
        t["watchlist"] = bool(t.get("watchlist_company"))

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
    # thuoc tep nay (audit 01/09). `outlet_count` du de danh gia do nong; danh sach
    # ten bao cap 3 (du cho source_note); `watchlist_company` trung y voi `watchlist`
    # thi bo. `chon` goc van dung nguyen cho write_timestamp ben duoi.
    xuat = []
    for t in chon:
        t2 = {k: v for k, v in t.items() if k not in ("watchlist_company", "seen_keys")}
        t2["outlets"] = t.get("outlets", [])[:3]
        xuat.append(t2)
    # BAT BUOC (luat Ong Chu 04/09/2026): tin watchlist (top brand nganh AI)
    # la PHAI co trong manifest cua Vera, tich luy sang hom sau neu sot.
    # MOT muc moi HANG moi NGAY (khong phai moi bai bao): Nvidia mua Hugging
    # Face co 3 bao thi Vera chon 1 bai la du. Chi hang LOI, hoac tin >= 2 bao.
    # Khop bang ten hang trong tieu de/tom tat cua Vera (keywords), khong theo link.
    if not a.lan_dau:
        nhom = {}
        for t in chon:
            hang = (t.get("watchlist_company") or "").lower()
            if not (t["watchlist"] and hang):
                continue
            if hang not in RANK_ERROR and (t.get("outlet_count") or 0) < 2:
                continue
            k = f"hang|{hang}|{t['date']}"
            # KHONG dung ten `cu`: do la bo nho da-thay (da_thay()) dung o cuoi
            # main cho write_timestamp. Ghi de no o day lam write_timestamp nhan None -> crash
            # sau khi da ghi --out, tuc Vera co tep ma moc khong duoc cap nhat
            # (tin bao lai hom sau). Bat 04/09/2026 khi chay thu scan_prepare.
            cu_nhom = nhom.get(k)
            if not cu_nhom or (t.get("outlet_count") or 0) > (cu_nhom.get("outlet_count") or 0):
                nhom[k] = t
        muc = [(k, f"{t['watchlist_company']}: {t['title']}", "watchlist",
                f"{t['outlet_count']} bao; {t['date']}", t.get("link", ""), [t["watchlist_company"]])
               for k, t in nhom.items()]
        so_moi = required.extra_many("vera", muc)
        print(f"  bat buoc: {len(muc)} tin watchlist, {so_moi} moi; tong dang cho "
              f"{len(required.read('vera'))} ({required.file('vera').name})", file=sys.stderr)

    ket = {"scanned_at": datetime.now(timezone.utc).isoformat(),
           "scanned_total": len(tin),
           "watchlist_count": sum(1 for t in chon if t["watchlist"]),
           "new_stories": xuat}
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
            print(f"  {dau} {t['date']}  ({t['feed_group']})  {t['outlet_count']} báo")
            print(f"        {t['title'][:100]}")
    # CHI danh dau tin DA DUA cho Vera (chon), khong phai tat ca tin quet duoc.
    # Truoc day danh dau het: ngay dot bien, phan bi van --top cat van vao seen
    # -> lan sau bi loc "da thay" -> khong bao gio toi Vera nua. Van an toan
    # thanh may xoa tin. Tin bi cat hom nay, mai van con moi thi van len duoc.
    # Nhom LLM xac nhan da bao (LOW-253) cung ghi lai, de lan sau buoc 1 loc
    # luon bang khoa, khong phai hoi LLM lai.
    write_timestamp({**cu, **{k: now for t in chon + reported for k in t["seen_keys"]}})


if __name__ == "__main__":
    main()
