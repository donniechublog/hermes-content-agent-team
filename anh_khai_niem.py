#!/usr/bin/env python3
"""Ảnh KHÁI NIỆM cho hero/bìa khi tin không có ảnh riêng — kỹ năng cũ của Dre,
nay là của engine.

Vì sao có tệp này (Ông Chủ 07/09/2026): "các Designer có vẻ mất kỹ năng tìm
hình trên internet, trong resource gốc không có hình hoặc hình không đạt là bỏ
qua luôn. Nhắc tới Nhật thì tìm cờ hoặc bản đồ nước Nhật, Nhật đầu tư xây
compute thì lấy hình datacenter". Trước 04/09 Dre có web_search nên tự làm;
từ kiến trúc 3 lớp vai không còn công cụ, còn `anh_chuan_bi` chỉ tìm ảnh CÙNG
TIN (Bing News + Commons theo tên hãng) — không ai tìm ảnh CÙNG KHÁI NIỆM nữa,
nên tin không ảnh đi thẳng sang Kite. Sửa ở engine để cả Ethan, Dre, Kite cùng
hưởng, đúng luật "vai chỉ chọn mã".

Ảnh khái niệm là ẢNH THẬT (cờ đang bay, toà nhà, dãy rack máy chủ) lấy từ
Wikimedia Commons — không vẽ, không AI. Nó chỉ được làm BÌA/HERO, đứng sau mọi
ảnh riêng của tin; caption "via Wikimedia Commons" do renderer ghi.

Ba phần, phần nào cũng thuần để test được:
  - `tu_khoa_khai_niem`  tiêu đề (+ tóm tắt) -> [{tu_khoa, ly_do}], ≤ 3;
                         heuristic bảng nước + chủ đề, thêm LLM khi có router.
  - `loc_commons`        lọc trang trả về của API Commons theo từ khoá.
  - `nhan_khai_niem`     siết nhãn "dùng được" của một ảnh đã phân loại.
"""
import json
import re
import sys
import urllib.request

import env_load

# Wikimedia doi UA co ten cong cu + duong lien he, khong nhan UA kieu trinh
# duyet (403, do 09/09/2026) -> dung chung mot cho: env_load.UA_WIKI.
UA = env_load.UA_WIKI
TOI_DA_TU_KHOA = 3

# Tên nước / khối -> tên chuẩn (khoá là chữ thường, khớp theo từ nguyên).
# Tính từ (Japanese) và tên (Japan) cùng về một chỗ.
NUOC = {}
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
        NUOC[_b] = _chuan
# Hai chữ hoa đứng riêng: "US", "UK" — khớp có phân biệt hoa thường ở dưới.
NUOC_VIET_TAT = {"US": "United States", "USA": "United States", "UK": "United Kingdom",
                 "EU": "European Union", "UAE": "United Arab Emirates"}

# Chủ đề -> vật thể THẬT chụp được. Không đưa khái niệm trừu tượng (funding,
# partnership) vì Commons chỉ trả ảnh minh hoạ tệ cho những thứ đó.
CHU_DE = [
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
]

# Tên tệp Commons báo hiệu đồ hoạ, không phải ảnh chụp.
# BIÊN GIỚI TỪ cho icon/graph/chart (09/09/2026): ba từ này viết trần thì khớp
# CHUỖI CON và loại nhầm chính thứ đang cần — "icon" nằm trong "sil-icon" nên
# MỌI ảnh "silicon wafer" đều bị bỏ, mà đó là từ khoá khái niệm của toàn bộ tin
# bán dẫn; "graph" nằm trong "photograph"; "chart" nằm trong "Charterhouse".
# Bọc \b vẫn bắt đủ "App icon.png", "Bar graph.png", "Chart of...".
TEN_LOAI = re.compile(r"logo|\bicons?\b|emblem|coat of arms|\bseal\b|\bsvg\b|diagram|"
                      r"\bcharts?\b|\bgraphs?\b|"
                      r"screenshot|poster|drawing|illustration|clipart|banner|badge|stamp|"
                      r"sticker|infographic|\bmap of\b(?!.*(satellite|relief))|locator map|"
                      r"\bcgi\b|variant|captured|render|3d\b|mockup|template|"
                      r"rising sun|ensign|naval|\bwar\b|military|protest", re.I)   # cờ chiến/biểu tình
TU_BO = {"of", "the", "in", "a", "an", "and", "with", "on", "at", "for"}


def _nuoc_trong(vb: str) -> list:
    """Tên nước chuẩn nhắc trong `vb`, theo thứ tự xuất hiện, không trùng."""
    ra = []
    # viết tắt phân biệt hoa thường: "US" là Mỹ, "us" là "chúng tôi".
    for m in re.finditer(r"\b(US|USA|UK|EU|UAE)\b", vb):
        t = NUOC_VIET_TAT[m.group(1)]
        if t not in ra:
            ra.append(t)
    thap = vb.lower()
    for m in re.finditer(r"[a-z]+", thap):
        t = NUOC.get(m.group(0))
        if t and t not in ra:
            ra.append(t)
    for cum in ("abu dhabi",):
        if cum in thap and NUOC[cum] not in ra:
            ra.append(NUOC[cum])
    return ra


def tu_khoa_heuristic(tieu_de: str, tom_tat: str = "") -> list:
    """Từ khoá theo bảng, không mạng. Nước trước (cờ), rồi chủ đề. Tối đa 3."""
    vb = f"{tieu_de or ''} {tom_tat or ''}"
    ra = []
    for nuoc in _nuoc_trong(vb)[:1]:
        ra.append({"tu_khoa": f"flag of {nuoc}", "ly_do": f"tin nhắc tới {nuoc}"})
    for mau, tk, ly_do in CHU_DE:
        if mau.search(vb) and all(x["tu_khoa"] != tk for x in ra):
            ra.append({"tu_khoa": tk, "ly_do": ly_do})
        if len(ra) >= TOI_DA_TU_KHOA:
            break
    return ra[:TOI_DA_TU_KHOA]


def tu_khoa_llm(tieu_de: str, tom_tat: str = "") -> list:
    """Hỏi model text qua router cục bộ thêm 1-3 từ khoá (tiếng Anh, vật thể thật).
    Router tắt / thiếu key / trả rác -> [] , không ném. Cùng model với con mắt
    của engine (flash, rẻ) — không mở thêm model."""
    env_load.nap()
    import os
    key = os.environ.get("OPENAI_API_KEY")
    if not key or not tieu_de:
        return []
    hoi = ("You pick REAL-PHOTO search keywords for Wikimedia Commons to illustrate a news "
           "story when the story itself has no usable image. Keywords must name concrete, "
           "photographable things (a flag flying, a building, server racks, a product), never "
           "abstract ideas (growth, partnership, AI). English only, 2-4 words each.\n"
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
    return doc_tra_loi_llm(txt)


def doc_tra_loi_llm(txt: str) -> list:
    """Bóc các dòng `KEYWORD: x | why` — thuần, test được."""
    ra = []
    for m in re.finditer(r"KEYWORD\s*:\s*([^|\n]{3,60})(?:\|\s*([^\n]{0,80}))?", txt or ""):
        tk = re.sub(r"[^A-Za-z0-9 \-]", "", m.group(1)).strip().lower()
        if 1 <= len(tk.split()) <= 5 and tk not in [x["tu_khoa"] for x in ra]:
            ra.append({"tu_khoa": tk, "ly_do": (m.group(2) or "").strip()[:80] or "gợi ý của model"})
    return ra[:TOI_DA_TU_KHOA]


def tu_khoa_khai_niem(tieu_de: str, tom_tat: str = "", dung_llm: bool = True) -> list:
    """Heuristic trước (chắc, không mạng), LLM bù cho tới 3 từ khoá."""
    ra = tu_khoa_heuristic(tieu_de, tom_tat)
    if dung_llm and len(ra) < TOI_DA_TU_KHOA:
        for x in tu_khoa_llm(tieu_de, tom_tat):
            if len(ra) >= TOI_DA_TU_KHOA:
                break
            if all(x["tu_khoa"] != y["tu_khoa"] for y in ra):
                ra.append(x)
    return ra


def _tu_dac_trung(tu_khoa: str) -> list:
    return [w for w in re.findall(r"[a-z0-9]+", tu_khoa.lower()) if w not in TU_BO and len(w) >= 3]


def loc_commons(pages: dict, tu_khoa: str, so: int = 4, canh_ngan_min: int = 700) -> list:
    """Lọc `query.pages` của API Commons: ảnh bitmap đủ lớn, tên tệp có ít nhất
    HAI từ đặc trưng của từ khoá (không ép nguyên cụm như tìm tên hãng — "flag of
    Japan" hiếm khi nằm nguyên cụm trong tên tệp, nhưng "flag" và "japan" thì có), không phải đồ hoạ. Xếp ảnh to trước."""
    dac_trung = _tu_dac_trung(tu_khoa)
    ra = []
    for pg in (pages or {}).values():
        ii = (pg.get("imageinfo") or [{}])[0]
        w, h = ii.get("width", 0), ii.get("height", 0)
        if min(w, h) < canh_ngan_min or ii.get("mime") not in ("image/jpeg", "image/png"):
            continue
        ten = (pg.get("title") or "").replace("File:", "")
        ten_thap = ten.lower()
        if TEN_LOAI.search(ten_thap):
            continue
        # Đủ ít nhất hai từ đặc trưng (hoặc tất cả nếu từ khoá ngắn): "center"
        # một mình khớp cả "Center of Excellence".
        if dac_trung and sum(t in ten_thap for t in dac_trung) < min(2, len(dac_trung)):
            continue
        ra.append({"anh": ii.get("thumburl") or ii.get("url"), "alt": "Commons: " + ten, "og": False,
                   "mime": ii.get("mime"), "tu": "khai_niem", "trang": "https://commons.wikimedia.org/wiki/File:" + ten.replace(" ", "_"),
                   "rong": w, "cao": h, "diem": 20, "khai_niem": {"tu_khoa": tu_khoa}})
    # JPEG trước PNG: ảnh chụp thật gần như luôn là JPEG, PNG trên Commons hay là
    # cờ vẽ / bản dựng ("Japan flag - variant.png", "CGI Japan Flag.png").
    ra.sort(key=lambda c: (c["mime"] != "image/jpeg", -(c["rong"] * c["cao"])))
    return ra[:so]


def anh_khai_niem(tu_khoa: str, ly_do: str = "", so: int = 4) -> list | None:
    """Ứng viên ảnh khái niệm từ Commons cho một từ khoá. Trả None nếu không gọi
    được API (lỗi mạng/HTTP); [] nếu gọi được nhưng không có ảnh nào khớp."""
    import quet_chung
    pages = quet_chung.hoi_commons(tu_khoa)                  # mot ban (ADF-r2-16), None = hong
    if pages is None:
        return None
    ra = loc_commons(pages, tu_khoa, so=so)
    for c in ra:
        c["khai_niem"]["ly_do"] = ly_do
    return ra


def cau_hoi_vision(tieu_de: str, tu_khoa: str) -> str:
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
    return (f"Bai bao: \"{tieu_de}\". Anh nay KHONG phai anh cua tin; no duoc tim lam ANH KHAI NIEM "
            f"theo tu khoa \"{tu_khoa}\" de lam anh bia.\nTra loi DUNG 2 dong:\n"
            "MO_TA: <mot cau tieng Viet co dau mo ta anh nay la gi>\n"
            f"LIEN_QUAN: co | khong  (co = anh CHUP THAT, ro net, dung la {tu_khoa}, khong co chu lon, "
            f"tu khoa \"{tu_khoa}\" that su hop chu de bai tren, VA nhin vao la NHAN RA NGAY vat "
            "chinh — vat do lien quan chu de bai; khong = khong phai thu do, do hoa/ban ve/so do/"
            "ban do phang, mo, nhieu chu, logo, co nguoi ro mat, tu khoa lac chu de bai, HOAC anh "
            "roi/chat chung khong nhan ra vat gi la vat chinh du co dung tu khoa "
            "(khong can dep, chi can NHIN RA va lien quan)")


def nhan_khai_niem(a: dict) -> dict:
    """Siết nhãn của một ảnh khái niệm ĐÃ qua `phan_loai`: chỉ bìa/hero (hoặc ghép
    dọc nếu ngang), không vào thân, không chart, không mặt người. Thuần."""
    kn = a.get("khai_niem") or {}
    tk, ly_do = kn.get("tu_khoa", "?"), kn.get("ly_do", "")
    if a.get("loai") == "chart" or a.get("mat"):
        a["dung"] = []
        a["ghi_chu"].insert(0, "❌ ảnh khái niệm mà là chart/đồ hoạ hoặc có mặt người → KHÔNG DÙNG")
        return a
    if a.get("lien_quan") is False:
        return a                                  # phan_loai đã xoá dung + ghi ❌
    if a.get("ngang"):
        a["dung"] = [d for d in a["dung"] if d.startswith("ghép dọc")]
    else:
        a["dung"] = ["bìa"]
    a["ghi_chu"] = [g for g in a["ghi_chu"] if "Wikimedia Commons" not in g]
    a["ghi_chu"].insert(0, f"🧭 ẢNH KHÁI NIỆM (từ khoá \"{tk}\"" + (f": {ly_do}" if ly_do else "") + ") "
                        "từ Wikimedia Commons — KHÔNG phải ảnh của tin; chỉ làm bìa/hero khi tin không có "
                        "ảnh riêng tốt hơn, không vào slide thân")
    return a
