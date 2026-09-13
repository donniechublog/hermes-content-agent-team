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


# Hai module rope.patchedast KHONG parse duoc (13/09/2026, do bang
# scratchpad/do_patchedast.py: 195 tep, 2 hong — f-string noi ngam co `{{`/ky tu
# ngoai ASCII lam patchedast do sai do dai chuoi, sua tung cho thi no hong cho
# khac). Chung bi loai khoi rope hoan toan; ten trong/ngoai hai tep nay doi bang
# TOKEN (tokenize) — chinh xac o muc NAME token, khong dung chuoi/chu thich.
NGOAI_ROPE = {"render_edu", "scan_models"}


# ---- rope ------------------------------------------------------------------
def _project(root: Path):
    from rope.base.project import Project
    return Project(str(root), ropefolder=None, save_objectdb=False,
                   ignored_resources=["venv", "hermes", ".claude", "__pycache__", "drafts",
                                      "state", "assets", "docs", ".git", "*.pyc",
                                      *[f"{m}.py" for m in NGOAI_ROPE]])


# ---- doi ten bang TOKEN (cho tep ngoai rope) ------------------------------------
def _doi_token(path: Path, quy_tac) -> int:
    """Viet lai tep theo NAME token: `quy_tac(pp, p, tok, nx) -> ten_moi | None`
    (pp = token truoc-truoc, p = token truoc, nx = token sau). Chi cham token
    NAME, nen chuoi/chu thich/khoa dict nguyen ven. Tra so lan doi."""
    src = path.read_text(encoding="utf-8")
    try:
        toks = list(tokenize.generate_tokens(iter(src.splitlines(True)).__next__))
    except (tokenize.TokenError, SyntaxError):
        return 0
    lines = src.splitlines(True)
    n = 0
    for i in range(len(toks) - 1, -1, -1):
        t = toks[i]
        if t.type != tokenize.NAME:
            continue
        moi = quy_tac(toks[i - 2] if i > 1 else None, toks[i - 1] if i else None, t,
                      toks[i + 1] if i + 1 < len(toks) else None)
        if not moi or moi == t.string:
            continue
        (r, c0), c1 = t.start, t.end[1]
        line = lines[r - 1]
        lines[r - 1] = line[:c0] + moi + line[c1:]
        n += 1
    if n:
        path.write_text("".join(lines), encoding="utf-8")
    return n


def _tep_ngoai_rope(root: Path) -> list:
    return [root / f"{m}.py" for m in NGOAI_ROPE if (root / f"{m}.py").exists()]


def _va_ngoai_rope_ten(root: Path, mod: str, old: str, new: str) -> int:
    """Sau MOI rope rename (mod, old->new): trong cac tep ngoai rope, `mod.old` -> `mod.new`
    (hai tep nay chi dung `import mod` + `mod.ten`, do 13/09)."""
    alias = mod.split(".")[-1]
    n = 0
    for f in _tep_ngoai_rope(root):
        if alias not in f.read_text(encoding="utf-8"):
            continue
        n += _doi_token(f, lambda pp, p, t, nx: new if _la_thuoc_tinh(pp, p, t, alias, old) else None)
    return n


def _la_thuoc_tinh(pp, p, t, alias: str, old: str) -> bool:
    """`alias.old` — token truoc la `.`, truoc nua la NAME == alias."""
    return (t.string == old and p is not None and p.string == "." and pp is not None
            and pp.type == tokenize.NAME and pp.string == alias)


def _va_ngoai_rope_module(root: Path, mod: str, base_moi: str) -> int:
    """Sau rope doi TEN TEP mod -> base_moi: trong tep ngoai rope, `import mod` va
    `mod.` -> ten moi."""
    base_cu = mod.split(".")[-1]
    n = 0
    for f in _tep_ngoai_rope(root):
        if base_cu not in f.read_text(encoding="utf-8"):
            continue
        n += _doi_token(f, lambda pp, p, t, nx: base_moi if (t.string == base_cu and
                                                           ((p and p.string in ("import", "from")) or
                                                            (nx and nx.string == "."))) else None)
    return n


def _doi_module_ngoai_rope(root: Path, mod: str, defs: list, consts: list) -> None:
    """Module KHONG qua rope: doi dinh nghia + moi tham chieu bang token.
    Trong tep: moi NAME == old (khong phai sau dau `.` cua module khac).
    Ngoai tep (.py chinh + tests): `mod.old` -> `mod.new`, va ten trong
    `from mod import ...` (cung dong)."""
    bang = {o: nw for o, nw, _k in defs}
    bang.update({o: nw for o, nw in consts})
    if not bang:
        return
    f = root / f"{mod}.py"
    k = _doi_token(f, lambda pp, p, t, nx: bang.get(t.string) if not (p and p.string == ".") else None)
    _log(f"  {mod} (token, trong tệp): {k} chỗ")
    k2 = 0
    for g in list(root.glob("*.py")) + list(root.glob("chuan_bi/*.py")) + list(root.glob("tests/*.py")):
        if g == f or mod not in g.read_text(encoding="utf-8"):
            continue
        src = g.read_text(encoding="utf-8")
        tu_import = set()
        for m in re.finditer(rf"^\s*from {re.escape(mod)} import ([^\n]+)", src, re.M):
            tu_import |= {x.strip().split(" as ")[0] for x in m.group(1).strip("()").split(",")}
        k2 += _doi_token(g, lambda pp, p, t, nx, tu=tu_import: bang.get(t.string)
                         if (t.string in bang and (_la_thuoc_tinh(pp, p, t, mod, t.string)
                                                  or t.string in tu)) else None)
    _log(f"  {mod} (token, tệp khác): {k2} chỗ")


def _rope_rename(proj, res_path: str, offset, new_name: str) -> list:
    """Một lần rename qua rope. Trả danh sách tệp đã đổi.

    `validate()` TRƯỚC mỗi lần: rope cache nội dung tệp; bước vá chuỗi ở đây ghi
    thẳng ra đĩa, nên nếu không đồng bộ lại thì lần rename sau tính offset trên
    bản cũ và chèn tên mới lệch chỗ (lô 1, 13/09/2026: `cu =count_attempt_redom_lai`
    trong test_cong_chan.py → SyntaxError). Kèm Project mới cho mỗi module."""
    from rope.refactor.rename import Rename
    proj.validate(proj.root)
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
BANG_TOAN_CUC = {}          # old -> new, mọi module (main() nạp từ plan)


def _modules_re_export(root: Path, mod_full: str, new: str) -> set:
    """Cac module M co `from <mod_full> import … new …` (sau rope) — chung
    RE-EXPORT ten do (image_prepare re-export _luu_crop cua chuan_bi.tai_loc;
    vong_bu re-export tai_va_loc). Tra ten base cua M."""
    ra = set()
    for f in list(root.glob("*.py")) + list(root.glob("chuan_bi/*.py")):
        s = f.read_text(encoding="utf-8")
        if re.search(rf"^\s*from\s+{re.escape(mod_full)}\s+import\s*\(?[^\n]*\b{re.escape(new)}\b", s, re.M) or \
           re.search(rf"^\s*from\s+{re.escape(mod_full)}\s+import\s*\((?:[^)]*\n)*?[^)]*\b{re.escape(new)}\b", s, re.M):
            ra.add(f.stem)
    return ra


def _va_re_export(root: Path, mod_full: str, old: str, new: str) -> int:
    """rope KHONG doi `cb._luu_crop` khi cb la module RE-EXPORT (`from chuan_bi.tai_loc
    import _luu_crop` trong image_prepare) — lo 2: test_cong_chan goi
    image_prepare._luu_crop/mo_ta_anh. Doi bang token: NAME==old, truoc la `.`,
    truoc nua la alias cua mot module re-export (trong tep do: `import M [as a]`,
    `from pkg import M [as a]`)."""
    Ms = _modules_re_export(root, mod_full, new)
    if not Ms:
        return 0
    n = 0
    for f in list(root.glob("*.py")) + list(root.glob("chuan_bi/*.py")) + list(root.glob("tests/*.py")):
        s = f.read_text(encoding="utf-8")
        if old not in s:
            continue
        alias = _alias_module(s, Ms)
        if not any(re.search(rf"^\s*(?:import|from)\b.*\b{re.escape(M)}\b", s, re.M) for M in Ms):
            continue                          # tep khong import module re-export nao
        n += _doi_token(f, lambda pp, p, t, nx, al=alias: new if (t.string == old and p is not None
                                                                   and p.string == "." and pp is not None
                                                                   and pp.string in al) else None)
    return n


BANG_MODULE = {}            # base cũ -> base mới của MỌI module đã/đang đổi (import cục bộ còn tên cũ)


def _va_import_cu(root: Path, cu_full: str, moi_full: str) -> int:
    """rope bo sot `import <cũ>` NAM TRONG HAM (test_cong_chan: `import anh_chuan_bi
    as cb` o 3 ham, lo 1) — chay duoc nho shim nhung patch.object/alias khong con
    nhan ra module. Doi bang token trong moi tep co cau import tro toi ten cu:
    NAME==base_cu khong sau dau cham (`import cũ`, `from chuan_bi import cũ`, `cũ.x`),
    hoac sau `.` ma truoc nua la ten goi (`chuan_bi.cũ`)."""
    cu_b, moi_b = cu_full.split(".")[-1], moi_full.split(".")[-1]
    goi = cu_full.split(".")[0] if "." in cu_full else None
    if cu_b == moi_b:
        return 0
    n = 0
    for f in list(root.glob("*.py")) + list(root.glob("chuan_bi/*.py")) + list(root.glob("tests/*.py")):
        if f.stem == cu_b:                                   # chinh shim
            continue
        s = f.read_text(encoding="utf-8")
        # Chi xet PHAN MA cua dong import (bo chu thich: test_phien_browser co
        # `from tam import x  # runner chung` + bien `with … as chung` -> doi nham).
        dong = s.splitlines()
        cau_import = [re.sub(r"#.*", "", d) for d in dong if re.match(r"\s*(?:import|from)\b", d)]
        if not any(re.search(rf"\b{re.escape(cu_b)}\b", d) for d in cau_import):
            continue
        # Ten TRAN `cũ` chi duoc coi la module khi co import RANG BUOC ten do
        # (`import cũ`, `from goi import cũ` — khong `as`); con lai chi doi trong cau import.
        rang_buoc = False
        for d in cau_import:
            m = (re.match(r"\s*import\s+(.*)$", d) if not goi
                 else re.match(rf"\s*from\s+{re.escape(goi)}\s+import\s+\(?(.*?)\)?\s*$", d))
            if m and any(p.strip() == cu_b for p in m.group(1).split(",")):
                rang_buoc = True

        def _qt(pp, p, t, nx):
            # Chi dung import hoac dung `cũ.x` — KHONG dung tham so/kwarg trung ten
            # (`vai="ethan"` la NAME token nhung khong phai module).
            if t.string != cu_b:
                return None
            la_import = re.match(r"\s*(?:import|from)\b", dong[t.start[0] - 1]) is not None
            if not la_import and not (rang_buoc and nx is not None and nx.string == "."):
                return None
            if p is None or p.string != ".":
                return moi_b
            if goi and pp is not None and pp.string == goi:
                return moi_b
            return None
        n += _doi_token(f, _qt)
    return n


def _khoa_dict_thuan(root: Path) -> set:
    """Chi cac khoa dict/JSON that (m["x"], .get("x"), "x":), KHONG gom ten module —
    dung de quyet doi `"ten_module_cu"` tran trong tests (lo 2: task body co
    "tim_anh_them" tran, test soi `kt.index("tim_anh_them")`)."""
    pat = re.compile(r'\[\s*["\']([A-Za-z_][\w]*)["\']\s*\]|\.get\(\s*["\']([A-Za-z_][\w]*)["\']|["\']([A-Za-z_][\w]*)["\']\s*:')
    ra = set()
    for f in list(root.glob("*.py")) + list(root.glob("chuan_bi/*.py")):
        for m in pat.finditer(f.read_text(encoding="utf-8")):
            ra.add(next(g for g in m.groups() if g))
    ra |= {p.name for p in root.iterdir() if p.is_dir()}      # ten thu muc = duong dan tren dia
    return ra


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
    # Ten MODULE/GOI/THU MUC cung la chuoi tren dia (`ROOT / "chuan_bi" / "nhin.py"`,
    # `state/<brand>/chuan_bi/`): lo 1 doi `"chuan_bi"` -> `"prepare_article"` vi
    # ham `chuan_bi` trong anh_chuan_bi trung ten goi. Khong bao gio doi ten tran nay.
    for p in list(root.glob("*.py")) + list(root.glob("*/")) + list(root.glob("*/*.py")):
        ra.add(p.stem)
    ra |= {"state", "drafts", "assets", "tests", "hermes", "docs"}
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
    fmid = getattr(tokenize, "FSTRING_MIDDLE", None)     # Python >= 3.12: f-string tach token
    # duyệt ngược để offset không trôi
    for t in reversed(toks):
        if t.type == fmid:
            # Phan chu cua f-string (dre_chuan_bi: f"… tim_anh_them.py {id}" — lo 2 bo sot).
            # Vi tri token sai khi co `{{`/`}}` (cpython#104825): chi doi khi lat cat
            # tren dong khop dung chuoi token, khong thi bo qua.
            (r0, c0), (r1, c1) = t.start, t.end
            if r0 != r1 or lines[r0 - 1][c0:c1] != t.string:
                continue
            moi = t.string
            for pat, rep in thay:
                moi, k = re.subn(pat, rep, moi)
                n += k
            if moi != t.string:
                lines[r0 - 1] = lines[r0 - 1][:c0] + moi + lines[r0 - 1][c1:]
            continue
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


def _alias_module(src: str, ten_mod: set) -> set:
    """Moi ten ma tep `src` dung de tro toi mot trong cac module `ten_mod` (ten base):
    chinh ten do, `import X as Y`, `from pkg import X [as Y]` (lo 2:
    patch.object(vong_bu, "tai_va_loc") khong duoc doi vi chi biet `import X as Y`)."""
    alias = set(ten_mod)
    # Ten CU cua module (import cuc bo rope bo sot, xem _va_import_cu) cung la alias.
    ten_mod = set(ten_mod) | {cu for cu, moi in BANG_MODULE.items() if moi in ten_mod}
    alias |= ten_mod
    for M in ten_mod:
        for m in re.finditer(rf"^\s*import\s+(?:[\w.]+\.)?{re.escape(M)}(?:\s+as\s+(\w+))?\s*(?:#.*)?$", src, re.M):
            if m.group(1):
                alias.add(m.group(1))
        for m in re.finditer(rf"^\s*from\s+[\w.]+\s+import\s+([^\n]*\b{re.escape(M)}\b[^\n]*)", src, re.M):
            for phan in m.group(1).split(","):
                ten = phan.strip().split(" as ")
                if ten[0].strip() == M:
                    alias.add(ten[-1].strip())
    return alias


def _thay_dong(src: str, thay_dong: list, mc: str, mm: str):
    """Ap cac mau co ngu canh (patch.object(X, "cũ")…) khi X tro dung module nay
    (hoac mot module RE-EXPORT ten do — phan tu thu 3 cua moi mau): thanh phan
    CUOI cua X (sau dau cham cuoi) phai la ten module cu/moi hoac alias cua no
    trong chinh tep test. Tra (src_moi, so_lan)."""
    n = 0
    for pat, new, them in thay_dong:
        alias = _alias_module(src, {mc, mm} | set(them))

        def _rep(m, new=new, alias=alias):
            nonlocal n
            muc_tieu = m.group(2).split(".")[-1] if m.group(2) else ""
            if muc_tieu not in alias:
                return m.group(0)
            n += 1
            return m.group(1) + new
        src = re.sub(pat, _rep, src)
    return src, n


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
    # Ten thuoc tinh trong chuoi cua patch/setattr/getattr: rope khong doi
    # (`mock.patch.object(la, "dem_mat")`, `patch("image_rules.dem_mat")`) —
    # test_anh_roi/test_bao_ve_tu_khoa lo 1 do vi the. Ap cho MOI test, khong
    # can gate read_text, vi ngu canh da noi ro day la ten thuoc tinh.
    # Mau CO NGU CANH (patch.object(la, "cũ") …) phai chay tren CA DONG, khong phai
    # tren rieng token chuoi — token chuoi chi la `"cũ"`, khong chua `patch.object(`.
    thay_dong = []
    mod_hien = mod_moi or mod_cu             # duong dan module SAU rope (import da doi theo)
    for old, new, _kind in defs:
        thay.append((rf"(?<![\w.])def {re.escape(old)}(?![\w])", f"def {new}"))   # cả "def cũ" không ngoặc
        thay.append((rf"(?<![\w\\]){re.escape(old)}(?=\\?\()", new))    # cả `nc.cũ(` (alias)
        thay.append((rf"(?<![\w]){re.escape(mc)}(\\?\.){re.escape(old)}\b", rf"{mm}\g<1>{new}"))
        # Doi tuong cua patch.object/setattr PHAI la chinh module nay (hoac alias
        # cua no trong tep test) — `nap` co o ca nop_chung lan env_load; lo 1 doi
        # `patch.object(nhin.env_load, "nap")` thanh "load_draft_context" (ten cua
        # nop_chung.nap) vi khong nhin doi tuong. Kiem bang callable, xem _thay_dong.
        # Module RE-EXPORT ten nay (vong_bu re-export tai_va_loc) cung la doi tuong hop le.
        re_exp = _modules_re_export(root, mod_hien, new)
        thay_dong.append((rf"((?:patch\.object|setattr|getattr|hasattr|monkeypatch\.setattr)\(\s*([\w.]+)\s*,\s*[\"']){re.escape(old)}(?=[\"'])", new, re_exp))
        thay_dong.append((rf"(patch\([\"']([\w.]*)\.){re.escape(old)}(?=[\"'])", new, re_exp))
    hang_tran = []
    for old, new, _kind in defs:
        # Ten ham NHIEU TU (`_vong_thuc_the`) dung tran o cuoi chuoi soi nguon
        # (`= _vong_thuc_the"` — khong co ngoac): doi trong test soi nguon.
        if "_" in old.strip("_"):
            hang_tran.append((rf"(?<![\w$]){re.escape(old)}(?![\w])", new))
    for old, new in consts:
        # `$` loại trừ biến shell trong chuỗi test ("$VAI" của quet_daily_scan.sh
        # không phải hằng Python — pilot 13/09 đã đổi nhầm thành "$ROLE").
        # Hang MOT TU (CAO, NGUON, RONG) la chu tieng Viet thuong gap trong chuoi
        # ("BAO CAO BI CAT", "NGUON KHONG LAY DUOC", JS `Y0+CAO`) — lo 2 doi bua
        # lam test_bang_nova/test_render_edu do. Chi doi tran khi ten co `_`,
        # va chi trong test SOI NGUON; con lai phai co `mod.` phia truoc.
        if "_" in old:
            hang_tran.append((rf"(?<![\w.$]){re.escape(old)}\b", new))
        thay.append((rf"(?<![\w]){re.escape(mc)}(\\?\.){re.escape(old)}\b", rf"{mm}\g<1>{new}"))
        re_exp = _modules_re_export(root, mod_hien, new)
        thay_dong.append((rf"((?:patch\.object|setattr|getattr|hasattr|monkeypatch\.setattr)\(\s*([\w.]+)\s*,\s*[\"']){re.escape(old)}(?=[\"'])", new, re_exp))
        thay_dong.append((rf"(patch\([\"']([\w.]*)\.){re.escape(old)}(?=[\"'])", new, re_exp))
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
    tran += hang_tran
    bo = [o for o, _n, _k in defs if o in khoa_json] + [o for o, _n in consts if o in khoa_json]
    if bo:
        _log(f"  (không thay tên trần trong chuỗi vì trùng khoá dict: {', '.join(bo)})")
    # Ten MODULE tran trong tests ("tim_anh_them" trong task body) — chi khi khong
    # phai khoa dict that / ten thu muc (khoa tren dia).
    if mod_moi and mc != mm:
        if mc in _khoa_dict_thuan(root):
            _log(f"  (không thay tên module trần \"{mc}\" trong tests: trùng khoá dict/thư mục)")
        else:
            tran.append((rf'(["\']){re.escape(mc)}\1', rf"\g<1>{mm}\g<1>"))
    if thay or tran or thay_dong:
        k2 = 0
        for f in root.glob("tests/*.py"):
            k2 += _thay_trong_chuoi_py(f, thay)
            src = f.read_text(encoding="utf-8")
            # Test soi NGUON (read_text/ast) hoac soi THAN TASK (task_bodies -> chuoi
            # co ten module/ham) moi duoc doi ten tran.
            if tran and ("read_text(" in src or "ast.parse" in src or "_ten_ham_trong" in src
                         or "task_bodies" in src or "than_task" in src):
                k2 += _thay_trong_chuoi_py(f, tran)
            src = f.read_text(encoding="utf-8")
            moi_src, kk = _thay_dong(src, thay_dong, mc, mm)
            k2 += kk
            if moi_src != src:
                f.write_text(moi_src, encoding="utf-8")
        if k2:
            _log(f"  chuỗi trong tests (def/gọi/hằng): {k2} chỗ")
        tong += k2
    # (3) MỌI `__all__` trong mã chính: một mục "cũ" mà tệp không còn bind tên đó
    # (đã bị rope đổi — định nghĩa tại chỗ HOẶC tên re-export từ module khác như
    # image_prepare re-export chuan_bi.manifest.bang_anh) thì đổi theo bảng toàn
    # cục. Tìm ĐÚNG câu `^__all__ = [` (lô 1: s.index trúng chú thích phía trên).
    bang = dict(BANG_TOAN_CUC)
    bang.update({o: n for o, n, _k in defs})
    bang.update(dict(consts))
    for mod_path in list(root.glob("*.py")) + list(root.glob("chuan_bi/*.py")):
        s = mod_path.read_text(encoding="utf-8")
        m_all = re.search(r"^__all__\s*=\s*\[", s, re.M)
        if not m_all:
            continue
        a, b = m_all.start(), s.index("]", m_all.end())
        khoi = s[a:b]
        # Ten con "bind" trong tep = xuat hien nhu NAME token NGOAI khoi __all__
        # (khong tinh chuoi: `wd / "bang_anh.png"` van con chu bang_anh trong
        # chuoi sau khi ham bang_anh da thanh contact_sheet).
        try:
            ten_bind = {t.string for t in tokenize.generate_tokens(iter((s[:a] + s[b:]).splitlines(True)).__next__)
                        if t.type == tokenize.NAME}
        except (tokenize.TokenError, SyntaxError):
            ten_bind = set(re.findall(r"[A-Za-z_]\w*", s[:a] + s[b:]))
        moi = khoi
        for old, new in bang.items():
            if f'"{old}"' in moi and old not in ten_bind:
                moi = moi.replace(f'"{old}"', f'"{new}"')
        if moi != khoi:
            mod_path.write_text(s[:a] + moi + s[b:], encoding="utf-8")
            _log(f"  __all__ của {mod_path.name} cập nhật")
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
    if mod in NGOAI_ROPE:                     # render_edu / scan_models: token, khong rope
        _doi_module_ngoai_rope(root, mod, defs, consts)
        _va_chuoi(root, mod, None, defs, consts)
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
        k = _va_ngoai_rope_ten(root, mod, old, new) + _va_re_export(root, mod, old, new)
        _log(f"  {old} -> {new}  ({len(tep)} tệp{f', +{k} ngoài rope' if k else ''})")
    # 2) hằng số
    for old, new in consts:
        text = (root / res_path).read_text(encoding="utf-8")
        off = _offset_def(text, old, "const")
        if off is None:
            _log(f"  !! không tìm thấy hằng {old} — bỏ qua")
            continue
        tep = _rope_rename(proj, res_path, off, new)
        k = _va_ngoai_rope_ten(root, mod, old, new) + _va_re_export(root, mod, old, new)
        _log(f"  {old} -> {new}  ({len(tep)} tệp{f', +{k} ngoài rope' if k else ''})")
    # 3) tên tệp module (chỉ tên tệp, không đổi thư mục gói ở đây)
    if mod_moi:
        base_moi = mod_moi.split(".")[-1]
        tep = _rope_rename(proj, res_path, None, base_moi)
        k = _va_ngoai_rope_module(root, mod, base_moi)
        _log(f"  module {mod} -> {base_moi}  ({len(tep)} tệp{f', +{k} ngoài rope' if k else ''})")
        res_path_moi = "/".join(mod.split(".")[:-1] + [base_moi]) + ".py"
        BANG_MODULE[mod.split(".")[-1]] = base_moi
        k = _va_import_cu(root, mod, ".".join(mod.split(".")[:-1] + [base_moi]))
        if k:
            _log(f"  import cục bộ còn tên cũ: {k} chỗ")
        _va_chuoi(root, mod, ".".join(mod.split(".")[:-1] + [base_moi]), defs, consts)
        shim = root / res_path
        if not shim.exists():
            # Module con trong goi: import theo duong DAY DU (chuan_bi.vision), khong
            # phai ten tran `vision` — lo 2: shim chuan_bi/nhin.py `import vision`
            # -> ModuleNotFoundError o moi tep con import ten cu.
            new_full = ".".join(mod.split(".")[:-1] + [base_moi])
            shim.write_text(SHIM.format(old=mod.split(".")[-1], new=new_full), encoding="utf-8")
            _log(f"  shim {shim.name} -> {new_full}")
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
    # Bảng toàn cục cũ->mới (mọi module) cho bước vá `__all__` re-export.
    for _m, ds in plan["defs"].items():
        BANG_TOAN_CUC.update({o: n for o, n, _k in ds})
    for _m, cs in plan["consts"].items():
        BANG_TOAN_CUC.update(dict(cs))
    # Module da doi o lo truoc: shim `<cũ>.py` ghi "tên cũ của `<mới>.py`".
    for shim in list(root.glob("*.py")) + list(root.glob("chuan_bi/*.py")):
        m = re.match(r'"""SHIM tạm \(LOW-50\): tên cũ của `(\w+)\.py`', shim.read_text(encoding="utf-8"))
        if m:
            BANG_MODULE[shim.stem] = m.group(1)
    py =str(root / "venv/bin/python") if (root / "venv/bin/python").exists() else sys.executable
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
    for mod in mods:
        # Project MỚI mỗi module: bước vá chuỗi/shim của module trước ghi thẳng ra
        # đĩa ngoài rope — không được để rope mang cache cũ sang module sau.
        proj = None if a.dry_run else _project(root)
        if not doi_mot_module(root, td, plan, mod, not a.no_module, a.dry_run, proj):
            return 1
        if proj is not None:
            proj.close()
        if not a.dry_run and not a.no_test and not _kiem(root, py):
            _log(f"DỪNG sau {mod} — sửa tay rồi chạy tiếp từ module kế.")
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
