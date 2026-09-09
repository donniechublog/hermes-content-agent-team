#!/usr/bin/env python3
"""Mọi người đọc manifest engine (`xong.json`) phải đi qua `schema.doc_manifest`
(audit lượt 2, C-r2-5 / ADF-r2-6).

F2 (8ae13cf) đưa upgrade-on-read vào schema nhưng chỉ anh_chuan_bi dùng; 4 vai
*_nop (nop_chung), tao_task_kite và nút hạ sàn (duyet_bai) đọc thô — manifest
bản 0 thiếu so_dung_duoc thì hạ sàn báo "Chỉ 0 ảnh thật" dù có 6, và body Kite
tự đếm ra 4 trong khi schema đếm 2 (khái niệm là một chùm).

Cổng quét bằng ast, không quét chuỗi (E-r2-4): chỉ bắt lời gọi json.loads /
_doc_json / read_text mà đối số có literal "xong.json" — comment nhắc tới tên
tệp không tính. Ada/Itachi có xong.json RIÊNG (không phải manifest engine, không
có `anh`) nên không nằm trong cổng này.

Chạy:  venv/bin/python tests/test_xong_qua_schema.py
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

NGUOI_DOC_ENGINE = ["nop_chung.py", "duyet_bai.py", "anh_chuan_bi.py", "dre_chuan_bi.py",
                    "ethan_chuan_bi.py", "kite_chuan_bi.py", "miles_chuan_bi.py", "route_thieu_anh.py",
                    "dre_nop.py", "ethan_nop.py", "kite_nop.py", "miles_nop.py"]


def _co_xong_json(node) -> bool:
    return any(isinstance(n, ast.Constant) and n.value == "xong.json" for n in ast.walk(node))


def _ten_goi(call: ast.Call) -> str:
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")


def _doc_tho(src: str):
    """Cac lenh doc xong.json khong qua doc_manifest: [(dong, ten ham)]."""
    xau = []
    for n in ast.walk(ast.parse(src)):
        if not isinstance(n, ast.Call):
            continue
        ten = _ten_goi(n)
        if ten in ("loads", "_doc_json", "read_text", "_nap_json", "doc_json") and _co_xong_json(n):
            xau.append((n.lineno, ten))
    return xau


def test_khong_ai_doc_xong_json_tho():
    xau = []
    for ten in NGUOI_DOC_ENGINE:
        p = ROOT / ten
        if not p.exists():
            continue
        for dong, ham in _doc_tho(p.read_text(encoding="utf-8")):
            xau.append(f"{ten}:{dong} {ham}(... xong.json)")
    assert not xau, "doc xong.json tho, khong qua schema.doc_manifest:\n  " + "\n  ".join(xau)


def test_cong_bat_duoc_doc_tho_va_bo_qua_comment():
    assert _doc_tho('m = json.loads((wd / "xong.json").read_text())') == [(1, "loads"), (1, "read_text")]
    assert _doc_tho('x = cb._doc_json(wd / "xong.json")') == [(1, "_doc_json")]
    assert _doc_tho('# doc xong.json o day\nm = schema.doc_manifest(wd / "xong.json")') == []


def test_doc_manifest_bu_so_dung_duoc_cho_ban_0():
    import schema
    m0 = {"anh": [{"ma": "A1", "dung": ["bìa"], "lien_quan": True},
                  {"ma": "A2", "dung": ["thân"], "lien_quan": None}]}
    m = schema.doc_manifest(m0)
    assert m["so_dung_duoc"] == 2 and m["phien_ban"] == schema.PHIEN_BAN_MANIFEST, m


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
