#!/usr/bin/env python3
"""journal_web.py — trang web tĩnh cho nhật ký 9router: Telegram chỉ gửi tóm tắt
+ link, bảng đầy đủ mở ở đây (điện thoại qua netbird cũng xem được).

Vì sao không nhét vào hermes-dashboard: đó là dashboard của Hermes (bind
127.0.0.1, có session token, code trong hermes-agent), không phải chỗ để thêm
trang của đội. Cái này là http.server chuẩn Python, KHÔNG phụ thuộc gói ngoài
nào — bảng .md tự dựng thành HTML bằng `md_bright_html` (bỏ `markdown`, audit D2)
— và CHỈ ĐỌC tệp trong state/9router/nhat_ky.

Đường dẫn:
    /                       danh sách ngày, mỗi ngày một dòng số quan trọng
    /9router/<ngày>         bản .md của ngày render thành HTML (bảng thật)
    /9router/<ngày>.json    số liệu thô (cho ai muốn vẽ thêm)

Chạy dưới systemd user `journal-web` (hermes/systemd/). Cổng NHAT_KY_PORT
(mặc định 9130), host NHAT_KY_HOST (mặc định 0.0.0.0 để đi qua netbird
100.87.121.46). Không có gì bí mật trong nhật ký (tên connection, model, tiền),
không có khoá.
"""
import html
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import monitor_9router as tdr                               # noqa: E402

# Mac dinh 127.0.0.1, KHONG phai 0.0.0.0 (doi 06/09/2026). Trang nay khong co
# xac thuc va hien chi phi theo vai, ten khoa API, ten ket noi, model dang chay
# — bind moi giao dien nghia la ai o cung LAN/netbird cung doc duoc. Muon mo
# cho dien thoai thi dat NHAT_KY_HOST = dia chi netbird trong unit systemd,
# dung mo ca 0.0.0.0.
HOST = os.environ.get("NHAT_KY_HOST", "127.0.0.1")
PORT = int(os.environ.get("NHAT_KY_PORT", "9130"))

CSS = """
body{font:15px/1.5 -apple-system,Segoe UI,Roboto,sans-serif;max-width:1100px;margin:0 auto;padding:12px;color:#222;background:#fafafa}
h1{font-size:1.3em}h2{font-size:1.05em;margin-top:1.6em;border-bottom:1px solid #ddd}
table{border-collapse:collapse;font-size:13px;margin:.5em 0;display:block;overflow-x:auto;white-space:nowrap}
th,td{border:1px solid #ddd;padding:3px 7px;text-align:right}th:first-child,td:first-child{text-align:left}
th{background:#eee}tr:nth-child(even){background:#f3f3f3}
a{color:#0a58ca;text-decoration:none}.top a{margin-right:1em}code{background:#eee;padding:0 3px}
.canh{color:#b00}@media(prefers-color-scheme:dark){body{background:#111;color:#ddd}th{background:#222}tr:nth-child(even){background:#181818}th,td{border-color:#333}a{color:#7ab}}
"""


def _page(tieu_de: str, than: str) -> bytes:
    return (f"<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>"
            f"<title>{html.escape(tieu_de)}</title><style>{CSS}</style><div class=top><a href='/'>← Danh sách ngày</a></div>"
            f"{than}").encode("utf-8")


def _bold(s: str) -> str:
    """`**dam**` -> <b>dam</b>. Chay SAU escape nen `s` khong con the HTML nao."""
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)


def md_bright_html(tho: str) -> str:
    """Bon cu phap markdown ma `monitor_9router` SINH RA: `#`/`##`, bang `|`,
    muc `- `, va `**dam**`. Khong phai bo render markdown day du (audit D2 —
    bo goi `markdown`).

    Lam duoc vi dau vao KHONG phai markdown bat ky: chinh ta sinh ra tep .md do,
    nen tap cu phap dong va kiem duoc (tests/test_nhat_ky_web.py).

    ESCAPE TRUOC, dung the SAU — thu tu nay la bat buoc: ten model, `status` va
    `lastError` trong tep deu chep tu usageHistory cua 9router, tuc tu client goi
    router. Mot ten model dat la `<img src=x onerror=...>` se chay trong trinh
    duyet cua Ong Chu khi bam link luc 6h sang. (Ban cu dung python-markdown
    cung phai escape truoc vi chinh ly do do.)"""
    ra, bang = [], []

    def xa_bang():
        if not bang:
            return
        # Dong thu hai cua bang markdown la vach ngan (|---|:--:|), khong phai du lieu.
        hang = [h for h in bang if not re.fullmatch(r"\|[\s:|-]+\|", h)]
        ra.append("<table>")
        for i, h in enumerate(hang):
            o = [c.strip() for c in h.strip().strip("|").split("|")]
            the = "th" if i == 0 else "td"
            ra.append("<tr>" + "".join(f"<{the}>{_bold(c)}</{the}>" for c in o) + "</tr>")
        ra.append("</table>")
        bang.clear()

    muc = False
    for dong in html.escape(tho, quote=False).splitlines():
        d = dong.rstrip()
        if d.startswith("|"):
            bang.append(d)
            continue
        xa_bang()
        if d.startswith("- "):
            if not muc:
                ra.append("<ul>")
                muc = True
            ra.append(f"<li>{_bold(d[2:])}</li>")
            continue
        if muc:
            ra.append("</ul>")
            muc = False
        if d.startswith("## "):
            ra.append(f"<h2>{_bold(d[3:])}</h2>")
        elif d.startswith("# "):
            ra.append(f"<h1>{_bold(d[2:])}</h1>")
        elif d.strip():
            ra.append(f"<p>{_bold(d)}</p>")
    xa_bang()
    if muc:
        ra.append("</ul>")
    return "\n".join(ra)


def page_date(ngay: str) -> bytes | None:
    p = tdr.JOURNAL / f"9router_{ngay}.md"
    if not p.exists():
        return None
    tho = p.read_text(encoding="utf-8")
    body = md_bright_html(tho)
    return _page(f"9router {ngay}", body + f"<p><a href='/9router/{ngay}.json'>json</a></p>")


def page_list_clean() -> bytes:
    L = ["<h1>Nhật ký 9router theo ngày (giờ VN)</h1>",
         "<table><tr><th>ngày</th><th>req</th><th>$</th><th>cache%</th><th>fallback</th><th>rỗng</th><th>lỗi</th>"
         "<th>$/bài blog</th><th>$/bài dcgr</th><th>model tốn nhất</th></tr>"]
    for p in sorted(tdr.JOURNAL.glob("9router_*.json"), reverse=True):
        try:
            m = json.loads(p.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            continue
        if m.get("loi_doc"):
            continue
        t, ngay = m["tong"], m["ngay"]
        brand = (m.get("vai") or {}).get("theo_brand", {})

        def bai(b):
            x = brand.get(b)
            return "-" if not x or x["usd_bai"] is None else f"{x['usd_bai']} ({x['bai']})"
        model = next(iter(m["theo_model"]), "-").split(" @ ")[0]
        canh = " class=canh" if (m.get("fallback") or sum((m.get("rong") or {}).values()) >= 3) else ""
        L.append(f"<tr{canh}><td><a href='/9router/{ngay}'>{ngay}</a></td><td>{t['req']}</td><td>{t['usd']}</td>"
                 f"<td>{t['cache_pct']}</td><td>{m.get('fallback', 0)}</td><td>{sum((m.get('rong') or {}).values())}</td>"
                 f"<td>{t['loi']}</td><td>{bai('blog')}</td><td>{bai('dcgr')}</td><td>{html.escape(model)}</td></tr>")
    L.append("</table><p>fallback = v4-flash→deepseek-chat trong ≤2 phút; rỗng = ok nhưng ≤5 token out dù prompt ≥1k; "
             "$/bài = $ ước lượng theo vai của brand / số bài published trong ngày (số bài trong ngoặc). Dòng đỏ: có chuyện đáng xem.</p>")
    return _page("Nhật ký 9router", "".join(L))


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):                               # im lặng, journal đủ rồi
        pass

    def _tra(self, code: int, body: bytes, kieu: str = "text/html; charset=utf-8"):
        self.send_response(code)
        self.send_header("Content-Type", kieu)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):                                        # noqa: N802
        duong = self.path.split("?")[0]
        if duong in ("/", "/9router", "/9router/"):
            return self._tra(200, page_list_clean())
        if duong.startswith("/9router/"):
            ten = duong[len("/9router/"):]
            json_ = ten.endswith(".json")
            ngay = ten[:-5] if json_ else ten
            if len(ngay) == 10 and ngay[4] == ngay[7] == "-" and ngay.replace("-", "").isdigit():
                if json_:
                    p = tdr.JOURNAL / f"9router_{ngay}.json"
                    if p.exists():
                        return self._tra(200, p.read_bytes(), "application/json; charset=utf-8")
                else:
                    b = page_date(ngay)
                    if b:
                        return self._tra(200, b)
        self._tra(404, _page("404", "<p>Không có trang này.</p>"))


def main() -> int:
    tdr.JOURNAL.mkdir(parents=True, exist_ok=True)
    srv = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"[web] http://{HOST}:{PORT}/ — đọc {tdr.JOURNAL}", flush=True)
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main())
