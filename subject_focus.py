"""subject_focus.py — tam chu the cua anh, de cat 4:5 dat chu the o NUA TREN khung (LOW-422).

Ong Chu 30/09/2026: bo dai nen duoi chu thi chu the phai nam tren de duoi con cho cho chu
(*"day logo cao len cho phan duoi nhieu khong gian"*). Cat giua (crop_ratio mac dinh) bo qua viec do.

  - `find(img)`: (x0, y0, x1, y1) 0..1 cua chu the — mat nguoi (YuNet) neu co, khong thi vung nang
    luong canh (Sobel) tap trung nhat; None neu anh phang, khong co gi noi bat.
  - `crop_center(img, ratio)`: (cx, cy) cho `crop_ratio.crop` sao cho chu the nam o TREN khung.
"""
import os
import tempfile

TARGET_Y = 0.34          # tam chu the dat o 34% chieu cao khung cat (vung chu bat dau ~62%)
MAX_SIDE = 320           # thu nho de do nang luong canh


def _faces(img):
    """Hop mat nguoi 0..1 cua anh; [] neu khong co / khong do duoc (thieu cv2, model)."""
    try:
        import image_rules_dre
        fd, path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            img.convert("RGB").save(path)
            return image_rules_dre.face_boxes(path) or []
        finally:
            os.unlink(path)
    except Exception:                                    # noqa: BLE001 — khong co mat thi dung canh
        return []


def _edge_box(img):
    """Hop (0..1) chua 90% nang luong canh — chu the khong co mat (logo, san pham, chart)."""
    import numpy as np
    from PIL import Image
    g = img.convert("L")
    ty = MAX_SIDE / max(g.size)
    if ty < 1:
        g = g.resize((max(1, round(g.width * ty)), max(1, round(g.height * ty))), Image.Resampling.BILINEAR)
    a = np.asarray(g, dtype=np.float64)
    if a.shape[0] < 3 or a.shape[1] < 3:
        return None
    gx = np.abs(np.diff(a, axis=1))[:-1, :]
    gy = np.abs(np.diff(a, axis=0))[:, :-1]
    e = gx + gy
    if e.sum() < 1e-6 or e.std() < 1.0:
        return None                                      # anh phang: khong co chu the de bam
    cols, rows = e.sum(axis=0), e.sum(axis=1)

    def span(v):
        c = np.cumsum(v) / v.sum()
        return float(np.searchsorted(c, 0.05)) / len(v), float(np.searchsorted(c, 0.95)) / len(v)

    x0, x1 = span(cols)
    y0, y1 = span(rows)
    return [x0, y0, x1, y1]


def find(img):
    faces = _faces(img)
    if faces:
        return [min(f[0] for f in faces), min(f[1] for f in faces),
                max(f[2] for f in faces), max(f[3] for f in faces)]
    return _edge_box(img)


def crop_center(img, ratio):
    """(cx, cy) 0..1 cho crop_ratio.crop: cat ngang bam tam chu the, cat doc dat tam chu the o
    TARGET_Y khung. Anh khong co chu the ro -> (0.5, 0.5) nhu cu."""
    box = find(img)
    if not box:
        return 0.5, 0.5
    w, h = img.size
    fx, fy = (box[0] + box[2]) / 2, (box[1] + box[3]) / 2
    nh = h if w / h > ratio else w / ratio            # chieu cao khung cat (crop_ratio.crop)
    y0 = fy * h - TARGET_Y * nh                          # dinh khung cat sao cho tam chu the o TARGET_Y
    cy = (y0 + nh / 2) / h
    return fx, min(1.0, max(0.0, cy))
