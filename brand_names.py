"""brand_names.py — nhan dien TEN HANG / TEN MODEL trong chu, va MAU to no (LOW-344).

Dung chung cho ca doi designer: Ethan (card.py, tieu de the), Dre (carousel.py,
hook bia), Kite (render_edu.py, tieu de slide) — va cho render_edu.subject_brand
(LOW-340, chon palette slide). Mot cho nhan dien, mot cho chon mau: hai vai
khong duoc troi mau khac nhau cho cung mot hang.

Truoc day `card._extract_label` chi tach theo dau cach, nen ten model — gan nhu
luon viet lien — truot het: "DEEPSEEK-V4.1-FLASH", "QWEN3.8-27B", "GPT-5.6",
"OPENAI/GPT-OSS-120B" deu khong duoc to (do 21/09/2026).

Luat to (Ong Chu chot 21/09/2026, LOW-344):
  1. to TRON CUM ten model ("DEEPSEEK-V4.1-FLASH"), khong chi phan ten hang;
  2. tien to to chuc ("DEEPSEEK-AI/") to KHAC MAU ten model;
  3. mau theo PALETTE cua hang (render_edu.THEMES qua BRAND_THEME): ten model =
     nhan chinh `a`, tien to = nhan phu `b` (hoac `a` pha nhat khi `b` gan nhu
     xam/trang, khong phan biet duoc voi chu). Hang chua co palette: mau
     `card.COLOR_RANK` cua no;
  4. hang tong den trang (OpenAI, xAI, Apple...): mau `fallback` do noi goi dua
     vao — mau nhan cua theme/kenh dang dung, mien noi bat.

Module nay KHONG import card/render_edu o dau tep (card import no) — chi import
luc goi ham.
"""
import colorsys
import re

# Tu khong nam trong `card.BRAND_FROM` (bang to ten hang cua Ethan).
BRAND_ALIAS = {"GPT": ("OPENAI",), "HUGGINGFACE": ("HUGGING", "FACE")}
# Cat mot tu ghep thanh cac manh de do ten hang: gach noi/cheo/cham/cong, va
# chu dinh so phien ban ("QWEN3.8" -> QWEN, 3.8; "LLAMA4" -> LLAMA, 4).
_SPLIT = re.compile(r"[-/:_.+]+")
_LETTER_DIGIT = re.compile(r"(?<=[A-Za-z])(?=\d)")
ORG_TINT = 0.45            # tien to: `a` pha trang bay nhieu khi `b` khong du mau
MIN_ORG_SATURATION = 0.3   # `b` duoi muc nay (xam/nga/trang) -> dung `a` pha nhat


def _parts(core: str) -> list:
    """Manh viet hoa cua mot tu ghep, bo manh rong."""
    return [p for p in _SPLIT.split(_LETTER_DIGIT.sub(" ", core).replace(" ", "-").upper()) if p]


def _key_in(core: str):
    """Khoa hang dau tien nam trong mot tu ghep (co ca cum nhieu manh nhu
    META-AI, HUGGING-FACE), hoac None."""
    import card
    parts = _parts(core)
    for i in range(len(parts)):
        for cum in card.BRAND_PHRASE:
            if tuple(parts[i:i + len(cum)]) == cum:
                return cum
        if parts[i] in card.BRAND_FROM:
            return (parts[i],)
        if parts[i] in BRAND_ALIAS:
            return BRAND_ALIAS[parts[i]]
    return None


def _split_punct(word: str) -> tuple:
    """(dau_truoc, loi, dau_sau): tach dau cau hai dau tu, giu dung ky tu goc."""
    import card
    core = word.strip(card._RIA)
    if not core:
        return word, "", ""
    i = word.index(core)
    return word[:i], core, word[i + len(core):]


def line_segments(line: str) -> list:
    """Cat mot dong thanh TU (theo dau cach, nhu cach Ethan ve), moi tu la danh
    sach khuc `(chu, vai, khoa_hang)` noi lien lai dung bang tu goc.

    vai: None (chu thuong) | "name" (ten hang / ten model) | "org" (tien to to
    chuc truoc dau "/"). Tu khong dinh ten hang tra ve dung mot khuc vai None."""
    import card
    words = line.split(" ")
    exact = card._extract_label(line)          # cum nhieu tu cach dau cach: HUGGING FACE, META AI
    out = []
    for word, (_w, key) in zip(words, exact, strict=True):
        lead, core, trail = _split_punct(word)
        segs = []
        if not core:
            out.append([(word, None, None)])
            continue
        if key is None and "/" in core:
            org, model = core.rsplit("/", 1)
            k_model, k_org = _key_in(model), _key_in(org)
            key = k_model or k_org
            if key and model:
                segs = [(org + "/", "org", key), (model, "name", key)]
        if not segs:
            key = key or _key_in(core)
            segs = [(core, "name", key)] if key else [(core, None, None)]
        if lead:
            segs.insert(0, (lead, None, None))
        if trail:
            segs.append((trail, None, None))
        out.append(segs)
    return out


def brand_keys(text: str) -> list:
    """Cac khoa hang trong `text`, theo thu tu xuat hien, khong lap."""
    keys = []
    for word in line_segments(text or ""):
        for _t, _vai, key in word:
            if key and key not in keys:
                keys.append(key)
    return keys


def hex_rgb(h: str) -> tuple:
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def tint(rgb, t: float) -> tuple:
    """Pha trang `t` (0..1) — giu hue, nhat hon."""
    return tuple(round(c + (255 - c) * t) for c in rgb)


def _saturation(rgb) -> float:
    return colorsys.rgb_to_hsv(*(c / 255 for c in rgb))[1]


def colors_for(key, fallback) -> tuple:
    """(mau_ten_model, mau_tien_to) cho mot hang, CHUA keo sang/toi theo nen.

    `fallback`: mau noi bat cua theme/kenh dang dung — cho hang den trang. None
    thi hang den trang tra (None, None): noi goi tu giu mau chu thuong."""
    import card
    import render_edu
    theme = render_edu.BRAND_THEME.get(key)
    b = None
    if theme:
        a = hex_rgb(render_edu.THEMES[theme]["a"])
        b = hex_rgb(render_edu.THEMES[theme]["b"])
    elif render_edu.is_mono_brand(key):
        a = fallback
    else:
        a = card._color_of_rank(key) or fallback
    if a is None:
        return None, None
    a = tuple(a[:3])
    org = b if b and _saturation(b) >= MIN_ORG_SATURATION else tint(a, ORG_TINT)
    return a, org
