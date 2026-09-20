#!/usr/bin/env python3
"""Phan KY THUAT THUAN dung chung cho ba module luat anh (LOW-310).

Luat "moi designer mot rule anh" (LOW-182) tach cong PHAN DOAN NOI DUNG theo vai
— sua Dre khong duoc lan sang Ethan/Kite. Chinh luat do noi phan **kiem ky thuat
thuan** thi giu CHUNG. Truoc 20/09/2026 ca hai loai deu chep 3 ban.

Ong Chu chot 20/09/2026: gop DUNG BON ham khong chua phan doan noi dung:

    load_yunet            nap mo hinh nhan mat (31 dong x 3)
    measure_chart_signal  do tin hieu bieu do bang pixel (31 x 3)
    is_blank_image        do anh trong bang pixel (14 x 3)
    record_used           ghi so anh da dung (12 x 3)

KHONG gop bat ky ham `check_*` nao. Tam ham cong (`check_not_reused`,
`check_chart_integrity`, `check_chart_standalone`, `check_unnamed_face`,
`check_crop_landscape`, `check_duplicate`, `check_blank_image`,
`check_resolution`) hien GIONG HET nhau ba ban — do khong phai ly do de gop:
chung de rieng la de MAI SAU sua cho mot vai khong lan sang vai kia. Nguong cung
vay: `EMPTY_COLOR`, `EMPTY_FLAT`, `FACE_EDGE_MAX`... van song trong tung module
vai va duoc TRUYEN VAO day, khong doc nguoc.

Ba module vai van xuat du ten cu (`_load_yunet`, `measure_chart_signal`,
`is_blank_image`, `record_used`, `_YUNET_LOCK`) nen moi cho goi ben ngoai khong
doi mot dong nao, va moi test dang va `image_rules_<vai>._load_yunet` van va
dung cho.
"""
import threading
from pathlib import Path

from PIL import Image, ImageOps

# Mot detector duy nhat cho ca tien trinh, thay vi ba ban giong het nhau. Truoc
# LOW-310 moi module vai nap rieng mot ban tu CUNG mot tep .onnx.
_YUNET = None
_YUNET_TRIED = False
YUNET_LOCK = threading.Lock()


def load_yunet():
    """Nap lazy model YuNet, dung mot lan cho ca doi tien trinh.

    Khoa bang YUNET_LOCK (audit_content_team B2): `classify` gio duoc
    prepare.vision._seen_image goi tu nhieu luong cung luc qua ThreadPoolExecutor.
    Khong khoa thi luong A dat co "da thu" = True TRUOC khi gan xong detector —
    `import cv2` va doc file .onnx o giua co the nha GIL — nen luong B doc co
    thay True nhung detector con None, tra ve None nham nhu may thieu cv2/model
    du thuc ra co day du. Hau qua im lang: count_faces() bao 0 mat, cong mat nguoi
    (IMAGE_RULES §6) tu tat theo may rui thu tu luong thay vi theo may that su co
    cv2 hay khong.
    """
    global _YUNET, _YUNET_TRIED
    if _YUNET_TRIED:
        return _YUNET
    with YUNET_LOCK:
        if _YUNET_TRIED:              # luong khac vua nap xong trong luc cho khoa
            return _YUNET
        try:
            import os as _os
            _os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
            import cv2
            m = Path(__file__).resolve().parent / "assets" / \
                "face_detection_yunet_2023mar.onnx"
            if m.exists():            # thieu model -> bo qua cong, khong crash build
                _YUNET = cv2.FaceDetectorYN_create(str(m), "", (320, 320),
                                                   score_threshold=0.7)
        except Exception:
            _YUNET = None
        _YUNET_TRIED = True           # dat SAU CUNG, sau khi detector da co gia tri chot
    return _YUNET


def measure_chart_signal(img, w=480):
    """(phang, so_mau). Thuan PIL — venv tren server khong chac co numpy.

      phang  — ti le cap pixel KE NHAU theo hang gan nhu bang nhau (lech <= 2).
               Do hoa vector (chart, bang, UI) toan mang phang voi vai buoc nhay
               dung; anh chup that thi moi pixel lech nhau mot chut.
      so_mau — so mau RIENG BIET sau khi luong hoa 5 bit/kenh. Day la phep do
               tach bach nhat: chart/screenshot dung mot bang mau tay nen ra vai
               chuc mau, anh chup that ra hang nghin.

    Thu nho bang NEAREST chu KHONG phai LANCZOS: LANCZOS lam nhoe vung phang cua
    screenshot thanh gradient, tuc la xoa dung cai dau hieu can do.

    Do tren 16 the that trong drafts/ (anh that + scrim phang, tinh huong KHO
    nhat): phang 0.31..0.95, so_mau 350..4552 — khong tam nao bi goi nham la
    chart. Chart/screenshot do duoc: phang 0.89..0.99, so_mau 42..65. Nguong dat
    giua khoang trong do va phai dung CA HAI.
    """
    h = max(1, round(img.height * w / img.width))
    v = img.convert("RGB").resize((w, h), Image.Resampling.NEAREST)
    px = v.convert("L").tobytes()
    bang = tong = 0
    for y in range(h):
        r = px[y * w:(y + 1) * w]
        for i in range(w - 1):
            tong += 1
            if abs(r[i] - r[i + 1]) <= 2:
                bang += 1
    phang = bang / max(1, tong)
    mau = ImageOps.posterize(v, 5).getcolors(w * h) or []
    return phang, len(mau)


def is_blank_image(img, empty_color, empty_flat):
    """Anh co RONG khong (trang tron / mot mau phang) -> (bool, mo_ta).

    `empty_color` / `empty_flat` la NGUONG CUA VAI, truyen vao chu khong doc
    nguoc tu module vai (LOW-310): nguong la chinh sach, than do la ky thuat.

    Bo Broadcom dcgr 04/09/2026: buoc chup tra ve anh trang tron (2 mau, phang
    100%), khong cong nao bat, ra mot slide trong tron chi co chu. Tro treu:
    anh trang la thu "giong chart" NHAT theo do_chart, nen cong chart cho qua.

    Do tren 76 anh trong kho: anh rong = 2 mau; anh that it mau nhat = 40 mau
    (screenshot UI toi hai tone). Cach nhau 20 lan nen nguong 4 la an toan —
    khac han cac phep do "slide trong" da thu va bo (chung chong lan voi chart
    sach). Day la RONG thuc su, khong phai "thua".
    """
    ph, mau = measure_chart_signal(img)
    return (mau <= empty_color and ph >= empty_flat), f"{mau} mau, phang {ph:.0%}"


def record_used(duong_dan, draft_id: str, vai: str, link: str, dhash_of, md5_of) -> None:
    """Ghi mot dong vao so anh da dung.

    `dhash_of` / `md5_of` la ham CUA VAI (moi module vai co ban rieng, chua chac
    mai sau con giong nhau) — truyen vao thay vi import nguoc, de module chung
    khong bao gio phu thuoc vao module vai (LOW-310).

    So nam o MOT cho (`image_provenance._used_images_log`) va ca ba vai deu thay
    ngay — patch rieng tung ban se lech nhau, dung cai LOW-182 dinh tranh.
    """
    import json
    import time

    import image_provenance
    q = Path(duong_dan)
    try:
        with Image.open(q) as im:
            h = dhash_of(im)
    except Exception:                                        # noqa: BLE001
        return
    dong = {"dhash": h, "draft_id": draft_id, "role": vai,
            "story_key": image_provenance.story_key(link),
            "file_name": q.name, "md5": md5_of(q), "used_at": int(time.time())}
    with open(image_provenance._used_images_log(), "a", encoding="utf-8") as f:
        f.write(json.dumps(dong, ensure_ascii=False) + "\n")
