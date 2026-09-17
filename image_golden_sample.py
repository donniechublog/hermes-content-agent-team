#!/usr/bin/env python3
"""Chọn mẫu BỘ NHÃN CHUẨN ảnh từ các lần chuẩn bị thật (LOW-224, 17/09/2026).

Đọc mọi `state/<brand>/prepare/<draft>/manifest.json`, chọn mẫu phân tầng (seed cố
định), rồi CHỤP RIÊNG từng ảnh ra `state/golden/<version>/` — ảnh thu nhỏ + md5
ảnh gốc + ngữ cảnh tin. Phải chụp riêng: chạy lại một draft (`*_prepare.py`,
`find_more_images.py`) ghi đè `original/A*.png` bằng ảnh KHÁC, nên trỏ thẳng vào `original/`
thì nhãn sẽ lệch ảnh mà không ai biết.

Phân tầng: giữ trọn các draft chỉ định (`--must`), phần còn lại chia ~1/3 ảnh
engine đang giữ, ~2/3 ảnh đang bỏ (đo LOẠI OAN là mục tiêu chính), mỗi nguồn `source`
tối thiểu một suất, mỗi draft tối đa vài tấm để mẫu trải rộng.

Chạy trên máy chủ:
    venv/bin/python image_golden_sample.py --version v0 --size 300 \\
        --must anthropic-ky-thoa-thuan-trung-tam-du-lie-dre-dcgr ...
"""
import argparse
import collections
import hashlib
import json
import random
import sys
from pathlib import Path

from PIL import Image

import schema
import state_paths
from image_eval import source_of, system_kept

ROOT = Path(__file__).resolve().parent
THUMB_MAX = 512
LEAD_CHARS = 700
# Khoá ảnh chép sang mẫu: đủ để người gán nhãn hiểu ảnh đến từ đâu, và đủ để
# image_eval dựng lại quyết định của engine (system_kept / drop_reason).
IMAGE_KEYS = ("id", "source", "domain", "url", "page_url", "alt", "description", "relevant", "uses", "notes",
              "cluttered", "has_keywords", "w", "h", "faces", "concept", "brand_match", "capture_source",
              "from_find_more", "commons", "ranking", "entity", "page_title")


def load_candidates(state_root: Path) -> list:
    """Mọi ứng viên còn tệp gốc trên đĩa, kèm ngữ cảnh tin của draft chứa nó."""
    out = []
    for manifest in sorted(Path(state_root).glob(f"*/{state_paths.PREPARE_DIR}/*/{state_paths.MANIFEST_FILE}")):
        try:
            d = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        # Ban 0/1 (khoa Viet) nang len ban 2 qua MOT cho doc (LOW-227).
        d = schema.read_manifest(d) if isinstance(d, dict) else None
        if d is None:
            continue
        brand = manifest.parents[2].name
        story = {"brand": brand, "draft_id": d.get("draft_id") or manifest.parent.name,
                 "title": d.get("title", ""), "title_en": d.get("title_en", ""),
                 "category": d.get("category", ""), "link": d.get("link", ""),
                 "summary": d.get("summary", ""),
                 "lead": ((d.get("material") or {}).get("lead_paragraph") or "")[:LEAD_CHARS]}
        for a in d.get("images") or []:
            goc = Path(a.get("original_path") or "")
            if not a.get("id") or not goc.is_file():
                continue
            out.append({"id": f"{brand}/{story['draft_id']}/{a['id']}", "story": story,
                        "image": {k: a[k] for k in IMAGE_KEYS if k in a}, "goc": str(goc)})
    return out


def stratified_sample(cands: list, size: int, must_drafts=(), seed: int = 17,
                      kept_share: float = 1 / 3, per_draft_cap: int = 4) -> list:
    """Chọn `size` ứng viên, tất định theo `seed`. Trọn các draft `must_drafts`
    trước; phần còn lại chia giữ/bỏ theo `kept_share`, rải đều theo nguồn."""
    rng = random.Random(seed)
    cands = sorted(cands, key=lambda c: c["id"])
    must = [c for c in cands if c["story"]["draft_id"] in set(must_drafts)]
    rest = [c for c in cands if c["story"]["draft_id"] not in set(must_drafts)]
    left = max(0, size - len(must))
    groups = {True: [c for c in rest if system_kept(c["image"])],
              False: [c for c in rest if not system_kept(c["image"])]}
    quota = {True: round(left * kept_share)}
    quota[False] = left - quota[True]
    picked = list(must)
    per_draft = collections.Counter(c["story"]["draft_id"] for c in must)
    for kept, pool in groups.items():
        by_src = collections.defaultdict(list)
        for c in pool:
            by_src[source_of(c["image"])].append(c)
        for lst in by_src.values():
            rng.shuffle(lst)
        chosen = 0
        # Vòng tròn qua các nguồn: nguồn nhỏ không bị nguồn lớn nuốt suất.
        while chosen < quota[kept] and any(by_src.values()):
            for src in sorted(by_src):
                if chosen >= quota[kept]:
                    break
                lst = by_src[src]
                while lst:
                    c = lst.pop()
                    if per_draft[c["story"]["draft_id"]] < per_draft_cap:
                        picked.append(c)
                        per_draft[c["story"]["draft_id"]] += 1
                        chosen += 1
                        break
            by_src = {k: v for k, v in by_src.items() if v}
    return picked


def write_snapshot(samples: list, out_dir: Path) -> Path:
    """Ảnh thu nhỏ `img/<n>.jpg` + `samples.jsonl` (md5 là của ảnh GỐC lúc chụp)."""
    img_dir = out_dir / "img"
    img_dir.mkdir(parents=True, exist_ok=True)
    rows = []
    for n, s in enumerate(samples, 1):
        data = Path(s["goc"]).read_bytes()
        im = Image.open(s["goc"])
        im.load()
        im = im.convert("RGB")
        im.thumbnail((THUMB_MAX, THUMB_MAX))
        thumb = img_dir / f"{n:03d}.jpg"
        im.save(thumb, "JPEG", quality=85)
        rows.append({"n": n, "id": s["id"], "md5": hashlib.md5(data).hexdigest(),
                     "thumb": f"img/{thumb.name}", "story": s["story"], "image": s["image"]})
    path = out_dir / "samples.jsonl"
    path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    return path


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--version", required=True)
    ap.add_argument("--size", type=int, default=300)
    ap.add_argument("--seed", type=int, default=17)
    ap.add_argument("--must", nargs="*", default=[])
    ap.add_argument("--state", default=str(ROOT / "state"))
    args = ap.parse_args(argv)
    out_dir = Path(args.state) / "golden" / args.version
    if (out_dir / "samples.jsonl").exists():
        print(f"[golden] {out_dir} đã có samples.jsonl — không ghi đè bộ nhãn cũ", file=sys.stderr)
        return 1
    cands = load_candidates(Path(args.state))
    samples = stratified_sample(cands, args.size, args.must, args.seed)
    path = write_snapshot(samples, out_dir)
    kept = sum(system_kept(s["image"]) for s in samples)
    print(f"[golden] {len(samples)} mẫu / {len(cands)} ứng viên (engine giữ {kept}, bỏ {len(samples) - kept}) -> {path}")
    for src, k in collections.Counter(source_of(s["image"]) for s in samples).most_common():
        print(f"  {src}: {k}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
