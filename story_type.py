#!/usr/bin/env python3
"""LOẠI TIN → những VẬT được phép làm ảnh. Bảng định lượng, thuần, không mạng.

Ông Chủ chốt 12/09/2026 (đóng LOW-34 theo hướng thứ ba): *"thứ liên quan chỉ gói
gọn trong vài thứ, đã có trong cơ sở rồi... tóm lại, tìm relevant image ko hề
khó, hoàn toàn xây dựng logic định lượng được"*. Nguyên văn bảng:

    nhắc đến brand   → logo, trụ sở, founder, mã cổ phiếu, lá cờ quốc gia của brand
    thương vụ        → hình liên quan của HAI brand đặt vào
    model            → thêm hình benchmark
    hạ tầng          → datacenter, nhà máy, cloud server

Đo trước khi viết (12/09): `category` của mỗi tin đã được Finn/Vera gán từ lúc
quét (`manifest_build.VALID_CATEGORIES`), `approve_pick` ghi vào draft,
`prepare/manifest.py` chép vào `manifest.json` — nhưng engine ảnh (`image_prepare`,
`image_concept`, `image_brand`, `prepare/*`) KHÔNG đọc nó ở đâu cả. Bộ phân
loại đã chạy, bảng vật thể đã có (Wikidata P154/P112/P169, `SUFFIX`, `TOPIC`,
`NUOC`, `xep_hang`), chỉ thiếu dây nối. Tệp này là dây nối.

Hai bảng dữ liệu mới (chưa có ở đâu trong repo): `COUNTRY_OF_RANK` — hãng thuộc
nước nào (trước đây cờ chỉ ra khi TIÊU ĐỀ nhắc tên nước, nên tin Samsung không
bao giờ ra cờ Hàn) — và `CODE_HAS_BALLOT` — mã niêm yết để chụp biểu đồ giá.

Thuần để test được. Không import module nào của engine.
"""
import re

import manifest_values

# ---- loại tin -------------------------------------------------------------
# Tên chuẩn dùng trong bảng. Nhận cả tiếng Việt lẫn cách viết lệch của Finn/Vera.
_CHUAN = {
    "M&A": ("M&A", "MA", "M-A", "MERGER", "ACQUISITION", "THAU TOM", "THÂU TÓM", "THUONG VU", "THƯƠNG VỤ"),
    "MODEL": ("MODEL", "MO HINH", "MÔ HÌNH", "OPEN WEIGHTS", "OPEN SOURCE"),
    "BENCHMARK": ("BENCHMARK", "XEP HANG", "XẾP HẠNG"),
    "INFRA": ("INFRA", "HA TANG", "HẠ TẦNG"),
    "LAB": ("LAB",),
    "BUSINESS": ("BUSINESS", "KINH DOANH"),
    "SECURITY": ("SECURITY", "AN NINH"),
    "ARXIV": ("ARXIV", "RESEARCH", "NGHIEN CUU", "NGHIÊN CỨU"),
    "TOOL": ("TOOL", "CONG CU", "CÔNG CỤ", "ENGINEERING", "UPDATE", "THU NGHIEM", "THỬ NGHIỆM"),
}
_TRA = {bt.upper(): chuan for chuan, bts in _CHUAN.items() for bt in bts}


def standard_type(category) -> str:
    """'m&a' / 'Thâu tóm' / 'MO HINH' -> tên chuẩn; không biết -> ''."""
    t = re.sub(r"\s+", " ", (category or "").strip().upper())
    return _TRA.get(t, "")


# ---- bảng: loại tin → thứ tự vật được phép -----------------------------------
# Tên vật là tên NHÁNH TÌM đã có trong engine, không phải mô tả (mã English từ
# LOW-230; tên cũ in ra brief qua manifest_values.STORY_OBJECT_LABELS):
#   two_company_pair      ảnh của CẢ HAI hãng trong tin, để vai ghép (thương vụ)
#   ranking               bảng benchmark chụp từ trang xếp hạng (ranking.py)
#   announcement_chart    chart trong trang công bố chính chủ (_extra_announcement_page)
#   logo/headquarters/founder   image_brand: Wikidata P154 / SUFFIX / P112-P169
#   stock                 biểu đồ giá theo CODE_HAS_BALLOT (image_brand.image_has_ballot)
#   stock_exchange        TOPIC "stock exchange trading floor"
#   company_country_flag  cờ nước của hãng (COUNTRY_OF_RANK -> image_concept "flag of")
#   concept               bảng TOPIC theo chữ trong tiêu đề (đường cũ)
#   infrastructure_concept  từ khoá hạ tầng ép cho INFRA (KEYWORD_LOWER_LAYER)
# LOW-264 (19/09/2026, Ông Chủ): "logo > CEO/founder > trụ sở > bảng xếp hạng >
# mã cổ phiếu" — đảo hẳn thứ tự cũ (BUSINESS từng đặt cổ phiếu lên đầu, logo/
# founder xuống cuối). Áp cho MỌI loại tin xoay quanh MỘT hãng cụ thể (BUSINESS/
# M&A/LAB) — không đụng MODEL/BENCHMARK/INFRA/SECURITY/ARXIV/TOOL, bản chất tin
# khác hẳn (ưu tiên ranking/concept/announcement_chart, không phải ảnh CỦA một
# hãng). `two_company_pair` (M&A) và `company_country_flag` (LAB) là TÍNH NĂNG
# riêng — không phải một "loại ảnh" cạnh tranh với 5 mục này — nên vẫn giữ,
# chỉ chèn 5 mục vào đúng chỗ (M&A: two_company_pair trước, LAB: 5 mục trước
# rồi mới đến cờ nước, phương án cuối khi hết cả 5).
_UU_TIEN_ANH_HANG = ("logo", "founder", "headquarters", "ranking", "stock")
BOARD_IMAGE_BY_TYPE = {
    "M&A":       ("two_company_pair",) + _UU_TIEN_ANH_HANG,
    # LOW-337 (Ong Chu 21/09/2026): tin ve MODEL uu tien logo > benchmark/chart > founder > office.
    # Qwen-Image-2.1 ra the anh toa nha Alibaba trong khi engine da co san the logo + Jack Ma.
    "MODEL":     ("logo", "ranking", "announcement_chart", "founder", "headquarters", "concept"),
    "BENCHMARK": ("ranking", "announcement_chart", "logo"),
    "INFRA":     ("infrastructure_concept", "headquarters", "company_country_flag", "logo"),
    "LAB":       _UU_TIEN_ANH_HANG + ("company_country_flag",),
    "BUSINESS":  _UU_TIEN_ANH_HANG,
    "SECURITY":  ("concept", "logo"),
    "ARXIV":     ("announcement_chart", "concept", "logo"),
    "TOOL":      ("announcement_chart", "logo", "concept"),
}
DEFAULT = _UU_TIEN_ANH_HANG + ("concept",)   # tin không có category hợp lệ


def order_image(category) -> tuple:
    return BOARD_IMAGE_BY_TYPE.get(standard_type(category), DEFAULT)


def late(category, vat: str) -> bool:
    """Loại tin này có muốn vật `vat` không."""
    return vat in order_image(category)


def is_ranking_story_type(category) -> bool:
    """Loại tin này LÀ tin xếp hạng (bảng xếp hạng là ảnh CHÍNH, đứng đầu bảng —
    MODEL/BENCHMARK). Khác `late(category, "ranking")`: từ LOW-264 BUSINESS/M&A/
    LAB cũng có `ranking`, nhưng ở cuối bảng, như ảnh BỐI CẢNH của hãng — dùng
    `late` ở chỗ này từng ép mọi tin về một hãng thành tin xếp hạng (LOW-266)."""
    # LOW-337: MODEL dat logo len dau nhung van la tin xep hang (ranking o vi tri 2);
    # BUSINESS/M&A/LAB dat ranking o vi tri 4-5 nen van khong lot vao day (LOW-266).
    return "ranking" in order_image(category)[:2]


# Điểm cộng theo thứ tự trong bảng: vật đứng đầu +100, kế +80, +60, +40, +20,
# còn lại 0. Cộng vào `score` gốc của ứng viên (photo 28 / person 24 / logo 18;
# stock 30 / ranking 26 ở nơi khác) TRƯỚC khi `_round_brand` sort — để cùng
# một bộ ứng viên, tin M&A đẩy logo lên trước chân dung, tin LAB đẩy trụ sở/
# founder lên trước logo.
#
# LOW-264 (19/09/2026): biên độ CŨ chỉ chênh tối đa 8 (+8/+6/+4/+2/0) — nhỏ
# hơn chênh lệch điểm GỐC theo loại ảnh (photo 28 vs logo 18 = 12 điểm), nên dù
# bảng nói "logo đứng đầu", logo (18+8=26) vẫn thua trụ sở (28+4=32) trên thực
# tế — bảng thứ tự CHỈ có tác dụng in ra brief, không thật sự lật thứ tự chọn
# ảnh, cho MỌI loại tin chứ không riêng BUSINESS (đo: MODEL cũng đặt logo
# trước founder nhưng logo 18+4=22 < founder 24+2=26). Biên độ mới (100) áp
# đảo hẳn mọi chênh lệch điểm gốc hiện có, để bảng THẬT SỰ quyết định thứ tự.
# Khoá = brand_match.kind, giá trị = vật trong bảng trên.
_LOAI_UNG_VIEN = {"photo": "headquarters", "person": "founder", "logo": "logo", "stock": "stock"}


def score_by_type(category, loai_ung_vien: str) -> int:
    vat = _LOAI_UNG_VIEN.get(loai_ung_vien, loai_ung_vien)
    thu_tu = order_image(category)
    if vat not in thu_tu:
        return 0
    return max(0, 100 - 20 * thu_tu.index(vat))


# ---- hãng → nước (cờ) ----------------------------------------------------------
# Tên nước = tên chuẩn trong `image_concept.COUNTRY` để "flag of <nước>" khớp tên tệp
# Commons. Khoá = khoá hãng của `image_brand.DISPLAY_NAME`.
COUNTRY_OF_RANK = {
    "anthropic": "United States", "openai": "United States", "google deepmind": "United States",
    "meta": "United States", "microsoft": "United States", "nvidia": "United States",
    "amazon": "United States", "apple": "United States", "amd": "United States",
    "intel": "United States", "broadcom": "United States", "qualcomm": "United States",
    "oracle": "United States", "tesla": "United States", "xai": "United States",
    "perplexity": "United States", "databricks": "United States", "snowflake": "United States",
    "hugging face": "United States", "midjourney": "United States", "runway": "United States",
    "cohere": "Canada",
    "mistral": "France",
    "stability ai": "United Kingdom", "arm": "United Kingdom",
    "deepseek": "China", "alibaba": "China", "baidu": "China", "bytedance": "China",
    "tencent": "China", "huawei": "China", "xiaomi": "China", "zhipu": "China",
    "moonshot": "China", "minimax": "China", "01.ai": "China", "lenovo": "China",
    "tsmc": "Taiwan",
    "samsung": "South Korea",
    "softbank": "Japan", "sony": "Japan",
    "black forest": "Germany",
}


def country_of(khoa: str) -> str:
    return COUNTRY_OF_RANK.get((khoa or "").lower(), "")


# ---- hãng → mã cổ phiếu (định dạng Google Finance TICKER:SAN) ---------------------
# Chỉ hãng NIÊM YẾT. Hãng tư nhân (anthropic, openai, deepseek, mistral, xai...)
# không có — `image_has_ballot` bỏ qua, không đoán.
CODE_HAS_BALLOT = {
    "nvidia": "NVDA:NASDAQ", "microsoft": "MSFT:NASDAQ", "apple": "AAPL:NASDAQ",
    "amazon": "AMZN:NASDAQ", "meta": "META:NASDAQ", "google deepmind": "GOOGL:NASDAQ",
    "amd": "AMD:NASDAQ", "intel": "INTC:NASDAQ", "broadcom": "AVGO:NASDAQ",
    "qualcomm": "QCOM:NASDAQ", "tesla": "TSLA:NASDAQ", "snowflake": "SNOW:NYSE",
    "oracle": "ORCL:NYSE", "arm": "ARM:NASDAQ", "tsmc": "TSM:NYSE", "sony": "SONY:NYSE",
    "alibaba": "BABA:NYSE", "baidu": "BIDU:NASDAQ",
    "tencent": "0700:HKG", "xiaomi": "1810:HKG", "lenovo": "0992:HKG",
    "samsung": "005930:KRX", "softbank": "9984:TYO",
}


def code_has_ballot(khoa: str) -> str:
    return CODE_HAS_BALLOT.get((khoa or "").lower(), "")


# ---- hạ tầng: từ khoá ép khi category = INFRA mà tiêu đề không khớp TOPIC ------
KEYWORD_LOWER_LAYER = ("data center server racks", "factory assembly line")


# ---- dòng brief dùng chung cho Dre/Ethan/Kite ------------------------------------
def line_brief(m: dict) -> list:
    """Hai dòng cho brief của vai: loại tin muốn vật gì (để vai biết vì sao bộ ảnh
    có logo/cờ/biểu đồ giá), và cặp ảnh hai hãng khi là thương vụ. Thuần."""
    ra = []
    loai = standard_type(m.get("category"))
    if loai:
        ra.append(f"Loại tin {loai} → ảnh hợp lệ theo thứ tự: "
                  + " > ".join(manifest_values.story_object_label(v) for v in order_image(loai))
                  + " (bảng story_type.py, Ông Chủ 12/09/2026).")
    if m.get("two_company_pairs"):
        ra.append("THƯƠNG VỤ: ghép ảnh của HAI hãng — " +
                  ", ".join("+".join(c) for c in m["two_company_pairs"]) +
                  " (logo+logo hoặc trụ sở+trụ sở, xếp dọc, cùng tone).")
    return ra
