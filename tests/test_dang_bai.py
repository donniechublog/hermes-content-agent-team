#!/usr/bin/env python3
"""Test cho hai diem sinh su co "dang trung" / "ket publishing" trong nhat ky
su co du an (issue E3):

  _form_background (approve_post.py)              phan nang cua nut Duyet, chay o thread
      rieng. publish() loi HOAC nem exception deu phai ha trang thai ve
      publish_failed -- khong bao gio duoc ket vinh vien o "publishing" (xem
      docstring cua chinh ham do). moat_publish.intake() chi duoc goi khi
      publish() tra ok=True.

  _rescue_article_end_publishing (approve_service.py)  chay MOT lan luc dich vu khoi
      dong: ha ve publish_failed cac draft con ket o "publishing" QUA
      END_PUBLISHING_SECONDS giay (thread nen bi SIGTERM giet giua chung khi
      dich vu restart), nhung PHAI de yen draft con moi (< nguong -- co the
      mot tien trinh khac dang xu ly that) va draft khong o trang thai
      "publishing" (published/rejected/...).

Chay:  venv/bin/python tests/test_dang_bai.py

--------------------------------------------------------------------------
BUG SAN XUAT PHAT HIEN KHI VIET TEST NAY -- DA SUA (09/09/2026):
approve_service.py dong ~46 import `_label_reason_redo` tu `duyet_giao_viec`,
nhung ham nay chi dinh nghia trong `approve_post.py` (dong 344). Loi phat sinh tu
commit 8cd8226 ("bo shim re-export 79 ten trong approve_service") -- khi don
import, ten nay bi dat nham vao tuple cua duyet_giao_viec. Hau qua:
`import approve_service` nem ImportError ngay lap tuc, dich vu approve_service
(ham loop()) khong khoi dong duoc. Da sua bang cach chuyen ten nay ve tuple
import cua duyet_bai; shim tam trong tep test nay da duoc go bo.
"""
import json
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import approve_post as db                                         # noqa: E402
import approve_service as aps                                  # noqa: E402


# =========================================================== _dang_nen =====
class _MoatGia:
    """Thay the module `moat_publish` that: chi ghi lai draft_id da goi
    intake(), khong dong mang that."""
    def __init__(self):
        self.goi = []

    def intake(self, draft_id):
        self.goi.append(draft_id)
        return True, "da day sang moat (gia)"


def _goi_dang_nen(publish_fn):
    """Thay the publish/mark_draft/moat_publish/_fix_story_go_button cua duyet_bai
    bang gia, goi db._form_background(...) voi msg toi thieu, roi tra ve
    (goi_mark_draft, goi_moat_intake, goi_sua_tin) de assert. Khoi phuc moi
    monkeypatch trong finally du _form_background co nem loi hay khong (khong duoc,
    nhung phong truong hop)."""
    goi_mark_draft = []
    goi_sua_tin = []
    moat_gia = _MoatGia()

    def _fake_mark_draft(draft_id, status):
        goi_mark_draft.append((draft_id, status))

    def _fake_sua_tin_go_nut(token, msg, note):
        goi_sua_tin.append((token, msg, note))

    cu = (db.publish, db.mark_draft, db.moat_publish, db._fix_story_go_button)
    db.publish = publish_fn
    db.mark_draft = _fake_mark_draft
    db.moat_publish = moat_gia
    db._fix_story_go_button = _fake_sua_tin_go_nut
    try:
        msg = {"chat": {"id": 1}, "message_id": 2, "text": "ban nhap goc"}
        db._form_background("tok", "chan", "d1", msg)
    finally:
        db.publish, db.mark_draft, db.moat_publish, db._fix_story_go_button = cu
    return goi_mark_draft, moat_gia.goi, goi_sua_tin


def test_dang_nen_publish_ok_thi_danh_dau_published_va_day_moat():
    """publish() tra ok=True -> mark_draft("d1", "published") va
    moat_publish.intake("d1") deu phai duoc goi (chi day moat khi Telegram da
    nhan bai, dung nhu ghi chu trong code)."""
    goi_mark_draft, goi_moat_intake, goi_sua_tin = _goi_dang_nen(
        lambda token, channel, draft_id: {"ok": True, "result": [{"message_id": 9}]})
    assert goi_mark_draft == [("d1", "published")], \
        f"phai mark_draft ve published: {goi_mark_draft}"
    assert goi_moat_intake == ["d1"], \
        f"phai day sang moat khi publish ok=True: {goi_moat_intake}"
    assert goi_sua_tin, "phai goi _fix_story_go_button de go nut tren tin nhan"
    assert "DA DANG" in goi_sua_tin[0][2].upper() or "ĐÃ ĐĂNG" in goi_sua_tin[0][2], \
        f"note phai bao da dang thanh cong: {goi_sua_tin[0][2]!r}"


def test_dang_nen_publish_tra_loi_thi_ha_publish_failed_khong_day_moat():
    """publish() tra {"ok": False, "description": ...} -> mark_draft phai ghi
    "publish_failed" (bam Duyet lai duoc) va moat_publish.intake TUYET DOI
    khong duoc goi (code chi day khi ok=True)."""
    goi_mark_draft, goi_moat_intake, goi_sua_tin = _goi_dang_nen(
        lambda token, channel, draft_id: {"ok": False, "description": "loi X"})
    assert goi_mark_draft == [("d1", "publish_failed")], \
        f"phai mark_draft ve publish_failed: {goi_mark_draft}"
    assert goi_moat_intake == [], \
        f"KHONG duoc day sang moat khi publish ok=False: {goi_moat_intake}"
    assert goi_sua_tin and "loi X" in goi_sua_tin[0][2], \
        f"note phai chua mo ta loi tu Telegram: {goi_sua_tin[0][2]!r}"


def test_dang_nen_publish_nem_exception_van_ha_publish_failed():
    """THEN CHOT cua docstring _form_background: "khong bao gio ket vinh vien o
    publishing" phai dung CA KHI publish() nem exception giua chung (mang rot,
    bug code...), khong chi khi no tra ve gon gang {"ok": False}. Truoc khi co
    try/except bao boc, nhanh nay se lam draft ket o "publishing" mai mai."""
    def _no(token, channel, draft_id):
        raise RuntimeError("boom")

    goi_mark_draft, goi_moat_intake, goi_sua_tin = _goi_dang_nen(_no)
    assert goi_mark_draft == [("d1", "publish_failed")], \
        f"exception giua publish() VAN phai ha publish_failed, khong duoc ket o publishing: {goi_mark_draft}"
    assert goi_moat_intake == [], \
        f"khong duoc day sang moat khi publish nem exception: {goi_moat_intake}"
    assert goi_sua_tin, "phai VAN goi _fix_story_go_button de go nut du publish() nem loi"
    note = goi_sua_tin[0][2]
    assert "RuntimeError" in note and "boom" in note, \
        f"note phai neu ro loai loi + thong diep de con debug: {note!r}"


# =============================================== _cuu_bai_ket_publishing ===
def _ghi_draft(tmp: Path, ten: str, **du_lieu) -> Path:
    p = tmp / f"{ten}.json"
    p.write_text(json.dumps(du_lieu), encoding="utf-8")
    return p


def _goi_cuu_bai(tmp: Path):
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


def test_cuu_bai_qua_han_ha_ve_publish_failed_va_bao_group():
    """draft "publishing" voi decided_at CU (qua END_PUBLISHING_SECONDS) -> phai
    ha ve publish_failed + ghi ghi_chu_cuu, VA phai bao qua Telegram (group)
    de Ong Chu biet ma bam Duyet lai."""
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        gio = int(time.time())
        p = _ghi_draft(tmp, "d1", status="publishing", decided_at=gio - 3600)
        goi_call = _goi_cuu_bai(tmp)
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d["status"] == "publish_failed", \
            f"qua nguong END_PUBLISHING_SECONDS thi phai ha publish_failed: {d}"
        assert d.get("ghi_chu_cuu"), f"phai ghi ghi_chu_cuu giai thich ly do: {d}"
        assert len(goi_call) == 1 and goi_call[0][0] == "sendMessage", \
            f"phai bao 1 tin nhan sendMessage ve group khi cuu duoc bai: {goi_call}"
        assert "d1" in goi_call[0][1].get("text", ""), \
            f"tin bao phai neu ten draft da cuu: {goi_call}"
        assert goi_call[0][1].get("chat_id") == "grp", \
            f"phai gui vao dung group truyen vao: {goi_call}"


def test_cuu_bai_da_len_channel_thi_danh_dau_published_khong_moi_bam_lai():
    """Nua sau cua E5: draft ket o "publishing" NHUNG da co dau
    `channel_*_mid` — `publish` ghi dau do NGAY khi Telegram tra ok, nen bai da
    that su len channel va tien trinh chi chet o buoc ghi trang thai.

    Ha ve publish_failed luc nay la moi Ong Chu bam Duyet lai mot bai DA len
    channel: doc gia thay hai bai giong het nhau. Phai danh dau published va noi
    ro DUNG bam lai."""
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        gio = int(time.time())
        p = _ghi_draft(tmp, "d9", status="publishing", decided_at=gio - 3600,
                       channel_album_mid=12345)
        goi_call = _goi_cuu_bai(tmp)
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d["status"] == "published", \
            f"co dau da len channel ma van ha publish_failed -> se dang trung: {d}"
        assert d.get("ghi_chu_cuu"), f"phai ghi ly do da danh dau published: {d}"
        text = goi_call[0][1].get("text", "") if goi_call else ""
        assert "d9" in text, f"tin bao phai neu ten draft: {goi_call}"
        assert "Duyệt lại" in text, f"tin bao phai noi ro ve chuyen bam lai: {text}"


def test_cuu_bai_dau_chu_cung_tinh_la_da_len_channel():
    """Bai chi co CHU (khong anh) chi de lai `channel_chu_mid` — cung phai duoc
    coi la da len channel, khong rieng gi album."""
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        gio = int(time.time())
        p = _ghi_draft(tmp, "d10", status="publishing", decided_at=gio - 3600,
                       channel_chu_mid=777)
        _goi_cuu_bai(tmp)
        assert json.loads(p.read_text(encoding="utf-8"))["status"] == "published"


def test_cuu_bai_con_moi_thi_giu_nguyen_publishing():
    """draft "publishing" voi decided_at MOI (chua qua nguong) -> PHAI GIU
    NGUYEN "publishing" -- co the mot tien trinh khac dang dang that, dong
    cua som se dam len bai dang chay dung."""
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        gio = int(time.time())
        p = _ghi_draft(tmp, "d2", status="publishing", decided_at=gio - 5)
        goi_call = _goi_cuu_bai(tmp)
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d["status"] == "publishing", \
            f"con moi (<END_PUBLISHING_SECONDS) khong duoc dong cua som: {d}"
        assert "ghi_chu_cuu" not in d, f"khong duoc dung den draft con moi: {d}"
        assert goi_call == [], \
            f"khong cuu bai nao thi khong duoc goi Telegram: {goi_call}"


def test_cuu_bai_bo_qua_draft_khong_o_trang_thai_publishing():
    """draft o trang thai khac (vd "published") -> khong dung den, du
    decided_at co cu den may."""
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        gio = int(time.time())
        goc = {"status": "published", "decided_at": gio - 3600}
        p = _ghi_draft(tmp, "d3", **goc)
        goi_call = _goi_cuu_bai(tmp)
        d = json.loads(p.read_text(encoding="utf-8"))
        assert d == goc, f"draft khong o publishing thi khong duoc dong cham gi: {d}"
        assert goi_call == [], f"khong cuu bai nao thi khong duoc goi Telegram: {goi_call}"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
