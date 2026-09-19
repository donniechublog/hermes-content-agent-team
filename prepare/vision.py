#!/usr/bin/env python3
"""PHA NHIN: hoi vision tung anh, do hinh hoc, quyet dinh anh dung duoc o dau.

Tach tu image_prepare.py 09/09/2026 (audit A1, di chuyen thuan — than ham giu y nguyen).
"""
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from PIL import Image, ImageStat

import env_load
import manifest_values
import role
import state_paths
import subject_fit

from prepare import decision_log
from prepare.source import all_proper_nouns
from prepare.download_filter import _chart_by_figure, _save_crop


VISION_MODEL = env_load.VISION_MODEL


VISION_URL = env_load.ROUTER_URL


# LOW-47 (Ong Chu 13/09/2026): "khong uu tien su dung tat ca nhung anh nhin
# roi". Do that tren bo Anthropic/Nvidia IPO: anh chup man hinh splash "Claude"
# con dong "loading chart...", do hoa "Nvidia Weighs $10B..." chu in chim sau
# cau quote, tieu de bao Nga RBC — ca ba deu qua cong LIEN_QUAN (dung chu de)
# nhung nhin roi. Chi con mat moi phan biet duoc anh roi voi anh sach.
#
# LOW-165 (15/09/2026): mo rong dinh nghia them nhanh "mang sang/toi/mau lech
# tong cuc bo trai rong hang tram px" — GaussianBlur cuc bo (card._open_region_text)
# chi san phang chi tiet ~QUOTE_BLUR px, KHONG xoa duoc mot mang lon nhu vay du
# blur bao nhieu, nen anh loai nay phai di duong nen dac (_text_bg_strict) thay vi
# blur mac dinh — truoc day chi "chu in san/chup man hinh/cat ghep" moi duoc gan cluttered,
# nen loai mang mau nay lot qua, blur nhe khong xoa het, con "sot" lai.
#
# Doi ten tag ROI -> CLUTTERED (15/09/2026, Ong Chu): "ROI" go khong dau cua "RỐI"
# trung chu voi tu viet tat tieng Anh "return on investment", gay hieu nham khi doc
# code/manifest. Dung han tieng Anh that cho tag + khoa manifest, giai thich van
# bang tieng Viet cho vision model.
SENTENCE_CLUTTERED = ("CLUTTERED: co | khong  (co = anh NHIN ROI: nhieu chu in san de len hinh (tieu de "
           "bao, banner chu, infographic nhoi chu), chup man hinh web/app nhieu chu, cat ghep nhieu "
           "hinh, do hoa/minh hoa nhoi nhet nhieu chi tiet tranh nhau, HOAC co mot mang sang/toi/mau "
           "lech tong RO RET so voi xung quanh trai rong tu vai tram px tro len (vd mot khoi anh chup "
           "khac sang hon/toi hon/mau khac han phan con lai) — loai mang nay lam chu de len tren no "
           "van doc ra loang lo du co lam mo; khong = anh chup that, logo, bien hieu, san pham voi MOT "
           "chu the ro, sang toi deu, hoac bieu do/bang so lieu gon gang)")
# Ong Chu 13/09/2026, cung ngay, ve CHINH do hoa "Nvidia Weighs $10B": "anh nay
# xung dang lam hero, the hien duoc day du moi tu khoa quan trong". Roi thi
# khong uu tien — TRU KHI nhin vao doc ra du tu khoa chinh cua tin.
SENTENCE_KEYWORD = ("TU_KHOA: co | khong  (co = nhin anh DOC RA DU cac tu khoa chinh cua bai: ten cac "
               "cong ty/nhan vat chinh VA con so hoac su kien chinh, vd logo hai hang + so tien + "
               "chu IPO; khong = chi thay mot phan, hoac khong doc ra)")


# LOW-273 (Ong Chu 19/09/2026): "tim hinh co main character dat vua trong 4:5". Hai
# dong do them cho MOI anh (chung mot luot nhin, khong ton them HTTP): hop bao chu the
# chinh + do trong cua tam anh. Do that 19/09 tren 5 anh loi: logo Instinct TRONG 0.90,
# logo SoftBank TRONG 0.93, anh SoftBank cua hang 0.12. Xem subject_fit.py.
SENTENCE_SUBJECT = ("CHU_THE: x0,y0,x1,y1 | loai  (HOP BAO KHIT cua CHU THE CHINH — nhan vat / san pham / "
                    "toa nha / logo / man hinh ma tam anh NOI VE; toa do 0..1 tren TOAN tam anh, goc "
                    "tren-trai la 0,0; NGUOI thi chi khoanh DAU va KHUON MAT; loai = person | product | "
                    "building | logo | screen | chart | other)")
SENTENCE_EMPTY = ("TRONG: 0..1  (phan cua CA tam anh la nen tron/khoang trong, khong co gi: logo nho tren "
                  "nen trang = 0.9, anh chup day khung = 0.05)")


# Man hinh HE THONG (driver/he dieu hanh/terminal) nhac ten hang van khong phai
# anh cua tin (A10 Ubuntu trong tin Broadcom, 05/09/2026) — khac giao dien cua
# chinh san pham trong tin (LOW-216).
SYSTEM_SCREEN = re.compile(r"driver|ubuntu|windows|terminal|c[aà]i \w*", re.I)


def _names_title_product(description: str, names: str) -> bool:
    """Mo ta co goi ten mot cum ten rieng cua tieu de khong (`names` = chuoi
    "A, B" nhu `all_proper_nouns` noi lai). Tinh ca tu dau cua cum ("Claude
    Cowork" -> "Claude"); ten < 4 ky tu (vd "AI") khong tinh."""
    words = set()
    for name in (names or "").split(","):
        name = name.strip()
        if len(name) >= 4:
            words.add(name)
        first = name.split()[0] if name.split() else ""
        if len(first) >= 4:
            words.add(first)
    return any(re.search(r"(?<!\w)" + re.escape(w) + r"(?!\w)", description or "", re.I)
               for w in words)


def description_image(path, tieu_de: str, hang: str = "", hoi_them: str = "",
              nhan_them: str = "", khai_niem: str = "", thuong_hieu: dict | None = None,
              khai_niem_theo_loai: bool = False, chup_nguon: bool = False,
              ket_qua: dict | None = None) -> tuple:
    """Con mat cua day chuyen. Hoi vision local: MOT cau mo ta + LIEN_QUAN co/khong
    theo tieu de bai. Tra ve (mo_ta, lien_quan) — lien_quan None neu KHONG HOI
    DUOC (thieu key, router hong ca hai lan thu lai cua `_call_router`): luc do
    brief noi ro la CHUA ai nhin, dung y nhu tu truoc.

    Ong Chu 12/09/2026, dong CONG FAIL-OPEN: truoc day router TRA LOI duoc
    nhung dong LIEN_QUAN khong doc ra duoc (model lech dinh dang) cung thanh
    None — ma moi noi loc `dung_duoc` deu viet `relevant is not False`, tuc
    None DUOC COI LA DUYET. Do that 12/09 tren may chu: anh Tesla (Terafab) va
    logo Anthropic (truoc khi sua ca thanh cong 32 diem) deu lot bia qua duong
    nay — router CO tra loi, chi la khong parse duoc. Phan biet ro hai ca:
      - KHONG HOI DUOC (thieu key / het luot thu 429-5xx / loi mang) -> giu
        nguyen None, KHONG hoi lai o day (da co backoff rieng o _call_router).
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
    anh cua tin — hoi cau khac (image_concept.sentence_ask_vision), khong hoi "co phai
    anh cua tin" vi chac chan khong, va khong ap override "ten hang trong mo ta".

    `chup_nguon` (LOW-45, 12/09/2026): anh hero CHUP TU CHINH TRANG NGUON
    (`fallback_rounds._round_capture_source`) — LA anh cua tin, cau hoi khong hoi lai "co
    lien quan khong" nua (chac chan co, tu DOM cua chinh bai), CHI hoi CHAT
    LUONG (ro net, khong phai anh bao chup lai mot man hinh khac). Truoc ticket
    nay nhanh `_round_capture_source` bo qua vision HOAN TOAN, ep `relevant = True`
    thang — do that 12/09: anh hero that cua bai Moonshot/Kimi K3 la mot anh
    bao Getty chup nghieng man hinh App Store, van bi ep True du xau, roi
    tam ngang do LAI bi mot vong khac (`_take_image_page`, da chan o LOW-45 phan
    1) chup lai lan nua thanh mot tam khac — ca hai deu khong qua cong chat
    luong nao. Nhanh nay dong no lai."""
    import base64, json as _j, urllib.request
    # `ket_qua` (LOW-47, 13/09/2026): dict nguoi goi truyen vao de nhan them
    # co "roi" (anh nhin roi) ma KHONG doi so phan tu tuple tra ve — Bob va
    # test deu mo goi 2/3 phan tu.
    # env_load.required nem SystemExit, ma SystemExit KHONG phai con cua
    # Exception — `except Exception` o day khong bat duoc. Thieu OPENAI_API_KEY
    # la ca engine chet giua chung, khong co manifest.json, vai chi thay "chua chuan
    # bi" ma khong biet vi sao (06/09/2026). Doc thang bien, khong nem.
    env_load.load()
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
        # mo" tu lau.
        #
        # LOW-201 (16/09/2026, dao LOW-45): tieu chi "anh minh hoa chung chung"
        # va IMAGE_PHRASES_SCREENSHOT (LOW-45, 13/09/2026 — chan anh "chup LAI
        # mot man hinh bang may anh khac") da GO khoi day. Do that: tin
        # "TypeSafe ra System One" (16/09) bi loai oan mot minh hoa bien tap goi
        # dung ten san pham "Jev" (dung nghia illustration, khong phai "chung
        # chung") VA mot screenshot SACH chup thang tu web (khong phai chup lai
        # man hinh bang may anh khac) — ca hai deu dung chu de nhung bi hai tieu
        # chi nay loai oan. Ong Chu 16/09: "ảnh minh hoạ chung chung ko phải vấn
        # đề, ảnh chụp bằng máy ảnh khác cũng ko phải vấn đề". Dieu kien "VA anh
        # phai RO NET" o duoi VAN GIU — anh mo/nghieng that su van bi chan qua
        # duong do, chi rieng "trong giong chup lai man hinh" la go.
        hoi = (f"Bai bao: \"{tieu_de}\"." + (f" Cong ty/san pham chinh: {hang}." if hang else "")
               + "\nTra loi DUNG 2 dong:\n"
               "MO_TA: <mot cau tieng Viet co dau mo ta anh nay la gi>\n"
               "LIEN_QUAN: co | khong  (co = anh/chart/bang ve dung tin nay, HOAC anh tru so/"
               "san pham/logo-tren-toa-nha/su kien cua chinh cong ty trong bai, VA anh phai RO NET; "
               "khong = quang cao, widget, logo bao, placeholder, cong ty/chu de khac)")
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
                   "khong = mo/nhoe)")
        elif khai_niem:
            import image_concept
            hoi = image_concept.sentence_ask_vision(tieu_de, khai_niem, theo_loai=khai_niem_theo_loai)
        elif thuong_hieu:
            # Cau chung hoi "co phai anh CUA TIN khong" — chan dung nha sang lap
            # va the logo chac chan khong phai, nen bi danh rot dung luc ta can
            # chung nhat (09/09/2026).
            import image_brand
            hoi = image_brand.sentence_ask_vision(tieu_de, thuong_hieu)
        # Moi nhanh deu hoi them dong ROI (LOW-47): anh roi khong bi cam, chi
        # xuong cuoi hang uu tien — xem submit_common.check_image_fall.
        hoi = (hoi.replace("DUNG 2 dong", "DUNG 6 dong") + "\n" + SENTENCE_CLUTTERED + "\n" + SENTENCE_KEYWORD
               + "\n" + SENTENCE_SUBJECT + "\n" + SENTENCE_EMPTY)
        if hoi_them and nhan_them:
            hoi = hoi.replace("DUNG 6 dong", "DUNG 7 dong") + f"\n{nhan_them}: {hoi_them}"
        body = {"model": VISION_MODEL, "thinking": {"type": "disabled"}, "max_tokens": 400,
                "stream": False, "temperature": 0,
                "messages": [{"role": "user", "content": [
                    {"type": "text", "text": hoi},
                    {"type": "image_url", "image_url": {"url": "data:image/png;base64," + b64}}]}]}
        req = urllib.request.Request(VISION_URL, data=_j.dumps(body).encode(),
                                     headers={"Content-Type": "application/json",
                                              "Authorization": "Bearer " + key})
        raw = _call_router(req).read().decode().strip()
        if raw.startswith("data:"):
            raw = raw.split("data: [DONE]")[0].strip()[5:].strip()
        txt = _j.loads(raw)["choices"][0]["message"]["content"]
        mo_ta = re.search(r"MO_TA\s*:\s*(.+)", txt)
        # LI[EÊ]N: model tra loi tieng Viet nen hay tu danh dau ca NHAN
        # "LIÊN_QUAN" (dung dau, khac de bai "LIEN_QUAN" khong dau) — regex cu
        # bo lo, roi anh RO RANG khong lien quan (widget gia co phieu A1/A4
        # trong tin TSMC) lai duoc dem la "chua nhin" = dung duoc, xuyen thang
        # qua cong chan lien_quan-is-False (12/09/2026, chay lai task TSMC sau
        # khi ha nguong: 5/5 tro thanh "du 6" chi vi 5 anh cu deu roi vao ke ho
        # nay, khong phai vi tim them anh that).
        lq = re.search(r"LI[EÊ]N[_\s]QUAN\s*:\s*(co|có|khong|không)", txt, re.I)
        mt = mo_ta.group(1).strip()[:200] if mo_ta else txt.strip()[:200]
        lqv = lq.group(1).lower().startswith("c") if lq else None
        if mo_ta and lq is None:
            # Truoc day im lang: mo_ta co (vision CHAY that) nhung lien_quan
            # khong parse duoc thi lqv=None GIONG HET truong hop chua goi duoc
            # router — nguoi doc log khong phan biet noi duoc "chua nhin" that
            # voi "da nhin nhung parse hong".
            print(f"[vision] {Path(path).name}: co MO_TA nhung khong parse duoc dong "
                  f"LIEN_QUAN tu: {txt[:200]!r}", file=sys.stderr)
        rr = re.search(r"^\s*CLUTTERED\s*:\s*(co|có|khong|không)", txt, re.I | re.M)
        cluttered = rr.group(1).lower().startswith("c") if rr else None
        tk = re.search(r"^\s*T[UỪ]_?\s*KHO[AÁ]\s*:\s*(co|có|khong|không)", txt, re.I | re.M)
        du_tk = tk.group(1).lower().startswith("c") if tk else None
        # Chot tat dinh: mo ta neu dung ten hang -> lien quan (anh tru so/san pham
        # Broadcom bi vision phan "khong" luc co luc khong, 05/09/2026).
        # ...nhung chi khi mo ta la BOI CANH hang (tru so/san pham/logo/su kien),
        # khong phai man hinh/driver/phan mem nhac ten hang (A10 Ubuntu 05/09).
        BOI_CANH = re.compile(r"tr[uụ] s[oở]|t[oò]a nh[aà]|campus|logo|s[aả]n ph[aẩ]m|thi[eế]t b[iị]|"
                              r"chip|s[uự] ki[eệ]n|v[aă]n ph[oò]ng|nh[aà] m[aá]y|bi[eể]n hi[eệ]u|"
                              r"headquarters|office|building|product|device|event", re.I)
        KHONG = re.compile(r"m[aà]n h[iì]nh|giao di[eệ]n|c[uử]a s[oổ]|driver|ph[aầ]n m[eề]m|screenshot|"
                           r"ubuntu|windows|terminal|c[aà]i \w*|website|trang web", re.I)
        lqv_vision, override = lqv, ""          # LOW-225: ghi lai vision noi gi TRUOC khi regex lat
        if khai_niem or thuong_hieu or chup_nguon:
            pass                                   # tin cau tra loi, khong override theo ten hang
        elif lqv is False and du_tk and BOI_CANH.search(mt) and not KHONG.search(mt):
            # LOW-164 (15/09/2026): `hang` chi la MOT cum ten rieng dau tieu de
            # (_leading_proper_noun) — bai nhac nhieu hang/nhieu ten goi khac nhau
            # cua cung mot chu de (vd tieu de bat "Opus" nhung mo ta anh lai noi
            # "Claude"/"AMD"/"Ryzen") thi so khop chu-doi-chu voi `hang` luon
            # truot, anh brand/thiet bi dung chu de van bi rot. Vision da tu doc
            # ra DU_TU_KHOA (TU_KHOA: co) cho chinh anh nay roi — dung thang tin
            # hieu do thay vi bat ten hang phai trung tung chu: anh la boi canh
            # hang/thiet bi that (khong phai man hinh/UI) VA vision xac nhan doc
            # ra du tu khoa chinh cua bai thi tinh la lien quan.
            lqv, override = True, "keyword_context_flip_true"
        elif hang and lqv is False and hang.lower() in mt.lower() and BOI_CANH.search(mt) and not KHONG.search(mt):
            lqv, override = True, "brand_name_in_description_flip_true"
        elif lqv is True and KHONG.search(mt) and not BOI_CANH.search(mt) \
                and (SYSTEM_SCREEN.search(mt) or not _names_title_product(mt, hang)):
            # LOW-216 (17/09/2026): tin PHAN MEM thi giao dien LA san pham. Do
            # that tin "Claude Cowork and chat are now one Claude": vision noi
            # "co" cho 9 anh giao dien Claude (menu Docs/Slides, app Cowork)
            # nhung nhanh nay lat het -> Dre chi con logo/dien thoai ngang thap,
            # phai ghep doc. Chi lat khi mo ta KHONG goi ten san pham cua tieu
            # de, hoac la man hinh he thong (driver/Ubuntu — ca goc 05/09).
            lqv, override = False, "screen_ui_flip_false"
        them = ""
        if hoi_them and nhan_them:
            t = re.search(nhan_them + r"\s*:\s*(.+)", txt)
            them = t.group(1).strip()[:120] if t else ""
        return mt, lqv, them, {"cluttered": cluttered, "has_keywords": du_tk,
                               **subject_fit.parse_subject(txt),
                               "vision_said": lqv_vision, "override": override,
                               "vision_raw": {"model": VISION_MODEL, "question": hoi, "answer": txt[:2000]}}

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
            phu["override"] = "unparsed_twice_forced_false"
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


def _call_router(req, _ngu=None):
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


def _classify_hide_whole(a: dict, wd: Path, tieu_de: str) -> dict:
    """classify cho executor.map: mot anh hong (PNG cut, count_faces/crop nem) KHONG
    duoc lam list(ex.map) nem — ca lo mat, ke ca anh da nhin xong, engine chet
    khong manifest.json (audit lượt 2, B-r2-3). Anh hong tro thanh anh "chua nhin"
    co ghi chu, cac anh khac di tiep."""
    try:
        return classify(a, wd, tieu_de)
    except Exception as e:                                   # noqa: BLE001
        print(f"[vision] {a.get('id')} {Path(a.get('original_path', '?')).name}: HONG khi phan loai — "
              f"{type(e).__name__}: {e!r}", file=sys.stderr)
        a.update({"uses": [], "relevant": None, "description": "", "faces": 0,
                  "notes": [f"⚠️ không phân loại được ({type(e).__name__}) — bỏ qua ảnh này"]})
        decision_log.note(a, "process_error", "drop", type(e).__name__, repr(e))
        a.setdefault("w", 0)
        a.setdefault("h", 0)
        return a


def classify(a: dict, wd: Path, tieu_de: str = "", chup_nguon: bool = False) -> dict:
    """Do mot anh bang module luat cua vai dang chay (`role.active_rules()`),
    quyet dinh no DUNG DUOC O DAU, cat san neu can.

    `chup_nguon` (LOW-45): anh hero chup tu chinh trang nguon — xem
    `description_image(..., chup_nguon=True)`."""
    img = Image.open(a["original_path"]).convert("RGB")
    w, h = img.size
    r = w / h
    la_ct, mo_ta = role.active_rules().is_chart(img)
    phang, _ = role.active_rules().measure_chart_signal(img)
    # Override chi khi phep do KHONG noi nguoc: chart that phang >= 82%, anh chup
    # 52-77% (do 05/09). Truoc day hint tu alt tu gan de len ca phang 52% -> hinh
    # minh hoa AI thanh "CHART", dan full be ngang, ra hai vung.
    if not la_ct and phang >= 0.75 and (a.get("chart_hint") or _chart_by_figure(img)):
        la_ct, mo_ta = True, mo_ta + "; nen trang + canh day / alt-tag chart"
    kn = (a.get("concept") or {}).get("keyword", "")
    # Tu khoa do LOAI TIN ep (story_type.py) thi con mat khong duoc tu phan "hop bai".
    kn_theo_loai = (a.get("concept") or {}).get("reason", "") == "theo loại tin"
    # Hang de con mat doi chieu: voi anh THUONG HIEU la hang cua chinh tam anh do,
    # khong phai ten rieng dau tieu de. Tin "Qualcomm ... with Amazon" ma dua
    # "Qualcomm" cho mot tam tru so Amazon thi chot "ten hang trong mo ta" khong
    # bao gio nay, anh that cua Amazon bi vision danh rot (09/09/2026).
    #
    # LIET KE CA (LOW-176, 16/09/2026): mot cum duy nhat (_leading_proper_noun)
    # van la cung mot loi — tin "Anthropic ra tich hop Salesforce" chi hoi
    # con mat ve "Anthropic", nen anh dung chu de nhat cua tin (su kien CHINH
    # cua Salesforce, co logo Salesforce) bi cham "khong lien quan" vi con mat
    # khong biet Salesforce cung la chu the cua bai. `all_proper_nouns` liet ke
    # HET cac cum ten rieng trong tieu de, khong dung o cum dau tien.
    hang = (a.get("brand_match") or {}).get("company") or ", ".join(all_proper_nouns(tieu_de))
    # HOI LUON co cat_ngang duoc khong (12/09/2026, su co t_a8ffd2f6 lan hai):
    # ngang cao >=700 truoc day duoc dan mac dinh "landscape_crop: true NEU la anh
    # nguoi/san pham KHONG co chu" — mot cau DIEU KIEN, khong ai xac nhan dieu
    # kien do co dung hay khong, ma_engine dem no la "dung duoc mot minh". Dre
    # chay that: 4/5 tam ngang cao la chart/logo/bien hieu CO CHU, chi 1 tam la
    # nguoi/san pham that — dem sai 2 slide. Hoi CHUNG mot luot voi mo_ta/lien_quan
    # (khong ton them HTTP), luu vao `a["landscape_crop_ok"]` (True/False/None =
    # khong hoi/khong parse duoc), dung ca o dung[] (cau chu dinh, khong con
    # "NEU") lan o dem slide (schema._only_stack_ok). Ket hop voi `chup_nguon`
    # (LOW-45) — hai co so doc lap, mot anh hero chup tu nguon van co the ngang
    # cao va can hoi cat_ngang binh thuong.
    hoi_cat_ngang = (r >= role.active_rules().LANDSCAPE_CLEAR and h >= 700 and not la_ct)
    kq = {}
    ket_qua = (description_image(a["original_path"], tieu_de, hang, khai_niem=kn,
                         khai_niem_theo_loai=kn_theo_loai,
                         thuong_hieu=a.get("brand_match"), chup_nguon=chup_nguon,
                         hoi_them=("Anh nay co phai la anh CHUP NGUOI hoac SAN PHAM, VA KHONG co "
                                   "chu/logo/so lieu/bieu do de len tren khong (de con cat doc duoc)? "
                                   "Tra loi CHI mot tu: co hoac khong.") if hoi_cat_ngang else "",
                         nhan_them="CAT_NGANG" if hoi_cat_ngang else "", ket_qua=kq)
              if tieu_de else ("", None, "") if hoi_cat_ngang else ("", None))
    if hoi_cat_ngang:
        a["description"], a["relevant"], cn_txt = ket_qua
        cn = re.search(r"(co|có|khong|không)", cn_txt or "", re.I)
        a["landscape_crop_ok"] = (cn.group(1).lower().startswith("c") if cn else None)
        if cn_txt and cn is None:
            print(f"[vision] {a.get('id')}: co tra loi CAT_NGANG nhung khong parse duoc: {cn_txt!r}",
                  file=sys.stderr)
    else:
        a["description"], a["relevant"] = ket_qua
        a["landscape_crop_ok"] = None
    a["cluttered"] = kq.get("cluttered")
    a["has_keywords"] = kq.get("has_keywords")
    # LOW-273: hop bao chu the + do trong (None = vision khong tra/khong doc ra -> fail-open)
    a["subject_box"] = kq.get("subject_box")
    a["subject_kind"] = kq.get("subject_kind")
    a["empty_share"] = kq.get("empty_share")
    # LOW-225: vision noi gi, nhanh regex nao lat, nguyen van cau hoi/tra loi —
    # de do lai offline ma khong goi vision lai.
    if kq.get("vision_raw"):
        a["vision_raw"] = kq["vision_raw"]
        said = kq.get("vision_said")
        decision_log.note(a, "vision", "flag" if said is None else ("keep" if said else "drop"),
                          "LIEN_QUAN", f"vision tra loi {said!r}")
        if kq.get("override"):
            decision_log.note(a, "vision_override", "keep" if a["relevant"] else "drop",
                              kq["override"], f"{said!r} -> {a['relevant']!r}")
    elif tieu_de:
        decision_log.note(a, "vision", "flag", "vision_unavailable",
                          "khong hoi duoc vision (mang/router/thieu key) — lien_quan None")
    # VISION TU NOI "bieu do/do thi" ma cong do hoa (pixel) bo lo (A11, 12/09):
    # tin theo chinh mo ta cua no hon la phep do phang mau — sua nguoc la_ct SAU
    # khi co mo_ta, truoc khi quyet dinh nhanh chart/anh o duoi.
    if not la_ct and re.search(r"biểu đồ|đồ thị|bảng số liệu", a["description"] or "", re.I):
        la_ct = True
        a["landscape_crop_ok"] = None       # la chart thi khong con hoi cat_ngang nua
    # None = cong mat KHONG CHAY (thieu cv2/model, hoac cv2 nem) — khac 0 = da
    # dem, khong co mat. Truoc audit lượt 2 (B-r2-1) day la `or 0`: 4 luong dua
    # nhau tren mot detector lam 80-95% anh tra None, tat ca thanh "khong mat".
    mat_tho = role.active_rules().count_faces(a["original_path"])
    mat = mat_tho or 0
    day = ImageStat.Stat(img.convert("L").crop((0, int(h * .75), w, h))).mean[0]
    goc_trai = ImageStat.Stat(img.convert("L").crop((0, int(h * .55), int(w * .6), h))).mean[0]
    a.update({"w": w, "h": h, "ratio": round(r, 2), "kind": "chart" if la_ct else "photo",
              "chart_stats": mo_ta, "faces": mat, "bottom_brightness": round(day),
              "bottom_left_brightness": round(goc_trai), "short_side": min(w, h),
              "landscape": r >= role.active_rules().LANDSCAPE_CLEAR, "ready_path": None, "uses": [], "notes": []})
    if mat_tho is None:
        a["notes"].append("⚠️ cổng mặt người KHÔNG chạy (thiếu cv2/model hoặc lỗi) — chưa kiểm mặt")
    san = wd / state_paths.READY_DIR / f"{a['id']}.png"
    if la_ct:
        if a.get("ranking"):
            # ANH XEP HANG GIU NGUYEN VEN, khong cat du cao bao nhieu: hang model
            # da khoanh co the nam duoi 55% dai chup (do that: hang #9, #11 bi cat
            # mat), va no la CHU THE cua tin chu khong phai anh minh hoa.
            a["ready_path"] = a["original_path"]
            a["notes"].append("bảng xếp hạng: giữ nguyên vẹn, dán full bề ngang")
        elif r < role.active_rules().TI_LE_45 - role.active_rules().TOLERANCE_RATIO:
            _save_crop(img, san, "4:5", cy=0.35)           # chart cao: cat bot day
            a["ready_path"] = str(san)
            a["notes"].append("chart cao, đã cắt bớt phần dưới về 4:5")
        else:
            a["ready_path"] = a["original_path"]                           # chart giu NGUYEN
        a["uses"] = ["body_chart_full_width"]
        if a["landscape"]:
            a["uses"].append("stack_vertical")
        a["notes"].append("KHÔNG làm bìa")
    else:
        if a["landscape"]:
            a["uses"] = ["stack_vertical"]
            if h < 700:
                # Banner thap (vd 1900x524): cat doc 4:5 chi con ~420px roi phong
                # len 1080 — mem nhoe (do thu 04/09). Chi con duong ghep.
                a["notes"].append("quá thấp để cắt dọc, chỉ ghép")
            elif a.get("landscape_crop_ok") is True:
                a["uses"].append("landscape_crop_confirmed")
            elif a.get("landscape_crop_ok") is False:
                a["notes"].append("có chữ/logo/số liệu đè lên (vision xác nhận) — không được crop, chỉ ghép")
            else:
                # vision khong tra loi duoc cau CAT_NGANG (hong/parse loi) — giu
                # dung dieu kien cu, dung tu quyet dinh thay writer.
                a["uses"].append("landscape_crop_if_no_text")
        else:
            ten = "1:1" if r > 0.9 else "4:5"
            _save_crop(img, san, ten, cy=0.4 if r < 0.7 else 0.5)
            a["ready_path"] = str(san)
            a["uses"] = ["body"]
            if not mat and goc_trai < 150:
                a["uses"].insert(0, "cover")
    if a.get("commons"):
        a["notes"].append("ảnh CHUNG của hãng từ Wikimedia Commons (trụ sở/sản phẩm), không phải ảnh của tin — hợp bìa/slide bối cảnh")
    if mat:
        # MOT ban regex duy nhat, o ban dang ky vai: cong "mat nguoi phai khai
        # ten" cua `role.can_be_hero` phai doc ra dung cai ten ma chu thich
        # duoi day hua la co.
        ten = role.person_names_of(a)
        if ten:
            a["notes"].append(f"CÓ {mat} MẶT NGƯỜI, alt nêu tên: {', '.join(ten[:2])} → "
                                "chỉ dùng khi đúng người đó, khai \"subject\" y hệt")
        else:
            a["notes"].append(f"CÓ {mat} MẶT NGƯỜI mà KHÔNG RÕ AI (alt/caption không nêu tên) → "
                                "KHÔNG DÙNG. Đừng điền tên CEO cho qua cổng — đó là bịa.")
            a["uses"] = [d for d in a["uses"] if d != "cover"]
    if a.get("cluttered") and a.get("has_keywords"):
        a["notes"].insert(0, "⭐ ẢNH RỐI NHƯNG ĐỦ TỪ KHOÁ chính của tin → dùng thoải mái, HỢP LÀM "
                               "BÌA; script tự hiện nguyên bề ngang + đặt nền chữ đặc")
    elif a.get("cluttered"):
        # Anh roi khong du tu khoa: khong la bia; lam than chi khi het anh sach
        # (submit_common.check_image_fall), va script tu dat nen chu dac (LOW-47).
        a["uses"] = [d for d in a["uses"] if str(d) not in manifest_values.COVER_PREFIX_USES]
        decision_log.note(a, "cluttered", "demote", "CLUTTERED_without_keyword", "khong lam bia, xuong cuoi hang")
        a["notes"].insert(0, "⚠️ ẢNH RỐI (chữ in sẵn/đồ hoạ nhồi/cắt ghép) → CHỈ dùng khi HẾT "
                               "ảnh sạch; buộc dùng thì script tự đặt nền chữ đặc")
    if a.get("relevant") is False:
        a["uses"] = []
        decision_log.note(a, "relevance", "drop", "capture_quality" if chup_nguon else "vision_not_relevant",
                          (a.get("description") or "")[:200])
        if chup_nguon:
            # LOW-192: nhanh chup_nguon (LOW-45) KHONG hoi "co lien quan" —
            # cau hoi vision o day chi ve CHAT LUONG (ro net, khong phai anh
            # chup lai man hinh khac). Ghi "KHONG LIEN QUAN BAI" o day la SAI
            # ban chat, danh lua nguoi doc brief/manifest ve sau.
            a["notes"].insert(0, "❌ ẢNH HERO TRANG NGUỒN NHƯNG KHÔNG ĐẠT CHẤT LƯỢNG "
                                   "(mờ/cắt lại từ màn hình khác — vision) → KHÔNG DÙNG")
        else:
            a["notes"].insert(0, "❌ KHÔNG LIÊN QUAN BÀI (vision) → KHÔNG DÙNG")
    if a["short_side"] < role.active_rules().SHORT_SIDE_MIN:
        a["notes"].append(f"cạnh ngắn {a['short_side']}px, phóng lên hơi mềm")
    if day > role.active_rules().BRIGHT_BOTTOM_MAX and not la_ct:
        a["notes"].append("đáy sáng, chữ trắng hơi nhạt")
    if a.get("concept"):
        import image_concept
        truoc = list(a.get("uses") or [])
        image_concept.label_concept(a)
        _note_use_change(a, truoc, "concept_gate", "image_concept.label_concept")
    if a.get("brand_match"):
        import image_brand
        truoc = list(a.get("uses") or [])
        image_brand.label_brand(a)
        _note_use_change(a, truoc, "brand_gate", "image_brand.label_brand")
    if a.get("uses") and a.get("relevant") is not False and role.face_no_clear_ai(a):
        # Van con `uses` nhung schema.count_image_use_ok + submit_common.check_subject_named
        # deu loai tam nay — ghi ro de khong ai tuong no dang duoc dem.
        decision_log.note(a, "face_gate", "drop", "role.face_no_clear_ai",
                          f"{a.get('faces')} mat nguoi, alt/thuong_hieu khong neu ten")
    return a


def _note_use_change(a: dict, truoc: list, stage: str, rule: str) -> None:
    """LOW-225: ham gan nhan (khai niem/thuong hieu) co doi `uses` thi ghi lai."""
    sau = list(a.get("uses") or [])
    if sau != truoc:
        decision_log.note(a, stage, "drop" if truoc and not sau else "demote", rule,
                          f"dung {manifest_values.use_labels(truoc)} -> {manifest_values.use_labels(sau)}")


def _seen_image(anh: list, nguon: dict, title: str, wd: Path) -> tuple:
    """Phan loai + vision tung anh; anh XH khong hoi vision. Tra
    (anh, dung_duoc, chua_nhin)."""
    print("[vision] nhin tung anh, hoi co lien quan bai khong...", file=sys.stderr)
    # Anh XH khong hoi vision (tham so tieu_de rong): no la anh do chinh engine chup
    # tu trang xep hang, da biet chac lien quan — hoi chi ton them mot luot LLM roi
    # ghi de ket qua ngay duoi. Van qua classify de co do hinh hoc (w/h/ti_le/san).
    # `classify` chi doc/ghi vao chinh dict `a` va duong dan rieng cua no -- khong
    # co state dung chung giua cac lan goi -- nen chay song song duoc (8-12 anh/bai,
    # moi anh mot luot HTTP vision tuan tu la cham, audit_content_team B2). Dung
    # executor.map de GIU NGUYEN thu tu ket qua nhu list-comprehension cu.
    with ThreadPoolExecutor(max_workers=env_load.quantity(4)) as ex:
        anh = list(ex.map(lambda a: _classify_hide_whole(a, wd, "" if a.get("ranking")
                                                       else (nguon.get("title_en") or title)), anh))
    for a in anh:
        if a.get("ranking"):
            a["description"] = a["alt"]
            a["relevant"] = True
            decision_log.note(a, "ranking_forced", "keep", "xep_hang", "anh xep hang engine tu chup, khong hoi vision")
            a["uses"] = ["cover_ranking", "body_chart"]
            a["notes"] = [g for g in a["notes"] if "KHÔNG DÙNG" not in g and "KHÔNG làm bìa" not in g]
            a["notes"].insert(0, "✅ ẢNH XẾP HẠNG do engine chụp từ nguồn — dùng làm ảnh chính")
    dung_duoc = [a for a in anh if a["uses"] and a.get("relevant") is not False]
    chua_nhin = [a["id"] for a in anh if a.get("relevant") is None]
    print(f"[anh] {len(dung_duoc)} anh DUNG DUOC / {len(anh)} tai ve"
          + (f"; CHUA NHIN duoc: {', '.join(chua_nhin)}" if chua_nhin else ""), file=sys.stderr)
    return anh, dung_duoc, chua_nhin
