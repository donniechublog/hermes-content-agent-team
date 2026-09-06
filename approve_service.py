#!/usr/bin/env python3
"""Dich vu Telegram cho content-team: duyet bai (nut bam) + chon tin (reply so).

Chi MOT tien trinh duoc long-poll mot bot token voi mot offset -- Telegram
getUpdates xac nhan (va xoa khoi hang doi) MOI update tinh toi offset, khong
chi loai dang loc qua allowed_updates. Chay hai poller doc lap se lam rot
update cua nhau. Vi vay dich vu nay xu ly ca hai luong trong cung mot vong lap:

  A) callback_query -- nut Duyet/Bo tren ban nhap draft (nhu truoc)
  B) message -- Ong Chu reply so thu tu trong topic scout -> tao cap task
     vai anh + vai viet cho dung tin da chon trong manifest cua Finn
  C) lenh slash -- /bai <url> <vai> dat bai TAY tu mot URL bat ky, khong qua
     vong quet cua Finn. Tuong minh: dung cu phap moi lam, sai la bao ngan
     roi dung — KHONG roi ve hoi thoai nhu tin thuong, khong doan y.

Tu 06/09/2026 tep nay CHI con vong poll + dieu phoi tin nhan (handle_message) + CLI
`push`. Phan con lai tach theo trach nhiem, di chuyen thuan (than ham y nguyen):
  duyet_co_so.py     nen: hang so, call, ghi JSON nguyen tu, khoa draft, chay nen
  duyet_giao_viec.py bang vai, kanban_create, doc kanban.db, bang den, bao tien do
  duyet_chon_tin.py  reply so -> manifest -> create_pair (khoa theo manifest)
  duyet_bai.py       nut Duyet/Bo/Lam lai, chuyen Kite, dang kenh, day hang duyet
  duyet_chat.py      chat theo topic: FIFO moi vai + semaphore
  duyet_lenh.py      lenh slash /bai /vai /hd
Moi ten cu (ke ca ten gach duoi) van import duoc tu day — anh_chuan_bi va cac
kich ban thu khong phai doi. Trang thai dung chung (khoa, dict) la CUNG mot doi
tuong o moi module vi `from X import Y` sao chep tham chieu; khong module nao
gan lai bien toan cuc (da grep `global`), nen sao chep la an toan.
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

from duyet_co_so import (  # noqa: E402,F401 — re-export: moi ten cu van goi duoc qua approve_service.*
    API, BRAND, DRAFTS, HERMES_HOME, HERMES_PY, OFFSET, ONG_CHU_IDS, ROOT, STATE_DIR, TELEGRAM_INCOMING, _KHOA_DRAFT, _KHOA_KHOA_DRAFT, _TEN_BRAND, _boc_dong, _chay_nen, _ghi_json, _gui_chu, _khoa_cua, _nap_json, _reply_that, call, load_secrets, log, rut,
)
from duyet_giao_viec import (  # noqa: E402,F401 — re-export: moi ten cu van goi duoc qua approve_service.*
    BANG_DEN_ASSIGNEE, BANG_DEN_BRANDS, BANG_DEN_NHAC, DA_BAO_TIEN_DO, KANBAN_DB, MAC_DINH_ANH, MAC_DINH_VIET, NHAN_CHUAN, SLUG_CU, TEN_SANG_CAP, TEN_VAI_ANH, TEN_VAI_VIET, VAI_ANH, VAI_CAROUSEL, VAI_EDU, _TEN_HIEN, _bang_den_ghi, _bang_den_root, _bao_nhan_viec, _tom_tat_run, _trang_thai_task, _xong_ma_khong_giao, bao_tien_do_kanban, chuan_assignee, chuan_nhan, kanban_create, vai_cua_topic,
)
from duyet_chon_tin import (  # noqa: E402,F401 — re-export: moi ten cu van goi duoc qua approve_service.*
    MANIFEST_THEO_TOPIC, _KHOA_KHOA_MANIFEST, _KHOA_MANIFEST, _draft_id, _khoa_manifest, _la_reply_bao_cao, _xu_ly_chon, create_pair, doc_lenh_chon, latest_manifest, slugify, write_meta,
)
from duyet_bai import (  # noqa: E402,F401 — re-export: moi ten cu van goi duoc qua approve_service.*
    CAPTION_LIMIT, LAM_LAI_CHO, LAM_LAI_HAN, _KHOA_LAM_LAI, _cho_trong_topic, _dang_nen, _giao_het_han, _giao_lam_lai, _lam_lai_het_han, _nap_lam_lai_cho, _nhan_ly_do_lam_lai, _qua_han, _send_media_group, _sua_tin_go_nut, _tach_ly_do_lam_lai, _xu_ly_ly_do_lam_lai, _xu_ly_nut, draft_push, handle_callback, handle_img_approval, keyboard, mark_draft, publish, tao_task_kite,
)
from duyet_chat import (  # noqa: E402,F401 — re-export: moi ten cu van goi duoc qua approve_service.*
    VAI_CHAT_LAM_VIEC, _CHO_CHAT, _DANG_CHAY, _HANG_PHIEN, _HangFIFO, _KHOA_DANG_CHAY, _KHOA_HANG_PHIEN, _SO_SONG_SONG, _ai_dang_chay, _bo_cong_cu_chat, _chat_co_khoa, _hang_cua, boi_canh_vai, handle_chat,
)
from duyet_lenh import (  # noqa: E402,F401 — re-export: moi ten cu van goi duoc qua approve_service.*
    DAT_BAI_SO, LENH_HELP, _HOST_CAM, _KHOA_DAT_BAI, _chuan_hoa_url, _doc_trang, _lenh_bai, _url_hop_le, handle_command,
)


def _tai_anh_dinh_kem(token, msg):
    """Tai anh dinh kem (photo hoac document anh) cua tin nhan ve dia, tra ve
    duong dan cuc bo hoac None neu tin khong co anh.

    Day la khe ho THAT khien 'reply vao anh de sua' khong bao gio hoat dong
    dung: truoc gio chi CHU (text/caption) toi duoc agent qua chat_router,
    file anh thi khong — agent phai tu doan bang cach doc /tmp, drafts/,
    nhat ky gui Telegram. Ham nay dua duong dan THAT vao thang prompt, agent
    khong con phai doan."""
    file_id, ext = None, ".jpg"
    photos = msg.get("photo")
    if photos:
        file_id = photos[-1]["file_id"]          # phan tu cuoi = do phan giai cao nhat
    elif msg.get("document") and str(msg["document"].get("mime_type", "")).startswith("image/"):
        file_id = msg["document"]["file_id"]
        ten = msg["document"].get("file_name", "")
        if "." in ten:
            ext = "." + ten.rsplit(".", 1)[-1]
    if not file_id:
        return None
    try:
        r = call(token, "getFile", file_id=file_id)
        if not r.get("ok"):
            return None
        file_path = r["result"]["file_path"]
        url = f"https://api.telegram.org/file/bot{token}/{file_path}"
        with httpx.Client(timeout=30) as c:
            data = c.get(url).content
    except Exception:                              # noqa: BLE001
        return None
    TELEGRAM_INCOMING.mkdir(parents=True, exist_ok=True)
    out = TELEGRAM_INCOMING / f"{msg['message_id']}{ext}"
    out.write_bytes(data)
    return str(out)

def handle_message(token, group, msg):
    mid = msg.get("message_id")
    if msg.get("from", {}).get("is_bot"):
        return                      # tin cua chinh bot, khong log cho khoi nhieu
    if msg.get("chat", {}).get("id") != int(group):
        log("vao", f"bo qua msg={mid}: chat {msg.get('chat', {}).get('id')} "
                   f"khong phai group {group}")
        return
    # Anh/album kem caption: Telegram de chu o field "caption", KHONG phai
    # "text" (text chi co o tin nhan thuan chu). Thieu fallback nay lam moi
    # reply-kem-anh (vd sua lai anh theo yeu cau) bi handle_message am tham
    # bo qua — khong loi, khong tin nhan, chi im re. handle_callback da biet
    # phan biet hai field nay (xem dong ~268), ham nay truoc day thi khong.
    text = (msg.get("text") or msg.get("caption") or "").strip()

    # Anh dinh kem (photo hoac document anh): tai ve, dua duong dan THAT vao
    # dau text — agent doc duoc ngay, khong phai doan qua nhat ky/thu muc.
    # Tin chi co anh, khong chu (chu qua bam Reply roi gui thang anh, khong
    # go gi them) van phai di tiep, khong duoc bo som nhu truoc.
    anh_path = _tai_anh_dinh_kem(token, msg)
    if anh_path:
        text = f"[Ảnh đính kèm đã tải về: {anh_path}]\n" + (text or "(không có chú thích kèm theo)")

    thread_id = msg.get("message_thread_id")
    log("vao", f"msg={mid} thread={thread_id} vai={vai_cua_topic(thread_id)} "
               f"from={msg.get('from', {}).get('id')} text={rut(text)}")
    if not text:
        # Sticker, voice, video, file khong phai anh... — khong hieu duoc thi
        # noi ro, khong im lang (im lang = "khong phan hoi" trong mat Ong Chu).
        loai = next((k for k in ("sticker", "voice", "video", "audio", "document",
                                 "animation", "video_note", "poll", "location")
                     if k in msg), "khong ro")
        log("vao", f"msg={mid} khong co chu/anh (loai={loai}) -> bao khong ho tro")
        call(token, "sendMessage", chat_id=group,
             **({"message_thread_id": thread_id} if thread_id else {}),
             text=f"Tin dạng {loai} chưa hỗ trợ — chỉ nhận chữ và ảnh (photo hoặc file ảnh).")
        return

    # Dau "/" = LENH, o bat ky topic nao — xu ly rieng, khong bao gio roi ve
    # hoi thoai (mot lenh go sai ma dem hoi LLM la vua on ao vua nguy hiem).
    # Chay nen: /bai co buoc fetch trang + research (nguon_bai, toi 180s),
    # khong duoc nghen vong poll — cung ly do voi handle_chat ben duoi.
    if text.startswith("/"):
        log("route", f"msg={mid} lenh slash")
        _chay_nen("lenh", handle_command, token, group, thread_id,
                  token, group, msg, thread_id, text)
        return

    # Topic nay dang CHO ly do "lam lai" (Ong Chu vua bam nut)? Nuot tin nay
    # lam ly do, giao task, xong. Dat TRUOC "chon so": mot dong "4: chart bi
    # cat" ma roi vao topic chon tin se bi hieu nham thanh chon bai so 4.
    if _nhan_ly_do_lam_lai(token, group, msg, thread_id, text):
        return

    # So trong topic cua MOT VAI DI TIM TIN = lenh chon tin — NHUNG chi khi la
    # REPLY dung vao bao cao (xem _la_reply_bao_cao). Moi thu khac (ke ca dung
    # so nhung go troi, khong bam Reply) la hoi thoai. Finn, Nova, Vera deu
    # duoc — cung mot cach tra loi.
    vai = vai_cua_topic(thread_id)
    lenh = doc_lenh_chon(text) if vai in MANIFEST_THEO_TOPIC else None
    if lenh is not None:
        # Ghi lai quyet dinh cong reply: khi Ong Chu bao "go so ma khong ra bai"
        # (hoac nguoc lai) thi mot dong nay du de biet Telegram gui reply nao len
        # va cong da xu ra sao — khoi phai dung lai ban debug in nguyen JSON.
        rt_that = _reply_that(msg)
        la_reply = _la_reply_bao_cao(vai, msg)
        log("route", f"msg={mid} ung-vien-chon vai={vai} "
                     f"reply_that={rt_that.get('message_id') if rt_that else None} "
                     f"la_reply_bao_cao={la_reply}")
        if not la_reply:
            log("route", f"msg={mid} giong lenh chon nhung khong phai reply bao cao "
                         f"vai={vai} -> coi la hoi thoai")
            lenh = None
    is_pick = lenh is not None
    if not is_pick:
        # Thi diem 04/09 (dcgr truoc): chat thuong di qua GATEWAY hermes bang bot
        # rieng (profile_routes theo topic). Bot approve chi con giu nut duyet,
        # chon so, lenh "/" va tien do kanban — KHONG tra loi chat nua, khong thi
        # hai bot cung dap mot cau. Bat bang CT_CHAT_QUA_GATEWAY=1 trong unit.
        if os.environ.get("CT_CHAT_QUA_GATEWAY", "") == "1":
            log("route", f"msg={mid} chat -> nhuong gateway (CT_CHAT_QUA_GATEWAY=1)")
            return
        # Chay nen: mot lan goi agent co the toi 10 phut, khong duoc de nghen
        # vong lap poll (nut Duyet/Bo phai bam duoc bat cu luc nao).
        _chay_nen("chat", handle_chat, token, group, thread_id,
                  token, group, msg, thread_id, text)
        return

    log("route", f"msg={mid} chon so vai={vai} lenh={lenh}")
    _chay_nen("chon", _xu_ly_chon, token, group, thread_id,
              token, group, thread_id, vai, lenh)

def _ghi_offset(offset: int):
    """Ghi offset NGUYEN TU. Chet giua luc ghi khong duoc de lai file cut:
    int() doc file cut se nem ValueError ngay khoi dong -> systemd restart ->
    crash-loop im lang, va kenh bao dong duy nhat (Telegram) thi can offset."""
    OFFSET.parent.mkdir(parents=True, exist_ok=True)
    tmp = OFFSET.with_suffix(".txt.tmp")
    tmp.write_text(str(offset))
    os.replace(tmp, OFFSET)

def _doc_offset() -> int:
    """File hong (cut nua chung, rac) thi ve 0 va bao — con hon chet han.
    offset=0 lam Telegram tra lai cac update con giu (toi da 24h), nhung
    handle_callback da co chot trang thai nen bai da xu ly khong dang lai."""
    if not OFFSET.exists():
        return 0
    try:
        return int(OFFSET.read_text().strip())
    except (ValueError, OSError) as e:
        print(f"[approve_service] offset.txt hong ({e}), ve 0", flush=True)
        return 0

def loop():
    token, channel, group = load_secrets()
    offset = _doc_offset()
    tp = env_load.topics_path()
    log("start", f"brand={ghi_log.brand()} group={group} state={STATE_DIR} "
                 f"topics={tp.name}({'co' if tp.exists() else 'THIEU'}) "
                 f"hermes_home={HERMES_HOME} offset={offset}")
    loi_lien_tiep = 0
    while True:
        try:
            r = call(token, "getUpdates", offset=offset, timeout=50,
                     allowed_updates=["callback_query", "message"])
            if not r.get("ok"):
                # 409 (hai poller cung token) / 429: long-poll khong giu duoc,
                # request tra ve NGAY -> khong sleep la nen API vo han.
                log("loi", "getUpdates tu choi: " + str(r.get("description")))
                time.sleep(5)
                continue
            for u in r.get("result", []):
                # Ghi offset TRUOC khi xu ly tung update. Truoc day ghi sau ca
                # lo: mot update no giua chung -> offset khong ghi -> restart
                # xu ly lai tu dau lo, DANG LAI bai da dang. Ghi truoc nghia la
                # update no se bi mat thay vi chay hai lan — voi dich vu duyet
                # bai, mat mot lenh (Ong Chu bam lai duoc) re hon dang trung
                # (doc gia thay hai bai giong het nhau tren channel).
                offset = u["update_id"] + 1
                _ghi_offset(offset)
                # Boc TUNG update: mot update hong khong duoc keo ca lo con
                # lai xuong except ngoai (bi bo qua im lang), va nut bam hong
                # thi Ong Chu phai thay nut ngung quay kem ly do.
                try:
                    if "callback_query" in u:
                        cq = u["callback_query"]
                        log("vao", f"callback data={cq.get('data')} "
                                   f"from={cq.get('from', {}).get('id')}")
                        # Chay nen: tao task/ghi bang den toi 2 phut, khong nghen poll.
                        _chay_nen("nut", _xu_ly_nut, token, group,
                                  (cq.get("message") or {}).get("message_thread_id"),
                                  token, channel, cq)
                    elif "message" in u:
                        handle_message(token, group, u["message"])
                except Exception as e:                      # noqa: BLE001
                    import traceback
                    log("loi", f"update {u.get('update_id')} hong: "
                               f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
            # getUpdates cho toi 50 giay moi luot, nen goi moi vong la du thua
            # cho viec nay: no chi doc mot cau SQL va thuong khong gui gi.
            _lam_lai_het_han(token, group)
            bao_tien_do_kanban(token, group)
            loi_lien_tiep = 0
        except Exception as e:                              # noqa: BLE001
            loi_lien_tiep += 1
            log("loi", "vong poll: " + type(e).__name__ + ": " + str(e))
            time.sleep(min(60, 5 * loi_lien_tiep))

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "push":
        tok, _ch, grp = load_secrets()
        draft_id = sys.argv[2]
        # Dinh tuyen topic theo loai noi dung: teaser ve topic Jean, tin tuc
        # ve topic Miles. Tham so thu 3 (neu co) van ghi de duoc.
        thread = None
        tp = env_load.topics_path()
        if tp.exists():
            topics = json.loads(tp.read_text(encoding="utf-8"))
            dpath = DRAFTS / (draft_id + ".json")
            category = ""
            if dpath.exists():
                try:
                    category = json.loads(
                        dpath.read_text(encoding="utf-8")).get("category", "")
                except Exception:                            # noqa: BLE001
                    pass
            # Mot container mot nguoi viet: tin thuong ve topic writer cua
            # container, teaser ve topic Jean.
            key = "teaser" if category.upper() == "TEASER" else MAC_DINH_VIET
            thread = topics.get(key)
        if len(sys.argv) > 3:
            thread = int(sys.argv[3])
        res = draft_push(tok, grp, draft_id, thread_id=thread)
        try:                                  # message_id the duyet: doi chieu bai <-> the (Ada phan tich)
            _mid = (res.get("result") or {}).get("message_id") if isinstance(res, dict) else None
            if _mid:
                _dp = DRAFTS / (draft_id + ".json")
                _d = json.loads(_dp.read_text(encoding="utf-8"))
                _d["tg_card_message_id"] = _mid
                _ghi_json(_dp, _d)
        except Exception as _e:                              # noqa: BLE001
            print(f"[push] khong luu message_id: {type(_e).__name__}: {_e}")
        print("day ban nhap -> topic " + str(thread) + " | " +
              ("OK" if res.get("ok") else str(res.get("description"))))
    else:
        loop()
