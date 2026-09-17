#!/usr/bin/env python3
"""Hợp đồng dữ liệu: một công thức, một bản đọc, không phụ thuộc thứ tự (F2).

Ba duong hong CO THAT ma tep nay giu:

  1. `usable_count` thieu khoa thi BA noi doan ba kieu — dre_prepare dem lai
     bang cong thuc khac nguoi ghi (chum anh khai niem dem thanh nhieu thay vi
     MOT), con approve_post/image_prepare coi la 0 ("khong co anh nao"). Nay ca ba
     di qua `schema.count_image_use_ok`.
  2. Manifest ban cu (truoc 09/09/2026) khong co `phien_ban` va co the thieu
     khoa dan xuat. `read_manifest` bu lai bang dung cong thuc cua nguoi ghi.
  3. `write_meta` ghi DE ca dict, ma `blackboard` ghi `root_task` vao cung tep tu
     mot tien trinh khac. Hom nay chua mat chi vi thu tu goi may man.

Chay:  venv/bin/python tests/test_schema.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import schema                                                 # noqa: E402
import state_paths                                            # noqa: E402


# ---------------------------------------------- cong thuc dan xuat, mot ban
def test_chum_khai_niem_dem_la_mot():
    """5 la co Nhat, khong phai 5 slide: ca chum anh khai niem chi lam bia."""
    anh = [{"uses": ["bìa"], "concept": {"keyword": "co"}},
           {"uses": ["bìa"], "concept": {"keyword": "rack"}},
           {"uses": ["thân"]}]
    assert schema.count_image_use_ok(anh, "ethan") == 2, \
        "hai anh khai niem phai dem la MOT (cong thuc cu dem thanh 3)"


def test_anh_khong_lien_quan_khong_duoc_tinh():
    anh = [{"uses": ["thân"], "relevant": False}, {"uses": ["thân"], "relevant": True}]
    assert schema.count_image_use_ok(anh, "ethan") == 1


def test_anh_khong_dung_duoc_o_dau_thi_khong_tinh():
    assert schema.count_image_use_ok([{"uses": []}, {"uses": ["thân"]}], "ethan") == 1


def test_danh_sach_rong_va_None_deu_ra_0():
    assert schema.count_image_use_ok([], "ethan") == 0
    assert schema.count_image_use_ok(None, "ethan") == 0


def test_khop_cong_thuc_cua_nguoi_ghi():
    """Nguoi ghi (`prepare.manifest.build_manifest`) phai goi CHINH ham nay —
    doc ma nguon de chan viec ai do chep lai cong thuc lan nua."""
    src = (ROOT / "prepare" / "manifest.py").read_text(encoding="utf-8")
    assert "schema.count_image_use_ok(" in src, "nguoi ghi khong dung cong thuc chung"
    assert "so_rieng = sum(" not in src, "cong thuc cu con nam lai trong nguoi ghi"


# ------------------------------------------------------------ read_manifest
def test_ban_moi_giu_nguyen_khong_bi_dung_cham():
    m = {"version": schema.VERSION_MANIFEST, "usable_count": 99,
         "ranking_count": 7, "images": []}
    assert schema.read_manifest(m) == m


def test_ban_cu_duoc_bu_so_dung_duoc_dung_cong_thuc():
    # `concept` phai co noi dung: dict RONG la falsy nen khong danh dau gi ca
    # (chinh cho nay lam ban dau cua test sai — giu lai lam vi du).
    # Ban 0 that mang khoa Viet: read_manifest doi ten ROI moi bu khoa dan xuat.
    cu = {"anh": [{"dung": ["bìa"], "khai_niem": {"tu_khoa": "co"}},
                  {"dung": ["bìa"], "khai_niem": {"tu_khoa": "rack"}},
                  {"dung": ["thân"]}]}
    ra = schema.read_manifest(cu)
    assert ra["usable_count"] == 2, ra
    assert ra["version"] == schema.VERSION_MANIFEST
    assert "so_dung_duoc" not in ra and "anh" not in ra, ra


def test_ban_cu_khong_co_bang_xep_hang_thi_so_xep_hang_la_0():
    """Nguoi doc tung mac dinh 1 ke ca khi khong co bang nao — nguoc y nghia."""
    assert schema.read_manifest({"anh": [], "xep_hang": None})["ranking_count"] == 0


def test_ban_cu_co_bang_thi_so_xep_hang_it_nhat_1():
    ra = schema.read_manifest({"anh": [], "xep_hang": {"model": "gpt", "kieu": "bang"}})
    assert ra["ranking_count"] == 1, ra
    assert ra["ranking"] == {"model": "gpt", "kind": "bang"}, ra


def test_khong_ghi_de_khoa_da_co_cua_ban_cu():
    ra = schema.read_manifest({"anh": [{"dung": ["thân"]}], "so_dung_duoc": 42})
    assert ra["usable_count"] == 42, "bu khoa THIEU, khong duoc sua khoa da co"


def test_doc_tu_duong_dan_va_khong_nem_khi_tep_hong():
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / state_paths.MANIFEST_FILE
        p.write_text(json.dumps({"anh": [], "title": "x"}), encoding="utf-8")
        assert schema.read_manifest(p)["title"] == "x"
        p.write_text("{khong phai json", encoding="utf-8")
        assert schema.read_manifest(p) is None, "tep hong phai ra None, khong nem"
        assert schema.read_manifest(Path(t) / "khong-co.json") is None


def test_tep_json_khong_phai_dict_cung_ra_None():
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / state_paths.MANIFEST_FILE
        p.write_text("[1, 2, 3]", encoding="utf-8")
        assert schema.read_manifest(p) is None


# ------------------------------------------------------------- merge_meta
def test_tron_giu_khoa_cu_khong_co_trong_ban_moi():
    """Dung duong da suyt mat: blackboard ghi root_task, write_meta ghi de."""
    ra = schema.merge_meta({"root_task": "t_9", "title": "cu"},
                              {"title": "moi", "brand": "dcgr"})
    assert ra.get("root_task") == "t_9", "mat root_task -> the goc bang den mo coi"   # .get: do bang FAIL, khong KeyError (E-r2-7)
    assert ra["title"] == "moi" and ra["brand"] == "dcgr"


def test_ban_moi_thang_ke_ca_khi_gia_tri_rong():
    """Rong la Y CUA NGUOI GHI, khong phai 'khong co gi'."""
    assert schema.merge_meta({"via": "cu"}, {"via": ""})["via"] == ""


def test_tron_voi_ban_cu_rong_hoac_None():
    assert schema.merge_meta(None, {"a": 1}) == {"a": 1}
    assert schema.merge_meta({}, {"a": 1}) == {"a": 1}


def test_khong_sua_dict_dau_vao():
    cu = {"root_task": "t_9"}
    schema.merge_meta(cu, {"title": "moi"})
    assert cu == {"root_task": "t_9"}, "hop_nhat_meta khong duoc sua ban cu tai cho"


def test_write_meta_that_su_tron_chu_khong_ghi_de():
    """Chay ham THAT, khong mo phong: day la cho da suyt mat root_task."""
    import approve_pick as dct
    with tempfile.TemporaryDirectory() as t:
        d = Path(t)
        cu = dct.DRAFTS
        dct.DRAFTS = d
        try:
            (d / "x.meta.json").write_text(json.dumps({"root_task": "t_9"}), encoding="utf-8")
            dct.write_meta("x", {"link": "http://a", "title": "moi", "category": "ai"},
                           "x.png", "dcgr")
            m = json.loads((d / "x.meta.json").read_text(encoding="utf-8"))
        finally:
            dct.DRAFTS = cu
    assert m.get("root_task") == "t_9", f"write_meta van xoa root_task: {m}"
    assert m.get("title") == "moi" and m.get("brand") == "dcgr", m


# --------------------------------------------------- khai bao khop thuc te
def test_moi_khoa_nguoi_ghi_sinh_ra_deu_co_trong_Manifest():
    """Them khoa vao build_manifest ma quen khai o schema.Manifest thi bang khai
    bao thanh vo dung — chan tu day."""
    import ast
    src = (ROOT / "prepare" / "manifest.py").read_text(encoding="utf-8")
    cay = ast.parse(src)
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "build_manifest")
    gan_m = next(n for n in ast.walk(ham)
                 if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict)
                 and any(isinstance(t, ast.Name) and t.id == "m" for t in n.targets))
    khoa = {k.value for k in gan_m.value.keys if isinstance(k, ast.Constant)}
    thieu = sorted(khoa - set(schema._kind(schema.Manifest)))
    assert not thieu, f"dung_manifest sinh khoa chua khai trong schema.Manifest: {thieu}"


def test_moi_khoa_write_meta_deu_co_trong_Meta():
    import ast
    src = (ROOT / "approve_pick.py").read_text(encoding="utf-8")
    cay = ast.parse(src)
    ham = next(n for n in ast.walk(cay)
               if isinstance(n, ast.FunctionDef) and n.name == "write_meta")
    # Loc theo TEN bien `meta` nhu test build_manifest (E-r2-6): lay dict Assign
    # DAU TIEN thi mot dict phu dat truoc `meta = {...}` la bao hong oan.
    gan = next(n for n in ast.walk(ham)
               if isinstance(n, ast.Assign) and isinstance(n.value, ast.Dict)
               and any(isinstance(t, ast.Name) and t.id == "meta" for t in n.targets))
    khoa = {k.value for k in gan.value.keys if isinstance(k, ast.Constant)}
    thieu = sorted(khoa - set(schema._kind(schema.Meta)))
    assert not thieu, f"write_meta sinh khoa chua khai trong schema.Meta: {thieu}"


def test_doc_manifest_phien_ban_kieu_la_khong_crash():
    """N-r2-7: "1" (chuoi) hay None tung nem TypeError o `<` — ham hua None khi
    khong doc duoc ma lai crash."""
    for pv in ("1", None, "abc", 1.0):
        m = schema.read_manifest({"phien_ban": pv, "anh": []})
        assert m is not None and m["version"] == schema.VERSION_MANIFEST, (pv, m)
        assert "phien_ban" not in m, (pv, m)
    for pv in ("2", None, "abc", 2.0):
        m = schema.read_manifest({"version": pv, "images": []})
        assert m is not None and m["version"] == schema.VERSION_MANIFEST, (pv, m)


# ------------------------------------------ LOW-227: khoa Viet -> English (ban 2)
_V1_CU = {
    "phien_ban": 1, "draft_id": "d1", "brand": "dcgr", "title": "t", "tao_luc": 5,
    "toi_thieu": 6, "toi_thieu_co_ban": 6, "vai_anh": "dre", "so_dung_duoc": 1,
    "tieu_de_en": "T", "chu_bai": "x", "so_mien": ["a.com"], "cap_ghep": [["A1", "A2"]],
    "ghep_hai_hang": [], "thu_tu_anh_theo_loai": ["logo"], "goi_y_bia": ["A1"], "chua_nhin": [],
    "tin_xep_hang": True, "so_xep_hang": 1, "nguon_path": "/n.json",
    "xep_hang": {"model": "gpt", "hang": 2, "site": "lmarena", "bang": "Text", "kieu": "bang",
                 "duoc_nhac": False},
    "tu_lieu": {"cau_co_so": ["tang 10%"], "doan_dau": "mo dau", "so_nguon": 1, "tu": "browser",
                "tieu_de": "t", "nguon": [{"nhan": "bài gốc", "url": "u", "tieu_de": "t", "doan": ["p"]}]},
    "thieu_anh": {"so": 1, "toi_thieu": 6},
    "anh": [{"ma": "A1", "goc": "/w/goc/A1.png", "san": "/w/san/A1.png", "url": "https://x/1.png",
             "tu": "gốc", "trang": "https://x", "mien": "x", "dung": ["bìa"], "ghi_chu": ["n"],
             "mo_ta": "m", "lien_quan": True, "roi": True, "ti_le": 1.5, "loai": "anh", "mat": 0,
             "khai_niem": {"tu_khoa": "flag", "ly_do": "theo loại tin"},
             "thuong_hieu": {"hang": "Nvidia", "khoa": "nvidia", "loai": "nguoi", "nguoi": "Jensen Huang",
                             "vai": "CEO", "bang": "b", "nen": "tối", "ma": "NVDA", "tu_khoa": "k"},
             "thuc_the": {"ten": "TSMC", "bai": "tsmc", "nguon": "wiki"},
             "xep_hang": {"tep": "/w/xh.png", "kieu": "bang", "nguon": "s", "bang": "Text", "hang": 2,
                          "dong": "2 | gpt", "duoc_nhac": True, "logo_co": False, "site": "lmarena",
                          "model": "gpt", "url": "https://l", "logo": "o"}}],
}


def test_ban_1_khoa_viet_doc_ra_khoa_english_ban_2():
    """LOW-227: manifest ban 1 (khoa Viet) qua read_manifest ra khoa English, ca khoa
    long trong anh/brand_match/ranking/material/missing_images; GIA TRI giu nguyen."""
    ra = schema.read_manifest(json.loads(json.dumps(_V1_CU)))
    assert ra is not None
    assert ra["version"] == 2 and "phien_ban" not in ra, ra
    assert set(ra) == {"version", "draft_id", "brand", "title", "created_at", "min_images",
                       "base_min_images", "image_role", "usable_count", "title_en", "article_text",
                       "domains", "stackable_pairs", "two_company_pairs", "image_order_by_story_type",
                       "cover_suggestions", "not_yet_seen", "is_ranking_story", "ranking_count",
                       "source_path", "ranking", "material", "missing_images", "images"}, sorted(ra)
    # ban 1 da co khoa dan xuat -> KHONG tinh lai
    assert ra["usable_count"] == 1 and ra["ranking_count"] == 1, ra
    assert ra["ranking"] == {"model": "gpt", "rank": 2, "site": "lmarena", "board": "Text",
                             "kind": "bang", "mentioned": False}, ra["ranking"]
    assert ra["material"] == {"number_sentences": ["tang 10%"], "lead_paragraph": "mo dau",
                              "source_count": 1, "source": "browser", "title": "t",
                              "sources": [{"label": "bài gốc", "url": "u", "title": "t",
                                           "paragraphs": ["p"]}]}, ra["material"]
    assert ra["missing_images"] == {"count": 1, "min_images": 6}, ra["missing_images"]
    a = ra["images"][0]
    assert a == {"id": "A1", "original_path": "/w/goc/A1.png", "ready_path": "/w/san/A1.png",
                 "url": "https://x/1.png", "source": "gốc", "page_url": "https://x", "domain": "x",
                 "uses": ["bìa"], "notes": ["n"], "description": "m", "relevant": True,
                 "cluttered_legacy": True, "ratio": 1.5, "kind": "anh", "faces": 0,
                 "concept": {"keyword": "flag", "reason": "theo loại tin"},
                 "brand_match": {"company": "Nvidia", "key": "nvidia", "kind": "nguoi",
                                 "person": "Jensen Huang", "person_role": "CEO", "board": "b",
                                 "background_tone": "tối", "ticker": "NVDA", "keyword": "k"},
                 "entity": {"name": "TSMC", "article_name": "tsmc", "source": "wiki"},
                 "ranking": {"file_path": "/w/xh.png", "kind": "bang", "source": "s", "board": "Text",
                             "rank": 2, "row": "2 | gpt", "mentioned": True, "has_logo": False,
                             "site": "lmarena", "model": "gpt", "url": "https://l", "logo": "o"}}, a
    # thu tu khoa giu nguyen (so byte-for-byte voi ban cu can dieu nay)
    assert list(a)[:4] == ["id", "original_path", "ready_path", "url"], list(a)


def test_ban_0_khong_co_phien_ban_van_bu_khoa_dan_xuat():
    ra = schema.read_manifest({"draft_id": "d0", "anh": [{"ma": "A1", "dung": ["thân"], "lien_quan": True}],
                               "xep_hang": {"model": "gpt", "kieu": "bang"}})
    assert ra["version"] == 2, ra
    assert ra["usable_count"] == 1 and ra["ranking_count"] == 1, ra
    assert ra["images"] == [{"id": "A1", "uses": ["thân"], "relevant": True}], ra


def test_migrate_manifest_idempotent_va_chan_lan_khoa():
    import manifest_migration as mig
    goc = json.loads(json.dumps(_V1_CU))
    mot = mig.migrate_manifest(goc)
    assert goc == _V1_CU, "migrate_manifest khong duoc sua dict dau vao tai cho"
    hai = mig.migrate_manifest(json.loads(json.dumps(mot)))
    assert hai == mot, "chay lan hai tren ban da doi phai ra y het"
    assert list(hai["images"][0]) == list(mot["images"][0]), "thu tu khoa phai giu"
    try:
        mig.migrate_manifest({"draft_id": "d", "anh": [{"ma": "A1", "id": "A1"}]})
    except mig.KeyConflict:
        pass
    else:
        raise AssertionError("anh co ca `ma` lan `id` phai nem KeyConflict, khong doan")
    assert schema.read_manifest({"draft_id": "d", "anh": [{"ma": "A1", "id": "A1"}]}) is None, \
        "read_manifest gap lan khoa phai ra None (khong nem)"


def test_xong_json_khong_phai_manifest_bi_bo_qua():
    """Itachi ghi `{khoa, slides}` va Ada ghi bao cao gom cung ten `manifest.json`."""
    import manifest_migration as mig
    assert not mig.is_manifest({"khoa": "k", "slides": [{"anh": "A1"}]})
    assert not mig.is_manifest({"token": 1, "kanban": {}, "manifest": {}, "draft": "d"})
    assert mig.is_manifest({"draft_id": "d", "anh": []})
    assert mig.is_manifest({"draft_id": "d", "images": []})


def _khoa_dict_ghi_vao(src: str, ten_tep: str) -> set:
    """Khoa cua dict literal duoc ghi vao tep co ten chua `ten_tep` (qua
    _write_json/ghi_json/write_text) — doc bang ast, comment khong tinh."""
    import ast
    ra = set()
    for n in ast.walk(ast.parse(src)):
        if not isinstance(n, ast.Call) or not n.args:
            continue
        co_tep = any(isinstance(c, ast.Constant) and isinstance(c.value, str) and ten_tep in c.value
                     for c in ast.walk(n.args[0]))
        if not co_tep:
            continue
        for d in ast.walk(n):
            if isinstance(d, ast.Dict):
                ra |= {k.value for k in d.keys if isinstance(k, ast.Constant)}
    return ra


def test_moi_khoa_writer_json_deu_co_trong_SidecarViet():
    """ADF-r2-5: .writer.json truoc day khong co TypedDict nao."""
    src = (ROOT / "approve_pick.py").read_text(encoding="utf-8")
    khoa = _khoa_dict_ghi_vao(src, "writer.json")
    assert khoa, "khong tim thay cho ghi writer.json trong approve_pick — cong nay mu"
    thieu = sorted(khoa - set(schema._kind(schema.SidecarWrite)))
    assert not thieu, f"writer.json ghi khoa chua khai trong schema.SidecarViet: {thieu}"


def test_moi_khoa_img_json_deu_co_trong_SidecarAnh():
    src = (ROOT / "approve_pick.py").read_text(encoding="utf-8")
    khoa = _khoa_dict_ghi_vao(src, "img.json")
    assert khoa, "khong tim thay cho ghi img.json trong approve_pick"
    thieu = sorted(khoa - set(schema._kind(schema.SidecarImage)))
    assert not thieu, f"img.json ghi khoa chua khai trong schema.SidecarAnh: {thieu}"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())


# ---------------------------------------- cat_ngang_ok (su co t_a8ffd2f6 lan hai, 12/09)
def test_ngang_qua_thap_van_chi_ghep_bat_ke_cat_ngang_ok():
    a = {"uses": ["x"], "relevant": True, "landscape": True, "h": 600, "landscape_crop_ok": True}
    assert schema._only_stack_ok(a), "duoi 700px thi du vision noi 'co' cung khong cat duoc"


def test_ngang_cao_co_chu_khong_dung_mot_minh_duoc():
    """A7/A12 tin TSMC: bien hieu/logo TREN toa nha (CO CHU) — vision tra
    landscape_crop_ok=False, truoc day cong thuc chi nhin chieu cao nen dem sai
    la "dung mot minh duoc", thua 2 slide so voi thuc te Dre gap."""
    a = {"uses": ["x"], "relevant": True, "landscape": True, "h": 1067, "landscape_crop_ok": False}
    assert schema._only_stack_ok(a)


def test_ngang_cao_nguoi_san_pham_khong_chu_dung_mot_minh_duoc():
    """A8 tin TSMC: ky thuat vien cam chip, KHONG chu — vision xac nhan True."""
    a = {"uses": ["x"], "relevant": True, "landscape": True, "h": 768, "landscape_crop_ok": True}
    assert not schema._only_stack_ok(a)


def test_chua_xac_nhan_thi_an_toan_coi_la_chi_ghep():
    """landscape_crop_ok vang mat (manifest cu chua nhin lai, hoac vision hong o
    cau hoi nay) -- None, KHAC voi False nhung van phai xu ly nhu chua dung
    mot minh duoc: dong con hon dem thua roi Dre chet giua chung lan hai."""
    a = {"uses": ["x"], "relevant": True, "landscape": True, "h": 900}
    assert schema._only_stack_ok(a)


def test_chart_ngang_cao_van_dung_mot_minh_du_khong_hoi_cat_ngang():
    """A10/A11: chart dung duoc qua duong rieng 'than, dan full be ngang', khong
    can landscape_crop_ok — landscape_crop_ok=None nhung kind=chart thi van KHONG chi_ghep."""
    a = {"uses": ["x"], "relevant": True, "landscape": True, "h": 1628, "kind": "chart"}
    assert not schema._only_stack_ok(a)


def test_tinh_lai_bo_anh_that_tsmc_lan_hai():
    """Tai hien dung bo 8 anh dung duoc cua t_a8ffd2f6 sau khi Dre chay that
    (12/09 chieu): A5 qua thap, A7/A12 co chu, A8 nguoi/san pham, A10/A11 chart."""
    def _a(ma, ngang, h, **k):
        d = {"id": ma, "uses": ["x"], "relevant": True, "landscape": ngang, "h": h}
        d.update(k)
        return d
    # ratio: A5 900x600 do that; A7/A12 bo goc khong ghi, gia dinh 16:9 (bien
    # hieu/logo chup ngang) — LOW-46 dem cap theo ti le that, khong con // 2.
    bo = [_a("A3", False, 1166), _a("A5", True, 600, ratio=1.5), _a("A6", False, 1020),
          _a("A7", True, 1067, landscape_crop_ok=False, ratio=1.78),
          _a("A8", True, 768, landscape_crop_ok=True),
          _a("A10", True, 1628, kind="chart"), _a("A11", True, 820, kind="chart"),
          _a("A12", True, 853, landscape_crop_ok=False, ratio=1.78)]
    # rieng khong chi_ghep: A3, A6, A8, A10, A11 = 5. chi_ghep: A5, A7, A12 = 3 ->
    # cap roi nhau lon nhat = 1 (ba tam chi ghep toi da mot cap).
    assert schema.count_image_use_ok(bo, "ethan") == 6
