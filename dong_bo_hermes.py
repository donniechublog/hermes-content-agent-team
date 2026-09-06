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

# Plugin kanban nam trong ban cai hermes nen `hermes update` SE ghi de. Da sua
# ba thu o day: thu tu cot (running/ready/blocked truoc), co chu nhan profile,
# va chia lane theo profile o moi cot chu khong chi cot running.
PLUGIN_GOC = Path.home() / "hermes-agent"
PLUGIN_KANBAN = PLUGIN_GOC / "plugins/kanban/dashboard"
PLUGIN_TEP = ["plugin_api.py", "dist/index.js", "dist/style.css"]
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
    for f in PLUGIN_TEP:
        ra.append((f"kanban {f}", PLUGIN_KANBAN / f,
                   REPO / "plugins" / "kanban" / f.replace("/", ".")))
    return ra


LA_PLUGIN = "kanban "

# Dau vet cua tung ban va doi tu sua trong plugin kanban. Cong bao ve cu so
# LECH KICH THUOC (15%) va chi chay o chieu --ra-hermes; no hong ca hai dau:
#  - Chieu --vao-repo KHONG co cong nao. Ngay 04/09/2026 mot ban ~/.hermes vua
#    bi `hermes update` reset ve upstream da di nguoc vao git (commit a1f9387)
#    va xoa mat hai ban va: thu tu cot va chia lane o moi cot.
#  - Ban hermes moi them ~130 dong vao plugin_api.py chi lam lech ~2,4% kich
#    thuoc, lot duoi nguong, nen --ra-hermes van de mat tinh nang upstream.
# Tu 06/09/2026 doi sang kiem THEO DAU VET, ap cho CA HAI CHIEU. Kich thuoc
# khong noi len ban va con hay mat; chuoi dac trung thi co.
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


def thieu_dau_vet(ten: str, nguon: bytes, dich: bytes) -> str | None:
    """Ly do KHONG nen ghi `nguon` de len `dich`, hoac None neu an toan.

    Chi chan khi ben DICH dang co dau vet ma ben NGUON thieu — do dung la kich
    ban ghi de lam mat ban va. Chieu nguoc lai (nguon co, dich thieu) chinh la
    dang mang ban va sang, phai cho chay. Khong bat Exception o day: ca hai ban
    byte da doc xong truoc khi goi, fail-open kieu cu la thu da giau loi.
    """
    if not ten.startswith(LA_PLUGIN):
        return None
    dau = DAU_VET.get(ten[len(LA_PLUGIN):])
    if not dau or nguon is None or dich is None:
        return None
    mat = [nhan for nhan, chuoi in dau
           if chuoi.encode() in dich and chuoi.encode() not in nguon]
    if not mat:
        return None
    return ("ben nguon thieu ban va ma ben dich dang co: " + ", ".join(mat)
            + " — ghi de la mat ban va")


MAU_UPSTREAM = """\
# Xuất xứ bản chép plugin kanban trong repo này. TỆP DO MÁY GHI, đừng sửa tay.
#
# `hermes/plugins/kanban/` không phải mã của đội: nó là bản cài hermes-agent
# (vendor) CỘNG ba bản vá của đội. Muốn nâng lên hermes mới thì phải biết bản
# vá đang đứng trên commit upstream nào, nếu không chỉ còn nước đoán.
#
# Rebase 3 chiều lần sau:
#   git -C ~/hermes-agent diff {hash}..HEAD -- plugins/kanban/dashboard
#   # xem upstream đổi gì, vá lại ba bản vá lên bản mới, chạy --vao-repo
#
# Dòng `commit:` được `dong_bo_hermes.py --vao-repo` ghi lại mỗi lần kéo bản
# cài về repo.

commit: {hash}
ghi_luc: {ngay}
"""


def hash_upstream() -> str | None:
    """HEAD cua ban cai hermes-agent, hoac None neu no khong phai repo git."""
    try:
        r = subprocess.run(["git", "-C", str(PLUGIN_GOC), "rev-parse", "HEAD"],
                           capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return None
    return r.stdout.strip() or None if r.returncode == 0 else None


def ghi_upstream() -> str | None:
    """Ghi lai HEAD upstream sau khi keo ban cai ve repo. Tra ve hash da ghi."""
    h = hash_upstream()
    if not h:
        return None
    TEP_UPSTREAM.parent.mkdir(parents=True, exist_ok=True)
    TEP_UPSTREAM.write_text(
        MAU_UPSTREAM.format(hash=h, ngay=time.strftime("%d/%m/%Y")),
        encoding="utf-8")
    return h


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
                    help="Ghi de ke ca khi ben nguon thieu ban va cua tep plugin "
                         "(dung sau khi da xem bang tay va chac chan)")
    ap.add_argument("--chi", metavar="CHUOI",
                    help="Chi dong bo cac muc co ten chua CHUOI (vd --chi carousel). "
                         "Dung khi drift hai chieu: day/keo tung phan, khong mu.")
    a = ap.parse_args()

    khac, thieu, bo_qua, da_chep = [], [], [], 0
    keo_plugin = False          # co keo tep plugin nao ve repo khong
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
            # Chieu nay truoc day khong co cong nao — chinh no lam mat hai ban
            # va hom 04/09/2026. Nguon = ban that, dich = ban repo.
            ly_do = thieu_dau_vet(ten, a_b, b_b)
            if ly_do and not a.ep:
                bo_qua.append((ten, ly_do))
                continue
            repo.parent.mkdir(parents=True, exist_ok=True)
            repo.write_bytes(chuan(a_b))          # ghi LF vao repo
            da_chep += 1
            if ten.startswith(LA_PLUGIN):
                keo_plugin = True
        elif a.ra_hermes:
            if b_b is None:
                continue                # khong co ban repo thi khong ghi de
            # Nguon = ban repo, dich = ban that. Chan khi ban that co tinh nang
            # upstream moi ma ban repo chua co.
            ly_do = thieu_dau_vet(ten, b_b, a_b)
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
    if keo_plugin:
        h = ghi_upstream()
        print(f"\nUpstream hermes-agent: {h}" if h
              else "\n[!] Khong doc duoc HEAD cua ~/hermes-agent, UPSTREAM giu nguyen.")
    if a.vao_repo or a.ra_hermes:
        print(f"\nDa chep {da_chep} tep.")
    else:
        print(f"\n{len(khac)} tep lech. Chay voi --vao-repo hoac --ra-hermes de dong bo.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
