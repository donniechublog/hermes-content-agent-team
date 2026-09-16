#!/usr/bin/env python3
"""Cổng chặn tên Việt-không-dấu quay lại mã (LOW-53, sau refactor LOW-50).

Sau 13/09/2026 mọi module/hàm/lớp/hằng top-level đã mang tên English theo từ
điển `docs/tu_dien_ten/`. Không có cổng thì mã mới (hoặc nhánh cũ rebase) lại
đưa `def tim_anh_moi()` vào `main` mà không ai thấy. Cổng dùng ĐÚNG máy đã đổi
tên: `bang_doi_ten()` — kế hoạch rename phải RỖNG. Còn dòng nào là còn token
Việt, in ra `module.tên → tên_đề_xuất` để người viết đổi (hoặc thêm từ vào
`them.json` PASS nếu là English/tên riêng bị nhận nhầm).

Phạm vi = phạm vi của LOW-50: tên top-level. Tham số/biến cục bộ không xét.
Shim tên cũ (`\"\"\"SHIM tạm`) được `quet` bỏ qua.

Chay:  venv/bin/python tests/test_name_english.py
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "docs" / "tu_dien_ten"))
from tudien import TuDien, bang_doi_ten                       # noqa: E402

TU_DIEN = ROOT / "docs" / "tu_dien_ten"


def _plan(root: Path) -> list:
    """[(module, tên_cũ, tên_đề_xuất, loại)] — rỗng là sạch. Chỉ quét tệp git
    theo dõi (LOW-55): tệp nháp bị .gitignore trên máy chủ không phải mã repo."""
    plan = bang_doi_ten(TuDien(TU_DIEN), root, chi_git=True)
    ra = []
    for mod, en in plan["modules"].items():
        ra.append((mod, mod, en, "module"))
    for mod, ds in plan["defs"].items():
        ra += [(mod, o, n, k) for o, n, k in ds]
    for mod, cs in plan["consts"].items():
        ra += [(mod, o, n, "const") for o, n in cs]
    return ra


def test_no_remaining_name_write_top_level():
    con = _plan(ROOT)
    assert con == [], "tên Việt không dấu ở top-level (đổi theo cột phải, hoặc thêm PASS vào them.json):\n" + \
        "\n".join(f"  {m}.{o} -> {n}  ({k})" for m, o, n, k in con[:40])


def test_skip_file_gitignore_but_still_catch_file_within_git():
    """LOW-55: máy chủ có `gif2png_tmp.py` (nháp, bị .gitignore) làm cổng đỏ giả
    dù CI xanh. Trong repo git: tệp bị ignore/untracked KHÔNG được tính, tệp đã
    `git add` mang tên Việt VẪN phải bị bắt."""
    import shutil
    import subprocess
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        g = Path(t)
        (g / "docs").mkdir()
        shutil.copytree(TU_DIEN, g / "docs" / "tu_dien_ten")
        subprocess.run(["git", "init", "-q", str(g)], check=True)
        (g / ".gitignore").write_text("anh_nhap_tmp.py\n", encoding="utf-8")
        (g / "anh_nhap_tmp.py").write_text("def doi_anh_nhap():\n    pass\n", encoding="utf-8")
        (g / "chua_add.py").write_text("def tim_chua_add():\n    pass\n", encoding="utf-8")
        (g / "thu_moi.py").write_text("def tim_anh_moi(x):\n    return x\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(g), "add", "thu_moi.py", "docs"], check=True)
        con = _plan(g)
    ten = {o for _m, o, _n, _k in con}
    assert "tim_anh_moi" in ten, con
    assert "doi_anh_nhap" not in ten and "anh_nhap_tmp" not in ten, con
    assert "tim_chua_add" not in ten and "chua_add" not in ten, con


def test_gate_catch_ok_name_write_new():
    """Cổng phải ĐỎ khi có `def tim_anh_moi()` — chứng minh cổng còn sống, không
    phải rỗng vì từ điển không nạp được."""
    import shutil
    import tempfile
    with tempfile.TemporaryDirectory() as t:
        g = Path(t)
        (g / "docs").mkdir()
        shutil.copytree(TU_DIEN, g / "docs" / "tu_dien_ten")
        (g / "thu_moi.py").write_text("def tim_anh_moi(x):\n    return x\n\nSO_LUOT_TOI_DA = 3\n", encoding="utf-8")
        con = _plan(g)
    ten = {(o, k) for _m, o, _n, k in con}
    assert ("tim_anh_moi", "def") in ten, con
    assert ("SO_LUOT_TOI_DA", "const") in ten, con
    assert any(k == "module" for _m, _o, _n, k in con), con


if __name__ == "__main__":
    from tam import chay_tat_ca
    chay_tat_ca(globals())
