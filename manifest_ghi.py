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
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from scan_sources import nguon_goc                          # noqa: E402

import env_load                                             # noqa: E402

ROOT = env_load.ROOT
# STATE theo container (state/<CT_BRAND>/), CUNG mot ham voi approve_service.
# Truoc 03/09/2026 ghi cung ROOT/state nen manifest cua Vera/Nova nam o goc,
# approve_service (doc state/<brand>/) khong thay -> tra loi so luon ra
# "Chua co danh sach tin nao de chon". Cron chay trong gateway co san CT_BRAND.
STATE = env_load.state_dir()
TIEN_TO = {"nova": "nova_candidates", "market": "vera_candidates",
           "vera": "vera_candidates", "qinn": "qinn_candidates"}

# Nhan mac dinh khi vai khong ghi `category`. Qinn quet X: phan lon la tool /
# ky thuat, nen TOOL (nhan hop le cua manifest_build) la mac dinh dung hon
# BUSINESS.
NHAN_MAC_DINH = {"nova": "MODEL", "qinn": "TOOL"}


import bat_buoc                                             # noqa: E402
import tieng_viet                                           # noqa: E402
import manifest_chung as mc                                 # noqa: E402
import quet_chung                                           # noqa: E402


def _so_bao(t: dict) -> str:
    # Tin X (Qinn): "1 báo" vô nghĩa — cái Ông Chủ cần thấy là TÁC GIẢ và tin
    # đến từ home hay từ list nào (list là tập tài khoản Ông Chủ tự chọn, nên
    # đáng tin hơn home; xem SOUL của Qinn).
    if t.get("nguon_x"):
        ai = t.get("toa_soan") or ""
        return f"{ai} · {t['nguon_x']}" if ai else str(t["nguon_x"])
    return f"{t.get('so_bao', 1)} báo: {', '.join(t.get('cac_bao', [])[:3]) or t.get('toa_soan', '')}"


def _muc_tu_nop(it: dict, i: int, nguon: list, vai: str, vai_bb: str) -> dict | None:
    """Mot muc vai nop -> mot muc manifest. None = bo qua (da in ly do ra stderr).

    Moi cong o day deu la mot lan da mat tin that, khong phai phong xa."""
    # Chon bang SO THU TU `k` trong brief (tu 05/09/2026): script tu lay link va
    # so bao tu quet.json, vai chi viet headline + summary. Van nhan `link`.
    t = None
    k = it.get("k") or it.get("stt") or it.get("#")
    if k is not None and nguon:
        t, loi = mc.chon_theo_k(k, nguon, f"muc {i}")
        if not t:
            print(f"[bo qua] {loi}", file=sys.stderr)
            return None
    link = ((it.get("link") or "").strip()) or (t["link"] if t else "")
    if not link and it.get("title"):
        # Nova: muc bat buoc da co link goi y (trang model / bang xep hang) —
        # vai chi can ghi dung ten model, khong phai di tim URL (05/09/2026).
        for v in bat_buoc.doc(vai_bb).values():
            if bat_buoc.khop(v, {"title": it["title"], "summary_vi": ""}):
                link = bat_buoc.link_goi_y(v)
                break
    if not it.get("title") and t:
        it["title"] = t.get("tieu_de", "")
    if not it.get("source_note") and t:
        it["source_note"] = _so_bao(t)
    if not it.get("title") or not link:
        print(f"[bo qua] muc {i} thieu title hoac link", file=sys.stderr)
        return None
    # Link phai la URL THAT. Cong chan cu chi doi khac rong, nen mot chuoi
    # nhu "blank" lot qua het: manifest ghi xong nhin binh thuong, Ong Chu
    # chon tin, roi vai dung anh moi phat hien khong co gi de tai va dung
    # lai. Ngay 24/08 ca nam tin cua Vera deu la "blank", ba cap task chet
    # cung mot kieu. Chan ngay tu day thi tin hong khong bao gio vao den
    # danh sach chon.
    if not link.lower().startswith(("http://", "https://")):
        print(f"[bo qua] muc {i} link khong phai URL: {link!r}", file=sys.stderr)
        return None
    # Headline la thu DUY NHAT Ong Chu doc tren topic, va brief hua "tieng
    # Viet co dau". Chi CANH BAO (khong bo tin) — tin van co gia tri.
    mat_dau = tieng_viet.tim_mat_dau(it["title"])
    if mat_dau:
        print(f"[canh bao] muc {i} title tieng Viet mat dau ({', '.join(mat_dau[:3])}): "
              f"{it['title'][:60]}", file=sys.stderr)
    tom, canh = mc.don_tom_tat(it.get("summary_vi"), f"muc {i}")
    for c in canh:
        print(f"[canh bao] {c}", file=sys.stderr)
    return {
        "title": it["title"],
        "link": link,
        # via = NGUON TIN, suy tu ten mien. Khong phai kenh phat hien.
        "via": it.get("via") or nguon_goc(link) or "",
        "source_note": it.get("source_note") or "",
        "summary_vi": tom,
        "score": it.get("score"),
        "score_reason": it.get("score_reason") or "",
        "category": it.get("category") or NHAN_MAC_DINH.get(vai, "BUSINESS"),
        "image_url": it.get("image_url"),
        "picked": False,
    }


def them_bat_buoc(items: list, nguon: list, vai: str, vai_bb: str) -> list:
    """Muc BAT BUOC vai bo sot: script TU THEM kem ghi chu ro tren bao cao, thay vi
    tu choi roi bat vai sua toi da 2 vong (05/09/2026). Luat Ong Chu van giu:
    quet thay la phai dua; bao cao ghi "vai bo sot" de Ong Chu biet ai sot."""
    for v in bat_buoc.kiem(vai_bb, items):
        link = bat_buoc.link_goi_y(v)
        if not link.lower().startswith(("http://", "https://")):
            print(f"[canh bao] muc BAT BUOC khong co link, khong tu them duoc: "
                  f"{str(v.get('ten', ''))[:60]}", file=sys.stderr)
            continue
        ten = str(v.get("ten", ""))
        title = ten.split(": ", 1)[1] if vai_bb == "vera" and ": " in ten else ten
        t = next((x for x in nguon
                  if bat_buoc.chuan_link(x.get("link", "")) == bat_buoc.chuan_link(link)), None)
        items.append({
            "title": title, "link": link, "via": nguon_goc(link) or "",
            "source_note": _so_bao(t) if t else (v.get("ghi_chu") or ""),
            "summary_vi": "", "score": None,
            "score_reason": "BAT BUOC, vai bo sot — script tu them",
            "category": "MODEL" if vai == "nova" else "BUSINESS",
            "image_url": None, "picked": False, "tu_them": True,
        })
        print(f"[tu them] muc BAT BUOC vai bo sot: {title[:60]}", file=sys.stderr)
    return items


def main():
    ap = argparse.ArgumentParser(description="Ghi manifest danh so cho Nova/Vera")
    ap.add_argument("--vai", required=True, choices=sorted(TIEN_TO))
    ap.add_argument("--in", dest="infile", required=True,
                    help="Tep JSON danh sach tin (title, link, summary_vi, ...)")
    ap.add_argument("--hau-to", default="", help="Them hau to vao ten tep")
    ap.add_argument("--bao-cao", metavar="PATH",
                    help="Ghi luon ban BAO CAO danh so ra tep nay, de gui thang "
                         "len Telegram bang publish.py --file")
    ap.add_argument("--khong-xoa-bat-buoc", action="store_true",
                    help="Thu: kiem nhung KHONG xoa muc bat buoc da dua")
    ap.add_argument("--out", help="Thu: ghi manifest ra tep nay thay vi state/<brand>/")
    ap.add_argument("--nguon", help="quet.json cua scan_business (Vera): de vai chon bang so thu tu `k`, "
                                    "script tu lay link, tieu de, so bao")
    a = ap.parse_args()

    ds = json.loads(Path(a.infile).read_text(encoding="utf-8"))
    if isinstance(ds, dict):
        ds = ds.get("items") or ds.get("candidates") or []
    if not ds:
        sys.exit("Danh sach rong — khong ghi manifest.")
    nguon = []
    if a.nguon and Path(a.nguon).exists():
        nguon = json.loads(Path(a.nguon).read_text(encoding="utf-8")).get("tin_moi", [])

    # "market" o day KHONG phai slug sot lai cua LOW-14 — no la chu Ong Chu (va
    # script cron cu) con go duoc; giu de lenh cu khong gay giua chung.
    vai_bb = "vera" if a.vai in ("market", "vera") else a.vai
    items = []
    for i, it in enumerate(ds, 1):
        muc = _muc_tu_nop(it, i, nguon, a.vai, vai_bb)
        if muc is not None:
            items.append(muc)
    items = them_bat_buoc(items, nguon, a.vai, vai_bb)
    mc.danh_so(items)

    # GIO VN, khong phai UTC. Ca doi song theo ngay VN: cron quet chay 05:01 VN,
    # `quet_chuan_bi.workdir` dat thu muc `vera_20260912`, bao cao mac dinh cua
    # `bao_cao_manifest.dung` cung lay gio VN. Rieng dong nay truoc 12/09/2026
    # lay UTC — tuc 05:01 VN van con la ngay HOM QUA. Hai hau qua that sang
    # 12/09: bao cao len topic de "Vera — 2026-09-11" cho ban quet ngay 12, va
    # ten tep dung vao ten cua hom truoc (da co) nen manifest roi xuong nhanh
    # `duong_ra_moi` -> `vera_candidates_2026-09-11_t2201.json`.
    ngay = datetime.now(quet_chung.VN).strftime("%Y-%m-%d")
    ten = f"{TIEN_TO[a.vai]}_{ngay}{('_' + a.hau_to) if a.hau_to else ''}.json"
    out = Path(a.out) if a.out else STATE / ten
    # KHONG ghi de manifest da co — ly do day du o `manifest_chung.duong_ra_moi`.
    # Ten ban ghi lai bo hau to di (giu nguyen hanh vi cu): `--hau-to` la co THU
    # thu cong, ban ghi lai cua no van mang ten ban chinh.
    if out.exists() and not a.out:
        out = mc.duong_ra_moi(STATE / f"{TIEN_TO[a.vai]}_{ngay}.json")
    mc.ghi_manifest(out, a.vai, items)
    print(out)
    mc.chot_bat_buoc(vai_bb, items, a.khong_xoa_bat_buoc)
    for it in items:
        print(f"  {it['index']}. [{it['via']}] {it['title'][:66]}", file=sys.stderr)
    mc.viet_bao_cao(a.bao_cao, items, a.vai, ngay)


if __name__ == "__main__":
    main()
