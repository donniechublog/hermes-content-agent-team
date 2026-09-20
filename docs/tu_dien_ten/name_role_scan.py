#!/usr/bin/env python3
"""Ten nao dang dong NHIEU VAI cung luc — ham / tham so / bien / khoa (LOW-333).

Cong CI `tests/test_name_english.py` chi soi ten TOP-LEVEL; docstring cua no ghi
ro "Tham so/bien cuc bo khong xet". Tep nay soi dung phan con lai, va soi theo
mot cau hoi khac han cau hoi "dich ra chu gi":

    doc mot ten, co biet no dang la HAM hay BIEN hay TRUONG khong?

Ong Chu 20/09/2026: "Dich la gi ko quan trong, quan trong ko lan ham, bien,
truong." Vi du nang nhat tim duoc:

    browser_session.py:150   def dong(self)     -> DONG (close)
    21 tep khac              dong = [...]       -> DONG (line)

Cung chu, khac vai, nghia nguoc nhau. `docs/tu_dien_ten` da danh dau nhap nhang
cho nhom nay (`hang`, `nhan`, `ma`, `muc`, `khoa`, `so`, `dong`, `chu`, `mau`,
`bo`, `moi`, `cu`) — nen KHONG doi hang loat bang may, phai doc tung cho.

Dung:
    venv/bin/python docs/tu_dien_ten/name_role_scan.py            # nhom lan ham<->bien
    venv/bin/python docs/tu_dien_ten/name_role_scan.py --all      # moi ten dong >=2 vai
    venv/bin/python docs/tu_dien_ten/name_role_scan.py --name so  # mot ten, kem tep

Gioi han phep do (noi truoc de khong ai tuong con so la tuyet doi): chi dem
`ast.FunctionDef` (ten + tham so), `ast.Assign` vao `ast.Name`, va chuoi hang mot
tu. KHONG dem thuoc tinh (`x.dong`), khoa dict dong, hay ten trong f-string.
"""
import argparse
import ast
import collections
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
from tudien import TuDien                                     # noqa: E402

# Viet tat English / ten thu vien bi tu dien dich nham — kiem tay tung cai.
ENGLISH_SHORT = {
    "im", "ap", "src", "res", "ds", "sl", "cq", "wd", "tid", "hi", "t0", "t1",
    "fn", "kw", "mm", "px", "arg", "args", "ok", "url", "id", "ids", "img",
    "el", "cfg", "env", "buf", "tmp", "idx", "pid", "msg", "ret", "val",
}
ROLE_FUNCTION, ROLE_PARAM, ROLE_VAR, ROLE_CONST, ROLE_KEY = (
    "ham", "tham so", "bien", "hang", "khoa/chuoi")


def _dictionary() -> TuDien:
    return TuDien(HERE)


def is_vietnamese(name: str, td: TuDien) -> bool:
    core = (name or "").lstrip("_")
    if len(core) < 2 or core in ENGLISH_SHORT or core.startswith(("__", "test_")):
        return False
    try:
        en, _ = td.dich(core)
    except Exception:                                        # noqa: BLE001
        return False
    return bool(en) and not en.startswith("?") and en.lower() != core.lower()


def scan(include_tests: bool = False) -> tuple:
    """({ten: Counter(vai)}, {ten: {tep}}) tren cac tep git dang theo doi."""
    td = _dictionary()
    roles = collections.defaultdict(collections.Counter)
    files_of = collections.defaultdict(set)
    listed = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT,
                            capture_output=True, text=True).stdout.split()
    for rel in listed:
        if rel.startswith("docs/") or (not include_tests and rel.startswith("tests/")):
            continue
        try:
            tree = ast.parse((ROOT / rel).read_text(encoding="utf-8"))
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            found = []
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if is_vietnamese(node.name, td):
                    found.append((node.name.lstrip("_"), ROLE_FUNCTION))
                a = node.args
                found += [(x.arg.lstrip("_"), ROLE_PARAM)
                          for x in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs)
                          if is_vietnamese(x.arg, td)]
            elif isinstance(node, ast.Assign):
                found += [(t.id.lstrip("_"), ROLE_CONST if t.id.isupper() else ROLE_VAR)
                          for t in node.targets
                          if isinstance(t, ast.Name) and is_vietnamese(t.id, td)]
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                if " " not in node.value and is_vietnamese(node.value, td):
                    found.append((node.value, ROLE_KEY))
            for name, role in found:
                roles[name][role] += 1
                files_of[name].add(rel)
    return roles, files_of


def _rows(roles, files_of, only_function_clash: bool):
    out = []
    for name, by in roles.items():
        if len(by) < 2:
            continue
        if only_function_clash and not (by.get(ROLE_FUNCTION) and
                                        (by.get(ROLE_VAR) or by.get(ROLE_PARAM) or by.get(ROLE_KEY))):
            continue
        out.append((name, sum(by.values()), by, sorted(files_of[name])))
    return sorted(out, key=lambda r: -r[1])


def main() -> int:
    ap = argparse.ArgumentParser(description="Ten dong nhieu vai (LOW-333)")
    ap.add_argument("--all", action="store_true",
                    help="Moi ten dong >=2 vai, khong chi nhom lan ham<->bien")
    ap.add_argument("--name", help="Chi mot ten, in kem danh sach tep")
    ap.add_argument("--include-tests", action="store_true", help="Tinh ca tests/")
    a = ap.parse_args()

    roles, files_of = scan(a.include_tests)
    if a.name:
        by = roles.get(a.name)
        if not by:
            print(f"'{a.name}': khong thay (hoac tu dien coi la English)")
            return 0
        print(f"{a.name}: {sum(by.values())} cho, {len(files_of[a.name])} tep")
        for role, n in sorted(by.items(), key=lambda x: -x[1]):
            print(f"  {role:<12} {n}")
        for f in sorted(files_of[a.name]):
            print(f"    {f}")
        return 0

    rows = _rows(roles, files_of, only_function_clash=not a.all)
    print(f"{'ten':<16}{'cho':>5}{'tep':>5}  vai")
    print("-" * 74)
    for name, total, by, files in rows[:30]:
        detail = ", ".join(f"{k} {v}" for k, v in sorted(by.items(), key=lambda x: -x[1]))
        print(f"{name:<16}{total:>5}{len(files):>5}  {detail}")
    tong = sum(r[1] for r in rows)
    tep = len({f for r in rows for f in r[3]})
    nhom = "dong >=2 vai" if a.all else "vua la HAM vua la BIEN/TRUONG"
    print(f"\n{len(rows)} ten {nhom} — {tong} cho, {tep} tep"
          + ("" if a.include_tests else " (chi ma san xuat)"))
    return 0


if __name__ == "__main__":
    sys.exit(main())
