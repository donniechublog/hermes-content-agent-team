#!/usr/bin/env python3
"""dre_prepare.py — BRIEF cho Dre (carousel). Phan co hoc nam o image_prepare.py
(engine dung chung); tep nay chi in ban chuan bi theo cach nhin cua Dre: bang
anh voi ma A1..An va nhan "dung duoc o dau" cho carousel, tu lieu, khung spec.

Dung:
    venv/bin/python dre_prepare.py <draft_id>            # in brief (chay engine neu chua)
    venv/bin/python dre_prepare.py <draft_id> --lam-moi  # bo cache, lam lai
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import image_prepare as cb                                    # noqa: E402
import schema                                                # noqa: E402
import manifest_values                                       # noqa: E402
import state_paths                                           # noqa: E402
import route_missing_images                                       # noqa: E402
import image_rules_dre                                       # noqa: E402
import role                                                  # noqa: E402

DRAFTS = cb.DRAFTS


def write_brief(m: dict, da_dung: dict | None) -> str:
    import carousel
    import brief_common
    L = brief_common.mark(
        m, "DRE",
        f"Brand: {m['brand']} | draft: {m['draft_id']} | slide tối thiểu: {m['min_images']}"
        + (" (FLAGSHIP: tin model của hãng frontier)" if m["flagship"] else "")
        + " | tối đa 10 | quote ≥ 2")
    L += brief_common.block_redo(
        da_dung,
        f"bìa {da_dung.get('cover_image')}, ảnh dùng {', '.join(da_dung.get('image_ids', []))}, "
        f"hook: “{da_dung.get('hook', '')}”. Lần này BÌA và HOOK phải khác, đổi ít "
        "nhất nửa số ảnh, đổi cách chia slide." if da_dung else "")
    L += brief_common.block_material(
        m, n_cau=99, n_doan=100000,
        tieu_de='## Tư liệu thật (khẳng định số liệu/so sánh CHỈ khi có ở đây; nguồn không nói '
                'thì ghi "chưa công bố" như Miles — không suy luận thay từ việc nhìn chart)',
        dong_thieu="(Không bóc được chữ từ nguồn — viết từ tóm tắt, KHÔNG bịa số, KHÔNG tự đọc "
                   "đường cong trên chart rồi kết luận thay.)")
    L.append("")
    L.append("Ảnh chart/Figure của paper (nếu có, mã A? kèm alt \"Figure N: ...\") là MINH HOẠ, "
             "không phải căn cứ để tự suy ra ai thắng ai thua. Chỉ viết khẳng định so sánh/kết quả "
             "cụ thể (vd \"ăn baseline\", \"vượt X%\") nếu câu đó có trong tư liệu chữ ở trên; "
             "không có thì mô tả trung tính (\"so sánh N phương pháp trên benchmark\") hoặc ghi "
             "\"chưa công bố\" — copy của bạn phải khớp với caption của Miles, không được nói ngược.")
    L.append("")
    L.append("## Ảnh đã tải & xử lý xong — chỉ dùng MÃ ẢNH, không tải/crop/mở gì thêm")
    if not m["images"]:
        L.append("KHÔNG CÓ ảnh thật nào dùng được. Không dựng hình giả. Kết thúc task bằng "
                 "một câu: \"Không tìm được ảnh thật cho tin này\" kèm link đã thử.")
    if m.get("kite_unavailable"):
        L.append("🛑 0 ẢNH THẬT dùng được và brand này CHƯA CÓ KITE. KHÔNG dựng hình giả. Kết thúc "
                 "task bằng một câu: \"Không có ảnh thật cho tin này, brand chưa có Kite\" — Ông Chủ "
                 "đã nhận nút Bỏ hẳn trên topic.")
        return "\n".join(L)
    if m.get("kite_task_id"):
        # Noi DUNG so anh, khong go cung "0": tu LOW-382 bai chuyen Kite khi
        # THIEU anh (1..min-1) chu khong chi khi rong, nen cau "0 anh that" cu
        # noi sai voi phan lon truong hop — va vai doc no truoc khi lam gi.
        _thieu = m.get("missing_images") or {}
        _so = _thieu.get("count", m.get("usable_count", 0))
        _tt = _thieu.get("min_images", m.get("min_images", 5))
        L.append(f"🛑 TIN NÀY ĐÃ CHUYỂN KITE (task {m['kite_task_id']}) vì chỉ có {_so}/{_tt} "
                 "ảnh thật dùng được. KHÔNG viết spec, KHÔNG dựng. Kết thúc task ngay bằng "
                 f"một câu: \"Đã chuyển Kite vì chỉ có {_so}/{_tt} ảnh thật\".")
        return "\n".join(L)
    # Mac dinh bang CUNG cong thuc voi nguoi ghi (schema.count_image_use_ok): ban
    # cu dem `len([a for a in m["images"] if a["uses"]])` — mot so KHAC, vi chum anh
    # khai niem phai dem la MOT (F2).
    so_dd = m.get("usable_count", schema.count_image_use_ok(m.get("images"), "dre"))
    if m["images"] and so_dd < m.get("min_images", 5):
        L.append(f"⚠️ THIẾU ẢNH: chỉ {so_dd} slide dựng được, cần ≥ {m.get('min_images', 5)}. "
                 "KHÔNG nhồi ảnh không liên quan cho đủ. Việc của bạn: TỰ ĐI TÌM — "
                 f"`cd {ROOT} && venv/bin/python find_more_images.py {m['draft_id']} --tu-khoa \"<từ khoá "
                 "TIẾNG ANH cụ thể>\"` (hãng, sản phẩm, nhà máy, sự kiện, người trong bài; có URL "
                 "trang/ảnh thì `--url`), tối đa 3 lượt, rồi chạy lại lệnh brief này. Hết 3 lượt "
                 "vẫn thiếu mới kanban_block, kể rõ từ khoá đã thử.")
    if m.get("domains") is not None:
        L.append(f"Ảnh dùng được lấy từ {len(m['domains'])} nguồn: {', '.join(m['domains']) or '—'}"
                 + (" — chỉ MỘT nguồn; bộ ≥4 slide nên có ảnh từ ≥2 nguồn, cân nhắc gộp ý."
                    if len(m['domains']) == 1 and so_dd >= 4 else ""))
    if m.get("not_yet_seen"):
        L.append(f"⚠️ CHƯA AI NHÌN {', '.join(m['not_yet_seen'])} (vision không chạy) — nhãn dưới chỉ là đo "
                 "số, có thể sai; mở contact_sheet.png trước khi dùng.")
    if m.get("is_ranking_story"):
        L.append(cb.ranking_brief_line(m, "bìa ", "dre_submit"))
    for a in m["images"]:
        if a.get("relevant") is False:
            L.append(f"- {a['id']}: ❌ KHÔNG LIÊN QUAN — {a.get('description') or 'không rõ'} → KHÔNG DÙNG "
                     f"(nguồn: {a['domain'] or manifest_values.source_label(a['source'])})")
            continue
        dong = (f"- {a['id']}: {a['w']}x{a['h']} ({a['ratio']}) {manifest_values.kind_label(a['kind']).upper()}"
                f"{' NGANG' if a['landscape'] else ''} | dùng: {'; '.join(manifest_values.use_labels(a['uses'])) or 'không'}"
                f" | nguồn: {a['domain'] or manifest_values.source_label(a['source'])}")
        if a.get("description"):
            dong += f" | ảnh là: {a['description'][:110]}"
        elif role.real_alt(a):               # LOW-285: alt anh tim web la cau truy van
            dong += f" | alt: {role.real_alt(a)[:70]}"
        if a.get("faces"):
            # Ten nguoi ma chinh tam anh mang theo (LOW-178): vai khai dung ten nay
            # la qua cong, ke ca khi chu bai khong nhac ten.
            ten = image_rules_dre.subject_names(a)
            dong += ((" | mặt người: tên theo vision/chú thích: " + " / ".join(f"\"{x}\"" for x in ten[:3])
                      + " — khai \"subject\" đúng tên NGƯỜI trong ảnh (không khai địa danh/cụm chữ)")
                     if ten else " | mặt người KHÔNG rõ ai: chỉ dùng nếu bài nêu đúng tên người này")
        if a["notes"]:
            dong += " | " + "; ".join(a["notes"])
        L.append(dong)
    if m.get("cover_suggestions"):
        L.append(f"Gợi ý bìa (không chart, không mặt, góc dưới-trái tối): {', '.join(m['cover_suggestions'])}")
    if m.get("stackable_pairs"):
        L.append("Cặp ảnh ngang ghép dọc được (cùng tone): " +
                 ", ".join("+".join(c) for c in m["stackable_pairs"]))
    import story_type
    L += story_type.line_brief(m)
    L.append("Ảnh CHỤP (trụ sở, nhà máy, người, sản phẩm) có biển hiệu, số nhà, logo trên tường "
             "VẪN LÀ ẢNH CHỤP — cắt dọc (landscape_crop) được. \"Có chữ\" cấm crop chỉ là chart, bảng, "
             "slide, banner, ảnh chụp màn hình có tiêu đề.")
    L.append("Mỗi ảnh đã được NHÌN (cột \"ảnh là\"). Ảnh ❌ tuyệt đối không dùng dù nhãn gì. "
             f"Bảng thu nhỏ: {m['workdir']}/{state_paths.CONTACT_SHEET_FILE}")
    L.append("")
    L.append(f"## Viết spec vào: {m['workdir']}/spec.json")
    khung = {
        "tier": "flagship" if m["flagship"] else "regular",
        "background_tone": "<dark | light — cả bộ một nền; dark: màn tối chữ trắng, light: màn sáng chữ đen; chọn theo ảnh, mặc định dark>",
        "cover": {"image": (m.get("cover_suggestions") or ["A?"])[0], "hook": "<một câu giật, ≤ 90 ký tự, có dấu>",
                  "category": "<" + " | ".join(carousel.CATEGORY_CALL_Y) + " | EARNINGS | M&A>",
                  "label": "<TÊN MODEL / HÃNG, VIẾT HOA>"},
        "slides": [
            {"image": "A?", "text": "<đoạn 1.\\n\\nđoạn 2 — tổng ≤ 240 ký tự>"},
            {"image": "A?", "quote": "<câu đắt nhất, DỊCH tiếng Việt, ≤ 150 ký tự>", "attrib": "<'via <tên báo>', hoặc tên người nói — không 'đọc/xem bài', không đuôi tên miền>"},
            {"stack": ["A?", "A?"], "text": "<hai ảnh ngang cùng tone xếp dọc>"},
            {"image": "A?", "subject": "<tên người trong bài>", "quote": "…", "attrib": "…"},
            {"image": "A?", "landscape_crop": True, "text": "<chỉ cho ảnh NGANG là người/sản phẩm không chữ>"},
        ],
    }
    L.append(json.dumps(khung, ensure_ascii=False, indent=1))
    L.append("Luật điền: mỗi slide MỘT ảnh, MỘT ý; `text` HOẶC `quote`+`attrib`; mỗi mã ảnh dùng đúng "
             "một lần; chart chỉ ở slide thân (script tự dán full bề ngang); ƯU TIÊN ảnh có CHỦ THỂ CHÍNH đặt vừa khung 4:5 "
             "(không phải tỉ lệ ảnh: ảnh NGANG chủ thể gọn cũng được, script tự cắt quanh chủ thể, không cần "
             "khai landscape_crop; KHÔNG cần đi tìm ảnh dọc/vuông), dùng MỘT ảnh — `stack` CHỈ khi hết ảnh như vậy; "
             "KHÔNG dùng ảnh gần như trống (logo nhỏ trên nền trơn), KHÔNG để chữ đè lên mặt/chủ thể "
             "(cổng chặn bắt đổi); ảnh NGANG mà chủ thể KHÔNG gọn trong khung 4:5 (bảng, banner chữ, cảnh rộng) "
             "thì `stack`; ảnh có mặt phải có `subject`; `background_tone` light khi đa số ảnh sáng/nền trắng (ảnh nổi hơn trên màn sáng), dark khi ảnh tối hoặc lẫn lộn. Tiếng Việt có dấu, không em-dash, "
             "câu quote phải DỊCH. `attrib` KHÔNG \"đọc bài\"/\"xem bài\" (thừa, slide chính là "
             "chỗ đọc rồi), KHÔNG đuôi tên miền (.com/.net/...) — nền tảng quét thành liên kết, "
             "giảm hiển thị cả bài; chỉ \"via <tên báo>\" hoặc tên người nói. Ảnh ⚠️ RỐI (chữ in "
             "sẵn, đồ hoạ nhồi, cắt ghép) chỉ dùng khi HẾT ảnh sạch — cổng chặn bắt đổi nếu còn "
             "ảnh sạch chưa dùng; ảnh ⭐ RỐI NHƯNG ĐỦ TỪ KHOÁ thì dùng thoải mái, hợp làm bìa. "
             "Bỏ các slide mẫu không dùng — khung trên chỉ minh hoạ cú pháp.")
    L.append("Khung kể: bìa HOOK (nghịch lý/con số) → chuyện gì vừa xảy ra → con số gây sốc → "
             "ý nghĩa thật → đối thủ/diễn biến → cái cần theo dõi (không chốt cụt).")
    L.append("")
    L.append("## Rồi chạy đúng MỘT lệnh:")
    L.append(f"cd {ROOT} && venv/bin/python dre_submit.py {m['draft_id']}")
    L.append("Script tự cắt/ghép ảnh theo spec, chạy cổng chặn, dựng slide, gửi album lên topic kèm nút "
             "duyệt, ghi bàn giao cho Miles. Báo [LOI] thì sửa đúng chỗ đó trong spec.json rồi chạy "
             "lại đúng lệnh này. KHÔNG curl, KHÔNG ls, KHÔNG mở từng ảnh, KHÔNG chạy carousel.py hay "
             "send_telegram.py tay.")
    return "\n".join(L)




def main() -> int:
    ap = argparse.ArgumentParser(description="Brief carousel cho Dre")
    ap.add_argument("draft_id")
    ap.add_argument("--lam-moi", action="store_true")
    ap.add_argument("--im", action="store_true")
    ap.add_argument("--khong-browser", action="store_true")
    ap.add_argument("--cho", type=int, default=300)
    a = ap.parse_args()
    m, wd, _ = cb.run(a.draft_id, a.lam_moi, a.khong_browser, a.cho,
                       sau_chuan_bi=route_missing_images.after_prepare)
    da_dung = cb._read_json(wd / state_paths.PREVIOUS_SUBMISSION_FILE)
    brief = write_brief(m, da_dung)
    (wd / "brief.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
