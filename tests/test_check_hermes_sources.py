#!/usr/bin/env python3
"""check_hermes.py lay hermes-agent va danh sach home tu MOT nguon (D16).

Vi sao phai co test: tep nay cung `~/hermes-agent` va `("blog", "dcgr")` trong khi
`env_load.hermes_homes()` (danh sach brand) va `kanban_plugin_build.HERMES_AGENT`
(ton trong HERMES_AGENT_DIR) da la nguon duy nhat cua phan con lai. Dat
HERMES_AGENT_DIR o cho khac hoac them mot brand thi check_hermes kiem sai cho ma
van bao xanh/do theo mot the gioi khong ton tai.

Chay:  venv/bin/python tests/test_check_hermes_sources.py
"""
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import check_hermes as ch  # noqa: E402
import env_load  # noqa: E402
import kanban_plugin_build as kpb  # noqa: E402
import tam  # noqa: E402


def test_hermes_py_follows_HERMES_AGENT_DIR():
    """Doc bien moi truong LUC IMPORT, nen kiem trong tien trinh con."""
    t = tam.temp_dir()
    r = subprocess.run([sys.executable, "-c",
                        "import check_hermes as c; print(c._hermes_py())"],
                       capture_output=True, text=True, cwd=ROOT,
                       env={**os.environ, "HERMES_AGENT_DIR": str(t / "agent")})
    assert r.returncode == 0, r.stderr
    assert r.stdout.strip() == str(t / "agent" / "venv" / "bin" / "python"), r.stdout


def test_chat_and_swarm_checks_use_the_configured_agent():
    t = tam.temp_dir()
    cu = kpb.HERMES_AGENT
    kpb.HERMES_AGENT = t / "agent"
    try:
        # chua co venv o thu muc do: bao dung duong dan cau hinh, khong phai ~/hermes-agent
        loi = ch.check_has_chat()
        assert loi and str(t / "agent") in loi[0], loi
        loi = ch.check_swarm()
        assert loi and str(t / "agent") in loi[0], loi
        # co venv gia in du cac co -> check_has_chat phai GOI dung no (xanh)
        py = t / "agent" / "venv" / "bin" / "python"
        py.parent.mkdir(parents=True)
        py.write_text("#!/bin/bash\necho " + " ".join(ch.HAS_CHAT) + "\n", encoding="utf-8")
        py.chmod(0o755)
        assert ch.check_has_chat() == [], ch.check_has_chat()
    finally:
        kpb.HERMES_AGENT = cu


def test_home_list_comes_from_env_load_hermes_homes():
    t = tam.temp_dir()
    cu = env_load.hermes_homes
    (t / "alpha").mkdir()
    (t / "beta").mkdir()
    (t / "beta" / "kanban.db").write_bytes(b"")
    env_load.hermes_homes = lambda: {"alpha": t / "alpha", "beta": t / "beta"}
    try:
        # brand ngoai blog/dcgr, va chi tinh home CO kanban.db
        assert ch._home_kanban() == [("beta", t / "beta" / "kanban.db")], ch._home_kanban()
        con = sqlite3.connect(t / "beta" / "kanban.db")
        con.execute("create table tasks (id text)")
        con.commit()
        con.close()
        loi = ch.check_column()
        assert any(x.startswith("beta: bang `tasks` thieu cot") for x in loi), loi
        assert not any(x.startswith(("blog", "dcgr")) for x in loi), loi
    finally:
        env_load.hermes_homes = cu


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
