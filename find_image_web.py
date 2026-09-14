#!/usr/bin/env python3
"""TÌM ẢNH WEB như người gõ Google Images — bằng chính Chromium của máy chủ.

Ông Chủ 12/09/2026: *"bạn đâu bị giới hạn bởi cái gì, nếu không thể code nổi một
đoạn mã tìm kiếm hình ảnh cho model thì tôi cũng không biết nên hiểu thế nào"*.
Đo trước khi viết, từ IP máy chủ (Chromium thật, UA Chrome, locale en-US):
  - Google Images: "unusual traffic", 0 ảnh.  DuckDuckGo: trang chủ trống.
  - Bing /images/async: có ảnh nhưng LỆCH ĐỀ 3/5 truy vấn ("Nvidia headquarters"
    → máy bay tàng hình, "Jensen Huang" → cú hoạt hình, "semiconductor
    cleanroom" → mèo) — Bing trả kết quả bot-degraded cho IP này. TẮT.
  - Yandex Images: đúng 6/6 truy vấn (TSMC wafer fab → pcworld/cybernews,
    Nvidia headquarters → Wikimedia, Jensen Huang → CES/Wikimedia, OpenAI Sam
    Altman → TechCrunch). NGUỒN CHÍNH.
Kết quả web xếp SAU og:image báo chí (diem 42) vì có thể lẫn rác cả loạt; vision
vẫn nhìn từng tấm như mọi ảnh khác. Thuần phần bóc/lọc để test được.
"""
import re
import sys
import urllib.parse as up

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")
_ANH_EXT = re.compile(r"\.(jpe?g|png|webp)(\?|$)", re.I)
DROP_DOMAIN_WEB = ("ytimg.com", "pinimg.com", "pikabu.ru", "playground.ru", "slideserve.com",
               "shutterstock.com", "alamy.com", "gettyimages.com", "istockphoto.com",
               "dreamstime.com", "123rf.com", "depositphotos.com")   # stock/watermark/thumb


def _use_ok(u: str) -> bool:
    if not u or not u.startswith("http") or len(u) > 500:
        return False
    if any(b in u for b in DROP_DOMAIN_WEB):
        return False
    return bool(_ANH_EXT.search(u.split("#")[0]))


def bing_murl(html: str) -> list:
    """URL ảnh gốc (murl) từ HTML /images/async: thuộc tính m='{"murl":...}'
    hoặc dạng đã escape &quot;."""
    ra = re.findall(r'"murl":"([^"]+)"', html or "")
    ra += re.findall(r"murl&quot;:&quot;([^&]+)", html or "")
    ra = [u.encode().decode("unicode_escape") if "\\u" in u else u for u in ra]
    return ra


def yandex_img_url(hrefs: list) -> list:
    ra = []
    for h in hrefs or []:
        m = re.search(r"img_url=([^&]+)", h)
        if m:
            ra.append(up.unquote(m.group(1)))
    return ra


def filter(urls: list, so: int, tu: str, q: str) -> list:
    thay, ra = set(), []
    for u in urls:
        if u in thay or not _use_ok(u):
            continue
        thay.add(u)
        # `trang` = chính ảnh: download_filter coi ảnh khác miền trang là quảng cáo,
        # mà kết quả tìm ảnh thì không có "trang" nào cả.
        ra.append({"anh": u, "alt": q, "og": False, "tu": tu, "trang": u,
                   # Duoi og:image bao chi (42): ket qua web co the lac de ca loat
                   # (Bing async tra "tiec tra" cho "TSMC wafer fab", 12/09), khong
                   # duoc chiem het tran tai TOI_DA_TAI cua tai_va_loc.
                   "rong": 0, "cao": 0, "diem": 40 if tu == "web_bing" else 38, "tu_khoa": q})
        if len(ra) >= so:
            break
    return ra


def _bing(page, q: str, so: int) -> list:
    # Ghe trang ket qua that TRUOC (dat ngu canh truy van + cookie), roi moi goi
    # /images/async cung q. Goi async tran tu trang chu, Bing thinh thoang tra
    # ket qua cua truy van KHAC (do 12/09: "semiconductor cleanroom" -> meo).
    page.goto(f"https://www.bing.com/images/search?q={up.quote(q)}&mkt=en-US&setlang=en&form=HDRSC2",
              timeout=30000)
    page.wait_for_timeout(2500)
    ra = bing_murl(page.content())
    page.goto(f"https://www.bing.com/images/async?q={up.quote(q)}&first=0&count=35&mkt=en-US&adlt=off",
              timeout=30000, referer=f"https://www.bing.com/images/search?q={up.quote(q)}")
    page.wait_for_timeout(2000)
    ra += bing_murl(page.content())
    return filter(ra, so, "web_bing", q)


def _yandex(page, q: str, so: int) -> list:
    page.goto(f"https://yandex.com/images/search?text={up.quote(q)}", timeout=30000)
    page.wait_for_timeout(5000)
    hrefs = page.evaluate("() => Array.from(document.querySelectorAll('a[href*=\"img_url=\"]')).map(a => a.href)")
    return filter(yandex_img_url(hrefs), so, "web_yandex", q)


# Bing giu code de bat lai khi IP doi; hien tai lech de 3/5 (xem docstring).
SOURCE = (("Yandex", lambda page, q, so: _yandex(page, q, so)),)


def find_image_web(q: str, so: int = 16, phien=None) -> list:
    """Ứng viên ảnh web cho một truy vấn TIẾNG ANH. [] khi hỏng (đã in lý do)."""
    from browser_session import session_or_new
    ra = []
    with session_or_new(phien) as ph:
        with ph.trang(user_agent=UA, locale="en-US", viewport={"width": 1366, "height": 900}) as page:
            for ten, ham in SOURCE:
                try:
                    kq = ham(page, q, so)
                    print(f"[tim anh web] {ten} '{q}': {len(kq)} ung vien", file=sys.stderr)
                    ra += kq
                except Exception as e:                       # noqa: BLE001
                    print(f"[tim anh web] {ten} '{q}' hong: {type(e).__name__}: {str(e)[:100]}", file=sys.stderr)
                if len(ra) >= so:
                    break
    thay, kq = set(), []
    for c in ra:
        if c["anh"] not in thay:
            thay.add(c["anh"])
            kq.append(c)
    return kq[:so]


if __name__ == "__main__":
    for c in find_image_web(" ".join(sys.argv[1:]) or "TSMC fab"):
        print(c["tu"], c["anh"][:120])
