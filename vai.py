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
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Vai:
    """Mot vai. `slug` PHAI trung ten thu muc profile that trong HERMES_HOME."""
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


VAI = {v.slug: v for v in [
    # --- ba vai DUNG ANH: moi vai mot cong cu dung anh rieng ---
    # anh_toi_thieu=1: card.py dung MOT tam anh lam nen hero. Su co 10/09/2026:
    # engine anh dung chung ap nguong cua carousel (5, hay 8 voi tin flagship)
    # cho CA Ethan, nen hai bai chi co 2 anh that bi chan o buoc "thieu anh" va
    # Ong Chu doc duoc dong "carousel can toi thieu 5 slide" tren task cua Ethan
    # — trong khi Ethan chi can 1 anh. Nguong phai di theo VAI, khong phai theo
    # module dung dau tien.
    Vai("designer", "Ethan", go=("img", "anh", "ethan"), slug_cu=("ethan", "chad"),
        renderer="card", nhan_anh=True, anh_toi_thieu=1),
    # 5 va 8 la carousel.MIN_SLIDE / carousel.FLAGSHIP_MIN. Chep so o day chu
    # khong import carousel: tep nay la BAN DANG KY, phai nhe (carousel keo theo
    # card + PIL). test_vai giu hai ban khong troi khoi nhau.
    Vai("carousel", "Dre", go=("cr", "dre"), slug_cu=("dre", "heller"),
        renderer="carousel", nhan_anh=True, anh_toi_thieu=5, anh_toi_thieu_flagship=8),
    # "kites": so nhieu tieng Anh — Ong Chu hay go the khi giao nhieu tin cung
    # luc ("3, 4 - Kites"). Thieu no la ca lenh chon bi tu choi (su co 06/09/2026).
    # anh_toi_thieu=1: Kite ve ART VECTOR GOC, anh that chi la hinh chen them —
    # bai khong co anh that van dung duoc bo slide (day cung la ly do
    # route_thieu_anh bo qua han vai nay).
    Vai("carousel-edu", "Kite", go=("edu", "kite", "kites"), slug_cu=("kite",),
        renderer="render_edu", nhan_anh=True, anh_toi_thieu=1),
    # --- vai VIET ---
    Vai("writer", "Miles", go=("cap", "miles"), slug_cu=("miles",), viet=True),
    # --- vai di tim tin / phan tich / chat ---
    Vai("scout", "Finn", slug_cu=("finn",)),
    Vai("nova", "Nova"),
    Vai("market", "Vera", slug_cu=("vera",)),
    Vai("teaser", "Cape", slug_cu=("jean",)),      # doi ten persona Jean -> Cape
    Vai("analyst", "Ada", slug_cu=("ada",)),
    Vai("gin", "Gin"),
    Vai("itachi", "Itachi"),
    Vai("bob", "Bob"),
]}

MAC_DINH_ANH = "designer"
MAC_DINH_VIET = "writer"


_TEN_THUONG = {v.ten.lower(): v.slug for v in VAI.values()}


def ten_hien(slug: str) -> str:
    """Ten persona de in ra bao cao; tra lai chinh slug neu chua khai."""
    v = VAI.get(slug)
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
