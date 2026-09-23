#!/usr/bin/env python3
"""Cong chan RO RI THU MUC TAM (LOW-390, 23/09/2026).

`tempfile.mkdtemp()` tra ve mot duong dan roi QUEN no: khong context manager,
khong finalizer, khong gi ca. Thu muc do nam lai mai mai. `TemporaryDirectory()`
thi tu don khi ra khoi `with`.

Vi sao thanh cong chan chu khong phai loi khuyen: 23/09/2026 may chu dc-group co
**3.185 thu muc tam bo lai, ~2,6 GB**, sinh deu ~1.600 moi ngay (1.617 hom truoc,
1.568 hom sau). `/tmp` o do la **tmpfs — an RAM, khong phai dia**. Goc la 40 cho
`mkdtemp()` trong 18 tep test, cong chinh dong `mktemp -d` cua `tests/run.sh`.
Khong cong nao bat duoc vi khong ai do rac de lai.

HAI CONG, co y bo tro nhau:
  - Cong TINH (tep nay): bat `mkdtemp(` MOI luc doc ma. Nhanh, chi ro dong nao.
  - Cong DONG (`tests/run.sh`): moi tep test chay trong TMPDIR rieng, con gi
    trong do la do. Cham hon nhung bat duoc ca ro ri cua THU VIEN (playwright,
    chromium) — thu ma grep khong bao gio thay.

CAN mkdtemp that (thu muc phai song lau hon ham tao ra no) thi ghi chu thich
`# mkdtemp-ok: <ly do>` ngay tren dong do. Khong co danh sach baseline roi rac:
ly do nam nearby ma, doc la thay.

Chay:  venv/bin/python tests/test_temp_cleanup.py
"""
import ast
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
EXEMPT_MARK = "mkdtemp-ok"

# Thu muc khong phai ma cua du an.
SKIP_DIRS = {"venv", ".git", "__pycache__", "node_modules", "state", "assets", "hermes"}


def _py_files() -> list:
    ra = []
    for p in ROOT.rglob("*.py"):
        if any(x in SKIP_DIRS for x in p.relative_to(ROOT).parts):
            continue
        ra.append(p)
    return sorted(ra)


def find_mkdtemp(path: Path) -> list:
    """[(dong, nguyen_van)] cac cho goi mkdtemp KHONG co chu thich mien."""
    try:
        src = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return []
    if "mkdtemp" not in src:
        return []
    src_lines = src.splitlines()
    try:
        tree = ast.parse(src)
    except SyntaxError:
        return []
    ra = []
    for n in ast.walk(tree):
        if not isinstance(n, ast.Call):
            continue
        f = n.func
        ten = f.attr if isinstance(f, ast.Attribute) else getattr(f, "id", "")
        if ten != "mkdtemp":
            continue
        i = n.lineno - 1
        # Chu thich mien dat ngay tren dong goi, hoac tren chinh dong do. Doc
        # NGUOC het khoi `#` lien ke phia tren chu khong chi mot dong: ly do
        # that thuong dai hai ba dong, bat no phai gon trong mot dong thi nguoi
        # ta viet ly do cut lui cho vua.
        nearby = [src_lines[i]]
        j = i - 1
        while j >= 0 and src_lines[j].lstrip().startswith("#"):
            nearby.append(src_lines[j])
            j -= 1
        if any(EXEMPT_MARK in c for c in nearby):
            continue
        ra.append((n.lineno, src_lines[i].strip()))
    return ra


def test_no_bare_mkdtemp_left():
    """Khong tep nao duoc goi `mkdtemp()` tran. Do la cai da de lai 2,6 GB."""
    bad = []
    for p in _py_files():
        for dong, text in find_mkdtemp(p):
            bad.append(f"{p.relative_to(ROOT)}:{dong}  {text[:70]}")
    assert not bad, (
        f"\n{len(bad)} cho goi tempfile.mkdtemp() ma khong co buoc don:\n  "
        + "\n  ".join(bad)
        + "\n\nDoi sang `with tempfile.TemporaryDirectory() as d:` (tu don khi ra"
          " khoi with).\nThuc su can thu muc song lau hon ham thi ghi"
          f" `# {EXEMPT_MARK}: <ly do>` ngay tren dong do."
    )


def test_shell_mktemp_needs_trap():
    """`mktemp -d` trong .sh phai di kem `trap ... rm` — khong thi no o lai mai.

    `tests/run.sh` tung la mot nguon ro ri nhu vay: no tao CT_STATE_DIR bang
    `mktemp -d` roi khong bao gio xoa (54 thu muc `tmp.XXXX` tren may chu)."""
    bad = []
    for p in sorted(ROOT.rglob("*.sh")):
        if any(x in SKIP_DIRS for x in p.relative_to(ROOT).parts):
            continue
        try:
            src = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if not re.search(r"mktemp\s+-d", src):
            continue
        if re.search(r"\btrap\b.*\brm\b", src):
            continue
        bad.append(str(p.relative_to(ROOT)))
    assert not bad, (
        "Tep .sh goi `mktemp -d` ma khong co `trap ... rm ...` de don khi thoat: "
        + ", ".join(bad)
    )


def test_runtime_gate_still_wired_in_run_sh():
    """Cong DONG khong bi go am tham: `run.sh` phai con do rac va do khi con rac.

    Cong tinh chi thay `mkdtemp` trong ma minh viet; ro ri cua playwright hay
    chromium chi cong dong moi thay. Go mot trong hai la mat mot nua tam nhin."""
    src = (ROOT / "tests" / "run.sh").read_text(encoding="utf-8")
    # `_tmp_run` + `trap` la lop 1 (LOW-382, don goc TMPDIR cua ca luot);
    # `TMPDIR=` tung tep + `trash_total` + "RAC TAM" la lop 2 (LOW-390, quy
    # trach nhiem va chan). Go bat ky manh nao la mat mot nua tac dung.
    for piece in ("_tmp_run", "trap ", "TMPDIR=", "trash_total", "RAC TAM"):
        assert piece in src, f"tests/run.sh thieu phan cong do rac tam: {piece!r}"


def test_static_gate_really_catches():
    """Cong bat duoc mkdtemp tran, va chu thich mien thi cho qua — kiem tren
    van ban that, khong tin vao viec doc ma bang mat."""
    import tempfile as _tf
    with _tf.TemporaryDirectory() as d:
        bad = Path(d) / "bad.py"
        bad.write_text("import tempfile\nd = tempfile.mkdtemp()\n", encoding="utf-8")
        assert find_mkdtemp(bad), "cong KHONG bat duoc mkdtemp tran"

        good = Path(d) / "good.py"
        good.write_text("import tempfile\n# mkdtemp-ok: thu muc song het phien\n"
                       "d = tempfile.mkdtemp()\n", encoding="utf-8")
        assert not find_mkdtemp(good), "chu thich mien khong duoc ton trong"

        # Ly do dai hai dong cung phai duoc ton trong — bat gon mot dong thi
        # nguoi ta viet ly do cut lui cho vua (chinh skill_lesson_commit.py can
        # hai dong de noi ro `finally` don o dau).
        multiline = Path(d) / "multiline.py"
        multiline.write_text("import tempfile\n# mkdtemp-ok: don o finally ngay duoi,\n"
                       "# trong remove_worktree() co shutil.rmtree\n"
                       "d = tempfile.mkdtemp()\n", encoding="utf-8")
        assert not find_mkdtemp(multiline), "chu thich mien nhieu dong bi bo qua"

        clean = Path(d) / "clean.py"
        clean.write_text("import tempfile\nwith tempfile.TemporaryDirectory() as d:\n"
                        "    pass\n", encoding="utf-8")
        assert not find_mkdtemp(clean), "TemporaryDirectory bi bat nham"


if __name__ == "__main__":
    n = 0
    for ten, ham in sorted(globals().items()):
        if ten.startswith("test_") and callable(ham):
            ham()
            n += 1
            print(f"  ok  {ten}")
    print(f"\n{n}/{n} test qua")
