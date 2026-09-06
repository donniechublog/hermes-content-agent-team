#!/usr/bin/env python3
"""xep_hang.py — ẢNH CHO TIN XẾP HẠNG: chụp đúng bảng/chart xếp hạng, khoanh đúng model.

Luật Ông Chủ 06/09/2026, nguyên văn:
  * nói về ranking phải là table / chart / standing / rank...
  * nếu không có ảnh thì capture screen
  * tìm tất cả các nguồn: terminalbench, arena.ai, artificialanalysis.ai... không
    giới hạn nguồn, miễn là capture được hình tử tế về ranking
  * khi capture phải KHOANH LẠI đúng model đang được nhắc tới
  * không dùng lại ảnh đã dùng trong phiên
  * không dùng ảnh không liên quan tới nội dung
  * không capture được thì ảnh = tên model + thứ hạng + logo model + site đánh giá
  Tham chiếu: đồ hoạ của arena.ai (bảng top-N, model chủ đề khoanh vàng), thẻ
  "GPT-5 is #1 on WebDev Arena". Không ra output tương tự là FAIL.

Vì sao cần tệp riêng: ba thẻ liền nhau về xếp hạng model (04–06/09) dùng bảng tỉ
số giải golf rồi bảng câu cá trên băng — khớp chữ "leaderboard", không dính gì
tới tin. Engine có sẵn browser chụp figure/table nhưng chỉ chụp trang BÀI BÁO;
tin xếp hạng thì bảng nằm ở TRANG XẾP HẠNG, và phải khoanh đúng hàng.

Đường đi (`tim_va_chup`):
  1. Tách tên model + thứ hạng khỏi tiêu đề; xếp nguồn theo gợi ý (link/via nhắc
     arena → arena trước), rồi tới toàn bộ registry.
  2. Mỗi nguồn: mở bằng chromium, tìm HÀNG chứa tên model trong bảng lớn nhất
     (khớp bỏ dấu cách/gạch: "GPT-5.5" ≡ "GPT 5.5"), chụp cửa sổ top-N quanh
     hàng đó FULL BỀ NGANG bảng (mục 2 LUAT_ANH), khoanh vàng hàng model, đọc
     thứ hạng từ ô đầu. Bảng không có thì thử chart SVG (khoanh nhãn).
  3. Không nguồn nào ra → thẻ dự phòng: tên model + #hạng + logo (nếu chụp được
     từ hàng) + site.
  Mọi ảnh đóng dấu `nguon_dung=chup_xep_hang|the_xep_hang` + model/nguon/hang.

Dùng tay:
    venv/bin/python xep_hang.py --tieu-de "Kimi-K3 leo lên #1 Frontend Code Arena" --ra kimi.png
    venv/bin/python xep_hang.py --model "Claude Opus 4.6" --nguon arena-text --ra x.png
"""
import argparse
import json
import re
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import luat_anh                                              # noqa: E402

DPR = 2
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
VANG = (245, 197, 24)          # màu khoanh — cùng gam với đồ hoạ tham chiếu của arena.ai
TOP_MAC_DINH = 10              # ít nhất top-N khi model nằm trong top
TREN_MODEL = 2                 # model nằm sâu: giữ 2 hàng phía trên, kéo dài xuống dưới
CAO_TOI_DA_CSS = 1500          # trần chiều cao cửa sổ chụp (CSS px)
# Kéo cửa sổ xuống cho tới khi rộng/cao <= mức này: 1.6 là trần ảnh đi một mình
# vào hero (kiem_anh_thap 50% khổ 4:5). Bảng arena ~1330px ngang, hàng ~57px ->
# ~15-16 hàng, đúng cỡ đồ hoạ tham chiếu (top-20). Model chủ đề luôn ở phần TRÊN
# ảnh, vì hero đặt hook lên nửa dưới qua màn tối.
TI_LE_MUC_TIEU = 1.5

# ---- Registry nguồn xếp hạng --------------------------------------------------
# Không giới hạn: đây là danh sách BIẾT SẴN để đi trước; `goi_y_nguon` còn nhận
# mọi URL trang xếp hạng xuất hiện trong link/via/chữ bài. Thứ tự = ưu tiên khi
# không có gợi ý.
NGUON = [
    {"ma": "arena-text",     "site": "ARENA.AI",  "bang": "Text Arena",
     "url": "https://arena.ai/leaderboard/text",          "mien": r"arena\.ai|lmarena"},
    {"ma": "arena-code",     "site": "ARENA.AI",  "bang": "WebDev / Code Arena",
     "url": "https://arena.ai/leaderboard/code",          "mien": r"arena\.ai|lmarena"},
    {"ma": "arena-vision",   "site": "ARENA.AI",  "bang": "Vision Arena",
     "url": "https://arena.ai/leaderboard/vision",        "mien": r"arena\.ai|lmarena"},
    {"ma": "arena-t2i",      "site": "ARENA.AI",  "bang": "Text-to-Image Arena",
     "url": "https://arena.ai/leaderboard/text-to-image", "mien": r"arena\.ai|lmarena"},
    {"ma": "arena-t2v",      "site": "ARENA.AI",  "bang": "Text-to-Video Arena",
     "url": "https://arena.ai/leaderboard/text-to-video", "mien": r"arena\.ai|lmarena"},
    {"ma": "arena-search",   "site": "ARENA.AI",  "bang": "Search Arena",
     "url": "https://arena.ai/leaderboard/search",        "mien": r"arena\.ai|lmarena"},
    {"ma": "aa-models",      "site": "ARTIFICIALANALYSIS.AI", "bang": "Intelligence Index",
     "url": "https://artificialanalysis.ai/leaderboards/models", "mien": r"artificialanalysis"},
    {"ma": "tbench",         "site": "TBENCH.AI", "bang": "Terminal-Bench",
     "url": "https://www.tbench.ai/leaderboard",          "mien": r"tbench|terminal[-_ ]?bench"},
    {"ma": "swebench",       "site": "SWEBENCH.COM", "bang": "SWE-bench",
     "url": "https://www.swebench.com/",                  "mien": r"swebench|swe[-_ ]?bench"},
    {"ma": "livebench",      "site": "LIVEBENCH.AI", "bang": "LiveBench",
     "url": "https://livebench.ai/",                      "mien": r"livebench"},
    {"ma": "aider",          "site": "AIDER.CHAT", "bang": "Aider Polyglot",
     "url": "https://aider.chat/docs/leaderboards/",      "mien": r"aider"},
]

# Từ khoá chọn bảng con của một site theo chủ đề tin (video → arena-t2v trước...)
CHU_DE = [
    (r"\bvideo\b|text-to-video|tạo video", ["arena-t2v"]),
    (r"\bimage\b|text-to-image|tạo ảnh|hình ảnh", ["arena-t2i"]),
    (r"\bvision\b|thị giác|multimodal|đa phương thức", ["arena-vision"]),
    (r"webdev|frontend|front-end|\bcode\b|coding|lập trình|swe[-_ ]?bench", ["arena-code", "swebench", "aider"]),
    (r"terminal|agentic|\bagent\b", ["tbench"]),
    (r"\bsearch\b|tìm kiếm", ["arena-search"]),
    (r"intelligence|trí tuệ|artificial ?analysis", ["aa-models"]),
]

# ---- Nhận diện tin xếp hạng + tách model/hạng ---------------------------------
_XEP_HANG = re.compile(
    r"(xếp hạng|thứ hạng|bảng xếp hạng|leaderboard|ranking|ranked|\brank\b|standing|"
    r"đứng đầu|dẫn đầu|đứng thứ|hạng \d|#\s?\d|top\s?\d|top-\d|leo \d|leo lên|vượt|áp sát|"
    r"soán ngôi|chen chân|lọt top|elo|arena|intelligence index|trí tuệ .{0,20}(artificial|analysis)|"
    r"benchmark.{0,25}(#\d|top|đầu|nhất)|số 1|number one|no\.\s?1|\bfirst place\b)", re.I)

# Họ model + đuôi phiên bản. Bắt cả "GPT-6 Astra (max)", "Claude Fable 5.1", "Kimi-K3",
# "Grok Imagine Video 1.5 Agent", "Qwen3.8-27B", "GLM-5.2 (Max)", "Muse Spark 1.2".
_HO = (r"GPT|Claude|Gemini|Gemma|Grok|Kimi|Qwen|GLM|DeepSeek|Llama|Mistral|Mixtral|Muse Spark|"
       r"MiniMax|Nemotron|Seed|Solar|Granite|Phi|Command|Nova|Jamba|Hunyuan|Doubao|Yi|Step|o\d")
# Duoi cho phep: TU dat ten (khong phai dong tu/tu Viet) hoac so phien ban. So tran
# (khong cham) chi nhan khi KHONG di truoc mot tu thuong: "Opus 4 (Thinking)" co,
# "55 điểm" khong. Neu khong, "GPT-6 Astra (max) 55 điểm" se an ca "55".
_DUOI = (r"(?:Astra|Flash|Pro|Max|Mini|Nano|Ultra|Sol|Sonnet|Opus|Haiku|Fable|Thinking|Imagine|"
         r"Video|Image|Agent|Spark|Coder|Instruct|Turbo|Lite|Next|Plus|Preview|Chat|Reasoning|"
         r"High|Low|Medium|XHigh|Vision|Code|Omni|Deep|Research|Horizon|Build|Exp|Experimental|"
         r"[KVRM]\d+(?:\.\d+)?[A-Za-z]*|\d+[bB]|\d+\.\d+(?:\.\d+)*[A-Za-z]*|"
         # (?-i:) — tat IGNORECASE cuc bo: co re.I thi [a-z] khop ca "A" cua "Astra"
         r"\d{1,3}(?![\s]*(?-i:[a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])))")
_MODEL = re.compile(r"\b((?:" + _HO + r")(?:[-\s]?" + _DUOI + r")*"
                    r"(?:\s?\((?:max|high|thinking|xhigh|low|medium|pro|mini)\))?)", re.I)

_HANG = re.compile(r"(?:#|hạng |thứ |rank(?:ed)? |vị trí |top )\s?(\d{1,3})\b|\b(\d{1,3})\s?(?:st|nd|rd|th)\b", re.I)


def la_tin_xep_hang(tieu_de: str, tom_tat: str = "") -> bool:
    return bool(_XEP_HANG.search(f"{tieu_de} {tom_tat}"))


def tach_model(tieu_de: str) -> list:
    """Danh sách tên model để thử khớp, DÀI trước NGẮN sau.
    "GPT-6 Astra (max) 55 điểm" -> ["GPT-6 Astra (max)", "GPT-6 Astra", "GPT-6"]."""
    m = _MODEL.search(tieu_de or "")
    if not m:
        return []
    ten = m.group(1).strip(" -:")
    ra = [ten]
    khong_ngoac = re.sub(r"\s?\([^)]*\)$", "", ten).strip()
    if khong_ngoac != ten:
        ra.append(khong_ngoac)
    ws = khong_ngoac.split()
    # bớt dần từ cuối, giữ tối thiểu "Họ + số" (GPT-6) hoặc "Họ Tên" (Muse Spark)
    while len(ws) > 1:
        ws = ws[:-1]
        ra.append(" ".join(ws))
    return list(dict.fromkeys(x for x in ra if len(x) >= 3))


def tach_hang(tieu_de: str, model: str = ""):
    """Thu hang trong tieu de. Tieu de hay nhac HAI model ("GPT-6 ... ap sat #1
    Claude Fable"): mot so hang di lien ngay truoc mot TEN MODEL KHAC thi thuoc ve
    model do, khong phai chu the. Con lai gan cho chu the."""
    t = tieu_de or ""
    for m in _HANG.finditer(t):
        sau = t[m.end():m.end() + 40]
        mm = _MODEL.match(sau.lstrip())
        if mm and model and not mm.group(1).lower().startswith(model.split()[0].lower()):
            continue                                 # "#1 Claude ..." — hang cua Claude
        return int(m.group(1) or m.group(2))
    return None


def goi_y_nguon(tieu_de: str = "", link: str = "", via: str = "", chu: str = "") -> list:
    """Xếp registry: nguồn được NHẮC (link/via/chữ bài) trước, rồi theo chủ đề tin,
    rồi phần còn lại. Không loại nguồn nào — "không giới hạn nguồn"."""
    goi = f"{link} {via} {chu[:3000]}".lower()
    chu_de = f"{tieu_de} {chu[:1500]}".lower()
    diem = {}
    for i, n in enumerate(NGUON):
        d = 1000 - i
        if re.search(n["mien"], goi, re.I):
            d += 500
        for pat, mas in CHU_DE:
            if n["ma"] in mas and re.search(pat, chu_de, re.I):
                d += 200
        diem[n["ma"]] = d
    return sorted(NGUON, key=lambda n: -diem[n["ma"]])


# ---- Chụp ----------------------------------------------------------------------
# Bảng xếp hạng hay nằm trong một KHUNG CUỘN RIÊNG (artificialanalysis: div
# overflow-auto cao 80vh chứa 300 hàng, tài liệu chỉ cao 4000px). Toạ độ "tài liệu"
# vô nghĩa ở đó: window.scrollTo không tới được hàng 125. Nên cách đo là: gọi
# scrollIntoView lên đúng phần tử cần thấy (nó cuộn cả cửa sổ lẫn khung), đợi,
# rồi đo lại theo VIEWPORT và clip ngay — không tính toạ độ trước rồi cuộn sau.
_JS_NORM = """
const norm = s => (s||'').toLowerCase().replace(/[\\s\\-_–—.]+/g,'');
const rect = el => { const r = el.getBoundingClientRect(); return {x: r.x, y: r.y, w: r.width, h: r.height}; };
const khungCuon = el => { for (let e = el.parentElement; e && e !== document.body; e = e.parentElement) {
  const cs = getComputedStyle(e); if (/(auto|scroll)/.test(cs.overflowY) && e.scrollHeight > e.clientHeight + 4) return e; }
  return null; };
const hangHien = t => Array.from(t.querySelectorAll('tr,[role=row]')).filter(r => { const b = r.getBoundingClientRect(); return b.width > 0 && b.height > 0; });
const vung = el => { const k = khungCuon(el); const vw = window.innerWidth, vh = window.innerHeight;
  if (!k) return {x: 0, y: 0, w: vw, h: vh};
  const r = k.getBoundingClientRect();
  return {x: Math.max(0, r.x), y: Math.max(0, r.y), w: Math.min(vw, r.right) - Math.max(0, r.x), h: Math.min(vh, r.bottom) - Math.max(0, r.y)}; };
"""

# Liệt kê MỌI bảng có hàng chứa model (không chỉ bảng lớn nhất — Ông Chủ 06/09:
# "trang ảnh rất ngang chắc chắn còn nhiều benchmark table khác"). Mỗi bảng kèm
# ước lượng tỉ lệ khi chụp đủ cao (rộng / min(cao đủ hàng, trần)), để chọn cái
# vừa khổ hero trước. Đánh dấu data-xh-bang="k" theo thứ tự.
_JS_TIM = _JS_NORM + """
([models, tranCao, tiLeMucTieu]) => {
  const ra = [];
  const bangs = Array.from(document.querySelectorAll('table,[role=table],[role=grid]'))
    .map(t => ({t, rows: hangHien(t)}))
    .filter(b => b.rows.length >= 5 && b.t.getBoundingClientRect().width >= 500);
  let k = 0;
  for (const {t, rows} of bangs) {
    for (const model of models) {
      const nm = norm(model);
      const idx = rows.findIndex((r, i) => i > 0 && norm(r.innerText || r.textContent).includes(nm));
      if (idx < 0) continue;
      const r = rows[idx];
      const cells = Array.from(r.children).map(c => (c.innerText || '').trim().replace(/\\s+/g, ' '));
      const hang = (cells.find(c => /^#?\\d{1,3}$/.test(c)) || '').replace('#', '');
      const img = r.querySelector('img'); if (img) img.setAttribute('data-xh-logo', String(k));
      t.setAttribute('data-xh-bang', String(k)); r.setAttribute('data-xh-row', String(k));
      const w = t.getBoundingClientRect().width;
      const caoDu = rows.slice(0, Math.min(rows.length, 40)).reduce((a, x) => a + x.getBoundingClientRect().height, 0);
      const cao = Math.min(caoDu, tranCao);
      ra.push({k, model, idx, so_hang: rows.length, hang: hang ? parseInt(hang, 10) : null,
               dong: cells.join(' | ').slice(0, 160), logo: !!img, w: Math.round(w),
               ti_le: w / Math.max(1, cao), vua: w / Math.max(1, cao) <= tiLeMucTieu});
      k++; break;
    }
  }
  // vừa khổ trước; trong nhóm đó bảng nhiều hàng hơn trước; rồi tới bảng hẹp hơn
  ra.sort((a, b) => (b.vua - a.vua) || (b.so_hang - a.so_hang) || (a.ti_le - b.ti_le));
  return ra;
}"""

# (phần cũ của _JS_TIM bị thay hết ở dưới — giữ thân cho vòng lặp)
# Cuộn phần tử vào tầm nhìn rồi đo TẤT CẢ theo viewport.
_JS_CUON_DO = _JS_NORM + """
([cach, dau, cuoi, k]) => {
  const t = document.querySelector('[data-xh-bang="' + k + '"]'); if (!t) return null;
  const rows = hangHien(t);
  const hdrH = rows[0].getBoundingClientRect().height;
  if (cach === 'top') { t.scrollIntoView({block: 'start', inline: 'nearest'}); window.scrollBy(0, -8); }
  else { rows[dau].scrollIntoView({block: 'start', inline: 'nearest'}); window.scrollBy(0, -(hdrH + 12)); }
  // Khung cuon con (khong go tran duoc): dat hang dau cua so ngay duoi header dinh.
  const kc = khungCuon(t);
  if (kc) { const kb = kc.getBoundingClientRect(); const muc = cach === 'top' ? t : rows[dau];
    const d = muc.getBoundingClientRect().y - kb.y - (cach === 'top' ? 0 : hdrH + 8);
    if (Math.abs(d) > 2) kc.scrollTop += d; }
  // VUNG DINH (sticky) THAT: header co the hai tang (artificialanalysis: 90px, rows[0]
  // chi 36px) — hang model trot xuong duoi tang hai, bi che. Do dinh/day cua moi phan
  // tu sticky dang nam o mep tren, roi cuon bu cho hang dau cua so nam duoi day do.
  const stickyDo = () => { let top = Infinity, bot = -Infinity;
    for (const e of t.querySelectorAll('thead, thead tr, tr, th, [role=columnheader], [role=rowgroup]')) {
      if (getComputedStyle(e).position !== 'sticky') continue;
      const b = e.getBoundingClientRect(); if (b.height <= 0) continue;
      top = Math.min(top, b.top); bot = Math.max(bot, b.bottom); }
    return isFinite(bot) ? {top, bot} : null; };
  let st = stickyDo();
  if (cach !== 'top' && st) {
    const y = rows[dau].getBoundingClientRect().y;
    if (y < st.bot + 4) { const d = y - (st.bot + 8);
      if (kc) kc.scrollTop += d; else window.scrollBy(0, d); }
    st = stickyDo();
  }
  return {vung: vung(t), bang: rect(t), rows: rows.map(rect), sticky: st,
          idx: rows.findIndex(r => r.getAttribute('data-xh-row') === String(k))};
}"""

_JS_SVG = _JS_NORM + """
(models) => {
  for (const model of models) {
    const nm = norm(model);
    const ts = Array.from(document.querySelectorAll('svg text, svg tspan'))
      .filter(t => norm(t.textContent).includes(nm) && t.getBoundingClientRect().width > 0);
    for (const t of ts) {
      const s = t.closest('svg'); if (!s) continue;
      const sb = s.getBoundingClientRect();
      if (sb.width < 500 || sb.height < 250) continue;
      s.scrollIntoView({block: 'center'});
      return {model, dong: (t.textContent||'').trim().slice(0,80), _t: null};
    }
  }
  return null;
}"""
_JS_SVG_DO = _JS_NORM + """
(models) => {
  for (const model of models) {
    const nm = norm(model);
    const t = Array.from(document.querySelectorAll('svg text, svg tspan'))
      .find(t => norm(t.textContent).includes(nm) && t.getBoundingClientRect().width > 0);
    if (!t) continue; const s = t.closest('svg');
    return {svg: rect(s), nhan: rect(t), vung: vung(s)};
  }
  return null;
}"""


def _doi_bang(page, toi_da_ms: int = 14000):
    """Đợi trang render xong bảng (≥5 hàng hiện) hoặc SVG lớn, tối đa `toi_da_ms`;
    thêm 1.2s cho font/logo. Chờ cố định 6s là đánh bạc: arena text-to-video có
    lúc chưa ra hàng nào ở giây thứ 6."""
    page.wait_for_timeout(1500)
    t0 = time.time()
    while (time.time() - t0) * 1000 < toi_da_ms:
        n = page.evaluate("""() => { let m = 0;
            for (const t of document.querySelectorAll('table,[role=table],[role=grid]')) {
              const k = Array.from(t.querySelectorAll('tr,[role=row]')).filter(r => r.getBoundingClientRect().height > 0).length;
              if (k > m) m = k; }
            const svg = Array.from(document.querySelectorAll('svg')).some(s => s.getBoundingClientRect().width >= 500);
            return m >= 5 ? m : (svg ? -1 : 0); }""")
        if n:
            break
        page.wait_for_timeout(700)
    page.wait_for_timeout(1200)


def _giao(a: dict, b: dict) -> dict:
    x0, y0 = max(a["x"], b["x"]), max(a["y"], b["y"])
    x1, y1 = min(a["x"] + a["w"], b["x"] + b["w"]), min(a["y"] + a["h"], b["y"] + b["h"])
    return {"x": x0, "y": y0, "w": max(0, x1 - x0), "h": max(0, y1 - y0)}


def _chup(page, r: dict, out: Path, dem: int = 8):
    """Chụp `r` (viewport px), thêm `dem` px hai bên nếu còn chỗ — mép bảng sát
    mũi tên sort/ô cuối (thấy trên tbench thu hẹp: "COST ⇅" và "$6.2k" chạm cạnh)."""
    if r["w"] < 50 or r["h"] < 30:
        raise RuntimeError(f"vùng chụp rỗng {r}")
    vw = page.viewport_size["width"]
    x0 = max(0, r["x"] - dem)
    x1 = min(vw, r["x"] + r["w"] + dem)
    page.screenshot(path=str(out), clip={"x": x0, "y": r["y"], "width": x1 - x0, "height": r["h"]})


def _khoanh(png: Path, x: float, y: float, w: float, h: float, dpr: int = DPR):
    im = Image.open(png).convert("RGB")
    d = ImageDraw.Draw(im)
    pad = 3 * dpr
    box = [max(0, x * dpr - pad), max(0, y * dpr - pad),
           min(im.width - 1, (x + w) * dpr + pad), min(im.height - 1, (y + h) * dpr + pad)]
    d.rounded_rectangle(box, radius=6 * dpr, outline=VANG, width=2 * dpr)
    im.save(png, "PNG")
    return im.size


def _cua_so(rows: list, idx: int, hdr_h: float, bang_w: float) -> tuple:
    """[dau, cuoi] hàng đưa vào ảnh. Trong top → từ hàng 1; sâu → từ idx-2. Kéo
    xuống tới khi ảnh đủ cao (rộng/cao <= TI_LE_MUC_TIEU) hoặc chạm trần."""
    n = len(rows)
    dau = 1 if idx <= TOP_MAC_DINH + 2 else max(1, idx - TREN_MODEL)
    cuoi = min(n - 1, max(idx + 2, dau + TOP_MAC_DINH - 1))
    cao = lambda k: rows[k]["y"] + rows[k]["h"] - rows[dau]["y"] + hdr_h
    while cuoi + 1 < n and cao(cuoi) < bang_w / TI_LE_MUC_TIEU and cao(cuoi + 1) <= CAO_TOI_DA_CSS:
        cuoi += 1
    while cuoi > idx + 1 and cao(cuoi) > CAO_TOI_DA_CSS:
        cuoi -= 1
    return dau, cuoi


TI_LE_GHEP = 1.6               # rộng/cao trên mức này thì một bảng không đi một mình vào hero được


def _chup_mot_bang(page, tim: dict, out: Path, dpr: int = DPR):
    """Chụp cửa sổ top-N của MỘT bảng (đã đánh dấu k), khoanh hàng model."""
    idx, k = tim["idx"], tim["k"]
    out.parent.mkdir(parents=True, exist_ok=True)
    # Lượt 1: cuộn header lên đầu (trường hợp top) hoặc hàng model vào giữa (sâu), đo.
    trong_top = idx <= TOP_MAC_DINH + 2
    do = page.evaluate(_JS_CUON_DO, ["top" if trong_top else "row", idx, idx, k])
    page.wait_for_timeout(400)
    do = page.evaluate(_JS_CUON_DO, ["top" if trong_top else "row", idx, idx, k])
    rows, vung, hdr = do["rows"], do["vung"], do["rows"][0]
    st = do.get("sticky")
    hdr_h = max(hdr["h"], (st["bot"] - st["top"]) if st else 0)
    dau, cuoi = _cua_so(rows, idx, hdr_h, do["bang"]["w"])
    x, w = do["bang"]["x"], do["bang"]["w"]
    # Hàng nào nằm dưới vùng DÍNH (header sticky, có thể nhiều tầng) hoặc ngoài
    # vùng nhìn thì bỏ khỏi band — không chụp cái không hiện.
    duoi_hdr = max(hdr["y"] + hdr["h"] if hdr["y"] >= vung["y"] - 1 else vung["y"],
                   st["bot"] if st else -1)
    hien = [k for k in range(dau, cuoi + 1)
            if rows[k]["y"] >= duoi_hdr - 1 and rows[k]["y"] + rows[k]["h"] <= vung["y"] + vung["h"] + 1]
    if idx not in hien and trong_top:
        # Hang model bi che (header dinh cao / cuon lech): thu cach 'row' — hang dau
        # cua so len dau viewport, lui mot header.
        do = page.evaluate(_JS_CUON_DO, ["row", dau, dau, k]); page.wait_for_timeout(300)
        do = page.evaluate(_JS_CUON_DO, ["row", dau, dau, k])
        rows, vung, hdr = do["rows"], do["vung"], do["rows"][0]
        st = do.get("sticky")
        duoi_hdr = max(hdr["y"] + hdr["h"] if hdr["y"] >= vung["y"] - 1 else vung["y"],
                       st["bot"] if st else -1)
        hien = [k for k in range(dau, cuoi + 1)
                if rows[k]["y"] >= duoi_hdr - 1 and rows[k]["y"] + rows[k]["h"] <= vung["y"] + vung["h"] + 1]
    if idx not in hien:
        return None, (f"thấy hàng {idx}/{tim['so_hang']} nhưng không đưa vào tầm nhìn được "
                      f"(vùng {round(vung['y'])}..{round(vung['y']+vung['h'])}, hàng y={round(rows[idx]['y'])} "
                      f"h={round(rows[idx]['h'])}, header y={round(hdr['y'])} h={round(hdr['h'])}, {len(hien)} hàng hiện)")
    dau, cuoi = hien[0], hien[-1]
    band = {"x": x, "w": w, "y": rows[dau]["y"], "h": rows[cuoi]["y"] + rows[cuoi]["h"] - rows[dau]["y"]}
    # Header lien ke band: header thuong (rows[0]) ngay tren, HOAC vung sticky ket
    # thuc sat tren band -> mot clip lien tu dinh header/sticky xuong het band.
    dinh = None
    if vung["y"] - 1 <= hdr["y"] and hdr["y"] + hdr["h"] <= band["y"] + 2:
        dinh = hdr["y"]
    elif st and st["bot"] <= band["y"] + 12 and st["top"] >= vung["y"] - 1:
        dinh = st["top"]
    if dinh is not None:
        r = _giao({"x": x, "w": w, "y": dinh, "h": band["y"] + band["h"] - dinh}, vung)
        _chup(page, r, out)
        goc = (max(0, r["x"] - 8), r["y"]); do_hdr = 0
    else:
        # Header không liền band (model sâu, header không dính): chụp riêng rồi ghép.
        p1, p2 = out.with_suffix(".h.png"), out.with_suffix(".b.png")
        _chup(page, _giao(band, vung), p2)
        row_luu = dict(rows[idx]); band_luu = dict(band)
        do2 = page.evaluate(_JS_CUON_DO, ["top", 0, 0, k]); page.wait_for_timeout(300)
        do2 = page.evaluate(_JS_CUON_DO, ["top", 0, 0, k])
        h2 = do2["rows"][0]
        _chup(page, _giao({"x": x, "w": w, "y": h2["y"], "h": h2["h"]}, do2["vung"]), p1)
        a, b = Image.open(p1).convert("RGB"), Image.open(p2).convert("RGB")
        g = Image.new("RGB", (max(a.width, b.width), a.height + b.height), (255, 255, 255))
        g.paste(a, (0, 0)); g.paste(b, (0, a.height)); g.save(out, "PNG"); p1.unlink(); p2.unlink()
        rows[idx] = row_luu; band = band_luu
        goc = (max(0, max(band["x"], vung["x"]) - 8), max(band["y"], vung["y"])); do_hdr = a.height / dpr
    row = rows[idx]
    _khoanh(out, row["x"] - goc[0], row["y"] - goc[1] + do_hdr, min(row["w"], w), row["h"], dpr)
    return {"kieu": "bang", "model": tim["model"], "hang": tim["hang"], "dong": tim["dong"],
            "idx": idx, "so_hang": tim["so_hang"], "logo_co": tim["logo"]}, ""


def chup_bang(page, models: list, out: Path, dpr: int = DPR):
    """Chụp bảng chứa model, chọn bảng VỪA KHỔ nhất trên trang.

    Ông Chủ 06/09/2026: "với những trang ảnh rất ngang, chắc chắn trong trang đó
    còn nhiều benchmark table khác có thể sử dụng". Trước đây lấy bảng lớn nhất rồi
    chịu thua nếu nó quá ngang (tbench: 15 hàng, rộng/cao 3.2). Nay: liệt kê mọi
    bảng có hàng model, thử theo thứ tự vừa khổ → nhiều hàng → hẹp; bảng đầu tiên
    ra rộng/cao ≤ TI_LE_GHEP thì dùng. Không bảng nào đủ cao thì GHÉP DỌC hai bảng
    cùng trang (cùng tone sẵn, mỗi bảng đã khoanh model), bảng vừa hơn lên trên."""
    ung = page.evaluate(_JS_TIM, [models, CAO_TOI_DA_CSS, TI_LE_MUC_TIEU])
    if not ung:
        return None, "không có bảng ≥5 hàng chứa tên model"
    out.parent.mkdir(parents=True, exist_ok=True)
    da, ly_do = [], []
    for tim in ung[:3]:
        p = out if not da else out.with_suffix(f".b{len(da)}.png")
        try:
            kq, ld = _chup_mot_bang(page, tim, p, dpr)
        except Exception as e:                               # noqa: BLE001
            kq, ld = None, f"{type(e).__name__}: {str(e)[:60]}"
        if not kq:
            ly_do.append(f"bảng {tim['k']} ({tim['so_hang']} hàng): {ld}")
            continue
        with Image.open(p) as im:
            r = im.width / im.height
        da.append((kq, p, r, tim))
        if r <= TI_LE_GHEP:
            break
    if not da:
        return None, "; ".join(ly_do)
    da.sort(key=lambda t: (t[2] > TI_LE_GHEP, t[2]))
    kq, p, r, tim = da[0]
    if r > TI_LE_GHEP and len(da) < 2:
        # Trang chi co MOT bang va no qua ngang (tbench: 15 hang trai 2319px o viewport
        # 2400): bang responsive tra rong theo cua so. Thu hep cua so — bang tu don
        # cot, van du noi dung, chi bo cuc hep lai. Lay ban dau tien vua kho.
        rong_cu = page.viewport_size["width"]
        for rong in (1500, 1200, 1000):
            page.set_viewport_size({"width": rong, "height": page.viewport_size["height"]})
            page.wait_for_timeout(700)
            p2 = out.with_suffix(f".w{rong}.png")
            try:
                kq2, _ = _chup_mot_bang(page, tim, p2, dpr)
            except Exception:                                # noqa: BLE001
                kq2 = None
            if not kq2:
                continue
            with Image.open(p2) as im2:
                r2 = im2.width / im2.height
            if r2 < r:
                for _, q, _, _ in da:
                    if q != out and q.exists():
                        q.unlink()
                da = [(kq2, p2, r2, tim)]
                kq, p, r = kq2, p2, r2
                kq["viewport"] = rong
            else:
                p2.unlink(missing_ok=True)
            if r <= TI_LE_GHEP:
                break
        page.set_viewport_size({"width": rong_cu, "height": page.viewport_size["height"]})
    if r > TI_LE_GHEP and len(da) >= 2:
        kq2, p2, r2, tim2 = da[1]
        a, b = Image.open(p).convert("RGB"), Image.open(p2).convert("RGB")
        b = b.resize((a.width, round(b.height * a.width / b.width)), Image.LANCZOS)
        g = Image.new("RGB", (a.width, a.height + b.height), (255, 255, 255))
        g.paste(a, (0, 0)); g.paste(b, (0, a.height))
        g.save(out, "PNG")
        kq = {**kq, "kieu": "bang-ghep", "dong": kq["dong"] + " ‖ " + kq2["dong"][:60],
              "ghep_voi": tim2["k"]}
    elif p != out:
        p.replace(out)
    for _, q, _, _ in da:
        if q != out and q.exists():
            q.unlink()
    if len(ung) > 1:
        kq["so_bang"] = len(ung)
    return kq, ""


def chup_svg(page, models: list, out: Path, dpr: int = DPR):
    tim = page.evaluate(_JS_SVG, models)
    if not tim:
        return None, "không có nhãn SVG chứa tên model"
    page.wait_for_timeout(400)
    do = page.evaluate(_JS_SVG_DO, models)
    if not do:
        return None, "nhãn SVG mất sau khi cuộn"
    out.parent.mkdir(parents=True, exist_ok=True)
    s = do["svg"]
    r = _giao({"x": s["x"], "y": s["y"], "w": s["w"], "h": min(s["h"], CAO_TOI_DA_CSS)}, do["vung"])
    _chup(page, r, out)
    n = do["nhan"]
    _khoanh(out, n["x"] - r["x"], n["y"] - r["y"], n["w"], n["h"], dpr)
    return {"kieu": "svg", "model": tim["model"], "hang": None, "dong": tim["dong"], "logo_co": False}, ""


def chup_logo(page, out: Path):
    """Logo model từ chính hàng vừa khớp (đã đánh dấu data-xh-logo). Best-effort."""
    try:
        el = page.query_selector("[data-xh-logo]")
        if not el:
            return None
        el.scroll_into_view_if_needed()
        el.screenshot(path=str(out))
        return out if out.exists() and out.stat().st_size > 200 else None
    except Exception:                                        # noqa: BLE001
        return None


def _dong_dau(png: Path, xuat_xu: str, **them):
    """`xuat_xu` la dau nguon_dung (chup_xep_hang / the_xep_hang); `them` la cac
    khoa mo ta (model, nguon, site, bang, hang, url) — ten khac nhau de khong dam."""
    im = Image.open(png)
    im.load()
    meta = luat_anh.dong_dau(xuat_xu)
    for k, v in them.items():
        if v is not None:
            meta.add_text(k, str(v))
    im.save(png, "PNG", pnginfo=meta)


# ---- Thẻ dự phòng: tên model + #hạng + logo + site ------------------------------
def the_du_phong(model: str, hang, site: str, bang: str, out: Path, brand: str = "donniechublog",
                 logo: Path | None = None, w: int = 1200, h: int = 1500) -> Path:
    """Khi không nguồn nào chụp được. Không phải minh hoạ — là một THẺ DỮ LIỆU:
    đúng bốn thứ Ông Chủ chốt, không thêm gì. Nội dung dồn lên NỬA TRÊN có chủ ý:
    thẻ này là `--image` của card.py, hook sẽ đè lên nửa dưới qua màn tối."""
    import card
    b = card.dat_thuong_hieu(brand)
    im = Image.new("RGB", (w, h), card.BG)
    d = ImageDraw.Draw(im)
    f_nho = card._f(card.F_MONO, 30)
    f_hang = card._f(card.F_HERO, 420, 700)
    f_ten = card._f(card.F_QUOTE, 84)
    f_phu = card._f(card.F_QUOTE_REG, 34)
    def giua(txt, font, y, mau):
        """Ve chu can giua theo INK BBOX that (Oswald 420pt bao cao hon ink ~25%,
        cong theo font.size la de chu sau de len chu truoc — loi thay tren the
        thu 06/09). Tra ve y duoi cung cua ink."""
        l, t, r, bt = d.textbbox((0, 0), txt, font=font)
        d.text((w / 2 - (r + l) / 2, y - t), txt, font=font, fill=mau)
        return y + (bt - t)

    y = 140
    nhan = f"{site} · {bang}".upper()
    y = giua(nhan, f_nho, y, card.CYAN) + 70
    if logo and Path(logo).exists():
        try:
            lg = Image.open(logo).convert("RGBA")
            lg.thumbnail((160, 160), Image.LANCZOS)
            im.paste(lg, (w // 2 - lg.width // 2, y), lg)
            y += lg.height + 50
        except Exception:                                    # noqa: BLE001
            pass
    # Co hang: "#N" la nhan vat chinh, ten model duoi. Khong hang: ten model la
    # nhan vat chinh — khong bia mot chu "TOP" vo nghia.
    if hang:
        y = giua(f"#{hang}", f_hang, y, card.FG) + 60
        f_ten_dung = f_ten
    else:
        f_ten_dung = card._f(card.F_QUOTE, 120)
        y += 120
    ten = model
    while d.textlength(ten, font=f_ten_dung) > w - 160 and f_ten_dung.size > 44:
        f_ten_dung = card._f(card.F_QUOTE, f_ten_dung.size - 6)
    y = giua(ten, f_ten_dung, y, card.FG) + 44
    d.line([(w // 2 - 60, y), (w // 2 + 60, y)], fill=card.CYAN, width=4)
    y += 44
    giua(f"trên bảng xếp hạng {bang}", f_phu, y, card.MUTED)
    handle = b.get("handle") or "@donniechublog"
    d.text((w // 2 - d.textlength(handle, font=f_nho) / 2, h - 110), handle, font=f_nho, fill=card.MUTED)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PNG")
    _dong_dau(out, "the_xep_hang", model=model, hang=hang, nguon=site, bang=bang)
    return out


# ---- Điều phối --------------------------------------------------------------------
def tim_va_chup(models: list, nguon_ds: list, out_dir: Path, brand: str = "donniechublog",
                hang_goi_y=None, gio_han: int = 150, in_log=print) -> dict | None:
    """Đi qua từng nguồn, nguồn nào ra ảnh khoanh được model thì dừng. Không nguồn
    nào → thẻ dự phòng. Trả về dict mô tả ảnh (tep, kieu, nguon, site, bang, hang,
    model, url) hoặc None nếu ngay cả thẻ dự phòng cũng không dựng được."""
    if not models:
        return None
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        in_log("[xep_hang] thiếu playwright — chỉ dựng được thẻ dự phòng")
        n = nguon_ds[0] if nguon_ds else NGUON[0]
        out = out_dir / "xep_hang_the.png"
        the_du_phong(models[0], hang_goi_y, n["site"], n["bang"], out, brand)
        return {"tep": str(out), "kieu": "the", "nguon": n["ma"], "site": n["site"], "bang": n["bang"],
                "hang": hang_goi_y, "model": models[0], "url": n["url"]}
    t0 = time.time()
    logo = None
    kq_cuoi = None
    with sync_playwright() as p:
        br = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage", "--force-color-profile=srgb"])
        # Viewport cao san bang tran cua so chup: khong doi kich thuoc giua chung
        # (doi la trang reflow, bbox do truoc do lech).
        ctx = br.new_context(viewport={"width": 2400, "height": CAO_TOI_DA_CSS + 250},
                             device_scale_factor=DPR, user_agent=UA)
        pg = ctx.new_page()
        for n in nguon_ds:
            if time.time() - t0 > gio_han:
                in_log(f"[xep_hang] hết giờ ({gio_han}s), dừng ở {n['ma']}")
                break
            out = out_dir / f"xep_hang_{n['ma']}.png"
            try:
                resp = pg.goto(n["url"], wait_until="domcontentloaded", timeout=40000)
                # Cloudflare challenge / 429: khong doi 14s vo ich, sang nguon khac ngay.
                # (arena.ai tra 429 "Just a moment..." sau ~25 luot thu tu mot IP trong
                # mot gio — may local luc dev; server moi bai goi mot lan.)
                pg.wait_for_timeout(800)
                tieu_de = (pg.title() or "").lower()
                if (resp and resp.status in (403, 429, 503)) or re.search(
                        r"just a moment|security verification|attention required|access denied", tieu_de):
                    in_log(f"[xep_hang] {n['ma']}: nguồn chặn ({resp.status if resp else '?'} — {tieu_de[:40]!r}), bỏ qua")
                    continue
                _doi_bang(pg)
                kq, ly_do = chup_bang(pg, models, out, DPR)
                if not kq:
                    kq2, ly_do2 = chup_svg(pg, models, out, DPR)
                    kq, ly_do = kq2, f"bảng: {ly_do}; svg: {ly_do2}"
            except Exception as e:                           # noqa: BLE001
                in_log(f"[xep_hang] {n['ma']}: {type(e).__name__}: {str(e)[:80]}")
                continue
            if not kq:
                in_log(f"[xep_hang] {n['ma']}: bỏ — {ly_do}")
                continue
            if kq.get("logo_co") and not logo:
                logo = chup_logo(pg, out_dir / "xep_hang_logo.png")
            _dong_dau(out, "chup_xep_hang", model=kq["model"], nguon=n["ma"], site=n["site"],
                      bang=n["bang"], hang=kq.get("hang"), url=n["url"])
            im = Image.open(out)
            in_log(f"[xep_hang] {n['ma']}: khớp {kq['model']!r} hàng #{kq.get('hang') or '?'} "
                   f"({kq['kieu']}, {im.width}x{im.height}) — {kq['dong'][:70]}")
            kq_cuoi = {"tep": str(out), "kieu": kq["kieu"], "nguon": n["ma"], "site": n["site"],
                       "bang": n["bang"], "hang": kq.get("hang") or hang_goi_y, "model": kq["model"],
                       "url": n["url"], "dong": kq["dong"], "logo": str(logo) if logo else None}
            break
        br.close()
    if kq_cuoi:
        return kq_cuoi
    n = nguon_ds[0] if nguon_ds else NGUON[0]
    out = out_dir / "xep_hang_the.png"
    the_du_phong(models[0], hang_goi_y, n["site"], n["bang"], out, brand, logo)
    in_log(f"[xep_hang] không nguồn nào chụp được → thẻ dự phòng {models[0]} #{hang_goi_y or '?'}")
    return {"tep": str(out), "kieu": "the", "nguon": n["ma"], "site": n["site"], "bang": n["bang"],
            "hang": hang_goi_y, "model": models[0], "url": n["url"], "logo": str(logo) if logo else None}


def main() -> int:
    ap = argparse.ArgumentParser(description="Ảnh xếp hạng: chụp bảng đúng nguồn, khoanh đúng model")
    ap.add_argument("--tieu-de", default="", help="Tiêu đề tin (tự tách model + hạng + chủ đề)")
    ap.add_argument("--model", default="", help="Tên model (ghi đè tách từ tiêu đề)")
    ap.add_argument("--hang", type=int, default=None)
    ap.add_argument("--nguon", default="", help="Mã nguồn thử trước (arena-code, tbench, aa-models...)")
    ap.add_argument("--link", default="", help="Link bài, để gợi ý nguồn")
    ap.add_argument("--brand", default="donniechublog")
    ap.add_argument("--ra", required=True, help="Tệp PNG ra")
    a = ap.parse_args()
    models = [a.model] if a.model else tach_model(a.tieu_de)
    if not models:
        sys.exit("Không tách được tên model — truyền --model")
    ds = goi_y_nguon(a.tieu_de, a.link)
    if a.nguon:
        ds = [n for n in NGUON if n["ma"] == a.nguon] + [n for n in ds if n["ma"] != a.nguon]
    ra = Path(a.ra)
    kq = tim_va_chup(models, ds, ra.parent / ".xep_hang_tmp", a.brand,
                     a.hang if a.hang is not None else tach_hang(a.tieu_de, models[0]),
                     in_log=lambda s: print(s, file=sys.stderr))
    if not kq:
        sys.exit("Không ra ảnh")
    Path(kq["tep"]).replace(ra)
    kq["tep"] = str(ra)
    print(json.dumps(kq, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
