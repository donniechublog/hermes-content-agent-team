#!/usr/bin/env python3
"""NẤC CUỐI, KHÔNG BAO GIỜ RỖNG: ảnh của chính các THỰC THỂ trong tiêu đề.

Ông Chủ 12/09/2026, đóng LOW-35 ("đường lùi khi 0 ảnh đạt"): *"ko có lý gì mà
ko tìm được ảnh minh hoạ đâu, đây là 2026, mọi thứ bạn cần đều có sẵn"*. Tức
không có đường lùi nào cả — thang ảnh kết thúc rỗng là LỖI CỦA THANG, không phải
của thế giới. Nấc này bảo đảm thang không rỗng, bằng hai nguồn chưa ai nối:

  1. Wikipedia `pageimages`: ảnh đại diện của BÀI về thực thể (hãng, model,
     người, sự kiện) — Anthropic ra 2865x2952 (đo 12/09). Khác search tên tệp
     Commons: đây là ảnh mà cộng đồng đã CHỌN làm đại diện cho thực thể đó.
  2. Commons full-text theo CỤM tên riêng (`_co_cum`, LOW-36) — mở rộng cái đã
     làm cho tên người sang mọi cụm viết hoa trong tiêu đề và tên model.

Đo trước khi viết: pageimages KHÔNG phải lúc nào cũng có (DeepSeek, "Claude
(AI)", "Age verification" trả rỗng; Paul Erdős chỉ 324x430) — nên cần cả hai,
và cả hai vẫn qua `phan_loai` + con mắt như mọi ảnh khác. Thuần phần lọc để
test được; mạng chỉ ở `pageimages` và `_hoi_commons`.
"""
import re
import sys

import env_load

WIKI_API = "https://en.wikipedia.org/w/api.php"
SHORT_SIDE_MIN = 700
MAX_ENTITY = 4          # cum ten rieng thu, tinh ca ten model
MAX_NEW_ENTITY = 2      # anh moi thuc the tu Commons


def entity_within_title(tieu_de: str, models: list | None = None) -> list:
    """Các cụm tên riêng (viết hoa liên tiếp) + tên model, bỏ trùng, giữ thứ tự."""
    from prepare.source import _leading_proper_noun
    import article_sources
    ra = []
    t = article_sources.strip_site_suffix(re.sub(r"^\[[^\]]{1,20}\]\s*", "", tieu_de or ""))
    ws = re.sub(r"[\$;:,\"'()\[\]|]", " ", t).split()
    i = 0
    while i < len(ws):
        w = ws[i]
        if w[:1].isupper() and w.isalpha() and len(w) >= 3 and w.lower() not in article_sources.FROM_EMPTY_QUERY:
            cum = [w]
            j = i + 1
            while j < len(ws) and j < i + 3 and ws[j][:1].isupper() and ws[j].isalpha():
                cum.append(ws[j]); j += 1
            c = " ".join(cum)
            if c not in ra:
                ra.append(c)
            i = j
        else:
            i += 1
    for m in (models or []):
        if m and m not in ra:
            ra.insert(0, m)
    dau = _leading_proper_noun(tieu_de)
    if dau and dau not in ra:
        ra.insert(0, dau)
    # MOT TU viet hoa dung mot minh ("Claude", "Flash", "Mathematicians") la bay
    # dong am — do that 12/09: "Claude" tren Commons ra tranh Claude Lorrain. Chi
    # giu tu don khi no la TEN HANG da biet (anh_thuong_hieu.TEN_HIEN); cum >= 2
    # tu thi giu (co `_co_cum` lam bien).
    import image_brand as th
    ra = [c for c in ra if len(c.split()) >= 2 or c.lower() in th.DISPLAY_NAME]
    return ra[:MAX_ENTITY]


def pageimages(ten: str) -> dict | None:
    """Ảnh đại diện của bài Wikipedia gần nhất với `ten`. None khi không có/hỏng."""
    import httpx
    try:
        r = httpx.get(WIKI_API, params={
            "action": "query", "generator": "search", "gsrsearch": ten, "gsrlimit": 1,
            "prop": "pageimages", "piprop": "original", "format": "json"},
            headers={"User-Agent": env_load.UA_WIKI}, timeout=20)
        r.raise_for_status()
        pg = next(iter(r.json().get("query", {}).get("pages", {}).values()), {})
    except Exception as e:                                   # noqa: BLE001
        print(f"[thuc_the] wikipedia {ten!r}: {type(e).__name__}", file=sys.stderr)
        return None
    o = pg.get("original") or {}
    if not o.get("source") or min(o.get("width", 0), o.get("height", 0)) < SHORT_SIDE_MIN:
        return None
    return {"anh": o["source"], "alt": f"Wikipedia: {pg.get('title', ten)}", "og": False,
            "tu": "thuc_the", "rong": o["width"], "cao": o["height"],
            "trang": "https://en.wikipedia.org/wiki/" + str(pg.get("title", ten)).replace(" ", "_"),
            "diem": 27, "thuc_the": {"ten": ten, "bai": pg.get("title", ten), "nguon": "wikipedia"}}


def commons_by_phrase(ten: str, so: int = MAX_NEW_ENTITY) -> list:
    """Commons full-text theo CỤM tên riêng, lọc `_co_cum` như LOW-36 (liền nhau,
    đúng thứ tự, biên giới từ) — không phải mỗi từ có mặt đâu đó."""
    import image_concept
    import image_brand as th
    pages = th._ask_commons(f'"{ten}"')
    if not pages:
        return []
    dt = th._from_distinctive(ten)
    ra = []
    for pg in pages.values():
        ii = (pg.get("imageinfo") or [{}])[0]
        w, h = ii.get("width", 0), ii.get("height", 0)
        if min(w, h) < SHORT_SIDE_MIN or ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        tep = (pg.get("title") or "").replace("File:", "")
        thap = tep.lower()
        if image_concept.NAME_TYPE.search(thap) or not th._has_phrase(dt, thap):
            continue
        ra.append({"anh": ii.get("thumburl") or ii.get("url"), "alt": "Commons: " + tep,
                   "og": False, "mime": ii.get("mime"), "tu": "thuc_the", "rong": w, "cao": h,
                   "trang": "https://commons.wikimedia.org/wiki/File:" + tep.replace(" ", "_"),
                   "diem": 25, "thuc_the": {"ten": ten, "nguon": "commons"}})
        if len(ra) >= so:
            break
    ra.sort(key=lambda c: (c["rong"] < c["cao"], -(c["rong"] * c["cao"])))   # ngang truoc
    return ra


def entity_images(tieu_de: str, models: list | None = None) -> list:
    """Ứng viên cho mọi thực thể trong tiêu đề: Wikipedia trước (ảnh đã được
    chọn làm đại diện), rồi Commons theo cụm. Không bao giờ ném."""
    ra, da = [], set()
    for ten in entity_within_title(tieu_de, models):
        for c in ([pageimages(ten)] if True else []) + commons_by_phrase(ten):
            if c and c["anh"] not in da:
                da.add(c["anh"])
                ra.append(c)
    return ra


def label_entity(a: dict) -> dict:
    """Nhãn brief: ảnh đại diện của thực thể, KHÔNG phải ảnh của sự việc; bìa/bối
    cảnh, đừng gán cho slide số liệu. Thuần."""
    tt = a.get("thuc_the") or {}
    if a.get("lien_quan") is False:
        return a
    a["ghi_chu"] = [g for g in a.get("ghi_chu", []) if "Wikimedia Commons" not in g]
    a["ghi_chu"].insert(0, (f"🧩 ẢNH THỰC THỂ \"{tt.get('ten', '?')}\" — ảnh đại diện từ "
                            f"{'bài Wikipedia ' + repr(tt.get('bai', '')) if tt.get('nguon') == 'wikipedia' else 'Commons'}; "
                            "ảnh CỦA THỰC THỂ trong tin, không phải ảnh của sự việc: hợp bìa/bối cảnh, "
                            "caption ghi tên thực thể · via Wikimedia Commons"))
    return a
