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
`scan_common.ask_commons` chỉ tìm theo MỘT cụm — cụm tên riêng ĐẦU tiêu đề
(`_leading_proper_noun`) — nên tin "Qualcomm ... with Amazon" không bao giờ hỏi tới
Amazon; và nó hỏi bằng đúng tên trần ("Qualcomm"), không hỏi thẳng cái mà hãng
nào cũng có ảnh: trụ sở / toà nhà / campus.

Khác `image_concept.py` ở CHỖ ĐỨNG, không chỉ ở từ khoá. Ảnh khái niệm (cờ Nhật,
rack datacenter) là ảnh MINH HOẠ chủ đề: chỉ được làm bìa, và cả chùm chỉ đếm là
MỘT khi xét đủ/thiếu. Ảnh thương hiệu là ảnh thật CỦA CHÍNH hãng đang nói trong
bài — đúng loại "trụ sở/sản phẩm" mà IMAGE_RULES §1.2 vẫn kể là ảnh liên quan — nên
nó vào được slide thân và đếm đủ. Thứ tự vì thế là: ảnh riêng của tin → ảnh
thương hiệu → ảnh khái niệm.

BỐN LOẠI TƯ LIỆU, theo độ "là ảnh chụp thật của hãng" giảm dần (Ông Chủ
09/09/2026: *"ko thấy ảnh liên quan thì lấy ảnh logo, ảnh founder, ảnh chụp trên
các bảng xếp hạng của model... có thiếu tư liệu đâu?"*):

  1. 🏢 **cơ sở**   — trụ sở/campus: tìm tên tệp Commons + `P18` của Wikidata.
  2. 👤 **chân dung** — founder/CEO (`P112`/`P169` -> `P18` của họ). Đi KÈM TÊN,
     nên khai được `subject` — đúng ngoại lệ của IMAGE_RULES §6.
  3. 📊 **bảng xếp hạng** — `prepare.fallback_rounds._ranking_context_edge` mượn `ranking.py`
     chụp bảng có model của hãng. Chỉ nhận ảnh chụp thật, không nhận thẻ dự phòng.
  4. 🔖 **thẻ logo** — logo chính thức (`P154`) đặt trên nền trơn. Đường CUỐI.

Vì sao phải qua Wikidata chứ không chỉ tìm tên tệp: hãng thuần phần mềm không có
tệp nào tên "<hãng> headquarters" — mà trụ sở OpenAI trên Commons lại tên
"Pioneer Building, San Francisco", không một chữ "openai" nào. Wikidata trỏ
thẳng tới nó. Và tìm tên tệp thì không đời nào với tới chân dung Dario Amodei.

Hàm thuần (test được, không mạng) + hàm chạm mạng:
  - `vendors_in_story`   tiêu đề (+ tóm tắt) -> các hãng lớn được nhắc, ≤ 3.
  - `truy_van`         một hãng -> các câu hỏi Commons [(tên, câu)].
  - `filter_commons`      lọc `query.pages` theo tên hãng + bảng nhiễu.
  - `_qid_claim`       bóc người từ claim, BỎ người đã thôi chức (P582).
  - `rank_has_model`    hãng này có model trên bảng xếp hạng không.
  - `sentence_ask_vision`   câu hỏi riêng cho từng loại tư liệu.
  - `label_brand` siết nhãn của một ảnh đã qua `classify`.
  - `material_wikidata` / `commons_urls` / `card_logo` / `vendor_images`  (mạng/ảnh).
"""
import re
import sys
from pathlib import Path

import env_load
import manifest_values
import state_paths

MAX_RANK = 3            # số hãng lấy trong một tin
MAX_NEW_RANK = 2        # ảnh mỗi hãng — để một bộ không thành album trụ sở
SHORT_SIDE_MIN = 700

# Tên đi tìm trên Commons cho từng hãng (khoá = tên hãng chuẩn của
# `scan_business.RANK_OF_NAME`). Nhiều tên khi tên trên biển hiệu khác tên pháp
# lý (Meta -> Facebook) hoặc khi hãng con nằm trong khuôn viên hãng mẹ
# (DeepMind -> Google). Tên đầu là tên hiện trong brief.
DISPLAY_NAME = {
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
NAME_EXTRA = {
    "google": "google deepmind", "alphabet": "google deepmind",
    "meta": "meta", "facebook": "meta", "instagram": "meta",
    "azure": "microsoft", "snapdragon": "qualcomm",
}

# Hậu tố hỏi Commons. Chỉ thứ hãng nào cũng có ảnh chụp thật, không hỏi thứ
# trừu tượng (partnership, funding) — Commons trả minh hoạ tệ, xem image_concept.
SUFFIX = ("headquarters", "building", "campus")
MAX_QUERY = 4

# Từ CHUNG trong tên công ty: có mặt trong câu hỏi để Commons xếp hạng đúng,
# nhưng KHÔNG được đòi phải có trong tên tệp — "Mistral AI headquarters" mà bắt
# tên tệp chứa "ai" thì không tệp nào qua.
FROM_COMMON_NAME = {"ai", "inc", "labs", "lab", "corp", "corporation", "company",
                "platforms", "holdings", "motors", "technologies", "group",
                "web", "services", "the", "of", "and"}

# Tên hãng trùng một thứ NỔI TIẾNG HƠN chính nó trên Commons. Không có bảng này
# thì "Amazon headquarters" trả rừng Amazon, "Apple" trả quả táo, "Tesla" trả
# Nikola Tesla. Khoá = từ đặc trưng ĐẦU của tên hãng.
MANY = {
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
# `NAME_TYPE` của image_concept có "protest" nhưng tên tệp này không có chữ đó.
# Không đưa "march" vào (trùng tháng Ba) hay "union" trần (trùng Union Square).
MANY_COMMON = re.compile(
    r"solidarity|rall(y|ies)|\bstrikes?\b|striking|picket|protest|demonstrat|"
    r"activis|boycott|walkout|placard|labou?r union|trade union|unioni[sz]", re.I)


def _from_distinctive(ten: str) -> list:
    """Các từ trong tên hãng PHẢI có trong tên tệp. Bỏ từ chung (AI, Inc, Labs)."""
    return [w for w in re.findall(r"[a-z0-9.]+", (ten or "").lower())
            if w not in FROM_COMMON_NAME and len(w) >= 2]


def _has_phrase(tus: list, vb: str) -> bool:
    """Cac tu dac trung phai dung LIEN NHAU, dung thu tu, theo bien gioi tu
    (LOW-35, 12/09/2026): "Hugging Face" tung khop "West Lighthouse, Rathlin
    hugging the cliff face" vi chi doi MOI tu co mat. Ten mot tu thi nhu cu."""
    if not tus:
        return False
    return bool(re.search(r"(?<!\w)" + r"\W+".join(re.escape(t) for t in tus) + r"(?!\w)", vb))


def _has_word(tu: str, vb: str) -> bool:
    """Khớp theo BIÊN GIỚI TỪ: "arm" không được khớp "harm"/"Armstrong", "meta"
    không được khớp "metal", "intel" không được khớp "intelligence"."""
    return bool(re.search(r"(?<!\w)" + re.escape(tu) + r"(?!\w)", vb))


def _many(ten: str):
    """Regex nhiễu của một tên hãng, hoặc None."""
    tu = _from_distinctive(ten)
    if not tu or tu[0] not in MANY:
        return None
    if tu[0] not in _NHIEU_BIEN:
        _NHIEU_BIEN[tu[0]] = re.compile(MANY[tu[0]], re.I)
    return _NHIEU_BIEN[tu[0]]


def vendors_in_story(tieu_de: str, tom_tat: str = "") -> list:
    """Các hãng tin này nói tới, theo thứ tự xuất hiện, tối đa `MAX_RANK`.

    Dùng chung WATCHLIST của `scan_business` — cùng một danh sách "tên trong
    ngành phải theo sát", không chép lại ở đây. Tên model/chip quy về hãng chủ
    qua RANK_OF_NAME, nên "Claude Opus 5" ra Anthropic, "Xring O3" ra Xiaomi.
    Trả [{"key": "qualcomm", "company": "Qualcomm"}].

    WATCHLIST/NAME_EXTRA chỉ để TỐI ƯU (biết ngay tên chuẩn/QID của hãng lớn
    hay gặp) — KHÔNG dùng để LOẠI hãng ngoài danh sách (LOW-176, 16/09/2026):
    tin "Anthropic ra tích hợp Salesforce" trước đây chỉ ra được "Anthropic"
    (Salesforce không có trong watchlist AI), nên cả vòng ảnh thương hiệu lẫn
    câu hỏi con mắt đều không bao giờ biết tới Salesforce — trong khi ảnh đúng
    chủ đề nhất của tin lại là ảnh sự kiện của CHÍNH Salesforce. Hãng nào được
    gọi tên rõ trong tiêu đề (cụm chữ hoa liên tiếp, qua `all_proper_nouns`)
    mà chưa khớp watchlist cũng được thử — qua CÙNG cơ chế Commons/Wikidata
    (đã tổng quát sẵn, xem `query()`: `DISPLAY_NAME.get(khoa, (khoa.title(),))`
    — hãng lạ vẫn tra được, chỉ là không có tên hiển thị đẹp sẵn).
    """
    import scan_business
    from prepare.source import all_proper_nouns
    vb = f"{tieu_de or ''} {tom_tat or ''}".lower()
    vi_tri, ten_that = {}, {}
    for ten in list(scan_business.WATCHLIST) + list(NAME_EXTRA):
        t = ten.strip()
        if len(t) < 3:                       # "yi" một mình bắt cả "yield"
            continue
        m = re.search(r"(?<!\w)" + re.escape(t) + r"(?!\w)", vb)
        if not m:
            continue
        khoa = NAME_EXTRA.get(t) or scan_business.RANK_OF_NAME.get(ten, ten).strip()
        if khoa not in vi_tri or m.start() < vi_tri[khoa]:
            vi_tri[khoa] = m.start()
    import image_concept
    for ten in all_proper_nouns(tieu_de):
        thap = ten.lower()
        if thap in image_concept.COUNTRY:
            continue                     # "Philippines"/"Japan"... la nuoc, khong phai hang
        # Chi giai qua TU DAU cua cum de doi chieu NAME_EXTRA/RANK_OF_NAME:
        # "Claude Opus" phai quy ve "anthropic" (tu "claude", da co trong
        # vi_tri qua vong watchlist tren) chu khong tach ra thanh mot muc
        # "Claude Opus" rieng, dung mot ma san pham lam hang gia.
        tu_dau = thap.split()[0]
        khoa = NAME_EXTRA.get(tu_dau) or scan_business.RANK_OF_NAME.get(tu_dau) or thap
        if khoa in vi_tri or len(khoa) < 3:
            continue
        m = re.search(r"(?<!\w)" + re.escape(thap) + r"(?!\w)", vb)
        if not m:
            continue
        vi_tri[khoa] = m.start()
        ten_that[khoa] = ten              # giu dung hoa nhu trong tieu de (Salesforce, khong phai salesforce)
    ra = [{"key": k, "company": DISPLAY_NAME.get(k, (ten_that.get(k) or k.title(),))[0]}
          for k, _ in sorted(vi_tri.items(), key=lambda kv: kv[1])]
    return ra[:MAX_RANK]


def query(khoa: str) -> list:
    """Câu hỏi Commons cho một hãng: [(tên dùng để lọc, câu hỏi)]. Tên đứng riêng
    vì tên tệp mang tên hãng chứ không mang hậu tố ("Samsung Town Seoul.jpg" ra
    từ câu "Samsung headquarters")."""
    ten = DISPLAY_NAME.get(khoa, (khoa.title(),))
    ra = []
    for t in ten[:2]:
        for h in SUFFIX:
            ra.append((t, f"{t} {h}"))
    # Tên chính đủ ba hậu tố trước, rồi mới tới tên phụ.
    return ra[:MAX_QUERY]


def filter_commons(pages: dict, ten: str, so: int = 4, canh_ngan_min: int = SHORT_SIDE_MIN) -> list:
    """Lọc `query.pages` của API Commons cho một tên hãng: bitmap đủ lớn, tên tệp
    có ĐỦ các từ đặc trưng của tên hãng (theo biên giới từ), không phải đồ hoạ
    (`image_concept.NAME_TYPE`), không dính bảng nhiễu. JPEG trước, ảnh to trước."""
    import image_concept
    dac_trung = _from_distinctive(ten)
    nhieu = _many(ten)
    ra = []
    for pg in (pages or {}).values():
        ii = (pg.get("imageinfo") or [{}])[0]
        w, h = ii.get("width", 0), ii.get("height", 0)
        if min(w, h) < canh_ngan_min or ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        ten_tep = (pg.get("title") or "").replace("File:", "")
        thap = ten_tep.lower()
        if image_concept.NAME_TYPE.search(thap) or MANY_COMMON.search(thap):
            continue
        if not _has_phrase(dac_trung, thap):
            continue
        if nhieu and nhieu.search(thap):
            continue
        ra.append({"image_url": ii.get("thumburl") or ii.get("url"), "alt": "Commons: " + ten_tep,
                   "og": False, "mime": ii.get("mime"), "source": "brand",
                   "page_url": "https://commons.wikimedia.org/wiki/File:" + ten_tep.replace(" ", "_"),
                   "w": w, "h": h, "score": 25})
    # JPEG trước PNG: ảnh chụp thật gần như luôn là JPEG (xem image_concept).
    ra.sort(key=lambda c: (c["mime"] != "image/jpeg", -(c["w"] * c["h"])))
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
P_GATE_BILLION = ("P154", "P159", "P452", "P1454", "P571", "P169", "P112", "P1128")
MAX_PERSON = 2


def _ask_api(url: str, **kw) -> dict:
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


def _file_claim(claims: dict, p: str) -> list:
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


def confirm_unlisted_vendor(key: str, company: str) -> bool:
    """LOW-260: một cụm từ `vendors_in_story` lấy từ `all_proper_nouns` (nhánh
    hãng NGOÀI watchlist) có thật là một công ty không, trước khi `_round_brand`
    tiêu ngân sách tải/vision vào nó. `vendors_in_story` phải giữ THUẦN (không
    mạng — xem docstring + `tests/test_brand.py`), nên việc xác nhận này nằm ở
    đây, gọi ngay trước khi tải ảnh, không phải trong `vendors_in_story`.

    Đo thật 19/09/2026: tiêu đề Title Case "Microsoft Advertising Sets New
    Rules for AI Generated Ads" khiến "Rules" (chữ thường bị viết hoa vì kiểu
    tiêu đề, không phải tên hãng) lọt qua thành một "hãng", tốn 1/3 suất
    `MAX_RANK` và 2 lượt tải+vision vào ảnh Commons "Rules headquarters" vô
    nghĩa. "Salesforce" (ca LOW-176 sinh ra nhánh này) và "Rules" đều là MỘT
    từ tiếng Anh viết hoa bình thường — không phân biệt được bằng chữ, chỉ
    phân biệt được bằng kiến thức: Salesforce có ≥ 2 thuộc tính công ty trên
    Wikidata (`P_GATE_BILLION`, dùng chung với `qid_rank`), "Rules" thì không.

    Không gọi được Wikidata (mạng hỏng) -> False (fail-closed): thà bỏ lỡ một
    hãng lạ hiếm gặp trong một lượt còn hơn lặp lại đúng lỗi này."""
    qid, _ = qid_rank(company)
    if qid is None:
        print(f"[thuong_hieu] {key!r}: khong xac nhan duoc la cong ty qua Wikidata "
              "-- bo qua, khong tinh la hang (LOW-260)", file=sys.stderr)
    return qid is not None


def qid_rank(hang: str) -> tuple:
    """(qid, claims) của entity CÔNG TY khớp tên hãng, hoặc (None, {})."""
    r = _ask_api(WIKIDATA, action="wbsearchentities", search=hang, language="en",
                 type="item", limit=5)
    if r is None:
        print(f"[thuong_hieu] qid_rank({hang!r}): khong goi duoc Wikidata (wbsearchentities), bo qua",
              file=sys.stderr)
        return None, {}
    ids = [x["id"] for x in r.get("search", []) if x.get("id")]
    if not ids:
        return None, {}
    ent = _ask_api(WIKIDATA, action="wbgetentities", ids="|".join(ids), props="claims")
    if ent is None:
        print(f"[thuong_hieu] qid_rank({hang!r}): khong goi duoc Wikidata (wbgetentities), bo qua",
              file=sys.stderr)
        return None, {}
    ent = ent.get("entities", {})
    for qid in ids:                       # giữ thứ tự xếp hạng của Wikidata
        cl = (ent.get(qid) or {}).get("claims", {})
        if sum(p in cl for p in P_GATE_BILLION) >= 2:
            return qid, cl
    return None, {}


def material_wikidata(hang: str) -> dict:
    """Hồ sơ ảnh của một hãng: {"qid", "photo_files": [tệp], "logo": [tệp],
    "people": [{"name","commons_file","person_role"}]}. Không có/hỏng mạng -> {}."""
    qid, cl = qid_rank(hang)
    if not qid:
        return {}
    ra = {"qid": qid, "photo_files": _file_claim(cl, P_ANH)[:2], "logo": _file_claim(cl, P_LOGO)[:1],
          "people": []}
    ceo = _qid_claim(cl, P_CEO)
    ids = list(dict.fromkeys(ceo + _qid_claim(cl, P_SANG_LAP)))[:MAX_PERSON + 1]
    if ids:
        ent = _ask_api(WIKIDATA, action="wbgetentities", ids="|".join(ids),
                       props="claims|labels", languages="en")
        if ent is None:
            print(f"[thuong_hieu] material_wikidata({hang!r}): khong goi duoc Wikidata "
                  "(nguoi/CEO), bo qua", file=sys.stderr)
            ent = {}
        else:
            ent = ent.get("entities", {})
        for i in ids:
            e = ent.get(i) or {}
            ten = ((e.get("labels") or {}).get("en") or {}).get("value", "")
            tep = _file_claim(e.get("claims", {}), P_ANH)[:1]
            if ten and tep:
                ra["people"].append({"name": ten, "commons_file": tep[0],
                                     "person_role": "CEO" if i in ceo else "nhà sáng lập"})
    ra["people"] = ra["people"][:MAX_PERSON]
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
# ranking.extract_model) trong slug link. Chỉ mạng tĩnh, ≤ 1 + len(PATH_STORY) fetch.
P_WEBSITE = "P856"
PATH_STORY = ("/news/", "/en/news/", "/blog/", "/news", "/blog", "/research/")
# Trang HTML bị chặn bot (openai.com trả 0 byte cho httpx, đo 11/09/2026) thì
# RSS công khai vẫn mở — cùng bài học với `article_sources._title_rss` (Economist).
PATH_FEED = ("/news/rss.xml", "/rss.xml", "/blog/rss.xml", "/blog/feed.xml", "/feed.xml")
MAX_ANNOUNCEMENT_PAGE = 1


def _slug(t: str) -> str:
    """'DeepSeek-V4.1-Flash' -> 'deepseek-v4-1-flash' — cùng cách hãng đặt slug URL."""
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", (t or "").lower())).strip("-")


def _lock_model(models: list) -> list:
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


def vendor_website(hang: str) -> str:
    """Website chính thức của hãng theo Wikidata P856, hoặc ''."""
    _, cl = qid_rank(hang)
    for c in (cl or {}).get(P_WEBSITE, []):
        if c.get("rank") == "deprecated":
            continue
        v = c.get("mainsnak", {}).get("datavalue", {}).get("value")
        if isinstance(v, str) and v.startswith("http"):
            return v.rstrip("/")
    return ""


def _download_html(url: str, timeout: int = 15, feed: bool = False) -> str:
    """HTML (hoặc RSS khi `feed`) của một trang, UA trình duyệt — trang hãng hay
    chặn UA bot. '' nếu hỏng hay sai loại nội dung."""
    import httpx
    import scan_common
    try:
        scan_common.check_url(url)
        r = httpx.get(url, headers={"User-Agent": env_load.UA_BROWSER,
                                    "Accept-Encoding": "gzip, deflate"},
                      timeout=timeout, follow_redirects=True)
        loai = r.headers.get("content-type", "")
        if r.status_code == 200 and (("xml" in loai or "rss" in loai) if feed else "html" in loai):
            return r.text[:400_000]
    except Exception as e:                                   # noqa: BLE001
        print(f"[cong bo] {url[:60]}: {type(e).__name__}", file=sys.stderr)
    return ""


def announcement_page(hang: dict, models: list) -> dict | None:
    """Trang công bố CHÍNH CHỦ của model trong tin — một mục `pages[]` của tệp nguồn:
    {"url", "kind": "announcement", "title", "outlet_url"}
    hoặc None. `hang` là một mục của `vendors_in_story`, `models` từ
    `ranking.extract_model`. Không hỏi gì khi thiếu một trong hai."""
    from urllib.parse import urljoin
    khoa = _lock_model(models)
    if not hang or not khoa:
        # Khong im (INV-3): truoc 12/09/2026 nhanh nay tra None khong mot dong,
        # nen "vi sao khong co trang cong bo" phai doan.
        print(f"[cong bo] {(hang or {}).get('company') or '?'}: bo qua — models={models!r} "
              f"khong ra khoa slug nao (can 'Hang-Ten-So', vd DeepSeek-V4.1-Flash)", file=sys.stderr)
        return None
    site = vendor_website(hang.get("company") or hang.get("key", ""))
    if not site:
        print(f"[cong bo] {hang.get('company')}: Wikidata khong co website (P856)", file=sys.stderr)
        return None
    mien = re.sub(r"^https?://(www\.)?", "", site).lower()
    for duong in PATH_STORY + PATH_FEED:
        la_feed = duong in PATH_FEED
        html = _download_html(site + duong, feed=la_feed)
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
                print(f"[cong bo] {hang.get('company')}: {u} (khop '{k}' o {duong})", file=sys.stderr)
                return {"url": u, "kind": "announcement", "title": "", "outlet_url": site}
    print(f"[cong bo] {hang.get('company')}: khong thay bai nao khop {khoa[:2]} tren {site}",
          file=sys.stderr)
    return None


def commons_urls(tens: list) -> dict:
    """Tên tệp Commons -> {url, w, h, mime}. Hỏi một lượt. SVG được Commons
    render sẵn ra PNG ở `thumburl`, nên logo vector cũng dùng được."""
    tens = [t for t in tens if t]
    if not tens:
        return {}
    r = _ask_api(COMMONS, action="query", titles="|".join("File:" + t for t in tens),
                 prop="imageinfo", iiprop="url|size|mime", iiurlwidth=1800)
    if r is None:
        print("[thuong_hieu] commons_urls: khong goi duoc Commons API, bo qua", file=sys.stderr)
        return {}
    ra = {}
    for pg in ((r.get("query") or {}).get("pages") or {}).values():
        ii = (pg.get("imageinfo") or [{}])[0]
        ten = (pg.get("title") or "").replace("File:", "")
        u = ii.get("thumburl") or ii.get("url")
        if u:
            ra[ten] = {"url": u, "w": ii.get("thumbwidth") or ii.get("width", 0),
                       "h": ii.get("thumbheight") or ii.get("height", 0),
                       "mime": ii.get("mime")}
    return ra


def card_logo(tep_logo, out, brand: str = "donniechublog"):
    """Đặt LOGO THẬT của hãng lên nền thương hiệu, dồn lên NỬA TRÊN để hook đè
    được nửa dưới. Không phải minh hoạ — cùng nguyên tắc với thẻ dự phòng của
    `ranking.fallback_card`: không thêm một nét nào của ta, chỉ là chỗ đặt.

    Logo Commons hay là PNG trong suốt / SVG render nền trong; dán thẳng lên nền
    tối thì chữ đen của wordmark biến mất, nên nền được chọn theo độ sáng của
    chính logo."""
    import card
    from PIL import Image
    card.set_brand(brand)
    w, h = 1200, 1500
    lg = Image.open(tep_logo)
    lg = lg.convert("RGBA") if lg.mode in ("RGBA", "LA", "P") else lg.convert("RGB")
    # Độ sáng phần KHÔNG trong suốt: logo chữ đen -> nền sáng, logo chữ trắng -> nền tối.
    px = lg.convert("RGBA")
    sang = _measure_bright_logo(px)
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
    import image_provenance
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PNG", pnginfo=image_provenance.stamp_provenance("logo_card"))
    return out, ("light" if sang < 110 else "dark")


def _measure_bright_logo(px) -> float:
    """Độ sáng trung bình của phần ĐỤC trong logo (bỏ vùng trong suốt)."""
    L = px.convert("L")
    a = px.getchannel("A")
    tong = so = 0
    for lum, alpha in zip(L.getdata(), a.getdata()):
        if alpha > 128:
            tong += lum
            so += 1
    return (tong / so) if so else 128.0


def image_wikidata(hang, wd=None) -> list:
    """Ứng viên từ hồ sơ Wikidata: ảnh công ty (P18) -> người sáng lập/CEO (P18
    của họ, KÈM TÊN để khai `subject`) -> logo (P154, dựng thành thẻ).

    Ảnh công ty của Wikidata với tới thứ mà tìm theo tên tệp không với được:
    trụ sở OpenAI trên Commons tên là "Pioneer Building, San Francisco" — không
    có chữ "openai" nào trong tên tệp (09/09/2026)."""
    khoa = hang["key"] if isinstance(hang, dict) else hang
    ten_chinh = DISPLAY_NAME.get(khoa, (khoa.title(),))[0]
    tl = material_wikidata(ten_chinh)
    if not tl:
        return []
    can = list(tl["photo_files"]) + [n["commons_file"] for n in tl["people"]] + list(tl["logo"])
    thong = commons_urls(can)
    ra = []
    for t in tl["photo_files"]:
        u = thong.get(t)
        if u and min(u["w"], u["h"]) >= SHORT_SIDE_MIN:
            ra.append(_candidate(u, t, ten_chinh, khoa, "photo", "ảnh công ty (Wikidata P18)"))
    for n in tl["people"]:
        u = thong.get(n["commons_file"])
        if u and min(u["w"], u["h"]) >= 500:
            c = _candidate(u, n["commons_file"], ten_chinh, khoa, "person",
                          f"{n['person_role']} {ten_chinh} (Wikidata)")
            c["brand_match"]["person"] = n["name"]
            c["brand_match"]["person_role"] = n["person_role"]
            c["alt"] = f"Commons: {n['name']} — {n['person_role']} {ten_chinh}"
            ra.append(c)
        # BAT ANH NGANG cua chinh nguoi nay tren Commons (Ong Chu 12/09/2026:
        # "chỉ cần search claude hay anthropic thì cũng ra một rừng ảnh rồi").
        # Wikidata P18 chi giu DUNG MOT anh (thuong la chan dung studio, doc) —
        # chua bao gio hoi Commons theo TEN NGUOI. Do that 12/09: search "Dario
        # Amodei" ra 9 anh su kien/hop bao 4000x2667..8192x5464, ti le 1.5, ma
        # pipeline chua bao gio cham toi vi SUFFIX chi khop "headquarters/
        # building/campus". Ten day du it dung hang nhu ten hang (khong nhu
        # "Anthropic" trung khao co, "Claude" trung hoi hoa) nen dung lai
        # `_tu_dac_trung`/`_has_phrase` cua chinh module nay, khong can bang NHIEU.
        for c in image_person_landscape(n["name"], n["person_role"], ten_chinh, khoa):
            ra.append(c)
    for t in tl["logo"]:
        u = thong.get(t)
        if not u or not wd:
            continue
        try:
            goc = Path(wd) / state_paths.LOGO_ORIGINAL_FILE
            goc.parent.mkdir(parents=True, exist_ok=True)
            import httpx
            goc.write_bytes(httpx.get(u["url"], headers={"User-Agent": env_load.UA_WIKI},
                                      timeout=30, follow_redirects=True).content)
            the, nen = card_logo(goc, Path(wd) / state_paths.LOGO_CARD_FILE, env_load.brand_long())
        except Exception as e:                               # noqa: BLE001
            print(f"[thuong_hieu] the logo hong: {type(e).__name__}", file=sys.stderr)
            continue
        c = _candidate(u, t, ten_chinh, khoa, "logo", "logo chính thức (Wikidata P154)")
        c["brand_match"]["background_tone"] = nen
        c.update({"file_path": str(the), "image_url": str(the), "graphic_allowed": True})
        ra.append(c)
    return ra


def _candidate(u: dict, ten_tep: str, hang: str, khoa: str, loai: str, ly_do: str) -> dict:
    return {"image_url": u["url"], "alt": "Commons: " + ten_tep, "og": False, "mime": u.get("mime"),
            "source": "brand", "w": u["w"], "h": u["h"],
            "page_url": "https://commons.wikimedia.org/wiki/File:" + ten_tep.replace(" ", "_"),
            "score": {"photo": 28, "person": 24, "logo": 18}.get(loai, 20),
            "brand_match": {"company": hang, "key": khoa, "kind": loai, "keyword": ly_do}}


MAX_PERSON_LANDSCAPE = 2   # tran anh ngang moi nguoi — tranh mot CEO chiem het luot


def image_person_landscape(ten: str, vai: str, hang: str, khoa: str) -> list:
    """Ảnh NGANG của chính người này trên Commons (họp báo, sự kiện, phỏng vấn)
    — KHÁC ảnh chân dung studio duy nhất mà Wikidata P18 giữ.

    Ông Chủ 12/09/2026: *"chỉ cần search claude hay anthropic thì cũng ra một
    rừng ảnh rồi, kiếm cái ảnh rõ nét và ratio phù hợp khó thế sao?"* — đúng, đo
    thật: search "Dario Amodei" ra 9 ảnh họp báo/sự kiện 4000x2667..8192x5464,
    tỉ lệ 1,5 (ngang), mà `image_wikidata` trước đây CHƯA BAO GIỜ hỏi Commons theo
    TÊN NGƯỜI — chỉ lấy đúng một ảnh P18 (thường là chân dung studio, dọc).

    Search "Anthropic"/"Claude AI" một mình thì nhiễu thật (khảo cổ, hội hoạ,
    từ điển — xem `NHIEU`), nhưng TÊN NGƯỜI ĐẦY ĐỦ hiếm khi trùng nghĩa khác;
    dùng lại đúng `_tu_dac_trung`/`_has_phrase` đã có cho tên hãng: các từ của tên
    phải nằm LIỀN NHAU, đúng thứ tự, theo biên giới từ. Vẫn cùng cổng IMAGE_RULES §6 với chân
    dung (khai `subject`) — chỉ khác đủ ngang để không teo khi lên bìa."""
    import image_concept
    pages = _ask_commons(f'"{ten}"')
    if pages is None:
        return []
    dac_trung = _from_distinctive(ten)
    ra = []
    for pg in pages.values():
        ii = (pg.get("imageinfo") or [{}])[0]
        w, h = ii.get("width", 0), ii.get("height", 0)
        if min(w, h) < SHORT_SIDE_MIN or w < h:            # doc/vuong hep -> bo, day la
            continue                                       # duong rieng cho "ti le phu hop"
        if ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        ten_tep = (pg.get("title") or "").replace("File:", "")
        thap = ten_tep.lower()
        # `_has_phrase` chu KHONG `all(_has_word(...))` (12/09/2026): ban long chi doi
        # MOI tu co mat dau do nen "Dario Amodei" khop ca "dario rossi meets luca
        # amodei in rome" — anh HAI NGUOI KHAC, ma caption lai khai
        # `subject: "Dario Amodei"`, tuc bia mat nguoi (IMAGE_RULES §0/§6). Cung
        # lop loi ma `filter_commons` vua duoc siet o cung ngay ("Hugging Face" khop
        # "Rathlin hugging the cliff face"); ban va do khong lan sang day.
        if image_concept.NAME_TYPE.search(thap) or not _has_phrase(dac_trung, thap):
            continue
        c = _candidate({"url": ii.get("thumburl") or ii.get("url"), "w": w, "h": h,
                       "mime": ii.get("mime")}, ten_tep, hang, khoa, "person",
                      f"{vai} {hang}, ảnh ngang (Commons)")
        c["score"] = 26    # giua "anh" cong ty/san pham (28) va chan dung doc (24):
                           # van la mot nguoi, nhung du ngang de khong can crop nat
        c["brand_match"]["person"] = ten
        c["brand_match"]["person_role"] = vai
        c["alt"] = f"Commons: {ten} — {vai} {hang}, ảnh ngang"
        ra.append(c)
        if len(ra) >= MAX_PERSON_LANDSCAPE:
            break
    return ra


HAS_BALLOT_URL = "https://www.google.com/finance/quote/{ma}"
HAS_BALLOT_WAIT = 2500            # ms cho bieu do SVG ve xong


def image_has_ballot(hang, wd, phien=None) -> list:
    """Biểu đồ giá cổ phiếu của hãng — chụp trang Google Finance ở khung mobile.

    Bảng loại tin (`story_type.py`, Ông Chủ 12/09/2026): tin BUSINESS/M&A thì "mã
    cổ phiếu" là một vật liên quan. Chỉ hãng có trong `story_type.CODE_HAS_BALLOT`
    (niêm yết); hãng tư nhân trả [] ngay, không đoán. Tường chặn bot -> [] (dùng
    chung `browser_session.got_block`). Là đồ hoạ có chủ ý (`graphic_allowed`, như thẻ
    logo) nên `download_and_filter` không loại nó như logo báo lọt."""
    import story_type
    from pathlib import Path as _P
    khoa = hang["key"] if isinstance(hang, dict) else hang
    ma = story_type.code_has_ballot(khoa)
    if not ma or wd is None:
        return []
    ten_chinh = DISPLAY_NAME.get(khoa, (khoa.title(),))[0]
    ra = _P(wd) / f"{state_paths.STOCK_IMAGE_PREFIX}{khoa.replace(' ', '_')}.png"
    ra.parent.mkdir(parents=True, exist_ok=True)
    try:
        from browser_session import (MOBILE_DPR, MOBILE_UA, MOBILE_VIEWPORT, got_block,
                                   session_or_new)
        with session_or_new(phien) as ph:
            with ph.trang(viewport=MOBILE_VIEWPORT, device_scale_factor=MOBILE_DPR,
                          is_mobile=True, has_touch=True, user_agent=MOBILE_UA) as page:
                resp = page.goto(HAS_BALLOT_URL.format(ma=ma), wait_until="domcontentloaded",
                                 timeout=40000)
                page.wait_for_timeout(HAS_BALLOT_WAIT)
                ly = got_block(page.title() or "", resp.status if resp else None,
                             page.evaluate("document.body ? document.body.innerText : ''") or "")
                if ly:
                    print(f"[co_phieu] {ma}: trang chặn ({ly}), bỏ", file=sys.stderr)
                    return []
                # Khoi bieu do: the <svg> to nhat trong man dau; khong co thi
                # chup vung main phia tren (gia + bieu do nam o day).
                khoi = page.evaluate("""() => {
                  let best = null, area = 0;
                  for (const el of document.querySelectorAll('svg, canvas')) {
                    const r = el.getBoundingClientRect();
                    if (r.width < 200 || r.height < 100 || r.top > window.innerHeight * 2) continue;
                    if (r.width * r.height > area) { area = r.width * r.height; best = r; }
                  }
                  if (!best) return null;
                  const dem = 60;   // lay ca dong gia/ten ngay tren bieu do
                  return {x: 0, y: Math.max(0, best.top - dem), w: window.innerWidth,
                          h: best.height + dem};
                }""")
                if not khoi:
                    print(f"[co_phieu] {ma}: khong thay bieu do", file=sys.stderr)
                    return []
                page.screenshot(path=str(ra), full_page=True,
                                clip={"x": khoi["x"], "y": khoi["y"],
                                      "width": khoi["w"], "height": khoi["h"]})
    except Exception as e:                                   # noqa: BLE001
        print(f"[co_phieu] {ma}: {type(e).__name__}: {e!r}", file=sys.stderr)
        return []
    if not (ra.exists() and ra.stat().st_size > 0):
        return []
    from PIL import Image as _Im
    with _Im.open(ra) as im:
        w, h = im.size
    c = _candidate({"url": str(ra), "w": w, "h": h, "mime": "image/png"},
                  ra.name, ten_chinh, khoa, "stock", f"biểu đồ giá {ma} (Google Finance)")
    c.update({"file_path": str(ra), "image_url": str(ra), "graphic_allowed": True, "score": 22})
    c["brand_match"]["ticker"] = ma
    return [c]


def vendor_images(hang, so: int = MAX_NEW_RANK, wd=None) -> list:
    """Ứng viên ảnh thương hiệu cho một hãng ({"key","company"} hoặc khoá).

    Hai đường, theo độ "là ảnh chụp thật của hãng" giảm dần:
      1. tìm tên tệp trên Commons: `"<Hãng> headquarters/building/campus"`;
      2. hồ sơ Wikidata: ảnh công ty -> founder/CEO (kèm tên) -> logo.
    Đường 2 chạy khi đường 1 chưa đủ `so` — hãng thuần phần mềm (Anthropic,
    DeepSeek) không có ảnh trụ sở nào trên Commons, và đó chính là loại tin hay
    bị dừng ở nút "chỉ 2/5 ảnh". Hỏng mạng -> []."""
    khoa = hang["key"] if isinstance(hang, dict) else hang
    ten_chinh = DISPLAY_NAME.get(khoa, (khoa.title(),))[0]
    ra, da, hong = [], set(), 0
    for ten, cau in query(khoa):
        if len(ra) >= so:
            break
        pages = _ask_commons(cau)
        if pages is None:                    # hong moi truong, KHONG phai "khong co anh"
            hong += 1
            continue
        for c in filter_commons(pages, ten, so=so):
            if c["image_url"] in da:
                continue
            da.add(c["image_url"])
            c["brand_match"] = {"company": ten_chinh, "key": khoa, "kind": "photo", "keyword": cau}
            ra.append(c)
            if len(ra) >= so:
                break
    if hong and not ra:
        # ADF-r2-16: truoc day {} cua _ask_commons di thang vao filter_commons nen
        # mat mang == hang khong co anh. Giu hop dong tra [] cua ham, nhung noi
        # ro de brief/nhat ky khong ket luan sai ve hang.
        print(f"[thuong_hieu] {khoa}: {hong} truy van Commons HONG (mang/API) — "
              "khong phai hang khong co anh", file=sys.stderr)
    if len(ra) < so:
        for c in image_wikidata(hang, wd):
            if c["image_url"] not in da:
                da.add(c["image_url"])
                ra.append(c)
    return ra


def rank_has_model(khoa: str) -> bool:
    """Hãng này có model nằm trên bảng xếp hạng không — mới đáng mở browser đi
    chụp bảng. Qualcomm/TSMC không làm LLM nên không bao giờ khớp hàng nào."""
    import scan_business
    return khoa in set(scan_business.RANK_OF_NAME.values()) | {
        "openai", "anthropic", "deepseek", "mistral", "xai", "cohere", "moonshot",
        "zhipu", "minimax", "01.ai", "stability ai", "black forest", "midjourney",
        "perplexity", "nvidia", "microsoft", "amazon", "meta", "google deepmind"}


def sentence_ask_vision(tieu_de: str, th: dict) -> str:
    """Câu hỏi riêng cho ảnh thương hiệu. Câu chung hỏi "có phải ảnh của tin
    không" — chân dung nhà sáng lập và logo chắc chắn không phải, nên bị đánh
    rớt dù đó đúng là thứ ta đi tìm (09/09/2026).

    LOW-201 (16/09/2026, dao LOW-45): ca "minh hoa chung chung" (nhanh "anh")
    lan IMAGE_PHRASES_SCREENSHOT (ca ba nhanh — LOW-45, 13/09/2026: chan anh
    "chup LAI mot man hinh bang may anh khac", dung cho ca Getty chup nghieng
    App Store cua Kimi K3) da GO khoi day. Ong Chu 16/09: hai tieu chi nay loai
    oan anh dung chu de (xem `prepare/vision.py` cho do that va ly do day du).

    LOW-260 (19/09/2026): nhánh "stock" tách riêng khỏi câu chung "trụ sở/
    campus/sản phẩm" bên dưới — một ảnh chụp màn hình biểu đồ giá không bao
    giờ trả lời "có" được câu hỏi đó, nên MỌI ảnh tier cổ phiếu (đúng hãng,
    đúng mã) bị vision loại oan, chắc chắn phí 1 trong `MAX_NEW_RANK` suất
    ảnh của hãng (đo thật: MSFT:NASDAQ của Microsoft)."""
    hang, loai = th.get("company", "hãng"), th.get("kind", "photo")
    if loai == "stock":
        ma = th.get("ticker", "")
        return (f"Bai bao: \"{tieu_de}\". Anh nay la BIEU DO GIA CO PHIEU: chup man hinh gia "
                f"co phieu {ma or hang} cua {hang} tu Google Finance.\n"
                "Tra loi DUNG 2 dong:\n"
                "MO_TA: <mot cau tieng Viet co dau mo ta anh nay la gi>\n"
                f"LIEN_QUAN: co | khong  (co = day la man hinh gia co phieu THAT cua {hang} "
                "(bat ky ten/ma nao hien tren do, khong can doc het); khong = khong phai bieu "
                "do gia co phieu, hoac ro rang la hang khac)")
    if loai == "person":
        ai = th.get("person", "")
        return (f"Bai bao: \"{tieu_de}\". Anh nay KHONG phai anh cua tin; no la anh CHAN DUNG "
                f"cua {ai} ({th.get('person_role','lanh dao')} {hang}) lay tu Wikidata/Commons.\n"
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
                "meo, khong lan mau nen; khong = logo hang KHAC, chu bi cat, qua nho, trong)")
    return (f"Bai bao: \"{tieu_de}\". Anh nay KHONG phai anh cua su viec trong tin; no duoc tim "
            f"lam ANH BOI CANH cua {hang} (tru so, campus, bien hieu, nha may, san pham).\n"
            "Tra loi DUNG 2 dong:\n"
            "MO_TA: <mot cau tieng Viet co dau mo ta anh nay la gi>\n"
            f"LIEN_QUAN: co | khong  (co = anh CHUP THAT dung la co so/san pham cua {hang}; "
            f"khong = hang khac, do hoa/ban ve, anh mit tinh/bieu tinh, qua mo)")


def _ask_commons(cau: str):
    """`query.pages` cua Commons, hoac None khi hong moi truong (C1). Mot ban o
    scan_common.ask_commons (ADF-r2-16) — truoc day ban nay tra {} va log khong
    repr, nen mat mang trong y het "hang khong co anh"."""
    import scan_common
    return scan_common.ask_commons(cau)


def label_by_type(th: dict) -> str:
    """Câu nhãn cho MỘT ảnh thương hiệu, theo LOẠI tư liệu. Thuần.

    Tách khỏi `label_brand` 10/09/2026 để brief nào cũng dùng đúng một bản:
    `ethan_prepare.label_ethan` dựng lại `notes` từ đầu nên tự viết một câu
    "trụ sở/campus/biển hiệu" chung cho MỌI loại — một tấm chân dung founder tới
    tay Ethan mất luôn cái TÊN để khai `subject`, mà `submit_common.check_subject_named`
    chặn ảnh có mặt người không khai tên. Tức Ethan buộc phải bỏ ảnh founder,
    đúng cái Ông Chủ hỏi ("task này thì ko chịu dùng hình của Founder")."""
    hang, loai = th.get("company", "?"), th.get("kind", "photo")
    if loai == "person":
        ai, vai = th.get("person", "?"), th.get("person_role", "lãnh đạo")
        return (f"👤 CHÂN DUNG {vai.upper()} — {ai}, {vai} {hang} (Wikidata/Commons). "
                f"Chỉ dùng khi BÀI CÓ NHẮC {ai}, và phải khai \"subject\": \"{ai}\" "
                "y hệt. Bài không nhắc tên người này thì bỏ (IMAGE_RULES §6).")
    if loai == "logo":
        return (f"🔖 THẺ LOGO {hang} — logo chính thức đặt trên nền trơn, dồn lên "
                f"nửa trên để hook đè nửa dưới. Nền {manifest_values.tone_label(th.get('background_tone', 'dark'))} → khai "
                f"\"background_tone\": \"{'light' if th.get('background_tone') == 'light' else 'dark'}\". "
                "Đường cuối khi tin không có ảnh thật nào khác — đừng dùng nếu đã "
                "có ảnh chụp.")
    if loai == "stock":
        return (f"📈 BIỂU ĐỒ GIÁ {th.get('ticker', '?')} của {hang} (Google Finance, khung điện thoại) — "
                "vật liên quan của tin BUSINESS/M&A theo bảng loại tin. Đồ hoạ có chủ ý: dán "
                "full bề ngang như chart, khai \"chart\": true ở slide thân; caption ghi "
                "\"via Google Finance\".")
    if loai == "ranking":
        return (f"📊 BẢNG XẾP HẠNG có {hang} — ảnh engine chụp từ "
                f"{th.get('site', '?')} ({th.get('board', '?')}), đã khoanh hàng. "
                "KHÔNG phải bảng của tin này; chỉ làm slide bối cảnh cho thấy hãng "
                "đang đứng đâu, và caption phải ghi rõ nguồn + bảng.")
    return (f"🏢 ẢNH THƯƠNG HIỆU ({hang}) từ Wikimedia Commons — ảnh THẬT của chính "
            "hãng trong tin (trụ sở/campus/biển hiệu/sản phẩm), KHÔNG phải ảnh của sự "
            "việc đang kể; hợp bìa và slide bối cảnh, đừng gán cho slide nói số liệu")


def label_brand(a: dict) -> dict:
    """Siết nhãn một ảnh thương hiệu ĐÃ qua `classify`. Thuần.

    Khác ảnh khái niệm: ảnh này ĐƯỢC vào slide thân (nó là ảnh thật của chính
    hãng trong tin). Giống ảnh khái niệm ở hai chỗ chặn: không phải chart của
    tin, và có mặt người thì bỏ — IMAGE_RULES §6 "không gọi được tên thì không được
    dùng", mà người đứng trước cửa hàng Samsung trên Commons thì không ai gọi
    được tên."""
    th = a.get("brand_match") or {}
    loai = th.get("kind", "photo")
    if a.get("relevant") is False:
        return a                                  # classify đã xoá dung + ghi ❌
    a["notes"] = [g for g in a["notes"] if "Wikimedia Commons" not in g]

    if loai == "person":
        # Mặt người ở đây là CÓ CHỦ Ý và GỌI ĐƯỢC TÊN — đúng ngoại lệ của
        # IMAGE_RULES §6 ("trừ khi khai subject"), khác hẳn mặt vô danh.
        #
        # KHÔNG chặn theo `faces` ở đây: `image_rules.count_faces` trả None (-> 0) khi
        # thiếu cv2/model, và IMAGE_RULES §6 nói rõ cổng mặt được phép tự tắt. Lấy
        # `faces == 0` làm "không phải chân dung" thì trên máy thiếu cv2 MỌI chân
        # dung đều bị bỏ câm lặng. Ảnh này là P18 của chính người đó trên
        # Wikidata; đúng/sai để con mắt (sentence_ask_vision) phán.
        a["notes"].insert(0, label_by_type(th))
        return a

    if loai == "logo":
        # Thẻ logo là nền trơn + chữ nên `classify` đọc ra "chart" và dán kèm
        # "KHÔNG làm bìa" — ngược hẳn công dụng của nó. Gỡ ghi chú đó, đừng để
        # brief tự mâu thuẫn với chính mình.
        a["uses"] = ["cover"]
        a["notes"] = [g for g in a["notes"]
                        if "KHÔNG làm bìa" not in g and "chart" not in g.lower()]
        a["notes"].insert(0, label_by_type(th))
        return a

    if loai == "stock":
        a["uses"] = ["body_chart_full_width"]
        a["notes"] = [g for g in a["notes"] if "KHÔNG làm bìa" not in g]
        a["notes"].insert(0, label_by_type(th))
        return a
    if loai == "ranking":
        a["notes"].insert(0, label_by_type(th))
        return a

    if a.get("kind") == "chart":
        a["uses"] = []
        a["notes"].insert(0, "❌ ảnh thương hiệu mà là chart/đồ hoạ → KHÔNG DÙNG "
                               "(chart phải là chart CỦA TIN)")
        return a
    if a.get("faces"):
        a["uses"] = []
        a["notes"].insert(0, f"❌ ảnh thương hiệu có {a['faces']} mặt người vô danh → KHÔNG DÙNG "
                               "(IMAGE_RULES §6)")
        return a
    a["notes"].insert(0, label_by_type(th))
    return a
