#!/usr/bin/env python3
"""kanban_plugin_build.py — dung plugin kanban = BAN GOC cua hermes-agent + BAN VA cua doi.

Vi sao (LOW-313): truoc 20/09/2026 repo chep NGUYEN `plugin_api.py` (3.053 dong)
va `dist/index.js` (205 KB) cua hermes-agent chi de giu ~90 dong sua. Ban chep cu
di ma khong ai biet: do that 20/09 thi ban goc tren may chu da tai cau truc con
1.706 dong, ban chep van la ban truoc tai cau truc va dang song nho 5 shim tuong
thich ma phia goc hen go. Sua bao mat phia goc khong toi duoc; nguoc lai
`sync_hermes --ra-hermes` chep de ban cu len moi lan chay.

Gio repo chi giu BAN VA (`hermes/plugins/kanban/patches/*.patch`, ~230 dong):

    ban goc  = git -C ~/hermes-agent show HEAD:plugins/kanban/dashboard/<tep>
    plugin   = ban goc + ban va          (git apply, KHONG fuzz)

Ban va khong ap duoc (phia goc doi dung cho doi sua) thi NEM `PluginPatchError`
— sync_hermes khong ghi gi va thoat khac 0, check_hermes bao HONG. Khong im lang.

`patches/MANIFEST.json` ghi sha256 cua ban goc luc lam ban va + sha256 ket qua:
ban goc con nguyen thi ket qua PHAI trung (chong hong tep va); ban goc da doi ma
ban va van ap sach thi dung duoc nhung `drifted` = True de nguoi chay biet ma
xem lai roi `sync_hermes.py --refresh-patches`.
"""
import hashlib
import json
import os
import subprocess
import tempfile
from pathlib import Path

import env_load

REPO = env_load.ROOT / "hermes"
HERMES_AGENT = Path(os.environ.get("HERMES_AGENT_DIR") or (Path.home() / "hermes-agent"))
UPSTREAM_DIR = "plugins/kanban/dashboard"
PATCH_DIR = REPO / "plugins" / "kanban" / "patches"
MANIFEST = PATCH_DIR / "MANIFEST.json"
PLUGIN_FILES = ["manifest.json", "plugin_api.py", "dist/index.js", "dist/style.css"]


class PluginPatchError(Exception):
    """Khong dung duoc plugin: thieu ban goc, hoac ban va khong ap duoc."""


def patch_path(name: str, patch_dir: Path = None) -> Path:
    """'dist/index.js' -> patches/dist__index.js.patch"""
    return (patch_dir or PATCH_DIR) / (name.replace("/", "__") + ".patch")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _git(args, cwd=None, data=None):
    return subprocess.run(["git", *args], cwd=cwd, input=data, capture_output=True, timeout=60)


def upstream_head(agent_dir: Path = None) -> str | None:
    r = _git(["-C", str(agent_dir or HERMES_AGENT), "rev-parse", "HEAD"])
    return r.stdout.decode().strip() if r.returncode == 0 else None


def pristine(name: str, agent_dir: Path = None, rev: str = "HEAD") -> bytes:
    """Ban goc theo GIT cua hermes-agent, khong doc working tree: ai do sua tay
    trong ~/hermes-agent thi plugin cua doi van dung tu ban da commit."""
    agent_dir = agent_dir or HERMES_AGENT
    r = _git(["-C", str(agent_dir), "show", f"{rev}:{UPSTREAM_DIR}/{name}"])
    if r.returncode != 0:
        raise PluginPatchError(
            f"khong doc duoc ban goc {name} tu {agent_dir} ({rev}): "
            + (r.stderr.decode(errors="replace").strip().splitlines() or ["?"])[-1]
            + " — dat HERMES_AGENT_DIR neu hermes-agent o cho khac")
    return r.stdout


def apply_patch(name: str, base: bytes, patch: bytes) -> bytes:
    """`base` + `patch` -> ket qua. Khong fuzz, khong ap mot phan: mot hunk lech
    la nem loi kem dong bao cua git."""
    with tempfile.TemporaryDirectory(prefix="kanban_patch_") as tmp:
        target = Path(tmp) / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base)
        r = _git(["apply", "-p1", "--whitespace=nowarn", "-"], cwd=tmp, data=patch)
        if r.returncode != 0:
            raise PluginPatchError(
                f"ban va {patch_path(name).name} KHONG ap duoc len ban goc — phia goc da doi "
                f"dung cho doi sua. Port lai bang tay roi chay sync_hermes.py --refresh-patches.\n"
                + r.stderr.decode(errors="replace").strip())
        return target.read_bytes()


def make_patch(name: str, base: bytes, result: bytes) -> bytes:
    """Ban va dua `base` thanh `result` (rong neu hai ban trung nhau)."""
    with tempfile.TemporaryDirectory(prefix="kanban_patch_") as tmp:
        for side, data in (("a", base), ("b", result)):
            p = Path(tmp) / side / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
        r = _git(["diff", "--no-index", "--no-color", "--no-prefix", f"a/{name}", f"b/{name}"],
                 cwd=tmp)
        if r.returncode not in (0, 1):                  # 1 = co khac biet
            raise PluginPatchError("git diff hong: " + r.stderr.decode(errors="replace"))
        return r.stdout


def _read_manifest(patch_dir: Path) -> dict:
    try:
        return json.loads((patch_dir / MANIFEST.name).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def build(agent_dir: Path = None, patch_dir: Path = None) -> dict:
    """{ten tep: {"data": bytes, "drifted": bool}} cho MOI tep plugin, hoac nem
    PluginPatchError. Hoac dung duoc CA BO hoac khong gi ca — plugin_api.py moi
    di voi index.js cu la mot giao dien lech nhau."""
    patch_dir = patch_dir or PATCH_DIR
    recorded = _read_manifest(patch_dir).get("files", {})
    out = {}
    for name in PLUGIN_FILES:
        base = pristine(name, agent_dir)
        pp = patch_path(name, patch_dir)
        data = apply_patch(name, base, pp.read_bytes()) if pp.exists() else base
        rec = recorded.get(name, {})
        drifted = bool(rec) and rec.get("upstream_sha256") != sha256(base)
        if rec and not drifted and rec.get("built_sha256") != sha256(data):
            raise PluginPatchError(
                f"{name}: ban goc dung ban da ghi trong {MANIFEST.name} nhung ket qua khac sha256 "
                f"da ghi — tep ban va bi sua tay? Chay sync_hermes.py --refresh-patches.")
        out[name] = {"data": data, "drifted": drifted}
    return out


def refresh(results: dict, agent_dir: Path = None, patch_dir: Path = None) -> list:
    """Lam lai ban va tu `results` = {ten tep: bytes ban DA SUA}. Tra ve danh
    sach tep ban va da ghi. Tep trung ban goc thi xoa ban va (neu co)."""
    patch_dir = patch_dir or PATCH_DIR
    patch_dir.mkdir(parents=True, exist_ok=True)
    files, written = {}, []
    for name in PLUGIN_FILES:
        base = pristine(name, agent_dir)
        result = results.get(name, base)
        pp = patch_path(name, patch_dir)
        diff = make_patch(name, base, result)
        if diff:
            pp.write_bytes(diff)
            written.append(pp)
        elif pp.exists():
            pp.unlink()
        files[name] = {"upstream_sha256": sha256(base), "built_sha256": sha256(result)}
    (patch_dir / MANIFEST.name).write_text(json.dumps(
        {"upstream_commit": upstream_head(agent_dir), "files": files}, indent=2) + "\n",
        encoding="utf-8")
    return written


def check() -> tuple:
    """(ok, dong bao) cho check_hermes/audit: ban va con ap duoc len ban dang cai khong."""
    try:
        built = build()
    except PluginPatchError as e:
        return False, str(e)
    drifted = sorted(n for n, v in built.items() if v["drifted"])
    if drifted:
        return True, ("ban va ap duoc, nhung ban goc DA DOI o: " + ", ".join(drifted)
                      + " — xem lai roi chay sync_hermes.py --refresh-patches")
    return True, "ban va ap sach len ban goc dang cai"
