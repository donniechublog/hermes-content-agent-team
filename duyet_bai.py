#!/usr/bin/env python3
"""duyet_bai.py — NUT BAM tren ban nhap va tren album anh: Duyet/Bo/Lam lai (hoi ly
do, het han), chuyen Kite khi thieu anh that, dang len kenh, day ban nhap vao
hang duyet. Tach tu approve_service.py 06/09/2026 (di chuyen thuan).
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
    API, DRAFTS, ONG_CHU_IDS, ROOT, STATE_DIR, _boc_dong, _chay_nen, _ghi_json, _gui_chu, _khoa_cua, _nap_json, _reply_that, call, log, rut,
)
from duyet_giao_viec import (  # noqa: E402
    BANG_DEN_NHAC, TEN_VAI_ANH, TEN_VAI_VIET, _bang_den_ghi, _bao_nhan_viec, _trang_thai_task, kanban_create,
)


def _xu_ly_nut(token, channel, cq):
    """Nut bam chay o thread NEN (qua _chay_nen): tao task kanban + ghi bang den
    toi ~2 phut, truoc day chay tren chinh thread poll nen moi nut/tin khac xep
    hang theo (audit 05/09/2026). Khoa theo draft de hai lan bam cung mot bai
    van chay lan luot — cac chot trang thai trong handle_callback giu nguyen
    y nghia nhu khi con tuan tu."""
    draft_id = cq.get("data", "").partition(":")[2]
    with _khoa_cua(draft_id):
        try:
            handle_callback(token, channel, cq)
        except Exception as e:                               # noqa: BLE001
            call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                 text=f"Lỗi: {type(e).__name__}: {str(e)[:150]}", show_alert=True)
            raise                                            # _chay_nen ghi traceback + bao topic

def keyboard(draft_id):
    return {"inline_keyboard": [[
        {"text": "✅ Duyệt & đăng", "callback_data": "ok:" + draft_id},
        {"text": "❌ Bỏ", "callback_data": "no:" + draft_id},
    ]]}

def _send_media_group(token, chat, media, thread_id=None):
    """Gui album anh xem truoc. Album KHONG the gan nut bam -- gioi han Bot API.

    `media` la duong dan CUC BO (draft_write ghi duong dan tuyet doi tren may
    nay) nen phai upload bang attach:// nhu publish() lam. Truoc day gui thang
    chuoi duong dan cho Telegram — Telegram khong doc duoc may minh, album KHONG
    BAO GIO hien, va gia tri tra ve bi vut nen loi im lang: Ong Chu duyet mu moi
    bai nhieu anh tu ngay dau."""
    items, files = [], {}
    for i, m in enumerate(media):
        m = str(m)
        if m.startswith("http://") or m.startswith("https://"):
            items.append({"type": "photo", "media": m})
        else:
            if not Path(m).exists():
                continue
            key = f"file{i}"
            items.append({"type": "photo", "media": f"attach://{key}"})
            files[key] = open(m, "rb")
    if not items:
        return {"ok": False, "description": "khong co anh nao ton tai"}
    data = {"chat_id": chat, "media": json.dumps(items)}
    if thread_id:
        data["message_thread_id"] = str(int(thread_id))
    try:
        with httpx.Client(timeout=120) as c:
            r = c.post(API.format(token=token, method="sendMediaGroup"),
                       data=data, files=files or None)
    finally:
        for fh in files.values():
            fh.close()
    return r.json()

def draft_push(token, group, draft_id, thread_id=None):
    d = json.loads((DRAFTS / (draft_id + ".json")).read_text(encoding="utf-8"))
    caption = "<b>BẢN NHÁP</b>\n\n" + d["caption"]
    payload = {"chat_id": group, "caption": caption, "parse_mode": "HTML",
               "reply_markup": keyboard(draft_id)}
    if thread_id:
        payload["message_thread_id"] = int(thread_id)

    images = d.get("images")
    if images:
        # Album truoc (khong nut), roi tin nhan chu rieng kem nut duyet --
        # nut bam luon nam tren tin nhan NAY, khong phai anh.
        ra = _send_media_group(token, group, images, thread_id)
        if not ra.get("ok"):
            # KHONG nuot loi: Ong Chu phai biet minh dang duyet thieu anh.
            caption += ("\n\n\u26a0\ufe0f Album xem truoc gui loi: "
                        + html_escape(str(ra.get("description"))))
        text_payload = {"chat_id": group, "text": caption, "parse_mode": "HTML",
                        "reply_markup": keyboard(draft_id)}
        if thread_id:
            text_payload["message_thread_id"] = int(thread_id)
        return call(token, "sendMessage", **text_payload)

    img = d.get("image")
    if img and Path(img).exists():
        with httpx.Client(timeout=120) as c, open(img, "rb") as fh:
            r = c.post(API.format(token=token, method="sendPhoto"),
                       data={k: (json.dumps(v) if k == "reply_markup" else v)
                             for k, v in payload.items()},
                       files={"photo": (Path(img).name, fh, "image/png")})
        return r.json()
    payload["text"] = payload.pop("caption")
    return call(token, "sendMessage", **payload)

CAPTION_LIMIT = 1024      # gioi han caption cua sendPhoto / sendMediaGroup

def publish(token, channel, draft_id):
    """Dang draft len channel.

    Caption dai (teaser thuong 3000+ ky tu) VUOT gioi han 1024 cua caption anh.
    Truong hop do: gui anh truoc khong caption, roi gui chu rieng — thay vi de
    Telegram tu choi ca bai.
    """
    d = json.loads((DRAFTS / (draft_id + ".json")).read_text(encoding="utf-8"))
    caption = d["caption"]
    long_caption = len(caption) > CAPTION_LIMIT

    images = d.get("images")
    if images:
        # Anh co the la URL (teaser lay tu bai goc) HOAC tep cuc bo (the do vai dung anh
        # dung + anh that tai ve). Tep cuc bo phai dinh kem multipart qua
        # attach://, khong the truyen duong dan — Telegram khong doc duoc o may ta.
        items, files = [], {}
        for i, m in enumerate(images[:10]):          # Telegram cho toi da 10
            e = {"type": "photo"}
            if str(m).startswith("http"):
                e["media"] = str(m)
            else:
                pth = Path(m)
                if not pth.exists():
                    continue
                khoa = f"anh{i}"
                e["media"] = f"attach://{khoa}"
                files[khoa] = (pth.name, pth.read_bytes(), "image/png")
            if not items and not long_caption:
                e["caption"] = caption
                e["parse_mode"] = "HTML"
            items.append(e)
        with httpx.Client(timeout=180) as c:
            r = c.post(API.format(token=token, method="sendMediaGroup"),
                       data={"chat_id": channel, "media": json.dumps(items)},
                       files=files or None)
        res = r.json()
        if long_caption and res.get("ok"):
            return _gui_chu(token, channel, caption)
        return res

    img = d.get("image")
    if img and Path(img).exists():
        with httpx.Client(timeout=120) as c, open(img, "rb") as fh:
            data = {"chat_id": channel, "parse_mode": "HTML"}
            if not long_caption:
                data["caption"] = caption
            r = c.post(API.format(token=token, method="sendPhoto"),
                       data=data,
                       files={"photo": (Path(img).name, fh, "image/png")})
        res = r.json()
        if long_caption and res.get("ok"):
            return _gui_chu(token, channel, caption)
        return res
    return _gui_chu(token, channel, caption)

def mark_draft(draft_id, status):
    p = DRAFTS / (draft_id + ".json")
    d = json.loads(p.read_text(encoding="utf-8"))
    d["status"] = status
    d["decided_at"] = int(time.time())
    _ghi_json(p, d)

def _tach_ly_do_lam_lai(text):
    """'4: chart bi cat' -> ('4', 'chart bi cat'); '2,5: ...' -> ('2, 5', ...);
    'tat ca: ...' -> ('CA BO', ...); khong co so -> (None, ca cau)."""
    t = (text or "").strip()
    m = re.match(r"^\s*(tất cả|tat ca|cả bộ|ca bo|all)\s*[:\-–—]?\s*(.*)$", t, re.I | re.S)
    if m:
        return "CA BO", m.group(2).strip()
    m = re.match(r"^\s*(?:slide|ảnh|anh)?\s*#?\s*(\d[\d\s,]*)\s*[:\-–—]\s*(.*)$", t, re.I | re.S)
    if m:
        so = sorted({int(x) for x in re.findall(r"\d+", m.group(1))})
        return ", ".join(str(x) for x in so), m.group(2).strip()
    return None, t

def _giao_lam_lai(draft_id, slide=None, ly_do=None):
    """Tao task lam lai cho draft. Tra ve (note, rid). `slide`/`ly_do` None = giao
    theo kieu cu (khong chi ro). Ca ba duong (co ly do / het han / kieu cu) deu
    di qua day de body task chi co MOT cho viet."""
    ip = DRAFTS / (draft_id + ".img.json")
    if not ip.exists():
        return "⚠️ Không thấy thông tin task ảnh để làm lại", None
    im = json.loads(ip.read_text(encoding="utf-8"))
    n = int(im.get("remakes", 0)) + 1
    if ly_do:
        chi_ro = (
            f"\n\n== LAM LAI (lan {n}) ==\n"
            "Ong Chu bam lam lai va CHI RO cho chua dat:\n"
            f"  SLIDE:  {slide or 'khong chi ro (xem ly do)'}\n"
            f"  LY DO:  {ly_do}\n"
            "Sua DUNG cho da chi, dung doi lung tung cai khac.\n"
            "- Carousel: dung lai spec cu, chi thay anh/copy cua slide da neu (cac "
            "slide khac giu nguyen), roi chay lai carousel.py de ra CA BO (album "
            "phai du slide).\n"
            "- Doc lai LUAT_ANH.md truoc khi chon anh moi: ly do o tren thuong "
            "tuong ung mot cong o do (chart nguyen ven, mat nguoi, hai vung...).\n"
            f"Van day len kem nut duyet nhu cu (--duyet {draft_id}).")
    else:
        chi_ro = (
            f"\n\n== LAM LAI (lan {n}) ==\n"
            "Anh truoc CHUA DAT, Ong Chu bam lam lai (khong neu ly do cu the). Chon "
            "ANH KHAC — goc khac, nguon khac, cach the hien khac; DUNG lap lai anh "
            f"cu. Van day len kem nut duyet nhu cu (--duyet {draft_id}).")
    tieu = ("Carousel (lam lai): " if im.get("carousel") else "Anh (lam lai): ") \
        + im.get("title", draft_id)
    # Bang den: task lam lai cung la con cua the goc, va tro thanh `dre_task` moi
    # trong .writer.json — de luc bam Duyet, Miles noi vao BAN LAM LAI (ban giao
    # moi nhat trong "Parent task results"), khong phai ban dau. Khong co the goc
    # (bai truoc 05/09, hoac brand chua bat) thi y nhu cu.
    wp = DRAFTS / (draft_id + ".writer.json")
    try:
        w = json.loads(wp.read_text(encoding="utf-8")) if wp.exists() else {}
    except Exception:                                        # noqa: BLE001
        w = {}
    rid, err = kanban_create(tieu, im["vai_anh"], im["body"] + chi_ro,
                             parent=w.get("root_task"))
    if err:
        return "⚠️ Làm lại lỗi: " + str(err), None
    if w.get("root_task"):
        w["dre_task"] = rid
        try:
            _ghi_json(wp, w)
        except OSError as e:
            log("bangden", f"{draft_id}: khong cap nhat dre_task: {e}")
        _bang_den_ghi(draft_id, "lam_lai",
                      {"lan": n, "slide": slide, "ly_do": ly_do, "task": rid,
                       "task_truoc": im.get("last_task")})
    im["remakes"], im["last_task"] = n, rid
    if ly_do:
        im.setdefault("ly_do_lam_lai", []).append({"lan": n, "slide": slide, "ly_do": ly_do})
    _ghi_json(ip, im)
    ten = TEN_VAI_ANH.get(im["vai_anh"], "Ethan")
    if ly_do:
        cho = f"slide {slide}" if slide and slide != "CA BO" else ("cả bộ" if slide == "CA BO" else "ảnh")
        return (f"🔄 Đã giao làm lại {cho} (lần {n}) — {ten} — lý do: {ly_do[:120]} "
                f"(task {rid})"), rid
    return f"🔄 Đã giao làm lại (lần {n}) — {ten} sẽ dựng ảnh khác (task {rid})", rid

# Doc-sua-ghi lam_lai_cho.json dien ra o HAI thread: nut Lam lai chay nen
# (_chay_nen) con han 10 phut quet o thread poll. Khoa nay chi om cac doan doc-
# ghi ngan (mot tep JSON nho), KHONG bao gio om lenh mang hay kanban_create.
_KHOA_LAM_LAI = threading.Lock()

def _nap_lam_lai_cho() -> dict:
    """Ban ghi "dang cho ly do lam lai", KHOA THEO DRAFT_ID.

    Vi sao doi khoa (06/09/2026): truoc day khoa la thread_id, ma mot topic
    (carousel cua Dre) thuong co nhieu bo cho duyet cung luc. Bam Lam lai bai A
    roi bam Lam lai bai B trong vong 10 phut thi ban ghi cua A bi ghi de IM
    LANG, trong khi nut cua A da doi chu thanh "Cho ly do lam lai" nen khong
    bam lai duoc nua: A khong bao gio duoc giao lam lai. Ban ghi CU (khoa la
    thread_id, chua co truong thread_id) van doc duoc de bai dang cho luc
    restart khong mat."""
    tho = _nap_json(LAM_LAI_CHO, {})
    ra = {}
    if not isinstance(tho, dict):
        return ra
    for k, v in tho.items():
        if not isinstance(v, dict) or not v.get("draft_id"):
            continue
        if "thread_id" not in v:          # ban ghi cu: khoa CHINH la thread_id
            v = dict(v, thread_id=(int(k) if str(k).lstrip("-").isdigit() else None))
        ra[v["draft_id"]] = v
    return ra

def _cho_trong_topic(cho: dict, thread_id) -> list:
    """Cac bai dang cho ly do trong DUNG mot topic."""
    return [v for v in cho.values() if str(v.get("thread_id")) == str(thread_id)]

def _qua_han(v: dict) -> bool:
    """Ban ghi cho ly do da qua LAM_LAI_HAN (vong poll chua kip don). `ts` rac
    cung tinh la qua han — de ket con te hon giao theo kieu cu."""
    try:
        return time.time() - float(v.get("ts", 0)) >= LAM_LAI_HAN
    except (TypeError, ValueError):
        return True

def _nhan_ly_do_lam_lai(token, group, msg, thread_id, text):
    """Neu topic nay dang CHO ly do lam lai va nguoi go la Ong Chu -> nuot tin
    nhan nay lam ly do, giao task, tra ve True. Khong thi False (tin di tiep
    duong binh thuong)."""
    with _KHOA_LAM_LAI:
        cho = _nap_lam_lai_cho()
        ds = _cho_trong_topic(cho, thread_id)
        if not ds:
            return False
        uid = msg.get("from", {}).get("id")
        cho_phep = _nap_json(ONG_CHU_IDS, [])
        if cho_phep and uid not in cho_phep:
            return False                  # nguoi khac go, khong phai tra loi cua Ong Chu
        # CHI nhan khi la REPLY toi dung tin hoi (Ong Chu 05/09/2026). Truoc day moi
        # chu go trong topic suot 10 phut deu bi nuot lam ly do — hoi Dre chuyen khac
        # cung thanh "ly do lam lai". Tin hoi da bat force_reply nen reply la mac dinh;
        # go tron thi tin di duong chat binh thuong, trang thai cho van giu.
        # `hoi_mid` con la thu DUY NHAT noi cau tra loi nay thuoc bai nao khi topic
        # co nhieu bo cho (06/09/2026) — doan mo la giao lam lai nham bai.
        rt = _reply_that(msg) or {}
        mid = rt.get("message_id")
        ho_so = next((v for v in ds if v.get("hoi_mid") and v["hoi_mid"] == mid), None)
        if ho_so is None:
            # Ban ghi khong co hoi_mid (tin hoi gui loi, hoac ban ghi cu truoc
            # 06/09) thi lui ve luat cu "reply toi mot tin cua bot" — chi cho
            # phep khi topic dang cho DUY NHAT mot bai, khong thi khong doan.
            thieu = [v for v in ds if not v.get("hoi_mid")]
            if len(ds) == 1 and thieu and rt.get("from", {}).get("is_bot"):
                ho_so = thieu[0]
        if ho_so is None:
            return False
        cho.pop(ho_so["draft_id"], None)
        _ghi_json(LAM_LAI_CHO, cho, indent=None)
    # Giao task (kanban_create + bang den, toi 2 phut) o thread nen, khong nghen poll.
    _chay_nen("lamlai", _xu_ly_ly_do_lam_lai, token, group, thread_id,
              token, group, msg, thread_id, ho_so["draft_id"], text)
    return True

def _xu_ly_ly_do_lam_lai(token, group, msg, thread_id, draft_id, text):
    with _khoa_cua(draft_id):
        t = text.strip().lower()
        if t in ("hủy", "huy", "bỏ", "bo", "thôi", "thoi", "cancel"):
            note = "↩️ Đã huỷ làm lại — giữ nguyên ảnh hiện tại"
        elif t in ("làm lại", "lam lai", "redo", ""):
            note, _ = _giao_lam_lai(draft_id)              # khong neu ly do -> kieu cu
        else:
            slide, ly_do = _tach_ly_do_lam_lai(text)
            note, _ = _giao_lam_lai(draft_id, slide, ly_do)
    log("nut", f"lam lai co ly do draft={draft_id}: {note}")
    call(token, "sendMessage", chat_id=group,
         **({"message_thread_id": thread_id} if thread_id else {}),
         reply_to_message_id=msg.get("message_id"), text=note)

def _lam_lai_het_han(token, group):
    """Cho qua LAM_LAI_HAN giay ma Ong Chu chua neu ly do -> giao theo kieu cu,
    de khong ket. Goi moi vong poll (re: chi doc mot tep JSON nho)."""
    with _KHOA_LAM_LAI:
        cho = _nap_lam_lai_cho()
        if not cho:
            return
        het = []
        for did in list(cho):
            if _qua_han(cho[did]):
                het.append(cho.pop(did))
        if het:
            _ghi_json(LAM_LAI_CHO, cho, indent=None)
    # Bat thread NGOAI khoa: _giao_het_han om khoa draft roi goi kanban (toi 2
    # phut), giu _KHOA_LAM_LAI suot doan do se chan ca nut Lam lai lan cau tra
    # loi cua Ong Chu.
    for ho_so in het:
        tid = ho_so.get("thread_id")
        tid = int(tid) if str(tid).lstrip("-").isdigit() else None
        _chay_nen("lamlai-han", _giao_het_han, token, group, tid,
                  token, group, tid, ho_so["draft_id"])

def _giao_het_han(token, group, thread_id, draft_id):
    with _khoa_cua(draft_id):
        note, _ = _giao_lam_lai(draft_id)
    log("nut", f"lam lai het han draft={draft_id}: {note}")
    call(token, "sendMessage", chat_id=group,
         **({"message_thread_id": thread_id} if thread_id else {}),
         text="⏱ Hết 10 phút chưa nêu lý do — " + note)

def tao_task_kite(draft_id: str, im: dict, ly_do: str = "") -> tuple:
    """Chuyen mot draft anh sang Kite (carousel-edu, art vector). Tao task
    EDU_BODY, ghi img.json (vai_anh=carousel-edu, giu vai cu o chuyen_tu) de nut
    Duyet/Lam lai sau do di dung Kite. Tra ve (task_id, loi)."""
    import task_bodies
    body_cu = im.get("body", "")
    link = im.get("link") or _boc_dong(body_cu, "Link")
    summary = im.get("summary") or _boc_dong(body_cu, "Tom tat")
    source_note = im.get("source_note") or _boc_dong(body_cu, "Nguon")
    title = im.get("title", draft_id)
    body = task_bodies.EDU_BODY.format(source_note=source_note, link=link, title=title,
                                       summary=summary, goc=str(ROOT), draft_id=draft_id)
    # Engine da nhin anh: co bao nhieu tam that dung duoc? Kite phai DUNG chung
    # (Ong Chu 05/09/2026), khong ra bo toan text & card.
    co = []
    try:
        xong = STATE_DIR / "chuan_bi" / draft_id / "xong.json"
        if xong.exists():
            mm = json.loads(xong.read_text(encoding="utf-8"))
            co = [a["ma"] for a in mm.get("anh", []) if a.get("dung") and a.get("lien_quan") is not False]
    except Exception:                                           # noqa: BLE001
        co = []
    if ly_do:
        body += f"\n\n== CHUYEN TU {TEN_VAI_ANH.get(im.get('vai_anh'), im.get('vai_anh'))} ==\n{ly_do}."
        if co:
            body += (f" Engine tim duoc {len(co)} anh THAT dung duoc ({', '.join(co)}, xem brief): "
                     "BAT BUOC dua vao slide (bia image hoac figure), phan con lai ve vector.")
        else:
            body += (" Tin nay KHONG co anh that dung duoc: ve vector hoan toan, kind figure chi khi "
                     "kite_chuan_bi liet ke hinh that.")
    # Bang den: task Kite la con cua the goc va tro thanh `dre_task` (vai anh hien
    # hanh) trong .writer.json — de Miles noi vao ban giao cua Kite, khong phai cua
    # Dre da dung. Ghi muc chuyen_kite de bang den ke dung chuyen (05/09: bai Gimlet
    # di Kite nhung muc `anh` van la cua Dre ban 1).
    wp = DRAFTS / (draft_id + ".writer.json")
    try:
        w = json.loads(wp.read_text(encoding="utf-8")) if wp.exists() else {}
    except Exception:                                           # noqa: BLE001
        w = {}
    if w.get("root_task"):
        body += BANG_DEN_NHAC.format(root=w["root_task"])
    rid, err = kanban_create("Carousel deck: " + title, "carousel-edu", body,
                             parent=w.get("root_task"))
    if err:
        return None, err
    if w.get("root_task"):
        w["dre_task_truoc_kite"], w["dre_task"] = w.get("dre_task"), rid
        try:
            _ghi_json(wp, w)
        except OSError as e:
            log("bangden", f"{draft_id}: khong cap nhat dre_task (kite): {e}")
        _bang_den_ghi(draft_id, "chuyen_kite",
                      {"task": rid, "tu_vai": im.get("vai_anh"), "ly_do": ly_do,
                       "anh_that_dung_duoc": co})
    im.update({"chuyen_tu": im.get("vai_anh"), "vai_anh": "carousel-edu", "carousel": True,
               "body": body, "chuyen_kite": rid, "ly_do_chuyen": ly_do})
    _ghi_json(DRAFTS / (draft_id + ".img.json"), im)
    return rid, None

def handle_img_approval(token, action, draft_id, cq):
    """Cong duyet ANH truoc khi viet. designer (Ethan)/Dre/Dre day anh len topic kem
    ba nut:
      imgok    (Duyet)   -> sinh task viet caption (writer_body cat san o
                            `<draft_id>.writer.json`).
      imgredo  (Lam lai) -> tao lai task ANH (body cat o `<draft_id>.img.json`,
                            them ghi chu chon anh khac) -> designer dung lai.
      imgno    (Bo han)  -> giet tin: khong viet, khong lam lai."""
    msg = cq["message"]
    chat_id, msg_id = msg["chat"]["id"], msg["message_id"]
    wp = DRAFTS / (draft_id + ".writer.json")

    if action == "imgno":
        try:
            w = json.loads(wp.read_text(encoding="utf-8")) if wp.exists() else {}
        except Exception:                                       # noqa: BLE001
            w = {}
        if w.get("created") is True:
            # Da bam Duyet truoc do (writer dang chay) — khong bo han nua de tranh
            # trang thai mau thuan (task viet da ton tai ma sidecar lai 'rejected').
            note = "⚠️ Bài đã duyệt, đang viết — không bỏ hẳn được nữa"
            call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                 text="Đã duyệt trước đó, không bỏ", show_alert=True)
        else:
            note = "🗑 Đã bỏ hẳn tin — không viết, không làm lại"
            call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                 text="Đã bỏ hẳn")
            if wp.exists():
                try:
                    w["created"] = "rejected"
                    _ghi_json(wp, w)
                except Exception as e:                          # noqa: BLE001
                    # Khong ghi duoc sidecar nghia la lenh bo KHONG dinh: bam
                    # Duyet sau do van sinh task viet cho tin da giet. Phai noi.
                    note = ("⚠️ Bỏ hẳn nhưng KHÔNG ghi được trạng thái ("
                            + type(e).__name__ + ") — bấm Bỏ hẳn lại lần nữa")
    elif action == "imgkite":
        ip = DRAFTS / (draft_id + ".img.json")
        if not ip.exists():
            note = "⚠️ Không thấy thông tin task ảnh"
            call(token, "answerCallbackQuery", callback_query_id=cq["id"], text=note, show_alert=True)
        else:
            im = json.loads(ip.read_text(encoding="utf-8"))
            if im.get("chuyen_kite"):
                note = f"↪️ Đã chuyển Kite trước đó (task {im['chuyen_kite']})"
                call(token, "answerCallbackQuery", callback_query_id=cq["id"], text=note)
            else:
                call(token, "answerCallbackQuery", callback_query_id=cq["id"], text="Đang giao Kite…")
                rid, err = tao_task_kite(draft_id, im, ly_do="Ong Chu bam Gui Kite (thieu anh that)")
                note = ("⚠️ Chuyển Kite lỗi: " + str(err)) if err else \
                       f"🎨 Đã giao Kite vẽ vector (task {rid}) — {TEN_VAI_ANH.get(im.get('chuyen_tu'), 'vai cũ')} dừng bộ này"
                if not err:
                    _bao_nhan_viec(token, chat_id, "carousel-edu", im.get("chuyen_tu"),
                                   im.get("title", draft_id), rid,
                                   ly_do="thiếu ảnh thật, Ông Chủ chuyển sang vẽ vector")
    elif action == "imgtiep":
        # Truoc 06/09/2026 nhanh nay chi in mot dong roi thoi: `toi_thieu` trong
        # xong.json van nguyen (8 voi tin flagship), nen dre_nop van chan "chi N
        # slide, can toi thieu 8" — bam nut xong van khong lam duoc, ngo cut.
        # Gio HA SAN that: ve `toi_thieu_co_ban` (san cua carousel.py). Duoi san
        # do thi carousel khong dung duoc, phai noi thang chu khong hua suong.
        xong = STATE_DIR / "chuan_bi" / draft_id / "xong.json"
        try:
            mm = json.loads(xong.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            mm = {}
        san = int(mm.get("toi_thieu_co_ban", 5))
        so = int(mm.get("so_dung_duoc", 0))
        cu = int(mm.get("toi_thieu", san))
        if not mm:
            note = "⚠️ Không đọc được bản chuẩn bị (xong.json) — chưa hạ sàn được, vai vẫn bị chặn như cũ"
            call(token, "answerCallbackQuery", callback_query_id=cq["id"], text="Thiếu xong.json", show_alert=True)
        elif so < san:
            note = (f"⚠️ Chỉ {so} ảnh thật mà carousel cần tối thiểu {san} slide — "
                    f"bấm tiếp cũng không dựng được. Chuyển Kite vẽ vector, hoặc bỏ tin.")
            call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                 text=f"Không đủ: {so} ảnh < {san} slide", show_alert=True)
        elif cu <= san:
            note = f"🖼 Sàn đã ở mức tối thiểu {san} slide — vai làm với {so} ảnh hiện có"
            call(token, "answerCallbackQuery", callback_query_id=cq["id"], text="OK, làm với số ảnh hiện có")
        else:
            mm["toi_thieu"] = san
            mm["ha_san_luc"] = int(time.time())
            try:
                tmp = xong.with_suffix(".json.tmp")
                tmp.write_text(json.dumps(mm, ensure_ascii=False, indent=1), encoding="utf-8")
                tmp.replace(xong)
                note = (f"🖼 Đã hạ sàn {cu} → {san} slide cho bài này: vai ảnh làm với "
                        f"{so} ảnh thật hiện có (gộp ý / giảm slide)")
                call(token, "answerCallbackQuery", callback_query_id=cq["id"], text=f"Hạ sàn còn {san} slide")
            except OSError as e:
                note = f"⚠️ Không ghi được xong.json ({type(e).__name__}) — sàn vẫn {cu}, vai sẽ còn bị chặn"
                call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                     text="Ghi xong.json lỗi", show_alert=True)
    elif action == "imgredo":
        # Ong Chu 04/09/2026: bam Lam lai phai co cho de noi SLIDE NAO va VI SAO.
        # Chi bam "lam lai" thi vai khong biet sua cho nao, lan sau van co the sai
        # y nhu cu. Nen KHONG giao ngay: ghi "dang cho ly do" cho topic nay, hoi
        # mot dong, va nuot tin nhan ke tiep cua Ong Chu lam ly do
        # (_nhan_ly_do_lam_lai). Het LAM_LAI_HAN giay chua tra loi -> giao kieu cu.
        ip = DRAFTS / (draft_id + ".img.json")
        if not ip.exists():
            note = "⚠️ Không thấy thông tin task ảnh để làm lại"
            call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                 text="Thiếu thông tin ảnh", show_alert=True)
        else:
            im = json.loads(ip.read_text(encoding="utf-8"))
            thread_id = msg.get("message_thread_id")
            # MOT topic chi cho ly do cua MOT bai mot luc: cau tra loi cua Ong Chu
            # la mot dong chu, khong mang dau hieu nao ve bai ngoai tin duoc reply.
            # Topic dang cho bai khac thi noi ro va GIU NGUYEN nut cua bai nay de
            # bam lai sau (thoat som, khong xuong doan go ban phim o cuoi ham).
            with _KHOA_LAM_LAI:
                cho = _nap_lam_lai_cho()
                khac = [v for v in _cho_trong_topic(cho, thread_id)
                        if v.get("draft_id") != draft_id and not _qua_han(v)]
                if not khac:
                    cho[draft_id] = {"draft_id": draft_id, "thread_id": thread_id,
                                     "ts": time.time(),
                                     "title": im.get("title", draft_id)}
                    _ghi_json(LAM_LAI_CHO, cho, indent=None)
            if khac:
                log("nut", f"imgredo {draft_id}: topic {thread_id} dang cho ly do "
                           f"cua {khac[0].get('draft_id')} -> khong nhan, giu nut")
                call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                     text="Đang chờ lý do bài: " + str(khac[0].get("title", ""))[:110]
                          + " — trả lời bài đó trước rồi bấm lại nút này.",
                     show_alert=True)
                return
            call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                 text="Chờ anh nêu slide + lý do…")
            n = int(im.get("remakes", 0)) + 1
            if im.get("carousel"):
                huong_dan = ("Trả lời <b>một dòng</b>: <code>số slide: lý do</code>\n"
                             "Vd: <code>4: chart bị cắt mất trục x</code> · nhiều slide: "
                             "<code>2,5: ...</code> · cả bộ: <code>tất cả: ...</code>")
            else:
                huong_dan = ("Trả lời <b>lý do</b> ảnh chưa đạt, vd: <code>mặt người lạ</code>, "
                             "<code>chart bị cắt</code>, <code>nửa dưới quá rối</code>")
            # force_reply: Telegram tu bat "tra loi tin nay" -> cau ly do cua Ong Chu la
            # REPLY toi bot duyet. Gateway (bot chat) duoc va de bo qua moi tin reply toi
            # bot khac (adapter, 05/09) -> het canh hai bot cung dap mot cau.
            r_hoi = call(token, "sendMessage", chat_id=chat_id,
                 **({"message_thread_id": thread_id} if thread_id else {}),
                 parse_mode="HTML", reply_markup={"force_reply": True, "selective": False},
                 text=(f"🔄 Làm lại <b>{im.get('title', draft_id)}</b> (lần {n}).\n"
                       + huong_dan + "\n"
                       "<b>Trả lời (reply) vào đúng tin này.</b> Chữ gõ rời sẽ được coi là chat, "
                       "không phải lý do. Reply <code>hủy</code> để không làm lại. "
                       "Không trả lời trong 10 phút → giao theo kiểu cũ (chỉ \"chọn ảnh khác\")."))
            try:                       # nho message_id tin hoi: chi nhan reply toi dung no
                _mid_hoi = (r_hoi.get("result") or {}).get("message_id")
                if _mid_hoi:
                    # Doc lai trong khoa: giua hai doan nay la mot lenh mang, han
                    # 10 phut o thread poll co the vua don ban ghi khac.
                    with _KHOA_LAM_LAI:
                        cho = _nap_lam_lai_cho()
                        if draft_id in cho:
                            cho[draft_id]["hoi_mid"] = _mid_hoi
                            _ghi_json(LAM_LAI_CHO, cho, indent=None)
            except Exception as _e:                              # noqa: BLE001
                log("nut", f"khong luu hoi_mid: {type(_e).__name__}: {_e}")
            note = f"⏳ Chờ lý do làm lại (lần {n})"
    else:                                                       # imgok
        if not wp.exists():
            note = "⚠️ Không thấy thông tin bài (writer sidecar) cho draft này"
            call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                 text="Thiếu thông tin bài", show_alert=True)
        else:
            w = json.loads(wp.read_text(encoding="utf-8"))
            if w.get("created") is True:
                note = "✅ Đã duyệt rồi — bài đang được viết"
                call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                     text="Đã duyệt trước đó")
            elif w.get("created") == "rejected":
                note = "🗑 Tin này đã bỏ hẳn trước đó — không viết"
                call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                     text="Đã bỏ hẳn", show_alert=True)
            else:
                call(token, "answerCallbackQuery", callback_query_id=cq["id"],
                     text="Đang giao cho người viết…")
                # Ban giao tu vai anh (dre_nop.py ghi: link that, nguon tung anh)
                # dan thang vao task viet — Miles khong phai hoi lai, Dre khong
                # phai "nhan Miles".
                _body = w["body"]
                _bg = DRAFTS / (draft_id + ".ban_giao.md")
                if _bg.exists():
                    _body += ("\n\n== BAN GIAO TU VAI ANH (tu dong) ==\n"
                              + _bg.read_text(encoding="utf-8"))
                # Bang den: Miles la con cua the goc + task Dre -> thay ban giao
                # cua Dre trong "Parent task results". Chi noi voi cha DA done:
                # sau "Lam lai" task Dre cu co the blocked, noi vao la Miles
                # nam todo mai.
                _cha = [t for t in (w.get("root_task"), w.get("dre_task"))
                        if t and _trang_thai_task(t) == "done"]
                if w.get("root_task"):
                    _body += BANG_DEN_NHAC.format(root=w["root_task"])
                wid, err = kanban_create("Bai: " + w.get("title", draft_id),
                                         w["vai_viet"], _body, parent=_cha)
                if err:
                    note = "⚠️ Duyệt ok nhưng tạo task viết lỗi: " + str(err)
                else:
                    w["created"], w["writer_task"] = True, wid
                    _ghi_json(wp, w)
                    ten = TEN_VAI_VIET.get(w["vai_viet"], "Miles")
                    note = f"✅ Đã duyệt ảnh — {ten} bắt đầu viết caption (task {wid})"

    log("nut", f"ket qua imgok/imgno/imgredo draft={draft_id}: {note}")
    base = msg.get("caption") or msg.get("text") or ""
    method = "editMessageCaption" if msg.get("caption") else "editMessageText"
    key = "caption" if msg.get("caption") else "text"
    r = call(token, method, chat_id=chat_id, message_id=msg_id,
             **{key: base + "\n\n<b>" + html_escape(note) + "</b>"},
             parse_mode="HTML", reply_markup={"inline_keyboard": []})
    if not r.get("ok"):
        call(token, "editMessageReplyMarkup", chat_id=chat_id, message_id=msg_id,
             reply_markup={"inline_keyboard": []})

def handle_callback(token, channel, cq):
    data = cq.get("data", "")
    action, _, draft_id = data.partition(":")
    msg = cq["message"]

    # Duyet ANH (truoc khi viet) — xu ly SOM vi luc nay ban nhap cuoi
    # (<draft>.json) chua ton tai, nhanh duoi se bao "khong tim thay ban nhap".
    if action in ("imgok", "imgno", "imgredo", "imgkite", "imgtiep"):
        handle_img_approval(token, action, draft_id, cq)
        return

    p = DRAFTS / (draft_id + ".json")
    if not p.exists():
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Không tìm thấy bản nháp", show_alert=True)
        return

    # CHOT TRANG THAI TRUOC KHI LAM GI KHAC. publish() co the mat toi 180s,
    # trong thoi gian do nut van quay vong va Ong Chu se bam lai — hai callback
    # xep hang, va truoc day ca hai deu dang. Doc status som + tra loi callback
    # NGAY de nut thoi quay, roi moi lam viec nang.
    try:
        st = json.loads(p.read_text(encoding="utf-8")).get("status")
    except Exception:                                        # noqa: BLE001
        st = None
    if st in ("published", "rejected"):
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Bài này đã xử lý rồi (" + st + ")", show_alert=True)
        return

    if st == "publishing":
        # Dang co thread dang bai nay (publish chay NEN, xem _dang_nen). Truoc
        # day publish chay dong bo nen callback thu hai tu xep hang sau; nay
        # phai chan tuong minh de hai thread khong cung dang mot bai.
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Đang đăng — chờ chút", show_alert=True)
        return

    if action == "ok":
        # Danh dau DANG XU LY roi tra callback NGAY; viec nang (upload toi 180s
        # + moat) chay o thread NEN de vong poll khong nghen — nut cua bai khac
        # va chat van bam duoc, cung ly do voi handle_chat/handle_command.
        mark_draft(draft_id, "publishing")
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Đang đăng…")
        threading.Thread(target=_dang_nen, daemon=True,
                         args=(token, channel, draft_id, msg)).start()
        return
    elif action == "no":
        mark_draft(draft_id, "rejected")
        note = "❌ ĐÃ BỎ — không đăng"
        call(token, "answerCallbackQuery", callback_query_id=cq["id"],
             text="Đã bỏ bài")
    else:
        return

    _sua_tin_go_nut(token, msg, note)

def _dang_nen(token, channel, draft_id, msg):
    """Phan nang cua nut Duyet, chay trong thread rieng. Moi duong loi deu phai
    ra trang thai ro rang: publish_failed cho bam Duyet lai duoc — khong bao
    gio ket vinh vien o 'publishing' (truoc day exception giua chung se ket)."""
    try:
        res = publish(token, channel, draft_id)
        ok = res.get("ok")
        mark_draft(draft_id, "published" if ok else "publish_failed")
        note = ("✅ ĐÃ ĐĂNG lên channel" if ok
                else "⚠️ Đăng lỗi: " + str(res.get("description")))
        # Bai da len channel thi day tiep sang moat cho extension dang len social.
        # Chi day khi Telegram da nhan -- khong dang duoc o day thi bai chua duyet xong.
        # Loi ben moat chi them mot dong vao the, KHONG lam hong luong duyet.
        if ok:
            pushed, why = moat_publish.intake(draft_id)
            note += ("\n\U0001f4e4 moat: " + why) if pushed else ("\n\u26a0\ufe0f moat: " + why)
    except Exception as e:                                   # noqa: BLE001
        try:
            mark_draft(draft_id, "publish_failed")
        except Exception:                                    # noqa: BLE001
            pass
        note = "⚠️ Đăng lỗi: " + type(e).__name__ + ": " + str(e)
    _sua_tin_go_nut(token, msg, note)

def _sua_tin_go_nut(token, msg, note):
    """Ghi ket qua vao tin nhan draft va go ban phim (dung chung cho nhanh Bo
    tren poll thread va nhanh Duyet chay nen)."""
    log("nut", f"ket qua msg={msg.get('message_id')}: {note}")
    chat_id, msg_id = msg["chat"]["id"], msg["message_id"]
    base = msg.get("caption") or msg.get("text") or ""
    body = base.replace("BẢN NHÁP", "BẢN NHÁP (đã xử lý)", 1)
    method = "editMessageCaption" if msg.get("caption") else "editMessageText"
    key = "caption" if msg.get("caption") else "text"
    # `note` co the chua text tho tu moat (trang HTML 502 cua nginx...). Khong
    # escape thi editMessageText bi tu choi -> inline_keyboard khong duoc go ->
    # nut van con, moi bam tiep. Escape TOAN BO note vi minh chi chen <b> quanh no.
    r = call(token, method, chat_id=chat_id, message_id=msg_id,
             **{key: body + "\n\n<b>" + html_escape(note) + "</b>"},
             parse_mode="HTML", reply_markup={"inline_keyboard": []})
    if not r.get("ok"):
        # Khong sua duoc tin nhan (vi du body cu co ky tu la) thi it nhat go nut.
        call(token, "editMessageReplyMarkup", chat_id=chat_id, message_id=msg_id,
             reply_markup={"inline_keyboard": []})

LAM_LAI_CHO = STATE_DIR / "lam_lai_cho.json"  # {draft_id: {draft_id, thread_id, ts, ...}} — dang cho ly do

LAM_LAI_HAN = 600                              # giay cho Ong Chu neu so slide + ly do
