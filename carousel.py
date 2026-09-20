#!/usr/bin/env python3
"""Dung carousel nhieu slide kieu bang tin — anh phu kin the, chip ten kenh o
goc duoi-trai. Khac han card.py (mot the bia kieu full_bleed): day la mot bo N slide
ke chuyen, dung cho Dre.

LUAT TREN HET (Ong Chu chot 04/09/2026, cap nhat 08/09/2026, CHUNG voi Kite
— xem IMAGE_RULES.md muc 7): moi slide la MOT MAT PHANG LIEN. Khong
vien, khong vach, khong vung den rieng, khong hai vung tach roi. Chu de len
anh: MAC DINH KHONG PHU LOP NAO — FG (trang/den, co dinh theo NEN ca bo) tu no
da tuong phan voi hau het anh. Chi khi do that tren pixel thay vung duoi chu
khong du tuong phan (qua sang/toi, hoac qua CLUTTERED) moi them mot lop mo+tinh
NGAN va VUA DU (_layer_if_can), khong bao gio bat dau truoc dong chu dau tien.
Nen bao gio cung la anh (lam mo neu can), khong bao gio la mot hop den dat
canh anh.

Bo cuc moi slide (1080x1350, ti le 4:5; background_tone "dark" mac dinh hoac "light" — xem BACKGROUND):

  Slide bia (slide 1):
    - Anh phu kin the (cover), lop mo+tinh o nua duoi CHI KHI can.
    - Cau hook chu dam, canh trai, nam sat day.
    - Nhan ngan (kicker) o duoi hook.

  Slide than (slide 2..N):
    - Anh full be ngang, giu nguyen ti le, KHONG cat hai canh (giu tron tieu de
      cua chart/bang). Cho nao lop sac khong phu thi ben duoi la chinh tam anh
      da LAM MO MANH lam nen — khong bao gio la nen den tro, cung khong bao gio
      la mot ban sao sac net cua chinh no (se doc ra hai vung).
    - Khoi chu canh trai o duoi, tach doan theo dong trong, DE LEN anh — lop
      mo+tinh (neu can) neo dung tai dong chu dau tien (_layer_if_can).
    - Chip ten kenh o goc DUOI-TRAI.

Xuat ra: <out>.png (bia), <out>_2.png, <out>_3.png ... <out>_N.png
Danh so nay khop dung glob cua draft_write.py (<id>.png + <id>_[0-9].png),
nen bo slide tu dong thanh album khi dang.

Nhap:
  --spec spec.json   (xem cau truc ben duoi)  hoac  --spec -  doc tu stdin

  {
    "handle": "donniechublog",           # watermark; mac dinh theo --handle/--brand
    "cover":  {"image": "...", "hook": "cau giat tit", "category": "MODEL RELEASE", "label": "QWEN 3.8 27B"},
    "slides": [
      {"image": "...", "text": "doan 1\\n\\ndoan 2"},
      ...
    ]
  }

Cong chan giong card.py: tieng Viet mat dau bi chan (tru --bo-qua-dau), em-dash
tu thay bang dau phay.
"""
import argparse
import re
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter

# Tai dung nguyen xi cac helper da kiem chung cua card.py thay vi viet lai:
# nap font co truc bien thien, wrap chu, contain/cover anh, cong chan tieng Viet.
import card
import image_rules_dre
import role_spec
import text_bg
from card import (
    _f, _wrap, _fit_cover,
    find_face_mark, drop_mark_forbid, set_brand, BRAND,
    F_REG,                       # Inter — sans khong chan, doc ra "bao" khong ra "code"
    FONTS,                       # thu muc font
    F_QUOTE, F_QUOTE_REG,        # kieu quote — cung dinh nghia font voi card.py
)

# ---- Khung so -------------------------------------------------------------
W, H = 1080, 1350                # kho dang chuan Instagram/Facebook 4:5
PAD = 84                         # le trai/phai cua chu, do tu mau tham chieu
# Hai bien the nen (Ong Chu chot 05/09/2026: nen KHONG co dinh den, nen phuc vu
# anh, den va trang la hai mau uu tien). "dark" = anh phu kin + man toi lien mach
# + chu trang (mac dinh); "light" = cung bo cuc, man SANG lien mach + chu den.
# Spec khai "background_tone": "light" (hoac --nen light). Moi bo carousel MOT nen.
# LOW-248: khoa tieng Viet cu toi/sang/mo -> dark/light/muted ("mo" = chu phu
# MO/nhat, ban dich cu "OPEN" la nham); --nen van nhan toi/sang (role_spec).
BACKGROUND = {"dark": {"bg": (0, 0, 0), "fg": (255, 255, 255), "muted": (190, 190, 190)},
       "light": {"bg": (255, 255, 255), "fg": (0, 0, 0), "muted": (80, 80, 80)}}
BACKGROUND_SHOW = "dark"
BG = (0, 0, 0)                   # nen/man phu (dat lai qua set_background)
FG = (255, 255, 255)            # chu chinh (dat lai qua set_background)
MUTED = (190, 190, 190)           # chu phu (dong nguon quote)


def set_background(ten):
    """Chon bien the nen cho ca bo. Goi truoc khi dung slide nao."""
    global BACKGROUND_SHOW, BG, FG, MUTED
    if ten not in BACKGROUND:
        raise ValueError(f"nen phai la mot trong: {', '.join(BACKGROUND)} (co: {ten!r})")
    BACKGROUND_SHOW = ten
    BG, FG, MUTED = BACKGROUND[ten]["bg"], BACKGROUND[ten]["fg"], BACKGROUND[ten]["muted"]
# Watermark ten kenh: MOT mau xanh co dinh (xanh nhu icon Finder cua macOS),
# KHONG doi theo brand nua.
WM = (10, 132, 255)             # #0A84FF — mau du phong neu chua nap thuong hieu

# Neobrutalism (dong bo voi card.py --kieu quote): chip khoi dac, vien den day,
# bong cung lech, chu mono. Mau chip lay CYAN nhan dien (dat qua set_brand
# trong main): donniechublog #00cce0, dcgr trang.
F_MONO_CH = str(FONTS / "JetBrainsMono-Regular.ttf")   # chip ten kenh (khong dam)
F_UI_CH = str(FONTS / "JetBrainsMono-Bold.ttf")        # chip category (dam)

# NEN CHO CHU O SLIDE THAN (Ong Chu chot 08/09/2026, nhac lai nhieu lan, CUNG
# luc voi Kite — xem IMAGE_RULES.md muc 7): FG la mot mau CO DINH theo NEN
# ca bo (trang tren "dark", den tren "light") — KHONG mac dinh phu lop nao len
# anh de dat chu. Chi khi do THAT SU tren pixel WYSIWYG (sau khi da dan anh,
# truoc khi ve chu) thay vung ngay duoi chu khong du tuong phan voi FG (qua
# sang/qua toi, hoac qua CLUTTERED — bien thien mau cao, chu mot mau khong an toan
# het cho) moi them MOT lop mo+tinh. Khi them: vua du (tran thap DARK_MAX,
# khong phai luon phu 80% roi moi tinh tiep), va KHONG BAO GIO bat dau truoc
# dong chu dau tien (khong con khoang dem VEIL_LEAD/VEIL_TOP chom truoc nhu
# ban cu).
BLUR_RADIUS = 14                 # mo NHE thoi — du diu chi tiet sau chu, khong lam nen "tho"/duc
BG_BLUR = 44                     # mo MANH ban cover lam nen: phai xoa het chi tiet doc duoc,
                                 # neu khong cho nao lop sac khong phu se lo mot BAN SAO
                                 # phong to cua chinh tam anh -> mat doc ra HAI VUNG
THRESHOLD_BRIGHT_DARK = 130    # nen "dark" (FG trang): sang trung binh duoi chu phai <= muc nay
THRESHOLD_BRIGHT_BRIGHT = 130   # nen "light" (FG den): (255 - sang) duoi chu phai <= muc nay
THRESHOLD_VARIANCE_NEEDS_LAYER = 26  # do lech mau (stddev xam) duoi chu vuot muc nay moi can lop
DARK_MAX = 140         # tran cua lop (0..255, ~55%) — "vua du", khong phu ca mang
VEIL_SPAN = 70           # px duong cong chuyen tiep — bat dau NGAY tai dong chu dau
VEIL_EASE = 1.3          # duong cong: nhat luc bat dau, dam dan trong VEIL_SPAN roi giu
TEXT_BASE = 1230                 # day khoi chu; dai 1230..H chua chip ten kenh (goc duoi-trai)
TEXT_MAX_H = 200                 # tran khoi chu: giu dinh chu >=1030 -> vung nen <=24% (<30%)

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
def _line_h(font, lines, lead):
    """Chieu cao MOT buoc dong, do bang CHINH cac dong SE VE — khong phai mot
    chuoi mau co dinh — roi nhan he so gian dong.

    Chuoi mau cu "ÂgqÁ" khong bao gom cac to hop dau DOI (mu/moc + dau thanh,
    vd "ẫ" "ệ" "ữ"): mot dong that co nhung to hop nay co the cao hon chuoi
    mau, khien hai dong lien nhau chong len nhau (Ong Chu nhac 08/09/2026 —
    dung phat hien cua card._step_line 06/09/2026 ben card.py: chuoi mau
    121px, dong that 134px, hai dong chong 11px). Rong danh sach (chua wrap
    duoc dong nao) thi lui ve chuoi mau tham chieu de van co mot con so."""
    hop = [font.getbbox(l) for l in lines if l] or [font.getbbox("ÂgqÁ")]
    tren = min(h[1] for h in hop)
    duoi = max(h[3] for h in hop)
    return int((duoi - tren) * lead)


def _fit_block(d, paragraphs, max_w, max_h, hi, lo, weight=None, lead=BODY_LEAD):
    """Chon co chu lon nhat de CA khoi (nhieu doan) con vua max_h.

    Tra ve (font, [(lines, line_h)], tong_cao). Qua nho van tra ve co lo.
    """
    for size in range(hi, lo - 1, -2):
        f = _f(F_REG, size, weight)
        wrapped = [_wrap(d, p, f, max_w) for p in paragraphs]
        lh = _line_h(f, [ln for w in wrapped for ln in w], lead)
        n_lines = sum(len(w) for w in wrapped)
        gap = int(lh * PARA_GAP) * max(0, len(paragraphs) - 1)
        total = n_lines * lh + gap
        if total <= max_h:
            return f, wrapped, lh, total
    f = _f(F_REG, lo, weight)
    wrapped = [_wrap(d, p, f, max_w) for p in paragraphs]
    lh = _line_h(f, [ln for w in wrapped for ln in w], lead)
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
    """CYAN nhan dien da nap qua set_brand (donniechublog #00cce0, dcgr
    trang). Chua nap thi ve mau du phong."""
    return card.CYAN or WM


def _net():
    """Mau NET (khung quote): CYAN nhan dien, nhung tren nen SANG mau gan trang
    (dcgr) thi khong thay — doi sang den. Chip van giu CYAN vi co vien den."""
    c = _cyan()
    if BACKGROUND_SHOW == "light" and card._measure_bright(c) > 0.85:
        return (0, 0, 0)
    return c


def _color_mark(mau_hang):
    """Mau dau " theo hang: nen toi keo sang cho doc duoc; nen sang giu nguyen
    (mau hang thuong dam, doc ro tren trang), tru khi qua nhat thi ve _net()."""
    if not mau_hang:
        return _net()
    if BACKGROUND_SHOW == "light":
        return _net() if card._measure_bright(tuple(mau_hang[:3])) > 0.85 else tuple(mau_hang[:3])
    return card._enough_bright(mau_hang)


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


# ---- Anh ------------------------------------------------------------------
def _open(path):
    img = Image.open(path).convert("RGB")
    return img


def _stack_if_can(muc, nhan, stem):
    """Slide/bia co "images": [a, b] (hai anh NGANG) -> ghep doc thanh mot anh
    (card.stack_read), ghi ra `<stem>.ghep.png` va gan vao muc["image"] de moi
    cong chan + builder phia sau dung nhu anh thuong. Xem ghi chu trong
    card.stack_read: thay vi crop anh ngang mat tieu de, xep hai anh ngang
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
    # Cong lech tone (`kiem_lech_tone`) da bo (Ong Chu 13/09/2026: bo
    # cam doan ve nguon/chat luong nay khoi he thong, moi vai).
    ra = Path(f"{stem}.ghep.png")
    ra.parent.mkdir(parents=True, exist_ok=True)
    # Dong dau XUAT XU (xem cong 2c): anh ghep co the roi dung 4:5 chan (vd hai
    # anh 16:10 xep doc), dau nay cho cong biet chinh carousel.py dung ra no.
    import image_provenance
    _meta = image_provenance.stamp_provenance("vertical_stack")
    stacked = card.stack_read(ds)
    stacked.save(ra, "PNG", pnginfo=_meta)
    muc["image"] = str(ra)
    # LOW-215: vi tri anh CUOI trong khung sau khi _body_image dan full be ngang
    # (cat giua doc neu cao hon H) — de cong sau do anh do con ro bao nhieu.
    last = Image.open(ds[-1])
    scale = W / stacked.width
    last_h = round(last.height * stacked.width / last.width * scale)
    total_h = round(stacked.height * scale)
    crop_top = (total_h - H) // 2 if total_h > H else 0
    muc["_stack_last"] = (total_h - last_h - crop_top, last_h)


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


def _measure_region_text(canvas, y0, y1):
    """Do sang trung binh + do roi (stddev xam) cua DUNG vung pixel WYSIWYG se
    nam duoi chu — doc thang tren canvas HIEN TAI (sau khi da dan anh, truoc
    khi ve chu), khong doan qua toa do nguon. -> (sang 0..255, variance 0..255)."""
    y0, y1 = max(0, int(y0)), min(H, int(y1))
    if y1 <= y0:
        return 255.0, 0.0
    return text_bg.measure_bright_offset(canvas.crop((0, y0, W, y1)))


# LOW-286 (Ong Chu 19/09/2026, hai slide Lovable dcgr): *"text chi duoc chiem khoang
# 20% dien tich, phan nen text da noi tu rat lau ko lam tho kech nhu vay, chi de nhu
# mot lop overlay tren anh, gio lai lam mot dong day com la sao"*. LOW-272 (sang cung
# ngay) cho MOI slide than co chi tiet duoi chu di nen dac cua LOW-215: mo 44px tu
# "khoang lang" (cat ngang mat nguoi) + phu mau nen 91% -> khoi den 33-47% khung.
# Tu nay slide than/quote CHI co mot OVERLAY gradient: bat dau OVERLAY_LEAD px tren
# dong chu dau, dam dan toi muc VUA DU tai dong chu dau roi giu, mo nhe
# OVERLAY_BLUR chi trong chinh vung do. Khong nen dac, khong dai mo phia tren.
OVERLAY_LEAD = 120               # px chuyen tu trong suot toi muc toi, ngay tren dong chu dau
OVERLAY_BLUR = 30                # mo chi tiet NGAY duoi chu (chu in san ~20-30px tan ra), chi trong vung overlay
OVERLAY_MIN, OVERLAY_MAX = 150, 205  # do toi overlay (0..255, ~59%..80%) tai vung chu
OVERLAY_FULL_BEFORE = 36         # overlay dat muc toi TRUOC dong chu dau bay nhieu px (dong dau khong nam tren dai chuyen)
OVERLAY_CLUTTERED = 205          # anh roi (LOW-47): overlay dam nhat, van la overlay
OVERLAY_BLUR_ALPHA = 220         # do dam cua lop MO trong cung mat na (0..255)
# Vong lui cua `_overlay_text` (LOW-330): nhan vao ca do mo lan do tinh. Buoc dau la
# nguyen ban LOW-286 — anh binh thuong dung ngay o buoc nay, khong doi gi. Anh sang +
# nhieu chi tiet (bang so lieu trang) moi phai lui, va lui toi khi do tren pixel that
# noi anh VAN con hien qua. 0.45 la day: duoi nua thi chu het tuong phan.
OVERLAY_BACKOFF = (1.0, 0.86, 0.72, 0.58, 0.45)
# LOW-330 (Ong Chu 20/09/2026, xem bia dcgr "Anthropic tu dat thuoc do": *"dung de cho
# nen dac, trong rat thieu chuyen nghiep"*). Truoc do BIA con mot duong rieng: anh roi
# lam bia thi phu MAU NEN DAC tu khoang lang xuong day (`_background_solid_below_text`,
# LOW-47) — nua duoi bia thanh mot khoi tron. Nay bia di cung duong voi slide than: chi
# overlay, ke ca anh roi. Khong con duong nao trong ma sinh ra nen dac nua.
# CONG DO nen chu tren pixel THAT (LOW-286): moi slide than/quote VA BIA (LOW-330), bat
# ke di duong code nao, so canvas NGAY TRUOC khi ve chu voi ban chi co anh. Do 19/09 tren
# 13 slide that (Lovable + Cowork): nen LOW-272 phu dac nhat 0.92-0.97 va dai doi manh bat
# dau tu 46-62% khung; overlay LOW-286 phu 0.64-0.84, dai doi toi da ~0.40 (quote dai nhat).
TEXT_BG_MAX_OPACITY = 0.88       # hang nao bi phu dac hon muc nay = nen dac, khong phai overlay
TEXT_BG_SAFE_OPACITY = 0.82      # dich cua vong lui `_overlay_text`: duoi tran, co bien an toan
TEXT_BG_MAX_SHARE = 0.42         # phan khung (tu day len) bi nen chu doi manh
TEXT_BG_CHANGED = 10             # do lech sang trung binh / hang coi la "doi manh"
TEXT_BG_LIFT_MIN = 40            # hang anh cach mau nen it nhat bay nhieu moi tinh do phu
# Bia duoc phu cao hon slide than vi HOOK cao hon han doan van: `_fit_block` cho hook toi
# 50% khung, cong OVERLAY_LEAD (9% khung) va hang chip duoi cung. Tran DO DAC thi GIONG
# HET slide than — "dac" la dac, bia hay slide than cung mot luat (LOW-330).
TEXT_BG_MAX_SHARE_COVER = 0.68


def _text_bg_report(before, after) -> dict:
    """So canvas SAU nen chu voi TRUOC nen chu (cung tam anh, chua ve chu) ->
    {"bg_share": phan khung tu hang doi manh dau tien xuong day,
     "bg_opacity": do phu lon nhat (0 = giu nguyen anh, 1 = mau nen dac)}.
    Do phu tinh tren trung binh hang nen lop mo (bao toan trung binh) khong lam sai."""
    import numpy as np
    b = np.asarray(before.convert("L"), dtype=np.float32)
    a = np.asarray(after.convert("L"), dtype=np.float32)
    doi = np.abs(a - b).mean(axis=1)
    ys = np.nonzero(doi > TEXT_BG_CHANGED)[0]
    share = float((H - ys.min()) / H) if len(ys) else 0.0
    bg = 0.299 * BG[0] + 0.587 * BG[1] + 0.114 * BG[2]
    bm, am = b.mean(axis=1), a.mean(axis=1)
    lift = bm - bg
    m = np.abs(lift) >= TEXT_BG_LIFT_MIN
    op = float(((bm - am)[m] / lift[m]).max()) if m.any() else 0.0
    return {"bg_share": round(share, 3), "bg_opacity": round(max(0.0, op), 3)}


def _gate_text_background(nhan, report, max_share=TEXT_BG_MAX_SHARE) -> str:
    """Nen chu vuot luat Ong Chu (LOW-286: "chi de nhu mot lop overlay tren anh") -> loi.
    Day la loi CODE dung slide, vai khong sua duoc bang spec.

    `max_share` de bia noi ra (TEXT_BG_MAX_SHARE_COVER): hook cao hon doan van nen vung
    phu cao hon. Tran DO DAC thi khong noi cho ai — do la chinh dinh nghia "nen dac"."""
    if not report:
        return ""
    sai = []
    if report["bg_opacity"] > TEXT_BG_MAX_OPACITY:
        sai.append(f"phu dac {report['bg_opacity']:.0%} > {TEXT_BG_MAX_OPACITY:.0%} (nen dac, khong phai overlay)")
    if report["bg_share"] > max_share:
        sai.append(f"nen chu doi anh tu {report['bg_share']:.0%} khung tro xuong > {max_share:.0%}")
    if not sai:
        return ""
    return (f"{nhan}: nen chu sai luat overlay — {'; '.join(sai)}. Loi CODE carousel.py "
            "(LOW-286), khong phai spec: KHONG gui album, kanban_block kem nguyen van dong nay.")


# Cap anh ghep doc co anh RO duoi nen bi phu (mo/toi) gan het thi anh do la
# vo ich va doc ra hai manh: chan, bat vai doi thu tu hoac dung anh khac.
STACK_BOTTOM_VISIBLE_MIN = 0.35


def _overlay_text(canvas, text_top, thieu, variance_excess, image_cluttered=False):
    """Nen chu slide than/quote (LOW-286): MOT overlay gradient tren anh, khong nen dac.

    Mat na bat dau `OVERLAY_LEAD` px tren dong chu dau, dam dan (ease) toi muc toi
    tai dong chu dau roi giu toi day. Muc toi tinh theo nhu cau do THAT tren pixel
    (qua sang / qua roi duoi chu), ke ca anh roi (LOW-47) — trong khoang
    OVERLAY_MIN..OVERLAY_MAX. Mo nhe OVERLAY_BLUR chi tren CUNG mat na: chi tiet ngay
    duoi chu diu di, phan anh phia tren giu nguyen (khong con dai mo manh cat ngang
    mat nguoi nhu nen LOW-215/272).

    LOW-330 (Ong Chu 20/09/2026: *"dung de cho nen dac, trong rat thieu chuyen nghiep"*):
    muc toi CO DINH o tren KHONG du de hua "khong bao giờ la nen dac". Do that hai slide
    dcgr 20/09: mo 30px + tinh 80% tren mot vung SANG va nhieu chi tiet (bang so lieu
    trang) lam vung do tu do lech 99,7 xuong 3,5 — tuc mat 96% chi tiet, mat nhin ra
    MOT MANG TRANG. Cong `_gate_text_background` bat dung (95% > 88%) nhung bat xong thi
    Dre DUNG han, khong ra bai. Nay tu LUI: do lai chinh ket qua tren pixel, con dac hon
    tran thi ha ca mo lan tinh theo `OVERLAY_BACKOFF` roi ve lai, toi khi anh that su con
    hien qua. Anh cang sang/cang nhieu chi tiet thi lui cang nhieu — dung cho no thanh
    mang mau."""
    top_y = max(0, int(text_top) - OVERLAY_LEAD)
    full_y = max(top_y + 1, int(text_top) - OVERLAY_FULL_BEFORE)
    if image_cluttered:
        do = OVERLAY_CLUTTERED
    else:
        do = min(OVERLAY_MAX, max(OVERLAY_MIN, thieu * 2.2, variance_excess * 3.0))
    # Mo tren CHINH canvas (khong phai ban cover `base`): slide ghep / anh ngang thap co
    # nen mo khac anh cover — lay cover se lo ban sao cua anh duoi chu (luat 04/09).
    # Ban mo tinh MOT lan: moi vong lui chi doi do dam cua mat na, khong doi anh mo.
    truoc = canvas.copy()
    blurred = canvas.convert("RGB").filter(ImageFilter.GaussianBlur(OVERLAY_BLUR))
    mau_nen = Image.new("RGB", (W, H), BG)
    for lui in OVERLAY_BACKOFF:
        if lui != OVERLAY_BACKOFF[0]:
            canvas.paste(truoc, (0, 0))                  # ve lai tu anh goc, khong chong lop
        canvas.paste(blurred, (0, 0), _ramp_mask(top_y, full_y, hi=int(OVERLAY_BLUR_ALPHA * lui), ease=VEIL_EASE))
        canvas.paste(mau_nen, (0, 0), _ramp_mask(top_y, full_y, hi=int(do * lui), ease=VEIL_EASE))
        if _text_bg_report(truoc, canvas)["bg_opacity"] <= TEXT_BG_SAFE_OPACITY:
            break
    return top_y


def _layer_if_can(canvas, base, text_top, text_bottom, image_cluttered=False, overlay_only=False):
    """Them mot lop mo+tinh NGAY TAI text_top — CHI KHI can (xem nguyen tac o
    dau file). Mac dinh khong lam gi: FG (co dinh theo NEN ca bo) da du tuong
    phan thi giu nguyen anh.

    `base` la ban COVER sac net (chua lam mo) dung lam nguon cho lop mo, cung
    mot tam anh voi phan da dan len canvas nen khong lech vung. `text_top`/
    `text_bottom` la vung se do de QUYET DINH co can lop khong; mat na ve ra
    luon giu phang tu `text_top + VEIL_SPAN` tro xuong H, khong phu thuoc
    `text_bottom`.

    `overlay_only`: slide than/quote LUON di duong overlay LOW-286. Anh roi cung vay,
    o moi cho ke ca bia (LOW-330) — khong con duong nen dac nao."""
    sang, variance = _measure_region_text(canvas, text_top, text_bottom)
    if FG == (255, 255, 255):
        thieu = max(0.0, sang - THRESHOLD_BRIGHT_DARK)          # nen "dark": qua sang la thieu
    else:
        thieu = max(0.0, (255 - sang) - THRESHOLD_BRIGHT_BRIGHT)  # nen "light": qua toi la thieu
    variance_excess = max(0.0, variance - THRESHOLD_VARIANCE_NEEDS_LAYER)
    if overlay_only or image_cluttered:
        # Slide than/quote: chi mot overlay (LOW-286). LOW-272 truoc day cho moi anh co
        # chi tiet duoi chu di nen dac LOW-215 -> khoi den 33-47% khung, Ong Chu bac.
        # Anh CLUTTERED o BIA truoc day di nen dac han (LOW-47) -> LOW-330 dua ve cung day.
        if thieu <= 0 and variance_excess <= 0 and not image_cluttered:
            return                   # da du tuong phan tren pixel that — khong phu gi
        return _overlay_text(canvas, text_top, thieu, variance_excess, image_cluttered)
    if thieu <= 0 and variance_excess <= 0:
        return                       # da du tuong phan tren pixel that — khong phu gi
    do = min(DARK_MAX, max(40.0, thieu * 1.8, variance_excess * 2.2))
    top_y = max(0, int(text_top))
    full_y = min(H, top_y + VEIL_SPAN)
    blurred = base.filter(ImageFilter.GaussianBlur(BLUR_RADIUS))
    # 1) mo NHE ban sac ngay tai vung chu — xoa chi tiet gay roi
    canvas.paste(blurred, (0, 0), _ramp_mask(top_y, full_y, hi=200, ease=VEIL_EASE))
    # 2) tinh VUA DU (tran DARK_MAX, khong phai mac dinh phu cao roi moi tinh)
    lop = Image.new("RGB", (W, H), BG)
    canvas.paste(lop, (0, 0), _ramp_mask(top_y, full_y, hi=int(do), ease=VEIL_EASE))


def _body_image(canvas, img):
    """Phu anh len canvas, KHONG cho nao la nen den tro va KHONG BAO GIO de lo
    HAI VUNG rieng biet (Ong Chu chot 04/09/2026):

      - NEN: ban COVER phu kin khung (0..H), LAM MO MANH (BG_BLUR). Phai mo:
        cover la ban PHONG TO cua chinh tam anh, de sac net thi cho nao lop tren
        khong phu se lo mot BAN SAO LECH cua cung noi dung (vd duoi bang
        benchmark hien lai chinh bang do o co khac) — mat doc ra hai vung, va
        con giong loi ky thuat. Lam mo bien nen thanh mot mang mau lien, de anh
        sac o tren doc ra MOT chu the tren MOT mat phang.
      - KHONG lam toi them nen: nen toi hon han lop sac se ve ra mot hinh chu
        nhat quanh chart — dung la hai vung. Chi _layer_if_can moi duoc lam toi
        (va chi khi thuc su can — xem ham do), theo gradient ngan nen khong
        sinh mep.
      - LOP SAC len tren: full be ngang, KHONG cat hai canh -> giu tron chi
        tiet mep (chup man hinh, bang so khong bi cat chu). Anh 4:5 phu kin
        luon (nen khong lo ra ti nao); anh 1:1 phu 0..~1080, phan duoi la nen.

    Tra ve ban COVER SAC (de _layer_if_can dung lam nguon mo neu can).
    (Luat: anh dua vao carousel da la 1:1 hoac 4:5 — xem crop_ratio.py; nen
    luon cham du sau.)"""
    cover = _fit_cover(img, W, H).convert("RGB")
    # Nen phu kin, khong cho nao den — va lam mo de khong lo ban sao sac net.
    canvas.paste(cover.filter(ImageFilter.GaussianBlur(BG_BLUR)), (0, 0))
    scale = W / img.width
    nh = round(img.height * scale)
    resized = img.resize((W, nh), Image.LANCZOS)
    y0 = 0
    if nh > H:                                    # cao hon khung: cat giua doc, full be ngang
        top = (nh - H) // 2
        resized = resized.crop((0, top, W, top + H))
    elif nh < int(H * 0.6):
        # Anh NGANG (chart/bang "chart": true) thap hon vung anh: dat vao GIUA
        # vung tren (0..~60% cao, tren scrim chu) thay vi dinh mep tren.
        y0 = max(0, (int(H * 0.6) - nh) // 2)
    canvas.paste(resized, (0, y0))                # lop sac uncropped len tren nen cover
    return cover


# ---- Dung tung slide ------------------------------------------------------
def build_body(img_path, text, handle, out, cluttered=False, report=None, logo_bg=None):
    """`logo_bg` (LOW-295): slide LOGO — anh dua vao da la khung dung san (logo 90% be ngang
    tren chinh mau nen cua no, xem logo_card.py). Luc do dan NGUYEN khung, chu lay mau tuong
    phan voi nen va KHONG co overlay (Ong Chu 20/09/2026: "dung co them nen text, rat la phen")."""
    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    if logo_bg:
        canvas.paste(_open(img_path).convert("RGB").resize((W, H)), (0, 0))
        base = None
    else:
        base = _body_image(canvas, _open(img_path))
    truoc_nen = canvas.copy() if report is not None else None

    # Do khoi chu TRUOC (tran 30%), NEO TU DUOI: mep duoi luon o TEXT_BASE, chu
    # cao bao nhieu day len bay nhieu — luon sat day, khong tran len qua 30%,
    # anh cao/thap khong keo vi tri chu. Copy dai thi _fit_block co chu nho lai
    # cho vua TEXT_MAX_H (van trong 30%).
    d = ImageDraw.Draw(canvas)
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    font, wrapped, lh, total = _fit_block(
        d, paras, W - 2 * PAD, TEXT_MAX_H, BODY_HI, BODY_LO)
    text_top = TEXT_BASE - total

    # Chi them lop khi do THAT tren pixel thay vung duoi chu khong du tuong
    # phan voi FG — xem _layer_if_can. Khong bao gio bat dau truoc text_top.
    if logo_bg:
        import logo_card
        touched, fg = None, logo_card.text_color(tuple(logo_bg))
    else:
        touched = _layer_if_can(canvas, base, text_top, TEXT_BASE, image_cluttered=cluttered,
                                overlay_only=True)
        fg = FG
    if report is not None:                      # LOW-286: do nen chu tren pixel that
        report.update(_text_bg_report(truoc_nen, canvas))

    _draw_paragraphs(d, PAD, text_top, wrapped, font, lh, fg)
    _watermark(canvas, handle)
    canvas.convert("RGB").save(out, "PNG")
    return touched


# ---- Slide than dang quote (tuy slide) ------------------------------------
# Mot so slide than khong phai doan van ke ma la MOT cau trich dan manh (phong
# van, phat bieu, cau chot). Render dang pull-quote: cau lon + dau ngoac kep +
# dong nguon, cung ngon ngu voi card.py --kieu quote. Anh van phu kin + veil
# lien mach nhu moi slide than; watermark van o day. Dau ngoac lay ACCENT theo
# brand (dong bo voi card.py --kieu quote): donniechublog xanh, dcgr trang.
Q_HI, Q_LO = 60, 38              # co chu quote trong slide than
# Be rong THAT su cua chu quote khi ve (build_body_quote thut vao trong khung).
# Cong chan _gate_overflow truoc 06/09/2026 do o W - 2*PAD = 912px trong khi ban ve
# chi rong 900px: cau vua du 7 dong luc do khi ve thanh 8 dong — lot cong roi
# bi cat. Hai cho phai dung CUNG mot so.
Q_FRAME_X = 40                   # le khung quote
Q_TEXT_X = Q_FRAME_X + 50        # chu thut vao trong khung
Q_AVAIL = W - 2 * Q_TEXT_X
Q_LEAD = 14                      # gian dong quote (theo px, giong card.py)
Q_LINES = 7                      # cau dai hon la nen cat — xem cong chan
# LOW-286 (Ong Chu 19/09/2026: "text chi duoc chiem khoang 20% dien tich"): khoi chu
# quote cao toi da 20% khung. Truoc day chon co lon nhat con vua Q_LINES dong -> cau
# 4 dong co 60 cao 336px (25%) va nen chu mo tu dinh khung quote (~47% khung).
Q_TEXT_MAX_H = round(H * 0.20)


def _fit_quote(d, quote):
    """Co chu quote LON NHAT ma khoi chu cao <= Q_TEXT_MAX_H va <= Q_LINES dong.
    -> (font, lines, buoc, tren, vua). `vua` False: o co Q_LO van cao qua — cong
    _gate_overflow bao vai cat cau; luc ve (bo qua cong) van dung co Q_LO."""
    for size in range(Q_HI, Q_LO - 1, -2):
        f = _f(F_QUOTE, size)
        lines = _wrap(d, quote, f, Q_AVAIL)
        buoc, tren = card._step_line(f, lines, Q_LEAD)
        if len(lines) <= Q_LINES and buoc * len(lines) <= Q_TEXT_MAX_H:
            return f, lines, buoc, tren, True
    return f, lines, buoc, tren, False


def build_body_quote(img_path, quote, attrib, handle, out, cluttered=False, report=None):
    """Slide than dang pull-quote — dung chung khung + bo cuc voi card.py --kieu
    quote. MAU: net khung + brand text CO DINH xanh Apple; DAU " doi theo hang
    duoc nhac. Duoi khung: chip ten kenh canh trai, roi dong nguon canh giua sat day."""
    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    base = _body_image(canvas, _open(img_path))
    truoc_nen = canvas.copy() if report is not None else None
    d = ImageDraw.Draw(canvas)

    FRAME_X, TEXT_X, avail = Q_FRAME_X, Q_TEXT_X, Q_AVAIL

    f_q, q_lines, buoc, tren, _vua = _fit_quote(d, quote)
    quote_h = buoc * len(q_lines)

    f_at = _f(F_QUOTE_REG, 26)
    at_lines = _wrap(d, attrib, f_at, avail) if attrib else []
    at_lh = _line_h(f_at, at_lines, 1.3)
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

    # Chi them lop khi do THAT can (xem _layer_if_can). Overlay neo o DONG CHU DAU
    # (LOW-286), khong phai dinh khung: truoc day tu frame_top nen nen chu phu ~47% khung.
    touched = _layer_if_can(canvas, base, max(0, first_line_top), H, image_cluttered=cluttered,
                            overlay_only=True)
    if report is not None:                      # LOW-286: do nen chu tren pixel that
        report.update(_text_bg_report(truoc_nen, canvas))

    # Cac dong quote.
    qy = first_line_top
    for ln in q_lines:
        d.text((TEXT_X, qy - tren), ln, font=f_q, fill=FG)
        qy += buoc

    # Net khung xanh Apple (WM) co dinh; dau " theo hang nhac trong quote/nguon.
    mau_hang = card._color_rank_within(quote) or card._color_rank_within(attrib)
    mark_col = _color_mark(mau_hang)
    card._quote_frame(d, FRAME_X, frame_top, W - FRAME_X, frame_bottom, _net(), mark_col)

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
        d.text(((W - lw_ln) / 2, ay), ln, font=f_at, fill=MUTED)
        ay += at_lh
    canvas.convert("RGB").save(out, "PNG")
    return touched


CATEGORY_CALL_Y = ["MODEL RELEASE", "MODEL UPDATE", "PRODUCT", "RESEARCH",
                  "FUNDING", "POLICY", "OPINION"]


def build_cover(img_path, hook, label, out, handle=None, category="MODEL UPDATE", cluttered=False,
                report=None):
    """Bia: hang chip duoi cung = chip CATEGORY (cyan, thay cho ten kenh — Ong
    Chu chot 03/09/2026: hero slide KHONG dung chip 'donniechublog', phai la
    'MODEL RELEASE' / 'MODEL UPDATE'...) + chip label trang (ten model/hang).
    Ten kenh chi xuat hien tren cac slide than."""
    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    if cluttered:
        # Anh roi lam bia (LOW-47): KHONG cover-crop — cat hai canh la mat chu
        # khoa o mep (do that A9: "NVIDIA" cut). Hien NGUYEN be ngang nhu slide than.
        cover = _body_image(canvas, _open(img_path))
    else:
        cover = _fit_cover(_open(img_path), W, H).convert("RGB")
        canvas.paste(cover, (0, 0))
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
    category = (category or "MODEL UPDATE").strip().upper()
    # Khong co label: hook van phai nam TREN chip category o goc duoi-trai.
    wtb = d.textbbox((0, 0), category, font=_f(F_MONO_CH, WM_SIZE))
    wm_h = (wtb[3] - wtb[1]) + 2 * 10
    hook_bottom = (y_label - 28) if label else (H - WM_BOTTOM - wm_h - 28)
    hf, wrapped, lh, total = _fit_block(
        d, [hook], W - 2 * PAD, int(H * 0.5), HOOK_HI, HOOK_LO,
        weight=HOOK_WEIGHT, lead=HOOK_LEAD)
    y = hook_bottom - total
    # Do vi tri hook TRUOC roi moi quyet dinh co can lop khong (xem
    # _layer_if_can) — the tich category/label o duoi la chip dac, tu doc duoc,
    # khong can lop bao ve.
    truoc_nen = canvas.copy() if report is not None else None
    _layer_if_can(canvas, cover, y, H, image_cluttered=cluttered)
    if report is not None:                      # LOW-330: bia cung bi do nhu slide than
        report.update(_text_bg_report(truoc_nen, canvas))
    _draw_paragraphs(d, PAD, y, wrapped, hf, lh, FG)
    if label:
        # Hang duoi cung: chip CATEGORY (cyan) + chip label (trang), cung y.
        bb = _watermark(canvas, category, y=y_label)
        cx = (bb[2] + 16 + 6) if bb else PAD           # cach chip truoc 16px + bong 6px
        # chip label: trang chu den tren nen toi, den chu trang tren nen sang
        _chip_neo(d, label, lf, cx, y_label, fill=FG, fg=BG, anchor="l")
    else:
        _watermark(canvas, category)    # chip category goc duoi-trai
    canvas.convert("RGB").save(out, "PNG")


# ---- Cong chan tam co tin ------------------------------------------------
# San tuyet doi cua mot bo carousel (ke ca bia). Duoi muc nay thi khong con la
# carousel — tin mot tang de Ethan dung mot the hero. image_prepare doc hang so
# nay (khong chep so 5) va ghi vao manifest.json de approve_service biet ha san toi
# dau khi Ong Chu bam "lam voi N anh".
# Ong Chu 12/09/2026: "ha flagship xuong 7, tin thuong giu 6" — hoi vi sao Dre doi 8
# anh khi mot carousel 6 la dat. Truoc do 5 / 8 (8 tu loi GPT-6 Astra 03/09).
MIN_SLIDE = 6
FLAGSHIP_MIN = 7
# Ho model cua cac hang frontier (My + top Trung Quoc, theo scan_models.py).
_FLAGSHIP_RE = re.compile(
    r"\b(GPT-?\d|GPT-?[0-9.]+|o[3-9](?:-pro|-mini)?|Claude|Opus|Sonnet|Gemini|Llama|"
    r"Grok|DeepSeek|Qwen|Kimi|GLM|MiniMax|Doubao|Mistral Large|Nova Premier)\b", re.I)


def _is_flagship(spec, cover, slides):
    """Tin flagship = spec khai "tier": "flagship", HOAC hook/label/chu nhac
    ten ho model frontier (tu dong, de vai khong "quen" khai). Khai
    "tier": "regular" thi tat tu dong (chi khi Ong Chu noi ro)."""
    tc = str(spec.get("tier") or "").strip().lower()
    if tc == "flagship":
        return True
    if tc == "regular":
        return False
    chu = " ".join([cover.get("hook", ""), cover.get("label", "")] +
                   [s.get("text", "") + " " + s.get("quote", "") for s in slides])
    return bool(_FLAGSHIP_RE.search(chu))


# ---- Cong chan tieng Viet -------------------------------------------------
def _gate_text(chunks, bo_qua_dau):
    """Chan tieng Viet mat dau tren toan bo chu cua carousel (giong cong 1 cua
    card.py). Tra ve danh sach loi; rong la sach."""
    loi = []
    if bo_qua_dau:
        return loi
    for nhan, t in chunks:
        mat = find_face_mark(t)
        if mat:
            loi.append(f"{nhan}: tieng Viet mat dau ({', '.join(mat)})")
    return loi


# ---- Cong chan anh + chu (code hoa luat, khong dua vao ky luat cua vai) ----
# Cac luat nay Ong Chu da chot va truoc day chi nam trong SKILL.md — tuc trong
# cho vai NHO va TUAN THU. Chuyen thanh cong chan cung: vi pham la dung han,
# in ro cach sua. Vai chi con hai viec khong the code: viet copy va chon anh.
def _gate_image(paths):
    """paths: [(nhan, duong_dan, muc)] — muc la dict cover/slide trong spec.

    Chi PHAN HOP cac cong chan cua `image_rules_dre` theo dung thu tu cua khung
    carousel; ban than cac luat nam ben do va dung chung voi Ethan/Itachi.
    Cai RIENG cua carousel chi la: dai ti le 4:5..1:1, va viec slide than khai
    "chart": true thi mien cong ti le (anh ngang duoc dan full be ngang).

    Tra ve (loi, canh_bao).
    """
    loi, canh_bao = [], []
    da_thay = {}
    da_subject = {}                      # LOW-265: chan dung lap chu the trong carousel

    def gom(ket_qua):
        a, b = ket_qua
        loi.extend(a)
        canh_bao.extend(b)
        return not a

    for nhan, p, muc in paths:
        muc = muc or {}
        if not Path(p).exists():
            loi.append(f"{nhan}: khong thay tep anh {p}")
            continue
        if not gom(image_rules_dre.check_duplicate(nhan, p, da_thay)):
            continue
        img = Image.open(p)
        w, h_px = img.size
        la_bia = (nhan == "bia")
        khai_chart = bool(muc.get("chart"))

        # Anh RONG chan TRUOC check_chart_integrity: anh trang tron duoc do_chart cham la
        # "chart" (phang 100%, 2 mau), de sau thi thong bao thanh "thieu co".
        if not gom(image_rules_dre.check_blank_image(nhan, img)):
            continue
        if not gom(image_rules_dre.check_chart_integrity(nhan, img, khai_chart, la_bia)):
            continue

        # RIENG CUA CAROUSEL: slide than khai "chart": true -> nhan ca anh NGANG
        # nguyen ven (_body_image dan full be ngang, khong cat). Bia thi khong,
        # vi hook de len anh; bia chart ngang phai ghep doc "images".
        r = w / h_px
        if khai_chart and not la_bia and r > image_rules_dre.TI_LE_11 + image_rules_dre.TOLERANCE_RATIO:
            if image_rules_dre.read_crop_trace(img):
                loi.append(f"{nhan}: chart ma van di qua crop_ratio.py — chart phai "
                           'NGUYEN VEN, dua thang anh goc vao voi "chart": true')
            continue
        # Anh GHEP DOC ("images") duoc san rieng STACK_FLOOR (LOW-178): _body_image
        # cat giua doc phan cao hon khung, dre_submit da canh bao mep nao bi cat.
        gom(image_rules_dre.check_aspect_ratio(
            nhan, p, w, h_px, img=img,                                # img: de mien tru anh xep hang
            lo=image_rules_dre.STACK_FLOOR if muc.get("images") else image_rules_dre.TI_LE_45))

        gom(image_rules_dre.check_crop_landscape(nhan, img, w, h_px, muc.get("crop_ok")))
        gom(image_rules_dre.check_resolution(nhan, w, h_px))
        gom(image_rules_dre.check_unnamed_face(nhan, p, muc.get("subject")))
        gom(image_rules_dre.check_repeated_subject_portrait(nhan, p, muc, da_subject))
        # LOW-267: tep ghep co 2 mat nen cong tren bo qua — kiem tung tam thanh phan.
        gom(image_rules_dre.check_stack_portrait_subjects(nhan, muc.get("images"), muc, da_subject))
    return loi, canh_bao


def _gate_overflow(slides):
    """Chan copy DAI qua vung chu 30%: o co chu NHO NHAT ma khoi chu van cao
    hon TEXT_MAX_H thi truoc day no lang le tran len tren — vi pham luat 30%.
    Gio dung han va bao thua bao nhieu de vai cat bot loi."""
    probe = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    loi = []
    for i, s in enumerate(slides, start=2):
        # Slide quote dung fit rieng (_fit_quote, cung ham luc ve): chan cau QUA DAI —
        # o co chu nho nhat van cao qua 20% khung (LOW-286) hoac qua Q_LINES dong.
        if s.get("quote"):
            _f_q, q_lines, buoc, _tren, vua = _fit_quote(probe, s["quote"])
            if not vua:
                loi.append(f"slide {i}: cau quote qua dai ({len(q_lines)} dong, cao "
                           f"{buoc * len(q_lines)}px > {Q_TEXT_MAX_H}px = 20% khung o co "
                           "nho nhat) — cat cau ngan lai, chu chi duoc chiem ~20% slide")
            continue
        paras = [p.strip() for p in s["text"].split("\n\n") if p.strip()]
        _f_, _w_, _lh_, total = _fit_block(
            probe, paras, W - 2 * PAD, TEXT_MAX_H, BODY_HI, BODY_LO)
        if total > TEXT_MAX_H:
            loi.append(f"slide {i}: copy dai qua vung chu 30% (thua "
                       f"{total - TEXT_MAX_H}px o co chu nho nhat) — cat bot "
                       f"khoang {round((total - TEXT_MAX_H) / total * 100)}% chu")
    return loi


def _gate_stack_last_hidden(nhan, muc, touched):
    """LOW-215: slide ghep doc ma anh CUOI bi nen chu (mo/toi) phu gan het —
    do that slide Claude Cowork: A29 ro 0/608px, chi con mot dai mong tren mep
    den, doc ra hai manh. `touched` = y dau tien nen chu dong vao (None = khong
    phu gi). Tra ve chuoi loi hoac ""."""
    geo = muc.get("_stack_last")
    if not geo or touched is None:
        return ""
    y0, h = geo
    visible = max(0, min(touched, H, y0 + h) - max(0, y0))
    if h <= 0 or visible / h >= STACK_BOTTOM_VISIBLE_MIN:
        return ""
    return (f"{nhan}: anh ghep duoi chi con ro {visible}/{h}px "
            f"({round(visible / h * 100)}% < {round(STACK_BOTTOM_VISIBLE_MIN * 100)}%) — "
            "nền chữ của ảnh RỐI phủ gần hết. Đặt ảnh RỐI lên TRÊN trong \"images\", "
            "hoặc dùng một ảnh sạch thay cho cặp ghép.")


def _gate_count(spec: dict, cover: dict, slides: list, out: Path) -> None:
    """Ghep anh `stack` truoc, roi kiem SO SLIDE va truong bat buoc cua bia.

    Ghep phai lam TRUOC moi cong khac: sau khi ghep, `cover["image"]`/`s["image"]`
    moi tro toi tam anh THAT se ve. Tach khoi `main` o LOW-309.
    """
    _stem0 = out.with_suffix("")
    _stack_if_can(cover, "bia", f"{_stem0}")
    for i, s in enumerate(slides, start=2):
        _stack_if_can(s, f"slide {i}", f"{_stem0}_{i}")
    if not cover.get("image") or not cover.get("hook"):
        sys.exit("Thieu cover.image hoac cover.hook trong spec.")
    if not slides:
        sys.exit("Carousel can it nhat mot slide than trong 'slides'.")
    if len(slides) + 1 > 10:
        sys.exit(f"Qua nhieu slide ({len(slides)+1}). draft_write gom toi _9, "
                 "toi da 10 slide ke ca bia.")
    if len(slides) + 1 < MIN_SLIDE:
        sys.exit(f"Carousel can IT NHAT {MIN_SLIDE} slide ke ca bia (hien {len(slides)+1}). "
                 "Chuan social content chat luong (Ong Chu chot). Chia them nhip, "
                 "hoac gom them anh that — ket hop official site + magazine.")
    # Ong Chu bat loi 03/09/2026: GPT-6 Astra (flagship OpenAI) ma chi 5 slide.
    # Tin model ra mat cua hang frontier phai 7-10 slide: bang benchmark, chart,
    # gia, context, so voi doi thu, phat bieu, cai can theo doi... du nhieu tang.
    if _is_flagship(spec, cover, slides) and len(slides) + 1 < FLAGSHIP_MIN:
        sys.exit(f"Tin FLAGSHIP (model ra mat cua hang frontier) can IT NHAT "
                 f"{FLAGSHIP_MIN} slide ke ca bia (hien {len(slides)+1}). Dao them tang: "
                 "bang benchmark nguyen ven, chart, gia/context/toc do, so voi doi thu, "
                 "phat bieu lanh dao, rui ro/an toan, cai can theo doi. Chi khi Ong Chu "
                 "noi ro tin nho moi duoc ghi \"tier\": \"regular\" de bo qua.")



def _standard_text(cover: dict, slides: list, bo_qua_dau: bool) -> None:
    """Chuan hoa em-dash + chan tieng Viet mat dau TRUOC KHI ve bat cu gi.

    Sua `cover`/`slides` TAI CHO — chu da chuan hoa chinh la chu se ve.
    """
    cover["hook"] = drop_mark_forbid(cover["hook"])
    cover["label"] = drop_mark_forbid(cover.get("label", ""))
    # Bia phai co "category" (chip cyan thay ten kenh — Ong Chu chot 03/09/2026).
    cover["category"] = str(cover.get("category") or "").strip().upper()
    if not cover["category"]:
        sys.exit("Bia thieu cover.category — chip cyan tren bia la CATEGORY, khong "
                 "phai ten kenh. Goi y: " + ", ".join(CATEGORY_CALL_Y) +
                 ". Vd: {\"category\": \"MODEL RELEASE\", \"label\": \"QWEN 3.8 27B\"}")
    chunks = [("bia/hook", cover["hook"])]
    for i, s in enumerate(slides, start=2):
        if not s.get("image"):
            sys.exit(f"Slide {i} thieu image.")
        # Moi slide than la MOT trong hai: doan van ke ("text") HOAC cau trich
        # dan ("quote", kem "attrib" tuy chon). Thieu ca hai la loi.
        if s.get("quote"):
            s["quote"] = drop_mark_forbid(s["quote"])
            s["attrib"] = drop_mark_forbid(s.get("attrib", ""))
            chunks.append((f"slide {i}", s["quote"]))
            if s["attrib"]:
                chunks.append((f"slide {i}/nguon", s["attrib"]))
        elif s.get("text"):
            s["text"] = drop_mark_forbid(s["text"])
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

    loi = _gate_text(chunks, bo_qua_dau)
    if loi:
        for e in loi:
            print(f"[LOI] {e}", file=sys.stderr)
        sys.exit("Chu carousel khong dat cong chan tieng Viet. Go lai co dau, "
                 "hoac --bo-qua-dau neu that su la tieng Anh.")


def _gate_image_and_overflow(cover: dict, slides: list) -> None:
    """Cong chan anh (trung / ti le / phan giai / day sang) va copy tran 30%."""
    anh = [("bia", cover["image"], cover)] + \
          [(f"slide {i}", s["image"], s) for i, s in enumerate(slides, start=2)]
    loi_anh, canh_bao = _gate_image(anh)
    loi_chu = _gate_overflow(slides)
    for c in canh_bao:
        print(f"[CANH BAO] {c}", file=sys.stderr)
    if loi_anh or loi_chu:
        for e in loi_anh + loi_chu:
            print(f"[LOI] {e}", file=sys.stderr)
        sys.exit("Carousel khong dat cong chan anh/chu. Sua theo huong dan o tren.")


def _build_slide(cover: dict, slides: list, out: Path, stem, handle: str) -> list:
    """Ve bia + tung slide than, roi hai cong do TREN PIXEL da ve.

    Thu tu thoat giu nguyen: nen chu sai luat overlay (LOW-286) bao TRUOC anh ghep
    bi che — cai dau la loi CODE, cai sau la loi chon anh cua vai.

    Tu LOW-330 BIA cung bi do nhu slide than (`report=bao_bia`), chi khac tran dien tich.
    """
    bao_bia = {}
    build_cover(cover["image"], cover["hook"], cover.get("label", ""), str(out), handle,
                category=cover["category"], cluttered=bool(cover.get("cluttered")), report=bao_bia)
    paths = [str(out)]
    loi_ghep, loi_nen = [], []
    loi = _gate_text_background("bia", bao_bia, max_share=TEXT_BG_MAX_SHARE_COVER)
    if loi:
        loi_nen.append(loi)
    for i, s in enumerate(slides, start=2):
        p = f"{stem}_{i}.png"
        bao = {}
        if s.get("quote"):
            touched = build_body_quote(s["image"], s["quote"], s.get("attrib", ""), handle, p,
                                       cluttered=bool(s.get("cluttered")), report=bao)
        else:
            touched = build_body(s["image"], s["text"], handle, p, cluttered=bool(s.get("cluttered")),
                                 report=bao, logo_bg=s.get("logo_bg"))
        paths.append(p)
        loi = _gate_stack_last_hidden(f"slide {i}", s, touched)
        if loi:
            loi_ghep.append(loi)
        loi = _gate_text_background(f"slide {i}", bao)
        if loi:
            loi_nen.append(loi)
    if loi_nen:
        for e in loi_nen:
            print(f"[LOI] {e}", file=sys.stderr)
        sys.exit("Nen chu sai luat overlay (LOW-286) — loi code, bao Ong Chu.")
    if loi_ghep:
        for e in loi_ghep:
            print(f"[LOI] {e}", file=sys.stderr)
        sys.exit("Carousel co anh ghep bi nen chu che gan het. Sua theo huong dan o tren.")

    return paths


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
    ap.add_argument("--nen", choices=list(BACKGROUND) + list(role_spec.BACKGROUND_TONE_LEGACY_VALUES),
                    help="Bien the nen: dark (mac dinh) | light (nhan ca toi | sang cu). "
                         "Ghi de spec.background_tone")
    ap.add_argument("--bo-qua-dau", action="store_true",
                    help="Tat cong chan tieng Viet (chi khi chu THAT SU la tieng Anh)")
    a = ap.parse_args()

    raw = sys.stdin.read() if a.spec == "-" else Path(a.spec).read_text("utf-8")
    spec = json.loads(raw)

    if a.brand not in BRAND:
        sys.exit(f"Thuong hieu khong nhan ra: {a.brand}")
    b = set_brand(a.brand)
    handle = a.handle or spec.get("handle") or b["handle"]
    nen = role_spec.background_tone(a.nen) or str(spec.get("background_tone") or "dark").strip().lower()
    try:
        set_background(nen)
    except ValueError as e:
        sys.exit(f"{e}")

    cover = spec.get("cover") or {}
    slides = spec.get("slides") or []
    _gate_count(spec, cover, slides, Path(a.out))
    _standard_text(cover, slides, a.bo_qua_dau)
    _gate_image_and_overflow(cover, slides)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    stem = out.with_suffix("")            # bo .png de ghep hau to _2, _3

    paths = _build_slide(cover, slides, out, stem, handle)

    print(f"da dung {len(paths)} slide:")
    for p in paths:
        print(f"  {p}")


if __name__ == "__main__":
    main()
