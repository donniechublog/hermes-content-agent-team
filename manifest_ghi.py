#!/usr/bin/env python3
"""Ghi manifest danh so cho Nova/Vera — tat dinh, khong LLM.

Vi sao can: Finn tu lau da ghi manifest danh so nen Ong Chu chi viec tra loi
"1" hoac "1,3" trong topic la ra bai. Nova va Vera thi bao cao van xuoi khong so,
nen Ong Chu doc xong khong biet rep gi. Ba vai deu la vai DI TIM TIN, phai chon
duoc bang cung mot cach.

Vai chi nop phan THUC SU phai nghi — tieu de, link, tom tat, ly do dang chu y.
Script tu dien phan co hoc: danh so theo thu tu, suy `via` tu ten mien, gan nhan
nguon, dong dau thoi gian.

Dung:
    venv/bin/python manifest_ghi.py --vai nova --in /tmp/nova.json
    (tep vao: [{"title":..., "link":..., "summary_vi":..., "score_reason":...,
                "category":..., "source_note":...}, ...])
"""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scan_sources import nguon_goc                          # noqa: E402

import env_load                                             # noqa: E402

ROOT = Path.home() / "content-team"
# STATE theo container (state/<CT_BRAND>/), CUNG mot ham voi approve_service.
# Truoc 03/09/2026 ghi cung ROOT/state nen manifest cua Vera/Nova nam o goc,
# approve_service (doc state/<brand>/) khong thay -> tra loi so luon ra
# "Chua co danh sach tin nao de chon". Cron chay trong gateway co san CT_BRAND.
STATE = env_load.state_dir()
TIEN_TO = {"nova": "nova_candidates", "market": "vera_candidates",
           "vera": "vera_candidates"}


def main():
    ap = argparse.ArgumentParser(description="Ghi manifest danh so cho Nova/Vera")
    ap.add_argument("--vai", required=True, choices=sorted(TIEN_TO))
    ap.add_argument("--in", dest="infile", required=True,
                    help="Tep JSON danh sach tin (title, link, summary_vi, ...)")
    ap.add_argument("--hau-to", default="", help="Them hau to vao ten tep")
    ap.add_argument("--bao-cao", metavar="PATH",
                    help="Ghi luon ban BAO CAO danh so ra tep nay, de gui thang "
                         "len Telegram bang publish.py --file")
    a = ap.parse_args()

    ds = json.loads(Path(a.infile).read_text(encoding="utf-8"))
    if isinstance(ds, dict):
        ds = ds.get("items") or ds.get("candidates") or []
    if not ds:
        sys.exit("Danh sach rong — khong ghi manifest.")

    items = []
    for i, it in enumerate(ds, 1):
        link = (it.get("link") or "").strip()
        if not it.get("title") or not link:
            print(f"[bo qua] muc {i} thieu title hoac link", file=sys.stderr)
            continue
        # Link phai la URL THAT. Cong chan cu chi doi khac rong, nen mot chuoi
        # nhu "blank" lot qua het: manifest ghi xong nhin binh thuong, Ong Chu
        # chon tin, roi vai dung anh moi phat hien khong co gi de tai va dung
        # lai. Ngay 24/08 ca nam tin cua Vera deu la "blank", ba cap task chet
        # cung mot kieu. Chan ngay tu day thi tin hong khong bao gio vao den
        # danh sach chon.
        if not link.lower().startswith(("http://", "https://")):
            print(f"[bo qua] muc {i} link khong phai URL: {link!r}",
                  file=sys.stderr)
            continue
        items.append({
            "index": i,
            "title": it["title"],
            "link": link,
            # via = NGUON TIN, suy tu ten mien. Khong phai kenh phat hien.
            "via": it.get("via") or nguon_goc(link) or "",
            "source_note": it.get("source_note") or "",
            "summary_vi": it.get("summary_vi") or "",
            "score": it.get("score"),
            "score_reason": it.get("score_reason") or "",
            "category": it.get("category") or ("MÔ HÌNH" if a.vai == "nova" else "KINH DOANH"),
            "image_url": it.get("image_url"),
            "picked": False,
        })

    ngay = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    ten = f"{TIEN_TO[a.vai]}_{ngay}{('_' + a.hau_to) if a.hau_to else ''}.json"
    out = STATE / ten
    # KHONG ghi de manifest da co. Ghi de la mat het cờ picked, va TE HON la
    # doi nghia so thu tu: muc "2" cua ban sang khac muc "2" cua ban toi, Ong
    # Chu tra loi theo tin nhan cu se ra bai khac. Quet lai trong ngay thi tu
    # dong deo hau to gio — latest_manifest chon theo mtime nen ban moi thang.
    if out.exists():
        out = STATE / (f"{TIEN_TO[a.vai]}_{ngay}"
                       f"_t{datetime.now(timezone.utc).strftime('%H%M')}.json")
    out.write_text(json.dumps(
        {"quet_luc": datetime.now(timezone.utc).isoformat(), "vai": a.vai,
         "items": items}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(out)
    for it in items:
        print(f"  {it['index']}. [{it['via']}] {it['title'][:66]}", file=sys.stderr)

    # Bao cao do CHINH SCRIPT dung, khong de agent go lai so. Go lai la co hoi
    # lech: so trong tin nhan mot dang, so trong manifest mot dang, Ong Chu tra
    # loi so lai ra bai khac. Sinh o day thi hai ben khong the lech.
    if a.bao_cao:
        import bao_cao_manifest
        Path(a.bao_cao).write_text(
            bao_cao_manifest.dung(items, a.vai, ngay), encoding="utf-8")
        print(f"  bao cao -> {a.bao_cao}", file=sys.stderr)


if __name__ == "__main__":
    main()
