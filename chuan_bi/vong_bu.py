#!/usr/bin/env python3
"""PHA VONG BU: kho mong thi di tim them — bao khac, bang xep hang, thuong hieu, khai niem.

Tach tu anh_chuan_bi.py 09/09/2026 (audit A1, di chuyen thuan — than ham giu y nguyen).
"""
import sys
from pathlib import Path


import luat_anh
import env_load
import xep_hang

from chuan_bi.browser import browser_pass
from chuan_bi.chung import TOI_DA_ANH, _brand_cua, _ghi_json, _mien
from chuan_bi.nguon import _ten_rieng_dau, _tieu_de_trang, anh_commons, ung_vien_social, ung_vien_tinh
from chuan_bi.nhin import phan_loai
from chuan_bi.tai_loc import tai_va_loc


def _bo_sung_nguon(nguon: dict, nguon_path: Path, trang: list, link: str) -> list:
    """Tieu de tieng Anh (mot fetch) va, khi bo nguon mong, them bao tu Bing —
    lam TRUOC khi mo browser de browser ghe luon cac trang do. Tra `trang`."""
    # Tieu de TIENG ANH cua bai that (tin Vera/Nova mang tieu de tieng Viet):
    # mot fetch httpx; khong ra thi browser lay og:title sau.
    if not nguon.get("tieu_de_en"):
        nguon["tieu_de_en"] = _tieu_de_trang(link)
        _ghi_json(nguon_path, nguon)
    # Bo nguon mong -> Bing News RSS bang tieu de tieng Anh (link chuyen huong HTTP
    # thuong, khong can browser). Lam TRUOC khi mo browser de browser ghe luon
    # cac trang bao nay lay anh. Ghi vao nguon json de tu_lieu (Miles) cung dung.
    if len(trang) < 3 and nguon.get("tieu_de_en"):
        import nguon_bai
        co = {t.get("url") for t in trang}
        mien_co = {_mien(t.get("url", "")) for t in trang}
        them = nguon_bai.bao_khac_bing(nguon["tieu_de_en"], so=4, bo_mien=tuple(mien_co))
        for t in them:
            if t["url"] not in co:
                nguon["trang"].append(t)
                co.add(t["url"])
        if them:
            _ghi_json(nguon_path, nguon)
            trang = nguon["trang"]
        print(f"[nguon] bing: +{len(them)} bao -> {len(trang)} trang", file=sys.stderr)
    return trang


def _them_trang_cong_bo(nguon: dict, nguon_path: Path, trang: list, tieu_de: str,
                        tom_tat: str = "") -> list:
    """TRANG CONG BO CHINH CHU cua model trong tin (LOW-21, Ong Chu 11/09/2026:
    "phai tim tat ca anh lien quan chu khong phai chi tim anh trong nguon topic,
    dac biet la nhung thong tin lien quan toi benchmark cua model"). Chay cho MOI
    tin nhac model cua hang trong watchlist, khong doi thieu anh — cung ly do
    voi `_vong_thuong_hieu`. Lam TRUOC khi mo browser de browser ghe trang do
    lay chart. Ghi vao nguon json de tu_lieu (Miles) cung dung. Tra `trang`."""
    import anh_thuong_hieu as th
    import xep_hang
    if any(t.get("loai") == "công bố" for t in trang):
        return trang
    # Lay ten model DAI NHAT tu ca hai tieu de, khong "en truoc vi thay" (LOW-34):
    # tieu de Viet giu nguyen "DeepSeek-V4.1-Flash" trong khi <title> HF chi ra "deepseek".
    import nguon_bai
    en = nguon_bai.bo_hau_to_site(nguon.get("tieu_de_en") or "")
    models = sorted(set(xep_hang.tach_model(en) + xep_hang.tach_model(tieu_de)),
                    key=lambda t: (-len(t), t))
    hangs = th.hang_trong_tin(f"{tieu_de} {en}", tom_tat) if models else []
    if not hangs:
        return trang
    mien_co = {_mien(t.get("url", "")) for t in trang}
    for h in hangs[:1]:
        cb = th.trang_cong_bo(h, models)
        if not cb or _mien(cb["url"]) in mien_co or any(t.get("url") == cb["url"] for t in trang):
            continue
        nguon.setdefault("trang", []).append(cb)
        _ghi_json(nguon_path, nguon)
        print(f"[nguon] cong bo chinh chu: {cb['url'][:90]}", file=sys.stderr)
        return nguon["trang"]
    return trang


def _lay_tu_browser(trang: list, wd: Path, nguon: dict, nguon_path: Path, phien=None) -> tuple:
    """Mot phien chromium: tieu de, chu, anh/figure, bao khac; gop vao `nguon`.
    Tra (bp, trang)."""
    print("[browser] mo trang goc (tieu de, chu, anh, figure) + bao khac...", file=sys.stderr)
    bp = browser_pass(trang, wd, tim_them=len(trang) < 2, phien=phien)
    doi = False
    if bp["tieu_de_en"] and not nguon.get("tieu_de_en"):
        nguon["tieu_de_en"] = bp["tieu_de_en"]
        doi = True
    co = {t.get("url") for t in trang}
    for t in bp["trang_them"]:
        if t["url"] not in co:
            nguon["trang"].append(t)
            co.add(t["url"])
            doi = True
    if doi:
        _ghi_json(nguon_path, nguon)
        trang = nguon["trang"]
    print(f"[browser] tieu de: {(nguon.get('tieu_de_en') or '')[:70]!r}; +{len(bp['trang_them'])} bao; "
          f"{len(bp['cands'])} anh/figure; {len(bp['chu'])} ky tu chu", file=sys.stderr)
    return bp, trang


def _chup_xep_hang(title: str, nguon: dict, tom: dict, link: str, meta: dict, bp: dict,
                   wd: Path, khong_browser: bool, phien=None) -> tuple:
    """Tin xep hang: chup bang tu chinh trang xep hang, khoanh model. Tra
    (xhs, tin_xep_hang); xhs [] khi khong phai tin xep hang / khong chup duoc.

    LAY NHIEU BANG khi chung do NANG LUC KHAC NHAU, khong chi mot (Ong Chu
    09/09/2026, dap lai de xuat gioi han con mot anh: "đã làm social media thì
    làm gì có chuyện bị giới hạn ở nguồn tư liệu" — vd tin GPT-Image-2.5 #1&#2
    CA "Text-to-Image Arena" LAN "Image Edit Arena", hai bang khong trung nhau).
    `xep_hang.tim_va_chup_nhieu` tu quyet dinh lay may bang qua co `doc_lap`
    tren tung nguon trong registry."""
    # TIN XEP HANG (Ong Chu chot 06/09/2026): anh phai la bang/chart xep hang, chup
    # tu chinh trang xep hang (arena.ai, artificialanalysis.ai, tbench...), khoanh
    # dung model. Lam TRUOC moi buoc tim anh khac: day la anh chinh, khong thuong
    # luong. Khong chup duoc thi the du phong (ten model + #hang + logo + site).
    xhs: list = []
    tieu_de_xh = f"{title} {nguon.get('tieu_de_en') or ''}"
    tin_xep_hang = xep_hang.la_tin_xep_hang(tieu_de_xh, tom.get("summary", ""))
    # Bang loai tin (loai_tin.py, Ong Chu 12/09/2026: "noi den model thi co them
    # hinh benchmark"): category MODEL/BENCHMARK ep chup bang du tieu de khong co
    # chu "#1"/"top" nao — truoc day chi regex tieu de quyet dinh.
    import loai_tin
    if loai_tin.muon(meta.get("category"), "xep_hang"):
        tin_xep_hang = True
    if not khong_browser and tin_xep_hang:
        models = xep_hang.tach_model(nguon.get("tieu_de_en") or "") or xep_hang.tach_model(title)
        if models:
            ds = xep_hang.goi_y_nguon(tieu_de_xh, link, meta.get("via", ""), bp.get("chu", ""))
            print(f"[xep_hang] tin xep hang: model={models[0]!r}, thu {', '.join(n['ma'] for n in ds[:4])}...",
                  file=sys.stderr)
            # BOC. `tim_va_chup_nhieu` import playwright va launch chromium NGOAI
            # moi try cua chinh no (xep_hang.py:899,904), va `br.close()` khong
            # nam trong finally. `hermes update` lam mat playwright khoi venv
            # chung (da xay ra voi pymupdf) hay chromium chua cai la: tin THUONG
            # van ra xong.json binh thuong, rieng tin XEP HANG giet ca engine
            # giua chung — khong xong.json, va vai chay lai qua `chay()` chet y
            # het. Nhanh "khong co ma XH" (:743) da co san, cu roi ve do.
            try:
                xhs = xep_hang.tim_va_chup_nhieu(
                    models, ds, wd / "goc", _brand_cua(meta),
                    xep_hang.tach_hang(title, models[0]) or xep_hang.tach_hang(nguon.get("tieu_de_en") or "", models[0]),
                    in_log=lambda t: print(t, file=sys.stderr), phien_browser=phien)
            except Exception as e:                           # noqa: BLE001
                print(f"[xep_hang] HONG: {type(e).__name__}: {e} — di tiep khong co anh XH",
                      file=sys.stderr)
                xhs = []
        else:
            print("[xep_hang] tin xep hang nhung khong tach duoc ten model tu tieu de", file=sys.stderr)
    return xhs, tin_xep_hang


def _anh_muc_xep_hang(i: int, xh: dict) -> dict:
    """Mot ket qua chup xep hang -> mot muc trong danh sach `anh`, mang MA rieng
    (XH cho cai dau, XH2/XH3... cho cac cai sau — nhieu bang do NANG LUC KHAC
    NHAU cua cung model, xem `_chup_xep_hang`). Ham THUAN, tach 09/09/2026 de
    test duoc khong can chay ca `_gom_va_tai_anh` (goi mang, cham).

    Khong di qua `tai_va_loc`: ham do luu lai PNG voi dau xuat xu cua no, se de
    mat dau `chup_xep_hang` + model/hang/site cua anh nay."""
    ma = "XH" if i == 0 else f"XH{i + 1}"
    mo_ta_xh = (f"bảng xếp hạng {xh['site']} ({xh['bang']}) — {xh['model']}"
                + (f" #{xh['hang']}" if xh.get("hang") else "")
                + (" — THẺ DỰ PHÒNG (không chụp được bảng)" if xh["kieu"] == "the" else ", đã khoanh hàng model"))
    return {"ma": ma, "goc": xh["tep"], "url": xh["url"], "alt": mo_ta_xh[:120],
            "tu": "xep_hang", "trang": xh["url"], "mien": _mien(xh["url"]),
            "hint_chart": xh["kieu"] != "the", "xep_hang": xh}


def _gom_va_tai_anh(title: str, link: str, nguon_path: Path, nguon: dict, trang: list,
                    bp: dict, wd: Path, xhs: list) -> list:
    """Ung vien (tim tinh + browser + bia arxiv) -> tai va loc -> chen anh XH ->
    bu Commons neu mong. Tra danh sach anh (chua phan loai).

    `xhs` co the co NHIEU hon mot khi tin len duoc nhieu bang xep hang do nang
    luc khac nhau (xem `_chup_xep_hang`) — moi cai mang MA rieng (XH, XH2, XH3)
    de vai chon dung tam, khong ghi de len nhau."""
    print(f"[anh] tim tinh qua {len(trang)} nguon...", file=sys.stderr)
    cands = ung_vien_social(link, wd) + ung_vien_tinh(title, link, nguon_path,
                                                     nguon.get("tieu_de_en", ""))
    co = {c["anh"] for c in cands}
    for c in bp["cands"]:
        if c["anh"] not in co:
            cands.append(c)
    # HINH THAT TRONG PAPER (Ong Chu 08/09/2026: "ngay dau paper co image ma
    # Kite khong dung de lam hero"). Bai arxiv thi anh that cua no la Figure 1,
    # Figure 2... do chinh nhom tac gia ve — nhung khong duong nao trong engine
    # cham toi chung: trang abs khong co figure, ban html xuat figure ra
    # <object> ma document.images khong thay. Boc thang tu PDF. Lam TRUOC nhanh
    # "khong con ung vien nao -> chup bia": trang bia (ten cong trinh + tac gia)
    # la duong cuoi, con bieu do ket qua moi la anh dat nhat cua tin.
    import arxiv_hinh
    cands = arxiv_hinh.ung_vien(link, wd / "goc") + cands
    # arxiv khong anh: bia paper
    if not cands:
        import arxiv_bia
        pdf = arxiv_bia.la_arxiv(link)
        if pdf:
            out = wd / "goc" / "arxiv.png"
            data = arxiv_bia.tai_pdf(pdf)
            bia = arxiv_bia.chup_bia(data) if data else None
            if bia is not None:
                out.parent.mkdir(parents=True, exist_ok=True)
                bia.save(out, "PNG", pnginfo=luat_anh.dong_dau("arxiv_bia"))
                cands.append({"anh": str(out), "tep": str(out), "alt": "trang bia paper",
                              "tu": "arxiv_bia", "trang": link, "diem": 60})
    cands.sort(key=lambda c: -c.get("diem", 0))
    anh = tai_va_loc(cands, wd)
    for i, xh in enumerate(xhs):
        anh.insert(i, _anh_muc_xep_hang(i, xh))
    print(f"[anh] tai duoc {len(anh)} anh (chua phan loai/nhin)", file=sys.stderr)
    if len(anh) < 5:
        # Tin mong anh: them anh that tu Wikimedia Commons theo ten rieng dau
        # tieu de (tru so, san pham, su kien). Chi bu phan thieu.
        tk = _ten_rieng_dau(nguon.get("tieu_de_en") or title)
        if tk:
            them = anh_commons(tk, so=6)
            if them is None:
                print(f"[anh] anh_commons('{tk}') khong chay duoc -- bo qua nguon nay", file=sys.stderr)
                them = []
            print(f"[commons] '{tk}': {len(them)} anh", file=sys.stderr)
            if them:
                da = {a["url"] for a in anh}
                bo_sung = tai_va_loc([c for c in them if c["anh"] not in da], wd / "commons")
                for i, a in enumerate(bo_sung, start=len(anh) + 1):
                    if len(anh) >= TOI_DA_ANH:
                        break
                    a["ma"] = f"A{i}"
                    moi = wd / "goc" / f"{a['ma']}.png"
                    Path(a["goc"]).replace(moi)
                    a["goc"] = str(moi)
                    a["commons"] = True
                    anh.append(a)
    return anh


def _vong_tim_rong(anh: list, trang: list, tieu_de_nhin: str, toi_thieu: int,
                   dung_duoc: list, wd: Path, phien=None) -> tuple:
    """VONG TIM RONG (Ong Chu 05/09/2026): kho mong thi engine phai di tim, khong
    bao "du" bang rac. Mot vong. Tra (anh, dung_duoc, chua_nhin)."""
    # VONG TIM RONG (Ong Chu 05/09/2026): kho mong thi engine phai di tim,
    # khong bao "du" bang rac. Them bao (Bing, loc lien quan, bo mien da co)
    # mo bang browser lay anh + Commons; tai, NHIN, dem lai. Mot vong.
    import nguon_bai
    mien_co = {_mien(t.get("url", "")) for t in trang} | {a.get("mien") for a in anh}
    them_bao = nguon_bai.bao_khac_bing(tieu_de_nhin, so=6, bo_mien=tuple(x for x in mien_co if x))[:4]
    # Tu LOW-12 vong nay con chay khi kho DU anh ma khong tam nao lam anh chinh
    # cua vai duoc — in "thieu (5/5)" luc do la noi doi nguoi doc log.
    ly_do = (f"thieu ({len(dung_duoc)}/{toi_thieu})" if len(dung_duoc) < toi_thieu
             else f"co {len(dung_duoc)} anh nhung khong tam nao lam anh chinh duoc")
    print(f"[tim rong] {ly_do}: +{len(them_bao)} bao moi"
          + (": " + ", ".join(_mien(t["url"]) for t in them_bao) if them_bao else ""), file=sys.stderr)
    wd2 = wd / "them"
    cands2 = []
    if them_bao:
        bp2 = browser_pass([{"url": t["url"], "loai": "báo"} for t in them_bao], wd2, tim_them=False, phien=phien)
        cands2 += bp2["cands"]
    tk = _ten_rieng_dau(tieu_de_nhin)
    if tk:
        them_commons = anh_commons(tk, so=6)
        if them_commons is None:
            print(f"[anh] anh_commons('{tk}') khong chay duoc -- bo qua nguon nay", file=sys.stderr)
            them_commons = []
        cands2 += them_commons
    da = {a["url"] for a in anh}
    cands2 = [c for c in cands2 if c["anh"] not in da]
    cands2.sort(key=lambda c: -c.get("diem", 0))
    bo_sung = tai_va_loc(cands2, wd2) if cands2 else []
    n0 = len(anh)
    for i, a in enumerate(bo_sung, start=n0 + 1):
        if len(anh) >= TOI_DA_ANH + 4:
            break
        a["ma"] = f"A{i}"
        moi = wd / "goc" / f"{a['ma']}.png"
        Path(a["goc"]).replace(moi)
        a["goc"] = str(moi)
        if a.get("tu") == "commons":
            a["commons"] = True
        anh.append(phan_loai(a, wd, tieu_de_nhin))
    dung_duoc = [a for a in anh if a["dung"] and a.get("lien_quan") is not False]
    chua_nhin = [a["ma"] for a in anh if a.get("lien_quan") is None]
    print(f"[tim rong] sau vong: {len(dung_duoc)} anh DUNG DUOC / {len(anh)} "
          f"(+{len(anh) - n0} tai them)", file=sys.stderr)
    return anh, dung_duoc, chua_nhin


TOI_DA_THEM_TH = 4          # tran anh thuong hieu them vao mot bo


XH_BOI_CANH_NGUON = 3       # so bang xep hang thu khi lay anh bang lam boi canh


def _xep_hang_boi_canh(hangs: list, wd: Path, brand: str, phien=None):
    """BANG XEP HANG lam anh BOI CANH cho tin thieu anh (Ong Chu 09/09/2026:
    "...anh chup tren cac bang xep hang cua model"). Khac `_chup_xep_hang`: kia
    chay cho TIN XEP HANG va anh la chu the bat buoc; day chay cho tin thuong
    ve mot hang lam model, chi de co mot tam thay hang do dang dung dau.

    Chi nhan anh CHUP THAT: `tim_va_chup` het duong thi tu dung THE DU PHONG
    ("<model> #<hang>") — the do cho mot tin KHONG PHAI tin xep hang la bia ra
    mot thu hang khong ai noi. Tra ung vien hoac None."""
    import anh_thuong_hieu as th
    hs = [h for h in hangs if th.hang_co_model(h["khoa"])]
    if not hs:
        return None
    h = hs[0]
    try:
        # `goi_y_nguon` PHAI nam trong try cung: no doc bang CHU_DE cua xep_hang,
        # va mot ban sua bang do dang do (them cot thu ba cho Image Edit Arena,
        # 09/09/2026) lam no nem ValueError. Day la nhanh BU anh — hong thi bo
        # qua, khong duoc keo ca engine chet giua chung nhu tin xep hang tung
        # lam (xem chu thich cua `_chup_xep_hang`).
        ds = xep_hang.goi_y_nguon("")[:XH_BOI_CANH_NGUON]
        kq = xep_hang.tim_va_chup([h["hang"]], ds, wd / "xh", brand, None,
                                  in_log=lambda t: print(t, file=sys.stderr), phien_browser=phien)
    except Exception as e:                                   # noqa: BLE001
        print(f"[thuong hieu] bang xep hang HONG: {type(e).__name__}: {e}", file=sys.stderr)
        return None
    if not kq or kq.get("kieu") == "the":
        print("[thuong hieu] khong bang nao co hang cua hang nay -> bo (khong dung the du phong)",
              file=sys.stderr)
        return None
    print(f"[thuong hieu] bang {kq['site']} ({kq['bang']}): khop {kq['model']!r}", file=sys.stderr)
    return {"anh": kq["tep"], "tep": kq["tep"], "alt": f"bảng {kq['site']} — {kq['bang']}",
            "tu": "thuong_hieu", "trang": kq["url"], "diem": 26, "hint_chart": True,
            "thuong_hieu": {"hang": h["hang"], "khoa": h["khoa"], "loai": "xep_hang",
                            "site": kq["site"], "bang": kq["bang"], "tu_khoa": kq["model"]}}


def _vong_thuong_hieu(anh: list, tieu_de_nhin: str, tom_tat: str, wd: Path,
                      toi_thieu: int = 5, khong_browser: bool = False, phien=None,
                      category: str = "") -> tuple:
    """VONG THUONG HIEU (Ong Chu 09/09/2026: "Dre van chua tu tim them hinh lien
    quan khi lam cac noi dung co Big Brand"): tin ve hang lon thi engine hoi
    Commons/Wikidata anh THAT cua chinh hang — logo, chan dung founder/CEO, tru
    so, toa nha, campus — TRUOC khi ha xuong anh khai niem chung chung. Mot vong.

    Nguoi goi chay vong nay cho MOI tin, khong doi toi luc thieu anh (Ong Chu
    10/09/2026: "Dre van ko chiu di tim cac hinh lien quan nhu logo, brand,
    founder, tru so... cua chu de duoc nhac toi" — lan thu hai cua cung mot loi).
    `toi_thieu` vi vay chi con dieu khien MOT thu: nhanh mo browser di chup bang
    xep hang o duoi, phan dat nhat, van chi chay khi that su thieu anh.

    Truoc vong nay chi co `anh_commons(_ten_rieng_dau(...))`: mot cum ten rieng
    DAU tieu de, hoi bang ten tran. Tin hai hang ("Qualcomm ... with Amazon")
    khong bao gio hoi toi hang thu hai. Tra (anh, dung_duoc, chua_nhin)."""
    import anh_thuong_hieu as th
    hangs = th.hang_trong_tin(tieu_de_nhin, tom_tat)
    print("[thuong hieu] hang trong tin: " + (", ".join(h["hang"] for h in hangs) or "khong ra"),
          file=sys.stderr)
    if not hangs:
        return anh, [a for a in anh if a["dung"] and a.get("lien_quan") is not False], \
            [a["ma"] for a in anh if a.get("lien_quan") is None]
    wd4 = wd / "thuong_hieu"
    import loai_tin
    cands = []
    for h in hangs:
        cands += th.anh_hang(h, wd=wd4 / h["khoa"])
        # Bang loai tin: BUSINESS/M&A muon bieu do gia (chi hang niem yet).
        if loai_tin.muon(category, "co_phieu") and not khong_browser:
            cands += th.anh_co_phieu(h, wd4 / h["khoa"], phien=phien)
    # Diem theo LOAI TIN cong vao diem goc truoc khi sort: cung bo ung vien,
    # tin M&A day logo len truoc chan dung, tin LAB day tru so/founder len
    # truoc logo (loai_tin.BANG_ANH_THEO_LOAI, Ong Chu 12/09/2026).
    for c in cands:
        c["diem"] = c.get("diem", 0) + loai_tin.diem_theo_loai(
            category, (c.get("thuong_hieu") or {}).get("loai", "anh"))
    # `tai_va_loc` tu ghi hop dong "tai ung vien THEO THU TU DIEM" — noi duy
    # nhat trong ca thang anh thuong hieu ma diem THAT SU khac nhau (anh noi/san
    # pham 28 > nguoi 24 > logo 18, dat o `anh_thuong_hieu._ung_vien`), nhung
    # bo sot sort nay tu dau (kieu tin nhieu hang: cands cua hang A duoc noi
    # TRUOC hang B bat ke loai anh, dung thu tu goi `anh_hang` chu khong theo
    # do "minh hoa duoc" nhieu hay it). `_vong_tim_rong` (:198) da lam dung.
    cands.sort(key=lambda c: -c.get("diem", 0))
    da = {a["url"] for a in anh}
    cands = [c for c in cands if c["anh"] not in da]
    bo_sung = tai_va_loc(cands, wd4) if cands else []
    n0 = len(anh)
    for i, a in enumerate(bo_sung, start=n0 + 1):
        if len(anh) >= TOI_DA_ANH + 4 or len(anh) - n0 >= TOI_DA_THEM_TH:
            break
        a["ma"] = f"A{i}"
        moi = wd / "goc" / f"{a['ma']}.png"
        Path(a["goc"]).replace(moi)
        a["goc"] = str(moi)
        anh.append(phan_loai(a, wd, tieu_de_nhin))
    dung_duoc = [a for a in anh if a["dung"] and a.get("lien_quan") is not False]
    if len(dung_duoc) < toi_thieu and not khong_browser and len(anh) - n0 < TOI_DA_THEM_TH:
        # `env_load.brand_dai()`, KHONG PHAI os.environ["CT_BRAND"] thang: CT_BRAND
        # la ten NGAN cho thu muc state ("blog"), con `card.dat_thuong_hieu` doi
        # slug DAI ("donniechublog") — bat 09/09/2026 khi chay lai draft
        # "gpt-image-2.5-sunburst...": truyen thang CT_BRAND nem SystemExit
        # "Khong biet thuong hieu 'blog'", giet ca `chuan_bi()`. Cung mot loi
        # lap lai o anh_thuong_hieu.py, sua chung mot cho o env_load.brand_dai().
        c = _xep_hang_boi_canh(hangs, wd4, env_load.brand_dai(), phien=phien)
        if c:
            them = tai_va_loc([c], wd4 / "bang")
            for a in them[:1]:
                a["ma"] = f"A{len(anh) + 1}"
                moi = wd / "goc" / f"{a['ma']}.png"
                Path(a["goc"]).replace(moi)
                a["goc"] = str(moi)
                anh.append(phan_loai(a, wd, tieu_de_nhin))
        dung_duoc = [a for a in anh if a["dung"] and a.get("lien_quan") is not False]
    chua_nhin = [a["ma"] for a in anh if a.get("lien_quan") is None]
    print(f"[thuong hieu] sau vong: +{len(anh) - n0} anh, "
          f"{sum(1 for a in dung_duoc if a.get('thuong_hieu'))} thuong hieu dung duoc",
          file=sys.stderr)
    return anh, dung_duoc, chua_nhin


TOI_DA_TRANG_CHUP = 3          # thu toi da 3 trang: bai goc roi hai bao khac


def _vong_chup_nguon(anh: list, link: str, trang: list, wd: Path,
                     khong_browser: bool = False, phien=None, tieu_de: str = "") -> tuple:
    """VONG CHUP TRANG NGUON (Ong Chu 06/09/2026, nhac lai 12/09): tin khong co
    anh dung duoc thi CHUP CHINH TRANG NGUON o khung dien thoai va cat lay khoi
    lead (anh chinh + tit), TRUOC khi ha xuong anh khai niem Commons.

    Vi sao nam TRUOC `_vong_khai_niem`: khoi lead la mot vat THAT cua chinh tin —
    anh khai niem thi khong. Tin "AI giai toan gioi, nen toan hoc thi lech chuan"
    (12/09/2026) khong co anh rieng nen roi thang xuong khai niem va ra mot tam
    day mang phong may, chang lien quan gi bai. Luat mobile da co tu 06/09 nhung
    chi song trong `xep_hang.py` (trang bang xep hang), khong ai bac sang duong
    anh cua tin thuong.

    Mot vong, toi da `TOI_DA_TRANG_CHUP` trang, lay tam DAU TIEN chup duoc.
    Tra (anh, dung_duoc, chua_nhin)."""
    def _ra():
        return anh, [a for a in anh if a["dung"] and a.get("lien_quan") is not False], \
            [a["ma"] for a in anh if a.get("lien_quan") is None]

    if khong_browser:
        print("[chup nguon] --khong-browser: bo qua vong nay", file=sys.stderr)
        return _ra()
    import chup_trang
    urls, da = [], set()
    for u in [link] + [t.get("url", "") for t in (trang or [])]:
        if u and u not in da:
            da.add(u)
            urls.append(u)
    wd5 = wd / "chup_nguon"
    for u in urls[:TOI_DA_TRANG_CHUP]:
        tam = wd5 / (_mien(u).replace(".", "_") + ".png")
        c = chup_trang.chup_lead_mobile(u, tam, phien=phien)
        if not c:
            continue
        # BAO KHAC phai CUNG TIN moi duoc lam "anh cua chinh bai" (LOW-33). Truoc
        # 12/09/2026 muc nay mien kiem — "day la trang cua CHINH tin" — nhung
        # `trang` gom ca bao khac do Bing khop bang 2 tu, va the DeepSeek-V4.1-Flash
        # ra anh hero cua bai "Hugging Face robot duck is already a hit". Bai goc
        # (`link`) van duoc tin; tit khong doc duoc thi khong ket luan, cho qua.
        if u != link and tieu_de and c.get("tit_trang"):
            import nguon_bai
            if not nguon_bai.cung_tin(tieu_de, c["tit_trang"]):
                print(f"[chup nguon] {_mien(u)}: tít {c['tit_trang'][:60]!r} KHÔNG cùng tin "
                      f"với {tieu_de[:50]!r} — bỏ, không phải bài gốc", file=sys.stderr)
                Path(tam).unlink(missing_ok=True)
                continue
        a = {"ma": f"A{len(anh) + 1}", "goc": str(tam), "url": u, "trang": u,
             "mien": _mien(u), "diem": 0, "hint_chart": False, **c}
        moi = wd / "goc" / f"{a['ma']}.png"
        moi.parent.mkdir(parents=True, exist_ok=True)
        Path(a["goc"]).replace(moi)
        a["goc"] = str(moi)
        # tieu_de rong = KHONG hoi vision, dung nhu anh xep hang: day la trang
        # cua CHINH tin, "co lien quan bai khong" thi khong phai cau hoi.
        a = phan_loai(a, wd, "")
        a["lien_quan"] = True
        a["mo_ta"] = "ảnh hero của chính bài gốc, chụp ở khung điện thoại"
        # `phan_loai` doc mot anh chup trang la "chart/screenshot" (nen trang,
        # nhieu chu) roi dan nhan KHONG LAM BIA — dung cho chart cua nguoi khac,
        # sai cho tam nay: Ong Chu 12/09/2026 chot "cat lay khoi lead roi lam
        # bia". Mo lai dung bia, TRU khi co mat nguoi: cong mat (LUAT_ANH §6)
        # doi khai `nhan_vat`, ma spec cua Kite khong co truong do.
        a["ghi_chu"] = [g for g in a["ghi_chu"] if "KHÔNG làm bìa" not in g]
        if not a.get("mat"):
            a["dung"] = ["bìa (ảnh hero của chính bài gốc)", "thân"]
        a["ghi_chu"].insert(0, "📰 ẢNH HERO CHỤP TỪ TRANG NGUỒN — ảnh chính của bài trên "
                               f"{a['mien']}, chụp ở khung điện thoại; caption ghi "
                               f"\"… · via {a['mien']}\"")
        anh.append(a)
        print(f"[chup nguon] {a['ma']} <- {a['mien']} ({a['w']}x{a['h']})", file=sys.stderr)
        break
    else:
        print("[chup nguon] khong trang nao do duoc khoi lead", file=sys.stderr)
    return _ra()


def _vong_khai_niem(anh: list, tieu_de_nhin: str, tom_tat: str, wd: Path,
                    category: str = "") -> tuple:
    """VONG KHAI NIEM (Ong Chu 07/09/2026): tin khong co anh rieng (thieu, hoac
    khong tam nao lam bia duoc) thi engine tim ANH THAT theo khai niem cua tin —
    co/ban do nuoc duoc nhac, datacenter cho tin compute... — nhu Dre tung tu
    lam khi con web_search. Chi Commons, chi bia/hero, dung sau anh rieng cua tin.
    Mot vong. Tra (anh, dung_duoc, chua_nhin)."""
    import anh_khai_niem
    import anh_thuong_hieu as th
    import loai_tin
    # Tu khoa do LOAI TIN ep truoc heuristic: co nuoc cua HANG trong tin (LAB/
    # INFRA — truoc day co chi ra khi tieu de nhac ten nuoc), datacenter/nha may
    # cho INFRA du tieu de khong khop CHU_DE. Bang: loai_tin.py (12/09/2026).
    them = []
    if loai_tin.muon(category, "co_nuoc_hang"):
        for h in th.hang_trong_tin(tieu_de_nhin, tom_tat):
            nuoc = loai_tin.nuoc_cua(h["khoa"])
            if nuoc and f"flag of {nuoc}" not in them:
                them.append(f"flag of {nuoc}")
    if loai_tin.muon(category, "khai_niem_ha_tang"):
        them += [t for t in loai_tin.TU_KHOA_HA_TANG if t not in them]
    if loai_tin.muon(category, "san_giao_dich"):
        them.append("stock exchange trading floor")
    tks = anh_khai_niem.tu_khoa_khai_niem(tieu_de_nhin, tom_tat, them=them)
    print("[khai niem] tu khoa: " + (", ".join(f"'{t['tu_khoa']}'" for t in tks) or "khong ra"),
          file=sys.stderr)
    if not tks:
        return anh, [a for a in anh if a["dung"] and a.get("lien_quan") is not False], \
            [a["ma"] for a in anh if a.get("lien_quan") is None]
    cands = []
    for t in tks:
        them_kn = anh_khai_niem.anh_khai_niem(t["tu_khoa"], t.get("ly_do", ""), so=2)
        if them_kn is None:
            print(f"[anh] anh_khai_niem('{t['tu_khoa']}') khong chay duoc -- bo qua nguon nay", file=sys.stderr)
            them_kn = []
        cands += them_kn
    da = {a["url"] for a in anh}
    cands = [c for c in cands if c["anh"] not in da]
    wd3 = wd / "khai_niem"
    bo_sung = tai_va_loc(cands, wd3) if cands else []
    n0 = len(anh)
    for i, a in enumerate(bo_sung, start=n0 + 1):
        if len(anh) >= TOI_DA_ANH + 6:
            break
        a["ma"] = f"A{i}"
        moi = wd / "goc" / f"{a['ma']}.png"
        Path(a["goc"]).replace(moi)
        a["goc"] = str(moi)
        anh.append(phan_loai(a, wd, tieu_de_nhin))
    dung_duoc = [a for a in anh if a["dung"] and a.get("lien_quan") is not False]
    chua_nhin = [a["ma"] for a in anh if a.get("lien_quan") is None]
    print(f"[khai niem] sau vong: +{len(anh) - n0} anh, "
          f"{sum(1 for a in dung_duoc if a.get('khai_niem'))} khai niem dung duoc", file=sys.stderr)
    return anh, dung_duoc, chua_nhin
