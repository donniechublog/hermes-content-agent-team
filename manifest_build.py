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

ROOT = Path.home() / "content-team"
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


def _norm(u: str) -> str:
    u = re.sub(r"^https?://(www\.)?", "", u or "").rstrip("/")
    return re.sub(r"[?#].*$", "", u).lower()


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
    for p in picks:
        key = _norm(p.get("link", ""))
        c = by_link.get(key)
        if not c:
            problems.append(f"khong tim thay trong candidates: {p.get('link')}")
            continue

        cat = (p.get("category") or "").strip()
        if cat and cat.upper() not in VALID_CATEGORIES:
            problems.append(f"category khong hop le: {cat!r} (bai: {c['title'][:40]})")

        tech = int(p.get("score_technical", 0))
        rel = int(p.get("score_relevance", 0))
        if not 0 <= tech <= 30:
            problems.append(f"score_technical phai 0-30, nhan {tech}")
        if not 0 <= rel <= 20:
            problems.append(f"score_relevance phai 0-20, nhan {rel}")

        items.append({
            # tu candidates.json — Finn khong phai go lai
            "title": c["title"],
            "link": c["link"],
            "source_note": f"{c['source']}, {c['points']} diem, "
                          f"{c['comments']} binh luan",
            "via": c["via"],
            "image_url": p.get("image_url") or c.get("image_url"),
            # tu danh gia cua Finn
            "category": cat or "CONG CU",
            "score_technical": tech,
            "score_relevance": rel,
            "score": c["score_partial"] + tech + rel,
            "score_reason": p.get("score_reason", ""),
            "summary_vi": p.get("summary_vi", ""),
            # tinh san, de doi chieu ve sau
            "score_recency": c["score_recency"],
            "score_spread": c["score_spread"],
            "picked": False,
        })

    if problems:
        print("PHAT HIEN VAN DE:", file=sys.stderr)
        for pr in problems:
            print("  - " + pr, file=sys.stderr)
        if not items:
            sys.exit("Khong co muc nao hop le — khong ghi manifest.")

    thieu = bat_buoc.kiem("scout", items)
    if thieu:
        sys.exit(bat_buoc.loi_thieu("scout", thieu))
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
