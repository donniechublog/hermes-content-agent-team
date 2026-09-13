#!/usr/bin/env python3
"""`chuan_bi.tai_loc` không được nuốt lỗi tải im lặng (audit lượt 2, C-r2-2).

Trước: `_tai_bytes` → `except Exception: return None` không log, và `tai_va_loc`
coi `not data` là `continue`. Mất DNS/proxy thì 5 ứng viên hỏng ra 0 dòng
stderr, engine kết luận "tải được 0 ảnh" → so_dung_duoc=0 → tự chuyển Kite,
không dấu vết lỗi môi trường nào.

Chạy:  venv/bin/python tests/test_tai_loc_log.py
"""
import io
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import chuan_bi.download_filter as tl                                 # noqa: E402


def _bat_stderr(ham):
    cu, sys.stderr = sys.stderr, io.StringIO()
    try:
        kq = ham()
        return kq, sys.stderr.getvalue()
    finally:
        sys.stderr = cu


def test_tai_bytes_hong_mang_phai_noi_ra():
    kq, err = _bat_stderr(lambda: tl._download_bytes("http://khong-ton-tai.invalid/a.png"))
    assert kq is None
    assert "[tai]" in err and "khong-ton-tai.invalid" in err, repr(err)
    assert "Error" in err or "error" in err, "phai co ten loi (repr), khong chi None"


def test_tai_va_loc_tat_ca_hong_thi_co_dong_tong():
    """Khong chi tung URL: mot dong tong noi 'TAT CA khong tai duoc' de brief
    phan biet voi bai khong co anh."""
    cands = [{"anh": f"http://khong-ton-tai.invalid/{i}.png", "trang": "http://x.invalid/"}
             for i in range(3)]
    with tempfile.TemporaryDirectory() as t:
        (ra, err) = _bat_stderr(lambda: tl.download_and_filter(cands, Path(t)))
    assert ra == [], ra
    assert "3/3 ung vien KHONG tai duoc" in err and "TAT CA" in err, repr(err)


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
