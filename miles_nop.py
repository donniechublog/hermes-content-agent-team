#!/usr/bin/env python3
"""miles_nop.py — NOP caption cua Miles: chuan hoa, do, cong chan, ghep draft, day
vao hang duyet. Vai chi viet caption.txt.

  1. Chuan hoa co hoc (thay vi bat vai sua roi chay lai): em-dash/en-dash ->
     dau phay, khoang trang thua, >2 dong trong.
  2. caption_check.kiem voi tu lieu that: loi thi in tung dong + con so cu the
     (ky tu, cau, so cho co so) va cach sua; thoat 1. Vai sua DUNG cho, chay lai.
  3. draft_write.py (ghep meta, luu draft) + `approve_service.py push` (vao hang
     duyet). --khong-push de thu.

Dung:
    venv/bin/python miles_nop.py <draft_id>
    venv/bin/python miles_nop.py <draft_id> --khong-push     # thu: chi kiem + ghi draft thu
"""
import json
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import anh_chuan_bi as cb                                    # noqa: E402
import caption_check                                         # noqa: E402

DRAFTS = cb.DRAFTS


def chuan_hoa(t: str) -> tuple:
    """Sua co hoc, tra ve (caption, [ghi chu da sua])."""
    ghi = []
    t2 = t.replace("\r\n", "\n").strip()
    if "—" in t2 or "–" in t2:
        t2 = re.sub(r"\s*[—–]\s*", ", ", t2)
        t2 = re.sub(r",\s*,", ",", t2)
        ghi.append("đã đổi em-dash/en-dash thành dấu phẩy")
    t3 = re.sub(r"[ \t]+\n", "\n", t2)
    t3 = re.sub(r"\n{3,}", "\n\n", t3)
    t3 = re.sub(r"[ \t]{2,}", " ", t3)
    if t3 != t2:
        ghi.append("đã dọn khoảng trắng/dòng trống thừa")
    return t3, ghi


def main() -> int:
    ap = argparse.ArgumentParser(description="Nop caption cua Miles (tat dinh)")
    ap.add_argument("draft_id")
    ap.add_argument("--caption")
    ap.add_argument("--khong-push", action="store_true", help="Thu: kiem + ghi draft vao workdir, khong push")
    a = ap.parse_args()

    cb.nap_meta(a.draft_id)                  # dat CT_BRAND theo brand cua draft
    import env_load
    wd = cb.workdir(env_load.state_dir(), a.draft_id)
    p_cap = Path(a.caption) if a.caption else wd / "caption.txt"
    if not p_cap.exists():
        sys.exit(f"Chua co caption: {p_cap} — viet caption theo brief ({wd / 'brief_miles.md'}) roi chay lai.")
    cap, ghi = chuan_hoa(p_cap.read_text(encoding="utf-8"))
    for g in ghi:
        print(f"[da sua] {g}")
    p_cap.write_text(cap, encoding="utf-8")

    p_tl = wd / "tu_lieu.md"
    tl = p_tl.read_text(encoding="utf-8") if p_tl.exists() else ""
    loi, canh, tin = caption_check.kiem(cap, tl)
    print(f"[do] {tin.get('do_dai', 0)} ký tự | {tin.get('so_cau', 0)} câu | {tin.get('so_trong_caption', 0)} chỗ có số"
          f" | tỉ lệ dấu {tin.get('ty_le_dau', 0):.2f}"
          + (f" | nguồn có {tin['cau_so_trong_nguon']} câu số liệu" if "cau_so_trong_nguon" in tin else ""))
    for c in canh:
        print(f"[nhac] {c}")
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        if tin.get("do_dai", 0) > caption_check.GIOI_HAN:
            print(f"[LOI] cần cắt ít nhất {tin['do_dai'] - caption_check.GIOI_HAN} ký tự "
                  "(cắt tính từ thừa, gộp câu; không cắt số liệu)")
        print(f"\nSua {p_cap} theo cac dong [LOI] roi chay lai: venv/bin/python miles_nop.py {a.draft_id}")
        return 1

    if a.khong_push:
        (wd / "draft_thu.txt").write_text(cap, encoding="utf-8")
        print(f"[thu] DAT cong chan. Khong ghep draft/khong push (--khong-push). Caption o {p_cap}")
        print(f"Ket qua task: caption {tin.get('do_dai')} ký tự đạt cổng chặn (thử).")
        return 0

    r = subprocess.run([sys.executable, str(ROOT / "draft_write.py"), a.draft_id,
                        "--caption-file", str(p_cap)] + (["--tu-lieu", str(p_tl)] if tl else []),
                       cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        for d in ((r.stderr or "") + "\n" + (r.stdout or "")).strip().splitlines()[-6:]:
            print(f"[LOI] {d}")
        return 1
    print((r.stdout or "").strip())
    r2 = subprocess.run([str(ROOT / "venv/bin/python"), str(ROOT / "approve_service.py"), "push", a.draft_id],
                        cwd=str(ROOT), capture_output=True, text=True, timeout=180)
    if r2.returncode != 0:
        for d in ((r2.stderr or "") + "\n" + (r2.stdout or "")).strip().splitlines()[-6:]:
            print(f"[LOI] push: {d}")
        return 1
    print((r2.stdout or "").strip()[-300:])
    # Bang den (kanban swarm, 05/09): ghi ban giao cua Miles len the goc; JSON nay
    # cung in ra "[metadata]" de Miles dan vao kanban_complete (len bang den).
    # Best-effort.
    md = {"do_dai": tin.get("do_dai"), "so_cau": tin.get("so_cau"),
          "so_trong_caption": tin.get("so_trong_caption"),
          "draft": f"drafts/{a.draft_id}.json"}
    import nop_chung as nc
    nc.ghi_bang_den(a.draft_id, "caption", md, "miles")
    print(f"[xong] caption {tin.get('do_dai')} ký tự, {tin.get('so_cau')} câu, "
          f"{tin.get('so_trong_caption')} chỗ có số — đã ghép draft và đẩy vào hàng duyệt.")
    print("[metadata] " + json.dumps(md, ensure_ascii=False))
    print("Ket qua task (dung dong nay de ket thuc task): "
          f"Viết caption {tin.get('do_dai')} ký tự, {tin.get('so_trong_caption')} chỗ có số, đã vào hàng duyệt.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
