#!/usr/bin/env python3
"""gin_nop.py — NỘP của Gin: xoá chữ bằng LaMa theo vùng OCR (trừ vùng `giu`),
ghi nen_sach.png, mask_debug.png, vung.json (vị trí + màu chữ đã đo, cho Itachi
dịch tại chỗ), gửi trả lời đúng tin nhắn Ông Chủ. Spec là tuỳ chọn.

Dùng:
    venv/bin/python gin_nop.py 338                 # xoá hết vùng chữ, gửi
    venv/bin/python gin_nop.py 338 --khong-gui     # thử, không gửi Telegram
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import gin_chuan_bi as gb                                    # noqa: E402

import cv2                                                   # noqa: E402


def don(id_: str, wd: Path, spec: dict) -> tuple:
    """Xoá chữ. Trả về (nen_sach, mask_debug, vung_json, số vùng xoá, số vùng giữ)."""
    import doi_chu_anh
    import luat_anh
    d = json.loads((wd / "vung_ocr.json").read_text(encoding="utf-8"))
    anh = Path(d["anh"])
    img = cv2.imread(str(anh))
    giu_stt = {int(x) for x in (spec.get("giu") or []) if str(x).isdigit()}
    # STT LA thi truoc 06/09/2026 bi bo IM LANG: vai go nham mot so, vung do
    # khong duoc giu, chu bi xoa mat — va vai tuong da giu duoc. Khac han y dinh.
    co_that = {int(v["stt"]) for v in d["vung"]}
    la = sorted(giu_stt - co_that)
    if la:
        sys.exit(f"[LOI] `giu` co stt khong ton tai: {', '.join(map(str, la))} "
                 f"(anh nay chi co vung {', '.join(map(str, sorted(co_that)))}). "
                 "Sua spec.json roi chay lai — go nham mot so la mot vung chu bi "
                 "xoa mat ma khong ai bao.")
    giu_list = [(v["x"], v["y"], v["w"], v["h"]) for v in d["vung"] if v["stt"] in giu_stt]
    xoa_them = []
    for r in spec.get("xoa_them") or []:
        try:
            xoa_them.append(tuple(int(x) for x in r))
        except (TypeError, ValueError):
            continue
    boxes = [(v["box"], v["text"], v["conf"]) for v in d["vung"]]
    mask = doi_chu_anh.dung_mask(img, boxes, giu_list, verbose=False)
    for x, y, w, h in xoa_them:
        mask[y:y + h, x:x + w] = 255
    if not mask.any():
        sys.exit("[LOI] Không có vùng nào để xoá (mọi vùng đều nằm trong `giu`, hoặc OCR không thấy chữ).")
    sach = doi_chu_anh.inpaint(img, mask, verbose=False)
    nen = wd / "nen_sach.png"
    cv2.imwrite(str(nen), sach)
    luat_anh.dong_dau_tep(nen, "doi_chu_anh")
    vis = img.copy()
    vis[mask > 0] = (0, 0, 255)
    vis = cv2.addWeighted(img, 0.5, vis, 0.5, 0)
    mask_dbg = wd / "mask_debug.png"
    cv2.imwrite(str(mask_dbg), vis)
    da_xoa = [v for v in d["vung"] if v["stt"] not in giu_stt]
    vung_json = wd / "vung.json"
    vung_json.write_text(json.dumps(
        [{"stt": v["stt"], "x": v["x"], "y": v["y"], "w": v["w"], "h": v["h"],
          "color_rgb": v["color_rgb"], "ocr_text": v["text"], "conf": v["conf"]} for v in da_xoa],
        ensure_ascii=False, indent=1), encoding="utf-8")
    return nen, mask_dbg, vung_json, len(da_xoa), len(giu_list)


def main() -> int:
    ap = argparse.ArgumentParser(description="Nộp dọn chữ của Gin")
    ap.add_argument("id", help="message_id (đã chạy gin_chuan_bi.py)")
    ap.add_argument("--khong-gui", action="store_true")
    a = ap.parse_args()
    wd = gb.workdir("gin", a.id)
    if not (wd / "vung_ocr.json").exists():
        sys.exit(f"Chưa chuẩn bị. Chạy trước: venv/bin/python gin_chuan_bi.py {a.id}")
    spec = {}
    if (wd / "spec.json").exists():
        try:
            spec = json.loads((wd / "spec.json").read_text(encoding="utf-8"))
        except Exception as e:                               # noqa: BLE001
            sys.exit(f"[LOI] spec.json không phải JSON hợp lệ: {type(e).__name__}: {e}")
    nen, mask_dbg, vung_json, so_xoa, so_giu = don(a.id, wd, spec)
    mo_ta = (f"Nền sạch ảnh {a.id}: xoá {so_xoa} vùng chữ" + (f", giữ {so_giu} vùng" if so_giu else "")
             + ". Ảnh 2 là mask debug (đỏ = vùng đã xoá)."
             + (f" {spec['ghi_chu']}" if spec.get("ghi_chu") else ""))
    mid = None
    if a.khong_gui:
        print(f"[thu] không gửi. {nen} | {mask_dbg} | {vung_json}")
    else:
        import gui_telegram
        reply = int(a.id) if str(a.id).isdigit() else None
        try:
            res = gui_telegram.post("gin", [str(nen), str(mask_dbg)], mo_ta[:1000], reply_to=reply)
        except gui_telegram.GuiLoi as e:
            sys.exit(f"[LOI] {e}")
        rr = res.get("result")
        mid = (rr[-1] if isinstance(rr, list) else rr or {}).get("message_id")
    print(f"[xong] xoá {so_xoa} vùng, giữ {so_giu} -> {nen}; vung.json cho Itachi: {vung_json}"
          + (f"; đã gửi topic gin (message_id={mid})" if mid else ""))
    print(f"Kết quả (trả lời Ông Chủ đúng một câu): Đã dọn ảnh {a.id}: xoá {so_xoa} vùng chữ"
          + (f", giữ {so_giu} vùng logo" if so_giu else "") + ", nền sạch và mask đã gửi trong topic."
          + (f" {spec['ghi_chu']}" if spec.get("ghi_chu") else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
