#!/usr/bin/env python3
"""Dọn dẹp tệp dữ liệu cũ và cắt ngắn nhật ký append-only jsonl.

Cách dùng:
  python cleanup.py --age-days 30 --keep-lines 5000 [--dry-run]

Mục tiêu:
- Xóa file ứng cử <vai>_candidates_*.json cũ hơn N ngày
- Cắt ngắn jsonl append-only, giữ M dòng gần nhất
- Xóa manifest/bat_buoc cũ nếu nhiều version

Tệp không xóa:
- kanban.db (cơ sở dữ liệu Kanban)
- state.db (nếu có)
- used_images.jsonl (tiếp tục dùng, chỉ cắt ngắn)
"""
import argparse
import io
import sys
from datetime import datetime, timedelta
from pathlib import Path

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", newline="")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", newline="")

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import env_load  # noqa: E402
import state_paths  # noqa: E402


def get_state_dir() -> Path:
    """Lấy thư mục trạng thái."""
    return env_load.state_dir()


def cleanup_old_candidates(state_dir: Path, age_days: int = 30, dry_run: bool = False) -> int:
    """Xóa file ứng cử cũ hơn age_days."""
    removed = 0
    cutoff = datetime.now() - timedelta(days=age_days)

    for candidate_file in state_dir.glob("*_candidates_*.json"):
        mtime = datetime.fromtimestamp(candidate_file.stat().st_mtime)
        if mtime < cutoff:
            if not dry_run:
                candidate_file.unlink()
            print(f"{'[DRY] ' if dry_run else ''}Xóa ứng cử cũ: {candidate_file.name} ({mtime.date()})")
            removed += 1

    return removed


def trim_jsonl(file_path: Path, keep_lines: int = 5000, dry_run: bool = False) -> int:
    """Cắt ngắn tệp jsonl, giữ keep_lines dòng gần nhất."""
    if not file_path.exists():
        return 0
    if keep_lines < 1:
        # lines[-0:] la CA tep: khong xoa gi ma van bao "xoa N dong" (B-r2-5).
        raise ValueError(f"keep_lines phai >= 1, nhan {keep_lines}")

    # deque(maxlen) chi giu M dong cuoi trong RAM — readlines() nuot ca tep
    # (500 MB jsonl tren server 2 vCPU la ~650 MB peak, do 1,3x).
    import collections
    import os
    try:
        with open(file_path, "r", encoding="utf-8") as fh:
            tong = 0
            cuoi = collections.deque(maxlen=keep_lines)
            for dong in fh:
                tong += 1
                cuoi.append(dong)
    except (OSError, UnicodeDecodeError) as e:
        print(f"[LỖI] Không đọc {file_path.name}: {e}", file=sys.stderr)
        return 0

    if tong <= keep_lines:
        return 0

    removed = tong - keep_lines
    if not dry_run:
        # Ghi ra tep tam CUNG thu muc roi os.replace: open('w') cat tep ve 0
        # truoc khi ghi lai, chet giua chung (het dia, kill) la MAT SACH nhat ky
        # — trong khi image_rules/send_telegram dang append vao chinh tep nay tu
        # tien trinh khac. Cung cach env_load.ghi_json da lam (B-r2-5).
        tam = file_path.with_name(f"{file_path.name}.tmp.{os.getpid()}")
        with open(tam, "w", encoding="utf-8") as fh:
            fh.writelines(cuoi)
        os.replace(tam, file_path)

    print(f"{'[DRY] ' if dry_run else ''}Cắt ngắn {file_path.name}: xóa {removed} dòng cũ")
    return removed


def cleanup_append_only_logs(state_dir: Path, keep_lines: int = 5000, dry_run: bool = False) -> int:
    """Cắt ngắn các tệp jsonl append-only."""
    trimmed = 0

    # telegram_sent/<vai>.jsonl
    telegram_sent = state_dir / "telegram_sent"
    if telegram_sent.exists():
        for vai_log in telegram_sent.glob("*.jsonl"):
            trimmed += trim_jsonl(vai_log, keep_lines, dry_run)

    # used_images.jsonl, used_edu_themes.jsonl
    for name in (state_paths.USED_IMAGES_FILE, state_paths.USED_EDU_THEMES_FILE):
        trimmed += trim_jsonl(state_dir / name, keep_lines, dry_run)

    return trimmed


def cleanup_old_manifests(state_dir: Path, age_days: int = 30, dry_run: bool = False) -> int:
    """Xóa các file manifest cũ, giữ lại bản mới nhất."""
    removed = 0
    cutoff = datetime.now() - timedelta(days=age_days)

    # Nhóm manifest theo vai
    manifest_groups = {}
    for manifest_file in state_dir.glob("*_manifest*.json"):
        vai = manifest_file.name.split("_")[0]
        if vai not in manifest_groups:
            manifest_groups[vai] = []
        manifest_groups[vai].append(manifest_file)

    # Xóa những cái cũ hơn age_days
    for vai, files in manifest_groups.items():
        for mf in files:
            mtime = datetime.fromtimestamp(mf.stat().st_mtime)
            if mtime < cutoff:
                if not dry_run:
                    mf.unlink()
                print(f"{'[DRY] ' if dry_run else ''}Xóa manifest cũ: {mf.name} ({mtime.date()})")
                removed += 1

    return removed


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--age-days", type=int, default=30,
                    help="Xóa file cũ hơn N ngày (mặc định: 30)")
    ap.add_argument("--keep-lines", type=int, default=5000,
                    help="Giữ N dòng gần nhất trong jsonl (mặc định: 5000)")
    ap.add_argument("--dry-run", action="store_true",
                    help="Chỉ in những gì sẽ làm, không thực hiện")
    ap.add_argument("--state-dir", type=Path, help="Thư mục state (mặc định: env_load.state_dir())")
    a = ap.parse_args()

    state_dir = a.state_dir or get_state_dir()
    if not state_dir.exists():
        print(f"[LỖI] Thư mục trạng thái không tồn tại: {state_dir}", file=sys.stderr)
        return 1

    print(f"Dọn dẹp {state_dir}")
    print()

    if a.dry_run:
        print("[DRY-RUN MODE]")
        print()

    total = 0

    print(f"Xóa file ứng cử cũ hơn {a.age_days} ngày:")
    removed_candidates = cleanup_old_candidates(state_dir, a.age_days, a.dry_run)
    total += removed_candidates
    print(f"→ Đã xóa {removed_candidates} file")
    print()

    print(f"Cắt ngắn nhật ký append-only (giữ {a.keep_lines} dòng):")
    trimmed = cleanup_append_only_logs(state_dir, a.keep_lines, a.dry_run)
    total += trimmed
    print(f"→ Đã cắt ngắn {trimmed} tệp")
    print()

    print(f"Xóa manifest cũ hơn {a.age_days} ngày:")
    removed_manifest = cleanup_old_manifests(state_dir, a.age_days, a.dry_run)
    total += removed_manifest
    print(f"→ Đã xóa {removed_manifest} file")
    print()

    print(f"Tổng cộng: {total} mục bị ảnh hưởng")

    if a.dry_run:
        print()
        print("Để thực hiện dọn dẹp thực sự, chạy lại mà không --dry-run")

    return 0


if __name__ == "__main__":
    sys.exit(main())
