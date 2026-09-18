#!/usr/bin/env python3
"""Test cho hai diem sinh su co "dang trung" / "ket publishing" trong nhat ky
su co du an (issue E3):

  _form_background (approve_post.py) DA BI GO 18/09/2026: nut Duyet khong con
      dang bai, no xep lich va `publish_schedule.publish_one()` dang. Ba test
      cua ham do chuyen nguyen luat sang tests/test_publish_schedule.py (Telegram
      loi thi khong day moat; ngoai le giua chung van ha ve publish_failed).

  _rescue_article_end_publishing (approve_service.py)  chay MOT lan luc dich vu khoi
      dong: ha ve publish_failed cac draft con ket o "publishing" QUA
      END_PUBLISHING_SECONDS giay (thread nen bi SIGTERM giet giua chung khi
      dich vu restart), nhung PHAI de yen draft con moi (< nguong -- co the
      mot tien trinh khac dang xu ly that) va draft khong o trang thai
      "publishing" (published/rejected/...).

Chay:  venv/bin/python tests/test_form_article.py

--------------------------------------------------------------------------
BUG SAN XUAT PHAT HIEN KHI VIET TEST NAY -- DA SUA (09/09/2026):
approve_service.py dong ~46 import `_label_reason_redo` tu `approve_dispatch`,
nhung ham nay chi dinh nghia trong `approve_post.py` (dong 344). Loi phat sinh tu
commit 8cd8226 ("bo shim re-export 79 ten trong approve_service") -- khi don
import, ten nay bi dat nham vao tuple cua approve_dispatch. Hau qua:
`import approve_service` nem ImportError ngay lap tuc, dich vu approve_service
(ham loop()) khong khoi dong duoc. Da sua bang cach chuyen ten nay ve tuple
import cua approve_post; shim tam trong tep test nay da duoc go bo.
"""
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import approve_service as aps                                  # noqa: E402


# =============================================== _rescue_article_end_publishing ===
def _write_draft(tmp: Path, ten: str, **du_lieu) -> Path:
    p = tmp / f"{ten}.json"
    p.write_text(json.dumps(du_lieu), encoding="utf-8")
    return p


def _call_rescue_article(tmp: Path):
    """Tro DRAFTS ve tmp va thay call() bang gia (tranh goi Telegram that) roi
    goi aps._rescue_article_end_publishing("tok", "grp"). Tra ve danh sach
    (method, kwargs) da goi qua call() de assert co bao Telegram hay khong."""
    goi_call = []

    def _fake_call(token, method, **kw):
        goi_call.append((method, kw))
        return {"ok": True}

    cu_drafts, cu_call = aps.DRAFTS, aps.call
    aps.DRAFTS = tmp
    aps.call = _fake_call
    try:
        aps._rescue_article_end_publishing("tok", "grp")
    finally:
        aps.DRAFTS, aps.call = cu_drafts, cu_call
    return goi_call


def test_rescue_article_over_limit_lower_about_publish_failed_and_report_group():
    """draft "publishing" voi decided_at CU (qua END_PUBLISHING_SECONDS) -> phai
    ha ve publish_failed + ghi rescue_note, VA phai bao qua Telegram (group)
    de Ong Chu biet ma bam Duyet lai."""
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        gio = int(time.time())
        p = _write_draft(tmp, "d1", status="publishing", decided_at=gio - 3600)
        goi_call = _call_rescue_article(tmp)
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d["status"] == "publish_failed", \
            f"qua nguong END_PUBLISHING_SECONDS thi phai ha publish_failed: {d}"
        assert d.get("rescue_note"), f"phai ghi rescue_note giai thich ly do: {d}"
        assert len(goi_call) == 1 and goi_call[0][0] == "sendMessage", \
            f"phai bao 1 tin nhan sendMessage ve group khi cuu duoc bai: {goi_call}"
        assert "d1" in goi_call[0][1].get("text", ""), \
            f"tin bao phai neu ten draft da cuu: {goi_call}"
        assert goi_call[0][1].get("chat_id") == "grp", \
            f"phai gui vao dung group truyen vao: {goi_call}"


def test_rescue_article_already_go_live_channel_then_list_mark_published_no_new_press_again():
    """Nua sau cua E5: draft ket o "publishing" NHUNG da co dau
    `channel_*_mid` — `publish` ghi dau do NGAY khi Telegram tra ok, nen bai da
    that su len channel va tien trinh chi chet o buoc ghi trang thai.

    Ha ve publish_failed luc nay la moi Ong Chu bam Duyet lai mot bai DA len
    channel: doc gia thay hai bai giong het nhau. Phai danh dau published va noi
    ro DUNG bam lai."""
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        gio = int(time.time())
        p = _write_draft(tmp, "d9", status="publishing", decided_at=gio - 3600,
                       channel_album_mid=12345)
        goi_call = _call_rescue_article(tmp)
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d["status"] == "published", \
            f"co dau da len channel ma van ha publish_failed -> se dang trung: {d}"
        assert d.get("rescue_note"), f"phai ghi ly do da danh dau published: {d}"
        text = goi_call[0][1].get("text", "") if goi_call else ""
        assert "d9" in text, f"tin bao phai neu ten draft: {goi_call}"
        assert "Duyệt lại" in text, f"tin bao phai noi ro ve chuyen bam lai: {text}"


def test_rescue_article_mark_text_same_static_is_already_go_live_channel():
    """Bai chi co CHU (khong anh) chi de lai `channel_text_mid` — cung phai duoc
    coi la da len channel, khong rieng gi album."""
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        gio = int(time.time())
        p = _write_draft(tmp, "d10", status="publishing", decided_at=gio - 3600,
                       channel_text_mid=777)
        _call_rescue_article(tmp)
        assert json.loads(p.read_text(encoding="utf-8"))["status"] == "published"


def test_rescue_article_remaining_new_then_keep_raw_publishing():
    """draft "publishing" voi decided_at MOI (chua qua nguong) -> PHAI GIU
    NGUYEN "publishing" -- co the mot tien trinh khac dang dang that, dong
    cua som se dam len bai dang chay dung."""
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        gio = int(time.time())
        p = _write_draft(tmp, "d2", status="publishing", decided_at=gio - 5)
        goi_call = _call_rescue_article(tmp)
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d["status"] == "publishing", \
            f"con moi (<END_PUBLISHING_SECONDS) khong duoc dong cua som: {d}"
        assert "rescue_note" not in d, f"khong duoc dung den draft con moi: {d}"
        assert goi_call == [], \
            f"khong cuu bai nao thi khong duoc goi Telegram: {goi_call}"


def test_rescue_article_skip_draft_no_cell_status_publishing():
    """draft o trang thai khac (vd "published") -> khong dung den, du
    decided_at co cu den may."""
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        gio = int(time.time())
        goc = {"status": "published", "decided_at": gio - 3600}
        p = _write_draft(tmp, "d3", **goc)
        goi_call = _call_rescue_article(tmp)
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d == goc, f"draft khong o publishing thi khong duoc dong cham gi: {d}"
        assert goi_call == [], f"khong cuu bai nao thi khong duoc goi Telegram: {goi_call}"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
