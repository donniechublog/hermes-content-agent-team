#!/usr/bin/env python3
"""state_paths.py (LOW-228): tên English cho mọi tệp/thư mục dưới state/<brand>/prepare/<draft_id>/.

Giữ ba điều:
  1. `prepare_root` TỪ CHỐI state còn thư mục `chuan_bi/` cũ (NotMigrated) — lặng lẽ
     tạo `prepare/` rỗng cạnh 192 draft cũ thì mọi draft trông như chưa chuẩn bị.
  2. Mọi hằng trong state_paths khớp đúng tên MỚI trong bảng đã duyệt
     docs/tu_dien_ten/state_paths_v2.json — code và bảng migrate không được lệch.
  3. Quét tĩnh (ast) mã production: không còn tên CŨ nằm ở chỗ dựng đường dẫn
     (toán hạng `/`, `open(...)`, `Path(...)`, `.glob(...)`…), và không còn chuỗi
     mang dạng tên tệp cũ (`chuan_bi.<n>.lock`, `xep_hang_<b>.png`, `chup_<n>_<k>.png`,
     `<id>.ngang.png`, `<id>.ban_giao.md`, `them_<n>`). Cùng từ tiếng Việt đó ở chỗ
     KHÔNG phải đường dẫn vẫn hợp lệ: `a.get("source") == "khai_niem"` là giá trị
     nguồn ảnh, không phải thư mục.

Ngoài phạm vi quét: shim LOW-50 (`*chuan_bi*.py`, gói `chuan_bi/`), chính bảng đổi
tên (`state_path_migration.py`, `migrate_state_paths.py`), `docs/`, `tests/`.

Chạy:  venv/bin/python tests/test_state_paths.py
"""
import ast
import json
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import state_paths                                            # noqa: E402

TABLE = json.loads((ROOT / "docs" / "tu_dien_ten" / "state_paths_v2.json").read_text(encoding="utf-8"))


# ------------------------------------------------------------ 1. prepare_root
def test_prepare_root_refuses_unmigrated_state():
    with tempfile.TemporaryDirectory() as t:
        state = Path(t)
        (state / "chuan_bi" / "some-draft").mkdir(parents=True)
        try:
            state_paths.prepare_root(state)
        except state_paths.NotMigrated as e:
            assert "chuan_bi" in str(e), e
        else:
            raise AssertionError("state con chuan_bi/ ma prepare_root khong nem NotMigrated")
        try:
            state_paths.workdir(state, "some-draft")
        except state_paths.NotMigrated:
            pass
        else:
            raise AssertionError("workdir phai di qua prepare_root va cung tu choi")
        assert not (state / "prepare").exists(), "khong duoc tao prepare/ khi tu choi"


def test_prepare_root_returns_prepare_when_migrated():
    with tempfile.TemporaryDirectory() as t:
        state = Path(t)
        assert state_paths.prepare_root(state) == state / "prepare"
        (state / "prepare").mkdir()
        assert state_paths.prepare_root(state) == state / "prepare"
        assert state_paths.workdir(state, "d1") == state / "prepare" / "d1"
        # tep (khong phai thu muc) ten chuan_bi khong phai layout cu
        (state / "chuan_bi").write_text("x")
        assert state_paths.prepare_root(state) == state / "prepare"


def test_not_migrated_is_runtime_error():
    assert issubclass(state_paths.NotMigrated, RuntimeError)


def test_helpers_build_new_names():
    wd = Path("/s/prepare/d1")
    assert state_paths.extra_dir(wd, 2) == wd / "extra_2"
    assert state_paths.handoff_file(Path("/drafts"), "d1") == Path("/drafts/d1.handoff.md")


# ------------------------------------------------------- 2. hang khop bang duyet
def test_constants_match_approved_table():
    t = TABLE
    df, dirs, pats = t["draft_files"], t["dirs"], t["file_patterns"]
    pairs = {
        "PREPARE_DIR": t["root"]["chuan_bi"],
        "LOCK_FILE": t["lock"]["chuan_bi.{n}.lock"].replace("{n}", "{}"),
        "MANIFEST_FILE": df["xong.json"],
        "PREPARE_LOG": df["chuan_bi.log"],
        "MATERIAL_FILE": df["tu_lieu.md"],
        "CONTACT_SHEET_FILE": df["bang_anh.png"],
        "RUNNING_PID_FILE": df["dang_chay.pid"],
        "CRASH_COUNT_FILE": df["so_lan_chet.json"],
        "FIND_MORE_FILE": df["tim_them.json"],
        "PREVIOUS_SUBMISSION_FILE": df["da_dung.json"],
        "SUBMIT_COUNT_FILE": df["nop_lan.json"],
        "ORIGINAL_DIR": dirs["goc"],
        "READY_DIR": dirs["san"],
        "EXTRA_DIR": dirs["them"],
        "CONCEPT_DIR": dirs["khai_niem"],
        "BRAND_MATCH_DIR": dirs["thuong_hieu"],
        "ENTITY_DIR": dirs["thuc_the"],
        "CAPTURE_SOURCE_DIR": dirs["chup_nguon"],
        "RANKING_DIR": dirs["xh"],
        "BOARD_DIR": dirs["bang"],
        "RANKING_IMAGE_PREFIX": pats["xep_hang_{board}.png"].split("{")[0],
        "CAPTURE_IMAGE_PREFIX": pats["chup_{n}_{k}.png"].split("{")[0],
        "LANDSCAPE_SUFFIX": pats["{id}.ngang.png"].split("}", 1)[1],
        "HANDOFF_SUFFIX": pats["{draft_id}.ban_giao.md"].split("}", 1)[1],
        "LEGACY_PREPARE_DIR": "chuan_bi",
    }
    sai = {k: (getattr(state_paths, k, None), v) for k, v in pairs.items() if getattr(state_paths, k, None) != v}
    assert not sai, f"hang lech bang duyet (hang, bang): {sai}"
    # them_{n} -> extra_{n} di qua extra_dir
    assert dirs["them_{n}"] == "extra_{n}" and state_paths.extra_dir(Path("w"), 3).name == "extra_3"
    # moi hang chuoi IN HOA deu da duoc doi chieu — hang moi phai vao bang truoc
    hang = {k for k, v in vars(state_paths).items() if k.isupper() and isinstance(v, str)}
    thieu = sorted(hang - set(pairs))
    assert not thieu, f"hang chua doi chieu voi state_paths_v2.json: {thieu}"


def test_every_draft_file_and_dir_in_table_has_a_constant():
    """Moi dong cua bang (tru ban sao luu v1.bak cua LOW-227) co mot hang tuong ung."""
    gia_tri = {v for k, v in vars(state_paths).items() if k.isupper() and isinstance(v, str)}
    moi = [v for k, v in TABLE["draft_files"].items() if not k.endswith(".bak")]
    moi += [v for k, v in TABLE["dirs"].items() if "{" not in k]
    thieu = sorted(set(moi) - gia_tri)
    assert not thieu, f"ten moi trong bang ma state_paths khong co hang: {thieu}"


# ------------------------------------------------------------ 3. quet production
OLD_NAMES = {"chuan_bi", "xong.json", "goc", "san", "bang_anh.png", "tu_lieu.md", "dang_chay.pid",
             "so_lan_chet.json", "tim_them.json", "da_dung.json", "nop_lan.json", "xh"}
# Phan con lai cua bang (thu muc vong tim anh, chuan_bi.log) cung la ten cu o cho duong dan.
OLD_NAMES |= set(TABLE["root"]) | {k for k in TABLE["draft_files"]} | {k for k in TABLE["dirs"] if "{" not in k}

# Dang ten tep cu — sai o BAT KY chuoi nao (khong tinh docstring). \0 = cho {bieu thuc} cua f-string.
OLD_FILE_SHAPES = [
    re.compile(r"^chuan_bi\."),                     # chuan_bi.{i}.lock, chuan_bi.log
    re.compile(r"^xep_hang_.*\.png$"),              # xep_hang_<board>.png
    re.compile(r"^chup_.*\.png$"),                  # chup_<n>_<k>.png
    re.compile(r"\.ngang\.png"),                    # <id>.ngang.png
    re.compile(r"\.ban_giao\.md"),                  # <draft_id>.ban_giao.md
    re.compile(r"^them_(\d+|\x00)$"),               # them_<n>
]

PATH_FUNCS = {"open", "Path", "PurePath", "PosixPath", "glob", "rglob", "joinpath", "join", "with_name"}
EXCLUDE_NAMES = {"state_path_migration.py", "migrate_state_paths.py"}


def _production_files():
    files = sorted(ROOT.glob("*.py")) + sorted((ROOT / "prepare").glob("*.py"))
    return [p for p in files if "chuan_bi" not in p.name and p.name not in EXCLUDE_NAMES]


def _template(node):
    """Chuoi cua Constant/JoinedStr, bieu thuc trong f-string thay bang \\0; None neu khong phai chuoi."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        return "".join(v.value if isinstance(v, ast.Constant) else "\x00" for v in node.values)
    return None


def _path_operands(node):
    """Cac nut chuoi DUNG o vi tri doan duong dan (di qua IfExp/BoolOp, khong di vao Call/Subscript)."""
    if isinstance(node, ast.IfExp):
        yield from _path_operands(node.body)
        yield from _path_operands(node.orelse)
    elif isinstance(node, ast.BoolOp):
        for v in node.values:
            yield from _path_operands(v)
    elif _template(node) is not None:
        yield node


def _skip_nodes(tree):
    """id cua docstring va cua phan hang BEN TRONG f-string (f-string duoc xet nguyen khoi)."""
    ra = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and n.body:
            first = n.body[0]
            if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant):
                ra.add(id(first.value))
        if isinstance(n, ast.JoinedStr):
            ra |= {id(v) for v in n.values}
    return ra


def _old_segment(tpl: str):
    for seg in tpl.split("/"):
        if seg in OLD_NAMES:
            return seg
    return None


def scan_source(src: str, name: str = "<src>") -> list:
    """[(ten tep, dong, mo ta)] cho moi cho production con dung ten cu."""
    tree = ast.parse(src)
    skip = _skip_nodes(tree)
    bad = []
    # (a) ten cu o vi tri doan duong dan
    for n in ast.walk(tree):
        cands = []
        if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
            cands = [n.left, n.right]
        elif isinstance(n, ast.Call):
            f = n.func
            fname = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
            if fname in PATH_FUNCS:
                cands = list(n.args)
        for c in cands:
            for op in _path_operands(c):
                seg = _old_segment(_template(op))
                if seg is not None:
                    bad.append((name, op.lineno, f"ten cu {seg!r} o cho dung duong dan"))
    # (b) chuoi mang dang ten tep cu, o bat ky dau (tru docstring)
    for n in ast.walk(tree):
        tpl = _template(n)
        if tpl is None or id(n) in skip:
            continue
        for rx in OLD_FILE_SHAPES:
            if rx.search(tpl):
                bad.append((name, n.lineno, f"chuoi dang ten tep cu {tpl.replace(chr(0), '{…}')!r}"))
                break
    return bad


def test_scanner_catches_old_path_names_and_allows_non_path_use():
    must_catch = [
        'wd / "goc" / f"{ma}.png"',
        'p = STATE_DIR / "chuan_bi" / draft_id / "xong.json"',
        'open(wd / "dang_chay.pid", "w")',
        'Path("state", "chuan_bi")',
        'wd.glob("goc/*.png")',
        'wd.glob("*/xong.json")',
        'd = wd / ("san" if ok else "goc")',
        'x = wd / f"chuan_bi/{d}/tu_lieu.md"',
        'lock = f"chuan_bi.{i}.lock"',
        'out = d / f"xep_hang_{slug}.png"',
        'ten = f"chup_{n}_{k}.png"',
        'p = src.with_name(f"{ma}.ngang.png")',
        'h = DRAFTS / f"{draft_id}.ban_giao.md"',
        'r = wd / f"them_{n}"',
        'r = wd / "them"',
        'r = wd / "thuong_hieu" / "xh"',
        'os.path.join(root, "bang_anh.png")',
    ]
    for src in must_catch:
        assert scan_source(src), f"quet bo sot: {src}"
    must_allow = [
        'ok = a.get("source") == "khai_niem"',
        'a["source"] = "chup_nguon"',
        'meta.add_text("nguon_dung", "chup_xep_hang")',
        'k = m.get("goc") or m.get("san")',
        'wd / m.get("goc")',
        'text = "ghép dọc với một ảnh ngang cùng tone"',
        'def f():\n    """ghi <id>.ngang.png va xong.json"""\n',
        'r = {"kind": "bang"}',
        'wd / state_paths.ORIGINAL_DIR / f"{ma}.png"',
        'wd / f"{ma}{state_paths.LANDSCAPE_SUFFIX}"',
    ]
    for src in must_allow:
        assert not scan_source(src), f"quet bat oan: {src} -> {scan_source(src)}"


def test_production_has_no_old_state_path_names():
    bad = []
    for p in _production_files():
        try:
            bad += scan_source(p.read_text(encoding="utf-8"), str(p.relative_to(ROOT)))
        except SyntaxError as e:
            bad.append((str(p.relative_to(ROOT)), e.lineno, f"SyntaxError {e.msg}"))
    assert not bad, (f"{len(bad)} cho production con ten duong dan cu (LOW-228):\n  "
                     + "\n  ".join(f"{f}:{d} {m}" for f, d, m in bad))


# Ten tep cap draft CO DUOI — trong chu gui vai/Ong Chu ("mở bang_anh.png", "Thiếu xong.json")
# ten cu cung sai: tep do khong con ton tai. Chan bien \w/. de "anh_da_dung.jsonl" (LOW-231) khong dinh.
OLD_FILE_TOKEN = re.compile(r"(?<![\w.])(" + "|".join(
    re.escape(k) for k in sorted(TABLE["draft_files"], key=len, reverse=True)) + r")(?![\w])")


def scan_text(src: str, name: str = "<src>") -> list:
    """[(ten tep, dong, ten cu)] cho chuoi (khong tinh docstring) nhac ten tep cap draft cu."""
    tree = ast.parse(src)
    skip = _skip_nodes(tree)
    bad = []
    for n in ast.walk(tree):
        if id(n) in skip:
            continue
        tpl = _template(n)
        if tpl is None:
            continue
        m = OLD_FILE_TOKEN.search(tpl)
        if m:
            bad.append((name, n.lineno, m.group(1)))
    return bad


def test_text_scanner_catches_old_file_names_in_messages():
    assert scan_text('L.append(f"Nhìn tất cả ảnh: {m[\'workdir\']}/bang_anh.png")')
    assert scan_text('note = "⚠️ Không đọc được bản chuẩn bị (xong.json)"')
    assert scan_text('x = "mở tu_lieu.md rồi đọc"')
    assert not scan_text('p = state_dir() / "anh_da_dung.jsonl"'), "LOW-231 ngoai pham vi"
    assert not scan_text('for f in d.glob("*_da_dung.jsonl"): pass')
    assert not scan_text('def f():\n    """doc xong.json"""\n')
    assert not scan_text('x = "mở contact_sheet.png rồi đọc material.md"')


def test_production_text_names_no_old_draft_files():
    bad = []
    for p in _production_files():
        try:
            bad += scan_text(p.read_text(encoding="utf-8"), str(p.relative_to(ROOT)))
        except SyntaxError:
            continue                                    # da bao o test_production_has_no_old_state_path_names
    assert not bad, (f"{len(bad)} chuoi production con nhac ten tep cu (LOW-228):\n  "
                     + "\n  ".join(f"{f}:{d} {m}" for f, d, m in bad))


def test_scan_covers_real_files():
    names = {p.name for p in _production_files()}
    assert {"image_prepare.py", "approve_post.py", "submit_common.py", "fallback_rounds.py"} <= names, names
    assert not any("chuan_bi" in n for n in names) and not names & EXCLUDE_NAMES


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
