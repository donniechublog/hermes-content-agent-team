#!/usr/bin/env python3
"""tat_title_generation.py — tat buoc phu `title_generation` cua Hermes trong
config.yaml cua MOI profile (ca hai brand) + config goc.

Vi sao (05/09/2026): buoc phu nay gui `response_format` ma DeepSeek v4-flash tra
`400 This response_format type is unavailable now`; 9router coi la loi provider
va dua v4-flash vao cooldown ~30s; hai lan retry cua vong chinh (2-3s) roi tron
trong cooldown -> `Fallback activated: v4-flash -> deepseek-chat`, dinh toi het
phien. Tieu de phien vo dung voi task kanban/cron, nen tat han.

Chay tren server:
    venv/bin/python tat_title_generation.py          # sua, co backup .bak-truoc-tat-title-0905
    venv/bin/python tat_title_generation.py --thu    # chi in se sua gi

Khong can restart gateway: worker kanban la tien trinh moi, doc config khi chay.
"""
import argparse
import glob
import os
import re
import shutil
import sys

try:
    import yaml
except ImportError:                                          # pragma: no cover
    yaml = None

KHOI = "auxiliary:\n  title_generation:\n    enabled: false\n"


def tep_config() -> list:
    h = os.path.expanduser("~")
    return sorted(glob.glob(f"{h}/.hermes-blog/profiles/*/config.yaml")
                  + glob.glob(f"{h}/.hermes-dcgr/profiles/*/config.yaml")
                  + [p for p in (f"{h}/.hermes-blog/config.yaml", f"{h}/.hermes-dcgr/config.yaml")
                     if os.path.exists(p)])


def sua(s: str) -> tuple:
    if re.search(r"^  title_generation:\n(?:    .*\n)*?    enabled: false", s, re.M):
        return s, "da co"
    if re.search(r"^  title_generation:\n", s, re.M):
        return re.sub(r"^  title_generation:\n", "  title_generation:\n    enabled: false\n",
                      s, count=1, flags=re.M), "chen enabled"
    if re.search(r"^auxiliary:\n", s, re.M):
        return re.sub(r"^auxiliary:\n", "auxiliary:\n  title_generation:\n    enabled: false\n",
                      s, count=1, flags=re.M), "chen title_generation"
    return s.rstrip("\n") + "\n" + KHOI, "them khoi auxiliary"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--thu", action="store_true", help="chi in, khong ghi")
    a = ap.parse_args()
    loi = 0
    for f in tep_config():
        s = open(f, encoding="utf-8").read()
        moi, trang_thai = sua(s)
        ok = True
        if yaml is not None:
            d = yaml.safe_load(moi) or {}
            ok = ((d.get("auxiliary") or {}).get("title_generation") or {}).get("enabled") is False
        if not ok:
            loi += 1
        if not a.thu and moi != s and ok:
            bak = f + ".bak-truoc-tat-title-0905"
            if not os.path.exists(bak):
                shutil.copy2(f, bak)
            open(f, "w", encoding="utf-8").write(moi)
        print(f"{'OK ' if ok else 'LOI'} {trang_thai:22s} {f.replace(os.path.expanduser('~'), '~')}"
              + (" (thu)" if a.thu else ""))
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(main())
