#!/usr/bin/env python3
"""BẢN ĐĂNG KÝ VAI — một nguồn sự thật cho slug, tên hiển thị và alias.

Vi sao (audit_content_team A4/F1): tri thuc ve vai nam rai it nhat sau cho —
VAI_ANH / TEN_SANG_CAP / TEN_VAI_ANH / VAI_CAROUSEL / VAI_EDU / SLUG_CU /
_TEN_HIEN trong duyet_giao_viec, cong map "slug -> ten" chep tay lai o
kite_chuan_bi va route_thieu_anh. Them mot vai phai dung tam cho; quen mot cho
thi hong CAM: su co 06/09/2026 "kites" khong khop TEN_SANG_CAP nen lenh chon roi
ve hoi thoai va gui nham cho Finn, con su co 01/09/2026 sidecar ghi slug cu
("dre") lam task nam 'ready' hai ngay vi khong profile nao ten vay.

Nay moi bang cu deu la VIEW dan xuat tu `VAI` o duoi. Them mot vai = them MOT
dong o day (+ mot cap <vai>_chuan_bi/_nop + mot SOUL), khong phai tam cho.

HAI LOAI ALIAS, co y tach doi — chung khong trung nhau:
  `go`      chu ONG CHU CO THE GO khi chon tin ("1 - Kites", "2 - img").
            Chi vai nhan viec truc tiep tu lenh chon moi can.
  `slug_cu` slug NAM TRONG SIDECAR CU tren dia (.img.json/.writer.json doi
            truoc). Dung de doc du lieu cu, khong phai de go.
Vd "chad"/"heller" chi la slug_cu (khong ai go nua), con "img"/"cr"/"kites" chi
la `go` (chua bao gio la ten thu muc profile).

TEN VAI MOI: dat theo TEN NHAN VAT, khong theo role — xem luat trong docstring
cua lop `Vai` ngay duoi.
"""
import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Vai:
    """Mot vai. `slug` PHAI trung ten thu muc profile that trong HERMES_HOME.

    LUAT DAT TEN (Ong Chu, 10/09/2026): **khong bao gio dat slug theo ROLE.**
    Moi vai chi co MOT cai ten, dung y het nhau o moi noi — trong ma nguon, tren
    kanban, trong ten topic Telegram, trong ten cap script. `slug` va `ten` vi
    the chi khac nhau o chu hoa: "jika" / "Jika".

    Vi sao: dat theo role la mot vai co hai ten, va nguoi doc phai thuoc long
    bang doi chieu. Da tra gia mot lan ngay hom dat ten: slug `writer-tech` vua
    ra doi da bi doc nham thanh "vai cua brand dcgr.tech" — brand kia ten co chu
    "tech", con "-tech" trong slug lai chi NGUOI DOC cua brand blog.

    Tam slug theo role cuoi cung (`writer`, `designer`, `carousel`,
    `carousel-edu`, `scout`, `market`, `teaser`, `analyst`) da tra xong o LOW-14
    (10/09/2026): doi mot lan cung voi kanban.db, thu muc profile va topics tren
    may chu. Chung nay nam trong `slug_cu` de doc 337 sidecar cu con tren dia.

    CAN THAN khi doc ma cu: "carousel" con la ten MODULE (`carousel.py`) va gia
    tri `renderer` — hai thu do KHONG phai slug vai, dung doi theo.
    """
    slug: str
    ten: str                                   # ten hien ra bao cao/topic
    go: tuple = ()                             # chu Ong Chu go duoc khi chon tin
    slug_cu: tuple = ()                        # slug cu con nam trong sidecar cu
    renderer: str = ""                         # card | carousel | render_edu
    nhan_anh: bool = False                     # vai DUNG ANH (chon tin giao duoc)
    viet: bool = False                         # vai viet caption
    # So ANH THAT toi thieu de vai nay dung duoc mot san pham. Voi vai carousel
    # con la so SLIDE toi thieu (moi slide mot anh rieng) — hai con so do trung
    # nhau nen `toi_thieu` trong manifest lam duoc ca hai viec; voi Ethan thi
    # KHONG trung, va do chinh la su co 10/09/2026 duoi day.
    anh_toi_thieu: int = 1
    anh_toi_thieu_flagship: int = 0            # 0 = tin flagship khong nang nguong
    # ---- SO LUONG co phai tieu chi cua vai nay khong (LOW-12, 10/09/2026) ----
    # Ong Chu: *"tieu chi ve anh thi la chung cua moi designer, nhung carousel la
    # nhieu anh con Ethan lam single image, nen 'so luong' ko the la thu ap vao
    # duoc"*. Tieu chi CHAT LUONG (net, khong rac, lien quan, day toi) van dung
    # chung o `luat_anh` + `chuan_bi.nhin.phan_loai` cho ca ba vai. Chi hai thu
    # duoi day di theo vai, va chung tra loi hai cau khac han nhau:
    #
    #   anh_muc_tieu_tim  BAO NHIEU tam thi ngung di tim. CHI co nghia voi vai
    #                     xep NHIEU anh (Dre: moi slide mot anh). 0 = vai lam
    #                     SAN PHAM MOT ANH -> khong dem, chi hoi "da co tam nao
    #                     dung lam anh chinh chua".
    #   ti_le_don_max     tam anh phai <= ti le nay moi DUNG MOT MINH duoc, theo
    #                     kho cua renderer. 0 = vai khong xet (moi anh dung duoc
    #                     deu la mot slide, tam lam bia do `phan_loai` dan nhan).
    anh_muc_tieu_tim: int = 0
    anh_muc_tieu_tim_flagship: int = 0
    ti_le_don_max: float = 0.0
    chart_don: bool = True                     # chart dung MOT MINH duoc khong


VAI = {v.slug: v for v in [
    # --- ba vai DUNG ANH: moi vai mot cong cu dung anh rieng ---
    # anh_toi_thieu=1: card.py dung MOT tam anh lam nen hero. Su co 10/09/2026:
    # engine anh dung chung ap nguong cua carousel (5, hay 8 voi tin flagship)
    # cho CA Ethan, nen hai bai chi co 2 anh that bi chan o buoc "thieu anh" va
    # Ong Chu doc duoc dong "carousel can toi thieu 5 slide" tren task cua Ethan
    # — trong khi Ethan chi can 1 anh. Nguong phai di theo VAI, khong phai theo
    # module dung dau tien.
    # anh_muc_tieu_tim=0: card.py dung MOT tam anh — "du 5 anh" khong noi len dieu
    # gi ve viec Ethan co dung duoc bo nay khong (LOW-12). 1.6 = 1200/750, nguong
    # kiem_anh_thap cua card.py o kho 4:5; chart va anh ngang hon the chi con
    # duong ghep doc, khong dung mot minh duoc.
    Vai("ethan", "Ethan", go=("img", "anh"), slug_cu=("designer", "chad"),
        renderer="card", nhan_anh=True, anh_toi_thieu=1,
        ti_le_don_max=1.6, chart_don=False),
    # 5 va 8 la carousel.MIN_SLIDE / carousel.FLAGSHIP_MIN. Chep so o day chu
    # khong import carousel: tep nay la BAN DANG KY, phai nhe (carousel keo theo
    # card + PIL). test_vai giu hai ban khong troi khoi nhau.
    Vai("dre", "Dre", go=("cr",), slug_cu=("carousel", "heller"),
        renderer="carousel", nhan_anh=True, anh_toi_thieu=5, anh_toi_thieu_flagship=8,
        anh_muc_tieu_tim=5, anh_muc_tieu_tim_flagship=8),
    # "kites": so nhieu tieng Anh — Ong Chu hay go the khi giao nhieu tin cung
    # luc ("3, 4 - Kites"). Thieu no la ca lenh chon bi tu choi (su co 06/09/2026).
    # anh_toi_thieu=1: Kite ve ART VECTOR GOC, anh that chi la hinh chen them —
    # bai khong co anh that van dung duoc bo slide (day cung la ly do
    # route_thieu_anh bo qua han vai nay).
    # anh_muc_tieu_tim 5/8: render_edu cung XEP NHIEU SLIDE, nen so luong van la
    # mot tieu chi that. Giu dung so engine van di tim tu truoc LOW-12 — vai nay
    # chua duoc ra lai, va ha xuong la Kite it hinh chen hon truoc.
    Vai("kite", "Kite", go=("edu", "kites"), slug_cu=("carousel-edu",),
        renderer="render_edu", nhan_anh=True, anh_toi_thieu=1,
        anh_muc_tieu_tim=5, anh_muc_tieu_tim_flagship=8),
    # --- vai VIET: MOI BRAND MOT NGUOI VIET (LOW-13, 10/09/2026) ---
    # Hai vai viet KHONG bao gio cung nam trong mot container, dung nhu `finn`
    # (chi blog) va `vera` (chi dcgr) — nen ban dang ky giu ca hai,
    # con moi home chi deploy mot. Ly do tach: nguoi doc hai brand hoi hai cau
    # khac han nhau (xem GIONG trong miles_chuan_bi), va MEMORY da tach theo
    # brand tu 05/09/2026 — bai hoc "bot so lieu, noi tien" cua tin kinh doanh
    # tung ro sang tin model, noi phai giu nguyen tham so va benchmark.
    Vai("miles", "Miles", go=("cap",), slug_cu=("writer",), viet=True),
    Vai("jika", "Jika", viet=True),
    # --- vai di tim tin / phan tich / chat ---
    Vai("finn", "Finn", slug_cu=("scout",)),
    Vai("nova", "Nova"),
    Vai("vera", "Vera", slug_cu=("market",)),
    Vai("cape", "Cape", slug_cu=("teaser", "jean")),   # persona cu: Jean
    Vai("ada", "Ada", slug_cu=("analyst",)),
    Vai("gin", "Gin"),
    Vai("itachi", "Itachi"),
    Vai("bob", "Bob"),
]}

MAC_DINH_ANH = "ethan"
# Nguoi viet MAC DINH khi khong biet gi ca (tin khong ro vai quet lan brand).
# Van la Miles: doi no la doi hanh vi cua moi duong cu chua kip truyen boi canh.
MAC_DINH_VIET = "miles"

# --- AI VIET TIN NAY (LOW-13) -----------------------------------------------
# Truoc 10/09/2026 chi co MOT nguoi viet, nen `MAC_DINH_VIET` la hang so va moi
# cho cu goi thang no. Gio co hai, va cau tra loi phu thuoc TIN — nen phai hoi
# qua `vai_viet_cua`, dung doc hang so.
#
# Hai bang, hoi theo THU TU nay, va thu tu do co ly do:
#   1. VAI QUET — chinh xac nhat, vi day la dieu Ong Chu chot: "vai viet di theo
#      vai quet". Biet vai quet la biet linh vuc that cua tin.
#   2. BRAND — luoi an toan cho cac duong khong cam theo vai quet (vd
#      `approve_service push` chi co draft_id + category). Hom nay hai bang cho
#      CUNG ket qua vi finn/nova nam ca o blog con vera o dcgr; giu ca hai la
#      de hom nao mot vai quet doi container thi ve (1) van dung ngay.
VIET_THEO_QUET = {
    "finn": "jika",                # Finn — HN/Reddit/arXiv
    "nova": "jika",                # Nova — model moi ra mat
    "vera": "miles",               # Vera — kinh doanh, dau tu
}

# Nhan CA khoa container ('blog') lan slug dai ('donniechublog'): brand di qua
# sidecar cua bai thi la slug dai, con qua CT_BRAND thi la khoa container.
# Chep hai chinh ta o day chu khong import env_load: tep nay la BAN DANG KY,
# giu khong phu thuoc (test_vai kiem hai ban khong troi khoi nhau).
VIET_THEO_BRAND = {
    "blog": "jika",
    "donniechublog": "jika",
    "dcgr": "miles",
    "dcgr.tech": "miles",
}


def vai_viet_cua(vai_quet=None, brand=None) -> str:
    """Slug nguoi viet cho mot tin: hoi VAI QUET truoc, roi toi BRAND.

    Khong nhan ra ca hai -> `MAC_DINH_VIET`. Nguoi goi nen keu mot dong khi roi
    vao day: mot tin khong biet ai quet lan thuoc brand nao la mot chuyen khac,
    va im lang o day thi bai cua blog roi vao topic cua Miles ma khong ai hay."""
    q = VIET_THEO_QUET.get(str(vai_quet or "").lower())
    if q:
        return q
    b = str(brand or "").lower()
    return VIET_THEO_BRAND.get(b, MAC_DINH_VIET)


_TEN_THUONG = {v.ten.lower(): v.slug for v in VAI.values()}


def ten_hien(slug: str) -> str:
    """Ten persona de in ra bao cao; tra lai chinh slug neu chua khai.

    Giai qua `slug_that` truoc: sau LOW-14 con 337 sidecar tren dia ghi slug
    role cu ("carousel", "designer"...). Tra thang VAI.get thi Ong Chu doc duoc
    dong "chuyen tu carousel" thay vi "chuyen tu Dre" — dung cai kieu lan lon
    role/name ma LOW-14 sinh ra de dep."""
    v = VAI.get(slug) or VAI.get(slug_that(slug))
    return v.ten if v else slug


def slug_that(chu: str) -> str:
    """Chu bat ky (ten cu trong sidecar, ten persona) -> slug profile hien tai.

    Khong nhan ra thi TRA LAI NGUYEN VAN — nguoi goi (chuan_assignee) con kiem
    profile co that khong roi bao loi tu te, dung nuot o day."""
    c = str(chu).lower()
    # Ten persona hien tai (Cape, Nova...) cung la mot cach goi hop le — N-r2-10:
    # "cape" khong co trong go/slug_cu nen tung tra nguyen "cape", chuan_assignee
    # bao "khong co profile cape" trong khi moi persona khac deu tu resolve.
    return _SLUG_CU.get(c) or _TEN_THUONG.get(c, chu)


def so_anh_toi_thieu(slug: str, flagship: bool = False) -> int:
    """So ANH THAT toi thieu de vai `slug` dung duoc san pham cua no.

    Vi sao la ham o day chu khong phai hang so trong carousel.py: engine anh
    (`anh_chuan_bi.chuan_bi`) chay CHUNG cho ca ba vai dung anh va truoc
    10/09/2026 no lay thang `carousel.MIN_SLIDE`/`FLAGSHIP_MIN` — tuc ap luat
    cua Dre cho Ethan lan Kite. Hau qua: bai giao Ethan chi co 2 anh (rat
    thuong gap voi tin khong phai benchmark) bi ket o buoc "thieu anh", roi
    Telegram noi voi Ethan bang tieng cua carousel ("chuyen Kite ve vector",
    "can toi thieu 5 slide") du card.py chi can 1 anh.

    Vai la khong biet -> nguong cua vai anh mac dinh (Ethan). Nguoi goi nen
    keu mot dong khi roi vao day: sidecar mat `vai_anh` la mot chuyen khac."""
    v = VAI.get(slug) or VAI[MAC_DINH_ANH]
    if flagship and v.anh_toi_thieu_flagship:
        return v.anh_toi_thieu_flagship
    return v.anh_toi_thieu


# Ten rieng >= 2 tu trong alt/caption ("Jensen Huang"). MOT ban duy nhat: chu
# thich anh cua `chuan_bi.nhin.phan_loai` va cong "mat nguoi phai khai ten" duoi
# day phai doc ra CUNG mot cai ten, khong duoc moi noi mot regex.
_TEN_NGUOI = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+")


def ten_nguoi_trong_alt(alt: str) -> list:
    """Cac ten nguoi neu trong alt/caption cua mot tam anh."""
    return _TEN_NGUOI.findall(alt or "")


def anh_chinh_duoc(slug: str, a: dict) -> bool:
    """Tam anh `a` (mot muc trong manifest) co dung MOT MINH lam ANH CHINH cua
    vai `slug` khong — bia cua bo carousel, hay nen hero cua the card.

    Tieu chi CHAT LUONG (net, khong rac, lien quan bai) khong nam o day: chung
    dung chung cho moi vai va da chay o `luat_anh` + `chuan_bi.nhin.phan_loai`.
    Ham nay chi tra loi phan di theo KHO cua renderer."""
    v = VAI.get(slug) or VAI[MAC_DINH_ANH]
    if a.get("lien_quan") is False or not a.get("dung"):
        return False
    if a.get("xep_hang"):
        return True                            # anh chinh BAT BUOC cua tin xep hang
    if not v.ti_le_don_max:
        # Vai xep NHIEU anh: "anh chinh" la tam lam BIA, nhan do phan_loai dan.
        return "bìa" in a["dung"]
    if a.get("loai") == "chart" and not v.chart_don:
        return False
    if float(a.get("ti_le") or 0) > v.ti_le_don_max:
        return False
    # Mat nguoi khong ro ai: `nop_chung.kiem_nhan_vat` chan, ma vai thi khong
    # duoc bia ten cho qua cong — tam do khong phai mot duong dung duoc.
    if a.get("mat") and not ((a.get("thuong_hieu") or {}).get("nguoi")
                             or ten_nguoi_trong_alt(a.get("alt") or "")):
        return False
    return True


def so_anh_muc_tieu_tim(slug: str, flagship: bool = False) -> int:
    """Bao nhieu tam thi NGUNG di tim. 0 = vai lam san pham mot anh, so luong
    khong phai tieu chi cua no — hoi `du_nguyen_lieu` thay vi so sanh con so nay."""
    v = VAI.get(slug) or VAI[MAC_DINH_ANH]
    if flagship and v.anh_muc_tieu_tim_flagship:
        return v.anh_muc_tieu_tim_flagship
    return v.anh_muc_tieu_tim


def du_nguyen_lieu(slug: str, dung_duoc: list, flagship: bool = False) -> bool:
    """Vai `slug` DA DU nguyen lieu chua — engine con phai di tim anh nua khong.

    Hai ve, va ve thu hai KHONG ap cho moi vai (Ong Chu 10/09/2026: *"carousel
    la nhieu anh con Ethan lam single image, nen 'so luong' ko the la thu ap vao
    duoc"*):

      1. phai co it nhat MOT tam dung lam anh chinh — moi vai deu can;
      2. va du so tam — CHI voi vai xep nhieu anh (`anh_muc_tieu_tim`), vi o do
         moi slide an mot tam that. Vai lam san pham mot anh de so nay bang 0.

    Truoc LOW-12 engine hoi ve thu hai bang so cua carousel (5, hay 8 voi tin
    flagship) cho CA Ethan: tin co 5 anh ngang 16:9 dem ra "du 5" nen engine
    ngung tim, trong khi card.py chan anh ngang >1.6 di mot minh — Ethan con 0
    duong dung, ma brief thi cam vai tu tai them."""
    if not any(anh_chinh_duoc(slug, a) for a in dung_duoc):
        return False
    # muc = 0 (vai mot anh): ve nay luon dung, tuc chi con ve thu nhat.
    return len(dung_duoc) >= so_anh_muc_tieu_tim(slug, flagship)


def don_vi_san(slug: str) -> str:
    """Chu de goi mot don vi san pham cua vai: "slide" hay "ảnh".

    Dung cho cau bao gui Ong Chu. Goi the don cua Ethan la "slide" chinh la
    thu lam su co 10/09/2026 doc ra nhu "Ethan khong tao duoc slide"."""
    v = VAI.get(slug)
    return "slide" if v and v.renderer in ("carousel", "render_edu") else "ảnh"


# ---- CAC VIEW DAN XUAT (bang cu, giu y nguyen ngu nghia) --------------------
# Thu tu chen giu nhu ban viet tay cu de so sanh diff cho de.

def _map_go(loc):
    ra = {}
    for v in VAI.values():
        if loc(v):
            ra[v.slug] = v.slug
            for g in v.go:
                ra[g] = v.slug
    return ra


# Chu go duoc khi chon tin -> slug vai ANH (gom ca chinh slug).
VAI_ANH = _map_go(lambda v: v.nhan_anh)

# Ong Chu go TEN NAO CUNG DUOC: ten nguoi VIET cung ra cap anh mac dinh, vi mot
# lua chon sinh ra mot CAP di lien nhau (nguoi dung anh lam cha, nguoi viet lam
# con) — bat nho ai dung anh ai viet la bat nho mot thu khong can nho.
TEN_SANG_CAP = dict(VAI_ANH)
TEN_SANG_CAP.update({k: MAC_DINH_ANH
                     for v in VAI.values() if v.viet
                     for k in (v.slug,) + v.go})

VAI_CAROUSEL = {v.slug for v in VAI.values() if v.renderer == "carousel"}
VAI_EDU = {v.slug for v in VAI.values() if v.renderer == "render_edu"}

TEN_VAI_ANH = {v.slug: v.ten for v in VAI.values() if v.nhan_anh}
TEN_VAI_VIET = {v.slug: v.ten for v in VAI.values() if v.viet}
TEN_HIEN = {v.slug: v.ten for v in VAI.values()}

# Slug cu (ten nhan vat) -> slug profile hien tai. Sidecar .img.json/.writer.json
# doi truoc con ghi "dre"/"miles"; task tao tu do khong ai nhan va nam 'ready'
# mai (su co 01/09/2026: hai bai dcgr ket 2 ngay).
_SLUG_CU = {cu: v.slug for v in VAI.values() for cu in v.slug_cu}
SLUG_CU = dict(_SLUG_CU)
