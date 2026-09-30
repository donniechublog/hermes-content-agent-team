#!/usr/bin/env python3
"""LOW-438 — cổng SSRF cho trình duyệt và urllib.

`scan_common.host_say_drop` mới chỉ phủ các đường httpx. Còn lọt:

  * `page.goto` của `capture_page` (URL do vai Bob nộp) và `prepare/browser`
    (đi theo link Google News sang bất kỳ đâu) — cả hai mở trang qua
    `BrowserSession.page`, nên cổng đặt ở đó;
  * `get_source.download` / `main` của skill url-mascot-frame — urlopen nhận cả
    `file://` (og:image do trang nguồn tự khai);
  * `article_extract.fetch` kiểm chuyển hướng SAU khi đi hết chuỗi — request tới
    127.0.0.1 đã đi rồi mới bị chặn.

Test dùng Chromium THẬT (CI cài sẵn `playwright install chromium`) với một server
cục bộ 127.0.0.1 đếm từng request nó nhận: "bị chặn" nghĩa là server KHÔNG nhận
được, không phải chỉ là có ngoại lệ. Host "công khai" giả lập bằng
`--host-resolver-rules=MAP pub.example 127.0.0.1` — tên này qua `host_say_drop`
(không resolve DNS, giới hạn có ý) nhưng lại tới đúng server test.

Chay:  venv/bin/python tests/test_low438_ssrf_browser_gate.py
"""
import atexit
import http.server
import socket
import sys
import threading
from contextlib import contextmanager
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import article_extract          # noqa: E402
import browser_session          # noqa: E402
import capture_page             # noqa: E402
import scan_common              # noqa: E402
import tam                      # noqa: E402

GET_SOURCE_DIR = ROOT / "hermes" / "skills" / "url-mascot-frame" / "scripts"
sys.path.insert(0, str(GET_SOURCE_DIR))
import get_source               # noqa: E402

PUBLIC = "pub.example"          # "host cong khai" gia lap, tro ve server test


# ------------------------------------------------------------------ server test
@contextmanager
def _server():
    """Server 127.0.0.1 ghi lai MOI duong dan no nhan. Trang /page nhung anh +
    iframe noi bo; /redir 302 ve 127.0.0.1; /jsnav tu dieu huong bang JS."""
    hits = []

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *_a):
            pass

        def do_GET(self):
            hits.append(self.path)
            port = self.server.server_address[1]
            if self.path == "/redir":
                self.send_response(302)
                self.send_header("Location", f"http://127.0.0.1:{port}/secret-redirect")
                self.end_headers()
                return
            if self.path == "/page":
                body = (f'<html><body><h1>trang cong khai</h1>'
                        f'<img src="http://127.0.0.1:{port}/secret-img.png">'
                        f'<iframe src="http://localhost:{port}/secret-frame"></iframe>'
                        f'</body></html>')
            elif self.path == "/jsnav":
                body = (f'<html><body><script>location.href='
                        f'"http://127.1:{port}/secret-jsnav"</script></body></html>')
            else:
                body = "<html><body>noi bo</body></html>"
            data = body.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    try:
        yield srv.server_address[1], hits
    finally:
        srv.shutdown()
        srv.server_close()


def _secret(hits):
    return [h for h in hits if h.startswith("/secret")]


# ------------------------------------------------------------ phien Chromium test
_MAP_PUBLIC = f"MAP {PUBLIC} 127.0.0.1"


class _PublicHostSession(browser_session.BrowserSession):
    """BrowserSession that, chi them anh xa `pub.example` -> 127.0.0.1.

    Chromium chi doc MOT `--host-resolver-rules` (cai cuoi) nen luat cua test
    phai ghep vao dau luat chan noi bo cua phien (neu co) — MAP dau tien khop
    thi thang, nen pub.example van toi server con 127.x thi van bi chan."""

    def browser(self, args=browser_session.ARGS_DEFAULT):
        return super().browser(tuple(args) + ("--host-resolver-rules=" + _MAP_PUBLIC,))


_SHARED = []


@contextmanager
def _session():
    """MOT phien cho ca tep: dong Chromium ton 5-30s tren may dev."""
    if not _SHARED:
        goc = getattr(browser_session, "ARG_BLOCK_INTERNAL", None)
        ghep = (goc.replace("--host-resolver-rules=", f"--host-resolver-rules={_MAP_PUBLIC}, ", 1)
                if goc else "--host-resolver-rules=" + _MAP_PUBLIC)
        ph = _PublicHostSession()
        with mock.patch.object(browser_session, "ARG_BLOCK_INTERNAL", ghep, create=True):
            ph.browser()                    # launch NGAY khi luat test con hieu luc
        atexit.register(ph.close)
        _SHARED.append(ph)
    yield _SHARED[0]


def _goto(page, url):
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=10000)
        return None
    except Exception as e:                                   # noqa: BLE001
        return str(e)


def _text(page):
    """Chu nhin thay cua trang; trang loi Chromium co the con dang dieu huong."""
    for _ in range(10):
        try:
            return page.evaluate("document.body ? document.body.innerText : ''") or ""
        except Exception:                                    # noqa: BLE001
            page.wait_for_timeout(200)
    return ""


# ---------------------------------------------------------------- ham thuan
def test_request_allowed_blocks_internal_and_non_http():
    chan = ["http://127.0.0.1:9130/", "http://127.1:20128/v1", "http://2130706433/",
            "http://localhost:9130/", "http://x.localhost/", "http://[::1]/",
            "http://169.254.169.254/latest/meta-data/", "http://100.87.121.46:9130/",
            "http://10.0.0.5/", "file:///etc/passwd", "ftp://x.com/a", "http://[::1/"]
    lot = [u for u in chan if browser_session.request_allowed(u)]
    assert not lot, f"lot cong: {lot}"
    cho = ["https://example.com/a.jpg", "http://news.ycombinator.com/item?id=1",
           "data:image/png;base64,iVBOR", "blob:https://example.com/uuid",
           "https://100.128.0.1/", "https://fdic.gov/", "https://fcbarcelona.com/"]
    oan = [u for u in cho if not browser_session.request_allowed(u)]
    assert not oan, f"chan oan: {oan}"


def test_host_say_drop_covers_localhost_subdomain_and_cgnat():
    """`*.localhost` (Chromium/systemd-resolved tra ve 127.0.0.1) va dai CGNAT
    netbird (journal_web 100.87.121.46:9130) — `ipaddress` khong coi la private."""
    for h in ("x.localhost", "100.64.0.1", "100.87.212.236", "100.127.255.255"):
        assert scan_common.host_say_drop(h), h
    for h in ("100.63.255.255", "100.128.0.1", "example.localhost.com"):
        assert not scan_common.host_say_drop(h), h


def test_resolver_rules_do_not_match_ordinary_domains():
    """Luat lop 2 khop theo MAU ten: mau IPv6 kieu `fd*` se nuot fdic.gov."""
    import fnmatch
    mau = browser_session._RESOLVER_BLOCK
    for ten in ("fdic.gov", "fcbarcelona.com", "fe80.com", "10.com", "0.xyz", "127.io",
                "example.com", "news.google.com"):
        khop = [m for m in mau if fnmatch.fnmatchcase(ten, m)]
        assert not khop, f"{ten} khop nham {khop}"


# -------------------------------------------------------- Chromium that
def test_capture_page_never_reaches_internal_host():
    """URL Bob nop tro thang vao 127.0.0.1 (capture_page.py:46)."""
    out = tam.temp_dir(prefix="low438_") / "a.png"
    with _server() as (port, hits), _session() as ph:
        capture_page.capture(f"http://127.0.0.1:{port}/secret-direct", out, phien=ph)
        capture_page.capture_lead_mobile(f"http://localhost:{port}/secret-lead", out, phien=ph)
    assert not _secret(hits), f"Chromium van toi host noi bo: {hits}"


def test_public_page_loads_but_internal_subresources_do_not():
    """Trang cong khai van mo duoc (khong chan oan), nhung anh/iframe trong trang
    tro vao 127.0.0.1/localhost bi huy."""
    out = tam.temp_dir(prefix="low438_") / "b.png"
    with _server() as (port, hits), _session() as ph:
        ok = capture_page.capture(f"http://{PUBLIC}:{port}/page", out, phien=ph)
    assert "/page" in hits, f"trang cong khai bi chan oan: {hits}"
    assert ok and out.exists()
    assert not _secret(hits), f"tai nguyen con toi host noi bo: {hits}"


def test_http_redirect_to_internal_is_blocked():
    """Playwright KHONG goi route cho buoc chuyen huong HTTP — lop 2
    (--host-resolver-rules) phai chan. prepare/browser.py:155 di theo dung loai
    chuyen huong nay tu link Google News."""
    with _server() as (port, hits), _session() as ph:
        with ph.page() as page:
            _goto(page, f"http://{PUBLIC}:{port}/redir")
    assert "/redir" in hits, hits
    assert not _secret(hits), f"302 dua Chromium vao host noi bo: {hits}"


def test_js_navigation_and_file_scheme_are_blocked():
    with _server() as (port, hits), _session() as ph:
        with ph.page() as page:
            _goto(page, f"http://{PUBLIC}:{port}/jsnav")
            page.wait_for_timeout(800)
        with ph.page() as page:
            loi = _goto(page, "file:///etc/hosts")
            noi_dung = _text(page)
    assert "/jsnav" in hits, hits
    assert not _secret(hits), f"dieu huong JS toi host noi bo: {hits}"
    assert loi and "localhost" not in noi_dung, f"file:// van mo duoc: {loi!r} {noi_dung[:80]!r}"


# ------------------------------------------------------------- get_source
def test_get_source_download_refuses_file_and_internal():
    out = tam.temp_dir(prefix="low438_") / "c.png"
    with _server() as (port, hits):
        for u in ("file:///etc/hosts", f"http://127.0.0.1:{port}/secret-dl",
                  f"http://2130706433:{port}/secret-dl2", f"http://localhost:{port}/secret-dl3"):
            try:
                get_source.download(u, str(out))
            except ValueError:
                continue
            except Exception as e:                           # noqa: BLE001
                raise AssertionError(f"{u}: phai ValueError, ra {type(e).__name__}: {e}") from e
            raise AssertionError(f"{u} lot cong get_source.download")
    assert not _secret(hits), hits
    assert not out.exists(), "tep van duoc ghi"


def test_get_source_main_exits_before_any_request():
    """Thoat KHAC 3: 3 nghia la 'khong co anh don', bob_submit se chup man hinh."""
    out = tam.temp_dir(prefix="low438_") / "d.png"
    with _server() as (port, hits):
        for u in (f"http://127.0.0.1:{port}/secret-main", "file:///etc/hosts"):
            with mock.patch.object(sys, "argv", ["get_source.py", u, str(out)]):
                try:
                    get_source.main()
                except SystemExit as e:
                    assert e.code not in (0, 3, None), f"{u}: ma thoat {e.code!r}"
                else:
                    raise AssertionError(f"{u}: main khong thoat")
    assert not _secret(hits), hits


def test_get_source_fallback_check_without_repo():
    """Ban chep skill trong Hermes home khong import duoc scan_common — van phai chan."""
    with mock.patch.dict(sys.modules, {"scan_common": None}):
        for u in ("file:///etc/passwd", "http://127.1/", "http://[::1]/", "http://x.localhost/",
                  "http://100.87.121.46:9130/", "http://169.254.169.254/"):
            try:
                get_source.check_url(u)
            except ValueError:
                continue
            raise AssertionError(f"{u} lot ban kiem toi thieu")
        get_source.check_url("https://pbs.twimg.com/media/abc?format=jpg&name=orig")


# ---------------------------------------------------------- article_extract
def test_article_extract_checks_redirect_hop_before_sending():
    """Truoc LOW-438: kiem SAU khi di het chuoi chuyen huong -> request toi
    127.0.0.1 da di. `pub.example` duoc tro ve server test bang getaddrinfo gia."""
    that = socket.getaddrinfo

    def gia(host, *a, **k):
        return that("127.0.0.1" if host == PUBLIC else host, *a, **k)

    with _server() as (port, hits), mock.patch("socket.getaddrinfo", gia):
        try:
            article_extract.fetch(f"http://{PUBLIC}:{port}/redir")
        except ValueError:
            pass
        else:
            raise AssertionError("chuyen huong ve 127.0.0.1 khong bi chan")
    assert "/redir" in hits, f"getaddrinfo gia khong an: {hits}"
    assert not _secret(hits), f"request toi host noi bo da di truoc khi bi chan: {hits}"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
