#!/usr/bin/env python3
"""LOW-313 — plugin kanban = ban goc hermes-agent + BAN VA, khong con chep ca tep.

Dieu phai giu:
  - dung duoc: ban goc (doc tu GIT cua hermes-agent) + ban va -> dung ban da sua
  - phia goc doi DUNG cho doi sua -> nem loi, sync KHONG ghi gi, thoat khac 0
  - phia goc doi cho KHAC -> van dung duoc, co co `drifted` de nguoi chay biet
  - tep ban va bi sua tay -> bat duoc nho sha256 trong MANIFEST.json
  - ban va THAT trong repo con mang du dau vet `sync_hermes.TRACE`

Khong dung ~/hermes-agent that: moi test dung mot repo git gia trong thu muc tam.
Chay:  venv/bin/python tests/test_kanban_plugin_patch.py
"""
import io
import json
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import kanban_plugin_build as kpb      # noqa: E402
import sync_hermes as sync             # noqa: E402

UPSTREAM = {
    "manifest.json": '{"name": "kanban"}\n',
    "plugin_api.py": "import time\n\nCOLUMNS = ['triage', 'todo']\n\n\ndef board():\n"
                     "    return {'now': int(time.time())}\n\n\ndef other():\n    return 1\n",
    "dist/index.js": "const ORDER = ['triage'];\nfunction lane() { return null; }\n",
    "dist/style.css": ".lane { font-size: 0.65rem; }\n",
}
OURS = {
    "plugin_api.py": UPSTREAM["plugin_api.py"].replace("['triage', 'todo']", "['running', 'todo']")
                                              .replace("{'now'", "{'display_names': {}, 'now'"),
    "dist/index.js": UPSTREAM["dist/index.js"].replace("['triage']", "['running']"),
}


def _git(cwd, *args):
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *args],
                   cwd=cwd, check=True, capture_output=True)


def _commit_upstream(agent, files):
    for name, text in files.items():
        p = agent / kpb.UPSTREAM_DIR / name
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text, encoding="utf-8")
    _git(agent, "add", "-A")
    _git(agent, "commit", "-qm", "upstream")


def _sandbox():
    """(thu muc tam, repo hermes-agent gia, thu muc ban va da lam tu OURS)."""
    t = Path(tempfile.mkdtemp(prefix="kanban_patch_test_"))
    agent, patches = t / "hermes-agent", t / "patches"
    agent.mkdir()
    _git(agent, "init", "-q", ".")
    _commit_upstream(agent, UPSTREAM)
    kpb.refresh({k: v.encode() for k, v in OURS.items()}, agent, patches)
    return t, agent, patches


def test_build_is_upstream_plus_patches_and_untouched_files_pass_through():
    t, agent, patches = _sandbox()
    assert sorted(p.name for p in patches.iterdir()) == [
        "MANIFEST.json", "dist__index.js.patch", "plugin_api.py.patch"]
    built = kpb.build(agent, patches)
    assert sorted(built) == sorted(kpb.PLUGIN_FILES)
    for name in kpb.PLUGIN_FILES:
        assert built[name]["data"].decode() == OURS.get(name, UPSTREAM[name]), name
        assert built[name]["drifted"] is False


def test_build_reads_committed_upstream_not_a_dirty_working_tree():
    t, agent, patches = _sandbox()
    (agent / kpb.UPSTREAM_DIR / "plugin_api.py").write_text("ai do sua tay\n", encoding="utf-8")
    assert kpb.build(agent, patches)["plugin_api.py"]["data"].decode() == OURS["plugin_api.py"]


def test_upstream_change_on_a_patched_line_fails_loudly():
    t, agent, patches = _sandbox()
    _commit_upstream(agent, {"plugin_api.py": UPSTREAM["plugin_api.py"].replace(
        "COLUMNS = ['triage', 'todo']", "COLUMNS = ('triage', 'todo', 'review')")})
    try:
        kpb.build(agent, patches)
    except kpb.PluginPatchError as e:
        assert "plugin_api.py.patch" in str(e) and "KHONG ap duoc" in str(e), e
    else:
        raise AssertionError("ban va lech ma khong bao")


def test_upstream_change_elsewhere_still_builds_but_is_flagged_drifted():
    t, agent, patches = _sandbox()
    _commit_upstream(agent, {"plugin_api.py": UPSTREAM["plugin_api.py"].replace(
        "return 1", "return 2  # sua bao mat phia goc")})
    built = kpb.build(agent, patches)
    data = built["plugin_api.py"]["data"].decode()
    assert "return 2  # sua bao mat phia goc" in data, "sua phia goc PHAI toi duoc plugin cua doi"
    assert "'running', 'todo'" in data and "display_names" in data
    assert built["plugin_api.py"]["drifted"] is True
    assert built["dist/index.js"]["drifted"] is False


def test_hand_edited_patch_is_caught_by_manifest_hash():
    t, agent, patches = _sandbox()
    pp = kpb.patch_path("dist/index.js", patches)
    pp.write_text(pp.read_text().replace("+const ORDER = ['running'];",
                                         "+const ORDER = ['hacked'];"), encoding="utf-8")
    try:
        kpb.build(agent, patches)
    except kpb.PluginPatchError as e:
        assert "sha256" in str(e), e
    else:
        raise AssertionError("ban va bi sua tay ma khong bao")


def test_missing_hermes_agent_is_an_error_not_an_empty_plugin():
    t, agent, patches = _sandbox()
    try:
        kpb.build(t / "khong-co", patches)
    except kpb.PluginPatchError as e:
        assert "HERMES_AGENT_DIR" in str(e)
    else:
        raise AssertionError("thieu hermes-agent ma khong bao")


def test_refresh_drops_patch_when_file_matches_upstream_again():
    t, agent, patches = _sandbox()
    kpb.refresh({"plugin_api.py": OURS["plugin_api.py"].encode()}, agent, patches)
    assert not kpb.patch_path("dist/index.js", patches).exists()
    m = json.loads((patches / "MANIFEST.json").read_text())
    assert m["files"]["dist/index.js"]["upstream_sha256"] == m["files"]["dist/index.js"]["built_sha256"]
    assert m["upstream_commit"] == kpb.upstream_head(agent)


# -------------------------------------------------------------------------
# sync_hermes: ghi vao home / tu choi
# -------------------------------------------------------------------------
_SYNC_CONSTANTS = ("HOMES", "REPO", "PLUGIN_REPO", "FILE_UPSTREAM", "ALL_GATE_OLD",
                   "FILE_CONFIG", "HERMES_AGENT")


def _run_sync(t, agent, patches, *argv):
    old = {k: getattr(sync, k) for k in _SYNC_CONSTANTS}
    old_patch_dir, old_argv = kpb.PATCH_DIR, sys.argv
    sync.HOMES = {"blog": t / "blog", "dcgr": t / "dcgr"}
    sync.REPO = t / "repo"
    sync.PLUGIN_REPO = sync.REPO / "plugins" / "kanban" / "dashboard"
    sync.FILE_UPSTREAM = sync.REPO / "plugins" / "kanban" / "UPSTREAM"
    sync.ALL_GATE_OLD = sync.REPO / "profiles" / "disabled_toolsets.json"
    sync.FILE_CONFIG = sync.REPO / "profiles" / "live_config_snapshot.yaml"
    sync.HERMES_AGENT = agent
    kpb.PATCH_DIR = patches
    sync._PLUGIN_BUILD.clear()
    sys.argv = ["sync_hermes.py", *argv]
    out, err = io.StringIO(), io.StringIO()
    try:
        with redirect_stdout(out), redirect_stderr(err):
            rc = sync.main()
    finally:
        for k, v in old.items():
            setattr(sync, k, v)
        kpb.PATCH_DIR, sys.argv = old_patch_dir, old_argv
        sync._PLUGIN_BUILD.clear()
    return rc, out.getvalue() + err.getvalue()


def _home_plugin(t, hk, name):
    return t / hk / "plugins" / "kanban" / "dashboard" / name


def test_ra_hermes_writes_built_plugin_into_both_homes():
    t, agent, patches = _sandbox()
    for hk in ("blog", "dcgr"):
        (t / hk).mkdir()
    rc, log = _run_sync(t, agent, patches, "--ra-hermes", "--chi", "kanban")
    assert rc == 0, log
    for hk in ("blog", "dcgr"):
        assert _home_plugin(t, hk, "plugin_api.py").read_text() == OURS["plugin_api.py"]
        assert _home_plugin(t, hk, "dist/style.css").read_text() == UPSTREAM["dist/style.css"]


def test_ra_hermes_writes_nothing_and_exits_nonzero_when_patch_no_longer_applies():
    t, agent, patches = _sandbox()
    (t / "blog").mkdir()
    stale = _home_plugin(t, "blog", "plugin_api.py")
    stale.parent.mkdir(parents=True)
    stale.write_text("ban dang chay\n", encoding="utf-8")
    _commit_upstream(agent, {"dist/index.js": "const ORDER = ['triage', 'moi'];\n"})
    rc, log = _run_sync(t, agent, patches, "--ra-hermes", "--chi", "kanban")
    assert rc == 1, log
    assert "PLUGIN KANBAN KHONG DUNG DUOC" in log and "dist__index.js.patch" in log
    assert stale.read_text() == "ban dang chay\n", "khong duoc ghi de khi khong dung duoc"
    assert not _home_plugin(t, "blog", "manifest.json").exists(), "hoac ca bo, hoac khong gi ca"


def test_vao_repo_never_copies_plugin_files_back_into_the_repo():
    t, agent, patches = _sandbox()
    p = _home_plugin(t, "blog", "plugin_api.py")
    p.parent.mkdir(parents=True)
    p.write_text("sua trong home\n", encoding="utf-8")
    rc, log = _run_sync(t, agent, patches, "--vao-repo", "--chi", "kanban")
    assert "--refresh-patches" in log
    assert not (t / "repo" / "plugins" / "kanban" / "dashboard").exists()


def test_refresh_patches_turns_a_home_edit_into_a_patch():
    t, agent, patches = _sandbox()
    edited = OURS["plugin_api.py"].replace("return 1", "return 1  # doi sua them")
    for hk in ("blog", "dcgr"):
        for name in kpb.PLUGIN_FILES:
            p = _home_plugin(t, hk, name)
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(edited if name == "plugin_api.py" else OURS.get(name, UPSTREAM[name]),
                         encoding="utf-8")
    rc, log = _run_sync(t, agent, patches, "--refresh-patches")
    assert rc == 0, log
    assert kpb.build(agent, patches)["plugin_api.py"]["data"].decode() == edited
    assert kpb.upstream_head(agent) in (t / "repo/plugins/kanban/UPSTREAM").read_text()
    # hai home lech nhau -> tu choi, khong doan
    _home_plugin(t, "dcgr", "plugin_api.py").write_text("khac\n", encoding="utf-8")
    rc, log = _run_sync(t, agent, patches, "--refresh-patches")
    assert rc == 1 and "KHAC NHAU" in log, log


# -------------------------------------------------------------------------
# ban va THAT trong repo
# -------------------------------------------------------------------------
def test_real_patches_still_carry_every_team_fix():
    """Mat mot ban va = mat mot dau vet trong cac dong `+` cua tep .patch."""
    for name, marks in sync.TRACE.items():
        added = "\n".join(line[1:] for line in kpb.patch_path(name).read_text(
            encoding="utf-8").splitlines() if line.startswith("+") and not line.startswith("+++"))
        for label, needle in marks:
            assert needle in added, f"{name}: ban va thieu '{label}' ({needle!r})"


def test_real_patches_touch_only_their_own_file_and_manifest_lists_all():
    m = json.loads(kpb.MANIFEST.read_text(encoding="utf-8"))
    assert sorted(m["files"]) == sorted(kpb.PLUGIN_FILES)
    assert len(m["upstream_commit"]) == 40
    assert m["upstream_commit"] in sync.FILE_UPSTREAM.read_text(encoding="utf-8")
    for name in kpb.PLUGIN_FILES:
        pp = kpb.patch_path(name)
        if not pp.exists():
            assert m["files"][name]["upstream_sha256"] == m["files"][name]["built_sha256"], name
            continue
        heads = [ln for ln in pp.read_text(encoding="utf-8").splitlines()
                 if ln.startswith(("--- ", "+++ "))]
        assert heads == [f"--- a/{name}", f"+++ b/{name}"], heads


def test_repo_no_longer_vendors_the_plugin():
    d = ROOT / "hermes" / "plugins" / "kanban" / "dashboard"
    assert not d.exists(), f"{d} quay lai — repo chi giu ban va (LOW-313)"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
