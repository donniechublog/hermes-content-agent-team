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
import io
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
# CATALOG cua HERMES (tai lieu cua hermes-agent), KHONG phai catalog cua
# 9router. metadata.source cua chinh tep do ghi "hermes-agent repo", va
# upstream hermes_cli/models.py dung dung tep nay lam danh muc model cua
# CLI. Truoc 06/09/2026 muc nay duoc dan nhan "MOI TREN ROUTER CUA TA —
# goi duoc ngay", tuc noi voi Nova mot dieu khong dung: co trong catalog
# Hermes khong co nghia la 9router cua ta dinh tuyen duoc.
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


def _get(url: str, timeout=45, params=None) -> httpx.Response:
    # KHONG xin brotli. May chu cua OpenAI tra ve luong brotli ma bo giai nen cua
    # httpx nghen giua chung ("decoder process called with data when
    # can_accept_more_data() is False") — feed hong han, khong phai loi encoding.
    # Bo 'br' khoi Accept-Encoding thi may chu chuyen sang gzip va doc binh thuong.
    return httpx.get(url, timeout=timeout, follow_redirects=True, params=params,
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


# mini-SWE-agent = che do BASH ONLY: agent chi duoc go lenh bash, khong co
# scaffold rieng cua hang. Bang Verified tho dang bi cac he thong agent thuong
# mai chiem dinh (dong dau la "Sonar Foundation Agent", model_display="Multiple")
# — do la thu hang cua HE THONG, khong phai cua MODEL. Loc bash-only moi ra
# duoc so sanh model-voi-model that su.
SWE_BASH = "mini-SWE-agent"
# Chi lay hai split con SONG. Do 06/09/2026: Lite dung tu 11/09/2025, Full tu
# 19/12/2025, Multimodal tu 17/11/2025 — deu qua han, khong dua vao.
SWE_SPLIT = [("swebench", "Verified", False), ("swe_bash", "Verified", True),
             ("swe_da_ngon_ngu", "Multilingual", True)]


def fetch_swebench(top: int) -> dict:
    """Cac bang SWE-bench. MOT request cho tat ca split (JSON nhung san trong
    <script id="leaderboard-data">, la LIST 5 split). Tra {ma: (rows, ngay)}."""
    try:
        html = _get(SWEBENCH, timeout=60).text
        m = re.search(r'<script type="application/json" id="leaderboard-data">\s*(.*?)\s*</script>',
                      html, re.S)
        data = json.loads(m.group(1))
    except Exception as e:                                   # noqa: BLE001
        print(f"[swebench] hong: {type(e).__name__}: {e}", file=sys.stderr)
        return {ma: ([], None) for ma, _s, _b in SWE_SPLIT}
    ra = {}
    for ma, split, chi_bash in SWE_SPLIT:
        bang = next((b for b in data if b.get("name") == split), None)
        kq = bang.get("results") or [] if bang else []
        if chi_bash:
            kq = [r for r in kq if r.get("agent") == SWE_BASH]
        ngay = max((r.get("date") or "" for r in kq), default="") or None
        # Cung mot model duoc chay lai o nhieu moc ngay -> giu diem cao nhat,
        # khong thi mot model chiem nhieu dong va thu hang thanh vo nghia.
        goc = {}
        for r in sorted(kq, key=lambda r: -(r.get("resolved") or 0)):
            ten = (r.get("model_display") if chi_bash else r.get("name")) or "?"
            goc.setdefault(ten, r)
        rows = []
        for i, (ten, r) in enumerate(list(goc.items())[:top]):
            org = (r.get("model_org") or "").lower()
            rows.append({"hang": i + 1, "ten": ten, "model": r.get("model_display"),
                         "to_chuc": org, "vung": vung_cua(org),
                         "diem": r.get("resolved"), "ngay": r.get("date"),
                         "gia_usd": r.get("cost")})
        ra[ma] = (rows, ngay)
    return ra


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


# ---------- nguon 9-14: cac chieu 12 bang cu KHONG do ------------------------
# Khao sat 06/09/2026 (16 nguon, moi ket luan bi mot lan fetch doc lap phan
# bien). Bo di vi BANG DA CHET, khong phai vi lay khong duoc — deu lay duoc:
#   BFCL      dong bang tu 13/04/2026   LiveCodeBench  tu 01/08/2025
#   Aider     tu 03/10/2025             BigCodeBench   tu 16/04/2025
#   PapersWithCode da dong cua          SWE-bench Lite/Full/Multimodal deu chet
# Bo Vellum vi tu no ghi la trang TONG HOP lai so cua nguoi khac — them vao la
# dem so cua AA/arena mot lan nua duoi ten khac. Bo GAIA vi no xep hang HE
# THONG AGENT, cot model la chuoi viet tay ("GPT 5.5, Gemini 3 Pro" trong mot o)
# nen khong join duoc voi bat ky bang nao o day.

def _goc_theo_ten(rows: list, top: int) -> list:
    """Gop bien the effort ve MOT dong (nhu _bang_goc cua AA) roi danh so lai.
    Khong gop thi mot model chiem 5 dong dau bang va bang chi con 2 model."""
    goc, ra = {}, []
    for r in sorted(rows, key=lambda x: -(x["diem"] or 0)):
        t = ten_goc(r["ten"])
        if t in goc:
            continue
        goc[t] = r
        ra.append({**r, "ten": t})
        if len(ra) >= top:
            break
    for i, r in enumerate(ra):
        r["hang"] = i + 1
    return ra


# ---------- nguon 9: Terminal-Bench (agent go lenh trong container that) ------
# Edge function moi tu bundle JS cua tbench.ai — KHONG phai API cong bo, doi
# project ref la chet im. Da do: 9 lan goi lien tiep deu 200, byte y het nhau.
TBENCH = "https://ofhuhcpkvzjlejydnvyd.supabase.co/functions/v1/leaderboard-read"
TBENCH_BANG = ("terminal-bench/terminal-bench", "4-0-0")


def fetch_tbench(top: int) -> tuple:
    """Terminal-Bench 4.0: model bi tha vao container Linux, tu go lenh, cham
    bang TRANG THAI CUOI cua may. Chieu duy nhat do agent van hanh that."""
    try:
        pkg, ten_bang = TBENCH_BANG
        d = _get(TBENCH, params={"package": pkg, "name": ten_bang}).json()
    except Exception as e:                                   # noqa: BLE001
        print(f"[tbench] hong: {type(e).__name__}: {e}", file=sys.stderr)
        return [], None
    rows, ngay = [], ""
    for r in d.get("rows") or []:
        md, mt = r.get("metadata") or {}, r.get("metrics") or {}
        # Schema lech giua cac phien ban: co ban tra chuoi, co ban tra {label:}
        m, a = md.get("model_display"), md.get("agent_display")
        ten = m.get("label") if isinstance(m, dict) else m
        agent = a.get("label") if isinstance(a, dict) else a
        if not ten or mt.get("accuracy") is None:
            continue
        ngay = max(ngay, md.get("date") or "")
        # display_accuracy co markdown ("**58.2%** +- 2.8%") — dung so that
        rows.append({"ten": str(ten), "agent": agent or "", "to_chuc": "",
                     "vung": "khac", "diem": round(float(mt["accuracy"]), 1)})
    return _goc_theo_ten(rows, top), (ngay or None)


# ---------- nguon 10: ARC-AGI (hoc ky nang moi tren bai CHUA TUNG THAY) ------
ARCAGI = "https://arcprize.org/media/data/leaderboard/v2.json"


def fetch_arcagi(top: int) -> tuple:
    """ARC-AGI-2: do tri thong minh luu loat. Khac moi bang khac o cho bo de
    giu kin, khong the hoc thuoc — model nen o day khong the do nhiem du lieu."""
    try:
        d = _get(ARCAGI).json()
    except Exception as e:                                   # noqa: BLE001
        print(f"[arcagi] hong: {type(e).__name__}: {e}", file=sys.stderr)
        return [], None
    rows = []
    for e in d.get("evaluations") or []:
        # Bang co ca dong moc NGUOI ("Human Panel", "Stem Grad") — khong phai model
        if not e.get("display") or (e.get("providerDisplayName") or "") == "Human":
            continue
        if e.get("score") is None:
            continue
        org = (e.get("providerDisplayName") or "").lower()
        rows.append({"ten": e.get("modelDisplayName") or "?",
                     "to_chuc": e.get("providerDisplayName") or "",
                     "vung": vung_cua(org), "diem": round(float(e["score"]) * 100, 1),
                     "gia_moi_bai": e.get("costPerTask")})
    return _goc_theo_ten(rows, top), (d.get("generatedAt") or "")[:10] or None


# ---------- nguon 11: Humanity's Last Exam (tran kien thuc han lam) ----------
HLE = "https://scale.com/leaderboard/humanitys_last_exam"
# Neo vao data-model-name (data-attribute), KHONG vao class Tailwind bam hash.
# Moi model xuat hien HAI lan trong HTML (bien the mobile + desktop) -> phai
# khu trung theo (hang, ten), neu khong bang dai gap doi va hang lap.
HLE_PAT = re.compile(
    r'shrink-0 w-8"><span[^>]*>(\d+)</span>.*?data-model-name="true"[^>]*title="([^"]*)"'
    r'.*?text-ink">([\d.]+)</span>', re.S)


def fetch_hle(top: int) -> tuple:
    """Humanity's Last Exam: ~2.500 cau do chuyen gia PhD dat, dap an dong.
    Day la TRAN tren cua kien thuc — bang duy nhat con cho de leo."""
    try:
        html = _get(HLE, timeout=60).text
    except Exception as e:                                   # noqa: BLE001
        print(f"[hle] hong: {type(e).__name__}: {e}", file=sys.stderr)
        return [], None
    thay, rows = set(), []
    for hang, ten, diem in HLE_PAT.findall(html):
        k = (hang, ten)
        if k in thay:
            continue
        thay.add(k)
        rows.append({"ten": ten.strip(), "to_chuc": "", "vung": "khac",
                     "diem": round(float(diem), 1)})
    if len(rows) < 5:                       # regex vo -> bao rong, dung bao sai
        print(f"[hle] chi boc duoc {len(rows)} dong — coi nhu hong", file=sys.stderr)
        return [], None
    return _goc_theo_ten(rows, top), None


# ---------- nguon 12: Epoch Capabilities Index -------------------------------
# CSV thuan, khong parse HTML dong nao. Nguon it rui ro vo nhat trong ca dot.
ECI = "https://epoch.ai/data/eci_scores.csv"


def fetch_epoch(top: int) -> tuple:
    """ECI: Epoch ghep ~50 benchmark thanh MOT so bang Item Response Theory,
    kem khoang tin cay 95%. Khac AA intelligence index o cho co CI — hai model
    lech 1 diem ma CI chong nhau thi KHONG phai 'vuot mat'."""
    import csv as _csv
    try:
        txt = _get(ECI, timeout=60).text
    except Exception as e:                                   # noqa: BLE001
        print(f"[epoch] hong: {type(e).__name__}: {e}", file=sys.stderr)
        return [], None
    rows, ngay = [], ""
    for r in _csv.DictReader(io.StringIO(txt)):
        try:
            diem = float(r.get("eci") or "")
        except ValueError:
            continue
        ngay = max(ngay, (r.get("date") or "")[:10])
        org = (r.get("Organization") or "").strip()
        rows.append({"ten": (r.get("Display name") or r.get("Model") or "?").strip(),
                     "to_chuc": org, "vung": vung_cua(org.lower().replace(" ", "-")),
                     "diem": round(diem, 1), "ra_mat": (r.get("date") or "")[:10],
                     "ci_thap": r.get("eci_ci_low"), "ci_cao": r.get("eci_ci_high")})
    rows.sort(key=lambda x: -x["diem"])
    ra = rows[:top]
    for i, r in enumerate(ra):
        r["hang"] = i + 1
    return ra, (ngay or None)


# ---------- nguon 13: OpenCompass CompassBench (bo de DONG, phan lon lab TQ) --
# Ly do co mat: Ong Chu uu tien "top 5 Trung Quoc", ma moi bang khac deu cat
# top-N TOAN CAU — khong lab TQ nao lot top 10 the gioi la bang do cam tiet.
# Day la bang duy nhat trong bo co da so dong la lab TQ.
OC_API = "https://rank.opencompass.org.cn/gw/opencompass-be/api/v1/rank/"


def fetch_opencompass(top: int) -> tuple:
    """CompassBench: de RIENG, khong cong khai, doi bo moi quy — nen mien nhiem
    do nhiem du lieu. Endpoint chi nhan POST, GET tra 405."""
    h = {"User-Agent": UA, "Content-Type": "application/json", "lang": "en-US"}
    # May chu dat o Trung Quoc: do 06/09/2026 thi 1 lan duoc / 4 lan thu, hong
    # kieu ReadTimeout va SSL EOF chu khong phai bi chan. Nen thu lai chu dung
    # bo — hong that thi bang chi vang mot ngay, va muc "NGUON KHONG LAY DUOC"
    # se noi ro la vang chu khong phai "khong co gi".
    d = d2 = None
    for lan in range(2):
        try:
            # Ten thang xoay theo quy, khong hardcode duoc -> hoi truoc roi lay
            d = httpx.post(OC_API + "listRankTableAvailableMonths", timeout=45,
                           json={"rankingType": 0, "benchmarkType": 1},
                           headers=h).json()
            ds = d.get("data") or []
            if not ds:
                return [], None
            thang, ngay = ds[0].get("month"), ds[0].get("updateTime")
            d2 = httpx.post(OC_API + "listModelRankings", timeout=45, headers=h,
                            json={"evalType": 0, "rankingType": 0,
                                  "benchmarkType": 1, "month": thang}).json()
            break
        except Exception as e:                               # noqa: BLE001
            print(f"[opencompass] lan {lan + 1}/2 hong: {type(e).__name__}: {e}",
                  file=sys.stderr)
            if lan < 1:
                time.sleep(2)
    if d2 is None:
        return [], None
    rows = []
    for r in ((d2.get("data") or {}).get("modelRankings") or [])[:top]:
        org = (r.get("org") or "").lower()
        rows.append({"hang": r.get("ranking"), "ten": r.get("model") or "?",
                     "to_chuc": r.get("org") or "", "vung": vung_cua(org),
                     "diem": r.get("score"), "mo_nguon": bool(r.get("openSource"))})
    return rows, ngay


# ---------- nguon 14: AA mang KHONG-PHAI-VAN-BAN (am thanh, anh dong tu anh) --
# 12 bang cu gan nhu 100% la LLM van ban. Am thanh la diem mu TUYET DOI: khong
# ASR, khong TTS, khong realtime voice — model giong noi moi ra thi Nova khong
# co MOT duong nao de biet. arena.ai da co text-to-image/image-edit/text-to-
# video roi nen KHONG lay ba bang tuong ung cua AA (do la do lai cung mot thu).
AA_MEDIA = [
    ("tts", "https://artificialanalysis.ai/text-to-speech", "TTS (giong doc)"),
    ("stt", "https://artificialanalysis.ai/speech-to-text", "STT (nghe chep)"),
    ("i2v", "https://artificialanalysis.ai/video/leaderboard/image-to-video",
     "anh -> video"),
]
# STT: khoi ld+json phang, diem la ti le LOI (WER) nen THAP hon la TOT hon.
STT_PAT = re.compile(r'\{"label":"([^"]+)","aaWerIndex":([\d.]+)\}')
# TTS: hostModels long nhau, Elo nam trong object `model` ben trong
TTS_PAT = re.compile(r'"model":\{"id":"[0-9a-f-]{36}","name":"([^"]+)".*?'
                     r'"qualityElo":([\d.]+)', re.S)
# i2v: cung schema `formatted`/`values` voi cac bang arena khac cua AA
I2V_PAT = re.compile(r'\{"formatted":\{"rank":(\d+),"elo":"([^"]*)"'
                     r'.*?"values":\{"id":"[0-9a-f-]{36}","name":"([^"]+)"', re.S)


def fetch_aa_media(top: int) -> dict:
    """Ba bang media cua AA. Tra {'tts': rows, 'stt': rows, 'i2v': rows}."""
    ra = {}
    for ma, url, _nhan in AA_MEDIA:
        try:
            s = _rsc(_get(url, timeout=60).text)
        except Exception as e:                               # noqa: BLE001
            print(f"[aa-{ma}] hong: {type(e).__name__}: {e}", file=sys.stderr)
            ra[ma] = []
            continue
        rows, thay = [], set()
        if ma == "stt":
            for ten, wer in STT_PAT.findall(s):
                if ten in thay:
                    continue
                thay.add(ten)
                # Doi WER -> do chinh xac de MOI bang deu "cao hon = tot hon";
                # so_hang() gia dinh hang 1 la tot nhat, tron chieu la sai het.
                rows.append({"ten": ten, "to_chuc": "", "vung": "khac",
                             "diem": round((1 - float(wer)) * 100, 2)})
        elif ma == "tts":
            for ten, elo in TTS_PAT.findall(s):
                if ten in thay:
                    continue
                thay.add(ten)
                rows.append({"ten": ten, "to_chuc": "", "vung": "khac",
                             "diem": round(float(elo))})
        else:
            # BAY: moi trang arena cua AA nhung NHIEU lat cat (bang tong + bang
            # theo tag use-case). Regex bat ca ngan match nhung bang tong chi
            # vai chuc dong — phai dung o cho rank thoi tang don dieu, khong
            # thi ra danh sach rac ma KHONG bao loi.
            truoc = 0
            for hang, elo, ten in I2V_PAT.findall(s):
                h = int(hang)
                if h <= truoc:
                    break
                truoc = h
                if ten in thay:
                    continue
                thay.add(ten)
                rows.append({"ten": ten, "to_chuc": "", "vung": "khac",
                             "diem": int(elo) if elo.isdigit() else None})
        rows.sort(key=lambda x: -(x["diem"] or 0))
        rows = rows[:top]
        for i, r in enumerate(rows):
            r["hang"] = i + 1
        ra[ma] = rows
    return ra


# ---------- nguon 15: HuggingFace trending (bat model mo SOM hon router) -----
# KHONG phai bang chat luong — trendingScore la da tang like+tai trong cua so
# ngan. Vao day de PHAT HIEN, khong vao so_hang: xep hang no se de ra tin
# "leo hang" gia moi ngay.
HF_API = "https://huggingface.co/api/models"
# Ban luong hoa / adapter cua CUNG mot model goc: chung len trending rieng nen
# khong loc thi mot model ra mat bi bao 3-4 lan duoi ten ky thuat. Da bat hut
# 'nvidia/Qwen3.8-Flash-Next-NVFP4' o lan chay thu 06/09 -> them ho FP4/W-A.
HF_RAC = re.compile(r"gguf|awq|gptq|abliterat|uncensor|-lora|adapter|mlx|exl2|"
                    r"bnb-|int4|int8|fp8|fp4|nvfp|w4a|w8a|smashed|quantiz|"
                    r"-bf16$|-fp16$", re.I)
HF_SAN = 20            # trending duoi muc nay chua du tin hieu de thanh BAT BUOC


def fetch_hf_trending(ngay: int, top: int) -> list:
    """Model open-weight dang len tren HuggingFace. Bat duoc ban trong so TRUOC
    khi no len router 1-3 ngay — va bat ca model chi tha trong so, khong bao
    gio len router (thu router khong the thay)."""
    try:
        d = _get(HF_API, params={"sort": "trendingScore", "limit": 100}).json()
    except Exception as e:                                   # noqa: BLE001
        print(f"[hf-trending] hong: {type(e).__name__}: {e}", file=sys.stderr)
        return []
    moc = (datetime.now(timezone.utc) - timedelta(days=ngay)).strftime("%Y-%m-%d")
    rows = []
    for m in d:
        mid = m.get("id") or ""
        # Bo ban luong hoa / adapter: chung len trending theo model goc, dua vao
        # la bao cung mot model nhieu lan duoi ten ky thuat.
        if not mid or HF_RAC.search(mid):
            continue
        tao = (m.get("createdAt") or "")[:10]
        if tao < moc:            # gpt2 va all-MiniLM trending vinh vien — bo
            continue
        if (m.get("trendingScore") or 0) < HF_SAN:
            continue
        org = mid.split("/")[0]
        rows.append({"id": mid, "to_chuc": org, "vung": vung_cua(org),
                     "diem": m.get("trendingScore"), "likes": m.get("likes"),
                     "tai": m.get("downloads"), "ra_mat": tao,
                     "viec": m.get("pipeline_tag") or ""})
    rows.sort(key=lambda x: -(x["diem"] or 0))
    return rows[:top]


# ---------- nguon 16: changelog Anthropic (hang frontier KHONG co RSS) -------
# Da do 21/08: Anthropic va Meta deu 404 moi duong RSS. Nua Meta cua de xuat
# nay la du lieu chet (repo meta-llama moi nhat 28/04/2025, im 16 thang) nen
# CHI lay nua Anthropic. Day la markdown thuan, khong phai bang xep hang.
ANTHROPIC_CL = "https://platform.claude.com/docs/en/release-notes/overview.md"


def fetch_anthropic(ngay: int) -> list:
    """Muc changelog cua Anthropic trong N ngay qua, do RSS khong ton tai."""
    try:
        txt = _get(ANTHROPIC_CL, timeout=45).text
    except Exception as e:                                   # noqa: BLE001
        print(f"[anthropic] hong: {type(e).__name__}: {e}", file=sys.stderr)
        return []
    moc = (datetime.now(timezone.utc) - timedelta(days=ngay)).date()
    ra = []
    # Muc dang "## September 3, 2026" roi den cac gach dau dong ben duoi
    khoi = re.split(r"\n#{2,3}\s+", "\n" + txt)
    for k in khoi[1:]:
        dong = k.split("\n", 1)
        try:
            d = datetime.strptime(dong[0].strip(), "%B %d, %Y").date()
        except ValueError:
            continue
        if d < moc:
            continue
        than = (dong[1] if len(dong) > 1 else "").strip()
        for ln in than.splitlines():
            ln = ln.strip(" -*\t")
            if len(ln) < 12 or ln.startswith("#"):
                continue
            ra.append({"ngay": d.isoformat(), "hang": "Anthropic",
                       "tieu_de": re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", ln)[:120],
                       "link": "https://platform.claude.com/docs/en/release-notes/overview"})
            if len(ra) >= 12:
                return ra
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
        # `agenticIndex` da duoc tai ve va bo vao gon() tu truoc, nhung chua bao
        # gio duoc dung bang xep hang -> so_hang() khong co moc de so, nen mot
        # model nhay tu #9 len #2 agentic ma tri tue khong doi thi Nova IM
        # LANG. Cung kieu su co qwen3.8-max WebDev 02/09. Bang nay chua het 0
        # request them: so da nam san trong payload.
        "bang_agentic_goc": _bang_goc(
            sorted((r for r in aa.values() if r.get("agenticIndex") is not None),
                   key=lambda r: -r["agenticIndex"]), gon2, top, khoa="agentic"),
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
    # Mot bang tam hong (fetch tra []) truoc 06/09/2026 se ghi de bo nho xep
    # hang cua bang do bang rong -> lan sau khong con moc de so, "leo hang"
    # im lang bien mat. Bang RONG khong phai tin moi: giu lai moc cu.
    cu = hang_cu()
    xep_hang = {**cu, **{k: v for k, v in (xep_hang or {}).items() if v}}
    for k, v in (xep_hang or {}).items():
        if not v and cu.get(k):
            print(f"[canh bao] bang '{k}' tra rong — giu moc cu {len(cu[k])} muc",
                  file=sys.stderr)
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


def ghi_bat_buoc(ra_mat_aa: list, leo_hang: list, moi_router: list,
                 hf_moi: list | None = None) -> None:
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
    # Model tha trong so tren HuggingFace: cung mot loai su kien "model xuat
    # hien" nhu router, nen cung bat buoc. Khu trung theo doan sau dau / — cung
    # mot model len ca hai noi (deepseek-ai/DeepSeek-V4 vs deepseek/deepseek-v4)
    # thi chi la MOT tin.
    ten_router = {(m["id"].split("/")[-1] or "").lower().replace("_", "-")
                  for m in moi_router}
    for m in hf_moi or []:
        goc = (m["id"].split("/")[-1] or "").lower().replace("_", "-")
        if any(goc in t or t in goc for t in ten_router):
            continue
        muc.append((f"hf|{m['id']}", m["id"], "hf",
                    f"tha trong so tren HuggingFace {m.get('ra_mat')}, "
                    f"trending {m.get('diem')}, {m.get('tai')} luot tai",
                    f"https://huggingface.co/{m['id']}"))
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
    ap.add_argument("--khong-bat-buoc", action="store_true",
                    help="Van GIEO muc bat buoc, chi khong IN lai o cuoi bao cao. "
                         "quet_chuan_bi dung co nay vi brief da in danh sach do "
                         "mot lan roi (ngoai vung cat) — in hai lan ton 5.600 ky "
                         "tu dung o duoi day, tuc chinh no bi cat truoc tien.")
    a = ap.parse_args()

    orouter = fetch_openrouter()
    catalog = fetch_catalog()
    arena = fetch_arena()
    aa = loc_aa(fetch_aa(), a.ngay, a.top)
    tin = fetch_tin_hang(a.ngay) + fetch_anthropic(a.ngay)
    tin.sort(key=lambda t: t.get("ngay") or "", reverse=True)
    gh = fetch_github(a.ngay)
    swe_all = fetch_swebench(a.top)
    swe, swe_ngay = swe_all["swebench"]
    lb, lb_ngay = fetch_livebench(a.top)
    orr, or_ngay = fetch_openrouter_usage(a.top)
    tb, tb_ngay = fetch_tbench(a.top)
    arc, arc_ngay = fetch_arcagi(a.top)
    hle, _hle_ngay = fetch_hle(a.top)
    eci, eci_ngay = fetch_epoch(a.top)
    oc, oc_ngay = fetch_opencompass(a.top)
    media = fetch_aa_media(a.top)
    hf = fetch_hf_trending(a.ngay, a.top)

    tat_ca = {m["id"] for m in orouter} | {m["id"] for m in catalog}
    cu = da_thay()

    # MOT nguon su that cho moi bang. Truoc 06/09/2026 danh sach bang bi chep
    # LAM HAI o hai cho (hang_moi de ghi moc, bang_so de so hang) — them bang
    # ma quen mot cho thi no khong bao gio sinh duoc tin "leo hang", va khong
    # co gi bao loi. Gio dan xuat hang_moi TU bang_so.
    # Bang coding AA vao bo nho tu 04/09/2026: truoc do chi so hang arena, nen
    # GPT-6 Astra vao #8 coding ngay ra mat ma khong ai hay.
    bang_so = dict(arena)                       # 7 bang arena.ai
    bang_so["coding"] = aa.get("bang_coding_goc", [])
    bang_so["tri_tue"] = aa.get("bang_tri_tue_goc", [])
    bang_so["agentic"] = aa.get("bang_agentic_goc", [])
    bang_so["swebench"] = swe
    bang_so["swe_bash"] = swe_all["swe_bash"][0]
    bang_so["swe_da_ngon_ngu"] = swe_all["swe_da_ngon_ngu"][0]
    bang_so["livebench"] = lb
    bang_so["openrouter"] = orr
    bang_so["tbench"] = tb
    bang_so["arcagi"] = arc
    bang_so["hle"] = hle
    bang_so["eci"] = eci
    bang_so["opencompass"] = oc
    bang_so["tts"] = media.get("tts") or []
    bang_so["stt"] = media.get("stt") or []
    bang_so["i2v"] = media.get("i2v") or []
    lech = set(bang_so) ^ set(KHOA_BANG)
    if lech:                    # them bang ma quen khai (hoac nguoc lai)
        print(f"[canh bao] bang_so lech ban ke khai KHOA_BANG: {sorted(lech)}",
              file=sys.stderr)
    # Bang hong truoc day chi... khong in ra, nen Nova khong phan biet duoc
    # "bang nay khong co gi moi" voi "bang nay khong lay duoc". Hai ket luan
    # khac han nhau. Ghi ten ra de Nova biet minh dang nhin thieu cai gi.
    hong = sorted(k for k, v in bang_so.items() if not v)
    hang_moi = {mod: {r["ten"]: r["hang"] for r in rows}
                for mod, rows in bang_so.items()}
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

    # Moc trong state giu hang DAY DU (mot model tut xuong #40 roi leo lai #8
    # phai doc ra "leo 32 bac"), nhung chi BAO cai dang o top N.
    leo_hang = so_hang({m: r[:a.top] for m, r in bang_so.items()}, hang_cu())

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
        "swebench": {"ngay": swe_ngay, "rows": swe},
        "swe_bash": {"ngay": swe_all["swe_bash"][1], "rows": swe_all["swe_bash"][0]},
        "swe_da_ngon_ngu": {"ngay": swe_all["swe_da_ngon_ngu"][1],
                            "rows": swe_all["swe_da_ngon_ngu"][0]},
        "livebench": {"ngay": lb_ngay, "rows": lb},
        "openrouter_usage": {"ngay": or_ngay, "rows": orr},
        "tbench": {"ngay": tb_ngay, "rows": tb},
        "arcagi": {"ngay": arc_ngay, "rows": arc},
        "hle": {"ngay": None, "rows": hle},
        "eci": {"ngay": eci_ngay, "rows": eci},
        "opencompass": {"ngay": oc_ngay, "rows": oc},
        "media": media,
        "hf_trending": hf,
        "bang_hong": hong,
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
    ghi_bat_buoc(ra_mat_aa, leo_hang, moi, hf)
    if not a.khong_bat_buoc:
        # In ra STDERR, khong phai stdout: `quet_chuan_bi` chep nguyen stdout vao
        # brief roi TU in danh sach bat buoc mot lan nua — Nova doc hai ban cua
        # cung mot danh sach, va ban in tu day con mang cau luat CU ("script ghi
        # manifest se tu choi neu thieu") mau thuan voi luat that tu 05/09
        # ("thieu thi script tu them"). Mot danh sach, mot cau luat (06/09/2026).
        import io
        import contextlib
        _dem = io.StringIO()
        with contextlib.redirect_stdout(_dem):
            bat_buoc.in_danh_sach("nova")
        print(_dem.getvalue(), file=sys.stderr, end="")


NHAN_BANG = {"text": "van ban", "webdev": "webdev", "vision": "vision", "search": "search",
             "image": "tao anh", "image_edit": "sua anh", "video": "tao video",
             "coding": "coding AA", "tri_tue": "tri tue AA", "agentic": "agentic AA",
             "swebench": "SWE-bench", "swe_bash": "SWE-b bash", "swe_da_ngon_ngu": "SWE-b da nn",
             "livebench": "LiveBench", "openrouter": "OpenRouter usage",
             "tbench": "Terminal-B", "arcagi": "ARC-AGI-2", "hle": "HLE",
             "eci": "Epoch ECI", "opencompass": "CompassBench",
             "tts": "giong doc", "stt": "nghe chep", "i2v": "anh->video",
             "hf": "HuggingFace"}


# Tran in an. Do 06/09/2026: o trang thai production (arena song + co moc cu de
# so hang) bao cao ra 13.635 ky tu, trong khi brief cua quet_chuan_bi cat o
# 12.000 — tuc LIVEBENCH va OPENROUTER USAGE bi nuot mat truoc khi Nova nhin
# thay, va khong co dau hieu nao bao la da cut. Ba muc duoi day truoc do KHONG
# CO CAN TREN, mot ngay xau la nuot sach phan duoi bao cao.
TRAN_MOI = 25          # MODEL MOI — truoc: vo han (40 model = 5.612 ky tu)
TRAN_BM = 5            # trich benchmark — truoc: vo han x 2 doan x 200 ky tu
TRAN_GH = 10           # ban phat hanh engine — truoc: vo han
TRAN_HF = 10
TRAN_BANG = 5          # moi bang xep hang — truoc: 8
VUNG_NHAN = {"my": "My", "tq": "TQ", "khac": "  "}
# Ban ke khai bang xep hang. main() dung de kiem `bang_so` khong lech, va bao
# cao dung de in con so. Go tay con so nay thi no lech ngay: ban dau ghi 20
# trong khi that su co 23 (test_bang_nova bat duoc).
KHOA_BANG = tuple([m for m, _d, _n in ARENA_BOARDS] +
                  ["coding", "tri_tue", "agentic", "swebench", "swe_bash",
                   "swe_da_ngon_ngu", "livebench", "openrouter", "tbench",
                   "arcagi", "hle", "eci", "opencompass", "tts", "stt", "i2v"])
SO_BANG = len(KHOA_BANG)


def _in_bang(nhan: str, rows, n: int = TRAN_BANG, ngay=None, diem_hau: str = "",
             them=None):
    """In mot bang xep hang theo dung mot khuon. Truoc 06/09/2026 moi bang tu
    in mot kieu, nen them bang la them mot doan lap va mot co hoi lech dinh
    dang; gio doi lai thanh mot ham."""
    rows = rows or []
    if not rows:
        return
    print(f"\n=== {nhan}{f' — {ngay}' if ngay else ''} ===")
    for r in rows[:n]:
        vung = VUNG_NHAN.get(r.get("vung") or "khac", "  ")
        org = str(r.get("to_chuc") or "")[:13]
        phu = (them(r) or "") if them else ""
        print(f"  #{str(r.get('hang')):<3s}[{vung}] {str(r.get('ten'))[:38]:<39s} "
              f"{str(r.get('diem')):>6s}{diem_hau} {org:<14s}{phu}")


def _in_bao_cao(k: dict, ngay: int):
    moi = k.get("model_moi") or []
    print(f"=== MODEL MOI ({ngay} ngay qua) — {len(moi)} cai ===")
    for m in moi[:TRAN_MOI]:
        vung = VUNG_NHAN[m["vung"]]
        gia = (f"${m['gia_vao']}/{m['gia_ra']} mot trieu"
               if m["gia_vao"] is not None else "chua co gia")
        print(f"  {m['ra_mat']}  [{vung}] {m['id'][:44]:<45s} {gia}")
    if len(moi) > TRAN_MOI:
        print(f"  ... con {len(moi) - TRAN_MOI} model nua, xem muc BAT BUOC o cuoi")
    co_bm = [m for m in moi if m.get("benchmark_trich")]
    if co_bm:
        print(f"\n=== MODEL LA CO CONG BO BENCHMARK ({len(co_bm)}) "
              "— Nova doc va phan dinh co an tuong khong ===")
        for m in co_bm[:TRAN_BM]:
            print(f"  --- {m['id']}  ({m['ra_mat']})")
            for d in m["benchmark_trich"][:1]:
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
    if k.get("moi_tren_router_cua_ta"):
        print(f"\n=== MOI TRONG CATALOG CUA HERMES ({len(k['moi_tren_router_cua_ta'])}) "
              "— danh muc model cua hermes-agent, CHUA chac 9router goi duoc ===")
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
        for g in gh[:TRAN_GH]:
            print(f"  {g['ngay']}  {g['repo']:<28s} {g['tag']}")

    hong = k.get("bang_hong") or []
    if hong:
        print(f"\n=== NGUON KHONG LAY DUOC LAN NAY ({len(hong)}) — cac bang duoi "
              "day VANG khoi bao cao, KHONG phai 'khong co gi moi' ===")
        print("  " + ", ".join(NHAN_BANG.get(x, x) for x in hong))

    hf = k.get("hf_trending") or []
    if hf:
        print(f"\n=== VUA THA TRONG SO TREN HUGGINGFACE ({len(hf)}) — bat truoc "
              "router 1-3 ngay, va bat ca model KHONG BAO GIO len router ===")
        for m in hf[:TRAN_HF]:
            print(f"  {m['ra_mat']}  {m['id'][:44]:<45s} trending {str(m['diem']):>4s}  "
                  f"{(m['tai'] or 0):>10,d} tai  {m['viec'][:18]}")

    # ---- Bang xep hang: tu day tro xuong la BOI CANH, khong phai tin moi. Giu
    # 5 dong/bang co chu dich — muc tren (ra mat / leo hang) moi la thu Nova
    # phai dua, va bao cao co TRAN 12.000 ky tu o brief cua quet_chuan_bi.
    print(f"\n\n########## BANG XEP HANG — {SO_BANG} bang, top {TRAN_BANG} "
          "moi bang (boi canh de xep thu tu, khong phai tin) ##########")

    bxh = k.get("bang_xep_hang") or {}
    for mod, _dd, nhan in ARENA_BOARDS:
        _in_bang(f"{nhan} (arena.ai)", bxh.get(mod), diem_hau="")
    _in_bang("TRI TUE (artificialanalysis intelligence index)",
             aa.get("bang_tri_tue_goc"))
    # Bang agentic: so DA co san trong payload AA tu lau, chua bao gio duoc xep
    # hang nen so_hang() khong bat duoc "leo hang agentic". Them tu 06/09/2026.
    _in_bang("AGENTIC (artificialanalysis agentic index)",
             aa.get("bang_agentic_goc"))
    _in_bang("EPOCH ECI (ghep ~50 benchmark bang IRT, co khoang tin cay)",
             (k.get("eci") or {}).get("rows"), ngay=(k.get("eci") or {}).get("ngay"),
             them=lambda r: f"[{r.get('ci_thap')}-{r.get('ci_cao')}]")
    _in_bang("HUMANITY'S LAST EXAM (cau hoi do chuyen gia PhD dat)",
             (k.get("hle") or {}).get("rows"), diem_hau="%")
    _in_bang("ARC-AGI-2 (bai CHUA TUNG THAY, khong hoc thuoc duoc)",
             (k.get("arcagi") or {}).get("rows"),
             ngay=(k.get("arcagi") or {}).get("ngay"), diem_hau="%",
             them=lambda r: (f"${r['gia_moi_bai']:.2f}/bai"
                             if r.get("gia_moi_bai") else ""))
    _in_bang("TERMINAL-BENCH 4.0 (agent go lenh trong container that)",
             (k.get("tbench") or {}).get("rows"),
             ngay=(k.get("tbench") or {}).get("ngay"), diem_hau="%",
             them=lambda r: str(r.get("agent") or "")[:16])
    for ma, nhan in (("swebench", "SWE-BENCH VERIFIED (moi he thong agent)"),
                     ("swe_bash", "SWE-BENCH VERIFIED — CHI BASH (so sanh model that)"),
                     ("swe_da_ngon_ngu", "SWE-BENCH DA NGON NGU (C/C++/Go/Java/PHP/Ruby/Rust)")):
        b = k.get(ma) or {}
        _in_bang(nhan, b.get("rows"), ngay=b.get("ngay"), diem_hau="%")
    _in_bang("COMPASSBENCH (de DONG cua OpenCompass, phan lon lab TQ)",
             (k.get("opencompass") or {}).get("rows"),
             ngay=(k.get("opencompass") or {}).get("ngay"),
             them=lambda r: "mo nguon" if r.get("mo_nguon") else "")
    lb = k.get("livebench") or {}
    _in_bang("LIVEBENCH", lb.get("rows"), ngay=lb.get("ngay"))
    md = k.get("media") or {}
    _in_bang("GIONG DOC — TTS (artificialanalysis, Elo)", md.get("tts"))
    _in_bang("NGHE CHEP — STT (artificialanalysis, do chinh xac)", md.get("stt"),
             diem_hau="%")
    _in_bang("ANH -> VIDEO (artificialanalysis, Elo)", md.get("i2v"))

    orr = k.get("openrouter_usage") or {}
    if orr.get("rows"):
        print(f"\n=== OPENROUTER USAGE (token/ngay, {orr.get('ngay')}) — thi "
              "truong bo phieu bang tien ===")
        for r in orr["rows"][:TRAN_BANG]:
            doi = (f"  {'+' if r['doi_pct'] > 0 else ''}{r['doi_pct']}% so hom truoc"
                   if r.get("doi_pct") is not None else "")
            print(f"  #{str(r['hang']):<3s} {r['ty_token']:>7}B  {r['ten'][:38]:<39s}{doi}")


if __name__ == "__main__":
    main()
