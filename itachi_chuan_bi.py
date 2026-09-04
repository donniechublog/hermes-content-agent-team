#!/usr/bin/env python3
"""itachi_chuan_bi.py — BRIEF cho Itachi (remake carousel: deck.py hoặc dịch tại chỗ).

Đầu vào: một hay nhiều message_id ảnh nguồn (slide tiếng Anh) Ông Chủ gửi. Với
mỗi ảnh, script tự làm phần của Gin nếu chưa có (OCR + LaMa → nen_sach.png +
vung.json), rồi in cho vai: chữ tiếng Anh từng vùng theo thứ tự đọc (không cần
vision), gợi ý cách làm, khung spec cho hai đường:

  - "tai_cho": dịch từng vùng, vẽ đúng vị trí/màu/cỡ chữ gốc (nhãn, tiêu đề
    ngắn; đoạn nhiều dòng thì gộp các vùng liền nhau bằng `gop`).
  - "deck": thiết kế lại bằng deck.py, 5 layout (statement, list_steps,
    checklist, grid3, cover), nền là nen_sach.png.

Trước (đo 27–28/08): mỗi lượt Itachi 33 tool call — ls/pip list/which tesseract,
PIL script đo ảnh, vision_analyze 4–7 lần, đọc deck.py. Phần vẽ tại chỗ nằm
trong itachi_nop.py; retouch/blend/nền AI chờ GPU (CPU quá nặng), đợt tới bật.

Dùng:
    venv/bin/python itachi_chuan_bi.py 338            # một slide
    venv/bin/python itachi_chuan_bi.py 336 338 340    # nhiều slide (id đầu là khoá bộ)
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import gin_chuan_bi as gb                                    # noqa: E402

LAYOUT_HELP = {
    "statement": '{"layout": "statement", "badge": "<tuỳ chọn, vd STEP 1>", "heading": "<câu lớn>", "subs": [{"text": "<dòng phụ>", "col": "white|cream|coral|blue|grey", "bold": false}]}',
    "list_steps": '{"layout": "list_steps", "badge": "<tuỳ chọn>", "serif": "<phần serif nghiêng>", "sans": "<phần sans đậm>", "rows": ["<dòng 1>", "<dòng 2>"], "footer": "<tuỳ chọn>"}',
    "checklist": '{"layout": "checklist", "title1": "<màu 1>", "title2": "<màu 2>", "sub": "<phụ đề>", "items": ["<mục>", "<mục>"], "footer1": "<tuỳ chọn>", "footer2": "<tuỳ chọn>"}',
    "grid3": '{"layout": "grid3", "badge": "<tuỳ chọn>", "serif": "…", "sans": "…", "sub": "<tuỳ chọn>", "nhan": [{"text": "<nhãn>", "x": <tâm x>, "y": <y>}], "footer": "<tuỳ chọn>"}',
    "cover": '{"layout": "cover", "tiers": [[["<DÒNG 1>", "<DÒNG 2>"], 150, 90], [["<dòng nhỏ>"], 80, 50]], "ghi_chu": {"text": "<ghi chú tay, tuỳ chọn>", "nghieng": -6, "x": 640}}',
}


def chuan_bi_slide(id_: str) -> dict:
    """Bảo đảm có OCR + nền sạch cho một ảnh (tự chạy phần Gin nếu chưa có)."""
    anh, id_ = gb.tim_anh(id_)
    wd = gb.workdir("gin", id_)
    if not (wd / "vung_ocr.json").exists():
        img, vung = gb.ocr_vung(anh)
        gb.ve_preview(img, vung, wd / "vung_preview.png")
        (wd / "vung_ocr.json").write_text(json.dumps({"anh": str(anh), "id": id_, "w": img.shape[1],
                                                      "h": img.shape[0], "vung": vung},
                                                     ensure_ascii=False, indent=1), encoding="utf-8")
    if not (wd / "nen_sach.png").exists():
        import gin_nop
        spec = {}
        if (wd / "spec.json").exists():
            spec = json.loads((wd / "spec.json").read_text(encoding="utf-8"))
        gin_nop.don(id_, wd, spec)
    d = json.loads((wd / "vung_ocr.json").read_text(encoding="utf-8"))
    vung = json.loads((wd / "vung.json").read_text(encoding="utf-8")) if (wd / "vung.json").exists() else []
    return {"id": id_, "anh": str(anh), "w": d["w"], "h": d["h"], "nen_sach": str(wd / "nen_sach.png"),
            "vung": vung, "so_vung_ocr": len(d["vung"])}


def goi_y_cach(s: dict) -> str:
    v = s["vung"]
    if not v:
        return "không có chữ: cover/statement trên nền sạch"
    cao = sorted(x["h"] for x in v)
    dong_dai = sum(1 for x in v if x["w"] > s["w"] * 0.55)
    if len(v) <= 4 and dong_dai <= 1:
        return "tai_cho (ít vùng, nhãn/tiêu đề ngắn)"
    if dong_dai >= 3:
        return "deck (đoạn văn nhiều dòng: statement/list_steps), hoặc tai_cho có gop"
    return "tai_cho nếu vùng rời nhau; deck nếu là đoạn"


def viet_brief(slides: list, khoa: str, wd: Path) -> str:
    L = [f"# ITACHI — ĐÃ CHUẨN BỊ {len(slides)} slide (khoá bộ: {khoa})",
         "Nền sạch (đã xoá chữ Anh) và vùng chữ gốc đã có sẵn cho từng slide. Bạn chỉ viết chữ Việt.", ""]
    for s in slides:
        L.append(f"## Slide {s['id']}: {s['w']}x{s['h']} | nền sạch: {s['nen_sach']} | gợi ý: {goi_y_cach(s)}")
        if not s["vung"]:
            L.append("  (không có vùng chữ)")
        for v in s["vung"]:
            L.append(f"  - v{v['stt']} | {v['ocr_text'][:70]!r} | x={v['x']} y={v['y']} w={v['w']} h={v['h']} | màu {v['color_rgb']}")
        L.append("")
    L += [f"## Viết spec vào: {wd}/spec.json — một mục cho MỖI slide, giữ thứ tự",
          json.dumps({"slides": [
              {"nguon": slides[0]["id"], "cach": "tai_cho",
               "vung": {"1": "<bản dịch vùng 1, có dấu>", "2": None,
                        "3": {"text": "<bản dịch>", "font": "bold|regular|serif|condensed|mono", "align": "left|center", "color_rgb": [255, 255, 255]}},
               "gop": [["<stt đầu>", "<stt cuối>", "<bản dịch cả đoạn, nhiều dòng tự xuống>"]]},
              {"nguon": "<id slide khác>", "cach": "deck", "layout": "statement", "bg_anh": True,
               "heading": "<câu lớn>", "subs": [{"text": "<dòng phụ>"}]},
          ]}, ensure_ascii=False, indent=1),
          "tai_cho: khoá là stt vùng (v1→\"1\"); null = bỏ vùng (logo/nhiễu OCR, nền sạch để trống); `gop` gộp "
          "một dải vùng liền nhau (đoạn văn) thành một khối rồi dịch cả đoạn. Màu: script dùng màu đo được; hai "
          "dòng cùng khối mà màu lệch hẳn (một tối một gần trắng) thì ghi color_rgb theo dòng đúng.",
          "deck: bg_anh true = dùng nền sạch của slide đó; bỏ bg_anh thì nền phẳng (\"bg\": \"cream\" hoặc đen). "
          "Trường theo layout:"]
    for k, v in LAYOUT_HELP.items():
        L.append(f"  {k}: {v}")
    L += ["Bảng màu deck: đen, kem, san hô, xanh — không chế màu khác. Chữ tiếng Việt có dấu, không em-dash. "
          "Không tự vẽ minh hoạ; logo/hình khối thương hiệu gốc là quyết định của Ông Chủ, không tự thay.",
          "", "## Rồi chạy đúng MỘT lệnh:",
          f"cd {ROOT} && venv/bin/python itachi_nop.py {khoa}",
          "Script vẽ chữ tại chỗ hoặc dựng deck.py, chạy cổng chặn tiếng Việt, gửi album trả lời đúng tin nhắn. "
          "Báo [LOI] thì sửa spec.json rồi chạy lại. KHÔNG ls/pip/which, KHÔNG PIL script, KHÔNG vision_analyze "
          "từng ảnh, KHÔNG chạy deck.py/doi_chu_anh.py/gui_telegram.py tay, KHÔNG dùng tool clarify."]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Brief remake carousel cho Itachi")
    ap.add_argument("ids", nargs="+", help="message_id (hoặc đường dẫn) các slide nguồn")
    ap.add_argument("--im", action="store_true")
    a = ap.parse_args()
    slides = [chuan_bi_slide(x) for x in a.ids]
    khoa = slides[0]["id"]
    wd = gb.workdir("itachi", khoa)
    (wd / "xong.json").write_text(json.dumps({"khoa": khoa, "slides": slides}, ensure_ascii=False, indent=1),
                                  encoding="utf-8")
    brief = viet_brief(slides, khoa, wd)
    (wd / "brief.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
