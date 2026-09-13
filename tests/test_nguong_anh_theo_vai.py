#!/usr/bin/env python3
"""Nguong "du anh" phai di theo ROLE, khong phai theo carousel (su co 10/09/2026).

Ong Chu bao: "viec cua Ethan la lam single image, sao hom nay Ethan lai bao
khong tao duoc slide?". Ethan KHONG bi giao nham task — phan cong van dung.
Sai o cho khac: `image_prepare.prepare_article()` chay CHUNG cho ca ba vai dung anh
nhung tinh so anh toi thieu bang `carousel.FLAGSHIP_MIN if flagship else
carousel.MIN_SLIDE`, tuc luon la 5 (hay 8) — ke ca khi bai la cua Ethan, ma
card.py chi can DUNG MOT tam anh. Hai bai co 2 anh that hom do bi ket o buoc
"thieu anh", roi Telegram noi voi Ethan bang tieng cua carousel:

    ⚠️ Chỉ 2 ảnh thật mà carousel cần tối thiểu 5 slide — bấm tiếp cũng không
    dựng được. Chuyển Kite vẽ vector, hoặc bỏ tin.
    (state/blog/approve.log 09-10 00:42, draft ...-designer-donniechubl)

Bon test duoi giu dung bon mat cua duong hong do: nguong trong manifest, quyet
dinh "co thieu anh khong", tang ghep noi co hoi Ong Chu khong, va cau chu cua
nut ha san.

Chay:  venv/bin/python tests/test_nguong_anh_theo_vai.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import role                                                    # noqa: E402
from prepare.manifest import build_manifest                   # noqa: E402


def _anh(ma: str, dung=("nền hero (một mình)",), lien_quan=True) -> dict:
    """Mot muc `anh` du khoa cho dung_manifest. ti_le < 1.3 co chu dich: `cap_ghep`
    chi MO TEP anh voi anh ngang, ma o day khong co tep that nao."""
    return {"ma": ma, "goc": f"/khong-co/{ma}.jpg", "ti_le": 1.0, "w": 1200, "h": 1200,
            "loai": "anh", "dung": list(dung), "lien_quan": lien_quan, "mat": 0,
            "goc_trai_sang": 60, "canh_ngan": 1200, "mien": "vi_du.com", "tu": "bai"}


def _manifest(vai_anh: str, so_anh: int, flagship=False) -> dict:
    """Manifest that (qua dung_manifest, khong che tay) cho `so_anh` anh dung duoc."""
    with tempfile.TemporaryDirectory() as tmp:
        return build_manifest(
            "d1", {"brand": "donniechublog", "title": "t"}, "t", "http://vi.du/a",
            {"tieu_de_en": ""}, Path(tmp) / "source.json", {}, Path(tmp),
            [_anh(f"A{i + 1}") for i in range(so_anh)], [], False,
            {"chu": ""}, {}, flagship,
            role.min_images(vai_anh, flagship), vai_anh=vai_anh)


# ------------------------------------------------ 1. nguong ghi vao manifest
def test_manifest_ghi_nguong_theo_vai_duoc_giao():
    """`toi_thieu` va `toi_thieu_co_ban` la cua ROLE DUOC GIAO. Truoc 10/09/2026
    `toi_thieu_co_ban` go cung `carousel.MIN_SLIDE` cho moi vai, nen nut "ha san"
    cua mot bai Ethan cung lay san 5."""
    m_ethan = _manifest("ethan", 2)
    assert m_ethan["toi_thieu"] == 1, m_ethan["toi_thieu"]
    assert m_ethan["toi_thieu_co_ban"] == 1, m_ethan["toi_thieu_co_ban"]
    assert m_ethan["vai_anh"] == "ethan"

    m_dre = _manifest("dre", 2)
    import carousel
    assert m_dre["toi_thieu"] == carousel.MIN_SLIDE, "Dre KHONG duoc doi hanh vi: moi slide mot anh"
    assert m_dre["toi_thieu_co_ban"] == carousel.MIN_SLIDE
    assert _manifest("dre", 2, flagship=True)["toi_thieu"] == carousel.FLAGSHIP_MIN, \
        "tin flagship lay nguong flagship cho Dre"


def test_tin_flagship_khong_lam_the_cua_ethan_can_them_anh():
    """`flagship` la luat cua carousel (bo phai day hon cho tin lon). The hero
    cua Ethan van la MOT tam anh du tin co lon co nao."""
    assert _manifest("ethan", 2, flagship=True)["toi_thieu"] == 1


# --------------------------------------- 2. quyet dinh "bai nay co thieu anh"
def test_hai_anh_that_la_DU_cho_ethan_va_THIEU_cho_dre():
    """Dung canh sinh ra su co: 2 anh that dung duoc.

    Voi Ethan phai la None (khong co gi de hoi) — truoc sua, ham nay tra
    {"so": 2, "toi_thieu": 5} va do la thu keo ca day "thieu anh" chay."""
    import image_prepare as cb
    assert cb._description_missing_image(_manifest("ethan", 2)) is None, \
        "2 anh that ma bao Ethan thieu anh — dung loi 10/09/2026"
    import carousel
    assert cb._description_missing_image(_manifest("dre", 2)) == {"so": 2, "toi_thieu": carousel.MIN_SLIDE}
    # Va khong anh nao thi Ethan cung thieu that (0 < 1) — cong van con.
    assert cb._description_missing_image(_manifest("ethan", 0)) == {"so": 0, "toi_thieu": 1}


# ------------------------------------------- 3. tang ghep noi khong hoi oan
def test_khong_hoi_ong_chu_khi_ethan_du_anh():
    """`sau_chuan_bi` chi hoi khi manifest co `thieu_anh`. Bai cua Ethan voi 2
    anh khong con khoa do -> khong mot tin nao gui len topic, khong nut "Gui
    Kite ve vector" nao moc vao task le ra chay tron."""
    import route_missing_images as rt
    goi = []
    cu_gui, cu_drafts = rt._time_send, rt.DRAFTS
    rt._time_send = lambda *a, **k: goi.append(a) or True
    try:
        with tempfile.TemporaryDirectory() as tmp:
            rt.DRAFTS = Path(tmp)
            (rt.DRAFTS / "d1.img.json").write_text(
                json.dumps({"vai_anh": "ethan"}), encoding="utf-8")
            m = _manifest("ethan", 2)
            import image_prepare as cb
            thieu = cb._description_missing_image(m)
            if thieu:
                m["thieu_anh"] = thieu
            rt.after_prepare("d1", m)
    finally:
        rt._time_send, rt.DRAFTS = cu_gui, cu_drafts
    assert not goi, f"da hoi Ong Chu du Ethan khong thieu anh: {goi}"
    assert "hoi_kite" not in m and "chuyen_kite" not in m


# ------------------------------------------------------ 4. cau chu cua nut
def _ha_san(tmp: Path, manifest: dict, sidecar: dict | None):
    """Chay approve_post._button_lower_ready voi moi truong gia, tra `note`."""
    import approve_post as db
    import approve_dispatch as dgv
    d = tmp / "state" / "chuan_bi" / "d1"
    d.mkdir(parents=True, exist_ok=True)
    (d / "xong.json").write_text(json.dumps(manifest), encoding="utf-8")
    drafts = tmp / "drafts"
    drafts.mkdir(exist_ok=True)
    if sidecar is not None:
        (drafts / "d1.img.json").write_text(json.dumps(sidecar), encoding="utf-8")
    (tmp / "home" / "profiles" / "kite").mkdir(parents=True, exist_ok=True)
    cu = (db.STATE_DIR, db.DRAFTS, dgv.HERMES_HOME, db.call)
    db.STATE_DIR, db.DRAFTS = tmp / "state", drafts
    dgv.HERMES_HOME = str(tmp / "home")
    db.call = lambda *a, **k: {"ok": True}
    try:
        note, _kb = db._button_lower_ready("tok", "d1", {"id": "cbq1"})
        return note
    finally:
        db.STATE_DIR, db.DRAFTS, dgv.HERMES_HOME, db.call = cu


def test_nut_ha_san_khong_goi_the_cua_ethan_la_slide():
    """Dong chu Ong Chu doc duoc hom 10/09: "carousel cần tối thiểu 5 slide" —
    tren mot task le ra chi la mot tam anh."""
    with tempfile.TemporaryDirectory() as tmp:
        note = _ha_san(Path(tmp), {"so_dung_duoc": 0, "toi_thieu": 1,
                                   "toi_thieu_co_ban": 1, "vai_anh": "ethan"}, None)
    assert "slide" not in note.lower(), f"van goi san pham cua Ethan la slide: {note}"
    assert "ảnh" in note


def test_nut_ha_san_van_noi_slide_cho_dre_va_cho_manifest_cu():
    """Dre khong doi gi; manifest cu (khong co `vai_anh`) giu nguyen chu cu."""
    with tempfile.TemporaryDirectory() as tmp:
        note = _ha_san(Path(tmp), {"so_dung_duoc": 4, "toi_thieu": 8,
                                   "toi_thieu_co_ban": 5, "vai_anh": "dre"}, None)
        assert "slide" in note, note
        cu = _ha_san(Path(tmp), {"so_dung_duoc": 4, "toi_thieu": 8,
                                 "toi_thieu_co_ban": 5}, None)
        assert "slide" in cu, cu


def test_nut_ha_san_theo_sidecar_khi_bai_da_chuyen_kite():
    """`tao_task_kite` doi `vai_anh` trong SIDECAR chu khong sua manifest, nen
    sidecar la ban moi nhat — bai da sang Kite thi lai goi la slide."""
    with tempfile.TemporaryDirectory() as tmp:
        note = _ha_san(Path(tmp), {"so_dung_duoc": 0, "toi_thieu": 1,
                                   "toi_thieu_co_ban": 1, "vai_anh": "ethan"},
                       {"vai_anh": "kite", "chuyen_tu": "ethan"})
    assert "slide" in note, note


# ------------------------------------------- 5. cong chan dung DONG da hong
def test_engine_lay_nguong_CHAN_tu_ban_dang_ky_vai():
    """Cong chan o muc MA NGUON, vi dong that su hong nam trong `prepare_article()` —
    ham do mo Chromium, tai anh, goi vision, khong unit test duoc.

    Dong cu:  toi_thieu = carousel.FLAGSHIP_MIN if flagship else carousel.MIN_SLIDE
    Dong nay: toi_thieu = role.min_images(vai_anh, flagship)

    Ai do viet lai theo kieu cu thi cac test tren VAN XANH (chung dung thang
    `role.min_images` de dung manifest) — chi cong nay bat duoc.

    Nguong CHAN va cau hoi "con phai di tim nua khong" la HAI thu: cai thu hai
    nay do `role.has_enough_material`, giu o `tests/test_tim_anh_theo_vai.py`."""
    import inspect
    import re

    import image_prepare as cb
    src = inspect.getsource(cb.prepare_article)
    assert re.search(r"^\s*toi_thieu = role\.min_images\(", src, re.M), \
        ("`toi_thieu` (nguong chan, di vao manifest) khong con lay tu ban dang ky "
         "vai — do la su co 10/09/2026")


def test_nguong_chan_khong_bi_dung_lam_muc_tieu_di_tim():
    """Nguoc lai voi test tren: lay nguong CHAN (Ethan 1) lam so de NGUNG DI TIM
    cung hong, chi la hong kieu khac — engine se dung ngay khi co mot tam bat ky
    dung duoc, ke ca tam Ethan khong lam hero duoc.

    Ban cu chong cai do bang `muc_tieu_tim = max(toi_thieu, MIN_SLIDE)`, tuc lay
    so cua carousel — chinh la thu Ong Chu bac 10/09/2026 ("carousel la nhieu anh
    con Ethan lam single image, nen 'so luong' ko the la thu ap vao duoc"). Nay
    hai duong tach han: `toi_thieu` chi de CHAN, con di tim thi hoi
    `role.has_enough_material` — no doi phai co anh CHINH, khong doi du so tam."""
    import inspect

    import image_prepare as cb
    import role as vai_mod
    src = inspect.getsource(cb.prepare_article)
    for dong in src.splitlines():
        d = dong.strip()
        if d.startswith("#") or "_round_widen_search(" not in d or "=" not in d:
            continue
        assert "toi_thieu" not in d.split("_round_widen_search(")[0], \
            f"vong tim anh dang do bang nguong chan: {d}"
    # Mot tam DUNG DUOC nhung khong lam hero duoc thi chua phai la du.
    a = {"dung": ["ghép dọc với một ảnh ngang cùng tone"], "lien_quan": True,
         "loai": "anh", "ti_le": 1.78, "mat": 0, "alt": ""}
    assert not vai_mod.has_enough_material("ethan", [a]), \
        "engine se ngung tim khi Ethan van chua co tam nao lam nen hero"


def test_sidecar_ghi_truoc_khi_engine_chay():
    """Engine doc `vai_anh` tu sidecar .img.json ngay dau. `create_pair` tung
    goi `_khoi_chay_engine` TRUOC `_cat_sidecar`, tuc engine doc mot tep chua ai
    ghi — truoc gio chi mat tom tat (im lang), tu 10/09/2026 mat ca nguong."""
    import inspect

    import approve_pick as dct
    src = inspect.getsource(dct.create_pair)
    assert src.index("_crop_sidecar(") < src.index("_block_run_engine("), \
        "create_pair chay engine truoc khi ghi sidecar — engine se khong biet vai"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
