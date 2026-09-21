#!/usr/bin/env python3
"""Test cho `publish_schedule.py` — hang doi xep lich dang bai cua mot brand.

Nut "Duyet & dang" khong con dang bai nua: no CHIEM MOT SLOT
(`max(now, last_slot + 1 tieng)`) roi tra the ve ngay, con viec dang giao cho
cron `publish-due`. Test o day giu ba thu:

  1. Con tro slot: bai dau = bay gio, bai ke = +1 tieng, hang vang thi ve bay
     gio. Teaser KHONG day con tro (chi len Telegram, khong gianh cho social).
  2. `due()` chi tra bai cua DUNG brand container nay -- hai brand dung chung
     thu muc drafts/, dua nham la dang bai cua dcgr bang khoa cua blog.
  3. Bat bien cu: Telegram loi thi TUYET DOI khong goi `moat_publish.intake`.
     Luat nay von o `tests/test_form_article.py` cho nhanh nut; sau khi tach
     `publish_one()` ra module nay thi phai co cho giu lai.

Cach ly: `publish_schedule` tinh duong dan state qua `env_load.state_dir()` MOI
LAN GOI, nen chi can dat `CT_STATE_DIR` la khong dung vao state that. `DRAFTS`
la bien module-level (giong `moat_publish.DRAFTS`) nen monkeypatch thang trong
try/finally, cung kieu voi tests/test_moat_publish.py.

Chay:  python tests/test_publish_schedule.py
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import publish_schedule as ps          # noqa: E402


class _Sandbox:
    """Thu muc drafts/ + state/ tam, tra lai nguyen trang khi thoat."""

    def __enter__(self):
        self._tmp = tempfile.TemporaryDirectory()
        base = Path(self._tmp.name)
        self.drafts = base / "drafts"
        self.drafts.mkdir()
        self._old_drafts = ps.DRAFTS
        self._old_state = os.environ.get("CT_STATE_DIR")
        ps.DRAFTS = self.drafts
        os.environ["CT_STATE_DIR"] = str(base / "state")
        return self

    def __exit__(self, *exc):
        ps.DRAFTS = self._old_drafts
        if self._old_state is None:
            os.environ.pop("CT_STATE_DIR", None)
        else:
            os.environ["CT_STATE_DIR"] = self._old_state
        self._tmp.cleanup()
        return False

    def write_draft(self, draft_id, **fields):
        d = {"caption": "bai thu", "brand": "donniechublog"}
        d.update(fields)
        (self.drafts / (draft_id + ".json")).write_text(
            json.dumps(d, ensure_ascii=False), encoding="utf-8")
        return d

    def read_draft(self, draft_id):
        return json.loads((self.drafts / (draft_id + ".json")).read_text(encoding="utf-8"))


# =========================================================================
# reserve() — con tro slot
# =========================================================================
def test_reserve_first_slot_is_now():
    """Hang doi trong: bai dau tien khong phai cho ai, slot la chinh bay gio."""
    with _Sandbox():
        now = 1_700_000_000
        assert ps.reserve(now=now) == now


def test_reserve_second_slot_is_one_hour_later():
    """Hai bai duyet lien tiep phai cach nhau dung GAP_SECONDS."""
    with _Sandbox():
        now = 1_700_000_000
        first = ps.reserve(now=now)
        second = ps.reserve(now=now + 5)      # bam nut 5 giay sau
        assert second == first + ps.GAP_SECONDS, (
            f"bai thu hai phai lui {ps.GAP_SECONDS}s, ra {second - first}s")


def test_reserve_third_slot_stacks_again():
    """Duyet don ba bai: 0, +1h, +2h — khong phai tat ca cung dan vao +1h."""
    with _Sandbox():
        now = 1_700_000_000
        slots = [ps.reserve(now=now), ps.reserve(now=now), ps.reserve(now=now)]
        assert slots == [now, now + ps.GAP_SECONDS, now + 2 * ps.GAP_SECONDS], slots


def test_reserve_returns_now_when_queue_went_idle():
    """Bai truoc da dang tu 3 tieng truoc -> khong con ly do bat bai nay cho."""
    with _Sandbox():
        now = 1_700_000_000
        ps.reserve(now=now)
        assert ps.reserve(now=now + 3 * 3600) == now + 3 * 3600


# =========================================================================
# schedule() — ghi vao draft
# =========================================================================
def test_schedule_marks_draft_scheduled_with_publish_at():
    with _Sandbox() as sb:
        sb.write_draft("d1")
        now = 1_700_000_000
        at = ps.schedule("d1", now=now)
        d = sb.read_draft("d1")
        assert at == now
        assert d["status"] == "scheduled", d
        assert d["publish_at"] == now, d


def test_schedule_teaser_publishes_now_without_taking_a_slot():
    """Teaser chi len Telegram (moat tu choi no), nen khong duoc gianh cho cua
    bai social: publish_at = bay gio VA con tro khong nhuc nhich."""
    with _Sandbox() as sb:
        sb.write_draft("teaser", category="TEASER")
        sb.write_draft("tin")
        now = 1_700_000_000
        assert ps.schedule("teaser", now=now) == now
        assert ps.schedule("tin", now=now) == now, (
            "teaser da an mat slot cua bai tin")


# =========================================================================
# due() — cron lay bai nao
# =========================================================================
def test_due_skips_drafts_not_yet_at_their_time():
    with _Sandbox() as sb:
        sb.write_draft("som", status="scheduled", publish_at=1_700_000_000)
        sb.write_draft("muon", status="scheduled", publish_at=1_700_003_600)
        assert ps.due(now=1_700_000_000, brand="donniechublog") == ["som"]


def test_due_sorts_by_publish_at():
    """Dang theo dung thu tu da hua voi Ong Chu, khong theo thu tu glob tra ve."""
    with _Sandbox() as sb:
        sb.write_draft("sau", status="scheduled", publish_at=1_700_000_100)
        sb.write_draft("truoc", status="scheduled", publish_at=1_700_000_000)
        assert ps.due(now=1_700_000_200, brand="donniechublog") == ["truoc", "sau"]


def test_due_ignores_other_brand():
    """Hai brand dung chung drafts/. Lay nham la dang bai dcgr bang khoa blog."""
    with _Sandbox() as sb:
        sb.write_draft("cua_toi", status="scheduled", publish_at=1_700_000_000)
        sb.write_draft("cua_ho", status="scheduled", publish_at=1_700_000_000,
                       brand="dcgr")
        assert ps.due(now=1_700_000_000, brand="donniechublog") == ["cua_toi"]


def test_due_ignores_cancelled_and_published():
    with _Sandbox() as sb:
        sb.write_draft("bo", status="cancelled", publish_at=1_700_000_000)
        sb.write_draft("xong", status="published", publish_at=1_700_000_000)
        assert ps.due(now=1_700_000_000, brand="donniechublog") == []


def test_due_catches_up_overdue_draft():
    """May tat 3 tieng: tick dau tien sau khi bat phai nhat bai qua gio len."""
    with _Sandbox() as sb:
        sb.write_draft("qua_gio", status="scheduled", publish_at=1_700_000_000)
        assert ps.due(now=1_700_000_000 + 3 * 3600,
                      brand="donniechublog") == ["qua_gio"]



# =========================================================================
# publish_one() — dang that, dung chung cho cron va nut "Dang ngay"
# =========================================================================
class _FakePublisher:
    """Thay cho module approve_post: chi hai ten ma publish_one dung toi."""

    def __init__(self, sandbox, res=None, raises=None):
        self.sandbox = sandbox
        self.res = res if res is not None else {"ok": True}
        self.raises = raises
        self.published = []
        self.marks = []

    def publish(self, token, channel, draft_id):
        self.published.append(draft_id)
        if self.raises:
            raise self.raises
        return self.res

    def mark_draft(self, draft_id, status):
        self.marks.append((draft_id, status))
        d = self.sandbox.read_draft(draft_id)
        d["status"] = status
        (self.sandbox.drafts / (draft_id + ".json")).write_text(
            json.dumps(d, ensure_ascii=False), encoding="utf-8")


def _swap_publish_deps(sandbox, publisher, intake):
    """Thay cac cua ra ngoai cua publish_one, tra ve ham hoan nguyen."""
    old = (ps._publisher, ps._secrets, ps.moat_publish.intake,
           ps.moat_publish.report_card, ps._finish_card)
    ps._publisher = lambda: publisher
    ps._secrets = lambda: ("token-gia", "channel-gia")
    ps.moat_publish.intake = intake
    ps.moat_publish.report_card = lambda *a, **k: True
    ps._finish_card = lambda *a, **k: None

    def restore():
        (ps._publisher, ps._secrets, ps.moat_publish.intake,
         ps.moat_publish.report_card, ps._finish_card) = old

    return restore


def test_publish_one_does_not_push_moat_when_telegram_rejected():
    """BAT BIEN: Telegram tu choi thi TUYET DOI khong goi moat.intake.

    Bai chua len channel la bai chua duyet xong. Luat nay von duoc giu o
    tests/test_form_article.py cho nhanh nut; sau khi tach publish_one() ra
    module nay thi day la cho giu no."""
    with _Sandbox() as sb:
        sb.write_draft("d1", status=ps.SCHEDULED, publish_at=1)
        goi = []
        publisher = _FakePublisher(sb, res={"ok": False, "description": "Bad Request"})
        restore = _swap_publish_deps(sb, publisher,
                                     lambda *a, **k: (goi.append(a) or (True, "da xep")))
        try:
            ok, note = ps.publish_one("d1")
        finally:
            restore()

        assert ok is False
        assert goi == [], "Telegram hong ma van day sang moat"
        assert sb.read_draft("d1")["status"] == "publish_failed"


def test_publish_one_pushes_moat_after_telegram_accepted():
    with _Sandbox() as sb:
        sb.write_draft("d1", status=ps.SCHEDULED, publish_at=1)
        goi = []
        publisher = _FakePublisher(sb, res={"ok": True})
        restore = _swap_publish_deps(
            sb, publisher, lambda draft_id, *a, **k: (goi.append(draft_id) or (True, "da xep 2 task publish")))
        try:
            ok, note = ps.publish_one("d1")
        finally:
            restore()

        assert ok is True, note
        assert goi == ["d1"], goi
        assert sb.read_draft("d1")["status"] == "published"


def test_publish_one_marks_publish_failed_when_publish_raises():
    """Ngoai le giua chung khong duoc de bai ket vinh vien o 'publishing' —
    ket o do la khong bam Duyet lai duoc, cung loai loi da sua truoc day."""
    with _Sandbox() as sb:
        sb.write_draft("d1", status=ps.SCHEDULED, publish_at=1)
        publisher = _FakePublisher(sb, raises=RuntimeError("mang dut"))
        restore = _swap_publish_deps(sb, publisher, lambda *a, **k: (True, ""))
        try:
            ok, note = ps.publish_one("d1")
        finally:
            restore()

        assert ok is False
        assert "mang dut" in note, note
        assert sb.read_draft("d1")["status"] == "publish_failed"


def test_publish_one_skips_draft_no_longer_scheduled():
    """Chan dang doi: hai tick cron chong nhau, hoac cron va nut 'Dang ngay'
    cung nham mot bai. Nguoi vao sau thay trang thai da doi thi bo qua."""
    with _Sandbox() as sb:
        sb.write_draft("d1", status="published", publish_at=1)
        publisher = _FakePublisher(sb)
        restore = _swap_publish_deps(sb, publisher, lambda *a, **k: (True, ""))
        try:
            ok, note = ps.publish_one("d1")
        finally:
            restore()

        assert publisher.published == [], "da dang mot bai khong con o trang thai cho"
        assert ok is False


# =========================================================================
# run_due() — dau vao cua cron
# =========================================================================
def test_run_due_publishes_overdue_and_leaves_future_alone():
    with _Sandbox() as sb:
        sb.write_draft("toi_gio", status=ps.SCHEDULED, publish_at=1_700_000_000)
        sb.write_draft("chua_toi", status=ps.SCHEDULED, publish_at=1_700_003_600)
        publisher = _FakePublisher(sb)
        restore = _swap_publish_deps(sb, publisher, lambda *a, **k: (True, "da xep"))
        try:
            ps.run_due(now=1_700_000_000, brand="donniechublog")
        finally:
            restore()

        assert publisher.published == ["toi_gio"], publisher.published
        assert sb.read_draft("chua_toi")["status"] == ps.SCHEDULED


# =========================================================================
# run_due() — nhip giua hai lan dang THAT (dan 20/09/2026)
# =========================================================================
def _ba_bai_qua_han(sb):
    for i, at in enumerate((1_700_000_000, 1_700_003_600, 1_700_007_200)):
        sb.write_draft("bai%d" % i, status=ps.SCHEDULED, publish_at=at)


def test_run_due_khong_dang_bu_ca_hang_doi_trong_mot_tick():
    """Sau mot khoang chet, MOI bai deu qua han cung luc.

    20/09/2026 he ngung ca ngay vi chuyen may; 21:50 song lai thi tick dau
    tien day 13 bai len channel trong 15 phut — dung cai ma file nay sinh ra
    de chan. Tick chi duoc dang MOT bai.
    """
    with _Sandbox() as sb:
        _ba_bai_qua_han(sb)
        publisher = _FakePublisher(sb)
        restore = _swap_publish_deps(sb, publisher, lambda *a, **k: (True, "da xep"))
        try:
            ps.run_due(now=1_700_010_000, brand="donniechublog")
        finally:
            restore()
        assert publisher.published == ["bai0"], publisher.published


def test_run_due_tick_ke_tiep_phai_cho_du_mot_tieng():
    """Cron chay moi phut: tick sau khong duoc dang tiep khi chua du GAP."""
    with _Sandbox() as sb:
        _ba_bai_qua_han(sb)
        publisher = _FakePublisher(sb)
        restore = _swap_publish_deps(sb, publisher, lambda *a, **k: (True, "da xep"))
        try:
            ps.run_due(now=1_700_010_000, brand="donniechublog")
            ps.run_due(now=1_700_010_060, brand="donniechublog")
            ps.run_due(now=1_700_010_120, brand="donniechublog")
        finally:
            restore()
        assert publisher.published == ["bai0"], publisher.published


def test_run_due_dang_bai_ke_tiep_khi_da_du_mot_tieng():
    """Du GAP thi hang doi nhich mot bai — bu dan, khong bu dồn."""
    with _Sandbox() as sb:
        _ba_bai_qua_han(sb)
        publisher = _FakePublisher(sb)
        restore = _swap_publish_deps(sb, publisher, lambda *a, **k: (True, "da xep"))
        try:
            ps.run_due(now=1_700_010_000, brand="donniechublog")
            ps.run_due(now=1_700_013_600, brand="donniechublog")
        finally:
            restore()
        assert publisher.published == ["bai0", "bai1"], publisher.published


def test_run_due_teaser_khong_bi_nhip_chan():
    """Luat da chot: teaser len thang Telegram, khong gianh cho bai social —
    nen cung khong bi nhip cua bai social giu lai."""
    with _Sandbox() as sb:
        sb.write_draft("bai_thuong", status=ps.SCHEDULED, publish_at=1_700_000_000)
        sb.write_draft("teaser", status=ps.SCHEDULED, publish_at=1_700_000_000,
                       category="TEASER")
        publisher = _FakePublisher(sb)
        restore = _swap_publish_deps(sb, publisher, lambda *a, **k: (True, "da xep"))
        try:
            ps.run_due(now=1_700_000_000, brand="donniechublog")
        finally:
            restore()
        assert sorted(publisher.published) == ["bai_thuong", "teaser"], publisher.published


def test_run_due_nhip_khong_troi_dan_khi_dang_dung_gio():
    """Cron tick moi phut nen lan dang truoc luon tre vai giay so voi gio hen.
    Khong co dung sai thi moi bai bi lui them vai giay, don lai thanh vai phut
    sau mot ngay."""
    with _Sandbox() as sb:
        sb.write_draft("a", status=ps.SCHEDULED, publish_at=1_700_000_000)
        sb.write_draft("b", status=ps.SCHEDULED, publish_at=1_700_003_600)
        publisher = _FakePublisher(sb)
        restore = _swap_publish_deps(sb, publisher, lambda *a, **k: (True, "da xep"))
        try:
            ps.run_due(now=1_700_000_045, brand="donniechublog")   # tre 45s
            ps.run_due(now=1_700_003_610, brand="donniechublog")   # tre 10s
        finally:
            restore()
        assert publisher.published == ["a", "b"], publisher.published


def test_run_due_khong_ghi_moc_nhip_khi_dang_that_bai():
    """Telegram loi thi tick sau phai thu lai ngay, khong phai cho mot tieng."""
    with _Sandbox() as sb:
        sb.write_draft("a", status=ps.SCHEDULED, publish_at=1_700_000_000)
        publisher = _FakePublisher(sb, res={"ok": False, "description": "loi gia"})
        restore = _swap_publish_deps(sb, publisher, lambda *a, **k: (True, "da xep"))
        try:
            ps.run_due(now=1_700_000_000, brand="donniechublog")
            sb.write_draft("a", status=ps.SCHEDULED, publish_at=1_700_000_000)
            ps.run_due(now=1_700_000_060, brand="donniechublog")
        finally:
            restore()
        assert publisher.published == ["a", "a"], publisher.published

if __name__ == "__main__":
    sys.path.insert(0, str(ROOT / "tests"))
    from tam import chay_tat_ca          # noqa: E402
    chay_tat_ca(globals())
