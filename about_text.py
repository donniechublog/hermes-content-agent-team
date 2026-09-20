#!/usr/bin/env python3
"""about_text.py — VE CHU VIET len anh, dung CHUNG cho Gin va Itachi.

Tach ra khoi itachi_submit.py (07/09/2026) khi Gin nhan viec thay chu tren the
quote: hai vai ve cung mot kieu, nen luat ve phai nam MOT cho. Truoc do
`_ve_khoi` (nay `about_block`) chi co trong itachi_submit.py; de Gin import cua Itachi la buoc mot vai
phu thuoc vao script cua vai khac, va sua mot ben quen ben kia.

Ham o day khong biet Telegram, khong biet spec, khong biet vai nao goi — chi
nhan (chu, hop, font, mau) va ve. Cong chan (mat dau, tran hop) tra ve danh
sach loi cho nguoi goi tu quyet.
"""
import sys
from pathlib import Path

from PIL import ImageDraw

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from card import _f, _wrap                                   # noqa: E402

FONTS = ROOT / "assets" / "fonts"
FONT = {"bold": FONTS / "BeVietnamPro-Bold.ttf", "regular": FONTS / "BeVietnamPro-Regular.ttf",
        "serif": FONTS / "NotoSerifDisplay.ttf", "condensed": FONTS / "Oswald.ttf",
        "mono": FONTS / "JetBrainsMono-Bold.ttf"}
HAS_MIN = 16
HAS_MEASURE = 200        # co chu dung de DO ti le muc/co — du lon de bot sai so lam tron


def path_font(font_key: str) -> str:
    return str(FONT.get(font_key) or FONT["regular"])


def font_default(h_vung: int, h_anh: int) -> str:
    """Doan font khi khong do duoc net chu (Itachi, duong cu): cao >= 4.5% anh
    thi coi la tieu de -> bold."""
    return "bold" if h_vung >= 0.045 * h_anh else "regular"


def height_item(d: ImageDraw.ImageDraw, text: str, font) -> float:
    """Chieu cao MUC that cua mot dong khi ve (bbox chu, khong phai bbox font)."""
    bb = d.textbbox((0, 0), text, font=font)
    return max(1, bb[3] - bb[1])


def has_by_original(d: ImageDraw.ImageDraw, text_goc: str, cao_net: int, font_key: str) -> int:
    """Co chu sao cho chu VE RA cao bang chu GOC do duoc tren anh.

    So sanh LIKE-FOR-LIKE: ve chinh chuoi GOC (text OCR doc duoc) bang font dich
    o co chuan, roi suy ra co chu can dung. Neu do bang chuoi TIENG VIET thi
    sai: 'GLOBAL EMPIRE' toan chu hoa khong co net thong xuong, ban dich co dau
    va co 'g','y' se cao hon o cung co chu — khop chieu cao muc se lam chu Viet
    NHO di thay vi bang chu goc (do that tren slide Hello Kitty 07/09/2026).
    """
    goc = (text_goc or "").strip() or "Hg"
    f = _f(path_font(font_key), HAS_MEASURE)
    return max(HAS_MIN, round(HAS_MEASURE * cao_net / height_item(d, goc, f)))


def ratio_empty(d: ImageDraw.ImageDraw, text: str, font_key: str) -> float:
    """Bề ngang trung bình một ký tự / chiều cao mực, khi VẼ `text` bằng font này."""
    f = _f(path_font(font_key), HAS_MEASURE)
    bb = d.textbbox((0, 0), text, font=f)
    cao, rong = max(1, bb[3] - bb[1]), bb[2] - bb[0]
    return rong / max(1, len((text or "").strip())) / cao


def pick_font(d: ImageDraw.ImageDraw, text: str, adv_goc: float, dam: bool) -> str:
    """Font gần chữ gốc nhất về BỀ NGANG, đo bằng chính font sẽ dùng để vẽ.

    Trước đây so `adv_goc` với một ngưỡng cố định. Ngưỡng đó chỉnh trên carousel
    Hello Kitty (condensed đo 0.386–0.463) rồi gãy ngay ở carousel kế tiếp: cùng
    MỘT tiêu đề ba dòng ra hai font khác nhau vì hai dòng đo 0.61–0.64 còn dòng
    kia 0.51. Không có ngưỡng nào đúng cho mọi font — nên hỏi thẳng từng font
    "nếu vẽ chuỗi này thì bề ngang bao nhiêu" rồi lấy font gần nhất. Đo lại toàn
    bộ ảnh đã có 07/09/2026: cả 6 tiêu đề đều ra đúng font nhìn thấy trên ảnh.
    """
    ung = ("bold", "condensed") if dam else ("regular",)
    if not adv_goc or len(ung) == 1:
        return ung[0]
    return min(ung, key=lambda k: abs(ratio_empty(d, text, k) - adv_goc))


def to_color(c):
    """color_rgb -> tuple 3 so 0-255. (Ten `color` bi tham so `color` cua about_block
    che mat sau khi doi ten LOW-50 — `color(color)` la TypeError; doi thanh to_color, LOW-56.) Spec cua vai co the ghi bat cu thu gi;
    truoc 06/09/2026 `tuple(color)` nem TypeError giua chung buoi ve, mat ca
    slide va vai chi thay traceback."""
    try:
        t = tuple(int(x) for x in list(c)[:3])
    except (TypeError, ValueError):
        return (20, 20, 20)
    if len(t) != 3 or any(not 0 <= x <= 255 for x in t):
        return (20, 20, 20)
    return t


def ceiling_box(d: ImageDraw.ImageDraw, text: str, w: int, h: int, font_key: str,
             co: int = None, buoc: int = None, cao_goc: int = None) -> int:
    """So pixel chieu cao BI TRAN ra ngoai hop khi da co chu nho het muc.

    `about_block` co lai co chu toi HAS_MIN roi VE BAT KE — vong while thoat vi
    `size > HAS_MIN` la sai, khong phai vi chu da vua. Cau dich dai gap doi cau
    goc thi chu tran de len phan anh ben duoi va khong cong nao bao (06/09/2026).
    """
    f = _f(path_font(font_key), HAS_MIN)
    lines = _wrap(d, text, f, w)
    lh = _space_line(d, lines, f, _slit(buoc, cao_goc, co, HAS_MIN))
    return max(0, lh * len(lines) - int(h * 1.05))


def _space_line(d: ImageDraw.ImageDraw, lines: list, f, khe: float = None) -> int:
    """Giãn dòng khi vẽ.

    `khe` là KHOẢNG TRỐNG giữa hai dòng đo được trên ảnh gốc (nhịp dòng trừ chiều
    cao mực). Có `khe` thì giãn dòng = chiều cao mực THẬT của dòng cao nhất đang
    vẽ + khe đó.

    Vì sao không dùng thẳng nhịp dòng gốc: nhịp đó là nhịp của chữ GỐC. Tiêu đề
    tiếng Anh chữ hoa không dấu chỉ cao bằng cap-height, chữ hoa tiếng Việt có
    dấu thanh phía trên và dấu nặng phía dưới nên cao hơn ~25% ở CÙNG cỡ chữ. Ép
    theo nhịp gốc thì dấu dòng dưới chồng lên nét dòng trên — ảnh TECHS
    07/09/2026: nhịp gốc 148px, dòng Oswald tiếng Việt ở cùng cỡ cao 198px, "NGHỀ
    RỦI" ra như mất dấu vì dấu nằm đè vào dòng trên.

    Không có `khe` thì ước lượng bằng chiều cao "ÂgqĐ" (đường cũ của Itachi).
    """
    if khe is None:
        return int((f.getbbox("ÂgqĐ")[3] - f.getbbox("ÂgqĐ")[1]) * 1.12)
    cao = max((height_item(d, ln, f) for ln in lines if ln.strip()), default=1)
    return int(cao + max(0, khe))


def _slit(buoc: int, cao_goc: int, co: int, size: int):
    """Khoảng trống giữa hai dòng của ảnh gốc, quy về cỡ chữ đang vẽ."""
    if not buoc or not cao_goc or not co:
        return None
    return max(0, buoc - cao_goc) * size / co


def pick_has(d: ImageDraw.ImageDraw, text: str, w: int, h: int, font_key: str,
            co: int = None, buoc: int = None, cao_goc: int = None) -> int:
    """Co chu THAT SU se ve ra: bat dau tu `co` mong muon roi thu nho den khi vua
    hop. Tach rieng de cong chan hoi duoc "co bao nhieu" TRUOC khi ve."""
    path = path_font(font_key)
    size = max(HAS_MIN, int(co if co else h * 0.82))
    while size > HAS_MIN:
        f = _f(path, size)
        lines = _wrap(d, text, f, w)
        if _space_line(d, lines, f, _slit(buoc, cao_goc, co, size)) * len(lines) <= h * 1.05:
            break
        size -= 2
    return size


def about_block(d: ImageDraw.ImageDraw, text: str, x: int, y: int, w: int, h: int,
            font_key: str, color, align: str, co: int = None,
            buoc: int = None, cao_goc: int = None) -> None:
    """Ve `text` vua trong hop (x,y,w,h). `co` la co chu MONG MUON (do tu chu
    goc), `buoc` la nhip dong do duoc tren anh goc; ca hai van bi thu nho neu
    khong vua hop. Khong co `co` thi lay 82% chieu cao hop nhu truoc."""
    path = path_font(font_key)
    size = pick_has(d, text, w, h, font_key, co, buoc, cao_goc)
    f = _f(path, size)
    lines = _wrap(d, text, f, w)
    lh = _space_line(d, lines, f, _slit(buoc, cao_goc, co, size))
    yy = y + max(0, (h - lh * len(lines)) // 2)
    for ln in lines:
        tw = d.textlength(ln, font=f)
        xx = x + (w - tw) / 2 if align == "center" else x
        d.text((xx, yy), ln, font=f, fill=to_color(color))
        yy += lh
