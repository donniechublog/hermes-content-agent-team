#!/usr/bin/env python3
"""ENGINE CON PHAI DI TIM ANH NUA KHONG — hoi theo ROLE, khong do bang so cua
carousel (LOW-12, 10/09/2026).

Ong Chu: *"Ethan khong tu di tim anh lien quan tren mang ma chi tim anh co trong
article goc"*. Hoi lai lan mot: *"Dre tim duoc anh ma Ethan ko tim duoc? dau can
phai tu di may mo. dung code co san cung tim duoc ma?"* — dung, `_round_widen_search`
(Bing -> bao khac cung tin -> browser boc anh + Commons) da co san du may moc,
hong nam o DIEU KIEN mo cong. Lan hai, chot cai sai that su: *"cach lam anh cua
Ethan dau phai la carousel? nhung gi thuoc ve carousel ma lien quan toi Ethan la
nhung thu ko dung"* va *"tieu chi ve anh thi la chung cua moi designer, nhung
carousel la nhieu anh con Ethan lam single image, nen 'so luong' ko the la thu
ap vao duoc"*.

Ban cu do bang MOT con so cho ca ba vai:

    muc_tieu_tim = max(toi_thieu, carousel.FLAGSHIP_MIN if flagship else carousel.MIN_SLIDE)
    if len(dung_duoc) < muc_tieu_tim ...

Tin co 5 anh ngang 16:9 (hinh dang thuong gap nhat cua anh bao) dem ra "du 5"
nen engine ngung tim; nhung card.py chan anh ngang >1.6 lan chart di mot minh,
tuc Ethan con 0 duong dung, ma brief cam vai tu tai them ("chi dung MA ANH").

Nay `role.has_enough_material` tra loi: MOI vai deu phai co mot tam lam anh chinh,
rieng SO LUONG thi chi vai xep nhieu anh moi bi dem. Tieu chi CHAT LUONG van
dung chung o image_rules + classify, khong dong toi.

Chay:  venv/bin/python tests/test_find_image_by_role.py
"""
import ast
import inspect
import sys
import tempfile
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_prepare as cb                                       # noqa: E402


# ------------------------------------------------------------------ do dac that
class _Phien:
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _image(ma: str, **doi) -> dict:
    """Anh doc 4:5, day toi, khong mat — `classify` dan nhan "bìa" cho no, va
    card.py cung dung lam nen hero duoc."""
    a = {"id": ma, "original_path": f"/khong-co/{ma}.png", "url": f"http://vi.du/{ma}.png",
         "ratio": 0.8, "w": 960, "h": 1200, "kind": "photo", "landscape": False,
         "uses": ["cover", "body"], "relevant": True, "faces": 0, "bottom_left_brightness": 60,
         "short_side": 960, "domain": "vi_du.com", "source": "bai", "alt": "", "notes": []}
    a.update(doi)
    return a


def _image_landscape(ma: str) -> dict:
    """16:9 (1.78): Dre ghep doc thanh mot slide, Ethan khong dung duoc (>1.6)."""
    return _image(ma, ratio=1.78, w=1920, h=1080, landscape=True, short_side=1080,
                uses=["stack_vertical"])


def _image_landscape_fit(ma: str) -> dict:
    """1.5: qua LANDSCAPE_CLEAR (1.4) nen KHONG co nhan "bìa" cua carousel, nhung card.py
    cho toi 1.6 — day dung la cho luat cua carousel bat Ethan di tim vo ich."""
    return _image(ma, ratio=1.5, w=1500, h=1000, landscape=True, short_side=1000,
                uses=["stack_vertical"])


def _image_chart(ma: str) -> dict:
    return _image(ma, ratio=1.2, w=1200, h=1000, kind="chart", short_side=1000,
                bottom_left_brightness=200, uses=["body_chart_full_width"])


PHA_NANG = ("BrowserSession", "load_source", "_summary_from_img_json", "_supplement_source", "_extra_announcement_page",
            "_take_from_browser", "_capture_ranking", "_gather_and_download_image", "_seen_image",
            "_round_widen_search", "_round_brand", "_round_concept", "_round_capture_source",
            "_round_entity", "_article_material",
            "build_manifest", "contact_sheet")


def _fallback_rounds_already_run(anh_bai: list, vai_anh="ethan", khong_browser=False,
                     tieu_de="OpenAI ships new image model for developers") -> list:
    """Chay THAT `prepare_article()` voi moi pha nang thay bang stub, tra ve ten cac vong
    bu da duoc goi. Khong mang, khong browser, khong vision."""
    goi = []
    cu = {k: getattr(cb, k) for k in PHA_NANG}

    def _vong(ten):
        def f(a, *args, **kw):
            goi.append(ten)
            return a, [x for x in a if x["uses"]], []
        return f

    cb.BrowserSession = lambda *a, **k: _Phien()
    cb.load_source = lambda d, m, s, phien=None: ({"pages": [], "title_en": tieu_de},
                                                Path(s) / "n.json", "http://vi.du/a")
    cb._summary_from_img_json = lambda d: {"image_role": vai_anh, "summary": ""}
    cb._supplement_source = lambda *a, **k: []
    cb._extra_announcement_page = lambda n, p, trang, *a, **k: trang
    cb._take_from_browser = lambda trang, *a, **k: (
        {"title_en": "", "article_text": "", "cands": [], "extra_pages": []}, trang)
    cb._capture_ranking = lambda *a, **k: ([], False)
    cb._gather_and_download_image = lambda *a, **k: anh_bai
    cb._seen_image = lambda a, nguon, t, wd: (a, [x for x in a if x["uses"]], [])
    cb._round_widen_search = _vong("tim_rong")
    cb._round_brand = _vong("thuong_hieu")
    cb._round_concept = _vong("khai_niem")
    # `_round_capture_source` PHAI thay bang gia nhu moi vong khac: truoc 13/09/2026
    # no bi bo quen, nen test "khong mang, khong browser" van goi that vao no —
    # thay bang mot dong "[chup_lead] ... AttributeError '_Phien' object has no
    # attribute 'trang'" o moi luot chay, va tu khi vong nay tu hoi them bao
    # cung tin (Bing) thi con la mot cu goi MANG THAT giua bo test offline.
    cb._round_capture_source = _vong("chup_nguon")
    # Nac thuc the (3a3cda5) cung la pha nang (Wikipedia/Commons) — khong stub thi
    # no chay mang that va co the tra du anh, khai niem khong bao gio toi luot.
    # `_round_entity` (Wikipedia pageimages) cung goi mang THAT, lam tep test
    # "khong mang" nay ton 6 phut 34 (do 13/09/2026) thay vi vai giay.
    cb._round_entity = _vong("thuc_the")
    cb._article_material = lambda *a, **k: {"sentence_has_count": [], "lead_paragraph": "", "source_count": 1}
    cb.build_manifest = lambda *a, **k: {"images": anh_bai}
    cb.contact_sheet = lambda *a, **k: None
    from tam import block_network
    try:
        with tempfile.TemporaryDirectory() as tmp, block_network() as tried:
            cb.prepare_article("d1", {"brand": "donniechublog", "title": tieu_de},
                        Path(tmp), Path(tmp), khong_browser=khong_browser)
    finally:
        for k, v in cu.items():
            setattr(cb, k, v)
    # Luoi cuoi cho moi pha lot stub (22/09/2026, xem tam.block_network).
    assert not tried, f"prepare_article() goi mang THAT — co pha nang chua stub: {tried[:5]}"
    return goi


# ------------------------------------------------------- vai MOT ANH (Ethan)
def test_article_enough_image_code_no_temp_which_len_hero_then_still_go_find():
    """Dung canh sinh ra su co: bai goc cho DU 5 anh nhung toan 16:9 / chart."""
    for ten, bo in (("5 ngang 16:9", [_image_landscape(f"A{i + 1}") for i in range(5)]),
                    ("3 ngang + 2 chart", [_image_landscape("A1"), _image_landscape("A2"), _image_landscape("A3"),
                                           _image_chart("A4"), _image_chart("A5")]),
                    ("9 ngang — nhieu khong cuu duoc", [_image_landscape(f"A{i + 1}") for i in range(9)])):
        goi = _fallback_rounds_already_run(bo)
        assert "tim_rong" in goi, \
            f"{ten}: Ethan het duong lam hero ma engine khong di tim (da chay: {goi or 'khong vong nao'})"


def test_face_no_clear_ai_no_static_is_hero():
    """`submit_common.check_subject_named` chan anh co mat ma khong khai `nhan_vat`, va vai
    khong duoc bia ten cho qua cong — tam do khong phai mot duong dung duoc."""
    assert "tim_rong" in _fallback_rounds_already_run([_image(f"A{i + 1}", faces=1) for i in range(5)])
    assert "tim_rong" not in _fallback_rounds_already_run(
        [_image("A1", faces=1, alt="Jensen Huang speaks at GTC")]), \
        "alt da neu ten thi Ethan khai duoc nhan_vat — khong can di tim nua"


def test_one_temp_hero_is_enough_wait_card_single():
    """So luong khong phai tieu chi cua vai lam san pham mot anh (Ong Chu
    10/09/2026). Mot tam dung duoc la du, khong doi cho du 5."""
    assert "tim_rong" not in _fallback_rounds_already_run([_image("A1")]), \
        "Ethan da co nen hero ma engine van tra tien mot phien browser di tim"


def test_rules_ratio_right_is_of_card_no_right_of_carousel():
    """Anh 1.5: carousel khong goi la "bìa" (qua LANDSCAPE_CLEAR 1.4) nhung card.py cho
    toi 1.6. Do bang nhan cua carousel la Ethan di tim mot cach vo ich."""
    assert "tim_rong" not in _fallback_rounds_already_run([_image_landscape_fit("A1")]), \
        "do anh cua Ethan bang nguong 1.4 cua carousel thay vi 1.6 cua card.py"


def test_no_browser_still_no_open_session_which():
    goi = _fallback_rounds_already_run([_image_landscape(f"A{i + 1}") for i in range(5)], khong_browser=True)
    assert "tim_rong" not in goi, f"--khong-browser ma van mo browser di tim rong: {goi}"


# --------------------------------------------------- vai NHIEU ANH (Dre, Kite)
def test_role_many_image_keep_raw_way_count_old():
    """Ban sua khong duoc dong toi Dre/Kite: o do moi slide an mot tam that, nen
    SO LUONG van la mot tieu chi that."""
    for vai_anh in ("dre", "kite"):
        assert "tim_rong" not in _fallback_rounds_already_run([_image(f"A{i + 1}") for i in range(6)],
                                                  vai_anh=vai_anh), \
            f"{vai_anh}: du 6 tam va co bia ma van di tim"
        assert "tim_rong" in _fallback_rounds_already_run([_image("A1"), _image("A2")], vai_anh=vai_anh), \
            f"{vai_anh}: moi 2 tam ma khong di tim — thieu 3 slide"
        assert "tim_rong" in _fallback_rounds_already_run([_image_landscape(f"A{i + 1}") for i in range(5)],
                                              vai_anh=vai_anh), \
            f"{vai_anh}: du 5 tam nhung khong tam nao lam bia duoc"


def test_image_concept_still_is_path_last():
    """Anh khai niem (co, rack, datacenter) chung chung, phai doi den luc that su
    het duong — va phai di SAU vong tim anh that o bao khac."""
    goi = _fallback_rounds_already_run([_image_landscape(f"A{i + 1}") for i in range(5)])
    assert goi.index("tim_rong") < goi.index("khai_niem")
    assert "khai_niem" not in _fallback_rounds_already_run([_image("A1")]), \
        "bai da co nen hero that ma van day them anh minh hoa chung chung"


# ------------------------------------------- cong o muc ma nguon (chong troi)
def _if_extract_error_call(goc: ast.AST, ten: str) -> list:
    """Cac node `ast.If` ma than no goi thang `ten(...)`."""
    ra = []

    def di(node, boc):
        if isinstance(node, ast.Call) and getattr(node.func, "id", "") == ten and boc is not None:
            ra.append(boc)
        if isinstance(node, ast.If):
            di(node.test, boc)
            for c in node.body + node.orelse:
                di(c, node)
            return
        for c in ast.iter_child_nodes(node):
            di(c, boc)

    di(goc, None)
    return ra


def _name_function_within(nut: ast.AST) -> set:
    ra = set()
    for n in ast.walk(nut):
        if isinstance(n, ast.Call):
            f = n.func
            ra.add(getattr(f, "id", "") or getattr(f, "attr", ""))
    return ra


def test_two_fallback_rounds_right_ask_copy_form_ky_role():
    """Cong chong troi: cac test tren dung stub, nen ai do do lai bang mot phep
    dem khac van co the vo tinh xanh khi con so tinh co thuan. Day bat thang
    HINH DANG cua ma."""
    goc = ast.parse(textwrap.dedent(inspect.getsource(cb.prepare_article)))
    for ten_vong in ("_round_widen_search", "_round_concept"):
        ifs = _if_extract_error_call(goc, ten_vong)
        assert ifs, f"khong tim thay loi goi {ten_vong} trong mot `if` cua chuan_bi()"
        for nut in ifs:
            assert "has_enough_material" in _name_function_within(nut.test), (
                f"dieu kien mo {ten_vong} khong con hoi `role.has_enough_material` — do la "
                "LOW-12: no se lai do bo anh cua Ethan bang so slide cua carousel")


def test_no_remaining_count_which_of_carousel_within_path_go_find():
    """`prepare_article()` chay chung cho ca ba vai, nen mot hang so cua carousel nam
    trong do la ap luat cua Dre len Ethan (Ong Chu 10/09/2026)."""
    src = textwrap.dedent(inspect.getsource(cb.prepare_article))
    for cam in ("MIN_SLIDE", "FLAGSHIP_MIN"):
        for dong in src.splitlines():
            d = dong.strip()
            assert d.startswith("#") or cam not in d, \
                f"con so cua carousel quay lai trong chuan_bi(): {d}"
    for dong in src.splitlines():
        d = dong.strip()
        assert d.startswith("#") or "len(dung_duoc)" not in d, \
            f"dang dem tam anh trong chuan_bi() thay vi hoi vai: {d}"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
