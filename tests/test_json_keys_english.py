#!/usr/bin/env python3
"""Cổng chặn KHOÁ JSON/dict và ĐOẠN ĐƯỜNG DẪN tiếng Việt không dấu MỚI (LOW-229).

`test_name_english` (LOW-53) chỉ xét tên top-level, nên `a["mo_ta"]`, `{"lien_quan": x}`,
`wd / "chuan_bi"` chưa bao giờ đỏ — đúng lớp mà LOW-227/228 vừa phải migrate trên máy
chủ. Cổng này quét AST mọi tệp .py git theo dõi (trừ tests/, docs/):

  - khoá: `x["k"]`, `{"k": …}`, `.get/.pop/.setdefault("k")`, `dict(k=…)`;
  - đoạn đường dẫn: toán hạng chuỗi của `/`, đối số `Path/open/glob/rglob/with_name`.

Một từ là Việt khi có cụm/từ đơn trong `docs/tu_dien_ten` mà không nằm trong PASS —
cùng máy với cổng tên. Code còn ~1 700 khoá Việt HỢP LỆ ngoài phạm vi (spec vai viết,
tệp ứng viên scan, nhật ký 9router, giá trị LOW-230, tệp cấp state LOW-231…), nên cổng
so với MỐC `docs/tu_dien_ten/vietnamese_keys_baseline.json` (theo tệp, theo khoá):
khoá mới hoặc số lần dùng TĂNG là đỏ; giảm thì xanh (cập nhật mốc cho gọn).

Đỏ vì từ English/tên riêng bị nhận nhầm → thêm vào `docs/tu_dien_ten/them.json` PASS.
Cố ý thêm khoá Việt (ví dụ đọc định dạng ngoài không đổi được) → viết lại mốc:

    venv/bin/python tests/test_json_keys_english.py --write-baseline

Chạy:  venv/bin/python tests/test_json_keys_english.py
"""
import ast
import collections
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "docs" / "tu_dien_ten"))
from tudien import TuDien                                       # noqa: E402

TU_DIEN = ROOT / "docs" / "tu_dien_ten"
BASELINE = TU_DIEN / "vietnamese_keys_baseline.json"
SKIP_TOP = ("tests/", "docs/")
PATH_CALLS = {"Path", "open", "glob", "rglob", "with_name", "joinpath"}
IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")


class Detector:
    def __init__(self, tu_dien_dir: Path = TU_DIEN):
        self.td = TuDien(tu_dien_dir)

    def is_vietnamese(self, word: str) -> bool:
        parts = [p for p in re.split(r"[^a-z0-9]+", word.lower()) if p]
        for i, p in enumerate(parts):
            for n in (4, 3, 2):
                phrase = "_".join(parts[i:i + n])
                # A whole phrase in PASS (English module name that also sits in
                # cum.json, e.g. `scan_business`) is not Vietnamese (LOW-240).
                if phrase in self.td.cum and phrase not in self.td.pass_:
                    return True
            if p not in self.td.pass_ and not p.isdigit() and p in self.td.don:
                return True
        return False


def _strings(node) -> list:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.JoinedStr):
        return [v.value for v in node.values if isinstance(v, ast.Constant) and isinstance(v.value, str)]
    return []


def scan_source(src: str, det: Detector) -> collections.Counter:
    found = collections.Counter()
    for n in ast.walk(ast.parse(src)):
        keys, segs = [], []
        if isinstance(n, ast.Subscript):
            keys += [s for s in _strings(n.slice) if isinstance(n.slice, ast.Constant)]
        elif isinstance(n, ast.Dict):
            for k in n.keys:
                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                    keys.append(k.value)
        elif isinstance(n, ast.Call):
            fn = n.func
            name = fn.attr if isinstance(fn, ast.Attribute) else fn.id if isinstance(fn, ast.Name) else ""
            if isinstance(fn, ast.Attribute) and name in ("get", "pop", "setdefault") and n.args \
                    and isinstance(n.args[0], ast.Constant):
                keys += _strings(n.args[0])
            if name == "dict":
                keys += [kw.arg for kw in n.keywords if kw.arg]
            if name in PATH_CALLS and n.args:
                segs += _strings(n.args[0])
        elif isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div):
            segs += _strings(n.left) + _strings(n.right)
        for k in keys:
            if IDENT.fullmatch(k) and det.is_vietnamese(k):
                found["key:" + k] += 1
        for s in segs:
            for seg in s.split("/"):
                stem = re.sub(r"(\.[A-Za-z0-9]+)+$", "", seg).strip("*{}")
                if stem and IDENT.fullmatch(stem) and det.is_vietnamese(stem):
                    found["path:" + seg] += 1
    return found


def tracked_py(root: Path) -> list:
    r = subprocess.run(["git", "-C", str(root), "ls-files", "-z", "--", "*.py"], capture_output=True)
    if r.returncode == 0 and r.stdout:
        names = [s for s in r.stdout.decode("utf-8").split("\0") if s]
    else:
        names = [str(p.relative_to(root)) for p in root.rglob("*.py")]
    return sorted(n for n in names if not n.startswith(SKIP_TOP) and (root / n).is_file())


def scan_repo(root: Path, det: Detector) -> dict:
    out = {}
    for rel in tracked_py(root):
        c = scan_source((root / rel).read_text(encoding="utf-8"), det)
        if c:
            out[rel] = dict(sorted(c.items()))
    return out


def load_baseline() -> dict:
    return json.loads(BASELINE.read_text(encoding="utf-8"))["files"]


def regressions(current: dict, baseline: dict) -> list:
    bad = []
    for f, items in current.items():
        base = baseline.get(f, {})
        for item, n in items.items():
            if n > base.get(item, 0):
                bad.append(f"{f}: {item} x{n} (mốc {base.get(item, 0)})")
    return bad


# ------------------------------------------------------------------ tests
def test_no_new_vietnamese_keys_or_paths():
    bad = regressions(scan_repo(ROOT, Detector()), load_baseline())
    assert not bad, ("khoá dict/đoạn đường dẫn tiếng Việt MỚI (đặt tên English, tra docs/tu_dien_ten; "
                     "nhận nhầm thì thêm PASS vào them.json):\n  " + "\n  ".join(bad[:40]))


def test_gate_catches_new_vietnamese_fixture():
    """Cổng phải ĐỎ trên `a["mo_ta"]` — chứng minh nó còn sống, không rỗng vì từ điển hỏng."""
    det = Detector()
    src = '''
def f(a, wd, m, n):
    x = a["mo_ta"]
    y = {"lien_quan": True, "url": 1, "id": 2}
    z = m.get("goi_y_bia") or m.get("images")
    p = wd / "chuan_bi" / f"them_{n}" / "manifest.json"
    q = dict(so_dung_duoc=1, version=2)
    if a.get("source") == "khai_niem":
        print("mở bang_anh.png")
    return Path("state/goc/A1.png")
'''
    got = scan_source(src, det)
    assert got["key:mo_ta"] == 1 and got["key:lien_quan"] == 1 and got["key:goi_y_bia"] == 1, got
    assert got["key:so_dung_duoc"] == 1 and got["path:chuan_bi"] == 1 and got["path:them_"] == 1, got
    assert got["path:goc"] == 1, got
    for english in ("key:url", "key:id", "key:images", "key:version", "key:source", "path:manifest.json"):
        assert english not in got, (english, got)
    assert not any("khai_niem" in k or "bang_anh" in k for k in got), \
        f"giá trị so sánh và chữ hiển thị không phải khoá/đường dẫn: {got}"
    # English module names that cum.json maps to themselves pass via a PASS phrase (LOW-240)
    for english in ("scan_business.py", "scan_models.txt", "manifest_build.py", "article_extract.py",
                    "draft_write.py", "render_edu.spec.json", "emoji_deck.json"):          # + LOW-242
        assert not scan_source(f'p = ROOT / "{english}"', det), english
    with tempfile.TemporaryDirectory() as t:
        (Path(t) / "new_module.py").write_text(src, encoding="utf-8")
        bad = regressions(scan_repo(Path(t), det), {})
    assert any("key:mo_ta" in b for b in bad), bad


def test_baseline_is_live_not_vacuous():
    """Mốc rỗng hay từ điển không nạp được thì cổng xanh vô nghĩa."""
    base = load_baseline()
    assert sum(sum(v.values()) for v in base.values()) > 100, "mốc gần rỗng — dựng lại bằng --write-baseline"
    cur = scan_repo(ROOT, Detector())
    assert cur, "quét repo không ra gì — từ điển/AST hỏng"
    stale = [f for f in base if not (ROOT / f).exists()]
    assert not stale, f"mốc nhắc tệp đã xoá — chạy lại --write-baseline: {stale[:5]}"


def test_data_contracts_are_english():
    """Hợp đồng đã migrate (LOW-227): mọi trường khai trong schema là English — không
    phụ thuộc mốc, thêm một trường Việt vào Manifest/Image/SidecarImage là đỏ ngay."""
    import schema
    det = Detector()
    for td in (schema.Manifest, schema.Image, schema.SidecarImage):
        viet = [k for k in schema._kind(td) if det.is_vietnamese(k)]
        assert not viet, f"{td.__name__} có trường tiếng Việt: {viet}"


def write_baseline() -> None:
    cur = scan_repo(ROOT, Detector())
    BASELINE.write_text(json.dumps({
        "_note": "Mốc khoá dict/đoạn đường dẫn tiếng Việt còn hợp lệ (LOW-229). Chỉ được GIẢM; "
                 "dựng lại: venv/bin/python tests/test_json_keys_english.py --write-baseline",
        "files": cur}, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    print(f"baseline: {len(cur)} files, {sum(sum(v.values()) for v in cur.values())} occurrences -> {BASELINE}")


if __name__ == "__main__":
    if "--write-baseline" in sys.argv:
        write_baseline()
    else:
        from tam import chay_tat_ca
        chay_tat_ca(globals())
