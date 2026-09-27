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
LOW-341 hoac anh chup + nen mo), nen chu = OVERLAY TRONG KHUNG cua the Ethan (xem build), neo tu
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

sys.path.insert(0, str(Path(__file__).resolve().parent))
import card                                                   # noqa: E402
import carousel                                               # noqa: E402
import safe_zone                                              # noqa: E402
from card import _f, _wrap, F_QUOTE, F_QUOTE_REG              # noqa: E402

W, H = carousel.W, carousel.H
FRAME_X, TEXT_X, TEXT_W = carousel.Q_FRAME_X, carousel.Q_TEXT_X, carousel.Q_AVAIL
# 19% (256px), khong phai tron 20%: tu 27/09 o phu (overlay trong khung) phu CA khung quote — ke
# ca khoang dem BOX_PAD_Y tren/duoi chu — nen dinh vung doi anh la dinh khung. Voi 270px, tieu de
# 3 dong day dinh khung len 43% khung, vuot tran LOW-286 (42%, `_gate_text_background`).
TEXT_MAX_H = round(H * 0.19)
TITLE_HI, TITLE_LO = 56, 36           # tieu de trong khung (quote Dre: 60/38)
TITLE_MAX_LINES = 3
SUMMARY_HI, SUMMARY_LO = 32, 26
# Tom tat duoi co nay la doc khong ra tren dien thoai; chi xuong toi SUMMARY_LO khi ha tieu de
# het muc van khong vua (do 25/09, bao cao Vera: tieu de to ep tom tat xuong 26px).
SUMMARY_PREFERRED = 30
SUMMARY_GAP_SIZE = 8                  # tom tat nho hon tieu de it nhat chung nay px
TITLE_LEAD = carousel.Q_LEAD          # gian dong tieu de = gian dong quote Dre (px)
SUMMARY_LEAD = 10                     # gian dong tom tat (px)
BOX_PAD_Y = 52                        # khung cao hon chu (Dre 62; 52 de o phu CA khung duoi tran LOW-286)
FRAME_SUMMARY_GAP = 20                # dau dong ngoac (Q_FRAME_DROP duoi khung) -> dong tom tat dau
CHIP_INSET = 24                       # chip ten kenh thut vao tu canh phai khung (= build_body_quote)
BOX_RADIUS = 30                       # bo goc o phu = ban kinh goc cua card._quote_frame
SUMMARY_BOX_PAD = 16                  # o phu tom tat rong hon chu tom tat chung nay px (tren/duoi)


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


def summary_box(canvas, box, dark: bool):
    """O phu tom tat: cung cach ve voi `card._text_box_overlay` (mo trong o + mot lop mot mau
    alpha TEXT_BOX_OPACITY, bo goc) nhung TONG do nguoi goi chon — lay theo o quote. Tra mau chu."""
    from PIL import ImageFilter
    x0, y0, x1, y1 = card._within_card(canvas, box)
    mask = Image.new("L", canvas.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle([x0, y0, x1, y1], radius=BOX_RADIUS, fill=255)
    canvas.paste(canvas.filter(ImageFilter.GaussianBlur(card.QUOTE_BLUR)), (0, 0), mask)
    tone = tuple(card.BG[:3]) if dark else tuple(card.FG[:3])
    mask = mask.point(lambda v: card.TEXT_BOX_OPACITY if v else 0)
    canvas.paste(Image.new(canvas.mode, canvas.size, tone + ((255,) if canvas.mode == "RGBA" else ())),
                 (0, 0), mask)
    return card.FG if dark else card.BG


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
    base, flat, hop, _ = carousel._place_image(canvas, carousel._open(img_path), plan,
                                               g["frame_top"] - carousel.Q_MARK_CLEAR, g["summary_bottom"])
    truoc_nen = canvas.copy() if report is not None else None
    if flat:
        pal = carousel._flat_palette(flat)
        fg = fg_sum = pal["fg"]
        net = pal["net"]
    else:
        # NEN CHU = OVERLAY TRONG KHUNG cua the quote Ethan (LOW-336, Ong Chu chot A/B 12 the:
        # "Overlay trong khung la style dat chuan"): MOT lop mot mau phang, bo goc, dung trong
        # khung quote; ngoai khung anh giu sac. Ong Chu 27/09/2026 bac dai toi chay het be
        # ngang cua slide than Dre (`_layer_if_can`) tren the Hiro: *"the quote ko duoc co lop
        # nen nhin thieu tham my nhu vay"*. Tom tat (ngoai khung) mot o phu cung kieu, rieng.
        fg = card._text_box_overlay(canvas, (FRAME_X, g["frame_top"], W - FRAME_X, g["frame_bottom"]),
                                    BOX_RADIUS)
        # O tom tat CUNG TONG voi o quote (dung lai lua chon sang/toi cua o quote), khong tu chon
        # lai theo anh ben duoi: dung that 27/09 slide TSMC ra o quote SANG + o tom tat TOI.
        fg_sum = summary_box(canvas, (FRAME_X, g["summary_top"] - SUMMARY_BOX_PAD,
                                      W - FRAME_X, g["summary_bottom"] + SUMMARY_BOX_PAD),
                             dark=fg == card.FG)
        net = carousel._net()
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
        bao = {}
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
