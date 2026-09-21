#!/usr/bin/env python3
"""PHA VONG BU: kho mong thi di tim them — bao khac, bang xep hang, thuong hieu, khai niem.

Tach tu image_prepare.py 09/09/2026 (audit A1, di chuyen thuan — than ham giu y nguyen).
"""
import sys
from pathlib import Path

from PIL import Image

import image_eval
import image_provenance
import role
import env_load
import ranking
import state_paths

from prepare import decision_log
from prepare.browser import browser_pass
from prepare.common import MAX_IMAGE, _brand_of, _write_json, _domain
from prepare.source import _leading_proper_noun, _title_page, commons_images, candidate_social, candidate_static
from prepare.vision import classify
from prepare.download_filter import download_and_filter


MAX_ARTICLE_SOURCES = 6           # tran nguon bai gop (Google News + Bing News) truoc khi chup

def _supplement_source(nguon: dict, nguon_path: Path, source_pages: list, link: str) -> list:
    """Tieu de tieng Anh (mot fetch) va, khi con MONG hon `MAX_ARTICLE_SOURCES`, them
    bao tu Bing — lam TRUOC khi mo browser de browser ghe luon cac trang do. Tra
    `trang`.

    Ong Chu 13/09/2026: "cần kết hợp với bing news, vì thường những chủ đề nóng
    có rất nhiều tạp chí đưa tin, chỉ cần lấy hình từ các article đó ra, mỗi tạp
    chí một hình cũng dư material" — truoc day nguong la `< 3` (chi bu khi CON
    THIEU), qua thap voi tin nong: Google News thuong da co san 2-3 bao la dung
    nguong, Bing khong bao gio duoc hoi them dai co the CO NHIEU tap chi hon,
    va `_round_capture_source` (LOW-45) chi thu duoc bao nhieu trang thi `trang` co
    bay nhieu. Nang nguong + so luong hoi Bing de co NHIEU tap chi hon lam vat
    lieu, khong chi bu cho du."""
    # Tieu de TIENG ANH cua bai that (tin Vera/Nova mang tieu de tieng Viet):
    # mot fetch httpx; khong ra thi browser lay og:title sau.
    if not nguon.get("title_en"):
        nguon["title_en"] = _title_page(link)
        _write_json(nguon_path, nguon)
    # Bo nguon mong -> Bing News RSS bang tieu de tieng Anh (link chuyen huong HTTP
    # thuong, khong can browser). Lam TRUOC khi mo browser de browser ghe luon
    # cac trang bao nay lay anh. Ghi vao nguon json de tu_lieu (Miles) cung dung.
    if len(source_pages) < MAX_ARTICLE_SOURCES and nguon.get("title_en"):
        import article_sources
        co = {t.get("url") for t in source_pages}
        mien_co = {_domain(t.get("url", "")) for t in source_pages}
        them = article_sources.other_outlets_bing(nguon["title_en"], so=MAX_ARTICLE_SOURCES, bo_mien=tuple(mien_co))
        for t in them:
            if t["url"] not in co:
                nguon["pages"].append(t)
                co.add(t["url"])
        if them:
            _write_json(nguon_path, nguon)
            source_pages = nguon["pages"]
        print(f"[nguon] bing: +{len(them)} bao -> {len(source_pages)} trang", file=sys.stderr)
    return source_pages


def _extra_announcement_page(nguon: dict, nguon_path: Path, source_pages: list, tieu_de: str,
                        tom_tat: str = "") -> list:
    """TRANG CONG BO CHINH CHU cua model trong tin (LOW-21, Ong Chu 11/09/2026:
    "phai tim tat ca anh lien quan chu khong phai chi tim anh trong nguon topic,
    dac biet la nhung thong tin lien quan toi benchmark cua model"). Chay cho MOI
    tin nhac model cua hang trong watchlist, khong doi thieu anh — cung ly do
    voi `_round_brand`. Lam TRUOC khi mo browser de browser ghe trang do
    lay chart. Ghi vao nguon json de tu_lieu (Miles) cung dung. Tra `trang`."""
    import image_brand as th
    import ranking
    if any(t.get("kind") == "announcement" for t in source_pages):
        return source_pages
    # Lay ten model DAI NHAT tu ca hai tieu de, khong "en truoc vi thay" (LOW-34):
    # tieu de Viet giu nguyen "DeepSeek-V4.1-Flash" trong khi <title> HF chi ra "deepseek".
    import article_sources
    en = article_sources.strip_site_suffix(nguon.get("title_en") or "")
    models = sorted(set(ranking.extract_model(en) + ranking.extract_model(tieu_de)),
                    key=lambda t: (-len(t), t))
    hangs = th.vendors_in_story(f"{tieu_de} {en}", tom_tat) if models else []
    if not hangs:
        return source_pages
    mien_co = {_domain(t.get("url", "")) for t in source_pages}
    for h in hangs[:1]:
        cb = th.announcement_page(h, models)
        if not cb or _domain(cb["url"]) in mien_co or any(t.get("url") == cb["url"] for t in source_pages):
            continue
        nguon.setdefault("pages", []).append(cb)
        _write_json(nguon_path, nguon)
        print(f"[nguon] cong bo chinh chu: {cb['url'][:90]}", file=sys.stderr)
        return nguon["pages"]
    return source_pages


def _take_from_browser(source_pages: list, wd: Path, nguon: dict, nguon_path: Path, phien=None) -> tuple:
    """Mot phien chromium: tieu de, chu, anh/figure, bao khac; gop vao `nguon`.
    Tra (bp, trang)."""
    print("[browser] mo trang goc (tieu de, chu, anh, figure) + bao khac...", file=sys.stderr)
    bp = browser_pass(source_pages, wd, tim_them=len(source_pages) < 2, phien=phien)
    doi = False
    if bp["title_en"] and not nguon.get("title_en"):
        nguon["title_en"] = bp["title_en"]
        doi = True
    co = {t.get("url") for t in source_pages}
    for t in bp["extra_pages"]:
        if t["url"] not in co:
            nguon["pages"].append(t)
            co.add(t["url"])
            doi = True
    if doi:
        _write_json(nguon_path, nguon)
        source_pages = nguon["pages"]
    print(f"[browser] tieu de: {(nguon.get('title_en') or '')[:70]!r}; +{len(bp['extra_pages'])} bao; "
          f"{len(bp['cands'])} anh/figure; {len(bp['article_text'])} ky tu chu", file=sys.stderr)
    return bp, source_pages


def _capture_ranking(title: str, nguon: dict, tom: dict, link: str, meta: dict, bp: dict,
                   wd: Path, khong_browser: bool, phien=None) -> tuple:
    """Tin xep hang: chup bang tu chinh trang xep hang, khoanh model. Tra
    (xhs, tin_xep_hang); xhs [] khi khong phai tin xep hang / khong chup duoc.

    LAY NHIEU BANG khi chung do NANG LUC KHAC NHAU, khong chi mot (Ong Chu
    09/09/2026, dap lai de xuat gioi han con mot anh: "đã làm social media thì
    làm gì có chuyện bị giới hạn ở nguồn tư liệu" — vd tin GPT-Image-2.5 #1&#2
    CA "Text-to-Image Arena" LAN "Image Edit Arena", hai bang khong trung nhau).
    `ranking.find_and_capture_many` tu quyet dinh lay may bang qua co `independent`
    tren tung nguon trong registry."""
    # TIN XEP HANG (Ong Chu chot 06/09/2026): anh phai la bang/chart xep hang, chup
    # tu chinh trang xep hang (arena.ai, artificialanalysis.ai, tbench...), khoanh
    # dung model. Lam TRUOC moi buoc tim anh khac: day la anh chinh, khong thuong
    # luong. Khong chup duoc thi the du phong (ten model + #hang + logo + site).
    xhs: list = []
    tieu_de_xh = f"{title} {nguon.get('title_en') or ''}"
    tin_xep_hang = ranking.is_ranking_story(tieu_de_xh, tom.get("summary", ""))
    # Bang loai tin (story_type.py, Ong Chu 12/09/2026: "noi den model thi co them
    # hinh benchmark"): category MODEL/BENCHMARK ep chup bang du tieu de khong co
    # chu "#1"/"top" nao — truoc day chi regex tieu de quyet dinh.
    import story_type
    if story_type.is_ranking_story_type(meta.get("category")):
        tin_xep_hang = True
    if not khong_browser and tin_xep_hang:
        models = ranking.extract_model(nguon.get("title_en") or "") or ranking.extract_model(title)
        if models:
            ds = ranking.suggest_sources(tieu_de_xh, link, meta.get("via", ""), bp.get("article_text", ""))
            print(f"[xep_hang] tin xep hang: model={models[0]!r}, thu {', '.join(n['id'] for n in ds[:4])}...",
                  file=sys.stderr)
            # BOC. `find_and_capture_many` import playwright va launch chromium NGOAI
            # moi try cua chinh no (ranking.py:899,904), va `br.close()` khong
            # nam trong finally. `hermes update` lam mat playwright khoi venv
            # chung (da xay ra voi pymupdf) hay chromium chua cai la: tin THUONG
            # van ra manifest.json binh thuong, rieng tin XEP HANG giet ca engine
            # giua chung — khong manifest.json, va vai chay lai qua `chay()` chet y
            # het. Nhanh "khong co ma XH" (:743) da co san, cu roi ve do.
            try:
                xhs = ranking.find_and_capture_many(
                    models, ds, wd / state_paths.ORIGINAL_DIR, _brand_of(meta),
                    ranking.extract_rank(title, models[0]) or ranking.extract_rank(nguon.get("title_en") or "", models[0]),
                    in_log=lambda t: print(t, file=sys.stderr), phien_browser=phien)
            except Exception as e:                           # noqa: BLE001
                print(f"[xep_hang] HONG: {type(e).__name__}: {e} — di tiep khong co anh XH",
                      file=sys.stderr)
                xhs = []
        else:
            print("[xep_hang] tin xep hang nhung khong tach duoc ten model tu tieu de", file=sys.stderr)
    return xhs, tin_xep_hang


def _image_item_ranking(i: int, xh: dict) -> dict:
    """Mot ket qua chup xep hang -> mot muc trong danh sach `anh`, mang MA rieng
    (XH cho cai dau, XH2/XH3... cho cac cai sau — nhieu bang do NANG LUC KHAC
    NHAU cua cung model, xem `_capture_ranking`). Ham THUAN, tach 09/09/2026 de
    test duoc khong can chay ca `_gather_and_download_image` (goi mang, cham).

    Khong di qua `download_and_filter`: ham do luu lai PNG voi dau xuat xu cua no, se de
    mat dau `ranking_capture` + model/hang/site cua anh nay."""
    ma = "XH" if i == 0 else f"XH{i + 1}"
    mo_ta_xh = (f"bảng xếp hạng {xh['site']} ({xh['board']}) — {xh['model']}"
                + (f" #{xh['rank']}" if xh.get("rank") else "")
                + (" — THẺ DỰ PHÒNG (không chụp được bảng)" if xh["kind"] == "card" else ", đã khoanh hàng model"))
    return {"id": ma, "original_path": xh["file_path"], "url": xh["url"], "alt": mo_ta_xh[:120],
            "source": "ranking", "page_url": xh["url"], "domain": _domain(xh["url"]),
            "chart_hint": xh["kind"] != "card", "ranking": xh}


def _gather_and_download_image(title: str, link: str, nguon_path: Path, nguon: dict, source_pages: list,
                    bp: dict, wd: Path, xhs: list) -> list:
    """Ung vien (tim tinh + browser + bia arxiv) -> tai va loc -> chen anh XH ->
    bu Commons neu mong. Tra danh sach anh (chua phan loai).

    `xhs` co the co NHIEU hon mot khi tin len duoc nhieu bang xep hang do nang
    luc khac nhau (xem `_capture_ranking`) — moi cai mang MA rieng (XH, XH2, XH3)
    de vai chon dung tam, khong ghi de len nhau."""
    print(f"[anh] tim tinh qua {len(source_pages)} nguon...", file=sys.stderr)
    cands = candidate_social(link, wd) + candidate_static(title, link, nguon_path,
                                                     nguon.get("title_en", ""))
    co = {c["image_url"] for c in cands}
    for c in bp["cands"]:
        if c["image_url"] not in co:
            cands.append(c)
    # HINH THAT TRONG PAPER (Ong Chu 08/09/2026: "ngay dau paper co image ma
    # Kite khong dung de lam hero"). Bai arxiv thi anh that cua no la Figure 1,
    # Figure 2... do chinh nhom tac gia ve — nhung khong duong nao trong engine
    # cham toi chung: trang abs khong co figure, ban html xuat figure ra
    # <object> ma document.images khong thay. Boc thang tu PDF. Lam TRUOC nhanh
    # "khong con ung vien nao -> chup bia": trang bia (ten cong trinh + tac gia)
    # la duong cuoi, con bieu do ket qua moi la anh dat nhat cua tin.
    import arxiv_figures
    cands = arxiv_figures.candidate(link, wd / state_paths.ORIGINAL_DIR) + cands
    # arxiv khong anh: bia paper
    if not cands:
        import arxiv_cover
        pdf = arxiv_cover.is_arxiv(link)
        if pdf:
            out = wd / state_paths.ORIGINAL_DIR / "arxiv.png"
            data = arxiv_cover.download_pdf(pdf)
            bia = arxiv_cover.capture_cover(data) if data else None
            if bia is not None:
                out.parent.mkdir(parents=True, exist_ok=True)
                bia.save(out, "PNG", pnginfo=image_provenance.stamp_provenance("arxiv_cover"))
                cands.append({"image_url": str(out), "file_path": str(out), "alt": "trang bia paper",
                              "source": "arxiv_cover", "page_url": link, "score": 60})
    cands.sort(key=lambda c: -c.get("score", 0))
    anh = download_and_filter(cands, wd)
    for i, xh in enumerate(xhs):
        anh.insert(i, _image_item_ranking(i, xh))
    print(f"[anh] tai duoc {len(anh)} anh (chua phan loai/nhin)", file=sys.stderr)
    if len(anh) < 5:
        # Tin mong anh: them anh that tu Wikimedia Commons theo ten rieng dau
        # tieu de (tru so, san pham, su kien). Chi bu phan thieu.
        tk = _leading_proper_noun(nguon.get("title_en") or title)
        if tk:
            them = commons_images(tk, so=6)
            if them is None:
                print(f"[anh] anh_commons('{tk}') khong chay duoc -- bo qua nguon nay", file=sys.stderr)
                them = []
            print(f"[commons] '{tk}': {len(them)} anh", file=sys.stderr)
            if them:
                da = {a["url"] for a in anh}
                bo_sung = download_and_filter([c for c in them if c["image_url"] not in da], wd / "commons")
                for i, a in enumerate(bo_sung, start=len(anh) + 1):
                    if len(anh) >= MAX_IMAGE:
                        break
                    a["id"] = f"A{i}"
                    moi = wd / state_paths.ORIGINAL_DIR / f"{a['id']}.png"
                    Path(a["original_path"]).replace(moi)
                    a["original_path"] = str(moi)
                    a["commons"] = True
                    anh.append(a)
    return anh


def _round_widen_search(anh: list, source_pages: list, tieu_de_nhin: str, toi_thieu: int,
                   dung_duoc: list, wd: Path, phien=None) -> tuple:
    """VONG TIM RONG (Ong Chu 05/09/2026): kho mong thi engine phai di tim, khong
    bao "du" bang rac. Mot vong. Tra (anh, dung_duoc, chua_nhin)."""
    # VONG TIM RONG (Ong Chu 05/09/2026): kho mong thi engine phai di tim,
    # khong bao "du" bang rac. Them bao (Bing, loc lien quan, bo mien da co)
    # mo bang browser lay anh + Commons; tai, NHIN, dem lai. Mot vong.
    import article_sources
    mien_co = {_domain(t.get("url", "")) for t in source_pages} | {a.get("domain") for a in anh}
    them_bao = article_sources.other_outlets_bing(tieu_de_nhin, so=6, bo_mien=tuple(x for x in mien_co if x))[:4]
    # Tu LOW-12 vong nay con chay khi kho DU anh ma khong tam nao lam anh chinh
    # cua vai duoc — in "thieu (5/5)" luc do la noi doi nguoi doc log.
    ly_do = (f"thieu ({len(dung_duoc)}/{toi_thieu})" if len(dung_duoc) < toi_thieu
             else f"co {len(dung_duoc)} anh nhung khong tam nao lam anh chinh duoc")
    print(f"[tim rong] {ly_do}: +{len(them_bao)} bao moi"
          + (": " + ", ".join(_domain(t["url"]) for t in them_bao) if them_bao else ""), file=sys.stderr)
    wd2 = wd / state_paths.EXTRA_DIR
    cands2 = []
    if them_bao:
        bp2 = browser_pass([{"url": t["url"], "kind": "other_outlet"} for t in them_bao], wd2, tim_them=False, phien=phien)
        cands2 += bp2["cands"]
        # Noi ra tung buoc (12/09/2026, tin TSMC): vong nay ghe 4 bao moi ma
        # "+0 tai them", khong mot dong nao cho biet 0 la do trang khong co anh,
        # anh trung, hay tai hong — phai doan.
        print(f"[tim rong] browser boc {len(bp2['cands'])} ung vien tu {len(them_bao)} bao", file=sys.stderr)
    tk = _leading_proper_noun(tieu_de_nhin)
    # TIM NHU NGUOI (Ong Chu 12/09/2026, 7 link TSMC tim tay): anh web (Bing/
    # Yandex qua Chromium) + og:image bao chi VE thuc the — khong doi "cung tin".
    # Truy van = ten rieng dau tieu de (hang/san pham), khong co thi ca tieu de.
    q_web = tk or tieu_de_nhin
    if q_web:
        import find_image_web
        import press_entity_images
        cands2 += find_image_web.find_image_web(q_web, so=16, phien=phien)
        cands2 += press_entity_images.press_entity_images([q_web], bo_mien=tuple(x for x in mien_co if x))
    if tk:
        them_commons = commons_images(tk, so=6)
        if them_commons is None:
            print(f"[anh] anh_commons('{tk}') khong chay duoc -- bo qua nguon nay", file=sys.stderr)
            them_commons = []
        print(f"[tim rong] Commons '{tk}': {len(them_commons)} ung vien", file=sys.stderr)
        cands2 += them_commons
    else:
        print("[tim rong] khong co ten rieng dau tieu de -> khong hoi Commons", file=sys.stderr)
    da = {a["url"] for a in anh}
    n_truoc = len(cands2)
    cands2 = [c for c in cands2 if c["image_url"] not in da]
    if n_truoc != len(cands2):
        print(f"[tim rong] bo {n_truoc - len(cands2)} ung vien trung URL da co", file=sys.stderr)
    cands2.sort(key=lambda c: -c.get("score", 0))
    bo_sung = download_and_filter(cands2, wd2) if cands2 else []
    print(f"[tim rong] tai + loc: {len(bo_sung)} anh giu lai / {len(cands2)} ung vien", file=sys.stderr)
    n0 = len(anh)
    for i, a in enumerate(bo_sung, start=n0 + 1):
        if len(anh) >= MAX_IMAGE + 4:
            break
        a["id"] = f"A{i}"
        moi = wd / state_paths.ORIGINAL_DIR / f"{a['id']}.png"
        Path(a["original_path"]).replace(moi)
        a["original_path"] = str(moi)
        if a.get("source") == "commons":
            a["commons"] = True
        anh.append(classify(a, wd, tieu_de_nhin))
    dung_duoc = [a for a in anh if a["uses"] and a.get("relevant") is not False]
    chua_nhin = [a["id"] for a in anh if a.get("relevant") is None]
    print(f"[tim rong] sau vong: {len(dung_duoc)} anh DUNG DUOC / {len(anh)} "
          f"(+{len(anh) - n0} tai them)", file=sys.stderr)
    return anh, dung_duoc, chua_nhin


# LOW-263 (19/09/2026): tung dung chung cho ca _round_brand LAN _round_entity.
# _round_brand bo han sub-quota nay (xem chu thich o "_round_brand": trong tong
# cua carousel (MAX_IMAGE + 4) + round-robin giua cac hang da du chan "mot hang
# nuot het slot" roi, khong can them mot tran rieng danh cho "anh thuong hieu")
# — hang chi con Microsoft/Google... ma tin thieu tu lieu thi khong con bi bop
# truoc nua. _round_entity (nac cuoi, anh dai dien cho THUC THE trong tieu de,
# khac ban chat voi anh hang) van giu tran rieng, tach ten de khong dung chung
# so phan voi quyet dinh tren.
MAX_EXTRA_ENTITY_ = 4          # tran anh thuc the them vao mot bo (_round_entity)


def _count_kept(anh: list) -> int:
    """So anh engine con giu (LOW-267) — anh da bi loai khong chiem cho trong tran."""
    return sum(1 for a in anh if image_eval.system_kept(a))


XH_CONTEXT_EDGE_SOURCE = 3       # so bang xep hang thu khi lay anh bang lam boi canh


def _ranking_context_edge(hangs: list, wd: Path, brand: str, phien=None):
    """BANG XEP HANG lam anh BOI CANH cho tin thieu anh (Ong Chu 09/09/2026:
    "...anh chup tren cac bang xep hang cua model"). Khac `_capture_ranking`: kia
    chay cho TIN XEP HANG va anh la chu the bat buoc; day chay cho tin thuong
    ve mot hang lam model, chi de co mot tam thay hang do dang dung dau.

    Chi nhan anh CHUP THAT: `find_and_capture` het duong thi tu dung THE DU PHONG
    ("<model> #<hang>") — the do cho mot tin KHONG PHAI tin xep hang la bia ra
    mot thu hang khong ai noi. Tra ung vien hoac None."""
    import image_brand as th
    hs = [h for h in hangs if th.rank_has_model(h["key"])]
    if not hs:
        return None
    h = hs[0]
    try:
        # `suggest_sources` PHAI nam trong try cung: no doc bang TOPIC cua xep_hang,
        # va mot ban sua bang do dang do (them cot thu ba cho Image Edit Arena,
        # 09/09/2026) lam no nem ValueError. Day la nhanh BU anh — hong thi bo
        # qua, khong duoc keo ca engine chet giua chung nhu tin xep hang tung
        # lam (xem chu thich cua `_capture_ranking`).
        ds = ranking.suggest_sources("")[:XH_CONTEXT_EDGE_SOURCE]
        kq = ranking.find_and_capture([h["company"]], ds, wd / state_paths.RANKING_DIR, brand, None,
                                  in_log=lambda t: print(t, file=sys.stderr), phien_browser=phien)
    except Exception as e:                                   # noqa: BLE001
        print(f"[thuong hieu] bang xep hang HONG: {type(e).__name__}: {e}", file=sys.stderr)
        return None
    if not kq or kq.get("kind") == "card":
        print("[thuong hieu] khong bang nao co hang cua hang nay -> bo (khong dung the du phong)",
              file=sys.stderr)
        return None
    print(f"[thuong hieu] bang {kq['site']} ({kq['board']}): khop {kq['model']!r}", file=sys.stderr)
    return {"image_url": kq["file_path"], "file_path": kq["file_path"], "alt": f"bảng {kq['site']} — {kq['board']}",
            "source": "brand", "page_url": kq["url"], "score": 26, "chart_hint": True,
            "brand_match": {"company": h["company"], "key": h["key"], "kind": "ranking",
                            "site": kq["site"], "board": kq["board"], "keyword": kq["model"]}}


def _report_brand_empty(h: dict, wd: Path, phien=None) -> list:
    """Tìm BÁO THẬT theo tên hãng qua `article_sources.report_about_keyword` (không đòi
    "cùng một sự kiện" như `other_outlets_bing`, KHÔNG giới hạn thời gian) rồi quét
    ảnh như `_round_widen_search` (`browser_pass`, đã sửa LOW-45 phần 1 nên không
    còn vớ nhầm `<figure>` là chart).

    Nguyên tắc nguồn chốt 13/09/2026 (IMAGE_RULES §1.2d): CHẠY LUÔN cho mọi hãng
    tin nhắc tới, SONG SONG với Commons/Wikidata — không còn là phương án cuối
    khi Commons rỗng. "Không có bất kỳ cấm đoán nào về nguồn" ngoài ba điều đã
    ghi (không giới hạn thời gian/sự kiện, không giới hạn định dạng miễn rõ
    nét, chỉ tiếng Anh/Trung); Commons chỉ còn là MỘT trong nhiều nguồn, không
    còn được hỏi trước/độc quyền. Đo thật: Moonshot AI (QID Wikidata trống,
    0 ảnh) → tìm "Moonshot AI" ra báo thật, quét ra ảnh minh hoạ/logo dùng được.

    Gắn `brand_match` cho từng ứng viên để đi qua đúng câu hỏi con mắt và điểm
    theo loại tin như ảnh Commons/Wikidata. Không mạng/router → []."""
    import article_sources
    bao = article_sources.report_about_keyword(h["company"], so=4)
    if not bao:
        print(f"[thuong hieu] {h['key']}: khong tim duoc bao ve \"{h['company']}\"", file=sys.stderr)
        return []
    print(f"[thuong hieu] {h['key']}: Commons/Wikidata rong, thu {len(bao)} bao "
          f"({', '.join(_domain(b['url']) for b in bao)})", file=sys.stderr)
    bp = browser_pass([{"url": b["url"], "kind": "other_outlet"} for b in bao], wd, tim_them=False, phien=phien)
    ra = []
    for c in bp["cands"]:
        c["brand_match"] = {"company": h["company"], "key": h["key"], "kind": "photo",
                            "keyword": f"báo về {h['company']}"}
        ra.append(c)
    return ra


def _round_brand(anh: list, tieu_de_nhin: str, tom_tat: str, wd: Path,
                      toi_thieu: int = 5, khong_browser: bool = False, phien=None,
                      category: str = "") -> tuple:
    """Vong thuong hieu (xem `_round_brand_body`) co HAN GIO cho phan TIM: dat
    `image_brand.start_deadline()` truoc, go sau, va in tong giay cua vong (log
    `prepare.log` truoc day khong co moc gio nao). Ong Chu 20/09/2026: "them gioi han
    cho thoi gian tim anh" (LOW-264 bo sung). Han mem — xem `image_brand.BRAND_ROUND_SECONDS`."""
    import time
    import image_brand as th
    started = time.monotonic()
    th.start_deadline()
    try:
        return _round_brand_body(anh, tieu_de_nhin, tom_tat, wd, toi_thieu=toi_thieu,
                                 khong_browser=khong_browser, phien=phien, category=category)
    finally:
        th.clear_deadline()
        print(f"[thuong hieu] vong tim anh hang mat {time.monotonic() - started:.1f}s "
              f"(han mem {th.BRAND_ROUND_SECONDS}s)", file=sys.stderr)


def _round_brand_body(anh: list, tieu_de_nhin: str, tom_tat: str, wd: Path,
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

    Truoc vong nay chi co `anh_commons(_leading_proper_noun(...))`: mot cum ten rieng
    DAU tieu de, hoi bang ten tran. Tin hai hang ("Qualcomm ... with Amazon")
    khong bao gio hoi toi hang thu hai. Tra (anh, dung_duoc, chua_nhin)."""
    import image_brand as th
    hangs = th.vendors_in_story(tieu_de_nhin, tom_tat)
    # LOW-260: `vendors_in_story` phai giu THUAN (khong mang), nen hang lay tu
    # nhanh all_proper_nouns ngoai watchlist (khong co trong DISPLAY_NAME) duoc
    # xac nhan la cong ty that qua Wikidata O DAY, ngay truoc khi tieu ngan
    # sach tai/vision — tranh lap lai ca "Rules" (tu tieu de Title Case) lot
    # qua thanh mot "hang" gia.
    hangs = [h for h in hangs if h["key"] in th.DISPLAY_NAME
             or th.confirm_unlisted_vendor(h["key"], h["company"])]
    print("[thuong hieu] hang trong tin: " + (", ".join(h["company"] for h in hangs) or "khong ra"),
          file=sys.stderr)
    wd4 = wd / state_paths.BRAND_MATCH_DIR
    import story_type
    # LOW-337: tin MODEL/BENCHMARK — logo CUA MODEL (Qwen, khong phai Alibaba).
    tin_model = story_type.is_model_story(category)
    logo_model = th.model_logo_images(tieu_de_nhin, wd4) if tin_model else []
    if logo_model:
        print("[thuong hieu] logo model: " + ", ".join(c["brand_match"]["company"] for c in logo_model),
              file=sys.stderr)
    if not hangs and not logo_model:
        return anh, [a for a in anh if a["uses"] and a.get("relevant") is not False], \
            [a["id"] for a in anh if a.get("relevant") is None]
    cands = []
    for h in hangs:
        if th.deadline_passed():
            th.note_deadline(f"hang {h['key']} (chua bat dau)")
            break
        cands_h = th.vendor_images(h, wd=wd4 / h["key"])
        if not khong_browser and not th.deadline_passed(th.BROWSER_STEP_MIN_LEFT):
            # LUON tim them bao THAT theo ten hang, SONG SONG voi Commons/
            # Wikidata — khong con doi Commons rong moi chay (Ong Chu
            # 13/09/2026, chot nguyen tac nguon o IMAGE_RULES §1.2d: "ngoai
            # nguyen tac [khong gioi han thoi gian/su kien/nguon, chi tieng
            # Anh-Trung], khong co bat ky cam doan nao ve nguon anh" — Commons
            # chi con la MOT nguon, khong con doc quyen/duoc hoi truoc).
            cands_h = cands_h + _report_brand_empty(h, wd4 / h["key"], phien=phien)
        cands += cands_h
        # Bang loai tin: BUSINESS/M&A muon bieu do gia (chi hang niem yet).
        if (story_type.late(category, "stock") and not khong_browser
                and not th.deadline_passed(th.BROWSER_STEP_MIN_LEFT)):
            cands += th.image_has_ballot(h, wd4 / h["key"], phien=phien)
    if tin_model:
        # Logo hang me KHONG duoc dung cho tin model (Ong Chu 21/09/2026) — chi logo model.
        cands = [c for c in cands if (c.get("brand_match") or {}).get("kind") != "logo"] + logo_model
    # Diem theo LOAI TIN cong vao diem goc truoc khi sort: cung bo ung vien,
    # tin M&A day logo len truoc chan dung, tin LAB day tru so/founder len
    # truoc logo (story_type.BOARD_IMAGE_BY_TYPE, Ong Chu 12/09/2026).
    # LOW-270: logo QUÁ NHỎ trong khung (image_brand.LOGO_FILL_MIN) không được
    # điểm ưu tiên loại tin — xuống cuối, dưới cả cổ phiếu.
    for c in cands:
        bm = c.get("brand_match") or {}
        if not bm.get("small_logo"):
            c["score"] = c.get("score", 0) + story_type.score_by_type(category, bm.get("kind", "photo"))
    # `download_and_filter` tu ghi hop dong "tai ung vien THEO THU TU DIEM" — noi duy
    # nhat trong ca thang anh thuong hieu ma diem THAT SU khac nhau (anh noi/san
    # pham 28 > nguoi 24 > logo 18, dat o `image_brand._candidate`), nhung
    # bo sot sort nay tu dau (kieu tin nhieu hang: cands cua hang A duoc noi
    # TRUOC hang B bat ke loai anh, dung thu tu goi `vendor_images` chu khong theo
    # do "minh hoa duoc" nhieu hay it). `_round_widen_search` (:198) da lam dung.
    cands.sort(key=lambda c: -c.get("score", 0))
    da = {a["url"] for a in anh}
    cands = [c for c in cands if c["image_url"] not in da]
    bo_sung = download_and_filter(cands, wd4) if cands else []
    # CONG BANG GIUA CAC HANG khi cat: neu cu giu nguyen thu tu diem (tren) roi
    # lay N tam dau, tin nhieu hang de bi mot hang co LOAI anh diem cao (vd
    # "nguoi": chan dung CEO) nuot het slot cua hang con lai chi co "anh"
    # thuong diem thap hon. Do that 13/09/2026 (Ong Chu: "bai nhac toi ca
    # Anthropic va Moonshot nhung chi co anh Anthropic, kha mat can doi"): tin
    # Anthropic+Alibaba+Moonshot ra 2+2+1 ung vien da tai, Anthropic (chan
    # dung) + Alibaba (tru so) chiem het 4 slot, ung vien Moonshot (mot anh
    # that tu TechCrunch) diem thap hon bi cat truoc khi vao brief — dung o
    # day, SAU khi tai (khong dung thu tu tai cua `download_and_filter`), chi
    # doi lai THU TU CHON trong luc cat: gop theo hang ("key"), giu nguyen
    # diem-giam-dan TRONG tung hang, roi XEN KE (round-robin) giua cac hang —
    # moi hang co it nhat mot ung vien vao truoc khi hang nao duoc ung vien
    # thu hai. LOW-263 (19/09/2026): khong con sub-quota rieng cho "anh
    # thuong hieu" (`MAX_EXTRA_BRAND_` cu) — vong nay chi con dung TRAN TUYET
    # DOI cua ca carousel (`MAX_IMAGE + 4`) lam diem dung; round-robin o day
    # van la thu bao dam mot hang khong nuot het tran do khi co nhieu hang,
    # con tin CHI mot hang thi hang do duoc lay toi da so anh tran do cho phep.
    theo_hang: dict = {}
    for a in bo_sung:
        khoa = (a.get("brand_match") or {}).get("key") or f"_khac_{id(a)}"
        theo_hang.setdefault(khoa, []).append(a)
    bo_sung = []
    con = list(theo_hang.values())
    while any(con):
        for nhom in con:
            if nhom:
                bo_sung.append(nhom.pop(0))
    # LOW-267 (19/09/2026): tran dem anh engine CON GIU (`image_eval.system_kept`),
    # KHONG dem ca anh da bi loai. Do that draft "Nha nghien cuu dung Claude tan
    # cong OpenAI": vong tim rong (Yandex "Researchers") de lai 12 anh, 7 anh da
    # bi loai (phong lab, toa nha vo danh) — dem `len(anh)` la cham tran 12 nen
    # 3 chan dung Dario Amodei CO TEN tu Wikidata da tai ve bi bo sach
    # ("+0 anh"), Dre chi con Sam Altman va chong hai tam Sam len mot slide.
    n0 = len(anh)
    for i, a in enumerate(bo_sung, start=n0 + 1):
        if _count_kept(anh) >= MAX_IMAGE + 4:
            break
        a["id"] = f"A{i}"
        moi = wd / state_paths.ORIGINAL_DIR / f"{a['id']}.png"
        Path(a["original_path"]).replace(moi)
        a["original_path"] = str(moi)
        anh.append(classify(a, wd, tieu_de_nhin))
    dung_duoc = [a for a in anh if a["uses"] and a.get("relevant") is not False]
    if (len(dung_duoc) < toi_thieu and not khong_browser and _count_kept(anh) < MAX_IMAGE + 4
            and not th.deadline_passed(th.BROWSER_STEP_MIN_LEFT)):
        # `env_load.brand_long()`, KHONG PHAI os.environ["CT_BRAND"] thang: CT_BRAND
        # la ten NGAN cho thu muc state ("blog"), con `card.set_brand` doi
        # slug DAI ("donniechublog") — bat 09/09/2026 khi chay lai draft
        # "gpt-image-2.5-sunburst...": truyen thang CT_BRAND nem SystemExit
        # "Khong biet thuong hieu 'blog'", giet ca `prepare_article()`. Cung mot loi
        # lap lai o image_brand.py, sua chung mot cho o env_load.brand_long().
        c = _ranking_context_edge(hangs, wd4, env_load.brand_long(), phien=phien)
        if c:
            them = download_and_filter([c], wd4 / state_paths.BOARD_DIR)
            for a in them[:1]:
                a["id"] = f"A{len(anh) + 1}"
                moi = wd / state_paths.ORIGINAL_DIR / f"{a['id']}.png"
                Path(a["original_path"]).replace(moi)
                a["original_path"] = str(moi)
                anh.append(classify(a, wd, tieu_de_nhin))
        dung_duoc = [a for a in anh if a["uses"] and a.get("relevant") is not False]
    chua_nhin = [a["id"] for a in anh if a.get("relevant") is None]
    print(f"[thuong hieu] sau vong: +{len(anh) - n0} anh, "
          f"{sum(1 for a in dung_duoc if a.get('brand_match'))} thuong hieu dung duoc",
          file=sys.stderr)
    return anh, dung_duoc, chua_nhin


# Ong Chu 13/09/2026, dua 6 anh chup man hinh 6 bao khac nhau cung mot tin TSMC:
# *"ai noi voi ban la chi duoc chup tu mot trang nguon duy nhat... 1 article hot
# thi co hang van to bao khap the gioi dua tin, ban chi cap 6 trong so do ve roi
# dat quote va text len ma cung phai nghi sao?"*. Truoc do vong nay chup TOI DA 3
# trang va `break` ngay sau tam DAU TIEN — ca vong chi bao gio ra 1 anh.
# 12 chu khong phai 6: do that 13/09/2026 tren 8 bao cung tin cua tin TSMC, chi
# 4 trang chup duoc (3 trang khong do ra khoi lead — anh hero lazy/bo cuc la,
# 1 trang chan bot 403). Ti le trung ~50%, nen muon 6 slide phai thu ~12 bao.
MAX_PAGE_CAPTURE = 12


def _round_capture_source(anh: list, link: str, source_pages: list, wd: Path,
                     khong_browser: bool = False, phien=None, tieu_de: str = "") -> tuple:
    """VONG CHUP TRANG NGUON (Ong Chu 06/09/2026, nhac lai 12/09): tin khong co
    anh dung duoc thi CHUP CHINH TRANG NGUON o khung dien thoai va cat lay khoi
    lead (anh chinh + tit), TRUOC khi ha xuong anh khai niem Commons.

    Vi sao nam TRUOC `_round_concept`: khoi lead la mot vat THAT cua chinh tin —
    anh khai niem thi khong. Tin "AI giai toan gioi, nen toan hoc thi lech chuan"
    (12/09/2026) khong co anh rieng nen roi thang xuong khai niem va ra mot tam
    day mang phong may, chang lien quan gi bai. Luat mobile da co tu 06/09 nhung
    chi song trong `ranking.py` (trang bang xep hang), khong ai bac sang duong
    anh cua tin thuong.

    Mot vong, toi da `MAX_PAGE_CAPTURE` trang — THU HET, khong dung o trang
    DAU TIEN qua duoc cong nua (LOW-45, Ong Chu 13/09/2026: do that ca Moonshot/
    Kimi K3, TechCrunch rot chat luong nhung trang thu hai qua cong ngay la mot
    anh minh hoa chung chung, trong khi cac trang con lai trong `trang` — bao
    khac cung tin, LOW-33 — rat co the co anh that cua nguoi sang lap ma vong cu
    CHUA BAO GIO thu toi vi da dung o trang thu hai). Sau khi thu het, chon BIA
    la ung vien qua cong DAU TIEN theo thu tu ma KHONG CO MAT NGUOI — anh co mat
    van qua cong nhung khong len duoc bia (IMAGE_RULES §6 doi khai "subject" ma
    Kite chua co truong do), giu lam `than` thay vi bo phi. Tra (anh, dung_duoc,
    chua_nhin)."""
    def _result():
        return anh, [a for a in anh if a["uses"] and a.get("relevant") is not False], \
            [a["id"] for a in anh if a.get("relevant") is None]

    if khong_browser:
        print("[chup nguon] --khong-browser: bo qua vong nay", file=sys.stderr)
        return _result()
    import capture_page
    urls, da = [], set()
    for u in [link] + [t.get("url", "") for t in (source_pages or [])]:
        if u and u not in da:
            da.add(u)
            urls.append(u)
    # Kho URL mong hon tran chup -> tu hoi them BAO CUNG TIN (Bing News). Truoc
    # day vong nay chi an theo `trang` co san: tin hot co hang tram bao dua ma
    # `_supplement_source` chi bo sung khi `len(trang) < 3`, nen thuong chi co 3 URL.
    if len(urls) < MAX_PAGE_CAPTURE and tieu_de:
        import article_sources
        mien_co = tuple(_domain(u) for u in urls if _domain(u))
        them = article_sources.other_outlets_bing(tieu_de, so=MAX_PAGE_CAPTURE - len(urls),
                                       bo_mien=mien_co)
        for t in them:
            if t["url"] not in da:
                da.add(t["url"])
                urls.append(t["url"])
        print(f"[chup nguon] +{len(them)} bao cung tin de chup"
              + (": " + ", ".join(_domain(t["url"]) for t in them) if them else ""), file=sys.stderr)
    wd5 = wd / state_paths.CAPTURE_SOURCE_DIR
    # LOAI TRUNG (Ong Chu 13/09/2026, xem carousel that: "có đến 3 ảnh giống hệt
    # nhau về nội dung, góc máy, bố cục. việc này không được phép"): nhieu bao
    # dung CHUNG mot anh photo-wire (AP/Reuters/Getty) cho cung mot tin — chup
    # tung trang rieng le khong qua `download_and_filter` nen KHONG bao gio duoc so trung
    # dHash nhu duong tai anh binh thuong. So tam chup MOI voi: (1) moi anh da
    # co san trong `anh` (tu vong khac), (2) cac tam DA chup trong CHINH vong nay.
    da_hash = []
    for a0 in anh:
        try:
            da_hash.append(role.active_rules().dhash(Image.open(a0["original_path"]).convert("RGB")))
        except Exception:                                    # noqa: BLE001
            pass
    for u in urls[:MAX_PAGE_CAPTURE]:
        tam = wd5 / (_domain(u).replace(".", "_") + ".png")
        c = capture_page.capture_lead_mobile(u, tam, phien=phien)
        if not c:
            continue
        # BAO KHAC phai CUNG TIN moi duoc lam "anh cua chinh bai" (LOW-33). Truoc
        # 12/09/2026 muc nay mien kiem — "day la trang cua CHINH tin" — nhung
        # `trang` gom ca bao khac do Bing khop bang 2 tu, va the DeepSeek-V4.1-Flash
        # ra anh hero cua bai "Hugging Face robot duck is already a hit". Bai goc
        # (`link`) van duoc tin; tit khong doc duoc thi khong ket luan, cho qua.
        if u != link and tieu_de and c.get("page_title"):
            import article_sources
            if not article_sources.same_story(tieu_de, c["page_title"]):
                print(f"[chup nguon] {_domain(u)}: tít {c['page_title'][:60]!r} KHÔNG cùng tin "
                      f"với {tieu_de[:50]!r} — bỏ, không phải bài gốc", file=sys.stderr)
                Path(tam).unlink(missing_ok=True)
                continue
        try:
            h = role.active_rules().dhash(Image.open(tam).convert("RGB"))
        except Exception:                                    # noqa: BLE001
            h = None
        if h is not None:
            trung = next((h2 for h2 in da_hash if role.active_rules().is_near_duplicate(h, h2)), None)
            if trung is not None:
                print(f"[chup nguon] {_domain(u)}: TRÙNG ảnh đã có (cùng photo-wire, "
                      f"lệch {bin(h ^ trung).count('1')} bit) — bỏ", file=sys.stderr)
                Path(tam).unlink(missing_ok=True)
                continue
            da_hash.append(h)
        a = {"id": f"A{len(anh) + 1}", "original_path": str(tam), "url": u, "page_url": u,
             "domain": _domain(u), "score": 0, "chart_hint": False, **c}
        moi = wd / state_paths.ORIGINAL_DIR / f"{a['id']}.png"
        moi.parent.mkdir(parents=True, exist_ok=True)
        # DEM NEN DEN (Ong Chu 13/09/2026, sua lai cung ngay): tam chup khoi lead
        # thuong la anh NGANG, de nguyen thi dinh luat "ngang phai ghep doi hoac
        # cat_ngang" va thanh tam le khong dung duoc. Dem xong no la 4:5 dung,
        # dung MOT MINH lam mot slide. Mau dem la DEN co dinh (khong sample mau
        # nen trang cua trang nguon) - carousel toi dung nen den + chu trang, dem
        # trang tao khoang trang lac long giua anh va khung, buoc carousel.py
        # phai phu them lop mo (_layer_if_can) len tren de chu doc duoc ("vet
        # nhat"). Dem den tu dau: khop luon voi nen anh, khong con khoang trang,
        # khong can lop phu nua.
        try:
            capture_page.count_background(tam, moi, "#000000")
            # GIU LAI `tam` (ti le tu nhien, chua dem vien) thay vi xoa (LOW-262):
            # renderer full-bleed cua Kite (render_edu.py) tu lo full-width fit/crop
            # rieng, dua no anh da dem vien den (quy uoc cua carousel.py/Dre) thi
            # vien do la pixel that, bi trai theo luon len slide. `unpadded_path`
            # la loi ra cho renderer do — `kite_submit.py` uu tien dung no.
            a["padding_color"] = "#000000"
            a["unpadded_path"] = str(tam)
        except Exception as e:                               # noqa: BLE001
            print(f"[chup nguon] {_domain(u)}: dem nen hong ({type(e).__name__}), giu tam goc",
                  file=sys.stderr)
            Path(a["original_path"]).replace(moi)
        a["original_path"] = str(moi)
        # Hoi CHAT LUONG, khong hoi lai "co lien quan" (LOW-45, 12/09/2026):
        # truoc day tieu_de rong = KHONG hoi vision, ep thang lien_quan=True vi
        # "day la trang cua CHINH tin". Dung ve TOPIC, nhung bo qua het CHAT
        # LUONG — do that 12/09: anh hero that cua bai Moonshot/Kimi K3 la mot
        # anh bao Getty chup nghieng man hinh App Store, van len bia du xau.
        # `chup_nguon=True` doi description_image hoi CAU RIENG (chi chat luong, xem
        # docstring), khong dung cau mac dinh (se hoi lai ca "co dung chu de"
        # — thua, va co the rot vi ly do sai). Rong tieu_de (hiem, ca xep_hang
        # cu) van skip vision nhu cu.
        a = classify(a, wd, tieu_de, chup_nguon=True) if tieu_de else classify(a, wd, "")
        if a.get("relevant") is None:
            a["relevant"] = True           # khong hoi duoc (rong/router hong) -> giu y cu, khong chan oan
            decision_log.note(a, "capture_source_forced", "keep", "vision_unavailable_keep_hero",
                              "khong hoi duoc vision cho anh hero trang nguon -> giu")
        a["description"] = a.get("description") or "ảnh hero của chính bài gốc, chụp ở khung điện thoại"
        # `classify` doc mot anh chup trang la "chart/screenshot" (nen trang,
        # nhieu chu) roi dan nhan KHONG LAM BIA — dung cho chart cua nguoi khac,
        # sai cho tam nay: Ong Chu 12/09/2026 chot "cat lay khoi lead roi lam
        # bia". Mo lai dung bia, TRU khi co mat nguoi: cong mat (IMAGE_RULES §6)
        # doi khai `subject`, ma spec cua Kite khong co truong do.
        a["notes"] = [g for g in a["notes"] if "KHÔNG làm bìa" not in g]
        # KHOI TIT (trang khong co anh hero) la NAC CUOI, sau khai niem (Ong Chu
        # 12/09/2026 xem bia toan chu-de-chu: "thieu idea den the a?"). Giu anh
        # trong `anh` nhung KHONG tinh la dung duoc; `capability_block_headline` mo lai lam
        # bia chi khi khai niem cung rong.
        if a.get("capture_kind") == "headline":
            a["uses"] = []
            a["notes"].insert(0, "📰 KHỐI TÍT CHỤP TỪ TRANG NGUỒN (trang không có ảnh hero) — "
                                   "chỉ làm bìa khi không còn ảnh nào khác")
            anh.append(a)
            print(f"[chup nguon] {a['id']} <- {a['domain']} khoi tit ({a['w']}x{a['h']}), de dau",
                  file=sys.stderr)
            break
        a["notes"].insert(0, "📰 ẢNH HERO CHỤP TỪ TRANG NGUỒN — ảnh chính của bài trên "
                               f"{a['domain']}, chụp ở khung điện thoại; caption ghi "
                               f"\"… · via {a['domain']}\"")
        anh.append(a)
        # ROT chat luong (LOW-45) hoac CO MAT NGUOI (IMAGE_RULES §6, xem duoi) deu
        # KHONG dung lai o day: THU HET moi URL (khong dung o trang DAU TIEN qua
        # cong nua, LOW-45 phan 2) roi moi chon anh nao len BIA sau vong lap —
        # giu chua tam nay lai, gan tam "than" tam thoi, roi quyet dinh that o
        # duoi khi da biet toan bo ung vien. (Thay cho bo dem n_chup cu — ban
        # feat/org-id-multitenant tach truoc LOW-45 phan 2, chua co vong chon
        # bia nay.)
        a["uses"] = [] if a.get("relevant") is False else ["body"]
        if a.get("relevant") is False:
            print(f"[chup nguon] {a['id']} <- {a['domain']} ({a['w']}x{a['h']}) RỚT chất lượng "
                  f"({a.get('description', '')[:60]!r}), thử URL khác", file=sys.stderr)
        else:
            print(f"[chup nguon] {a['id']} <- {a['domain']} ({a['w']}x{a['h']}) qua cổng"
                  + (", CÓ mặt người" if a.get("faces") else "")
                  + (f", nền {a['padding_color']}" if a.get("padding_color") else "")
                  + ", thử thêm để so ảnh", file=sys.stderr)
    # CHON BIA sau khi da thu HET cac URL (LOW-45, Ong Chu 13/09/2026): trong so
    # cac ung vien QUA CONG (lien_quan True, khong phai khoi tit), uu tien tam
    # KHONG CO MAT NGUOI dau tien theo thu tu thu — tam co mat khong len bia
    # duoc vi cong mat (IMAGE_RULES §6) doi khai "subject" ma Kite chua co truong
    # do, nhung VAN giu lai lam `than` thay vi bo phi (do that: anh founder that
    # cua Yang Zhilin tren cac bao khac ve Moonshot/Kimi K3 rat co the nam trong
    # so nay — truoc ban va nay bi bo qua hoan toan vi vong lap dung som).
    ung_vien = [a for a in anh if a.get("source") == "capture_source" and a.get("capture_kind") != "headline"
                and a.get("relevant") is True]
    khong_mat = [a for a in ung_vien if not a.get("faces")]
    if khong_mat:
        bia = khong_mat[0]
        bia["uses"] = ["cover_article_hero", "body"]
        print(f"[chup nguon] {bia['id']} <- {bia['domain']} lên BÌA (không mặt người)", file=sys.stderr)
    elif ung_vien:
        print(f"[chup nguon] {len(ung_vien)} ảnh qua cổng đều CÓ mặt người vô danh với Kite "
              "(thiếu \"subject\") — không tấm nào lên bìa, giữ làm thân", file=sys.stderr)
    if not any(a.get("capture_kind") == "headline" for a in anh) and not ung_vien:
        print("[chup nguon] khong trang nao do duoc khoi lead", file=sys.stderr)
    return _result()


def capability_block_headline(anh: list) -> tuple:
    """Nấc cuối cùng: mở khối tít đã chụp (`capture_kind == "headline"`) làm bìa khi thực thể
    và khái niệm đều rỗng. Thuần. Trả (anh, dung_duoc, chua_nhin)."""
    for a in anh:
        if a.get("capture_kind") == "headline" and not a["uses"] and not a.get("faces"):
            a["uses"] = ["cover_headline_block", "body"]
            print(f"[chup nguon] {a['id']}: nang khoi tit lam bia (nac cuoi)", file=sys.stderr)
            break
    return anh, [a for a in anh if a["uses"] and a.get("relevant") is not False], \
        [a["id"] for a in anh if a.get("relevant") is None]


def _round_concept(anh: list, tieu_de_nhin: str, tom_tat: str, wd: Path,
                    category: str = "") -> tuple:
    """VONG KHAI NIEM (Ong Chu 07/09/2026): tin khong co anh rieng (thieu, hoac
    khong tam nao lam bia duoc) thi engine tim ANH THAT theo khai niem cua tin —
    co/ban do nuoc duoc nhac, datacenter cho tin compute... — nhu Dre tung tu
    lam khi con web_search. Chi Commons, chi bia/hero, dung sau anh rieng cua tin.
    Mot vong. Tra (anh, dung_duoc, chua_nhin)."""
    import image_concept
    import image_brand as th
    import story_type
    # Tu khoa do LOAI TIN ep truoc heuristic: co nuoc cua HANG trong tin (LAB/
    # INFRA — truoc day co chi ra khi tieu de nhac ten nuoc), datacenter/nha may
    # cho INFRA du tieu de khong khop TOPIC. Bang: story_type.py (12/09/2026).
    them = []
    if story_type.late(category, "company_country_flag"):
        for h in th.vendors_in_story(tieu_de_nhin, tom_tat):
            nuoc = story_type.country_of(h["key"])
            if nuoc and f"flag of {nuoc}" not in them:
                them.append(f"flag of {nuoc}")
    if story_type.late(category, "infrastructure_concept"):
        them += [t for t in story_type.KEYWORD_LOWER_LAYER if t not in them]
    if story_type.late(category, "stock_exchange"):
        them.append("stock exchange trading floor")
    tks = image_concept.keyword_concept(tieu_de_nhin, tom_tat, them=them)
    print("[khai niem] tu khoa: " + (", ".join(f"'{t['keyword']}'" for t in tks) or "khong ra"),
          file=sys.stderr)
    if not tks:
        return anh, [a for a in anh if a["uses"] and a.get("relevant") is not False], \
            [a["id"] for a in anh if a.get("relevant") is None]
    cands = []
    for t in tks:
        them_kn = image_concept.image_concept(t["keyword"], t.get("reason", ""), so=2)
        if them_kn is None:
            print(f"[anh] image_concept('{t['keyword']}') khong chay duoc -- bo qua nguon nay", file=sys.stderr)
            them_kn = []
        cands += them_kn
    da = {a["url"] for a in anh}
    cands = [c for c in cands if c["image_url"] not in da]
    wd3 = wd / state_paths.CONCEPT_DIR
    bo_sung = download_and_filter(cands, wd3) if cands else []
    n0 = len(anh)
    for i, a in enumerate(bo_sung, start=n0 + 1):
        if len(anh) >= MAX_IMAGE + 6:
            break
        a["id"] = f"A{i}"
        moi = wd / state_paths.ORIGINAL_DIR / f"{a['id']}.png"
        Path(a["original_path"]).replace(moi)
        a["original_path"] = str(moi)
        anh.append(classify(a, wd, tieu_de_nhin))
    dung_duoc = [a for a in anh if a["uses"] and a.get("relevant") is not False]
    chua_nhin = [a["id"] for a in anh if a.get("relevant") is None]
    print(f"[khai niem] sau vong: +{len(anh) - n0} anh, "
          f"{sum(1 for a in dung_duoc if a.get('concept'))} khai niem dung duoc", file=sys.stderr)
    return anh, dung_duoc, chua_nhin


def _round_entity(anh: list, tieu_de_nhin: str, wd: Path) -> tuple:
    """NAC CUOI, KHONG BAO GIO RONG (Ong Chu 12/09/2026, dong LOW-35: "ko co ly gi
    ma ko tim duoc anh minh hoa dau, day la 2026, moi thu ban can deu co san").
    Anh dai dien cua chinh cac THUC THE trong tieu de — Wikipedia pageimages +
    Commons theo cum ten rieng (entity_images.py). Chi chay khi cac nac tren van
    de bo thieu; qua classify + con mat nhu moi anh. Tra (anh, dung_duoc, chua_nhin)."""
    import entity_images
    models = ranking.extract_model(tieu_de_nhin)
    cands = entity_images.entity_images(tieu_de_nhin, models)
    print("[thuc the] " + (", ".join(sorted({c["entity"]["name"] for c in cands})) or "khong ra thuc the nao"),
          file=sys.stderr)
    da = {a["url"] for a in anh}
    cands = [c for c in cands if c["image_url"] not in da]
    cands.sort(key=lambda c: -c.get("score", 0))
    wd6 = wd / state_paths.ENTITY_DIR
    bo_sung = download_and_filter(cands, wd6) if cands else []
    n0 = len(anh)
    for i, a in enumerate(bo_sung, start=n0 + 1):
        if len(anh) >= MAX_IMAGE + 6 or len(anh) - n0 >= MAX_EXTRA_ENTITY_:
            break
        a["id"] = f"A{i}"
        moi = wd / state_paths.ORIGINAL_DIR / f"{a['id']}.png"
        moi.parent.mkdir(parents=True, exist_ok=True)
        Path(a["original_path"]).replace(moi)
        a["original_path"] = str(moi)
        # Hoi con mat cau cua ANH KHAI NIEM ("co dung la <ten>, chup that, hop bia"),
        # KHONG hoi "co phai anh cua su viec" — do that tren may chu 12/09/2026: anh
        # Wikipedia cua Anthropic 2865x2952 bi tu choi vi cau mac dinh hoi sai. Cung
        # bay ma anh khai niem da tranh tu 07/09 (docstring description_image).
        a["concept"] = {"keyword": a["entity"]["name"], "reason": "thực thể trong tiêu đề"}
        a = classify(a, wd, tieu_de_nhin)
        anh.append(entity_images.label_entity(a))
    dung_duoc = [a for a in anh if a["uses"] and a.get("relevant") is not False]
    chua_nhin = [a["id"] for a in anh if a.get("relevant") is None]
    print(f"[thuc the] sau vong: +{len(anh) - n0} anh", file=sys.stderr)
    return anh, dung_duoc, chua_nhin
