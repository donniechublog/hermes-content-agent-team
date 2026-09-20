#!/usr/bin/env python3
"""trace_harness.py — bo GHI VET dung chung cho test doi chieu vet (LOW-311).

Loi luong duyet (approve_*, publish, moat_publish) la may trang thai: dung/sai
nam o THU TU cac lan goi ra ngoai (Telegram, kanban, subprocess, tep state),
khong nam o gia tri tra ve cua mot ham. Bo nay thay moi CANH I/O bang ban ghi
vet tra du lieu dinh san, de mot kich ban khang dinh duoc ba thu:

    1. vet goi ra ngoai   (thu tu + tham so)      -> h.trace / h.tg.sent()
    2. tep state sau cung                         -> h.snapshot(thu_muc)
    3. tin gui cho Ong Chu                        -> h.tg.texts()

Dot 07-08/09/2026 da lam dung phuong phap nay trong scratchpad (vet_chung.py)
roi MAT theo phien. Tep nay nam trong tests/ de khong mat lan nua.

Cach dung (xem tests/test_trace_approve_service.py):

    with Harness(svc, post) as h:
        h.tg.script("sendMessage", {"ok": False, "description": "boom"})
        h.inline_background()
        svc.handle_message("TOK", "-100", msg)
        assert h.tg.methods() == ["sendMessage"]

Nguyen tac:
  - `call` duoc import THEO TEN vao tung module (`from approve_base import call`)
    nen phai thay o MOI module dang giu ten do: `patch_everywhere`.
  - Moi thu thay deu tra lai trong __exit__, ke ca khi test hong.
  - Khong cham sys.modules, khong cham tep that: state/drafts nam trong tmp.

Khong phai tep test: ten khong bat dau bang test_ nen tests/run.sh bo qua.
"""
import json
import shutil
import tempfile
import types
from pathlib import Path


class StopLoop(BaseException):
    """Nem tu canh gia de thoat mot vong `while True` cua code san xuat.
    La BaseException: `except Exception` trong vong poll khong nuot duoc."""


class Trace:
    """Danh sach su kien theo dung thu tu xay ra: (kind, name, data)."""

    def __init__(self):
        self.events = []

    def add(self, kind, name, **data):
        self.events.append((kind, name, data))

    def of(self, kind):
        return [(n, d) for k, n, d in self.events if k == kind]

    def names(self, kind=None):
        return [n for k, n, _ in self.events if kind is None or k == kind]

    def kinds(self):
        return [f"{k}:{n}" for k, n, _ in self.events]


class FakeTelegram:
    """Thay cho `approve_base.call(token, method, **kw)`.

    Mac dinh moi method tra ok voi message_id tang dan (giong Telegram that:
    moi tin mot id). `script(method, r1, r2...)` xep hang cau tra loi cho
    method do; het hang thi ve mac dinh. Cau tra loi la dict, hoac callable
    (kw) -> dict, hoac mot BaseException de nem."""

    def __init__(self, trace, first_message_id=1000):
        self.trace = trace
        self._next = first_message_id
        self._queue = {}

    def script(self, method, *responses):
        self._queue.setdefault(method, []).extend(responses)
        return self

    def __call__(self, token, method, **kw):
        self.trace.add("tg", method, token=token, **kw)
        q = self._queue.get(method)
        if q:
            r = q.pop(0)
            if isinstance(r, BaseException) or (
                    isinstance(r, type) and issubclass(r, BaseException)):
                raise r
            return r(kw) if callable(r) else r
        self._next += 1
        if method == "getUpdates":
            return {"ok": True, "result": []}
        return {"ok": True, "result": {"message_id": self._next}}

    def sent(self, method=None):
        return [d for n, d in self.trace.of("tg") if method is None or n == method]

    def methods(self):
        return self.trace.names("tg")

    def texts(self, method="sendMessage"):
        return [d.get("text") or d.get("caption") or "" for d in self.sent(method)]


class FakeClock:
    """Dong ho dieu khien duoc. `sleep` KHONG ngu: ghi vet roi day gio toi."""

    def __init__(self, trace, now=1_790_000_000.0):
        self.trace = trace
        self.now = float(now)

    def time(self):
        return self.now

    def sleep(self, s):
        self.trace.add("clock", "sleep", seconds=s)
        self.now += float(s)

    def advance(self, s):
        self.now += float(s)

    def as_module(self, real_time):
        """Vat the thay cho ten global `time` cua mot module: time/sleep gia,
        phan con lai (strftime, localtime, monotonic...) cua module that."""
        ns = types.SimpleNamespace(**{k: getattr(real_time, k)
                                      for k in dir(real_time) if not k.startswith("_")})
        ns.time, ns.sleep = self.time, self.sleep
        return ns


class FakeRun:
    """Thay cho `subprocess.run`. `script(match, returncode, stdout, stderr)`:
    lenh nao co `match` trong chuoi argv thi tra ket qua do; khong khop -> 0."""

    def __init__(self, trace):
        self.trace = trace
        self._rules = []

    def script(self, match, returncode=0, stdout="", stderr="", raises=None):
        self._rules.append((match, returncode, stdout, stderr, raises))
        return self

    def __call__(self, argv, *a, **kw):
        flat = " ".join(str(x) for x in argv) if isinstance(argv, (list, tuple)) else str(argv)
        self.trace.add("run", flat, kwargs={k: v for k, v in kw.items() if k != "env"})
        for match, rc, out, err, raises in self._rules:
            if match in flat:
                if raises:
                    raise raises
                return types.SimpleNamespace(returncode=rc, stdout=out, stderr=err, args=argv)
        return types.SimpleNamespace(returncode=0, stdout="", stderr="", args=argv)


_MISSING = object()


class Harness:
    """Context manager gom moi canh gia + tra lai nguyen trang khi thoat.

    `modules`: cac module san xuat dang thu — `patch_everywhere` chi dung vao
    nhung module nay (module nao KHONG co ten do thi bo qua, khong tao moi)."""

    def __init__(self, *modules, token="TOK", group="-1001", channel="-1002"):
        self.modules = modules
        self.token, self.group, self.channel = token, group, channel
        self.trace = Trace()
        self.tg = FakeTelegram(self.trace)
        self.clock = FakeClock(self.trace)
        self.run = FakeRun(self.trace)
        self.tmp = None
        self._undo = []

    # -- vong doi --------------------------------------------------------
    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="trace_"))
        self.drafts = self.tmp / "drafts"
        self.state = self.tmp / "state"
        self.drafts.mkdir()
        self.state.mkdir()
        self.patch_everywhere("call", self.tg)
        self._repoint_paths()
        return self

    def _repoint_paths(self):
        """Doi MOI hang so Path cap module dang tro vao state/ hoac drafts/ that
        sang tmp — khong chi STATE_DIR/DRAFTS ma ca hang so TINH SAN luc import
        (`BOSS_IDS = STATE_DIR / ...`, `REDO_WAIT`, `OFFSET`...): thay moi
        STATE_DIR thi cac hang so do van tro ve thu muc cu."""
        for m in self.modules:
            roots = [(getattr(m, "STATE_DIR", None), self.state),
                     (getattr(m, "DRAFTS", None), self.drafts)]
            for name, val in list(vars(m).items()):
                if not isinstance(val, Path):
                    continue
                for old, new in roots:
                    if old is None:
                        continue
                    if val == old:
                        self.patch(m, name, new)
                        break
                    try:
                        rel = val.relative_to(old)
                    except ValueError:
                        continue
                    self.patch(m, name, new / rel)
                    break

    def __exit__(self, *exc):
        for obj, name, old in reversed(self._undo):
            if old is _MISSING:
                delattr(obj, name)
            else:
                setattr(obj, name, old)
        self._undo.clear()
        shutil.rmtree(self.tmp, ignore_errors=True)
        return False

    # -- thay canh -------------------------------------------------------
    def patch(self, obj, name, value):
        self._undo.append((obj, name, getattr(obj, name, _MISSING)))
        setattr(obj, name, value)
        return value

    def patch_everywhere(self, name, value):
        """Thay `name` o moi module dang thu CO san ten do. Tra so cho da thay."""
        n = 0
        for m in self.modules:
            if hasattr(m, name):
                self.patch(m, name, value)
                n += 1
        return n

    def patch_env(self, environ, **kv):
        """Dat/xoa bien moi truong (gia tri None = xoa), tra lai khi thoat."""
        for k, v in kv.items():
            old = environ.get(k, _MISSING)
            self._undo.append((_EnvSlot(environ, k), "value", old))
            if v is None:
                environ.pop(k, None)
            else:
                environ[k] = v

    def spy(self, name, returns=None, side_effect=None):
        """Ham gia ghi vet ("fn", name, args/kwargs) roi tra `returns` (hoac goi
        `side_effect(*a, **kw)`). Dung cho canh noi bo: create_pair, publish..."""
        def _fn(*a, **kw):
            self.trace.add("fn", name, args=a, kwargs=kw)
            if side_effect is not None:
                return side_effect(*a, **kw)
            return returns
        _fn.__name__ = name
        return _fn

    def inline_background(self, run=False):
        """Thay `_run_background` (thread daemon) bang ban DONG BO, ghi vet
        ("bg", ten, fn=..., args=...). `run=True` thi goi luon fn(*args) — dung
        khi kich ban can di xuyen qua thread; mac dinh chi ghi (khang dinh
        DIEU PHOI: tin nay di vao nhanh nao, voi tham so gi)."""
        def _bg(ten, fn, token, group, thread_id, *args):
            self.trace.add("bg", ten, fn=getattr(fn, "__name__", str(fn)),
                           thread_id=thread_id, args=args)
            if run:
                fn(*args)
        return self.patch_everywhere("_run_background", _bg)

    def capture_logs(self):
        """Thay `log(nhan, chu)` bang ban ghi vet ("log", nhan, text=chu, level=…).

        Tu LOW-305 co hai duong nua: `write_log.warn/error` (dung khi nhan dung
        chung cho ca dong tot lan dong hong, vd `tele`/`kanban`/`start`). Hai ham
        do goi QUA thuoc tinh module nen `patch_everywhere` khong voi toi — phai
        va thang vao `write_log`, khong thi dong warn/error bien mat khoi vet.
        """
        import logging
        import write_log

        def _log(nhan, chu="", level=None):
            self.trace.add("log", nhan, text=str(chu),
                           level=logging.getLevelName(
                               level if level is not None
                               else (logging.ERROR if nhan in write_log.ERROR_LABELS
                                     else logging.INFO)))

        n = self.patch_everywhere("log", _log)
        self.patch(write_log, "log", _log)
        self.patch(write_log, "warn", lambda nhan, chu="": _log(nhan, chu, logging.WARNING))
        self.patch(write_log, "error", lambda nhan, chu="": _log(nhan, chu, logging.ERROR))
        return n

    def logs(self, nhan=None):
        return [d["text"] for n, d in self.trace.of("log") if nhan is None or n == nhan]

    def log_levels(self, nhan=None):
        """[(text, ten muc)] — de test khang dinh dong nao la ERROR/WARNING."""
        return [(d["text"], d["level"]) for n, d in self.trace.of("log")
                if nhan is None or n == nhan]

    def topics(self, mapping):
        """Ghi topics.json vao tmp va tro `env_load.topics_path` toi do (tep that
        la cau hinh commit trong repo — test khong duoc phu thuoc noi dung no)."""
        import env_load
        p = self.tmp / "topics.json"
        p.write_text(json.dumps(mapping), encoding="utf-8")
        self.patch(env_load, "topics_path", lambda brand=None: p)
        return p

    def fake_time(self, *modules):
        """Thay ten global `time` cua cac module bang dong ho dieu khien duoc."""
        import time as real_time
        for m in modules or self.modules:
            if hasattr(m, "time"):
                self.patch(m, "time", self.clock.as_module(real_time))

    # -- du lieu ---------------------------------------------------------
    def write_draft(self, draft_id, **fields):
        d = {"id": draft_id, "status": "pending"}
        d.update(fields)
        (self.drafts / f"{draft_id}.json").write_text(
            json.dumps(d, ensure_ascii=False), encoding="utf-8")
        return d

    def read_draft(self, draft_id):
        return json.loads((self.drafts / f"{draft_id}.json").read_text(encoding="utf-8"))

    def snapshot(self, root=None):
        """{duong dan tuong doi: noi dung} cua moi tep duoi `root` (mac dinh ca
        tmp). JSON thi parse, con lai de chuoi; nhi phan ghi kich thuoc."""
        root = Path(root or self.tmp)
        out = {}
        for p in sorted(root.rglob("*")):
            if not p.is_file():
                continue
            rel = str(p.relative_to(root))
            try:
                raw = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                out[rel] = f"<{p.stat().st_size} bytes>"
                continue
            try:
                out[rel] = json.loads(raw)
            except ValueError:
                out[rel] = raw
        return out


class _EnvSlot:
    """De __exit__ cua Harness tra lai bien moi truong bang cung mot vong undo."""

    def __init__(self, environ, key):
        self.environ, self.key = environ, key

    def __setattr__(self, name, value):
        if name in ("environ", "key"):
            object.__setattr__(self, name, value)
        elif value is _MISSING:
            self.environ.pop(self.key, None)
        else:
            self.environ[self.key] = value

    def __delattr__(self, name):
        self.environ.pop(self.key, None)


def message(mid, text=None, *, thread=None, chat="-1001", user=42, reply_to=None,
            **extra):
    """Dung mot `message` cua Telegram. `reply_to` la message_id cua tin duoc
    Reply THAT; khong dat thi — giong Telegram that trong sieu nhom co topic —
    gan san reply toi tin goc topic (forum_topic_created), thu ma
    `_reply_real` phai loc ra (xem quirk 06/09/2026)."""
    m = {"message_id": mid, "chat": {"id": int(chat)}, "from": {"id": user, "is_bot": False}}
    if text is not None:
        m["text"] = text
    if thread is not None:
        m["message_thread_id"] = thread
        m["reply_to_message"] = {"message_id": thread, "message_thread_id": thread,
                                 "from": {"is_bot": True}, "forum_topic_created": {}}
    if reply_to is not None:
        m["reply_to_message"] = {"message_id": reply_to, "from": {"is_bot": True},
                                 **({"message_thread_id": thread} if thread else {})}
    m.update(extra)
    return m


def callback(data, *, mid=500, thread=None, user=42, cq_id="cq1", text=None, caption=None):
    """Dung mot `callback_query` (bam nut inline) tren tin `mid`."""
    msg = {"message_id": mid, "chat": {"id": -1001}}
    if thread is not None:
        msg["message_thread_id"] = thread
    if text is not None:
        msg["text"] = text
    if caption is not None:
        msg["caption"] = caption
    return {"id": cq_id, "data": data, "from": {"id": user}, "message": msg}


def run_tests(namespace):
    """Chay moi ham test_* trong `namespace`, in theo dung dinh dang run.sh doc
    ("N/M test qua"), tra ma thoat."""
    import traceback
    tests = [(k, v) for k, v in sorted(namespace.items())
             if k.startswith("test_") and callable(v)]
    ok = 0
    for name, fn in tests:
        try:
            fn()
            ok += 1
            print(f"ok   {name}")
        except Exception:                                    # noqa: BLE001
            print(f"FAIL {name}")
            traceback.print_exc()
    print(f"\n{ok}/{len(tests)} test qua")
    return 0 if ok == len(tests) else 1
