#!/usr/bin/env python3
"""gin_submit.py — NỘP của Gin: trám nền THẺ QUOTE rồi VẼ CHỮ VIỆT lên đúng chỗ,
đúng màu, cỡ và font đo được từ chữ gốc; chặn tiếng Việt mất dấu và chữ tràn
hộp; gửi kết quả trả lời đúng tin nhắn Ông Chủ.

Chỉ nhận vùng NỀN PHẲNG (thẻ/dải một màu). Trám bằng `cv2.inpaint` chứ không
LaMa: nền phẳng thì Telea trám đúng trong ~0.1s, còn LaMa mất ~2 phút/ảnh trên
CPU cho cùng kết quả. LaMa để dành cho Itachi — chữ đè lên ảnh thật, chỗ duy
nhất cv2.inpaint để lại vệt loang.

Hàm `don()` phía dưới là đường CŨ (LaMa, xoá sạch chữ, trả nền cho Itachi vẽ
lên): `itachi_prepare.py` gọi nó, đừng bỏ.

Dùng:
    venv/bin/python gin_submit.py 338                 # spec ở state/<brand>/chuan_bi/gin_338/spec.json
    venv/bin/python gin_submit.py 338 --khong-gui     # thử, không gửi Telegram
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import gin_prepare as gb                                    # noqa: E402
import submit_common as nc                                       # noqa: E402
import about_text                                                # noqa: E402
from card import find_face_mark, drop_mark_forbid                     # noqa: E402

import cv2                                                   # noqa: E402
import numpy as np                                           # noqa: E402
from PIL import Image, ImageDraw                             # noqa: E402

BAN_KINH_TRAM = 5      # px lan toa cua cv2.inpaint (Telea) — du trum vien mo chu
RATIO_HAS_MIN = 0.75   # chu ve ra duoi 75% co chu goc thi coi la khong dat


def single(id_: str, wd: Path, spec: dict) -> tuple:
    """Xoá chữ. Trả về (nen_sach, mask_debug, vung_json, số vùng xoá, số vùng giữ)."""
    import swap_image_text
    import image_rules
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
    mask = swap_image_text.use_mask(img, boxes, giu_list, verbose=False)
    for x, y, w, h in xoa_them:
        mask[y:y + h, x:x + w] = 255
    if not mask.any():
        sys.exit("[LOI] Không có vùng nào để xoá (mọi vùng đều nằm trong `giu`, hoặc OCR không thấy chữ).")
    sach = swap_image_text.inpaint(img, mask, verbose=False)
    nen = wd / "nen_sach.png"
    cv2.imwrite(str(nen), sach)
    image_rules.stamp_file(nen, "doi_chu_anh")
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


def _no_box(box, shape) -> list:
    """Nới hộp OCR ra một chút trước khi dựng mask.

    Hộp EasyOCR ôm sát chữ tới mức nét cuối hay lòi ra ngoài vài px: dấu nháy
    đóng của `"yes."` nằm ngoài hộp nên không vào mask, xoá xong còn một vệt
    trắng nổi trên nền đen (đo thật 07/09/2026). Nới theo CHIỀU CAO chữ chứ
    không theo số px cố định — ảnh 2048px và ảnh 1080px lệch nhau hơn hai lần.
    """
    h_anh, w_anh = shape[:2]
    p = np.array(box, np.int32)
    x0, y0 = int(p[:, 0].min()), int(p[:, 1].min())
    x1, y1 = int(p[:, 0].max()), int(p[:, 1].max())
    pad = max(4, int((y1 - y0) * 0.08))
    x0, y0 = max(0, x0 - pad), max(0, y0 - pad)
    x1, y1 = min(w_anh, x1 + pad), min(h_anh, y1 + pad)
    return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]]


def _box_translate(d: dict, spec: dict) -> tuple:
    """(danh sách khối cần vẽ, danh sách lỗi). Khối: vùng OCR + bản dịch."""
    vung = {str(v["stt"]): v for v in d["vung"]}
    khai = spec.get("vung") or {}
    if not isinstance(khai, dict):
        return [], ['spec.json: "vung" phải là object {"<stt>": "<bản dịch>"} — xem brief.md.']
    if not khai and not spec.get("gop"):
        return [], ['spec.json chưa có `gop` lẫn `vung` — chưa khai bản dịch nào. Xem brief.md.']
    ep = {str(x) for x in (spec.get("ep_phang") or [])}
    loi, khoi, da_gop = [], [], set()
    # GOP: cau tieng Viet hiem khi ngat dong giong cau tieng Anh. OCR tra MOT
    # hop moi DONG, nen dich tung hop thi ban dich dai hon bi ep vao be ngang
    # cua dong goc va co nho lai — do that 07/09/2026: mot dong thu bai ra chu
    # be bang nua cac dong con lai. Gop ca doan thanh mot khoi roi wrap trong
    # khoi do moi ra dung mot co chu.
    for g in spec.get("gop") or []:
        try:
            a, b, text = int(g[0]), int(g[1]), str(g[2])
        except (TypeError, ValueError, IndexError):
            loi.append('gop phải là [stt_đầu, stt_cuối, "bản dịch"]')
            continue
        ds = [vung[str(k)] for k in range(a, b + 1) if str(k) in vung]
        if not ds:
            loi.append(f"gop {a}..{b} không có vùng nào")
            continue
        ngoai = [v["stt"] for v in ds if v.get("nen") != "phang" and str(v["stt"]) not in ep]
        if ngoai:
            loi.append(f"gop {a}..{b} chứa vùng nền ảnh {ngoai} — việc của Itachi. "
                       "Thu hẹp dải gộp, hoặc thêm vào `ep_phang` nếu đã xem preview.")
            continue
        text = drop_mark_forbid(text.strip())
        if not text:
            loi.append(f"gop {a}..{b}: bản dịch rỗng")
            continue
        x0, y0 = min(v["x"] for v in ds), min(v["y"] for v in ds)
        x1, y1 = max(v["x"] + v["w"] for v in ds), max(v["y"] + v["h"] for v in ds)
        cao = sorted(v.get("cao_net") or 0 for v in ds)[len(ds) // 2]
        # Nhip dong THAT: khoang cach giua hai dinh dong lien nhau tren anh goc.
        dinh = sorted({v["y"] for v in ds})
        buoc = sorted(b - a for a, b in zip(dinh, dinh[1:])) if len(dinh) > 1 else []
        # Can le va font lay theo DA SO cac vung thanh vien. Khong lay tu vung
        # dau tien: mot doan can giua ma OCR cat dong dau thanh hai hop thi vung
        # dau ra "left" va ca doan lech (carousel TECHS 07/09/2026). Cung khong
        # so tam hop gop voi tam anh: mot doan CAN TRAI dai gan het be ngang thi
        # tam no cung trung tam anh, va ca doan bi thut vao giua (slide Hello
        # Kitty). `_doc_can_le` da doc cot le trai chung cua ca the roi.
        cans = [v.get("can") or "left" for v in ds]
        can = max(set(cans), key=cans.count)
        fonts = [v.get("font") or "regular" for v in ds]
        khoi.append({"stt": f"{a}-{b}", "x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0,
                     "vung_goc": ds, "text": text,
                     "text_goc": " ".join(v["text"] for v in ds),
                     "cao_net": cao or int((y1 - y0) * 0.5),
                     "font": max(set(fonts), key=fonts.count),
                     "buoc": buoc[len(buoc) // 2] if buoc else None,
                     "color_rgb": ds[0]["color_rgb"], "can": can})
        da_gop.update(str(v["stt"]) for v in ds)
    la = [k for k in khai if k not in vung]
    if la:
        loi.append(f"`vung` có stt không tồn tại: {', '.join(sorted(la))} "
                   f"(ảnh này chỉ có {', '.join(sorted(vung, key=lambda x: int(x)))}).")
    # Vung NEN PHANG ma vai QUEN khai: chu goc se bi xoa neu nam trong mask, hoac
    # o lai tieng Anh giua mot the da dich. Hai y dinh do phai phan biet duoc,
    # nen quen la dung — muon giu chu goc thi ghi null.
    quen = [v["stt"] for v in d["vung"]
            if v.get("nen") == "phang" and str(v["stt"]) not in khai
            and str(v["stt"]) not in da_gop]
    if quen:
        loi.append(f"vùng nền phẳng {', '.join(str(x) for x in sorted(quen))} chưa khai trong "
                   "`vung` — dịch thì ghi bản dịch, cố ý giữ chữ gốc thì ghi null.")
    for k, val in khai.items():
        v = vung.get(k)
        if v is None or val is None or k in da_gop:
            continue
        if v.get("nen") != "phang" and k not in ep:
            loi.append(f"vùng {k} {v['text'][:32]!r} nằm trên NỀN ẢNH (std {v.get('std_nen')}), "
                       "xoá là hỏng ảnh — đó là việc của Itachi. Ghi null để giữ nguyên, "
                       'hoặc thêm "ep_phang": [' + k + "] nếu bạn đã xem preview và chắc nền phẳng.")
            continue
        if isinstance(val, str):
            val = {"text": val}
        if not isinstance(val, dict):
            loi.append(f"vùng {k}: phải là chuỗi bản dịch, null, hoặc object "
                       '{"text": …, "font": …, "color_rgb": …, "can": …}.')
            continue
        text = drop_mark_forbid(str(val.get("text") or "").strip())
        if not text:
            loi.append(f"vùng {k}: bản dịch rỗng — ghi null nếu cố ý giữ chữ gốc.")
            continue
        khoi.append({"stt": v["stt"], "x": v["x"], "y": v["y"], "w": v["w"], "h": v["h"],
                     "vung_goc": [v], "text": text, "text_goc": v["text"],
                     "cao_net": v.get("cao_net") or int(v["h"] * 0.7),
                     "font": val.get("font") or v.get("font") or "regular",
                     "color_rgb": val.get("color_rgb") or v["color_rgb"],
                     "buoc": None,
                     "can": val.get("can") or v.get("can") or "left"})
    return khoi, loi


def make_card(id_: str, wd: Path, spec: dict, bo_qua_dau: bool) -> tuple:
    """Trám nền + vẽ chữ Việt. Trả về (đường dẫn kết quả, khối đã vẽ, lỗi)."""
    d = json.loads((wd / "vung_ocr.json").read_text(encoding="utf-8"))
    img = cv2.imread(str(Path(d["anh"])))
    if img is None:
        return None, [], [f"không đọc được ảnh gốc {d['anh']}"]
    khoi, loi = _box_translate(d, spec)
    if not khoi and not loi:
        loi.append("không có vùng nào được dịch (mọi vùng đều null).")
    if loi:
        return None, [], loi

    # Cong TRAN HOP chay TRUOC khi trám: hong thi anh goc con nguyen, khong de
    # lai mot tep nen da xoa chu ma chua ve gi.
    do = ImageDraw.Draw(Image.new("RGB", (8, 8)))
    for kh in khoi:
        if not bo_qua_dau and find_face_mark(kh["text"]):
            loi.append(f"vùng {kh['stt']}: tiếng Việt mất dấu: {kh['text'][:50]!r}")
        mong = about_text.has_by_original(do, kh["text_goc"], kh["cao_net"], kh["font"])
        tran = about_text.ceiling_box(do, kh["text"], kh["w"], kh["h"], kh["font"],
                               mong, kh["buoc"], kh["cao_net"])
        if tran:
            loi.append(f"vùng {kh['stt']}: bản dịch {kh['text'][:36]!r} tràn hộp {tran}px kể cả "
                       f"khi đã nhỏ hết cỡ ({about_text.HAS_MIN}px) — rút gọn câu.")
            continue
        # CONG CO CHU: "vua hop" thoi thi chua du. Ban dich dai hon cau goc bi thu
        # nho de nhet vua, va mot khoi chu be bang nua khoi ben canh trong ngay ra
        # la khong dat "sat nguyen mau ve co chu". Do that 07/09/2026: mot dong
        # thu bai slide Hello Kitty ve ra co 55% co goc, lech han cac dong khac.
        that = about_text.pick_has(do, kh["text"], kh["w"], kh["h"], kh["font"], mong,
                              kh["buoc"], kh["cao_net"])
        if that < mong * RATIO_HAS_MIN:
            loi.append(f"vùng {kh['stt']}: bản dịch {kh['text'][:36]!r} phải thu xuống {that}px "
                       f"mới vừa hộp, chữ gốc {mong}px — lệch quá {int((1-RATIO_HAS_MIN)*100)}%, "
                       "nhìn sẽ bé hẳn so với dòng bên cạnh. Rút gọn câu, hoặc `gop` cả đoạn "
                       "để có chỗ rộng hơn.")
    if loi:
        return None, [], loi

    import swap_image_text
    import image_rules
    # Tram TUNG VUNG bang chinh mau nen do duoc, khong dua het cho cv2.inpaint.
    # Telea lan mau tu vien vao trong, net chu DAY thi giua net khong voi toi
    # vien va con lai mot bong ma xam hinh chu — thay ro tren tieu de condensed
    # anh TECHS 07/09/2026. Vung da xac dinh la nen phang thi mau nen la mot so
    # DA BIET, to thang vao la sach tuyet doi, khong phai doan.
    sach = img.copy()
    mask = np.zeros(img.shape[:2], np.uint8)
    # CHUA vung khong phai cua minh. Mask no rong de nuot vien chu co the tran
    # sang hop ben canh; hop ben canh lai la vung Itachi giu nguyen, va Gin to
    # mau nen de len giua chu tieng Anh cua no (anh TECHS 07/09/2026: dai den
    # cat ngang "AI COULD BECOME"). Tram cua minh dung o ranh giới.
    lam = {v["stt"] for kh in khoi for v in kh["vung_goc"]}
    chua = np.zeros(img.shape[:2], np.uint8)
    for v in d["vung"]:
        if v["stt"] in lam:
            continue
        p = np.array(v["box"], np.int32)
        cv2.fillPoly(chua, [p], 255)
    for kh in khoi:
        for v in kh["vung_goc"]:
            # No mask theo CHIEU CAO CHU, khong theo so px co dinh. Chu tren
            # the quote thuong co vien/bong toi phia sau de noi len khoi anh;
            # Otsu chi bat duoc NET SANG, vien toi bi coi la nen va o lai —
            # xoa xong con nguyen bong ma den hinh chu (anh TECHS 07/09/2026,
            # tieu de cao 132px, vien day hon 10px mac dinh cua doi_chu_anh).
            # Vung nen phang thi no rong khong mat gi: cho nao thua cung chi to
            # lai dung mau nen.
            no = max(swap_image_text.DILATE_PX, int((v.get("cao_net") or v["h"]) * 0.15))
            m = swap_image_text.use_mask(img, [(_no_box(v["box"], img.shape), v["text"], 1.0)],
                                      [], dilate_px=no, verbose=False)
            m[chua > 0] = 0
            mask = cv2.bitwise_or(mask, m)
    if not mask.any():
        return None, [], ["mask rỗng — không có nét chữ nào để xoá."]
    # To thang mau nen do duoc thi SAI o cho nen chuyen mau: dai chu duoi cung
    # slide Hello Kitty nam ngay mep anh mo dan, to phang [4,2,2] de lai mot
    # mang toi hinh chu (do that 07/09/2026). Telea lan mau tu vien nen bam
    # theo chuyen mau; bong ma truoc day la do VIEN chu chua vao mask, da sua
    # bang cach no mask theo chieu cao chu.
    sach = cv2.inpaint(img, mask, BAN_KINH_TRAM, cv2.INPAINT_TELEA)

    im = Image.fromarray(cv2.cvtColor(sach, cv2.COLOR_BGR2RGB))
    dd = ImageDraw.Draw(im)
    for kh in khoi:
        co = about_text.has_by_original(dd, kh["text_goc"], kh["cao_net"], kh["font"])
        about_text.about_block(dd, kh["text"], kh["x"], kh["y"], kh["w"], kh["h"],
                       kh["font"], kh["color_rgb"], kh["can"], co=co, buoc=kh["buoc"],
                       cao_goc=kh["cao_net"])
    out = wd / f"ket_qua_{id_}.png"
    im.save(out, "PNG")
    image_rules.stamp_file(out, "doi_chu_anh")
    vis = img.copy()
    vis[mask > 0] = (0, 0, 255)
    cv2.imwrite(str(wd / "mask_debug.png"), cv2.addWeighted(img, 0.5, vis, 0.5, 0))
    return out, khoi, []


def main() -> int:
    ap = argparse.ArgumentParser(description="Nộp thẻ quote tiếng Việt của Gin")
    ap.add_argument("id", help="id đã chạy gin_prepare.py")
    ap.add_argument("--khong-gui", action="store_true")
    ap.add_argument("--bo-qua-dau", action="store_true",
                    help="Chỉ khi bản dịch THẬT SỰ là tiếng Anh (tên riêng, mã sản phẩm)")
    a = ap.parse_args()
    wd = gb.workdir("gin", a.id)
    if not (wd / "vung_ocr.json").exists():
        sys.exit(f"Chưa chuẩn bị. Chạy trước: venv/bin/python gin_prepare.py {a.id}")
    if not (wd / "spec.json").exists():
        sys.exit(f"Chưa có spec: {wd / 'spec.json'} — viết theo brief ({wd / 'brief.md'}) "
                 "rồi chạy lại.")
    try:
        spec = json.loads((wd / "spec.json").read_text(encoding="utf-8"))
    except Exception as e:                                   # noqa: BLE001
        sys.exit(f"[LOI] spec.json không phải JSON hợp lệ: {type(e).__name__}: {e}")

    out, khoi, loi = make_card(a.id, wd, spec, a.bo_qua_dau)
    if loi:
        for e in loi:
            print(f"[LOI] {e}")
        return nc.count_round_error(wd, loi, f"venv/bin/python gin_submit.py {a.id}")

    d = json.loads((wd / "vung_ocr.json").read_text(encoding="utf-8"))
    con = [v["stt"] for v in d["vung"] if v.get("nen") != "phang"]
    mo_ta = (f"Thẻ quote tiếng Việt (ảnh {a.id}): thay {len(khoi)} vùng chữ."
             + (f" Còn {len(con)} vùng nằm trên nền ảnh (stt {', '.join(str(x) for x in con)}) "
                "— việc của Itachi." if con else "")
             + (f" {spec['ghi_chu']}" if spec.get("ghi_chu") else ""))
    mid = None
    if a.khong_gui:
        print(f"[thu] không gửi. {out}")
    else:
        import send_telegram
        reply = int(a.id) if str(a.id).isdigit() else None
        try:
            res = send_telegram.post("gin", [str(out)], mo_ta[:1000], reply_to=reply)
        except send_telegram.SendError as e:
            sys.exit(f"[LOI] {e}")
        rr = res.get("result")
        mid = (rr[-1] if isinstance(rr, list) else rr or {}).get("message_id")
    print(f"[xong] {len(khoi)} vùng -> {out}"
          + (f"; đã gửi topic gin (message_id={mid})" if mid else ""))
    print("Kết quả (trả lời Ông Chủ đúng một câu): " + mo_ta)
    return 0


if __name__ == "__main__":
    sys.exit(main())
