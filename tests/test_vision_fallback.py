#!/usr/bin/env python3
"""Vision co du phong (LOW-326, 20/09/2026): model chinh KHONG TRA LOI DUOC thi hoi
`VISION_FALLBACK_MODEL` dung MOT lan; mot cau tra loi "khong lien quan" that thi KHONG
bi hoi lai.

Nguon goc: DeepSeek het tien 05/09 va 20/09 — `description_image` nuot loi thanh "CHUA AI
NHIN" cho MOI anh, engine mu ca ngay. Do 20/09 tren 300 anh co nhan Ong Chu, model chinh
doi sang ag/gemini-3.8-flash, DeepSeek giu lam du phong (khac nha cung cap).

`vision._call_router` bi thay hoan toan o day nen backoff 429/5xx cua no KHONG duoc chay:
test nay chi kiem viec CHUYEN model, con backoff da co test_seen_parallel.

Chay:  venv/bin/python tests/test_vision_fallback.py
"""
import http.client
import io
import json
import socket
import sys
import tempfile
import urllib.error
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import env_load                                                 # noqa: E402
from prepare import vision                                      # noqa: E402

PRIMARY, FALLBACK = "test/primary", "test/fallback"
YES = "MO_TA: tru so hang.\nLIEN_QUAN: co\nCLUTTERED: khong\nTU_KHOA: co"
NO = "MO_TA: quang cao ban hang.\nLIEN_QUAN: khong"


class _Res:
    def __init__(self, data: bytes):
        self._d = data

    def read(self):
        return self._d


def _answer(text: str) -> bytes:
    return json.dumps({"choices": [{"message": {"content": text}}]}).encode()


def _http_error(code: int):
    return urllib.error.HTTPError("http://127.0.0.1:20128/v1/chat/completions", code, "loi", {}, None)


class _Router:
    """Thay `vision._call_router`. `script`: {model: [buoc, ...]}; moi buoc la bytes (than tra
    loi) hoac mot exception se bi nem. Het buoc thi lap lai buoc cuoi."""

    def __init__(self, script):
        self.script = {m: list(s) for m, s in script.items()}
        self.models = []

    def __call__(self, req, _ngu=None):
        model = json.loads(req.data)["model"]
        self.models.append(model)
        steps = self.script[model]
        step = steps.pop(0) if len(steps) > 1 else steps[0]
        if isinstance(step, BaseException):
            raise step
        return _Res(step)


def _run(script, primary=PRIMARY, fallback=FALLBACK):
    """(ket qua, ket_qua dict, stderr, cac model da duoc hoi theo thu tu)."""
    from PIL import Image
    router, found = _Router(script), {}
    with tempfile.TemporaryDirectory() as tmp, \
         mock.patch.dict("os.environ", {"OPENAI_API_KEY": "x"}), \
         mock.patch.object(vision, "VISION_MODEL", primary), \
         mock.patch.object(vision, "VISION_FALLBACK_MODEL", fallback), \
         mock.patch.object(vision, "_call_router", router):
        p = Path(tmp) / "a.png"
        Image.new("RGB", (4, 4), (200, 200, 200)).save(p)
        cu, sys.stderr = sys.stderr, io.StringIO()
        try:
            res = vision.description_image(str(p), "TSMC ra chip moi", ket_qua=found)
            err = sys.stderr.getvalue()
        finally:
            sys.stderr = cu
    return res, found, err, router.models


def test_primary_answer_is_used_and_fallback_is_never_asked():
    res, found, err, models = _run({PRIMARY: [_answer(YES)], FALLBACK: [AssertionError("khong duoc hoi")]})
    assert res[1] is True, res
    assert models == [PRIMARY], models
    assert found["vision_raw"]["model"] == PRIMARY
    assert FALLBACK not in err, err


def test_primary_http_error_asks_fallback_once():
    """DeepSeek het tien tra 402 (ba vao 503) — dung ca goc su co 20/09."""
    res, found, err, models = _run({PRIMARY: [_http_error(402)], FALLBACK: [_answer(YES)]})
    assert res[1] is True, res
    assert models == [PRIMARY, FALLBACK], models
    assert found["vision_raw"]["model"] == FALLBACK, "ghi lai model THAT SU da nhin anh"
    assert PRIMARY in err and FALLBACK in err and "HTTPError" in err, err


def test_primary_timeout_asks_fallback():
    res, _, _, models = _run({PRIMARY: [socket.timeout("timed out")], FALLBACK: [_answer(YES)]})
    assert res[1] is True and models == [PRIMARY, FALLBACK], (res, models)


def test_primary_connection_refused_asks_fallback():
    refused = urllib.error.URLError(ConnectionRefusedError(111, "Connection refused"))
    res, _, _, models = _run({PRIMARY: [refused], FALLBACK: [_answer(YES)]})
    assert res[1] is True and models == [PRIMARY, FALLBACK], (res, models)


def test_primary_broken_json_asks_fallback():
    res, _, _, models = _run({PRIMARY: [b"<html>502 bad gateway</html>"], FALLBACK: [_answer(YES)]})
    assert res[1] is True and models == [PRIMARY, FALLBACK], (res, models)


def test_primary_reply_without_choices_asks_fallback():
    body = json.dumps({"error": {"message": "No active credentials for provider"}}).encode()
    res, _, _, models = _run({PRIMARY: [body], FALLBACK: [_answer(YES)]})
    assert res[1] is True and models == [PRIMARY, FALLBACK], (res, models)


def test_primary_http_client_exception_asks_fallback():
    res, _, _, models = _run({PRIMARY: [http.client.IncompleteRead(b"ab")], FALLBACK: [_answer(YES)]})
    assert res[1] is True and models == [PRIMARY, FALLBACK], (res, models)


def test_both_models_down_leaves_the_image_unseen_not_rejected():
    """Ca hai hong = "chua ai nhin" (None) nhu cu, KHONG bien thanh "khong lien quan"."""
    res, _, err, models = _run({PRIMARY: [_http_error(503)], FALLBACK: [_http_error(402)]})
    assert res == ("", None), res
    assert models == [PRIMARY, FALLBACK], models
    assert "HTTPError" in err, err


def test_a_real_no_from_primary_is_final():
    """Model chinh TRA LOI "khong lien quan" — do la cau tra loi, khong phai loi: khong hoi lai."""
    res, found, _, models = _run({PRIMARY: [_answer(NO)], FALLBACK: [_answer(YES)]})
    assert res[1] is False, res
    assert models == [PRIMARY], models
    assert found["vision_raw"]["model"] == PRIMARY


def test_programming_error_is_not_masked_by_a_second_call():
    """Loi lap trinh khong phai "model khong tra loi duoc": khong hoi doi so luot de che loi."""
    res, _, err, models = _run({PRIMARY: [AttributeError("bug")], FALLBACK: [_answer(YES)]})
    assert res == ("", None), res
    assert models == [PRIMARY], models
    assert "AttributeError" in err, err


def test_no_fallback_configured_asks_only_the_primary():
    for fallback in ("", PRIMARY):
        res, _, _, models = _run({PRIMARY: [_http_error(503)], FALLBACK: [_answer(YES)]}, fallback=fallback)
        assert res == ("", None), (fallback, res)
        assert models == [PRIMARY], (fallback, models)


def test_reask_after_unparseable_answer_can_still_fall_back():
    """Lan dau model chinh tra loi nhung khong doc ra LIEN_QUAN -> hoi lai; lan hai router chet
    -> du phong nhin, khong roi vao "COI LA ROT"."""
    res, found, _, models = _run({PRIMARY: [_answer("khong biet"), _http_error(503)],
                                  FALLBACK: [_answer(YES)]})
    assert res[1] is True, res
    assert models == [PRIMARY, PRIMARY, FALLBACK], models
    assert found["vision_raw"]["model"] == FALLBACK


def test_fallback_is_a_different_provider_from_primary():
    """Bai hoc LOW-324: du phong cung nha cung cap voi model chinh thi chet cung luc."""
    assert env_load.VISION_MODEL and env_load.VISION_FALLBACK_MODEL
    assert env_load.VISION_MODEL.split("/")[0] != env_load.VISION_FALLBACK_MODEL.split("/")[0], \
        "VISION_FALLBACK_MODEL phai di tuyen 9router KHAC VISION_MODEL"
    assert vision.VISION_MODEL == env_load.VISION_MODEL
    assert vision.VISION_FALLBACK_MODEL == env_load.VISION_FALLBACK_MODEL


def test_monitor_knows_both_vision_models():
    """Model du phong xuat hien trong usage ma monitor khong biet = bi bao "model la"."""
    import monitor_9router as mon
    with tempfile.TemporaryDirectory() as tmp, mock.patch.object(mon, "HERMES_HOMES", [Path(tmp)]):
        names = mon.string_already_config()
    for model in (env_load.VISION_MODEL, env_load.VISION_FALLBACK_MODEL):
        for ten in mon._each_name(model):
            assert "engine anh:vision" in names.get(ten, []), (model, ten)


if __name__ == "__main__":
    import role
    role.set_active_role("ethan")            # xem tam.chay_tat_ca (LOW-182)
    ok = 0
    ten = [n for n in dir() if n.startswith("test_")]
    for n in ten:
        try:
            globals()[n]()
            ok += 1
        except AssertionError as e:
            print(f"FAIL {n}: {e}")
    print(f"{ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
