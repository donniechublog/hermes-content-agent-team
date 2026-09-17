#!/usr/bin/env python3
"""ada_prepare.py — BRIEF cho Ada (analyst): mọi con số đo được, in một lần.

Trước (28/08): mỗi lượt Ada 13–40 tool call, toàn truy vấn sqlite tay vào
kanban.db/state.db, ls drafts, đọc manifest từng tệp. Giờ script gom:

  - Manifest N ngày (Finn/Nova/Vera): từng tin, điểm, có được chọn không, giao
    vai nào → tỉ lệ chọn theo bậc điểm / nguồn / category; tin điểm cao bị bỏ,
    tin điểm thấp được chọn.
  - Draft: pending / published / rejected + điểm Finn của bài đó.
  - Kanban: task theo vai, done/blocked/failed, thời gian chạy, lỗi cuối.
  - Token: tool call, input token, api call theo vai (profiles/*/state.db) +
    chi phí thật 9router N ngày (từ nhật ký ngày của monitor_9router).
  - 9router theo NGÀY (monitor_9router.py): req/$/cache%/lật model/lỗi/khoá
    API/IP máy gọi từng ngày, để so ngày này với ngày trước thay vì một số gộp.

Ada chỉ viết nhận xét + đề xuất rubric có bằng chứng vào spec.json, rồi
ada_submit.py dựng báo cáo và gửi topic analyst.

Dùng:
    venv/bin/python ada_prepare.py [--ngay 7]
"""
import argparse
import collections
import json
import os
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import env_load                                              # noqa: E402
import state_paths                                           # noqa: E402
import hermes_adapter                                        # noqa: E402

VN = timezone(timedelta(hours=7))
DRAFTS = ROOT / "drafts"
HERMES = env_load.hermes_home()


def workdir() -> Path:
    wd = state_paths.prepare_root(env_load.state_dir()) / f"ada_{datetime.now(VN).strftime('%Y%m%d')}"
    wd.mkdir(parents=True, exist_ok=True)
    return wd


def _tier(score) -> str:
    try:
        s = int(score)
    except (TypeError, ValueError):
        return "không điểm"
    return "≥90" if s >= 90 else "80–89" if s >= 80 else "70–79" if s >= 70 else "<70"


def gather_manifest(ngay: int) -> dict:
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
            items.append({"role": d.get("scan_role") or p.name.split("_")[0], "title": it.get("title", "")[:70],
                          "score": it.get("score"), "picked": bool(it.get("picked")),
                          "source": (it.get("via") or it.get("source_note") or "").split(",")[0][:20],
                          "category": it.get("category", ""), "image_roles": ",".join(g.get("image_role", "")
                                                                                   for g in it.get("assignments", [])),
                          "date": p.name.rsplit("_", 1)[-1][:10]})
    theo_bac = collections.defaultdict(lambda: [0, 0])
    theo_nguon = collections.defaultdict(lambda: [0, 0])
    theo_cat = collections.defaultdict(lambda: [0, 0])
    for it in items:
        for k, d in ((_tier(it["score"]), theo_bac), (it["source"] or "?", theo_nguon), (it["category"] or "?", theo_cat)):
            d[k][0] += 1
            d[k][1] += int(it["picked"])
    cao_bo = sorted([it for it in items if not it["picked"] and (it["score"] or 0) >= 85],
                    key=lambda x: -(x["score"] or 0))[:8]
    thap_chon = sorted([it for it in items if it["picked"] and (it["score"] or 100) < 75],
                       key=lambda x: (x["score"] or 0))[:8]
    return {"item_count": len(items), "picked_count": sum(1 for it in items if it["picked"]),
            "by_score_tier": dict(theo_bac), "by_source": dict(sorted(theo_nguon.items(), key=lambda kv: -kv[1][0])[:10]),
            "by_category": dict(theo_cat), "high_score_dropped": cao_bo, "low_score_picked": thap_chon}


def gather_draft(ngay: int) -> dict:
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
    return {"by_status": dict(ra), "draft": sorted(ds, key=lambda x: x["status"])[:40]}


def gather_kanban(ngay: int) -> dict:
    # Doc qua hermes_adapter (C2) — kanban.db la bang cua hermes-agent, chi mot
    # tep duoc biet schema cua no.
    viec = hermes_adapter.job(tu_ts=int(time.time() - ngay * 86400))
    if viec is None:
        return {}
    theo_vai = collections.defaultdict(collections.Counter)
    thoi_gian = collections.defaultdict(list)
    loi = []
    for v in viec:
        aid, st, err = v["assignee"], v["status"], v["error"]
        sa, ea = v["started_at"], v["completed_at"]
        theo_vai[aid][st] += 1
        if sa and ea:
            thoi_gian[aid].append(int(ea) - int(sa))
        if st in ("blocked", "failed") or err:
            loi.append({"role": aid, "status": st,
                        "title": (v["title"] or "")[:60], "error": (err or "")[:160]})
    return {"by_role": {k: dict(v) for k, v in theo_vai.items()},
            "avg_seconds": {k: int(sum(v) / len(v)) for k, v in thoi_gian.items() if v},
            "task_errors": loi[:10]}


def gather_token(ngay: int) -> dict:
    ra = {}
    moc = int(time.time() - ngay * 86400)
    loi_doc = []
    for p in hermes_adapter.state_db_each_profile(HERMES):
        prof = p.parent.name
        # Qua adapter (ADF-r2-3), va None (khong doc duoc) phai LO ra trong brief
        # thay vi `continue` cam — Ada tuong vai do khong lam gi ca tuan.
        tt = hermes_adapter.summary_session(p, moc)
        if tt is None:
            loi_doc.append(prof)
            continue
        if tt["sessions"]:
            ra[prof] = dict(tt)
    nk = gather_9router(ngay)
    return {"by_role": ra, "unreadable_profiles": loi_doc,
            "router_cost_by_model": nk.pop("cost_by_model", {}), "router_journal": nk}


def gather_9router(ngay: int) -> dict:
    """N ngày gần nhất từ nhật ký 9router (chốt sẵn bởi cron; thiếu thì dựng tại
    chỗ, chỉ đọc sqlite). Gọn: mỗi ngày một dòng + gộp lật model/lỗi/IP."""
    try:
        import monitor_9router as tdr
    except Exception:                                        # noqa: BLE001
        return {}
    hom_nay = datetime.now(VN).date()
    theo_ngay, lat, loi, khoa = [], collections.Counter(), collections.Counter(), collections.Counter()
    vai, brand, rong, loi_kn, chi_phi = {}, {}, collections.Counter(), [], {}
    # Doc khoa English cua nhat ky 9router (LOW-239); khoa dump Ada: docs/tu_dien_ten/ada_keys_v2.json (LOW-246).
    for i in range(ngay, -1, -1):
        d = (hom_nay - timedelta(days=i)).strftime("%Y-%m-%d")
        m = tdr.download(d, lam_moi=(i == 0))
        if not m or m.get("read_error"):
            continue
        t = m["totals"]
        model_chinh = next(iter(m["by_model"]), "-")
        theo_ngay.append({"date": d[5:], "req": t["req"], "usd": t["usd"], "cache_pct": t["cache_pct"],
                          "fallback": m.get("fallback", 0), "error_count": t["error_count"],
                          "top_cost_model": model_chinh})
        lat.update(m["model_switches"])
        loi.update(m["errors_by_model_status"])
        for nhan, v in m["by_model"].items():          # $ theo model gop N ngay (thay usage_audit)
            c = chi_phi.setdefault(nhan.split(" @ ")[0], {"req": 0, "prompt": 0, "usd": 0.0})
            c["req"] += v["req"]
            c["prompt"] += v["prompt"]
            c["usd"] = round(c["usd"] + v["usd"], 4)
        for k, v in m["by_api_key"].items():
            khoa[k] += v["usd"]
        rong.update(m.get("empty_responses") or {})
        loi_kn += [f"{d[5:]} {x['name']} [{x['error_code']}] {x['last_error'][:60]}"
                   for x in (m.get("connection_errors") or []) if x["error_in_window"]]
        for k, a in (m.get("role_costs") or {}).get("by_role", {}).items():
            t = vai.setdefault(k, {"usd": 0.0, "api": 0, "task_done": 0, "sessions": 0})
            t["usd"] += a["usd"]
            t["api"] += a["api"]
            t["task_done"] += a["task_done"]
            t["sessions"] += a["sessions"]
        for b, x in (m.get("role_costs") or {}).get("by_brand", {}).items():
            t = brand.setdefault(b, {"usd": 0.0, "published_count": 0})
            t["usd"] += x["usd"]
            t["published_count"] += x["published_count"]
    for t in vai.values():
        t["usd"] = round(t["usd"], 4)
        t["usd_task"] = round(t["usd"] / t["task_done"], 4) if t["task_done"] else None
    for t in brand.values():
        t["usd"] = round(t["usd"], 4)
        t["usd_per_published"] = round(t["usd"] / t["published_count"], 4) if t["published_count"] else None
    return {"by_date": theo_ngay, "cost_by_role": dict(sorted(vai.items(), key=lambda kv: -kv[1]["usd"])), "brand": brand,
            "empty_responses": dict(rong.most_common(5)), "connection_errors": loi_kn[:8],
            "model_switches": dict(lat.most_common(6)), "errors": dict(loi.most_common(6)),
            "cost_by_api_key": {k: round(v, 4) for k, v in khoa.items()}, "cost_by_model": chi_phi}


def write_brief(m: dict, wd: Path) -> str:
    ng = m["days"]
    L = [f"# ADA — SỐ LIỆU {ng} NGÀY QUA (đến {datetime.now(VN).strftime('%d/%m %H:%M')} VN), brand {m['brand']}", ""]
    mf = m["candidates"]
    L += [f"## Tin quét & chọn: {mf['item_count']} tin, chọn {mf['picked_count']}"]
    L.append("Theo bậc điểm (tổng/chọn): " + ", ".join(f"{k}: {v[0]}/{v[1]}" for k, v in mf["by_score_tier"].items()))
    L.append("Theo nguồn (tổng/chọn): " + ", ".join(f"{k}: {v[0]}/{v[1]}" for k, v in mf["by_source"].items()))
    L.append("Theo category (tổng/chọn): " + ", ".join(f"{k}: {v[0]}/{v[1]}" for k, v in mf["by_category"].items()))
    if mf["high_score_dropped"]:
        L.append("Điểm ≥85 mà KHÔNG chọn: " + "; ".join(f"[{it['score']}] {it['title'][:45]} ({it['role']}, {it['date']})" for it in mf["high_score_dropped"]))
    if mf["low_score_picked"]:
        L.append("Điểm <75 mà ĐƯỢC chọn: " + "; ".join(f"[{it['score']}] {it['title'][:45]} ({it['role']}, {it['date']})" for it in mf["low_score_picked"]))
    dr = m["draft"]
    L += ["", f"## Draft: {dr['by_status']}"]
    for d in dr["draft"][:20]:
        L.append(f"  - {d['status']:9s} [{d['score'] if d['score'] is not None else '-'}] {d['id']}")
    kb = m["kanban"]
    if kb:
        L += ["", "## Kanban theo vai: " + "; ".join(f"{k}: {v}" for k, v in kb["by_role"].items())]
        L.append("Giây trung bình/task: " + ", ".join(f"{k}: {v}" for k, v in kb["avg_seconds"].items()))
        for e in kb["task_errors"]:
            L.append(f"  - {e['role']} {e['status']}: {e['title']} | {e['error']}")
    tk = m["token"]
    L += ["", "## Token theo vai (phiên / tool call / input token / api call)"]
    if tk.get("unreadable_profiles"):
        L.append("⚠️ KHÔNG đọc được state.db của: " + ", ".join(tk["unreadable_profiles"])
                 + " — số dưới đây THIẾU các vai đó, không phải họ không làm gì")
    for k, v in sorted(tk["by_role"].items(), key=lambda kv: -kv[1]["input"]):
        L.append(f"  - {k}: {v['sessions']} / {v['tool']} / {v['input']:,} / {v['api']} | nặng nhất: "
                 + "; ".join(f"{t} ({tc} tool, {it:,} in)" for t, tc, it in v["top"]))
    if tk["router_cost_by_model"]:
        top = sorted(tk["router_cost_by_model"].items(), key=lambda kv: -kv[1]["usd"])[:8]
        tong = round(sum(v["usd"] for v in tk["router_cost_by_model"].values()), 3)
        L.append(f"Chi phí 9router (chung cả 2 brand, tổng ${tong}, 8 model tốn nhất): " + ", ".join(
            f"{k}: {v['req']} req, {v['prompt']:,} prompt, ${v['usd']}" for k, v in top))
    nk = tk.get("router_journal") or {}
    if nk.get("by_date"):
        L += ["", "## 9router theo ngày (req / $ / cache% / fallback v4-flash→deepseek-chat / lỗi | model tốn nhất)"]
        for d in nk["by_date"]:
            L.append(f"  - {d['date']}: {d['req']} / ${d['usd']} / {d['cache_pct']}% / {d['fallback']} / {d['error_count']} | {d['top_cost_model']}")
        if nk["model_switches"]:
            L.append("Đổi model liên tiếp gộp (gồm cả vai chạy song song, chỉ v4-flash→deepseek-chat là fallback thật): "
                     + "; ".join(f"{k} {v} lần" for k, v in nk["model_switches"].items()))
        if nk["errors"]:
            L.append("Lỗi gộp: " + "; ".join(f"{k} {v}" for k, v in nk["errors"].items()))
        if nk.get("cost_by_role"):
            L.append("$ theo vai (ước lượng phân bổ token, gộp N ngày) — vai: $ / api call / task done / $/task:")
            for k, t in list(nk["cost_by_role"].items())[:12]:
                L.append(f"  - {k}: ${t['usd']} / {t['api']} / {t['task_done']} / "
                         f"{('$' + str(t['usd_task'])) if t['usd_task'] is not None else '-'}")
        if nk.get("brand"):
            L.append("$/bài published theo brand: " + ", ".join(
                f"{b}: ${t['usd']} / {t['published_count']} bài = "
                f"{('$' + str(t['usd_per_published'])) if t['usd_per_published'] is not None else 'chưa có bài'}"
                for b, t in nk["brand"].items()))
        if nk.get("empty_responses"):
            L.append("Phiên rỗng (ok nhưng ≤5 token out dù prompt ≥1k): " + ", ".join(f"{k} {v}" for k, v in nk["empty_responses"].items()))
        if nk.get("connection_errors"):
            L.append("Connection lỗi trong ngày: " + "; ".join(nk["connection_errors"]))
        if nk["cost_by_api_key"]:
            L.append("Theo khoá API: " + ", ".join(f"{k} ${v}" for k, v in nk["cost_by_api_key"].items()))
    L += ["", f"## Viết nhận xét vào: {wd}/spec.json — CHỈ từ số liệu trên, mỗi ý kèm bằng chứng (bài nào, điểm bao nhiêu, kết quả gì)",
          json.dumps({"observations": ["<3–5 điều rút ra, mỗi điều một câu có số>"],
                      "rubric_proposals": [{"change": "<sửa trọng số/tiêu chí gì>", "evidence": "<bài, điểm, kết quả>"}],
                      "token": "<1–2 câu: vai nào đốt nhiều nhất, vì sao, cắt ở đâu>",
                      "router": "<1–2 câu: ngày nào đốt nhất, vai nào đắt nhất và $/bài, có fallback/phiên rỗng/connection lỗi/IP lạ không>",
                      "conclusion": "<một câu>"}, ensure_ascii=False, indent=1),
          "Không có gì đáng chỉnh thì ghi rubric_proposals: [] và nói thẳng. Không suy diễn ngoài số liệu.",
          "", "## Rồi chạy đúng MỘT lệnh:",
          f"cd {ROOT} && venv/bin/python ada_submit.py",
          "Script dựng báo cáo (số liệu do code, nhận xét của bạn), lưu nhật ký, gửi topic analyst. KHÔNG truy "
          "vấn sqlite tay, KHÔNG ls drafts, KHÔNG đọc từng manifest."]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Brief số liệu cho Ada")
    ap.add_argument("--ngay", type=int, default=7)
    ap.add_argument("--im", action="store_true")
    a = ap.parse_args()
    wd = workdir()
    m = {"days": a.ngay, "brand": os.environ.get("CT_BRAND", "?"),
         "candidates": gather_manifest(a.ngay), "draft": gather_draft(a.ngay),
         "kanban": gather_kanban(a.ngay), "token": gather_token(a.ngay)}
    (wd / state_paths.ADA_METRICS_FILE).write_text(json.dumps(m, ensure_ascii=False, indent=1, default=str), encoding="utf-8")
    brief = write_brief(m, wd)
    (wd / "brief.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
