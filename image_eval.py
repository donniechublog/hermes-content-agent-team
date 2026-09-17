#!/usr/bin/env python3
"""Đo quyết định ảnh của engine trên BỘ NHÃN CHUẨN (LOW-224, Ông Chủ chốt 17/09/2026).

Hai con số mọi PR sửa cổng ảnh phải báo, trên cùng một bộ nhãn:

  - LOẠI OAN  = ảnh nhãn `usable=yes` mà engine KHÔNG giữ;
  - LỌT RÁC   = ảnh nhãn `usable=no`  mà engine VẪN giữ.

Trước ticket này không ai đo được hai số đó: ảnh xấu lọt thì Ông Chủ thấy trên
Telegram, ảnh tốt bị bỏ thì vô hình — nên mỗi sự cố chỉ sinh thêm cổng siết
(LOW-201 đảo LOW-45, LOW-182 đảo LOW-12…). Tệp này KHÔNG đổi hành vi engine, chỉ đọc.

Chạy (trên máy chủ, nơi có state/golden/):
    venv/bin/python image_eval.py state/golden/v0/samples.jsonl tests/golden/image_labels_v0.jsonl
"""
import argparse
import collections
import json
import sys
from pathlib import Path

import role


def system_kept(a: dict) -> bool:
    """Engine có GIỮ tấm này làm ảnh dùng được không — đúng điều kiện lọc đầu
    của `schema.count_image_use_ok` (một công thức, không đoán lại lần thứ hai)."""
    return bool(a.get("dung")) and a.get("lien_quan") is not False and not role.face_no_clear_ai(a)


def drop_reason(a: dict) -> str:
    """Tầng nào khiến engine bỏ tấm này, đọc từ khoá có cấu trúc trước, `ghi_chu`
    sau. Chỉ để chia bảng đo — bản ghi quyết định thật là việc của LOW-225."""
    if system_kept(a):
        return "kept"
    if a.get("lien_quan") is False:
        return "capture_quality" if a.get("chup_nguon") else "vision_not_relevant"
    if role.face_no_clear_ai(a):
        return "unnamed_face"
    notes = " ".join(a.get("ghi_chu") or [])
    if "ảnh khái niệm" in notes:
        return "concept_gate"
    if a.get("lien_quan") is None:
        return "not_seen"
    return "no_use_slot"


def source_of(a: dict) -> str:
    """Nguồn ứng viên, gộp hai cách viết cũ của cùng một nguồn."""
    tu = a.get("tu") or "?"
    return "báo khác" if tu in ("bao khac", "báo khác") else tu


def read_jsonl(path) -> list:
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            out.append(json.loads(line))
    return out


def evaluate(samples: list, labels: list) -> dict:
    """Ghép nhãn với mẫu theo `id`, trả bảng đếm. Mẫu chưa có nhãn (hoặc nhãn
    `usable` không phải yes/no) không tính — in riêng để biết còn thiếu bao nhiêu."""
    by_id = {s["id"]: s for s in samples}
    total = collections.Counter()
    by_source = collections.defaultdict(collections.Counter)
    by_reason = collections.defaultdict(collections.Counter)
    wrongly_dropped, junk_kept, unlabeled = [], [], 0
    labeled_ids = set()
    for lab in labels:
        s = by_id.get(lab.get("id"))
        usable = lab.get("usable")
        if s is None or usable not in ("yes", "no"):
            continue
        labeled_ids.add(s["id"])
        kept = system_kept(s["image"])
        src, why = source_of(s["image"]), drop_reason(s["image"])
        key = ("yes" if usable == "yes" else "no") + ("_kept" if kept else "_dropped")
        for c in (total, by_source[src], by_reason[why]):
            c[key] += 1
        if usable == "yes" and not kept:
            wrongly_dropped.append((s["id"], src, why, lab.get("note", "")))
        elif usable == "no" and kept:
            junk_kept.append((s["id"], src, lab.get("defect", ""), lab.get("note", "")))
    unlabeled = len([s for s in samples if s["id"] not in labeled_ids])
    return {"total": total, "by_source": by_source, "by_reason": by_reason,
            "wrongly_dropped": wrongly_dropped, "junk_kept": junk_kept, "unlabeled": unlabeled}


def _rates(c: collections.Counter) -> tuple:
    yes = c["yes_kept"] + c["yes_dropped"]
    no = c["no_kept"] + c["no_dropped"]
    wrong_drop = c["yes_dropped"] / yes if yes else 0.0
    junk_pass = c["no_kept"] / no if no else 0.0
    return yes, no, wrong_drop, junk_pass


def format_report(r: dict) -> str:
    lines = []
    yes, no, wd, jp = _rates(r["total"])
    lines.append(f"Nhãn: {yes + no} (dùng được {yes}, không dùng được {no}); chưa nhãn: {r['unlabeled']}")
    lines.append(f"LOẠI OAN: {r['total']['yes_dropped']}/{yes} = {wd:.0%}   "
                 f"LỌT RÁC: {r['total']['no_kept']}/{no} = {jp:.0%}")
    for title, table in (("Theo nguồn", r["by_source"]), ("Theo tầng bỏ ảnh", r["by_reason"])):
        lines.append("")
        lines.append(f"{title}:  tên | dùng được (giữ/bỏ) | không dùng được (giữ/bỏ) | loại oan | lọt rác")
        for name, c in sorted(table.items(), key=lambda kv: -sum(kv[1].values())):
            y, n, wd_, jp_ = _rates(c)
            lines.append(f"  {name:22} | {c['yes_kept']:3}/{c['yes_dropped']:<3} | "
                         f"{c['no_kept']:3}/{c['no_dropped']:<3} | {wd_:4.0%} | {jp_:4.0%}")
    lines.append("")
    lines.append(f"Loại oan ({len(r['wrongly_dropped'])}):")
    lines += [f"  {i} [{src}/{why}] {note}" for i, src, why, note in r["wrongly_dropped"]]
    lines.append(f"Lọt rác ({len(r['junk_kept'])}):")
    lines += [f"  {i} [{src}/{defect}] {note}" for i, src, defect, note in r["junk_kept"]]
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("samples", help="samples.jsonl do image_golden_sample.py ghi")
    ap.add_argument("labels", help="tệp nhãn JSONL (id, usable, relevant, defect, subject, ...)")
    args = ap.parse_args(argv)
    print(format_report(evaluate(read_jsonl(args.samples), read_jsonl(args.labels))))
    return 0


if __name__ == "__main__":
    sys.exit(main())
