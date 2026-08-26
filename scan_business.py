#!/usr/bin/env python3
"""Quet tin DAU TU / KINH TE / DOANH NGHIEP / THUONG HIEU quanh AI — tat dinh.

Viec cua Vera (profile market). Khac hai vai kia:
  - Finn quet HN/Reddit/arXiv: tin ky thuat, can co nguoi ban luan.
  - Nova doc so dang ky model: model nao vua ra, manh yeu the nao.
  - Vera doc bao kinh doanh: tien di dau, ai mua ai, chinh sach nao vua doi,
    nghe nao sap mat viec.

Xuong song la Google News RSS: mien phi, khong khoa, va quan trong nhat la
TRUY VAN TU DO — muon theo doi chu de moi thi them mot dong vao TRUY_VAN, khong
phai di tim nguon moi. Da do song: 'Anthropic IPO' ra 92 bai, 'AI acquisition'
ra 100 bai trong do co dung tin Stripe mua OpenRouter.

Bo sung vai feed bao cong nghe de khong phu thuoc mot nha.

Chong trung: Google News tra ve cung mot su kien tu nhieu bao. Gom theo tieu de
da chuan hoa (bo ten toa soan phia sau dau gach, bo dau cau, ha chu thuong) roi
giu ban som nhat, nen mot su kien chi hien mot lan du muoi bao dua tin.
"""
import argparse
import json
import re
import sys
import time
import unicodedata
import urllib.parse as up
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import httpx

ROOT = Path.home() / "content-team"
STATE = ROOT / "state" / "business_seen.json"
UA = "Mozilla/5.0 (compatible; donniechu-scout/1.0)"
GNEWS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

# Moi dong la mot goc theo doi. Them chu de moi = them mot dong.
TRUY_VAN = [
    ("gọi vốn / IPO", "AI startup IPO OR funding round OR valuation when:7d"),
    ("thâu tóm", "AI company acquisition OR acquires OR merger when:7d"),
    ("hạ tầng & vốn lớn", "AI datacenter investment billion when:7d"),
    ("chính sách & nhãn AI", "AI generated content label OR watermark OR disclosure policy when:14d"),
    ("lao động & việc làm", "AI job losses OR layoffs OR humanoid robot workers when:14d"),
    ("thương hiệu & sản phẩm", "brand launches AI product OR partnership when:7d"),
    ("kiện tụng & bản quyền", "AI copyright lawsuit OR settlement when:14d"),
    # Ba nhom them sau khi doi chieu voi mot ban tin ben ngoai va thay bo sot:
    # Databricks goi von $5 ty va Snowflake/TrueFoundry deu la ha tang du lieu
    # doanh nghiep, khong nhom nao trong sau nhom tren phu toi.
    ("hạ tầng dữ liệu doanh nghiệp",
     "data platform OR data warehouse AI funding OR valuation when:7d"),
    ("MLOps & công cụ triển khai",
     "MLOps OR inference platform OR model serving startup when:7d"),
    ("chip & bán dẫn cho AI",
     "AI chip deal OR semiconductor financing OR foundry capacity when:7d"),
    # Them 26/08: nhom tren chi bat DEAL/tai chinh chip, khong bat RA MAT san
    # pham. Xiaomi ra mat AI Cube (mini PC chay chip Xring) phu day tren Reuters
    # va Bloomberg ma khong dong nao cham toi: "brand launches AI product" qua
    # chung nen Google News chon no xuong duoi 50 tin khac. Dong nay nham thang
    # vao ra mat chip / phan cung AI.
    ("ra mắt chip & phần cứng AI",
     "AI chip OR processor OR NPU OR mini PC unveils OR launches OR announces when:7d"),
]

# Feed bao de khong phu thuoc mot minh Google News
RSS_BAO = [
    ("TechCrunch", "https://techcrunch.com/category/artificial-intelligence/feed/"),
    ("The Verge", "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml"),
]

# Toa soan uy tin — dung de xep do tin cay, khong dung de loai bo
BAO_LON = ("reuters", "bloomberg", "financial times", "wall street journal", "wsj",
           "the information", "cnbc", "axios", "forbes", "fortune", "nytimes",
           "new york times", "the economist", "techcrunch", "the verge", "ft.com")

# WATCHLIST — cac ten trong nganh AI ma tin ve chung PHAI theo sat, bat ke may
# bao dua hay diem co hoc bao nhieu. Day la nguyen tac chu khong phai goi y: tin
# ve mot ten trong day KHONG BAO GIO bi cat truoc khi Vera nhin (xem chon_cho_vera).
#
# Vi sao can rieng danh sach nay: diem co hoc xep hang theo "nhieu bao dua". Google
# News RSS chi tra vai bien the tit cho mot su kien, moi bien the mot bao, nen tin
# lon nhung chi hien vai dong (Xiaomi ra mat AI Cube, Apple ra chip M6) bi cham
# thap va cat mat. Ma day la nhung thu tac dong ca nganh. MiMo cua Xiaomi tung la
# model tieu thu token nhieu nhat the gioi truoc khi v4-flash ra; bo tin Xiaomi la
# bo dung loai tin quan trong nhat.
#
# Gom ca TEN HANG lan TEN MODEL/CHIP, vi tin thuong goi ten san pham chu khong goi
# ten hang (vd "MiMo", "M6", "Xring", "Gemini" thay vi "Xiaomi", "Apple", "Google").
WATCHLIST = (
    # phong thi nghiem & hang lam model
    "openai", "chatgpt", "gpt", "anthropic", "claude", "google deepmind",
    "deepmind", "gemini", "meta ai", "llama", "mistral", "mixtral", "cohere",
    "perplexity", "xai", "grok", "stability ai", "stable diffusion", "midjourney",
    "runway", "hugging face", "black forest", "flux",
    # hang Trung Quoc & model
    "deepseek", "qwen", "alibaba", "tongyi", "bytedance", "doubao", "tencent",
    "hunyuan", "baidu", "ernie", "moonshot", "kimi", "zhipu", "glm", "minimax",
    "xiaomi", "mimo", "xring", "01.ai", "yi ",
    # hang phan cung & nen tang lon
    "nvidia", "apple", "microsoft", "amazon", "aws", "samsung", "huawei",
    "qualcomm", "intel", "amd", "tsmc", "arm", "broadcom", "sony", "tesla",
    "databricks", "snowflake", "oracle", "softbank", "lenovo",
)


# Nhieu ten cung mot hang: gom ve mot moi de "cuu" khong dem Xiaomi/MiMo/Xring
# thanh ba hang khac nhau, va de OpenAI/ChatGPT/GPT khong chiem ba suat.
HANG_CUA_TEN = {
    "chatgpt": "openai", "gpt": "openai",
    "claude": "anthropic",
    "gemini": "google deepmind", "deepmind": "google deepmind",
    "google deepmind": "google deepmind",
    "meta ai": "meta", "llama": "meta",
    "mixtral": "mistral",
    "stable diffusion": "stability ai",
    "tongyi": "alibaba", "qwen": "alibaba",
    "doubao": "bytedance", "hunyuan": "tencent", "ernie": "baidu",
    "kimi": "moonshot", "glm": "zhipu",
    "mimo": "xiaomi", "xring": "xiaomi",
    "aws": "amazon",
    "flux": "black forest", "yi ": "01.ai",
}


def ten_watchlist(tieu_de: str) -> str | None:
    """Ten HANG trong watchlist ma tin nay noi toi, hoac None.

    So theo BIEN GIOI TU de "arm" khong khop "harm", "yi" khong khop "yield".
    Ten model/chip (MiMo, Gemini...) duoc quy ve hang chu (Xiaomi, Google) qua
    HANG_CUA_TEN, de khau "cuu" dam bao du HANG chu khong trung mot hang nhieu lan.
    """
    td = " " + tieu_de.lower() + " "
    for ten in WATCHLIST:
        khop = (ten in td) if " " in ten else (
            f" {ten} " in td or f" {ten}'" in td
            or f" {ten}," in td or f" {ten}." in td or f" {ten}:" in td)
        if khop:
            return HANG_CUA_TEN.get(ten, ten)
    return None


def trong_watchlist(tieu_de: str) -> bool:
    return ten_watchlist(tieu_de) is not None


# Dong tu ra mat: dung de UU TIEN khi cuu tin watchlist, khong dung de cham diem.
# Tin ra mat chip/model/san pham cua hang lon la loai tac dong ca nganh (Apple M6,
# Xiaomi AI Cube), phai noi len tren tin lat vat (kien tung, co phieu) cung hang.
DONG_TU_RA_MAT = ("unveil", "launch", "announce", "introduce", "reveal", "debut",
                  "release", "roll out", "ra mat", "gioi thieu", "trinh lang")


def la_ra_mat(tieu_de: str) -> bool:
    return any(v in tieu_de.lower() for v in DONG_TU_RA_MAT)


def _get(url: str, timeout=40) -> httpx.Response:
    # Khong xin brotli: mot so may chu (OpenAI) tra luong brotli lam httpx nghen.
    return httpx.get(url, timeout=timeout, follow_redirects=True,
                     headers={"User-Agent": UA, "Accept-Encoding": "gzip, deflate"})


def _ts(txt: str) -> float:
    for f in (lambda t: parsedate_to_datetime(t).timestamp(),
              lambda t: datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()):
        try:
            return f(txt)
        except Exception:                                    # noqa: BLE001
            continue
    return 0.0


def chuan_hoa(tieu_de: str) -> str:
    """Rut tieu de ve dang so sanh duoc, de gom cac bao dua cung mot tin.

    Google News gan ' - Ten Toa Soan' vao cuoi. Cat phan do truoc, roi bo dau
    cau va ha chu thuong."""
    t = re.sub(r"\s+-\s+[^-]{2,40}$", "", tieu_de).strip()
    t = unicodedata.normalize("NFKD", t)
    t = re.sub(r"[^\w\s]", " ", t.lower())
    return re.sub(r"\s+", " ", t).strip()


def toa_soan(tieu_de: str) -> str:
    m = re.search(r"\s+-\s+([^-]{2,40})$", tieu_de)
    return m.group(1).strip() if m else ""


def quet_gnews(gio_toi_da: int) -> list:
    nguong = time.time() - gio_toi_da * 3600
    ra = []
    for nhan, q in TRUY_VAN:
        try:
            root = ET.fromstring(_get(GNEWS.format(q=up.quote(q))).content)
        except Exception as e:                               # noqa: BLE001
            print(f"[gnews {nhan}] hong: {type(e).__name__}", file=sys.stderr)
            continue
        for it in root.findall(".//item"):
            td = (it.findtext("title") or "").strip()
            ts = _ts(it.findtext("pubDate") or "")
            if not td or (ts and ts < nguong):
                continue
            ra.append({"goc": nhan, "tieu_de": td, "toa_soan": toa_soan(td),
                       "link": it.findtext("link") or "", "ts": ts,
                       "ngay": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
                       if ts else "?"})
    return ra


def quet_bao(gio_toi_da: int) -> list:
    nguong = time.time() - gio_toi_da * 3600
    ra = []
    ns = {"a": "http://www.w3.org/2005/Atom"}
    for ten, url in RSS_BAO:
        try:
            root = ET.fromstring(_get(url).content)
        except Exception as e:                               # noqa: BLE001
            print(f"[rss {ten}] hong: {type(e).__name__}", file=sys.stderr)
            continue
        for it in (root.findall(".//item") or root.findall(".//a:entry", ns)):
            td = (it.findtext("title") or (it.find("a:title", ns).text
                  if it.find("a:title", ns) is not None else "") or "").strip()
            ngay_txt = (it.findtext("pubDate") or it.findtext("published")
                        or (it.find("a:published", ns).text
                            if it.find("a:published", ns) is not None else "") or "")
            ts = _ts(ngay_txt)
            if not td or (ts and ts < nguong):
                continue
            link = it.findtext("link") or ""
            if not link and it.find("a:link", ns) is not None:
                link = it.find("a:link", ns).get("href") or ""
            ra.append({"goc": "báo công nghệ", "tieu_de": td, "toa_soan": ten,
                       "link": link, "ts": ts,
                       "ngay": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d")
                       if ts else "?"})
    return ra


# Tu qua pho bien, khong giup phan biet su kien
TU_RONG = {"the", "a", "an", "of", "in", "on", "to", "for", "and", "or", "with",
           "as", "at", "by", "from", "its", "it", "is", "are", "be", "new", "ai",
           "says", "said", "after", "over", "into", "amid", "this", "that"}


def _tu_khoa(tieu_de: str) -> set:
    return {w for w in chuan_hoa(tieu_de).split() if w not in TU_RONG and len(w) > 2}


def gom_trung(tin: list, nguong=0.6) -> list:
    """Mot su kien nhieu bao dua -> giu ban som nhat, dem so bao de biet do nong.

    So khop nguyen van KHONG du: cac bao dien dat khac nhau ve cung mot viec.
    Da gap that — Reuters viet "Nvidia invests in data center developer Cloverleaf
    Infrastructure", TechCrunch viet "Nvidia partners with data center developer
    Cloverleaf", so nguyen van thi thanh hai tin. Nen gom theo DO TRUNG TU KHOA:
    hai tieu de dung chung >= 60% tu dac trung (bo tu rong) thi coi la mot.
    """
    nhom = []
    for t in sorted(tin, key=lambda x: x["ts"] or 0):      # som nhat truoc
        tu = _tu_khoa(t["tieu_de"])
        if not tu:
            continue
        vao = None
        for n in nhom:
            chung = tu & n["_tu"]
            if chung and len(chung) / min(len(tu), len(n["_tu"])) >= nguong:
                vao = n
                break
        if vao is None:
            t = dict(t)
            t["so_bao"] = 1
            t["cac_bao"] = [t["toa_soan"]] if t["toa_soan"] else []
            t["_tu"] = tu
            nhom.append(t)
        else:
            vao["so_bao"] += 1
            if t["toa_soan"] and t["toa_soan"] not in vao["cac_bao"]:
                vao["cac_bao"].append(t["toa_soan"])
    for n in nhom:
        n.pop("_tu", None)
    return nhom


def cham(t: dict) -> int:
    """Diem co hoc 0-50, phan con lai de Vera cham.

    30d do moi + 20d do lan (bao nhieu toa soan dua, co bao lon khong)."""
    tuoi_h = (time.time() - t["ts"]) / 3600 if t["ts"] else 999
    moi = 30 if tuoi_h <= 24 else (0 if tuoi_h >= 168 else
                                   int(round(30 * (168 - tuoi_h) / 144)))
    lan = min(12, (t.get("so_bao", 1) - 1) * 4)
    if any(b.lower() in " ".join(t.get("cac_bao", [])).lower() for b in BAO_LON):
        lan += 8
    return moi + min(lan, 20)


def da_thay() -> set:
    if STATE.exists():
        return set(json.loads(STATE.read_text(encoding="utf-8")).get("khoa", []))
    return set()


def ghi_moc(khoa: set):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    # Giu 2000 khoa gan nhat — du de chong trung ma khong phinh vo han
    STATE.write_text(json.dumps(
        {"cap_nhat": datetime.now(timezone.utc).isoformat(),
         "khoa": sorted(khoa)[-2000:]}, ensure_ascii=False, indent=2),
        encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="Quet tin kinh doanh/dau tu quanh AI")
    ap.add_argument("--gio", type=int, default=72, help="Chi lay tin trong N gio (mac dinh 72)")
    ap.add_argument("--top", type=int, default=15, help="So tin dua ra (mac dinh 15)")
    ap.add_argument("--top-watch", type=int, default=10,
                    help="Toi da bao nhieu tin WATCHLIST bi rot khoi top van "
                         "duoc them vao cho Vera nhin (mac dinh 10)")
    ap.add_argument("--lan-dau", action="store_true", help="Chi ghi moc, khong bao")
    ap.add_argument("--out", help="Ghi JSON ra tep")
    ap.add_argument("--state", help="Duong dan file seen khac (de TEST khong dung "
                    "business_seen.json that). Mac dinh dung file that.")
    a = ap.parse_args()

    # Cho phep tro seen sang file khac khi test. Su co 26/08: chay --lan-dau khi
    # test lam ghi de business_seen that, danh dau nham tin chua bao la da thay.
    global STATE
    if a.state:
        STATE = Path(a.state)

    tin = gom_trung(quet_gnews(a.gio) + quet_bao(a.gio))
    cu = da_thay()
    khoa_moi = {chuan_hoa(t["tieu_de"]) for t in tin}

    if a.lan_dau:
        ghi_moc(khoa_moi)
        print(f"Da ghi moc {len(khoa_moi)} tin. Lan sau chi bao cai moi.")
        return

    moi = [t for t in tin if chuan_hoa(t["tieu_de"]) not in cu]
    for t in moi:
        t["diem_co_hoc"] = cham(t)
        t["hang_watch"] = ten_watchlist(t["tieu_de"])
    moi.sort(key=lambda t: -t["diem_co_hoc"])

    # CHON CHO VERA: top theo diem, CONG tin watchlist bi rot, DA DANG THEO HANG.
    #
    # Diem co hoc xep theo "nhieu bao dua", nen tin ve top brand ma RSS chi tra
    # vai dong (Xiaomi Cube, Apple M6) bi cham thap va cat mat. Nguyen tac: tin ve
    # ten trong watchlist KHONG bi cat truoc khi Vera nhin.
    #
    # Cuu theo HANG chu khong theo diem: neu chi lay top diem thi OpenAI mot minh
    # an het suat cuu (5/10 lan do thay), Xiaomi lai rot. Moi hang lay tin tot
    # nhat cua no truoc, xong vong hai moi lay them. Nho vay "tat ca top brand
    # deu duoc theo sat" chu khong phai "brand nao nhieu tin thi lan at".
    top = moi[:a.top]
    # Gom tin watchlist bi rot theo HANG. Trong moi hang, UU TIEN tin ra mat
    # (chip/model/san pham) roi moi toi diem — tin tac dong nganh phai noi len
    # tren tin lat vat cung hang.
    def _uu_tien(t):
        return (0 if la_ra_mat(t["tieu_de"]) else 1, -t["diem_co_hoc"])
    theo_hang = {}
    for t in moi[a.top:]:
        if t["hang_watch"]:
            theo_hang.setdefault(t["hang_watch"], []).append(t)
    for h in theo_hang:
        theo_hang[h].sort(key=_uu_tien)
    # Vong tron qua tung hang; hang xep theo do "dang chu y" cua tin dau bang no,
    # de neu cham cap thi hang co tin ra mat / diem cao duoc cuu truoc.
    hang_xep = sorted(theo_hang, key=lambda h: _uu_tien(theo_hang[h][0]))
    them = []
    while len(them) < a.top_watch and any(theo_hang.values()):
        for h in hang_xep:
            if theo_hang[h] and len(them) < a.top_watch:
                them.append(theo_hang[h].pop(0))
    chon = top + them
    for t in chon:                 # co booleen ro rang cho Vera doc
        t["watchlist"] = bool(t["hang_watch"])

    ket = {"quet_luc": datetime.now(timezone.utc).isoformat(),
           "tong_quet": len(tin),
           "tin_watchlist_them": len(them), "tin_moi": chon}
    if a.out:
        Path(a.out).write_text(json.dumps(ket, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        print(a.out)
    else:
        print(f"=== TIN MOI ({len(moi)}/{len(tin)} sau khi gom trung va bo da bao) ===\n")
        for t in moi:
            bao = ", ".join(t.get("cac_bao", [])[:3]) or t["toa_soan"]
            print(f"  [{t['diem_co_hoc']:>2d}d] {t['ngay']}  ({t['goc']})")
            print(f"        {t['tieu_de'][:100]}")
            print(f"        {t['so_bao']} báo: {bao[:70]}")
    ghi_moc(cu | khoa_moi)


if __name__ == "__main__":
    main()
