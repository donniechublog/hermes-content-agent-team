#!/usr/bin/env python3
"""Test cho lop gui/nhan Telegram — audit E3: lop nay chua co test nao.

Hai muc tieu:

  1. `duyet_co_so.call()` — goi Bot API that qua mot `httpx.Client(timeout=90)`
     TU TAO ben trong ham (khong nhan client/transport tu ngoai). De gia lap
     Telegram ma khong dung mang that, monkeypatch `httpx.Client` (thuoc tinh
     module, dung MOT module `httpx` nam trong `sys.modules` voi ca
     duyet_co_so.py) thanh mot wrapper luon gan them `transport=
     httpx.MockTransport(handler)`. Muc tieu: (a) loi mang -> call() bat lai,
     tra dict {"ok": False, ...}, KHONG nem exception ra ngoai; (b) thanh cong
     (HTTP 200 that qua MockTransport) -> call() tra DUNG json cua response.

  2. `tele_util.chia_tin()` — ham THUAN chia tin dai, test truc tiep khong
     can mock gi ca.

Chay:  python tests/test_gui_tele.py
"""
import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import duyet_co_so                  # noqa: E402
import tele_util                    # noqa: E402


# ============================================================ duyet_co_so.call
def _goi_voi_mock_transport(handler, token, method, **kw):
    """Goi duyet_co_so.call(token, method, **kw) nhung ep httpx.Client() O BEN
    TRONG no dung MockTransport(handler) thay vi mang that, roi phuc hoi lai.

    call() tu tao `httpx.Client(timeout=90)` MOI, khong nhan client tu ngoai
    -> khong the truyen transport truc tiep vao. Monkeypatch `httpx.Client`
    (thuoc tinh module) la cach don gian nhat de chen MockTransport vao ma
    khong dung toi code san xuat: duyet_co_so.py chi luu ten module `httpx`
    luc import, roi tra cuu `httpx.Client` MOI LAN goi — nen doi thuoc tinh o
    day cung doi luon noi goi ben trong no (cung mot object module trong
    sys.modules)."""
    cu = httpx.Client

    def _client_gia(*a, **k):
        k.pop("transport", None)
        return cu(*a, transport=httpx.MockTransport(handler), **k)

    httpx.Client = _client_gia
    try:
        return duyet_co_so.call(token, method, **kw)
    finally:
        httpx.Client = cu


def test_call_mang_loi_tra_dict_khong_nem_exception():
    """Transport nem httpx.ConnectError (gia lap mat mang / DNS fail) -> call()
    PHAI bat lai va tra dict {"ok": False, ...}, dung docstring cua call():
    'loi mang -> {"ok": False, "description"}', khong duoc de exception thoat
    ra ngoai ham."""
    def handler_loi(request):
        raise httpx.ConnectError("gia lap mat mang", request=request)

    res = _goi_voi_mock_transport(handler_loi, "fake-token", "sendMessage",
                                   chat_id=1, text="x")

    assert isinstance(res, dict), f"phai tra ve dict ke ca khi loi, duoc {type(res)}"
    assert not res.get("ok"), f"ok phai la False/falsy khi mang loi: {res}"
    assert "description" in res, f"thieu description de biet loi gi: {res}"


def test_call_loi_bat_ky_khong_phai_httpx_cung_khong_thoat_ra_ngoai():
    """`except Exception` trong call() la bat CHUNG, khong rieng loi httpx —
    dam bao dieu do bang mot loi hoan toan khac (RuntimeError), khong lien
    quan gi den mang."""
    def handler_loi_la(request):
        raise RuntimeError("loi bat ky, khong phai loi mang httpx")

    res = _goi_voi_mock_transport(handler_loi_la, "fake-token", "sendMessage",
                                   chat_id=1, text="x")

    assert isinstance(res, dict) and not res.get("ok"), (
        f"except Exception phai bat ca loi khong-httpx, khong duoc nem ra ngoai: {res}")


def test_call_thanh_cong_tra_dung_json_cua_response():
    """MockTransport tra HTTP 200 that + json {"ok": true, "result": {...}}
    -> call() phai tra DUNG dict do (r.json(), khong bien doi gi them)."""
    ket_qua_gia = {"ok": True, "result": {"message_id": 42, "chat": {"id": 1}}}
    goi = []

    def handler_ok(request):
        goi.append(request)
        return httpx.Response(200, json=ket_qua_gia)

    res = _goi_voi_mock_transport(handler_ok, "fake-token", "sendMessage",
                                   chat_id=1, text="x")

    assert res == ket_qua_gia, f"phai tra dung json cua response thanh cong: {res}"
    assert len(goi) == 1, f"handler (Bot API gia) phai duoc goi dung 1 lan: {len(goi)}"
    assert goi[0].method == "POST", f"Bot API phai duoc goi bang POST: {goi[0].method}"
    assert "/sendMessage" in str(goi[0].url), f"sai URL goi Bot API: {goi[0].url}"


# ============================================================ tele_util.chia_tin
def test_chia_tin_ngan_hon_gioi_han_giu_nguyen_mot_phan():
    """Text ngan hon gioi han: KHONG chia, tra ve dung 1 phan tu = text.rstrip()
    (ham luon rstrip() truoc, xem dong dau cua chia_tin())."""
    text = "Xin chao, day la mot tin nhan ngan.   \n\n"
    ket_qua = tele_util.chia_tin(text, gioi_han=50)

    assert len(ket_qua) == 1, f"text ngan hon gioi han phai tra dung 1 phan tu: {ket_qua}"
    assert ket_qua == [text.rstrip()], f"phan tu do phai la text.rstrip(): {ket_qua!r}"


def test_chia_tin_dai_hon_gioi_han_nhieu_lan_chia_dung_do_dai():
    """Text dai gap nhieu lan gioi_han -> nhieu phan, MOI phan <= gioi_han ky tu."""
    gioi_han = 50
    tu = ["chia", "tin", "dai", "thanh", "nhieu", "phan", "cho", "vua", "gioi", "han"]
    text = " ".join(tu * 20)                      # dai hon gioi_han nhieu lan
    assert len(text) > gioi_han * 5, "tien de test sai: text dung de chia chua du dai"

    ket_qua = tele_util.chia_tin(text, gioi_han=gioi_han)

    assert len(ket_qua) > 1, f"text dai hon gioi han nhieu lan phai bi chia lam nhieu phan: {len(ket_qua)}"
    for i, p in enumerate(ket_qua):
        assert len(p) <= gioi_han, f"phan thu {i} dai {len(p)} > gioi_han {gioi_han}: {p!r}"


def test_chia_tin_ghep_lai_khong_mat_noi_dung():
    """Ghep tat ca cac phan lai, bo whitespace o ranh gioi cat (dung docstring
    'khong mat noi dung, chi bo whitespace o ranh gioi'), phai cho lai DUNG
    chuoi ky tu khong-whitespace nhu text goc. Text co ca newline xen giua de
    kiem luon nhanh uu tien cat o \\n."""
    gioi_han = 50
    dong = "Cau so {0} co mot vai chu de keo dai van ban ra them mot chut nua."
    text = "\n".join(dong.format(i) for i in range(15))

    ket_qua = tele_util.chia_tin(text, gioi_han=gioi_han)

    assert len(ket_qua) > 1, "tien de test sai: text dung de ghep chua bi chia"
    for p in ket_qua:
        assert len(p) <= gioi_han, f"phan vuot gioi han khi ghep: {len(p)} > {gioi_han}"

    goc_khong_trang = "".join(c for c in text if not c.isspace())
    ghep_khong_trang = "".join(c for c in "".join(ket_qua) if not c.isspace())
    assert ghep_khong_trang == goc_khong_trang, (
        "mat hoac sai lech noi dung ky tu khi ghep cac phan lai voi nhau "
        f"(goc {len(goc_khong_trang)} ky tu, ghep lai duoc {len(ghep_khong_trang)} ky tu)")


def test_chia_tin_uu_tien_cat_o_xuong_dong():
    """Khi mot xuong dong nam trong nua sau cua so gioi_han, ham phai cat DUNG
    tai do va giu nguyen ca dong — khong lui ve cat bang khoang trang giua
    dong (dung nhu docstring module: 'uu tien cat o ranh gioi xuong dong roi
    khoang trang')."""
    gioi_han = 40
    dong_1 = "a" * 30            # dong 1 dai 30: xuong dong sau no nam o vi tri 30 (>= 40//2)
    dong_2 = "b" * 30
    text = dong_1 + "\n" + dong_2

    ket_qua = tele_util.chia_tin(text, gioi_han=gioi_han)

    assert ket_qua == [dong_1, dong_2], (
        f"phai cat dung tai xuong dong, giu nguyen tung dong: {ket_qua}")


def test_chia_tin_text_rong_tra_ve_it_nhat_mot_phan_tu():
    """Docstring: 'Luon tra ve list co it nhat MOT phan tu (co the la chuoi
    rong)' de nguoi goi cu lap la gui du, khong can kiem tra rong truoc."""
    ket_qua = tele_util.chia_tin("", gioi_han=50)

    assert isinstance(ket_qua, list) and len(ket_qua) >= 1, f"phai co it nhat 1 phan tu: {ket_qua}"
    assert ket_qua == [""], f"text rong phai tra ve mot phan tu la chuoi rong: {ket_qua}"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
