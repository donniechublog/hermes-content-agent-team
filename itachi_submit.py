#!/usr/bin/env python3
"""itachi_submit.py — NỘP của Itachi: vẽ chữ Việt tại chỗ (retouch/blend chờ
GPU, đợt tới) hoặc dựng deck.py theo spec, cổng chặn tiếng Việt, gửi album trả lời
đúng tin nhắn.

Vẽ tại chỗ: mỗi vùng OCR gốc (x,y,w,h, màu đo được) nhận bản dịch; chọn cỡ chữ
lớn nhất còn vừa bề ngang và chiều cao box (tối thiểu 16px), font theo chiều
cao (≥4.5% ảnh → bold, không thì regular) trừ khi spec ghi `font`; `gop`
[a, b, text] gộp dải vùng a..b thành một khối, wrap nhiều dòng trong khối đó.

Màu chữ MẶC ĐỊNH giữ nguyên màu đo được lúc OCR (gin_prepare.color_text, đo
TRÊN ẢNH GỐC, trước khi xoá) — giữ đúng thiết kế gốc. Nhưng nền dưới đó là
NỀN ĐÃ XOÁ/VẼ LẠI (LaMa), có thể lệch tông so với lúc đo màu chữ; script tự
đo lại độ tương phản THẬT giữa màu đó và nền hiện tại (`text_bg.py`, dùng
chung với card.py/carousel.py/render_edu.py) ngay trước khi vẽ — chỉ khi
KHÔNG đủ mới đổi sang màu an toàn (trắng/đen tuỳ nền), xem `_color_hide_whole`.

Dùng:
    venv/bin/python itachi_submit.py 338              # spec ở state/<brand>/prepare/itachi_338/spec.json
    venv/bin/python itachi_submit.py 338 --khong-gui  # thử
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import gin_prepare as gb                                    # noqa: E402
import state_paths                                          # noqa: E402
import text_bg                                               # noqa: E402
import submit_common as nc                                       # noqa: E402
from vietnamese import find_face_mark, drop_mark_forbid               # noqa: E402
import about_text                                                # noqa: E402
from about_text import HAS_MIN                                    # noqa: E402  (giu ten cu cho phan duoi)

# Ti le tuong phan toi thieu (WCAG) giua mau chu va nen — muc "chu lon/dam"
# (3.0) chu khong phai muc "chu thuong" (4.5): chu dich luon to/dam het co
# theo _about_block. Duoi muc nay moi doi mau, dung "mac dinh khong doi gi neu
# khong can" — giu dung thiet ke goc khi van con doc duoc.
THRESHOLD_WALL_PART = 3.0

# Luat VE (font, co chu, mau, cong tran hop) da chuyen sang about_text.py (ten cu
# about_text.py, 07/09/2026) de Gin dung chung. Bon ten duoi la loi vao cu, giu
# nguyen cach goi (LOW-56: ghep nhanh rename/jean-to-cape len main da doi ten).
_font_default = about_text.font_default
_about_block = about_text.about_block
_ceiling_box = about_text.ceiling_box
_color = about_text.to_color


def _color_hide_whole(color_rgb, nen_vung) -> tuple:
    """Mau chu OCR do tren anh GOC (truoc khi xoa) co con du tuong phan voi
    NEN THAT sau khi da xoa/ve lai (LaMa) khong — do thang tren pixel
    (text_bg.py), khong doan. Du roi thi GIU NGUYEN mau goc (mac dinh khong
    doi gi). Khong du (nen sau khi xoa lech tong so voi luc do mau chu) moi
    doi sang mau AN TOAN — trang tren nen toi, den tren nen sang.

    -> (mau_dung, co_doi_khong)."""
    if nen_vung.width < 1 or nen_vung.height < 1:
        return color_rgb, False
    mau_nen = text_bg.color_average(nen_vung)
    if text_bg.ratio_wall_part(color_rgb, mau_nen) >= THRESHOLD_WALL_PART:
        return color_rgb, False
    sang, _ = text_bg.measure_bright_offset(nen_vung)
    return ((255, 255, 255) if sang < 128 else (0, 0, 0)), True


def about_download_wait(s: dict, muc: dict, out: Path, bo_qua_dau: bool) -> list:
    """Trả về danh sách lỗi (rỗng = đã vẽ xong ra `out`)."""
    loi = []
    vung = {str(v["stt"]): v for v in s["vung"]}
    im = Image.open(s["nen_sach"]).convert("RGB")
    d = ImageDraw.Draw(im)
    da_dung = set()
    khoi = []
    for g in muc.get("gop") or []:
        try:
            a, b, text = int(g[0]), int(g[1]), str(g[2])
        except (TypeError, ValueError, IndexError):
            loi.append(f"slide {s['id']}: gop phải là [stt_đầu, stt_cuối, \"bản dịch\"]")
            continue
        ds = [vung[str(k)] for k in range(a, b + 1) if str(k) in vung]
        if not ds:
            loi.append(f"slide {s['id']}: gop {a}..{b} không có vùng nào")
            continue
        x0, y0 = min(v["x"] for v in ds), min(v["y"] for v in ds)
        x1, y1 = max(v["x"] + v["w"] for v in ds), max(v["y"] + v["h"] for v in ds)
        khoi.append({"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0, "text": text,
                     "color_rgb": ds[0]["color_rgb"], "font": None, "align": "left",
                     "h_dong": max(v["h"] for v in ds)})
        da_dung.update(str(v["stt"]) for v in ds)
    for k, val in (muc.get("vung") or {}).items():
        if k in da_dung or val is None:
            continue
        v = vung.get(str(k))
        if not v:
            loi.append(f"slide {s['id']}: vùng {k} không tồn tại (có: {', '.join(vung)})")
            continue
        if isinstance(val, str):
            val = {"text": val}
        text = str(val.get("text") or "").strip()
        if not text:
            continue
        khoi.append({"x": v["x"], "y": v["y"], "w": v["w"], "h": v["h"], "text": text,
                     "color_rgb": val.get("color_rgb") or v["color_rgb"], "font": val.get("font"),
                     "align": val.get("align") or "left", "h_dong": v["h"]})
    if not khoi and not loi:
        loi.append(f"slide {s['id']}: tai_cho nhưng không có vùng nào được dịch")
    # VUNG OCR KHONG CO TRONG SPEC: truoc 06/09/2026 vong tren chi duyet cac
    # khoa CO trong `muc["vung"]`, nen mot vung vai QUEN khai thi bien mat y het
    # vung vai co y bo (`null`) — chu goc bi xoa, chu dich khong duoc ve, khong
    # mot dong [LOI]. Hai y dinh do phai phan biet duoc.
    da_khai = set(da_dung) | {str(k) for k in (muc.get("vung") or {})}
    quen = [k for k in vung if str(k) not in da_khai]
    if quen:
        loi.append(f"slide {s['id']}: vùng {', '.join(sorted(quen, key=lambda x: int(x) if str(x).isdigit() else 0))} "
                   "chưa khai trong spec — dịch thì ghi bản dịch, cố ý bỏ trống "
                   "thì ghi null (chữ gốc đã bị xoá, không khai là mất hẳn)")
    for kh in khoi:
        kh["text"] = drop_mark_forbid(kh["text"])
        if not bo_qua_dau and find_face_mark(kh["text"]):
            loi.append(f"slide {s['id']}: tiếng Việt mất dấu: {kh['text'][:50]!r}")
        tran = _ceiling_box(d, kh["text"], kh["w"], kh["h"],
                         kh["font"] or _font_default(kh["h_dong"], s["h"]))
        if tran:
            loi.append(f"slide {s['id']}: bản dịch {kh['text'][:36]!r} tràn hộp "
                       f"{tran}px kể cả khi đã nhỏ hết cỡ ({HAS_MIN}px) — rút gọn "
                       "câu, hoặc gộp vùng để có chỗ rộng hơn")
        # Mau chu do luc OCR (tren anh GOC) co the khong con du tuong phan voi
        # NEN THAT sau khi LaMa da xoa/ve lai — do lai tren dung pixel se hien
        # (im la nen_sach, chua ve gi len o day). Chi doi mau khi that su
        # khong du, con lai giu nguyen thiet ke goc.
        nen_vung = im.crop((kh["x"], kh["y"], kh["x"] + kh["w"], kh["y"] + kh["h"]))
        kh["color_rgb"], da_doi_mau = _color_hide_whole(_color(kh["color_rgb"]), nen_vung)
        if da_doi_mau:
            print(f"[canh bao] slide {s['id']}: vùng {kh['x']},{kh['y']} màu chữ gốc "
                  "không đủ tương phản với nền sau khi đã xoá — đã đổi sang màu an toàn",
                  file=sys.stderr)
    if loi:
        return loi
    for kh in khoi:
        _about_block(d, kh["text"], kh["x"], kh["y"], kh["w"], kh["h"],
                 kh["font"] or _font_default(kh["h_dong"], s["h"]), kh["color_rgb"], kh["align"])
    out.parent.mkdir(parents=True, exist_ok=True)
    im.save(out, "PNG")
    return []


def main() -> int:
    ap = argparse.ArgumentParser(description="Nộp remake carousel của Itachi")
    ap.add_argument("khoa", help="id slide đầu (khoá bộ, đã chạy itachi_prepare.py)")
    ap.add_argument("--khong-gui", action="store_true")
    ap.add_argument("--bo-qua-dau", action="store_true")
    a = ap.parse_args()
    wd = gb.workdir("itachi", a.khoa)
    if not (wd / state_paths.MANIFEST_FILE).exists():
        sys.exit(f"Chưa chuẩn bị. Chạy trước: venv/bin/python itachi_prepare.py {a.khoa}")
    m = json.loads((wd / state_paths.MANIFEST_FILE).read_text(encoding="utf-8"))
    slides = {s["id"]: s for s in m["slides"]}
    if not (wd / "spec.json").exists():
        sys.exit(f"Chưa có spec: {wd / 'spec.json'} — viết theo brief ({wd / 'brief.md'}) rồi chạy lại.")
    try:
        spec = json.loads((wd / "spec.json").read_text(encoding="utf-8"))
    except Exception as e:                                   # noqa: BLE001
        sys.exit(f"[LOI] spec.json không phải JSON hợp lệ: {type(e).__name__}: {e}")

    loi, files, deck_slides, deck_idx = [], [], [], []
    for i, muc in enumerate(spec.get("slides") or [], 1):
        sid = str(muc.get("nguon") or "")
        s = slides.get(sid)
        if not s:
            loi.append(f"mục {i}: nguon {sid!r} không có trong bộ (có: {', '.join(slides)})")
            continue
        cach = (muc.get("cach") or "tai_cho").lower()
        out = wd / (f"ket_qua_{sid}.png")
        if cach == "tai_cho":
            loi += about_download_wait(s, muc, out, a.bo_qua_dau)
            files.append(out)
        elif cach == "deck":
            ds = {k: v for k, v in muc.items() if k not in ("nguon", "cach", "bg_anh")}
            if muc.get("bg_anh"):
                ds["bg_anh"] = s["nen_sach"]
            if ds.get("layout") not in ("statement", "list_steps", "checklist", "grid3", "cover"):
                loi.append(f"mục {i}: layout {ds.get('layout')!r} không hợp lệ")
            deck_slides.append(ds)
            deck_idx.append(out)
            files.append(out)
        else:
            loi.append(f"mục {i}: cach phải là \"tai_cho\" hoặc \"deck\"")
    if not files and not loi:
        loi.append("spec không có slide nào")
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        return nc.count_round_error(wd, loi,
                               f"venv/bin/python itachi_submit.py {a.khoa}")
    if deck_slides:
        p_spec = wd / "deck.spec.json"
        p_spec.write_text(json.dumps({"slides": deck_slides}, ensure_ascii=False, indent=1), encoding="utf-8")
        stem = wd / "deck"
        r = subprocess.run([sys.executable, str(ROOT / "deck.py"), "--spec", str(p_spec), "--out", f"{stem}.png"]
                           + (["--bo-qua-dau"] if a.bo_qua_dau else []),
                           cwd=str(ROOT), capture_output=True, text=True, timeout=600)
        if r.returncode != 0:
            for d in ((r.stderr or "") + "\n" + (r.stdout or "")).strip().splitlines()[-8:]:
                print(f"[LOI] {d}")
            print(f"\nSửa {wd / 'spec.json'} rồi chạy lại: venv/bin/python itachi_submit.py {a.khoa}")
            return 1
        ra = [Path(f"{stem}.png")] + [Path(f"{stem}_{k}.png") for k in range(2, len(deck_slides) + 1)]
        for src, dst in zip(ra, deck_idx):
            src.replace(dst)
    thieu = [str(f) for f in files if not f.exists()]
    if thieu:
        sys.exit(f"[LOI] thiếu tệp kết quả: {thieu}")
    mo_ta = f"Remake {len(files)} slide tiếng Việt (bộ {a.khoa})"
    mid = None
    if a.khong_gui:
        print(f"[thu] không gửi. {[str(f) for f in files]}")
    else:
        import send_telegram
        reply = int(a.khoa) if str(a.khoa).isdigit() else None
        try:
            res = send_telegram.post("itachi", [str(f) for f in files], mo_ta, reply_to=reply)
        except send_telegram.SendError as e:
            sys.exit(f"[LOI] {e}")
        rr = res.get("result")
        mid = (rr[-1] if isinstance(rr, list) else rr or {}).get("message_id")
    print(f"[xong] {len(files)} slide -> {wd}" + (f"; đã gửi topic itachi (message_id={mid})" if mid else ""))
    print(f"Kết quả (trả lời Ông Chủ đúng một câu): Đã dựng {len(files)} slide tiếng Việt cho bộ {a.khoa}, "
          "album đã gửi trong topic.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
