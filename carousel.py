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

# Vung anh cua slide than. Anh bam MEP TREN va HAI CANH (full be ngang), day
# anh TAN dan vao nen den — khong co duong ngang chia "vung anh" voi "vung chu".
# Ca the la mot mat phang den lien: anh o tren, tan vao den, chu nam tren den do.
# Tuyet doi khong ve vien, vach, hay khung — cai lam hai vung tach roi.
IMG_REGION_H = 860               # anh chiem tu mep tren xuong toi da day nay — 860/1350=64%, nen toi con lai 36%, duoi muc 40% da hen
# Duoi `day` (mep anh that) KHONG con pixel anh nao. Ban dau tung fade "het
# anh roi nhay thang sang mau nen dac" — ngay ca sau khi noi dai bang mot dai
# mo, van con MOT MOC ro rang la "anh (roi mo) het, tu day la mang mau dac".
# Nguoi dung van thay ro hai vung.
#
# Doi sang dung HAN cach cua card.py (_tran_anh, da chung minh chay tot cho
# hero image "kieu tran" — xem STYLE_TEXT_SPEC): KHONG co moc "het anh". Man
# toi la MOT DUONG CONG LIEN TUC bat dau tu RAT SOM — ngay trong vung anh con
# ro — dam dan len, chu khong phai "sang het muc roi toi nhanh cuoi cung".
# Nguoi xem thay chinh tam anh dang tam toi dan, khong thay mot ranh gioi.
BLUR_STRIP = 70                  # lay day nay px sat day anh lam nguon mo
BLUR_RADIUS = 46                 # do mo — du manh de khong con thay chi tiet
# Diem UON: cho man toi chuyen tu "dam dan tu 0" (con trong vung anh, uon
# cong t²) sang "dam dan len het muc" (uon cong nhe hon). Tinh theo TI LE
# `day` — anh nao cung uon dung mot nhip, khong phu thuoc anh cao hay ngang.
UON_TI_LE = 0.55
# Tu `day` di THEM chung nay px thi dat do toi toi da (255) — chu bat dau
# ngay sau do la doc duoc ro rang. Dai mo phai phu it nhat toi day.
FULL_TOI_SAU_DAY = 150
BLUR_EXT = FULL_TOI_SAU_DAY + 30  # du xa qua moc dat 255, khong ho mot khoang trong nao
TEXT_GAP = 48                    # tu mep duoi anh that (day) toi dong chu dau
TEXT_TOP = IMG_REGION_H + TEXT_GAP  # moc TRAN — anh doc du cao thi dung moc nay
TEXT_BOTTOM = 1240               # chua chu qua day nay (chua cho watermark)
# Tran RIENG cho chieu cao khoi chu, doc lap voi cho con trong. Neu chi bi
# chan boi (TEXT_BOTTOM - text_top), anh ngang (day thap) mo ra nhieu cho hon
# thi _fit_block lai chon co chu TO HON de lap day — dung nguoc voi y muon
# "chu nhe tay". Tran nay giu do day chu on dinh du anh cao hay ngang.
TEXT_MAX_H = 400                 # ~30% chieu cao khung — muc tran da hen

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


def _fade_to_black(canvas, day):
    """Man toi MOT DUONG CONG LIEN TUC tu y=0 (chu khong phai tu mot moc
    "het anh") — dung cach cua card._tran_anh, da chung minh khong de lo ranh
    gioi cho hero image. Hai doan noi nhau tai `uon` (ca hai cong thuc deu ra
    dung 90 tai do, khong nhay bac):

      y <= uon : dam dan tu 0 len 90, cong t² (cham roi nhanh dan) — day la
                 doan CON TRONG vung anh, nen chi tao mot lop toi mong, mat
                 van thay ro anh, nhung KHONG con "trong tuyet doi" o dau.
      y >  uon : dam tiep tu 90 len 255, cong t^0.85 (giam toc nhe) — dat 255
                 tai day + FULL_TOI_SAU_DAY, ngay truoc khi chu bat dau.

    Ca man luon phu KIN chieu cao the (0..H), khong chi mot doan — dung tinh
    than "anh phu kin the" cua kieu tran, ke ca phan duoi `day` gio la dai mo
    noi dai chu khong phai mot khoang trong."""
    uon = max(1, int(day * UON_TI_LE))
    full_y = day + FULL_TOI_SAU_DAY
    grad = Image.new("L", (1, H), 0)
    for y in range(H):
        if y <= uon:
            a = 90 * (y / uon) ** 2
        else:
            t = min(1.0, (y - uon) / max(1, full_y - uon))
            a = 90 + (255 - 90) * t ** 0.85
        grad.putpixel((0, y), min(255, int(a)))
    lop = Image.new("RGBA", (W, H), (*BG, 0))
    lop.putalpha(grad.resize((W, H)))
    canvas.alpha_composite(lop)


def _body_image(canvas, img):
    """Slide than: anh full be ngang, bam mep tren + hai canh, day tan vao den.

    Anh cao hon vung thi cat bot theo chieu doc (giu giua), khong bao gio de lo
    hai canh ben — cat ngang la mat noi dung, va vien den hai ben lam anh nhin
    nhu mot cai hop rieng. Anh thap hon vung thi nen den lo o duoi, van tan muot
    nen khong lo duong ngang nao.

    Tra ve `day` (mep duoi cung cua anh that, theo px) de build_body dat chu
    NGAY SAU do thay vi mot moc co dinh — anh ngang (vd chup man hinh 16:9)
    chi cao ~600px sau khi fit be ngang, con IMG_REGION_H tinh cho anh doc
    (~800px). Moc chu co dinh tung de lai mot khoang den CHET ~240px giua anh
    va chu — cong don vao thi vung toi vuot qua 50% khung, nhin nang."""
    scale = W / img.width
    nh = round(img.height * scale)
    resized = img.resize((W, nh), Image.LANCZOS)
    if nh >= IMG_REGION_H:
        top = (nh - IMG_REGION_H) // 2            # cat giua theo chieu doc
        canvas.paste(resized.crop((0, top, W, top + IMG_REGION_H)), (0, 0))
        day = IMG_REGION_H
        strip_y = top + IMG_REGION_H - BLUR_STRIP
    else:
        canvas.paste(resized, (0, 0))
        day = nh
        strip_y = max(0, nh - BLUR_STRIP)
    strip = resized.crop((0, strip_y, W, strip_y + BLUR_STRIP))

    # Noi dai chinh anh (khong phai phu mau nen) xuong duoi `day`: phong to
    # dai mong sat day roi lam mo that manh — mot dai mau/sac tiep tuc tu
    # chinh anh, khong phai mot khoi mau dac roi vao tu ben ngoai. Chi can phu
    # toi FULL_TOI_SAU_DAY (+ mot khoang an toan) — qua moc do man toi da dac
    # 255, co gi ben duoi cung khong con thay duoc nua.
    ext = strip.resize((W, BLUR_EXT), Image.LANCZOS)
    ext = ext.filter(ImageFilter.GaussianBlur(BLUR_RADIUS))
    canvas.paste(ext, (0, day))

    # Man toi la MOT duong cong lien tuc tu y=0, khong phai tu `day` — xem
    # docstring cua _fade_to_black.
    _fade_to_black(canvas, day)
    return day


# ---- Dung tung slide ------------------------------------------------------
def build_body(img_path, text, handle, out, mau_watermark=None):
    canvas = Image.new("RGBA", (W, H), (*BG, 255))
    day = _body_image(canvas, _open(img_path))
    # Anh ngang (vd chup man hinh 16:9) sau khi fit be ngang chi cao ~600px,
    # thap hon nhieu so voi IMG_REGION_H (800, tinh cho anh doc). Dat chu ngay
    # sau MEP THAT cua anh (day) thay vi mot moc co dinh — khong thi giua anh
    # va chu ho ra mot khoang den chet, cong don vao vung toi qua 50% khung.
    text_top = min(TEXT_TOP, day + TEXT_GAP)
    d = ImageDraw.Draw(canvas)
    paras = [p.strip() for p in text.split("\n\n") if p.strip()]
    max_h = min(TEXT_BOTTOM - text_top, TEXT_MAX_H)
    font, wrapped, lh, _ = _fit_block(
        d, paras, W - 2 * PAD, max_h, BODY_HI, BODY_LO)
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
