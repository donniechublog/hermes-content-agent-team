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
    # thi them "image": bia lay chinh hinh do lam hero, khong ve so do nua.
    # Hinh that bao gio cung noi duoc nhieu hon mot so do trang tri. KHONG ghi
    # nguon anh len slide (LOW-292) — nguon nam o ban giao + metadata PNG.
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
     "image": "drafts/chart_swebench.png",   # chụp bằng capture_chart.py
     "standfirst": "Chữ minh hoạ cho phần chiều cao còn thừa dưới hình.",
     "cards": [{"num": "01", "text": "..."}]},

    # Khong co hinh that nhung bai co vai con so: bieu do cot ngang tu so THAT
    # (2..6 cot, "value" la so, "text" la cach ghi). `caption` o day la nguon
    # CON SO (bat buoc) — khong phai nguon anh, nen LOW-292 khong dung toi.
    {"kind": "bars", "eyebrow": "SỐ LIỆU",
     "title": "Chi phí mỗi task giảm ba lần", "accent": "ba lần",
     "bars": [{"label": "Trước", "value": 2.75, "text": "2,75 USD"},
              {"label": "Sau boost", "value": 0.9, "text": "0,90 USD", "highlight": true}],
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
dòng chữ đầu tiên (không có khoảng đệm để trống phía trên chữ). Ảnh phải rộng
>= 800px (chụp bằng capture_chart.py). Slide KHÔNG ghi dòng nguồn ảnh (LOW-292).
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
import vietnamese  # noqa: E402  (cùng thư mục) — chỉ cần cổng chữ, không cần PIL
# đo tương phản WCAG dùng CHUNG với card.py/Ethan + itachi_submit.py — xem LOW-9
import text_bg  # noqa: E402
# nhan dien + mau ten hang dung chung ca doi designer — LOW-344
import brand_names  # noqa: E402
import safe_zone  # noqa: E402

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
    # Palette THEO HANG (LOW-340, Ong Chu 21/09/2026): tin DeepSeek (xanh duong
    # · xam · trang) ra slide xanh la "moss". Tin ve mot hang co mau nhan dien
    # ro thi palette di theo hang, khong theo tam trang. Chi dung qua
    # BRAND_THEME (khong tham gia so hue / xoay vong). Mau goc cua hang ghi ben
    # canh; mau nao thieu tuong phan tren nen toi da tron them trang (giu hue)
    # cho toi >= 5:1 — tests/test_low340_brand_palettes.py khoa nguong 4.5.
    "deepseek":    dict(bg="#141821", panel="#1D2330", line="#303848",
                        a="#7189FE", b="#C3C9D4", stand="#C9CFDA"),  # #4D6BFE x xam x trang
    "anthropic":   dict(bg="#1F1D1A", panel="#2A2723", line="#3E3A33",
                        a="#DB7E5F", b="#F0EEE6", stand="#D3CCC0"),  # cam dat Claude #D97757 x nga
    "gemini":      dict(bg="#141824", panel="#1D2334", line="#2F3850",
                        a="#4796E3", b="#9D86CD", stand="#C4CBDB"),  # xanh #4796E3 x tim #9177C7
    "meta":        dict(bg="#121821", panel="#1A2330", line="#2B3648",
                        a="#2493FC", b="#C5CCD6", stand="#C3CBD8"),  # xanh Meta #0081FB x xam
    "qwen":        dict(bg="#17162A", panel="#211F38", line="#34314F",
                        a="#8885F2", b="#C9C6F5", stand="#CCC9E0"),  # tim Qwen #615CED x lavender
    "mistral":     dict(bg="#1D1611", panel="#29201A", line="#40322A",
                        a="#FF8205", b="#FFD800", stand="#D6C8BA"),  # cam x vang Mistral
    "nvidia":      dict(bg="#141612", panel="#1E211A", line="#33382B",
                        a="#76B900", b="#D0D0D0", stand="#C8CCC0"),  # xanh NVIDIA x xam
    "huggingface": dict(bg="#1D1A12", panel="#29251A", line="#403A2A",
                        a="#FFD21E", b="#FF9D00", stand="#D6CDB8"),  # vang x cam Hugging Face
    "perplexity":  dict(bg="#091717", panel="#122222", line="#1F3535",
                        a="#20B8CD", b="#FBFAF4", stand="#C2D0CE"),  # ngoc x trang giay
}
# 5 theme tam trang: dung cho tin KHONG gan hang co palette — so hue voi anh
# bia / mau hang, va xoay vong. Palette hang khong vao day: mot tin Microsoft
# anh xanh khong duoc ra palette Meta chi vi hue gan.
MOOD_THEMES = ("orbit", "ember", "moss", "ink", "rose")
# Khoa hang (tuple cua `card._extract_label`) -> palette hang.
BRAND_THEME = {
    ("DEEPSEEK",): "deepseek",
    ("ANTHROPIC",): "anthropic", ("CLAUDE",): "anthropic",
    ("GOOGLE",): "gemini", ("GEMINI",): "gemini", ("DEEPMIND",): "gemini",
    ("META",): "meta", ("META", "AI"): "meta", ("LLAMA",): "meta",
    ("QWEN",): "qwen",
    ("MISTRAL",): "mistral", ("MISTRAL", "AI"): "mistral",
    ("NVIDIA",): "nvidia",
    ("HUGGING", "FACE"): "huggingface",
    ("PERPLEXITY",): "perplexity",
}
# Hang tong chu dao DEN TRANG: khong can palette — nen toi chu trang cua Kite
# da la tone do (Ong Chu 21/09/2026). Bang mau cua Ethan (`card.COLOR_RANK`)
# van cho OpenAI xanh la / Kimi xanh duong de to TEN hang, nen phai liet ke;
# hang co mau xam trong COLOR_RANK thi `is_mono_brand` tu nhan theo do bao hoa.
MONO_BRANDS = {("OPENAI",), ("CHATGPT",), ("KIMI",), ("MOONSHOT",)}
# Noi dang model/ma nguon, khong phai chu the: tin "deepseek-ai/... tha trong so
# tren Hugging Face" la tin DeepSeek. Chi tinh khi khong nhac hang nao khac.
PLATFORM_BRANDS = {("HUGGING", "FACE"), ("GITHUB",)}
HEROES = ("orbit", "grid", "wave", "rings", "graph")   # ten hero SVG tren bia

W, H = 1080, 1350
# LOW-366/391: o vuong Instagram cat 4:5 (lech len ~20px so voi tam). Chu cua slide — masthead
# tren, folio duoi — phai nam trong vung an toan, khong thi dang 1:1 mat dong chan
# "@dcgr.tech - Phan tich - N phut doc" va nua masthead. Le hai ben giu 80px nhu cu.
PAD_TOP = safe_zone.top(W, H)            # 127
PAD_BOT = H - safe_zone.bottom(W, H)     # 167

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
  overflow:hidden;padding:%(PAD_TOP)spx 80px %(PAD_BOT)spx;display:flex;flex-direction:column;
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
.brand{color:var(--bc);}
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
/* LOW-366: le tren/duoi cua slide theo vung an toan nen cot chu thap hon 134px — slide
   `steps` la kieu day nhat, thu khoang dem moi buoc 26 -> 12px cho vua (do that: tran 47px). */
.step{display:flex;flex-direction:row;align-items:flex-start;gap:32px;
  padding:12px 0;border-top:1px solid %(LINE)s;}
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
/* LOW-366: slide `bars` von da tran SAN tren main (do that: folio bi day xuong 1338..1384, tuc
   dong chan mat hut khi dang). Le theo vung an toan lam cot chu thap hon 134px nua, nen thu
   khoang dem va chieu cao thanh cho vua — buoc thu khoang trang (`__fitSafe`) lo hang thi cong
   chan bao vai cat chu. */
.bar{display:flex;flex-direction:row;align-items:center;gap:22px;padding:6px 0;}
.bar-l{font-family:%(MONO)s;font-size:26px;font-weight:700;color:%(SOFT)s;
  flex:none;width:300px;line-height:1.2;}
.bar-track{flex-grow:1;height:40px;background:%(PANEL)s;border:1px solid %(LINE)s;
  position:relative;}
.bar-fill{position:absolute;left:0;top:0;bottom:0;background:%(VIOLET)s;}
.bar-fill.highlight{background:%(CYAN)s;}
.bar-v{font-family:%(MONO)s;font-size:30px;font-weight:700;color:%(WHITE)s;
  flex:none;width:190px;text-align:right;}
/* hinh that: phu kin the, KHONG bao gio la mot hop dat canh chu */
.figwrap{position:absolute;left:0;top:0;width:%(W)spx;height:%(H)spx;
  z-index:0;overflow:hidden;background:%(BG)s;}
.fig-sac{position:absolute;left:0;width:%(W)spx;object-fit:cover;display:block;}
/* lop MO cua chinh anh, chi hien tu dong chu dau tro xuong khi anh DOC chom qua
   vung chu (bang xep hang); anh ngang ket thuc tren chu thi lop nay display:none */
.fig-molop{position:absolute;left:0;top:0;width:%(W)spx;height:%(H)spx;overflow:hidden;}
.fig-molop img{position:absolute;left:0;width:%(W)spx;object-fit:cover;display:block;
  filter:blur(14px);}
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


# LOW-366: cot chu cua slide phai nam TRON trong vung an toan (masthead tren, folio duoi) vi o
# vuong Instagram cat 4:5. Le tren/duoi da lay tu `safe_zone`, nhung slide day chu (`steps`,
# `bars`, `loop`, cover chu dai) van tran — va `bars` thi tran SAN tu truoc (do tren main: folio
# bi day xuong 1338..1384, tuc dong chan mat hut khi dang). Thay vi chinh tay tung kieu slide,
# thu KHOANG TRANG cho vua: nhan cac khoang dem doc (margin cua khoi `.mid`, padding cua
# `.step`/`.bar`, khoang cua tieu de) voi mot he so <= 1, khong dong toi co chu. Con tran sau khi
# thu het muc thi la chu qua dai — cong chan bao vai cat bot.
FIT_MIN_SPACE = 0.45             # thu khoang trang toi da con bay nhieu phan
FIT_JS = """
window.__fitSafe = function (top_limit, bottom_limit) {
  const art = document.querySelector('.art');
  const mast = document.querySelector('.mast');
  if (!art) return null;
  // Day cot chu: khoi chu cuoi cung cua slide (nen va anh la lop tuyet doi, khong tinh).
  const cot = () => [...art.children]
    .filter(e => !e.classList.contains('figwrap') && !e.classList.contains('glow'))
    .reduce((m, e) => Math.max(m, e.getBoundingClientRect().bottom), 0);
  const over = () => cot() - bottom_limit;
  const bao = (factor) => ({factor: factor, over: over(),
    mast_top: mast ? Math.round(mast.getBoundingClientRect().top) : null,
    text_bottom: Math.round(cot()), top_limit: top_limit, bottom_limit: bottom_limit});
  if (over() <= 0) return bao(1);
  const nodes = [];
  art.querySelectorAll('.mid, .mid > *, .step, .bar, .chips, .card, .callout').forEach(e => {
    const cs = getComputedStyle(e);
    nodes.push({e: e, mt: parseFloat(cs.marginTop) || 0, mb: parseFloat(cs.marginBottom) || 0,
                pt: parseFloat(cs.paddingTop) || 0, pb: parseFloat(cs.paddingBottom) || 0});
  });
  let factor = 1;
  for (let k = 0; k < 12; k++) {
    factor = Math.max(%(FIT_MIN)s, factor - 0.05);
    nodes.forEach(n => {
      n.e.style.marginTop = (n.mt * factor) + 'px';
      n.e.style.marginBottom = (n.mb * factor) + 'px';
      n.e.style.paddingTop = (n.pt * factor) + 'px';
      n.e.style.paddingBottom = (n.pb * factor) + 'px';
    });
    if (over() <= 0 || factor <= %(FIT_MIN)s) break;
  }
  return bao(factor);
};
""" % {"FIT_MIN": FIT_MIN_SPACE}


def base_css(th):
    return BASE_CSS_TPL % {
        "W": W, "H": H, "PAD_TOP": PAD_TOP, "PAD_BOT": PAD_BOT,
        "BG": th["bg"], "PANEL": th["panel"], "LINE": th["line"],
        "WHITE": WHITE, "SOFT": SOFT, "MUTED": MUTED, "DIM": DIM,
        "CYAN": th["a"], "VIOLET": th["b"], "STAND": th["stand"],
        "DISPLAY": _ff("Display"), "SERIF": _ff("EditSerif"), "MONO": _ff("Mono"),
    }


def rgba(hexs, alpha):
    h = hexs.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"

_SVG_HEAD = ('<svg width="100%" viewBox="0 0 920 470" preserveAspectRatio="xMidYMid meet"'
             ' xmlns="http://www.w3.org/2000/svg"'
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
# Be ngang la NOI DUNG (cung luat voi capture_chart.py): mot bieu do bi cat mep
# phai thi mat truc, mat cot cuoi, mat luon cai diem duoc to sang — no NOI SAI
# chu khong phai thieu mot ti. Nen anh LUON trai het 1080px, khong bao gio cat
# hai ben. Chieu cao thi cat duoc: cao qua tran thi giu mep tren, phan con lai
# cua chieu cao slide moi den luot chu minh hoa.
IMAGE_MIME = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
            ".webp": "image/webp", ".gif": "image/gif"}
FIG_EMPTY_MIN = 800    # hep hon the ma keo len 1080 thi be nat

# Bo so lay NGUYEN cua carousel.py (vai Dre) de hai vai noi cung mot thu tieng.
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
# phan ~4.5-5.1:1 — sai huong). Tinh lai bang text_bg.threshold_wall_part (dung
# cong thuc CHUNG voi card.py/Ethan) cho DUNG cap mau THAT dang dung o day,
# thay vi mot con so co dinh dung chung cho ca chu sang tuyet doi lan chu toi
# alpha-blend.
_MAU_CHU_SANG_RGB = tuple(int(WHITE.lstrip("#")[k:k + 2], 16) for k in (0, 2, 4))
_MAU_CHU_TOI_HIEU_DUNG = (38, 38, 38)  # xap xi 0.15 x nen sang (rgba đen 0.85)
THRESHOLD_BRIGHT_TEXT_DARK = round(text_bg.threshold_wall_part(_MAU_CHU_SANG_RGB, _MAU_CHU_TOI_HIEU_DUNG))
FIG_TITLE_LINE = 2   # slide co anh: tieu de toi da bay nhieu dong
FIG_FIXED = 150         # chua masthead: anh khong bao gio tran len day
FIG_BOTTOM_FLAT = 0.63   # anh nen PHANG dung o day; duoi la mat phang sach cho chu
# Lop mo CHI cho phan anh chom xuong vung chu (anh doc keo dai: bang xep hang).
# 955f33b don xac co che nay; dua lai 12/09/2026 sau khi Ong Chu tach hai viec:
# blur ca anh lam nen = KHONG BAO GIO, mo phan anh nam duoi tit/subtitle = CO.
DARK_MAX_OPEN = 0.93   # do dac toi da cua lop tint mau theme phu len phan mo
VEIL_SPAN = 64         # px: be day duong cong chuyen tiep, bat dau NGAY tai dong chu dau
VEIL_LEAD = 48         # px: dai phu bat dau SOM hon dong chu dau chung nay, de kicker nam tren phan da phu (LOW-345)
FLAT_TEXT_GAP = 8       # px: anh nen phang ket thuc TREN dong chu dau it nhat chung nay (LOW-345)


# Mot tam anh bi soi di soi lai: cong chan doc no, cong chan 2 dong dung slide
# mot lan, roi vong chup dung lai lan nua. Rieng doc_nen phai quet toan bo pixel
# va _anh_data_uri phai base64 ca tep — lam lai 3 lan cho mot anh 4MB la phi.
_NHO_ANH = {}


def _small(khoa, lam):
    if khoa not in _NHO_ANH:
        _NHO_ANH[khoa] = lam()
    return _NHO_ANH[khoa]


def _measure_image(duong_dan):
    """-> (Path, rong, cao). Duong dan tuong doi tinh theo CWD truoc, roi ROOT."""
    return _small(("do", str(duong_dan)), lambda: _measure_image_real(duong_dan))


def _measure_image_real(duong_dan):
    p = Path(duong_dan)
    if not p.exists() and not p.is_absolute():
        p = ROOT / duong_dan
    if not p.exists():
        raise FileNotFoundError(f"khong thay anh '{duong_dan}'")
    if p.suffix.lower() not in IMAGE_MIME:
        raise ValueError(f"anh '{p.name}' duoi la {p.suffix} — "
                         f"chi nhan {', '.join(sorted(IMAGE_MIME))}")
    from PIL import Image
    with Image.open(p) as im:
        return p, im.width, im.height


def _image_data_uri(p):
    """Nhung base64: Chromium doc HTML tu chuoi nen khong co URL goc de giai
    duong dan tuong doi (giong ly do font phai nhung)."""
    def build():
        b64 = base64.b64encode(p.read_bytes()).decode("ascii")
        return f"data:{IMAGE_MIME[p.suffix.lower()]};base64,{b64}"
    return _small(("uri", str(p)), build)


def _bright(rgb):
    return 0.2126 * rgb[0] + 0.7152 * rgb[1] + 0.0722 * rgb[2]


def read_background(p):
    """Nen quanh lop sac phai LIEN voi no, khong bao gio la mot mang khac tone.

    Dre lam nen bang chinh tam anh phong to + lam mo — dung cho ANH CHUP. Nhung
    bieu do/bang so/trang bao cao thi nen cua no la mot mau PHANG (thuong la
    trang): lam mo ban cover cua no ra mot mang xam-xanh lech han tone voi chinh
    tam anh sac o tren, van doc ra hai vung. Voi loai do, trai thang MAU NEN cua
    anh ra ca the la lien mach tuyet doi — cung mot mau, khong the co mep.

    -> (kieu, mau nen, nen co sang khong)
    """
    return _small(("nen", str(p)), lambda: _read_background_real(p))


THRESHOLD_OFFSET_BORDER = 20        # +-do lech mau (tung kenh) con tinh la "gan mau nen"
RATIO_FLAT_MIN = 0.85  # ti le pixel vien phai gan mau nen moi goi la phang


def _read_background_real(p):
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
                lo, hi = max(0, med[k] - THRESHOLD_OFFSET_BORDER), min(255, med[k] + THRESHOLD_OFFSET_BORDER)
                ti_le.append(sum(st.h[k * 256:k * 256 + 256][lo:hi + 1]) / st.count[k])
        toan = ImageStat.Stat(im).mean[:3]
    khac = max(abs(a[k] - b[k]) for a in tb for b in tb for k in range(3))
    phang = min(ti_le) >= RATIO_FLAT_MIN and khac < 16
    mau = tuple(int(sum(t[k] for t in tb) / 4) for k in range(3))
    # Dinh the luon la NEN (anh khong tran len FIG_DINH), nen do sang o dinh la
    # do sang cua nen: mau phang, hoac mau trung binh cua ban lam mo.
    return ("phang" if phang else "mo",
            "#%02X%02X%02X" % mau,
            _bright(mau if phang else toan) > THRESHOLD_BRIGHT_TEXT_DARK)


def set_image(rong, cao, phang):
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
    day = int(H * FIG_BOTTOM_FLAT) if phang else H
    tran = day - FIG_FIXED
    cao_hien = min(cao_that, tran)
    return cao_hien, FIG_FIXED, cao_that


# ---- helpers --------------------------------------------------------------
def esc(s):
    return html.escape(str(s), quote=True)


def _hex(rgb) -> str:
    return "#%02X%02X%02X" % tuple(rgb[:3])


def _brand_title_html(title, th):
    """HTML tieu de voi ten hang/ten model to theo palette hang (LOW-344), hoac
    None neu tieu de khong nhac hang nao.

    Moi khuc ten hang la `<span class="brand">` mang hai bien CSS: `--bc` (nen
    toi, keo sang cho doc duoc) va `--bcd` (vung chu tren nen SANG, ep toi 42%
    nhu `_color_dark`). Hang den trang lay mau nhan `a` cua theme dang dung."""
    import card
    words = brand_names.line_segments(title or "")
    if not any(role for w in words for _t, role, _k in w):
        return None
    fallback = brand_names.hex_rgb(th["a"]) if th else card.BRAND_NAME_FALLBACK
    out = []
    for w in words:
        parts = []
        for text, role, key in w:
            if not role:
                parts.append(esc(text))
                continue
            ten, org = brand_names.colors_for(key, fallback)
            mau = card._enough_bright(org if role == "org" else ten)
            toi = tuple(int(c * 0.42) for c in mau)
            parts.append(f'<span class="brand" style="--bc:{_hex(mau)};--bcd:{_hex(toi)}">'
                         f'{esc(text)}</span>')
        out.append("".join(parts))
    return " ".join(out)


def accent_html(title, accent, th=None):
    """Bọc cụm nhấn trong title thành span cyan (giữ escape).

    LOW-344 (Ông Chủ 21/09/2026, "theo tiêu chuẩn mới, bỏ qua tiêu chuẩn cũ"):
    tiêu đề có TÊN HÃNG thì tô tên hãng theo palette hãng và BỎ `accent` Kite
    tự chọn; không nhắc hãng nào thì `accent` chạy như cũ."""
    brand = _brand_title_html(title, th)
    if brand is not None:
        return brand
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
    """DA BO khoi slide (LOW-366, Ong Chu 23/09/2026: *"'@dcgr.tech … 5 phút đọc' là thông tin
    ko bắt buộc phải có trong nội dung ig, có thể lược phần đó mà ko cần phải lo gì cả"*).

    O vuong Instagram cat 4:5 nen dai duoi khung bi cat; dong folio nam dung do, va giu no thi
    cot chu phai thu lai cho vua vung an toan. Bo han: khung rong ra ~90px, chu giu nguyen co.
    Ham giu lai (tra ve chuoi rong) de mot cho quyet dinh, khong rai `if` o cac cho goi."""
    return ""


# ---- slide builders (mỗi cái trả về body HTML giữa .mast và .folio) -------
def s_cover(sl, th):
    """Bia. Mac dinh la hero art vector; nhung neu tin CO SAN mot tam hinh dang
    dua len thi ghi "image" — luc do bia dung chinh tam hinh do lam hero, chu
    chim vao no, thay vi mot so do tu ve. Hinh that bao gio cung noi duoc nhieu
    hon mot so do trang tri."""
    if sl.get("image"):
        return _cover_image(sl, th)
    byline = byline_html(sl)
    g = (glow(f"top:40px;left:50%;transform:translateX(-50%);width:900px;height:640px;"
              f"background:radial-gradient(ellipse at center,{rgba(th['a'],0.20)} 0%,{rgba(th['a'],0)} 60%);")
         + glow(f"top:120px;right:-80px;width:520px;height:520px;"
                f"background:radial-gradient(circle at center,{rgba(th['b'],0.16)} 0%,{rgba(th['b'],0)} 62%);"))
    head = (
        f'<div class="mid" style="position:relative;">'
        f'{eyebrow(sl["eyebrow"])}'
        f'<h1 class="title" style="font-size:88px;margin:24px 0 26px;">{accent_html(sl["title"], sl.get("accent"), th)}</h1>'
        f'<p class="standfirst" style="font-size:38px;margin-bottom:30px;max-width:860px;">{esc(sl["standfirst"])}</p>'
        f'{byline}</div>'
    )
    hero = f'<div style="margin:8px 0;">{hero_svg(th["hero"], th)}</div>'
    return g + hero + head


def byline_html(sl):
    """DA BO khoi bia (LOW-366, Ong Chu 23/09/2026): *"'@dcgr.tech … 5 phút đọc' là thông tin ko
    bắt buộc phải có trong nội dung ig, có thể lược phần đó mà ko cần phải lo gì cả"*. Ten kenh
    da hien ngay tren bai Instagram, con dong folio thi bo cung dot nay (xem `folio`).

    `sl["byline"]` van la truong hop le cua spec (vai cu viet), chi khong ve ra nua."""
    return ""


def _cover_image(sl, th):
    """Bia lay anh that lam hero — anh vao dong, khoi chu nam duoi mep anh."""
    nen, anh = image_make_background(sl, th, "bia")
    chu = (f'{eyebrow(sl["eyebrow"])}'
           # 74px chu khong phai 88px nhu bia art: bia co anh chi cho tieu de 2
           # dong, co chu nho hon mot bac thi 2 dong do chua duoc du y.
           f'<h1 class="title" style="font-size:74px;margin:22px 0 26px;">'
           f'{accent_html(sl["title"], sl.get("accent"), th)}</h1>'
           f'<p class="standfirst" style="font-size:36px;max-width:880px;'
           f'margin-bottom:28px;">{esc(sl["standfirst"])}</p>')
    chu += byline_html(sl)
    # KHONG ve dong nguon anh (LOW-292, 20/09/2026): xem ghi chu o `s_figure`.
    return (nen + anh
            + '<div style="flex-grow:1;min-height:0;"></div>'
            + f'<div class="mid" id="figtxt">{chu}</div>')


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
        f'<h1 class="title" style="font-size:78px;margin:36px 0 40px;">{accent_html(sl["title"], sl.get("accent"), th)}</h1>'
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
        f'<h1 class="title" style="font-size:80px;margin:24px 0 8px;">{accent_html(sl["title"], sl.get("accent"), th)}</h1>'
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
        f'<h1 class="title" style="font-size:80px;margin:32px 0 44px;">{accent_html(sl["title"], sl.get("accent"), th)}</h1>'
        f'<div class="chips" style="margin-bottom:44px;">{chips}</div>'
        f'<p class="standfirst" style="font-size:40px;max-width:900px;">{esc(sl["standfirst"])}</p>'
        f'</div>'
        f'<div class="mid" style="margin-top:44px;">{callout}</div>'
    )
    return g + body


def _color_dark(th):
    """Ma hex CYAN nhan dien cua theme, ep toi 42% — van ra dung mau nhung doc
    duoc tren nen sang. Dung cho eyebrow/accent khi chu phai doi sang TOI."""
    a = [int(th["a"].lstrip("#")[k:k + 2], 16) for k in (0, 2, 4)]
    return "#%02X%02X%02X" % tuple(int(c * 0.42) for c in a)


def _css_mast_dark():
    """Masthead (ten kenh trai, section phai, gach ngang) doi sang TOI — dung
    khi DINH the (o tren, sau masthead) la nen sang: mot man toi rieng dat len
    tren se ve ra mot dai band vat ngang, dung cai dang tranh."""
    return ('<style>.mast-name,.mast-sec{color:rgba(0,0,0,0.62);}'
            '.rule{background:rgba(0,0,0,0.16);}</style>')


def _css_text_dark_region(scope, th):
    """<style> lat toan bo mau chu trong `scope` (vd '#figtxt') sang TOI — dung
    khi vung ngay duoi khoi chu do la SANG. Ap dung het: eyebrow, tieu de,
    accent, standfirst, caption, card, byline — khong chi rieng eyebrow nhu
    truoc (Ong Chu chot 08/09/2026: doi mau chu la cach chinh, khong phai
    phu them nen)."""
    a_toi = _color_dark(th)
    return (f'<style>{scope} .eyebrow-txt{{color:{a_toi};}}'
            f'{scope} .eyebrow-bar{{background:{a_toi};}}'
            f'{scope} .fig-bar{{background:{a_toi};}}'
            f'{scope} .title{{color:rgba(0,0,0,0.85);}}'
            f'{scope} .accent{{color:{a_toi};}}'
            f'{scope} .brand{{color:var(--bcd);}}'
            f'{scope} .standfirst{{color:rgba(0,0,0,0.68);}}'
            f'{scope} .fig-cap{{color:rgba(0,0,0,0.55);}}'
            f'{scope} .card-txt{{color:rgba(0,0,0,0.78);}}'
            f'{scope} .card-num{{color:{a_toi};}}'
            f'{scope} .byline{{color:rgba(0,0,0,0.55);}}'
            f'{scope} .byline .b0{{color:rgba(0,0,0,0.85);}}'
            f'{scope} .dot{{background:rgba(0,0,0,0.4);}}</style>')


CONTAIN_GROUND_MIN = 0.80   # moi mep anh phai >= ti le nay gan mau nen thi hop anh moi "tan" vao khung


def edge_ground_share(p):
    """-> (ti le mep KEM DEU nhat gan mau nen, mau nen RGB). Mau nen = trung vi 4 mep.

    Thap hon `RATIO_FLAT_MIN` cua `read_background` vi logo net den cham mep lam mep do
    mat vai phan tram (A77: mep tren 83%, ba mep con lai 91-97%), nhung van du de hop anh
    hoa vao nen. Anh chup that (toa nha, man hinh, logo tren mat bang) co mep lon xon nen
    khong dat, va se di duong cu."""
    from PIL import Image
    with Image.open(p) as im:
        return _edge_share(im.convert("RGB"))


def _edge_share(im):
    """`edge_ground_share` tren doi tuong PIL RGB (dung cho ca anh da cat)."""
    from PIL import ImageStat
    w, h = im.size
    d = max(2, min(w, h) // 50)
    strips = [im.crop((0, 0, w, d)), im.crop((0, h - d, w, h)),
              im.crop((0, 0, d, h)), im.crop((w - d, 0, w, h))]
    meds = [[int(round(x)) for x in ImageStat.Stat(v).median] for v in strips]
    ground = tuple(int(sum(m[k] for m in meds) / 4) for k in range(3))
    worst = 1.0
    for v in strips:
        st = ImageStat.Stat(v)
        for k in range(3):
            lo = max(0, ground[k] - THRESHOLD_OFFSET_BORDER)
            hi = min(255, ground[k] + THRESHOLD_OFFSET_BORDER)
            worst = min(worst, sum(st.h[k * 256:k * 256 + 256][lo:hi + 1]) / st.count[k])
    return worst, ground


def subject_below_text_zone(a):
    """LOW-339: manifest image `a` la logo/hinh ve (vision `subject_kind`) ma day chu the
    (`subject_box[3]`) roi xuong duoi vung tren khung chu `FIG_BOTTOM_FLAT`, nghia la
    nua duoi hinh se nam sau chu. The logo 4:5 co logo tren cao thi khong."""
    import logo_card
    if not logo_card.is_logo_image(a) or not a.get("w") or not a.get("h"):
        return False
    return a["subject_box"][3] * round(W * a["h"] / a["w"]) > CONTAIN_BOTTOM - FIG_FIXED


CONTAIN_CONTENT_TOL = 24                    # lech mau (0..255) tro len la "noi dung", duoi do la nen
CONTAIN_BOTTOM = int(H * FIG_BOTTOM_FLAT)   # y (px) cua mep duoi anh khi co: ke tu dinh khung


def contain_ground(p, iw, ih):
    """Mau nen RGB neu che do co anh AP DUNG cho anh nay (cao hon vung tren chu VA mep
    dong mau), nguoc lai None. Dung chung cho renderer va cong chan o kite_submit, de hai
    ben khong lech nhau ve viec anh nao duoc co."""
    if max(1, round(W * ih / iw)) <= CONTAIN_BOTTOM - FIG_FIXED:
        return None
    share, ground = edge_ground_share(p)
    return ground if share >= CONTAIN_GROUND_MIN else None


def _image_crop_uri(p, box):
    """Data URI cua anh da cat theo `box` (None = nguyen anh)."""
    if not box:
        return _image_data_uri(p)

    def build():
        import io
        from PIL import Image
        with Image.open(p) as im:
            buf = io.BytesIO()
            im.convert("RGB").crop(box).save(buf, "PNG")
        return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")
    return _small(("uri_crop", str(p), box), build)


CONTAIN_ARTIFACT_MAX = 0.06     # dai vien thua day toi da (ti le canh) — day hon la noi dung that
CONTAIN_ARTIFACT_CONTRAST = 90  # do lech do sang (0..255) so voi long anh de tinh la "thua"
CONTAIN_ARTIFACT_GROUND_GAP = 40  # ... va phai khac mau nen it nhat chung nay (khong thi la le nen)


def _artifact_depth(g, side, ground_luma):
    """So dong/cot sat mep `side` ('top','bottom','left','right') cua anh xam `g` la dai vien
    THUA (thanh trang, vach mong o mep). Dai chi tinh khi no MONG (<= CONTAIN_ARTIFACT_MAX) va
    long anh ngay sau do tro ve binh thuong; troi dai het muc do (bau troi sang, nen trang
    that) thi la noi dung, khong cat. Dong/cot gan mau NEN (`ground_luma`) khong tinh: do la le
    nen con sot hoac dau net ve chom mep (chop rau cua logo cuop bien), khong phai vach thua."""
    from PIL import ImageStat
    w, h = g.size
    vertical = side in ("top", "bottom")
    span = h if vertical else w
    max_d = max(1, int(span * CONTAIN_ARTIFACT_MAX))

    def strip(i0, i1):
        if side == "top":
            box = (0, i0, w, i1)
        elif side == "bottom":
            box = (0, h - i1, w, h - i0)
        elif side == "left":
            box = (i0, 0, i1, h)
        else:
            box = (w - i1, 0, w - i0, h)
        return ImageStat.Stat(g.crop(box)).mean[0]

    ref = strip(int(span * 0.08), max(int(span * 0.08) + 1, int(span * 0.14)))
    depth = 0
    for i in range(max_d):
        mean = strip(i, i + 1)
        if abs(mean - ref) > CONTAIN_ARTIFACT_CONTRAST and abs(mean - ground_luma) > CONTAIN_ARTIFACT_GROUND_GAP:
            depth = i + 1
    if depth >= max_d:          # van con "thua" o do sau toi da: la noi dung that
        return 0
    return depth


HAIRLINE_MAX = 0.006        # vien hairline: day toi da 0,6% canh (>= 2px)
HAIRLINE_STD_MAX = 12       # dong ngoai cung phai gan nhu MOT MAU (vach ke, khong phai nen anh)


def hairline_box(p):
    """(x0, y0, x1, y1) sau khi bo VIEN HAIRLINE o mep, hoac None neu khong co (LOW-347).

    Ap cho MOI anh Kite (khong chi anh trong che do co). Do tren 133 anh Kite that (21/09/2026):
    bo dai mep tong quat (`_artifact_depth` toi 6% canh) danh dau 23 anh, phan lon la NOI DUNG
    that (le dem 4:5, chu thich duoi bieu do, nhan truc, vien giao dien, mep anh chup nguoi) nen
    khong ap dai tra. Chi nhom hairline (<= 0,6% canh, dong ngoai cung mot mau, lech manh so
    voi long anh) moi an toan: 3/5 anh trong nhom la vach thua that (vien hong 2px bang
    ukisai, vach do 13px bang paper bellman, vach do 1px anh chup Gemini); thanh nhan cam 7px
    cua anh Elon (1,1% canh) va vet toi 25px anh Infineon (khong deu mau) thi GIU."""
    from PIL import Image, ImageStat
    try:
        with Image.open(p) as im:
            g = im.convert("L")
    except OSError:                      # tep cut cut/hong: de duong cu tu xu ly, khong lam sap render
        return None
    w, h = g.size
    sides = {}
    for side in ("top", "bottom", "left", "right"):
        span = h if side in ("top", "bottom") else w
        depth = _artifact_depth(g, side, -1000)
        if not depth or depth > max(2, int(span * HAIRLINE_MAX)):
            continue
        outer = {"top": (0, 0, w, 1), "bottom": (0, h - 1, w, h),
                 "left": (0, 0, 1, h), "right": (w - 1, 0, w, h)}[side]
        if ImageStat.Stat(g.crop(outer)).stddev[0] <= HAIRLINE_STD_MAX:
            sides[side] = depth
    if not sides:
        return None
    return (sides.get("left", 0), sides.get("top", 0), w - sides.get("right", 0), h - sides.get("bottom", 0))


def content_box(p, ground):
    """Hop noi dung (x0, y0, x1, y1, toa do pixel anh goc) sau khi bo (1) vien PHANG cung mau
    `ground` va (2) dai vien THUA (thanh trang, vach mong o mep — Ong Chu 21/09/2026: "nhung
    doan chi tiet thua vo duyen ... phai loai bo triet de"), hoac None neu khong co gi de bo.

    Nhieu logo/anh da duoc dem nen san thanh khung 4:5 (1080x1350 nen den quanh mot tam
    that): co ca khung thi tam that chi con ~50% be ngang, chu trong infographic khong
    doc duoc (dung thu 21/09/2026 tren 6 anh that). Bo vien nen roi moi co. Buoc (1) do tren
    ban thu nho, buoc (2) do tren anh goc."""
    from PIL import Image, ImageChops
    with Image.open(p) as im:
        im = im.convert("RGB")
        w, h = im.size
        k = min(1.0, 400 / max(w, h))
        small = im.resize((max(1, round(w * k)), max(1, round(h * k))), Image.LANCZOS) if k < 1 else im
        diff = ImageChops.difference(small, Image.new("RGB", small.size, ground)).convert("L")
        box = diff.point(lambda v: 255 if v > CONTAIN_CONTENT_TOL else 0).getbbox()
        if not box:
            return None
        x0, y0, x1, y1 = (round(box[0] / k), round(box[1] / k),
                          min(w, round(box[2] / k)), min(h, round(box[3] / k)))
        g = im.crop((x0, y0, x1, y1)).convert("L")
        gl = _bright(ground)
        top, bottom = _artifact_depth(g, "top", gl), _artifact_depth(g, "bottom", gl)
        left, right = _artifact_depth(g, "left", gl), _artifact_depth(g, "right", gl)
    x0, y0, x1, y1 = x0 + left, y0 + top, x1 - right, y1 - bottom
    if x0 <= 0 and y0 <= 0 and x1 >= w and y1 >= h:
        return None
    return (x0, y0, x1, y1)


CONTAIN_FULL_WIDTH_MIN = 0.90   # hinh co co khung rieng ma hep hon ti le nay (theo be ngang khung) thi khong dung


def contain_fit(p, iw, ih):
    """Hinh hoc co anh, hoac None neu che do co khong ap dung.

    -> {"ground", "box", "width", "height", "width_share", "blends"}. `blends`: vien cua
    phan NOI DUNG (sau khi bo nen thua) van dong mau nen, tuc hinh la net ve/logo hoa vao
    nen (mat cuop bien, GA Today). Nguoc lai la mot TAM ANH co khung rieng (toa nha, banner
    cookie): hep hon khung thi lo thanh cai hop tren nen den — Ong Chu 21/09/2026: "ko hien
    thi duoc full width thi ko su dung nhung hinh nhu vay"."""
    ground = contain_ground(p, iw, ih)
    if ground is None:
        return None
    from PIL import Image
    box = content_box(p, ground)
    cw, ch = (box[2] - box[0], box[3] - box[1]) if box else (iw, ih)
    scale = min(W / cw, (CONTAIN_BOTTOM - FIG_FIXED) / ch)
    width, height = max(1, round(cw * scale)), max(1, round(ch * scale))
    with Image.open(p) as im:
        content = im.convert("RGB")
        if box:
            content = content.crop(box)
        blends = _edge_share(content)[0] >= CONTAIN_GROUND_MIN
    return {"ground": ground, "box": box, "width": width, "height": height,
            "width_share": width / W, "blends": blends}


def _boxed_picture(fit):
    """Tam anh co khung rieng ma co xong van hep hon khung: lo thanh cai hop tren nen."""
    return fit["width_share"] < CONTAIN_FULL_WIDTH_MIN and not fit["blends"]


def _image_contain_background(p, iw, ih, th):
    """LOW-339: logo / hinh ve tren nen tron ma day chu the roi xuong duoi vung tren khung
    chu (`subject_below_text_zone`) -> CO CA TAM ANH cho vua vung tren chu, khong cat mep
    duoi hay de xuong sau khung chu (slide 04/06 "Pirate Face": ~40% anh nam sau chu).
    Tra None khi anh da vua san hoac mep anh khong dong mau (anh chup that di duong cu).

    Co CA TAM, khong co theo `subject_box`: hop do vision uoc luong khong phu het hinh
    (do thu tren the Gemini va logo GA Today: phan cuoi hinh van tran xuong de len chu).
    Vien nen phang thua duoc bo truoc (`content_box`). Khung = mau nen CHINH anh
    (`edge_ground_share`), anh dat canh tren duoi masthead va canh giua ngang, hai ben la
    cung mot mau nen nen khong lo hop; chu doi mau tuong phan (`_css_text_dark_region`),
    khong overlay, khong blur (Ong Chu 21/09/2026, LOW-341 + huong (a) cua LOW-339).
    """
    fit = contain_fit(p, iw, ih)
    if fit is None or _boxed_picture(fit):
        return None
    ground, box, width, height = fit["ground"], fit["box"], fit["width"], fit["height"]
    ground_hex = "#%02X%02X%02X" % ground
    html_bg = (f'<div class="figwrap" style="background:{ground_hex};">'
               f'<img class="fig-sac" src="{_image_crop_uri(p, box)}" alt="" '
               f'style="top:{FIG_FIXED}px;left:{(W - width) // 2}px;width:{width}px;'
               f'height:{height}px;object-fit:contain;"></div>')
    if _bright(ground) > THRESHOLD_BRIGHT_TEXT_DARK:
        html_bg += _css_mast_dark() + _css_text_dark_region("#figtxt", th)
    return html_bg


def image_make_background(sl, th, ten):
    """Dung ANH THAT thanh nen ca the. Dung chung cho slide `figure` va cho
    bia khi bia co anh. -> (html nen, html anh trong dong). Khoi chu goi
    rieng, id="figtxt".

    Nguyen tac (Ong Chu chot 08/09/2026, `e883880`, CUNG luc voi Dre/carousel.py
    — xem IMAGE_RULES_KITE.md muc 7 — nhac lai nhieu lan; day la nguyen tac SAU hon ban
    cu "man toi lien mach"). Kite doi mau theo TUNG DAI DONG (_css_chu_toi_vung,
    ham tren) thay vi mot FG co dinh ca bo nhu carousel.py, vi chu Kite nhieu va
    da dang hon han — hai co che khac nhau cho cung mot ket luan, dung suy
    ngang tu ben kia:

      MAC DINH KHONG PHU LOP NAO len anh. Doi MAU CHU (sang hoac toi) cho
      tuong phan voi dung vung anh nam duoi no la du — do thang do sang tren
      pixel that cua ban mo lam nen (xem _vung_duoi_chu), khong doan.
      Tu 10/09/2026 (aac796a) khong con lop mo nao het, ke ca khi vung duoi
      chu roi: anh di vao DONG nen khoi chu khong the de len anh — khong con
      gi de che.

      NEN bao gio cung la anh (hoac dung mau nen phang cua no), khong bao gio
      la mot hop den dat canh anh. LOP SAC trai full be ngang, KHONG cat hai
      canh.
    """
    p, iw, ih = _measure_image(sl["image"])
    crop_box = None
    force_photo = False
    if sl.get("image_fit") == "contain":
        contained = _image_contain_background(p, iw, ih, th)
        if contained is not None:
            return contained, ""
        fit = contain_fit(p, iw, ih)
        if fit is not None:
            # Hinh co khung rieng khong hien thi duoc full be ngang (cong nop chan, tru khi
            # slide ghi image_force). Buoc phai dung thi PHONG full be ngang, bo vien nen dem thua,
            # phan thua cham chu thi lop chu phu len (duong anh chup co san). Ong Chu 21/09/2026.
            force_photo, crop_box = True, fit["box"]
            if crop_box:
                iw, ih = crop_box[2] - crop_box[0], crop_box[3] - crop_box[1]
    if crop_box is None:
        # LOW-347: vien hairline (vach 1-13px o mep) bo cho MOI anh, khong chi anh trong che do co.
        crop_box = _small(("hairline", str(p)), lambda: hairline_box(p))
        if crop_box:
            iw, ih = crop_box[2] - crop_box[0], crop_box[3] - crop_box[1]
    kieu, mau_nen, nen_sang = read_background(p)
    if force_photo:
        kieu = "mo"
    cao, y0, cao_that = set_image(iw, ih, kieu == "phang")
    if cao_that > cao and ("bao", str(p), cao) not in _NHO_ANH:
        # Bao ra de Kite biet mat bao nhieu: neu phan mat la phan dang noi toi
        # thi phai tu cat lai cho dung truoc khi dua vao day. Chi bao MOT lan:
        # slide duoc dung hai luot (cong chan 2 dong, roi vong chup), bao ca hai
        # luot thi Kite tuong co hai anh bi cat.
        _NHO_ANH[("bao", str(p), cao)] = True
        print(f"{ten} {p.name}: {iw}x{ih}, cao {cao_that}px -> con {cao}px "
              f"(giu mep tren, mat {cao_that - cao}px duoi)", file=sys.stderr)
    uri = _image_crop_uri(p, crop_box)
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
        # LOW-345: khoi chu dai co the bat dau SOM hon FIG_BOTTOM_FLAT; anh phang chi duoc ket thuc
        # (va tan dan) TREN dong chu dau, khong thi hang cuoi cua bang lot ra sau kicker.
        nen += (f'<script>window.__datMan=function(){{'
                f'var im=document.querySelector(".figwrap .fig-doi"),t=document.getElementById("figtxt");'
                f'if(!im||!t)return;'
                f'var lim=t.getBoundingClientRect().top-{FLAT_TEXT_GAP};'
                f'if({y0}+{cao}<=lim)return;'
                f'im.style.height=Math.max(1,Math.floor(lim-{y0}))+"px";'
                f'var g="linear-gradient(to bottom,#000 calc(100% - 130px),transparent 100%)";'
                f'im.style.maskImage=g;im.style.webkitMaskImage=g;}};</script>')
        if nen_sang:
            nen += _css_mast_dark() + _css_text_dark_region("#figtxt", th)
        return nen, ""

    # kieu == "mo" — ANH CHUP. Ong Chu chot lai 12/09/2026, nguyen van ba y:
    #   (1) "dung anh hero trong main article lam thumbnail cho hero slide, vi
    #       anh do la chu nhat ngang, nen no hien thi vua van voi nua tren";
    #   (2) "blur toan bo tam anh de lam nen cho hero slide CHUA-BAO-GIO la viec
    #       duoc yeu cau voi Kite ca, chi can chon color palette tuong dong voi
    #       chu de la duoc";
    #   (3) blur CHI danh cho anh DOC keo qua xuong vung chu (bang xep hang): mo
    #       phan duoi de tit/subtitle hien len — "chu ko phai la blur toan bo
    #       anh chinh roi dat lam nen".
    # NEN = mau theme (palette da chon theo mau anh o chon_theme_tu_dong), khong
    # `.fig-nen`; ANH = `.fig-sac` full be ngang neo duoi masthead, cao tu nhien
    # (dat_anh cat khi qua H); LOP MO chi bat khi mep duoi anh chom qua dong chu
    # dau — do bang JS luc layout — va chi tu dong chu do tro xuong.
    r, g, b = (int(th["bg"].lstrip("#")[k:k + 2], 16) for k in (0, 2, 4))
    nen = (f'<div class="figwrap" style="background:{th["bg"]};">'
           f'<img class="fig-sac fig-doi" src="{uri}" alt="" '
           f'style="top:{y0}px;height:{cao}px;object-position:top;{mo_day}">'
           f'<div class="fig-molop" id="figmo" style="display:none">'
           f'<img class="fig-doi" src="{uri}" alt="" style="top:{y0}px;height:{cao}px;'
           f'object-fit:cover;object-position:top;"></div>'
           f'<div class="fig-man" id="figman" style="display:none"></div></div>'
           f'<script>window.__datMan=function(){{'
           f'var H={H},Y0={y0},CAO={cao},MAX={DARK_MAX_OPEN:.3f};'
           f'var v=document.getElementById("figman"),m=document.getElementById("figmo");'
           f'if(!v||!m)return;'
           f'var t=document.getElementById("figtxt");'
           f'var top=t?t.getBoundingClientRect().top:H*0.58;'
           f'if(Y0+CAO<=top){{v.style.display="none";m.style.display="none";return;}}'
           f'v.style.display="block";m.style.display="block";'
           f'var tren=Math.max(0,top-{VEIL_LEAD}),day=Math.min(H,top+{VEIL_SPAN}-{VEIL_LEAD});'
           f'var span=Math.max(1,H-tren);var st=[],sm=[];'
           f'for(var i=0;i<=16;i++){{'
           f'var q=i/16,ss=q*q*(3-2*q),y=tren+(day-tren)*q,'
           f'pc=((y-tren)/span*100).toFixed(2);'
           f'st.push("rgba({r},{g},{b},"+(MAX*ss).toFixed(3)+") "+pc+"%");'
           f'sm.push("rgba(0,0,0,"+(0.85*ss*ss).toFixed(3)+") "+(y/H*100).toFixed(2)+"%");}}'
           f'st.push("rgba({r},{g},{b},{DARK_MAX_OPEN:.3f}) 100%");'
           f'sm.unshift("rgba(0,0,0,0) 0%");sm.push("rgba(0,0,0,0.85) 100%");'
           f'var gr="linear-gradient(to bottom,"+sm.join(",")+")";'
           f'm.style.webkitMaskImage=gr;m.style.maskImage=gr;'
           f'v.style.top=tren+"px";'
           f'v.style.background="linear-gradient(to bottom,"+st.join(",")+")";'
           f'}};</script>')
    return nen, ""


def s_figure(sl, th):
    """Hinh that trai het be ngang, chu chim vao anh o duoi."""
    nen, anh = image_make_background(sl, th, "figure")
    chu = (f'{eyebrow(sl["eyebrow"])}'
           f'<h1 class="title" style="font-size:62px;margin:22px 0 0;">'
           f'{accent_html(sl["title"], sl.get("accent"), th)}</h1>')
    # KHONG ve dong nguon anh (LOW-292, 20/09/2026). Ong Chu khoanh do dong
    # "— <mo ta anh> · via <trang>" o ca bia lan slide than cua album Gemini
    # (task t_22d038a3): "noi dung khong duoc phep xuat hien". Nguon anh VAN
    # duoc giu o ban giao cho writer va metadata PNG (image_provenance) — chi
    # khong hien tren slide. Dong `caption` cua kind `bars` la nguon CON SO
    # trong bai, viec khac, giu nguyen.
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
            + f'<div class="mid" id="figtxt">{chu}</div>')


def _count(v):
    """2.75 -> '2,75'; 3.0 -> '3' (kieu Viet, dung khi slide khong ghi 'text')."""
    f = float(v)
    return str(int(f)) if f == int(f) else f"{f:.2f}".rstrip("0").rstrip(".").replace(".", ",")


_SO_TRONG_CHU = re.compile(r"\d[\d.,]*")
_CHAM_NGHIN = re.compile(r"^\d{1,3}(\.\d{3})+$")


def _value(v):
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
    theo cot lon nhat; cot co 'highlight': true (mac dinh cot dau) mau chinh, con
    lai mau phu. Khong co truc/luoi: 2..6 cot, doc trong 3 giay."""
    items = sl.get("bars", [])
    vals = [_value(b["value"]) for b in items]
    vmax = max(vals, default=0.0) or 1.0
    co_nhan = any(b.get("highlight") for b in items)
    rows = ""
    for i, (b, v) in enumerate(zip(items, vals)):
        pct = max(0.0, min(100.0, v / vmax * 100))
        cls = "bar-fill highlight" if (b.get("highlight") or (i == 0 and not co_nhan)) else "bar-fill"
        rows += (f'<div class="bar"><span class="bar-l">{esc(b["label"])}</span>'
                 f'<span class="bar-track"><span class="{cls}" style="width:{pct:.1f}%;"></span></span>'
                 f'<span class="bar-v">{esc(b.get("text") or _count(v))}</span></div>')
    cap = (f'<div class="fig-cap" style="margin-top:28px;"><span class="fig-bar"></span>'
           f'<span>{esc(sl["caption"])}</span></div>') if sl.get("caption") else ""
    stand = (f'<p class="standfirst" style="font-size:34px;max-width:900px;margin-top:30px;">'
             f'{esc(sl["standfirst"])}</p>') if sl.get("standfirst") else ""
    g = glow("bottom:-120px;left:-140px;width:560px;height:560px;"
             f"background:radial-gradient(circle at center,{rgba(th['a'],0.13)} 0%,{rgba(th['a'],0)} 62%);")
    body = (
        f'<div class="mid" style="margin-top:46px;">'
        f'{eyebrow(sl["eyebrow"])}'
        f'<h1 class="title" style="font-size:76px;margin:24px 0 8px;">{accent_html(sl["title"], sl.get("accent"), th)}</h1>'
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
        f'<h1 class="title" style="font-size:76px;margin:32px 0 48px;">{accent_html(sl["title"], sl.get("accent"), th)}</h1>'
        f'{checks_wrap}</div>'
        f'<div class="mid">{readmore}</div>'
    )
    return g + body


BUILDERS = {
    "cover": s_cover, "statement": s_statement, "steps": s_steps,
    "loop": s_loop, "figure": s_figure, "bars": s_bars, "cta": s_cta,
}


def slide_read(sl, idx, total, brand, section, folio_left, font_css, th):
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
    # `.folio` da bo (LOW-366) — day cot chu gio la khoi chu cuoi cung cua `body`.
    return (f'<!doctype html><html><head><meta charset="utf-8"><style>'
            f'{font_css}{base_css(th)}'
            # SVG nao KHONG dat `height` thi trinh duyet noi suy chieu cao tu
            # viewBox (hero bia 920x470, ky hieu vector) nho preserveAspectRatio
            # — nho vay hero giu dung ti le thay vi bi keo gian theo be ngang.
            f'svg{{height:auto;}}'
            f'</style></head><body>'
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
# Truoc day bang nay chi song o kite_submit.py va gate_slides khong kiem truong nao
# ca: mot spec thieu `standfirst` o slide 4 di qua cong sach se, render() mo
# Chromium, roi `s_statement` nem KeyError THO. Neu no ra o vong chup thu hai
# (:1281) thi mot phan album da nam trong drafts/ — dung cai album cut ma thiet
# ke hai vong sinh ra de tranh. Va moi duong khong di qua nop (goi thang
# render_edu, `--spec -`) thi truoc gio khong co cong nao.
#
# `fields`: truong bat buoc; `nested`: (ten danh sach, cac khoa moi phan tu phai co).
REQUIRED_KIND: dict[str, dict] = {
    "cover":     {"fields": ("eyebrow", "title", "standfirst")},
    "statement": {"fields": ("eyebrow", "title", "standfirst"),
                  "nested": ("cards", ("num", "text"))},
    "steps":     {"fields": ("eyebrow", "title", "steps"),
                  "nested": ("steps", ("title", "desc"))},
    "loop":      {"fields": ("eyebrow", "title", "standfirst", "callout", "chips")},
    # `caption` KHONG con bat buoc o figure (LOW-292): dong nguon anh khong ve nua.
    "figure":    {"fields": ("eyebrow", "title", "standfirst", "image"),
                  "nested": ("cards", ("num", "text"))},
    "bars":      {"fields": ("eyebrow", "title", "standfirst", "caption", "bars"),
                  "nested": ("bars", ("label", "value"))},
    "cta":       {"fields": ("eyebrow", "title", "checks")},
}


def check_field(slides) -> list:
    """Thieu truong bat buoc / kind la — bat o day, khong de builder nem."""
    loi = []
    for i, sl in enumerate(slides, 1):
        kind = sl.get("kind")
        if kind not in BUILDERS:
            loi.append(f"slide {i}: kind {kind!r} khong co — chon mot trong "
                       + ", ".join(sorted(BUILDERS)))
            continue
        q = REQUIRED_KIND.get(kind, {})
        for k in q.get("fields", ()):
            if not sl.get(k):
                loi.append(f"slide {i} [{kind}]: thieu '{k}'")
        ten_ds, khoa = q.get("nested", (None, ()))
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
    loi = check_field(slides)
    if any("kind" in d and "khong co" in d for d in loi):
        return loi
    try:
        loi += _gate_content(slides, bo_qua_dau)
    except Exception as e:                                   # noqa: BLE001
        loi.append(f"[cong noi dung dung giua chung: {type(e).__name__}: {e} — "
                   "sua cac loi tren truoc roi chay lai]")
    return loi


def _gate_content(slides, bo_qua_dau):
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
                mat = vietnamese.find_face_mark(t)
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
            _, rong, cao = _measure_image(sl["image"])
        except (FileNotFoundError, ValueError) as e:
            loi.append(f"slide {i}: {e}")
            continue
        if rong < FIG_EMPTY_MIN:
            loi.append(f"slide {i}: anh rong {rong}px, keo len {W}px la be nat. "
                       f"Chup lai bang capture_chart.py (DPR 2) hoac xin ban goc.")
        # Truoc LOW-292 o day con cong "slide co anh phai co caption": dong
        # nguon anh khong len slide nua nen cong do khong con nghia.

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
                gt = _value(b.get("value"))
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
                    gt_text = _value(so_text.group(0))
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
def _journal_theme() -> Path:
    """state/<brand>/used_edu_themes.jsonl — so theme/hero da dung gan day.

    Truoc 06/09/2026 tep nay nam o `state/` GOC, tuc dung chung cho ca hai
    brand. Kite gio chay cho ca hai, nen bo "4 bo gan nhat" tron lan: mot bo
    dcgr vua dung theme X la bo blog ke tiep bi day sang theme khac ma khong
    co ly do nao — hai kenh khac nhau, nguoi doc khac nhau.

    Goi ham chu khong phai hang o cap module: `env_load.state_dir()` doc
    CT_BRAND luc CHAY, con hang thi chot luc import.
    """
    import env_load
    import state_paths
    return env_load.state_dir() / state_paths.USED_EDU_THEMES_FILE


def _theme_near_bottom(n=4):
    """[(theme, hero)] cua n bo gan nhat, moi nhat truoc."""
    if not _journal_theme().exists():
        return []
    rows = []
    for line in _journal_theme().read_text("utf-8").splitlines():
        try:
            d = json.loads(line)
            rows.append((d.get("theme"), d.get("hero")))
        except Exception:
            continue
    return rows[::-1][:n]


def _write_theme(out, theme, hero):
    try:
        _journal_theme().parent.mkdir(parents=True, exist_ok=True)
        with open(_journal_theme(), "a", encoding="utf-8") as f:
            f.write(json.dumps({"out": str(out), "theme": theme, "hero": hero},
                               ensure_ascii=False) + "\n")
    except OSError:
        pass


# >nguong nay (vong tron hue, 0..0.5) la LECH TONG. Tung la 0.28 (~100 do):
# moss xanh la lech xanh DeepSeek 0.262 van coi la "cung tong", khong mot dong
# canh bao (LOW-340). 0.15 ~ 54 do: cyan-xanh duong con cung tong, xanh la thi khong.
THRESHOLD_HUE_OFFSET_COLOR = 0.15
RATIO_IMAGE_HAS_COLOR = 0.01       # duoi muc nay pixel co mau tren CA TAM -> anh coi nhu khong mau
RATIO_COLOR_APPLY_INVERT = 0.05       # mau noi bat phai chiem tung nay so pixel DA LOC


def color_say_catch(path) -> tuple | None:
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
            for r, g, b in list(im.getdata()):   # list(): getdata() tra ImagingCore, stub khong coi la iterable
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
    if tong_loc / n < RATIO_IMAGE_HAS_COLOR or dinh / tong_loc < RATIO_COLOR_APPLY_INVERT:
        return None
    r, g, b = colorsys.hsv_to_rgb(bucket / 24, 0.65, 0.85)
    return (round(r * 255), round(g * 255), round(b * 255))


def offset_hue(rgb, ten: str) -> float:
    """Khoang cach hue (vong tron, 0..0.5) giua `rgb` va accent chinh cua theme."""
    import colorsys
    h0, _, _ = colorsys.rgb_to_hsv(*(c / 255 for c in rgb))
    a = THEMES[ten]["a"].lstrip("#")
    r, g, b = (int(a[i:i + 2], 16) for i in (0, 2, 4))
    h1, _, _ = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
    d = abs(h0 - h1)
    return min(d, 1 - d)


def theme_near_color(rgb) -> str | None:
    """Ten THEME TAM TRANG co mau `a` (accent chinh) GAN NHAT voi `rgb` theo
    khoang cach hue tren vong tron mau. None neu rgb la None (anh khong co mau
    ro ret). Palette hang khong du so hue — xem MOOD_THEMES."""
    if rgb is None:
        return None
    return min(MOOD_THEMES, key=lambda ten: offset_hue(rgb, ten))


def subject_brand(texts) -> tuple | None:
    """Khoa hang CHU THE cua tin: hang dau tien nhac toi trong `texts` (theo
    thu tu), bo qua noi dang model (PLATFORM_BRANDS) neu con hang khac. None
    neu khong nhac hang nao.

    Nhan dien ten hang (ke ca trong ten model viet lien — "DeepSeek-V4.1-Flash",
    "deepseek-ai/...", "Swift-Qwen3.8-27b") dung CHUNG `brand_names` voi cho to
    ten hang cua ca doi (LOW-344), khong giu ban rieng."""
    found = []
    for text in texts:
        for key in brand_names.brand_keys(text or ""):
            if key not in found:
                found.append(key)
    return next((k for k in found if k not in PLATFORM_BRANDS), found[0] if found else None)


def is_mono_brand(key) -> bool:
    """Hang tong den trang (MONO_BRANDS, hoac mau trong COLOR_RANK gan nhu xam):
    khong co mau de bam — hue cua mau xam la ngau nhien (xAI (225,225,225) tung
    ra theme hong 'rose')."""
    import card
    import colorsys
    if key in MONO_BRANDS:
        return True
    mau = card._color_of_rank(key)
    return bool(mau) and colorsys.rgb_to_hsv(*(c / 255 for c in mau))[1] < 0.2


def _brand_texts(spec) -> tuple:
    """Cho do hang chu the, theo thu tu tin cay: `subject` (tieu de tin goc,
    kite_submit ghi vao tu manifest — chu the luon dung dau) -> folio -> eyebrow
    -> title cua bia (do vai viet, hay nhac hang khac trong cau so sanh)."""
    bia = (spec.get("slides") or [{}])[0]
    return (spec.get("subject"), spec.get("folio"), bia.get("eyebrow"), bia.get("title"))


def brand_theme_of(spec) -> tuple:
    """(palette, khoa_hang) cua hang chu the. palette None khi khong nhac hang,
    hang den trang, hoac hang chua co palette rieng."""
    key = subject_brand(_brand_texts(spec))
    return BRAND_THEME.get(key) if key else None, key


def is_brand_theme(theme) -> bool:
    return theme in THEMES and theme not in MOOD_THEMES


def color_rank_within_spec(spec) -> tuple | None:
    """Mau nhan dien cua hang CHU THE trong spec, hoac None (khong nhac hang,
    hoac hang den trang).

    Tra cuu CUNG mot bang voi cho to ten hang trong tieu de cua Ethan
    (`card.COLOR_RANK` / `COLOR_PHRASE`) — mot bang mau cho ca doi, khong dung bang
    thu hai roi de hai cho troi khoi nhau."""
    import card
    key = subject_brand(_brand_texts(spec))
    if key is None or is_mono_brand(key):
        return None
    return card._color_of_rank(key)


def pick_theme_auto(spec, bia_anh=False, anh_mau=None):
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

    THU TU chon mau cho theme (Ong Chu chot 21/09/2026, LOW-340 — thay thu tu
    10/09 cua LOW-11, khi anh bia con dung dau):
      1. PALETTE CUA HANG CHU THE (BRAND_THEME) — thang ca theme spec tu ghi:
         tin DeepSeek ma vai ghi "moss" van ra "deepseek";
      2. mau NOI BAT cua anh bia that;
      3. mau nhan dien cua hang chua co palette (`card.COLOR_RANK`) -> theme tam
         trang gan hue nhat; hang den trang thi bo qua tang nay;
      4. xoay vong 5 theme tam trang cho khoi lap bo truoc.
    Nen mot loat tin cung hang se cung tone: do la y muon, khong phai trui."""
    gan = _theme_near_bottom()
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

    locked, key = brand_theme_of(spec)
    if locked:
        # Tang 1: theme do vai tu ghi KHONG thang palette hang — canh bao stderr
        # thi LLM bo qua (bo DeepSeek 21/09 ghi "moss" ma khong ai hay).
        if theme and theme != locked:
            print(f"[theme] tin {' '.join(key)} -> {locked} (bo theme={theme} "
                  "trong spec: palette khoa theo hang chu the)", file=sys.stderr)
        theme = locked
        rgb = theme_khop_mau = None
    else:
        rgb = color_say_catch(anh_mau) if (bia_anh and anh_mau) else None
        nguon = "anh bia"
        if rgb is None:
            # Anh bia khong co mau ro ret (hoac bia ve vector): bam MAU NHAN
            # DIEN CUA HANG (chua co palette rieng) thay vi xoay vong mu mau.
            rgb = color_rank_within_spec(spec)
            nguon = "mau hang nhac trong spec"
        theme_khop_mau = theme_near_color(rgb)
    if not theme:
        theme = theme_khop_mau or it_dung_nhat(list(MOOD_THEMES), [t for t, _ in gan], seed)
    elif theme_khop_mau and theme != theme_khop_mau and offset_hue(rgb, theme) > THRESHOLD_HUE_OFFSET_COLOR:
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
    dem = {"served": 0}

    def _respond(route, request):
        ten = request.url.rsplit("/", 1)[-1]
        fp = FONTS_DIR / ten
        # Chi phuc vu tep NGAY TRONG assets/fonts, khong di theo "../".
        if fp.parent.resolve() != FONTS_DIR.resolve() or not fp.exists():
            route.abort()
            return
        dem["served"] += 1
        route.fulfill(status=200, body=fp.read_bytes(),
                      headers={"content-type": "font/ttf",
                               "cache-control": "max-age=86400"})

    page.route(FONT_URL + "*", _respond)
    return dem


def _check_title_line(page, browser, slides, dung_doc):
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
        if n > FIG_TITLE_LINE:
            loi_dong.append(
                f"slide {i}: tieu de {n} dong — slide co anh chi cho "
                f"{FIG_TITLE_LINE} dong. Anh da noi phan viec cua no roi, "
                f"tieu de dai them la giam cua nhau. Cat ngan tieu de lai.")
    if loi_dong:
        browser.close()
        print("CONG CHAN DUNG:", file=sys.stderr)
        for x in loi_dong:
            print("  - " + x, file=sys.stderr)
        raise SystemExit(1)


def _fit_safe_zone(page, i, kind, loi):
    """LOW-366: thu khoang trang cho cot chu vua VUNG AN TOAN, roi kiem lai tren hop chu THAT.
    Con tran thi ghi loi (chu qua dai — viec cua vai, khong phai cua code)."""
    page.add_script_tag(content=FIT_JS)
    bao = page.evaluate(f"() => window.__fitSafe({PAD_TOP}, {H - PAD_BOT})")
    if not bao:
        return
    if bao["over"] > 0:
        loi.append(f"slide {i} ({kind}): chu vuot vung an toan {int(bao['over'])}px "
                   f"(day khoi chu o {bao['text_bottom']}, tran duoi la {bao['bottom_limit']}) "
                   "— dang 1:1 se cat mat chu. Cat bot chu cua slide nay.")
    if bao.get("mast_top") is not None and bao["mast_top"] < bao["top_limit"]:
        loi.append(f"slide {i} ({kind}): masthead o {bao['mast_top']} cao hon tran tren "
                   f"{bao['top_limit']} — dang 1:1 se cat mat.")


def _capture_each_slide(page, slides, dung_doc, out, stem):
    """Chup tung slide ra PNG; slide 1 la `out`, con lai `<stem>_<i>.png`."""
    outs, loi = [], []
    for i, sl in enumerate(slides, start=1):
        doc = dung_doc(sl, i)
        page.set_content(doc, wait_until="load")
        page.evaluate("document.fonts.ready")
        # Lop mo phan duoi chu dat theo dong chu dau THAT — sau khi font xong.
        page.evaluate("window.__datMan && window.__datMan()")
        _fit_safe_zone(page, i, sl.get("kind"), loi)
        page.wait_for_timeout(120)
        path = out if i == 1 else Path(f"{stem}_{i}.png")
        page.screenshot(path=str(path),
                        clip={"x": 0, "y": 0, "width": W, "height": H})
        outs.append(path)
    if loi:
        print("CONG CHAN DUNG:", file=sys.stderr)
        for x in loi:
            print("  - " + x, file=sys.stderr)
        raise SystemExit(1)
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
    theme, hero = pick_theme_auto(spec, bia_anh, slides[0].get("image") if bia_anh else None)
    th = dict(THEMES[theme], hero=hero)
    print(f"theme={theme} hero=" + (hero or "- (bia dung anh that)"))

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as e:
        # `from e`: ImportError o day thuong la "thieu goi", nhung cung co the la
        # playwright da cai ma hong mot phu thuoc con — giu chuoi loi goc de con
        # doc ra la cai nao (B904).
        raise SystemExit(
            "Thieu Playwright. Tren server:\n"
            "  venv/bin/pip install playwright\n"
            "  venv/bin/playwright install chromium") from e

    out = Path(out)
    stem = out.with_suffix("")
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--force-color-profile=srgb"])
        ctx = browser.new_context(viewport={"width": W, "height": H},
                                  device_scale_factor=scale)
        page = ctx.new_page()

        dem_font = _route_font(page)

        def read_slide(sl, i):
            return slide_read(sl, i, total, brand, section, folio_left, font_css, th)

        _check_title_line(page, browser, slides, read_slide)
        outs = _capture_each_slide(page, slides, read_slide, out, stem)
        # Font phuc vu qua route thi PHAI co it nhat mot luot. Zero nghia la
        # Chromium da roi ve font he thong: album van ra anh, chi la sai chu —
        # dung loai hong ma nhin anh moi biet, nen chan o day.
        if not dem_font["served"]:
            browser.close()
            raise SystemExit(
                "KHONG font nao duoc nap qua page.route — album se sai chu.\n"
                f"Kiem assets/fonts va FONT_URL ({FONT_URL}) trong render_edu.py.")
        browser.close()
    _write_theme(out, theme, hero)   # hero=None khi bia dung anh that
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
