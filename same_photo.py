#!/usr/bin/env python3
"""same_photo.py — hai tep anh co phai CUNG MOT buc anh (tai tu hai nguon, cat/nen khac nhau).

LOW-284 (19/09/2026, album dcgr "Lovable mua Sutro"): anh tay cam dien thoai chay app
Lovable len ca slide 5 (A59, 9to5mac.com) lan slide 6 (A26, computerworld.com); anh
chup trang chu Lovable len slide 2 (A76) lan slide 6 (A42). `check_duplicate` chi so md5,
ma hai tep tu hai URL thi md5 khac nhau.

dHash KHONG tach duoc (LOW-265 da thu): ban cat khac cua cung anh lech 7-17 bit, anh khac
han chi cach 20-36 bit. Do 19/09 tren moi cap anh dung duoc trong tung bai cua may chu:
dem diem khop ORB con lai sau RANSAC (homography) — cap cung anh 222-957, cap khac nhau
lay ngau nhien toi da 114. Nhung hai do hoa khac nhau CHUNG LOGO (Apple "M3 Ultra" vs
"M6/M5 Ultra", logo Lovable tren hai nen) cung khop 256-277 diem. Nen buoc hai: can anh A
len anh B theo chinh homography do roi so PIXEL vung chong (tuong quan Pearson): cung anh
0.85-1.00, chung logo/khuon 0.66-0.83. CHI dung cho anh CHUP: chart/bang xep hang cung
khuon (cung paper, Arena) khop 230-360 diem va tuong quan ~0.81-0.83, khong xet o day.

Ham THUAN, khong biet vai nao goi. Thieu cv2 -> None (khong ket luan).
"""
from functools import lru_cache

SAME_PHOTO_INLIERS = 200         # diem khop ORB sau RANSAC tu muc nay moi xet tiep
SAME_PHOTO_CORR = 0.82           # tuong quan pixel sau khi can A len B tu muc nay = cung anh
MIN_OVERLAP = 0.30               # phan anh B duoc A phu sau khi can, duoi muc nay khong ket luan
MAX_EDGE = 640                   # thu nho truoc khi do (nhanh, on dinh giua cac co anh)
N_FEATURES = 1000
RATIO = 0.75                     # Lowe ratio test


@lru_cache(maxsize=256)
def _load(path: str):
    """(anh xam thu nho, toa do diem, descriptor) hoac None."""
    import cv2
    im = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if im is None:
        return None
    s = MAX_EDGE / max(im.shape)
    if s < 1:
        im = cv2.resize(im, (max(1, int(im.shape[1] * s)), max(1, int(im.shape[0] * s))),
                        interpolation=cv2.INTER_AREA)
    # `ignore[attr-defined]` o duoi: ORB_create CO THAT luc chay, chi thieu trong
    # stub cua opencv-python (do 20/09/2026, cv2 4.x) — khong phai loi cua ta.
    kp, des = cv2.ORB_create(nfeatures=N_FEATURES).detectAndCompute(im, None)  # type: ignore[attr-defined]
    if des is None or len(des) < 10:
        return None
    return im, [k.pt for k in kp], des


def compare(path_a, path_b):
    """(so diem khop sau RANSAC, tuong quan pixel sau khi can A len B) hoac None neu khong
    do duoc (thieu cv2, anh loi). Tuong quan 0.0 khi qua it diem / vung chong qua nho."""
    try:
        import cv2
        import numpy as np
    except ImportError:
        return None
    fa, fb = _load(str(path_a)), _load(str(path_b))
    if fa is None or fb is None:
        return 0, 0.0
    (ia, pa_all, da), (ib, pb_all, db) = fa, fb
    ms = [m[0] for m in cv2.BFMatcher(cv2.NORM_HAMMING).knnMatch(da, db, k=2)
          if len(m) == 2 and m[0].distance < RATIO * m[1].distance]
    if len(ms) < 8:
        return len(ms), 0.0
    pa = np.float32([pa_all[m.queryIdx] for m in ms])
    pb = np.float32([pb_all[m.trainIdx] for m in ms])
    h, mask = cv2.findHomography(pa, pb, cv2.RANSAC, 5.0)
    if h is None or mask is None:
        return 0, 0.0
    n = int(mask.sum())
    size = (ib.shape[1], ib.shape[0])
    wa = cv2.warpPerspective(ia, h, size)
    phu = cv2.warpPerspective(np.full_like(ia, 255), h, size) > 0
    if phu.mean() < MIN_OVERLAP or phu.sum() < 100:
        return n, 0.0
    x, y = wa[phu].astype(np.float32), ib[phu].astype(np.float32)
    if x.std() < 1 or y.std() < 1:
        return n, 0.0
    return n, float(np.corrcoef(x, y)[0, 1])


def is_same_photo(path_a, path_b) -> bool:
    kq = compare(path_a, path_b)
    return kq is not None and kq[0] >= SAME_PHOTO_INLIERS and kq[1] >= SAME_PHOTO_CORR
