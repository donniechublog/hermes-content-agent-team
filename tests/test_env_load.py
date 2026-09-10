#!/usr/bin/env python3
"""Vài hàm nhỏ của env_load thêm ở đợt 6 (audit lượt 2): so_luong, ghi_json.

Chạy:  venv/bin/python tests/test_env_load.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import env_load                                               # noqa: E402


def _voi_env(ten, gia_tri, ham):
    cu = os.environ.get(ten)
    if gia_tri is None:
        os.environ.pop(ten, None)
    else:
        os.environ[ten] = gia_tri
    try:
        return ham()
    finally:
        if cu is None:
            os.environ.pop(ten, None)
        else:
            os.environ[ten] = cu


def test_so_luong_chi_ha_khong_nang():
    """B-r2-6: CT_WORKERS la TRAN chung; khong dat thi giu mac dinh cua cho goi."""
    assert _voi_env("CT_WORKERS", None, lambda: env_load.so_luong(6)) == 6
    assert _voi_env("CT_WORKERS", "2", lambda: env_load.so_luong(6)) == 2
    assert _voi_env("CT_WORKERS", "16", lambda: env_load.so_luong(6)) == 6, "khong nang qua mac dinh"
    assert _voi_env("CT_WORKERS", "0", lambda: env_load.so_luong(6)) == 6
    assert _voi_env("CT_WORKERS", "xyz", lambda: env_load.so_luong(6)) == 6, "gia tri rac -> mac dinh"


def test_ghi_json_hong_giua_chung_khong_de_tmp_va_giu_tep_cu():
    """ADF-r2-11: mot ban ghi nguyen tu cho 4 cho tung tu viet — phai don tmp
    khi hong va khong cham tep cu."""
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "a" / "b.json"
        env_load.ghi_json(p, {"x": 1})                    # tu mkdir
        assert json.loads(p.read_text(encoding="utf-8")) == {"x": 1}
        truoc = p.read_bytes()
        import os as _os
        cu = _os.replace

        def _no(*a, **k):
            raise OSError(28, "ENOSPC")
        _os.replace = _no
        try:
            try:
                env_load.ghi_json(p, {"z": 2})
            except OSError:
                pass
        finally:
            _os.replace = cu
        assert not list((Path(t) / "a").glob("*.tmp.*")), "tmp con sot lai sau khi hong"
        assert p.read_bytes() == truoc, "tep cu bi dong vao khi ghi hong"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
