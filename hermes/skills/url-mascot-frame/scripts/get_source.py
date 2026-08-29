#!/usr/bin/env python3
"""Resolve a URL to its ORIGINAL full-res image and save it to disk.

Social platforms serve compressed/resized variants; downloading the *displayed*
image gives a soft copy that no upscaler can truly fix. The fix is to grab the
CDN original, deterministically:

  - pbs.twimg.com media url      -> rewrite to name=orig (full upload resolution)
  - x.com / twitter.com POST url -> social-crawl -> media[] CDN link (-> name=orig)
  - instagram.com POST url       -> social-crawl -> media[] CDN link
  - any other direct image url   -> download as-is

On success: writes the file and prints its path. Exits 3 when there is no single
downloadable image (a text-only tweet, an article, a generic page) so the caller
can fall back to a screenshot. This keeps the "always fetch the original" rule in
CODE, not in the agent's judgement.

Usage:  python3 get_source.py "<url>" <out-path>
"""
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/120.0 Safari/537.36")
SOCIAL_FETCH = Path.home() / ".claude" / "skills" / "social-crawl" / "scripts" / "social_fetch.py"


def twimg_orig(url: str) -> str:
    """Rewrite a pbs.twimg.com media URL to the original upload resolution."""
    u = urlparse(url)
    if "pbs.twimg.com" not in u.netloc:
        return url
    q = parse_qs(u.query)
    fmt = (q.get("format") or ["jpg"])[0]
    path = u.path
    m = re.match(r"(/media/[A-Za-z0-9_-]+)(\.\w+)?$", path)
    if m:
        path = m.group(1)
        if m.group(2):
            fmt = m.group(2).lstrip(".")
    return urlunparse(u._replace(path=path, query=urlencode({"format": fmt, "name": "orig"})))


def download(url: str, out: str) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if not data:
        sys.exit(f"tai ve 0 byte tu {url}")
    Path(out).write_bytes(data)
    return len(data)


def social_media_urls(url: str) -> list:
    """Ask social-crawl for the post's media[] CDN links (may be empty for X)."""
    if not SOCIAL_FETCH.exists():
        return []
    try:
        r = subprocess.run([sys.executable, str(SOCIAL_FETCH), url],
                           capture_output=True, text=True, timeout=200)
        j = json.loads(r.stdout)
    except Exception:
        return []
    return [m.get("url") for m in (j.get("media") or []) if m.get("url")]


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: get_source.py <url> <out-path>")
    url, out = sys.argv[1], sys.argv[2]
    host = urlparse(url).netloc.lower().removeprefix("www.")

    # 1) direct twitter image → original resolution
    if "pbs.twimg.com" in host:
        n = download(twimg_orig(url), out)
        print(out, file=sys.stderr)
        print(out)
        return

    # 2) X / Instagram post → original media via social-crawl
    if host in ("x.com", "twitter.com", "instagram.com"):
        urls = [twimg_orig(u) for u in social_media_urls(url)]
        if not urls:
            sys.exit(3)  # no single image (text tweet / carousel miss) → screenshot
        download(urls[0], out)
        print(out)
        return

    # 3) anything else — keep it ONLY if the server says it's an image. This
    #    handles extensionless CDN image urls, and lets real pages fall through
    #    to a screenshot (exit 3) without guessing from the extension.
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            ctype = (r.headers.get("Content-Type") or "").lower()
            if not ctype.startswith("image/"):
                sys.exit(3)          # a page, not a single image → screenshot
            data = r.read()
    except SystemExit:
        raise
    except Exception:
        sys.exit(3)
    if not data:
        sys.exit(3)
    Path(out).write_bytes(data)
    print(out)


if __name__ == "__main__":
    main()
