#!/usr/bin/env python3
"""Stop scope worker kanban MO COI — task da roi 'running' ma scope van song (LOW-126).

VI SAO. Dispatcher hermes boc moi worker bang `systemd-run --user --scope`
(`hermes-worker-kanban-<task>-run-<n>.scope`). Scope chi ket thuc khi tien trinh
CUOI CUNG trong cgroup chet, va hermes khong bao gio `systemctl stop` no. Tool
browser sinh `browser_harness.daemon` tu tach khoi worker nhung van o trong
cgroup, khong co idle timeout -> 12/09/2026 scope t_7fb5375f song 2 ngay sau khi
task done, giu `bu-default.sock` tro vao Chromium da chet.

VI SAO O DAY, KHONG VA HERMES. ~/hermes-agent tren may chu la clone sach cua
upstream; va dispatcher la fork phai va lai sau moi lan `hermes update` va phai
restart ca hai gateway. Quet tu ngoai chi can doc kanban.db (qua hermes_adapter).

KHI NAO STOP. Chi khi tim thay task trong kanban.db cua mot brand VA run cua
scope da dong (ended_at) tu hon `--grace` giay — worker vua kanban_complete con
vai giay ghi log/thoat, khong giet ngang. Khong doc duoc DB, khong thay task,
run chua dong: bo qua (khong biet thi khong giet).

DAEMON BROWSER DUNG CHUNG (17/09/2026). Moi worker goi browser deu dung session
`default` (`~/.config/browser-harness/runtime/bu-default.sock`, chung ca blog +
dcgr). Daemon nam trong scope cua worker DA SPAWN no; worker sau chi attach. Stop
scope do khi worker khac dang chay = giet browser cua nguoi ta. Nen scope nao dang
chua PID trong `bu-default.pid` chi stop khi KHONG con task 'running' nao khac o
ca hai brand (khong doc duoc kanban thi giu). Session ten rieng (vd `bu-dre48ca`)
khong ai dung chung -> stop nhu thuong.

Dung:
    venv/bin/python worker_scope_sweep.py              # quet + stop
    venv/bin/python worker_scope_sweep.py --dry-run    # chi in
Chay dinh ky: hermes/systemd/worker-scope-sweep.timer (5 phut).
"""
import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

import hermes_adapter as ha

SCOPE_PATTERN = re.compile(r"^hermes-worker-kanban-(t_[0-9a-f]+)-run-(\d+)\.scope$")
BROWSER_RUNTIME = Path.home() / ".config" / "browser-harness" / "runtime"
SHARED_BROWSER_PID = "bu-default.pid"


def kanban_homes():
    """[(brand, kanban.db)] cua moi home co kanban tren may nay."""
    return [(p.name.removeprefix(".hermes-"), p / "kanban.db")
            for p in sorted(Path.home().glob(".hermes-*")) if (p / "kanban.db").exists()]


def list_scopes(run=subprocess.run):
    """[(unit, task_id, run_id)] cho moi scope worker kanban dang active.
    None neu systemctl loi (khac [] = khong co scope nao)."""
    try:
        r = run(["systemctl", "--user", "list-units", "--type=scope", "--state=active",
                 "--no-legend", "--plain", "hermes-worker-kanban-*"],
                capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError) as e:
        print(f"[LOI] systemctl list-units: {e!r}", file=sys.stderr)
        return None
    if r.returncode != 0:
        print(f"[LOI] systemctl list-units rc={r.returncode}: {r.stderr[-200:]}", file=sys.stderr)
        return None
    ra = []
    for dong in r.stdout.splitlines():
        unit = dong.split()[0] if dong.split() else ""
        m = SCOPE_PATTERN.match(unit)
        if m:
            ra.append((unit, m.group(1), int(m.group(2))))
    return ra


def decide(tid, run_id, homes, now, grace):
    """(stop?, ly do). Mot task id chi nam o mot brand; khong thay o dau thi giu."""
    khong_doc = []
    for brand, db in homes:
        st = ha.worker_run_state(tid, run_id, db=db)
        if st is None:
            khong_doc.append(brand)
            continue
        if not st:
            continue
        if st["trang_thai"] == "running" and st["run_hien_tai"] == run_id:
            return False, f"{brand}: dang chay"
        ended = st["run_ket_thuc"]
        if ended is None:
            return False, f"{brand}: run {run_id} chua dong (task {st['trang_thai']})"
        if now - ended < grace:
            return False, f"{brand}: run dong {int(now - ended)}s truoc, cho du {grace}s"
        return True, f"{brand}: task {st['trang_thai']}, run {run_id} dong {int(now - ended)}s truoc"
    if khong_doc:
        return False, f"khong doc duoc kanban {','.join(khong_doc)}"
    return False, "khong thay task o brand nao"


def shared_browser_daemon_unit(runtime=BROWSER_RUNTIME, proc=Path("/proc")):
    """Scope worker kanban dang chua daemon browser session `default`, hoac None
    (khong co pid file, PID da chet, hay daemon khong nam trong scope worker nao)."""
    try:
        pid = int((runtime / SHARED_BROWSER_PID).read_text().strip())
        cgroup = (proc / str(pid) / "cgroup").read_text()
    except (OSError, ValueError):
        return None
    for line in cgroup.splitlines():
        unit = line.rsplit("/", 1)[-1]
        if SCOPE_PATTERN.match(unit):
            return unit
    return None


def other_running_tasks(tid, homes):
    """["brand/task"] dang 'running' ngoai `tid`; None neu co brand khong doc duoc."""
    others = []
    for brand, db in homes:
        running = ha.run_start(db=db)
        if running is None:
            return None
        others += [f"{brand}/{t}" for t in sorted(running) if t != tid]
    return others


def stop(unit, run=subprocess.run):
    try:
        r = run(["systemctl", "--user", "stop", unit], capture_output=True, text=True, timeout=60)
    except (OSError, subprocess.SubprocessError) as e:
        return f"{e!r}"
    return None if r.returncode == 0 else f"rc={r.returncode}: {r.stderr[-200:]}"


def main(argv=None, run=subprocess.run, homes=None, now=None,
         find_daemon_unit=shared_browser_daemon_unit):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--grace", type=int, default=300, help="giay sau khi run dong moi stop")
    a = ap.parse_args(argv)
    scopes = list_scopes(run)
    if scopes is None:
        return 2
    homes = kanban_homes() if homes is None else homes
    now = time.time() if now is None else now
    daemon_unit = find_daemon_unit()
    hong = 0
    for unit, tid, run_id in scopes:
        co, ly_do = decide(tid, run_id, homes, now, a.grace)
        if co and unit == daemon_unit:
            others = other_running_tasks(tid, homes)
            if others is None:
                co, ly_do = False, "chua daemon browser bu-default, khong doc duoc kanban de biet con ai dung"
            elif others:
                co, ly_do = False, (f"chua daemon browser bu-default dung chung, con {len(others)} task "
                                    f"running ({', '.join(others[:3])})")
            else:
                ly_do += "; kem daemon browser bu-default, khong con task running"
        if not co:
            print(f"giu  {unit}: {ly_do}")
            continue
        if a.dry_run:
            print(f"[DRY] stop {unit}: {ly_do}")
            continue
        loi = stop(unit, run)
        if loi:
            hong += 1
            print(f"[LOI] stop {unit}: {loi}", file=sys.stderr)
        else:
            print(f"stop {unit}: {ly_do}")
    return 1 if hong else 0


if __name__ == "__main__":
    sys.exit(main())
