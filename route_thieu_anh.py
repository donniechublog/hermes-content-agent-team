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
import vai as vai_mod                                        # noqa: E402

DRAFTS = env_load.ROOT / "drafts"


def _tg_gui(vai: str, text: str, kb: dict | None = None) -> None:
    """Gui mot tin CHU len topic cua `vai` (kem nut neu co). Dung env cua
    gui_telegram; im lang neu thieu token (chay tay ngoai container)."""
    env_load.nap()
    token, group = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_GROUP_ID")
    thread = env_load.topics().get(vai)
    if not token or not group or not thread:
        print(f"[route] thieu TELEGRAM_BOT_TOKEN/GROUP hoac topic '{vai}' -> khong gui tin", file=sys.stderr)
        return
    body = {"chat_id": group, "message_thread_id": thread,
            "text": text, "parse_mode": "HTML", "disable_web_page_preview": True}
    if kb:
        body["reply_markup"] = kb
    # timeout=30: ham nay chay TRONG khoa draft cua engine, treo o day la cac
    # tien trinh khac phai doi (xem `chay`), nen khong duoc de mo.
    httpx.post(f"https://api.telegram.org/bot{token}/sendMessage", json=body, timeout=30)


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
    vai = im.get("vai_anh", "")
    if vai == "carousel-edu" or im.get("chuyen_kite"):
        return                                     # da la Kite / da chuyen roi
    so, tt = int(thieu.get("so", 0)), int(thieu.get("toi_thieu", 5))
    ten = vai_mod.ten_hien(vai)      # ban dang ky: vai.py (audit A4)
    tieu = m.get("title", draft_id)
    from duyet_giao_viec import chuan_assignee
    from duyet_bai import tao_task_kite
    _, khong_kite = chuan_assignee("carousel-edu")
    if khong_kite:
        # Brand nay chua co Kite (dcgr 05/09/2026). Noi thang, dung hua chuyen.
        kb = {"inline_keyboard": [[{"text": "❌ Bỏ hẳn tin", "callback_data": "imgno:" + draft_id}]]}
        if so == 0:
            _tg_gui(vai, f"🖼 <b>{tieu}</b>: <b>0 ảnh thật</b> dùng được, và brand này <b>chưa có Kite</b> "
                         f"để vẽ vector. {ten} sẽ không dựng được bộ này — bỏ tin, hoặc tạo Kite cho brand.", kb)
            m["khong_kite"] = True
        else:
            kb["inline_keyboard"][0].insert(0, {"text": f"🖼 {ten} làm với {so} ảnh", "callback_data": "imgtiep:" + draft_id})
            _tg_gui(vai, f"⚠️ <b>{tieu}</b>: chỉ <b>{so}/{tt}</b> ảnh thật dùng được; brand này chưa có Kite. Chọn:", kb)
            m["hoi_kite"] = True
        return
    if so == 0:
        rid, loi = tao_task_kite(draft_id, im, ly_do="engine: 0 anh that dung duoc")
        if loi:
            _tg_gui(vai, f"🖼 <b>{tieu}</b>: 0 ảnh thật dùng được, chuyển Kite <b>lỗi</b>: {loi}")
            return
        m["chuyen_kite"] = rid
        _tg_gui(vai, f"🖼 <b>{tieu}</b>: <b>0 ảnh thật</b> dùng được → đã tự chuyển <b>Kite</b> "
                     f"vẽ vector (task {rid}). {ten} không dựng bộ này.")
        print(f"[route] 0 anh -> Kite task {rid}", file=sys.stderr)
        return
    kb = {"inline_keyboard": [[
        {"text": "🎨 Gửi Kite vẽ vector", "callback_data": "imgkite:" + draft_id},
        {"text": f"🖼 {ten} làm với {so} ảnh", "callback_data": "imgtiep:" + draft_id}]]}
    _tg_gui(vai, f"⚠️ <b>{tieu}</b>: chỉ <b>{so}/{tt}</b> ảnh thật dùng được "
                 f"(nguồn: {', '.join(m.get('so_mien') or []) or '—'}). Chọn đường:", kb)
    m["hoi_kite"] = True
