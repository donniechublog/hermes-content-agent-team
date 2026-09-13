#!/usr/bin/env python3
"""ROLE LAM ANH DUOC DI TIM ANH; engine dem SLIDE dung duoc, khong dem TAM.

Su co 12/09/2026, tin TSMC (t_a8ffd2f6): engine tai 7 anh, dem "5 dung duoc /
toi thieu 5" roi NGUNG TIM. Nhung A5 900x600 la anh ngang qua thap, chi "ghep"
duoc ma khong co cap -> thuc te 4 slide. Dre block, Ong Chu phai go tay, va hoi:
"designer ma khong duoc phep di tim anh, ai nghi ra cai luat thieu nang nay?"

Giu phan dung (engine chuan bi, cong chan cua script), bo phan pha hoai:
  1. `schema.count_image_use_ok` dem slide dung duoc: anh ngang < 700px chi ghep
     duoc, hai tam moi thanh mot slide, mot tam le = 0;
  2. `role.has_enough_material` hoi cung cong thuc do -> engine di tim tiep;
  3. `find_more_images.py`: vai tu tim theo tu khoa tieng Anh / URL, toi da 3 luot;
     body task va brief Dre tro toi lenh nay TRUOC khi cho phep kanban_block.

Chay:  venv/bin/python tests/test_tim_anh_them.py
"""
import inspect
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import schema                                                 # noqa: E402
import task_bodies                                            # noqa: E402
import role                                                    # noqa: E402
import find_more_images                                           # noqa: E402
from chuan_bi import manifest                                 # noqa: E402


def _a(**k):
    a = {"ma": "A", "dung": ["thân"], "lien_quan": True, "ngang": False, "h": 1200,
         "ti_le": 1.0, "loai": "anh", "goc_trai_sang": 50, "canh_ngan": 1000, "mat": 0, "alt": ""}
    a.update(k)
    return a


def _ngang(h=1280, cat_ngang_ok=True, **k):
    # Mac dinh cat_ngang_ok=True: cac test o day dung `_ngang` de kiem tra
    # NGUONG CHIEU CAO (700px), khong phai kiem tra noi dung anh -- danh dau
    # "da xac nhan dung mot minh duoc" nhu vision that se lam voi anh nguoi/
    # san pham. Test rieng ve noi dung (chart/co chu) nam o tests/test_schema.py.
    k.setdefault("dung", ["ghép dọc với một ảnh ngang cùng tone",
                          "cat_ngang: true NẾU là ảnh người/sản phẩm KHÔNG có chữ"])
    return _a(ngang=True, h=h, ti_le=1.5, cat_ngang_ok=cat_ngang_ok, **k)


def test_anh_ngang_qua_thap_khong_dem_mot_minh():
    # Dung bo anh TSMC: bia A3, A2/A6/A7 ngang cao, A5 900x600 chi ghep.
    bo = [_a(ma="A3", dung=["bìa", "thân"]), _ngang(ma="A2", h=942), _ngang(ma="A6"),
          _ngang(ma="A7"), _ngang(ma="A5", h=600, dung=["ghép dọc với một ảnh ngang cùng tone"])]
    assert schema.count_image_use_ok(bo) == 4, "A5 le khong co cap -> 4 slide, khong phai 5"
    bo.append(_ngang(ma="A8", h=650, dung=["ghép dọc với một ảnh ngang cùng tone"]))
    assert schema.count_image_use_ok(bo) == 5, "hai tam thap ghep thanh MOT slide"
    assert schema.count_image_use_ok([_ngang(h=0)]) == 1, "khong biet chieu cao thi khong tru"


def test_engine_phai_tim_tiep_khi_chi_du_tam_ma_thieu_slide():
    # Nguong Dre tu 12/09/2026 la 6 (carousel.MIN_SLIDE); bo 6 tam trong do mot tam
    # 900x600 chi ghep duoc -> 5 slide -> chua du.
    bo = [_a(ma="A3", dung=["bìa", "thân"]), _ngang(ma="A2", h=942), _ngang(ma="A6"),
          _ngang(ma="A7"), _a(ma="A8"), _ngang(ma="A5", h=600, dung=["ghép dọc với một ảnh ngang cùng tone"])]
    assert schema.count_image_use_ok(bo) == 5
    assert not role.has_enough_material("dre", bo), "6 tam nhung 5 slide: engine CHUA duoc ngung tim"
    bo[-1]["h"] = 1000
    bo[-1]["cat_ngang_ok"] = True   # cao du (>=700) VA vision da xac nhan dung mot minh duoc
    assert role.has_enough_material("dre", bo)


def test_dre_nop_dung_cung_nguong_cat_ngang():
    src = (ROOT / "dre_nop.py").read_text(encoding="utf-8")
    assert "schema.HEIGHT_MIN_CROP_LANDSCAPE" in src, "dre_nop go cung 700 rieng -> hai nguong lech nhau"
    assert 'a["h"] < 700' not in src


def test_manifest_va_tim_them_dung_mot_cong_thuc_dan_xuat():
    src = inspect.getsource(manifest.build_manifest)
    assert "compute_derived(" in src
    src2 = inspect.getsource(find_more_images.fresh_manifest)
    assert "compute_derived(" in src2


def test_lam_moi_manifest_tinh_lai_thieu_anh():
    m = {"anh": [_a(ma="A1", dung=["bìa", "thân"]), _a(ma="A2")], "toi_thieu": 5,
         "so_dung_duoc": 5, "thieu_anh": None, "so_xep_hang": 0, "draft_id": "x"}
    # cap_ghep mo anh tu dia -> bo anh ngang rong de khong dung toi PIL
    find_more_images.fresh_manifest(m)
    assert m["so_dung_duoc"] == 2
    assert m["thieu_anh"] == {"so": 2, "toi_thieu": 5}
    m["anh"] += [_a(ma=f"A{i}") for i in range(3, 6)]
    find_more_images.fresh_manifest(m)
    assert m["so_dung_duoc"] == 5 and "thieu_anh" not in m


def test_tu_khoa_phai_tieng_anh_va_ngan():
    assert find_more_images.check_keyword(["TSMC fab Arizona"]) == []
    loi = find_more_images.check_keyword(["nhà máy TSMC", "", "a b c d e f g h"])
    assert len(loi) == 3 and "TIENG ANH" in loi[0]


def test_body_task_bao_vai_tu_tim_truoc_khi_block():
    kt = task_bodies.ket_thuc_vai_anh("/goc", "draft-1")
    assert "find_more_images.py draft-1" in kt and "/goc" in kt, "duong dan phai duoc dien, khong con {goc}"
    assert "{goc}" not in kt and "{draft_id}" not in kt
    assert kt.index("find_more_images") < kt.index("kanban_block"), "tim TRUOC, block SAU"
    for f in ("duyet_chon_tin.py", "duyet_bai.py"):
        src = (ROOT / f).read_text(encoding="utf-8")
        assert "task_bodies.ket_thuc_vai_anh(" in src, f"{f} van dien KET_THUC_VAI_ANH tho (con {{goc}})"
    body = task_bodies.CAROUSEL_BODY.format(source_note="", link="", title="", summary="", draft_id="d",
                                            brand="b", goc="/g", ket_thuc=kt)
    assert "find_more_images.py draft-1" in body


def test_brief_dre_tro_toi_lenh_tim_them_va_noi_ro_anh_chup_co_bien_hieu():
    src = (ROOT / "dre_chuan_bi.py").read_text(encoding="utf-8")
    assert "find_more_images.py" in src
    assert "biển hiệu" in src and "cat_ngang" in src


def test_openverse_chi_lay_anh_cc_du_lon():
    kq = {"results": [
        {"url": "https://u/a.jpg", "width": 4000, "height": 3000, "license": "by", "title": "TSMC Fab 18",
         "foreign_landing_url": "https://commons.wikimedia.org/wiki/File:a.jpg", "creator": "x", "source": "wikimedia"},
        {"url": "https://u/b.jpg", "width": 500, "height": 400, "license": "by"},          # nho
        {"url": "https://u/c.jpg", "width": 4000, "height": 3000, "license": "by-nc-nd"},  # giay phep khong dung duoc
        {"url": "https://u/d.svg", "width": 4000, "height": 3000, "license": "cc0"},       # do hoa
    ]}
    ra = find_more_images.filter_openverse(kq, "TSMC fab", so=8)
    assert [c["anh"] for c in ra] == ["https://u/a.jpg"]
    assert ra[0]["tu"] == "openverse" and ra[0]["giay_phep"] == "by"
    assert find_more_images.filter_openverse({}, "x", 8) == [] and find_more_images.filter_openverse(None, "x", 8) == []
    src = (ROOT / "chuan_bi" / "download_filter.py").read_text(encoding="utf-8")
    assert '"openverse"' in src, "download_and_filter se vut anh Openverse vi host khac trang (flickr cdn)"


def test_anh_commons_qua_to_lay_ban_thumb():
    u = "https://upload.wikimedia.org/wikipedia/commons/d/d6/Trucks_TSMC_Fab_18.jpg"
    u2, w, h = find_more_images.try_small_commons(u, 8192, 5461)
    assert u2 == "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/Trucks_TSMC_Fab_18.jpg/2000px-Trucks_TSMC_Fab_18.jpg"
    assert (w, h) == (2000, 1333)
    assert find_more_images.try_small_commons(u, 1800, 1200) == (u, 1800, 1200), "du nho thi giu goc"
    x = "https://live.staticflickr.com/1/a_b.jpg"
    assert find_more_images.try_small_commons(x, 9000, 6000) == (x, 9000, 6000), "khong phai Commons thi khong dong"
    kq = {"results": [{"url": u, "width": 8192, "height": 5461, "license": "by"}]}
    assert find_more_images.filter_openverse(kq, "x", 8)[0]["anh"] == u2
    src = inspect.getsource(find_more_images.candidate_commons)
    assert "try_small_commons(" in src, "duong Commons truc tiep cung phai thu nho (3 anh bi bo 12/09)"


def test_vong_tim_rong_noi_ra_tung_buoc():
    src = (ROOT / "chuan_bi" / "fallback_rounds.py").read_text(encoding="utf-8")
    for dau in ("browser boc", "Commons", "tai + loc"):
        assert f"[tim rong] {dau}" in src, f"vong tim rong im lang o buoc: {dau}"


if __name__ == "__main__":
    ok = 0
    ten = [n for n in dir() if n.startswith("test_")]
    for n in ten:
        try:
            globals()[n]()
            ok += 1
        except AssertionError as e:
            print(f"FAIL {n}: {e}")
    print(f"{ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
