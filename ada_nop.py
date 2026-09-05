#!/usr/bin/env python3
"""ada_nop.py — NỘP của Ada: dựng báo cáo (số liệu do ada_chuan_bi.py, nhận xét
từ spec.json), kiểm tiếng Việt, lưu state/<brand>/nhat_ky/phan_tich_<ngày>.md,
gửi topic analyst.

Dùng:
    venv/bin/python ada_nop.py
    venv/bin/python ada_nop.py --khong-gui
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import ada_chuan_bi as ab                                    # noqa: E402
import env_load                                              # noqa: E402
from card import tim_mat_dau, bo_dau_cam                     # noqa: E402


def dung_bao_cao(m: dict, spec: dict) -> str:
    mf, dr, tk = m["manifest"], m["draft"], m["token"]
    L = [f"<b>Ada: phân tích {m['ngay']} ngày qua</b>", ""]
    L.append(f"<b>Tin:</b> quét {mf['tong']}, chọn {mf['chon']}. Theo bậc điểm: "
             + ", ".join(f"{k} {v[1]}/{v[0]}" for k, v in mf["theo_bac"].items()) + ".")
    L.append(f"<b>Draft:</b> " + ", ".join(f"{k} {v}" for k, v in dr["theo_trang_thai"].items()) + ".")
    vai_nang = sorted(tk["theo_vai"].items(), key=lambda kv: -kv[1]["input"])[:3]
    if vai_nang:
        L.append("<b>Token nặng nhất:</b> " + "; ".join(f"{k} {v['input']:,} input / {v['tool']} tool" for k, v in vai_nang) + ".")
    L += ["", "<b>Nhận xét</b>"]
    for x in spec.get("nhan_xet") or []:
        L.append(f"• {bo_dau_cam(str(x))}")
    L += ["", "<b>Đề xuất chỉnh rubric</b>"]
    dx = spec.get("de_xuat_rubric") or []
    if not dx:
        L.append("Không có gì đáng chỉnh.")
    for x in dx:
        L.append(f"• {bo_dau_cam(str(x.get('thay_doi', '')))} — bằng chứng: {bo_dau_cam(str(x.get('bang_chung', '')))}")
    if spec.get("token"):
        L += ["", f"<b>Token:</b> {bo_dau_cam(str(spec['token']))}"]
    nk = tk.get("nhat_ky_9router") or {}
    if nk.get("theo_ngay"):
        L += ["", "<b>9router theo ngày</b> (req / $ / cache% / fallback / lỗi / IP ngoài)"]
        for d in nk["theo_ngay"]:
            L.append(f"• {d['ngay']}: {d['req']} / ${d['usd']} / {d['cache_pct']}% / {d['lat']} / {d['loi']} / "
                     f"{d['ip_ngoai'] if d['watcher'] else '?'}")
    if nk.get("vai"):
        L.append("<b>$ theo vai:</b> " + "; ".join(f"{k} ${t['usd']}" for k, t in list(nk["vai"].items())[:4]) + ".")
    if nk.get("brand"):
        L.append("<b>$/bài:</b> " + "; ".join(
            f"{b} {('$' + str(t['usd_bai'])) if t['usd_bai'] is not None else 'chưa có bài'} ({t['bai']} bài)"
            for b, t in nk["brand"].items()) + ".")
    if spec.get("router"):
        L += ["", f"<b>Router:</b> {bo_dau_cam(str(spec['router']))}"]
    if spec.get("ket_luan"):
        L += ["", f"<b>Kết luận:</b> {bo_dau_cam(str(spec['ket_luan']))}"]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Nộp báo cáo của Ada")
    ap.add_argument("--khong-gui", action="store_true")
    a = ap.parse_args()
    wd = ab.workdir()
    if not (wd / "xong.json").exists():
        sys.exit("Chưa chuẩn bị. Chạy trước: venv/bin/python ada_chuan_bi.py")
    if not (wd / "spec.json").exists():
        sys.exit(f"Chưa có spec: {wd / 'spec.json'} — viết theo brief rồi chạy lại.")
    m = json.loads((wd / "xong.json").read_text(encoding="utf-8"))
    try:
        spec = json.loads((wd / "spec.json").read_text(encoding="utf-8"))
    except Exception as e:                                   # noqa: BLE001
        sys.exit(f"[LOI] spec.json không phải JSON hợp lệ: {type(e).__name__}: {e}")
    loi = []
    for k in ("nhan_xet", "de_xuat_rubric", "token", "router", "ket_luan"):
        v = spec.get(k)
        chuoi = " ".join(str(x.get("thay_doi", "")) + " " + str(x.get("bang_chung", "")) if isinstance(x, dict) else str(x)
                         for x in (v if isinstance(v, list) else [v or ""]))
        mat = tim_mat_dau(chuoi)
        if mat:
            loi.append(f"{k}: tiếng Việt mất dấu ({', '.join(mat)})")
    if not spec.get("nhan_xet"):
        loi.append("thiếu nhan_xet")
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        return 1
    bao_cao = dung_bao_cao(m, spec)
    ngay = datetime.now(ab.VN).strftime("%Y-%m-%d")
    p_md = env_load.state_dir() / "nhat_ky" / f"phan_tich_{ngay}.md"
    p_md.parent.mkdir(parents=True, exist_ok=True)
    p_md.write_text(bao_cao, encoding="utf-8")
    (wd / "bao_cao.txt").write_text(bao_cao, encoding="utf-8")
    if a.khong_gui:
        print(f"[thu] không gửi. Báo cáo lưu {p_md}:\n\n{bao_cao}")
        return 0
    r = subprocess.run([str(ROOT / "venv/bin/python"), str(ROOT / "publish.py"), "--to-env", "TELEGRAM_GROUP_ID",
                        "--thread-name", "analyst", "--file", str(wd / "bao_cao.txt")],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"[LOI] gửi: {(r.stderr or r.stdout)[-300:]}")
        return 1
    print(f"[xong] báo cáo đã gửi topic analyst, lưu {p_md}")
    print("Kết quả (trả lời Ông Chủ đúng một câu): Báo cáo phân tích đã gửi trong topic analyst.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
