#!/usr/bin/env python3
"""Bang lich dang cua Ada (LOW-428): MOT tin moi brand moi ngay trong topic
Ada, tu sua moi khi co bai duoc xep lich, da dang, dang loi hay bi huy lich.

Vi sao: 30/09/2026 Ong Chu duyet anh 9 carousel blog roi hoi "Miles va Jika co
lam gi dau?" -- ca 9 caption da nop, da duyet va dang xep hang moi tieng mot
bai, nhung the caption nam rai o topic Miles/Jika va ket qua dang ghi duoi tung
the. Khong co cho nao nhin mot lan thay ca hang lich.

Script thuan, khong goi LLM: trang thai lich la du lieu co hoc (drafts/*.json),
dung tinh than SOUL Ada. Chay moi vong poll cua approve_service (~50s) -- chi
doc vai tep JSON, va chi goi Telegram khi noi dung bang DOI (so dau van tay).
Cron `publish-due` la tien trinh khac nen khong goi ham nay: bai no dang xong
hien len bang o vong poll ke tiep, khong co hai tien trinh cung sua mot tin.
"""
import hashlib
import json
import os
import time
from datetime import datetime, timedelta, timezone
from html import escape as html_escape

import env_load
import moat_publish
import role
import state_paths

VN = timezone(timedelta(hours=7))          # cung quy uoc voi approve_post.VN
DRAFTS = env_load.ROOT / "drafts"

# Topic cua Ada trong state/topics.<brand>.json.
BOARD_TOPIC = "ada"

# Trang thai draft len bang, kem bieu tuong. Thu tu = thu tu dem o dong tieu de.
STATUS_ICONS = {
    "published": "✅",
    "scheduled": "🕒",
    "publishing": "⏳",
    "publish_failed": "⚠️",
    "cancelled": "🗑",
}
STATUS_LABELS = {
    "published": "đã đăng",
    "scheduled": "chờ",
    "publishing": "đang đăng",
    "publish_failed": "lỗi",
    "cancelled": "huỷ",
}

# Tin Telegram toi da 4096 ky tu; mot dong ~150. 25 dong du cho mot ngay
# (nhip 1 tieng/bai), phan du gop thanh mot dong "... va N bai nua".
MAX_ROWS = 25
TITLE_MAX = 70


def _today(now):
    return datetime.fromtimestamp(int(now), VN).strftime("%Y-%m-%d")


def _clock(at):
    return datetime.fromtimestamp(int(at), VN).strftime("%H:%M")


def _writer_and_title(draft_id):
    """(ten nguoi viet, tieu de bai goc) tu sidecar <draft>.writer.json.
    Thieu sidecar thi ("", "") -- bang van hien dong, chi thieu ten."""
    try:
        s = json.loads((DRAFTS / (draft_id + ".writer.json")).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return "", ""
    slug = str(s.get("writer_role") or "")
    return (role.display_name(slug) if slug else ""), str(s.get("title") or "")


def collect(now=None, brand=None):
    """Cac dong cua bang: bai cua brand nay co gio dang ROI VAO hom nay (gio VN),
    cong moi bai con cho o ngay sau. Sap theo gio dang.

    Loc brand cung ly le voi publish_schedule.due: hai container dung chung
    thu muc drafts/."""
    now = int(now if now is not None else time.time())
    if brand is None:
        brand = moat_publish.brand_container()
    today = _today(now)
    rows = []
    for path in DRAFTS.glob("*.json"):
        if path.name.count(".") > 1:          # .meta/.img/.writer/.bak -- khong phai draft
            continue
        try:
            d = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(d, dict):
            continue
        status = d.get("status")
        if status not in STATUS_ICONS:
            continue
        if brand and (d.get("brand") or moat_publish.DEFAULT_BRAND) != brand:
            continue
        at = int(d.get("publish_at") or 0)
        if not at:
            continue
        day = _today(at)
        if day != today and not (status == "scheduled" and day > today):
            continue
        writer, title = _writer_and_title(path.stem)
        rows.append({"draft_id": path.stem, "status": status, "at": at,
                     "writer": writer, "title": title or path.stem,
                     "card": d.get("tg_card_message_id")})
    rows.sort(key=lambda r: (r["at"], r["draft_id"]))
    return rows


def _card_link(group, mid):
    """Link toi the duyet trong supergroup (-100xxxx -> t.me/c/xxxx/mid)."""
    g = str(group or "")
    if not mid or not g.startswith("-100"):
        return ""
    return f"https://t.me/c/{g[4:]}/{int(mid)}"


def render(rows, now, brand, group=None):
    """Noi dung bang (HTML Telegram). KHONG chua gio cap nhat -- phan do ghep
    rieng o `refresh` de dau van tay chi doi khi lich that su doi."""
    today = datetime.fromtimestamp(int(now), VN)
    counts = {s: 0 for s in STATUS_ICONS}
    for r in rows:
        counts[r["status"]] += 1
    summary = " · ".join(f"{STATUS_ICONS[s]} {counts[s]} {STATUS_LABELS[s]}"
                         for s in STATUS_ICONS if counts[s])
    lines = [f"📅 <b>Lịch đăng {html_escape(brand or '')} — {today:%d/%m}</b>",
             summary or "Chưa có bài nào được xếp lịch hôm nay.", ""]
    for r in rows[:MAX_ROWS]:
        title = r["title"]
        if len(title) > TITLE_MAX:
            title = title[:TITLE_MAX - 1] + "…"
        title = html_escape(title)
        link = _card_link(group, r["card"])
        if link:
            title = f'<a href="{link}">{title}</a>'
        when = _clock(r["at"])
        if _today(r["at"]) != _today(now):
            when += datetime.fromtimestamp(r["at"], VN).strftime(" %d/%m")
        who = f" · {html_escape(r['writer'])}" if r["writer"] else ""
        lines.append(f"{STATUS_ICONS[r['status']]} {when}{who} · {title}")
    if len(rows) > MAX_ROWS:
        lines.append(f"… và {len(rows) - MAX_ROWS} bài nữa")
    return "\n".join(lines).rstrip()


def _state_path():
    return env_load.state_dir() / state_paths.SCHEDULE_BOARD_FILE


def _read_state():
    try:
        d = json.loads(_state_path().read_text(encoding="utf-8"))
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def _write_state(d):
    p = _state_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    env_load.write_json(p, d)


def _thread():
    try:
        return json.loads(env_load.topics_path().read_text(encoding="utf-8")).get(BOARD_TOPIC)
    except (OSError, ValueError):
        return None


def refresh(call, token, group, now=None, brand=None):
    """Dua bang len dung trang thai. `call(token, method, **kw)` la
    approve_base.call (luon tra dict, khong nem).

    - Chua co bai nao hom nay va chua co tin -> im lang (khong gui bang rong).
    - Ngay moi hoac chua co tin -> gui tin moi, nho message_id.
    - Noi dung doi -> editMessageText; tin da bi xoa -> gui tin moi.
    Tra ve "sent" / "edited" / "unchanged" / "empty" / "error: ...".
    """
    now = int(now if now is not None else time.time())
    if brand is None:
        brand = moat_publish.brand_container()
    rows = collect(now=now, brand=brand)
    body = render(rows, now, brand, group)
    fingerprint = hashlib.sha1(body.encode("utf-8"), usedforsecurity=False).hexdigest()
    st = _read_state()
    day = _today(now)
    mid = st.get("message_id") if st.get("date") == day else None
    if mid and st.get("fingerprint") == fingerprint:
        return "unchanged"
    if not mid and not rows:
        return "empty"
    text = body + f"\n\n<i>Cập nhật {_clock(now)}</i>"
    if mid:
        r = call(token, "editMessageText", chat_id=group, message_id=mid, text=text,
                 parse_mode="HTML", disable_web_page_preview=True)
        desc = str(r.get("description") or "")
        if r.get("ok") or "not modified" in desc:
            _write_state({"date": day, "message_id": mid, "fingerprint": fingerprint})
            return "edited"
        if "not found" not in desc and "can't be edited" not in desc:
            return "error: " + desc
        # tin bang da bi xoa / qua cu -> gui tin moi ben duoi
    thread = _thread()
    r = call(token, "sendMessage", chat_id=group, text=text, parse_mode="HTML",
             disable_web_page_preview=True,
             **({"message_thread_id": thread} if thread else {}))
    new_mid = (r.get("result") or {}).get("message_id")
    if not r.get("ok") or not new_mid:
        return "error: " + str(r.get("description"))
    _write_state({"date": day, "message_id": new_mid, "fingerprint": fingerprint})
    return "sent"


if __name__ == "__main__":
    # In thu bang cua brand hien tai, khong gui gi.
    _now = time.time()
    _brand = moat_publish.brand_container()
    env_load.load()
    print(render(collect(now=_now, brand=_brand), _now, _brand,
                 os.environ.get("TELEGRAM_GROUP_ID")))
