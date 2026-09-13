#!/usr/bin/env python3
"""kiem_hermes.py — kiem cac cho content-team LE THUOC NOI BO cua hermes-agent.

Vi sao (audit 06/09/2026): dinh dang in ra cua `chat -Q`, schema tho cua
kanban.db, va ham private `kanban_swarm._activate_root_inline` deu la thu hermes
co quyen doi bat cu luc nao. Ta doc chung bang regex va SQL tho, khong qua API
nao. Truoc dot nay khong co gi bao khi chung doi — su co `-z` nuot `--continue`
(moi vai deu mo phien trang, "khong nho gi") mat may ngay moi lo ra.

CHAY SAU MOI `hermes update`:

    venv/bin/python kiem_hermes.py            # CHI DOC — an toan, khong tao gi
    venv/bin/python kiem_hermes.py --day-du   # them mot luot chat + mot task that

Mac dinh chi doc. `--day-du` moi goi LLM va TAO TASK THAT tren kanban, chi dung
khi that su can doi chieu dau-cuoi.
"""
import argparse
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import env_load                                              # noqa: E402
import hermes_adapter                                        # noqa: E402

HERMES_PY = Path.home() / "hermes-agent" / "venv" / "bin" / "python"

# Cot ta doc bang SQL THO. Thieu mot cot la nhat ky/bang dieu phoi chet cham.
COT_CAN = {
    # nhat_ky.phan_kanban + duyet_giao_viec (SELECT ... FROM tasks)
    # Tu 09/09/2026 (C2) moi cau doc kanban.db di qua hermes_adapter — danh sach
    # nay phai KHOP hermes_adapter._COT_VIEC / _COT_LAN_CHAY. Review Fable bat
    # duoc hai cot thieu: `started_at` (ada_chuan_bi tinh giay trung binh) va
    # `task_runs.id` (adapter ORDER BY id de lay lan chay cuoi) — hermes doi
    # hai cot do thi script nay van xanh ma adapter vo.
    # DAN XUAT tu adapter (ADF-r2-4): truoc day chep tay "phai KHOP" ma khong
    # test nao noi hai bang — hermes doi cot thi kiem_hermes van xanh, adapter vo.
    "tasks": [c for c, _ in hermes_adapter._COT_VIEC],
    # nhat_ky.phan_kanban + duyet_giao_viec (banh giao doc `metadata` o DAY,
    # khong phai o `tasks` — cot cua hai bang de nho nham). `id`/`task_id` la
    # cot adapter dung trong WHERE/ORDER BY, khong nam trong bang map.
    "task_runs": ["id", "task_id"] + [c for c, _ in hermes_adapter._COT_LAN_CHAY],
    # plugin kanban: stream_events
    "task_events": ["id", "task_id", "run_id", "kind", "payload", "created_at"],
}
# profiles/<vai>/state.db — mat ghep noi thu 6 (audit lượt 2, ADF-r2-3): truoc
# day theo_doi_9router va ada_chuan_bi doc thang bang SQL tho, khong ai kiem.
# Phai KHOP hermes_adapter._COT_DUNG_MODEL / _COT_PHIEN.
COT_CAN_STATE = {
    "session_model_usage": list(hermes_adapter._COT_DUNG_MODEL),
    "sessions": list(hermes_adapter._COT_PHIEN),
}
# Co CLI ta truyen cho `hermes chat`. `-z` tung duoc xu ly TRUOC va thoat luon
# nen `--continue` bi bo qua im lang — do la ly do danh sach nay ton tai.
CO_CHAT = ["-c", "--create-if-missing", "--no-restore-cwd", "-Q", "-q"]


def _home_kanban() -> list:
    ra = []
    for ten in ("blog", "dcgr"):
        db = Path.home() / f".hermes-{ten}" / "kanban.db"
        if db.exists():
            ra.append((ten, db))
    return ra


def _kiem_bang(ten: str, db: Path, can: dict) -> list:
    """So cot cua mot tep sqlite voi bang `can` {bang: [cot]}. Tra list loi."""
    loi = []
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    except sqlite3.Error as e:
        return [f"{ten}: khong mo duoc {db}: {e}"]
    for bang, cot in can.items():
        try:
            co = {r[1] for r in con.execute(f"PRAGMA table_info({bang})")}
        except sqlite3.Error as e:
            loi.append(f"{ten}: doc schema {bang} loi: {e}")
            continue
        if not co:
            loi.append(f"{ten}: KHONG con bang `{bang}`")
            continue
        thieu = [c for c in cot if c not in co]
        if thieu:
            loi.append(f"{ten}: bang `{bang}` thieu cot {', '.join(thieu)}")
    con.close()
    return loi


def kiem_cot() -> list:
    loi = []
    for ten, db in _home_kanban():
        loi += _kiem_bang(ten, db, COT_CAN)
        # state.db cua tung profile cung home (ADF-r2-3): kiem MOT profile la du
        # vi schema do hermes tao giong nhau, nhung profile chua chay lan nao thi
        # chua co tep — lay tep dau tien co that.
        for sdb in sorted(db.parent.glob("profiles/*/state.db"))[:1]:
            loi += _kiem_bang(f"{ten}/{sdb.parent.name}", sdb, COT_CAN_STATE)
    if not _home_kanban():
        loi.append("khong thay kanban.db o home nao (chay tren may chu?)")
    return loi


def kiem_co_chat() -> list:
    """Cac co CLI ta truyen co con trong `hermes chat --help` khong."""
    if not HERMES_PY.exists():
        return [f"khong thay python cua hermes: {HERMES_PY}"]
    try:
        r = subprocess.run([str(HERMES_PY), "-m", "hermes_cli.main", "chat", "--help"],
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        return [f"khong chay duoc `hermes chat --help`: {type(e).__name__}: {e}"]
    if r.returncode != 0:
        return [f"`hermes chat --help` thoat {r.returncode}: {(r.stderr or '')[-200:]}"]
    tro_giup = r.stdout + r.stderr
    return [f"co `{c}` khong con trong `hermes chat --help`" for c in CO_CHAT
            if c not in tro_giup]


def kiem_swarm() -> list:
    """Ham private cua kanban_swarm ma bang_den goi."""
    if not HERMES_PY.exists():
        return [f"khong thay python cua hermes: {HERMES_PY}"]
    ma = ("import hermes_cli.kanban_swarm as ks\n"
          "thieu = [t for t in ('_activate_root_inline',) if not hasattr(ks, t)]\n"
          "print('THIEU:' + ','.join(thieu) if thieu else 'OK')\n")
    try:
        r = subprocess.run([str(HERMES_PY), "-c", ma], capture_output=True,
                           text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        return [f"khong import duoc kanban_swarm: {type(e).__name__}: {e}"]
    out = (r.stdout or "").strip()
    if r.returncode != 0:
        return [f"import kanban_swarm loi: {(r.stderr or '')[-200:]}"]
    return [] if out == "OK" else [f"kanban_swarm {out}"]


def main() -> int:
    ap = argparse.ArgumentParser(description="Kiem cac cho le thuoc noi bo hermes")
    ap.add_argument("--day-du", action="store_true",
                    help="them mot luot chat that va MOT TASK THAT (ton LLM, tao state)")
    a = ap.parse_args()
    env_load.load()

    tat_ca = []
    for ten, ham in (("schema kanban.db", kiem_cot),
                     ("co CLI cua `hermes chat`", kiem_co_chat),
                     ("ham private kanban_swarm", kiem_swarm)):
        loi = ham()
        print(f"{'OK  ' if not loi else 'HONG'}  {ten}")
        for d in loi:
            print(f"        - {d}")
        tat_ca += loi

    if a.day_du:
        print("\n--- day du: mot luot chat that ---")
        r = subprocess.run([str(HERMES_PY), "-m", "hermes_cli.main", "chat",
                            "-c", "kiem-hermes", "--create-if-missing",
                            "--no-restore-cwd", "-Q", "-q", "Tra loi dung mot tu: OK"],
                           capture_output=True, text=True, timeout=600)
        print((r.stdout or "")[-300:])
        if r.returncode != 0:
            tat_ca.append(f"chat roundtrip thoat {r.returncode}")

    print()
    if tat_ca:
        print(f"[HONG] {len(tat_ca)} cho le thuoc da doi — sua truoc khi chay tiep.")
        return 1
    print("[OK] moi cho le thuoc noi bo hermes van dung nhu ta gia dinh.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
