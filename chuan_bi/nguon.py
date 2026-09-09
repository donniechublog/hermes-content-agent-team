#!/usr/bin/env python3
"""PHA NGUON: nap tu lieu bai goc, ung vien anh tinh/social, ten rieng, Commons.

Tach tu anh_chuan_bi.py 09/09/2026 (audit A1, di chuyen thuan — than ham giu y nguyen).
"""
import re
import sys
from pathlib import Path

import httpx

import env_load

from chuan_bi.chung import DRAFTS, GNEWS, _doc_json, _ghi_json


def _tom_tat_tu_img_json(draft_id: str) -> dict:
    """Tom tat + source_note nam trong body task (img.json). Doc lai tu do thay
    vi bat vai chep — mot nguon, khong lech."""
    d = _doc_json(DRAFTS / f"{draft_id}.img.json", {}) or {}
    body = d.get("body", "")
    ra = {}
    for khoa, nhan in (("summary", "Tom tat"), ("source_note", "Nguon")):
        if d.get(khoa):                         # approve_service ghi thang khoa nay
            ra[khoa] = str(d[khoa]).strip()
            continue
        m = re.search(rf"^{nhan}: (.*)$", body, re.M)   # sidecar cu: boc tu body
        ra[khoa] = (m.group(1).strip() if m else "")
    ra["remakes"] = int(d.get("remakes", 0) or 0)
    ra["vai_anh"] = d.get("vai_anh", "")
    return ra


# ---- 1. nguon ---------------------------------------------------------------
def nap_nguon(draft_id: str, meta: dict, state: Path, phien=None) -> tuple:
    """Tra ve (nguon_dict, nguon_path, link_that). Giai ma link Google News neu
    can va ghi nguoc vao nguon json + meta de moi vai sau cung dung link that."""
    import nguon_bai
    p = state / f"nguon_{draft_id}.json"
    link = meta.get("source_url", "")
    nguon = _doc_json(p) or {"tieu_de": meta.get("title", ""), "link_goc": link,
                             "trang": [{"url": link, "loai": "gốc",
                                        "tieu_de": meta.get("title", "")}]}
    link_goc = nguon.get("link_goc") or link
    if GNEWS in link_goc:
        that = nguon_bai.giai_ma_gnews(link_goc, phien=phien)
        if that:
            print(f"[nguon] giai ma Google News -> {that[:90]}", file=sys.stderr)
            nguon["link_gnews"] = link_goc
            nguon["link_goc"] = that
            for t in nguon.get("trang", []):
                if t.get("url") == link_goc:
                    t["url"] = that
            _ghi_json(p, nguon)
            link_goc = that
            if meta.get("source_url") != that:
                meta["source_url"] = that
                _ghi_json(DRAFTS / f"{draft_id}.meta.json", meta)
    # Tieu de TIENG ANH cua bai that: tin cua Vera/Nova mang tieu de tieng Viet,
    # tim Google News/RSS bang tieu de do ra rong. Lay <title>/og:title cua trang
    # goc mot lan, ghi vao nguon json de anh_bai/tu_lieu tim bao khac bang no.
    return nguon, p, link_goc


def _tieu_de_trang(url: str) -> str:
    """og:title cua bai goc — mot ban duy nhat o nguon_bai (co luat: tieu de
    tieng Viet thi tra rong, khong duoc dem di tim kiem)."""
    import nguon_bai
    return nguon_bai._tieu_de_trang(url)


def ung_vien_social(link: str, wd: Path) -> list:
    """Anh CUA CHINH post (X/Instagram/Facebook) lam ung vien hang dau.

    Vi sao khong de duong tim anh thuong lo: post mang xa hoi chan khach chua
    dang nhap, browser_pass mo facebook.com chi thay tuong dang nhap, con
    anh_bai.tim di tim "bao khac" cho mot post ca nhan thi ra rac. Anh nguoi ta
    dang kem bai CHINH LA anh that cua tin do — Ong Chu chot 08/09/2026.

    Diem 95: cao hon moi nguon khac de no dung dau khi tai_va_loc cat bot, nhung
    van de xep_hang (anh bang xep hang, khong di qua tai_va_loc) dung tren.
    Tai han ve dia thay vi giu link CDN: link CDN co tham so het han (`oe=`).
    """
    import social_post
    if not social_post.la_social(link):
        return []
    d = social_post.doc(link, tai_ve=wd / "social",
                        in_log=lambda t: print(f"[social] {t}", file=sys.stderr))
    if not d:
        return []
    cands = []
    for i, m in enumerate(d["media"], 1):
        if m["type"] != "image" or not m["tep"]:
            continue
        cands.append({"anh": m["tep"], "tep": m["tep"],
                      "alt": f"ảnh {i} trong post của {d['author']}".strip(),
                      "tu": "social_post", "trang": d["link"], "diem": 95})
    print(f"[social] {len(cands)} anh that tu chinh post", file=sys.stderr)
    return cands


def ung_vien_tinh(title: str, link: str, nguon_path: Path, title_en: str = "") -> list:
    """anh_bai.tim tren bo nguon cua Finn; it qua thi tim rong them (bao khac,
    bang tieu de tieng Anh cua bai that)."""
    import anh_bai
    ds = anh_bai.tim(title, link, sau_rong=True, tu_nguon=str(nguon_path))
    if len(ds) < 4:
        them = anh_bai.tim(title_en or title, link, sau_rong=True, tu_nguon=None)
        co = {c["anh"] for c in ds}
        ds += [c for c in them if c["anh"] not in co]
    return ds


def anh_commons(tu_khoa: str, so: int = 4) -> list | None:
    """Anh that tren Wikimedia Commons (tru so, san pham, su kien) cho tin mong
    anh — LUAT_ANH muc 1.2 ke Commons la nguon hop le. Chi goi khi bai + bao khac
    khong du 5 anh. Loai SVG/logo (mime + _do_hoa o buoc tai).

    Tra None khi HONG VI MOI TRUONG (mang, API loi) — KHAC voi [] (da chay het,
    khong ra anh nao). Nguoi goi phai tu phan biet hai truong hop nay (quy uoc
    "hong phai lo", audit_content_team C1)."""
    try:
        r = httpx.get("https://commons.wikimedia.org/w/api.php", params={
            "action": "query", "generator": "search", "gsrsearch": f"{tu_khoa} filetype:bitmap",
            "gsrnamespace": 6, "gsrlimit": 14, "prop": "imageinfo",
            "iiprop": "url|size|mime", "iiurlwidth": 1800, "format": "json"},
            headers={"User-Agent": env_load.UA_WIKI}, timeout=20)
        pages = r.json().get("query", {}).get("pages", {})
    except Exception as e:                                   # noqa: BLE001
        print(f"[commons] hong: {type(e).__name__}: {e!r}", file=sys.stderr)
        return None
    ra = []
    for pg in pages.values():
        ii = (pg.get("imageinfo") or [{}])[0]
        w, h = ii.get("width", 0), ii.get("height", 0)
        if min(w, h) < 600 or ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        ten = (pg.get("title") or "").replace("File:", "")
        if tu_khoa.lower() not in ten.lower():       # tim mo cua Commons hay lac de
            continue
        ra.append({"anh": ii.get("thumburl") or ii.get("url"), "alt": "Commons: " + ten, "og": False,
                   "tu": "commons", "trang": "https://commons.wikimedia.org/wiki/File:" + ten.replace(" ", "_"),
                   "rong": w, "cao": h, "diem": 30})
    ra.sort(key=lambda c: -(c["rong"] * c["cao"]))
    return ra[:so]


# Tu tieng Anh CHUNG hay bi nham la ten rieng vi dung dau cau/sau dau hai cham
# (viet hoa theo chinh ta tieng Anh, khong phai vi la ten rieng) — "Foundry
# power balance flips: Samsung's choice..." -> "Foundry" mot minh ra Commons
# toan xuong duc kim loai Milwaukee/quan bar ten "Foundry Live", khong lien
# quan gi ban dan (Ong Chu 08/09/2026, cung loai loi voi "Gimlet" -> cocktail
# 05/09/2026 nhung khac nguyen nhan: do la tu hiem gap tu vung chung, day la tu
# thuong dung nhung ro ngau nhien dung dau cau/menh de). RIENG cho ham nay —
# KHONG gop vao nguon_bai.TU_RONG_TRUY_VAN vi set do con dung loc tu truy van
# bao khac, noi "foundry" la tu khoa TOT can giu lai.
TU_CHUNG_DAU_CAU = {
    "foundry", "power", "choice", "chip", "chips", "deal", "deals", "report",
    "study", "data", "demand", "supply", "growth", "boom", "wave", "race",
    "war", "threat", "risk", "rise", "fall", "shift", "era", "future",
    "market", "markets", "jobs", "job", "apocalypse", "crisis", "battle",
    "fight", "surge", "slump", "crunch", "squeeze", "gap", "divide", "bet",
    "bets", "bubble", "boost", "cut", "cuts", "push", "plan", "plans",
}


def _ten_rieng_dau(tieu_de: str) -> str:
    """Cum ten rieng dau tieu de (hang/san pham) lam tu khoa Commons: lay CAC TU
    VIET HOA LIEN TIEP ("Gimlet Labs", "Thinking Machines"), khong chi mot tu —
    "Gimlet" mot minh ra cocktail (05/09/2026). Bo the "[News]" dau tieu de."""
    import nguon_bai
    t = re.sub(r"^\[[^\]]{1,20}\]\s*", "", tieu_de or "")
    ws = re.sub(r"[\$;:,\"'()\[\]|]", " ", t).split()
    for i, w in enumerate(ws):
        if w[:1].isupper() and w.isalpha() and len(w) >= 4 and w.lower() not in nguon_bai.TU_RONG_TRUY_VAN \
                and w.lower() not in TU_CHUNG_DAU_CAU:
            cum = [w]
            for w2 in ws[i + 1:i + 3]:
                if w2[:1].isupper() and w2.isalpha() and w2.lower() not in nguon_bai.TU_RONG_TRUY_VAN \
                        and w2.lower() not in ("raises", "nabs", "drops", "launches", "unveils", "forecasts"):
                    cum.append(w2)
                else:
                    break
            return " ".join(cum)
    return ""
