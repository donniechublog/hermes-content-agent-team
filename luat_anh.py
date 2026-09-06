#!/usr/bin/env python3
"""luat_anh.py — BO TIEU CHI ANH DUNG CHUNG cho moi vai lam anh.

Ong Chu chot 04/09/2026: lam MOT bo tieu chi chung thay vi moi vai mot bo.

DUONG CAT — mot cau:
    "Anh nay co DUOC DUNG khong"      -> CHUNG, nam o day.
    "Dat no LEN KHUNG the nao"        -> RIENG tung vai, o lai renderer.

Vi sao phai chung (so lieu thuc do 04/09/2026 trong repo nay):

    Cong chan          card.py(Ethan)  carousel.py(Dre)  deck.py(Itachi)
    mat nguoi              khong            co               khong
    dau vet crop           khong            co               khong
    anh trung              khong            co               khong
    chart nguyen ven       khong            co               khong

Moi luat doi bang may ngay bat loi deu chi nam trong DUNG MOT tep, va nam o do
khong phai vi thiet ke ma vi do la cho Ong Chu bat loi. Khong co ly do nao de
"khong dung mat nguoi la" dung voi Dre ma khong dung voi Ethan hay Itachi.

Gia cua viec chia le da tra roi: trong cung mot ngay, hai phien lam hai lan
cung mot viec "nhan dien chart", va mot ban ra ket qua sai (bo sot chinh cai
chart gay ra su co K2 Horizon).

CACH DUNG: moi ham `kiem_*` tra ve (loi, canh_bao) — hai danh sach chuoi. Vai
tu chon cong nao hop voi khung cua minh roi gop lai. Khong ham nao ve gi, khong
ham nao biet den canvas — de vai nao cung goi duoc.
"""
from pathlib import Path

from PIL import Image, ImageOps, ImageStat

# ---- Nguong (do thuc tren kho anh cua doi, xem chu thich tung cong) --------
TI_LE_45, TI_LE_11 = 0.8, 1.0
DUNG_SAI_TI_LE = 0.03            # dai hop le 4:5..1:1, nong 3%
KHIT = 0.005                     # "dung khit" mot ti le -> dau hieu cat tay
NGANG_RO = 1.4                   # anh goc >= 1.4 la NGANG ro (16:9, 3:2)
CANH_NGAN_MIN = 1000             # duoi nguong nay phong len 1080 se mem
DAY_SANG_MAX = 150               # do sang trung binh 25% duoi anh
CHART_PHANG = 0.85
CHART_SO_MAU = 220
RONG_MAU = 4                     # <= 4 mau rieng biet (sau luong hoa 5 bit) = anh rong
RONG_PHANG = 0.995               # ... va gan nhu 100% cap pixel ke nhau bang nhau
# Anh cao duoi nguong nay so voi khung KHOA KHO thi khung bo trong phan con lai.
# Ti le chieu cao khi trai full be ngang: 16:9 = 0.45, 3:2 = 0.53, 4:3 = 0.60,
# 1:1 = 0.80. Dat 0.50 de chan 16:9 va rong hon; tu 3:2 tro len van qua, vi o do
# phan toi con lai la CHO DAT CHU chu khong phai cho trong.
CAO_TOI_THIEU = 0.50

DAU_PNG = ("crop_ti_le", "nguon_dung")   # cac khoa metadata bao "do doi dung ra"


# ---- Dau vet xuat xu ------------------------------------------------------
def dong_dau(nguon, **them):
    """Tra ve PngInfo mang dau `nguon_dung=<nguon>` (+ cac khoa phu neu co).

    Moi cong cu trong doi sinh ra anh PHAI dong dau: crop_ti_le.py, arxiv_bia.py,
    ghep doc cua carousel.py, chup_chart.py. Cong `kiem_xuat_xu` dua vao dau nay
    de phan biet "anh do doi dung ra" voi "anh cat tay bang cong cu ngoai".
    """
    from PIL.PngImagePlugin import PngInfo
    m = PngInfo()
    m.add_text("nguon_dung", str(nguon))
    for k, v in them.items():
        if v is not None:
            m.add_text(str(k), str(v))
    return m


def dong_dau_tep(duong_dan, nguon):
    """Mo lai mot tep PNG DA LUU va ghi dau `nguon_dung` vao do.

    Cho cac cong cu khong luu bang PIL (playwright screenshot, cv2.imwrite,
    tai thang tu URL). Khong phai PNG thi bo qua, tra ve False — dong dau la
    viec phu, khong duoc lam hong buoc chinh.
    """
    q = Path(duong_dan)
    try:
        im = Image.open(q)
        if (im.format or "").upper() != "PNG":
            return False
        im.load()
        im.save(q, "PNG", pnginfo=dong_dau(nguon))
        return True
    except Exception:
        return False


def _text(img):
    return (getattr(img, "text", None) or img.info or {})


def doc_dau_crop(img):
    """Dau vet crop_ti_le.py -> (w_goc, h_goc), hoac None."""
    m = _text(img).get("crop_ti_le")
    if not m:
        return None
    try:
        goc = [k for k in m.split(";") if k.startswith("goc=")][0][4:]
        w, h = goc.lower().split("x")
        return int(w), int(h)
    except Exception:
        return None


def doc_cat_ngang(img):
    """crop_ti_le.py co duoc phep cat BE NGANG tam nay khong (co --cat-ngang)?

    Day la mot UY QUYEN da ghi lai luc cat, tuong duong `crop_ok` khai trong
    spec — chi khac la no duoc dong dau ngay tai cho cat nen khong khai lai
    duoc. `kiem_crop_ngang` nhan ca hai."""
    return _text(img).get("crop_ti_le", "").find("cat_ngang=1") >= 0


def la_xep_hang(img):
    """Anh do xep_hang.py dung: bang xep hang chup tu nguon (co khoanh model) hoac
    the du phong. Voi tin xep hang thi DAY LA CHU THE cua tin (Ong Chu 06/09/2026),
    nen no duoc mien hai cong von cam chart len bia/hero."""
    return _text(img).get("nguon_dung") in ("chup_xep_hang", "the_xep_hang")


def doc_xep_hang(img) -> dict:
    """Dau xep hang: {model, hang, site, bang, nguon, url} — rong neu khong phai."""
    t = _text(img)
    if not la_xep_hang(img):
        return {}
    return {k: t.get(k) for k in ("model", "hang", "site", "bang", "nguon", "url") if t.get(k)}


def co_xuat_xu(img):
    """Anh co dau vet cua bat ky cong cu nao trong doi khong."""
    t = _text(img)
    return any(t.get(k) for k in DAU_PNG)


def la_ghep(img):
    """Anh nay co phai ban GHEP DOC do doi dung ra khong."""
    return _text(img).get("nguon_dung") == "ghep_doc"


# ---- Do luong anh ---------------------------------------------------------
def do_chart(img, w=480):
    """(phang, so_mau). Thuan PIL — venv tren server khong chac co numpy.

      phang  — ti le cap pixel KE NHAU theo hang gan nhu bang nhau (lech <= 2).
               Do hoa vector (chart, bang, UI) toan mang phang voi vai buoc nhay
               dung; anh chup that thi moi pixel lech nhau mot chut.
      so_mau — so mau RIENG BIET sau khi luong hoa 5 bit/kenh. Day la phep do
               tach bach nhat: chart/screenshot dung mot bang mau tay nen ra vai
               chuc mau, anh chup that ra hang nghin.

    Thu nho bang NEAREST chu KHONG phai LANCZOS: LANCZOS lam nhoe vung phang cua
    screenshot thanh gradient, tuc la xoa dung cai dau hieu can do.

    Do tren 16 the that trong drafts/ (anh that + scrim phang, tinh huong KHO
    nhat): phang 0.31..0.95, so_mau 350..4552 — khong tam nao bi goi nham la
    chart. Chart/screenshot do duoc: phang 0.89..0.99, so_mau 42..65. Nguong dat
    giua khoang trong do va phai dung CA HAI.
    """
    h = max(1, round(img.height * w / img.width))
    v = img.convert("RGB").resize((w, h), Image.NEAREST)
    px = v.convert("L").tobytes()
    bang = tong = 0
    for y in range(h):
        r = px[y * w:(y + 1) * w]
        for i in range(w - 1):
            tong += 1
            if abs(r[i] - r[i + 1]) <= 2:
                bang += 1
    phang = bang / max(1, tong)
    mau = ImageOps.posterize(v, 5).getcolors(w * h) or []
    return phang, len(mau)


def la_chart(img):
    """`img` co phai chart / bang / screenshot / slide khong -> (bool, mo_ta).

    UOC LUONG, khong phai su that. Do thuc 04/09/2026 cho thay no BO SOT chart
    co duong mau khu rang cua: training-losses.png cua K2 Horizon ra 1176 mau
    nen bi cham la "khong phai chart", trong khi do dung la chart gay ra su co.
    Vi vay `kiem_chart` chi dung ket qua nay theo MOT CHIEU — xem chu thich o do.
    """
    phang, so_mau = do_chart(img)
    return (phang >= CHART_PHANG and so_mau <= CHART_SO_MAU), \
           f"phang {phang:.0%}, chi {so_mau} mau"


def dhash(im, kich=8) -> int:
    """Difference hash: hai anh cung noi dung (khac co, khac nen, JPEG lai) cho
    hash gan nhau. Dung de bat "dung lai anh" ma khong can trung byte."""
    g = im.convert("L").resize((kich + 1, kich), Image.LANCZOS)
    px = list(g.getdata())
    return sum(((px[r * (kich + 1) + c] > px[r * (kich + 1) + c + 1]) << (r * kich + c))
               for r in range(kich) for c in range(kich))


def gan_giong(h1: int, h2: int, nguong: int = 6) -> bool:
    return bin(h1 ^ h2).count("1") <= nguong


def _so_da_dung():
    """state/<brand>/anh_da_dung.jsonl — moi dong mot anh da GUI DI (khong phai
    ung vien). Ghi o buoc gui album, doc o buoc nop."""
    import env_load
    return env_load.state_dir() / "anh_da_dung.jsonl"


def ghi_da_dung(duong_dan, draft_id: str, vai: str) -> None:
    import hashlib, json, time
    q = Path(duong_dan)
    try:
        with Image.open(q) as im:
            h = dhash(im)
        md5 = hashlib.md5(q.read_bytes()).hexdigest()
    except Exception:                                        # noqa: BLE001
        return
    dong = {"dhash": h, "md5": md5, "draft_id": draft_id, "vai": vai,
            "ten": q.name, "luc": int(time.time())}
    with open(_so_da_dung(), "a", encoding="utf-8") as f:
        f.write(json.dumps(dong, ensure_ascii=False) + "\n")


def kiem_da_dung(nhan, duong_dan, draft_id: str, so_ngay: int = 14):
    """KHONG DUNG LAI ANH DA DUNG (Ong Chu chot 06/09/2026): bang ti so giai golf
    Ricoh len hai the cua hai tin khac nhau trong cung mot ngay.

    So theo dHash (gan giong <= 6 bit) chu khong theo ten/byte, vi cung mot tam
    tai lai tu bao khac se khac byte. Bo qua chinh draft nay (lam lai mot bai thi
    duoc giu anh). Cua so `so_ngay` — "trong phien" hieu la vai tuan gan day:
    nguoi doc kenh nho anh lau hon mot ngay.
    """
    import hashlib, json, time
    so = _so_da_dung()
    if not so.exists():
        return [], []
    try:
        with Image.open(duong_dan) as im:
            h = dhash(im)
        md5 = hashlib.md5(Path(duong_dan).read_bytes()).hexdigest()
    except Exception:                                        # noqa: BLE001
        return [], []
    moc = time.time() - so_ngay * 86400
    for line in so.read_text(encoding="utf-8").splitlines():
        try:
            d = json.loads(line)
        except Exception:                                    # noqa: BLE001
            continue
        if d.get("draft_id") == draft_id or d.get("luc", 0) < moc:
            continue
        if d.get("md5") == md5 or gan_giong(int(d.get("dhash", 0)), h):
            khi = time.strftime("%d/%m %H:%M", time.localtime(d.get("luc", 0)))
            return [f"{nhan}: TRUNG anh da dung o bai '{d.get('draft_id')}' ({d.get('vai')}, {khi}) — "
                    "moi tin mot anh, nguoi doc kenh nhan ra anh lap lai ngay. Tim anh khac."], []
    return [], []


def lech_tone(ims, nguong_sang=60, nguong_mau=70):
    """Hai anh ghep chung khung ma TONE lech nhau nhieu thi doc ra nhu HAI VUNG
    rieng biet (Ong Chu chot 03/09/2026, siet thanh cong chan 04/09)."""
    ds = []
    for im in ims:
        nho = im.resize((64, 64))
        ds.append((ImageStat.Stat(nho.convert("L")).mean[0],
                   ImageStat.Stat(nho).mean))
    ra = []
    for i in range(len(ds) - 1):
        (l1, c1), (l2, c2) = ds[i], ds[i + 1]
        d_sang = abs(l1 - l2)
        d_mau = sum((a - b) ** 2 for a, b in zip(c1, c2)) ** 0.5
        if d_sang > nguong_sang or d_mau > nguong_mau:
            ra.append(f"anh {i+1} va {i+2} lech tone (sang {l1:.0f} vs {l2:.0f}, "
                      f"mau lech {d_mau:.0f}) — hai vung nhin tach roi; uu tien "
                      "hai anh CUNG tone (cung nen sang/toi, cung gam mau)")
    return ra


_YUNET = None
_YUNET_DA_THU = False


def _yunet():
    global _YUNET, _YUNET_DA_THU
    if _YUNET_DA_THU:
        return _YUNET
    _YUNET_DA_THU = True
    try:
        import os as _os
        _os.environ.setdefault("OPENCV_LOG_LEVEL", "SILENT")
        import cv2
        m = Path(__file__).resolve().parent / "assets" / \
            "face_detection_yunet_2023mar.onnx"
        if not m.exists():
            return None          # thieu model -> bo qua cong, khong crash build
        _YUNET = cv2.FaceDetectorYN_create(str(m), "", (320, 320),
                                           score_threshold=0.7)
    except Exception:
        _YUNET = None
    return _YUNET


def dem_mat(path):
    """So mat nguoi trong anh. None neu khong chay duoc (thieu cv2/model)."""
    det = _yunet()
    if det is None:
        return None
    try:
        import cv2
        im = cv2.imread(str(path))
        if im is None:
            return None
        h, w = im.shape[:2]
        det.setInputSize((w, h))
        _n, res = det.detect(im)
        return 0 if res is None else len(res)
    except Exception:
        return None


# ---- Cong chan: moi ham tra ve (loi, canh_bao) ----------------------------
def la_anh_rong(img):
    """Anh co RONG khong (trang tron / mot mau phang) -> (bool, mo_ta).

    Bo Broadcom dcgr 04/09/2026: buoc chup tra ve anh trang tron (2 mau, phang
    100%), khong cong nao bat, ra mot slide trong tron chi co chu. Tro treu:
    anh trang la thu "giong chart" NHAT theo do_chart, nen cong chart cho qua.

    Do tren 76 anh trong kho: anh rong = 2 mau; anh that it mau nhat = 40 mau
    (screenshot UI toi hai tone). Cach nhau 20 lan nen nguong 4 la an toan —
    khac han cac phep do "slide trong" da thu va bo (chung chong lan voi chart
    sach). Day la RONG thuc su, khong phai "thua".
    """
    ph, mau = do_chart(img)
    return (mau <= RONG_MAU and ph >= RONG_PHANG), f"{mau} mau, phang {ph:.0%}"


def kiem_anh_rong(nhan, img):
    """Anh rong (trang tron / mot mau) -> CHAN. Goi TRUOC kiem_chart, neu khong
    thong bao se la "chart thieu co" thay vi "anh khong co gi"."""
    rong, mo_ta = la_anh_rong(img)
    if rong:
        return [f"{nhan}: anh RONG ({mo_ta}) — khong co noi dung nao de hien. "
                "Thuong la buoc chup tra ve trang trang (trang chua render, "
                "selector bat nham phan tu rong, hoac tai ve tep hong). Mo anh "
                "ra XEM truoc khi ghi vao spec; chup lai bang chup_chart.py "
                "hoac chon anh khac."], []
    return [], []


def kiem_chart(nhan, img, khai_chart, la_bia=False):
    """Chart phai NGUYEN VEN va FULL BE NGANG (Ong Chu chot 04/09/2026).

    CONG NAY MOT CHIEU, co chu y:

      - THIEU co ma may nhan ra la chart  -> CHAN. Sai thi vai khai them co,
        gia rat re.
      - CO co ma may khong nhan ra chart  -> CANH BAO, khong chan. Vi `la_chart`
        bo sot that: bo K2 Horizon lam DUNG (chart goc + "chart": true) tung bi
        chan sach voi ly do "anh khong phai chart (1176 mau)", va thong bao con
        bao vai "bo co di va cat ve 1:1/4:5" — tuc chi thang vao dung cai sai da
        gay ra su co. Chan o chieu nay la giet viec dung.

    Anh GHEP DOC duoc mien han: no da nguyen ven va full be ngang san.
    """
    loi, canh_bao = [], []
    if la_ghep(img) or la_xep_hang(img):
        return loi, canh_bao
    la_ct, mo_ta = la_chart(img)
    if la_ct and not khai_chart:
        if la_bia:
            loi.append(f"{nhan}: BIA la chart/screenshot ({mo_ta}). Bia co hook de "
                       "len anh nen chart nam duoi chu, doc khong ra. Ghep DOC hai "
                       'anh ngang cung tone ("images": [a, b]), hoac de chart o '
                       'SLIDE THAN voi "chart": true va tim anh khac lam bia.')
        else:
            loi.append(f"{nhan}: anh nay LA CHART/SCREENSHOT ({mo_ta}) ma slide "
                       'khong khai "chart": true. Them co do vao slide — anh se '
                       "duoc dan FULL BE NGANG NGUYEN VEN (khong crop, khong ep "
                       "ti le). Do la duong duy nhat giu tron tieu de, truc va "
                       "nhan cua chart.")
    elif khai_chart and not la_ct and not la_bia:
        canh_bao.append(f"{nhan}: khai \"chart\": true nhung may khong nhan ra la "
                        f"chart ({mo_ta}) — phep do nay bo sot chart co duong mau "
                        "khu rang cua, nen neu dung la chart thi CU DE CO. Chi xem "
                        "lai neu day thuc su la anh chup thuong.")
    return loi, canh_bao


def kiem_anh_thap(nhan, w_anh, h_anh, w_khung, h_khung, da_ghep=False):
    """Anh QUA NGANG so voi mot khung KHOA KHO -> khung bo trong phan con lai.

    Ong Chu bat loi 04/09/2026 (the "Nvidia thau tom Hugging Face"): anh 16:9
    trai full be ngang 1200 chi cao 675, tuc 45% kho 4:5. Nua tren la anh, 55%
    con lai la ban cover lam mo — mot mang bun khong mang thong tin gi. Man toi
    lien mach chi xoa duoc cai MEP giua hai lop, khong xoa duoc chuyen nua khung
    bo trong.

    CHI goi cong nay khi khung KHOA KHO (vd card.py --kieu quote, carousel).
    Khung troi theo anh (card.py --kieu dai) hoac khung co lop nen vung chu cao
    len bu (--kieu tran) thi khong dinh: o do phan thieu duoc bu that.

    Anh GHEP DOC mien han — do chinh la duong ra cua cong nay.
    """
    loi, canh_bao = [], []
    if da_ghep or not w_anh or not h_anh:
        return loi, canh_bao
    nat_h = round(w_khung * h_anh / w_anh)
    if nat_h >= h_khung * CAO_TOI_THIEU:
        return loi, canh_bao
    loi.append(
        f"{nhan}: anh QUA NGANG cho khung {w_khung}x{h_khung}. Trai full be "
        f"ngang thi no chi cao {nat_h}px = {nat_h/h_khung:.0%} khung, "
        f"{1-nat_h/h_khung:.0%} con lai la ban cover lam mo — mot mang bun "
        "khong mang thong tin gi. Duong ra: tim them MOT anh ngang nua CUNG "
        "TONE trong cung bai roi ghep DOC (card.py: --image2; carousel: "
        '"images": [a, b]) — hai anh 16:9 xep lai cao 90% khung. Hoac tim anh '
        "dung/gan vuong hon: tu 3:2 tro len la du.")
    return loi, canh_bao


def kiem_lech_tone(nhan, ims):
    """Hai anh sap GHEP DOC ma lech tone thi chan.

    Do luong nam o `lech_tone`; day la phan QUYET DINH. Tach ra thanh cong rieng
    vi ghep doc la duong ra duoc EP dung boi `kiem_anh_thap` va `kiem_chart` —
    ep nguoi ta vao mot duong ma de chinh duong do hong lang thi vo nghia.
    """
    canh = lech_tone(ims)
    if not canh:
        return [], []
    return ([f"{nhan}: " + "; ".join(canh) + ". Ghep chung khung thi doc ra dung "
             "HAI VUNG rieng biet — thu ma ca hero lan carousel deu cam. Tot "
             "nhat lay hai anh trong CUNG MOT BO anh cua bai."], [])


def kiem_chart_mot_minh(nhan, img, da_ghep=False):
    """Chart di MOT MINH vao mot khung dat CHU DE LEN anh phu kin -> CHAN.

    Khac `kiem_chart` (do la chuyen khai co "chart": true cho slide than). Cong
    nay danh cho khung kieu hero/bia: anh phu kin va mot man toi an ~40% day de
    chu doc duoc. Chart nam mot minh o do la mat nua duoi cua chinh no — truc x,
    chu thich, dong nguon. Chart phai NGUYEN VEN va TRAI FULL BE NGANG.

    Anh GHEP DOC duoc mien: chart nam nua tren con nguyen, anh thu hai o duoi
    chiu man toi. Do la duong ra, khong phai vi pham.
    """
    if da_ghep or la_ghep(img) or la_xep_hang(img):
        return [], []
    la_ct, mo_ta = la_chart(img)
    if not la_ct:
        return [], []
    return ([f"{nhan}: CHART DI MOT MINH vao khung co chu de len anh ({mo_ta}). "
             "Nua duoi cua chart chim han duoi man toi: mat truc x, chu thich, "
             "dong nguon. Ba duong ra: (1) tim them mot anh ngang CUNG TONE roi "
             "ghep DOC (card.py --image2 / carousel \"images\": [a, b]) — chart "
             "nam nua tren con nguyen; (2) de chart cho slide than voi "
             "\"chart\": true, o do no duoc dan full be ngang nguyen ven; "
             "(3) doi anh khac lam hero (nguoi, thiet bi, hien truong) va van "
             "dan chart o slide than."], [])


def kiem_xep_hang(nhan, img, tin_xep_hang: bool, la_chinh: bool = True):
    """TIN XEP HANG thi anh CHINH (hero / bia) PHAI la anh xep hang (Ong Chu chot
    06/09/2026: "noi ve ranking phai la table / chart / standing / rank"; ba the
    lien nhau dung bang ti so golf, bang cau ca tren bang). Anh phu (slide than)
    khong bat, nhung anh chinh ma khong phai bang xep hang thi la FAIL, khong
    phai chuyen thay ly."""
    if not tin_xep_hang or not la_chinh or la_xep_hang(img):
        return [], []
    return ([f"{nhan}: TIN XEP HANG ma anh chinh khong phai bang/chart xep hang. "
             "Engine da chup san bang tu nguon xep hang va khoanh model (ma XH trong "
             "brief) — dung ma do. Khong co ma XH nghia la engine khong chup duoc va "
             "da dung the du phong (ten model + #hang + site); van dung ma XH. Anh "
             "khac cho tin xep hang la sai de tai."], [])


def kiem_ti_le(nhan, p, w, h, lo=TI_LE_45, hi=TI_LE_11, dung_sai=DUNG_SAI_TI_LE):
    """Anh phai nam trong dai 4:5..1:1 (anh ghep doc roi vao giua dai nay)."""
    r = w / h
    if lo - dung_sai <= r <= hi + dung_sai:
        return [], []
    if r >= NGANG_RO:
        # Anh NGANG: crop_ti_le tu choi cat be ngang (can --cat-ngang), va cat
        # be ngang cung la sai huong — mat truc/nhan/cot cuoi. Dan thang sang
        # hai duong dung, dung goi y crop truoc.
        return [f"{nhan}: ti le {w}x{h} ({r:.2f}) khong nam trong 4:5..1:1. Anh "
                f"NGANG thi KHONG cat be ngang: (a) tim them mot anh ngang cung "
                f'tone roi ghep doc, ghi "images": [a, b]; hoac (b) chart/bang '
                f'benchmark thi ghi "chart": true de hien full be ngang nguyen ven '
                f"(slide than). Chi khi la anh chup nguoi/san pham KHONG co chu moi "
                f"duoc cat be ngang: crop_ti_le.py --anh {p} --ra <ra.png> "
                f"--ti-le 4:5 --cat-ngang"], []
    return [f"{nhan}: ti le {w}x{h} ({r:.2f}) khong nam trong 4:5..1:1 — cat "
            f"truoc: venv/bin/python crop_ti_le.py --anh {p} --ra <ra.png> "
            f"[--ti-le 4:5] [--cx/--cy]"], []


def kiem_crop_ngang(nhan, img, w, h, crop_ok=None):
    """Anh goc NGANG ma di qua crop_ti_le.py -> CHAN (Ong Chu bat loi 03/09/2026).

    Chart / bang / slide bi crop ve 4:5 la mat tieu de, mat truc, doc ra vo nghia.
    Chi anh chup nguoi/san pham KHONG co chu moi duoc crop, va co hai cach uy
    quyen: khai "crop_ok" trong spec, HOAC cat bang `crop_ti_le.py --cat-ngang`
    (co do dong dau vao PNG, xem `doc_cat_ngang`).
    """
    goc = doc_dau_crop(img)
    if goc and goc[0] / goc[1] >= NGANG_RO and not crop_ok and not doc_cat_ngang(img):
        return [f"{nhan}: anh goc NGANG {goc[0]}x{goc[1]} da bi crop ve {w}x{h} — "
                "bang/chart/slide/banner co tieu de PHAI NGUYEN VEN, khong crop. "
                'Tim them mot anh ngang cung tone, ghi "images": [a, b] de ghep '
                "doc. Chi anh chup nguoi/san pham KHONG co chu moi duoc crop: "
                'ghi "crop_ok": "<ly do>" vao slide.'], []
    return [], []


def kiem_xuat_xu(nhan, img, w, h):
    """Anh dung khit 4:5/1:1 ma KHONG dau vet -> da cat bang cong cu ngoai.

    Ong Chu bat loi 04/09/2026 (bo K2 Horizon): ca 7 anh deu dung khit 4:5
    (0.7996..0.8004) ma khong anh nao co dau crop_ti_le. Vai cat bang
    PIL/cv2/ImageMagick, nen cong `kiem_crop_ngang` — von chi doc dau vet cua
    crop_ti_le.py — khong thay gi de chan. Cong do hoa ra PHAT nguoi lam dung
    va THA nguoi lach.

    Anh that tai ve gan nhu khong bao gio dung khit (thuc do tren kho anh cua
    doi: 1.16, 1.50, 1.78, 1.91...). Moi cong cu trong doi deu dong dau, nen
    chan o day khong dung vao duong di hop le nao.

    KHONG mien tru bang "crop_ok": crop_ok noi "toi co y crop", cong nay noi
    "crop bang gi thi khong ai biet".
    """
    if co_xuat_xu(img):
        return [], []
    r = w / h
    for dich, ten in ((TI_LE_45, "4:5"), (TI_LE_11, "1:1")):
        if abs(r - dich) <= KHIT:
            return [f"{nhan}: anh {w}x{h} dung khit {ten} ({r:.4f}) ma KHONG co dau "
                    f"vet crop_ti_le.py — day la anh da cat bang cong cu ngoai "
                    f"(PIL/cv2/ImageMagick), vi pham luat 'chi crop qua "
                    f'crop_ti_le.py\'. Chart/bang/slide/banner co chu: DUNG crop — '
                    f'ghi "chart": true (slide than) hoac ghep doc "images": [a, b]. '
                    f"Anh chup khong co chu: cat LAI bang venv/bin/python "
                    f"crop_ti_le.py --anh <goc> --ra <ra.png> --ti-le {ten} "
                    f"(anh GOC NGANG >={NGANG_RO} thi crop_ti_le tu choi cat be ngang, "
                    f"phai them --cat-ngang, va chi duoc lam vay voi anh chup "
                    f"nguoi/san pham KHONG co chu). Anh goc VON DA {ten}: van chay qua "
                    f"crop_ti_le.py mot lan de dong dau (cat 0, khong mat gi)."], []
    return [], []


def kiem_do_phan_giai(nhan, w, h):
    """Canh ngan < 1000px thi phong len 1080 se mem. Canh bao, khong chan —
    anh doc quyen nho van hon anh sai."""
    if min(w, h) < CANH_NGAN_MIN:
        return [], [f"{nhan}: canh ngan {min(w, h)}px < {CANH_NGAN_MIN} — phong len "
                    "1080 se hoi mem, co ban to hon thi thay"]
    return [], []


def kiem_day_sang(nhan, img, tu=0.75):
    """Day anh qua sang thi chu trang de len se nhat. Canh bao."""
    w, h = img.size
    sang = ImageStat.Stat(img.convert("L").crop((0, int(h * tu), w, h))).mean[0]
    if sang > DAY_SANG_MAX:
        return [], [f"{nhan}: 25% duoi anh sang (muc {sang:.0f}/255) — chu trang "
                    "tren scrim ~80% van doc duoc nhung nhat; co anh day toi hon "
                    "thi uu tien"]
    return [], []


def kiem_mat_nguoi(nhan, path, nhan_vat=None):
    """Khong dung anh mot nguoi VO DANH (Ong Chu bat loi 03/09/2026).

    Code chi bao co mat hay khong; vai tu chiu trach nhiem nguoi do co phai
    nhan vat trong bai khong. Co mat la CHAN, tru khi khai "nhan_vat".
    """
    n = dem_mat(path)
    if not n:
        return [], []
    nv = str(nhan_vat or "").strip()
    if nv:
        return [], [f"{nhan}: {n} mat nguoi, khai la '{nv}' — OK neu dung la nguoi "
                    "do; sai ten la bia dat."]
    return [f"{nhan}: phat hien {n} mat nguoi ma KHONG khai nhan vat. Anh nguoi vo "
            "danh / khong lien quan tin la loi (doc ra la stock). Doi sang anh san "
            "pham/screenshot/chart; con neu dung la nhan vat trong bai (CEO phat "
            "bieu, tac gia paper) thi khai ten — carousel/deck: \"nhan_vat\": "
            "\"<ten>\" trong slide; card.py (hero): --nhan-vat \"<ten>\"."], []


def kiem_trung(nhan, path, da_thay):
    """Moi slide mot hinh DUY NHAT. Bat theo NOI DUNG tep (hash), khong theo ten.

    Han che da biet: hai CROP khac nhau cua cung mot tam thi hash khac — cai do
    van phai nho mat nguoi soi.
    """
    import hashlib
    h = hashlib.md5(Path(path).read_bytes()).hexdigest()
    if h in da_thay:
        return [f"{nhan}: trung anh voi {da_thay[h]} — moi slide phai mot hinh "
                "DUY NHAT, tim anh khac"], []
    da_thay[h] = nhan
    return [], []
