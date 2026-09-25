#!/usr/bin/env python3
"""Tang GHEP NOI: bai thieu anh that thi chuyen Kite (hoac hoi, khi brand chua co Kite).

Vi sao tach ra (audit_content_team A1): hai viec nay — gui Telegram va tao task
Kite — la viec cua tang DIEU PHOI, nhung truoc 09/09/2026 chung nam ngay trong
ENGINE (`image_prepare`, ham cu `_route_thieu_anh`, da xoa). Engine vi vay phai
`from approve_dispatch import standard_assignee` va `from approve_post import
create_task_kite`: lop CHUAN BI goi NGUOC len lop dieu phoi. Do la vong phu thuoc
that, chi bi che di bang hai import luoi trong than ham.

Nay engine chi MO TA (`manifest.json["missing_images"] = {"count": 2, "min_images": 5}`) va
nhan mot ham `sau_chuan_bi` de goi. Tep nay la noi DUY NHAT biet ca hai phia,
nen mui ten phu thuoc chi con mot chieu: ghep noi -> engine, ghep noi -> dich vu.

QUAN TRONG — vi sao van goi DONG BO trong khoa cua engine chu khong doi ra
ngoai: `chay()` giu `running.pid` va chi ghi `manifest.json` SAU khi ham nay
xong, nen moi nguoi doc `manifest.json` deu thay quyet dinh da chot (co
`kite_task_id`/`kite_asked`/`kite_unavailable` hay khong). Neu day viec nay ra sau
`chay()` — hoac sang mot vong poll khac — thi co khe: `dre_prepare.py:41,46`
va `kite_prepare.py:54` doc `manifest.json` de dung brief, doc trung khe do la
brief IM LANG bao "du anh" trong khi tin dang cho chuyen Kite.
"""
import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402 — LOW-159: truoc httpx de dat OPENSSL_CONF kip

import httpx                                                  # noqa: E402

import role as vai_mod                                        # noqa: E402

DRAFTS = env_load.ROOT / "drafts"


def _time_send(vai: str, text: str, kb: dict | None = None) -> bool:
    """Gui mot tin CHU len topic cua `vai` (kem nut neu co). Tra True CHI KHI
    Telegram nhan (ok=true); moi truong hop khac in ly do ra stderr va tra False.

    Truoc audit lượt 2 (C-r2-1) ham nay tra None va vut ket qua httpx.post:
    Telegram tra 400 (HTML sai, topic sai) hay mat mang thi khong log, ma
    sau_chuan_bi van ghi m["kite_asked"]=True — bai "dang cho Ong Chu chon" trong
    khi Ong Chu chua bao gio nhan cau hoi. Nguoi goi PHAI nhin gia tri tra ve."""
    env_load.load()
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


def _write_img(draft_id: str, im: dict) -> None:
    (DRAFTS / (draft_id + ".img.json")).write_text(
        json.dumps(im, ensure_ascii=False, indent=2), encoding="utf-8")


def _unblock_image(draft_id: str, im: dict, reason: str) -> None:
    """Mo chan task anh ma `create_pair` da chan (LOW-382) — vai lam tiep binh thuong.

    Chi dong vao task ma CHINH minh da chan (`blocked_for_engine`): draft cu,
    hay draft tao qua duong "Lam lai", khong co co nay va khong bi cham toi.
    Ha co xuong ngay sau khi mo: goi lai ham nay (engine chay lai `--lam-moi`)
    khong duoc di mo mot task dang chay."""
    tid = im.get("image_task")
    if not im.get("blocked_for_engine") or not tid:
        return
    from approve_dispatch import kanban_unblock
    ok, _ = kanban_unblock(tid, reason)
    if ok:
        im["blocked_for_engine"] = False
        try:
            _write_img(draft_id, im)
        except OSError as e:                                  # noqa: BLE001
            print(f"[route] khong ghi duoc img.json sau khi mo chan: {e!r}", file=sys.stderr)


def _close_image_task(draft_id: str, old_tid: str, new_tid: str, why: str = "thieu anh that") -> None:
    """Dong task cua vai CU sau khi viec da sang Kite (LOW-382).

    Chi dong khi task chua chay ('blocked'/'ready'): dang chay thi worker van
    chay tiep du co dong dong trong kanban.db hay khong, ma brief cua vai cu da
    co cau "TIN NAY DA CHUYEN KITE — ket thuc task ngay", nen de no tu ket.
    Task `gave_up` (LOW-411) cung nam 'blocked' nen dong duoc."""
    if not old_tid:
        return
    import hermes_adapter
    from approve_dispatch import ROUTED_TO_KITE_RESULT, kanban_complete
    tt = hermes_adapter.status(old_tid)
    if tt not in ("blocked", "ready"):
        # '' = khong ro, None = khong doc duoc kanban.db: ca hai deu KHONG dong,
        # dong nham mot task dang chay con te hon de no tu ket.
        print(f"[route] task cu {old_tid} o trang thai {tt!r} — khong dong", file=sys.stderr)
        return
    # Ket qua BAT DAU bang ROUTED_TO_KITE_RESULT: bang tien do nhan ra task do he
    # thong dong bang chinh chu do, khong bao "vai dong sai cach" (LOW-410).
    kanban_complete(old_tid, f"{ROUTED_TO_KITE_RESULT} (task {new_tid}) — {why}.")
    ip = DRAFTS / (draft_id + ".img.json")
    try:
        im = json.loads(ip.read_text(encoding="utf-8"))
        im["image_task"], im["blocked_for_engine"] = new_tid, False
        _write_img(draft_id, im)
    except (OSError, ValueError) as e:                        # noqa: BLE001
        print(f"[route] khong cap nhat duoc img.json sau khi dong task cu: {e!r}", file=sys.stderr)


def after_prepare(draft_id: str, m: dict) -> None:
    """Thieu anh that -> TU CHUYEN Kite, khong hoi (LOW-382). Brand chua co Kite
    thi moi hoi bang nut.

    Doc co `m["missing_images"]` do engine ghi. Ghi nguoc quyet dinh vao `m`
    (`kite_task_id` / `kite_asked` / `kite_unavailable`) — engine ghi ca `m` xuong
    `manifest.json` ngay sau khi ham nay tra ve.

    Day cung la noi CHOT VAI ANH (LOW-382): `create_pair` chan task anh lai cho
    toi luc nay, nen ham nay phai ket thuc bang DUNG mot trong hai viec — mo chan
    cho vai cu lam tiep, hoac dong task cu va tao task Kite. Thoat ma khong lam
    viec nao thi task nam `blocked` mai."""
    ip = DRAFTS / (draft_id + ".img.json")
    if not ip.exists():
        return
    im = json.loads(ip.read_text(encoding="utf-8"))
    thieu = m.get("missing_images")
    # canonical_slug: sidecar cu con ghi ten persona ("dre", "miles") — chinh ly do
    # role.py ton tai. Dung tho thi topics().get("dre") miss -> khong gui gi.
    vai = vai_mod.canonical_slug(im.get("image_role", ""))
    if not thieu:
        _unblock_image(draft_id, im, f"engine dem xong: du anh cho {vai or 'vai anh'}")
        return                                     # du anh, khong co gi de hoi
    if vai == "kite" or im.get("kite_task_id"):
        # Kite dung duoc voi it anh (`anh_toi_thieu=1`), va bai da chuyen roi thi
        # task cu khong con la cua ai — ca hai truong hop deu khong doi vai nua.
        _unblock_image(draft_id, im, "engine dem xong: Kite lam voi so anh dang co")
        return
    so, tt = int(thieu.get("count", 0)), int(thieu.get("min_images", 5))
    ten = vai_mod.display_name(vai)      # ban dang ky: role.py (audit A4)
    tieu = m.get("title", draft_id)
    from approve_dispatch import standard_assignee
    from approve_post import create_task_kite
    _, khong_kite = standard_assignee("kite")

    def _ask(co: str, text: str, kb=None) -> None:
        # Chi dat co "da hoi/da bao" khi Telegram THAT SU nhan. Khong thi ghi
        # `route_error` de brief/nhat ky lo ra, thay vi bai dung mai cho mot cau
        # hoi khong ai nhan (C-r2-1).
        if _time_send(vai, text, kb):
            m[co] = True
        else:
            m["route_error"] = f"khong gui duoc tin '{co}' len topic {vai} — xem stderr engine"

    if khong_kite:
        # Brand nay chua co Kite (dcgr 05/09/2026). Noi thang, dung hua chuyen.
        # Van MO CHAN: khong co Kite thi khong doi vai nua, va cau hoi o day la
        # "lam voi N anh hay bo tin" — de task nam blocked cho mot cau tra loi
        # co the khong bao gio toi la giam mot bai im lang.
        _unblock_image(draft_id, im, f"engine dem xong: {so}/{tt} anh, brand chua co Kite")
        kb = {"inline_keyboard": [[{"text": "❌ Bỏ hẳn tin", "callback_data": "imgno:" + draft_id}]]}
        if so == 0:
            _ask("kite_unavailable", f"🖼 <b>{tieu}</b>: <b>0 ảnh thật</b> dùng được, và brand này <b>chưa có Kite</b> "
                               f"để vẽ vector. {ten} sẽ không dựng được bộ này — bỏ tin, hoặc tạo Kite cho brand.", kb)
        else:
            kb["inline_keyboard"][0].insert(0, {"text": f"🖼 {ten} làm với {so} ảnh", "callback_data": "imgtiep:" + draft_id})
            _ask("kite_asked", f"⚠️ <b>{tieu}</b>: chỉ <b>{so}/{tt}</b> ảnh thật dùng được; brand này chưa có Kite. Chọn:", kb)
        return
    # THIEU ANH -> TU CHUYEN KITE, KHONG HOI (LOW-382, Ong Chu chot 23/09/2026:
    # "cu tim duoc duoi 6 anh thi de Kite, tren 6 thi de Dre").
    #
    # Truoc day chi nhanh `so == 0` tu chuyen, con 1..tt-1 la mot cau hoi co hai
    # nut. Do tren approve.log 18-22/09/2026 (ca hai brand): 27 lan bam trong 5
    # ngay o duong nay, va khong lan nao doi huong khoi luat da co san — tuc cau
    # hoi khong con la mot quyet dinh, chi la mot buoc go tay lap lai luat "thieu
    # anh thi pass Kite". Nguong lay tu `min_images` cua manifest (engine da hoi
    # `role.min_images` cua VAI DUOC GIAO: Dre 6, tin flagship 7) — khong co so 6
    # nao viet thang o day.
    #
    # Brand chua co Kite thi VAN hoi (nhanh `khong_kite` o tren): o do that su con
    # mot lua chon — ha san lam voi N anh, hay bo tin.
    ly_do = ("engine: 0 anh that dung duoc" if so == 0
             else f"engine: chi {so}/{tt} anh that dung duoc")
    old_tid = im.get("image_task")              # doc TRUOC: create_task_kite ghi de img.json
    rid, loi = create_task_kite(draft_id, im, ly_do=ly_do)
    if loi:
        _time_send(vai, f"🖼 <b>{tieu}</b>: {so}/{tt} ảnh thật dùng được, chuyển Kite <b>lỗi</b>: {loi}")
        # Ghi lai de brief/nhat ky lo ra: bai nay dang ket o vai cu ma khong ai
        # biet (cung ly le voi `_ask`, C-r2-1). Truoc day nhanh nay im lang.
        m["route_error"] = f"chuyen Kite loi: {loi}"
        # Task cu VAN phai duoc mo chan: tao Kite hong thi vai cu la duong duy
        # nhat con lai, de no blocked la giet bai.
        _unblock_image(draft_id, im, f"chuyen Kite hong ({loi}) — vai cu lam tiep")
        return
    m["kite_task_id"] = rid                     # task DA tao — co du tin bao co di hay khong
    # Dong task cua vai cu NGAY: no dang blocked (create_pair chan), nen dong o
    # day la no khong bao gio chay. Do 21 ngay truoc khi co buoc nay: 33 task cu
    # co vet chay, 23 trong so do bat dau TRUOC luc chuyen — 191 phut cua Dre.
    _close_image_task(draft_id, old_tid, rid)
    if not _time_send(vai, f"🖼 <b>{tieu}</b>: <b>{so}/{tt} ảnh thật</b> dùng được → đã tự chuyển "
                        f"<b>Kite</b> vẽ vector (task {rid}). {ten} không dựng bộ này."):
        m["route_error"] = f"da chuyen Kite (task {rid}) nhung khong bao duoc len topic {vai}"
    print(f"[route] {so}/{tt} anh -> Kite task {rid}", file=sys.stderr)


# --- vai dung carousel het ngan sach HAI lan -> Kite (LOW-411) -----------------
# Hermes cho chay lai MOT lan; hong lan hai thi `gave_up` va task nam `blocked`
# mai — khong ai mo, bai chet im lang. Do dcgr 16–25/09/2026: 10 task Dre het
# 90/90 luot, 7 chay lai thi xong, 3 chet (Microsoft 22/09, Alibaba 24/09,
# ByteDance 25/09). Hai loi duoi day nghia la "vai khong xong trong ngan sach":
# lan chay thu ba cung vay, nen di duong "thieu anh thi pass Kite" nhu `after_prepare`.
# `pid ... not alive` (worker chet) thi KHONG chuyen — do la ha tang, chay lai la duoc.
_OUT_OF_BUDGET = re.compile(r"Iteration budget exhausted|^elapsed \d+s > limit \d+s")
# Task da THU chuyen trong tien trinh nay: tao Kite hong thi khong thu lai moi vong
# poll (50 giay) — bang tien do van bao ⛔ kem ly do nhu cu, Ong Chu bam Gui Kite duoc.
_ROUTE_TRIED = set()


def _log(msg: str) -> None:
    """Duong LOW-411 chay trong approve_service: ghi approve.log (noi doc log cua
    vong poll); stderr chi la duong lui."""
    try:
        from approve_base import log
        log("route", msg)
    except Exception:                                        # noqa: BLE001
        print(f"[route] {msg}", file=sys.stderr)


def out_of_budget(run: dict) -> bool:
    """Lan chay cuoi la `gave_up` vi het luot/het gio (khong phai vi worker chet)."""
    return run.get("status") == "gave_up" and bool(_OUT_OF_BUDGET.search(str(run.get("error") or "")))


def _draft_of_image_task(tid: str) -> tuple:
    """(draft_id, img.json) cua task anh `tid` qua khoa `image_task` ma create_pair
    ghi (LOW-382); (None, None) neu khong co — draft cu hon LOW-382 khong co khoa nay."""
    for p in sorted(DRAFTS.glob("*.img.json")):
        try:
            im = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if im.get("image_task") == tid:
            return p.name[:-len(".img.json")], im
    return None, None


def _route_one_out_of_budget(token, group, task: dict, run: dict):
    """Chuyen MOT task het ngan sach sang Kite. Tra ve id task Kite, hoac None."""
    tid = task["id"]
    draft_id, im = _draft_of_image_task(tid)
    if not draft_id:
        _log(f"{tid} het ngan sach nhung khong thay draft nao co image_task nay — de nguyen")
        return None
    if im.get("kite_task_id"):                       # da sang Kite tu truoc
        return None
    from approve_dispatch import _report_receive_job, standard_assignee
    from approve_post import create_task_kite
    _, no_kite = standard_assignee("kite")
    if no_kite:                                      # brand chua co Kite: de bang tien do bao ⛔
        return None
    role_slug = vai_mod.canonical_slug(task["assignee"]) or task["assignee"]
    name = vai_mod.display_name(role_slug)
    title = im.get("title") or draft_id
    budget = str(run.get("error") or "").split(" — ")[0][:80]
    reason = f"{name} het ngan sach hai lan ({budget}), chua nop duoc bo qua cong anh"
    kite_tid, err = create_task_kite(draft_id, im, ly_do=reason)
    if err:
        _log(f"{tid} het ngan sach, chuyen Kite LOI: {err}")
        _time_send(role_slug, f"🖼 <b>{title}</b>: {name} hết ngân sách hai lần, chuyển Kite <b>lỗi</b>: {err}")
        return None
    _close_image_task(draft_id, tid, kite_tid, why=f"{name} het ngan sach hai lan")
    _time_send(role_slug, f"🖼 <b>{title}</b>: <b>{name}</b> hết ngân sách hai lần ({budget}) mà chưa "
                          f"nộp được bộ qua cổng ảnh → đã tự chuyển <b>Kite</b> (task {kite_tid}).")
    _report_receive_job(token, group, "kite", role_slug, title, kite_tid,
                        ly_do=f"{name} hết ngân sách hai lần, chưa nộp được bộ qua cổng ảnh")
    _log(f"{tid} het ngan sach ({budget}) -> Kite task {kite_tid}, draft {draft_id}")
    return kite_tid


def route_out_of_budget(token, group, rows=None) -> list:
    """Task vai carousel `gave_up` vi het ngan sach -> chuyen Kite. Tra [(tid, kite_tid)].

    approve_service goi MOI vong poll, TRUOC bang tien do: task cu dong trong vong
    nay (ket qua ROUTED_TO_KITE_RESULT) thi bang tien do im lang (LOW-410), tin
    "🖼 … đã tự chuyển Kite" o day la tin duy nhat. Khong bao gio nem: hong o day
    ma de exception len vong poll thi vong poll hieu nham la mat ket noi Telegram."""
    try:
        import hermes_adapter
        from approve_dispatch import ROLE_CAROUSEL
        if rows is None:
            rows = hermes_adapter.job(tu_ts=time.time() - 86400) or []
        candidates = [r for r in rows if r["status"] == "blocked" and r["assignee"] in ROLE_CAROUSEL
                      and r["id"] not in _ROUTE_TRIED]
        if not candidates:
            return []
        runs = hermes_adapter.last_run_many([r["id"] for r in candidates]) or {}
        routed = []
        for task in candidates:
            run = runs.get(task["id"]) or {}
            if not out_of_budget(run):
                continue
            _ROUTE_TRIED.add(task["id"])
            kite_tid = _route_one_out_of_budget(token, group, task, run)
            if kite_tid:
                routed.append((task["id"], kite_tid))
        return routed
    except Exception as e:                                   # noqa: BLE001
        _log(f"chuyen Kite khi het ngan sach hong: {type(e).__name__}: {e!r}")
        return []
