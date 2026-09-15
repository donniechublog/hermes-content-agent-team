#!/usr/bin/env python3
"""Test cho LOW-160: `approve_service.py push <draft_id>` phai bao loi that
qua ma thoat khi Telegram sendMessage/sendMediaGroup that bai, khong duoc
luon thoat 0.

Bai san xuat that (15/09/2026, task t_77f75527): Miles ghep draft xong roi
goi `approve_service.py push` de day the duyet len Telegram. `sendMessage`
bi cat giua chung (RemoteProtocolError: Server disconnected without sending
a response). Nhanh CLI `push` chi IN loi ra, khong `sys.exit(1)`, nen
`miles_submit.py` (chi kiem subprocess.returncode) coi day la thanh cong va
bao task "done" -- trong khi the duyet CHUA TUNG len Telegram va khong ai
biet de gui lai.

Test nay goi thang `_finish_push_cli` (phan duoc tach ra tu nhanh CLI `push`)
voi `res` gia lap ca hai truong hop (thanh cong/that bai), khong dung mang
that.

Chay:  venv/bin/python tests/test_approve_push_exit_code.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import approve_service as aps                                  # noqa: E402


def _voi_drafts_tam(draft_id, noi_dung, ham):
    """Monkeypatch aps.DRAFTS ve thu muc tam co san draft_id.json = noi_dung,
    chay ham(), tra ve draft sau khi chay + gia tri ham() tra ve. Khoi phuc
    DRAFTS du ham co nem loi hay khong."""
    cu = aps.DRAFTS
    with tempfile.TemporaryDirectory() as tmp_s:
        tmp = Path(tmp_s)
        (tmp / f"{draft_id}.json").write_text(
            json.dumps(noi_dung, ensure_ascii=False), encoding="utf-8")
        aps.DRAFTS = tmp
        try:
            ket_qua = ham()
            draft_sau = json.loads((tmp / f"{draft_id}.json").read_text(encoding="utf-8"))
        finally:
            aps.DRAFTS = cu
    return ket_qua, draft_sau


def test_push_ok_thoat_0_va_luu_message_id():
    res = {"ok": True, "result": {"message_id": 42}}
    ma, draft_sau = _voi_drafts_tam(
        "d_ok", {"caption": "x"},
        lambda: aps._finish_push_cli(res, "d_ok", thread=9))
    assert ma == 0, f"push thanh cong phai thoat 0, duoc {ma}"
    assert draft_sau.get("tg_card_message_id") == 42, \
        f"phai luu lai message_id de doi chieu bai <-> the: {draft_sau}"


def test_push_that_bai_thoat_1_khong_luu_message_id():
    """Day chinh la ca that: Telegram tra ok=False (vd sendMessage bi cat
    giua chung). Truoc LOW-160, nhanh nay van thoat 0 -- vai bao task
    "done" nham du the duyet chua tung len Telegram."""
    res = {"ok": False, "description": "RemoteProtocolError: Server disconnected without sending a response."}
    ma, draft_sau = _voi_drafts_tam(
        "d_loi", {"caption": "x"},
        lambda: aps._finish_push_cli(res, "d_loi", thread=9))
    assert ma == 1, \
        f"push that bai PHAI thoat khac 0 de nguoi goi (miles_submit.py) khong bao thanh cong nham, duoc {ma}"
    assert "tg_card_message_id" not in draft_sau, \
        f"khong co message_id that (gui that bai) thi khong duoc bia ra: {draft_sau}"


def test_push_khong_co_result_van_thoat_theo_ok():
    """res=ok=True nhung thieu 'result' (vd Telegram tra ve dang khac) --
    khong duoc nem loi, van thoat 0 theo dung 'ok', chi la khong luu duoc
    message_id."""
    res = {"ok": True}
    ma, draft_sau = _voi_drafts_tam(
        "d_khong_mid", {"caption": "x"},
        lambda: aps._finish_push_cli(res, "d_khong_mid", thread=None))
    assert ma == 0
    assert "tg_card_message_id" not in draft_sau


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bat ca Exception, luon in N/M (E-r2-2)
    chay_tat_ca(globals())
