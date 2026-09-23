#!/usr/bin/env python3
"""LOW-267 (19/09/2026) — carousel dcgr "Nhà nghiên cứu dùng Claude tấn công OpenAI":
slide 4 chồng HAI tấm Sam Altman, không có Dario Amodei. Ông Chủ: *"nếu đã dùng
founder thì ảnh trên là founder OpenAI thì ảnh dưới phải là founder Anthropic"*.

Hai gốc, đo trên manifest + log thật của draft:

  1. Engine ĐÃ tải 3 chân dung Dario Amodei có tên (Wikidata, `brand_match.person`)
     nhưng `_round_brand` bỏ sạch ("+0 anh"): trần `MAX_IMAGE + 4` đếm `len(anh)`,
     tính cả 7/12 ảnh đã bị loại vì không liên quan (phòng lab, toà nhà vô danh).
  2. `check_repeated_subject_portrait` (LOW-265) chạy trên tệp ĐÃ GHÉP — hai chân
     dung ghép lại thành một tệp 2 mặt, mà cổng chỉ xét tệp đúng 1 mặt. Mô phỏng
     trên máy chủ với 2 ảnh Sam thật: không chặn.

Chạy:  venv/bin/python tests/test_low267_stack_portrait_balance.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image                                        # noqa: E402

import image_rules_dre as dre                                 # noqa: E402
import state_paths                                            # noqa: E402
from prepare import fallback_rounds                           # noqa: E402


def _noise(p, w=1200, h=675, seed=1):
    Image.effect_noise((w, h), 40 + seed).convert("RGB").save(p)


# ------------------------------------------------ 1. _round_brand: tran dem anh con giu
def test_round_brand_anh_da_loai_khong_chiem_tran():
    """12 ảnh sẵn có, 7 ảnh đã bị loại: vòng thương hiệu vẫn phải thêm được 3 chân
    dung Dario (trước LOW-267: "+0 anh" vì `len(anh)` đã = MAX_IMAGE + 4)."""
    giu = [{"id": f"A{i}", "url": f"https://x/giu{i}.jpg", "uses": ["body"], "relevant": True}
           for i in range(1, 6)]
    loai = [{"id": f"A{i}", "url": f"https://x/loai{i}.jpg", "uses": [], "relevant": False}
            for i in range(6, 13)]
    anh = giu + loai
    assert len(anh) == fallback_rounds.MAX_IMAGE + 4

    dario = [{"image_url": f"https://commons/dario{i}.jpg", "alt": "", "og": False,
              "source": "brand", "w": 1920, "h": 1280, "page_url": "https://commons/x",
              "score": 24, "brand_match": {"company": "Anthropic", "key": "anthropic",
                                           "kind": "person", "person": "Dario Amodei"}}
             for i in range(3)]

    def tai_va_loc_gia(cands, wd, da_giu=()):
        wd.mkdir(parents=True, exist_ok=True)
        ra = []
        for i, c in enumerate(cands):
            c = dict(c, url=c["image_url"])
            p = wd / f"tai_{i}.png"
            p.write_bytes(b"\x89PNG\r\n")
            c["original_path"] = str(p)
            ra.append(c)
        return ra

    def phan_loai_gia(a, wd, tieu_de):
        a["uses"] = ["body"]
        a["relevant"] = True
        return a

    with tempfile.TemporaryDirectory() as d, \
         mock.patch("image_brand.vendors_in_story",
                    return_value=[{"company": "Anthropic", "key": "anthropic"}]), \
         mock.patch("image_brand.confirm_unlisted_vendor", return_value=True), \
         mock.patch("image_brand.vendor_images", return_value=dario), \
         mock.patch("image_brand.model_logo_images", return_value=[]), \
         mock.patch.object(fallback_rounds, "download_and_filter", side_effect=tai_va_loc_gia), \
         mock.patch.object(fallback_rounds, "classify", side_effect=phan_loai_gia):
        (Path(d) / state_paths.ORIGINAL_DIR).mkdir(parents=True)
        ra, dung_duoc, _ = fallback_rounds._round_brand(
            anh, "Researchers used Claude to hack OpenAI", "", Path(d), khong_browser=True)

    them = [a for a in ra if (a.get("brand_match") or {}).get("person") == "Dario Amodei"]
    assert len(them) == 3, f"chan dung Dario bi cat: +{len(them)} (anh da loai van chiem tran)"
    assert len(dung_duoc) == 8, len(dung_duoc)


def test_round_brand_van_dung_o_tran_khi_anh_con_giu_da_du():
    """Tran van con hieu luc: 12 anh DEU con giu thi khong them."""
    anh = [{"id": f"A{i}", "url": f"https://x/{i}.jpg", "uses": ["body"], "relevant": True}
           for i in range(1, fallback_rounds.MAX_IMAGE + 5)]
    cand = [{"image_url": "https://commons/dario.jpg", "alt": "", "og": False, "source": "brand",
             "w": 1920, "h": 1280, "page_url": "https://commons/x", "score": 24,
             "brand_match": {"company": "Anthropic", "key": "anthropic", "kind": "person",
                             "person": "Dario Amodei"}}]

    def tai_va_loc_gia(cands, wd, da_giu=()):
        wd.mkdir(parents=True, exist_ok=True)
        p = wd / "tai.png"
        p.write_bytes(b"\x89PNG\r\n")
        return [dict(cands[0], url=cands[0]["image_url"], original_path=str(p))]

    with tempfile.TemporaryDirectory() as d, \
         mock.patch("image_brand.vendors_in_story",
                    return_value=[{"company": "Anthropic", "key": "anthropic"}]), \
         mock.patch("image_brand.confirm_unlisted_vendor", return_value=True), \
         mock.patch("image_brand.vendor_images", return_value=cand), \
         mock.patch.object(fallback_rounds, "download_and_filter", side_effect=tai_va_loc_gia), \
         mock.patch.object(fallback_rounds, "classify", side_effect=lambda a, *_: a):
        (Path(d) / state_paths.ORIGINAL_DIR).mkdir(parents=True)
        ra, _, _ = fallback_rounds._round_brand(anh, "OpenAI news", "", Path(d), khong_browser=True)
    assert len(ra) == fallback_rounds.MAX_IMAGE + 4, len(ra)


# --------------------------------------- 2. check_stack_portrait_subjects (Dre)
def _voi_mat(so_mat):
    cu = dre.count_faces
    dre.count_faces = lambda p: so_mat[str(p)]
    return cu


def test_ghep_hai_chan_dung_mot_ten_bi_chan():
    """Đúng ca draft: stack Sam + Sam, khai "subject": "Sam Altman"."""
    with tempfile.TemporaryDirectory() as t:
        a, b = Path(t) / "a.png", Path(t) / "b.png"
        cu = _voi_mat({str(a): 1, str(b): 1})
        try:
            loi, _ = dre.check_stack_portrait_subjects(
                "slide 4", [str(a), str(b)], {"subject": "Sam Altman"}, {})
        finally:
            dre.count_faces = cu
    assert loi and "CHAN DUNG" in loi[0] and "Dario Amodei" in loi[0], loi


def test_ghep_hai_chan_dung_hai_ten_qua():
    with tempfile.TemporaryDirectory() as t:
        a, b = Path(t) / "a.png", Path(t) / "b.png"
        cu = _voi_mat({str(a): 1, str(b): 1})
        try:
            for nv in ("Sam Altman, Dario Amodei", "Sam Altman và Dario Amodei",
                       "Sam Altman / Dario Amodei"):
                da = {}
                loi, _ = dre.check_stack_portrait_subjects(
                    "slide 4", [str(a), str(b)], {"subject": nv}, da)
                assert loi == [], (nv, loi)
                assert set(da) == {"sam altman", "dario amodei"}, da
        finally:
            dre.count_faces = cu


def test_ghep_hai_lan_cung_mot_ten_bi_chan():
    with tempfile.TemporaryDirectory() as t:
        a, b = Path(t) / "a.png", Path(t) / "b.png"
        cu = _voi_mat({str(a): 1, str(b): 1})
        try:
            loi, _ = dre.check_stack_portrait_subjects(
                "slide 4", [str(a), str(b)], {"subject": "Sam Altman, sam altman"}, {})
        finally:
            dre.count_faces = cu
    assert loi, "khai trung ten hai lan van la mot nguoi"


def test_ghep_chan_dung_voi_logo_toa_nha_khong_chan():
    """Một chân dung + một ảnh không người (logo/trụ sở) — không phải hai chân dung."""
    with tempfile.TemporaryDirectory() as t:
        a, b = Path(t) / "a.png", Path(t) / "b.png"
        cu = _voi_mat({str(a): 1, str(b): 0})
        try:
            loi, _ = dre.check_stack_portrait_subjects(
                "slide 4", [str(a), str(b)], {"subject": "Sam Altman"}, {})
        finally:
            dre.count_faces = cu
    assert loi == [], loi


def test_ghep_roi_slide_khac_lap_lai_nguoi_do_bi_chan():
    """Tên đã dùng trong slide ghép cũng tính cho cổng lặp chủ thể LOW-265."""
    with tempfile.TemporaryDirectory() as t:
        a, b, c = Path(t) / "a.png", Path(t) / "b.png", Path(t) / "c.png"
        cu = _voi_mat({str(a): 1, str(b): 1, str(c): 1})
        try:
            da = {}
            loi1, _ = dre.check_stack_portrait_subjects(
                "slide 4", [str(a), str(b)], {"subject": "Sam Altman, Dario Amodei"}, da)
            loi2, _ = dre.check_repeated_subject_portrait(
                "slide 6", str(c), {"subject": "Dario Amodei"}, da)
        finally:
            dre.count_faces = cu
    assert loi1 == [], loi1
    assert loi2 and "slide 4" in loi2[0], loi2


def test_khong_kiem_duoc_mat_thi_khong_chan():
    with tempfile.TemporaryDirectory() as t:
        a, b = Path(t) / "a.png", Path(t) / "b.png"
        cu = _voi_mat({str(a): None, str(b): 1})
        try:
            loi, _ = dre.check_stack_portrait_subjects(
                "slide 4", [str(a), str(b)], {"subject": "Sam Altman"}, {})
        finally:
            dre.count_faces = cu
    assert loi == [], loi


# ------------------------------------------ 3. noi day that trong carousel._gate_image
def test_gate_image_carousel_chan_slide_ghep_hai_sam():
    """Qua đúng đường carousel: `_stack_if_can` ghép trước, tệp ghép 2 mặt —
    LOW-265 bỏ qua, cổng LOW-267 phải bắt."""
    import carousel
    with tempfile.TemporaryDirectory() as t:
        a, b = Path(t) / "a.png", Path(t) / "b.png"
        _noise(a, seed=1)
        _noise(b, seed=2)
        for nv, phai_chan in (("Sam Altman", True), ("Sam Altman, Dario Amodei", False)):
            s = {"images": [str(a), str(b)], "subject": nv, "quote": "x"}
            carousel._stack_if_can(s, "slide 4", f"{t}/s4")
            so = {str(a): 1, str(b): 1, s["image"]: 2}
            cu = _voi_mat(so)
            try:
                loi, _ = carousel._gate_image([("slide 4", s["image"], s)])
            finally:
                dre.count_faces = cu
            bi_chan = any("anh CHAN DUNG" in e for e in loi)
            assert bi_chan == phai_chan, (nv, loi)


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
