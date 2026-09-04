#!/usr/bin/env python3
"""itachi_nop.py — NỘP của Itachi: vẽ chữ Việt tại chỗ (thay ve_chu_thay_the.py
đã mất) hoặc dựng deck.py theo spec, cổng chặn tiếng Việt, gửi album trả lời
đúng tin nhắn.

Vẽ tại chỗ: mỗi vùng OCR gốc (x,y,w,h, màu đo được) nhận bản dịch; chọn cỡ chữ
lớn nhất còn vừa bề ngang và chiều cao box (tối thiểu 16px), font theo chiều
cao (≥4.5% ảnh → bold, không thì regular) trừ khi spec ghi `font`; `gop`
[a, b, text] gộp dải vùng a..b thành một khối, wrap nhiều dòng trong khối đó.

Dùng:
    venv/bin/python itachi_nop.py 338              # spec ở state/<brand>/chuan_bi/itachi_338/spec.json
    venv/bin/python itachi_nop.py 338 --khong-gui  # thử
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import gin_chuan_bi as gb                                    # noqa: E402
from card import _f, _wrap, tim_mat_dau, bo_dau_cam          # noqa: E402

FONTS = ROOT / "assets" / "fonts"
FONT = {"bold": FONTS / "BeVietnamPro-Bold.ttf", "regular": FONTS / "BeVietnamPro-Regular.ttf",
        "serif": FONTS / "NotoSerifDisplay.ttf", "condensed": FONTS / "Oswald.ttf",
        "mono": FONTS / "JetBrainsMono-Bold.ttf"}
CO_MIN = 16


def _font_mac_dinh(h_vung: int, h_anh: int) -> str:
    return "bold" if h_vung >= 0.045 * h_anh else "regular"


def _ve_khoi(d: ImageDraw.ImageDraw, text: str, x: int, y: int, w: int, h: int, font_key: str,
             color, align: str) -> None:
    path = str(FONT.get(font_key) or FONT["regular"])
    size = max(CO_MIN, int(h * 0.82))
    while size > CO_MIN:
        f = _f(path, size)
        lines = _wrap(d, text, f, w)
        lh = int((f.getbbox("ÂgqĐ")[3] - f.getbbox("ÂgqĐ")[1]) * 1.12)
        if lh * len(lines) <= h * 1.05:
            break
        size -= 2
    f = _f(path, size)
    lines = _wrap(d, text, f, w)
    lh = int((f.getbbox("ÂgqĐ")[3] - f.getbbox("ÂgqĐ")[1]) * 1.12)
    yy = y + max(0, (h - lh * len(lines)) // 2)
    for ln in lines:
        tw = d.textlength(ln, font=f)
        xx = x + (w - tw) / 2 if align == "center" else x
        d.text((xx, yy), ln, font=f, fill=tuple(color))
        yy += lh


def ve_tai_cho(s: dict, muc: dict, out: Path, bo_qua_dau: bool) -> list:
    """Trả về danh sách lỗi (rỗng = đã vẽ xong ra `out`)."""
    loi = []
    vung = {str(v["stt"]): v for v in s["vung"]}
    im = Image.open(s["nen_sach"]).convert("RGB")
    d = ImageDraw.Draw(im)
    da_dung = set()
    khoi = []
    for g in muc.get("gop") or []:
        try:
            a, b, text = int(g[0]), int(g[1]), str(g[2])
        except (TypeError, ValueError, IndexError):
            loi.append(f"slide {s['id']}: gop phải là [stt_đầu, stt_cuối, \"bản dịch\"]")
            continue
        ds = [vung[str(k)] for k in range(a, b + 1) if str(k) in vung]
        if not ds:
            loi.append(f"slide {s['id']}: gop {a}..{b} không có vùng nào")
            continue
        x0, y0 = min(v["x"] for v in ds), min(v["y"] for v in ds)
        x1, y1 = max(v["x"] + v["w"] for v in ds), max(v["y"] + v["h"] for v in ds)
        khoi.append({"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0, "text": text,
                     "color_rgb": ds[0]["color_rgb"], "font": None, "align": "left",
                     "h_dong": max(v["h"] for v in ds)})
        da_dung.update(str(v["stt"]) for v in ds)
    for k, val in (muc.get("vung") or {}).items():
        if k in da_dung or val is None:
            continue
        v = vung.get(str(k))
        if not v:
            loi.append(f"slide {s['id']}: vùng {k} không tồn tại (có: {', '.join(vung)})")
            continue
        if isinstance(val, str):
            val = {"text": val}
        text = str(val.get("text") or "").strip()
        if not text:
            continue
        khoi.append({"x": v["x"], "y": v["y"], "w": v["w"], "h": v["h"], "text": text,
                     "color_rgb": val.get("color_rgb") or v["color_rgb"], "font": val.get("font"),
                     "align": val.get("align") or "left", "h_dong": v["h"]})
    if not khoi and not loi:
        loi.append(f"slide {s['id']}: tai_cho nhưng không có vùng nào được dịch")
    for kh in khoi:
        kh["text"] = bo_dau_cam(kh["text"])
        if not bo_qua_dau and tim_mat_dau(kh["text"]):
            loi.append(f"slide {s['id']}: tiếng Việt mất dấu: {kh['text'][:50]!r}")
    if loi:
        return loi
    for kh in khoi:
        _ve_khoi(d, kh["text"], kh["x"], kh["y"], kh["w"], kh["h"],
                 kh["font"] or _font_mac_dinh(kh["h_dong"], s["h"]), kh["color_rgb"], kh["align"])
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PNG")
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description="Nộp remake carousel của Itachi")
    ap.add_argument("khoa", help="id slide đầu (khoá bộ, đã chạy itachi_chuan_bi.py)")
    ap.add_argument("--khong-gui", action="store_true")
    ap.add_argument("--bo-qua-dau", action="store_true")
    a = ap.parse_args()
    wd = gb.workdir("itachi", a.khoa)
    if not (wd / "xong.json").exists():
        sys.exit(f"Chưa chuẩn bị. Chạy trước: venv/bin/python itachi_chuan_bi.py {a.khoa}")
    m = json.loads((wd / "xong.json").read_text(encoding="utf-8"))
    slides = {s["id"]: s for s in m["slides"]}
    if not (wd / "spec.json").exists():
        sys.exit(f"Chưa có spec: {wd / 'spec.json'} — viết theo brief ({wd / 'brief.md'}) rồi chạy lại.")
    try:
        spec = json.loads((wd / "spec.json").read_text(encoding="utf-8"))
    except Exception as e:                                   # noqa: BLE001
        sys.exit(f"[LOI] spec.json không phải JSON hợp lệ: {type(e).__name__}: {e}")

    loi, files, deck_slides, deck_idx = [], [], [], []
    for i, muc in enumerate(spec.get("slides") or [], 1):
        sid = str(muc.get("nguon") or "")
        s = slides.get(sid)
        if not s:
            loi.append(f"mục {i}: nguon {sid!r} không có trong bộ (có: {', '.join(slides)})")
            continue
        cach = (muc.get("cach") or "tai_cho").lower()
        out = wd / (f"ket_qua_{sid}.png")
        if cach == "tai_cho":
            loi += ve_tai_cho(s, muc, out, a.bo_qua_dau)
            files.append(out)
        elif cach == "deck":
            ds = {k: v for k, v in muc.items() if k not in ("nguon", "cach", "bg_anh")}
            if muc.get("bg_anh"):
                ds["bg_anh"] = s["nen_sach"]
            if ds.get("layout") not in ("statement", "list_steps", "checklist", "grid3", "cover"):
                loi.append(f"mục {i}: layout {ds.get('layout')!r} không hợp lệ")
            deck_slides.append(ds)
            deck_idx.append(out)
            files.append(out)
        else:
            loi.append(f"mục {i}: cach phải là \"tai_cho\" hoặc \"deck\"")
    if not files and not loi:
        loi.append("spec không có slide nào")
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        print(f"\nSửa {wd / 'spec.json'} rồi chạy lại: venv/bin/python itachi_nop.py {a.khoa}")
        return 1
    if deck_slides:
        p_spec = wd / "deck.spec.json"
        p_spec.write_text(json.dumps({"slides": deck_slides}, ensure_ascii=False, indent=1), encoding="utf-8")
        stem = wd / "deck"
        r = subprocess.run([sys.executable, str(ROOT / "deck.py"), "--spec", str(p_spec), "--out", f"{stem}.png"]
                           + (["--bo-qua-dau"] if a.bo_qua_dau else []),
                           cwd=str(ROOT), capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            for d in ((r.stderr or "") + "\n" + (r.stdout or "")).strip().splitlines()[-8:]:
                print(f"[LOI] {d}")
            print(f"\nSửa {wd / 'spec.json'} rồi chạy lại: venv/bin/python itachi_nop.py {a.khoa}")
            return 1
        ra = [Path(f"{stem}.png")] + [Path(f"{stem}_{k}.png") for k in range(2, len(deck_slides) + 1)]
        for src, dst in zip(ra, deck_idx):
            src.replace(dst)
    thieu = [str(f) for f in files if not f.exists()]
    if thieu:
        sys.exit(f"[LOI] thiếu tệp kết quả: {thieu}")
    mo_ta = f"Remake {len(files)} slide tiếng Việt (bộ {a.khoa})"
    mid = None
    if a.khong_gui:
        print(f"[thu] không gửi. {[str(f) for f in files]}")
    else:
        import gui_telegram
        reply = int(a.khoa) if str(a.khoa).isdigit() else None
        res = gui_telegram.post("itachi", [str(f) for f in files], mo_ta, reply_to=reply)
        rr = res.get("result")
        mid = (rr[-1] if isinstance(rr, list) else rr or {}).get("message_id")
    print(f"[xong] {len(files)} slide -> {wd}" + (f"; đã gửi topic itachi (message_id={mid})" if mid else ""))
    print(f"Kết quả (trả lời Ông Chủ đúng một câu): Đã dựng {len(files)} slide tiếng Việt cho bộ {a.khoa}, "
          "album đã gửi trong topic.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
