#!/usr/bin/env python3
"""NOI DUY NHAT biet ruot cua hermes-agent: kanban.db va hermes_cli.

Vi sao (audit_content_team C2): truoc 09/09/2026 tri thuc ve kanban.db nam rai
o nam tep — duyet_giao_viec.py (4 cau SQL), duyet_chat.py, nhat_ky.py,
ada_chuan_bi.py — moi tep tu mo sqlite, tu viet ten bang va ten cot, tu chiu
loi mot kieu. kanban.db la bang cua TIEN TRINH KHAC: hermes co quyen doi schema
bat cu luc nao, va da doi. Khi do phai di sua nam cho, ma quen mot cho thi cho
do hong CAM (tra ve rong, khong ai bao) — dung lop loi C1 goi la "hong cam
lang". `kiem_hermes.COT_CAN` phai liet ke 20 cot chinh vi ly do do.

Nay: hermes doi thi sua MOT tep nay. Cac ham doc tra ve dict DA CHUAN HOA voi
ten khoa cua RIENG ta (id/vai/trang_thai/tieu_de/...), nen ten cot cua hermes
khong con ro ri ra ngoai; hermes doi ten cot chi cham toi cac hang MAP o duoi.

Quy uoc loi (C1 "hong phai lo"): moi ham DOC tra ve None khi khong doc duoc
kanban.db (thieu tep, sai schema, DB khoa) — KHAC voi [] / 0 nghia la "doc
duoc, khong co gi". Nguoi goi phai phan biet hai truong hop do; log o day da
kem repr(e) de con biet loi that la gi.
"""
import json
import sqlite3
import sys
from pathlib import Path

import env_load


def kanban_db() -> Path:
    """Duong dan kanban.db cua container hien tai (theo HERMES_HOME)."""
    return Path(env_load.hermes_home()) / "kanban.db"


def co_kanban() -> bool:
    """Container nay CO kanban khong.

    Tach khoi "doc khong duoc": khong co kanban.db la mot cau hinh hop le (brand
    chua bat kanban) nen nguoi goi im lang bo qua; con co tep ma doc khong duoc
    thi phai keu. Thieu phan biet nay thi vong poll ~50 giay se do mot dong log
    moi lan cho mot chuyen binh thuong."""
    return kanban_db().exists()


# --- MAP: ten cot cua hermes -> ten khoa cua ta. Hermes doi cot thi sua O DAY.
_COT_VIEC = (("id", "id"), ("assignee", "vai"), ("status", "trang_thai"),
             ("title", "tieu_de"), ("created_at", "tao_luc"),
             ("started_at", "bat_dau_luc"), ("completed_at", "xong_luc"),
             ("result", "ket_qua"), ("last_failure_error", "loi"))
_COT_LAN_CHAY = (("summary", "tom_tat"), ("error", "loi"),
                 ("status", "trang_thai"), ("metadata", "metadata"))


def _mo(db=None):
    """Ket noi CHI DOC toi kanban.db, None neu khong mo duoc.

    `mode=ro` vi day la DB cua tien trinh khac dang ghi: mo ghi la co nguy co
    khoa nham hermes. `db` de chi ro mot kanban.db KHAC container hien tai —
    theo_doi_9router quet kanban cua MOI brand, khong chi brand dang chay."""
    p = Path(db) if db else kanban_db()
    if not p.exists():
        return None
    try:
        return sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    except sqlite3.Error as e:
        print(f"[hermes] khong mo duoc {p.name}: {type(e).__name__}: {e!r}",
              file=sys.stderr)
        return None


def _hoi(cau: str, tham=(), buoc: str = "doc kanban", db=None):
    """Chay mot cau SELECT, tra ve list hang tho — None neu khong doc duoc."""
    con = _mo(db)
    if con is None:
        return None
    try:
        return list(con.execute(cau, tham))
    except sqlite3.Error as e:
        print(f"[hermes] {buoc}: {type(e).__name__}: {e!r}", file=sys.stderr)
        return None
    finally:
        con.close()


def viec(tu_ts=None, vai=None, so=None, moi_truoc=False):
    """Danh sach task da chuan hoa; None neu khong doc duoc kanban.db.

    tu_ts     chi lay task tao TU moc thoi gian nay (epoch giay)
    vai       chi lay task cua mot assignee
    so        gioi han so ban ghi
    moi_truoc sap xep moi nhat len dau (mac dinh: cu nhat truoc)
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
    hang = _hoi(cau, tuple(tham), "doc danh sach task")
    if hang is None:
        return None
    return [dict(zip([k for _, k in _COT_VIEC], h)) for h in hang]


def mot_viec(tid):
    """Task theo id, da chuan hoa. None neu khong doc duoc HOAC khong co."""
    hang = _hoi("SELECT " + ", ".join(c for c, _ in _COT_VIEC)
                + " FROM tasks WHERE id = ?", (tid,), f"doc task {tid}")
    if not hang:
        return None
    return dict(zip([k for _, k in _COT_VIEC], hang[0]))


def trang_thai(tid):
    """Trang thai hien tai cua mot task ('' neu khong ro, None neu khong doc
    duoc kanban.db)."""
    if not tid:
        return ""
    hang = _hoi("SELECT status FROM tasks WHERE id = ?", (tid,),
                f"doc trang thai {tid}")
    if hang is None:
        return None
    return hang[0][0] if hang else ""


def dem_dang_chay(tru_tid=None):
    """So task dang xep hang / dang chay (de noi "xep hang sau N viec").

    None neu khong doc duoc kanban.db — nguoi goi PHAI phan biet voi 0 ("khong
    con viec nao"), hai cau do noi hai chuyen khac han."""
    cau = "SELECT count(*) FROM tasks WHERE status IN ('ready','running')"
    tham = ()
    if tru_tid:
        cau += " AND id != ?"
        tham = (tru_tid,)
    hang = _hoi(cau, tham, "dem viec dang chay")
    return None if hang is None else hang[0][0]


def lan_chay_cuoi(tid):
    """Lan chay CUOI CUNG cua mot task, da chuan hoa:
    {tom_tat, loi, trang_thai, metadata} — metadata luon la dict.
    None neu khong doc duoc; {} neu task chua co lan chay nao."""
    if not tid:
        return {}
    hang = _hoi("SELECT " + ", ".join(c for c, _ in _COT_LAN_CHAY)
                + " FROM task_runs WHERE task_id = ? ORDER BY id DESC LIMIT 1",
                (tid,), f"doc lan chay cua {tid}")
    if hang is None:
        return None
    return _chuan_hoa_lan_chay(hang[0]) if hang else {}


def _chuan_hoa_lan_chay(hang):
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


def dem_xong_theo_vai(tu_ts, den_ts, db=None):
    """{vai: so task 'done' xong trong khoang [tu_ts, den_ts)} — None neu khong
    doc duoc. `db` de doc kanban cua brand KHAC (theo_doi_9router quet ca hai)."""
    hang = _hoi("SELECT assignee, count(*) FROM tasks WHERE status='done' "
                "AND completed_at >= ? AND completed_at < ? GROUP BY assignee",
                (int(tu_ts), int(den_ts)), "dem task xong theo vai", db=db)
    return None if hang is None else {h[0]: h[1] for h in hang}


def lan_chay_cuoi_nhieu(tids):
    """{task_id: lan_chay_cuoi} cho nhieu task trong MOT luot doc.

    nhat_ky/ada_chuan_bi duyet hang tram task mot ngay; goi lan_chay_cuoi()
    tung cai la mo/dong kanban.db hang tram lan."""
    tids = [t for t in (tids or []) if t]
    if not tids:
        return {}
    ra = {}
    for i in range(0, len(tids), 400):          # SQLite gioi han so tham so
        lo = tids[i:i + 400]
        cho = ",".join("?" * len(lo))
        hang = _hoi(
            "SELECT task_id, " + ", ".join(c for c, _ in _COT_LAN_CHAY)
            + " FROM task_runs WHERE task_id IN (" + cho + ") "
              "ORDER BY id ASC", tuple(lo), "doc lan chay hang loat")
        if hang is None:
            return None
        for h in hang:                          # ASC nen ban sau de len ban truoc
            ra[h[0]] = _chuan_hoa_lan_chay(h[1:])
    return ra
