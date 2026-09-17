#!/usr/bin/env python3
"""BẢN ĐĂNG KÝ VAI — một nguồn sự thật cho slug, tên hiển thị và alias.

Vi sao (audit_content_team A4/F1): tri thuc ve vai nam rai it nhat sau cho —
ROLE_IMAGE / NAME_BRIGHT_CAP / NAME_ROLE_IMAGE / ROLE_CAROUSEL / ROLE_EDU / SLUG_OLD /
_TEN_HIEN trong approve_dispatch, cong map "slug -> ten" chep tay lai o
kite_prepare va route_missing_images. Them mot vai phai dung tam cho; quen mot cho
thi hong CAM: su co 06/09/2026 "kites" khong khop NAME_BRIGHT_CAP nen lenh chon roi
ve hoi thoai va gui nham cho Finn, con su co 01/09/2026 sidecar ghi slug cu
("dre") lam task nam 'ready' hai ngay vi khong profile nao ten vay.

Nay moi bang cu deu la VIEW dan xuat tu `VAI` o duoi. Them mot vai = them MOT
dong o day (+ mot cap <vai>_prepare/_submit + mot SOUL), khong phai tam cho.

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
class Role:
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
    # Module tieu chi anh RIENG cua vai nay ("" = vai khong dung anh / khong co
    # bo luat rieng). LOW-182 (16/09/2026): moi vai lam anh co MOT module rieng
    # (`image_rules_<vai>.py`) — xem `rules_module()` duoi day.
    rules: str = ""
    # So ANH THAT toi thieu de vai nay dung duoc mot san pham. Voi vai carousel
    # con la so SLIDE toi thieu (moi slide mot anh rieng) — hai con so do trung
    # nhau nen `min_images` trong manifest lam duoc ca hai viec; voi Ethan thi
    # KHONG trung, va do chinh la su co 10/09/2026 duoi day.
    anh_toi_thieu: int = 1
    anh_toi_thieu_flagship: int = 0            # 0 = tin flagship khong nang nguong
    # ---- SO LUONG co phai tieu chi cua vai nay khong (LOW-12, 10/09/2026) ----
    # Ong Chu: *"tieu chi ve anh thi la chung cua moi designer, nhung carousel la
    # nhieu anh con Ethan lam single image, nen 'so luong' ko the la thu ap vao
    # duoc"*. Tieu chi CHAT LUONG (net, khong rac, lien quan, day toi) TUNG dung
    # chung o `image_rules` + `prepare.vision.classify` cho ca ba vai — DAO NGUOC
    # o LOW-182 (16/09/2026, Ong Chu chu dong doi lai): gio ca CHAT LUONG cung di
    # theo vai (`rules` o tren), khong con phan nao chung nua. Hai thu duoi day
    # van la rieng cua vai tu truoc LOW-182, khong doi:
    #
    #   anh_muc_tieu_tim  BAO NHIEU tam thi ngung di tim. CHI co nghia voi vai
    #                     xep NHIEU anh (Dre: moi slide mot anh). 0 = vai lam
    #                     SAN PHAM MOT ANH -> khong dem, chi hoi "da co tam nao
    #                     dung lam anh chinh chua".
    #   ti_le_don_max     tam anh phai <= ti le nay moi DUNG MOT MINH duoc, theo
    #                     kho cua renderer. 0 = vai khong xet (moi anh dung duoc
    #                     deu la mot slide, tam lam bia do `classify` dan nhan).
    anh_muc_tieu_tim: int = 0
    anh_muc_tieu_tim_flagship: int = 0
    ti_le_don_max: float = 0.0
    chart_don: bool = True                     # chart dung MOT MINH duoc khong


ROLE = {v.slug: v for v in [
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
    Role("ethan", "Ethan", go=("img", "anh"), slug_cu=("designer", "chad"),
        renderer="card", nhan_anh=True, anh_toi_thieu=1, rules="image_rules_ethan",
        ti_le_don_max=1.6, chart_don=False),
    # 6 va 7 la carousel.MIN_SLIDE / carousel.FLAGSHIP_MIN (12/09/2026). Chep so o day chu
    # khong import carousel: tep nay la BAN DANG KY, phai nhe (carousel keo theo
    # card + PIL). test_vai giu hai ban khong troi khoi nhau.
    Role("dre", "Dre", go=("cr",), slug_cu=("carousel", "heller"),
        renderer="carousel", nhan_anh=True, anh_toi_thieu=6, anh_toi_thieu_flagship=7,
        anh_muc_tieu_tim=6, anh_muc_tieu_tim_flagship=7, rules="image_rules_dre"),
    # "kites": so nhieu tieng Anh — Ong Chu hay go the khi giao nhieu tin cung
    # luc ("3, 4 - Kites"). Thieu no la ca lenh chon bi tu choi (su co 06/09/2026).
    # anh_toi_thieu=1: Kite ve ART VECTOR GOC, anh that chi la hinh chen them —
    # bai khong co anh that van dung duoc bo slide (day cung la ly do
    # route_missing_images bo qua han vai nay).
    # anh_muc_tieu_tim 5/8: render_edu cung XEP NHIEU SLIDE, nen so luong van la
    # mot tieu chi that. Giu dung so engine van di tim tu truoc LOW-12 — vai nay
    # chua duoc ra lai, va ha xuong la Kite it hinh chen hon truoc.
    Role("kite", "Kite", go=("edu", "kites"), slug_cu=("carousel-edu",),
        renderer="render_edu", nhan_anh=True, anh_toi_thieu=1, rules="image_rules_kite",
        anh_muc_tieu_tim=6, anh_muc_tieu_tim_flagship=7),
    # --- WRITER roles (LOW-13 2026-09-10, LOW-123/LOW-136 2026-09-14) ---
    # BOTH brands have Miles and Jika sharing work by queue (WRITERS_BY_BRAND),
    # differing only in writing voice. Readers of the two
    # brands ask very different questions (see VOICE in miles_prepare), and MEMORY
    # is split per brand since 2026-09-05 — the business-news lesson "fewer figures,
    # talk money" once leaked into model news, which must keep params and benchmarks.
    Role("miles", "Miles", go=("cap",), slug_cu=("writer",), viet=True),
    Role("jika", "Jika", viet=True),
    # --- vai di tim tin / phan tich / chat ---
    Role("finn", "Finn", slug_cu=("scout",)),
    Role("nova", "Nova"),
    Role("vera", "Vera", slug_cu=("market",)),
    # Qinn (12/09/2026) — quet X. Khong tu crawl: doc lai qua GET /tweets cua
    # social-publishing (session X song tren may crawler). CHI brand blog, nhu
    # Finn; chay 4 lan/ngay vi tin X troi nhanh hon HN/arXiv.
    Role("qinn", "Qinn"),
    Role("cape", "Cape", slug_cu=("teaser", "jean")),   # persona cu: Jean
    Role("ada", "Ada", slug_cu=("analyst",)),
    Role("gin", "Gin"),
    Role("itachi", "Itachi"),
    Role("bob", "Bob"),
]}

DEFAULT_IMAGE = "ethan"
# Nguoi viet MAC DINH khi khong biet gi ca (tin khong ro vai quet lan brand).
# Van la Miles: doi no la doi hanh vi cua moi duong cu chua kip truyen boi canh.
DEFAULT_WRITE = "miles"

# --- AI VIET TIN NAY (LOW-13) -----------------------------------------------
# Truoc 10/09/2026 chi co MOT nguoi viet, nen `DEFAULT_WRITE` la hang so va moi
# cho cu goi thang no. Gio co hai, va cau tra loi phu thuoc TIN — nen phai hoi
# qua `writer_for`, dung doc hang so.
#
# Hai bang, hoi theo THU TU nay, va thu tu do co ly do:
#   1. VAI QUET — chinh xac nhat, vi day la dieu Ong Chu chot: "vai viet di theo
#      vai quet". Biet vai quet la biet linh vuc that cua tin.
#   2. BRAND — luoi an toan cho cac duong khong cam theo vai quet (vd
#      `approve_service push` chi co draft_id + category). Hom nay hai bang cho
#      CUNG ket qua vi finn/qinn nam o blog con vera/nova o dcgr (Nova chuyen
#      sang dcgr 14/09/2026, LOW-135); giu ca hai la de hom nao mot vai quet doi
#      container thi ve (1) van dung ngay. Ca hai chi la nguoi viet TAM: brand
#      nao cung co Miles + Jika chia viec theo hang cho (WRITERS_BY_BRAND).
WRITE_BY_SCAN = {
    "finn": "jika",                # Finn — HN/Reddit/arXiv
    "qinn": "jika",                # Qinn — X (tin ky thuat, cung nguoi doc voi Finn)
    "nova": "miles",               # Nova — model moi ra mat (dcgr tu LOW-135)
    "vera": "miles",               # Vera — kinh doanh, dau tu
}

# Nhan CA khoa container ('blog') lan slug dai ('donniechublog'): brand di qua
# sidecar cua bai thi la slug dai, con qua CT_BRAND thi la khoa container.
# Chep hai chinh ta o day chu khong import env_load: tep nay la BAN DANG KY,
# giu khong phu thuoc (test_vai kiem hai ban khong troi khoi nhau).
WRITE_BY_BRAND = {
    "blog": "jika",
    "donniechublog": "jika",
    "dcgr": "miles",
    "dcgr.tech": "miles",
}

# Writers that SHARE the work in each brand: Miles and Jika, who differ only in
# writing voice (blog LOW-123, dcgr LOW-136, both 2026-09-14). `writer_for` only
# gives a TENTATIVE writer at pick time; the real writer is chosen by queue when
# the boss approves the image (approve_post).
WRITERS_BY_BRAND = {
    "blog": ("miles", "jika"),
    "donniechublog": ("miles", "jika"),
    "dcgr": ("miles", "jika"),
    "dcgr.tech": ("miles", "jika"),
}


def writers_for_brand(brand) -> tuple:
    """Writer slugs sharing the work in this brand; empty for an unknown brand."""
    return WRITERS_BY_BRAND.get(str(brand or "").lower(), ())


def pick_by_queue(candidates, waiting: dict, last_assigned: dict) -> str:
    """The writer with the fewest waiting tasks; ties go to whoever was assigned
    least recently, then to the order of `candidates`."""
    return min(candidates, key=lambda slug: (waiting.get(slug, 0), last_assigned.get(slug) or 0,
                                             candidates.index(slug)))


def writer_for(vai_quet=None, brand=None) -> str:
    """Slug nguoi viet cho mot tin: hoi VAI QUET truoc, roi toi BRAND.

    Khong nhan ra ca hai -> `DEFAULT_WRITE`. Nguoi goi nen keu mot dong khi roi
    vao day: mot tin khong biet ai quet lan thuoc brand nao la mot chuyen khac,
    va im lang o day thi bai cua blog roi vao topic cua Miles ma khong ai hay."""
    # canonical_slug: sidecar cu ghi `vai_quet: "scout"` (LOW-14) — khong bac cau thi
    # duong chinh xac nhat cua tin blog tu roi xuong luoi brand ma khong ai hay.
    q = WRITE_BY_SCAN.get(canonical_slug(vai_quet or "").lower())
    if q:
        return q
    b = str(brand or "").lower()
    return WRITE_BY_BRAND.get(b, DEFAULT_WRITE)


_TEN_THUONG = {v.ten.lower(): v.slug for v in ROLE.values()}


def display_name(slug: str) -> str:
    """Ten persona de in ra bao cao; tra lai chinh slug neu chua khai.

    Giai qua `canonical_slug` truoc: sau LOW-14 con 337 sidecar tren dia ghi slug
    role cu ("carousel", "designer"...). Tra thang VAI.get thi Ong Chu doc duoc
    dong "chuyen tu carousel" thay vi "chuyen tu Dre" — dung cai kieu lan lon
    role/name ma LOW-14 sinh ra de dep."""
    v = ROLE.get(slug) or ROLE.get(canonical_slug(slug))
    return v.ten if v else slug


def rules_module(vai_anh: str):
    """Module `image_rules_<vai>` cua vai lam anh nay (LOW-182, 16/09/2026).

    Moi vai lam anh (Ethan/Dre/Kite) co MOT module tieu chi rieng, hoan toan
    doc lap — khong con `image_rules.py` dung chung. `vai_anh` khong khop vai
    nao co `rules` (rong hoac slug la) thi nem ValueError ngay, khong fail-open
    ve mot module mac dinh: dung sai module la ap nham tieu chi cua vai khac.
    """
    v = ROLE.get(vai_anh) or ROLE.get(canonical_slug(vai_anh))
    if not v or not v.rules:
        raise ValueError(f"vai '{vai_anh}' khong co module tieu chi anh rieng (role.rules)")
    import importlib
    return importlib.import_module(v.rules)


_ACTIVE_VAI = None    # xem set_active_role/active_rules ngay duoi


def set_active_role(vai_anh: str) -> None:
    """Ghi vai lam anh dang chay TRONG TIEN TRINH NAY (LOW-182, 16/09/2026).

    Bien tien trinh (khong phai contextvar/khoa luong), va day la lua chon co
    y: kien truc hien tai la MOI TIEN TRINH PYTHON XU LY DUNG MOT DRAFT/VAI roi
    thoat — moi `*_prepare.py`/`*_submit.py` nhan MOT `draft_id` qua CLI
    (`sys.exit(main())`), khong co duong nao mot tien trinh xu ly hai vai xen
    ke de doi gia tri nay giua chung. `ThreadPoolExecutor` trong
    `prepare.vision._seen_image` chi chay song song NHIEU ANH cua CUNG MOT
    draft — tuc CUNG MOT vai — nen doc tu luong khac trong luc do van an toan:
    gia tri khong doi trong suot vong doi tien trinh sau lan goi dau.

    Goi cang SOM cang tot trong tien trinh (truoc khi bat cu anh nao duoc tai/
    nhin): `image_prepare.prepare_article` goi ngay khi doc duoc `image_role` tu
    sidecar, TRUOC ca `load_source`; cac CLI don le khong di qua do
    (`crop_ratio.py`, `capture_chart.py`, `arxiv_figures.py` khi chay tay) tu
    goi voi vai duoc truyen qua `--vai`.
    """
    global _ACTIVE_VAI
    rules_module(vai_anh)          # nem som neu vai khong hop le, dung de sai lang le
    _ACTIVE_VAI = canonical_slug(vai_anh)


def active_rules():
    """Module tieu chi anh cua vai dang chay trong tien trinh nay.

    Nem RuntimeError neu chua goi `set_active_role` — KHONG fail-open ve mot vai
    mac dinh nao: ap nham tieu chi cua vai khac la dung sai luat ma khong ai
    biet, dung mot loi ro con hon mot ket qua sai lang le.
    """
    if not _ACTIVE_VAI:
        raise RuntimeError(
            "role.active_rules(): chua goi set_active_role() trong tien trinh nay — "
            "khong biet dang chay cho vai nao nen khong the chon module tieu chi anh")
    return rules_module(_ACTIVE_VAI)


def canonical_slug(chu: str) -> str:
    """Chu bat ky (ten cu trong sidecar, ten persona) -> slug profile hien tai.

    Khong nhan ra thi TRA LAI NGUYEN VAN — nguoi goi (standard_assignee) con kiem
    profile co that khong roi bao loi tu te, dung nuot o day."""
    c = str(chu).lower()
    # Ten persona hien tai (Cape, Nova...) cung la mot cach goi hop le — N-r2-10:
    # "cape" khong co trong go/slug_cu nen tung tra nguyen "cape", standard_assignee
    # bao "khong co profile cape" trong khi moi persona khac deu tu resolve.
    return _SLUG_CU.get(c) or _TEN_THUONG.get(c, chu)


# ---- NGAN SACH THOI GIAN mot lan chay (LOW-25, 12/09/2026) ----------------------
# Truoc do moi task tao voi "25m" cung mot gia tri (hermes_adapter.create_task mac
# dinh, khong call site nao override). Do tren kanban.db may chu 14 ngay
# (run completed, phut): dre median 3.0 / p95 22.9, kite p95 17.8 / max 22.9,
# ethan p95 2.3 (blog) 7.6 (dcgr); vai viet/quet p95 <= 8.6. Vai anh mo
# Chromium + vision tung anh nen 25m la sat tran; vai viet thi 25m thua.
# Canh bao "chay lau" o approve_dispatch (THRESHOLD_STALLED_MINUTES=20) phai NHO HON ca
# hai con so nay — test_ngan_sach_thoi_gian giu bat bien do.
MAX_RUNTIME = "25m"
MAX_RUNTIME_IMAGE = "40m"


def max_runtime_for(slug: str) -> str:
    """`--max-runtime` cho task cua vai nay: vai DUNG ANH 40m, con lai 25m."""
    v = ROLE.get(canonical_slug(slug) or slug)
    return MAX_RUNTIME_IMAGE if v and v.nhan_anh else MAX_RUNTIME


def min_images(slug: str, flagship: bool = False) -> int:
    """So ANH THAT toi thieu de vai `slug` dung duoc san pham cua no.

    Vi sao la ham o day chu khong phai hang so trong carousel.py: engine anh
    (`image_prepare.prepare_article`) chay CHUNG cho ca ba vai dung anh va truoc
    10/09/2026 no lay thang `carousel.MIN_SLIDE`/`FLAGSHIP_MIN` — tuc ap luat
    cua Dre cho Ethan lan Kite. Hau qua: bai giao Ethan chi co 2 anh (rat
    thuong gap voi tin khong phai benchmark) bi ket o buoc "thieu anh", roi
    Telegram noi voi Ethan bang tieng cua carousel ("chuyen Kite ve vector",
    "can toi thieu 5 slide") du card.py chi can 1 anh.

    Vai la khong biet -> nguong cua vai anh mac dinh (Ethan). Nguoi goi nen
    keu mot dong khi roi vao day: sidecar mat `image_role` la mot chuyen khac."""
    v = ROLE.get(slug) or ROLE[DEFAULT_IMAGE]
    if flagship and v.anh_toi_thieu_flagship:
        return v.anh_toi_thieu_flagship
    return v.anh_toi_thieu


# Ten rieng >= 2 tu trong alt/caption ("Jensen Huang"). MOT ban duy nhat: chu
# thich anh cua `prepare.vision.classify` va cong "mat nguoi phai khai ten" duoi
# day phai doc ra CUNG mot cai ten, khong duoc moi noi mot regex.
_TEN_NGUOI = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)+")


def person_names_in_alt(alt: str) -> list:
    """Cac ten nguoi neu trong alt/caption cua mot tam anh."""
    return _TEN_NGUOI.findall(alt or "")


def has_label_cover(dung) -> bool:
    """Nhan "dung duoc o dau" cua mot tam co cho phep lam BIA khong.

    KHONG so bang `"bìa" in dung`: do la phep so PHAN TU trong list, ma nhan
    that su duoc dan co the mang duoi giai thich — "bìa (ảnh hero của chính bài
    gốc)" cua vong chup trang nguon. Su co 13/09/2026: sau khi cho vong chup
    chay TRUOC, engine chup ve 4 anh bao cung tin (deu la bia hop le) roi van
    ket luan "co 6 anh nhung khong tam nao lam anh chinh duoc" va di tim tiep
    tren web — chi vi hai chuoi khong bang nhau tuyet doi. Cung ly do khien
    anh chup khong bao gio xuat hien trong `cover_suggestions`.

    Tu LOW-230 `uses` luu MA slot: so voi `manifest_values.COVER_PREFIX_USES` — dung
    ba ma co nhan bat dau "bìa" ma phep `startswith` cu nhan (KHONG gom
    `cover_ranking`, nhan "HERO / BÌA…" chua bao gio khop)."""
    import manifest_values
    return any(str(d) in manifest_values.COVER_PREFIX_USES for d in (dung or []))


def face_no_clear_ai(a: dict) -> bool:
    """Tam co mat nguoi ma khong biet la ai — thuong hieu khong gan ten nguoi,
    alt/caption khong neu ten. `submit_common.check_subject_named` chan tam nhu the, vai
    khong duoc bia ten cho qua cong, nen no KHONG phai mot duong dung duoc: ca
    `can_be_hero` lan nguoi dem slide (`schema.count_image_use_ok`, LOW-46) hoi
    CHINH ham nay, khong moi noi mot dieu kien."""
    return bool(a.get("faces")) and not ((a.get("brand_match") or {}).get("person")
                                       or person_names_in_alt(a.get("alt") or ""))


def can_be_hero(slug: str, a: dict) -> bool:
    """Tam anh `a` (mot muc trong manifest) co dung MOT MINH lam ANH CHINH cua
    vai `slug` khong — bia cua bo carousel, hay nen hero cua the card.

    Tieu chi CHAT LUONG (net, khong rac, lien quan bai) khong nam o day: chung
    dung chung cho moi vai va da chay o `image_rules` + `prepare.vision.classify`.
    Ham nay chi tra loi phan di theo KHO cua renderer."""
    v = ROLE.get(slug) or ROLE[DEFAULT_IMAGE]
    if a.get("relevant") is False or not a.get("uses"):
        return False
    if a.get("ranking"):
        return True                            # anh chinh BAT BUOC cua tin xep hang
    if not v.ti_le_don_max:
        # Vai xep NHIEU anh: "anh chinh" la tam lam BIA, nhan do classify dan.
        return has_label_cover(a.get("uses"))
    if a.get("kind") == "chart" and not v.chart_don:
        return False
    if float(a.get("ratio") or 0) > v.ti_le_don_max:
        return False
    # Mat nguoi khong ro ai: `submit_common.check_subject_named` chan, ma vai thi khong
    # duoc bia ten cho qua cong — tam do khong phai mot duong dung duoc.
    if face_no_clear_ai(a):
        return False
    return True


def search_target_for(slug: str, flagship: bool = False) -> int:
    """Bao nhieu tam thi NGUNG di tim. 0 = vai lam san pham mot anh, so luong
    khong phai tieu chi cua no — hoi `has_enough_material` thay vi so sanh con so nay."""
    v = ROLE.get(slug) or ROLE[DEFAULT_IMAGE]
    if flagship and v.anh_muc_tieu_tim_flagship:
        return v.anh_muc_tieu_tim_flagship
    return v.anh_muc_tieu_tim


def has_enough_material(slug: str, dung_duoc: list, flagship: bool = False) -> bool:
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
    if not any(can_be_hero(slug, a) for a in dung_duoc):
        return False
    # muc = 0 (vai mot anh): ve nay luon dung, tuc chi con ve thu nhat.
    # Dem SLIDE dung duoc (schema.count_image_use_ok), khong dem TAM: tin TSMC
    # 12/09/2026 co 5 tam nhung mot tam 900x600 chi ghep duoc ma khong co cap
    # -> 4 slide, engine van bao "du 5" va ngung tim (t_a8ffd2f6).
    import schema
    return schema.count_image_use_ok(dung_duoc, slug) >= search_target_for(slug, flagship)


def product_unit_for(slug: str) -> str:
    """Chu de goi mot don vi san pham cua vai: "slide" hay "ảnh".

    Dung cho cau bao gui Ong Chu. Goi the don cua Ethan la "slide" chinh la
    thu lam su co 10/09/2026 doc ra nhu "Ethan khong tao duoc slide"."""
    v = ROLE.get(slug)
    return "slide" if v and v.renderer in ("carousel", "render_edu") else "ảnh"


# ---- CAC VIEW DAN XUAT (bang cu, giu y nguyen ngu nghia) --------------------
# Thu tu chen giu nhu ban viet tay cu de so sanh diff cho de.

def _build_go_map(loc):
    ra = {}
    for v in ROLE.values():
        if loc(v):
            ra[v.slug] = v.slug
            for g in v.go:
                ra[g] = v.slug
    return ra


# Chu go duoc khi chon tin -> slug vai ANH (gom ca chinh slug).
ROLE_IMAGE = _build_go_map(lambda v: v.nhan_anh)

# Ong Chu go TEN NAO CUNG DUOC: ten nguoi VIET cung ra cap anh mac dinh, vi mot
# lua chon sinh ra mot CAP di lien nhau (nguoi dung anh lam cha, nguoi viet lam
# con) — bat nho ai dung anh ai viet la bat nho mot thu khong can nho.
NAME_BRIGHT_CAP = dict(ROLE_IMAGE)
NAME_BRIGHT_CAP.update({k: DEFAULT_IMAGE
                     for v in ROLE.values() if v.viet
                     for k in (v.slug,) + v.go})

ROLE_CAROUSEL = {v.slug for v in ROLE.values() if v.renderer == "carousel"}
ROLE_EDU = {v.slug for v in ROLE.values() if v.renderer == "render_edu"}

NAME_ROLE_IMAGE = {v.slug: v.ten for v in ROLE.values() if v.nhan_anh}
NAME_ROLE_WRITE = {v.slug: v.ten for v in ROLE.values() if v.viet}
DISPLAY_NAME = {v.slug: v.ten for v in ROLE.values()}

# Slug cu (ten nhan vat) -> slug profile hien tai. Sidecar .img.json/.writer.json
# doi truoc con ghi "dre"/"miles"; task tao tu do khong ai nhan va nam 'ready'
# mai (su co 01/09/2026: hai bai dcgr ket 2 ngay).
_SLUG_CU = {cu: v.slug for v in ROLE.values() for cu in v.slug_cu}
SLUG_OLD = dict(_SLUG_CU)
