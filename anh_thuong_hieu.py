#!/usr/bin/env python3
"""Ảnh THƯƠNG HIỆU — tin về hãng lớn mà kho ảnh mỏng thì engine đi tìm ảnh THẬT
của chính hãng đó trên Wikimedia Commons: trụ sở, campus, biển hiệu, nhà máy,
gian hàng, sản phẩm.

Vì sao có tệp này (Ông Chủ 09/09/2026): *"Dre vẫn chưa tự tìm thêm hình liên quan
khi làm các nội dung có Big Brand"*. Sáng 09/09 năm tin liên tiếp — Qualcomm ×
Amazon, xưởng Samsung, kiện tập thể Anthropic, DeepSeek gọi vốn, Philippines rót
34 tỷ — đều dừng ở cùng một câu hỏi đẩy sang Ông Chủ: *"chỉ 2/5 ảnh thật dùng
được, chọn đường: Kite vẽ vector / Dre làm với 2 ảnh"*. Toàn hãng mà Commons có
hàng trăm ảnh thật.

Chỗ hụt nằm ở ENGINE chứ không ở vai (từ 04/09 vai không còn công cụ tìm ảnh):
`anh_chuan_bi.anh_commons` chỉ tìm theo MỘT cụm — cụm tên riêng ĐẦU tiêu đề
(`_ten_rieng_dau`) — nên tin "Qualcomm ... with Amazon" không bao giờ hỏi tới
Amazon; và nó hỏi bằng đúng tên trần ("Qualcomm"), không hỏi thẳng cái mà hãng
nào cũng có ảnh: trụ sở / toà nhà / campus.

Khác `anh_khai_niem.py` ở CHỖ ĐỨNG, không chỉ ở từ khoá. Ảnh khái niệm (cờ Nhật,
rack datacenter) là ảnh MINH HOẠ chủ đề: chỉ được làm bìa, và cả chùm chỉ đếm là
MỘT khi xét đủ/thiếu. Ảnh thương hiệu là ảnh thật CỦA CHÍNH hãng đang nói trong
bài — đúng loại "trụ sở/sản phẩm" mà LUAT_ANH §1.2 vẫn kể là ảnh liên quan — nên
nó vào được slide thân và đếm đủ. Thứ tự vì thế là: ảnh riêng của tin → ảnh
thương hiệu → ảnh khái niệm.

BỐN LOẠI TƯ LIỆU, theo độ "là ảnh chụp thật của hãng" giảm dần (Ông Chủ
09/09/2026: *"ko thấy ảnh liên quan thì lấy ảnh logo, ảnh founder, ảnh chụp trên
các bảng xếp hạng của model... có thiếu tư liệu đâu?"*):

  1. 🏢 **cơ sở**   — trụ sở/campus: tìm tên tệp Commons + `P18` của Wikidata.
  2. 👤 **chân dung** — founder/CEO (`P112`/`P169` -> `P18` của họ). Đi KÈM TÊN,
     nên khai được `nhan_vat` — đúng ngoại lệ của LUAT_ANH §6.
  3. 📊 **bảng xếp hạng** — `anh_chuan_bi._xep_hang_boi_canh` mượn `xep_hang.py`
     chụp bảng có model của hãng. Chỉ nhận ảnh chụp thật, không nhận thẻ dự phòng.
  4. 🔖 **thẻ logo** — logo chính thức (`P154`) đặt trên nền trơn. Đường CUỐI.

Vì sao phải qua Wikidata chứ không chỉ tìm tên tệp: hãng thuần phần mềm không có
tệp nào tên "<hãng> headquarters" — mà trụ sở OpenAI trên Commons lại tên
"Pioneer Building, San Francisco", không một chữ "openai" nào. Wikidata trỏ
thẳng tới nó. Và tìm tên tệp thì không đời nào với tới chân dung Dario Amodei.

Hàm thuần (test được, không mạng) + hàm chạm mạng:
  - `hang_trong_tin`   tiêu đề (+ tóm tắt) -> các hãng lớn được nhắc, ≤ 3.
  - `truy_van`         một hãng -> các câu hỏi Commons [(tên, câu)].
  - `loc_commons`      lọc `query.pages` theo tên hãng + bảng nhiễu.
  - `_qid_claim`       bóc người từ claim, BỎ người đã thôi chức (P582).
  - `hang_co_model`    hãng này có model trên bảng xếp hạng không.
  - `cau_hoi_vision`   câu hỏi riêng cho từng loại tư liệu.
  - `nhan_thuong_hieu` siết nhãn của một ảnh đã qua `phan_loai`.
  - `tu_lieu_wikidata` / `url_commons` / `the_logo` / `anh_hang`  (mạng/ảnh).
"""
import re
import sys
from pathlib import Path

import env_load

TOI_DA_HANG = 3            # số hãng lấy trong một tin
TOI_DA_MOI_HANG = 2        # ảnh mỗi hãng — để một bộ không thành album trụ sở
CANH_NGAN_MIN = 700

# Tên đi tìm trên Commons cho từng hãng (khoá = tên hãng chuẩn của
# `scan_business.HANG_CUA_TEN`). Nhiều tên khi tên trên biển hiệu khác tên pháp
# lý (Meta -> Facebook) hoặc khi hãng con nằm trong khuôn viên hãng mẹ
# (DeepMind -> Google). Tên đầu là tên hiện trong brief.
TEN_HIEN = {
    "openai": ("OpenAI",),
    "anthropic": ("Anthropic",),
    "google deepmind": ("Google", "DeepMind"),
    "meta": ("Meta Platforms", "Facebook"),
    "mistral": ("Mistral AI",),
    "cohere": ("Cohere",),
    "perplexity": ("Perplexity AI",),
    "xai": ("xAI",),
    "stability ai": ("Stability AI",),
    "midjourney": ("Midjourney",),
    "runway": ("Runway AI",),
    "hugging face": ("Hugging Face",),
    "black forest": ("Black Forest Labs",),
    "deepseek": ("DeepSeek",),
    "alibaba": ("Alibaba",),
    "bytedance": ("ByteDance",),
    "tencent": ("Tencent",),
    "baidu": ("Baidu",),
    "moonshot": ("Moonshot AI",),
    "zhipu": ("Zhipu AI",),
    "minimax": ("MiniMax",),
    "xiaomi": ("Xiaomi",),
    "01.ai": ("01.AI",),
    "nvidia": ("Nvidia",),
    "apple": ("Apple", "Apple Park"),
    "microsoft": ("Microsoft",),
    "amazon": ("Amazon", "Amazon Web Services"),
    "samsung": ("Samsung",),
    "huawei": ("Huawei",),
    "qualcomm": ("Qualcomm",),
    "intel": ("Intel",),
    "amd": ("AMD",),
    "tsmc": ("TSMC",),
    "arm": ("Arm Holdings",),
    "broadcom": ("Broadcom",),
    "sony": ("Sony",),
    "tesla": ("Tesla",),
    "databricks": ("Databricks",),
    "snowflake": ("Snowflake Inc",),
    "oracle": ("Oracle Corporation",),
    "softbank": ("SoftBank",),
    "lenovo": ("Lenovo",),
}

# WATCHLIST của `scan_business` là danh sách CHỌN TIN: nó giữ "google deepmind",
# "meta ai" — dạng có liên quan AI — chứ không giữ tên trần "Google", "Meta".
# Mà tin thì viết tên trần ("Google, Meta and Nvidia raise AI spending"). Bổ
# sung ở đây, KHÔNG sửa WATCHLIST: thêm "google" bên đó là đổi luật chọn tin,
# mọi tin có chữ google thành tin bắt buộc.
TEN_THEM = {
    "google": "google deepmind", "alphabet": "google deepmind",
    "meta": "meta", "facebook": "meta", "instagram": "meta",
    "azure": "microsoft", "snapdragon": "qualcomm",
}

# Hậu tố hỏi Commons. Chỉ thứ hãng nào cũng có ảnh chụp thật, không hỏi thứ
# trừu tượng (partnership, funding) — Commons trả minh hoạ tệ, xem anh_khai_niem.
HAU_TO = ("headquarters", "building", "campus")
TOI_DA_TRUY_VAN = 4

# Từ CHUNG trong tên công ty: có mặt trong câu hỏi để Commons xếp hạng đúng,
# nhưng KHÔNG được đòi phải có trong tên tệp — "Mistral AI headquarters" mà bắt
# tên tệp chứa "ai" thì không tệp nào qua.
TU_CHUNG_TEN = {"ai", "inc", "labs", "lab", "corp", "corporation", "company",
                "platforms", "holdings", "motors", "technologies", "group",
                "web", "services", "the", "of", "and"}

# Tên hãng trùng một thứ NỔI TIẾNG HƠN chính nó trên Commons. Không có bảng này
# thì "Amazon headquarters" trả rừng Amazon, "Apple" trả quả táo, "Tesla" trả
# Nikola Tesla. Khoá = từ đặc trưng ĐẦU của tên hãng.
NHIEU = {
    "amazon": r"rainforest|rain forest|river|jungle|basin|amazonas|forest|parrot|"
              r"\bfrog\b|tribe|indigenous|peru|ecuador|bolivia|manaus",
    "apple": r"\bfruit\b|orchard|\btree\b|blossom|\bpie\b|juice|cider|\bseed\b|malus|harvest",
    "arm": r"wrestl|anatomy|prosthe|human arm|robotic arm|coat of arms|firearm|\barmy\b|armour",
    "oracle": r"delphi|greek|temple|priestess|ancient|oracle bone|pythia",
    "tesla": r"nikola|\bcoil\b|wardenclyffe|statue|museum|\bunit\b|magnetic",
    "snowflake": r"\bsnow\b|crystal|winter|frost|macro|\bice\b|flake",
    "runway": r"airport|airfield|aircraft|taxiway|landing|takeoff|fashion|catwalk",
    "mistral": r"\bwind\b|amphibious|warship|\bnavy\b|l9013|\bcloud|frigate",
    "meta": r"metadata|\bmetal\b|metamorph",
    "moonshot": r"\bmoon\b|lunar|rocket|apollo|space",
    "minimax": r"algorithm|game tree|\bchess\b",
    "black": r"schwarzwald|\bcake\b|gateau|hiking|\btrees\b|baden",   # Black Forest Labs
    "intel": r"intelligence agency|\bcia\b|\bnsa\b",
}
_NHIEU_BIEN: dict = {}

# Nhiễu CHUNG cho mọi hãng: tên tệp mang đúng tên hãng nhưng ảnh không phải bối
# cảnh của hãng. Đo thật 09/09/2026: câu "Amazon building" trả về hai tấm
# "International Day of Solidarity With Alabama Amazon Workers" — ảnh mít tinh
# công đoàn, đúng chữ "Amazon" mà sai hẳn loại ảnh cho một tin ký hợp đồng chip.
# `TEN_LOAI` của anh_khai_niem có "protest" nhưng tên tệp này không có chữ đó.
# Không đưa "march" vào (trùng tháng Ba) hay "union" trần (trùng Union Square).
NHIEU_CHUNG = re.compile(
    r"solidarity|rall(y|ies)|\bstrikes?\b|striking|picket|protest|demonstrat|"
    r"activis|boycott|walkout|placard|labou?r union|trade union|unioni[sz]", re.I)


def _tu_dac_trung(ten: str) -> list:
    """Các từ trong tên hãng PHẢI có trong tên tệp. Bỏ từ chung (AI, Inc, Labs)."""
    return [w for w in re.findall(r"[a-z0-9.]+", (ten or "").lower())
            if w not in TU_CHUNG_TEN and len(w) >= 2]


def _co_tu(tu: str, vb: str) -> bool:
    """Khớp theo BIÊN GIỚI TỪ: "arm" không được khớp "harm"/"Armstrong", "meta"
    không được khớp "metal", "intel" không được khớp "intelligence"."""
    return bool(re.search(r"(?<!\w)" + re.escape(tu) + r"(?!\w)", vb))


def _nhieu(ten: str):
    """Regex nhiễu của một tên hãng, hoặc None."""
    tu = _tu_dac_trung(ten)
    if not tu or tu[0] not in NHIEU:
        return None
    if tu[0] not in _NHIEU_BIEN:
        _NHIEU_BIEN[tu[0]] = re.compile(NHIEU[tu[0]], re.I)
    return _NHIEU_BIEN[tu[0]]


def hang_trong_tin(tieu_de: str, tom_tat: str = "") -> list:
    """Các hãng lớn tin này nói tới, theo thứ tự xuất hiện, tối đa `TOI_DA_HANG`.

    Dùng chung WATCHLIST của `scan_business` — cùng một danh sách "tên trong
    ngành phải theo sát", không chép lại ở đây. Tên model/chip quy về hãng chủ
    qua HANG_CUA_TEN, nên "Claude Opus 5" ra Anthropic, "Xring O3" ra Xiaomi.
    Trả [{"khoa": "qualcomm", "hang": "Qualcomm"}].
    """
    import scan_business
    vb = f"{tieu_de or ''} {tom_tat or ''}".lower()
    vi_tri = {}
    for ten in list(scan_business.WATCHLIST) + list(TEN_THEM):
        t = ten.strip()
        if len(t) < 3:                       # "yi" một mình bắt cả "yield"
            continue
        m = re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", vb)
        if not m:
            continue
        khoa = TEN_THEM.get(t) or scan_business.HANG_CUA_TEN.get(ten, ten).strip()
        if khoa not in vi_tri or m.start() < vi_tri[khoa]:
            vi_tri[khoa] = m.start()
    ra = [{"khoa": k, "hang": TEN_HIEN.get(k, (k.title(),))[0]}
          for k, _ in sorted(vi_tri.items(), key=lambda kv: kv[1])]
    return ra[:TOI_DA_HANG]


def truy_van(khoa: str) -> list:
    """Câu hỏi Commons cho một hãng: [(tên dùng để lọc, câu hỏi)]. Tên đứng riêng
    vì tên tệp mang tên hãng chứ không mang hậu tố ("Samsung Town Seoul.jpg" ra
    từ câu "Samsung headquarters")."""
    ten = TEN_HIEN.get(khoa, (khoa.title(),))
    ra = []
    for t in ten[:2]:
        for h in HAU_TO:
            ra.append((t, f"{t} {h}"))
    # Tên chính đủ ba hậu tố trước, rồi mới tới tên phụ.
    return ra[:TOI_DA_TRUY_VAN]


def loc_commons(pages: dict, ten: str, so: int = 4, canh_ngan_min: int = CANH_NGAN_MIN) -> list:
    """Lọc `query.pages` của API Commons cho một tên hãng: bitmap đủ lớn, tên tệp
    có ĐỦ các từ đặc trưng của tên hãng (theo biên giới từ), không phải đồ hoạ
    (`anh_khai_niem.TEN_LOAI`), không dính bảng nhiễu. JPEG trước, ảnh to trước."""
    import anh_khai_niem
    dac_trung = _tu_dac_trung(ten)
    nhieu = _nhieu(ten)
    ra = []
    for pg in (pages or {}).values():
        ii = (pg.get("imageinfo") or [{}])[0]
        w, h = ii.get("width", 0), ii.get("height", 0)
        if min(w, h) < canh_ngan_min or ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        ten_tep = (pg.get("title") or "").replace("File:", "")
        thap = ten_tep.lower()
        if anh_khai_niem.TEN_LOAI.search(thap) or NHIEU_CHUNG.search(thap):
            continue
        if not dac_trung or not all(_co_tu(t, thap) for t in dac_trung):
            continue
        if nhieu and nhieu.search(thap):
            continue
        ra.append({"anh": ii.get("thumburl") or ii.get("url"), "alt": "Commons: " + ten_tep,
                   "og": False, "mime": ii.get("mime"), "tu": "thuong_hieu",
                   "trang": "https://commons.wikimedia.org/wiki/File:" + ten_tep.replace(" ", "_"),
                   "rong": w, "cao": h, "diem": 25})
    # JPEG trước PNG: ảnh chụp thật gần như luôn là JPEG (xem anh_khai_niem).
    ra.sort(key=lambda c: (c["mime"] != "image/jpeg", -(c["rong"] * c["cao"])))
    return ra[:so]


# ---- Wikidata: hồ sơ chính thức của hãng ------------------------------------
# Ông Chủ 09/09/2026: *"ko thấy ảnh liên quan thì lấy ảnh logo, ảnh founder, ảnh
# chụp trên các bảng xếp hạng của model... có thiếu tư liệu đâu?"* — đúng, và
# tìm theo TÊN TỆP thì không bao giờ với tới ba thứ đó. Wikidata giữ sẵn hồ sơ
# có cấu trúc của gần như mọi hãng trong watchlist, nên hỏi thẳng nó:
WIKIDATA = "https://www.wikidata.org/w/api.php"
COMMONS = "https://commons.wikimedia.org/w/api.php"
P_ANH, P_LOGO, P_SANG_LAP, P_CEO = "P18", "P154", "P112", "P169"
# Dấu hiệu entity là CÔNG TY chứ không phải khái niệm trùng tên: tìm "Anthropic"
# trên Wikidata trả về cả `anthropic principle` (Q240581, một khái niệm triết
# học). Đòi ít nhất HAI thuộc tính chỉ công ty mới có.
P_CONG_TY = ("P154", "P159", "P452", "P1454", "P571", "P169", "P112", "P1128")
TOI_DA_NGUOI = 2


def _hoi_api(url: str, **kw) -> dict:
    """Gọi Wikidata/Commons API, trả JSON đã parse. None nếu gọi API thất bại
    (lỗi mạng, thiếu dependency, exception ngoài dự kiến) — KHÔNG phải {} rỗng,
    để người gọi phân biệt được với API trả lời hợp lệ nhưng rỗng thật sự."""
    kw.setdefault("format", "json")
    try:
        import httpx
        return httpx.get(url, params=kw, headers={"User-Agent": env_load.UA_WIKI},
                         timeout=20).json()
    except Exception as e:                                   # noqa: BLE001
        print(f"[thuong_hieu] {url.split('//')[-1][:20]}: {type(e).__name__}: {e!r}", file=sys.stderr)
        return None


def _tep_claim(claims: dict, p: str) -> list:
    """Tên tệp Commons trong một thuộc tính ảnh (P18/P154)."""
    ra = []
    for c in (claims or {}).get(p, []):
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(v, str):
            ra.append(v)
    return ra


def _qid_claim(claims: dict, p: str) -> list:
    """Q-id trong một thuộc tính người (P112/P169), BỎ người đã thôi chức.

    Wikidata giữ cả người tiền nhiệm trong P169: hỏi CEO của OpenAI trả về cả
    Sam Altman lẫn Mira Murati (CEO tạm quyền cuối 2023), phân biệt bằng
    *qualifier* P582 "end time" chứ không phải bằng thứ tự. Không lọc thì brief
    ghi "CEO OpenAI: Mira Murati" — sai sự thật, mà vai không có đường nào kiểm
    (09/09/2026). Bậc `deprecated` cũng bỏ."""
    ra = []
    for c in (claims or {}).get(p, []):
        if c.get("rank") == "deprecated" or "P582" in (c.get("qualifiers") or {}):
            continue
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value") or {}
        if isinstance(v, dict) and v.get("id"):
            ra.append(v["id"])
    return ra


def qid_hang(hang: str) -> tuple:
    """(qid, claims) của entity CÔNG TY khớp tên hãng, hoặc (None, {})."""
    r = _hoi_api(WIKIDATA, action="wbsearchentities", search=hang, language="en",
                 type="item", limit=5)
    if r is None:
        print(f"[thuong_hieu] qid_hang({hang!r}): khong goi duoc Wikidata (wbsearchentities), bo qua",
              file=sys.stderr)
        return None, {}
    ids = [x["id"] for x in r.get("search", []) if x.get("id")]
    if not ids:
        return None, {}
    ent = _hoi_api(WIKIDATA, action="wbgetentities", ids="|".join(ids), props="claims")
    if ent is None:
        print(f"[thuong_hieu] qid_hang({hang!r}): khong goi duoc Wikidata (wbgetentities), bo qua",
              file=sys.stderr)
        return None, {}
    ent = ent.get("entities", {})
    for qid in ids:                       # giữ thứ tự xếp hạng của Wikidata
        cl = (ent.get(qid) or {}).get("claims", {})
        if sum(p in cl for p in P_CONG_TY) >= 2:
            return qid, cl
    return None, {}


def tu_lieu_wikidata(hang: str) -> dict:
    """Hồ sơ ảnh của một hãng: {"qid", "anh": [tệp], "logo": [tệp],
    "nguoi": [{"ten","tep","vai"}]}. Không có/hỏng mạng -> {}."""
    qid, cl = qid_hang(hang)
    if not qid:
        return {}
    ra = {"qid": qid, "anh": _tep_claim(cl, P_ANH)[:2], "logo": _tep_claim(cl, P_LOGO)[:1],
          "nguoi": []}
    ceo = _qid_claim(cl, P_CEO)
    ids = list(dict.fromkeys(ceo + _qid_claim(cl, P_SANG_LAP)))[:TOI_DA_NGUOI + 1]
    if ids:
        ent = _hoi_api(WIKIDATA, action="wbgetentities", ids="|".join(ids),
                       props="claims|labels", languages="en")
        if ent is None:
            print(f"[thuong_hieu] tu_lieu_wikidata({hang!r}): khong goi duoc Wikidata "
                  "(nguoi/CEO), bo qua", file=sys.stderr)
            ent = {}
        else:
            ent = ent.get("entities", {})
        for i in ids:
            e = ent.get(i) or {}
            ten = ((e.get("labels") or {}).get("en") or {}).get("value", "")
            tep = _tep_claim(e.get("claims", {}), P_ANH)[:1]
            if ten and tep:
                ra["nguoi"].append({"ten": ten, "tep": tep[0],
                                    "vai": "CEO" if i in ceo else "nhà sáng lập"})
    ra["nguoi"] = ra["nguoi"][:TOI_DA_NGUOI]
    return ra


# ---- Trang CÔNG BỐ chính chủ của model ---------------------------------------
# Ông Chủ 11/09/2026 (LOW-21): *"khi làm carousel từ một topic gốc, phải tìm tất
# cả ảnh liên quan chứ không phải chỉ tìm ảnh trong nguồn topic, đặc biệt là
# những thông tin liên quan tới benchmark của model"* — và *"chỉ cần vào trang
# announce của DeepSeek đã quá nhiều tư liệu và hình ảnh"*. Đo thật: trang
# deepseek.com/en/news/deepseek-v4-1-flash/ có 4 chart benchmark 5148×2640…,
# nhưng Google News không index nó và 13/14 báo không link sang, nên engine
# không có đường nào tới. Đường ở đây: Wikidata P856 (website chính thức) ->
# trang danh sách tin của hãng -> khớp tên model (đã tách bằng
# xep_hang.tach_model) trong slug link. Chỉ mạng tĩnh, ≤ 1 + len(DUONG_TIN) fetch.
P_WEBSITE = "P856"
DUONG_TIN = ("/news/", "/en/news/", "/blog/", "/news", "/blog", "/research/")
# Trang HTML bị chặn bot (openai.com trả 0 byte cho httpx, đo 11/09/2026) thì
# RSS công khai vẫn mở — cùng bài học với `nguon_bai._tieu_de_rss` (Economist).
DUONG_FEED = ("/news/rss.xml", "/rss.xml", "/blog/rss.xml", "/blog/feed.xml", "/feed.xml")
TOI_DA_TRANG_CONG_BO = 1


def _slug(t: str) -> str:
    """'DeepSeek-V4.1-Flash' -> 'deepseek-v4-1-flash' — cùng cách hãng đặt slug URL."""
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", (t or "").lower())).strip("-")


def _khoa_model(models: list) -> list:
    """Các khoá slug để khớp link, DÀI trước NGẮN sau, bỏ hậu tố effort/thinking
    (`-max`, `-high`…: trang công bố đặt tên model, không đặt tên biến thể effort).
    Khoá ngắn nhất phải còn ≥ 2 mảnh (`deepseek-v4`), tránh khớp mọi bài của hãng."""
    ra = []
    for m in models or []:
        s = _slug(m)
        s = re.sub(r"-(max|high|xhigh|low|medium|thinking|effort)$", "", s)
        while s.count("-") >= 1:
            if s not in ra:
                ra.append(s)
            s = s.rsplit("-", 1)[0]
    return ra


def website_hang(hang: str) -> str:
    """Website chính thức của hãng theo Wikidata P856, hoặc ''."""
    _, cl = qid_hang(hang)
    for c in (cl or {}).get(P_WEBSITE, []):
        if c.get("rank") == "deprecated":
            continue
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(v, str) and v.startswith("http"):
            return v.rstrip("/")
    return ""


def _tai_html(url: str, timeout: int = 15, feed: bool = False) -> str:
    """HTML (hoặc RSS khi `feed`) của một trang, UA trình duyệt — trang hãng hay
    chặn UA bot. '' nếu hỏng hay sai loại nội dung."""
    import httpx
    import quet_chung
    try:
        quet_chung.kiem_url(url)
        r = httpx.get(url, headers={"User-Agent": env_load.UA_TRINH_DUYET,
                                    "Accept-Encoding": "gzip, deflate"},
                      timeout=timeout, follow_redirects=True)
        loai = r.headers.get("content-type", "")
        if r.status_code == 200 and (("xml" in loai or "rss" in loai) if feed else "html" in loai):
            return r.text[:400_000]
    except Exception as e:                                   # noqa: BLE001
        print(f"[cong bo] {url[:60]}: {type(e).__name__}", file=sys.stderr)
    return ""


def trang_cong_bo(hang: dict, models: list) -> dict | None:
    """Trang công bố CHÍNH CHỦ của model trong tin: {"url", "tieu_de", "toa_soan"}
    hoặc None. `hang` là một mục của `hang_trong_tin`, `models` từ
    `xep_hang.tach_model`. Không hỏi gì khi thiếu một trong hai."""
    from urllib.parse import urljoin
    khoa = _khoa_model(models)
    if not hang or not khoa:
        return None
    site = website_hang(hang.get("hang") or hang.get("khoa", ""))
    if not site:
        print(f"[cong bo] {hang.get('hang')}: Wikidata khong co website (P856)", file=sys.stderr)
        return None
    mien = re.sub(r"^https?://(www\.)?", "", site).lower()
    for duong in DUONG_TIN + DUONG_FEED:
        la_feed = duong in DUONG_FEED
        html = _tai_html(site + duong, feed=la_feed)
        if not html:
            continue
        links = []
        # Chỉ <a href> (HTML) hoặc <link> (RSS): <link rel=preload href=…cover.webp>
        # cũng mang slug model (đo 11/09: bắt nhầm ảnh bìa thay vì bài). Bỏ luôn
        # URL có đuôi tệp.
        mau = r"<link>\s*([^<\s]+)\s*</link>" if la_feed else r"""<a\s[^>]*?href=["']([^"'#?]+)"""
        for m in re.finditer(mau, html, re.I):
            u = urljoin(site + duong, m.group(1).rstrip("\\"))
            if mien in u.lower() and u not in links \
                    and not re.search(r"\.(png|jpe?g|webp|gif|svg|pdf|css|js|xml)$", u, re.I):
                links.append(u)
        for k in khoa:                              # khoá dài (đúng model) thắng khoá ngắn
            # Khớp trên ĐƯỜNG DẪN (bỏ scheme + host): '/en/news/deepseek-v4-1-flash/'
            trung = [u for u in links if k in _slug(re.sub(r"^https?://[^/]+", "", u))]
            if trung:
                u = trung[0]
                print(f"[cong bo] {hang.get('hang')}: {u} (khop '{k}' o {duong})", file=sys.stderr)
                return {"url": u, "loai": "công bố", "tieu_de": "", "toa_soan": site}
    print(f"[cong bo] {hang.get('hang')}: khong thay bai nao khop {khoa[:2]} tren {site}",
          file=sys.stderr)
    return None


def url_commons(tens: list) -> dict:
    """Tên tệp Commons -> {url, rong, cao, mime}. Hỏi một lượt. SVG được Commons
    render sẵn ra PNG ở `thumburl`, nên logo vector cũng dùng được."""
    tens = [t for t in tens if t]
    if not tens:
        return {}
    r = _hoi_api(COMMONS, action="query", titles="|".join("File:" + t for t in tens),
                 prop="imageinfo", iiprop="url|size|mime", iiurlwidth=1800)
    if r is None:
        print("[thuong_hieu] url_commons: khong goi duoc Commons API, bo qua", file=sys.stderr)
        return {}
    ra = {}
    for pg in ((r.get("query") or {}).get("pages") or {}).values():
        ii = (pg.get("imageinfo") or [{}])[0]
        ten = (pg.get("title") or "").replace("File:", "")
        u = ii.get("thumburl") or ii.get("url")
        if u:
            ra[ten] = {"url": u, "rong": ii.get("thumbwidth") or ii.get("width", 0),
                       "cao": ii.get("thumbheight") or ii.get("height", 0),
                       "mime": ii.get("mime")}
    return ra


def the_logo(tep_logo, out, brand: str = "donniechublog"):
    """Đặt LOGO THẬT của hãng lên nền thương hiệu, dồn lên NỬA TRÊN để hook đè
    được nửa dưới. Không phải minh hoạ — cùng nguyên tắc với thẻ dự phòng của
    `xep_hang.the_du_phong`: không thêm một nét nào của ta, chỉ là chỗ đặt.

    Logo Commons hay là PNG trong suốt / SVG render nền trong; dán thẳng lên nền
    tối thì chữ đen của wordmark biến mất, nên nền được chọn theo độ sáng của
    chính logo."""
    import card
    from PIL import Image
    card.dat_thuong_hieu(brand)
    w, h = 1200, 1500
    lg = Image.open(tep_logo)
    lg = lg.convert("RGBA") if lg.mode in ("RGBA", "LA", "P") else lg.convert("RGB")
    # Độ sáng phần KHÔNG trong suốt: logo chữ đen -> nền sáng, logo chữ trắng -> nền tối.
    px = lg.convert("RGBA")
    sang = _do_sang_logo(px)
    nen = (245, 245, 245) if sang < 110 else card.BG
    im = Image.new("RGB", (w, h), nen)
    rong = int(w * 0.62)
    cao = max(1, round(lg.height * rong / lg.width))
    if cao > h * 0.30:                       # logo dọc: khớp theo chiều cao
        cao = int(h * 0.30)
        rong = max(1, round(lg.width * cao / lg.height))
    lg = lg.resize((rong, cao), Image.LANCZOS)
    hop = ((w - rong) // 2, int(h * 0.30) - cao // 2)
    im.paste(lg, hop, lg if lg.mode == "RGBA" else None)
    import luat_anh
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PNG", pnginfo=luat_anh.dong_dau("the_logo"))
    return out, ("sáng" if sang < 110 else "tối")


def _do_sang_logo(px) -> float:
    """Độ sáng trung bình của phần ĐỤC trong logo (bỏ vùng trong suốt)."""
    L = px.convert("L")
    a = px.getchannel("A")
    tong = so = 0
    for lum, alpha in zip(L.getdata(), a.getdata()):
        if alpha > 128:
            tong += lum
            so += 1
    return (tong / so) if so else 128.0


def anh_wikidata(hang, wd=None) -> list:
    """Ứng viên từ hồ sơ Wikidata: ảnh công ty (P18) -> người sáng lập/CEO (P18
    của họ, KÈM TÊN để khai `nhan_vat`) -> logo (P154, dựng thành thẻ).

    Ảnh công ty của Wikidata với tới thứ mà tìm theo tên tệp không với được:
    trụ sở OpenAI trên Commons tên là "Pioneer Building, San Francisco" — không
    có chữ "openai" nào trong tên tệp (09/09/2026)."""
    khoa = hang["khoa"] if isinstance(hang, dict) else hang
    ten_chinh = TEN_HIEN.get(khoa, (khoa.title(),))[0]
    tl = tu_lieu_wikidata(ten_chinh)
    if not tl:
        return []
    can = list(tl["anh"]) + [n["tep"] for n in tl["nguoi"]] + list(tl["logo"])
    thong = url_commons(can)
    ra = []
    for t in tl["anh"]:
        u = thong.get(t)
        if u and min(u["rong"], u["cao"]) >= CANH_NGAN_MIN:
            ra.append(_ung_vien(u, t, ten_chinh, khoa, "anh", "ảnh công ty (Wikidata P18)"))
    for n in tl["nguoi"]:
        u = thong.get(n["tep"])
        if u and min(u["rong"], u["cao"]) >= 500:
            c = _ung_vien(u, n["tep"], ten_chinh, khoa, "nguoi",
                          f"{n['vai']} {ten_chinh} (Wikidata)")
            c["thuong_hieu"]["nguoi"] = n["ten"]
            c["thuong_hieu"]["vai"] = n["vai"]
            c["alt"] = f"Commons: {n['ten']} — {n['vai']} {ten_chinh}"
            ra.append(c)
        # BAT ANH NGANG cua chinh nguoi nay tren Commons (Ong Chu 12/09/2026:
        # "chỉ cần search claude hay anthropic thì cũng ra một rừng ảnh rồi").
        # Wikidata P18 chi giu DUNG MOT anh (thuong la chan dung studio, doc) —
        # chua bao gio hoi Commons theo TEN NGUOI. Do that 12/09: search "Dario
        # Amodei" ra 9 anh su kien/hop bao 4000x2667..8192x5464, ti le 1.5, ma
        # pipeline chua bao gio cham toi vi HAU_TO chi khop "headquarters/
        # building/campus". Ten day du it dung hang nhu ten hang (khong nhu
        # "Anthropic" trung khao co, "Claude" trung hoi hoa) nen dung lai
        # `_tu_dac_trung`/`_co_tu` cua chinh module nay, khong can bang NHIEU.
        for c in anh_nguoi_ngang(n["ten"], n["vai"], ten_chinh, khoa):
            ra.append(c)
    for t in tl["logo"]:
        u = thong.get(t)
        if not u or not wd:
            continue
        try:
            goc = Path(wd) / "logo_goc.png"
            goc.parent.mkdir(parents=True, exist_ok=True)
            import httpx
            goc.write_bytes(httpx.get(u["url"], headers={"User-Agent": env_load.UA_WIKI},
                                      timeout=30, follow_redirects=True).content)
            the, nen = the_logo(goc, Path(wd) / "the_logo.png", env_load.brand_dai())
        except Exception as e:                               # noqa: BLE001
            print(f"[thuong_hieu] the logo hong: {type(e).__name__}", file=sys.stderr)
            continue
        c = _ung_vien(u, t, ten_chinh, khoa, "logo", "logo chính thức (Wikidata P154)")
        c["thuong_hieu"]["nen"] = nen
        c.update({"tep": str(the), "anh": str(the), "cho_do_hoa": True})
        ra.append(c)
    return ra


def _ung_vien(u: dict, ten_tep: str, hang: str, khoa: str, loai: str, ly_do: str) -> dict:
    return {"anh": u["url"], "alt": "Commons: " + ten_tep, "og": False, "mime": u.get("mime"),
            "tu": "thuong_hieu", "rong": u["rong"], "cao": u["cao"],
            "trang": "https://commons.wikimedia.org/wiki/File:" + ten_tep.replace(" ", "_"),
            "diem": {"anh": 28, "nguoi": 24, "logo": 18}.get(loai, 20),
            "thuong_hieu": {"hang": hang, "khoa": khoa, "loai": loai, "tu_khoa": ly_do}}


TOI_DA_NGUOI_NGANG = 2   # tran anh ngang moi nguoi — tranh mot CEO chiem het luot


def anh_nguoi_ngang(ten: str, vai: str, hang: str, khoa: str) -> list:
    """Ảnh NGANG của chính người này trên Commons (họp báo, sự kiện, phỏng vấn)
    — KHÁC ảnh chân dung studio duy nhất mà Wikidata P18 giữ.

    Ông Chủ 12/09/2026: *"chỉ cần search claude hay anthropic thì cũng ra một
    rừng ảnh rồi, kiếm cái ảnh rõ nét và ratio phù hợp khó thế sao?"* — đúng, đo
    thật: search "Dario Amodei" ra 9 ảnh họp báo/sự kiện 4000x2667..8192x5464,
    tỉ lệ 1,5 (ngang), mà `anh_wikidata` trước đây CHƯA BAO GIỜ hỏi Commons theo
    TÊN NGƯỜI — chỉ lấy đúng một ảnh P18 (thường là chân dung studio, dọc).

    Search "Anthropic"/"Claude AI" một mình thì nhiễu thật (khảo cổ, hội hoạ,
    từ điển — xem `NHIEU`), nhưng TÊN NGƯỜI ĐẦY ĐỦ hiếm khi trùng nghĩa khác;
    dùng lại đúng `_tu_dac_trung`/_co_tu` đã có cho tên hãng: lọc CẢ hai từ của
    tên phải khớp tên tệp theo biên giới từ. Vẫn cùng cổng LUAT_ANH §6 với chân
    dung (khai `nhan_vat`) — chỉ khác đủ ngang để không teo khi lên bìa."""
    import anh_khai_niem
    pages = _hoi_commons(f'"{ten}"')
    if pages is None:
        return []
    dac_trung = _tu_dac_trung(ten)
    ra = []
    for pg in pages.values():
        ii = (pg.get("imageinfo") or [{}])[0]
        w, h = ii.get("width", 0), ii.get("height", 0)
        if min(w, h) < CANH_NGAN_MIN or w < h:            # doc/vuong hep -> bo, day la
            continue                                       # duong rieng cho "ti le phu hop"
        if ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        ten_tep = (pg.get("title") or "").replace("File:", "")
        thap = ten_tep.lower()
        if anh_khai_niem.TEN_LOAI.search(thap) or not all(_co_tu(t, thap) for t in dac_trung):
            continue
        c = _ung_vien({"url": ii.get("thumburl") or ii.get("url"), "rong": w, "cao": h,
                       "mime": ii.get("mime")}, ten_tep, hang, khoa, "nguoi",
                      f"{vai} {hang}, ảnh ngang (Commons)")
        c["diem"] = 26     # giua "anh" cong ty/san pham (28) va chan dung doc (24):
                           # van la mot nguoi, nhung du ngang de khong can crop nat
        c["thuong_hieu"]["nguoi"] = ten
        c["thuong_hieu"]["vai"] = vai
        c["alt"] = f"Commons: {ten} — {vai} {hang}, ảnh ngang"
        ra.append(c)
        if len(ra) >= TOI_DA_NGUOI_NGANG:
            break
    return ra


def anh_hang(hang, so: int = TOI_DA_MOI_HANG, wd=None) -> list:
    """Ứng viên ảnh thương hiệu cho một hãng ({"khoa","hang"} hoặc khoá).

    Hai đường, theo độ "là ảnh chụp thật của hãng" giảm dần:
      1. tìm tên tệp trên Commons: `"<Hãng> headquarters/building/campus"`;
      2. hồ sơ Wikidata: ảnh công ty -> founder/CEO (kèm tên) -> logo.
    Đường 2 chạy khi đường 1 chưa đủ `so` — hãng thuần phần mềm (Anthropic,
    DeepSeek) không có ảnh trụ sở nào trên Commons, và đó chính là loại tin hay
    bị dừng ở nút "chỉ 2/5 ảnh". Hỏng mạng -> []."""
    khoa = hang["khoa"] if isinstance(hang, dict) else hang
    ten_chinh = TEN_HIEN.get(khoa, (khoa.title(),))[0]
    ra, da, hong = [], set(), 0
    for ten, cau in truy_van(khoa):
        if len(ra) >= so:
            break
        pages = _hoi_commons(cau)
        if pages is None:                    # hong moi truong, KHONG phai "khong co anh"
            hong += 1
            continue
        for c in loc_commons(pages, ten, so=so):
            if c["anh"] in da:
                continue
            da.add(c["anh"])
            c["thuong_hieu"] = {"hang": ten_chinh, "khoa": khoa, "loai": "anh", "tu_khoa": cau}
            ra.append(c)
            if len(ra) >= so:
                break
    if hong and not ra:
        # ADF-r2-16: truoc day {} cua _hoi_commons di thang vao loc_commons nen
        # mat mang == hang khong co anh. Giu hop dong tra [] cua ham, nhung noi
        # ro de brief/nhat ky khong ket luan sai ve hang.
        print(f"[thuong_hieu] {khoa}: {hong} truy van Commons HONG (mang/API) — "
              "khong phai hang khong co anh", file=sys.stderr)
    if len(ra) < so:
        for c in anh_wikidata(hang, wd):
            if c["anh"] not in da:
                da.add(c["anh"])
                ra.append(c)
    return ra


def hang_co_model(khoa: str) -> bool:
    """Hãng này có model nằm trên bảng xếp hạng không — mới đáng mở browser đi
    chụp bảng. Qualcomm/TSMC không làm LLM nên không bao giờ khớp hàng nào."""
    import scan_business
    return khoa in set(scan_business.HANG_CUA_TEN.values()) | {
        "openai", "anthropic", "deepseek", "mistral", "xai", "cohere", "moonshot",
        "zhipu", "minimax", "01.ai", "stability ai", "black forest", "midjourney",
        "perplexity", "nvidia", "microsoft", "amazon", "meta", "google deepmind"}


def cau_hoi_vision(tieu_de: str, th: dict) -> str:
    """Câu hỏi riêng cho ảnh thương hiệu. Câu chung hỏi "có phải ảnh của tin
    không" — chân dung nhà sáng lập và logo chắc chắn không phải, nên bị đánh
    rớt dù đó đúng là thứ ta đi tìm (09/09/2026)."""
    hang, loai = th.get("hang", "hãng"), th.get("loai", "anh")
    if loai == "nguoi":
        ai = th.get("nguoi", "")
        return (f"Bai bao: \"{tieu_de}\". Anh nay KHONG phai anh cua tin; no la anh CHAN DUNG "
                f"cua {ai} ({th.get('vai','lanh dao')} {hang}) lay tu Wikidata/Commons.\n"
                "Tra loi DUNG 2 dong:\n"
                "MO_TA: <mot cau tieng Viet co dau mo ta anh nay la gi>\n"
                f"LIEN_QUAN: co | khong  (co = anh chup that MOT NGUOI, ro mat, hop lam anh chan "
                f"dung cho {hang}; khong = do hoa/tranh ve, anh nhom dong nguoi, qua mo, "
                "hoac ro rang khong phai anh chan dung)")
    if loai == "logo":
        return (f"Bai bao: \"{tieu_de}\". Anh nay la THE LOGO: logo chinh thuc cua {hang} dat "
                "tren nen tron.\nTra loi DUNG 2 dong:\n"
                "MO_TA: <mot cau tieng Viet co dau mo ta anh nay la gi>\n"
                f"LIEN_QUAN: co | khong  (co = doc duoc ro logo/ten {hang}, khong be xiu, khong "
                "meo, khong lan mau nen; khong = logo hang KHAC, chu bi cat, qua nho, hoac trong)")
    return (f"Bai bao: \"{tieu_de}\". Anh nay KHONG phai anh cua su viec trong tin; no duoc tim "
            f"lam ANH BOI CANH cua {hang} (tru so, campus, bien hieu, nha may, san pham).\n"
            "Tra loi DUNG 2 dong:\n"
            "MO_TA: <mot cau tieng Viet co dau mo ta anh nay la gi>\n"
            f"LIEN_QUAN: co | khong  (co = anh CHUP THAT dung la co so/san pham cua {hang}; "
            "khong = hang khac, do hoa/ban ve, anh mit tinh/bieu tinh, qua mo, hoac chi la anh "
            "minh hoa chung chung)")


def _hoi_commons(cau: str):
    """`query.pages` cua Commons, hoac None khi hong moi truong (C1). Mot ban o
    quet_chung.hoi_commons (ADF-r2-16) — truoc day ban nay tra {} va log khong
    repr, nen mat mang trong y het "hang khong co anh"."""
    import quet_chung
    return quet_chung.hoi_commons(cau)


def nhan_theo_loai(th: dict) -> str:
    """Câu nhãn cho MỘT ảnh thương hiệu, theo LOẠI tư liệu. Thuần.

    Tách khỏi `nhan_thuong_hieu` 10/09/2026 để brief nào cũng dùng đúng một bản:
    `ethan_chuan_bi.nhan_ethan` dựng lại `ghi_chu` từ đầu nên tự viết một câu
    "trụ sở/campus/biển hiệu" chung cho MỌI loại — một tấm chân dung founder tới
    tay Ethan mất luôn cái TÊN để khai `nhan_vat`, mà `nop_chung.kiem_nhan_vat`
    chặn ảnh có mặt người không khai tên. Tức Ethan buộc phải bỏ ảnh founder,
    đúng cái Ông Chủ hỏi ("task này thì ko chịu dùng hình của Founder")."""
    hang, loai = th.get("hang", "?"), th.get("loai", "anh")
    if loai == "nguoi":
        ai, vai = th.get("nguoi", "?"), th.get("vai", "lãnh đạo")
        return (f"👤 CHÂN DUNG {vai.upper()} — {ai}, {vai} {hang} (Wikidata/Commons). "
                f"Chỉ dùng khi BÀI CÓ NHẮC {ai}, và phải khai \"nhan_vat\": \"{ai}\" "
                "y hệt. Bài không nhắc tên người này thì bỏ (LUAT_ANH §6).")
    if loai == "logo":
        return (f"🔖 THẺ LOGO {hang} — logo chính thức đặt trên nền trơn, dồn lên "
                f"nửa trên để hook đè nửa dưới. Nền {th.get('nen', 'tối')} → khai "
                f"\"nen\": \"{'sang' if th.get('nen') == 'sáng' else 'toi'}\". "
                "Đường cuối khi tin không có ảnh thật nào khác — đừng dùng nếu đã "
                "có ảnh chụp.")
    if loai == "xep_hang":
        return (f"📊 BẢNG XẾP HẠNG có {hang} — ảnh engine chụp từ "
                f"{th.get('site', '?')} ({th.get('bang', '?')}), đã khoanh hàng. "
                "KHÔNG phải bảng của tin này; chỉ làm slide bối cảnh cho thấy hãng "
                "đang đứng đâu, và caption phải ghi rõ nguồn + bảng.")
    return (f"🏢 ẢNH THƯƠNG HIỆU ({hang}) từ Wikimedia Commons — ảnh THẬT của chính "
            "hãng trong tin (trụ sở/campus/biển hiệu/sản phẩm), KHÔNG phải ảnh của sự "
            "việc đang kể; hợp bìa và slide bối cảnh, đừng gán cho slide nói số liệu")


def nhan_thuong_hieu(a: dict) -> dict:
    """Siết nhãn một ảnh thương hiệu ĐÃ qua `phan_loai`. Thuần.

    Khác ảnh khái niệm: ảnh này ĐƯỢC vào slide thân (nó là ảnh thật của chính
    hãng trong tin). Giống ảnh khái niệm ở hai chỗ chặn: không phải chart của
    tin, và có mặt người thì bỏ — LUAT_ANH §6 "không gọi được tên thì không được
    dùng", mà người đứng trước cửa hàng Samsung trên Commons thì không ai gọi
    được tên."""
    th = a.get("thuong_hieu") or {}
    loai = th.get("loai", "anh")
    if a.get("lien_quan") is False:
        return a                                  # phan_loai đã xoá dung + ghi ❌
    a["ghi_chu"] = [g for g in a["ghi_chu"] if "Wikimedia Commons" not in g]

    if loai == "nguoi":
        # Mặt người ở đây là CÓ CHỦ Ý và GỌI ĐƯỢC TÊN — đúng ngoại lệ của
        # LUAT_ANH §6 ("trừ khi khai nhan_vat"), khác hẳn mặt vô danh.
        #
        # KHÔNG chặn theo `mat` ở đây: `luat_anh.dem_mat` trả None (-> 0) khi
        # thiếu cv2/model, và LUAT_ANH §6 nói rõ cổng mặt được phép tự tắt. Lấy
        # `mat == 0` làm "không phải chân dung" thì trên máy thiếu cv2 MỌI chân
        # dung đều bị bỏ câm lặng. Ảnh này là P18 của chính người đó trên
        # Wikidata; đúng/sai để con mắt (cau_hoi_vision) phán.
        a["ghi_chu"].insert(0, nhan_theo_loai(th))
        return a

    if loai == "logo":
        # Thẻ logo là nền trơn + chữ nên `phan_loai` đọc ra "chart" và dán kèm
        # "KHÔNG làm bìa" — ngược hẳn công dụng của nó. Gỡ ghi chú đó, đừng để
        # brief tự mâu thuẫn với chính mình.
        a["dung"] = ["bìa"]
        a["ghi_chu"] = [g for g in a["ghi_chu"]
                        if "KHÔNG làm bìa" not in g and "chart" not in g.lower()]
        a["ghi_chu"].insert(0, nhan_theo_loai(th))
        return a

    if loai == "xep_hang":
        a["ghi_chu"].insert(0, nhan_theo_loai(th))
        return a

    if a.get("loai") == "chart":
        a["dung"] = []
        a["ghi_chu"].insert(0, "❌ ảnh thương hiệu mà là chart/đồ hoạ → KHÔNG DÙNG "
                               "(chart phải là chart CỦA TIN)")
        return a
    if a.get("mat"):
        a["dung"] = []
        a["ghi_chu"].insert(0, f"❌ ảnh thương hiệu có {a['mat']} mặt người vô danh → KHÔNG DÙNG "
                               "(LUAT_ANH §6)")
        return a
    a["ghi_chu"].insert(0, nhan_theo_loai(th))
    return a
