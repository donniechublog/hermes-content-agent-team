#!/usr/bin/env python3
"""PHA NHIN: hoi vision tung anh, do hinh hoc, quyet dinh anh dung duoc o dau.

Tach tu anh_chuan_bi.py 09/09/2026 (audit A1, di chuyen thuan — than ham giu y nguyen).
"""
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageStat

import luat_anh
import env_load
import vai

from chuan_bi.nguon import _ten_rieng_dau
from chuan_bi.tai_loc import _chart_theo_hinh, _luu_crop


VISION_MODEL = env_load.VISION_MODEL


VISION_URL = env_load.ROUTER_URL


# LOW-47 (Ong Chu 13/09/2026): "khong uu tien su dung tat ca nhung anh nhin
# roi". Do that tren bo Anthropic/Nvidia IPO: anh chup man hinh splash "Claude"
# con dong "loading chart...", do hoa "Nvidia Weighs $10B..." chu in chim sau
# cau quote, tieu de bao Nga RBC — ca ba deu qua cong LIEN_QUAN (dung chu de)
# nhung nhin roi. Chi con mat moi phan biet duoc anh roi voi anh sach.
CAU_ROI = ("ROI: co | khong  (co = anh NHIN ROI: nhieu chu in san de len hinh (tieu de bao, "
           "banner chu, infographic nhoi chu), chup man hinh web/app nhieu chu, cat ghep nhieu "
           "hinh, do hoa/minh hoa nhoi nhet nhieu chi tiet tranh nhau; khong = anh chup that, "
           "logo, bien hieu, san pham voi MOT chu the ro, hoac bieu do/bang so lieu gon gang)")
# Ong Chu 13/09/2026, cung ngay, ve CHINH do hoa "Nvidia Weighs $10B": "anh nay
# xung dang lam hero, the hien duoc day du moi tu khoa quan trong". Roi thi
# khong uu tien — TRU KHI nhin vao doc ra du tu khoa chinh cua tin.
CAU_TU_KHOA = ("TU_KHOA: co | khong  (co = nhin anh DOC RA DU cac tu khoa chinh cua bai: ten cac "
               "cong ty/nhan vat chinh VA con so hoac su kien chinh, vd logo hai hang + so tien + "
               "chu IPO; khong = chi thay mot phan, hoac khong doc ra)")


def mo_ta_anh(path, tieu_de: str, hang: str = "", hoi_them: str = "",
              nhan_them: str = "", khai_niem: str = "", thuong_hieu: dict | None = None,
              khai_niem_theo_loai: bool = False, chup_nguon: bool = False,
              ket_qua: dict | None = None) -> tuple:
    """Con mat cua day chuyen. Hoi vision local: MOT cau mo ta + LIEN_QUAN co/khong
    theo tieu de bai. Tra ve (mo_ta, lien_quan) — lien_quan None neu KHONG HOI
    DUOC (thieu key, router hong ca hai lan thu lai cua `_goi_router`): luc do
    brief noi ro la CHUA ai nhin, dung y nhu tu truoc.

    Ong Chu 12/09/2026, dong CONG FAIL-OPEN: truoc day router TRA LOI duoc
    nhung dong LIEN_QUAN khong doc ra duoc (model lech dinh dang) cung thanh
    None — ma moi noi loc `dung_duoc` deu viet `lien_quan is not False`, tuc
    None DUOC COI LA DUYET. Do that 12/09 tren may chu: anh Tesla (Terafab) va
    logo Anthropic (truoc khi sua ca thanh cong 32 diem) deu lot bia qua duong
    nay — router CO tra loi, chi la khong parse duoc. Phan biet ro hai ca:
      - KHONG HOI DUOC (thieu key / het luot thu 429-5xx / loi mang) -> giu
        nguyen None, KHONG hoi lai o day (da co backoff rieng o _goi_router).
      - HOI DUOC nhung khong doc ra LIEN_QUAN -> HOI LAI DUNG 1 LAN; van khong
        doc ra thi COI LA ROT (lqv=False), khong con la None nua.

    Do 05/09/2026 tren bo Broadcom: widget linh kien / bang Fear&Greed / logo bao /
    nguoi dan ong G20 -> khong; ~2s moi anh. Khong heuristic nao bat duoc "widget
    co khi tren bai Broadcom" — chi co nhin moi biet.

    `hoi_them` / `nhan_them` (tuy chon): xin THEM mot dong tra loi va lay ve
    nguyen van dong do — luc nay ham tra ve (mo_ta, lien_quan, them). Bob dung
    de hoi luon mood cua anh trong CHINH luot nhin nay, thay vi mo mot lenh
    HTTP rieng (meo cu nam trong MEMORY.md, khong ai kiem). Cac vai khac khong
    truyen thi hanh vi va gia tri tra ve giu nguyen y cu.

    `khai_niem` (07/09/2026): anh tim theo tu khoa (co, datacenter) chu khong phai
    anh cua tin — hoi cau khac (anh_khai_niem.cau_hoi_vision), khong hoi "co phai
    anh cua tin" vi chac chan khong, va khong ap override "ten hang trong mo ta".

    `chup_nguon` (LOW-45, 12/09/2026): anh hero CHUP TU CHINH TRANG NGUON
    (`vong_bu._vong_chup_nguon`) — LA anh cua tin, cau hoi khong hoi lai "co
    lien quan khong" nua (chac chan co, tu DOM cua chinh bai), CHI hoi CHAT
    LUONG (ro net, khong phai anh bao chup lai mot man hinh khac). Truoc ticket
    nay nhanh `_vong_chup_nguon` bo qua vision HOAN TOAN, ep `lien_quan = True`
    thang — do that 12/09: anh hero that cua bai Moonshot/Kimi K3 la mot anh
    bao Getty chup nghieng man hinh App Store, van bi ep True du xau, roi
    tam ngang do LAI bi mot vong khac (`_lay_anh_trang`, da chan o LOW-45 phan
    1) chup lai lan nua thanh mot tam khac — ca hai deu khong qua cong chat
    luong nao. Nhanh nay dong no lai."""
    import base64, json as _j, urllib.request
    # `ket_qua` (LOW-47, 13/09/2026): dict nguoi goi truyen vao de nhan them
    # co "roi" (anh nhin roi) ma KHONG doi so phan tu tuple tra ve — Bob va
    # test deu mo goi 2/3 phan tu.
    # env_load.bat_buoc nem SystemExit, ma SystemExit KHONG phai con cua
    # Exception — `except Exception` o day khong bat duoc. Thieu OPENAI_API_KEY
    # la ca engine chet giua chung, khong co xong.json, vai chi thay "chua chuan
    # bi" ma khong biet vi sao (06/09/2026). Doc thang bien, khong nem.
    env_load.nap()
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        print("[vision] thieu OPENAI_API_KEY -> khong nhin duoc anh, brief se ghi CHUA AI NHIN",
              file=sys.stderr)
        return ("", None, "") if (hoi_them and nhan_them) else ("", None)

    def _mot_lan():
        """Mot lan hoi + parse. Nem exception khi KHONG HOI DUOC (mang/router/
        JSON hong); tra (mo_ta, lien_quan, them) khi hoi duoc — lien_quan van
        co the None o day, nghia la HOI DUOC nhung khong doc ra LIEN_QUAN."""
        b64 = base64.b64encode(Path(path).read_bytes()).decode()
        # Dieu kien RO NET (LOW-45, 12/09/2026, Ong Chu: "chi can dung lay anh
        # xau"): truoc day cau hoi mac dinh (duong "anh rieng cua tin", pho bien
        # nhat) chi hoi "co lien quan bai khong", KHONG hoi ve do net/goc chup —
        # khac han hai nhanh khai_niem/thuong_hieu ben duoi da co san cum "qua
        # mo" tu lau. Anh bao chup nghieng mot man hinh (vd App Store cua Kimi
        # K3, do that tren dcgr) lot qua de dang vi dung chu de nhung mo/nghieng
        # — them dung mot dieu kien nhu hai nhanh kia, khong mo cau hoi rieng.
        hoi = (f"Bai bao: \"{tieu_de}\"." + (f" Cong ty/san pham chinh: {hang}." if hang else "")
               + "\nTra loi DUNG 2 dong:\n"
               "MO_TA: <mot cau tieng Viet co dau mo ta anh nay la gi>\n"
               "LIEN_QUAN: co | khong  (co = anh/chart/bang ve dung tin nay, HOAC anh tru so/"
               "san pham/logo-tren-toa-nha/su kien cua chinh cong ty trong bai, VA anh phai RO NET; "
               "khong = quang cao, widget, logo bao, placeholder, anh minh hoa chung chung, cong ty/"
               f"chu de khac, {luat_anh.CUM_ANH_CHUP_LAI_MAN_HINH})")
        if chup_nguon:
            # LA anh cua tin (tu chinh DOM cua bai) — khong hoi lai "co lien
            # quan khong", CHI hoi CHAT LUONG. Tach khoi nhanh mac dinh o tren
            # vi cau do con hoi ca "co dung chu de" — cau hoi thua, va vo tinh
            # cho phep mot cau tra loi "khong" vi LY DO CHU DE (hiem gap that
            # nhung ve mat logic van sai) lam rot mot anh chac chan la hero.
            hoi = (f"Day la ANH HERO cua chinh bai bao: \"{tieu_de}\" — CHAC CHAN la anh cua tin, "
                   "khong hoi 'co lien quan khong'.\nTra loi DUNG 2 dong:\n"
                   "MO_TA: <mot cau tieng Viet co dau mo ta anh nay la gi>\n"
                   "LIEN_QUAN: co | khong  (co = anh RO NET, xuat truc tiep tu web/thiet ke; "
                   f"khong = mo/nhoe, {luat_anh.CUM_ANH_CHUP_LAI_MAN_HINH})")
        elif khai_niem:
            import anh_khai_niem
            hoi = anh_khai_niem.cau_hoi_vision(tieu_de, khai_niem, theo_loai=khai_niem_theo_loai)
        elif thuong_hieu:
            # Cau chung hoi "co phai anh CUA TIN khong" — chan dung nha sang lap
            # va the logo chac chan khong phai, nen bi danh rot dung luc ta can
            # chung nhat (09/09/2026).
            import anh_thuong_hieu
            hoi = anh_thuong_hieu.cau_hoi_vision(tieu_de, thuong_hieu)
        # Moi nhanh deu hoi them dong ROI (LOW-47): anh roi khong bi cam, chi
        # xuong cuoi hang uu tien — xem nop_chung.kiem_anh_roi.
        hoi = hoi.replace("DUNG 2 dong", "DUNG 4 dong") + "\n" + CAU_ROI + "\n" + CAU_TU_KHOA
        if hoi_them and nhan_them:
            hoi = hoi.replace("DUNG 4 dong", "DUNG 5 dong") + f"\n{nhan_them}: {hoi_them}"
        body = {"model": VISION_MODEL, "thinking": {"type": "disabled"}, "max_tokens": 400,
                "stream": False, "temperature": 0,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": hoi},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}}]}]}
        req = urllib.request.Request(VISION_URL, data=_j.dumps(body).encode(),
                                     headers={"Content-Type": "application/json",
                                              "Authorization": "Bearer " + key})
        raw = _goi_router(req).read().decode().strip()
        if raw.startswith("data:"):
            raw = raw.split("data: [DONE]")[0].strip()[5:].strip()
        txt = _j.loads(raw)["choices"][0]["message"]["content"]
        mo_ta = re.search(r"MO_TA\s*:\s*(.+)", txt)
        lq = re.search(r"LIEN_QUAN\s*:\s*(co|có|khong|không)", txt, re.I)
        mt = mo_ta.group(1).strip()[:200] if mo_ta else txt.strip()[:200]
        lqv = lq.group(1).lower().startswith("c") if lq else None
        # Chot tat dinh: mo ta neu dung ten hang -> lien quan (anh tru so/san pham
        # Broadcom bi vision phan "khong" luc co luc khong, 05/09/2026).
        # ...nhung chi khi mo ta la BOI CANH hang (tru so/san pham/logo/su kien),
        # khong phai man hinh/driver/phan mem nhac ten hang (A10 Ubuntu 05/09).
        BOI_CANH = re.compile(r"tr[uụ] s[oở]|t[oò]a nh[aà]|campus|logo|s[aả]n ph[aẩ]m|thi[eế]t b[iị]|"
                              r"chip|s[uự] ki[eệ]n|v[aă]n ph[oò]ng|nh[aà] m[aá]y|bi[eể]n hi[eệ]u|"
                              r"headquarters|office|building|product|device|event", re.I)
        KHONG = re.compile(r"m[aà]n h[iì]nh|giao di[eệ]n|c[uử]a s[oổ]|driver|ph[aầ]n m[eề]m|screenshot|"
                           r"ubuntu|windows|terminal|c[aà]i \w*|website|trang web", re.I)
        if khai_niem or thuong_hieu or chup_nguon:
            pass                                   # tin cau tra loi, khong override theo ten hang
        elif hang and lqv is False and hang.lower() in mt.lower() and BOI_CANH.search(mt) and not KHONG.search(mt):
            lqv = True
        elif lqv is True and KHONG.search(mt) and not BOI_CANH.search(mt):
            lqv = False
        them = ""
        if hoi_them and nhan_them:
            t = re.search(nhan_them + r"\s*:\s*(.+)", txt)
            them = t.group(1).strip()[:120] if t else ""
        rr = re.search(r"^\s*R[OỐ]I\s*:\s*(co|có|khong|không)", txt, re.I | re.M)
        roi = rr.group(1).lower().startswith("c") if rr else None
        tk = re.search(r"^\s*T[UỪ]_?\s*KHO[AÁ]\s*:\s*(co|có|khong|không)", txt, re.I | re.M)
        du_tk = tk.group(1).lower().startswith("c") if tk else None
        return mt, lqv, them, {"roi": roi, "du_tu_khoa": du_tk}

    try:
        mt, lqv, them, phu = _mot_lan()
    except Exception as e:                                   # noqa: BLE001
        print(f"[vision] {Path(path).name}: {type(e).__name__}: {e!r}", file=sys.stderr)
        return ("", None, "") if (hoi_them and nhan_them) else ("", None)

    if lqv is None:
        # HOI DUOC (khong nem o tren) nhung khong doc ra LIEN_QUAN — hoi lai
        # DUNG MOT LAN truoc khi ket luan. Loi lan 2 (mang/router) van la
        # "khong hoi duoc", khong phai co so de ROT — nhung da co MOT cau tra
        # loi that (lan 1) ma van khong parse duoc lan nao thi khong the tiep
        # tuc coi la "chua ai nhin": dong lai thanh ROT.
        print(f"[vision] {Path(path).name}: khong doc duoc LIEN_QUAN, hoi lai 1 lan", file=sys.stderr)
        try:
            mt2, lqv2, them2, phu2 = _mot_lan()
        except Exception as e:                               # noqa: BLE001
            print(f"[vision] {Path(path).name}: lan 2 hong: {type(e).__name__}: {e!r}", file=sys.stderr)
            mt2, lqv2, them2, phu2 = mt, None, them, phu
        if lqv2 is None:
            print(f"[vision] {Path(path).name}: van khong doc duoc sau 2 lan hoi -> COI LA ROT "
                  "(khong con fail-open)", file=sys.stderr)
            mt, lqv, them = (mt2 or mt), False, (them2 or them)
            phu = {k: (phu[k] if phu2.get(k) is None else phu2[k]) for k in phu}
        else:
            mt, lqv, them, phu = mt2, lqv2, them2, phu2

    if ket_qua is not None:
        ket_qua.update(phu)
    if hoi_them and nhan_them:
        return mt, lqv, them
    return mt, lqv


# Ma HTTP dang thu lai: router qua tai / gateway. 401/400 thi khong (thu lai vo ich).
_THU_LAI = (429, 502, 503, 504)
_CHO_THU_LAI = (1, 2, 4)      # giay, tang dan; 3 lan thu lai


def _goi_router(req, _ngu=None):
    """urlopen co thu lai khi 429/5xx (audit lượt 2, B-r2-2): B2 cho 4 luong ban
    cung luc vao router, gap 429 la anh roi vao "CHUA AI NHIN" va bi loai khoi
    dung_duoc — song song hoa lam 429 de xay ra HON ban tuan tu ma khong co
    backoff nao. `_ngu` de test thay time.sleep."""
    import time
    import urllib.error
    import urllib.request
    ngu = _ngu or time.sleep
    for lan, cho in enumerate(_CHO_THU_LAI + (None,)):
        try:
            return urllib.request.urlopen(req, timeout=45)
        except urllib.error.HTTPError as e:
            if e.code not in _THU_LAI or cho is None:
                raise
            print(f"[vision] router tra {e.code}, thu lai sau {cho}s (lan {lan + 1}/{len(_CHO_THU_LAI)})",
                  file=sys.stderr)
            ngu(cho)


def _phan_loai_an_toan(a: dict, wd: Path, tieu_de: str) -> dict:
    """phan_loai cho executor.map: mot anh hong (PNG cut, dem_mat/crop nem) KHONG
    duoc lam list(ex.map) nem — ca lo mat, ke ca anh da nhin xong, engine chet
    khong xong.json (audit lượt 2, B-r2-3). Anh hong tro thanh anh "chua nhin"
    co ghi chu, cac anh khac di tiep."""
    try:
        return phan_loai(a, wd, tieu_de)
    except Exception as e:                                   # noqa: BLE001
        print(f"[vision] {a.get('ma')} {Path(a.get('goc', '?')).name}: HONG khi phan loai — "
              f"{type(e).__name__}: {e!r}", file=sys.stderr)
        a.update({"dung": [], "lien_quan": None, "mo_ta": "", "mat": 0,
                  "ghi_chu": [f"⚠️ không phân loại được ({type(e).__name__}) — bỏ qua ảnh này"]})
        a.setdefault("w", 0)
        a.setdefault("h", 0)
        return a


def phan_loai(a: dict, wd: Path, tieu_de: str = "", chup_nguon: bool = False) -> dict:
    """Do mot anh bang luat_anh, quyet dinh no DUNG DUOC O DAU, cat san neu can.

    `chup_nguon` (LOW-45): anh hero chup tu chinh trang nguon — xem
    `mo_ta_anh(..., chup_nguon=True)`."""
    img = Image.open(a["goc"]).convert("RGB")
    w, h = img.size
    r = w / h
    la_ct, mo_ta = luat_anh.la_chart(img)
    phang, _ = luat_anh.do_chart(img)
    # Override chi khi phep do KHONG noi nguoc: chart that phang >= 82%, anh chup
    # 52-77% (do 05/09). Truoc day hint tu alt tu gan de len ca phang 52% -> hinh
    # minh hoa AI thanh "CHART", dan full be ngang, ra hai vung.
    if not la_ct and phang >= 0.75 and (a.get("hint_chart") or _chart_theo_hinh(img)):
        la_ct, mo_ta = True, mo_ta + "; nen trang + canh day / alt-tag chart"
    kn = (a.get("khai_niem") or {}).get("tu_khoa", "")
    # Tu khoa do LOAI TIN ep (loai_tin.py) thi con mat khong duoc tu phan "hop bai".
    kn_theo_loai = (a.get("khai_niem") or {}).get("ly_do", "") == "theo loại tin"
    # Hang de con mat doi chieu: voi anh THUONG HIEU la hang cua chinh tam anh do,
    # khong phai ten rieng dau tieu de. Tin "Qualcomm ... with Amazon" ma dua
    # "Qualcomm" cho mot tam tru so Amazon thi chot "ten hang trong mo ta" khong
    # bao gio nay, anh that cua Amazon bi vision danh rot (09/09/2026).
    hang = (a.get("thuong_hieu") or {}).get("hang") or _ten_rieng_dau(tieu_de)
    kq = {}
    a["mo_ta"], a["lien_quan"] = (mo_ta_anh(a["goc"], tieu_de, hang, khai_niem=kn,
                                            khai_niem_theo_loai=kn_theo_loai,
                                            thuong_hieu=a.get("thuong_hieu"),
                                            chup_nguon=chup_nguon, ket_qua=kq)
                                  if tieu_de else ("", None))
    a["roi"] = kq.get("roi")
    a["du_tu_khoa"] = kq.get("du_tu_khoa")
    # None = cong mat KHONG CHAY (thieu cv2/model, hoac cv2 nem) — khac 0 = da
    # dem, khong co mat. Truoc audit lượt 2 (B-r2-1) day la `or 0`: 4 luong dua
    # nhau tren mot detector lam 80-95% anh tra None, tat ca thanh "khong mat".
    mat_tho = luat_anh.dem_mat(a["goc"])
    mat = mat_tho or 0
    day = ImageStat.Stat(img.convert("L").crop((0, int(h * .75), w, h))).mean[0]
    goc_trai = ImageStat.Stat(img.convert("L").crop((0, int(h * .55), int(w * .6), h))).mean[0]
    a.update({"w": w, "h": h, "ti_le": round(r, 2), "loai": "chart" if la_ct else "anh",
              "do_chart": mo_ta, "mat": mat, "day_sang": round(day),
              "goc_trai_sang": round(goc_trai), "canh_ngan": min(w, h),
              "ngang": r >= luat_anh.NGANG_RO, "san": None, "dung": [], "ghi_chu": []})
    if mat_tho is None:
        a["ghi_chu"].append("⚠️ cổng mặt người KHÔNG chạy (thiếu cv2/model hoặc lỗi) — chưa kiểm mặt")
    san = wd / "san" / f"{a['ma']}.png"
    if la_ct:
        if a.get("xep_hang"):
            # ANH XEP HANG GIU NGUYEN VEN, khong cat du cao bao nhieu: hang model
            # da khoanh co the nam duoi 55% dai chup (do that: hang #9, #11 bi cat
            # mat), va no la CHU THE cua tin chu khong phai anh minh hoa.
            a["san"] = a["goc"]
            a["ghi_chu"].append("bảng xếp hạng: giữ nguyên vẹn, dán full bề ngang")
        elif r < luat_anh.TI_LE_45 - luat_anh.DUNG_SAI_TI_LE:
            _luu_crop(img, san, "4:5", cy=0.35)           # chart cao: cat bot day
            a["san"] = str(san)
            a["ghi_chu"].append("chart cao, đã cắt bớt phần dưới về 4:5")
        else:
            a["san"] = a["goc"]                           # chart giu NGUYEN
        a["dung"] = ["thân (chart, dán full bề ngang nguyên vẹn)"]
        if a["ngang"]:
            a["dung"].append("ghép dọc với một ảnh ngang cùng tone")
        a["ghi_chu"].append("KHÔNG làm bìa")
    else:
        if a["ngang"]:
            a["dung"] = ["ghép dọc với một ảnh ngang cùng tone"]
            if h >= 700:
                a["dung"].append("cat_ngang: true NẾU là ảnh người/sản phẩm KHÔNG có chữ")
            else:
                # Banner thap (vd 1900x524): cat doc 4:5 chi con ~420px roi phong
                # len 1080 — mem nhoe (do thu 04/09). Chi con duong ghep.
                a["ghi_chu"].append("quá thấp để cắt dọc, chỉ ghép")
        else:
            ten = "1:1" if r > 0.9 else "4:5"
            _luu_crop(img, san, ten, cy=0.4 if r < 0.7 else 0.5)
            a["san"] = str(san)
            a["dung"] = ["thân"]
            if not mat and goc_trai < 150:
                a["dung"].insert(0, "bìa")
    if a.get("commons"):
        a["ghi_chu"].append("ảnh CHUNG của hãng từ Wikimedia Commons (trụ sở/sản phẩm), không phải ảnh của tin — hợp bìa/slide bối cảnh")
    if mat:
        # MOT ban regex duy nhat, o ban dang ky vai: cong "mat nguoi phai khai
        # ten" cua `vai.anh_chinh_duoc` phai doc ra dung cai ten ma chu thich
        # duoi day hua la co.
        ten = vai.ten_nguoi_trong_alt(a.get("alt", "") or "")
        if ten:
            a["ghi_chu"].append(f"CÓ {mat} MẶT NGƯỜI, alt nêu tên: {', '.join(ten[:2])} → "
                                "chỉ dùng khi đúng người đó, khai \"nhan_vat\" y hệt")
        else:
            a["ghi_chu"].append(f"CÓ {mat} MẶT NGƯỜI mà KHÔNG RÕ AI (alt/caption không nêu tên) → "
                                "KHÔNG DÙNG. Đừng điền tên CEO cho qua cổng — đó là bịa.")
            a["dung"] = [d for d in a["dung"] if d != "bìa"]
    if a.get("roi") and a.get("du_tu_khoa"):
        a["ghi_chu"].insert(0, "⭐ ẢNH RỐI NHƯNG ĐỦ TỪ KHOÁ chính của tin → dùng thoải mái, HỢP LÀM "
                               "BÌA; script tự hiện nguyên bề ngang + đặt nền chữ đặc")
    elif a.get("roi"):
        # Anh roi khong du tu khoa: khong la bia; lam than chi khi het anh sach
        # (nop_chung.kiem_anh_roi), va script tu dat nen chu dac (LOW-47).
        a["dung"] = [d for d in a["dung"] if not str(d).startswith("bìa")]
        a["ghi_chu"].insert(0, "⚠️ ẢNH RỐI (chữ in sẵn/đồ hoạ nhồi/cắt ghép) → CHỈ dùng khi HẾT "
                               "ảnh sạch; buộc dùng thì script tự đặt nền chữ đặc")
    if a.get("lien_quan") is False:
        a["dung"] = []
        a["ghi_chu"].insert(0, "❌ KHÔNG LIÊN QUAN BÀI (vision) → KHÔNG DÙNG")
    if a["canh_ngan"] < luat_anh.CANH_NGAN_MIN:
        a["ghi_chu"].append(f"cạnh ngắn {a['canh_ngan']}px, phóng lên hơi mềm")
    if day > luat_anh.DAY_SANG_MAX and not la_ct:
        a["ghi_chu"].append("đáy sáng, chữ trắng hơi nhạt")
    if a.get("khai_niem"):
        import anh_khai_niem
        anh_khai_niem.nhan_khai_niem(a)
    if a.get("thuong_hieu"):
        import anh_thuong_hieu
        anh_thuong_hieu.nhan_thuong_hieu(a)
    return a


def _nhin_anh(anh: list, nguon: dict, title: str, wd: Path) -> tuple:
    """Phan loai + vision tung anh; anh XH khong hoi vision. Tra
    (anh, dung_duoc, chua_nhin)."""
    print("[vision] nhin tung anh, hoi co lien quan bai khong...", file=sys.stderr)
    # Anh XH khong hoi vision (tham so tieu_de rong): no la anh do chinh engine chup
    # tu trang xep hang, da biet chac lien quan — hoi chi ton them mot luot LLM roi
    # ghi de ket qua ngay duoi. Van qua phan_loai de co do hinh hoc (w/h/ti_le/san).
    # `phan_loai` chi doc/ghi vao chinh dict `a` va duong dan rieng cua no -- khong
    # co state dung chung giua cac lan goi -- nen chay song song duoc (8-12 anh/bai,
    # moi anh mot luot HTTP vision tuan tu la cham, audit_content_team B2). Dung
    # executor.map de GIU NGUYEN thu tu ket qua nhu list-comprehension cu.
    with ThreadPoolExecutor(max_workers=env_load.so_luong(4)) as ex:
        anh = list(ex.map(lambda a: _phan_loai_an_toan(a, wd, "" if a.get("xep_hang")
                                                       else (nguon.get("tieu_de_en") or title)), anh))
    for a in anh:
        if a.get("xep_hang"):
            a["mo_ta"] = a["alt"]
            a["lien_quan"] = True
            a["dung"] = ["HERO / BÌA (bảng xếp hạng, model đã khoanh — ảnh chính bắt buộc của tin xếp hạng)",
                         "thân (chart)"]
            a["ghi_chu"] = [g for g in a["ghi_chu"] if "KHÔNG DÙNG" not in g and "KHÔNG làm bìa" not in g]
            a["ghi_chu"].insert(0, "✅ ẢNH XẾP HẠNG do engine chụp từ nguồn — dùng làm ảnh chính")
    dung_duoc = [a for a in anh if a["dung"] and a.get("lien_quan") is not False]
    chua_nhin = [a["ma"] for a in anh if a.get("lien_quan") is None]
    print(f"[anh] {len(dung_duoc)} anh DUNG DUOC / {len(anh)} tai ve"
          + (f"; CHUA NHIN duoc: {', '.join(chua_nhin)}" if chua_nhin else ""), file=sys.stderr)
    return anh, dung_duoc, chua_nhin
