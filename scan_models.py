#!/usr/bin/env python3
"""Quet model MOI RA MAT — tat dinh, khong LLM. Viec cua Nova (profile radar/nova).

Khac Finn: Finn quet HN/Reddit/arXiv, tuc chi thay tin KHI DA CO NGUOI BAN LUAN.
Model release khong can cho thao luan moi dang gia — luc bao chi viet thi model da
len so dang ky vai ngay roi. Nen o day doc thang SO DANG KY.

Ba nguon, moi nguon doc lap (mot nguon chet khong keo do ca lan quet):

  1. OpenRouter /api/v1/models — 400+ model, MOI model deu co moc `created`, kem
     gia in/out, context, co reasoning. Phat hien model moi = phep tru tap hop
     tren ID, khong can LLM, khong the trung.
  2. Catalog cua 9router — tra loi cau thuc dung hon: "model moi nao HOM NAY ta
     goi duoc ngay", vi no da loc theo tai khoan dang co.
  3. lmarena.ai/leaderboard — bang xep hang. Du lieu nam trong payload RSC cua
     Next.js (self.__next_f), phai giai ma chuoi JS roi moi raw_decode duoc.
     Trang con /leaderboard/image va /video tai bang JS nen RONG — phai lay tu
     trang chinh, o do co ca `rankByModality` cho anh va video.

Uu tien (Ong Chu chot): frontier My, top 5 Trung Quoc, top tao anh, top tao video.

Dung:
    venv/bin/python scan_models.py                 # bao model moi tu lan quet truoc
    venv/bin/python scan_models.py --lan-dau       # khoi tao moc, khong bao gi
    venv/bin/python scan_models.py --ngay 7        # coi la moi neu ra trong 7 ngay
"""
import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

import env_load

STATE = env_load.state_dir() / "models_seen.json"
UA = "Mozilla/5.0 (compatible; donniechu-scout/1.0)"

OPENROUTER = "https://openrouter.ai/api/v1/models"
CATALOG = "https://hermes-agent.nousresearch.com/docs/api/model-catalog.json"
ARENA = "https://lmarena.ai/leaderboard"
# Bang Code Arena WebDev — nam o trang rieng, payload khac bang text. Su co
# 04/09/2026: qwen3.8-max-0902 vao #1 WebDev (1691 Elo, tren Fable 5) ngay 02/09
# ma Nova bao "khong model nao vao/leo hang" vi chi doc text/anh/video.
ARENA_WEBDEV = "https://arena.ai/leaderboard/code/webdev"
# Trang cham diem — theo sat MOI hang, ke ca Anthropic va Meta (hai hang khong
# co RSS). Ong Chu chot: bam vao trang cham diem thay vi bam theo tung hang.
# Payload RSC chua 616 model voi ~80 truong: releaseDate (phu 616/616),
# modelCreatorCountry (615/616), isOpenWeights (616/616), codingIndex,
# agenticIndex, terminalbenchHard, cacheHitPrice, licenseName.
AA = "https://artificialanalysis.ai/leaderboards/models"

# RSS cua hang — bat nhung su kien KHONG hien ra o so dang ky: mo ma nguon, doi
# giay phep, cong bo benchmark. Da do song 21/08: Anthropic va Meta KHONG co RSS
# (404 moi duong thu), model moi cua ho van hien o OpenRouter nen khong mat tin.
# Qwen co feed hop le nhung bai moi nhat tu 9/2025 — feed chet, da bo.
RSS_HANG = [
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Google DeepMind", "https://deepmind.google/blog/rss.xml"),
    ("HuggingFace", "https://huggingface.co/blog/feed.xml"),
    ("Mistral", "https://mistral.ai/rss.xml"),
]

# Repo co ban phat hanh thuong bao model moi duoc ho tro TRUOC ca thong cao
GITHUB_REPOS = ["vllm-project/vllm", "ggml-org/llama.cpp", "huggingface/transformers"]

# Tu khoa loc tin: chi giu bai co ve lien quan model/ma nguon mo
TU_KHOA_TIN = ("model", "open-source", "open source", "open-weight", "open weight",
               "release", "launch", "introducing", "benchmark", "swe-bench",
               "weights", "apache", "mit license", "available now")

# Cac hang duoc uu tien, chia theo vung. Doi chieu bang truong `organization`
# cua arena va tien to ID cua OpenRouter.
HANG_MY = {"openai", "anthropic", "google", "google-deepmind", "meta", "meta-llama",
           "xai", "x-ai", "microsoft", "nvidia", "mistralai", "mistral", "amazon",
           "cohere", "ai21", "perplexity", "luma-ai", "bfl", "ideogram", "runway",
           "liquid", "recraft", "stability", "pika", "openrouter", "inception"}
HANG_TQ = {"deepseek", "moonshot", "moonshotai", "qwen", "alibaba", "zai", "z-ai",
           "zhipuai", "minimax", "bytedance", "tencent", "baidu", "01-ai", "01ai",
           "stepfun", "wan", "kuaishou", "baichuan", "inclusionai", "skywork",
           "hunyuan", "seed", "iflytek", "sensetime", "kling", "vidu"}

BIG = 9007199254740991          # arena dung so nay lam "khong xep hang"


def _get(url: str, timeout=45) -> httpx.Response:
    # KHONG xin brotli. May chu cua OpenAI tra ve luong brotli ma bo giai nen cua
    # httpx nghen giua chung ("decoder process called with data when
    # can_accept_more_data() is False") — feed hong han, khong phai loi encoding.
    # Bo 'br' khoi Accept-Encoding thi may chu chuyen sang gzip va doc binh thuong.
    return httpx.get(url, timeout=timeout, follow_redirects=True,
                     headers={"User-Agent": UA,
                              "Accept-Encoding": "gzip, deflate"})


def vung_cua(org: str) -> str:
    """Khop ca ten day du lan tien to — ID that hay co dang 'bytedance-seed',
    'google-deepmind', 'meta-llama', nen so khop tuyet doi se bo sot."""
    o = (org or "").strip().lower().lstrip("~")
    if not o:
        return "khac"
    for tap, nhan in ((HANG_MY, "my"), (HANG_TQ, "tq")):
        if o in tap:
            return nhan
        for h in tap:
            if o.startswith(h + "-") or o.startswith(h + "_"):
                return nhan
    return "khac"


# ---------- nguon 1: OpenRouter ----------

def fetch_openrouter() -> list:
    try:
        d = _get(OPENROUTER).json()["data"]
    except Exception as e:                                   # noqa: BLE001
        print(f"[openrouter] hong: {type(e).__name__}: {e}", file=sys.stderr)
        return []
    out = []
    for m in d:
        created = m.get("created")
        if not created:
            continue
        p = m.get("pricing") or {}
        org = (m.get("id") or "").split("/")[0].lstrip("~")
        out.append({
            "nguon": "openrouter",
            "id": m["id"],
            "ten": m.get("name") or m["id"],
            "to_chuc": org,
            "vung": vung_cua(org),
            "ra_mat": datetime.fromtimestamp(created, timezone.utc).strftime("%Y-%m-%d"),
            "ra_mat_ts": created,
            # OpenRouter bao gia theo USD/token — nhan 1e6 cho ve USD/1M cho de doc
            "gia_vao": _usd_1m(p.get("prompt")),
            "gia_ra": _usd_1m(p.get("completion")),
            "context": m.get("context_length"),
            "co_reasoning": bool(m.get("reasoning")),
            "hf_id": m.get("hugging_face_id") or "",
            # Model la thuong KHONG co hugging_face_id (da kiem: sakana, dots-3,
            # ox-alpha, solar-pro4 deu None). Luc do mo ta cua chinh hang la
            # manh moi duy nhat con lai. Tim nguoc tren HuggingFace theo ten thi
            # ra model KHAC (tim "sakana" ra TinySwallow) — dua so sai con te hon
            # khong co so, nen khong lam.
            # 150 ky tu du de Nova biet model la gi; chi tiet no tu doc link.
            # Truoc day [:400] x moi model moi trong 14 ngay lam prompt phinh
            # theo ngay nhieu model ra mat (audit 01/09).
            "mo_ta": (m.get("description") or "")[:150],
        })
    return out


def _usd_1m(v):
    try:
        return round(float(v) * 1_000_000, 4)
    except (TypeError, ValueError):
        return None


# ---------- nguon 2: catalog cua 9router ----------

def fetch_catalog() -> list:
    try:
        d = _get(CATALOG).json()
    except Exception as e:                                   # noqa: BLE001
        print(f"[catalog] hong: {type(e).__name__}: {e}", file=sys.stderr)
        return []
    # Cau truc that: {"providers": {"<ten nha cung cap>": {"models": [...]}}}
    out = []
    for nha, khoi in (d.get("providers") or {}).items():
        for m in (khoi or {}).get("models") or []:
            mid = m.get("id") or m.get("model")
            if not mid:
                continue
            org = str(mid).split("/")[0]
            out.append({"nguon": "catalog", "id": f"{nha}/{mid}",
                        "ten": m.get("name") or mid, "nha_cung_cap": nha,
                        "to_chuc": org, "vung": vung_cua(org), "ra_mat": None,
                        "ra_mat_ts": None, "gia_vao": None, "gia_ra": None,
                        "context": m.get("context_length"), "co_reasoning": None})
    return out


# ---------- nguon 3: bang xep hang arena ----------

ARENA_BOARDS = (
    # (khoa, duong dan, nhan in)
    ("text", "text", "VAN BAN"),
    ("webdev", "code/webdev", "CODE WEBDEV"),
    ("vision", "vision", "VISION"),
    ("search", "search", "SEARCH"),
    ("image", "text-to-image", "TAO ANH"),
    ("image_edit", "image-edit", "SUA ANH"),
    ("video", "text-to-video", "TAO VIDEO"),
)


def _arena_board(duong_dan: str) -> list:
    """Mot bang bat ky cua arena.ai. Hang ghi trong object co `modelDisplayName`
    + `rank` + `rating` (Elo) trong payload RSC. Mot model co the xuat hien
    nhieu lan (nhieu provider) — giu hang tot nhat."""
    url = f"https://arena.ai/leaderboard/{duong_dan}"
    try:
        html = _get(url, timeout=90).text
    except Exception as e:                                   # noqa: BLE001
        print(f"[arena {duong_dan}] hong: {type(e).__name__}: {e}", file=sys.stderr)
        return []
    manh = re.findall(r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)', html)
    if not manh:
        print(f"[arena {duong_dan}] khong thay payload RSC", file=sys.stderr)
        return []
    raw = "".join(json.loads('"' + c + '"') for c in manh)
    dec = json.JSONDecoder()
    xep = []
    for m in re.finditer(r'\{"[a-zA-Z]', raw):
        try:
            o, _ = dec.raw_decode(raw[m.start():])
        except Exception:                                    # noqa: BLE001
            continue
        if isinstance(o, dict) and o.get("modelDisplayName") and o.get("rank"):
            xep.append(o)
    rows, seen = [], set()
    for o in sorted(xep, key=lambda x: x.get("rank") or 999):
        ten = o["modelDisplayName"]
        if ten in seen:
            continue
        seen.add(ten)
        org = (o.get("modelOrganization") or "").lower()
        rows.append({"hang": o["rank"], "ten": ten, "to_chuc": org,
                     "vung": vung_cua(org), "diem": round(o.get("rating") or 0, 1),
                     "votes": o.get("votes")})
    return rows


def fetch_arena() -> dict:
    """{'text': [...], 'webdev': [...], 'vision': ..., 'search', 'image',
    'image_edit', 'video'} — moi bang cua arena.ai, sap theo hang.

    Truoc 04/09/2026 chi doc bang text + rankByModality image/video tu trang
    lmarena cu, nen qwen3.8-max-0902 vao #1 WebDev (02/09) khong ai hay."""
    ra = {}
    for khoa, duong_dan, _nhan in ARENA_BOARDS:
        ra[khoa] = _arena_board(duong_dan)
    return ra


# ---------- nguon 6: SWE-bench Verified ----------

SWEBENCH = "https://www.swebench.com/"


def fetch_swebench(top: int) -> list:
    """Bang SWE-bench Verified (chinh thuc). JSON nam trong
    <script id="leaderboard-data">. Moi dong = agent + model; lay % resolved."""
    try:
        html = _get(SWEBENCH, timeout=60).text
        m = re.search(r'<script type="application/json" id="leaderboard-data">\s*(.*?)\s*</script>',
                      html, re.S)
        data = json.loads(m.group(1))
    except Exception as e:                                   # noqa: BLE001
        print(f"[swebench] hong: {type(e).__name__}: {e}", file=sys.stderr)
        return []
    bang = next((b for b in data if b.get("name") == "Verified"), None)
    if not bang:
        return []
    rows = sorted(bang["results"], key=lambda r: -(r.get("resolved") or 0))
    return [{"hang": i + 1, "ten": r.get("name", "?"), "model": r.get("model_display"),
             "to_chuc": (r.get("model_org") or "").lower(), "vung": "khac",
             "diem": r.get("resolved"), "ngay": r.get("date")}
            for i, r in enumerate(rows[:top])]


# ---------- nguon 7: LiveBench ----------

LIVEBENCH = "https://livebench.ai/"


def fetch_livebench(top: int) -> tuple:
    """LiveBench: trang React, du lieu o table_<YYYY_MM_DD>.csv; danh sach ngay
    nam trong bundle JS. Tra (rows, ngay_ban). Diem = trung binh cac cot."""
    try:
        html = _get(LIVEBENCH, timeout=60).text
        js_path = re.search(r'src="\./(static/js/main\.[a-z0-9]+\.js)"', html).group(1)
        js = _get(LIVEBENCH + js_path, timeout=60).text
        tat_ca = sorted(set(re.findall(r'"(20\d\d-\d\d-\d\d)"', js)))
        ngay = tat_ca[-1] if tat_ca else None
        csv_txt = None
        for n in reversed(tat_ca[-4:]):        # ngay moi nhat co the chua co csv
            r = _get(f"{LIVEBENCH}table_{n.replace('-', '_')}.csv", timeout=60)
            if r.status_code == 200 and r.text.startswith("model,"):
                csv_txt, ngay = r.text, n
                break
        if not csv_txt:
            return [], ngay
    except Exception as e:                                   # noqa: BLE001
        print(f"[livebench] hong: {type(e).__name__}: {e}", file=sys.stderr)
        return [], None
    import csv as _csv
    import io
    rows = []
    for r in _csv.DictReader(io.StringIO(csv_txt)):
        diem = [float(v) for k, v in r.items() if k != "model" and v not in ("", None)]
        if diem:
            rows.append({"ten": r["model"], "diem": round(sum(diem) / len(diem), 1),
                         "to_chuc": "", "vung": "khac"})
    rows.sort(key=lambda x: -x["diem"])
    for i, r in enumerate(rows):
        r["hang"] = i + 1
    return rows[:top], ngay


# ---------- nguon 8: OpenRouter usage (token thuc te) ----------

OPENROUTER_RANK = "https://openrouter.ai/api/frontend/v1/rankings/models"


def fetch_openrouter_usage(top: int) -> tuple:
    """Model nao duoc DUNG nhieu nhat (token/ngay tren OpenRouter). Khac bang
    diem: day la thi truong bo phieu bang tien. Tra (rows, ngay)."""
    try:
        data = _get(OPENROUTER_RANK, timeout=60).json().get("data", [])
    except Exception as e:                                   # noqa: BLE001
        print(f"[openrouter usage] hong: {type(e).__name__}: {e}", file=sys.stderr)
        return [], None
    if not data:
        return [], None
    ngay = max(r["date"] for r in data)[:10]
    truoc = sorted({r["date"] for r in data})
    ngay_truoc = truoc[-2][:10] if len(truoc) > 1 else None
    tong, tong_truoc = {}, {}
    for r in data:
        slug = re.sub(r"-\d{8}$", "", r["model_permaslug"])   # bo hau to ngay
        tk = (r.get("total_completion_tokens") or 0) + (r.get("total_prompt_tokens") or 0)
        if r["date"][:10] == ngay:
            tong[slug] = tong.get(slug, 0) + tk
        elif ngay_truoc and r["date"][:10] == ngay_truoc:
            tong_truoc[slug] = tong_truoc.get(slug, 0) + tk
    rows = []
    for i, (slug, tk) in enumerate(sorted(tong.items(), key=lambda x: -x[1])[:top]):
        org = slug.split("/")[0]
        doi = (tk - tong_truoc[slug]) / tong_truoc[slug] * 100 if tong_truoc.get(slug) else None
        rows.append({"hang": i + 1, "ten": slug, "to_chuc": org, "vung": vung_cua(org),
                     "ty_token": round(tk / 1e9, 1),
                     "doi_pct": round(doi) if doi is not None else None})
    return rows, ngay



# ---------- nguon 4: trang cham diem ----------

def _rsc(html: str) -> str:
    """Giai ma payload RSC cua Next.js (self.__next_f) thanh chuoi lien tuc."""
    manh = re.findall(r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)', html)
    return "".join(json.loads('"' + c + '"') for c in manh)


def fetch_aa() -> dict:
    """{slug: ban ghi} tu artificialanalysis. Day la XUONG SONG cua Nova:
    no cham diem moi hang nen bat duoc ca Anthropic lan Meta."""
    try:
        raw = _rsc(_get(AA, timeout=90).text)
    except Exception as e:                                   # noqa: BLE001
        print(f"[aa] hong: {type(e).__name__}: {e}", file=sys.stderr)
        return {}
    if not raw:
        print("[aa] khong thay payload RSC — trang co the da doi", file=sys.stderr)
        return {}
    dec = json.JSONDecoder()
    ra = {}
    for m in re.finditer(r'\{"', raw):
        try:
            o, _ = dec.raw_decode(raw[m.start():])
        except Exception:                                    # noqa: BLE001
            continue
        if isinstance(o, dict) and o.get("slug") and "intelligenceIndex" in o:
            ra[o["slug"]] = o
    return ra


def loc_aa(aa: dict, ngay: int, top: int) -> dict:
    """Chia du lieu cham diem thanh cac muc dang bao."""
    moc = (datetime.now(timezone.utc) - timedelta(days=ngay)
           ).strftime("%Y-%m-%d")
    gan_day = [r for r in aa.values() if (r.get("releaseDate") or "") >= moc]

    def gon(r):
        return {
            "ten": r.get("name"), "slug": r["slug"],
            "hang_sx": r.get("modelCreatorName"),
            # Quoc gia lay tu chinh nguon, khong con doan theo tien to ID
            "nuoc": (r.get("modelCreatorCountry") or "?").lower(),
            "ra_mat": r.get("releaseDate"),
            "coding": _lam_tron(r.get("codingIndex")),
            "agentic": _lam_tron(r.get("agenticIndex")),
            "terminal_bench": _lam_tron(r.get("terminalbenchHard")),
            "tri_tue": _lam_tron(r.get("intelligenceIndex")),
            "gia_vao": r.get("price1mInputTokens"),
            "gia_ra": r.get("price1mOutputTokens"),
            "gia_cache": r.get("cacheHitPrice"),
            "nguon_mo": bool(r.get("isOpenWeights")),
            "giay_phep": r.get("licenseName"),
            "openrouter_id": r.get("openrouterApiId"),
        }

    co_diem = [r for r in aa.values() if r.get("codingIndex") is not None]
    co_diem.sort(key=lambda r: -r["codingIndex"])
    hang_coding = {r["slug"]: i + 1 for i, r in enumerate(co_diem)}

    def gon2(r):
        g = gon(r)
        g["hang_coding"] = hang_coding.get(r["slug"])
        g["ten_goc"] = ten_goc(g["ten"])
        return g

    # NHOM THEO TEN GOC: AA liet ke moi muc effort la mot dong ("GPT-6 Astra
    # (high)", "(max)", "(low)"...). Voi Nova do la MOT model ra mat, khong
    # phai bay. Lay bien the diem coding cao nhat lam dai dien.
    ra_mat_goc = {}
    for r in sorted((gon2(r) for r in gan_day),
                    key=lambda x: -(x["coding"] or 0)):
        ra_mat_goc.setdefault(r["ten_goc"], r)
    return {
        "moi_ra_mat": sorted((gon2(r) for r in gan_day),
                             key=lambda x: x["ra_mat"] or "", reverse=True),
        "ra_mat_theo_ten": sorted(ra_mat_goc.values(),
                                  key=lambda x: (x["ra_mat"] or "", -(x["coding"] or 0)),
                                  reverse=True),
        "bang_coding_goc": _bang_goc(co_diem, gon2, top),
        "bang_tri_tue_goc": _bang_goc(
            sorted((r for r in aa.values() if r.get("intelligenceIndex") is not None),
                   key=lambda r: -r["intelligenceIndex"]), gon2, top, khoa="tri_tue"),
        "nguon_mo_moi": sorted(
            (gon(r) for r in gan_day if r.get("isOpenWeights")),
            key=lambda x: x["ra_mat"] or "", reverse=True),
        "top_coding": [gon(r) for r in co_diem[:top]],
    }


def ten_goc(ten: str) -> str:
    """'GPT-6 Astra (high)' -> 'GPT-6 Astra'; bo phan trong ngoac va hau to effort."""
    t = re.sub(r"\s*\(.*?\)\s*", " ", str(ten or "")).strip()
    return re.sub(r"\s+", " ", t)


def _bang_goc(co_diem: list, gon2, top: int, khoa: str = "coding") -> list:
    """Top coding theo TEN GOC (moi model mot dong, hang = hang cua bien the
    tot nhat) — de so hang lan nay voi lan truoc bat 'vao top / leo hang'."""
    ra, thay = [], set()
    for r in co_diem:
        g = gon2(r)
        if g["ten_goc"] in thay:
            continue
        thay.add(g["ten_goc"])
        ra.append({"hang": len(ra) + 1, "ten": g["ten_goc"], "to_chuc": g["hang_sx"],
                   "vung": "khac", "coding": g["coding"], "diem": g[khoa],
                   "ra_mat": g["ra_mat"]})
        if len(ra) >= top:
            break
    return ra


def _lam_tron(v):
    try:
        return round(float(v), 1)
    except (TypeError, ValueError):
        return None


# ---------- nguon 5: tin cua hang ----------

def fetch_tin_hang(ngay: int) -> list:
    """RSS cac hang. Bat su kien so dang ky khong the hien: mo ma nguon, doi
    giay phep, cong bo benchmark. Moi feed doc lap, mot cai chet khong keo do."""
    import email.utils as eut
    import xml.etree.ElementTree as ET
    nguong = time.time() - ngay * 86400
    ra = []
    for hang, url in RSS_HANG:
        try:
            # Dua bytes: tep XML tu khai bao encoding o dong dau nen de parser
            # tu doc, khoi doan sai.
            root = ET.fromstring(_get(url, timeout=40).content)
        except Exception as e:                               # noqa: BLE001
            print(f"[rss {hang}] hong: {type(e).__name__}", file=sys.stderr)
            continue
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for it in (root.findall(".//item") or root.findall(".//a:entry", ns)):
            def _t(*ten):
                for n in ten:
                    e = it.find(n) if not n.startswith("a:") else it.find(n, ns)
                    if e is not None and (e.text or e.get("href")):
                        return e.text or e.get("href")
                return ""
            tieu_de = (_t("title", "a:title") or "").strip()
            ngay_txt = _t("pubDate", "a:updated", "a:published")
            link = _t("link", "a:link") or ""
            if it.find("a:link", ns) is not None:
                link = it.find("a:link", ns).get("href") or link
            ts = 0.0
            try:
                ts = eut.parsedate_to_datetime(ngay_txt).timestamp()
            except Exception:                                # noqa: BLE001
                try:
                    ts = datetime.fromisoformat(
                        (ngay_txt or "").replace("Z", "+00:00")).timestamp()
                except Exception:                            # noqa: BLE001
                    ts = 0.0
            if ts and ts < nguong:
                continue
            low = tieu_de.lower()
            if not any(k in low for k in TU_KHOA_TIN):
                continue
            ra.append({"hang": hang, "tieu_de": tieu_de, "link": link,
                       "ngay": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
                       if ts else "?"})
    ra.sort(key=lambda x: x["ngay"], reverse=True)
    return ra


def fetch_github(ngay: int) -> list:
    """Ban phat hanh moi cua engine suy luan — thuong ho tro model moi truoc
    ca khi hang ra thong cao."""
    nguong = time.time() - ngay * 86400
    ra = []
    for repo in GITHUB_REPOS:
        try:
            d = _get(f"https://api.github.com/repos/{repo}/releases/latest",
                     timeout=30).json()
        except Exception:                                    # noqa: BLE001
            continue
        pub = d.get("published_at") or ""
        try:
            ts = datetime.fromisoformat(pub.replace("Z", "+00:00")).timestamp()
        except Exception:                                    # noqa: BLE001
            continue
        if ts < nguong:
            continue
        ra.append({"repo": repo, "tag": d.get("tag_name"), "ngay": pub[:10],
                   "ghi_chu": (d.get("body") or "")[:300]})
    return ra


# ---------- benchmark cua model la ----------

# Model card cua moi hang mot kieu bang khac nhau, regex boc so ra la hong —
# da thu, no bat nham. Nen o day code chi lam phan CO HOC: tai card ve va CAT
# doan quanh cho nhac benchmark. Doc bang va phan dinh con so co an tuong khong
# la viec cua Nova, vi do la doc that chu khong phai so khop chuoi.
BENCH_HINTS = ("swe-bench", "swebench", "swe bench", "aider", "livecodebench",
               "humaneval", "mbpp", "terminal-bench")


def _lam_sach(t: str) -> str:
    """Bo the HTML va gop khoang trang — card cua Qwen nhung ca CSS inline."""
    # Card cua vai hang (Qwen) nhung CSS inline. Vi ta CAT mot cua so giua chung,
    # doan trich hay bat dau/ket thuc GIUA mot the — nen ngoai viec bo the tron
    # con phai bo not manh the cut o hai dau, roi quet lai nhung manh CSS le.
    t = re.sub(r"<[^>]*>", " ", t)          # the tron ven
    t = re.sub(r"^[^<]*?>", " ", t, count=1)   # duoi the bi cat o dau doan
    t = re.sub(r"<[^>]*$", " ", t)             # dau the bi cat o cuoi doan
    t = re.sub(r"[a-zA-Z-]+\s*:\s*[^;\s]{1,40};", " ", t)   # khai bao CSS le
    t = re.sub(r"\S*(?:#[0-9a-fA-F]{3,8}|rgba?\()\S*", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def trich_benchmark(hf_id: str, quanh: int = 400) -> list:
    """Tra ve vai doan van ban quanh cho model card nhac toi benchmark code."""
    if not hf_id:
        return []
    url = f"https://huggingface.co/{hf_id}/raw/main/README.md"
    try:
        r = _get(url, timeout=30)
        if r.status_code != 200:
            return []
        card = r.text
    except Exception:                                        # noqa: BLE001
        return []
    doan, da_lay = [], []
    low = card.lower()
    for h in BENCH_HINTS:
        i = low.find(h)
        if i < 0:
            continue
        a, b = max(0, i - quanh // 2), min(len(card), i + quanh)
        if any(abs(a - x) < quanh for x in da_lay):   # tranh cat trung cho
            continue
        da_lay.append(a)
        doan.append(_lam_sach(card[a:b]))
        if len(doan) >= 3:
            break
    return doan


# ---------- moc da thay ----------

def doc_state() -> dict:
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def da_thay() -> set:
    return set(doc_state().get("ids", []))


def hang_cu() -> dict:
    """{'text': {'ten model': hang}, ...} tu lan quet truoc."""
    return doc_state().get("xep_hang", {})


def aa_da_bao() -> dict:
    """{ten goc: ngay ra mat} cac model AA da BAO roi (moi model bao dung mot lan)."""
    return doc_state().get("aa_da_bao", {})


def ghi_moc(ids: set, xep_hang: dict, da_bao: dict | None = None):
    if da_bao is None:
        da_bao = aa_da_bao()
    STATE.parent.mkdir(parents=True, exist_ok=True)
    # Ghi atomic (tmp + os.replace) nhu scan_business: write_text truc tiep ma
    # chet giua chung se de lai tep hong, mat sach bo nho da-thay.
    tmp = STATE.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(
        {"cap_nhat": datetime.now(timezone.utc).isoformat(),
         "ids": sorted(ids), "xep_hang": xep_hang, "aa_da_bao": da_bao},
        ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, STATE)


import bat_buoc                                              # noqa: E402


def ghi_bat_buoc(ra_mat_aa: list, leo_hang: list, moi_router: list) -> None:
    """Tich luy moi su kien tat dinh vao danh sach BAT BUOC cua Nova (xem
    bat_buoc.py). Luat Ong Chu 04/09/2026: xuat hien tren bang la phai dua;
    hom truoc sot thi hom sau bo sung, khong duoc bo."""
    muc = []
    for r in ra_mat_aa:
        muc.append((f"ra_mat|{r['ten_goc']}", r["ten_goc"], "ra_mat",
                    f"ra mat {r['ra_mat']}, {r['hang_sx']}, coding={r['coding']}"
                    + (f" #{r['hang_coding']}" if r.get("hang_coding") else ""), ""))
    for l in leo_hang:
        muc.append((f"{l['loai']}|{l['ten']}", l["ten"], l["loai"], l["ghi_chu"],
                    bat_buoc.link_goi_y({"loai": l["loai"], "ten": l["ten"]})))
    for m in moi_router:
        muc.append((f"router|{m['id']}", m["id"], "router",
                    f"moi tren router, ra mat {m.get('ra_mat')}",
                    bat_buoc.link_goi_y({"loai": "router", "ten": m["id"]})))
    bat_buoc.them_nhieu("nova", muc)


def so_hang(arena: dict, cu: dict) -> list:
    """So thu hang lan nay voi lan truoc — bat model VUA LEO HANG.

    Model moi vao bang (khong co trong lan truoc) cung tinh la dang chu y, vi
    'vao thang top 3' la tin, khong phai chuyen thuong."""
    ra = []
    for mod, rows in arena.items():
        truoc = cu.get(mod) or {}
        for r in rows:
            ten, h = r["ten"], r["hang"]
            h_cu = truoc.get(ten)
            if h_cu is None:
                if truoc:                       # co du lieu cu ma khong co model nay
                    ra.append({"loai": mod, "ten": ten, "hang": h, "hang_cu": None,
                               "buoc": None, "ghi_chu": f"MOI vao bang, thang hang #{h}"})
            elif h < h_cu:
                ra.append({"loai": mod, "ten": ten, "hang": h, "hang_cu": h_cu,
                           "buoc": h_cu - h,
                           "ghi_chu": f"leo {h_cu - h} bac: #{h_cu} -> #{h}"})
    # leo nhieu bac nhat len dau; model moi vao bang xep theo hang
    ra.sort(key=lambda x: (-(x["buoc"] or 99), x["hang"]))
    return ra


def main():
    ap = argparse.ArgumentParser(description="Quet model moi ra mat (tat dinh)")
    ap.add_argument("--lan-dau", action="store_true",
                    help="Chi ghi moc, khong bao gi — dung cho lan chay dau tien")
    ap.add_argument("--ngay", type=int, default=14,
                    help="Coi la moi neu ra mat trong N ngay (mac dinh 14)")
    ap.add_argument("--top", type=int, default=10,
                    help="Chi lay top N moi bang xep hang (mac dinh 10)")
    ap.add_argument("--khong-benchmark", action="store_true",
                    help="Bo qua buoc tai model card cua model la")
    ap.add_argument("--out", help="Ghi JSON ra tep thay vi in ra man hinh")
    a = ap.parse_args()

    orouter = fetch_openrouter()
    catalog = fetch_catalog()
    arena = fetch_arena()
    aa = loc_aa(fetch_aa(), a.ngay, a.top)
    tin = fetch_tin_hang(a.ngay)
    gh = fetch_github(a.ngay)
    swe = fetch_swebench(a.top)
    lb, lb_ngay = fetch_livebench(a.top)
    orr, or_ngay = fetch_openrouter_usage(a.top)

    tat_ca = {m["id"] for m in orouter} | {m["id"] for m in catalog}
    cu = da_thay()

    hang_moi = {mod: {r["ten"]: r["hang"] for r in rows}
                for mod, rows in arena.items()}
    # Bang coding AA (theo ten goc) cung vao bo nho xep hang -> lan sau bat
    # duoc "vao top coding" / "leo hang coding". Truoc 04/09/2026 chi so hang
    # arena, nen GPT-6 Astra vao #8 coding ngay ra mat ma khong ai hay.
    hang_moi["coding"] = {r["ten"]: r["hang"] for r in aa.get("bang_coding_goc", [])}
    hang_moi["tri_tue"] = {r["ten"]: r["hang"] for r in aa.get("bang_tri_tue_goc", [])}
    hang_moi["swebench"] = {r["ten"]: r["hang"] for r in swe}
    hang_moi["livebench"] = {r["ten"]: r["hang"] for r in lb}
    hang_moi["openrouter"] = {r["ten"]: r["hang"] for r in orr}
    if a.lan_dau:
        ghi_moc(tat_ca, hang_moi)
        print(f"Da ghi moc {len(tat_ca)} model. Lan sau se chi bao cai moi.")
        return

    nguong = time.time() - a.ngay * 86400
    moi = [m for m in orouter
           if m["id"] not in cu and (m["ra_mat_ts"] or 0) >= nguong]
    moi.sort(key=lambda m: -(m["ra_mat_ts"] or 0))
    moi_catalog = [m for m in catalog if m["id"] not in cu]

    for mod in list(arena):
        arena[mod] = arena[mod][:a.top]

    # Model trong top N thi da co hang de noi. Model LA — ngoai top, hang khong
    # ten — chi dang nhac neu benchmark that su noi troi. Lay san doan benchmark
    # de Nova phan dinh, thay vi de Nova tu di mo tung trang.
    ten_top = {r["ten"].lower() for rows in arena.values() for r in rows}
    if not a.khong_benchmark:
        for m in moi:
            goc = (m["id"].split("/")[-1] or "").lower()
            if any(goc in t or t in goc for t in ten_top):
                continue                       # da nam trong top, khoi tra them
            # Giu MOT doan trich la du de Nova phan dinh "co an tuong khong";
            # muon xem het thi mo model card — nhieu doan chi phinh prompt.
            m["benchmark_trich"] = trich_benchmark(m.get("hf_id") or "")[:1]

    bang_so = {m: r[:a.top] for m, r in arena.items()}
    bang_so["coding"] = aa.get("bang_coding_goc", [])
    bang_so["tri_tue"] = aa.get("bang_tri_tue_goc", [])
    bang_so["swebench"] = swe
    bang_so["livebench"] = lb
    bang_so["openrouter"] = orr
    leo_hang = so_hang(bang_so, hang_cu())

    # RA MAT THEO BANG CHAM DIEM: nguon "moi" thu hai, doc lap voi router.
    # Router-based `moi` bo sot model khong len router (GPT-6 Astra 03/09) va
    # chi bao MOT lan dung ngay id xuat hien — hom do Nova hong la mat luon.
    da_bao = aa_da_bao()
    ra_mat_aa = [r for r in aa.get("ra_mat_theo_ten", []) if r["ten_goc"] not in da_bao]

    ket = {
        "quet_luc": datetime.now(timezone.utc).isoformat(),
        "top_moi_bang": a.top,
        "model_moi": moi,
        "leo_hang": leo_hang,
        "cham_diem": aa,
        "ra_mat_aa_chua_bao": ra_mat_aa,
        "swebench": swe,
        "livebench": {"ngay": lb_ngay, "rows": lb},
        "openrouter_usage": {"ngay": or_ngay, "rows": orr},
        "tin_hang": tin,
        "ban_phat_hanh": gh,
        "moi_tren_router_cua_ta": moi_catalog,
        "bang_xep_hang": arena,
        "tong_theo_doi": len(tat_ca),
    }

    if a.out:
        Path(a.out).write_text(json.dumps(ket, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        print(a.out)
    else:
        _in_bao_cao(ket, a.ngay)

    da_bao.update({r["ten_goc"]: r["ra_mat"] for r in ra_mat_aa})
    ghi_moc(tat_ca | cu, hang_moi, da_bao)
    ghi_bat_buoc(ra_mat_aa, leo_hang, moi)
    bat_buoc.in_danh_sach("nova")


NHAN_BANG = {"text": "van ban", "webdev": "webdev", "vision": "vision", "search": "search",
             "image": "tao anh", "image_edit": "sua anh", "video": "tao video",
             "coding": "coding AA", "tri_tue": "tri tue AA", "swebench": "SWE-bench",
             "livebench": "LiveBench", "openrouter": "OpenRouter usage"}


def _in_bao_cao(k: dict, ngay: int):
    moi = k["model_moi"]
    print(f"=== MODEL MOI ({ngay} ngay qua) — {len(moi)} cai ===")
    for m in moi:
        vung = {"my": "My", "tq": "TQ", "khac": "  "}[m["vung"]]
        gia = (f"${m['gia_vao']}/{m['gia_ra']} mot trieu"
               if m["gia_vao"] is not None else "chua co gia")
        print(f"  {m['ra_mat']}  [{vung}] {m['id'][:44]:<45s} {gia}")
    co_bm = [m for m in moi if m.get("benchmark_trich")]
    if co_bm:
        print(f"\n=== MODEL LA CO CONG BO BENCHMARK ({len(co_bm)}) "
              "— Nova doc va phan dinh co an tuong khong ===")
        for m in co_bm:
            print(f"  --- {m['id']}  ({m['ra_mat']})")
            for d in m["benchmark_trich"][:2]:
                print(f"      {d[:200].replace(chr(10), ' ')}")
    la_khong_bm = [m for m in moi
                   if not m.get("benchmark_trich") and m.get("mo_ta")
                   and "benchmark_trich" in m]
    if la_khong_bm:
        print(f"\n=== MODEL LA KHONG CO MODEL CARD ({len(la_khong_bm)}) "
              "— chi con mo ta cua hang ===")
        for m in la_khong_bm[:8]:
            print(f"  --- {m['id']}  ({m['ra_mat']})")
            print(f"      {m['mo_ta'][:180]}")
    if k["moi_tren_router_cua_ta"]:
        print(f"\n=== MOI TREN ROUTER CUA TA ({len(k['moi_tren_router_cua_ta'])}) "
              "— goi duoc ngay ===")
        for m in k["moi_tren_router_cua_ta"][:15]:
            print(f"  {m['id']}")
    aa = k.get("cham_diem") or {}
    rm = k.get("ra_mat_aa_chua_bao") or []
    if rm:
        print(f"\n=== RA MAT THEO BANG CHAM DIEM ({len(rm)}) — artificialanalysis, "
              "CHUA BAO LAN NAO, moi ten goc mot dong ===")
        for r in rm[:12]:
            hc = f"#{r['hang_coding']} coding" if r.get("hang_coding") else "chua co diem coding"
            print(f"  {r['ra_mat']}  [{r['nuoc']}] {r['ten_goc'][:34]:<35s} "
                  f"{str(r['hang_sx'])[:14]:<15s} coding={r['coding']}  {hc}"
                  f"{'  MO NGUON' if r.get('nguon_mo') else ''}")
    tc = aa.get("top_coding") or []
    if tc:
        print("\n=== TOP CODING (artificialanalysis) ===")
        for r in tc[:10]:
            ca = f"cache ${r['gia_cache']}" if r["gia_cache"] is not None else "khong cache"
            print(f"  {str(r['coding']):>5s}  [{r['nuoc']}] {str(r['ten'])[:34]:<35s} "
                  f"{r['ra_mat']}  vao ${r['gia_vao']}  {ca}")
    nm = aa.get("nguon_mo_moi") or []
    if nm:
        print(f"\n=== VUA MO NGUON ({len(nm)}) — bat duoc ca hang khong co RSS ===")
        for r in nm[:8]:
            print(f"  {r['ra_mat']}  [{r['nuoc']}] {str(r['ten'])[:34]:<35s} "
                  f"{r['giay_phep']}  coding={r['coding']}")

    leo = k.get("leo_hang") or []
    if leo:
        print(f"\n=== VUA LEO HANG ({len(leo)}) — thay doi so voi lan quet truoc ===")
        for r in leo[:10]:
            nhan = NHAN_BANG.get(r["loai"], r["loai"])
            print(f"  [{nhan:<9s}] {r['ten'][:36]:<37s} {r['ghi_chu']}")

    tin = k.get("tin_hang") or []
    if tin:
        print(f"\n=== TIN TU HANG ({len(tin)}) — su kien so dang ky khong the hien ===")
        for t in tin[:10]:
            print(f"  {t['ngay']}  [{t['hang']:<15s}] {t['tieu_de'][:70]}")

    gh = k.get("ban_phat_hanh") or []
    if gh:
        print(f"\n=== ENGINE SUY LUAN RA BAN MOI ({len(gh)}) ===")
        for g in gh:
            print(f"  {g['ngay']}  {g['repo']:<28s} {g['tag']}")

    bxh = k.get("bang_xep_hang") or {}
    for mod, _dd, nhan in ARENA_BOARDS:
        rows = bxh.get(mod) or []
        if not rows:
            continue
        print(f"\n=== TOP {nhan} (arena.ai) ===")
        for r in rows[:8]:
            vung = {"my": "My", "tq": "TQ", "khac": "  "}[r["vung"]]
            diem = f"  {r['diem']}" if r.get("diem") else ""
            print(f"  #{str(r['hang']):<4s} [{vung}] {r['ten'][:40]:<41s} {r['to_chuc']}{diem}")

    tt = (aa.get("bang_tri_tue_goc") or [])
    if tt:
        print("\n=== TOP TRI TUE (artificialanalysis intelligence index, theo ten goc) ===")
        for r in tt[:8]:
            print(f"  #{str(r['hang']):<4s} {r['ten'][:40]:<41s} {str(r['to_chuc'])[:14]:<15s} {r['diem']}  ra mat {r['ra_mat']}")
    swe = k.get("swebench") or []
    if swe:
        print(f"\n=== SWE-BENCH VERIFIED (chinh thuc, muc moi nhat {max(r['ngay'] or '' for r in swe)}) ===")
        for r in swe[:8]:
            print(f"  #{str(r['hang']):<4s} {r['diem']:>5}%  {r['ten'][:44]:<45s} model={r['model']}  {r['ngay']}")
    lb = k.get("livebench") or {}
    if lb.get("rows"):
        print(f"\n=== LIVEBENCH (ban {lb.get('ngay')}) ===")
        for r in lb["rows"][:8]:
            print(f"  #{str(r['hang']):<4s} {r['diem']:>5}  {r['ten'][:50]}")
    orr = k.get("openrouter_usage") or {}
    if orr.get("rows"):
        print(f"\n=== OPENROUTER USAGE (token/ngay, ngay {orr.get('ngay')}) — thi truong bo phieu bang tien ===")
        for r in orr["rows"][:10]:
            doi = f"  {'+' if r['doi_pct'] > 0 else ''}{r['doi_pct']}% so hom truoc" if r.get("doi_pct") is not None else ""
            print(f"  #{str(r['hang']):<4s} {r['ty_token']:>8}B  {r['ten'][:40]:<41s}{doi}")


if __name__ == "__main__":
    main()
