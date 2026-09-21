#!/usr/bin/env python3
"""Cong chan spec carousel cua Dre (`dre_submit.resolve_spec`).

Audit 06/09/2026 do: ham nay 166 dong, 36 nhanh, va gan nhu KHONG co test —
`test_gate` nhac `bob_submit` 19 lan, `dre_submit` mot lan. No la cho duy nhat
kiem spec cua Dre truoc khi ve, va phan lon luat trong do la luat Ong Chu tu
dat sau mot su co that: khong dung lai anh, khong lay chart lam bia, mat nguoi
phai khai ten co trong bai. (13/09/2026: bo cong "khong ghep hai anh lech
tone" khoi he thong, xem test_ghep_hai_anh_lech_tone_khong_con_bi_chan.)

Cong nay bao loi THAY VI ve sai, nen no hong theo hai chieu deu dat:
  - bao oan  -> Dre sua kieu gi cung khong nop duoc (da xay ra voi cong xep
                hang, xem chu thich dai o dre_submit.py:97)
  - bo sot   -> anh sai len thang Telegram

Chay:  venv/bin/python tests/test_spec_dre.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw  # noqa: E402

from tam import so_tam  # noqa: E402
import state_paths                                            # noqa: E402


# ------------------------------------------------------------------ do gia
def _ve(w, h, tone=(60, 70, 90), seed=7):
    """Anh co van, tone chi dinh — `tone_mismatch` do do sang va mau trung binh.
    `seed` khac nhau -> hoa van khac nhau: cung seed la CUNG MOT buc anh (LOW-284,
    submit_common.check_same_photo chan hai ma cung anh o hai slide)."""
    im = Image.new("RGB", (w, h), tone)
    d = ImageDraw.Draw(im)
    b = seed
    for x in range(0, w, 29):
        for y in range(0, h, 31):
            b = (b * 1103515245 + 12345) % 2147483648
            d.ellipse([x, y, x + 14, y + 14],
                      fill=tuple(min(255, c + b % 40) for c in tone))
    return im


def _anh(wd, ma, w, h, loai="photo", tone=(60, 70, 90), **k):
    """Mot dong manifest anh, dung cac khoa ma `image_prepare` that su ghi ra."""
    import image_rules_dre as image_rules
    goc = wd / state_paths.ORIGINAL_DIR / f"{ma}.png"
    goc.parent.mkdir(parents=True, exist_ok=True)
    seed = sum(ord(c) * 131 ** i for i, c in enumerate(ma))    # moi ma mot anh rieng (LOW-284)
    _ve(w, h, tone, seed).save(goc)
    san = wd / state_paths.READY_DIR / f"{ma}.png"
    san.parent.mkdir(parents=True, exist_ok=True)
    _ve(min(w, h), min(w, h), tone, seed).save(san)         # ban da cat san
    a = {"id": ma, "original_path": str(goc), "ready_path": str(san), "w": w, "h": h,
         "ratio": round(w / h, 2), "kind": loai, "landscape":w / h >= image_rules.LANDSCAPE_CLEAR,
         "faces": 0, "relevant": True, "description": f"anh thu {ma}", "alt": "", "uses": []}
    a.update(k)
    return a


def _m(wd, anh, **k):
    m = {"images": anh, "draft_id": "tin-thu", "link": "https://vi.du/bai",
         "article_text":"Nvidia mở kho mô hình Nemotron cho mọi nhà phát triển",
         "material": {}, "min_images": 5, "stackable_pairs": None, "cover_suggestions": [],
         "image_role": "dre"}
    m.update(k)
    return m


def _spec(cover, slides, **k):
    d = {"cover": cover, "slides": slides}
    d.update(k)
    return d


def _bia(ma="A1", **k):
    d = {"image": ma, "hook": "Nvidia mở kho mô hình", "category": "MODEL RELEASE"}
    d.update(k)
    return d


def _slide(ma, text="Một câu nội dung cho slide này", **k):
    d = {"image": ma, "text": text}
    d.update(k)
    return d


def _du_slide(anh_ma):
    """Bon slide hop le, hai trong so do co quote — du qua cong so luong."""
    return [_slide(anh_ma[0], quote="Chúng tôi mở kho mô hình", attrib="Jensen Huang"),
            _slide(anh_ma[1], quote="Ai cũng tải được", attrib="Nvidia"),
            _slide(anh_ma[2]), _slide(anh_ma[3])]


def _chay(spec, m, wd):
    import dre_submit
    return dre_submit.resolve_spec(spec, m, Path(wd))


def _co(loi, *manh):
    """Co dong loi nao chua het cac manh chuoi khong."""
    return any(all(x in l for x in manh) for l in loi)


def _du(tmp):
    """Bo do day du: 5 anh doc, spec hop le. Tra ve (spec, m, wd)."""
    wd = Path(tmp)
    anh = [_anh(wd, f"A{i}", 1000, 1250) for i in range(1, 6)]
    return _spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"])), _m(wd, anh), wd


# ------------------------------------------------------------ duong hop le
def test_spec_du_thi_khong_mot_loi_nao():
    """Chot chieu con lai: cong nay bao oan la Dre khong bao gio nop duoc."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        ra, loi, _canh, dung = _chay(*_du(t))
        assert loi == [], loi
        assert ra["cover"]["hook"] == "Nvidia mở kho mô hình"
        assert len(ra["slides"]) == 4
        assert [n for n, _ in dung] == ["bìa", "slide 2", "slide 3", "slide 4", "slide 5"]


def test_giu_nguyen_cac_truong_chu_cua_vai():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["slides"][0].update({"label": "SỐ LIỆU", "subject": "Jensen Huang"})
        ra, loi, _c, _d = _chay(spec, m, wd)
        assert ra["slides"][0]["label"] == "SỐ LIỆU"
        assert ra["slides"][0]["quote"] == "Chúng tôi mở kho mô hình"


def test_thieu_cover_hoac_slides_bao_ro():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        m = _m(wd, [_anh(wd, "A1", 1000, 1250)])
        _ra, loi, _c, _d = _chay(_spec(None, []), m, wd)
        assert _co(loi, "thiếu", "cover") and _co(loi, "thiếu", "slides"), loi


# ------------------------------------------------------------ ma anh
def test_ma_anh_khong_ton_tai_thi_liet_ke_ma_co_that():
    """Bao "khong ton tai" ma khong noi co nhung ma nao thi vai doan tiep."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["slides"][0]["image"] = "A99"
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "slide 2", "A99", "A1"), loi


def test_mot_anh_dung_hai_slide_bi_chan():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["slides"][1]["image"] = spec["slides"][0]["image"]
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "đã dùng ở", "slide 2"), loi


def test_thieu_ca_anh_lan_ghep_thi_bao_ca_hai_duong():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["slides"][0].pop("image")
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "slide 2", "image", "stack"), loi


def test_anh_bi_danh_dau_khong_lien_quan_thi_chan():
    """`relevant: False` la ket luan cua buoc nhin anh — dung no la dang bai
    mot tam anh khong dinh gi toi tin."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, f"A{i}", 1000, 1250) for i in range(1, 6)]
        anh[1]["relevant"] = False
        anh[1]["description"] = "một con mèo trên ghế sofa"
        _ra, loi, _c, _d = _chay(_spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"])),
                                 _m(wd, anh), wd)
        assert _co(loi, "KHÔNG LIÊN QUAN", "A2", "con mèo"), loi


# ------------------------------------------------------------ chart / xep hang
def test_chart_khong_duoc_lam_bia_va_goi_y_bia_khac():
    """Hook de len nua duoi chart la mat nua duoi bang so. Chart NEN PHANG thi lam bia duoc
    (LOW-341: anh 90% be ngang tren chinh mau nen, hook khong de len) — o day chart co nen
    CHUYEN MAU, khong phang."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1200, 900, loai="chart")] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(2, 6)]
        Image.linear_gradient("L").resize((1200, 900)).convert("RGB").save(anh[0]["original_path"])
        _ra, loi, _c, _d = _chay(_spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"])),
                                 _m(wd, anh, cover_suggestions=["A3", "A4"]), wd)
        assert _co(loi, "bìa", "A1", "CHART"), loi
        assert _co(loi, "A3"), "khong goi y bia thay the"


def test_chart_lam_slide_thi_dan_nguyen_full_be_ngang():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250)] + \
              [_anh(wd, "A2", 1200, 900, loai="chart")] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(3, 6)]
        ra, loi, _c, _d = _chay(_spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"])),
                                _m(wd, anh), wd)
        assert loi == [], loi
        assert ra["slides"][0].get("chart") is True, ra["slides"][0]


def test_anh_xep_hang_duoc_lam_bia_con_lam_slide_thi_la_chart():
    """Anh xep hang la chart nhung DUOC lam bia — bang o nua tren, hook nua duoi."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        xh = _anh(wd, "XH", 1200, 900, loai="chart", ranking={"site": "LMArena"})
        anh = [xh] + [_anh(wd, f"A{i}", 1000, 1250) for i in range(2, 6)]
        m = _m(wd, anh, is_ranking_story=True, ranking={"kind": "table"})
        ra, loi, _c, _d = _chay(_spec(_bia("XH"), _du_slide(["A2", "A3", "A4", "A5"])), m, wd)
        assert loi == [], loi
        assert "chart" not in ra["cover"], "bia xep hang khong duoc dan kieu chart"


def test_tin_xep_hang_ma_bia_khong_phai_bang_thi_chan():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        xh = _anh(wd, "XH", 1200, 900, loai="chart", ranking={"site": "LMArena"})
        anh = [xh] + [_anh(wd, f"A{i}", 1000, 1250) for i in range(2, 6)]
        m = _m(wd, anh, is_ranking_story=True, ranking={"kind": "table", "site": "LMArena",
                                                     "board": "text", "model": "GPT"})
        _ra, loi, _c, _d = _chay(_spec(_bia("A2"), _du_slide(["A3", "A4", "A5", "XH"])), m, wd)
        assert _co(loi, "bìa", "TIN XẾP HẠNG"), loi


def test_khong_co_anh_xep_hang_that_thi_KHONG_ep_bia_dung_XH():
    """Hoi quy 06/09/2026 chieu: cong nay tung chan ca khi engine khong chup
    duoc bang, tuc bao vai dung ma "XH" trong khi ma do khong ton tai — vai sua
    kieu gi cung sai va khong bao gio nop duoc."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, f"A{i}", 1000, 1250) for i in range(1, 6)]
        m = _m(wd, anh, is_ranking_story=True, ranking=None)
        _ra, loi, _c, _d = _chay(_spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"])), m, wd)
        assert loi == [], loi


# ------------------------------------------------------------ anh ngang
def test_anh_ngang_di_mot_minh_thi_bao_dung_hai_duong_ra():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250)] + [_anh(wd, "A2", 1920, 1080)] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(3, 6)]
        _ra, loi, _c, _d = _chay(_spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"])),
                                 _m(wd, anh, stackable_pairs=["A2", "A3"]), wd)
        assert _co(loi, "slide 2", "NGANG", "stack", "landscape_crop"), loi


def test_cat_ngang_anh_qua_thap_thi_chan():
    """Cat doc 4:5 roi phong len 1080 se nhoe."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250)] + [_anh(wd, "A2", 1600, 600)] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(3, 6)]
        spec = _spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"]))
        spec["slides"][0]["landscape_crop"] = True
        _ra, loi, _c, _d = _chay(spec, _m(wd, anh), wd)
        assert _co(loi, "slide 2", "600px"), loi


def test_cat_ngang_hop_le_thi_ra_tep_da_cat():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250)] + [_anh(wd, "A2", 1920, 1080)] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(3, 6)]
        spec = _spec(_bia("A1"), _du_slide(["A2", "A3", "A4", "A5"]))
        spec["slides"][0].update({"landscape_crop": True, "crop_center": [0.5, 0.4]})
        ra, loi, _c, _d = _chay(spec, _m(wd, anh), wd)
        assert loi == [], loi
        assert Path(ra["slides"][0]["image"]).exists()
        assert ra["slides"][0]["image"].endswith("A2" + state_paths.LANDSCAPE_SUFFIX)


# ------------------------------------------------------------ ghep doc
def test_ghep_phai_dung_hai_ma():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["slides"][0] = {"stack": ["A2"], "text": "x"}
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "slide 2", "đúng 2 mã ảnh"), loi


def test_ghep_ra_ti_le_ngoai_dai_thi_chan():
    """Hai anh cao ghep doc ra tam anh rat cao — ngoai dai 4:5..1:1."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250)] + \
              [_anh(wd, "A2", 800, 1600), _anh(wd, "A3", 800, 1600)] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(4, 7)]
        spec = _spec(_bia("A1"), [{"stack": ["A2", "A3"], "text": "x", "quote": "Một câu", "attrib": "X"},
                                  _slide("A4", quote="Câu hai", attrib="Y"),
                                  _slide("A5"), _slide("A6")])
        _ra, loi, _c, _d = _chay(spec, _m(wd, anh, stackable_pairs=["A4", "A5"]), wd)
        assert _co(loi, "slide 2", "ngoài dải ghép"), loi


def test_ghep_hai_anh_3_2_qua_cong_kem_canh_bao_low178():
    """LOW-178 (16/09/2026, tin Samsung Taylor): bốn ảnh sạch đều 3:2, ghép nhau
    ra 0.75 — trước đây "ngoài dải 4:5..1:1", Dre block. Nay qua cổng, chỉ CẢNH
    BÁO mép nào bị cắt (lệch tỉ lệ = lỗi nhỏ, Ông Chủ 12/09/2026)."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250)] + \
              [_anh(wd, "A2", 1500, 1000), _anh(wd, "A3", 1500, 1000)] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(4, 7)]
        spec = _spec(_bia("A1"), [{"stack": ["A2", "A3"], "text": "x", "quote": "Một câu", "attrib": "X"},
                                  _slide("A4", quote="Câu hai", attrib="Y"),
                                  _slide("A5"), _slide("A6")])
        ra, loi, canh, _d = _chay(spec, _m(wd, anh, stackable_pairs=["A2", "A3"]), wd)
        assert loi == [], loi
        assert ra["slides"][0]["images"] == [anh[1]["original_path"], anh[2]["original_path"]]
        assert _co(canh, "slide 2", "0.75", "mép"), canh


def test_carousel_gate_nhan_anh_ghep_cao_hon_4_5_low178():
    """Lưới thứ hai: cổng ảnh của `carousel.py` chạy lại `check_aspect_ratio` trên
    tấm `.ghep.png` — phải dùng sàn STACK_FLOOR cho mục có "images", không thì
    dre_submit cho qua rồi carousel lại chặn (đúng kiểu kẹt hai đầu 06/09)."""
    import carousel
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "x.ghep.png"
        # Nhieu hat ngau nhien de khong bi do_chart nhan nham la chart (anh phang, it mau).
        Image.merge("RGB", [Image.effect_noise((1080, 1440), 60) for _ in range(3)]).save(p)   # 0.75
        loi, _canh = carousel._gate_image([("slide 2", str(p), {"images": ["a", "b"], "image": str(p)})])
        assert not [x for x in loi if "ti le" in x], loi
        loi, _canh = carousel._gate_image([("slide 3", str(p), {"image": str(p)})])
        assert [x for x in loi if "ti le" in x], "anh DON 0.75 van phai qua dai 4:5..1:1"


# ------------------------------------------------------------ nhan_vat (LOW-178)
def _anh_mat(wd, ma, **k):
    return _anh(wd, ma, 1000, 1250, faces=1, **k)


def test_nhan_vat_theo_chu_thich_anh_low178():
    """Bài về Nvidia không gõ "Jensen Huang", nhưng caption Wikimedia của chính tấm
    ảnh có tên — khai đúng tên đó không phải bịa (LOW-178, 16/09/2026)."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        m["images"][1] = _anh_mat(wd, "A2", alt="Jensen Huang speaking at GTC 2026")
        spec["slides"][0]["subject"] = "Jensen Huang"
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert loi == [], loi


def test_nhan_vat_theo_nhan_thuong_hieu_low178():
    """Vòng thương hiệu gắn `brand_match.person` (Wikidata founder/CEO) — cùng bằng
    chứng `role.face_no_clear_ai` đã dùng để ĐẾM tấm này là dùng được."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        m["images"][1] = _anh_mat(wd, "A2", brand_match={"person": "C.C. Wei", "kind": "chan_dung"})
        spec["slides"][0]["subject"] = "C.C. Wei"
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert loi == [], loi


def test_nhan_vat_khong_co_o_bai_lan_chu_thich_van_chan():
    """Sự cố gốc 05/09 (ảnh quan chức G20 khai "Hock Tan") vẫn bị chặn: caption ảnh
    không có tên, bài cũng không."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        m["images"][1] = _anh_mat(wd, "A2", alt="Officials pose for a group photo at the summit")
        spec["slides"][0]["subject"] = "Hock Tan"
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "slide 2", "Hock Tan", "không xuất hiện"), loi


def test_chu_thich_anh_khac_khong_bao_lanh_low178():
    """Chỉ tấm ĐANG khai mới làm bằng chứng — tên nằm ở caption của tấm khác
    trong manifest không cho tấm mặt lạ này qua."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        m["images"][1] = _anh_mat(wd, "A2", alt="")
        m["images"][2]["alt"] = "Jensen Huang speaking at GTC 2026"
        spec["slides"][0]["subject"] = "Jensen Huang"
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "slide 2", "Jensen Huang", "không xuất hiện"), loi


def test_subject_names_bo_headline_uu_tien_vision_low178():
    """Đo thật 16/09/2026 (A18 tin Nvidia/Anthropic): alt là tiêu đề báo Title-Case,
    regex tên riêng đọc ra "Here Following"; brief in ra, Dre khai đúng thế và
    qua cổng với một tên bịa — trong khi vision description nói rõ "CEO Jensen Huang"."""
    import image_rules_dre as dre
    a18 = {"alt": "Nvidia CEO Says AGI is Here Following GPT-6 Astra Launch",
           "description":"Anh CEO Jensen Huang cua Nvidia dang phat bieu, phia sau la logo Nvidia."}
    assert dre.subject_names(a18) == ["Jensen Huang"]
    # caption thuong (khong phai headline) van la bang chung
    assert dre.subject_names({"alt": "Jensen Huang speaking at GTC 2026",
                              "description":"Anh mot nguoi dan ong dang phat bieu"}) == ["Jensen Huang"]
    # tien to "Anh ..." cua description khong dau bi cat
    assert dre.subject_names({"description":"Anh Lisa Su gioi thieu chip"}) == ["Lisa Su"]
    assert dre.subject_names({"alt": "Officials pose for a group photo at the summit",
                              "description":"Anh quan chuc G20"}) == []
    assert dre.subject_names({"brand_match": {"person": "C.C. Wei"}, "alt": ""}) == ["C.C. Wei"]


def test_nhan_vat_bia_tu_headline_van_chan_ten_that_qua_low178():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        m["images"][1] = _anh_mat(wd, "A2", alt="Nvidia CEO Says AGI is Here Following GPT-6 Astra Launch",
                               description="Anh CEO Jensen Huang cua Nvidia dang phat bieu")
        spec["slides"][0]["subject"] = "Here Following"
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "slide 2", "Here Following", "không xuất hiện"), loi
        spec["slides"][0]["subject"] = "Jensen Huang"
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert loi == [], loi


def test_ghep_hai_anh_lech_tone_khong_con_bi_chan():
    """Ông Chủ 13/09/2026: bỏ `kiem_lech_tone`/`image_rules.tone_mismatch` khỏi hệ
    thống, mọi vai — ghép hai ảnh lệch tone hẳn (một tối 15/15/20, một sáng
    235/235/240) không còn bị chặn ở slide ghép."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250)] + \
              [_anh(wd, "A2", 1600, 900, tone=(15, 15, 20)),
               _anh(wd, "A3", 1600, 900, tone=(235, 235, 240))] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(4, 7)]
        spec = _spec(_bia("A1"), [{"stack": ["A2", "A3"], "text": "x", "quote": "Một câu", "attrib": "X"},
                                  _slide("A4", quote="Câu hai", attrib="Y"),
                                  _slide("A5"), _slide("A6")])
        _ra, loi, _c, _d = _chay(spec, _m(wd, anh), wd)
        assert not _co(loi, "lệch tone"), loi


def test_ghep_dung_lai_anh_da_dung_o_slide_khac():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, "A1", 1000, 1250)] + \
              [_anh(wd, "A2", 1600, 900), _anh(wd, "A3", 1600, 900)] + \
              [_anh(wd, f"A{i}", 1000, 1250) for i in range(4, 7)]
        spec = _spec(_bia("A2"), [{"stack": ["A2", "A3"], "text": "x", "quote": "Một câu", "attrib": "X"},
                                  _slide("A4", quote="Câu hai", attrib="Y"),
                                  _slide("A5"), _slide("A6")])
        _ra, loi, _c, _d = _chay(spec, _m(wd, anh), wd)
        assert _co(loi, "đã dùng ở", "bìa"), loi


# ------------------------------------------------------------ cong bien tap
def test_bia_thieu_hook_hoac_category():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["cover"].update({"hook": "  ", "category": ""})
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "bìa", "hook") and _co(loi, "bìa", "category"), loi


def test_slide_thieu_ca_text_lan_quote():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["slides"][3]["text"] = "   "
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "slide 5", "text", "quote"), loi


def test_it_hon_toi_thieu_slide_thi_chan_va_goi_y_chia_tang():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        anh = [_anh(wd, f"A{i}", 1000, 1250) for i in range(1, 6)]
        spec = _spec(_bia("A1"), [_slide("A2", quote="Câu một", attrib="X"),
                                  _slide("A3", quote="Câu hai", attrib="Y")])
        _ra, loi, _c, _d = _chay(spec, _m(wd, anh, min_images=5), wd)
        assert _co(loi, "chỉ 3 slide", "tối thiểu 5"), loi


def test_duoi_hai_quote_thi_chan():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["slides"][1].pop("quote")
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "chỉ 1 slide quote"), loi


def test_quote_con_nguyen_tieng_anh_thi_chan():
    """card.find_face_mark CO Y bo qua tieng Anh, nen quote chua dich lot thang
    len Telegram neu cong nay khong bat (06/09/2026)."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["slides"][0]["quote"] = "We are opening the model zoo to every developer out there"
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "slide 2"), loi
        assert any("dịch" in l.lower() or "tiếng việt" in l.lower() for l in loi), loi


# ------------------------------------------------------------ nen / tam co
def test_nen_khong_hop_le_thi_liet_ke_lua_chon():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["background_tone"] = "cau vong"
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "background_tone", "cau vong", "dark | light"), loi


def test_nen_hop_le_di_thang_sang_carousel():
    import carousel
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        spec["background_tone"] = list(carousel.BACKGROUND)[0].upper()
        ra, loi, _c, _d = _chay(spec, m, wd)
        assert loi == [], loi
        assert ra["background_tone"] == list(carousel.BACKGROUND)[0]


def test_flagship_cua_manifest_thanh_tam_co():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        m["flagship"] = True
        ra, _l, _c, _d = _chay(spec, m, wd)
        assert ra["tier"] == "flagship"
        spec2, m2, wd2 = _du(t)
        assert "tier" not in _chay(spec2, m2, wd2)[0]


# ------------------------------------------------------------ khong dung lai anh
def test_anh_da_gui_o_bai_khac_thi_chan():
    """Ong Chu chot 06/09: bang tỉ số giải golf lên hai thẻ của hai tin khác
    nhau trong cùng một ngày."""
    import image_rules_dre as image_rules
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        image_rules.record_used(m["images"][1]["original_path"], "tin-khac", "dre",
                             "https://vi.du/mot-tin-khac-han")
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert _co(loi, "slide 2", "TRUNG anh da dung", "tin-khac"), loi


def test_lam_lai_chinh_bai_nay_thi_khong_bi_coi_la_dung_lai():
    """Lam lai mot bai thi duoc giu anh — chan la vai khong bao gio lam lai duoc."""
    import image_rules_dre as image_rules
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        image_rules.record_used(m["images"][1]["original_path"], m["draft_id"], "dre", m["link"])
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert loi == [], loi


def test_cung_tin_nhung_vai_khac_thi_khong_chan():
    """Mot tin giao ca Dre lan Ethan ra hai draft_id nhung dung CHUNG bo anh
    engine tai ve; chan la vai nop sau khong con anh nao (do 06/09/2026)."""
    import image_rules_dre as image_rules
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        image_rules.record_used(m["images"][1]["original_path"], "tin-thu-ethan", "ethan", m["link"])
        _ra, loi, _c, _d = _chay(spec, m, wd)
        assert loi == [], loi


def test_lam_lai_slide_cu_the_van_ra_dung_anh_cu_thi_chan():
    """Ong Chu 13/09/2026 (Anthropic/Nvidia IPO): bam Lam lai chi ro slide, ban
    moi van la CUNG MOT anh (chi doi ma A3 -> A5, cung file). approve_post da chup
    dHash cua anh bi che vao img.json["forbidden_slide_images"]["3"] luc bam nut; cong
    o day phai chan slide 3 du ma anh doi ten."""
    import shutil
    import dre_submit
    import image_rules_dre as image_rules
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        with tempfile.TemporaryDirectory() as dr:
            dre_submit.DRAFTS = Path(dr)
            try:
                h = image_rules.dhash(Image.open(m["images"][1]["original_path"]).convert("RGB"))
                (Path(dr) / f"{m['draft_id']}.img.json").write_text(
                    json.dumps({"forbidden_slide_images":{"3": [format(h, "x")]}}),
                    encoding="utf-8")
                # A3 la anh o slide 3; sao chep chinh no thanh "A5" (doi ten
                # ma, GIU NGUYEN noi dung file) roi dat vao slide 3 thay A3.
                a5 = next(a for a in m["images"] if a["id"] == "A5")
                shutil.copyfile(m["images"][1]["original_path"], a5["original_path"])
                spec["slides"][1]["image"] = "A5"
                _ra, loi, _c, _d = _chay(spec, m, wd)
                assert _co(loi, "slide 3", "đã bị Ông Chủ từ chối"), loi
            finally:
                dre_submit.DRAFTS = dre_submit.ROOT / "drafts"


def test_lam_lai_slide_khac_khong_bi_anh_huong():
    """Cam chi ap cho DUNG slide bi neu — cac slide khac trong ban lam lai van
    duoc giu anh cu binh thuong, khong bi chan oan."""
    import dre_submit
    import image_rules_dre as image_rules
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _du(t)
        with tempfile.TemporaryDirectory() as dr:
            dre_submit.DRAFTS = Path(dr)
            try:
                h = image_rules.dhash(Image.open(m["images"][1]["original_path"]).convert("RGB"))
                (Path(dr) / f"{m['draft_id']}.img.json").write_text(
                    json.dumps({"forbidden_slide_images":{"6": [format(h, "x")]}}),
                    encoding="utf-8")
                _ra, loi, _c, _d = _chay(spec, m, wd)
                assert loi == [], loi
            finally:
                dre_submit.DRAFTS = dre_submit.ROOT / "drafts"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
