#!/usr/bin/env python3
"""arena_x.py — ảnh xếp hạng lấy từ tài khoản X của arena.ai (@arena), NGUỒN ĐẦU TIÊN
cho tin benchmark model (LOW-337).

Ông Chủ 21/09/2026: *"cứ lấy hình từ tài khoản twitter của arena.ai là chuẩn nhất, khi nói
tới benchmark, ko tìm được thì mới dùng bảng của bên khác"*. @arena đăng đồ hoạ xếp hạng
chính chủ cho từng model mới ("Gemini Omni 1.1 Flash has landed #1 in the Text-to-Video
Arena" kèm ảnh bảng) — đẹp và đúng hơn ảnh engine tự chụp trang bảng.

Đường đi — CHỈ dùng hạ tầng sẵn có của đội, không tự mò (Ông Chủ 21/09/2026: *"skill crawl X
trong repo của chúng ta có rồi, tận dụng thôi"*):
  - Tweet của @arena: kho tweet của crawler X (`scan_x.read_tweets`, GET /tweets) và skill
    `social-crawl` đọc trang `x.com/arena` (tweet đầu/ghim + thread của nó) qua crawl-queue.
  - Ảnh: `url-mascot-frame/scripts/get_source.py` — post X trả `media[]` rỗng, script đó đọc
    `pbs.twimg.com/media/<id>` trong HTML và tải bản `name=orig`.
  Crawl-queue chỉ đọc MỘT post mỗi lần (trang hồ sơ/trang tìm kiếm đều trả một tweet), nên
  danh sách tweet mới dựa vào kho crawler X — kho đó dừng từ 13/09/2026 (xem báo cáo LOW-337).

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
    """Ảnh gốc của post X qua skill url-mascot-frame (`get_source.py`)."""
    import subprocess
    try:
        subprocess.run([sys.executable, str(GET_SOURCE), url, str(out)], capture_output=True,
                       text=True, timeout=240)
    except Exception:                                        # noqa: BLE001
        return False
    return out.exists() and out.stat().st_size > 0


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


def find_arena_images(models: list, out_dir: Path, in_log=print) -> list:
    """Ảnh xếp hạng từ tweet @arena cho `models`, cùng dạng kết quả với
    `ranking.find_and_capture_many`. Không có -> []."""
    from PIL import Image
    import image_provenance
    import state_paths
    ungvien, da = [], set()
    for tw in crawler_tweets() + profile_tweets():
        m = _STATUS.search(tw["url"])
        if m and m.group(2) not in da and usable(tw, models):
            da.add(m.group(2))
            ungvien.append((m.group(2), tw))
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
