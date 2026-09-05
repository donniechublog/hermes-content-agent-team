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
import html as _htmllib
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse, urljoin

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


def download(url: str, out: str, ua: str = UA) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if not data:
        sys.exit(f"tai ve 0 byte tu {url}")
    Path(out).write_bytes(data)
    return len(data)


def _is_image_file(path: str) -> bool:
    """Magic-byte check — the og:image download really is an image, not an HTML
    redirect stub (Facebook lookaside serves stubs to the wrong UA)."""
    try:
        with open(path, "rb") as f:
            h = f.read(16)
    except Exception:
        return False
    return (h[:3] == b"\xff\xd8\xff" or h[:8] == b"\x89PNG\r\n\x1a\n"
            or h[:6] in (b"GIF87a", b"GIF89a") or h[:2] == b"BM"
            or (h[:4] == b"RIFF" and h[8:12] == b"WEBP"))


# X stopped putting the post's photo in og:image — the card there is now a
# rendered summary at jf.x.com/images/post/<id>.png (author, truncated text and
# a cropped, faded thumbnail). The real upload is still in the page HTML, and
# the crawl endpoint returns an empty media[] for photo posts, so read the media
# id straight off the page and rebuild the CDN url at full resolution.
TWIMG_MEDIA_RE = re.compile(r"pbs\.twimg\.com/media/([A-Za-z0-9_-]{6,})")


def twimg_from_page(url: str) -> list:
    """Full-resolution CDN urls for the photos embedded in an x.com post page."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": BOT_UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            page = r.read().decode("utf-8", "ignore")
    except Exception:
        return []
    seen, out = set(), []
    for mid in TWIMG_MEDIA_RE.findall(page):
        if mid in seen:
            continue
        seen.add(mid)
        # Rebuilt from the id, not rewritten: the page also carries
        # `<id>.jpg:large` forms that twimg_orig() cannot parse.
        out.append(f"https://pbs.twimg.com/media/{mid}?format=jpg&name=orig")
    return out


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


SCREENSHOT_JS = Path(__file__).resolve().parent / "screenshot.js"


def screenshot(url: str, out: str) -> bool:
    """High-DPR (Retina) screenshot fallback for pages that are not a single
    image. Returns True if it produced a non-empty file."""
    if not SCREENSHOT_JS.exists():
        return False
    try:
        subprocess.run(["node", str(SCREENSHOT_JS), url, out],
                       capture_output=True, text=True, timeout=120)
    except Exception:
        return False
    p = Path(out)
    return p.exists() and p.stat().st_size > 0


def _og_image_url(page_html: str, base: str):
    """The post's OWN image, from the page's og:image / twitter:image meta —
    i.e. the picture a link-preview would show. Absolute-ised against `base`."""
    pats = [
        r'<meta[^>]+property=["\']og:image(?::url)?["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image(?::url)?["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
    ]
    for pat in pats:
        m = re.search(pat, page_html, re.I)
        if m:
            return urljoin(base, _htmllib.unescape(m.group(1).strip()))
    return None


# Facebook (and others) emit og: tags only to known crawlers — a browser UA
# gets a 400 / login wall. Fetch the HTML as a crawler to read the preview image.
BOT_UA = "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"


FB_HOSTS = ("facebook.com", "m.facebook.com", "mbasic.facebook.com",
            "web.facebook.com", "business.facebook.com", "fb.com", "fb.me",
            "fb.watch")

# Facebook wraps outbound links as l.facebook.com/l.php?u=<encoded real url>.
# Resolving the wrapper only ever yields FB's interstitial page, so unwrap it
# and resolve the real destination instead.
FB_LINK_HOSTS = ("l.facebook.com", "lm.facebook.com", "l.messenger.com")


def unwrap_fb_link(url: str) -> str:
    u = urlparse(url)
    if u.netloc.lower().removeprefix("www.") not in FB_LINK_HOSTS:
        return url
    return (parse_qs(u.query).get("u") or [""])[0] or url


def page_fallback(url: str, out: str, allow_screenshot: bool = True) -> bool:
    """A page, not a direct image: grab the post's OWN image (og:image) first —
    that is 'the image in the post', not the whole page. Screenshot only if the
    page has no such image AND a screenshot would be meaningful.

    `allow_screenshot=False` for login-gated hosts (Facebook): a logged-out
    screenshot there is only ever the login wall, so framing it is worse than
    failing. Returns True on success."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": BOT_UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            page = r.read().decode("utf-8", "ignore")
        img = _og_image_url(page, url)
        if img:
            # Crawler UA first: FB lookaside serves the real bytes only to a
            # crawler. Some og:image links (a placeholder media_id) hand back an
            # HTML stub to every UA, so retry once as a browser before giving up.
            for ua in (BOT_UA, UA):
                try:
                    download(twimg_orig(img), out, ua=ua)
                except Exception:
                    continue
                if _is_image_file(out):
                    return True
            # A non-image left at `out` is worse than no file at all: the caller
            # checks that the path exists and would frame an HTML page as art.
            Path(out).unlink(missing_ok=True)
    except Exception:
        pass
    return screenshot(url, out) if allow_screenshot else False


def main():
    if len(sys.argv) < 3:
        sys.exit("usage: get_source.py <url> <out-path>")
    url, out = sys.argv[1], sys.argv[2]
    url = unwrap_fb_link(url)
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
        if urls:
            download(urls[0], out)
            print(out)
            return
        # X photo post: no media[] from the crawler and og:image is only the
        # card, so take the upload out of the page before settling for that.
        if host in ("x.com", "twitter.com"):
            for cdn in twimg_from_page(url):
                try:
                    download(cdn, out)
                except Exception:
                    continue
                if _is_image_file(out):
                    print(out)
                    return
            Path(out).unlink(missing_ok=True)
        # text tweet / no media → the post's og:image, else a screenshot
        if page_fallback(url, out):
            print(out)
            return
        sys.exit(3)

    # 2b) Facebook — login-gated. og:image (crawler UA) resolves public Page
    #     posts; NEVER screenshot (a logged-out FB screenshot is only the login
    #     wall). Gated/personal posts can't be scraped — send the image into the
    #     topic instead and Bob frames it directly.
    if host in FB_HOSTS:
        if page_fallback(url, out, allow_screenshot=False):
            print(out)
            return
        print("facebook: bai nay khong tra og:image cong khai (login wall hoac "
              "bai gioi han nguoi xem). Gui thang anh vao topic de frame.",
              file=sys.stderr)
        sys.exit(3)

    # 3) any other url — keep it if the server returns image/* (handles
    #    extensionless CDN links); otherwise it's a page.
    data = None
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=60) as r:
            if (r.headers.get("Content-Type") or "").lower().startswith("image/"):
                data = r.read()
    except Exception:
        data = None
    if data:
        Path(out).write_bytes(data)
        print(out)
        return
    # 4) a page → its OWN image (og:image), then a high-DPR screenshot
    if page_fallback(url, out):
        print(out)
        return
    sys.exit(3)


if __name__ == "__main__":
    main()
