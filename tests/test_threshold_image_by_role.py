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

Chay:  venv/bin/python tests/test_threshold_image_by_role.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import role                                                    # noqa: E402
from prepare.manifest import build_manifest                   # noqa: E402
import schema                                                 # noqa: E402
import state_paths                                            # noqa: E402


def _image(ma: str, dung=("nền hero (một mình)",), lien_quan=True) -> dict:
    """Mot muc `images` du khoa cho build_manifest. ratio < 1.3 co chu dich: `stackable_pairs`
    chi MO TEP anh voi anh ngang, ma o day khong co tep that nao."""
    return {"id": ma, "original_path": f"/khong-co/{ma}.jpg", "ratio": 1.0, "w": 1200, "h": 1200,
            "kind": "photo", "uses": list(dung), "relevant": lien_quan, "faces": 0,
            "bottom_left_brightness": 60, "short_side": 1200, "domain": "vi_du.com", "source": "bai"}


def _manifest(vai_anh: str, so_anh: int, flagship=False) -> dict:
    """Manifest that (qua build_manifest, khong che tay) cho `so_anh` anh dung duoc."""
    with tempfile.TemporaryDirectory() as tmp:
        return build_manifest(
            "d1", {"brand": "donniechublog", "title": "t"}, "t", "http://vi.du/a",
            {"tieu_de_en": ""}, Path(tmp) / "source.json", {}, Path(tmp),
            [_image(f"A{i + 1}") for i in range(so_anh)], [], False,
            {"chu": ""}, {}, flagship,
            role.min_images(vai_anh, flagship), vai_anh=vai_anh)


# ------------------------------------------------ 1. nguong ghi vao manifest
def test_manifest_write_threshold_by_role_ok_hand():
    """`min_images` va `base_min_images` la cua ROLE DUOC GIAO. Truoc 10/09/2026
    `base_min_images` go cung `carousel.MIN_SLIDE` cho moi vai, nen nut "ha san"
    cua mot bai Ethan cung lay san 5."""
    m_ethan = _manifest("ethan", 2)
    assert m_ethan["min_images"] == 1, m_ethan["min_images"]
    assert m_ethan["base_min_images"] == 1, m_ethan["base_min_images"]
    assert m_ethan["image_role"] == "ethan"

    m_dre = _manifest("dre", 2)
    import carousel
    assert m_dre["min_images"] == carousel.MIN_SLIDE, "Dre KHONG duoc doi hanh vi: moi slide mot anh"
    assert m_dre["base_min_images"] == carousel.MIN_SLIDE
    assert _manifest("dre", 2, flagship=True)["min_images"] == carousel.FLAGSHIP_MIN, \
        "tin flagship lay nguong flagship cho Dre"


def test_story_flagship_no_make_card_of_ethan_can_extra_image():
    """`flagship` la luat cua carousel (bo phai day hon cho tin lon). The hero
    cua Ethan van la MOT tam anh du tin co lon co nao."""
    assert _manifest("ethan", 2, flagship=True)["min_images"] == 1


# --------------------------------------- 2. quyet dinh "bai nay co thieu anh"
def test_two_image_real_is_enough_wait_ethan_and_missing_wait_dre():
    """Dung canh sinh ra su co: 2 anh that dung duoc.

    Voi Ethan phai la None (khong co gi de hoi) — truoc sua, ham nay tra
    {"count": 2, "min_images": 5} va do la thu keo ca day "thieu anh" chay."""
    import image_prepare as cb
    assert cb._description_missing_image(_manifest("ethan", 2)) is None, \
        "2 anh that ma bao Ethan thieu anh — dung loi 10/09/2026"
    import carousel
    assert cb._description_missing_image(_manifest("dre", 2)) == {"count": 2, "min_images": carousel.MIN_SLIDE}
    # Va khong anh nao thi Ethan cung thieu that (0 < 1) — cong van con.
    assert cb._description_missing_image(_manifest("ethan", 0)) == {"count": 0, "min_images": 1}


# ------------------------------------------- 3. tang ghep noi khong hoi oan
def test_no_ask_boss_when_ethan_enough_image():
    """`sau_chuan_bi` chi hoi khi manifest co `missing_images`. Bai cua Ethan voi 2
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
                json.dumps({"image_role": "ethan"}), encoding="utf-8")
            m = _manifest("ethan", 2)
            import image_prepare as cb
            thieu = cb._description_missing_image(m)
            if thieu:
                m["missing_images"] = thieu
            rt.after_prepare("d1", m)
    finally:
        rt._time_send, rt.DRAFTS = cu_gui, cu_drafts
    assert not goi, f"da hoi Ong Chu du Ethan khong thieu anh: {goi}"
    assert "kite_asked" not in m and "kite_task_id" not in m


# ------------------------------------------------------ 4. cau chu cua nut
def _lower_ready(tmp: Path, manifest: dict, sidecar: dict | None):
    """Chay approve_post._button_lower_ready voi moi truong gia, tra `note`."""
    import approve_post as db
    import approve_dispatch as dgv
    d = tmp / "state" / state_paths.PREPARE_DIR / "d1"
    d.mkdir(parents=True, exist_ok=True)
    (d / state_paths.MANIFEST_FILE).write_text(json.dumps({"version": schema.VERSION_MANIFEST, **manifest}), encoding="utf-8")
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


def test_button_lower_ready_no_call_card_of_ethan_is_slide():
    """Dong chu Ong Chu doc duoc hom 10/09: "carousel cần tối thiểu 5 slide" —
    tren mot task le ra chi la mot tam anh."""
    with tempfile.TemporaryDirectory() as tmp:
        note = _lower_ready(Path(tmp), {"usable_count": 0, "min_images": 1,
                                   "base_min_images": 1, "image_role": "ethan"}, None)
    assert "slide" not in note.lower(), f"van goi san pham cua Ethan la slide: {note}"
    assert "ảnh" in note


def test_button_lower_ready_still_say_slide_wait_dre_and_wait_manifest_old():
    """Dre khong doi gi; manifest cu (khong co `image_role`) giu nguyen chu cu."""
    with tempfile.TemporaryDirectory() as tmp:
        note = _lower_ready(Path(tmp), {"usable_count": 4, "min_images": 8,
                                   "base_min_images": 5, "image_role": "dre"}, None)
        assert "slide" in note, note
        cu = _lower_ready(Path(tmp), {"usable_count": 4, "min_images": 8,
                                 "base_min_images": 5}, None)
        assert "slide" in cu, cu


def test_button_lower_ready_by_sidecar_when_article_already_transfer_kite():
    """`create_task_kite` doi `image_role` trong SIDECAR chu khong sua manifest, nen
    sidecar la ban moi nhat — bai da sang Kite thi lai goi la slide."""
    with tempfile.TemporaryDirectory() as tmp:
        note = _lower_ready(Path(tmp), {"usable_count": 0, "min_images": 1,
                                   "base_min_images": 1, "image_role": "ethan"},
                       {"image_role": "kite", "transferred_from": "ethan"})
    assert "slide" in note, note


# ------------------------------------------- 5. cong chan dung DONG da hong
def test_engine_take_threshold_block_from_copy_form_ky_role():
    """Cong chan o muc MA NGUON, vi dong that su hong nam trong `prepare_article()` —
    ham do mo Chromium, tai anh, goi vision, khong unit test duoc.

    Dong cu:  toi_thieu = carousel.FLAGSHIP_MIN if flagship else carousel.MIN_SLIDE
    Dong nay: toi_thieu = role.min_images(vai_anh, flagship)

    Ai do viet lai theo kieu cu thi cac test tren VAN XANH (chung dung thang
    `role.min_images` de dung manifest) — chi cong nay bat duoc.

    Nguong CHAN va cau hoi "con phai di tim nua khong" la HAI thu: cai thu hai
    nay do `role.has_enough_material`, giu o `tests/test_find_image_by_role.py`."""
    import inspect
    import re

    import image_prepare as cb
    src = inspect.getsource(cb.prepare_article)
    assert re.search(r"^\s*toi_thieu = role\.min_images\(", src, re.M), \
        ("`toi_thieu` (nguong chan, di vao manifest) khong con lay tu ban dang ky "
         "vai — do la su co 10/09/2026")


def test_threshold_block_no_got_use_make_target_go_find():
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
    a = {"uses": ["stack_vertical"], "relevant": True,
         "kind": "photo", "ratio": 1.78, "faces": 0, "alt": ""}
    assert not vai_mod.has_enough_material("ethan", [a]), \
        "engine se ngung tim khi Ethan van chua co tam nao lam nen hero"


def test_sidecar_write_before_when_engine_run():
    """Engine doc `image_role` tu sidecar .img.json ngay dau. `create_pair` tung
    goi `_block_run_engine` TRUOC `_crop_sidecar`, tuc engine doc mot tep chua ai
    ghi — truoc gio chi mat tom tat (im lang), tu 10/09/2026 mat ca nguong."""
    import inspect

    import approve_pick as dct
    src = inspect.getsource(dct.create_pair)
    assert src.index("_crop_sidecar(") < src.index("_block_run_engine("), \
        "create_pair chay engine truoc khi ghi sidecar — engine se khong biet vai"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
