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


def chay_tat_ca(ns: dict) -> None:
    """Runner chung cho moi tests/test_*.py (audit lượt 2, E-r2-2).

    Truoc day 35 tep chep cung mot khoi `except AssertionError` — tuc mot loi
    KHONG phai AssertionError (TypeError, KeyError, JSONDecodeError...) giet ca
    tep: rc=1 nhung khong dong "N/M test qua", cac test sau khong chay, chay.sh
    chi hien "HONG (ma 1)". Gap 3 lan khi mutation va 1 lan that o HEAD. Day la
    dieu lượt 1 xep "lam ngay" ma chua lam.

    Dung:  if __name__ == "__main__": chay_tat_ca(globals())
    - test_* chay theo thu tu dinh nghia; AssertionError -> FAIL; loi khac -> ERR
      kem ten loi (van dem la hong, van chay tiep);
    - luon in "N/M test qua" va thoat 1 neu co hong, de chay.sh doc duoc."""
    import traceback
    ham = [v for k, v in list(ns.items()) if k.startswith("test_") and callable(v)]
    hong = 0
    for h in ham:
        try:
            h()
            print(f"OK   {h.__name__}")
        except AssertionError as e:
            hong += 1
            print(f"FAIL {h.__name__}: {e}")
        except Exception as e:                               # noqa: BLE001
            hong += 1
            dong = traceback.extract_tb(e.__traceback__)[-1]
            print(f"ERR  {h.__name__}: {type(e).__name__}: {e} "
                  f"({Path(dong.filename).name}:{dong.lineno})")
    print(f"\n{len(ham) - hong}/{len(ham)} test qua")
    sys.exit(1 if hong else 0)


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
