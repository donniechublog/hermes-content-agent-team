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

from PIL import Image, ImageDraw, ImageFilter

# Tai dung nguyen xi cac helper da kiem chung cua card.py thay vi viet lai:
# nap font co truc bien thien, wrap chu, contain/cover anh, cong chan tieng Viet.
import card
from card import (
    _f, _wrap, _fit_contain, _fit_cover,
    tim_mat_dau, bo_dau_cam, dat_thuong_hieu, THUONG_HIEU,
    F_REG,                       # Inter — sans khong chan, doc ra "bao" khong ra "code"
    _tach_nhan, _mau_cua_hang,    # nhan dien + mau that cua hang duoc nhac trong bai
)

# ---- Khung so -------------------------------------------------------------
W, H = 1080, 1350                # kho dang chuan Instagram/Facebook 4:5
PAD = 84                         # le trai/phai cua chu, do tu mau tham chieu
BG = (0, 0, 0)                   # den tuyet doi — dau an cua kieu carousel nay
FG = (255, 255, 255)            # chu chinh trang
WM = (150, 150, 150)            # watermark mo

# NEN CHO CHU O SLIDE THAN — rang buoc Ong Chu chot (ap cho MOI vai tao hinh):
#  (1) TREN dong chu dau: KHONG co lop nen — anh SACH. Lop nen KHONG BAO GIO
#      cao hon dong chu dau.
#  (2) NGAY TAI dong chu dau: lop nen gan nhu TRONG SUOT — dong chu dau HOA vao
#      main image, khong bi ngan cach.
#  (3) Cang XUONG cang DAM DAN len — mot fade DEU tu nhat toi dam, khong thô.
#      Vung dam NHAT chi ~60% opacity: anh luon con hien >=40%, khong bao gio
#      thanh mot mang nen nang. Cham 60% quanh dong chu cuoi roi giu.
BLUR_RADIUS = 14                 # mo NHE thoi — du diu chi tiet sau chu, khong lam nen "tho"/duc
MAX_TOI = 153                    # do toi TOI DA = 60% opacity (153/255). Anh con hien 40% cho ca o dam nhat
VEIL_EASE = 1.15                 # gan tuyen tinh: fade DEU tu nhat (dong dau) toi dam, khong dam giat
TEXT_BASE = 1230                 # day khoi chu, chua ~40px toi watermark
TEXT_MAX_H = 200                 # tran khoi chu: giu dinh chu >=1030 -> vung nen <=24% (<30%)
FULL_TOI_PAD = 40                # cham 60% truoc day khoi chu chung nay px (dong cuoi nam tren nen dam nhat)

# Chu than: thu tu co lon nhat con vua ca chieu cao, giong tinh than _grow cua card.
# BODY_LO ha xuong 28 de copy dai van vua vung nen 30% (ma khong tran); copy
# ngan van len toi BODY_HI.
BODY_HI, BODY_LO = 46, 28
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


def _watermark(canvas, handle, mau=None):
    """Ve watermark thang (khong nghieng), canh giua o day.

    `mau`: mau hang duoc nhac toi trong bai, da hoi toi (xem WM_MO) de la chi
    tiet PHU chu khong canh tranh voi chu chinh. None thi ve mau WM mac dinh
    (xam mo) — khong nhan ra thuong hieu nao trong bai."""
    if not handle:
        return
    font = _f(F_REG, WM_SIZE, 500)
    d = ImageDraw.Draw(canvas)
    tw = d.textlength(handle, font=font)
    b = font.getbbox("Âg")
    th = b[3] - b[1]
    x = (W - tw) / 2
    y = H - 66 - th // 2 - b[1]
    d.text((x, y), handle, font=font, fill=mau or WM)


def _scrim(canvas, tu=0.34):
    """Man toi day dan cho slide bia: trong o tren, dam dan xuong day de chu
    hook doc ro. `tu` la moc bat dau lam toi (theo ti le chieu cao).

    Truoc day tu=0.42, mu 1.4: voi hook 2 dong (truong hop ly tuong theo
    skill Heller) thi du toi, nhung hook 3 dong — van hop le, chi la cau dai
    hon — day dong dau len cao toi vung con nhat (~34% do toi o do). Da do
    that tren anh nen phuc tap (nhieu mau, chu san co): dong tren cua hook
    bi lo nen phia sau. Ha moc bat dau va giam mu (bot "day" ve cuoi) de toi
    som va deu hon ma khong doi tran do toi o sat day (van ra 235 tai y=H).
    """
    man = Image.new("L", (1, H), 0)
    y0 = int(H * tu)
    for y in range(y0, H):
        t = (y - y0) / max(1, H - y0)
        man.putpixel((0, y), int(235 * t ** 1.15))
    lop = Image.new("RGBA", (W, H), (*BG, 0))
    lop.putalpha(man.resize((W, H)))
    canvas.alpha_composite(lop)


# ---- Anh ------------------------------------------------------------------
def _open(path):
    img = Image.open(path).convert("RGB")
    return img


def _ramp_mask(top_y, full_y, hi=255, ease=1.4):
    """Mat na chieu doc: 0 tren `top_y`, tang dan (ease t^) len `hi` tai
    `full_y`, giu `hi` ben duoi. Dung chung cho ca lop mo lan lop toi nen
    hai lop chay cung mot nhip, khong lech."""
    m = Image.new("L", (1, H), 0)
    for y in range(H):
        if y <= top_y:
            a = 0
        elif y >= full_y:
            a = hi
        else:
            t = (y - top_y) / max(1, full_y - top_y)
            a = hi * t ** ease
        m.putpixel((0, y), min(255, int(a)))
    return m.resize((W, H))


def _veil_bottom(canvas, veil_rgb, text_top):
    """Lam NEN CHO CHU sao cho DONG CHU DAU hoa vao anh, KHONG bi ngan cach:

      - TREN `text_top`: mat na = 0. Anh sach hoan toan. Lop nen khong bao gio
        cao hon dong chu dau.
      - TAI `text_top`: mat na ~0 (gan nhu trong suot) — dong dau lien voi anh.
      - Cang xuong cang dam (ease VEIL_EASE > 1: giu trong suot lau o tren roi
        dam nhanh dan), cham gan-max tai `full_y` (~dong cuoi) roi giu xuong day.

    Ca lop mo lan lop toi dung cung mot mat na nay -> dong dau vua trong vua
    net (lien anh), dong cuoi vua toi vua mo (chu bat ro). Van la ANH LAM MO
    chu khong phai mau den dat vao (MAX_TOI<255): khong o den chet.

    `veil_rgb` la ban COVER phu kin khung; bi lam mo manh nen cat/phong to (do
    cover) khong lo ra."""
    top_y = text_top                              # bat dau NGAY o dong chu dau, tren do = 0
    full_y = TEXT_BASE - FULL_TOI_PAD             # cham gan-max quanh dong chu cuoi
    blurred = veil_rgb.filter(ImageFilter.GaussianBlur(BLUR_RADIUS))
    # 1) tron dan sang ban mo — trong tai dong dau, mo dan xuong
    canvas.paste(blurred, (0, 0), _ramp_mask(top_y, full_y, hi=255, ease=VEIL_EASE))
    # 2) phu lop toi tang dan — trong tai dong dau, gan-max o dong cuoi
    lop = Image.new("RGB", (W, H), BG)
    canvas.paste(lop, (0, 0), _ramp_mask(top_y, full_y, hi=MAX_TOI, ease=VEIL_EASE))


def _body_image(canvas, img):
    """Phu anh len canvas, KHONG cho nao la nen den tro:

      - NEN: ban COVER phu kin khung truoc (0..H) -> duoi day anh sac cung la
        anh (cropped), khong phai mau den. Nho vay veil nhat o tren van khong
        lo mot dai den nao.
      - LOP SAC len tren: full be ngang, KHONG cat hai canh -> giu tron chi
        tiet mep (chup man hinh, bang so khong bi cat chu). Anh 4:5 phu kin
        luon; anh 1:1 phu 0..~1080, phan duoi la nen cover (nam duoi chu +
        watermark, da bi veil lam mo).

    Tra ve ban COVER de _veil_bottom dung lam nguon ban mo. (Luat: anh dua vao
    carousel da la 1:1 hoac 4:5 — xem crop_ti_le.py; nen luon cham du sau.)"""
    cover = _fit_cover(img, W, H).convert("RGB")
    canvas.paste(cover, (0, 0))                   # nen phu kin, khong cho nao den
    scale = W / img.width
    nh = round(img.height * scale)
    resized = img.resize((W, nh), Image.LANCZOS)
    if nh > H:                                    # cao hon khung: cat giua doc, full be ngang
        top = (nh - H) // 2
        resized = resized.crop((0, top, W, top + H))
    canvas.paste(resized, (0, 0))                 # lop sac uncropped len tren nen cover
    return cover


# ---- Dung tung slide ------------------------------------------------------
def build_body(img_path, text, handle, out, mau_watermark=None):
    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    base = _body_image(canvas, _open(img_path))

    # Do khoi chu TRUOC (tran 30%), NEO TU DUOI: mep duoi luon o TEXT_BASE, chu
    # cao bao nhieu day len bay nhieu — luon sat day, khong tran len qua 30%,
    # anh cao/thap khong keo vi tri chu. Copy dai thi _fit_block co chu nho lai
    # cho vua TEXT_MAX_H (van trong 30%).
    d = ImageDraw.Draw(canvas)
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    font, wrapped, lh, total = _fit_block(
        d, paras, W - 2 * PAD, TEXT_MAX_H, BODY_HI, BODY_LO)
    text_top = TEXT_BASE - total

    # Lop nen neo vao dong chu dau: gan-max ngay tu dong chu dau tro xuong (anh
    # con <10%, chu bat ro), doan chuyen mo dan chi ngay tren dong chu dau.
    _veil_bottom(canvas, base, text_top)

    _draw_paragraphs(d, PAD, text_top, wrapped, font, lh, FG)
    _watermark(canvas, handle, mau_watermark)
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


# ---- Mau watermark theo thuong hieu duoc nhac toi -------------------------
WM_MO = 0.55                     # do mo cua mau hang o watermark, so voi mau goc

def _dinh_mau_watermark(chunks):
    """Do qua tung doan chu THEO THU TU (bia/hook truoc, roi cac slide) tim
    thuong hieu DAU TIEN duoc nhac toi — dung lai dung bang MAU_HANG/logic
    nhan dien cua card.py (da co san, dung chung cho ten hang to trong tieu
    de the tin) thay vi tu lam mot bang mau moi.

    Watermark la chi tiet PHU — khong duoc canh tranh voi chu chinh (trang,
    sang toi da). Keo mau hang ve toi (nhan WM_MO, KHONG qua _du_sang — ham
    do keo SANG len de lam chu to/dam doc ro, nguoc huong voi y muon "mo hon"
    o day) truoc khi tra ve, mo tuong tu muc mac dinh (150,150,150 tren nen
    trang 255,255,255 ~ 0.59) chu khong ve nguyen mau goc.

    Tra ve None neu khong nhan ra hang nao — watermark khi do ve mau WM
    mac dinh (xam mo)."""
    for _nhan, text in chunks:
        for _tu, khoa in _tach_nhan(text):
            if khoa:
                mau = _mau_cua_hang(khoa)
                if mau:
                    return tuple(round(c * WM_MO) for c in mau)
    return None


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

    mau_wm = _dinh_mau_watermark(chunks)

    build_cover(cover["image"], cover["hook"], cover.get("label", ""), str(out))
    paths = [str(out)]
    for i, s in enumerate(slides, start=2):
        p = f"{stem}_{i}.png"
        build_body(s["image"], s["text"], handle, p, mau_wm)
        paths.append(p)

    print(f"da dung {len(paths)} slide:")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
