#!/usr/bin/env python3
"""social_post.py — MOT cua duy nhat doc post X/Instagram/Facebook.

Vi sao tach ra: hai noi can cung mot thu va vi ly do khac nhau —
`approve_command.py` (/bai) can CHU de lam brief, `image_prepare.py` can HINH cua
chinh post do lam anh that cho slide. Viet hai ban thi mot ban sua, ban kia
lech; dac biet la luat chuan hoa URL Facebook (xem SKILL.md cua social-crawl)
von da dat gia moi tim ra.

Ban than viec crawl van do skill `social-crawl` lam (script stdlib thuan, goi
curl); tep nay chi goi no bang tien trinh con va don ket qua ve mot dang.
"""
import json
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT / "hermes" / "skills" / "social-crawl" / "scripts" / "social_fetch.py"

HOSTS = {"x.com", "twitter.com", "mobile.twitter.com", "instagram.com",
         "facebook.com", "m.facebook.com", "web.facebook.com",
         "mbasic.facebook.com", "fb.com", "fb.watch"}


def is_social(url: str) -> bool:
    """URL nay co phai post mang xa hoi (crawl duoc toan van + anh) khong."""
    try:
        return urlsplit(url or "").netloc.lower().removeprefix("www.") in HOSTS
    except ValueError:
        return False


def title_from_text(text: str, gioi_han: int = 100) -> str:
    """Cau dau tien lam tieu de: post khong co tieu de nhu bai bao, va dong dau
    thuong chinh la cau chot. Cat o ranh gioi tu, khong cat giua chu."""
    import re
    dong = next((d.strip() for d in (text or "").splitlines() if d.strip()), "")
    cau = re.split(r"(?<=[.!?…])\s", dong)[0].strip() or dong
    if len(cau) > gioi_han:
        cau = cau[:gioi_han].rsplit(" ", 1)[0] + "…"
    return cau


GET_SOURCE = ROOT / "hermes" / "skills" / "url-mascot-frame" / "scripts" / "get_source.py"
X_HOSTS = {"x.com", "twitter.com", "mobile.twitter.com"}


def x_photos(url: str, out_dir: Path, in_log=lambda t: None) -> list:
    """Anh nguoi dang tai len cua MOT post X, qua skill url-mascot-frame
    (`get_source.save_x_photo`) — dang media giong `read()`. [] neu khong phai post X.

    Vi sao: crawl-queue tra `media[]` RONG cho post anh tren X (gioi han da biet, xem
    SKILL.md cua social-crawl), nen truoc 22/09/2026 moi post X lam nguon bai deu ra 0 anh
    that o `candidate_social`, du skill cua Bob da biet lay anh goc tu HTML trang post."""
    if urlsplit(url or "").netloc.lower().removeprefix("www.") not in X_HOSTS:
        return []
    if str(GET_SOURCE.parent) not in sys.path:
        sys.path.insert(0, str(GET_SOURCE.parent))
    try:
        import get_source
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        p = Path(out_dir) / "x_01.jpg"
        ok = get_source.save_x_photo(url, str(p))
    except Exception as e:                                   # noqa: BLE001
        in_log(f"get_source X hong ({type(e).__name__}) cho {url}")
        return []
    in_log(f"get_source X: {'1 anh goc' if ok else 'post khong co anh'} cho {url}")
    return [{"type": "image", "url": url, "file_path": str(p)}] if ok else []


def read(url: str, tai_ve: Path | None = None, tries: int = 3, cho: int = 300,
        in_log=lambda t: None) -> dict | None:
    """Doc mot post. Tra ve dict da don:

        {"title", "text", "author", "link", "media": [{"type", "url", "file_path"}]}

    `tai_ve`: thu muc de tai media that ve (dat ten 01.jpg, 02.jpg... theo thu
    tu carousel) — can khi muon DUNG anh, vi link CDN co tham so het han.
    Tra None khi khong lay duoc: goi la de goi y, khong phai de chan viec.
    """
    cmd = [sys.executable, str(SCRIPT), url, "--tries", str(tries)]
    if tai_ve is not None:
        cmd += ["--download", str(tai_ve)]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=cho)
    except (subprocess.TimeoutExpired, OSError) as e:            # noqa: BLE001
        in_log(f"social_fetch that bai ({type(e).__name__}) cho {url}")
        return None
    if r.returncode != 0:
        in_log(f"social_fetch rc={r.returncode}: {(r.stderr or '')[-200:].strip()}")
        return None
    try:
        d = json.loads(r.stdout)
    except ValueError:
        in_log("social_fetch tra ve khong phai JSON")
        return None

    tw = d.get("tweet") or {}
    text = (d.get("text") or tw.get("text") or "").strip()
    if not text and not (d.get("media") or tw.get("media")):
        in_log("social_fetch: JSON khong co chu lan anh")
        return None
    tac_gia = d.get("author") or tw.get("author") or ""
    if isinstance(tac_gia, dict):                 # X/Instagram tra object, Facebook tra chuoi
        tac_gia = tac_gia.get("name") or tac_gia.get("handle") or ""

    media = []
    for m in (d.get("media") or tw.get("media") or []):
        if not m.get("url"):
            continue
        stt = int(m.get("index") or len(media) + 1)
        tep = None
        if tai_ve is not None:
            duoi = "mp4" if m.get("type") == "video" else "jpg"
            p = Path(tai_ve) / f"{stt:02d}.{duoi}"
            # 0 byte = CDN 302 hut hoac link het han; coi nhu khong tai duoc.
            if p.exists() and p.stat().st_size > 0:
                tep = str(p)
        media.append({"type": m.get("type") or "image", "url": m["url"], "file_path": tep})
    if tai_ve is not None and not any(m["file_path"] and m["type"] == "image" for m in media):
        media += x_photos(d.get("url") or tw.get("url") or url, Path(tai_ve), in_log)

    in_log(f"social_fetch OK: {len(text)}c, {len(media)} media, tac gia {tac_gia!r}")
    return {"title": title_from_text(text), "text": text, "author": tac_gia,
            "link": d.get("url") or tw.get("url") or url, "media": media}
