#!/usr/bin/env python3
"""Dung carousel nhieu slide kieu bang tin — anh o tren, khoi chu trang tren
nen den o duoi, watermark nghieng o day. Khac han card.py (mot the bia kieu
tran): day la mot bo N slide ke chuyen, dung cho Heller.

Bo cuc moi slide (1080x1350, ti le 4:5, nen den):

  Slide bia (slide 1):
    - Anh phu kin the (cover), man toi day dan o nua duoi.
    - Cau hook chu dam trang, canh trai, nam sat day.
    - Nhan ngan (kicker) o duoi hook.

  Slide than (slide 2..N):
    - Anh full be ngang, giu nguyen ti le (contain), canh day vung anh.
      Anh ngan/ngang thi de lo nen den o tren — dung, khong phong to.
    - Khoi chu trang canh trai o duoi, tach doan theo dong trong.
    - Watermark nghieng canh giua o day.

Xuat ra: <out>.png (bia), <out>_2.png, <out>_3.png ... <out>_N.png
Danh so nay khop dung glob cua draft_write.py (<id>.png + <id>_[0-9].png),
nen bo slide tu dong thanh album khi dang.

Nhap:
  --spec spec.json   (xem cau truc ben duoi)  hoac  --spec -  doc tu stdin

  {
    "handle": "donniechublog",           # watermark; mac dinh theo --handle/--brand
    "cover":  {"image": "...", "hook": "cau giat tit", "label": "AI"},
    "slides": [
      {"image": "...", "text": "doan 1\\n\\ndoan 2"},
      ...
    ]
  }

Cong chan giong card.py: tieng Viet mat dau bi chan (tru --bo-qua-dau), em-dash
tu thay bang dau phay.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw

# Tai dung nguyen xi cac helper da kiem chung cua card.py thay vi viet lai:
# nap font co truc bien thien, wrap chu, contain/cover anh, cong chan tieng Viet.
import card
from card import (
    _f, _wrap, _fit_contain, _fit_cover,
    tim_mat_dau, bo_dau_cam, dat_thuong_hieu, THUONG_HIEU,
    F_REG,                       # Inter — sans khong chan, doc ra "bao" khong ra "code"
)

# ---- Khung so -------------------------------------------------------------
W, H = 1080, 1350                # kho dang chuan Instagram/Facebook 4:5
PAD = 84                         # le trai/phai cua chu, do tu mau tham chieu
BG = (0, 0, 0)                   # den tuyet doi — dau an cua kieu carousel nay
FG = (255, 255, 255)            # chu chinh trang
WM = (150, 150, 150)            # watermark mo

# Vung anh cua slide than. Anh bam MEP TREN va HAI CANH (full be ngang), day
# anh TAN dan vao nen den — khong co duong ngang chia "vung anh" voi "vung chu".
# Ca the la mot mat phang den lien: anh o tren, tan vao den, chu nam tren den do.
# Tuyet doi khong ve vien, vach, hay khung — cai lam hai vung tach roi.
IMG_REGION_H = 800               # anh chiem tu mep tren xuong toi da day nay
IMG_FADE = 190                   # day anh tan vao den trong chung nay px
TEXT_TOP = 848                   # chu bat dau, nam tren phan da den han
TEXT_BOTTOM = 1240               # chua chu qua day nay (chua cho watermark)

# Chu than: thu tu co lon nhat con vua ca chieu cao, giong tinh than _grow cua card.
BODY_HI, BODY_LO = 50, 34
BODY_LEAD = 1.28                 # gian dong trong mot doan
PARA_GAP = 0.7                   # khoang giua hai doan, theo don vi chieu cao dong

# Hook o bia: chu dam, to, tu co theo do dai cau.
HOOK_HI, HOOK_LO = 76, 46
HOOK_LEAD = 1.12
HOOK_WEIGHT = 700

WM_SIZE = 30                     # watermark
LABEL_SIZE = 34                  # nhan duoi hook o bia


# ---- Ve chu ---------------------------------------------------------------
def _line_h(font, lead):
    """Chieu cao mot dong theo bbox chu co dau, nhan he so gian dong."""
    b = font.getbbox("ÂgqÁ")
    return int((b[3] - b[1]) * lead)


def _fit_block(d, paragraphs, max_w, max_h, hi, lo, weight=None, lead=BODY_LEAD):
    """Chon co chu lon nhat de CA khoi (nhieu doan) con vua max_h.

    Tra ve (font, [(lines, line_h)], tong_cao). Qua nho van tra ve co lo.
    """
    for size in range(hi, lo - 1, -2):
        f = _f(F_REG, size, weight)
        lh = _line_h(f, lead)
        wrapped = [_wrap(d, p, f, max_w) for p in paragraphs]
        n_lines = sum(len(w) for w in wrapped)
        gap = int(lh * PARA_GAP) * max(0, len(paragraphs) - 1)
        total = n_lines * lh + gap
        if total <= max_h:
            return f, wrapped, lh, total
    f = _f(F_REG, lo, weight)
    lh = _line_h(f, lead)
    wrapped = [_wrap(d, p, f, max_w) for p in paragraphs]
    return f, wrapped, lh, sum(len(w) for w in wrapped) * lh


def _draw_paragraphs(d, x, y, wrapped, font, lh, fill):
    """Ve lan luot cac doan tu (x, y) xuong. Tra ve y sau khi ve xong."""
    gap = int(lh * PARA_GAP)
    for pi, lines in enumerate(wrapped):
        for ln in lines:
            d.text((x, y), ln, font=font, fill=fill)
            y += lh
        if pi != len(wrapped) - 1:
            y += gap
    return y


def _watermark(canvas, handle):
    """Ve watermark nghieng, canh giua o day. Khong co font italic rieng nen
    ve len lop phu roi nghieng bang bien doi affine (shear)."""
    if not handle:
        return
    font = _f(F_REG, WM_SIZE, 500)
    d0 = ImageDraw.Draw(canvas)
    tw = int(d0.textlength(handle, font=font))
    b = font.getbbox("Âg")
    th = b[3] - b[1]
    pad = th                                    # dem cho phan nghieng khong bi cat
    lop = Image.new("RGBA", (tw + pad * 2, th + pad), (0, 0, 0, 0))
    ImageDraw.Draw(lop).text((pad, 0), handle, font=font, fill=(*WM, 255))
    shear = 0.20                                # do nghieng gia italic
    lop = lop.transform(
        lop.size, Image.AFFINE, (1, shear, -shear * th, 0, 1, 0),
        resample=Image.BICUBIC)
    x = (W - lop.width) // 2
    y = H - 66 - th // 2
    canvas.alpha_composite(lop, (x, y))


def _scrim(canvas, tu=0.42):
    """Man toi day dan cho slide bia: trong o tren, dam dan xuong day de chu
    hook doc ro. `tu` la moc bat dau lam toi (theo ti le chieu cao)."""
    man = Image.new("L", (1, H), 0)
    y0 = int(H * tu)
    for y in range(y0, H):
        t = (y - y0) / max(1, H - y0)
        man.putpixel((0, y), int(235 * t ** 1.4))
    lop = Image.new("RGBA", (W, H), (*BG, 0))
    lop.putalpha(man.resize((W, H)))
    canvas.alpha_composite(lop)


# ---- Anh ------------------------------------------------------------------
def _open(path):
    img = Image.open(path).convert("RGB")
    return img


def _fade_to_black(canvas, y_top, y_bot):
    """Phu mot lop den tang dan tu trong (y_top) sang dac (y_bot tro xuong).
    Duoi y_bot den han. Nho lop nay day anh KHONG lo ra mot canh cung, ma tan
    vao nen — anh va vung chu doc ra mot mat lien."""
    grad = Image.new("L", (1, H), 0)
    for y in range(H):
        if y <= y_top:
            a = 0
        elif y >= y_bot:
            a = 255
        else:
            t = (y - y_top) / max(1, y_bot - y_top)
            a = int(255 * t ** 1.35)
        grad.putpixel((0, y), a)
    lop = Image.new("RGBA", (W, H), (*BG, 0))
    lop.putalpha(grad.resize((W, H)))
    canvas.alpha_composite(lop)


def _body_image(canvas, img):
    """Slide than: anh full be ngang, bam mep tren + hai canh, day tan vao den.

    Anh cao hon vung thi cat bot theo chieu doc (giu giua), khong bao gio de lo
    hai canh ben — cat ngang la mat noi dung, va vien den hai ben lam anh nhin
    nhu mot cai hop rieng. Anh thap hon vung thi nen den lo o duoi, van tan muot
    nen khong lo duong ngang nao."""
    scale = W / img.width
    nh = round(img.height * scale)
    resized = img.resize((W, nh), Image.LANCZOS)
    if nh >= IMG_REGION_H:
        top = (nh - IMG_REGION_H) // 2            # cat giua theo chieu doc
        canvas.paste(resized.crop((0, top, W, top + IMG_REGION_H)), (0, 0))
        day = IMG_REGION_H
    else:
        canvas.paste(resized, (0, 0))
        day = nh
    _fade_to_black(canvas, day - IMG_FADE, day)


# ---- Dung tung slide ------------------------------------------------------
def build_body(img_path, text, handle, out):
    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    _body_image(canvas, _open(img_path))
    d = ImageDraw.Draw(canvas)
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    font, wrapped, lh, _ = _fit_block(
        d, paras, W - 2 * PAD, TEXT_BOTTOM - TEXT_TOP, BODY_HI, BODY_LO)
    _draw_paragraphs(d, PAD, TEXT_TOP, wrapped, font, lh, FG)
    _watermark(canvas, handle)
    canvas.convert("RGB").save(out, "PNG")


def build_cover(img_path, hook, label, out):
    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    cover = _fit_cover(_open(img_path), W, H)
    canvas.paste(cover.convert("RGB"), (0, 0))
    _scrim(canvas)
    d = ImageDraw.Draw(canvas)
    # Nhan nho o duoi cung; hook nam ngay tren nhan.
    label = (label or "").strip()
    y_label = None
    if label:
        lf = _f(F_REG, LABEL_SIZE, 600)
        lb = lf.getbbox("Âg")
        y_label = H - 96 - (lb[3] - lb[1])
    hook_bottom = (y_label - 28) if y_label else (H - 96)
    hf, wrapped, lh, total = _fit_block(
        d, [hook], W - 2 * PAD, int(H * 0.5), HOOK_HI, HOOK_LO,
        weight=HOOK_WEIGHT, lead=HOOK_LEAD)
    y = hook_bottom - total
    _draw_paragraphs(d, PAD, y, wrapped, hf, lh, FG)
    if label:
        d.text((PAD, y_label), label, font=lf, fill=(220, 220, 220))
    canvas.convert("RGB").save(out, "PNG")


# ---- Cong chan tieng Viet -------------------------------------------------
def _gate_text(chunks, bo_qua_dau):
    """Chan tieng Viet mat dau tren toan bo chu cua carousel (giong cong 1 cua
    card.py). Tra ve danh sach loi; rong la sach."""
    loi = []
    if bo_qua_dau:
        return loi
    for nhan, t in chunks:
        mat = tim_mat_dau(t)
        if mat:
            loi.append(f"{nhan}: tieng Viet mat dau ({', '.join(mat)})")
    return loi


def main():
    ap = argparse.ArgumentParser(description="Dung carousel nhieu slide (Heller)")
    ap.add_argument("--spec", required=True,
                    help="File JSON mo ta carousel, hoac '-' doc tu stdin")
    ap.add_argument("--out", required=True,
                    help="Duong dan slide bia, vi du drafts/<id>.png. "
                         "Cac slide sau la <id>_2.png, _3.png ...")
    ap.add_argument("--brand", default="donniechublog",
                    help="donniechublog | dcgr — quyet dinh handle mac dinh")
    ap.add_argument("--handle", help="Ghi de watermark (mac dinh lay theo brand)")
    ap.add_argument("--bo-qua-dau", action="store_true",
                    help="Tat cong chan tieng Viet (chi khi chu THAT SU la tieng Anh)")
    a = ap.parse_args()

    raw = sys.stdin.read() if a.spec == "-" else Path(a.spec).read_text("utf-8")
    spec = json.loads(raw)

    if a.brand not in THUONG_HIEU:
        sys.exit(f"Thuong hieu khong nhan ra: {a.brand}")
    b = dat_thuong_hieu(a.brand)
    handle = a.handle or spec.get("handle") or b["handle"]

    cover = spec.get("cover") or {}
    slides = spec.get("slides") or []
    if not cover.get("image") or not cover.get("hook"):
        sys.exit("Thieu cover.image hoac cover.hook trong spec.")
    if not slides:
        sys.exit("Carousel can it nhat mot slide than trong 'slides'.")
    if len(slides) + 1 > 10:
        sys.exit(f"Qua nhieu slide ({len(slides)+1}). draft_write gom toi _9, "
                 "toi da 10 slide ke ca bia.")

    # Chuan hoa em-dash + chan tieng Viet mat dau truoc khi ve bat cu gi.
    cover["hook"] = bo_dau_cam(cover["hook"])
    cover["label"] = bo_dau_cam(cover.get("label", ""))
    chunks = [("bia/hook", cover["hook"])]
    for i, s in enumerate(slides, start=2):
        if not s.get("image") or not s.get("text"):
            sys.exit(f"Slide {i} thieu image hoac text.")
        s["text"] = bo_dau_cam(s["text"])
        chunks.append((f"slide {i}", s["text"]))
    loi = _gate_text(chunks, a.bo_qua_dau)
    if loi:
        for e in loi:
            print(f"[LOI] {e}", file=sys.stderr)
        sys.exit("Chu carousel khong dat cong chan tieng Viet. Go lai co dau, "
                 "hoac --bo-qua-dau neu that su la tieng Anh.")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    stem = out.with_suffix("")            # bo .png de ghep hau to _2, _3

    build_cover(cover["image"], cover["hook"], cover.get("label", ""), str(out))
    paths = [str(out)]
    for i, s in enumerate(slides, start=2):
        p = f"{stem}_{i}.png"
        build_body(s["image"], s["text"], handle, p)
        paths.append(p)

    print(f"da dung {len(paths)} slide:")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
