#!/usr/bin/env python3
"""LOW-155 — album/anh xem truoc len hang duyet WriteTimeout (su co 14/09/2026).

Do duoc that tren may chu (khong suy doan): duong truyen toi api.telegram.org
~28 KB/s khi upload anh (curl toi dich khac ~7 MB/s cung luc — rieng duong toi
Telegram), trong khi album carousel PNG toi ~11,8 MB/7 anh gui trong MOT request
`sendMediaGroup` voi timeout co dinh 120s cu. `miles_submit.py` (t_30fe03ed,
bai TSMC CoWoS) chet o buoc push, WriteTimeout 5 lan lien tiep, task blocked.

Hai lop sua, hai nhom test:
  A. `approve_base.call_upload` — retry loi CHUA CHAC gui di (ConnectError/
     ConnectTimeout), KHONG retry mu WriteTimeout/ReadTimeout (co the da gui
     mot phan — thu lai se co nguy co trung anh).
  B. `approve_post._compress_preview` / `_upload_timeout` — anh xem truoc qua
     kich thuoc/canh thi nen JPEG truoc khi gui, ngan sach ghi tinh theo dung
     luong SAU KHI nen.

Chay:  venv/bin/python tests/test_upload_preview.py
"""
import io
import sys
import tempfile
from pathlib import Path

import httpx
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import approve_base as ab                                         # noqa: E402
import approve_post as db                                          # noqa: E402


# ==================================================================== A. call_upload
class _FakeFile(io.BytesIO):
    """Tay cam gia: nhu file that (httpx doc noi dung de dung multipart truoc khi
    toi MockTransport) nhung ghi lai co bi .close() hay khong."""

    def __init__(self):
        super().__init__(b"gia lap noi dung anh")
        self.closed_that = False

    def close(self):
        self.closed_that = True
        super().close()


def _goi(handler, *, n_files=1, timeout=30):
    """Goi that ab.call_upload voi httpx.Client bi ep dung MockTransport(handler)
    (cung ky thuat voi tests/test_gui_tele.py). Tra ve (ket_qua, so_lan_mo_file,
    danh_sach_tay_cam_da_tao)."""
    cu = httpx.Client
    tay_cam = []
    so_lan_mo = [0]

    def _mo():
        so_lan_mo[0] += 1
        ds = [_FakeFile() for _ in range(n_files)]
        tay_cam.append(ds)
        return {f"file{i}": f for i, f in enumerate(ds)}

    def _client_gia(*a, **k):
        k.pop("transport", None)
        return cu(*a, transport=httpx.MockTransport(handler), **k)

    ab.httpx.Client = _client_gia
    cu_retry, ab.UPLOAD_RETRY_DELAYS = ab.UPLOAD_RETRY_DELAYS, (0, 0)
    try:
        res = ab.call_upload("tok", "sendPhoto", {"chat_id": -1}, _mo, timeout=timeout)
    finally:
        ab.httpx.Client = cu
        ab.UPLOAD_RETRY_DELAYS = cu_retry
    return res, so_lan_mo[0], tay_cam


def test_call_upload_retries_connect_error_then_succeeds():
    goi = [0]

    def handler(request):
        goi[0] += 1
        if goi[0] < 3:
            raise httpx.ConnectError("gia lap mat ket noi", request=request)
        return httpx.Response(200, json={"ok": True, "result": {"message_id": 1}})

    res, so_lan_mo, tay_cam = _goi(handler)
    assert res == {"ok": True, "result": {"message_id": 1}}, res
    assert so_lan_mo == 3, f"phai thu lai du 2 lan loi ket noi + 1 lan thanh cong: {so_lan_mo}"
    assert all(f.closed_that for ds in tay_cam for f in ds), "moi tay cam (ke ca lan hong) phai duoc dong"


def test_call_upload_gives_up_after_all_connect_retries():
    def handler(request):
        raise httpx.ConnectTimeout("gia lap timeout ket noi", request=request)

    res, so_lan_mo, _ = _goi(handler)
    assert not res.get("ok"), res
    assert "ConnectTimeout" in res.get("description", ""), res
    assert so_lan_mo == 3, f"3 lan thu (1 + 2 retry) roi bao loi, dang {so_lan_mo}"


def test_call_upload_does_not_retry_write_timeout():
    """WriteTimeout co the da gui MOT PHAN du lieu — KHONG duoc thu lai mu (nguy
    co gui trung anh); phai tra loi NGAY, chi mot lan mo tay cam."""
    def handler(request):
        raise httpx.WriteTimeout("gia lap ghi cham", request=request)

    res, so_lan_mo, tay_cam = _goi(handler)
    assert not res.get("ok"), res
    assert "WriteTimeout" in res.get("description", ""), res
    assert so_lan_mo == 1, f"WriteTimeout khong duoc thu lai, dang mo {so_lan_mo} lan"
    assert all(f.closed_that for ds in tay_cam for f in ds)


def test_call_upload_does_not_retry_read_timeout():
    def handler(request):
        raise httpx.ReadTimeout("gia lap doi phan hoi lau", request=request)

    res, so_lan_mo, _ = _goi(handler)
    assert not res.get("ok") and so_lan_mo == 1, (res, so_lan_mo)


def test_call_upload_no_files_sends_none_not_empty_dict():
    """Album toan URL (khong tep cuc bo) -> paths={} -> phai gui files=None, khong
    phai files={} (httpx tao multipart rong vo ich neu truyen dict rong)."""
    seen = {}

    def handler(request):
        seen["content_type"] = request.headers.get("content-type", "")
        return httpx.Response(200, json={"ok": True, "result": {}})

    res, so_lan_mo, _ = _goi(handler, n_files=0)
    assert res.get("ok") and so_lan_mo == 1
    assert "multipart" not in seen["content_type"], seen


# =========================================================== B. compress + timeout
def _anh_nho(tmp: Path) -> Path:
    p = tmp / "small.png"
    Image.new("RGB", (200, 150), (10, 20, 30)).save(p, "PNG")
    return p


def _anh_lon(tmp: Path) -> Path:
    p = tmp / "big.png"
    Image.effect_noise((2000, 1200), 60).convert("RGB").save(p, "PNG")
    return p


def test_compress_preview_keeps_small_image_untouched():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        src = _anh_nho(tmp)
        out = db._compress_preview(src, tmp)
    assert out == src, f"anh da nho/dung du chuan thi phai giu nguyen, dang tra ve {out}"


def test_compress_preview_shrinks_oversized_image():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        src = _anh_lon(tmp)
        src_size = src.stat().st_size
        out = db._compress_preview(src, tmp)
        assert out != src and out.suffix == ".jpg", out
        out_size = out.stat().st_size
        with Image.open(out) as im:
            dims = im.size
    assert out_size < src_size, "anh nen phai NHO HON anh goc"
    assert out_size <= db.PREVIEW_MAX_BYTES, \
        f"anh nen van vuot han {db.PREVIEW_MAX_BYTES}: {out_size}"
    assert max(dims) <= db.PREVIEW_MAX_DIM, dims


def test_compress_preview_falls_back_to_original_on_bad_file():
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        bad = tmp / "hong.png"
        bad.write_bytes(b"khong phai anh that")
        out = db._compress_preview(bad, tmp)
    assert out == bad, "anh hong thi tra ve nguyen ban, khong duoc nem loi"


def test_upload_timeout_scales_with_size_and_has_floor_and_ceiling():
    nho = db._upload_timeout(10_000)
    lon = db._upload_timeout(50_000_000)
    assert nho.connect == 30.0 and lon.connect == 30.0, "ngan sach ket noi CO DINH, tach khoi ngan sach ghi"
    assert nho.write >= 60, f"san toi thieu 60s: {nho.write}"
    assert lon.write == db.UPLOAD_WRITE_CEILING, f"phai tran o {db.UPLOAD_WRITE_CEILING}: {lon.write}"
    assert nho.write < lon.write, "anh lon hon phai duoc ngan sach ghi lon hon (chua tran)"


def test_send_media_group_computes_budget_from_compressed_not_original_size():
    """total_bytes truyen vao _upload_timeout phai la dung luong SAU KHI nen —
    khong thi anh 11,8 MB van tinh ra ngan sach nhu truoc khi sua (LOW-155)."""
    goi = {}

    def call_upload_gia(token, method, data, open_files, *, timeout):
        goi["total_write_budget"] = timeout.write
        handles = open_files()
        for fh in handles.values():
            fh.close()
        return {"ok": True, "result": [{"message_id": 1}]}

    cu = db.call_upload
    db.call_upload = call_upload_gia
    try:
        with tempfile.TemporaryDirectory() as t:
            tmp = Path(t)
            src = _anh_lon(tmp)
            res = db._send_media_group("tok", -1, [str(src)])
    finally:
        db.call_upload = cu
    assert res == {"ok": True, "result": [{"message_id": 1}]}
    # Anh nen ~duoi PREVIEW_MAX_BYTES -> ngan sach ghi phai GAN san toi thieu
    # (60s), CACH XA muc se sinh ra tu 11,8 MB goc (se cham tran UPLOAD_WRITE_CEILING).
    assert goi["total_write_budget"] < db.UPLOAD_WRITE_CEILING, \
        f"ngan sach dang tinh tu anh CHUA nen (tran o {goi['total_write_budget']})"


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
