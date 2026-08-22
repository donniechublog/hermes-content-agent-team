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

ROOT = Path.home() / "content-team"
STATE = ROOT / "state" / "models_seen.json"
UA = "Mozilla/5.0 (compatible; donniechu-scout/1.0)"

OPENROUTER = "https://openrouter.ai/api/v1/models"
CATALOG = "https://hermes-agent.nousresearch.com/docs/api/model-catalog.json"
ARENA = "https://lmarena.ai/leaderboard"

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
    return httpx.get(url, timeout=timeout, follow_redirects=True,
                     headers={"User-Agent": UA})


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

def da_thay() -> set:
    if STATE.exists():
        return set(json.loads(STATE.read_text(encoding="utf-8")).get("ids", []))
    return set()


def ghi_moc(ids: set):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(
        {"cap_nhat": datetime.now(timezone.utc).isoformat(), "ids": sorted(ids)},
        ensure_ascii=False, indent=2), encoding="utf-8")


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

    tat_ca = {m["id"] for m in orouter} | {m["id"] for m in catalog}
    cu = da_thay()

    if a.lan_dau:
        ghi_moc(tat_ca)
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

    ket = {
        "quet_luc": datetime.now(timezone.utc).isoformat(),
        "top_moi_bang": a.top,
        "model_moi": moi,
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

    ghi_moc(tat_ca | cu)


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
