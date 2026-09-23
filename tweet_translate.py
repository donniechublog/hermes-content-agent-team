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

Hai bước:

    venv/bin/python tweet_translate.py "<link>" --brief
    venv/bin/python tweet_translate.py "<link>" --vi-file vi.txt --out tweet.png

`--brief` in ra nguyên văn tweet để người dịch chép — chính chữ trong thẻ, nên
không phải gọi crawl-queue (10–40s/lượt) chỉ để lấy lại đúng đoạn đang hiển thị.

Trong bản dịch, bọc cụm cần TÔ ĐỎ bằng `<hl>…</hl>`:

    Qwen3.8 Flash <hl>miễn phí</hl> trong một tuần.

Ảnh ra đưa tiếp cho Bob đóng khung + mascot + handle:

    venv/bin/python image_frame.py --image tweet.png --emoji "🤖" --out framed.png
"""
import argparse
import contextlib
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

import image_provenance                                      # noqa: E402
import vietnamese                                            # noqa: E402
from browser_session import (MOBILE_DPR, MOBILE_UA,          # noqa: E402
                            MOBILE_VIEWPORT, session_or_new)

EMBED = "https://platform.twitter.com/embed/Tweet.html"
# Đỏ của X (`#f4212e`) chứ không phải đỏ thuần: thẻ nhúng dùng đúng mã này, nên
# cụm tô đỏ nhìn ra "một phần của thẻ" thay vì chữ dán lên.
HL_COLOR = "#f4212e"
# Node chữ của thẻ nhúng. Tên do X đặt và X có thể đổi bất cứ lúc nào — không
# thấy thì DỪNG, đừng chụp bừa: ảnh ra khi đó là tweet tiếng Anh nguyên vẹn,
# nhìn vẫn "đẹp" nên rất dễ lọt tới bước đăng.
SEL_TEXT = '[data-testid="tweetText"]'
SEL_CARD = ('[data-testid="tweet"]', "article")
TIME_LIMIT = 45000
WAIT_LAYOUT = 900          # ms cho font/ảnh nhúng ổn định trước khi chụp
IMAGE_TRY = 8              # số lần đợi ảnh đính kèm tải xong

_STATUS = re.compile(r"(?:x|twitter)\.com/[^/]+/status(?:es)?/(\d{5,25})", re.I)

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


def to_html(vi: str) -> str:
    """Bản dịch (chữ thường + `<hl>…</hl>`) -> HTML an toàn để gán vào thẻ.

    Escape TRƯỚC rồi mới mở lại đúng hai thẻ `<hl>`: bản dịch là chữ người viết
    chứ không phải HTML — để lọt một dấu `<` của người dịch là vỡ cả bố cục thẻ.
    """
    s = html.escape(vi)
    s = s.replace("&lt;hl&gt;", f'<span style="color:{HL_COLOR};font-weight:700">')
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
           quote_vi=None, hide_quote=False, phien=None) -> list:
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
            source = [(n.inner_text() or "") for n in nodes]
            if vi is not None:
                nodes[0].evaluate("(n, h) => { n.innerHTML = h; }", to_html(vi))
                if len(nodes) > 1:
                    if hide_quote:
                        nodes[1].evaluate(_JS_HIDE_QUOTE)
                    elif quote_vi is not None:
                        nodes[1].evaluate("(n, h) => { n.innerHTML = h; }", to_html(quote_vi))
            if clean:
                n = page.evaluate(_JS_CLEAN)
                print(f"[tweet_translate] ẩn {n} nút tương tác (--clean)", file=sys.stderr)
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
                    help="Ẩn nút theo dõi/thích/trả lời, giữ avatar-tên-tick-ngày")
    ap.add_argument("--quote-vi", help="Bản dịch cho tweet được QUOTE bên trong")
    ap.add_argument("--quote-vi-file", help="Tệp chứa bản dịch của tweet được quote")
    ap.add_argument("--hide-quote", action="store_true",
                    help="Ẩn hẳn khối quote thay vì dịch nó")
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
    if not (a.vi or a.vi_file):
        sys.exit("Thiếu --vi / --vi-file. Chạy --brief trước để lấy nguyên văn tweet.")

    vi = read_vi(a.vi, a.vi_file, a.bo_qua_dau, "tweet chính")
    quote_vi = (read_vi(a.quote_vi, a.quote_vi_file, a.bo_qua_dau, "quote")
                if (a.quote_vi or a.quote_vi_file) else None)
    source = render(a.url, vi, a.out, theme=a.theme, lang=a.lang, clean=a.clean,
                    quote_vi=quote_vi, hide_quote=a.hide_quote)
    # Tweet có QUOTE mà không dịch, không ẩn => ảnh ra lẫn nguyên một khối tiếng
    # Anh, nhìn vẫn "đẹp" nên rất dễ lọt tới bước đăng. Chặn ở đây, và xoá luôn
    # tấm vừa chụp để không ai nhặt nhầm.
    if len(source) > 1 and quote_vi is None and not a.hide_quote:
        Path(a.out).unlink(missing_ok=True)
        sys.exit("Tweet này có QUOTE lồng bên trong, chữ tiếng Anh của nó sẽ nằm trong ảnh:\n"
                 f"  {source[1][:160]!r}\n"
                 "Dịch nó bằng --quote-vi-file, hoặc bỏ hẳn bằng --hide-quote.")
    print(f"gốc  : {source[0][:120]!r}", file=sys.stderr)
    print(f"dịch : {strip_marks(vi)[:120]!r}", file=sys.stderr)
    print(a.out)


if __name__ == "__main__":
    main()
