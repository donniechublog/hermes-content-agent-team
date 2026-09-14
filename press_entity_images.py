#!/usr/bin/env python3
"""ẢNH BÁO CHÍ THEO THỰC THỂ: og:image của các bài báo gần đây VỀ hãng/sản phẩm/
người trong tin — cách một người tìm ảnh bằng tay.

Ông Chủ 12/09/2026, ném 7 link ảnh TSMC (CNBC, tekedia, electronicsweekly,
seekingalpha, 247wallst, kaohoon, watcher.guru): *"một thực tập sinh không có
kỹ năng còn có thể tìm ra từng này hình"*. Tất cả 7 tấm đều là ảnh hero (og:image)
của một bài báo nói về TSMC — KHÔNG phải bài cùng tin. Engine tới lúc đó chỉ có:
báo CÙNG TIN (LOW-33, đúng cho tư liệu nhưng quá hẹp cho ảnh), Commons theo tên
tệp, Openverse. Bing Images từ IP máy chủ trả rác (đo 12/09: "TSMC fab" ra bản đồ
Seoul), DuckDuckGo chặn. Bing News RSS theo TÊN THỰC THỂ thì ra 11 bài/truy vấn,
og:image của chúng đúng là loại ảnh trên.

Thuần phần lọc để test được; mạng chỉ ở `_rss` và `_og`.
"""
import re
import sys
import urllib.parse as up
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

import httpx

import article_sources
import scan_common
from prepare.common import _domain

BING_RSS = "https://www.bing.com/news/search?q={q}&format=rss&mkt={mkt}"
MKT = ("en-US", "en-GB")          # hai thi truong -> hai bo bai khac nhau (do 12/09)
MAX_NEW_DOMAIN = 2               # mot toa soan khong lap ca kho
MAX_ARTICLE = 24
_OG = (re.compile(r"<meta[^>]+(?:property|name)=[\"'](?:og:image|twitter:image)(?::src)?[\"'][^>]*?content=[\"']([^\"']+)", re.I),
       re.compile(r"<meta[^>]+content=[\"']([^\"']+)[\"'][^>]*?(?:property|name)=[\"'](?:og:image|twitter:image)", re.I))


def link_real(link: str) -> str:
    """Link Bing RSS (apiclick.aspx?...&url=<encoded>) -> URL bài thật. Không có
    `url=` thì trả nguyên (đã là link thẳng)."""
    m = re.search(r"[?&]url=([^&]+)", link or "")
    return up.unquote(m.group(1)) if m else (link or "")


def filter_article(items: list, bo_mien: tuple = (), toi_da: int = MAX_ARTICLE) -> list:
    """`items` = [(link, title)] từ RSS (đã hoặc chưa giải url=). Bỏ trùng URL,
    bỏ miền tổng hợp/chặn bot (article_sources.DROP_DOMAIN + bo_mien), tối đa
    MAX_NEW_DOMAIN bài một miền. Giữ thứ tự RSS (mới trước)."""
    ra, thay, dem = [], set(), {}
    for link, title in items:
        u = link_real(link)
        if not u.startswith("http") or u in thay:
            continue
        mien = _domain(u)
        if not mien or any(b in mien for b in article_sources.DROP_DOMAIN + tuple(bo_mien)):
            continue
        if dem.get(mien, 0) >= MAX_NEW_DOMAIN:
            continue
        thay.add(u)
        dem[mien] = dem.get(mien, 0) + 1
        ra.append({"url": u, "tieu_de": (title or "")[:160], "mien": mien})
        if len(ra) >= toi_da:
            break
    return ra


def _rss(q: str, mkt: str) -> list:
    try:
        r = article_sources._download(BING_RSS.format(q=up.quote(q), mkt=mkt), 20)
        return [(it.findtext("link") or "", it.findtext("title") or "")
                for it in ET.fromstring(r.content).findall(".//item")]
    except Exception as e:                                   # noqa: BLE001
        print(f"[bao thuc the] Bing RSS '{q}' ({mkt}) hong: {type(e).__name__}", file=sys.stderr)
        return []


def report_about(tu_khoa: list, bo_mien: tuple = (), toi_da: int = MAX_ARTICLE) -> list:
    """Bài báo gần đây về các từ khoá (mỗi từ khoá × MKT). Trả [{url, tieu_de, mien}]."""
    items = []
    for q in tu_khoa:
        for mkt in MKT:
            items += _rss(q, mkt)
    return filter_article(items, bo_mien, toi_da)


def og_from_html(html: str, url_bai: str) -> str | None:
    for rx in _OG:
        m = rx.search(html or "")
        if m:
            u = m.group(1).strip()
            return up.urljoin(url_bai, u) if not u.startswith("http") else u
    return None


def _og(bai: dict) -> dict | None:
    u = bai["url"]
    if not scan_common.url_hide_whole(u):
        return None
    try:
        r = httpx.get(u, headers=article_sources.HDR, timeout=12, follow_redirects=True)
        if r.status_code != 200:
            print(f"[bao thuc the] {bai['mien']}: HTTP {r.status_code}", file=sys.stderr)
            return None
        im = og_from_html(r.text[:400_000], str(r.url))
        if not im or not scan_common.url_hide_whole(im):
            return None
        return {"anh": im, "alt": bai["tieu_de"], "og": True, "tu": "bao_thuc_the",
                # `trang` = chính ảnh: og:image gần như luôn nằm trên CDN khác
                # miền bài (image.cnbcfm.com / cnbc.com) và download_filter coi "khác
                # miền" là quảng cáo; bài gốc giữ ở `bai` để truy nguồn.
                "trang": im, "bai": u, "mien_bai": bai["mien"], "rong": 0, "cao": 0, "diem": 42}
    except Exception as e:                                   # noqa: BLE001
        print(f"[bao thuc the] {bai['mien']}: {type(e).__name__}", file=sys.stderr)
        return None


def press_entity_images(tu_khoa: list, bo_mien: tuple = (), so_anh: int = 12) -> list:
    """Ứng viên ảnh (og:image) từ báo chí về các từ khoá. [] khi không ra gì."""
    bai = report_about(tu_khoa, bo_mien)
    print(f"[bao thuc the] {len(bai)} bài về {tu_khoa}: "
          + ", ".join(sorted({b['mien'] for b in bai})), file=sys.stderr)
    if not bai:
        return []
    with ThreadPoolExecutor(max_workers=8) as ex:
        ra = [c for c in ex.map(_og, bai) if c]
    thay, kq = set(), []
    for c in ra:
        if c["anh"] in thay:
            continue
        thay.add(c["anh"])
        kq.append(c)
    print(f"[bao thuc the] {len(kq)} og:image / {len(bai)} bài", file=sys.stderr)
    return kq[:so_anh]
