#!/usr/bin/env python3
"""ada_chuan_bi.py — BRIEF cho Ada (analyst): mọi con số đo được, in một lần.

Trước (28/08): mỗi lượt Ada 13–40 tool call, toàn truy vấn sqlite tay vào
kanban.db/state.db, ls drafts, đọc manifest từng tệp. Giờ script gom:

  - Manifest N ngày (Finn/Nova/Vera): từng tin, điểm, có được chọn không, giao
    vai nào → tỉ lệ chọn theo bậc điểm / nguồn / category; tin điểm cao bị bỏ,
    tin điểm thấp được chọn.
  - Draft: pending / published / rejected + điểm Finn của bài đó.
  - Kanban: task theo vai, done/blocked/failed, thời gian chạy, lỗi cuối.
  - Token: tool call, input token, api call theo vai (profiles/*/state.db) +
    chi phí thật 9router N ngày.

Ada chỉ viết nhận xét + đề xuất rubric có bằng chứng vào spec.json, rồi
ada_nop.py dựng báo cáo và gửi topic analyst.

Dùng:
    venv/bin/python ada_chuan_bi.py [--ngay 7]
"""
import argparse
import collections
import glob
import json
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import env_load                                              # noqa: E402

VN = timezone(timedelta(hours=7))
DRAFTS = ROOT / "drafts"
HERMES = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))


def workdir() -> Path:
    wd = env_load.state_dir() / "chuan_bi" / f"ada_{datetime.now(VN).strftime('%Y%m%d')}"
    wd.mkdir(parents=True, exist_ok=True)
    return wd


def _bac(score) -> str:
    try:
        s = int(score)
    except (TypeError, ValueError):
        return "không điểm"
    return "≥90" if s >= 90 else "80–89" if s >= 80 else "70–79" if s >= 70 else "<70"


def gom_manifest(ngay: int) -> dict:
    state = env_load.state_dir()
    moc = time.time() - ngay * 86400
    items = []
    for p in list(state.glob("finn_candidates_*.json")) + list(state.glob("nova_candidates_*.json")) \
            + list(state.glob("vera_candidates_*.json")):
        if p.stat().st_mtime < moc:
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            continue
        for it in d.get("items", []):
            items.append({"vai": d.get("vai") or p.name.split("_")[0], "title": it.get("title", "")[:70],
                          "score": it.get("score"), "picked": bool(it.get("picked")),
                          "source": (it.get("via") or it.get("source_note") or "").split(",")[0][:20],
                          "category": it.get("category", ""), "vai_anh": ",".join(g.get("vai_anh", "")
                                                                                   for g in it.get("da_giao", [])),
                          "ngay": p.name.rsplit("_", 1)[-1][:10]})
    theo_bac = collections.defaultdict(lambda: [0, 0])
    theo_nguon = collections.defaultdict(lambda: [0, 0])
    theo_cat = collections.defaultdict(lambda: [0, 0])
    for it in items:
        for k, d in ((_bac(it["score"]), theo_bac), (it["source"] or "?", theo_nguon), (it["category"] or "?", theo_cat)):
            d[k][0] += 1
            d[k][1] += int(it["picked"])
    cao_bo = sorted([it for it in items if not it["picked"] and (it["score"] or 0) >= 85],
                    key=lambda x: -(x["score"] or 0))[:8]
    thap_chon = sorted([it for it in items if it["picked"] and (it["score"] or 100) < 75],
                       key=lambda x: (x["score"] or 0))[:8]
    return {"tong": len(items), "chon": sum(1 for it in items if it["picked"]),
            "theo_bac": dict(theo_bac), "theo_nguon": dict(sorted(theo_nguon.items(), key=lambda kv: -kv[1][0])[:10]),
            "theo_cat": dict(theo_cat), "cao_bo": cao_bo, "thap_chon": thap_chon}


def gom_draft(ngay: int) -> dict:
    moc = time.time() - ngay * 86400
    ra = collections.Counter()
    ds = []
    for p in DRAFTS.glob("*.json"):
        if p.name.endswith((".meta.json", ".img.json", ".writer.json")) or p.stat().st_mtime < moc:
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            continue
        st = d.get("status", "?")
        ra[st] += 1
        meta = {}
        mp = p.with_name(p.stem + ".meta.json")
        if mp.exists():
            try:
                meta = json.loads(mp.read_text(encoding="utf-8"))
            except Exception:                                # noqa: BLE001
                pass
        ds.append({"id": p.stem[:50], "status": st, "score": meta.get("score"), "brand": d.get("brand", "")})
    return {"theo_trang_thai": dict(ra), "draft": sorted(ds, key=lambda x: x["status"])[:40]}


def gom_kanban(ngay: int) -> dict:
    p = HERMES / "kanban.db"
    if not p.exists():
        return {}
    c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    moc = int(time.time() - ngay * 86400)
    theo_vai = collections.defaultdict(collections.Counter)
    thoi_gian = collections.defaultdict(list)
    loi = []
    for aid, st, title, ca, sa, ea, err in c.execute(
            "select assignee,status,title,created_at,started_at,completed_at,last_failure_error from tasks where created_at>=?", (moc,)):
        theo_vai[aid][st] += 1
        if sa and ea:
            thoi_gian[aid].append(int(ea) - int(sa))
        if st in ("blocked", "failed") or err:
            loi.append({"vai": aid, "status": st, "title": (title or "")[:60], "loi": (err or "")[:160]})
    return {"theo_vai": {k: dict(v) for k, v in theo_vai.items()},
            "giay_trung_binh": {k: int(sum(v) / len(v)) for k, v in thoi_gian.items() if v},
            "loi": loi[:10]}


def gom_token(ngay: int) -> dict:
    ra = {}
    moc = int(time.time() - ngay * 86400)
    for p in glob.glob(str(HERMES / "profiles" / "*" / "state.db")):
        prof = Path(p).parent.name
        try:
            c = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
            n, tools, inp, api = c.execute(
                "select count(*), coalesce(sum(tool_call_count),0), coalesce(sum(input_tokens),0), "
                "coalesce(sum(api_call_count),0) from sessions where started_at>=?", (moc,)).fetchone()
            top = c.execute("select coalesce(title,''), tool_call_count, input_tokens from sessions where started_at>=? "
                            "order by input_tokens desc limit 2", (moc,)).fetchall()
        except Exception:                                    # noqa: BLE001
            continue
        if n:
            ra[prof] = {"phien": n, "tool": tools, "input": inp, "api": api,
                        "top": [(t[:40], tc, it) for t, tc, it in top]}
    chi_phi = {}
    try:
        import usage_audit
        agg, _ = usage_audit.doc_usage(ngay * 24, None)
        chi_phi = {m: {"req": v["req"], "prompt": v["prompt"], "usd": round(v["usd"], 4)} for m, v in agg.items()}
    except Exception:                                        # noqa: BLE001
        pass
    return {"theo_vai": ra, "chi_phi_9router": chi_phi}


def viet_brief(m: dict, wd: Path) -> str:
    ng = m["ngay"]
    L = [f"# ADA — SỐ LIỆU {ng} NGÀY QUA (đến {datetime.now(VN).strftime('%d/%m %H:%M')} VN), brand {m['brand']}", ""]
    mf = m["manifest"]
    L += [f"## Tin quét & chọn: {mf['tong']} tin, chọn {mf['chon']}"]
    L.append("Theo bậc điểm (tổng/chọn): " + ", ".join(f"{k}: {v[0]}/{v[1]}" for k, v in mf["theo_bac"].items()))
    L.append("Theo nguồn (tổng/chọn): " + ", ".join(f"{k}: {v[0]}/{v[1]}" for k, v in mf["theo_nguon"].items()))
    L.append("Theo category (tổng/chọn): " + ", ".join(f"{k}: {v[0]}/{v[1]}" for k, v in mf["theo_cat"].items()))
    if mf["cao_bo"]:
        L.append("Điểm ≥85 mà KHÔNG chọn: " + "; ".join(f"[{it['score']}] {it['title'][:45]} ({it['vai']}, {it['ngay']})" for it in mf["cao_bo"]))
    if mf["thap_chon"]:
        L.append("Điểm <75 mà ĐƯỢC chọn: " + "; ".join(f"[{it['score']}] {it['title'][:45]} ({it['vai']}, {it['ngay']})" for it in mf["thap_chon"]))
    dr = m["draft"]
    L += ["", f"## Draft: {dr['theo_trang_thai']}"]
    for d in dr["draft"][:20]:
        L.append(f"  - {d['status']:9s} [{d['score'] if d['score'] is not None else '-'}] {d['id']}")
    kb = m["kanban"]
    if kb:
        L += ["", "## Kanban theo vai: " + "; ".join(f"{k}: {v}" for k, v in kb["theo_vai"].items())]
        L.append("Giây trung bình/task: " + ", ".join(f"{k}: {v}" for k, v in kb["giay_trung_binh"].items()))
        for e in kb["loi"]:
            L.append(f"  - {e['vai']} {e['status']}: {e['title']} | {e['loi']}")
    tk = m["token"]
    L += ["", "## Token theo vai (phiên / tool call / input token / api call)"]
    for k, v in sorted(tk["theo_vai"].items(), key=lambda kv: -kv[1]["input"]):
        L.append(f"  - {k}: {v['phien']} / {v['tool']} / {v['input']:,} / {v['api']} | nặng nhất: "
                 + "; ".join(f"{t} ({tc} tool, {it:,} in)" for t, tc, it in v["top"]))
    if tk["chi_phi_9router"]:
        top = sorted(tk["chi_phi_9router"].items(), key=lambda kv: -kv[1]["usd"])[:8]
        tong = round(sum(v["usd"] for v in tk["chi_phi_9router"].values()), 3)
        L.append(f"Chi phí 9router (chung cả 2 brand, tổng ${tong}, 8 model tốn nhất): " + ", ".join(
            f"{k}: {v['req']} req, {v['prompt']:,} prompt, ${v['usd']}" for k, v in top))
    L += ["", f"## Viết nhận xét vào: {wd}/spec.json — CHỈ từ số liệu trên, mỗi ý kèm bằng chứng (bài nào, điểm bao nhiêu, kết quả gì)",
          json.dumps({"nhan_xet": ["<3–5 điều rút ra, mỗi điều một câu có số>"],
                      "de_xuat_rubric": [{"thay_doi": "<sửa trọng số/tiêu chí gì>", "bang_chung": "<bài, điểm, kết quả>"}],
                      "token": "<1–2 câu: vai nào đốt nhiều nhất, vì sao, cắt ở đâu>",
                      "ket_luan": "<một câu>"}, ensure_ascii=False, indent=1),
          "Không có gì đáng chỉnh thì ghi de_xuat_rubric: [] và nói thẳng. Không suy diễn ngoài số liệu.",
          "", "## Rồi chạy đúng MỘT lệnh:",
          f"cd {ROOT} && venv/bin/python ada_nop.py",
          "Script dựng báo cáo (số liệu do code, nhận xét của bạn), lưu nhật ký, gửi topic analyst. KHÔNG truy "
          "vấn sqlite tay, KHÔNG ls drafts, KHÔNG đọc từng manifest."]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Brief số liệu cho Ada")
    ap.add_argument("--ngay", type=int, default=7)
    ap.add_argument("--im", action="store_true")
    a = ap.parse_args()
    wd = workdir()
    m = {"ngay": a.ngay, "brand": os.environ.get("CT_BRAND", "?"),
         "manifest": gom_manifest(a.ngay), "draft": gom_draft(a.ngay),
         "kanban": gom_kanban(a.ngay), "token": gom_token(a.ngay)}
    (wd / "xong.json").write_text(json.dumps(m, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    brief = viet_brief(m, wd)
    (wd / "brief.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
