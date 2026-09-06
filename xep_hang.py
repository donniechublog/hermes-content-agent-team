#!/usr/bin/env python3
"""xep_hang.py — ẢNH CHO TIN XẾP HẠNG: chụp bảng xếp hạng thật, khoanh đúng model.

Luật Ông Chủ 06/09/2026: tin về thứ hạng thì ảnh phải là bảng/chart xếp hạng —
không có sẵn thì tự chụp màn hình, chụp phải khoanh đúng model đang nói tới,
không chụp được thì thẻ dữ liệu (tên model + #hạng + logo + site).

Vì sao là tệp riêng: engine chung chỉ chụp figure/table trên trang BÀI BÁO, còn
bảng xếp hạng nằm ở TRANG XẾP HẠNG và phải khoanh đúng hàng. Không có nó, ba thẻ
liền nhau (04–06/09) đã lấy bảng tỉ số giải golf và bảng câu cá trên băng vì
khớp chữ "leaderboard".

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
# Vien mobile, chi cho nguon danh dau "mobile" (arena.ai — co giao dien mobile
# rieng, danh sach the doc thay vi bang cuon ngang). 414px * DPR 3 = 1242px, gan
# khop kho the 1200px nen chu gan nhu khong bi co; chup desktop thi 2668px phai
# co gan mot nua, chu nho han hai lan.
MOBILE_VIEWPORT = {"width": 414, "height": 896}
MOBILE_DPR = 3
MOBILE_UA = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 "
            "(KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1")
VANG = (245, 197, 24)          # màu khoanh — cùng gam với đồ hoạ tham chiếu của arena.ai
TOP_MAC_DINH = 10              # ít nhất top-N khi model nằm trong top
TREN_MODEL = 2                 # model nằm sâu: giữ 2 hàng phía trên, kéo dài xuống dưới
CAO_TOI_DA_CSS = 1500          # trần chiều cao cửa sổ chụp (CSS px)
GIO_HAN = 150                  # trần thời gian đi hết các nguồn (giây)
# Anh coi la VUA KHO khi rong/cao <= muc nay. Cong hero chan o 1.6 (kiem_anh_thap:
# anh di mot minh phai chiem >=50% kho 4:5), de 1.5 cho co bien.
TI_LE_VUA = 1.5

# ---- Registry nguồn xếp hạng --------------------------------------------------
# Thu tu trong danh sach = uu tien khi tin khong goi y gi; `goi_y_nguon` chi xep
# lai thu tu nay, khong them nguon la.
NGUON = [
    {"ma": "arena-text",     "site": "ARENA.AI",  "bang": "Text Arena",
     "url": "https://arena.ai/leaderboard/text",          "mien": r"arena\.ai|lmarena", "mobile": True},
    {"ma": "arena-code",     "site": "ARENA.AI",  "bang": "WebDev / Code Arena",
     "url": "https://arena.ai/leaderboard/code",          "mien": r"arena\.ai|lmarena", "mobile": True},
    {"ma": "arena-vision",   "site": "ARENA.AI",  "bang": "Vision Arena",
     "url": "https://arena.ai/leaderboard/vision",        "mien": r"arena\.ai|lmarena", "mobile": True},
    {"ma": "arena-t2i",      "site": "ARENA.AI",  "bang": "Text-to-Image Arena",
     "url": "https://arena.ai/leaderboard/text-to-image", "mien": r"arena\.ai|lmarena", "mobile": True},
    {"ma": "arena-t2v",      "site": "ARENA.AI",  "bang": "Text-to-Video Arena",
     "url": "https://arena.ai/leaderboard/text-to-video", "mien": r"arena\.ai|lmarena", "mobile": True},
    {"ma": "arena-search",   "site": "ARENA.AI",  "bang": "Search Arena",
     "url": "https://arena.ai/leaderboard/search",        "mien": r"arena\.ai|lmarena", "mobile": True},
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
    # Ông Chủ 06/09/2026: "phải sử dụng hình ảnh từ tất cả trang này, đừng tự giới
    # hạn nguồn ảnh". Bảy mục dưới đây đều ĐO THẬT (chụp ra ảnh có khoanh model)
    # trước khi thêm — không thêm nguồn chưa chụp được, vì mỗi nguồn hỏng ngốn
    # ~18s của trần 150s mà không bao giờ ra ảnh.
    # ĐÃ THỬ, CHƯA ĐƯỢC, nên KHÔNG có trong danh sách:
    #   bigcode-bench.github.io — có bảng 171 hàng nhưng hàng nằm dưới đáy khung
    #     nhìn mà `scrollIntoView` không kéo trang lên (khung cuộn lạ).
    #   designarena.ai / scale.com/leaderboard / vals.ai — không có <table> lẫn
    #     nhóm hàng lặp nào nhận ra được; mỗi trang cần một bộ bóc riêng.
    #   epoch.ai — bảng vẽ bằng <canvas>, không định vị được hàng để khoanh.
    #   mteb (HF Space) — benchmark embedding, không phải xếp hạng model kiểu tin.
    # KHONG mobile: openrouter khong render bang xep hang nao o khung <900px.
    {"ma": "openrouter",     "site": "OPENROUTER.AI", "bang": "LLM Rankings (lượt dùng)",
     "url": "https://openrouter.ai/rankings",             "mien": r"openrouter"},
    {"ma": "livecodebench",  "site": "LIVECODEBENCH", "bang": "LiveCodeBench",
     "url": "https://livecodebench.github.io/leaderboard.html", "mien": r"livecodebench"},
    {"ma": "bfcl",           "site": "GORILLA (UC BERKELEY)", "bang": "Function-Calling Leaderboard",
     "url": "https://gorilla.cs.berkeley.edu/leaderboard.html",
     "mien": r"\bbfcl\b|gorilla\.cs\.berkeley|berkeley function"},
    {"ma": "gaia",           "site": "GAIA BENCHMARK", "bang": "GAIA",
     "url": "https://gaia-benchmark-leaderboard.hf.space/", "mien": r"\bgaia\b"},
    {"ma": "hle",            "site": "SAFE.AI", "bang": "Humanity's Last Exam",
     "url": "https://agi.safe.ai/",                       "mien": r"agi\.safe\.ai|humanity'?s? last exam|\bHLE\b"},
    {"ma": "vellum",         "site": "VELLUM.AI", "bang": "LLM Leaderboard",
     "url": "https://www.vellum.ai/llm-leaderboard",      "mien": r"vellum"},
    {"ma": "opencompass",    "site": "OPENCOMPASS", "bang": "OpenCompass LLM",
     "url": "https://rank.opencompass.org.cn/leaderboard/llm", "mien": r"opencompass|司南"},
]

# Từ khoá chọn bảng con của một site theo chủ đề tin (video → arena-t2v trước...)
CHU_DE = [
    (r"\bvideo\b|text-to-video|tạo video", ["arena-t2v"]),
    (r"\bimage\b|text-to-image|tạo ảnh|hình ảnh", ["arena-t2i"]),
    (r"\bvision\b|thị giác|multimodal|đa phương thức", ["arena-vision"]),
    (r"webdev|frontend|front-end|\bcode\b|coding|lập trình|swe[-_ ]?bench",
     ["arena-code", "swebench", "aider", "livecodebench"]),
    (r"terminal|agentic|\bagent\b", ["tbench", "gaia"]),
    (r"\bsearch\b|tìm kiếm", ["arena-search"]),
    (r"intelligence|trí tuệ|artificial ?analysis", ["aa-models"]),
    # Xep hang theo LUOT DUNG THAT, khong phai diem benchmark — khac han ve ban chat
    # nen phai co tu khoa rieng, dung de tin "top 10 OpenRouter" roi vao bang diem.
    (r"openrouter|\busage\b|lượt dùng|thị phần|market share|token/tuần", ["openrouter"]),
    (r"function[- ]?call|tool[- ]?use|gọi hàm|dùng công cụ", ["bfcl"]),
    (r"humanity'?s? last exam|\bhle\b|đề thi khó nhất", ["hle"]),
]

# ---- Nhận diện tin xếp hạng + tách model/hạng ---------------------------------
# CHI nhan khi co dau hieu BANG XEP HANG, khong nhan tu roi. Truoc 06/09/2026
# mau nay con bat "vượt", "dẫn đầu", "đứng đầu", "số 1", "top N" dung mot minh —
# nhung chu co trong hau het tom tat cua Finn/Nova/Vera. Do that: 6/6 tieu de
# goi von / doanh thu / gia chip deu bi dong dau TIN XEP HANG ("Reflection gọi
# vốn 2 tỷ USD, vòng seed do Nvidia dẫn đầu"), keo theo ca chuoi hong ben duoi.
_XEP_HANG = re.compile(
    # (a) ten bang / khai niem xep hang — tu no da du nghia
    r"(xếp hạng|thứ hạng|bảng xếp hạng|leaderboard|ranking|ranked|\brank\b|"
    r"elo|arena|intelligence index|trí tuệ .{0,20}(artificial|analysis)|"
    r"soán ngôi|lọt top|"
    # (b) tu chi vi tri — CHI khi di kem ngu canh bang/benchmark trong 40 ky tu
    r"(?:đứng đầu|dẫn đầu|đứng thứ|vượt|áp sát|chen chân|số 1|number one|no\.\s?1|"
    r"first place|hạng \d|#\s?\d|top\s?\d|top-\d|leo \d|leo lên)"
    r".{0,40}(bảng|leaderboard|arena|benchmark|xếp hạng|bxh)|"
    r"(?:bảng|leaderboard|arena|benchmark|xếp hạng|bxh).{0,40}"
    r"(?:đứng đầu|dẫn đầu|đứng thứ|vượt|áp sát|số 1|hạng \d|#\s?\d|top\s?\d|leo lên))", re.I)

# Họ model + đuôi phiên bản. Bắt cả "GPT-6 Astra (max)", "Claude Fable 5.1", "Kimi-K3",
# "Grok Imagine Video 1.5 Agent", "Qwen3.8-27B", "GLM-5.2 (Max)", "Muse Spark 1.2".
# Ho model. Cac ho TRUNG TU THUONG tieng Anh/Viet (Seed, Solar, Granite, Phi,
# Command, Nova, Step, Yi) da tach rieng xuong _HO_CAN_SO: chung chi duoc nhan
# khi DI KEM so phien ban. Truoc 06/09/2026 chung nam chung o day, nen "vòng
# seed do Nvidia dẫn đầu" ra models=['seed'] va keo ca engine di luc 11 bang
# xep hang cho mot tin goi von.
_HO = (r"GPT|Claude|Gemini|Gemma|Grok|Kimi|Qwen|GLM|DeepSeek|Llama|Mistral|Mixtral|Muse Spark|"
       r"MiniMax|Nemotron|Jamba|Hunyuan|Doubao|o\d")
_HO_CAN_SO = r"Seed|Solar|Granite|Phi|Command|Nova|Step|Yi"
# Duoi cho phep: TU dat ten (khong phai dong tu/tu Viet) hoac so phien ban. So tran
# (khong cham) chi nhan khi KHONG di truoc mot tu thuong: "Opus 4 (Thinking)" co,
# "55 điểm" khong. Neu khong, "GPT-6 Astra (max) 55 điểm" se an ca "55".
_DUOI = (r"(?:Astra|Flash|Pro|Max|Mini|Nano|Ultra|Sol|Sonnet|Opus|Haiku|Fable|Thinking|Imagine|"
         r"Video|Image|Agent|Spark|Coder|Instruct|Turbo|Lite|Next|Plus|Preview|Chat|Reasoning|"
         r"High|Low|Medium|XHigh|Vision|Code|Omni|Deep|Research|Horizon|Build|Experimental|Exp|"
         r"[KVRM]\d+(?:\.\d+)?[A-Za-z]*|\d+[bB]|\d+\.\d+(?:\.\d+)*[A-Za-z]*|"
         # (?-i:) — tat IGNORECASE cuc bo: co re.I thi [a-z] khop ca "A" cua "Astra"
         r"\d{1,3}(?![\s]*(?-i:[a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ])))")
_MODEL = re.compile(r"\b((?:(?:" + _HO + r")|(?:(?:" + _HO_CAN_SO + r")(?=[-\s]?\d)))"
                    r"(?:[-\s]?" + _DUOI + r")*"
                    r"(?:\s?\((?:max|high|thinking|xhigh|low|medium|pro|mini)\))?)", re.I)

_HANG = re.compile(r"(?:#|hạng |thứ |rank(?:ed)? |vị trí |top )\s?(\d{1,3})\b|\b(\d{1,3})\s?(?:st|nd|rd|th)\b", re.I)


def la_tin_xep_hang(tieu_de: str, tom_tat: str) -> bool:
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


def tach_hang(tieu_de: str, model: str):
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
    """Xếp registry: nguồn được NHẮC (tiêu đề/link/via/chữ bài) trước, rồi theo chủ
    đề tin, rồi phần còn lại. Không loại nguồn nào — "không giới hạn nguồn".

    Mỗi mục trả về mang thêm `duoc_nhac`: True khi CHÍNH TIN nhắc tới nguồn đó.
    Chụp được từ nguồn `duoc_nhac=False` nghĩa là ảnh nói về MỘT BẢNG KHÁC với
    bảng trong tiêu đề — vẫn dùng được nhưng phải cảnh báo, xem `cau_xep_hang`
    trong anh_chuan_bi.py."""
    # Tieu de NAM TRONG chuoi do "nguon duoc nhac": tin hay goi thang ten trang
    # ("#1 LiveCodeBench", "leo top OpenCompass") ma khong co link toi trang do.
    goi = f"{tieu_de} {link} {via} {chu[:3000]}".lower()
    chu_de = f"{tieu_de} {chu[:1500]}".lower()
    diem, ra = {}, []
    for i, n in enumerate(NGUON):
        d = 1000 - i
        nhac = bool(re.search(n["mien"], goi, re.I))
        if nhac:
            d += 500
        for pat, mas in CHU_DE:
            if n["ma"] in mas and re.search(pat, chu_de, re.I):
                d += 200
        diem[n["ma"]] = d
        ra.append({**n, "duoc_nhac": nhac})
    return sorted(ra, key=lambda n: -diem[n["ma"]])


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
      // Cot HANG (neu co) luon nam trong hai o dau tien tinh tu trai — arena "Rank",
      // swebench cot checkbox+"#", tbench "RANK". artificialanalysis KHONG CO cot hang
      // (sap xep ngam theo Intelligence Index) nen KHONG duoc do o ca hang: truoc day
      // regex bat BAT KY o nao khop "so nguyen <=3 chu so" trong ca hang, va vo nham
      // chinh diem Intelligence (vd "55") lam thu hang — bao sai "hang #55" trong khi
      // do la diem so. Gioi han vung do ve HAI O DAU tien moi dung.
      const hang = (cells.slice(0, 2).find(c => /^#?\\d{1,3}$/.test(c)) || '').replace('#', '');
      const img = r.querySelector('img'); if (img) img.setAttribute('data-xh-logo', String(k));
      t.setAttribute('data-xh-bang', String(k));
      const w = t.getBoundingClientRect().width;
      const caoDu = rows.slice(0, Math.min(rows.length, 40)).reduce((a, x) => a + x.getBoundingClientRect().height, 0);
      const cao = Math.min(caoDu, tranCao);
      ra.push({k, model, idx, so_hang: rows.length, hang: hang ? parseInt(hang, 10) : null,
               dong: cells.join(' | ').slice(0, 160), logo: !!img,
               ti_le: w / Math.max(1, cao), vua: w / Math.max(1, cao) <= tiLeMucTieu});
      k++; break;
    }
  }
  // vừa khổ trước; trong nhóm đó bảng nhiều hàng hơn trước; rồi tới bảng hẹp hơn
  ra.sort((a, b) => (b.vua - a.vua) || (b.so_hang - a.so_hang) || (a.ti_le - b.ti_le));
  return ra;
}"""

# Cuộn phần tử vào tầm nhìn rồi đo TẤT CẢ theo viewport.
_JS_CUON_DO = _JS_NORM + """
([cach, dau, k]) => {
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
  return {vung: vung(t), bang: rect(t), rows: rows.map(rect), sticky: st};
}"""

# `cuon=true`: tim nhan SVG mang ten model trong mot chart du lon roi cuon toi;
# `false`: do lai chinh nhan do sau khi cuon.
_JS_SVG = _JS_NORM + """
([models, cuon]) => {
  for (const model of models) {
    const nm = norm(model);
    for (const t of document.querySelectorAll('svg text, svg tspan')) {
      if (!norm(t.textContent).includes(nm) || t.getBoundingClientRect().width <= 0) continue;
      const s = t.closest('svg'); if (!s) continue;
      const sb = s.getBoundingClientRect();
      if (sb.width < 500 || sb.height < 250) continue;
      if (cuon) { s.scrollIntoView({block: 'center'});
                  return {model, dong: (t.textContent||'').trim().slice(0,80)}; }
      return {svg: rect(s), nhan: rect(t), vung: vung(s)};
    }
  }
  return null;
}"""


def _doi_bang(page):
    """Đợi trang render xong bảng (≥5 hàng hiện) hoặc SVG lớn, tối đa 14s, rồi
    thêm 1.2s cho font/logo. Chờ cố định 6s là đánh bạc: arena text-to-video có
    lúc chưa ra hàng nào ở giây thứ 6."""
    page.wait_for_timeout(1500)
    t0 = time.time()
    while time.time() - t0 < 14:
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


def _cua_so(rows: list, idx: int, hdr_h: float) -> tuple:
    """[dau, cuoi] hàng đưa vào ảnh: trong top → từ hàng 1, sâu → từ idx-2, rồi
    kéo xuống hết CAO_TOI_DA_CSS. Ông Chủ 06/09/2026: "chụp full chiều dài cũng
    chả vấn đề" — càng nhiều hàng quanh model càng tốt, chỉ chặn ở trần vì thẻ
    cao bấy nhiêu, chụp thêm cũng bị cắt."""
    n = len(rows)
    dau = 1 if idx <= TOP_MAC_DINH + 2 else max(1, idx - TREN_MODEL)
    cuoi = min(n - 1, max(idx + 2, dau + TOP_MAC_DINH - 1))
    cao = lambda k: rows[k]["y"] + rows[k]["h"] - rows[dau]["y"] + hdr_h
    while cuoi + 1 < n and cao(cuoi + 1) <= CAO_TOI_DA_CSS:
        cuoi += 1
    while cuoi > idx + 1 and cao(cuoi) > CAO_TOI_DA_CSS:
        cuoi -= 1
    return dau, cuoi


def _chup_mot_bang(page, tim: dict, out: Path):
    """Chụp cửa sổ top-N của MỘT bảng (đã đánh dấu k), khoanh hàng model."""
    idx, k = tim["idx"], tim["k"]
    out.parent.mkdir(parents=True, exist_ok=True)
    # Lượt 1: cuộn header lên đầu (trường hợp top) hoặc hàng model vào giữa (sâu), đo.
    trong_top = idx <= TOP_MAC_DINH + 2
    do = page.evaluate(_JS_CUON_DO, ["top" if trong_top else "row", idx, k])
    page.wait_for_timeout(400)
    do = page.evaluate(_JS_CUON_DO, ["top" if trong_top else "row", idx, k])
    rows, vung, hdr = do["rows"], do["vung"], do["rows"][0]
    st = do.get("sticky")
    hdr_h = max(hdr["h"], (st["bot"] - st["top"]) if st else 0)
    dau, cuoi = _cua_so(rows, idx, hdr_h)
    x, w = do["bang"]["x"], do["bang"]["w"]
    # Hàng nào nằm dưới vùng DÍNH (header sticky, có thể nhiều tầng) hoặc ngoài
    # vùng nhìn thì bỏ khỏi band — không chụp cái không hiện.
    duoi_hdr = max(hdr["y"] + hdr["h"] if hdr["y"] >= vung["y"] - 1 else vung["y"],
                   st["bot"] if st else -1)
    hien = [k for k in range(dau, cuoi + 1)
            if rows[k]["y"] >= duoi_hdr - 1 and rows[k]["y"] + rows[k]["h"] <= vung["y"] + vung["h"] + 1]
    if idx not in hien:
        # Hang model bi che (header dinh cao / cuon lech): thu cach 'row' — hang dau
        # cua so len dau viewport, lui mot header.
        do = page.evaluate(_JS_CUON_DO, ["row", dau, k]); page.wait_for_timeout(300)
        do = page.evaluate(_JS_CUON_DO, ["row", dau, k])
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
        do2 = page.evaluate(_JS_CUON_DO, ["top", 0, k]); page.wait_for_timeout(300)
        do2 = page.evaluate(_JS_CUON_DO, ["top", 0, k])
        h2 = do2["rows"][0]
        _chup(page, _giao({"x": x, "w": w, "y": h2["y"], "h": h2["h"]}, do2["vung"]), p1)
        a, b = Image.open(p1).convert("RGB"), Image.open(p2).convert("RGB")
        g = Image.new("RGB", (max(a.width, b.width), a.height + b.height), (255, 255, 255))
        g.paste(a, (0, 0)); g.paste(b, (0, a.height)); g.save(out, "PNG"); p1.unlink(); p2.unlink()
        goc = (max(0, max(band["x"], vung["x"]) - 8), max(band["y"], vung["y"])); do_hdr = a.height / DPR
    row = rows[idx]
    _khoanh(out, row["x"] - goc[0], row["y"] - goc[1] + do_hdr, min(row["w"], w), row["h"])
    return {"kieu": "bang", "model": tim["model"], "hang": tim["hang"], "dong": tim["dong"],
            "logo_co": tim["logo"]}, ""


def chup_bang(page, models: list, out: Path):
    """Chụp bảng chứa model, chọn bảng VỪA KHỔ nhất trang. Thử tối đa 3 bảng theo
    thứ tự vừa khổ → nhiều hàng → hẹp, lấy bảng đầu ra rộng/cao ≤ TI_LE_VUA.
    Vẫn quá ngang thì thu hẹp cửa sổ trình duyệt cho bảng tự dồn cột (tbench ra
    3.2 nếu không làm)."""
    ung = page.evaluate(_JS_TIM, [models, CAO_TOI_DA_CSS, TI_LE_VUA])
    if not ung:
        return None, "không có bảng ≥5 hàng chứa tên model"
    da, ly_do = [], []
    for tim in ung[:3]:
        p = out if not da else out.with_suffix(f".b{len(da)}.png")
        try:
            kq, ld = _chup_mot_bang(page, tim, p)
        except Exception as e:                               # noqa: BLE001
            kq, ld = None, f"{type(e).__name__}: {str(e)[:60]}"
        if not kq:
            ly_do.append(f"bảng {tim['k']} ({tim['so_hang']} hàng): {ld}")
            continue
        with Image.open(p) as im:
            r = im.width / im.height
        da.append((kq, p, r, tim))
        if r <= TI_LE_VUA:
            break
    if not da:
        return None, "; ".join(ly_do)
    da.sort(key=lambda t: t[2])
    kq, p, r, tim = da[0]
    if r > TI_LE_VUA and len(da) < 2:
        # Trang chi co MOT bang va no qua ngang (tbench: 15 hang trai 2319px o viewport
        # 2400): bang responsive tra rong theo cua so. Thu hep cua so — bang tu don
        # cot, van du noi dung, chi bo cuc hep lai. Lay ban dau tien vua kho.
        rong_cu = page.viewport_size["width"]
        for rong in (1500, 1200, 1000):
            page.set_viewport_size({"width": rong, "height": page.viewport_size["height"]})
            page.wait_for_timeout(700)
            p2 = out.with_suffix(f".w{rong}.png")
            try:
                kq2, _ = _chup_mot_bang(page, tim, p2)
            except Exception:                                # noqa: BLE001
                kq2 = None
            if not kq2:
                continue
            with Image.open(p2) as im2:
                r2 = im2.width / im2.height
            if r2 < r:
                if p != out:
                    p.unlink(missing_ok=True)     # ban hep hon truoc do, khong con dung toi
                da = [(kq2, p2, r2, tim)]
                kq, p, r = kq2, p2, r2
            else:
                p2.unlink(missing_ok=True)
            if r <= TI_LE_VUA:
                break
        page.set_viewport_size({"width": rong_cu, "height": page.viewport_size["height"]})
    if r > TI_LE_VUA and len(da) >= 2:
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
    return kq, ""


# ---- Chụp DANH SÁCH MOBILE (arena.ai: div-list, không phải <table>) -----------
# arena.ai có giao diện mobile riêng: danh sách <div> hàng-thẻ, mỗi hàng full-width
# 380px cho màn 414px. Ba site còn lại (tbench/swebench/aa) KHÔNG có — bảng của
# chúng giữ nguyên bề ngang trong khung cuộn ngang, vào viewport hẹp chỉ thấy lát
# cắt bên trái, nên chúng đi đường desktop.
#
# Hai cái khó riêng ở đây:
#   1. Danh sách chỉ hiện ~11-12 mục đầu và KHÔNG tải thêm khi cuộn — đã thử cả
#      `.scrollTop` lẫn `mouse.wheel()` thật, chờ tới 3.6s mỗi lần, nội dung không
#      đổi. (Có ô tìm kiếm riêng để nhảy tới model sâu, nhưng lái nó qua Playwright
#      không ổn định giữa các lần tải.) Nên: model không có trong danh sách đầu thì
#      trả None, `tim_va_chup` rơi về bảng desktop — tìm được ở bất kỳ hạng nào.
#   2. Không có thẻ ngữ nghĩa (không <tr>, không role=row), chỉ là <div> + class
#      Tailwind. Nhận diện TỔNG QUÁT (nhóm anh em cùng cha cùng chuỗi class, >=5
#      phần tử, kích thước dạng một hàng) thay vì khoá cứng một chuỗi class — đo
#      đúng trên cả arena-code lẫn arena-text, hai giao diện hơi khác nhau.
_JS_NORM_DS = """
const norm = s => (s||'').toLowerCase().replace(/[\\s\\-_.]+/g,'');
const rect = el => { const r = el.getBoundingClientRect(); return {x:r.x,y:r.y,w:r.width,h:r.height}; };
const timDanhSach = (models) => {
  const chuaModel = els => {
    if (!models || !models.length) return false;
    const t = norm(els.map(e => e.textContent || '').join(' '));
    return models.some(m => t.includes(norm(m)));
  };
  const groups = new Map();
  // div/li/a: openrouter dung <ol><li>, arena dung <div> — quet ca ba, dung khoa
  // cung mot loai the.
  document.querySelectorAll('div,li,a').forEach(el => {
    const p = el.parentElement; if (!p) return;
    if (!groups.has(p)) groups.set(p, new Map());
    const m = groups.get(p);
    const kk = el.tagName + '|' + (el.className||'').toString().trim();
    if (!m.has(kk)) m.set(kk, []);
    m.get(kk).push(el);
  });
  let best = null;
  for (const [, m] of groups) {
    for (const [, els] of m) {
      if (els.length < 5) continue;
      const r0 = els[0].getBoundingClientRect();
      if (r0.width < 200 || r0.width > 500 || r0.height < 25 || r0.height > 120) continue;
      // Hang phai CO CHU. openrouter co dung 10 <div class="flex flex-col"> rong
      // lam khung bo cuc, dung kich thuoc hang that -> khong loc thi vo nham
      // chung roi bao "khong thay model".
      if (els.filter(e => (e.textContent||'').trim().length > 2).length < 5) continue;
      // Nhom CHUA MODEL luon thang nhom dong hon: openrouter co thanh dieu huong
      // 12 muc dung dang mot hang, con cot xep hang that chi 5 hang.
      const diem = [chuaModel(els) ? 1 : 0, els.length];
      if (!best || diem[0] > best.diem[0] || (diem[0] === best.diem[0] && diem[1] > best.diem[1]))
        best = Object.assign(els, {diem});
    }
  }
  return best;
};
// Moi nhom CUNG DANG voi nhom tot nhat (cung tag+class, khac cha) — openrouter
// chia top-10 thanh hai <ol> canh nhau, moi cot 5 hang.
const nhomCungDang = (models) => {
  const best = timDanhSach(models); if (!best) return [];
  const dau = best[0];
  const chuKy = dau.tagName + '|' + (dau.className||'').toString().trim();
  const theoCha = new Map();
  for (const e of document.querySelectorAll(dau.tagName)) {
    if (e.tagName + '|' + (e.className||'').toString().trim() !== chuKy) continue;
    const r = e.getBoundingClientRect();
    if (r.height < 10) continue;
    const p = e.parentElement; if (!p) continue;
    if (!theoCha.has(p)) theoCha.set(p, []);
    theoCha.get(p).push(e);
  }
  return [...theoCha.values()].filter(v => v.length >= 3)
    .sort((a, b) => { const ra = a[0].getBoundingClientRect(), rb = b[0].getBoundingClientRect();
                      return (ra.y - rb.y) || (ra.x - rb.x); });
};
const khungCuonDs = el => { for (let e = el; e; e = e.parentElement) {
  const cs = getComputedStyle(e);
  if (/(auto|scroll)/.test(cs.overflowY) && e.scrollHeight > e.clientHeight + 4) return e; }
  return null; };
"""

# `cuon=true`: dua hang model vao giua khung nhin roi do; `false`: chi do lai.
# `cot`: -1 = nhom chua model; >=0 = nhom thu may trong cac nhom CUNG DANG (dung
# de lay not cac cot con lai roi ghep doc, xem `chup_danh_sach`).
_JS_DS = _JS_NORM_DS + """
([models, cuon, cot]) => {
  const els = cot >= 0 ? (nhomCungDang(models)[cot] || null) : timDanhSach(models);
  if (!els) return null;
  let idx = -1, model = null;
  for (const m of models) {
    const nm = norm(m);
    idx = els.findIndex(e => norm(e.innerText || e.textContent).includes(nm));
    if (idx >= 0) { model = m; break; }
  }
  // Cot duoc goi DICH DANH (cot >= 0) thi khong doi phai co model: do la cac cot
  // con lai cua cung mot bang, lay tron de ghep doc.
  if (idx < 0) { if (cot < 0) return null; idx = 0; }
  if (cuon) { els[idx].scrollIntoView({block: 'center'}); return {cuon_roi: true}; }
  const cells = (els[idx].innerText || '').trim().split('\\n').map(s => s.trim()).filter(Boolean);
  const hang = (cells.find(c => /^#?\\d{1,3}$/.test(c)) || '').replace('#', '');
  const kc = khungCuonDs(els[0]);
  const r = kc ? kc.getBoundingClientRect() : {x:0, y:0, width:window.innerWidth, height:window.innerHeight};
  return {idx, model, hang: hang ? parseInt(hang, 10) : null,
          dong: cells.join(' | ').slice(0, 160), rows: els.map(rect),
          vung: {x: Math.max(0,r.x), y: Math.max(0,r.y),
                 w: Math.min(window.innerWidth, r.x+r.width) - Math.max(0,r.x),
                 h: Math.min(window.innerHeight, r.y+r.height) - Math.max(0,r.y)}};
}
"""


def _chup_mot_cot(page, models: list, out: Path, dpr: int, cot: int = -1):
    """Chụp một cột danh sách: `cot=-1` là cột chứa model (và khoanh hàng model),
    `cot>=0` là cột thứ N trong các cột cùng dạng (chụp trọn, không khoanh).
    Trả về `(thong_tin, ly_do)`."""
    do = page.evaluate(_JS_DS, [models, False, cot])
    if not do:
        return None, "mất dấu danh sách"
    idx, rows, vung = do["idx"], do["rows"], do["vung"]
    dau = 0 if idx <= TOP_MAC_DINH else max(0, idx - TREN_MODEL)
    cuoi = idx if cot < 0 else len(rows) - 1
    cao = lambda k: rows[k]["y"] + rows[k]["h"] - rows[dau]["y"]
    while cuoi + 1 < len(rows) and cao(cuoi + 1) <= CAO_TOI_DA_CSS:
        cuoi += 1
    hien = [k for k in range(dau, cuoi + 1)
            if rows[k]["y"] >= vung["y"] - 1 and rows[k]["y"] + rows[k]["h"] <= vung["y"] + vung["h"] + 1]
    if not hien or (cot < 0 and idx not in hien):
        return None, f"hàng model không nằm trong vùng nhìn ({len(hien)}/{cuoi-dau+1} hàng hiện)"
    dau, cuoi = hien[0], hien[-1]
    out.parent.mkdir(parents=True, exist_ok=True)
    r = _giao({"x": rows[dau]["x"], "w": rows[dau]["w"], "y": rows[dau]["y"],
               "h": rows[cuoi]["y"] + rows[cuoi]["h"] - rows[dau]["y"]}, vung)
    _chup(page, r, out)
    if cot < 0:
        row = rows[idx]
        _khoanh(out, row["x"] - r["x"], row["y"] - r["y"], row["w"], row["h"], dpr)
    return {"model": do["model"], "hang": do["hang"], "dong": do["dong"]}, ""


def chup_danh_sach(page, models: list, out: Path, dpr: int = DPR):
    """Danh sách hàng-thẻ (`<div>`/`<li>`) thay cho `<table>`: arena.ai ở khung
    mobile, openrouter.ai ở khung desktop.

    Chụp dải hàng quanh model, khoanh hàng model. Cột quá ngang mà trang còn cột
    CÙNG DẠNG (openrouter dàn top-10 thành hai `<ol>` 5 hàng cạnh nhau, một cột
    rộng/cao ~1.75) thì GHÉP DỌC các cột lại — cùng một cách `chup_bang` ghép hai
    bảng, để ra khối dọc vừa khổ hero thay vì dải ngang."""
    # Doi danh sach render xong, giong `_doi_bang` cua duong desktop: openrouter
    # dung hang ~3s moi co CHU trong hang (do co hang rong truoc do), 800ms cua
    # `tim_va_chup` la khong du. Poll thay vi cho cung mot con so.
    t0 = time.time()
    while time.time() - t0 < 12:
        if page.evaluate(_JS_DS, [models, True]):
            break
        page.wait_for_timeout(700)
    else:
        return None, "không có model nào trong danh sách đang hiển thị"
    page.wait_for_timeout(350)
    kq, ly_do = _chup_mot_cot(page, models, out, dpr)
    if not kq:
        return None, ly_do
    with Image.open(out) as im:
        r = im.width / im.height
    so_cot = page.evaluate(_JS_NORM_DS + "(models) => nhomCungDang(models).length", models)
    if r <= TI_LE_VUA or so_cot < 2:
        return {"kieu": "danh-sach", **kq, "logo_co": False}, ""
    # Qua ngang + con cot cung dang: ghep doc theo dung thu tu tren trang.
    cot_model = page.evaluate(_JS_NORM_DS + """
        (models) => { const b = timDanhSach(models);
                      return nhomCungDang(models).findIndex(g => g[0] === b[0]); }""", models)
    manh, tam = [], []
    for i in range(so_cot):
        if i == cot_model:
            manh.append(out)
            continue
        p = out.with_suffix(f".c{i}.png")
        k2, _ = _chup_mot_cot(page, models, p, dpr, cot=i)
        if k2:
            manh.append(p); tam.append(p)
    if len(manh) < 2:
        return {"kieu": "danh-sach", **kq, "logo_co": False}, ""
    ims = [Image.open(p).convert("RGB") for p in manh]
    rong = max(i.width for i in ims)
    ims = [i if i.width == rong else i.resize((rong, round(i.height * rong / i.width)), Image.LANCZOS)
           for i in ims]
    g = Image.new("RGB", (rong, sum(i.height for i in ims)), (255, 255, 255))
    y = 0
    for i in ims:
        g.paste(i, (0, y)); y += i.height
    for i in ims:
        i.close()
    g.save(out, "PNG")
    for p in tam:
        p.unlink(missing_ok=True)
    return {"kieu": "danh-sach-ghep", **kq, "logo_co": False}, ""



def chup_svg(page, models: list, out: Path):
    tim = page.evaluate(_JS_SVG, [models, True])
    if not tim:
        return None, "không có nhãn SVG chứa tên model"
    page.wait_for_timeout(400)
    do = page.evaluate(_JS_SVG, [models, False])
    if not do:
        return None, "nhãn SVG mất sau khi cuộn"
    out.parent.mkdir(parents=True, exist_ok=True)
    s = do["svg"]
    r = _giao({"x": s["x"], "y": s["y"], "w": s["w"], "h": min(s["h"], CAO_TOI_DA_CSS)}, do["vung"])
    _chup(page, r, out)
    n = do["nhan"]
    _khoanh(out, n["x"] - r["x"], n["y"] - r["y"], n["w"], n["h"])
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


# ---- Thẻ dự phòng: tên model + #hạng + logo + site ------------------------------
def the_du_phong(model: str, hang, site: str, bang: str, out: Path, brand: str = "donniechublog",
                 logo: Path | None = None) -> Path:
    """Khi không nguồn nào chụp được. Không phải minh hoạ — là một THẺ DỮ LIỆU:
    đúng bốn thứ Ông Chủ chốt, không thêm gì. Nội dung dồn lên NỬA TRÊN có chủ ý:
    thẻ này là `--image` của card.py, hook sẽ đè lên nửa dưới qua màn tối."""
    import card
    w, h = 1200, 1500
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
    while d.textlength(model, font=f_ten_dung) > w - 160 and f_ten_dung.size > 44:
        f_ten_dung = card._f(card.F_QUOTE, f_ten_dung.size - 6)
    y = giua(model, f_ten_dung, y, card.FG) + 44
    d.line([(w // 2 - 60, y), (w // 2 + 60, y)], fill=card.CYAN, width=4)
    y += 44
    giua(f"trên bảng xếp hạng {bang}", f_phu, y, card.MUTED)
    handle = b["handle"]
    d.text((w // 2 - d.textlength(handle, font=f_nho) / 2, h - 110), handle, font=f_nho, fill=card.MUTED)
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PNG")
    luat_anh.dong_dau_tep(out, "the_xep_hang", model=model, hang=hang, nguon=site, bang=bang)
    return out


# ---- Điều phối --------------------------------------------------------------------
def tim_va_chup(models: list, nguon_ds: list, out_dir: Path, brand: str = "donniechublog",
                hang_goi_y=None, in_log=print) -> dict:
    """Đi qua từng nguồn, nguồn nào ra ảnh khoanh được model thì dừng; không nguồn
    nào ra thì dựng thẻ dự phòng. Luôn trả về dict mô tả ảnh (tep, kieu, nguon,
    site, bang, hang, model, url). `models` phải khác rỗng."""
    from playwright.sync_api import sync_playwright
    t0 = time.time()
    logo = None
    kq_cuoi = None
    with sync_playwright() as p:
        br = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage", "--force-color-profile=srgb"])
        # Viewport cao san bang tran cua so chup: khong doi kich thuoc giua chung
        # (doi la trang reflow, bbox do truoc do lech). HAI bo context: mobile
        # cho nguon co co "mobile" (arena.ai — chu von to san cho man 414px, gan
        # nhu khong bi co lai khi vao the 1200px, khac han desktop phai co gan
        # mot nua), desktop cho phan con lai. Tao LAZY, dung lai giua cac nguon
        # cung loai — khong tao lai context moi lan.
        ctx_desktop = ctx_mobile = pg_desktop = pg_mobile = None

        def trang_desktop():
            nonlocal ctx_desktop, pg_desktop
            if ctx_desktop is None:
                ctx_desktop = br.new_context(viewport={"width": 2400, "height": CAO_TOI_DA_CSS + 250},
                                             device_scale_factor=DPR, user_agent=UA)
                pg_desktop = ctx_desktop.new_page()
            return pg_desktop

        def chup_desktop(pg, url=None):
            """Đường bảng desktop: bảng trước, không có thì chart SVG."""
            if url:
                pg.goto(url, wait_until="domcontentloaded", timeout=40000)
                pg.wait_for_timeout(800)
            _doi_bang(pg)
            kq, ly_do = chup_bang(pg, models, out)
            if kq:
                return kq, ly_do
            # Khong phai <table>: thu danh sach hang-the (openrouter dung <ol><li>).
            kq2, ly_do2 = chup_danh_sach(pg, models, out, DPR)
            if kq2:
                return kq2, ly_do2
            kq3, ly_do3 = chup_svg(pg, models, out)
            return kq3, f"bảng: {ly_do}; danh sách: {ly_do2}; svg: {ly_do3}"

        for n in nguon_ds:
            di_dong = bool(n.get("mobile"))
            if di_dong:
                if ctx_mobile is None:
                    ctx_mobile = br.new_context(viewport=MOBILE_VIEWPORT, device_scale_factor=MOBILE_DPR,
                                                is_mobile=True, has_touch=True, user_agent=MOBILE_UA)
                    pg_mobile = ctx_mobile.new_page()
                pg = pg_mobile
            else:
                pg = trang_desktop()
            if time.time() - t0 > GIO_HAN:
                in_log(f"[xep_hang] hết giờ ({GIO_HAN}s), dừng ở {n['ma']}")
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
                if di_dong:
                    kq, ly_do = chup_danh_sach(pg, models, out, MOBILE_DPR)
                    if not kq:
                        # Model ngoai ~11-12 muc dau cua danh sach mobile: mo lai chinh
                        # nguon nay o khung desktop, bang <table> tim duoc moi hang.
                        # Chu se nho hon vi anh desktop phai co ve kho the, nhung con
                        # hon khong co anh.
                        kq, ly_do2 = chup_desktop(trang_desktop(), n["url"])
                        ly_do = f"mobile: {ly_do}; desktop: {ly_do2}"
                else:
                    kq, ly_do = chup_desktop(pg)
            except Exception as e:                           # noqa: BLE001
                in_log(f"[xep_hang] {n['ma']}: {type(e).__name__}: {str(e)[:80]}")
                continue
            if not kq:
                # Khop duoc hang nhung khong chup noi bang: van vot lay logo model
                # tu chinh hang do cho THE DU PHONG (duong duy nhat the do chay toi).
                if logo is None:
                    logo = chup_logo(pg, out_dir / "xep_hang_logo.png")
                in_log(f"[xep_hang] {n['ma']}: bỏ — {ly_do}")
                continue
            luat_anh.dong_dau_tep(out, "chup_xep_hang", model=kq["model"], nguon=n["ma"],
                                  site=n["site"], bang=n["bang"], hang=kq.get("hang"), url=n["url"])
            im = Image.open(out)
            in_log(f"[xep_hang] {n['ma']}: khớp {kq['model']!r} hàng #{kq.get('hang') or '?'} "
                   f"({kq['kieu']}, {im.width}x{im.height}) — {kq['dong'][:70]}")
            kq_cuoi = {"tep": str(out), "kieu": kq["kieu"], "nguon": n["ma"], "site": n["site"],
                       "bang": n["bang"], "hang": kq.get("hang") or hang_goi_y, "model": kq["model"],
                       "url": n["url"], "dong": kq["dong"], "logo": str(logo) if logo else None,
                       "duoc_nhac": bool(n.get("duoc_nhac", True))}
            break
        br.close()  # dong browser cung dong het cac context/page con lai
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
