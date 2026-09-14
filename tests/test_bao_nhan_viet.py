#!/usr/bin/env python3
"""Duyệt ảnh (imgok) tạo task viết cho Miles/Jika — topic của người viết phải
biết NGAY, không phải đợi dispatcher (poll 50-60s + hàng đợi).

Đây là lỗ hổng CÙNG LOẠI với LOW-28 (`_report_already_label` ở duyệt chọn số), nhưng ở
một đường XẢY RA NHIỀU HƠN NHIỀU: mọi tấm ảnh được duyệt đều đi qua `_button_approve`,
trong khi lệnh chọn số chỉ xảy ra vài lần một ngày. Ông Chủ 12/09/2026: *"tất cả
các role đều cần trả lời 'đã gửi [task] cho [name]' và 'đã nhận [task] từ
[name]', còn khi nào bắt tay vào làm thì sẽ thông báo 'đã bắt đầu ...'"* — vế
"đã bắt đầu" đã có sẵn (`report_progress_kanban`, dòng ▶️ khi dispatcher chạy thật);
vế "đã nhận" ở topic người viết thì thiếu hẳn trên đường này.

Chay:  venv/bin/python tests/test_bao_nhan_viet.py
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import approve_post as db                                          # noqa: E402


def _dung(tmp: Path, *, vai_anh="dre", vai_viet="miles", root_task=None):
    """Dung mot draft o trang thai 'da duyet anh, chua tao task viet': ghi
    .img.json (de code doc vai_anh cho tu_vai) + .writer.json (created=False)."""
    draft_id = "test-imgok-bao-nhan"
    (tmp / f"{draft_id}.img.json").write_text(json.dumps(
        {"vai_anh": vai_anh, "title": "Tin test", "carousel": False}), encoding="utf-8")
    wp = tmp / f"{draft_id}.writer.json"
    wp.write_text(json.dumps(
        {"vai_viet": vai_viet, "title": "Tin test", "body": "than bai",
         "created": False, "root_task": root_task, "dre_task": "t_anh1"}), encoding="utf-8")
    return draft_id, wp


def _goi(tmp: Path, *, vai_anh="dre", vai_viet="miles", kanban_loi=None):
    """Goi that db._button_approve(...) voi moi phu thuoc ngoai da thay gia. Tra ve
    (note, cac_lan_goi_bao_nhan, cac_lan_tao_task)."""
    draft_id, wp = _dung(tmp, vai_anh=vai_anh, vai_viet=vai_viet)
    goi_bao_nhan = []
    goi_tao_task = []

    def _kanban_gia(tieu, vai, body, parent=None):
        goi_tao_task.append((tieu, vai, body, parent))
        return (None, kanban_loi) if kanban_loi else ("t_writer1", None)

    cu = (db.DRAFTS, db.kanban_create, db._report_receive_job, db._status_task, db.call)
    db.DRAFTS = tmp
    db.kanban_create = _kanban_gia
    db._report_receive_job = lambda *a, **k: goi_bao_nhan.append((a, k))
    db._status_task = lambda _tid: "done"          # cha coi nhu da xong
    db.call = lambda *a, **k: {"ok": True}
    try:
        note = db._button_approve("tok", -100, draft_id, {"id": "cbq1"}, wp)
    finally:
        db.DRAFTS, db.kanban_create, db._report_receive_job, db._status_task, db.call = cu
    return note, goi_bao_nhan, goi_tao_task


def test_duyet_anh_bao_ngay_cho_topic_nguoi_viet():
    """Cot loi cua ticket: tao task viet thanh cong -> PHAI goi _report_receive_job
    mot lan, khong duoc im lang cho toi dispatcher."""
    with tempfile.TemporaryDirectory() as t:
        _note, goi_bao_nhan, goi_tao_task = _goi(Path(t))
    assert goi_tao_task, "test hong: khong thay tao task viet nao"
    assert len(goi_bao_nhan) == 1, \
        f"phai bao đúng MOT lan cho nguoi viet biet ngay, dang la {len(goi_bao_nhan)}"


def test_bao_nhan_dung_chat_va_vai_viet():
    with tempfile.TemporaryDirectory() as t:
        _note, goi_bao_nhan, _ = _goi(Path(t), vai_viet="jika")
    args, _kw = goi_bao_nhan[0]
    token, chat_id, vai, _tu_vai, title, tid = args[:6]
    assert chat_id == -100, f"phai bao vao dung group, duoc {chat_id}"
    assert vai == "jika", f"phai bao vao topic CUA NGUOI VIET (jika), duoc {vai}"
    assert tid == "t_writer1", f"phai la task VUA tao, duoc {tid}"
    assert "Tin test" in title


def test_bao_nhan_neu_ro_chuyen_tu_vai_anh():
    """Nguoi viet doc duoc NGAY tu ai chuyen sang — dung 'tu_vai' cua
    _report_receive_job (da co san co che 'chuyển từ X'), khong phai chuoi rieng."""
    with tempfile.TemporaryDirectory() as t:
        _note, goi_bao_nhan, _ = _goi(Path(t), vai_anh="dre", vai_viet="miles")
    args, _kw = goi_bao_nhan[0]
    tu_vai = args[3]
    assert tu_vai == "dre", f"phai biet task tu Dre chuyen sang, duoc {tu_vai!r}"


def test_note_noi_da_gui_khong_phai_da_bat_dau():
    """Ong Chu 12/09/2026: 'send' va 'bat dau' la HAI moc khac nhau — dispatcher
    (report_progress_kanban, dong ▶️) moi la nguoi bao 'bat dau' THAT, khi task
    chuyen sang running. Cau tra loi ngay luc duyet khong duoc noi truoc
    'bắt đầu' vi task con dang xep hang, chua chac ai dong cham toi ngay."""
    with tempfile.TemporaryDirectory() as t:
        note, _, _ = _goi(Path(t))
    assert "đã gửi" in note, f"note phai noi 'đã gửi', dang la: {note!r}"
    assert "bắt đầu" not in note, \
        f"note KHONG duoc noi 'bắt đầu' — do la viec cua report_progress_kanban: {note!r}"


def test_khong_bao_khi_tao_task_that_bai():
    """kanban_create loi -> KHONG duoc bao 'da nhan' cho mot task khong ton tai."""
    with tempfile.TemporaryDirectory() as t:
        note, goi_bao_nhan, _ = _goi(Path(t), kanban_loi="het cho")
    assert goi_bao_nhan == [], f"tao task that bai thi khong duoc bao nhan: {goi_bao_nhan}"
    assert "lỗi" in note.lower()


def test_khong_bao_lai_khi_bam_nut_lan_hai():
    """Bam lai nut cua tin DA duyet (w['created'] is True) -> chi doc trang thai,
    KHONG tao task moi, KHONG bao nhan lan nua (da bao lan dau roi)."""
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        draft_id, wp = _dung(tmp)
        w = json.loads(wp.read_text(encoding="utf-8"))
        w["created"], w["writer_task"] = True, "t_writer1"
        wp.write_text(json.dumps(w), encoding="utf-8")

        goi_bao_nhan = []
        cu = (db.DRAFTS, db._report_receive_job, db._status_task, db.link_result, db.call)
        db.DRAFTS = tmp
        db._report_receive_job = lambda *a, **k: goi_bao_nhan.append((a, k))
        db._status_task = lambda _tid: "running"
        db.link_result = lambda _tid: ""
        db.call = lambda *a, **k: {"ok": True}
        try:
            db._button_approve("tok", -100, draft_id, {"id": "cbq1"}, wp)
        finally:
            db.DRAFTS, db._report_receive_job, db._status_task, db.link_result, db.call = cu
    assert goi_bao_nhan == [], f"bam lai nut cu KHONG duoc bao nhan lan nua: {goi_bao_nhan}"


def _goi_hang_cho(tmp: Path, *, vai_viet, brand, hang_cho):
    """imgok voi meta brand + hang cho nguoi viet gia. Tra ve (cac_lan_tao_task,
    sidecar sau khi bam)."""
    import hermes_adapter
    draft_id, wp = _dung(tmp, vai_viet=vai_viet)
    (tmp / f"{draft_id}.meta.json").write_text(json.dumps({"brand": brand}), encoding="utf-8")
    w = json.loads(wp.read_text(encoding="utf-8"))
    w["body"] = (f"cd /r && venv/bin/python {vai_viet}_prepare.py {draft_id}\n"
                 f"cd /r && venv/bin/python {vai_viet}_submit.py {draft_id}")
    wp.write_text(json.dumps(w), encoding="utf-8")
    tao = []
    cu = (db.DRAFTS, db.kanban_create, db._report_receive_job, db._status_task, db.call,
          hermes_adapter.writer_queue)
    db.DRAFTS = tmp
    db.kanban_create = lambda tieu, vai, body, parent=None: (tao.append((vai, body)) or ("t_writer1", None))
    db._report_receive_job = lambda *a, **k: None
    db._status_task = lambda _tid: "done"
    db.call = lambda *a, **k: {"ok": True}
    hermes_adapter.writer_queue = hang_cho
    try:
        db._button_approve("tok", -100, draft_id, {"id": "cbq1"}, wp)
    finally:
        (db.DRAFTS, db.kanban_create, db._report_receive_job, db._status_task, db.call,
         hermes_adapter.writer_queue) = cu
    return tao, json.loads(wp.read_text(encoding="utf-8"))


def test_blog_giao_nguoi_viet_it_viec_cho_hon():
    """LOW-123: nguoi viet tam la Jika nhung Jika dang co 2 task cho, Miles trong
    -> task giao Miles, hai lenh script trong body va sidecar doi theo."""
    with tempfile.TemporaryDirectory() as t:
        tao, w = _goi_hang_cho(Path(t), vai_viet="jika", brand="donniechublog",
                               hang_cho=lambda s: {"miles": (0, None), "jika": (2, 100)})
    vai, body = tao[0]
    assert vai == "miles", f"phai giao Miles (hang cho trong), duoc {vai}"
    assert "miles_prepare.py" in body and "miles_submit.py" in body and "jika_" not in body, body
    assert w["vai_viet"] == "miles", "sidecar phai ghi nguoi viet that de prepare/submit/topic doc dung"


def test_khong_doc_duoc_kanban_thi_giu_nguoi_viet_tam():
    with tempfile.TemporaryDirectory() as t:
        tao, w = _goi_hang_cho(Path(t), vai_viet="jika", brand="donniechublog",
                               hang_cho=lambda s: None)
    assert tao[0][0] == "jika" and w["vai_viet"] == "jika"


def test_dcgr_mot_nguoi_viet_khong_hoi_hang_cho():
    def _cam(_s):
        raise AssertionError("dcgr chi co Miles, khong duoc doc hang cho")
    with tempfile.TemporaryDirectory() as t:
        tao, _w = _goi_hang_cho(Path(t), vai_viet="miles", brand="dcgr.tech", hang_cho=_cam)
    assert tao[0][0] == "miles"


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bắt cả Exception, luôn in N/M
    chay_tat_ca(globals())
