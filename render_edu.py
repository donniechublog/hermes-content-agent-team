#!/usr/bin/env python3
"""render_edu.py — renderer carousel tech-editorial (role carousel.edu, vai Kite).

Biến một spec JSON thành album PNG kiểu tạp chí công nghệ: art VECTOR gốc + bộ
khung magazine (masthead, eyebrow chuyên mục, folio, hero orbit), KHÔNG ảnh thật.
Khác `carousel.py` (ảnh thật + PIL) và `deck.py` (editorial-deck): ở đây từng
slide là HTML/CSS/SVG, render bằng Chromium headless (Playwright) rồi chụp.

    venv/bin/python render_edu.py --spec spec.json --out drafts/<id>.png

Xuất ra: <out>.png (bìa) + <out>_2.png, _3.png ... <out>_N.png — đúng glob
`{id}_[0-9].png` của draft_write.py, nên tự thành album khi đăng.

Chạy TRÊN SERVER (như cả đội). Cần Chromium của Playwright:
    venv/bin/pip install playwright
    venv/bin/playwright install chromium

FONT: dùng font Vietnamese-safe có sẵn trong assets/fonts (Be Vietnam Pro cho
display+body, Noto Serif cho standfirst in nghiêng, JetBrains Mono cho nhãn/số).
Bản canvas gốc (skill carousel-edu/reference) dùng Archivo + Newsreader — để khớp
100%, thả 2 TTF đó vào assets/fonts rồi đổi bảng FONTS bên dưới. Font nhúng dạng
base64 data-URI nên Chromium headless không cần font hệ thống (tránh tofu tiếng
Việt trên server tối giản).

Spec JSON:
{
  "brand": "donniechublog",        # tuỳ chọn, mặc định theo --brand
  "section": "AI TOOLING",         # nhãn phải của masthead (mono)
  "folio": "GOOGLE ANTIGRAVITY",   # nhãn trái của folio
  "slides": [
    {"kind": "cover", "eyebrow": "GOOGLE ANTIGRAVITY · DEEP DIVE",
     "title": "Lệnh /boost biến bug khó thành lời giải chắc tay",
     "accent": "/boost",
     "standfirst": "Bên trong cách agent chia nhỏ vấn đề...",
     "byline": ["donniechublog", "Phân tích", "5 phút đọc"]},

    {"kind": "statement", "eyebrow": "BỐI CẢNH",
     "title": "Với bug khó, agent hay đoán mò", "accent": "đoán mò",
     "standfirst": "Lỗi càng phức tạp...",
     "cards": [{"num": "01", "text": "..."}, {"num": "02", "text": "..."}]},

    {"kind": "steps", "eyebrow": "CÁCH VẬN HÀNH",
     "title": "Chia để trị, rồi kiểm chứng",
     "steps": [{"title": "Tách bài toán", "desc": "..."}, ...]},

    {"kind": "loop", "eyebrow": "CƠ CHẾ",
     "title": "Chỉ bàn giao khi qua hết test", "accent": "qua hết test",
     "chips": ["Phân tích", "Sửa", "Chạy lại test"],
     "standfirst": "Còn test đỏ thì còn lặp...",
     "callout": "Kết quả: một bản fix đã được kiểm chứng bằng test."},

    {"kind": "cta", "eyebrow": "ÁP DỤNG",
     "title": "Cho bug khó & refactor rủi ro cao",
     "checks": ["...", "...", "..."],
     "readmore": {"label": "ĐỌC THÊM", "text": "“Boost deep reasoning...”"},
     "follow": "Theo dõi @donniechublog"}
  ]
}

Mọi chữ là tiếng Việt CÓ DẤU — cổng chặn dừng nếu thiếu (dùng --bo-qua-dau chỉ
khi copy thật sự là tiếng Anh). Số slide: 6..10.
"""

import argparse
import base64
import html
import json
import sys
from pathlib import Path

# tái dùng cổng chặn tiếng Việt của cả đội
import card  # noqa: E402  (cùng thư mục)

ROOT = Path(__file__).resolve().parent
FONTS_DIR = ROOT / "assets" / "fonts"

# ---- Design tokens (khớp reference bộ /boost) -----------------------------
BG      = "#0A0B0E"
PANEL   = "#14161B"
LINE    = "#262A33"
WHITE   = "#F4F6F9"
SOFT    = "#E7EAEF"
MUTED   = "#949AA6"
DIM     = "#7B828E"
CYAN    = "#2FD4E1"
VIOLET  = "#8E86F0"

W, H = 1080, 1350

# Bảng font: family-logic -> (tên file trong assets/fonts, weight, style).
# Đổi sang Archivo/Newsreader = thả TTF vào assets/fonts rồi sửa đúng dòng dưới.
FONTS = {
    "Display":   [("BeVietnamPro-Bold.ttf",    "700", "normal"),
                  ("BeVietnamPro-Regular.ttf", "400", "normal")],
    "EditSerif": [("NotoSerif.ttf",            "500", "normal")],
    "Mono":      [("JetBrainsMono-Bold.ttf",   "700", "normal"),
                  ("JetBrainsMono-Regular.ttf","500", "normal")],
}
FALLBACK = {
    "Display":   "system-ui, -apple-system, 'Segoe UI', sans-serif",
    "EditSerif": "Georgia, 'Times New Roman', serif",
    "Mono":      "ui-monospace, 'SFMono-Regular', monospace",
}


def _font_face_css():
    """Nhúng font base64 để Chromium headless không cần font hệ thống."""
    blocks = []
    thieu = []
    for fam, faces in FONTS.items():
        for fname, weight, style in faces:
            fp = FONTS_DIR / fname
            if not fp.exists():
                thieu.append(fname)
                continue
            b64 = base64.b64encode(fp.read_bytes()).decode("ascii")
            blocks.append(
                "@font-face{font-family:'%s';font-weight:%s;font-style:%s;"
                "font-display:block;src:url(data:font/ttf;base64,%s) "
                "format('truetype');}" % (fam, weight, style, b64)
            )
    if thieu:
        raise SystemExit(
            "THIEU FONT trong assets/fonts: " + ", ".join(sorted(set(thieu)))
            + "\nTai ve roi dat vao assets/fonts/, hoac sua bang FONTS trong "
              "render_edu.py cho khop font co san."
        )
    return "\n".join(blocks)


def _ff(fam):
    return f"'{fam}', {FALLBACK[fam]}"


BASE_CSS = """
*{margin:0;padding:0;box-sizing:border-box;}
.art{position:relative;width:%(W)spx;height:%(H)spx;background:%(BG)s;
  overflow:hidden;padding:80px;display:flex;flex-direction:column;
  font-family:%(DISPLAY)s;color:%(WHITE)s;}
.glow{position:absolute;pointer-events:none;}
/* masthead */
.mast{display:flex;flex-direction:row;align-items:center;gap:24px;
  position:relative;z-index:2;}
.mast-name{font-family:%(DISPLAY)s;font-weight:700;font-size:30px;
  letter-spacing:-0.5px;color:%(WHITE)s;}
.rule{flex-grow:1;height:1px;background:%(LINE)s;}
.mast-sec{font-family:%(MONO)s;font-weight:500;font-size:22px;
  letter-spacing:2px;color:%(DIM)s;}
/* eyebrow */
.eyebrow{display:flex;flex-direction:row;align-items:center;gap:14px;}
.eyebrow-bar{width:34px;height:8px;background:%(CYAN)s;display:inline-block;}
.eyebrow-txt{font-family:%(MONO)s;font-weight:700;font-size:23px;
  letter-spacing:3px;color:%(CYAN)s;}
/* headings */
.title{font-family:%(DISPLAY)s;font-weight:700;line-height:1.05;
  letter-spacing:-1.5px;color:%(WHITE)s;}
.accent{color:%(CYAN)s;}
.standfirst{font-family:%(SERIF)s;font-style:italic;font-weight:500;
  line-height:1.4;color:#B7BDC7;}
.byline{display:flex;flex-direction:row;align-items:center;gap:18px;
  font-family:%(MONO)s;font-size:22px;font-weight:500;color:%(DIM)s;}
.byline .b0{color:%(WHITE)s;}
.dot{width:4px;height:4px;border-radius:50%%;background:#4a505c;
  display:inline-block;}
/* blocks */
.mid{position:relative;z-index:2;}
.card{display:flex;flex-direction:row;align-items:center;gap:24px;
  background:%(PANEL)s;border:1px solid #23262E;border-left:5px solid %(CYAN)s;
  padding:30px 34px;}
.card-num{font-family:%(MONO)s;font-size:26px;font-weight:700;color:%(VIOLET)s;}
.card-txt{font-size:34px;line-height:1.35;color:%(SOFT)s;}
.step{display:flex;flex-direction:row;align-items:flex-start;gap:32px;
  padding:26px 0;border-top:1px solid #23262E;}
.step-num{font-family:%(MONO)s;font-size:48px;font-weight:700;color:%(CYAN)s;
  line-height:1;min-width:78px;}
.step-t{font-family:%(DISPLAY)s;font-size:42px;font-weight:700;color:%(WHITE)s;
  margin-bottom:8px;letter-spacing:-0.5px;}
.step-d{font-size:31px;font-weight:400;line-height:1.4;color:%(MUTED)s;}
.chips{display:flex;flex-direction:row;align-items:center;gap:18px;
  flex-wrap:wrap;}
.chip{font-family:%(MONO)s;font-size:29px;font-weight:700;color:%(SOFT)s;
  background:%(PANEL)s;border:1px solid #2A2E37;padding:12px 22px;}
.chip0{color:%(BG)s;background:%(CYAN)s;border:none;}
.arrow{color:%(DIM)s;font-size:32px;font-weight:800;}
.loopmark{color:%(VIOLET)s;font-size:30px;font-weight:700;}
.callout{background:%(PANEL)s;border:1px solid #23262E;border-left:5px solid %(CYAN)s;
  padding:34px 38px;font-size:34px;font-weight:600;line-height:1.45;color:%(SOFT)s;}
.check{display:flex;flex-direction:row;align-items:flex-start;gap:22px;}
.check-m{color:%(CYAN)s;font-size:38px;font-weight:800;line-height:1.1;}
.check-t{font-size:35px;font-weight:500;line-height:1.35;color:%(SOFT)s;}
.readmore{background:%(PANEL)s;border:1px solid #23262E;padding:34px 38px;}
.readmore-l{font-family:%(MONO)s;font-size:22px;font-weight:500;color:%(DIM)s;
  letter-spacing:2px;margin-bottom:14px;}
.readmore-t{font-family:%(SERIF)s;font-style:italic;font-size:36px;font-weight:500;
  color:%(WHITE)s;line-height:1.3;}
/* folio pinned bottom */
.folio{margin-top:auto;position:relative;z-index:2;}
.folio-line{height:1px;background:%(LINE)s;margin-bottom:20px;}
.folio-row{display:flex;flex-direction:row;justify-content:space-between;
  align-items:center;font-family:%(MONO)s;font-size:22px;font-weight:500;
  color:%(DIM)s;letter-spacing:1px;}
.folio-row .cy{color:%(CYAN)s;}
""" % {
    "W": W, "H": H, "BG": BG, "PANEL": PANEL, "LINE": LINE, "WHITE": WHITE,
    "SOFT": SOFT, "MUTED": MUTED, "DIM": DIM, "CYAN": CYAN, "VIOLET": VIOLET,
    "DISPLAY": _ff("Display"), "SERIF": _ff("EditSerif"), "MONO": _ff("Mono"),
}

HERO_SVG = """
<svg width="100%%" viewBox="0 0 920 470" xmlns="http://www.w3.org/2000/svg"
     style="display:block;position:relative;z-index:2;">
  <defs><radialGradient id="core" cx="50%%" cy="50%%" r="50%%">
    <stop offset="0%%" stop-color="%(CYAN)s" stop-opacity="0.9"/>
    <stop offset="100%%" stop-color="%(CYAN)s" stop-opacity="0.05"/>
  </radialGradient></defs>
  <g transform="translate(460 235)">
    <ellipse rx="380" ry="150" fill="none" stroke="%(CYAN)s" stroke-opacity="0.28" stroke-width="1.5" transform="rotate(-18)"/>
    <ellipse rx="300" ry="112" fill="none" stroke="%(VIOLET)s" stroke-opacity="0.30" stroke-width="1.5" transform="rotate(16)"/>
    <ellipse rx="200" ry="74" fill="none" stroke="%(CYAN)s" stroke-opacity="0.22" stroke-width="1.5" transform="rotate(-6)"/>
    <line x1="0" y1="0" x2="-262" y2="-70" stroke="%(CYAN)s" stroke-opacity="0.35" stroke-width="1.5"/>
    <line x1="0" y1="0" x2="252" y2="86" stroke="%(VIOLET)s" stroke-opacity="0.35" stroke-width="1.5"/>
    <line x1="0" y1="0" x2="150" y2="-118" stroke="%(CYAN)s" stroke-opacity="0.30" stroke-width="1.5"/>
    <circle cx="-262" cy="-70" r="20" fill="%(BG)s" stroke="%(CYAN)s" stroke-width="2"/>
    <circle cx="-262" cy="-70" r="6" fill="%(CYAN)s"/>
    <circle cx="252" cy="86" r="20" fill="%(BG)s" stroke="%(VIOLET)s" stroke-width="2"/>
    <circle cx="252" cy="86" r="6" fill="%(VIOLET)s"/>
    <circle cx="150" cy="-118" r="16" fill="%(BG)s" stroke="%(CYAN)s" stroke-width="2"/>
    <circle cx="150" cy="-118" r="5" fill="%(CYAN)s"/>
    <circle r="120" fill="url(#core)"/>
    <rect x="-58" y="-58" width="116" height="116" rx="26" fill="#101218" stroke="%(CYAN)s" stroke-width="2.5"/>
    <path d="M 8 -34 L -20 6 L -2 6 L -8 34 L 20 -6 L 2 -6 Z" fill="%(CYAN)s"/>
  </g>
  <g fill="%(CYAN)s" fill-opacity="0.5">
    <circle cx="70" cy="60" r="3"/><circle cx="860" cy="120" r="3"/>
    <circle cx="820" cy="400" r="3"/><circle cx="120" cy="410" r="3"/>
    <circle cx="470" cy="30" r="2.5"/>
  </g>
</svg>
""" % {"CYAN": CYAN, "VIOLET": VIOLET, "BG": BG}


# ---- helpers --------------------------------------------------------------
def esc(s):
    return html.escape(str(s), quote=True)


def accent_html(title, accent):
    """Bọc cụm nhấn trong title thành span cyan (giữ escape)."""
    t = esc(title)
    if accent:
        a = esc(accent)
        if a in t:
            t = t.replace(a, f'<span class="accent">{a}</span>', 1)
    return t


def glow(css):
    return f'<div class="glow" style="{css}"></div>'


def masthead(brand, section):
    return (f'<div class="mast"><span class="mast-name">{esc(brand)}</span>'
            f'<span class="rule"></span>'
            f'<span class="mast-sec">{esc(section)}</span></div>')


def eyebrow(text):
    return (f'<div class="eyebrow"><span class="eyebrow-bar"></span>'
            f'<span class="eyebrow-txt">{esc(text)}</span></div>')


def folio(left, n, total):
    return (f'<div class="folio"><div class="folio-line"></div>'
            f'<div class="folio-row"><span>{esc(left)}</span>'
            f'<span><span class="cy">{n:02d}</span> / {total:02d}</span></div></div>')


# ---- slide builders (mỗi cái trả về body HTML giữa .mast và .folio) -------
def s_cover(sl):
    by = sl.get("byline", [])
    bits = []
    for i, b in enumerate(by):
        if i:
            bits.append('<span class="dot"></span>')
        cls = "b0" if i == 0 else ""
        bits.append(f'<span class="{cls}">{esc(b)}</span>')
    byline = f'<div class="byline">{"".join(bits)}</div>' if by else ""
    g = (glow(f"top:40px;left:50%;transform:translateX(-50%);width:900px;height:640px;"
              f"background:radial-gradient(ellipse at center,rgba(47,212,225,0.20) 0%,rgba(47,212,225,0) 60%);")
         + glow(f"top:120px;right:-80px;width:520px;height:520px;"
                f"background:radial-gradient(circle at center,rgba(142,134,240,0.16) 0%,rgba(142,134,240,0) 62%);"))
    head = (
        f'<div class="mid" style="position:relative;">'
        f'{eyebrow(sl["eyebrow"])}'
        f'<h1 class="title" style="font-size:88px;margin:24px 0 26px;">{accent_html(sl["title"], sl.get("accent"))}</h1>'
        f'<p class="standfirst" style="font-size:38px;margin-bottom:30px;max-width:860px;">{esc(sl["standfirst"])}</p>'
        f'{byline}</div>'
    )
    hero = f'<div style="margin:8px 0;">{HERO_SVG}</div>'
    return g + hero + head


def s_statement(sl):
    cards = ""
    for c in sl.get("cards", []):
        cards += (f'<div class="card"><span class="card-num">{esc(c["num"])}</span>'
                  f'<span class="card-txt">{esc(c["text"])}</span></div>')
    cards_wrap = (f'<div style="display:flex;flex-direction:column;gap:20px;'
                  f'position:relative;z-index:2;margin-top:44px;">{cards}</div>') if cards else ""
    g = glow("bottom:-120px;right:-120px;width:560px;height:560px;"
             "background:radial-gradient(circle at center,rgba(142,134,240,0.14) 0%,rgba(142,134,240,0) 62%);")
    body = (
        f'<div class="mid" style="margin-top:52px;">'
        f'{eyebrow(sl["eyebrow"])}'
        f'<h1 class="title" style="font-size:78px;margin:36px 0 40px;">{accent_html(sl["title"], sl.get("accent"))}</h1>'
        f'<p class="standfirst" style="font-size:40px;max-width:880px;">{esc(sl["standfirst"])}</p>'
        f'</div>{cards_wrap}'
    )
    return g + body


def s_steps(sl):
    rows = ""
    for i, st in enumerate(sl.get("steps", []), start=1):
        rows += (f'<div class="step"><span class="step-num">{i:02d}</span>'
                 f'<div style="flex-grow:1;padding-top:4px;">'
                 f'<div class="step-t">{esc(st["title"])}</div>'
                 f'<div class="step-d">{esc(st["desc"])}</div></div></div>')
    g = glow("top:-100px;right:-120px;width:520px;height:520px;"
             "background:radial-gradient(circle at center,rgba(47,212,225,0.13) 0%,rgba(47,212,225,0) 62%);")
    body = (
        f'<div class="mid" style="margin-top:46px;">'
        f'{eyebrow(sl["eyebrow"])}'
        f'<h1 class="title" style="font-size:80px;margin:24px 0 8px;">{accent_html(sl["title"], sl.get("accent"))}</h1>'
        f'</div>'
        f'<div class="mid" style="margin-top:38px;">{rows}'
        f'<div style="border-bottom:1px solid #23262E;"></div></div>'
    )
    return g + body


def s_loop(sl):
    chips = ""
    items = sl.get("chips", [])
    for i, c in enumerate(items):
        if i:
            chips += '<span class="arrow">&rarr;</span>'
        chips += f'<span class="chip {"chip0" if i == 0 else ""}">{esc(c)}</span>'
    chips += '<span class="loopmark">&#8635;</span>'
    callout = (f'<div class="callout" style="margin-top:0;">{esc(sl["callout"])}</div>'
               if sl.get("callout") else "")
    g = glow("top:200px;left:-120px;width:520px;height:520px;"
             "background:radial-gradient(circle at center,rgba(47,212,225,0.12) 0%,rgba(47,212,225,0) 62%);")
    body = (
        f'<div class="mid" style="margin-top:40px;">'
        f'{eyebrow(sl["eyebrow"])}'
        f'<h1 class="title" style="font-size:80px;margin:32px 0 44px;">{accent_html(sl["title"], sl.get("accent"))}</h1>'
        f'<div class="chips" style="margin-bottom:44px;">{chips}</div>'
        f'<p class="standfirst" style="font-size:40px;max-width:900px;">{esc(sl["standfirst"])}</p>'
        f'</div>'
        f'<div class="mid" style="margin-top:44px;">{callout}</div>'
    )
    return g + body


def s_cta(sl):
    checks = ""
    for c in sl.get("checks", []):
        checks += (f'<div class="check"><span class="check-m">&check;</span>'
                   f'<span class="check-t">{esc(c)}</span></div>')
    checks_wrap = (f'<div style="display:flex;flex-direction:column;gap:26px;">{checks}</div>'
                   if checks else "")
    rm = sl.get("readmore")
    readmore = (f'<div class="readmore" style="margin-top:40px;">'
                f'<div class="readmore-l">{esc(rm["label"])}</div>'
                f'<div class="readmore-t">{esc(rm["text"])}</div></div>') if rm else ""
    g = glow("top:80px;right:-100px;width:540px;height:540px;"
             "background:radial-gradient(circle at center,rgba(142,134,240,0.15) 0%,rgba(142,134,240,0) 62%);")
    body = (
        f'<div class="mid" style="margin-top:40px;">'
        f'{eyebrow(sl["eyebrow"])}'
        f'<h1 class="title" style="font-size:76px;margin:32px 0 48px;">{accent_html(sl["title"], sl.get("accent"))}</h1>'
        f'{checks_wrap}</div>'
        f'<div class="mid">{readmore}</div>'
    )
    return g + body


BUILDERS = {
    "cover": s_cover, "statement": s_statement, "steps": s_steps,
    "loop": s_loop, "cta": s_cta,
}


def slide_doc(sl, idx, total, brand, section, folio_left, font_css, follow=None):
    kind = sl.get("kind")
    if kind not in BUILDERS:
        raise SystemExit(f"slide {idx}: kind khong hop le '{kind}' "
                         f"(chon: {', '.join(BUILDERS)})")
    body = BUILDERS[kind](sl)
    # slide cta có thể ghi 'follow' vào folio trái thay nhãn mặc định
    fol_left = sl.get("follow", follow) if kind == "cta" and (sl.get("follow") or follow) else folio_left
    inner = masthead(brand, section) + body + folio(fol_left, idx, total)
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>'
            f'{font_css}{BASE_CSS}</style></head><body>'
            f'<div class="art">{inner}</div></body></html>')


# ---- cổng chặn ------------------------------------------------------------
def gate_slides(slides, bo_qua_dau):
    loi = []
    n = len(slides)
    if n < 6:
        loi.append(f"Chi co {n} slide — toi thieu 6 (paper dai, edu can du y).")
    if n > 10:
        loi.append(f"Co {n} slide — toi da 10 (draft_write gom hut qua do).")
    if slides and slides[0].get("kind") != "cover":
        loi.append("Slide 1 phai la kind 'cover' (bia).")
    if not bo_qua_dau:
        for i, sl in enumerate(slides, 1):
            for nhan, t in _texts(sl):
                mat = card.tim_mat_dau(t)
                if mat:
                    loi.append(f"slide {i} [{nhan}]: tieng Viet mat dau ({', '.join(mat)})")
    return loi


def _texts(sl):
    """(nhan, chuoi) mọi trường chữ cần soi dấu."""
    out = []
    for k in ("eyebrow", "title", "standfirst", "callout"):
        if sl.get(k):
            out.append((k, sl[k]))
    for c in sl.get("cards", []):
        out.append(("card", c.get("text", "")))
    for st in sl.get("steps", []):
        out.append(("step.title", st.get("title", "")))
        out.append(("step.desc", st.get("desc", "")))
    for c in sl.get("chips", []):
        out.append(("chip", c))
    for c in sl.get("checks", []):
        out.append(("check", c))
    if sl.get("readmore"):
        out.append(("readmore", sl["readmore"].get("text", "")))
    return out


# ---- render ---------------------------------------------------------------
def render(spec, out, brand, bo_qua_dau, scale):
    brand = spec.get("brand") or brand   # spec ghi brand thi thang co --brand
    slides = spec.get("slides") or []
    loi = gate_slides(slides, bo_qua_dau)
    if loi:
        print("CONG CHAN DUNG:", file=sys.stderr)
        for x in loi:
            print("  - " + x, file=sys.stderr)
        raise SystemExit(1)

    section = spec.get("section", "AI TOOLING")
    # Thieu folio thi dung ten brand — truoc day roi ve nhan mau "GOOGLE
    # ANTIGRAVITY" cua bo demo, lot len album that ma khong ai bao.
    folio_left = spec.get("folio") or brand
    total = len(slides)
    # Nhung font mot lan cho ca album — truoc day encode lai ~1.4MB TTF moi slide.
    font_css = _font_face_css()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit(
            "Thieu Playwright. Tren server:\n"
            "  venv/bin/pip install playwright\n"
            "  venv/bin/playwright install chromium")

    out = Path(out)
    stem = out.with_suffix("")
    outs = []
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        ctx = browser.new_context(viewport={"width": W, "height": H},
                                  device_scale_factor=scale)
        page = ctx.new_page()
        for i, sl in enumerate(slides, start=1):
            doc = slide_doc(sl, i, total, brand, section, folio_left, font_css)
            page.set_content(doc, wait_until="load")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(120)
            path = out if i == 1 else Path(f"{stem}_{i}.png")
            page.screenshot(path=str(path),
                            clip={"x": 0, "y": 0, "width": W, "height": H})
            outs.append(path)
        browser.close()
    return outs


def main():
    ap = argparse.ArgumentParser(description="Renderer carousel.edu (vai Kite)")
    ap.add_argument("--spec", required=True, help="file JSON, hoac '-' doc stdin")
    ap.add_argument("--out", required=True, help="drafts/<id>.png (bia)")
    ap.add_argument("--brand", default="donniechublog",
                    choices=["donniechublog", "dcgr"])
    ap.add_argument("--bo-qua-dau", action="store_true",
                    help="chi khi copy that su la tieng Anh")
    ap.add_argument("--scale", type=int, default=2,
                    help="device scale factor (2 = 2160x2700, net hon)")
    a = ap.parse_args()

    raw = sys.stdin.read() if a.spec == "-" else Path(a.spec).read_text("utf-8")
    spec = json.loads(raw)
    spec.setdefault("brand", a.brand)

    outs = render(spec, a.out, a.brand, a.bo_qua_dau, a.scale)
    print("Da dung " + str(len(outs)) + " slide:")
    for p in outs:
        print("  " + str(p))


if __name__ == "__main__":
    main()
