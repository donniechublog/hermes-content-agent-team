#!/usr/bin/env python3
"""dre_chuan_bi.py — BRIEF cho Dre (carousel). Phan co hoc nam o anh_chuan_bi.py
(engine dung chung); tep nay chi in ban chuan bi theo cach nhin cua Dre: bang
anh voi ma A1..An va nhan "dung duoc o dau" cho carousel, tu lieu, khung spec.

Dung:
    venv/bin/python dre_chuan_bi.py <draft_id>            # in brief (chay engine neu chua)
    venv/bin/python dre_chuan_bi.py <draft_id> --lam-moi  # bo cache, lam lai
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import anh_chuan_bi as cb                                    # noqa: E402

DRAFTS = cb.DRAFTS


def viet_brief(m: dict, da_dung: dict | None) -> str:
    import carousel
    import brief_chung
    L = brief_chung.dau(
        m, "DRE",
        f"Brand: {m['brand']} | draft: {m['draft_id']} | slide tối thiểu: {m['toi_thieu']}"
        + (" (FLAGSHIP: tin model của hãng frontier)" if m["flagship"] else "")
        + " | tối đa 10 | quote ≥ 2")
    L += brief_chung.khoi_lam_lai(
        da_dung,
        f"bìa {da_dung.get('bia')}, ảnh dùng {', '.join(da_dung.get('anh', []))}, "
        f"hook: “{da_dung.get('hook', '')}”. Lần này BÌA và HOOK phải khác, đổi ít "
        "nhất nửa số ảnh, đổi cách chia slide." if da_dung else "")
    L += brief_chung.khoi_tu_lieu(m, n_cau=99, n_doan=100000)
    L.append("")
    L.append("## Ảnh đã tải & xử lý xong — chỉ dùng MÃ ẢNH, không tải/crop/mở gì thêm")
    if not m["anh"]:
        L.append("KHÔNG CÓ ảnh thật nào dùng được. Không dựng hình giả. Kết thúc task bằng "
                 "một câu: \"Không tìm được ảnh thật cho tin này\" kèm link đã thử.")
    if m.get("khong_kite"):
        L.append("🛑 0 ẢNH THẬT dùng được và brand này CHƯA CÓ KITE. KHÔNG dựng hình giả. Kết thúc "
                 "task bằng một câu: \"Không có ảnh thật cho tin này, brand chưa có Kite\" — Ông Chủ "
                 "đã nhận nút Bỏ hẳn trên topic.")
        return "\n".join(L)
    if m.get("chuyen_kite"):
        L.append(f"🛑 TIN NÀY ĐÃ CHUYỂN KITE (task {m['chuyen_kite']}) vì 0 ảnh thật dùng được. "
                 "KHÔNG viết spec, KHÔNG dựng. Kết thúc task ngay bằng một câu: "
                 "\"Đã chuyển Kite vì không có ảnh thật\".")
        return "\n".join(L)
    so_dd = m.get("so_dung_duoc", len([a for a in m["anh"] if a["dung"]]))
    if m["anh"] and so_dd < m.get("toi_thieu", 5):
        L.append(f"⚠️ THIẾU ẢNH: chỉ {so_dd} ảnh dùng được, cần ≥ {m.get('toi_thieu', 5)} slide. "
                 "KHÔNG nhồi ảnh không liên quan cho đủ. Hoặc gộp ý để giảm số slide, hoặc "
                 "kết thúc task: \"Thiếu ảnh thật cho tin này\" kèm số ảnh có.")
    if m.get("so_mien") is not None:
        L.append(f"Ảnh dùng được lấy từ {len(m['so_mien'])} nguồn: {', '.join(m['so_mien']) or '—'}"
                 + (" — chỉ MỘT nguồn; bộ ≥4 slide nên có ảnh từ ≥2 nguồn, cân nhắc gộp ý."
                    if len(m['so_mien']) == 1 and so_dd >= 4 else ""))
    if m.get("chua_nhin"):
        L.append(f"⚠️ CHƯA AI NHÌN {', '.join(m['chua_nhin'])} (vision không chạy) — nhãn dưới chỉ là đo "
                 "số, có thể sai; mở bang_anh.png trước khi dùng.")
    if m.get("tin_xep_hang"):
        L.append(cb.dong_brief_xep_hang(m, "bìa ", "dre_nop"))
    for a in m["anh"]:
        if a.get("lien_quan") is False:
            L.append(f"- {a['ma']}: ❌ KHÔNG LIÊN QUAN — {a.get('mo_ta') or 'không rõ'} → KHÔNG DÙNG "
                     f"(nguồn: {a['mien'] or a['tu']})")
            continue
        dong = (f"- {a['ma']}: {a['w']}x{a['h']} ({a['ti_le']}) {a['loai'].upper()}"
                f"{' NGANG' if a['ngang'] else ''} | dùng: {'; '.join(a['dung']) or 'không'}"
                f" | nguồn: {a['mien'] or a['tu']}")
        if a.get("mo_ta"):
            dong += f" | ảnh là: {a['mo_ta'][:110]}"
        elif a.get("alt"):
            dong += f" | alt: {a['alt'][:70]}"
        if a["ghi_chu"]:
            dong += " | " + "; ".join(a["ghi_chu"])
        L.append(dong)
    if m.get("goi_y_bia"):
        L.append(f"Gợi ý bìa (không chart, không mặt, góc dưới-trái tối): {', '.join(m['goi_y_bia'])}")
    if m.get("cap_ghep"):
        L.append("Cặp ảnh ngang ghép dọc được (cùng tone): " +
                 ", ".join("+".join(c) for c in m["cap_ghep"]))
    L.append("Mỗi ảnh đã được NHÌN (cột \"ảnh là\"). Ảnh ❌ tuyệt đối không dùng dù nhãn gì. "
             f"Bảng thu nhỏ: {m['workdir']}/bang_anh.png")
    L.append("")
    L.append(f"## Viết spec vào: {m['workdir']}/spec.json")
    khung = {
        "tam_co": "flagship" if m["flagship"] else "thuong",
        "nen": "<toi | sang — cả bộ một nền; toi: màn tối chữ trắng, sang: màn sáng chữ đen; chọn theo ảnh, mặc định toi>",
        "cover": {"anh": (m.get("goi_y_bia") or ["A?"])[0], "hook": "<một câu giật, ≤ 90 ký tự, có dấu>",
                  "category": "<" + " | ".join(carousel.CATEGORY_GOI_Y) + " | EARNINGS | M&A>",
                  "label": "<TÊN MODEL / HÃNG, VIẾT HOA>"},
        "slides": [
            {"anh": "A?", "text": "<đoạn 1.\\n\\nđoạn 2 — tổng ≤ 240 ký tự>"},
            {"anh": "A?", "quote": "<câu đắt nhất, DỊCH tiếng Việt, ≤ 150 ký tự>", "attrib": "<Ai nói / Đọc bài “…” - nguồn>"},
            {"ghep": ["A?", "A?"], "text": "<hai ảnh ngang cùng tone xếp dọc>"},
            {"anh": "A?", "nhan_vat": "<tên người trong bài>", "quote": "…", "attrib": "…"},
            {"anh": "A?", "cat_ngang": True, "text": "<chỉ cho ảnh NGANG là người/sản phẩm không chữ>"},
        ],
    }
    L.append(json.dumps(khung, ensure_ascii=False, indent=1))
    L.append("Luật điền: mỗi slide MỘT ảnh, MỘT ý; `text` HOẶC `quote`+`attrib`; mỗi mã ảnh dùng đúng "
             "một lần; chart chỉ ở slide thân (script tự dán full bề ngang); ảnh NGANG phải `ghep` "
             "hoặc `cat_ngang`; ảnh có mặt phải có `nhan_vat`; `nen` sang khi đa số ảnh sáng/nền trắng (ảnh nổi hơn trên màn sáng), toi khi ảnh tối hoặc lẫn lộn. Tiếng Việt có dấu, không em-dash, "
             "câu quote phải DỊCH. Bỏ các slide mẫu không dùng — khung trên chỉ minh hoạ cú pháp.")
    L.append("Khung kể: bìa HOOK (nghịch lý/con số) → chuyện gì vừa xảy ra → con số gây sốc → "
             "ý nghĩa thật → đối thủ/diễn biến → cái cần theo dõi (không chốt cụt).")
    L.append("")
    L.append("## Rồi chạy đúng MỘT lệnh:")
    L.append(f"cd {ROOT} && venv/bin/python dre_nop.py {m['draft_id']}")
    L.append("Script tự cắt/ghép ảnh theo spec, chạy cổng chặn, dựng slide, gửi album lên topic kèm nút "
             "duyệt, ghi bàn giao cho Miles. Báo [LOI] thì sửa đúng chỗ đó trong spec.json rồi chạy "
             "lại đúng lệnh này. KHÔNG curl, KHÔNG ls, KHÔNG mở từng ảnh, KHÔNG chạy carousel.py hay "
             "gui_telegram.py tay.")
    return "\n".join(L)




def main() -> int:
    ap = argparse.ArgumentParser(description="Brief carousel cho Dre")
    ap.add_argument("draft_id")
    ap.add_argument("--lam-moi", action="store_true")
    ap.add_argument("--im", action="store_true")
    ap.add_argument("--khong-browser", action="store_true")
    ap.add_argument("--cho", type=int, default=300)
    a = ap.parse_args()
    m, wd, _ = cb.chay(a.draft_id, a.lam_moi, a.khong_browser, a.cho)
    da_dung = cb._doc_json(wd / "da_dung.json")
    brief = viet_brief(m, da_dung)
    (wd / "brief.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
