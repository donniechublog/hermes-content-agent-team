#!/usr/bin/env python3
"""PHA MANIFEST: dung bang anh, cau tu lieu va brief cho vai doc.

Tach tu image_prepare.py 09/09/2026 (audit A1, di chuyen thuan — than ham giu y nguyen).
"""
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

import schema
import state_paths
import role as vai_mod                 # `vai` la ten tham so o vai ham duoi

from prepare.common import ROOT, _brand_of


def describe_ranking_image(m: dict) -> str:
    """Mot cau ta anh XH engine da chup, dung chung cho brief cua Ethan/Dre va cho
    cau bao loi cua ethan_submit/dre_submit — de loi noi cung mot thu o moi noi."""
    xh = m.get("ranking") or {}
    if not xh:
        return "engine KHÔNG có ảnh xếp hạng cho bài này"
    cau = (f"engine đã chụp {xh.get('site')} ({xh.get('board')}): {xh.get('model')}"
           + (f" #{xh.get('rank')}" if xh.get("rank") else ""))
    if xh.get("kind") == "the":
        cau += " — THẺ DỰ PHÒNG vì không chụp được bảng"
    else:
        # IN RA HANG THAT da khoanh, khong chi khang dinh "da khoanh hang model":
        # ba bai 15/09/2026 khoanh hang "9. | DeepSeek Harness" (mot app cua nguoi
        # khac trong bang Apps) ma cau nay van noi "DeepSeek #2, da khoanh hang
        # model". `row` nam san trong manifest.json nhung chua tung ra toi brief hay
        # cau chan, nen ca vai lan nguoi duyet deu khong co gi de soat (LOW-180).
        dong = " ".join((xh.get("row") or "").split())
        cau += f", hàng đã khoanh: {dong[:90]}" if dong else ", đã khoanh hàng model"
    # Bang trong anh KHAC bang trong tieu de: khong chup duoc bang tin nhac toi nen
    # engine lay bang khac cua cung model. Anh dung, nhung so hang trong anh co the
    # KHAC so hang o tieu de — viet theo ANH, dung bung tieu de len ma anh khong do.
    if xh.get("mentioned") is False and xh.get("kind") != "the":
        cau += (f". ⚠️ ĐÂY LÀ BẢNG KHÁC với bảng tiêu đề nhắc tới — engine không chụp "
                f"được bảng đó. Viết theo ĐÚNG bảng và thứ hạng TRONG ẢNH "
                f"({xh.get('site')}" + (f" #{xh.get('rank')}" if xh.get("rank") else "")
                + "), đừng nhắc lại thứ hạng ở tiêu đề như thể ảnh chứng minh nó")
    return cau


def ranking_brief_line(m: dict, khoa: str, vai: str) -> str:
    """Dong 🏁 trong brief: `khoa` la "anh" (hero) hay "bìa" (carousel), `vai` la
    ten file nop chan (ethan_submit / dre_submit)."""
    import ranking
    xh_ = m.get("ranking") or {}
    if xh_ and not ranking.is_capture(xh_.get("kind")):
        # Khong chup duoc bang that -> chi co the du phong. Goi y, khong ep.
        return ("🏁 Tin xếp hạng nhưng engine KHÔNG chụp được bảng thật, chỉ dựng được "
                f"THẺ DỰ PHÒNG (mã \"XH\": {describe_ranking_image(m)}). Thẻ đó KHÔNG khẳng định thứ "
                f"hạng đã kiểm chứng, nên {vai} không ép: dùng ảnh thật tốt nhất nếu có, "
                "chỉ dùng thẻ khi không còn ảnh nào khá hơn.")
    if xh_:
        # Nhieu bang doc lap (09/09/2026: model tao anh + sua anh, hai bang khong
        # trung nhau) — noi ro co ma XH2 de vai dua ca hai vao thay vi chi dung
        # "XH" roi bo phi tam con lai (no van nam trong danh sach hinh that duoi,
        # nhung khong ai doc brief nay se biet no lien quan toi cung mot chuyen).
        them = ""
        if m.get("ranking_count", 1) > 1:
            them = (f" Engine còn chụp được {m['ranking_count'] - 1} bảng KHÁC cùng model này "
                    "(mã \"XH2\"... trong danh sách hình thật dưới, đo năng lực khác — vd tạo ảnh "
                    "vs chỉnh sửa ảnh) — nên dùng thêm, không chỉ dừng ở XH.")
        return (f"🏁 TIN XẾP HẠNG → {khoa}\"anh\": \"XH\" là BẮT BUỘC (luật Ông Chủ 06/09: nói về "
                f"ranking phải là bảng/chart xếp hạng, khoanh đúng model). {vai} chặn ảnh khác. "
                + describe_ranking_image(m) + "." + them)
    # Khong co ma XH: KHONG duoc bao "bat buoc dung XH" nua — truoc 06/09/2026
    # chieu, brief van doi ma do trong khi no khong ton tai, va nop cung chan
    # theo, nen vai khong bao gio nop duoc bai. Noi that trang thai va loi ra.
    return ("🏁 Tin này trông như tin XẾP HẠNG nhưng engine KHÔNG chụp được bảng "
            "(thường vì tiêu đề không nêu tên model cụ thể). KHÔNG có mã \"XH\": "
            f"dùng ảnh thật tốt nhất trong danh sách dưới, {vai} không chặn. "
            "Nói lại một câu cho Ông Chủ là bài xếp hạng mà không có bảng.")


def pair_two_vendor_images(anh: list, category) -> list:
    """Tin THƯƠNG VỤ: cặp ảnh của HAI hãng khác nhau để vai ghép dọc. Bảng loại
    tin (Ông Chủ 12/09/2026): *"nếu nói đến thương vụ thì lấy hình liên quan của
    hai brand đặt vào"*. Trả [[ma_A, ma_B], ...] — ưu tiên cùng loại (logo+logo,
    trụ sở+trụ sở) và dùng được; rỗng khi không phải M&A hay chỉ có một hãng."""
    import story_type
    if not story_type.late(category, "ghep_hai_hang"):
        return []
    theo_hang = {}
    for a in anh:
        th = a.get("brand_match") or {}
        if not th.get("key") or not a.get("uses") or a.get("relevant") is False:
            continue
        theo_hang.setdefault(th["key"], []).append(a)
    if len(theo_hang) < 2:
        return []
    (ka, la), (kb, lb) = list(theo_hang.items())[:2]
    ra = []
    for loai in ("logo", "anh", "nguoi"):
        x = next((a for a in la if (a.get("brand_match") or {}).get("kind") == loai), None)
        y = next((a for a in lb if (a.get("brand_match") or {}).get("kind") == loai), None)
        if x and y:
            ra.append([x["id"], y["id"]])
    if not ra:
        ra.append([la[0]["id"], lb[0]["id"]])
    return ra


def stackable_pairs(anh: list) -> list:
    """Cac cap anh NGANG ghep doc duoc: ti le sau ghep nam trong dai carousel
    chap nhan. (13/09/2026: bo dieu kien "cung tone" — image_rules.tone_mismatch
    khong con la cam doan ve chat luong/nguon, moi vai.)"""
    ngang = [a for a in anh if a["ratio"] >= 1.3]
    ra = []
    for i in range(len(ngang)):
        for j in range(i + 1, len(ngang)):
            x, y = ngang[i], ngang[j]
            if vai_mod.active_rules().stack_fit_frame(x["ratio"], y["ratio"]):
                ra.append([x["id"], y["id"]])
    return ra


def contact_sheet(anh: list, out: Path) -> None:
    """Mot tam thu nho gom moi anh, nhan MA + kich thuoc + loai: vai muon nhin
    thi mo MOT tam nay, khong mo tung anh."""
    if not anh:
        return
    from PIL import ImageFont
    try:
        f = ImageFont.truetype(str(ROOT / "assets/fonts/Inter.ttf"), 22)
    except Exception:                                        # noqa: BLE001
        f = ImageFont.load_default()
    W, cot = 360, 3
    hang = (len(anh) + cot - 1) // cot
    canvas = Image.new("RGB", (W * cot, 300 * hang), (18, 18, 18))
    d = ImageDraw.Draw(canvas)
    for k, a in enumerate(anh):
        im = Image.open(a["original_path"]).convert("RGB")
        im.thumbnail((W - 16, 240))
        x, y = (k % cot) * W + 8, (k // cot) * 300 + 8
        canvas.paste(im, (x, y))
        nhan = f"{a['id']}  {a['w']}x{a['h']}  {a['kind'].upper()}" + \
               ("  MẶT" if a["faces"] else "") + ("  NGANG" if a["landscape"] else "")
        d.text((x, y + 250), nhan, font=f, fill=(0, 204, 224))
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "PNG")


# ---- 4. tu lieu ------------------------------------------------------------
def gather_material(title: str, link: str, nguon_path: Path, wd: Path, tieu_de_en: str = "") -> dict:
    import material
    p = wd / state_paths.MATERIAL_FILE
    try:
        tl = material.gather(title, link, tu_nguon=str(nguon_path))
        p.write_text(material.use_page(tl), encoding="utf-8")
        doan = []
        for n in tl.get("sources", []):
            if n.get("label") == "bài gốc":
                doan = n.get("paragraphs", [])
                break
        if not doan and tl.get("sources"):
            doan = tl["sources"][0].get("paragraphs", [])
        # Cau co so tu BAO KHAC chi giu khi lien quan toi tin (chung >= 1 tu dac
        # trung voi tieu de): trang tong hop kieu "Top Tech News" keo theo ca
        # tin tuyen phi cong, funding cua hang khac (do that 04/09, Broadcom).
        import article_sources as _nb
        goc_tu = _nb._tu(title) | _nb._tu(tieu_de_en or "")
        goc_url = (link or "").rstrip("/")
        cau_goc = set()
        for n in tl.get("sources", []):
            if (n.get("url") or "").rstrip("/") == goc_url or n.get("label") == "bài gốc":
                cau_goc.update(material.sentence_has_count(n.get("paragraphs", [])))
        # Lien quan = chung >= 2 tu, hoac chung mot tu MANG SO/ten rieng dau
        # (115b, fy27, broadcom). Chung mot tu thuong ("nearly", "revenue")
        # chua du: cau tuyen phi cong "increased nearly 40%" tung lot vi "nearly".
        manh = {t for t in goc_tu if any(ch.isdigit() for ch in t)}
        ten_dau = _nb._tu(" ".join((tieu_de_en or title).split()[:2]))
        cau = []
        for c in tl.get("number_sentences", []):
            tu_c = _nb._tu(c)
            chung = goc_tu & tu_c
            if c in cau_goc or len(chung) >= 2 or (chung & (manh | ten_dau)):
                cau.append(c)
        return {"number_sentences": cau[:25],
                "lead_paragraph": " ".join(doan)[:1500],
                "source_count": len(tl.get("sources", []))}
    except Exception as e:                                   # noqa: BLE001
        print(f"[tu_lieu] hong: {type(e).__name__}: {e!r}", file=sys.stderr)
        return {"number_sentences": [], "lead_paragraph": "", "source_count": 0}


def _article_material(title: str, link: str, nguon_path: Path, wd: Path, nguon: dict, bp: dict) -> dict:
    """Tu lieu cho vai viet; fetch tinh rong (trang JS) thi dung chu tu browser."""
    print("[tu_lieu] boc chu tu nguon...", file=sys.stderr)
    tl = gather_material(title, link, nguon_path, wd, nguon.get("tieu_de_en", ""))
    if len(tl.get("number_sentences", [])) < 3 and bp.get("chu"):
        # Fetch tinh doc ra rong (trang JS) -> dung chu lay tu browser.
        import material as _tl
        doan = [d.strip() for d in bp["chu"].split("\n") if len(d.strip()) > 40]
        cau_so = _tl.sentence_has_count(doan)[:25]
        tl = {"number_sentences": cau_so, "lead_paragraph": " ".join(doan)[:1500],
              "source_count": max(tl.get("source_count", 0), 1), "source": "browser"}
        # Dung CHINH `use_page` de dung tep, khong tu ghep chuoi.
        #
        # Ban tu ghep truoc 06/09/2026 chi in cac doan van thuan, KHONG co dong
        # nao bat dau bang "- ". Ma `caption_check` tim cau nguon bang dung dau
        # hieu do (`l.startswith("- ") and SO.search(l)`), nen tren moi bai di
        # qua nhanh nay — bai trang JS, tuc phan lon trang san pham hien dai —
        # cong "nguon co so ma caption khong co so" TU TAT, khong bao gi, va
        # `cau_so_trong_nguon` ve 0. Miles doc material.md chu khong doc manifest.json
        # nen khong co duong nao khac de biet.
        (wd / state_paths.MATERIAL_FILE).write_text(
            _tl.use_page({"title": title, "number_sentences": cau_so,
                            "sources": [{"label": "Chữ lấy từ browser", "title": title,
                                         "url": link, "paragraphs": doan[:60]}]}),
            encoding="utf-8")
    return tl


def compute_derived(anh: list, vai_anh: str, so_xh: int = 0) -> dict:
    """Cac gia tri DAN XUAT tu bo anh: dung_duoc, not_yet_seen, domains, usable_count,
    cover_suggestions, stackable_pairs. MOT ban cho hai nguoi goi: `build_manifest` luc engine
    chay xong, va `find_more_images.fresh_manifest` khi vai tim them anh sau do —
    khong thi manifest sau khi them anh mang so cu (12/09/2026)."""
    dung_duoc = [a for a in anh if a["uses"] and a.get("relevant") is not False]
    chua_nhin = [a["id"] for a in anh if a.get("relevant") is None]
    so_mien = sorted({(a.get("domain") or a.get("source") or "?") for a in dung_duoc})
    # Anh khai niem chi lam bia, nen ca chum chi DEM LA MOT khi xet du/thieu:
    # 5 la co Nhat khong phai 5 slide. `usable_count` di vao brief (THIEU ANH)
    # va co `missing_images` (xem _description_missing_image) ma route_missing_images doc de quyet
    # dinh hoi Ong Chu hay chuyen Kite.
    so_dung_duoc = schema.count_image_use_ok(anh, vai_anh)
    # Thu tu goi y bia: anh RIENG cua tin -> anh THUONG HIEU (tru so that cua
    # hang trong tin, 09/09/2026) -> anh KHAI NIEM (co, rack, chung chung; 07/09).
    goi_y_bia = [a["id"] for a in sorted(
        (a for a in anh if vai_mod.has_label_cover(a["uses"]) and a.get("relevant") is not False),
        key=lambda a: (bool(a.get("concept")), bool(a.get("brand_match")),
                       a["bottom_left_brightness"], -a["short_side"]))][:3]
    # `xhs` co the co NHIEU HON MOT (bang xep hang do nang luc khac nhau, xem
    # `_capture_ranking`) — goi y het cac ma XH/XH2/... truoc anh khac; `ranking`
    # (so, dung boi cong chan/brief "bat buoc dung XH") van la BANG DAU TIEN.
    if so_xh:
        goi_y_bia = ["XH" if i == 0 else f"XH{i + 1}" for i in range(so_xh)] + goi_y_bia
    return {"dung_duoc": dung_duoc, "not_yet_seen": chua_nhin, "domains": so_mien,
            "usable_count": so_dung_duoc, "cover_suggestions": goi_y_bia, "stackable_pairs": stackable_pairs(dung_duoc)}


def build_manifest(draft_id: str, meta: dict, title: str, link: str, nguon: dict, nguon_path: Path,
                  tom: dict, wd: Path, anh: list, xhs: list, tin_xep_hang: bool, bp: dict, tl: dict,
                  flagship: bool, toi_thieu: int, vai_anh: str = "", dropped: list | None = None) -> dict:
    """Manifest (manifest.json) cua bai — thu ma moi *_prepare va *_submit doc. Cac gia
    tri dan xuat (dung_duoc, not_yet_seen, domains, cover_suggestions) tinh o day tu `images`."""
    import story_type            # import tinh de cong cu doi ten nhin thay (LOW-50), nhu dong 78
    xhs = xhs or []            # nhan ca None (quy uoc cu, con trong vai noi goi truc tiep/test)
    dx = compute_derived(anh, vai_anh, so_xh=len(xhs))
    chua_nhin, so_mien = dx["not_yet_seen"], dx["domains"]
    so_dung_duoc, goi_y_bia = dx["usable_count"], dx["cover_suggestions"]
    m = {"version": schema.VERSION_MANIFEST,
         "draft_id": draft_id, "brand": _brand_of(meta), "title": title, "link": link,
         "via": meta.get("via", ""), "category": meta.get("category", ""),
         "summary": tom.get("summary", ""), "source_note": tom.get("source_note", ""),
         "workdir": str(wd), "created_at": int(time.time()),
         "flagship": flagship, "min_images": toi_thieu,
         # VAI se dung bo anh nay. Ghi vao manifest de nguoi doc sau (nut "ha
         # san" cua approve_post) khoi phai doan tu draft_id — va de biet goi san
         # pham la "slide" hay "ảnh" (su co 10/09/2026).
         "image_role": vai_anh,
         # San tuyet doi cua VAI DO (Dre 5 = carousel.MIN_SLIDE, Ethan 1). Ong
         # Chu bam "lam voi N anh" (imgtiep) thi approve_service ha `min_images`
         # ve day, khong ha thap hon duoc. Truoc 10/09/2026 cho nay go cung
         # carousel.MIN_SLIDE cho moi vai, nen bai cua Ethan bi doi 5 anh.
         "base_min_images": vai_mod.min_images(vai_anh), "domains": so_mien,
         "images": anh, "stackable_pairs": dx["stackable_pairs"], "cover_suggestions": goi_y_bia, "material": tl,
         "two_company_pairs": pair_two_vendor_images(anh, meta.get("category", "")),
         "image_order_by_story_type": list(story_type.order_image(meta.get("category", ""))),
         "usable_count": so_dung_duoc, "not_yet_seen": chua_nhin,
         "ranking": ({k: xhs[0].get(k) for k in ("model", "rank", "site", "board", "kind", "mentioned")}
                     if xhs else None),
         "ranking_count": len(xhs),
         "is_ranking_story": tin_xep_hang,
         "article_text": (bp.get("chu") or "")[:20000],
         "source_path": str(nguon_path), "title_en": nguon.get("tieu_de_en", ""),
         # LOW-225: ung vien bi bo TRUOC khi thanh anh (pha tai) — truoc day chi co o stderr.
         "dropped": dropped or []}
    return m
