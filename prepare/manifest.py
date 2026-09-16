#!/usr/bin/env python3
"""PHA MANIFEST: dung bang anh, cau tu lieu va brief cho vai doc.

Tach tu image_prepare.py 09/09/2026 (audit A1, di chuyen thuan — than ham giu y nguyen).
"""
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

import schema
import role as vai_mod                 # `vai` la ten tham so o vai ham duoi

from prepare.common import ROOT, _brand_of


def describe_ranking_image(m: dict) -> str:
    """Mot cau ta anh XH engine da chup, dung chung cho brief cua Ethan/Dre va cho
    cau bao loi cua ethan_submit/dre_submit — de loi noi cung mot thu o moi noi."""
    xh = m.get("xep_hang") or {}
    if not xh:
        return "engine KHÔNG có ảnh xếp hạng cho bài này"
    cau = (f"engine đã chụp {xh.get('site')} ({xh.get('bang')}): {xh.get('model')}"
           + (f" #{xh.get('hang')}" if xh.get("hang") else ""))
    if xh.get("kieu") == "the":
        cau += " — THẺ DỰ PHÒNG vì không chụp được bảng"
    else:
        # IN RA HANG THAT da khoanh, khong chi khang dinh "da khoanh hang model":
        # ba bai 15/09/2026 khoanh hang "9. | DeepSeek Harness" (mot app cua nguoi
        # khac trong bang Apps) ma cau nay van noi "DeepSeek #2, da khoanh hang
        # model". `dong` nam san trong xong.json nhung chua tung ra toi brief hay
        # cau chan, nen ca vai lan nguoi duyet deu khong co gi de soat (LOW-180).
        dong = " ".join((xh.get("dong") or "").split())
        cau += f", hàng đã khoanh: {dong[:90]}" if dong else ", đã khoanh hàng model"
    # Bang trong anh KHAC bang trong tieu de: khong chup duoc bang tin nhac toi nen
    # engine lay bang khac cua cung model. Anh dung, nhung so hang trong anh co the
    # KHAC so hang o tieu de — viet theo ANH, dung bung tieu de len ma anh khong do.
    if xh.get("duoc_nhac") is False and xh.get("kieu") != "the":
        cau += (f". ⚠️ ĐÂY LÀ BẢNG KHÁC với bảng tiêu đề nhắc tới — engine không chụp "
                f"được bảng đó. Viết theo ĐÚNG bảng và thứ hạng TRONG ẢNH "
                f"({xh.get('site')}" + (f" #{xh.get('hang')}" if xh.get("hang") else "")
                + "), đừng nhắc lại thứ hạng ở tiêu đề như thể ảnh chứng minh nó")
    return cau


def ranking_brief_line(m: dict, khoa: str, vai: str) -> str:
    """Dong 🏁 trong brief: `khoa` la "anh" (hero) hay "bìa" (carousel), `vai` la
    ten file nop chan (ethan_submit / dre_submit)."""
    import ranking
    xh_ = m.get("xep_hang") or {}
    if xh_ and not ranking.is_capture(xh_.get("kieu")):
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
        if m.get("so_xep_hang", 1) > 1:
            them = (f" Engine còn chụp được {m['so_xep_hang'] - 1} bảng KHÁC cùng model này "
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
        th = a.get("thuong_hieu") or {}
        if not th.get("khoa") or not a.get("dung") or a.get("lien_quan") is False:
            continue
        theo_hang.setdefault(th["khoa"], []).append(a)
    if len(theo_hang) < 2:
        return []
    (ka, la), (kb, lb) = list(theo_hang.items())[:2]
    ra = []
    for loai in ("logo", "anh", "nguoi"):
        x = next((a for a in la if (a.get("thuong_hieu") or {}).get("loai") == loai), None)
        y = next((a for a in lb if (a.get("thuong_hieu") or {}).get("loai") == loai), None)
        if x and y:
            ra.append([x["ma"], y["ma"]])
    if not ra:
        ra.append([la[0]["ma"], lb[0]["ma"]])
    return ra


def stackable_pairs(anh: list) -> list:
    """Cac cap anh NGANG ghep doc duoc: ti le sau ghep nam trong dai carousel
    chap nhan. (13/09/2026: bo dieu kien "cung tone" — image_rules.tone_mismatch
    khong con la cam doan ve chat luong/nguon, moi vai.)"""
    ngang = [a for a in anh if a["ti_le"] >= 1.3]
    ra = []
    for i in range(len(ngang)):
        for j in range(i + 1, len(ngang)):
            x, y = ngang[i], ngang[j]
            if vai_mod.active_rules().stack_fit_frame(x["ti_le"], y["ti_le"]):
                ra.append([x["ma"], y["ma"]])
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
        im = Image.open(a["goc"]).convert("RGB")
        im.thumbnail((W - 16, 240))
        x, y = (k % cot) * W + 8, (k // cot) * 300 + 8
        canvas.paste(im, (x, y))
        nhan = f"{a['ma']}  {a['w']}x{a['h']}  {a['loai'].upper()}" + \
               ("  MẶT" if a["mat"] else "") + ("  NGANG" if a["ngang"] else "")
        d.text((x, y + 250), nhan, font=f, fill=(0, 204, 224))
    out.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(out, "PNG")


# ---- 4. tu lieu ------------------------------------------------------------
def gather_material(title: str, link: str, nguon_path: Path, wd: Path, tieu_de_en: str = "") -> dict:
    import material
    p = wd / "tu_lieu.md"
    try:
        tl = material.gather(title, link, tu_nguon=str(nguon_path))
        p.write_text(material.use_page(tl), encoding="utf-8")
        doan = []
        for n in tl.get("nguon", []):
            if n.get("nhan") == "bài gốc":
                doan = n.get("doan", [])
                break
        if not doan and tl.get("nguon"):
            doan = tl["nguon"][0].get("doan", [])
        # Cau co so tu BAO KHAC chi giu khi lien quan toi tin (chung >= 1 tu dac
        # trung voi tieu de): trang tong hop kieu "Top Tech News" keo theo ca
        # tin tuyen phi cong, funding cua hang khac (do that 04/09, Broadcom).
        import article_sources as _nb
        goc_tu = _nb._tu(title) | _nb._tu(tieu_de_en or "")
        goc_url = (link or "").rstrip("/")
        cau_goc = set()
        for n in tl.get("nguon", []):
            if (n.get("url") or "").rstrip("/") == goc_url or n.get("nhan") == "bài gốc":
                cau_goc.update(material.sentence_has_count(n.get("doan", [])))
        # Lien quan = chung >= 2 tu, hoac chung mot tu MANG SO/ten rieng dau
        # (115b, fy27, broadcom). Chung mot tu thuong ("nearly", "revenue")
        # chua du: cau tuyen phi cong "increased nearly 40%" tung lot vi "nearly".
        manh = {t for t in goc_tu if any(ch.isdigit() for ch in t)}
        ten_dau = _nb._tu(" ".join((tieu_de_en or title).split()[:2]))
        cau = []
        for c in tl.get("cau_co_so", []):
            tu_c = _nb._tu(c)
            chung = goc_tu & tu_c
            if c in cau_goc or len(chung) >= 2 or (chung & (manh | ten_dau)):
                cau.append(c)
        return {"cau_co_so": cau[:25],
                "doan_dau": " ".join(doan)[:1500],
                "so_nguon": len(tl.get("nguon", []))}
    except Exception as e:                                   # noqa: BLE001
        print(f"[tu_lieu] hong: {type(e).__name__}: {e!r}", file=sys.stderr)
        return {"cau_co_so": [], "doan_dau": "", "so_nguon": 0}


def _article_material(title: str, link: str, nguon_path: Path, wd: Path, nguon: dict, bp: dict) -> dict:
    """Tu lieu cho vai viet; fetch tinh rong (trang JS) thi dung chu tu browser."""
    print("[tu_lieu] boc chu tu nguon...", file=sys.stderr)
    tl = gather_material(title, link, nguon_path, wd, nguon.get("tieu_de_en", ""))
    if len(tl.get("cau_co_so", [])) < 3 and bp.get("chu"):
        # Fetch tinh doc ra rong (trang JS) -> dung chu lay tu browser.
        import material as _tl
        doan = [d.strip() for d in bp["chu"].split("\n") if len(d.strip()) > 40]
        cau_so = _tl.sentence_has_count(doan)[:25]
        tl = {"cau_co_so": cau_so, "doan_dau": " ".join(doan)[:1500],
              "so_nguon": max(tl.get("so_nguon", 0), 1), "tu": "browser"}
        # Dung CHINH `use_page` de dung tep, khong tu ghep chuoi.
        #
        # Ban tu ghep truoc 06/09/2026 chi in cac doan van thuan, KHONG co dong
        # nao bat dau bang "- ". Ma `caption_check` tim cau nguon bang dung dau
        # hieu do (`l.startswith("- ") and SO.search(l)`), nen tren moi bai di
        # qua nhanh nay — bai trang JS, tuc phan lon trang san pham hien dai —
        # cong "nguon co so ma caption khong co so" TU TAT, khong bao gi, va
        # `cau_so_trong_nguon` ve 0. Miles doc tu_lieu.md chu khong doc xong.json
        # nen khong co duong nao khac de biet.
        (wd / "tu_lieu.md").write_text(
            _tl.use_page({"tieu_de": title, "cau_co_so": cau_so,
                            "nguon": [{"nhan": "Chữ lấy từ browser", "tieu_de": title,
                                       "url": link, "doan": doan[:60]}]}),
            encoding="utf-8")
    return tl


def compute_derived(anh: list, vai_anh: str, so_xh: int = 0) -> dict:
    """Cac gia tri DAN XUAT tu bo anh: dung_duoc, chua_nhin, so_mien, so_dung_duoc,
    goi_y_bia, cap_ghep. MOT ban cho hai nguoi goi: `build_manifest` luc engine
    chay xong, va `find_more_images.fresh_manifest` khi vai tim them anh sau do —
    khong thi manifest sau khi them anh mang so cu (12/09/2026)."""
    dung_duoc = [a for a in anh if a["dung"] and a.get("lien_quan") is not False]
    chua_nhin = [a["ma"] for a in anh if a.get("lien_quan") is None]
    so_mien = sorted({(a.get("mien") or a.get("tu") or "?") for a in dung_duoc})
    # Anh khai niem chi lam bia, nen ca chum chi DEM LA MOT khi xet du/thieu:
    # 5 la co Nhat khong phai 5 slide. `so_dung_duoc` di vao brief (THIEU ANH)
    # va co `thieu_anh` (xem _description_missing_image) ma route_missing_images doc de quyet
    # dinh hoi Ong Chu hay chuyen Kite.
    so_dung_duoc = schema.count_image_use_ok(anh, vai_anh)
    # Thu tu goi y bia: anh RIENG cua tin -> anh THUONG HIEU (tru so that cua
    # hang trong tin, 09/09/2026) -> anh KHAI NIEM (co, rack, chung chung; 07/09).
    goi_y_bia = [a["ma"] for a in sorted(
        (a for a in anh if vai_mod.has_label_cover(a["dung"]) and a.get("lien_quan") is not False),
        key=lambda a: (bool(a.get("khai_niem")), bool(a.get("thuong_hieu")),
                       a["goc_trai_sang"], -a["canh_ngan"]))][:3]
    # `xhs` co the co NHIEU HON MOT (bang xep hang do nang luc khac nhau, xem
    # `_capture_ranking`) — goi y het cac ma XH/XH2/... truoc anh khac; `xep_hang`
    # (so, dung boi cong chan/brief "bat buoc dung XH") van la BANG DAU TIEN.
    if so_xh:
        goi_y_bia = ["XH" if i == 0 else f"XH{i + 1}" for i in range(so_xh)] + goi_y_bia
    return {"dung_duoc": dung_duoc, "chua_nhin": chua_nhin, "so_mien": so_mien,
            "so_dung_duoc": so_dung_duoc, "goi_y_bia": goi_y_bia, "cap_ghep": stackable_pairs(dung_duoc)}


def build_manifest(draft_id: str, meta: dict, title: str, link: str, nguon: dict, nguon_path: Path,
                  tom: dict, wd: Path, anh: list, xhs: list, tin_xep_hang: bool, bp: dict, tl: dict,
                  flagship: bool, toi_thieu: int, vai_anh: str = "") -> dict:
    """Manifest (xong.json) cua bai — thu ma moi *_prepare va *_submit doc. Cac gia
    tri dan xuat (dung_duoc, chua_nhin, so_mien, goi_y_bia) tinh o day tu `anh`."""
    import story_type            # import tinh de cong cu doi ten nhin thay (LOW-50), nhu dong 78
    xhs = xhs or []            # nhan ca None (quy uoc cu, con trong vai noi goi truc tiep/test)
    dx = compute_derived(anh, vai_anh, so_xh=len(xhs))
    chua_nhin, so_mien = dx["chua_nhin"], dx["so_mien"]
    so_dung_duoc, goi_y_bia = dx["so_dung_duoc"], dx["goi_y_bia"]
    m = {"phien_ban": schema.VERSION_MANIFEST,
         "draft_id": draft_id, "brand": _brand_of(meta), "title": title, "link": link,
         "via": meta.get("via", ""), "category": meta.get("category", ""),
         "summary": tom.get("summary", ""), "source_note": tom.get("source_note", ""),
         "workdir": str(wd), "tao_luc": int(time.time()),
         "flagship": flagship, "toi_thieu": toi_thieu,
         # VAI se dung bo anh nay. Ghi vao manifest de nguoi doc sau (nut "ha
         # san" cua approve_post) khoi phai doan tu draft_id — va de biet goi san
         # pham la "slide" hay "ảnh" (su co 10/09/2026).
         "vai_anh": vai_anh,
         # San tuyet doi cua VAI DO (Dre 5 = carousel.MIN_SLIDE, Ethan 1). Ong
         # Chu bam "lam voi N anh" (imgtiep) thi approve_service ha `toi_thieu`
         # ve day, khong ha thap hon duoc. Truoc 10/09/2026 cho nay go cung
         # carousel.MIN_SLIDE cho moi vai, nen bai cua Ethan bi doi 5 anh.
         "toi_thieu_co_ban": vai_mod.min_images(vai_anh), "so_mien": so_mien,
         "anh": anh, "cap_ghep": dx["cap_ghep"], "goi_y_bia": goi_y_bia, "tu_lieu": tl,
         "ghep_hai_hang": pair_two_vendor_images(anh, meta.get("category", "")),
         "thu_tu_anh_theo_loai": list(story_type.order_image(meta.get("category", ""))),
         "so_dung_duoc": so_dung_duoc, "chua_nhin": chua_nhin,
         "xep_hang": ({k: xhs[0].get(k) for k in ("model", "hang", "site", "bang", "kieu", "duoc_nhac")}
                      if xhs else None),
         "so_xep_hang": len(xhs),
         "tin_xep_hang": tin_xep_hang,
         "chu_bai": (bp.get("chu") or "")[:20000],
         "nguon_path": str(nguon_path), "tieu_de_en": nguon.get("tieu_de_en", "")}
    return m
