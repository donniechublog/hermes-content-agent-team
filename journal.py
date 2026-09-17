#!/usr/bin/env python3
"""Nhat ky lam viec hang ngay — gom tu cac nguon da co, khong nho LLM tom tat.

Truoc day muon biet "hom qua doi lam gi" phai mo bon noi: state/finn_candidates_*
xem diem cham, kanban.db xem task nao duoc tao, profiles/*/sessions/ xem agent
nghi gi, roi cuon Telegram xem Ong Chu chon so may. File nay ghep san lai.

HAI PHAN, tach bach co chu y:

  - Phan TU DONG: doc lai tu executions.db, kanban.db, state/*.json, git log.
    Sinh lai duoc bat cu luc nao, chay lai khong hong gi.
  - Phan GHI CHU TAY: van de gap, bug o dau, sua the nao. Thu nay khong suy ra
    duoc tu du lieu. Luu rieng o notes.jsonl (chi noi them, khong sua) roi
    ghep vao khi dung trang. Nho vay sinh lai phan tu dong KHONG BAO GIO xoa
    mat ghi chu — day la ly do khong luu thang vao tep .md.

Dung:
    venv/bin/python journal.py                          # dung trang hom nay
    venv/bin/python journal.py --ngay 2026-08-21        # dung trang ngay khac
    venv/bin/python journal.py --note "Telegram dinh chu, do agent nhet bao cao
        vao mot dong shell" --loai bug
    venv/bin/python journal.py --note "Vá publish.py: doi <br> thanh xuong dong"
        --loai fix
"""
import argparse
import functools
import json
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import env_load
import hermes_adapter
import state_paths

ROOT = env_load.ROOT
HERMES = env_load.hermes_home()
DIRECTORY = env_load.state_dir() / state_paths.JOURNAL_DIR
NOTES = DIRECTORY / state_paths.JOURNAL_NOTES_FILE
VN = timezone(timedelta(hours=7))

TYPE = {"bug": "🐞 Bug", "fix": "🔧 Đã sửa", "van-de": "⚠️ Vấn đề",
        "ghi-chu": "📝 Ghi chú", "quyet-dinh": "🎯 Quyết định"}


def _hours_vn(v) -> datetime | None:
    """Chuan hoa moc thoi gian ve gio VN. Nguon tron ISO va epoch nen phai do."""
    if v in (None, ""):
        return None
    try:
        if isinstance(v, (int, float)) or str(v).isdigit():
            return datetime.fromtimestamp(float(v), timezone.utc).astimezone(VN)
        s = str(v).replace("Z", "+00:00")
        d = datetime.fromisoformat(s)
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return d.astimezone(VN)
    except Exception:                                        # noqa: BLE001
        return None


def _within_date(v, ngay: str) -> bool:
    d = _hours_vn(v)
    return bool(d) and d.strftime("%Y-%m-%d") == ngay


def _open(db: Path):
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True) if db.exists() else None


# Cac loi doc DB gap trong lan dung trang nay — in ra CUOI trang thay vi lam
# hong ca trang.
ERROR_READ = []


def _bear_error_db(khi_loi):
    """Boc mot phan_* doc SQLite cua hermes: schema doi la GHI RA, khong chet.

    Ba ham duoi doc thang bang noi bo cua hermes-agent (`executions`, `tasks`,
    `task_runs`) bang SQL tho. Do la bang cua tien trinh KHAC, hermes co quyen
    doi bat cu luc nao — va da tung doi (`_heal_session_model_usage_pk` trong
    hermes_state_schema). Truoc 06/09/2026 khong ai boc, ma cron lai chay
    `>/dev/null 2>&1`, nen mot lan `hermes update` doi ten cot la nhat ky chet
    IM LANG: khong trang, khong dong log, khong ai biet cho toi khi can tra cuu.
    """
    def bao(f):
        @functools.wraps(f)
        def trong(*a, **k):
            try:
                return f(*a, **k)
            except (sqlite3.Error, OSError, ValueError) as e:
                # OSError/ValueError (C-r2-7): part_finn/part_model doc JSON tho —
                # mot tep finn_candidates cut la ca nhat ky ngay do khong sinh,
                # dung kieu "chet cam" 06/09 ma decorator nay sinh ra de chan.
                loi = f"{f.__name__}: {type(e).__name__}: {e!r}"
                ERROR_READ.append(loi)
                print(f"[nhat_ky] loi doc DB — {loi}", file=sys.stderr)
                return khi_loi
        return trong
    return bao


# ---------- cac nguon ----------

# Trang thai hermes dat cho luot da nhan nhung chua xong. Nhat ky chay 23:00 UTC
# cung dot voi cac viec ngay khac, doc trung luc chung con dang chay - khong phai loi.
FORM_RUN = ("running", "claimed", "started", "pending")

# Viec chay tren nguong nay trong mot ngay chi in mot dong tong, khong ke tung luot.
EXCESS = 6


def _gather_by_job(c: list) -> list:
    """Gom cac luot theo ten viec, giu thu tu luot dau tien xuat hien."""
    nhom = {}
    for x in c:
        nhom.setdefault(x["ten"], []).append(x)
    return list(nhom.items())


@_bear_error_db([])
def part_cron(ngay: str) -> list:
    con = _open(HERMES / "cron" / "executions.db")
    if not con:
        return []
    ten = {}
    jp = HERMES / "cron" / "jobs.json"
    if jp.exists():
        ten = {j["id"]: j["name"] for j in json.loads(jp.read_text(encoding="utf-8"))["jobs"]}
    ra = []
    for jid, st, s, f, err in con.execute(
            "select job_id,status,started_at,finished_at,error from executions"):
        if not _within_date(s, ngay):
            continue
        a, b = _hours_vn(s), _hours_vn(f)
        ra.append({"ten": ten.get(jid, jid), "gio": a.strftime("%H:%M") if a else "?",
                   "giay": round((b - a).total_seconds(), 1) if a and b else None,
                   "trang_thai": st, "loi": err})
    ra.sort(key=lambda x: x["gio"])
    return ra


@_bear_error_db([])
def part_kanban(ngay: str) -> list:
    # Doc qua hermes_adapter (C2): kanban.db la bang cua hermes, chi mot tep
    # duoc biet schema cua no. Hai luot doc thay vi N+1 — truoc day moi task
    # trong ngay la mot cau `select ... from task_runs` rieng.
    tat_ca = hermes_adapter.job()
    if tat_ca is None:
        # Adapter da nuot sqlite3.Error va tra None, nen `_bear_error_db` KHONG
        # con bat duoc gi — ma cai decorator do sinh ra dung de dua loi doc DB
        # len CUOI TRANG (LOI_DOC) thay vi de trang im lang "khong co task".
        # Review Fable 09/09/2026 bat duoc: ban dau tien cua doan nay tra []
        # im lang, tuc lam lai dung su co 06/09 ma decorator da sua.
        loi = "part_kanban: hermes_adapter khong doc duoc kanban.db (xem stderr)"
        ERROR_READ.append(loi)
        print(f"[nhat_ky] loi doc DB — {loi}", file=sys.stderr)
        return []
    trong_ngay = [v for v in tat_ca if _within_date(v["created_at"], ngay)]
    runs = {}
    if trong_ngay:                    # khong co task thi khong co gi de tra, khong co gi de bao
        runs = hermes_adapter.last_run_many([v["id"] for v in trong_ngay])
        if runs is None:
            loi = "part_kanban: khong doc duoc task_runs — tom tat/loi cua task se trong"
            ERROR_READ.append(loi)
            print(f"[nhat_ky] loi doc DB — {loi}", file=sys.stderr)
            runs = {}
    ra = []
    for v in trong_ngay:
        a, b = _hours_vn(v["created_at"]), _hours_vn(v["completed_at"])
        run = runs.get(v["id"]) or {}
        tom = (run.get("summary") or v["result"]) or ""
        ra.append({"id": v["id"], "tieu_de": v["title"], "vai": v["assignee"],
                   "trang_thai": v["status"],
                   "gio": a.strftime("%H:%M") if a else "?",
                   "giay": round((b - a).total_seconds()) if a and b else None,
                   "tom_tat": re.sub(r"\s+", " ", str(tom))[:300],
                   "loi": (v["error"] or run.get("error") or "") or ""})
    ra.sort(key=lambda x: x["gio"])
    return ra


@_bear_error_db(None)
def part_finn(ngay: str) -> dict | None:
    p = env_load.state_dir() / f"finn_candidates_{ngay}.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    its = d.get("items", d) if isinstance(d, dict) else d
    chon = [i for i in its if str(i.get("picked", "")).lower() == "true"]
    def _diem(i):
        try:
            return int(i.get("score", 0))
        except (TypeError, ValueError):
            return 0
    top = sorted(its, key=_diem, reverse=True)[:3]
    return {"so_tin": len(its), "da_chon": len(chon),
            "top": [{"diem": i.get("score"), "tieu_de": i.get("title", "")[:80],
                     "nguon": i.get("source_note", "")} for i in top],
            "chon": [i.get("title", "")[:80] for i in chon]}


def part_draft(ngay: str) -> list:
    ra = []
    d = ROOT / "drafts"
    if not d.exists():
        return ra
    for p in sorted(d.glob("*.json")):
        if p.name.endswith(".meta.json"):
            continue
        t = _hours_vn(p.stat().st_mtime)
        if not t or t.strftime("%Y-%m-%d") != ngay:
            continue
        try:
            j = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            continue
        ra.append({"id": p.stem, "gio": t.strftime("%H:%M"),
                   "trang_thai": j.get("status", "?"),
                   "chu": len(j.get("caption") or ""),
                   "co_anh": bool(j.get("image"))})
    return ra


def part_git(ngay: str) -> list:
    """Commit trong ngay — day chinh la ban ghi 'sua cai gi' tin cay nhat."""
    try:
        out = subprocess.run(
            ["git", "log", f"--since={ngay} 00:00", f"--until={ngay} 23:59",
             "--date=format:%H:%M", "--pretty=%h|%ad|%s"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=30).stdout
    except Exception:                                        # noqa: BLE001
        return []
    ra = []
    for d in out.strip().splitlines():
        p = d.split("|", 2)
        if len(p) == 3:
            ra.append({"ma": p[0], "gio": p[1], "mo_ta": p[2]})
    return ra


@_bear_error_db(None)
def part_model(ngay: str) -> dict | None:
    p = env_load.state_dir() / "model_health.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    if not _within_date(d.get("checked_at"), ngay):
        return None
    ms = d.get("models", {})
    hong = [m for m, v in ms.items() if not v.get("ok")]
    return {"tong": len(ms), "hong": hong,
            "ly_do": {m: ms[m].get("why") for m in hong}}


# ---------- ghi chu tay ----------

def extra_notes(noi_dung: str, loai: str, ngay: str):
    DIRECTORY.mkdir(parents=True, exist_ok=True)
    ban = {"ngay": ngay, "luc": datetime.now(VN).strftime("%H:%M"),
           "loai": loai, "noi_dung": noi_dung.strip()}
    with NOTES.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ban, ensure_ascii=False) + "\n")
    return ban


def read_notes(ngay: str) -> list:
    if not NOTES.exists():
        return []
    ra = []
    for d in NOTES.read_text(encoding="utf-8").splitlines():
        d = d.strip()
        if not d:
            continue
        try:
            b = json.loads(d)
        except Exception:                                    # noqa: BLE001
            continue
        if b.get("ngay") == ngay:
            ra.append(b)
    return ra


# ---------- dung trang ----------

def use_page(ngay: str) -> str:
    ERROR_READ.clear()
    L = [f"# Nhật ký {ngay}", "",
         f"*Dựng lúc {datetime.now(VN).strftime('%H:%M %d/%m')} (giờ VN). "
         "Phần tự động sinh lại được; ghi chú tay lưu riêng ở `notes.jsonl`.*", ""]

    gc = read_notes(ngay)
    if gc:
        L += ["## Vấn đề, bug và cách sửa", ""]
        for b in gc:
            L.append(f"- **{TYPE.get(b['loai'], b['loai'])}** ({b['luc']}) — {b['noi_dung']}")
        L.append("")

    g = part_git(ngay)
    if g:
        L += ["## Thay đổi mã nguồn", ""]
        for c in g:
            L.append(f"- `{c['ma']}` {c['gio']} — {c['mo_ta']}")
        L.append("")

    f = part_finn(ngay)
    if f:
        L += ["## Finn quét tin", "",
              f"- Quét được **{f['so_tin']}** tin, Ông Chủ chọn **{f['da_chon']}**", ""]
        for t in f["top"]:
            L.append(f"  - [{t['diem']}đ] {t['tieu_de']} — *{t['nguon']}*")
        if f["chon"]:
            L += ["", "  Đã chọn:"] + [f"  - {x}" for x in f["chon"]]
        L.append("")

    k = part_kanban(ngay)
    if k:
        xong = sum(1 for x in k if x["trang_thai"] == "done")
        L += ["## Task kanban", "",
              f"- {len(k)} task, {xong} xong, {len(k) - xong} chưa", ""]
        for x in k:
            gy = f" ({x['giay']}s)" if x["giay"] else ""
            L.append(f"- `{x['id']}` {x['gio']} **{x['vai']}** — {x['tieu_de']} "
                     f"→ {x['trang_thai']}{gy}")
            if x["tom_tat"]:
                L.append(f"  > {x['tom_tat']}")
            if x["loi"]:
                L.append(f"  ❌ {re.sub(chr(10), ' ', str(x['loi']))[:200]}")
        L.append("")

    d = part_draft(ngay)
    if d:
        L += ["## Bài viết", ""]
        for x in d:
            L.append(f"- `{x['id']}` {x['gio']} — {x['chu']} ký tự, "
                     f"{'có ảnh' if x['co_anh'] else 'chưa có ảnh'}, {x['trang_thai']}")
        L.append("")

    c = part_cron(ngay)
    if c:
        loi = [x for x in c if x["trang_thai"] not in ("completed", *FORM_RUN)]
        dang = [x for x in c if x["trang_thai"] in FORM_RUN]
        dem = f"- {len(c)} lượt chạy, {len(loi)} lỗi"
        if dang:
            dem += f", {len(dang)} còn đang chạy lúc dựng nhật ký"
        L += ["## Cron", "", dem, ""]

        # Gom theo việc: việc chạy dày chỉ cần một dòng tổng, việc thưa thì kể từng lượt.
        for ten, nhom in _gather_by_job(c):
            if len(nhom) > EXCESS:
                gy = [x["giay"] for x in nhom if x["giay"] is not None]
                d = f"- `{ten}` — {len(nhom)} lượt"
                if gy:
                    cham = max(nhom, key=lambda x: x["giay"] if x["giay"] is not None else -1)
                    d += (f", trung bình {sum(gy) / len(gy):.1f}s"
                          f", chậm nhất {cham['giay']}s lúc {cham['gio']}")
                nl = sum(1 for x in nhom if x["trang_thai"] not in ("completed", *FORM_RUN))
                d += f", {nl} lỗi" if nl else ", không lỗi"
                L.append(d)
            else:
                for x in nhom:
                    gy = f" {x['giay']}s" if x["giay"] is not None else ""
                    dau = ("⏳" if x["trang_thai"] in FORM_RUN
                           else "✓" if x["trang_thai"] == "completed" else "✗")
                    L.append(f"- {dau} {x['gio']} {x['ten']}{gy}"
                             + (f" — {x['loi']}" if x["loi"] else ""))

        if loi:
            L += ["", "**Lượt lỗi**", ""]
            for x in loi:
                L.append(f"- ✗ {x['gio']} {x['ten']} — {x['loi'] or x['trang_thai']}")
        L.append("")

    m = part_model(ngay)
    if m:
        L += ["## Model", ""]
        if m["hong"]:
            for x in m["hong"]:
                L.append(f"- 🔴 `{x}` — {m['ly_do'].get(x)}")
        else:
            L.append(f"- Cả {m['tong']} model đều khoẻ")
        L.append("")

    if len(L) <= 4:
        L.append("*Không có hoạt động nào được ghi lại trong ngày.*")
    if ERROR_READ:
        # Hien ngay tren trang: nhat ky thieu mot mang thi phai NHIN THAY la
        # thieu, khong duoc de nguoi doc tuong hom do khong co viec gi.
        L += ["", "## ⚠️ Không đọc được một phần dữ liệu", "",
              "Các mục dưới đây trống vì lỗi đọc CSDL của hermes, **không phải**"
              " vì hôm đó không có việc:", ""]
        L += [f"- `{d}`" for d in ERROR_READ]
        L += ["", "Thường gặp sau `hermes update` đổi schema. Chạy lại "
              "`venv/bin/python journal.py --ngay <ngày>` để xem stderr đầy đủ.", ""]
    return "\n".join(L).rstrip() + "\n"


def main():
    a_p = argparse.ArgumentParser(description="Nhat ky lam viec hang ngay")
    a_p.add_argument("--ngay", help="YYYY-MM-DD (mac dinh: hom nay, gio VN)")
    a_p.add_argument("--note", help="Them mot ghi chu tay vao ngay do")
    a_p.add_argument("--loai", default="ghi-chu", choices=sorted(TYPE),
                     help="Loai ghi chu (mac dinh ghi-chu)")
    a_p.add_argument("--in-ra", action="store_true", help="In ra man hinh thay vi chi ghi tep")
    a = a_p.parse_args()

    ngay = a.ngay or datetime.now(VN).strftime("%Y-%m-%d")
    if a.note:
        b = extra_notes(a.note, a.loai, ngay)
        print(f"da ghi [{b['loai']}] {b['luc']} ngay {ngay}")

    DIRECTORY.mkdir(parents=True, exist_ok=True)
    trang = use_page(ngay)
    out = DIRECTORY / f"{ngay}.md"
    out.write_text(trang, encoding="utf-8")
    print(out)
    if a.in_ra:
        print("\n" + trang)


if __name__ == "__main__":
    main()
