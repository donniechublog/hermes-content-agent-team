#!/usr/bin/env python3
"""Do dung chung cua cac tep test — KHONG phai mot tep test (run.sh chi chay
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
    tep: rc=1 nhung khong dong "N/M test qua", cac test sau khong chay, run.sh
    chi hien "HONG (ma 1)". Gap 3 lan khi mutation va 1 lan that o HEAD. Day la
    dieu lượt 1 xep "lam ngay" ma chua lam.

    Dung:  if __name__ == "__main__": chay_tat_ca(globals())
    - test_* chay theo thu tu dinh nghia; AssertionError -> FAIL; loi khac -> ERR
      kem ten loi (van dem la hong, van chay tiep);
    - luon in "N/M test qua" va thoat 1 neu co hong, de run.sh doc duoc."""
    import traceback
    import role
    ham = [v for k, v in list(ns.items()) if k.startswith("test_") and callable(v)]
    hong = 0
    for h in ham:
        try:
            # Mac dinh MOI test (LOW-182, 16/09/2026): `role.active_rules()` doi
            # `set_active_role()` da goi trong tien trinh. "ethan" chi la mot lua
            # chon hop le trung tinh — ba module luat giong het nhau tai thoi
            # diem tach, nen khong anh huong ket qua; test nao can DUNG vai cu
            # the (vd hanh vi rieng cua dre_submit) thi tu goi lai set_active_role
            # trong than test cua no.
            role.set_active_role("ethan")
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

    Truoc 06/09/2026 bon test gan thang `la._used_images_log = lambda: d/"s.jsonl"`
    va khong bao gio tra lai. Ca suite chay trong MOT tien trinh theo thu tu
    dinh nghia, nen tu test dau tien tro di `_used_images_log()` tro toi mot
    TemporaryDirectory DA BI XOA: `check_not_reused` thay tep khong ton tai va tra
    ve ([], []) VO DIEU KIEN. Cong "khong dung lai anh trong 14 ngay" chet im
    trong moi test sau do — ke ca test_kite_khong_ep_dung_anh_chua_nhin, von di
    qua dung cong do o kite_submit.py:88. Test xanh ma cong khong chay.

    Emoji cung mot bai hoc, xem `lay_emoji` cua teaser_assemble.assemble.
    """
    # LOW-182 (16/09/2026): `_used_images_log` song o image_provenance.py, dung
    # CHUNG ca ba module luat vai (ho goi QUA TEN MODULE, khong `from ... import`,
    # dung de patch dung MOT cho nay la ca ba deu thay).
    import image_provenance as la
    cu = la._used_images_log
    d = Path(tmp)
    # Ten tep giu nguyen "s.jsonl" cua ban cu: co test doc thang ten do.
    la._used_images_log = lambda: d / "s.jsonl"
    try:
        yield d
    finally:
        la._used_images_log = cu


@contextlib.contextmanager
def bat_buoc_tam(tmp, **danh_sach):
    """Tro danh sach BAT BUOC vao thu muc tam VA TRA LAI khi ra khoi khoi.

    `danh_sach`: vai -> dict muc, vd `bat_buoc_tam(t, scout={"k1": {...}})`.
    Cung mot bai hoc voi `so_tam`: `required.file()` doc `env_load.state_dir()`,
    tuc state THAT cua brand dang chay — mot test quen tra lai la moi test sau
    do doc nham danh sach cua may that.
    """
    import json

    import required as bb
    cu = bb.file
    d = Path(tmp)
    for vai, muc in danh_sach.items():
        (d / f"required_{vai}.json").write_text(json.dumps(muc, ensure_ascii=False),
                                                encoding="utf-8")
    bb.file = lambda vai: d / f"required_{vai}.json"
    try:
        yield d
    finally:
        bb.file = cu


@contextlib.contextmanager
def block_network():
    """Chan MOI ket noi mang trong khoi, ghi lai tung lan thu (22/09/2026).

    Cac test "khong mang" cua `prepare_article()` thay tung pha nang bang stub
    theo mot danh sach ten. Pha moi (hay pha bi quen) thi khong ai stub: no chay
    mang THAT, loi mang bi chinh pha do nuot, test van xanh — chi cham di. Da
    gap ba lan: `_round_capture_source` (13/09), `_round_entity` (13/09, 6 phut
    34), va lai `_round_entity` trong test_round_brand_always_run (22/09: Wikipedia
    + vision 9router, qua 180s tren may chu, keo chet ca `tests/run.sh`).

    Chan o muc socket (getaddrinfo + connect) nen bat duoc moi thu vien (urllib,
    httpx, requests), ke ca localhost (9router). Raise OSError de pha lot luoi
    tra loi ngay thay vi treo; test phai tu `assert not tried` de lot luoi la DO,
    khong phai xanh nho pha do nuot loi.

    Dung:
        with block_network() as tried:
            ...
        assert not tried, f"goi mang that: {tried}"
    """
    import socket

    tried = []
    old_getaddrinfo = socket.getaddrinfo
    old_connect = socket.socket.connect
    old_connect_ex = socket.socket.connect_ex

    def _refuse(target):
        tried.append(target)
        raise OSError(f"tests.tam.block_network: test offline goi mang that ({target})")

    socket.getaddrinfo = lambda host, *a, **k: _refuse(host)
    socket.socket.connect = lambda self, address: _refuse(address)
    socket.socket.connect_ex = lambda self, address: _refuse(address)
    try:
        yield tried
    finally:
        socket.getaddrinfo = old_getaddrinfo
        socket.socket.connect = old_connect
        socket.socket.connect_ex = old_connect_ex
