#!/usr/bin/env python3
"""Vài hàm nhỏ của env_load thêm ở đợt 6 (audit lượt 2): quantity, ghi_json.

Chạy:  venv/bin/python tests/test_env_load.py
"""
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import env_load                                               # noqa: E402

# Tep goi Telegram truc tiep: cong nay giu chung dung thu tu, khong duoc trom
# cua nhau. Cap nhat danh sach khi them tep goi Telegram moi.
TEP_GOI_TELEGRAM = ["send_telegram.py", "publish.py", "approve_service.py",
                    "route_missing_images.py", "approve_base.py"]


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
    assert _voi_env("CT_WORKERS", None, lambda: env_load.quantity(6)) == 6
    assert _voi_env("CT_WORKERS", "2", lambda: env_load.quantity(6)) == 2
    assert _voi_env("CT_WORKERS", "16", lambda: env_load.quantity(6)) == 6, "khong nang qua mac dinh"
    assert _voi_env("CT_WORKERS", "0", lambda: env_load.quantity(6)) == 6
    assert _voi_env("CT_WORKERS", "xyz", lambda: env_load.quantity(6)) == 6, "gia tri rac -> mac dinh"


def test_ghi_json_hong_giua_chung_khong_de_tmp_va_giu_tep_cu():
    """ADF-r2-11: mot ban ghi nguyen tu cho 4 cho tung tu viet — phai don tmp
    khi hong va khong cham tep cu."""
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "a" / "b.json"
        env_load.write_json(p, {"x": 1})                    # tu mkdir
        assert json.loads(p.read_text(encoding="utf-8")) == {"x": 1}
        truoc = p.read_bytes()
        import os as _os
        cu = _os.replace

        def _no(*a, **k):
            raise OSError(28, "ENOSPC")
        _os.replace = _no
        try:
            try:
                env_load.write_json(p, {"z": 2})
            except OSError:
                pass
        finally:
            _os.replace = cu
        assert not list((Path(t) / "a").glob("*.tmp.*")), "tmp con sot lai sau khi hong"
        assert p.read_bytes() == truoc, "tep cu bi dong vao khi ghi hong"


def test_openssl_conf_dat_khi_import_va_khong_de_len_gia_tri_co_san():
    """LOW-159: chi import env_load (chua goi load()) phai dat OPENSSL_CONF tro
    dung tep .cnf trong git, tru khi tien trinh da tu dat gia tri khac truoc do
    (setdefault, khong de len)."""
    kw_dep = str(ROOT / "hermes" / "systemd" / "openssl" / "hermes-groups.cnf")
    env_rong = {k: v for k, v in os.environ.items() if k != "OPENSSL_CONF"}

    r = subprocess.run([sys.executable, "-c", "import env_load, os; print(os.environ.get('OPENSSL_CONF'))"],
                       cwd=str(ROOT), capture_output=True, text=True, env=env_rong)
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == kw_dep, f"import env_load khong dat OPENSSL_CONF dung tep: {r.stdout!r}\n{r.stderr}"

    r2 = subprocess.run([sys.executable, "-c", "import env_load, os; print(os.environ.get('OPENSSL_CONF'))"],
                        cwd=str(ROOT), capture_output=True, text=True,
                        env={**os.environ, "OPENSSL_CONF": "/da/tu/dat"})
    assert r2.returncode == 0, r2.stderr
    assert r2.stdout.strip() == "/da/tu/dat", "setdefault phai giu gia tri da co, khong de len"


def test_tep_goi_telegram_nap_env_load_truoc_httpx():
    """LOW-159: OPENSSL_CONF phai dat TRUOC `import httpx` moi co tac dung (do
    truc tiep tren may chu 14/09: set SAU khong sua duoc handshake da hong).
    Sap xep lai thu tu import trong tuong lai ma quen dieu nay se tai dien
    dung sy co Nova bi block 15/09 (httpx.ConnectTimeout luc bat tay TLS)."""
    mau_env_load = re.compile(r"^\s*import\s+env_load\b", re.M)
    mau_httpx = re.compile(r"^\s*import\s+httpx\b", re.M)
    loi = []
    for ten in TEP_GOI_TELEGRAM:
        s = (ROOT / ten).read_text(encoding="utf-8")
        m_env, m_httpx = mau_env_load.search(s), mau_httpx.search(s)
        if not (m_env and m_httpx):
            loi.append(f"{ten}: khong tim thay ca hai dong import (kiem tra tay)")
        elif m_env.start() > m_httpx.start():
            loi.append(f"{ten}: `import httpx` dung TRUOC `import env_load` — OPENSSL_CONF se khong kip dat")
    assert not loi, "\n".join(loi)


def test_hermes_home_from_profile_worker_resolves_to_brand_home():
    """LOW-217: kanban worker dat HERMES_HOME = home profile; hermes_home() phai
    tra home brand, neu khong kiem profile Kite bao sai "brand chua co Kite"."""
    brand = str(Path.home() / ".hermes-blog")
    assert _voi_env("HERMES_HOME", brand, env_load.hermes_home) == Path(brand)
    assert _voi_env("HERMES_HOME", brand + "/profiles/dre", env_load.hermes_home) == Path(brand)
    assert _voi_env("HERMES_HOME", None, env_load.hermes_home) == Path.home() / ".hermes"


def test_standard_assignee_finds_kite_from_dre_worker():
    """LOW-217: dung dung duong goi that — approve_dispatch.standard_assignee
    chay trong tien trinh co HERMES_HOME cua profile Dre."""
    with tempfile.TemporaryDirectory() as t:
        brand = Path(t) / ".hermes-blog"
        for vai in ("dre", "kite"):
            (brand / "profiles" / vai).mkdir(parents=True)
        ma = ("from approve_dispatch import standard_assignee; "
              "print(standard_assignee('kite'))")
        r = subprocess.run([sys.executable, "-c", ma], cwd=str(ROOT), capture_output=True, text=True,
                           env={**os.environ, "HERMES_HOME": str(brand / "profiles" / "dre")}, timeout=60)
        assert r.returncode == 0, r.stderr[-500:]
        assert r.stdout.strip().splitlines()[-1] == "('kite', None)", r.stdout


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
