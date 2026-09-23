#!/usr/bin/env python3
"""LOW-337 (23/09/2026), phần nối: cổng ẢNH TRỐNG phải có MỘT bản luật cho mọi vai.

LOW-337 đã cho cổng nộp của Kite hỏi qua `role.blocked_empty` — nơi thẻ logo hãng
được miễn từ LOW-295 — vì bài "GPT-6 Sol and Luna" (23/09) kẹt cứng: bộ ép đòi A13
(thẻ logo OpenAI), còn cổng nộp đọc thẳng `check_empty_image` nên chặn đúng A13 đó.

Nhưng LOW-337 chỉ sửa chỗ gọi của Kite. Dre (4 chỗ) và Ethan (1 chỗ) vẫn đọc thẳng
`check_empty_image`, tức HAI vai còn lại vẫn mang luật riêng — đúng cái thế "hai cổng
hai luật" mà LOW-337 đặt ra để dẹp. Ông Chủ chốt 23/09/2026: cả ba vai đọc một bản.

Ngưỡng KHÔNG đổi: `role.blocked_empty` lấy đúng `image_rules_<vai>.EMPTY_SHARE_MAX`
(đo được: dre/ethan/kite đều 0.6). Khác biệt duy nhất là thẻ logo được miễn.

Chạy:  venv/bin/python tests/test_low337_empty_gate_one_rule.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import role  # noqa: E402
import subject_fit  # noqa: E402
from tam import so_tam  # noqa: E402
from test_spec_dre import _anh, _bia, _co, _slide  # noqa: E402
from test_spec_dre import _m as _m_dre, _spec as _spec_dre  # noqa: E402
from test_spec_dre import _chay as _chay_dre  # noqa: E402
from test_spec_ethan import _bo, _chay as _chay_ethan, _m as _m_ethan, _spec as _spec_ethan  # noqa: E402

TRONG = "gần như TRỐNG"
# THẺ LOGO HÃNG thật (`image_brand.card_logo` dựng ra): LOW-295 dựng lại thành SLIDE
# LOGO 90% bề ngang nên KHÔNG còn là "ảnh trống" theo nghĩa cổng này chặn.
THE_LOGO_HANG = {"empty_share": 0.9, "logo_card": True, "subject_kind": "logo",
                 "brand_match": {"kind": "logo"}, "subject_box": [0.2, 0.2, 0.8, 0.6]}
# Ảnh CHỤP logo nhỏ trên nền trơn, `logo_card.is_logo_image` cũng gắn cờ `logo_card`
# nhưng KHÔNG phải thẻ hãng — đúng loại LOW-273 sinh ra để chặn. Đo trên state thật
# 23/09/2026: 138/188 tấm thuộc loại này (ảnh nắp MacBook bài Apple `empty_share` 0.95,
# ảnh logo lạ trên nền kẻ sọc bài Toyota).
ANH_CHUP_LOGO = {"empty_share": 0.9, "logo_card": True, "subject_kind": "logo",
                 "subject_box": [0.2, 0.2, 0.8, 0.6]}
ANH_TRONG = {"empty_share": 0.9, "subject_kind": "logo",
             "subject_box": [0.4, 0.45, 0.6, 0.55]}


# --------------------------------------------- 1. một bản luật, đo ở `blocked_empty`
def test_all_three_roles_read_one_rule_and_the_same_threshold():
    """Ngưỡng phải y như cũ ở cả ba vai — đổi cổng KHÔNG được kéo theo đổi ngưỡng."""
    import image_rules_dre, image_rules_ethan, image_rules_kite
    for slug, mod in (("dre", image_rules_dre), ("ethan", image_rules_ethan),
                      ("kite", image_rules_kite)):
        thang = getattr(mod, "EMPTY_SHARE_MAX", subject_fit.EMPTY_SHARE_MAX)
        qua = getattr(role.rules_module(role.ROLE[slug].slug), "EMPTY_SHARE_MAX",
                      subject_fit.EMPTY_SHARE_MAX)
        assert thang == qua, (slug, thang, qua)
        assert role.blocked_empty({**THE_LOGO_HANG}, slug) is False, slug
        assert role.blocked_empty({**ANH_TRONG}, slug) is True, slug


def test_only_brand_card_narrows_the_exemption_to_real_brand_cards():
    """Ong Chu chot 23/09/2026: Dre/Ethan chi mien THE LOGO HANG, khong mien moi tam
    co co `logo_card` — neu khong thi 138 anh chup logo nho tren nen tron lot qua,
    tuc LOW-273 bi go mat o hai vai."""
    for slug in ("dre", "ethan"):
        assert role.blocked_empty({**THE_LOGO_HANG}, slug, only_brand_card=True) is False, slug
        assert role.blocked_empty({**ANH_CHUP_LOGO}, slug, only_brand_card=True) is True, slug
        assert role.blocked_empty({**ANH_TRONG}, slug, only_brand_card=True) is True, slug
    # Kite giu nguyen duong cu cua LOW-337 (mien het) — doi Kite la viec rieng
    assert role.blocked_empty({**ANH_CHUP_LOGO}, "kite") is False


# --------------------------------------------------------------- 2. cổng nộp của Dre
# Phải đi đường GHÉP (`_resolve_stack`): ảnh một mình thì Dre đã rẽ sớm sang nhánh
# dựng SLIDE LOGO (LOW-295) và không chạm cổng này, nên thử ở đó không chứng minh
# được gì — đo 23/09/2026: test ảnh-một-mình xanh cả trên mã CŨ lẫn mã MỚI.
def _bo_ghep(t, **k_a2):
    """Bộ đủ của Dre, slide 2 là GHÉP hai ảnh ngang A2+A3."""
    wd = Path(t)
    anh = [_anh(wd, "A1", 1000, 1250),
           _anh(wd, "A2", 1500, 1000, **k_a2), _anh(wd, "A3", 1500, 1000)] +           [_anh(wd, f"A{i}", 1000, 1250) for i in range(4, 7)]
    spec = _spec_dre(_bia("A1"), [{"stack": ["A2", "A3"], "text": "x",
                                   "quote": "Một câu", "attrib": "X"},
                                  _slide("A4", quote="Câu hai", attrib="Y"),
                                  _slide("A5"), _slide("A6")])
    return spec, _m_dre(wd, anh, stackable_pairs=["A2", "A3"]), wd


def test_dre_submit_gate_lets_a_brand_logo_card_through():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        _ra, loi, _c, _d = _chay_dre(*_bo_ghep(t, **THE_LOGO_HANG))
        assert not _co(loi, TRONG), loi


def test_dre_submit_gate_still_blocks_a_really_empty_image():
    """Chiều còn lại: bỏ cổng đi thì test trên vẫn xanh mà luật LOW-273 mất."""
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        _ra, loi, _c, _d = _chay_dre(*_bo_ghep(t, **ANH_TRONG))
        assert _co(loi, TRONG), loi


# ------------------------------------------------------------- 3. cổng nộp của Ethan
def test_ethan_submit_gate_lets_a_brand_logo_card_through():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        anh[0] = _anh(wd, "A1", 1000, 1250, **THE_LOGO_HANG)
        _ra, loi, _c = _chay_ethan(_spec_ethan("A1"), _m_ethan(wd, anh), wd)
        assert not _co(loi, TRONG), loi


def test_ethan_submit_gate_still_blocks_a_really_empty_image():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        anh[0] = _anh(wd, "A1", 1000, 1250, **ANH_TRONG)
        _ra, loi, _c = _chay_ethan(_spec_ethan("A1"), _m_ethan(wd, anh), wd)
        assert _co(loi, TRONG), loi


# ------------------------------- 4. chiều hẹp: ảnh CHỤP logo nhỏ vẫn phải bị chặn
def test_dre_gate_still_blocks_a_logo_photo_that_is_not_a_brand_card():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        _ra, loi, _c, _d = _chay_dre(*_bo_ghep(t, **ANH_CHUP_LOGO))
        assert _co(loi, TRONG), loi


def test_ethan_gate_still_blocks_a_logo_photo_that_is_not_a_brand_card():
    with tempfile.TemporaryDirectory() as t, so_tam(t):
        anh, wd = _bo(t)
        anh[0] = _anh(wd, "A1", 1000, 1250, **ANH_CHUP_LOGO)
        _ra, loi, _c = _chay_ethan(_spec_ethan("A1"), _m_ethan(wd, anh), wd)
        assert _co(loi, TRONG), loi


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
