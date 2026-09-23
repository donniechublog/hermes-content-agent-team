#!/usr/bin/env python3
"""LOW-270 (19/09/2026, Ông Chủ): "logo mà hiển thị quá nhỏ so với khung hình thì
cũng ko ưu tiên".

Đo thật 39 hãng: thẻ logo cũ ép logo rộng 62% khung, dán cả viền trống của tệp
nguồn — logo chữ ngang chỉ chiếm 3–10% diện tích (Microsoft 6,6%). Sửa gốc:
cắt viền, trải 88% bề ngang; nền chọn theo số điểm ảnh bị chìm (không theo độ
sáng trung bình — Hugging Face từng mất chữ); logo VẪN nhỏ dưới
`LOGO_FILL_MIN` thì không được điểm ưu tiên và xếp cuối gợi ý bìa.

Chạy:  venv/bin/python tests/test_low270_logo_card_size.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import image_brand as th                                     # noqa: E402
from prepare import fallback_rounds                            # noqa: E402
from prepare import manifest                                   # noqa: E402


def _wordmark(path: Path, size=(1000, 1000), box=(300, 450, 700, 550), color=(20, 20, 20, 255),
              background=(0, 0, 0, 0)) -> Path:
    """Logo giả: một khối chữ `box` giữa một khung rộng nhiều viền trống."""
    im = Image.new("RGBA", size, background)
    ImageDraw.Draw(im).rectangle(box, fill=color)
    im.save(path)
    return path


def test_trim_logo_margin_transparent_and_white_background():
    with tempfile.TemporaryDirectory() as d:
        clear = th._trim_logo_margin(Image.open(_wordmark(Path(d) / "a.png")))
        assert clear.size == (401, 101), clear.size
        white = th._trim_logo_margin(Image.open(_wordmark(Path(d) / "b.png", background=(255, 255, 255, 255))))
        assert white.size == (401, 101), white.size          # nen trang duc cung duoc cat
        assert white.getpixel((0, 0))[3] == 255               # phan logo van duc


def test_card_logo_fills_width_not_old_62_percent():
    """Cùng một logo 4:1 có viền rộng: thẻ cũ ra ~6% khung, giờ phải trải 88%."""
    with tempfile.TemporaryDirectory() as d:
        src = _wordmark(Path(d) / "wide.png")
        out, tone, fill = th.card_logo(src, Path(d) / "card.png")
        im = Image.open(out).convert("RGB")
        bg = im.getpixel((5, 5))
        cols = [x for x in range(im.width) if im.getpixel((x, 450)) != bg]
        assert cols and (cols[-1] - cols[0] + 1) / im.width > 0.85, (cols[0], cols[-1])
        assert fill > 0.08 and fill >= th.LOGO_FILL_MIN, fill
        assert tone == "light"                                 # chu den -> nen sang


def test_card_logo_background_keeps_dark_text_visible():
    """Hugging Face: mặt cười vàng lớn + chữ xanh đen. Độ sáng trung bình cũ ra
    nền tối, chữ chìm mất. Giờ nền phải là nền sáng để chữ hiện."""
    with tempfile.TemporaryDirectory() as d:
        im = Image.new("RGBA", (1000, 300), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        dr.ellipse((0, 0, 300, 300), fill=(255, 210, 30, 255))           # mat cuoi vang
        dr.rectangle((340, 110, 1000, 190), fill=(10, 16, 35, 255))      # chu xanh den
        src = Path(d) / "hf.png"
        im.save(src)
        _, tone, fill = th.card_logo(src, Path(d) / "card.png")
        assert tone == "light", tone
        assert fill > 0.1, fill          # phan chu duoc tinh la nhin thay


def test_small_logo_label_and_normal_label():
    small_label = th.label_by_type({"company": "Anthropic", "kind": "logo", "background_tone": "light",
                                    "small_logo": True, "logo_fill": 0.0698})
    assert "QUÁ NHỎ" in small_label and "7%" in small_label, small_label
    big_label = th.label_by_type({"company": "Microsoft", "kind": "logo", "background_tone": "light",
                                  "logo_fill": 0.133})
    assert "Ưu tiên đầu" in big_label and "Đường cuối" not in big_label, big_label


def test_round_brand_small_logo_gets_no_priority_bonus():
    """BUSINESS: logo đứng đầu (+100) — trừ khi logo quá nhỏ, khi đó xuống dưới
    cả chân dung founder."""
    def cand(kind, score, small=False):
        bm = {"company": "Anthropic", "key": "anthropic", "kind": kind, "keyword": kind}
        if small:
            bm["small_logo"] = True
        return {"image_url": f"https://x/{kind}.png", "alt": kind, "og": False, "source": "brand",
                "w": 1200, "h": 1500, "page_url": "https://x", "score": score, "brand_match": bm}

    def run(small):
        seen = {}

        def download(cands, wd, da_giu=()):
            seen["kinds"] = [c["brand_match"]["kind"] for c in cands]
            return []
        with tempfile.TemporaryDirectory() as d, \
             mock.patch("image_brand.vendors_in_story", return_value=[{"company": "Anthropic", "key": "anthropic"}]), \
             mock.patch("image_brand.vendor_images",
                        return_value=[cand("person", 24), cand("logo", 18, small=small)]), \
             mock.patch.object(fallback_rounds, "_report_brand_empty", return_value=[]), \
             mock.patch.object(fallback_rounds, "download_and_filter", side_effect=download):
            fallback_rounds._round_brand([], "Anthropic raises funding", "", Path(d), category="BUSINESS",
                                         khong_browser=True)
        return seen["kinds"]

    assert run(small=False) == ["logo", "person"]
    assert run(small=True) == ["person", "logo"]


def test_cover_suggestions_small_logo_last():
    def img(i, **o):
        a = {"id": i, "uses": ["cover"], "relevant": True, "bottom_left_brightness": 40,
             "short_side": 1200, "domain": "x.com", "source": "brand", "ratio": 0.8}
        a.update(o)
        return a
    anh = [img("A1", brand_match={"kind": "logo", "small_logo": True}),
           img("A2", concept=True),
           img("A3", brand_match={"kind": "photo"})]
    covers = manifest.compute_derived(anh, "dre")["cover_suggestions"]
    assert covers[-1] == "A1", covers


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
