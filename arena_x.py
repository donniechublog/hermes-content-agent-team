#!/usr/bin/env python3
"""arena_x.py — ảnh xếp hạng lấy từ tài khoản X của arena.ai (@arena), NGUỒN ĐẦU TIÊN
cho tin benchmark model (LOW-337).

Ông Chủ 21/09/2026: *"cứ lấy hình từ tài khoản twitter của arena.ai là chuẩn nhất, khi nói
tới benchmark, ko tìm được thì mới dùng bảng của bên khác"*. @arena đăng đồ hoạ xếp hạng
chính chủ cho từng model mới ("Gemini Omni 1.1 Flash has landed #1 in the Text-to-Video
Arena" kèm ảnh bảng) — đẹp và đúng hơn ảnh engine tự chụp trang bảng.

Đường đi (đo 21/09/2026 trên máy chủ):
  - Timeline công khai của X (`syndication.twitter.com/srv/timeline-profile`) trả 429 từ
    mọi máy, không dùng được. Không đăng nhập X hộ ai.
  - Đọc MỘT tweet theo ID (`cdn.syndication.twimg.com/tweet-result`) thì chạy: có chữ,
    ngày, tác giả, ảnh gốc `pbs.twimg.com`.
  - ID tweet lấy từ hai chỗ: tìm DuckDuckGo `site:x.com/arena "<model>"` (Bing không trả
    link status), và kho tweet của crawler social-publishing (`scan_x.read_tweets`) — kho
    này chỉ bắt @arena khi lọt vào feed, và crawler đã dừng từ 13/09/2026.

Khớp CHẶT tên model: tìm "Qwen-Image-2.1" ra toàn tweet Qwen-Image-2.0 / Qwen 3 cũ, nên
chỉ nhận tweet chứa đúng tên (kể cả số phiên bản), đăng trong `MAX_AGE_DAYS` ngày, có ảnh.
Không ra gì -> [] và `ranking` đi chụp các trang bảng như trước.
"""
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402

HANDLES = ("arena", "lmarena_ai")          # lmarena_ai: tên cũ của cùng tài khoản
MAX_AGE_DAYS = 45
MAX_IMAGES = 2
MAX_TWEETS_CHECKED = 12
SEARCH_URL = "https://html.duckduckgo.com/html/"
TWEET_URL = "https://cdn.syndication.twimg.com/tweet-result"
KIND = "x_post"                             # ranking.kind cho ảnh lấy từ tweet
SITE = "Arena (X @arena)"
_STATUS = re.compile(r"(?:x|twitter)\.com(?:/|%2F)(" + "|".join(HANDLES) + r")(?:/|%2F)status(?:/|%2F)(\d{15,20})",
                     re.I)


def _norm(t: str) -> str:
    """'Qwen-Image-2.1' / 'qwen image 2.1' -> 'qwen image 2.1' (so khớp không lệ thuộc gạch nối)."""
    return re.sub(r"[\s\-_]+", " ", (t or "").lower()).strip()


def model_keys(models: list) -> list:
    """Các tên được phép khớp, DÀI trước. Tên đầy đủ có số phiên bản thì tên ngắn cũng phải
    còn số — 'Qwen-Image' không được khớp thay 'Qwen-Image-2.1' (sai model)."""
    ra = [_norm(re.sub(r"\(.*?\)", " ", m)) for m in models or [] if m]
    # Ten day du co so phien ban: ten ngan cung phai con so. Khong co so: CHI ten day du —
    # "gemini omni" rut gon tu "Gemini Omni Flash" khop nham "Gemini Omni 1.1 Flash".
    ra = [k for k in ra if re.search(r"\d", k)] if ra and re.search(r"\d", ra[0]) else ra[:1]
    return [k for k in dict.fromkeys(ra) if len(k) >= 4]


def tweet_matches(text: str, models: list) -> str:
    """Tên model (đã chuẩn hoá) mà ĐOẠN ĐẦU của tweet nhắc ĐÚNG, hoặc ''. Biên từ hai phía để
    'qwen image 2.1' không khớp 'qwen image 2.15'. Chỉ đoạn đầu (tiêu đề): tweet "Gemini Omni
    1.1 Flash has landed #1 …" có nhắc "Gemini Omni Flash" ở cuối để SO SÁNH — bảng khoanh bản
    1.1, không phải bản cũ (đo 21/09/2026)."""
    dau = re.split(r"\n\s*\n", (text or "").strip(), maxsplit=1)[0]
    vb = _norm(re.sub(r"https?://\S+", " ", dau))
    for k in model_keys(models):
        if re.search(r"(?<![a-z0-9.])" + re.escape(k) + r"(?![a-z0-9]|\.\d| \d)", vb):
            return k
    return ""


def _ua():
    return {"User-Agent": env_load.UA_BROWSER, "Accept-Language": "en-US,en;q=0.9"}


def search_ids(models: list) -> list:
    """ID tweet của @arena nhắc model, từ DuckDuckGo. Hỏng mạng -> []."""
    import httpx
    ids = []
    for k in model_keys(models)[:2]:
        try:
            r = httpx.get(SEARCH_URL, params={"q": f'site:x.com/arena "{k}"'}, headers=_ua(),
                          timeout=20, follow_redirects=True)
        except Exception as e:                               # noqa: BLE001
            print(f"[arena_x] tim tweet hong: {type(e).__name__}", file=sys.stderr)
            continue
        ids += [m.group(2) for m in _STATUS.finditer(r.text)]
    return list(dict.fromkeys(ids))


def crawler_ids(models: list) -> list:
    """ID tweet của @arena có sẵn trong kho crawler social-publishing và nhắc model."""
    import scan_x
    try:
        goi = scan_x.read_tweets(24 * MAX_AGE_DAYS, 5000)
    except (SystemExit, Exception) as e:                     # noqa: BLE001 — read_tweets sys.exit khi thieu khoa
        print(f"[arena_x] kho tweet crawler khong doc duoc: {e}", file=sys.stderr)
        return []
    ra = []
    for t in goi.get("tweets", []):
        tay = ((t.get("author") or {}).get("handle") or "").lstrip("@").lower()
        m = _STATUS.search(t.get("url") or "")
        if tay in HANDLES and m and tweet_matches(t.get("text"), models):
            ra.append(m.group(2))
    return ra


def fetch_tweet(tweet_id: str) -> dict:
    """{id, handle, created, text, photos:[url]} của một tweet, hoặc {}."""
    import httpx
    try:
        r = httpx.get(TWEET_URL, params={"id": tweet_id, "token": "a"}, headers=_ua(), timeout=20)
        if r.status_code != 200:
            return {}
        d = r.json()
    except Exception:                                        # noqa: BLE001
        return {}
    return {"id": tweet_id, "handle": ((d.get("user") or {}).get("screen_name") or "").lower(),
            "created": d.get("created_at") or "", "text": d.get("text") or "",
            "photos": [m["media_url_https"] for m in d.get("mediaDetails") or []
                       if m.get("type") == "photo" and m.get("media_url_https")]}


def usable(tw: dict, models: list, now=None) -> str:
    """Tên model khớp nếu tweet dùng được (đúng @arena, mới, có ảnh, nhắc đúng model), hoặc ''."""
    if not tw or tw.get("handle") not in HANDLES or not tw.get("photos"):
        return ""
    try:
        ngay = datetime.fromisoformat(tw["created"].replace("Z", "+00:00"))
    except ValueError:
        return ""
    if ((now or datetime.now(timezone.utc)) - ngay).days > MAX_AGE_DAYS:
        return ""
    return tweet_matches(tw.get("text"), models)


def find_arena_images(models: list, out_dir: Path, in_log=print) -> list:
    """Ảnh xếp hạng từ tweet @arena cho `models`, cùng dạng kết quả với
    `ranking.find_and_capture_many`. Không có -> []."""
    import httpx
    from PIL import Image
    import image_provenance
    import state_paths
    ids = list(dict.fromkeys(crawler_ids(models) + search_ids(models)))[:MAX_TWEETS_CHECKED]
    ra = []
    for tid in ids:
        tw = fetch_tweet(tid)
        khop = usable(tw, models)
        if not khop:
            continue
        url = f"https://x.com/{tw['handle']}/status/{tid}"
        for i, anh in enumerate(tw["photos"][:1]):
            out = Path(out_dir) / f"{state_paths.RANKING_IMAGE_PREFIX}arena_x_{tid}_{i}.png"
            try:
                out.parent.mkdir(parents=True, exist_ok=True)
                tam = out.with_suffix(".tmp")
                tam.write_bytes(httpx.get(anh.split("?")[0] + "?name=large", headers=_ua(), timeout=30,
                                          follow_redirects=True).content)
                Image.open(tam).convert("RGB").save(out, "PNG")
                tam.unlink(missing_ok=True)
            except Exception as e:                           # noqa: BLE001
                in_log(f"[arena_x] tai anh tweet {tid} hong: {type(e).__name__}")
                continue
            dong = (tw["text"].splitlines() or [""])[0][:90]
            image_provenance.stamp_file(out, "ranking_capture", model=khop, source="arena-x",
                                        site=SITE, board=dong, rank=None, url=url)
            in_log(f"[arena_x] {url}: khớp {khop!r} — {dong}")
            ra.append({"file_path": str(out), "kind": KIND, "source": "arena-x", "site": SITE,
                       "board": dong, "rank": None, "model": khop, "url": url, "row": dong,
                       "logo": None, "mentioned": True})
        if len(ra) >= MAX_IMAGES:
            break
        time.sleep(0.3)
    return ra
