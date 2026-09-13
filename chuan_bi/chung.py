#!/usr/bin/env python3
"""Nen dung chung cho moi pha: hang so, header HTTP, doc/ghi JSON, ten mien.

Tach tu image_prepare.py 09/09/2026 (audit A1, di chuyen thuan — than ham giu y nguyen).
"""
import json
import re
from pathlib import Path


import env_load


# BOC (09/09/2026): copy nguyen van tu anh_chuan_bi.py o GOC du an, nhung
# tep nay nam trong chuan_bi/ — mot cap .parent la khong du, DRAFTS thanh
# chuan_bi/drafts (rong) thay vi drafts/ that. kite_nop.py bao "Khong thay
# drafts/....meta.json" du tep do TON TAI, chi sai duong dan.
ROOT = Path(__file__).resolve().parent.parent


DRAFTS = ROOT / "drafts"


TOI_DA_ANH = 8              # anh giu lai sau khi loc — du cho 10 slide ke ca ghep


GNEWS = "news.google.com/rss/articles"


UA = "Mozilla/5.0 (compatible; donniechu-dre/1.0)"


HDR = {"User-Agent": UA, "Accept": "image/*,*/*;q=0.8"}


_WIKI = re.compile(r"(^|\.)wikimedia\.org$|(^|\.)wikipedia\.org$", re.I)


def _hdr(url: str) -> dict:
    """Header tai anh. Wikimedia doi UA rieng (env_load.UA_WIKI) — UA chung o day
    bi 403 ngay o buoc tai byte, ke ca khi API da tra ve link (do 09/09/2026)."""
    if _WIKI.search(_mien(url)):
        return {**HDR, "User-Agent": env_load.UA_WIKI}
    return HDR


# ---- tien ich -------------------------------------------------------------
def _brand_cua(meta: dict) -> str:
    return meta.get("brand") or "donniechublog"


def _mien(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url or "")
    return (m.group(1) if m else "").replace("www.", "")


def _doc_json(p: Path, mac_dinh=None):
    try:
        return json.loads(Path(p).read_text(encoding="utf-8"))
    except Exception:                                        # noqa: BLE001
        return mac_dinh


def _ghi_json(p: Path, d) -> None:
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    env_load.write_json(p, d)


def _goc_mien(h: str) -> str:
    """registrable domain tho: 2 nhan cuoi (thestar.com.my -> com.my? -> lay 3 neu TLD 2 chu)."""
    h = (h or "").lower().replace("www.", "")
    ps = h.split(".")
    if len(ps) >= 3 and len(ps[-1]) == 2 and len(ps[-2]) <= 3:
        return ".".join(ps[-3:])
    return ".".join(ps[-2:])
