#!/usr/bin/env python3
"""gin_prepare.py — BRIEF cho Gin (thay chữ Anh bằng chữ Việt trên THẺ QUOTE):
tải ảnh nếu đầu vào là link, OCR định vị vùng chữ, đánh số, đo màu chữ, đo NỀN
phẳng hay nền ảnh, đo cỡ và độ đậm chữ gốc, vẽ preview — KHÔNG xoá, KHÔNG vẽ gì
(việc đó ở gin_submit.py).

Việc của Gin là ca DỄ: chữ nằm trên THẺ/DẢI NỀN PHẲNG (bảng đen dưới ảnh, badge,
banner một màu). Xoá chỉ là trám lại đúng màu nền, ảnh thật phía trên không hề
bị đụng tới. Chữ đè THẲNG lên ảnh thật (mặt người, phố, đồ vật) là việc của
Itachi — phải tái tạo nền bằng LaMa; script này đo và báo, không nhận.

Trước (đo 28/08–04/09): mỗi ảnh Gin tốn 11–39 tool call: `df -h`, `ls`, dò
cv2/easyocr đã cài chưa, viết PIL script xem kích thước, `vision_analyze` 5–15
lần để đọc chữ trên ảnh, chạy swap_image_text 2 lần. Giờ: một lệnh in danh sách vùng
chữ có SỐ THỨ TỰ + text OCR + toạ độ + màu + nền phẳng/ảnh + font đo được; vai
chỉ viết bản dịch tiếng Việt rồi chạy gin_submit.py.

Đầu vào: message_id của ảnh Ông Chủ gửi (tệp state/<brand>/telegram_incoming/
<id>.*), đường dẫn ảnh, HOẶC link post Instagram/X. Workdir:
state/<brand>/prepare/gin_<id>/.

Dùng:
    venv/bin/python gin_prepare.py 338                          # theo message_id
    venv/bin/python gin_prepare.py /path/anh.jpg                # theo đường dẫn
    venv/bin/python gin_prepare.py "https://www.instagram.com/p/ABC/?img_index=7"
    venv/bin/python gin_prepare.py "https://www.instagram.com/p/ABC/" --slide 7
"""
import argparse
import json
import re
import subprocess
import sys
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import env_load                                              # noqa: E402
import state_paths                                           # noqa: E402

import about_text                                                # noqa: E402

import cv2                                                   # noqa: E402
import numpy as np                                           # noqa: E402
from PIL import Image, ImageDraw                             # noqa: E402

# Bút vẽ rỗng, chỉ để ĐO bề ngang chữ khi chọn font (không vẽ ra tệp nào).
_BUT = ImageDraw.Draw(Image.new("RGB", (8, 8)))

SOCIAL = ROOT / "hermes" / "skills" / "social-crawl" / "scripts" / "social_fetch.py"

# Ngưỡng ĐO THẬT trên ảnh của đội 07/09/2026 (carousel Hello Kitty @teach 2048x2550,
# thẻ đen dưới ảnh; slide 338 bảng chart nền đen; slide 646 chữ trên nền trắng).
# `std_nen` = độ lệch chuẩn màu của NỀN quanh hộp chữ, đã trừ mọi hộp chữ khác:
#     nền phẳng thật (dải đen, nền trắng)      0.0 – 10.5
#     chữ đè lên ảnh thật (mặt người, phố)    28.9 – 55.5
# Khoảng trống giữa hai nhóm rất rộng; lấy 12.0 nằm gọn trong khoảng đó.
FLAT_STD = 12.0
# Tỉ lệ MỰC (pixel chữ / diện tích khung chữ) tách đậm khỏi thường. Đo cùng ngày:
#     thân bài regular   0.147 – 0.272
#     tiêu đề đậm        0.370 – 0.525
BOLD_ITEM = 0.32
# Đậm rồi thì chọn giữa BeVietnamPro-Bold và Oswald bằng `about_text.pick_font`:
# hỏi từng font "vẽ chuỗi này ra bề ngang bao nhiêu" rồi lấy font gần chữ gốc
# nhất. Không dùng ngưỡng cố định — xem chú thích trong about_text.pick_font.


def _download_link(url: str, slide: int = None) -> tuple:
    """Tải ảnh từ link Instagram/X về máy. Trả về (đường dẫn ảnh, id)."""
    q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
    if slide is None and q.get("img_index"):
        try:
            slide = int(q["img_index"][0])
        except ValueError:
            slide = None
    m = re.search(r"/(?:p|reel|status)/([A-Za-z0-9_-]+)", url)
    ma = m.group(1) if m else "post"
    dest = env_load.state_dir() / state_paths.DOWNLOADS_DIR / ma
    anh = sorted(dest.glob("[0-9][0-9].jpg")) if dest.exists() else []
    if not anh:
        # Endpoint crawl chay bat dong bo, mot luot mat 10–40s; social_fetch tu
        # thu lai. In JSON ra stdout nen phai nuot, chi giu stderr de bao loi.
        r = subprocess.run([sys.executable, str(SOCIAL), url, "--download", str(dest)],
                           capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            sys.exit(f"[LOI] không tải được {url}\n{(r.stderr or '').strip()[-600:]}")
        anh = sorted(dest.glob("[0-9][0-9].jpg"))
    if not anh:
        sys.exit(f"[LOI] link tải được nhưng không có ảnh nào trong {dest} "
                 "(post chỉ có video, hoặc X không trả media — X hay trả media[] rỗng).")
    if len(anh) > 1 and slide is None:
        ds = ", ".join(p.stem for p in anh)
        sys.exit(f"[LOI] carousel có {len(anh)} ảnh ({ds}) — chưa biết làm ảnh nào. "
                 f"Chạy lại kèm --slide N, hoặc dán link có ?img_index=N.")
    n = slide or 1
    p = dest / f"{n:02d}.jpg"
    if not p.exists():
        sys.exit(f"[LOI] không có ảnh {n} trong post (chỉ có {', '.join(q.stem for q in anh)}).")
    return p, f"{ma}_{n:02d}"


def find_image(dau_vao: str, slide: int = None) -> tuple:
    """(đường dẫn ảnh, id). id = message_id nếu đầu vào là số, <shortcode>_NN
    nếu là link."""
    if str(dau_vao).startswith(("http://", "https://")):
        return _download_link(str(dau_vao), slide)
    p = Path(dau_vao)
    if p.exists():
        return p, p.stem
    inc = env_load.state_dir() / "telegram_incoming"
    for q in sorted(inc.glob(f"{dau_vao}.*")):
        return q, dau_vao
    sys.exit(f"Không thấy ảnh {dau_vao!r} (đã tìm {inc}/{dau_vao}.*)")


def workdir(vai: str, id_: str) -> Path:
    wd = state_paths.prepare_root(env_load.state_dir()) / f"{vai}_{id_}"
    wd.mkdir(parents=True, exist_ok=True)
    return wd


def _extract_text(img_bgr, box):
    """(crop BGR, mặt nạ bool phía CHỮ trong crop) — tách Otsu, phía chữ là phía
    có ÍT pixel hơn (nền luôn chiếm nhiều hơn trong một hộp OCR)."""
    pts = np.array(box, dtype=np.int32)
    h, w = img_bgr.shape[:2]
    x0, y0 = max(0, pts[:, 0].min()), max(0, pts[:, 1].min())
    x1, y1 = min(w, pts[:, 0].max()), min(h, pts[:, 1].max())
    crop = img_bgr[y0:y1, x0:x1]
    if crop.size == 0:
        return None, None
    gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
    if gray.min() == gray.max():
        return crop, None
    nguong, _ = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    sang = gray > nguong
    return crop, (sang if sang.sum() < (~sang).sum() else ~sang)


def color_text(img_bgr, box) -> list:
    """Màu chữ thật (RGB) = trung vị pixel phía CHỮ sau khi tách Otsu trong box.
    Phía chữ là phía có ÍT pixel hơn (nền chiếm nhiều hơn) — không dùng độ sáng
    trung vị cả vùng vì vùng nhỏ hay lật (BodyMist 28/08 ra màu nền trắng)."""
    crop, chu = _extract_text(img_bgr, box)
    if crop is None:
        return [255, 255, 255]
    if chu is None:
        return [int(v) for v in crop.reshape(-1, 3).mean(axis=0)[::-1]]
    px = crop[chu]
    if px.size == 0:
        px = crop.reshape(-1, 3)
    med = np.median(px, axis=0)
    return [int(med[2]), int(med[1]), int(med[0])]


def distinctive_text(img_bgr, box, text: str) -> dict:
    """Đo CỠ và ĐỘ ĐẬM chữ gốc để chữ Việt vẽ đè lên bám sát nguyên mẫu.

    - `cao_net`: chiều cao MỰC thật (hàng có pixel chữ), không phải chiều cao
      hộp OCR — hộp rộng hơn nét chữ và rộng khác nhau tuỳ dòng có dấu hay không.
    - `muc`: pixel chữ / diện tích khung nét chữ → đậm hay thường.
    - `hep`: bề ngang trung bình một ký tự / chiều cao nét → font bó hẹp hay không.
    """
    crop, chu = _extract_text(img_bgr, box)
    if crop is None or chu is None:
        return {"cao_net": 0, "muc": 0.0, "font": "regular"}
    # Hang co IT hon 2% be ngang la muc, coi nhu khong phai net chu: thuong la
    # vien antialias hoac net thong xuong cua DONG BEN CANH lot vao hop OCR. De
    # nguyen thi 'global icon far' do ra cao 162px con 'into a timeless' cung co
    # chu chi 83px, va hai nua cua CUNG MOT DONG ve ra hai co (do that
    # 07/09/2026 tren slide Hello Kitty).
    dac = chu.sum(axis=1) >= max(1, int(chu.shape[1] * 0.02))
    rows = np.where(dac)[0]
    cols = np.where(chu.any(axis=0))[0]
    if rows.size == 0 or cols.size == 0:
        return {"cao_net": 0, "muc": 0.0, "font": "regular"}
    cao = int(rows[-1] - rows[0] + 1)
    rong = int(cols[-1] - cols[0] + 1)
    net = chu[rows[0]:rows[-1] + 1, cols[0]:cols[-1] + 1]
    muc = float(net.sum() / net.size)
    adv = rong / max(1, len((text or "").strip())) / max(1, cao)
    font = about_text.pick_font(_BUT, text, adv, muc >= BOLD_ITEM)
    return {"cao_net": cao, "muc": round(muc, 3), "adv": round(adv, 3), "font": font}


def measure_background(img_bgr, boxes: list, i: int) -> dict:
    """Nền quanh hộp chữ thứ i PHẲNG hay là ẢNH thật.

    Đo trên VÀNH quanh hộp, đã TRỪ mọi hộp chữ khác. Không trừ thì dòng kế bên
    lọt vào vành và mọi vùng đều ra "ảnh": đo thật trên slide Hello Kitty
    07/09/2026, cùng một dải đen phẳng cho std 51–106 khi để nguyên vành, còn
    0.0–4.0 sau khi trừ các dòng chữ khác.
    """
    h, w = img_bgr.shape[:2]
    che = np.zeros((h, w), np.uint8)
    for b in boxes:
        p = np.array(b, np.int32)
        x0, y0 = max(0, p[:, 0].min()), max(0, p[:, 1].min())
        x1, y1 = min(w, p[:, 0].max()), min(h, p[:, 1].max())
        pad = max(4, int((y1 - y0) * 0.12))
        che[max(0, y0 - pad):min(h, y1 + pad), max(0, x0 - pad):min(w, x1 + pad)] = 255
    p = np.array(boxes[i], np.int32)
    x0, y0 = max(0, p[:, 0].min()), max(0, p[:, 1].min())
    x1, y1 = min(w, p[:, 0].max()), min(h, p[:, 1].max())
    m = max(8, int((y1 - y0) * 0.8))
    X0, Y0 = max(0, x0 - m), max(0, y0 - m)
    X1, Y1 = min(w, x1 + m), min(h, y1 + m)
    sub, subche = img_bgr[Y0:Y1, X0:X1], che[Y0:Y1, X0:X1]
    px = sub[subche == 0]
    if px.size < 200 * 3:
        # Chu day dac quanh het vanh (khong con nen de do) — khong dam chac la
        # phang, de Itachi lam cho an toan.
        return {"nen": "anh", "std_nen": -1.0, "nen_rgb": None}
    px = px.reshape(-1, 3)
    std = float(np.std(px, axis=0).max())
    med = np.median(px, axis=0)
    return {"nen": "phang" if std <= FLAT_STD else "anh", "std_nen": round(std, 1),
            "nen_rgb": [int(med[2]), int(med[1]), int(med[0])]}


def ocr_region(anh: Path) -> tuple:
    """(img_bgr, [vùng]) — vùng: {stt, box, x, y, w, h, text, conf, color_rgb,
    nen, std_nen, nen_rgb, cao_net, muc, font, can}, sắp trên→dưới, trái→phải."""
    import swap_image_text
    img = cv2.imread(str(anh))
    if img is None:
        sys.exit(f"Không đọc được ảnh: {anh}")
    res = swap_image_text.find_region_text(img, verbose=False)
    boxes = [box for box, _, _ in res]
    vung = []
    for i, (box, text, conf) in enumerate(res):
        pts = np.array(box, dtype=np.int32)
        x, y = int(pts[:, 0].min()), int(pts[:, 1].min())
        w, h = int(pts[:, 0].max() - x), int(pts[:, 1].max() - y)
        v = {"box": [[int(a), int(b)] for a, b in box], "x": x, "y": y, "w": w, "h": h,
             "text": text, "conf": round(float(conf), 2), "color_rgb": color_text(img, box)}
        v.update(measure_background(img, boxes, i))
        v.update(distinctive_text(img, box, text))
        vung.append(v)
    _read_can_odd(vung, img.shape[1])
    vung.sort(key=lambda v: (round(v["y"] / max(1, img.shape[0]) * 40), v["x"]))
    for i, v in enumerate(vung, 1):
        v["stt"] = i
    return img, vung


def _read_can_odd(vung: list, w_anh: int) -> None:
    """Gán `can` cho từng vùng theo CỘT LỀ TRÁI chung của cả thẻ.

    Đoán từng hộp một là sai: một dòng dài gần hết bề ngang thì tâm nó trùng tâm
    ảnh, và luật "tâm trùng tâm ảnh thì căn giữa" biến đúng dòng dài nhất của một
    đoạn căn trái thành căn giữa — đo thật 07/09/2026, hai dòng thân bài slide
    Hello Kitty bị thụt vào giữa trong khi các dòng còn lại căn trái.
    """
    from collections import Counter
    tol = max(6, int(w_anh * 0.015))
    phang = [v for v in vung if v.get("nen") == "phang"]
    dem = Counter(round(v["x"] / tol) for v in phang)
    cot = dem.most_common(1)[0] if dem else (None, 0)
    for v in vung:
        if cot[1] >= 2 and round(v["x"] / tol) == cot[0]:
            v["can"] = "left"
        elif abs((v["x"] + v["w"] / 2) - w_anh / 2) / w_anh < 0.03:
            v["can"] = "center"
        else:
            v["can"] = "left"


def about_preview(img_bgr, vung: list, out: Path) -> None:
    vis = img_bgr.copy()
    for v in vung:
        mau = (0, 200, 0) if v.get("nen") == "phang" else (0, 0, 255)
        cv2.rectangle(vis, (v["x"], v["y"]), (v["x"] + v["w"], v["y"] + v["h"]), mau, 3)
        cv2.putText(vis, str(v["stt"]), (v["x"], max(28, v["y"] - 6)), cv2.FONT_HERSHEY_SIMPLEX,
                    1.0, mau, 3)
    out.parent.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(out), vis)


def write_brief(id_: str, anh: Path, img, vung: list, wd: Path) -> str:
    h, w = img.shape[:2]
    phang = [v for v in vung if v.get("nen") == "phang"]
    anh_v = [v for v in vung if v.get("nen") != "phang"]
    L = [f"# GIN — OCR XONG ảnh {id_}: {w}x{h}, {len(vung)} vùng chữ "
         f"({len(phang)} nền phẳng = việc của bạn, {len(anh_v)} nền ảnh = của Itachi)",
         f"Ảnh gốc: {anh}",
         f"Preview đánh số (mở MỘT lần nếu cần; xanh = nền phẳng, đỏ = nền ảnh): "
         f"{wd / state_paths.GIN_REGIONS_PREVIEW_FILE}", ""]
    L += ["## Vùng NỀN PHẲNG — bạn dịch (stt | text Anh | x,y,w,h | màu chữ | font đo được | nền)"]
    if not phang:
        L.append("(không có vùng nào nền phẳng — cả ảnh này là việc của Itachi, báo lại Ông Chủ.)")
    for v in phang:
        L.append(f"- {v['stt']:2d} | {v['text'][:56]!r} | {v['x']},{v['y']},{v['w']},{v['h']} | "
                 f"chữ {v['color_rgb']} | {v['font']} cao {v['cao_net']}px | nền {v['nen_rgb']}")
    if anh_v:
        L += ["", "## Vùng NỀN ẢNH — KHÔNG nhận (chữ đè lên ảnh thật, xoá là hỏng ảnh)"]
        for v in anh_v:
            L.append(f"- {v['stt']:2d} | {v['text'][:56]!r} | std nền {v['std_nen']} "
                     f"(> {FLAT_STD} là nền ảnh)")
        L.append("Ảnh có cả hai loại thì làm phần phẳng, và ghi `ghi_chu` báo Ông Chủ "
                 "chuyển phần còn lại cho Itachi.")
    L += ["", f"## Spec — viết vào {wd}/spec.json",
          json.dumps({"gop": [["<stt đầu>", "<stt cuối>", "<bản dịch cả đoạn>"]],
                      "vung": {"<stt>": "<bản dịch một dòng>", "<stt khác>": None},
                      "ghi_chu": "<tuỳ chọn, một câu cho Ông Chủ>"},
                     ensure_ascii=False, indent=1),
          "ĐOẠN NHIỀU DÒNG thì dùng `gop`: OCR trả một hộp mỗi DÒNG, mà câu tiếng Việt hiếm khi "
          "ngắt dòng giống bản Anh — dịch từng dòng là bản dịch dài hơn bị ép vào bề ngang dòng "
          "gốc rồi co nhỏ lại, lệch hẳn cỡ so với các dòng bên cạnh. Gộp cả đoạn thành một khối, "
          "script tự ngắt dòng trong khối đó. Nhãn, badge, tiêu đề một dòng thì dùng `vung`.",
          "Mỗi vùng nền phẳng phải khai: nằm trong một `gop`, có bản dịch, hoặc `null` nếu cố ý "
          "giữ nguyên chữ gốc (logo, tên thương hiệu). Quên khai là script dừng — quên và cố ý "
          "giữ phải phân biệt được. Màu chữ, cỡ chữ, font, căn lề lấy theo số đo ở trên, không "
          'cần ghi; muốn đè thì ghi {"text": "…", "font": "bold|regular|condensed|serif", '
          '"color_rgb": [r,g,b], "can": "left|center"}.',
          "", "## Rồi chạy đúng MỘT lệnh:",
          f"cd {ROOT} && venv/bin/python gin_submit.py {id_}",
          "Script trám nền phẳng, vẽ chữ Việt đúng vị trí/màu/cỡ/font đo được, chặn tiếng Việt "
          "mất dấu và chữ tràn hộp, gửi kết quả trả lời đúng tin nhắn. KHÔNG df/ls/pip, KHÔNG "
          "viết PIL script, KHÔNG vision_analyze từng ảnh, KHÔNG chạy swap_image_text.py/"
          "send_telegram.py tay."]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Brief thay chữ trên thẻ quote cho Gin")
    ap.add_argument("anh", help="message_id, đường dẫn ảnh, hoặc link post Instagram/X")
    ap.add_argument("--slide", type=int, default=None,
                    help="Ảnh thứ mấy trong carousel (mặc định lấy ?img_index= trong link)")
    ap.add_argument("--im", action="store_true")
    a = ap.parse_args()
    anh, id_ = find_image(a.anh, a.slide)
    wd = workdir("gin", id_)
    img, vung = ocr_region(anh)
    about_preview(img, vung, wd / state_paths.GIN_REGIONS_PREVIEW_FILE)
    (wd / state_paths.GIN_REGIONS_OCR_FILE).write_text(json.dumps({"anh": str(anh), "id": id_, "w": img.shape[1],
                                                  "h": img.shape[0], "vung": vung},
                                                 ensure_ascii=False, indent=1), encoding="utf-8")
    brief = write_brief(id_, anh, img, vung, wd)
    (wd / "brief.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
