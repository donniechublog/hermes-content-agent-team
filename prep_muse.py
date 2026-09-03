#!/usr/bin/env python3
"""Chuan bi anh thuc cho carousel Muse Spark 1.3 -> canvas 1080x1350 (4:5).
Chi CROP/COVER tu anh that; bench co them vung den phia duoi (canvas) de cho
doan text do be kiem no che vao bang so lieu (khong phai ve minh hoa).
Vung den = giu nguyen bang + them dieu dor ro text. Anh khong thay ba lan.
"""
import sys
from pathlib import Path
from PIL import Image, ImageOps

OUT = Path("drafts/src_muse")
SZ = (1080, 1350)  # 4:5

def cover(img, cx=0.5, cy=0.5):
    w, h = img.size
    tw, th = SZ
    sw, sh_ = tw / w, th / h
    s = max(sw, sh_)          # cover: tran de lo vung thieu
    nw, nh = round(w * s), round(h * s)
    x = int(cx * (nw - tw))
    y = int(cy * (nh - th))
    im2 = img.resize((nw, nh), Image.LANCZOS).crop((x, y, x + tw, y + th))
    return im2

src = {
    "src_cover.png": ("felloai_hero.webp", dict(cx=0.42, cy=0.5)),
    "src_num.png":   ("NEVERBENCH", dict()),     # handle rieng phia duoi
    "src_zuck.png":  ("unite_hero.png", dict(cx=0.5, cy=0.45)),
    "src_term.png":  ("musecodes_og.jpg", dict(cx=0.5, cy=0.4)),
    "src_agent.png": ("silicon_demo.png", dict(cx=0.5, cy=0.42)),
    "src_banner.png":("meta_banner.webp", dict(cx=0.5, cy=0.5)),
}

for out_name, (fname, opts) in src.items():
    if out_name == "src_num.png":
        continue
    im = Image.open(OUT / fname).convert("RGB")
    canvas = cover(im, **opts)
    canvas.save(OUT / out_name)
    print(out_name, "from", fname, "->", canvas.size)

# ---- rieng bench: giu nguyen bang do rong 1080, them vung den phia duoi den
# du canvas 4:5; bang nam goi tren cung, khong mat hang so lieu.
b = Image.open(OUT / "bench_table.png").convert("RGB")
# bench la 1080x970: bảng vua dung be ngang, chỉ can day den thanh 1350
canvas = Image.new("RGB", SZ, (0, 0, 0))
canvas.paste(b, (0, 0))
canvas.save(OUT / "src_num.png")
print("src_num.png bench-> 1080x1350 (table top, den duoi text zone)")

# kiem dieu kien co ban
for p in sorted(OUT.glob("src_*.png")):
    im = Image.open(p)
    print("  ", p.name, im.size, "rat", round(im.size[0]/im.size[1],3), "short", min(im.size))
