#!/usr/bin/env python3
"""Trich xuat bai viet tu donniechu.com ra JSON tat dinh — khong dung LLM.

Dung <article>, JSON-LD BlogPosting va OpenGraph de lay tieu de, outline
(h2/h3), toan bo doan van, va anh noi dung (loai avatar/logo).
"""
import argparse
import json
import re
import sys
from urllib.parse import urljoin, urlsplit

import httpx
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (compatible; donniechu-content-bot/1.0)"

# Chan host noi bo. URL toi day KHONG phai luon tin duoc: jean_chuan_bi.py boc
# dung URL Ong Chu dan vao chat, tu_lieu.py boc link nguon cac vai quet ve tu
# web. Bot lai chay ngay tren server cung 9router (127.0.0.1:20128), dashboard
# (9130) va tunnel — nen mot URL tro nguoc vao trong la fetch thang vao ruot he
# thong. Cong /bai da chan viec nay tu lau (duyet_lenh._HOST_CAM); duong nay thi
# chua, phat hien 06/09/2026.
# Chep lai regex thay vi import duyet_lenh: tep nay la script doc lap, chay bang
# venv rieng trong tien trinh con; keo ca the gioi approve_service vao chi de
# dung mot regex la doi lay rui ro import de lay mot dong code. Sua mot ben thi
# sua ca hai.
_HOST_CAM = re.compile(
    r"^(localhost$|127\.|10\.|192\.168\.|169\.254\.|0\.)"
    r"|^172\.(1[6-9]|2\d|3[01])\."
    r"|\.(local|internal|netbird\.mated)$", re.I)


def _kiem_host(url: str, cho: str = "URL") -> None:
    """Nem ValueError neu URL tro vao mang noi bo. Chi so khop TEN host, khong
    resolve DNS — cung muc do voi cong /bai, du cho mo hinh rui ro nay."""
    p = urlsplit(str(url))
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError(f"{cho} phai la http/https day du: {url!r}")
    if _HOST_CAM.search(p.hostname):
        raise ValueError(f"{cho} tro vao host noi bo ({p.hostname}) — khong boc.")
SKIP_IMG_HINTS = ("avatar", "logo", "favicon", "icon-")


def fetch(url: str) -> str:
    # Kiem HAI lan: truoc khi goi, va lai sau khi di het chuoi chuyen huong.
    # Chi kiem URL dau la ho: follow_redirects=True nen mot dia chi cong khai
    # van co the 302 ve 127.0.0.1 — dung tro cu cua SSRF.
    _kiem_host(url)
    r = httpx.get(url, headers={"User-Agent": UA}, timeout=25, follow_redirects=True)
    _kiem_host(r.url, "URL sau chuyen huong")
    r.raise_for_status()
    return r.text


def extract(url: str) -> dict:
    html = fetch(url)
    soup = BeautifulSoup(html, "lxml")
    art = soup.find("article") or soup.find("main") or soup

    def meta(prop):
        tag = soup.find("meta", property=prop) or soup.find("meta", attrs={"name": prop})
        return (tag.get("content") or "").strip() if tag else ""

    title = meta("og:title") or (soup.title.string.strip() if soup.title else "")
    description = meta("og:description") or meta("description")
    og_image = meta("og:image")

    date_published = ""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "{}")
        except Exception:                                    # noqa: BLE001
            continue
        for node in data.get("@graph", [data]):
            if isinstance(node, dict) and node.get("@type") == "BlogPosting":
                date_published = node.get("datePublished", "")
                break
        if date_published:
            break

    outline = []
    for h in art.find_all(["h2", "h3"]):
        text = h.get_text(strip=True)
        if text:
            outline.append({"level": h.name, "text": text})

    paragraphs = []
    for p in art.find_all("p"):
        text = p.get_text(" ", strip=True)
        if text and len(text) > 2:
            paragraphs.append(text)

    images = []
    for im in art.find_all("img"):
        src = im.get("src") or im.get("data-src") or ""
        if not src or any(h in src.lower() for h in SKIP_IMG_HINTS):
            continue
        src = urljoin(url, src)
        if src.startswith("http") and "/_next/image" not in src:
            if src not in images:
                images.append(src)
    if og_image and og_image not in images:
        images.insert(0, og_image)

    word_count = sum(len(p.split()) for p in paragraphs)

    return {
        "url": url,
        "title": title,
        "description": description,
        "date_published": date_published,
        "outline": outline,
        "paragraphs": paragraphs,
        "images": images,
        "word_count": word_count,
    }


def main():
    ap = argparse.ArgumentParser(description="Trich xuat bai viet donniechu.com")
    ap.add_argument("url")
    ap.add_argument("--out", help="Ghi JSON ra file thay vi stdout")
    a = ap.parse_args()
    try:
        data = extract(a.url)
    except Exception as e:                                  # noqa: BLE001
        print(json.dumps({"error": str(e), "url": a.url}, ensure_ascii=False))
        sys.exit(1)
    out = json.dumps(data, ensure_ascii=False, indent=2)
    if a.out:
        with open(a.out, "w", encoding="utf-8") as f:
            f.write(out)
        print(a.out)
    else:
        print(out)


if __name__ == "__main__":
    main()
