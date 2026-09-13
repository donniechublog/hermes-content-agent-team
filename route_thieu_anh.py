#!/usr/bin/env python3
"""Tang GHEP NOI: bai thieu anh that thi hoi Ong Chu hay chuyen Kite.

Vi sao tach ra (audit_content_team A1): hai viec nay — gui Telegram va tao task
Kite — la viec cua tang DIEU PHOI, nhung truoc 09/09/2026 chung nam trong
`anh_chuan_bi._route_thieu_anh`, tuc trong ENGINE. Engine vi vay phai
`from duyet_giao_viec import chuan_assignee` va `from duyet_bai import
tao_task_kite`: lop CHUAN BI goi NGUOC len lop dieu phoi. Do la vong phu thuoc
that, chi bi che di bang hai import luoi trong than ham.

Nay engine chi MO TA (`xong.json["thieu_anh"] = {"so": 2, "toi_thieu": 5}`) va
nhan mot ham `sau_chuan_bi` de goi. Tep nay la noi DUY NHAT biet ca hai phia,
nen mui ten phu thuoc chi con mot chieu: ghep noi -> engine, ghep noi -> dich vu.

QUAN TRONG — vi sao van goi DONG BO trong khoa cua engine chu khong doi ra
ngoai: `chay()` giu `dang_chay.pid` va chi ghi `xong.json` SAU khi ham nay
xong, nen moi nguoi doc `xong.json` deu thay quyet dinh da chot (co
`chuyen_kite`/`hoi_kite`/`khong_kite` hay khong). Neu day viec nay ra sau
`chay()` — hoac sang mot vong poll khac — thi co khe: `dre_chuan_bi.py:41,46`
va `kite_chuan_bi.py:54` doc `xong.json` de dung brief, doc trung khe do la
brief IM LANG bao "du anh" trong khi tin dang cho chuyen Kite.
"""
import json
import os
import sys
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402
import role as vai_mod                                        # noqa: E402

DRAFTS = env_load.ROOT / "drafts"


def _tg_gui(vai: str, text: str, kb: dict | None = None) -> bool:
    """Gui mot tin CHU len topic cua `vai` (kem nut neu co). Tra True CHI KHI
    Telegram nhan (ok=true); moi truong hop khac in ly do ra stderr va tra False.

    Truoc audit lượt 2 (C-r2-1) ham nay tra None va vut ket qua httpx.post:
    Telegram tra 400 (HTML sai, topic sai) hay mat mang thi khong log, ma
    sau_chuan_bi van ghi m["hoi_kite"]=True — bai "dang cho Ong Chu chon" trong
    khi Ong Chu chua bao gio nhan cau hoi. Nguoi goi PHAI nhin gia tri tra ve."""
    env_load.nap()
    token, group = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_GROUP_ID")
    thread = env_load.topics().get(vai)
    if not token or not group or not thread:
        print(f"[route] thieu TELEGRAM_BOT_TOKEN/GROUP hoac topic '{vai}' -> khong gui tin", file=sys.stderr)
        return False
    body = {"chat_id": group, "message_thread_id": thread,
            "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb:
        body["reply_markup"] = kb
    # timeout=30: ham nay chay TRONG khoa draft cua engine, treo o day la cac
    # tien trinh khac phai doi (xem `chay`), nen khong duoc de mo.
    try:
        r = httpx.post(f"https://api.telegram.org/bot{token}/sendMessage", json=body, timeout=30)
        kq = r.json()
    except Exception as e:                                   # noqa: BLE001
        print(f"[route] gui Telegram topic '{vai}' hong: {type(e).__name__}: {e!r}", file=sys.stderr)
        return False
    if not kq.get("ok"):
        print(f"[route] Telegram tu choi (topic '{vai}', HTTP {r.status_code}): "
              f"{kq.get('description', kq)!r}", file=sys.stderr)
        return False
    return True


def sau_chuan_bi(draft_id: str, m: dict) -> None:
    """0 anh that -> tu chuyen Kite; thieu -> hoi Ong Chu bang nut.

    Doc co `m["thieu_anh"]` do engine ghi. Ghi nguoc quyet dinh vao `m`
    (`chuyen_kite` / `hoi_kite` / `khong_kite`) — engine ghi ca `m` xuong
    `xong.json` ngay sau khi ham nay tra ve."""
    thieu = m.get("thieu_anh")
    if not thieu:
        return                                     # du anh, khong co gi de hoi
    ip = DRAFTS / (draft_id + ".img.json")
    if not ip.exists():
        return
    im = json.loads(ip.read_text(encoding="utf-8"))
    # slug_that: sidecar cu con ghi ten persona ("dre", "miles") — chinh ly do
    # vai.py ton tai. Dung tho thi topics().get("dre") miss -> khong gui gi.
    vai = vai_mod.canonical_slug(im.get("vai_anh", ""))
    if vai == "kite" or im.get("chuyen_kite"):
        return                                     # da la Kite / da chuyen roi
    so, tt = int(thieu.get("so", 0)), int(thieu.get("toi_thieu", 5))
    ten = vai_mod.display_name(vai)      # ban dang ky: vai.py (audit A4)
    tieu = m.get("title", draft_id)
    from duyet_giao_viec import chuan_assignee
    from duyet_bai import tao_task_kite
    _, khong_kite = chuan_assignee("kite")

    def _hoi(co: str, text: str, kb=None) -> None:
        # Chi dat co "da hoi/da bao" khi Telegram THAT SU nhan. Khong thi ghi
        # `route_loi` de brief/nhat ky lo ra, thay vi bai dung mai cho mot cau
        # hoi khong ai nhan (C-r2-1).
        if _tg_gui(vai, text, kb):
            m[co] = True
        else:
            m["route_loi"] = f"khong gui duoc tin '{co}' len topic {vai} — xem stderr engine"

    if khong_kite:
        # Brand nay chua co Kite (dcgr 05/09/2026). Noi thang, dung hua chuyen.
        kb = {"inline_keyboard": [[{"text": "❌ Bỏ hẳn tin", "callback_data": "imgno:" + draft_id}]]}
        if so == 0:
            _hoi("khong_kite", f"🖼 <b>{tieu}</b>: <b>0 ảnh thật</b> dùng được, và brand này <b>chưa có Kite</b> "
                               f"để vẽ vector. {ten} sẽ không dựng được bộ này — bỏ tin, hoặc tạo Kite cho brand.", kb)
        else:
            kb["inline_keyboard"][0].insert(0, {"text": f"🖼 {ten} làm với {so} ảnh", "callback_data": "imgtiep:" + draft_id})
            _hoi("hoi_kite", f"⚠️ <b>{tieu}</b>: chỉ <b>{so}/{tt}</b> ảnh thật dùng được; brand này chưa có Kite. Chọn:", kb)
        return
    if so == 0:
        rid, loi = tao_task_kite(draft_id, im, ly_do="engine: 0 anh that dung duoc")
        if loi:
            _tg_gui(vai, f"🖼 <b>{tieu}</b>: 0 ảnh thật dùng được, chuyển Kite <b>lỗi</b>: {loi}")
            return
        m["chuyen_kite"] = rid                     # task DA tao — co du tin bao co di hay khong
        if not _tg_gui(vai, f"🖼 <b>{tieu}</b>: <b>0 ảnh thật</b> dùng được → đã tự chuyển <b>Kite</b> "
                            f"vẽ vector (task {rid}). {ten} không dựng bộ này."):
            m["route_loi"] = f"da chuyen Kite (task {rid}) nhung khong bao duoc len topic {vai}"
        print(f"[route] 0 anh -> Kite task {rid}", file=sys.stderr)
        return
    kb = {"inline_keyboard": [[
        {"text": "🎨 Gửi Kite vẽ vector", "callback_data": "imgkite:" + draft_id},
        {"text": f"🖼 {ten} làm với {so} ảnh", "callback_data": "imgtiep:" + draft_id}]]}
    _hoi("hoi_kite", f"⚠️ <b>{tieu}</b>: chỉ <b>{so}/{tt}</b> ảnh thật dùng được "
                     f"(nguồn: {', '.join(m.get('so_mien') or []) or '—'}). Chọn đường:", kb)
