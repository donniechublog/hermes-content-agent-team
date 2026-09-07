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


_HANG_DE = ("HOMES", "REPO", "PLUGIN_REPO", "TEP_UPSTREAM", "TAT_CONG_CU",
            "TEP_CAU_HINH")


def _tam():
    """Tro MOI hang duong dan cua dong_bo_hermes vao thu muc tam.

    Truoc 06/09/2026 chi de HOMES/REPO/PLUGIN_REPO. Ba hang con lai
    (TEP_UPSTREAM, TAT_CONG_CU, TEP_CAU_HINH) duoc tinh TU `REPO` LUC IMPORT
    nen de `REPO` khong lam chung doi theo: mot test cho `dong_bo_tat_cong_cu`,
    `ghi_upstream` hay `chup_cau_hinh` se ghi THANG vao repo that
    (hermes/profiles/disabled_toolsets.json, hermes/plugins/kanban/UPSTREAM,
    hermes/profiles/cau_hinh_that.yaml). Cai bay do dang mo san; day dong lai.

    Goi trong `with _tam() as t:` de tra lai hang cu — hom nay moi tep test la
    mot tien trinh nen ro ri khong lo ra, nhung doi sang pytest gom mot tien
    trinh la ro sang moi test khac import dong_bo_hermes.
    """
    return _TamCtx()


class _TamCtx:
    def __enter__(self):
        self.cu = {k: getattr(db, k) for k in _HANG_DE}
        t = self.t = Path(tempfile.mkdtemp())
        db.HOMES = {"blog": t / "blog", "dcgr": t / "dcgr"}
        db.REPO = t / "repo"
        db.PLUGIN_REPO = db.REPO / "plugins" / "kanban" / "dashboard"
        db.TEP_UPSTREAM = db.REPO / "plugins" / "kanban" / "UPSTREAM"
        db.TAT_CONG_CU = db.REPO / "profiles" / "disabled_toolsets.json"
        db.TEP_CAU_HINH = db.REPO / "profiles" / "cau_hinh_that.yaml"
        return t

    def __exit__(self, *e):
        for k, v in self.cu.items():
            setattr(db, k, v)
        return False


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
    with _tam() as t:
        cap = {ten: (that, repo) for ten, that, repo in db.cap_tep() if ten.startswith("kanban ")}
        assert len(cap) == len(db.PLUGIN_TEP) * 2, sorted(cap)
        that, repo = cap["kanban blog dist/index.js"]
        assert that == t / "blog" / "plugins" / "kanban" / "dashboard" / "dist" / "index.js", that
        assert repo == db.PLUGIN_REPO / "dist" / "index.js", repo
        # KHONG con tro vao ban cai hermes-agent
        assert not any("hermes-agent" in str(p) for _, (p, _) in cap.items())


def test_hai_home_lech_bi_tu_choi():
    with _tam():
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
    with _tam():
        H = db.HOMES["blog"]; H.mkdir(parents=True)
        (H / "config.yaml").write_text("plugins:\n  enabled:\n    - kanban\n", encoding="utf-8")
        assert db.kanban_da_bat(H) is True
        (H / "config.yaml").write_text("plugins:\n  enabled: []\n", encoding="utf-8")
        assert db.kanban_da_bat(H) is False
        (H / "config.yaml").write_text("model:\n  default: x\n", encoding="utf-8")
        assert db.kanban_da_bat(H) is False
        assert db.kanban_da_bat(db.HOMES["dcgr"]) is None       # khong co tep


def test_tam_tra_lai_moi_hang_duong_dan():
    """Chinh cai bay o tren: _tam() phai de VA tra lai du sau hang, khong thi
    test sau (hoac tep test khac khi doi sang pytest) ghi vao repo that."""
    truoc = {k: getattr(db, k) for k in _HANG_DE}
    with _tam() as t:
        for k in _HANG_DE:
            v = getattr(db, k)
            duong = list(v.values()) if isinstance(v, dict) else [v]
            assert all(str(t) in str(p) for p in duong), f"{k} khong tro vao thu muc tam: {v}"
    assert {k: getattr(db, k) for k in _HANG_DE} == truoc, "khong tra lai hang cu"


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
