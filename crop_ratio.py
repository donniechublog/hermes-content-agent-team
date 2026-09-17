#!/usr/bin/env python3
"""Cat mot anh ve dung ti le truoc khi dua vao carousel.

Luat cua Ong Chu: anh dung trong carousel phai la 1:1 (vuong) hoac 4:5. Tim
duoc anh dung ti le thi thoi; KHONG thi cat ve mot trong hai ti le do — dung
de carousel.py tu xoay xo. Cat CENTER theo mac dinh (giu giua khung), hoac
chi dinh tam bang --cx / --cy (ti le 0..1 theo be ngang/cao) de om dung chu the.

Dung:
    venv/bin/python crop_ratio.py --anh vao.jpg --ra ra.png            # 1:1, giua
    venv/bin/python crop_ratio.py --anh vao.jpg --ra ra.png --ti-le 4:5
    venv/bin/python crop_ratio.py --anh vao.jpg --ra ra.png --cx 0.62  # tam lech phai
"""
import argparse
import sys
from pathlib import Path

from PIL import Image

import role

RATIO = {"1:1": 1.0, "4:5": 0.8}          # rong/cao


def crop(img, ratio, cx=0.5, cy=0.5, cat_ngang=False):
    """Cat anh ve `ratio` (rong/cao), tam o (cx, cy) theo ti le 0..1. Giu
    toi da kich thuoc — chi bo phan thua o chieu vuot.

    CHIEU RONG DI TRUOC, CHIEU CAO XET SAU (Ong Chu chot 04/09/2026). Voi chart
    va bang benchmark, be ngang MANG NOI DUNG: truc, nhan chuoi, cot cuoi cung
    cua bang. Cat mot phan be ngang la cat mat du lieu, va thu con lai doc ra vo
    nghia — thay vi thieu mot ti thi no NOI SAI. Chieu cao thi khac: cat bot mep
    tren/duoi cua mot chart thuong chi mat khoang tho.

    Nen anh goc NGANG (>= nguong `LANDSCAPE_CLEAR` cua module luat vai dang
    chay, `role.active_rules()` — LOW-182, 16/09/2026) mac dinh KHONG duoc cat
    be ngang. Muon cat that thi truyen `cat_ngang=True` (CLI: --cat-ngang) va
    phai co ly do: anh chup nguoi/san pham khong co chu, crop la chon khung
    chu the."""
    w, h = img.size
    if w / h > ratio and not cat_ngang and w / h >= role.active_rules().LANDSCAPE_CLEAR:
        raise ValueError(
            f"KHONG CAT BE NGANG anh NGANG {w}x{h} ({w/h:.2f}) ve {ratio:.2f}.\n"
            "  Chart / bang benchmark / slide co tieu de: be ngang la NOI DUNG\n"
            "  (truc, nhan chuoi, cot cuoi cua bang). Cat di thi thu con lai\n"
            "  khong phai thieu mot ti — no NOI SAI. Luat: full be ngang truoc,\n"
            "  chieu cao xet sau.\n"
            "  - Carousel: dua thang anh GOC vao slide than voi \"chart\": true\n"
            "    (carousel.py dan full be ngang nguyen ven), hoac tim them mot\n"
            "    anh ngang cung tone roi ghi \"images\": [a, b] de ghep DOC.\n"
            "  - Hero/quote: dua thang anh goc vao --image, hoac --image2 de ghep doc.\n"
            "  - That su la anh chup nguoi/san pham KHONG co chu thi chay lai\n"
            "    voi --cat-ngang.")
    if w / h > ratio:                     # anh rong hon -> cat bot BE NGANG
        nw = round(h * ratio)
        nh = h
    else:                                 # anh cao hon -> cat bot CHIEU CAO
        nw = w
        nh = round(w / ratio)
    x = round(cx * w - nw / 2)
    y = round(cy * h - nh / 2)
    x = max(0, min(w - nw, x))            # khong tran ra ngoai anh
    y = max(0, min(h - nh, y))
    return img.crop((x, y, x + nw, y + nh))


def main():
    ap = argparse.ArgumentParser(description="Cat anh ve 1:1 hoac 4:5 cho carousel")
    ap.add_argument("--anh", required=True)
    ap.add_argument("--ra", required=True)
    ap.add_argument("--ti-le", default="1:1", choices=list(RATIO))
    ap.add_argument("--cx", type=float, default=0.5, help="tam ngang 0..1 (mac dinh giua)")
    ap.add_argument("--cy", type=float, default=0.5, help="tam doc 0..1 (mac dinh giua)")
    ap.add_argument("--cat-ngang", action="store_true",
                    help="Cho phep cat BE NGANG anh ngang (>=1.4). Chi dung voi anh "
                         "chup nguoi/san pham KHONG co chu — chart/bang thi khong.")
    # BAT BUOC (LOW-182, 16/09/2026): script chi chay tay, khong biet dang cat
    # cho vai nao de chon dung nguong NGANG cua module luat.
    ap.add_argument("--vai", required=True, choices=["ethan", "dre", "kite"],
                    help="Vai dang cat anh cho ai — chon dung module tieu chi anh")
    a = ap.parse_args()
    role.set_active_role(a.vai)

    img = Image.open(a.anh).convert("RGB")
    try:
        out = crop(img, RATIO[a.ti_le], a.cx, a.cy, cat_ngang=a.cat_ngang)
    except ValueError as e:
        sys.exit(str(e))
    Path(a.ra).parent.mkdir(parents=True, exist_ok=True)
    # Ghi dau vet crop vao metadata PNG: carousel.py doc ra de CHAN truong hop
    # crop anh NGANG co tieu de (bang/chart/slide) — Ong Chu bat loi 03/09/2026:
    # benchmark chart bi crop mat dau/mat truc, doc ra vo nghia. Anh ngang co
    # chu thi phai GHEP DOC hai anh ("images": [a, b]), khong crop.
    if Path(a.ra).suffix.lower() != ".png":
        sys.exit("--ra phai la .png (de giu metadata crop cho carousel.py kiem).")
    import image_provenance
    from PIL.PngImagePlugin import PngInfo
    meta = PngInfo()
    meta.add_text(image_provenance.CROP_TRACE_KEY, image_provenance.crop_trace_text(
        img.size[0], img.size[1], a.ti_le, a.cx, a.cy, a.cat_ngang))
    out.save(a.ra, "PNG", pnginfo=meta)
    print(f"{img.size} -> {out.size} ({a.ti_le}) -> {a.ra}", file=sys.stderr)


if __name__ == "__main__":
    main()
