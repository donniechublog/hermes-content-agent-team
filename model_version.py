#!/usr/bin/env python3
"""Ảnh phải KHỚP PHIÊN BẢN model mà tin nói tới (LOW-363).

Ông Chủ 22/09/2026, xem carousel Gemini (tin tháng 9/2026) dùng bảng benchmark Gemini
1.0/1.5 năm 2024: *"năm bao nhiêu rồi mà vẫn còn gemini 1.5 ?"*, rồi chốt tiêu chí:
*"ko giới hạn thời gian tức là trong bài nói tới gemini 3 thì dù ảnh đó được đăng năm bao
nhiêu miễn là của gemini 3 thì nó ko outdated. còn đây là gemini 1, đâu có liên quan"* và
*"tin ra vào tháng 5/2026, ko cần nhắc mô hình nào thì cũng phải chọn mô hình có date gần
nhất"*.

Nên tiêu chí là PHIÊN BẢN, không bao giờ là tuổi/ngày đăng ảnh (§1.2d "không giới hạn thời
gian" giữ nguyên):
  - bài nhắc phiên bản nào của một họ model → phiên bản tham chiếu là các phiên bản đó;
  - bài nhắc họ model mà không nhắc phiên bản → phiên bản MỚI NHẤT ra trước ngày của tin,
    theo bảng lịch sử phiên bản trên Wikipedia (không lấy từ trí nhớ LLM — chính trí nhớ
    đó đã gõ "Gemini 1.5 Pro benchmark");
  - ảnh/từ khoá ghi một phiên bản của họ đó mà SỐ CHÍNH khác phiên bản tham chiếu → loại.
So theo số chính (3 Pro ~ 3.1 Flash) — biến thể cùng thế hệ coi là khớp.
"""
import json
import re
import sys
import time
from datetime import date, datetime

# họ model -> (regex tên họ, trang Wikipedia có bảng lịch sử phiên bản)
FAMILIES = {
    "gemini": (r"gemini", "Gemini_(language_model)"),
    "gemma": (r"gemma", "Gemma_(language_model)"),
    "claude": (r"claude", "Claude_(AI)"),
    "gpt": (r"chatgpt|gpt", "ChatGPT"),
    "llama": (r"llama", "Llama_(language_model)"),
    "qwen": (r"qwen", "Qwen"),
    "grok": (r"grok", "Grok_(chatbot)"),
    "deepseek": (r"deepseek(?:[\s-]?[vr])?", "DeepSeek"),
    "mistral": (r"mistral", "Mistral_AI"),
}
# Chữ bậc/biến thể có thể đứng giữa tên họ và số ("Claude Opus 4.7", "Gemini Pro 1.5").
_TIER = r"(?:pro|ultra|flash|nano|lite|opus|sonnet|haiku|fable|mythos|max|plus|turbo|mini|image)"
# Số phiên bản: tối đa 2 chữ số phần chính — "Gemini 2026" là năm, không phải phiên bản.
_NUM = r"(\d{1,2}(?:\.\d{1,2})?)(?!\d)"
WIKI_API = "https://en.wikipedia.org/w/api.php"
CACHE_SECONDS = 3 * 86400
MAX_MAJOR = 15                  # so chinh lon hon la mo ho (slug URL mat dau cham), khong chan
MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august",
     "september", "october", "november", "december"], 1)}


def _family_rx(pat: str) -> re.Pattern:
    return re.compile(r"(?<![a-z])(?:" + pat + r")[\s-]*(?:" + _TIER + r"[\s-]*){0,2}v?" + _NUM, re.I)


# Tên model CŨ không kèm số mà vẫn chỉ đúng một phiên bản (dựng lại draft Gemini 22/09/2026:
# bảng "Gemini Ultra vs GPT-4" lọt cổng vì không có số). Chỉ khớp khi KHÔNG có số theo sau.
LEGACY_NAMES = {r"gemini\s+ultra": ("gemini", "1.0"), r"\bbard\b": ("gemini", "1.0")}


def versions_in_text(text: str) -> dict:
    """{họ: {"3.1", "1.5", ...}} — các phiên bản có số được ghi trong đoạn chữ. Thuần."""
    ra = {}
    for fam, (pat, _) in FAMILIES.items():
        for m in _family_rx(pat).finditer(text or ""):
            ra.setdefault(fam, set()).add(m.group(1))
    for pat, (fam, v) in LEGACY_NAMES.items():
        if re.search(r"(?<![a-z])" + pat + r"(?![\s-]*\d)", text or "", re.I):
            ra.setdefault(fam, set()).add(v)
    return ra


def families_in_text(text: str) -> set:
    thap = (text or "").lower()
    return {f for f, (pat, _) in FAMILIES.items() if re.search(r"(?<![a-z])(?:" + pat + r")", thap)}


def major(v: str) -> str:
    return (v or "").split(".")[0]


def story_date(title: str, summary: str = "", fallback_ts=None) -> date:
    """Ngày của tin: "in May 2026" / "tháng 5/2026" / "05/2026" trong tiêu đề hoặc tóm tắt
    (lấy cuối tháng đó), không có thì ngày `fallback_ts` (unix), không có nữa thì hôm nay."""
    t = f"{title or ''} {summary or ''}"
    m = re.search(r"\b(" + "|".join(MONTHS) + r")\s+(20\d\d)\b", t, re.I)
    if m:
        return _month_end(int(m.group(2)), MONTHS[m.group(1).lower()])
    m = re.search(r"th[aá]ng\s*(\d{1,2})\s*[/.-]\s*(20\d\d)", t, re.I)
    if m and 1 <= int(m.group(1)) <= 12:
        return _month_end(int(m.group(2)), int(m.group(1)))
    if fallback_ts:
        try:
            return datetime.fromtimestamp(float(fallback_ts)).date()
        except (TypeError, ValueError, OSError):
            pass
    return date.today()


def _month_end(y: int, mth: int) -> date:
    import calendar
    return date(y, mth, calendar.monthrange(y, mth)[1])


# ---- lịch sử phiên bản từ Wikipedia -------------------------------------------------
_DATE_TPL = re.compile(r"\{\{\s*(?:date|dts|start date)\s*\|\s*([^}]*)\}\}", re.I)


def _parse_tpl_date(arg: str):
    parts = [p.strip() for p in re.split(r"[|]", arg) if p.strip() and "=" not in p]
    if len(parts) == 1:
        parts = re.split(r"-", parts[0])
    try:
        y = int(parts[0])
        mth = int(parts[1]) if len(parts) > 1 else 12
        d = int(parts[2]) if len(parts) > 2 else 1
        return date(y, mth, d)
    except (ValueError, IndexError):
        return None


def parse_version_table(wikitext: str) -> list:
    """[(phiên bản, ngày ra mắt)] từ mọi bảng wikitable có cột tên + template ngày. Thuần."""
    ra = []
    for bang in re.findall(r"\{\|[^\n]*wikitable.*?\n\|\}", wikitext or "", re.S):
        for dong in re.split(r"\n\|-[^\n]*", bang)[1:]:
            o = [x for x in re.split(r"\n[|!]|\|\||!!", "\n" + dong.strip()) if x.strip()]
            if len(o) < 2:
                continue
            ten = re.sub(r"\[\[(?:[^|\]]*\|)?([^\]]*)\]\]", r"\1", o[0])
            ten = re.sub(r"^[^|]*=\"[^\"]*\"\s*\|", "", ten).strip()     # scope="row" |
            so = re.search(r"(?<![\d.])" + _NUM, ten)
            ngay = next((_parse_tpl_date(m.group(1)) for c in o[1:4] for m in [_DATE_TPL.search(c)] if m), None)
            if so and ngay:
                ra.append((so.group(1), ngay))
    return ra


def _cache_path():
    import env_load
    import state_paths
    return env_load.state_dir() / state_paths.MODEL_VERSIONS_FILE


def release_timeline(family: str, fetch=None) -> list:
    """[(phiên bản, ngày)] của họ model, cache 3 ngày trong state. `fetch(page) -> wikitext`
    thay được để test. Lỗi mạng -> dùng cache cũ nếu có, không thì []."""
    page = FAMILIES.get(family, (None, None))[1]
    if not page:
        return []
    try:
        p = _cache_path()
        cache = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    except (OSError, ValueError):
        p, cache = None, {}
    muc = cache.get(family) or {}
    if muc and time.time() - muc.get("ts", 0) < CACHE_SECONDS:
        return [(v, date.fromisoformat(d)) for v, d in muc.get("rows", [])]
    wt = (fetch or _fetch_wikitext)(page)
    if not wt:
        return [(v, date.fromisoformat(d)) for v, d in muc.get("rows", [])]
    rows = parse_version_table(wt)
    cache[family] = {"ts": time.time(), "page": page, "rows": [(v, d.isoformat()) for v, d in rows]}
    if p is not None:
        try:
            p.write_text(json.dumps(cache, ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass
    return rows


def _fetch_wikitext(page: str) -> str:
    try:
        import httpx
        import env_load
        r = httpx.get(WIKI_API, params={"action": "parse", "page": page, "prop": "wikitext",
                                        "redirects": 1, "format": "json"},
                      headers={"User-Agent": env_load.UA_WIKI}, timeout=20)
        return r.json().get("parse", {}).get("wikitext", {}).get("*", "")
    except Exception as e:                                   # noqa: BLE001
        print(f"[phien ban] Wikipedia {page}: {type(e).__name__}", file=sys.stderr)
        return ""


# ---- phiên bản tham chiếu + cổng ------------------------------------------------------
def reference_versions(title: str, text: str = "", when: date = None, timeline=release_timeline) -> dict:
    """{họ: {"versions": [...], "source": "article"|"wikipedia", "date": iso|None}} cho mọi
    họ model được nhắc trong tiêu đề/thân bài."""
    toan = f"{title or ''}\n{text or ''}"
    co_so = versions_in_text(toan)
    ra = {}
    for fam in families_in_text(title or "") | set(co_so):
        if fam in co_so:
            ra[fam] = {"versions": sorted(co_so[fam]), "source": "article", "date": None}
            continue
        rows = [(v, d) for v, d in timeline(fam) if when is None or d <= when]
        if rows:
            v, d = max(rows, key=lambda r: r[1])
            ra[fam] = {"versions": [v], "source": "wikipedia", "date": d.isoformat()}
    return ra


def mismatches(text: str, ref: dict) -> list:
    """["Gemini 1.5"...] — phiên bản ghi trong `text` thuộc họ có tham chiếu mà số chính
    không trùng số chính nào của tham chiếu. Thuần."""
    ra = []
    for fam, vs in versions_in_text(text).items():
        r = ref.get(fam)
        if not r:
            continue
        cho = {major(x) for x in r["versions"]}
        # So chinh > MAX_MAJOR la mo ho, khong chan: slug URL bo dau cham ("gemini-35-pro"
        # = Gemini 3.5 Pro, do that A37 22/09/2026) — chua ho model nao toi so do.
        ra += [f"{fam} {v}" for v in sorted(vs) if major(v) not in cho and int(major(v)) <= MAX_MAJOR]
    return ra


def describe_reference(ref: dict) -> str:
    """Một dòng cho brief: "gemini 3 Pro (Wikipedia, ra 2025-11-18)"."""
    out = []
    for fam, r in sorted(ref.items()):
        v = "/".join(r["versions"])
        out.append(f"{fam} {v}" + (f" (Wikipedia, ra {r['date']})" if r["source"] == "wikipedia" else " (bài nhắc)"))
    return "; ".join(out)


IMAGE_TEXT_KEYS = ("description", "alt", "url", "page_url", "printed_version")


def apply_image_gate(images: list, ref: dict) -> int:
    """Ảnh ghi phiên bản sai số chính -> `relevant=False`, `uses=[]`, `version_mismatch`.
    Trả số ảnh bị chặn. Ảnh không ghi phiên bản (logo trơn, người, trụ sở) không bị xét."""
    n = 0
    if not ref:
        return 0
    for a in images:
        # Tung truong rieng: noi chuoi lai thi "…Gemini" cuoi truong nay + "35%…" dau truong
        # sau thanh mot phien ban gia.
        sai = sorted({x for k in IMAGE_TEXT_KEYS for x in mismatches(str(a.get(k) or ""), ref)})
        if sai:
            a["version_mismatch"] = ", ".join(sai)
            a["relevant"], a["uses"] = False, []
            n += 1
    return n
