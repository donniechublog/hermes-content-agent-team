#!/usr/bin/env python3
"""duyet_lenh.py — LENH SLASH: /bai <url> <vai> dat bai tay, /vai, /hd.
Nguyen tac: mot dau "/" nghia la Ong Chu dang RA LENH, khong tro chuyen.
Dung cu phap moi chay; sai cu phap / sai ten vai / URL hong thi bao ngan
va dung han — khong roi ve hoi thoai, khong tu suy dien "chac y la...".
Tach tu approve_service.py 06/09/2026 (di chuyen thuan).
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
import threading
import time
from pathlib import Path

from html import escape as html_escape

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402
import bang_den                                              # noqa: E402
import chat_router                                          # noqa: E402
import moat_publish                                         # noqa: E402
import tele_util                                            # noqa: E402
import ghi_log                                              # noqa: E402

from duyet_co_so import (  # noqa: E402
    BRAND, ONG_CHU_IDS, STATE_DIR, _ghi_json, _nap_json, call, log, rut,
)
from duyet_giao_viec import (  # noqa: E402
    MAC_DINH_VIET, TEN_SANG_CAP, TEN_VAI_ANH, TEN_VAI_VIET, VAI_ANH, VAI_CAROUSEL, VAI_EDU,
)
from duyet_chon_tin import (  # noqa: E402
    _draft_id, create_pair,
)


DAT_BAI_SO = STATE_DIR / "dat_bai.json"     # so dedup: url chuan hoa -> lan dat

# handle_command chay o thread rieng: hai /bai cung luc se cung doc-sua-ghi
# dat_bai.json -> mat ban ghi dedup, tao cap task trung. Mot khoa la du.
_KHOA_DAT_BAI = threading.Lock()

# Chan host noi bo: bot chay ngay tren server (tunnel, dashboard, cron) nen
# mot URL tro nguoc vao trong la fetch thang vao ruot he thong. Chi so khop
# ten host, khong resolve DNS — du cho mo hinh rui ro nay (chi Ong Chu ra
# lenh duoc), khong phai tuong lua.
_HOST_CAM = re.compile(
    r"^(localhost$|127\.|10\.|192\.168\.|169\.254\.|0\.)"
    r"|^172\.(1[6-9]|2\d|3[01])\."
    r"|\.(local|internal|netbird\.mated)$", re.I)

def _chuan_hoa_url(url):
    """Bo fragment + tham so tracking de dedup: cung mot bai dan hai lan tu
    hai nguon (newsletter, mang xa hoi) thuong chi khac nhau dung utm_*."""
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
    p = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(p.query)
         if not k.lower().startswith(("utm_", "fbclid", "gclid", "ref"))]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(),
                       p.path.rstrip("/"), urlencode(q), ""))

def _url_hop_le(url):
    """None neu dung duoc, chuoi ly do neu khong."""
    from urllib.parse import urlsplit
    try:
        p = urlsplit(url)
    except ValueError:
        return "URL không đọc được."
    if p.scheme not in ("http", "https") or not p.hostname:
        return "URL phải là http/https đầy đủ."
    if _HOST_CAM.search(p.hostname):
        return "Host này là địa chỉ nội bộ — không nhận."
    return None

def _doc_trang(url):
    """Lay title + anh og:image de dien khuon task. Chi can THE, khong can
    sach: vai duoc giao van tu doc bai goc va chay research (nguon_bai.py)
    nhu moi bai Finn quet. Tra (title|None, image_url, ghi_chu) — title None
    nghia la khong ket noi duoc (URL chet), con trang tra loi loi HTTP
    (paywall 403...) van tien hanh duoc, chi kem ghi chu."""
    try:
        with httpx.Client(timeout=20, follow_redirects=True, headers={
                "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) content-team"}) as c:
            r = c.get(url)
    except Exception as e:                                   # noqa: BLE001
        return None, "", f"không tải được trang ({type(e).__name__})"
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(r.text[:500_000], "html.parser")
    og = soup.find("meta", property="og:title")
    title = (og and og.get("content") or "").strip()
    if not title and soup.title and soup.title.string:
        title = soup.title.string.strip()
    ogi = soup.find("meta", property="og:image")
    image_url = (ogi and ogi.get("content") or "").strip()
    ghi_chu = ""
    if r.status_code >= 400:
        ghi_chu = (f"trang trả HTTP {r.status_code} (paywall/chặn bot?) — "
                   "vai được giao cần tự kiểm tra đọc được không")
    if not title:
        from urllib.parse import urlsplit
        p = urlsplit(url)
        title = p.netloc + p.path
    return title, image_url, ghi_chu

LENH_HELP = (
    "<b>Lệnh:</b>\n"
    "<code>/bai &lt;url&gt; &lt;vai&gt;</code> — đặt bài tay từ URL: tạo cặp task "
    "ảnh + viết, không qua vòng quét của Finn.\n"
    "  vai nhận: <code>designer</code> (thẻ bìa) hoặc <code>carousel</code> "
    "(nhiều slide); brand cố định theo container.\n"
    "<code>/vai</code> — bảng vai trong container này.\n"
    "<code>/help</code> — tin này.\n"
    "Sai cú pháp thì không làm gì — lệnh phải tường minh.")

def _lenh_bai(tra_loi, args):
    if len(args) != 2 or not args[0].lower().startswith(("http://", "https://")):
        tra_loi("Cú pháp: <code>/bai &lt;url&gt; &lt;vai&gt;</code> — đúng hai "
                "phần, URL trước vai sau. Không tạo gì.")
        return
    url, ten = args[0], args[1].lower()
    if ten not in TEN_SANG_CAP:
        tra_loi("Không có vai <b>" + html_escape(ten) + "</b>. Vai nhận: "
                + ", ".join(sorted(TEN_SANG_CAP)) + ". Không tạo gì.")
        return
    loi = _url_hop_le(url)
    if loi:
        tra_loi("❌ " + loi + " Không tạo gì.")
        return
    url_chuan = _chuan_hoa_url(url)
    so = _nap_json(DAT_BAI_SO, {})
    if url_chuan in so:
        cu = so[url_chuan]
        tra_loi("URL này đã đặt " + cu.get("ngay", "?") + " — draft <code>"
                + html_escape(cu.get("draft_id", "?")) + "</code>, giao "
                + cu.get("vai", "?") + ". Không tạo lại.")
        return

    vai_anh, brand = TEN_SANG_CAP[ten], BRAND
    title, image_url, ghi_chu = _doc_trang(url)
    if title is None:
        tra_loi("❌ " + ghi_chu + " — không tạo task. Kiểm tra URL rồi /bai lại.")
        return

    import hashlib
    item = {
        # index vao fallback cua slugify — bam theo URL de hai bai tieng Viet
        # (slug rong) khong de len nhau
        "index": "b" + hashlib.sha1(url_chuan.encode()).hexdigest()[:8],
        "title": title, "link": url,
        "summary_vi": "",
        "source_note": "Ong Chu dat tay qua lenh /bai — tu doc bai goc va tu tom tat.",
        "via": "", "image_url": image_url or "khong co",
        "category": None, "score": "?",
        "score_reason": "dat tay, khong qua cham diem",
        "nguon": "adhoc",
    }
    tid, err = create_pair(item, vai_anh=vai_anh, brand=brand)
    if err:
        tra_loi("❌ " + html_escape(err))
        return

    draft_id = _draft_id(item, brand, vai_anh)
    so[url_chuan] = {"ngay": time.strftime("%Y-%m-%d %H:%M"),
                     "draft_id": draft_id, "vai": vai_anh, "brand": brand,
                     "tasks": [tid], "title": title}
    _ghi_json(DAT_BAI_SO, so)

    ten_hien = TEN_VAI_ANH.get(vai_anh, "Ethan")
    ten_viet = TEN_VAI_VIET.get(MAC_DINH_VIET, "Miles")
    dong = ("✅ <b>" + html_escape(title) + "</b>\n"
            + f"{ten_hien} dựng ảnh ({brand}) — task {tid}. "
            + f"{ten_viet} viết caption SAU khi Ông Chủ bấm Duyệt ảnh.")
    if ghi_chu:
        dong += "\n⚠️ " + ghi_chu
    tra_loi(dong)

def handle_command(token, group, msg, thread_id, text):
    def tra_loi(t):
        call(token, "sendMessage", chat_id=group,
             **({"message_thread_id": thread_id} if thread_id else {}),
             text=t, parse_mode="HTML", disable_web_page_preview=True)

    # Allowlist: co file state/ong_chu.json (danh sach user_id) thi chi nhung
    # id do duoc ra lenh; chua co file thi giu hanh vi cu (ca group — group
    # hien chi co Ong Chu). Tin bao loi kem id de them vao file cho de.
    uid = msg.get("from", {}).get("id")
    cho_phep = _nap_json(ONG_CHU_IDS, [])
    if cho_phep and uid not in cho_phep:
        tra_loi("Lệnh slash chỉ nhận từ Ông Chủ. (id của bạn: <code>"
                + str(uid) + "</code>)")
        return

    phan = text.split()
    lenh = phan[0].split("@")[0].lower()    # "/bai@TenBot" -> "/bai"
    goi_bot = phan[0].split("@")[1].lower() if "@" in phan[0] else ""

    # Hai bot chung group (05/09/2026): lenh cua approve la /bai /vai /hd (+/help
    # khi goi dich danh /help@<bot duyet>). Lenh KHAC la cua Hermes (gateway):
    # /help, /kanban, /new, /status... -> approve IM, khong "Khong co lenh".
    # Gateway phia kia bo qua /bai /vai /hd (telegram.extra.ignore_commands).
    qua_gateway = os.environ.get("CT_CHAT_QUA_GATEWAY", "") == "1"
    if lenh == "/help" and qua_gateway and goi_bot and "pm" not in goi_bot:
        return                                  # /help@hermesdcgr_bot: cua gateway
    if lenh == "/help" and qua_gateway and not goi_bot:
        log("route", "/help tran: de gateway tra loi; approve co /hd")
        return
    if lenh not in ("/bai", "/vai", "/hd", "/help") and qua_gateway:
        log("route", f"lenh {lenh}: cua Hermes/gateway, approve im")
        return

    if lenh in ("/help", "/hd"):
        tra_loi(LENH_HELP)
    elif lenh == "/vai":
        dong = [f"<b>Vai ảnh</b> (brand cố định của container: {BRAND}):"]
        for ten, va in sorted(VAI_ANH.items()):
            kieu = ("carousel deck" if va in VAI_EDU
                    else "carousel" if va in VAI_CAROUSEL else "thẻ bìa")
            dong.append(f"  <code>{ten}</code> → {va} ({kieu})")
        dong.append("<b>Vai viết</b>: <code>writer</code> — một người viết cho container này.")
        tra_loi("\n".join(dong))
    elif lenh == "/bai":
        with _KHOA_DAT_BAI:
            _lenh_bai(tra_loi, phan[1:])
    else:
        tra_loi("Không có lệnh " + html_escape(lenh) + " — /help để xem. "
                "Sai lệnh thì không làm gì.")
