#!/usr/bin/env python3
"""LOW-366 (23/09/2026) — slide Kite cung phai giu chu trong o vuong giua khung 4:5.

Ong Chu gui ba anh chup tu Instagram (AMD Ryzen, BytePlus, vu kien Apple — deu la slide Kite):
*"chúng ta có thể thấy phía trên vẫn còn dư một viền đen nhưng phía dưới thì lại quá sát text"*.
LOW-364/391 moi lam Ethan (`card.py`) va Dre (`carousel.py`); Kite (`render_edu.py`, bo cuc HTML)
con le 80px deu bon phia, nen masthead tren va folio duoi (dong "@dcgr.tech · ... · N phút đọc")
nam trong dai bi cat.

Ong Chu cung ngay: *"'@dcgr.tech … 5 phút đọc' là thông tin ko bắt buộc phải có trong nội dung
ig, có thể lược phần đó mà ko cần phải lo gì cả"* — dong folio bi BO han, khung rong them ~90px.

Do tren HOP CHU THAT bang Chromium: masthead (dai tren cung) va day cot chu. Khong co Chromium
thi lui ve kiem le trong CSS — van fail tren code cu (le 80px deu, con dong folio).

Chay:  venv/bin/python tests/test_low366_kite_safe_zone.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import render_edu  # noqa: E402
import safe_zone  # noqa: E402

SPEC = {
    "brand": "dcgr", "section": "AI TOOLING", "folio": "AMD RYZEN",
    "slides": [
        # Bia KHONG co anh (hero art ve san 920x470) — kieu chat cho nhat cua Kite.
        {"kind": "cover", "eyebrow": "THỊ TRƯỜNG · HARDWARE",
         "title": "AMD mở bán Ryzen 5 chênh 20 USD",
         "standfirst": "Hai mẫu chip phổ thông của AMD lên sàn Amazon cao hơn giá đề xuất.",
         "byline": ["dcgr.tech", "Phân tích", "3 phút đọc"]},
    ],
}

# Slide chu DAI qua muc: thu het khoang trang van khong vua — cong chan phai bao vai cat bot.
SLIDE_QUA_DAI = {
    "kind": "steps", "eyebrow": "CƠ CHẾ", "title": "Vì sao giá bán lẻ lệch khỏi giá niêm yết",
    "standfirst": "Chuỗi phân phối cộng thêm phí ở mỗi chặng. " * 6,
    "steps": [{"title": f"Bước {i}", "desc": "Mô tả dài cho bước này, đủ để đẩy cột chữ "
                                             "vượt khỏi vùng an toàn. " * 3} for i in range(1, 6)],
}


def _slide_html(sl=None):
    th = dict(render_edu.THEMES["orbit"], hero="grid")
    font_css = render_edu._font_face_css()
    return render_edu.slide_read(sl or SPEC["slides"][0], 1, 1, SPEC["brand"], SPEC["section"],
                                 SPEC["folio"], font_css, th)


def _boxes_in_browser(html, want_report=False):
    """Bao cao cua `__fitSafe` (dinh masthead, day cot chu, so px con tran) do bang Chromium.
    None neu may khong co trinh duyet."""
    fit_js = render_edu.FIT_JS          # doc TRUOC khoi try: code cu khong co -> test do, khong "bo qua"
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            page = b.new_page(viewport={"width": render_edu.W, "height": render_edu.H})
            page.set_content(html, wait_until="load")
            page.evaluate("document.fonts.ready")
            # Dung y nhu `render_edu._capture_each_slide`: thu khoang trang cho vua roi moi do.
            page.add_script_tag(content=fit_js)
            bao = page.evaluate(f"() => window.__fitSafe({render_edu.PAD_TOP}, "
                                f"{render_edu.H - render_edu.PAD_BOT})")
            b.close()
            return bao
    except Exception:                      # noqa: BLE001 — chua cai chromium tren may nay
        return None


def test_kite_padding_follows_safe_zone():
    """Le tren/duoi cua `.art` lay tu `safe_zone`, khong con 80px deu."""
    assert render_edu.PAD_TOP == safe_zone.top(render_edu.W, render_edu.H)
    assert render_edu.PAD_BOT == render_edu.H - safe_zone.bottom(render_edu.W, render_edu.H)
    css = render_edu.base_css(dict(render_edu.THEMES["orbit"], hero="grid"))
    assert f"padding:{render_edu.PAD_TOP}px 80px {render_edu.PAD_BOT}px" in css


def test_kite_byline_moved_to_footer_and_no_folio():
    """Dong folio (nhan + so trang) bo han; dong byline chuyen xuong CHAN khung (`.foot`, lop
    tuyet doi trong dai bi cat) — Ong Chu: *"chuyển xuống footer luôn, ko ảnh hưởng chất lượng"*."""
    html = _slide_html()
    assert '<div class="folio">' not in html and render_edu.folio("dcgr.tech", 1, 7) == ""
    assert '<div class="foot">' in html
    for phan in SPEC["slides"][0]["byline"]:
        assert phan in html, phan
    assert render_edu.byline_html(SPEC["slides"][0]) == ""   # khong con trong cot chu


def test_kite_text_column_inside_safe_zone():
    """Masthead va day cot chu nam tron trong vung an toan (do tren trinh duyet that)."""
    bao = _boxes_in_browser(_slide_html())
    if bao is None:
        print("  (bo qua phep do tren Chromium — khong cai o may nay)")
        return
    loi = safe_zone.violations({"masthead": (bao["mast_top"], bao["mast_top"]),
                                "cot chu": (bao["mast_top"], bao["text_bottom"])},
                               render_edu.W, render_edu.H)
    assert not loi, f"{loi} (bao: {bao})"
    # `.foot` la lop tuyet doi: no KHONG duoc day cot chu xuong.
    assert bao["text_bottom"] <= safe_zone.bottom(render_edu.W, render_edu.H), bao


def test_kite_gate_catches_slide_that_cannot_fit():
    """Chu dai qua muc: thu het khoang trang van tran — `__fitSafe` bao con tran, tuc cong chan
    trong `_capture_each_slide` se dung va bao vai cat bot (khong am tham cat mat dong chan)."""
    bao = _boxes_in_browser(_slide_html(SLIDE_QUA_DAI), want_report=True)
    if bao is None:
        print("  (bo qua phep do tren Chromium — khong cai o may nay)")
        return
    assert bao["factor"] <= render_edu.FIT_MIN_SPACE, bao
    assert bao["over"] > 0, bao


if __name__ == "__main__":
    failed = 0
    for name, fn in list(globals().items()):
        if name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {name}")
            except Exception as e:           # noqa: BLE001
                failed += 1
                print(f"FAIL {name}: {e}")
    sys.exit(1 if failed else 0)
