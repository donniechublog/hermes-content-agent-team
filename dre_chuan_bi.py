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
    L = []
    L.append(f"# DRE — ĐÃ CHUẨN BỊ XONG: {m['title']}")
    L.append(f"Brand: {m['brand']} | draft: {m['draft_id']} | "
             f"slide tối thiểu: {m['toi_thieu']}"
             + (" (FLAGSHIP: tin model của hãng frontier)" if m["flagship"] else "")
             + " | tối đa 10 | quote ≥ 2")
    L.append(f"Link gốc: {m['link']}" + (f" | via: {m['via']}" if m.get("via") else ""))
    if m.get("tieu_de_en"):
        L.append(f"Tiêu đề bài gốc: {m['tieu_de_en']}")
    if da_dung:
        L.append("")
        L.append(f"⚠️ LÀM LẠI — lần trước đã gửi lúc {da_dung.get('luc', '?')}: bìa {da_dung.get('bia')}, "
                 f"ảnh dùng {', '.join(da_dung.get('anh', []))}, hook: “{da_dung.get('hook', '')}”. "
                 "Lần này BÌA và HOOK phải khác, đổi ít nhất nửa số ảnh, đổi cách chia slide.")
    L.append("")
    L.append("## Tư liệu")
    if m.get("summary"):
        L.append(f"Tóm tắt (Finn): {m['summary']}")
    if m.get("source_note"):
        L.append(f"Nguồn (Finn): {m['source_note']}")
    tl = m.get("tu_lieu", {})
    if tl.get("cau_co_so"):
        L.append("Câu có số liệu (bóc từ bài, dùng làm text/quote):")
        for i, c in enumerate(tl["cau_co_so"], 1):
            L.append(f"  {i}. {c}")
    if tl.get("doan_dau"):
        L.append(f"Đoạn đầu bài gốc: {tl['doan_dau']}")
    if not tl.get("cau_co_so") and not tl.get("doan_dau"):
        L.append("(Không bóc được chữ từ nguồn — viết từ tóm tắt, KHÔNG bịa số.)")
    L.append("")
    L.append("## Ảnh đã tải & xử lý xong — chỉ dùng MÃ ẢNH, không tải/crop/mở gì thêm")
    if not m["anh"]:
        L.append("KHÔNG CÓ ảnh thật nào dùng được. Không dựng hình giả. Kết thúc task bằng "
                 "một câu: \"Không tìm được ảnh thật cho tin này\" kèm link đã thử.")
    for a in m["anh"]:
        dong = (f"- {a['ma']}: {a['w']}x{a['h']} ({a['ti_le']}) {a['loai'].upper()}"
                f"{' NGANG' if a['ngang'] else ''} | dùng: {'; '.join(a['dung'])}"
                f" | nguồn: {a['mien'] or a['tu']}")
        if a.get("alt"):
            dong += f" | alt: {a['alt'][:70]}"
        if a["ghi_chu"]:
            dong += " | " + "; ".join(a["ghi_chu"])
        L.append(dong)
    if m.get("goi_y_bia"):
        L.append(f"Gợi ý bìa (không chart, không mặt, góc dưới-trái tối): {', '.join(m['goi_y_bia'])}")
    if m.get("cap_ghep"):
        L.append("Cặp ảnh ngang ghép dọc được (cùng tone): " +
                 ", ".join("+".join(c) for c in m["cap_ghep"]))
    L.append(f"Nhìn tất cả ảnh trong MỘT tấm: {m['workdir']}/bang_anh.png (mở tối đa một lần, khi thật cần).")
    L.append("")
    L.append(f"## Viết spec vào: {m['workdir']}/spec.json")
    khung = {
        "tam_co": "flagship" if m["flagship"] else "thuong",
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
             "hoặc `cat_ngang`; ảnh có mặt phải có `nhan_vat`. Tiếng Việt có dấu, không em-dash, "
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
