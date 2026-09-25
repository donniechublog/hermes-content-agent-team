"""LOW-406: `/hiro on|off` — Hiro tu dung ban tin khi researcher nop bao cao.

Ong Chu 25/09/2026: bat auto mode ma bao cao tren 10 tin thi *"cu lay 10 tin dau tien"*.

Giu:
  1. Co theo brand, mac dinh TAT, KHONG tu het han; `/hiro` tra trang thai.
  2. Bat -> moi bao cao vua gui sinh MOT task Hiro, tren 10 tin lay 10 tin dau; tat -> khong.
  3. Moc trong scan_submit KHONG BAO GIO lam hong lenh nop (bao cao da len topic roi —
     loi o day ma tra ma khac 0 thi vai nop lai = gui trung bao cao).
  4. `/hiro` chay ca khi hai bot chung group (CT_CHAT_VIA_GATEWAY=1), co trong menu "/".

Chay:  python tests/test_low406_hiro_auto.py
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import approve_base as base                                   # noqa: E402
import approve_command as cmd                                 # noqa: E402
import hiro_auto                                              # noqa: E402
import hiro_pick                                              # noqa: E402
import scan_submit                                            # noqa: E402
import tam                                                    # noqa: E402
import tele_command                                           # noqa: E402
from trace_harness import Harness, message                    # noqa: E402

VERA_15 = [{"index": i, "title": f"Tin {i}", "link": f"https://x.test/{i}"} for i in range(1, 16)]


class _State:
    """state/ rieng qua CT_STATE_DIR (hiro_auto tinh duong dan luc goi)."""

    def __enter__(self):
        self.tmp = Path(tam.temp_dir(prefix="low406_"))
        self.old = os.environ.get("CT_STATE_DIR")
        os.environ["CT_STATE_DIR"] = str(self.tmp)
        return self

    def __exit__(self, *exc):
        if self.old is None:
            os.environ.pop("CT_STATE_DIR", None)
        else:
            os.environ["CT_STATE_DIR"] = self.old
        return False


def test_flag_defaults_off_and_persists_without_expiry():
    with _State():
        assert not hiro_auto.is_on() and "TẮT" in hiro_auto.status_line()
        hiro_auto.set_on(True, by=42)
        assert hiro_auto.is_on() and "BẬT" in hiro_auto.status_line()
        assert "lấy 10 tin đầu" in hiro_auto.status_line()
        hiro_auto.set_on(False, by=42)
        assert not hiro_auto.is_on()


def test_auto_takes_first_ten():
    c = hiro_pick.first_items_command(VERA_15)
    assert c.exclude == tuple(range(11, 16))
    got, err = hiro_pick.select_items(VERA_15, c)
    assert not err and [it["index"] for it in got] == list(range(1, 11))
    assert hiro_pick.first_items_command(VERA_15[:8]).exclude == ()


class _Auto:
    """Bat/tat co + ghi lai moi lan tao task / nhan tin cua hiro_pick."""

    def __init__(self, on=True):
        self.on = on

    def __enter__(self):
        self.st = _State().__enter__()
        hiro_auto.set_on(self.on)
        self.sent, self.created = [], []
        keys = ("STATE_DIR", "DRAFTS", "_send_text", "kanban_create", "enabled")
        self.saved = {k: getattr(hiro_pick, k) for k in keys}
        self.saved_env = {k: os.environ.get(k) for k in ("TELEGRAM_BOT_TOKEN", "TELEGRAM_GROUP_ID")}
        self.saved_topics = hiro_pick.env_load.topics
        self.saved_load = hiro_pick.env_load.load
        (self.st.tmp / "drafts").mkdir()
        hiro_pick.STATE_DIR, hiro_pick.DRAFTS = self.st.tmp, self.st.tmp / "drafts"
        hiro_pick.enabled = lambda: True
        hiro_pick._send_text = lambda token, group, text, thread=None: self.sent.append((thread, text))
        hiro_pick.kanban_create = lambda title, who, body, parent=None: (
            self.created.append((title, who)) or (f"t_{len(self.created)}", None))
        hiro_pick.env_load.topics = lambda brand=None: {"vera": 83, "hiro": 5980}
        hiro_pick.env_load.load = lambda *a: None
        os.environ.update(TELEGRAM_BOT_TOKEN="TOK", TELEGRAM_GROUP_ID="-100")
        self.manifest = self.st.tmp / "vera_candidates_2026-09-25.json"
        self.manifest.write_text(json.dumps({"items": VERA_15}, ensure_ascii=False), encoding="utf-8")
        return self

    def __exit__(self, *exc):
        for k, v in self.saved.items():
            setattr(hiro_pick, k, v)
        hiro_pick.env_load.topics, hiro_pick.env_load.load = self.saved_topics, self.saved_load
        for k, v in self.saved_env.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        self.st.__exit__()
        return False


def test_on_builds_one_digest_of_first_ten_in_researcher_topic():
    with _Auto(on=True) as env:
        them = hiro_pick.auto_from_report("vera", env.manifest)
        assert env.created == [("Hiro: bản tin vắn 10 tin từ Vera (#1–#10)", "hiro")], env.created
        thread, text = env.sent[0]
        assert thread == 83 and text.startswith("🤖") and "bỏ #11–#15" in text, text
        assert "task t_1" in them


def test_off_or_no_manifest_does_nothing():
    with _Auto(on=False) as env:
        assert hiro_pick.auto_from_report("vera", env.manifest) == ""
        assert env.created == [] and env.sent == []
    with _Auto(on=True) as env:
        assert hiro_pick.auto_from_report("vera", None) == ""
        assert env.created == []


def test_auto_never_raises_into_scan_submit():
    with _Auto(on=True) as env:
        def boom(*a, **k):
            raise RuntimeError("kanban chet")
        hiro_pick.kanban_create = boom
        them = hiro_pick.auto_from_report("vera", env.manifest)
        assert "lỗi" in them and "RuntimeError" in them
    saved = hiro_pick.auto_from_report
    hiro_pick.auto_from_report = lambda *a: (_ for _ in ()).throw(ImportError("x"))
    try:
        assert "lỗi" in scan_submit._auto_hiro("vera", Path("m.json"))
    finally:
        hiro_pick.auto_from_report = saved


def test_scan_submit_hooks_after_main_report_and_skips_trial():
    src = (ROOT / "scan_submit.py").read_text(encoding="utf-8")
    main = src[src.index("def main("):src.index("def _count_items(")]
    assert main.index("ok = send(") < main.index("_auto_hiro(")
    assert '"" if a.thu else _auto_hiro(' in main


# ---- lenh slash ----------------------------------------------------------------

def _harness():
    h = Harness(cmd, base)
    h.__enter__()
    h.capture_logs()
    h.patch_env(os.environ, CT_CHAT_VIA_GATEWAY=None, CT_STATE_DIR=str(h.state))
    h.patch(hiro_pick, "enabled", lambda: True)
    return h


def _send(h, text):
    cmd.handle_command(h.token, h.group, message(1, text, thread=55), 55, text)


def test_slash_hiro_on_off_status():
    h = _harness()
    try:
        _send(h, "/hiro on")
        assert hiro_auto.is_on() and "BẬT" in h.tg.texts()[-1]
        _send(h, "/hiro")
        assert "BẬT" in h.tg.texts()[-1]
        _send(h, "/hiro bat")
        assert "Cú pháp" in h.tg.texts()[-1] and hiro_auto.is_on(), "sai cu phap khong doi gi"
        _send(h, "/hiro off")
        assert not hiro_auto.is_on() and "TẮT" in h.tg.texts()[-1]
    finally:
        h.__exit__()


def test_slash_hiro_refuses_brand_without_topic_and_works_beside_gateway():
    h = _harness()
    try:
        h.patch(hiro_pick, "enabled", lambda: False)
        _send(h, "/hiro on")
        assert not hiro_auto.is_on() and "chưa có topic" in h.tg.texts()[-1]
        h.patch(hiro_pick, "enabled", lambda: True)
        h.patch_env(os.environ, CT_CHAT_VIA_GATEWAY="1")
        n = len(h.tg.texts())
        _send(h, "/hiro")
        assert len(h.tg.texts()) == n + 1, "hai bot chung group: /hiro van la lenh cua bot duyet"
    finally:
        h.__exit__()


def test_menu_lists_hiro():
    mo_ta = dict(tele_command.COMMANDS)
    assert "hiro" in mo_ta and len(mo_ta["hiro"]) <= 256
    assert "/hiro" in cmd.COMMAND_HELP


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
