#!/usr/bin/env python3
"""Nhat ky lam viec hang ngay — gom tu cac nguon da co, khong nho LLM tom tat.

Truoc day muon biet "hom qua doi lam gi" phai mo bon noi: state/finn_candidates_*
xem diem cham, kanban.db xem task nao duoc tao, profiles/*/sessions/ xem agent
nghi gi, roi cuon Telegram xem Ong Chu chon so may. File nay ghep san lai.

HAI PHAN, tach bach co chu y:

  - Phan TU DONG: doc lai tu executions.db, kanban.db, state/*.json, git log.
    Sinh lai duoc bat cu luc nao, chay lai khong hong gi.
  - Phan GHI CHU TAY: van de gap, bug o dau, sua the nao. Thu nay khong suy ra
    duoc tu du lieu. Luu rieng o ghi_chu.jsonl (chi noi them, khong sua) roi
    ghep vao khi dung trang. Nho vay sinh lai phan tu dong KHONG BAO GIO xoa
    mat ghi chu — day la ly do khong luu thang vao tep .md.

Dung:
    venv/bin/python nhat_ky.py                          # dung trang hom nay
    venv/bin/python nhat_ky.py --ngay 2026-08-21        # dung trang ngay khac
    venv/bin/python nhat_ky.py --note "Telegram dinh chu, do agent nhet bao cao
        vao mot dong shell" --loai bug
    venv/bin/python nhat_ky.py --note "Vá publish.py: doi <br> thanh xuong dong"
        --loai fix
"""
import argparse
import json
import re
import os
import sqlite3
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

import env_load

ROOT = Path.home() / "content-team"
HERMES = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
THU_MUC = env_load.state_dir() / "nhat_ky"
GHI_CHU = THU_MUC / "ghi_chu.jsonl"
VN = timezone(timedelta(hours=7))

LOAI = {"bug": "🐞 Bug", "fix": "🔧 Đã sửa", "van-de": "⚠️ Vấn đề",
        "ghi-chu": "📝 Ghi chú", "quyet-dinh": "🎯 Quyết định"}


def _gio_vn(v) -> datetime | None:
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


def _trong_ngay(v, ngay: str) -> bool:
    d = _gio_vn(v)
    return bool(d) and d.strftime("%Y-%m-%d") == ngay


def _mo(db: Path):
    return sqlite3.connect(f"file:{db}?mode=ro", uri=True) if db.exists() else None


# ---------- cac nguon ----------

# Trang thai hermes dat cho luot da nhan nhung chua xong. Nhat ky chay 23:00 UTC
# cung dot voi cac viec ngay khac, doc trung luc chung con dang chay - khong phai loi.
DANG_CHAY = ("running", "claimed", "started", "pending")

# Viec chay tren nguong nay trong mot ngay chi in mot dong tong, khong ke tung luot.
THUA = 6


def _gom_theo_viec(c: list) -> list:
    """Gom cac luot theo ten viec, giu thu tu luot dau tien xuat hien."""
    nhom = {}
    for x in c:
        nhom.setdefault(x["ten"], []).append(x)
    return list(nhom.items())


def phan_cron(ngay: str) -> list:
    con = _mo(HERMES / "cron" / "executions.db")
    if not con:
        return []
    ten = {}
    jp = HERMES / "cron" / "jobs.json"
    if jp.exists():
        ten = {j["id"]: j["name"] for j in json.loads(jp.read_text(encoding="utf-8"))["jobs"]}
    ra = []
    for jid, st, s, f, err in con.execute(
            "select job_id,status,started_at,finished_at,error from executions"):
        if not _trong_ngay(s, ngay):
            continue
        a, b = _gio_vn(s), _gio_vn(f)
        ra.append({"ten": ten.get(jid, jid), "gio": a.strftime("%H:%M") if a else "?",
                   "giay": round((b - a).total_seconds(), 1) if a and b else None,
                   "trang_thai": st, "loi": err})
    ra.sort(key=lambda x: x["gio"])
    return ra


def phan_kanban(ngay: str) -> list:
    con = _mo(HERMES / "kanban.db")
    if not con:
        return []
    ra = []
    for tid, tie, ai, tt, tao, xong, kq, loi in con.execute(
            "select id,title,assignee,status,created_at,completed_at,result,last_failure_error from tasks"):
        if not _trong_ngay(tao, ngay):
            continue
        a, b = _gio_vn(tao), _gio_vn(xong)
        run = list(con.execute(
            "select summary,error,status from task_runs where task_id=? order by id desc limit 1", (tid,)))
        tom = (run[0][0] if run and run[0][0] else kq) or ""
        ra.append({"id": tid, "tieu_de": tie, "vai": ai, "trang_thai": tt,
                   "gio": a.strftime("%H:%M") if a else "?",
                   "giay": round((b - a).total_seconds()) if a and b else None,
                   "tom_tat": re.sub(r"\s+", " ", str(tom))[:300],
                   "loi": (loi or (run[0][1] if run else "")) or ""})
    ra.sort(key=lambda x: x["gio"])
    return ra


def phan_finn(ngay: str) -> dict | None:
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


def phan_draft(ngay: str) -> list:
    ra = []
    d = ROOT / "drafts"
    if not d.exists():
        return ra
    for p in sorted(d.glob("*.json")):
        if p.name.endswith(".meta.json"):
            continue
        t = _gio_vn(p.stat().st_mtime)
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


def phan_git(ngay: str) -> list:
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


def phan_model(ngay: str) -> dict | None:
    p = env_load.state_dir() / "model_health.json"
    if not p.exists():
        return None
    d = json.loads(p.read_text(encoding="utf-8"))
    if not _trong_ngay(d.get("checked_at"), ngay):
        return None
    ms = d.get("models", {})
    hong = [m for m, v in ms.items() if not v.get("ok")]
    return {"tong": len(ms), "hong": hong,
            "ly_do": {m: ms[m].get("why") for m in hong}}


# ---------- ghi chu tay ----------

def them_ghi_chu(noi_dung: str, loai: str, ngay: str):
    THU_MUC.mkdir(parents=True, exist_ok=True)
    ban = {"ngay": ngay, "luc": datetime.now(VN).strftime("%H:%M"),
           "loai": loai, "noi_dung": noi_dung.strip()}
    with GHI_CHU.open("a", encoding="utf-8") as f:
        f.write(json.dumps(ban, ensure_ascii=False) + "\n")
    return ban


def doc_ghi_chu(ngay: str) -> list:
    if not GHI_CHU.exists():
        return []
    ra = []
    for d in GHI_CHU.read_text(encoding="utf-8").splitlines():
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

def dung_trang(ngay: str) -> str:
    L = [f"# Nhật ký {ngay}", "",
         f"*Dựng lúc {datetime.now(VN).strftime('%H:%M %d/%m')} (giờ VN). "
         "Phần tự động sinh lại được; ghi chú tay lưu riêng ở `ghi_chu.jsonl`.*", ""]

    gc = doc_ghi_chu(ngay)
    if gc:
        L += ["## Vấn đề, bug và cách sửa", ""]
        for b in gc:
            L.append(f"- **{LOAI.get(b['loai'], b['loai'])}** ({b['luc']}) — {b['noi_dung']}")
        L.append("")

    g = phan_git(ngay)
    if g:
        L += ["## Thay đổi mã nguồn", ""]
        for c in g:
            L.append(f"- `{c['ma']}` {c['gio']} — {c['mo_ta']}")
        L.append("")

    f = phan_finn(ngay)
    if f:
        L += ["## Finn quét tin", "",
              f"- Quét được **{f['so_tin']}** tin, Ông Chủ chọn **{f['da_chon']}**", ""]
        for t in f["top"]:
            L.append(f"  - [{t['diem']}đ] {t['tieu_de']} — *{t['nguon']}*")
        if f["chon"]:
            L += ["", "  Đã chọn:"] + [f"  - {x}" for x in f["chon"]]
        L.append("")

    k = phan_kanban(ngay)
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

    d = phan_draft(ngay)
    if d:
        L += ["## Bài viết", ""]
        for x in d:
            L.append(f"- `{x['id']}` {x['gio']} — {x['chu']} ký tự, "
                     f"{'có ảnh' if x['co_anh'] else 'chưa có ảnh'}, {x['trang_thai']}")
        L.append("")

    c = phan_cron(ngay)
    if c:
        loi = [x for x in c if x["trang_thai"] not in ("completed", *DANG_CHAY)]
        dang = [x for x in c if x["trang_thai"] in DANG_CHAY]
        dem = f"- {len(c)} lượt chạy, {len(loi)} lỗi"
        if dang:
            dem += f", {len(dang)} còn đang chạy lúc dựng nhật ký"
        L += ["## Cron", "", dem, ""]

        # Gom theo việc: việc chạy dày chỉ cần một dòng tổng, việc thưa thì kể từng lượt.
        for ten, nhom in _gom_theo_viec(c):
            if len(nhom) > THUA:
                gy = [x["giay"] for x in nhom if x["giay"] is not None]
                d = f"- `{ten}` — {len(nhom)} lượt"
                if gy:
                    cham = max(nhom, key=lambda x: x["giay"] if x["giay"] is not None else -1)
                    d += (f", trung bình {sum(gy) / len(gy):.1f}s"
                          f", chậm nhất {cham['giay']}s lúc {cham['gio']}")
                nl = sum(1 for x in nhom if x["trang_thai"] not in ("completed", *DANG_CHAY))
                d += f", {nl} lỗi" if nl else ", không lỗi"
                L.append(d)
            else:
                for x in nhom:
                    gy = f" {x['giay']}s" if x["giay"] is not None else ""
                    dau = ("⏳" if x["trang_thai"] in DANG_CHAY
                           else "✓" if x["trang_thai"] == "completed" else "✗")
                    L.append(f"- {dau} {x['gio']} {x['ten']}{gy}"
                             + (f" — {x['loi']}" if x["loi"] else ""))

        if loi:
            L += ["", "**Lượt lỗi**", ""]
            for x in loi:
                L.append(f"- ✗ {x['gio']} {x['ten']} — {x['loi'] or x['trang_thai']}")
        L.append("")

    m = phan_model(ngay)
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
    return "\n".join(L).rstrip() + "\n"


def main():
    a_p = argparse.ArgumentParser(description="Nhat ky lam viec hang ngay")
    a_p.add_argument("--ngay", help="YYYY-MM-DD (mac dinh: hom nay, gio VN)")
    a_p.add_argument("--note", help="Them mot ghi chu tay vao ngay do")
    a_p.add_argument("--loai", default="ghi-chu", choices=sorted(LOAI),
                     help="Loai ghi chu (mac dinh ghi-chu)")
    a_p.add_argument("--in-ra", action="store_true", help="In ra man hinh thay vi chi ghi tep")
    a = a_p.parse_args()

    ngay = a.ngay or datetime.now(VN).strftime("%Y-%m-%d")
    if a.note:
        b = them_ghi_chu(a.note, a.loai, ngay)
        print(f"da ghi [{b['loai']}] {b['luc']} ngay {ngay}")

    THU_MUC.mkdir(parents=True, exist_ok=True)
    trang = dung_trang(ngay)
    out = THU_MUC / f"{ngay}.md"
    out.write_text(trang, encoding="utf-8")
    print(out)
    if a.in_ra:
        print("\n" + trang)


if __name__ == "__main__":
    main()
