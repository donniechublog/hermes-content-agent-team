#!/usr/bin/env python3
"""LOW-264 (bổ sung, 20/09/2026, Ông Chủ: "miễn logo khỏi rule").

Đo thật: `card_logo` dựng hai lần từ cùng tệp P154 cho md5 y hệt, nên bài thứ hai
về cùng hãng bị `check_not_reused` chặn ("TRUNG anh da dung") trong 14 ngày — làm
logo-first (LOW-264) và logo phóng to (LOW-270) thành lượt sửa vô ích. Miễn theo
DẤU XUẤT XỨ `logo_card` như ảnh xếp hạng; dấu đó từng bị `download_and_filter`
ghi đè thành `engine_download`, nên test cả hai đầu.

Chạy:  venv/bin/python tests/test_low264_logo_card_reuse_exempt.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_brand as th                                     # noqa: E402
import image_provenance                                        # noqa: E402
import image_rules_dre as dre                                  # noqa: E402
import image_rules_ethan as ethan                              # noqa: E402
import image_rules_kite as kite                                # noqa: E402
import prepare.download_filter as download_filter               # noqa: E402

LINK_1 = "https://a.example.com/tin-microsoft-1"
LINK_2 = "https://b.example.com/tin-microsoft-2"


def _wordmark(path: Path) -> Path:
    im = Image.new("RGBA", (1000, 400), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rectangle((0, 0, 380, 400), fill=(242, 80, 34, 255))
    d.rectangle((420, 100, 1000, 300), fill=(90, 90, 90, 255))
    im.save(path)
    return path


def test_provenance_survives_download_and_filter():
    """Dấu `logo_card` do card_logo đóng phải còn nguyên ở original/A?.png."""
    with tempfile.TemporaryDirectory() as d:
        wd = Path(d)
        card, _, _ = th.card_logo(_wordmark(wd / "logo.png"), wd / "card.png")
        cand = {"image_url": str(card), "file_path": str(card), "alt": "Commons: logo", "source": "brand",
                "page_url": "https://commons.wikimedia.org/wiki/File:x.svg", "graphic_allowed": True, "score": 18,
                "brand_match": {"company": "Microsoft", "key": "microsoft", "kind": "logo"}}
        ra = download_filter.download_and_filter([cand], wd / "out")
        assert ra, "the logo bi bo o download_and_filter"
        with Image.open(ra[0]["original_path"]) as im:
            assert image_provenance.is_logo_card(im), image_provenance.provenance(im)
        # anh thuong cung duong (khong phai the logo) van la engine_download
        other = dict(cand, graphic_allowed=False, brand_match={"kind": "photo"})
        assert download_filter._provenance_of(other) == "engine_download"
        assert download_filter._provenance_of(dict(cand, brand_match={"kind": "person"})) == "engine_download"


def test_logo_card_exempt_in_all_three_rule_modules_but_not_other_images():
    with tempfile.TemporaryDirectory() as d:
        wd = Path(d)
        card, _, _ = th.card_logo(_wordmark(wd / "logo.png"), wd / "card.png")
        ledger = wd / "used_images.jsonl"
        with mock.patch.object(image_provenance, "_used_images_log", lambda: ledger):
            for mod in (dre, ethan, kite):
                ledger.write_text("", encoding="utf-8")
                mod.record_used(card, "draft-bai-1", "dre", LINK_1)
                assert ledger.read_text(encoding="utf-8").strip(), "so khong ghi duoc"
                # bai 2 (khac story) cung the logo -> duoc qua
                assert mod.check_not_reused("bia", card, "draft-bai-2", LINK_2) == ([], []), mod.__name__
                # CUNG diem anh nhung dong dau engine_download -> van bi chan: mien theo dau, khong theo may man
                with Image.open(card) as im:
                    plain = wd / f"plain_{mod.__name__}.png"
                    im.save(plain, "PNG", pnginfo=image_provenance.stamp_provenance("engine_download"))
                loi, _ = mod.check_not_reused("bia", plain, "draft-bai-2", LINK_2)
                assert loi and "TRUNG anh da dung" in loi[0], (mod.__name__, loi)


def test_is_logo_card_reads_only_logo_stamp():
    with tempfile.TemporaryDirectory() as d:
        for stamp, expect in (("logo_card", True), ("ranking_capture", False), ("engine_download", False)):
            p = Path(d) / f"{stamp}.png"
            Image.new("RGB", (20, 20), (255, 255, 255)).save(p, "PNG", pnginfo=image_provenance.stamp_provenance(stamp))
            with Image.open(p) as im:
                assert image_provenance.is_logo_card(im) is expect, stamp


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
