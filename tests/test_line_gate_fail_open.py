#!/usr/bin/env python3
"""LOW-fail-open: `lien_quan=None` không còn là "duyệt mặc định" (Ông Chủ
12/09/2026: *"đóng luôn cổng fail-open"*).

Đo trên máy chủ 12/09: ảnh trụ sở Tesla (Terafab) và một ứng viên thương hiệu
Anthropic đều lọt bìa dù router ĐÃ TRẢ LỜI — chỉ là câu trả lời không đọc ra
được dòng LIEN_QUAN, và mọi nơi lọc `dung_duoc` viết `lien_quan is not False`
nên None trôi qua như đã duyệt.

Luật mới trong `prepare.vision.description_image`:
  - HỎI ĐƯỢC nhưng không đọc ra LIEN_QUAN -> hỏi lại ĐÚNG 1 LẦN; vẫn không đọc
    ra thì COI LÀ RỚT (`False`), không còn là `None`.
  - KHÔNG HỎI ĐƯỢC (thiếu key, hoặc mạng/router hỏng ngay từ lần đầu) -> giữ
    nguyên `None` — đây là "vision tắt" có chủ đích ở nơi khác (kite_submit.py),
    không phải ca cần đóng.

Chạy:  venv/bin/python tests/test_line_gate_fail_open.py
"""
import sys
import tempfile
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import prepare.vision as vision                                   # noqa: E402

_TAM = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
_TAM.write(b"\x89PNG\r\n\x1a\n" + b"\0" * 32)
_TAM.close()
ANH = _TAM.name


class _Resp:
    def __init__(self, txt: str):
        import json
        self._b = json.dumps({"choices": [{"message": {"content": txt}}]}).encode()

    def read(self):
        return self._b


LEN_XEP = "MO_TA: một tấm ảnh.\nLIEN_QUAN: khong"     # dung dinh dang
LECH_DINH_DANG = "Đây là một tấm ảnh trụ sở, có vẻ liên quan tới bài."  # KHONG co dong LIEN_QUAN


def _with_key(f):
    def _boc(*a, **k):
        with mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}):
            return f(*a, **k)
    _boc.__name__ = f.__name__
    return _boc


@_with_key
def test_read_out_date_then_no_ask_again():
    """Đường thường: đọc ra LIEN_QUAN ngay lần 1 thì KHÔNG có lần hỏi thứ hai."""
    goi = {"n": 0}

    def _goi(req, _ngu=None):
        goi["n"] += 1
        return _Resp(LEN_XEP)

    with mock.patch.object(vision, "_call_router", side_effect=_goi):
        mt, lq = vision.description_image(ANH, "Tin gì đó")
    assert lq is False and goi["n"] == 1, (lq, goi["n"])


@_with_key
def test_offset_format_attempt_1_read_ok_attempt_2_then_use_sentence_return_error_attempt_2():
    """Lần 1 lệch định dạng (None), lần 2 đọc ra được -> dùng kết quả lần 2,
    KHÔNG phải mặc định duyệt hay mặc định rớt."""
    goi = {"n": 0}

    def _goi(req, _ngu=None):
        goi["n"] += 1
        return _Resp(LECH_DINH_DANG if goi["n"] == 1 else LEN_XEP)

    with mock.patch.object(vision, "_call_router", side_effect=_goi):
        mt, lq = vision.description_image(ANH, "Tin gì đó")
    assert lq is False and goi["n"] == 2, (lq, goi["n"])


@_with_key
def test_offset_format_all_two_attempt_then_fail_no_right_none():
    """Đo thật 12/09: router trả lời cả hai lần nhưng không lần nào đọc ra được
    LIEN_QUAN — TRƯỚC ĐÂY đây là chỗ None lọt qua làm bìa. Giờ phải RỚT."""
    goi = {"n": 0}

    def _goi(req, _ngu=None):
        goi["n"] += 1
        return _Resp(LECH_DINH_DANG)

    with mock.patch.object(vision, "_call_router", side_effect=_goi):
        mt, lq = vision.description_image(ANH, "Tin gì đó")
    assert lq is False, "hỏi được 2 lần mà không đọc ra LIEN_QUAN lần nào -> phải RỚT, không phải None"
    assert goi["n"] == 2, "phải hỏi lại đúng 1 lần (tổng 2 lần gọi), không hơn"


def test_missing_key_still_keep_none_no_ask_again():
    """'Vision tắt' (thiếu OPENAI_API_KEY) là ca có chủ đích ở nơi khác
    (kite_submit.py) — KHÔNG đóng, và không tốn thêm lượt hỏi nào."""
    # LOW-127: description_image tu goi env_load.load() — may chu co secret.*.env that
    # nen xoa os.environ khong du, key bi nap lai va router bi goi (do: (None, 1)).
    with mock.patch.dict("os.environ", {}, clear=True), \
         mock.patch.object(vision.env_load, "load", lambda *a, **k: None), \
         mock.patch.object(vision, "_call_router") as m:
        mt, lq = vision.description_image(ANH, "Tin gì đó")
    assert lq is None and m.call_count == 0, (lq, m.call_count)


@_with_key
def test_network_broken_date_attempt_mark_still_keep_none_no_force_fail():
    """Lần đầu KHÔNG HỎI ĐƯỢC (mạng/router ném lỗi, không phải 'trả lời lệch
    định dạng') -> vẫn là 'chưa ai nhìn' (None), không tự ý coi là rớt."""
    def _goi(req, _ngu=None):
        raise TimeoutError("router khong phan hoi")

    with mock.patch.object(vision, "_call_router", side_effect=_goi):
        mt, lq = vision.description_image(ANH, "Tin gì đó")
    assert lq is None, lq


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
