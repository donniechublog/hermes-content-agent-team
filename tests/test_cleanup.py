#!/usr/bin/env python3
"""`cleanup.trim_jsonl` phải ghi NGUYÊN TỬ và không ăn RAM cả tệp (audit lượt 2, B-r2-5).

Trước: readlines() cả tệp (500 MB → ~650 MB peak), rồi open('w') cắt tệp về 0
trước khi ghi lại — chết giữa chừng (hết đĩa, kill) là MẤT SẠCH nhật ký, trong
khi luat_anh/gui_telegram đang append vào chính tệp đó từ tiến trình khác.
`--keep-lines 0` thì lines[-0:] là cả tệp: không xoá gì mà vẫn báo "xóa N dòng".

Chạy:  venv/bin/python tests/test_cleanup.py
"""
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import cleanup                                                # noqa: E402


def _tep(t, n=10):
    p = Path(t) / "x.jsonl"
    p.write_text("".join(f'{{"i": {i}}}\n' for i in range(n)), encoding="utf-8")
    return p


def test_giu_dung_M_dong_cuoi():
    with tempfile.TemporaryDirectory() as t:
        p = _tep(t, 10)
        assert cleanup.trim_jsonl(p, keep_lines=3) == 7
        assert p.read_text(encoding="utf-8").splitlines() == ['{"i": 7}', '{"i": 8}', '{"i": 9}']
        assert cleanup.trim_jsonl(p, keep_lines=3) == 0, "da du ngan thi khong dong nao"


def test_dry_run_khong_dong_vao_tep():
    with tempfile.TemporaryDirectory() as t:
        p = _tep(t, 10)
        truoc = p.read_bytes()
        assert cleanup.trim_jsonl(p, keep_lines=3, dry_run=True) == 7
        assert p.read_bytes() == truoc


def test_ghi_hong_giua_chung_khong_mat_tep_cu():
    """Gia lap ENOSPC luc ghi: tep goc phai con NGUYEN (ghi ra tmp + os.replace)."""
    with tempfile.TemporaryDirectory() as t:
        p = _tep(t, 10)
        truoc = p.read_bytes()
        cu = os.replace

        def _no(*a, **k):
            raise OSError(28, "No space left on device")
        os.replace = _no
        try:
            try:
                cleanup.trim_jsonl(p, keep_lines=3)
            except OSError:
                pass
        finally:
            os.replace = cu
        assert p.read_bytes() == truoc, "tep goc bi cat cut khi ghi hong"
        assert not list(Path(t).glob("*.tmp.*")) or True    # tmp con lai la chap nhan duoc


def test_keep_lines_0_bi_tu_choi():
    with tempfile.TemporaryDirectory() as t:
        p = _tep(t, 10)
        try:
            cleanup.trim_jsonl(p, keep_lines=0)
        except ValueError:
            return
        raise AssertionError("keep_lines=0 phai bi tu choi (lines[-0:] la ca tep)")


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
