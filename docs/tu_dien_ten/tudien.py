#!/usr/bin/env python3
"""tudien.py — thư viện dùng chung của gen.py (sinh bảng) và rename.py (thực thi).

Một chỗ duy nhất biết: đọc 5 tệp JSON, tách tên theo cụm/từ đơn/PASS/override,
quét repo lấy module + def/class + hằng số. gen.py và rename.py chỉ gọi vào đây,
không chép lại (luật 07/09: gộp hàm trùng, không viết lại).
"""
import ast
import collections
import json
import re
from pathlib import Path

# Thu muc KHONG quet: vendor, moi truong, du lieu, tai lieu, worktree.
BO_QUA = {"venv", "hermes", ".claude", "tests", "__pycache__", "drafts", "state", "assets", "docs"}
# Ten Python giu nguyen, khong bao gio dich.
GIU_NGUYEN = {"__init__", "main"}


class TuDien:
    """5 tệp JSON đã nạp + phép dịch. `S` = thư mục docs/tu_dien_ten."""

    def __init__(self, S: Path):
        S = Path(S).resolve()
        self.S = S
        self.cum = json.load(open(S / "cum.json", encoding="utf-8"))
        self.don = json.load(open(S / "don.json", encoding="utf-8"))
        self.moho = json.load(open(S / "moho.json", encoding="utf-8"))
        them = json.load(open(S / "them.json", encoding="utf-8"))
        for k, v in them.get("DON", {}).items():          # tuong thich ban nhap
            (self.cum if "_" in k else self.don).setdefault(k, v)
        self.pass_ = set(them["PASS"])
        ov = S / "overrides.json"
        self.overrides = json.load(open(ov, encoding="utf-8")) if ov.exists() else {}
        # Moi token English ma CHINH tu dien sinh ra (gia tri cum/don/override)
        # cung la PASS: sau khi mot module da doi ten, gen.py quet lai thay
        # `writer_for`, `display_name`… — khong duoc bao "chua map" cai minh vua dat.
        for v in list(self.cum.values()) + list(self.don.values()) + list(self.overrides.values()):
            for t in re.split(r"[._]", re.sub(r"(?<!^)(?=[A-Z])", "_", v).lower()):
                if t:
                    self.pass_.add(t)

    def dich(self, name: str):
        """Việt-không-dấu -> (đề xuất English, {token mơ hồ}). Cụm 4→3→2 trước,
        rồi PASS (giữ), rồi từ đơn, rồi `?token` (chưa map)."""
        parts = name.lower().split("_")
        out, flags, i = [], set(), 0
        while i < len(parts):
            hit = None
            for L in (4, 3, 2):
                k = "_".join(parts[i:i + L])
                if k in self.cum:
                    hit = (self.cum[k], L)
                    break
            if hit:
                out.append(hit[0])
                i += hit[1]
                continue
            p = parts[i]
            if p in self.moho:
                flags.add(p)
            out.append(p if (p in self.pass_ or p.isdigit()) else self.don.get(p, f"?{p}"))
            i += 1
        return "_".join(out), flags

    def dich_ten(self, mod: str, name: str, kind: str):
        """Tên hàm/lớp/hằng -> (English, {cờ}). `overrides.json` theo `module.ten`
        thắng tuyệt đối. `kind`: def | class | const."""
        khoa = f"{mod}.{name}"
        if khoa in self.overrides:
            return self.overrides[khoa], set()
        if name in GIU_NGUYEN or name.startswith("__"):
            return name, set()
        lead = "_" if name.startswith("_") else ""
        core = name.lstrip("_")
        if kind == "class":
            snake = re.sub(r"(?<!^)(?=[A-Z])", "_", core).lower()
            en, fl = self.dich(snake)
            return "".join(w.capitalize() for w in en.split("_")), fl
        if kind == "const":
            en, fl = self.dich(core.lower())
            return lead + en.upper(), fl
        en, fl = self.dich(core)
        return lead + en, fl

    def dich_module(self, mod: str):
        """'chuan_bi.vong_bu' -> ('prepare.fallback_rounds', {cờ}). Tra theo tên
        tệp trong cum trước (cả tên module là một khoá), rồi mới tách token."""
        base = mod.split(".")[-1]
        if base in GIU_NGUYEN or base.startswith("__"):
            en, fl = base, set()
        elif base in self.cum:
            en, fl = self.cum[base], set()
        else:
            en, fl = self.dich(base)
        goi = mod.rsplit(".", 1)[0] if "." in mod else ""
        if goi:
            goi_en = self.cum.get(goi) or self.dich(goi)[0]
            return f"{goi_en}.{en}", fl
        return en, fl


def quet(ROOT: Path):
    """Quét repo: (mods, defs, consts, where).
    defs   = [(mod, name, kind, lineno)] — MỌI def/class (kể cả nested, để in bảng)
    consts = {(mod, NAME)} — gán ở cột 0, tên CHỮ_HOA
    top    = {mod: [(name, kind)]} — CHỈ top-level (thứ dùng để rename + kiểm va chạm)
    where  = {token: {mod}} — để mục E chỉ ra token nằm ở đâu"""
    ROOT = Path(ROOT).resolve()
    files = sorted(p for p in ROOT.rglob("*.py")
                   if not any(part in BO_QUA for part in p.relative_to(ROOT).parts[:-1]))
    mods, defs, consts, top = [], [], set(), collections.defaultdict(list)
    where = collections.defaultdict(set)

    def _them_tu(name, mod):
        for t in name.lower().split("_"):
            if t:
                where[t].add(mod)

    for f in files:
        mod = str(f.relative_to(ROOT))[:-3].replace("/", ".")
        src = f.read_text(encoding="utf-8")
        if src.startswith('"""SHIM tạm (LOW-50)'):       # tên cũ đã đổi: không phải module thật
            continue
        mods.append(mod)
        for t in mod.split("."):
            _them_tu(t, mod)
        try:
            tree = ast.parse(src)
        except Exception:                                    # noqa: BLE001
            continue
        for n in tree.body:
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                top[mod].append((n.name, "class" if isinstance(n, ast.ClassDef) else "def"))
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defs.append((mod, n.name, "def", n.lineno))
                _them_tu(n.name, mod)
                for a in n.args.args + n.args.kwonlyargs:
                    _them_tu(a.arg, mod)
            elif isinstance(n, ast.ClassDef):
                defs.append((mod, n.name, "class", n.lineno))
                _them_tu(n.name, mod)
            elif isinstance(n, ast.Assign) and n.col_offset == 0:
                for t in n.targets:
                    if isinstance(t, ast.Name) and re.fullmatch(r"[A-Z][A-Z0-9_]+", t.id):
                        consts.add((mod, t.id))
            elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                _them_tu(n.id, mod)
    return sorted(set(mods)), defs, consts, top, where, files


def va_cham(td: TuDien, top: dict) -> dict:
    """{mod: {ten_en: [ten_goc,...]}} — hai def/class top-level cùng module dịch
    ra cùng tên. Rỗng = an toàn để rename."""
    ra = {}
    for mod, items in top.items():
        en_names = collections.defaultdict(list)
        for name, kind in items:
            if name in GIU_NGUYEN or name.startswith("__"):
                continue
            en, _ = td.dich_ten(mod, name, kind)
            en_names[en].append(name)
        dup = {en: o for en, o in en_names.items() if len(o) > 1}
        if dup:
            ra[mod] = dup
    return ra


def va_cham_module(td: TuDien, ROOT: Path, mods: list) -> dict:
    """Tên module MỚI trùng với một tên đã dùng ở bất kỳ tệp nào (kể cả tests):
    biến cục bộ, tham số, def/class, alias import — sau rename, tên đó SHADOW
    module → UnboundLocalError/pyflakes đỏ. Ca thật (pilot 13/09/2026):
    test_vai.py có `role = sorted(...)` trong hàm đang dùng `role.ROLE`.
    Trả {ten_moi: [(tệp, dòng, loại, tên_module_cũ)]}. Rỗng = an toàn."""
    ROOT = Path(ROOT).resolve()
    files = [p for p in ROOT.rglob("*.py")
             if not any(part in (BO_QUA - {"tests"}) for part in p.relative_to(ROOT).parts[:-1])]
    trees = {}
    for f in files:
        try:
            trees[str(f.relative_to(ROOT))] = ast.parse(f.read_text(encoding="utf-8"))
        except Exception:                                    # noqa: BLE001
            pass
    # Ten module con (trong goi) chi thanh TEN TRAN khi co ai `from goi import con`
    # hoac `import goi.con as con` — khong ai lam vay thi khong shadow duoc gi.
    ten_tran_goi = set()
    for tree in trees.values():
        for n in ast.walk(tree):
            if isinstance(n, ast.ImportFrom) and n.module:
                for a in n.names:
                    ten_tran_goi.add((n.module, a.asname or a.name))
            elif isinstance(n, ast.Import):
                for a in n.names:
                    if "." in a.name and a.asname:
                        ten_tran_goi.add((a.name.rsplit(".", 1)[0], a.asname))
    moi = {}
    for mod in mods:
        base_cu = mod.split(".")[-1]
        if base_cu in GIU_NGUYEN or base_cu.startswith("__"):
            continue
        en, _ = td.dich_module(mod)
        if en == mod:
            continue
        base = en.split(".")[-1]
        if base == base_cu:                                  # chi doi goi, ten tran khong doi
            continue
        if "." in mod:                                       # module con: chi khi bi import tran
            goi = mod.rsplit(".", 1)[0]
            goi_en = en.rsplit(".", 1)[0]
            if not any(g in (goi, goi_en) and b in (base_cu, base) for g, b in ten_tran_goi):
                continue
        moi.setdefault(base, []).append(mod)
    if not moi:
        return {}
    # module mới trùng module CŨ còn tồn tại (không phải chính nó)
    ra = collections.defaultdict(list)
    co_san = {m.split(".")[-1] for m in mods}
    for base, goc in moi.items():
        for m in mods:
            if m.split(".")[-1] == base and m not in goc:
                ra[base].append((m.replace(".", "/") + ".py", 0, "module", ",".join(goc)))
    for rel, tree in trees.items():
        # Chi tep NAO IMPORT module do moi co the bi shadow — tep khac dat ten
        # bien `role` ma khong import `role` thi khong sao.
        nhap = set()
        for n in ast.walk(tree):
            if isinstance(n, ast.Import):
                nhap.update(a.name for a in n.names)
            elif isinstance(n, ast.ImportFrom) and n.module:
                nhap.add(n.module)
                nhap.update(f"{n.module}.{a.name}" for a in n.names)
        lien_quan = {base for base, goc in moi.items()
                     if any(m in nhap or td.dich_module(m)[0] in nhap for m in goc)}
        if not lien_quan:
            continue
        for n in ast.walk(tree):
            ten, loai = None, None
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
                ten, loai = n.id, "biến"
            elif isinstance(n, ast.arg):
                ten, loai = n.arg, "tham số"
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                ten, loai = n.name, "def/class"
            elif isinstance(n, ast.alias):
                ten, loai = (n.asname or n.name.split(".")[0]), "import"
            if ten in lien_quan and rel != moi[ten][0].replace(".", "/") + ".py":
                # import chính module đó thì là mong đợi, không phải va chạm
                if loai == "import" and ten in co_san:
                    continue
                ra[ten].append((rel, getattr(n, "lineno", 0), loai, ",".join(moi[ten])))
    return dict(ra)


def bang_doi_ten(td: TuDien, ROOT: Path) -> dict:
    """Toàn bộ kế hoạch rename cho rename.py:
    {"modules": {mod: mod_en}, "defs": {mod: [(old, new, kind)]},
     "consts": {mod: [(old, new)]}} — chỉ ghi những cái THỰC SỰ đổi."""
    mods, _defs, consts, top, _where, _files = quet(ROOT)
    plan = {"modules": {}, "defs": collections.defaultdict(list), "consts": collections.defaultdict(list)}
    for mod in mods:
        en, _ = td.dich_module(mod)
        if en != mod:
            plan["modules"][mod] = en
        for name, kind in top.get(mod, []):
            new, _ = td.dich_ten(mod, name, kind)
            if new != name and "?" not in new:
                plan["defs"][mod].append((name, new, kind))
    for mod, c in sorted(consts):
        new, _ = td.dich_ten(mod, c, "const")
        if new != c and "?" not in new:
            plan["consts"][mod].append((c, new))
    plan["defs"] = dict(plan["defs"])
    plan["consts"] = dict(plan["consts"])
    return plan
