#!/usr/bin/env python3
"""digest_slide.py — dung slide "ban tin van" cua Hiro: anh that + khung QUOTE + tom tat.

Mot slide = mot headline cua researcher. KHONG co bia: bo 10 headline la 10 slide.

HAI KIEU XEN KE (LOW-420, Ong Chu 26/09/2026, gui ba bia logo Anthropic/OpenAI/Microsoft cua
Dre: *"Day cung la style can cho Hiro, se dat xen ke voi style quote"*): slide le = BIA LOGO,
dung nguyen `carousel.build_cover` (the logo nen phang, tieu de lon to mau ten hang, chip category
+ chip ten hang); slide chan = QUOTE (duoi day). Kieu theo vi tri: hiro_prepare.style_at.

KIEU QUOTE (LOW-420, Ong Chu 26/09/2026): *"Output cua Hiro nen la dang Quote cua Dre, nhung
thay vi dan mot cau trong noi dung thi phan text la tieu de tom tat. Sau do o ngoai the quote
se la summary ngan gon."* Nen:
  - TRONG khung quote (khung + dau ngoac + chip ten kenh y het `carousel.build_body_quote`):
    TIEU DE tom tat, font quote cua Dre, dau ngoac mau theo hang duoc nhac;
  - NGOAI khung, ngay duoi: TOM TAT ngan, canh trai thang voi chu trong khung.
Truoc LOW-420 slide Hiro la kieu slide THAN cua Dre (tieu de dam + tom tat, khong khung).

Dung lai DUNG cac khau cua Dre trong `carousel.py` — dan anh (`_place_image`: nen phang
LOW-341 hoac anh chup + nen mo), overlay chi khi do tren pixel can (`_layer_if_can`, neo tu
dong chu DAU nhu slide quote, LOW-286), cong do nen chu tren pixel (`_text_bg_report` +
`_gate_text_background`), vung an toan 1:1 (`safe_zone`, LOW-364).

Tran chu `TEXT_MAX_H` = 20% chieu cao khung cho CA tieu de + tom tat (LOW-286: "text chi duoc
chiem khoang 20% dien tich"; slide quote Dre cung tran 20% cho cau trich). Khong vua o co nho
nhat -> `TextOverflow`, hiro_submit bao vai rut gon, KHONG tu cat chu.

VUNG AN TOAN: ca khung quote LAN tom tat nam trong o vuong giua — tom tat la noi dung chinh,
khong phai dong nguon (dong nguon cua Dre da bo, LOW-364), nen khong duoc roi vao dai cat 1:1.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))
import card                                                   # noqa: E402
import carousel                                               # noqa: E402
import safe_zone                                              # noqa: E402
from card import _f, _wrap, F_QUOTE, F_QUOTE_REG              # noqa: E402

W, H = carousel.W, carousel.H
FRAME_X, TEXT_X, TEXT_W = carousel.Q_FRAME_X, carousel.Q_TEXT_X, carousel.Q_AVAIL
TEXT_MAX_H = round(H * 0.20)          # 270px — xem docstring
TITLE_HI, TITLE_LO = 56, 36           # tieu de trong khung (quote Dre: 60/38)
TITLE_MAX_LINES = 3
SUMMARY_HI, SUMMARY_LO = 32, 26
# Tom tat duoi co nay la doc khong ra tren dien thoai; chi xuong toi SUMMARY_LO khi ha tieu de
# het muc van khong vua (do 25/09, bao cao Vera: tieu de to ep tom tat xuong 26px).
SUMMARY_PREFERRED = 30
SUMMARY_GAP_SIZE = 8                  # tom tat nho hon tieu de it nhat chung nay px
TITLE_LEAD = carousel.Q_LEAD          # gian dong tieu de = gian dong quote Dre (px)
SUMMARY_LEAD = 10                     # gian dong tom tat (px)
BOX_PAD_Y = 62                        # khung cao hon chu (= build_body_quote)
FRAME_SUMMARY_GAP = 26                # dau dong ngoac (Q_FRAME_DROP duoi khung) -> dong tom tat dau
CHIP_INSET = 24                       # chip ten kenh thut vao tu canh phai khung (= build_body_quote)


class TextOverflow(ValueError):
    """Tieu de + tom tat khong vua TEXT_MAX_H ngay o co nho nhat."""


@dataclass
class Layout:
    title_font: object
    title_lines: list
    title_step: int
    title_ink_top: int
    summary_font: object
    summary_lines: list
    summary_step: int
    summary_ink_top: int
    total: int                        # chieu cao chu tieu de + tom tat (khong tinh khung, khoang ho)


def _layout(d, title, summary, ts, ss, max_h):
    """Layout o dung co (ts, ss), hoac None neu khong vua."""
    tf = _f(F_QUOTE, ts)
    tl = _wrap(d, title, tf, TEXT_W)
    if len(tl) > TITLE_MAX_LINES:
        return None
    t_step, t_top = card._step_line(tf, tl, TITLE_LEAD)
    sf = _f(F_QUOTE_REG, ss)
    sl = _wrap(d, summary, sf, TEXT_W) if summary else []
    s_step, s_top = card._step_line(sf, sl, SUMMARY_LEAD)
    total = t_step * len(tl) + s_step * len(sl)
    if total > max_h:
        return None
    return Layout(tf, tl, t_step, t_top, sf, sl, s_step, s_top, total)


def fit_text(d, title: str, summary: str, max_h: int = TEXT_MAX_H,
             title_max: int = TITLE_HI, summary_max: int = SUMMARY_HI) -> Layout:
    """Co lon nhat cho tieu de (toi da TITLE_MAX_LINES dong) roi tom tat, ca hai <= max_h.

    Hai luot: luot dau giu tom tat >= SUMMARY_PREFERRED (ha tieu de truoc), luot sau moi cho
    tom tat xuong SUMMARY_LO. `title_max`/`summary_max`: tran co — build_all dung de ca bo
    mot co chu (xem deck_sizes)."""
    for floor in (SUMMARY_PREFERRED, SUMMARY_LO):
        for ts in range(title_max, TITLE_LO - 1, -2):
            for ss in range(min(summary_max, ts - SUMMARY_GAP_SIZE), floor - 1, -2):
                lay = _layout(d, title, summary, ts, ss, max_h)
                if lay:
                    return lay
    raise TextOverflow(f"tieu de + tom tat cao hon {max_h}px ngay o co nho nhat "
                       f"({TITLE_LO}/{SUMMARY_LO}px) — rut gon")


def check_text(title: str, summary: str) -> str:
    """"" neu vua khung, nguoc lai mot dong loi — goi TRUOC khi dung (hiro_submit)."""
    d = ImageDraw.Draw(Image.new("RGB", (W, H)))
    try:
        fit_text(d, title, summary)
    except TextOverflow as e:
        return str(e)
    return ""


def deck_sizes(slides: list) -> tuple[int, int]:
    """(co tieu de, co tom tat) CHUNG cho moi slide QUOTE cua bo = co nho nhat ma moi slide can.

    Luot ngang mot bo ban tin, co chu nhay 50 -> 40 -> 50 giua cac slide doc ra lon xon
    (do 25/09). Mot co cho ca bo; slide chu ngan chi rong hon, khong to hon. Slide bia logo co
    co hook rieng cua `build_cover`, khong tinh o day."""
    d = ImageDraw.Draw(Image.new("RGB", (W, H)))
    lays = [fit_text(d, s["title"], s.get("summary", "")) for s in slides if s.get("style", "quote") == "quote"]
    if not lays:
        return TITLE_HI, SUMMARY_HI
    return (min(lay.title_font.size for lay in lays), min(lay.summary_font.size for lay in lays))


def geometry(lay: Layout) -> dict:
    """Toa do doc (tu DUOI len): tom tat sat day vung an toan, khung quote ngay tren. Thuan."""
    summary_h = lay.summary_step * len(lay.summary_lines)
    summary_bottom = safe_zone.bottom(W, H)
    summary_top = summary_bottom - summary_h
    frame_bottom = summary_top - FRAME_SUMMARY_GAP - carousel.Q_FRAME_DROP
    last_line_bottom = frame_bottom - BOX_PAD_Y
    first_line_top = last_line_bottom - lay.title_step * len(lay.title_lines)
    frame_top = first_line_top - BOX_PAD_Y
    return {"frame_top": frame_top, "first_line_top": first_line_top, "frame_bottom": frame_bottom,
            "summary_top": summary_top, "summary_bottom": summary_bottom}


def _contrast_p10(canvas, y0, y1):
    """(tuong phan chu TRANG, tuong phan chu DEN) o PHAN VI 10% (pixel te nhat) cua vung [y0, y1)."""
    import numpy as np
    y0, y1 = max(0, int(y0)), min(canvas.height, int(y1))
    a = np.asarray(canvas.convert("RGB").crop((0, y0, canvas.width, max(y0 + 1, y1))), dtype=np.float64) / 255.0
    a = np.where(a <= 0.03928, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)
    lum = 0.2126 * a[..., 0] + 0.7152 * a[..., 1] + 0.0722 * a[..., 2]
    return float(np.percentile(1.05 / (lum + 0.05), 10)), float(np.percentile((lum + 0.05) / 0.05, 10))


def _contrast_bg(canvas, y0, y1):
    """Mau nen GIA de chon mau chu: (0,0,0) neu chu TRANG doc tot hon, (255,255,255) neu chu DEN.
    Do THEO PIXEL, lay diem tuong phan tu te (phan vi 10%) cua moi mau chu va chon mau cao hon:
    nen xanh dam lan logo xanh nhat thi chu trang tot o nen nhung mat het tren logo (p10 1,35),
    chu den tren ca hai van >= 3,7 — dem ti le pixel >= 4,5 chon nham trang o ca nay."""
    white, black = _contrast_p10(canvas, y0, y1)
    return (0, 0, 0) if white >= black else (255, 255, 255)


# NE VUNG ROI (LOW-422, Ong Chu 30/09/2026: "ne vung"): khong con dai nen, nen khi vung chu roi vao
# cho vua sang vua toi (logo trang tren nen den) thi khong mau chu nao doc het. Thu nhieu KHUNG CAT
# (phong nhe + dich) cua anh, chon khung ma CA HAI khoi chu doc duoc nhat.
LEGIBLE_CR = 4.5             # tuong phan du doc — dat roi thi khong can phong/dich them
ZOOMS = (1.0, 1.12, 1.25, 1.4)
ZOOM_COST = 2.0              # phat tren moi 1.0 phong to (uu tien khung goc, cat it nhat)
SHIFT_COST = 0.4             # phat theo do lech khoi tam
FACE_TEXT_GAP = 12           # mat nguoi phai nam TREN dong chu dau it nhat bay nhieu px


EXT_MAX = 0.30               # keo dai day anh toi da bay nhieu phan chieu cao (de day chu the len cao)
EXT_SIMPLE_STD = 22          # chi keo dai khi day anh DON GIAN: do lech xam cua 8% hang cuoi <= muc nay
EXT_FADE = 0.06              # phan chieu cao cuoi anh chuyen dan sang mau keo dai (het moi noi)


def extend_bottom(img):
    """(anh, he so cao) — keo dai DAY anh bang chinh mau mep day cua no (khong blur, khong dai nen):
    day chu the len cao de duoi con cho cho chu (Ong Chu 30/09/2026). Chi khi day anh don gian
    (nen toi/phang); anh nhieu chi tiet o day thi giu nguyen (he so 1.0) vi keo dai se lo vet."""
    import numpy as np
    a = np.asarray(img.convert("RGB"), dtype=np.float64)
    h, w = a.shape[:2]
    if h < 20 or a[int(h * 0.92):].mean(axis=2).std() > EXT_SIMPLE_STD:
        return img, 1.0
    col = a[int(h * 0.96):].reshape(-1, 3).mean(axis=0)
    ext = round(h * EXT_MAX)
    out = np.empty((h + ext, w, 3))
    out[:h] = a
    out[h:] = col
    fade = max(2, round(h * EXT_FADE))
    ramp = np.linspace(0.0, 1.0, fade)[:, None, None]
    out[h - fade:h] = a[h - fade:h] * (1 - ramp) + col * ramp
    return Image.fromarray(out.round().astype("uint8"), "RGB"), (h + ext) / h


def _face_boxes(img_path):
    """Hop mat nguoi 0..1 hoac [] (khong do duoc: thieu cv2/model thi bo qua rang buoc mat)."""
    try:
        import image_rules_dre
        return image_rules_dre.face_boxes(img_path) or []
    except Exception:                                   # noqa: BLE001
        return []


def _windows(sw, sh, z):
    """Cac khung cat ty le W:H, phong z lan so voi khung phu kin toi thieu: [(x0, y0, w, h)]."""
    ww, wh = (sh * W / H, sh) if sw / sh > W / H else (sw, sw * H / W)
    ww, wh = ww / z, wh / z
    xs = [0.0] if sw - ww < 1 else [(sw - ww) * k / 4 for k in range(5)]
    ys = [0.0] if sh - wh < 1 else [(sh - wh) * k / 4 for k in range(5)]
    return [(x, y, ww, wh) for x in xs for y in ys]


def choose_window(img, faces, g):
    """(x0, y0, w, h) khung cat toi uu (toa do anh nguon) — thuan, khong ve. `g`: geometry(lay)."""
    src = img.convert("RGB")
    ty = 1600 / max(src.size)
    if ty < 1:
        src = src.resize((max(1, round(src.width * ty)), max(1, round(src.height * ty))), Image.Resampling.BILINEAR)
    sw, sh = src.size
    k = 0.25                                                    # cham diem tren ban 1/4 cho nhanh
    title = (g["first_line_top"] * k, g["frame_bottom"] * k)
    summ = (g["summary_top"] * k, g["summary_bottom"] * k)
    best, best_u = None, None
    for z in ZOOMS:
        for (x0, y0, ww, wh) in _windows(sw, sh, z):
            if any(not (x0 <= f[0] * sw and f[2] * sw <= x0 + ww and y0 <= f[1] * sh
                        and (f[3] * sh - y0) / wh * H <= g["first_line_top"] - FACE_TEXT_GAP)
                   for f in faces):
                continue                                        # mat bi cat hoac roi vao vung chu
            small = src.crop((round(x0), round(y0), round(x0 + ww), round(y0 + wh))).resize(
                (round(W * k), round(H * k)), Image.Resampling.BILINEAR)
            cr = min(max(_contrast_p10(small, *title)), max(_contrast_p10(small, *summ)))
            lech = (abs((x0 + ww / 2) / sw - 0.5) + abs((y0 + wh / 2) / sh - 0.5))
            u = min(cr, LEGIBLE_CR) - ZOOM_COST * (z - 1) - SHIFT_COST * lech
            if best_u is None or u > best_u:
                best, best_u = (x0 / ty if ty < 1 else x0, y0 / ty if ty < 1 else y0,
                                ww / ty if ty < 1 else ww, wh / ty if ty < 1 else wh), u
    return best or _windows(*img.size, 1.0)[len(_windows(*img.size, 1.0)) // 2]


def build(img_path, title: str, summary: str, handle: str, out, report=None,
          cluttered: bool = False, sizes: tuple | None = None):
    """Ve mot slide ra `out`. `report` (dict) nhan so do nen chu LOW-286/LOW-341.
    `sizes`: (tran co tieu de, tran co tom tat) chung ca bo — xem deck_sizes."""
    canvas = Image.new("RGBA", (W, H), (*carousel.BG, 255))
    d = ImageDraw.Draw(canvas)
    lay = fit_text(d, title, summary, *((TEXT_MAX_H,) + tuple(sizes) if sizes else ()))
    g = geometry(lay)
    safe_zone.gate("slide Hiro", {"quote_frame": (g["frame_top"] - carousel.Q_MARK_CLEAR,
                                                  g["frame_bottom"] + carousel.Q_FRAME_DROP),
                                  "summary": (g["summary_top"], g["summary_bottom"])}, W, H)

    # Nhu build_body_quote: voi anh nen phang, "dinh vung chu" la dinh dau " + chip (tren net
    # ngang tren cua khung); day vung chu la day tom tat.
    plan = carousel._flat_plan({"image": str(img_path)})
    img = carousel._open(img_path)
    if plan and plan[0]:             # nen phang (LOW-341): giu duong cu, KHONG dung nen mau "zone"
        _, flat, hop, _ = carousel._place_image(canvas, img, (plan[0], None),
                                                g["frame_top"] - carousel.Q_MARK_CLEAR, g["summary_bottom"])
    else:                            # LOW-422 (Ong Chu 30/09: "ko blur nen"): anh SAC NET phu kin khung
        flat, hop = None, None
        img, kdai = extend_bottom(img)
        faces = [[f[0], f[1] / kdai, f[2], f[3] / kdai] for f in _face_boxes(img_path)]
        x0, y0, ww, wh = choose_window(img, faces, g)
        canvas.paste(img.convert("RGB").crop((round(x0), round(y0), round(x0 + ww), round(y0 + wh)))
                     .resize((W, H), Image.Resampling.LANCZOS), (0, 0))
    truoc_nen = canvas.copy() if report is not None else None
    # LOW-422 (Ong Chu 30/09/2026: *"khong co dai nen duoi text"*, *"nen sang thi dung chu mau den"*):
    # KHONG overlay, KHONG vien/quang. Chu doi mau theo do sang THAT cua anh duoi chu (sang -> den,
    # toi -> trang), y het cach anh nen phang doi mau chu (LOW-341).
    # Tieu de (trong khung) va tom tat (ngoai khung) nam o hai vung anh khac nhau: moi khoi do mau rieng.
    ref = flat or _contrast_bg(canvas, g["first_line_top"], g["frame_bottom"])
    pal = carousel._flat_palette(ref)
    fg = pal["fg"]
    # Net khung + dau ngoac GIU MAU GOC cua quote Dre (cyan/trang theo thuong hieu) — chi doi
    # mau CHU; ai muon doi mau khung thi noi (Ong Chu 30/09: "tai sao lai thay mau duong line").
    net = pal["net"] if flat else carousel._net()
    fg_sum = pal["fg"] if flat else carousel._flat_palette(_contrast_bg(canvas, g["summary_top"], g["summary_bottom"]))["fg"]
    if report is not None:
        report.update(carousel._text_bg_report(truoc_nen, canvas))
        carousel._note_flat(report, canvas, flat, hop)

    y = g["first_line_top"]
    for ln in lay.title_lines:
        d.text((TEXT_X, y - lay.title_ink_top), ln, font=lay.title_font, fill=fg)
        y += lay.title_step
    mau_hang = card._color_rank_within(title)
    mark_col = carousel._flat_mark(mau_hang, pal) if flat else carousel._color_mark(mau_hang)
    card._quote_frame(d, FRAME_X, g["frame_top"], W - FRAME_X, g["frame_bottom"], net, mark_col)

    if handle:                       # chip ten kenh goc TREN-PHAI khung, nhu slide quote Dre
        f_wm = _f(carousel.F_MONO_CH, carousel.WM_SIZE)
        wtb = d.textbbox((0, 0), handle, font=f_wm)
        cw = (wtb[2] - wtb[0]) + 2 * 18
        ch = (wtb[3] - wtb[1]) + 2 * 10
        carousel._watermark(canvas, handle, x=W - FRAME_X - CHIP_INSET - cw, y=g["frame_top"] - ch // 2)

    y = g["summary_top"]
    for ln in lay.summary_lines:
        d.text((TEXT_X, y - lay.summary_ink_top), ln, font=lay.summary_font, fill=fg_sum)
        y += lay.summary_step
    canvas.convert("RGB").save(out, "PNG")


def build_all(slides: list, out: Path, brand: str, tone: str = "dark") -> tuple[list, list]:
    """Dung ca bo: slide 1 ra `out`, slide k ra `<stem>_k.png` (dung khuon album_secondary).

    `slides`: [{"image", "title", "summary", "style"?, "label"?, "category"?, "cluttered"?}] — `style`
    "cover" (bia logo, `carousel.build_cover`) hoac "quote" (mac dinh). Tra (duong dan, loi cong)."""
    handle = carousel.set_brand(brand)["handle"]
    carousel.set_background(tone)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    stem = out.with_suffix("")
    sizes = deck_sizes(slides)
    paths, errors = [], []
    for i, s in enumerate(slides, start=1):
        p = out if i == 1 else Path(f"{stem}_{i}.png")
        bao: dict[Any, Any] = {}
        if s.get("style") == "cover":
            # Bia logo: DUNG NGUYEN bia cua Dre — chip category + chip ten hang thay ten kenh,
            # to mau ten hang tren tieu de (LOW-344), nen phang thi doi mau chu (LOW-341).
            carousel.build_cover(s["image"], s["title"], s.get("label", ""), str(p), handle,
                                 category=s.get("category") or "BUSINESS", cluttered=bool(s.get("cluttered")),
                                 report=bao, plan=carousel._flat_plan({"image": str(s["image"])}))
            max_share = carousel.TEXT_BG_MAX_SHARE_COVER
        else:
            build(s["image"], s["title"], s.get("summary", ""), handle, p, report=bao,
                  cluttered=bool(s.get("cluttered")), sizes=sizes)
            max_share = carousel.TEXT_BG_MAX_SHARE
        paths.append(p)
        loi = (carousel._gate_text_background(f"slide {i}", bao, max_share=max_share)
               or carousel._gate_flat(f"slide {i}", bao))
        if loi:
            errors.append(loi)
    return paths, errors
