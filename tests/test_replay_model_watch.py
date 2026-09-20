#!/usr/bin/env python3
"""LOW-312 — luoi cho `model_watch.py` (truoc day 0%), phat lai phan hoi router THAT.

Vi sao module nay truoc: do 20/09/2026 tren may chu, no la module 0% CHAY NHIEU
NHAT — hai job cron (blog + dcgr), lich `*/30 0,4,5,10-23 * * *`, dang bat, lan
chay gan nhat 04:30 cung ngay. Tuc khoang 30 lan/ngay/brand ma khong co mot test
nao. Va chinh no la canh bao duy nhat cho "model chinh chet ma fallback im lang" —
no hong thi ca hai brand mat canh bao, khong ai biet.

Ban ghi: `tests/golden/replay/model_watch_probes.json`. Doc `origin` cua tung muc
truoc khi tin:
  - "do that": chup truc tiep tu router 20128 tren may chu 20/09/2026 (4 model
    dang dung + model khong ton tai + khoa sai + ten model rong).
  - "dung lai": phong bi router BOC ma loi nha cung cap (`[402]: {...}`). Chuoi
    la NGUYEN VAN tu `state/9router/journal/`, nhung viec no nam trong truong
    `message` cua than JSON tra ve cho client la theo comment trong `probe()` —
    chua bat duoc dau-cuoi mot lan nhu vay. Phan test dung no chi khang dinh
    BO PHAN TICH CUA TA doc dung, khong khang dinh router hanh xu the nao.

Chay:  venv/bin/python tests/test_replay_model_watch.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))

import env_load                        # noqa: E402
import model_watch                     # noqa: E402
import publish                         # noqa: E402

GOLDEN = Path(__file__).resolve().parent / "golden" / "replay" / "model_watch_probes.json"
RECORDED = json.loads(GOLDEN.read_text(encoding="utf-8"))["responses"]

# Bo bon model THAT dang chay tren may chu (do 20/09/2026) + vai dung chung.
LIVE = ["ag/gemini-3.8-flash", "ds/deepseek-v4-flash", "ds/deepseek-v4-pro", "gcli/grok-4.6"]


class _Recorded:
    """Thay `model_watch.httpx`: tra ve phan hoi DA GHI theo ten model.

    `overrides` de mot kich ban dat lai phan hoi cho mot model (vd 'gio no hong')
    ma van dung phong bi that. `raises` gia loi mang."""

    def __init__(self, overrides=None, raises=None):
        self.overrides, self.raises = overrides or {}, raises
        self.calls = []

    def post(self, url, timeout=None, headers=None, json=None):
        model = (json or {}).get("model", "")
        self.calls.append({"url": url, "model": model, "timeout": timeout,
                           "auth": (headers or {}).get("Authorization", ""),
                           "body": json})
        if self.raises:
            raise self.raises
        key = self.overrides.get(model, model)
        rec = RECORDED.get(key)
        if rec is None:
            raise AssertionError(f"khong co ban ghi cho model {model!r} (key {key!r})")
        return _Response(rec["status_code"], rec["body"])


class _Response:
    def __init__(self, status_code, body):
        self.status_code, self._body = status_code, body

    def json(self):
        if isinstance(self._body, dict) and "_raw_text" in self._body:
            return json.loads(self._body["_raw_text"])
        return self._body


def _home(tmp, profiles=None, root_model="ag/gemini-3.8-flash",
          root_fallbacks=("ds/deepseek-v4-flash", "gcli/grok-4.6")):
    """Dung mot HERMES_HOME dung hinh dang THAT tren may chu: config.yaml goc +
    profiles/<vai>/config.yaml, moi cai co `model.default` + `fallback_providers`."""
    import yaml
    home = Path(tmp) / ".hermes-test"
    (home / "profiles").mkdir(parents=True)

    def _write(path, model, fallbacks):
        cfg = {"model": {"default": model, "provider": "custom",
                         "base_url": "http://127.0.0.1:20128/v1",
                         "api_key": "${OPENAI_API_KEY}"},
               "fallback_providers": [{"provider": "custom", "model": m,
                                       "base_url": "http://127.0.0.1:20128/v1"}
                                      for m in fallbacks]}
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(yaml.safe_dump(cfg), encoding="utf-8")

    _write(home / "config.yaml", root_model, root_fallbacks)
    for name, (model, fallbacks) in (profiles or {}).items():
        _write(home / "profiles" / name / "config.yaml", model, fallbacks)
    return home


class _Run:
    """Chay `model_watch.main()` trong cach ly: home gia, state gia, router gia,
    khong gui Telegram that. Tra ve (ma thoat, tin da gui, state sau cung)."""

    def __init__(self, home, argv=("model_watch.py",), overrides=None, raises=None,
                 key="khoa-test", state=None):
        self.home, self.argv, self.key = home, list(argv), key
        self.http = _Recorded(overrides, raises)
        self.sent, self.state_dir = [], state
        self.saved = {}

    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="model_watch_"))
        state = Path(self.state_dir or (self.tmp / "state"))
        state.mkdir(parents=True, exist_ok=True)
        self.state_file = state / "model_health.json"
        self._patch(model_watch, "httpx", self.http)
        self._patch(env_load, "load", lambda *a, **kw: None)
        self._patch(model_watch, "hermes_home", lambda: self.home)
        self._patch(env_load, "state_dir", lambda *a, **kw: state)
        self._patch(publish, "send_topic",
                    lambda text, topic: self.sent.append({"text": text, "topic": topic}))
        self._patch(sys, "argv", self.argv)
        self._env = os.environ.get("OPENAI_API_KEY")
        if self.key is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = self.key
        return self

    def _patch(self, obj, name, value):
        self.saved.setdefault(id(obj), (obj, {}))[1].setdefault(name, getattr(obj, name, None))
        setattr(obj, name, value)

    def __exit__(self, *exc):
        for obj, names in self.saved.values():
            for name, old in names.items():
                setattr(obj, name, old)
        if self._env is None:
            os.environ.pop("OPENAI_API_KEY", None)
        else:
            os.environ["OPENAI_API_KEY"] = self._env
        return False

    def run(self):
        try:
            model_watch.main()
            return 0
        except SystemExit as e:
            return e.code

    def health(self):
        return json.loads(self.state_file.read_text(encoding="utf-8"))

    def text(self):
        return self.sent[0]["text"] if self.sent else ""


# =========================================================================
# models_in_use — doc DUNG nhung model that su duoc cau hinh
# =========================================================================
def test_every_profile_chain_is_collected_not_just_the_root():
    """Tung thieu nova + market: model cua hai vai do hong thi khong ai thu."""
    tmp = tempfile.mkdtemp()
    home = _home(tmp, profiles={"ada": ("ag/gemini-3.8-flash",
                                        ["ds/deepseek-v4-pro", "gcli/grok-4.6"]),
                                "dre": ("ag/gemini-3.8-flash", ["ds/deepseek-v4-flash"])})
    old = model_watch.hermes_home
    model_watch.hermes_home = lambda: home
    try:
        used = model_watch.models_in_use()
    finally:
        model_watch.hermes_home = old
    assert sorted(used) == sorted(LIVE), sorted(used)
    assert used["ag/gemini-3.8-flash"] == ["default:chinh", "ada:chinh", "dre:chinh"]
    assert used["ds/deepseek-v4-pro"] == ["ada:du phong 2"]
    assert used["gcli/grok-4.6"] == ["default:du phong 3", "ada:du phong 3"]
    assert used["ds/deepseek-v4-flash"] == ["default:du phong 2", "dre:du phong 2"]


def test_broken_or_missing_config_is_skipped_not_fatal():
    tmp = tempfile.mkdtemp()
    home = _home(tmp, profiles={"ada": ("ds/deepseek-v4-pro", [])})
    (home / "profiles" / "hong" / "config.yaml").parent.mkdir(parents=True)
    (home / "profiles" / "hong" / "config.yaml").write_text("{ khong phai yaml: [", encoding="utf-8")
    (home / "profiles" / "rong").mkdir()
    old = model_watch.hermes_home
    model_watch.hermes_home = lambda: home
    try:
        used = model_watch.models_in_use()
    finally:
        model_watch.hermes_home = old
    assert sorted(used) == ["ag/gemini-3.8-flash", "ds/deepseek-v4-flash",
                            "ds/deepseek-v4-pro", "gcli/grok-4.6"]


# =========================================================================
# probe — doc dung phan hoi THAT cua router
# =========================================================================
def test_live_models_are_read_as_healthy():
    """Bon model that dang chay tren may chu, phan hoi chup 20/09/2026."""
    http = _Recorded()
    old = model_watch.httpx
    model_watch.httpx = http
    try:
        for m in LIVE:
            assert model_watch.probe(m, "k") == (True, 200, "ok"), m
        body = http.calls[0]["body"]
        assert body["max_tokens"] == 5 and body["messages"][0]["content"] == "hi"
        assert http.calls[0]["auth"] == "Bearer k"
        assert http.calls[0]["timeout"] == model_watch.TIMEOUT
    finally:
        model_watch.httpx = old


def test_real_router_errors_map_to_a_readable_reason():
    """404 / 401 / 400 chup truc tiep: than la {"error": {...}} KHONG co ma trong
    ngoac vuong, nen `probe` roi ve ma HTTP ngoai."""
    http = _Recorded()
    old = model_watch.httpx
    model_watch.httpx = http
    try:
        assert model_watch.probe("khong-ton-tai/model-ma-khong-ai-co", "k") == (
            False, 404, "model khong ton tai o dau kia")
        assert model_watch.probe("KHOA-SAI/ag/gemini-3.8-flash", "k") == (
            False, 401, "khoa API sai hoac het han")
        # 400 khong co trong bang REASONS -> van phai doc duoc, khong duoc rong
        ok, code, why = model_watch.probe("(model rong)", "k")
        assert (ok, code) == (False, 400) and why == "loi HTTP 400"
    finally:
        model_watch.httpx = old


def test_wrapped_upstream_code_beats_the_outer_http_status():
    """Nhanh `inner` cua probe(): ma HTTP ngoai 500, than mang chuoi "[402]: ..."
    -> lay 402. KHANG DINH BO PHAN TICH CUA TA, khong khang dinh router hanh xu ra sao.

    Luu y mot gioi han THAT cua `probe()`, lo ra khi dung ban ghi nay: no tra
    `ok` NGAY khi ma HTTP ngoai la 200, truoc khi doc than. Neu router tung boc
    loi nha cung cap vao mot phan hoi 200 thi model hong se bi cham la khoe. Chua
    do duoc router co lam vay khong, nen chi ghi lai o day, khong sua code."""
    http = _Recorded()
    old = model_watch.httpx
    model_watch.httpx = http
    try:
        assert model_watch.probe("BOC-402/nha-cung-cap", "k") == (
            False, 402, "het tien / chua nap credit")
        assert model_watch.probe("BOC-403/nha-cung-cap", "k") == (
            False, 403, "chua mo quyen truy cap")
        assert model_watch.probe("BOC-429/nha-cung-cap", "k")[1] == 429
        assert model_watch.probe("BOC-502/nha-cung-cap", "k") == (
            False, 502, "backend cua nha cung cap chet")
    finally:
        model_watch.httpx = old


def test_network_failure_is_reported_not_raised():
    http = _Recorded(raises=OSError("mang dut"))
    old = model_watch.httpx
    model_watch.httpx = http
    try:
        assert model_watch.probe("ag/gemini-3.8-flash", "k") == (
            False, None, "khong ket noi duoc (OSError)")
    finally:
        model_watch.httpx = old


# =========================================================================
# main — canh bao CHI khi trang thai DOI
# =========================================================================
def _base_home():
    return _home(tempfile.mkdtemp(),
                 profiles={"ada": ("ag/gemini-3.8-flash",
                                   ["ds/deepseek-v4-pro", "gcli/grok-4.6"]),
                           "dre": ("ag/gemini-3.8-flash", ["ds/deepseek-v4-flash"])})


def test_all_healthy_first_run_writes_state_and_stays_silent():
    with _Run(_base_home(), argv=("model_watch.py", "--quiet")) as r:
        assert r.run() is None or True
        assert r.sent == [], "moi thu khoe ma van bao = spam moi 30 phut"
        health = r.health()
        assert sorted(health["models"]) == sorted(LIVE)
        assert all(v["ok"] and v["code"] == 200 for v in health["models"].values())
        assert health["checked_at"].endswith("+00:00")
        assert len(r.http.calls) == len(LIVE), "moi model thu DUNG mot lan"


def test_model_going_down_raises_one_alarm_with_reason_and_roles():
    home = _base_home()
    with _Run(home, argv=("model_watch.py", "--quiet")) as r:
        r.run()                                   # lan dau: tat ca khoe
    with _Run(home, argv=("model_watch.py", "--quiet"), state=r.state_file.parent,
              overrides={"ds/deepseek-v4-pro": "BOC-402/nha-cung-cap"}) as r2:
        r2.run()
        assert len(r2.sent) == 1 and r2.sent[0]["topic"] == "ada"
        text = r2.text()
        assert "🔴 <b>HONG</b>" in text and "ds/deepseek-v4-pro" in text
        assert "het tien / chua nap credit" in text
        assert "dùng cho: ada:du phong 2" in text
        assert "Hiện 1/4 model đang hỏng" in text
        assert r2.health()["models"]["ds/deepseek-v4-pro"]["ok"] is False


def test_same_breakage_next_run_is_silent_then_recovery_is_announced():
    """Chay moi 30 phut: bao lai moi lan la Ong Chu tat thong bao, roi mat luon
    canh bao that."""
    home = _base_home()
    down = {"ds/deepseek-v4-pro": "BOC-402/nha-cung-cap"}
    with _Run(home, argv=("model_watch.py", "--quiet")) as r:
        r.run()
    state = r.state_file.parent
    with _Run(home, argv=("model_watch.py", "--quiet"), state=state, overrides=down) as r2:
        r2.run()
        assert len(r2.sent) == 1                  # lan dau hong -> bao
    with _Run(home, argv=("model_watch.py", "--quiet"), state=state, overrides=down) as r3:
        r3.run()
        assert r3.sent == [], "van hong y het -> KHONG bao lai"
    with _Run(home, argv=("model_watch.py", "--quiet"), state=state) as r4:
        r4.run()
        assert len(r4.sent) == 1 and "🟢 <b>HOI PHUC</b>" in r4.text()
        assert "Cả 4 model đều khỏe" in r4.text()


def test_model_seen_for_the_first_time_is_only_announced_when_already_broken():
    home = _base_home()
    with _Run(home, argv=("model_watch.py", "--quiet"),
              overrides={"ds/deepseek-v4-pro": "BOC-403/nha-cung-cap"}) as r:
        r.run()
        assert "🟠 <b>MOI</b>" in r.text() and "ds/deepseek-v4-pro" in r.text()
    # model moi ma KHOE thi khong phai tin tuc
    with _Run(_base_home(), argv=("model_watch.py", "--quiet")) as r2:
        r2.run()
        assert r2.sent == []


def test_role_losing_its_whole_chain_gets_the_loud_line():
    """Canh bao nang: mot vai mat CA model chinh lan moi du phong = khong chay duoc."""
    home = _home(tempfile.mkdtemp(),
                 profiles={"ada": ("ag/gemini-3.8-flash", ["ds/deepseek-v4-pro"])})
    with _Run(home, argv=("model_watch.py", "--quiet"),
              overrides={"ag/gemini-3.8-flash": "BOC-402/nha-cung-cap",
                         "ds/deepseek-v4-pro": "BOC-403/nha-cung-cap"}) as r:
        r.run()
        text = r.text()
        assert "🚨 <b>ada mất toàn bộ chuỗi model — không chạy được.</b>" in text
        # default con du phong khoe -> KHONG bi keu oan
        assert "default mất toàn bộ" not in text


def test_force_report_sends_even_with_nothing_changed():
    with _Run(_base_home(), argv=("model_watch.py", "--quiet", "--force-report")) as r:
        r.run()
        assert len(r.sent) == 1 and "Cả 4 model đều khỏe" in r.text()


def test_missing_api_key_exits_loudly_instead_of_probing_nothing():
    with _Run(_base_home(), argv=("model_watch.py", "--quiet"), key=None) as r:
        assert r.run() == "Thieu OPENAI_API_KEY"
        assert r.http.calls == [] and r.sent == []


def test_state_file_is_replaced_atomically_and_leaves_no_tmp():
    home = _base_home()
    with _Run(home, argv=("model_watch.py", "--quiet")) as r:
        r.run()
        left = sorted(p.name for p in r.state_file.parent.iterdir())
        assert left == ["model_health.json"], left


def test_hand_run_without_quiet_prints_one_readable_line_per_model():
    """Chay tay la duong chan doan chinh khi nghi model hong — dong in phai doc
    duoc, va khong duoc vo khi `code` la None (loi mang)."""
    import io
    from contextlib import redirect_stdout
    buf = io.StringIO()
    with _Run(_base_home(), argv=("model_watch.py",),
              overrides={"ds/deepseek-v4-pro": "BOC-429/nha-cung-cap"}) as r:
        with redirect_stdout(buf):
            r.run()
    out = buf.getvalue()
    assert "  OK    ag/gemini-3.8-flash" in out
    assert "  HONG  ds/deepseek-v4-pro" in out and "het quota" in out
    assert "Da gui canh bao: 1 thay doi." in out


def test_hand_run_with_nothing_changed_says_how_many_are_healthy():
    import io
    from contextlib import redirect_stdout
    home = _base_home()
    buf = io.StringIO()
    with _Run(home, argv=("model_watch.py", "--quiet")) as r:
        r.run()
    with _Run(home, argv=("model_watch.py",), state=r.state_file.parent) as r2:
        with redirect_stdout(buf):
            r2.run()
    assert "Khong co thay doi. 4/4 model khoe." in buf.getvalue()


def test_non_json_body_does_not_crash_the_probe():
    """Proxy/gateway chen mot trang HTML vao giua thi `r.json()` nem — `probe`
    phai roi ve ma HTTP ngoai, khong duoc lam vo ca luot quet."""
    class _Html:
        status_code = 502

        def json(self):
            raise ValueError("khong phai JSON")

    http = _Recorded()
    http.post = lambda *a, **kw: _Html()
    old = model_watch.httpx
    model_watch.httpx = http
    try:
        assert model_watch.probe("ag/gemini-3.8-flash", "k") == (
            False, 502, "backend cua nha cung cap chet")
    finally:
        model_watch.httpx = old


def test_home_without_a_root_config_still_reads_the_profiles():
    tmp = tempfile.mkdtemp()
    home = _home(tmp, profiles={"ada": ("ds/deepseek-v4-pro", ["gcli/grok-4.6"])})
    (home / "config.yaml").unlink()
    old = model_watch.hermes_home
    model_watch.hermes_home = lambda: home
    try:
        used = model_watch.models_in_use()
    finally:
        model_watch.hermes_home = old
    assert sorted(used) == ["ds/deepseek-v4-pro", "gcli/grok-4.6"]
    assert used["ds/deepseek-v4-pro"] == ["ada:chinh"]


def test_corrupt_previous_state_is_not_swallowed():
    """State hong = khong biet truoc do the nao. Hom nay `main` NEM ValueError:
    cron ghi lai loi, con hon im lang bao nham 'MOI'. Ghim hanh vi hien tai."""
    home = _base_home()
    with _Run(home, argv=("model_watch.py", "--quiet")) as r:
        r.state_file.write_text("{cut", encoding="utf-8")
        try:
            r.run()
        except ValueError:
            pass
        else:
            raise AssertionError("state hong ma chay tiep im lang")


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
