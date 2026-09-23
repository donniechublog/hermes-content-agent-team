#!/usr/bin/env python3
"""LOW-288 (20/09/2026) — ảnh bị cổng ẢNH TRỐNG (LOW-273) chặn thì cũng không được
nằm trong các danh sách "ảnh dùng được" mà cổng khác dựa vào.

Dre làm lại tin Lovable (task t_c4e5d636) kẹt ở slide 6: `check_image_fall` đòi dùng
"ảnh sạch chưa dùng A77/A78" trước khi cho dùng ảnh rối, mà A77/A78 chính là logo
Lovable trên nền trơn (empty_share 0.75) — `check_empty_image` chặn cứng. Cùng gốc:
`count_image_use_ok` đếm cả ảnh trống (LOW-280), `kite_prepare._force_raw` ép Kite
dùng A12 trống 0.85 (LOW-278).

Chạy:  venv/bin/python tests/test_low288_empty_image_usable.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import kite_prepare  # noqa: E402
import role  # noqa: E402
import schema  # noqa: E402
import submit_common as nc  # noqa: E402


def _img(ma, empty=0.05, **k):
    a = {"id": ma, "original_path": f"/tmp/{ma}.png", "uses": ["body"], "relevant": True,
         "cluttered": False, "kind": "photo", "faces": 0, "landscape": False, "h": 1300,
         "w": 1040, "ratio": 0.8, "empty_share": empty}
    a.update(k)
    return a


def test_blocked_empty_matches_gate():
    trong = _img("A77", empty=0.75)          # logo Lovable nen tron
    day = _img("A26", empty=0.05)
    for vai in ("dre", "ethan", "kite"):
        assert role.blocked_empty(trong, vai) is True, vai
        assert role.blocked_empty(day, vai) is False, vai
    # vision chua do -> khong chan (y nhu check_empty_image)
    assert role.blocked_empty(_img("A1", empty=None), "dre") is False


def _limit(vai):
    """Nguong cua vai — dung con so ma chinh `role.blocked_empty` dung."""
    import subject_fit
    return getattr(role.rules_module(vai), "EMPTY_SHARE_MAX", subject_fit.EMPTY_SHARE_MAX)


def test_logo_card_not_blocked_by_submit_gate():
    """LOW-295: logo tren nen tron duoc renderer dung lai thanh SLIDE LOGO, nen cong
    nop khong duoc goi no la "anh trong".

    Fail tren ma cu: `check_empty_image` chan A77 du `logo_card` True — anh qua duoc
    danh sach "dung duoc" (role.blocked_empty mien) roi chet o cong nop. Dung loi Ong
    Chu va tay tren may chu 23/09/2026."""
    the_logo = _img("A77", empty=0.75, logo_card=True)
    assert nc.check_empty_image(the_logo, "bìa", _limit("dre")) == [], \
        "cong nop van goi slide logo la anh trong"
    # khong phai logo_card thi VAN chan — khong noi long ca cong
    assert nc.check_empty_image(_img("A78", empty=0.75), "bìa", _limit("dre")) != []


def test_two_gates_agree_on_every_sample():
    """Hai cong phai tra CUNG mot cau tra loi: `role.blocked_empty` la ban duy nhat
    (docstring cua chinh no), `check_empty_image` chi la mat cua no o buoc nop.

    Day la test giu cho chung khoi lech lan nua — lan truoc lech lam Kite dung han
    (LOW-337) va Dre ket o slide 6 (LOW-288)."""
    mau = [_img("A26", empty=0.05),                        # anh day
           _img("A77", empty=0.75),                        # logo nen tron, chua dung lai
           _img("A77b", empty=0.75, logo_card=True),       # ... da dung thanh slide logo
           _img("A1", empty=None),                         # vision chua do
           _img("A2", empty=0.75, logo_card=False)]
    for vai in ("dre", "ethan", "kite"):
        for a in mau:
            cong_nop = bool(nc.check_empty_image(a, "bìa", _limit(vai)))
            ban_duy_nhat = role.blocked_empty(a, vai)
            assert cong_nop == ban_duy_nhat, \
                f"{vai}/{a['id']}: cong nop noi {cong_nop}, role.blocked_empty noi {ban_duy_nhat}"


def test_image_fall_not_ask_for_empty_image(monkey=None):
    """A56 rối được dùng khi ảnh sạch còn lại chỉ là logo nền trơn A77/A78."""
    anh = {"A56": _img("A56", cluttered=True, has_keywords=False),
           "A77": _img("A77", empty=0.75), "A78": _img("A78", empty=0.75)}
    m = {"image_role": "dre", "draft_id": "lovable-mua-sutro", "link": "https://x/y"}
    cu = role.rules_module("dre").check_not_reused
    role.rules_module("dre").check_not_reused = lambda *a, **k: ([], [])
    try:
        assert nc.check_image_fall(anh, {"A56": "slide 6"}, m) == []
        # con anh sach THAT (khong trong) thi van doi doi
        anh["A80"] = _img("A80", empty=0.05)
        loi = nc.check_image_fall(anh, {"A56": "slide 6"}, m)
        assert loi and "A80" in loi[0] and "A77" not in loi[0], loi
    finally:
        role.rules_module("dre").check_not_reused = cu


def test_count_image_use_ok_skips_empty():
    bo = [_img(f"A{i}") for i in range(1, 5)] + [_img("A77", empty=0.75)]
    assert schema.count_image_use_ok(bo, "dre") == 4, schema.count_image_use_ok(bo, "dre")


def test_kite_force_list_skips_empty(tmp_path=None):
    """Tin chuyển sang Kite: mã ảnh trống không còn bị ép vào bộ (LOW-278)."""
    m = {"draft_id": "d1", "kite_task_id": "t_1",
         "images": [_img("A12", empty=0.85, kind="chart"), _img("A13"), _img("A15")]}
    ep = kite_prepare._force_raw(m)
    assert "A12" not in ep and "A13" in ep and "A15" in ep, ep


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
