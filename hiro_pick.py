#!/usr/bin/env python3
"""hiro_pick.py — Ong Chu reply `Hiro` / `Hiro 1-10` vao bao cao researcher -> MOT task Hiro.

LOW-403 (con cua LOW-401, Ong Chu 25/09/2026). Hiro gom CA danh sach mot researcher
(Finn/Nova/Vera/Qinn) vua nop thanh MOT carousel "ban tin van": moi headline mot slide.

CU PHAP — chu `Hiro` DUNG DAU, nen khong dung lenh chon tin nao dang co:
    Hiro              ca danh sach cua bao cao duoc reply
    Hiro 1-10         headline 1 toi 10 (nhan ca `1 - 10`, `1–10`, `1..10`, `Hiro: 3-5`)
    Hiro /3,5         ca danh sach, BO tin 3 va 5 (LOW-418; phan sau dau `/` la tin bi loai)
    Hiro 1-12 /4,6    tin 1..12, bo 4 va 6; loai ca khoang: `Hiro /11-15`

Vi sao chu dung dau (Ong Chu: "thay doi cach nhap de ko bi xung dot"): `read_pick_command`
doc `1 - 10` la HAI tin rieng (1 va 10) giao Ethan, con `1 - Ethan` la tin 1 cho Ethan —
khoang so dat truoc ten vai se dung nghia ca hai. Moi tin MO DAU bang "hiro" thi hom nay
`read_pick_command` tra None ("hiro" khong nam trong NAME_BRIGHT_CAP) va roi ve hoi thoai,
nen chan truoc no khong doi nghia lenh cu nao.

Tin da vao bo Hiro KHONG bi danh dau `assignments`: Ong Chu chot Hiro chi dua tieu de + y
chinh, Ethan/Dre/Kite van nhan rieng tung tin de lam sau (khong chan trung giua hai tang).
"""
import json
import os
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from html import escape as html_escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                               # noqa: E402
import role as _role                                          # noqa: E402
import state_paths                                           # noqa: E402
import task_bodies                                           # noqa: E402

from approve_base import BRAND, DRAFTS, ROOT, STATE_DIR, _load_json, _send_text, _write_json, log  # noqa: E402
from approve_dispatch import kanban_create, standard_label    # noqa: E402
import approve_pick                                          # noqa: E402

ROLE = "hiro"
# LOW-418 (Ong Chu 25/09/2026: "de Hiro dang 10 bai la duoc"): Telegram nhan toi da 10 anh
# mot album (sendMediaGroup), moat toi da 10 anh mot bai (moat_publish.py:299) — bo 11-20
# slide mat slide cuoi khi len kenh (LOW-413). Hiro KHONG co bia, nen 10 headline = 10 slide.
# Bao cao dai hon (Vera toi 15, LOW-283) thi Ong Chu loai tin bang dau `/`.
MAX_SLIDES = 10
# Tin nhan tu Telegram: khong giai ma so dai hon the (so thu tu trong bao cao <= 99).
_MAX_DIGITS = 2

_HEAD = re.compile(r"^\s*hiro\b\s*[:,]?\s*(.*?)\s*$", re.I | re.S)
_RANGE = re.compile(r"^(\d{1,%d})\s*(?:-|–|—|\.\.)\s*(\d{1,%d})$" % (_MAX_DIGITS, _MAX_DIGITS))
# Phan sau chu Hiro CHI co so/dau -> Ong Chu dang go lenh (sai cu phap thi bao loi).
# Co chu cai ("Hiro oi lam gi day") -> hoi thoai, tra None.
_LOOKS_LIKE_COMMAND = re.compile(r"^[\d\s,;.:/\-–—]+$")
_DASH = re.compile(r"\s*(?:-|–|—|\.\.)\s*")
_EXCLUDE_TOKEN = re.compile(r"^(\d{1,%d})(?:-(\d{1,%d}))?$" % (_MAX_DIGITS, _MAX_DIGITS))

USAGE = ("Cú pháp: <code>Hiro</code> (cả danh sách), <code>Hiro 1-10</code> (headline 1 tới 10), "
         "<code>Hiro /3,5</code> (bỏ tin 3 và 5), <code>Hiro 1-12 /4,6</code>; "
         f"tối đa {MAX_SLIDES} tin một bộ.")


@dataclass(frozen=True)
class HiroCommand:
    """`start`/`end` None = ca danh sach. `exclude`: so tin bi loai (sau dau `/`).
    `error` khac rong = go sai cu phap, bao lai."""
    start: int | None = None
    end: int | None = None
    exclude: tuple = ()
    error: str = ""


def _runs(nums) -> list:
    """[3, 4, 5, 9] -> [(3, 5), (9, 9)]."""
    ra = []
    for n in sorted(set(nums)):
        if ra and n == ra[-1][1] + 1:
            ra[-1] = (ra[-1][0], n)
        else:
            ra.append((n, n))
    return ra


def numbers_label(nums) -> str:
    """Chu hien cho Ong Chu: [1, 2, 4, 6, 7, 8] -> '#1–#2, #4, #6–#8'."""
    return ", ".join(f"#{a}" if a == b else f"#{a}–#{b}" for a, b in _runs(nums))


def numbers_command(nums) -> str:
    """Chu go lai duoc sau dau `/`: [3, 5, 11, 12, 13] -> '3,5,11-13'."""
    return ",".join(str(a) if a == b else f"{a}-{b}" for a, b in _runs(nums))


def _read_exclude(text: str) -> tuple[tuple, str]:
    """Phan sau dau `/`: '3, 5 11-15' -> ((3, 5, 11, 12, 13, 14, 15), ''); sai -> ((), loi)."""
    ra = []
    for tok in re.split(r"[,;\s/]+", _DASH.sub("-", text.strip())):
        if not tok:
            continue
        m = _EXCLUDE_TOKEN.match(tok)
        if not m:
            return (), f"Không hiểu phần loại tin <code>/{html_escape(text.strip())}</code>. {USAGE}"
        a = int(m.group(1))
        b = int(m.group(2) or a)
        if a < 1 or b < a:
            return (), f"Khoảng loại <code>{a}-{b}</code> không hợp lệ. {USAGE}"
        ra += range(a, b + 1)
    if not ra:
        return (), f"Sau dấu <code>/</code> phải có số tin cần loại, vd <code>Hiro /3,5</code>. {USAGE}"
    return tuple(sorted(set(ra))), ""


def read_hiro_command(text: str) -> HiroCommand | None:
    """Lenh Hiro trong mot tin reply, hoac None neu tin khong phai lenh Hiro."""
    m = _HEAD.match(text or "")
    if not m:
        return None
    rest = m.group(1)
    head, slash, tail = rest.partition("/")
    head = head.strip()
    start = end = None
    if head:
        r = _RANGE.match(head)
        if not r:
            if _LOOKS_LIKE_COMMAND.match(rest):
                return HiroCommand(error=f"Không hiểu <code>Hiro {html_escape(rest)}</code>. {USAGE}")
            return None                                      # "Hiro oi ..." -> hoi thoai
        start, end = int(r.group(1)), int(r.group(2))
        if start < 1 or end < start:
            return HiroCommand(error=f"Khoảng <code>{start}-{end}</code> không hợp lệ — số đầu phải "
                                     f"từ 1 và không lớn hơn số cuối. {USAGE}")
    exclude = ()
    if slash:
        if not _LOOKS_LIKE_COMMAND.match(tail or "/"):
            return None                                      # "Hiro / anh oi ..." -> hoi thoai
        exclude, loi = _read_exclude(tail)
        if loi:
            return HiroCommand(error=loi)
        if start is not None:
            ngoai = [n for n in exclude if not start <= n <= end]
            if ngoai:
                return HiroCommand(error=f"Tin loại {numbers_label(ngoai)} không nằm trong khoảng "
                                         f"<code>{start}-{end}</code>. {USAGE}")
    if start is not None:
        kept = end - start + 1 - len(exclude)
        if kept < 1:
            return HiroCommand(error=f"Đã loại hết các tin trong khoảng <code>{start}-{end}</code>. {USAGE}")
        if kept > MAX_SLIDES:
            return HiroCommand(error=f"Khoảng <code>{start}-{end}</code> còn {kept} tin, quá "
                                     f"{MAX_SLIDES} slide một bài — loại thêm {kept - MAX_SLIDES} tin "
                                     f"bằng dấu <code>/</code>. {USAGE}")
    return HiroCommand(start=start, end=end, exclude=exclude)


def select_items(items: list, cmd: HiroCommand) -> tuple[list, str]:
    """(cac tin theo thu tu so, loi). Loi khac rong thi khong tao task."""
    by_index = {it.get("index"): it for it in items if isinstance(it.get("index"), int)}
    if not by_index:
        return [], "Báo cáo này không có tin nào để dựng."
    co = f"(có {numbers_label(by_index)})"
    pool = sorted(by_index) if cmd.start is None else list(range(cmd.start, cmd.end + 1))
    missing = [k for k in pool if k not in by_index]
    if missing:
        return [], f"Báo cáo không có tin số {', '.join(map(str, missing))} {co}."
    # Loai mot so khong co trong bao cao = go nham so: bao, khong bo qua ngam (tin dinh loai
    # van len slide ma Ong Chu tuong da bo).
    lac = [k for k in cmd.exclude if k not in by_index]
    if lac:
        return [], f"Báo cáo không có tin số {', '.join(map(str, lac))} để loại {co}."
    bo = set(cmd.exclude)
    chosen = [k for k in pool if k not in bo]
    if not chosen:
        return [], "Đã loại hết tin trong báo cáo, không còn gì để dựng."
    if len(chosen) > MAX_SLIDES:
        over = len(chosen) - MAX_SLIDES
        goi_y = sorted(bo | set(chosen[-over:]))
        khoang = f"{cmd.start}-{cmd.end} " if cmd.start is not None else ""
        return [], (f"Còn {len(chosen)} tin, quá {MAX_SLIDES} slide một bài — loại thêm {over} tin "
                    f"bằng dấu <code>/</code>, vd <code>Hiro {khoang}/{numbers_command(goi_y)}</code>.")
    return [by_index[k] for k in chosen], ""


def make_draft_id(scan_role: str, now: datetime | None = None) -> str:
    """`hiro-<researcher>-<yymmdd-HHMMSS>`: <= 55 ky tu, dung khuon draft_id cua nut Duyet
    (approve_post._DRAFT_ID_HOP_LE). Theo giay: hai lenh Hiro cung bao cao la hai bo rieng."""
    now = now or datetime.now()
    return f"{ROLE}-{re.sub(r'[^a-z0-9]+', '', scan_role.lower())[:12]}-{now:%y%m%d-%H%M%S}"


# Chi mang sang job nhung truong Hiro can: tieu de + tom tat len slide, link/anh de tim anh.
_ITEM_KEYS = ("index", "title", "summary_vi", "link", "via", "category", "image_url", "source_note")


def write_job(draft_id: str, scan_role: str, manifest_path: Path, items: list, brand: str) -> Path:
    """Ghi `hiro_job.json` vao thu muc chuan bi cua draft — hiro_prepare doc tu day (LOW-404)."""
    wd = state_paths.workdir(STATE_DIR, draft_id)
    wd.mkdir(parents=True, exist_ok=True)
    job = {
        "draft_id": draft_id,
        "scan_role": scan_role,
        "brand": brand,
        "manifest": str(manifest_path),
        "created_at": datetime.now().isoformat(timespec="seconds"),
        "items": [{k: it.get(k) for k in _ITEM_KEYS if it.get(k) is not None} for it in items],
    }
    p = wd / state_paths.HIRO_JOB_FILE
    p.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
    return p


def enabled() -> bool:
    """Hiro chi chay o brand DA CO topic `hiro` (cung khuon `scan_submit.overflow_target`).

    Chua tao topic/profile tren may chu ma van tao task thi task nam 'ready' mai khong ai
    nhan (su co 01/09/2026) va album khong co cho gui (`send_telegram._topic` nem). Chot
    nay cho merge code truoc khi dung profile ma khong bat Hiro o dau ca."""
    return ROLE in env_load.topics()


def digest_title(scan_role: str, items: list, now: datetime | None = None) -> str:
    now = now or datetime.now()
    return f"Bản tin {_role.display_name(scan_role)} {now:%d/%m}: {len(items)} tin ({_span(items)})"


def write_sidecars(draft_id: str, scan_role: str, items: list, brand: str, title: str,
                   body: str, task_id: str) -> str:
    """meta / img / writer sidecar — cung ba tep `create_pair` ghi cho Dre, de nut Duyet va
    Lam lai cua approve_post chay nguyen duong cu. Tra ve vai viet.

    meta.source_url = link tin #dau: draft_write can MOT link (LOW-405 lo phan viet cho ca
    bo); `digest_links` giu du danh sach."""
    links = [it.get("link", "") for it in items]
    nhan = Counter(standard_label(it.get("category")) for it in items).most_common(1)
    meta_p = DRAFTS / f"{draft_id}.meta.json"
    meta = _load_json(meta_p, {})
    meta.update({"source_url": links[0], "category": nhan[0][0] if nhan else "BUSINESS",
                 "via": "", "image": str(DRAFTS / f"{draft_id}.png"), "title": title,
                 "score": None, "score_reason": "", "brand": brand,
                 "digest": True, "scan_role": scan_role, "digest_links": links})
    _write_json(meta_p, meta)
    _write_json(DRAFTS / f"{draft_id}.img.json",
                {"image_role": ROLE, "carousel": True, "title": title, "body": body,
                 "remakes": 0, "link": links[0], "summary": "", "source_note": "", "via": "",
                 "image_task": task_id, "blocked_for_engine": False})
    writer = _role.writer_for(scan_role, brand)
    headlines = "\n".join(f"{i}. {it.get('title', '')} — {it.get('link', '')}"
                          for i, it in enumerate(items, start=1))
    _write_json(DRAFTS / f"{draft_id}.writer.json",
                {"writer_role": writer, "title": title, "created": False,
                 "root_task": None, "dre_task": task_id,
                 "body": task_bodies.HIRO_WRITER_BODY.format(
                     title=title, n=len(items), headlines=headlines, draft_id=draft_id,
                     brand=brand, goc=str(ROOT), persona=_role.display_name(writer).lower())})
    return writer


def _span(items: list) -> str:
    """Cac tin cua bo: '#1–#10', hoac '#1–#2, #4, #6–#12' khi co tin bi loai giua chung."""
    return numbers_label(it["index"] for it in items)


def process_hiro(token, group, thread_id, scan_role: str, cmd: HiroCommand, manifest_path,
                 auto: bool = False):
    """Tao MOT task Hiro tu bao cao duoc reply (hoac vua nop, `auto`). Tra task id, None neu
    khong tao. Duong reply chay nen (_run_background); duong tu dong goi dong bo tu scan_submit."""
    if not enabled():
        _send_text(token, group, "⚠️ Hiro chưa bật ở brand này (chưa có topic <code>hiro</code>) "
                                 "— chưa tạo gì.", thread=thread_id)
        return None
    if cmd.error:
        _send_text(token, group, "⚠️ Chưa tạo bộ Hiro. " + cmd.error, thread=thread_id)
        return None
    manifest_path = (manifest_path or approve_pick.manifest_already_send(scan_role)
                     or approve_pick.latest_manifest(scan_role))
    if not manifest_path:
        _send_text(token, group, f"⚠️ Chưa tạo bộ Hiro: {_role.display_name(scan_role)} chưa có "
                                 "báo cáo nào trong container này.", thread=thread_id)
        return None
    items, err = select_items(_load_json(Path(manifest_path), {}).get("items", []), cmd)
    if err:
        _send_text(token, group, "⚠️ Chưa tạo bộ Hiro. " + err, thread=thread_id)
        return None

    draft_id = make_draft_id(scan_role)
    job = write_job(draft_id, scan_role, Path(manifest_path), items, BRAND)
    scan_name = _role.display_name(scan_role)
    body = task_bodies.HIRO_BODY.format(draft_id=draft_id, goc=str(ROOT), n=len(items),
                                        scan_name=scan_name, brand=BRAND, job=str(job))
    title = f"Hiro: bản tin vắn {len(items)} tin từ {scan_name} ({_span(items)})"
    tid, loi = kanban_create(title, ROLE, body)
    log("hiro", f"{draft_id} {scan_role} {_span(items)} manifest={Path(manifest_path).name} "
                f"task={tid} loi={loi}")
    if loi:
        _send_text(token, group, f"⚠️ Chưa tạo bộ Hiro: lỗi tạo task — {html_escape(loi[:200])}",
                   thread=thread_id)
        return None
    write_sidecars(draft_id, scan_role, items, BRAND, digest_title(scan_role, items), body, tid)
    dong = "\n".join(f"<b>#{it['index']}</b> <i>{html_escape((it.get('title') or '')[:70])}</i>"
                     for it in items)
    bo = f" — bỏ {numbers_label(cmd.exclude)}" if cmd.exclude else ""
    dau = ("🤖 <b>Hiro</b> tự dựng (chế độ tự động, <code>/hiro off</code> để tắt) bản tin vắn"
           if auto else "📨 Đã nhận — <b>Hiro</b> dựng bản tin vắn")
    _send_text(token, group,
               f"{dau} <b>{len(items)} slide</b> từ báo cáo {scan_name} ({_span(items)}){bo}, "
               f"task {tid}:\n{dong}",
               thread=thread_id)
    return tid


def first_items_command(items: list) -> HiroCommand:
    """Che do tu dong (LOW-406, Ong Chu 25/09/2026: *"neu bat auto mode thi cu lay 10 tin dau
    tien"*): loai moi tin sau tin thu MAX_SLIDES theo thu tu so. Bao cao <= 10 tin thi lay het."""
    so = sorted(it["index"] for it in items if isinstance(it.get("index"), int))
    return HiroCommand(exclude=tuple(so[MAX_SLIDES:]))


def auto_from_report(scan_role: str, manifest_path) -> str:
    """`/hiro on` -> dung bo Hiro tu bao cao VUA gui (scan_submit goi, SAU khi bao cao chinh da
    len topic). Tra doan them vao dong "Ket qua task" cua researcher ("" = khong lam gi).

    KHONG BAO GIO nem: bao cao da gui roi — loi o day ma lam scan_submit tra ma khac 0 thi vai
    nop lai, tuc gui THEM mot ban bao cao (su co 12/09/2026, xem scan_submit.BLOCK_SEND)."""
    try:
        import hiro_auto
        if not manifest_path or not hiro_auto.is_on() or not enabled():
            return ""
        env_load.load()
        token, group = os.environ.get("TELEGRAM_BOT_TOKEN"), os.environ.get("TELEGRAM_GROUP_ID")
        thread = env_load.topics().get(scan_role)
        if not (token and group and thread):
            return " ⚠️ Hiro tự động: thiếu token/group/topic, chưa dựng bản tin."
        items = _load_json(Path(manifest_path), {}).get("items", [])
        tid = process_hiro(token, group, thread, scan_role, first_items_command(items),
                           Path(manifest_path), auto=True)
        return (f" Hiro tự dựng bản tin vắn (task {tid})." if tid
                else " ⚠️ Hiro tự động chưa dựng được bản tin (xem topic).")
    except Exception as e:                                   # noqa: BLE001 — xem docstring
        log("hiro", f"tu dong {scan_role} loi: {type(e).__name__}: {e!r}")
        return f" ⚠️ Hiro tự động lỗi ({type(e).__name__}), chưa dựng bản tin."
