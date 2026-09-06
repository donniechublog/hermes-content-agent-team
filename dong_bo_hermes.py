#!/usr/bin/env python3
"""Dong bo SOUL/MEMORY/cron/plugin kanban giua cac HERMES_HOME dang chay va ban trong git.

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
    hermes/plugins/kanban/dashboard/*      -> <home>/plugins/kanban/dashboard/*  (ca hai)

Slug la ten thu muc THAT trong home (generic: carousel, designer, writer...),
khong phai ten nhan vat cu (heller/dre...). Profile co trong git ma home khong
co (vd carousel-edu chua deploy) se bao [thieu], KHONG bi tao ra.

Dung:
    venv/bin/python dong_bo_hermes.py                  # chi so sanh, khong ghi
    venv/bin/python dong_bo_hermes.py --vao-repo       # home -> repo (truoc khi commit)
    venv/bin/python dong_bo_hermes.py --ra-hermes      # repo -> home (sau khi sua trong git)
    venv/bin/python dong_bo_hermes.py --kiem-upstream  # hermes-agent doi gi o kanban ke tu UPSTREAM
    venv/bin/python dong_bo_hermes.py --chot-upstream  # da port xong: ghi HEAD hermes-agent vao UPSTREAM
"""
import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

import env_load

ROOT = env_load.ROOT
REPO = ROOT / "hermes"
# Moi brand mot home rieng. Them brand = them mot dong o day.
HOMES = {"blog": Path.home() / ".hermes-blog",
         "dcgr": Path.home() / ".hermes-dcgr"}

# ---- Plugin kanban: PLUGIN NGUOI DUNG, khong con va vao ban cai hermes -------
# Truoc 06/09/2026 ban va nam TRONG ~/hermes-agent/plugins/kanban/dashboard —
# tuc trong ban cai hermes — nen `hermes update` reset no ve upstream, roi mot
# lan --vao-repo keo ban da bi reset vao git va xoa mat ba ban va (a1f9387).
# Cong lech-kich-thuoc 15% khong bat duoc, cong dau vet (06/09 sang) bat duoc
# nhung van la vo dau: goc re la de ban va o cho hermes update se ghi de.
#
# Hermes co san cach dung: dashboard quet <HERMES_HOME>/plugins/<ten>/dashboard/
# TRUOC plugins di kem, va khu trung THEO TEN (web_server._discover_dashboard_
# plugins, `seen_names`). Mot plugin ten `kanban` o thu muc nguoi dung che
# hoan toan ban di kem — ca dist/ lan plugin_api.py — va `hermes update` khong
# bao gio dung vao <HERMES_HOME>/plugins/. Nen tu 06/09/2026 chieu:
#
#     hermes/plugins/kanban/dashboard/  <->  <home>/plugins/kanban/dashboard/
#
# cho CA HAI home. ~/hermes-agent chi con la NGUON DE SOI upstream doi gi
# (--kiem-upstream), khong con la diem dong bo. Dieu kien de API cua plugin
# nguoi dung duoc mount: `plugins.enabled` trong config.yaml cua home phai co
# "kanban" (hermes gate theo GHSA-mcfc-hp25-cjv7) — script kiem va nhac.
HERMES_AGENT = Path(os.environ.get("HERMES_AGENT_DIR") or (Path.home() / "hermes-agent"))
PLUGIN_TEP = ["manifest.json", "plugin_api.py", "dist/index.js", "dist/style.css"]
PLUGIN_REPO = REPO / "plugins" / "kanban" / "dashboard"
# Ghi lai ban va dang dung tren commit upstream nao, de lan sau con rebase 3
# chieu duoc thay vi doan. Xem chu thich trong chinh tep UPSTREAM.
TEP_UPSTREAM = REPO / "plugins" / "kanban" / "UPSTREAM"
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


def plugin_home(H: Path) -> Path:
    return H / "plugins" / "kanban" / "dashboard"


def cap_tep():
    """[(ten hien thi, duong that trong home, duong trong repo)]"""
    ra = []

    def them_profile(slug, repo_soul, home_keys):
        for hk in home_keys:
            H = HOMES[hk]
            ra.append((f"SOUL {hk}/{slug}",
                       H / "profiles" / slug / "SOUL.md", repo_soul))
            # MEMORY.md mang HANH VI (vd quy uoc tag fact_store), can lich su
            # nhu SOUL. USER.md rieng tung profile KHONG dong bo (co the co du
            # lieu ca nhan) — chi USER.md base cua home moi chep.
            # SOUL dung chung (shared/) van co the co MEMORY rieng tung brand
            # (profiles/<brand>/<slug>.MEMORY.md, vd carousel/designer/writer
            # tu 05/09/2026): uu tien ban rieng, khong co thi lay ban canh SOUL.
            rieng = REPO / "profiles" / hk / f"{slug}.MEMORY.md"
            repo_mem = rieng if rieng.exists() else repo_soul.with_name(f"{slug}.MEMORY.md")
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
    # Ten muc: "kanban <home> <tep>" — thieu_dau_vet tach tep bang split(" ", 2).
    for f in PLUGIN_TEP:
        for hk, H in HOMES.items():
            ra.append((f"kanban {hk} {f}", plugin_home(H) / f, PLUGIN_REPO / f))
    return ra


LA_PLUGIN = "kanban "

# Dau vet cua tung ban va doi tu sua trong plugin kanban. Van giu du ban va da
# ra khoi ban cai hermes: no la cong "khong thut lui" — mot lan --vao-repo keo
# tu mot home vua bi ai do chep nham ban upstream vao van bi chan, thay vi lang
# le xoa ban va nhu a1f9387. Ap cho CA HAI CHIEU.
DAU_VET = {
    "dist/index.js": [
        ("nhan ten vai", "tenVai("),
        ("chia lane moi cot", "if (!props.laneByProfile) return null;"),
        ("thu tu cot", '["running", "ready", "blocked"'),
    ],
    "dist/style.css": [
        # Khong dung "font-size: 0.82rem;" lam dau vet: chuoi do con nam o
        # .hermes-kanban-md h4 va mot rule khac, co ca o ban CHUA va, nen
        # khong phan biet duoc. Lay cau chu thich rieng cua ban va.
        ("co chu lane", "0.65rem qua nho"),
        ("vien trai lane", "border-left: 3px solid var(--color-ring"),
        ("nen huy hieu profile", "color-mix(in srgb, var(--color-ring) 16%"),
    ],
    "plugin_api.py": [
        ("ten vai tu profile.yaml", "display_names"),
    ],
}


def _tep_plugin(ten: str) -> str | None:
    """'kanban blog dist/index.js' -> 'dist/index.js'; None neu khong phai muc plugin."""
    if not ten.startswith(LA_PLUGIN):
        return None
    phan = ten.split(" ", 2)
    return phan[2] if len(phan) == 3 else None


def thieu_dau_vet(ten: str, nguon: bytes, dich: bytes) -> str | None:
    """Ly do KHONG nen ghi `nguon` de len `dich`, hoac None neu an toan.

    Chi chan khi ben DICH dang co dau vet ma ben NGUON thieu — do dung la kich
    ban ghi de lam mat ban va. Chieu nguoc lai (nguon co, dich thieu) chinh la
    dang mang ban va sang, phai cho chay. Khong bat Exception o day: ca hai ban
    byte da doc xong truoc khi goi, fail-open kieu cu la thu da giau loi.
    """
    tep = _tep_plugin(ten)
    dau = DAU_VET.get(tep) if tep else None
    if not dau or nguon is None or dich is None:
        return None
    mat = [nhan for nhan, chuoi in dau
           if chuoi.encode() in dich and chuoi.encode() not in nguon]
    if not mat:
        return None
    return ("ben nguon thieu ban va ma ben dich dang co: " + ", ".join(mat)
            + " — ghi de la mat ban va")


def hai_home_lech(tep: str, doc_fn=None) -> str | None:
    """--vao-repo: hai home phai giong nhau o tep plugin nay, khong thi tu choi
    — chep 'home nao doc sau thang' la im lang nuot ban cua home kia. Tra ve ly
    do, hoac None neu chi mot home co tep / ca hai giong nhau."""
    doc_fn = doc_fn or doc
    ban = {hk: chuan(doc_fn(plugin_home(H) / tep)) for hk, H in HOMES.items()}
    ban = {hk: b for hk, b in ban.items() if b is not None}
    if len({b for b in ban.values()}) <= 1:
        return None
    return ("hai home co hai ban KHAC NHAU (" + ", ".join(sorted(ban)) + ") — "
            "xem diff bang tay, chon mot ban, chay lai voi --chi kanban <home>")


MAU_UPSTREAM = """\
# Xuất xứ bản chép plugin kanban trong repo này. TỆP DO MÁY GHI, đừng sửa tay.
#
# `hermes/plugins/kanban/dashboard/` là plugin NGƯỜI DÙNG (che plugin đi kèm
# cùng tên, hermes update không đụng), gồm bản upstream CỘNG bốn bản vá của đội.
# Vì bị che nên upstream đổi gì ở dashboard kanban đội cũng không tự nhận được —
# đó là cái giá đổi lấy việc không còn mất bản vá. Muốn nhận thì port có chủ ý:
#
#   venv/bin/python dong_bo_hermes.py --kiem-upstream   # upstream đổi gì kể từ hash dưới
#   # vá lại bốn bản vá lên bản mới, --ra-hermes, restart dashboard, rồi:
#   venv/bin/python dong_bo_hermes.py --chot-upstream   # ghi HEAD mới vào đây
#
# `commit:` là HEAD của ~/hermes-agent lúc port lần cuối.

commit: {hash}
ghi_luc: {ngay}
"""


def hash_upstream() -> str | None:
    """HEAD cua ban cai hermes-agent, hoac None neu no khong phai repo git."""
    try:
        r = subprocess.run(["git", "-C", str(HERMES_AGENT), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() or None if r.returncode == 0 else None


def doc_upstream() -> str | None:
    try:
        for d in TEP_UPSTREAM.read_text(encoding="utf-8").splitlines():
            if d.startswith("commit:"):
                return d.split(":", 1)[1].strip() or None
    except OSError:
        pass
    return None


def ghi_upstream() -> str | None:
    """Ghi HEAD hermes-agent hien tai vao UPSTREAM (sau khi da port). Tra ve hash."""
    h = hash_upstream()
    if not h:
        return None
    TEP_UPSTREAM.parent.mkdir(parents=True, exist_ok=True)
    TEP_UPSTREAM.write_text(
        MAU_UPSTREAM.format(hash=h, ngay=time.strftime("%d/%m/%Y")),
        encoding="utf-8")
    return h


def kiem_upstream() -> int:
    """In diff cua hermes-agent o plugins/kanban/dashboard ke tu hash trong UPSTREAM."""
    goc = doc_upstream()
    if not goc:
        print(f"[!] Khong doc duoc hash trong {TEP_UPSTREAM}", file=sys.stderr)
        return 1
    if not (HERMES_AGENT / ".git").exists():
        print(f"[!] {HERMES_AGENT} khong phai repo git (dat HERMES_AGENT_DIR neu o cho khac)",
              file=sys.stderr)
        return 1
    r = subprocess.run(["git", "-C", str(HERMES_AGENT), "diff", "--stat",
                        f"{goc}..HEAD", "--", "plugins/kanban/dashboard"],
                       capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"[!] git diff loi: {r.stderr.strip()[:300]}", file=sys.stderr)
        return 1
    head = hash_upstream()
    print(f"UPSTREAM da port: {goc[:12]}   HEAD hermes-agent: {(head or '?')[:12]}")
    if not r.stdout.strip():
        print("Upstream KHONG doi gi o plugins/kanban/dashboard ke tu lan port cuoi.")
        return 0
    print("Upstream DA DOI (chua co trong plugin cua doi):\n" + r.stdout)
    print("Xem chi tiet:  git -C", HERMES_AGENT, f"diff {goc[:12]}..HEAD -- plugins/kanban/dashboard")
    return 0


def kanban_da_bat(H: Path) -> bool | None:
    """config.yaml cua home co `plugins.enabled` chua "kanban" khong.
    None = khong doc duoc (thieu tep / thieu pyyaml)."""
    p = H / "config.yaml"
    try:
        import yaml
        cfg = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
    except Exception:                                        # noqa: BLE001
        return None
    pl = cfg.get("plugins") if isinstance(cfg, dict) else None
    en = pl.get("enabled") if isinstance(pl, dict) else None
    return isinstance(en, list) and "kanban" in en


def nhac_bat_plugin() -> None:
    """Plugin nguoi dung chi duoc mount API khi co trong plugins.enabled — thieu
    thi tab kanban van hien ma moi request /api/plugins/kanban/* deu 404."""
    hermes_py = HERMES_AGENT / "venv" / "bin" / "python"
    for hk, H in HOMES.items():
        if not plugin_home(H).exists():
            continue
        ok = kanban_da_bat(H)
        if ok:
            continue
        ly = "chua co 'kanban' trong plugins.enabled" if ok is False else "khong doc duoc config.yaml"
        print(f"\n[!] {hk}: {ly} — API cua plugin se KHONG duoc mount. Bat mot lan:")
        print(f"    HERMES_HOME={H} {hermes_py} -m hermes_cli.main plugins enable kanban")
        print(f"    systemctl --user restart hermes-dashboard@{hk}   # hoac unit dashboard cua home nay")


def nhac_don_ban_cai() -> None:
    """Ban cai hermes-agent con giu ban va cu (di san truoc 06/09) thi la ban thu
    ba gay nhieu: ke tu nay ban di kem phai LA upstream nguyen ban."""
    d = HERMES_AGENT / "plugins" / "kanban" / "dashboard"
    if not (HERMES_AGENT / ".git").exists() or not d.exists():
        return
    # --untracked-files=no: chi tinh tep git THEO DOI bi sua. Sau tep .bak cu
    # (untracked) tung lam canh bao nay keu nham ngay 07/09 du ban cai da sach.
    r = subprocess.run(["git", "-C", str(HERMES_AGENT), "status", "--porcelain",
                        "--untracked-files=no", "--", str(d)],
                       capture_output=True, text=True, timeout=10)
    if r.returncode == 0 and r.stdout.strip():
        print(f"\n[!] {d} dang lech so voi upstream (ban va cu con nam trong ban cai).")
        print("    Ke tu 06/09/2026 ban va song o <home>/plugins/kanban/, ban cai phai nguyen ban:")
        print(f"    git -C {HERMES_AGENT} checkout -- plugins/kanban/dashboard")


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
    ap = argparse.ArgumentParser(description="Dong bo SOUL/cron/plugin kanban voi git (multi-home)")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--vao-repo", action="store_true", help="home -> repo")
    g.add_argument("--ra-hermes", action="store_true", help="repo -> home")
    g.add_argument("--kiem-upstream", action="store_true",
                   help="hermes-agent doi gi o plugins/kanban/dashboard ke tu hash trong UPSTREAM")
    g.add_argument("--chot-upstream", action="store_true",
                   help="Da port xong upstream: ghi HEAD hermes-agent vao UPSTREAM")
    ap.add_argument("--ep", action="store_true",
                    help="Ghi de ke ca khi ben nguon thieu ban va cua tep plugin "
                         "(dung sau khi da xem bang tay va chac chan)")
    ap.add_argument("--chi", metavar="CHUOI",
                    help="Chi dong bo cac muc co ten chua CHUOI (vd --chi carousel, "
                         "--chi 'kanban blog'). Dung khi drift hai chieu: day/keo tung phan.")
    a = ap.parse_args()

    if a.kiem_upstream:
        return kiem_upstream()
    if a.chot_upstream:
        h = ghi_upstream()
        print(f"UPSTREAM = {h}" if h else f"[!] Khong doc duoc HEAD cua {HERMES_AGENT}")
        return 0 if h else 1

    khac, thieu, bo_qua, da_chep = [], [], [], 0
    plugin_da_chep = set()      # --vao-repo: moi tep plugin chep MOT lan du hai home
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
            tep = _tep_plugin(ten)
            if tep:
                if tep in plugin_da_chep:
                    continue                          # home kia da chep roi
                ly_do = None if a.chi else hai_home_lech(tep)
                if ly_do and not a.ep:
                    bo_qua.append((ten, ly_do))
                    continue
            # Chieu nay truoc day khong co cong nao — chinh no lam mat hai ban
            # va hom 04/09/2026. Nguon = ban that, dich = ban repo.
            ly_do = thieu_dau_vet(ten, a_b, b_b)
            if ly_do and not a.ep:
                bo_qua.append((ten, ly_do))
                continue
            repo.parent.mkdir(parents=True, exist_ok=True)
            repo.write_bytes(chuan(a_b))          # ghi LF vao repo
            da_chep += 1
            if tep:
                plugin_da_chep.add(tep)
        elif a.ra_hermes:
            if b_b is None:
                continue                # khong co ban repo thi khong ghi de
            # Nguon = ban repo, dich = ban that. Chan khi ban that co dau vet
            # ma ban repo thieu (repo thut lui).
            ly_do = thieu_dau_vet(ten, b_b, a_b)
            if ly_do and not a.ep:
                bo_qua.append((ten, ly_do))
                continue
            that.parent.mkdir(parents=True, exist_ok=True)
            that.write_bytes(chuan(b_b))          # ghi LF vao home
            da_chep += 1

    for t in thieu:
        print(f"  [thieu] {t}", file=sys.stderr)
    # Plugin nguoi dung: home CHUA co thi --ra-hermes TAO (khac profile: day la
    # thu duy nhat repo la nguon goc, khong phai ban chep cua home).
    if a.ra_hermes:
        for hk, H in HOMES.items():
            if not H.exists():
                continue
            for f in PLUGIN_TEP:
                dich, nguon = plugin_home(H) / f, PLUGIN_REPO / f
                if not dich.exists() and nguon.exists() and (not a.chi or a.chi in f"kanban {hk} {f}"):
                    dich.parent.mkdir(parents=True, exist_ok=True)
                    dich.write_bytes(chuan(nguon.read_bytes()))
                    da_chep += 1
                    print(f"  TAO   kanban {hk} {f} -> home")

    if not khac and not da_chep:
        print("Hai ben khop nhau, khong co gi de dong bo.")
        nhac_bat_plugin()
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
    nhac_bat_plugin()
    nhac_don_ban_cai()
    return 0


if __name__ == "__main__":
    sys.exit(main())
