#!/usr/bin/env python3
"""Duyệt ngầm có hạn: im lặng quá cửa sổ chờ thì tự xếp lịch đăng (LOW-382).

Do tren approve.log 18-22/09/2026 (ca hai brand): cong duyet bai an 100 cu bam
trong 5 ngay, trong do 98 la "duyet" va 2 la "bo" — tuc gan nhu moi lan bam deu
la "ok, di tiep". Doi thanh IM LANG LA DONG Y thi tai cua nguoi ti le voi so bai
CO VAN DE (2%), khong phai tong so bai.

Test giu bon thu, moi thu la mot duong da tra gia neu hong:
  1. Cong TAT thi khong bai nao tu di — mac dinh phai la khong lam gi.
  2. Bon rao (cua so cho, khung gio, lay mau, "Giu lai") deu chan that.
  3. Tick goi DUNG `publish_schedule.schedule` ma nut ✅ goi — khong duong dang
     thu hai de lech dan theo thoi gian (cung ly le voi docs/publish_schedule.md).
  4. Co tu het han: bat nham khong thanh trang thai vinh vien.

Chay:  venv/bin/python tests/test_auto_handoff.py
"""
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import auto_handoff as ah                                     # noqa: E402


# ------------------------------------------------------------------ cái cờ
def _co(tmp):
    """Tro co sang mot tep tam. Tra ve ham hoan tac."""
    p = Path(tmp) / "auto_handoff.json"
    cu = ah._path
    ah._path = lambda: p
    return lambda: setattr(ah, "_path", cu)


def test_gate_off_by_default():
    with tempfile.TemporaryDirectory() as tmp:
        tra = _co(tmp)
        try:
            on, ly_do = ah.is_on(ah.GATE_DRAFT_TO_PUBLISH)
            assert on is False and "chưa bật" in ly_do, (on, ly_do)
        finally:
            tra()


def test_set_gate_on_then_off():
    with tempfile.TemporaryDirectory() as tmp:
        tra = _co(tmp)
        try:
            ah.set_gate(ah.GATE_DRAFT_TO_PUBLISH, True, by=7)
            assert ah.is_on(ah.GATE_DRAFT_TO_PUBLISH)[0] is True
            ah.set_gate(ah.GATE_DRAFT_TO_PUBLISH, False)
            assert ah.is_on(ah.GATE_DRAFT_TO_PUBLISH)[0] is False
        finally:
            tra()


def test_expired_gate_turns_itself_off_on_disk():
    """Het han thi khong chi tra False — phai TAT LUON tren dia, khong thi moi
    lan hoi deu phai tinh lai va `/auto` van khoe la dang bat."""
    with tempfile.TemporaryDirectory() as tmp:
        tra = _co(tmp)
        try:
            ah.set_gate(ah.GATE_DRAFT_TO_PUBLISH, True, hours=-1)   # da het han
            on, ly_do = ah.is_on(ah.GATE_DRAFT_TO_PUBLISH)
            assert on is False and "hết hạn" in ly_do, (on, ly_do)
            tren_dia = json.loads(Path(tmp, "auto_handoff.json").read_text(encoding="utf-8"))
            assert tren_dia[ah.GATE_DRAFT_TO_PUBLISH]["on"] is False, tren_dia
        finally:
            tra()


def test_pause_today_blocks_rest_of_day_without_clearing_flag():
    with tempfile.TemporaryDirectory() as tmp:
        tra = _co(tmp)
        try:
            ah.set_gate(ah.GATE_DRAFT_TO_PUBLISH, True)
            ah.pause_today(ah.GATE_DRAFT_TO_PUBLISH)
            on, ly_do = ah.is_on(ah.GATE_DRAFT_TO_PUBLISH)
            assert on is False and "Giữ lại" in ly_do, (on, ly_do)
            # Co van ON: sang mai chay lai, khong ai phai nho bat lai.
            assert json.loads(Path(tmp, "auto_handoff.json").read_text(
                encoding="utf-8"))[ah.GATE_DRAFT_TO_PUBLISH]["on"] is True
        finally:
            tra()


def test_sampling_is_stable_for_the_same_draft():
    """Tick chay moi vong poll: mot bai da roi vao phan lay mau thi lan sau van
    phai la mau, khong thi cho no vai vong la thanh bai auto."""
    ten = [f"bai-so-{i}" for i in range(400)]
    lan1 = [ah.must_review(t) for t in ten]
    lan2 = [ah.must_review(t) for t in ten]
    assert lan1 == lan2, "must_review khong tat dinh"
    ti_le = 100 * sum(lan1) / len(lan1)
    assert abs(ti_le - ah.SAMPLE_PERCENT) < 8, f"ti le lay mau lech: {ti_le:.1f}%"


def test_outside_auto_hours_is_false():
    import datetime as dt
    khuya = dt.datetime(2026, 9, 23, 3, 0, tzinfo=ah.VN).timestamp()
    trua = dt.datetime(2026, 9, 23, 12, 0, tzinfo=ah.VN).timestamp()
    assert ah.in_auto_hours(khuya) is False
    assert ah.in_auto_hours(trua) is True


# ------------------------------------------------------------------- cái tick
def _tick(tmp, draft, gate_on=True, gio_ok=True, must_review=False):
    """Chay auto_schedule_silent_drafts voi mot draft gia. Tra (da xep lich, tin)."""
    import approve_post as db
    drafts = Path(tmp) / "drafts"
    drafts.mkdir(parents=True, exist_ok=True)
    (drafts / "d1.json").write_text(json.dumps(draft), encoding="utf-8")
    da_xep, tin = [], []
    cu = (db.DRAFTS, db.publish_schedule.schedule, db.moat_publish.brand_container,
          db.call, ah.is_on, ah.in_auto_hours, ah.must_review, db.log)
    db.DRAFTS = drafts
    db.publish_schedule.schedule = lambda did: (da_xep.append(did), 1790000000)[1]
    db.moat_publish.brand_container = lambda: "donniechublog"
    db.call = lambda tok, method, **kw: (tin.append((method, kw)), {"ok": True})[1]
    ah.is_on = lambda g: (gate_on, "" if gate_on else "tắt")
    ah.in_auto_hours = lambda *a: gio_ok
    ah.must_review = lambda did: must_review
    try:
        db.auto_schedule_silent_drafts("tok", "grp")
        return da_xep, tin
    finally:
        (db.DRAFTS, db.publish_schedule.schedule, db.moat_publish.brand_container,
         db.call, ah.is_on, ah.in_auto_hours, ah.must_review, db.log) = cu


def _draft(**kw):
    d = {"status": "pending", "brand": "donniechublog", "caption": "x",
         "card_pushed_at": time.time() - 3600, "tg_card_message_id": 55}
    d.update(kw)
    return d


def test_silent_draft_gets_scheduled_by_the_same_function_as_the_button():
    """Fail tren ma cu: truoc 23/09/2026 khong co tick nao, the nam do mai."""
    with tempfile.TemporaryDirectory() as tmp:
        da_xep, tin = _tick(tmp, _draft())
        assert da_xep == ["d1"], da_xep
        ph = [m for m, _ in tin]
        assert "editMessageReplyMarkup" in ph and "sendMessage" in ph, ph


def test_inside_hold_window_waits():
    with tempfile.TemporaryDirectory() as tmp:
        da_xep, _ = _tick(tmp, _draft(card_pushed_at=time.time() - 60))
        assert da_xep == [], "xep lich khi the moi len duoc 1 phut"


def test_gate_off_does_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        da_xep, tin = _tick(tmp, _draft(), gate_on=False)
        assert da_xep == [] and tin == [], (da_xep, tin)


def test_outside_hours_does_nothing():
    with tempfile.TemporaryDirectory() as tmp:
        da_xep, _ = _tick(tmp, _draft(), gio_ok=False)
        assert da_xep == [], "tu dang luc 3h sang: im lang luc do khong phai dong y"


def test_sampled_draft_waits_for_a_real_press():
    with tempfile.TemporaryDirectory() as tmp:
        da_xep, _ = _tick(tmp, _draft(), must_review=True)
        assert da_xep == [], "bai lay mau ma van tu di"


def test_held_draft_stays():
    with tempfile.TemporaryDirectory() as tmp:
        da_xep, _ = _tick(tmp, _draft(hold=True))
        assert da_xep == [], "da bam Giu lai ma van tu di"


def test_other_brand_untouched():
    """Hai container dung chung drafts/: lay nham la tu dang bai cua brand kia."""
    with tempfile.TemporaryDirectory() as tmp:
        da_xep, _ = _tick(tmp, _draft(brand="dcgr"))
        assert da_xep == [], da_xep


def test_already_scheduled_or_dropped_untouched():
    for st in ("scheduled", "published", "rejected"):
        with tempfile.TemporaryDirectory() as tmp:
            da_xep, _ = _tick(tmp, _draft(status=st))
            assert da_xep == [], (st, da_xep)


def test_card_never_pushed_is_not_counted_as_silence():
    """Khong co `card_pushed_at` = the CHUA len topic. Im lang cua mot cai the
    chua ai thay khong phai la dong y."""
    with tempfile.TemporaryDirectory() as tmp:
        d = _draft()
        d.pop("card_pushed_at")
        da_xep, _ = _tick(tmp, d)
        assert da_xep == [], da_xep


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
