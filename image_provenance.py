#!/usr/bin/env python3
"""image_provenance.py — dấu vết xuất xứ PNG, THUẦN CƠ CHẾ, không có tiêu chí nào.

Tách khỏi `image_rules.py` khi bỏ file dùng chung đó (LOW-182, 16/09/2026): mọi
`check_*`/`kiem_*` (có ngưỡng, có phán đoán "ảnh này dùng được không") đi vào ba
module riêng của Ethan/Dre/Kite (`image_rules_<vai>.py`), CÒN mấy hàm ở đây thì
không — chúng chỉ đọc/ghi một dòng text vào metadata PNG ("ảnh này do công cụ
nào tạo ra"), không có ngưỡng nào để mà lệch giữa các vai. Bằng chứng: Gin và
Itachi vốn đã gọi `stamp_file` từ trước 16/09/2026 mà KHÔNG áp bộ luật ảnh nào
cả (`swap_image_text.py`/`gin_submit.py` chỉ sửa ảnh gốc, không tạo ảnh mới) —
tức bản thân hệ thống đã coi đây là hạ tầng đứng ngoài "luật", không phải một
phần của thứ vừa bị tách ba.

Mọi công cụ TẠO ảnh (`crop_ratio.py`, `capture_chart.py`, `arxiv_figures.py`,
`ranking.py`, `carousel.py` ghép dọc, `prepare/browser.py`, `prepare/fallback_rounds.py`)
và công cụ SỬA ảnh (`gin_submit.py`, `swap_image_text.py`) đều đóng dấu qua đây,
bất kể đang làm cho vai nào — ba module luật đọc dấu này qua `read_crop_trace`/
`allows_landscape_crop`/`is_ranking_image`/`is_stacked_composite`.
"""
from pathlib import Path

from PIL import Image

# ---- Ten metadata PNG (LOW-237) -----------------------------------------------
# Ham GHI chi dung ten English duoi day. PNG cu tren may chu (~9 GB, md5 da ghi so)
# KHONG ghi lai, nen mang metadata tieng Viet mai mai: moi ham DOC phai nhan CA ten/
# gia tri cu lan moi. Kien thuc cu -> moi CHI nam o ba bang LEGACY_* nay (bang duyet:
# docs/tu_dien_ten/image_search_keys_v2.json) — khong viet chuoi cu rai o module khac.
PROVENANCE_KEY = "provenance"       # cong cu nao dung ra anh
CROP_TRACE_KEY = "crop_trace"       # dau vet crop_ratio: original=WxH;ratio=..;cx=..;cy=..;landscape_crop=0|1
FIGURE_KEY = "figure"               # arxiv_figures: "Figure 1"
PDF_PAGE_KEY = "pdf_page"           # arxiv_figures: so trang PDF (1-based)

# Ten CU co chu y (anh PNG da luu mang dau cu mai mai) — cac khoa nay nam trong moc
# tests/test_json_keys_english.py co ly do, khong phai khoa moi.
LEGACY_KEYS = {"nguon_dung": PROVENANCE_KEY, "crop_ti_le": CROP_TRACE_KEY,
               "hinh": FIGURE_KEY, "trang_pdf": PDF_PAGE_KEY}
LEGACY_CROP_TOKENS = {"goc": "original", "ti_le": "ratio", "cat_ngang": "landscape_crop"}
LEGACY_PROVENANCE_VALUES = {
    "chup_xep_hang": "ranking_capture", "the_xep_hang": "ranking_card", "ghep_doc": "vertical_stack",
    "chup_chart": "chart_capture", "doi_chu_anh": "image_text_swap", "arxiv_bia": "arxiv_cover",
    "arxiv_hinh": "arxiv_figure", "the_logo": "logo_card", "dre_chuan_bi": "engine_download"}

MARK_PNG = (CROP_TRACE_KEY, PROVENANCE_KEY) + tuple(
    cu for cu, moi in LEGACY_KEYS.items() if moi in (CROP_TRACE_KEY, PROVENANCE_KEY))


def stamp_provenance(xuat_xu, **them):
    """Tra ve PngInfo mang dau `provenance=<xuat_xu>` (+ cac khoa phu neu co).

    Ten tham so la `xuat_xu` chu khong phai `nguon`: `nguon` la mot trong nhung
    khoa phu hay dung nhat (nguon=ARENA.AI), de trung ten thi vo TypeError.

    Moi cong cu trong doi sinh ra anh PHAI dong dau: crop_ratio.py, arxiv_cover.py,
    ghep doc cua carousel.py, capture_chart.py. Cong `kiem_xuat_xu` dua vao dau nay
    de phan biet "anh do doi dung ra" voi "anh cat tay bang cong cu ngoai".
    """
    from PIL.PngImagePlugin import PngInfo
    m = PngInfo()
    m.add_text(PROVENANCE_KEY, str(xuat_xu))
    for k, v in them.items():
        if v is not None:
            m.add_text(str(k), str(v))
    return m


def stamp_file(duong_dan, xuat_xu, **them):
    """Mo lai mot tep PNG DA LUU va ghi dau `provenance` (+ khoa phu) vao do.

    Cho cac cong cu khong luu bang PIL (playwright screenshot, cv2.imwrite,
    tai thang tu URL). Khong phai PNG thi bo qua, tra ve False — dong dau la
    viec phu, khong duoc lam hong buoc chinh.
    """
    q = Path(duong_dan)
    try:
        im = Image.open(q)
        if (im.format or "").upper() != "PNG":
            return False
        im.load()
        im.save(q, "PNG", pnginfo=stamp_provenance(xuat_xu, **them))
        return True
    except Exception:
        return False


def crop_trace_text(w, h, ratio, cx, cy, landscape_crop) -> str:
    """Gia tri khoa `crop_trace` — MOT cho dung chuoi cho crop_ratio.py CLI va
    prepare/download_filter._save_crop (truoc LOW-237 hai noi tu viet tay)."""
    return f"original={w}x{h};ratio={ratio};cx={cx};cy={cy};landscape_crop={int(landscape_crop)}"


def _text(img):
    return (getattr(img, "text", None) or img.info or {})


def read_text(img, raw=None) -> dict:
    """Text chunk cua PNG voi ten/gia tri cu da quy ve ten moi (LOW-237): khoa, gia tri
    `provenance` va ten token trong `crop_trace`. Ca hai ten cung co (khong le xay ra)
    thi ten moi thang."""
    raw = _text(img) if raw is None else raw
    ra = {}
    for k, v in raw.items():
        moi = LEGACY_KEYS.get(k, k)
        if moi != k and moi in raw:
            continue
        if moi == PROVENANCE_KEY and isinstance(v, str):
            v = LEGACY_PROVENANCE_VALUES.get(v, v)
        elif moi == CROP_TRACE_KEY and isinstance(v, str):
            v = ";".join(_new_crop_token(tok) for tok in v.split(";"))
        ra[moi] = v
    return ra


def carried_text(img) -> dict:
    """Text chunk de CHEP sang ban cat (`_save_crop`): ten cu da dich sang ten moi,
    BO dau crop (ca `crop_ti_le` cu lan `crop_trace` moi) vi ban cat ghi dau crop cua
    rieng no — chep ca dau cu thi mot anh mang hai dau crop."""
    raw = getattr(img, "text", None) or {}      # chi text chunk that, khong phai img.info
    return {k: v for k, v in read_text(img, raw).items() if k != CROP_TRACE_KEY and isinstance(v, str)}


def _new_crop_token(tok: str) -> str:
    k, sep, v = tok.partition("=")
    return f"{LEGACY_CROP_TOKENS.get(k, k)}{sep}{v}"


def parse_crop_trace(s) -> dict:
    """"original=WxH;ratio=4:5;..." (hoac ban cu "goc=WxH;ti_le=...;cat_ngang=1") -> dict ten moi."""
    ra = {}
    for tok in str(s or "").split(";"):
        k, sep, v = tok.partition("=")
        if sep:
            ra[LEGACY_CROP_TOKENS.get(k.strip(), k.strip())] = v.strip()
    return ra


def provenance(img):
    """Gia tri `provenance` da quy ve ten moi, hoac None."""
    return read_text(img).get(PROVENANCE_KEY)


def read_crop_trace(img):
    """Dau vet crop_ratio.py -> (w_goc, h_goc), hoac None."""
    m = read_text(img).get(CROP_TRACE_KEY)
    if not m:
        return None
    try:
        w, h = parse_crop_trace(m)["original"].lower().split("x")
        return int(w), int(h)
    except Exception:
        return None


def allows_landscape_crop(img):
    """crop_ratio.py co duoc phep cat BE NGANG tam nay khong (co --cat-ngang)?

    Day la mot UY QUYEN da ghi lai luc cat, tuong duong `crop_ok` khai trong
    spec — chi khac la no duoc dong dau ngay tai cho cat nen khong khai lai
    duoc. `check_crop_landscape` (moi module luat) nhan ca hai."""
    return parse_crop_trace(read_text(img).get(CROP_TRACE_KEY, "")).get("landscape_crop") == "1"


def is_ranking_image(img):
    """Anh do ranking.py dung: bang xep hang chup tu nguon (co khoanh model) hoac
    the du phong. Voi tin xep hang thi DAY LA CHU THE cua tin (Ong Chu 06/09/2026),
    nen no duoc mien hai cong von cam chart len bia/hero."""
    return provenance(img) in ("ranking_capture", "ranking_card")


def is_logo_card(img):
    """The logo chinh thuc cua hang do `image_brand.card_logo` dung tu Wikidata P154.
    Cung mot hang thi MOI bai deu dung lai dung tam do (md5 y het) — logo lap giua
    cac bai ve cung hang la binh thuong, khac anh su kien, nen duoc mien luat
    "khong dung lai anh da dung" (Ong Chu 20/09/2026, LOW-264 bo sung)."""
    return provenance(img) == "logo_card"


def is_source_capture(img):
    """Anh chup trang nguon cua chinh tin (`capture_page.frame_source_capture`,
    LOW-336): ti le tu nhien, KHONG dem. Renderer dan full be ngang tren nen la
    chinh no lam mo, nen no duoc mien cong ti le 4:5..1:1 va khong duoc cover-crop."""
    return provenance(img) == "source_capture"


def is_stacked_composite(img):
    """Anh nay co phai ban GHEP DOC do doi dung ra khong."""
    return provenance(img) == "vertical_stack"


# ---- So "anh da dung" — THUAN I/O, dung CHUNG ca ba vai theo thiet ke -------
#
# `state/<brand>/used_images.jsonl` la MOT tep dung chung co y: cung mot tin co
# the giao cho Dre roi Ethan ra HAI draft_id khac nhau (`story_key`), va ca hai
# phai thay duoc anh nhau da dung — tach tep nay theo vai se lam vai nop sau
# khong biet vai truoc da dung anh nao, dung cai bug 06/09/2026 tung xay ra
# (Ethan mat toan bo 5-6 ma Dre da dung, khong nop duoc). Khong co nguong/phan
# doan nao o day — ba module luat (`image_rules_<vai>.py`) tu tinh `dhash`/
# `is_near_duplicate` cua RIENG minh roi ghi/doc qua ba ham nay.
def _used_images_log():
    """state/<brand>/used_images.jsonl — moi dong mot anh da GUI DI (khong phai
    ung vien). Ghi o buoc gui album, doc o buoc nop."""
    import env_load
    import state_paths
    return env_load.state_dir() / state_paths.USED_IMAGES_FILE


def story_key(link: str) -> str:
    """Khoa on dinh cua MOT TIN (khong phai mot draft).

    Cung mot tin giao cho Dre roi giao cho Ethan ra HAI draft_id khac nhau
    (approve_pick._draft_id ghep them vai-brand) nhung van la MOT tin va dung
    CHUNG bo anh engine tai ve. So "anh da dung" khoa theo draft thi vai nop sau
    bi chan sach anh cua vai truoc — do 06/09/2026: Ethan mat toan bo 5-6 ma Dre
    da dung, khong nop duoc the nao."""
    import re as _re
    u = _re.sub(r"^https?://(www\.)?", "", (link or "").strip().lower()).rstrip("/")
    return _re.sub(r"[?#].*$", "", u)


def remove_used_for_draft(draft_id: str) -> int:
    """Go moi dong cua mot draft khoi so "anh da dung". Tra so dong da go.

    So duoc ghi o buoc GUI album, tuc TRUOC khi Ong Chu bam nut. Bam "Bo han
    tin" hay "Lam lai" thi bai chet / album bi thay, anh KHONG bao gio len
    kenh — nhung truoc 06/09/2026 chung van nam trong so va chan moi bai khac
    suot 14 ngay. Voi cac tin cung chu de (cung anh wire Reuters/AP, cung anh
    tru so hang) thi bai sau bi day sang anh kem hon, hoac tac han neu tam bi
    khoa la anh that duy nhat — ma thong bao chan chi noi ten bai va cham, KHONG
    noi bai do da bi bo.
    """
    import json
    used_log = _used_images_log()
    if not used_log.exists():
        return 0
    dong = used_log.read_text(encoding="utf-8").splitlines()
    giu = []
    for d in dong:
        try:
            giu.append(d) if json.loads(d).get("draft_id") != draft_id else None
        except Exception:                                    # noqa: BLE001
            giu.append(d)                                    # dong hong: giu nguyen
    if len(giu) == len(dong):
        return 0
    tmp = used_log.with_suffix(".jsonl.tmp")
    tmp.write_text(("\n".join(giu) + "\n") if giu else "", encoding="utf-8")
    tmp.replace(used_log)
    return len(dong) - len(giu)
