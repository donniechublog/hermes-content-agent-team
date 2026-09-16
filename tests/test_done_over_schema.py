#!/usr/bin/env python3
"""Mọi người đọc manifest engine (`xong.json`) phải đi qua `schema.read_manifest`
(audit lượt 2, C-r2-5 / ADF-r2-6).

F2 (8ae13cf) đưa upgrade-on-read vào schema nhưng chỉ image_prepare dùng; 4 vai
*_submit (submit_common), create_task_kite và nút hạ sàn (approve_post) đọc thô — manifest
bản 0 thiếu so_dung_duoc thì hạ sàn báo "Chỉ 0 ảnh thật" dù có 6, và body Kite
tự đếm ra 4 trong khi schema đếm 2 (khái niệm là một chùm).

Cổng quét bằng ast, không quét chuỗi (E-r2-4): chỉ bắt lời gọi json.loads /
_read_json / read_text mà đối số có literal "xong.json" — comment nhắc tới tên
tệp không tính. Ada/Itachi có xong.json RIÊNG (không phải manifest engine, không
có `anh`) nên không nằm trong cổng này.

Chạy:  venv/bin/python tests/test_done_over_schema.py
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NGUOI_DOC_ENGINE = ["submit_common.py", "approve_post.py", "image_prepare.py", "dre_prepare.py",
                    "ethan_prepare.py", "kite_prepare.py", "miles_prepare.py", "route_missing_images.py",
                    "dre_submit.py", "ethan_submit.py", "kite_submit.py", "miles_submit.py"]


def _has_done_json(node) -> bool:
    return any(isinstance(n, ast.Constant) and n.value == "xong.json" for n in ast.walk(node))


def _name_call(call: ast.Call) -> str:
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")


def _read_raw(src: str):
    """Cac lenh doc xong.json khong qua read_manifest: [(dong, ten ham)]."""
    xau = []
    for n in ast.walk(ast.parse(src)):
        if not isinstance(n, ast.Call):
            continue
        ten = _name_call(n)
        if ten in ("loads", "_read_json", "read_text", "_load_json", "doc_json") and _has_done_json(n):
            xau.append((n.lineno, ten))
    return xau


def test_no_ai_read_done_json_raw():
    xau = []
    for ten in NGUOI_DOC_ENGINE:
        p = ROOT / ten
        if not p.exists():
            continue
        for dong, ham in _read_raw(p.read_text(encoding="utf-8")):
            xau.append(f"{ten}:{dong} {ham}(... xong.json)")
    assert not xau, "doc xong.json tho, khong qua schema.read_manifest:\n  " + "\n  ".join(xau)


def test_gate_catch_ok_read_raw_and_skip_comment():
    assert _read_raw('m = json.loads((wd / "xong.json").read_text())') == [(1, "loads"), (1, "read_text")]
    assert _read_raw('x = cb._read_json(wd / "xong.json")') == [(1, "_read_json")]
    assert _read_raw('# doc xong.json o day\nm = schema.read_manifest(wd / "xong.json")') == []


def test_read_manifest_fallback_count_use_ok_wait_copy_0():
    import schema
    m0 = {"anh": [{"ma": "A1", "dung": ["bìa"], "lien_quan": True},
                  {"ma": "A2", "dung": ["thân"], "lien_quan": None}]}
    m = schema.read_manifest(m0)
    assert m["so_dung_duoc"] == 2 and m["phien_ban"] == schema.VERSION_MANIFEST, m


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
