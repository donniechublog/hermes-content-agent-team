#!/usr/bin/env python3
"""ada_submit.py — NỘP của Ada: dựng báo cáo (số liệu do ada_prepare.py, nhận xét
từ spec.json), kiểm tiếng Việt, lưu state/<brand>/journal/analysis_<ngày>.md,
gửi topic analyst.

Dùng:
    venv/bin/python ada_submit.py
    venv/bin/python ada_submit.py --khong-gui
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import ada_prepare as ab                                    # noqa: E402
import caption_check as cc                                   # noqa: E402
import env_load                                              # noqa: E402
import state_paths                                           # noqa: E402
from vietnamese import find_face_mark, drop_mark_forbid               # noqa: E402


# LOW-246: khoa spec.json cu (vai viet truoc deploy, doc lai khi "Lam lai") -> khoa moi.
# MOT cho duy nhat; bang docs/tu_dien_ten/ada_keys_v2.json (ada_spec).
LEGACY_SPEC_KEYS = {"nhan_xet": "observations", "de_xuat_rubric": "rubric_proposals", "ket_luan": "conclusion"}
LEGACY_PROPOSAL_KEYS = {"thay_doi": "change", "bang_chung": "evidence"}
SPEC_KEYS = ("observations", "rubric_proposals", "token", "router", "conclusion")


def _legacy_spec(spec):
    """Spec khoa cu/lan -> khoa moi; co ca hai thi khoa moi thang. Khong sua dau vao."""
    def rename(d, table):
        out = {}
        for k, v in d.items():
            if k in table:
                if table[k] not in d:
                    out[table[k]] = v
            else:
                out[k] = v
        return out
    if not isinstance(spec, dict):
        return spec
    out = rename(spec, LEGACY_SPEC_KEYS)
    if isinstance(out.get("rubric_proposals"), list):
        out["rubric_proposals"] = [rename(x, LEGACY_PROPOSAL_KEYS) if isinstance(x, dict) else x
                                   for x in out["rubric_proposals"]]
    return out


def use_report(m: dict, spec: dict) -> str:
    mf, dr, tk = m["candidates"], m["draft"], m["token"]
    L = [f"<b>Ada: phân tích {m['days']} ngày qua</b>", ""]
    L.append(f"<b>Tin:</b> quét {mf['item_count']}, chọn {mf['picked_count']}. Theo bậc điểm: "
             + ", ".join(f"{k} {v[1]}/{v[0]}" for k, v in mf["by_score_tier"].items()) + ".")
    L.append("<b>Draft:</b> " + ", ".join(f"{k} {v}" for k, v in dr["by_status"].items()) + ".")
    vai_nang = sorted(tk["by_role"].items(), key=lambda kv: -kv[1]["input"])[:3]
    if vai_nang:
        L.append("<b>Token nặng nhất:</b> " + "; ".join(f"{k} {v['input']:,} input / {v['tool']} tool" for k, v in vai_nang) + ".")
    L += ["", "<b>Nhận xét</b>"]
    for x in spec.get("observations") or []:
        L.append(f"• {drop_mark_forbid(str(x))}")
    L += ["", "<b>Đề xuất chỉnh rubric</b>"]
    dx = spec.get("rubric_proposals") or []
    if not dx:
        L.append("Không có gì đáng chỉnh.")
    for x in dx:
        L.append(f"• {drop_mark_forbid(str(x.get('change', '')))} — bằng chứng: {drop_mark_forbid(str(x.get('evidence', '')))}")
    if spec.get("token"):
        L += ["", f"<b>Token:</b> {drop_mark_forbid(str(spec['token']))}"]
    nk = tk.get("router_journal") or {}
    if nk.get("by_date"):
        L += ["", "<b>9router theo ngày</b> (req / $ / cache% / fallback / lỗi)"]
        for d in nk["by_date"]:
            L.append(f"• {d['date']}: {d['req']} / ${d['usd']} / {d['cache_pct']}% / {d['fallback']} / {d['error_count']}")
    if nk.get("cost_by_role"):
        L.append("<b>$ theo vai:</b> " + "; ".join(f"{k} ${t['usd']}" for k, t in list(nk["cost_by_role"].items())[:4]) + ".")
    if nk.get("brand"):
        L.append("<b>$/bài:</b> " + "; ".join(
            f"{b} {('$' + str(t['usd_per_published'])) if t['usd_per_published'] is not None else 'chưa có bài'} "
            f"({t['published_count']} bài)"
            for b, t in nk["brand"].items()) + ".")
    if spec.get("router"):
        L += ["", f"<b>Router:</b> {drop_mark_forbid(str(spec['router']))}"]
    if spec.get("conclusion"):
        L += ["", f"<b>Kết luận:</b> {drop_mark_forbid(str(spec['conclusion']))}"]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Nộp báo cáo của Ada")
    ap.add_argument("--khong-gui", action="store_true")
    a = ap.parse_args()
    wd = ab.workdir()
    if not (wd / state_paths.ADA_METRICS_FILE).exists():
        sys.exit("Chưa chuẩn bị. Chạy trước: venv/bin/python ada_prepare.py")
    if not (wd / "spec.json").exists():
        sys.exit(f"Chưa có spec: {wd / 'spec.json'} — viết theo brief rồi chạy lại.")
    m = json.loads((wd / state_paths.ADA_METRICS_FILE).read_text(encoding="utf-8"))
    try:
        spec = _legacy_spec(json.loads((wd / "spec.json").read_text(encoding="utf-8")))
    except Exception as e:                                   # noqa: BLE001
        sys.exit(f"[LOI] spec.json không phải JSON hợp lệ: {type(e).__name__}: {e}")
    loi, canh = [], []
    for k in SPEC_KEYS:
        v = spec.get(k)
        chuoi = " ".join(str(x.get("change", "")) + " " + str(x.get("evidence", "")) if isinstance(x, dict) else str(x)
                         for x in (v if isinstance(v, list) else [v or ""]))
        mat = find_face_mark(chuoi)
        if mat:
            loi.append(f"{k}: tiếng Việt mất dấu ({', '.join(mat)})")
    if not spec.get("observations"):
        loi.append("thiếu observations")

    # ADA PHAI CO BANG CHUNG, KHONG CHI CO CHU (06/09/2026).
    #
    # Truoc do cong chi kiem dau tieng Viet va "observations khong rong": brief bat
    # "moi y kem bang chung (bai nao, diem bao nhieu)" va bat rubric_proposals[]
    # co `evidence`, nhung ca hai chi la CHU trong brief — mot de xuat co
    # `evidence` rong van in ra binh thuong. Ma bao cao cua Ada la thu Ong Chu
    # dung de doi rubric, tuc mot con so bia o day di thang vao cach cham diem.
    #
    # `ada_metrics.json` da chua moi so THAT, va `brief.md` in chung ra — nen doi chieu
    # duoc bang code, dung ky thuat `caption_check.count_is` (so sanh theo chuoi
    # chu so, bo dau cham/phay/cach, vi hai ben viet "2,5 ti" / "2.5B" / "2500
    # trieu"). Chi CANH BAO, khong chan: hai cach viet khac nhau la chuyen
    # thuong, chan cung se chan oan.
    thieu_bc = [str(x.get("change", ""))[:50] for x in (spec.get("rubric_proposals") or [])
                if isinstance(x, dict) and not str(x.get("evidence", "")).strip()]
    if thieu_bc:
        loi.append("rubric_proposals thiếu evidence: " + "; ".join(f'"{t}"' for t in thieu_bc[:3])
                   + " — đề xuất đổi cách chấm điểm mà không nêu bài nào/điểm bao nhiêu "
                     "thì Ông Chủ không có cách nào kiểm")
    brief = ""
    try:
        brief = (wd / "brief.md").read_text(encoding="utf-8")
    except OSError:
        pass
    if brief:
        chuoi = " ".join(
            (str(x.get("change", "")) + " " + str(x.get("evidence", "")))
            if isinstance(x, dict) else str(x)
            for k in SPEC_KEYS
            for x in (spec.get(k) if isinstance(spec.get(k), list) else [spec.get(k) or ""]))
        la = cc.count_is(chuoi, brief)
        if la:
            canh.append("số không có trong brief: " + ", ".join(la[:6])
                        + " — Ada chỉ được dùng số của brief, không tự tính lại "
                          "hay nhớ từ hôm trước")
    for c in canh:
        print(f"[canh bao] {c}")
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        return 1
    bao_cao = use_report(m, spec)
    ngay = datetime.now(ab.VN).strftime("%Y-%m-%d")
    p_md = env_load.state_dir() / state_paths.JOURNAL_DIR / f"{state_paths.ANALYSIS_REPORT_PREFIX}{ngay}.md"
    p_md.parent.mkdir(parents=True, exist_ok=True)
    p_md.write_text(bao_cao, encoding="utf-8")
    (wd / state_paths.ADA_REPORT_FILE).write_text(bao_cao, encoding="utf-8")
    if a.khong_gui:
        print(f"[thu] không gửi. Báo cáo lưu {p_md}:\n\n{bao_cao}")
        return 0
    r = subprocess.run([str(ROOT / "venv/bin/python"), str(ROOT / "publish.py"), "--to-env", "TELEGRAM_GROUP_ID",
                        "--thread-name", "ada", "--file", str(wd / state_paths.ADA_REPORT_FILE)],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"[LOI] gửi: {(r.stderr or r.stdout)[-300:]}")
        return 1
    print(f"[xong] báo cáo đã gửi topic analyst, lưu {p_md}")
    print("Kết quả (trả lời Ông Chủ đúng một câu): Báo cáo phân tích đã gửi trong topic analyst.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
