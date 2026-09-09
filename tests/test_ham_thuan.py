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
  - `env_load.brand_dai` doi CT_BRAND (ten NGAN cho state, "blog"/"dcgr") ra slug
                     thuong hieu DAI ("donniechublog"/"dcgr") ma card.py doi.
                     Sinh 09/09/2026: lan thang CT_BRAND vao card.dat_thuong_hieu
                     lam SystemExit "Khong biet thuong hieu 'blog'", giet ca
                     `chuan_bi()" — bat HAI cho lam sai giong het nhau trong cung
                     mot lan chay lai (anh_chuan_bi.py va anh_thuong_hieu.py).

Chay:  venv/bin/python tests/test_ham_thuan.py
"""
import os
import sys
import threading
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


# ------------------------------------------------------------- env_load.brand_dai
def test_brand_dai_doi_dung_ca_hai_chieu():
    """CT_BRAND ('blog') phai ra 'donniechublog' — chinh loi bat 09/09/2026 (hai
    cho trong anh_thuong_hieu.py truyen thang CT_BRAND vao card.dat_thuong_hieu,
    nem 'Khong biet thuong hieu blog' vi card.py chi biet slug DAI)."""
    import env_load
    cu = os.environ.get("CT_BRAND")
    try:
        os.environ["CT_BRAND"] = "blog"
        assert env_load.brand_dai() == "donniechublog"
        os.environ["CT_BRAND"] = "dcgr"
        assert env_load.brand_dai() == "dcgr"          # trung ca hai chieu, sao cung dung
    finally:
        if cu is None:
            os.environ.pop("CT_BRAND", None)
        else:
            os.environ["CT_BRAND"] = cu


def test_brand_dai_khong_biet_thi_ve_mac_dinh():
    """CT_BRAND rong/la (che do don, hoac gia tri khong ro) -> mac_dinh, khong nem."""
    import env_load
    cu = os.environ.get("CT_BRAND")
    try:
        os.environ.pop("CT_BRAND", None)
        assert env_load.brand_dai() == "donniechublog"
        os.environ["CT_BRAND"] = "khong-ro"
        assert env_load.brand_dai("dcgr") == "dcgr"
    finally:
        if cu is None:
            os.environ.pop("CT_BRAND", None)
        else:
            os.environ["CT_BRAND"] = cu


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


# --------------------------------------------------- allowlist va ma bai
def test_la_ong_chu_khong_co_tep_thi_cho_qua():
    """Chua co state/ong_chu.json = giu hanh vi cu (group rieng). Neu doi thanh
    "chan het" thi bat cai nay len la khoa chet may dang chay."""
    import tempfile
    import duyet_co_so as cs
    with tempfile.TemporaryDirectory() as tmp:
        cu = cs.ONG_CHU_IDS
        cs.ONG_CHU_IDS = Path(tmp) / "khong-co.json"
        try:
            assert cs.la_ong_chu({"from": {"id": 999}}) is True
        finally:
            cs.ONG_CHU_IDS = cu


def test_la_ong_chu_co_tep_thi_chan_nguoi_la():
    import json as _j
    import tempfile
    import duyet_co_so as cs
    with tempfile.TemporaryDirectory() as tmp:
        p = Path(tmp) / "ong_chu.json"
        p.write_text(_j.dumps([8112291996]), encoding="utf-8")
        cu = cs.ONG_CHU_IDS
        cs.ONG_CHU_IDS = p
        try:
            assert cs.la_ong_chu({"from": {"id": 8112291996}}) is True
            assert cs.la_ong_chu({"from": {"id": 12345}}) is False
            assert cs.la_ong_chu({}) is False          # nut khong co `from`
            assert cs.la_ong_chu(None) is False
        finally:
            cs.ONG_CHU_IDS = cu


def test_ma_bai_tu_nut_phai_khop_mau():
    """`draft_id` trong callback_data den tu client va di THANG vao duong dan
    tep. `_draft_id` sinh no bang slugify nen moi id that deu khop mau nay."""
    import duyet_bai as db
    import duyet_chon_tin as dct
    hop_le = db._DRAFT_ID_HOP_LE
    # id that do chinh he thong sinh ra phai qua duoc
    tin = {"title": "Nvidia đàm phán rót 2,5 tỷ USD vào Thinking Machines", "index": 3}
    that = dct._draft_id(tin, "donniechublog", "carousel")
    assert hop_le.match(that), that
    for xau in ["../../state/blog/lam_lai_cho", "a/b", "..", "", "A-Hoa",
                "x" * 60, "tin_gach_duoi", "-mo-dau-bang-gach"]:
        assert not hop_le.match(xau), f"nhan ma bai xau: {xau!r}"


# ------------------------------------------------------------- host noi bo
NOI_BO = ["127.0.0.1", "127.1", "127.0.1", "2130706433", "0x7f.0.0.1",
          "::1", "[::1]", "localhost", "10.0.0.5", "192.168.1.61",
          "169.254.169.254", "172.16.0.1", "172.31.255.1", "0.0.0.0",
          "may.local", "x.internal", "abc.netbird.mated"]
CONG_KHAI = ["openai.com", "172.32.0.1", "8.8.8.8", "1.1.1.1",
             "vnexpress.net", "news.ycombinator.com", "arxiv.org"]


def test_host_noi_bo_bat_ca_dang_viet_rut_gon():
    """Cong cu chi so khop CHUOI nen "127.0.0.1" bi chan con "127.1",
    "2130706433" va "[::1]" thi khong — dung ba cach vong qua ma libc (curl,
    chromium, httpx) van hieu."""
    import quet_chung as qc
    sot = [h for h in NOI_BO if not qc.host_noi_bo(h)]
    assert not sot, f"khong chan: {sot}"


def test_host_cong_khai_khong_bi_chan_oan():
    """Chan oan con te hon bo lot: day chuyen se im lang khong tai duoc anh."""
    import quet_chung as qc
    oan = [h for h in CONG_KHAI if qc.host_noi_bo(h)]
    assert not oan, f"chan oan: {oan}"


def test_kiem_url_chan_scheme_khong_phai_http():
    """chup_chart tai bang urllib, ma urllib nhan ca `file://`."""
    import quet_chung as qc
    for u in ["file:///etc/passwd", "ftp://x.com/a", "data:text/html,x", "x"]:
        assert not qc.url_an_toan(u), u
    assert qc.url_an_toan("https://openai.com/index/abc")


def test_moi_duong_tai_deu_qua_cong():
    """Doc bang AST: cac ham tai da duoc noi vao cong. Them mot duong tai moi
    ma quen goi cong la mo lai cua da dong."""
    import ast
    # `_tai_bytes` sang chuan_bi/tai_loc.py khi tach goi 09/09/2026 (audit A1) —
    # cong host van phai duoc goi y nhu cu, chi doi cho tim.
    for tep, ham in [("chuan_bi/tai_loc.py", "_tai_bytes"), ("anh_bai.py", "_tai"),
                     ("chup_chart.py", "tai_anh"), ("article_extract.py", "fetch")]:
        cay = ast.parse((ROOT / tep).read_text(encoding="utf-8"))
        f = next((n for n in ast.walk(cay)
                  if isinstance(n, ast.FunctionDef) and n.name == ham), None)
        assert f, f"{tep}: khong thay ham {ham}"
        goi = {ast.unparse(n.func) for n in ast.walk(f) if isinstance(n, ast.Call)}
        assert any("kiem_url" in g or "url_an_toan" in g or "_kiem_host" in g
                   for g in goi), f"{tep}:{ham} khong goi cong host"


# --------------------------------------------------------- dung_argv (chat)
def test_argv_chat_khong_bao_gio_co_z():
    """Dung doan da gay su co 04/09: `-z` duoc hermes_cli xu ly TRUOC va thoat
    ngay, nen `--continue` bi bo qua IM LANG va MOI tin mo mot phien moi — vai
    nao cung "khong nho gi". Truoc day muon kiem dong lenh nay phai chay ca mot
    tien trinh hermes that."""
    import chat_router as cr
    a = cr.dung_argv("writer", "tele-writer", "xin chao", "safe")
    assert "-z" not in a, a
    assert a[a.index("chat") + 1:a.index("chat") + 3] == ["-c", "tele-writer"]
    for co in ("--create-if-missing", "--no-restore-cwd", "-Q", "-q"):
        assert co in a, f"thieu {co}: {a}"
    assert a[a.index("--toolsets") + 1] == "safe"
    assert a[:2] == [a[0], "-m"] and a[2] == "hermes_cli.main"


def test_argv_khong_profile_thi_khong_co_co_p():
    import chat_router as cr
    a = cr.dung_argv(None, "tele-general", "x")
    assert "-p" not in a, a
    assert "--toolsets" not in a


def test_argv_khop_ban_ke_khai_cua_kiem_hermes():
    """`kiem_hermes.CO_CHAT` la danh sach co ma script kiem sau moi
    `hermes update`. Hai ban ke khai nay phai khop, khong thi kiem_hermes bao
    xanh cho mot dong lenh khong con dung."""
    import chat_router as cr
    import kiem_hermes as kh
    a = set(cr.dung_argv("writer", "tele-writer", "x"))
    thieu = [c for c in kh.CO_CHAT if c not in a]
    assert not thieu, f"kiem_hermes doi co {thieu} ma dung_argv khong sinh ra"


# ------------------------------------------------------------ tong_hop (9router)
# Tach khoi `doc_ngay` 07/09/2026. Phep dem o day quyet dinh nhung thu khong lo
# ra khi sai: nhan khoa API (chi duoc 4 ky tu cuoi — bao cao nay duoc ghi ra dia
# VA phuc vu qua nhat_ky_web), cap lat model nao tinh la fallback, model nao bi
# goi la "tra rong".
def _dong(giay, model="ds/deepseek-v4-pro", cid="c1", ak="sk-abcd1234efgh",
          status=None, ptok=2000, ctok=500, cost=0.01, cache=0):
    """Mot dong usageHistory, dung thu tu SELECT cua doc_ngay."""
    import json as _j
    from datetime import datetime, timedelta, timezone
    ts = (datetime(2026, 9, 5, 17, 0, tzinfo=timezone.utc)
          + timedelta(seconds=giay)).isoformat().replace("+00:00", "Z")
    return (ts, model.split("/")[0], model, cid, ak, status, ptok, ctok, cost,
            _j.dumps({"cached_tokens": cache}))


def test_tong_hop_khong_bao_gio_ghi_khoa_api_tho():
    """Khoa da xoay khong con trong bang `apiKeys` — ban truoc 06/09/2026 lay
    CHINH CHUOI KHOA lam nhan, roi nhan do di vao json/md va ra trang HTTP."""
    import theo_doi_9router as tr
    d, _ = tr.tong_hop([_dong(0, ak="sk-SIEU-BI-MAT-9999")], cap_fb=set())
    nhan = list(d["theo_khoa"])
    assert nhan == ["khoa la …9999"], nhan
    assert "SIEU-BI-MAT" not in repr(d), "khoa tho lot vao bao cao"


def test_tong_hop_lay_ten_khoa_khi_con_trong_bang():
    import theo_doi_9router as tr
    d, _ = tr.tong_hop([_dong(0, ak="sk-x1")], {"sk-x1": "blog"}, cap_fb=set())
    assert list(d["theo_khoa"]) == ["blog"]


def test_tong_hop_dem_lat_model_trong_nguong_va_bo_qua_ngoai_nguong():
    """Lat model = hai lan goi LIEN TIEP khac model, cach nhau <= GIAY_LAT."""
    import theo_doi_9router as tr
    gan = [_dong(0, "a"), _dong(tr.GIAY_LAT - 1, "b")]
    xa = [_dong(0, "a"), _dong(tr.GIAY_LAT + 1, "b")]
    lap = [_dong(0, "a"), _dong(10, "a")]
    assert tr.tong_hop(gan, cap_fb=set())[0]["lat_model"] == {"a → b": 1}
    assert tr.tong_hop(xa, cap_fb=set())[0]["lat_model"] == {}
    assert tr.tong_hop(lap, cap_fb=set())[0]["lat_model"] == {}


def test_tong_hop_chi_dem_fallback_dung_cap_duoc_khai():
    """`fallback` la con so Ong Chu doc de biet model chinh co dang chet khong.
    Dem moi lan lat vao day la bao dong gia moi ngay."""
    import theo_doi_9router as tr
    rows = [_dong(0, "chinh"), _dong(5, "phu"), _dong(200, "chinh"), _dong(205, "la")]
    d, _ = tr.tong_hop(rows, cap_fb={("chinh", "phu")})
    assert d["fallback"] == 1, d["lat_model"]
    assert tr.tong_hop(rows, cap_fb=set())[0]["fallback"] == 0


def test_tong_hop_bat_tra_loi_rong_va_khong_bat_lan_bao_loi():
    """Prompt to ma out ~0 nhung status ok = model nuot tien khong tra gi. Lan
    BAO LOI thi da co muc `loi` roi, dem hai lan la doc ra hai su co."""
    import theo_doi_9router as tr
    rows = [_dong(0, "a", ptok=tr.RONG_PROMPT_MIN, ctok=tr.RONG_OUT_MAX),
            _dong(300, "b", ptok=tr.RONG_PROMPT_MIN, ctok=tr.RONG_OUT_MAX + 1),
            _dong(600, "c", ptok=tr.RONG_PROMPT_MIN - 1, ctok=0),
            _dong(900, "d", ptok=99999, ctok=0, status="error 429")]
    d, _ = tr.tong_hop(rows, cap_fb=set())
    assert d["rong"] == {"a": 1}, d["rong"]
    assert d["loi"] == {"d: error 429": 1}, d["loi"]
    assert d["tong"]["loi"] == 1


def test_tong_hop_cache_pct_va_tong_tien():
    import theo_doi_9router as tr
    rows = [_dong(0, ptok=1000, cache=250, cost=0.5),
            _dong(300, ptok=3000, cache=750, cost=0.25)]
    d, tho = tr.tong_hop(rows, cap_fb=set())
    assert d["tong"]["cache_pct"] == 25.0, d["tong"]
    assert d["tong"]["usd"] == 0.75
    assert tho["tong"]["usd"] == 0.75, "tho phai la ban CHUA lam tron"


def test_tong_hop_top_prompt_lay_5_lan_ton_nhat():
    import theo_doi_9router as tr
    rows = [_dong(i * 300, ptok=(i + 1) * 1000) for i in range(8)]
    d, _ = tr.tong_hop(rows, cap_fb=set())
    assert [x["prompt"] for x in d["top_prompt"]] == [8000, 7000, 6000, 5000, 4000]


def test_tong_hop_ngay_rong_khong_no():
    """Ngay khong co luot goi nao (9router vua restart) van phai ra bao cao."""
    import theo_doi_9router as tr
    d, tho = tr.tong_hop([], cap_fb=set())
    assert d["tong"]["req"] == 0 and d["tong"]["cache_pct"] == 0.0
    assert d["theo_model"] == {} and d["top_prompt"] == []
    assert tho["tong"]["prompt"] == 0


def test_tong_hop_khong_cham_vao_dia():
    """Ham THUAN — no khong duoc mo CSDL hay doc config. Neu mot ban sau lai
    goi `cap_fallback()` vo dieu kien thi test nay do (cap_fb da truyen vao)."""
    import theo_doi_9router as tr
    goi = []
    that = tr.cap_fallback
    tr.cap_fallback = lambda: goi.append(1) or set()
    try:
        tr.tong_hop([_dong(0)], cap_fb=set())
    finally:
        tr.cap_fallback = that
    assert goi == [], "tong_hop van tu doc config du da duoc truyen cap_fb"


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
