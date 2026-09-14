#!/usr/bin/env python3
"""Lệnh chọn số được nhận thì phải BÁO NGAY, vào đúng topic Ông Chủ vừa gõ.

Đo thật trên `state/dcgr/approve.log` ngày 11/09/2026: lệnh vào lúc 04:22:43,
dòng `[chon] xong sau 157s` lúc 04:25:20 — **157 giây** topic không có gì. Có
`_report_receive_job`, nhưng nó gửi vào topic CỦA ROLE NHẬN (Dre), không phải topic
quét Ông Chủ đang nhìn; nên ở bên này im lặng y hệt lúc lệnh bị nuốt.

Luật Ông Chủ 12/09/2026: *"phải có phản hồi 'đang gửi cho Dre' ngay sau khi
nhận được reply"*.

Chay:  venv/bin/python tests/test_bao_da_nhan.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import approve_pick as dct                                  # noqa: E402

THREAD_VERA = 83          # topic Ông Chủ gõ; topic của Dre là 290 — khác nhau


def _manifest(d: Path) -> Path:
    p = d / "vera_candidates_2026-09-12.json"
    p.write_text(json.dumps({"vai": "vera", "items": [
        {"index": 1, "title": "Moonshot AI (Kimi) đặt mục tiêu 2 tỷ USD doanh thu năm",
         "link": "https://a.vn/1"},
        {"index": 7, "title": "TSMC doanh thu tháng 8 tăng 53% lên kỷ lục 16,35 tỷ USD",
         "link": "https://a.vn/7"},
    ]}, ensure_ascii=False), encoding="utf-8")
    return p


class _Ghi:
    """Ghi lại THỨ TỰ các việc có tác dụng ra ngoài, để khẳng định 'ngay'."""

    def __init__(self):
        self.moc = []

    def gui_chu(self, _token, _group, text, thread=None):
        self.moc.append(("gui", thread, text))

    def create_pair(self, it, **_kw):
        self.moc.append(("create_pair", it["index"]))
        return "t_" + str(it["index"]), None


def _chay(manifest_path, lenh):
    g = _Ghi()
    # Chi va `latest_manifest`, KHONG dung toi `manifest_already_send`: tep test nay
    # phai fail tren code cu vi THIEU DONG BAO, khong phai vi thieu mot ham cua
    # ticket khac (luat LOW-17 — test fail dung ly do). Tren code moi,
    # `manifest_already_send` doc tep mid trong CT_STATE_DIR tam, khong co nen tra
    # None va roi ve `latest_manifest` da va.
    cu = (dct._send_text, dct.create_pair, dct._report_receive_job, dct._write_json,
          dct.latest_manifest, dct.call)
    dct._send_text = g.gui_chu
    dct.create_pair = g.create_pair
    dct._report_receive_job = lambda *a, **k: None
    dct._write_json = lambda *a, **k: None
    dct.latest_manifest = lambda _vai="finn": manifest_path
    dct.call = lambda *a, **k: {"ok": True}
    try:
        dct._process_pick("tok", -100, THREAD_VERA, "vera", lenh)
    finally:
        (dct._send_text, dct.create_pair, dct._report_receive_job, dct._write_json,
         dct.latest_manifest, dct.call) = cu
    return g.moc


def test_bao_da_nhan_di_truoc_moi_viec():
    """Dòng báo phải nằm TRƯỚC create_pair — create_pair mất tới 180s mỗi tin,
    xếp sau nó thì 'ngay' không còn nghĩa gì."""
    with tempfile.TemporaryDirectory() as t:
        moc = _chay(_manifest(Path(t)), [(1, "dre", "dcgr"), (7, "dre", "dcgr")])
    assert moc, "không có việc nào chạy"
    assert moc[0][0] == "gui", f"việc đầu tiên phải là báo đã nhận, đang là {moc[0][0]}"
    i_bao = 0
    i_pair = next(i for i, m in enumerate(moc) if m[0] == "create_pair")
    assert i_bao < i_pair, moc


def test_bao_dung_topic_ong_chu_vua_go():
    """`_report_receive_job` bắn vào topic của Dre; dòng này phải ở lại topic quét."""
    with tempfile.TemporaryDirectory() as t:
        moc = _chay(_manifest(Path(t)), [(1, "dre", "dcgr")])
    assert moc[0][1] == THREAD_VERA, f"gửi nhầm thread {moc[0][1]}"


def test_bao_co_ten_vai_va_tieu_de_tung_so():
    """Ông Chủ phải đọc được NGAY là số vừa gõ có trỏ đúng tin định giao không."""
    with tempfile.TemporaryDirectory() as t:
        moc = _chay(_manifest(Path(t)), [(1, "dre", "dcgr"), (7, "dre", "dcgr")])
    text = moc[0][2]
    assert "đang gửi cho" in text and "Dre" in text, text
    assert "#1" in text and "#7" in text, text
    assert "Moonshot" in text and "TSMC" in text, "thiếu tiêu đề để đối chiếu"


def test_bao_noi_ro_so_khong_co_trong_danh_sach():
    """Gõ nhầm số ngoài dải: phải biết ngay, không phải đợi 'Kết quả chọn'."""
    with tempfile.TemporaryDirectory() as t:
        moc = _chay(_manifest(Path(t)), [(99, "dre", "dcgr")])
    assert "#99" in moc[0][2] and "không có số này" in moc[0][2], moc[0][2]


def test_moi_vai_deu_duoc_ke_ten():
    with tempfile.TemporaryDirectory() as t:
        moc = _chay(_manifest(Path(t)), [(1, "dre", "dcgr"), (7, "ethan", "dcgr")])
    assert "Dre" in moc[0][2] and "Ethan" in moc[0][2], moc[0][2]


def test_van_con_dong_ket_qua_o_cuoi():
    """Báo đã nhận là THÊM, không thay dòng kết quả cuối."""
    with tempfile.TemporaryDirectory() as t:
        moc = _chay(_manifest(Path(t)), [(1, "dre", "dcgr")])
    cuoi = [m for m in moc if m[0] == "gui"][-1]
    assert "Kết quả chọn" in cuoi[2], cuoi


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bắt cả Exception, luôn in N/M
    chay_tat_ca(globals())
