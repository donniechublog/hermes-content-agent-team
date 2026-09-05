#!/usr/bin/env python3
"""nop_chung.py — phan dung chung cua cac script NOP (dre_nop, ethan_nop, kite_nop,
miles_nop): nap meta/workdir/xong.json/spec.json, chuan hoa chuoi, kiem "lam
lai", gui album kem nut duyet + ghi da_dung.json, ghi bang den.

Truoc 05/09/2026 moi doan nay chep 3–4 ban giong het nhau o tung nop; sua mot
ban thi ban kia troi (audit 05/09). Tep nay KHONG chua logic rieng cua vai nao.
"""
import json
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import anh_chuan_bi as cb                                    # noqa: E402
import env_load                                              # noqa: E402


def chuan(t) -> str:
    """Chuoi de so 'giong het': gop khoang trang, ha chu thuong."""
    return re.sub(r"\s+", " ", (t or "").strip().lower())


def nap(draft_id: str, spec_arg, ten_brief: str, ten_nop: str) -> tuple:
    """(meta, brand, wd, m, spec, spec_path, da_dung) cho mot draft. Thieu gi thi
    dung han voi cau chi dan cho vai (sys.exit) — nop la CLI, vai doc stdout."""
    meta = cb.nap_meta(draft_id)               # dat CT_BRAND theo brand cua draft
    brand = cb._brand_cua(meta)
    wd = cb.workdir(env_load.state_dir(), draft_id)
    m = cb._doc_json(wd / "xong.json")
    if not m:
        sys.exit(f"Chua chuan bi. Chay truoc: venv/bin/python {ten_brief} {draft_id}")
    spec_path = Path(spec_arg) if spec_arg else wd / "spec.json"
    if not spec_path.exists():
        sys.exit(f"Chua co spec: {spec_path} — viet theo khung trong {wd / 'brief.md'} roi chay lai "
                 f"venv/bin/python {ten_nop} {draft_id}.")
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except Exception as e:                                   # noqa: BLE001
        sys.exit(f"[LOI] spec.json khong phai JSON hop le: {type(e).__name__}: {e}")
    return meta, brand, wd, m, spec, spec_path, cb._doc_json(wd / "da_dung.json")


def kiem_lam_lai(da_dung, nhan_anh: str, anh_moi, hook_moi, khoa_anh: str = "anh") -> list:
    """Lam lai ma van giu anh/hook cua lan truoc -> loi. `khoa_anh` la khoa trong
    da_dung.json ("bia" voi carousel, "anh" voi hero)."""
    if not da_dung:
        return []
    loi = []
    cu = da_dung.get(khoa_anh)
    if anh_moi and cu and anh_moi == cu:
        loi.append(f"LÀM LẠI: {nhan_anh} vẫn là {cu} như lần trước — Ông Chủ bấm làm lại "
                   f"nghĩa là {nhan_anh} chưa đạt, đổi {nhan_anh} khác")
    if chuan(hook_moi) == chuan(da_dung.get("hook")):
        loi.append("LÀM LẠI: hook giống hệt lần trước — viết hook khác")
    return loi


def gui_album(vai: str, files, mo_ta: str, draft_id: str, wd: Path, da_dung, ghi: dict):
    """Gui anh/album len topic cua `vai` kem nut duyet, roi ghi da_dung.json
    (`ghi` = cac truong rieng cua vai: bia/anh/hook/theme...). Tra ve message_id."""
    import gui_telegram
    res = gui_telegram.post(vai, [str(f) for f in files], mo_ta[:1000], duyet=draft_id)
    r = res.get("result")
    mid = (r[-1] if isinstance(r, list) else r or {}).get("message_id")
    cb._ghi_json(wd / "da_dung.json", {**ghi, "luc": time.strftime("%H:%M %d/%m"),
                                       "lan": int((da_dung or {}).get("lan", 0)) + 1,
                                       "message_id": mid})
    return mid


def ghi_bang_den(draft_id: str, key: str, value, author: str) -> None:
    """Ghi ban giao co cau truc len the goc (kanban swarm). Best-effort: hong thi
    in mot dong canh bao, khong lam hong bai."""
    import bang_den
    ok, loi = bang_den.ghi_nen(draft_id, key, value, author)
    if not ok:
        print(f"[CANH BAO] bang den: {loi}")
