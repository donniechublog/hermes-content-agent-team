#!/usr/bin/env python3
"""Bia Kite khong duoc lay anh bi cong ANH TRONG chan (LOW-273/LOW-288).

Ban va nong tren may chu 22/09/2026 11:47 (kite_prepare.figure_hero), dua vao repo
truoc khi deploy LOW-337 de push khong de mat no. Test FAIL tren code truoc ban va:
logo nho tren nen tron (empty_share 0.9) duoc chon lam bia.

Chay:  python tests/test_kite_hero_blocked_empty.py
"""
import sys
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import kite_prepare  # noqa: E402


def _m():
    return {"draft_id": "x", "images": [
        {"id": "A1", "w": 1600, "h": 1600, "kind": "photo", "relevant": True, "empty_share": 0.9},
        {"id": "A2", "w": 1600, "h": 900, "kind": "photo", "relevant": True, "empty_share": 0.1}]}


def test_blank_image_is_not_the_cover():
    with mock.patch.object(kite_prepare, "_force_raw", lambda m: []):
        assert kite_prepare.figure_hero(_m())["id"] == "A2"


def test_only_blank_images_means_no_image_cover():
    m = _m()
    m["images"] = m["images"][:1]
    with mock.patch.object(kite_prepare, "_force_raw", lambda m: []):
        assert kite_prepare.figure_hero(m) is None


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
