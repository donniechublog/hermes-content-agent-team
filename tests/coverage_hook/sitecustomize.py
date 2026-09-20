"""Python tự nạp tệp này lúc khởi động khi thư mục này nằm trong PYTHONPATH (LOW-301).

Bật đo độ phủ trong MỌI tiến trình Python, kể cả tiến trình con do test sinh ra, khi CI
đặt COVERAGE_PROCESS_START (trỏ tới .coveragerc). Không có biến đó thì không làm gì. Không
được làm chết tiến trình đang chạy: thiếu hoặc hỏng coverage chỉ in một dòng cảnh báo.

Không phải test — tests/run.sh chỉ chạy `tests/test_*.py` ở thư mục ngoài cùng.
"""
import os
import sys

if os.environ.get("COVERAGE_PROCESS_START"):
    try:
        import coverage
        coverage.process_startup()
    except Exception as e:                                       # noqa: BLE001
        print(f"[coverage_hook] không bật được coverage: {type(e).__name__}: {e}", file=sys.stderr)
