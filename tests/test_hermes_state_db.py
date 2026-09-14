#!/usr/bin/env python3
"""`hermes_adapter` đọc profiles/<vai>/state.db — mặt ghép nối thứ 6 với hermes
(audit lượt 2, ADF-r2-3).

Trước đây monitor_9router (bảng `session_model_usage`) và ada_prepare (bảng
`sessions`) đọc thẳng bằng SQL thô, `except: continue` — hermes đổi một cột là
nhật ký và brief của Ada hỏng câm sau `hermes update`. Nay hai câu SELECT nằm
trong adapter, cột dùng khai ở `_COT_DUNG_MODEL`/`_COT_PHIEN`, và
`check_hermes.COLUMN_CAN_STATE` phải KHỚP — test cuối giữ hai bảng đó không lệch.

Chạy:  venv/bin/python tests/test_hermes_state_db.py
"""
import sqlite3
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import hermes_adapter as ha                                   # noqa: E402
import check_hermes                                            # noqa: E402


def _state_db(tmp):
    """state.db toi gian voi dung cac cot adapter dung (mo phong schema hermes)."""
    p = Path(tmp) / "profiles" / "miles" / "state.db"
    p.parent.mkdir(parents=True)
    con = sqlite3.connect(p)
    con.executescript("""
    create table session_model_usage(session_id text, model text, api_call_count int,
        input_tokens int, output_tokens int, cache_read_tokens int, reasoning_tokens int,
        last_seen int);
    create table sessions(session_id text, title text, tool_call_count int, input_tokens int,
        api_call_count int, started_at int);
    insert into session_model_usage values
        ('s1','gpt-5',3,1000,200,50,10,1000), ('s2','gpt-5',2,500,100,0,0,1500),
        ('s3','claude',1,700,300,0,0,1200), ('s4','gpt-5',9,9,9,9,9,5000);
    insert into sessions values
        ('s1','viet bai A',12,1000,3,1000), ('s2','viet bai B',4,500,2,1500),
        ('s0','cu',1,1,1,10);
    """)
    con.commit()
    con.close()
    return p


def test_dung_theo_model_gop_theo_model_trong_cua_so():
    with tempfile.TemporaryDirectory() as t:
        p = _state_db(t)
        ra = ha.use_by_model(p, 1000, 2000)          # s4 (5000) nam ngoai
        assert ra is not None
        theo = {r["model"]: r for r in ra}
        assert theo["gpt-5"]["api"] == 5 and theo["gpt-5"]["in"] == 1500, theo
        assert theo["gpt-5"]["phien"] == 2 and theo["claude"]["phien"] == 1, theo


def test_tom_tat_phien_dem_va_top():
    with tempfile.TemporaryDirectory() as t:
        p = _state_db(t)
        tt = ha.summary_session(p, 100)                    # s0 (10) bi loai
        assert tt == {"phien": 2, "tool": 16, "input": 1500, "api": 5,
                      "top": [("viet bai A", 12, 1000), ("viet bai B", 4, 500)]}, tt


def test_state_db_hong_thi_None_khong_phai_rong():
    """C1: hong moi truong phai lo ra. Truoc day `except: continue` — vai bien
    mat khoi nhat ky ma khong ai hay."""
    with tempfile.TemporaryDirectory() as t:
        p = Path(t) / "state.db"
        p.write_bytes(b"khong phai sqlite")
        assert ha.use_by_model(p, 0, 9) is None
        assert ha.summary_session(p, 0) is None
        assert ha.use_by_model(Path(t) / "khong_co.db", 0, 9) is None


def test_state_db_cac_profile_liet_ke_dung_home():
    with tempfile.TemporaryDirectory() as t:
        p = _state_db(t)
        assert ha.state_db_each_profile(t) == [p]
        assert ha.state_db_each_profile(Path(t) / "rong") == []


def test_cot_adapter_khop_kiem_hermes():
    """Adapter va check_hermes la HAI bang chep tay — lech nhau la check_hermes
    xanh tren server ma adapter vo (dung loi review Fable bat o C2)."""
    assert set(ha._COT_DUNG_MODEL) == set(check_hermes.COLUMN_CAN_STATE["session_model_usage"])
    assert set(ha._COT_PHIEN) == set(check_hermes.COLUMN_CAN_STATE["sessions"])


def test_kiem_bang_bat_duoc_cot_thieu():
    with tempfile.TemporaryDirectory() as t:
        p = _state_db(t)
        assert check_hermes._check_board("thu", p, check_hermes.COLUMN_CAN_STATE) == []
        loi = check_hermes._check_board("thu", p, {"sessions": ["title", "cot_khong_co"]})
        assert loi and "cot_khong_co" in loi[0], loi


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
