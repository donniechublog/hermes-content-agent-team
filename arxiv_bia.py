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
    venv/bin/python arxiv_bia.py --link https://arxiv.org/abs/2504.09762 \
        --out drafts/xxx.png
    venv/bin/python arxiv_bia.py --link ... --out ... --json   # in metadata

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

# Kho dien thoai chuan, dong bo voi card.py kieu tran.
RONG = 1200
TI_LE = 5 / 4                       # cao / rong -> 4:5
CAO = round(RONG * TI_LE)

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")


def la_arxiv(link: str) -> str | None:
    """Tra ve URL PDF neu link la arxiv, nguoc lai None."""
    m = re.search(r"arxiv\.org/(?:abs|pdf)/([0-9]{4}\.[0-9]{4,5})(v\d+)?", link)
    if not m:
        return None
    return f"https://arxiv.org/pdf/{m.group(1)}"


def tai_pdf(url: str, timeout=40) -> bytes | None:
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


def chup_bia(pdf_bytes: bytes) -> Image.Image | None:
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
    trang = doc[0]

    # Render ca trang o be ngang dien thoai.
    thu_phong = RONG / trang.rect.width
    pix = trang.get_pixmap(matrix=pymupdf.Matrix(thu_phong, thu_phong))
    anh = Image.frombytes("RGB", (pix.width, pix.height), pix.samples)

    if anh.height >= CAO:
        anh = anh.crop((0, 0, RONG, CAO))
    else:
        # Trang thap hon kho (rat hiem): dat sat tren, duoi de nen trang giay.
        khung = Image.new("RGB", (RONG, CAO), (255, 255, 255))
        khung.paste(anh, (0, 0))
        anh = khung
    return _toi_nua_duoi(anh)


# Mau tan cung cua lop toi. Khop nen ca hai thuong hieu (navy donniechublog va
# den dcgr deu rat toi), nen nuong san mau nay vao thi lop card ve tiep len tren
# lien mach, khong lo mot duong noi.
TOI = (10, 12, 16)
# Vung headline luon nam o 40% duoi (card.TRAN_TEXTBOX). Nen lop toi phai gan
# nhu DAC han o do de chu bai bien mat, chu khong toi dan nhe. Trong: bat dau
# toi tu 0.40, len gan dac o 0.60, roi giu dac toi day.
BAT_DAU_TOI = 0.40
DAC_TU = 0.60             # tu day tro xuong coi nhu vung chu, toi han
DAC = 244                 # do dac toi da (chua toi 255 de con thay chut giay)


def _toi_nua_duoi(anh: Image.Image) -> Image.Image:
    """Nuong san lop toi vao nua duoi trang bia.

    Trang paper day chu den tren nen trang. Man toi cua card mot minh khong du
    de dan chu do xuong duoi vung headline, nen chu bai va chu tieu de tranh
    nhau. Toi san nua duoi ngay trong tam bia thi: tren van sang ro (ten cong
    trinh, tac gia), duoi thanh mot vung sach han cho headline. Lam o day thay
    vi trong card vi chi rieng anh tai lieu day chu moi can, anh chup thi khong.
    """
    from PIL import Image as _I
    man = _I.new("L", (1, CAO))
    for y in range(CAO):
        r = y / CAO
        if r <= BAT_DAU_TOI:
            a = 0
        elif r >= DAC_TU:
            a = DAC
        else:
            t = (r - BAT_DAU_TOI) / (DAC_TU - BAT_DAU_TOI)
            a = int(DAC * t ** 0.85)
        man.putpixel((0, y), a)
    lop = _I.new("RGB", (RONG, CAO), TOI)
    return _I.composite(lop, anh, man.resize((RONG, CAO)))


def main():
    ap = argparse.ArgumentParser(description="Chup trang bia paper arxiv")
    ap.add_argument("--link", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    pdf_url = la_arxiv(a.link)
    if not pdf_url:
        print("Khong phai link arxiv nhan ra duoc.", file=sys.stderr)
        return 1
    pdf = tai_pdf(pdf_url)
    if not pdf:
        print(f"Khong tai duoc PDF: {pdf_url}", file=sys.stderr)
        return 1
    bia = chup_bia(pdf)
    if bia is None:
        print("Khong dung duoc trang bia tu PDF.", file=sys.stderr)
        return 1
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    bia.save(out, "PNG", optimize=True)
    if a.json:
        print(json.dumps({"out": str(out), "pdf": pdf_url,
                          "rong": bia.width, "cao": bia.height},
                         ensure_ascii=False))
    else:
        print(f"da chup bia -> {out} ({bia.width}x{bia.height})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
