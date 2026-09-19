#!/usr/bin/env python3
"""LOW-273: chu the chinh phai dat vua khung 4:5; ghep doc chi khi het anh nhu vay.

Ong Chu 19/09/2026: "uu tien tim hinh dat vua 4:5 ratio ma co chu the truoc, neu ko thi
chuyen qua ghep" — roi cung ngay, kem 4 slide bi loai (logo Instinct tren nen trang, mat
Altman duoi khung quote, trang bao Hyperscale nhoe mot dai, ghep SoftBank voi logo tren
nen trang): "ko chap nhan nhung hinh nhu the nay o moi designer. ko phai la tim hinh co
ty le 4:5, ma la tim hinh co main character dat vua trong 4:5".

Chay:  venv/bin/python tests/test_stack_last_resort.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image  # noqa: E402

from tam import so_tam  # noqa: E402
import test_spec_dre as ts  # noqa: E402
import subject_fit  # noqa: E402

FIT = {"subject_box": [0.3, 0.1, 0.7, 0.5], "subject_kind": "product", "empty_share": 0.2}


# ------------------------------------------------------------ subject_fit (ham thuan)
def test_parse_subject_reads_box_kind_empty():
    r = subject_fit.parse_subject("MO_TA: x\nCHU_THE: 0.42,0.36,0.58,0.60 | logo\nTRONG: 0.9")
    assert r == {"subject_box": [0.42, 0.36, 0.58, 0.60], "subject_kind": "logo", "empty_share": 0.9}, r


def test_parse_subject_rejects_pixel_coordinates_and_garbage():
    r = subject_fit.parse_subject("CHU_THE: 120,40,800,600 | person\nTRONG: 35")
    assert r["subject_box"] is None and r["empty_share"] is None and r["subject_kind"] == "person", r
    assert subject_fit.parse_subject("") == {"subject_box": None, "subject_kind": None, "empty_share": None}
    assert subject_fit.parse_subject("CHU_THE: 0.1,0.1,0.5,0.5 | ghe")["subject_kind"] is None   # ma la


def test_crop_window_keeps_subject_above_text_zone():
    # anh ngang 1920x1080, chu the gon o giua-tren
    win = subject_fit.crop_window(1920, 1080, [0.4, 0.1, 0.6, 0.5], 0.3)
    x0, y0, x1, y1 = win
    assert (x1 - x0) / (y1 - y0) == 0.8 or abs((x1 - x0) / (y1 - y0) - 0.8) < 0.01
    assert x0 <= 0.4 * 1920 and x1 >= 0.6 * 1920
    assert 0.5 * 1080 <= y0 + 0.7 * (y1 - y0) + 1


def test_crop_window_none_when_subject_too_wide_or_under_text():
    assert subject_fit.crop_window(1920, 1080, [0.05, 0.1, 0.95, 0.4], 0.3) is None      # qua rong
    # mat o 0.3..0.65 cua anh ngang: khung doc cao het anh, vung quote bat dau 0.55
    assert subject_fit.crop_window(4250, 2832, [0.4, 0.3, 0.55, 0.65], 0.45) is None
    assert subject_fit.crop_window(4250, 2832, [0.4, 0.3, 0.55, 0.65], 0.30) is not None


def test_band_full_width_matches_carousel_placement():
    # bieu do 5148x2640 -> cao 554 trong khung 1350, dat giua 60% tren
    top, bot = subject_fit.band_full_width(5148, 2640, [0.1, 0.02, 0.9, 0.95], 1080, 1350)
    assert bot < 0.55, (top, bot)
    # trang 4:5 noi dung toi 80% -> lan vung chu 30%
    assert subject_fit.band_full_width(1080, 1350, [0.06, 0.03, 0.94, 0.8], 1080, 1350)[1] == 0.8


def test_too_empty_threshold():
    assert subject_fit.too_empty(0.9) and subject_fit.too_empty(0.92)
    assert not subject_fit.too_empty(0.35) and not subject_fit.too_empty(None)


# ------------------------------------------------------------ bo spec Dre
def _bo(wd, **fit):
    """Bia A1 + ghep A2/A3 (hai anh ngang) o slide 2; A4..A5 cac slide con lai;
    A6 la anh co chu the vua khung con roi (chua dung)."""
    fit = {**FIT, **fit}
    anh = [ts._anh(wd, "A1", 1000, 1250, uses=["cover"]),
           ts._anh(wd, "A2", 1600, 1000, uses=["body"]),
           ts._anh(wd, "A3", 1600, 1000, uses=["body"]),
           ts._anh(wd, "A4", 1000, 1250, uses=["body"]),
           ts._anh(wd, "A5", 1000, 1250, uses=["body"]),
           ts._anh(wd, "A6", 1000, 1250, uses=["body"], **fit)]
    for a in anh:
        a.setdefault("cluttered", False)
    slides = [{"stack": ["A2", "A3"], "text": "x", "quote": "Một câu", "attrib": "X"},
              ts._slide("A4", quote="Câu hai", attrib="Y"), ts._slide("A5")]
    return ts._spec(ts._bia("A1"), slides), ts._m(wd, anh, min_images=4), wd


def _blocked(loi):
    return ts._co(loi, "CHỦ THỂ đặt vừa khung 4:5")


def test_con_anh_chu_the_vua_khung_chua_dung_thi_chan_ghep():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t))
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert ts._co(loi, "slide 2", "ghép A2+A3", "A6"), loi


def test_ty_le_4_5_ma_chua_do_chu_the_khong_tinh():
    """Ty le anh khong noi gi (Ong Chu): chua co hop chu the thi khong khang dinh vua."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t))
        m["images"][5].pop("subject_box")
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert not _blocked(loi), loi


def test_anh_4_5_nhung_trong_logo_nho_khong_tinh():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t), empty_share=0.9)
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert not _blocked(loi), loi


def test_anh_ngang_cat_doc_duoc_chu_the_gon_thi_tinh():
    """Khong phai ty le: anh NGANG khong chu, chu the gon o giua -> van la ung vien."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t), subject_box=[0.4, 0.1, 0.6, 0.5])
        m["images"][5].update({"w": 1920, "h": 1080, "ratio": 1.78, "landscape": True,
                               "landscape_crop_ok": True})
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert _blocked(loi), loi


def test_anh_ngang_co_chu_khong_tinh():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t), subject_box=[0.4, 0.1, 0.6, 0.5])
        m["images"][5].update({"w": 1920, "h": 1080, "ratio": 1.78, "landscape": True,
                               "landscape_crop_ok": False})
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert not _blocked(loi), loi


def test_het_anh_vua_khung_thi_cho_ghep():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t))
        spec["slides"].append(ts._slide("A6"))
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert not _blocked(loi), loi


def test_anh_roi_hoac_khong_lien_quan_hoac_mat_nguoi_khong_tinh():
    for k, v in (("cluttered", True), ("relevant", False), ("faces", 1)):
        with tempfile.TemporaryDirectory() as t, so_tam(t):
            spec, m, wd = _bo(Path(t))
            m["images"][5][k] = v
            _ra, loi, _c, _d = ts._chay(spec, m, wd)
            assert not _blocked(loi), (k, loi)


# ------------------------------------------------------------ anh trong: moi designer
def test_dre_anh_trong_bi_chan_o_slide_va_trong_cap_ghep():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t))
        m["images"][4]["empty_share"] = 0.9                   # A5 dung o slide 4
        m["images"][2]["empty_share"] = 0.92                  # A3 trong cap ghep
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert ts._co(loi, "slide 4", "A5", "TRỐNG"), loi
        assert ts._co(loi, "slide 2", "A3", "TRỐNG"), loi


def test_check_empty_image_shared_for_ethan_and_kite_thresholds():
    import submit_common as nc
    import image_rules_ethan
    import image_rules_kite
    a = {"id": "A22", "empty_share": 0.9}
    assert nc.check_empty_image(a, "image", image_rules_ethan.EMPTY_SHARE_MAX)
    assert nc.check_empty_image(a, "slide 3", image_rules_kite.EMPTY_SHARE_MAX)
    assert nc.check_empty_image({"id": "A5", "empty_share": 0.15}, "x", image_rules_kite.EMPTY_SHARE_MAX) == []
    assert nc.check_empty_image({"id": "A5"}, "x", 0.6) == []


def test_ethan_and_kite_submit_call_the_empty_gate():
    """Chot duong day: ca hai nop deu goi cong (Ong Chu: 'o moi designer')."""
    for f in ("ethan_submit.py", "kite_submit.py", "dre_submit.py"):
        src = (ROOT / f).read_text(encoding="utf-8")
        assert "check_empty_image(" in src and "EMPTY_SHARE_MAX" in src, f


# ------------------------------------------------------------ Dre: dat chu the
def test_dre_cat_4_5_quanh_chu_the_thay_ban_cat_giua():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t))
        spec["slides"][2] = ts._slide("A6")
        spec["slides"].append(ts._slide("A5"))
        ra, loi, _c, _d = ts._chay(spec, m, wd)
        p = ra["slides"][2]["image"]
        assert p.endswith("A6.subject.png"), p
        w, h = Image.open(p).size
        assert abs(w / h - 0.8) < 0.01, (w, h)


def test_dre_mat_nguoi_duoi_vung_quote_bi_chan_nhung_slide_text_thi_qua():
    """Altman 19/09: anh ngang, khung doc cao het anh nen khong day mat len duoc — dau
    ket thuc o ~58% cao: quote (vung chu tu 55%) thi mat nam duoi khung chu, slide text
    (vung chu tu 70%) thi van vua."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        wd = Path(t)
        spec, m, wd = _bo(wd)
        a = ts._anh(wd, "A7", 2124, 1416, uses=["body"], faces=1, landscape=True,
                    landscape_crop_ok=True, cluttered=False, subject_kind="person",
                    subject_box=[0.3, 0.25, 0.65, 0.85], empty_share=0.55)
        m["images"].append(a)
        m["article_text"] += ". Jensen Huang phát biểu"
        spec["slides"][1] = ts._slide("A7", quote="Câu hai", attrib="Y", landscape_crop=True,
                                      subject="Jensen Huang")
        faces = [[0.42, 0.30, 0.55, 0.50]]              # dau (mo rong) 0.20..0.58
        with mock.patch("image_rules_dre.face_boxes", return_value=faces):
            _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert ts._co(loi, "slide 3", "khuôn mặt", "A7", "slide quote"), loi
        spec["slides"][1] = ts._slide("A7", landscape_crop=True, subject="Jensen Huang")
        spec["slides"][0] = {"stack": ["A2", "A3"], "text": "x", "quote": "Một câu", "attrib": "X"}
        spec["slides"].append(ts._slide("A4", quote="Câu ba", attrib="Z"))
        with mock.patch("image_rules_dre.face_boxes", return_value=faces):
            ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert not ts._co(loi, "khuôn mặt", "A7"), loi


def test_dre_chart_noi_dung_lan_vung_chu_bi_chan():
    """Hyperscale 19/09: trang bao 1080x1350 dan full, noi dung toi 80% khung."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t))
        m["images"][4].update({"kind": "chart", "subject_box": [0.06, 0.03, 0.94, 0.8],
                               "empty_share": 0.05, "ready_path": None})   # chart dung tep goc
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert ts._co(loi, "slide 4", "A5", "vùng chữ"), loi


def test_dre_chart_gon_nua_tren_thi_qua():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = _bo(Path(t))
        m["images"][4].update({"kind": "chart", "subject_box": [0.06, 0.03, 0.94, 0.55],
                               "empty_share": 0.1, "ready_path": None})
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert not ts._co(loi, "A5", "vùng chữ"), loi


def test_dre_chua_do_chu_the_thi_giu_duong_cu():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = ts._du(t)
        ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert loi == [], loi
        assert not any(s["image"].endswith(".subject.png") for s in ra["slides"])


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
