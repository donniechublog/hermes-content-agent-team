#!/usr/bin/env python3
"""Bảng vai dẫn xuất phải khớp CHÍNH XÁC bảng viết tay cũ (issue A4/F1).

Tri thuc ve vai tung nam rai sau cho trong duyet_giao_viec cong ba map "slug ->
ten" chep tay o noi khac. `vai.py` gom lai mot cho va sinh lai cac bang do.

Tep nay giu hai thu:
  1. HOP DONG KHONG DOI: cac bang duoi day duoc chep NGUYEN VAN tu ban viet tay
     truoc khi gom (git 3a18f79:duyet_giao_viec.py). Bang dan xuat lech mot khoa
     la mot duong hong THAT — `SLUG_CU` sai thi task khong ai nhan va nam
     'ready' mai (su co 01/09/2026), `TEN_SANG_CAP` thieu mot chu thi ca lenh
     chon bi tu choi roi gui nham topic (su co 06/09/2026 voi "kites").
  2. Them mot vai chi ton MOT dong: kiem bang chinh bang dang ky, khong phai
     bang cach doc code.

Chay:  venv/bin/python tests/test_vai.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import vai                                                    # noqa: E402

# ---- chep NGUYEN VAN tu ban viet tay truoc khi gom (3a18f79) ----------------
VAI_ANH_CU = {
    "designer": "designer", "img": "designer", "anh": "designer",
    "ethan": "designer",
    "carousel": "carousel", "cr": "carousel",
    "dre": "carousel",
    "carousel-edu": "carousel-edu", "edu": "carousel-edu",
    "kite": "carousel-edu",
    "kites": "carousel-edu",
}
TEN_SANG_CAP_CU = dict(VAI_ANH_CU)
TEN_SANG_CAP_CU.update({"writer": "designer", "cap": "designer", "miles": "designer"})
# LOW-13 (10/09/2026): them nguoi viet thu hai. Cac dong duoi day KHONG thuoc ban
# chup 3a18f79 — chung la phan MOI duoc them co chu dich, ghi rieng ra de doc
# diff sau nay con phan biet "vai moi" voi "bang dan xuat troi".
TEN_SANG_CAP_CU.update({"jika": "designer"})
VAI_CAROUSEL_CU = {"carousel"}
VAI_EDU_CU = {"carousel-edu"}
TEN_VAI_ANH_CU = {"designer": "Ethan", "carousel": "Dre", "carousel-edu": "Kite"}
TEN_VAI_VIET_CU = {"writer": "Miles", "jika": "Jika"}          # +Jika: LOW-13
SLUG_CU_CU = {"miles": "writer", "dre": "carousel", "ethan": "designer",
              "chad": "designer", "heller": "carousel", "kite": "carousel-edu",
              "finn": "scout", "vera": "market", "jean": "teaser", "ada": "analyst"}
TEN_HIEN_CU = {"designer": "Ethan", "carousel": "Dre", "carousel-edu": "Kite",
               "writer": "Miles", "scout": "Finn", "nova": "Nova", "market": "Vera",
               "teaser": "Cape", "analyst": "Ada", "gin": "Gin", "itachi": "Itachi",
               "bob": "Bob",
               "jika": "Jika",                                        # +Jika: LOW-13
               "qinn": "Qinn"}                                         # +Qinn: vai quet X, 12/09/2026

# ---- LOW-14 (10/09/2026): tam slug role cuoi cung doi sang ten nhan vat ------
# Cac bang `*_CU` tren KHONG duoc sua tay: chung la ban chup 3a18f79, va sua
# tay la mat luon cai cong bat troi ma tep nay sinh ra de giu. Thay vao do khai
# PHEP DOI o DUNG MOT CHO roi ap len ban chup — doc diff sau nay van phan biet
# duoc "doi ten co chu dich" voi "bang dan xuat troi".
DOI_LOW14 = {"designer": "ethan", "carousel": "dre", "carousel-edu": "kite",
             "writer": "miles", "scout": "finn", "market": "vera",
             "teaser": "cape", "analyst": "ada"}


def _ad(chu):
    return DOI_LOW14.get(chu, chu)


def _ap_doi(cu):
    """Ap phep doi len CA khoa lan gia tri. Dung cho cac bang 'chu go -> slug':
    "img"->"designer" thanh "img"->"ethan", con "ethan"->"designer" thanh
    "ethan"->"ethan" (ten nhan vat gio la chinh slug, tu tru voi dong dau)."""
    return {_ad(k): _ad(v) for k, v in cu.items()}


def _ap_doi_slug_cu(cu):
    """SLUG_CU DAO CHIEU chu khong phai doi ten phang: ten nhan vat tu ALIAS
    thanh SLUG, con chu role tu SLUG thanh ALIAS. "miles"->"writer" hom nay doc
    nguoc thanh "writer"->"miles". Alias khong phai ten nhan vat ("chad",
    "heller", "jean") thi o nguyen cho, chi doi gia tri."""
    ra = {}
    for alias, slug in cu.items():
        moi = _ad(slug)
        ra[slug if alias == moi else alias] = moi
    # "teaser" chua bao gio nam trong SLUG_CU (Cape hoi do resolve qua ten
    # persona o `_TEN_THUONG`, xem N-r2-10). Doi xong thi no la slug CU that —
    # 11 topic/task tren dia con ghi chu do — nen phai khai them.
    ra["teaser"] = "cape"
    return ra


def _khop(ten, moi, cu):
    thieu = {k: v for k, v in cu.items() if k not in moi}
    thua = {k: v for k, v in moi.items() if k not in cu}
    lech = {k: (cu[k], moi[k]) for k in cu if k in moi and cu[k] != moi[k]}
    assert not (thieu or thua or lech), \
        f"{ten} lech ban viet tay:\n  thieu={thieu}\n  thua={thua}\n  lech={lech}"


def test_VAI_ANH_khop_ban_cu():
    _khop("VAI_ANH", vai.VAI_ANH, _ap_doi(VAI_ANH_CU))


def test_TEN_SANG_CAP_khop_ban_cu():
    """Thieu mot chu o day la ca lenh chon bi tu choi (su co "kites" 06/09)."""
    _khop("TEN_SANG_CAP", vai.TEN_SANG_CAP, _ap_doi(TEN_SANG_CAP_CU))


def test_SLUG_CU_khop_ban_cu():
    """Sai o day la task khong ai nhan, nam 'ready' mai (su co 01/09)."""
    _khop("SLUG_CU", vai.SLUG_CU, _ap_doi_slug_cu(SLUG_CU_CU))


def test_TEN_VAI_ANH_va_VIET_khop_ban_cu():
    _khop("TEN_VAI_ANH", vai.TEN_VAI_ANH, _ap_doi(TEN_VAI_ANH_CU))
    _khop("TEN_VAI_VIET", vai.TEN_VAI_VIET, _ap_doi(TEN_VAI_VIET_CU))


def test_TEN_HIEN_khop_ban_cu():
    _khop("TEN_HIEN", vai.TEN_HIEN, _ap_doi(TEN_HIEN_CU))


def test_VAI_CAROUSEL_va_EDU_khop_ban_cu():
    assert vai.VAI_CAROUSEL == {_ad(s) for s in VAI_CAROUSEL_CU}, vai.VAI_CAROUSEL
    assert vai.VAI_EDU == {_ad(s) for s in VAI_EDU_CU}, vai.VAI_EDU


def test_mac_dinh_khong_doi():
    assert vai.MAC_DINH_ANH == "ethan" and vai.MAC_DINH_VIET == "miles"


def test_khong_slug_nao_con_dat_theo_role():
    """LOW-14 — Ong Chu: *"KHONG BAO GIO DAT TEN THEO ROLE"*. Cong nay chan mot
    vai moi lot vao ban dang ky bang chu role, va chan luon viec ai do revert
    tam dong da doi. `slug` chi duoc khac `ten` o chu hoa."""
    lech = {v.slug: v.ten for v in vai.VAI.values() if v.slug != v.ten.lower()}
    assert not lech, f"slug khong phai ten nhan vat viet thuong: {lech}"
    role = sorted(set(DOI_LOW14) & set(vai.VAI))
    assert not role, f"chu role quay lai lam slug: {role}"


# ---- tinh chat cua ban dang ky ---------------------------------------------
def test_slug_that_nhan_ten_cu_va_giu_nguyen_chu_la():
    assert vai.slug_that("carousel") == "dre", "slug role cu (LOW-14) van phai doc duoc"
    assert vai.slug_that("Jean") == "cape", "phai khong phan biet hoa thuong"
    assert vai.slug_that("dre") == "dre", "slug hien tai giu nguyen"
    assert vai.slug_that("khong-co-that") == "khong-co-that", \
        "chu la phai tra NGUYEN VAN de chuan_assignee con bao loi tu te"


def test_ten_hien_roi_ve_slug_khi_chua_khai():
    assert vai.ten_hien("dre") == "Dre"
    assert vai.ten_hien("chua-khai") == "chua-khai"


def test_moi_vai_anh_deu_co_renderer():
    thieu = [v.slug for v in vai.VAI.values() if v.nhan_anh and not v.renderer]
    assert not thieu, f"vai dung anh ma khong khai renderer: {thieu}"


def test_khong_alias_nao_dam_len_slug_cua_vai_khac():
    """Mot chu vua la slug cua vai A vua la alias cua vai B thi lookup thanh
    may rui theo thu tu chen — chan tu trong ban dang ky."""
    xau = []
    for v in vai.VAI.values():
        for chu in v.go + v.slug_cu:
            if chu in vai.VAI and chu != v.slug:
                xau.append(f"{chu!r} la slug cua {chu} nhung lam alias cho {v.slug}")
    assert not xau, xau


def test_them_vai_chi_ton_mot_dong():
    """F1: them mot dong vao VAI la moi bang dan xuat co ngay, khong phai sua
    tam cho. Kiem bang chinh ban dang ky chu khong doc code."""
    them = vai.Vai("thu_nghiem", "Thu", go=("tn",), renderer="card", nhan_anh=True)
    v2 = dict(vai.VAI, thu_nghiem=them)
    ten_hien = {v.slug: v.ten for v in v2.values()}
    anh = {}
    for v in v2.values():
        if v.nhan_anh:
            anh[v.slug] = v.slug
            for g in v.go:
                anh[g] = v.slug
    assert ten_hien["thu_nghiem"] == "Thu"
    assert anh["tn"] == "thu_nghiem" and anh["thu_nghiem"] == "thu_nghiem"
    assert {v.slug for v in v2.values() if v.renderer == "card"} == {"ethan", "thu_nghiem"}


# ---- tai lieu khong duoc lech ban dang ky (audit C6) ------------------------
def _bang_vai_trong_readme():
    """(ten, slug) tu bang 'Doi hinh' trong README: `| Ten | \\`slug\\` | ... |`."""
    import re
    doc = (ROOT / "README.md").read_text(encoding="utf-8")
    return {m.group(2): m.group(1).strip()
            for m in re.finditer(r"^\|\s*([A-ZĐ][\wÀ-ỹ]*)\s*\|\s*`([a-z-]+)`\s*\|", doc, re.M)}


def test_README_goi_dung_ten_vai_nhu_ban_dang_ky():
    """Su co C6: tai lieu con goi Kite/Cape bang ten persona cu (Jean, Heller...)
    trong khi ma da doi. Ten trong bang README phai khop vai.TEN_HIEN."""
    lech = {slug: (ten, vai.TEN_HIEN.get(slug))
            for slug, ten in _bang_vai_trong_readme().items()
            if vai.TEN_HIEN.get(slug) != ten}
    assert not lech, f"README goi ten khac ban dang ky (slug: README vs vai.py): {lech}"


def test_moi_vai_trong_ban_dang_ky_deu_co_trong_README():
    """Them mot dong vao vai.py ma quen ghi vao bang README thi doi khong biet
    vai do ton tai — F1 hua 'them vai = mot dong registry', cai gia la phai
    dong bo tai lieu ngay canh."""
    thieu = sorted(set(vai.VAI) - set(_bang_vai_trong_readme()))
    assert not thieu, f"co trong vai.py ma khong co trong bang README: {thieu}"


def test_khong_vai_la_nao_trong_README():
    thua = sorted(set(_bang_vai_trong_readme()) - set(vai.VAI))
    assert not thua, f"README ke vai khong co trong vai.py: {thua}"


def test_slug_that_nhan_ten_persona_hien_tai():
    """N-r2-10: "cape" khong co trong go/slug_cu nen tung tra nguyen "cape".
    Sau LOW-14 "cape" la chinh slug, con "teaser" moi la chu phai bac cau."""
    assert vai.slug_that("cape") == "cape"
    assert vai.slug_that("Cape") == "cape"
    assert vai.slug_that("teaser") == "cape", "slug role cu van phai dung"
    assert vai.slug_that("jean") == "cape", "persona cu van phai dung"
    assert vai.slug_that("nova") == "nova"
    assert vai.slug_that("khong-co") == "khong-co", "khong nhan ra thi tra nguyen van"


def test_chat_router_TOPIC_PROFILE_khop_ban_dang_ky():
    """ADF-r2-2: bang topic->profile cua chat_router tung chep tay 12 dong; thieu
    vai moi thi chat trong topic do roi ve profile mac dinh, im lang."""
    import chat_router
    assert set(chat_router.TOPIC_PROFILE) == set(vai.VAI), \
        set(chat_router.TOPIC_PROFILE) ^ set(vai.VAI)


def test_duyet_giao_viec_SLUG_CU_la_chinh_ban_cua_vai():
    """ADF-r2-1: bang chep tay tung ghi de ban dan xuat 21 dong sau."""
    import duyet_giao_viec as dgv
    assert dgv.SLUG_CU is vai.SLUG_CU


def test_handle_kenh_mot_ban_hai_kieu_khoa():
    """ADF-r2-9: bob (co @) va kite (khong @) tung cho hai ket qua khac nhau
    voi cung 'blog'."""
    import env_load
    assert env_load.handle_kenh("blog") == "@donniechublog"
    assert env_load.handle_kenh("donniechublog") == "@donniechublog"
    assert env_load.handle_kenh("blog", co_a_cong=False) == "donniechublog"
    assert env_load.handle_kenh("dcgr", co_a_cong=False).startswith("dcgr")
    assert env_load.handle_kenh("la").startswith("@")


def test_nguong_anh_cua_carousel_khong_troi_khoi_carousel_py():
    """`vai.py` chep 5/8 cua carousel.py de khong phai import carousel (keo theo
    card + PIL vao mot ban dang ky phai nhe). Chep thi phai co cong giu."""
    import carousel
    assert vai.VAI["dre"].anh_toi_thieu == carousel.MIN_SLIDE, \
        f"vai.py ghi {vai.VAI['dre'].anh_toi_thieu}, carousel.MIN_SLIDE={carousel.MIN_SLIDE}"
    assert vai.VAI["dre"].anh_toi_thieu_flagship == carousel.FLAGSHIP_MIN, \
        f"vai.py ghi {vai.VAI['dre'].anh_toi_thieu_flagship}, " \
        f"carousel.FLAGSHIP_MIN={carousel.FLAGSHIP_MIN}"
    # Ca hai vai XEP NHIEU ANH deu di tim toi so slide cua carousel: Dre vi moi
    # slide an mot tam that, Kite vi render_edu cung xep nhieu slide.
    for slug in ("dre", "kite"):
        assert vai.so_anh_muc_tieu_tim(slug) == carousel.MIN_SLIDE
        assert vai.so_anh_muc_tieu_tim(slug, flagship=True) == carousel.FLAGSHIP_MIN


def test_vai_mot_anh_khong_co_so_luong_de_ap():
    """LOW-12 — Ong Chu: *"carousel la nhieu anh con Ethan lam single image, nen
    'so luong' ko the la thu ap vao duoc"*. `anh_muc_tieu_tim` cua Ethan phai la
    0, tuc engine khong duoc dem tam nao ca ma chi hoi da co anh chinh chua."""
    assert vai.so_anh_muc_tieu_tim("ethan") == 0
    assert vai.so_anh_muc_tieu_tim("ethan", flagship=True) == 0, \
        "tin flagship KHONG lam the hero cua Ethan can them anh"
    assert vai.VAI["ethan"].ti_le_don_max == 1.6 and not vai.VAI["ethan"].chart_don


def _a(**doi) -> dict:
    a = {"dung": ["bìa", "thân"], "lien_quan": True, "loai": "anh", "ti_le": 0.8,
         "mat": 0, "alt": ""}
    a.update(doi)
    return a


def test_anh_chinh_duoc_hoi_dung_luat_cua_tung_renderer():
    """Cung mot tam anh, hai vai tra loi khac nhau — va khac dung o cho kho anh
    khac nhau, khong phai o tieu chi chat luong (thu do dung chung, chay o
    luat_anh + phan_loai truoc khi toi day)."""
    # Ti le 1.5: qua NGANG_RO (1.4) nen phan_loai KHONG dan nhan "bìa" -> Dre
    # khong lam bia duoc; nhung card.py cho toi 1.6 nen Ethan dung lam nen hero.
    ngang_vua = _a(ti_le=1.5, ngang=True, dung=["ghép dọc với một ảnh ngang cùng tone"])
    assert vai.anh_chinh_duoc("ethan", ngang_vua)
    assert not vai.anh_chinh_duoc("dre", ngang_vua)
    # 16:9 thi ca hai deu chiu.
    ngang_han = _a(ti_le=1.78, ngang=True, dung=["ghép dọc với một ảnh ngang cùng tone"])
    assert not vai.anh_chinh_duoc("ethan", ngang_han)
    assert not vai.anh_chinh_duoc("dre", ngang_han)
    # Chart: card.py chan di mot minh.
    assert not vai.anh_chinh_duoc("ethan", _a(loai="chart", ti_le=1.2))
    # ...tru bang xep hang, la anh chinh BAT BUOC cua tin do.
    assert vai.anh_chinh_duoc("ethan", _a(loai="chart", ti_le=1.2, xep_hang={"site": "arena"}))
    # Mat nguoi khong ro ai: khai `nhan_vat` la bia, nen khong phai mot duong dung.
    assert not vai.anh_chinh_duoc("ethan", _a(mat=1))
    assert vai.anh_chinh_duoc("ethan", _a(mat=1, alt="Jensen Huang on stage"))
    assert vai.anh_chinh_duoc("ethan", _a(mat=1, thuong_hieu={"nguoi": "Jensen Huang"}))
    # Vision danh rot thi khong vai nao dung.
    assert not vai.anh_chinh_duoc("ethan", _a(lien_quan=False))


def test_du_nguyen_lieu_chi_dem_tam_voi_vai_nhieu_anh():
    mot_hero = [_a()]
    assert vai.du_nguyen_lieu("ethan", mot_hero), \
        "Ethan co mot tam lam hero duoc la du — the cua anh ta chi dung MOT anh"
    assert not vai.du_nguyen_lieu("dre", mot_hero), \
        "Dre co bia nhung moi mot tam: van thieu 4 slide"
    nam_ngang = [_a(ti_le=1.78, ngang=True, dung=["ghép dọc với một ảnh ngang cùng tone"])
                 for _ in range(5)]
    assert not vai.du_nguyen_lieu("ethan", nam_ngang), \
        "5 anh ngang 16:9 khong cho Ethan mot duong nao — dung su co LOW-12"
    assert not vai.du_nguyen_lieu("dre", nam_ngang), "du 5 tam nhung khong co bia"
    assert not vai.du_nguyen_lieu("dre", [_a() for _ in range(5)]), "tin thuong can 6 slide (12/09/2026)"
    assert vai.du_nguyen_lieu("dre", [_a() for _ in range(6)])
    assert not vai.du_nguyen_lieu("dre", [_a() for _ in range(6)], flagship=True), \
        "tin flagship can 7 slide"
    # Vai la -> luat cua vai anh mac dinh, khong nem.
    assert vai.du_nguyen_lieu("khong-co-vai-nay", mot_hero) == vai.du_nguyen_lieu(
        vai.MAC_DINH_ANH, mot_hero)


def test_so_anh_toi_thieu_theo_tung_vai():
    """Su co 10/09/2026: engine ap nguong carousel cho MOI vai dung anh, nen bai
    2 anh cua Ethan bi bao thieu anh va Ong Chu doc thay "carousel can toi thieu
    5 slide" tren task cua Ethan. Ethan can DUNG MOT anh (card.py), Kite ve
    vector nen cung mot anh la du; chi Dre moi can 6, va 7 khi tin flagship (12/09/2026)."""
    assert vai.so_anh_toi_thieu("ethan") == 1
    assert vai.so_anh_toi_thieu("ethan", flagship=True) == 1, \
        "tin flagship KHONG lam the hero cua Ethan can them anh"
    assert vai.so_anh_toi_thieu("kite") == 1
    assert vai.so_anh_toi_thieu("dre") == 6, "Ong Chu 12/09/2026: tin thuong 6"
    assert vai.so_anh_toi_thieu("dre", flagship=True) == 7, "Ong Chu 12/09/2026: flagship 7"
    # Vai la (sidecar hong, chay tay) -> nguong cua vai anh mac dinh, khong nem.
    assert vai.so_anh_toi_thieu("") == vai.so_anh_toi_thieu(vai.MAC_DINH_ANH)
    assert vai.so_anh_toi_thieu("khong-co-vai-nay") == vai.so_anh_toi_thieu(vai.MAC_DINH_ANH)


def test_don_vi_san_goi_dung_ten_san_pham():
    """Goi the don cua Ethan la "slide" chinh la thu doc ra thanh "Ethan khong
    tao duoc slide" (su co 10/09/2026)."""
    assert vai.don_vi_san("ethan") == "ảnh"
    assert vai.don_vi_san("dre") == "slide"
    assert vai.don_vi_san("kite") == "slide"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())


# ---- ai viet tin nay (LOW-13, 10/09/2026) ----------------------------------
# Truoc do chi co MOT nguoi viet nen khong co gi de kiem. Gio sai o day la bai
# cua blog roi vao topic cua Miles (hoac nguoc lai) ma KHONG ai bao loi: ca hai
# slug deu la profile co that, task van tao duoc, chi la giao nham nguoi.

def test_vai_viet_di_theo_vai_quet():
    """Dieu Ong Chu chot: nguoi viet di theo vai QUET, khong theo vai anh."""
    assert vai.vai_viet_cua("finn") == "jika", "Finn -> Jika"
    assert vai.vai_viet_cua("nova") == "jika", "Nova -> Jika"
    assert vai.vai_viet_cua("vera") == "miles", "Vera -> Miles"


def test_vai_viet_theo_brand_khi_khong_biet_vai_quet():
    """Duong `approve_service push` chi co draft_id + category, khong cam vai
    quet — no phai ra dung nguoi viet bang brand."""
    for b in ("blog", "donniechublog"):
        assert vai.vai_viet_cua(None, b) == "jika", b
    for b in ("dcgr", "dcgr.tech"):
        assert vai.vai_viet_cua(None, b) == "miles", b


def test_vai_quet_thang_brand_khi_hai_ben_khac_nhau():
    """Vai quet chinh xac hon brand: no noi ve LINH VUC that cua tin."""
    assert vai.vai_viet_cua("vera", "blog") == "miles"
    assert vai.vai_viet_cua("nova", "dcgr") == "jika"


def test_vai_viet_khong_biet_gi_thi_ve_mac_dinh():
    assert vai.vai_viet_cua() == vai.MAC_DINH_VIET
    assert vai.vai_viet_cua("khong-co", "khong-co") == vai.MAC_DINH_VIET


def test_moi_nguoi_viet_duoc_tro_toi_deu_co_that_va_la_vai_viet():
    """Go nham slug trong hai bang dinh tuyen = task giao cho profile khong ton
    tai (su co 01/09/2026 nam 'ready' hai ngay)."""
    xau = []
    for ten, bang in (("VIET_THEO_QUET", vai.VIET_THEO_QUET),
                      ("VIET_THEO_BRAND", vai.VIET_THEO_BRAND)):
        for khoa, slug in bang.items():
            v = vai.VAI.get(slug)
            if v is None or not v.viet:
                xau.append(f"{ten}[{khoa!r}] -> {slug!r} khong phai vai viet")
    assert not xau, xau


def test_moi_vai_quet_that_deu_co_nguoi_viet():
    """Vai quet nao co manifest chay that thi phai co ten trong VIET_THEO_QUET,
    khong duoc roi ve mac dinh im lang."""
    import duyet_chon_tin
    thieu = sorted(set(duyet_chon_tin.MANIFEST_THEO_TOPIC) - set(vai.VIET_THEO_QUET))
    assert not thieu, f"vai quet khong biet giao cho ai viet: {thieu}"


def test_hai_bang_dinh_tuyen_khong_mau_thuan_voi_the_trien_khai_hom_nay():
    """Hom nay moi vai quet nam GON trong mot brand, nen hai duong phai cho cung
    ket qua. Lech = mot ben da doi ma ben kia quen (vd chuyen Nova sang dcgr)."""
    brand_cua_quet = {"finn": "blog", "nova": "blog", "vera": "dcgr"}
    for quet, brand in brand_cua_quet.items():
        assert vai.vai_viet_cua(quet) == vai.vai_viet_cua(None, brand),             f"{quet} ({brand}): bang theo quet va bang theo brand lech nhau"


def test_ten_brand_khop_chinh_ta_cua_env_load():
    """VIET_THEO_BRAND chep chinh ta brand thay vi import env_load (giu ban dang
    ky nhe). Chep thi phai co cong giu hai ban khong troi khoi nhau."""
    import env_load
    for ngan, dai in env_load.BRAND_DAI.items():
        assert ngan in vai.VIET_THEO_BRAND, f"thieu khoa container {ngan!r}"
        assert dai in vai.VIET_THEO_BRAND, f"thieu slug dai {dai!r}"
        assert vai.VIET_THEO_BRAND[ngan] == vai.VIET_THEO_BRAND[dai],             f"{ngan!r} va {dai!r} la MOT brand ma tro toi hai nguoi viet"
