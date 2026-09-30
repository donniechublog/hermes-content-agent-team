#!/usr/bin/env python3
"""update_hermes.sh chi lui khi ban cap nhat lam HONG THEM (LOW-448).

Vi sao phai co test: `kiem` = check_hermes AND check_env, chay chi SAU cap nhat.
May thieu khoa API/Chromium (check_env do tu truoc) -> cap nhat thanh cong,
check_hermes qua, `kiem` van hong chi vi check_env -> script `git reset --hard`
lui mot ban hermes TOT roi do loi cho lan cap nhat. Nay script kiem MOT lan
truoc (moc) va chi lui khi mot buoc TUNG QUA nay do.

Mo phong bang HOME gia: content-team gia (check_*.py doc ma thoat tu tep theo
HEAD cua hermes-agent gia), hermes-agent la repo git that, `hermes` gia tao
them mot commit.

Chay:  venv/bin/python tests/test_update_hermes.py
"""
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPT = ROOT / "hermes" / "scripts" / "update_hermes.sh"
BASH = shutil.which("bash")
GIT = shutil.which("git")

# check gia: ma thoat = noi dung tep `verdict/<ten>.<8 ky tu dau HEAD>`, khong co
# thi `verdict/<ten>` (ket qua cua HEAD cu). `hermes` gia ghi tep theo HEAD moi.
CHECK = """import subprocess, sys, pathlib
v = pathlib.Path(sys.argv[0]).resolve().parent / "verdict"
head = subprocess.check_output(["git", "-C", "%(agent)s", "rev-parse", "--short=8", "HEAD"], text=True).strip()
name = "%(name)s"
f = v / f"{name}.{head}"
if not f.exists():
    f = v / name
code = int(f.read_text().strip() or "0")
print(f"{name} @ {head} -> {code}")
sys.exit(code)
"""


def _git(agent, *a):
    return subprocess.run([GIT, "-C", str(agent), *a], capture_output=True, text=True, check=True).stdout.strip()


def _dung(home: Path):
    """Dung ~/content-team + ~/hermes-agent gia; tra ve (agent, verdict_dir, goc)."""
    agent = home / "hermes-agent"
    ct = home / "content-team"
    (agent / "venv" / "bin").mkdir(parents=True)
    (ct / "venv" / "bin").mkdir(parents=True)
    (ct / "verdict").mkdir()
    for d in (agent, ct):
        py = d / "venv" / "bin" / "python"
        py.symlink_to(sys.executable)
    for name in ("check_hermes", "check_env"):
        (ct / f"{name}.py").write_text(CHECK % {"agent": agent, "name": name}, encoding="utf-8")
    _git(agent, "init", "-q", "-b", "main")
    _git(agent, "config", "user.email", "t@t")
    _git(agent, "config", "user.name", "t")
    (agent / "a.txt").write_text("1")
    _git(agent, "add", "a.txt")
    _git(agent, "commit", "-q", "-m", "c1")
    goc = _git(agent, "rev-parse", "HEAD")
    (home / "bin").mkdir()
    return agent, ct / "verdict", goc


def _hermes_gia(home: Path, agent: Path, v: Path, h_sau, m_sau):
    """`hermes update` gia: them mot commit moi va ghi ket qua check cho HEAD moi."""
    fake = home / "bin" / "hermes"
    fake.write_text(
        f'#!/bin/bash\ncd "{agent}" && echo 2 > a.txt && git add a.txt && git commit -q -m c2\n'
        f'h=$(git rev-parse --short=8 HEAD)\n'
        f'echo {h_sau} > "{v}/check_hermes.$h"\necho {m_sau} > "{v}/check_env.$h"\n',
        encoding="utf-8")
    fake.chmod(0o755)


def _chay(home: Path, *args):
    env = {**os.environ, "HOME": str(home), "PATH": f"{home / 'bin'}:{os.environ['PATH']}"}
    env.pop("LENH_CAP_NHAT", None)
    return subprocess.run([BASH, str(SCRIPT), *args], capture_output=True, text=True, env=env)


def _tinh_huong(h_truoc, m_truoc, h_sau, m_sau, *args):
    """Chay script voi ket qua check truoc/sau cap nhat; tra (proc, HEAD cuoi, HEAD goc)."""
    with tempfile.TemporaryDirectory() as d:
        home = Path(d)
        agent, v, goc = _dung(home)
        (v / "check_hermes").write_text(str(h_truoc))
        (v / "check_env").write_text(str(m_truoc))
        _hermes_gia(home, agent, v, h_sau, m_sau)
        r = _chay(home, *args)
        return r, _git(agent, "rev-parse", "HEAD"), goc


def test_env_do_tu_truoc_khong_lui_ban_tot():
    """LOW-448: check_env do tu truoc, check_hermes qua -> giu ban moi, thoat 0."""
    if not (BASH and GIT):
        print("  (bo qua: thieu bash/git)")
        return
    r, cuoi, goc = _tinh_huong(0, 1, 0, 1)
    assert cuoi != goc, f"da lui ban tot vi check_env do tu truoc:\n{r.stdout}{r.stderr}"
    assert r.returncode == 0, f"phai thoat 0, duoc {r.returncode}:\n{r.stdout}{r.stderr}"
    assert "KHONG lui" in r.stderr, r.stderr


def test_check_hermes_hong_do_ban_moi_thi_van_lui():
    """Buoc TUNG QUA (check_hermes) nay do -> lui ve dung HEAD cu, thoat 1 (du check_env do san)."""
    if not (BASH and GIT):
        print("  (bo qua: thieu bash/git)")
        return
    r, cuoi, goc = _tinh_huong(0, 1, 1, 1)
    assert cuoi == goc, f"khong lui khi check_hermes hong do ban moi:\n{r.stdout}{r.stderr}"
    assert r.returncode == 1, f"phai thoat 1, duoc {r.returncode}:\n{r.stdout}{r.stderr}"
    assert "da lui ve" in r.stderr, r.stderr


def test_check_env_tung_qua_nay_do_thi_lui():
    """check_env qua truoc, do sau (vd cap nhat go mat goi pip) -> lui."""
    if not (BASH and GIT):
        print("  (bo qua: thieu bash/git)")
        return
    r, cuoi, goc = _tinh_huong(0, 0, 0, 1)
    assert cuoi == goc, f"khong lui khi check_env do MOI:\n{r.stdout}{r.stderr}"
    assert r.returncode == 1, f"phai thoat 1, duoc {r.returncode}:\n{r.stdout}{r.stderr}"


def test_tat_ca_lanh_thoat_0_giu_ban_moi():
    if not (BASH and GIT):
        print("  (bo qua: thieu bash/git)")
        return
    r, cuoi, goc = _tinh_huong(0, 0, 0, 0)
    assert cuoi != goc and r.returncode == 0, f"{r.returncode}:\n{r.stdout}{r.stderr}"


def test_khong_tu_lui_van_ton_trong():
    """--khong-lui: hong THAT (te hon moc) thi bao, khong lui."""
    if not (BASH and GIT):
        print("  (bo qua: thieu bash/git)")
        return
    r, cuoi, goc = _tinh_huong(0, 0, 1, 0, "--khong-lui")
    assert r.returncode == 1 and cuoi != goc, f"{r.returncode}:\n{r.stdout}{r.stderr}"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
