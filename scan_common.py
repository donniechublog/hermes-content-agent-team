#!/usr/bin/env python3
"""scan_common.py — thu cac script QUET va script GHI MANIFEST dung chung.

Vi sao co tep nay (06/09/2026, audit dot 1): cung mot viec duoc viet lai o
nhieu cho, va cac ban da bat dau lech nhau.

  - Chuan hoa URL: `scan_sources._norm_url`, `manifest_build._norm`,
    `required` (ham cu `chuan_link`) — ba ban CUNG y dinh, khac thu tu `.lower()` va
    `.strip()`. Ba ban chuan hoa khac nhau nghia la "da thay tin nay chua" tra
    loi khac nhau tuy ai hoi.
  - Tai trang: `scan_models._get` va `scan_business._get`, cung chu thich ve
    brotli, khac moi tham so `params`.
  - User-Agent: nam roi o NAM tep.
  - Ghi JSON nguyen tu: ba ban tmp + replace.
  - Ten hien thi cua vai: hai bang.

Tep nay KHONG chua logic quet — chi nhung manh nho ma moi nguoi deu can. Script
quet nao can thu rieng thi cu giu rieng.
"""
import ipaddress
import re
import socket
from datetime import timedelta, timezone
from email.utils import parsedate_to_datetime
from datetime import datetime

import httpx

# Mot User-Agent duy nhat cho ca doi: bao nao chan thi chan tat, khong phai do
# xem script nao dang bi chan.
UA = "Mozilla/5.0 (compatible; donniechu-scout/1.0)"

VN = timezone(timedelta(hours=7))

# Ten hien thi cua ba vai di tim tin. Truoc day co hai bang (scan_submit.NAME va
# manifest_report.NAME_ROLE) va chung phai nho sua cung luc.
# `vera` la but danh cu cho role `market` — manifest_report van nhan ca hai
# de bao cao cu khong ra "None".
NAME_ROLE = {"finn": "Finn", "nova": "Nova", "vera": "Vera", "qinn": "Qinn"}

# Nguong "dang len bao cao" cua Finn: diem tong = diem CO HOC (script cham: moi +
# lan) + technical (0-30) + relevance (0-20) do vai cham. MOT ban duy nhat, vi
# brief noi nguong nay cho vai doc CON scan_submit lay no de chan dong "hom nay
# khong co gi" (LOW-317) — hai ban lech nhau thi cong chan sai ngay.
SCORE_PASS = 50


# ---------------------------------------------------------------- host noi bo
_HOST_CAM_TEN = re.compile(r"^localhost$|\.(local|internal|netbird\.mated)$", re.I)


def host_say_drop(host: str) -> bool:
    """Host nay co tro vao trong may / mang rieng khong.

    MOT cho duy nhat cho ca doi. Truoc 06/09/2026 chi `article_extract` va
    `approve_command` co cong nay, va ca hai deu so khop bang regex tren CHUOI:
    `127.0.0.1` bi chan nhung `127.1`, `2130706433` (dang thap phan) va
    `[::1]` thi khong. Cac duong tai con lai — anh trong HTML bai bao,
    `page.goto` theo trang tim kiem, `httpx.head` theo chuyen huong,
    `capture_chart` — khong co cong nao.

    Dung `ipaddress` nen bat duoc moi cach viet cua cung mot dia chi. Van
    KHONG resolve DNS: mot ten mien cong khai tro ve 127.0.0.1 se lot, va do
    la gioi han co y (chan tren tung hop, khong phai tuong lua). Bu lai bang
    cach kiem CA sau chuyen huong, nhu article_extract da lam.
    """
    h = (host or "").strip().strip("[]").lower()
    if not h:
        return True
    if _HOST_CAM_TEN.search(h):
        return True
    try:
        ip = ipaddress.ip_address(h)
    except ValueError:
        # Dang rut gon ma `ipaddress` tu choi nhung libc (curl, chromium,
        # httpx qua getaddrinfo) van hieu: "127.1", "2130706433", "0x7f.0.0.1".
        # Day dung la cach vong qua mot bo loc chi so khop chuoi.
        try:
            ip = ipaddress.IPv4Address(socket.inet_aton(h))
        except (OSError, ValueError):
            return False           # ten mien binh thuong
    return (ip.is_loopback or ip.is_private or ip.is_link_local
            or ip.is_reserved or ip.is_multicast or ip.is_unspecified)


def check_url(url, cho: str = "URL") -> None:
    """Nem ValueError neu URL khong phai http/https hoac tro vao mang noi bo."""
    from urllib.parse import urlsplit
    p = urlsplit(str(url))
    if p.scheme not in ("http", "https") or not p.hostname:
        raise ValueError(f"{cho} phai la http/https day du: {str(url)[:120]!r}")
    if host_say_drop(p.hostname):
        raise ValueError(f"{cho} tro vao host noi bo ({p.hostname}) — khong tai.")


def url_hide_whole(url) -> bool:
    """Ban khong nem, cho cac vong loc bo qua URL xau thay vi dung han."""
    try:
        check_url(url)
        return True
    except ValueError:
        return False


def standard_link(u: str) -> str:
    r"""URL ve dang so sanh duoc: bo scheme, bo `www.`, bo query/fragment, bo `/`
    cuoi, ha chu thuong.

    Day la phep so "hai link co phai mot bai khong" cua CA day chuyen — sua o
    day la sua cho moi noi, va do la diem cua tep nay.

    HA CHU THUONG TRUOC roi moi boc scheme. Ban cua `scan_sources`/
    `manifest_build` ha chu o CUOI, ma regex `^https?://(www\.)?` phan biet hoa
    thuong — nen "HTTP://WWW.a.io" khong bi boc scheme va thanh mot khoa khac
    han "a.io". Hai ban do coi cung mot bai la hai bai; ban cua `required` lam
    dung, va day lay theo no.
    """
    from urllib.parse import parse_qsl, urlencode
    u = re.sub(r"^https?://(www\.)?", "", (u or "").strip().lower())
    u = u.split("#", 1)[0]
    duong, _, truy_van = u.partition("?")
    # GIU truy van, chi bo tham so theo doi (sua 06/09/2026 dot 2).
    #
    # Ban cu cat sach `?...`. Tren HackerNews, moi bai Ask/Show HN khong co URL
    # ngoai deu mang link `news.ycombinator.com/item?id=<so>` — cat query la ca
    # NGHIN bai gop ve dung mot khoa `news.ycombinator.com/item`. Hai he qua,
    # ca hai im lang: `scan_sources` thay bai text HN thu hai la "da xu ly" nen
    # bo VINH VIEN, va khoa bat buoc `link|...` trung nen muc thu hai khong bao
    # gio duoc them. `youtube.com/watch?v=` cung so phan.
    giu = [(k, v) for k, v in parse_qsl(truy_van)
           if not k.startswith(("utm_", "fbclid", "gclid", "ref", "oc", "igshid",
                                "mc_cid", "mc_eid", "_hsenc", "_hsmi"))]
    duong = duong.rstrip("/")
    return f"{duong}?{urlencode(sorted(giu))}" if giu else duong


def ask_commons(cau: str, so: int = 20, loai_logo: bool = True):
    """Tim anh bitmap tren Wikimedia Commons. Tra `query.pages` (dict, co the
    rong = KHONG CO anh), hoac None khi HONG VI MOI TRUONG (mang, HTTP, JSON).

    MOT ban cho ba nguoi goi (prepare/source, image_concept, image_brand).
    Truoc audit lượt 2 (ADF-r2-16) cung query nay chep ba lan, va quy uoc C1
    chi ap cho hai: image_brand._ask_commons tra {} khi mat mang, log khong
    co repr — "mat mang" va "hang khong co anh" la mot.

    `loai_logo`: them -intitle:logo -intitle:icon (anh khai niem / thuong hieu);
    nguon.anh_commons tim tru so/san pham nen khong loai (co the la anh co logo
    tren toa nha). Dung UA_WIKI: Wikimedia doi UA co ten cong cu + lien he,
    UA gia trinh duyet la 403 (do 09/09/2026)."""
    import sys as _sys
    tim = f"{cau} filetype:bitmap" + (" -intitle:logo -intitle:icon" if loai_logo else "")
    try:
        r = httpx.get("https://commons.wikimedia.org/w/api.php", params={
            "action": "query", "generator": "search", "gsrsearch": tim,
            "gsrnamespace": 6, "gsrlimit": so, "prop": "imageinfo",
            "iiprop": "url|size|mime", "iiurlwidth": 1800, "format": "json"},
            headers={"User-Agent": env_load.UA_WIKI}, timeout=20)
        r.raise_for_status()
        return r.json().get("query", {}).get("pages", {})
    except Exception as e:                                   # noqa: BLE001
        print(f"[commons] '{cau[:60]}': {type(e).__name__}: {e!r}", file=_sys.stderr)
        return None


def get(url: str, timeout: int = 45, params=None) -> httpx.Response:
    """GET mot trang.

    KHONG xin brotli: may chu cua OpenAI tra ve luong brotli ma bo giai nen cua
    httpx nghen giua chung ("decoder process called with data when
    can_accept_more_data() is False") — feed hong han, khong phai loi encoding.
    Bo 'br' khoi Accept-Encoding thi may chu chuyen sang gzip va doc binh thuong.
    """
    return httpx.get(url, timeout=timeout, follow_redirects=True, params=params,
                     headers={"User-Agent": UA, "Accept-Encoding": "gzip, deflate"})


import env_load                                              # noqa: E402

# Mot ban duy nhat, o env_load (moi script deu da import no).
ghi_json = env_load.write_json


def timestamp_time(txt: str) -> float:
    """Chuoi ngay cua RSS/Atom -> epoch. 0 neu khong doc duoc.

    Hai dinh dang deu gap that: RFC 2822 (`Tue, 02 Sep 2026 10:00:00 GMT`) cua
    RSS va ISO 8601 cua Atom.
    """
    for f in (lambda t: parsedate_to_datetime(t).timestamp(),
              lambda t: datetime.fromisoformat(t.replace("Z", "+00:00")).timestamp()):
        try:
            return f(txt)
        except Exception:                                    # noqa: BLE001
            continue
    return 0.0

# Tu qua chung, bo khi so "hai tieu de co noi cung mot chuyen khong". Truoc
# 06/09/2026 co hai ban: `article_sources.FROM_EMPTY` va mot bo go tay trong
# `article_images` (ham cu `_tu_dac_trung`), khac nhau dung mot tu ("how") — nen cung mot cap tieu
# de co the "cung tin" voi ham nay va "khac tin" voi ham kia.
FROM_EMPTY = {"the", "a", "an", "of", "in", "on", "to", "for", "and", "or", "with",
           "new", "ai", "model", "is", "its", "as", "at", "by", "from", "how"}


def from_distinctive(t: str) -> set:
    """Tu dac trung cua mot tieu de: bo dau cau, bo tu chung, bo tu <= 2 ky tu."""
    return {w for w in re.sub(r"[^\w\s]", " ", (t or "").lower()).split()
            if w not in FROM_EMPTY and len(w) > 2}
