#!/usr/bin/env python3
"""check_env.py — chặn đầu trước khi chạy engine (LOW-307, module 0% độ phủ).

Nghịch lý đáng giữ: đây là tệp có nhiệm vụ KÊU khi môi trường thiếu, mà chính nó
lại chưa bao giờ được test. Thiếu cv2 hay thiếu model YuNet đều làm `_load_yunet()`
trả None và cổng mặt người TỰ TẮT không một dòng báo — `check_env` là chỗ duy
nhất phân biệt được hai lý do đó.

Hợp đồng test này giữ:
  * mỗi `check_*` trả `(ok, lý_do)` và **không bao giờ ném ra ngoài**;
  * một mục hỏng KHÔNG được làm mất khả năng báo các mục còn lại (quy ước C1) —
    kể cả khi chính hàm kiểm crash;
  * mã thoát: 0 khi đủ, 1 khi thiếu (script này đứng trước engine trong setup.sh);
  * thiếu FILE model và thiếu GÓI cv2 phải ra hai lý do khác nhau.

Chay:  venv/bin/python tests/test_check_env.py
"""
import contextlib
import io
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import check_env as ce                                       # noqa: E402
import env_load                                              # noqa: E402


@contextlib.contextmanager
def _env(**kv):
    cu = {k: os.environ.get(k) for k in kv}
    for k, v in kv.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
    try:
        yield
    finally:
        for k, v in cu.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


@contextlib.contextmanager
def _items(ds):
    cu = ce.ITEM_CHECK
    ce.ITEM_CHECK = ds
    try:
        yield
    finally:
        ce.ITEM_CHECK = cu


def _main():
    """Chạy `main()` không cho nó nạp secret thật; trả (mã thoát, những gì đã in)."""
    cu_load, cu_out, cu_argv = env_load.load, sys.stdout, sys.argv
    env_load.load = lambda *a, **k: None
    sys.stdout = io.StringIO()
    sys.argv = ["check_env.py"]
    try:
        ma = ce.main()
        return ma, sys.stdout.getvalue()
    finally:
        env_load.load, sys.stdout, sys.argv = cu_load, cu_out, cu_argv


# ---------- biến môi trường ----------

def test_variable_set_then_ok():
    with _env(BIEN_THU_LOW307="co gia tri"):
        assert ce.check_variable_environment("BIEN_THU_LOW307") == (True, "")


def test_variable_empty_counts_as_missing():
    """Chuỗi rỗng KHÔNG phải là "đã đặt" — token rỗng gửi Telegram im lặng."""
    with _env(BIEN_THU_LOW307=""):
        ok, ly_do = ce.check_variable_environment("BIEN_THU_LOW307")
    assert ok is False and "chua dat" in ly_do, (ok, ly_do)


def test_telegram_token_missing_says_it_may_be_on_purpose():
    """Bob tắt Telegram có chủ ý — lý do phải nói thế, không tự kết luận sai cấu hình."""
    with _env(TELEGRAM_BOT_TOKEN=None):
        ok, ly_do = ce.check_telegram_token()
    assert ok is False and "CO Y" in ly_do and "bob_submit.py" in ly_do, ly_do


def test_openai_key_present_then_ok():
    with _env(OPENAI_API_KEY="sk-gia"):
        assert ce.check_openai_key()[0] is True


# ---------- cv2 & YuNet ----------

def test_cv2_ok_reports_version_on_this_machine():
    ok, ly_do = ce.check_cv2()
    assert ok is True and ly_do.startswith("ban "), (ok, ly_do)


def test_cv2_missing_says_how_to_install_and_does_not_raise():
    import builtins
    that = builtins.__import__

    def no(ten, *a, **k):
        if ten == "cv2":
            raise ImportError("gia vo thieu cv2")
        return that(ten, *a, **k)
    builtins.__import__ = no
    try:
        ok, ly_do = ce.check_cv2()
    finally:
        builtins.__import__ = that
    assert ok is False and "pip install opencv-python" in ly_do, ly_do


def test_yunet_ok_on_this_machine():
    ok, ly_do = ce.check_yunet()
    assert ok is True, ly_do


def test_missing_model_file_is_a_different_reason_than_missing_cv2():
    """Hai nguyên nhân cùng cho `_load_yunet() -> None`; lý do phải tách được."""
    import image_rules_ethan as rules
    cu = rules.__file__
    with tempfile.TemporaryDirectory() as t:
        rules.__file__ = str(Path(t) / "image_rules_ethan.py")
        try:
            ok, ly_do = ce.check_yunet()
        finally:
            rules.__file__ = cu
    assert ok is False and "khong thay file model" in ly_do, ly_do
    assert ce.NAME_MODEL_YUNET in ly_do, ly_do


def test_yunet_returning_none_points_back_at_cv2():
    import image_rules_ethan as rules
    cu = rules._load_yunet
    rules._load_yunet = lambda: None
    try:
        ok, ly_do = ce.check_yunet()
    finally:
        rules._load_yunet = cu
    assert ok is False and "xem muc cv2 o tren" in ly_do, ly_do


def test_yunet_loader_blowing_up_is_caught_not_raised():
    import image_rules_ethan as rules
    cu = rules._load_yunet

    def no():
        raise RuntimeError("onnx hong")
    rules._load_yunet = no
    try:
        ok, ly_do = ce.check_yunet()
    finally:
        rules._load_yunet = cu
    assert ok is False and "RuntimeError: onnx hong" in ly_do, ly_do


# ---------- Chromium ----------

def test_chromium_missing_playwright_says_how_to_install():
    that = sys.modules.pop("playwright.sync_api", None)
    sys.modules["playwright.sync_api"] = None       # import -> ImportError
    try:
        ok, ly_do = ce.check_chromium()
    finally:
        if that is None:
            sys.modules.pop("playwright.sync_api", None)
        else:
            sys.modules["playwright.sync_api"] = that
    assert ok is False and "pip install playwright" in ly_do, ly_do


# ---------- tổng kết & mã thoát ----------

def test_all_ok_then_exit_zero_and_says_so():
    with _items([("muc mot", lambda: (True, "")), ("muc hai", lambda: (True, "ghi chu"))]):
        ma, ra = _main()
    assert ma == 0 and "2/2 muc OK" in ra and "[OK]" in ra, (ma, ra)
    assert "OK     muc mot" in ra and "muc hai: ghi chu" in ra, ra


def test_one_missing_then_exit_one_and_counts():
    with _items([("muc mot", lambda: (True, "")), ("muc hai", lambda: (False, "thieu roi"))]):
        ma, ra = _main()
    assert ma == 1 and "1/2 muc OK" in ra and "[THIEU] 1 muc" in ra, (ma, ra)
    assert "THIEU  muc hai: thieu roi" in ra, ra


def test_one_check_crashing_does_not_kill_the_rest():
    """Quy ước C1: một mục hỏng không được làm mất khả năng báo các mục còn lại."""
    def no():
        raise RuntimeError("tu crash")
    with _items([("muc no", no), ("muc sau", lambda: (True, ""))]):
        ma, ra = _main()
    assert ma == 1, ma
    assert "ham kiem tu crash: RuntimeError: tu crash" in ra, ra
    assert "OK     muc sau" in ra, "mục sau mục crash không được chạy"


def test_status_column_is_aligned():
    """`OK   ` và `THIEU` cùng 5 ký tự — lệch cột là bảng khó đọc lúc đang sự cố."""
    with _items([("a", lambda: (True, "")), ("b", lambda: (False, "x"))]):
        _ma, ra = _main()
    dong = [d for d in ra.splitlines() if d.startswith(("OK", "THIEU"))]
    assert len({d.index(" ", 6) for d in dong}) == 1, dong


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M
    chay_tat_ca(globals())
