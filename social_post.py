#!/usr/bin/env python3
"""social_post.py — MOT cua duy nhat doc post X/Instagram/Facebook.

Vi sao tach ra: hai noi can cung mot thu va vi ly do khac nhau —
`duyet_lenh.py` (/bai) can CHU de lam brief, `anh_chuan_bi.py` can HINH cua
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


def la_social(url: str) -> bool:
    """URL nay co phai post mang xa hoi (crawl duoc toan van + anh) khong."""
    try:
        return urlsplit(url or "").netloc.lower().removeprefix("www.") in HOSTS
    except ValueError:
        return False


def tieu_de_tu_text(text: str, gioi_han: int = 100) -> str:
    """Cau dau tien lam tieu de: post khong co tieu de nhu bai bao, va dong dau
    thuong chinh la cau chot. Cat o ranh gioi tu, khong cat giua chu."""
    import re
    dong = next((d.strip() for d in (text or "").splitlines() if d.strip()), "")
    cau = re.split(r"(?<=[.!?…])\s", dong)[0].strip() or dong
    if len(cau) > gioi_han:
        cau = cau[:gioi_han].rsplit(" ", 1)[0] + "…"
    return cau


def doc(url: str, tai_ve: Path | None = None, tries: int = 3, cho: int = 300,
        in_log=lambda t: None) -> dict | None:
    """Doc mot post. Tra ve dict da don:

        {"title", "text", "author", "link", "media": [{"type", "url", "tep"}]}

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
        media.append({"type": m.get("type") or "image", "url": m["url"], "tep": tep})

    in_log(f"social_fetch OK: {len(text)}c, {len(media)} media, tac gia {tac_gia!r}")
    return {"title": tieu_de_tu_text(text), "text": text, "author": tac_gia,
            "link": d.get("url") or tw.get("url") or url, "media": media}
