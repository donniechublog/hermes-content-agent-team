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


def chu_bai_cua(m: dict, wd: Path) -> str:
    """Chu bai + tu lieu gom ve mot chuoi chu thuong, de doi chieu ten nguoi hay
    so lieu vai khai co that su nam trong bai khong."""
    tl = m.get("tu_lieu") or {}
    s = ((m.get("chu_bai") or "") + " " + (tl.get("doan_dau") or "")
         + " " + " ".join(tl.get("cau_co_so") or [])).lower()
    try:
        s += " " + (wd / "tu_lieu.md").read_text(encoding="utf-8").lower()
    except OSError:
        pass
    return s


def kiem_nhan_vat(anh: dict, ma_ds, nhan_vat, chu_bai: str, nhan: str) -> list:
    """Cong chan MAT NGUOI dung chung Dre/Ethan.

    Truoc 06/09/2026 chi dre_nop co day du ba lop nay; ethan_nop chi kiem "co
    khai ten hay chua", nen mot cai ten CEO bia dat van qua cong cho the hero
    (su co bia Broadcom 05/09: anh quan chuc G20, khai "Hock Tan"). Gom mot cho
    de hai vai khong con lech."""
    co = [ma for ma in ma_ds if ma and anh.get(ma, {}).get("mat")]
    nv = str(nhan_vat or "").strip()
    loi = []
    if co and not nv:
        loi.append(f"{nhan}{', '.join(co)} có mặt người mà không khai \"nhan_vat\": "
                   "\"<tên người trong bài>\" — khai tên nếu đúng là nhân vật, "
                   "không thì đổi ảnh khác")
        return loi
    if not co or not nv:
        return loi
    ho = nv.split(",")[0].strip().lower()
    if chu_bai and ho and ho not in chu_bai and not all(w in chu_bai for w in ho.split()[-2:]):
        loi.append(f"{nhan}nhan_vat \"{nv}\" không xuất hiện trong chữ bài — "
                   "khai tên người KHÔNG có trong bài là bịa. Bỏ ảnh này.")
    for ma in co:
        mo_ta = (anh.get(ma, {}).get("mo_ta") or "").lower()
        if mo_ta and any(k in mo_ta for k in ("không liên quan", "g20", "logo")):
            loi.append(f"{nhan}{ma} — vision mô tả: \"{anh[ma]['mo_ta'][:80]}\" — "
                       "không phải nhân vật bài này")
    return loi


def kiem_so_tren_anh(chu: str, m: dict, wd: Path) -> list:
    """Canh bao (khong chan) cac con so vai viet len ANH ma tu lieu khong co.

    Cung mot phep doi chieu caption_check dung cho caption cua Miles, nhung
    truoc 06/09/2026 khong vai lam anh nao goi — so bia tren slide di thang len
    Telegram. Chi CANH BAO vi doi don vi (2,5 ti / 2.5B) la chuyen binh thuong."""
    import caption_check
    la = caption_check.so_la(chu, chu_bai_cua(m, wd))
    if not la:
        return []
    return [f"số trên slide KHÔNG thấy trong tư liệu: {', '.join(la[:8])} — "
            "kiểm lại nguồn, số không có trong tư liệu là bịa (trừ khi đổi đơn vị)"]


def kiem_quote_dich(chu: str, nhan: str) -> list:
    """Quote con nguyen tieng Anh -> loi. Luat 'quote phai DICH sang tieng Viet'
    tu truoc chi nam trong SOUL/brief, khong cong nao kiem (06/09/2026).
    Do bang dau tieng Viet: cau tieng Viet that gan nhu luon co dau."""
    t = (chu or "").strip()
    if len(t) < 25:
        return []
    import caption_check
    if caption_check.ty_le_dau(t) < 0.02:
        return [f"{nhan}: \"{t[:60]}…\" trông như còn nguyên tiếng Anh — quote phải DỊCH sang "
                "tiếng Việt (giữ nguyên tên riêng, thuật ngữ)"]
    return []


def gui_album(vai: str, files, mo_ta: str, draft_id: str, wd: Path, da_dung, ghi: dict):
    """Gui anh/album len topic cua `vai` kem nut duyet, roi ghi da_dung.json
    (`ghi` = cac truong rieng cua vai: bia/anh/hook/theme...). Tra ve message_id."""
    import gui_telegram
    try:
        res = gui_telegram.post(vai, [str(f) for f in files], mo_ta[:1000], duyet=draft_id)
    except gui_telegram.GuiLoi as e:
        sys.exit(f"[LOI] {e}")
    r = res.get("result")
    mid = (r[-1] if isinstance(r, list) else r or {}).get("message_id")
    cb._ghi_json(wd / "da_dung.json", {**ghi, "luc": time.strftime("%H:%M %d/%m"),
                                       "lan": int((da_dung or {}).get("lan", 0)) + 1,
                                       "message_id": mid})
    # So anh da dung LIEN PHIEN (Ong Chu 06/09/2026): ghi anh GOC cua tung ma da
    # dung, de bai sau khong dung lai (kiem_da_dung o buoc nop).
    import luat_anh
    xong = cb._doc_json(wd / "xong.json") or {}
    goc = {a["ma"]: a["goc"] for a in xong.get("anh", [])}
    ma_ds = ghi.get("anh") if isinstance(ghi.get("anh"), list) else [ghi.get("anh"), ghi.get("bia")]
    for ma in ma_ds or []:
        if ma and goc.get(ma):
            luat_anh.ghi_da_dung(goc[ma], draft_id, vai)
    return mid


def ghi_bang_den(draft_id: str, key: str, value, author: str) -> None:
    """Ghi ban giao co cau truc len the goc (kanban swarm). Best-effort: hong thi
    in mot dong canh bao, khong lam hong bai."""
    import bang_den
    ok, loi = bang_den.ghi_nen(draft_id, key, value, author)
    if not ok:
        print(f"[CANH BAO] bang den: {loi}")
