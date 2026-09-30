#!/usr/bin/env python3
"""sync_hermes --ra-hermes ghi tep cron LIVE phai NGUYEN TU (B20).

Vi sao phai co test: `write_bytes` cat tep ve 0 byte roi moi ghi. `publish_due.sh`
chay MOI PHUT tu cron, nen co xac suat that no mo dung luc tep dang cut va chay
mot ban thieu dong. Cach chua la ghi ra tep tam cung thu muc roi `os.replace`,
va phai GIU quyen thuc thi (script cron mat +x thi cron im lang bo qua).

Chay:  venv/bin/python tests/test_sync_atomic_write.py
"""
import argparse
import os
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import sync_hermes as db  # noqa: E402
import tam  # noqa: E402


def test_write_atomic_keeps_exec_bit_and_leaves_no_temp():
    d = tam.temp_dir()
    p = d / "publish_due.sh"
    p.write_bytes(b"old\n")
    p.chmod(0o755)
    db.write_atomic(p, b"new\n")
    assert p.read_bytes() == b"new\n"
    assert stat.S_IMODE(p.stat().st_mode) == 0o755, oct(p.stat().st_mode)
    assert [x.name for x in d.iterdir()] == ["publish_due.sh"], list(d.iterdir())


def test_write_atomic_reader_never_sees_truncated_file():
    """Luc os.replace chay, tep dich con NGUYEN ban cu, ban moi da ghi du o tep tam."""
    d = tam.temp_dir()
    p = d / "x.sh"
    p.write_bytes(b"old-content\n")
    thay = os.replace
    thay_vet = {}

    def do_thay(src, dst):
        thay_vet["dich"] = Path(dst).read_bytes()
        thay_vet["tam"] = Path(src).read_bytes()
        thay(src, dst)
    db.os.replace = do_thay
    try:
        db.write_atomic(p, b"new-content\n")
    finally:
        db.os.replace = thay
    assert thay_vet == {"dich": b"old-content\n", "tam": b"new-content\n"}, thay_vet


def test_write_atomic_failure_keeps_old_file_and_cleans_temp():
    d = tam.temp_dir()
    p = d / "x.sh"
    p.write_bytes(b"old\n")
    thay = os.replace

    def hong(src, dst):
        raise OSError("dia day")
    db.os.replace = hong
    try:
        try:
            db.write_atomic(p, b"new\n")
        except OSError:
            pass
        else:
            raise AssertionError("phai nem loi")
    finally:
        db.os.replace = thay
    assert p.read_bytes() == b"old\n"
    assert [x.name for x in d.iterdir()] == ["x.sh"], list(d.iterdir())


def test_write_atomic_new_file_and_symlink_target():
    d = tam.temp_dir()
    moi = d / "moi.sh"
    db.write_atomic(moi, b"a\n")
    assert moi.read_bytes() == b"a\n"
    that = d / "that.sh"
    that.write_bytes(b"1\n")
    ln = d / "ln.sh"
    ln.symlink_to(that)
    db.write_atomic(ln, b"2\n")
    assert ln.is_symlink() and that.read_bytes() == b"2\n", "phai ghi vao dich cua symlink"


def test_ra_hermes_cron_script_keeps_exec_bit():
    """Duong that: _sync_pair --ra-hermes ghi de tep cron LIVE ma khong mat +x."""
    t = tam.temp_dir()
    cu = (db.HOMES, db.REPO)
    db.HOMES, db.REPO = {"blog": t / "blog"}, t / "repo"
    try:
        (db.REPO / "scripts").mkdir(parents=True)
        (db.REPO / "scripts" / "publish_due.sh").write_bytes(b"#!/bin/bash\necho moi\n")
        live = db.HOMES["blog"] / "scripts" / "publish_due.sh"
        live.parent.mkdir(parents=True)
        live.write_bytes(b"#!/bin/bash\necho cu\n")
        live.chmod(0o755)
        a = argparse.Namespace(chi="cron blog/publish_due", vao_repo=False, ra_hermes=True, ep=False)
        khac, _, bo_qua, da_chep = db._sync_pair(a)
        assert da_chep == 1 and not bo_qua, (khac, bo_qua, da_chep)
        assert live.read_bytes() == b"#!/bin/bash\necho moi\n"
        assert stat.S_IMODE(live.stat().st_mode) == 0o755, oct(live.stat().st_mode)
    finally:
        db.HOMES, db.REPO = cu


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
