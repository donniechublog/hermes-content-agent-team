#!/usr/bin/env python3
"""miles_chuan_bi.py — BRIEF cho Miles (writer): moi thu de viet caption, in MOT lan.

Do 04/09/2026 truoc khi doi: moi task Miles 14-24 tool call — caption_check chay
2-13 lan (vong sua lap), curl/grep tu doc lai bai, python3 /tmp/cnt.py dem ky tu
8 lan, patch caption nhieu lan. Nguyen nhan: vai phai tu gom tu lieu, tu dem, tu
doan luat. Gio:

  - Tu lieu lay lai tu engine chuan bi cua vai anh (cung draft_id, cung bo nguon
    — bai viet giai thich dung cai doc gia thay tren anh); chua co thi engine
    chay (khong can anh).
  - Ban giao cua vai anh (hook tren the/bia, nguon anh) dan san.
  - Moi luat co hoc cua caption (do dai, the HTML, em-dash, link, cum sao rong,
    so lieu, tu cong bo) in mot lan kem con so cu the; miles_nop.py do lai va
    bao dung cho, vai khong phai dem.

Dung:
    venv/bin/python miles_chuan_bi.py <draft_id>
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import anh_chuan_bi as cb                                    # noqa: E402
import caption_check                                         # noqa: E402

DRAFTS = cb.DRAFTS
GIONG = {
    "donniechublog": ("dân kỹ thuật: hỏi *làm thế nào*; con số đáng nhớ là benchmark, tham số, tốc độ; "
                      "thuật ngữ quen (transformer, fine-tune, inference) giữ nguyên"),
    "dcgr": ("dân kinh doanh, tài chính, truyền thông (cạnh dân công nghệ): hỏi *rồi sao nữa* — ai được lợi, "
             "ai mất phần, tốn bao nhiêu, đổi cách làm việc thế nào; con số đáng nhớ là tiền, thị phần, quy mô, "
             "thời gian; thuật ngữ giải thích gọn ngay trong câu; tin có nghịch lý/vòng lợi ích thì mở bằng "
             "chính nghịch lý, không mở bằng nguồn tin"),
}


def viet_brief(m: dict, meta: dict, wd: Path) -> str:
    brand = cb._brand_cua(meta)
    # Diem va ly do cham nam san trong meta.json (approve_service.write_meta).
    # Truoc day boc bang regex tu VAN BAN body task: doi mot chu trong mau la
    # regex chet im (regex tom tat da chet nhu the, audit 05/09/2026).
    diem = str(meta.get("score") if meta.get("score") is not None else "")
    ly_do = str(meta.get("score_reason") or "")
    bg = ""
    for p in (DRAFTS / f"{m['draft_id']}.ban_giao.md", wd / f"{m['draft_id']}.ban_giao.md"):
        if p.exists():
            bg = p.read_text(encoding="utf-8")
            break
    L = [f"# MILES — TƯ LIỆU ĐÃ SẴN: {m['title']}",
         f"Brand: {brand} | draft: {m['draft_id']} | category: {meta.get('category', '')} | via: {meta.get('via', '')}",
         f"Link gốc (thật): {m['link']}"]
    if m.get("tieu_de_en"):
        L.append(f"Tiêu đề bài gốc: {m['tieu_de_en']}")
    if ly_do:
        L.append(f"Điểm chấm: {diem}/100 — lý do (dùng cho câu Ý NGHĨA, không suy diễn thêm): {ly_do}")
    L += ["", f"## Người đọc: {GIONG.get(brand, GIONG['donniechublog'])}"]
    L += ["", "## Tư liệu thật (CHỈ viết những gì có ở đây; nguồn không nói thì ghi \"chưa công bố\")"]
    if m.get("summary"):
        L.append(f"Tóm tắt (Finn/Vera, chỉ là điểm khởi đầu): {m['summary']}")
    tl = m.get("tu_lieu", {})
    cs = tl.get("cau_co_so", [])
    if cs:
        L.append(f"Câu có số liệu ({len(cs)} câu — caption PHẢI có số, lấy từ đây):")
        for i, c in enumerate(cs[:25], 1):
            L.append(f"  {i}. {c}")
    else:
        L.append("(Nguồn không bóc được câu có số — nói rõ là thiếu số liệu, KHÔNG bịa số.)")
    if tl.get("doan_dau"):
        L.append(f"Đoạn đầu bài gốc: {tl['doan_dau'][:1500]}")
    if bg:
        L += ["", "## Ảnh đã duyệt (bàn giao từ vai ảnh — caption bổ trợ cho ảnh, không lặp lại hook)", bg.strip()]
    L += ["", f"## Viết caption vào: {wd}/caption.txt  (CHỈ caption, HTML Telegram)",
          "Bốn ý bắt buộc, mỗi ý một câu là đủ, mỗi CÂU xuống dòng riêng, mỗi ĐOẠN cách một dòng trống:",
          "  1. Chuyện gì vừa xảy ra, kèm con số quan trọng nhất.",
          "  2. So sánh: hơn/kém cái gì, cách biệt bao nhiêu; nguồn nói chỗ THUA thì phải nói.",
          "  3. Hạn chế hoặc điều kiện kèm theo, nếu nguồn có.",
          "  4. Ý nghĩa: vì sao quan trọng (theo lý do chấm điểm), nói thẳng bằng thông tin cụ thể.",
          f"Độ dài: nhắm 800–1000 ký tự, tối đa {caption_check.GIOI_HAN} (giới hạn chú thích ảnh Telegram). "
          f"Thẻ HTML chỉ <b> <i> <code>. Không em-dash (— –). Không URL/tên miền sống (viết z . ai). "
          f"Cấm cụm: {', '.join(caption_check.SAO_RONG)}; cấm thổi phồng: {', '.join(caption_check.THOI_PHONG[:6])}… "
          "Số liệu hãng tự công bố phải ghi rõ \"hãng tự công bố\". Không lặp một cụm 6 từ hai lần. "
          "Chỉ dùng số có trong tư liệu.",
          "", "## Rồi chạy đúng MỘT lệnh:",
          f"cd {ROOT} && venv/bin/python miles_nop.py {m['draft_id']}",
          "Script tự chuẩn hoá (em-dash → phẩy), đếm ký tự/câu/số, chạy cổng chặn, ghép draft, đẩy vào hàng "
          "duyệt. Báo [LOI] thì sửa đúng chỗ đó trong caption.txt rồi chạy lại. KHÔNG tự đếm ký tự, KHÔNG "
          "curl đọc lại bài, KHÔNG chạy caption_check/draft_write/approve_service tay."]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Brief caption cho Miles")
    ap.add_argument("draft_id")
    ap.add_argument("--lam-moi", action="store_true")
    ap.add_argument("--im", action="store_true")
    ap.add_argument("--cho", type=int, default=300)
    a = ap.parse_args()
    # Engine dung chung: da chay tu luc chon tin (vai anh) -> chi doc; chua co thi
    # chay khong browser (Miles chi can chu).
    m, wd, meta = cb.chay(a.draft_id, a.lam_moi, khong_browser=True, cho=a.cho)
    brief = viet_brief(m, meta, wd)
    (wd / "brief_miles.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
