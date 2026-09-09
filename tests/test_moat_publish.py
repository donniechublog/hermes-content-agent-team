#!/usr/bin/env python3
"""E3 -- test cho `moat_publish.intake` va `moat_publish.poll`.

Day bai da duyet sang moat (hang doi publish Facebook/Instagram) la duong hai
chieu tu chinh host nay chu dong, khong ai goi nguoc vao: `intake(draft_id)`
day mot draft, `poll()` hoi trang thai cac bai da day. Ca hai deu cam ket
"khong bao gio nem ngoai le" (xem docstring cua tung ham trong moat_publish.py)
-- rot mang hay rot cau hinh moat chi duoc PHEP tra ve (False, note)/[], khong
duoc lam vo cron hay luong duyet bai tren Telegram.

Khong co server moat that de goi trong test: MOI cho co the goi HTTP deu duoc
mock qua `httpx.MockTransport`, boc trong mot doi tuong thay THE BINDING module-
level `moat_publish.httpx` (khong dung cham vao module `httpx` that/sys.modules,
nen an toan phuc hoi bang try/finally nhu moi bien khac). `moat_publish.py` chi
co DUNG hai cho goi `httpx.Client(...)` luc chay (dong 284 trong `intake`, dong
312 trong `_fetch_status` ma `poll()` -> `_poll_mot_bai` goi toi) -- da doi
chieu bang grep truoc khi viet, nen fake object chi can mot thuoc tinh `Client`.

`DRAFTS` (thu muc drafts that su) va cac ham cau hinh (`base_url`, `config`,
`brand_container`, `read_draft`, `write_draft`) deu la BIEN/HAM Muc module cua
moat_publish.py, duoc goi qua ten global (khong qua class) -- nen monkeypatch
thang thuoc tinh module (`mp.TEN = ...` trong try/finally) la du, giong cach
tests/test_ha_san_nut.py da lam voi `db.STATE_DIR`/`db.call`.

Chay:  python tests/test_moat_publish.py
"""
import json
import sys
import tempfile
import time
import types
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import moat_publish as mp          # noqa: E402


def _fake_httpx_module(handler):
    """Thay THE cho ten global `httpx` ben trong moat_publish: `.Client(...)`
    tra ve mot httpx.Client THAT nhung ep dung MockTransport, nen khong co goi
    mang nao thoat ra ngoai may test. Chi dinh nghia `.Client` vi day la thuoc
    tinh DUY NHAT cua module httpx ma moat_publish dung luc chay (da grep xac
    nhan; `httpx.Timeout` chi dung luc IMPORT de dung TIMEOUT_DAY/TIMEOUT, tuc
    truoc khi monkeypatch co hieu luc, nen khong can co mat o day)."""
    transport = httpx.MockTransport(handler)

    def fake_client(*args, **kwargs):
        kwargs["transport"] = transport
        return httpx.Client(*args, **kwargs)

    return types.SimpleNamespace(Client=fake_client)


# =========================================================================
# intake()
# =========================================================================
def test_intake_draft_khong_doc_duoc_tra_false_khong_nem_ngoai_le():
    """read_draft nem loi (tep hong/mat) -> intake PHAI bat lai, tra (False,
    note co ngu canh loi), khong duoc de ngoai le thoat ra ngoai ham."""
    def hong(draft_id):
        raise OSError("khong tim thay tep draft")

    cu = mp.read_draft
    mp.read_draft = hong
    try:
        ok, note = mp.intake("draft-khong-ton-tai")
    finally:
        mp.read_draft = cu

    assert ok is False
    assert "khong doc duoc draft" in note, f"note thieu ngu canh: {note!r}"
    assert "khong tim thay tep draft" in note, f"note khong giu loi goc: {note!r}"


def test_intake_chua_co_config_moat_tra_false_ro_ly_do():
    """config(brand) tra (None, None) -- brand nay chua khai MOAT_BASE_URL/khoa
    -- intake phai dung LAI o day, tra false kem ten thuong hieu, KHONG duoc di
    tiep den buoc goi API."""
    draft = {"brand": "donniechublog", "caption": "abc",
             "images": ["http://x.test/anh.jpg"]}
    cu_read, cu_config = mp.read_draft, mp.config
    mp.read_draft = lambda draft_id: dict(draft)
    mp.config = lambda brand=None: (None, None)
    try:
        ok, note = mp.intake("draft-chua-cau-hinh")
    finally:
        mp.read_draft, mp.config = cu_read, cu_config

    assert ok is False
    assert "chua cau hinh" in note, f"note phai noi ro chua cau hinh: {note!r}"
    assert "donniechublog" in note, f"note phai neu dung thuong hieu: {note!r}"


def test_intake_da_day_truoc_do_khong_goi_lai_api():
    """d['moat']['workflow_id'] da co san (bai nay day roi tu lan truoc) ->
    intake tra (True, "da day truoc do") NGAY, tuyet doi khong goi lai HTTP --
    dem so lan httpx.Client duoc tao de xac nhan, khong doan mo."""
    draft = {
        "brand": "donniechublog",
        "caption": "abc",
        "images": ["http://x.test/anh.jpg"],
        "moat": {"workflow_id": "wf-da-day-tu-truoc"},
    }
    so_lan_tao_client = []

    def fake_client(*args, **kwargs):
        so_lan_tao_client.append((args, kwargs))
        return None            # khong duoc goi toi day; None se lam intake tu
                                # bat loi (AttributeError o __enter__) va tra
                                # (False, ...) -- assert ok is True se lo ngay.

    cu_read = mp.read_draft
    cu_config = mp.config
    cu_httpx = mp.httpx
    mp.read_draft = lambda draft_id: dict(draft)
    mp.config = lambda brand=None: ("http://fake-moat.test", "fake-key")
    mp.httpx = types.SimpleNamespace(Client=fake_client)
    try:
        ok, note = mp.intake("draft-da-day")
    finally:
        mp.read_draft, mp.config, mp.httpx = cu_read, cu_config, cu_httpx

    assert ok is True, f"phai coi la thanh cong (idempotent): {note!r}"
    assert note == "da day truoc do", f"note sai: {note!r}"
    assert so_lan_tao_client == [], "khong duoc goi lai API moat khi da co workflow_id"


def test_intake_thanh_cong_day_duoc_va_ghi_workflow_id_vao_draft():
    """Duong vui: draft hop le, config day du, moat tra 200 kem workflowId ->
    intake tra (True, note co so task), va ghi dung workflow_id/brand vao
    draft qua write_draft (mock write_draft de khong dung tep that trong
    drafts/ that cua repo)."""
    draft = {
        "brand": "donniechublog",
        "caption": "Ban tin thu nghiem, khong dau <b>dam</b>.",
        "images": ["http://x.test/anh1.jpg"],
        "category": "NEWS",
    }

    def handler(request):
        assert request.url.path == "/publish-intake"
        assert request.headers.get("X-API-Key") == "fake-key"
        body = json.loads(request.content.decode("utf-8"))
        assert body["externalId"] == "draft-thanh-cong"
        # Boc the HTML: chu_thuan() phai da go <b> truoc khi gui sang moat.
        assert "<b>" not in body["caption"]
        return httpx.Response(200, json={
            "workflowId": "wf-moi-123",
            "externalId": "draft-thanh-cong",
            "tasks": [{"id": "t1"}, {"id": "t2"}],
        })

    ghi_lai = []
    cu_read = mp.read_draft
    cu_config = mp.config
    cu_write = mp.write_draft
    cu_httpx = mp.httpx
    mp.read_draft = lambda draft_id: dict(draft)
    mp.config = lambda brand=None: ("http://fake-moat.test", "fake-key")
    mp.write_draft = lambda draft_id, data: ghi_lai.append((draft_id, data))
    mp.httpx = _fake_httpx_module(handler)
    try:
        ok, note = mp.intake("draft-thanh-cong")
    finally:
        mp.read_draft = cu_read
        mp.config = cu_config
        mp.write_draft = cu_write
        mp.httpx = cu_httpx

    assert ok is True, f"phai thanh cong: {note!r}"
    assert note == "da xep 2 task publish", f"note sai: {note!r}"
    assert len(ghi_lai) == 1, f"phai ghi draft dung MOT lan: {ghi_lai}"
    draft_id_ghi, data_ghi = ghi_lai[0]
    assert draft_id_ghi == "draft-thanh-cong"
    assert data_ghi["moat"]["workflow_id"] == "wf-moi-123"
    assert data_ghi["moat"]["brand"] == "donniechublog"


# =========================================================================
# poll()
# =========================================================================
def test_poll_khong_co_base_url_tra_ve_rong():
    """Chua cau hinh MOAT_BASE_URL (che do lui ve khong day moat) -> poll()
    phai dung ngay o dong dau, tra [] -- khong duoc do thu muc drafts/."""
    cu = mp.base_url
    mp.base_url = lambda: ""
    try:
        ket_qua = mp.poll()
    finally:
        mp.base_url = cu
    assert ket_qua == [], f"phai tra ve rong khi chua cau hinh: {ket_qua}"


def test_poll_thu_muc_drafts_rong_tra_ve_rong():
    """DRAFTS ton tai nhung khong co tep .json nao -> khong co gi de duyet,
    poll() tra ve []."""
    with tempfile.TemporaryDirectory() as tmp:
        cu_base_url = mp.base_url
        cu_drafts = mp.DRAFTS
        cu_brand = mp.brand_container
        mp.base_url = lambda: "http://fake-moat.test"
        mp.DRAFTS = Path(tmp)
        mp.brand_container = lambda: ""
        try:
            ket_qua = mp.poll()
        finally:
            mp.base_url = cu_base_url
            mp.DRAFTS = cu_drafts
            mp.brand_container = cu_brand

        assert ket_qua == [], f"thu muc rong phai tra ve rong: {ket_qua}"


def test_poll_mot_draft_hop_le_chay_khong_crash_va_bao_dung_trang_thai():
    """Mot draft da day (co d['moat']['external_id']), moat tra ve hai task:
    mot published mot failed -> poll() khong crash VA sinh dung hai dong bao,
    dung nhan nen tang, dung URL/loi. Uu tien do TIN CAY: dung MockTransport
    that su thay vi chi kiem tra "khong nem ngoai le" suong."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "draft-dang-theo-doi.json").write_text(json.dumps({
            "brand": "donniechublog",
            "moat": {
                "workflow_id": "wf-dang-theo-doi",
                "external_id": "ext-1",
                "brand": "donniechublog",
                "platforms": ["facebook_post", "instagram_carousel"],
                "pushed_at": int(time.time()),
                "reported": {},
            },
        }, ensure_ascii=False), encoding="utf-8")

        def handler(request):
            return httpx.Response(200, json={"tasks": [
                {"id": "t1", "status": "published", "platform": "facebook",
                 "result_url": "https://facebook.com/post/1"},
                {"id": "t2", "status": "failed", "platform": "instagram",
                 "last_error": "loi upload"},
            ]})

        cu_base_url = mp.base_url
        cu_drafts = mp.DRAFTS
        cu_brand = mp.brand_container
        cu_config = mp.config
        cu_httpx = mp.httpx
        mp.base_url = lambda: "http://fake-moat.test"
        mp.DRAFTS = tmp_path
        mp.brand_container = lambda: ""
        mp.config = lambda brand=None: ("http://fake-moat.test", "fake-key")
        mp.httpx = _fake_httpx_module(handler)
        try:
            lines = mp.poll()
        finally:
            mp.base_url = cu_base_url
            mp.DRAFTS = cu_drafts
            mp.brand_container = cu_brand
            mp.config = cu_config
            mp.httpx = cu_httpx

        assert len(lines) == 2, f"phai co dung 2 dong thong bao: {lines}"
        assert "đã lên Facebook" in lines[0], lines[0]
        assert "https://facebook.com/post/1" in lines[0], lines[0]
        assert "đăng Instagram lỗi: loi upload" in lines[1], lines[1]


def test_poll_bo_qua_file_meta_json_khong_parse_thanh_draft():
    """`path.name.endswith(".meta.json")` (dong 428) phai loai file nay TRUOC
    ca json.loads. Dung noi dung la MOT JSON HOP LE nhung KHONG PHAI dict
    ([]) thay vi JSON loi: try/except quanh json.loads trong poll() se nuot
    MOI loi parse du dong 428 co ton tai hay khong, nen JSON loi khong phan
    biet duoc "bi bo qua dung cho" voi "vo tinh parse hong roi cung bi nuot".
    JSON hop le nhung sai kieu thi khac: neu dong 428 bi go/hong, file se lot
    qua json.loads (khong loi), roi bay thang vao _poll_mot_bai(path, d, ...)
    voi d la list -- d.get("moat") nem AttributeError NGAY, ma khong try/except
    nao trong poll() bao boc loi nay ca (try/except o do chi quanh rieng
    json.loads). Poll() chay xong khong crash tuc la dong 428 that su chay."""
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "draft-nao-do.meta.json").write_text("[]", encoding="utf-8")

        cu_base_url = mp.base_url
        cu_drafts = mp.DRAFTS
        cu_brand = mp.brand_container
        mp.base_url = lambda: "http://fake-moat.test"
        mp.DRAFTS = tmp_path
        mp.brand_container = lambda: ""
        try:
            lines = mp.poll()
        finally:
            mp.base_url = cu_base_url
            mp.DRAFTS = cu_drafts
            mp.brand_container = cu_brand

        assert lines == [], f".meta.json phai bi bo qua hoan toan: {lines}"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
