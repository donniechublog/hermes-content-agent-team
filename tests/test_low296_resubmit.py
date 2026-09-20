#!/usr/bin/env python3
"""LOW-296: mot draft chi co MOT the duyet song trong topic, va draft da duyet
thi writer khong nop de duoc nua.

Bai that (20/09/2026, task t_c0bc2c8d, Jika/dcgr): trong MOT lan chay, writer
chay `jika_submit.py` 5 lan; moi lan dat cong deu ghep draft + push nen topic co
5 the (album + ban nhap + nut). Lan nop thu 5 con ghi de caption SAU khi Ong Chu
da bam Duyet, nen bai dang ra khac ban da duyet tren the.

Chay:  venv/bin/python tests/test_low296_resubmit.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import approve_post as ap                                       # noqa: E402
import approve_service as aps                                   # noqa: E402
import draft_write as dw                                        # noqa: E402

CAP = "💸 Tin mới về chi tiêu AI.\n\nGartner dự báo 2,7 nghìn tỷ USD, theo hãng tự công bố."


def _drafts(tmp, draft_id, data):
    (tmp / f"{draft_id}.json").write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def _read(tmp, draft_id):
    return json.loads((tmp / f"{draft_id}.json").read_text(encoding="utf-8"))


def _with_tmp(fn):
    old = (dw.DRAFTS, aps.DRAFTS)
    with tempfile.TemporaryDirectory() as s:
        tmp = Path(s)
        dw.DRAFTS = aps.DRAFTS = tmp
        try:
            return fn(tmp)
        finally:
            dw.DRAFTS, aps.DRAFTS = old


# ------------------------------------------------------------ A: draft da duyet thi khoa
def test_draft_da_duyet_bi_khoa():
    def run(tmp):
        for st in ("scheduled", "publishing", "published"):
            _drafts(tmp, "d1", {"caption": CAP, "status": st})
            ly_do = dw.locked_reason("d1")
            assert ly_do and st in ly_do and "KHÔNG nộp lại" in ly_do, (st, ly_do)
    _with_tmp(run)


def test_draft_pending_hoac_chua_co_thi_nop_duoc():
    def run(tmp):
        assert dw.locked_reason("chua-co") is None
        for st in ("pending", "rejected", "cancelled", "publish_failed"):
            _drafts(tmp, "d1", {"caption": CAP, "status": st})
            assert dw.locked_reason("d1") is None, st
    _with_tmp(run)


def _chay_draft_write(tmp, draft_id, caption):
    (tmp / f"{draft_id}.meta.json").write_text(
        json.dumps({"source_url": "https://x.example/a", "category": "AI", "brand": "dcgr"}), encoding="utf-8")
    cf = tmp / f"{draft_id}.caption.txt"
    cf.write_text(caption, encoding="utf-8")
    argv = sys.argv
    sys.argv = ["draft_write.py", draft_id, "--caption-file", str(cf), "--bo-qua-kiem"]
    try:
        dw.main()
    finally:
        sys.argv = argv


def test_draft_write_tu_choi_ghi_de_draft_da_duyet():
    def run(tmp):
        _drafts(tmp, "d1", {"caption": "BAN DA DUYET", "status": "scheduled", "publish_at": "1"})
        try:
            _chay_draft_write(tmp, "d1", CAP)
        except SystemExit as e:
            assert "[LOI]" in str(e.code) and "scheduled" in str(e.code), e.code
        else:
            raise AssertionError("phai thoat khi draft da scheduled")
        d = _read(tmp, "d1")
        assert d["caption"] == "BAN DA DUYET" and d["status"] == "scheduled" and d["publish_at"] == "1", d
    _with_tmp(run)


# ------------------------------------------------------------ B: giu dau vet the song
def test_draft_write_giu_dau_vet_the_khi_con_pending():
    def run(tmp):
        _drafts(tmp, "d1", {"caption": "cu", "status": "pending", "tg_card_message_id": 4110,
                            "tg_extra_message_ids": [4101, 4102], "tg_push_fingerprint": "abc"})
        _chay_draft_write(tmp, "d1", CAP)
        d = _read(tmp, "d1")
        assert d["caption"] == CAP and d["status"] == "pending", d
        assert d["tg_card_message_id"] == 4110 and d["tg_extra_message_ids"] == [4101, 4102], d
        assert d["tg_push_fingerprint"] == "abc", d
    _with_tmp(run)


def test_draft_write_bo_dau_vet_khi_the_cu_da_doi_trang_thai():
    """rejected: the cu da thanh 'da bo', khong duoc xoa nham nen khong mang id qua."""
    def run(tmp):
        _drafts(tmp, "d1", {"caption": "cu", "status": "rejected", "tg_card_message_id": 4110})
        _chay_draft_write(tmp, "d1", CAP)
        assert "tg_card_message_id" not in _read(tmp, "d1")
    _with_tmp(run)


def test_fingerprint_doi_khi_caption_hoac_anh_doi():
    with tempfile.TemporaryDirectory() as s:
        img = Path(s) / "a.png"
        img.write_bytes(b"1234")
        d = {"caption": CAP, "images": [str(img)]}
        f1 = ap.push_fingerprint(d)
        assert f1 == ap.push_fingerprint(dict(d))
        assert f1 != ap.push_fingerprint({**d, "caption": CAP + "!"})
        img.write_bytes(b"12345678")                      # anh duoc ve lai
        assert f1 != ap.push_fingerprint(d)


def _gia_lap_push(monkey):
    """Thay draft_push/delete_messages: dem so the gui va ghi lai id bi xoa."""
    log = {"push": 0, "deleted": []}
    cu = (aps.draft_push, aps.delete_messages)

    def fake_push(tok, grp, draft_id, thread_id=None):
        log["push"] += 1
        n = log["push"]
        return {"ok": True, "result": {"message_id": 5000 + n}, "extra_ids": [4000 + n]}

    def fake_delete(tok, chat, ids):
        log["deleted"] += list(ids)
        return len(ids)

    aps.draft_push, aps.delete_messages = fake_push, fake_delete
    try:
        return monkey(log)
    finally:
        aps.draft_push, aps.delete_messages = cu


def test_nop_hai_lan_y_het_chi_con_mot_the():
    def run(tmp):
        _drafts(tmp, "d1", {"caption": CAP, "status": "pending"})

        def kich_ban(log):
            assert aps._push_replace("t", "g", "d1", 1) == 0
            assert log["push"] == 1 and log["deleted"] == []
            d1 = _read(tmp, "d1")
            assert d1["tg_card_message_id"] == 5001 and d1["tg_extra_message_ids"] == [4001], d1
            # lan 2: cung caption + anh -> khong gui gi
            assert aps._push_replace("t", "g", "d1", 1) == 0
            assert log["push"] == 1 and log["deleted"] == [], log
        _gia_lap_push(kich_ban)
    _with_tmp(run)


def test_nop_lai_caption_khac_thay_the_cu():
    def run(tmp):
        _drafts(tmp, "d1", {"caption": CAP, "status": "pending"})

        def kich_ban(log):
            aps._push_replace("t", "g", "d1", 1)
            d = _read(tmp, "d1")
            d["caption"] = CAP + "\n\nThêm một câu."           # writer sua roi nop lai
            _drafts(tmp, "d1", d)
            assert aps._push_replace("t", "g", "d1", 1) == 0
            assert log["push"] == 2, log
            assert sorted(log["deleted"]) == [4001, 5001], log   # the + album cua ban truoc
            assert _read(tmp, "d1")["tg_card_message_id"] == 5002
        _gia_lap_push(kich_ban)
    _with_tmp(run)


def test_force_van_gui_lai_y_het():
    def run(tmp):
        _drafts(tmp, "d1", {"caption": CAP, "status": "pending"})

        def kich_ban(log):
            aps._push_replace("t", "g", "d1", 1)
            aps._push_replace("t", "g", "d1", 1, force=True)
            assert log["push"] == 2 and sorted(log["deleted"]) == [4001, 5001], log
        _gia_lap_push(kich_ban)
    _with_tmp(run)


def test_the_da_duyet_khong_bi_xoa():
    """Status khac pending: the la 'DA DUYET/DA BO', khong dong vao khi push lai."""
    def run(tmp):
        _drafts(tmp, "d1", {"caption": CAP, "status": "scheduled", "tg_card_message_id": 4110,
                            "tg_extra_message_ids": [4101]})

        def kich_ban(log):
            aps._push_replace("t", "g", "d1", 1)
            assert log["push"] == 1 and log["deleted"] == [], log
        _gia_lap_push(kich_ban)
    _with_tmp(run)


def test_push_loi_thi_giu_the_cu():
    def run(tmp):
        _drafts(tmp, "d1", {"caption": CAP, "status": "pending", "tg_card_message_id": 4110,
                            "tg_extra_message_ids": [4101], "tg_push_fingerprint": "cu"})
        cu = (aps.draft_push, aps.delete_messages)
        xoa = []
        aps.draft_push = lambda *a, **k: {"ok": False, "description": "boom"}
        aps.delete_messages = lambda t, c, ids: xoa.extend(ids) or len(ids)
        try:
            assert aps._push_replace("t", "g", "d1", 1) == 1
        finally:
            aps.draft_push, aps.delete_messages = cu
        assert xoa == [], "gui that bai thi KHONG duoc xoa the cu"
    _with_tmp(run)


# ------------------------------------------------------------ C: loi huong dan
def test_brief_noi_ro_nhac_khong_phai_loi():
    import miles_prepare
    src = (ROOT / "miles_prepare.py").read_text(encoding="utf-8")
    assert "KHÔNG sửa chỉ vì nó" in src and "KHÔNG phải lỗi" in src and "kết thúc task ngay" in src
    assert "tối đa {caption_check.LIMIT}" not in src, "brief con bao 1024 la tran cung"
    assert hasattr(miles_prepare, "write_brief")


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
