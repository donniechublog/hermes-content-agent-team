#!/usr/bin/env python3
"""LAY NHIEU BANG XEP HANG cho MOT tin — sinh sau su co 09/09/2026.

Sau khi vá xong "Image Edit Arena" thiếu và tên mã biến thể bị nuốt
(tests/test_ranking.py), Ông Chủ bác luôn cả tiền đề "mỗi tin chỉ mang một ảnh
xếp hạng": *"đã làm social media thì làm gì có chuyện bị giới hạn ở nguồn tư
liệu"*, và hai bảng ví dụ *"một bảng là top model tạo sinh, một bảng là top
model chỉnh sửa, đâu có trùng lặp"*. `ranking.find_and_capture_many` (test riêng
ở tests/test_ranking.py) lo phần CHỤP; tệp này test phần MANG VÀO MANIFEST —
`image_prepare._gather_and_download_image` gắn mã XH/XH2, `build_manifest` gộp vào
goi_y_bia/so_xep_hang, `ranking_brief_line` nói cho vai biết có tấm thứ hai.

Chay:  venv/bin/python tests/test_ranking_many.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_prepare as cb   # noqa: E402


def _xh(bang, model, kieu="table"):
    return {"file_path": f"/tmp/{bang}.png", "kind": kieu, "source": bang, "site": "ARENA.AI",
            "board": bang, "rank": 1, "model": model, "url": f"https://arena.ai/{bang}",
            "row": "...", "logo": None, "mentioned": True}


def _a(ma, xep_hang=None, dung=None, ti_le=0.8):
    # Anh xep hang THAT (qua _seen_image) mang uses=["cover_ranking", "body_chart"]
    # ("HERO / BÌA (...)") — CHU KHONG PHAI "cover" tran. Neu de tran "cover" thi comprehension
    # goi_y_bia (khop CHINH XAC phan tu list) doc trung no VOI ca prepend rieng
    # cho xhs, dem trung XH hai lan trong mot test bia dat sai gia dinh nay.
    if dung is None:
        dung = ["cover_ranking", "body_chart"] if xep_hang else ["cover"]
    return {"id": ma, "uses": list(dung), "relevant": True, "domain": "arena.ai", "source": "ranking",
            "ratio": ti_le, "bottom_left_brightness": 50, "short_side": 1000, "landscape": False, "kind": "chart",
            **({"ranking": xep_hang} if xep_hang else {})}


# -------------------------------------------------- _image_item_ranking: gan ma
# `_gather_and_download_image` goi mang that (article_images, arxiv_figures...) nen khong goi thang o
# day — no chi la mot vong lap `for i, xh in enumerate(xhs): anh.insert(i,
# _image_item_ranking(i, xh))` quanh ham thuan duoi, test dung ham thuan la du.
def test_image_item_ranking_list_code_use_by_position():
    """Ket qua dau (i=0) la 'XH' tran; cac ket qua sau danh so XH2, XH3... —
    khong duoc trung ma (tao anh + sua anh la hai bang KHAC nhau, ghi de len
    nhau la mat mot trong hai)."""
    xhs = [_xh("Text-to-Image Arena", "GPT-Image-2.5 Sunburst"),
           _xh("Image Edit Arena", "GPT-Image-2.5 Sunburst")]
    muc = [cb._image_item_ranking(i, xh) for i, xh in enumerate(xhs)]
    assert [m["id"] for m in muc] == ["XH", "XH2"], [m["id"] for m in muc]
    assert {m["id"]: m["ranking"]["board"] for m in muc} == \
        {"XH": "Text-to-Image Arena", "XH2": "Image Edit Arena"}


def test_image_item_ranking_one_result_still_is_xh_ceiling():
    """CHI mot bang (truong hop thuong, khong doi hanh vi cu): ma van la 'XH'
    tran, khong phai 'XH1'."""
    muc = cb._image_item_ranking(0, _xh("Text Arena", "Kimi-K3"))
    assert muc["id"] == "XH", muc["id"]


def test_image_item_ranking_new_temp_keep_own_board_of_no():
    """`ranking` gan vao moi muc phai la CHINH tam do, khong bi tam khac de
    len — day la du lieu ca_xep_hang()/dong_brief_xep_hang doc de ta dung bang."""
    xhs = [_xh("Text-to-Image Arena", "GPT-Image-2.5 Sunburst"),
           _xh("Image Edit Arena", "GPT-Image-2.5 Flare")]
    muc = [cb._image_item_ranking(i, xh) for i, xh in enumerate(xhs)]
    assert muc[0]["ranking"]["model"] == "GPT-Image-2.5 Sunburst"
    assert muc[1]["ranking"]["model"] == "GPT-Image-2.5 Flare"


# --------------------------------------------------------- build_manifest
def test_use_manifest_two_board_len_all_two_code_call_y_cover():
    anh = [_a("XH", _xh("Text-to-Image Arena", "GPT-Image-2.5 Sunburst")),
           _a("XH2", _xh("Image Edit Arena", "GPT-Image-2.5 Sunburst")),
           _a("A1")]
    m = cb.build_manifest("t", {"brand": "dcgr"}, "t", "http://x", {}, Path("/nonexist"), {},
                         Path("/tmp"), anh, [anh[0]["ranking"], anh[1]["ranking"]],
                         True, {}, {}, False, 5, vai_anh="ethan")
    assert m["cover_suggestions"][:2] == ["XH", "XH2"], m["cover_suggestions"]
    assert m["ranking_count"] == 2, m["ranking_count"]
    # m["ranking"] (so, dung boi cong chan needs_ranking_image) la bang DAU TIEN
    assert m["ranking"]["board"] == "Text-to-Image Arena", m["ranking"]


def test_use_manifest_one_board_backward_compatible():
    """Truyen dung MOT phan tu (hanh vi truoc 09/09/2026) — so_xep_hang=1,
    khong co "XH2" nao trong goi_y_bia."""
    xh = _xh("Text Arena", "Kimi-K3")
    anh = [_a("XH", xh)]
    m = cb.build_manifest("t", {"brand": "dcgr"}, "t", "http://x", {}, Path("/nonexist"), {},
                         Path("/tmp"), anh, [xh], True, {}, {}, False, 5, vai_anh="ethan")
    assert m["cover_suggestions"] == ["XH"], m["cover_suggestions"]
    assert m["ranking_count"] == 1
    assert "XH2" not in m["cover_suggestions"]


def test_use_manifest_label_none_like_convention_old():
    """Vai/test khac (test_concept.py, test_brand.py) van truyen None
    o vi tri nay — KHONG duoc nem TypeError tu len(None)."""
    m = cb.build_manifest("t", {"brand": "dcgr"}, "t", "http://x", {}, Path("/nonexist"), {},
                         Path("/tmp"), [_a("A1", dung=("cover",))], None, False, {}, {}, False, 5, vai_anh="ethan")
    assert m["ranking_count"] == 0
    assert m["ranking"] is None


def test_use_manifest_no_board_then_no_fixed_xh_into_call_y():
    m = cb.build_manifest("t", {"brand": "dcgr"}, "t", "http://x", {}, Path("/nonexist"), {},
                         Path("/tmp"), [_a("A1", dung=("cover",))], [], False, {}, {}, False, 5, vai_anh="ethan")
    assert "XH" not in m["cover_suggestions"] and m["ranking_count"] == 0


# ------------------------------------------------------- ranking_brief_line
def test_brief_say_clear_has_board_try_two():
    m = {"is_ranking_story": True,
         "ranking": {"site": "ARENA.AI", "board": "Text-to-Image Arena",
                     "model": "GPT-Image-2.5 Sunburst", "rank": 1, "kind": "table",
                     "mentioned": True},
         "ranking_count": 2}
    dong = cb.ranking_brief_line(m, "bìa", "dre_submit")
    assert "XH2" in dong, dong
    assert "BẮT BUỘC" in dong


def test_brief_one_board_no_mention_xh2():
    m = {"is_ranking_story": True,
         "ranking": {"site": "ARENA.AI", "board": "Text Arena", "model": "Kimi-K3",
                     "rank": 1, "kind": "table", "mentioned": True},
         "ranking_count": 1}
    dong = cb.ranking_brief_line(m, "bìa", "dre_submit")
    assert "XH2" not in dong, dong


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
