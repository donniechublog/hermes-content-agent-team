#!/usr/bin/env python3
"""BẢN GHI QUYẾT ĐỊNH cho mọi ứng viên ảnh (LOW-225, Ông Chủ chốt 17/09/2026).

Trước ticket này ảnh tốt bị bỏ là VÔ HÌNH: pha tải bỏ ứng viên ở hơn chục chỗ
`continue` (năm chỗ không in cả dòng stderr), vision + ba nhánh regex lật
`lien_quan` mà không ghi nhánh nào đã lật, và `ghi_chu` là văn bản tự do. Ảnh xấu
lọt thì Ông Chủ thấy trên Telegram; ảnh tốt bị bỏ thì không ai thấy — nên cổng
chỉ có chiều siết, không bao giờ nới đúng lúc.

Module này CHỈ GHI, không quyết định gì — `dung`, `lien_quan`, `so_dung_duoc`
giữ nguyên từng bit (test so đầu ra bật/tắt bản ghi).

  - `note(a, stage, outcome, rule, evidence)`: nối một quyết định vào
    `a["decisions"]` của ảnh ĐÃ tải (đi vào xong.json cùng ảnh).
  - `drop_candidate(wd, c, stage, rule, evidence, im)`: ứng viên bị bỏ TRƯỚC khi
    thành ảnh — ghi một dòng `wd/dropped/dropped.jsonl` + ảnh thu nhỏ (nếu đã
    mở được ảnh), để bộ nhãn chuẩn (LOW-224) gán nhãn được về sau.
  - `collect(wd, since)`: gom mọi dòng bỏ dưới `wd` (mọi vòng con: commons/,
    them_N/...) ghi từ `since` trở đi — manifest dùng làm `dropped`.
"""
import json
import time
import uuid
from pathlib import Path

DROPPED_DIR = "dropped"
DROPPED_FILE = "dropped.jsonl"
THUMB_MAX = 512
OUTCOMES = ("keep", "drop", "demote", "flag")


def note(a: dict, stage: str, outcome: str, rule: str = "", evidence: str = "") -> None:
    if outcome not in OUTCOMES:
        raise ValueError(f"outcome {outcome!r} không thuộc {OUTCOMES}")
    a.setdefault("decisions", []).append(
        {"stage": stage, "outcome": outcome, "rule": rule, "evidence": str(evidence)[:300]})


def drop_candidate(wd: Path, c: dict, stage: str, rule: str = "", evidence: str = "", im=None) -> None:
    """Không bao giờ ném: một bản ghi hỏng không được làm hỏng pha tải."""
    try:
        d = Path(wd) / DROPPED_DIR
        d.mkdir(parents=True, exist_ok=True)
        thumb = ""
        if im is not None:
            t = im.copy()
            t.thumbnail((THUMB_MAX, THUMB_MAX))
            name = f"{uuid.uuid4().hex[:12]}.jpg"
            t.convert("RGB").save(d / name, "JPEG", quality=85)
            thumb = str(d / name)
        row = {"ts": time.time(), "stage": stage, "outcome": "drop", "rule": rule,
               "evidence": str(evidence)[:300], "url": c.get("anh", ""), "trang": c.get("trang", ""),
               "alt": (c.get("alt") or c.get("alt_chup") or "")[:200], "tu": c.get("tu", ""),
               "thumb": thumb}
        with open(d / DROPPED_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    except Exception as e:                                   # noqa: BLE001
        import sys
        print(f"[decision_log] khong ghi duoc ban ghi bo anh: {type(e).__name__}: {e!r}", file=sys.stderr)


def collect(wd: Path, since: float = 0.0) -> list:
    out = []
    for f in sorted(Path(wd).glob(f"**/{DROPPED_DIR}/{DROPPED_FILE}")):
        try:
            lines = f.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for line in lines:
            try:
                row = json.loads(line)
            except ValueError:
                continue
            if row.get("ts", 0) >= since:
                out.append(row)
    return sorted(out, key=lambda r: r.get("ts", 0))
