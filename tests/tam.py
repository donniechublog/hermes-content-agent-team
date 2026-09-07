#!/usr/bin/env python3
"""Do dung chung cua cac tep test — KHONG phai mot tep test (chay.sh chi chay
`test_*.py`).

Vi sao co tep nay: `_so_tam` da duoc chep sang tep test thu hai (07/09/2026).
Bai hoc cua chinh no la mot ban sua mot cho ma quen cho kia; de hai ban song
song la dinh dung cai bay do.
"""
import contextlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@contextlib.contextmanager
def so_tam(tmp):
    """Tro so "anh da dung" vao thu muc tam VA TRA LAI khi ra khoi khoi.

    Truoc 06/09/2026 bon test gan thang `la._so_da_dung = lambda: d/"s.jsonl"`
    va khong bao gio tra lai. Ca suite chay trong MOT tien trinh theo thu tu
    dinh nghia, nen tu test dau tien tro di `_so_da_dung()` tro toi mot
    TemporaryDirectory DA BI XOA: `kiem_da_dung` thay tep khong ton tai va tra
    ve ([], []) VO DIEU KIEN. Cong "khong dung lai anh trong 14 ngay" chet im
    trong moi test sau do — ke ca test_kite_khong_ep_dung_anh_chua_nhin, von di
    qua dung cong do o kite_nop.py:88. Test xanh ma cong khong chay.

    Emoji cung mot bai hoc, xem `lay_emoji` cua teaser_assemble.assemble.
    """
    import luat_anh as la
    cu = la._so_da_dung
    d = Path(tmp)
    # Ten tep giu nguyen "s.jsonl" cua ban cu: co test doc thang ten do.
    la._so_da_dung = lambda: d / "s.jsonl"
    try:
        yield d
    finally:
        la._so_da_dung = cu


@contextlib.contextmanager
def bat_buoc_tam(tmp, **danh_sach):
    """Tro danh sach BAT BUOC vao thu muc tam VA TRA LAI khi ra khoi khoi.

    `danh_sach`: vai -> dict muc, vd `bat_buoc_tam(t, scout={"k1": {...}})`.
    Cung mot bai hoc voi `so_tam`: `bat_buoc.tep()` doc `env_load.state_dir()`,
    tuc state THAT cua brand dang chay — mot test quen tra lai la moi test sau
    do doc nham danh sach cua may that.
    """
    import json

    import bat_buoc as bb
    cu = bb.tep
    d = Path(tmp)
    for vai, muc in danh_sach.items():
        (d / f"bat_buoc_{vai}.json").write_text(json.dumps(muc, ensure_ascii=False),
                                                encoding="utf-8")
    bb.tep = lambda vai: d / f"bat_buoc_{vai}.json"
    try:
        yield d
    finally:
        bb.tep = cu
