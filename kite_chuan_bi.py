#!/usr/bin/env python3
"""kite_chuan_bi.py — BRIEF cho Kite (carousel.edu, render_edu.py).

Kite dung art vector goc, KHONG anh that — tru bieu do/bang co that trong bai
(kind `figure`, hoac bia co `image`). Phan co hoc (nguon, chu bai, chup bang/
figure, tu lieu) nam o anh_chuan_bi.py dung chung; tep nay in brief theo cach
nhin cua Kite: tu lieu de dien dat lai paper, danh sach HINH THAT la chart
(>= 800px) dung duoc cho `figure`, theme/hero goi y (khong trung bo gan day),
va khung spec 7 kind voi gioi han do dai tung truong (do theo co chu trong
render_edu.py de khong tran).

Do 04/09/2026 truoc khi doi: moi task Kite 32 tool call — ls 18, skill_view 13,
read_file 19, vision_analyze 13 (doc skill + reference + mo tung slide ra xem).

Dung:
    venv/bin/python kite_chuan_bi.py <draft_id>
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import anh_chuan_bi as cb                                    # noqa: E402
import card                                                  # noqa: E402


def handle_kenh(brand: str) -> str:
    """Handle hien thi cua brand: dcgr -> dcgr.tech (Ong Chu 05/09/2026: slide cuoi
    in 'Theo doi @dcgr' vi dung thang slug). Mot nguon: bang brand cua card.py."""
    return (getattr(card, 'THUONG_HIEU', {}).get(brand) or {}).get('handle') or brand


FIG_RONG_TOI_THIEU = 800


def hinh_that(m: dict) -> list:
    """Hinh THAT Kite duoc dung: chart/bang VA anh chup, dieu kien: engine da nhin
    va khong danh dau KHONG LIEN QUAN, >= 800px, khong phai mat nguoi khong ro
    ai. Ong Chu 05/09/2026: "Dre tim duoc 1-2 anh chat luong thi Kite cung nen
    dua vao slide, chu khong chi text & card don dieu". Truoc do chi lay chart
    -> anh chup bi bo, con chart khong lien quan (Fear&Greed) van lot."""
    ra = []
    for a in m["anh"]:
        if a["w"] < FIG_RONG_TOI_THIEU or a.get("lien_quan") is False:
            continue
        if any("KHÔNG RÕ AI" in g for g in a.get("ghi_chu", [])):
            continue
        ra.append(a)
    return ra


def goi_y_tone(title: str) -> tuple:
    """(theme, hero, gan_day) — chon cai chua dung gan day, xoay theo tieu de."""
    import render_edu
    gan = render_edu._theme_gan_day(4)
    try:
        theme, hero = render_edu.chon_theme_tu_dong({"folio": title}, False)
    except SystemExit:
        theme, hero = "orbit", "orbit"
    return theme, hero, gan


def viet_brief(m: dict, da_dung: dict | None) -> str:
    theme, hero, gan = goi_y_tone(m["title"])
    import brief_chung
    L = brief_chung.dau(
        m, "KITE",
        f"Brand: {m['brand']} | draft: {m['draft_id']} | 6..10 slide, slide 1 là cover | "
        "art vector gốc, KHÔNG ảnh thật trừ hình thật liệt kê dưới")
    L += brief_chung.khoi_lam_lai(
        da_dung, f"theme={da_dung.get('theme')} hero={da_dung.get('hero')}, hook "
                 f"“{da_dung.get('hook', '')}”. Lần này BẮT BUỘC đổi theme hoặc hero, "
                 "và đổi hook/cách chia slide." if da_dung else "")
    L += brief_chung.khoi_tu_lieu(
        m, tieu_de="## Tư liệu (diễn đạt lại cho tường minh, KHÔNG bịa số, KHÔNG bịa quote)",
        n_cau=25, n_doan=1500,
        dong_thieu="(Không bóc được chữ từ nguồn — chỉ dùng tóm tắt, KHÔNG bịa.)")
    L += ["", "## Hình thật dùng được cho `figure` / bìa `image` (đã nhìn, ≥ 800px)"]
    ht = hinh_that(m)
    if not ht:
        L.append("Không có hình thật nào liên quan — dùng art vector cho cả bộ (bình thường với paper trắng).")
    else:
        nhin = [a for a in ht if a.get("lien_quan") is True]
        if nhin:
            L.append(f"CÓ {len(nhin)} hình thật ĐÃ NHÌN và liên quan → BẮT BUỘC dùng ít nhất một: "
                     "`figure` cho chart/bảng, bìa `image` hoặc `figure` cho ảnh chụp. "
                     "Bộ toàn text & card khi có ảnh thật là thiếu.")
        else:
            # Vision tat/thieu khoa -> moi anh lien_quan=None. Khong duoc ep.
            L.append(f"Có {len(ht)} hình đủ khổ nhưng ⚠️ CHƯA AI NHÌN (vision không chạy) — chưa biết "
                     "chúng có đúng bài không. Dùng thì tự kiểm bằng bang_anh.png, không bắt buộc.")
    for a in ht:
        kieu = ("BIỂU ĐỒ/BẢNG" if a["loai"] == "chart" else "ẢNH CHỤP") + \
               ("" if a.get("lien_quan") is True else " ⚠️CHƯA NHÌN")
        L.append(f"- {a['ma']}: {kieu} {a['w']}x{a['h']} ({a['ti_le']}) | nguồn: {a['mien'] or a['tu']}"
                 + (f" | ảnh là: {a['mo_ta'][:90]}" if a.get("mo_ta") else (f" | alt: {a['alt'][:70]}" if a.get("alt") else ""))
                 + (" | có mặt người, khai đúng tên trong caption" if a.get("mat") else ""))
    rac = [a["ma"] for a in m["anh"] if a.get("lien_quan") is False]
    if rac:
        L.append(f"Không dùng (engine đánh dấu không liên quan): {', '.join(rac)}")
    L.append(f"Nhìn tất cả trong MỘT tấm: {m['workdir']}/bang_anh.png (chỉ khi cần).")
    L += ["", "## Tone cho bộ này (mỗi bộ một tone, không trùng bộ gần đây)",
          f"Gợi ý: theme={theme}, hero={hero}. Gần đây đã dùng: {gan or 'chưa có'}.",
          "theme: orbit (agent/hệ thống) | ember (hiệu năng/cảnh báo) | moss (dữ liệu mở/tăng trưởng) | "
          "ink (benchmark/học thuật) | rose (sinh ảnh/sáng tạo). hero: orbit (phân việc) | grid (bảng số) | "
          "wave (xu hướng) | rings (độ chính xác) | graph (quan hệ)."]
    L += ["", f"## Viết spec vào: {m['workdir']}/spec.json  (6..10 slide; mỗi slide MỘT ý; tiếng Việt có dấu)"]
    khung = {
        "theme": theme, "hero": hero,
        "section": "<CHUYÊN MỤC ≤ 24 ký tự, vd RESEARCH · ARXIV>",
        "folio": "<TÊN NGẮN CỦA BÀI ≤ 24 ký tự>",
        "slides": [
            {"kind": "cover", "eyebrow": "<CHUYÊN MỤC · DEEP DIVE, ≤ 28>", "title": "<hook ≤ 60 ký tự>",
             "accent": "<cụm trong title cần nhấn>", "standfirst": "<1 câu ≤ 200 ký tự>",
             "byline": [handle_kenh(m["brand"]), "Phân tích", "5 phút đọc"],
             "image": "<mã hình thật A? nếu bìa dùng ảnh, hoặc bỏ>", "caption": "<'… · via <ai>' bắt buộc khi có image>"},
            {"kind": "statement", "eyebrow": "BỐI CẢNH", "title": "<≤ 60>", "accent": "<cụm nhấn>",
             "standfirst": "<≤ 220>", "cards": [{"num": "01", "text": "<≤ 90>"}, {"num": "02", "text": "<≤ 90>"}]},
            {"kind": "steps", "eyebrow": "CÁCH VẬN HÀNH", "title": "<≤ 60>",
             "steps": [{"title": "<≤ 30>", "desc": "<≤ 80>"}, {"title": "…", "desc": "…"}, {"title": "…", "desc": "…"}]},
            {"kind": "figure", "eyebrow": "SỐ LIỆU", "title": "<≤ 60, tối đa 2 dòng>", "accent": "<cụm>",
             "image": "<mã hình thật A?>", "caption": "<Biểu đồ trong bài · via <ai>>", "standfirst": "<≤ 200>"},
            {"kind": "bars", "eyebrow": "SỐ LIỆU", "title": "<≤ 60>", "accent": "<cụm>",
             "bars": [{"label": "<≤ 28>", "value": "<số THẬT trong bài, viết dạng số>", "text": "<cách ghi, vd 2,75 USD>"},
                      {"label": "<≤ 28>", "value": "<số>", "text": "<…>", "nhan": True}],
             "caption": "<Số trong bài · via <ai>>", "standfirst": "<≤ 160, tuỳ chọn>"},
            {"kind": "loop", "eyebrow": "CƠ CHẾ", "title": "<≤ 60>", "accent": "<cụm>",
             "chips": ["<≤ 3 từ>", "<≤ 3 từ>", "<≤ 3 từ>"], "standfirst": "<≤ 220>", "callout": "<≤ 110>"},
            {"kind": "cta", "eyebrow": "ÁP DỤNG", "title": "<≤ 60>", "checks": ["<≤ 70>", "<≤ 70>", "<≤ 70>"],
             "readmore": {"label": "ĐỌC THÊM", "text": "<“Tên bài” - tác giả/nơi đăng, ≤ 90>"},
             "follow": f"Theo dõi @{handle_kenh(m['brand'])}"},
        ],
    }
    L.append(json.dumps(khung, ensure_ascii=False, indent=1))
    L.append("Nhịp feature: bìa hook → bối cảnh/vấn đề → cách vận hành (steps) → số liệu (figure nếu có hình thật, "
             "không thì bars từ 2..6 số THẬT trong bài, không có số thì bỏ) → cơ chế/hệ quả (loop) → áp dụng + CTA. "
             "Ý nào hình nói nhanh hơn chữ thì dùng hình (steps/loop/bars), chữ thuần là đường cuối. Bỏ `figure` "
             "nếu không có hình thật; thêm `statement` khi cần đủ 6. Dẫn nguồn ghi 'via', không ghi 'nguồn'. Cấm logo hãng, số bịa, "
             "quote bịa, ảnh AI. Không em-dash.")
    L += ["", "## Rồi chạy đúng MỘT lệnh:",
          f"cd {ROOT} && venv/bin/python kite_nop.py {m['draft_id']}",
          "Script tự kiểm spec, dựng bằng render_edu.py (Chromium), gửi album lên topic kèm nút duyệt, ghi bàn "
          "giao cho Miles. Báo [LOI] thì sửa đúng chỗ đó trong spec.json rồi chạy lại. KHÔNG mở từng slide ra "
          "xem, KHÔNG chạy render_edu.py/gui_telegram.py tay, KHÔNG sinh agent con, KHÔNG gửi lại."]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Brief carousel.edu cho Kite")
    ap.add_argument("draft_id")
    ap.add_argument("--lam-moi", action="store_true")
    ap.add_argument("--im", action="store_true")
    ap.add_argument("--khong-browser", action="store_true")
    ap.add_argument("--cho", type=int, default=300)
    a = ap.parse_args()
    m, wd, _ = cb.chay(a.draft_id, a.lam_moi, a.khong_browser, a.cho)
    brief = viet_brief(m, cb._doc_json(wd / "da_dung.json"))
    (wd / "brief.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
