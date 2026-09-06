#!/usr/bin/env python3
"""Kiem tra env_load.album_phu — chan hoi bug that: glob "_[0-9].png" chi khop
mot chu so nen bo sot slide thu 10 tro len, lam mat slide cuoi khoi album dang
kenh (audit 06/09/2026, xem draft_write.py/dre_nop.py/kite_nop.py).

Khong dung pytest (chua co trong venv). Chay truc tiep:
    venv/bin/python tests/test_album_phu.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import env_load  # noqa: E402


def _tao(d: Path, ten: list) -> None:
    for t in ten:
        (d / t).write_bytes(b"")


def test_du_10_slide():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        _tao(d, [f"bai1_{i}.png" for i in range(2, 11)])
        ra = env_load.album_phu("bai1", d)
        assert [p.name for p in ra] == [f"bai1_{i}.png" for i in range(2, 11)], ra
        assert len(ra) == 9, f"phai co du 9 anh phu (_2.._10), duoc {len(ra)}"


def test_khong_lan_sang_draft_khac():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        _tao(d, ["bai1_2.png", "bai1_10.png", "bai12_2.png"])
        ra = [p.name for p in env_load.album_phu("bai1", d)]
        assert ra == ["bai1_2.png", "bai1_10.png"], ra


def test_bo_qua_ghep_va_khong_phai_so():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        _tao(d, ["bai1_2.png", "bai1_3.ghep.png", "bai1_x.png"])
        ra = [p.name for p in env_load.album_phu("bai1", d)]
        assert ra == ["bai1_2.png"], ra


def test_rong_khi_khong_co_anh_phu():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp)
        assert env_load.album_phu("bai1", d) == []


if __name__ == "__main__":
    ham = [v for k, v in list(globals().items()) if k.startswith("test_")]
    loi = 0
    for h in ham:
        try:
            h()
            print(f"OK   {h.__name__}")
        except AssertionError as e:
            loi += 1
            print(f"FAIL {h.__name__}: {e}")
    print(f"\n{len(ham) - loi}/{len(ham)} test qua")
    sys.exit(1 if loi else 0)
