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


def test_submit_gate_phrases_what_blocked_empty_decided():
    """Tu LOW-337, `check_empty_image` chi la CAI MIENG: `role.blocked_empty(...,
    only_brand_card=True)` quyet dinh, roi goi ham nay de lay CAU CHU.

    Nen ham nay khong duoc tu mien gi them — mien o day la cam mieng dung luc cai
    dau vua bao "chan". PR #256 tung mien ca `logo_card` va lam do main: 138/188 tam
    duoc tha la anh CHUP logo nho tren nen tron, dung loai LOW-273 sinh ra de chan."""
    import subject_fit
    limit = getattr(role.rules_module("dre"), "EMPTY_SHARE_MAX", subject_fit.EMPTY_SHARE_MAX)
    anh_chup_logo = _img("A77", empty=0.75, logo_card=True)      # co co nhung KHONG phai the hang
    assert role.blocked_empty(anh_chup_logo, "dre", only_brand_card=True) is True
    assert nc.check_empty_image(anh_chup_logo, "bìa", limit) != [], \
        "cai dau bao chan ma cai mieng im — anh di tiep, khong ai biet"
    the_logo_hang = _img("A13", empty=0.9, logo_card=True, brand_match={"kind": "logo"})
    assert role.blocked_empty(the_logo_hang, "dre", only_brand_card=True) is False, \
        "the logo hang phai duoc mien o CAI DAU (LOW-295), khong phai o cai mieng"


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
