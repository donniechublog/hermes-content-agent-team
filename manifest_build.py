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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_common                                            # noqa: E402
import env_load                                             # noqa: E402
import required                                             # noqa: E402
import manifest_common as mc                                 # noqa: E402

ROOT = env_load.ROOT
STATE = env_load.state_dir()      # state/<brand>/ — cung cho approve_service doc

# Nhan chuan la TIENG ANH (approve_service.LABEL_STANDARD) — SOUL/brief cua Finn ke
# ARXIV / MODEL / LAB / INFRA / TOOL / ENGINEERING / BUSINESS / RESEARCH /
# SECURITY. Bang cu chi co ban tieng Viet nen moi lan Finn nop deu bi bao
# "category khong hop le" (thay 04/09/2026 khi chay thu scan_submit). Nhan ca hai.
VALID_CATEGORIES = {"ARXIV", "MODEL", "LAB", "INFRA", "TOOL", "ENGINEERING", "BUSINESS",
                    "RESEARCH", "SECURITY", "OPEN SOURCE", "OPEN WEIGHTS", "BENCHMARK",
                    "M&A", "UPDATE",
                    "MO HINH", "MÔ HÌNH", "THU NGHIEM", "THỬ NGHIỆM",
                    "HA TANG", "HẠ TẦNG", "CONG CU", "CÔNG CỤ"}


# Brief cua Finn ghi "toi da 8 tin". Truoc 06/09/2026 chi co cau chu do, khong
# co cong chan: vai nop 12 muc thi ca 12 vao manifest. Muc BAT BUOC khong bi
# tran nay cat (luat Ong Chu: quet thay la phai dua).
MAX_PICK = 8


_norm = scan_common.standard_link          # mot ban duy nhat, xem scan_common


def _item_from_pick(p: dict, c: dict, problems: list) -> dict:
    """Mot muc danh gia cua Finn + mot ung vien tu candidates.json -> mot muc
    manifest. Khong doc dia, khong ghi gi; moi thu can sua deu ghi vao
    `problems` va deu di kem ten bai de Ong Chu doi chieu duoc tren bao cao."""
    cat = (p.get("category") or "").strip()
    cat_xau = bool(cat) and cat.upper() not in VALID_CATEGORIES
    if cat_xau:
        problems.append(f"category khong hop le: {cat!r} -> TOOL (bai: {c['title'][:40]})")

    tech, sua_t = mc.score_part(p.get("score_technical", 0), "score_technical", 30, problems, c["title"])
    rel, sua_r = mc.score_part(p.get("score_relevance", 0), "score_relevance", 20, problems, c["title"])
    ghi_chu = p.get("score_reason", "")
    if sua_t or sua_r or cat_xau:
        ghi_chu = (ghi_chu + " | script sua: "
                   + ", ".join(x for x in (
                       "diem ky thuat cat ve dai" if sua_t else "",
                       "diem lien quan cat ve dai" if sua_r else "",
                       f"category {cat!r} khong hop le -> TOOL" if cat_xau else "") if x)).strip()

    # Cung mot bo kiem cho ca ba vai di tim tin (`manifest_common.single_summary`):
    # headline la thu DUY NHAT Ong Chu doc tren topic, va brief hua "summary_vi
    # mot menh de <= 15 tu". Truoc 06/09/2026 nhanh Finn khong kiem gi — summary
    # dai ba dong len bao cao y nguyen, va em-dash lot xuong tan caption.
    tom, canh = mc.single_summary(p.get("summary_vi"), f"bai: {c['title'][:40]}")
    problems.extend(canh)

    return {
        # tu candidates.json — Finn khong phai go lai
        "title": c["title"],
        "link": c["link"],
        "source_note": f"{required.source_label(c['source'])}, {c['points']} diem, "
                      f"{c['comments']} binh luan",
        "via": c["via"],
        "image_url": p.get("image_url") or c.get("image_url"),
        # tu danh gia cua Finn
        "category": "TOOL" if (cat_xau or not cat) else cat,
        "score_technical": tech,
        "score_relevance": rel,
        "score": c["score_partial"] + tech + rel,
        "score_reason": ghi_chu,
        "summary_vi": tom,
        # tinh san, de doi chieu ve sau
        "score_recency": c["score_recency"],
        "score_spread": c["score_spread"],
        "picked": False,
    }


def gather_item(picks: list, cands: list) -> tuple:
    """picks cua Finn + candidates -> (items, problems). Ham THUAN."""
    by_link = {_norm(c["link"]): c for c in cands}
    items, problems = [], []
    da_chon = set()                    # k / link da lay: chan vai nop trung mot tin
    for p in picks:
        # Chon bang SO THU TU `k` trong brief (tu 05/09/2026): vai khong phai chep URL
        # "y het" nua — sai mot ky tu la "khong tim thay" (4/8 muc, 05/09). Van nhan
        # `link` cho tuong thich.
        k = p.get("k") or p.get("stt") or p.get("#")
        if k is not None:
            c, loi = mc.pick_by_k(k, cands, "")
            if not c:
                problems.append(loi.lstrip(": "))
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
        items.append(_item_from_pick(p, c, problems))
    return items, problems


def crop_ceiling(items: list, bb_link: set, problems: list) -> list:
    """Tran 8 tin — CHI ap cho tin thuong.

    Muc BAT BUOC vai da nop phai o ngoai tran: muc ton tu hom truoc duoc
    `_supplement_required` gan score_partial=0 nen tran diem chi con 50 (0+30+20),
    LUON xep chot va LUON bi cat. Cat xong thi `required.check` lai them BAN
    TRONG (score=0, summary_vi rong, ghi chu "vai bo sot") — bao cao gui Ong Chu
    do oan cho vai la bo sot dung cai tin no vua cham ky, con vai viet bai thi
    mat sach tom tat (06/09/2026)."""
    la_bb = [it for it in items if required.chuan_link(it["link"]) in bb_link]
    thuong = [it for it in items if required.chuan_link(it["link"]) not in bb_link]
    if len(thuong) > MAX_PICK:
        thuong.sort(key=lambda x: x["score"], reverse=True)
        bo = thuong[MAX_PICK:]
        thuong = thuong[:MAX_PICK]
        problems.append(f"vai nop {len(thuong) + len(bo)} tin thuong, tran la {MAX_PICK} — "
                        f"giu {MAX_PICK} tin diem cao nhat, bo: "
                        + "; ".join(f"{b['title'][:40]} ({b['score']}d)" for b in bo)
                        + (f" (giu nguyen {len(la_bb)} muc BAT BUOC, khong tinh vao tran)"
                           if la_bb else ""))
    return la_bb + thuong


def extra_required(items: list, cands: list) -> list:
    """Muc BAT BUOC vai bo sot: script TU THEM (diem vai = 0, ghi chu ro tren bao
    cao) thay vi tu choi roi bat vai sua toi da 2 vong (05/09/2026: 4/8 muc, Finn
    mo 18 tool call roi block task). Luat Ong Chu van giu: quet thay la phai dua."""
    by_link = {_norm(c["link"]): c for c in cands}
    da_co = {_norm(it["link"]) for it in items}
    for v in required.check("finn", items):
        c = by_link.get(_norm(v.get("link", "")))
        if not c or _norm(c["link"]) in da_co:
            print(f"  [canh bao] muc BAT BUOC khong co trong candidates, khong tu them duoc: "
                  f"{str(v.get('name', ''))[:60]}", file=sys.stderr)
            continue
        items.append({
            "title": c["title"], "link": c["link"],
            "source_note": f"{required.source_label(c['source'])}, {c['points']} diem, {c['comments']} binh luan",
            "via": c["via"], "image_url": c.get("image_url"),
            "category": "TOOL", "score_technical": 0, "score_relevance": 0,
            "score": c["score_partial"],
            "score_reason": "BAT BUOC, vai bo sot — script tu them, chua cham",
            "summary_vi": "", "score_recency": c["score_recency"],
            "score_spread": c["score_spread"], "picked": False, "auto_added": True,
        })
        da_co.add(_norm(c["link"]))
        print(f"  [tu them] muc BAT BUOC vai bo sot: {c['title'][:60]}", file=sys.stderr)
    return items


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
    ap.add_argument("--ghi-de", action="store_true",
                    help="Cho ghi de manifest da co (chi dung khi THU — ban that "
                         "khong duoc ghi de vi approve_pick ghi nguoc picked/assignments vao do)")
    ap.add_argument("--khong-xoa-bat-buoc", action="store_true",
                    help="Thu: kiem nhung KHONG xoa muc bat buoc da dua")
    a = ap.parse_args()

    cands = json.loads(Path(a.candidates).read_text(encoding="utf-8"))["candidates"]
    picks = json.loads(Path(a.picks).read_text(encoding="utf-8"))
    if isinstance(picks, dict):
        picks = picks.get("picks") or picks.get("items") or []

    items, problems = gather_item(picks, cands)
    bb_link = {required.chuan_link(v.get("link", "")) for v in required.read("finn").values()
               if v.get("link")}
    items = crop_ceiling(items, bb_link, problems)

    if problems:
        # In ca stdout LAN stderr: scan_submit chi in stdout khi rc=0 nen canh bao
        # o stderr truoc day khong ai thay (audit 06/09/2026).
        print("PHAT HIEN VAN DE:")
        for pr in problems:
            print("  - " + pr)
            print("  - " + pr, file=sys.stderr)

    items = extra_required(items, cands)
    # CONG RONG — dat NGOAI khoi `if problems`. Truoc 06/09/2026 no nam LOT
    # TRONG khoi do, ma ca hai duong vao deu cho problems RONG: Finn ghi picks
    # la `[]`, hoac ghi dict sai khoa (`{"tin": [...]}` — script chi nhan "picks"
    # / "items"). Khi ay items=[] va problems=[] nen cong khong bao gio chay:
    # script ghi manifest 0 muc, ghi bao cao chi co tieu de + dong moi tra loi
    # so ma khong co so nao, tra rc=0, va scan_submit gui thang len topic.
    # Nang hon: scan_submit co dinh ten `finn_candidates_<ngay>.json` nen lan chay
    # lai de THANG len tep tot trong ngay, con approve_pick chon manifest theo
    # mtime — ban rong thanh ban moi nhat, khong co duong lui.
    if not items:
        sys.exit("Khong co muc nao hop le — KHONG ghi manifest (tranh de len ban tot "
                 "cua lan chay truoc).\n"
                 "  - picks rong hay sai khoa? Script chi doc mang, hoac dict co "
                 "khoa \"picks\"/\"items\".\n"
                 "  - That su hom nay khong co tin nao dat nguong thi chay lai "
                 "scan_submit voi --khong-co.")

    items.sort(key=lambda x: x["score"], reverse=True)
    mc.list_count(items)

    out = Path(a.out)
    # KHONG ghi de manifest da co trong ngay (sua 06/09/2026 dot 2) — cung luat
    # ma manifest_write da ap cho Nova/Vera, rieng nhanh Finn thi chua. Ly do day
    # du o `manifest_common.path_out_new`.
    if out.exists() and not a.ghi_de:
        moi = mc.path_out_new(out)
        print(f"[canh bao] {out.name} da co — ghi ban moi ra {moi.name} de khong "
              "mat co picked/assignments cua ban dang dung", file=sys.stderr)
        out = moi
    mc.write_manifest(out, "finn", items)
    print(f"da ghi {len(items)} muc -> {out}")
    mc.finalize_required("finn", items, a.khong_xoa_bat_buoc)
    mc.write_report(a.bao_cao, items, "finn")
    for it in items:
        print(f"  #{it['index']} [{it['score']:3d}] {it['title'][:60]}")


if __name__ == "__main__":
    main()
