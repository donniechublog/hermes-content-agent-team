#!/usr/bin/env python3
"""social_fetch.py — Fetch an X/Twitter post or Instagram post/reel/carousel via the
internal social-publishing crawl endpoint. No API key, no OAuth.

Endpoint is async + does warm-up prefetch: the first call after a URL hasn't been
crawled recently can return a false-negative error ("url must be an https x.com or
twitter.com URL", "Instagram media JSON not found for <shortcode>"). This script
polls with retries instead of failing on the first response.

Usage:
    python3 social_fetch.py "<x-or-instagram-url>"                 # print JSON to stdout
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


def detect_platform(url: str) -> str:
    host = urlparse(url).netloc.lower().removeprefix("www.")
    if host in {"x.com", "twitter.com", "mobile.twitter.com"}:
        return "x"
    if host in {"instagram.com"}:
        return "instagram"
    sys.exit(f"URL không thuộc x.com/twitter.com hay instagram.com: {url}")


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
    for m in media:
        idx = m.get("index", 1)
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
    data = crawl(args.url, args.tries)

    if args.download:
        media = data.get("tweet", {}).get("media") if platform == "x" else data.get("media")
        media = media or []
        if not media:
            print("Không có media[] để tải.", file=sys.stderr)
        else:
            slug = data.get("author", {}).get("handle") or data.get("tweet", {}).get("author", {}).get("handle", "unknown")
            shortcode = data.get("shortcode") or data.get("tweet", {}).get("id", "post")
            out_dir = Path(args.download)
            download_media(media, out_dir if args.download != "-" else Path(f"downloads/{slug}-{shortcode}"))

    print(json.dumps(data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
