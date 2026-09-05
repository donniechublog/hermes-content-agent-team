#!/usr/bin/env python3
"""Dung carousel kieu SLIDE-THIET-KE (editorial deck) — khac han Dre.

Dre (carousel.py) lam bang tin: anh o tren, chu o duoi, mot khuon duy nhat.
Deck nay lam kieu "template thiet ke": moi slide mot BO CUC rieng — cau tuyen bo
lon, badge STEP, tieu de hai tang (serif nghieng + sans dam), danh sach co ngoac,
checklist, grid anh, CTA. Dung de remake/viet lai cac carousel dang infographic.

Spec JSON: {"slides": [ {"layout": "...", ...fields}, ... ]}
Xuat ra: <out>.png (slide 1) + <out>_2.png ... <out>_N.png (khop album draft_write).

Cong chan tieng Viet giong card.py/carousel.py: mat dau bi chan tru --bo-qua-dau.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

from card import _f, _wrap, tim_mat_dau

ASSETS = Path(__file__).resolve().parent / "assets"
FONTS = ASSETS / "fonts"
F_SANS = str(FONTS / "BeVietnamPro-Bold.ttf")       # tieu de sans dam
F_SERIF = str(FONTS / "NotoSerifDisplay.ttf")       # tieu de serif nghieng
F_BODY = str(FONTS / "Inter.ttf")                   # than chu
F_COND = str(FONTS / "Oswald.ttf")                  # sans hep (badge, nhan)

W, H = 1080, 1350
PAD = 84

# Bang mau he editorial (rut tu carousel goc): den, kem, san ho, xanh.
BG_DARK = (13, 13, 13)
BG_CREAM = (236, 230, 220)
CREAM = (236, 230, 220)
WHITE = (245, 245, 245)
INK = (17, 17, 17)
CORAL = (202, 101, 71)
BLUE = (43, 104, 232)
GREY = (150, 150, 150)


# ---- helper chung ---------------------------------------------------------
def _grow(d, text, path, max_w, hi, lo=None, weight=None, italic=False):
    """Wrap text o co `hi`. Ten cu hua "co lon nhat vua max_w" nhung vong lap
    luon tra ve ngay co dau tien (_wrap luon co ket qua khi text khong rong),
    nen hanh vi that la CO DINH `hi` — giu nguyen de khong doi layout cac deck
    da xuat. `lo`/`italic` giu cho tuong thich, khong dung."""
    f = _f(path, hi, weight)
    return f, _wrap(d, text, f, max_w)


def _draw_lines(d, x, y, lines, font, fill, lead=1.16):
    b = font.getbbox("ÂgqĐ")
    lh = int((b[3] - b[1]) * lead)
    for ln in lines:
        d.text((x, y), ln, font=font, fill=fill)
        y += lh
    return y


def _line_h(font, lead=1.16):
    b = font.getbbox("ÂgqĐ")
    return int((b[3] - b[1]) * lead)


def _badge(d, x, y, text, bg=CORAL, fg=WHITE, size=30):
    """Badge kieu 'STEP 3:' — nen dac bo goc, chu hep viet hoa."""
    f = _f(F_COND, size, 600)
    tw = d.textlength(text, font=f)
    b = f.getbbox("Âg")
    th = b[3] - b[1]
    padx, pady = 20, 12
    d.rounded_rectangle([x, y, x + tw + padx * 2, y + th + pady * 2],
                        radius=8, fill=bg)
    d.text((x + padx, y + pady - b[1]), text, font=f, fill=fg)
    return y + th + pady * 2


def _two_tone_title(d, x, y, serif_text, sans_text, max_w,
                    serif_col=CORAL, sans_col=WHITE, hi=104):
    """Tieu de hai tang: dong serif nghieng o tren, dong sans dam o duoi, hoi
    chong len nhau nhu carousel goc."""
    sf, sl = _grow(d, serif_text, F_SERIF, max_w, hi, 48, italic=True)
    y = _draw_lines(d, x, y, sl, sf, serif_col, lead=1.0)
    nf, nl = _grow(d, sans_text, F_SANS, max_w, hi + 4, 48)
    y2 = _draw_lines(d, x, y - int(_line_h(sf) * 0.12), nl, nf, sans_col, lead=1.0)
    return y2


def _open_bg(layout):
    """Nen mot slide: mau phang (mac dinh) hoac ANH THAT da qua doi_chu_anh.py
    (chu tieng Anh da xoa sach). `bg_anh` la duong dan anh — dung khi remake
    mot carousel co san, giu nguyen anh nguon, chi thay chu."""
    if layout.get("bg_anh"):
        img = Image.open(layout["bg_anh"]).convert("RGB")
        scale = max(W / img.width, H / img.height)
        nw, nh = round(img.width * scale), round(img.height * scale)
        img = img.resize((nw, nh), Image.LANCZOS)
        x, y = (nw - W) // 2, (nh - H) // 2
        canvas = img.crop((x, y, x + W, y + H)).convert("RGBA")
        fg = CREAM if layout.get("fg") == "cream" else WHITE
        return canvas, fg, INK
    if layout.get("bg") == "cream":
        return Image.new("RGBA", (W, H), (*BG_CREAM, 255)), INK, CREAM
    return Image.new("RGBA", (W, H), (*BG_DARK, 255)), CREAM, INK


# ---- cac layout -----------------------------------------------------------
def lay_statement(s):
    """Cau tuyen bo lon + 1-2 dong phu. Slide dau/loi keu."""
    canvas, fg, _ = _open_bg(s)
    d = ImageDraw.Draw(canvas)
    y = int(H * 0.08)
    if s.get("badge"):
        y = _badge(d, PAD, y, s["badge"]) + 30
    y = max(y, int(H * 0.20)) if not s.get("badge") else y
    hf, hl = _grow(d, s["heading"], F_SANS, W - 2 * PAD, 96, 52)
    y = _draw_lines(d, PAD, y, hl, hf, s.get("heading_col_rgb") or fg, lead=1.12)
    y += int(_line_h(hf) * 0.5)
    for sub in s.get("subs", []):
        # "y"/"x"/"max_w" ghi de vi tri: dung khi bg_anh da co san mot khoi
        # thiet ke co dinh (vd hop trich dan mau dac) ma chu Viet phai nam
        # DUNG cho do, khong theo dong chay tu tren xuong nhu cac sub khac.
        y_ve = sub["y"] if "y" in sub else y
        x_ve = sub.get("x", PAD)
        mw = sub.get("max_w", W - x_ve - PAD)
        col = {"white": WHITE, "cream": CREAM, "coral": CORAL,
               "blue": BLUE, "grey": GREY, "den": INK}.get(sub.get("col", "white"), WHITE)
        bold = sub.get("bold", False)
        sf, sl = _grow(d, sub["text"], F_SANS if bold else F_BODY,
                       mw, sub.get("hi", 44), sub.get("lo", 30),
                       weight=None if bold else 500)
        y_sau = _draw_lines(d, x_ve, y_ve, sl, sf, col, lead=1.2)
        if "y" in sub:
            continue
        y = y_sau + int(_line_h(sf) * 0.35)
    return canvas


def lay_list_steps(s):
    """Danh sach 'Slide X: ...' co ngoac trai — kieu Value Escalation."""
    canvas, fg, _ = _open_bg(s)
    d = ImageDraw.Draw(canvas)
    y = PAD + 20
    if s.get("badge"):
        y = _badge(d, PAD, y, s["badge"]) + 30
    y = _two_tone_title(d, PAD, y, s["serif"], s["sans"], W - 2 * PAD,
                        serif_col=CORAL, sans_col=fg, hi=96)
    y += int(H * 0.03)
    rows = s["rows"]
    gap = int((H - 260 - y) / max(1, len(rows)))
    rf = _f(F_SANS, 40)
    for i, r in enumerate(rows):
        ry = y + i * gap
        # ngoac trai
        bx = PAD
        d.line([(bx, ry), (bx, ry + 60)], fill=CORAL, width=8)
        d.line([(bx, ry), (bx + 22, ry)], fill=CORAL, width=6)
        d.line([(bx, ry + 60), (bx + 22, ry + 60)], fill=CORAL, width=6)
        # gach noi
        d.line([(bx + 55, ry + 30), (bx + 95, ry + 30)], fill=CORAL, width=6)
        d.text((bx + 120, ry + 30 - rf.getbbox("Âg")[3] // 2), r,
               font=rf, fill=fg)
    # footer
    _footer_burst(d, s.get("footer"), fg)
    return canvas


def lay_checklist(s):
    """Tieu de hai mau + checklist o vuong + footer."""
    canvas, fg, _ = _open_bg(s)
    d = ImageDraw.Draw(canvas)
    y = PAD + 10
    # tieu de hai mau tren cung dong sans dam
    tf, tl = _grow(d, s["title1"] + " " + s["title2"], F_SANS, W - 2 * PAD, 100, 56)
    # ve rieng hai mau: don gian ve title1 (mau 1) roi title2 (mau 2) neu vua 1 dong
    tf2 = _f(F_SANS, tf.size)
    l1 = _wrap(d, s["title1"], tf2, W - 2 * PAD)
    y = _draw_lines(d, PAD, y, l1, tf2, fg, lead=1.02)
    l2 = _wrap(d, s["title2"], tf2, W - 2 * PAD)
    y = _draw_lines(d, PAD, y, l2, tf2, CORAL, lead=1.02)
    y += 14
    sf, sl = _grow(d, s["sub"], F_BODY, W - 2 * PAD, 40, 28, weight=600)
    y = _draw_lines(d, PAD, y, sl, sf, GREY, lead=1.2)
    y += int(H * 0.03)
    items = s["items"]
    gap = int((H - 320 - y) / max(1, len(items)))
    itf = _f(F_SANS, 38)
    for i, it in enumerate(items):
        iy = y + i * gap
        d.rounded_rectangle([PAD, iy, PAD + 42, iy + 42], radius=6,
                            outline=CORAL, width=4)
        d.text((PAD + 66, iy + 21 - itf.getbbox("Âg")[3] // 2), it,
               font=itf, fill=fg)
    _footer_two(d, s.get("footer1"), s.get("footer2"), fg)
    return canvas


def lay_grid3(s):
    """Badge + tieu de hai tang + nhan chu dat duoi cac anh nho co san TRONG
    bg_anh (grid mockup) — layout KHONG tu ve anh grid, chi dinh vi chu that
    duoi anh that. Dung khi remake slide 'STEP...' co san 2-3 anh minh hoa
    xep hang ngang, chi can doi chu, giu nguyen anh."""
    canvas, fg, _ = _open_bg(s)
    d = ImageDraw.Draw(canvas)
    y = PAD + 20
    if s.get("badge"):
        y = _badge(d, PAD, y, s["badge"]) + 30
    y = _two_tone_title(d, PAD, y, s["serif"], s["sans"], W - 2 * PAD,
                        serif_col=CORAL, sans_col=fg, hi=80)
    if s.get("sub"):
        y += int(H * 0.02)
        sf, sl = _grow(d, s["sub"], F_BODY, W - 2 * PAD, 36, 26, weight=500)
        y = _draw_lines(d, PAD, y, sl, sf, GREY, lead=1.2)
    nf = _f(F_SANS, 30)
    for nhan in s.get("nhan", []):
        tw = d.textlength(nhan["text"], font=nf)
        d.text((nhan["x"] - tw / 2, nhan["y"]), nhan["text"], font=nf, fill=fg)
    _footer_burst(d, s.get("footer"), fg)
    return canvas


def lay_cover(s):
    """Tieu de khong lo xep tang (moi dong/tier tu no rieng) de len ANH THAT
    (bg_anh) — kieu bia carousel remake. Tuy chon mot doan chu nghieng nho o
    goc, kieu ghi chu tay dinh kem. `tiers`: [[[dong,...], co_cao, co_thap], ...]
    — cac dong trong CUNG mot tier dung chung mot co (co lon nhat con vua ca
    ca tier), tier khac nhau co doc lap."""
    canvas, fg, _ = _open_bg(s)
    d = ImageDraw.Draw(canvas)
    max_w = W - 2 * PAD
    rows = []
    for lines, hi, lo in s["tiers"]:
        size = min(_fit_size(d, ln, max_w, hi, lo) for ln in lines)
        f = _f(F_SANS, size)
        b = f.getbbox("Âg")
        lh = int((b[3] - b[1]) * 0.94)
        for ln in lines:
            rows.append((ln, f, lh))
    tong_cao = sum(lh for _, _, lh in rows)
    y = (H - PAD) - tong_cao
    title_top = y
    for text, f, lh in rows:
        d.text((PAD, y), text, font=f, fill=s.get("title_col_rgb") or fg)
        y += lh

    gc = s.get("ghi_chu")
    if gc:
        gc_max_w = gc.get("max_w", 330)
        cf_size, max_cap_h = 40, max(60, title_top - 40 - 60)
        while cf_size > 22:
            cf = _f(F_SANS, cf_size)
            cap_lines = _wrap(d, gc["text"], cf, gc_max_w)
            clh = int((cf.getbbox("Âg")[3] - cf.getbbox("Âg")[1]) * 1.25)
            if clh * len(cap_lines) <= max_cap_h:
                break
            cf_size -= 2
        lop = Image.new("RGBA", (gc_max_w + 70, clh * len(cap_lines) + 40), (0, 0, 0, 0))
        dl = ImageDraw.Draw(lop)
        cy = 10
        for ln in cap_lines:
            dl.text((10, cy), ln, font=cf, fill=(255, 255, 255, 255))
            cy += clh
        if gc.get("nghieng"):
            lop = lop.rotate(gc["nghieng"], resample=Image.BICUBIC, expand=True)
        cap_y = max(60, title_top - 40 - lop.height)
        canvas.alpha_composite(lop, (gc.get("x", 640), cap_y))
    return canvas


def _fit_size(d, text, max_w, hi, lo):
    for size in range(hi, lo - 1, -2):
        if d.textlength(text, font=_f(F_SANS, size)) <= max_w:
            return size
    return lo


def _footer_burst(d, text, fg):
    if not text:
        return
    f, lines = _grow(d, text, F_SANS, W - 2 * PAD - 70, 34, 26)
    lh = _line_h(f, 1.18)
    y = H - PAD - lh * len(lines)
    # dau hoa thi burst
    _burst(d, PAD + 20, y + lh // 2, CORAL, 26)
    _draw_lines(d, PAD + 70, y, lines, f, fg, lead=1.18)


def _footer_two(d, t1, t2, fg):
    if not t1:
        return
    f1, l1 = _grow(d, t1, F_SANS, W - 2 * PAD, 44, 30)
    f2, l2 = _grow(d, t2 or "", F_SANS, W - 2 * PAD, 44, 30)
    lh = _line_h(f1, 1.14)
    total = lh * (len(l1) + len(l2))
    y = H - PAD - total
    y = _draw_lines(d, PAD, y, l1, f1, fg, lead=1.14)
    _draw_lines(d, PAD, y, l2, f2, CORAL, lead=1.14)


def _burst(d, cx, cy, col, r):
    import math
    for k in range(12):
        a = math.pi * k / 6
        d.line([(cx, cy), (cx + r * math.cos(a), cy + r * math.sin(a))],
               fill=col, width=6)


LAYOUTS = {
    "statement": lay_statement,
    "list_steps": lay_list_steps,
    "checklist": lay_checklist,
    "grid3": lay_grid3,
    "cover": lay_cover,
}


def _gate(slides, bo_qua_dau):
    if bo_qua_dau:
        return []
    loi = []
    for i, s in enumerate(slides, 1):
        blob = " ".join(str(v) for k, v in s.items()
                        if isinstance(v, str) and k not in ("layout", "bg", "badge"))
        for r in s.get("rows", []) + s.get("items", []):
            blob += " " + r
        for sub in s.get("subs", []):
            blob += " " + sub.get("text", "")
        for nhan in s.get("nhan", []):
            blob += " " + nhan.get("text", "")
        for lines, _hi, _lo in s.get("tiers", []):
            blob += " " + " ".join(lines)
        if s.get("ghi_chu"):
            blob += " " + s["ghi_chu"].get("text", "")
        mat = tim_mat_dau(blob)
        if mat:
            loi.append(f"slide {i}: tieng Viet mat dau ({', '.join(mat)})")
    return loi


def main():
    ap = argparse.ArgumentParser(description="Dung carousel slide-thiet-ke")
    ap.add_argument("--spec", required=True, help="JSON spec, hoac '-' tu stdin")
    ap.add_argument("--out", required=True, help="drafts/<id>.png")
    ap.add_argument("--bo-qua-dau", action="store_true")
    a = ap.parse_args()

    raw = sys.stdin.read() if a.spec == "-" else Path(a.spec).read_text("utf-8")
    spec = json.loads(raw)
    slides = spec.get("slides") or []
    if not slides:
        sys.exit("Spec khong co slide nao.")
    if len(slides) > 10:
        sys.exit(f"Qua nhieu slide ({len(slides)}). Toi da 10 (album _[0-9]).")

    loi = _gate(slides, a.bo_qua_dau)
    if loi:
        for e in loi:
            print(f"[LOI] {e}", file=sys.stderr)
        sys.exit("Chu carousel mat dau tieng Viet. Go lai co dau hoac --bo-qua-dau.")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    stem = out.with_suffix("")
    paths = []
    for i, s in enumerate(slides, 1):
        fn = LAYOUTS.get(s.get("layout"))
        if not fn:
            sys.exit(f"slide {i}: layout khong ho tro: {s.get('layout')}")
        canvas = fn(s)
        p = str(out) if i == 1 else f"{stem}_{i}.png"
        canvas.convert("RGB").save(p, "PNG")
        paths.append(p)
    print(f"da dung {len(paths)} slide:")
    for p in paths:
        print("  " + p)


if __name__ == "__main__":
    main()
