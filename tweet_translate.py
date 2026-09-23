#!/usr/bin/env python3
"""tweet_translate.py — chụp lại một tweet với phần chữ đã dịch sang tiếng Việt.

KHÔNG OCR, KHÔNG xoá chữ, KHÔNG vẽ lại thẻ. Mở đúng thẻ nhúng CÔNG KHAI của X
(`platform.twitter.com/embed/Tweet.html`), THAY thẳng nội dung chữ trong DOM
bằng bản dịch, rồi chụp. Trình duyệt tự xuống dòng, nên câu tiếng Việt dài hơn
câu gốc ~25% vẫn nằm gọn trong thẻ — không phải đo cỡ chữ, chọn font, đo màu
hay nới mask như tuyến `swap_image_text` (Gin/Itachi). Toàn bộ danh sách bẫy
trong `hermes/skills/inplace-translate/SKILL.md` không áp vào đường này.

Vì sao là thẻ NHÚNG chứ không phải x.com: x.com đòi đăng nhập và
`browser_session` không nạp cookie/storage_state nào cho X, nên chụp thẳng
`x.com/<ai>/status/<id>` chỉ ra tường đăng nhập. Thẻ nhúng đọc được mà không
cần đăng nhập — đo thật 23/09/2026 (tweet id 20, ra đủ avatar, tick, logo X,
metrics, nút "Đọc N trả lời").

Ảnh đính kèm trong tweet GIỮ NGUYÊN (Ông Chủ 23/09/2026: *"để nguyên hình gốc,
ko dịch text trên hình"*). Chữ tiếng Anh nằm TRÊN tấm ảnh đó là việc của
Gin/Itachi, không phải của script này.

Khung chụp là khung MOBILE dùng chung của đội (`browser_session.MOBILE_*`,
414px × DPR 3 = 1242px) — cùng một bản với `capture_page`, không chép số riêng.

Một lệnh, MÁY DỊCH bằng Grok (`env_load.TRANSLATE_MODEL`):

    venv/bin/python tweet_translate.py "<link>" --out tweet.png

Bản dịch máy in ra stderr để người duyệt. Muốn bản của mình thì `--vi`, nó
thắng tuyệt đối; `--brief` chỉ in nguyên văn tweet rồi dừng.

Vì sao Grok: Ông Chủ 23/09/2026 — *"hiểu twitter nhất chắc chắn là grok"*. Đo
thật cùng ngày trên một tweet đầy tiếng lóng, các bản rẻ hơn đều hỏng theo cách
riêng (grok-3 bỏ nguyên hai dòng không dịch, grok-4 gộp đoạn); số đo trong
`env_load.TRANSLATE_MODEL`.

Mặc định thẻ ra đã được tỉa: bỏ cả hàng trái tim / "Trả lời" / "Sao chép liên
kết đến bài đăng" lẫn khối "Đọc N trả lời" — ảnh đăng lên kênh mình thì không
ai bấm được. Thẻ kết thúc ngay sau dòng ngày. `--clean` sạch hơn nữa: bỏ luôn
nút Theo dõi và icon ⓘ, chỉ còn avatar-tên-tick-chữ-ngày.

Trong bản dịch, bọc cụm cần NHẤN MÀU bằng `<hl>…</hl>`:

    Qwen3.8 Flash <hl>miễn phí</hl> trong một tuần.

Màu nhấn chọn theo id tweet từ bảng màu thương hiệu của X, để các ảnh không ra
cùng một màu (Ông Chủ 23/09/2026); `--hl-color` ép một màu cụ thể.

Ảnh ra đưa tiếp cho Bob đóng khung + mascot + handle:

    venv/bin/python image_frame.py --image tweet.png --emoji "🤖" --out framed.png
"""
import argparse
import contextlib
import html
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import env_load                                              # noqa: E402
import image_provenance                                      # noqa: E402
import vietnamese                                            # noqa: E402
from browser_session import (MOBILE_DPR, MOBILE_UA,          # noqa: E402
                            MOBILE_VIEWPORT, session_or_new)

EMBED = "https://platform.twitter.com/embed/Tweet.html"
# MÀU NHẤN — một bảng, không phải một màu (Ông Chủ 23/09/2026: *"đừng để các màu
# giống nhau ở mọi hình"*). Lấy đúng bộ màu thương hiệu của X, nên cụm được nhấn
# nhìn ra "một phần của thẻ" thay vì chữ dán lên.
#
# Chọn theo id tweet: TẤT ĐỊNH (chạy lại cùng một tweet ra đúng màu cũ, dựng lại
# ảnh không bị đổi màu giữa chừng) mà vẫn rải đều giữa các bài. Ép màu cụ thể
# bằng `--hl-color`.
HL_DARK = {
    "red": "#f4212e", "blue": "#1d9bf0", "green": "#00ba7c",
    "yellow": "#ffd400", "pink": "#f91880", "purple": "#8c6bff",
    "orange": "#ff7a00",
}
# Nền sáng cần tông đậm hơn: vàng #ffd400 trên nền trắng gần như không đọc được,
# nên bảng này bỏ vàng và kéo mọi mã xuống tối hơn.
HL_LIGHT = {
    "red": "#d81b25", "blue": "#0f7cc0", "green": "#00875a",
    "pink": "#c9146a", "purple": "#5b3fd1", "orange": "#c25b00",
}
_HEX = re.compile(r"#[0-9a-fA-F]{6}\Z")
# Node chữ của thẻ nhúng. Tên do X đặt và X có thể đổi bất cứ lúc nào — không
# thấy thì DỪNG, đừng chụp bừa: ảnh ra khi đó là tweet tiếng Anh nguyên vẹn,
# nhìn vẫn "đẹp" nên rất dễ lọt tới bước đăng.
SEL_TEXT = '[data-testid="tweetText"]'
SEL_CARD = ('[data-testid="tweet"]', "article")
TIME_LIMIT = 45000
WAIT_LAYOUT = 900          # ms cho font/ảnh nhúng ổn định trước khi chụp
IMAGE_TRY = 8              # số lần đợi ảnh đính kèm tải xong

_STATUS = re.compile(r"(?:x|twitter)\.com/[^/]+/status(?:es)?/(\d{5,25})", re.I)

# Tweet DÀI bị thẻ nhúng cắt: chữ dừng giữa chừng và đính thêm một span "Hiển thị
# thêm" NGAY TRONG node chữ. Đo 23/09/2026 trên arena/2102497076831818113 — thẻ
# chỉ trả 293 ký tự, và bấm vào span đó KHÔNG mở rộng (293 trước, 293 sau), tức
# phần còn lại không nằm trong DOM. `social_fetch` qua crawl-queue cắt đúng chỗ
# ấy, nên không có nguồn nào trong đội lấy được toàn văn — người dịch phải tự mở
# link. Ở đây chỉ làm một việc: NÓI RA, thay vì lặng lẽ đưa bản cụt đi dịch.
#
# Bám chữ chứ không bám tên node (X không đặt data-testid cho span này trong thẻ
# nhúng). X đổi chữ thì mất cảnh báo — không ra ảnh sai, vì bản dịch vẫn là chữ
# người viết đưa vào.
SHOW_MORE = ("hiển thị thêm", "xem thêm", "show more")


def cut_show_more(t: str) -> tuple:
    """(chữ đã bỏ nhãn 'Hiển thị thêm', tweet có bị cắt không)."""
    s = (t or "").rstrip()
    for nhan in SHOW_MORE:
        if s.lower().endswith(nhan):
            return (s[: -len(nhan)].rstrip(), True)
    return (s, False)

# MẶC ĐỊNH bỏ hết phần tương tác ở chân thẻ (Ông Chủ 23/09/2026): hàng trái tim
# / "Trả lời" / "Sao chép liên kết đến bài đăng", và khối "Đọc N trả lời". Chúng
# là lời mời bấm, mà ảnh đăng lên kênh mình thì không bấm được. Thẻ kết thúc
# ngay sau dòng ngày.
#
# Bám CẤU TRÚC chứ không bám chữ: chữ đổi theo `--lang` và theo bề ngang thẻ
# ("Sao liên kết" / "Sao chép liên kết đến bài đăng").
#
# Hàng nút phải xét TRƯỚC: con đầu của nó cũng là một `a[role="link"]` có chữ
# (số lượt thích), nên nhánh dưới chạy trước sẽ chộp nhầm nó.
_JS_TRIM = """
() => {
  const root = document.querySelector('article');
  if (!root) return 0;
  let n = 0;
  const hide = el => { if (el && el.style.display !== 'none') { el.style.display = 'none'; n++; } };
  const kids = [...root.children];
  const iText = kids.findIndex(c => c.querySelector('[data-testid="tweetText"]'));
  kids.forEach((c, i) => {
    if (i <= iText) return;
    if (c.querySelector('[role="button"]')) { hide(c); return; }
    const a = c.querySelector('a[role="link"]');
    if (a && (a.innerText || '').trim() && !/\\d{4}/.test(c.innerText || '')) hide(c);
  });
  return n;
}
"""

# Ẩn phần điều khiển khi có `--clean` — giữ avatar, tên, handle, tick, logo X,
# ảnh đính kèm và ngày, vì đó là thứ chứng minh tweet này của ai.
#
# Đi theo CẤU TRÚC chứ không theo tên lớp: `<article>` của thẻ nhúng có các con
# trực tiếp xếp phẳng theo thứ tự header → chữ → (ảnh) → ngày → hàng nút →
# "Đọc N trả lời" (đọc DOM thật 23/09/2026). Mốc là khối chứa `tweetText`; mọi
# thứ TRƯỚC nó giữ nguyên, sau nó chỉ ẩn khối có nút bấm hoặc khối chỉ là một
# liên kết có chữ. Tên lớp của X đổi liên tục, thứ tự này thì không.
#
# Hỏng selector ở đây chỉ làm ảnh thừa vài nút — không ra ảnh sai ngôn ngữ, nên
# không cần chặn cứng như `SEL_TEXT`.
_JS_CLEAN = """
() => {
  const art = document.querySelector('article');
  if (!art) return 0;
  let n = 0;
  const hide = el => { if (el && el.style.display !== 'none') { el.style.display = 'none'; n++; } };
  const kids = [...art.children];
  const iText = kids.findIndex(c => c.querySelector('[data-testid="tweetText"]'));
  kids.forEach((c, i) => {
    if (i <= iText) return;
    if (c.querySelector('[role="button"]')) { hide(c); return; }
    const a = c.querySelector('a[role="link"]');
    if (a && (a.innerText || '').trim() && !/\\d{4}/.test(c.innerText || '')) hide(c);
  });
  art.querySelectorAll('a[href*="/intent/"]').forEach(hide);
  // Dấu chấm giữa còn trơ lại sau khi ẩn nút "Theo dõi". Dòng ngày cũng có một
  // dấu như vậy nhưng nằm chung một span với cả chuỗi, nên không dính.
  art.querySelectorAll('span').forEach(s => {
    if ((s.textContent || '').trim() === '\\u00b7') hide(s);
  });
  // Icon ⓘ ở dòng ngày. CHỈ link không có chữ: cả dòng ngày cũng là một
  // `a[role="link"]` (đo 23/09/2026), quét cả nắm thì mất luôn ngày tháng.
  const day = kids.find((c, i) => i > iText && /\\d{4}/.test(c.innerText || ''));
  if (day) day.querySelectorAll('a[role="link"]').forEach(a => {
    if (!(a.innerText || '').trim()) hide(a);
  });
  return n;
}
"""

# Ảnh đính kèm lazy-load: chụp sớm thì ra một ô xám. Hỏi CHÍNH trình duyệt đã
# tải xong chưa, thay vì ngủ một khoảng đoán mò.
_JS_IMAGES_READY = """
() => {
  const imgs = [...document.images];
  return imgs.length === 0 || imgs.every(i => i.complete && i.naturalWidth > 0);
}
"""

# Ẩn cả khối QUOTE, không phải mỗi dòng chữ của nó.
#
# Quote có `<article>` RIÊNG lồng trong article chính (đo 23/09/2026) — leo từ
# node chữ lên `closest('article')` sẽ dừng ở article của chính quote, ẩn ra
# đúng mỗi đoạn chữ và để lại nguyên khung: avatar, tên @SpaceXAI, và tấm bảng
# tiếng Anh. Phải lấy article NGOÀI CÙNG làm mốc rồi ẩn con trực tiếp của nó.
_JS_HIDE_QUOTE = """
(n) => {
  const root = document.querySelector('article');
  if (!root) return false;
  let el = n.closest('article');
  if (!el || el === root) el = n;
  while (el.parentElement && el.parentElement !== root) el = el.parentElement;
  if (el === root || !el.parentElement) return false;
  el.style.display = 'none';
  return true;
}
"""


def tweet_id(url: str) -> str:
    """Link tweet -> id. Nhận cả id trần."""
    m = _STATUS.search(url or "")
    if m:
        return m.group(1)
    # Id trần: nhận từ 2 chữ số. Tweet thời nay 19 chữ số, nhưng tweet đời đầu
    # chỉ có hai (`20` = "just setting up my twttr") và đó là ca test tiện nhất.
    if re.fullmatch(r"\d{2,25}", (url or "").strip()):
        return url.strip()
    sys.exit(f"Không đọc được id tweet từ: {url!r} (cần dạng x.com/<ai>/status/<id>)")


def embed_url(tid: str, theme: str, lang: str) -> str:
    # `conversation=none&hideThread=true` KHÔNG phải để cho gọn — nó là điều kiện
    # ĐÚNG/SAI. Thiếu nó, thẻ nhúng dựng cả chuỗi hội thoại và node chữ ĐẦU TIÊN
    # lại là tweet CHA chứ không phải tweet của id mình đưa: đo thật 23/09/2026
    # trên `arena/status/2102497079834882494` — bản dịch bị gắn vào tweet cha,
    # ảnh ra cao 3864px với hai khối tiếng Anh chưa dịch nằm dưới.
    return (f"{EMBED}?id={tid}&theme={theme}&lang={lang}&dnt=true"
            f"&conversation=none&hideThread=true")


# Dịch tự động bằng Grok (`env_load.TRANSLATE_MODEL`). Ông Chủ 23/09/2026: *"hiểu
# twitter nhất chắc chắn là grok"* — tweet đầy tiếng lóng, viết tắt và ẩn ý của
# giới công nghệ, thứ mà một model dịch chung hay dịch phẳng ra hoặc bỏ qua.
TRANSLATE_TIMEOUT = 180
PROMPT_TRANSLATE = """Dịch tweet sau sang tiếng Việt, cho người Việt đọc tin công nghệ.

LUẬT:
- Dịch HẾT. Không để lại câu nào bằng tiếng Anh, kể cả câu đùa hay khẩu hiệu cuối bài.
- Giữ NGUYÊN tên model, tên hãng, @handle, con số, mã kỹ thuật, tên benchmark.
- Giữ ĐÚNG số đoạn và vị trí dòng trống của bản gốc.
- Tiếng lóng thì dịch sang cách nói tương đương của người Việt, đừng dịch từng chữ.
- Bọc <hl>…</hl> quanh ĐÚNG một hoặc hai cụm đáng nhấn nhất: con số đắt giá, hoặc cái mới. Không bọc cả câu.
- Chỉ trả về bản dịch. Không giải thích, không thêm dấu ngoặc kép bao ngoài.
"""
# Thêm khi thẻ nhúng đã cắt mất phần đuôi: chữ dừng giữa chừng nên mẩu cuối là
# một mảnh câu. Không dặn thì model dịch cả mảnh đó — đo thật 23/09/2026: tweet
# cụt ở "The", bản dịch ra một dòng "Cái" lơ lửng nằm chình ình trong ảnh.
PROMPT_CUT = ("- Tweet này BỊ CẮT giữa chừng. Bỏ hẳn mẩu câu dở dang ở cuối, "
              "kết thúc ở câu hoàn chỉnh cuối cùng.\n")


def translate(text: str, model=None, cut=False, verbose=True) -> str:
    """Nguyên văn tweet -> bản dịch tiếng Việt có sẵn `<hl>`. Hỏng thì thoát,
    KHÔNG trả về chữ tiếng Anh: ảnh "vietsub" mà còn nguyên tiếng Anh nhìn vẫn
    "đẹp" nên rất dễ lọt tới bước đăng."""
    env_load.load()
    model = model or env_load.TRANSLATE_MODEL
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        sys.exit("Thiếu OPENAI_API_KEY (secret.common.env) — không gọi được router để dịch. "
                 "Tự dịch rồi truyền qua --vi.")
    if verbose:
        print(f"[tweet_translate] dịch bằng {model}...", file=sys.stderr, flush=True)
    prompt = PROMPT_TRANSLATE + (PROMPT_CUT if cut else "") + "\nTWEET:\n" + text
    body = {"model": model, "max_tokens": 1500, "stream": False, "temperature": 0.3,
            "messages": [{"role": "user", "content": prompt}]}
    t0 = time.time()
    try:
        req = urllib.request.Request(
            env_load.ROUTER_URL, data=json.dumps(body).encode(),
            headers={"Content-Type": "application/json", "Authorization": "Bearer " + key})
        raw = urllib.request.urlopen(req, timeout=TRANSLATE_TIMEOUT).read().decode().strip()
        # 9router có lúc trả dạng SSE dù `stream: false` — cùng mẹo bóc như
        # article_sources._ask_same_event.
        if raw.startswith("data:"):
            raw = raw.split("data: [DONE]")[0].strip()[5:].strip()
        vi = json.loads(raw)["choices"][0]["message"]["content"]
    except Exception as e:                                   # noqa: BLE001
        ma = getattr(e, "code", "") or ""
        sys.exit(f"Dịch hỏng ({type(e).__name__}{f' {ma}' if ma else ''}) trên model "
                 f"{model!r}. Tự dịch rồi truyền qua --vi.")
    vi = (vi or "").strip().strip('"')
    if not vi:
        sys.exit(f"Model {model!r} trả về rỗng. Tự dịch rồi truyền qua --vi.")
    if verbose:
        print(f"[tweet_translate] dịch xong {time.time() - t0:.1f}s", file=sys.stderr)
    return vi


def pick_hl(tid: str, theme: str, chon=None) -> tuple:
    """(tên, mã màu) cho cụm được nhấn. `chon` = tên trong bảng hoặc mã `#rrggbb`."""
    bang = HL_LIGHT if theme == "light" else HL_DARK
    if chon:
        if _HEX.match(chon):
            return ("tự chọn", chon.lower())
        if chon in bang:
            return (chon, bang[chon])
        sys.exit(f"--hl-color không nhận {chon!r}. Dùng mã #rrggbb hoặc một trong: "
                 f"{', '.join(bang)}")
    ten = list(bang)[int(tid) % len(bang)]
    return (ten, bang[ten])


def to_html(vi: str, hl_color: str) -> str:
    """Bản dịch (chữ thường + `<hl>…</hl>`) -> HTML an toàn để gán vào thẻ.

    Escape TRƯỚC rồi mới mở lại đúng hai thẻ `<hl>`: bản dịch là chữ người viết
    chứ không phải HTML — để lọt một dấu `<` của người dịch là vỡ cả bố cục thẻ.
    """
    s = html.escape(vi)
    s = s.replace("&lt;hl&gt;", f'<span style="color:{hl_color};font-weight:700">')
    s = s.replace("&lt;/hl&gt;", "</span>")
    return s.replace("\n", "<br>")


def strip_marks(vi: str) -> str:
    """Bỏ `<hl>` để còn lại chữ thuần — dùng cho các cổng kiểm chữ."""
    return re.sub(r"</?hl>", "", vi or "")


def _card(page):
    for sel in SEL_CARD:
        el = page.query_selector(sel)
        if el and (el.bounding_box() or {}).get("height", 0) > 60:
            return el
    return None


def render(url: str, vi, out_path, theme="dark", lang="vi", clean=False,
           quote_vi=None, hide_quote=False, hl_color=None, auto=None, phien=None) -> list:
    """Mở thẻ nhúng của `url`, thay chữ bằng `vi` (None = giữ nguyên), chụp ra
    `out_path` (None = không chụp).

    Trả về danh sách nguyên văn ĐỌC ĐƯỢC trước khi thay: phần tử 0 là tweet
    chính, phần tử 1 (nếu có) là tweet được QUOTE bên trong.
    """
    out_path = Path(out_path) if out_path else None
    if out_path:
        out_path.parent.mkdir(parents=True, exist_ok=True)
    tid = tweet_id(url)
    with session_or_new(phien) as ph:
        with ph.page(viewport=MOBILE_VIEWPORT, device_scale_factor=MOBILE_DPR,
                     is_mobile=True, has_touch=True, user_agent=MOBILE_UA) as page:
            # Nói ngay là đang chờ gì. Bước này im lặng 15–30s (bật Chromium rồi
            # tải thẻ) — không báo thì nhìn như treo và người chạy bấm Ctrl+C,
            # đã xảy ra thật 23/09/2026.
            print(f"[tweet_translate] mở thẻ nhúng id {tid} — bật Chromium và tải "
                  f"thẻ, thường 15–30s...", file=sys.stderr, flush=True)
            page.goto(embed_url(tid, theme, lang), wait_until="domcontentloaded",
                      timeout=TIME_LIMIT)
            try:
                page.wait_for_selector(SEL_TEXT, timeout=TIME_LIMIT)
            except Exception:                                # noqa: BLE001
                sys.exit(f"Không thấy chữ tweet trong thẻ nhúng (id {tid}). Tweet đã xoá/khoá, "
                         f"hoặc X đã đổi tên node '{SEL_TEXT}' — kiểm tra trước khi chạy tiếp, "
                         f"đừng chụp bừa.")
            # Node 0 = tweet chính; node 1 = tweet được QUOTE lồng bên trong.
            # `conversation=none` bỏ được thread nhưng KHÔNG bỏ quote — quote là
            # một phần của chính tweet này.
            nodes = page.query_selector_all(SEL_TEXT)
            source, da_cat = [], []
            for i, n in enumerate(nodes):
                chu, bi_cat = cut_show_more(n.inner_text() or "")
                source.append(chu)
                da_cat.append(bi_cat)
                if bi_cat:
                    print(f"[tweet_translate] CẢNH BÁO: {'tweet' if i == 0 else 'quote'} dài, "
                          f"thẻ nhúng chỉ trả {len(chu)} ký tự rồi cắt. Mở link đọc phần còn "
                          f"lại trước khi dịch — bản in ra CHƯA ĐỦ.", file=sys.stderr, flush=True)
            # Tự dịch NGAY TRONG phiên trình duyệt này: `auto` (tên model, hoặc
            # True để lấy mặc định). Dịch ở ngoài thì phải mở Chromium hai lượt,
            # một lượt lấy chữ và một lượt dựng ảnh — 15-30s mỗi lượt.
            if vi is None and auto:
                model = None if auto is True else auto
                vi = translate(source[0], model=model, cut=da_cat[0])
                print("--- BẢN DỊCH MÁY (sửa được bằng --vi) ---\n"
                      + strip_marks(vi) + "\n", file=sys.stderr)
                if len(source) > 1 and not hide_quote and quote_vi is None:
                    quote_vi = translate(source[1], model=model, cut=da_cat[1])
                    print("--- BẢN DỊCH MÁY CHO QUOTE ---\n"
                          + strip_marks(quote_vi) + "\n", file=sys.stderr)
            if vi is not None:
                ten_mau, ma_mau = pick_hl(tid, theme, hl_color)
                print(f"[tweet_translate] màu nhấn: {ten_mau} {ma_mau}"
                      + ("" if hl_color else " (theo id tweet; đổi bằng --hl-color)"),
                      file=sys.stderr)
                nodes[0].evaluate("(n, h) => { n.innerHTML = h; }", to_html(vi, ma_mau))
                if len(nodes) > 1:
                    if hide_quote:
                        nodes[1].evaluate(_JS_HIDE_QUOTE)
                    elif quote_vi is not None:
                        nodes[1].evaluate("(n, h) => { n.innerHTML = h; }",
                                          to_html(quote_vi, ma_mau))
            n = page.evaluate(_JS_CLEAN if clean else _JS_TRIM)
            print(f"[tweet_translate] ẩn {n} phần điều khiển"
                  + (" (--clean)" if clean else ""), file=sys.stderr)
            for _ in range(IMAGE_TRY):
                if page.evaluate(_JS_IMAGES_READY):
                    break
                page.wait_for_timeout(WAIT_LAYOUT)
            # Ảnh của thẻ nhúng có cái vẽ bằng `background-image`, không nằm
            # trong `document.images` — vòng trên khi đó trả true ngay. Đợi
            # thêm mạng lặng; hết giờ thì chụp tiếp, không bỏ cả lượt.
            with contextlib.suppress(Exception):
                page.wait_for_load_state("networkidle", timeout=8000)
            page.wait_for_timeout(WAIT_LAYOUT)
            if out_path:
                el = _card(page)
                if el is None:
                    sys.exit(f"Không khoanh được thẻ tweet để chụp (id {tid}).")
                el.screenshot(path=str(out_path))
    if out_path:
        if not (out_path.exists() and out_path.stat().st_size > 0):
            sys.exit(f"Chụp ra tệp rỗng: {out_path}")
        image_provenance.stamp_file(out_path, "tweet_translate", source=f"x.com/i/status/{tid}")
    return source


def read_vi(text, file_path, bo_qua_dau: bool, nhan: str) -> str:
    vi = Path(file_path).read_text(encoding="utf-8") if file_path else text
    if not file_path:
        # `--vi` gõ trên MỘT dòng lệnh: nhận `\n` viết liền hai ký tự thành
        # xuống dòng thật. Vai Bob chạy theo allowlist từng chuỗi lệnh nên
        # không ghi được tệp tạm, mà tweet thì gần như luôn nhiều đoạn.
        vi = (vi or "").replace("\\n", "\n")
    vi = (vi or "").strip("\n")
    if not vi.strip():
        sys.exit(f"Bản dịch {nhan} rỗng.")
    # Áp TỪNG DÒNG. `drop_mark_forbid` nén `\s{2,}` về một dấu cách — viết cho
    # tiêu đề một dòng, và `\s` gồm cả `\n`, nên gọi thẳng trên cả bản dịch thì
    # mọi dòng trống giữa các đoạn biến mất: đo thật 23/09/2026, tweet bốn đoạn
    # ra một khối chữ liền, nhìn không còn giống tweet nữa.
    vi = "\n".join(vietnamese.drop_mark_forbid(d) for d in vi.split("\n"))
    if not bo_qua_dau:
        thieu = vietnamese.find_face_mark(strip_marks(vi))
        if thieu:
            sys.exit(f"Bản dịch {nhan} có chữ tiếng Việt mất dấu: {thieu}. Gõ lại cho đủ dấu, "
                     f"hoặc --bo-qua-dau nếu bản dịch thật sự là tiếng Anh.")
    return vi


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("url", help="Link tweet (x.com/<ai>/status/<id>) hoặc id trần")
    ap.add_argument("--brief", action="store_true",
                    help="Chỉ in nguyên văn tweet để dịch, không chụp")
    ap.add_argument("--vi", help="Bản dịch tiếng Việt (dùng <hl>…</hl> cho cụm tô đỏ)")
    ap.add_argument("--vi-file", help="Tệp chứa bản dịch — dùng cái này khi có nhiều dòng")
    ap.add_argument("--out", help="Ảnh PNG xuất ra")
    ap.add_argument("--theme", default="dark", choices=("dark", "light"))
    ap.add_argument("--lang", default="vi",
                    help="Ngôn ngữ CHỮ UI của thẻ (Theo dõi/Trả lời/ngày). Mặc định vi.")
    ap.add_argument("--clean", action="store_true",
                    help="Sạch hơn mặc định: bỏ luôn nút Theo dõi và icon ⓘ, "
                         "chỉ còn avatar-tên-tick-chữ-ngày")
    ap.add_argument("--quote-vi", help="Bản dịch cho tweet được QUOTE bên trong")
    ap.add_argument("--quote-vi-file", help="Tệp chứa bản dịch của tweet được quote")
    ap.add_argument("--hide-quote", action="store_true",
                    help="Ẩn hẳn khối quote thay vì dịch nó")
    ap.add_argument("--hl-color",
                    help="Màu cụm <hl>: mã #rrggbb hoặc tên "
                         f"({', '.join(HL_DARK)}). Không đặt thì chọn theo id tweet.")
    ap.add_argument("--model", help=f"Model dịch (mặc định {env_load.TRANSLATE_MODEL}). "
                                    "Chỉ dùng khi KHÔNG truyền --vi.")
    ap.add_argument("--bo-qua-dau", action="store_true",
                    help="Bỏ qua cổng chặn chữ Việt mất dấu (bản dịch là tiếng Anh)")
    a = ap.parse_args()

    if a.brief:
        source = render(a.url, None, None, theme=a.theme, lang=a.lang)
        print(source[0])
        if len(source) > 1:
            print("\n--- TWEET ĐƯỢC QUOTE BÊN TRONG (cũng nằm trong ảnh) ---\n")
            print("\n\n".join(source[1:]))
        return

    if not a.out:
        sys.exit("Thiếu --out (hoặc dùng --brief để chỉ đọc nguyên văn).")

    # Không đưa bản dịch thì MÁY DỊCH. `--vi` vẫn thắng tuyệt đối.
    tu_dich = None if (a.vi or a.vi_file) else (a.model or True)
    vi = (read_vi(a.vi, a.vi_file, a.bo_qua_dau, "tweet chính")
          if (a.vi or a.vi_file) else None)
    quote_vi = (read_vi(a.quote_vi, a.quote_vi_file, a.bo_qua_dau, "quote")
                if (a.quote_vi or a.quote_vi_file) else None)
    source = render(a.url, vi, a.out, theme=a.theme, lang=a.lang, clean=a.clean,
                    quote_vi=quote_vi, hide_quote=a.hide_quote, hl_color=a.hl_color,
                    auto=tu_dich)
    # Tweet có QUOTE mà không dịch, không ẩn => ảnh ra lẫn nguyên một khối tiếng
    # Anh, nhìn vẫn "đẹp" nên rất dễ lọt tới bước đăng. Chặn ở đây, và xoá luôn
    # tấm vừa chụp để không ai nhặt nhầm.
    # Cổng này chỉ còn cho trường hợp NGƯỜI đưa bản dịch: máy dịch thì quote đã
    # được dịch ngay trong render.
    if len(source) > 1 and quote_vi is None and not a.hide_quote and not tu_dich:
        Path(a.out).unlink(missing_ok=True)
        sys.exit("Tweet này có QUOTE lồng bên trong, chữ tiếng Anh của nó sẽ nằm trong ảnh:\n"
                 f"  {source[1][:160]!r}\n"
                 "Dịch nó bằng --quote-vi-file, hoặc bỏ hẳn bằng --hide-quote.")
    print(f"gốc  : {source[0][:120]!r}", file=sys.stderr)
    print(a.out)


if __name__ == "__main__":
    main()
