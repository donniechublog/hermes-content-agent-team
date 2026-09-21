#!/usr/bin/env python3
"""LOW-338 (21/09/2026) — the quote/tran cards: text block <= 20% of card height, overlay narrow.

Ong Chu, the Qwen-Image-2.1 cards: text background too big; text only ~20% of the area,
background just an overlay layer. Run:  python tests/test_low338_card_text_share.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from PIL import Image, ImageDraw  # noqa: E402

import card  # noqa: E402

QUOTE = "Alibaba tung Qwen-Image-2.1 chỉ 7 tỷ tham số, tạo ảnh 2K và chỉnh sửa ngay trong một mô hình"


def test_quote_block_at_most_20_percent():
    card.set_brand("dcgr")
    d = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    for h in card.RATIOS.values():
        g = card._quote_geometry(d, QUOTE, "via The Decoder", "@dcgr.tech", h)
        assert g.buoc * len(g.q_lines) <= h * card.TEXT_MAX_SHARE, (h, g.buoc, len(g.q_lines))


def test_ceiling_text_box_is_smaller_than_before():
    assert card.CEILING_TEXTBOX <= 0.30 and card.TEXT_MAX_SHARE == 0.20


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
