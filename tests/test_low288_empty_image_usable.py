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


def test_logo_card_exempt_is_decided_by_the_caller():
    """LOW-393 (23/09/2026): MIEN TRU la viec cua NGUOI GOI (`role.blocked_empty`), con
    `check_empty_image` chi do nguong.

    Truoc do mien o CA HAI noi nen hai luat nuot nhau: LOW-295/LOW-288 mien moi tam co
    `logo_card` ngay trong `check_empty_image`, con LOW-337 (Ong Chu chot 23/09) noi
    Dre/Ethan chi mien THE LOGO HANG that — cong cua Dre/Ethan thanh ra khong ra loi nao
    (do that: `test_low337_empty_gate_one_rule` fail 2/8 ngay tren main `9ce4a77`)."""
    the_logo = _img("A77", empty=0.75, logo_card=True)
    # Kite mien moi `logo_card` -> tam nay khong bao gio di toi cong nop.
    assert role.blocked_empty(the_logo, "kite") is False
    # Dre/Ethan chi mien THE LOGO HANG that; anh CHUP logo nho van bi chan.
    assert role.blocked_empty(the_logo, "dre", only_brand_card=True) is True
    the_hang = dict(_img("A77c", empty=0.75, logo_card=True), brand_match={"kind": "logo"})
    assert role.blocked_empty(the_hang, "dre", only_brand_card=True) is False
    # Cong nop chi do nguong: khong tu mien, cung khong tu noi long.
    assert nc.check_empty_image(the_logo, "bìa", _limit("dre")) != []
    assert nc.check_empty_image(_img("A78", empty=0.75), "bìa", _limit("dre")) != []
    assert nc.check_empty_image(_img("A26", empty=0.05), "bìa", _limit("dre")) == []


def test_two_gates_agree_on_every_sample():
    """Hai cong phai khop khi da tinh MIEN TRU: `role.blocked_empty` = phep do cua
    `check_empty_image` CONG lop mien tru cua vai (LOW-393).

    Day la test giu cho chung khoi lech lan nua — lan truoc lech lam Kite dung han
    (LOW-337) va Dre ket o slide 6 (LOW-288)."""
    mau = [_img("A26", empty=0.05),                        # anh day
           _img("A77", empty=0.75),                        # logo nen tron, chua dung lai
           _img("A77b", empty=0.75, logo_card=True),       # ... da dung thanh slide logo
           _img("A1", empty=None),                         # vision chua do
           _img("A2", empty=0.75, logo_card=False)]
    for vai in ("dre", "ethan", "kite"):
        chi_the_hang = vai in ("dre", "ethan")     # LOW-337: hai vai nay chi mien the logo hang
        for a in mau:
            cong_nop = bool(nc.check_empty_image(a, "bìa", _limit(vai)))
            mien = role.is_brand_logo_card(a) if chi_the_hang else bool(a.get("logo_card"))
            ban_duy_nhat = role.blocked_empty(a, vai, only_brand_card=chi_the_hang)
            assert ban_duy_nhat == (cong_nop and not mien), \
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
