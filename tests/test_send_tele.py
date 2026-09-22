#!/usr/bin/env python3
"""Test cho lop gui/nhan Telegram — audit E3: lop nay chua co test nao.

Hai muc tieu:

  1. `approve_base.call()` — goi Bot API that qua mot `httpx.Client(timeout=90)`
     TU TAO ben trong ham (khong nhan client/transport tu ngoai). De gia lap
     Telegram ma khong dung mang that, monkeypatch `httpx.Client` (thuoc tinh
     module, dung MOT module `httpx` nam trong `sys.modules` voi ca
     approve_base.py) thanh mot wrapper luon gan them `transport=
     httpx.MockTransport(handler)`. Muc tieu: (a) loi mang -> call() bat lai,
     tra dict {"ok": False, ...}, KHONG nem exception ra ngoai; (b) thanh cong
     (HTTP 200 that qua MockTransport) -> call() tra DUNG json cua response.

  2. `tele_util.split_message()` — ham THUAN chia tin dai, test truc tiep khong
     can mock gi ca.

Chay:  python tests/test_send_tele.py
"""
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import approve_base                  # noqa: E402
import tele_util                    # noqa: E402


# ============================================================ approve_base.call
def _call_with_mock_transport(handler, token, method, **kw):
    """Goi approve_base.call(token, method, **kw) nhung ep httpx.Client() O BEN
    TRONG no dung MockTransport(handler) thay vi mang that, roi phuc hoi lai.

    call() tu tao `httpx.Client(timeout=90)` MOI, khong nhan client tu ngoai
    -> khong the truyen transport truc tiep vao. Monkeypatch `httpx.Client`
    (thuoc tinh module) la cach don gian nhat de chen MockTransport vao ma
    khong dung toi code san xuat: approve_base.py chi luu ten module `httpx`
    luc import, roi tra cuu `httpx.Client` MOI LAN goi — nen doi thuoc tinh o
    day cung doi luon noi goi ben trong no (cung mot object module trong
    sys.modules)."""
    cu = httpx.Client

    def _client_gia(*a, **k):
        k.pop("transport", None)
        return cu(*a, transport=httpx.MockTransport(handler), **k)

    httpx.Client = _client_gia
    try:
        return approve_base.call(token, method, **kw)
    finally:
        httpx.Client = cu


def test_call_network_error_return_dict_no_throw_exception():
    """Transport nem httpx.ConnectError (gia lap mat mang / DNS fail) -> call()
    PHAI bat lai va tra dict {"ok": False, ...}, dung docstring cua call():
    'loi mang -> {"ok": False, "description"}', khong duoc de exception thoat
    ra ngoai ham."""
    def handler_loi(request):
        raise httpx.ConnectError("gia lap mat mang", request=request)

    res = _call_with_mock_transport(handler_loi, "fake-token", "sendMessage",
                                   chat_id=1, text="x")

    assert isinstance(res, dict), f"phai tra ve dict ke ca khi loi, duoc {type(res)}"
    assert not res.get("ok"), f"ok phai la False/falsy khi mang loi: {res}"
    assert "description" in res, f"thieu description de biet loi gi: {res}"


def test_call_error_catch_ky_no_right_httpx_same_no_exit_out_outside():
    """`except Exception` trong call() la bat CHUNG, khong rieng loi httpx —
    dam bao dieu do bang mot loi hoan toan khac (RuntimeError), khong lien
    quan gi den mang."""
    def handler_loi_la(request):
        raise RuntimeError("loi bat ky, khong phai loi mang httpx")

    res = _call_with_mock_transport(handler_loi_la, "fake-token", "sendMessage",
                                   chat_id=1, text="x")

    assert isinstance(res, dict) and not res.get("ok"), (
        f"except Exception phai bat ca loi khong-httpx, khong duoc nem ra ngoai: {res}")


def test_call_success_return_use_json_of_response():
    """MockTransport tra HTTP 200 that + json {"ok": true, "result": {...}}
    -> call() phai tra DUNG dict do (r.json(), khong bien doi gi them)."""
    ket_qua_gia = {"ok": True, "result": {"message_id": 42, "chat": {"id": 1}}}
    goi = []

    def handler_ok(request):
        goi.append(request)
        return httpx.Response(200, json=ket_qua_gia)

    res = _call_with_mock_transport(handler_ok, "fake-token", "sendMessage",
                                   chat_id=1, text="x")

    assert res == ket_qua_gia, f"phai tra dung json cua response thanh cong: {res}"
    assert len(goi) == 1, f"handler (Bot API gia) phai duoc goi dung 1 lan: {len(goi)}"
    assert goi[0].method == "POST", f"Bot API phai duoc goi bang POST: {goi[0].method}"
    assert "/sendMessage" in str(goi[0].url), f"sai URL goi Bot API: {goi[0].url}"


# ============================================================ tele_util.split_message
def test_split_message_short_than_limit_keep_raw_one_part():
    """Text ngan hon gioi han: KHONG chia, tra ve dung 1 phan tu = text.rstrip()
    (ham luon rstrip() truoc, xem dong dau cua split_message())."""
    text = "Xin chao, day la mot tin nhan ngan.   \n\n"
    ket_qua = tele_util.split_message(text, gioi_han=50)

    assert len(ket_qua) == 1, f"text ngan hon gioi han phai tra dung 1 phan tu: {ket_qua}"
    assert ket_qua == [text.rstrip()], f"phan tu do phai la text.rstrip(): {ket_qua!r}"


def test_split_message_long_than_limit_many_attempt_split_use_measure_long():
    """Text dai gap nhieu lan gioi_han -> nhieu phan, MOI phan <= gioi_han ky tu."""
    gioi_han = 50
    tu = ["chia", "tin", "dai", "thanh", "nhieu", "phan", "cho", "vua", "gioi", "han"]
    text = " ".join(tu * 20)                      # dai hon gioi_han nhieu lan
    assert len(text) > gioi_han * 5, "tien de test sai: text dung de chia chua du dai"

    ket_qua = tele_util.split_message(text, gioi_han=gioi_han)

    assert len(ket_qua) > 1, f"text dai hon gioi han nhieu lan phai bi chia lam nhieu phan: {len(ket_qua)}"
    for i, p in enumerate(ket_qua):
        assert len(p) <= gioi_han, f"phan thu {i} dai {len(p)} > gioi_han {gioi_han}: {p!r}"


def test_split_message_stack_again_no_face_content():
    """Ghep tat ca cac phan lai, bo whitespace o ranh gioi cat (dung docstring
    'khong mat noi dung, chi bo whitespace o ranh gioi'), phai cho lai DUNG
    chuoi ky tu khong-whitespace nhu text goc. Text co ca newline xen giua de
    kiem luon nhanh uu tien cat o \\n."""
    gioi_han = 50
    dong = "Cau so {0} co mot vai chu de keo dai van ban ra them mot chut nua."
    text = "\n".join(dong.format(i) for i in range(15))

    ket_qua = tele_util.split_message(text, gioi_han=gioi_han)

    assert len(ket_qua) > 1, "tien de test sai: text dung de ghep chua bi chia"
    for p in ket_qua:
        assert len(p) <= gioi_han, f"phan vuot gioi han khi ghep: {len(p)} > {gioi_han}"

    goc_khong_trang = "".join(c for c in text if not c.isspace())
    ghep_khong_trang = "".join(c for c in "".join(ket_qua) if not c.isspace())
    assert ghep_khong_trang == goc_khong_trang, (
        "mat hoac sai lech noi dung ky tu khi ghep cac phan lai voi nhau "
        f"(goc {len(goc_khong_trang)} ky tu, ghep lai duoc {len(ghep_khong_trang)} ky tu)")


def test_split_message_priority_crop_cell_down_line():
    """Khi mot xuong dong nam trong nua sau cua so gioi_han, ham phai cat DUNG
    tai do va giu nguyen ca dong — khong lui ve cat bang khoang trang giua
    dong (dung nhu docstring module: 'uu tien cat o ranh gioi xuong dong roi
    khoang trang')."""
    gioi_han = 40
    dong_1 = "a" * 30            # dong 1 dai 30: xuong dong sau no nam o vi tri 30 (>= 40//2)
    dong_2 = "b" * 30
    text = dong_1 + "\n" + dong_2

    ket_qua = tele_util.split_message(text, gioi_han=gioi_han)

    assert ket_qua == [dong_1, dong_2], (
        f"phai cat dung tai xuong dong, giu nguyen tung dong: {ket_qua}")


def test_split_message_text_empty_return_it_most_one_part_from():
    """Docstring: 'Luon tra ve list co it nhat MOT phan tu (co the la chuoi
    rong)' de nguoi goi cu lap la gui du, khong can kiem tra rong truoc."""
    ket_qua = tele_util.split_message("", gioi_han=50)

    assert isinstance(ket_qua, list) and len(ket_qua) >= 1, f"phai co it nhat 1 phan tu: {ket_qua}"
    assert ket_qua == [""], f"text rong phai tra ve mot phan tu la chuoi rong: {ket_qua}"


# ==================================== approve_base.call — 429 va ngan sach connect
def _call_ghi_lai(handler, token, method, **kw):
    """Nhu `_call_with_mock_transport` nhung ghi lai THEM hai thu de khang dinh:
    `timeout` ma call() dua cho httpx.Client, va cac lan `time.sleep` no goi.

    Tra ve (ket_qua, timeouts, cac_lan_ngu)."""
    cu_client, cu_sleep = httpx.Client, approve_base.time.sleep
    timeouts, cac_lan_ngu = [], []

    def _client_gia(*a, **k):
        k.pop("transport", None)
        timeouts.append(k.get("timeout"))
        return cu_client(*a, transport=httpx.MockTransport(handler), **k)

    httpx.Client = _client_gia
    approve_base.time.sleep = cac_lan_ngu.append
    try:
        return approve_base.call(token, method, **kw), timeouts, cac_lan_ngu
    finally:
        httpx.Client, approve_base.time.sleep = cu_client, cu_sleep


def _tra_loi_429(giay):
    """Dung nguyen van Telegram tra ve khi bop bang: HTTP 429 + parameters.retry_after."""
    return httpx.Response(429, json={
        "ok": False, "error_code": 429,
        "description": "Too Many Requests: retry after %d" % giay,
        "parameters": {"retry_after": giay}})


def test_call_429_doi_dung_so_giay_telegram_bao_roi_gui_lai():
    """Telegram bop bang -> tin KHONG den noi. Truoc day call() chi ghi mot dong
    log roi thoi, nen cac tin bao tien do bi mat im (do tren dc-group: 5 lan
    trong 16,5 gio, mat han cac tin "Miles bat dau", "Kite xong task"). Telegram
    da noi san phai cho bao lau o `parameters.retry_after` — cho dung chung do
    roi gui lai."""
    tra_loi = [_tra_loi_429(5), httpx.Response(200, json={"ok": True, "result": {"message_id": 7}})]
    goi = []

    def handler(request):
        goi.append(request)
        return tra_loi.pop(0)

    res, _, cac_lan_ngu = _call_ghi_lai(handler, "tok", "sendMessage", chat_id=1, text="x")

    assert res.get("ok") is True, "phai gui lai va thanh cong, duoc: %r" % (res,)
    assert len(goi) == 2, "phai goi Bot API 2 lan (lan dau 429, lan sau lai), duoc %d" % len(goi)
    assert cac_lan_ngu and cac_lan_ngu[0] >= 5, \
        "phai ngu it nhat 5s dung nhu Telegram bao, duoc: %r" % (cac_lan_ngu,)


def test_call_429_mai_thi_bo_cuoc_va_tra_ve_loi_chu_khong_treo():
    """Bop bang khong dut thi khong duoc thu mai: moi lan thu deu chiem luon
    thread nen, ma nut bam con phai kip TTL 60s cua callback_query_id."""
    goi = []

    def handler(request):
        goi.append(request)
        return _tra_loi_429(1)

    res, _, cac_lan_ngu = _call_ghi_lai(handler, "tok", "sendMessage", chat_id=1, text="x")

    assert isinstance(res, dict) and not res.get("ok"), \
        "bo cuoc thi van phai tra dict doc duoc: %r" % (res,)
    assert "Too Many Requests" in str(res.get("description")), \
        "phai giu nguyen loi cua Telegram de log noi duoc ly do: %r" % (res,)
    assert 2 <= len(goi) <= 4, "so lan thu phai co tran, duoc %d" % len(goi)
    assert sum(cac_lan_ngu) <= 60, \
        "tong thoi gian cho phai duoi TTL 60s cua callback_query: %r" % (cac_lan_ngu,)


def test_call_429_tong_thoi_gian_cho_luon_duoi_ttl_60s():
    """Tran TUNG LAN thoi thi chua du: hai lan cho 30s lien la 62 giay, da
    vuot TTL ~60s cua callback_query_id ma chinh luat nay dat ra de bao ve.
    Phai co tran cho TONG thoi gian cho."""
    goi = []

    def handler(request):
        goi.append(request)
        return _tra_loi_429(approve_base.RATE_LIMIT_MAX_WAIT)

    _, _, cac_lan_ngu = _call_ghi_lai(handler, "tok", "sendMessage", chat_id=1, text="x")

    assert sum(cac_lan_ngu) < 60, \
        "tong thoi gian cho %r vuot TTL 60s cua callback_query" % (cac_lan_ngu,)


def test_call_429_bao_cho_qua_lau_thi_khong_cho():
    """Telegram thinh thoang bao retry_after hang tram giay. Ngu chung do la
    treo thread nen ca vai phut — thua bo cuoc ngay."""
    goi = []

    def handler(request):
        goi.append(request)
        return _tra_loi_429(600)

    res, _, cac_lan_ngu = _call_ghi_lai(handler, "tok", "sendMessage", chat_id=1, text="x")

    assert not res.get("ok") and len(goi) == 1, \
        "cho 600s thi phai bo cuoc ngay, khong thu lai: %d lan goi" % len(goi)
    assert not cac_lan_ngu, "khong duoc ngu chut nao: %r" % (cac_lan_ngu,)


def test_call_ngan_sach_connect_ngan_du_read_van_dai():
    """`httpx.Client(timeout=90)` ap MOT con so cho ca connect/read/write. Mang
    cua may nay nuot ~1/30 goi SYN, nen mot lan bat tay ho den ngon tron 90 giay
    — vuot TTL ~60s cua callback_query_id va nut bam bao "query is too old"
    (11 lan ngay 21/09/2026). Connect ngan de loi mang lo som; read van dai vi
    Bot API tra cham khi tin co anh."""
    def handler(request):
        return httpx.Response(200, json={"ok": True, "result": {}})

    _, timeouts, _ = _call_ghi_lai(handler, "tok", "sendMessage", chat_id=1, text="x")

    assert timeouts and isinstance(timeouts[0], httpx.Timeout), \
        "timeout phai la httpx.Timeout de tach rieng connect, duoc: %r" % (timeouts[0],)
    assert timeouts[0].connect is not None and timeouts[0].connect <= 5.0, \
        "connect=%r — mot bat tay ho den van ngon qua lau" % (timeouts[0].connect,)
    assert timeouts[0].read is not None and timeouts[0].read >= 90.0, \
        "read=%r — cat ngan read se lam hong cac tin co anh" % (timeouts[0].read,)

if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
