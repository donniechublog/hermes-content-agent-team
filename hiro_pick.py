#!/usr/bin/env python3
"""hiro_pick.py — Ong Chu reply `Hiro` / `Hiro 1-10` vao bao cao researcher -> MOT task Hiro.

LOW-403 (con cua LOW-401, Ong Chu 25/09/2026). Hiro gom CA danh sach mot researcher
(Finn/Nova/Vera/Qinn) vua nop thanh MOT carousel "ban tin van": moi headline mot slide.

CU PHAP — chu `Hiro` DUNG DAU, nen khong dung lenh chon tin nao dang co:
    Hiro          ca danh sach cua bao cao duoc reply
    Hiro 1-10     headline 1 toi 10 (nhan ca `1 - 10`, `1–10`, `1..10`, `Hiro: 3-5`)

Vi sao chu dung dau (Ong Chu: "thay doi cach nhap de ko bi xung dot"): `read_pick_command`
doc `1 - 10` la HAI tin rieng (1 va 10) giao Ethan, con `1 - Ethan` la tin 1 cho Ethan —
khoang so dat truoc ten vai se dung nghia ca hai. Moi tin MO DAU bang "hiro" thi hom nay
`read_pick_command` tra None ("hiro" khong nam trong NAME_BRIGHT_CAP) va roi ve hoi thoai,
nen chan truoc no khong doi nghia lenh cu nao.

Tin da vao bo Hiro KHONG bi danh dau `assignments`: Ong Chu chot Hiro chi dua tieu de + y
chinh, Ethan/Dre/Kite van nhan rieng tung tin de lam sau (khong chan trung giua hai tang).
"""
import json
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
# Instagram nhan toi da 20 anh mot bai. Hiro KHONG co slide bia (Ong Chu: "10 headlines thi
# tao 10 slide"), nen 20 headline = 20 slide. Vera da chan o 15 (LOW-283).
MAX_SLIDES = 20
# Tin nhan tu Telegram: khong giai ma so dai hon the (so thu tu trong bao cao <= 99).
_MAX_DIGITS = 2

_HEAD = re.compile(r"^\s*hiro\b\s*[:,]?\s*(.*?)\s*$", re.I | re.S)
_RANGE = re.compile(r"^(\d{1,%d})\s*(?:-|–|—|\.\.)\s*(\d{1,%d})$" % (_MAX_DIGITS, _MAX_DIGITS))
# Phan sau chu Hiro CHI co so/dau -> Ong Chu dang go lenh (sai cu phap thi bao loi).
# Co chu cai ("Hiro oi lam gi day") -> hoi thoai, tra None.
_LOOKS_LIKE_COMMAND = re.compile(r"^[\d\s,;.:\-–—]+$")

USAGE = ("Cú pháp: <code>Hiro</code> (cả danh sách) hoặc <code>Hiro 1-10</code> "
         f"(headline 1 tới 10, tối đa {MAX_SLIDES} tin một bộ).")


@dataclass(frozen=True)
class HiroCommand:
    """`start`/`end` None = ca danh sach. `error` khac rong = go sai cu phap, bao lai."""
    start: int | None = None
    end: int | None = None
    error: str = ""


def read_hiro_command(text: str) -> HiroCommand | None:
    """Lenh Hiro trong mot tin reply, hoac None neu tin khong phai lenh Hiro."""
    m = _HEAD.match(text or "")
    if not m:
        return None
    rest = m.group(1)
    if not rest:
        return HiroCommand()
    r = _RANGE.match(rest)
    if r:
        a, b = int(r.group(1)), int(r.group(2))
        if a < 1 or b < a:
            return HiroCommand(error=f"Khoảng <code>{a}-{b}</code> không hợp lệ — số đầu phải "
                                     f"từ 1 và không lớn hơn số cuối. {USAGE}")
        if b - a + 1 > MAX_SLIDES:
            return HiroCommand(error=f"Khoảng <code>{a}-{b}</code> là {b - a + 1} tin, quá "
                                     f"{MAX_SLIDES} slide một bài. {USAGE}")
        return HiroCommand(start=a, end=b)
    if _LOOKS_LIKE_COMMAND.match(rest):
        return HiroCommand(error=f"Không hiểu <code>Hiro {html_escape(rest)}</code>. {USAGE}")
    return None


def select_items(items: list, cmd: HiroCommand) -> tuple[list, str]:
    """(cac tin theo thu tu so, loi). Loi khac rong thi khong tao task."""
    by_index = {it.get("index"): it for it in items if isinstance(it.get("index"), int)}
    if not by_index:
        return [], "Báo cáo này không có tin nào để dựng."
    if cmd.start is None:
        chosen = [by_index[k] for k in sorted(by_index)]
        if len(chosen) > MAX_SLIDES:
            return [], (f"Báo cáo có {len(chosen)} tin, quá {MAX_SLIDES} slide một bài — "
                        f"gõ khoảng, vd <code>Hiro 1-{MAX_SLIDES}</code>.")
        return chosen, ""
    missing = [k for k in range(cmd.start, cmd.end + 1) if k not in by_index]
    if missing:
        return [], (f"Báo cáo không có tin số {', '.join(map(str, missing))} "
                    f"(có #{min(by_index)}–#{max(by_index)}).")
    return [by_index[k] for k in range(cmd.start, cmd.end + 1)], ""


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
    first, last = items[0]["index"], items[-1]["index"]
    return f"#{first}" if first == last else f"#{first}–#{last}"


def process_hiro(token, group, thread_id, scan_role: str, cmd: HiroCommand, manifest_path):
    """Tao MOT task Hiro tu bao cao duoc reply. Chay nen (_run_background)."""
    if not enabled():
        _send_text(token, group, "⚠️ Hiro chưa bật ở brand này (chưa có topic <code>hiro</code>) "
                                 "— chưa tạo gì.", thread=thread_id)
        return
    if cmd.error:
        _send_text(token, group, "⚠️ Chưa tạo bộ Hiro. " + cmd.error, thread=thread_id)
        return
    manifest_path = (manifest_path or approve_pick.manifest_already_send(scan_role)
                     or approve_pick.latest_manifest(scan_role))
    if not manifest_path:
        _send_text(token, group, f"⚠️ Chưa tạo bộ Hiro: {_role.display_name(scan_role)} chưa có "
                                 "báo cáo nào trong container này.", thread=thread_id)
        return
    items, err = select_items(_load_json(Path(manifest_path), {}).get("items", []), cmd)
    if err:
        _send_text(token, group, "⚠️ Chưa tạo bộ Hiro. " + err, thread=thread_id)
        return

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
        return
    write_sidecars(draft_id, scan_role, items, BRAND, digest_title(scan_role, items), body, tid)
    dong = "\n".join(f"<b>#{it['index']}</b> <i>{html_escape((it.get('title') or '')[:70])}</i>"
                     for it in items)
    _send_text(token, group,
               f"📨 Đã nhận — <b>Hiro</b> dựng bản tin vắn <b>{len(items)} slide</b> "
               f"từ báo cáo {scan_name} ({_span(items)}), task {tid}:\n{dong}",
               thread=thread_id)
