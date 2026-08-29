#!/usr/bin/env python3
"""Tim ANH TOT NHAT cho mot tin — tat dinh, khong LLM.

Vi sao phai lam lai: truoc day pipeline chi nhin DUNG MOT link ma Finn nhat duoc.
Link do thuong la trang tai lieu hoac repo, va og:image cua no la mot the thuong
hieu chung chung — "deepseek-social-card.jpeg" cho MOI bai cua DeepSeek. Ket qua
la anh bai nao cung giong bai nao, hoac khong co anh that de dung.

Vi du that: tin "DeepSeek-v4-flash-vision-exp" co link
api-docs.deepseek.com/guides/vision/ -> og:image la the thuong hieu. Trong khi
bang benchmark that (2025x1652) nam o bai dua tin cua officechai.com.

Nen cach lam moi: coi mot TIN la mot su kien, khong phai mot URL.
  1. Lay anh tu chinh link goc (og:image + anh trong bai)
  2. Tim cac bao KHAC dua cung tin nay qua Google News, lay anh cua ho
  3. Loc bo the thuong hieu / logo / avatar, do kich thuoc that
  4. Xep hang: uu tien anh LON, ti le hop ly, va ten/alt goi y bieu do — bang
     benchmark va bieu do so sanh la thu doc gia muon thay, khong phai logo

Dung:
    venv/bin/python anh_bai.py --tieu-de "..." --link "..."
    venv/bin/python anh_bai.py --tieu-de "..." --link "..." --tai /tmp/anh.png
"""
import argparse
import concurrent.futures as cf
import io
import json
import re
import sys
import urllib.parse as up
import xml.etree.ElementTree as ET
from pathlib import Path

import httpx
from PIL import Image

UA = "Mozilla/5.0 (compatible; donniechu-scout/1.0)"
HDR = {"User-Agent": UA, "Accept-Encoding": "gzip, deflate"}
GNEWS = "https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"

# Anh khong dai dien noi dung — the thuong hieu, logo, avatar...
RAC = re.compile(
    r"(logo|favicon|avatar|sprite|placeholder|1x1|pixel|spacer|"
    r"social[-_]?card|og[-_]?default|default[-_]?og|share[-_]?image|"
    r"card[-_]?default|banner[-_]?site|gravatar|author)", re.I)

# Ten tep / alt goi y day la bieu do, bang so — thu doc gia muon xem
QUY = re.compile(
    r"(benchmark|chart|graph|table|figure|fig[-_]?\d|result|score|compar|"
    r"eval|plot|diagram|screenshot|demo|arch)", re.I)

# Voi tin ve MODEL, bang so moi la noi dung chinh — anh bia dep khong noi duoc gi
QUY_MODEL = re.compile(
    r"(swe[-_ ]?bench|benchmark|eval|score|leaderboard|compar|chart|graph|"
    r"table|result|pass@|accuracy|mmlu|gpqa|aime|humaneval|arena)", re.I)

# Dau hieu tin ve model — de biet khi nao phai uu tien bang so
LA_TIN_MODEL = re.compile(
    r"\b(model|llm|gpt|claude|gemini|llama|qwen|deepseek|kimi|mistral|grok|"
    r"opus|sonnet|haiku|flash|pro|nemotron|glm|minimax|benchmark|multimodal|"
    r"vision|reasoning|open[-_ ]?weight)\b", re.I)

DAI_TOI_DA = 6          # so bai dua tin lay them
ANH_MOI_TRANG = 6       # so anh lay toi da moi trang
DIEN_TICH_TOI_THIEU = 120_000     # ~350x350; nho hon thi vo khi phong len the

# Kich thuoc CHINH XAC ma cac model sinh anh hay xuat ra. Anh chup man hinh hay
# bang so that gan nhu khong bao gio roi dung vao mot trong nhung con so nay —
# chung bi cat xen nen kich thuoc le. Cac trang tong hop tin hay chen anh minh
# hoa AI sinh: chong xu, qua cau mang, bo nao phat sang. Nhin thi ra ve co thong
# tin nhung khong mang mot so lieu that nao — te hon la khong co anh, vi doc gia
# tuong day la du lieu. Da gap that: hai anh 1344x768 tu mot trang tong hop, mot
# cai ve chong xu "0.01", mot cai ve qua cau ket noi.
CO_AI_SINH = {
    (1024, 1024), (1152, 896), (896, 1152), (1216, 832), (832, 1216),
    (1344, 768), (768, 1344), (1536, 640), (640, 1536), (1024, 576),
    (576, 1024), (1280, 720), (1024, 768), (1408, 704), (704, 1408),
}


def _tai(url: str, timeout=15):
    return httpx.get(url, headers=HDR, timeout=timeout, follow_redirects=True)


def anh_trong_trang(url: str) -> list:
    """Tra ve [(url_anh, alt, la_og)] — ca og:image lan anh trong than bai."""
    try:
        r = _tai(url, 20)
        if r.status_code != 200 or "html" not in r.headers.get("content-type", ""):
            return []
        html = r.text[:400_000]
    except Exception:                                        # noqa: BLE001
        return []
    ra, thay = [], set()

    def them(src, alt, og):
        if not src:
            return
        src = src.strip()
        if src.startswith("//"):
            src = "https:" + src
        if not src.startswith("http") or src in thay:
            return
        thay.add(src)
        ra.append((src, alt or "", og))

    for prop in ("og:image:secure_url", "og:image", "twitter:image"):
        for pat in (r"""<meta[^>]+(?:property|name)=["']{p}["'][^>]*content=["']([^"']+)["']""",
                    r"""<meta[^>]+content=["']([^"']+)["'][^>]*(?:property|name)=["']{p}["']"""):
            m = re.search(pat.replace("{p}", re.escape(prop)), html, re.I)
            if m:
                them(m.group(1), "", True)
                break

    for m in re.finditer(r"<img[^>]+>", html, re.I):
        the = m.group(0)
        src = re.search(r"""\ssrc=["']([^"']+)["']""", the, re.I)
        alt = re.search(r"""\salt=["']([^"']*)["']""", the, re.I)
        them(src.group(1) if src else "", alt.group(1) if alt else "", False)
        if len(ra) > ANH_MOI_TRANG * 2:
            break
    return ra[: ANH_MOI_TRANG * 2]


def _tu_dac_trung(t: str) -> set:
    bo = {"the", "a", "an", "of", "in", "on", "to", "for", "and", "or", "with",
          "new", "ai", "model", "is", "its", "as", "at", "by", "from"}
    return {w for w in re.sub(r"[^\w\s]", " ", t.lower()).split()
            if w not in bo and len(w) > 2}


def bao_khac(tieu_de: str, so=DAI_TOI_DA) -> list:
    """Bai bao KHAC dua cung tin nay — noi thuong co bieu do va bang so that.

    Google News KHONG cho URL bai. `<link>` cua no la duong chuyen huong
    news.google.com/rss/articles/CBMi... chay bang JS, theo redirect ra trang
    trung gian 592KB khong co link that; chuoi CBMi cung khong phai base64 cua
    URL. Da thu ca DuckDuckGo html/lite — tra 202, chan bot.

    Nhung Google News CO cho ten mien toa soan o <source url>. Nen di duong vong:
    lay ten mien -> doc RSS cua chinh toa soan do -> tim bai theo tieu de. RSS
    toa soan chi giu 10-40 bai gan nhat, nhung tin cua ta luon duoi 72h nen vua du.
    """
    try:
        r = _tai(GNEWS.format(q=up.quote(tieu_de)), 25)
        its = ET.fromstring(r.content).findall(".//item")
    except Exception:                                        # noqa: BLE001
        return []
    mien = []
    for it in its[:so * 2]:
        src = it.find("source")
        u = (src.get("url") if src is not None else "") or ""
        td = it.findtext("title") or ""
        if u and (u, td) not in mien:
            mien.append((u.rstrip("/"), td))

    goc = _tu_dac_trung(tieu_de)

    def _tim_trong_feed(cap):
        m, td_gg = cap
        for duong in ("/feed/", "/rss", "/feed", "/rss.xml", "/index.xml"):
            try:
                rr = _tai(m + duong, 15)
                if rr.status_code != 200 or b"<item" not in rr.content[:400_000]:
                    continue
                for i in ET.fromstring(rr.content).findall(".//item"):
                    t = i.findtext("title") or ""
                    chung = goc & _tu_dac_trung(t)
                    if chung and len(chung) / max(len(goc), 1) >= 0.5:
                        return (i.findtext("link") or "", t)
                return None
            except Exception:                                # noqa: BLE001
                continue
        return None

    ra = []
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for kq in ex.map(_tim_trong_feed, mien[:so * 2]):
            if kq and kq[0]:
                ra.append(kq)
            if len(ra) >= so:
                break
    return ra


def _do_hoa(im) -> str:
    """Doan anh la DO HOA (logo/wordmark/the thuong hieu) thay vi ANH CHUP THAT.

    Tra ve LY DO (chuoi) neu nghi la do hoa, "" neu la anh that. Dua tren ba dau
    hieu ma anh chup gan nhu KHONG BAO GIO co: vung trong suot, qua it mau, hoac
    mot mau nen chiem phan lon khung. Nguong dat CHAT de khoi loai nham anh that."""
    try:
        # 1) Trong suot: anh chup khong co alpha; logo/wordmark PNG thi co.
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            a = im.convert("RGBA").getchannel("A")
            h = a.histogram()
            trong = sum(h[:32]) / (sum(h) or 1)          # alpha thap ~ trong suot
            if trong > 0.06:
                return f"co ~{int(trong*100)}% vung trong suot (logo/do hoa)"
        # 2) Dem mau + ti le mau nen troi tren thumbnail 64x64.
        nho = im.convert("RGB").resize((64, 64))
        mau = nho.getcolors(4096) or []
        if mau:
            mau.sort(reverse=True)
            so_mau = len(mau)
            troi = mau[0][0] / 4096.0
            if so_mau <= 32:
                return f"chi {so_mau} mau (logo/wordmark)"
            if troi >= 0.68 and so_mau <= 260:
                return f"mot mau nen chiem {int(troi * 100)}% (the thuong hieu)"
    except Exception:                                        # noqa: BLE001
        pass
    return ""


def do_anh(url: str) -> tuple:
    """(rong, cao, byte, do_hoa) — tai anh, doc kich thuoc VA doan co phai DO HOA
    (logo/wordmark) khong. `do_hoa` la ly_do neu nghi la do hoa, "" neu anh that.

    Tai nhieu hon truoc (toi 4MB) de giai ma noi dung ma phan tich; anh > 4MB gan
    chac la anh chup that nen khoi phan tich."""
    try:
        with httpx.stream("GET", url, headers=HDR, timeout=15,
                          follow_redirects=True) as r:
            if r.status_code != 200:
                return (0, 0, 0, "")
            buf = b""
            for chunk in r.iter_bytes(65536):
                buf += chunk
                if len(buf) > 4_000_000:
                    break
            try:
                im = Image.open(io.BytesIO(buf))
                im.load()
                return (im.size[0], im.size[1], len(buf), _do_hoa(im))
            except Exception:                                # noqa: BLE001
                # Tai thieu / cat giua chung: chi doc duoc header kich thuoc,
                # khong phan tich noi dung (anh lon bi cat gan chac la anh that).
                try:
                    im = Image.open(io.BytesIO(buf))
                    return (im.size[0], im.size[1], len(buf), "")
                except Exception:                            # noqa: BLE001
                    return (0, 0, 0, "")
    except Exception:                                        # noqa: BLE001
        pass
    return (0, 0, 0, "")


def cham(url: str, alt: str, la_og: bool, rong: int, cao: int,
         do_hoa: str = "", tin_model: bool = False) -> tuple:
    """(diem, ly_do). Diem cang cao cang dang dung.

    Hai uu tien Ong Chu chot:
      1. Anh RO NET nhat — do phan giai la thuoc do truc tiep, nen cho no trong
         so lon va khong chan tran som.
      2. Tin ve MODEL thi bang so / SWE-bench la noi dung chinh. Mot anh bia dep
         khong noi duoc model manh yeu ra sao; bang benchmark thi noi duoc.
    """
    if rong == 0 or cao == 0:
        return (-1, "khong doc duoc kich thuoc")
    dt = rong * cao
    if dt < DIEN_TICH_TOI_THIEU:
        return (-1, f"qua nho {rong}x{cao}")
    ti = max(rong, cao) / min(rong, cao)
    if ti > 4:
        return (-1, f"ti le qua lech {rong}x{cao}")
    if RAC.search(url) or RAC.search(alt):
        return (-1, "the thuong hieu / logo")
    # Loai logo/wordmark phat hien qua NOI DUNG anh — TRU khi anh co dau hieu la
    # bang so / bieu do (thu pipeline MUON): bang benchmark cung it mau, nen
    # trang troi, de bi nham la do hoa. Tin vao goi y chart de khoi loai nham.
    la_chart = QUY.search(url) or QUY.search(alt) or QUY_MODEL.search(url) or QUY_MODEL.search(alt)
    if do_hoa and not la_chart:
        return (-1, do_hoa)
    if (rong, cao) in CO_AI_SINH:
        return (-1, f"{rong}x{cao} — cỡ chuẩn của model sinh ảnh, gần chắc là minh hoạ AI")

    d, ly = 0, []
    # Do net: 1MP duoc ~50d, 2MP ~70d, tran 90d. Canh nho duoi 600px bi phat
    # vi phong len khung 1200 se vo.
    d += min(90, int((dt / 1_000_000) ** 0.6 * 50))
    ly.append(f"{rong}x{cao}")
    canh_nho = min(rong, cao)
    if canh_nho < 600:
        d -= 20
        ly.append(f"cạnh ngắn chỉ {canh_nho}px")
    elif canh_nho >= 900:
        d += 12
        ly.append("nét")

    if tin_model:
        if QUY_MODEL.search(url) or QUY_MODEL.search(alt):
            d += 70
            ly.append("BẢNG SỐ / benchmark — tin model ưu tiên")
        else:
            d -= 15
            ly.append("không mang số liệu")
    elif QUY.search(url) or QUY.search(alt):
        d += 35
        ly.append("có vẻ là biểu đồ/bảng số")

    if 1.0 <= ti <= 2.2:
        d += 10
        ly.append("tỉ lệ đẹp")
    if la_og:
        d += 5
        ly.append("og:image")
    return (d, ", ".join(ly))


def tim(tieu_de: str, link: str, sau_rong=True, tin_model=None, tu_nguon=None) -> list:
    if tin_model is None:
        tin_model = bool(LA_TIN_MODEL.search(tieu_de))
    # Uu tien bo nguon Finn da research. Chi tu di tim khi khong co tep do —
    # tim nguon la viec cua Finn, khong phai viec cua nguoi dung anh.
    if tu_nguon and Path(tu_nguon).exists():
        j = json.loads(Path(tu_nguon).read_text(encoding="utf-8"))
        trang = [(t["url"], "gốc" if t.get("loai") == "gốc" else "báo khác")
                 for t in j.get("trang", []) if t.get("url")]
        print(f"[anh_bai] dung {len(trang)} nguon Finn da research", file=sys.stderr)
    else:
        trang = [(link, "goc")]
        if sau_rong:
            trang += [(u, "bao khac") for u, _ in bao_khac(tieu_de) if u]

    ung_vien = []
    with cf.ThreadPoolExecutor(max_workers=6) as ex:
        for (u, nguon), ds in zip(trang, ex.map(lambda t: anh_trong_trang(t[0]), trang)):
            for src, alt, og in ds:
                ung_vien.append({"anh": src, "alt": alt, "og": og,
                                 "tu": nguon, "trang": u})
    # Cung mot anh thuong duoc phuc vu o nhieu co: image-46.png (2025x1652) va
    # image-46-1024x835.png?resize=640,522. Gom theo ten goc roi GIU BAN GOC —
    # ban co hau to kich co luon la ban da thu nho, chon no la tu bo do net.
    theo_goc = {}
    for c in ung_vien:
        k = re.sub(r"[-_]\d{2,4}x\d{2,4}|\?.*$", "", c["anh"])
        cu = theo_goc.get(k)
        if cu is None:
            theo_goc[k] = c
            continue
        def _da_thu_nho(u):
            return bool(re.search(r"[-_]\d{2,4}x\d{2,4}|resize=|\bw=\d+", u))
        if _da_thu_nho(cu["anh"]) and not _da_thu_nho(c["anh"]):
            theo_goc[k] = c
    loc = list(theo_goc.values())

    with cf.ThreadPoolExecutor(max_workers=8) as ex:
        for c, kt in zip(loc, ex.map(lambda x: do_anh(x["anh"]), loc)):
            c["rong"], c["cao"], c["byte"], c["do_hoa"] = kt
            c["diem"], c["ly_do"] = cham(c["anh"], c["alt"], c["og"],
                                         kt[0], kt[1], do_hoa=kt[3],
                                         tin_model=tin_model)
    tot = [c for c in loc if c["diem"] > 0]
    tot.sort(key=lambda c: -c["diem"])
    return tot


def main():
    ap = argparse.ArgumentParser(description="Tim anh tot nhat cho mot tin")
    ap.add_argument("--tieu-de", required=True)
    ap.add_argument("--link", required=True)
    ap.add_argument("--chi-link-goc", action="store_true",
                    help="Chi soi link goc, khong tim bao khac (nhanh hon)")
    ap.add_argument("--tai", help="Tai anh tot nhat ve duong dan nay")
    ap.add_argument("--tu-nguon", metavar="PATH",
                    help="Tep nguon do Finn research san (nguon_bai.py). Dung "
                         "bo nguon nay thay vi tu di tim lai.")
    ap.add_argument("--tin-model", action="store_true",
                    help="Ep coi day la tin ve model (uu tien manh bang so/SWE-bench)")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    kq = tim(a.tieu_de, a.link, sau_rong=not a.chi_link_goc,
             tin_model=True if a.tin_model else None, tu_nguon=a.tu_nguon)

    if a.json:
        print(json.dumps(kq[:10], ensure_ascii=False, indent=2))
    else:
        if not kq:
            print("Khong tim duoc anh nao dung duoc.", file=sys.stderr)
        for c in kq[:8]:
            print(f"  [{c['diem']:>3d}d] {c['ly_do']:<44s} ({c['tu']})")
            print(f"         {c['anh'][:110]}")
    if a.tai and kq:
        r = _tai(kq[0]["anh"], 40)
        Path(a.tai).write_bytes(r.content)
        print(f"da tai -> {a.tai} ({len(r.content):,} byte)")
    return 0 if kq else 1


if __name__ == "__main__":
    sys.exit(main())
