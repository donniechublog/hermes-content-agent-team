#!/usr/bin/env python3
"""Dung carousel nhieu slide kieu bang tin — anh o tren, khoi chu trang tren
nen den o duoi, watermark nghieng o day. Khac han card.py (mot the bia kieu
tran): day la mot bo N slide ke chuyen, dung cho Dre.

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
    FONTS,                       # thu muc font
    F_QUOTE, F_QUOTE_REG,        # kieu quote — cung dinh nghia font voi card.py
)

# ---- Khung so -------------------------------------------------------------
W, H = 1080, 1350                # kho dang chuan Instagram/Facebook 4:5
PAD = 84                         # le trai/phai cua chu, do tu mau tham chieu
BG = (0, 0, 0)                   # den tuyet doi — dau an cua kieu carousel nay
FG = (255, 255, 255)            # chu chinh trang
# Watermark ten kenh: MOT mau xanh co dinh (xanh nhu icon Finder cua macOS),
# KHONG doi theo brand nua.
WM = (10, 132, 255)             # #0A84FF — mau du phong neu chua nap thuong hieu

# Neobrutalism (dong bo voi card.py --kieu quote): chip khoi dac, vien den day,
# bong cung lech, chu mono. Mau chip lay CYAN nhan dien (dat qua dat_thuong_hieu
# trong main): donniechublog #00cce0, dcgr trang.
F_MONO_CH = str(FONTS / "JetBrainsMono-Regular.ttf")   # chip ten kenh (khong dam)
F_UI_CH = str(FONTS / "JetBrainsMono-Bold.ttf")        # chip category (dam)

# NEN CHO CHU O SLIDE THAN — SCRIM LIEN MACH kieu cover (Ong Chu chot: chu phai
# "chim" vao anh, KHONG duoc lo mot dai band):
#  (1) Man toi KHONG bat dau ngay o dong chu dau. Bat dau o do tao mot buoc
#      nhay toi ngay tren dong dau — tren anh SANG (logo, nen trang) mat bat
#      duoc mep ngay, doc ra "anh + bang chu". Nen bat dau lam toi tu CAO hon
#      nhieu (som nhat ~42% chieu cao), giong scrim cua slide bia.
#  (2) Tu do dam DAN xuong theo duong cong — gradient DAI, khong mep. Dong chu
#      dau da nam trong phan gradient (khong con "hoa vao anh sach" nhu truoc,
#      doi lai la lien mach that tren MOI loai anh).
#  (3) Cham ~MAX_TOI o vung chu de chu trang bat ro ke ca tren anh sang.
BLUR_RADIUS = 14                 # mo NHE thoi — du diu chi tiet sau chu, khong lam nen "tho"/duc
MAX_TOI = 205                    # do toi o vung chu ~80% (truoc 153/60%): dam hon de
                                 # chu chim lien mach ca tren anh sang, khong lo band
VEIL_TOP = 0.42                  # scrim bat dau SOM NHAT o 42% chieu cao (kieu cover)
VEIL_LEAD = 0.16                 # ...va luon bat dau TREN dong chu dau it nhat 16% chieu cao
VEIL_EASE = 1.4                  # duong cong: nhat o tren, dam dan xuong — khong mep
TEXT_BASE = 1230                 # day khoi chu; dai 1230..H chua chip ten kenh (goc duoi-trai)
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


def _cyan():
    """CYAN nhan dien da nap qua dat_thuong_hieu (donniechublog #00cce0, dcgr
    trang). Chua nap thi ve mau du phong."""
    return card.CYAN or WM


def _chip_neo(d, txt, font, x, y, fill, fg=(0, 0, 0), anchor="l",
              off=6, bord=4, pad_x=18, pad_y=10):
    """Chip NEOBRUTALISM dong bo voi card.py --kieu quote: khoi dac, vien den
    day, bong cung lech (khong mo), chu mono. anchor 'l' xep tu x sang phai,
    'r' canh phai o x. Tra ve (x0, y0, x1, y1) de xep tiep."""
    tb = d.textbbox((0, 0), txt, font=font)
    bw, bh = (tb[2] - tb[0]) + 2 * pad_x, (tb[3] - tb[1]) + 2 * pad_y
    x0 = x if anchor == "l" else x - bw
    x1, y1 = x0 + bw, y + bh
    d.rectangle([x0 + off, y + off, x1 + off, y1 + off], fill=(0, 0, 0))       # bong cung
    d.rectangle([x0, y, x1, y1], fill=fill, outline=(0, 0, 0), width=bord)     # khoi + vien
    d.text((x0 + pad_x - tb[0], y + pad_y - tb[1]), txt, font=font, fill=fg)
    return (x0, y, x1, y1)


WM_BOTTOM = 48                   # mep duoi chip ten kenh cach day khung


def _watermark(canvas, handle, x=None, y=None):
    """BRAND TEXT (ten kenh) — CHIP neobrutalism: khoi CYAN nhan dien, vien den,
    bong cung, chu mono. Dong bo voi hero card.

    VI TRI: goc DUOI-trai, trong dai trong duoi khoi chu (TEXT_BASE..H) — vung
    scrim toi nhat, KHONG bao gio de len noi dung anh. Truoc day dat goc tren-trai
    (y=48) nen de thang len tieu de/chart cua anh (Ong Chu bat loi 03/09/2026).
    `x`/`y` cho phep slide bia xep chip canh chip chuyen muc. Tra ve bbox."""
    if not handle:
        return None
    d = ImageDraw.Draw(canvas)
    f = _f(F_MONO_CH, WM_SIZE)
    if y is None:
        tb = d.textbbox((0, 0), handle, font=f)
        y = H - WM_BOTTOM - ((tb[3] - tb[1]) + 2 * 10)     # + 2*pad_y cua _chip_neo
    return _chip_neo(d, handle, f, PAD if x is None else x, y, fill=_cyan(), anchor="l")


def _scrim(canvas, tu=0.34):
    """Man toi day dan cho slide bia: trong o tren, dam dan xuong day de chu
    hook doc ro. `tu` la moc bat dau lam toi (theo ti le chieu cao).

    Truoc day tu=0.42, mu 1.4: voi hook 2 dong (truong hop ly tuong theo
    skill Dre) thi du toi, nhung hook 3 dong — van hop le, chi la cau dai
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


def _ghep_neu_can(muc, nhan, stem):
    """Slide/bia co "images": [a, b] (hai anh NGANG) -> ghep doc thanh mot anh
    (card.ghep_doc), ghi ra `<stem>.ghep.png` va gan vao muc["image"] de moi
    cong chan + builder phia sau dung nhu anh thuong. Xem ghi chu trong
    card.ghep_doc: thay vi crop anh ngang mat tieu de, xep hai anh ngang
    trong cung khung."""
    ds = muc.get("images")
    if not ds:
        return
    if not isinstance(ds, list) or len(ds) < 2:
        sys.exit(f"{nhan}: 'images' phai la danh sach >= 2 anh (ghep doc); "
                 "mot anh thi dung 'image'.")
    for q in ds:
        if not Path(q).exists():
            sys.exit(f"{nhan}: khong thay tep anh {q}")
    ra = Path(f"{stem}.ghep.png")
    ra.parent.mkdir(parents=True, exist_ok=True)
    card.ghep_doc(ds).save(ra, "PNG")
    muc["image"] = str(ra)


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
    """Lam NEN CHO CHU theo kieu SCRIM LIEN MACH cua cover — chu "chim" vao anh,
    khong lo mot dai band nao ke ca tren anh sang:

      - Man toi bat dau tu CAO (`top_y`, som nhat VEIL_TOP=42% chieu cao, va luon
        tren dong chu dau it nhat VEIL_LEAD). KHONG bat dau ngay o text_top: bat
        o do tao mot buoc nhay toi ngay tren dong dau, tren anh sang la lo mep.
      - Tu `top_y` dam DAN xuong theo duong cong (ease VEIL_EASE), cham gan-max
        (MAX_TOI) quanh dong chu cuoi (`full_y`) roi giu xuong day. Gradient DAI
        nen mat khong bat duoc mep.
      - Dong chu dau nay nam TRONG phan gradient (khong con "hoa vao anh sach"
        nhu ban cu) — doi lai la lien mach that tren MOI loai anh.

    Ca lop mo lan lop toi dung cung mot mat na. Van la ANH LAM MO chu khong phai
    mang den dat vao (MAX_TOI<255): o dam nhat anh van con hien.

    `veil_rgb` la ban COVER phu kin khung; bi lam mo manh nen cat/phong to (do
    cover) khong lo ra."""
    # Bat dau lam toi tu CAO (>=42% chieu cao), va luon TREN dong chu dau it
    # nhat VEIL_LEAD — de gradient DAI, khong lo mep ngay tren dong dau nhu khi
    # bat dau dung o text_top. Day la khac biet lam chu "chim" vao anh.
    top_y = max(0, min(text_top - int(H * VEIL_LEAD), int(H * VEIL_TOP)))
    full_y = TEXT_BASE - FULL_TOI_PAD             # cham max quanh dong chu cuoi
    blurred = veil_rgb.filter(ImageFilter.GaussianBlur(BLUR_RADIUS))
    # 1) tron dan sang ban mo — nhat o tren, mo dan xuong
    canvas.paste(blurred, (0, 0), _ramp_mask(top_y, full_y, hi=245, ease=VEIL_EASE))
    # 2) phu lop toi tang dan — nhat o tren, gan-max o vung chu
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
def build_body(img_path, text, handle, out):
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
    _watermark(canvas, handle)
    canvas.convert("RGB").save(out, "PNG")


# ---- Slide than dang quote (tuy slide) ------------------------------------
# Mot so slide than khong phai doan van ke ma la MOT cau trich dan manh (phong
# van, phat bieu, cau chot). Render dang pull-quote: cau lon + dau ngoac kep +
# dong nguon, cung ngon ngu voi card.py --kieu quote. Anh van phu kin + veil
# lien mach nhu moi slide than; watermark van o day. Dau ngoac lay ACCENT theo
# brand (dong bo voi card.py --kieu quote): donniechublog xanh, dcgr trang.
Q_HI, Q_LO = 60, 38              # co chu quote trong slide than
Q_LEAD = 14                      # gian dong quote (theo px, giong card.py)
Q_LINES = 7                      # cau dai hon la nen cat — xem cong chan
Q_BOTTOM = 1150                  # day cum quote


def build_body_quote(img_path, quote, attrib, handle, out):
    """Slide than dang pull-quote — dung chung khung + bo cuc voi card.py --kieu
    quote. MAU: net khung + brand text CO DINH xanh Apple; DAU " doi theo hang
    duoc nhac. Duoi khung: chip ten kenh canh trai, roi dong nguon canh giua sat day."""
    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    base = _body_image(canvas, _open(img_path))
    d = ImageDraw.Draw(canvas)

    FRAME_X = 40
    TEXT_X = FRAME_X + 50                     # chu thut vao, hai canh khung thoang
    avail = W - 2 * TEXT_X

    f_q, q_lines = card._fit_text(d, quote, avail, max_lines=Q_LINES,
                                  hi=Q_HI, lo=Q_LO, path=F_QUOTE)
    buoc, tren = card._buoc_dong(f_q, q_lines, Q_LEAD)
    quote_h = buoc * len(q_lines)

    f_at = _f(F_QUOTE_REG, 26)
    at_lines = _wrap(d, attrib, f_at, avail) if attrib else []
    at_lh = _line_h(f_at, 1.3)
    at_h = at_lh * len(at_lines)

    BOX_PAD_Y = 62       # khung cao hon chu — khoang tho + dau " o goc
    CHIP_INSET = 24      # chip thut vao tu canh phai khung
    G_FRAME_SRC = 44     # net ngang duoi cua khung <-> dong nguon
    BR_LIFT = 22         # net ngang duoi nam tren frame_bottom (card._quote_frame)

    # Dong bo voi card._render_quote (Ong Chu chot 03/09/2026): chip ten kenh o
    # goc TREN-PHAI khung, tam chip ngang muc net ngang tren; khung giu design
    # goc; dong nguon canh giua sat day.
    src_top = H - (WM_BOTTOM - 20) - at_h
    frame_bottom = src_top - G_FRAME_SRC + BR_LIFT
    last_line_bottom = frame_bottom - BOX_PAD_Y
    first_line_top = last_line_bottom - quote_h
    frame_top = first_line_top - BOX_PAD_Y

    # Man toi lien mach, neo tu tren dinh khung.
    _veil_bottom(canvas, base, max(0, frame_top - 24))

    # Cac dong quote.
    qy = first_line_top
    for ln in q_lines:
        d.text((TEXT_X, qy - tren), ln, font=f_q, fill=FG)
        qy += buoc

    # Net khung xanh Apple (WM) co dinh; dau " theo hang nhac trong quote/nguon.
    mau_hang = card._mau_hang_trong(quote) or card._mau_hang_trong(attrib)
    mark_col = card._du_sang(mau_hang) if mau_hang else _cyan()
    card._quote_frame(d, FRAME_X, frame_top, W - FRAME_X, frame_bottom, _cyan(), mark_col)

    # Chip ten kenh goc TREN-PHAI khung, tam chip ngang muc net ngang tren.
    if handle:
        f_wm = _f(F_MONO_CH, WM_SIZE)
        wtb = d.textbbox((0, 0), handle, font=f_wm)
        cw = (wtb[2] - wtb[0]) + 2 * 18
        ch = (wtb[3] - wtb[1]) + 2 * 10
        _watermark(canvas, handle, x=W - FRAME_X - CHIP_INSET - cw, y=frame_top - ch // 2)

    # Dong nguon CANH GIUA, sat day the.
    ay = src_top
    for ln in at_lines:
        lw_ln = d.textlength(ln, font=f_at)
        d.text(((W - lw_ln) / 2, ay), ln, font=f_at, fill=(190, 190, 190))
        ay += at_lh
    canvas.convert("RGB").save(out, "PNG")


def build_cover(img_path, hook, label, out, handle=None):
    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    cover = _fit_cover(_open(img_path), W, H)
    canvas.paste(cover.convert("RGB"), (0, 0))
    _scrim(canvas)
    d = ImageDraw.Draw(canvas)
    # Nhan nho o duoi cung; hook nam ngay tren nhan.
    label = (label or "").strip().upper()          # category -> chip, viet hoa
    y_label = None
    lf = None
    if label:
        lf = _f(F_UI_CH, LABEL_SIZE - 8)            # mono bold, vua chip
        ltb = d.textbbox((0, 0), label, font=lf)
        chip_h = (ltb[3] - ltb[1]) + 2 * 10         # + 2*pad_y
        y_label = H - 84 - chip_h
    # Khong co label: hook van phai nam TREN chip ten kenh o goc duoi-trai.
    wm_h = 0
    if handle:
        wtb = d.textbbox((0, 0), handle, font=_f(F_MONO_CH, WM_SIZE))
        wm_h = (wtb[3] - wtb[1]) + 2 * 10
    hook_bottom = (y_label - 28) if label else (H - WM_BOTTOM - wm_h - 28 if handle else H - 96)
    hf, wrapped, lh, total = _fit_block(
        d, [hook], W - 2 * PAD, int(H * 0.5), HOOK_HI, HOOK_LO,
        weight=HOOK_WEIGHT, lead=HOOK_LEAD)
    y = hook_bottom - total
    _draw_paragraphs(d, PAD, y, wrapped, hf, lh, FG)
    if label:
        # Hang duoi cung: chip ten kenh (cyan) + chip category (trang), cung y.
        bb = _watermark(canvas, handle, y=y_label)
        cx = (bb[2] + 16 + 6) if bb else PAD           # cach chip truoc 16px + bong 6px
        _chip_neo(d, label, lf, cx, y_label, fill=(255, 255, 255), anchor="l")
    else:
        _watermark(canvas, handle)      # chip ten kenh goc duoi-trai, nhu moi slide
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


# ---- Cong chan anh + chu (code hoa luat, khong dua vao ky luat cua vai) ----
# Cac luat nay Ong Chu da chot va truoc day chi nam trong SKILL.md — tuc trong
# cho vai NHO va TUAN THU. Chuyen thanh cong chan cung: vi pham la dung han,
# in ro cach sua. Vai chi con hai viec khong the code: viet copy va chon anh.
# --- Phat hien mat nguoi (offload luat "anh mot nguoi vo danh" cho code) ------
# Code chi BAT DUOC co mat nguoi hay khong (YuNet, nhe, khong torch). Con "co
# phai nhan vat cu the trong bai khong" thi code KHONG biet -> de vai/nguoi duyet
# phan doan. Vi vay day la CANH BAO, khong chan cung.
_YUNET = None
_YUNET_DA_THU = False


def _yunet():
    global _YUNET, _YUNET_DA_THU
    if _YUNET_DA_THU:
        return _YUNET
    _YUNET_DA_THU = True
    try:
        import os as _os
        _os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
        import cv2
        m = Path(__file__).resolve().parent / "assets" / \
            "face_detection_yunet_2023mar.onnx"
        if not m.exists():
            return None  # thieu model -> bo qua cong nay, khong crash build
        _YUNET = cv2.FaceDetectorYN_create(str(m), "", (320, 320),
                                           score_threshold=0.7)
    except Exception:
        _YUNET = None  # thieu cv2 / loi -> bo qua em
    return _YUNET


def _dem_mat(path):
    """So mat nguoi trong anh. None neu khong chay duoc (thieu cv2/model)."""
    det = _yunet()
    if det is None:
        return None
    try:
        import cv2
        im = cv2.imread(str(path))
        if im is None:
            return None
        h, w = im.shape[:2]
        det.setInputSize((w, h))
        _n, res = det.detect(im)
        return 0 if res is None else len(res)
    except Exception:
        return None


def _gate_anh(paths):
    """paths: [(nhan, duong_dan)]. Tra ve (loi, canh_bao)."""
    import hashlib
    from PIL import ImageStat
    loi, canh_bao = [], []
    da_thay = {}
    for nhan, p in paths:
        f = Path(p)
        if not f.exists():
            loi.append(f"{nhan}: khong thay tep anh {p}")
            continue
        # 1) TRUNG ANH: moi slide mot hinh duy nhat. Bat trung theo noi dung
        # tep (hash), khong theo ten — copy cung mot anh ra hai ten van bat.
        # (Hai CROP khac nhau cua cung mot tam thi hash khac — cai do van phai
        # nho vai/nguoi duyet soi, code khong bat chac chan duoc.)
        h = hashlib.md5(f.read_bytes()).hexdigest()
        if h in da_thay:
            loi.append(f"{nhan}: trung anh voi {da_thay[h]} — moi slide phai "
                       "mot hinh DUY NHAT, tim anh khac")
            continue
        da_thay[h] = nhan
        img = Image.open(p)
        w, h_px = img.size
        # 2) TI LE: phai 1:1 hoac 4:5 (dung sai 3%). Sai thi cat truoc bang
        # crop_ti_le.py — khong de carousel.py tu xoay so.
        # Chap nhan ca dai GIUA 4:5 va 1:1 (anh ghep doc hai anh ngang roi vao
        # day) — full be ngang deu phu 1080..1350 cao, khong lo nen.
        r = w / h_px
        if not (0.8 - 0.03 <= r <= 1.0 + 0.03):
            loi.append(f"{nhan}: ti le {w}x{h_px} ({r:.2f}) khong nam trong 4:5..1:1 "
                       f"— cat truoc: venv/bin/python crop_ti_le.py "
                       f"--anh {p} --ra <ra.png> [--ti-le 4:5] [--cx/--cy]; hoac anh "
                       f"NGANG thi tim them mot anh ngang nua, ghi \"images\": [a, b]")
        # 3) DO PHAN GIAI: canh ngan <1000px phong len 1080 se mem/vo net.
        # Canh bao thoi (khong chan): anh doc quyen nho van hon anh sai.
        if min(w, h_px) < 1000:
            canh_bao.append(f"{nhan}: canh ngan {min(w, h_px)}px < 1000 — "
                            "phong len 1080 se hoi mem, co ban to hon thi thay")
        # 4) DAY ANH SANG: nen chu chi toi max 60% opacity, chu trang can day
        # anh TOI. Do do sang trung binh 25% duoi; sang qua thi canh bao de
        # vai crop lai cho day roi vao vung toi (nhu vu mat duong truoc via he).
        day = img.convert("L").crop((0, int(h_px * 0.75), w, h_px))
        sang = ImageStat.Stat(day).mean[0]
        if sang > 150:
            canh_bao.append(f"{nhan}: 25% duoi anh sang (muc {sang:.0f}/255) — "
                            "chu trang tren nen 60% se kho doc; crop lai cho "
                            "day anh la vung toi hon")
        # 5) MAT NGUOI: luat "khong dung anh mot nguoi vo danh". Code chi bao co
        # mat hay khong; vai tu phan doan co phai nhan vat trong bai khong.
        nmat = _dem_mat(p)
        if nmat:
            canh_bao.append(f"{nhan}: phat hien {nmat} mat nguoi — neu KHONG phai "
                            "nhan vat cu the duoc nhac trong bai thi doi anh, hoac "
                            "crop bo (vd webcam reviewer o goc). Anh mot nguoi vo "
                            "danh doc ra la stock.")
    return loi, canh_bao


def _gate_chu(slides):
    """Chan copy DAI qua vung chu 30%: o co chu NHO NHAT ma khoi chu van cao
    hon TEXT_MAX_H thi truoc day no lang le tran len tren — vi pham luat 30%.
    Gio dung han va bao thua bao nhieu de vai cat bot loi."""
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    loi = []
    for i, s in enumerate(slides, start=2):
        # Slide quote dung fit rieng (cau don, khong theo vung 30%): chi chan
        # cau QUA DAI, o co chu nho nhat van tran qua so dong cho phep.
        if s.get("quote"):
            n = len(_wrap(probe, s["quote"], _f(F_QUOTE, Q_LO), W - 2 * PAD))
            if n > Q_LINES:
                loi.append(f"slide {i}: cau quote qua dai ({n} dong > {Q_LINES} "
                           "o co nho nhat) — cat cau ngan lai")
            continue
        paras = [p.strip() for p in s["text"].split("\n\n") if p.strip()]
        _f_, _w_, _lh_, total = _fit_block(
            probe, paras, W - 2 * PAD, TEXT_MAX_H, BODY_HI, BODY_LO)
        if total > TEXT_MAX_H:
            loi.append(f"slide {i}: copy dai qua vung chu 30% (thua "
                       f"{total - TEXT_MAX_H}px o co chu nho nhat) — cat bot "
                       f"khoang {round((total - TEXT_MAX_H) / total * 100)}% chu")
    return loi


def main():
    ap = argparse.ArgumentParser(description="Dung carousel nhieu slide (Dre)")
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
    _stem0 = Path(a.out).with_suffix("")
    _ghep_neu_can(cover, "bia", f"{_stem0}")
    for i, s in enumerate(slides, start=2):
        _ghep_neu_can(s, f"slide {i}", f"{_stem0}_{i}")
    if not cover.get("image") or not cover.get("hook"):
        sys.exit("Thieu cover.image hoac cover.hook trong spec.")
    if not slides:
        sys.exit("Carousel can it nhat mot slide than trong 'slides'.")
    if len(slides) + 1 > 10:
        sys.exit(f"Qua nhieu slide ({len(slides)+1}). draft_write gom toi _9, "
                 "toi da 10 slide ke ca bia.")
    if len(slides) + 1 < 5:
        sys.exit(f"Carousel can IT NHAT 5 slide ke ca bia (hien {len(slides)+1}). "
                 "Chuan social content chat luong (Ong Chu chot). Chia them nhip, "
                 "hoac gom them anh that — ket hop official site + magazine.")

    # Chuan hoa em-dash + chan tieng Viet mat dau truoc khi ve bat cu gi.
    cover["hook"] = bo_dau_cam(cover["hook"])
    cover["label"] = bo_dau_cam(cover.get("label", ""))
    chunks = [("bia/hook", cover["hook"])]
    for i, s in enumerate(slides, start=2):
        if not s.get("image"):
            sys.exit(f"Slide {i} thieu image.")
        # Moi slide than la MOT trong hai: doan van ke ("text") HOAC cau trich
        # dan ("quote", kem "attrib" tuy chon). Thieu ca hai la loi.
        if s.get("quote"):
            s["quote"] = bo_dau_cam(s["quote"])
            s["attrib"] = bo_dau_cam(s.get("attrib", ""))
            chunks.append((f"slide {i}", s["quote"]))
            if s["attrib"]:
                chunks.append((f"slide {i}/nguon", s["attrib"]))
        elif s.get("text"):
            s["text"] = bo_dau_cam(s["text"])
            chunks.append((f"slide {i}", s["text"]))
        else:
            sys.exit(f"Slide {i} thieu 'text' (doan van) hoac 'quote' (cau trich dan).")

    # Cong chan: MOI carousel phai co IT NHAT 2 slide QUOTE (Ong Chu chot — de
    # format trich dan duoc ap dung deu moi ngay, khong bi bo quen).
    so_quote = sum(1 for s in slides if s.get("quote"))
    if so_quote < 2:
        sys.exit(f"Carousel can IT NHAT 2 slide QUOTE (hien co {so_quote}). Chon "
                 "cac cau dat trong bai (phat bieu, con so, cau chot) lam slide "
                 "dang 'quote'+'attrib' — xem muc 'Slide quote' trong skill.")

    loi = _gate_text(chunks, a.bo_qua_dau)
    if loi:
        for e in loi:
            print(f"[LOI] {e}", file=sys.stderr)
        sys.exit("Chu carousel khong dat cong chan tieng Viet. Go lai co dau, "
                 "hoac --bo-qua-dau neu that su la tieng Anh.")

    # Cong chan anh (trung / ti le / phan giai / day sang) va copy tran 30%.
    anh = [("bia", cover["image"])] + \
          [(f"slide {i}", s["image"]) for i, s in enumerate(slides, start=2)]
    loi_anh, canh_bao = _gate_anh(anh)
    loi_chu = _gate_chu(slides)
    for c in canh_bao:
        print(f"[CANH BAO] {c}", file=sys.stderr)
    if loi_anh or loi_chu:
        for e in loi_anh + loi_chu:
            print(f"[LOI] {e}", file=sys.stderr)
        sys.exit("Carousel khong dat cong chan anh/chu. Sua theo huong dan o tren.")

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    stem = out.with_suffix("")            # bo .png de ghep hau to _2, _3

    build_cover(cover["image"], cover["hook"], cover.get("label", ""), str(out), handle)
    paths = [str(out)]
    for i, s in enumerate(slides, start=2):
        p = f"{stem}_{i}.png"
        if s.get("quote"):
            build_body_quote(s["image"], s["quote"], s.get("attrib", ""), handle, p)
        else:
            build_body(s["image"], s["text"], handle, p)
        paths.append(p)

    print(f"da dung {len(paths)} slide:")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
