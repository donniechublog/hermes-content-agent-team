#!/usr/bin/env python3
"""sync_hermes --compare-runtime: so config gateway + unit systemd voi ban chup (D18).

Vi sao phai co test: unit systemd va config.yaml gateway quyet dinh hanh vi that
nhung nam ngoai phan dong bo cua sync_hermes (README systemd: "khong ghi de").
Che do so sanh chi-doc phai (1) bat dung lech, (2) khong bao nham vi token dashboard
da che trong repo hay vi CRLF, (3) TUYET DOI khong ghi gi.

Chay:  venv/bin/python tests/test_sync_compare_runtime.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import sync_hermes as sh  # noqa: E402
import tam  # noqa: E402

TOKEN_REPO = "Environment=HERMES_DASHBOARD_SESSION_TOKEN=<DAT TOKEN THAT O DAY — KHONG COMMIT>\n"
FILES = {
    "gateway/dcgr/config.yaml": "model:\n  default: DS-v4Flash\ngateway:\n  multiplex_profiles: true\n",
    "systemd/hermes-dashboard-dcgr.service": "[Service]\n" + TOKEN_REPO,
    "systemd/hermes-approve@.service.d/openssl-groups.conf": "[Service]\nEnvironment=OPENSSL_CONF=%h/x\n",
    "systemd/openssl/hermes-groups.cnf": "Groups = X25519\n",
    "systemd/README.md": "khong so sanh tep nay\n",
}


class _Cay:
    """Repo gia + cau hinh may gia; tro sync_hermes vao do, tra lai khi thoat."""

    def __enter__(self):
        t = self.t = tam.temp_dir()
        self.cu = (sh.GATEWAY_REPO, sh.SYSTEMD_REPO)
        repo = t / "repo"
        for rel, nd in FILES.items():
            p = repo / rel
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(nd, encoding="utf-8")
        sh.GATEWAY_REPO, sh.SYSTEMD_REPO = repo / "gateway", repo / "systemd"
        self.cfg = t / "cfg"
        self.homes = {"dcgr": t / "home-dcgr", "blog": t / "home-blog"}
        for h in self.homes.values():
            h.mkdir()
        self.dat_may()
        return self

    def dat_may(self):
        """May chu khop ban chup, tru token that va xuong dong CRLF."""
        (self.homes["dcgr"] / "config.yaml").write_bytes(FILES["gateway/dcgr/config.yaml"].replace("\n", "\r\n").encode())
        (self.homes["blog"] / "config.yaml").write_text("model: {}\n", encoding="utf-8")
        u = self.cfg / "systemd" / "user"
        for rel, nd in FILES.items():
            if not rel.startswith("systemd/") or rel.endswith("README.md"):
                continue
            r = rel[len("systemd/"):]
            p = (self.cfg / r) if r.startswith("openssl/") else u / r
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(nd.replace("<DAT TOKEN THAT O DAY — KHONG COMMIT>", "tok-that-123"), encoding="utf-8")

    def __exit__(self, *e):
        sh.GATEWAY_REPO, sh.SYSTEMD_REPO = self.cu

    def snapshot(self):
        return {str(p): (p.read_bytes(), p.stat().st_mtime_ns) for p in self.t.rglob("*") if p.is_file()}

    def compare(self, **k):
        return sh.compare_runtime(self.homes, self.cfg, **k)


def test_khop_thi_khong_bao_lech_du_token_that_va_crlf():
    with _Cay() as c:
        lech, ghi_chu = c.compare()
        assert lech == [], lech
        # blog co config.yaml that ma repo chua co ban chup -> chi ghi chu, khong tinh la lech
        assert any("gateway blog" in g for g in ghi_chu), ghi_chu


def test_bat_dung_khac_thieu_va_chi_co_tren_may():
    with _Cay() as c:
        (c.homes["dcgr"] / "config.yaml").write_text(
            "model:\n  default: OTHER\ngateway:\n  multiplex_profiles: true\n", encoding="utf-8")
        (c.cfg / "openssl" / "hermes-groups.cnf").unlink()
        u = c.cfg / "systemd" / "user"
        (u / "hermes-extra.service").write_text("[Service]\n", encoding="utf-8")
        (u / "hermes-approve@.service.d" / "them.conf").write_text("[Service]\n", encoding="utf-8")
        (u / "khong-phai-cua-doi.service").write_text("x", encoding="utf-8")    # khong hermes-* -> bo qua
        (u / "hermes-alias.service").symlink_to(u / "hermes-extra.service")     # symlink enable -> bo qua
        lech, _ = c.compare()
        m = {(muc, ten) for muc, ten, _ in lech}
        assert m == {("KHAC", "gateway dcgr/config.yaml"),
                     ("THIEU", "systemd openssl/hermes-groups.cnf"),
                     ("CHI_CO_TREN_MAY", "systemd hermes-extra.service"),
                     ("CHI_CO_TREN_MAY", "systemd hermes-approve@.service.d/them.conf")}, m
        chi_tiet = [d for muc, ten, d in lech if muc == "KHAC"][0]
        assert "-  default: DS-v4Flash" in chi_tiet and "+  default: OTHER" in chi_tiet, chi_tiet


def test_lech_that_o_unit_khong_bi_che_token_nuot_mat():
    with _Cay() as c:
        p = c.cfg / "systemd" / "user" / "hermes-dashboard-dcgr.service"
        p.write_text(p.read_text(encoding="utf-8") + "Environment=CT_BRAND=blog\n", encoding="utf-8")
        lech, _ = c.compare()
        assert [(m, t) for m, t, _ in lech] == [("KHAC", "systemd hermes-dashboard-dcgr.service")], lech


def test_chi_loc_theo_ten():
    with _Cay() as c:
        (c.cfg / "openssl" / "hermes-groups.cnf").unlink()
        (c.homes["dcgr"] / "config.yaml").write_text("x: 1\n", encoding="utf-8")
        lech, _ = c.compare(chi="openssl")
        assert [t for _, t, _ in lech] == ["systemd openssl/hermes-groups.cnf"], lech


def test_chi_doc_khong_ghi_gi_va_ma_thoat():
    with _Cay() as c:
        (c.homes["dcgr"] / "config.yaml").write_text("x: 1\n", encoding="utf-8")
        (c.cfg / "openssl" / "hermes-groups.cnf").unlink()
        cu = sh.HOMES, sh.USER_CONFIG
        sh.HOMES, sh.USER_CONFIG = c.homes, c.cfg
        try:
            truoc = c.snapshot()
            assert sh.compare_runtime_main() == 1
            assert c.snapshot() == truoc, "che do so sanh da ghi/sua tep"
            c.dat_may()
            (c.homes["dcgr"] / "config.yaml").write_text(FILES["gateway/dcgr/config.yaml"], encoding="utf-8")
            assert sh.compare_runtime_main() == 0
        finally:
            sh.HOMES, sh.USER_CONFIG = cu


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
