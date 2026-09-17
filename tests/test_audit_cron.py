#!/usr/bin/env python3
"""Job soat cron — cai duy nhat bao khi mot job cron chet.

Vi sao phai co test: job nay la NGUOI CANH cuoi cung. Moi loi im lang khac
trong repo con co no de lo ra; no im lang thi khong con ai. Va ba kieu hong
nang nhat (ticker dung, job bi pause, job bi tat) khong sinh mot lan chay nao,
tuc `failure_streak` van bang 0 — chung chi bi bat neu chinh cac phep so o day
dung.

Chay:  venv/bin/python tests/test_audit_cron.py
"""
import json
import sys
import tempfile
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

BAY_GIO = time.time()


def _iso(lech_giay: float) -> str:
    return (datetime.now(timezone.utc) + timedelta(seconds=lech_giay)).isoformat()


def _home(goc: Path, ten: str, jobs, nhip=0.0, thanh=None):
    """Dung mot HERMES_HOME gia. `nhip`/`thanh`: so giay TRUOC bay gio."""
    h = goc / ten
    (h / "cron").mkdir(parents=True, exist_ok=True)
    (h / "cron" / "jobs.json").write_text(json.dumps({"jobs": jobs}), encoding="utf-8")
    (h / "cron" / "ticker_heartbeat").write_text(str(BAY_GIO - nhip), encoding="utf-8")
    (h / "cron" / "ticker_last_success").write_text(
        str(BAY_GIO - (nhip if thanh is None else thanh)), encoding="utf-8")
    return h


def _job(ten, **k):
    d = {"name": ten, "enabled": True, "state": "scheduled", "failure_streak": 0,
         "last_status": "ok", "last_error": None, "last_delivery_error": None,
         "next_run_at": _iso(600)}
    d.update(k)
    return d


def _ten(van_de):
    return {f"{m['brand']}/{m['name']}": m["severity"] for m in van_de}


# ---------------------------------------------------------------- job binh thuong
def test_moi_thu_khoe_thi_khong_bao_gi():
    import audit_cron as sc
    with tempfile.TemporaryDirectory() as t:
        g = Path(t)
        homes = {"blog": _home(g, "blog", [_job("finn-daily-scan"), _job("daily-log")]),
                 "dcgr": _home(g, "dcgr", [_job("vera-daily-scan")])}
        van_de, tong, thieu = sc.audit(homes, BAY_GIO)
        assert van_de == [], f"bao nham khi moi thu khoe: {van_de}"
        assert tong == 3, tong
        assert thieu == []


# ---------------------------------------------------------------- failure_streak
def test_failure_streak_va_last_error_deu_ra_HONG():
    import audit_cron as sc
    with tempfile.TemporaryDirectory() as t:
        g = Path(t)
        homes = {"blog": _home(g, "blog", [
            _job("finn-daily-scan", failure_streak=3, last_status="error",
                 last_error="quet LOI: khong tao duoc task")])}
        van_de, _, _ = sc.audit(homes, BAY_GIO)
        assert _ten(van_de) == {"blog/finn-daily-scan": "BROKEN"}, _ten(van_de)
        ly = " | ".join(van_de[0]["reasons"])
        assert "3 lần" in ly and "khong tao duoc task" in ly, ly


def test_khong_gui_duoc_ket_qua_cung_la_HONG():
    """`last_delivery_error`: job chay xong ma ket qua khong toi ai — dung kieu
    hong ma `last_status: ok` che mat."""
    import audit_cron as sc
    with tempfile.TemporaryDirectory() as t:
        homes = {"blog": _home(Path(t), "blog", [
            _job("daily-log", last_delivery_error="chat not found")]) }
        van_de, _, _ = sc.audit(homes, BAY_GIO)
        assert _ten(van_de) == {"blog/daily-log": "BROKEN"}, _ten(van_de)


# ---------------------------------------------- ba kieu hong KHONG co lan chay nao
def test_job_bi_tat_va_bi_pause_deu_lo_ra():
    """Ca hai deu giu failure_streak = 0 va last_status = ok mai mai."""
    import audit_cron as sc
    with tempfile.TemporaryDirectory() as t:
        homes = {"blog": _home(Path(t), "blog", [
            _job("model-watch", enabled=False),
            _job("vera-daily-scan", state="paused", paused_reason="gateway restart")])}
        van_de, _, _ = sc.audit(homes, BAY_GIO)
        assert _ten(van_de) == {"blog/model-watch": "OFF",
                                "blog/vera-daily-scan": "OFF"}, _ten(van_de)


def test_ticker_dung_bao_MOT_dong_cho_ca_kho():
    """Ticker chet = moi job dong bang. Bao mot dong ve ticker, khong phai N
    dong 'le hen' noi cung mot chuyen."""
    import audit_cron as sc
    with tempfile.TemporaryDirectory() as t:
        homes = {"dcgr": _home(Path(t), "dcgr",
                               [_job("vera-daily-scan"), _job("daily-log")],
                               nhip=3 * 3600)}
        van_de, _, _ = sc.audit(homes, BAY_GIO)
        assert _ten(van_de) == {"dcgr/ticker": "STUCK"}, _ten(van_de)
        assert "3 giờ" in van_de[0]["reasons"][0], van_de[0]["reasons"]


def test_ticker_song_ma_moi_tick_deu_hong():
    """Nhip con dap (thread song) nhung khong tick nao thanh cong — truong hop
    `hermes cron status` sinh ra hai tep moc de phan biet."""
    import audit_cron as sc
    with tempfile.TemporaryDirectory() as t:
        homes = {"blog": _home(Path(t), "blog", [_job("daily-log")],
                               nhip=10, thanh=4 * 3600)}
        van_de, _, _ = sc.audit(homes, BAY_GIO)
        assert _ten(van_de) == {"blog/ticker": "STUCK"}, _ten(van_de)


def test_nguong_ticker_bam_theo_hermes_cron_status():
    """200s = TICKER_INTERVAL_SECONDS * 3 + 20. Duoi nguong khong duoc bao —
    khong thi moi lan restart gateway la mot bao dong gia."""
    import audit_cron as sc
    assert sc.TICK_OLD == 200, sc.TICK_OLD
    with tempfile.TemporaryDirectory() as t:
        g = Path(t)
        assert sc.audit({"b": _home(g, "b", [_job("x")], nhip=199)}, BAY_GIO)[0] == []
        assert sc.audit({"c": _home(g, "c", [_job("x")], nhip=201)}, BAY_GIO)[0] != []


# ---------------------------------------------------------------- le hen
def test_job_le_hen_ra_KET_con_job_dang_tat_thi_khong():
    """`next_run_at` nam lai qua khu = scheduler khong no. Nhung job dang TAT
    thi moc cu la binh thuong — bao la bao nham."""
    import audit_cron as sc
    with tempfile.TemporaryDirectory() as t:
        homes = {"blog": _home(Path(t), "blog", [
            _job("daily-log", next_run_at=_iso(-3600)),
            _job("model-watch", enabled=False, next_run_at=_iso(-99999))])}
        van_de, _, _ = sc.audit(homes, BAY_GIO)
        assert _ten(van_de) == {"blog/daily-log": "STUCK",
                                "blog/model-watch": "OFF"}, _ten(van_de)
        assert len([m for m in van_de if m["name"] == "model-watch"][0]["reasons"]) == 1


def test_le_hen_it_hon_15_phut_khong_tinh():
    """Restart gateway lam lech vai phut la chuyen thuong."""
    import audit_cron as sc
    with tempfile.TemporaryDirectory() as t:
        homes = {"blog": _home(Path(t), "blog", [_job("x", next_run_at=_iso(-600))])}
        assert sc.audit(homes, BAY_GIO)[0] == []


# ---------------------------------------------------------------- kho theo profile
def test_soat_ca_kho_cron_cua_tung_profile():
    """Hermes tach cron theo profile (cron/jobs.py, #4707): job cua profile
    `coder` nam o <home>/profiles/coder/cron/jobs.json. Chi soat kho goc la bo
    sot ca mot nhom job."""
    import audit_cron as sc
    with tempfile.TemporaryDirectory() as t:
        g = Path(t)
        h = _home(g, "blog", [_job("daily-log")])
        p = h / "profiles" / "coder"
        (p / "cron").mkdir(parents=True)
        (p / "cron" / "jobs.json").write_text(
            json.dumps({"jobs": [_job("coder-job", failure_streak=9)]}), encoding="utf-8")
        (p / "cron" / "ticker_heartbeat").write_text(str(BAY_GIO), encoding="utf-8")
        (p / "cron" / "ticker_last_success").write_text(str(BAY_GIO), encoding="utf-8")
        van_de, tong, _ = sc.audit({"blog": h}, BAY_GIO)
        assert _ten(van_de) == {"blog/coder/coder-job": "BROKEN"}, _ten(van_de)
        assert tong == 2, tong


# ---------------------------------------------------------------- home / tep hong
def test_home_bien_mat_thi_bao_rieng_khong_phai_im():
    import audit_cron as sc
    with tempfile.TemporaryDirectory() as t:
        g = Path(t)
        van_de, _, thieu = sc.audit({"blog": _home(g, "blog", [_job("x")]),
                                    "dcgr": g / "khong-co"}, BAY_GIO)
        assert thieu == ["dcgr"], thieu
        assert van_de == []


def test_jobs_json_hong_khong_lam_ca_lan_soat_chet():
    """Kho hong la mot phat hien, khong phai mot traceback — con hai brand kia
    van phai duoc soat."""
    import audit_cron as sc
    with tempfile.TemporaryDirectory() as t:
        g = Path(t)
        h = _home(g, "blog", [_job("x")])
        (h / "cron" / "jobs.json").write_text("{ khong phai json", encoding="utf-8")
        ok = _home(g, "dcgr", [_job("y", failure_streak=2)])
        van_de, _, _ = sc.audit({"blog": h, "dcgr": ok}, BAY_GIO)
        muc = sorted(m["severity"] for m in van_de)
        assert muc == ["BROKEN", "BROKEN"], van_de
        assert any("dcgr/y" == f"{m['brand']}/{m['name']}" for m in van_de), van_de


# ---------------------------------------------------------------- chong bao trung
def test_khoa_khong_doi_khi_streak_tang():
    """Chu ky bo van de KHONG gom ly do: streak 3 -> 4 khong phai tin moi, va
    neu tinh ca ly do thi container thu hai nhan lai y het."""
    import audit_cron as sc
    a = [{"brand": "blog", "name": "finn", "severity": "BROKEN", "reasons": ["hỏng 3 lần"]}]
    b = [{"brand": "blog", "name": "finn", "severity": "BROKEN", "reasons": ["hỏng 4 lần"]}]
    assert sc.lock_still_for(a) == sc.lock_still_for(b)


def test_khoa_doi_khi_co_them_job_hong():
    import audit_cron as sc
    a = [{"brand": "blog", "name": "finn", "severity": "BROKEN", "reasons": []}]
    b = a + [{"brand": "dcgr", "name": "vera", "severity": "STUCK", "reasons": []}]
    assert sc.lock_still_for(a) != sc.lock_still_for(b)


# ---------------------------------------------------------------- tin nhan
def test_tin_nhan_escape_HTML_trong_loi():
    """stderr co `<module>` / `&` -> Telegram tu choi CA tin voi loi parse HTML,
    tuc dung hom co loi thi canh bao bien mat (loi da sua o journal_web)."""
    import audit_cron as sc
    van_de = [{"brand": "blog", "name": "daily-log", "severity": "BROKEN",
               "reasons": ['lỗi: File "<stdin>", line 1 & <module>']}]
    tin = sc.use_story(van_de, 9, [], "07/09", 2)
    assert "<stdin>" not in tin and "&lt;stdin&gt;" in tin, tin
    assert "&amp;" in tin, tin
    # The cua chinh minh phai con nguyen, khong bi escape lay.
    assert "<b>blog / daily-log</b>" in tin, tin


def test_tin_nhan_dem_ca_home_bien_mat():
    import audit_cron as sc
    tin = sc.use_story([], 0, ["dcgr"], "07/09", 2)
    assert "1 hỏng" in tin, tin


def test_severity_codes_follow_table_and_printed_words_stay():
    """LOW-239: `severity` la ma English trong bang; chu in ra stdout (HONG/KET/TAT, ban
    ghi duy nhat khi Telegram hong) va icon trong tin giu nguyen nhu truoc."""
    import audit_cron as sc
    table = json.loads((ROOT / "docs" / "tu_dien_ten" / "journal_keys_v2.json").read_text(encoding="utf-8"))
    codes = table["audit_cron_issue.severity"]
    assert sc.SEVERITY_LABELS == {new: old for old, new in codes.items()}, sc.SEVERITY_LABELS
    assert sc.ITEM == {codes["HONG"]: "🔴", codes["KET"]: "🟠", codes["TAT"]: "⚪"}, sc.ITEM
    assert sc.MARK.name == "cron_audit.json" and sc.MARK.parent.name == "state", sc.MARK


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
