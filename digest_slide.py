#!/usr/bin/env python3
"""digest_slide.py — dung slide "ban tin van" cua Hiro (LOW-404): anh that + TIEU DE + tom tat.

Mot slide = mot headline cua researcher (Ong Chu 25/09/2026: "moi slide la anh kem voi
title va summary ngan gon"). KHONG co bia, KHONG co slide quote: bo 10 headline la 10 slide.

Dung lai DUNG cac khau cua slide than Dre trong `carousel.py` — dan anh (`_place_image`: nen
phang LOW-341 hoac anh chup + nen mo), lop overlay chi khi do tren pixel can
(`_layer_if_can`, LOW-286), cong do nen chu tren pixel (`_text_bg_report` +
`_gate_text_background`), vung an toan 1:1 (`safe_zone`, LOW-364), chip ten kenh. Chi khoi
CHU la khac: tieu de dam + tom tat thuong, thay cho mot doan van cung co.

Tran khoi chu `TEXT_MAX_H` = 20% chieu cao khung (Ong Chu 19/09/2026, LOW-286: "text chi duoc
chiem khoang 20% dien tich"). Slide Dre giu 200px (~15%) vi chi co mot doan; o day hai tang
chu nen dung tron 20%, khong hon. Khong vua o co nho nhat -> `TextOverflow`, hiro_submit bao
vai rut gon, KHONG tu cat chu.
"""
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageDraw

sys.path.insert(0, str(Path(__file__).resolve().parent))
import carousel                                               # noqa: E402
import safe_zone                                              # noqa: E402
from card import _f, _wrap, F_REG                              # noqa: E402

W, H, PAD = carousel.W, carousel.H, carousel.PAD
TEXT_MAX_H = round(H * 0.20)          # 270px — xem docstring
TITLE_HI, TITLE_LO = 50, 34
TITLE_WEIGHT = 700
TITLE_MAX_LINES = 3
SUMMARY_HI, SUMMARY_LO = 34, 26
SUMMARY_GAP_SIZE = 8                  # tom tat nho hon tieu de it nhat chung nay px
TITLE_LEAD, SUMMARY_LEAD = 1.15, 1.3
BLOCK_GAP = 0.55                      # khoang tieu de -> tom tat, theo chieu cao dong tom tat


class TextOverflow(ValueError):
    """Tieu de + tom tat khong vua TEXT_MAX_H ngay o co nho nhat."""


@dataclass
class Layout:
    title_font: object
    title_lines: list
    title_lh: int
    summary_font: object
    summary_lines: list
    summary_lh: int
    gap: int
    total: int
    ink_over: int


def fit_text(d, title: str, summary: str, max_h: int = TEXT_MAX_H) -> Layout:
    """Co lon nhat cho tieu de (toi da TITLE_MAX_LINES dong) roi tom tat, ca khoi <= max_h."""
    max_w = W - 2 * PAD
    for ts in range(TITLE_HI, TITLE_LO - 1, -2):
        tf = _f(F_REG, ts, TITLE_WEIGHT)
        tl = _wrap(d, title, tf, max_w)
        if len(tl) > TITLE_MAX_LINES:
            continue
        tlh = carousel._line_h(tf, tl, TITLE_LEAD)
        for ss in range(min(SUMMARY_HI, ts - SUMMARY_GAP_SIZE), SUMMARY_LO - 1, -2):
            sf = _f(F_REG, ss)
            sl = _wrap(d, summary, sf, max_w) if summary else []
            slh = carousel._line_h(sf, sl or ["x"], SUMMARY_LEAD)
            gap = int(slh * BLOCK_GAP) if sl else 0
            total = len(tl) * tlh + gap + len(sl) * slh
            if total <= max_h:
                ink = carousel._ink_over(sf, [sl], slh) if sl else carousel._ink_over(tf, [tl], tlh)
                return Layout(tf, tl, tlh, sf, sl, slh, gap, total, ink)
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


def build(img_path, title: str, summary: str, handle: str, out, report=None,
          cluttered: bool = False):
    """Ve mot slide ra `out`. `report` (dict) nhan so do nen chu LOW-286/LOW-341."""
    canvas = Image.new("RGBA", (W, H), (*carousel.BG, 255))
    d = ImageDraw.Draw(canvas)
    lay = fit_text(d, title, summary)
    text_top = carousel.TEXT_BASE - lay.total - lay.ink_over
    text_bottom = text_top + lay.total + lay.ink_over

    plan = carousel._flat_plan({"image": str(img_path)})
    base, flat, hop, _ = carousel._place_image(canvas, carousel._open(img_path), plan,
                                               text_top, text_bottom)
    truoc_nen = canvas.copy() if report is not None else None
    if flat:
        fg = carousel._flat_palette(flat)["fg"]      # LOW-341: doi mau chu, khong phu lop toi
    else:
        carousel._layer_if_can(canvas, base, text_top, carousel.TEXT_BASE,
                               image_cluttered=cluttered, overlay_only=True)
        fg = carousel.FG
    if report is not None:
        report.update(carousel._text_bg_report(truoc_nen, canvas))
        carousel._note_flat(report, canvas, flat, hop)

    safe_zone.gate("slide Hiro", {"text_block": (text_top, text_bottom)}, W, H)
    y = text_top
    for ln in lay.title_lines:
        d.text((PAD, y), ln, font=lay.title_font, fill=fg)
        y += lay.title_lh
    y += lay.gap
    for ln in lay.summary_lines:
        d.text((PAD, y), ln, font=lay.summary_font, fill=fg)
        y += lay.summary_lh
    carousel._watermark(canvas, handle)
    canvas.convert("RGB").save(out, "PNG")


def build_all(slides: list, out: Path, brand: str, tone: str = "dark") -> tuple[list, list]:
    """Dung ca bo: slide 1 ra `out`, slide k ra `<stem>_k.png` (dung khuon album_secondary).

    `slides`: [{"image", "title", "summary", "cluttered"?}]. Tra (duong dan, loi cong nen chu)."""
    handle = carousel.set_brand(brand)["handle"]
    carousel.set_background(tone)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    stem = out.with_suffix("")
    paths, errors = [], []
    for i, s in enumerate(slides, start=1):
        p = out if i == 1 else Path(f"{stem}_{i}.png")
        bao = {}
        build(s["image"], s["title"], s.get("summary", ""), handle, p, report=bao,
              cluttered=bool(s.get("cluttered")))
        paths.append(p)
        loi = carousel._gate_text_background(f"slide {i}", bao) or carousel._gate_flat(f"slide {i}", bao)
        if loi:
            errors.append(loi)
    return paths, errors
