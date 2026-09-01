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
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

import env_load

ROOT = Path.home() / "content-team"
STATE = env_load.state_dir() / "models_seen.json"
UA = "Mozilla/5.0 (compatible; donniechu-scout/1.0)"

OPENROUTER = "https://openrouter.ai/api/v1/models"
CATALOG = "https://hermes-agent.nousresearch.com/docs/api/model-catalog.json"
ARENA = "https://lmarena.ai/leaderboard"
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
            "mo_ta": (m.get("description") or "")[:400],
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

def fetch_arena() -> dict:
    """Tra {'text': [...], 'image': [...], 'video': [...]} da sap theo hang."""
    try:
        html = _get(ARENA, timeout=90).text
    except Exception as e:                                   # noqa: BLE001
        print(f"[arena] hong: {type(e).__name__}: {e}", file=sys.stderr)
        return {}
    # Du lieu nam trong cac manh self.__next_f.push([1,"...."]) — la chuoi JS
    # da escape, phai json.loads tung manh roi noi lai moi parse duoc.
    manh = re.findall(r'self\.__next_f\.push\(\[1,\s*"((?:[^"\\]|\\.)*)"\]\)', html)
    if not manh:
        print("[arena] khong thay payload RSC — trang co the da doi cau truc",
              file=sys.stderr)
        return {}
    raw = "".join(json.loads('"' + c + '"') for c in manh)
    dec = json.JSONDecoder()

    xep, danh_muc = [], {}
    for m in re.finditer(r'\{"[a-zA-Z]', raw):
        try:
            o, _ = dec.raw_decode(raw[m.start():])
        except Exception:                                    # noqa: BLE001
            continue
        if not isinstance(o, dict):
            continue
        if "avgScore" in o and o.get("model"):
            xep.append(o)
        elif o.get("publicName") and isinstance(o.get("rankByModality"), dict):
            danh_muc[o["publicName"]] = o

    ra = {}
    # text: co diem that (avgScore), lay tu bang xep hang chinh
    seen = set()
    text = []
    for o in sorted(xep, key=lambda x: x.get("rank") or 999):
        if o["model"] in seen:
            continue
        seen.add(o["model"])
        org = (o.get("modelOrganization") or "").lower()
        text.append({"hang": o.get("rank"), "ten": o["model"], "to_chuc": org,
                     "vung": vung_cua(org),
                     "diem": round((o.get("avgScore") or {}).get("value", 0), 4),
                     "gia_vao": o.get("inputPricePerMillion"),
                     "gia_ra": o.get("outputPricePerMillion"),
                     "license": o.get("license"), "link": o.get("modelUrl")})
    ra["text"] = text

    # anh / video: trang chinh khong kem diem, nhung co rankByModality
    for mod in ("image", "video"):
        rows = []
        for ten, o in danh_muc.items():
            h = o["rankByModality"].get(mod)
            if h in (None, BIG):
                continue
            org = (o.get("organization") or "").lower()
            rows.append({"hang": h, "ten": ten, "to_chuc": org, "vung": vung_cua(org)})
        rows.sort(key=lambda r: r["hang"])
        ra[mod] = rows
    return ra


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
    moc = (datetime.now(timezone.utc) - __import__("datetime").timedelta(days=ngay)
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
    return {
        "moi_ra_mat": sorted((gon(r) for r in gan_day),
                             key=lambda x: x["ra_mat"] or "", reverse=True),
        "nguon_mo_moi": sorted(
            (gon(r) for r in gan_day if r.get("isOpenWeights")),
            key=lambda x: x["ra_mat"] or "", reverse=True),
        "top_coding": [gon(r) for r in co_diem[:top]],
    }


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


def ghi_moc(ids: set, xep_hang: dict):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(
        {"cap_nhat": datetime.now(timezone.utc).isoformat(),
         "ids": sorted(ids), "xep_hang": xep_hang},
        ensure_ascii=False, indent=2), encoding="utf-8")


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

    tat_ca = {m["id"] for m in orouter} | {m["id"] for m in catalog}
    cu = da_thay()

    hang_moi = {mod: {r["ten"]: r["hang"] for r in rows}
                for mod, rows in arena.items()}
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
            m["benchmark_trich"] = trich_benchmark(m.get("hf_id") or "")

    leo_hang = so_hang({m: r[:a.top] for m, r in arena.items()}, hang_cu())

    ket = {
        "quet_luc": datetime.now(timezone.utc).isoformat(),
        "top_moi_bang": a.top,
        "model_moi": moi,
        "leo_hang": leo_hang,
        "cham_diem": aa,
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

    ghi_moc(tat_ca | cu, hang_moi)


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
            nhan = {"text": "van ban", "image": "tao anh", "video": "tao video"}.get(
                r["loai"], r["loai"])
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
    for mod, nhan in (("text", "VAN BAN"), ("image", "TAO ANH"), ("video", "TAO VIDEO")):
        rows = bxh.get(mod) or []
        if not rows:
            continue
        print(f"\n=== TOP {nhan} (arena) ===")
        for r in rows[:8]:
            vung = {"my": "My", "tq": "TQ", "khac": "  "}[r["vung"]]
            print(f"  #{str(r['hang']):<4s} [{vung}] {r['ten'][:40]:<41s} {r['to_chuc']}")


if __name__ == "__main__":
    main()
