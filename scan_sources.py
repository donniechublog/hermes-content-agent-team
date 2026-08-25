#!/usr/bin/env python3
"""Quet HN / Reddit / arXiv, loc, chong trung, tinh truoc 50/100 diem rubric.

Tat dinh, khong LLM. Ganh toan bo phan co hoc de Finn chi con lam dung viec
can tri tue: cham 2 thanh phan diem con lai (suc nang ky thuat, lien quan),
tom tat, va chon top N.

Hai thanh phan diem tinh duoc bang toan:
  - Do moi (30d): tuyen tinh theo tuoi bai, >72h thi loai thang
  - Do lan (20d): diem/upvote so voi TRUNG VI cua chinh nguon do trong lan quet

Moi nguon fetch doc lap — mot nguon chet khong keo do ca lan quet (Reddit tung
tra connection refused; luc do HN + arXiv van chay binh thuong).
"""
import argparse
import concurrent.futures as cf
import json
import re
import statistics
import sys
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path

import httpx

ROOT = Path.home() / "content-team"
STATE = ROOT / "state"
UA = "Mozilla/5.0 (compatible; donniechu-scout/1.0)"

MAX_AGE_HOURS = 72
SUBS = ["MachineLearning", "LocalLLaMA", "singularity", "OpenAI", "StableDiffusion"]
ARXIV_CATS = ["cs.AI", "cs.LG", "cs.CL", "cs.CV"]

# Loc so bo cho HN — HN co rat nhieu bai khong lien quan AI. Danh sach de rong
# tay, LLM van la nguoi quyet dinh cuoi cung ve do lien quan.
AI_HINTS = (
    "ai", "llm", "gpt", "claude", "gemini", "llama", "mistral", "qwen",
    "deepseek", "kimi", "grok", "model", "neural", "transformer", "diffusion",
    "inference", "quantization", "quantized", "gguf", "fine-tun", "finetun",
    "embedding", "rag", "agent", "openai", "anthropic", "huggingface",
    "pytorch", "tensor", "cuda", "gpu", "training", "benchmark", "dataset",
    "machine learning", "deep learning", "reasoning", "multimodal", "vision",
    "speech", "tts", "stable diffusion", "midjourney", "sora", "nvidia",
)


# Ten to chuc theo ten mien. `via` phai ghi NGUON TIN, khong phai kenh phat hien.
# Truoc day HN dat via="@nguoi_dang", nguoi do chi bam nut submit, con tin la cua
# hang lam ra no. Ai dua tin ve DeepSeek cung phai lay tu DeepSeek.
TEN_TO_CHUC = {
    "deepseek.com": "DeepSeek", "openai.com": "OpenAI",
    "anthropic.com": "Anthropic", "ai.meta.com": "Meta AI", "meta.com": "Meta",
    "deepmind.google": "Google DeepMind", "blog.google": "Google",
    "google.com": "Google", "mistral.ai": "Mistral",
    "qwenlm.github.io": "Qwen", "qwen.ai": "Qwen", "moonshot.ai": "Moonshot",
    "z.ai": "Z.ai", "zhipuai.cn": "Zhipu AI", "x.ai": "xAI",
    "nvidia.com": "NVIDIA", "huggingface.co": "Hugging Face",
    "github.com": "GitHub", "arxiv.org": "arXiv",
    "the-decoder.com": "The Decoder", "techcrunch.com": "TechCrunch",
    "theverge.com": "The Verge", "reuters.com": "Reuters",
    "bloomberg.com": "Bloomberg", "nytimes.com": "NYT",
    "techinasia.com": "Tech in Asia", "venturebeat.com": "VentureBeat",
    "simonwillison.net": "Simon Willison",
}


def nguon_goc(url: str) -> str:
    """Ten nguon tin, suy tu ten mien cua link."""
    try:
        from urllib.parse import urlparse
        host = (urlparse(url).netloc or "").lower().removeprefix("www.")
    except Exception:                                        # noqa: BLE001
        return ""
    if not host:
        return ""
    for mien, ten in TEN_TO_CHUC.items():
        if host == mien or host.endswith("." + mien):
            return ten
    goc = host.split(".")
    while len(goc) > 2 and goc[0] in ("api", "api-docs", "docs", "blog", "news",
                                      "www", "developer", "developers", "research"):
        goc = goc[1:]
    ten = goc[0] if goc else host
    return ten[:1].upper() + ten[1:]


def _is_ai_ish(text: str) -> bool:
    low = text.lower()
    return any(h in low for h in AI_HINTS)


def _age_hours(ts_epoch: float) -> float:
    return (time.time() - ts_epoch) / 3600.0


def score_recency(age_h: float) -> int:
    """30d neu duoi 24h, giam tuyen tinh toi 0 o moc 72h."""
    if age_h <= 24:
        return 30
    if age_h >= MAX_AGE_HOURS:
        return 0
    return int(round(30 * (MAX_AGE_HOURS - age_h) / (MAX_AGE_HOURS - 24)))


def score_spread(points: int, median: float) -> int:
    """20d khi gap doi trung vi cua nguon, 10d khi bang trung vi, 0 khi khong co."""
    if median <= 0:
        return 0
    ratio = points / median
    return max(0, min(20, int(round(ratio * 10))))


# ---------- cac nguon ----------

def fetch_hn(limit=40) -> list:
    out = []
    with httpx.Client(timeout=25, headers={"User-Agent": UA}) as c:
        ids = c.get("https://hacker-news.firebaseio.com/v0/topstories.json").json()
        for sid in ids[:limit]:
            try:
                it = c.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{sid}.json").json()
            except Exception:                                # noqa: BLE001
                continue
            if not it or it.get("type") != "story" or not it.get("title"):
                continue
            age = _age_hours(it.get("time", 0))
            if age > MAX_AGE_HOURS:
                continue
            title = it["title"]
            if not _is_ai_ish(title):
                continue
            out.append({
                "source": "hackernews",
                "title": title,
                "link": it.get("url") or f"https://news.ycombinator.com/item?id={sid}",
                "discussion": f"https://news.ycombinator.com/item?id={sid}",
                "points": it.get("score", 0),
                "comments": it.get("descendants", 0),
                "via": nguon_goc(it.get("url") or "") or "HackerNews",
                "nguoi_dang": "@" + it.get("by", "hn"),
                "age_hours": round(age, 1),
            })
    return out


def fetch_reddit(limit_per_sub=25) -> list:
    """Reddit HIEN KHONG TRUY CAP DUOC tu server nay.

    Chan doan (2026-08-20): www.reddit.com phan giai ve ::1 tren resolver cua
    may (127.0.0.53), con old./np. deu chuyen huong sang trang dang nhap. Day
    la chan o tang mang/tai khoan, khong phai loi code.

    Giu nguyen ham de bat lai ngay khi duong mang thong tro lai — khong dung
    thu thuat ne chan. Neu can Reddit gap, huong di dung la dang ky Reddit
    OAuth app va dung API chinh thuc co xac thuc.
    """
    out = []
    with httpx.Client(timeout=25, headers={"User-Agent": UA},
                      follow_redirects=True) as c:
        for sub in SUBS:
            try:
                data = c.get(
                    f"https://www.reddit.com/r/{sub}/hot.json?limit={limit_per_sub}"
                ).json()
            except Exception as e:                           # noqa: BLE001
                print(f"  [canh bao] Reddit r/{sub} loi: {type(e).__name__}",
                      file=sys.stderr)
                continue
            for child in data.get("data", {}).get("children", []):
                d = child.get("data", {})
                if d.get("stickied") or not d.get("title"):
                    continue
                age = _age_hours(d.get("created_utc", 0))
                if age > MAX_AGE_HOURS:
                    continue
                out.append({
                    "source": f"reddit/r/{sub}",
                    "title": d["title"],
                    "link": d.get("url_overridden_by_dest") or
                            ("https://www.reddit.com" + d.get("permalink", "")),
                    "discussion": "https://www.reddit.com" + d.get("permalink", ""),
                    "points": d.get("score", 0),
                    "comments": d.get("num_comments", 0),
                    "via": nguon_goc(d.get("url") or "") or ("r/" + sub),
                    "nguoi_dang": "r/" + sub,
                    "age_hours": round(age, 1),
                })
    return out


def fetch_arxiv(max_results=30) -> list:
    query = "+OR+".join(f"cat:{c}" for c in ARXIV_CATS)
    url = (f"https://export.arxiv.org/api/query?search_query={query}"
           f"&sortBy=submittedDate&sortOrder=descending&max_results={max_results}")
    out = []
    try:
        with httpx.Client(timeout=30, headers={"User-Agent": UA}) as c:
            root = ET.fromstring(c.get(url).text)
    except Exception as e:                                   # noqa: BLE001
        print(f"  [canh bao] arXiv loi: {type(e).__name__}", file=sys.stderr)
        return out
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for entry in root.findall("a:entry", ns):
        title = " ".join((entry.findtext("a:title", "", ns) or "").split())
        link = entry.findtext("a:id", "", ns)
        published = entry.findtext("a:published", "", ns)
        try:
            dt = datetime.strptime(published, "%Y-%m-%dT%H:%M:%SZ").replace(
                tzinfo=timezone.utc)
            age = (datetime.now(timezone.utc) - dt).total_seconds() / 3600
        except Exception:                                    # noqa: BLE001
            continue
        if age > MAX_AGE_HOURS:
            continue
        out.append({
            "source": "arxiv",
            "title": title,
            "link": link,
            "discussion": link,
            "points": 0,          # arXiv khong co chi so lan truyen
            "comments": 0,
            "via": "arxiv",
            "age_hours": round(age, 1),
        })
    return out


# ---------- chong trung ----------

def _norm_url(u: str) -> str:
    u = re.sub(r"^https?://(www\.)?", "", u or "").rstrip("/")
    return re.sub(r"[?#].*$", "", u).lower()


def seen_keys() -> set:
    """Gom URL da tung xuat hien trong cac manifest truoc va cac draft da tao."""
    keys = set()
    for f in STATE.glob("finn_candidates_*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            continue
        for it in data.get("items", []):
            if it.get("link"):
                keys.add(_norm_url(it["link"]))
    for f in (ROOT / "drafts").glob("*.json"):
        try:
            d = json.loads(f.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            continue
        if d.get("source_url"):
            keys.add(_norm_url(d["source_url"]))
    return keys


# ---------- anh minh hoa ----------

# Nhung duong khong bao gio co anh dung duoc — khoi mat mot luot tai
KHONG_CO_ANH = re.compile(r"\.pdf($|\?)|arxiv\.org/(abs|pdf)/|news\.ycombinator\.com/item", re.I)

# Anh mac dinh cua nen tang, khong dai dien noi dung bai — lay ve chi to giong nhau
ANH_RAC = re.compile(
    r"(logo|favicon|default[-_]?og|placeholder|avatar|sprite|1x1|pixel|"
    r"twitter[-_]card[-_]default|social[-_]?default)", re.I)


def _anh_cua(url: str, timeout=8) -> str:
    """Lay og:image (hoac twitter:image) cua mot bai. Hong thi tra chuoi rong.

    Vi sao can: truoc day khong co buoc nay, `image_url` LUON None, nen vai dung anh
    lan nao cung phai tu ve SVG — moi the anh nhin giong het nhau. Da kiem 23/23
    tin trong ba ngay deu khong co anh.
    """
    if not url or KHONG_CO_ANH.search(url):
        return ""
    try:
        r = httpx.get(url, timeout=timeout, follow_redirects=True,
                      headers={"User-Agent": UA, "Accept-Encoding": "gzip, deflate"})
        if r.status_code != 200 or "html" not in r.headers.get("content-type", ""):
            return ""
        # Chi doc phan dau: the og:image luon nam trong <head>
        html = r.text[:200_000]
    except Exception:                                        # noqa: BLE001
        return ""
    for prop in ("og:image:secure_url", "og:image", "twitter:image",
                 "twitter:image:src"):
        m = re.search(
            r"""<meta[^>]+(?:property|name)\s*=\s*["']""" + re.escape(prop)
            + r"""["'][^>]*\scontent\s*=\s*["']([^"']+)["']""", html, re.I)
        if not m:
            m = re.search(
                r"""<meta[^>]+content\s*=\s*["']([^"']+)["'][^>]*(?:property|name)\s*=\s*["']"""
                + re.escape(prop) + r"""["']""", html, re.I)
        if m:
            src = m.group(1).strip()
            if src.startswith("//"):
                src = "https:" + src
            if src.startswith("http") and not ANH_RAC.search(src):
                return src
    return ""


def gan_anh(items: list, workers=8) -> int:
    """Gan image_url cho tung ung vien, tai song song. Tra ve so bai co anh."""
    with cf.ThreadPoolExecutor(max_workers=workers) as ex:
        for it, anh in zip(items, ex.map(lambda i: _anh_cua(i.get("link", "")), items)):
            it["image_url"] = anh or None
    return sum(1 for i in items if i.get("image_url"))


def main():
    ap = argparse.ArgumentParser(
        description="Quet nguon, chong trung, tinh truoc diem co hoc cho Finn")
    ap.add_argument("--out", help="Ghi JSON ra file thay vi stdout")
    ap.add_argument("--top", type=int, default=40,
                    help="So ung vien toi da giu lai (mac dinh 40)")
    ap.add_argument("--khong-lay-anh", action="store_true",
                    help="Bo qua buoc tai og:image (nhanh hon, nhung vai dung anh se thieu goi y)")
    a = ap.parse_args()

    print("Dang quet...", file=sys.stderr)
    items = []
    for name, fn in (("HackerNews", fetch_hn), ("Reddit", fetch_reddit),
                     ("arXiv", fetch_arxiv)):
        got = fn()
        print(f"  {name}: {len(got)} bai", file=sys.stderr)
        items.extend(got)

    seen = seen_keys()
    fresh = [it for it in items if _norm_url(it["link"]) not in seen]
    print(f"  chong trung: bo {len(items) - len(fresh)} bai da xu ly",
          file=sys.stderr)

    # Trung vi tinh RIENG cho tung nguon — so sanh trong cung ho moi cong bang
    by_source = {}
    for it in fresh:
        by_source.setdefault(it["source"], []).append(it["points"])
    medians = {s: statistics.median(v) if v else 0 for s, v in by_source.items()}

    for it in fresh:
        it["score_recency"] = score_recency(it["age_hours"])
        if it["source"] == "arxiv":
            # arXiv khong co upvote — cham 0 se day moi bai arXiv xuong day du
            # rubric coi day la nguon chinh. Dat muc trung tinh 10/20 va de
            # Finn quyet dinh bang 2 thanh phan diem con lai.
            it["score_spread"] = 10
            it["spread_note"] = "arXiv khong co chi so lan truyen — dat trung tinh 10/20"
        else:
            it["score_spread"] = score_spread(it["points"], medians[it["source"]])
        it["score_partial"] = it["score_recency"] + it["score_spread"]
        it["source_median_points"] = medians[it["source"]]

    fresh.sort(key=lambda x: x["score_partial"], reverse=True)
    fresh = fresh[: a.top]

    if not a.khong_lay_anh:
        t0 = time.time()
        co = gan_anh(fresh)
        print(f"  anh minh hoa: {co}/{len(fresh)} bai co og:image "
              f"({time.time() - t0:.0f}s)", file=sys.stderr)
    else:
        for it in fresh:
            it.setdefault("image_url", None)

    result = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "note": ("score_recency (0-30) va score_spread (0-20) da tinh san bang "
                 "cong thuc. Finn chi can cham score_technical (0-30) va "
                 "score_relevance (0-20), roi cong lai thanh score tong."),
        "candidates": fresh,
    }
    out_json = json.dumps(result, ensure_ascii=False, indent=2)
    if a.out:
        Path(a.out).write_text(out_json, encoding="utf-8")
        print(f"  ghi {len(fresh)} ung vien -> {a.out}", file=sys.stderr)
        print(a.out)
    else:
        print(out_json)


if __name__ == "__main__":
    main()
