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
    venv/bin/python swap_image_text.py --anh slide.jpg --out clean_background.png \
        [--giu "x,y,w,h"] [--giu "x2,y2,w2,h2" ...] \
        [--xem-mask mask_debug.png]

--giu khoanh vung KHONG duoc dong den (logo, icon thuong hieu goc...) — co the
lap lai nhieu lan. Toa do tinh tren anh GOC (truoc khi resize).

Vai Gin dung script nay. Chay xong, dua clean_background.png cho deck.py qua key
`"bg_anh"` trong JSON spec cua tung slide (khong phai co CLI) de Itachi ve chu
tieng Viet len (deck.py lo phan typography, script nay khong dung toi chu Viet).
"""
import argparse
import sys
import time
from pathlib import Path

import image_provenance

import cv2
import numpy as np
from PIL import Image

DILATE_PX = 10      # no mask them bao nhieu px de trum het vien mo/bong chu
# Duoi nguong nay (px²) thi to KIN ca hop chu thay vi tach nguong Otsu — mot
# badge ~120x40=4800 khong du mau cho Otsu tach dang tin cay (da do that: chu
# vo vun con sot net). Doan than bai nhieu dong thuong tren 30000, an toan.
AREA_TO_SEALED = 15000
# Tren nguong nay thi THU NHO anh truoc khi cho LaMa, roi chi ghep lai dung
# vung da xoa. Do that 07/09/2026 tren may nay (7GB RAM, CPU):
#     1024x1275  OK   9s        1536x1912  OK  16s
#     1280x1593  OK  10s        2048x2550  CHET — doi 14.7GB mot luot cap phat
# 2048x2550 la kich thuoc CHUAN cua carousel Instagram, nghia la truoc khi co
# ham nay Itachi khong lam duoc bat ky anh IG nao — chet giua chung voi mot
# traceback cua torch, khong mot dong nao noi la anh qua to.
MAX_PX_LAMA = 3_000_000


def _read_keep(args_giu):
    ra = []
    for s in args_giu or []:
        try:
            x, y, w, h = (int(v) for v in s.split(","))
        except ValueError:
            sys.exit(f"--giu sai dinh dang: {s!r} (can 'x,y,w,h')")
        ra.append((x, y, w, h))
    return ra


def _within_keep(box, giu_list):
    xs = [p[0] for p in box]
    ys = [p[1] for p in box]
    cx, cy = sum(xs) / 4, sum(ys) / 4
    return any(x <= cx <= x + w and y <= cy <= y + h for x, y, w, h in giu_list)


def find_region_text(img_bgr, verbose=True):
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


def use_mask(img_bgr, boxes, giu_list, dilate_px=DILATE_PX, verbose=True):
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
        if _within_keep(box, giu_list):
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
        if crop.size < AREA_TO_SEALED or crop.min() == crop.max():
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


def _lama_run(img_bgr, mask):
    lama = _lama()
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    out = lama(Image.fromarray(img_rgb), Image.fromarray(mask))
    return cv2.cvtColor(np.array(out), cv2.COLOR_RGB2BGR)


def inpaint(img_bgr, mask, verbose=True):
    """Xoa vung `mask` bang LaMa. Anh qua to thi dung nen o do phan giai thap
    roi GHEP LAI dung vung da xoa vao anh goc — ngoai vung do khong mot pixel
    nao bi dong den, nen anh khong mem di. Vung trong mask von la nen BIA ra,
    thap phan giai hon mot chut o do chap nhan duoc; het bo nho thi khong co
    ket qua nao het."""
    h, w = img_bgr.shape[:2]
    thu_nho = h * w > MAX_PX_LAMA
    if verbose:
        print(f"[3/3] LaMa inpaint {w}x{h}"
              + (" (thu nho de vua bo nho, ghep lai vung xoa)" if thu_nho else "")
              + " (lan dau nap model ~5s)...", file=sys.stderr)
    t0 = time.time()
    if not thu_nho:
        ra = _lama_run(img_bgr, mask)
    else:
        r = (MAX_PX_LAMA / (h * w)) ** 0.5
        nw, nh = max(1, int(w * r)), max(1, int(h * r))
        nho = cv2.resize(img_bgr, (nw, nh), interpolation=cv2.INTER_AREA)
        # Mask thu nho bang INTER_AREA roi lay MOI pixel khac 0: net chu manh
        # thu nho bang NEAREST se dut quang va LaMa bo sot net.
        m_nho = (cv2.resize(mask, (nw, nh), interpolation=cv2.INTER_AREA) > 0
                 ).astype(np.uint8) * 255
        out = cv2.resize(_lama_run(nho, m_nho), (w, h), interpolation=cv2.INTER_LANCZOS4)
        # Ghep co vuot bien: cat thang theo mask de lai duong vien ro giua pixel
        # goc va pixel phong to. Nhoe 3px, va giu nguyen alpha=1 ben trong mask.
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (7, 7))
        alpha = cv2.GaussianBlur(cv2.dilate(mask, k).astype(np.float32) / 255.0, (0, 0), 3)
        alpha = np.clip(alpha, 0.0, 1.0)
        alpha[mask > 0] = 1.0
        a = alpha[:, :, None]
        ra = (img_bgr.astype(np.float32) * (1 - a) + out.astype(np.float32) * a
              ).clip(0, 255).astype(np.uint8)
    if verbose:
        print(f"      xong {time.time()-t0:.1f}s", file=sys.stderr)
    return ra


def delete_text(img_bgr, giu_list=None, xoa_them_list=None, verbose=True):
    """Ham loi tai dung duoc: anh (BGR, numpy) vao -> (nen_sach BGR, mask,
    boxes_da_xoa) ra. CLI ben duoi chi la lop mong quanh ham nay."""
    boxes = find_region_text(img_bgr, verbose=verbose)
    mask = use_mask(img_bgr, boxes, giu_list or [], verbose=verbose)
    for x, y, w, h in (xoa_them_list or []):
        mask[y:y + h, x:x + w] = 255
    if not mask.any():
        sys.exit("Khong co vung nao de xoa (het bi --giu chan, hoac OCR "
                 "khong thay chu). Kiem tra lai anh dau vao.")
    sach = inpaint(img_bgr, mask, verbose=verbose)
    da_xoa = [(b, t, c) for b, t, c in boxes if not _within_keep(b, giu_list or [])]
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
    giu_list = _read_keep(a.giu)
    xoa_them_list = _read_keep(a.xoa_them)

    sach, mask, da_xoa = delete_text(img_bgr, giu_list, xoa_them_list)

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), sach)
    image_provenance.stamp_file(out, "doi_chu_anh")
    print(f"da xoa {len(da_xoa)} vung chu -> {out}", file=sys.stderr)

    if a.xem_mask:
        vis = img_bgr.copy()
        vis[mask > 0] = (0, 0, 255)
        vis = cv2.addWeighted(img_bgr, 0.5, vis, 0.5, 0)
        cv2.imwrite(a.xem_mask, vis)
        print(f"mask debug -> {a.xem_mask}", file=sys.stderr)


if __name__ == "__main__":
    main()
