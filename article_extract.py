#!/usr/bin/env python3
"""Trich xuat bai viet tu donniechu.com ra JSON tat dinh — khong dung LLM.

Dung <article>, JSON-LD BlogPosting va OpenGraph de lay tieu de, outline
(h2/h3), toan bo doan van, va anh noi dung (loai avatar/logo).
"""
import argparse
import importlib
import json
import sys
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_common                                            # noqa: E402

UA = "Mozilla/5.0 (compatible; donniechu-content-bot/1.0)"

# Chan host noi bo. URL toi day KHONG phai luon tin duoc: cape_chuan_bi.py boc
# dung URL Ong Chu dan vao chat, tu_lieu.py boc link nguon cac vai quet ve tu
# web. Bot lai chay ngay tren server cung 9router (127.0.0.1:20128), dashboard
# (9130) va tunnel — nen mot URL tro nguoc vao trong la fetch thang vao ruot he
# thong. Cong /bai da chan viec nay tu lau (duyet_lenh._HOST_CAM); duong nay thi
# chua, phat hien 06/09/2026.
# Lay cong tu `quet_chung` chu khong chep lai regex (doi 06/09/2026 dot 2).
# `quet_chung` la module thuan, khong keo approve_service vao — nen li do cu de
# chep ("tep nay chay doc lap trong tien trinh con") khong con dung. Ban chep
# tay chi so khop CHUOI nen "127.1" va "2130706433" deu lot; ban chung dung
# `ipaddress` + `inet_aton` va la MOT cho duy nhat cho ca day chuyen.
_kiem_host = scan_common.check_url
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


def _parser() -> str:
    """Ten parser cho BeautifulSoup: lxml neu co, khong thi html.parser + KEU.

    Audit D2 de nghi bo han lxml va dung html.parser (duyet_lenh.py dung parser
    do tu lau). Do KHONG mien phi, da thu: hai parser cho ket qua y het tren HTML
    dong the day du, nhung voi `<p>` KHONG DONG — hop le trong HTML va rat pho
    bien tren bao that — lxml tu dong the con html.parser long doan sau vao doan
    truoc:
        <article><h2>A</h2><p>Mot.<p>Hai.</article>
        lxml        -> ["Mot.", "Hai."]
        html.parser -> ["Mot. Hai.", "Hai."]     (gop VA nhan doi)
    Doan bi nhan doi di thang vao `cau_co_so` cua brief, nen giu lxml lam parser
    CHINH.

    Nhung thieu lxml khong duoc chet CAM: truoc day `BeautifulSoup(html, "lxml")`
    nem FeatureNotFound, article_extract chet, con tu_lieu chi thay tien trinh
    con thoat khac 0 (dung lop loi C1). Nay roi ve html.parser va noi ro la ket
    qua kem hon, thay vi khong co ket qua nao."""
    global _DA_BAO_PARSER
    try:
        # import_module chu khong `import lxml`: van import THAT (bat duoc ban
        # cai vo), nhung khong de lai mot ten thua cho pyflakes keu — C4 dinh
        # cho CI chan tren pyflakes.
        importlib.import_module("lxml")
        return "lxml"
    except ImportError:
        if not _DA_BAO_PARSER:
            _DA_BAO_PARSER = True
            print("[article_extract] THIEU lxml -> dung html.parser: doan van tren "
                  "trang co <p> khong dong se bi gop/nhan doi. Cai lxml de dung "
                  "(xem requirements.txt).", file=sys.stderr)
        return "html.parser"


_DA_BAO_PARSER = False


def extract(url: str) -> dict:
    html = fetch(url)
    soup = BeautifulSoup(html, _parser())
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
