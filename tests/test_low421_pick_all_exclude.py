#!/usr/bin/env python3
"""LOW-421: ten designer DUNG DAU = lam het bao cao, sau dau `/` la tin bo.

Ong Chu 27/09/2026: "cac role designer nhu Kite, Dre, Ethan khi reply voi [name] dat truoc thi
se lam het cac tin, sau dau / thi la nhung tin ko lam".
    Dre /1, 2, 10   -> Dre lam moi tin tru 1, 2, 10
    3, 4, 5 - Dre   -> Dre lam tin 3, 4, 5 (nhu cu)

Tren code cu: `Dre /1,2,10` tra None (roi ve hoi thoai), `Dre 1, 2` giao 1 va 2 cho ETHAN.

Chay:  python tests/test_low421_pick_all_exclude.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import approve_pick as pick                                    # noqa: E402
import hiro_pick                                               # noqa: E402

REPORT_12 = [{"index": i, "title": f"Tin {i}", "link": f"https://x.test/{i}"} for i in range(1, 13)]


def _expand(text, items=REPORT_12):
    cmd = pick.read_pick_command(text)
    assert isinstance(cmd, pick.PickAll) and not cmd.error, (text, cmd)
    got, err = pick.expand_pick_all(cmd, items)
    assert not err, (text, err)
    return [(n, role) for n, role, _brand in got]


def test_name_first_takes_whole_report_minus_slash():
    assert _expand("Dre /1, 2, 10") == [(n, "dre") for n in range(1, 13) if n not in (1, 2, 10)]
    assert _expand("Kite /8-12") == [(n, "kite") for n in range(1, 8)]
    assert _expand("Ethan / 3 5") == [(n, "ethan") for n in range(1, 13) if n not in (3, 5)]
    assert _expand("Kites /1–3") == [(n, "kite") for n in range(4, 13)]     # alias + en dash


def test_bare_name_takes_whole_report():
    assert _expand("Dre") == [(n, "dre") for n in range(1, 13)]


def test_numbers_first_keeps_old_meaning():
    for text, want in [
        ("3, 4, 5 - Dre", [(3, "dre"), (4, "dre"), (5, "dre")]),
        ("1, 3 - Ethan, 2 - Dre", [(1, "ethan"), (3, "ethan"), (2, "dre")]),
        ("1 - Ethan 3, 4 - Kites", [(1, "ethan"), (3, "kite"), (4, "kite")]),
        ("1", [(1, "ethan")]),
    ]:
        got = pick.read_pick_command(text)
        assert isinstance(got, list), (text, got)
        assert [(n, r) for n, r, _b in got] == want, (text, got)


def test_name_first_with_numbers_is_reported_not_given_to_ethan():
    """Code cu: `Dre 1, 2` -> tin 1, 2 cho ETHAN, im lang."""
    cmd = pick.read_pick_command("Dre 1, 2")
    assert isinstance(cmd, pick.PickAll) and cmd.error, cmd
    assert "1, 2 - Dre" in cmd.error, cmd.error
    assert pick.read_pick_command("Dre, Kite /1").error


def test_bad_slash_part_is_reported():
    for text in ("Dre /", "Dre /0", "Dre /5-3", "Dre /1-2-3"):
        cmd = pick.read_pick_command(text)
        assert isinstance(cmd, pick.PickAll) and cmd.error, (text, cmd)


def test_chat_starting_with_a_name_stays_chat():
    for text in ("Dre làm lại đi", "Kite ơi", "Dre / anh ơi xem lại", "chào Finn", "ok"):
        assert pick.read_pick_command(text) is None, text


def test_excluding_a_number_not_in_report_is_reported():
    cmd = pick.read_pick_command("Dre /13")
    got, err = pick.expand_pick_all(cmd, REPORT_12)
    assert not got and "13" in err and "#1–#12" in err, err
    got, err = pick.expand_pick_all(pick.read_pick_command("Dre /1-12"), REPORT_12)
    assert not got and "bỏ hết" in err, err


def test_process_pick_expands_on_the_replied_report():
    """Mo rong theo manifest cua bao cao duoc reply, bao 'Da nhan' co dong Bo, tao dung task."""
    sent, pairs = [], []
    with tempfile.TemporaryDirectory() as t:
        mf = Path(t) / "vera_candidates_2026-09-27.json"
        mf.write_text(json.dumps({"scan_role": "vera", "items": REPORT_12[:5]}), encoding="utf-8")
        saved = {k: getattr(pick, k) for k in
                 ("_send_text", "create_pair", "_report_receive_job", "_write_json", "call")}
        pick._send_text = lambda _t, _g, text, thread=None: sent.append(text)
        pick.create_pair = lambda it, **kw: (pairs.append((it["index"], kw["vai_anh"])) or ("t_1", None))
        pick._report_receive_job = lambda *a, **k: None
        pick._write_json = lambda *a, **k: None
        pick.call = lambda *a, **k: {"ok": True}
        try:
            pick._process_pick("tok", -1, 83, "vera", pick.read_pick_command("Dre /2,4"), mf)
        finally:
            for k, v in saved.items():
                setattr(pick, k, v)
    assert pairs == [(1, "dre"), (3, "dre"), (5, "dre")], pairs
    assert "Bỏ: #2, #4" in sent[0], sent[0]


def test_process_pick_reports_syntax_error_without_touching_report():
    sent = []
    saved = pick._send_text
    pick._send_text = lambda _t, _g, text, thread=None: sent.append(text)
    try:
        pick._process_pick("tok", -1, 83, "vera", pick.read_pick_command("Dre 1, 2"),
                           Path("/khong/co/manifest.json"))
    finally:
        pick._send_text = saved
    assert len(sent) == 1 and "Chưa tạo bài" in sent[0], sent


def test_hiro_exclude_still_reads_the_same():
    assert hiro_pick.read_hiro_command("Hiro /3, 5 11-15").exclude == (3, 5, 11, 12, 13, 14, 15)
    assert "không hợp lệ" in hiro_pick.read_hiro_command("Hiro /5-3").error
    assert "Không hiểu" in hiro_pick.read_hiro_command("Hiro /123").error


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
