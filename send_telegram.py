#!/usr/bin/env python3
"""Gui anh (mot hoac nhieu — sendPhoto/sendMediaGroup) vao dung topic Telegram
cua mot vai, va ghi lai nhat ky (message_id, file, mo ta) de sau nay tra loi
mot yeu cau sua con biet dang noi anh nao.

Dung cho MOI vai dung anh (slug: designer, carousel, gin, itachi...) de
tu day anh minh vua dung ra topic cua chinh minh — khong phai cho writer viet
xong roi moi co anh trong bai. Gin/Itachi con duoc goi tu `--gui <vai>` trong
tao_nen_ai.py, no goi thang ham post() o day.

Khong dung chung tien trinh voi approve_service.py (dich vu duyet bai) — day
la mot lenh CHAY MOT LAN, khong long-poll, khong dung chung offset Telegram
voi dich vu kia. An toan goi bao nhieu lan cung duoc.

Dung:
    venv/bin/python send_telegram.py --vai itachi \\
      --anh a.png --anh b.png --mo-ta "Doraemon bat tay Conan, lang La"
    venv/bin/python send_telegram.py --vai itachi --list      # gan day da gui gi
"""
import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load
import role

STATE = env_load.state_dir() / "telegram_sent"
TOPICS = env_load.topics_path()
API = "https://api.telegram.org/bot{token}/{method}"


class SendError(RuntimeError):
    """Loi gui anh/topic. La Exception THUONG de nguoi goi thu vien bat duoc —
    SystemExit lot qua moi `except Exception` (bai hoc o publish.TelegramTuChoi).
    CLI (main) va cac nop bat loi nay roi thoat gon."""


def _topic(vai: str) -> int:
    m = env_load.topics()
    if vai not in m:
        raise SendError(f"Vai '{vai}' chua co topic trong {TOPICS}")
    return m[vai]


def _md5(files) -> list:
    return [hashlib.md5(Path(f).read_bytes()).hexdigest() for f in files]


# Nghi giua cac lan thu lai khi mang loi (LOW-134). Test dat ve 0.
RETRY_DELAYS = (2, 5, 15)


def _telegram_post(token: str, method: str, data: dict, open_files=None,
                   timeout: int = 60, retry_all: bool = False) -> dict:
    """Goi Bot API, thu lai khi MANG loi; het luot thi nem SendError — khong de
    httpx.* lot ra ngoai. Su co 14/09/2026 (LOW-134): ConnectError o tin nut Duyet
    khong phai SendError nen nhanh cuu cua submit_common khong chay, vai chi thay
    traceback tran.

    Mac dinh chi thu lai loi CHUA GUI DI (ConnectError/ConnectTimeout): ReadTimeout
    o sendMediaGroup co the album DA len, gui lai la trung album. `retry_all` danh
    cho tin nut — trung mot tin nut con hon mat nut.
    `open_files()` mo lai tep MOI lan thu (handle da doc het sau lan dau)."""
    err = None
    for attempt in range(len(RETRY_DELAYS) + 1):
        handles = open_files() if open_files else None
        try:
            with httpx.Client(timeout=timeout) as c:
                r = c.post(API.format(token=token, method=method), data=data, files=handles)
            return r.json()
        except (httpx.ConnectError, httpx.ConnectTimeout) as e:
            err = e
        except httpx.TransportError as e:
            if not retry_all:
                raise SendError(f"Mang loi khi {method}: {type(e).__name__}: {e}") from e
            err = e
        except ValueError as e:
            raise SendError(f"Telegram tra ve khong phai JSON ({method}): {e}") from e
        finally:
            for fh in (handles or {}).values():
                (fh[1] if isinstance(fh, tuple) else fh).close()
        if attempt < len(RETRY_DELAYS):
            print(f"[mang] {method} loi {type(err).__name__}, thu lai sau {RETRY_DELAYS[attempt]}s",
                  file=sys.stderr)
            time.sleep(RETRY_DELAYS[attempt])
    raise SendError(f"Mang loi khi {method} sau {len(RETRY_DELAYS) + 1} lan thu: "
                    f"{type(err).__name__}: {err}")


def _write_journal(vai: str, message_ids, files, mo_ta: str, button_draft=None) -> None:
    """`message_ids` = MOI tin cua album (LOW-134): Ong Chu reply vao anh nao cung
    tra ra dung draft. Co `button_draft` thi ghi `button_message_id` = None cho toi
    khi tin nut len that (_mark_button_sent) — lan chay lai nho do biet gui bu nut."""
    STATE.mkdir(parents=True, exist_ok=True)
    dong = {"ts": int(time.time()), "message_id": message_ids[-1], "message_ids": list(message_ids),
            "files": [str(f) for f in files], "md5": _md5(files), "mo_ta": mo_ta}
    if button_draft:
        dong["button_draft"], dong["button_message_id"] = button_draft, None
    with (STATE / f"{vai}.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(dong, ensure_ascii=False) + "\n")


def _mark_button_sent(vai: str, album_message_id, button_message_id) -> None:
    """Ghi `button_message_id` vao dong cua album trong so (ghi nguyen tu)."""
    p = STATE / f"{vai}.jsonl"
    dong = p.read_text(encoding="utf-8").splitlines()
    for i in range(len(dong) - 1, -1, -1):
        try:
            d = json.loads(dong[i])
        except ValueError:
            continue
        if d.get("message_id") == album_message_id:
            d["button_message_id"] = button_message_id
            dong[i] = json.dumps(d, ensure_ascii=False)
            tmp = p.with_suffix(".jsonl.tmp")
            tmp.write_text("\n".join(dong) + "\n", encoding="utf-8")
            os.replace(tmp, p)
            return


def _send_button(token: str, group: str, thread_id: int, draft_id: str, album_message_id) -> int:
    """Gui tin nut Duyet/Lam lai/Bo (reply vao album), tra message_id; hong thi SendError."""
    res = _telegram_post(token, "sendMessage", {
        "chat_id": group, "message_thread_id": str(int(thread_id)),
        "text": "Ảnh đã xong. Duyệt để người viết làm caption, hoặc bỏ nếu ảnh chưa đạt.",
        "reply_markup": json.dumps(_kb_approve(draft_id)),
        "reply_to_message_id": str(int(album_message_id)),
        "allow_sending_without_reply": "true",
    }, retry_all=True)
    if not res.get("ok"):
        raise SendError(f"Telegram tu choi tin nut Duyet: {res.get('description')}")
    return res["result"]["message_id"]


def _already_send_near_bottom(vai: str, files, phut: int = 30):
    """Tra ve ban ghi gan nhat neu CUNG bo file da gui trong `phut` phut.

    So theo NOI DUNG (md5) chu khong chi theo ten (audit 05/09/2026): ban "Lam
    lai" ghi ra dung ten cu drafts/<id>.png, so ten thi album moi bi coi la
    trung va KHONG bao gio len topic. Dong cu chua co md5 thi so ten nhu truoc."""
    import time as _t
    p = STATE / f"{vai}.jsonl"
    if not p.exists():
        return None
    ten = sorted(Path(f).name for f in files)
    md5 = sorted(_md5(files))
    moc = _t.time() - phut * 60
    for dong in reversed(p.read_text(encoding="utf-8").splitlines()):
        try:
            d = json.loads(dong)
        except Exception:                                    # noqa: BLE001
            continue
        if d.get("ts", 0) < moc:
            break
        giong = (sorted(d["md5"]) == md5) if d.get("md5") else \
            (sorted(Path(f).name for f in d.get("files", [])) == ten)
        if giong:
            rec = {"message_id": d.get("message_id"),
                   "luc": _t.strftime("%H:%M", _t.localtime(d["ts"]))}
            if "button_message_id" in d:            # dong cu (truoc LOW-134) khong co
                rec["button_message_id"] = d["button_message_id"]
            return rec
    return None


def _kb_approve(draft_id: str) -> dict:
    """Ba nut cho tam anh (approve_service xu ly callback):
      imgok   Duyet   -> sinh task viet caption.
      imgredo Lam lai -> tao lai task anh, designer dung anh khac.
      imgno   Bo han   -> giet tin, khong viet khong lam lai."""
    return {"inline_keyboard": [
        [{"text": "✅ Duyệt ảnh → viết caption", "callback_data": "imgok:" + draft_id}],
        [{"text": "🔄 Làm lại", "callback_data": "imgredo:" + draft_id},
         {"text": "🗑 Bỏ hẳn", "callback_data": "imgno:" + draft_id}],
    ]}


def post(vai: str, files, mo_ta: str = "", reply_to=None, duyet=None) -> dict:
    """Gui 1 hoac nhieu anh (>1 tu dong thanh album) vao topic cua `vai`.

    `reply_to` (message_id, tuy chon): gui thanh REPLY vao dung tin nhan yeu
    cau — dung khi tra ket qua cho mot yeu cau sua cu the, de Ong Chu thay
    ngay ket qua nam duoi dung cau hoi cua minh thay vi mot tin roi o cuoi
    topic. Bo trong thi gui binh thuong (khong reply ai).

    Tra ve response Telegram (list ket qua neu la album, dict neu mot anh).
    Luon ghi nhat ky sau khi gui thanh cong, de `--list` doc lai duoc.
    """
    env_load.load()
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    group = os.environ.get("TELEGRAM_GROUP_ID")
    if not token or not group:
        raise SendError("Thieu TELEGRAM_BOT_TOKEN/TELEGRAM_GROUP_ID trong secret.<brand>.env")
    thread_id = _topic(vai)

    files = [Path(f) for f in files]
    thieu = [f for f in files if not f.exists()]
    if thieu:
        raise SendError(f"Khong thay file: {', '.join(str(f) for f in thieu)}")
    if len(files) > 10:
        raise SendError("Toi da 10 anh mot album (gioi han Telegram).")

    # CHONG GUI TRUNG: cung vai + cung bo file trong 30 phut -> khong gui lai.
    # Su co 04/09/2026: Kite sinh agent con de "kiem tra anh", agent con tu gui
    # album (msg 301) roi het gio; Kite khong biet nen gui lai (msg 308). Ong
    # Chu thay mot tin hai album. Ai goi lai cung nhan message_id cu, khong loi.
    truoc = _already_send_near_bottom(vai, files, phut=30)
    if truoc:
        print(f"da gui truoc do luc {truoc['luc']} (message_id={truoc['message_id']}), "
              f"KHONG gui lai. Muon gui lai that thi doi ten file hoac cho qua 30 phut.")
        out = {"ok": True, "result": {"message_id": truoc["message_id"]}, "trung": True,
               "button_state": "unknown"}
        if duyet and "button_message_id" in truoc:
            if truoc["button_message_id"]:
                out["button_state"], out["button_message_id"] = "sent", truoc["button_message_id"]
            else:
                # Lan truoc album len nhung tin nut hong (LOW-134). Truoc day nhanh
                # nay return luon: chay lai bao nhieu lan cung KHONG BAO GIO co nut.
                bid = _send_button(token, group, thread_id, duyet, truoc["message_id"])
                _mark_button_sent(vai, truoc["message_id"], bid)
                print(f"da gui BU nut Duyet (message_id={bid}) cho album cu.")
                out["button_state"], out["button_message_id"] = "resent", bid
        return out

    data = {"chat_id": group, "message_thread_id": str(int(thread_id))}
    if reply_to:
        data["reply_to_message_id"] = str(int(reply_to))
    if len(files) == 1:
        if mo_ta:
            data["caption"] = mo_ta[:1024]
        res = _telegram_post(token, "sendPhoto", data, timeout=120, open_files=lambda: {
            "photo": (files[0].name, open(files[0], "rb"), "image/png")})
    else:
        items = []
        for i in range(len(files)):
            e = {"type": "photo", "media": f"attach://file{i}"}
            if i == 0 and mo_ta:
                e["caption"] = mo_ta[:1024]
            items.append(e)
        data["media"] = json.dumps(items)
        res = _telegram_post(token, "sendMediaGroup", data, timeout=180, open_files=lambda: {
            f"file{i}": open(f, "rb") for i, f in enumerate(files)})

    if not res.get("ok"):
        raise SendError(f"Gui Telegram loi: {res.get('description')}")

    result = res["result"]
    ids = [m.get("message_id") for m in (result if isinstance(result, list) else [result])]
    _write_journal(vai, ids, files, mo_ta, button_draft=duyet)

    # Album KHONG gan duoc nut (gioi han Bot API), nen nut Duyet luon nam tren
    # mot tin nhan chu RIENG ngay duoi anh — dung cho ca anh don lan album.
    if duyet:
        try:
            bid = _send_button(token, group, thread_id, duyet, ids[0])
        except SendError as e:
            # Khong duoc im lang: anh da len nhung nut Duyet khong xuat hien thi
            # pipeline dung o cong duyet ma khong ai biet. So da ghi
            # button_message_id=None nen chay lai se CHI gui bu nut.
            raise SendError(f"Anh da gui nhung tin nhan nut Duyet LOI: {e} — chay lai DUNG "
                            f"lenh nop se chi gui bu nut, khong trung album.") from e
        _mark_button_sent(vai, ids[-1], bid)
        res["button_state"], res["button_message_id"] = "sent", bid
    return res


def near_bottom(vai: str, n: int = 5) -> list:
    p = STATE / f"{vai}.jsonl"
    if not p.exists():
        return []
    dong = [json.loads(x) for x in p.read_text(encoding="utf-8").splitlines() if x.strip()]
    return dong[-n:]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--vai", required=True, type=role.canonical_slug,
                    help="slug vai — khop key trong topics.<brand>.json (nhan ca slug cu)")
    ap.add_argument("--anh", action="append", default=[], help="Duong dan PNG, lap lai cho nhieu anh (album)")
    ap.add_argument("--mo-ta", default="", help="Caption ngan mo ta anh — giup tra loi SAU biet dang noi anh nao")
    ap.add_argument("--reply-to", type=int, default=None,
                    help="message_id can reply — ket qua sua theo yeu cau thi reply DUNG tin da yeu cau, "
                         "khong gui roi o cuoi topic")
    ap.add_argument("--duyet", default=None, metavar="DRAFT_ID",
                    help="Gan nut Duyet/Bo cho tam anh (draft_id). Bam Duyet thi "
                         "approve_service moi sinh task viet caption; khong co co "
                         "nay thi chi day anh, khong hoi duyet (dung cho chat le).")
    ap.add_argument("--list", action="store_true", help="In cac lan gui gan day (mac dinh 5) thay vi gui moi")
    a = ap.parse_args()

    if a.list:
        for d in near_bottom(a.vai):
            print(json.dumps(d, ensure_ascii=False))
        return

    if not a.anh:
        ap.error("--anh la bat buoc (tru khi dung --list)")
    try:
        res = post(a.vai, a.anh, a.mo_ta, reply_to=a.reply_to, duyet=a.duyet)
    except SendError as e:
        sys.exit(str(e))
    result = res["result"]
    mid = result[-1]["message_id"] if isinstance(result, list) else result["message_id"]
    print(f"da gui {len(a.anh)} anh vao topic '{a.vai}', message_id={mid}")


if __name__ == "__main__":
    main()
