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
import vai as vai_mod                                        # noqa: E402
import route_thieu_anh                                       # noqa: E402


def handle_kenh(brand: str) -> str:
    """Handle hien thi cua brand KHONG co "@" (slide cuoi tu ghep): dcgr ->
    dcgr.tech (Ong Chu 05/09/2026: slide cuoi in 'Theo doi @dcgr' vi dung thang
    slug). Mot ban o env_load.handle_kenh (ADF-r2-9) — truoc day ban nay khong
    doi 'blog' -> 'donniechublog' nhu bob_nop."""
    import env_load
    return env_load.handle_kenh(brand, co_a_cong=False)


FIG_RONG_TOI_THIEU = 800
# Tran hinh BAT BUOC: bo chi duoc 6..10 slide, tru bia va cta con 8. Ep het khi
# engine tim duoc 9 tam la hai cong da nhau, vai khong co duong nao nop duoc.
TOI_DA_EP_HINH = 6


def chuyen_tu_vai(m: dict) -> str:
    """Tên vai đã CHUYỂN tin này sang Kite vì thiếu ảnh thật ("Dre"/"Ethan"), hoặc "".

    Mọi đường vào Kite đều là đường THIẾU ẢNH: `duyet_bai` chỉ gắn nút "Gửi Kite"
    ở hai chỗ báo thiếu ảnh, và `anh_chuan_bi._route_thieu_anh` tự chuyển khi 0
    ảnh. Cả hai đều đi qua `tao_task_kite`, nơi ghi `chuyen_tu` vào img.json —
    xong.json thì KHÔNG có (nút của Ông Chủ bấm sau khi engine đã ghi xong).
    """
    im = cb._doc_json(cb.DRAFTS / (str(m.get("draft_id", "")) + ".img.json"), {}) or {}
    tu = im.get("chuyen_tu") or ""
    if tu:
        return vai_mod.ten_hien(tu)      # ban dang ky: vai.py (audit A4)
    return "vai ảnh" if (m.get("chuyen_kite") or im.get("chuyen_kite")) else ""


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


def hinh_mo_dau(ht: list) -> dict | None:
    """Hinh MO DAU cua paper trong danh sach hinh that (Figure 1, hoac hinh paper
    dau tien boc duoc), hoac None. Do la tam dung lam hero cua bia."""
    paper = [a for a in ht if a.get("paper_hinh")]
    return paper[0] if paper else None


def hinh_hero(m: dict) -> dict | None:
    """Tam duoc chon lam HERO cua bia, hoac None khi bia ve vector.

    Ong Chu 10/09/2026: *"kite van dung vector lam hero, chua su dung anh"*. Ban
    truoc (08/09) chi chi dinh hero khi anh co `paper_hinh`, tuc **chi bai
    arxiv**: moi tin con lai — anh chup, tru so, co nuoc, bieu do — brief noi
    "bia `image` HOAC `figure`" (tuy chon) va cong chi doi "dung it nhat mot anh
    o dau do", nen dat het vao `figure` than roi ve hero vector la HOP LE.

    Thu tu theo LUAT_ANH: hinh paper (§1.4 "Figure 1 la hero") -> anh rieng cua
    tin -> anh thuong hieu (§1.2d) -> anh khai niem (§1.2c); hai loai bu xep sau
    moi anh rieng cua tin, dung nhu tai lieu ghi.

    Chi anh DA DUOC NHIN, tru hinh paper (boc thang tu PDF nen khong the la
    quang cao): vision tat thi moi anh co `lien_quan=None`, ep luc do la day
    banner len bia — cung bai hoc voi `hinh_phai_dung`.

    MOT nguon cho ca brief lan cong chan (`kite_nop`).
    """
    ut = [a for a in hinh_that(m)
          if a.get("lien_quan") is True or a.get("paper_hinh")]
    if not ut:
        return None
    rieng = [a for a in ut if not (a.get("khai_niem") or a.get("thuong_hieu"))]
    xep = ([a for a in rieng if a.get("paper_hinh")] + rieng
           + [a for a in ut if a.get("thuong_hieu")]
           + [a for a in ut if a.get("khai_niem")])
    # Tin CHUYEN sang Kite vi thieu anh: `kite_nop` doi hinh that nam o slide
    # THAN (Ong Chu 09/09), ma cung mot anh khong len duoc hai slide
    # (`luat_anh.kiem_trung`). Tam nao bi than giu doc quyen thi bo, LUI xuong
    # ung vien ke tiep — anh khai niem khong nam trong `hinh_phai_dung` (§1.2c
    # cam no o than) nen no van nhan duoc bia khi anh rieng bi than giu. Het
    # ung vien thi than thang va bia ve vector: ep ca hai la hai cong da nhau,
    # vai khong co duong nao nop duoc.
    ep = hinh_phai_dung(m)
    for chon in xep:
        if not ep or [ma for ma in ep if ma != chon["ma"]]:
            return chon
    return None


def _hero_la_gi(h: dict) -> tuple:
    """(tam nay LA GI, caption goi y) cho dong ⭐ HERO."""
    if h.get("paper_hinh"):
        return (f"{h['paper_hinh']} — hình mở đầu của chính paper, tấm nói nhiều nhất về bài",
                f"{h['paper_hinh']} trong paper · via <ai>")
    if h.get("khai_niem"):
        tk = h["khai_niem"].get("tu_khoa", "")
        # §1.2c: anh khai niem CHI dung o bia/hero, khong vao slide than — nen
        # khi no la hero thi noi thang, keo vai lai dat xuong `figure`.
        return (f"ảnh khái niệm ({tk}) — loại này CHỈ được dùng ở bìa, không vào slide thân",
                f"{tk} · via Wikimedia Commons")
    if h.get("thuong_hieu"):
        return (f"ảnh thương hiệu của {h['thuong_hieu'].get('hang')} (xem nhãn ở trên để "
                "chú thích đúng loại: cơ sở · chân dung · bảng xếp hạng · thẻ logo)",
                "<chú thích đúng loại tấm> · via <ai>")
    return ("biểu đồ/bảng của bài" if h["loai"] == "chart" else "ảnh chụp của bài",
            "<chú thích ngắn> · via <ai>")


def dong_hero(m: dict) -> list:
    """Dong chi cho Kite dat tam nao len bia, hoac [] khi bia ve vector."""
    h = hinh_hero(m)
    if not h:
        return []
    la_gi, cap = _hero_la_gi(h)
    return ["", f"⭐ HERO: {h['ma']} là {la_gi}. Đặt `\"image\": \"{h['ma']}\"` vào SLIDE 1 "
                f"(cover) kèm `\"caption\": \"{cap}\"`; lúc đó bìa lấy chính hình đó làm hero, "
                "KHÔNG vẽ hero art — `kite_nop.py` chặn bìa vector khi có hình thật dùng được. "
                "Chỉ bỏ qua khi hình sai bài (xem bang_anh.png) — lúc đó nói rõ một câu vì sao. "
                "Hình còn lại để cho `figure`."]


def hinh_phai_dung(m: dict) -> list:
    """Mã hình BẮT BUỘC vào bộ, khi tin được CHUYỂN sang Kite vì thiếu ảnh thật.

    Ông Chủ 09/09/2026: *"sau khi tìm được hình tốt mà vẫn ko đủ để làm và pass
    qua cho Kite thì Kite cũng phải dùng những hình đó trong body"*. Rỗng khi
    tin không phải hàng chuyển sang, hoặc chưa ai nhìn ảnh (vision tắt thì ép là
    đẩy quảng cáo/widget lên slide — xem chú thích cùng loại ở kite_nop).

    KHÔNG ép **ảnh khái niệm** (§1.2c: "chỉ bìa/hero, không vào slide thân").
    Cổng này đòi mỗi mã một slide `figure` *và* ít nhất một tấm ở thân, nên để
    ảnh khái niệm lọt vào đây là ÉP nó xuống đúng chỗ luật cấm — đo 10/09/2026:
    tin chuyển sang mà chỉ có một tấm cờ nước thì đường nộp duy nhất là đặt cờ
    vào `figure` thân. Nó rơi khỏi danh sách này và về bìa qua `hinh_hero`.
    Ảnh thương hiệu thì Ở LẠI: §1.2d cho nó vào thân (ảnh thật của chính hãng
    trong tin).

    MỘT nguồn cho cả brief lẫn cổng chặn: hai bản đếm khác nhau là brief bảo
    dùng 3 mã còn cổng đòi 4.
    """
    if not chuyen_tu_vai(m):
        return []
    return [a["ma"] for a in hinh_that(m)
            if a.get("lien_quan") is True and not a.get("khai_niem")][:TOI_DA_EP_HINH]


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
    # Mã bắt buộc, bỏ mã đã lên bìa: khung in sẵn MỘT `figure` cho mỗi mã còn
    # lại, để vai khỏi phải tự suy ra "à, ba hình thì ba slide". Chú thích này có
    # từ đầu nhưng code KHÔNG bỏ mã của bìa: in cùng một mã ở cả cover lẫn
    # `figure` là `luat_anh.kiem_trung` chặn — khung mẫu đẩy vai vào cổng.
    hero_anh = hinh_hero(m)
    ep_khung = [ma for ma in hinh_phai_dung(m)
                if not (hero_anh and ma == hero_anh["ma"])]
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
        tu_vai, ep = chuyen_tu_vai(m), hinh_phai_dung(m)
        if ep:
            # Ong Chu 09/09/2026: "sau khi tim duoc hinh tot ma van ko du de lam
            # va pass qua cho Kite thi Kite cung phai dung nhung hinh do trong
            # body". Truoc do brief chi doi "it nhat mot", ma mot tam thi Kite
            # de len bia roi ve vector ca body — dung cai Ong Chu che.
            L.append(f"🔁 TIN NÀY CHUYỂN TỪ {tu_vai} SANG KITE VÌ THIẾU ẢNH THẬT — nhưng "
                     f"{len(ep)} tấm engine tìm được ({', '.join(ep)}) KHÔNG BỊ BỎ ĐI. "
                     "Luật cho bộ này:")
            L.append(f"- **Cả {len(ep)} mã đều phải xuất hiện** trong spec — thiếu tấm nào "
                     "`kite_nop.py` chặn, kèm tên mã.")
            L.append("- **Phải có hình ở BODY**, không chỉ ở bìa: mỗi tấm một slide `figure` "
                     "(`\"image\": \"<mã>\"` + `\"caption\": \"… · via <ai>\"`). Đặt hết lên bìa "
                     "rồi vẽ vector cả thân là đúng cái lỗi khiến tin phải chuyển sang đây.")
            L.append("- Vector chỉ để lấp phần CÒN THIẾU (steps/loop/bars/statement), không thay "
                     "cho bằng chứng thật đã có.")
        elif nhin:
            L.append(f"CÓ {len(nhin)} hình thật ĐÃ NHÌN và liên quan → BẮT BUỘC dùng ít nhất một: "
                     "`figure` cho chart/bảng, bìa `image` hoặc `figure` cho ảnh chụp"
                     + (" — và một tấm phải lên BÌA làm hero, xem ⭐ dưới. "
                        if hero_anh else ". ")
                     + "Bộ toàn text & card khi có ảnh thật là thiếu.")
        else:
            # Vision tat/thieu khoa -> moi anh lien_quan=None. Khong duoc ep.
            L.append(f"Có {len(ht)} hình đủ khổ nhưng ⚠️ CHƯA AI NHÌN (vision không chạy) — chưa biết "
                     "chúng có đúng bài không. Dùng thì tự kiểm bằng bang_anh.png, không bắt buộc.")
    for a in ht:
        kieu = ("BIỂU ĐỒ/BẢNG" if a["loai"] == "chart" else "ẢNH CHỤP") + \
               ("" if a.get("lien_quan") is True else " ⚠️CHƯA NHÌN")
        th = a.get("thuong_hieu") or {}
        # Anh THUONG HIEU: noi ro no LA GI, vi caption phai khac nhau han. Mot the
        # logo bi chu thich "anh tru so" la sai su that (09/09/2026).
        nhan_th = {"anh": f"🏢 ảnh cơ sở của {th.get('hang')} (KHÔNG phải ảnh của sự việc)",
                   "nguoi": f"👤 chân dung {th.get('vai', 'lãnh đạo')} {th.get('hang')}: "
                            f"{th.get('nguoi')} — caption phải nêu đúng tên này, và chỉ dùng khi "
                            "bài có nhắc người đó",
                   "logo": f"🔖 THẺ LOGO {th.get('hang')} (logo chính thức trên nền trơn) — hợp làm "
                           "bìa, đừng chú thích như ảnh chụp",
                   "xep_hang": f"📊 bảng {th.get('site')} · {th.get('bang')} có {th.get('hang')} — "
                               "KHÔNG phải bảng của tin này, caption ghi rõ nguồn + tên bảng",
                   }.get(th.get("loai"), "")
        # Anh KHAI NIEM: no la anh chup that nen di qua moi cong ky thuat, chi
        # CHO DUNG cua no bi gioi han (§1.2c). Danh sach nay mang tieu de "dung
        # duoc cho `figure` / bia `image`" — khong noi gi thi vai dat co nuoc
        # vao `figure` than roi an cong chan cua kite_nop (do 10/09/2026).
        kn = a.get("khai_niem") or {}
        nhan_kn = (f"🧭 ẢNH KHÁI NIỆM ({kn.get('tu_khoa')}) — minh hoạ chủ đề, KHÔNG phải "
                   "ảnh của tin: CHỈ dùng ở bìa (slide 1), không vào slide thân; "
                   "caption 'via Wikimedia Commons'") if kn else ""
        L.append(f"- {a['ma']}: {kieu} {a['w']}x{a['h']} ({a['ti_le']}) | nguồn: {a['mien'] or a['tu']}"
                 + (f" | {a['paper_hinh']} của chính paper" if a.get("paper_hinh") else "")
                 + (f" | {nhan_kn}" if nhan_kn else "")
                 + (f" | {nhan_th}" if nhan_th else "")
                 + (f" | ảnh là: {a['mo_ta'][:90]}" if a.get("mo_ta") else (f" | alt: {a['alt'][:70]}" if a.get("alt") else ""))
                 + (" | có mặt người, khai đúng tên trong caption" if a.get("mat") else ""))
    L += dong_hero(m)
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
             "image": (hero_anh["ma"] if hero_anh else "<mã hình thật A? nếu bìa dùng ảnh, hoặc bỏ>"),  # noqa: E501
             "caption": (_hero_la_gi(hero_anh)[1] if hero_anh
                         else "<'… · via <ai>' bắt buộc khi có image>")},
            {"kind": "statement", "eyebrow": "BỐI CẢNH", "title": "<≤ 60>", "accent": "<cụm nhấn>",
             "standfirst": "<≤ 220>", "cards": [{"num": "01", "text": "<≤ 90>"}, {"num": "02", "text": "<≤ 90>"}]},
            {"kind": "steps", "eyebrow": "CÁCH VẬN HÀNH", "title": "<≤ 60>",
             "steps": [{"title": "<≤ 30>", "desc": "<≤ 80>"}, {"title": "…", "desc": "…"}, {"title": "…", "desc": "…"}]},
            *[{"kind": "figure", "eyebrow": "SỐ LIỆU", "title": "<≤ 60, tối đa 2 dòng>",
               "accent": "<cụm>", "image": ma, "caption": "<… · via <ai>>",
               "standfirst": "<≤ 200>"} for ma in (ep_khung or ["<mã hình thật A?>"])],
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
    m, wd, _ = cb.chay(a.draft_id, a.lam_moi, a.khong_browser, a.cho,
                       sau_chuan_bi=route_thieu_anh.sau_chuan_bi)
    brief = viet_brief(m, cb._doc_json(wd / "da_dung.json"))
    (wd / "brief.md").write_text(brief, encoding="utf-8")
    if not a.im:
        print(brief)
    return 0


if __name__ == "__main__":
    sys.exit(main())
