#!/usr/bin/env python3
"""Ghep manifest tu danh gia cua Finn + du lieu san co — tat dinh, khong LLM.

Truoc day Finn phai go lai title / link / source_note / via / image_url cho
tung bai vao manifest, du scan_sources.py da tra ve day du. Tam bai la 40 gia
tri go tay, moi gia tri la mot co hoi go sai (nhat la URL dai).

Nay Finn chi nop phan THUC SU phai nghi:
    [{"link": "...", "category": "...", "score_technical": 24,
      "score_relevance": 18, "score_reason": "...", "summary_vi": "..."}]

Script tu doi chieu voi candidates.json de lay phan con lai, tu cong diem
tong (partial + technical + relevance), tu danh so thu tu theo diem giam dan.
"""
import argparse
import json
import sys as _sys
from datetime import datetime, timezone
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                             # noqa: E402
import bat_buoc                                             # noqa: E402

ROOT = env_load.ROOT
STATE = env_load.state_dir()      # state/<brand>/ — cung cho approve_service doc

# Nhan chuan la TIENG ANH (approve_service.NHAN_CHUAN) — SOUL/brief cua Finn ke
# ARXIV / MODEL / LAB / INFRA / TOOL / ENGINEERING / BUSINESS / RESEARCH /
# SECURITY. Bang cu chi co ban tieng Viet nen moi lan Finn nop deu bi bao
# "category khong hop le" (thay 04/09/2026 khi chay thu quet_nop). Nhan ca hai.
VALID_CATEGORIES = {"ARXIV", "MODEL", "LAB", "INFRA", "TOOL", "ENGINEERING", "BUSINESS",
                    "RESEARCH", "SECURITY", "OPEN SOURCE", "OPEN WEIGHTS", "BENCHMARK",
                    "M&A", "UPDATE",
                    "MO HINH", "MÔ HÌNH", "THU NGHIEM", "THỬ NGHIỆM",
                    "HA TANG", "HẠ TẦNG", "CONG CU", "CÔNG CỤ"}


# Brief cua Finn ghi "toi da 8 tin". Truoc 06/09/2026 chi co cau chu do, khong
# co cong chan: vai nop 12 muc thi ca 12 vao manifest. Muc BAT BUOC khong bi
# tran nay cat (luat Ong Chu: quet thay la phai dua).
TOI_DA_PICK = 8


def _norm(u: str) -> str:
    u = re.sub(r"^https?://(www\.)?", "", u or "").rstrip("/")
    return re.sub(r"[?#].*$", "", u).lower()


def _diem(gt, ten: str, hi: int, problems: list, tieu_de: str) -> tuple:
    """Doc mot thanh phan diem cua vai: (diem da cat ve dai 0..hi, da_sua?).

    Truoc 06/09/2026: `int(p.get(...))` no thang khi vai ghi "24 diem" hoac
    null, va diem ngoai dai chi ghi mot dong stderr roi VAN vao manifest —
    ma quet_nop nuot stderr khi rc=0 nen khong ai thay. Gio cat ve dai va ghi
    chu tren bao cao, khong bao im lang, khong bat vai sua them mot vong."""
    try:
        d = int(gt)
    except (TypeError, ValueError):
        problems.append(f"{ten} khong phai so: {gt!r} -> 0 (bai: {tieu_de[:40]})")
        return 0, True
    if d < 0 or d > hi:
        problems.append(f"{ten} phai 0-{hi}, nhan {d} -> cat ve dai (bai: {tieu_de[:40]})")
        return max(0, min(hi, d)), True
    return d, False


def main():
    ap = argparse.ArgumentParser(
        description="Ghep manifest tu danh gia cua Finn + candidates.json")
    ap.add_argument("--candidates", default="/tmp/candidates.json",
                    help="File do scan_sources.py sinh ra")
    ap.add_argument("--picks", required=True,
                    help="File JSON danh gia cua Finn (mang cac muc)")
    ap.add_argument("--out", required=True, help="Duong dan manifest ghi ra")
    ap.add_argument("--bao-cao", metavar="PATH",
                    help="Ghi luon ban bao cao danh so, de gui bang publish.py --file")
    ap.add_argument("--khong-xoa-bat-buoc", action="store_true",
                    help="Thu: kiem nhung KHONG xoa muc bat buoc da dua")
    a = ap.parse_args()

    cands = json.loads(Path(a.candidates).read_text(encoding="utf-8"))["candidates"]
    by_link = {_norm(c["link"]): c for c in cands}

    picks = json.loads(Path(a.picks).read_text(encoding="utf-8"))
    if isinstance(picks, dict):
        picks = picks.get("picks") or picks.get("items") or []

    items, problems = [], []
    da_chon = set()                    # k / link da lay: chan vai nop trung mot tin
    for p in picks:
        # Chon bang SO THU TU `k` trong brief (tu 05/09/2026): vai khong phai chep URL
        # "y het" nua — sai mot ky tu la "khong tim thay" (4/8 muc, 05/09). Van nhan
        # `link` cho tuong thich.
        k = p.get("k") or p.get("stt") or p.get("#")
        if k is not None:
            try:
                k = int(k)
            except (TypeError, ValueError):
                k = 0
            c = cands[k - 1] if 1 <= k <= len(cands) else None
            if not c:
                problems.append(f"k={p.get('k')} ngoai danh sach 1..{len(cands)}")
                continue
        else:
            c = by_link.get(_norm(p.get("link", "")))
            if not c:
                problems.append(f"khong tim thay trong candidates: {p.get('link')}")
                continue

        # Trung tin: vai nop hai muc cung tro ve mot bai (hay gap khi vua ghi `k`
        # vua ghi `link`). Lay muc dau, bo muc sau, noi ro tren bao cao.
        khoa = _norm(c["link"])
        if khoa in da_chon:
            problems.append(f"tin trung, bo muc sau: {c['title'][:50]}")
            continue
        da_chon.add(khoa)

        cat = (p.get("category") or "").strip()
        cat_xau = bool(cat) and cat.upper() not in VALID_CATEGORIES
        if cat_xau:
            problems.append(f"category khong hop le: {cat!r} -> TOOL (bai: {c['title'][:40]})")

        tech, sua_t = _diem(p.get("score_technical", 0), "score_technical", 30, problems, c["title"])
        rel, sua_r = _diem(p.get("score_relevance", 0), "score_relevance", 20, problems, c["title"])
        ghi_chu = p.get("score_reason", "")
        if sua_t or sua_r or cat_xau:
            ghi_chu = (ghi_chu + " | script sua: "
                       + ", ".join(x for x in (
                           "diem ky thuat cat ve dai" if sua_t else "",
                           "diem lien quan cat ve dai" if sua_r else "",
                           f"category {cat!r} khong hop le -> TOOL" if cat_xau else "") if x)).strip()

        items.append({
            # tu candidates.json — Finn khong phai go lai
            "title": c["title"],
            "link": c["link"],
            "source_note": f"{c['source']}, {c['points']} diem, "
                          f"{c['comments']} binh luan",
            "via": c["via"],
            "image_url": p.get("image_url") or c.get("image_url"),
            # tu danh gia cua Finn
            "category": "TOOL" if (cat_xau or not cat) else cat,
            "score_technical": tech,
            "score_relevance": rel,
            "score": c["score_partial"] + tech + rel,
            "score_reason": ghi_chu,
            "summary_vi": p.get("summary_vi", ""),
            # tinh san, de doi chieu ve sau
            "score_recency": c["score_recency"],
            "score_spread": c["score_spread"],
            "picked": False,
        })

    # Tran 8 tin: giu 8 muc diem cao nhat cua vai, bo phan du va noi ro muc nao
    # bi bo. Muc BAT BUOC them ben duoi khong tinh vao tran nay.
    if len(items) > TOI_DA_PICK:
        items.sort(key=lambda x: x["score"], reverse=True)
        bo = items[TOI_DA_PICK:]
        items = items[:TOI_DA_PICK]
        problems.append(f"vai nop {len(items) + len(bo)} tin, tran la {TOI_DA_PICK} — "
                        f"giu {TOI_DA_PICK} tin diem cao nhat, bo: "
                        + "; ".join(f"{b['title'][:40]} ({b['score']}d)" for b in bo))

    if problems:
        # In ca stdout LAN stderr: quet_nop chi in stdout khi rc=0 nen canh bao
        # o stderr truoc day khong ai thay (audit 06/09/2026).
        print("PHAT HIEN VAN DE:")
        for pr in problems:
            print("  - " + pr)
            print("  - " + pr, file=sys.stderr)
        if not items:
            sys.exit("Khong co muc nao hop le — khong ghi manifest.")

    # Muc BAT BUOC vai bo sot: script TU THEM (diem vai = 0, ghi chu ro tren bao cao)
    # thay vi tu choi roi bat vai sua toi da 2 vong (05/09/2026: 4/8 muc, Finn mo
    # 18 tool call roi block task). Luat Ong Chu van giu: quet thay la phai dua.
    da_co = {_norm(it["link"]) for it in items}
    for v in bat_buoc.kiem("scout", items):
        c = by_link.get(_norm(v.get("link", "")))
        if not c or _norm(c["link"]) in da_co:
            print(f"  [canh bao] muc BAT BUOC khong co trong candidates, khong tu them duoc: "
                  f"{str(v.get('ten', ''))[:60]}", file=sys.stderr)
            continue
        items.append({
            "title": c["title"], "link": c["link"],
            "source_note": f"{c['source']}, {c['points']} diem, {c['comments']} binh luan",
            "via": c["via"], "image_url": c.get("image_url"),
            "category": "TOOL", "score_technical": 0, "score_relevance": 0,
            "score": c["score_partial"],
            "score_reason": "BAT BUOC, vai bo sot — script tu them, chua cham",
            "summary_vi": "", "score_recency": c["score_recency"],
            "score_spread": c["score_spread"], "picked": False, "tu_them": True,
        })
        da_co.add(_norm(c["link"]))
        print(f"  [tu them] muc BAT BUOC vai bo sot: {c['title'][:60]}", file=sys.stderr)
    items.sort(key=lambda x: x["score"], reverse=True)
    for i, it in enumerate(items, 1):
        it["index"] = i

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Khoa goc giong het manifest cua Nova va Vera. Ba vai di tim tin phai ra
    # cung mot dinh dang, khong moi noi mot kieu.
    out.write_text(json.dumps(
        {"quet_luc": datetime.now(timezone.utc).isoformat(), "vai": "scout",
         "items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"da ghi {len(items)} muc -> {out}")
    if not a.khong_xoa_bat_buoc:
        print(f"da xac nhan {bat_buoc.xoa('scout', items)} muc bat buoc, "
              f"con lai {len(bat_buoc.doc('scout'))}")

    # Bao cao do SCRIPT viet, khong de Finn go lai so. Dung chung ham voi Nova
    # va Vera nen ba vai hien cung mot dinh dang.
    if a.bao_cao:
        import bao_cao_manifest
        Path(a.bao_cao).write_text(
            bao_cao_manifest.dung(items, "scout"), encoding="utf-8")
        print(f"  bao cao -> {a.bao_cao}", file=_sys.stderr)
    for it in items:
        print(f"  #{it['index']} [{it['score']:3d}] {it['title'][:60]}")


if __name__ == "__main__":
    main()
