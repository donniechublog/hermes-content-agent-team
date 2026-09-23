#!/usr/bin/env python3
"""Quet model MOI RA MAT — tat dinh, khong LLM. Viec cua Nova (profile radar/nova).

Khac Finn: Finn quet HN/Reddit/arXiv, tuc chi thay tin KHI DA CO NGUOI BAN LUAN.
Model release khong can cho thao luan moi dang gia — luc bao chi viet thi model da
len so dang ky vai ngay roi. Nen o day doc thang SO DANG KY.

Hai nguon, moi nguon doc lap (mot nguon chet khong keo do ca lan quet):

  1. Catalog cua 9router — tra loi cau thuc dung hon: "model moi nao HOM NAY ta
     goi duoc ngay", vi no da loc theo tai khoan dang co.
  2. lmarena.ai/leaderboard — bang xep hang. Du lieu nam trong payload RSC cua
     Next.js (self.__next_f), phai giai ma chuoi JS roi moi raw_decode duoc.
     Trang con /leaderboard/image va /video tai bang JS nen RONG — phai lay tu
     trang chinh, o do co ca `rankByModality` cho anh va video.

Model moi ra mat con duoc bat qua "ra mat theo bang cham diem" (artificialanalysis,
doc lap voi hai nguon tren) va qua HuggingFace trending (tha trong so). Truoc
16/09/2026 con co OpenRouter (/api/v1/models cho catalog, rankings cho usage
token/ngay) la mot nguon nua — Ong Chu chot bo han (LOW-185): tieu chi research
cua Nova chi con benchmark uy tin + HuggingFace, khong dua so lieu usage/gateway
vao lam tin hieu chon model.

Uu tien (Ong Chu chot): frontier My, top 5 Trung Quoc, top tao anh, top tao video.

Dung:
    venv/bin/python scan_models.py                 # bao model moi tu lan quet truoc
    venv/bin/python scan_models.py --lan-dau       # khoi tao moc, khong bao gi
    venv/bin/python scan_models.py --ngay 7        # coi la moi neu ra trong 7 ngay
"""
import argparse
import io
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

import model_boards                                            # noqa: E402
import scan_common                                            # noqa: E402
import scan_seen                                              # noqa: E402
import state_paths                                            # noqa: E402
import env_load

STATE = env_load.state_dir() / state_paths.MODELS_SEEN_FILE
UA = scan_common.UA                     # mot ban duy nhat, xem scan_common

# ---- kho nho DA-THAY cho ba nguon TIN (LOW-375) ----------------------------
# Truoc LOW-375 ba nguon nay KHONG co bo nho nao: bo loc duy nhat la cua so
# `--ngay` (7 ngay), nen repo nao con trending thi duoc bao lai MOI NGAY toi 7
# ngay lien. Do 23/09/2026 tren may chu: 9/20 dong bao cao 23/09 la model da
# nam trong bao cao 22/09; muc TIN TU HANG lap 9/10 giua 21/09 va 22/09.
#
# Ba truong nay nam CUNG tep voi `ids`/`rankings`/`aa_reported` — `SeenStore`
# doc tep cu va chi thay truong cua no, nen ba truong kia khong suy suyen.
# Khoa phai la DINH DANH ON DINH: cung mot repo ma 22/09 bao "dung dau
# trending", 23/09 bao "tha trong so", va ngay thi 20/09 roi 16/09 — loc bang
# tieu de hay bang ngay deu hong.
HF_SEEN_FIELD = "hf_seen"            # khoa: `org/name` cua repo HuggingFace
STORY_SEEN_FIELD = "story_seen"      # khoa: link da chuan hoa
GITHUB_SEEN_FIELD = "github_seen"    # khoa: `repo@tag`


def seen_store(field: str, window_days: float) -> scan_seen.SeenStore:
    """Kho da-thay tro vao STATE HIEN TAI (test doi STATE lay tep tam)."""
    return scan_seen.SeenStore(STATE, field=field, window_days=window_days)


def github_key(g: dict) -> str:
    return f"{g.get('repo', '')}@{g.get('tag', '')}"

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
# (404 moi duong thu). Anthropic co fetch_anthropic() rieng (changelog) lam luoi
# an toan; Meta thi KHONG — tu 16/09/2026 (bo OpenRouter, LOW-185) model moi cua
# Meta chi con bat duoc qua GITHUB_REPOS (llama.cpp) hoac khi len arena/AA/HF.
# Qwen: do lai 20/09/2026 (LOW-322) — feed VAN CHET, bai moi nhat 23/09/2025;
# `QwenLM/Qwen3` va `QwenLM/Qwen3-VL` tren GitHub thi 0 ban phat hanh (Qwen dang
# model thang len HuggingFace). Nen khong them lai duong nao cho Qwen o day; model
# moi cua ho van bat duoc qua catalog/arena/AA nhu cac hang Trung Quoc khac.
RSS_RANK = [
    ("OpenAI", "https://openai.com/news/rss.xml"),
    ("Google DeepMind", "https://deepmind.google/blog/rss.xml"),
    ("HuggingFace", "https://huggingface.co/blog/feed.xml"),
    ("Mistral", "https://mistral.ai/rss.xml"),
    # LOW-322 (20/09/2026). Duong CUOI CUNG sau chuyen huong: `blog.google/
    # technology/ai/rss/` gio 302 sang `/innovation-and-ai/...` — ghi thang
    # duong moi de khong phu thuoc chuyen huong.
    ("Google", "https://blog.google/innovation-and-ai/technology/ai/rss/"),
    ("Google Research", "https://research.google/blog/rss/"),
    # NVIDIA dang rat day va phan lon la huong dan ky thuat, khong phai ra mat
    # model — `KEYWORD_STORY` la cai giu no khong lan bao cao cua Nova.
    ("NVIDIA", "https://developer.nvidia.com/blog/feed/"),
]

# Repo co ban phat hanh thuong bao model moi duoc ho tro TRUOC ca thong cao
GITHUB_REPOS = ["vllm-project/vllm", "ggml-org/llama.cpp", "huggingface/transformers"]

# Tu khoa loc tin: chi giu bai co ve lien quan model/ma nguon mo
KEYWORD_STORY = ("model", "open-source", "open source", "open-weight", "open weight",
               "release", "launch", "introducing", "benchmark", "swe-bench",
               "weights", "apache", "mit license", "available now")

# Cac hang duoc uu tien, chia theo vung. Doi chieu bang truong `organization`
# cua arena va tien to ID cua OpenRouter.
RANK_MY = {"openai", "anthropic", "google", "google-deepmind", "meta", "meta-llama",
           "xai", "x-ai", "microsoft", "nvidia", "mistralai", "mistral", "amazon",
           "cohere", "ai21", "perplexity", "luma-ai", "bfl", "ideogram", "runway",
           "liquid", "recraft", "stability", "pika", "openrouter", "inception"}
RANK_CHINA = {"deepseek", "moonshot", "moonshotai", "qwen", "alibaba", "zai", "z-ai",
           "zhipuai", "minimax", "bytedance", "tencent", "baidu", "01-ai", "01ai",
           "stepfun", "wan", "kuaishou", "baichuan", "inclusionai", "skywork",
           "hunyuan", "seed", "iflytek", "sensetime", "kling", "vidu"}

BIG = 9007199254740991          # arena dung so nay lam "khong xep hang"


_get = scan_common.get                  # mot ban duy nhat, xem scan_common


def region_of(org: str) -> str:
    """Khop ca ten day du lan tien to — ID that hay co dang 'bytedance-seed',
    'google-deepmind', 'meta-llama', nen so khop tuyet doi se bo sot."""
    o = (org or "").strip().lower().lstrip("~")
    if not o:
        return "khac"
    for tap, nhan in ((RANK_MY, "my"), (RANK_CHINA, "tq")):
        if o in tap:
            return nhan
        for h in tap:
            if o.startswith(h + "-") or o.startswith(h + "_"):
                return nhan
    return "khac"


# ---------- nguon 1: catalog cua 9router ----------

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
            out.append({"source": "catalog", "id": f"{nha}/{mid}",
                        "name": m.get("name") or mid, "provider": nha,
                        "organization": org, "region": region_of(org), "released": None,
                        "released_ts": None, "input_price": None, "output_price": None,
                        "context": m.get("context_length"), "has_reasoning": None})
    return out


# ---------- nguon 3: bang xep hang arena ----------

# Bang arena doc tu BAN DANG KY dung chung (model_boards): khoa, duong dan API,
# nhan in. Xem model_boards.py cho ly do gom.
ARENA_BOARDS = model_boards.ARENA_BOARDS


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
        rows.append({"rank": o["rank"], "name": ten, "organization": org,
                     "region": region_of(org), "score": round(o.get("rating") or 0, 1),
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
             ("swe_multilingual", "Multilingual", True)]


def fetch_swebench(top: int) -> dict:
    """Cac bang SWE-bench. MOT request cho tat ca split (JSON nhung san trong
    <script id="leaderboard-data">, la LIST 5 split). Tra {ma: (rows, ngay)}."""
    try:
        html = _get(SWEBENCH, timeout=60).text
        m = re.search(r'<script type="application/json" id="leaderboard-data">\s*(.*?)\s*</script>',
                      html, re.S)
        if m is None:
            raise ValueError("khong thay <script id=leaderboard-data> — trang doi hinh")
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
            rows.append({"rank": i + 1, "name": ten, "model": r.get("model_display"),
                         "organization": org, "region": region_of(org),
                         "score": r.get("resolved"), "date": r.get("date"),
                         "price_usd": r.get("cost")})
        ra[ma] = (rows, ngay)
    return ra


# ---------- nguon 7: LiveBench ----------

LIVEBENCH = "https://livebench.ai/"


def fetch_livebench(top: int) -> tuple:
    """LiveBench: trang React, du lieu o table_<YYYY_MM_DD>.csv; danh sach ngay
    nam trong bundle JS. Tra (rows, ngay_ban). Diem = trung binh cac cot."""
    try:
        html = _get(LIVEBENCH, timeout=60).text
        m_js = re.search(r'src="\./(static/js/main\.[a-z0-9]+\.js)"', html)
        if m_js is None:
            raise ValueError("khong thay bundle static/js/main.*.js — trang doi hinh")
        js_path = m_js.group(1)
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
    # `hang` chu khong `r`: `r` o tren la mot Response httpx, dung lai ten do cho
    # mot hang CSV lam ca nguoi doc lan may doc kieu deu lac (LOW-308).
    for hang in _csv.DictReader(io.StringIO(csv_txt)):
        diem = [float(v) for k, v in hang.items() if k != "model" and v not in ("", None)]
        if diem:
            rows.append({"name": hang["model"], "score": round(sum(diem) / len(diem), 1),
                         "organization": "", "region": "khac"})
    rows.sort(key=lambda x: -x["score"])
    for i, hang in enumerate(rows):
        hang["rank"] = i + 1
    return rows[:top], ngay


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

def _original_by_name(rows: list, top: int) -> list:
    """Gop bien the effort ve MOT dong (nhu _bang_goc cua AA) roi danh so lai.
    Khong gop thi mot model chiem 5 dong dau bang va bang chi con 2 model."""
    goc, ra = {}, []
    for r in sorted(rows, key=lambda x: -(x["score"] or 0)):
        t = name_original(r["name"])
        if t in goc:
            continue
        goc[t] = r
        ra.append({**r, "name": t})
        if len(ra) >= top:
            break
    for i, r in enumerate(ra):
        r["rank"] = i + 1
    return ra


# ---------- nguon 9: Terminal-Bench (agent go lenh trong container that) ------
# Edge function moi tu bundle JS cua tbench.ai — KHONG phai API cong bo, doi
# project ref la chet im. Da do: 9 lan goi lien tiep deu 200, byte y het nhau.
TBENCH = "https://ofhuhcpkvzjlejydnvyd.supabase.co/functions/v1/leaderboard-read"
TBENCH_BOARD = ("terminal-bench/terminal-bench", "4-0-0")


def fetch_tbench(top: int) -> tuple:
    """Terminal-Bench 4.0: model bi tha vao container Linux, tu go lenh, cham
    bang TRANG THAI CUOI cua may. Chieu duy nhat do agent van hanh that."""
    try:
        pkg, ten_bang = TBENCH_BOARD
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
        rows.append({"name": str(ten), "agent": agent or "", "organization": "",
                     "region": "khac", "score": round(float(mt["accuracy"]), 1)})
    return _original_by_name(rows, top), (ngay or None)


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
        rows.append({"name": e.get("modelDisplayName") or "?",
                     "organization": e.get("providerDisplayName") or "",
                     "region": region_of(org), "score": round(float(e["score"]) * 100, 1),
                     "cost_per_task": e.get("costPerTask")})
    return _original_by_name(rows, top), (d.get("generatedAt") or "")[:10] or None


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
        rows.append({"name": ten.strip(), "organization": "", "region": "khac",
                     "score": round(float(diem), 1)})
    if len(rows) < 5:                       # regex vo -> bao rong, dung bao sai
        print(f"[hle] chi boc duoc {len(rows)} dong — coi nhu hong", file=sys.stderr)
        return [], None
    return _original_by_name(rows, top), None


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
        rows.append({"name": (r.get("Display name") or r.get("Model") or "?").strip(),
                     "organization": org, "region": region_of(org.lower().replace(" ", "-")),
                     "score": round(diem, 1), "released": (r.get("date") or "")[:10],
                     "ci_low": r.get("eci_ci_low"), "ci_high": r.get("eci_ci_high")})
    rows.sort(key=lambda x: -x["score"])
    ra = rows[:top]
    for i, r in enumerate(ra):
        r["rank"] = i + 1
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
    # `ranking` co the thieu (OpenCompass la bang chap chon nhat bo, xem NHAT KY).
    # `so_hang` so `h < h_cu`, va None < int nem TypeError giet ca luot quet —
    # nen danh so lai theo thu tu tra ve nhu 22 bang kia thay vi tin truong nay.
    for k, r in enumerate(((d2.get("data") or {}).get("modelRankings") or [])[:top], 1):
        org = (r.get("org") or "").lower()
        rows.append({"rank": r.get("ranking") or k, "name": r.get("model") or "?",
                     "organization": r.get("org") or "", "region": region_of(org),
                     "score": r.get("score"), "open_source": bool(r.get("openSource"))})
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
                rows.append({"name": ten, "organization": "", "region": "khac",
                             "score": round((1 - float(wer)) * 100, 2)})
        elif ma == "tts":
            for ten, elo in TTS_PAT.findall(s):
                if ten in thay:
                    continue
                thay.add(ten)
                rows.append({"name": ten, "organization": "", "region": "khac",
                             "score": round(float(elo))})
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
                rows.append({"name": ten, "organization": "", "region": "khac",
                             "score": int(elo) if elo.isdigit() else None})
        rows.sort(key=lambda x: -(x["score"] or 0))
        rows = rows[:top]
        for i, r in enumerate(rows):
            r["rank"] = i + 1
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
HF_JUNK = re.compile(r"gguf|awq|gptq|abliterat|uncensor|-lora|adapter|mlx|exl2|"
                    r"bnb-|int4|int8|fp8|fp4|nvfp|w4a|w8a|smashed|quantiz|"
                    r"-bf16$|-fp16$", re.I)
HF_READY = 20            # trending duoi muc nay chua du tin hieu de thanh BAT BUOC


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
        if not mid or HF_JUNK.search(mid):
            continue
        tao = (m.get("createdAt") or "")[:10]
        if tao < moc:            # gpt2 va all-MiniLM trending vinh vien — bo
            continue
        if (m.get("trendingScore") or 0) < HF_READY:
            continue
        org = mid.split("/")[0]
        rows.append({"id": mid, "organization": org, "region": region_of(org),
                     "score": m.get("trendingScore"), "likes": m.get("likes"),
                     "downloads": m.get("downloads"), "released": tao,
                     "pipeline_tag": m.get("pipeline_tag") or ""})
    rows.sort(key=lambda x: -(x["score"] or 0))
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
            ra.append({"date": d.isoformat(), "company": "Anthropic",
                       "title": re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", ln)[:120],
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


def filter_aa(aa: dict, ngay: int, top: int) -> dict:
    """Chia du lieu cham diem thanh cac muc dang bao."""
    moc = (datetime.now(timezone.utc) - timedelta(days=ngay)
           ).strftime("%Y-%m-%d")
    gan_day = [r for r in aa.values() if (r.get("releaseDate") or "") >= moc]

    def gon(r):
        return {
            "name": r.get("name"), "slug": r["slug"],
            "maker": r.get("modelCreatorName"),
            # Quoc gia lay tu chinh nguon, khong con doan theo tien to ID
            "country": (r.get("modelCreatorCountry") or "?").lower(),
            "released": r.get("releaseDate"),
            "coding": _make_full(r.get("codingIndex")),
            "agentic": _make_full(r.get("agenticIndex")),
            "terminal_bench": _make_full(r.get("terminalbenchHard")),
            "intelligence": _make_full(r.get("intelligenceIndex")),
            "input_price": r.get("price1mInputTokens"),
            "output_price": r.get("price1mOutputTokens"),
            "cache_price": r.get("cacheHitPrice"),
            "open_weights": bool(r.get("isOpenWeights")),
            "license": r.get("licenseName"),
            "openrouter_id": r.get("openrouterApiId"),
        }

    co_diem = [r for r in aa.values() if r.get("codingIndex") is not None]
    co_diem.sort(key=lambda r: -r["codingIndex"])
    hang_coding = {r["slug"]: i + 1 for i, r in enumerate(co_diem)}

    def slim_with_rank(r):
        g = gon(r)
        g["coding_rank"] = hang_coding.get(r["slug"])
        g["original_name"] = name_original(g["name"])
        return g

    # NHOM THEO TEN GOC: AA liet ke moi muc effort la mot dong ("GPT-6 Astra
    # (high)", "(max)", "(low)"...). Voi Nova do la MOT model ra mat, khong
    # phai bay. Lay bien the diem coding cao nhat lam dai dien.
    ra_mat_goc = {}
    for r in sorted((slim_with_rank(r) for r in gan_day),
                    key=lambda x: -(x["coding"] or 0)):
        ra_mat_goc.setdefault(r["original_name"], r)
    return {
        "new_releases": sorted((slim_with_rank(r) for r in gan_day),
                             key=lambda x: x["released"] or "", reverse=True),
        "releases_by_name": sorted(ra_mat_goc.values(),
                                  key=lambda x: (x["released"] or "", -(x["coding"] or 0)),
                                  reverse=True),
        "coding_board_original": _board_original(co_diem, slim_with_rank, top),
        "intelligence_board_original": _board_original(
            sorted((r for r in aa.values() if r.get("intelligenceIndex") is not None),
                   key=lambda r: -r["intelligenceIndex"]), slim_with_rank, top, khoa="intelligence"),
        # `agenticIndex` da duoc tai ve va bo vao gon() tu truoc, nhung chua bao
        # gio duoc dung bang xep hang -> so_hang() khong co moc de so, nen mot
        # model nhay tu #9 len #2 agentic ma tri tue khong doi thi Nova IM
        # LANG. Cung kieu su co qwen3.8-max WebDev 02/09. Bang nay chua het 0
        # request them: so da nam san trong payload.
        "agentic_board_original": _board_original(
            sorted((r for r in aa.values() if r.get("agenticIndex") is not None),
                   key=lambda r: -r["agenticIndex"]), slim_with_rank, top, khoa="agentic"),
        "new_open_weights": sorted(
            (gon(r) for r in gan_day if r.get("isOpenWeights")),
            key=lambda x: x["released"] or "", reverse=True),
        "top_coding": [gon(r) for r in co_diem[:top]],
    }


def name_original(ten: str) -> str:
    """'GPT-6 Astra (high)' -> 'GPT-6 Astra'; bo phan trong ngoac va hau to effort."""
    t = re.sub(r"\s*\(.*?\)\s*", " ", str(ten or "")).strip()
    return re.sub(r"\s+", " ", t)


def _board_original(co_diem: list, gon2, top: int, khoa: str = "coding") -> list:
    """Top coding theo TEN GOC (moi model mot dong, hang = hang cua bien the
    tot nhat) — de so hang lan nay voi lan truoc bat 'vao top / leo hang'."""
    ra, thay = [], set()
    for r in co_diem:
        g = gon2(r)
        if g["original_name"] in thay:
            continue
        thay.add(g["original_name"])
        ra.append({"rank": len(ra) + 1, "name": g["original_name"], "organization": g["maker"],
                   "region": "khac", "coding": g["coding"], "score": g[khoa],
                   "released": g["released"]})
        if len(ra) >= top:
            break
    return ra


def _make_full(v):
    try:
        return round(float(v), 1)
    except (TypeError, ValueError):
        return None


# ---------- nguon 5: tin cua hang ----------

def fetch_story_rank(ngay: int) -> list:
    """RSS cac hang. Bat su kien so dang ky khong the hien: mo ma nguon, doi
    giay phep, cong bo benchmark. Moi feed doc lap, mot cai chet khong keo do."""
    import safe_xml
    nguong = time.time() - ngay * 86400
    ra = []
    for hang, url in RSS_RANK:
        try:
            # Dua bytes: tep XML tu khai bao encoding o dong dau nen de parser
            # tu doc, khoi doan sai.
            root = safe_xml.fromstring(_get(url, timeout=40).content)
        except Exception as e:                               # noqa: BLE001
            print(f"[rss {hang}] hong: {type(e).__name__}", file=sys.stderr)
            continue
        ns = {"a": "http://www.w3.org/2005/Atom"}
        for it in (root.findall(".//item") or root.findall(".//a:entry", ns)):
            # `_t` doc `it`/`ns` cua lan lap hien tai (B023). Vo hai: ba loi goi
            # `_t(...)` nam ngay duoi, trong cung lan lap; ham khong bi luu lai
            # hay day sang ThreadPoolExecutor (cac `ex.submit` o ham main deu
            # buoc gia tri bang tham so mac dinh `lambda fn=fn: ...`).
            def _t(*ten):
                for n in ten:
                    e = it.find(n) if not n.startswith("a:") else it.find(n, ns)  # noqa: B023
                    if e is not None and (e.text or e.get("href")):
                        return e.text or e.get("href")
                return ""
            tieu_de = (_t("title", "a:title") or "").strip()
            ngay_txt = _t("pubDate", "a:updated", "a:published")
            link = _t("link", "a:link") or ""
            if it.find("a:link", ns) is not None:
                link = it.find("a:link", ns).get("href") or link
            ts = scan_common.timestamp_time(ngay_txt or "")   # mot ban (ADF-r2-15)
            if ts and ts < nguong:
                continue
            low = tieu_de.lower()
            if not any(k in low for k in KEYWORD_STORY):
                continue
            ra.append({"company": hang, "title": tieu_de, "link": link,
                       "date": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
                       if ts else "?"})
    ra.sort(key=lambda x: x["date"], reverse=True)
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
        ts = scan_common.timestamp_time(pub)
        if not ts or ts < nguong:
            continue
        ra.append({"repo": repo, "tag": d.get("tag_name"), "date": pub[:10],
                   "note": (d.get("body") or "")[:300]})
    return ra


# ---------- moc da thay ----------

def read_state() -> dict:
    """Moc da thay; {} neu chua co.

    Truoc 06/09/2026 khong boc loi: mot lan ghi bi cat ngang (het dia, kill)
    lam MOI lan chay sau do chet ngay o `da_thay()` cho toi khi co nguoi xoa
    tay — ma theo muc cron o duoi, khong ai duoc bao. Nay doi ten tep hong roi
    di tiep voi moc rong: bao cao hom do thua tin (moi thu deu "moi") nhung
    day chuyen khong dung, va dong canh bao noi ro vi sao.
    """
    if not STATE.exists():
        return {}
    try:
        return json.loads(STATE.read_text(encoding="utf-8"))
    except Exception as e:                                   # noqa: BLE001
        hong = STATE.with_suffix(".json.hong")
        try:
            STATE.replace(hong)
        except OSError:
            hong = "(khong doi ten duoc)"
        print(f"[canh bao] {STATE.name} HONG ({type(e).__name__}) — da doi ten "
              f"thanh {hong}, chay tiep voi moc RONG. Bao cao lan nay se coi moi "
              "model la moi; lan sau tro lai binh thuong.", file=sys.stderr)
        return {}


def already_see() -> set:
    return set(read_state().get("ids", []))


def rank_old() -> dict:
    """{'text': {'ten model': hang}, ...} tu lan quet truoc."""
    return read_state().get("rankings", {})


def aa_already_report() -> dict:
    """{ten goc: ngay ra mat} cac model AA da BAO roi (moi model bao dung mot lan)."""
    return read_state().get("aa_reported", {})


def write_timestamp(ids: set, xep_hang: dict, da_bao: dict | None = None):
    if da_bao is None:
        da_bao = aa_already_report()
    # Mot bang tam hong (fetch tra []) truoc 06/09/2026 se ghi de bo nho xep
    # hang cua bang do bang rong -> lan sau khong con moc de so, "leo hang"
    # im lang bien mat. Bang RONG khong phai tin moi: giu lai moc cu.
    cu = rank_old()
    xep_hang = {**cu, **{k: v for k, v in (xep_hang or {}).items() if v}}
    for k, v in (xep_hang or {}).items():
        if not v and cu.get(k):
            print(f"[canh bao] bang '{k}' tra rong — giu moc cu {len(cu[k])} muc",
                  file=sys.stderr)
    STATE.parent.mkdir(parents=True, exist_ok=True)
    # Ghi nguyen tu qua env_load.ghi_json (tmp mang PID + os.replace):
    # write_text thang ma chet giua chung se de lai tep hong, mat sach bo nho
    # da-thay; con ten tep tam CO DINH (`.json.tmp`, ban truoc 06/09/2026) thi
    # cron va mot lan chay tay `--lam-moi` trung thoi diem se ghi lan vao cung
    # mot tep tam va `replace` ban cut cua nhau.
    # LOW-375 luat 2: DOC TEP CU, CHI THAY TRUONG CUA MINH. Ban truoc ghi mot
    # dict CO DINH bon khoa, nen moi truong khac trong tep bi xoa o lan chay ke
    # tiep. Tu LOW-375 tep nay con giu `hf_seen`/`story_seen`/`github_seen`, va
    # ham nay chay TRUOC cac lan `mark()` — giu nguyen kieu cu thi bo nho
    # ngay-qua-ngay cua Nova bi xoa sach moi sang, dung thu no sinh ra de chan.
    # Day chinh la su co `note` cua business_seen ngay 26/08.
    goc = read_state()
    goc.update({"updated_at": datetime.now(timezone.utc).isoformat(),
                "ids": sorted(ids), "rankings": xep_hang,
                "aa_reported": da_bao})
    env_load.write_json(STATE, goc)


import required                                              # noqa: E402


def write_required(ra_mat_aa: list, leo_hang: list,
                 hf_moi: list | None = None) -> None:
    """Tich luy moi su kien tat dinh vao danh sach BAT BUOC cua Nova (xem
    required.py). Luat Ong Chu 04/09/2026: xuat hien tren bang la phai dua;
    hom truoc sot thi hom sau bo sung, khong duoc bo."""
    muc = []
    for r in ra_mat_aa:
        muc.append((f"{required.KIND_RELEASE}|{r['original_name']}", r["original_name"], required.KIND_RELEASE,
                    f"ra mat {r['released']}, {r['maker']}, coding={r['coding']}"
                    + (f" #{r['coding_rank']}" if r.get("coding_rank") else ""), ""))
    for l in leo_hang:
        muc.append((f"{l['board']}|{l['name']}", l["name"], l["board"], l["note"],
                    required.link_call_y({"kind": l["board"], "name": l["name"]})))
    # Model tha trong so tren HuggingFace: mot loai su kien "model xuat hien",
    # nen cung bat buoc.
    for m in hf_moi or []:
        muc.append((f"hf|{m['id']}", m["id"], "hf",
                    f"tha trong so tren HuggingFace {m.get('released')}, "
                    f"trending {m.get('score')}, {m.get('downloads')} luot tai",
                    f"https://huggingface.co/{m['id']}"))
    required.extra_many("nova", muc)


def count_rank(arena: dict, cu: dict) -> list:
    """So thu hang lan nay voi lan truoc — bat model VUA LEO HANG.

    Model moi vao bang (khong co trong lan truoc) cung tinh la dang chu y, vi
    'vao thang top 3' la tin, khong phai chuyen thuong."""
    ra = []
    for mod, rows in arena.items():
        truoc = cu.get(mod) or {}
        for r in rows:
            ten, h = r["name"], r["rank"]
            h_cu = truoc.get(ten)
            if h_cu is None:
                if truoc:                       # co du lieu cu ma khong co model nay
                    ra.append({"board": mod, "name": ten, "rank": h, "previous_rank": None,
                               "climb": None, "note": f"MOI vao bang, thang hang #{h}"})
            elif h < h_cu:
                ra.append({"board": mod, "name": ten, "rank": h, "previous_rank": h_cu,
                           "climb": h_cu - h,
                           "note": f"leo {h_cu - h} bac: #{h_cu} -> #{h}"})
    # leo nhieu bac nhat len dau; model moi vao bang xep theo hang
    ra.sort(key=lambda x: (-(x["climb"] or 99), x["rank"]))
    return ra


def _try(ten: str, fn, khi_hong):
    """Hang rao cuoi cho MOT nguon: loi bat ngo khong duoc keo do ca luot quet.

    Vi sao can du moi fetcher da co try rieng: cac try do chi boc LOI GOI MANG,
    khong boc phan PARSE. `float(v)` (livebench khi o la "-"),
    `float(mt["accuracy"])` (tbench doi schema), `r["codingIndex"]`,
    `h < h_cu` khi OpenCompass thieu `ranking` — tat ca nam NGOAI try va nem
    thang ra `main`, giet ca 22 bang. Khi do:
    stdout rong, khong bang nao, khong ghi moc, va `brief_nova` van dung bao
    cao rong do -> Nova ket luan "hom nay khong co gi". Dung loai hong ma
    README goi la dang so nhat.

    Nguon hong ghi vao `_HONG_KHAC` de in cung muc "NGUON KHONG LAY DUOC" —
    `broken_boards` chi bat duoc fetcher tra RONG, khong bat duoc fetcher NEM.
    """
    try:
        return fn()
    except Exception as e:                                   # noqa: BLE001
        print(f"[{ten}] HONG (ngoai try cua chinh no): {type(e).__name__}: {e}",
              file=sys.stderr)
        _HONG_KHAC.append(ten)
        return khi_hong


_HONG_KHAC = []


def main():
    ap = argparse.ArgumentParser(description="Quet model moi ra mat (tat dinh)")
    ap.add_argument("--lan-dau", action="store_true",
                    help="Chi ghi moc, khong bao gi — dung cho lan chay dau tien")
    ap.add_argument("--ngay", type=int, default=14,
                    help="Coi la moi neu ra mat trong N ngay (mac dinh 14)")
    ap.add_argument("--top", type=int, default=10,
                    help="Chi lay top N moi bang xep hang (mac dinh 10)")
    ap.add_argument("--out", help="Ghi JSON ra tep thay vi in ra man hinh")
    ap.add_argument("--khong-bat-buoc", action="store_true",
                    help="Van GIEO muc bat buoc, chi khong IN lai o cuoi bao cao. "
                         "scan_prepare dung co nay vi brief da in danh sach do "
                         "mot lan roi (ngoai vung cat) — in hai lan ton 5.600 ky "
                         "tu dung o duoi day, tuc chinh no bi cat truoc tien.")
    # LOW-375 luat 6: khong bao gio de mot lan chay THU ghi vao kho that.
    # `scan_business` da co co nay tu sau su co 26/08 (chay `--lan-dau` luc
    # test ghi de business_seen that, danh dau nham tin chua bao la da thay);
    # Nova thi chua, nen tu truoc toi nay chay thu la hong moc cua Nova.
    ap.add_argument("--state", help="Duong dan tep moc khac (de TEST khong dung "
                    "models_seen.json that). Mac dinh dung tep that.")
    a = ap.parse_args()

    global STATE
    if a.state:
        STATE = Path(a.state)

    RONG2 = ([], None)                       # cac fetch tra (rows, ngay)
    # 15 nguon doc lap, moi nguon da boc trong _thu (hang rao cuoi rieng —
    # xem docstring _thu) nen an toan chay song song: khong nguon nao doc/ghi
    # bien chung ngoai _HONG_KHAC (list.append atomic trong CPython). Nop TAT
    # CA qua executor.submit truoc, roi moi .result() theo DUNG THU TU VA CACH
    # GHEP nhu ban tuan tu cu — _thu tu bat het Exception nen .result() o day
    # khong bao gio nem, chi cho toi khi luong cua no xong.
    with ThreadPoolExecutor(max_workers=env_load.quantity(8)) as ex:
        f_catalog = ex.submit(_try, "catalog", fetch_catalog, [])
        f_arena = ex.submit(_try, "arena", fetch_arena, {})
        f_aa = ex.submit(_try, "aa", lambda: filter_aa(fetch_aa(), a.ngay, a.top), {})
        f_rss = ex.submit(_try, "rss hang", lambda: fetch_story_rank(a.ngay), [])
        f_anthropic = ex.submit(
            _try, "anthropic", lambda: fetch_anthropic(a.ngay), [])
        f_gh = ex.submit(_try, "github", lambda: fetch_github(a.ngay), [])
        # Cac bang tra (rows, ngay): gom MOT dict, khoa = khoa trong ban dang ky
        # (model_boards). Truoc 07/09/2026 moi bang la mot cap bien rieng (`lb,
        # lb_ngay`...) roi duoc chep tay vao `bang_so` va `ket` — them bang o day
        # ma quen `ket` thi bao cao im lang thieu bang do, va `hong` khong bat vi
        # `bang_so` van co no.
        f_swebench = ex.submit(
            _try, "swebench", lambda: fetch_swebench(a.top),
            {"swebench": RONG2, "swe_bash": RONG2, "swe_multilingual": RONG2})
        f_top = {}
        for khoa, ten, fn in (
                ("livebench", "livebench", fetch_livebench),
                ("tbench", "tbench", fetch_tbench),
                ("arcagi", "arcagi", fetch_arcagi),
                ("hle", "hle", fetch_hle),
                ("eci", "epoch", fetch_epoch),
                ("opencompass", "opencompass", fetch_opencompass)):
            f_top[khoa] = ex.submit(_try, ten, lambda fn=fn: fn(a.top), RONG2)
        f_media = ex.submit(_try, "aa media", lambda: fetch_aa_media(a.top), {})
        f_hf = ex.submit(
            _try, "hf-trending", lambda: fetch_hf_trending(a.ngay, a.top), [])

        catalog = f_catalog.result()
        arena = f_arena.result()
        aa = f_aa.result()
        tin = f_rss.result() + f_anthropic.result()
        tin.sort(key=lambda t: t.get("date") or "", reverse=True)
        gh = f_gh.result()
        top = f_swebench.result()
        for khoa, f in f_top.items():
            top[khoa] = f.result()
        media = f_media.result()
        hf = f_hf.result()

    tat_ca = {m["id"] for m in catalog}
    cu = already_see()

    # LOW-375: ba kho da-thay cho ba nguon TIN. Cua so quet la `a.ngay`, kho
    # nho gap doi (xem luat 6 trong scan_seen) — muc con trong cua so ma da
    # roi khoi kho la muc se quay lai bao cao.
    hf_seen = seen_store(HF_SEEN_FIELD, a.ngay)
    story_seen = seen_store(STORY_SEEN_FIELD, a.ngay)
    gh_seen = seen_store(GITHUB_SEEN_FIELD, a.ngay)

    # MOT nguon su that cho moi bang. Truoc 06/09/2026 danh sach bang bi chep
    # LAM HAI o hai cho (hang_moi de ghi moc, bang_so de so hang) — them bang
    # ma quen mot cho thi no khong bao gio sinh duoc tin "leo hang", va khong
    # co gi bao loi. Gio dan xuat hang_moi TU bang_so.
    # Bang coding AA vao bo nho tu 04/09/2026: truoc do chi so hang arena, nen
    # GPT-6 Astra vao #8 coding ngay ra mat ma khong ai hay.
    bang_so = dict(arena)                       # 7 bang arena.ai
    bang_so["coding"] = aa.get("coding_board_original", [])
    bang_so["intelligence"] = aa.get("intelligence_board_original", [])
    bang_so["agentic"] = aa.get("agentic_board_original", [])
    for khoa, (rows, _ngay) in top.items():
        bang_so[khoa] = rows
    bang_so["tts"] = media.get("tts") or []
    bang_so["stt"] = media.get("stt") or []
    bang_so["i2v"] = media.get("i2v") or []
    lech = set(bang_so) ^ set(LOCK_BOARD)
    if lech:                    # them bang ma quen khai (hoac nguoc lai)
        print(f"[canh bao] bang_so lech ban ke khai KHOA_BANG: {sorted(lech)}",
              file=sys.stderr)
    # Bang hong truoc day chi... khong in ra, nen Nova khong phan biet duoc
    # "bang nay khong co gi moi" voi "bang nay khong lay duoc". Hai ket luan
    # khac han nhau. Ghi ten ra de Nova biet minh dang nhin thieu cai gi.
    hong = sorted(k for k, v in bang_so.items() if not v)
    # Nguon KHONG phai bang xep hang khong nam trong `bang_so`, nen `hong` mu
    # voi chung: catalog 5xx mot sang la muc "MOI TRONG CATALOG" in ra rong ma
    # khong ai hay — catalog luon co hang tram model, rong = hong, khong co
    # cach doc nao khac.
    for ten, gt in (("catalog", catalog),
                    ("aa", aa), ("aa media", media), ("arena", arena)):
        if not gt and ten not in _HONG_KHAC:
            print(f"[{ten}] tra RONG — coi nhu khong lay duoc", file=sys.stderr)
            _HONG_KHAC.append(ten)
    hang_moi = {mod: {r["name"]: r["rank"] for r in rows}
                for mod, rows in bang_so.items()}
    if a.lan_dau:
        write_timestamp(tat_ca, hang_moi)
        # `--lan-dau` = chi ghi moc, khong bao. Ba nguon tin cung phai duoc ghi
        # moc o day, neu khong thi lan chay THAT ngay sau se do het tin cu 7
        # ngay vao bao cao dau tien.
        hf_seen.mark(m["id"] for m in hf)
        story_seen.mark(scan_common.standard_link(t.get("link", "")) for t in tin)
        gh_seen.mark(github_key(g) for g in gh)
        print(f"Da ghi moc {len(tat_ca)} model. Lan sau se chi bao cai moi.")
        return

    moi_catalog = [m for m in catalog if m["id"] not in cu]

    # LOW-375 — luat Ong Chu 23/09/2026: "chung ta ko dan lai tin da research
    # duoc". Bo cac muc DA TUNG vao bao cao cua Nova.
    hf, bo_hf = hf_seen.unseen(hf, key=lambda m: m["id"])
    tin, bo_tin = story_seen.unseen(
        tin, key=lambda t: scan_common.standard_link(t.get("link", "")))
    gh, bo_gh = gh_seen.unseen(gh, key=github_key)
    if bo_hf or bo_tin or bo_gh:
        print(f"  chong trung ngay-qua-ngay: bo {bo_hf} repo HF, {bo_tin} tin hang, "
              f"{bo_gh} ban phat hanh da bao hom truoc", file=sys.stderr)

    for mod in list(arena):
        arena[mod] = arena[mod][:a.top]

    # Moc trong state giu hang DAY DU (mot model tut xuong #40 roi leo lai #8
    # phai doc ra "leo 32 bac"), nhung chi BAO cai dang o top N.
    leo_hang = count_rank({m: r[:a.top] for m, r in bang_so.items()}, rank_old())

    # RA MAT THEO BANG CHAM DIEM: nguon "moi" thu hai, doc lap voi router.
    # Router-based `moi` bo sot model khong len router (GPT-6 Astra 03/09) va
    # chi bao MOT lan dung ngay id xuat hien — hom do Nova hong la mat luon.
    da_bao = aa_already_report()
    ra_mat_aa = [r for r in aa.get("releases_by_name", []) if r["original_name"] not in da_bao]

    ket = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "top_per_board": a.top,
        "rank_climbs": leo_hang,
        "aa_scores": aa,
        "aa_releases_unreported": ra_mat_aa,
        # Moi bang kieu (rows, ngay) mot muc, khoa theo ban dang ky (`ket_khoa`
        # neu khac khoa trong bang_so).
        **{(b.ket_khoa or b.khoa): {"date": top[b.khoa][1], "rows": top[b.khoa][0]}
           for b in model_boards.BOARD if b.nguon == "top"},
        "media": media,
        "hf_trending": hf,
        "broken_boards": hong,
        "broken_sources": sorted(set(_HONG_KHAC)),
        "company_news": tin,
        "releases": gh,
        "new_on_our_router": moi_catalog,
        "leaderboards": arena,
        "tracked_total": len(tat_ca),
    }

    if a.out:
        Path(a.out).write_text(json.dumps(ket, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        print(a.out)
    else:
        _in_report(ket)

    da_bao.update({r["original_name"]: r["released"] for r in ra_mat_aa})
    write_timestamp(tat_ca | cu, hang_moi, da_bao)
    # LOW-375 luat 3: CHI danh dau thu DA VAO BAO CAO. Phan bi tran CEILING_*
    # cat khong duoc danh dau — mai no van con moi thi van phai len duoc, dung
    # bai hoc cua scan_business ("danh dau het la may xoa tin").
    hf_seen.mark(m["id"] for m in hf[:CEILING_HF])
    story_seen.mark(scan_common.standard_link(t.get("link", ""))
                    for t in tin[:CEILING_STORY])
    gh_seen.mark(github_key(g) for g in gh[:CEILING_GH])
    write_required(ra_mat_aa, leo_hang, hf)
    if not a.khong_bat_buoc:
        # In ra STDERR, khong phai stdout: `scan_prepare` chep nguyen stdout vao
        # brief roi TU in danh sach bat buoc mot lan nua — Nova doc hai ban cua
        # cung mot danh sach, va ban in tu day con mang cau luat CU ("script ghi
        # manifest se tu choi neu thieu") mau thuan voi luat that tu 05/09
        # ("thieu thi script tu them"). Mot danh sach, mot cau luat (06/09/2026).
        import io
        import contextlib
        _dem = io.StringIO()
        with contextlib.redirect_stdout(_dem):
            required.in_list_clean("nova")
        print(_dem.getvalue(), file=sys.stderr, end="")


LABEL_BOARD = model_boards.LABEL_BOARD


# Tran in an. Do 06/09/2026: o trang thai production (arena song + co moc cu de
# so hang) bao cao ra 13.635 ky tu, trong khi brief cua scan_prepare cat o
# 12.000 — tuc LIVEBENCH va OPENROUTER USAGE bi nuot mat truoc khi Nova nhin
# thay, va khong co dau hieu nao bao la da cut. Ba muc duoi day truoc do KHONG
# CO CAN TREN, mot ngay xau la nuot sach phan duoi bao cao.
CEILING_GH = 10           # ban phat hanh engine — truoc: vo han
CEILING_HF = 10
# TIN TU HANG: truoc LOW-375 la so 10 go thang trong vong in. Dat ten vi gio
# no con la moc DANH DAU DA-THAY — hai cho phai dung CUNG mot con so, lech
# nhau thi tin in ra ma khong duoc danh dau (bao lai hom sau), hoac nguoc
# lai tin bi cat ma van bi danh dau (mat vinh vien).
CEILING_STORY = 10
CEILING_BOARD = 5          # moi bang xep hang — truoc: 8
REGION_LABEL = {"my": "My", "tq": "TQ", "khac": "  "}
# Ban ke khai bang xep hang. main() dung de kiem `bang_so` khong lech, va bao
# cao dung de in con so. Go tay con so nay thi no lech ngay: ban dau ghi 20
# trong khi that su co 23 (test_model_boards bat duoc).
LOCK_BOARD = model_boards.LOCK_BOARD
COUNT_BOARD = model_boards.COUNT_BOARD


def _in_board(nhan: str, rows, n: int = CEILING_BOARD, ngay=None, diem_hau: str = "",
             them=None):
    """In mot bang xep hang theo dung mot khuon. Truoc 06/09/2026 moi bang tu
    in mot kieu, nen them bang la them mot doan lap va mot co hoi lech dinh
    dang; gio doi lai thanh mot ham."""
    rows = rows or []
    if not rows:
        return
    print(f"\n=== {nhan}{f' — {ngay}' if ngay else ''} ===")
    for r in rows[:n]:
        vung = REGION_LABEL.get(r.get("region") or "khac", "  ")
        org = str(r.get("organization") or "")[:13]
        phu = (them(r) or "") if them else ""
        print(f"  #{str(r.get('rank')):<3s}[{vung}] {str(r.get('name'))[:38]:<39s} "
              f"{str(r.get('score')):>6s}{diem_hau} {org:<14s}{phu}")


def _in_report(k: dict):
    if k.get("new_on_our_router"):
        print(f"\n=== MOI TRONG CATALOG CUA HERMES ({len(k['new_on_our_router'])}) "
              "— danh muc model cua hermes-agent, CHUA chac 9router goi duoc ===")
        for m in k["new_on_our_router"][:15]:
            print(f"  {m['id']}")
    aa = k.get("aa_scores") or {}
    rm = k.get("aa_releases_unreported") or []
    if rm:
        print(f"\n=== RA MAT THEO BANG CHAM DIEM ({len(rm)}) — artificialanalysis, "
              "CHUA BAO LAN NAO, moi ten goc mot dong ===")
        for r in rm[:12]:
            hc = f"#{r['coding_rank']} coding" if r.get("coding_rank") else "chua co diem coding"
            print(f"  {r['released']}  [{r['country']}] {r['original_name'][:34]:<35s} "
                  f"{str(r['maker'])[:14]:<15s} coding={r['coding']}  {hc}"
                  f"{'  MO NGUON' if r.get('open_weights') else ''}")
    tc = aa.get("top_coding") or []
    if tc:
        print("\n=== TOP CODING (artificialanalysis) ===")
        for r in tc[:10]:
            ca = f"cache ${r['cache_price']}" if r["cache_price"] is not None else "khong cache"
            print(f"  {str(r['coding']):>5s}  [{r['country']}] {str(r['name'])[:34]:<35s} "
                  f"{r['released']}  vao ${r['input_price']}  {ca}")
    nm = aa.get("new_open_weights") or []
    if nm:
        print(f"\n=== VUA MO NGUON ({len(nm)}) — bat duoc ca hang khong co RSS ===")
        for r in nm[:8]:
            print(f"  {r['released']}  [{r['country']}] {str(r['name'])[:34]:<35s} "
                  f"{r['license']}  coding={r['coding']}")

    leo = k.get("rank_climbs") or []
    if leo:
        print(f"\n=== VUA LEO HANG ({len(leo)}) — thay doi so voi lan quet truoc ===")
        for r in leo[:10]:
            nhan = LABEL_BOARD.get(r["board"], r["board"])
            print(f"  [{nhan:<9s}] {r['name'][:36]:<37s} {r['note']}")

    tin = k.get("company_news") or []
    if tin:
        print(f"\n=== TIN TU HANG ({len(tin)}) — su kien so dang ky khong the hien ===")
        for t in tin[:CEILING_STORY]:
            print(f"  {t['date']}  [{t['company']:<15s}] {t['title'][:70]}")

    gh = k.get("releases") or []
    if gh:
        print(f"\n=== ENGINE SUY LUAN RA BAN MOI ({len(gh)}) ===")
        for g in gh[:CEILING_GH]:
            print(f"  {g['date']}  {g['repo']:<28s} {g['tag']}")

    hong = k.get("broken_boards") or []
    hong_khac = k.get("broken_sources") or []
    if hong or hong_khac:
        n = len(hong) + len(hong_khac)
        print(f"\n=== NGUON KHONG LAY DUOC LAN NAY ({n}) — cac nguon duoi "
              "day VANG khoi bao cao, KHONG phai 'khong co gi moi' ===")
        if hong:
            print("  bang xep hang: " + ", ".join(LABEL_BOARD.get(x, x) for x in hong))
        if hong_khac:
            # Nguon nem loi (parse doi schema) hoac tra rong bat thuong. Truoc
            # 06/09/2026 chung khong vao muc nay: mot loi parse giet ca luot
            # quet ma bao cao van "sach".
            print("  nguon khac: " + ", ".join(hong_khac))

    hf = k.get("hf_trending") or []
    if hf:
        print(f"\n=== VUA THA TRONG SO TREN HUGGINGFACE ({len(hf)}) — bat truoc "
              "router 1-3 ngay, va bat ca model KHONG BAO GIO len router ===")
        for m in hf[:CEILING_HF]:
            print(f"  {m['released']}  {m['id'][:44]:<45s} trending {str(m['score']):>4s}  "
                  f"{(m['downloads'] or 0):>10,d} tai  {m['pipeline_tag'][:18]}")

    # ---- Bang xep hang: tu day tro xuong la BOI CANH, khong phai tin moi. Giu
    # 5 dong/bang co chu dich — muc tren (ra mat / leo hang) moi la thu Nova
    # phai dua, va bao cao co TRAN 12.000 ky tu o brief cua scan_prepare.
    print(f"\n\n########## BANG XEP HANG — {COUNT_BOARD} bang, top {CEILING_BOARD} "
          "moi bang (boi canh de xep thu tu, khong phai tin) ##########")

    # MOT vong cho ca 21 bang in theo khuon chung, doc tu ban dang ky
    # (`model_boards.BOARD`, thu tu trong do CHINH LA thu tu in). Truoc 07/09/2026
    # day la 21 loi goi viet tay, moi cai tu ghi lai tieu de, hau to diem va cot
    # phu — them mot bang la them mot doan lap va mot co hoi lech dinh dang.
    for b in model_boards.BOARD:
        if not b.in_bang:
            continue
        rows, ngay_b = model_boards.rank_and_date(k, b)
        _in_board(b.tieu_de, rows, ngay=ngay_b, diem_hau=b.diem_hau, them=b.them)


if __name__ == "__main__":
    main()
