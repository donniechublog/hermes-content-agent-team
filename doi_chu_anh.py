#!/usr/bin/env python3
"""Xoa chu tieng Anh tren anh nen, tra lai nen SACH cho deck.py ve chu Viet len.

Dung khi remake mot carousel co san (vd Sociyell) sang tieng Viet: anh goc co
chu tieng Anh de/dan len anh that (chu khong phai mang chu rieng biet). Ba
buoc, tat ca chay that khong mo phong:

  1. OCR (EasyOCR) DINH VI moi vung co chu — KHONG can doc dung noi dung. Chu
     tieng Viet ghi de len sau la do nguoi viet cung cap qua deck.py, khong
     phai dich tu ket qua OCR. Vi vay du OCR doc sai/loi (chu khong lo, hai
     dong dinh nhau...) van dung duoc, mien dinh dung VI TRI.
  2. Mask OM SAT net chu: nguong gan-trang (hoac gan-toi, tuy nen) NGAY TRONG
     tung vung OCR tim thay, khong phai ca hinh chu nhat bao quanh. Mask cang
     sat chu, vung LaMa phai "bia" cang nho, ket qua cang net — da do that:
     mask kieu khoi lam nen mo di ro o giua vung lon, mask om sat giam han.
  3. Inpaint bang LaMa (simple-lama-inpainting). cv2.inpaint KHONG dung duoc
     cho anh nen phuc tap (nguoi, pho, kien truc...) — de lai vet loang thay
     vi tai tao duong net that. Da so sanh truc tiep, chenh lech ro rang.

Dung:
    venv/bin/python doi_chu_anh.py --anh slide.jpg --out nen_sach.png \
        [--giu "x,y,w,h"] [--giu "x2,y2,w2,h2" ...] \
        [--xem-mask mask_debug.png]

--giu khoanh vung KHONG duoc dong den (logo, icon thuong hieu goc...) — co the
lap lai nhieu lan. Toa do tinh tren anh GOC (truoc khi resize).

Vai Gin dung script nay. Chay xong, dua nen_sach.png cho deck.py qua key
`"bg_anh"` trong JSON spec cua tung slide (khong phai co CLI) de Irene ve chu
tieng Viet len (deck.py lo phan typography, script nay khong dung toi chu Viet).
"""
import argparse
import sys
import time
from pathlib import Path

import cv2
import numpy as np
from PIL import Image

DILATE_PX = 10      # no mask them bao nhieu px de trum het vien mo/bong chu
# Duoi nguong nay (px²) thi to KIN ca hop chu thay vi tach nguong Otsu — mot
# badge ~120x40=4800 khong du mau cho Otsu tach dang tin cay (da do that: chu
# vo vun con sot net). Doan than bai nhieu dong thuong tren 30000, an toan.
DIEN_TICH_TO_KIN = 15000


def _doc_giu(args_giu):
    ra = []
    for s in args_giu or []:
        try:
            x, y, w, h = (int(v) for v in s.split(","))
        except ValueError:
            sys.exit(f"--giu sai dinh dang: {s!r} (can 'x,y,w,h')")
        ra.append((x, y, w, h))
    return ra


def _trong_giu(box, giu_list):
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    cx, cy = sum(xs) / 4, sum(ys) / 4
    return any(x <= cx <= x + w and y <= cy <= y + h for x, y, w, h in giu_list)


def tim_vung_chu(img_bgr, verbose=True):
    """OCR dinh vi moi vung co chu. Tra ve danh sach (box, text, conf) tho —
    KHONG loc, KHONG doi ten — de goi biet chinh xac OCR thay gi truoc khi
    quyet dinh xoa vung nao."""
    import easyocr
    if verbose:
        print("[1/3] OCR dinh vi vung chu (EasyOCR, CPU)...", file=sys.stderr)
    t0 = time.time()
    reader = easyocr.Reader(["en"], gpu=False, verbose=False)
    res = reader.readtext(img_bgr)
    if verbose:
        print(f"      {len(res)} vung, {time.time()-t0:.1f}s", file=sys.stderr)
        for box, text, conf in res:
            print(f"        conf={conf:.2f}  {text!r}", file=sys.stderr)
    return res


def dung_mask(img_bgr, boxes, giu_list, dilate_px=DILATE_PX, verbose=True):
    """Mask OM SAT net chu trong tung vung OCR — khong phai ca hinh chu nhat.

    Nguong sang tinh RIENG cho tung vung bang Otsu (tren chinh cac gia tri xam
    trong vung do), khong dung mot nguong co dinh cho ca anh. Da do that: mot
    nguong co dinh (185) bat dung chu TRANG DAM (tieu de) nhung bo sot chu XAM
    NHAT (doan than bai — cung mau trang nhung do sang thap hon, tuong phan
    voi nen den yeu hon) — anh xoa ra con "bong ma" chu cu chu khong sach han.
    Otsu tu tim diem chia tach ro nhat GIUA chu va nen cua rieng vung do, nen
    khong phu thuoc do sang tuyet doi cua tung kieu chu.

    Chieu (chu SANG-tren-nen-toi hay chu TOI-tren-nen-sang) van quyet dinh
    bang do sang trung vi ca vung — nen chiem dien tich lon hon chu nen trung
    vi lech ve phia nen."""
    h, w = img_bgr.shape[:2]
    mask = np.zeros((h, w), dtype=np.uint8)
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    so_xoa = 0
    for box, text, conf in boxes:
        if _trong_giu(box, giu_list):
            continue
        so_xoa += 1
        poly = np.zeros((h, w), dtype=np.uint8)
        pts = np.array(box, dtype=np.int32)
        cv2.fillPoly(poly, [pts], 255)
        vals = gray[poly > 0]
        if vals.size == 0:
            continue
        x0, y0 = max(0, pts[:, 0].min()), max(0, pts[:, 1].min())
        x1, y1 = min(w, pts[:, 0].max()), min(h, pts[:, 1].max())
        crop = gray[y0:y1, x0:x1]
        if crop.size == 0:
            continue
        if crop.size < DIEN_TICH_TO_KIN or crop.min() == crop.max():
            # Vung QUA NHO (badge, nhan nho...) de Otsu co du mau tach chu
            # khoi nen dang tin cay — da do that: chu vo vun, con sot net
            # rach. Vung nho khong co van de "noi giua mask lon" (ly do ta
            # om sat mask o cho khac), nen to KIN CA HINH thay vi tach —
            # chac chan sach, khong danh doi gi.
            mask = cv2.bitwise_or(mask, poly)
            continue
        nguong, _ = cv2.threshold(crop, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        if np.median(vals) < nguong:
            chu = ((gray > nguong) & (poly > 0)).astype(np.uint8) * 255
        else:
            chu = ((gray < nguong) & (poly > 0)).astype(np.uint8) * 255
        mask = cv2.bitwise_or(mask, chu)
    if verbose:
        print(f"[2/3] Mask om sat chu: {so_xoa} vung xoa, "
              f"{len(boxes)-so_xoa} vung giu (logo/--giu)", file=sys.stderr)
    k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (dilate_px * 2 + 1,) * 2)
    return cv2.dilate(mask, k)


_LAMA = None


def _lama():
    """Nap model LaMa mot lan, dung lai giua cac lan goi trong cung tien
    trinh (batch nhieu anh khoi nap lai moi lan ~2s)."""
    global _LAMA
    if _LAMA is not None:
        return _LAMA
    import torch
    device = torch.device("cpu")   # MPS thieu op cho big-lama tren torch 2.8
    # Checkpoint luu san tensor CUDA; ep map_location=cpu ngay luc load.
    _orig_load = torch.jit.load
    torch.jit.load = lambda f, *a, **kw: _orig_load(f, map_location=device)
    try:
        from simple_lama_inpainting import SimpleLama
        _LAMA = SimpleLama(device=device)
    finally:
        torch.jit.load = _orig_load
    return _LAMA


def inpaint(img_bgr, mask, verbose=True):
    if verbose:
        print("[3/3] LaMa inpaint (lan dau nap model se cham ~5s, "
              "moi anh sau do ~2 phut tren CPU)...", file=sys.stderr)
    t0 = time.time()
    lama = _lama()
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    out = lama(Image.fromarray(img_rgb), Image.fromarray(mask))
    if verbose:
        print(f"      xong {time.time()-t0:.1f}s", file=sys.stderr)
    return cv2.cvtColor(np.array(out), cv2.COLOR_RGB2BGR)


def xoa_chu(img_bgr, giu_list=None, xoa_them_list=None, verbose=True):
    """Ham loi tai dung duoc: anh (BGR, numpy) vao -> (nen_sach BGR, mask,
    boxes_da_xoa) ra. CLI ben duoi chi la lop mong quanh ham nay."""
    boxes = tim_vung_chu(img_bgr, verbose=verbose)
    mask = dung_mask(img_bgr, boxes, giu_list or [], verbose=verbose)
    for x, y, w, h in (xoa_them_list or []):
        mask[y:y + h, x:x + w] = 255
    if not mask.any():
        sys.exit("Khong co vung nao de xoa (het bi --giu chan, hoac OCR "
                 "khong thay chu). Kiem tra lai anh dau vao.")
    sach = inpaint(img_bgr, mask, verbose=verbose)
    da_xoa = [(b, t, c) for b, t, c in boxes if not _trong_giu(b, giu_list or [])]
    return sach, mask, da_xoa


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0],
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--anh", required=True, help="Anh nguon (jpg/png)")
    ap.add_argument("--out", required=True, help="Nen sach xuat ra (png)")
    ap.add_argument("--giu", action="append",
                    help="'x,y,w,h' vung KHONG xoa (logo...). Lap lai duoc.")
    ap.add_argument("--xoa-them", action="append",
                    help="'x,y,w,h' vung XOA THEM du OCR khong thay (chu qua "
                         "nho/mo). Lap lai duoc. Luon xem --xem-mask truoc "
                         "khi giao — OCR thinh thoang bo sot mot ky tu don le.")
    ap.add_argument("--xem-mask", help="Ghi them anh debug: mask do len nen goc")
    a = ap.parse_args()

    img_bgr = cv2.imread(a.anh)
    if img_bgr is None:
        sys.exit(f"Khong doc duoc anh: {a.anh}")
    giu_list = _doc_giu(a.giu)
    xoa_them_list = _doc_giu(a.xoa_them)

    sach, mask, da_xoa = xoa_chu(img_bgr, giu_list, xoa_them_list)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), sach)
    print(f"da xoa {len(da_xoa)} vung chu -> {out}", file=sys.stderr)

    if a.xem_mask:
        vis = img_bgr.copy()
        vis[mask > 0] = (0, 0, 255)
        vis = cv2.addWeighted(img_bgr, 0.5, vis, 0.5, 0)
        cv2.imwrite(a.xem_mask, vis)
        print(f"mask debug -> {a.xem_mask}", file=sys.stderr)


if __name__ == "__main__":
    main()
