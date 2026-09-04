#!/usr/bin/env python3
"""gin_chuan_bi.py — BRIEF cho Gin (dọn chữ trên ảnh nền): OCR định vị vùng chữ,
đánh số, đo màu chữ, vẽ preview — KHÔNG xoá gì (LaMa chạy ở gin_nop.py).

Trước (đo 28/08–04/09): mỗi ảnh Gin tốn 11–39 tool call: `df -h`, `ls`, dò
cv2/easyocr đã cài chưa, viết PIL script xem kích thước, `vision_analyze` 5–15
lần để đọc chữ trên ảnh, chạy doi_chu_anh 2 lần. Giờ: một lệnh in danh sách vùng
chữ có SỐ THỨ TỰ + text OCR + toạ độ + màu; vai chỉ quyết vùng nào là logo cần
giữ (theo text, không cần nhìn ảnh) rồi chạy gin_nop.py.

Đầu vào: message_id của ảnh Ông Chủ gửi (tệp state/<brand>/telegram_incoming/
<id>.*) hoặc đường dẫn ảnh. Workdir: state/<brand>/chuan_bi/gin_<id>/.

Dùng:
    venv/bin/python gin_chuan_bi.py 338            # theo message_id
    venv/bin/python gin_chuan_bi.py /path/anh.jpg  # theo đường dẫn
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import env_load                                              # noqa: E402

import cv2                                                   # noqa: E402
import numpy as np                                           # noqa: E402


def tim_anh(dau_vao: str) -> tuple:
    """(đường dẫn ảnh, id). id = message_id nếu đầu vào là số."""
    p = Path(dau_vao)
    if p.exists():
        return p, p.stem
    inc = env_load.state_dir() / "telegram_incoming"
    for q in sorted(inc.glob(f"{dau_vao}.*")):
        return q, dau_vao
    sys.exit(f"Không thấy ảnh {dau_vao!r} (đã tìm {inc}/{dau_vao}.*)")


def workdir(vai: str, id_: str) -> Path:
    wd = env_load.state_dir() / "chuan_bi" / f"{vai}_{id_}"
    wd.mkdir(parents=True, exist_ok=True)
    return wd


def mau_chu(img_bgr, box) -> list:
    """Màu chữ thật (RGB) = trung vị pixel phía CHỮ sau khi tách Otsu trong box.
    Phía chữ là phía có ÍT pixel hơn (nền chiếm nhiều hơn) — không dùng độ sáng
    trung vị cả vùng vì vùng nhỏ hay lật (BodyMist 28/08 ra màu nền trắng)."""
    pts = np.array(box, dtype=np.int32)
    h, w = img_bgr.shape[:2]
    x0, y0 = max(0, pts[:, 0].min()), max(0, pts[:, 1].min())
    x1, y1 = min(w, pts[:, 0].max()), min(h, pts[:, 1].max())
    crop = img_bgr[y0:y1, x0:x1]
    if crop.size == 0:
        return [255, 255, 255]
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    if gray.min() == gray.max():
        return [int(v) for v in crop.reshape(-1, 3).mean(axis=0)[::-1]]
    nguong, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    sang = gray > nguong
    chu = sang if sang.sum() < (~sang).sum() else ~sang
    px = crop[chu]
    if px.size == 0:
        px = crop.reshape(-1, 3)
    med = np.median(px, axis=0)
    return [int(med[2]), int(med[1]), int(med[0])]


def ocr_vung(anh: Path) -> tuple:
    """(img_bgr, [vùng]) — vùng: {stt, box, x, y, w, h, text, conf, color_rgb},
    sắp trên→dưới, trái→phải."""
    import doi_chu_anh
    img = cv2.imread(str(anh))
    if img is None:
        sys.exit(f"Không đọc được ảnh: {anh}")
    res = doi_chu_anh.tim_vung_chu(img, verbose=False)
    vung = []
    for box, text, conf in res:
        pts = np.array(box, dtype=np.int32)
        x, y = int(pts[:, 0].min()), int(pts[:, 1].min())
        w, h = int(pts[:, 0].max() - x), int(pts[:, 1].max() - y)
        vung.append({"box": [[int(a), int(b)] for a, b in box], "x": x, "y": y, "w": w, "h": h,
                     "text": text, "conf": round(float(conf), 2), "color_rgb": mau_chu(img, box)})
    vung.sort(key=lambda v: (round(v["y"] / max(1, img.shape[0]) * 40), v["x"]))
    for i, v in enumerate(vung, 1):
        v["stt"] = i
    return img, vung


def ve_preview(img_bgr, vung: list, out: Path) -> None:
    vis = img_bgr.copy()
    for v in vung:
        cv2.rectangle(vis, (v["x"], v["y"]), (v["x"] + v["w"], v["y"] + v["h"]), (0, 0, 255), 3)
        cv2.putText(vis, str(v["stt"]), (v["x"], max(28, v["y"] - 6)), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, (0, 0, 255), 3)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), vis)


def viet_brief(id_: str, anh: Path, img, vung: list, wd: Path) -> str:
    h, w = img.shape[:2]
    L = [f"# GIN — OCR XONG ảnh {id_}: {w}x{h}, {len(vung)} vùng chữ",
         f"Ảnh gốc: {anh}", f"Preview vùng đánh số (mở MỘT lần nếu cần): {wd / 'vung_preview.png'}", "",
         "## Vùng chữ (stt | text OCR | x,y,w,h | conf | màu chữ RGB)"]
    if not vung:
        L.append("(OCR không thấy chữ nào — báo lại Ông Chủ, không có gì để dọn.)")
    for v in vung:
        L.append(f"- {v['stt']:2d} | {v['text'][:60]!r} | {v['x']},{v['y']},{v['w']},{v['h']} | "
                 f"{v['conf']:.2f} | {v['color_rgb']}")
    L += ["", f"## Spec (TUỲ CHỌN) — chỉ khi có vùng cần GIỮ (logo/tên thương hiệu gốc) hoặc xoá thêm: {wd}/spec.json",
          json.dumps({"giu": ["<stt vùng là logo/brand, KHÔNG xoá — vd 3>"],
                      "xoa_them": [["<x>", "<y>", "<w>", "<h>"]],
                      "ghi_chu": "<một câu cho Ông Chủ: logo gì đang giữ, cần quyết thay bằng gì>"},
                     ensure_ascii=False, indent=1),
          "Mặc định (không có spec): xoá TẤT CẢ vùng chữ. Logo/hình khối thương hiệu là quyết định thiết kế, "
          "không tự xoá rồi bỏ trống: giữ (giu) và ghi_chu để báo lại. Không cần đọc đúng nội dung OCR, chỉ "
          "cần vị trí.",
          "", "## Rồi chạy đúng MỘT lệnh:",
          f"cd {ROOT} && venv/bin/python gin_nop.py {id_}",
          "Script xoá chữ bằng LaMa (~30s lần đầu nạp model, ~5s/ảnh sau đó), ghi nen_sach.png + mask_debug.png "
          "+ vung.json (vị trí + màu chữ cho Itachi), gửi cả hai ảnh trả lời đúng tin nhắn. KHÔNG df/ls/pip, "
          "KHÔNG viết PIL script, KHÔNG vision_analyze từng ảnh, KHÔNG chạy doi_chu_anh.py/gui_telegram.py tay."]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Brief dọn chữ cho Gin")
    ap.add_argument("anh", help="message_id hoặc đường dẫn ảnh")
    ap.add_argument("--im", action="store_true")
    a = ap.parse_args()
    anh, id_ = tim_anh(a.anh)
    wd = workdir("gin", id_)
    img, vung = ocr_vung(anh)
    ve_preview(img, vung, wd / "vung_preview.png")
    (wd / "vung_ocr.json").write_text(json.dumps({"anh": str(anh), "id": id_, "w": img.shape[1],
                                                  "h": img.shape[0], "vung": vung},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    brief = viet_brief(id_, anh, img, vung, wd)
    (wd / "brief.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
