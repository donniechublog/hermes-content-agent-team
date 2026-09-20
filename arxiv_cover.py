#!/usr/bin/env python3
"""Chup trang bia paper cho cac tin khong co anh (arxiv, OpenReview, PDF hoc thuat).

Vi sao can: Ethan va Ethan co mot nguyen tac cung — khong tim duoc anh THAT thi
dung lai, khong tu ve minh hoa. Nhung mot bai arxiv thi "anh that" cua no chinh
la trang dau paper: ten cong trinh va nhom tac gia, in ra tren nen trang. Do la
anh that, khong phai hinh bia dat, nen dung nguyen tac van giu.

Ket qua nhin nhu mot anh chup man hinh dien thoai mo file PDF: trang dau vua be
ngang, tren la tieu de va tac gia, than bai chay tiep xuong. Nua duoi duoc nuong
san mot lop toi de lop card kieu tran de headline tieng Viet len ma khong bi chu
bai (den tren nen trang) chen vao.

Lay CA TRANG DAU chu khong cat rieng khoi tieu de: header gon (it tac gia) thi
cat rieng se thua ra mot mang trang lon, con dung ca trang thi khung luon day.

Dung:
    venv/bin/python arxiv_cover.py --link https://arxiv.org/abs/2504.09762 \
        --out drafts/xxx.png
    venv/bin/python arxiv_cover.py --link ... --out ... --json   # in metadata

Thoat 0 neu dung duoc trang bia, 1 neu khong (khong phai PDF, tai loi, trang rong).
"""
import argparse
import json
import re
import sys
from pathlib import Path

import httpx
import pymupdf
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parent))
import env_load                                              # noqa: E402

# Kho dien thoai chuan, dong bo voi card.py kieu tran.
EMPTY = 1200
RATIO = 5 / 4                       # cao / rong -> 4:5
HEIGHT = round(EMPTY * RATIO)

UA = env_load.UA_BROWSER        # mot ban duy nhat, xem env_load (A5)


def is_arxiv(link: str) -> str | None:
    """Tra ve URL PDF neu link la arxiv, nguoc lai None."""
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})(v\d+)?", link)
    if not m:
        return None
    return f"https://arxiv.org/pdf/{m.group(1)}"


def download_pdf(url: str, timeout=40) -> bytes | None:
    try:
        r = httpx.get(url, follow_redirects=True, timeout=timeout,
                      headers={"user-agent": UA})
    except Exception:                                        # noqa: BLE001
        return None
    if r.status_code != 200:
        return None
    if "pdf" not in r.headers.get("content-type", "") and not r.content[:5] == b"%PDF-":
        return None
    return r.content


def capture_cover(pdf_bytes: bytes) -> Image.Image | None:
    """Chup TRANG DAU paper, cat phan tren dung kho dien thoai 4:5.

    Truoc day cat rieng khoi tieu de + tac gia roi dat len nen trang: header gon
    (it tac gia) thi thua ra mot mang trang lon o duoi. Nay dung ca trang dau,
    hien full be ngang roi cat phan tren cho vua 4:5 — dung nhu anh chup man hinh
    dien thoai mo mot file PDF: tieu de va tac gia o tren, than bai chay tiep
    xuong, khong con khoang trang dat them.

    Trang paper cao hon kho 4:5 nen luon co du cho: khong bao gio phai chen trang.
    """
    try:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
    except Exception:                                        # noqa: BLE001
        return None
    if doc.page_count == 0:
        return None
    page = doc[0]

    # Render ca trang o be ngang dien thoai.
    thu_phong = EMPTY / page.rect.width
    pix = page.get_pixmap(matrix=pymupdf.Matrix(thu_phong, thu_phong))
    anh = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    if anh.height >= HEIGHT:
        anh = anh.crop((0, 0, EMPTY, HEIGHT))
    else:
        # Trang thap hon kho (rat hiem): dat sat tren, duoi de nen trang giay.
        khung = Image.new("RGB", (EMPTY, HEIGHT), (255, 255, 255))
        khung.paste(anh, (0, 0))
        anh = khung
    return _dark_half_below(anh)


# Mau tan cung cua lop toi. Khop nen ca hai thuong hieu (navy donniechublog va
# den dcgr deu rat toi), nen nuong san mau nay vao thi lop card ve tiep len tren
# lien mach, khong lo mot duong noi.
DARK = (10, 12, 16)
# Vung headline luon nam o 40% duoi (card.CEILING_TEXTBOX). Nen lop toi phai gan
# nhu DAC han o do de chu bai bien mat, chu khong toi dan nhe. Trong: bat dau
# toi tu 0.40, len gan dac o 0.60, roi giu dac toi day.
START_DARK = 0.40
SOLID_FROM = 0.60             # tu day tro xuong coi nhu vung chu, toi han
SOLID = 244                 # do dac toi da (chua toi 255 de con thay chut giay)


def _dark_half_below(anh: Image.Image) -> Image.Image:
    """Nuong san lop toi vao nua duoi trang bia.

    Trang paper day chu den tren nen trang. Man toi cua card mot minh khong du
    de dan chu do xuong duoi vung headline, nen chu bai va chu tieu de tranh
    nhau. Toi san nua duoi ngay trong tam bia thi: tren van sang ro (ten cong
    trinh, tac gia), duoi thanh mot vung sach han cho headline. Lam o day thay
    vi trong card vi chi rieng anh tai lieu day chu moi can, anh chup thi khong.
    """
    from PIL import Image as _I
    man = _I.new("L", (1, HEIGHT))
    for y in range(HEIGHT):
        r = y / HEIGHT
        if r <= START_DARK:
            a = 0
        elif r >= SOLID_FROM:
            a = SOLID
        else:
            t = (r - START_DARK) / (SOLID_FROM - START_DARK)
            a = int(SOLID * t ** 0.85)
        man.putpixel((0, y), a)
    lop = _I.new("RGB", (EMPTY, HEIGHT), DARK)
    return _I.composite(lop, anh, man.resize((EMPTY, HEIGHT)))


def main():
    ap = argparse.ArgumentParser(description="Chup trang bia paper arxiv")
    ap.add_argument("--link", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    pdf_url = is_arxiv(a.link)
    if not pdf_url:
        print("Khong phai link arxiv nhan ra duoc.", file=sys.stderr)
        return 1
    pdf = download_pdf(pdf_url)
    if not pdf:
        print(f"Khong tai duoc PDF: {pdf_url}", file=sys.stderr)
        return 1
    bia = capture_cover(pdf)
    if bia is None:
        print("Khong dung duoc trang bia tu PDF.", file=sys.stderr)
        return 1
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Dong dau XUAT XU: anh nay ra dung 1200x1500 (4:5 chan) ma khong qua
    # crop_ratio.py — carousel.py chan anh 4:5/1:1 "chan" khong co dau vet vi do
    # la dau hieu cat tay ne cong (Ong Chu bat loi 04/09/2026). Dau nay cho cong
    # biet chinh cong cu cua doi dung ra anh, khong phai cat lui.
    import image_provenance
    _meta = image_provenance.stamp_provenance("arxiv_cover")
    bia.save(out, "PNG", optimize=True, pnginfo=_meta)
    if a.json:
        print(json.dumps({"out": str(out), "pdf": pdf_url,
                          "w": bia.width, "h": bia.height},
                         ensure_ascii=False))
    else:
        print(f"da chup bia -> {out} ({bia.width}x{bia.height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
