#!/usr/bin/env python3
"""Kiem co che dong bo plugin kanban cua dong_bo_hermes.py — day la lan thu ba
co che nay bi mat ban va (a1f9387), nen phai co luoi.

Khong dung pytest (chua co trong venv). Chay:
    venv/bin/python tests/test_dong_bo_kanban.py
Khong dung home that: HOMES/REPO tro vao thu muc tam.
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import dong_bo_hermes as db  # noqa: E402

CO_VA = b'x\nif (!props.laneByProfile) return null;\nCOLUMN_ORDER = ["running", "ready", "blocked"]\ntenVai(a)\n'
KHONG_VA = b'x\nif (!props.laneByProfile || props.column.name !== "running") return null;\nCOLUMN_ORDER = ["triage", "todo"]\n'


def _tam():
    t = Path(tempfile.mkdtemp())
    db.HOMES = {"blog": t / "blog", "dcgr": t / "dcgr"}
    db.REPO = t / "repo"
    db.PLUGIN_REPO = db.REPO / "plugins" / "kanban" / "dashboard"
    return t


def test_ten_muc_tach_dung_tep():
    assert db._tep_plugin("kanban blog dist/index.js") == "dist/index.js"
    assert db._tep_plugin("kanban dcgr plugin_api.py") == "plugin_api.py"
    assert db._tep_plugin("SOUL blog/bob") is None
    assert db._tep_plugin("kanban dist/index.js") is None       # dinh dang cu, khong nhan


def test_cong_dau_vet_chan_thut_lui_ca_hai_chieu():
    ten = "kanban blog dist/index.js"
    # dich co ban va, nguon khong -> chan (day la kich ban a1f9387)
    assert db.thieu_dau_vet(ten, KHONG_VA, CO_VA)
    # nguon co, dich khong -> dang mang ban va sang, cho qua
    assert db.thieu_dau_vet(ten, CO_VA, KHONG_VA) is None
    # giong nhau -> qua
    assert db.thieu_dau_vet(ten, CO_VA, CO_VA) is None
    # manifest.json khong co dau vet -> khong bao gio chan
    assert db.thieu_dau_vet("kanban blog manifest.json", b"a", b"b") is None


def test_cap_tep_tro_vao_plugin_nguoi_dung():
    t = _tam()
    cap = {ten: (that, repo) for ten, that, repo in db.cap_tep() if ten.startswith("kanban ")}
    assert len(cap) == len(db.PLUGIN_TEP) * 2, sorted(cap)
    that, repo = cap["kanban blog dist/index.js"]
    assert that == t / "blog" / "plugins" / "kanban" / "dashboard" / "dist" / "index.js", that
    assert repo == db.PLUGIN_REPO / "dist" / "index.js", repo
    # KHONG con tro vao ban cai hermes-agent
    assert not any("hermes-agent" in str(p) for _, (p, _) in cap.items())


def test_hai_home_lech_bi_tu_choi():
    t = _tam()
    for hk in ("blog", "dcgr"):
        p = db.plugin_home(db.HOMES[hk]) / "dist" / "index.js"
        p.parent.mkdir(parents=True)
        p.write_bytes(CO_VA if hk == "blog" else KHONG_VA)
    ly = db.hai_home_lech("dist/index.js")
    assert ly and "blog" in ly and "dcgr" in ly, ly
    # mot home thieu tep -> khong lech
    (db.plugin_home(db.HOMES["dcgr"]) / "dist" / "index.js").unlink()
    assert db.hai_home_lech("dist/index.js") is None
    # hai home giong nhau (khac CRLF) -> khong lech
    (db.plugin_home(db.HOMES["dcgr"]) / "dist" / "index.js").write_bytes(CO_VA.replace(b"\n", b"\r\n"))
    assert db.hai_home_lech("dist/index.js") is None


def test_kanban_da_bat_doc_config():
    t = _tam()
    H = db.HOMES["blog"]; H.mkdir(parents=True)
    (H / "config.yaml").write_text("plugins:\n  enabled:\n    - kanban\n", encoding="utf-8")
    assert db.kanban_da_bat(H) is True
    (H / "config.yaml").write_text("plugins:\n  enabled: []\n", encoding="utf-8")
    assert db.kanban_da_bat(H) is False
    (H / "config.yaml").write_text("model:\n  default: x\n", encoding="utf-8")
    assert db.kanban_da_bat(H) is False
    assert db.kanban_da_bat(db.HOMES["dcgr"]) is None       # khong co tep


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
