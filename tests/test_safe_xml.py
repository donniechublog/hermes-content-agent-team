#!/usr/bin/env python3
"""Cổng chặn parse XML từ bên ngoài mà không qua defusedxml (LOW-303).

Feed RSS/Atom (Google News, Bing News, feed tòa soạn) là dữ liệu của người lạ. `xml.etree`
không chặn thực thể lồng nhau ("billion laughs"), nên một feed độc có thể làm treo hoặc ngốn
hết RAM tiến trình research. Các test dưới giữ ba điều: (1) `safe_xml.fromstring` từ chối
khai báo thực thể và tham chiếu ngoài, không phình ra; (2) thiếu defusedxml thì rơi về
`xml.etree` kèm MỘT dòng cảnh báo, không chết; (3) không ai lén quay lại `ET.fromstring`
trực tiếp trong mã.

Gói tải bomb ở đây có CHẶN kích thước (4 tầng x 10 = 10^4 lần "lol") — nếu defusedxml hỏng
mà để nó phình ra thì test vẫn không ăn hết máy.

Chạy:  venv/bin/python tests/test_safe_xml.py
"""
import contextlib
import importlib.util
import io
import os
import re
import sys
import time
import types
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import safe_xml                                                  # noqa: E402

RSS = (b'<?xml version="1.0" encoding="UTF-8"?><rss><channel><item><title>Hello</title>'
       b'<link>https://a.example/1</link></item></channel></rss>')


def _bomb(levels: int = 4) -> bytes:
    """Thực thể lồng nhau đúng dạng "billion laughs", nhưng chặn ở 10**levels lần "lol"."""
    decl = ['<!ENTITY e0 "lol">']
    for n in range(1, levels + 1):
        decl.append(f'<!ENTITY e{n} "' + f"&e{n - 1};" * 10 + '">')
    return (f'<?xml version="1.0"?><!DOCTYPE lolz [{"".join(decl)}]><rss><channel><item>'
            f'<title>&e{levels};</title></item></channel></rss>').encode()


def _has_defusedxml() -> bool:
    return importlib.util.find_spec("defusedxml") is not None


def _skip_without_defusedxml() -> bool:
    """True (và in dòng SKIP) khi máy này chưa cài defusedxml — máy dev/venv máy chủ trước khi cài.
    CI luôn có (requirements.lock), `test_ci_has_defusedxml` bắt trường hợp lock thiếu."""
    if _has_defusedxml():
        return False
    print("     SKIP: chưa cài defusedxml ở máy này (đường thật chỉ chạy được khi có nó)")
    return True


def test_parses_a_feed_like_plain_etree():
    root = safe_xml.fromstring(RSS)
    assert [i.findtext("title") for i in root.findall(".//item")] == ["Hello"]
    assert [i.findtext("link") for i in root.findall(".//item")] == ["https://a.example/1"]
    assert isinstance(root, ET.Element), "phải là Element thường của xml.etree để chỗ gọi không đổi gì"
    same = ET.fromstring(RSS)
    assert ET.tostring(root) == ET.tostring(same)


def test_accepts_str_and_bytes():
    assert safe_xml.fromstring("<a><b>x</b></a>").findtext("b") == "x"
    assert safe_xml.fromstring(b"<a><b>y</b></a>").findtext("b") == "y"


def test_malformed_xml_still_raises_parse_error():
    try:
        safe_xml.fromstring(b"<rss><channel><item></rss>")
    except ET.ParseError:
        return
    raise AssertionError("XML hỏng phải ném ParseError như xml.etree")


def test_dtd_without_entities_still_parses():
    root = safe_xml.fromstring(b'<?xml version="1.0"?><!DOCTYPE rss><rss><channel><item><title>T</title></item></channel></rss>')
    assert root.findtext(".//title") == "T"


def test_entity_bomb_is_refused_not_expanded():
    if _skip_without_defusedxml():
        return
    t0 = time.monotonic()
    try:
        safe_xml.fromstring(_bomb())
    except Exception as e:                                       # noqa: BLE001
        assert type(e).__name__ == "EntitiesForbidden", f"ném {type(e).__name__} chứ không phải EntitiesForbidden: {e}"
        assert isinstance(e, ValueError), "DefusedXmlException là ValueError — chỗ gọi `except Exception` bắt được"
    else:
        raise AssertionError("bomb thực thể lồng nhau phải bị từ chối, không được parse xong")
    assert time.monotonic() - t0 < 2, "từ chối phải tức thì, không phải sau khi phình ra"


def test_external_entity_is_refused():
    if _skip_without_defusedxml():
        return
    payload = b'<?xml version="1.0"?><!DOCTYPE r [<!ENTITY x SYSTEM "file:///etc/passwd">]><r>&x;</r>'
    try:
        safe_xml.fromstring(payload)
    except Exception as e:                                       # noqa: BLE001
        assert type(e).__name__ in ("EntitiesForbidden", "ExternalReferenceForbidden"), type(e).__name__
    else:
        raise AssertionError("thực thể tham chiếu ngoài phải bị từ chối")


def test_fallback_warns_once_and_still_parses():
    real_backend, real_warned = safe_xml._backend, safe_xml._WARNED
    safe_xml._backend, safe_xml._WARNED = (lambda: None), False        # giả lập "chưa cài defusedxml"
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            a = safe_xml.fromstring(RSS)
            b = safe_xml.fromstring(RSS)
    finally:
        safe_xml._backend, safe_xml._WARNED = real_backend, real_warned
    assert a.findtext(".//title") == b.findtext(".//title") == "Hello"
    assert err.getvalue().count("THIEU defusedxml") == 1, err.getvalue()


def test_ci_has_defusedxml():
    """Không có test này thì CI thiếu defusedxml chỉ chạy đường dự phòng mà vẫn xanh (cùng lớp
    lỗi ở tests/test_requirements_lock.py): GitHub đặt CI=true, và lock phải ghim defusedxml."""
    if not os.environ.get("CI"):
        return
    assert _has_defusedxml(), "CI không có defusedxml — requirements.lock thiếu dòng defusedxml=="


def test_a_refused_feed_is_skipped_by_the_call_site():
    """Một call site thật (Bing RSS ở press_entity_images) gặp feed độc thì trả [] chứ không ném/treo."""
    if _skip_without_defusedxml():
        return
    import article_sources
    import press_entity_images
    real = article_sources._download
    article_sources._download = lambda *a, **k: types.SimpleNamespace(content=_bomb(), status_code=200)
    err = io.StringIO()
    try:
        with contextlib.redirect_stderr(err):
            ra = press_entity_images._rss("nvidia", "en-US")
    finally:
        article_sources._download = real
    assert ra == [], ra
    assert "EntitiesForbidden" in err.getvalue(), err.getvalue()


def test_no_direct_etree_parse_of_outside_xml():
    """Ai viết lại `ET.fromstring(` ở mã sản xuất là mở lại lỗ hổng: chỉ safe_xml.py được đụng xml.etree."""
    skip_dirs = {"tests", "venv", ".claude", "docs", "state", "drafts", "__pycache__", ".git"}
    pattern = re.compile(r"\b(?:ET|ElementTree)\.(?:fromstring|XML|parse|iterparse)\(|\bminidom\b|\bxml\.sax\b")
    bad = []
    for path in sorted(ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT)
        if rel.parts[0] in skip_dirs or rel.parts[:2] == ("hermes", "plugins") or rel.name == "safe_xml.py":
            continue
        for n, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if pattern.search(line) and not line.lstrip().startswith("#"):
                bad.append(f"{rel}:{n}: {line.strip()[:90]}")
    assert not bad, "parse XML trực tiếp bằng xml.etree — dùng safe_xml.fromstring:\n  " + "\n  ".join(bad)


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bắt cả Exception, luôn in N/M
    chay_tat_ca(globals())
