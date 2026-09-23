#!/usr/bin/env python3
"""LOW-345: kicker (dòng đầu khối chữ) phải đọc được trên ảnh sáng phủ xuống sau chữ.

Đo thật 21/09/2026 (theme ink, chữ kicker xanh nhạt 143,179,255), tương quan WCAG kicker/nền
quanh chữ, trước khi sửa:

  Pirate Face đường ảnh chụp   1,09   (dải phủ bắt đầu ĐÚNG mép trên khối chữ, mà kicker là
  bảng benchmark DeepSeek      1,29    dòng đầu nên nằm ở chỗ độ phủ ~0)
  TSMC / banner cookie         3,4 / 6,9

Sau khi dời dải phủ lên VEIL_LEAD px: 6,8 – 8,0. Bìa Qwen (ảnh bảng nền phẳng) là cơ chế khác:
ảnh chỉ tan dần ở 63% khung, khối chữ dài bắt đầu sớm hơn (778px) nên hàng bảng lọt ra sau
kicker; giờ ảnh phẳng kết thúc TRÊN dòng chữ đầu (`FLAT_TEXT_GAP`).

Chạy:  venv/bin/python tests/test_low345_kicker_contrast.py
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import render_edu as re_                                      # noqa: E402
import tam  # noqa: E402

LONG_TITLE = "Kế hoạch bảo tồn trọng số mở của nhiều mô hình lớn"
LONG_STAND = ("Hình ảnh cướp biển đại diện cho triết lý chia sẻ ngang hàng tự do không thể bị kiểm duyệt, "
              "kèm cam kết lưu trữ phân tán trên nhiều máy chủ độc lập ở nhiều quốc gia khác nhau.")
CARDS = [{"num": "01", "text": "Trọng số được băm và lưu trên mạng ngang hàng."},
         {"num": "02", "text": "Không một bên nào có thể gỡ bỏ."}]


def _light_photo(w=1200, h=1500):
    """Ảnh SÁNG kiểu ảnh chụp: mép lốm đốm (=> 'mo', không phẳng), cao hơn vùng trên chữ."""
    import random
    from PIL import Image
    random.seed(4)
    im = Image.new("RGB", (w, h))
    px = im.load()
    for y in range(h):
        for x in range(w):
            v = 205 + random.randint(-45, 45)
            px[x, y] = (v, v, min(255, v + 8))
    tmp = Path(tam.temp_dir()) / "light.png"
    im.save(tmp)
    return tmp


def _flat_table(w=1200, h=1500):
    """Bảng nền TRẮNG PHẲNG có hàng đỏ dày suốt chiều cao (đỏ để tách khỏi chữ kicker xanh)."""
    from PIL import Image, ImageDraw
    im = Image.new("RGB", (w, h), (255, 255, 255))
    d = ImageDraw.Draw(im)
    for y in range(60, h, 70):
        d.rectangle((60, y, w - 60, y + 30), fill=(220, 30, 30))
    tmp = Path(tam.temp_dir()) / "table.png"
    im.save(tmp)
    return tmp


def _render(image, long_text=False):
    """-> (png slide 4, y đỉnh khối chữ đo bằng Chromium)."""
    import kite_submit as ks
    fig = {"kind": "figure", "eyebrow": "BIỂU TƯỢNG", "title": LONG_TITLE if long_text else "Logo mới",
           "standfirst": LONG_STAND if long_text else "Biểu tượng mới.", "image": str(image)}
    if long_text:
        fig["cards"] = CARDS
    slides = [{"kind": "cover", "eyebrow": "A", "title": "Bìa test", "standfirst": "s", "byline": ["b"]},
              {"kind": "statement", "eyebrow": "B", "title": "Hai", "standfirst": "s",
               "cards": [{"num": "01", "text": "x"}]},
              {"kind": "steps", "eyebrow": "C", "title": "Ba", "steps": [{"title": "t", "desc": "d"}]},
              fig,
              {"kind": "loop", "eyebrow": "D", "title": "Năm", "standfirst": "s", "chips": ["a", "b"], "callout": "c"},
              {"kind": "cta", "eyebrow": "E", "title": "Sáu", "checks": ["a", "b"]}]
    spec = {"brand": "donniechublog", "section": "TEST", "folio": "TEST", "theme": "ink", "hero": "orbit",
            "slides": slides}
    d = Path(tam.temp_dir())
    (d / "spec.json").write_text(json.dumps(spec, ensure_ascii=False), encoding="utf-8")
    r = subprocess.run([sys.executable, str(ROOT / "render_edu.py"), "--spec", str(d / "spec.json"),
                        "--out", str(d / "s.png"), "--brand", "donniechublog", "--theme", "ink",
                        "--bo-qua-dau", "--scale", "1"], capture_output=True, text=True, encoding="utf-8")
    assert r.returncode == 0, r.stderr[-400:]
    return d / "s_4.png", ks.measure_text_tops(spec, "donniechublog")[4]


def _lum(c):
    def f(v):
        v /= 255
        return v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4
    return 0.2126 * f(c[0]) + 0.7152 * f(c[1]) + 0.0722 * f(c[2])


def _kicker_contrast(png, top, accent):
    """Tương quan WCAG giữa màu kicker và NỀN NGAY QUANH nét chữ (vòng 3–6px quanh pixel chữ)."""
    from PIL import Image, ImageFilter, ImageStat
    im = Image.open(png).convert("RGB")
    y0 = int(top)
    reg = im.crop((60, y0, 460, y0 + 36))
    mask = Image.new("L", reg.size, 0)
    src, dst = reg.load(), mask.load()
    for y in range(reg.size[1]):
        for x in range(reg.size[0]):
            p = src[x, y]
            if sum(abs(p[k] - accent[k]) for k in range(3)) < 60:
                dst[x, y] = 255
    assert ImageStat.Stat(mask).sum[0] / 255 > 50, "không thấy chữ kicker trong vùng đo"
    wide = mask.filter(ImageFilter.MaxFilter(11)).point(lambda v: 255 if v else 0)
    near = mask.filter(ImageFilter.MaxFilter(5)).point(lambda v: 255 if v else 0)
    ring = Image.eval(wide, lambda v: v)
    ring.paste(0, mask=near)
    bg = ImageStat.Stat(reg, mask=ring).median
    hi, lo = sorted((_lum(accent), _lum(bg)), reverse=True)
    return (hi + 0.05) / (lo + 0.05)


def test_veil_ramp_starts_above_the_first_text_line():
    """Dải phủ bắt đầu VEIL_LEAD px TRƯỚC dòng chữ đầu và kín trước khi hết dòng kicker."""
    assert re_.VEIL_LEAD > 0
    nen, _ = re_.image_make_background({"image": str(_light_photo())}, dict(next(iter(re_.THEMES.values())),
                                                                              hero=None), "figure")
    assert f"top-{re_.VEIL_LEAD}" in nen and f"top+{re_.VEIL_SPAN}-{re_.VEIL_LEAD}" in nen, nen[-700:]
    assert re_.VEIL_SPAN - re_.VEIL_LEAD <= 24, "dải phủ phải kín trong nửa đầu dòng kicker"


def test_kicker_readable_on_light_photo():
    accent = tuple(int(re_.THEMES["ink"]["a"].lstrip("#")[k:k + 2], 16) for k in (0, 2, 4))
    png, top = _render(_light_photo())
    c = _kicker_contrast(png, top, accent)
    assert c >= 4.5, f"kicker tương quan {c:.2f} < 4.5 trên ảnh sáng (trước sửa: 1,09)"


def test_flat_table_ends_above_first_text_line():
    """Bảng nền phẳng + khối chữ dài: hàng bảng (đỏ) không được lọt vào dòng kicker/tiêu đề."""
    png, top = _render(_flat_table(), long_text=True)
    from PIL import Image
    im = Image.open(png).convert("RGB")
    bad = 0
    for y in range(int(top) - 6, int(top) + 60):
        for x in range(0, im.size[0], 3):
            p = im.getpixel((x, y))
            if p[0] - p[1] > 40 and p[0] > 150:                 # ám đỏ của hàng bảng
                bad += 1
    assert top < 850 - 60, f"khối chữ lẽ ra phải bắt đầu sớm hơn 63% khung, đo được {top}"
    assert bad == 0, f"{bad} pixel hàng bảng lọt vào vùng chữ (đỉnh chữ y={top})"


def test_flat_branch_carries_trim_script():
    """Nhánh phẳng phải có script cắt ảnh ở dòng chữ đầu (renderer gọi window.__datMan)."""
    from PIL import Image
    p = Path(tam.temp_dir()) / "flat.png"
    Image.new("RGB", (1200, 1500), (255, 255, 255)).save(p)
    nen, _ = re_.image_make_background({"image": str(p)}, dict(next(iter(re_.THEMES.values())), hero=None),
                                        "figure")
    assert "window.__datMan" in nen and f"-{re_.FLAT_TEXT_GAP}" in nen


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
