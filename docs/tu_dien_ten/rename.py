#!/usr/bin/env python3
"""rename.py — THỰC THI đổi tên Việt-không-dấu → English theo từ điển (LOW-50).

Mỗi module là một đơn vị: đổi hàm/lớp top-level → hằng số → (tuỳ chọn) tên tệp
module, rồi vá chuỗi tham chiếu mà rope không thấy (test đọc văn bản nguồn,
`__all__`, SOUL/skill/cron nhắc `<tên>.py`), tạo shim cho tên tệp cũ, chạy
pyflakes + tests/chay.sh. Đỏ là dừng, để nguyên thay đổi cho người xem.

    venv/bin/python docs/tu_dien_ten/rename.py . vai [luat_anh ...]   # theo lô
    venv/bin/python docs/tu_dien_ten/rename.py . vai --dry-run        # chỉ in kế hoạch
    venv/bin/python docs/tu_dien_ten/rename.py . vai --no-module      # giữ tên tệp
    venv/bin/python docs/tu_dien_ten/rename.py . --package chuan_bi   # đổi thư mục gói (làm cuối)

Vì sao rope chứ không sed: `rope.refactor.rename` đổi ĐỊNH NGHĨA + MỌI NƠI GỌI
(import, `mod.ten`, `from mod import ten`) trong một bước bằng phân tích AST —
`docs=False` nên KHÔNG đụng chuỗi/chú thích → khoá JSON trên đĩa
(`m["xep_hang"]`) và đường dẫn state (`state/<brand>/chuan_bi/`) giữ nguyên.
Chuỗi nào PHẢI đổi (tên tệp script) thì vá riêng, có quy tắc hẹp, ở `_va_chuoi`.
"""
import argparse
import re
import subprocess
import sys
import tokenize
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tudien import TuDien, bang_doi_ten                      # noqa: E402

# Tệp ngoài .py được vá `<cũ>.py` -> `<mới>.py`. KHÔNG vá lịch sử (nhat_ky/,
# NHAT_KY_SU_CO.md) và không vá chính từ điển.
DUOI_VAN_BAN = ("*.md", "*.json", "*.sh", "*.yml", "*.yaml", "*.txt")
BO_VA = ("nhat_ky/", "NHAT_KY_SU_CO.md", "docs/tu_dien_ten/", "hermes-agent/", ".git/", "venv/")

SHIM = '''"""SHIM tạm (LOW-50): tên cũ của `{new}.py`. Mọi thứ nằm ở `{new}.py`.

Giữ để task kanban đang `ready`, cron và SOUL trên máy chủ gọi tên cũ vẫn chạy
trong lúc đổi. `sys.modules[__name__] = <module mới>` nên `import {old}` và
`{old}.ten` đều trỏ đúng đối tượng thật (kể cả tên `_riêng`). Gỡ sau 1 tuần
(ticket con của LOW-50)."""
import sys as _sys

import {new} as _new

_sys.modules[__name__] = _new

if __name__ == "__main__":
    _sys.exit(_new.main() if hasattr(_new, "main") else 0)
'''


def _log(*a):
    print("[rename]", *a, file=sys.stderr)


# ---- rope ------------------------------------------------------------------
def _project(root: Path):
    from rope.base.project import Project
    return Project(str(root), ropefolder=None, save_objectdb=False,
                   ignored_resources=["venv", "hermes", ".claude", "__pycache__", "drafts",
                                      "state", "assets", "docs", ".git", "*.pyc"])


def _rope_rename(proj, res_path: str, offset, new_name: str) -> list:
    """Một lần rename qua rope. Trả danh sách tệp đã đổi."""
    from rope.refactor.rename import Rename
    res = proj.get_resource(res_path)
    ch = Rename(proj, res, offset).get_changes(new_name, docs=False)
    tep = [c.resource.path for c in ch.changes if hasattr(c, "resource")]
    proj.do(ch)
    return tep


def _offset_def(text: str, name: str, kind: str):
    if kind == "const":
        m = re.search(rf"^{re.escape(name)}\s*=", text, re.M)
        return m.start() if m else None
    m = re.search(rf"^(?:async\s+)?(?:def|class)\s+{re.escape(name)}\b", text, re.M)
    return (m.end() - len(name)) if m else None


# ---- vá chuỗi ------------------------------------------------------------------
_KHOA_DICT_CACHE = {}


def _khoa_dict(root: Path) -> set:
    """Mọi tên đang dùng làm KHOÁ dict/JSON trong mã chính: m["x"], .get("x"), "x":.
    Đây là hợp đồng dữ liệu trên đĩa — tuyệt đối không đổi (luật LOW-49)."""
    k = str(root)
    if k in _KHOA_DICT_CACHE:
        return _KHOA_DICT_CACHE[k]
    pat = re.compile(r'\[\s*["\']([A-Za-z_][\w]*)["\']\s*\]|\.get\(\s*["\']([A-Za-z_][\w]*)["\']|["\']([A-Za-z_][\w]*)["\']\s*:')
    ra = set()
    for f in list(root.glob("*.py")) + list(root.glob("chuan_bi/*.py")):
        for m in pat.finditer(f.read_text(encoding="utf-8")):
            ra.add(next(g for g in m.groups() if g))
    _KHOA_DICT_CACHE[k] = ra
    return ra


def _thay_trong_chuoi_py(path: Path, thay: list) -> int:
    """Thay TRONG STRING LITERAL của một tệp .py (tokenize), không đụng mã.
    `thay` = [(regex, replacement)]. Trả số lần thay."""
    src = path.read_text(encoding="utf-8")
    try:
        toks = list(tokenize.generate_tokens(iter(src.splitlines(True)).__next__))
    except (tokenize.TokenError, SyntaxError):
        return 0
    lines = src.splitlines(True)
    n = 0
    # duyệt ngược để offset không trôi
    for t in reversed(toks):
        if t.type != tokenize.STRING:
            continue
        (r0, c0), (r1, c1) = t.start, t.end
        if r0 != r1:                          # chuỗi nhiều dòng: chỉ phần TRONG chuỗi
            dau, cuoi = lines[r0 - 1][:c0], lines[r1 - 1][c1:]
            block = lines[r0 - 1][c0:] + "".join(lines[r0:r1 - 1]) + lines[r1 - 1][:c1]
            moi = block
            for pat, rep in thay:
                moi, k = re.subn(pat, rep, moi)
                n += k
            if moi != block:
                lines[r0 - 1:r1] = [dau + moi + cuoi]
            continue
        line = lines[r0 - 1]
        s = line[c0:c1]
        moi = s
        for pat, rep in thay:
            moi, k = re.subn(pat, rep, moi)
            n += k
        if moi != s:
            lines[r0 - 1] = line[:c0] + moi + line[c1:]
    if n:
        path.write_text("".join(lines), encoding="utf-8")
    return n


def _va_chuoi(root: Path, mod_cu: str, mod_moi, defs: list, consts: list):
    """Sau rope: (1) `<cũ>.py` -> `<mới>.py` ở mọi tệp văn bản + string literal
    .py; (2) trong tests: `def cũ(` / `cũ(` trong string literal -> mới (test
    đọc văn bản nguồn); (3) `__all__` của chính module: `"cũ"` -> `"mới"`."""
    tong = 0
    if mod_moi and mod_moi != mod_cu:
        cu_py = mod_cu.split(".")[-1] + ".py"
        moi_py = mod_moi.split(".")[-1] + ".py"
        pat = [(rf"(?<![\w/])(?:{re.escape(mod_cu.split('.')[-1])})\.py\b", moi_py)]
        for duoi in DUOI_VAN_BAN:
            for f in root.rglob(duoi):
                r = str(f.relative_to(root))
                if any(b in r for b in BO_VA):
                    continue
                s = f.read_text(encoding="utf-8", errors="ignore")
                moi, k = re.subn(pat[0][0], pat[0][1], s)
                if k:
                    f.write_text(moi, encoding="utf-8")
                    tong += k
        for f in list(root.glob("*.py")) + list(root.glob("chuan_bi/*.py")) + list(root.glob("tests/*.py")):
            tong += _thay_trong_chuoi_py(f, pat)
        _log(f"  chuỗi `{cu_py}` -> `{moi_py}`: {tong} chỗ")
    # (2) test đọc văn bản nguồn: `def cũ(`, `cũ(`, và `modcũ.cũ` (test_tim_anh_theo_vai
    # tìm chuỗi "vai.du_nguyen_lieu" trong nguồn anh_chuan_bi). Thay theo CẶP
    # (module, tên) nên không đụng khoá JSON kiểu "vai" trần.
    thay = []
    mc = mod_cu.split(".")[-1]
    mm = (mod_moi or mod_cu).split(".")[-1]
    # Test hay viết chuỗi REGEX: `vai\.so_anh_toi_thieu\(` — dấu `\` trước `.`/`(`
    # phải được chấp nhận và GIỮ NGUYÊN (\g<1>), không thì test soi nguồn đỏ.
    for old, new, _kind in defs:
        thay.append((rf"(?<![\w.])def {re.escape(old)}(?=\\?\()", f"def {new}"))
        thay.append((rf"(?<![\w.\\]){re.escape(old)}(?=\\?\()", new))
        thay.append((rf"(?<![\w]){re.escape(mc)}(\\?\.){re.escape(old)}\b", rf"{mm}\g<1>{new}"))
    for old, new in consts:
        # `$` loại trừ biến shell trong chuỗi test ("$VAI" của quet_daily_scan.sh
        # không phải hằng Python — pilot 13/09 đã đổi nhầm thành "$ROLE").
        thay.append((rf"(?<![\w.$]){re.escape(old)}\b", new))
        thay.append((rf"(?<![\w]){re.escape(mc)}(\\?\.){re.escape(old)}\b", rf"{mm}\g<1>{new}"))
    if mod_moi and mc != mm:                   # `modcũ.tên_giữ_nguyên` -> `modmới.tên`
        thay.append((rf"(?<![\w]){re.escape(mc)}(?=\\?\.[A-Za-z_])", mm))
    # Tên TRẦN trong ngoặc kép ("du_nguyen_lieu") — test soi AST hỏi tên hàm.
    # CHỈ khi tên đó không phải khoá dict/JSON ở đâu trong mã (m["xep_hang"],
    # .get("xep_hang"), "xep_hang":) — khoá trên đĩa không được đổi.
    khoa_json = _khoa_dict(root)
    tran = [(rf'(["\']){re.escape(old)}\1', rf"\g<1>{new}\g<1>")
            for old, new, _k in defs if old not in khoa_json]
    tran += [(rf'(["\']){re.escape(old)}\1', rf"\g<1>{new}\g<1>")
             for old, new in consts if old not in khoa_json]
    bo = [o for o, _n, _k in defs if o in khoa_json] + [o for o, _n in consts if o in khoa_json]
    if bo:
        _log(f"  (không thay tên trần trong chuỗi vì trùng khoá dict: {', '.join(bo)})")
    if thay or tran:
        k2 = 0
        for f in root.glob("tests/*.py"):
            k2 += _thay_trong_chuoi_py(f, thay)
            src = f.read_text(encoding="utf-8")
            if tran and ("read_text(" in src or "ast.parse" in src or "_ten_ham_trong" in src):
                k2 += _thay_trong_chuoi_py(f, tran)
        if k2:
            _log(f"  chuỗi trong tests (def/gọi/hằng): {k2} chỗ")
        tong += k2
    # (3) __all__ của chính module
    mod_path = root / (mod_moi or mod_cu).replace(".", "/")
    mod_path = mod_path.with_suffix(".py")
    if mod_path.exists() and "__all__" in mod_path.read_text(encoding="utf-8"):
        s = mod_path.read_text(encoding="utf-8")
        a, b = s.index("__all__"), s.index("]", s.index("__all__"))
        khoi = s[a:b]
        moi = khoi
        for old, new, _k in defs:
            moi = moi.replace(f'"{old}"', f'"{new}"')
        for old, new in consts:
            moi = moi.replace(f'"{old}"', f'"{new}"')
        if moi != khoi:
            mod_path.write_text(s[:a] + moi + s[b:], encoding="utf-8")
            _log("  __all__ cập nhật")
    return tong


# ---- kiểm sau mỗi module -------------------------------------------------------
def _kiem(root: Path, py: str) -> bool:
    r = subprocess.run([py, "-m", "pyflakes", *map(str, root.glob("*.py")), *map(str, root.glob("chuan_bi/*.py")),
                        *map(str, root.glob("tests/*.py"))], capture_output=True, text=True)
    if r.returncode:
        _log("pyflakes ĐỎ:\n" + r.stdout[-3000:])
        return False
    r = subprocess.run(["bash", "tests/chay.sh"], cwd=str(root), capture_output=True, text=True,
                       env={**__import__("os").environ, "PY": py})
    tail = r.stdout.strip().splitlines()[-2:]
    _log("tests:", " | ".join(tail))
    if r.returncode:
        _log("tests ĐỎ:\n" + "\n".join(l for l in r.stdout.splitlines() if "FAIL" in l or "HONG" in l)[-3000:])
        return False
    return True


# ---- một module -----------------------------------------------------------------
def doi_mot_module(root: Path, td: TuDien, plan: dict, mod: str, doi_tep: bool, dry: bool, proj=None):
    defs = plan["defs"].get(mod, [])
    consts = plan["consts"].get(mod, [])
    mod_moi = plan["modules"].get(mod) if doi_tep else None
    res_path = mod.replace(".", "/") + ".py"
    _log(f"== {mod}: {len(defs)} hàm/lớp, {len(consts)} hằng, tệp -> {mod_moi or '(giữ)'}")
    if dry:
        for old, new, k in defs:
            print(f"   {k:<5} {old} -> {new}")
        for old, new in consts:
            print(f"   const {old} -> {new}")
        return True
    if proj is None:
        proj = _project(root)
    # 1) hàm/lớp
    for old, new, kind in defs:
        text = (root / res_path).read_text(encoding="utf-8")
        off = _offset_def(text, old, kind)
        if off is None:
            _log(f"  !! không tìm thấy định nghĩa {old} — bỏ qua")
            continue
        tep = _rope_rename(proj, res_path, off, new)
        _log(f"  {old} -> {new}  ({len(tep)} tệp)")
    # 2) hằng số
    for old, new in consts:
        text = (root / res_path).read_text(encoding="utf-8")
        off = _offset_def(text, old, "const")
        if off is None:
            _log(f"  !! không tìm thấy hằng {old} — bỏ qua")
            continue
        tep = _rope_rename(proj, res_path, off, new)
        _log(f"  {old} -> {new}  ({len(tep)} tệp)")
    # 3) tên tệp module (chỉ tên tệp, không đổi thư mục gói ở đây)
    if mod_moi:
        base_moi = mod_moi.split(".")[-1]
        tep = _rope_rename(proj, res_path, None, base_moi)
        _log(f"  module {mod} -> {base_moi}  ({len(tep)} tệp)")
        res_path_moi = "/".join(mod.split(".")[:-1] + [base_moi]) + ".py"
        _va_chuoi(root, mod, ".".join(mod.split(".")[:-1] + [base_moi]), defs, consts)
        shim = root / res_path
        if not shim.exists():
            shim.write_text(SHIM.format(old=mod.split(".")[-1], new=base_moi), encoding="utf-8")
            _log(f"  shim {shim.name} -> {base_moi}")
        assert (root / res_path_moi).exists()
    else:
        _va_chuoi(root, mod, None, defs, consts)
    return True


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("root")
    ap.add_argument("modules", nargs="*")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--no-module", action="store_true", help="giữ tên tệp, chỉ đổi hàm/hằng")
    ap.add_argument("--no-test", action="store_true")
    ap.add_argument("--package", help="đổi tên THƯ MỤC gói (vd chuan_bi) — làm cuối, một mình")
    ap.add_argument("--docs", default=str(Path(__file__).resolve().parent))
    a = ap.parse_args()
    root = Path(a.root).resolve()
    td = TuDien(Path(a.docs))
    plan = bang_doi_ten(td, root)
    py = str(root / "venv/bin/python") if (root / "venv/bin/python").exists() else sys.executable
    if a.package:
        moi = td.dich_module(a.package)[0]
        _log(f"== gói {a.package} -> {moi}")
        if not a.dry_run:
            proj = _project(root)
            tep = _rope_rename(proj, a.package, None, moi)
            _log(f"  ({len(tep)} tệp)")
            _va_chuoi(root, a.package, moi, [], [])
            (root / a.package).mkdir(exist_ok=True)
            (root / a.package / "__init__.py").write_text(
                f'"""SHIM tạm (LOW-50): gói cũ của `{moi}/`."""\nimport sys as _sys\nimport {moi} as _new\n_sys.modules[__name__] = _new\n',
                encoding="utf-8")
        return 0 if a.dry_run or a.no_test or _kiem(root, py) else 1
    mods = a.modules or sorted(set(plan["defs"]) | set(plan["consts"]) | set(plan["modules"]))
    proj = None if a.dry_run else _project(root)
    for mod in mods:
        if not doi_mot_module(root, td, plan, mod, not a.no_module, a.dry_run, proj):
            return 1
        if not a.dry_run and not a.no_test and not _kiem(root, py):
            _log(f"DỪNG sau {mod} — sửa tay rồi chạy tiếp từ module kế.")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
