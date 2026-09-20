#!/usr/bin/env python3
"""Cổng chặn requirements.lock trôi khỏi requirements.txt (LOW-300).

CI cài từ lock, không phải từ requirements.txt. Thêm một gói vào requirements.txt mà
quên làm mới lock thì CI KHÔNG cài gói đó — và nếu code có đường rơi về khi thiếu gói
(như `article_extract._parser()` với lxml, hay defusedxml ở LOW-303) thì test vẫn xanh
mà chạy nhầm đường rơi về. Ba test đầu chặn đúng lớp đó; phần còn lại kiểm phép tính
bao đóng phụ thuộc của lock_requirements.py.

Chạy:  venv/bin/python tests/test_requirements_lock.py
"""
import contextlib
import io
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import lock_requirements as lr                                   # noqa: E402

EXACT_PIN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*==[0-9][A-Za-z0-9.!+_-]*$")


def _lock_lines() -> list:
    text = (ROOT / "requirements.lock").read_text(encoding="utf-8")
    return [ln.strip() for ln in text.splitlines() if ln.strip() and not ln.lstrip().startswith("#")]


def test_lock_every_line_is_an_exact_pin():
    bad = [ln for ln in _lock_lines() if not EXACT_PIN.match(ln)]
    assert not bad, "dòng không phải `tên==phiên_bản`: " + ", ".join(bad)


def test_lock_has_no_duplicate_package():
    names = [lr.norm_name(ln.split("==")[0]) for ln in _lock_lines()]
    dup = sorted({n for n in names if names.count(n) > 1})
    assert not dup, "gói ghim hai lần: " + ", ".join(dup)


def test_lock_pins_every_declared_requirement():
    declared = lr.parse_roots((ROOT / "requirements.txt").read_text(encoding="utf-8"))
    locked = {lr.norm_name(ln.split("==")[0]) for ln in _lock_lines()}
    missing = [n for n in declared if n not in locked]
    assert declared, "không đọc được gói nào từ requirements.txt"
    assert not missing, ("requirements.txt khai mà requirements.lock không ghim: " + ", ".join(missing)
                         + " — làm mới lock theo hướng dẫn ở đầu requirements.txt")


def test_parse_roots_skips_comments_options_and_specifiers():
    text = ("# comment\n\nhttpx>=0.27          # ghi chu\n-r other.txt\nPyYAML>=6\n"
            "opencv-python-headless>=4.9  # x\n  # thut le\n")
    assert lr.parse_roots(text) == ["httpx", "pyyaml", "opencv-python-headless"]


def test_norm_name_is_pep503():
    assert lr.norm_name("PyYAML") == "pyyaml"
    assert lr.norm_name("typing_extensions") == lr.norm_name("Typing.Extensions") == "typing-extensions"


def test_closure_follows_transitive_requirements_and_skips_extras_and_false_markers():
    graph = {
        "app": ("App", "1.0", ["dep-a>=1", "dep-old ; python_version < '3.0'",
                               "dep-socks[x] ; extra == 'socks'"]),
        "dep-a": ("dep_a", "2.0", ["leaf (>=1)"]),
        "leaf": ("Leaf", "3.1", []),
        "dep-old": ("dep-old", "9", []),
        "dep-socks": ("dep-socks", "9", []),
    }
    found, missing = lr.closure(["app"], graph.get,
                                lambda marker: "python_version" not in marker and "extra" not in marker)
    assert found == {"app": ("App", "1.0"), "dep-a": ("dep_a", "2.0"), "leaf": ("Leaf", "3.1")}, found
    assert missing == []


def test_closure_reports_packages_that_are_not_installed():
    graph = {"a": ("a", "1", ["ghost-dep"])}
    found, missing = lr.closure(["a", "ghost"], graph.get, lambda marker: True)
    assert list(found) == ["a"]
    assert missing == ["ghost", "ghost-dep"], missing


def test_marker_treats_extra_as_not_requested():
    applies = lr._marker_applies()
    assert applies('python_version >= "3.0"')
    assert not applies('python_version < "3.0"')
    assert not applies('extra == "socks"')


def _run_main(requirements_text: str) -> tuple:
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "requirements.txt"
        path.write_text(requirements_text, encoding="utf-8")
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            rc = lr.main([str(path)])
    return rc, out.getvalue(), err.getvalue()


def test_main_writes_pins_for_installed_packages():
    # httpx: tests/run.sh đòi nó có mặt, nên có ở mọi nơi test chạy.
    rc, out, _ = _run_main("httpx>=0.27\n")
    lines = [ln for ln in out.splitlines() if not ln.startswith("#")]
    assert rc == 0
    assert any(ln.lower().startswith("httpx==") for ln in lines), out
    assert all(EXACT_PIN.match(ln) for ln in lines), lines


def test_main_refuses_to_write_a_partial_lock():
    rc, out, err = _run_main("httpx>=0.27\nno-such-package-lock-test>=1\n")
    assert rc == 1
    assert out == "", "không được in lock dở dang"
    assert "no-such-package-lock-test" in err


if __name__ == "__main__":
    from tam import chay_tat_ca          # runner chung: bắt cả Exception, luôn in N/M
    chay_tat_ca(globals())
