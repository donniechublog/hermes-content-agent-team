#!/usr/bin/env python3
"""doi_model_combo.py — doi `model.default` cua MOI profile Hermes (ca hai brand)
+ config goc sang mot ten model khac, mac dinh combo `DS-v4Flash` cua 9router.

Vi sao (05/09/2026): 9router chi xoay giua cac connection CUNG provider; ba
provider v4-flash (deepseek truc tiep, xKiro `dsx/`, aellm `dsa/`) chi noi
duoc voi nhau qua Combo. Goi combo bang dung ten combo lam model (khong co
prefix `combo/`). Da thu 05/09: `DS-v4Flash` tra loi va goi tool duoc, `dsx/`
va `dsa/` cung vay.

Chay tren server:
    venv/bin/python doi_model_combo.py --thu                 # chi in
    venv/bin/python doi_model_combo.py                       # sua, backup .bak-truoc-doi-combo-0905
    venv/bin/python doi_model_combo.py --model ds/deepseek-v4-flash   # quay lai
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


def tep_config() -> list:
    h = os.path.expanduser("~")
    return sorted(glob.glob(f"{h}/.hermes-blog/profiles/*/config.yaml")
                  + glob.glob(f"{h}/.hermes-dcgr/profiles/*/config.yaml")
                  + [p for p in (f"{h}/.hermes-blog/config.yaml", f"{h}/.hermes-dcgr/config.yaml")
                     if os.path.exists(p)])


def sua(s: str, model: str, tu: str = "ds/deepseek-v4-flash") -> tuple:
    """Chi doi dong `  default:` nam trong khoi `model:`, va chi khi gia tri hien
    tai la `tu` (mac dinh v4-flash truc tiep) — analyst dung deepseek-reasoner
    co chu y, khong dong cham."""
    m = re.search(r"^model:\n((?:  .*\n)+)", s, re.M)
    if not m:
        return s, "khong co khoi model"
    khoi = m.group(1)
    cu = re.search(r"^  default: (.*)$", khoi, re.M)
    if not cu:
        return s, "khong co default"
    if cu.group(1).strip() == model:
        return s, f"da la {model}"
    if tu and cu.group(1).strip() != tu:
        return s, f"giu nguyen {cu.group(1).strip()} (khong phai {tu})"
    khoi_moi = khoi[:cu.start(1)] + model + khoi[cu.end(1):]
    return s[:m.start(1)] + khoi_moi + s[m.end(1):], f"{cu.group(1).strip()} -> {model}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="DS-v4Flash")
    ap.add_argument("--tu", default="ds/deepseek-v4-flash",
                    help="chi doi profile dang o model nay; '' = doi tat ca")
    ap.add_argument("--thu", action="store_true", help="chi in, khong ghi")
    a = ap.parse_args()
    loi = 0
    for f in tep_config():
        s = open(f, encoding="utf-8").read()
        moi, trang_thai = sua(s, a.model, a.tu)
        ok = True
        if yaml is not None and moi != s:
            ok = ((yaml.safe_load(moi) or {}).get("model") or {}).get("default") == a.model
        if not ok:
            loi += 1
        if not a.thu and moi != s and ok:
            bak = f + ".bak-truoc-doi-combo-0905"
            if not os.path.exists(bak):
                shutil.copy2(f, bak)
            open(f, "w", encoding="utf-8").write(moi)
        print(f"{'OK ' if ok else 'LOI'} {trang_thai:42s} {f.replace(os.path.expanduser('~'), '~')}"
              + (" (thu)" if a.thu else ""))
    return 1 if loi else 0


if __name__ == "__main__":
    sys.exit(main())
