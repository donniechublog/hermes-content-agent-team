#!/usr/bin/env python3
"""Tìm ảnh web (Bing async / Yandex qua Chromium) — phần bóc/lọc thuần, không mạng.

Ông Chủ 12/09/2026: "bạn đâu bị giới hạn bởi cái gì, nếu không thể code nổi một
đoạn mã tìm kiếm hình ảnh cho model thì tôi cũng không biết nên hiểu thế nào".
Xem docstring find_image_web.py cho bảng đo Google/DDG/Bing/Yandex từ IP máy chủ.

Chạy:  venv/bin/python tests/test_tim_anh_web.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import find_image_web as tw                                      # noqa: E402


def test_bing_murl_hai_dinh_dang_va_unicode():
    html = ('<a class="iusc" m=\'{"murl":"https://a.com/x.jpg","turl":"t"}\'></a>'
            'm=&quot;{&quot;murl&quot;:&quot;https://b.com/y.png&quot;}'
            '{"murl":"https://c.com/\\u5716.jpg"}')
    ra = tw.bing_murl(html)
    assert "https://a.com/x.jpg" in ra and "https://b.com/y.png" in ra
    assert any("圖" in u for u in ra), ra


def test_yandex_img_url_giai_ma():
    hs = ["https://yandex.com/images/search?img_url=https%3A%2F%2Fcdn.x.com%2Fa.jpg&pos=1", "https://yandex.com/khac"]
    assert tw.yandex_img_url(hs) == ["https://cdn.x.com/a.jpg"]


def test_loc_bo_stock_thumb_khong_phai_anh_va_trung():
    urls = ["https://i.ytimg.com/vi/x/maxresdefault.jpg",          # thumb youtube
            "https://www.shutterstock.com/a.jpg",                    # stock watermark
            "https://a.com/page.html",                               # khong phai anh
            "https://cdn.wccftech.com/x.jpg", "https://cdn.wccftech.com/x.jpg",
            "https://b.com/y.webp?w=1"]
    ra = tw.filter(urls, 10, "web_bing", "q")
    assert [c["anh"] for c in ra] == ["https://cdn.wccftech.com/x.jpg", "https://b.com/y.webp?w=1"]
    assert ra[0]["trang"] == ra[0]["anh"], "trang = chinh anh de qua loc ben thu ba"
    assert ra[0]["diem"] > tw.filter(urls, 10, "web_yandex", "q")[0]["diem"], "Bing xep truoc Yandex"
    assert ra[0]["diem"] < 42, "web phai xep SAU og:image bao chi (42): web co the lac de ca loat"
    assert len(tw.filter(urls, 1, "web_bing", "q")) == 1


def test_yandex_la_nguon_chinh_bing_tat():
    assert [t for t, _ in tw.SOURCE] == ["Yandex"], "Bing lech de 3/5 tu IP may chu (12/09) — khong duoc bat mac dinh"


def test_noi_vao_vai_va_engine():
    assert "find_image_web.find_image_web(" in (ROOT / "find_more_images.py").read_text(encoding="utf-8")
    src = (ROOT / "chuan_bi" / "fallback_rounds.py").read_text(encoding="utf-8")
    assert "find_image_web.find_image_web(" in src and "press_entity_images.press_entity_images(" in src, \
        "engine phai TU tim web + bao ve thuc the trong vong tim rong, khong doi vai goi"


if __name__ == "__main__":
    ok = 0
    ten = [n for n in dir() if n.startswith("test_")]
    for n in ten:
        try:
            globals()[n]()
            ok += 1
        except AssertionError as e:
            print(f"FAIL {n}: {e}")
    print(f"{ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
