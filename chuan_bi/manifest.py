#!/usr/bin/env python3
"""PHA MANIFEST: dung bang anh, cau tu lieu va brief cho vai doc.

Tach tu anh_chuan_bi.py 09/09/2026 (audit A1, di chuyen thuan — than ham giu y nguyen).
"""
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw

import luat_anh
import schema
import vai as vai_mod                 # `vai` la ten tham so o vai ham duoi

from chuan_bi.chung import ROOT, _brand_cua


def cau_xep_hang(m: dict) -> str:
    """Mot cau ta anh XH engine da chup, dung chung cho brief cua Ethan/Dre va cho
    cau bao loi cua ethan_nop/dre_nop — de loi noi cung mot thu o moi noi."""
    xh = m.get("xep_hang") or {}
    if not xh:
        return "engine KHÔNG có ảnh xếp hạng cho bài này"
    cau = (f"engine đã chụp {xh.get('site')} ({xh.get('bang')}): {xh.get('model')}"
           + (f" #{xh.get('hang')}" if xh.get("hang") else "")
           + (" — THẺ DỰ PHÒNG vì không chụp được bảng" if xh.get("kieu") == "the"
              else ", đã khoanh hàng model"))
    # Bang trong anh KHAC bang trong tieu de: khong chup duoc bang tin nhac toi nen
    # engine lay bang khac cua cung model. Anh dung, nhung so hang trong anh co the
    # KHAC so hang o tieu de — viet theo ANH, dung bung tieu de len ma anh khong do.
    if xh.get("duoc_nhac") is False and xh.get("kieu") != "the":
        cau += (f". ⚠️ ĐÂY LÀ BẢNG KHÁC với bảng tiêu đề nhắc tới — engine không chụp "
                f"được bảng đó. Viết theo ĐÚNG bảng và thứ hạng TRONG ẢNH "
                f"({xh.get('site')}" + (f" #{xh.get('hang')}" if xh.get("hang") else "")
                + "), đừng nhắc lại thứ hạng ở tiêu đề như thể ảnh chứng minh nó")
    return cau


def dong_brief_xep_hang(m: dict, khoa: str, vai: str) -> str:
    """Dong 🏁 trong brief: `khoa` la "anh" (hero) hay "bìa" (carousel), `vai` la
    ten file nop chan (ethan_nop / dre_nop)."""
    import xep_hang
    xh_ = m.get("xep_hang") or {}
    if xh_ and not xep_hang.la_chup(xh_.get("kieu")):
        # Khong chup duoc bang that -> chi co the du phong. Goi y, khong ep.
        return ("🏁 Tin xếp hạng nhưng engine KHÔNG chụp được bảng thật, chỉ dựng được "
                f"THẺ DỰ PHÒNG (mã \"XH\": {cau_xep_hang(m)}). Thẻ đó KHÔNG khẳng định thứ "
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
                + cau_xep_hang(m) + "." + them)
    # Khong co ma XH: KHONG duoc bao "bat buoc dung XH" nua — truoc 06/09/2026
    # chieu, brief van doi ma do trong khi no khong ton tai, va nop cung chan
    # theo, nen vai khong bao gio nop duoc bai. Noi that trang thai va loi ra.
    return ("🏁 Tin này trông như tin XẾP HẠNG nhưng engine KHÔNG chụp được bảng "
            "(thường vì tiêu đề không nêu tên model cụ thể). KHÔNG có mã \"XH\": "
            f"dùng ảnh thật tốt nhất trong danh sách dưới, {vai} không chặn. "
            "Nói lại một câu cho Ông Chủ là bài xếp hạng mà không có bảng.")


def ghep_hai_hang(anh: list, category) -> list:
    """Tin THƯƠNG VỤ: cặp ảnh của HAI hãng khác nhau để vai ghép dọc. Bảng loại
    tin (Ông Chủ 12/09/2026): *"nếu nói đến thương vụ thì lấy hình liên quan của
    hai brand đặt vào"*. Trả [[ma_A, ma_B], ...] — ưu tiên cùng loại (logo+logo,
    trụ sở+trụ sở) và dùng được; rỗng khi không phải M&A hay chỉ có một hãng."""
    import loai_tin
    if not loai_tin.muon(category, "ghep_hai_hang"):
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


def cap_ghep(anh: list) -> list:
    """Cac cap anh NGANG ghep doc duoc: cung tone (luat_anh.lech_tone) va ti le
    sau ghep nam trong dai carousel chap nhan."""
    ngang = [a for a in anh if a["ti_le"] >= 1.3]
    ims = {a["ma"]: Image.open(a["goc"]).convert("RGB") for a in ngang}
    ra = []
    for i in range(len(ngang)):
        for j in range(i + 1, len(ngang)):
            x, y = ngang[i], ngang[j]
            rc = 1 / (1 / x["ti_le"] + 1 / y["ti_le"])
            if not (luat_anh.TI_LE_45 - luat_anh.DUNG_SAI_TI_LE <= rc
                    <= luat_anh.TI_LE_11 + luat_anh.DUNG_SAI_TI_LE):
                continue
            if luat_anh.lech_tone([ims[x["ma"]], ims[y["ma"]]]):
                continue
            ra.append([x["ma"], y["ma"]])
    return ra


def bang_anh(anh: list, out: Path) -> None:
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
def gom_tu_lieu(title: str, link: str, nguon_path: Path, wd: Path, tieu_de_en: str = "") -> dict:
    import tu_lieu
    p = wd / "tu_lieu.md"
    try:
        tl = tu_lieu.gom(title, link, tu_nguon=str(nguon_path))
        p.write_text(tu_lieu.dung_trang(tl), encoding="utf-8")
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
        import nguon_bai as _nb
        goc_tu = _nb._tu(title) | _nb._tu(tieu_de_en or "")
        goc_url = (link or "").rstrip("/")
        cau_goc = set()
        for n in tl.get("nguon", []):
            if (n.get("url") or "").rstrip("/") == goc_url or n.get("nhan") == "bài gốc":
                cau_goc.update(tu_lieu.cau_co_so(n.get("doan", [])))
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


def _tu_lieu_bai(title: str, link: str, nguon_path: Path, wd: Path, nguon: dict, bp: dict) -> dict:
    """Tu lieu cho vai viet; fetch tinh rong (trang JS) thi dung chu tu browser."""
    print("[tu_lieu] boc chu tu nguon...", file=sys.stderr)
    tl = gom_tu_lieu(title, link, nguon_path, wd, nguon.get("tieu_de_en", ""))
    if len(tl.get("cau_co_so", [])) < 3 and bp.get("chu"):
        # Fetch tinh doc ra rong (trang JS) -> dung chu lay tu browser.
        import tu_lieu as _tl
        doan = [d.strip() for d in bp["chu"].split("\n") if len(d.strip()) > 40]
        cau_so = _tl.cau_co_so(doan)[:25]
        tl = {"cau_co_so": cau_so, "doan_dau": " ".join(doan)[:1500],
              "so_nguon": max(tl.get("so_nguon", 0), 1), "tu": "browser"}
        # Dung CHINH `dung_trang` de dung tep, khong tu ghep chuoi.
        #
        # Ban tu ghep truoc 06/09/2026 chi in cac doan van thuan, KHONG co dong
        # nao bat dau bang "- ". Ma `caption_check` tim cau nguon bang dung dau
        # hieu do (`l.startswith("- ") and SO.search(l)`), nen tren moi bai di
        # qua nhanh nay — bai trang JS, tuc phan lon trang san pham hien dai —
        # cong "nguon co so ma caption khong co so" TU TAT, khong bao gi, va
        # `cau_so_trong_nguon` ve 0. Miles doc tu_lieu.md chu khong doc xong.json
        # nen khong co duong nao khac de biet.
        (wd / "tu_lieu.md").write_text(
            _tl.dung_trang({"tieu_de": title, "cau_co_so": cau_so,
                            "nguon": [{"nhan": "Chữ lấy từ browser", "tieu_de": title,
                                       "url": link, "doan": doan[:60]}]}),
            encoding="utf-8")
    return tl


def dan_xuat(anh: list, so_xh: int = 0) -> dict:
    """Cac gia tri DAN XUAT tu bo anh: dung_duoc, chua_nhin, so_mien, so_dung_duoc,
    goi_y_bia, cap_ghep. MOT ban cho hai nguoi goi: `dung_manifest` luc engine
    chay xong, va `tim_anh_them.lam_moi_manifest` khi vai tim them anh sau do —
    khong thi manifest sau khi them anh mang so cu (12/09/2026)."""
    dung_duoc = [a for a in anh if a["dung"] and a.get("lien_quan") is not False]
    chua_nhin = [a["ma"] for a in anh if a.get("lien_quan") is None]
    so_mien = sorted({(a.get("mien") or a.get("tu") or "?") for a in dung_duoc})
    # Anh khai niem chi lam bia, nen ca chum chi DEM LA MOT khi xet du/thieu:
    # 5 la co Nhat khong phai 5 slide. `so_dung_duoc` di vao brief (THIEU ANH)
    # va co `thieu_anh` (xem _mo_ta_thieu_anh) ma route_thieu_anh doc de quyet
    # dinh hoi Ong Chu hay chuyen Kite.
    so_dung_duoc = schema.so_anh_dung_duoc(anh)
    # Thu tu goi y bia: anh RIENG cua tin -> anh THUONG HIEU (tru so that cua
    # hang trong tin, 09/09/2026) -> anh KHAI NIEM (co, rack, chung chung; 07/09).
    goi_y_bia = [a["ma"] for a in sorted(
        (a for a in anh if vai_mod.co_nhan_bia(a["dung"]) and a.get("lien_quan") is not False),
        key=lambda a: (bool(a.get("khai_niem")), bool(a.get("thuong_hieu")),
                       a["goc_trai_sang"], -a["canh_ngan"]))][:3]
    # `xhs` co the co NHIEU HON MOT (bang xep hang do nang luc khac nhau, xem
    # `_chup_xep_hang`) — goi y het cac ma XH/XH2/... truoc anh khac; `xep_hang`
    # (so, dung boi cong chan/brief "bat buoc dung XH") van la BANG DAU TIEN.
    if so_xh:
        goi_y_bia = ["XH" if i == 0 else f"XH{i + 1}" for i in range(so_xh)] + goi_y_bia
    return {"dung_duoc": dung_duoc, "chua_nhin": chua_nhin, "so_mien": so_mien,
            "so_dung_duoc": so_dung_duoc, "goi_y_bia": goi_y_bia, "cap_ghep": cap_ghep(dung_duoc)}


def dung_manifest(draft_id: str, meta: dict, title: str, link: str, nguon: dict, nguon_path: Path,
                  tom: dict, wd: Path, anh: list, xhs: list, tin_xep_hang: bool, bp: dict, tl: dict,
                  flagship: bool, toi_thieu: int, vai_anh: str = "") -> dict:
    """Manifest (xong.json) cua bai — thu ma moi *_chuan_bi va *_nop doc. Cac gia
    tri dan xuat (dung_duoc, chua_nhin, so_mien, goi_y_bia) tinh o day tu `anh`."""
    xhs = xhs or []            # nhan ca None (quy uoc cu, con trong vai noi goi truc tiep/test)
    dx = dan_xuat(anh, so_xh=len(xhs))
    _, chua_nhin, so_mien = dx["dung_duoc"], dx["chua_nhin"], dx["so_mien"]
    so_dung_duoc, goi_y_bia = dx["so_dung_duoc"], dx["goi_y_bia"]
    m = {"phien_ban": schema.PHIEN_BAN_MANIFEST,
         "draft_id": draft_id, "brand": _brand_cua(meta), "title": title, "link": link,
         "via": meta.get("via", ""), "category": meta.get("category", ""),
         "summary": tom.get("summary", ""), "source_note": tom.get("source_note", ""),
         "workdir": str(wd), "tao_luc": int(time.time()),
         "flagship": flagship, "toi_thieu": toi_thieu,
         # VAI se dung bo anh nay. Ghi vao manifest de nguoi doc sau (nut "ha
         # san" cua duyet_bai) khoi phai doan tu draft_id — va de biet goi san
         # pham la "slide" hay "ảnh" (su co 10/09/2026).
         "vai_anh": vai_anh,
         # San tuyet doi cua VAI DO (Dre 5 = carousel.MIN_SLIDE, Ethan 1). Ong
         # Chu bam "lam voi N anh" (imgtiep) thi approve_service ha `toi_thieu`
         # ve day, khong ha thap hon duoc. Truoc 10/09/2026 cho nay go cung
         # carousel.MIN_SLIDE cho moi vai, nen bai cua Ethan bi doi 5 anh.
         "toi_thieu_co_ban": vai_mod.so_anh_toi_thieu(vai_anh), "so_mien": so_mien,
         "anh": anh, "cap_ghep": dx["cap_ghep"], "goi_y_bia": goi_y_bia, "tu_lieu": tl,
         "ghep_hai_hang": ghep_hai_hang(anh, meta.get("category", "")),
         "thu_tu_anh_theo_loai": list(__import__("loai_tin").thu_tu_anh(meta.get("category", ""))),
         "so_dung_duoc": so_dung_duoc, "chua_nhin": chua_nhin,
         "xep_hang": ({k: xhs[0].get(k) for k in ("model", "hang", "site", "bang", "kieu", "duoc_nhac")}
                      if xhs else None),
         "so_xep_hang": len(xhs),
         "tin_xep_hang": tin_xep_hang,
         "chu_bai": (bp.get("chu") or "")[:20000],
         "nguon_path": str(nguon_path), "tieu_de_en": nguon.get("tieu_de_en", "")}
    return m
