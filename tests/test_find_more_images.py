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

Chay:  venv/bin/python tests/test_find_more_images.py
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
from prepare import manifest                                 # noqa: E402


def _a(**k):
    a = {"id": "A", "uses": ["body"], "relevant": True, "landscape": False, "h": 1200,
         "ratio": 1.0, "kind": "photo", "bottom_left_brightness": 50, "short_side": 1000, "faces": 0, "alt": ""}
    a.update(k)
    return a


def _landscape(h=1280, cat_ngang_ok=True, **k):
    # Mac dinh landscape_crop_ok=True: cac test o day dung `_landscape` de kiem tra
    # NGUONG CHIEU CAO (700px), khong phai kiem tra noi dung anh -- danh dau
    # "da xac nhan dung mot minh duoc" nhu vision that se lam voi anh nguoi/
    # san pham. Test rieng ve noi dung (chart/co chu) nam o tests/test_schema.py.
    k.setdefault("uses", ["stack_vertical",
                          "landscape_crop_if_no_text"])
    k.setdefault("ratio", 1.5)
    return _a(landscape=True, h=h, landscape_crop_ok=cat_ngang_ok, **k)


def test_image_landscape_over_low_no_count_alone():
    # Dung bo anh TSMC: bia A3, A2/A6/A7 ngang cao, A5 900x600 chi ghep.
    bo = [_a(id="A3", uses=["cover", "body"]), _landscape(id="A2", h=942), _landscape(id="A6"),
          _landscape(id="A7"), _landscape(id="A5", h=600, uses=["stack_vertical"])]
    assert schema.count_image_use_ok(bo, "dre") == 4, "A5 le khong co cap -> 4 slide, khong phai 5"
    bo.append(_landscape(id="A8", h=650, uses=["stack_vertical"]))
    # LOW-46: nguoi dem hoi cung `stack_fit_frame` voi cong chan; LOW-178 (16/09/2026):
    # san ghep rieng cua Dre nhan cap 3:2+3:2 (0.75), nen ca hai cung dem A5+A8 la MOT slide.
    assert schema.count_image_use_ok(bo, "dre") == 5, \
        "hai tam 3:2 ghep ra 0.75 — Dre ghep duoc (STACK_FLOOR), dem mot slide"
    bo[-2]["ratio"] = bo[-1]["ratio"] = 1.0
    assert schema.count_image_use_ok(bo, "dre") == 4, "hai tam 1:1 ghep ra 0.5 — duoi san, khong dem"
    bo[-2]["ratio"] = bo[-1]["ratio"] = 1.78
    assert schema.count_image_use_ok(bo, "dre") == 5, "hai tam 16:9 thap ghep thanh MOT slide"
    assert schema.count_image_use_ok([_landscape(h=0)], "dre") == 1, "khong biet chieu cao thi khong tru"


def test_engine_right_find_next_when_only_enough_temp_code_missing_slide():
    # Nguong Dre tu 12/09/2026 la 6 (carousel.MIN_SLIDE); bo 6 tam trong do mot tam
    # 900x600 chi ghep duoc -> 5 slide -> chua du.
    bo = [_a(id="A3", uses=["cover", "body"]), _landscape(id="A2", h=942), _landscape(id="A6"),
          _landscape(id="A7"), _a(id="A8"), _landscape(id="A5", h=600, uses=["stack_vertical"])]
    assert schema.count_image_use_ok(bo, "dre") == 5
    assert not role.has_enough_material("dre", bo), "6 tam nhung 5 slide: engine CHUA duoc ngung tim"
    bo[-1]["h"] = 1000
    bo[-1]["landscape_crop_ok"] = True   # cao du (>=700) VA vision da xac nhan dung mot minh duoc
    assert role.has_enough_material("dre", bo)


def test_dre_submit_use_same_threshold_crop_landscape():
    src = (ROOT / "dre_submit.py").read_text(encoding="utf-8")
    assert "schema.HEIGHT_MIN_CROP_LANDSCAPE" in src, "dre_submit go cung 700 rieng -> hai nguong lech nhau"
    assert 'a["h"] < 700' not in src


def test_manifest_and_find_extra_use_one_gate_actual_guide_export():
    src = inspect.getsource(manifest.build_manifest)
    assert "compute_derived(" in src
    src2 = inspect.getsource(find_more_images.fresh_manifest)
    assert "compute_derived(" in src2


def test_fresh_manifest_static_again_missing_image():
    m = {"images": [_a(id="A1", uses=["cover", "body"]), _a(id="A2")], "min_images": 5,
         "usable_count": 5, "missing_images": None, "ranking_count": 0, "draft_id": "x",
         "image_role": "dre"}
    # stackable_pairs mo anh tu dia -> bo anh ngang rong de khong dung toi PIL
    find_more_images.fresh_manifest(m)
    assert m["usable_count"] == 2
    assert m["missing_images"] == {"count": 2, "min_images": 5}
    m["images"] += [_a(id=f"A{i}") for i in range(3, 6)]
    find_more_images.fresh_manifest(m)
    assert m["usable_count"] == 5 and "missing_images" not in m


def test_keyword_right_language_image_and_short():
    assert find_more_images.check_keyword(["TSMC fab Arizona"]) == []
    loi = find_more_images.check_keyword(["nhà máy TSMC", "", "a b c d e f g h"])
    assert len(loi) == 3 and "TIENG ANH" in loi[0]


def test_body_task_report_role_from_find_before_when_block():
    kt = task_bodies.end_role_image("/goc", "draft-1")
    assert "find_more_images.py draft-1" in kt and "/goc" in kt, "duong dan phai duoc dien, khong con {goc}"
    assert "{goc}" not in kt and "{draft_id}" not in kt
    assert kt.index("find_more_images") < kt.index("kanban_block"), "tim TRUOC, block SAU"
    for f in ("approve_pick.py", "approve_post.py"):
        src = (ROOT / f).read_text(encoding="utf-8")
        assert "task_bodies.end_role_image(" in src, f"{f} van dien END_ROLE_IMAGE tho (con {{goc}})"
    body = task_bodies.CAROUSEL_BODY.format(source_note="", link="", title="", summary="", draft_id="d",
                                            brand="b", goc="/g", ket_thuc=kt)
    assert "find_more_images.py draft-1" in body


def test_brief_dre_point_dark_command_find_extra_and_say_clear_image_capture_has_variable_understand():
    src = (ROOT / "dre_prepare.py").read_text(encoding="utf-8")
    assert "find_more_images.py" in src
    assert "biển hiệu" in src and "landscape_crop" in src


def test_openverse_only_take_image_cc_enough_large():
    kq = {"results": [
        {"url": "https://u/a.jpg", "width": 4000, "height": 3000, "license": "by", "title": "TSMC Fab 18",
         "foreign_landing_url": "https://commons.wikimedia.org/wiki/File:a.jpg", "creator": "x", "source": "wikimedia"},
        {"url": "https://u/b.jpg", "width": 500, "height": 400, "license": "by"},          # nho
        {"url": "https://u/c.jpg", "width": 4000, "height": 3000, "license": "by-nc-nd"},  # giay phep khong dung duoc
        {"url": "https://u/d.svg", "width": 4000, "height": 3000, "license": "cc0"},       # do hoa
    ]}
    ra = find_more_images.filter_openverse(kq, "TSMC fab", so=8)
    assert [c["image_url"] for c in ra] == ["https://u/a.jpg"]
    assert ra[0]["source"] == "openverse" and ra[0]["license"] == "by"
    assert find_more_images.filter_openverse({}, "x", 8) == [] and find_more_images.filter_openverse(None, "x", 8) == []
    src = (ROOT / "prepare" / "download_filter.py").read_text(encoding="utf-8")
    assert '"openverse"' in src, "download_and_filter se vut anh Openverse vi host khac trang (flickr cdn)"


def test_commons_images_over_to_take_copy_thumb():
    u = "https://upload.wikimedia.org/wikipedia/commons/d/d6/Trucks_TSMC_Fab_18.jpg"
    u2, w, h = find_more_images.try_small_commons(u, 8192, 5461)
    assert u2 == "https://upload.wikimedia.org/wikipedia/commons/thumb/d/d6/Trucks_TSMC_Fab_18.jpg/2000px-Trucks_TSMC_Fab_18.jpg"
    assert (w, h) == (2000, 1333)
    assert find_more_images.try_small_commons(u, 1800, 1200) == (u, 1800, 1200), "du nho thi giu goc"
    x = "https://live.staticflickr.com/1/a_b.jpg"
    assert find_more_images.try_small_commons(x, 9000, 6000) == (x, 9000, 6000), "khong phai Commons thi khong dong"
    kq = {"results": [{"url": u, "width": 8192, "height": 5461, "license": "by"}]}
    assert find_more_images.filter_openverse(kq, "x", 8)[0]["image_url"] == u2
    src = inspect.getsource(find_more_images.candidate_commons)
    assert "try_small_commons(" in src, "duong Commons truc tiep cung phai thu nho (3 anh bi bo 12/09)"


def test_round_widen_search_say_out_each_step():
    src = (ROOT / "prepare" / "fallback_rounds.py").read_text(encoding="utf-8")
    for dau in ("browser boc", "Commons", "tai + loc"):
        assert f"[tim rong] {dau}" in src, f"vong tim rong im lang o buoc: {dau}"


def test_keywords_run_in_parallel_each_in_own_dir():
    # LOW-456: 3 tu khoa tuan tu ~115 s + vision cham terminal.timeout 180 s cua hermes.
    import tempfile
    import time
    seen_dirs = []

    def slow(tk, wd, mien_co, phien=None, deadline=None, out=None):
        seen_dirs.append(wd)
        time.sleep(0.5)
        out.append({"image_url": f"https://x/{tk}.jpg", "score": 40})
        return out

    wd = Path(tempfile.mkdtemp())
    t0 = time.time()
    cands, unfinished = find_more_images.search_keywords(["a", "b", "c"], wd, set(), budget=5, search=slow)
    took = time.time() - t0
    assert took < 1.2, f"3 tu khoa x 0.5 s phai chay song song, mat {took:.2f}s"
    assert sorted(c["image_url"] for c in cands) == ["https://x/a.jpg", "https://x/b.jpg", "https://x/c.jpg"]
    assert unfinished == []
    assert len(set(seen_dirs)) == 3, "moi tu khoa mot thu muc: anh chup figure dat ten theo so trang, chung la de len nhau"


def test_budget_returns_partial_candidates_instead_of_hanging():
    # LOW-456: 8/58 lan goi 03/10 bi giet o 180 s, mat het ung vien da tim.
    import tempfile
    import time

    def hang(tk, wd, mien_co, phien=None, deadline=None, out=None):
        out.append({"image_url": f"https://x/{tk}.jpg", "score": 40})   # nguon dau da xong
        if tk == "slow":
            time.sleep(3)                                                  # nguon sau treo
        return out

    t0 = time.time()
    cands, unfinished = find_more_images.search_keywords(["fast", "slow"], Path(tempfile.mkdtemp()), set(),
                                                         budget=0.3, search=hang)
    took = time.time() - t0
    assert took < 1.5, f"het ngan sach 0.3 s phai tra ngay, mat {took:.2f}s"
    assert unfinished == ["slow"]
    assert {c["image_url"] for c in cands} == {"https://x/fast.jpg", "https://x/slow.jpg"}, \
        "ung vien cua tu khoa chua xong van phai duoc dung"


def test_candidate_keyword_skips_remaining_sources_after_deadline():
    import time
    import find_image_web
    calls = []
    old = (find_image_web.find_image_web, find_more_images.article_sources.other_outlets_bing)
    find_image_web.find_image_web = lambda *a, **k: calls.append("web") or [{"image_url": "u", "score": 1}]
    find_more_images.article_sources.other_outlets_bing = lambda *a, **k: calls.append("bing") or []
    try:
        out = find_more_images.candidate_keyword("x", Path("."), set(), deadline=time.time() - 1)
    finally:
        find_image_web.find_image_web, find_more_images.article_sources.other_outlets_bing = old
    assert calls == ["web"], f"qua moc thi khong goi tiep nguon nao: {calls}"
    assert out == [{"image_url": "u", "score": 1}]


def test_search_budget_leaves_room_under_terminal_timeout():
    # p90 tai + loc + vision sau pha tim ~50 s (do 29/09–03/10); hermes giet o 180 s.
    assert find_more_images.SEARCH_BUDGET_SECONDS + 60 < 180


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
