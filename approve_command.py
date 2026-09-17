#!/usr/bin/env python3
"""approve_command.py — LENH SLASH: /bai <url> <vai> dat bai tay, /vai, /hd.
Nguyen tac: mot dau "/" nghia la Ong Chu dang RA LENH, khong tro chuyen.
Dung cu phap moi chay; sai cu phap / sai ten vai / URL hong thi bao ngan
va dung han — khong roi ve hoi thoai, khong tu suy dien "chac y la...".
Tach tu approve_service.py 06/09/2026 (di chuyen thuan).
"""
import os
import re
import sys
import threading
import time
from pathlib import Path

from html import escape as html_escape

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import scan_common                                           # noqa: E402
import state_paths                                           # noqa: E402

from approve_base import (  # noqa: E402
    BRAND, STATE_DIR, _write_json, _load_json, call, is_boss, log,
)
from approve_dispatch import (  # noqa: E402
    NAME_BRIGHT_CAP, NAME_ROLE_IMAGE, NAME_ROLE_WRITE, ROLE_IMAGE, ROLE_CAROUSEL, ROLE_EDU,
)
from approve_pick import (  # noqa: E402
    _draft_id, create_pair,
)


SET_ARTICLE_COUNT = STATE_DIR / state_paths.ARTICLE_REQUEST_COUNTS_FILE     # so dedup: url chuan hoa -> lan dat

# handle_command chay o thread rieng: hai /bai cung luc se cung doc-sua-ghi
# article_request_counts.json -> mat ban ghi dedup, tao cap task trung. Mot khoa la du.
_KHOA_DAT_BAI = threading.Lock()

# Chan host noi bo: bot chay ngay tren server (tunnel, dashboard, cron) nen
# mot URL tro nguoc vao trong la fetch thang vao ruot he thong. Chi so khop
# ten host, khong resolve DNS — du cho mo hinh rui ro nay (chi Ong Chu ra
# lenh duoc), khong phai tuong lua.
_HOST_CAM = re.compile(
    r"^(localhost$|127\.|10\.|192\.168\.|169\.254\.|0\.)"
    r"|^172\.(1[6-9]|2\d|3[01])\."
    r"|\.(local|internal|netbird\.mated)$", re.I)

def _standard_ify_url(url):
    """Bo fragment + tham so tracking de dedup: cung mot bai dan hai lan tu
    hai nguon (newsletter, mang xa hoi) thuong chi khac nhau dung utm_*."""
    from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
    p = urlsplit(url)
    q = [(k, v) for k, v in parse_qsl(p.query)
         if not k.lower().startswith(("utm_", "fbclid", "gclid", "ref"))]
    return urlunsplit((p.scheme.lower(), p.netloc.lower(),
                       p.path.rstrip("/"), urlencode(q), ""))

def _url_valid(url):
    """None neu dung duoc, chuoi ly do neu khong."""
    from urllib.parse import urlsplit
    try:
        p = urlsplit(url)
    except ValueError:
        return "URL không đọc được."
    if p.scheme not in ("http", "https") or not p.hostname:
        return "URL phải là http/https đầy đủ."
    # `scan_common.host_say_drop` la MOT cong cho ca day chuyen: `_HOST_CAM` o tren
    # chi so khop chuoi nen bo lot "127.1", "2130706433" va "[::1]". Giu ca hai
    # cho ro y dinh; ban chung moi la ban quyet dinh.
    if _HOST_CAM.search(p.hostname) or scan_common.host_say_drop(p.hostname):
        return "Host này là địa chỉ nội bộ — không nhận."
    return None

def _read_page(url):
    """Lay title + anh og:image de dien khuon task. Chi can THE, khong can
    sach: vai duoc giao van tu doc bai goc va chay research (article_sources.py)
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

# Post mang xa hoi: trang thuong doc bang the og: la du, nhung X/Instagram/
# Facebook tra ve vo SPA — do that 08/09/2026 tren mot link facebook: 4 cach
# (UA thuong, UA facebookexternalhit, mbasic, iframe plugins/post.php) deu chi
# ra ten nguoi dang, 340 KB HTML khong co lay mot cau tieng Viet nao. Duong duy
# nhat lay duoc chu la endpoint crawl noi bo (skill social-crawl) — cac vai
# Nova/Scout/Gin dung hang ngay, rieng /bai thi truoc day chua noi vao, nen mot
# link Facebook sinh ra task tieu de "Nguyen Doan Tung" voi brief rong (su co
# 08/09/2026, task t_905914b6).
#
# Cua goi chung nam o social_post.py — image_prepare.py cung goi dung cua do de
# lay ANH cua post. Dung viet lai o day.


def _read_social(url):
    """Toan van post. Tra (title, summary, image_url, link, ghi_chu) hoac None
    khi khong lay duoc — goi la de goi y roi ve _read_page, khong chan lenh.

    Khong tai anh ve o buoc nay: /bai chi can mot link de dien vao the. Anh that
    cho slide do image_prepare.py tai (`candidate_social`) khi dung brief, boi luc
    do moi co thu muc lam viec cua draft."""
    import social_post
    d = social_post.read(url, in_log=lambda t: log("bai", t))
    if not d or not d["text"]:
        return None
    img = next((m["url"] for m in d["media"] if m["type"] == "image"), "")
    ghi_chu = "" if img else "post khong co anh — vai tu lo phan hinh"
    return d["title"], d["text"], img, d["link"], ghi_chu


# Danh sach vai sinh tu ROLE_IMAGE chu khong go tay: truoc 08/09/2026 dong nay ke
# "designer hoac carousel" trong khi ma da nhan them kite/edu tu 05/09 — Ong Chu
# doc /hd thi tuong khong giao duoc cho Kite.
def _line_role_help():
    kieu = {}
    for ten, va in sorted(ROLE_IMAGE.items()):
        kieu.setdefault(va, []).append(ten)
    ta = {"ethan": "thẻ bìa", "dre": "nhiều slide ảnh thật",
          "kite": "carousel art vector"}
    return "; ".join(f"<code>{' / '.join(t)}</code> ({ta.get(v, v)})"
                     for v, t in sorted(kieu.items()))


COMMAND_HELP = (
    "<b>Lệnh:</b>\n"
    "<code>/bai &lt;url&gt; &lt;vai&gt;</code> — đặt bài tay từ URL: tạo cặp task "
    "ảnh + viết, không qua vòng quét của Finn.\n"
    "  vai nhận: " + _line_role_help() + "; brand cố định theo container.\n"
    "  Link X / Instagram / Facebook: tự lấy TOÀN VĂN post (crawl 30-60 giây), "
    "vai không phải đọc lại trang gốc.\n"
    "<code>/vai</code> — bảng vai trong container này.\n"
    "<code>/help</code> — tin này.\n"
    "Sai cú pháp thì không làm gì — lệnh phải tường minh.")

def _command_article(tra_loi, args):
    if len(args) != 2 or not args[0].lower().startswith(("http://", "https://")):
        tra_loi("Cú pháp: <code>/bai &lt;url&gt; &lt;vai&gt;</code> — đúng hai "
                "phần, URL trước vai sau. Không tạo gì.")
        return
    url, ten = args[0], args[1].lower()
    if ten not in NAME_BRIGHT_CAP:
        tra_loi("Không có vai <b>" + html_escape(ten) + "</b>. Vai nhận: "
                + ", ".join(sorted(NAME_BRIGHT_CAP)) + ". Không tạo gì.")
        return
    loi = _url_valid(url)
    if loi:
        tra_loi("❌ " + loi + " Không tạo gì.")
        return
    url_chuan = _standard_ify_url(url)
    so = _load_json(SET_ARTICLE_COUNT, {})
    if url_chuan in so:
        cu = so[url_chuan]
        tra_loi("URL này đã đặt " + cu.get("ngay", "?") + " — draft <code>"
                + html_escape(cu.get("draft_id", "?")) + "</code>, giao "
                + cu.get("vai", "?") + ". Không tạo lại.")
        return

    vai_anh, brand = NAME_BRIGHT_CAP[ten], BRAND
    # Post mang xa hoi: lay TOAN VAN truoc (crawl that, 25-90s nen bao truoc);
    # that bai thi roi ve doc the og: nhu bai bao thuong.
    summary, source_note = "", ("Ong Chu dat tay qua lenh /bai — tu doc bai goc "
                                "va tu tom tat.")
    social = None
    import social_post
    if social_post.is_social(url):
        tra_loi("⏳ Đang đọc post (crawl thật, có thể 30-60 giây)…")
        social = _read_social(url)
    if social:
        title, summary, image_url, url, ghi_chu = social
        # Toan van da nam trong brief: bao vai dung lai, khoi chay research doc
        # trang goc — Facebook/X chan bot, vai co doc lai cung chi thay tuong dang nhap.
        source_note = ("Ong Chu dat tay qua lenh /bai — TOAN VAN post da lay san "
                       "bang crawl noi bo, dung truc tiep, khong can mo lai trang goc.")
        url_chuan = _standard_ify_url(url)          # dedup theo permalink da chuan hoa
        if url_chuan in so:
            cu = so[url_chuan]
            tra_loi("Post này đã đặt " + cu.get("ngay", "?") + " — draft <code>"
                    + html_escape(cu.get("draft_id", "?")) + "</code>, giao "
                    + cu.get("vai", "?") + ". Không tạo lại.")
            return
    else:
        title, image_url, ghi_chu = _read_page(url)
        if title is None:
            tra_loi("❌ " + ghi_chu + " — không tạo task. Kiểm tra URL rồi /bai lại.")
            return

    import hashlib
    item = {
        # index vao fallback cua slugify — bam theo URL de hai bai tieng Viet
        # (slug rong) khong de len nhau
        "index": "b" + hashlib.sha1(url_chuan.encode()).hexdigest()[:8],
        "title": title, "link": url,
        "summary_vi": summary,
        "source_note": source_note,
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
    _write_json(SET_ARTICLE_COUNT, so)

    ten_hien = NAME_ROLE_IMAGE.get(vai_anh, "Ethan")
    # Ong Chu 08/09/2026: bo cum "X viet caption sau khi duyet anh" — thua, ai
    # cung biet quy trinh, khong can nhac lai moi lan giao task. Cung luat voi
    # approve_pick.py (bao cao chon tin) — sot lai o day vi hai cho viet rieng.
    dong = ("✅ <b>" + html_escape(title) + "</b>\n"
            + f"{ten_hien} dựng ảnh ({brand}) — task {tid}")
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
    if not is_boss(msg):
        tra_loi("Lệnh slash chỉ nhận từ Ông Chủ. (id của bạn: <code>"
                + str(msg.get("from", {}).get("id")) + "</code>)")
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
        tra_loi(COMMAND_HELP)
    elif lenh == "/vai":
        dong = [f"<b>Vai ảnh</b> (brand cố định của container: {BRAND}):"]
        for ten, va in sorted(ROLE_IMAGE.items()):
            kieu = ("carousel deck" if va in ROLE_EDU
                    else "carousel" if va in ROLE_CAROUSEL else "thẻ bìa")
            dong.append(f"  <code>{ten}</code> → {va} ({kieu})")
        viet = ", ".join(f"<code>{s}</code>" for s in sorted(NAME_ROLE_WRITE))
        dong.append(f"<b>Vai viết</b>: {viet} — duyệt ảnh xong thì giao cho người viết "
                    "đang ít việc chờ hơn (blog: Miles/Jika, dcgr: Miles).")
        tra_loi("\n".join(dong))
    elif lenh == "/bai":
        with _KHOA_DAT_BAI:
            _command_article(tra_loi, phan[1:])
    else:
        tra_loi("Không có lệnh " + html_escape(lenh) + " — /help để xem. "
                "Sai lệnh thì không làm gì.")
