#!/usr/bin/env python3
"""Tim NGUON cho mot tin — buoc research, thuoc khau cua Finn.

Vi sao dat o day: viec di tim nguon la RESEARCH, do la nghe cua Finn. Truoc day
Iris tu tim nguon de lay anh, Quinn lai tu tim nguon de lay chu — hai lan tra
cuu cho cung mot tin, va co the ra hai bo bai khac nhau, khien bai viet noi mot
dang con tam anh cho thay mot dang khac.

Nay Finn lam mot lan ngay sau khi Ong Chu chon tin, ghi ra
state/nguon_<draft_id>.json, roi ca Iris lan Quinn cung doc tep do.

Cach tim: Google News KHONG cho URL bai (link cua no la duong chuyen huong chay
bang JS, chuoi CBMi khong phai base64 cua URL, con DuckDuckGo tra 202 chan bot).
Nhung Google News CO cho ten mien toa soan o <source url>. Nen di duong vong:
ten mien -> RSS cua chinh toa soan -> khop tieu de -> ra link bai that.

Dung:
    venv/bin/python nguon_bai.py --tieu-de "..." --link "..." --out state/nguon_x.json
"""
import argparse
import concurrent.futures as cf
import json
import re
import sys
import urllib.parse as up
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx

UA = "Mozilla/5.0 (compatible; donniechu-scout/1.0)"
HDR = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
GNEWS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
SO_NGUON = 4

TU_RONG = {"the", "a", "an", "of", "in", "on", "to", "for", "and", "or", "with",
           "new", "ai", "model", "is", "its", "as", "at", "by", "from", "how"}


def _tu(t: str) -> set:
    return {w for w in re.sub(r"[^\w\s]", " ", t.lower()).split()
            if w not in TU_RONG and len(w) > 2}


def _tai(url: str, timeout=20):
    return httpx.get(url, headers=HDR, timeout=timeout, follow_redirects=True)


def tim(tieu_de: str, link: str, so=SO_NGUON) -> dict:
    ra = [{"url": link, "loai": "gốc", "tieu_de": tieu_de}]
    try:
        its = ET.fromstring(_tai(GNEWS.format(q=up.quote(tieu_de)), 25).content
                            ).findall(".//item")
    except Exception as e:                                   # noqa: BLE001
        print(f"[nguon_bai] google news hong: {type(e).__name__}", file=sys.stderr)
        its = []

    mien = []
    for it in its[: so * 3]:
        src = it.find("source")
        u = (src.get("url") if src is not None else "") or ""
        if u:
            u = u.rstrip("/")
            if u not in [m for m, _ in mien]:
                mien.append((u, it.findtext("title") or ""))

    goc = _tu(tieu_de)

    def _trong_feed(cap):
        m, _ = cap
        for duong in ("/feed/", "/rss", "/feed", "/rss.xml", "/index.xml"):
            try:
                rr = _tai(m + duong, 15)
                if rr.status_code != 200 or b"<item" not in rr.content[:400_000]:
                    continue
                for i in ET.fromstring(rr.content).findall(".//item"):
                    t = i.findtext("title") or ""
                    chung = goc & _tu(t)
                    if chung and len(chung) / max(len(goc), 1) >= 0.5:
                        return {"url": i.findtext("link") or "", "loai": "báo",
                                "tieu_de": t, "toa_soan": m}
                return None
            except Exception:                                # noqa: BLE001
                continue
        return None

    thay = {link}
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for kq in ex.map(_trong_feed, mien[: so * 3]):
            if kq and kq["url"] and kq["url"] not in thay:
                thay.add(kq["url"])
                ra.append(kq)
            if len(ra) > so:
                break
    return {"tieu_de": tieu_de, "link_goc": link, "trang": ra}


def main():
    ap = argparse.ArgumentParser(description="Tim nguon cho mot tin (viec cua Finn)")
    ap.add_argument("--tieu-de", required=True)
    ap.add_argument("--link", required=True)
    ap.add_argument("--so", type=int, default=SO_NGUON)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    kq = tim(a.tieu_de, a.link, a.so)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(kq, ensure_ascii=False, indent=2),
                           encoding="utf-8")
    print(a.out)
    for t in kq["trang"]:
        print(f"  [{t['loai']}] {t['url'][:88]}", file=sys.stderr)
    return 0 if len(kq["trang"]) > 1 else 1


if __name__ == "__main__":
    sys.exit(main())
