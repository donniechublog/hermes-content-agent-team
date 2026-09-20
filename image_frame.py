#!/usr/bin/env python3
"""Đóng khung ảnh cho Bob bằng PIL — thay `frame.js` (audit_content_team A6).

Vi sao bo Node: ca runtime Node tren server chi de phuc vu MOT vai. package.json
cua skill url-mascot-frame keo playwright (ban Node) + sharp, trong khi Python
cua du an DA co Playwright va Pillow lam dung hai viec do. Bo di thi server het
`npm ci`, het mot he sinh thai phai nang cap rieng.

GIU NGUYEN hinh hoc cua frame.js — moi hang so o duoi chep tu do, khong lam tron
lai theo y minh. Mot khung donniechu.com: the kem, bong den cung (hard offset),
thanh tieu de kieu macOS; anh giu nguyen ti le, canvas co gian theo anh.

  header : ba cham macOS (trai) + @handle (phai)
  anh    : ti le goc, bo tron, KHONG vien rieng
  footer : dong prompt (trai) + mascot cuoi ngang mep duoi anh (phai)

KHONG khop tung pixel voi ban Node, va khong the khop:
  - `sharp.sharpen({sigma: 0.8})` va `ImageFilter.UnsharpMask` la hai cong thuc
    khac nhau, khong co tham so nao bac cau chinh xac;
  - chu do librsvg/fontconfig rasterize khac FreeType cua PIL (khu rang cua).
Cai PHAI khop la hinh hoc, mau va vi tri — `tests/test_khung_anh.py` do dung
nhung thu do bang cach dung ca hai ban roi so.
"""
import argparse
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parent
SKILL = ROOT / "hermes" / "skills" / "url-mascot-frame"
AVATARS = SKILL / "assets" / "avatars"
FONT_DIR = SKILL / "assets" / "fonts"

MAXW = 2048          # giu chi tiet (di kem sendDocument, Telegram khong nen lai)

# --- brand token, chep tu frame.js (doc tu CSS cua trang that) ---------------
BG = "#f7f5f0"
BORDER = "#0a0a0a"
COLOR_HANDLE = "#6e6e6e"
COLOR_PROMPT = "#008299"     # brand light-variant, doc duoc tren nen kem
DOTS = ("#ff5f57", "#febc2e", "#28c840")     # den giao thong macOS
K_DROP_FULL_CARD = 0.016
K_DROP_FULL_OUTSIDE = 0.014
K_SHADOW = 0.028

# Dong footer THEO BRAND. Truoc day la mot hang so cung nen moi khung Bob lam
# cho dcgr.tech deu mang tagline cua donniechublog — loai loi thuong hieu khong
# ai thay cho toi khi da dang. Handle la khoa; handle la thi KHONG co footer
# (khong muon tra ve tagline cua brand khac) va noi ra tren stderr.
FOOTER = {"@donniechublog": ">_ vibe working & agentic AI"}


def _make_full(x) -> int:
    """Lam tron NHU `Math.round` cua JS: nua lam tron LEN.

    Khong dung `round()` cua Python: no lam tron ve so CHAN (banker's rounding),
    nen round(40.5)=40 trong khi JS cho 41. Sai mot don vi o `canh` la canvas
    lech 2 pixel so voi ban Node — do duoc bang cach dung ca hai ban roi so."""
    import math
    return math.floor(x + 0.5)


def _color(s: str) -> tuple:
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) for i in (0, 2, 4))


def _font(duong_dan: Path, co: int):
    return ImageFont.truetype(str(duong_dan), co)


def avatar_wait_emoji(emoji: str) -> Path | None:
    """Avatar da ghim san cho mot emoji trong mood-palette.json, None neu khong co.

    Ban Node con doc them MASCOT_DIR (kho avatar rieng tren may tac gia). Bo han:
    thu muc do khong bao gio ton tai tren server, va `assets/avatars` di kem
    skill moi la nguon that."""
    try:
        bang = json.loads((SKILL / "assets" / "mood-palette.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    for muc in bang:
        if muc.get("emoji") == emoji and muc.get("file"):
            p = AVATARS / muc["file"]
            return p if p.exists() else None
    return None


def _about_rgb(im: Image.Image) -> Image.Image:
    """Ve RGB ma KHONG lam hong hai loai anh Bob hay nhan (audit lượt 2, N-r2-3):

    - RGBA/LA/P-co-trong-suot (logo, meme, sticker): `convert("RGB")` vut alpha,
      vung trong suot ra DEN. sharp composite giu alpha nen ban Node ra nen the
      kem — day dan len nen BG bang kenh alpha truoc.
    - I;16 (PNG 16-bit, export khoa hoc/mot so tool chup): convert("RGB") ket
      gia tri >255 thanh 255 -> anh TRANG TINH, khong loi, Bob van gui. Chia
      ve 8-bit truoc."""
    if im.mode.startswith("I"):
        im = im.point(lambda v: v / 256).convert("L")
    elif im.mode == "P" and "transparency" in im.info:
        im = im.convert("RGBA")
    if im.mode in ("RGBA", "LA"):
        nen = Image.new("RGB", im.size, _color(BG))
        nen.paste(im.convert("RGBA"), mask=im.getchannel("A"))
        return nen
    return im.convert("RGB")


def line_frame(nguon, out_path, emoji: str = "", handle: str = "@donniechublog",
               footer: str | None = None, avatar=None, khong_mascot: bool = False) -> dict:
    """Dong khung mot anh. Tra ve dict mo ta y nhu frame.js in ra."""
    im = Image.open(nguon)
    try:
        from PIL import ImageOps
        im = ImageOps.exif_transpose(im)          # sharp().rotate() theo EXIF
    except Exception:                             # noqa: BLE001
        pass
    im = _about_rgb(im)
    if im.width > MAXW:
        im = im.resize((MAXW, _make_full(im.height * MAXW / im.width)), Image.Resampling.LANCZOS)
    # Unsharp nhe — bu lai do net mat khi thu nho. KHONG khop chinh xac
    # `sharp.sharpen({sigma: 0.8})`; xem docstring dau tep.
    im = im.filter(ImageFilter.UnsharpMask(radius=0.8, percent=100, threshold=0))

    W, H = im.size
    ngan = min(W, H)
    R = _make_full

    # --- hinh hoc (chep tu frame.js, khong doi mot he so nao) ---
    canh = R(ngan * 0.045)
    header_h = R(ngan * 0.05)
    footer_h = R(ngan * 0.05)
    bo_tron = max(8, R(ngan * K_DROP_FULL_CARD))
    bo_tron_ngoai = max(6, R(ngan * K_DROP_FULL_OUTSIDE))
    day = max(2, R(ngan * 0.005))
    khe_tren = R(ngan * 0.02)
    the_w = W + canh * 2
    the_h = H + header_h + khe_tren + footer_h
    bong = R(ngan * K_SHADOW)
    CW, CH = the_w + bong, the_h + bong
    anh_top = header_h + khe_tren

    # VE LOP VECTOR O 4x ROI THU NHO. PIL khong khu rang cua cho duong/hinh,
    # nen ve thang o 1x thi goc bo tron va vach ngan ra canh CUNG, trong re hon
    # han ban Node (librsvg co khu rang cua). Do duoc: truoc khi lam vay, rieng
    # goc bo tron da lech 1479 pixel so voi ban Node. Anh nguon va mascot dan o
    # 1x SAU khi thu nho, de khong bi lay mau lai hai lan.
    N = 4
    lop = Image.new("RGB", (CW * N, CH * N), _color(BG))
    d = ImageDraw.Draw(lop)
    # Bong den cung: mot the den lech xuong duoi-phai.
    d.rounded_rectangle([bong * N, bong * N, (bong + the_w) * N - 1, (bong + the_h) * N - 1],
                        radius=bo_tron_ngoai * N, fill=_color(BORDER))
    # The kem + vien den. SVG ve net GIUA duong (straddle): frame.js dat rect o
    # x=thick/2 nen net phu [0, thick). PIL ve net VAO TRONG hop, nen phai dua
    # hop ra sat mep (0) moi trung — lui nua do day nhu SVG la lech 2,5px, do
    # duoc bang cach lay mau pixel (1, 200) tren ca hai ban.
    d.rounded_rectangle([0, 0, the_w * N - 1, the_h * N - 1], radius=bo_tron_ngoai * N,
                        fill=_color(BG), outline=_color(BORDER), width=day * N)
    # Vach ngan duoi thanh tieu de — ve bang hinh chu nhat de bam dung dai
    # [header_h - day/2, header_h + day/2) nhu net SVG.
    d.rectangle([0, (header_h - day / 2) * N, the_w * N - 1, (header_h + day / 2) * N - 1],
                fill=_color(BORDER))

    # --- header: ba cham + @handle ben phai ---
    cham_d = max(6, R(header_h * 0.50))
    cham_r = cham_d / 2
    cham_khe = R(cham_d * 0.7)
    cham_cy = R(header_h / 2)
    for i, mau in enumerate(DOTS):
        cx = canh + cham_r + i * (cham_d + cham_khe)
        d.ellipse([(cx - cham_r) * N, (cham_cy - cham_r) * N,
                   (cx + cham_r) * N, (cham_cy + cham_r) * N],
                  fill=_color(mau), outline=_color(BORDER), width=max(1, R(day / 2)) * N)

    co_header = R(header_h * 0.50)
    # SVG dat `y` o DUONG CO SO (baseline). PIL dung anchor "ls"/"rs" = baseline.
    day_header = R(header_h / 2 + co_header * 0.35)
    _text_space(d, (the_w - canh) * N, day_header * N, handle,
              _font(FONT_DIR / "JetBrainsMono-Bold.ttf", co_header * N),
              _color(COLOR_HANDLE), gian=0.3 * N, ve_phai=True)

    # --- footer: dong prompt ---
    prompt = FOOTER.get(handle, "") if footer is None else footer
    if not prompt and footer is None:
        print(f"[khung] khong co dong footer cho {handle} — dung khung khong co no. "
              f"Them vao FOOTER trong image_frame.py, hoac truyen --footer \"<dong>\".",
              file=sys.stderr)
    if prompt:
        co_footer = R(footer_h * 0.62)
        day_footer = the_h - R(footer_h / 2) + R(co_footer * 0.35)
        d.text((canh * N, day_footer * N), prompt,
               font=_font(FONT_DIR / "JetBrainsMono-Regular.ttf", co_footer * N),
               fill=_color(COLOR_PROMPT), anchor="ls")

    khung = lop.resize((CW, CH), Image.Resampling.LANCZOS)

    # --- anh nguon: bo tron, KHONG vien, tha noi trong the (dan o 1x) ---
    mat_na = Image.new("L", (W * N, H * N), 0)
    ImageDraw.Draw(mat_na).rounded_rectangle([0, 0, W * N - 1, H * N - 1],
                                             radius=bo_tron * N, fill=255)
    khung.paste(im, (canh, anh_top), mat_na.resize((W, H), Image.Resampling.LANCZOS))

    # --- mascot: cuoi NGANG mep duoi anh, goc duoi-phai ---
    da_chon = None
    if not khong_mascot:
        p_av = Path(avatar) if avatar else (avatar_wait_emoji(emoji) if emoji else None)
        if p_av and Path(p_av).exists():
            da_chon = Path(p_av)
            av = Image.open(p_av).convert("RGBA")
            cao = R(ngan * 0.16)
            av = av.resize((_make_full(av.width * cao / av.height), cao), Image.Resampling.LANCZOS)
            mep = the_h - footer_h                 # mep duoi anh = dinh footer
            khung.paste(av, (max(0, the_w - canh - av.width), max(0, mep - R(av.height / 2))), av)
        elif emoji:
            print(f'[khung] khong co mascot cho emoji "{emoji}", dung khung khong mascot.',
                  file=sys.stderr)

    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    khung.save(out_path)
    return {"out": str(out_path), "frame": "donnie",
            "canvas": {"width": CW, "height": CH},
            "source": {"width": W, "height": H},
            "emoji": emoji or None,
            "avatar": da_chon.name if da_chon else None,
            "handle": handle}


def _text_space(d, x, y, chu, font, mau, gian=0.0, ve_phai=False):
    """Ve chu co letter-spacing. PIL khong co san nen ve tung ky tu.

    frame.js dat letter-spacing 0.3 cho @handle; bo qua thi chu ngan hon ban
    Node va lech khoi mep phai."""
    if not chu:
        return
    rong = sum(d.textlength(c, font=font) + gian for c in chu) - gian
    cx = x - rong if ve_phai else x
    for c in chu:
        d.text((cx, y), c, font=font, fill=mau, anchor="ls")
        cx += d.textlength(c, font=font) + gian


def main() -> int:
    ap = argparse.ArgumentParser(description="Dong khung anh thuong hieu cho Bob (thay frame.js)")
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", default="framed.png")
    ap.add_argument("--emoji", default="")
    ap.add_argument("--avatar", default="")
    ap.add_argument("--handle", default="@donniechublog")
    ap.add_argument("--footer", default=None)
    ap.add_argument("--no-mascot", action="store_true")
    a = ap.parse_args()
    # Console Windows hay dung codepage cu (cp1252): in JSON co emoji la
    # UnicodeEncodeError, tuc anh DA dung xong ma lenh van bao that bai.
    for _s in (sys.stdout, sys.stderr):
        # `reconfigure` chi co tren TextIOWrapper; stdout co the da bi thay bang
        # StringIO (test) hoac mot ong khac — hoi truoc thay vi de except nuot.
        doi = getattr(_s, "reconfigure", None)
        if doi is not None:
            try:
                doi(errors="replace")
            except (ValueError, OSError):
                pass
    if not Path(a.image).exists():
        print(f"Image not found: {a.image}", file=sys.stderr)
        return 1
    mo_ta = line_frame(a.image, a.out, emoji=a.emoji, handle=a.handle, footer=a.footer,
                       avatar=a.avatar or None, khong_mascot=a.no_mascot)
    print(json.dumps(mo_ta, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
