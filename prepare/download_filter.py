#!/usr/bin/env python3
"""PHA TAI & LOC: tai bytes ung vien (song song), loc rac/trung/do hoa, cat san.

Tach tu image_prepare.py 09/09/2026 (audit A1, di chuyen thuan — than ham giu y nguyen).
"""
import io
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import httpx
from PIL import Image

import role
import scan_common
import env_load                                              # noqa: E402
import state_paths

from prepare import decision_log
from prepare.common import MAX_IMAGE, _original_domain, _hdr, _domain

# `url_junk`/`short_side_drop` KHONG con la hang so module-level (LOW-182,
# 16/09/2026): tieu chi gio di theo vai (`role.active_rules()`), ma vai chi
# biet duoc SAU khi `image_prepare.prepare_article` doc xong sidecar — truoc
# do o day chi la hang so import-time nen luon la ban cua vai dau tien chay
# trong tien trinh. Doc truc tiep trong `download_and_filter` moi lan can.


MAX_DOWNLOAD = 14             # ung vien thu tai (co cai hong/trung)


DOWNLOAD_MAX_BYTE = 14_000_000


# ---- 2. anh -----------------------------------------------------------------
def _download_bytes(url: str) -> bytes | None:
    # Cong host noi bo. URL o day den tu `src` cua HTML bai bao va tu trang tim
    # kiem — khong phai tu ta. Mot `<img src="http://127.0.0.1:9121/...">` (hay
    # mot 302 tro ve do) truoc 06/09/2026 duoc tai ve, di qua vision, roi vao
    # bang anh cua vai. Kiem CA sau chuyen huong, nhu article_extract.
    if not scan_common.url_hide_whole(url):
        print(f"[tai] bo qua URL noi bo: {str(url)[:80]}", file=sys.stderr)
        return None
    try:
        with httpx.stream("GET", url, headers=_hdr(url), timeout=40,
                          follow_redirects=True) as r:
            if r.status_code != 200 or not scan_common.url_hide_whole(r.url):
                print(f"[tai] {str(url)[:70]}: HTTP {r.status_code}"
                      + ("" if scan_common.url_hide_whole(r.url) else " (chuyen huong vao dia chi noi bo)"),
                      file=sys.stderr)
                return None
            buf = b""
            for chunk in r.iter_bytes(65536):
                buf += chunk
                if len(buf) > DOWNLOAD_MAX_BYTE:
                    print(f"[tai] {str(url)[:70]}: qua {DOWNLOAD_MAX_BYTE // 1_000_000} MB, bo", file=sys.stderr)
                    return None
            return buf
    except Exception as e:                                   # noqa: BLE001
        # Truoc audit lượt 2 (C-r2-2): `return None` khong log — mat DNS/proxy thi
        # 5 ung vien hong ra 0 dong stderr, engine ket luan "tai duoc 0 anh" ->
        # so_dung_duoc=0 -> tu chuyen Kite, khong dau vet loi moi truong nao.
        print(f"[tai] {str(url)[:70]}: {type(e).__name__}: {e!r}", file=sys.stderr)
        return None


# CHI nha cung cap CDN dung chung. Truoc dat ca nhan con "img."/"cdn." -> img.phemex.com
# (quang cao san crypto tren siliconangle) duoc coi la CDN va lot (05/09/2026).
_CDN = re.compile(r"cloudfront\.net|imgix\.net|akamai|gstatic\.com|googleusercontent\.com|wp\.com|"
                  r"files\.wordpress\.com|twimg\.com|cloudinary\.com|fastly|brightspotcdn|ggpht|"
                  r"ytimg\.com|wikimedia\.org|wikipedia\.org|amazonaws\.com|azureedge\.net|"
                  r"cloudflare|substackcdn|medium\.com|mzstatic|apple\.com|arxiv\.org", re.I)


def _host_is_side_try_three(c: dict) -> bool:
    """Anh nam tren host KHAC domain trang va khong phai CDN -> gan nhu chac la
    quang cao/widget ben thu ba (banner Phemex tren siliconangle, 05/09/2026).
    Anh do engine tu chup/tai (tep local, commons, arxiv) khong xet."""
    if c.get("tep") or c.get("source") in ("browser_capture", "commons", "arxiv_cover", "openverse"):
        return False
    ha, ht = _domain(c.get("image_url", "") or ""), _domain(c.get("page_url", "") or "")
    if not ha or not ht:
        return False
    if _original_domain(ha) == _original_domain(ht) or _CDN.search(ha):
        return False
    return True


def _download_candidate(c: dict) -> tuple:
    """Bytes cho MOT ung vien cua download_and_filter: file local (c['tep']) hoac HTTP
    qua _download_bytes — ham THUAN, khong dung chung state, an toan chay song song
    (audit_content_team B3). Tra (data, loi): `loi` giu lai exception cua
    Path.read_bytes() (`_download_bytes` tu no da nuot loi, khong bao gio nem) de pha
    loc tuan tu phia duoi nem lai va in dung log nhu khi con goi truc tiep tai
    day, khong lam mat dong log loi hien co."""
    try:
        if c.get("tep"):
            return Path(c["tep"]).read_bytes(), None
        return _download_bytes(c["image_url"]), None
    except Exception as e:                                   # noqa: BLE001
        return None, e


def download_and_filter(cands: list, wd: Path) -> list:
    """Tai ung vien theo thu tu diem, loai trung (md5) va anh be, luu PNG co dau
    xuat xu. Tra ve danh sach anh da tai [{id, original_path, ...}].

    Pha 1 (song song, ThreadPoolExecutor): tai TRUOC toan bo bytes cho tung ung
    vien — moi tai la mot HTTP GET doc lap, khong quyet dinh gi ve loc/dedup.
    Pha 2 (tuan tu, y het truoc day): loc/dedup/early-break PHAI giu dung thu
    tu diem (quyet dinh "ban nao trung thi giu ban lon hon"), nen khong song
    song duoc — chi khac o cho lay `data` tu ket qua Pha 1 thay vi tai lai.
    Chap nhan over-fetch (tai het cands[:MAX_DOWNLOAD+6], early-break Pha 2 co
    the bo khong dung toi vai ban) — danh doi lay toc do, audit_content_team B3."""
    import article_images
    import image_provenance
    rules = role.active_rules()
    url_junk, short_side_drop = rules.JUNK, rules.SHORT_SIDE_DOWNLOAD
    goc_dir = wd / state_paths.ORIGINAL_DIR
    goc_dir.mkdir(parents=True, exist_ok=True)
    ung_vien = cands[:MAX_DOWNLOAD + 6]
    with ThreadPoolExecutor(max_workers=env_load.quantity(6)) as ex:
        tai_truoc = list(ex.map(_download_candidate, ung_vien))
    da_tai = []                       # [(dhash, im, c, data_len)] — de khu trung gan giong
    for i_uv, (c, (data, loi)) in enumerate(zip(ung_vien, tai_truoc)):
        if len(da_tai) >= MAX_IMAGE + 4:
            # LOW-225: truoc day cac ung vien con lai bi bo IM LANG — ghi lai.
            for c_con, _ in zip(ung_vien[i_uv:], tai_truoc[i_uv:]):
                decision_log.drop_candidate(wd, c_con, "over_limit", "MAX_IMAGE+4",
                                            f"da giu {len(da_tai)} anh truoc ung vien nay")
            break
        try:
            if loi is not None:
                raise loi
            if not data:
                decision_log.drop_candidate(wd, c, "acquire_error", "no_bytes",
                                            "tai khong ra byte nao (HTTP/mang — xem dong [tai] cung URL)")
                continue
            im = Image.open(io.BytesIO(data))
            im.load()
            im = im.convert("RGB")
            w, hh = im.size
            if min(w, hh) < short_side_drop:
                decision_log.drop_candidate(wd, c, "too_small", "SHORT_SIDE_DOWNLOAD",
                                            f"{w}x{hh} < {short_side_drop}", im=im)
                continue
            if _host_is_side_try_three(c):
                print(f"[tai] bo anh host ben thu ba (quang cao?): {_domain(c.get('image_url',''))} tren {_domain(c.get('page_url',''))}", file=sys.stderr)
                decision_log.drop_candidate(wd, c, "third_party_host", "_host_is_side_try_three",
                                            f"{_domain(c.get('image_url', ''))} tren {_domain(c.get('page_url', ''))}", im=im)
                continue
            if not c.get("cho_do_hoa") and (url_junk.search(c.get("image_url", "") or "")
                                            or url_junk.search(c.get("alt", "") or "")):
                # `cho_do_hoa` mien cong nay: bo tu vung RAC co chu "logo", ma
                # THE LOGO thi duong dan lan ten tep Commons deu co chu do — no
                # tu chan chinh no (09/09/2026). Cong nay de chan logo bao/quang
                # cao lot vao tu <img> cua trang, khong phai logo ta co tinh lay.
                print(f"[tai] bo url/alt rac: {str(c.get('image_url'))[-60:]}", file=sys.stderr)
                khop = url_junk.search(c.get("image_url", "") or "") or url_junk.search(c.get("alt", "") or "")
                decision_log.drop_candidate(wd, c, "junk_url", "rules.JUNK",
                                            f"khop {khop.group(0)!r}" if khop else "", im=im)
                continue                                  # placeholder/onboarding/logo/ad
            if rules.is_blank_image(im)[0]:
                print(f"[tai] bo anh RONG: {str(c.get('image_url'))[-60:]}", file=sys.stderr)
                decision_log.drop_candidate(wd, c, "blank", "rules.is_blank_image", im=im)
                continue
            if (w, hh) in article_images.HAS_AI_GENERATE:
                decision_log.drop_candidate(wd, c, "ai_generated_size", "HAS_AI_GENERATE", f"{w}x{hh}", im=im)
                continue
            ly_do_do_hoa = article_images._graphic(im)
            la_ct, _ = rules.is_chart(im)
            if ly_do_do_hoa and not la_ct and not _chart_by_figure(im) and not c.get("cho_do_hoa"):
                decision_log.drop_candidate(wd, c, "graphic_logo", "article_images._graphic",
                                            ly_do_do_hoa, im=im)
                continue                                  # logo/wordmark
            # `cho_do_hoa`: ung vien CO CHU Y la do hoa — the logo chinh thuc cua
            # hang (image_brand.card_logo). Cong tren sinh ra de chan logo lot
            # vao tu <img> cua bai bao, khong phai de chan thu ta co tinh dung.
            h = rules.dhash(im)
            # Trung gan giong (cung anh o co khac, anh <img> vs figure chup): giu ban LON hon.
            # Nguong theo LOAI anh: voi do hoa (chart/bang) dHash 8x8 chi doc bo
            # xuong bo cuc nen HAI bieu do khac han so lieu chi cach nhau 4-5 bit
            # — nguong chung 6 lam mat mot trong hai chart cua CUNG mot bai. Va
            # phai IN RA: cac nhanh loai bo khac quanh day deu co dong stderr,
            # rieng nhanh nay truoc 06/09/2026 bo im lang.
            ng = rules.dhash_threshold_for(im)
            trung = next((k for k, (h2, im2, _, _) in enumerate(da_tai)
                          if rules.is_near_duplicate(h, h2, rules.dhash_threshold_for(im2, ng))), None)
            if trung is not None:
                lon_hon = w * hh > da_tai[trung][1].width * da_tai[trung][1].height
                print(f"[tai] bo ban {'nho' if lon_hon else 'sau'} vi trung gan giong "
                      f"(lech {bin(h ^ da_tai[trung][0]).count('1')} bit, nguong {ng}): "
                      f"{str(c.get('image_url'))[:60]}", file=sys.stderr)
                bang_chung = (f"lech {bin(h ^ da_tai[trung][0]).count('1')} bit, nguong {ng}, "
                              f"trung voi {str(da_tai[trung][2].get('image_url'))[:120]}")
                if lon_hon:
                    decision_log.drop_candidate(wd, da_tai[trung][2], "near_duplicate", "dhash_smaller",
                                                bang_chung, im=da_tai[trung][1])
                    da_tai[trung] = (h, im, c, len(data))
                else:
                    decision_log.drop_candidate(wd, c, "near_duplicate", "dhash_later", bang_chung, im=im)
                continue
            da_tai.append((h, im, c, len(data)))
        except Exception as e:                               # noqa: BLE001
            print(f"[tai] {str(c.get('image_url'))[:60]}: {type(e).__name__}: {e!r}", file=sys.stderr)
            # Loi LAY anh (tai/doc tep) tach khoi loi XU LY anh da co trong tay.
            decision_log.drop_candidate(wd, c, "acquire_error" if loi is not None else "process_error",
                                        type(e).__name__, repr(e))
    # MOT dong tong de brief/route phan biet "trang khong co anh" voi "khong
    # tai duoc anh nao" (loi moi truong) — C-r2-2. Tung URL da co dong rieng.
    khong_tai = sum(1 for d, l in tai_truoc if not d)
    if ung_vien and khong_tai:
        print(f"[tai] {khong_tai}/{len(ung_vien)} ung vien KHONG tai duoc"
              + (" — TAT CA, nghi mang/DNS/proxy truoc khi nghi bai khong co anh" if khong_tai == len(ung_vien) else ""),
              file=sys.stderr)
    for h, im, c, _ in da_tai[MAX_IMAGE:]:
        # LOW-225: phan vuot MAX_IMAGE truoc day bi cat IM LANG.
        decision_log.drop_candidate(wd, c, "over_limit", "MAX_IMAGE", f"chi giu {MAX_IMAGE} anh dau", im=im)
    ra = []
    for n, (h, im, c, _) in enumerate(da_tai[:MAX_IMAGE], start=1):
        ma = f"A{n}"
        out = goc_dir / f"{ma}.png"
        im.save(out, "PNG", pnginfo=image_provenance.stamp_provenance(
            {"browser_capture": "chup_chart", "arxiv_figure": "arxiv_hinh"}.get(c.get("source"), "dre_chuan_bi")))
        # Chi tin cau truc (table/canvas/svg) hoac alt/url THAT cua trang; <figure>
        # khong noi len gi (bao boc ca anh minh hoa lan quang cao).
        hint = bool((c.get("source") != "browser_capture" and (article_images.RULE.search(c.get("image_url", "") or "")
                                                 or article_images.RULE.search(c.get("alt", "") or "")
                                                 or article_images.RULE_MODEL.search(c.get("alt", "") or "")))
                    or c.get("html_tag") in ("table", "canvas", "svg")
                    or c.get("source") == "arxiv_figure")
        ra.append({"id": ma, "original_path": str(out), "url": c.get("image_url", ""),
                   "alt": (c.get("alt") or c.get("alt_chup") or "")[:120], "source": c.get("source", ""),
                   "page_url": c.get("page_url", ""), "domain": _domain(c.get("page_url") or c.get("image_url")),
                   "score": c.get("score", 0), "score_reason": c.get("score_reason", ""), "chart_hint": hint,
                   # Ten hinh trong paper ("Figure 1") — Kite doc de biet tam nao
                   # la hinh mo dau bai, va de viet caption cho dung.
                   **({"paper_figure": c["paper_figure"]} if c.get("paper_figure") else {}),
                   **({"concept": c["concept"]} if c.get("concept") else {}),
                   **({"brand_match": c["brand_match"]} if c.get("brand_match") else {}),
                   **({"entity": c["entity"]} if c.get("entity") else {})})
        decision_log.note(ra[-1], "download", "keep", "download_and_filter")
    return ra


def _chart_by_figure(im: Image.Image) -> bool:
    """Bo sung cho rules.is_chart (bo sot chart co duong mau khu rang cua, xem
    chu thich ben do). Do 04/09/2026 tren 11 anh that: chart/bang/infographic co
    NEN GAN TRANG 0.64-0.82 va MAT DO CANH 0.09-0.14; anh chup 0.00-0.06 /
    0.04-0.05; anh chup co vien trang 0.36 / 0.05. Can CA HAI: nen trang nhieu
    (mot tam san pham tren nen trang co canh thua) VA canh day (chu, truc, cot)."""
    from PIL import ImageFilter
    w, h = im.size
    v = im.resize((480, max(1, round(h * 480 / w))))
    L = v.convert("L")
    n = v.width * v.height
    trang = sum(L.histogram()[236:]) / n
    canh = sum(L.filter(ImageFilter.FIND_EDGES).histogram()[60:]) / n
    return trang >= 0.45 and canh >= 0.08


# ---- 3. do, phan loai, cat san --------------------------------------------
def _save_crop(img: Image.Image, out: Path, ti_le_ten: str, cx=0.5, cy=0.5,
              cat_ngang=False) -> Image.Image:
    """Cat qua crop_ratio.crop va DONG DAU y het CLI crop_ratio.py — cong
    `kiem_xuat_xu`/`check_crop_landscape` doc dau nay."""
    import crop_ratio
    from PIL.PngImagePlugin import PngInfo
    ra = crop_ratio.crop(img, crop_ratio.RATIO[ti_le_ten], cx, cy, cat_ngang=cat_ngang)
    meta = PngInfo()
    # CHEP LAI dau cua anh goc truoc khi them dau crop. Truoc 06/09/2026 ham nay
    # dung PngInfo TRANG, nen ban cat mat `nguon_dung=chup_xep_hang` -> is_ranking_image
    # tra False -> mat mien tru o image_rules, va carousel chan dung cai bia ma
    # dre_submit bat buoc dung. Xay ra 100% voi anh chup bang tren khung mobile.
    for k, v in (getattr(img, "text", None) or {}).items():
        if k != "crop_ti_le" and isinstance(v, str):
            meta.add_text(k, v)
    meta.add_text("crop_ti_le", f"goc={img.size[0]}x{img.size[1]};ti_le={ti_le_ten};"
                                f"cx={cx};cy={cy};cat_ngang={int(cat_ngang)}")
    out.parent.mkdir(parents=True, exist_ok=True)
    ra.save(out, "PNG", pnginfo=meta)
    return ra
