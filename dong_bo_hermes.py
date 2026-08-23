#!/usr/bin/env python3
"""Dong bo SOUL va script cron giua ~/.hermes/ va ban trong git.

Vi sao can: phan lon HANH VI cua doi nam trong SOUL va script cron, ma hai thu
do lai o ngoai git. Ngay 22/08 script don em-dash lam hong 21 tep Python: 20 tep
khoi phuc tu git trong mot lenh, con moat_publish.py khong nam trong git nen
phai va tay tung khoi. Sang 23/08 lai phat hien ba script cron dung sai mui gio
ma khong co lich su de doi chieu da doi gi.

Ban CHAY THAT van o ~/.hermes/. Thu muc hermes/ trong repo chi la ban chep de co
lich su. Script nay giu hai ben khop nhau va noi ro ben nao moi hon.

Dung:
    venv/bin/python dong_bo_hermes.py              # chi so sanh, khong ghi
    venv/bin/python dong_bo_hermes.py --vao-repo   # ~/.hermes -> repo (truoc khi commit)
    venv/bin/python dong_bo_hermes.py --ra-hermes  # repo -> ~/.hermes (sau hermes update)
"""
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path.home() / "content-team"
HERMES = Path.home() / ".hermes"
REPO = ROOT / "hermes"

VAI = ["scout", "illustrator", "writer", "analyst", "teaser", "nova", "market"]
SCRIPT = ["finn_daily_scan", "nova_daily_scan", "vera_daily_scan",
          "model_watch", "usage_audit", "nhat_ky_daily"]


def cap_tep():
    """[(ten hien thi, duong that, duong trong repo)]"""
    ra = []
    for v in VAI:
        ra.append((f"SOUL {v}", HERMES / "profiles" / v / "SOUL.md",
                   REPO / "profiles" / f"{v}.SOUL.md"))
    for s in SCRIPT:
        ra.append((f"cron {s}", HERMES / "scripts" / f"{s}.sh",
                   REPO / "scripts" / f"{s}.sh"))
    return ra


def doc(p: Path):
    try:
        return p.read_bytes()
    except Exception:                                        # noqa: BLE001
        return None


def main():
    ap = argparse.ArgumentParser(description="Dong bo SOUL va cron voi git")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--vao-repo", action="store_true", help="~/.hermes -> repo")
    g.add_argument("--ra-hermes", action="store_true", help="repo -> ~/.hermes")
    a = ap.parse_args()

    khac, thieu, da_chep = [], [], 0
    for ten, that, repo in cap_tep():
        a_b, b_b = doc(that), doc(repo)
        if a_b is None:
            thieu.append(f"{ten}: khong co ban that ({that})")
            continue
        if a_b == b_b:
            continue
        khac.append((ten, that, repo, b_b is None))

        if a.vao_repo:
            repo.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(that, repo)
            da_chep += 1
        elif a.ra_hermes:
            if b_b is None:
                continue                # khong co ban repo thi khong ghi de
            that.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(repo, that)
            da_chep += 1

    for t in thieu:
        print(f"  [thieu] {t}", file=sys.stderr)
    if not khac:
        print("Hai ben khop nhau, khong co gi de dong bo.")
        return 0

    huong = "-> repo" if a.vao_repo else ("-> ~/.hermes" if a.ra_hermes else "")
    for ten, _, _, moi in khac:
        print(f"  {'MOI  ' if moi else 'KHAC '} {ten} {huong}")
    if a.vao_repo or a.ra_hermes:
        print(f"\nDa chep {da_chep} tep.")
    else:
        print(f"\n{len(khac)} tep lech. Chay voi --vao-repo hoac --ra-hermes de dong bo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
