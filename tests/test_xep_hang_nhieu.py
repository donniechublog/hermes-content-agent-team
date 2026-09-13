#!/usr/bin/env python3
"""LAY NHIEU BANG XEP HANG cho MOT tin — sinh sau su co 09/09/2026.

Sau khi vá xong "Image Edit Arena" thiếu và tên mã biến thể bị nuốt
(tests/test_xep_hang.py), Ông Chủ bác luôn cả tiền đề "mỗi tin chỉ mang một ảnh
xếp hạng": *"đã làm social media thì làm gì có chuyện bị giới hạn ở nguồn tư
liệu"*, và hai bảng ví dụ *"một bảng là top model tạo sinh, một bảng là top
model chỉnh sửa, đâu có trùng lặp"*. `ranking.find_and_capture_many` (test riêng
ở tests/test_xep_hang.py) lo phần CHỤP; tệp này test phần MANG VÀO MANIFEST —
`image_prepare._gom_va_tai_anh` gắn mã XH/XH2, `dung_manifest` gộp vào
goi_y_bia/so_xep_hang, `dong_brief_xep_hang` nói cho vai biết có tấm thứ hai.

Chay:  venv/bin/python tests/test_xep_hang_nhieu.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_prepare as cb   # noqa: E402


def _xh(bang, model, kieu="bang"):
    return {"tep": f"/tmp/{bang}.png", "kieu": kieu, "nguon": bang, "site": "ARENA.AI",
            "bang": bang, "hang": 1, "model": model, "url": f"https://arena.ai/{bang}",
            "dong": "...", "logo": None, "duoc_nhac": True}


def _a(ma, xep_hang=None, dung=None, ti_le=0.8):
    # Anh xep hang THAT (qua _nhin_anh) mang dung=["HERO / BÌA (...)", "thân
    # (chart)"] — CHU KHONG PHAI "bìa" tran. Neu de tran "bìa" thi comprehension
    # goi_y_bia (khop CHINH XAC phan tu list) doc trung no VOI ca prepend rieng
    # cho xhs, dem trung XH hai lan trong mot test bia dat sai gia dinh nay.
    if dung is None:
        dung = ["HERO / BÌA (bảng xếp hạng)", "thân (chart)"] if xep_hang else ["bìa"]
    return {"ma": ma, "dung": list(dung), "lien_quan": True, "mien": "arena.ai", "tu": "xep_hang",
            "ti_le": ti_le, "goc_trai_sang": 50, "canh_ngan": 1000, "ngang": False, "loai": "chart",
            **({"xep_hang": xep_hang} if xep_hang else {})}


# -------------------------------------------------- _anh_muc_xep_hang: gan ma
# `_gom_va_tai_anh` goi mang that (anh_bai, arxiv_hinh...) nen khong goi thang o
# day — no chi la mot vong lap `for i, xh in enumerate(xhs): anh.insert(i,
# _anh_muc_xep_hang(i, xh))` quanh ham thuan duoi, test dung ham thuan la du.
def test_anh_muc_xep_hang_danh_ma_dung_theo_vi_tri():
    """Ket qua dau (i=0) la 'XH' tran; cac ket qua sau danh so XH2, XH3... —
    khong duoc trung ma (tao anh + sua anh la hai bang KHAC nhau, ghi de len
    nhau la mat mot trong hai)."""
    xhs = [_xh("Text-to-Image Arena", "GPT-Image-2.5 Sunburst"),
           _xh("Image Edit Arena", "GPT-Image-2.5 Sunburst")]
    muc = [cb._image_item_ranking(i, xh) for i, xh in enumerate(xhs)]
    assert [m["ma"] for m in muc] == ["XH", "XH2"], [m["ma"] for m in muc]
    assert {m["ma"]: m["xep_hang"]["bang"] for m in muc} == \
        {"XH": "Text-to-Image Arena", "XH2": "Image Edit Arena"}


def test_anh_muc_xep_hang_mot_ket_qua_van_la_xh_tran():
    """CHI mot bang (truong hop thuong, khong doi hanh vi cu): ma van la 'XH'
    tran, khong phai 'XH1'."""
    muc = cb._image_item_ranking(0, _xh("Text Arena", "Kimi-K3"))
    assert muc["ma"] == "XH", muc["ma"]


def test_anh_muc_xep_hang_moi_tam_giu_rieng_bang_cua_no():
    """`xep_hang` gan vao moi muc phai la CHINH tam do, khong bi tam khac de
    len — day la du lieu ca_xep_hang()/dong_brief_xep_hang doc de ta dung bang."""
    xhs = [_xh("Text-to-Image Arena", "GPT-Image-2.5 Sunburst"),
           _xh("Image Edit Arena", "GPT-Image-2.5 Flare")]
    muc = [cb._image_item_ranking(i, xh) for i, xh in enumerate(xhs)]
    assert muc[0]["xep_hang"]["model"] == "GPT-Image-2.5 Sunburst"
    assert muc[1]["xep_hang"]["model"] == "GPT-Image-2.5 Flare"


# --------------------------------------------------------- dung_manifest
def test_dung_manifest_hai_bang_len_ca_hai_ma_goi_y_bia():
    anh = [_a("XH", _xh("Text-to-Image Arena", "GPT-Image-2.5 Sunburst")),
           _a("XH2", _xh("Image Edit Arena", "GPT-Image-2.5 Sunburst")),
           _a("A1")]
    m = cb.build_manifest("t", {"brand": "dcgr"}, "t", "http://x", {}, Path("/nonexist"), {},
                         Path("/tmp"), anh, [anh[0]["xep_hang"], anh[1]["xep_hang"]],
                         True, {}, {}, False, 5)
    assert m["goi_y_bia"][:2] == ["XH", "XH2"], m["goi_y_bia"]
    assert m["so_xep_hang"] == 2, m["so_xep_hang"]
    # m["xep_hang"] (so, dung boi cong chan can_anh_xep_hang) la bang DAU TIEN
    assert m["xep_hang"]["bang"] == "Text-to-Image Arena", m["xep_hang"]


def test_dung_manifest_mot_bang_tuong_thich_nguoc():
    """Truyen dung MOT phan tu (hanh vi truoc 09/09/2026) — so_xep_hang=1,
    khong co "XH2" nao trong goi_y_bia."""
    xh = _xh("Text Arena", "Kimi-K3")
    anh = [_a("XH", xh)]
    m = cb.build_manifest("t", {"brand": "dcgr"}, "t", "http://x", {}, Path("/nonexist"), {},
                         Path("/tmp"), anh, [xh], True, {}, {}, False, 5)
    assert m["goi_y_bia"] == ["XH"], m["goi_y_bia"]
    assert m["so_xep_hang"] == 1
    assert "XH2" not in m["goi_y_bia"]


def test_dung_manifest_nhan_none_nhu_quy_uoc_cu():
    """Vai/test khac (test_khai_niem.py, test_thuong_hieu.py) van truyen None
    o vi tri nay — KHONG duoc nem TypeError tu len(None)."""
    m = cb.build_manifest("t", {"brand": "dcgr"}, "t", "http://x", {}, Path("/nonexist"), {},
                         Path("/tmp"), [_a("A1", dung=("bìa",))], None, False, {}, {}, False, 5)
    assert m["so_xep_hang"] == 0
    assert m["xep_hang"] is None


def test_dung_manifest_khong_bang_thi_khong_dinh_xh_vao_goi_y():
    m = cb.build_manifest("t", {"brand": "dcgr"}, "t", "http://x", {}, Path("/nonexist"), {},
                         Path("/tmp"), [_a("A1", dung=("bìa",))], [], False, {}, {}, False, 5)
    assert "XH" not in m["goi_y_bia"] and m["so_xep_hang"] == 0


# ------------------------------------------------------- dong_brief_xep_hang
def test_brief_noi_ro_co_bang_thu_hai():
    m = {"tin_xep_hang": True,
         "xep_hang": {"site": "ARENA.AI", "bang": "Text-to-Image Arena",
                      "model": "GPT-Image-2.5 Sunburst", "hang": 1, "kieu": "bang",
                      "duoc_nhac": True},
         "so_xep_hang": 2}
    dong = cb.ranking_brief_line(m, "bìa", "dre_nop")
    assert "XH2" in dong, dong
    assert "BẮT BUỘC" in dong


def test_brief_mot_bang_khong_nhac_xh2():
    m = {"tin_xep_hang": True,
         "xep_hang": {"site": "ARENA.AI", "bang": "Text Arena", "model": "Kimi-K3",
                      "hang": 1, "kieu": "bang", "duoc_nhac": True},
         "so_xep_hang": 1}
    dong = cb.ranking_brief_line(m, "bìa", "dre_nop")
    assert "XH2" not in dong, dong


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
