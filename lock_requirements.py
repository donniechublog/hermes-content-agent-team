#!/usr/bin/env python3
"""Generate requirements.lock: the installed version of every package that
requirements.txt declares, plus everything those packages pull in (LOW-300).

Run it with the Python of the venv that is known to work, i.e. on the server, not
on a laptop, because the lock must record what actually runs there:

    scp requirements.txt lock_requirements.py donniechu-01.netbird.mated:/tmp/
    ssh donniechu-01.netbird.mated '~/hermes-agent/venv/bin/python /tmp/lock_requirements.py /tmp/requirements.txt' > requirements.lock

That venv is shared with hermes (~150 packages). Only the closure of OUR
requirements is locked, never the whole `pip freeze`. Read-only: it installs and
changes nothing, and it refuses to write a partial lock when a declared package
is not installed.
"""
import importlib.metadata as metadata
import platform
import re
import sys
from datetime import date
from pathlib import Path

NAME_AT_START = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]*")


def norm_name(name: str) -> str:
    """PEP 503: 'PyYAML' == 'pyyaml', 'typing_extensions' == 'typing-extensions'."""
    return re.sub(r"[-_.]+", "-", name).lower()


def parse_roots(text: str) -> list:
    """Package names declared in a requirements.txt (comments, blanks, options skipped)."""
    roots = []
    for line in text.splitlines():
        line = line.split("#", 1)[0].strip()
        if not line or line.startswith("-"):
            continue
        hit = NAME_AT_START.match(line)
        if hit:
            roots.append(norm_name(hit.group(0)))
    return roots


def closure(roots: list, lookup, applies) -> tuple:
    """-> ({name: (display_name, version)}, [names that are not installed]).

    `lookup(name)` -> (display_name, version, [requirement strings]) or None when
    the package is not installed. `applies(marker)` -> whether an environment
    marker holds on this interpreter. Extras are not followed: requirements.txt
    asks for none, and a requirement gated on `extra == ...` does not apply."""
    found, missing, todo = {}, [], list(roots)
    while todo:
        name = todo.pop()
        if name in found or name in missing:
            continue
        hit = lookup(name)
        if hit is None:
            missing.append(name)
            continue
        display, version, requires = hit
        found[name] = (display, version)
        for requirement in requires:
            spec, _, marker = requirement.partition(";")
            if marker.strip() and not applies(marker.strip()):
                continue
            dep = NAME_AT_START.match(spec.strip())
            if dep:
                todo.append(norm_name(dep.group(0)))
    return found, sorted(missing)


def _installed_lookup():
    index = {norm_name(d.metadata["Name"]): d for d in metadata.distributions()}

    def lookup(name):
        dist = index.get(name)
        if dist is None:
            return None
        return dist.metadata["Name"], dist.version, list(dist.requires or [])

    return lookup


def _marker_applies():
    try:
        from packaging.markers import Marker
    except ImportError:
        from pip._vendor.packaging.markers import Marker
    # extra="" makes `extra == "socks"` false, which is what "no extras requested" means
    return lambda marker: Marker(marker).evaluate({"extra": ""})


def main(argv: list | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    path = Path(argv[0]) if argv else Path(__file__).resolve().parent / "requirements.txt"
    roots = parse_roots(path.read_text(encoding="utf-8"))
    found, missing = closure(roots, _installed_lookup(), _marker_applies())
    if missing:
        print("[ERROR] not installed in this venv, lock NOT written: " + ", ".join(missing),
              file=sys.stderr)
        return 1
    print("# requirements.lock — sinh boi lock_requirements.py, KHONG sua tay (LOW-300).")
    print(f"# Nguon: Python {platform.python_version()} tren {platform.node()}, ngay {date.today().isoformat()}.")
    print(f"# {len(found)} goi = cac goi khai trong requirements.txt + phu thuoc bac cau; khong phai ca")
    print("# venv dung chung voi hermes. Cach lam moi: xem dau requirements.txt.")
    for name in sorted(found):
        display, version = found[name]
        print(f"{display}=={version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
