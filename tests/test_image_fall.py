#!/usr/bin/env python3
"""LOW-47: ảnh RỐI không được ưu tiên, buộc dùng thì nền chữ đậm hơn (LOW-330: vẫn là overlay).

Ông Chủ 13/09/2026: *"không ưu tiên sử dụng tất cả những ảnh nhìn rối, trong
trường hợp buộc phải dùng, thì lớp nền của text phải làm cho nghiêm chỉnh, đừng
nham nhở"*. Bộ Anthropic/Nvidia IPO có ba ảnh rối lọt qua cổng LIEN_QUAN: splash
"Claude" còn "loading chart...", đồ hoạ "Nvidia Weighs $10B..." in chìm sau câu
quote, tiêu đề báo Nga RBC.

Bốn phần, mỗi phần có ví dụ ĐÚNG-PHẢI-QUA đi kèm SAI-PHẢI-CHẶN:
  1. vision hỏi thêm dòng CLUTTERED, trả qua `ket_qua` mà không đổi số phần tử tuple;
  2. `classify`: ảnh rối không làm bìa, có ghi chú đầu dòng;
  3. `submit_common.check_image_fall`: chỉ chặn khi CÒN ảnh sạch thật sự thay được;
  4. nền chữ của ảnh rối ở carousel (bìa) và thẻ Ethan: đậm hơn ảnh sạch nhưng CHỈ overlay
     — không bao giờ là mảng màu đặc (LOW-330, Ông Chủ 20/09/2026).

Chạy:  venv/bin/python tests/test_image_fall.py
"""
import json
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw  # noqa: E402

import prepare.vision as vision  # noqa: E402
import manifest_values  # noqa: E402
import image_rules_ethan  # noqa: E402
from tam import so_tam  # noqa: E402


class _Resp:
    def __init__(self, txt: str):
        self._b = json.dumps({"choices": [{"message": {"content": txt}}]}).encode()

    def read(self):
        return self._b


def _image_temp(tmp, ten="a.png", w=1000, h=1250, tone=(30, 30, 40), seed=3):
    im = Image.new("RGB", (w, h), tone)
    d = ImageDraw.Draw(im)
    b = seed
    for x in range(0, w, 37):
        for y in range(0, h, 41):
            b = (b * 1103515245 + 12345) % 2147483648
            d.rectangle([x, y, x + 10 + b % 25, y + 10 + (b // 9) % 25],
                        fill=tuple(min(255, c + b % 180) for c in tone))
    p = Path(tmp) / ten
    im.save(p)
    return p


def _ask_vision(tra_loi, **k):
    """Goi description_image voi router gia; tra (ket qua, ket_qua dict, cau hoi da gui)."""
    gui = {}

    def _goi(req, _ngu=None):
        gui["hoi"] = json.loads(req.data)["messages"][0]["content"][0]["text"]
        return _Resp(tra_loi)

    kq = {}
    with tempfile.TemporaryDirectory() as t, \
            mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}), \
            mock.patch.object(vision, "_call_router", side_effect=_goi):
        p = _image_temp(t)
        ra = vision.description_image(str(p), "Nvidia rót 10 tỷ USD vào IPO Anthropic", ket_qua=kq, **k)
    return ra, kq, gui.get("hoi", "")


# ---------------------------------------------------------------- 1. vision
def test_vision_ask_extra_line_fall_and_read_out():
    ra, kq, hoi = _ask_vision("MO_TA: đồ hoạ tin tức nhiều chữ.\nLIEN_QUAN: co\nCLUTTERED: co")
    assert "DUNG 7 dong" in hoi and "CLUTTERED:" in hoi and "TU_KHOA:" in hoi and "CHU_THE:" in hoi, hoi
    assert ra == ("đồ hoạ tin tức nhiều chữ.", True)       # tuple van 2 phan tu
    assert kq["cluttered"] is True


def test_vision_image_clean_is_false():
    _ra, kq, _hoi = _ask_vision("MO_TA: biển hiệu trụ sở Nvidia.\nLIEN_QUAN: có\nCLUTTERED: không")
    assert kq["cluttered"] is False


def test_vision_read_out_enough_keyword():
    _ra, kq, _hoi = _ask_vision("MO_TA: đồ hoạ Nvidia Anthropic $10B IPO.\nLIEN_QUAN: co\n"
                                "CLUTTERED: co\nTỪ_KHOÁ: có")
    assert kq["cluttered"] is True and kq["has_keywords"] is True, kq


def test_vision_no_return_line_fall_then_none_no_guess():
    _ra, kq, _hoi = _ask_vision("MO_TA: ảnh.\nLIEN_QUAN: co")
    assert kq["cluttered"] is None and kq["has_keywords"] is None


def test_vision_ask_extra_of_bob_still_three_part_from():
    ra, kq, hoi = _ask_vision("MO_TA: ảnh.\nLIEN_QUAN: co\nCLUTTERED: khong\nMOOD: vui",
                              hoi_them="tâm trạng ảnh", nhan_them="MOOD")
    assert "DUNG 8 dong" in hoi, hoi
    assert ra == ("ảnh.", True, "vui")
    assert kq["cluttered"] is False


# ---------------------------------------------------------------- 2. classify
def test_classify_image_fall_no_make_cover_and_notes_mark_line():
    def _gia(path, tieu_de, hang="", **k):
        k["ket_qua"]["cluttered"] = True
        return ("đồ hoạ nhiều chữ", True)

    with tempfile.TemporaryDirectory() as t:
        p = _image_temp(t, tone=(20, 20, 25))                  # toi, doc: binh thuong duoc goi y bia
        a = {"id": "A1", "original_path": str(p)}
        with mock.patch.object(vision, "description_image", side_effect=_gia), \
                mock.patch.object(image_rules_ethan, "count_faces", return_value=0):
            vision.classify(a, Path(t), "Tin gì đó")
    assert a["cluttered"] is True
    assert not any(manifest_values.use_label(d).startswith("bìa") for d in a["uses"]), a["uses"]
    assert a["uses"], "anh roi van dung duoc lam than khi het anh sach"
    assert a["notes"][0].startswith("⚠️ ẢNH RỐI"), a["notes"]


# ---------------------------------------------------------------- 3. check_image_fall
def _item(tmp, ma, seed, **k):
    a = {"id": ma, "original_path": str(_image_temp(tmp, f"{ma}.png", seed=seed)), "uses": ["body"],
         "relevant": True, "cluttered": False, "kind": "photo", "faces": 0, "landscape": False, "h": 1250}
    a.update(k)
    return a


def test_remaining_image_clean_not_yet_use_then_block_image_fall():
    import submit_common as nc
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh = {"A1": _item(t, "A1", 1, cluttered=True), "A2": _item(t, "A2", 2)}
        loi = nc.check_image_fall(anh, {"A1": "slide 5"}, {"draft_id": "tin", "link": "https://x/y", "image_role": "ethan"})
    assert loi and "slide 5" in loi[0] and "A2" in loi[0], loi


def test_image_fallback_enough_keyword_ok_domain_gate():
    """Ông Chủ chọn chính đồ hoạ rối "Nvidia Weighs $10B" làm hero vì đủ từ khoá."""
    import submit_common as nc
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh = {"A1": _item(t, "A1", 1, cluttered=True, has_keywords=True), "A2": _item(t, "A2", 2)}
        loi = nc.check_image_fall(anh, {"A1": "bìa"}, {"draft_id": "tin", "link": "https://x/y", "image_role": "ethan"})
    assert loi == [], loi


def test_classify_fallback_enough_keyword_keep_cover_and_notes_star():
    def _gia(path, tieu_de, hang="", **k):
        k["ket_qua"].update({"cluttered": True, "has_keywords": True})
        return ("đồ hoạ đủ từ khoá", True)

    with tempfile.TemporaryDirectory() as t:
        p = _image_temp(t, tone=(20, 20, 25))
        a = {"id": "A1", "original_path": str(p)}
        with mock.patch.object(vision, "description_image", side_effect=_gia), \
                mock.patch.object(image_rules_ethan, "count_faces", return_value=0):
            vision.classify(a, Path(t), "Tin gì đó")
    assert a["has_keywords"] is True
    assert a["notes"][0].startswith("⭐"), a["notes"]
    assert not a["notes"][0].startswith("⚠️")


def test_dre_submit_graphic_fall_chart_make_cover_ok():
    import test_spec_dre as ts
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = ts._du(t)
        m["images"][0].update({"kind": "chart", "cluttered": True, "has_keywords": True})      # A1 la bia
        # LOW-341: chart NEN PHANG lam bia duoc (anh tren chu, phan lan hook phu mau nen) — o day
        # nen CHUYEN MAU de van canh luat chart thuong khong lam bia.
        from PIL import Image
        Image.linear_gradient("L").resize((1000, 1250)).convert("RGB").save(m["images"][0]["original_path"])
        ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert not ts._co(loi, "bìa", "CHART"), loi
        assert ra["cover"].get("cluttered") is True and ra["cover"]["image"] == m["images"][0]["original_path"]
        m["images"][0]["cluttered"] = False                                                 # chart that
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert ts._co(loi, "bìa", "CHART"), loi


def test_all_done_image_clean_then_ok_use_image_fall():
    import submit_common as nc
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh = {"A1": _item(t, "A1", 1, cluttered=True), "A2": _item(t, "A2", 2)}
        loi = nc.check_image_fall(anh, {"A1": "slide 5", "A2": "slide 6"},
                              {"draft_id": "tin", "link": "https://x/y", "image_role": "ethan"})
    assert loi == [], loi


def test_no_static_is_clean_if_no_card_use_alone():
    """Chặn oan là vai kẹt vòng: ứng viên phải thật sự thay được, không cần khai thêm."""
    import submit_common as nc
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh = {"A1": _item(t, "A1", 1, cluttered=True),
               "A2": _item(t, "A2", 2, cluttered=None),                       # chua ai noi la sach
               "A3": _item(t, "A3", 3, faces=1),                          # mat nguoi
               "A4": _item(t, "A4", 4, kind="chart"),
               "A5": _item(t, "A5", 5, landscape=True, h=600, landscape_crop_ok=True),   # qua thap
               "A6": _item(t, "A6", 6, landscape=True, h=900, landscape_crop_ok=False),  # co chu
               "A7": _item(t, "A7", 7, relevant=False),
               "A8": _item(t, "A8", 8, uses=[])}
        loi = nc.check_image_fall(anh, {"A1": "slide 2"}, {"draft_id": "tin", "link": "https://x/y", "image_role": "ethan"})
    assert loi == [], loi


def test_image_landscape_crop_read_ok_is_image_clean_see_ok():
    import submit_common as nc
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh = {"A1": _item(t, "A1", 1, cluttered=True),
               "A2": _item(t, "A2", 2, landscape=True, h=1000, landscape_crop_ok=True)}
        loi = nc.check_image_fall(anh, {"A1": "slide 2"}, {"draft_id": "tin", "link": "https://x/y", "image_role": "ethan"})
    assert loi and "A2" in loi[0], loi


def test_image_clean_already_live_article_other_no_static():
    import submit_common as nc
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh = {"A1": _item(t, "A1", 1, cluttered=True), "A2": _item(t, "A2", 2)}
        image_rules_ethan.record_used(anh["A2"]["original_path"], "tin-khac", "dre", "https://x/khac")
        loi = nc.check_image_fall(anh, {"A1": "slide 2"}, {"draft_id": "tin", "link": "https://x/y", "image_role": "ethan"})
    assert loi == [], loi


def test_dre_submit_near_fall_wait_slide_and_block_when_remaining_image_clean():
    import test_spec_dre as ts
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        spec, m, wd = ts._du(t)
        m["images"][1]["cluttered"] = True                              # A2 o slide 2
        ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert loi == [], loi                                  # khong co anh sach nao thay
        assert ra["slides"][0].get("cluttered") is True
        assert not ra["slides"][1].get("cluttered")
        m["images"].append(ts._anh(wd, "A6", 1000, 1250, uses=["body"], cluttered=False))
        _ra, loi, _c, _d = ts._chay(spec, m, wd)
        assert ts._co(loi, "slide 2", "RỐI", "A6"), loi


# -------------------------------------------- 4. nen chu cua anh CLUTTERED (chi overlay)
def _canvas_region(W, H, vung, nen=(40, 40, 40)):
    """Canvas co cac DAI ngang `vung` = [(y0, y1, kieu)]:
    "chu" = soc manh day dac (nhu chu in san), "anh" = soc thua tuong phan
    vua (nhu chi tiet anh chup); ngoai cac dai la mau phang (khoang lang)."""
    im = Image.new("RGBA", (W, H), (*nen, 255))
    d = ImageDraw.Draw(im)
    for y0, y1, kieu in vung:
        if kieu == "chu":
            # net 4px cach 4px, trang tren toi: sau khi thu nho 4 lan van con
            # xen ke sang/toi tung diem — nhu chu in san that (A9: 25-47)
            for x in range(0, W, 8):
                d.rectangle([x, y0, x + 3, y1], fill=(250, 250, 250, 255))
        else:
            for x in range(0, W, 40):
                d.rectangle([x, y0, x + 19, y1], fill=(110, 110, 110, 255))
    return im


def _is_background(canvas, y, bg):
    return all(canvas.getpixel((x, y))[:3] == tuple(bg) for x in (0, 301, 777, canvas.width - 1))


def _row_far_from_background(canvas, y, bg):
    """Do lech lon nhat giua mot hang va mau nen: 0 = mang mau nen dac."""
    return max(abs(canvas.getpixel((x, y))[c] - bg[c])
               for x in (0, 301, 777, canvas.width - 1) for c in range(3))


def _row_energy(canvas, y):
    """Chi tiet ngang trung binh cua mot hang: chu in san cho so cao, mang mau phang ~0."""
    g = canvas.convert("L")
    return sum(abs(g.getpixel((x + 1, y)) - g.getpixel((x, y))) for x in range(canvas.width - 1)) / canvas.width


def test_carousel_image_fall_secondary_full_text_in_ready_keep_image_side_on():
    """LOW-330: anh CLUTTERED lam BIA (khong truyen overlay_only) truoc day phu MAU NEN DAC tu
    khoang lang xuong day. Nay cung chi la overlay: anh van lo qua o moi hang."""
    import carousel
    carousel.set_background("dark")
    cv = _canvas_region(carousel.W, carousel.H, [(0, 600, "anh"), (700, 980, "chu")])
    truoc = cv.copy()
    carousel._layer_if_can(cv, cv.convert("RGB"), 1030, carousel.H, image_cluttered=True)
    for y in (1035, 1100, carousel.H - 1):
        assert not _is_background(cv, y, carousel.BG), (y, cv.getpixel((0, y)))
        assert _row_far_from_background(cv, y, carousel.BG) >= 8, (y, cv.getpixel((301, y)))
    assert cv.getpixel((3, 300)) == truoc.getpixel((3, 300)), "anh phia tren khong duoc dong"
    # Chu in san ngay tren dong chu cua ta phai diu han di, nhung khong bi xoa bang nen dac.
    assert _row_energy(cv, 960) < _row_energy(truoc, 960) * 0.5, (_row_energy(cv, 960), _row_energy(truoc, 960))


def test_carousel_image_clean_keep_raw_layer_open_old():
    import carousel
    carousel.set_background("dark")
    canvas = Image.new("RGBA", (carousel.W, carousel.H), (10, 10, 10, 255))
    truoc = canvas.copy()
    carousel._layer_if_can(canvas, canvas.convert("RGB"), 1000, carousel.H)
    assert canvas.tobytes() == truoc.tobytes(), "nen toi deu du tuong phan -> khong phu gi"


def test_card_text_bg_overlay_keeps_image_visible_and_damps_printed_text():
    """LOW-330: the Ethan dung anh CLUTTERED truoc day phu NEN DAC tu khoang lang xuong day
    (`_text_bg_strict`). Nay chi overlay: anh con lo qua, chu in san van diu han di."""
    import card
    card.set_brand("dcgr")
    cv = _canvas_region(1200, 1500, [(0, 650, "anh"), (780, 1100, "chu"), (1150, 1490, "chu")])
    truoc = cv.copy()
    card._text_bg_overlay(cv, 1160)
    for y in (1170, 1300, 1499):
        assert not _is_background(cv, y, card.BG), (y, cv.getpixel((0, y)))
    assert cv.getpixel((3, 300)) == truoc.getpixel((3, 300)), "anh phia tren khong duoc dong"
    # Chu in san NAM DUOI khung chu cua ta phai diu han di (khong con lem nhem sau chu moi);
    # chu in san PHIA TREN vung phu thi giu nguyen — LOW-286 cam dai mo cat ngang anh.
    assert _row_energy(cv, 1300) < _row_energy(truoc, 1300) * 0.35, (_row_energy(cv, 1300), _row_energy(truoc, 1300))
    assert _row_energy(cv, 900) == _row_energy(truoc, 900), "chu in san tren vung phu giu nguyen"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
