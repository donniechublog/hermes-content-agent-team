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

import image_rules
import scan_common
import env_load                                              # noqa: E402

from chuan_bi.chung import TOI_DA_ANH, _goc_mien, _hdr, _mien


# Nguong (cung goc voi luat_anh; o day chi la phan CHON anh de tai)
URL_RAC = image_rules.JUNK                 # mot bo tu vung, xem luat_anh


CANH_NGAN_BO = image_rules.SHORT_SIDE_DOWNLOAD   # xem luat_anh (ba nguong dat canh nhau)


TOI_DA_TAI = 14             # ung vien thu tai (co cai hong/trung)


TAI_TOI_DA_BYTE = 14_000_000


# ---- 2. anh -----------------------------------------------------------------
def _tai_bytes(url: str) -> bytes | None:
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
                if len(buf) > TAI_TOI_DA_BYTE:
                    print(f"[tai] {str(url)[:70]}: qua {TAI_TOI_DA_BYTE // 1_000_000} MB, bo", file=sys.stderr)
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


def _host_la_ben_thu_ba(c: dict) -> bool:
    """Anh nam tren host KHAC domain trang va khong phai CDN -> gan nhu chac la
    quang cao/widget ben thu ba (banner Phemex tren siliconangle, 05/09/2026).
    Anh do engine tu chup/tai (tep local, commons, arxiv) khong xet."""
    if c.get("tep") or c.get("tu") in ("chup", "commons", "arxiv_bia", "openverse"):
        return False
    ha, ht = _mien(c.get("anh", "") or ""), _mien(c.get("trang", "") or "")
    if not ha or not ht:
        return False
    if _goc_mien(ha) == _goc_mien(ht) or _CDN.search(ha):
        return False
    return True


def _tai_ung_vien(c: dict) -> tuple:
    """Bytes cho MOT ung vien cua tai_va_loc: file local (c['tep']) hoac HTTP
    qua _tai_bytes — ham THUAN, khong dung chung state, an toan chay song song
    (audit_content_team B3). Tra (data, loi): `loi` giu lai exception cua
    Path.read_bytes() (`_tai_bytes` tu no da nuot loi, khong bao gio nem) de pha
    loc tuan tu phia duoi nem lai va in dung log nhu khi con goi truc tiep tai
    day, khong lam mat dong log loi hien co."""
    try:
        if c.get("tep"):
            return Path(c["tep"]).read_bytes(), None
        return _tai_bytes(c["anh"]), None
    except Exception as e:                                   # noqa: BLE001
        return None, e


def tai_va_loc(cands: list, wd: Path) -> list:
    """Tai ung vien theo thu tu diem, loai trung (md5) va anh be, luu PNG co dau
    xuat xu. Tra ve danh sach anh da tai [{ma, goc, ...}].

    Pha 1 (song song, ThreadPoolExecutor): tai TRUOC toan bo bytes cho tung ung
    vien — moi tai la mot HTTP GET doc lap, khong quyet dinh gi ve loc/dedup.
    Pha 2 (tuan tu, y het truoc day): loc/dedup/early-break PHAI giu dung thu
    tu diem (quyet dinh "ban nao trung thi giu ban lon hon"), nen khong song
    song duoc — chi khac o cho lay `data` tu ket qua Pha 1 thay vi tai lai.
    Chap nhan over-fetch (tai het cands[:TOI_DA_TAI+6], early-break Pha 2 co
    the bo khong dung toi vai ban) — danh doi lay toc do, audit_content_team B3."""
    import anh_bai
    goc_dir = wd / "goc"
    goc_dir.mkdir(parents=True, exist_ok=True)
    ung_vien = cands[:TOI_DA_TAI + 6]
    with ThreadPoolExecutor(max_workers=env_load.quantity(6)) as ex:
        tai_truoc = list(ex.map(_tai_ung_vien, ung_vien))
    da_tai = []                       # [(dhash, im, c, data_len)] — de khu trung gan giong
    for c, (data, loi) in zip(ung_vien, tai_truoc):
        if len(da_tai) >= TOI_DA_ANH + 4:
            break
        try:
            if loi is not None:
                raise loi
            if not data:
                continue
            im = Image.open(io.BytesIO(data))
            im.load()
            im = im.convert("RGB")
            w, hh = im.size
            if min(w, hh) < CANH_NGAN_BO:
                continue
            if _host_la_ben_thu_ba(c):
                print(f"[tai] bo anh host ben thu ba (quang cao?): {_mien(c.get('anh',''))} tren {_mien(c.get('trang',''))}", file=sys.stderr)
                continue
            if not c.get("cho_do_hoa") and (URL_RAC.search(c.get("anh", "") or "")
                                            or URL_RAC.search(c.get("alt", "") or "")):
                # `cho_do_hoa` mien cong nay: bo tu vung RAC co chu "logo", ma
                # THE LOGO thi duong dan lan ten tep Commons deu co chu do — no
                # tu chan chinh no (09/09/2026). Cong nay de chan logo bao/quang
                # cao lot vao tu <img> cua trang, khong phai logo ta co tinh lay.
                print(f"[tai] bo url/alt rac: {str(c.get('anh'))[-60:]}", file=sys.stderr)
                continue                                  # placeholder/onboarding/logo/ad
            if image_rules.is_blank_image(im)[0]:
                print(f"[tai] bo anh RONG: {str(c.get('anh'))[-60:]}", file=sys.stderr)
                continue
            if (w, hh) in anh_bai.CO_AI_SINH:
                continue
            ly_do_do_hoa = anh_bai._do_hoa(im)
            la_ct, _ = image_rules.is_chart(im)
            if ly_do_do_hoa and not la_ct and not _chart_theo_hinh(im) and not c.get("cho_do_hoa"):
                continue                                  # logo/wordmark
            # `cho_do_hoa`: ung vien CO CHU Y la do hoa — the logo chinh thuc cua
            # hang (anh_thuong_hieu.the_logo). Cong tren sinh ra de chan logo lot
            # vao tu <img> cua bai bao, khong phai de chan thu ta co tinh dung.
            h = image_rules.dhash(im)
            # Trung gan giong (cung anh o co khac, anh <img> vs figure chup): giu ban LON hon.
            # Nguong theo LOAI anh: voi do hoa (chart/bang) dHash 8x8 chi doc bo
            # xuong bo cuc nen HAI bieu do khac han so lieu chi cach nhau 4-5 bit
            # — nguong chung 6 lam mat mot trong hai chart cua CUNG mot bai. Va
            # phai IN RA: cac nhanh loai bo khac quanh day deu co dong stderr,
            # rieng nhanh nay truoc 06/09/2026 bo im lang.
            ng = image_rules.dhash_threshold_for(im)
            trung = next((k for k, (h2, im2, _, _) in enumerate(da_tai)
                          if image_rules.is_near_duplicate(h, h2, image_rules.dhash_threshold_for(im2, ng))), None)
            if trung is not None:
                lon_hon = w * hh > da_tai[trung][1].width * da_tai[trung][1].height
                print(f"[tai] bo ban {'nho' if lon_hon else 'sau'} vi trung gan giong "
                      f"(lech {bin(h ^ da_tai[trung][0]).count('1')} bit, nguong {ng}): "
                      f"{str(c.get('anh'))[:60]}", file=sys.stderr)
                if lon_hon:
                    da_tai[trung] = (h, im, c, len(data))
                continue
            da_tai.append((h, im, c, len(data)))
        except Exception as e:                               # noqa: BLE001
            print(f"[tai] {str(c.get('anh'))[:60]}: {type(e).__name__}: {e!r}", file=sys.stderr)
    # MOT dong tong de brief/route phan biet "trang khong co anh" voi "khong
    # tai duoc anh nao" (loi moi truong) — C-r2-2. Tung URL da co dong rieng.
    khong_tai = sum(1 for d, l in tai_truoc if not d)
    if ung_vien and khong_tai:
        print(f"[tai] {khong_tai}/{len(ung_vien)} ung vien KHONG tai duoc"
              + (" — TAT CA, nghi mang/DNS/proxy truoc khi nghi bai khong co anh" if khong_tai == len(ung_vien) else ""),
              file=sys.stderr)
    ra = []
    for n, (h, im, c, _) in enumerate(da_tai[:TOI_DA_ANH], start=1):
        ma = f"A{n}"
        out = goc_dir / f"{ma}.png"
        im.save(out, "PNG", pnginfo=image_rules.stamp_provenance(
            {"chup": "chup_chart", "arxiv_hinh": "arxiv_hinh"}.get(c.get("tu"), "dre_chuan_bi")))
        # Chi tin cau truc (table/canvas/svg) hoac alt/url THAT cua trang; <figure>
        # khong noi len gi (bao boc ca anh minh hoa lan quang cao).
        hint = bool((c.get("tu") != "chup" and (anh_bai.QUY.search(c.get("anh", "") or "")
                                                 or anh_bai.QUY.search(c.get("alt", "") or "")
                                                 or anh_bai.QUY_MODEL.search(c.get("alt", "") or "")))
                    or c.get("the") in ("table", "canvas", "svg")
                    or c.get("tu") == "arxiv_hinh")
        ra.append({"ma": ma, "goc": str(out), "url": c.get("anh", ""),
                   "alt": (c.get("alt") or c.get("alt_chup") or "")[:120], "tu": c.get("tu", ""),
                   "trang": c.get("trang", ""), "mien": _mien(c.get("trang") or c.get("anh")),
                   "diem": c.get("diem", 0), "ly_do": c.get("ly_do", ""), "hint_chart": hint,
                   # Ten hinh trong paper ("Figure 1") — Kite doc de biet tam nao
                   # la hinh mo dau bai, va de viet caption cho dung.
                   **({"paper_hinh": c["paper_hinh"]} if c.get("paper_hinh") else {}),
                   **({"khai_niem": c["khai_niem"]} if c.get("khai_niem") else {}),
                   **({"thuong_hieu": c["thuong_hieu"]} if c.get("thuong_hieu") else {}),
                   **({"thuc_the": c["thuc_the"]} if c.get("thuc_the") else {})})
    return ra


def _chart_theo_hinh(im: Image.Image) -> bool:
    """Bo sung cho luat_anh.la_chart (bo sot chart co duong mau khu rang cua, xem
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
def _luu_crop(img: Image.Image, out: Path, ti_le_ten: str, cx=0.5, cy=0.5,
              cat_ngang=False) -> Image.Image:
    """Cat qua crop_ti_le.cat va DONG DAU y het CLI crop_ti_le.py — cong
    `kiem_xuat_xu`/`kiem_crop_ngang` doc dau nay."""
    import crop_ti_le
    from PIL.PngImagePlugin import PngInfo
    ra = crop_ti_le.cat(img, crop_ti_le.TI_LE[ti_le_ten], cx, cy, cat_ngang=cat_ngang)
    meta = PngInfo()
    # CHEP LAI dau cua anh goc truoc khi them dau crop. Truoc 06/09/2026 ham nay
    # dung PngInfo TRANG, nen ban cat mat `nguon_dung=chup_xep_hang` -> la_xep_hang
    # tra False -> mat mien tru o luat_anh, va carousel chan dung cai bia ma
    # dre_nop bat buoc dung. Xay ra 100% voi anh chup bang tren khung mobile.
    for k, v in (getattr(img, "text", None) or {}).items():
        if k != "crop_ti_le" and isinstance(v, str):
            meta.add_text(k, v)
    meta.add_text("crop_ti_le", f"goc={img.size[0]}x{img.size[1]};ti_le={ti_le_ten};"
                                f"cx={cx};cy={cy};cat_ngang={int(cat_ngang)}")
    out.parent.mkdir(parents=True, exist_ok=True)
    ra.save(out, "PNG", pnginfo=meta)
    return ra
