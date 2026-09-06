#!/usr/bin/env python3
"""Cac ham THUAN chua ai canh — re nhat de test, dat nhat khi hong im.

Audit 06/09/2026: nhung ham duoi day khong goi mang, khong doc dia, khong can
Hermes — nhung khong ham nao co test, va phan lon quyet dinh nhung viec khong
lo ra khi hong:

  - `co_tieng_viet`  quyet dinh co nem tieu de Viet vao Google News/Bing khong
                     (luat Ong Chu 05/09). Hong = hai tieng tim kiem vo ich va
                     Dre bo cuoc vi khong co anh.
  - `_url_hop_le`    cong chan URL noi bo cho lenh /bai.
  - `route`          topic nao thi vai nao tra loi.
  - `_HangFIFO`      thu tu tra loi chat trong mot phien; cau truc dong bo tu
                     viet, sinh ra sau su co 04/09 (Itachi doi Gin 108 giay).
  - `gom_trung`      gop nhieu bao dua cung mot su kien. Docstring cua no ke
                     hai lan hoi quy that; ca hai o day thanh test.
  - `chuan_hoa`      khoa dedup ghi vao business_seen.json.

Chay:  venv/bin/python tests/test_ham_thuan.py
"""
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ------------------------------------------------------------ co_tieng_viet
def test_co_tieng_viet_bat_dau_khong_bat_ascii():
    import nguon_bai as nb
    for t in ["Nvidia đàm phán rót 2,5 tỷ USD", "Mô hình mở", "đ", "Ý"]:
        assert nb.co_tieng_viet(t), f"bo sot dau: {t!r}"
    for t in ["Nvidia in talks to invest $2.5B", "GPT-5 Codex Max", "",
              "Qwen3-Max: 1 trieu token context"]:
        assert not nb.co_tieng_viet(t), f"bao nham co dau: {t!r}"


def test_co_tieng_viet_nhan_none():
    import nguon_bai as nb
    assert nb.co_tieng_viet(None) is False


def test_truy_van_bing_tu_choi_tieng_viet():
    """Chan cung, khong phai loi khuyen: tieu de Viet -> khong sinh truy van."""
    import nguon_bai as nb
    assert nb._truy_van_bing("Nvidia đàm phán rót 2,5 tỷ USD") == []
    assert nb._truy_van_bing("Nvidia in talks to invest $2.5B") != []


# -------------------------------------------------------------- _url_hop_le
def test_url_hop_le_chan_host_noi_bo():
    import duyet_lenh as dl
    for u in ["http://localhost:9130/", "http://127.0.0.1:9121/x",
              "http://10.0.0.5/", "http://192.168.1.61:20128/v1",
              "http://169.254.169.254/latest/meta-data/",
              "http://172.16.0.1/", "http://172.31.255.1/",
              "http://may.local/", "http://x.internal/"]:
        assert dl._url_hop_le(u), f"khong chan host noi bo: {u}"


def test_url_hop_le_nhan_url_that_va_chan_scheme_la():
    import duyet_lenh as dl
    assert dl._url_hop_le("https://openai.com/index/abc") is None
    assert dl._url_hop_le("http://vnexpress.net/bai-1.html") is None
    # 172.32 KHONG thuoc dai rieng (dai la 172.16-172.31)
    assert dl._url_hop_le("http://172.32.0.1/") is None
    for u in ["file:///etc/passwd", "ftp://x.com/a", "khong-phai-url",
              "https://", "javascript:alert(1)"]:
        assert dl._url_hop_le(u), f"khong chan scheme/URL la: {u}"


def test_chuan_hoa_url_bo_tracking_giu_phan_con_lai():
    import duyet_lenh as dl
    assert (dl._chuan_hoa_url("https://X.com/Bai?utm_source=a&id=7#doan2")
            == "https://x.com/Bai?id=7")
    assert (dl._chuan_hoa_url("https://x.com/a/") == dl._chuan_hoa_url("https://x.com/a"))


# -------------------------------------------------------------------- route
def test_route_topic_ra_dung_vai():
    import chat_router as cr
    topics = {"scout": 11, "writer": 22, "carousel-edu": 33}
    assert cr.route(11, topics) == ("scout", "tele-scout")
    assert cr.route(33, topics) == ("carousel-edu", "tele-carousel-edu")


def test_route_topic_la_khong_ra_profile_nhung_van_co_phien():
    """Topic khong co trong TOPIC_PROFILE: profile None (hermes dung profile mac
    dinh) nhung phien van rieng theo topic — hai topic la khong duoc dung chung
    mot phien chat."""
    import chat_router as cr
    assert cr.route(99, {}) == (None, "tele-general")
    assert cr.route(44, {"la_hoac": 44}) == (None, "tele-la_hoac")


# ---------------------------------------------------------------- _HangFIFO
def test_hang_fifo_dung_thu_tu_duoi_nhieu_luong():
    import duyet_chat as dc
    h = dc._HangFIFO()
    ra, khoa = [], threading.Lock()

    # lay so TUAN TU (dung nhu vong poll: mot thread nhan tin), roi tha ra
    sos = []
    for i in range(5):
        sos.append(h.lay_so())
    assert [s[1] for s in sos] == [0, 1, 2, 3, 4], "so nguoi dung truoc sai"
    # phuc vu theo dung thu tu ve
    for _ in range(5):
        h.release()

    h2 = dc._HangFIFO()
    ts = []
    for i in range(5):
        so, _ = h2.lay_so()               # lay so trong thread chinh -> thu tu chac chan
        t = threading.Thread(target=_phuc_vu, args=(h2, so, i, ra, khoa))
        ts.append(t)
    for t in ts:
        t.start()
    for t in ts:
        t.join(5)
    assert ra == [0, 1, 2, 3, 4], f"khong FIFO: {ra}"


def _phuc_vu(h, so, i, ra, khoa):
    h.doi(so)
    with khoa:
        ra.append(i)
    h.release()


def test_hang_fifo_bao_dung_so_nguoi_dang_doi():
    """Con so nay di thang vao tin 'dang tra loi N tin truoc' gui cho Ong Chu."""
    import duyet_chat as dc
    h = dc._HangFIFO()
    assert h.lay_so() == (0, 0)           # nguoi dau: khong ai truoc
    assert h.lay_so() == (1, 1)
    assert h.lay_so() == (2, 2)
    h.release()                           # nguoi 0 xong
    assert h.lay_so() == (3, 2)           # con 2 nguoi truoc, khong phai 3


# ------------------------------------------------------- gom_trung / chuan_hoa
def _tin(td, ts, toa="x"):
    return {"tieu_de": td, "ts": ts, "toa_soan": toa, "link": "", "goc": "g"}


def test_gom_trung_gop_cung_su_kien_khac_dong_tu():
    """Ca Cloverleaf kinh dien trong docstring cua gom_trung: Reuters viet
    'invests in', TechCrunch viet 'partners with' — mot su kien."""
    import scan_business as sb
    tin = [_tin("Nvidia invests in data center developer Cloverleaf Infrastructure", 100, "reuters"),
           _tin("Nvidia partners with data center developer Cloverleaf", 200, "techcrunch")]
    ra = sb.gom_trung(tin)
    assert len(ra) == 1, [t["tieu_de"] for t in ra]
    assert ra[0]["so_bao"] == 2
    assert ra[0]["ts"] == 100, "phai giu ban som nhat"


def test_gom_trung_khong_gop_hai_tin_nguoc_nhau():
    """Phan con lai cua cung docstring: mau so la MAX chu khong phai MIN, neu
    khong thi 'Nvidia stock jumps' nuot 'Nvidia stock slides after...' — hai tin
    NGUOC nhau thanh mot va Vera bao nham chieu."""
    import scan_business as sb
    tin = [_tin("Nvidia stock jumps", 100),
           _tin("Nvidia stock slides after Beijing bans chip purchases", 200)]
    ra = sb.gom_trung(tin)
    assert len(ra) == 2, f"gop nham hai tin nguoc nhau: {[t['tieu_de'] for t in ra]}"


def test_chuan_hoa_lam_khoa_dedup_on_dinh():
    import scan_business as sb
    a = sb.chuan_hoa("Nvidia's Q3 Revenue Jumps 34%!")
    b = sb.chuan_hoa("nvidia's  q3 revenue jumps 34%")
    assert a == b, f"{a!r} != {b!r}"
    assert a, "chuoi rong -> moi tin cung mot khoa"
    assert sb.chuan_hoa("Nvidia buys X") != sb.chuan_hoa("Nvidia sells X")


def test_ten_watchlist_theo_bien_gioi_tu():
    """Docstring khai 'arm' khong duoc khop 'harm'."""
    import scan_business as sb
    assert sb.ten_watchlist("Arm raises guidance") is not None
    assert sb.ten_watchlist("New harm reduction policy for AI") is None


# ------------------------------------------------------------- cap_fallback
def test_cap_fallback_doc_tu_config_dang_chay():
    """Hang so `FALLBACK_THAT` chi co cap (v4-flash -> deepseek-chat), von khong
    con profile nao dung tu khi doi combo 05/09/2026 — nen `m["fallback"]` luon
    0 va `van_de()` khong bao gio danh thuc ai. Cap phai duoc dung TU config."""
    import tempfile
    import theo_doi_9router as t
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / ".hermes-blog"
        (home / "profiles" / "writer").mkdir(parents=True)
        (home / "profiles" / "writer" / "config.yaml").write_text(
            "model:\n  default: DS-v4Flash\n"
            "fallback_providers:\n  - model: ds/deepseek-v4-pro\n"
            "  - model: ds/deepseek-chat\n", encoding="utf-8")
        cu = t.HERMES_HOMES
        t.HERMES_HOMES = [home]
        try:
            cap = t.cap_fallback()
        finally:
            t.HERMES_HOMES = cu
    assert ("ds-v4flash", "deepseek-v4-pro") in cap, sorted(cap)
    assert ("deepseek-v4-pro", "deepseek-chat") in cap, sorted(cap)
    assert ("deepseek-v4-flash", "deepseek-chat") in cap, "phai giu ca hang so cu"


def test_cap_fallback_bo_qua_chuoi_trung_ten():
    """Combo lat giua ba route CUNG mot model khong phai fallback — usage ghi
    cung mot `model` nen dem vao la bao dong gia moi ngay."""
    import tempfile
    import theo_doi_9router as t
    with tempfile.TemporaryDirectory() as tmp:
        home = Path(tmp) / ".hermes-dcgr"
        home.mkdir(parents=True)
        (home / "config.yaml").write_text(
            "model:\n  default: ds/deepseek-v4-flash\n"
            "fallback_providers:\n  - model: ds/deepseek-v4-flash\n", encoding="utf-8")
        cu = t.HERMES_HOMES
        t.HERMES_HOMES = [home]
        try:
            cap = t.cap_fallback()
        finally:
            t.HERMES_HOMES = cu
    assert cap == set(t.FALLBACK_THAT), f"them cap trung ten: {sorted(cap)}"


if __name__ == "__main__":
    ham = [v for k, v in list(globals().items()) if k.startswith("test_")]
    loi = 0
    for h in ham:
        try:
            h()
            print(f"OK   {h.__name__}")
        except AssertionError as e:
            loi += 1
            print(f"FAIL {h.__name__}: {e}")
    print(f"\n{len(ham) - loi}/{len(ham)} test qua")
    sys.exit(1 if loi else 0)
