#!/usr/bin/env python3
"""LOW-362: reply chon lai mot tin nhieu lan vao bao cao researcher (ke ca bao cao cu);
tin da giao thi hoi lai kem nut "[vai] lam lai" / "Khong lam lai".

Ong Chu 22/09/2026: "duoc phep reply 1 so nhieu lan vao researcher, researcher co the hoi
lai, bai da duoc [name z] lam, co muon lam lai ko. Nut tra loi [name x] [name y] lam lai /
Ko lam lai".
"""
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import approve_pick as pick                 # noqa: E402
import scan_submit                          # noqa: E402
import state_paths                          # noqa: E402

DRAFT_ID_OK = re.compile(r"^[a-z0-9][a-z0-9-]{0,54}$")     # = approve_post._DRAFT_ID_HOP_LE


class _Env:
    """STATE_DIR/DRAFTS gia + ghi lai moi lan goi Telegram / tao task."""

    def __enter__(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="low362_"))
        (self.tmp / "drafts").mkdir()
        self.calls, self.created, self.redo = [], [], []
        self.saved = {k: getattr(pick, k) for k in ("STATE_DIR", "DRAFTS", "call", "_send_text",
                                                    "create_pair", "_report_receive_job",
                                                    "_report_already_label")}
        pick.STATE_DIR, pick.DRAFTS = self.tmp, self.tmp / "drafts"
        pick.call = lambda token, method, **kw: (self.calls.append((method, kw)), {"ok": True})[1]
        pick._send_text = lambda *a, **k: self.calls.append(("sendText", a))
        pick._report_receive_job = lambda *a, **k: None
        pick._report_already_label = lambda *a, **k: None

        def fake_pair(it, vai_anh="ethan", brand="b", vai_quet=None):
            tid = f"t_new{len(self.created) + 1}"
            it.setdefault("assignments", []).append({"image_role": vai_anh, "brand": brand, "image_task": tid})
            self.created.append((it["index"], vai_anh, brand))
            return tid, None
        pick.create_pair = fake_pair
        return self

    def __exit__(self, *exc):
        for k, v in self.saved.items():
            setattr(pick, k, v)
        return False

    def manifest(self, name, items):
        p = self.tmp / name
        p.write_text(json.dumps({"items": items}, ensure_ascii=False), encoding="utf-8")
        return p

    def report(self, vai, mids, manifest):
        (self.tmp / state_paths.REPORT_MESSAGE_ID_FILE.format(vai)).write_text(
            json.dumps({"message_ids": mids, "message_id": mids[-1], "manifest": str(manifest)}), encoding="utf-8")
        scan_submit.record_report_history(self.tmp / state_paths.REPORT_MESSAGE_ID_FILE.format(vai),
                                          self.tmp / state_paths.REPORT_HISTORY_FILE.format(vai))


def _reply(mid):
    return {"message_id": 999, "text": "3 - Dre", "message_thread_id": 7,
            "reply_to_message": {"message_id": mid, "from": {"is_bot": True}, "text": "bao cao"}}


def test_reply_to_old_report_uses_its_own_manifest():
    with _Env() as e:
        cu = e.manifest("finn_candidates_old.json", [{"index": 3, "title": "Tin cu"}])
        moi = e.manifest("finn_candidates_new.json", [{"index": 3, "title": "Tin moi"}])
        e.report("finn", [100, 101], cu)
        e.report("finn", [200], moi)
        assert pick.reply_report_target("finn", _reply(200)) == (True, moi)
        assert pick.reply_report_target("finn", _reply(100)) == (True, cu)       # truoc day: hoi thoai
        assert pick.reply_report_target("finn", _reply(555)) == (False, None)
        assert pick._is_reply_report("finn", _reply(101))


def test_reply_latest_without_manifest_is_still_a_pick():
    with _Env() as e:
        (e.tmp / state_paths.REPORT_MESSAGE_ID_FILE.format("vera")).write_text(
            json.dumps({"message_ids": [300]}), encoding="utf-8")
        assert pick.reply_report_target("vera", _reply(300)) == (True, None)


def test_history_is_trimmed():
    with _Env() as e:
        m = e.manifest("finn_candidates_x.json", [])
        for i in range(scan_submit.REPORT_HISTORY_KEEP + 5):
            e.report("finn", [i + 1], m)
        dong = (e.tmp / state_paths.REPORT_HISTORY_FILE.format("finn")).read_text(encoding="utf-8").splitlines()
        assert len(dong) == scan_submit.REPORT_HISTORY_KEEP and json.loads(dong[-1])["message_ids"] == [205]


def test_repeat_pick_asks_instead_of_silently_skipping():
    with _Env() as e:
        m = e.manifest("finn_candidates_a.json", [{"index": 3, "title": "Gemini hacked", "assignments": [
            {"image_role": "dre", "brand": "blog", "image_task": "t_1"},
            {"image_role": "kite", "brand": "blog", "image_task": "t_2"}]}])
        pick._process_pick("tok", -100, 7, "finn", [(3, "dre", "blog")], manifest_path=m)
        assert e.created == []                                  # khong tao trung task
        hoi = [kw for meth, kw in e.calls if meth == "sendMessage" and "reply_markup" in kw]
        assert len(hoi) == 1 and "Có muốn làm lại không?" in hoi[0]["text"] and "t_1" in hoi[0]["text"]
        kb = hoi[0]["reply_markup"]["inline_keyboard"]
        cb = [b["callback_data"] for row in kb for b in row]
        assert [c.split(":")[0] for c in cb] == ["rpk", "rpk", "rpkno"], cb
        for c in cb:                                            # Telegram <= 64 byte; approve_post chi nhan [a-z0-9-]
            assert len(c.encode()) <= 64 and DRAFT_ID_OK.match(c.partition(":")[2]), c
        texts = [b["text"] for row in kb for b in row]
        assert texts[-1] == "✋ Không làm lại" and all("làm lại" in t for t in texts)
        pending = json.loads((e.tmp / state_paths.REPICK_PENDING_FILE).read_text(encoding="utf-8"))
        assert list(pending.values())[0]["roles"] == ["dre", "kite"]


def _ask(e):
    m = e.manifest("finn_candidates_b.json", [{"index": 5, "title": "Tin B", "assignments": [
        {"image_role": "dre", "brand": "blog", "image_task": "t_9"}]}])
    key = pick.ask_repick("tok", -100, 7, "finn", m, 5, json.loads(m.read_text())["items"][0], "blog")
    return m, key


def _cq(data):
    return {"id": "cq1", "data": data, "message": {"chat": {"id": -100}, "message_id": 42, "text": "hoi"}}


def test_button_no_redo_closes_question_without_task():
    with _Env() as e:
        _m, key = _ask(e)
        pick.handle_repick_button("tok", "rpkno", key, _cq("rpkno:" + key))
        assert e.created == [] and "Không làm lại" in [kw for m_, kw in e.calls if m_ == "editMessageText"][-1]["text"]
        # bam lai: da tra loi roi
        pick.handle_repick_button("tok", "rpkno", key, _cq("rpkno:" + key))
        assert e.calls[-1][1].get("show_alert") is True


def test_button_redo_uses_redo_path_when_draft_exists():
    import types
    with _Env() as e:
        m, key = _ask(e)
        it = json.loads(m.read_text())["items"][0]
        did = pick._draft_id(it, "blog", "dre")
        (e.tmp / "drafts" / (did + ".img.json")).write_text("{}", encoding="utf-8")
        fake_post = types.SimpleNamespace(_hand_redo=lambda d: (e.redo.append(d), ("🔄 Đã giao làm lại", "t_r"))[1])
        saved = sys.modules.get("approve_post")
        sys.modules["approve_post"] = fake_post
        try:
            pick.handle_repick_button("tok", "rpk", f"{key}-dre", _cq(f"rpk:{key}-dre"))
        finally:
            if saved is None:
                sys.modules.pop("approve_post", None)
            else:
                sys.modules["approve_post"] = saved
        assert e.redo == [did] and e.created == []


def test_button_redo_creates_fresh_pair_when_no_draft():
    import types
    with _Env() as e:
        m, key = _ask(e)
        saved = sys.modules.get("approve_post")
        sys.modules["approve_post"] = types.SimpleNamespace(_hand_redo=lambda d: ("x", None))
        try:
            pick.handle_repick_button("tok", "rpk", f"{key}-dre", _cq(f"rpk:{key}-dre"))
        finally:
            if saved is None:
                sys.modules.pop("approve_post", None)
            else:
                sys.modules["approve_post"] = saved
        assert e.created == [(5, "dre", "blog")]
        assert len(json.loads(m.read_text())["items"][0]["assignments"]) == 2     # ghi lai manifest


def test_button_rejects_role_not_offered():
    with _Env() as e:
        _m, key = _ask(e)
        pick.handle_repick_button("tok", "rpk", f"{key}-ethan", _cq(f"rpk:{key}-ethan"))
        assert e.created == [] and "không có trong câu hỏi" in [kw for m_, kw in e.calls if m_ == "editMessageText"][-1]["text"]


def test_callback_routes_rpk_before_draft_lookup():
    src = (ROOT / "approve_post.py").read_text(encoding="utf-8")
    src = src[src.index("def handle_callback("):]
    i_route = src.index('if action in ("rpk", "rpkno"):')
    assert i_route < src.index('p = DRAFTS / (draft_id + ".json")') and src.index("if not is_boss(cq):") < i_route


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
