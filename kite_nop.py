#!/usr/bin/env python3
"""kite_nop.py — NOP carousel.edu cua Kite: kiem spec, dung bang render_edu.py,
gui album, ban giao, ghi da_dung. Vai chi viet spec.json (khung do
kite_chuan_bi.py in ra).

Kiem TRUOC khi render (render_edu cung co cong chan, nhung bao som thi vai sua
mot vong): so slide 6..10, slide 1 la cover, kind hop le, truong bat buoc tung
kind, ma hinh that -> tep (chi hinh la chart >= 800px), caption khi co image,
theme/hero hop le va (lam lai) phai khac lan truoc, do dai chu vuot muc thi
canh bao.

Dung:
    venv/bin/python kite_nop.py <draft_id>
    venv/bin/python kite_nop.py <draft_id> --khong-gui --out /tmp/k/k.png   # thu
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import anh_chuan_bi as cb                                    # noqa: E402
import kite_chuan_bi as kb                                   # noqa: E402
import nop_chung as nc                                       # noqa: E402

DRAFTS = cb.DRAFTS
BAT_BUOC = {
    "cover": ("eyebrow", "title", "standfirst"),
    "statement": ("eyebrow", "title", "standfirst"),
    "steps": ("eyebrow", "title", "steps"),
    "loop": ("eyebrow", "title", "chips", "standfirst"),
    "figure": ("eyebrow", "title", "image", "caption"),
    "bars": ("eyebrow", "title", "bars", "caption"),
    "cta": ("eyebrow", "title", "checks"),
}
GIOI_HAN = {"title": 70, "standfirst": 240, "callout": 130, "eyebrow": 32}


def giai_spec(spec: dict, m: dict) -> tuple:
    import render_edu
    loi, canh = [], []
    slides = spec.get("slides") or []
    if not (6 <= len(slides) <= 10):
        loi.append(f"có {len(slides)} slide — cần 6..10")
    if slides and slides[0].get("kind") != "cover":
        loi.append("slide 1 phải là kind \"cover\"")
    hinh = {a["ma"]: a for a in kb.hinh_that(m)}
    # brand trong spec render la CHU in o masthead/folio (render_edu chi dung no
    # lam chu) -> phai la handle hien thi (dcgr -> dcgr.tech), khong phai slug.
    # d24ddfc da sua byline/follow, con masthead van in "dcgr" (05/09/2026).
    ra = {"brand": kb.handle_kenh(m["brand"]), "section": spec.get("section") or "RESEARCH",
          "folio": spec.get("folio") or m["title"][:24].upper()}
    theme, hero = spec.get("theme"), spec.get("hero")
    if theme and theme not in render_edu.THEMES:
        loi.append(f"theme \"{theme}\" không có (chọn: {', '.join(render_edu.THEMES)})")
    if hero and hero not in render_edu.HEROES:
        loi.append(f"hero \"{hero}\" không có (chọn: {', '.join(render_edu.HEROES)})")
    if theme:
        ra["theme"] = theme
    if hero:
        ra["hero"] = hero
    ra["slides"] = []
    for i, sl in enumerate(slides, 1):
        k = sl.get("kind")
        if k not in BAT_BUOC:
            loi.append(f"slide {i}: kind \"{k}\" không hợp lệ (cover/statement/steps/loop/figure/bars/cta)")
            continue
        thieu = [f for f in BAT_BUOC[k] if not sl.get(f)]
        if thieu:
            loi.append(f"slide {i} ({k}): thiếu {', '.join(thieu)}")
        s2 = dict(sl)
        img = sl.get("image")
        if img:
            if img not in hinh:
                loi.append(f"slide {i}: image \"{img}\" không phải mã hình thật dùng được "
                           f"(có: {', '.join(hinh) or 'không có'}) — bỏ image hoặc đổi mã")
            else:
                s2["image"] = hinh[img]["goc"]
                if not sl.get("caption"):
                    loi.append(f"slide {i}: có image thì phải có caption \"… · via <ai>\"")
        for f, gh in GIOI_HAN.items():
            v = sl.get(f)
            if isinstance(v, str) and len(v) > gh:
                canh.append(f"slide {i}: {f} dài {len(v)} ký tự (> {gh}) — có thể tràn/nhỏ chữ")
        for c in sl.get("cards", []) or []:
            if len(str(c.get("text", ""))) > 100:
                canh.append(f"slide {i}: card \"{str(c.get('text'))[:30]}…\" dài, rút ≤ 90")
        for st in sl.get("steps", []) or []:
            if len(str(st.get("desc", ""))) > 90:
                canh.append(f"slide {i}: step desc dài, rút ≤ 80")
        for t in sl.get("checks", []) or []:
            if len(str(t)) > 80:
                canh.append(f"slide {i}: check dài, rút ≤ 70")
        if k == "bars":
            bs = sl.get("bars") or []
            if not 2 <= len(bs) <= 6:
                loi.append(f"slide {i}: bars cần 2..6 cột (có {len(bs)})")
            for j, b in enumerate(bs, 1):
                b = b if isinstance(b, dict) else {}
                try:
                    render_edu._gia_tri(b.get("value"))
                except (ValueError, TypeError):
                    loi.append(f"slide {i}: cột {j} \"value\" phải là số thật trong bài (có {b.get('value')!r})")
                if len(str(b.get("label", ""))) > 28:
                    canh.append(f"slide {i}: cột {j} label dài, rút ≤ 28")
        if any("nguồn" in str(v).lower() for v in sl.values() if isinstance(v, str)):
            loi.append(f"slide {i}: dẫn nguồn ghi 'via', không ghi 'nguồn'")
        ra["slides"].append(s2)
    return ra, loi, canh


def main() -> int:
    ap = argparse.ArgumentParser(description="Nop carousel.edu cua Kite (tat dinh)")
    ap.add_argument("draft_id")
    ap.add_argument("--spec")
    ap.add_argument("--khong-gui", action="store_true")
    ap.add_argument("--bo-qua-dau", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    meta, brand, wd, m, spec, spec_path, da_dung = nc.nap(a.draft_id, a.spec, "kite_chuan_bi.py", "kite_nop.py")
    spec_r, loi, canh = giai_spec(spec, m)
    hook = (spec.get("slides") or [{}])[0].get("title", "")
    if da_dung:
        if (spec.get("theme"), spec.get("hero")) == (da_dung.get("theme"), da_dung.get("hero")):
            loi.append("LÀM LẠI: theme và hero trùng lần trước — đổi ít nhất một")
        if nc.chuan(hook) == nc.chuan(da_dung.get("hook")):
            loi.append("LÀM LẠI: hook bìa giống lần trước — viết khác")
    for c in canh:
        print(f"[CANH BAO] {c}")
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        print(f"\nSua {spec_path} roi chay lai: venv/bin/python kite_nop.py {a.draft_id}")
        return 1

    out = Path(a.out or meta.get("image") or str(DRAFTS / f"{a.draft_id}.png"))
    out.parent.mkdir(parents=True, exist_ok=True)
    stem = out.with_suffix("")
    for p in stem.parent.glob(stem.name + "_[0-9].png"):
        p.unlink(missing_ok=True)
    p_spec = wd / "render_edu.spec.json"
    p_spec.write_text(json.dumps(spec_r, ensure_ascii=False, indent=2), encoding="utf-8")
    args = [sys.executable, str(ROOT / "render_edu.py"), "--spec", str(p_spec), "--out", str(out),
            "--brand", brand] + (["--bo-qua-dau"] if a.bo_qua_dau else [])
    r = subprocess.run(args, cwd=str(ROOT), capture_output=True, text=True, timeout=900)
    if r.returncode != 0:
        for d in ((r.stderr or "") + "\n" + (r.stdout or "")).splitlines():
            if d.strip().startswith("-") or "CONG CHAN" in d or "CANH BAO" in d or "Error" in d:
                print(f"[LOI] {d.strip()}")
        cuoi = [d for d in (r.stderr or "").strip().splitlines() if d.strip()]
        if cuoi:
            print(f"[LOI] {cuoi[-1]}")
        print(f"\nSua {spec_path} theo bao loi roi chay lai: venv/bin/python kite_nop.py {a.draft_id}")
        return 1
    m_theme = re.search(r"theme=(\w+) hero=(\S+)", r.stdout or "")
    theme, hero = (m_theme.group(1), m_theme.group(2)) if m_theme else (spec.get("theme"), spec.get("hero"))
    n = len(spec_r["slides"])
    files = [out] + [Path(f"{stem}_{i}.png") for i in range(2, n + 1)]
    thieu = [str(f) for f in files if not f.exists()]
    if thieu:
        sys.exit(f"[LOI] render_edu bao xong nhung thieu tep: {thieu}")

    hinh = [s.get("image") for s in spec.get("slides") or [] if s.get("image")]
    bg = "\n".join([f"Nguồn tin: {m['title']}", f"Link gốc: {m['link']}"]
                   + ([f"Via: {m['via']}"] if m.get("via") else [])
                   + [f"Bộ slide: {n} slide art vector gốc, theme {theme}, hero {hero}"]
                   + ([f"Hình thật đã chèn: {', '.join(hinh)} (nguồn: bài gốc)"] if hinh else [])
                   + [f"Hook bìa: {hook}", f"Tệp: {out}"])
    bg_path = (wd if a.khong_gui else DRAFTS) / f"{a.draft_id}.ban_giao.md"
    bg_path.write_text(bg, encoding="utf-8")

    mid = None
    if a.khong_gui:
        print(f"[thu] khong gui Telegram (--khong-gui). {n} slide o {out.parent}")
    else:
        mid = nc.gui_album("carousel-edu", files, f"Carousel edu {n} slide: {hook}", a.draft_id, wd, da_dung,
                           {"theme": theme, "hero": hero, "hook": hook})
    # Bang den (kanban swarm): ban giao co cau truc cua Kite len the goc + dong
    # "[metadata]" de Kite dan vao kanban_complete -> Miles thay trong
    # "Parent task results". Best-effort.
    md = {"slide": n, "hook": hook, "theme": theme, "hero": hero, "hinh_that": hinh,
          "tep": str(out), "ban_giao": str(bg_path), "message_id": mid, "vai": "kite"}
    if not a.khong_gui:
        nc.ghi_bang_den(a.draft_id, "anh", md, "kite")
    print("[metadata] " + json.dumps(md, ensure_ascii=False))
    print(f"[xong] {n} slide -> {out}; theme={theme} hero={hero}"
          + (f"; da gui topic carousel-edu (message_id={mid}) kem nut duyet" if mid else "")
          + f"; ban giao: {bg_path}")
    print("Ket qua task (dung dong nay de ket thuc task): "
          f"Dựng {n} slide carousel edu “{hook}” (theme {theme}, hero {hero})"
          + ("; đã gửi topic kèm nút duyệt, bàn giao nguồn cho Miles tự động." if mid else "; chưa gửi (thử)."))
    return 0


if __name__ == "__main__":
    sys.exit(main())
