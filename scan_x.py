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
from datetime import datetime, timezone
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                             # noqa: E402
import scan_seen                                              # noqa: E402
import state_paths                                           # noqa: E402
from scan_common import VN, UA                                # noqa: E402

env_load.load()

STATE = env_load.state_dir() / state_paths.X_SEEN_FILE
DEFAULT_URL = "https://webhook-social-publishing.mated.dev"
# Crawler quay 15 phut/lan. Qua 3 tieng khong co tweet moi nghia la no dung,
# khong phai X im — ca home lan list deu khong bao gio vang the lau.
CEILING_OLD_HOURS = 3
# Bo nho da-thay giu 14 ngay: tweet cu hon the ma quay lai thi coi nhu tin moi.
KEEP_DATE = 14

# Text ngan hon the ma khong co link ngoai thi khong co gi de doc — mot dong
# hype ("this is wild"), anh don, hoac quote trong khong.
MIN_KY_FROM = 60

LINK_CAPABILITY = re.compile(
    r"https?://(?:www\.)?(?:github\.com|arxiv\.org|huggingface\.co|"
    r"[a-z0-9.-]*\.?(?:dev|docs?\.[a-z]+)|gitlab\.com|news\.ycombinator\.com)",
    re.I,
)
LINK_CATCH_KY = re.compile(r"https?://\S+", re.I)

# `skipped` codes (LOW-240) -> the words the stdout summary always printed, so the
# debug line `bo: {...}` stays byte-identical.
SKIPPED_LABELS = {"reply": "reply", "too_short": "ngan", "already_seen": "da_thay",
                  "missing_id_or_url": "rong"}


def read_tweets(gio: int, limit: int) -> dict:
    """GET /tweets — tra nguyen goi {count, freshness, tweets}."""
    base = (os.environ.get("X_READ_URL") or DEFAULT_URL).rstrip("/")
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


# LOW-375: bo nho da-thay dung CHUNG `scan_seen.SeenStore` voi Finn/Nova/Vera.
# Doan cu o day da lam dung (cat theo thoi gian, giu truong la) nhung la ban
# chep tay thu hai; gio chi con MOT ban, va no ghi nguyen tu bang ten tep tam
# mang PID — Qinn chay HAI luot mot ngay nen day khong phai chuyen ly thuyet.
# `KEEP_DATE = 14` giu nguyen: tweet cu hon the ma quay lai thi coi nhu tin moi.


def seen_store() -> scan_seen.SeenStore:
    return scan_seen.SeenStore(STATE, keep_days=KEEP_DATE)


def already_see() -> dict:
    return seen_store().read()


def one_line(text: str, tran: int = 140) -> str:
    s = re.sub(r"\s+", " ", (text or "").strip())
    return s[:tran]


def score_mechanical(t: dict) -> int:
    """Chi de XEP thu tu Qinn doc. Khong cat tin theo so nay."""
    m = t.get("metrics") or {}
    def _as_int(x):
        try:
            return max(0, int(x))
        except (TypeError, ValueError):
            return 0
    d = 0.0
    d += 3 * math.log10(1 + _as_int(m.get("views")))
    d += 4 * math.log10(1 + _as_int(m.get("likes")))
    d += 2 * math.log10(1 + _as_int(m.get("replies")))
    text = t.get("text") or ""
    d += min(len(text), 1500) / 120.0          # bai dai = co gi de doc
    if LINK_CAPABILITY.search(text):
        d += 12                                # github/arxiv/docs: nguon goc
    if t.get("type") in ("thread", "article"):
        d += 6                                 # thread/article = co trien khai
    if (t.get("media") or []):
        d += 2
    return round(d)


def filter(tweets: list, cu: dict) -> tuple:
    """(giu, bo_dem) — bo_dem noi ro vi sao, de bao cao doi chieu duoc."""
    bo = {"reply": 0, "too_short": 0, "already_seen": 0, "missing_id_or_url": 0}
    giu = []
    for t in tweets:
        tid = t.get("id") or ""
        text = (t.get("text") or "").strip()
        if not tid or not t.get("url"):
            bo["missing_id_or_url"] += 1
            continue
        if t.get("type") == "reply":
            bo["reply"] += 1
            continue
        if tid in cu:
            bo["already_seen"] += 1
            continue
        if len(text) < MIN_KY_FROM and not LINK_CATCH_KY.search(text):
            bo["too_short"] += 1
            continue
        giu.append(t)
    return giu, bo


def out_story(t: dict) -> dict:
    """Mot tweet -> mot muc `new_stories`, cung hinh dang voi scan_business de
    manifest_write --nguon chon duoc bang so thu tu k."""
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
        "title": one_line(t.get("title") or t.get("text") or ""),
        "link": t.get("url"),
        "date": ngay,
        "author": handle,
        "outlet_count": 1,
        "x_source": t.get("source") or "home",
        "tweet_type": t.get("type") or "tweet",
        "metrics": {k: m.get(k) for k in ("views", "likes", "replies", "retweets")},
        "media_count": len(media),
        "mechanical_score": score_mechanical(t),
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

    goi = read_tweets(a.gio, a.limit)
    tweets = goi.get("tweets") or []
    fresh = goi.get("freshness") or {}
    cu = already_see()

    if a.lan_dau:
        seen_store().mark(t["id"] for t in tweets if t.get("id"))
        print(f"Da ghi moc {len(tweets)} tweet. Lan sau chi bao cai moi.")
        return 0

    giu, bo = filter(tweets, cu)
    giu.sort(key=score_mechanical, reverse=True)
    chon = [out_story(t) for t in giu[: a.top]]

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
    elif tre_gio > CEILING_OLD_HOURS:
        canh_bao.append(
            f"CRAWLER DUNG: tweet moi nhat da {tre_gio:.1f} gio truoc "
            f"({moc}). Vong quet 15 phut/lan nen qua {CEILING_OLD_HOURS}h la may crawler "
            "tat, Chrome mat session X, hoac vong lap bi tat. Bao Ong Chu — "
            "dung ket luan 'hom nay khong co tin'."
        )

    ket = {
        "scanned_at": datetime.now(timezone.utc).isoformat(),
        "window_hours": a.gio,
        "scanned_total": len(tweets),
        "new_stories": chon,
        "skipped": bo,
        "freshness": fresh,
        "crawl_lag_hours": round(tre_gio, 1) if tre_gio is not None else None,
        "warnings": canh_bao,
    }
    if a.out:
        Path(a.out).write_text(json.dumps(ket, ensure_ascii=False, indent=2), encoding="utf-8")
        print(a.out)
    else:
        bo_hien = {SKIPPED_LABELS.get(k, k): v for k, v in bo.items()}
        print(f"=== {len(chon)}/{len(tweets)} tweet (bo: {bo_hien}) ===")
        for c in canh_bao:
            print(f"[!] {c}", file=sys.stderr)
        for k, t in enumerate(chon, 1):
            print(f"#{k} [{t['mechanical_score']}] {t['x_source']} {t['author']}: {t['title'][:90]}")

    # CHI danh dau tin DA DUA cho Qinn. Tin bi --top cat hom nay van con moi
    # cho lan sau — dung bai hoc cua scan_business: danh dau het la may xoa tin.
    seen_store().mark(t["id"] for t in chon if t.get("id"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
