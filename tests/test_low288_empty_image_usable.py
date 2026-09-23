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


def test_brand_logo_card_not_blocked_by_submit_gate():
    """LOW-295: THE LOGO HANG duoc renderer dung lai thanh SLIDE LOGO, nen cong nop
    khong duoc goi no la "anh trong". Dung loi Ong Chu va tay tren may chu 23/09/2026.

    Hoi qua `role.blocked_empty` — ban DUY NHAT cua luat — chu khong hoi thang
    `check_empty_image`: ham do chi DUNG LOI, khong tu quyet dinh mien ai."""
    the_hang = _img("A77", empty=0.75, logo_card=True, brand_match={"kind": "logo"})
    for vai in ("dre", "ethan"):
        assert role.blocked_empty(the_hang, vai, only_brand_card=True) is False, vai
    assert role.blocked_empty(the_hang, "kite") is False


def test_a_logo_photo_that_is_not_a_brand_card_stays_blocked_for_dre_and_ethan():
    """Chieu con lai cua LOW-273, Ong Chu chot 23/09/2026. Co `logo_card` do
    `logo_card.is_logo_image` gan cho ca anh CHUP thuong — do tren state that: trong
    188 tam cong Dre/Ethan se tha neu mien het, 138 tam la anh chup logo nho tren nen
    tron (anh nap MacBook bai Apple, anh logo la bai Toyota, deu `empty_share` 0.95).

    #256 tung mien `logo_card` ngay trong `check_empty_image` — the thi phan hep nay
    vo hieu, vi cong cua vai co noi "chan" thi ham do van tra ve []."""
    anh_chup = _img("A78", empty=0.75, logo_card=True)          # khong co brand_match
    for vai in ("dre", "ethan"):
        assert role.blocked_empty(anh_chup, vai, only_brand_card=True) is True, vai
        assert nc.check_empty_image(anh_chup, "bìa", _limit(vai)) != [], vai


def test_the_gate_reports_whenever_the_one_rule_says_blocked():
    """Hai cong khong duoc lech nhau NUA — lan truoc lech lam Kite dung han (LOW-337)
    va Dre ket o slide 6 (LOW-288).

    Giao keo dung: `role.blocked_empty` quyet dinh AI bi chan; `check_empty_image` chi
    dung cau loi va PHAI kieu khi ban duy nhat noi "chan". Nguoi goi hoi cai truoc roi
    moi goi cai sau — nen chi can chieu nay dung la hai ben khong the lech."""
    mau = [_img("A26", empty=0.05),                        # anh day
           _img("A77", empty=0.75),                        # logo nen tron, chua dung lai
           _img("A77b", empty=0.75, logo_card=True),       # anh chup logo, KHONG phai the hang
           _img("A77c", empty=0.75, logo_card=True,        # THE LOGO HANG that
                brand_match={"kind": "logo"}),
           _img("A1", empty=None),                         # vision chua do
           _img("A2", empty=0.75, logo_card=False)]
    for vai, hep in (("dre", True), ("ethan", True), ("kite", False)):
        for a in mau:
            if role.blocked_empty(a, vai, only_brand_card=hep):
                assert nc.check_empty_image(a, "bìa", _limit(vai)) != [],                     f"{vai}/{a['id']}: ban duy nhat noi CHAN ma cong nop im lang"


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
