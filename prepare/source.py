#!/usr/bin/env python3
"""PHA NGUON: nap tu lieu bai goc, ung vien anh tinh/social, ten rieng, Commons.

Tach tu image_prepare.py 09/09/2026 (audit A1, di chuyen thuan — than ham giu y nguyen).
"""
import re
import sys
from pathlib import Path

import schema

from prepare.common import DRAFTS, GNEWS, _read_json, _write_json


def _summary_from_img_json(draft_id: str) -> dict:
    """Tom tat + source_note nam trong body task (img.json). Doc lai tu do thay
    vi bat vai chep — mot nguon, khong lech."""
    d = _read_json(DRAFTS / f"{draft_id}.img.json", {}) or {}
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
def load_source(draft_id: str, meta: dict, state: Path, phien=None) -> tuple:
    """Tra ve (nguon_dict, nguon_path, link_real). Giai ma link Google News neu
    can va ghi nguoc vao nguon json + meta de moi vai sau cung dung link that."""
    import article_sources
    p = state / f"nguon_{draft_id}.json"
    link = meta.get("source_url", "")
    nguon = _read_json(p) or {"tieu_de": meta.get("title", ""), "link_goc": link,
                             "trang": [{"url": link, "loai": "gốc",
                                        "tieu_de": meta.get("title", "")}]}
    link_goc = nguon.get("link_goc") or link
    if GNEWS in link_goc:
        that = article_sources.resolve_code_gnews(link_goc, phien=phien)
        if that:
            print(f"[nguon] giai ma Google News -> {that[:90]}", file=sys.stderr)
            nguon["link_gnews"] = link_goc
            nguon["link_goc"] = that
            for t in nguon.get("trang", []):
                if t.get("url") == link_goc:
                    t["url"] = that
            _write_json(p, nguon)
            link_goc = that
            if meta.get("source_url") != that:
                meta["source_url"] = that
                # TRON vao ban TREN DIA hien tai, khong ghi de nguyen `meta` (co
                # the da cu di so voi luc goi ham nay — pipeline chay lau, va
                # `.meta.json` la tep BA TIEN TRINH cung ghi khong khoa chung:
                # approve_service, engine nen, va blackboard cua hermes ghi
                # `root_task` rieng, xem docstring env_load.ghi_json). Ghi de ca
                # dict y het loi merge_meta da sua cho approve_pick.py —
                # ghi de mat `root_task` neu blackboard vua ghi xong trong luc
                # tien trinh nay con dang giai ma Google News.
                p_meta = DRAFTS / f"{draft_id}.meta.json"
                _write_json(p_meta, schema.merge_meta(
                    _read_json(p_meta, {}), {"source_url": that}))
    # Tieu de TIENG ANH cua bai that: tin cua Vera/Nova mang tieu de tieng Viet,
    # tim Google News/RSS bang tieu de do ra rong. Lay <title>/og:title cua trang
    # goc mot lan, ghi vao nguon json de article_images/material tim bao khac bang no.
    return nguon, p, link_goc


def _title_page(url: str) -> str:
    """og:title cua bai goc — mot ban duy nhat o article_sources (co luat: tieu de
    tieng Viet thi tra rong, khong duoc dem di tim kiem)."""
    import article_sources
    return article_sources._title_page(url)


def candidate_social(link: str, wd: Path) -> list:
    """Anh CUA CHINH post (X/Instagram/Facebook) lam ung vien hang dau.

    Vi sao khong de duong tim anh thuong lo: post mang xa hoi chan khach chua
    dang nhap, browser_pass mo facebook.com chi thay tuong dang nhap, con
    article_images.find di tim "bao khac" cho mot post ca nhan thi ra rac. Anh nguoi ta
    dang kem bai CHINH LA anh that cua tin do — Ong Chu chot 08/09/2026.

    Diem 95: cao hon moi nguon khac de no dung dau khi download_and_filter cat bot, nhung
    van de xep_hang (anh bang xep hang, khong di qua download_and_filter) dung tren.
    Tai han ve dia thay vi giu link CDN: link CDN co tham so het han (`oe=`).
    """
    import social_post
    if not social_post.is_social(link):
        return []
    d = social_post.read(link, tai_ve=wd / "social",
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


def candidate_static(title: str, link: str, nguon_path: Path, title_en: str = "") -> list:
    """article_images.find tren bo nguon cua Finn; it qua thi tim rong them (bao khac,
    bang tieu de tieng Anh cua bai that)."""
    import article_images
    ds = article_images.find(title, link, sau_rong=True, tu_nguon=str(nguon_path))
    if len(ds) < 4:
        them = article_images.find(title_en or title, link, sau_rong=True, tu_nguon=None)
        co = {c["anh"] for c in ds}
        ds += [c for c in them if c["anh"] not in co]
    return ds


def commons_images(tu_khoa: str, so: int = 4) -> list | None:
    """Anh that tren Wikimedia Commons (tru so, san pham, su kien) cho tin mong
    anh — IMAGE_RULES muc 1.2 ke Commons la nguon hop le. Chi goi khi bai + bao khac
    khong du 5 anh. Loai SVG/logo (mime + _graphic o buoc tai).

    Tra None khi HONG VI MOI TRUONG (mang, API loi) — KHAC voi [] (da chay het,
    khong ra anh nao). Nguoi goi phai tu phan biet hai truong hop nay (quy uoc
    "hong phai lo", audit_content_team C1)."""
    import scan_common
    pages = scan_common.ask_commons(tu_khoa, so=14, loai_logo=False)   # mot ban (ADF-r2-16)
    if pages is None:
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
# KHONG gop vao article_sources.FROM_EMPTY_QUERY vi set do con dung loc tu truy van
# bao khac, noi "foundry" la tu khoa TOT can giu lai.
FROM_COMMON_MARK_SENTENCE = {
    "foundry", "power", "choice", "chip", "chips", "deal", "deals", "report",
    "study", "data", "demand", "supply", "growth", "boom", "wave", "race",
    "war", "threat", "risk", "rise", "fall", "shift", "era", "future",
    "market", "markets", "jobs", "job", "apocalypse", "crisis", "battle",
    "fight", "surge", "slump", "crunch", "squeeze", "gap", "divide", "bet",
    "bets", "bubble", "boost", "cut", "cuts", "push", "plan", "plans",
}


def all_proper_nouns(tieu_de: str) -> list:
    """TAT CA cum ten rieng trong tieu de, theo thu tu xuat hien — khong dung
    lai o cum DAU TIEN nhu `_leading_proper_noun` (LOW-176, 16/09/2026: tin
    hai hang "Anthropic ra tich hop Salesforce" chi ra duoc "Anthropic" lam
    tu khoa, nen ca vong anh thuong hieu lan cau hoi vision deu khong bao gio
    biet toi Salesforce — ma anh dung chu de nhat cua tin lai la anh su kien
    cua CHINH Salesforce). Dung CHUNG mot bo loc voi ham do (STOPWORD
    FROM_EMPTY_QUERY/FROM_COMMON_MARK_SENTENCE), chi khac la quet HET tieu de
    thay vi dung lai o tu dau tien khop."""
    import article_sources
    # Hau to site (" · Hugging Face") khong phai ten rieng cua tin (LOW-35):
    # no tung thanh tu khoa Commons va ra "Octopus' Hugging Face.jpg".
    t = article_sources.strip_site_suffix(re.sub(r"^\[[^\]]{1,20}\]\s*", "", tieu_de or ""))
    ws = re.sub(r"[\$;:,\"'()\[\]|]", " ", t).split()
    ra = []
    i = 0
    while i < len(ws):
        w = ws[i]
        if w[:1].isupper() and w.isalpha() and len(w) >= 4 and w.lower() not in article_sources.FROM_EMPTY_QUERY \
                and w.lower() not in FROM_COMMON_MARK_SENTENCE:
            cum = [w]
            j, da_qua_so = i + 1, False
            while j < len(ws) and len(cum) < 3:
                w2 = ws[j]
                if w2[:1].isupper() and w2.isalpha() and w2.lower() not in article_sources.FROM_EMPTY_QUERY \
                        and w2.lower() not in ("raises", "nabs", "drops", "launches", "unveils", "forecasts"):
                    cum.append(w2)
                    j += 1
                    da_qua_so = False
                elif not da_qua_so and re.fullmatch(r"[0-9][0-9a-zA-Z]*", w2):
                    # So/ma phien ban xen giua chinh ten san pham ("Snapdragon 8
                    # Elite", "GPT-4 Turbo") — bo qua token nay (khong dua vao
                    # ten hien thi) nhung KHONG cat cum, de tu hoa ke tiep van
                    # duoc gop chung MOT ten thay vi bi doc thanh mot "hang" rieng
                    # gia (LOW-176: "Snapdragon 8 Elite" tung ra hai muc "Qualcomm"
                    # va "Elite" — "Elite" la hang bia).
                    j += 1
                    da_qua_so = True
                else:
                    break
            cum_ten = " ".join(cum)
            if cum_ten not in ra:
                ra.append(cum_ten)
            i = j
        else:
            i += 1
    return ra


def _leading_proper_noun(tieu_de: str) -> str:
    """Cum ten rieng dau tieu de (hang/san pham) lam tu khoa Commons: lay CAC TU
    VIET HOA LIEN TIEP ("Gimlet Labs", "Thinking Machines"), khong chi mot tu —
    "Gimlet" mot minh ra cocktail (05/09/2026). Bo the "[News]" dau tieu de.

    MOT trong (co the nhieu) cum ten rieng cua tieu de — xem `all_proper_nouns`
    khi can CA cac cum con lai (LOW-176)."""
    ra = all_proper_nouns(tieu_de)
    return ra[0] if ra else ""
