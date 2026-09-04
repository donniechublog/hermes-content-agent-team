#!/usr/bin/env python3
"""Danh sach BAT BUOC cho cac vai di tim tin (Finn/scout, Nova/nova, Vera/market).

Luat Ong Chu 04/09/2026: nguon/su kien ma script quet thay la PHAI dua vao
bao cao, vai khong duoc tu quyet "khong dang". Hom truoc sot thi hom sau bo
sung — muc nam trong danh sach cho toi khi thuc su co trong manifest.

Co che:
  - Script quet goi `them(vai, khoa, ten, loai, ghi_chu, link)` cho tung muc
    dat tieu chi tat dinh (top diem, watchlist, vao bang xep hang...). Trung
    khoa thi giu muc cu (ngay phat hien cu).
  - Script ghi manifest goi `kiem(vai, items)`: tra ve cac muc CHUA co trong
    danh sach vai nop -> tu choi ghi. Sau khi ghi thanh cong goi
    `xoa(vai, items)` de bo cac muc da dua.
  - Khop bang link (chuan hoa) hoac bang ten: moi manh chu/so (>=2 ky tu) cua
    ten phai co trong tieu de + tom tat (da bo dau cach, ky hieu).

Tep: state/<brand>/bat_buoc_<vai>.json (runtime, gitignore).
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402


def tep(vai: str) -> Path:
    return env_load.state_dir() / f"bat_buoc_{vai}.json"


def doc(vai: str) -> dict:
    p = tep(vai)
    try:
        return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except Exception:                                        # noqa: BLE001
        return {}


def _ghi(vai: str, bb: dict) -> None:
    p = tep(vai)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(bb, ensure_ascii=False, indent=2), encoding="utf-8")
    tmp.replace(p)


def them(vai: str, khoa: str, ten: str, loai: str, ghi_chu: str = "",
         link: str = "") -> bool:
    """Them mot muc; tra True neu la muc MOI."""
    bb = doc(vai)
    if khoa in bb:
        return False
    bb[khoa] = {"ten": ten, "loai": loai, "ghi_chu": ghi_chu, "link": link or "",
                "ngay": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
    _ghi(vai, bb)
    return True


def them_nhieu(vai: str, muc: list) -> int:
    """muc = [(khoa, ten, loai, ghi_chu, link)]. Tra so muc moi."""
    bb = doc(vai)
    moi = 0
    hom_nay = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    for m in muc:
        khoa, ten, loai, ghi_chu, link = m[:5]
        tu_khoa = list(m[5]) if len(m) > 5 and m[5] else []
        if khoa in bb:
            continue
        bb[khoa] = {"ten": ten, "loai": loai, "ghi_chu": ghi_chu,
                    "link": link or "", "ngay": hom_nay, "tu_khoa": tu_khoa}
        moi += 1
    if moi:
        _ghi(vai, bb)
    return moi


def chuan_link(u: str) -> str:
    u = (u or "").strip().lower()
    u = re.sub(r"^https?://(www\.)?", "", u)
    u = re.sub(r"[?#].*$", "", u)
    return u.rstrip("/")


def _chuan(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", str(t or "").lower())


def khop(muc: dict, item: dict) -> bool:
    if muc.get("link") and item.get("link"):
        if chuan_link(muc["link"]) == chuan_link(item["link"]):
            return True
    van_ban = _chuan((item.get("title") or "") + " " + (item.get("summary_vi") or ""))
    # `tu_khoa` (neu co): chi can DU cac tu khoa nay — dung cho tin "mot hang
    # mot ngay" cua Vera (Nvidia mua Hugging Face: 3 bao, Vera chon 1 bai).
    if muc.get("tu_khoa"):
        # Chi khop trong TIEU DE: tom tat bai khac nhac "OpenAI" khong tinh la
        # da dua tin OpenAI.
        tieu_de = _chuan(item.get("title") or "")
        return all(_chuan(t) in tieu_de for t in muc["tu_khoa"])
    manh = [m for m in re.findall(r"[a-z0-9]+", str(muc.get("ten", "")).lower())
            if len(m) >= 2]
    return bool(manh) and all(m in van_ban for m in manh)


def kiem(vai: str, items: list) -> list:
    """Cac muc bat buoc CHUA co trong `items` (list dict co title/summary_vi/link)."""
    return [v for v in doc(vai).values() if not any(khop(v, it) for it in items)]


def xoa(vai: str, items: list) -> int:
    """Bo cac muc da co trong `items`. Tra so muc da bo."""
    bb = doc(vai)
    con = {k: v for k, v in bb.items() if not any(khop(v, it) for it in items)}
    _ghi(vai, con)
    return len(bb) - len(con)


def in_danh_sach(vai: str, tieu_de: str = "BAT BUOC DUA VAO BAO CAO") -> None:
    bb = doc(vai)
    if not bb:
        return
    print(f"\n=== {tieu_de} ({len(bb)}) — {vai} KHONG duoc bo, script ghi manifest "
          "se tu choi neu thieu ===")
    for v in bb.values():
        print(f"  {v['ngay']}  [{v['loai']:<10s}] {str(v['ten'])[:60]:<61s} {v.get('ghi_chu', '')[:70]}")
        if v.get("link"):
            print(f"        {v['link'][:110]}")


def loi_thieu(vai: str, thieu: list) -> str:
    return ("TU CHOI ghi manifest: thieu " + str(len(thieu)) + " muc BAT BUOC "
            "(luat Ong Chu: script quet thay la phai dua, khong duoc bo):\n  - "
            + "\n  - ".join(f"{v['ten']} ({v['loai']}: {v.get('ghi_chu', '')[:80]})"
                            + (f"\n      {v['link']}" if v.get("link") else "")
                            for v in thieu)
            + "\nThem cac muc nay vao danh sach roi chay lai.")
