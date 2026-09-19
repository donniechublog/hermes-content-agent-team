#!/usr/bin/env python3
"""subject_fit.py — CHU THE CHINH (main character) cua mot anh co dat vua khung 4:5 khong.

LOW-273 (Ong Chu 19/09/2026): "khong phai la tim hinh co ty le 4:5, ma la tim hinh
co main character dat vua trong 4:5". Ty le anh KHONG noi len gi: mot anh 4:5 co the
la logo nho tren nen trang (Instinct, empty 0.9), mot anh ngang van cat 4:5 duoc neu
chu the nam gon o giua.

Ham THUAN, khong biet vai nao goi, khong goi vision: nhan hop bao (vision tra qua
dong CHU_THE cua `prepare/vision.py`) va tinh. Dung chung cho moi designer — ty le
khung/vung chu la tham so cua tung vai.
"""
import re

FRAME_RATIO = 0.8                # rong/cao cua khung 4:5
TEXT_SHARE = 0.30                # phan DUOI khung danh cho chu o slide than Dre
EMPTY_SHARE_MAX = 0.60           # tam anh trong hon muc nay = chu the qua nho tren nen tron
                                 # (do that 19/09: logo Instinct 0.90, logo SoftBank 0.93)

# Ma loai chu the (English, LOW-230) — vision duoc hoi tra thang ma nay
KINDS = ("person", "product", "building", "logo", "screen", "chart", "other")

_NUM = r"-?\d*\.?\d+"


def parse_subject(txt: str) -> dict:
    """Doc 2 dong vision tra: `CHU_THE: x0,y0,x1,y1 | loai` va `TRONG: 0..1`.
    Khong doc ra thi None tung khoa (fail-open: khong co so do thi khong chan)."""
    out = {"subject_box": None, "subject_kind": None, "empty_share": None}
    m = re.search(rf"^\s*CHU_TH[EỂ]\s*:\s*({_NUM})\s*[, ]\s*({_NUM})\s*[, ]\s*({_NUM})\s*[, ]\s*({_NUM})"
                  r"\s*(?:\|\s*([A-Za-z_]+))?", txt or "", re.I | re.M)
    if m:
        x0, y0, x1, y1 = (float(m.group(i)) for i in range(1, 5))
        if -0.02 <= x0 < x1 <= 1.02 and -0.02 <= y0 < y1 <= 1.02:      # bo vai nguoi tra toa do pixel/rac
            out["subject_box"] = [max(0.0, x0), max(0.0, y0), min(1.0, x1), min(1.0, y1)]
        kind = (m.group(5) or "").lower()
        out["subject_kind"] = kind if kind in KINDS else None
    e = re.search(rf"^\s*TR[OỐ]NG\s*:\s*({_NUM})", txt or "", re.I | re.M)
    if e:
        v = float(e.group(1))
        if 0.0 <= v <= 1.0:
            out["empty_share"] = v
    return out


def crop_window(w: int, h: int, box, text_share: float = TEXT_SHARE, ratio: float = FRAME_RATIO):
    """Khung cat `ratio` (rong/cao) LON NHAT trong anh w x h, dat sao cho HOP BAO chu the
    nam TRON trong khung VA nam TREN vung chu (`text_share` phan duoi khung).

    Tra ve (x0, y0, x1, y1) pixel, hoac None neu chu the khong vua (qua rong / qua cao /
    khong the dat len tren vung chu). Chu the that su nam o giua thi ket qua om chu the;
    thieu hop bao thi None (khong biet = khong khang dinh vua)."""
    if not box or w <= 0 or h <= 0:
        return None
    if w / h >= ratio:
        ch, cw = h, round(h * ratio)
    else:
        cw, ch = w, round(w / ratio)
    sx0, sy0, sx1, sy1 = box[0] * w, box[1] * h, box[2] * w, box[3] * h
    usable = (1.0 - text_share) * ch
    if sx1 - sx0 > cw or sy1 - sy0 > usable:
        return None
    x0 = min(max(round((sx0 + sx1) / 2 - cw / 2), 0), w - cw)
    y0 = min(max(round((sy0 + sy1) / 2 - usable / 2), 0), h - ch)
    if sx0 < x0 - 1 or sx1 > x0 + cw + 1 or sy0 < y0 - 1 or sy1 > y0 + usable + 1:
        return None
    return (x0, y0, x0 + cw, y0 + ch)


def too_empty(empty_share, limit: float = EMPTY_SHARE_MAX) -> bool:
    """Tam anh phan lon la nen tron (logo/bieu tuong nho tren nen trang): khong dung duoc.
    `limit` la nguong RIENG cua tung vai (image_rules_<vai>.EMPTY_SHARE_MAX)."""
    return empty_share is not None and float(empty_share) >= limit


def head_box(faces):
    """Hop DAU NGUOI tu cac hop MAT (0..1, do bang code — YuNet): gop moi mat, noi them
    toc/tran phia tren va cam/co phia duoi. Do that 19/09: vision duoc dan "chi khoanh
    dau va mat" van khoanh ca than (Altman 0.25..0.85), nen voi anh nguoi dung mat
    do bang code, khong dung hop cua vision (luat "code truoc, LLM sau")."""
    if not faces:
        return None
    x0 = min(f[0] for f in faces); y0 = min(f[1] for f in faces)
    x1 = max(f[2] for f in faces); y1 = max(f[3] for f in faces)
    fw, fh = x1 - x0, y1 - y0
    return [max(0.0, x0 - 0.3 * fw), max(0.0, y0 - 0.5 * fh),
            min(1.0, x1 + 0.3 * fw), min(1.0, y1 + 0.4 * fh)]


def band_full_width(w: int, h: int, box, frame_w: int, frame_h: int, short_top_share: float = 0.6):
    """Chu the nam o dai doc nao cua KHUNG (0..1) khi anh dan FULL BE NGANG kieu
    carousel._body_image: cao hon khung thi cat giua doc; thap hon `short_top_share`
    khung thi dat giua vung tren do; con lai sat mep tren. -> (top, bottom) hoac None."""
    if not box or w <= 0 or h <= 0:
        return None
    nh = h * frame_w / w
    if nh > frame_h:
        y0 = -(nh - frame_h) / 2
    elif nh < frame_h * short_top_share:
        y0 = (frame_h * short_top_share - nh) / 2
    else:
        y0 = 0.0
    return ((y0 + box[1] * nh) / frame_h, (y0 + box[3] * nh) / frame_h)
