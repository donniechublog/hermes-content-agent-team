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
quét (`manifest_build.VALID_CATEGORIES`), `duyet_chon_tin` ghi vào draft,
`chuan_bi/manifest.py` chép vào `xong.json` — nhưng engine ảnh (`anh_chuan_bi`,
`anh_khai_niem`, `anh_thuong_hieu`, `chuan_bi/*`) KHÔNG đọc nó ở đâu cả. Bộ phân
loại đã chạy, bảng vật thể đã có (Wikidata P154/P112/P169, `HAU_TO`, `CHU_DE`,
`NUOC`, `xep_hang`), chỉ thiếu dây nối. Tệp này là dây nối.

Hai bảng dữ liệu mới (chưa có ở đâu trong repo): `NUOC_CUA_HANG` — hãng thuộc
nước nào (trước đây cờ chỉ ra khi TIÊU ĐỀ nhắc tên nước, nên tin Samsung không
bao giờ ra cờ Hàn) — và `MA_CO_PHIEU` — mã niêm yết để chụp biểu đồ giá.

Thuần để test được. Không import module nào của engine.
"""
import re

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


def chuan_loai(category) -> str:
    """'m&a' / 'Thâu tóm' / 'MO HINH' -> tên chuẩn; không biết -> ''."""
    t = re.sub(r"\s+", " ", (category or "").strip().upper())
    return _TRA.get(t, "")


# ---- bảng: loại tin → thứ tự vật được phép -----------------------------------
# Tên vật là tên NHÁNH TÌM đã có trong engine, không phải mô tả:
#   ghep_hai_hang  ảnh của CẢ HAI hãng trong tin, để vai ghép (thương vụ)
#   xep_hang       bảng benchmark chụp từ trang xếp hạng (xep_hang.py)
#   chart_cong_bo  chart trong trang công bố chính chủ (_them_trang_cong_bo)
#   logo/tru_so/founder   anh_thuong_hieu: Wikidata P154 / HAU_TO / P112-P169
#   co_phieu       biểu đồ giá theo MA_CO_PHIEU (anh_thuong_hieu.anh_co_phieu)
#   san_giao_dich  CHU_DE "stock exchange trading floor"
#   co_nuoc_hang   cờ nước của hãng (NUOC_CUA_HANG -> anh_khai_niem "flag of")
#   khai_niem      bảng CHU_DE theo chữ trong tiêu đề (đường cũ)
BANG_ANH_THEO_LOAI = {
    "M&A":       ("ghep_hai_hang", "logo", "tru_so", "founder", "co_phieu"),
    "MODEL":     ("xep_hang", "chart_cong_bo", "logo", "founder", "khai_niem"),
    "BENCHMARK": ("xep_hang", "chart_cong_bo", "logo"),
    "INFRA":     ("khai_niem_ha_tang", "tru_so", "co_nuoc_hang", "logo"),
    "LAB":       ("tru_so", "founder", "logo", "co_nuoc_hang"),
    "BUSINESS":  ("co_phieu", "san_giao_dich", "tru_so", "logo", "founder"),
    "SECURITY":  ("khai_niem", "logo"),
    "ARXIV":     ("chart_cong_bo", "khai_niem", "logo"),
    "TOOL":      ("chart_cong_bo", "logo", "khai_niem"),
}
MAC_DINH = ("tru_so", "founder", "logo", "khai_niem")   # tin không có category hợp lệ


def thu_tu_anh(category) -> tuple:
    return BANG_ANH_THEO_LOAI.get(chuan_loai(category), MAC_DINH)


def muon(category, vat: str) -> bool:
    """Loại tin này có muốn vật `vat` không."""
    return vat in thu_tu_anh(category)


# Điểm cộng theo thứ tự trong bảng: vật đứng đầu +8, kế +6, +4, +2, còn lại 0.
# Cộng vào `diem` gốc của ứng viên (anh 28 / nguoi 24 / logo 18) TRƯỚC khi
# `_vong_thuong_hieu` sort — để cùng một bộ ứng viên, tin M&A đẩy logo lên
# trước chân dung, tin LAB đẩy trụ sở/founder lên trước logo.
_LOAI_UNG_VIEN = {"anh": "tru_so", "nguoi": "founder", "logo": "logo", "co_phieu": "co_phieu"}


def diem_theo_loai(category, loai_ung_vien: str) -> int:
    vat = _LOAI_UNG_VIEN.get(loai_ung_vien, loai_ung_vien)
    thu_tu = thu_tu_anh(category)
    if vat not in thu_tu:
        return 0
    return max(0, 8 - 2 * thu_tu.index(vat))


# ---- hãng → nước (cờ) ----------------------------------------------------------
# Tên nước = tên chuẩn trong `anh_khai_niem.NUOC` để "flag of <nước>" khớp tên tệp
# Commons. Khoá = khoá hãng của `anh_thuong_hieu.TEN_HIEN`.
NUOC_CUA_HANG = {
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


def nuoc_cua(khoa: str) -> str:
    return NUOC_CUA_HANG.get((khoa or "").lower(), "")


# ---- hãng → mã cổ phiếu (định dạng Google Finance TICKER:SAN) ---------------------
# Chỉ hãng NIÊM YẾT. Hãng tư nhân (anthropic, openai, deepseek, mistral, xai...)
# không có — `anh_co_phieu` bỏ qua, không đoán.
MA_CO_PHIEU = {
    "nvidia": "NVDA:NASDAQ", "microsoft": "MSFT:NASDAQ", "apple": "AAPL:NASDAQ",
    "amazon": "AMZN:NASDAQ", "meta": "META:NASDAQ", "google deepmind": "GOOGL:NASDAQ",
    "amd": "AMD:NASDAQ", "intel": "INTC:NASDAQ", "broadcom": "AVGO:NASDAQ",
    "qualcomm": "QCOM:NASDAQ", "tesla": "TSLA:NASDAQ", "snowflake": "SNOW:NYSE",
    "oracle": "ORCL:NYSE", "arm": "ARM:NASDAQ", "tsmc": "TSM:NYSE", "sony": "SONY:NYSE",
    "alibaba": "BABA:NYSE", "baidu": "BIDU:NASDAQ",
    "tencent": "0700:HKG", "xiaomi": "1810:HKG", "lenovo": "0992:HKG",
    "samsung": "005930:KRX", "softbank": "9984:TYO",
}


def ma_co_phieu(khoa: str) -> str:
    return MA_CO_PHIEU.get((khoa or "").lower(), "")


# ---- hạ tầng: từ khoá ép khi category = INFRA mà tiêu đề không khớp CHU_DE ------
TU_KHOA_HA_TANG = ("data center server racks", "factory assembly line")


# ---- dòng brief dùng chung cho Dre/Ethan/Kite ------------------------------------
def dong_brief(m: dict) -> list:
    """Hai dòng cho brief của vai: loại tin muốn vật gì (để vai biết vì sao bộ ảnh
    có logo/cờ/biểu đồ giá), và cặp ảnh hai hãng khi là thương vụ. Thuần."""
    ra = []
    loai = chuan_loai(m.get("category"))
    if loai:
        ra.append(f"Loại tin {loai} → ảnh hợp lệ theo thứ tự: " + " > ".join(thu_tu_anh(loai))
                  + " (bảng loai_tin.py, Ông Chủ 12/09/2026).")
    if m.get("ghep_hai_hang"):
        ra.append("THƯƠNG VỤ: ghép ảnh của HAI hãng — " +
                  ", ".join("+".join(c) for c in m["ghep_hai_hang"]) +
                  " (logo+logo hoặc trụ sở+trụ sở, xếp dọc, cùng tone).")
    return ra
