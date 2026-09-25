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
  approve_base.py     nen: hang so, call, ghi JSON nguyen tu, khoa draft, chay nen
  approve_dispatch.py bang vai, kanban_create, doc kanban.db, bang den, bao tien do
  approve_pick.py  reply so -> manifest -> create_pair (khoa theo manifest)
  approve_post.py       nut Duyet/Bo/Lam lai, chuyen Kite, dang kenh, day hang duyet
  approve_chat.py      chat theo topic: FIFO moi vai + semaphore
  approve_command.py      lenh slash /bai /vai /hd
Khong con re-export names tu day (sua 09/09/2026): image_prepare va cac kich ban
thu goi duyet_* truc tiep neu can.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

from html import escape as html_escape

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402 — LOW-159: truoc httpx de dat OPENSSL_CONF kip

import httpx                                                  # noqa: E402

import write_log                                              # noqa: E402
import submit_common                                             # noqa: E402
import state_paths                                               # noqa: E402
import role as _vai                                           # noqa: E402
import hiro_pick                                              # noqa: E402

from approve_base import (  # noqa: E402
    DRAFTS, HERMES_HOME, OFFSET, STATE_DIR, TELEGRAM_INCOMING, _run_background, _write_json, _send_text, _reply_real, call, is_boss, load_secrets, log, rut,
)
from approve_dispatch import (  # noqa: E402
    report_progress_kanban, role_of_topic,
)
from approve_pick import (  # noqa: E402
    MANIFEST_BY_TOPIC, read_pick_command, _process_pick, reply_report_target,
)
from approve_post import (  # noqa: E402
    _redo_all_done_limit, _label_reason_redo, _process_button, already_len_channel, draft_push,
    handle_reply_approval, push_fingerprint, delete_messages, auto_schedule_silent_drafts,
)
from approve_chat import (  # noqa: E402
    handle_chat,
)
from approve_command import (  # noqa: E402
    handle_command,
)
from route_missing_images import route_out_of_budget  # noqa: E402


def _download_image_fixed_with(token, msg):
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
        # Duoi tep lay tu `file_name` cua NGUOI GUI. Chi nhan duoi chu-so
        # ngan: chuoi nay di thang vao ten tep ghi ra dia ben duoi, va mot
        # `file_name` chua dau gach cheo hay dau cham kep se dat bytes ra ngoai
        # thu muc dinh san.
        ten = msg["document"].get("file_name", "")
        if "." in ten:
            duoi = ten.rsplit(".", 1)[-1]
            ext = "." + duoi.lower() if re.fullmatch(r"[A-Za-z0-9]{1,5}", duoi) else ".jpg"
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

def _report_no_family_point(token, group, thread_id, msg, mid):
    """Sticker, voice, video, file khong phai anh... — khong hieu duoc thi noi
    ro, khong im lang (im lang = "khong phan hoi" trong mat Ong Chu)."""
    loai = next((k for k in ("sticker", "voice", "video", "audio", "document",
                             "animation", "video_note", "poll", "location")
                 if k in msg), "khong ro")
    log("vao", f"msg={mid} khong co chu/anh (loai={loai}) -> bao khong ho tro")
    call(token, "sendMessage", chat_id=group,
         **({"message_thread_id": thread_id} if thread_id else {}),
         text=f"Tin dạng {loai} chưa hỗ trợ — chỉ nhận chữ và ảnh (photo hoặc file ảnh).")


def _pick_command_if_has(token, group, msg, thread_id, text, mid):
    """So trong topic cua MOT VAI DI TIM TIN = lenh chon tin — NHUNG chi khi la
    REPLY dung vao bao cao (xem _is_reply_report). Tra (vai, lenh); lenh None
    la hoi thoai. Ghi lai quyet dinh cong reply: khi Ong Chu bao "go so ma
    khong ra bai" thi mot dong log du de biet cong da xu ra sao."""
    vai = role_of_topic(thread_id)
    lenh = read_pick_command(text) if vai in MANIFEST_BY_TOPIC else None
    manifest = None
    if lenh is not None:
        rt_that = _reply_real(msg)
        # LOW-362: reply vao BAT KY bao cao nao cua vai (ke ca cu) -> manifest cua chinh no.
        la_reply, manifest = reply_report_target(vai, msg)
        log("route", f"msg={mid} ung-vien-chon vai={vai} "
                     f"reply_that={rt_that.get('message_id') if rt_that else None} "
                     f"la_reply_bao_cao={la_reply}")
        if not la_reply:
            log("route", f"msg={mid} giong lenh chon nhung khong phai reply bao cao "
                         f"vai={vai} -> coi la hoi thoai")
            _report_no_right_reply(token, group, thread_id, vai, rt_that)
            lenh = None
    return vai, lenh, manifest


def _hiro_command_if_has(token, group, msg, thread_id, text, mid) -> bool:
    """`Hiro` / `Hiro 1-10` trong topic researcher -> task Hiro chay nen; True = da xu ly.

    Cung cong reply voi lenh chon so (LOW-362): phai reply DUNG mot bao cao da gui, va
    dung ban manifest cua chinh bao cao do. Khong phai reply thi noi ro vi sao, KHONG roi
    ve hoi thoai — "Hiro" tran khong phai cau hoi cho researcher."""
    vai = role_of_topic(thread_id)
    if vai not in MANIFEST_BY_TOPIC:
        return False
    cmd = hiro_pick.read_hiro_command(text)
    if cmd is None:
        return False
    la_reply, manifest = reply_report_target(vai, msg)
    log("route", f"msg={mid} lenh Hiro vai={vai} {cmd} la_reply_bao_cao={la_reply}")
    if not la_reply:
        _report_no_right_reply(token, group, thread_id, vai, _reply_real(msg))
        return True
    _run_background("hiro", hiro_pick.process_hiro, token, group, thread_id,
                    token, group, thread_id, vai, cmd, manifest)
    return True


def _report_no_right_reply(token, group, thread_id, vai, rt_that):
    """Noi ro VI SAO lenh chon so khong chay, thay vi im lang.

    Cong reply (06/09/2026) ha moi tin khong-phai-reply xuong hoi thoai. Nhung
    tren dcgr hoi thoai lai nhuong cho gateway, ma gateway dat
    `require_mention: true` va da bo `free_response_topics` (08/09/2026) — tin
    khong nhac ten bot thi KHONG AI tra loi. Ket qua: Ong Chu reply "1, 7 - Dre"
    luc 07:24 ngay 12/09/2026 (nham vao ban bao cao thu hai trong ba ban Vera
    gui sang hom do) va khong nhan duoc gi ca: khong bai, khong loi, khong mot
    dong. Im lang la trang thai te nhat — no giong het luc bot chet."""
    ly_do = ("tin này không bấm Reply" if not rt_that
             else "tin này Reply vào một bản báo cáo cũ")
    _send_text(token, group,
             f"⚠️ Chưa tạo bài: lệnh chọn số phải Reply đúng vào báo cáo MỚI NHẤT "
             f"của {_vai.display_name(vai)} — {ly_do}.\n"
             f"Bấm Reply vào báo cáo cuối cùng trong topic rồi gửi lại đúng dòng vừa gõ.",
             thread=thread_id)


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

    thread_id = msg.get("message_thread_id")
    log("vao", f"msg={mid} thread={thread_id} vai={role_of_topic(thread_id)} "
               f"from={msg.get('from', {}).get('id')} text={rut(text)}")

    # ALLOWLIST cho MOI tin, khong chi lenh slash. Truoc 06/09/2026 chi
    # approve_command va nhanh "ly do lam lai" kiem `boss_ids.json`; lenh chon so va
    # chat thi khong — bat ky ai trong group reply "1, 3" vao bao cao Finn la
    # tao duoc cap task ton LLM, con reply kem URL la agent chay voi bo cong cu
    # day du. Khong co tep boss_ids.json thi giu nguyen hanh vi cu (xem
    # `is_boss`), nen bat cai nay khong lam ket chet may dang chay.
    if not is_boss(msg):
        uid = msg.get("from", {}).get("id")
        log("vao", f"msg={mid} TU CHOI: {uid} khong co trong {state_paths.BOSS_IDS_FILE}")
        call(token, "sendMessage", chat_id=group,
             **({"message_thread_id": thread_id} if thread_id else {}),
             text="Chỉ Ông Chủ ra lệnh cho đội được. (id của bạn: <code>"
                  + str(uid) + "</code>)", parse_mode="HTML")
        return

    # Anh dinh kem (photo hoac document anh): tai ve, dua duong dan THAT vao
    # dau text — agent doc duoc ngay, khong phai doan qua nhat ky/thu muc.
    # Tin chi co anh, khong chu (chu qua bam Reply roi gui thang anh, khong
    # go gi them) van phai di tiep, khong duoc bo som nhu truoc.
    #
    # SAU allowlist, khong truoc: ham nay ghi bytes cua nguoi gui ra dia
    # (`state/<brand>/telegram_incoming/`) va truoc 06/09/2026 no chay o dong
    # dau tien cua handle_message — nguoi la trong group ghi duoc tep vao may
    # ma khong qua mot cong nao.
    anh_path = _download_image_fixed_with(token, msg)
    if anh_path:
        text = f"[Ảnh đính kèm đã tải về: {anh_path}]\n" + (text or "(không có chú thích kèm theo)")

    if not text:
        _report_no_family_point(token, group, thread_id, msg, mid)
        return

    # Dau "/" = LENH, o bat ky topic nao — xu ly rieng, khong bao gio roi ve
    # hoi thoai (mot lenh go sai ma dem hoi LLM la vua on ao vua nguy hiem).
    # Chay nen: /bai co buoc fetch trang + research (article_sources, toi 180s),
    # khong duoc nghen vong poll — cung ly do voi handle_chat ben duoi.
    if text.startswith("/"):
        log("route", f"msg={mid} lenh slash")
        _run_background("lenh", handle_command, token, group, thread_id,
                  token, group, msg, thread_id, text)
        return

    # Topic nay dang CHO ly do "lam lai" (Ong Chu vua bam nut)? Nuot tin nay
    # lam ly do, giao task, xong. Dat TRUOC "chon so": mot dong "4: chart bi
    # cat" ma roi vao topic chon tin se bi hieu nham thanh chon bai so 4.
    if _label_reason_redo(token, group, msg, thread_id, text):
        return

    # Reply vao album anh "gửi cho Miles" / "duyệt" = bam ✅ Duyet (LOW-134): duong
    # du phong khi tin nut khong len vi mang loi. Chi an khi reply DUNG mot album
    # co trong so gui anh — con lai di tiep nhu cu.
    if handle_reply_approval(token, group, msg, thread_id, text):
        return

    # "Hiro" / "Hiro 1-10" reply vao bao cao researcher = MOT carousel ban tin van (LOW-403).
    # Xet TRUOC lenh chon so: chu Hiro dung dau nen khong trung lenh chon nao dang co.
    if _hiro_command_if_has(token, group, msg, thread_id, text, mid):
        return

    # So trong topic cua MOT VAI DI TIM TIN = lenh chon tin — NHUNG chi khi la
    # REPLY dung vao bao cao (xem _is_reply_report). Moi thu khac (ke ca dung
    # so nhung go troi, khong bam Reply) la hoi thoai. Finn, Nova, Vera deu
    # duoc — cung mot cach tra loi.
    vai, lenh, manifest = _pick_command_if_has(token, group, msg, thread_id, text, mid)
    is_pick = lenh is not None
    if not is_pick:
        # Thi diem 04/09 (dcgr truoc): chat thuong di qua GATEWAY hermes bang bot
        # rieng (profile_routes theo topic). Bot approve chi con giu nut duyet,
        # chon so, lenh "/" va tien do kanban — KHONG tra loi chat nua, khong thi
        # hai bot cung dap mot cau. Bat bang CT_CHAT_VIA_GATEWAY=1 trong unit.
        if os.environ.get("CT_CHAT_VIA_GATEWAY", "") == "1":
            log("route", f"msg={mid} chat -> nhuong gateway (CT_CHAT_VIA_GATEWAY=1)")
            return
        # Chay nen: mot lan goi agent co the toi 10 phut, khong duoc de nghen
        # vong lap poll (nut Duyet/Bo phai bam duoc bat cu luc nao).
        _run_background("chat", handle_chat, token, group, thread_id,
                  token, group, msg, thread_id, text)
        return

    log("route", f"msg={mid} chon so vai={vai} lenh={lenh} manifest={manifest.name if manifest else None}")
    _run_background("chon", _process_pick, token, group, thread_id,
              token, group, thread_id, vai, lenh, manifest)

def _write_offset(offset: int):
    """Ghi offset NGUYEN TU. Chet giua luc ghi khong duoc de lai file cut:
    int() doc file cut se nem ValueError ngay khoi dong -> systemd restart ->
    crash-loop im lang, va kenh bao dong duy nhat (Telegram) thi can offset."""
    OFFSET.parent.mkdir(parents=True, exist_ok=True)
    tmp = OFFSET.with_suffix(".txt.tmp")
    tmp.write_text(str(offset))
    os.replace(tmp, OFFSET)

def _read_offset() -> int:
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

def _audit_tirith():
    """Bao neu bo quet prompt-injection duoc KHAI la bat nhung khong chay duoc.

    Phat hien 06/09/2026: moi config deu co tirith_enabled: true, tirith_path:
    tirith, tirith_fail_open: true — nhung BINARY KHONG CO tren may. fail_open
    nghia la quet hong thi cho lenh chay tiep, nen cai lop phong thu nay dang
    tat mot cach im lang. Te hon: hermes co in canh bao, nhung dong do bat dau
    bang khoang trang + "⚠" nen roi dung vao bo loc _DONG_RAC cua chat_router
    (xem chinh vi du trong comment o do) — khong bao gio den mat ai.
    Ghi mot dong luc khoi dong la du de con biet duong: khong sua gi, khong
    chan gi, chi thoi khong noi doi trong nhat ky nua."""
    import shutil
    try:
        cau_hinh = Path(HERMES_HOME) / "config.yaml"
        chu = cau_hinh.read_text(encoding="utf-8") if cau_hinh.exists() else ""
    except OSError:
        return
    if "tirith_enabled: true" not in chu:
        return
    m = re.search(r"^\s*tirith_path:\s*(\S+)", chu, re.M)
    duong = m.group(1) if m else "tirith"
    if shutil.which(duong):
        return
    mo = "tirith_fail_open: true" in chu
    # WARNING chu khong INFO (LOW-305): dich vu van chay, nhung mot cong bao mat dang
    # TAT — dung loai dong phai loc ra duoc bang `journalctl -p warning`.
    write_log.warn("start", f"⚠️ tirith_enabled: true nhung KHONG co binary '{duong}' "
                            f"trong PATH — quet prompt-injection dang TAT"
                            + (" (fail_open: true nen lenh van chay tiep)" if mo else ""))


END_PUBLISHING_SECONDS = 15 * 60          # qua ngan nay ma con "publishing" = ket


def _rescue_article_end_publishing(token, group):
    """Bai ket vinh vien o trang thai `publishing` sau khi dich vu khoi dong lai.

    `handle_callback` ghi `publishing` roi dang o mot thread DAEMON. Unit co
    `Restart=always` va khong co `TimeoutStopSec`, nen SIGTERM giet thread do
    giua chung — publish() mot minh da toi 180 giay, cong buoc moat toi 600.
    Sau restart khong co buoc nao doc lai trang thai: `handle_callback` thay
    `publishing` va tra "Đang đăng — chờ chút" cho MOI lan bam ve sau. Bai do
    khong bao gio dang duoc va cung khong bo duoc, tru khi co nguoi sua tay
    tep JSON. Docstring cua `_form_background` hua "khong bao gio ket vinh vien" —
    dieu do chi dung voi exception, khong dung voi restart.

    Chay MOT lan luc khoi dong: bai nao con `publishing` qua 15 phut thi ha ve
    `publish_failed` (bam Duyet lai duoc) va noi ra o topic cua bai.
    """
    gio = int(time.time())
    cuu, da_len = [], []
    try:
        ds = sorted(DRAFTS.glob("*.json"))
    except OSError:
        return
    for p in ds:
        if p.name.endswith((".meta.json", ".img.json", ".writer.json")):
            continue
        try:
            d = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if d.get("status") != "publishing":
            continue
        if gio - int(d.get("decided_at") or 0) < END_PUBLISHING_SECONDS:
            continue                    # co the mot tien trinh khac dang dang that
        # CO DAU len channel = Telegram DA nhan bai nay (`publish` ghi dau ngay
        # khi tra ok, truoc moi viec khac). Tien trinh chet sau do la chet o
        # buoc GHI TRANG THAI, khong phai o buoc dang. Ha ve publish_failed luc
        # nay la moi Ong Chu bam Duyet lai mot bai DA len channel — dung duong
        # sinh ra "dang trung" ma E5 di dong.
        if already_len_channel(d):
            d["status"] = "published"
            d["rescue_note"] = (f"dich vu khoi dong lai luc {gio}; bai DA len channel "
                                "(co dau channel_*_mid) nen danh dau published")
            dich = da_len
        else:
            d["status"] = "publish_failed"
            d["rescue_note"] = f"dich vu khoi dong lai luc {gio}, bo trang thai publishing"
            dich = cuu
        try:
            _write_json(p, d)
        except OSError:
            continue
        dich.append(p.stem)
    if not cuu and not da_len:
        return
    # WARNING (LOW-305): dich vu tat giua luc dang dang — chay tiep duoc nhung la
    # trang thai bat thuong, Ong Chu phai kiem channel, nen phai loc ra duoc.
    write_log.warn("start", f"cuu {len(cuu)} bai ket o publishing, {len(da_len)} bai da len "
                            f"channel: {', '.join(cuu + da_len)}")
    phan = []
    if da_len:
        phan.append("✅ " + str(len(da_len)) + " bài ĐÃ lên channel trước khi dịch vụ tắt "
                    "(Telegram đã nhận) — đã đánh dấu <b>published</b>, "
                    "<b>đừng bấm Duyệt lại</b> kẻo đăng trùng:\n"
                    + "\n".join("• " + html_escape(x) for x in da_len[:10]))
    if cuu:
        phan.append("⚠️ " + str(len(cuu)) + " bài kẹt ở trạng thái \"đang đăng\" mà CHƯA có "
                    "dấu nào cho thấy đã lên channel — đã mở khoá, kiểm tra channel rồi "
                    "bấm Duyệt lại nếu chưa lên:\n"
                    + "\n".join("• " + html_escape(x) for x in cuu[:10]))
    call(token, "sendMessage", chat_id=group,
         text="Dịch vụ vừa khởi động lại giữa lúc đang đăng.\n\n" + "\n\n".join(phan),
         parse_mode="HTML")


def loop():
    token, channel, group = load_secrets()
    offset = _read_offset()
    tp = env_load.topics_path()
    log("start", f"brand={write_log.brand()} group={group} state={STATE_DIR} "
                 f"topics={tp.name}({'co' if tp.exists() else 'THIEU'}) "
                 f"hermes_home={HERMES_HOME} offset={offset}")
    _audit_tirith()
    _rescue_article_end_publishing(token, group)
    loi_lien_tiep = 0
    mat_ket_noi_tu = None       # epoch luc bat dau chuoi loi hien tai, None = dang on
    loai_loi_dang_bao = None    # loai loi (409/429/ten exception) da bao — chi bao 1 lan/loai
    while True:
        try:
            r = call(token, "getUpdates", offset=offset, timeout=50,
                     allowed_updates=["callback_query", "message"])
            if not r.get("ok"):
                # 409 (hai poller cung token) / 429: long-poll khong giu duoc,
                # request tra ve NGAY -> khong sleep la nen API vo han.
                mo_ta = str(r.get("description"))
                log("loi", "getUpdates tu choi: " + mo_ta)
                if mat_ket_noi_tu is None:
                    mat_ket_noi_tu = time.time()
                if loai_loi_dang_bao != mo_ta:
                    # Bao NGAY (sendMessage la endpoint khac getUpdates, 409/429 cua
                    # getUpdates khong can trong no van goi duoc) — chi 1 lan cho
                    # moi loai loi, tranh spam khi 409 lap lien tuc.
                    loai_loi_dang_bao = mo_ta
                    try:
                        call(token, "sendMessage", chat_id=group,
                             text="🔌 Telegram từ chối getUpdates (" + html_escape(mo_ta)
                                  + "), đang thử lại…", parse_mode="HTML")
                    except Exception as e:                       # noqa: BLE001
                        # R-r2-7: token sai (401) thi ca getUpdates lan sendMessage
                        # deu hong — phai co dau vet, khong chi "getUpdates tu choi".
                        log("loi", "bao mat/hoi ket noi hong: " + repr(e))
                time.sleep(5)
                continue
            if mat_ket_noi_tu is not None:
                # Vong nay goi duoc: het chuoi loi (409/429 tu choi hoac exception
                # ket noi ben duoi).
                phut = (time.time() - mat_ket_noi_tu) / 60
                if loai_loi_dang_bao is not None:      # da bao luc mat -> bao khi hoi lai
                    try:
                        call(token, "sendMessage", chat_id=group,
                             text=f"✅ Đã kết nối lại Telegram sau {phut:.1f} phút mất kết nối")
                    except Exception as e:                       # noqa: BLE001
                        # R-r2-7: token sai (401) thi ca getUpdates lan sendMessage
                        # deu hong — phai co dau vet, khong chi "getUpdates tu choi".
                        log("loi", "bao mat/hoi ket noi hong: " + repr(e))
                mat_ket_noi_tu = None
                loai_loi_dang_bao = None
            for u in r.get("result", []):
                # Ghi offset TRUOC khi xu ly tung update. Truoc day ghi sau ca
                # lo: mot update no giua chung -> offset khong ghi -> restart
                # xu ly lai tu dau lo, DANG LAI bai da dang. Ghi truoc nghia la
                # update no se bi mat thay vi chay hai lan — voi dich vu duyet
                # bai, mat mot lenh (Ong Chu bam lai duoc) re hon dang trung
                # (doc gia thay hai bai giong het nhau tren channel).
                offset = u["update_id"] + 1
                _write_offset(offset)
                # Boc TUNG update: mot update hong khong duoc keo ca lo con
                # lai xuong except ngoai (bi bo qua im lang), va nut bam hong
                # thi Ong Chu phai thay nut ngung quay kem ly do.
                try:
                    if "callback_query" in u:
                        cq = u["callback_query"]
                        log("vao", f"callback data={cq.get('data')} "
                                   f"from={cq.get('from', {}).get('id')}")
                        # Chay nen: tao task/ghi bang den toi 2 phut, khong nghen poll.
                        _run_background("nut", _process_button, token, group,
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
            _redo_all_done_limit(token, group)
            # Cong tu duyet ban nhap (LOW-382): the im lang qua cua so cho thi
            # tu xep lich dang. Cung ly do dat o day voi hai dong tren —
            # getUpdates da cho toi 50 giay moi vong, nen goi moi vong la du
            # thua cho mot viec chi doc vai tep JSON.
            auto_schedule_silent_drafts(token, group)
            # LOW-411: Dre het ngan sach HAI lan (gave_up) -> tu chuyen Kite, thay vi
            # task nam blocked mai (3 bai dcgr chet 22–25/09). Dat TRUOC bang tien do:
            # task cu dong trong vong nay thi bang tien do im lang (LOW-410).
            route_out_of_budget(token, group)
            report_progress_kanban(token, group)
            loi_lien_tiep = 0
        except Exception as e:                              # noqa: BLE001
            loi_lien_tiep += 1
            log("loi", "vong poll: " + type(e).__name__ + ": " + repr(e))
            # R-r2-4: day moi la "mat ket noi" that (timeout/DNS/mang dut) — nhanh
            # tren chi bat 409/429 la API con tra loi duoc. Khong gui duoc gi luc
            # nay, nhung DAT MOC de vong sau goi duoc thi bao "da ket noi lai sau
            # N phut"; truoc day moc khong bao gio dat nen khong bao gio bao.
            if mat_ket_noi_tu is None:
                mat_ket_noi_tu = time.time()
            if loai_loi_dang_bao is None:
                loai_loi_dang_bao = type(e).__name__
            time.sleep(min(60, 5 * loi_lien_tiep))


def _live_card(draft_id):
    """(draft, [id tin]) cua the duyet dang SONG (draft con pending), hoac
    (None, []). The da chuyen thanh "da duyet/da bo" thi khong dong vao."""
    try:
        d = json.loads((DRAFTS / (draft_id + ".json")).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None, []
    if d.get("status") != "pending" or not d.get("tg_card_message_id"):
        return None, []
    ids = [d["tg_card_message_id"]] + list(d.get("tg_extra_message_ids") or [])
    return d, ids


def _push_replace(tok, grp, draft_id, thread, force=False):
    """Nhanh CLI `push`, tach ra de test (LOW-296). Mot draft chi co MOT the song
    trong topic: y het lan truoc thi bo qua; khac thi gui the moi roi xoa the cu.
    Tra ve ma thoat."""
    live, old_ids = _live_card(draft_id)
    if live and not force and live.get("tg_push_fingerprint") == push_fingerprint(live):
        print("[push] bản nháp y hệt thẻ đã ở topic " + str(thread) + ", không đẩy lại "
              "(thêm --force nếu thật sự cần gửi lại).")
        return 0
    res = draft_push(tok, grp, draft_id, thread_id=thread)
    rc = _finish_push_cli(res, draft_id, thread)
    if rc == 0 and old_ids:
        n = delete_messages(tok, grp, old_ids)
        print(f"[push] đã thay thẻ cũ: xoá {n}/{len(old_ids)} tin của bản trước.")
    return rc


def _finish_push_cli(res, draft_id, thread):
    """Ket thuc lenh CLI `push`: luu message_id (best-effort), in ket qua, tra
    ve ma thoat.

    LOW-160: truoc day nhanh nay luon in roi ket thuc ham __main__ (thoat 0)
    du `res.get("ok")` la False — mot lan Telegram sendMessage bi cat giua
    chung (vd RemoteProtocolError) la vai (Miles/Jika, qua miles_submit.py)
    bao task "done"/"da vao hang duyet" trong khi the duyet CHUA TUNG len
    Telegram, khong ai biet de gui lai. Tach rieng ham nay de test duoc va
    tra ve 1 khi that bai, de nguoi goi (kiem tra returncode subprocess) coi
    day la task that bai thay vi bao thanh cong nham."""
    try:                                  # message_id the duyet: doi chieu bai <-> the (Ada phan tich)
        _mid = (res.get("result") or {}).get("message_id") if isinstance(res, dict) else None
        if _mid:
            _dp = DRAFTS / (draft_id + ".json")
            _d = json.loads(_dp.read_text(encoding="utf-8"))
            _d["tg_card_message_id"] = _mid
            # Moc THE LEN TOPIC (LOW-382): cua so "im lang la dong y" dem tu day,
            # khong dem tu mtime cua tep — tep con bi ghi lai nhieu lan sau do.
            _d["card_pushed_at"] = time.time()
            _d["tg_extra_message_ids"] = (res.get("extra_ids") or []) if isinstance(res, dict) else []
            _d["tg_push_fingerprint"] = push_fingerprint(_d)
            _write_json(_dp, _d)
    except Exception as _e:                              # noqa: BLE001
        print(f"[push] khong luu message_id: {type(_e).__name__}: {_e}")
    print("day ban nhap -> topic " + str(thread) + " | " +
          ("OK" if res.get("ok") else str(res.get("description"))))
    return 0 if res.get("ok") else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "push":
        tok, _ch, grp = load_secrets()
        draft_id = sys.argv[2]
        # Dinh tuyen topic theo loai noi dung: teaser ve topic Cape, tin tuc
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
                except Exception as e:                       # noqa: BLE001
                    log("loi", f"doc category cua {dpath.name} hong (dung topic mac dinh): {e!r}")
            # Tin thuong ve topic NGUOI VIET CUA BAI, teaser ve topic Cape.
            # Truoc 10/09/2026 cho nay go `DEFAULT_WRITE` vi ca doi chi co mot
            # nguoi viet ("mot container mot nguoi viet"). Van dung mot nguoi
            # moi container, nhung ten cua nguoi do khac nhau theo brand
            # (LOW-13), va cau tra loi da duoc chot tu luc chon tin — doc lai
            # sidecar thay vi doan lai, de bai khong roi vao topic cua vai kia.
            if category.upper() == "TEASER":
                key = "cape"
            else:
                key = submit_common.writer_for_article(draft_id, env_load.brand_long())
            thread = topics.get(key)
        force = "--force" in sys.argv
        extra = [x for x in sys.argv[3:] if x != "--force"]
        if extra:
            thread = int(extra[0])
        sys.exit(_push_replace(tok, grp, draft_id, thread, force))
    else:
        loop()
