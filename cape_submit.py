#!/usr/bin/env python3
"""cape_submit.py — NỘP của Cape: ráp teaser từ spec (title + paragraphs), kiểm độ
dài + giọng tường thuật (teaser_assemble), gửi vào topic teaser.

Dùng:
    venv/bin/python cape_submit.py "<url>"
    venv/bin/python cape_submit.py "<url>" --khong-gui          # thử: in teaser
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import cape_prepare as jb                                   # noqa: E402
import teaser_assemble                                       # noqa: E402
from vietnamese import find_face_mark, drop_mark_forbid               # noqa: E402


def main() -> int:
    ap = argparse.ArgumentParser(description="Nộp teaser của Cape")
    ap.add_argument("url")
    ap.add_argument("--khong-gui", action="store_true")
    ap.add_argument("--bo-qua-kiem-tra", action="store_true", help="Chỉ khi Ông Chủ yêu cầu")
    a = ap.parse_args()
    wd = jb.workdir(a.url)
    art = wd / "article.json"
    if not art.exists():
        sys.exit(f"Chưa chuẩn bị. Chạy trước: venv/bin/python cape_prepare.py \"{a.url}\"")
    if not (wd / "spec.json").exists():
        sys.exit(f"Chưa có spec: {wd / 'spec.json'} — viết theo brief rồi chạy lại.")
    d = json.loads(art.read_text(encoding="utf-8"))
    try:
        spec = json.loads((wd / "spec.json").read_text(encoding="utf-8"))
    except Exception as e:                                   # noqa: BLE001
        sys.exit(f"[LOI] spec.json không phải JSON hợp lệ: {type(e).__name__}: {e}")
    title = drop_mark_forbid(str(spec.get("title") or "").strip())
    paras = [drop_mark_forbid(str(p).strip()) for p in (spec.get("paragraphs") or []) if str(p).strip()]
    loi = []
    if not title:
        loi.append("thiếu title")
    for i, p in enumerate([title] + paras):
        mat = find_face_mark(p)
        if mat:
            loi.append(f"{'title' if i == 0 else 'đoạn ' + str(i)}: tiếng Việt mất dấu ({', '.join(mat)})")
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        return 1
    try:
        kq = teaser_assemble.assemble(title, paras, d.get("images", []),
                                      bo_qua_kiem_tra=a.bo_qua_kiem_tra,
                                      outline=d.get("outline"))
    except ValueError as e:
        for dong in str(e).splitlines():
            print(f"[LOI] {dong}")
        print(f"\nSửa {wd / 'spec.json'} rồi chạy lại: venv/bin/python cape_submit.py \"{a.url}\"")
        return 1
    caption = kq["caption"]
    (wd / "teaser.txt").write_text(caption, encoding="utf-8")
    print(f"[do] {kq['word_count']} từ | {kq['paragraph_count']} đoạn | emoji {' '.join(kq['emoji_used'])}")

    if a.khong_gui:
        print(f"[thu] không gửi. Teaser:\n\n{caption}")
        return 0
    r = subprocess.run([str(ROOT / "venv/bin/python"), str(ROOT / "publish.py"), "--to-env", "TELEGRAM_GROUP_ID",
                        "--thread-name", "cape", "--file", str(wd / "teaser.txt")],
                       cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    if r.returncode != 0:
        print(f"[LOI] gửi: {(r.stderr or r.stdout)[-300:]}")
        return 1
    print(f"[xong] teaser {kq['word_count']} từ đã gửi vào topic teaser")
    print(f"Kết quả (trả lời Ông Chủ đúng một câu): Teaser {kq['word_count']} từ, {kq['paragraph_count']} đoạn đã gửi "
          "trong topic, tiêu đề: " + title[:80])
    return 0


if __name__ == "__main__":
    sys.exit(main())
