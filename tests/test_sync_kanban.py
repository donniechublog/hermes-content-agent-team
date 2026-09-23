#!/usr/bin/env python3
"""Kiem co che dong bo plugin kanban cua sync_hermes.py — day la lan thu ba
co che nay bi mat ban va (a1f9387), nen phai co luoi.

Khong dung pytest (chua co trong venv). Chay:
    venv/bin/python tests/test_sync_kanban.py
Khong dung home that: HOMES/REPO tro vao thu muc tam.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import sync_hermes as db  # noqa: E402
import tam  # noqa: E402

CO_VA = b'x\nif (!props.laneByProfile) return null;\nCOLUMN_ORDER = ["running", "ready", "blocked"]\ntenVai(a)\n'
KHONG_VA = b'x\nif (!props.laneByProfile || props.column.name !== "running") return null;\nCOLUMN_ORDER = ["triage", "todo"]\n'


_HANG_DE = ("HOMES", "REPO", "PLUGIN_REPO", "FILE_UPSTREAM", "ALL_GATE_OLD",
            "FILE_CONFIG")


def _temp():
    """Tro MOI hang duong dan cua sync_hermes vao thu muc tam.

    Truoc 06/09/2026 chi de HOMES/REPO/PLUGIN_REPO. Ba hang con lai
    (FILE_UPSTREAM, ALL_GATE_OLD, FILE_CONFIG) duoc tinh TU `REPO` LUC IMPORT
    nen de `REPO` khong lam chung doi theo: mot test cho `sync_all_gate_old`,
    `write_upstream` hay `chup_cau_hinh` se ghi THANG vao repo that
    (hermes/profiles/disabled_toolsets.json, hermes/plugins/kanban/UPSTREAM,
    hermes/profiles/live_config_snapshot.yaml). Cai bay do dang mo san; day dong lai.

    Goi trong `with _temp() as t:` de tra lai hang cu — hom nay moi tep test la
    mot tien trinh nen ro ri khong lo ra, nhung doi sang pytest gom mot tien
    trinh la ro sang moi test khac import sync_hermes.
    """
    return _TamCtx()


class _TamCtx:
    def __enter__(self):
        self.cu = {k: getattr(db, k) for k in _HANG_DE}
        t = self.t = Path(tam.temp_dir())
        db.HOMES = {"blog": t / "blog", "dcgr": t / "dcgr"}
        db.REPO = t / "repo"
        db.PLUGIN_REPO = db.REPO / "plugins" / "kanban" / "dashboard"
        db.FILE_UPSTREAM = db.REPO / "plugins" / "kanban" / "UPSTREAM"
        db.ALL_GATE_OLD = db.REPO / "profiles" / "disabled_toolsets.json"
        db.FILE_CONFIG = db.REPO / "profiles" / "live_config_snapshot.yaml"
        return t

    def __exit__(self, *e):
        for k, v in self.cu.items():
            setattr(db, k, v)
        return False


def test_name_item_extract_use_file():
    assert db._file_plugin("kanban blog dist/index.js") == "dist/index.js"
    assert db._file_plugin("kanban dcgr plugin_api.py") == "plugin_api.py"
    assert db._file_plugin("SOUL blog/bob") is None
    assert db._file_plugin("kanban dist/index.js") is None       # dinh dang cu, khong nhan


def test_gate_trace_block_indent_back_all_two_dimension():
    ten = "kanban blog dist/index.js"
    # dich co ban va, nguon khong -> chan (day la kich ban a1f9387)
    assert db.missing_trace(ten, KHONG_VA, CO_VA)
    # nguon co, dich khong -> dang mang ban va sang, cho qua
    assert db.missing_trace(ten, CO_VA, KHONG_VA) is None
    # giong nhau -> qua
    assert db.missing_trace(ten, CO_VA, CO_VA) is None
    # manifest.json khong co dau vet -> khong bao gio chan
    assert db.missing_trace("kanban blog manifest.json", b"a", b"b") is None


def test_cap_file_point_into_plugin_user():
    with _temp() as t:
        cap = {ten: (that, repo) for ten, that, repo in db.cap_file() if ten.startswith("kanban ")}
        assert len(cap) == len(db.PLUGIN_FILE) * 2, sorted(cap)
        that, repo = cap["kanban blog dist/index.js"]
        assert that == t / "blog" / "plugins" / "kanban" / "dashboard" / "dist" / "index.js", that
        assert repo == db.PLUGIN_REPO / "dist" / "index.js", repo
        # KHONG con tro vao ban cai hermes-agent
        assert not any("hermes-agent" in str(p) for _, (p, _) in cap.items())


def test_two_home_offset_got_reject():
    with _temp():
        for hk in ("blog", "dcgr"):
            p = db.plugin_home(db.HOMES[hk]) / "dist" / "index.js"
            p.parent.mkdir(parents=True)
            p.write_bytes(CO_VA if hk == "blog" else KHONG_VA)
        ly = db.two_home_offset("dist/index.js")
        assert ly and "blog" in ly and "dcgr" in ly, ly
        # mot home thieu tep -> khong lech
        (db.plugin_home(db.HOMES["dcgr"]) / "dist" / "index.js").unlink()
        assert db.two_home_offset("dist/index.js") is None
        # hai home giong nhau (khac CRLF) -> khong lech
        (db.plugin_home(db.HOMES["dcgr"]) / "dist" / "index.js").write_bytes(CO_VA.replace(b"\n", b"\r\n"))
        assert db.two_home_offset("dist/index.js") is None


def test_kanban_already_catch_read_config():
    with _temp():
        H = db.HOMES["blog"]; H.mkdir(parents=True)
        (H / "config.yaml").write_text("plugins:\n  enabled:\n    - kanban\n", encoding="utf-8")
        assert db.kanban_already_catch(H) is True
        (H / "config.yaml").write_text("plugins:\n  enabled: []\n", encoding="utf-8")
        assert db.kanban_already_catch(H) is False
        (H / "config.yaml").write_text("model:\n  default: x\n", encoding="utf-8")
        assert db.kanban_already_catch(H) is False
        assert db.kanban_already_catch(db.HOMES["dcgr"]) is None       # khong co tep


def test_temp_return_again_new_rank_path():
    """Chinh cai bay o tren: _temp() phai de VA tra lai du sau hang, khong thi
    test sau (hoac tep test khac khi doi sang pytest) ghi vao repo that."""
    truoc = {k: getattr(db, k) for k in _HANG_DE}
    with _temp() as t:
        for k in _HANG_DE:
            v = getattr(db, k)
            duong = list(v.values()) if isinstance(v, dict) else [v]
            assert all(str(t) in str(p) for p in duong), f"{k} khong tro vao thu muc tam: {v}"
    assert {k: getattr(db, k) for k in _HANG_DE} == truoc, "khong tra lai hang cu"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
