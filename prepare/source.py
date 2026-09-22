#!/usr/bin/env python3
"""PHA NGUON: nap tu lieu bai goc, ung vien anh tinh/social, ten rieng, Commons.

Tach tu image_prepare.py 09/09/2026 (audit A1, di chuyen thuan — than ham giu y nguyen).
"""
import re
import sys
from pathlib import Path

import schema
import state_paths

from prepare.common import DRAFTS, GNEWS, _read_json, _write_json


def _summary_from_img_json(draft_id: str) -> dict:
    """Tom tat + source_note nam trong body task (img.json). Doc lai tu do thay
    vi bat vai chep — mot nguon, khong lech."""
    d = _read_json(DRAFTS / f"{draft_id}.img.json", {}) or {}
    body = d.get("body", "")
    ra = {}
    for khoa, nhan in (("summary", "Tom tat"), ("source_note", "Nguon")):
        if d.get(khoa):                         # approve_service ghi thang khoa nay
            ra[khoa] = str(d[khoa]).strip()
            continue
        m = re.search(rf"^{nhan}: (.*)$", body, re.M)   # sidecar cu: boc tu body
        ra[khoa] = (m.group(1).strip() if m else "")
    ra["remakes"] = int(d.get("remakes", 0) or 0)
    ra["image_role"] = d.get("image_role", "")
    return ra


# ---- 1. nguon ---------------------------------------------------------------
def load_source(draft_id: str, meta: dict, state: Path, phien=None) -> tuple:
    """Tra ve (nguon_dict, nguon_path, link_real). Giai ma link Google News neu
    can va ghi nguoc vao nguon json + meta de moi vai sau cung dung link that."""
    import article_sources
    p = state_paths.article_source_file(state, draft_id)
    link = meta.get("source_url", "")
    nguon = _read_json(p) or {"title": meta.get("title", ""), "source_url": link,
                             "pages": [{"url": link, "kind": "article",
                                        "title": meta.get("title", "")}]}
    link_goc = nguon.get("source_url") or link
    if GNEWS in link_goc:
        that = article_sources.resolve_code_gnews(link_goc, phien=phien)
        if that:
            print(f"[nguon] giai ma Google News -> {that[:90]}", file=sys.stderr)
            nguon["gnews_url"] = link_goc
            nguon["source_url"] = that
            for t in nguon.get("pages", []):
                if t.get("url") == link_goc:
                    t["url"] = that
            _write_json(p, nguon)
            link_goc = that
            if meta.get("source_url") != that:
                meta["source_url"] = that
                # TRON vao ban TREN DIA hien tai, khong ghi de nguyen `meta` (co
                # the da cu di so voi luc goi ham nay — pipeline chay lau, va
                # `.meta.json` la tep BA TIEN TRINH cung ghi khong khoa chung:
                # approve_service, engine nen, va blackboard cua hermes ghi
                # `root_task` rieng, xem docstring env_load.ghi_json). Ghi de ca
                # dict y het loi merge_meta da sua cho approve_pick.py —
                # ghi de mat `root_task` neu blackboard vua ghi xong trong luc
                # tien trinh nay con dang giai ma Google News.
                p_meta = DRAFTS / f"{draft_id}.meta.json"
                _write_json(p_meta, schema.merge_meta(
                    _read_json(p_meta, {}), {"source_url": that}))
    # Tieu de TIENG ANH cua bai that: tin cua Vera/Nova mang tieu de tieng Viet,
    # tim Google News/RSS bang tieu de do ra rong. Lay <title>/og:title cua trang
    # goc mot lan, ghi vao nguon json de article_images/material tim bao khac bang no.
    return nguon, p, link_goc


def _title_page(url: str) -> str:
    """og:title cua bai goc — mot ban duy nhat o article_sources (co luat: tieu de
    tieng Viet thi tra rong, khong duoc dem di tim kiem)."""
    import article_sources
    return article_sources._title_page(url)


def candidate_social(link: str, wd: Path) -> list:
    """Anh CUA CHINH post (X/Instagram/Facebook) lam ung vien hang dau.

    Vi sao khong de duong tim anh thuong lo: post mang xa hoi chan khach chua
    dang nhap, browser_pass mo facebook.com chi thay tuong dang nhap, con
    article_images.find di tim "bao khac" cho mot post ca nhan thi ra rac. Anh nguoi ta
    dang kem bai CHINH LA anh that cua tin do — Ong Chu chot 08/09/2026.

    Diem 95: cao hon moi nguon khac de no dung dau khi download_and_filter cat bot, nhung
    van de xep_hang (anh bang xep hang, khong di qua download_and_filter) dung tren.
    Tai han ve dia thay vi giu link CDN: link CDN co tham so het han (`oe=`).
    """
    import social_post
    if not social_post.is_social(link):
        return []
    log = lambda t: print(f"[social] {t}", file=sys.stderr)   # noqa: E731
    d = social_post.read(link, tai_ve=wd / "social", in_log=log)
    if not d:
        # crawl-queue hong van lay duoc anh post X tu chinh trang post (get_source).
        d = {"author": "", "link": link, "media": social_post.x_photos(link, wd / "social", log)}
    cands = []
    for i, m in enumerate(d["media"], 1):
        if m["type"] != "image" or not m["file_path"]:
            continue
        cands.append({"image_url": m["file_path"], "file_path": m["file_path"],
                      "alt": f"ảnh {i} trong post của {d['author']}".strip(),
                      "source": "social_post", "page_url": d["link"], "score": 95})
    print(f"[social] {len(cands)} anh that tu chinh post", file=sys.stderr)
    return cands


# LOW-355 (Ong Chu 22/09/2026, tin Grok 4.7): *"thay vi dung hinh cap tu tweet, sao ban ko vao
# chinh cai tweet duoc retweet co hinh goc chat luong cao"*. Slide dung anh Futu tu chup tweet
# (611x734, giao dien dich tieng Trung) trong khi decrypt.co — cung nam trong nguon cua draft —
# nhung link x.com/elonmusk/status/2102071804495872374, tu do get_source tai ve bieu do goc
# 3062x1960. Bao nhung tweet bang <blockquote class="twitter-tweet"><a href=".../status/<id>">
# nen link status nam san trong HTML tinh.
EMBEDDED_TWEET_MAX = 4
EMBEDDED_TWEET_MAX_AGE_DAYS = 14
EMBEDDED_TWEET_MAX_PAGES = 12
EMBEDDED_TWEET_SCORE = 90            # duoi anh cua CHINH post nguon (95), tren anh bao
_X_STATUS_IN_HTML = re.compile(
    r"(?:x|twitter)\.com/(\w{1,15})/status(?:es)?/(\d{15,20})", re.I)
_TWITTER_EPOCH_MS = 1288834974657


def tweet_time(tweet_id: str) -> float:
    """Gio dang (epoch giay) doc tu chinh id tweet (snowflake) — khong can goi X."""
    return (((int(tweet_id) >> 22) + _TWITTER_EPOCH_MS) / 1000.0)


def embedded_tweet_urls(pages_html: list, now: float, skip_urls: tuple = ()) -> list:
    """Link post X nhung trong cac trang bao, MOI NHAT truoc, bo tweet cu hon
    `EMBEDDED_TWEET_MAX_AGE_DAYS` (bao hay nhung lai tweet cu lam boi canh). Ham thuan."""
    bo = {m.group(2) for u in skip_urls for m in [_X_STATUS_IN_HTML.search(u or "")] if m}
    theo_id: dict = {}
    for html in pages_html:
        for handle, tid in _X_STATUS_IN_HTML.findall(html or ""):
            if tid in bo or tid in theo_id:
                continue
            if now - tweet_time(tid) > EMBEDDED_TWEET_MAX_AGE_DAYS * 86400:
                continue
            theo_id[tid] = f"https://x.com/{handle}/status/{tid}"
    return [theo_id[t] for t in sorted(theo_id, key=int, reverse=True)][:EMBEDDED_TWEET_MAX]


def candidate_embedded_tweets(source_pages: list, link: str, wd: Path) -> list:
    """Anh GOC cua cac tweet ma bao nguon nhung lai — qua `social_post.x_photos` (get_source,
    ban `name=orig`), khong phai anh bao tu chup lai tweet. Vision van chot co lien quan."""
    import concurrent.futures as cf
    import time
    import article_images
    import social_post
    log = lambda t: print(f"[x_goc] {t}", file=sys.stderr)   # noqa: E731
    urls = [u for u in dict.fromkeys([link] + [t.get("url") for t in source_pages])
            if u and not social_post.is_social(u)][:EMBEDDED_TWEET_MAX_PAGES]

    def _html(u):
        try:
            r = article_images._download(u, 20)
            return r.text[:800_000] if r.status_code == 200 else ""
        except Exception:                                    # noqa: BLE001
            return ""
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        pages_html = list(ex.map(_html, urls))
    tweets = embedded_tweet_urls(pages_html, time.time(), skip_urls=(link,))
    if not tweets:
        log(f"khong bao nguon nao nhung tweet ({len(urls)} trang)")
        return []
    log(f"{len(tweets)} tweet nhung trong bao nguon: {', '.join(tweets)}")

    def _photo(u):
        tid = _X_STATUS_IN_HTML.search(u).group(2)
        return u, social_post.x_photos(u, wd / "social" / f"x_{tid}", log)
    with cf.ThreadPoolExecutor(max_workers=4) as ex:
        ket_qua = list(ex.map(_photo, tweets))
    cands = []
    for u, media in ket_qua:
        for m in media:
            handle = _X_STATUS_IN_HTML.search(u).group(1)
            cands.append({"image_url": m["file_path"], "file_path": m["file_path"],
                          "alt": f"ảnh gốc trong tweet của @{handle}",
                          "source": "embedded_tweet", "page_url": u, "score": EMBEDDED_TWEET_SCORE,
                          # Do hoa CO CHU Y (bieu do/bang chinh chu dang), khong phai logo lot tu
                          # <img> bao: chay that 22/09 bieu do CursorBench 3062x1960 nen trang 69%
                          # bi cong `graphic_logo` loai ("the thuong hieu").
                          "graphic_allowed": True})
    log(f"{len(cands)} anh goc tu tweet nhung")
    return cands


def candidate_static(title: str, link: str, nguon_path: Path, title_en: str = "") -> list:
    """article_images.find tren bo nguon cua Finn; it qua thi tim rong them (bao khac,
    bang tieu de tieng Anh cua bai that)."""
    import article_images
    ds = article_images.find(title, link, sau_rong=True, tu_nguon=str(nguon_path))
    if len(ds) < 4:
        them = article_images.find(title_en or title, link, sau_rong=True, tu_nguon=None)
        co = {c["image_url"] for c in ds}
        ds += [c for c in them if c["image_url"] not in co]
    return ds


def commons_images(tu_khoa: str, so: int = 4) -> list | None:
    """Anh that tren Wikimedia Commons (tru so, san pham, su kien) cho tin mong
    anh — IMAGE_RULES muc 1.2 ke Commons la nguon hop le. Chi goi khi bai + bao khac
    khong du 5 anh. Loai SVG/logo (mime + _graphic o buoc tai).

    Tra None khi HONG VI MOI TRUONG (mang, API loi) — KHAC voi [] (da chay het,
    khong ra anh nao). Nguoi goi phai tu phan biet hai truong hop nay (quy uoc
    "hong phai lo", audit_content_team C1)."""
    import scan_common
    pages = scan_common.ask_commons(tu_khoa, so=14, loai_logo=False)   # mot ban (ADF-r2-16)
    if pages is None:
        return None
    ra = []
    for pg in pages.values():
        ii = (pg.get("imageinfo") or [{}])[0]
        w, h = ii.get("width", 0), ii.get("height", 0)
        if min(w, h) < 600 or ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        ten = (pg.get("title") or "").replace("File:", "")
        if tu_khoa.lower() not in ten.lower():       # tim mo cua Commons hay lac de
            continue
        ra.append({"image_url": ii.get("thumburl") or ii.get("url"), "alt": "Commons: " + ten, "og": False,
                   "source": "commons", "page_url": "https://commons.wikimedia.org/wiki/File:" + ten.replace(" ", "_"),
                   "w": w, "h": h, "score": 30})
    ra.sort(key=lambda c: -(c["w"] * c["h"]))
    return ra[:so]


# Tu tieng Anh CHUNG hay bi nham la ten rieng vi dung dau cau/sau dau hai cham
# (viet hoa theo chinh ta tieng Anh, khong phai vi la ten rieng) — "Foundry
# power balance flips: Samsung's choice..." -> "Foundry" mot minh ra Commons
# toan xuong duc kim loai Milwaukee/quan bar ten "Foundry Live", khong lien
# quan gi ban dan (Ong Chu 08/09/2026, cung loai loi voi "Gimlet" -> cocktail
# 05/09/2026 nhung khac nguyen nhan: do la tu hiem gap tu vung chung, day la tu
# thuong dung nhung ro ngau nhien dung dau cau/menh de). RIENG cho ham nay —
# KHONG gop vao article_sources.FROM_EMPTY_QUERY vi set do con dung loc tu truy van
# bao khac, noi "foundry" la tu khoa TOT can giu lai.
FROM_COMMON_MARK_SENTENCE = {
    "foundry", "power", "choice", "chip", "chips", "deal", "deals", "report",
    "study", "data", "demand", "supply", "growth", "boom", "wave", "race",
    "war", "threat", "risk", "rise", "fall", "shift", "era", "future",
    "market", "markets", "jobs", "job", "apocalypse", "crisis", "battle",
    "fight", "surge", "slump", "crunch", "squeeze", "gap", "divide", "bet",
    "bets", "bubble", "boost", "cut", "cuts", "push", "plan", "plans",
}


# ---- bang chung ten rieng tu THAN BAI (LOW-222, 17/09/2026) -------------------
# Truoc: moi tu viet hoa >= 4 chu trong tieu de la "ten rieng", chan bang danh
# sach tu tay (FROM_COMMON_MARK_SENTENCE + dong tu "raises/nabs..."). Tieu de
# title-case viet hoa MOI tu nen "Banks" (tin Blackstone/Alphabet), "OpenAI
# Considers", "Financing" thanh hang — Commons ra ca si Banks, Yandex/bao thuc
# the/vision deu hoi sai ten. Moi su co them vai tu vao danh sach, khong bao gio du.
# Nay (luat Ong Chu 17/09: "xu ly bang code toi da"): hoi chinh THAN BAI cua tin.
# Ten rieng that duoc viet hoa o giua cau van; tu thuong thi viet thuong
# ("banks", "considering", "financing"). Khong co than bai dang tin -> giu cach
# tach cu, khong doan.
_STORY_TEXT = ""
_EVIDENCE_MIN_CHARS = 400
_SENTENCE_END = set(".!?:\n•—–|")
_FUNCTION_WORDS = {"the", "a", "an", "of", "to", "in", "on", "for", "and", "or", "with", "by", "at",
                   "as", "from", "into", "via", "vs", "than", "its", "is", "are", "be"}
# Bien cua token: khong tinh chu nam trong URL/ten mien/tu ghep gach noi/handle
# ("claude.ai", "claude-opus-4", "@garrytan") — do la ma, khong phai van xuoi.
_TOKEN_LEFT = r"(?<![A-Za-z0-9._/@-])"
_TOKEN_RIGHT = r"(?![A-Za-z0-9_@-]|\.[A-Za-z])"


def set_story_text(text: str) -> None:
    """Than bai tieng Anh cua tin DANG CHAY trong tien trinh nay — bien tien trinh
    giong `role.set_active_role`: moi tien trinh engine xu ly dung MOT draft
    (`approve_pick` goi `image_prepare.py` bang subprocess). Goi "" de xoa."""
    global _STORY_TEXT
    _STORY_TEXT = text or ""


def story_text() -> str:
    return _STORY_TEXT


def _is_title_case(text: str) -> bool:
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'’-]*", text or "") if w.lower() not in _FUNCTION_WORDS]
    return len(words) >= 3 and sum(w[0].isupper() for w in words) / len(words) >= 0.7


def _enclosing_sentence(body: str, i: int) -> str:
    left = max(body.rfind("\n", 0, i), body.rfind(". ", 0, i), body.rfind("? ", 0, i), body.rfind("! ", 0, i))
    ends = [e for e in (body.find("\n", i), body.find(". ", i), body.find("? ", i), body.find("! ", i)) if e != -1]
    return body[left + 1 if left >= 0 else 0: min(ends) if ends else len(body)]


def _casing_counts(word: str, body: str) -> tuple:
    """(viet hoa giua cau, viet hoa dau cau, viet thuong) cua `word` trong than bai.
    Dong kieu headline (tit bai khac, menu) bi bo qua khi dem viet hoa. Viet
    thuong tinh ca bien the -s/-es/-ed/-ing ("Considers" <- "considering")."""
    upper_mid = upper_start = 0
    for m in re.finditer(_TOKEN_LEFT + re.escape(word) + _TOKEN_RIGHT, body):
        if _is_title_case(_enclosing_sentence(body, m.start())):
            continue
        before = body[:m.start()].rstrip(" \t \"'“‘(")
        if before and before[-1] not in _SENTENCE_END:
            upper_mid += 1
        else:
            upper_start += 1
    low = word.lower()
    stems = {low} | {low[: -len(suf)] for suf in ("ing", "ed", "es", "s")
                     if low.endswith(suf) and len(low) - len(suf) >= 3}
    lower = sum(len(re.findall(_TOKEN_LEFT + re.escape(st) + r"(?:s|es|ed|ing)?" + _TOKEN_RIGHT, body))
                for st in stems)
    return upper_mid, upper_start, lower


def _looks_like_name(word: str) -> bool:
    """Hoa ben trong tu (OpenAI, DeepSeek) hoac viet tat (NVIDIA, LLMs) — tu no la ten."""
    return bool(re.search(r"[a-z][A-Z]|^[A-Z0-9]{2,}$|^[A-Z]{2,}[a-z]", word))


def _body_is_about_story(title: str, body: str) -> bool:
    """Than bai co that la bai cua tin khong (trang chan bot, trang loi thi khong)."""
    if len(body or "") < _EVIDENCE_MIN_CHARS:
        return False
    words = {w.lower() for w in re.findall(r"[A-Za-z][A-Za-z0-9]{3,}", title or "")
             if w.lower() not in _FUNCTION_WORDS}
    if not words:
        return False
    hit = sum(1 for w in words if re.search(r"(?<![A-Za-z])" + re.escape(w) + r"(?![A-Za-z])", body, re.I))
    return hit >= 2 and hit / len(words) >= 0.3


def _keep_by_evidence(word: str, body: str, title_case: bool) -> bool:
    if _looks_like_name(word):
        return True
    upper_mid, upper_start, lower = _casing_counts(word, body)
    if lower == 0 and upper_mid + upper_start > 0:
        return True
    if upper_mid > 0 and upper_mid >= lower:
        return True
    if lower > 0:
        return False
    # Vang mat khoi than bai: tieu de sentence-case thi viet hoa giua tit la bang
    # chung; tieu de title-case thi viet hoa khong noi gi -> bo.
    return not title_case


def _title_clusters(tieu_de: str) -> list:
    """Cum chu viet hoa lien tiep cua tieu de (cach tach cu), nhung TACH o dau
    cau `: ; , |`, gach ngang tach menh de va so huu cach — "Intel, AMD",
    "Nvidia’s Huang" la HAI ten, khong phai mot."""
    import article_sources
    # Hau to site (" · Hugging Face") khong phai ten rieng cua tin (LOW-35):
    # no tung thanh tu khoa Commons va ra "Octopus' Hugging Face.jpg".
    t = article_sources.strip_site_suffix(re.sub(r"^\[[^\]]{1,20}\]\s*", "", tieu_de or ""))
    t = re.sub(r"(\w)[’']s\b", r"\1 |", t)
    ra = []
    for segment in re.split(r"[:;,|]|\s[–—-]\s", t):
        ws = re.sub(r"[\$\"'()\[\]]", " ", segment).split()
        i = 0
        while i < len(ws):
            w = ws[i]
            if w[:1].isupper() and w.isalpha() and len(w) >= 4 and w.lower() not in article_sources.FROM_EMPTY_QUERY \
                    and w.lower() not in FROM_COMMON_MARK_SENTENCE:
                cum = [w]
                j, da_qua_so = i + 1, False
                while j < len(ws) and len(cum) < 3:
                    w2 = ws[j]
                    if w2[:1].isupper() and w2.isalpha() and w2.lower() not in article_sources.FROM_EMPTY_QUERY \
                            and w2.lower() not in ("raises", "nabs", "drops", "launches", "unveils", "forecasts"):
                        cum.append(w2)
                        j += 1
                        da_qua_so = False
                    elif not da_qua_so and re.fullmatch(r"[0-9][0-9a-zA-Z]*", w2):
                        # So/ma phien ban xen giua chinh ten san pham ("Snapdragon 8
                        # Elite", "GPT-4 Turbo") — bo qua token nay (khong dua vao
                        # ten hien thi) nhung KHONG cat cum, de tu hoa ke tiep van
                        # duoc gop chung MOT ten thay vi bi doc thanh mot "hang" rieng
                        # gia (LOW-176: "Snapdragon 8 Elite" tung ra hai muc "Qualcomm"
                        # va "Elite" — "Elite" la hang bia).
                        j += 1
                        da_qua_so = True
                    else:
                        break
                cum_ten = " ".join(cum)
                if cum_ten not in ra:
                    ra.append(cum_ten)
                i = j
            else:
                i += 1
    return ra


def all_proper_nouns(tieu_de: str, body: str | None = None) -> list:
    """TAT CA cum ten rieng trong tieu de, theo thu tu xuat hien — khong dung
    lai o cum DAU TIEN nhu `_leading_proper_noun` (LOW-176, 16/09/2026: tin
    hai hang "Anthropic ra tich hop Salesforce" chi ra duoc "Anthropic" lam
    tu khoa, nen ca vong anh thuong hieu lan cau hoi vision deu khong bao gio
    biet toi Salesforce — ma anh dung chu de nhat cua tin lai la anh su kien
    cua CHINH Salesforce).

    LOW-222: `body` (mac dinh = `story_text()` cua tien trinh) la than bai cua
    tin. Co than bai dang tin thi moi tu cua cum phai qua bang chung viet hoa/
    viet thuong trong bai; cum bi cat ve phan co bang chung ("OpenAI Considers"
    -> "OpenAI", "Banks" bi bo). Khong co thi tra dung cach tach cu."""
    clusters = _title_clusters(tieu_de)
    body = story_text() if body is None else (body or "")
    if not _body_is_about_story(tieu_de, body):
        return clusters
    import article_sources
    for echo in {tieu_de, article_sources.strip_site_suffix(tieu_de or "")}:
        if echo:
            body = body.replace(echo, " ")        # tit bai in lai trong trang khong phai bang chung
    title_case = _is_title_case(tieu_de)
    names = []

    def _add(name: str) -> None:
        if name and name not in names:
            names.append(name)

    for cluster in clusters:
        words = cluster.split()
        if len(words) > 1:
            upper_mid, upper_start, lower = _casing_counts(cluster, body)
            if upper_mid + upper_start > lower:
                _add(cluster)
                continue
        run = []
        for word in words + [None]:
            if word is not None and _keep_by_evidence(word, body, title_case):
                run.append(word)
            else:
                _add(" ".join(run))
                run = []
    return names


def _leading_proper_noun(tieu_de: str) -> str:
    """Cum ten rieng dau tieu de (hang/san pham) lam tu khoa Commons: lay CAC TU
    VIET HOA LIEN TIEP ("Gimlet Labs", "Thinking Machines"), khong chi mot tu —
    "Gimlet" mot minh ra cocktail (05/09/2026). Bo the "[News]" dau tieu de.

    MOT trong (co the nhieu) cum ten rieng cua tieu de — xem `all_proper_nouns`
    khi can CA cac cum con lai (LOW-176)."""
    ra = all_proper_nouns(tieu_de)
    return ra[0] if ra else ""
