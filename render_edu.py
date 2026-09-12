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
100%, thả 2 TTF đó vào assets/fonts rồi đổi bảng FONTS bên dưới. Font được
`page.route` phục vụ từ assets/fonts nên Chromium headless không cần font hệ
thống (tránh tofu tiếng Việt trên server tối giản).

Spec JSON:
{
  "brand": "donniechublog",        # tuỳ chọn, mặc định theo --brand
  "section": "AI TOOLING",         # nhãn phải của masthead (mono)
  "folio": "GOOGLE ANTIGRAVITY",   # nhãn trái của folio
  "theme": "ember",                # tuỳ chọn: orbit|ember|moss|ink|rose — bỏ trống = tự xoay
  "hero": "grid",                  # tuỳ chọn: orbit|grid|wave|rings|graph — bỏ trống = tự xoay
  "slides": [
    # Bia dung ART VECTOR (mac dinh). Tin nao CO SAN mot tam hinh dang dua len
    # thi them "image" + "caption": bia lay chinh hinh do lam hero, khong ve so
    # do nua. Hinh that bao gio cung noi duoc nhieu hon mot so do trang tri.
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

    # Khong co hinh that nhung bai co vai con so: bieu do cot ngang tu so THAT
    # (2..6 cot, "value" la so, "text" la cach ghi), caption "via" bat buoc.
    {"kind": "bars", "eyebrow": "SỐ LIỆU",
     "title": "Chi phí mỗi task giảm ba lần", "accent": "ba lần",
     "bars": [{"label": "Trước", "value": 2.75, "text": "2,75 USD"},
              {"label": "Sau boost", "value": 0.9, "text": "0,90 USD", "nhan": true}],
     "caption": "Số trong bài · via Google DeepMind",
     "standfirst": "Tuỳ chọn, ≤ 160 ký tự."},

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
quá thì giữ mép trên. Chữ đè lên ảnh: MẶC ĐỊNH không phủ lớp nền nào — chỉ đổi
màu chữ (sáng/tối) tương phản với đúng vùng ảnh nằm dưới chữ. Lớp mờ+tối chỉ
thêm khi vùng đó thật sự rối (đo trực tiếp trên pixel), và khi thêm thì cũng
chỉ vừa đủ — không bao giờ tối hơn mức cần, và ranh giới trên không vượt quá
dòng chữ đầu tiên (không có khoảng đệm để trống phía trên chữ). Bắt buộc có
"caption" ghi "via <ai>", và ảnh phải rộng >= 800px (chụp bằng chup_chart.py).
Vẫn cấm: ảnh minh hoạ AI, screenshot dựng lại, logo hãng, số liệu tự bịa.
"""

import argparse
import base64
import html
import json
import re
import sys
from pathlib import Path

# tái dùng cổng chặn tiếng Việt của cả đội
import tieng_viet  # noqa: E402  (cùng thư mục) — chỉ cần cổng chữ, không cần PIL
# đo tương phản WCAG dùng CHUNG với card.py/Ethan + itachi_nop.py — xem LOW-9
import nen_chu  # noqa: E402

ROOT = Path(__file__).resolve().parent
FONTS_DIR = ROOT / "assets" / "fonts"

# ---- Design tokens ---------------------------------------------------------
# Mau CHU dung chung cho moi theme. Nen/panel/hairline/mau nhan thi khong: moi
# theme mot bo rieng (THEMES ben duoi). Truoc day chi co mot bo cyan x tim + mot
# hero "quy dao" nen moi bo Kite dung ra deu giong nhau (Ong Chu che 04/09:
# "lam di lam lai mot tone"). Gio spec ghi "theme" / "hero", khong ghi thi
# renderer tu XOAY khac lan truoc (xem chon_theme_tu_dong).
WHITE   = "#F4F6F9"
SOFT    = "#E7EAEF"
MUTED   = "#949AA6"
DIM     = "#7B828E"

# Moi theme: nen, panel, hairline, 2 mau nhan (chinh x phu), va mau standfirst.
# Tat ca deu NEN TOI + CHU SANG (luat tuong phan cua ca doi), khac nhau o hue.
# Nen KHONG phai den dac. Ban dau lay den gan tuyet doi (#0A0B0E...), dan len
# the la ca the thanh mot khoi muc, nang tri (Ong Chu che 04/09/2026). Nang nen
# len mot bac va cho no mot do sang nhe o dinh the (xem BASE_CSS_TPL): van tuong
# phan cung voi chu trang, ma mat tho hon han.
THEMES = {
    "orbit":  dict(bg="#171A21", panel="#212530", line="#333846",
                   a="#2FD4E1", b="#8E86F0", stand="#BFC5CF"),   # cyan x tim (bo /boost)
    "ember":  dict(bg="#1D1814", panel="#292118", line="#40342A",
                   a="#FFB454", b="#FF6B6B", stand="#D0C6BB"),   # cam ho phach x do san ho
    "moss":   dict(bg="#151C18", panel="#1F2A24", line="#2E3D35",
                   a="#7BE495", b="#D6F26A", stand="#BCCAC0"),   # xanh la x vang chanh
    "ink":    dict(bg="#161B29", panel="#1F2739", line="#303D5C",
                   a="#8FB3FF", b="#F2C94C", stand="#C1C9DC"),   # xanh navy x vang
    "rose":   dict(bg="#1F1721", panel="#2B1F2F", line="#3E2C43",
                   a="#FF7EB6", b="#B892FF", stand="#D2C0CF"),   # hong x tim oai huong
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


FONT_URL = "https://font.noi-bo/"      # khong ra mang: page.route chan het (xem _route_font)


def _font_face_css():
    """CSS @font-face TRO TOI `page.route`, khong nhung base64 (audit B7).

    Truoc day moi font duoc base64 thang vao CSS, va CSS do di vao HTML cua TUNG
    slide: ~4,7MB moi `set_content`, 6-10 slide mot bai. Base64 con phinh 33%.
    Nay CSS chi tro toi mot URL gia va `_route_font` phuc vu tep tu dia — Chromium
    tai moi font mot lan roi dung lai cho cac slide sau.

    Van kiem tep font co du TAI DAY (khong doi toi luc render): thieu font ma de
    Chromium tu roi ve font he thong la ca album sai chu ma nhin anh moi biet."""
    blocks = []
    thieu = []
    for fam, faces in FONTS.items():
        for fname, weight, style in faces:
            fp = FONTS_DIR / fname
            if not fp.exists():
                thieu.append(fname)
                continue
            blocks.append(
                "@font-face{font-family:'%s';font-weight:%s;font-style:%s;"
                "font-display:block;src:url('%s%s') "
                "format('truetype');}" % (fam, weight, style, FONT_URL, fname)
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
.art{position:relative;width:%(W)spx;height:%(H)spx;
  background:radial-gradient(ellipse 130%% 78%% at 50%% -8%%,%(PANEL)s 0%%,%(BG)s 66%%);
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
.dot{width:4px;height:4px;border-radius:50%%;background:%(DIM)s;
  display:inline-block;}
/* blocks */
.mid{position:relative;z-index:2;}
.card{display:flex;flex-direction:row;align-items:center;gap:24px;
  background:%(PANEL)s;border:1px solid %(LINE)s;border-left:5px solid %(CYAN)s;
  padding:30px 34px;}
.card-num{font-family:%(MONO)s;font-size:26px;font-weight:700;color:%(VIOLET)s;}
.card-txt{font-size:34px;line-height:1.35;color:%(SOFT)s;}
.step{display:flex;flex-direction:row;align-items:flex-start;gap:32px;
  padding:26px 0;border-top:1px solid %(LINE)s;}
.step-num{font-family:%(MONO)s;font-size:48px;font-weight:700;color:%(CYAN)s;
  line-height:1;min-width:78px;}
.step-t{font-family:%(DISPLAY)s;font-size:42px;font-weight:700;color:%(WHITE)s;
  margin-bottom:8px;letter-spacing:-0.5px;}
.step-d{font-size:31px;font-weight:400;line-height:1.4;color:%(MUTED)s;}
.chips{display:flex;flex-direction:row;align-items:center;gap:18px;
  flex-wrap:wrap;}
.chip{font-family:%(MONO)s;font-size:29px;font-weight:700;color:%(SOFT)s;
  background:%(PANEL)s;border:1px solid %(LINE)s;padding:12px 22px;}
.chip0{color:%(BG)s;background:%(CYAN)s;border:none;}
.arrow{color:%(DIM)s;font-size:32px;font-weight:800;}
.chip-grp{display:inline-flex;flex-direction:row;align-items:center;gap:18px;}
.loopmark{color:%(VIOLET)s;font-size:30px;font-weight:700;}
.callout{background:%(PANEL)s;border:1px solid %(LINE)s;border-left:5px solid %(CYAN)s;
  padding:34px 38px;font-size:34px;font-weight:600;line-height:1.45;color:%(SOFT)s;}
.check{display:flex;flex-direction:row;align-items:flex-start;gap:22px;}
.check-m{color:%(CYAN)s;font-size:38px;font-weight:800;line-height:1.1;}
.check-t{font-size:35px;font-weight:500;line-height:1.35;color:%(SOFT)s;}
/* bieu do cot ngang tu so that trong bai (kind bars) */
.bar{display:flex;flex-direction:row;align-items:center;gap:22px;padding:15px 0;}
.bar-l{font-family:%(MONO)s;font-size:26px;font-weight:700;color:%(SOFT)s;
  flex:none;width:300px;line-height:1.2;}
.bar-track{flex-grow:1;height:46px;background:%(PANEL)s;border:1px solid %(LINE)s;
  position:relative;}
.bar-fill{position:absolute;left:0;top:0;bottom:0;background:%(VIOLET)s;}
.bar-fill.nhan{background:%(CYAN)s;}
.bar-v{font-family:%(MONO)s;font-size:30px;font-weight:700;color:%(WHITE)s;
  flex:none;width:190px;text-align:right;}
/* hinh that: phu kin the, KHONG bao gio la mot hop dat canh chu */
.figwrap{position:absolute;left:0;top:0;width:%(W)spx;height:%(H)spx;
  z-index:0;overflow:hidden;background:%(BG)s;}
.fig-nen{position:absolute;left:50%%;top:50%%;width:128%%;height:128%%;
  transform:translate(-50%%,-50%%);object-fit:cover;filter:blur(%(BLURNEN)spx);}
.fig-sac{position:absolute;left:0;width:%(W)spx;object-fit:cover;display:block;}
/* ANH CHUP vao DONG: nam giua masthead va khoi chu, an het phan trong con lai
   va KHONG BAO GIO bi chu de len (khong con lop mo 0.93 che mep duoi anh).
   max-height:100%% + object-fit:contain = hien FULL hinh, khong cat, khong keo
   meo; thieu cho thi thu nho chu khong crop. */
.fig-anh-wrap{position:relative;z-index:1;flex:1 1 auto;min-height:0;
  display:flex;flex-direction:row;align-items:flex-start;justify-content:center;
  margin-top:14px;}
.fig-anh{max-width:100%%;max-height:100%%;width:auto;height:auto;display:block;}
/* lop MO cua chinh anh, hien dan theo cung nhip voi man toi — chinh no moi xoa
   het chi tiet doc duoc duoi chu; chi lam toi khong thi chu van chong len chu */
.fig-molop{position:absolute;left:0;top:0;width:%(W)spx;height:%(H)spx;
  overflow:hidden;}
.fig-molop img{position:absolute;left:0;width:%(W)spx;object-fit:cover;
  display:block;filter:blur(14px);}
/* man toi cho chu — dat lai bang script theo dung dong chu dau */
.fig-man{position:absolute;left:0;right:0;bottom:0;}
.fig-cap{display:flex;flex-direction:row;align-items:baseline;gap:16px;
  margin-top:22px;font-family:%(MONO)s;font-size:23px;font-weight:500;
  line-height:1.45;color:%(DIM)s;letter-spacing:0.5px;}
.fig-bar{flex:none;width:26px;height:3px;background:%(CYAN)s;
  transform:translateY(-7px);}
.readmore{background:%(PANEL)s;border:1px solid %(LINE)s;padding:34px 38px;}
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
        "BLURNEN": FIG_BLUR_NEN,
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
FIG_RONG_TOI_THIEU = 800    # hep hon the ma keo len 1080 thi be nat

# Bo so lay NGUYEN cua carousel.py (vai Dre) de hai vai noi cung mot thu tieng.
FIG_BLUR_NEN = 44      # mo manh ban cover lam nen: phai xoa het chi tiet doc duoc,
                       # khong thi cho nao lop sac khong phu se lo mot BAN SAO
                       # phong to cua chinh tam anh -> mat doc ra HAI VUNG
# MAC DINH KHONG CO LOP NEN (Ong Chu chot 08/09/2026, nhac lai nhieu lan): chu
# de len anh thi doi MAU CHU (sang/toi) cho tuong phan voi dung vung anh nam
# duoi no, KHONG mac dinh phu mot man toi/mo len ca anh. Lop mo+tinh chi la
# NGOAI LE — dung khi do thang tren pixel thay vung do qua "roi" (bien thien
# cao, chu mot mau khong an toan), va khi dung thi cung chi VUA DU, khong bao
# gio dam hon muc can. Truoc day FIG_MAX_TOI co san 0.80 la sai huong: luon
# phu du roi moi tinh tiep, thay vi hoi truoc co can phu khong.
# Chu "toi" o day la rgba(0,0,0,0.85) DE LEN nen (xem _css_chu_toi_vung), khong
# phai den tuyet doi: ~15% mau nen con xuyen qua. Nguong 150 cu la so tay, chua
# tung kiem lai bang phep do WCAG that — LOW-9: Kite ra chu gan nhu lien mau
# voi nen (vd nen xam ~130-149, code van chon chu SANG vi 130-149 < 150, nhung
# tuong phan chu sang/nen 130-149 chi ~2.7-3.1:1, trong khi chu toi cho tuong
# phan ~4.5-5.1:1 — sai huong). Tinh lai bang nen_chu.nguong_tuong_phan (dung
# cong thuc CHUNG voi card.py/Ethan) cho DUNG cap mau THAT dang dung o day,
# thay vi mot con so co dinh dung chung cho ca chu sang tuyet doi lan chu toi
# alpha-blend.
_MAU_CHU_SANG_RGB = tuple(int(WHITE.lstrip("#")[k:k + 2], 16) for k in (0, 2, 4))
_MAU_CHU_TOI_HIEU_DUNG = (38, 38, 38)  # xap xi 0.15 x nen sang (rgba đen 0.85)
NGUONG_SANG_CHU_TOI = round(nen_chu.nguong_tuong_phan(_MAU_CHU_SANG_RGB, _MAU_CHU_TOI_HIEU_DUNG))
NGUONG_ROI_CAN_LOP = 26    # do lech (stddev xam) vung duoi chu: qua nguong moi can lop
# Muc toi khi can_lop (09/09/2026, tang tu 0.55 sau khi Ong Chu xem anh that:
# so ma van doc duoc ro qua lop mo yeu — xem chu thich tai noi dung max_toi).
# Khong dat 1.0 tuyet doi: giu lai chut kho anh phia duoi de van la "anh duoc
# xu ly" chu khong phai "hop mau ke len anh", nhung 0.93 da du toi de khong con
# chu/so nao doc duoc.
TOI_TOI_DA_MO = 0.93
VEIL_SPAN = 64             # px: be day duong cong chuyen tiep, bat dau NGAY tai
                           # dong chu dau — khong con khoang dem truoc no nua
FIG_TIEU_DE_DONG = 2   # slide co anh: tieu de toi da bay nhieu dong
FIG_DINH = 150         # chua masthead: anh khong bao gio tran len day
FIG_DAY_PHANG = 0.63   # anh nen PHANG dung o day; duoi la mat phang sach cho chu


# Mot tam anh bi soi di soi lai: cong chan doc no, cong chan 2 dong dung slide
# mot lan, roi vong chup dung lai lan nua. Rieng doc_nen phai quet toan bo pixel
# va _anh_data_uri phai base64 ca tep — lam lai 3 lan cho mot anh 4MB la phi.
_NHO_ANH = {}


def _nho(khoa, lam):
    if khoa not in _NHO_ANH:
        _NHO_ANH[khoa] = lam()
    return _NHO_ANH[khoa]


def _do_anh(duong_dan):
    """-> (Path, rong, cao). Duong dan tuong doi tinh theo CWD truoc, roi ROOT."""
    return _nho(("do", str(duong_dan)), lambda: _do_anh_that(duong_dan))


def _do_anh_that(duong_dan):
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
    def lam():
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        return f"data:{ANH_MIME[p.suffix.lower()]};base64,{b64}"
    return _nho(("uri", str(p)), lam)


def _sang(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def doc_nen(p):
    """Nen quanh lop sac phai LIEN voi no, khong bao gio la mot mang khac tone.

    Dre lam nen bang chinh tam anh phong to + lam mo — dung cho ANH CHUP. Nhung
    bieu do/bang so/trang bao cao thi nen cua no la mot mau PHANG (thuong la
    trang): lam mo ban cover cua no ra mot mang xam-xanh lech han tone voi chinh
    tam anh sac o tren, van doc ra hai vung. Voi loai do, trai thang MAU NEN cua
    anh ra ca the la lien mach tuyet doi — cung mot mau, khong the co mep.

    -> (kieu, mau nen, nen co sang khong)
    """
    return _nho(("nen", str(p)), lambda: _doc_nen_that(p))


NGUONG_LECH_VIEN = 20        # +-do lech mau (tung kenh) con tinh la "gan mau nen"
TI_LE_PHANG_TOI_THIEU = 0.85  # ti le pixel vien phai gan mau nen moi goi la phang


def _doc_nen_that(p):
    from PIL import Image, ImageStat
    with Image.open(p) as im:
        im = im.convert("RGB")
        w, h = im.size
        d = max(2, min(w, h) // 50)
        vien = [im.crop((0, 0, w, d)), im.crop((0, h - d, w, h)),
                im.crop((0, 0, d, h)), im.crop((w - d, 0, w, h))]
        # MEDIAN + ti le pixel gan mau nen, khong phai mean/stddev: mot bang so
        # duoc chup sat mep thi hang cuoi (chu/duong ke) hay dinh dung ngay tren
        # dai vien duoi — chi la THIEU SO trong vien do, nhung stddev bi mot
        # nhom pixel tuong phan cao keo vong len rat manh, doc nham ra "mo" (anh
        # chup) roi che mat man toi tran ca len phan bang con doc duoc (Ong Chu
        # bao 08/09/2026: bang cau hinh bi che mat hang cuoi, chu va anh doc ra
        # hai mang). Ti le pixel nam trong NGUONG_LECH_VIEN quanh median moi
        # phan anh dung cau hoi "vien nay co phai CHU YEU mot mau khong".
        tb, ti_le = [], []
        for v in vien:
            st = ImageStat.Stat(v)
            med = [int(round(x)) for x in st.median]
            tb.append(med)
            for k in range(3):
                lo, hi = max(0, med[k] - NGUONG_LECH_VIEN), min(255, med[k] + NGUONG_LECH_VIEN)
                ti_le.append(sum(st.h[k * 256:k * 256 + 256][lo:hi + 1]) / st.count[k])
        toan = ImageStat.Stat(im).mean[:3]
    khac = max(abs(a[k] - b[k]) for a in tb for b in tb for k in range(3))
    phang = min(ti_le) >= TI_LE_PHANG_TOI_THIEU and khac < 16
    mau = tuple(int(sum(t[k] for t in tb) / 4) for k in range(3))
    # Dinh the luon la NEN (anh khong tran len FIG_DINH), nen do sang o dinh la
    # do sang cua nen: mau phang, hoac mau trung binh cua ban lam mo.
    return ("phang" if phang else "mo",
            "#%02X%02X%02X" % mau,
            _sang(mau if phang else toan) > NGUONG_SANG_CHU_TOI)


def _vung_duoi_chu(p, ti_le=0.35):
    """Do sang (0..255) cua NEN se nam duoi khoi chu.

    Anh CHUP vao dong (xem anh_lam_nen): khoi chu luon nam DUOI mep anh, tren
    nen la chinh tam anh cover phong to lam mo. Do ban mo do, khong do tam anh
    — chon mau chu theo tam anh la sai (chu trang tren nen mo sang = mat chu).
    """
    from PIL import Image, ImageFilter, ImageOps, ImageStat
    im = _nho(("pil", str(p)), lambda: Image.open(p).convert("RGB"))
    d = max(1, int(H * ti_le))
    dai = im.resize((max(1, W // 8), max(1, H // 8))).convert("L")
    return ImageStat.Stat(dai.crop((0, dai.height - max(1, d // 8), dai.width,
                                    dai.height))).mean[0], 0.0


def dat_anh(rong, cao, phang):
    """Cho anh trai HET be ngang slide roi tra ve (cao hien, y0, cao ti le).

    Nen tang lay cua _body_image trong carousel.py, chinh hai cho cho khung edu:

      - Chua san FIG_DINH cho masthead. Dre khong co masthead nen anh tran len
        tan dau the duoc; o day tran len la ten kenh nam de len chu trong anh.
      - Anh co nen PHANG (bieu do, bang so, trang tai lieu) chi duoc dung trong
        vung tren, KHONG tran xuong vung chu: duoi man toi no van con doc duoc
        mo mo, chu minh de len chu cua nguoi ta thanh mot dam roi. Anh CHUP thi
        khong co van de do — cu phu xuong nhu ben Dre.
      - Cao hon phan duoc phep thi cat, GIU MEP TREN (bieu do/bang de tieu de,
        truc, hang dau o tren).
      - Thap hon thi NEO NGAY DUOI MASTHEAD (y0 = FIG_DINH), khong dat giua.
        Dat giua de lai mot dai trong ~280px giua chip kenh va mep tren anh,
        doc ra nhu anh bi day xuong / bi cat cut (Ong Chu bat 10/09/2026: "day
        len cao va hien thi full hinh, tinh tu duoi chip"). Anh nam sat ngay
        duoi chip, phan trong con lai don het xuong duoi khoi chu.
    """
    cao_that = max(1, round(W * cao / rong))
    day = int(H * FIG_DAY_PHANG) if phang else H
    tran = day - FIG_DINH
    cao_hien = min(cao_that, tran)
    return cao_hien, FIG_DINH, cao_that


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
    """Bia. Mac dinh la hero art vector; nhung neu tin CO SAN mot tam hinh dang
    dua len thi ghi "image" — luc do bia dung chinh tam hinh do lam hero, chu
    chim vao no, thay vi mot so do tu ve. Hinh that bao gio cung noi duoc nhieu
    hon mot so do trang tri."""
    if sl.get("image"):
        return _cover_anh(sl, th)
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


def _cover_anh(sl, th):
    """Bia lay anh that lam hero — anh vao dong, khoi chu nam duoi mep anh."""
    nen, js, anh = anh_lam_nen(sl, th, "bia")
    by = sl.get("byline", [])
    bits = []
    for i, b in enumerate(by):
        if i:
            bits.append('<span class="dot"></span>')
        bits.append(f'<span class="{"b0" if i == 0 else ""}">{esc(b)}</span>')
    chu = (f'{eyebrow(sl["eyebrow"])}'
           # 74px chu khong phai 88px nhu bia art: bia co anh chi cho tieu de 2
           # dong, co chu nho hon mot bac thi 2 dong do chua duoc du y.
           f'<h1 class="title" style="font-size:74px;margin:22px 0 26px;">'
           f'{accent_html(sl["title"], sl.get("accent"))}</h1>'
           f'<p class="standfirst" style="font-size:36px;max-width:880px;'
           f'margin-bottom:28px;">{esc(sl["standfirst"])}</p>')
    if by:
        chu += f'<div class="byline">{"".join(bits)}</div>'
    if sl.get("caption"):
        chu += (f'<div class="fig-cap" style="margin-top:18px;">'
                f'<span class="fig-bar"></span>'
                f'<span>{esc(sl["caption"])}</span></div>')
    return (nen + anh
            + '<div style="flex-grow:1;min-height:0;"></div>'
            + f'<div class="mid" id="figtxt">{chu}</div>'
            + js)


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
        f'<div style="border-bottom:1px solid {th["line"]};"></div></div>'
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
            phan = '<span class="arrow">&rarr;</span>' + phan
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


def _mau_toi(th):
    """Ma hex CYAN nhan dien cua theme, ep toi 42% — van ra dung mau nhung doc
    duoc tren nen sang. Dung cho eyebrow/accent khi chu phai doi sang TOI."""
    a = [int(th["a"].lstrip("#")[k:k + 2], 16) for k in (0, 2, 4)]
    return "#%02X%02X%02X" % tuple(int(c * 0.42) for c in a)


def _css_mast_toi():
    """Masthead (ten kenh trai, section phai, gach ngang) doi sang TOI — dung
    khi DINH the (o tren, sau masthead) la nen sang: mot man toi rieng dat len
    tren se ve ra mot dai band vat ngang, dung cai dang tranh."""
    return ('<style>.mast-name,.mast-sec{color:rgba(0,0,0,0.62);}'
            '.rule{background:rgba(0,0,0,0.16);}</style>')


def _css_chu_toi_vung(scope, th):
    """<style> lat toan bo mau chu trong `scope` (vd '#figtxt') sang TOI — dung
    khi vung ngay duoi khoi chu do la SANG. Ap dung het: eyebrow, tieu de,
    accent, standfirst, caption, card, byline — khong chi rieng eyebrow nhu
    truoc (Ong Chu chot 08/09/2026: doi mau chu la cach chinh, khong phai
    phu them nen)."""
    a_toi = _mau_toi(th)
    return (f'<style>{scope} .eyebrow-txt{{color:{a_toi};}}'
            f'{scope} .eyebrow-bar{{background:{a_toi};}}'
            f'{scope} .fig-bar{{background:{a_toi};}}'
            f'{scope} .title{{color:rgba(0,0,0,0.85);}}'
            f'{scope} .accent{{color:{a_toi};}}'
            f'{scope} .standfirst{{color:rgba(0,0,0,0.68);}}'
            f'{scope} .fig-cap{{color:rgba(0,0,0,0.55);}}'
            f'{scope} .card-txt{{color:rgba(0,0,0,0.78);}}'
            f'{scope} .card-num{{color:{a_toi};}}'
            f'{scope} .byline{{color:rgba(0,0,0,0.55);}}'
            f'{scope} .byline .b0{{color:rgba(0,0,0,0.85);}}'
            f'{scope} .dot{{background:rgba(0,0,0,0.4);}}</style>')


def anh_lam_nen(sl, th, ten):
    """Dung ANH THAT thanh nen ca the. Dung chung cho slide `figure` va cho
    bia khi bia co anh. -> (html nen, html script dat lop mo neu can). Khoi
    chu goi rieng, id="figtxt".

    Nguyen tac (Ong Chu chot 08/09/2026, nhac lai nhieu lan — day la nguyen
    tac SAU hon ban cu "man toi lien mach"):

      MAC DINH KHONG PHU LOP NAO len anh. Doi MAU CHU (sang hoac toi) cho
      tuong phan voi dung vung anh nam duoi no la du — do thang do sang tren
      pixel that (ImageOps.fit mo phong dung object-fit:cover), khong doan.
      Chi khi vung do THAT SU roi (bien thien mau cao — vd anh chup nhieu chi
      tiet) thi moi them mot lop mo+tinh nhe, va khi them cung chi VUA DU de
      xoa chi tiet gay roi, khong bao gio dam hon muc can. Ranh gioi tren cua
      lop do khong duoc vuot qua dong chu dau tien — khong con khoang dem de
      trong phia tren chu nhu ban cu.

      NEN bao gio cung la anh (hoac dung mau nen phang cua no), khong bao gio
      la mot hop den dat canh anh. LOP SAC trai full be ngang, KHONG cat hai
      canh.
    """
    p, iw, ih = _do_anh(sl["image"])
    kieu, mau_nen, nen_sang = doc_nen(p)
    cao, y0, cao_that = dat_anh(iw, ih, kieu == "phang")
    if cao_that > cao and ("bao", str(p), cao) not in _NHO_ANH:
        # Bao ra de Kite biet mat bao nhieu: neu phan mat la phan dang noi toi
        # thi phai tu cat lai cho dung truoc khi dua vao day. Chi bao MOT lan:
        # slide duoc dung hai luot (cong chan 2 dong, roi vong chup), bao ca hai
        # luot thi Kite tuong co hai anh bi cat.
        _NHO_ANH[("bao", str(p), cao)] = True
        print(f"{ten} {p.name}: {iw}x{ih}, cao {cao_that}px -> con {cao}px "
              f"(giu mep tren, mat {cao_that - cao}px duoi)", file=sys.stderr)
    uri = _anh_data_uri(p)
    # Bi cat thi cho phan cuoi TAN vao nen thay vi dut ngang: nen cung mau nen
    # anh chi viec loang ra, doc thanh "con nua o duoi" chu khong phai "bi xen".
    mo_day = ('' if cao_that <= cao else
              'mask-image:linear-gradient(to bottom,#000 calc(100% - 130px),'
              'transparent 100%);-webkit-mask-image:linear-gradient(to bottom,'
              '#000 calc(100% - 130px),transparent 100%);')

    if kieu == "phang":
        # Nen la MOT MAU PHANG tu tren xuong duoi (mau_nen trai het figwrap):
        # duoi anh KHONG con chi tiet gi de "chim" hay can mo — chi can chon
        # mau chu tuong phan voi mau_nen, KHONG phu lop nao.
        nen = (f'<div class="figwrap" style="background:{mau_nen};">'
               f'<img class="fig-sac fig-doi" src="{uri}" alt="" '
               f'style="top:{y0}px;height:{cao}px;object-position:top;{mo_day}">'
               f'</div>')
        if nen_sang:
            nen += _css_mast_toi() + _css_chu_toi_vung("#figtxt", th)
        return nen, "", ""

    # kieu == "mo": ANH CHUP di vao DONG (flex item) giua masthead va khoi chu,
    # khong con lop tuyet doi de chu de len. Truoc 10/09/2026 anh nam lop
    # absolute tai top:y0 va khoi chu (neo day the) de len phan duoi cua no, che
    # bang mot lop mo 0.93 — Ong Chu doc ra la "anh bi cat got" (10/09/2026).
    # Dua vao dong thi KHONG THE chong nhau: anh an het phan trong con lai va
    # khoi chu luon nam duoi mep anh.
    # Nen the van la chinh tam anh cover phong to lam mo = mot mat phang lien.
    nen = (f'<div class="figwrap" style="background:{mau_nen};">'
           f'<img class="fig-nen" src="{uri}" alt=""></div>')
    sang_duoi, _ = _vung_duoi_chu(p)
    chu_toi = sang_duoi > NGUONG_SANG_CHU_TOI
    if nen_sang:
        nen += _css_mast_toi()
    if chu_toi:
        nen += _css_chu_toi_vung("#figtxt", th)
    anh = (f'<div class="fig-anh-wrap"><img class="fig-anh" src="{uri}" '
           f'alt=""></div>')
    return nen, "", anh


def s_figure(sl, th):
    """Hinh that trai het be ngang, chu chim vao anh o duoi."""
    nen, js, anh = anh_lam_nen(sl, th, "figure")
    chu = (f'{eyebrow(sl["eyebrow"])}'
           f'<h1 class="title" style="font-size:62px;margin:22px 0 0;">'
           f'{accent_html(sl["title"], sl.get("accent"))}</h1>')
    if sl.get("caption"):
        chu += (f'<div class="fig-cap"><span class="fig-bar"></span>'
                f'<span>{esc(sl["caption"])}</span></div>')
    if sl.get("standfirst"):
        chu += (f'<p class="standfirst" style="font-size:35px;max-width:900px;'
                f'margin-top:24px;">{esc(sl["standfirst"])}</p>')
    for c in sl.get("cards", []):
        chu += (f'<div class="card" style="margin-top:20px;background:none;'
                f'border:none;border-left:4px solid {th["a"]};padding:4px 0 4px 26px;">'
                f'<span class="card-num">{esc(c["num"])}</span>'
                f'<span class="card-txt" style="font-size:31px;">{esc(c["text"])}</span></div>')
    return (nen + anh
            + '<div style="flex-grow:1;min-height:0;"></div>'
            + f'<div class="mid" id="figtxt">{chu}</div>'
            + js)


def _so(v):
    """2.75 -> '2,75'; 3.0 -> '3' (kieu Viet, dung khi slide khong ghi 'text')."""
    f = float(v)
    return str(int(f)) if f == int(f) else f"{f:.2f}".rstrip("0").rstrip(".").replace(".", ",")


_SO_TRONG_CHU = re.compile(r"\d[\d.,]*")
_CHAM_NGHIN = re.compile(r"^\d{1,3}(\.\d{3})+$")


def _gia_tri(v):
    """value cua bars: so, hoac chuoi so kieu Viet ('2,75' thap phan, '1.200'
    hang nghin).

    Truoc 06/09/2026 chi doi ',' thanh '.', con dau CHAM giu nguyen — nen
    float("1.200") = 1.2. Kite viet "1.200 tac vu" (dung kieu Viet, dung cai
    docstring noi la chap nhan) canh mot cot "900" thi cot 1.200 ve rong 0.1%
    con cot 900 ve rong 100%: bieu do noi NGUOC han so lieu, trong khi chu tren
    cot van ghi dung "1.200 tac vu". Cong khong bat vi 1.2 van la so >= 0.

    Chi hong khi TRON dinh dang trong cung mot slide — moi cot cung viet cham
    hang nghin thi deu chia 1000, ti le van dung — nhung "so 4 chu so canh so 3
    chu so" chinh la canh hay gap nhat.
    """
    if isinstance(v, bool):
        raise ValueError("value phai la so")
    if isinstance(v, (int, float)):
        return float(v)
    t = str(v).strip().replace(" ", "")
    if "," in t:
        # kieu Viet day du: cham la hang nghin, phay la thap phan
        return float(t.replace(".", "").replace(",", "."))
    if _CHAM_NGHIN.match(t):
        return float(t.replace(".", ""))
    return float(t)                       # "2.75" kieu Anh: cham la thap phan


def s_bars(sl, th):
    """Bieu do cot ngang tu so THAT trong bai: nhan | thanh | gia tri. Be rong
    theo cot lon nhat; cot co 'nhan': true (mac dinh cot dau) mau chinh, con
    lai mau phu. Khong co truc/luoi: 2..6 cot, doc trong 3 giay."""
    items = sl.get("bars", [])
    vals = [_gia_tri(b["value"]) for b in items]
    vmax = max(vals, default=0.0) or 1.0
    co_nhan = any(b.get("nhan") for b in items)
    rows = ""
    for i, (b, v) in enumerate(zip(items, vals)):
        pct = max(0.0, min(100.0, v / vmax * 100))
        cls = "bar-fill nhan" if (b.get("nhan") or (i == 0 and not co_nhan)) else "bar-fill"
        rows += (f'<div class="bar"><span class="bar-l">{esc(b["label"])}</span>'
                 f'<span class="bar-track"><span class="{cls}" style="width:{pct:.1f}%;"></span></span>'
                 f'<span class="bar-v">{esc(b.get("text") or _so(v))}</span></div>')
    cap = (f'<div class="fig-cap" style="margin-top:28px;"><span class="fig-bar"></span>'
           f'<span>{esc(sl["caption"])}</span></div>') if sl.get("caption") else ""
    stand = (f'<p class="standfirst" style="font-size:34px;max-width:900px;margin-top:30px;">'
             f'{esc(sl["standfirst"])}</p>') if sl.get("standfirst") else ""
    g = glow("bottom:-120px;left:-140px;width:560px;height:560px;"
             f"background:radial-gradient(circle at center,{rgba(th['a'],0.13)} 0%,{rgba(th['a'],0)} 62%);")
    body = (
        f'<div class="mid" style="margin-top:46px;">'
        f'{eyebrow(sl["eyebrow"])}'
        f'<h1 class="title" style="font-size:76px;margin:24px 0 8px;">{accent_html(sl["title"], sl.get("accent"))}</h1>'
        f'</div>'
        f'<div class="mid" style="margin-top:44px;">{rows}'
        f'<div style="border-bottom:1px solid {th["line"]};"></div>{cap}{stand}</div>'
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
    "loop": s_loop, "figure": s_figure, "bars": s_bars, "cta": s_cta,
}


def slide_doc(sl, idx, total, brand, section, folio_left, font_css, th):
    kind = sl.get("kind")
    if kind not in BUILDERS:
        raise SystemExit(f"slide {idx}: kind khong hop le '{kind}' "
                         f"(chon: {', '.join(BUILDERS)})")
    body = BUILDERS[kind](sl, th)
    # slide cta có thể ghi 'follow' vào folio trái thay nhãn mặc định
    fol_left = sl["follow"] if kind == "cta" and sl.get("follow") else folio_left
    # slide cta đã có follow (vd "Theo dõi @donniechublog") thì header bỏ chữ,
    # chỉ giữ hairline — tránh nhắc nhận diện kênh 2 lần trên cùng một slide.
    bare = kind == "cta" and bool(sl.get("follow"))
    inner = masthead(brand, section, bare=bare) + body + folio(fol_left, idx, total)
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>'
            f'{font_css}{base_css(th)}</style></head><body>'
            f'<div class="art">{inner}</div></body></html>')


# ---- cổng chặn ------------------------------------------------------------
# "Nguon:" / "nguon tu" dau mot cum dan nguon — KHONG khop "ma nguon mo",
# "nguon von", "nguon dien", "tai nguyen".
_DAN_NGUON_SAI = re.compile(
    r"(?<!\bmã\s)\bnguồn\s*[:—-]"          # "Nguồn: X", "nguồn — X"
    r"|\bnguồn\s+(?:tin|từ|theo|bài|ảnh|dữ liệu|số liệu)\b"
    r"|\btheo\s+nguồn\b",
    re.I)


# Truong BAT BUOC cua tung kind — kiem TRONG gate_slides, tuc TRUOC khi mo
# Chromium (doi 06/09/2026 dot 2).
#
# Truoc day bang nay chi song o kite_nop.py va gate_slides khong kiem truong nao
# ca: mot spec thieu `standfirst` o slide 4 di qua cong sach se, render() mo
# Chromium, roi `s_statement` nem KeyError THO. Neu no ra o vong chup thu hai
# (:1281) thi mot phan album da nam trong drafts/ — dung cai album cut ma thiet
# ke hai vong sinh ra de tranh. Va moi duong khong di qua nop (goi thang
# render_edu, `--spec -`) thi truoc gio khong co cong nao.
#
# `long`: (ten danh sach, cac khoa moi phan tu phai co).
BAT_BUOC_KIND = {
    "cover":     {"truong": ("eyebrow", "title", "standfirst")},
    "statement": {"truong": ("eyebrow", "title", "standfirst"),
                  "long": ("cards", ("num", "text"))},
    "steps":     {"truong": ("eyebrow", "title", "steps"),
                  "long": ("steps", ("title", "desc"))},
    "loop":      {"truong": ("eyebrow", "title", "standfirst", "callout", "chips")},
    "figure":    {"truong": ("eyebrow", "title", "standfirst", "image", "caption"),
                  "long": ("cards", ("num", "text"))},
    "bars":      {"truong": ("eyebrow", "title", "standfirst", "caption", "bars"),
                  "long": ("bars", ("label", "value"))},
    "cta":       {"truong": ("eyebrow", "title", "checks")},
}


def kiem_truong(slides) -> list:
    """Thieu truong bat buoc / kind la — bat o day, khong de builder nem."""
    loi = []
    for i, sl in enumerate(slides, 1):
        kind = sl.get("kind")
        if kind not in BUILDERS:
            loi.append(f"slide {i}: kind {kind!r} khong co — chon mot trong "
                       + ", ".join(sorted(BUILDERS)))
            continue
        q = BAT_BUOC_KIND.get(kind, {})
        for k in q.get("truong", ()):
            if not sl.get(k):
                loi.append(f"slide {i} [{kind}]: thieu '{k}'")
        ten_ds, khoa = q.get("long", (None, ()))
        if ten_ds:
            for j, muc in enumerate(sl.get(ten_ds) or [], 1):
                if not isinstance(muc, dict):
                    loi.append(f"slide {i} [{kind}]: {ten_ds}[{j}] phai la object")
                    continue
                for k in khoa:
                    if muc.get(k) in (None, ""):
                        loi.append(f"slide {i} [{kind}]: {ten_ds}[{j}] thieu '{k}'")
        # `readmore` cua cta la tuy chon, nhung co thi phai du hai khoa
        rm = sl.get("readmore")
        if isinstance(rm, dict):
            for k in ("label", "text"):
                if not rm.get(k):
                    loi.append(f"slide {i} [{kind}]: readmore thieu '{k}'")
    return loi


def gate_slides(slides, bo_qua_dau):
    # Truong bat buoc TRUOC tien. Kind LA thi dung han (moi cong duoi deu gia
    # dinh kind hop le); thieu truong thi van chay tiep cac cong con lai de vai
    # nhan DU loi trong mot lan thay vi sua ba vong. Cac cong duoi doc bang
    # `.get` nen thieu truong khong lam chung nem — con neu co gi nem that thi
    # bat lai o duoi, danh sach loi da co van duoc tra ve.
    loi = kiem_truong(slides)
    if any("kind" in d and "khong co" in d for d in loi):
        return loi
    try:
        loi += _gate_noi_dung(slides, bo_qua_dau)
    except Exception as e:                                   # noqa: BLE001
        loi.append(f"[cong noi dung dung giua chung: {type(e).__name__}: {e} — "
                   "sua cac loi tren truoc roi chay lai]")
    return loi


def _gate_noi_dung(slides, bo_qua_dau):
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
                mat = tieng_viet.tim_mat_dau(t)
                if mat:
                    loi.append(f"slide {i} [{nhan}]: tieng Viet mat dau ({', '.join(mat)})")
    # slide figure: anh phai co that va phai du to. Anh 600px keo len 1080px
    # (roi chup o scale 2 nua) thi chu tren bieu do nhoe thanh vet — dang len
    # la ca bo hong, ma luc dung khong ai nhin ra tren man to.
    for i, sl in enumerate(slides, 1):
        if sl.get("kind") == "figure" and not sl.get("image"):
            loi.append(f"slide {i}: kind 'figure' phai co 'image' (duong dan tep anh)")
            continue
        if not sl.get("image"):        # bia thi anh la tuy chon
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
            loi.append(f"slide {i}: slide co anh phai co 'caption' — hinh muon "
                       f"cua nguoi ta thi phai ghi 'via <ai>'.")

    # bars: so that, 2..6 cot, nhan ngan, caption via (so muon cua bai)
    for i, sl in enumerate(slides, 1):
        if sl.get("kind") != "bars":
            continue
        items = sl.get("bars") or []
        if not 2 <= len(items) <= 6:
            loi.append(f"slide {i}: kind 'bars' can 2..6 cot (co {len(items)})")
        for j, b in enumerate(items, 1):
            if not isinstance(b, dict) or not b.get("label"):
                loi.append(f"slide {i}: cot {j} thieu 'label'")
                continue
            if len(b["label"]) > 28:
                loi.append(f"slide {i}: cot {j} label {len(b['label'])} ky tu, toi da 28")
            try:
                gt = _gia_tri(b.get("value"))
                if gt < 0:
                    raise ValueError
            except (ValueError, TypeError):
                loi.append(f"slide {i}: cot {j} 'value' phai la so >= 0 (co: {b.get('value')!r})")
                continue
            # `text` la thu NGUOI DOC nhin thay tren cot, `value` la thu quyet
            # dinh CHIEU DAI cot. Hai cai lech nhau thi bieu do noi mot dang, chu
            # noi mot dang — va khong cong nao bat duoc neu khong doi chieu.
            so_text = _SO_TRONG_CHU.search(str(b.get("text") or ""))
            if so_text:
                try:
                    gt_text = _gia_tri(so_text.group(0))
                except (ValueError, TypeError):
                    gt_text = None
                if gt_text is not None and abs(gt_text - gt) > max(0.01, abs(gt) * 0.01):
                    loi.append(f"slide {i}: cot {j} 'text' ghi {so_text.group(0)!r} nhung "
                               f"'value' la {b.get('value')!r} (doc ra {gt:g}) — chieu dai "
                               "cot se khong khop con so nguoi doc nhin thay")
        if not sl.get("caption"):
            loi.append(f"slide {i}: kind 'bars' phai co 'caption' ghi 'via <ai>' — so la cua bai, khong phai cua ta")

    # Quy uoc dan nguon: dung 'via', khong viet 'nguon'.
    #
    # CHI bat mau DAN NGUON, khong bat moi chu "nguon" (sua 06/09/2026 dot 2).
    # Ban cu `if "nguồn" in low` chan oan "mo hinh mã nguồn mở", "nguồn vốn",
    # "nguồn điện" — rieng "mã nguồn mở" co trong gan nhu moi tin model, va
    # khong co co nao lach duoc, nen Kite bi day thang vao vong "sua 3 lan roi
    # bi chan" ma khong sua duoc gi.
    for i, sl in enumerate(slides, 1):
        for nhan, t in _texts(sl):
            if _DAN_NGUON_SAI.search(t or ""):
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
    for b in sl.get("bars", []):
        out.append(("bar.label", b.get("label", "")))
        if b.get("text"):
            out.append(("bar.text", b["text"]))
    if sl.get("readmore"):
        out.append(("readmore", sl["readmore"].get("text", "")))
    return out



# ---- chon theme / hero ------------------------------------------------------
def _nhat_ky_theme() -> Path:
    """state/<brand>/edu_theme_da_dung.jsonl — so theme/hero da dung gan day.

    Truoc 06/09/2026 tep nay nam o `state/` GOC, tuc dung chung cho ca hai
    brand. Kite gio chay cho ca hai, nen bo "4 bo gan nhat" tron lan: mot bo
    dcgr vua dung theme X la bo blog ke tiep bi day sang theme khac ma khong
    co ly do nao — hai kenh khac nhau, nguoi doc khac nhau.

    Goi ham chu khong phai hang o cap module: `env_load.state_dir()` doc
    CT_BRAND luc CHAY, con hang thi chot luc import.
    """
    import env_load
    return env_load.state_dir() / "edu_theme_da_dung.jsonl"


def _theme_gan_day(n=4):
    """[(theme, hero)] cua n bo gan nhat, moi nhat truoc."""
    if not _nhat_ky_theme().exists():
        return []
    rows = []
    for line in _nhat_ky_theme().read_text("utf-8").splitlines():
        try:
            d = json.loads(line)
            rows.append((d.get("theme"), d.get("hero")))
        except Exception:
            continue
    return rows[::-1][:n]


def _ghi_theme(out, theme, hero):
    try:
        _nhat_ky_theme().parent.mkdir(parents=True, exist_ok=True)
        with open(_nhat_ky_theme(), "a", encoding="utf-8") as f:
            f.write(json.dumps({"out": str(out), "theme": theme, "hero": hero},
                               ensure_ascii=False) + "\n")
    except OSError:
        pass


NGUONG_HUE_LECH_MAU = 0.28    # >nguong nay (vong tron hue, 0..0.5) la LECH TONG
TI_LE_ANH_CO_MAU = 0.01       # duoi muc nay pixel co mau tren CA TAM -> anh coi nhu khong mau
TI_LE_MAU_AP_DAO = 0.05       # mau noi bat phai chiem tung nay so pixel DA LOC


def mau_noi_bat(path) -> tuple | None:
    """Mau NOI BAT nhat trong mot anh that (bia/hero) — hue HSV pho bien nhat
    trong vung du bao hoa, bo qua nen trang/den/xam. None neu anh khong co mau
    ro net nao (vd anh den-trang, anh gan nhu khong con pixel mau nao sau khi
    loc, hoac mau noi bat khong chiem du ty le de tin cay — < 5% so pixel da
    loc).

    Dung de chon THEME khop mau voi anh that: khac vector Kite tu ve theo mau
    theme, anh that (chup man hinh bang xep hang, anh bao...) mau CO SAN,
    khong doi duoc — theme phai chay theo anh, khong phai nguoc lai."""
    from PIL import Image
    import colorsys
    try:
        with Image.open(path) as im:
            im = im.convert("RGB").resize((80, 80))
            n = im.width * im.height
            dem: dict = {}
            for r, g, b in im.getdata():
                h, s, v = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
                # s < 0.35 da loai trang/xam; KHONG loai them v > 0.97 — do la
                # loai moi mau bao hoa thuan (do (255,0,0), vang, chinh accent
                # #FFB454 cua theme ember), tuc anh chart mau tuoi ra None roi
                # roi ve xoay vong mu mau (audit lượt 2, R-r2-1).
                if s < 0.35 or v < 0.25:
                    continue                  # xam/qua toi -> khong tinh la "mau"
                # 24 khoang ~15 do; % 24 vi round(h*24) cho 0..24 ma 0 va 24 la
                # CUNG mau do (vong tron hue) — khong gop thi do bi chia doi hai
                # bucket, thua mau khac it hon (R-r2-2).
                bucket = round(h * 24) % 24
                dem[bucket] = dem.get(bucket, 0) + 1
    except (OSError, ValueError):
        return None
    if not dem:
        return None
    tong_loc = sum(dem.values())
    bucket, dinh = max(dem.items(), key=lambda kv: kv[1])
    # Do do AP DAO tren so pixel DA LOC, khong tren tong pixel: anh logo hang la
    # mot mark mau nam tren NEN SANG, nen sang da bi bo loc s<0.35 gat het roi ma
    # van dem chia cho ca tam thi logo nao nho hon 5% dien tich cung ket luan
    # "khong co mau" — DeepSeek (xanh #4D6CF7) roi ve vong xoay mu mau, ra theme
    # moss xanh la (LOW-11). Sang TI_LE_ANH_CO_MAU giu cho vai pixel nhieu le
    # khong tu quyet theme cho ca bo.
    if tong_loc / n < TI_LE_ANH_CO_MAU or dinh / tong_loc < TI_LE_MAU_AP_DAO:
        return None
    r, g, b = colorsys.hsv_to_rgb(bucket / 24, 0.65, 0.85)
    return (round(r * 255), round(g * 255), round(b * 255))


def lech_hue(rgb, ten: str) -> float:
    """Khoang cach hue (vong tron, 0..0.5) giua `rgb` va accent chinh cua theme."""
    import colorsys
    h0, _, _ = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    a = THEMES[ten]["a"].lstrip("#")
    r, g, b = (int(a[i:i + 2], 16) for i in (0, 2, 4))
    h1, _, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    d = abs(h0 - h1)
    return min(d, 1 - d)


def theme_gan_mau(rgb) -> str | None:
    """Ten THEME co mau `a` (accent chinh) GAN NHAT voi `rgb` theo khoang cach
    hue tren vong tron mau. None neu rgb la None (anh khong co mau ro ret)."""
    if rgb is None:
        return None
    return min(THEMES, key=lambda ten: lech_hue(rgb, ten))


def mau_hang_trong_spec(spec) -> tuple | None:
    """Mau nhan dien cua hang duoc nhac toi trong spec, hoac None.

    Tra cuu CUNG mot bang voi cho to ten hang trong tieu de cua Ethan
    (`card.MAU_HANG` / `MAU_CUM`) — mot bang mau cho ca doi, khong dung bang
    thu hai roi de hai cho troi khoi nhau.

    Doc `folio` TRUOC roi moi toi eyebrow/title cua bia: folio la nhan chu de
    ("GOOGLE ANTIGRAVITY"), gan nhu luon la chinh chu the cua tin, con title
    thi hay nhac hang khac trong cau so sanh ("... vuot GPT-5")."""
    import card
    bia = (spec.get("slides") or [{}])[0]
    for text in (spec.get("folio"), bia.get("eyebrow"), bia.get("title")):
        mau = card._mau_hang_trong(text or "")
        if mau:
            return mau
    return None


def chon_theme_tu_dong(spec, bia_anh=False, anh_mau=None):
    """Spec khong ghi theme/hero -> chon cai IT DUNG NHAT gan day, va khong bao
    gio trung voi bo vua dung truoc. Ghi ro thi ton trong, nhung neu trung
    het ca theme lan hero voi bo ngay truoc thi bao de Kite biet (khong chan:
    Ong Chu co the co y muon mot loat cung tone).

    `bia_anh`: bia dung anh that -> ca bo khong ve hero nao, tra hero=None.
    `anh_mau`: duong dan anh bia (khi bia_anh) — mau NOI BAT cua no, neu ro
    ret, se CHON THEME KHOP MAU thay vi xoay vong (khi spec chua ghi theme),
    va CANH BAO neu spec DA ghi mot theme lech mau xa (Ong Chu 09/09/2026:
    "hình thì tông green, yellow mà slide thì toàn pink purple ko được liên
    quan lắm" — anh that mau CO SAN, theme phai chay theo no).

    THU TU chon mau cho theme (Ong Chu chot 10/09/2026, LOW-11):
      1. mau NOI BAT cua anh bia that — manh nhat, khong doi duoc;
      2. mau NHAN DIEN CUA HANG nhac trong spec (`card.MAU_HANG`) — palette
         cua slide di cung mau brand, giong cho to ten hang cua Ethan;
      3. xoay vong cho khoi lap bo truoc — chi khi ca hai tren deu khong co.
    Nen mot loat tin cung hang se cung tone: do la y muon, khong phai trui."""
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

    rgb = mau_noi_bat(anh_mau) if (bia_anh and anh_mau) else None
    nguon = "anh bia"
    if rgb is None:
        # Anh bia khong co mau ro ret (hoac bia ve vector): bam MAU NHAN DIEN
        # CUA HANG duoc nhac toi, thay vi xoay vong mu mau — tin DeepSeek (xanh
        # #4D6CF7) tung ra slide theme moss xanh la (LOW-11). Tang nay chi do
        # cho cho VONG XOAY, khong dung tren mau anh that: luat 09/09/2026
        # "anh that mau co san, theme phai chay theo anh" van thang.
        rgb = mau_hang_trong_spec(spec)
        nguon = "mau hang nhac trong spec"
    theme_khop_mau = theme_gan_mau(rgb)
    if not theme:
        theme = theme_khop_mau or it_dung_nhat(list(THEMES), [t for t, _ in gan], seed)
    elif theme_khop_mau and theme != theme_khop_mau and lech_hue(rgb, theme) > NGUONG_HUE_LECH_MAU:
        # R-r2-3: chi bao khi theme DA CHON lech tong ro (qua nguong), khong
        # phai moi khi no khac theme gan nhat — moss (0.37) vs orbit (0.51)
        # lech 0,08 la cung tong, bao la nhieu.
        r, g, b = rgb
        print(f"CANH BAO: theme={theme} LECH MAU voi {nguon} (mau "
              f"#{r:02X}{g:02X}{b:02X}, hop voi theme={theme_khop_mau} hon) — "
              "mau do co san, doi theme cho khop thay vi doi mau.",
              file=sys.stderr)
    if bia_anh:
        hero = None
    elif not hero:
        hero = it_dung_nhat(list(HEROES), [h for _, h in gan], seed // 7)
    if gan and gan[0] == (theme, hero):
        print(f"CANH BAO: theme={theme} hero={hero} TRUNG voi bo ngay truoc "
              f"({gan[0]}). Neu la 'lam lai' thi phai doi.", file=sys.stderr)
    return theme, hero

# ---- render ---------------------------------------------------------------
def _route_font(page) -> dict:
    """Phuc vu font TU DIA cho moi yeu cau toi FONT_URL. Tra ve bo dem da phuc vu.

    Chan tai `FONT_URL` nen KHONG bao gio ra mang that. Bo dem de nguoi goi biet
    font co thuc su duoc nap khong: khac voi `data:` URL (khong bao giu hong),
    route hong thi Chromium lang le roi ve font he thong va ca album sai chu."""
    dem = {"phuc_vu": 0}

    def _tra(route, request):
        ten = request.url.rsplit("/", 1)[-1]
        fp = FONTS_DIR / ten
        # Chi phuc vu tep NGAY TRONG assets/fonts, khong di theo "../".
        if fp.parent.resolve() != FONTS_DIR.resolve() or not fp.exists():
            route.abort()
            return
        dem["phuc_vu"] += 1
        route.fulfill(status=200, body=fp.read_bytes(),
                      headers={"content-type": "font/ttf",
                               "cache-control": "max-age=86400"})

    page.route(FONT_URL + "*", _tra)
    return dem


def _kiem_tieu_de_dong(page, browser, slides, dung_doc):
    """Cong chan DO THAT: tieu de tren slide co anh toi da FIG_TIEU_DE_DONG dong,
    do bang chinh Chromium. Chay het mot luot TRUOC khi chup — hong thi khong de
    lai nua album trong drafts/ cho Kite tuong la xong."""
    # Cong chan DO THAT: tieu de tren slide co anh toi da 2 dong. Dem chu
    # thi doan sai (dau tieng Viet, tu dai ngan khac nhau), nen dung chinh
    # Chromium do. Chay het mot luot TRUOC khi chup, de neu hong thi khong
    # de lai nua album trong drafts/ cho Kite tuong la xong.
    loi_dong = []
    for i, sl in enumerate(slides, start=1):
        if not sl.get("image"):
            continue
        page.set_content(dung_doc(sl, i), wait_until="load")
        page.evaluate("document.fonts.ready")
        n = page.evaluate(
            "() => {const h=document.querySelector('#figtxt h1');"
            "if(!h) return 0;"
            "const lh=parseFloat(getComputedStyle(h).lineHeight);"
            "return Math.round(h.getBoundingClientRect().height/lh);}")
        if n > FIG_TIEU_DE_DONG:
            loi_dong.append(
                f"slide {i}: tieu de {n} dong — slide co anh chi cho "
                f"{FIG_TIEU_DE_DONG} dong. Anh da noi phan viec cua no roi, "
                f"tieu de dai them la giam cua nhau. Cat ngan tieu de lai.")
    if loi_dong:
        browser.close()
        print("CONG CHAN DUNG:", file=sys.stderr)
        for x in loi_dong:
            print("  - " + x, file=sys.stderr)
        raise SystemExit(1)


def _chup_cac_slide(page, slides, dung_doc, out, stem):
    """Chup tung slide ra PNG; slide 1 la `out`, con lai `<stem>_<i>.png`."""
    outs = []
    for i, sl in enumerate(slides, start=1):
        doc = dung_doc(sl, i)
        page.set_content(doc, wait_until="load")
        page.evaluate("document.fonts.ready")
        # Font doi chieu cao dong -> doi luon cho dong chu dau. Dat lai man
        # toi SAU khi font xong, khong thi mep man lech khoi khoi chu.
        page.evaluate("window.__datMan && window.__datMan()")
        page.wait_for_timeout(120)
        path = out if i == 1 else Path(f"{stem}_{i}.png")
        page.screenshot(path=str(path),
                        clip={"x": 0, "y": 0, "width": W, "height": H})
        outs.append(path)
    return outs


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
    # Hero art CHI ve tren bia. Bia dung anh that thi ca bo khong co hero nao —
    # van ghi hero vao nhat ky la lan sau no tranh mot hero chua tung xuat hien,
    # xoay sai. Ghi None cho dung.
    bia_anh = bool(slides and slides[0].get("image"))
    theme, hero = chon_theme_tu_dong(spec, bia_anh, slides[0].get("image") if bia_anh else None)
    th = dict(THEMES[theme], hero=hero)
    print(f"theme={theme} hero=" + (hero or "- (bia dung anh that)"))

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise SystemExit(
            "Thieu Playwright. Tren server:\n"
            "  venv/bin/pip install playwright\n"
            "  venv/bin/playwright install chromium")

    out = Path(out)
    stem = out.with_suffix("")
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        ctx = browser.new_context(viewport={"width": W, "height": H},
                                  device_scale_factor=scale)
        page = ctx.new_page()

        dem_font = _route_font(page)

        def dung_doc(sl, i):
            return slide_doc(sl, i, total, brand, section, folio_left, font_css, th)

        _kiem_tieu_de_dong(page, browser, slides, dung_doc)
        outs = _chup_cac_slide(page, slides, dung_doc, out, stem)
        # Font phuc vu qua route thi PHAI co it nhat mot luot. Zero nghia la
        # Chromium da roi ve font he thong: album van ra anh, chi la sai chu —
        # dung loai hong ma nhin anh moi biet, nen chan o day.
        if not dem_font["phuc_vu"]:
            browser.close()
            raise SystemExit(
                "KHONG font nao duoc nap qua page.route — album se sai chu.\n"
                f"Kiem assets/fonts va FONT_URL ({FONT_URL}) trong render_edu.py.")
        browser.close()
    _ghi_theme(out, theme, hero)   # hero=None khi bia dung anh that
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
