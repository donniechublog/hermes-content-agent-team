#!/usr/bin/env python3
"""NOI DUY NHAT biet ruot cua hermes-agent: kanban.db va hermes_cli.

Vi sao (audit_content_team C2): truoc 09/09/2026 tri thuc ve kanban.db nam rai
o nam tep — approve_dispatch.py (4 cau SQL), approve_chat.py, journal.py,
ada_prepare.py — moi tep tu mo sqlite, tu viet ten bang va ten cot, tu chiu
loi mot kieu. kanban.db la bang cua TIEN TRINH KHAC: hermes co quyen doi schema
bat cu luc nao, va da doi. Khi do phai di sua nam cho, ma quen mot cho thi cho
do hong CAM (tra ve rong, khong ai bao) — dung lop loi C1 goi la "hong cam
lang". `check_hermes.COLUMN_CAN` phai liet ke 20 cot chinh vi ly do do.

Nay: hermes doi thi sua MOT tep nay. Cac ham doc tra ve dict DA CHUAN HOA voi
ten khoa cua RIENG ta (id/assignee/status/title/...), nen ten cot cua hermes
khong con ro ri ra ngoai; hermes doi ten cot chi cham toi cac hang MAP o duoi.

Quy uoc loi (C1 "hong phai lo"): moi ham DOC tra ve None khi khong doc duoc
kanban.db (thieu tep, sai schema, DB khoa) — KHAC voi [] / 0 nghia la "doc
duoc, khong co gi". Nguoi goi phai phan biet hai truong hop do; log o day da
kem repr(e) de con biet loi that la gi.
"""
import json
import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import env_load


def kanban_db() -> Path:
    """Duong dan kanban.db cua container hien tai (theo HERMES_HOME)."""
    return Path(env_load.hermes_home()) / "kanban.db"


def has_kanban() -> bool:
    """Container nay CO kanban khong.

    Tach khoi "doc khong duoc": khong co kanban.db la mot cau hinh hop le (brand
    chua bat kanban) nen nguoi goi im lang bo qua; con co tep ma doc khong duoc
    thi phai keu. Thieu phan biet nay thi vong poll ~50 giay se do mot dong log
    moi lan cho mot chuyen binh thuong."""
    return kanban_db().exists()


# --- MAP: ten cot cua hermes -> ten khoa cua ta. Hermes doi cot thi sua O DAY.
# Khoa cua ta dung lai dung ten cot kanban cua hermes (LOW-236, bang
# docs/tu_dien_ten/runtime_dicts_v2.json); rieng last_failure_error -> error, id run -> run_id.
_COT_VIEC = (("id", "id"), ("assignee", "assignee"), ("status", "status"),
             ("title", "title"), ("created_at", "created_at"),
             ("started_at", "started_at"), ("completed_at", "completed_at"),
             ("result", "result"), ("last_failure_error", "error"))
_COT_LAN_CHAY = (("summary", "summary"), ("error", "error"),
                 ("status", "status"), ("metadata", "metadata"),
                 ("id", "run_id"))      # id de bao MOI lan timed_out dung mot lan


def _open(db=None):
    """Ket noi CHI DOC toi kanban.db, None neu khong mo duoc.

    `mode=ro` vi day la DB cua tien trinh khac dang ghi: mo ghi la co nguy co
    khoa nham hermes. `db` de chi ro mot kanban.db KHAC container hien tai —
    monitor_9router quet kanban cua MOI brand, khong chi brand dang chay."""
    p = Path(db) if db else kanban_db()
    if not p.exists():
        return None
    try:
        return sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    except sqlite3.Error as e:
        print(f"[hermes] khong mo duoc {p.name}: {type(e).__name__}: {e!r}",
              file=sys.stderr)
        return None


def _ask(cau: str, tham=(), buoc: str = "doc kanban", db=None):
    """Chay mot cau SELECT, tra ve list hang tho — None neu khong doc duoc."""
    con = _open(db)
    if con is None:
        return None
    try:
        return list(con.execute(cau, tham))
    except sqlite3.Error as e:
        print(f"[hermes] {buoc}: {type(e).__name__}: {e!r}", file=sys.stderr)
        return None
    finally:
        con.close()


# --- state.db cua TUNG PROFILE (profiles/<vai>/state.db) -----------------------
# Mat ghep noi thu 6 voi hermes (audit lượt 2, ADF-r2-3): monitor_9router va
# ada_prepare tung doc thang bang `session_model_usage` / `sessions` bang SQL
# tho o hai tep, adapter khong biet, check_hermes khong kiem — hermes doi mot
# cot la nhat ky va brief cua Ada hong cam SAU `hermes update`. Cot dung o day
# phai KHOP check_hermes.COLUMN_CAN["session_model_usage"] / ["sessions"].
_COT_DUNG_MODEL = ("model", "api_call_count", "input_tokens", "output_tokens",
                   "cache_read_tokens", "reasoning_tokens", "session_id", "last_seen")
_COT_PHIEN = ("title", "tool_call_count", "input_tokens", "api_call_count", "started_at")


def state_db_each_profile(home=None):
    """Moi profiles/*/state.db duoi mot HERMES_HOME (mac dinh: container hien tai)."""
    goc = Path(home) if home else Path(env_load.hermes_home())
    return sorted(goc.glob("profiles/*/state.db"))


def use_by_model(state_db, tu_ts, den_ts):
    """Tong token/api theo model cua mot profile trong [tu_ts, den_ts) —
    list dict {model, api, in, out, cache, reasoning, sessions}; [] neu khong co;
    None neu khong doc duoc (C1: hong moi truong phai lo ra, khac voi rong)."""
    hang = _ask("select model, sum(api_call_count), sum(input_tokens), sum(output_tokens), "
                "sum(cache_read_tokens), sum(reasoning_tokens), count(distinct session_id) "
                "from session_model_usage where last_seen >= ? and last_seen < ? group by model",
                (tu_ts, den_ts), buoc=f"doc session_model_usage {Path(state_db).parent.name}",
                db=state_db)
    if hang is None:
        return None
    return [{"model": m, "api": api or 0, "in": i or 0, "out": o or 0, "cache": c or 0,
             "reasoning": r or 0, "sessions": p or 0} for m, api, i, o, c, r, p in hang]


def summary_session(state_db, tu_ts, so_top=2):
    """Dem phien cua mot profile tu `tu_ts`: dict {sessions, tool, input, api, top}
    (top = [(tieu_de, tool, input)] so_top phien nang nhat); None neu khong doc duoc."""
    ten = Path(state_db).parent.name
    tong = _ask("select count(*), coalesce(sum(tool_call_count),0), coalesce(sum(input_tokens),0), "
                "coalesce(sum(api_call_count),0) from sessions where started_at>=?",
                (tu_ts,), buoc=f"doc sessions {ten}", db=state_db)
    if tong is None:
        return None
    top = _ask("select coalesce(title,''), tool_call_count, input_tokens from sessions "
               "where started_at>=? order by input_tokens desc limit ?",
               (tu_ts, so_top), buoc=f"doc sessions top {ten}", db=state_db)
    if top is None:
        return None
    n, tools, inp, api = tong[0]
    return {"sessions": n, "tool": tools, "input": inp, "api": api,
            "top": [(t[:40], tc, it) for t, tc, it in top]}


def create_task(title, assignee, body, parent=None, max_runtime="25m"):
    """Tao mot task kanban qua CLI cua hermes. Tra (task_id, loi).

    Day la noi DUY NHAT biet hinh dang lenh `hermes kanban create` — co nao,
    chay o dau, doc ket qua kieu gi. Nguoi goi chi biet "tao task cho vai nay".

    `parent` la mot id hoac danh sach id (Miles co hai cha: task Dre + the goc
    bang den). `--parent` lap lai duoc; None/rong thi bo qua.
    """
    home = str(env_load.hermes_home())
    # --workspace dir:<co dinh>: mac dinh `scratch` tao thu muc moi moi task
    # (kanban/workspaces/t_xxx) va Hermes in "Current working directory: ..."
    # vao GIUA system prompt -> 37% cuoi prompt (skills, memory) khong bao gio
    # trung cache giua hai task cung vai. Do 05/09: 2 task carousel cach 5 phut
    # chi khac dung dong nay. Thu muc co dinh, khong phai git repo (tranh Hermes
    # bat "coding posture"); script cua vai deu dung duong dan tuyet doi.
    ws = Path(home) / "kanban" / "workspaces" / "co-dinh"
    try:
        ws.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        return None, f"khong tao duoc workspace {ws}: {e!r}"
    args = [str(env_load.HERMES_PY), "-m", "hermes_cli.main", "kanban", "create", title,
            "--assignee", assignee, "--max-runtime", max_runtime, "--json",
            "--workspace", f"dir:{ws}", "--body", body]
    for _cha in ([parent] if isinstance(parent, str) else (parent or [])):
        if _cha:
            args += ["--parent", _cha]
    try:
        r = subprocess.run(args, cwd=str(env_load.HERMES_DIR),
                           env=dict(os.environ, HERMES_HOME=home),
                           capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError) as e:
        return None, f"{type(e).__name__}: {e!r}"
    if r.returncode != 0:
        return None, (r.stderr[-300:] or r.stdout[-300:])
    try:
        return json.loads(r.stdout)["id"], None
    except (ValueError, KeyError, TypeError):
        return None, r.stdout[-300:]


def job(tu_ts=None, vai=None, so=None, moi_truoc=False, db=None):
    """Danh sach task da chuan hoa; None neu khong doc duoc kanban.db.

    tu_ts     chi lay task tao TU moc thoi gian nay (epoch giay)
    vai       chi lay task cua mot assignee
    so        gioi han so ban ghi
    moi_truoc sap xep moi nhat len dau (mac dinh: cu nhat truoc)
    db        kanban.db cua home KHAC container hien tai (audit_cron soat ca hai brand)
    """
    dieu_kien, tham = [], []
    if tu_ts is not None:
        dieu_kien.append("created_at >= ?")
        tham.append(int(tu_ts))
    if vai:
        dieu_kien.append("assignee = ?")
        tham.append(vai)
    cau = "SELECT " + ", ".join(c for c, _ in _COT_VIEC) + " FROM tasks"
    if dieu_kien:
        cau += " WHERE " + " AND ".join(dieu_kien)
    cau += " ORDER BY created_at " + ("DESC" if moi_truoc else "ASC")
    if so is not None:
        cau += " LIMIT ?"                       # tham so hoa, khong noi chuoi
        tham.append(int(so))
    hang = _ask(cau, tuple(tham), "doc danh sach task", db=db)
    if hang is None:
        return None
    return [dict(zip([k for _, k in _COT_VIEC], h)) for h in hang]


def one_job(tid):
    """Task theo id, da chuan hoa. None neu khong doc duoc HOAC khong co."""
    hang = _ask("SELECT " + ", ".join(c for c, _ in _COT_VIEC)
                + " FROM tasks WHERE id = ?", (tid,), f"doc task {tid}")
    if not hang:
        return None
    return dict(zip([k for _, k in _COT_VIEC], hang[0]))


def status(tid):
    """Trang thai hien tai cua mot task ('' neu khong ro, None neu khong doc
    duoc kanban.db)."""
    if not tid:
        return ""
    hang = _ask("SELECT status FROM tasks WHERE id = ?", (tid,),
                f"doc trang thai {tid}")
    if hang is None:
        return None
    return hang[0][0] if hang else ""


def count_form_run(tru_tid=None):
    """So task dang xep hang / dang chay (de noi "xep hang sau N viec").

    None neu khong doc duoc kanban.db — nguoi goi PHAI phan biet voi 0 ("khong
    con viec nao"), hai cau do noi hai chuyen khac han."""
    cau = "SELECT count(*) FROM tasks WHERE status IN ('ready','running')"
    tham = ()
    if tru_tid:
        cau += " AND id != ?"
        tham = (tru_tid,)
    hang = _ask(cau, tham, "dem viec dang chay")
    return None if hang is None else hang[0][0]


def writer_queue(slugs):
    """{slug: (waiting or running task count, created_at of the newest task)}; None
    when kanban.db is unreadable. `blocked` is not counted: such a task waits on the
    boss and does not hold the role's slot."""
    slugs = tuple(slugs)
    if not slugs:
        return {}
    sql = ("SELECT assignee, SUM(CASE WHEN status IN ('todo','scheduled','ready','running') "
           "THEN 1 ELSE 0 END), MAX(created_at) FROM tasks WHERE assignee IN ("
           + ",".join("?" * len(slugs)) + ") GROUP BY assignee")
    rows = _ask(sql, slugs, "count writer queue")
    if rows is None:
        return None
    queue = {slug: (0, None) for slug in slugs}
    queue.update({assignee: (int(count or 0), newest) for assignee, count, newest in rows})
    return queue


def last_run(tid):
    """Lan chay CUOI CUNG cua mot task, da chuan hoa:
    {summary, error, status, metadata, run_id} — metadata luon la dict.
    None neu khong doc duoc; {} neu task chua co lan chay nao."""
    if not tid:
        return {}
    hang = _ask("SELECT " + ", ".join(c for c, _ in _COT_LAN_CHAY)
                + " FROM task_runs WHERE task_id = ? ORDER BY id DESC LIMIT 1",
                (tid,), f"doc lan chay cua {tid}")
    if hang is None:
        return None
    return _standard_ify_run(hang[0]) if hang else {}


def _standard_ify_run(hang):
    """Mot hang task_runs -> dict cua ta; `metadata` LUON la dict.

    hermes ghi metadata la chuoi JSON, nhung da tung ghi ca NULL lan chuoi
    rong; nguoi goi khong nen phai biet dieu do."""
    ra = dict(zip([k for _, k in _COT_LAN_CHAY], hang))
    md = ra.get("metadata")
    if isinstance(md, (str, bytes)):
        try:
            md = json.loads(md)
        except (ValueError, TypeError):
            md = {}
    ra["metadata"] = md if isinstance(md, dict) else {}
    return ra



# --- LAN CHAY HIEN TAI + NHIP THO (LOW-23, 12/09/2026) ------------------------
# `tasks.started_at` la moc LAN DAU task tung chay, hermes KHONG bao gio cap nhat
# (`COALESCE(started_at, ?)`), va chinh bo quet timeout cua hermes ghi: "Runtime
# is per attempt, not lifetime-of-task". Do "chay bao lau" phai lay tu
# task_runs cua run dang mo; "con song khong" lay tu last_heartbeat_at/worker_pid
# — ca hai deu co san trong kanban.db, truoc day khong ai SELECT.

def run_start(db=None):
    """{task_id: (started_at cua run dang mo, run_id)} cho moi task 'running'.
    {} neu khong co; None neu khong doc duoc."""
    hang = _ask("SELECT t.id, r.started_at, r.id FROM tasks t "
                "JOIN task_runs r ON r.id = t.current_run_id "
                "WHERE t.status = 'running'", (), "doc moc lan chay", db=db)
    if hang is None:
        return None
    return {h[0]: (h[1], h[2]) for h in hang}


def heartbeat(tids, db=None):
    """{task_id: (last_heartbeat_at, worker_pid)} — {} neu khong co; None neu
    khong doc duoc (kanban.db cu chua co cot thi cung ve None, nguoi goi coi
    nhu 'khong biet', khong phai 'da chet')."""
    tids = [t for t in (tids or []) if t]
    if not tids:
        return {}
    ra = {}
    for i in range(0, len(tids), 400):
        lo = tids[i:i + 400]
        hang = _ask("SELECT id, last_heartbeat_at, worker_pid FROM tasks "
                    "WHERE id IN (" + ",".join("?" * len(lo)) + ")",
                    tuple(lo), "doc nhip tho", db=db)
        if hang is None:
            return None
        for h in hang:
            ra[h[0]] = (h[1], h[2])
    return ra


def pid_alive(pid) -> bool | None:
    """True/False neu kiem duoc; None neu khong co pid. Cung may voi hermes
    (approve_service chay canh gateway) nen `os.kill(pid, 0)` co nghia."""
    if not pid:
        return None
    try:
        os.kill(int(pid), 0)
    except (ProcessLookupError, ValueError):
        return False
    except PermissionError:
        return True
    return True

def worker_run_state(tid, run_id, db=None):
    """Trang thai de biet scope worker `hermes-worker-kanban-<tid>-run-<run_id>`
    con viec khong (LOW-126): {status, current_run_id, run_ended_at} —
    run_ended_at la ended_at cua DUNG run do (None neu run chua dong).
    {} neu task khong co trong kanban.db nay; None neu khong doc duoc."""
    hang = _ask("SELECT t.status, t.current_run_id, r.ended_at FROM tasks t "
                "LEFT JOIN task_runs r ON r.id = ? AND r.task_id = t.id "
                "WHERE t.id = ?", (int(run_id), tid), f"doc run {tid}/{run_id}", db=db)
    if hang is None:
        return None
    if not hang:
        return {}
    st, cur, ended = hang[0]
    return {"status": st, "current_run_id": cur, "run_ended_at": ended}


def count_done_by_role(tu_ts, den_ts, db=None):
    """{vai: so task 'done' xong trong khoang [tu_ts, den_ts)} — None neu khong
    doc duoc. `db` de doc kanban cua brand KHAC (monitor_9router quet ca hai)."""
    hang = _ask("SELECT assignee, count(*) FROM tasks WHERE status='done' "
                "AND completed_at >= ? AND completed_at < ? GROUP BY assignee",
                (int(tu_ts), int(den_ts)), "dem task xong theo vai", db=db)
    return None if hang is None else {h[0]: h[1] for h in hang}


def last_run_many(tids):
    """{task_id: last_run} cho nhieu task trong MOT luot doc.

    journal/ada_prepare duyet hang tram task mot ngay; goi last_run()
    tung cai la mo/dong kanban.db hang tram lan."""
    tids = [t for t in (tids or []) if t]
    if not tids:
        return {}
    ra = {}
    for i in range(0, len(tids), 400):          # SQLite gioi han so tham so
        lo = tids[i:i + 400]
        cho = ",".join("?" * len(lo))
        hang = _ask(
            "SELECT task_id, " + ", ".join(c for c, _ in _COT_LAN_CHAY)
            + " FROM task_runs WHERE task_id IN (" + cho + ") "
              "ORDER BY id ASC", tuple(lo), "doc lan chay hang loat")
        if hang is None:
            return None
        for h in hang:                          # ASC nen ban sau de len ban truoc
            ra[h[0]] = _standard_ify_run(h[1:])
    return ra
