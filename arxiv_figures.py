#!/usr/bin/env python3
"""Boc HINH THAT trong paper (arxiv / PDF): Figure 1, Figure 2... cua chinh bai.

Vi sao can (Ong Chu 08/09/2026): "ngay dau paper co image ma Kite khong dung de
lam hero". Dung — paper nao cung mo dau bang mot hinh ket qua tong, va do la ANH
THAT dat nhat cua tin: chinh nhom tac gia ve, chinh so cua ho. Nhung engine anh
khong bao gio thay no:

  - link arxiv trong kho tin la `arxiv.org/abs/<id>` — trang abs chi co tom tat,
    khong mot figure nao. Browser mo trang do ve tay khong.
  - ban HTML (`arxiv.org/html/<id>`) co hinh, nhung LaTeXML xuat figure ra
    `<object type="image/svg+xml">`, ma `document.images` cua browser_pass khong
    thay `<object>`; con cong chup `figure` thi doi >= 600x300 nen mot hinh rong
    ma thap (Figure 1 cua ACE: 521x160pt) bi loai.
  - `arxiv_cover.py` chi chup TRANG BIA (ten cong trinh + tac gia) va chi chay khi
    khong con ung vien nao. Trang bia khong phai bieu do ket qua.

Nen boc thang tu PDF: dinh vi cac khoi chu "Figure N:", lay vung do hoa nam ngay
tren chu thich do, render vung do o do phan giai cao. Vector trong PDF nen phong
to bao nhieu cung net — khac han anh chup man hinh.

CHI HINH, KHONG BANG (§BANG). Bang trong paper khong co moc dang tin de chan
vung cat: chu thich khi o tren khi o duoi tuy noi dang bai (BERT dat duoi), va
tung DONG cua bang trong nhu mot dong than bai — khong the phan biet "het bang"
voi "bat dau doan van". Thu roi: bang cua BERT cat ra thanh nguyen mot trang chu
hai cot. Cat sai mot cai bang la dang len slide mot bang KHAC voi bang trong
bai, nen tha khong co. Hinh thi co moc chac: chu thich o duoi, do hoa o tren.

Dung:
    venv/bin/python arxiv_figures.py --link https://arxiv.org/abs/2510.04618 --ra /tmp/h
    venv/bin/python arxiv_figures.py --link ... --ra /tmp/h --json

Thoat 0 neu boc duoc it nhat mot hinh, 1 neu khong.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# ---- kho ra -----------------------------------------------------------------
# Vector trong PDF phong to khong vo, nen cu render du to. EMPTY_ITEM vuot 2160 =
# be ngang slide cua render_edu (1080) nhan DPR 2 luc chup, nen hinh khong bao
# gio phai phong len. SHORT_SIDE_ITEM vuot image_rules.SHORT_SIDE_MIN (1000) de khoi
# dinh canh bao "canh ngan, phong len se mem" luc nop — va bo xa hai nguong duoi
# no: image_rules.SHORT_SIDE_DOWNLOAD (500, duoi do image_prepare khong buon tai) va
# render_edu.FIG_EMPTY_MIN (800).
EMPTY_ITEM = 2200
SHORT_SIDE_ITEM = 1000
ZOOM_MAX = 12.0
ZOOM_MIN = 1.5
# Bang ba dong rong het cot (Attention: 406x52pt = 7.8:1) dan len slide 4:5 chi
# con mot vet ngang — dung duoc thi cung khong ai doc noi. Bo o day, dung de
# buoc tai cua image_prepare lang le vut (canh ngan < 500).
RATIO_MAX = 5.0

COUNT_PAGE = 8                     # chi quet phan dau bai; phu luc toan prompt/bang phu
MAX = 4
COUNT = 5.0                        # via pt chua quanh vung cat
# Vung nghi la CHAY DAU TRANG / SO TRANG: khoi chu nam tron trong 8% tren hay
# duoi trang. Hinh nam ngay dau trang thi dai cat cham toi duong ke duoi chay
# dau va keo theo nua dong "Published as a conference paper at ICLR 2026" vao
# anh (do that: Figure 4 cua ACE). Chan bang chinh khoi chu do chu KHONG bang
# mot le co dinh: co paper (DeepSeek-R1) khong co chay dau, hinh bat dau ngay
# tu ~6% trang — le cung se cat cut ten bieu do.
ODD_RUN_MARK = 0.08
ODD_SAME = 0.015                  # via toi thieu, ke ca khi khong co chay dau
SLIT_TEXT = 10.0                   # chu ke sat ngoai khung ve van tinh la cua hinh

# Chu thich hinh trong paper: "Figure 1:", "Fig. 2.", "Table 3:", va kieu
# "Figure 1 | ..." cua DeepSeek/Google. BAT BUOC co dau ngan cach: khong co no
# thi "Figure 1(a) depicts..." va "Table 3 summarizes..." — hai cau THAN BAI mo
# dau bang tham chieu hinh (do that trong DeepSeek-R1) — cung thanh chu thich.
ANNOTATION = re.compile(r"^\s*(figure|fig\.|table)\s*(\d+)\s*[:.|–—]\s*(\S.*)",
                       re.I | re.S)


def is_annotation(text: str) -> tuple | None:
    """("figure"|"table", so, chu) neu khoi chu la mot chu thich hinh, nguoc lai None."""
    m = ANNOTATION.match((text or "").strip())
    if not m:
        return None
    loai = "table" if m.group(1).lower().startswith("t") else "figure"
    return loai, int(m.group(2)), " ".join(m.group(3).split())


def is_body_article(text: str, rong: float, rong_cot: float) -> bool:
    """Khoi chu nay la THAN BAI (moc chan vung hinh) hay chu ben trong hinh?

    Doi CA HAI: trai gan het be ngang cot VA co chu that. Dong chu trong hinh
    (ten bieu do, nhan truc, nhan cot) bao gio cung hep hon cot vi no can giua
    mot panel — ke ca khi dai ("DeepSeek-R1-Zero average length per response
    during training": 59 ky tu, rong 213pt tren cot 450pt). Neu chi do DAI thi
    ten bieu do do thanh "than bai", moc bi keo xuong va anh cat mat ten hinh.
    """
    t = (text or "").strip()
    return rong >= 0.5 * max(rong_cot, 1) and len(t) >= 20


def _hand(a: tuple, b: tuple) -> tuple | None:
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[2], b[2]), min(a[3], b[3])
    return (x0, y0, x1, y1) if x1 >= x0 and y1 >= y0 else None


def _merge(a: tuple | None, b: tuple) -> tuple:
    if a is None:
        return b
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _anti_landscape(a: tuple, b: tuple) -> float:
    """Phan be ngang chung cua hai hop, tinh theo hop hep hon (0..1)."""
    chung = min(a[2], b[2]) - max(a[0], b[0])
    hep = min(a[2] - a[0], b[2] - b[0])
    return chung / hep if hep > 0 and chung > 0 else 0.0


def annotation_enough_line(cap_khoi: tuple, khoi: list) -> tuple:
    """Hop chu thich gom CA cac dong noi tiep cua no.

    `get_text("blocks")` cua MuPDF gom ca doan lam mot khoi voi paper nay
    (ACE) nhung cat TUNG DONG voi paper khac (DeepSeek-R1) — luc do hop chu
    thich chi cao mot dong, va anh cat ra cut mat cac dong sau. Gom them dong
    ke duoi khi no gan nhu dinh vao (khe < nua chieu cao MOT DONG) va thang cot.

    Khe phai do theo chieu cao mot DONG chu khong phai ca khoi: chu thich 5
    dong cua BERT cao 60pt, lay nua do (30pt) lam khe thi doan than bai ngay
    duoi lot vao, roi chuoi tiep xuong het trang — anh ra la ca trang chu.
    """
    cap = tuple(cap_khoi[:4])
    so_dong = max(1, (cap_khoi[4] or "").strip().count("\n") + 1)
    cao_dong = max(cap[3] - cap[1], 8.0) / so_dong
    hop = cap
    for _ in range(6):
        tiep = None
        for k in khoi:
            if k[1] < hop[3] - 1 or k[1] - hop[3] > 0.5 * cao_dong:
                continue
            if _anti_landscape(cap, k) < 0.6 or is_annotation(k[4]) is not None:
                continue
            if tiep is None or k[1] < tiep[1]:
                tiep = k
        if tiep is None:
            return hop
        hop = _merge(hop, (tiep[0], tiep[1], tiep[2], tiep[3]))
    return hop


def _drop_run_mark(cap: tuple, khoi: list, page: tuple) -> tuple:
    """(gioi han tren, gioi han duoi) cua vung noi dung — bo chay dau trang / so trang.

    Chay dau ("Published as a conference paper at ICLR 2026") va so trang la
    khoi chu nam tron trong le tren/duoi. Duong ke mo cua chay dau thi khong
    phai chu, khong tu nhan ra duoc — nhung no luon nam ngay duoi khoi chu do,
    nen chan tu day chu chay dau la du.
    """
    cao = page[3] - page[1]
    tren, duoi = page[1] + ODD_SAME * cao, page[3] - ODD_SAME * cao
    for k in khoi:
        if is_annotation(k[4]) is not None:
            continue
        if k[3] <= page[1] + ODD_RUN_MARK * cao:
            tren = max(tren, k[3] + 3)
        if k[1] >= page[3] - ODD_RUN_MARK * cao:
            duoi = min(duoi, k[1] - 3)
    return tren, duoi


def _graphic_within_long(cap: tuple, ve: list, dai: tuple, page: tuple) -> tuple | None:
    """Hop cua phan do hoa nam trong `dai` va cung cot voi chu thich."""
    dt_trang = max((page[2] - page[0]) * (page[3] - page[1]), 1.0)
    hop = None
    for r in ve:
        if (r[2] - r[0]) * (r[3] - r[1]) >= 0.9 * dt_trang:
            continue                              # nen trang, khong phai hinh
        g = _hand(r, dai)
        if g is None or _anti_landscape(cap, g) < 0.15:
            continue
        hop = _merge(hop, g)
    return hop


def region_figure(cap_khoi: tuple, khoi: list, ve: list, page: tuple) -> tuple | None:
    """Vung can cat cho MOT chu thich hinh — ham THUAN (chi hop toa do, khong pymupdf).

    cap_khoi  khoi chu thich (x0,y0,x1,y1,text);
    khoi      [(x0,y0,x1,y1,text)] moi khoi chu trong trang;
    ve        [(x0,y0,x1,y1)] hop cua net ve + anh nhung trong trang;
    trang     hop trang giay.

    Tra hop da chua ca hinh lan chu thich, hoac None khi khong thay do hoa nao.

    Cach lam: chan mot DAI giua chu thich va khoi than bai gan nhat phia tren,
    roi lay hop cua phan do hoa nam trong dai do. Khong dung nguyen hop cua net
    ve: PDF hay ve cot bieu do bang duong keo dai roi cat bang clip, nen hop cua
    net ve co the tran ra ngoai trang (do that tren ACE: cot cao toi y=964 tren
    trang 792). Cat theo dai thi cai tran ra do khong keo vung cat di dau.
    """
    cap = annotation_enough_line(cap_khoi, khoi)
    rong_cot = max(cap[2] - cap[0], 1.0)
    gh_tren = _drop_run_mark(cap, khoi, page)[0]
    # Cac moc chan co the: day cua tung khoi "than bai" phia tren chu thich, gan
    # nhat truoc. Thu lan luot chu khong chot ngay moc dau: so do hoa trong hinh
    # thuong co dong chu trai rong bang cot (hang o token cua BERT hinh 1) va
    # cong `is_body_article` cham nham no la than bai — chot ngay moc do thi anh chi
    # con mot vet duoi cung cua hinh. Hinh nao con cham tran dai thi noi dai len.
    mocs = sorted({k[3] for k in khoi
                   if (is_annotation(k[4]) is not None
                       or is_body_article(k[4], k[2] - k[0], rong_cot))
                   and _anti_landscape(cap, k) >= 0.2 and k[3] <= cap[1] + 1
                   and k[3] > gh_tren}, reverse=True) + [gh_tren]
    hop = dai = None
    for moc in mocs:
        if cap[1] - moc < 8:
            continue
        dai = (page[0], moc, page[2], cap[1])
        hop = _graphic_within_long(cap, ve, dai, page)
        if hop is not None and hop[1] > dai[1] + 2:
            break                                 # hinh khong cham tran dai: du roi
    if hop is None or dai is None:
        return None
    # Chu ben trong hinh (ten bieu do, nhan truc, nhan cot, chu so tren cot) hay
    # tho ra ngoai khung ve — keo hop ra cho du. Chong len khung thi lay het;
    # chi ke SAT ben ngoai (ten bieu do dat tren khung 1-2pt) thi phai khong
    # phai than bai moi lay, khong thi doan van ngay tren hinh cung bi keo vao.
    for _ in range(3):
        truoc = hop
        for k in khoi:
            kb = _hand((k[0], k[1], k[2], k[3]), dai)
            if kb is None:
                continue
            if _hand(kb, hop) is None:
                gan = (_anti_landscape(kb, hop) > 0.05
                       and max(kb[1] - hop[3], hop[1] - kb[3]) <= SLIT_TEXT)
                if not gan or is_body_article(k[4], k[2] - k[0], rong_cot):
                    continue
            hop = _merge(hop, kb)
        if hop == truoc:
            break
    hop = _merge(hop, cap)
    return (max(page[0], hop[0] - COUNT), max(page[1], hop[1] - COUNT),
            min(page[2], hop[2] + COUNT), min(page[3], hop[3] + COUNT))


# ---- phan cham vao PDF -------------------------------------------------------
def pdf_of_link(link: str) -> str | None:
    """URL PDF cua mot link paper: arxiv (abs/pdf/html) hoac link .pdf thang."""
    m = re.search(r"arxiv\.org/(?:abs|pdf|html)/([0-9]{4}\.[0-9]{4,5})", link or "")
    if m:
        return f"https://arxiv.org/pdf/{m.group(1)}"
    return link if re.search(r"\.pdf($|\?)", link or "", re.I) else None


def _graphic_page(page) -> list:
    """Hop cua net ve + anh nhung trong mot trang PDF."""
    ra = []
    try:
        for d in page.get_drawings():
            r = d["rect"]
            ra.append((r.x0, r.y0, r.x1, r.y1))
    except Exception:                                        # noqa: BLE001
        pass
    try:
        for i in page.get_image_info():
            b = i["bbox"]
            ra.append((b[0], b[1], b[2], b[3]))
    except Exception:                                        # noqa: BLE001
        pass
    return ra


def _no_page_full(anh) -> bool:
    """Vung cat co gi de nhin khong — chan hinh trang tron / gan trong."""
    from PIL import ImageStat
    L = anh.convert("L")
    h = L.histogram()
    n = max(sum(h), 1)
    if sum(h[236:]) / n > 0.985:
        return False
    return ImageStat.Stat(L).stddev[0] > 4


def extract(pdf_bytes: bytes, ra_dir, so_trang=COUNT_PAGE, toi_da=MAX) -> list:
    """Boc hinh cua paper ra PNG trong `ra_dir`. Tra [{file_path, kind, number, caption, page_number, w, h}]."""
    import pymupdf
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception:                                        # noqa: BLE001
        return []
    ra_dir = Path(ra_dir)
    ra_dir.mkdir(parents=True, exist_ok=True)
    ra, da_co = [], set()
    for so_t in range(min(so_trang, doc.page_count)):
        page = doc[so_t]
        tr = (page.rect.x0, page.rect.y0, page.rect.x1, page.rect.y1)
        try:
            khoi = [(b[0], b[1], b[2], b[3], b[4]) for b in page.get_text("blocks")
                    if b[6] == 0 and (b[4] or "").strip()]
        except Exception as e:                               # noqa: BLE001
            print(f"[arxiv_hinh] trang {so_t + 1}: {type(e).__name__} — bo qua", file=sys.stderr)
            continue
        ve = _graphic_page(page)
        for k in khoi:
            ct = is_annotation(k[4])
            if ct is None:
                continue
            loai, so, chu = ct
            if loai != "figure":
                continue                          # xem chu thich §BANG o dau tep
            if (loai, so) in da_co:
                continue                          # "Figure 1" nhac lai o phu luc
            hop = region_figure(k, khoi, ve, tr)
            if hop is None:
                continue
            w, h = hop[2] - hop[0], hop[3] - hop[1]
            if w < 120 or h < 40 or h > 0.95 * (tr[3] - tr[1]):
                continue
            if max(w / h, h / w) > RATIO_MAX:
                print(f"[arxiv_hinh] bo {loai} {so}: ti le {w / h:.1f}:1, dan len slide "
                      "chi con mot vet", file=sys.stderr)
                continue
            zoom = max(ZOOM_MIN, min(ZOOM_MAX, max(EMPTY_ITEM / w, SHORT_SIDE_ITEM / h)))
            try:
                pix = page.get_pixmap(matrix=pymupdf.Matrix(zoom, zoom),
                                       clip=pymupdf.Rect(*hop))
            except Exception as e:                           # noqa: BLE001
                print(f"[arxiv_hinh] {loai} {so}: render hong ({type(e).__name__})", file=sys.stderr)
                continue
            from PIL import Image
            anh = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)
            # Hinh co nen trang rong hon noi dung (savefig co padding) ra le dac hai ben;
            # cong check_side_bars (LOW-336) cua ca ba vai chan anh do. Do 22/09/2026 tren
            # 23 paper that: 19/60 hinh bi chan khi khong got, 0/60 khi got.
            import image_rules_common
            anh = image_rules_common.trim_flat_sides_until_clean(anh)
            if not _no_page_full(anh):
                continue
            import image_provenance
            tep = ra_dir / f"paper_{loai}_{so}.png"
            anh.save(tep, "PNG", pnginfo=image_provenance.stamp_provenance(
                "arxiv_figure", **{image_provenance.FIGURE_KEY: f"{loai} {so}",
                                 image_provenance.PDF_PAGE_KEY: so_t + 1}))
            da_co.add((loai, so))
            ra.append({"file_path": str(tep), "kind": loai, "number": so, "caption": chu[:300],
                       "page_number": so_t + 1, "w": anh.width, "h": anh.height})
            if len(ra) >= toi_da:
                return ra
    return ra


def download_pdf(url: str, timeout=40) -> bytes | None:
    import arxiv_cover
    return arxiv_cover.download_pdf(url, timeout)


def candidate(link: str, ra_dir) -> list:
    """Hinh cua paper duoi dang UNG VIEN cua image_prepare (`file_path` + `score` + `alt`).

    Diem cao hon moi ung vien khac (og:image ~90, chup figure 50, browser 45):
    hinh cua CHINH bai la bang chung goc, khong phai anh minh hoa muon o dau.
    Hinh dau tien (thuong la Figure 1 — bieu do ket qua tong) cao nhat: no la
    tam dung lam hero.

    KHONG BAO GIO NEM: ham nay chay tren MOI tin arxiv/PDF, ngay giua
    `prepare_article()`. Nem la mat luon manifest.json cua ca bai — dung loai su co da
    xay ra voi `ranking.find_and_capture` (05/09/2026) va rat de xay ra lai o day:
    `hermes update` dung lai venv chung tung lam mat `pymupdf` khoi no, ma
    `boc()` va `arxiv_cover` deu import pymupdf.
    """
    pdf_url = pdf_of_link(link)
    if not pdf_url:
        return []
    try:
        data = download_pdf(pdf_url)
        if not data:
            print(f"[arxiv_hinh] khong tai duoc PDF: {pdf_url}", file=sys.stderr)
            return []
        hinh = extract(data, ra_dir)
    except Exception as e:                                   # noqa: BLE001
        print(f"[arxiv_hinh] HONG: {type(e).__name__}: {e} — di tiep khong co hinh paper",
              file=sys.stderr)
        return []
    print(f"[arxiv_hinh] {len(hinh)} hinh trong paper: "
          + (", ".join(f"{h['kind']} {h['number']} ({h['w']}x{h['h']})" for h in hinh) or "khong co"),
          file=sys.stderr)
    ra = []
    for i, h in enumerate(hinh):
        ten = ("Figure" if h["kind"] == "figure" else "Table") + f" {h['number']}"
        ra.append({"image_url": h["file_path"], "file_path": h["file_path"], "alt": f"{ten}: {h['caption']}"[:200],
                   "og": False, "source": "arxiv_figure", "page_url": link, "html_tag": "figure",
                   "w": h["w"], "h": h["h"], "score": 95 if i == 0 else 80,
                   "score_reason": f"{ten} trong chinh paper", "paper_figure": ten})
    return ra


def main() -> int:
    ap = argparse.ArgumentParser(description="Boc hinh that trong paper arxiv/PDF")
    ap.add_argument("--link", required=True)
    ap.add_argument("--ra", required=True, help="thu muc ghi PNG")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    pdf_url = pdf_of_link(a.link)
    if not pdf_url:
        print("Khong phai link arxiv / PDF nhan ra duoc.", file=sys.stderr)
        return 1
    data = download_pdf(pdf_url)
    if not data:
        print(f"Khong tai duoc PDF: {pdf_url}", file=sys.stderr)
        return 1
    hinh = extract(data, a.ra)
    if not hinh:
        print("Khong boc duoc hinh nao trong paper.", file=sys.stderr)
        return 1
    if a.json:
        print(json.dumps(hinh, ensure_ascii=False))
    else:
        for h in hinh:
            print(f"{h['kind']} {h['number']} (trang {h['page_number']}) {h['w']}x{h['h']} -> {h['file_path']}")
            print(f"    {h['caption'][:100]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
