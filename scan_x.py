#!/usr/bin/env python3
"""scan_x.py — quet tin tu X cho vai Qinn (brand donniechublog).

KHONG tu crawl X. Session X song tren may crawler (Chrome da login, extension
`extension-crawler` cua repo tech-news-publishing); may nay chi DOC lai qua
`GET /tweets` cua social-publishing server. Xem docs/qinn.md ben repo do.

Hai thu tep nay co y KHONG lam:
  * Khong cham diem de CAT tin. Diem co hoc chi de XEP thu tu Qinn doc — cach
    cu (classifier DeepSeek 3 bac ben social-publishing) da chung minh hau qua:
    nhung ngay cuoi truoc khi crawler tat, moi me deu `relevant 0`, tuc no loai
    sach ma khong ai xem lai duoc. Bo loc that la Qinn.
  * Khong im lang khi khong co tin. `freshness` tu server cho biet tweet moi
    nhat crawl luc nao; qua TRAN_CU gio thi bao cao mo dau bang canh bao
    "crawler dung", khong phai "hom nay khong co gi" — dung cho da im 12 ngay
    (31/08-12/09/2026).

Dung:
    venv/bin/python scan_x.py --gio 6 --out /tmp/x.json
"""
import argparse
import json
import math
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                             # noqa: E402
from quet_chung import VN, UA                                # noqa: E402

env_load.nap()

STATE = env_load.state_dir() / "x_seen.json"
MAC_DINH_URL = "https://webhook-social-publishing.mated.dev"
# Crawler quay 15 phut/lan. Qua 3 tieng khong co tweet moi nghia la no dung,
# khong phai X im — ca home lan list deu khong bao gio vang the lau.
TRAN_CU_GIO = 3
# Bo nho da-thay giu 14 ngay: tweet cu hon the ma quay lai thi coi nhu tin moi.
GIU_NGAY = 14

# Text ngan hon the ma khong co link ngoai thi khong co gi de doc — mot dong
# hype ("this is wild"), anh don, hoac quote trong khong.
TOI_THIEU_KY_TU = 60

LINK_NANG = re.compile(
    r"https?://(?:www\.)?(?:github\.com|arxiv\.org|huggingface\.co|"
    r"[a-z0-9.-]*\.?(?:dev|docs?\.[a-z]+)|gitlab\.com|news\.ycombinator\.com)",
    re.I,
)
LINK_BAT_KY = re.compile(r"https?://\S+", re.I)


def doc_tweets(gio: int, limit: int) -> dict:
    """GET /tweets — tra nguyen goi {count, freshness, tweets}."""
    base = (os.environ.get("X_READ_URL") or MAC_DINH_URL).rstrip("/")
    key = os.environ.get("X_READ_KEY") or ""
    if not key:
        sys.exit("[LOI] thieu X_READ_KEY (secret.blog.env) — khong doc duoc /tweets")
    r = httpx.get(
        f"{base}/tweets",
        params={"hours": gio, "limit": limit},
        headers={"x-api-key": key, "User-Agent": UA},
        timeout=60,
    )
    if r.status_code != 200:
        sys.exit(f"[LOI] GET /tweets -> {r.status_code}: {r.text[:300]}")
    return r.json()


def da_thay() -> dict:
    if not STATE.exists():
        return {}
    d = json.loads(STATE.read_text(encoding="utf-8")).get("khoa", {})
    return d if isinstance(d, dict) else {k: time.time() for k in d}


def ghi_moc(khoa: dict) -> None:
    """Giu cac truong khac cua tep, cat bo nho theo THOI GIAN (khong theo ten)."""
    STATE.parent.mkdir(parents=True, exist_ok=True)
    cu = {}
    if STATE.exists():
        try:
            cu = json.loads(STATE.read_text(encoding="utf-8"))
        except ValueError:
            cu = {}
    nguong = time.time() - GIU_NGAY * 86400
    cu["khoa"] = {k: v for k, v in khoa.items() if v >= nguong}
    cu["ghi_luc"] = datetime.now(timezone.utc).isoformat()
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(cu, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(STATE)


def mot_dong(text: str, tran: int = 140) -> str:
    s = re.sub(r"\s+", " ", (text or "").strip())
    return s[:tran]


def diem_co_hoc(t: dict) -> int:
    """Chi de XEP thu tu Qinn doc. Khong cat tin theo so nay."""
    m = t.get("metrics") or {}
    def so(x):
        try:
            return max(0, int(x))
        except (TypeError, ValueError):
            return 0
    d = 0.0
    d += 3 * math.log10(1 + so(m.get("views")))
    d += 4 * math.log10(1 + so(m.get("likes")))
    d += 2 * math.log10(1 + so(m.get("replies")))
    text = t.get("text") or ""
    d += min(len(text), 1500) / 120.0          # bai dai = co gi de doc
    if LINK_NANG.search(text):
        d += 12                                # github/arxiv/docs: nguon goc
    if t.get("type") in ("thread", "article"):
        d += 6                                 # thread/article = co trien khai
    if (t.get("media") or []):
        d += 2
    return round(d)


def loc(tweets: list, cu: dict) -> tuple:
    """(giu, bo_dem) — bo_dem noi ro vi sao, de bao cao doi chieu duoc."""
    bo = {"reply": 0, "ngan": 0, "da_thay": 0, "rong": 0}
    giu = []
    for t in tweets:
        tid = t.get("id") or ""
        text = (t.get("text") or "").strip()
        if not tid or not t.get("url"):
            bo["rong"] += 1
            continue
        if t.get("type") == "reply":
            bo["reply"] += 1
            continue
        if tid in cu:
            bo["da_thay"] += 1
            continue
        if len(text) < TOI_THIEU_KY_TU and not LINK_BAT_KY.search(text):
            bo["ngan"] += 1
            continue
        giu.append(t)
    return giu, bo


def ra_tin(t: dict) -> dict:
    """Mot tweet -> mot muc `tin_moi`, cung hinh dang voi scan_business de
    manifest_ghi --nguon chon duoc bang so thu tu k."""
    ts = t.get("timestamp") or t.get("crawledAt") or ""
    try:
        ngay = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(VN).strftime("%Y-%m-%d")
    except ValueError:
        ngay = ""
    handle = (t.get("author") or {}).get("handle") or ""
    handle = handle if handle.startswith("@") else f"@{handle}" if handle else ""
    m = t.get("metrics") or {}
    media = t.get("media") or []
    return {
        "id": t.get("id") or "",
        "tieu_de": mot_dong(t.get("title") or t.get("text") or ""),
        "link": t.get("url"),
        "ngay": ngay,
        "toa_soan": handle,
        "so_bao": 1,
        "nguon_x": t.get("source") or "home",
        "loai": t.get("type") or "tweet",
        "so_lieu": {k: m.get(k) for k in ("views", "likes", "replies", "retweets")},
        "so_anh": len(media),
        "diem": diem_co_hoc(t),
        # Qinn doc phan nay de cham diem. Cat 1200 ky tu: du cho mot thread da
        # gop, con prompt thi an theo kich thuoc tep nay.
        "text": (t.get("text") or "")[:1200],
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="Quet tin X cho vai Qinn")
    ap.add_argument("--gio", type=int, default=6, help="Cua so gio (mac dinh 6)")
    ap.add_argument("--top", type=int, default=40,
                    help="Van an toan: toi da bao nhieu tin dua cho Qinn")
    ap.add_argument("--limit", type=int, default=1000, help="Tran doc tu server")
    ap.add_argument("--out", help="Ghi JSON ra tep")
    ap.add_argument("--state", help="File seen khac (de TEST khong dung x_seen.json that)")
    ap.add_argument("--lan-dau", action="store_true", help="Chi ghi moc, khong bao")
    a = ap.parse_args()

    global STATE
    if a.state:
        STATE = Path(a.state)

    goi = doc_tweets(a.gio, a.limit)
    tweets = goi.get("tweets") or []
    fresh = goi.get("freshness") or {}
    cu = da_thay()
    now = time.time()

    if a.lan_dau:
        ghi_moc({**cu, **{t["id"]: now for t in tweets if t.get("id")}})
        print(f"Da ghi moc {len(tweets)} tweet. Lan sau chi bao cai moi.")
        return 0

    giu, bo = loc(tweets, cu)
    giu.sort(key=diem_co_hoc, reverse=True)
    chon = [ra_tin(t) for t in giu[: a.top]]

    # Canh bao tuoi du lieu — thu DUY NHAT phan biet "khong co tin dang" voi
    # "crawler dung". Tinh tu freshness cua server, khong tu so tweet doc duoc.
    canh_bao = []
    moc = fresh.get("latestCrawledAt")
    tre_gio = None
    if moc:
        try:
            tre_gio = (datetime.now(timezone.utc)
                       - datetime.fromisoformat(moc.replace("Z", "+00:00"))).total_seconds() / 3600
        except ValueError:
            tre_gio = None
    if tre_gio is None:
        canh_bao.append("Server khong tra moc crawl nao — DB tin X co the rong.")
    elif tre_gio > TRAN_CU_GIO:
        canh_bao.append(
            f"CRAWLER DUNG: tweet moi nhat da {tre_gio:.1f} gio truoc "
            f"({moc}). Vong quet 15 phut/lan nen qua {TRAN_CU_GIO}h la may crawler "
            "tat, Chrome mat session X, hoac vong lap bi tat. Bao Ong Chu — "
            "dung ket luan 'hom nay khong co tin'."
        )

    ket = {
        "quet_luc": datetime.now(timezone.utc).isoformat(),
        "cua_so_gio": a.gio,
        "tong_quet": len(tweets),
        "tin_moi": chon,
        "bo_qua": bo,
        "freshness": fresh,
        "tre_gio": round(tre_gio, 1) if tre_gio is not None else None,
        "canh_bao": canh_bao,
    }
    if a.out:
        Path(a.out).write_text(json.dumps(ket, ensure_ascii=False, indent=2), encoding="utf-8")
        print(a.out)
    else:
        print(f"=== {len(chon)}/{len(tweets)} tweet (bo: {bo}) ===")
        for c in canh_bao:
            print(f"[!] {c}", file=sys.stderr)
        for k, t in enumerate(chon, 1):
            print(f"#{k} [{t['diem']}] {t['nguon_x']} {t['toa_soan']}: {t['tieu_de'][:90]}")

    # CHI danh dau tin DA DUA cho Qinn. Tin bi --top cat hom nay van con moi
    # cho lan sau — dung bai hoc cua scan_business: danh dau het la may xoa tin.
    ghi_moc({**cu, **{t["id"]: now for t in chon if t.get("id")}})
    return 0


if __name__ == "__main__":
    sys.exit(main())
