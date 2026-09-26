#!/usr/bin/env python3
"""hiro_submit.py — NOP carousel ban tin van cua Hiro (tat dinh, LOW-404).

Doc spec vai viet (moi headline mot slide: `index`, `image`, `title`, `summary`), chay cong,
dung slide bang `digest_slide`, gui album len topic `hiro` kem nut Duyet. Sidecar meta/img/
writer da co tu luc chon (hiro_pick) nen nut Duyet/Lam lai cua approve_post chay duong cu.

CONG (vi pham = dung, in cach sua):
  - moi tin trong danh sach phai co MOT slide hoac nam trong `skipped` kem ly do — khong bo
    im lang; thu tu slide = thu tu so; ma anh phai la anh CUA CHINH tin do;
  - tieng Viet co dau (carousel._gate_text), bo em-dash; chu vua khung 20% (digest_slide);
  - sau khi ve: nen chu dung luat overlay LOW-286 / nen phang LOW-341, do tren pixel.

Tran MAX_SLIDES = 10 (LOW-418, bang hiro_pick.MAX_SLIDES): vua MOT album Telegram. `send` van
chia album moi ALBUM_MAX anh, nut Duyet o album cuoi — phong khi tran doi.

KHONG ghi so "anh da dung" (`rules.record_used`): anh hero cua mot tin trong ban tin van la
anh Ethan/Dre se can khi Ong Chu giao rieng tin do (Ong Chu chot 25/09: hai tang khong loai
tru nhau) — ghi vao so la chan chinh bai sau cua tin do.

Dung:
    venv/bin/python hiro_submit.py <draft_id> [--khong-gui] [--out /tmp/x.png]
"""
import argparse
import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import env_load                                               # noqa: E402
import hiro_prepare                                           # noqa: E402
import role                                                   # noqa: E402
import state_paths                                            # noqa: E402

ROLE = hiro_prepare.ROLE
DRAFTS = ROOT / "drafts"
MAX_SLIDES = 10                    # = hiro_pick.MAX_SLIDES (LOW-418); test giu hai ban khop nhau
ALBUM_MAX = 10                     # gioi han sendMediaGroup cua Telegram
TITLE_MAX, SUMMARY_MAX = 110, 260  # ky tu — tran cung truoc khi do khung (digest_slide)


def resolve(spec: dict, job: dict, images: dict, bo_qua_dau: bool = False) -> tuple[list, list]:
    """(slide da giai [{index,image,title,summary,code,style,label,category}], loi). Loi rong moi dung.
    Kieu slide theo VI TRI (hiro_prepare.style_at): le = bia logo, chan = quote (LOW-420)."""
    import carousel
    import digest_slide
    from card import drop_mark_forbid
    loi, ra, chunks = [], [], []
    order = [it["index"] for it in job["items"]]
    slides = spec.get("slides") or []
    skipped = {s.get("index"): str(s.get("reason") or "").strip() for s in spec.get("skipped") or []}
    seen = set()
    for pos, s in enumerate(slides, start=1):
        n = s.get("index")
        nhan = f"slide {pos} (tin #{n})"
        if n not in order:
            loi.append(f"{nhan}: `index` {n!r} khong co trong danh sach tin ({order})")
            continue
        if n in seen:
            loi.append(f"{nhan}: tin #{n} xuat hien hai lan")
            continue
        seen.add(n)
        codes = {a["code"]: a for a in images.get(n) or []}
        a = codes.get(s.get("image"))
        if not a:
            loi.append(f"{nhan}: ma anh {s.get('image')!r} khong phai anh cua tin #{n} "
                       f"(co: {', '.join(codes) or 'khong co anh nao — chuyen sang skipped'})")
        title = drop_mark_forbid(str(s.get("title") or "").strip())
        summary = drop_mark_forbid(str(s.get("summary") or "").strip())
        if not title or not summary:
            loi.append(f"{nhan}: thieu `title` hoac `summary`")
            continue
        if len(title) > TITLE_MAX or len(summary) > SUMMARY_MAX:
            loi.append(f"{nhan}: title {len(title)}/{TITLE_MAX}, summary {len(summary)}/{SUMMARY_MAX} "
                       "ky tu — rut gon")
            continue
        style = hiro_prepare.style_at(pos)
        if style == "quote":
            vua = digest_slide.check_text(title, summary)
            if vua:
                loi.append(f"{nhan}: {vua}")
        chunks += [(f"{nhan}/title", title), (f"{nhan}/summary", summary)]
        item = next((it for it in job["items"] if it["index"] == n), {})
        label = drop_mark_forbid(str(s.get("label") or hiro_prepare.logo_label(images, n)).strip())[:24]
        category = str(s.get("category") or item.get("category") or "BUSINESS").strip().upper()[:20]
        if a:
            ra.append({"index": n, "code": a["code"], "image": a["path"], "title": title,
                       "summary": summary, "style": style, "label": label, "category": category})
    for n, reason in skipped.items():
        if n not in order:
            loi.append(f"skipped: `index` {n!r} khong co trong danh sach tin")
        elif n in seen:
            loi.append(f"tin #{n} vua co slide vua nam trong skipped")
        elif not reason:
            loi.append(f"skipped tin #{n}: thieu `reason` (vi sao bo)")
    thieu = [n for n in order if n not in seen and n not in skipped]
    if thieu:
        loi.append(f"tin {', '.join(f'#{n}' for n in thieu)} khong co slide cung khong nam trong "
                   "skipped — moi tin phai co mot slide, bo thi ghi ly do")
    got = [s.get("index") for s in slides if s.get("index") in order]
    if got != sorted(got, key=order.index):
        loi.append(f"thu tu slide {got} lech thu tu so {order} — giu dung thu tu bao cao")
    if not slides:
        loi.append("spec khong co slide nao")
    if len(slides) > MAX_SLIDES:
        loi.append(f"{len(slides)} slide, qua {MAX_SLIDES} slide mot bai")
    loi += carousel._gate_text(chunks, bo_qua_dau)
    return ra, loi


def clear_old_slides(stem: Path) -> None:
    """Xoa <id>_2..N.png cua lan truoc: lan lam lai it slide hon se lot slide cu vao album."""
    for p in env_load.album_secondary(stem.name, stem.parent):
        p.unlink(missing_ok=True)


def handoff(job: dict, slides: list, images: dict) -> str:
    L = [f"Bản tin vắn {len(slides)} tin từ {role.display_name(job['scan_role'])}", ""]
    by = {it["index"]: it for it in job["items"]}
    for k, s in enumerate(slides, start=1):
        it = by[s["index"]]
        dom = next((a["domain"] for a in images.get(s["index"]) or [] if a["code"] == s["code"]), "")
        L.append(f"Slide {k} (tin #{s['index']}): {s['title']}")
        L.append(f"  Link: {it.get('link', '')}" + (f" | ảnh ← {dom}" if dom else ""))
    return "\n".join(L)


def send(files: list, title: str, draft_id: str) -> int | None:
    """Gui album (chia moi ALBUM_MAX anh), nut Duyet o album cuoi. Tra message_id album dau."""
    import send_telegram
    chunks = [files[i:i + ALBUM_MAX] for i in range(0, len(files), ALBUM_MAX)]
    first = None
    for k, part in enumerate(chunks, start=1):
        cap = f"Bản tin vắn {len(files)} slide: {title}"
        if len(chunks) > 1:
            dau = (k - 1) * ALBUM_MAX + 1
            cap += f" (phần {k}/{len(chunks)}: slide {dau}–{dau + len(part) - 1})"
        try:
            res = send_telegram.post(ROLE, [str(f) for f in part], cap[:1000],
                                     duyet=draft_id if k == len(chunks) else None)
        except send_telegram.SendError as e:
            # Chay lai DUNG lenh nop: album da len thi post() nhan ra (chong gui trung 30 phut)
            # va chi gui bu nut Duyet — cung co che LOW-134 cua Dre.
            sys.exit(f"[LOI] gui Telegram phan {k}/{len(chunks)}: {e}\nDoi 1-2 phut roi chay lai "
                     "DUNG lenh nop (khong gui trung album da len).")
        result = res.get("result")
        msgs = result if isinstance(result, list) else [result or {}]
        first = first or msgs[0].get("message_id")
    return first


def main() -> int:
    ap = argparse.ArgumentParser(description="Nop carousel ban tin van cua Hiro")
    ap.add_argument("draft_id")
    ap.add_argument("--spec", help="Tep spec (mac dinh state/<brand>/prepare/<id>/spec.json)")
    ap.add_argument("--khong-gui", action="store_true", help="Chi dung slide, khong gui Telegram")
    ap.add_argument("--bo-qua-dau", action="store_true",
                    help="Tat cong tieng Viet (chi khi chu THAT SU la tieng Anh)")
    ap.add_argument("--out", help="Ghi slide ra cho khac (de thu, khong de len drafts/)")
    a = ap.parse_args()
    role.set_active_role(ROLE)

    wd = hiro_prepare.workdir(a.draft_id)
    job = hiro_prepare.load_job(a.draft_id)
    cache = wd / state_paths.HIRO_IMAGES_FILE
    spec_path = Path(a.spec) if a.spec else wd / "spec.json"
    if not cache.exists() or not spec_path.exists():
        sys.exit(f"[LOI] chua chuan bi — chay truoc: venv/bin/python hiro_prepare.py {a.draft_id}")
    images = {int(k): v for k, v in json.loads(cache.read_text(encoding="utf-8")).items()}
    spec = json.loads(spec_path.read_text(encoding="utf-8"))

    slides, loi = resolve(spec, job, images, a.bo_qua_dau)
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        print(f"\nSua {spec_path} (chi phan bi bao) roi chay lai: "
              f"venv/bin/python hiro_submit.py {a.draft_id}")
        return 1

    import digest_slide
    out = Path(a.out or DRAFTS / f"{a.draft_id}.png")
    clear_old_slides(out.with_suffix(""))
    tone = str(spec.get("background_tone") or "dark").strip().lower()
    paths, gate = digest_slide.build_all(slides, out, job["brand"], tone)
    if gate:
        for e in gate:
            print(f"[LOI] {e}")
        print("Nen chu sai luat overlay (LOW-286) / nen phang (LOW-341) — loi code, bao Ong Chu.")
        return 1

    meta = json.loads((DRAFTS / f"{a.draft_id}.meta.json").read_text(encoding="utf-8")) \
        if (DRAFTS / f"{a.draft_id}.meta.json").exists() else {}
    title = meta.get("title") or f"Bản tin {role.display_name(job['scan_role'])}"
    bg_path = state_paths.handoff_file(wd if a.khong_gui else DRAFTS, a.draft_id)
    bg_path.write_text(handoff(job, slides, images), encoding="utf-8")

    mid = None
    if a.khong_gui:
        print(f"[thu] khong gui Telegram (--khong-gui). {len(paths)} slide o {out.parent}")
    else:
        mid = send(paths, title, a.draft_id)
        (wd / state_paths.PREVIOUS_SUBMISSION_FILE).write_text(json.dumps(
            {"image_ids": [s["code"] for s in slides], "submitted_at": time.strftime("%H:%M %d/%m"),
             "message_id": mid}, ensure_ascii=False), encoding="utf-8")
    skipped = spec.get("skipped") or []
    md = {"slide": len(paths), "skipped": [s.get("index") for s in skipped], "file_path": str(out),
          "handoff_path": str(bg_path), "message_id": mid}
    print(f"[xong] {len(paths)} slide -> {out}"
          + (f"; da gui topic hiro (message_id={mid}) kem nut duyet" if mid else ""))
    print("[metadata] " + json.dumps(md, ensure_ascii=False))
    # `skipped` khong con chi la "khong co anh": tran 10 slide (LOW-418) va tin vai tu bo cung vao day.
    bo = f", bỏ {len(skipped)} tin (lý do trong spec)" if skipped else ""
    print("Ket qua task (dung dong nay de ket thuc task): "
          f"Dựng bản tin vắn {len(paths)} slide{bo}; "
          + ("đã gửi topic kèm nút duyệt." if mid else "chưa gửi (thử)."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
