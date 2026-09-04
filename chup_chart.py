#!/usr/bin/env python3
"""Chup chart / bang benchmark: FULL CHIEU RONG truoc, chieu cao xet sau.

Luat Ong Chu 04/09/2026. Be ngang cua mot chart la NOI DUNG: truc, nhan chuoi,
cot cuoi cua bang, cai bubble duoc to sang ma ca bai dang noi toi. Cat mot phan
be ngang thi thu con lai khong phai thieu mot ti — no NOI SAI. Chieu cao thi
khac: cat bot mep tren/duoi mot chart thuong chi mat khoang tho.

Bia "Gemini 3.8 Flash" 04/09/2026 lot luoi dung kieu nay: anh chup mat nua phai,
mat "GLM 5.3", mat "Muse Spark 1.2" va mat luon diem Gemini duoc to sang.

Vi sao can mot script rieng thay vi "nho chup cho rong": mac dinh cua moi cong
cu chup deu la mot khung nho san (screenshot.js cua repo nay dat 820px), va mot
chart rong 1400px trong khung do hoac bi cat, hoac bi trang reflow xuong cho
chat cung. Script nay do BE NGANG THAT cua phan tu roi NOI KHUNG cho vua, chup
xong con do lai anh ra de chac la khong mat mot cot nao.

Dung:
    venv/bin/python chup_chart.py --url <trang> --ra chart.png
    venv/bin/python chup_chart.py --url <trang> --chon "figure.chart" --ra chart.png
    venv/bin/python chup_chart.py --url <link anh truc tiep> --ra chart.png

Can playwright + chromium (giong render_edu.py):
    venv/bin/pip install playwright && venv/bin/playwright install chromium
"""
import argparse
import sys
from pathlib import Path

# Khung mo dau. Rong ngay tu dau de trang khong reflow xuong bo cuc dien thoai:
# bo cuc dien thoai xep chart thanh cot doc, chu be lai, va luc do co chup dung
# be ngang thi cung khong con la cai chart tren desktop nua.
RONG_DAU = 1920
RONG_TOI_DA = 4200            # tran an toan: qua nguong nay chromium ton bo nho
DPR = 2                       # net gap doi, du cho khung the 1200px
CAO_CANH_BAO = 3.0            # cao hon 3 lan be ngang thi bao de nguoi chon


def khung_can(rong_that: float, rong_hien: int) -> int:
    """Be ngang khung can de phan tu hien TRON VEN.

    Tach rieng ra khoi phan trinh duyet de test duoc bang so, khong can chromium.
    Tra ve be ngang moi (>= `rong_hien`), da cong le va da chan tran.
    """
    if rong_that <= rong_hien:
        return rong_hien
    # Cong mot chut le: nhieu trang co padding/scrollbar an mat vai chuc pixel,
    # do sat khit thi lan chup lai van thieu dung mep phai.
    return min(RONG_TOI_DA, int(rong_that) + 80)


def _la_anh(url: str) -> bool:
    duoi = url.split("?")[0].rsplit(".", 1)
    return len(duoi) == 2 and duoi[1].lower() in {
        "png", "jpg", "jpeg", "webp", "gif", "avif"}


def tai_anh(url: str, ra: Path) -> bool:
    """Link tro thang vao mot tam anh: tai NGUYEN BAN, khong resize, khong crop.
    Do la ban day du nhat co the co — moi buoc xu ly them chi lam mat pixel."""
    import urllib.request
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=45) as r:
        data = r.read()
    if not data:
        return False
    ra.parent.mkdir(parents=True, exist_ok=True)
    ra.write_bytes(data)
    return True


# Thu tu tim phan tu chart khi khong co --chon. Dat svg/canvas len truoc <img>:
# chart hien dai thuong la svg, va tren cung trang con co logo/avatar la <img>.
CHON_MAC_DINH = ["figure", "svg", "canvas", "table", "img", "picture"]

DO_JS = """
(sels) => {
  let tot = null;
  for (const s of sels) {
    for (const el of document.querySelectorAll(s)) {
      const r = el.getBoundingClientRect();
      // scrollWidth bat ca phan bi tran ra ngoai khung nhin — dung cai do lam
      // "be ngang that", khong dung be ngang dang hien.
      const w = Math.max(el.scrollWidth || 0, r.width);
      const h = Math.max(el.scrollHeight || 0, r.height);
      if (w < 320 || h < 200) continue;              // logo, icon, spacer
      if (!tot || w * h > tot.w * tot.h) tot = {sel: s, w, h};
    }
    if (tot) break;                                   // uu tien theo thu tu sels
  }
  const de = document.documentElement;
  return tot || {sel: null, w: de.scrollWidth, h: de.scrollHeight};
}
"""


def chup(url: str, ra: Path, chon: str = "", rong_dau: int = RONG_DAU) -> int:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit("Thieu playwright. Cai: venv/bin/pip install playwright && "
                 "venv/bin/playwright install chromium")

    ra.parent.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--no-sandbox", "--disable-dev-shm-usage",
                                    "--force-color-profile=srgb"])
        try:
            ctx = b.new_context(viewport={"width": rong_dau, "height": 1400},
                                device_scale_factor=DPR)
            page = ctx.new_page()
            page.goto(url, wait_until="networkidle", timeout=60000)
            page.wait_for_timeout(1500)          # font + animation cua chart

            do = page.evaluate(DO_JS, [chon] if chon else CHON_MAC_DINH)
            rong_moi = khung_can(do["w"], rong_dau)
            if rong_moi > rong_dau:
                # NOI KHUNG chu khong cat anh. Phai tai lai: nhieu chart do be
                # ngang mot lan luc dung roi ve theo so do, resize khong ve lai.
                print(f"[noi khung] {rong_dau} -> {rong_moi}px cho vua chart "
                      f"rong {do['w']:.0f}px", file=sys.stderr)
                ctx.close()
                ctx = b.new_context(viewport={"width": rong_moi, "height": 1400},
                                    device_scale_factor=DPR)
                page = ctx.new_page()
                page.goto(url, wait_until="networkidle", timeout=60000)
                page.wait_for_timeout(1500)
                do = page.evaluate(DO_JS, [chon] if chon else CHON_MAC_DINH)

            el = page.query_selector(do["sel"]) if do["sel"] else None
            if el:
                el.scroll_into_view_if_needed()
                page.wait_for_timeout(400)
                el.screenshot(path=str(ra))
            else:
                page.screenshot(path=str(ra), full_page=True)
        finally:
            b.close()

    # DO LAI ANH RA. Day moi la cho bat loi that: neu be ngang anh chup con nho
    # hon be ngang that cua phan tu (nhan DPR) thi da mat mot phan ben phai —
    # dung cai loi ma ca script nay sinh ra de chan.
    from PIL import Image
    with Image.open(ra) as im:
        w, h = im.size
    can = int(do["w"] * DPR * 0.98)          # 2% dung sai cho bo tron/vien
    if w < can:
        sys.exit(f"CHUP THIEU BE NGANG: anh ra {w}px, chart rong {can}px. "
                 "Mat phan ben phai — dung tam nay. Thu lai voi --chon tro dung "
                 "phan tu chart, hoac --rong lon hon.")
    print(f"{w}x{h} (DPR {DPR}) -> {ra}", file=sys.stderr)
    if h > w * CAO_CANH_BAO:
        print(f"[canh bao] anh RAT CAO ({h/w:.1f} lan be ngang). Be ngang da du; "
              "chieu cao thi duoc phep cat — cat bot mep tren/duoi bang "
              "crop_ti_le.py (no chi chan cat BE NGANG).", file=sys.stderr)
    return 0


def main():
    ap = argparse.ArgumentParser(
        description="Chup chart/bang benchmark full chieu rong (chieu cao xet sau)")
    ap.add_argument("--url", required=True, help="Trang chua chart, hoac link anh truc tiep")
    ap.add_argument("--ra", required=True, help="Tep .png ra")
    ap.add_argument("--chon", default="", help="CSS selector cua phan tu chart "
                                               "(khong co thi tu tim phan tu lon nhat)")
    ap.add_argument("--rong", type=int, default=RONG_DAU,
                    help=f"Be ngang khung mo dau (mac dinh {RONG_DAU}); script tu noi "
                         "them neu chart rong hon")
    a = ap.parse_args()
    ra = Path(a.ra)
    if _la_anh(a.url):
        # Link anh truc tiep: ban goc luon day du hon moi ban chup lai.
        if tai_anh(a.url, ra):
            from PIL import Image
            with Image.open(ra) as im:
                print(f"{im.size[0]}x{im.size[1]} (tai nguyen ban) -> {ra}", file=sys.stderr)
            return 0
        sys.exit(f"Tai khong duoc {a.url}")
    return chup(a.url, ra, a.chon, a.rong)


if __name__ == "__main__":
    sys.exit(main())
