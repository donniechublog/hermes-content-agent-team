#!/usr/bin/env python3
"""Mọi người đọc manifest engine (`manifest.json`) phải đi qua `schema.read_manifest`
(audit lượt 2, C-r2-5 / ADF-r2-6).

F2 (8ae13cf) đưa upgrade-on-read vào schema nhưng chỉ image_prepare dùng; 4 vai
*_submit (submit_common), create_task_kite và nút hạ sàn (approve_post) đọc thô — manifest
bản 0 thiếu so_dung_duoc (nay `usable_count`) thì hạ sàn báo "Chỉ 0 ảnh thật" dù có 6, và body Kite
tự đếm ra 4 trong khi schema đếm 2 (khái niệm là một chùm).

Cổng quét bằng ast, không quét chuỗi (E-r2-4): chỉ bắt lời gọi json.loads /
_read_json / read_text mà đối số NÊU TÊN manifest — comment nhắc tới tên tệp
không tính. Ada/Itachi có manifest.json RIÊNG (không phải manifest engine, không
có `images`) nên không nằm trong cổng này.

LOW-228 (17/09/2026): tên tệp đổi `xong.json` -> `manifest.json` và code dựng
đường dẫn qua `state_paths.MANIFEST_FILE` thay vì literal. Cổng cũ chỉ so literal
"xong.json" nên sau đợt đổi tên sẽ im lặng không bắt gì. Nay "nêu tên manifest" =
literal "manifest.json", literal cũ "xong.json" (bắt cả đường lùi về tên cũ),
thuộc tính `<x>.MANIFEST_FILE`, hoặc tên `MANIFEST_FILE` / bí danh của nó khi
`from state_paths import MANIFEST_FILE [as X]`.

Chạy:  venv/bin/python tests/test_done_over_schema.py
"""
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import state_paths                                            # noqa: E402

NGUOI_DOC_ENGINE = ["submit_common.py", "approve_post.py", "image_prepare.py", "dre_prepare.py",
                    "ethan_prepare.py", "kite_prepare.py", "miles_prepare.py", "route_missing_images.py",
                    "dre_submit.py", "ethan_submit.py", "kite_submit.py", "miles_submit.py"]
# Ada/Itachi ghi tệp CÙNG TÊN nhưng không phải manifest engine: cố ý ngoài cổng.
NGOAI_CONG = ["ada_prepare.py", "ada_submit.py", "itachi_prepare.py", "itachi_submit.py"]

TEN_MANIFEST = {state_paths.MANIFEST_FILE, "xong.json"}
HANG_MANIFEST = "MANIFEST_FILE"
HAM_DOC = ("loads", "_read_json", "read_text", "_load_json", "doc_json")


def _manifest_aliases(tree) -> set:
    """Tên cục bộ trỏ tới state_paths.MANIFEST_FILE (`from state_paths import MANIFEST_FILE as X`)."""
    ra = {HANG_MANIFEST}
    for n in ast.walk(tree):
        if isinstance(n, ast.ImportFrom) and (n.module or "").split(".")[-1] == "state_paths":
            ra |= {a.asname or a.name for a in n.names if a.name == HANG_MANIFEST}
    return ra


def _names_manifest(node, aliases: set) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Constant) and n.value in TEN_MANIFEST:
            return True
        if isinstance(n, ast.Attribute) and n.attr == HANG_MANIFEST:
            return True
        if isinstance(n, ast.Name) and n.id in aliases:
            return True
    return False


def _name_call(call: ast.Call) -> str:
    f = call.func
    return f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")


def _read_raw(src: str):
    """Cac lenh doc manifest khong qua read_manifest: [(dong, ten ham)]."""
    tree = ast.parse(src)
    aliases = _manifest_aliases(tree)
    xau = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        ten = _name_call(n)
        if ten in HAM_DOC and _names_manifest(n, aliases):
            xau.append((n.lineno, ten))
    return xau


def _mention_count(src: str) -> int:
    """So nut AST nêu tên manifest — de chung minh cong khong mu."""
    tree = ast.parse(src)
    aliases = _manifest_aliases(tree)
    return sum(1 for n in ast.walk(tree)
               if (isinstance(n, ast.Constant) and n.value in TEN_MANIFEST)
               or (isinstance(n, ast.Attribute) and n.attr == HANG_MANIFEST)
               or (isinstance(n, ast.Name) and n.id in aliases))


def test_no_ai_read_done_json_raw():
    xau = []
    for ten in NGUOI_DOC_ENGINE:
        p = ROOT / ten
        if not p.exists():
            continue
        for dong, ham in _read_raw(p.read_text(encoding="utf-8")):
            xau.append(f"{ten}:{dong} {ham}(... {state_paths.MANIFEST_FILE})")
    assert not xau, (f"doc {state_paths.MANIFEST_FILE} tho, khong qua schema.read_manifest:\n  "
                     + "\n  ".join(xau))


def test_gate_not_blind_readers_still_name_manifest():
    """Neu code doi cach neu ten manifest (vd hang moi) ma cong khong theo, cong
    se xanh vi khong thay gi. Nguoi doc engine phai con nhac toi manifest o dang
    cong nhan ra duoc."""
    tong = sum(_mention_count((ROOT / ten).read_text(encoding="utf-8"))
               for ten in NGUOI_DOC_ENGINE if (ROOT / ten).exists())
    assert tong > 0, "khong tep nao trong NGUOI_DOC_ENGINE nhac toi manifest — cong dang mu"


def test_gate_catch_ok_read_raw_and_skip_comment():
    assert _read_raw('m = json.loads((wd / "xong.json").read_text())') == [(1, "loads"), (1, "read_text")]
    assert _read_raw('x = cb._read_json(wd / "xong.json")') == [(1, "_read_json")]
    assert _read_raw('# doc xong.json o day\nm = schema.read_manifest(wd / "xong.json")') == []


def test_gate_catch_raw_read_through_state_paths_constant():
    """LOW-228: doc tho qua hang so van bi bat; qua read_manifest van qua."""
    assert _read_raw("m = json.loads((wd / state_paths.MANIFEST_FILE).read_text())") == \
        [(1, "loads"), (1, "read_text")]
    assert _read_raw('m = json.loads((wd / "manifest.json").read_text())') == [(1, "loads"), (1, "read_text")]
    assert _read_raw("x = cb._read_json(wd / sp.MANIFEST_FILE)") == [(1, "_read_json")]
    assert _read_raw("from state_paths import MANIFEST_FILE as MF\n"
                     "m = json.loads((wd / MF).read_text())") == [(2, "loads"), (2, "read_text")]
    assert _read_raw("# doc manifest.json o day\n"
                     "m = schema.read_manifest(wd / state_paths.MANIFEST_FILE)") == []
    # tep khac trong workdir khong phai manifest -> khong bat
    assert _read_raw("x = json.loads((wd / state_paths.FIND_MORE_FILE).read_text())") == []


def test_ada_itachi_outside_gate():
    assert not set(NGOAI_CONG) & set(NGUOI_DOC_ENGINE)


def test_read_manifest_fallback_count_use_ok_wait_copy_0():
    import schema
    m0 = {"anh": [{"ma": "A1", "dung": ["bìa"], "lien_quan": True},
                  {"ma": "A2", "dung": ["thân"], "lien_quan": None}]}
    m = schema.read_manifest(m0)
    assert m["usable_count"] == 2 and m["version"] == schema.VERSION_MANIFEST, m


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
