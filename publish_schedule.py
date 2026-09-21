#!/usr/bin/env python3
"""Xep lich dang bai: hai bai lien tiep cach nhau mot tieng.

Truoc file nay, nut "Duyet & dang" lam ca ba viec trong mot thread nen: dang
len Telegram channel, day sang moat, roi sua the. Duyet 5 bai trong 3 phut la
channel ra 5 bai trong 3 phut, va extension cung nha 5 bai len social gan nhu
cung luc.

Gio nut chi CHIEM MOT SLOT roi tra the ve ngay:

    slot = max(bay_gio, last_slot + GAP_SECONDS)

`last_slot` la MOT con tro duy nhat trong state/<brand>/publish_schedule.json.
Hang vang (bai truoc da qua mot tieng) thi slot chinh la bay gio -- bam nut van
la dang ngay, gian cach chi hien ra khi that su co don bai.

Viec dang giao cho cron `publish-due` (moi phut, moi HERMES_HOME mot job):
`due()` liet ke bai toi gio, `publish_one()` dang. Nut "Dang ngay" goi DUNG
`publish_one()` do -- mot duong code, khong co nhanh "dang nhanh" rieng de lech
dan theo thoi gian.

Vi sao cron chu khong phai threading.Timer: lich phai song sot systemctl
restart, OOM va mat dien. Con tro + publish_at nam tren dia, nen may tat ba
tieng roi bat lai thi hang doi van duoc dang bu -- nhung RAI RA, moi tick
mot bai va cach nhau dung GAP_SECONDS (xem `run_due`). Bu DON tung lam
channel ra 13 bai trong 15 phut toi 20/09/2026, dung cai file nay sinh ra
de chan.

Toan bo ly do va cac luat da chot: docs/publish_schedule.md
"""
import fcntl
import json
import os
import sys
import time
from contextlib import contextmanager
from pathlib import Path

import env_load
import state_paths

sys.path.insert(0, str(Path(__file__).resolve().parent))
import moat_publish                                      # noqa: E402

ROOT = env_load.ROOT
DRAFTS = ROOT / "drafts"

# Khoang cach giua hai bai lien tiep. HANG SO, khong phai bien moi truong:
# doi nhip dang bai la mot quyet dinh co chu dinh, nen di qua commit de con
# doc duoc "tu bao gio" trong git log.
GAP_SECONDS = 3600

# Dung sai khi do nhip giua hai lan dang THAT. Cron chay moi phut nen lan
# dang truoc luon tre vai giay so voi gio hen; tru khoan nay di thi bai ke
# tiep khong bi day lui them vai giay moi lan, don lai thanh vai phut sau
# mot ngay.
GAP_TOLERANCE_SECONDS = 120

# Trang thai draft ma file nay them vao vong doi cu (draft/publishing/published/
# publish_failed/rejected).
SCHEDULED = "scheduled"          # da duyet, dang cho toi gio
LAST_PUBLISH_KEY = "last_publish"   # moc lan dang THAT gan nhat, cung file con tro
CANCELLED = "cancelled"          # Ong Chu huy lich truoc khi toi gio


def _state_file(name):
    """Duong dan trong state/<brand>/. Tinh MOI LAN GOI chu khong cache o cap
    module: `env_load.state_dir()` doc CT_STATE_DIR luc goi, nen test chi can
    dat bien moi truong la cach ly duoc, khong phai monkeypatch duong dan."""
    return env_load.state_dir() / name


@contextmanager
def _locked(name):
    """flock doc quyen tren state/<brand>/<name>.

    HAI khoa RIENG, khong gop lam mot:
      - PUBLISH_SLOT_LOCK: chia slot. Giu vai micro-giay.
      - PUBLISH_DUE_LOCK: dang mot bai. Giu toi vai PHUT (upload carousel tren
        uplink ~50 KB/s), va con de hai bai khong upload chong len nhau.
    Gop lam mot la bam "Duyet" bai moi bi treo may phut cho cron dang xong bai
    truoc -- the khong tra ve, Ong Chu bam lai.
    """
    path = _state_file(name)
    with open(path, "a+", encoding="utf-8") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)


def _read_state():
    """Ca file trang thai. Doc ca cum chu khong tung khoa: `reserve` va
    `run_due` ghi hai khoa khac nhau vao CUNG mot file, ai ghi de nguyen
    file la xoa moc cua ben kia."""
    try:
        d = json.loads(_state_file(state_paths.PUBLISH_SCHEDULE_FILE)
                       .read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except Exception:                                    # noqa: BLE001
        # Chua co file, file hong, hoac khoa lac kieu -- coi nhu hang trong.
        # Mat con tro chi lam bai ke tiep dang som hon, khong lam hong gi.
        return {}


def _read_cursor():
    return int(_read_state().get("last_slot") or 0)


def _read_last_publish():
    """Epoch cua lan dang THAT gan nhat (0 = chua dang bao gio)."""
    return int(_read_state().get(LAST_PUBLISH_KEY) or 0)


def _write_last_publish(now):
    with _locked(state_paths.PUBLISH_SLOT_LOCK):
        d = _read_state()
        d[LAST_PUBLISH_KEY] = int(now)
        moat_publish._write_json(
            _state_file(state_paths.PUBLISH_SCHEDULE_FILE), d)


def reserve(now=None):
    """Chiem slot ke tiep cua brand nay, tra ve epoch.

    Ghi con tro NGAY trong lock: mot slot da phat ra khong bao gio duoc phat
    lai, ke ca khi nguoi goi that bai o buoc sau.
    """
    now = int(now if now is not None else time.time())
    with _locked(state_paths.PUBLISH_SLOT_LOCK):
        d = _read_state()
        slot = max(now, int(d.get("last_slot") or 0) + GAP_SECONDS)
        d["last_slot"] = slot
        moat_publish._write_json(
            _state_file(state_paths.PUBLISH_SCHEDULE_FILE), d)
    return slot


def _read_draft(draft_id):
    """Doc draft qua DRAFTS cua CHINH module nay, khong muon cua moat_publish:
    hai bien tro cung mot cho luc chay, nhung ai doi mot ben (test, hoac mot
    ban vi tri drafts/ khac sau nay) ma ben kia khong theo la mot loi cam."""
    return json.loads((DRAFTS / (draft_id + ".json")).read_text(encoding="utf-8"))


def _is_teaser(d):
    """Teaser CHI len Telegram -- `moat_publish.intake` von da tu choi no vi
    Instagram/TikTok khong cho link an duoc. Khong gianh cho voi bai social."""
    return (d.get("category") or "").upper() == "TEASER"


def schedule(draft_id, now=None):
    """Danh dau draft da duyet va hen gio dang. Tra ve epoch se dang.

    Teaser di thang (publish_at = bay gio, con tro dung im); con lai xep hang.
    """
    now = int(now if now is not None else time.time())
    path = DRAFTS / (draft_id + ".json")
    d = _read_draft(draft_id)
    at = now if _is_teaser(d) else reserve(now=now)
    d["publish_at"] = at
    d["status"] = SCHEDULED
    moat_publish._write_json(path, d)
    return at


def due(now=None, brand=None):
    """draft_id da toi gio dang, cua DUNG brand container nay, som truoc.

    Loc brand khong phai cho vui: hai container dung chung thu muc drafts/, ma
    khoa moat moi la thu quyet dinh bai len org nao -- lay nham la dang bai
    dcgr.tech bang khoa cua donniechublog.
    """
    now = int(now if now is not None else time.time())
    if brand is None:
        brand = moat_publish.brand_container()
    ra = []
    for path in DRAFTS.glob("*.json"):
        if path.name.endswith(".meta.json"):     # ho so anh, khong phai draft
            continue
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except Exception:                                # noqa: BLE001
            continue
        if not isinstance(d, dict) or d.get("status") != SCHEDULED:
            continue
        if brand and (d.get("brand") or moat_publish.DEFAULT_BRAND) != brand:
            continue
        at = int(d.get("publish_at") or 0)
        if at > now:
            continue
        ra.append((at, path.stem))
    # Sap theo (gio, ten): gio bang nhau thi van ra mot thu tu on dinh, khong
    # phu thuoc thu tu glob tra ve cua he thong tep.
    return [ten for _, ten in sorted(ra)]


def _publisher():
    """Module approve_post, nap MUON.

    approve_post import file nay o dau file (nut Duyet goi `schedule`), nen
    import nguoc lai o cap module la vong tron. Nap trong ham cung la cach
    moat_publish nap `publish` -- quy uoc san cua repo.
    """
    import approve_post                                   # noqa: PLC0415
    return approve_post


def _secrets():
    """(token, channel) cua brand nay."""
    import publish                                        # noqa: PLC0415
    return publish.load_secrets()


def _finish_card(draft_id, note):
    """Go ban phim tren the duyet va bao ket qua ngay duoi no.

    Cron khong co doi tuong `message` cua callback nhu nhanh nut, nhung the
    nam trong topic writer cua TELEGRAM_GROUP_ID va draft da giu
    `tg_card_message_id` tu luc day ban nhap -- du de sua dung the do.
    """
    try:
        d = _read_draft(draft_id)
    except Exception:                                     # noqa: BLE001
        d = {}
    mid = d.get("tg_card_message_id")
    env_load.load()
    group = os.environ.get("TELEGRAM_GROUP_ID")
    if mid and group:
        moat_publish._tele("editMessageReplyMarkup", chat_id=group,
                           message_id=int(mid), reply_markup={"inline_keyboard": []})
    moat_publish.report_card(draft_id, note)


def publish_one(draft_id):
    """Dang MOT bai: len Telegram channel truoc, chi khi channel nhan moi day
    sang moat. Tra (ok, note). Khong bao gio nem ngoai le.

    Dung chung cho cron `publish-due` va nut "⚡ Đăng ngay" -- mot duong code,
    khong co ban sao "dang nhanh" de lech dan.
    """
    with _locked(state_paths.PUBLISH_DUE_LOCK):
        # Doc lai trang thai TRONG khoa: nguoi vao truoc co the vua dang xong
        # bai nay (hai tick cron chong nhau, hoac cron va nut cung nham mot
        # bai). Chi bai dang cho moi duoc di tiep.
        try:
            d = _read_draft(draft_id)
        except Exception as e:                            # noqa: BLE001
            return False, "khong doc duoc draft: " + str(e)
        if d.get("status") != SCHEDULED:
            return False, "bo qua: trang thai da la " + str(d.get("status"))

        ap = _publisher()
        try:
            token, channel = _secrets()
            res = ap.publish(token, channel, draft_id)
            ok = bool(res.get("ok"))
            ap.mark_draft(draft_id, "published" if ok else "publish_failed")
            note = ("✅ ĐÃ ĐĂNG lên channel" if ok
                    else "⚠️ Đăng lỗi: " + str(res.get("description")))
            if ok:
                # Chi day khi Telegram DA nhan: bai chua len channel la bai
                # chua duyet xong. Loi ben moat chi them mot line vao the.
                pushed, why = moat_publish.intake(draft_id)
                note += ("\n\U0001f4e4 moat: " + why) if pushed else ("\n⚠️ moat: " + why)
                if not pushed:
                    # Nut cua the bi go ngay sau day, nen loi moat nam trong
                    # `note` la mot line chu chet. Mot tin RIENG co nut de
                    # con nguoi ra tay bat cu luc nao.
                    moat_publish.report_card(
                        draft_id,
                        "⚠️ Chưa đẩy được sang moat: " + moat_publish._exit(why)
                        + "\nĐang tự thử lại theo lịch lùi; bấm nút để thử ngay.",
                        [{"text": "🔁 Đẩy lại moat", "callback_data": "mlai:" + draft_id}])
            return ok, note
        except Exception as e:                            # noqa: BLE001
            # Khong bao gio de bai ket vinh vien o 'publishing': ket o do la
            # khong con duong nao bam lai.
            try:
                ap.mark_draft(draft_id, "publish_failed")
            except Exception:                             # noqa: BLE001
                pass
            return False, "⚠️ Đăng lỗi: " + type(e).__name__ + ": " + str(e)


def _publish_with_card(draft_id):
    """Dang mot bai + sua the. Tra (ok, line ban ghi)."""
    ok, note = publish_one(draft_id)
    _finish_card(draft_id, note)
    return ok, ("✅ " if ok else "⚠️ ") + draft_id + ": " + note.replace("\n", " | ")


def run_due(now=None, brand=None):
    """Dau vao cua cron `publish-due`: dang moi bai da toi gio, tra ve cac line
    ban ghi. Im lang khi khong co gi -- cron chay moi phut.

    KHONG giu khoa quanh ca vong lap: `publish_one` tu khoa tung bai, nen mot
    bai upload lau khong chan nut "Duyet" cua bai khac (khoa slot la khoa
    khac).
    """
    now = int(now if now is not None else time.time())
    lines = []
    queue = []
    for draft_id in due(now=now, brand=brand):
        try:
            teaser = _is_teaser(_read_draft(draft_id))
        except Exception:                                 # noqa: BLE001
            teaser = False          # doc khong duoc thi cu coi la bai thuong
        if teaser:
            lines.append(_publish_with_card(draft_id)[1])
            continue
        queue.append(draft_id)

    # Chi MOT bai moi nhip. Khong co dieu kien nay thi mot khoang chet
    # (20/09/2026: ca ngay vi chuyen may) lam moi bai qua han cung luc va
    # tick dau tien day het len channel trong vai phut.
    if queue and now - _read_last_publish() >= GAP_SECONDS - GAP_TOLERANCE_SECONDS:
        ok, line = _publish_with_card(queue[0])
        lines.append(line)
        # Chi ghi moc khi Telegram DA nhan: dang loi thi tick sau phai duoc
        # thu lai ngay, khong phai cho them mot tieng.
        if ok:
            _write_last_publish(now)
    return lines


if __name__ == "__main__":
    for line in run_due():
        print(line)
