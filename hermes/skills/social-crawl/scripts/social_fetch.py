#!/usr/bin/env python3
"""social_fetch.py — Fetch an X/Twitter, Instagram or Facebook post via the internal
social-publishing crawl endpoint. No API key, no OAuth.

Endpoint is async + does warm-up prefetch: the first call after a URL hasn't been
crawled recently can return a false-negative error ("url must be an https x.com or
twitter.com URL", "Instagram media JSON not found for <shortcode>"). This script
polls with retries instead of failing on the first response.

Usage:
    python3 social_fetch.py "<x-instagram-or-facebook-url>"        # print JSON to stdout
    python3 social_fetch.py "<instagram-url>" --download OUT_DIR   # also pull media locally
    python3 social_fetch.py "<x-url>" --download OUT_DIR           # X posts rarely carry
                                                                     # media, but downloads
                                                                     # any that's present
    python3 social_fetch.py "<url>" --tries 10

Instagram media downloads as OUT_DIR/NN.jpg or NN.mp4 (+ NN-thumb.jpg for video
covers), numbered by carousel order starting at 01. X posts print full JSON
(author, text, metrics, thread, replies); pass --download to also pull any attached
media the same way.

Quirks (do not "fix" without re-reading these):
  - NEVER use `localPath`/`mediaPath` from the response — that path is inside the
    crawl service's own container, not reachable from this shell. Always re-download
    from `media[].url` (CDN link).
  - Video CDN links 302-redirect; downloads always follow redirects (curl -L
    equivalent). Missing that yields a 0-byte file, not an error.
  - CDN URLs carry an expiry param (`oe=`) — never cache one from a previous crawl;
    re-crawl to get a fresh link before downloading.
  - Facebook only matches the NUMERIC permalink `/<owner>/posts/<id>`. A `/share/<code>`
    link 400s, the slug form (`/posts/có-những-…-<id>/`) 500s with "không khoanh được
    post", and `permalink.php?story_fbid=` sees 0 stories. normalize_url() below turns
    all of those into the numeric form — measured 08/09/2026, do not "simplify" it away.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse

ENDPOINT = "https://webhook-social-publishing.mated.dev/crawl-queue"
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")


FACEBOOK_HOSTS = {"facebook.com", "m.facebook.com", "web.facebook.com", "mbasic.facebook.com",
                  "fb.com", "fb.watch"}


def detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if host in {"x.com", "twitter.com", "mobile.twitter.com"}:
        return "x"
    if host in {"instagram.com"}:
        return "instagram"
    if host in FACEBOOK_HOSTS:
        return "facebook"
    sys.exit(f"URL không thuộc x.com/twitter.com, instagram.com hay facebook.com: {url}")


# Facebook answers 400 to a current desktop-Chrome UA but serves the og/canonical shell
# to its own scraper UA — measured 08/09/2026 on a /share/ link: Chrome/120 → 400 with a
# 1.5 KB body, facebookexternalhit → 200 with 340 KB. Only the meta tags are read here.
SHARE_UA = "facebookexternalhit/1.1"


def _fetch_html(url: str) -> str:
    """Page HTML via curl (follow redirects). Empty string on any failure."""
    try:
        return subprocess.run(
            ["curl", "-sL", "-m", "30", "-A", SHARE_UA, url],
            capture_output=True, text=True, timeout=45,
        ).stdout
    except (subprocess.TimeoutExpired, OSError):
        return ""


def normalize_url(url: str, platform: str) -> str:
    """Rewrite a Facebook URL into the only shape the crawl endpoint matches:
    ``https://www.facebook.com/<owner>/posts/<numeric id>``.

    A ``/share/<code>`` link carries no owner or id, so the share page is fetched once
    and its canonical link read out of the HTML. Slug permalinks already carry both —
    the id is the last numeric path segment. Anything unrecognised is returned as-is so
    the endpoint (not this function) has the last word.
    """
    if platform != "facebook":
        return url
    path = urlparse(url).path
    if re.match(r"^/share/", path):
        html = _fetch_html(url)
        m = (re.search(r'rel="canonical"[^>]+href="([^"]+)"', html)
             or re.search(r'property="og:url"[^>]+content="([^"]+)"', html))
        if not m:
            return url
        url = m.group(1)
        path = urlparse(url).path
    m = re.match(r"^/([^/]+)/posts/(.+)$", path)
    if m:
        owner, rest = m.group(1), m.group(2)
        ids = re.findall(r"(\d{6,})", rest)
        if ids:
            return f"https://www.facebook.com/{owner}/posts/{ids[-1]}"
    return url


def crawl(url: str, tries: int) -> dict:
    """POST to the crawl endpoint until it returns `data` (or exhausts `tries`)."""
    last = ""
    for attempt in range(1, tries + 1):
        try:
            out = subprocess.run(
                ["curl", "-s", "-m", "60", "-X", "POST", ENDPOINT,
                 "-H", "Content-Type: application/json",
                 "-d", json.dumps({"url": url})],
                capture_output=True, text=True, timeout=75,
            ).stdout
            payload = json.loads(out)
        except (json.JSONDecodeError, subprocess.TimeoutExpired) as e:
            last = f"{type(e).__name__}: {e}"
            print(f"[crawl {attempt}/{tries}] {last}", file=sys.stderr)
            time.sleep(3)
            continue
        if "data" in payload:
            print(f"[crawl {attempt}/{tries}] OK", file=sys.stderr)
            return payload["data"]
        last = payload.get("error", json.dumps(payload)[:200])
        print(f"[crawl {attempt}/{tries}] {last}", file=sys.stderr)
        time.sleep(3)
    sys.exit(f"CRAWL FAIL sau {tries} lần: {last}")


def fetch_binary(url: str, dest: Path) -> int:
    subprocess.run(
        ["curl", "-sL", "-A", UA, "--retry", "3", "-o", str(dest), url],
        check=False, timeout=300,
    )
    return dest.stat().st_size if dest.exists() else 0


def download_media(media: list, dest: Path) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    ok = 0
    # Facebook media[] carries no `index` — falling back to a constant 1 wrote every
    # photo to 01.jpg, so a 2-photo post came out as one file (measured 08/09/2026).
    # Position in the array is the carousel order for all three platforms.
    for pos, m in enumerate(media, 1):
        idx = m.get("index") or pos
        ext = "mp4" if m.get("type") == "video" else "jpg"
        size = fetch_binary(m["url"], dest / f"{idx:02d}.{ext}")
        if m.get("type") == "video" and m.get("thumbnailUrl"):
            fetch_binary(m["thumbnailUrl"], dest / f"{idx:02d}-thumb.jpg")
        status = "OK" if size > 0 else "FAIL"
        print(f"  #{idx:02d} {m.get('type', '?'):<6} {size:>9} bytes  {status}", file=sys.stderr)
        ok += size > 0
    print(f"DOWNLOAD {ok}/{len(media)} -> {dest}", file=sys.stderr)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url")
    ap.add_argument("--download", metavar="OUT_DIR", default=None,
                     help="Also download media[] to this local folder")
    ap.add_argument("--tries", type=int, default=6,
                     help="Poll attempts against the async crawl endpoint (default 6)")
    args = ap.parse_args()

    platform = detect_platform(args.url)
    url = normalize_url(args.url, platform)
    if url != args.url:
        print(f"[url] {args.url} -> {url}", file=sys.stderr)
    data = crawl(url, args.tries)

    if args.download:
        media = data.get("tweet", {}).get("media") if platform == "x" else data.get("media")
        media = media or []
        if not media:
            print("Không có media[] để tải.", file=sys.stderr)
        else:
            # Facebook returns `author` as a plain name string, X/Instagram as an object —
            # calling .get() on the string form raises AttributeError mid-download.
            author = data.get("author")
            slug = (author.get("handle") if isinstance(author, dict) else author) \
                or data.get("tweet", {}).get("author", {}).get("handle", "unknown")
            slug = re.sub(r"[^\w.-]+", "-", str(slug)).strip("-") or "unknown"
            shortcode = (data.get("shortcode") or data.get("postId")
                         or data.get("tweet", {}).get("id", "post"))
            out_dir = Path(args.download)
            download_media(media, out_dir if args.download != "-" else Path(f"downloads/{slug}-{shortcode}"))

    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
