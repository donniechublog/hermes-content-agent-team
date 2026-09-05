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
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import anh_chuan_bi as cb                                    # noqa: E402
import kite_chuan_bi as kb                                   # noqa: E402

DRAFTS = cb.DRAFTS
BAT_BUOC = {
    "cover": ("eyebrow", "title", "standfirst"),
    "statement": ("eyebrow", "title", "standfirst"),
    "steps": ("eyebrow", "title", "steps"),
    "loop": ("eyebrow", "title", "chips", "standfirst"),
    "figure": ("eyebrow", "title", "image", "caption"),
    "cta": ("eyebrow", "title", "checks"),
}
GIOI_HAN = {"title": 70, "standfirst": 240, "callout": 130, "eyebrow": 32}


def _chuan(t):
    return re.sub(r"\s+", " ", (t or "").strip().lower())


def giai_spec(spec: dict, m: dict) -> tuple:
    import render_edu
    loi, canh = [], []
    slides = spec.get("slides") or []
    if not (6 <= len(slides) <= 10):
        loi.append(f"có {len(slides)} slide — cần 6..10")
    if slides and slides[0].get("kind") != "cover":
        loi.append("slide 1 phải là kind \"cover\"")
    hinh = {a["ma"]: a for a in kb.hinh_that(m)}
    ra = {"brand": m["brand"], "section": spec.get("section") or "RESEARCH",
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
            loi.append(f"slide {i}: kind \"{k}\" không hợp lệ (cover/statement/steps/loop/figure/cta)")
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
        if any("nguồn" in str(v).lower() for v in sl.values() if isinstance(v, str)):
            loi.append(f"slide {i}: dẫn nguồn ghi 'via', không ghi 'nguồn'")
        ra["slides"].append(s2)
    return ra, loi, canh


def ghi_bang_den(draft_id: str, key: str, value, author: str = "kite") -> None:
    """Ghi mot muc len bang den cua bai qua bang_den.py (python cua hermes). Im lang
    khi loi — chi in canh bao. Giong dre_nop/miles_nop."""
    hermes_py = Path.home() / "hermes-agent" / "venv" / "bin" / "python"
    try:
        r = subprocess.run([str(hermes_py), str(ROOT / "bang_den.py"), "ghi", draft_id,
                            key, json.dumps(value, ensure_ascii=False), "--author", author],
                           cwd=str(ROOT), capture_output=True, text=True, timeout=60)
        if r.returncode != 0 or "[bang-den] lỗi" in (r.stderr or ""):
            print(f"[CANH BAO] bang den: {(r.stderr or r.stdout).strip()[-200:]}")
    except Exception as e:                                   # noqa: BLE001
        print(f"[CANH BAO] bang den: {type(e).__name__}: {e}")


def main() -> int:
    ap = argparse.ArgumentParser(description="Nop carousel.edu cua Kite (tat dinh)")
    ap.add_argument("draft_id")
    ap.add_argument("--spec")
    ap.add_argument("--khong-gui", action="store_true")
    ap.add_argument("--bo-qua-dau", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    meta = cb.nap_meta(a.draft_id)
    brand = cb._brand_cua(meta)
    import env_load
    wd = cb.workdir(env_load.state_dir(), a.draft_id)
    m = cb._doc_json(wd / "xong.json")
    if not m:
        sys.exit(f"Chua chuan bi. Chay truoc: venv/bin/python kite_chuan_bi.py {a.draft_id}")
    spec_path = Path(a.spec) if a.spec else wd / "spec.json"
    if not spec_path.exists():
        sys.exit(f"Chua co spec: {spec_path} — viet theo khung trong {wd / 'brief.md'} roi chay lai.")
    try:
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
    except Exception as e:                                   # noqa: BLE001
        sys.exit(f"[LOI] spec.json khong phai JSON hop le: {type(e).__name__}: {e}")

    da_dung = cb._doc_json(wd / "da_dung.json")
    spec_r, loi, canh = giai_spec(spec, m)
    hook = (spec.get("slides") or [{}])[0].get("title", "")
    if da_dung:
        if (spec.get("theme"), spec.get("hero")) == (da_dung.get("theme"), da_dung.get("hero")):
            loi.append("LÀM LẠI: theme và hero trùng lần trước — đổi ít nhất một")
        if _chuan(hook) == _chuan(da_dung.get("hook")):
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
        import gui_telegram
        res = gui_telegram.post("carousel-edu", [str(f) for f in files],
                                f"Carousel edu {n} slide: {hook}"[:1000], duyet=a.draft_id)
        rr = res.get("result")
        mid = (rr[-1] if isinstance(rr, list) else rr or {}).get("message_id")
        cb._ghi_json(wd / "da_dung.json", {"theme": theme, "hero": hero, "hook": hook,
                                           "luc": time.strftime("%H:%M %d/%m"),
                                           "lan": int((da_dung or {}).get("lan", 0)) + 1,
                                           "message_id": mid})
    # Bang den (kanban swarm): ban giao co cau truc cua Kite len the goc + dong
    # "[metadata]" de Kite dan vao kanban_complete -> Miles/Ada thay trong
    # "Parent task results". Best-effort.
    md = {"slide": n, "hook": hook, "theme": theme, "hero": hero, "hinh_that": hinh,
          "tep": str(out), "ban_giao": str(bg_path), "message_id": mid, "vai": "kite"}
    if not a.khong_gui:
        ghi_bang_den(a.draft_id, "anh", md)
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
