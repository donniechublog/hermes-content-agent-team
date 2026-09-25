"""LOW-403: reply `Hiro` / `Hiro 1-10` vao bao cao researcher -> MOT task Hiro.

Hai dieu phai giu:
  1. Cu phap moi KHONG doi nghia lenh chon cu nao (`1 - 10`, `1 - Ethan`, `3 - Dre`...).
  2. Mot lenh Hiro = MOT task (khong phai N task), job ghi du tin theo thu tu so, va
     manifest KHONG bi danh dau `assignments` (tin van giao rieng cho Ethan/Dre/Kite duoc).

Chay:  python tests/test_low403_hiro_pick.py
"""
import json
import re
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import approve_pick as pick                                    # noqa: E402
import hiro_pick                                               # noqa: E402
import role                                                    # noqa: E402
import state_paths                                             # noqa: E402
import tam                                                     # noqa: E402

DRAFT_ID_OK = re.compile(r"^[a-z0-9][a-z0-9-]{0,54}$")     # = approve_post._DRAFT_ID_HOP_LE
H = hiro_pick.HiroCommand


# ---- cu phap --------------------------------------------------------------

def test_hiro_alone_takes_whole_report():
    for t in ("Hiro", "hiro", "  HIRO  ", "Hiro:"):
        assert hiro_pick.read_hiro_command(t) == H(), t


def test_hiro_range_forms():
    for t in ("Hiro 1-10", "hiro 1 - 10", "Hiro: 1–10", "HIRO 1..10", "Hiro, 1 — 10"):
        assert hiro_pick.read_hiro_command(t) == H(1, 10), t
    assert hiro_pick.read_hiro_command("Hiro 3-3") == H(3, 3)


def test_hiro_bad_range_is_reported_not_silently_dropped():
    for t in ("Hiro 10-1", "Hiro 0-5", "Hiro 1-21", "Hiro 5", "Hiro 1, 3", "Hiro 1-"):
        cmd = hiro_pick.read_hiro_command(t)
        assert cmd is not None and cmd.error and cmd.start is None, (t, cmd)
    assert hiro_pick.read_hiro_command("Hiro 1-20") == H(1, 20)      # tran dung 20


def test_non_hiro_text_is_not_a_hiro_command():
    for t in ("", "1 - 10", "3 - Dre", "1, 2 - Ethan", "Hiro ơi hôm nay làm gì",
              "hiroshima 1-3", "gửi Hiro 1-10", "Hiro làm 1-10 nhé"):
        assert hiro_pick.read_hiro_command(t) is None, t


def test_old_pick_commands_keep_their_meaning():
    """Hop dong cu cua read_pick_command — Hiro khong duoc lam lech mot lenh nao."""
    b = pick.BRAND
    cases = {
        "1": [(1, "ethan", b)],
        "1, 2, 3": [(1, "ethan", b), (2, "ethan", b), (3, "ethan", b)],
        "1 - Ethan, 2 - Dre": [(1, "ethan", b), (2, "dre", b)],
        "3 - Kites": [(3, "kite", b)],
        "1 - 10": [(1, "ethan", b), (10, "ethan", b)],      # nghia cu: HAI tin rieng
    }
    for t, want in cases.items():
        assert pick.read_pick_command(t) == want, (t, pick.read_pick_command(t))


def test_every_hiro_command_was_unused_by_old_parser():
    """Chan truoc read_pick_command an toan vi moi chuoi Hiro nhan, bo doc cu deu bo qua."""
    for t in ("Hiro", "Hiro 1-10", "hiro 1 - 10", "Hiro 1..10", "Hiro 5", "Hiro 10-1"):
        assert hiro_pick.read_hiro_command(t) is not None
        assert pick.read_pick_command(t) is None, t


def test_hiro_is_not_a_per_item_pick_role():
    """`1 - Hiro` khong duoc thanh lenh chon tung tin (Hiro khong nhan tin le)."""
    assert "hiro" in role.ROLE and role.display_name("hiro") == "Hiro"
    assert "hiro" not in role.NAME_BRIGHT_CAP and "hiro" not in role.ROLE_IMAGE
    assert pick.read_pick_command("1 - Hiro") is None


# ---- chon tin -------------------------------------------------------------

def _items(n):
    return [{"index": i, "title": f"Tin {i}", "link": f"https://x.test/{i}",
             "summary_vi": f"Tóm tắt {i}", "score": 7} for i in range(1, n + 1)]


def test_select_whole_and_range_in_index_order():
    items = list(reversed(_items(12)))
    got, err = hiro_pick.select_items(items, H())
    assert not err and [it["index"] for it in got] == list(range(1, 13))
    got, err = hiro_pick.select_items(items, H(3, 5))
    assert not err and [it["index"] for it in got] == [3, 4, 5]


def test_select_rejects_missing_and_over_cap():
    got, err = hiro_pick.select_items(_items(8), H(5, 10))
    assert got == [] and "9, 10" in err
    got, err = hiro_pick.select_items(_items(21), H())
    assert got == [] and "Hiro 1-20" in err
    got, err = hiro_pick.select_items([], H())
    assert got == [] and err


def test_draft_id_fits_approve_button():
    d = hiro_pick.make_draft_id("vera", datetime(2026, 9, 25, 10, 15, 30))
    assert d == "hiro-vera-260925-101530" and DRAFT_ID_OK.match(d)
    assert DRAFT_ID_OK.match(hiro_pick.make_draft_id("Some-Very_Long.Researcher"))


# ---- tao task -------------------------------------------------------------

class _Env:
    def __enter__(self):
        self.tmp = Path(tam.temp_dir(prefix="low403_"))
        self.sent, self.created = [], []
        self.saved = {k: getattr(hiro_pick, k) for k in ("STATE_DIR", "DRAFTS", "_send_text",
                                                         "kanban_create", "enabled")}
        hiro_pick.STATE_DIR, hiro_pick.DRAFTS = self.tmp, self.tmp / "drafts"
        (self.tmp / "drafts").mkdir()
        hiro_pick.enabled = lambda: True
        hiro_pick._send_text = lambda token, group, text, thread=None: self.sent.append(text)

        def fake_create(title, assignee, body, parent=None):
            self.created.append((title, assignee, body))
            return f"t_{len(self.created)}", None
        hiro_pick.kanban_create = fake_create
        return self

    def __exit__(self, *exc):
        for k, v in self.saved.items():
            setattr(hiro_pick, k, v)
        return False

    def manifest(self, items):
        p = self.tmp / "vera_candidates_2026-09-25.json"
        p.write_text(json.dumps({"items": items}, ensure_ascii=False), encoding="utf-8")
        return p


def test_one_command_makes_one_task_with_all_items():
    with _Env() as env:
        mf = env.manifest(_items(10))
        hiro_pick.process_hiro("tok", "-100", 7, "vera", H(), mf)
        assert len(env.created) == 1, env.created
        title, assignee, body = env.created[0]
        assert assignee == "hiro" and "10 tin" in title and "Vera" in title
        m = re.search(r"hiro_prepare\.py (\S+)", body)
        assert m and DRAFT_ID_OK.match(m.group(1)), body
        job = json.loads((state_paths.workdir(env.tmp, m.group(1)) / state_paths.HIRO_JOB_FILE)
                         .read_text(encoding="utf-8"))
        assert job["scan_role"] == "vera" and job["manifest"] == str(mf)
        assert [it["index"] for it in job["items"]] == list(range(1, 11))
        assert job["items"][0]["summary_vi"] == "Tóm tắt 1" and "score" not in job["items"][0]
        assert len(env.sent) == 1 and "10 slide" in env.sent[0]


def test_range_command_and_manifest_left_untouched():
    with _Env() as env:
        mf = env.manifest(_items(15))
        before = mf.read_text(encoding="utf-8")
        hiro_pick.process_hiro("tok", "-100", 7, "vera", H(1, 10), mf)
        assert len(env.created) == 1 and "#1–#10" in env.created[0][0]
        assert mf.read_text(encoding="utf-8") == before, "Hiro khong duoc danh dau assignments"


def test_errors_reply_and_create_nothing():
    with _Env() as env:
        mf = env.manifest(_items(5))
        hiro_pick.process_hiro("tok", "-100", 7, "vera", H(3, 8), mf)
        hiro_pick.process_hiro("tok", "-100", 7, "vera", hiro_pick.read_hiro_command("Hiro 9-2"), mf)
        assert env.created == [] and len(env.sent) == 2
        assert all(s.startswith("⚠️ Chưa tạo bộ Hiro") for s in env.sent)


# ---- noi vao approve_service ----------------------------------------------

def test_service_checks_hiro_before_pick_and_needs_report_reply():
    src = (ROOT / "approve_service.py").read_text(encoding="utf-8")
    hm = src[src.index("def handle_message("):]
    assert hm.index("_hiro_command_if_has(") < hm.index("_pick_command_if_has("), \
        "lenh Hiro phai xet TRUOC lenh chon so"
    fn = src[src.index("def _hiro_command_if_has("):src.index("def _report_no_right_reply(")]
    assert "reply_report_target(" in fn and "MANIFEST_BY_TOPIC" in fn


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
