"""LOW-418: Hiro toi da 10 slide mot bo + loai tin bang dau `/`.

Ong Chu 25/09/2026: "de Hiro dang 10 bai la duoc ... Vera tim ra 15 tin, thi phai co slash de
biet nhung headline nao bi loai". Telegram nhan toi da 10 anh mot album, moat toi da 10 anh mot
bai — bo tren 10 slide mat slide cuoi khi len kenh (LOW-413).

Giu:
  1. `Hiro /3,5`, `Hiro /11-15`, `Hiro 1-12 /4,6` chon dung tin, dung thu tu.
  2. Loai so khong co trong bao cao / ngoai khoang / loai het / con > 10 tin -> BAO, khong
     lam ngam; goi y mot lenh go lai duoc.
  3. Lenh chon tin cu va hoi thoai "Hiro oi ..." khong doi nghia.

Chay:  python tests/test_low418_hiro_exclude.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "tests"))
import approve_pick as pick                                    # noqa: E402
import hiro_pick                                               # noqa: E402
import hiro_submit                                             # noqa: E402
import tam                                                     # noqa: E402

H = hiro_pick.HiroCommand
VERA_15 = [{"index": i, "title": f"Tin {i}", "link": f"https://x.test/{i}"} for i in range(1, 16)]


def _pick(text, items=VERA_15):
    cmd = hiro_pick.read_hiro_command(text)
    assert cmd is not None and not cmd.error, (text, cmd)
    got, err = hiro_pick.select_items(items, cmd)
    assert not err, (text, err)
    return [it["index"] for it in got]


def test_cap_is_ten_everywhere():
    assert hiro_pick.MAX_SLIDES == hiro_submit.MAX_SLIDES == 10


def test_slash_excludes_headlines():
    assert _pick("Hiro /3,5,7,9,11") == [1, 2, 4, 6, 8, 10, 12, 13, 14, 15]
    assert _pick("Hiro /11-15") == list(range(1, 11))
    assert _pick("Hiro 1-12 /4,6") == [1, 2, 3, 5, 7, 8, 9, 10, 11, 12]
    # cach go de dai: khong cach, co cach, gach dai, nhieu dau /
    assert _pick("hiro 1-12/4, 6") == _pick("Hiro 1 - 12 / 4 6") == _pick("Hiro 1–12 /4 /6")
    assert _pick("Hiro /1, 2, 13–15") == list(range(3, 13))


def test_parsed_command_carries_sorted_unique_exclusions():
    assert hiro_pick.read_hiro_command("Hiro /5,3,5") == H(exclude=(3, 5))
    assert hiro_pick.read_hiro_command("Hiro 1-12 /6,4") == H(1, 12, (4, 6))


def test_bad_exclusions_are_reported_not_silently_dropped():
    loi_cu_phap = ("Hiro /", "Hiro /5-3", "Hiro /0", "Hiro 1-10 /12", "Hiro 1-3 /1-3",
                   "Hiro 1-13 /4,6")                       # 1-13 bo 2 con 11 > 10
    for t in loi_cu_phap:
        cmd = hiro_pick.read_hiro_command(t)
        assert cmd is not None and cmd.error, (t, cmd)
    # so loai khong co trong bao cao -> loi o buoc chon tin (bao cao moi biet co bao nhieu tin)
    _, err = hiro_pick.select_items(VERA_15, hiro_pick.read_hiro_command("Hiro /3,20"))
    assert "20" in err and "để loại" in err, err


def test_over_cap_suggests_a_command_to_type():
    for text, want in (("Hiro", "Hiro /11-15"), ("Hiro /3", "Hiro /3,12-15")):
        _, err = hiro_pick.select_items(VERA_15, hiro_pick.read_hiro_command(text))
        assert want in err and "loại thêm" in err, (text, err)
        # goi y phai go lai duoc va ra dung 10 tin
        assert len(_pick(want)) == 10


def test_labels_show_gaps():
    assert hiro_pick.numbers_label([1, 2, 4, 6, 7, 8]) == "#1–#2, #4, #6–#8"
    assert hiro_pick.numbers_command([3, 5, 11, 12, 13]) == "3,5,11-13"
    assert hiro_pick._span([{"index": i} for i in (1, 2, 3, 5, 7, 8)]) == "#1–#3, #5, #7–#8"


def test_chat_and_old_pick_commands_untouched():
    for t in ("Hiro ơi /3", "Hiro / anh xem giúp", "Hiro /abc3", "gửi Hiro /3", "1 - 10", "3 - Dre"):
        assert hiro_pick.read_hiro_command(t) is None, t
    for t in ("Hiro /3,5", "Hiro 1-12 /4,6", "Hiro /11-15"):
        assert pick.read_pick_command(t) is None, t


def test_reply_names_excluded_headlines():
    import json
    tmp = Path(tam.temp_dir(prefix="low418_"))
    (tmp / "drafts").mkdir()
    mf = tmp / "vera_candidates_2026-09-25.json"
    mf.write_text(json.dumps({"items": VERA_15}, ensure_ascii=False), encoding="utf-8")
    sent, created = [], []
    keys = ("STATE_DIR", "DRAFTS", "_send_text", "kanban_create", "enabled")
    saved = {k: getattr(hiro_pick, k) for k in keys}
    hiro_pick.STATE_DIR, hiro_pick.DRAFTS = tmp, tmp / "drafts"
    hiro_pick.enabled = lambda: True
    hiro_pick._send_text = lambda token, group, text, thread=None: sent.append(text)
    hiro_pick.kanban_create = lambda title, who, body, parent=None: (created.append(title) or ("t_1", None))
    try:
        hiro_pick.process_hiro("tok", "-1", 7, "vera", hiro_pick.read_hiro_command("Hiro /3,5,7,9,11"), mf)
    finally:
        for k, v in saved.items():
            setattr(hiro_pick, k, v)
    assert len(created) == 1 and "10 tin" in created[0], created
    assert "bỏ #3, #5, #7, #9, #11" in sent[0] and "10 slide" in sent[0], sent


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
