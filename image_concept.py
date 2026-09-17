#!/usr/bin/env python3
"""Ảnh KHÁI NIỆM cho hero/bìa khi tin không có ảnh riêng — kỹ năng cũ của Dre,
nay là của engine.

Vì sao có tệp này (Ông Chủ 07/09/2026): "các Designer có vẻ mất kỹ năng tìm
hình trên internet, trong resource gốc không có hình hoặc hình không đạt là bỏ
qua luôn. Nhắc tới Nhật thì tìm cờ hoặc bản đồ nước Nhật, Nhật đầu tư xây
compute thì lấy hình datacenter". Trước 04/09 Dre có web_search nên tự làm;
từ kiến trúc 3 lớp vai không còn công cụ, còn `image_prepare` chỉ tìm ảnh CÙNG
TIN (Bing News + Commons theo tên hãng) — không ai tìm ảnh CÙNG KHÁI NIỆM nữa,
nên tin không ảnh đi thẳng sang Kite. Sửa ở engine để cả Ethan, Dre, Kite cùng
hưởng, đúng luật "vai chỉ chọn mã".

Ảnh khái niệm là ẢNH THẬT (cờ đang bay, toà nhà, dãy rack máy chủ) lấy từ
Wikimedia Commons — không vẽ, không AI. Nó chỉ được làm BÌA/HERO, đứng sau mọi
ảnh riêng của tin; caption "via Wikimedia Commons" do renderer ghi.

Ba phần, phần nào cũng thuần để test được:
  - `keyword_concept`  tiêu đề (+ tóm tắt) -> [{tu_khoa, ly_do}], ≤ 3;
                         heuristic bảng nước + chủ đề, thêm LLM khi có router.
  - `filter_commons`        lọc trang trả về của API Commons theo từ khoá.
  - `label_concept`     siết nhãn "dùng được" của một ảnh đã phân loại.
"""
import json
import re
import sys
import urllib.request

import env_load

# Wikimedia doi UA co ten cong cu + duong lien he, khong nhan UA kieu trinh
# duyet (403, do 09/09/2026) -> dung chung mot cho: env_load.UA_WIKI.
UA = env_load.UA_WIKI
MAX_KEYWORD = 3

# Tên nước / khối -> tên chuẩn (khoá là chữ thường, khớp theo từ nguyên).
# Tính từ (Japanese) và tên (Japan) cùng về một chỗ.
COUNTRY = {}
for _chuan, _bien_the in {
    "Japan": ("japan", "japanese", "tokyo"),
    "China": ("china", "chinese", "beijing", "shanghai"),
    "South Korea": ("korea", "korean", "seoul"),
    "Taiwan": ("taiwan", "taiwanese", "taipei"),
    "India": ("india", "indian", "delhi", "bangalore", "bengaluru"),
    "Vietnam": ("vietnam", "vietnamese", "hanoi", "saigon"),
    "Singapore": ("singapore", "singaporean"),
    "Indonesia": ("indonesia", "indonesian", "jakarta"),
    "Malaysia": ("malaysia", "malaysian"),
    "Thailand": ("thailand", "thai", "bangkok"),
    # Thiếu trong bảng SEA tới 09/09/2026 (đủ 5 nước còn lại) nên tin
    # "Philippines rót 34 tỷ USD đuổi theo cuộc đua AI" không ra từ khoá nào.
    "Philippines": ("philippines", "filipino", "manila"),
    "Australia": ("australia", "australian", "sydney"),
    "United States": ("america", "american", "washington", "pentagon"),
    "Canada": ("canada", "canadian"),
    "United Kingdom": ("britain", "british", "england", "london"),
    "France": ("france", "french", "paris"),
    "Germany": ("germany", "german", "berlin"),
    "Italy": ("italy", "italian"),
    "Spain": ("spain", "spanish"),
    "Netherlands": ("netherlands", "dutch"),
    "Sweden": ("sweden", "swedish"),
    "Switzerland": ("switzerland", "swiss"),
    "Israel": ("israel", "israeli"),
    "United Arab Emirates": ("uae", "emirates", "dubai", "abu dhabi"),
    "Saudi Arabia": ("saudi", "riyadh"),
    "Russia": ("russia", "russian", "moscow"),
    "Brazil": ("brazil", "brazilian"),
    "Mexico": ("mexico", "mexican"),
    "European Union": ("eu", "european", "brussels"),
}.items():
    for _b in _bien_the:
        COUNTRY[_b] = _chuan
# Hai chữ hoa đứng riêng: "US", "UK" — khớp có phân biệt hoa thường ở dưới.
COUNTRY_WRITE_ALL = {"US": "United States", "USA": "United States", "UK": "United Kingdom",
                 "EU": "European Union", "UAE": "United Arab Emirates"}

# Chủ đề -> vật thể THẬT chụp được. Không đưa khái niệm trừu tượng (funding,
# partnership) vì Commons chỉ trả ảnh minh hoạ tệ cho những thứ đó.
TOPIC = [
    (re.compile(r"data ?cent|compute|gpu cluster|supercomput|hyperscal|server farm|cloud region|"
                r"\bgpus?\b|\bhbm\b|nvidia h\d|blackwell|rubin", re.I),
     "data center server racks", "tin hạ tầng tính toán"),
    (re.compile(r"\bchips?\b|semiconductor|wafer|foundry|\bfab\b|lithograph|\btsmc\b|\bsmic\b|"
                r"\bnm process\b|\d\s?nm\b", re.I),
     "silicon wafer", "tin bán dẫn"),
    (re.compile(r"\brobots?\b|humanoid|robotic", re.I),
     "humanoid robot", "tin robot"),
    (re.compile(r"self[- ]driving|autonomous (car|vehicle|driving)|robotaxi|\bwaymo\b|\btesla fsd\b", re.I),
     "self-driving car lidar", "tin xe tự lái"),
    (re.compile(r"\bdrones?\b|quadcopter|\buav\b", re.I),
     "quadcopter drone flying", "tin drone"),
    (re.compile(r"satellite|\borbit\b|\brocket\b|spacex|starlink|launch pad", re.I),
     "satellite in orbit", "tin vũ trụ"),
    (re.compile(r"nuclear|reactor|power plant|gigawatt|\bGW\b|grid|electricity|energy", re.I),
     "power plant cooling towers", "tin năng lượng"),
    (re.compile(r"\bsolar\b|photovoltaic", re.I),
     "solar farm panels", "tin điện mặt trời"),
    (re.compile(r"\bstocks?\b|\bshares?\b|\bipo\b|nasdaq|wall street|market cap|\bearnings\b|"
                r"\bvaluation\b|stock market|\bnyse\b", re.I),
     "stock exchange trading floor", "tin thị trường chứng khoán"),
    (re.compile(r"\bbanks?\b|banking|\bfintech\b|payments?\b", re.I),
     "bank headquarters building", "tin ngân hàng / thanh toán"),
    (re.compile(r"smartphone|\biphone\b|\bandroid\b|\bpixel \d|galaxy s\d", re.I),
     "smartphone in hand", "tin điện thoại"),
    (re.compile(r"\blaptop\b|\bmacbook\b|\bpc\b|desktop computer", re.I),
     "laptop computer desk", "tin máy tính"),
    (re.compile(r"hospital|\bpatients?\b|\bdrugs?\b|\bfda\b|clinical|medical|healthcare", re.I),
     "hospital ward", "tin y tế"),
    (re.compile(r"\bcourt\b|lawsuit|antitrust|\bruling\b|\bjudge\b|\bsued?\b|litigation", re.I),
     "courthouse", "tin pháp lý"),
    (re.compile(r"regulat|\blaw\b|legislation|\bparliament\b|\bsenate\b|\bcongress\b|\bpolicy\b|\bban\b|"
                r"\bministry\b|government", re.I),
     "parliament building", "tin chính sách"),
    # "hack" TRAN bat nham nghia (Ong Chu 12/09/2026): trong tin AI, "reward
    # hacking" / "benchmark hacking" la mo hinh lach thuoc do, khong phai tin
    # tac — ma `\bhack` khop het, nen tin "AI giai toan gioi, nen toan hoc thi
    # lech chuan" roi vao ro an ninh mang va ra mot tam day mang phong may lam
    # bia. "hackathon" cung tung khop. Chi bat khi that su noi toi ke tan cong.
    (re.compile(r"\bcyber|\bhackers?\b|\bhacked\b|"
                r"\bhacking (?:group|campaign|attack|incident|spree)\b|"
                r"ransomware|\bbreach\b|malware|\bphishing\b", re.I),
     "server room cables", "tin an ninh mạng"),
    (re.compile(r"\bfactory\b|manufactur|assembly line|\bplant\b", re.I),
     "factory assembly line", "tin sản xuất"),
    (re.compile(r"\bcars?\b|\bev\b|electric vehicle|\bbattery\b|automaker", re.I),
     "electric car charging", "tin xe điện"),
    (re.compile(r"\bcoding\b|developer|programm|\bgithub\b|\bide\b|software engineer", re.I),
     "programmer typing code", "tin lập trình"),
    # Toan / khoa hoc / lop hoc (Ong Chu 12/09/2026: "AI giai toan gioi hoan toan
    # co the dung hinh bang den cong thuc lam hero, thieu idea den the a?"). Bang
    # nay truoc do khong co dong nao cho tin nghien cuu, nen tin toan roi thang
    # xuong chup khoi tit. Do Commons 12/09: "blackboard mathematical formulas"
    # ra 3 anh ngang >= 1600px; "laboratory bench scientist" 4; "classroom students" 4.
    (re.compile(r"\bmath(s|ematic\w*)?\b|\btheorem\b|\bproof\b|\bolympiad\b|\bimo\b|"
                r"\bequation|\balgebra|\bgeometr|\bcalculus\b|erd[oő]s", re.I),
     "blackboard mathematical formulas", "tin toán học"),
    (re.compile(r"\bscien(ce|tist)|\bresearch(er)?s?\b|\bphysic|\bchemist|\bbiolog|\bprotein|"
                r"\bgenom|\bnobel\b|\blab\b|laboratory", re.I),
     "laboratory bench scientist", "tin khoa học"),
    (re.compile(r"\bstudents?\b|\bschools?\b|\bteachers?\b|\bclassroom|\buniversit|\beducation|"
                r"\bexams?\b|\bhomework\b", re.I),
     "classroom students", "tin giáo dục"),
]

# Tên tệp Commons báo hiệu đồ hoạ, không phải ảnh chụp.
# BIÊN GIỚI TỪ cho icon/graph/chart (09/09/2026): ba từ này viết trần thì khớp
# CHUỖI CON và loại nhầm chính thứ đang cần — "icon" nằm trong "sil-icon" nên
# MỌI ảnh "silicon wafer" đều bị bỏ, mà đó là từ khoá khái niệm của toàn bộ tin
# bán dẫn; "graph" nằm trong "photograph"; "chart" nằm trong "Charterhouse".
# Bọc \b vẫn bắt đủ "App icon.png", "Bar graph.png", "Chart of...".
NAME_TYPE = re.compile(r"logo|\bicons?\b|emblem|coat of arms|\bseal\b|\bsvg\b|diagram|"
                      r"\bcharts?\b|\bgraphs?\b|"
                      # poster|drawing|illustration TUNG bi loai o day. Ong Chu 12/09/2026:
                      # "ảnh illustration cũng chả sao, The Economist còn dùng" — IMAGE_RULES §0
                      # cam TU VE, khong cam DUNG minh hoa co san. Van loai clipart/icon/so do.
                      r"screenshot|clipart|banner|badge|stamp|"
                      r"sticker|infographic|\bmap of\b(?!.*(satellite|relief))|locator map|"
                      r"\bcgi\b|variant|captured|render|3d\b|mockup|template|"
                      r"rising sun|ensign|naval|\bwar\b|military|protest", re.I)   # cờ chiến/biểu tình
FROM_DROP = {"of", "the", "in", "a", "an", "and", "with", "on", "at", "for"}


def _country_within(vb: str) -> list:
    """Tên nước chuẩn nhắc trong `vb`, theo thứ tự xuất hiện, không trùng."""
    ra = []
    # viết tắt phân biệt hoa thường: "US" là Mỹ, "us" là "chúng tôi".
    for m in re.finditer(r"\b(US|USA|UK|EU|UAE)\b", vb):
        t = COUNTRY_WRITE_ALL[m.group(1)]
        if t not in ra:
            ra.append(t)
    thap = vb.lower()
    for m in re.finditer(r"[a-z]+", thap):
        t = COUNTRY.get(m.group(0))
        if t and t not in ra:
            ra.append(t)
    for cum in ("abu dhabi",):
        if cum in thap and COUNTRY[cum] not in ra:
            ra.append(COUNTRY[cum])
    return ra


def keyword_heuristic(tieu_de: str, tom_tat: str = "") -> list:
    """Từ khoá theo bảng, không mạng. Nước trước (cờ), rồi chủ đề. Tối đa 3."""
    vb = f"{tieu_de or ''} {tom_tat or ''}"
    ra = []
    for nuoc in _country_within(vb)[:1]:
        ra.append({"tu_khoa": f"flag of {nuoc}", "ly_do": f"tin nhắc tới {nuoc}"})
    for mau, tk, ly_do in TOPIC:
        if mau.search(vb) and all(x["tu_khoa"] != tk for x in ra):
            ra.append({"tu_khoa": tk, "ly_do": ly_do})
        if len(ra) >= MAX_KEYWORD:
            break
    return ra[:MAX_KEYWORD]


def keyword_llm(tieu_de: str, tom_tat: str = "") -> list:
    """Hỏi model text qua router cục bộ thêm 1-3 từ khoá (tiếng Anh, vật thể thật).
    Router tắt / thiếu key / trả rác -> [] , không ném. Cùng model với con mắt
    của engine (flash, rẻ) — không mở thêm model."""
    env_load.load()
    import os
    key = os.environ.get("OPENAI_API_KEY")
    if not key or not tieu_de:
        return []
    # Thien kien PHONG MAY (Ong Chu 12/09/2026, hai lan): bo vi du "server racks"
    # roi model VAN de "computer server rack" cho tin toan — vi tin nao cung co
    # chu "AI". Nen phai CAM THANG, khong chi bo vi du. Minh hoa bien tap (ve
    # tay/digital nhu The Economist) duoc dung nhu anh chup — chi cam tu ve.
    #
    # NHAI LAI VI DU (LOW-191, 16/09/2026): ban cu ket bang mot cau "Pick the
    # thing the story is about (math -> chalkboard equations; law ->
    # courthouse; school -> classroom)" — mot danh sach "chu de -> dap an" co
    # san de chep, va model (flash, re, temperature=0) tra ve NGUYEN VAN ca
    # ba vi du cho tin "TypeSafe ra System One: nhanh hon 193,6 lan, re hon
    # 444,6 lan" — mot tin ve toc do/gia model, khong dinh gi toi toan/luat/
    # truong hoc. Anh Commons ra cho "laboratory bench" la tam chup vo nuoc
    # gan ban thi nghiem THAT, dung nghia den chu khong phai an du
    # "benchmark". Bo han cau vi du dang cap "chu de -> dap an" va ca list
    # vat the mau — khong con gi de chep nguyen van nua, chi con mo ta +
    # doi hoi bam vao chu THAT trong Story/Summary. Luoi thu hai (khong doi
    # con model) o `read_return_error_llm`: loai thang tu khoa nao TRUNG
    # NGUYEN VAN mot cum tung/dang nam trong prompt (ke ca ban truoc khi sua),
    # phong khi model van tu nho hoac ban sua sau nay lo dem vi du tro lai.
    hoi = ("You pick search keywords for Wikimedia Commons to illustrate a news story when "
           "the story itself has no usable image. A keyword must name ONE concrete, visible "
           "thing a camera could photograph — never an abstract idea (growth, partnership, AI, "
           "speed, cost).\n"
           "HARD RULE: do NOT suggest AI-industry hardware — server racks, data center, GPU, chip, "
           "circuit board, robot, computer screen — unless the story is literally about that hardware. "
           "Every story here is about AI; that is NOT a reason to show a machine room.\n"
           "Ground every keyword in a SPECIFIC noun or topic taken from the Story/Summary text below, "
           "not from these instructions.\n"
           "English only, 2-4 words each.\n"
           f"Story: {tieu_de}\n" + (f"Summary: {tom_tat[:400]}\n" if tom_tat else "")
           + "Answer with up to 3 lines, each exactly: KEYWORD: <keyword> | <why, 5 words>")
    body = {"model": env_load.VISION_MODEL, "thinking": {"type": "disabled"}, "max_tokens": 200,
            "stream": False, "temperature": 0,
            "messages": [{"role": "user", "content": hoi}]}
    try:
        req = urllib.request.Request(env_load.ROUTER_URL, data=json.dumps(body).encode(),
                                     headers={"Content-Type": "application/json",
                                              "Authorization": "Bearer " + key})
        raw = urllib.request.urlopen(req, timeout=60).read().decode().strip()
        if raw.startswith("data:"):
            raw = raw.split("data: [DONE]")[0].strip()[5:].strip()
        txt = json.loads(raw)["choices"][0]["message"]["content"]
    except Exception as e:                                   # noqa: BLE001
        print(f"[khai_niem] llm: {type(e).__name__}", file=sys.stderr)
        return []
    return read_return_error_llm(txt)


# Cac cum tung xuat hien lam VI DU trong prompt cua `keyword_llm` — ban hien
# tai lan ban truoc khi sua (LOW-191). Model tra ve NGUYEN VAN mot trong so
# nay nghia la no dang CHEP VI DU chu khong suy tu bai: do that 16/09/2026,
# tin "TypeSafe ra System One" (toc do/gia model) ra ca ba "chalkboard
# equations", "courthouse", "laboratory bench" — dung nguyen ba vi du cu,
# khong lien quan gi bai. Kiem NGUYEN VAN (khong phai substring) de khong
# chan nham cum hop le chua cung tu — "harvard laboratory bench renovation"
# vAn qua duoc. Giu ca vi du BAN CU (da bo khoi prompt) phong model con nho
# tu du lieu huan luyen truoc, hoac prompt bi sua lai vo tinh.
_PROMPT_ECHO = {
    "flag flying", "a flag flying", "building", "a building",
    "laboratory bench", "a laboratory bench", "product", "a product",
    "chalkboard", "a chalkboard", "chalkboard equations",
    "courthouse", "courthouse building", "classroom", "classroom students",
}


def read_return_error_llm(txt: str) -> list:
    """Bóc các dòng `KEYWORD: x | why` — thuần, test được.

    Bỏ luôn từ khoá NGUYÊN VĂN trùng một ví dụ minh hoạ trong prompt của
    `keyword_llm` (`_PROMPT_ECHO`) — dấu hiệu model nhại lại ví dụ chứ không
    suy ra từ bài (LOW-191)."""
    ra = []
    for m in re.finditer(r"KEYWORD\s*:\s*([^|\n]{3,60})(?:\|\s*([^\n]{0,80}))?", txt or ""):
        tk = re.sub(r"[^A-Za-z0-9 \-]", "", m.group(1)).strip().lower()
        if tk in _PROMPT_ECHO:
            print(f"[khai_niem] llm: bỏ từ khoá {tk!r} — trùng nguyên văn ví dụ trong prompt, "
                  "không phải suy ra từ bài", file=sys.stderr)
            continue
        if 1 <= len(tk.split()) <= 5 and tk not in [x["tu_khoa"] for x in ra]:
            ra.append({"tu_khoa": tk, "ly_do": (m.group(2) or "").strip()[:80] or "gợi ý của model"})
    return ra[:MAX_KEYWORD]


def keyword_concept(tieu_de: str, tom_tat: str = "", dung_llm: bool = True,
                      them: list | None = None) -> list:
    """Heuristic trước (chắc, không mạng), LLM bù cho tới 3 từ khoá.

    `them` (12/09/2026, bảng loại tin `story_type.py`): từ khoá do LOẠI TIN ép
    vào TRƯỚC heuristic — cờ nước của hãng (`COUNTRY_OF_RANK`), datacenter/nhà
    máy cho tin INFRA dù tiêu đề không có chữ nào khớp `TOPIC`. Trước đây cờ
    chỉ ra khi tiêu đề nhắc tên nước, nên tin Samsung không bao giờ ra cờ Hàn."""
    ra = [{"tu_khoa": t, "ly_do": "theo loại tin"} for t in (them or []) if t]
    for x in keyword_heuristic(tieu_de, tom_tat):
        if len(ra) >= MAX_KEYWORD:
            break
        if all(x["tu_khoa"] != y["tu_khoa"] for y in ra):
            ra.append(x)
    if dung_llm and len(ra) < MAX_KEYWORD:
        for x in keyword_llm(tieu_de, tom_tat):
            if len(ra) >= MAX_KEYWORD:
                break
            if all(x["tu_khoa"] != y["tu_khoa"] for y in ra):
                ra.append(x)
    return ra


def _from_distinctive(tu_khoa: str) -> list:
    return [w for w in re.findall(r"[a-z0-9]+", tu_khoa.lower()) if w not in FROM_DROP and len(w) >= 3]


def filter_commons(pages: dict, tu_khoa: str, so: int = 4, canh_ngan_min: int = 700) -> list:
    """Lọc `query.pages` của API Commons: ảnh bitmap đủ lớn, tên tệp có ít nhất
    HAI từ đặc trưng của từ khoá (không ép nguyên cụm như tìm tên hãng — "flag of
    Japan" hiếm khi nằm nguyên cụm trong tên tệp, nhưng "flag" và "japan" thì có), không phải đồ hoạ. Xếp ảnh to trước."""
    dac_trung = _from_distinctive(tu_khoa)
    ra = []
    for pg in (pages or {}).values():
        ii = (pg.get("imageinfo") or [{}])[0]
        w, h = ii.get("width", 0), ii.get("height", 0)
        if min(w, h) < canh_ngan_min or ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        ten = (pg.get("title") or "").replace("File:", "")
        ten_thap = ten.lower()
        if NAME_TYPE.search(ten_thap):
            continue
        # Đủ ít nhất hai từ đặc trưng (hoặc tất cả nếu từ khoá ngắn): "center"
        # một mình khớp cả "Center of Excellence".
        # Tu khoa DAI (>= 3 tu dac trung, thuong do LLM sinh: "mathematics blackboard
        # equations") hiem khi co 2 tu cung nam trong ten tep — do that 12/09/2026:
        # ca hai tu khoa toan hoc tra 0 anh. Voi loai do 1 tu khop la du; con mat
        # (sentence_ask_vision) moi la cong quyet dinh, khong phai ten tep.
        can = 1 if len(dac_trung) >= 3 else min(2, len(dac_trung))
        if dac_trung and sum(t in ten_thap for t in dac_trung) < can:
            continue
        ra.append({"image_url": ii.get("thumburl") or ii.get("url"), "alt": "Commons: " + ten, "og": False,
                   "mime": ii.get("mime"), "source": "concept", "page_url": "https://commons.wikimedia.org/wiki/File:" + ten.replace(" ", "_"),
                   "rong": w, "cao": h, "score": 20, "concept": {"keyword": tu_khoa}})
    # JPEG trước PNG: ảnh chụp thật gần như luôn là JPEG, PNG trên Commons hay là
    # cờ vẽ / bản dựng ("Japan flag - variant.png", "CGI Japan Flag.png").
    ra.sort(key=lambda c: (c["mime"] != "image/jpeg", -(c["rong"] * c["cao"])))
    return ra[:so]


def image_concept(tu_khoa: str, ly_do: str = "", so: int = 4) -> list | None:
    """Ứng viên ảnh khái niệm từ Commons cho một từ khoá. Trả None nếu không gọi
    được API (lỗi mạng/HTTP); [] nếu gọi được nhưng không có ảnh nào khớp."""
    import scan_common
    pages = scan_common.ask_commons(tu_khoa)                  # mot ban (ADF-r2-16), None = hong
    if pages is None:
        return None
    ra = filter_commons(pages, tu_khoa, so=so)
    for c in ra:
        c["concept"]["reason"] = ly_do
    return ra


def sentence_ask_vision(tieu_de: str, tu_khoa: str, theo_loai: bool = False) -> str:
    """Câu hỏi con mắt engine dành riêng cho ảnh khái niệm: không hỏi "có phải ảnh
    của tin" (chắc chắn không), hỏi "có đúng là <từ khoá>, chụp thật, hợp làm bìa".

    Chiều RÕ RÀNG (LOW-34, Ông Chủ chốt 12/09/2026). Ticket mở ra để hỏi "thế nào
    là ảnh đẹp" — Ông Chủ gạt luôn vế thẩm mỹ: *"ĐẸP hay ko thì ko phải vấn đề,
    nhưng ảnh hiển thị rõ ràng, có các object liên quan tới topic thì được tính
    là đẹp"*. Nên không có thang thẩm mỹ nào ở đây; chỉ hai điều kiện NHÌN LÀ
    THẤY, con mắt trả lời được:

      1. NHÌN RA ĐƯỢC vật chính — không phải một mảng rối không biết đang xem gì.
      2. Vật trong ảnh LIÊN QUAN topic của bài.

    Khác chiều "từ khoá có hợp bài không" (LOW-30) ở chỗ: ca đó chặn từ khoá SAI
    ngay từ đầu; chiều này chặn ca từ khoá ĐÚNG mà tấm ảnh vẫn vô dụng — vd
    "data center server racks" cho tin compute là đúng từ khoá, nhưng nếu tấm ảnh
    là một búi dây chằng chịt không nhận ra rack nào thì vẫn trượt."""
    # `theo_loai` (bang loai tin, 12/09/2026): tu khoa do LOAI TIN quy dinh (co nuoc
    # cua hang, bieu do gia, datacenter cho tin INFRA) — con mat KHONG duoc tu phan
    # "co nuoc thi lien quan gi bai xac minh tuoi": Ong Chu da chot co nuoc cua hang
    # LA vat lien quan. Chi con xet: co dung la vat do, chup that, nhin ra.
    quy_dinh = (f" Tu khoa \"{tu_khoa}\" do LOAI TIN quy dinh la vat lien quan (bang loai tin cua "
                "Ong Chu) — KHONG xet no co hop bai hay khong, coi nhu hop; chi xet anh co dung la "
                "vat do, nhin ra vat chinh." if theo_loai else "")
    # LOW-201 (16/09/2026, dao LOW-45): go IMAGE_PHRASES_SCREENSHOT khoi day —
    # xem prepare/vision.py cho do that va ly do day du.
    return (f"Bai bao: \"{tieu_de}\". Anh nay KHONG phai anh cua tin; no duoc tim lam ANH KHAI NIEM "
            f"theo tu khoa \"{tu_khoa}\" de lam anh bia.{quy_dinh}\nTra loi DUNG 2 dong:\n"
            "MO_TA: <mot cau tieng Viet co dau mo ta anh nay la gi>\n"
            f"LIEN_QUAN: co | khong  (co = anh chup that HOAC minh hoa bien tap (ve tay/digital) "
            f"ro net, dung la {tu_khoa}, khong co chu lon, "
            f"tu khoa \"{tu_khoa}\" that su hop chu de bai tren, VA nhin vao la NHAN RA NGAY vat "
            "chinh — vat do lien quan chu de bai; khong = khong phai thu do, so do/icon/clipart/"
            "ban do phang, mo, nhieu chu, logo, co nguoi ro mat, tu khoa lac chu de bai, "
            "HOAC anh roi/chat chung khong nhan ra vat gi la vat chinh du co dung tu khoa "
            "(khong can dep, chi can NHIN RA va lien quan)")


def label_concept(a: dict) -> dict:
    """Siết nhãn của một ảnh khái niệm ĐÃ qua `classify`: chỉ bìa/hero (hoặc ghép
    dọc nếu ngang), không vào thân, không chart, không mặt người. Thuần."""
    kn = a.get("concept") or {}
    tk, ly_do = kn.get("keyword", "?"), kn.get("reason", "")
    if a.get("kind") == "chart" or a.get("faces"):
        a["uses"] = []
        a["notes"].insert(0, "❌ ảnh khái niệm mà là chart/đồ hoạ hoặc có mặt người → KHÔNG DÙNG")
        return a
    if a.get("relevant") is False:
        return a                                  # classify đã xoá dung + ghi ❌
    if a.get("landscape"):
        a["uses"] = [d for d in a["uses"] if d == "stack_vertical"]
    else:
        a["uses"] = ["cover"]
    a["notes"] = [g for g in a["notes"] if "Wikimedia Commons" not in g]
    a["notes"].insert(0, f"🧭 ẢNH KHÁI NIỆM (từ khoá \"{tk}\"" + (f": {ly_do}" if ly_do else "") + ") "
                        "từ Wikimedia Commons — KHÔNG phải ảnh của tin; chỉ làm bìa/hero khi tin không có "
                        "ảnh riêng tốt hơn, không vào slide thân")
    return a
