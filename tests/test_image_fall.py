#!/usr/bin/env python3
"""LOW-47: ảnh RỐI không được ưu tiên, buộc dùng thì nền chữ phải đặc.

Ông Chủ 13/09/2026: *"không ưu tiên sử dụng tất cả những ảnh nhìn rối, trong
trường hợp buộc phải dùng, thì lớp nền của text phải làm cho nghiêm chỉnh, đừng
nham nhở"*. Bộ Anthropic/Nvidia IPO có ba ảnh rối lọt qua cổng LIEN_QUAN: splash
"Claude" còn "loading chart...", đồ hoạ "Nvidia Weighs $10B..." in chìm sau câu
quote, tiêu đề báo Nga RBC.

Bốn phần, mỗi phần có ví dụ ĐÚNG-PHẢI-QUA đi kèm SAI-PHẢI-CHẶN:
  1. vision hỏi thêm dòng ROI, trả qua `ket_qua` mà không đổi số phần tử tuple;
  2. `classify`: ảnh rối không làm bìa, có ghi chú đầu dòng;
  3. `submit_common.check_image_fall`: chỉ chặn khi CÒN ảnh sạch thật sự thay được;
  4. nền chữ đặc ở carousel và thẻ Ethan.

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
    assert "DUNG 4 dong" in hoi and "CLUTTERED:" in hoi and "TU_KHOA:" in hoi, hoi
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
    assert "DUNG 5 dong" in hoi, hoi
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


# ---------------------------------------------------------------- 4. nen chu dac
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


def test_threshold_distinguish_text_in_ready_with_image_capture():
    """Hai loại dải giả phải rơi đúng hai phía ngưỡng CLUTTERED_BG_TEXT, không thì
    các test dưới đo sai thứ."""
    import card
    e = card._capability_flow_rank(_canvas_region(1080, 400, [(0, 199, "chu"), (200, 399, "anh")]))
    assert min(e[20:180]) >= card.CLUTTERED_BG_TEXT, min(e[20:180])
    assert card.CLUTTERED_BG_LANG <= max(e[220:380]) < card.CLUTTERED_BG_TEXT, max(e[220:380])


def test_timestamp_background_solid_climb_up_range_lang_on_text_in_ready():
    """Đo thật A9 carousel: chữ in sẵn 690–989, khe lặng 630–689, phía trên là
    ảnh chụp. Nền đặc phủ trọn chữ in sẵn, dải chuyển nằm trong khe lặng."""
    import card
    cv = _canvas_region(1080, 1350, [(0, 600, "anh"), (700, 980, "chu")])
    dac, top = card._timestamp_background_solid(cv, 990)
    assert 690 <= dac <= 700, dac
    assert 600 <= top < dac, (top, dac)


def test_timestamp_background_solid_slit_narrow_date_below_text_in_ready_no_ok_use():
    """Đo thật thẻ Ethan A9: chữ in sẵn 780–1109, khe 1110–1136 ngay trên chữ
    của ta. Dừng ở khe đó là tiêu đề in sẵn lộ nguyên — phải leo qua."""
    import card
    cv = _canvas_region(1200, 1500, [(0, 650, "anh"), (780, 1100, "chu")])
    dac, top = card._timestamp_background_solid(cv, 1136)
    assert 770 <= dac <= 780, dac


def test_timestamp_background_solid_touch_ceiling_then_about_range_lang_no_crop_text_in_ready():
    """Đo thật A9 slide quote: khe lặng 627–650 ngay trên khung quote, phía trên
    lại có chữ in sẵn "$10B INVESTMENT" vắt qua trần 40% (540). Dừng ở trần là
    dải chuyển cắt nửa chữ — phải quay về khe lặng cao nhất đã gặp."""
    import card
    cv = _canvas_region(1080, 1350, [(0, 480, "anh"), (500, 560, "chu"), (690, 980, "chu")])
    dac, top = card._timestamp_background_solid(cv, 650)
    assert dac == 650, dac
    assert 561 <= top < dac, (top, dac)                  # dai chuyen khong cham dai chu 500-560


def test_timestamp_background_solid_text_ta_lie_below_range_lang_empty_then_keep_raw_position():
    import card
    cv = _canvas_region(1080, 1350, [(0, 500, "anh")])
    dac, top = card._timestamp_background_solid(cv, 990)
    assert dac == 990 and 990 - card.CLUTTERED_BG_SPREAD <= top < 990, (dac, top)


def test_timestamp_background_solid_no_has_range_lang_then_use_cell_ceiling_40_percent():
    import card
    cv = _canvas_region(1080, 1350, [(0, 1349, "chu")])
    dac, top = card._timestamp_background_solid(cv, 990)
    assert dac == int(1350 * card.CLUTTERED_BG_CEILING), dac
    assert top == dac - card.CLUTTERED_BG_SPREAD_SAME, top


def test_carousel_image_fall_secondary_full_text_in_ready_keep_image_side_on():
    import carousel
    carousel.set_background("dark")
    cv = _canvas_region(carousel.W, carousel.H, [(0, 600, "anh"), (700, 980, "chu")])
    truoc = cv.copy()
    carousel._layer_if_can(cv, cv.convert("RGB"), 1030, carousel.H, image_cluttered=True)
    for y in (705, 800, 975, 1100, carousel.H - 1):
        assert _is_background(cv, y, carousel.BG), (y, cv.getpixel((0, y)))
    assert cv.getpixel((3, 300)) == truoc.getpixel((3, 300)), "anh phia tren khong duoc dong"
    L = [cv.convert("L").getpixel((30, y)) for y in range(601, 700)]      # cot nen cua dai "anh"
    assert max(abs(L[i + 1] - L[i]) for i in range(len(L) - 1)) < 20, "khong co buoc nhay = khong co vach"


def test_carousel_image_clean_keep_raw_layer_open_old():
    import carousel
    carousel.set_background("dark")
    canvas = Image.new("RGBA", (carousel.W, carousel.H), (10, 10, 10, 255))
    truoc = canvas.copy()
    carousel._layer_if_can(canvas, canvas.convert("RGB"), 1000, carousel.H)
    assert canvas.tobytes() == truoc.tobytes(), "nen toi deu du tuong phan -> khong phu gi"


def test_card_text_bg_strict_secondary_full_text_in_ready():
    import card
    card.set_brand("dcgr")
    cv = _canvas_region(1200, 1500, [(0, 650, "anh"), (780, 1100, "chu")])
    truoc = cv.copy()
    card._text_bg_strict(cv, 1160)
    for y in (790, 1000, 1499):
        assert _is_background(cv, y, card.BG), (y, cv.getpixel((0, y)))
    assert cv.getpixel((3, 300)) == truoc.getpixel((3, 300))


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
