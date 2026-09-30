#!/usr/bin/env python3
"""D21 (audit 30/09/2026): (a) bandit bao 14 HIGH gia — md5/sha1 dung de khu trung,
khong phai bao mat; (b) token bot Telegram nam trong URL nen ngoai le `{e!r}` kem
URL la kem luon token vao log.

(a) khoa bang AST: moi `hashlib.md5/sha1(...)` trong ma nguon phai co
    `usedforsecurity=False` (dong thoi khong doi gia tri bam — test rieng).
(b) khoa o `write_log.log()` — mot cho, moi `log/warn/error` va ca dong ghi ra
    TEP approve.log deu di qua do; cong them cac cho print thang (publish,
    route_missing_images, moat_publish) qua `write_log.redact`.

Chay:  venv/bin/python tests/test_d21_hash_and_token_redact.py
"""
import ast
import hashlib
import io
import logging
import logging.handlers
import os
import subprocess
import sys
import warnings
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import write_log                                             # noqa: E402
import tam                                                   # noqa: E402
import test_write_log_level as wl                            # noqa: E402

TOKEN = "123456789:AAFake-Token_abc123XYZ"
URL = f"https://api.telegram.org/bot{TOKEN}/sendMessage"


# ---------------------------------------------------------------- (a) bam
def _tracked_py():
    out = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True,
                         text=True, check=True).stdout.split()
    return [ROOT / f for f in out if not f.startswith("tests/")]


def test_every_md5_sha1_call_declares_usedforsecurity_false():
    thieu = []
    for f in _tracked_py():
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")               # SyntaxWarning '\s' cua tep cu, khong lien quan
            cay = ast.parse(f.read_text(encoding="utf-8"))
        for n in ast.walk(cay):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)
                    and n.func.attr in ("md5", "sha1")
                    and isinstance(n.func.value, ast.Name) and n.func.value.id == "hashlib"):
                if not any(k.arg == "usedforsecurity" and isinstance(k.value, ast.Constant)
                           and k.value.value is False for k in n.keywords):
                    thieu.append(f"{f.name}:{n.lineno}")
    assert not thieu, thieu


def test_usedforsecurity_false_keeps_the_same_digest():
    assert hashlib.md5(b"abc", usedforsecurity=False).hexdigest() == "900150983cd24fb0d6963f7d28e17f72"
    assert hashlib.sha1(b"abc", usedforsecurity=False).hexdigest() == \
        "a9993e364706816aba3e25717850c26c9cd0d89d"
    h = hashlib.sha1(usedforsecurity=False)
    h.update(b"abc")
    assert h.hexdigest() == "a9993e364706816aba3e25717850c26c9cd0d89d"


# ---------------------------------------------------------------- (b) token
def test_redact_replaces_bot_token_only():
    r = write_log.redact(f"POST {URL} that bai; chat 12345 khong doi")
    assert TOKEN not in r and "bot<redacted>/sendMessage" in r, r
    assert "chat 12345 khong doi" in r
    assert write_log.redact("khong co token") == "khong co token"


def test_log_redacts_exception_repr_for_every_level():
    exc = RuntimeError(f"Client error '404 Not Found' for url '{URL}'")
    for goi in (lambda w: w.log("loi", f"gui hong: {exc!r}"),
                lambda w: w.warn("tele", f"gui hong: {exc}"),
                lambda w: w.error("tele", f"gui hong: {exc!r}")):
        with redirect_stdout(io.StringIO()):          # handler stdout gan sys.stdout luc tao
            cap, restore = wl._fresh_logger()
        try:
            with redirect_stdout(io.StringIO()):
                goi(write_log)
            assert len(cap.records) == 1
            msg = cap.records[0].getMessage()
            assert TOKEN not in msg and "AAFake" not in msg, msg
            assert "bot<redacted>/sendMessage" in msg, msg
        finally:
            restore()


def test_log_redacts_stdout_and_approve_log_file():
    d = tam.temp_dir("d21_")
    cu = os.environ.get("CT_STATE_DIR")
    os.environ["CT_STATE_DIR"] = str(d)
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            cap, restore = wl._fresh_logger(CT_BRAND="donblog")     # co CT_BRAND -> co ghi tep
            try:
                write_log.log("loi", f"gui hong: {RuntimeError(URL)!r}")
            finally:
                for h in list(logging.getLogger("approve").handlers):
                    h.flush()
                restore()
        tep = list(d.rglob("approve.log"))
        assert tep, list(d.rglob("*"))
        for txt in (buf.getvalue(), tep[0].read_text(encoding="utf-8")):
            assert "gui hong" in txt, txt
            assert TOKEN not in txt and "AAFake" not in txt, txt
    finally:
        if cu is None:
            os.environ.pop("CT_STATE_DIR", None)
        else:
            os.environ["CT_STATE_DIR"] = cu
        for h in list(logging.getLogger("approve").handlers):
            if isinstance(h, logging.handlers.RotatingFileHandler):
                h.close()


def test_direct_print_sites_are_redacted():
    """publish.send_topic* + route_missing_images._time_send + moat_publish._tele khong
    di qua write_log.log nhung in/tra ngoai le tho — phai che token o do."""
    import httpx
    import publish
    import route_missing_images as rmi
    import moat_publish

    class _Boom:
        """httpx.Client / httpx.post gia: nem ngoai le kem URL that (nhu httpx that
        khi HTTP loi), URL nay chua token."""
        def __init__(self, *a, **k):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def post(self, url, *a, **k):
            raise RuntimeError(f"tcp loi toi {url}")

    def _boom_post(url, *a, **k):
        raise RuntimeError(f"tcp loi toi {url}")

    cu_httpx = (httpx.Client, httpx.post)
    cu_load, cu_topics = publish.env_load.load, publish.env_load.topics
    cu_env = {k: os.environ.get(k) for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_GROUP_ID")}
    out = io.StringIO()
    try:
        httpx.Client, httpx.post = _Boom, _boom_post
        os.environ["TELEGRAM_BOT_TOKEN"] = TOKEN
        os.environ["TELEGRAM_GROUP_ID"] = "-1"
        publish.env_load.load = lambda *a: None
        publish.env_load.topics = lambda *a: {"vera": 62}
        with redirect_stdout(out), redirect_stderr(out):
            publish.send_topic("x", "vera")
            publish.send_topic_with_keyboard("x", "vera", {"inline_keyboard": []})
            rmi._time_send("vera", "x")
            res = moat_publish._tele("sendMessage", chat_id="-1", text="x")
    finally:
        httpx.Client, httpx.post = cu_httpx
        publish.env_load.load, publish.env_load.topics = cu_load, cu_topics
        for k, v in cu_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
    txt = out.getvalue()
    assert txt.count("tcp loi toi") == 3, txt      # publish x2 + route: da chay vao nhanh loi
    assert TOKEN not in txt and "AAFake" not in txt, txt
    assert res["ok"] is False and "tcp loi toi" in res["description"], res
    assert TOKEN not in res["description"] and "bot<redacted>" in res["description"], res


if __name__ == "__main__":
    ok = 0
    ten = [k for k in list(globals()) if k.startswith("test_")]
    for k in ten:
        try:
            globals()[k]()
            ok += 1
        except Exception as e:                                # noqa: BLE001
            print(f"    FAIL {k}: {type(e).__name__}: {e}")
    print(f"{Path(__file__).name:<34} {ok}/{len(ten)} test qua")
    sys.exit(0 if ok == len(ten) else 1)
