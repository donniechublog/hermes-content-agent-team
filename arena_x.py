#!/usr/bin/env python3
"""arena_x.py — ảnh lấy từ tài khoản X của arena.ai (@arena), NGUỒN ĐẦU TIÊN cho MỌI tin
model release / benchmark, ở mọi designer (LOW-337).

Ông Chủ 21/09/2026: *"cứ lấy hình từ tài khoản twitter của arena.ai là chuẩn nhất, khi nói
tới benchmark, ko tìm được thì mới dùng bảng của bên khác"*. 22/09/2026, lần nhắc tiếp theo
(tweet Grok 4.7): *"miễn là tin về model release, cứ lấy từ arena.ai đầu tiên, ko có thì mới
qua nguồn khác"* — kể cả tweet poll/xu hướng chưa có điểm. @arena đăng đồ hoạ chính chủ
cho từng model mới — đẹp và đúng hơn ảnh engine tự chụp trang bảng.

Đường đi — CHỈ dùng hạ tầng sẵn có của đội, không tự mò (Ông Chủ 21/09 + 22/09/2026: *"skill
crawl X trong repo của chúng ta có rồi, tận dụng thôi"*). Nguồn tweet, theo thứ tự, dừng ở
nguồn đầu tiên có tweet khớp:
  1. Link tweet @arena có sẵn trong tư liệu của bài (link gốc, thân bài) — đọc thẳng post đó.
  2. Trang `x.com/arena` không đăng nhập (`get_source.x_page_posts`): ~6 tweet mới nhất kèm
     nguyên văn. Đây là đường chính từ 22/09/2026 — trước đó hai đường dưới gần như luôn rỗng
     (crawler chết từ 13/09, crawl-queue chỉ trả MỘT tweet đầu/ghim), `find_arena_images` trả
     [] im lặng và tweet Grok 4.7 không bao giờ được thấy.
  3. Kho tweet của crawler X (`scan_x.read_tweets`, GET /tweets).
  4. Skill `social-crawl` đọc trang `x.com/arena` qua crawl-queue (chậm, 10–40s).
  Ảnh: `url-mascot-frame/scripts/get_source.py` (`save_x_photo`) — post X trả `media[]` rỗng,
  script đó đọc `pbs.twimg.com/media/<id>` trong HTML và tải bản `name=orig`; KHÔNG rơi về
  thẻ og:image hay ảnh chụp tường đăng nhập.

Khớp CHẶT tên model: tìm "Qwen-Image-2.1" ra toàn tweet Qwen-Image-2.0 / Qwen 3 cũ, nên
chỉ nhận tweet chứa đúng tên (kể cả số phiên bản), đăng trong `MAX_AGE_DAYS` ngày, có ảnh.
Không ra gì -> [] và `ranking` đi chụp các trang bảng như trước.
"""
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

HANDLES = ("arena", "lmarena_ai")          # lmarena_ai: tên cũ của cùng tài khoản
MAX_AGE_DAYS = 45
MAX_IMAGES = 2
MAX_TWEETS_CHECKED = 12
ROOT = Path(__file__).resolve().parent
SOCIAL_FETCH = ROOT / "hermes/skills/social-crawl/scripts/social_fetch.py"
GET_SOURCE = ROOT / "hermes/skills/url-mascot-frame/scripts/get_source.py"
PROFILE_URL = "https://x.com/arena"
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


def _record(url: str, handle: str, created: str, text: str) -> dict:
    return {"url": url or "", "handle": (handle or "").lstrip("@").lower(), "created": created or "",
            "text": text or ""}


def _get_source():
    """Module `get_source.py` của skill url-mascot-frame (không phải package, nạp theo đường dẫn)."""
    if str(GET_SOURCE.parent) not in sys.path:
        sys.path.insert(0, str(GET_SOURCE.parent))
    import get_source
    return get_source


def created_from_id(tid: str) -> str:
    """Giờ đăng suy từ ID tweet (snowflake: 41 bit mili-giây từ mốc Twitter 1288834974657)."""
    ms = (int(tid) >> 22) + 1288834974657
    return datetime.fromtimestamp(ms / 1000, timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def page_tweets(url: str) -> list:
    """Tweet hiện trên một trang x.com không đăng nhập (hồ sơ hoặc một post) — qua
    `get_source.x_page_posts`. Hỏng -> []."""
    try:
        posts = _get_source().x_page_posts(url)
    except Exception as e:                                   # noqa: BLE001
        print(f"[arena_x] doc trang {url} hong: {type(e).__name__}", file=sys.stderr)
        return []
    return [_record(p["url"], p["handle"], created_from_id(p["id"]), p["text"]) for p in posts]


def status_urls(texts) -> list:
    """Link tweet @arena nằm sẵn trong tư liệu của bài (link gốc, thân bài), không trùng."""
    ra = []
    for t in texts or []:
        for m in _STATUS.finditer(t or ""):
            u = f"https://x.com/{m.group(1).lower()}/status/{m.group(2)}"
            if u not in ra:
                ra.append(u)
    return ra


def crawler_tweets() -> list:
    """Tweet @arena trong kho crawler X (GET /tweets). Không đọc được -> []."""
    import scan_x
    try:
        goi = scan_x.read_tweets(24 * MAX_AGE_DAYS, 5000)
    except (SystemExit, Exception) as e:                     # noqa: BLE001 — read_tweets sys.exit khi thieu khoa
        print(f"[arena_x] kho tweet crawler khong doc duoc: {e}", file=sys.stderr)
        return []
    ra = [_record(t.get("url"), (t.get("author") or {}).get("handle"), t.get("timestamp"), t.get("text"))
          for t in goi.get("tweets", [])]
    return [r for r in ra if r["handle"] in HANDLES]


def profile_tweets() -> list:
    """Tweet đầu trang x.com/arena + thread của nó, qua skill social-crawl. Hỏng -> []."""
    import json
    import subprocess
    try:
        out = subprocess.run([sys.executable, str(SOCIAL_FETCH), PROFILE_URL, "--tries", "3"],
                             capture_output=True, text=True, timeout=240).stdout
        d = json.loads(out[out.index("{"):])
    except Exception as e:                                   # noqa: BLE001
        print(f"[arena_x] social-crawl {PROFILE_URL} hong: {type(e).__name__}", file=sys.stderr)
        return []
    ra = []
    for t in [d.get("tweet") or {}] + list(d.get("thread") or []):
        ra.append(_record(t.get("url"), (t.get("author") or {}).get("handle") or "arena",
                          t.get("timestamp"), t.get("text")))
    return ra


def download_image(url: str, out: Path) -> bool:
    """Ảnh gốc của post X qua skill url-mascot-frame (`get_source.save_x_photo`). Chỉ ảnh
    người đăng tải lên: chạy script cả bộ thì post không ảnh rơi về thẻ og:image/ảnh chụp
    tường đăng nhập, và thẻ đó sẽ thành "ảnh xếp hạng" của bài."""
    try:
        return _get_source().save_x_photo(url, str(out))
    except Exception:                                        # noqa: BLE001
        return False


def usable(tw: dict, models: list, now=None) -> str:
    """Tên model khớp nếu tweet dùng được (đúng @arena, mới, nhắc đúng model), hoặc ''."""
    if not tw or tw.get("handle") not in HANDLES or not _STATUS.search(tw.get("url") or ""):
        return ""
    try:
        ngay = datetime.fromisoformat(tw["created"].replace("Z", "+00:00"))
    except ValueError:
        return ""
    if ((now or datetime.now(timezone.utc)) - ngay).days > MAX_AGE_DAYS:
        return ""
    return tweet_matches(tw.get("text"), models)


def tweet_sources(extra_urls=()) -> list:
    """(tên, hàm trả danh sách tweet) theo thứ tự thử — xem docstring đầu tệp."""
    ds = [(f"link {u}", lambda u=u: page_tweets(u)) for u in status_urls(extra_urls)]
    return ds + [("trang x.com/arena", lambda: page_tweets(PROFILE_URL)),
                 ("kho crawler X", crawler_tweets),
                 ("social-crawl x.com/arena", profile_tweets)]


def matching_tweets(models: list, extra_urls=(), in_log=print) -> list:
    """[(id, tweet)] @arena khớp `models`, MỚI NHẤT trước. Dừng ở nguồn đầu tiên có tweet
    khớp. Không nguồn nào đọc được gì thì báo TO — khác hẳn "đọc được mà không có tweet
    khớp": từ 13/09 tới 22/09/2026 đường này chết im lặng mà không ai biết."""
    candidates, seen, read_ok = [], set(), []
    for name, fetch in tweet_sources(extra_urls):
        tweets = fetch()
        if tweets:
            read_ok.append(f"{name} ({len(tweets)})")
        for tw in tweets:
            m = _STATUS.search(tw["url"])
            if m and m.group(2) not in seen and usable(tw, models):
                seen.add(m.group(2))
                candidates.append((m.group(2), tw))
        if candidates:
            break
    if not read_ok:
        in_log("[arena_x] ⚠️ KHÔNG ĐỌC ĐƯỢC nguồn tweet @arena nào (trang x.com/arena, kho "
               "crawler, social-crawl đều rỗng) — ảnh @arena bị bỏ qua vì HỎNG NGUỒN, không phải vì "
               "@arena chưa đăng")
    elif not candidates:
        in_log(f"[arena_x] đã đọc {', '.join(read_ok)}: không tweet nào nhắc đúng {models[:2]}")
    return sorted(candidates, key=lambda x: -int(x[0]))


def find_arena_images(models: list, out_dir: Path, in_log=print, extra_urls=()) -> list:
    """Ảnh từ tweet @arena cho `models`, cùng dạng kết quả với
    `ranking.find_and_capture_many`. `extra_urls`: link gốc/thân bài — link tweet @arena
    trong đó được đọc TRƯỚC. Không có -> []."""
    from PIL import Image
    import image_provenance
    import state_paths
    ungvien = matching_tweets(models, extra_urls, in_log)
    ra = []
    for tid, tw in ungvien[:MAX_TWEETS_CHECKED]:
        khop = usable(tw, models)
        url = f"https://x.com/{tw['handle']}/status/{tid}"
        out = Path(out_dir) / f"{state_paths.RANKING_IMAGE_PREFIX}arena_x_{tid}.png"
        out.parent.mkdir(parents=True, exist_ok=True)
        tam = out.with_suffix(".src")
        if not download_image(url, tam):
            in_log(f"[arena_x] {url}: khong lay duoc anh")
            continue
        try:
            Image.open(tam).convert("RGB").save(out, "PNG")
        except Exception as e:                               # noqa: BLE001
            in_log(f"[arena_x] anh tweet {tid} hong: {type(e).__name__}")
            continue
        finally:
            tam.unlink(missing_ok=True)
        dong = (tw["text"].splitlines() or [""])[0][:90]
        image_provenance.stamp_file(out, "ranking_capture", model=khop, source="arena-x",
                                    site=SITE, board=dong, rank=None, url=url)
        in_log(f"[arena_x] {url}: khớp {khop!r} — {dong}")
        ra.append({"file_path": str(out), "kind": KIND, "source": "arena-x", "site": SITE,
                   "board": dong, "rank": None, "model": khop, "url": url, "row": dong,
                   "logo": None, "mentioned": True})
        if len(ra) >= MAX_IMAGES:
            break
    return ra
