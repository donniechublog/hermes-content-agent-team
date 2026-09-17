#!/usr/bin/env python3
"""ethan_prepare.py — BRIEF cho Ethan (designer, hero card `card.py`).

Phan co hoc (nguon, anh, do, cat, tu lieu) nam o image_prepare.py — dung chung
voi Dre. Tep nay chi in ban chuan bi theo cach nhin cua HERO CARD: mot tam anh
lam nen, mot cau hook de len (kieu `quote`, mac dinh) hoac mot tieu de + kicker
(kieu `tran`). Nhan "dung duoc o dau" khac Dre vi card.py khoa kho 4:5:

  - anh chup ti le <= 1.6 (card.kiem_anh_thap: trai full be ngang 1200 phai cao
    >= 750px): dung mot minh duoc;
  - anh NGANG hon 1.6, hoac CHART/bang: card.py CHAN mot minh -> phai ghep doc
    voi mot anh ngang cung tone (`anh2`), khong co cap thi khong dung;
  - co mat nguoi: phai khai `nhan_vat` (nguoi duoc nhac trong bai).

Dung:
    venv/bin/python ethan_prepare.py <draft_id>            # in brief
    venv/bin/python ethan_prepare.py <draft_id> --lam-moi  # bo cache, lam lai
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import image_prepare as cb                                    # noqa: E402
import route_missing_images                                       # noqa: E402
import role                                                   # noqa: E402

# 1200/750 — nguong kiem_anh_thap cua card.py o kho 4:5. Song o ban dang ky vai
# vi engine anh cung phai biet no: no la thu quyet dinh mot tam co lam nen hero
# duoc khong, tuc co dang di tim tiep khong (LOW-12).
RATIO_HERO_MAX = role.ROLE["ethan"].ti_le_don_max
TAGLINE_CALL_Y = ["MODEL RELEASE", "MODEL UPDATE", "FUNDING", "M&A", "EARNINGS", "ROBOTICS",
                 "CYBERSECURITY", "APPS", "OPEN SOURCE", "RESEARCH", "POLICY", "INFRA", "IN BRIEF"]


def label_ethan(a: dict) -> tuple:
    """(dung, ghi_chu) cho mot anh theo luat cua card.py."""
    dung, ghi = [], []
    r = a["ratio"]
    if a.get("ranking"):
        xh = a["ranking"]
        dung.append("✅ ẢNH XẾP HẠNG — ẢNH CHÍNH BẮT BUỘC của tin này, dùng MỘT MÌNH được "
                    f"(bảng {xh.get('site')} · {xh.get('board')}, {xh.get('model')}"
                    + (f" #{xh.get('rank')}" if xh.get('rank') else "") + ", đã khoanh hàng model)")
        if r > RATIO_HERO_MAX:
            ghi.append(f"bảng quá ngang ({r}): thêm \"anh2\" ngang cùng tone để ghép dọc")
        return dung, ghi
    if a["kind"] == "chart":
        dung.append("CHỈ ghép dọc (anh2) với một ảnh ngang cùng tone, chart một mình bị chặn")
    elif r > RATIO_HERO_MAX:
        dung.append("ảnh NGANG quá 1.6: CHỈ ghép dọc (anh2) với ảnh ngang cùng tone")
    else:
        dung.append("nền hero (một mình)")
        if a.get("bottom_left_brightness", 0) >= 150:
            ghi.append("nửa dưới sáng, câu hook đè lên hơi nhạt")
    if a.get("faces"):
        ghi.append(f"CÓ {a['faces']} MẶT NGƯỜI → chỉ dùng khi khai \"nhan_vat\": \"<tên người trong bài>\"")
    if a.get("short_side", 0) < 1000:
        ghi.append(f"cạnh ngắn {a['short_side']}px, phóng lên hơi mềm")
    if a.get("commons"):
        ghi.append("ảnh CHUNG của hãng từ Wikimedia Commons (trụ sở/sản phẩm), không phải ảnh của tin")
    if a.get("brand_match"):
        # Nhãn theo ĐÚNG LOẠI tư liệu (chân dung có tên / thẻ logo / bảng xếp
        # hạng / ảnh cơ sở), một bản dùng chung với brief của Dre. Bản cũ ở đây
        # dán một câu "trụ sở/campus/biển hiệu" cho MỌI loại, nên chân dung
        # founder tới tay Ethan không có cái tên để khai `nhan_vat` — mà cổng
        # `check_subject_named` chặn mặt người không khai tên, tức Ethan buộc phải bỏ
        # ảnh founder (Ông Chủ 10/09/2026).
        import image_brand
        ghi.append(image_brand.label_by_type(a["brand_match"]))
    if a.get("concept"):
        kn = a["concept"]
        ghi.append(f"🧭 ẢNH KHÁI NIỆM (từ khoá \"{kn.get('keyword')}\"" + (f": {kn['reason']}" if kn.get("reason") else "")
                   + ") từ Wikimedia Commons — KHÔNG phải ảnh của tin; làm nền hero khi tin không có ảnh riêng tốt hơn")
    return dung, ghi


def stackable_pairs_hero(m: dict) -> list:
    """Cap anh ngang ghep doc duoc cho card.py: cung tone (da tinh trong engine)
    va ti le sau ghep <= 1.6."""
    anh = {a["id"]: a for a in m["images"]}
    ra = []
    for x, y in m.get("stackable_pairs", []):
        rc = 1 / (1 / anh[x]["ratio"] + 1 / anh[y]["ratio"])
        if rc <= RATIO_HERO_MAX:
            ra.append([x, y])
    return ra


def write_brief(m: dict, da_dung: dict | None) -> str:
    import brief_common
    L = brief_common.mark(
        m, "ETHAN",
        f"Brand: {m['brand']} | draft: {m['draft_id']} | kiểu mặc định: quote (thẻ HOOK 4:5)")
    L += brief_common.block_redo(
        da_dung, f"ảnh {da_dung.get('anh')}, hook “{da_dung.get('hook', '')}”. "
                 "Lần này ẢNH và HOOK phải khác." if da_dung else "")
    L += brief_common.block_material(m, nhan="Finn/Vera", n_cau=15, n_doan=800)
    L += ["", "## Ảnh đã tải & xử lý — chỉ dùng MÃ ẢNH, không tải/crop/mở gì thêm"]
    if not m["images"]:
        L.append("KHÔNG CÓ ảnh thật nào dùng được. Không dựng thẻ, không vẽ. Kết thúc task bằng "
                 "một câu: \"Không tìm được ảnh thật cho tin này\" kèm link đã thử.")
    # Nhan cua vision (06/09/2026): truoc day brief cua Ethan khong in co
    # `relevant` lan mo ta, nen vai chon phai anh ❌ roi bi ethan_submit doi lai —
    # mat mot vong ma vai khong hieu vi sao. Dre da in day du tu truoc.
    if m.get("not_yet_seen"):
        L.append(f"⚠️ CHƯA AI NHÌN {', '.join(m['not_yet_seen'])} (vision không chạy) — nhãn dưới chỉ là đo "
                 "số, có thể sai; mở bang_anh.png trước khi dùng.")
    goi_y = []
    if m.get("is_ranking_story"):
        L.append(cb.ranking_brief_line(m, "", "ethan_submit"))
    for a in m["images"]:
        if a.get("relevant") is False:
            L.append(f"- {a['id']}: ❌ KHÔNG LIÊN QUAN — {a.get('description') or 'không rõ'} → KHÔNG DÙNG "
                     f"(nguồn: {a['domain'] or a['source']})")
            continue
        dung, ghi = label_ethan(a)
        if dung[0].startswith("nền hero") and not a.get("faces"):
            goi_y.append((a.get("bottom_left_brightness", 0), -a.get("short_side", 0), a["id"]))
        dong = (f"- {a['id']}: {a['w']}x{a['h']} ({a['ratio']}) {a['kind'].upper()} | {'; '.join(dung)}"
                f" | nguồn: {a['domain'] or a['source']}")
        if a.get("description"):
            dong += f" | ảnh là: {a['description'][:110]}"
        elif a.get("alt"):
            dong += f" | alt: {a['alt'][:70]}"
        if ghi:
            dong += " | " + "; ".join(ghi)
        L.append(dong)
    goi_y.sort()
    if goi_y:
        L.append("Gợi ý nền hero (không chart, không mặt, nửa dưới tối trước): " + ", ".join(g[2] for g in goi_y[:3]))
    cap = stackable_pairs_hero(m)
    import story_type
    L += story_type.line_brief(m)
    if cap:
        L.append("Cặp ghép dọc được (cùng tone, dùng \"anh\"+\"anh2\"): " + ", ".join("+".join(c) for c in cap))
    L.append(f"Nhìn tất cả ảnh trong MỘT tấm: {m['workdir']}/bang_anh.png (mở tối đa một lần, khi thật cần).")
    L += ["", f"## Viết spec vào: {m['workdir']}/spec.json"]
    khung = {
        "anh": (goi_y[0][2] if goi_y else "A?"),
        "kieu": "quote",
        "hook": "<một câu ĐẬP VÀO MẮT trong 3 giây, có dấu, ≤ 120 ký tự: tiêu đề/góc giật có CON SỐ, hoặc lời có thật>",
        "tagline": "<" + " | ".join(TAGLINE_CALL_Y) + ">",
        "attrib": "<'via <báo>' nếu hook là câu bạn soạn; 'Phát biểu của <tên>, <chức/hãng>' CHỈ khi là lời có thật>",
        "anh2": "<mã ảnh ngang thứ hai để ghép dọc, hoặc bỏ trường này>",
        "nhan_vat": "<tên người trong ảnh nếu ảnh có mặt, hoặc bỏ trường này>",
    }
    L.append(json.dumps(khung, ensure_ascii=False, indent=1))
    L.append("Kiểu \"tran\" (đổi không khí, hiếm dùng): {\"anh\": \"A?\", \"kieu\": \"tran\", \"title\": \"<MỘT câu "
             "hoàn chỉnh bao quát tin, có số nếu tin có số>\", \"kicker\": \"<≤ 2 từ tiếng Anh: BREAKING, MODEL "
             "RELEASE, FUNDING...>\"}")
    L.append("Luật: hook là MỘT câu, tiếng Việt có dấu, không em-dash, không gán câu tự soạn thành lời một người; "
             "tên hãng trong câu tự tô màu. Chart/ảnh ngang >1.6 phải có anh2. Ảnh có mặt phải có nhan_vat.")
    L += ["", "## Rồi chạy đúng MỘT lệnh:",
          f"cd {ROOT} && venv/bin/python ethan_submit.py {m['draft_id']}",
          "Script tự ghép/cắt, chạy mọi cổng chặn của card.py, dựng thẻ, gửi lên topic kèm nút duyệt, ghi bàn "
          "giao cho Miles. Báo [LOI] thì sửa đúng chỗ đó trong spec.json rồi chạy lại đúng lệnh này. KHÔNG "
          "curl, KHÔNG ls, KHÔNG mở từng ảnh, KHÔNG chạy card.py hay send_telegram.py tay."]
    return "\n".join(L)


def main() -> int:
    ap = argparse.ArgumentParser(description="Brief hero card cho Ethan")
    ap.add_argument("draft_id")
    ap.add_argument("--lam-moi", action="store_true")
    ap.add_argument("--im", action="store_true")
    ap.add_argument("--khong-browser", action="store_true")
    ap.add_argument("--cho", type=int, default=300)
    a = ap.parse_args()
    m, wd, _ = cb.run(a.draft_id, a.lam_moi, a.khong_browser, a.cho,
                       sau_chuan_bi=route_missing_images.after_prepare)
    brief = write_brief(m, cb._read_json(wd / "da_dung.json"))
    (wd / "brief.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
