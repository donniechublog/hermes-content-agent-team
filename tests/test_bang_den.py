#!/usr/bin/env python3
"""`blackboard.create_root` ghi `root_task` vào `.meta.json` bằng cách TRỘN, không ghi đè
(audit lượt 2, C-r2-4).

`.meta.json` là tệp ba tiến trình cùng ghi không khoá chung. `create_root` đọc meta
ở đầu hàm, chạy cả khối kanban (SQLite, write_txn — mất thời gian), rồi mới ghi
lại: engine (`prepare/source.py`) có thể vừa trộn `source_url` thật vào trong
khoảng đó. Ghi đè nguyên dict cũ là xoá của người khác — cùng lỗi d59691c vừa
sửa ở đầu kia của cùng tệp. Hôm nay chưa mất chỉ vì `create_pair` gọi `create_root`
TRƯỚC khi khởi chạy engine — thứ tự tình cờ, không phải bảo vệ.

Chạy:  venv/bin/python tests/test_bang_den.py
"""
import contextlib
import json
import sys
import tempfile
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import blackboard                                               # noqa: E402
import schema                                                 # noqa: E402


class _KbGia:
    """Dung du API create_root goi; `luc_tao` la moc de mot tien trinh khac chen vao
    giua luc blackboard dang ban voi kanban."""
    def __init__(self, luc_tao=None):
        self.luc_tao = luc_tao

    @contextlib.contextmanager
    def connect_closing(self):
        yield object()

    @contextlib.contextmanager
    def write_txn(self, conn):
        yield

    def create_task(self, conn, **k):
        if self.luc_tao:
            self.luc_tao()
        return "t_root"

    def get_task(self, conn, rid):
        return types.SimpleNamespace(status="done")

    def recompute_ready(self, conn):
        pass


class _KsGia:
    def _activate_root_inline(self, *a, **k):
        return True

    def post_blackboard_update(self, *a, **k):
        pass


def _voi_drafts_tam(ham):
    with tempfile.TemporaryDirectory() as t:
        cu = (blackboard.DRAFTS, blackboard._kb)
        blackboard.DRAFTS = Path(t)
        try:
            return ham(Path(t))
        finally:
            blackboard.DRAFTS, blackboard._kb = cu


def test_root_task_tron_vao_meta_khong_xoa_cua_nguoi_khac():
    def _chay(d):
        p = d / "d1.meta.json"
        p.write_text(json.dumps({"source_url": "http://gnews", "title": "T"}), encoding="utf-8")

        def engine_chen_vao():
            # Engine giai xong Google News dung luc blackboard dang trong kanban
            p.write_text(json.dumps(schema.merge_meta(
                json.loads(p.read_text(encoding="utf-8")), {"source_url": "http://that"})),
                encoding="utf-8")
        blackboard._kb = lambda: (_KbGia(engine_chen_vao), _KsGia())
        rid, moi = blackboard.create_root("d1", "T", "", "test")
        return rid, moi, json.loads(p.read_text(encoding="utf-8"))
    rid, moi, meta = _voi_drafts_tam(_chay)
    assert (rid, moi) == ("t_root", True)
    assert meta["root_task"] == "t_root", meta
    assert meta["source_url"] == "http://that", f"ghi de mat source_url cua engine: {meta}"


def test_da_co_root_task_thi_khong_dung_kanban():
    def _chay(d):
        (d / "d2.meta.json").write_text(json.dumps({"root_task": "t_cu"}), encoding="utf-8")
        blackboard._kb = lambda: (_ for _ in ()).throw(AssertionError("khong duoc goi kanban"))
        return blackboard.create_root("d2", "T", "", "test")
    assert _voi_drafts_tam(_chay) == ("t_cu", False)


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
