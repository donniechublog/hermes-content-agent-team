#!/usr/bin/env python3
"""miles_prepare.py — BRIEF cho Miles (writer): moi thu de viet caption, in MOT lan.

Do 04/09/2026 truoc khi doi: moi task Miles 14-24 tool call — caption_check chay
2-13 lan (vong sua lap), curl/grep tu doc lai bai, python3 /tmp/cnt.py dem ky tu
8 lan, patch caption nhieu lan. Nguyen nhan: vai phai tu gom tu lieu, tu dem, tu
doan luat. Gio:

  - Tu lieu lay lai tu engine chuan bi cua vai anh (cung draft_id, cung bo nguon
    — bai viet giai thich dung cai doc gia thay tren anh); chua co thi engine
    chay (khong can anh).
  - Ban giao cua vai anh (hook tren the/bia, nguon anh) dan san.
  - Moi luat co hoc cua caption (do dai, the HTML, em-dash, link, cum sao rong,
    so lieu, tu cong bo) in mot lan kem con so cu the; miles_submit.py do lai va
    bao dung cho, vai khong phai dem.

Dung:
    venv/bin/python miles_prepare.py <draft_id>
"""
import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import image_prepare as cb                                    # noqa: E402
import route_missing_images                                       # noqa: E402
import caption_check                                         # noqa: E402
import submit_common as nc                                        # noqa: E402
import state_paths                                                # noqa: E402

DRAFTS = cb.DRAFTS
VOICE = {
    "donniechublog": ("dân kỹ thuật: hỏi *làm thế nào*; con số đáng nhớ là benchmark, tham số, tốc độ; "
                      "thuật ngữ quen (transformer, fine-tune, inference) giữ nguyên"),
    "dcgr": ("dân kinh doanh, tài chính, truyền thông (cạnh dân công nghệ): hỏi *rồi sao nữa* — ai được lợi, "
             "ai mất phần, tốn bao nhiêu, đổi cách làm việc thế nào; con số đáng nhớ là tiền, thị phần, quy mô, "
             "thời gian; thuật ngữ giải thích gọn ngay trong câu; tin có nghịch lý/vòng lợi ích thì mở bằng "
             "chính nghịch lý, không mở bằng nguồn tin"),
}


def write_brief(m: dict, meta: dict, wd: Path, persona: str = "miles") -> str:
    brand = cb._brand_of(meta)
    # Diem va ly do cham nam san trong meta.json (approve_service.write_meta).
    # Truoc day boc bang regex tu VAN BAN body task: doi mot chu trong mau la
    # regex chet im (regex tom tat da chet nhu the, audit 05/09/2026).
    diem = str(meta.get("score") if meta.get("score") is not None else "")
    ly_do = str(meta.get("score_reason") or "")
    bg = ""
    for p in (state_paths.handoff_file(DRAFTS, m['draft_id']), state_paths.handoff_file(wd, m['draft_id'])):
        if p.exists():
            bg = p.read_text(encoding="utf-8")
            break
    L = [f"# {persona.upper()} — TƯ LIỆU ĐÃ SẴN: {m['title']}",
         f"Brand: {brand} | draft: {m['draft_id']} | category: {meta.get('category', '')} | via: {meta.get('via', '')}",
         f"Link gốc (thật): {m['link']}"]
    if m.get("title_en"):
        L.append(f"Tiêu đề bài gốc: {m['title_en']}")
    if ly_do:
        L.append(f"Điểm chấm: {diem}/100 — lý do (dùng cho câu Ý NGHĨA, không suy diễn thêm): {ly_do}")
    L += ["", f"## Người đọc: {VOICE.get(brand, VOICE['donniechublog'])}"]
    import brief_common
    L += brief_common.block_material(
        m, tieu_de='## Tư liệu thật (CHỈ viết những gì có ở đây; nguồn không nói thì ghi "chưa công bố")',
        nhan="Finn/Vera, chỉ là điểm khởi đầu", n_cau=25, n_doan=1500,
        dong_thieu="(Nguồn không bóc được câu có số — nói rõ là thiếu số liệu, KHÔNG bịa số.)")
    if bg:
        L += ["", "## Ảnh đã duyệt (bàn giao từ vai ảnh — caption bổ trợ cho ảnh, không lặp lại hook)", bg.strip()]
    L += ["", f"## Viết caption vào: {wd}/caption.txt  (CHỈ caption, HTML Telegram)",
          "CÂU ĐẦU là hook khiến người đang lướt dừng lại: một con số lớn, một tình huống mâu thuẫn, một nghịch lý, "
          "một hệ quả bất ngờ. Không mở bằng \"Hãng X vừa công bố\" hay bằng nguồn tin; không lặp hook trên ảnh.",
          "Bốn ý bắt buộc, mỗi ý một câu là đủ, mỗi CÂU xuống dòng riêng, mỗi ĐOẠN cách một dòng trống:",
          "  1. Chuyện gì vừa xảy ra, kèm con số quan trọng nhất.",
          "  2. So sánh: hơn/kém cái gì, cách biệt bao nhiêu; nguồn nói chỗ THUA thì phải nói.",
          "  3. Hạn chế hoặc điều kiện kèm theo, nếu nguồn có.",
          "  4. Ý nghĩa: vì sao quan trọng (theo lý do chấm điểm), nói thẳng bằng thông tin cụ thể.",
          "Độ dài: từ khoảng 800 ký tự trở lên cho đủ ý, trần cứng "
          f"{caption_check.CEILING_BACKGROUND_LAYER}. Caption dài script tự tách khi đăng, KHÔNG cần cắt cho ngắn lại. "
          f"Thẻ HTML chỉ <b> <i> <code>. Không em-dash (— –). Không URL/tên miền sống (viết z . ai). "
          f"Cấm cụm: {', '.join(caption_check.STAR_EMPTY)}; cấm thổi phồng: {', '.join(caption_check.TIME_ROOM[:6])}… "
          "Số liệu hãng tự công bố phải ghi rõ \"hãng tự công bố\". Không lặp một cụm 6 từ hai lần. "
          "Chỉ dùng số có trong tư liệu.",
          "", "## Rồi chạy đúng MỘT lệnh:",
          f"cd {ROOT} && venv/bin/python {persona}_submit.py {m['draft_id']}",
          "Script tự chuẩn hoá (em-dash → phẩy), đếm ký tự/câu/số, chạy cổng chặn, ghép draft, đẩy vào hàng "
          "duyệt. CHỈ khi script báo [LOI] mới sửa đúng chỗ đó trong caption.txt rồi chạy lại. Dòng [nhac] là cảnh "
          "báo mềm, KHÔNG phải lỗi: không sửa, không chạy lại vì nó. Thấy dòng [xong] nghĩa là ĐÃ ĐẨY VÀO HÀNG "
          "DUYỆT: kết thúc task ngay, KHÔNG chạy lại lệnh nộp (mỗi lần nộp lại là đổi thẻ trong topic của Ông Chủ). "
          "KHÔNG tự đếm ký tự, KHÔNG curl đọc lại bài, KHÔNG chạy caption_check/draft_write/approve_service tay."]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Brief caption cho vai viet (Miles/Jika)")
    ap.add_argument("draft_id")
    ap.add_argument("--lam-moi", action="store_true")
    ap.add_argument("--im", action="store_true")
    ap.add_argument("--cho", type=int, default=300)
    a = ap.parse_args()
    # Engine dung chung: da chay tu luc chon tin (vai anh) -> chi doc; chua co thi
    # chay khong browser (Miles chi can chu).
    m, wd, meta = cb.run(a.draft_id, a.lam_moi, khong_browser=True, cho=a.cho,
                          sau_chuan_bi=route_missing_images.after_prepare)
    # AI viet bai nay (LOW-13): quyet dinh da chot tu luc chon tin, nam trong
    # sidecar writer.json. Ten tep brief va lenh nop in ra deu theo persona do.
    persona = nc.writer_persona_name(nc.writer_for_article(a.draft_id, cb._brand_of(meta)))
    brief = write_brief(m, meta, wd, persona)
    (wd / f"brief_{persona}.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
