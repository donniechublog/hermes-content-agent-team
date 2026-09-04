#!/usr/bin/env python3
"""Dong bo SOUL/MEMORY/cron giua cac HERMES_HOME dang chay va ban trong git.

Vi sao can: phan lon HANH VI cua doi nam trong SOUL va script cron, ma hai thu
do lai o ngoai git. Ngay 22/08 script don em-dash lam hong 21 tep Python: 20 tep
khoi phuc tu git trong mot lenh, con moat_publish.py khong nam trong git nen
phai va tay tung khoi. Sang 23/08 lai phat hien ba script cron dung sai mui gio
ma khong co lich su de doi chieu da doi gi.

Da TACH CONTAINER theo brand: moi brand mot HERMES_HOME rieng
(`~/.hermes-blog`, `~/.hermes-dcgr`). Ban CHAY THAT nam trong cac home do; thu
muc hermes/ trong repo la ban chep co lich su, to chuc theo container:

    hermes/profiles/blog/<slug>.SOUL.md    -> ~/.hermes-blog/profiles/<slug>/
    hermes/profiles/dcgr/<slug>.SOUL.md    -> ~/.hermes-dcgr/profiles/<slug>/
    hermes/profiles/shared/<slug>.SOUL.md  -> CA HAI home

Slug la ten thu muc THAT trong home (generic: carousel, designer, writer...),
khong phai ten nhan vat cu (heller/dre...). Profile co trong git ma home khong
co (vd carousel-edu chua deploy) se bao [thieu], KHONG bi tao ra.

Dung:
    venv/bin/python dong_bo_hermes.py              # chi so sanh, khong ghi
    venv/bin/python dong_bo_hermes.py --vao-repo   # home -> repo (truoc khi commit)
    venv/bin/python dong_bo_hermes.py --ra-hermes  # repo -> home (sau hermes update)
"""
import argparse
import sys
from pathlib import Path

ROOT = Path.home() / "content-team"
REPO = ROOT / "hermes"
# Moi brand mot home rieng. Them brand = them mot dong o day.
HOMES = {"blog": Path.home() / ".hermes-blog",
         "dcgr": Path.home() / ".hermes-dcgr"}

# Plugin kanban nam trong ban cai hermes nen `hermes update` SE ghi de. Da sua
# ba thu o day: thu tu cot (running/ready/blocked truoc), co chu nhan profile,
# va chia lane theo profile o moi cot chu khong chi cot running.
PLUGIN_KANBAN = Path.home() / "hermes-agent/plugins/kanban/dashboard"
PLUGIN_TEP = ["plugin_api.py", "dist/index.js", "dist/style.css"]
# Cron scripts brand-aware (mot ban, doc CT_BRAND). Dong bo sang scripts/ cua
# CA HAI home; home nao khong chay job do thi khong co tep -> bao [thieu],
# KHONG tao (ton trong phan chia job per-brand trong jobs.json). "moat_publish_
# watch" tung nam ngoai danh sach du la job chay DAY NHAT (moi phut) co ca
# find -delete — mot script hong ngoai git la dung kich ban 22/08.
SCRIPT = ["finn_daily_scan", "nova_daily_scan", "vera_daily_scan",
          "model_watch", "usage_audit", "nhat_ky_daily", "moat_publish_watch"]
# Skill KHONG dong bo: ban that da o thang trong repo (hermes/skills/), profile
# tro vao qua skills.external_dirs nen `hermes update` khong xoa duoc.


def _slug(soul_path: Path) -> str:
    return soul_path.name[: -len(".SOUL.md")]


def cap_tep():
    """[(ten hien thi, duong that trong home, duong trong repo)]"""
    ra = []

    def them_profile(slug, repo_soul, home_keys):
        repo_mem = repo_soul.with_name(f"{slug}.MEMORY.md")
        for hk in home_keys:
            H = HOMES[hk]
            ra.append((f"SOUL {hk}/{slug}",
                       H / "profiles" / slug / "SOUL.md", repo_soul))
            # MEMORY.md mang HANH VI (vd quy uoc tag fact_store), can lich su
            # nhu SOUL. USER.md rieng tung profile KHONG dong bo (co the co du
            # lieu ca nhan) — chi USER.md base cua home moi chep.
            if repo_mem.exists():
                ra.append((f"MEMORY {hk}/{slug}",
                           H / "profiles" / slug / "memories" / "MEMORY.md",
                           repo_mem))

    for brand in ("blog", "dcgr"):
        d = REPO / "profiles" / brand
        for soul in sorted(d.glob("*.SOUL.md")):
            them_profile(_slug(soul), soul, [brand])
    for soul in sorted((REPO / "profiles" / "shared").glob("*.SOUL.md")):
        them_profile(_slug(soul), soul, ["blog", "dcgr"])

    for hk, H in HOMES.items():
        ra.append((f"MEMORY base {hk}", H / "memories" / "MEMORY.md",
                   REPO / "memories" / "MEMORY.md"))
        ra.append((f"USER base {hk}", H / "memories" / "USER.md",
                   REPO / "memories" / "USER.md"))
    for s in SCRIPT:
        for hk, H in HOMES.items():
            ra.append((f"cron {hk}/{s}", H / "scripts" / f"{s}.sh",
                       REPO / "scripts" / f"{s}.sh"))
    for f in PLUGIN_TEP:
        ra.append((f"kanban {f}", PLUGIN_KANBAN / f,
                   REPO / "plugins" / "kanban" / f.replace("/", ".")))
    return ra


# Tep plugin nam trong ban cai hermes. `hermes update` co the doi ca cau truc
# ben trong, luc do de ban cu cua ta len la hong bang. Neu kich thuoc lech qua
# nguong nay thi KHONG ghi de, bat phai xem lai bang tay.
NGUONG_LECH = 0.15          # 15%
LA_PLUGIN = "kanban "


def canh_bao_de_len(ten: str, that: Path, repo: Path) -> str | None:
    """Tra ve ly do KHONG nen ghi de, hoac None neu an toan."""
    if not ten.startswith(LA_PLUGIN):
        return None
    try:
        a, b = that.stat().st_size, repo.stat().st_size
    except Exception:                                        # noqa: BLE001
        return None
    if a == 0 or b == 0:
        return None
    lech = abs(a - b) / max(a, b)
    if lech > NGUONG_LECH:
        return (f"ban that {a:,} byte / ban repo {b:,} byte, lech {lech:.0%} "
                "— co the hermes da cap nhat, va rat co the doi cau truc")
    return None


def doc(p: Path):
    try:
        return p.read_bytes()
    except Exception:                                        # noqa: BLE001
        return None


def chuan(b):
    """Chuan hoa xuong dong ve LF. Dev tren Windows (CRLF), home tren Unix (LF)
    — so sanh/ghi theo byte tho se bao KHAC het du noi dung y het. So sanh va
    ghi deu qua ham nay: dong bo dung noi dung, khong lam ban xuong dong."""
    if b is None:
        return None
    return b.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def main():
    ap = argparse.ArgumentParser(description="Dong bo SOUL/cron voi git (multi-home)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--vao-repo", action="store_true", help="home -> repo")
    g.add_argument("--ra-hermes", action="store_true", help="repo -> home")
    ap.add_argument("--ep", action="store_true",
                    help="Ghi de ke ca khi tep plugin lech nhieu (dung sau khi "
                         "da xem bang tay va chac chan)")
    ap.add_argument("--chi", metavar="CHUOI",
                    help="Chi dong bo cac muc co ten chua CHUOI (vd --chi carousel). "
                         "Dung khi drift hai chieu: day/keo tung phan, khong mu.")
    a = ap.parse_args()

    khac, thieu, bo_qua, da_chep = [], [], [], 0
    for ten, that, repo in cap_tep():
        if a.chi and a.chi not in ten:
            continue
        a_b, b_b = doc(that), doc(repo)
        if a_b is None:
            thieu.append(f"{ten}: khong co ban that ({that})")
            continue
        if chuan(a_b) == chuan(b_b):     # so sanh theo noi dung (bo qua CRLF)
            continue
        khac.append((ten, that, repo, b_b is None))

        if a.vao_repo:
            repo.parent.mkdir(parents=True, exist_ok=True)
            repo.write_bytes(chuan(a_b))          # ghi LF vao repo
            da_chep += 1
        elif a.ra_hermes:
            if b_b is None:
                continue                # khong co ban repo thi khong ghi de
            ly_do = canh_bao_de_len(ten, that, repo)
            if ly_do and not a.ep:
                bo_qua.append((ten, ly_do))
                continue
            that.parent.mkdir(parents=True, exist_ok=True)
            that.write_bytes(chuan(b_b))          # ghi LF vao home
            da_chep += 1

    for t in thieu:
        print(f"  [thieu] {t}", file=sys.stderr)
    if not khac:
        print("Hai ben khop nhau, khong co gi de dong bo.")
        return 0

    huong = "-> repo" if a.vao_repo else ("-> home" if a.ra_hermes else "")
    for ten, _, _, moi in khac:
        print(f"  {'MOI  ' if moi else 'KHAC '} {ten} {huong}")
    if bo_qua:
        print()
        for ten, ly_do in bo_qua:
            print(f"  [BO QUA] {ten}")
            print(f"           {ly_do}")
        print("  Xem lai bang tay roi va lai tu ban moi, hoac chay --ep neu chac chan.")
    if a.vao_repo or a.ra_hermes:
        print(f"\nDa chep {da_chep} tep.")
    else:
        print(f"\n{len(khac)} tep lech. Chay voi --vao-repo hoac --ra-hermes de dong bo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
