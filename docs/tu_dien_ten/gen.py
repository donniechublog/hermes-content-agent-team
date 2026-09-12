#!/usr/bin/env python3
"""gen.py — sinh lại TU_DIEN_TEN_nhap.md từ 4 tệp bên cạnh (cum.json / don.json /
moho.json / them.json) + repo hiện tại. KHÔNG đụng mã nguồn, chỉ đọc + in ra .md.

Vì sao có tệp này: đây là bước 0 của việc "đổi tên Việt không dấu -> English"
(feedback_dat_ten_english_cho_sau.md trong memory) — Ông Chủ duyệt bảng từ điển
trước, sửa cum.json/don.json/moho.json/them.json rồi CHẠY LẠI tệp này để bảng
B/C/D/E cập nhật theo, thay vì phải nhờ dựng lại từ đầu.

Dùng:
    cd docs/tu_dien_ten
    python3 gen.py .
"""
import ast
import collections
import json
import re
import sys
from pathlib import Path

S = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent
ROOT = S.parent.parent  # docs/tu_dien_ten/.. .. = gốc repo

# ---- quét repo: module .py trong mã chính (khong venv/hermes vendor/.claude/tests) ----
BO_QUA = {"venv", "hermes", ".claude", "tests", "__pycache__", "drafts", "state", "assets"}


def _mo_du(p: Path) -> bool:
    return not any(part in BO_QUA for part in p.relative_to(ROOT).parts[:-1])


files = sorted(p for p in ROOT.rglob("*.py") if _mo_du(p))

raw_mods, raw_defs, raw_consts = [], [], []
tok = collections.Counter()
where = collections.defaultdict(set)


def _them_tu(name: str, mod: str) -> None:
    for t in name.lower().split("_"):
        if t:
            tok[t] += 1
            where[t].add(mod)


for f in files:
    mod = str(f.relative_to(ROOT))[:-3].replace("/", ".")
    raw_mods.append(mod)
    for t in mod.split("."):
        _them_tu(t, mod)
    try:
        tree = ast.parse(f.read_text(encoding="utf-8"))
    except Exception as e:                                       # noqa: BLE001
        print(f"[gen] bỏ qua {f}: {type(e).__name__}", file=sys.stderr)
        continue
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            raw_defs.append((mod, n.name, "def", n.lineno))
            _them_tu(n.name, mod)
            for a in n.args.args + n.args.kwonlyargs:
                _them_tu(a.arg, mod)
        elif isinstance(n, ast.ClassDef):
            raw_defs.append((mod, n.name, "class", n.lineno))
            _them_tu(n.name, mod)
        elif isinstance(n, ast.Assign) and n.col_offset == 0:
            for t in n.targets:
                if isinstance(t, ast.Name) and re.fullmatch(r"[A-Z][A-Z0-9_]+", t.id):
                    raw_consts.append((mod, t.id))
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            _them_tu(n.id, mod)

CUM = json.load(open(S / "cum.json", encoding="utf-8"))
DON = json.load(open(S / "don.json", encoding="utf-8"))
MO_HO = json.load(open(S / "moho.json", encoding="utf-8"))
them = json.load(open(S / "them.json", encoding="utf-8"))
for k, v in them["DON"].items():
    (CUM if "_" in k else DON).setdefault(k, v)
PASS = set(them["PASS"])


def dich(name: str):
    """Việt-không-dấu -> (đề xuất English, {token mơ hồ cần chọn tay})."""
    parts = name.lower().split("_")
    out, flags, i = [], set(), 0
    while i < len(parts):
        hit = None
        for L in (4, 3, 2):
            k = "_".join(parts[i:i + L])
            if k in CUM:
                hit = (CUM[k], L)
                break
        if hit:
            out.append(hit[0])
            i += hit[1]
            continue
        p = parts[i]
        if p in MO_HO:
            flags.add(p)
        out.append(p if (p in PASS or p.isdigit()) else DON.get(p, f"?{p}"))
        i += 1
    return "_".join(out), flags


mods = sorted(set(raw_mods))
unmapped = collections.Counter()
L = [
    "# TỪ ĐIỂN TÊN — bản nháp bước 0 (chưa đụng mã)", "",
    f"Sinh tự động bởi `gen.py` từ repo hiện tại: {len(mods)} module, {len(raw_defs)} def/class "
    f"({len({d[1] for d in raw_defs})} tên khác nhau), {len(set(raw_consts))} hằng số. "
    "`?token` = chưa có trong bảng; ⚠️ = token mơ hồ, phải chọn tay theo nghĩa tại chỗ.", "",
    "Luật: rename 1-1 giữ cấu trúc cụm; khoá JSON trên đĩa KHÔNG đổi; tên vai "
    "(ethan/dre/kite…) giữ nguyên; token đã là English giữ nguyên. Sửa `cum.json` / "
    "`don.json` / `moho.json` / `them.json` rồi chạy lại `python3 gen.py .` để bảng dưới cập nhật.",
    "", "## A. Từ gốc — CỤM (khớp trước)", "", "| Việt | English |", "|---|---|",
]
L += [f"| `{k}` | `{v}` |" for k, v in sorted(CUM.items()) if "_" in k]
L += ["", "## A2. Từ gốc — TỪ ĐƠN", "", "| Việt | English | Mơ hồ |", "|---|---|---|"]
L += [f"| `{k}` | `{v}` | {('⚠️ ' + MO_HO[k]) if k in MO_HO else ''} |" for k, v in sorted(DON.items())]
L += ["", "## B. Module", "", "| Hiện tại | Đề xuất | Cờ |", "|---|---|---|"]
for m in mods:
    base = m.split(".")[-1]
    en = CUM.get(base)
    fl = set()
    if en is None:
        en, fl = dich(base)
    en = ("prepare." if m.startswith("chuan_bi.") else "") + en
    L.append(f"| `{m}` | `{en}` | {('⚠️ ' + ' '.join(sorted(fl))) if fl else ''} |")
L += ["", "## C. Hàm/lớp theo module", ""]
by = collections.defaultdict(list)
for mod, name, kind, ln in raw_defs:
    by[mod].append((name, kind, ln))
for mod in mods:
    if not by.get(mod):
        continue
    L += [f"### `{mod}`", "", "| Hiện tại | Đề xuất | Cờ |", "|---|---|---|"]
    seen = set()
    for name, kind, ln in sorted(by[mod], key=lambda x: x[2]):
        if name in seen or name.startswith("__") or name == "main":
            continue
        seen.add(name)
        lead = "_" if name.startswith("_") else ""
        core = name.lstrip("_")
        if kind == "class":
            snake = re.sub(r"(?<!^)(?=[A-Z])", "_", core).lower()
            en, fl = dich(snake)
            en = "".join(w.capitalize() for w in en.split("_"))
        else:
            en, fl = dich(core)
        for p in en.split("_"):
            if p.startswith("?"):
                unmapped[p[1:]] += 1
        L.append(f"| `{name}` | `{lead}{en}` | {('⚠️ ' + ' '.join(sorted(fl))) if fl else ''} |")
    L.append("")
L += ["## D. Hằng số module", "", "| Module | Hiện tại | Đề xuất | Cờ |", "|---|---|---|---|"]
for mod, c in sorted(set(raw_consts)):
    en, fl = dich(c.lower())
    en = en.upper()
    for p in en.split("_"):
        if p.startswith("?"):
            unmapped[p[1:].lower()] += 1
    L.append(f"| `{mod}` | `{c}` | `{en}` | {('⚠️ ' + ' '.join(sorted(fl))) if fl else ''} |")
L += ["", "## E. Token chưa có trong bảng", "", "| token | lần | ví dụ module |", "|---|---|---|"]
for t, n in unmapped.most_common():
    L.append(f"| `{t}` | {n} | {', '.join(sorted(where.get(t, []))[:3])} |")

out = S / "TU_DIEN_TEN_nhap.md"
out.write_text("\n".join(L), encoding="utf-8")
print(f"đã ghi {out} — {len(L)} dòng, {len(unmapped)} token chưa map ({sum(unmapped.values())} lượt)")
