#!/usr/bin/env python3
"""render_edu.py — renderer carousel tech-editorial (role carousel.edu, vai Kite).

Biến một spec JSON thành album PNG kiểu tạp chí công nghệ: art VECTOR gốc + bộ
khung magazine (masthead, eyebrow chuyên mục, folio, hero orbit). Không đi tìm
ảnh minh hoạ, nhưng biểu đồ/bảng/báo cáo CÓ SẴN thì chèn bản thật (kind
"figure", trải hết bề ngang slide).
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
  "theme": "ember",                # tuỳ chọn: orbit|ember|moss|ink|rose — bỏ trống = tự xoay
  "hero": "grid",                  # tuỳ chọn: orbit|grid|wave|rings|graph — bỏ trống = tự xoay
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

    {"kind": "figure", "eyebrow": "SỐ LIỆU",
     "title": "Điểm số dựng lại trên SWE-bench", "accent": "SWE-bench",
     "image": "drafts/chart_swebench.png",   # chụp bằng chup_chart.py
     "caption": "Biểu đồ trong bài công bố · via Google DeepMind",
     "standfirst": "Chữ minh hoạ cho phần chiều cao còn thừa dưới hình.",
     "cards": [{"num": "01", "text": "..."}]},

    {"kind": "cta", "eyebrow": "ÁP DỤNG",
     "title": "Cho bug khó & refactor rủi ro cao",
     "checks": ["...", "...", "..."],
     "readmore": {"label": "ĐỌC THÊM", "text": "“Boost deep reasoning...”"},
     "follow": "Theo dõi @donniechublog"}
  ]
}

Mọi chữ là tiếng Việt CÓ DẤU — cổng chặn dừng nếu thiếu (dùng --bo-qua-dau chỉ
khi copy thật sự là tiếng Anh). Số slide: 6..10.

ẢNH THẬT: khung này vẽ art vector, nhưng tin nào CÓ SẴN biểu đồ, bảng số hay
trang báo cáo thì chèn bản thật bằng kind "figure" — ảnh trải hết bề ngang
slide (không bao giờ cắt hai bên: bề ngang của một biểu đồ là nội dung), cao
quá thì giữ mép trên, phần chiều cao còn thừa mới để chữ minh hoạ. Bắt buộc có
"caption" ghi "via <ai>", và ảnh phải rộng >= 800px (chụp bằng chup_chart.py).
Vẫn cấm: ảnh minh hoạ AI, screenshot dựng lại, logo hãng, số liệu tự bịa.
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

# ---- Design tokens ---------------------------------------------------------
# Mau trung tinh dung chung; MAU NHAN (CYAN/VIOLET) lay theo THEME. Truoc day
# chi co mot bo cyan x tim + mot hero "quy dao" nen moi bo Kite dung ra deu
# giong nhau (Ong Chu chê 04/09: "lam di lam lai mot tone"). Gio spec ghi
# "theme" / "hero", khong ghi thi renderer tu XOAY khac lan truoc (xem
# chon_theme_tu_dong).
BG      = "#0A0B0E"
PANEL   = "#14161B"
LINE    = "#262A33"
WHITE   = "#F4F6F9"
SOFT    = "#E7EAEF"
MUTED   = "#949AA6"
DIM     = "#7B828E"
CYAN    = "#2FD4E1"     # mac dinh (theme "orbit"); render() ghi de theo theme
VIOLET  = "#8E86F0"

# Moi theme: nen, panel, hairline, 2 mau nhan (chinh x phu), va mau standfirst.
# Tat ca deu NEN TOI + CHU SANG (luat tuong phan cua ca doi), khac nhau o hue.
THEMES = {
    "orbit":  dict(bg="#0A0B0E", panel="#14161B", line="#262A33",
                   a="#2FD4E1", b="#8E86F0", stand="#B7BDC7"),   # cyan x tim (bo /boost)
    "ember":  dict(bg="#0E0B09", panel="#1B1512", line="#33281F",
                   a="#FFB454", b="#FF6B6B", stand="#C9BFB4"),   # cam ho phach x do san ho
    "moss":   dict(bg="#090D0B", panel="#121A16", line="#22302A",
                   a="#7BE495", b="#D6F26A", stand="#B4C2B8"),   # xanh la x vang chanh
    "ink":    dict(bg="#0A0E1A", panel="#131A2B", line="#243050",
                   a="#8FB3FF", b="#F2C94C", stand="#B9C1D6"),   # xanh navy x vang
    "rose":   dict(bg="#100A10", panel="#1C1220", line="#332238",
                   a="#FF7EB6", b="#B892FF", stand="#CBB8C8"),   # hong x tim oai huong
}
HEROES = ("orbit", "grid", "wave", "rings", "graph")   # ten hero SVG tren bia

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


BASE_CSS_TPL = """
*{margin:0;padding:0;box-sizing:border-box;}
.art{position:relative;width:%(W)spx;height:%(H)spx;background:%(BG)s;
  overflow:hidden;padding:80px;display:flex;flex-direction:column;
  font-family:%(DISPLAY)s;color:%(WHITE)s;}
.glow{position:absolute;pointer-events:none;}
/* masthead */
.mast{display:flex;flex-direction:row;align-items:center;gap:24px;
  position:relative;z-index:2;}
.mast-name{font-family:%(DISPLAY)s;font-weight:500;font-size:26px;
  letter-spacing:-0.5px;color:%(DIM)s;}
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
  line-height:1.4;color:%(STAND)s;}
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
.chip-grp{display:inline-flex;flex-direction:row;align-items:center;gap:18px;}
.loopmark{color:%(VIOLET)s;font-size:30px;font-weight:700;}
.callout{background:%(PANEL)s;border:1px solid #23262E;border-left:5px solid %(CYAN)s;
  padding:34px 38px;font-size:34px;font-weight:600;line-height:1.45;color:%(SOFT)s;}
.check{display:flex;flex-direction:row;align-items:flex-start;gap:22px;}
.check-m{color:%(CYAN)s;font-size:38px;font-weight:800;line-height:1.1;}
.check-t{font-size:35px;font-weight:500;line-height:1.35;color:%(SOFT)s;}
/* dai hinh that: keo ra ngoai padding 80px de cham hai mep slide */
.fig{position:relative;z-index:2;width:%(W)spx;margin-left:-80px;
  overflow:hidden;background:%(PANEL)s;line-height:0;}
.fig img{width:100%%;height:100%%;object-fit:cover;display:block;}
.fig-cap{display:flex;flex-direction:row;align-items:baseline;gap:16px;
  margin-top:22px;font-family:%(MONO)s;font-size:23px;font-weight:500;
  line-height:1.45;color:%(DIM)s;letter-spacing:0.5px;}
.fig-bar{flex:none;width:26px;height:3px;background:%(CYAN)s;
  transform:translateY(-7px);}
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
"""


def base_css(th):
    return BASE_CSS_TPL % {
        "W": W, "H": H, "BG": th["bg"], "PANEL": th["panel"], "LINE": th["line"],
        "WHITE": WHITE, "SOFT": SOFT, "MUTED": MUTED, "DIM": DIM,
        "CYAN": th["a"], "VIOLET": th["b"], "STAND": th["stand"],
        "DISPLAY": _ff("Display"), "SERIF": _ff("EditSerif"), "MONO": _ff("Mono"),
    }


def rgba(hexs, alpha):
    h = hexs.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

_SVG_HEAD = ('<svg width="100%" viewBox="0 0 920 470" xmlns="http://www.w3.org/2000/svg"'
             ' style="display:block;position:relative;z-index:2;">')

# Hero ve trong mot khung 920x470 co hai. Cac hero co MANG TO kin khung (grid:
# luoi + dai quet; wave: vung song do bong) bi cat cut o dung bien khung, nhin ra
# mot HINH CHU NHAT dan len nen — dung luat "moi slide la mot mat phang lien".
# Mask nay lam mem bon canh, art tan dan vao nen thay vi dut ngang.
_HERO_MASK = """
  <defs>
    <filter id="heroBlur" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="30"/>
    </filter>
    <mask id="heroFade">
      <rect x="38" y="26" width="844" height="418" fill="#fff" filter="url(#heroBlur)"/>
    </mask>
  </defs>
"""

# "orbit": loi phat sang + node bay quy dao (bo /boost goc)
HERO_ORBIT = """
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
"""

# "grid": luoi toa do + mot o sang + duong quet — hop benchmark, bang so, do luong
HERO_GRID = """
  <defs><linearGradient id="sweep" x1="0" x2="1" y1="0" y2="0">
    <stop offset="0%%" stop-color="%(CYAN)s" stop-opacity="0"/>
    <stop offset="100%%" stop-color="%(CYAN)s" stop-opacity="0.55"/>
  </linearGradient></defs>
  <g stroke="%(CYAN)s" stroke-opacity="0.16" stroke-width="1.2">
    %(GRID_LINES)s
  </g>
  <rect x="0" y="0" width="920" height="470" fill="url(#sweep)" opacity="0.18"/>
  <g transform="translate(560 190)">
    <rect x="-70" y="-70" width="140" height="140" fill="%(BG)s" stroke="%(CYAN)s" stroke-width="2.5"/>
    <rect x="-42" y="-42" width="84" height="84" fill="%(CYAN)s" fill-opacity="0.85"/>
    <rect x="-70" y="-70" width="140" height="140" fill="none" stroke="%(CYAN)s" stroke-opacity="0.35" stroke-width="18"/>
  </g>
  <g fill="%(VIOLET)s">
    <rect x="200" y="330" width="46" height="46"/><rect x="330" y="80" width="46" height="46" fill-opacity="0.6"/>
    <rect x="760" y="270" width="46" height="46" fill-opacity="0.5"/>
  </g>
  <line x1="60" y1="405" x2="860" y2="405" stroke="%(VIOLET)s" stroke-opacity="0.5" stroke-width="2" stroke-dasharray="14 10"/>
"""

# "wave": ba dai song chong nhau + diem noi — hop xu huong, tin hieu, doi thay theo thoi gian
HERO_WAVE = """
  <defs><linearGradient id="wf" x1="0" x2="0" y1="0" y2="1">
    <stop offset="0%%" stop-color="%(CYAN)s" stop-opacity="0.32"/>
    <stop offset="100%%" stop-color="%(CYAN)s" stop-opacity="0"/>
  </linearGradient></defs>
  <path d="M0 300 C 150 200, 260 380, 420 250 S 700 120, 920 210 L 920 470 L 0 470 Z" fill="url(#wf)"/>
  <path d="M0 300 C 150 200, 260 380, 420 250 S 700 120, 920 210" fill="none" stroke="%(CYAN)s" stroke-width="3"/>
  <path d="M0 360 C 180 300, 300 420, 460 330 S 720 240, 920 300" fill="none" stroke="%(VIOLET)s" stroke-width="2.5" stroke-opacity="0.75"/>
  <path d="M0 220 C 160 160, 280 260, 440 190 S 700 60, 920 130" fill="none" stroke="%(CYAN)s" stroke-width="1.5" stroke-opacity="0.35" stroke-dasharray="10 12"/>
  <g>
    <circle cx="420" cy="250" r="16" fill="%(BG)s" stroke="%(CYAN)s" stroke-width="3"/>
    <circle cx="420" cy="250" r="6" fill="%(CYAN)s"/>
    <circle cx="700" cy="180" r="12" fill="%(BG)s" stroke="%(VIOLET)s" stroke-width="3"/>
    <circle cx="700" cy="180" r="4" fill="%(VIOLET)s"/>
    <circle cx="150" cy="245" r="10" fill="%(CYAN)s" fill-opacity="0.7"/>
  </g>
  <g fill="%(VIOLET)s" fill-opacity="0.5">
    <circle cx="90" cy="70" r="3"/><circle cx="840" cy="60" r="3"/><circle cx="600" cy="420" r="3"/>
  </g>
"""

# "rings": vong tron dong tam + kim chi — hop muc tieu, do chinh xac, tang lop
HERO_RINGS = """
  <defs><radialGradient id="rc" cx="50%%" cy="50%%" r="50%%">
    <stop offset="0%%" stop-color="%(VIOLET)s" stop-opacity="0.55"/>
    <stop offset="100%%" stop-color="%(VIOLET)s" stop-opacity="0"/>
  </radialGradient></defs>
  <g transform="translate(460 240)">
    <circle r="210" fill="url(#rc)"/>
    <circle r="210" fill="none" stroke="%(CYAN)s" stroke-opacity="0.2" stroke-width="1.5"/>
    <circle r="160" fill="none" stroke="%(CYAN)s" stroke-opacity="0.35" stroke-width="1.5" stroke-dasharray="6 10"/>
    <circle r="110" fill="none" stroke="%(VIOLET)s" stroke-opacity="0.55" stroke-width="2"/>
    <circle r="60" fill="none" stroke="%(CYAN)s" stroke-width="3"/>
    <circle r="14" fill="%(CYAN)s"/>
    <line x1="0" y1="0" x2="150" y2="-120" stroke="%(CYAN)s" stroke-width="2.5"/>
    <circle cx="150" cy="-120" r="9" fill="%(BG)s" stroke="%(CYAN)s" stroke-width="3"/>
    <path d="M -230 0 L -200 0 M 200 0 L 230 0 M 0 -230 L 0 -200 M 0 200 L 0 230" stroke="%(VIOLET)s" stroke-width="2" stroke-opacity="0.8"/>
  </g>
  <g fill="%(CYAN)s" fill-opacity="0.5">
    <circle cx="80" cy="80" r="3"/><circle cx="850" cy="110" r="3"/><circle cx="120" cy="400" r="3"/><circle cx="830" cy="410" r="3"/>
  </g>
"""

# "graph": mang node-canh khong deu — hop he thong, agent, quan he, so sanh nhieu ben
HERO_GRAPH = """
  <g stroke="%(CYAN)s" stroke-opacity="0.45" stroke-width="2">
    <line x1="140" y1="120" x2="380" y2="230"/><line x1="380" y1="230" x2="560" y2="110"/>
    <line x1="380" y1="230" x2="470" y2="380"/><line x1="560" y1="110" x2="790" y2="180"/>
    <line x1="470" y1="380" x2="790" y2="180"/><line x1="140" y1="120" x2="200" y2="360"/>
    <line x1="200" y1="360" x2="470" y2="380"/>
  </g>
  <line x1="560" y1="110" x2="470" y2="380" stroke="%(VIOLET)s" stroke-width="2" stroke-dasharray="8 8"/>
  <g>
    <circle cx="140" cy="120" r="18" fill="%(BG)s" stroke="%(CYAN)s" stroke-width="3"/>
    <circle cx="560" cy="110" r="18" fill="%(BG)s" stroke="%(VIOLET)s" stroke-width="3"/>
    <circle cx="790" cy="180" r="22" fill="%(BG)s" stroke="%(CYAN)s" stroke-width="3"/>
    <circle cx="470" cy="380" r="18" fill="%(BG)s" stroke="%(VIOLET)s" stroke-width="3"/>
    <circle cx="200" cy="360" r="14" fill="%(BG)s" stroke="%(CYAN)s" stroke-width="3"/>
    <circle cx="380" cy="230" r="46" fill="%(CYAN)s" fill-opacity="0.15" stroke="%(CYAN)s" stroke-width="3"/>
    <circle cx="380" cy="230" r="16" fill="%(CYAN)s"/>
    <circle cx="790" cy="180" r="7" fill="%(CYAN)s"/><circle cx="560" cy="110" r="6" fill="%(VIOLET)s"/>
  </g>
"""

HERO_TPL = {"orbit": HERO_ORBIT, "grid": HERO_GRID, "wave": HERO_WAVE,
            "rings": HERO_RINGS, "graph": HERO_GRAPH}


def hero_svg(name, th):
    grid_lines = "".join(
        f'<line x1="{x}" y1="0" x2="{x}" y2="470"/>' for x in range(60, 920, 80)
    ) + "".join(
        f'<line x1="0" y1="{y}" x2="920" y2="{y}"/>' for y in range(55, 470, 80)
    )
    body = HERO_TPL[name] % {"CYAN": th["a"], "VIOLET": th["b"], "BG": th["bg"],
                             "GRID_LINES": grid_lines}
    return (_SVG_HEAD + _HERO_MASK
            + '<g mask="url(#heroFade)">' + body + "</g></svg>")



# ---- anh that: hinh minh hoa / bieu do / bao cao --------------------------
# Luat khung edu la ART VECTOR, nhung tin nao CO SAN mot bieu do, mot bang so
# hay mot trang bao cao thi ve lai bang tay vua mat cong vua de sai — chen thang
# ban that vao. Slide kind "figure" lam viec do.
#
# Be ngang la NOI DUNG (cung luat voi chup_chart.py): mot bieu do bi cat mep
# phai thi mat truc, mat cot cuoi, mat luon cai diem duoc to sang — no NOI SAI
# chu khong phai thieu mot ti. Nen anh LUON trai het 1080px, khong bao gio cat
# hai ben. Chieu cao thi cat duoc: cao qua tran thi giu mep tren, phan con lai
# cua chieu cao slide moi den luot chu minh hoa.
ANH_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".webp": "image/webp", ".gif": "image/gif"}
FIG_CAO_TOI_DA = 700        # dai anh cao nhat, con lai danh cho eyebrow/title/chu
FIG_RONG_TOI_THIEU = 800    # hep hon the ma keo len 1080 thi be nat


def _do_anh(duong_dan):
    """-> (Path, rong, cao). Duong dan tuong doi tinh theo CWD truoc, roi ROOT."""
    p = Path(duong_dan)
    if not p.exists() and not p.is_absolute():
        p = ROOT / duong_dan
    if not p.exists():
        raise FileNotFoundError(f"khong thay anh '{duong_dan}'")
    if p.suffix.lower() not in ANH_MIME:
        raise ValueError(f"anh '{p.name}' duoi la {p.suffix} — "
                         f"chi nhan {', '.join(sorted(ANH_MIME))}")
    from PIL import Image
    with Image.open(p) as im:
        return p, im.width, im.height


def _anh_data_uri(p):
    """Nhung base64: Chromium doc HTML tu chuoi nen khong co URL goc de giai
    duong dan tuong doi (giong ly do font phai nhung)."""
    b64 = base64.b64encode(p.read_bytes()).decode("ascii")
    return f"data:{ANH_MIME[p.suffix.lower()]};base64,{b64}"


def khung_anh(rong, cao):
    """-> (cao hien, cao neu giu tron ti le). Bang nhau = khong cat ti nao."""
    cao_that = max(1, round(W * cao / rong))
    return min(cao_that, FIG_CAO_TOI_DA), cao_that


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


def masthead(brand, section, bare=False):
    # bare=True: chỉ giữ hairline, không chữ — dùng cho slide cta đã có
    # "Theo dõi @donniechublog" ở folio, tránh lặp nhận diện kênh 2 chỗ.
    if bare:
        return '<div class="mast"><span class="rule"></span></div>'
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
def s_cover(sl, th):
    by = sl.get("byline", [])
    bits = []
    for i, b in enumerate(by):
        if i:
            bits.append('<span class="dot"></span>')
        cls = "b0" if i == 0 else ""
        bits.append(f'<span class="{cls}">{esc(b)}</span>')
    byline = f'<div class="byline">{"".join(bits)}</div>' if by else ""
    g = (glow(f"top:40px;left:50%;transform:translateX(-50%);width:900px;height:640px;"
              f"background:radial-gradient(ellipse at center,{rgba(th['a'],0.20)} 0%,{rgba(th['a'],0)} 60%);")
         + glow(f"top:120px;right:-80px;width:520px;height:520px;"
                f"background:radial-gradient(circle at center,{rgba(th['b'],0.16)} 0%,{rgba(th['b'],0)} 62%);"))
    head = (
        f'<div class="mid" style="position:relative;">'
        f'{eyebrow(sl["eyebrow"])}'
        f'<h1 class="title" style="font-size:88px;margin:24px 0 26px;">{accent_html(sl["title"], sl.get("accent"))}</h1>'
        f'<p class="standfirst" style="font-size:38px;margin-bottom:30px;max-width:860px;">{esc(sl["standfirst"])}</p>'
        f'{byline}</div>'
    )
    hero = f'<div style="margin:8px 0;">{hero_svg(th["hero"], th)}</div>'
    return g + hero + head


def s_statement(sl, th):
    cards = ""
    for c in sl.get("cards", []):
        cards += (f'<div class="card"><span class="card-num">{esc(c["num"])}</span>'
                  f'<span class="card-txt">{esc(c["text"])}</span></div>')
    cards_wrap = (f'<div style="display:flex;flex-direction:column;gap:20px;'
                  f'position:relative;z-index:2;margin-top:44px;">{cards}</div>') if cards else ""
    g = glow("bottom:-120px;right:-120px;width:560px;height:560px;"
             f"background:radial-gradient(circle at center,{rgba(th['b'],0.14)} 0%,{rgba(th['b'],0)} 62%);")
    body = (
        f'<div class="mid" style="margin-top:52px;">'
        f'{eyebrow(sl["eyebrow"])}'
        f'<h1 class="title" style="font-size:78px;margin:36px 0 40px;">{accent_html(sl["title"], sl.get("accent"))}</h1>'
        f'<p class="standfirst" style="font-size:40px;max-width:880px;">{esc(sl["standfirst"])}</p>'
        f'</div>{cards_wrap}'
    )
    return g + body


def s_steps(sl, th):
    rows = ""
    for i, st in enumerate(sl.get("steps", []), start=1):
        rows += (f'<div class="step"><span class="step-num">{i:02d}</span>'
                 f'<div style="flex-grow:1;padding-top:4px;">'
                 f'<div class="step-t">{esc(st["title"])}</div>'
                 f'<div class="step-d">{esc(st["desc"])}</div></div></div>')
    g = glow("top:-100px;right:-120px;width:520px;height:520px;"
             f"background:radial-gradient(circle at center,{rgba(th['a'],0.13)} 0%,{rgba(th['a'],0)} 62%);")
    body = (
        f'<div class="mid" style="margin-top:46px;">'
        f'{eyebrow(sl["eyebrow"])}'
        f'<h1 class="title" style="font-size:80px;margin:24px 0 8px;">{accent_html(sl["title"], sl.get("accent"))}</h1>'
        f'</div>'
        f'<div class="mid" style="margin-top:38px;">{rows}'
        f'<div style="border-bottom:1px solid #23262E;"></div></div>'
    )
    return g + body


def s_loop(sl, th):
    # Hang chip xuong dong duoc, nhung mui ten "→" khong duoc dung cuoi dong va
    # dau lap "↻" khong duoc dung dau dong mot minh (cu de roi tung the la flex
    # item thi ca hai deu bi vat ra rieng, nhin nhu loi). Nen buoc moi mui ten
    # voi chip DI SAU no, va dau lap voi chip CUOI, thanh mot cum khong the tach.
    items = sl.get("chips", [])
    cum = []
    for i, c in enumerate(items):
        phan = f'<span class="chip {"chip0" if i == 0 else ""}">{esc(c)}</span>'
        if i:
            phan = f'<span class="arrow">&rarr;</span>' + phan
        if i == len(items) - 1:
            phan += '<span class="loopmark">&#8635;</span>'
        cum.append(f'<span class="chip-grp">{phan}</span>')
    chips = "".join(cum) or '<span class="loopmark">&#8635;</span>'
    callout = (f'<div class="callout" style="margin-top:0;">{esc(sl["callout"])}</div>'
               if sl.get("callout") else "")
    g = glow("top:200px;left:-120px;width:520px;height:520px;"
             f"background:radial-gradient(circle at center,{rgba(th['a'],0.12)} 0%,{rgba(th['a'],0)} 62%);")
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


def s_figure(sl, th):
    """Hinh that trai full be ngang; chieu cao thua moi den luot chu."""
    p, iw, ih = _do_anh(sl["image"])
    cao, cao_that = khung_anh(iw, ih)
    cat = cao_that > cao
    if cat:
        # Bao ra de Kite biet anh bi cat bao nhieu: neu phan mat la phan dang
        # noi toi thi phai tu cat lai cho dung truoc khi dua vao day.
        print(f"figure {p.name}: {iw}x{ih}, cao {cao_that}px -> con {cao}px "
              f"(giu mep tren, mat {cao_that - cao}px duoi)", file=sys.stderr)
    # Cat thi giu MEP TREN: bieu do va bang so de tieu de, truc, hang dau o tren.
    # Mep duoi loang dan vao nen — cat ngang than mot dong chu ma de nguyen thi
    # trong nhu anh bi xen hong, loang di thi doc ra la "con nua o duoi".
    loang = (f'<div style="position:absolute;left:0;right:0;bottom:0;height:96px;'
             f'background:linear-gradient(to bottom,{rgba(th["bg"], 0)} 0%,'
             f'{rgba(th["bg"], 0.92)} 100%);"></div>') if cat else ""
    band = (f'<div class="fig" style="height:{cao}px;">'
            f'<img src="{_anh_data_uri(p)}" alt="" '
            f'style="object-position:{"top" if cat else "center"};">'
            f'{loang}</div>')
    cap = (f'<div class="fig-cap"><span class="fig-bar"></span>'
           f'<span>{esc(sl["caption"])}</span></div>') if sl.get("caption") else ""
    chu = ""
    if sl.get("standfirst"):
        chu += (f'<p class="standfirst" style="font-size:36px;max-width:900px;'
                f'margin-top:30px;">{esc(sl["standfirst"])}</p>')
    for c in sl.get("cards", []):
        chu += (f'<div class="card" style="margin-top:22px;">'
                f'<span class="card-num">{esc(c["num"])}</span>'
                f'<span class="card-txt" style="font-size:31px;">{esc(c["text"])}</span></div>')
    g = glow("top:-80px;left:-140px;width:520px;height:520px;"
             f"background:radial-gradient(circle at center,{rgba(th['a'],0.12)} 0%,{rgba(th['a'],0)} 62%);")
    body = (
        f'<div class="mid" style="margin-top:40px;">'
        f'{eyebrow(sl["eyebrow"])}'
        f'<h1 class="title" style="font-size:62px;margin:22px 0 30px;">'
        f'{accent_html(sl["title"], sl.get("accent"))}</h1></div>'
        f'{band}'
        f'<div class="mid">{cap}{chu}</div>'
    )
    return g + body


def s_cta(sl, th):
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
             f"background:radial-gradient(circle at center,{rgba(th['b'],0.15)} 0%,{rgba(th['b'],0)} 62%);")
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
    "loop": s_loop, "figure": s_figure, "cta": s_cta,
}


def slide_doc(sl, idx, total, brand, section, folio_left, font_css, th, follow=None):
    kind = sl.get("kind")
    if kind not in BUILDERS:
        raise SystemExit(f"slide {idx}: kind khong hop le '{kind}' "
                         f"(chon: {', '.join(BUILDERS)})")
    body = BUILDERS[kind](sl, th)
    # slide cta có thể ghi 'follow' vào folio trái thay nhãn mặc định
    fol_left = sl.get("follow", follow) if kind == "cta" and (sl.get("follow") or follow) else folio_left
    # slide cta đã có follow (vd "Theo dõi @donniechublog") thì header bỏ chữ,
    # chỉ giữ hairline — tránh nhắc nhận diện kênh 2 lần trên cùng một slide.
    bare = kind == "cta" and bool(sl.get("follow") or follow)
    inner = masthead(brand, section, bare=bare) + body + folio(fol_left, idx, total)
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>'
            f'{font_css}{base_css(th)}</style></head><body>'
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
    # slide figure: anh phai co that va phai du to. Anh 600px keo len 1080px
    # (roi chup o scale 2 nua) thi chu tren bieu do nhoe thanh vet — dang len
    # la ca bo hong, ma luc dung khong ai nhin ra tren man to.
    for i, sl in enumerate(slides, 1):
        if sl.get("kind") != "figure":
            continue
        if not sl.get("image"):
            loi.append(f"slide {i}: kind 'figure' phai co 'image' (duong dan tep anh)")
            continue
        try:
            _, rong, cao = _do_anh(sl["image"])
        except (FileNotFoundError, ValueError) as e:
            loi.append(f"slide {i}: {e}")
            continue
        if rong < FIG_RONG_TOI_THIEU:
            loi.append(f"slide {i}: anh rong {rong}px, keo len {W}px la be nat. "
                       f"Chup lai bang chup_chart.py (DPR 2) hoac xin ban goc.")
        if not sl.get("caption"):
            loi.append(f"slide {i}: figure phai co 'caption' — hinh muon cua "
                       f"nguoi ta thi phai ghi 'via <ai>'.")

    # quy ước dẫn nguồn: dùng 'via', không viết 'nguồn'
    for i, sl in enumerate(slides, 1):
        for nhan, t in _texts(sl):
            low = t.lower()
            if "nguồn" in low:
                loi.append(f"slide {i} [{nhan}]: dan nguon phai ghi 'via', khong ghi 'nguồn'")
    return loi


def _texts(sl):
    """(nhan, chuoi) mọi trường chữ cần soi dấu."""
    out = []
    for k in ("eyebrow", "title", "standfirst", "callout", "caption"):
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



# ---- chon theme / hero ------------------------------------------------------
NHAT_KY_THEME = ROOT / "state" / "edu_theme_da_dung.jsonl"


def _theme_gan_day(n=4):
    """[(theme, hero)] cua n bo gan nhat, moi nhat truoc."""
    if not NHAT_KY_THEME.exists():
        return []
    rows = []
    for line in NHAT_KY_THEME.read_text("utf-8").splitlines():
        try:
            d = json.loads(line)
            rows.append((d.get("theme"), d.get("hero")))
        except Exception:
            continue
    return rows[::-1][:n]


def _ghi_theme(out, theme, hero):
    try:
        NHAT_KY_THEME.parent.mkdir(parents=True, exist_ok=True)
        with open(NHAT_KY_THEME, "a", encoding="utf-8") as f:
            f.write(json.dumps({"out": str(out), "theme": theme, "hero": hero},
                               ensure_ascii=False) + "\n")
    except OSError:
        pass


def chon_theme_tu_dong(spec):
    """Spec khong ghi theme/hero -> chon cai IT DUNG NHAT gan day, va khong bao
    gio trung voi bo vua dung truoc. Ghi ro thi ton trong, nhung neu trung
    het ca theme lan hero voi bo ngay truoc thi bao de Kite biet (khong chan:
    Ong Chu co the co y muon mot loat cung tone)."""
    gan = _theme_gan_day()
    theme, hero = spec.get("theme"), spec.get("hero")
    if theme and theme not in THEMES:
        raise SystemExit(f"theme '{theme}' khong co (chon: {', '.join(THEMES)})")
    if hero and hero not in HEROES:
        raise SystemExit(f"hero '{hero}' khong co (chon: {', '.join(HEROES)})")

    import hashlib
    seed = int(hashlib.md5(str(spec.get("folio", "")).encode()).hexdigest(), 16)

    def it_dung_nhat(ung_vien, da_dung, xoay):
        # uu tien cai chua xuat hien trong lich su gan day; cai vua dung xep
        # cuoi. Trong nhom "chua dung", xoay theo seed de theme va hero khong
        # di theo cap co dinh (orbit-orbit, ember-grid...).
        thu_tu = {x: i for i, x in enumerate(da_dung)}   # 0 = moi nhat
        chua = [x for x in ung_vien if x not in thu_tu]
        if chua:
            return chua[xoay % len(chua)]
        return sorted(ung_vien, key=lambda x: -thu_tu[x])[0]

    if not theme:
        theme = it_dung_nhat(list(THEMES), [t for t, _ in gan], seed)
    if not hero:
        hero = it_dung_nhat(list(HEROES), [h for _, h in gan], seed // 7)
    if gan and gan[0] == (theme, hero):
        print(f"CANH BAO: theme={theme} hero={hero} TRUNG voi bo ngay truoc "
              f"({gan[0]}). Neu la 'lam lai' thi phai doi.", file=sys.stderr)
    return theme, hero

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
    theme, hero = chon_theme_tu_dong(spec)
    th = dict(THEMES[theme], hero=hero)
    print(f"theme={theme} hero={hero}")

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
            doc = slide_doc(sl, i, total, brand, section, folio_left, font_css, th)
            page.set_content(doc, wait_until="load")
            page.evaluate("document.fonts.ready")
            page.wait_for_timeout(120)
            path = out if i == 1 else Path(f"{stem}_{i}.png")
            page.screenshot(path=str(path),
                            clip={"x": 0, "y": 0, "width": W, "height": H})
            outs.append(path)
        browser.close()
    _ghi_theme(out, theme, hero)
    return outs


def main():
    ap = argparse.ArgumentParser(description="Renderer carousel.edu (vai Kite)")
    ap.add_argument("--spec", required=True, help="file JSON, hoac '-' doc stdin")
    ap.add_argument("--out", required=True, help="drafts/<id>.png (bia)")
    ap.add_argument("--brand", default="donniechublog",
                    choices=["donniechublog", "dcgr"])
    ap.add_argument("--bo-qua-dau", action="store_true",
                    help="chi khi copy that su la tieng Anh")
    ap.add_argument("--theme", choices=list(THEMES),
                    help="bang mau; bo trong = tu xoay khac lan truoc")
    ap.add_argument("--hero", choices=list(HEROES),
                    help="hero art tren bia; bo trong = tu xoay khac lan truoc")
    ap.add_argument("--scale", type=int, default=2,
                    help="device scale factor (2 = 2160x2700, net hon)")
    a = ap.parse_args()

    raw = sys.stdin.read() if a.spec == "-" else Path(a.spec).read_text("utf-8")
    spec = json.loads(raw)
    spec.setdefault("brand", a.brand)
    if a.theme:
        spec["theme"] = a.theme
    if a.hero:
        spec["hero"] = a.hero

    outs = render(spec, a.out, a.brand, a.bo_qua_dau, a.scale)
    print("Da dung " + str(len(outs)) + " slide:")
    for p in outs:
        print("  " + str(p))


if __name__ == "__main__":
    main()
